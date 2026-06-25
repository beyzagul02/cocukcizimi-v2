"""
FastAPI REST API - Çocuk Resim Analiz Servisi
Flutter uygulaması bu API'ye resim gönderir, JSON sonuç alır.
"""

import os
import sys
import tempfile
import json
import pickle
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Proje kök dizinine ekle (api.py ile aynı klasörde çalışır)
sys.path.insert(0, str(Path(__file__).parent))

from torchvision import models, transforms
from PIL import Image
from ultralytics import YOLO

from analyze_relationships import RelationshipAnalyzer
from analyze_colors import ColorAnalyzer

# ------------------------------------------------------------
# Sabitler
# ------------------------------------------------------------
BACKEND_DIR = str(Path(__file__).parent)
MODEL_PATH  = os.path.join(BACKEND_DIR, "fusion_mlp_model.pth")
STATS_PATH  = os.path.join(BACKEND_DIR, "fusion_stats.json")
PCA_PATH    = os.path.join(BACKEND_DIR, "pca_model.pkl")
CNN_PATH    = os.path.join(BACKEND_DIR, "finetuned_cnn.pth")
IMG_SIZE    = (224, 224)
CLASSES     = ["Angry", "Fear", "Happy", "Sad"]
COLOR_ORDER = ["Kırmızı", "Mavi", "Yeşil", "Sarı", "Siyah",
               "Kahverengi", "Mor", "Turuncu", "Pembe", "Gri"]

# ------------------------------------------------------------
# Global model nesneleri (startup'ta yüklenir)
# ------------------------------------------------------------
_models: dict = {}


class FusionMLP(nn.Module):
    def __init__(self, input_dim, num_classes):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 512), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(512, 128),       nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(128, num_classes)
        )

    def forward(self, x):
        return self.net(x)


def get_best_yolo_model():
    finetuned = os.path.join(BACKEND_DIR, "yolo_finetuned.pt")
    if Path(finetuned).exists():
        return finetuned

    runs_dir = Path(os.path.join(BACKEND_DIR, "runs", "detect"))
    if runs_dir.exists():
        def run_num(p):
            s = p.name.replace("yolo_person_model", "")
            return int(s) if s.isdigit() else 0
        candidates = sorted(runs_dir.glob("yolo_person_model*"), key=run_num, reverse=True)
        if candidates:
            wp = candidates[0] / "weights" / "best.pt"
            if wp.exists():
                return str(wp)
    return os.path.join(BACKEND_DIR, "yolov8n.pt")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Uygulama başladığında modelleri yükle — her istekte yükleme yok."""
    print("⏳ Modeller yükleniyor...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # Stats & PCA
    with open(STATS_PATH) as f:
        stats = json.load(f)
    mean = np.array(stats["mean"], dtype=np.float32)
    std  = np.array(stats["std"],  dtype=np.float32)
    with open(PCA_PATH, "rb") as f:
        pca = pickle.load(f)

    # YOLO
    yolo = YOLO(get_best_yolo_model())

    # CNN (feature extractor)
    cnn = models.mobilenet_v2(weights=None)
    in_feat = cnn.classifier[1].in_features
    cnn.classifier[1] = nn.Linear(in_feat, len(CLASSES))
    if Path(CNN_PATH).exists():
        try:
            cnn.load_state_dict(torch.load(CNN_PATH, map_location=device))
            print(f"CNN modeli yüklendi: {CNN_PATH}")
        except Exception as e:
            print(f"CNN state_dict yükleme hatası: {e}")
    cnn.classifier = nn.Identity()
    cnn = cnn.to(device).eval()

    # Fusion MLP
    mlp = FusionMLP(input_dim=128, num_classes=len(CLASSES)).to(device)
    mlp.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    mlp.eval()

    # Color & Relationship
    color_analyzer = ColorAnalyzer()

    _models.update({
        "device": device, "yolo": yolo, "cnn": cnn, "mlp": mlp,
        "pca": pca, "mean": mean, "std": std,
        "color_analyzer": color_analyzer,
    })
    print("✅ Tüm modeller hazır!")
    yield
    # shutdown — temizleme
    _models.clear()


# ------------------------------------------------------------
# FastAPI uygulaması
# ------------------------------------------------------------
app = FastAPI(
    title="Çocuk Resim Analiz API",
    description="Flutter uygulaması için çocuk çizimi duygu & KFD analizi",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — Flutter emülatör ve gerçek cihaz için izin ver
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------
# Yardımcı fonksiyonlar
# ------------------------------------------------------------
def tr_emotion(eng: str) -> str:
    return {"Angry": "Öfkeli", "Fear": "Korku/Endişe",
            "Happy": "Mutlu", "Sad": "Üzgün"}.get(eng, eng)


def extract_yolo_features(yolo_model, img_path: str) -> np.ndarray:
    # imgsz=640 YOLO'nun standart eğitim çözünürlüğüdür, küçük figürleri daha iyi bulur
    results = yolo_model.predict(img_path, verbose=False, conf=0.25)
    r = results[0]
    person_boxes = [b for b in r.boxes if yolo_model.names[int(b.cls[0])] == "person"]
    n = len(person_boxes)
    if n:
        confs = [float(b.conf[0]) for b in person_boxes]
        areas = [float(b.xywhn[0][2] * b.xywhn[0][3]) for b in person_boxes]
        cx    = [float(b.xywhn[0][0]) for b in person_boxes]
        cy    = [float(b.xywhn[0][1]) for b in person_boxes]
        mi    = areas.index(max(areas))
        return np.array([n, max(confs), max(areas), sum(areas)/n, cx[mi], cy[mi], 1], dtype=np.float32)
    return np.array([0, 0, 0, 0, 0.5, 0.5, 0], dtype=np.float32)


def extract_color_features(analyzer, img_path: str) -> np.ndarray:
    try:
        res = analyzer.analyze(img_path, k=5)
        vec = np.zeros(len(COLOR_ORDER), dtype=np.float32)
        for item in res:
            if item["name"] in COLOR_ORDER:
                vec[COLOR_ORDER.index(item["name"])] = item["percent"]
        return vec / 100.0
    except Exception:
        return np.zeros(len(COLOR_ORDER), dtype=np.float32)


def make_serializable(obj):
    """numpy türlerini JSON-serileştirilebilir Python türlerine çevirir."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.generic):
        return obj.item()
    elif isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_serializable(v) for v in obj]
    elif isinstance(obj, tuple):
        return [make_serializable(v) for v in obj]
    return obj


def run_predict(image_path: str) -> dict:
    d     = _models["device"]
    yolo  = _models["yolo"]
    cnn   = _models["cnn"]
    mlp   = _models["mlp"]
    pca   = _models["pca"]
    mean  = _models["mean"]
    std   = _models["std"]
    color = _models["color_analyzer"]

    # YOLO features
    yolo_feat = extract_yolo_features(yolo, image_path)

    # CNN features
    transform = transforms.Compose([
        transforms.Resize(IMG_SIZE),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    img = Image.open(image_path).convert("RGB")
    with torch.no_grad():
        cnn_feat = cnn(transform(img).unsqueeze(0).to(d)).cpu().numpy().flatten()

    # Color features
    color_feat = extract_color_features(color, image_path)

    # Fuse + Normalize + PCA
    combined   = np.concatenate([cnn_feat, yolo_feat, color_feat])
    normalized = (combined - mean) / std
    pca_feat = pca.transform(normalized.reshape(1, -1))[0]

    # Predict
    tensor_in = torch.from_numpy(pca_feat).float().unsqueeze(0).to(d)
    with torch.no_grad():
        out   = mlp(tensor_in) / 2.0   # temperature=2
        probs = torch.softmax(out, dim=1)
        conf, pred = torch.max(probs, 1)

    class_name = CLASSES[pred.item()]
    conf_score = conf.item() * 100

    result = {
        "filename":             Path(image_path).name,
        "prediction":           class_name,
        "prediction_tr":        tr_emotion(class_name),
        "confidence":           round(conf_score, 2),
        "probabilities":        {c: round(probs[0][i].item() * 100, 2) for i, c in enumerate(CLASSES)},
        "person_count":         0,
        "style":                {},
        "movement":             [],
        "details":              [],
        "animals":              [],
        "colors":               [],
        "psychological_summary": "",
        "warnings":             [],
    }

    # KFD & Renk Analizi
    try:
        ra = RelationshipAnalyzer(model=yolo)
        report = ra.analyze_image(image_path)
        result["person_count"] = report.get("person_count", 0)
        result["style"]        = report.get("style_dimensions", {})
        result["movement"]     = report.get("movement_dimensions", [])
        result["details"]      = report.get("details", [])
        result["animals"]      = report.get("animals", [])
        if "error" in report:
            result["warnings"].append(report["error"])

        colors = color.analyze(image_path)
        result["colors"] = colors

        # Psikolojik özet oluştur
        pc    = result["person_count"]
        p_happy = result["probabilities"].get("Happy", 0)
        p_fear  = result["probabilities"].get("Fear", 0)
        placement = result["style"].get("placement", "")

        parts = [
            f"Çizim genel olarak **{class_name}** ({tr_emotion(class_name)}) "
            f"kategorisinde değerlendirilmiştir (Güven: %{conf_score:.0f}).",
            f"Tespit edilen kişi sayısı: {pc}."
        ]

        if pc == 0:
            parts.append("Resimde insan figürü tespit edilememiştir. Bu durum, çocuğun insan ilişkilerinden kaçınma eğilimi veya çizim tarzıyla (soyut/nesne odaklı) ilgili olabilir.")
            if class_name == "Angry" and p_fear > 15:
                parts.append("Model öfke tespiti yapsa da, figür eksikliği gizli bir endişe veya 'boşluk' hissini yansıtıyor olabilir.")

        if class_name == "Fear" and p_happy > 15:
            if "Üst Kısım" in placement or "Sağa Yatkın" in placement:
                warn = "Model 'Korku' tespit etti ancak çizim yerleşimi 'İyimserlik' (mutluluk) işaretleri taşıyor."
                result["warnings"].append(warn)
                parts.append("Dikkat: Yerleşim özellikleri ile tespit edilen duygu arasında çelişki olabilir.")

        hier = result["style"].get("hierarchy", "")
        if pc > 1:
            if "Belirgin" in hier:
                parts.append("Aile içinde belirgin bir güç dengesizliği veya otorite figürü vurgusu göze çarpmaktadır.")
            elif "Orta Düzey" in hier:
                parts.append("Aile bireyleri arasında boyut farkları mevcuttur.")

        if colors:
            dom  = colors[0]["name"]
            pos  = ["Sarı", "Turuncu", "Yeşil", "Pembe"]
            neg  = ["Siyah", "Gri", "Kırmızı"]
            if class_name not in ["Happy"] and dom in pos:
                parts.append(f"Canlı renk kullanımı ({dom}) umut veya savunma mekanizmasına işaret edebilir.")
            elif class_name == "Happy" and dom in neg:
                parts.append(f"Karanlık renk kullanımı ({dom}) gizli bir endişeye işaret edebilir.")
            else:
                parts.append(f"Renk kullanımı ({dom}) tespit edilen duygu durumuyla uyumludur.")

        result["psychological_summary"] = " ".join(parts)
    except Exception as e:
        result["warnings"].append(f"Analiz hatası: {e}")

    return result


# ------------------------------------------------------------
# Endpoint'ler
# ------------------------------------------------------------
@app.get("/health")
def health():
    """Sunucu hazır mı?"""
    return {"status": "ok", "models_loaded": len(_models) > 0}


@app.get("/")
def root():
    """Kök endpoint."""
    return {"status": "healthy", "message": "Child Drawing Analysis API is running", "version": "v2.0"}


@app.post("/analyze")
async def analyze(image: UploadFile = File(...)):
    """
    Resim yükle ve analiz et.
    - multipart/form-data, field adı: 'image'
    - Döndürür: JSON (duygu, KFD, renkler, psikolojik özet)
    """
    if not _models:
        raise HTTPException(503, "Modeller henüz yüklenmedi, lütfen bekleyin.")

    # Geçici dosyaya kaydet (masaüstü versiyonuyla aynı: ön işleme yok)
    suffix = Path(image.filename).suffix if image.filename else ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        contents = await image.read()
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        result = run_predict(tmp_path)
        serializable = make_serializable(result)
        return JSONResponse(content=serializable)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(500, f"Analiz başarısız: {e}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

