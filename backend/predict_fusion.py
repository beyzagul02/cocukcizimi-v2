import numpy as np
import torch
import torch.nn as nn
from ultralytics import YOLO
from torchvision import models, transforms
from PIL import Image
import json
import argparse
import pickle
from pathlib import Path
from analyze_relationships import RelationshipAnalyzer
from analyze_colors import ColorAnalyzer

COLOR_ORDER = ["Kırmızı", "Mavi", "Yeşil", "Sarı", "Siyah", "Kahverengi", "Mor", "Turuncu", "Pembe", "Gri"]

# --- AYARLAR ---
model_path = "fusion_mlp_model.pth"
stats_path = "fusion_stats.json"
img_size = (224, 224)
classes = ["Angry", "Fear", "Happy", "Sad"]

# MLP Modeli Tanımı (Eğitimdeki ile AYNI olmalı)
class FusionMLP(nn.Module):
    def __init__(self, input_dim, num_classes):
        super(FusionMLP, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, num_classes)
        )
        
    def forward(self, x):
        return self.net(x)

def get_best_yolo_model():
    runs_dir = Path("runs/detect")
    if not runs_dir.exists():
        return "yolov8n.pt"
        
    def get_run_number(p):
        name = p.name
        suffix = name.replace("yolo_person_model", "")
        return int(suffix) if suffix.isdigit() else 0

    candidates = sorted(list(runs_dir.glob("yolo_person_model*")), key=get_run_number, reverse=True)
    if candidates:
        weights_path = candidates[0] / "weights" / "best.pt"
        if weights_path.exists():
            return str(weights_path)
    return "yolov8n.pt"

def extract_yolo_features(model, img_path):
    # YOLO feature extraction logic
    results = model.predict(img_path, verbose=False, conf=0.25)
    r = results[0]
    
    person_boxes = []
    for box in r.boxes:
        cls_id = int(box.cls[0])
        cname = model.names[cls_id]
        if cname == "person":
            person_boxes.append(box)
    
    person_count = len(person_boxes)
    has_person = 1 if person_count > 0 else 0
    
    if has_person:
        confs = [float(box.conf[0]) for box in person_boxes]
        areas = [float(box.xywhn[0][2] * box.xywhn[0][3]) for box in person_boxes]
        centers_x = [float(box.xywhn[0][0]) for box in person_boxes]
        centers_y = [float(box.xywhn[0][1]) for box in person_boxes]
        
        max_conf = max(confs)
        max_area = max(areas)
        mean_area = sum(areas) / person_count
        
        max_area_idx = areas.index(max_area)
        main_center_x = centers_x[max_area_idx]
        main_center_y = centers_y[max_area_idx]
    else:
        max_conf = 0.0
        max_area = 0.0
        mean_area = 0.0
        main_center_x = 0.5
        main_center_y = 0.5
        
    return np.array([person_count, max_conf, max_area, mean_area, main_center_x, main_center_y, has_person], dtype=np.float32)

def extract_color_features(analyzer, img_path):
    """
    Returns a fixed-size vector (len=10) of color percentages based on COLOR_ORDER.
    """
    try:
        results = analyzer.analyze(img_path, k=5)
        feat_vec = np.zeros(len(COLOR_ORDER), dtype=np.float32)
        for item in results:
            name = item['name']
            if name in COLOR_ORDER:
                idx = COLOR_ORDER.index(name)
                feat_vec[idx] = item['percent']
        # Normalize to 0-1 range
        feat_vec = feat_vec / 100.0
        return feat_vec
    except Exception as e:
        print(f"Color extract error {img_path}: {e}")
        return np.zeros(len(COLOR_ORDER), dtype=np.float32)

def tr_emotion(eng):
    mapping = {"Angry": "Öfkeli", "Fear": "Korku/Endişe", "Happy": "Mutlu", "Sad": "Üzgün"}
    return mapping.get(eng, eng)

def print_cli_report(result):
    print("\n" + "="*60)
    print(f"ÇOCUK RESMİ ANALİZ RAPORU")
    print("="*60)
    print(f"DOSYA: {result['filename']}")
    print("-" * 60)
    
    print(f"\n[1] DUYGU ANALİZİ (Fusion):")
    print(f"  ANA TAHMİN:  {result['prediction'].upper()} (Güven: %{result['confidence']:.1f})")
    
    # Probabilities
    sorted_probs = sorted(result['probabilities'].items(), key=lambda x: x[1], reverse=True)
    for cls, scr in sorted_probs:
        bar = "█" * int(scr/5)
        print(f"    - {cls:5s}: %{scr:.1f}  {bar}")
        
    if result["warnings"]:
        print("\n  [!] UYARILAR:")
        for w in result["warnings"]:
            print(f"    - {w}")

    print("\n[2] PSİKOLOJİK SENARYO (ÖZET):")
    print(f"  {result['psychological_summary']}")

    print("\n[3] KOMPOZİSYON VE İLİŞKİLER (KFD):")
    style = result.get('style', {})
    print(f"  * Yerleşim: {style.get('placement', 'N/A')}")
    print(f"  * Hiyerarşi: {style.get('hierarchy', 'N/A')}")
    
    movement = result.get('movement', [])
    if movement:
        for m in movement:
            print(f"  * {m['pair'][0]} <-> {m['pair'][1]}: {m['comment']} ({m['distance']:.2f})")
            
    colors = result.get('colors', [])
    if colors:
        print(f"\n[4] RENK ANALİZİ:")
        for c in colors[:5]:
            print(f"  * {c['name']} (%{c['percent']:.1f}): {c['meaning']}")
            
    animals = result.get('animals', [])
    if animals:
        print(f"\n[5] HAYVAN FİGÜRLERİ:")
        for a in animals:
            print(f"  * Tespit: {a['type']} (Güven: %{a['confidence']*100:.1f})")
            
    print("\n" + "="*60 + "\n")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
stats_mean = None
stats_std = None
yolo_model = None
cnn_model = None
color_analyzer = None
mlp_model = None
pca_model = None

def init_models():
    global stats_mean, stats_std, yolo_model, cnn_model, color_analyzer, mlp_model, pca_model
    if yolo_model is not None:
        return
        
    print("Modeller hafızaya yükleniyor...")
    
    # 1. Load Stats
    if not Path(stats_path).exists():
        print("HATA: İstatistik dosyası bulunamadı. Önce eğitimi çalıştırın.")
        return
        
    with open(stats_path, "r") as f:
        stats = json.load(f)
    stats_mean = np.array(stats["mean"], dtype=np.float32)
    stats_std = np.array(stats["std"], dtype=np.float32)
    
    # 2. Load Models
    yolo_model = YOLO(get_best_yolo_model())
    
    cnn_model = models.mobilenet_v2(weights=None)
    in_features = cnn_model.classifier[1].in_features
    cnn_model.classifier[1] = nn.Linear(in_features, len(classes))
    if Path('finetuned_cnn.pth').exists():
        cnn_model.load_state_dict(torch.load('finetuned_cnn.pth', map_location=device))
    cnn_model.classifier = nn.Identity()
    cnn_model = cnn_model.to(device)
    cnn_model.eval()

    # Color Analyzer
    color_analyzer = ColorAnalyzer()
    
    # 3. Load MLP
    mlp_model = FusionMLP(input_dim=128, num_classes=len(classes)).to(device)
    if Path(model_path).exists():
        mlp_model.load_state_dict(torch.load(model_path, map_location=device))
    mlp_model.eval()
    
    # 4. Load PCA
    try:
        with open("pca_model.pkl", "rb") as f:
            pca_model = pickle.load(f)
    except Exception as e:
        print(f"PCA yükleme hatası: {e}")

# Modelleri Flask ayağa kalkarken otomatik yükle
init_models()

def predict(image_path):
    init_models()
    if yolo_model is None or cnn_model is None or mlp_model is None:
        print("HATA: Modeller yüklenemedi.")
        return None
        
    # 4. Extract Features
    print(f"Analiz ediliyor: {image_path}")
    
    # YOLO
    try:
        yolo_feat = extract_yolo_features(yolo_model, image_path)
    except Exception as e:
         print(f"YOLO Hatası: {e}")
         return None

    # CNN
    try:
        transform = transforms.Compose([
            transforms.Resize(img_size),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        img = Image.open(image_path).convert('RGB')
        img_t = transform(img).unsqueeze(0).to(device)
        
        with torch.no_grad():
            cnn_feat = cnn_model(img_t)
        cnn_feat = cnn_feat.cpu().numpy().flatten()
    except Exception as e:
        print(f"CNN Hatası: {e}")
        return None

    # Color
    try:
        color_feat = extract_color_features(color_analyzer, image_path)
    except Exception as e:
        print(f"Color Feat Hatası: {e}")
        return None

    # 5. Fuse & Normalize
    try:
        combined_feat = np.concatenate([cnn_feat, yolo_feat, color_feat])
        normalized_feat = (combined_feat - stats_mean) / stats_std
        
        if pca_model is not None:
            normalized_feat = pca_model.transform(normalized_feat.reshape(1, -1))[0]
        
    except Exception as e:
        print(f"Özellik Birleştirme veya PCA Hatası: {e}")
        return None
    
    # 6. Predict
    tensor_input = torch.from_numpy(normalized_feat).float().unsqueeze(0).to(device)
    temperature = 2.0
    
    with torch.no_grad():
        outputs = mlp_model(tensor_input)
        scaled_outputs = outputs / temperature
        probs = torch.softmax(scaled_outputs, dim=1)
        confidence, predicted = torch.max(probs, 1)
        
    class_idx = predicted.item()
    class_name = classes[class_idx]
    conf_score = confidence.item() * 100
    
    # Store results
    result_data = {
        "filename": Path(image_path).name,
        "prediction": class_name,
        "confidence": conf_score,
        "probabilities": {cls: probs[0][i].item()*100 for i, cls in enumerate(classes)},
        "person_count": 0,
        "style": {},
        "movement": [],
        "details": [],
        "psychological_summary": "",
        "warnings": []
    }

    # 7. Relationship Analysis & Extensions
    try:
        analyzer = RelationshipAnalyzer(model=yolo_model)
        report = analyzer.analyze_image(image_path)
        
        result_data["person_count"] = report.get("person_count", 0)
        result_data["style"] = report.get("style_dimensions", {})
        result_data["movement"] = report.get("movement_dimensions", [])
        result_data["details"] = report.get("details", [])
        result_data["animals"] = report.get("animals", [])
        
        if "error" in report:
            result_data["warnings"].append(report["error"])

        # Color Analysis Report
        colors = color_analyzer.analyze(image_path)
        result_data["colors"] = colors

        # --- HEURISTICS & SYNTHESIS ---
        summary_parts = []
        
        summary_parts.append(f"Çizim genel olarak **{class_name}** ({tr_emotion(class_name)}) kategorisinde değerlendirilmiştir (Güven: %{conf_score:.0f}).")
        
        person_count = result_data.get("person_count", 0)
        placement = result_data["style"].get("placement", "")
        p_happy = result_data["probabilities"].get("Happy", 0)
        p_fear = result_data["probabilities"].get("Fear", 0)
        
        if person_count == 0:
            summary_parts.append("Resimde insan figürü tespit edilememiştir. Bu durum, çocuğun insan ilişkilerinden kaçınma eğilimi veya çizim tarzıyla (soyut/nesne odaklı) ilgili olabilir.")
            if class_name == "Angry" and p_fear > 15:
                 summary_parts.append("Model öfke tespiti yapsa da, figür eksikliği gizli bir endişe veya 'boşluk' hissini yansıtıyor olabilir.")
        
        if class_name == "Fear" and p_happy > 15:
            if "Üst Kısım" in placement or "Sağa Yatkın" in placement:
                warn = "Model 'Korku' tespit etti ancak çizim yerleşimi 'İyimserlik' (mutluluk) işaretleri taşıyor."
                result_data["warnings"].append(warn)
                summary_parts.append("Dikkat: Yerleşim özellikleri ile tespit edilen duygu arasında çelişki olabilir.")

        hier_note = result_data["style"].get("hierarchy", "")
        if person_count > 1:
            if "Belirgin Hiyerarşik Fark" in hier_note:
                summary_parts.append("Aile içinde belirgin bir güç dengesizliği veya otorite figürü vurgusu göze çarpmaktadır.")
            elif "Orta Düzey" in hier_note:
                summary_parts.append("Aile bireyleri arasında boyut farkları mevcuttur.")
            
        if colors:
            dom_color = colors[0]
            # dom_meaning = dom_color["meaning"]
            
            positive_colors = ["Sarı", "Turuncu", "Yeşil", "Pembe"]
            negative_colors = ["Siyah", "Gri", "Kırmızı"] # Kırmızıyı da ekleyelim (öfke)
            
            emotion_type = "Positive" if class_name in ["Happy"] else "Negative"
            color_type = "Neutral"
            if dom_color["name"] in positive_colors: color_type = "Positive"
            if dom_color["name"] in negative_colors: color_type = "Negative"
            
            if emotion_type == "Negative" and color_type == "Positive":
                summary_parts.append(f"Duygu analizi negatif ({tr_emotion(class_name)}) olmasına rağmen, kullanılan canlı renkler ({dom_color['name']}) umut veya savunma mekanizmasına işaret edebilir.")
            elif emotion_type == "Positive" and color_type == "Negative":
                 summary_parts.append(f"Duygu analizi pozitif olsa da, karanlık renklerin ({dom_color['name']}) kullanımı gizli bir endişeye işaret edebilir.")
            else:
                 summary_parts.append(f"Renk kullanımı ({dom_color['name']}) tespit edilen duygu durumuyla uyumludur.")

        result_data["psychological_summary"] = " ".join(summary_parts)

    except Exception as e:
        print(f"Analiz hatası: {e}")
        result_data["warnings"].append(f"Analiz sırasında hata: {e}")

    return result_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("image", nargs="?", help="Resim dosyasının yolu")
    args = parser.parse_args()
    
    if args.image:
        res = predict(args.image)
        if res: print_cli_report(res)
    else:
        test_dir = Path("dataset_all/Happy")
        if test_dir.exists():
            test_img = next(test_dir.glob("*.jpg"), None)
            if test_img:
                res = predict(str(test_img))
                if res: print_cli_report(res)
            else:
                print("Lütfen bir resim yolu belirtin.")
