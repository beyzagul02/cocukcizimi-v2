import sys
from ultralytics import YOLO
import cv2
from pathlib import Path
import argparse

def predict_persons(params):
    # Confidence threshold (varsayılan 0.4 veya kullanıcının girdiği)
    conf_thres = float(params.conf) if params.conf else 0.4
    
    # 1. Model Yükleme
    # En son eğitilen modeli otomatik bul
    runs_dir = Path("runs/detect")
    runs_dir = Path("runs/detect")
    # Sort numerically by suffix (e.g., yolo_person_model7 > yolo_person_model2)
    def get_run_number(p):
        name = p.name
        suffix = name.replace("yolo_person_model", "")
        return int(suffix) if suffix.isdigit() else 0

    candidates = sorted(list(runs_dir.glob("yolo_person_model*")), key=get_run_number, reverse=True)
    
    custom_model_path = None
    if candidates:
        latest_model_dir = candidates[0]
        possible_weight = latest_model_dir / "weights" / "best.pt"
        if possible_weight.exists():
            custom_model_path = str(possible_weight)
            
    if custom_model_path and Path(custom_model_path).exists():
        print(f"Özel eğitilmiş model yükleniyor: {custom_model_path}")
        model = YOLO(custom_model_path)
    else:
        print("UYARI: Özel model bulunamadı (veya runs/detect klasörü boş), genel 'yolov8n.pt' modeli kullanılıyor.")
        model = YOLO("yolov8n.pt")

    # Tek resim modu
    if params.image:
        img_path = Path(params.image)
        if not img_path.exists():
            print(f"HATA: Dosya bulunamadı: {img_path}")
            return

        print(f"\n--- Tek Resim Analizi: {img_path.name} ---")
        # save=True ile sonuç görselini runs/detect/predict klasörüne kaydeder
        results = model.predict(img_path, save=True, conf=conf_thres, verbose=False)
        
        for r in results:
            person_count = 0
            for box in r.boxes:
                # Sınıf kontrolü
                cls_id = int(box.cls[0])
                class_name = model.names[cls_id] if model.names else "unknown"
                
                if class_name == "person":
                    person_count += 1
            
            print(f"Tespit edilen kişi sayısı: {person_count}")
            print(f"Sonuç görseli kaydedildi: {r.save_dir}")
            
            with open("last_result.txt", "w", encoding="utf-8") as f:
                f.write(f"Count: {person_count}\nPath: {r.save_dir}")
        return

    # Toplu mod (Klasör tarama)
    search_paths = [Path("dataset_all"), Path(".")]
    emotions = ["Angry", "Fear", "Happy", "Sad"]
    
    print("\n--- Toplu Person Sayma İşlemi Başlıyor ---\n")

    for emotion in emotions:
        emotion_dir = None
        for search_path in search_paths:
            candidate = search_path / emotion
            if candidate.exists() and candidate.is_dir():
                emotion_dir = candidate
                break
        
        if not emotion_dir:
            continue

        print(f"\n>>> Klasör: {emotion}")
        
        images = list(emotion_dir.glob("*.jpg")) + list(emotion_dir.glob("*.png")) + list(emotion_dir.glob("*.jpeg"))
        
        if not images:
            print("  Resim bulunamadı.")
            continue

        # batch işleme
        results = model.predict(images, stream=True, conf=conf_thres, verbose=False)
        
        for r in results:
            current_img_persons = 0
            for box in r.boxes:
                cls_id = int(box.cls[0])
                class_name = model.names[cls_id] if model.names else "unknown"
                
                if class_name == "person":
                    current_img_persons += 1
            
            # Her resim için yazdır
            print(f"  {Path(r.path).name} -> {current_img_persons} kişi")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLO Person Sayma")
    parser.add_argument("--image", type=str, help="Tek bir resim yolu verin (Opsiyonel)")
    parser.add_argument("--conf", type=float, help="Güven eşiği (0.1 - 1.0 arası)", default=0.4)
    args = parser.parse_args()

    predict_persons(args)

    