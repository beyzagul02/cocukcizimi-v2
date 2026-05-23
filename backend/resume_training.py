from ultralytics import YOLO

def resume_training():
    print("Eğitim kaldığı yerden devam ettiriliyor...")
    print("Ezberleme (overfitting) kontrolü aktif: 20 epoch boyunca iyileşme olmazsa eğitim duracak.")
    
    # Load the model from the last checkpoint
    # Bu dosya önceki eğitimin optimizasyon durumunu ve ayarlarını içerir
    model = YOLO("runs/detect/yolo_person_model5/weights/last.pt")
    
    # Resume training
    # resume=True parametresi, önceki ayarlarla (patience=20 dahil) devam etmesini sağlar
    results = model.train(resume=True)

if __name__ == "__main__":
    resume_training()
