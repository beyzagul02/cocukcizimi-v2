import os
from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.model_selection import train_test_split

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

# --- AYARLAR ---
img_size = (224, 224)
data_dir = Path("dataset_all")

# --- 1) KLASÖRLERDEN RESİMLERİ ELLE OKU ---

# Sınıf isimlerini klasör adlarından al
class_names = sorted([d.name for d in data_dir.iterdir() if d.is_dir()])
num_classes = len(class_names)
print("Sınıflar:", class_names)

class_to_idx = {name: i for i, name in enumerate(class_names)}

images = []
labels = []

for class_name in class_names:
    class_folder = data_dir / class_name
    for img_path in class_folder.glob("*.*"):
        try:
            # Resmi aç, RGB'ye çevir, yeniden boyutlandır
            img = Image.open(img_path).convert("RGB")
            img = img.resize(img_size)

            images.append(np.array(img))
            labels.append(class_to_idx[class_name])
        except Exception as e:
            print("Atlanıyor:", img_path, "hata:", e)

images = np.array(images, dtype="float32") / 255.0  # 0-1 arası normalizasyon
labels = np.array(labels)

print("Toplam görüntü:", images.shape, "Toplam etiket:", labels.shape)

# One-hot encode etiketler
labels_cat = keras.utils.to_categorical(labels, num_classes=num_classes)

# --- 2) TRAIN / VAL / TEST BÖL ---
X_train, X_temp, y_train, y_temp = train_test_split(
    images, labels_cat, test_size=0.2, random_state=42, stratify=labels
)

X_val, X_test, y_val, y_test = train_test_split(
    X_temp, y_temp, test_size=0.5, random_state=42
)

print("Train:", X_train.shape, "Val:", X_val.shape, "Test:", X_test.shape)

# --- 3) MODEL (Transfer Learning - MobileNetV2) ---

input_shape = img_size + (3,)

base_model = tf.keras.applications.MobileNetV2(
    input_shape=input_shape,
    include_top=False,
    weights="imagenet"
)
base_model.trainable = False  # önce dondurduk

inputs = keras.Input(shape=input_shape)
# MobileNet için uygun ölçeklendirme
x = tf.keras.applications.mobilenet_v2.preprocess_input(inputs)
x = base_model(x, training=False)
x = layers.GlobalAveragePooling2D()(x)
x = layers.Dropout(0.3)(x)
outputs = layers.Dense(num_classes, activation="softmax")(x)

model = keras.Model(inputs, outputs)

model.compile(
    optimizer=keras.optimizers.Adam(1e-4),
    loss="categorical_crossentropy",
    metrics=["accuracy"]
)

model.summary()

# --- 4) EĞİTİM ---
history = model.fit(
    X_train, y_train,
    validation_data=(X_val, y_val),
    epochs=10,
    batch_size=16
)

# --- 5) TEST PERFORMANSI ---
test_loss, test_acc = model.evaluate(X_test, y_test)
print("Test loss:", test_loss)
print("Test accuracy:", test_acc)

# --- 6) MODELİ KAYDET ---
model.save("emotion_model.h5")
print("Model kaydedildi: emotion_model.h5")
