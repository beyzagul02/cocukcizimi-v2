import os
import numpy as np
from pathlib import Path
from ultralytics import YOLO
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

from analyze_colors import ColorAnalyzer

COLOR_ORDER = ["Kırmızı", "Mavi", "Yeşil", "Sarı", "Siyah", "Kahverengi", "Mor", "Turuncu", "Pembe", "Gri"]

# --- AYARLAR ---
dataset_path = Path("dataset_all")
output_file_X = "fusion_features.npy"
output_file_y = "fusion_labels.npy"
img_size = (224, 224)

# Sınıflar
classes = ["Angry", "Fear", "Happy", "Sad"]
class_map = {cls: i for i, cls in enumerate(classes)}

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
            print(f"Loading custom YOLO model: {weights_path}")
            return str(weights_path)
    
    print("Custom model not found, using yolov8n.pt")
    return "yolov8n.pt"

def extract_yolo_features(model, img_path):
    results = model.predict(img_path, verbose=False, conf=0.25)
    r = results[0]
    
    person_boxes = []
    for box in r.boxes:
        cls_id = int(box.cls[0])
        # class names might be missing or different index, check names dict
        # yolov8n base model: person is usually class 0
        cname = model.names[cls_id]
        if cname == "person":
            person_boxes.append(box)
    
    person_count = len(person_boxes)
    has_person = 1 if person_count > 0 else 0
    
    if has_person:
        confs = [float(box.conf[0]) for box in person_boxes]
        # xywhn -> x_center, y_center, width, height (normalized)
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
        # analyze returns list of dicts: {'name': 'Kırmızı', 'percent': 20.0, ...}
        # default k=5
        results = analyzer.analyze(img_path, k=5)
        
        feat_vec = np.zeros(len(COLOR_ORDER), dtype=np.float32)
        
        for item in results:
            name = item['name']
            if name in COLOR_ORDER:
                idx = COLOR_ORDER.index(name)
                feat_vec[idx] = item['percent']
                
        # Normalize to 0-1 range (optional, but good for MLP)
        # Percentages sum to <= 100. Let's divide by 100.
        feat_vec = feat_vec / 100.0
        return feat_vec
        
    except Exception as e:
        print(f"Color extract error {img_path}: {e}")
        return np.zeros(len(COLOR_ORDER), dtype=np.float32)

def main():
    # 1. Cihaz Seçimi
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Kullanılan cihaz: {device}")

    # 2. Modelleri Yükle
    print("YOLO Modeli yükleniyor...")
    yolo_path = get_best_yolo_model()
    yolo_model = YOLO(yolo_path)
    # ultralytics handles device internally
    
    print("Fine-Tuned CNN (MobileNetV2) Modeli yükleniyor...")
    cnn_model = models.mobilenet_v2(weights=None)
    in_features = cnn_model.classifier[1].in_features
    cnn_model.classifier[1] = nn.Linear(in_features, len(classes))
    
    if os.path.exists('finetuned_cnn.pth'):
        cnn_model.load_state_dict(torch.load('finetuned_cnn.pth', map_location=device))
        print("  -> Başarıyla yüklendi: finetuned_cnn.pth")
    else:
        print("  -> UYARI: finetuned_cnn.pth bulunamadı!")
        
    cnn_model.classifier = nn.Identity() # Sınıflandırma başlığını kesip özellik (feature) çıkartıcı yapıyoruz
    cnn_model = cnn_model.to(device)
    cnn_model.eval()

    # Color Analyzer
    print("Renk Analizörü hazırlanıyor...")
    color_analyzer = ColorAnalyzer()

    # Preprocessing
    transform = transforms.Compose([
        transforms.Resize(img_size),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    
    X_features = []
    y_labels = []
    
    
    print("Veri işleniyor...")
    current_idx = 0
    total_images = sum([len(list((dataset_path / cls).glob("*.*"))) for cls in classes if (dataset_path / cls).exists()])
    
    for cls in classes:
            folder = dataset_path / cls
            if not folder.exists():
                continue
                
            label = class_map[cls]
            
            for img_file in folder.iterdir():
                if img_file.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.webp', '.bmp']:
                    continue
                    
                try:
                    # --- Step A: YOLO Features (7-dim) ---
                    # YOLO expects path or image
                    yolo_feat = extract_yolo_features(yolo_model, str(img_file))
                    
                    # --- Step B: CNN Features (1280-dim) ---
                    img = Image.open(img_file).convert('RGB')
                    img_t = transform(img).unsqueeze(0).to(device)
                    
                    with torch.no_grad():
                        cnn_feat = cnn_model(img_t) # (1, 1280) veya benzeri
                        # MobilenetV2 classifier replaced with Identity usually returns pooled features if we modify classifier correctly.
                        # Wait, original classifier is Sequential(Dropout, Linear).
                        # Replacing it with Identity leaves output of features + pooling?
                        # checking architecture: features -> adaptive avg pool -> classifier.
                        # So replacing classifier with Identity gives output of pooling (1280). Correct.

                    cnn_feat = cnn_feat.cpu().numpy().flatten()

                    # --- Step C: Color Features (10-dim) ---
                    color_feat = extract_color_features(color_analyzer, str(img_file))
                    
                    # --- Step D: Concatenate ---
                    combined_feat = np.concatenate([cnn_feat, yolo_feat, color_feat])
                    
                    X_features.append(combined_feat)
                    y_labels.append(label)
                    
                except Exception as e:
                    print(f"Error processing {img_file.name}: {e}")
                
                current_idx += 1
                if current_idx % 50 == 0:
                    print(f"İşlenen: {current_idx}/{total_images}", end="\r")

    X = np.array(X_features)
    y = np.array(y_labels)
    
    if len(X) == 0:
        print("HATA: Hiç özellik çıkarılamadı!")
        return

    print(f"\nİşlem tamamlandı!")
    print(f"Toplam Veri: {len(X)}")
    print(f"Özellik Vektörü Boyutu: {X.shape[1]}")
    
    np.save(output_file_X, X)
    np.save(output_file_y, y)
    print(f"Dosyalar kaydedildi: {output_file_X}, {output_file_y}")

if __name__ == "__main__":
    main()
