from ultralytics import YOLO
import torch

def train_yolo():
    # 1. Model seçimi (Transfer learning için yolov8n.pt kullanıyoruz)
    # Eğer önceden eğittiğiniz bir model varsa yolunu verin (örn: "runs/detect/train/weights/best.pt")
    model = YOLO("yolov8n.pt") 

    # 2. Eğitim parametreleri
    # data: data.yaml dosyasının yolu
    # epochs: Eğitim tur sayısı (örn: 50 veya 100)
    # imgsz: Resim boyutu (YOLOv8 genelde 640 kullanır)
    # batch: Batch size (GPU belleğine göre ayarlayın, -1 otomatiktir)
    
    print("Eğitim başlıyor...")
    
    # Check for GPU
    device = 0 if torch.cuda.is_available() else "cpu"
    print(f"Kullanılan cihaz: {device}")

    try:
        results = model.train(
            data="data.yaml",
            epochs=30,
            imgsz=640,
            device=device,
            name="yolo_person_model", # Kaydedilecek klasör adı
            patience=20, # Erken durdurma
        )
        print("Eğitim tamamlandı.")
        print(f"En iyi model şurada kaydedildi: runs/detect/yolo_person_model/weights/best.pt")
        
    except Exception as e:
        print(f"Eğitim sırasında hata oluştu: {e}")
        print("Lütfen 'dataset' klasörünüzün ve 'data.yaml' dosyanızın doğru yapılandırıldığından emin olun.")

if __name__ == "__main__":
    train_yolo()
