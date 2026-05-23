import numpy as np
from pathlib import Path
from PIL import Image
import tensorflow as tf
from tensorflow import keras
import sys

# --- AYARLAR ---
img_size = (224, 224)
# Model dosyasının yolu - script ile aynı dizinde olduğunu varsayıyoruz
model_path = Path(__file__).parent / "emotion_model.h5"

# Sınıf isimleri (Eğitimdeki alfabetik sıraya göre)
# dataset_all klasörüne bakarak bu sırayı doğruladım: Angry, Fear, Happy, Sad
class_names = ["Angry", "Fear", "Happy", "Sad"]

# Türkçe Karşılıklar
tr_map = {
    "Angry": "Kızgın",
    "Fear": "Korku",
    "Happy": "Mutlu",
    "Sad": "Üzgün"
}

def predict_single_image(image_path):
    # Modeli yükle (Eğer global yüklemediysek, her çağrıda yüklemek yavaş olabilir ama tek seferlik test için ok)
    if not model_path.exists():
        print(f"HATA: Model dosyası bulunamadı: {model_path}")
        return

    print("Model yükleniyor...")
    model = keras.models.load_model(model_path)

    img_path = Path(image_path)
    if not img_path.exists():
        print(f"HATA: Resim dosyası bulunamadı: {img_path}")
        return

    # Resmi işle
    try:
        img = Image.open(img_path).convert("RGB")
        img = img.resize(img_size)
    except Exception as e:
        print(f"Resim açılırken hata oluştu: {e}")
        return

    x = np.array(img, dtype="float32") / 255.0  # 0-1 arası normalizasyon
    x = np.expand_dims(x, axis=0)  # (1, 224, 224, 3) batch boyutu ekle

    # Tahmin
    preds = model.predict(x)[0]
    pred_idx = np.argmax(preds)
    pred_label_en = class_names[pred_idx]
    pred_label_tr = tr_map.get(pred_label_en, pred_label_en)
    confidence = preds[pred_idx]

    # Çıktı
    print("-" * 30)
    print(f"Dosya: {img_path.name}")
    print(f"Baskın Duygu: {pred_label_tr} ({pred_label_en})")
    print(f"Güven Oranı: %{confidence * 100:.2f}")
    print("-" * 30)
    return pred_label_tr

if __name__ == "__main__":
    # Konsoldan argüman olarak resim yolu alabilir veya varsayılanı kullanabilir
    if len(sys.argv) > 1:
        target_img = sys.argv[1]
    else:
        # Varsayılan test resmi (Eğer varsa)
        target_img = "dataset_all/Happy/h1.jpg"
    
    predict_single_image(target_img)
