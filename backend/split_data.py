from pathlib import Path
import os
import shutil
import random

# TÜM RESİMLERİN OLDUĞU KLASÖR
SOURCE_DIR = Path("dataset_all")  # CocukDuyguProje/dataset_all
TARGET_DIR = Path("dataset")     # Yeni klasörümüz

# Yüzde oranları
train_ratio = 0.7
val_ratio = 0.15
test_ratio = 0.15

random.seed(42)

classes = [d.name for d in SOURCE_DIR.iterdir() if d.is_dir()]
print("Sınıflar:", classes)

# dataset/train, dataset/val, dataset/test klasörlerini oluştur
for split in ["train", "val", "test"]:
    for cls in classes:
        (TARGET_DIR / split / cls).mkdir(parents=True, exist_ok=True)

for cls in classes:
    images = list((SOURCE_DIR / cls).glob("*.*"))
    random.shuffle(images)

    n_total = len(images)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)

    train_imgs = images[:n_train]
    val_imgs = images[n_train:n_train + n_val]
    test_imgs = images[n_train + n_val:]

    print(f"{cls} -> train:{len(train_imgs)}, val:{len(val_imgs)}, test:{len(test_imgs)}")

    for img in train_imgs:
        shutil.copy(img, TARGET_DIR / "train" / cls / img.name)
    for img in val_imgs:
        shutil.copy(img, TARGET_DIR / "val" / cls / img.name)
    for img in test_imgs:
        shutil.copy(img, TARGET_DIR / "test" / cls / img.name)

print("Bölme tamamlandı!")
