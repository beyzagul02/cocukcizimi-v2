import os
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, transforms, models
from torch.utils.data import DataLoader, random_split
from sklearn.utils.class_weight import compute_class_weight
import numpy as np

# --- AYARLAR ---
data_dir = 'dataset_all'
batch_size = 32
num_epochs = 8
learning_rate = 1e-4

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Kullanılan cihaz: {device}")

# 1. Veri Artırma (Data Augmentation) ve Yükleme
# Eğitim seti için agresif veri artırma
train_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(15),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

# Validasyon seti için normal yükleme
val_transforms = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

full_dataset = datasets.ImageFolder(data_dir)
print(f"Sınıflar: {full_dataset.classes}")
num_classes = len(full_dataset.classes)

# Class Weights (Sınıf Ağırlıkları)
targets = [s[1] for s in full_dataset.samples]
class_weights = compute_class_weight(class_weight='balanced', classes=np.unique(targets), y=targets)
class_weights_tensor = torch.tensor(class_weights, dtype=torch.float32).to(device)
print(f"Sınıf Ağırlıkları: {class_weights}")

# Train / Val Split (%80 Train, %20 Val)
train_size = int(0.8 * len(full_dataset))
val_size = len(full_dataset) - train_size
train_dataset, val_dataset = random_split(full_dataset, [train_size, val_size], generator=torch.Generator().manual_seed(42))

# Transformları uygulama (PyTorch Subset üzerinde transformları override edemediğimiz için wrapper)
class DatasetWrapper(torch.utils.data.Dataset):
    def __init__(self, subset, transform):
        self.subset = subset
        self.transform = transform
        
    def __getitem__(self, index):
        x, y = self.subset[index]
        # ImageFolder already loads PIL Images
        return self.transform(x), y
        
    def __len__(self):
        return len(self.subset)

# Veriyi geri wrapper ile yükleyelim
# Wait, subset returns (image, label) where image is already transformed by the generic full_dataset Transform.
# To do this correctly, we recreate ImageFolder un-transformed mapping.
dataset_raw = datasets.ImageFolder(data_dir)
train_subset, val_subset = random_split(dataset_raw, [train_size, val_size], generator=torch.Generator().manual_seed(42))

train_dataset = DatasetWrapper(train_subset, train_transforms)
val_dataset = DatasetWrapper(val_subset, val_transforms)

train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, pin_memory=True)
val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, pin_memory=True)

# 2. Model Kurulumu
print("MobileNetV2 Yükleniyor...")
model = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)

# Linear katmanı (Classification) 4 sınıflı yapıyoruz (Angry, Fear, Happy, Sad)
# MobileNetV2 son katmanı: model.classifier = Sequential(Dropout, Linear)
in_features = model.classifier[1].in_features
model.classifier[1] = nn.Linear(in_features, num_classes)
model = model.to(device)

criterion = nn.CrossEntropyLoss(weight=class_weights_tensor)
optimizer = optim.Adam(model.parameters(), lr=learning_rate, weight_decay=1e-4) # L2 Regularization eklendi
scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', patience=2, factor=0.5)

# 3. Eğitim Döngüsü
best_val_loss = float('inf')
patience_counter = 0
early_stop_patience = 5

for epoch in range(num_epochs):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    
    for i, (images, labels) in enumerate(train_loader):
        images, labels = images.to(device), labels.to(device)
        
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        
        loss.backward()
        optimizer.step()
        
        running_loss += loss.item()
        _, predicted = torch.max(outputs.data, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()
        
    train_acc = 100 * correct / total
    
    # Validasyon
    model.eval()
    val_loss = 0.0
    val_correct = 0
    val_total = 0
    
    with torch.no_grad():
        for images, labels in val_loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)
            
            val_loss += loss.item()
            _, predicted = torch.max(outputs.data, 1)
            val_total += labels.size(0)
            val_correct += (predicted == labels).sum().item()
            
    val_acc = 100 * val_correct / val_total
    avg_val_loss = val_loss / len(val_loader)
    
    print(f"Epoch [{epoch+1}/{num_epochs}] - Train Loss: {running_loss/len(train_loader):.4f}, Train Acc: {train_acc:.2f}% | Val Loss: {avg_val_loss:.4f}, Val Acc: {val_acc:.2f}%")
    
    scheduler.step(avg_val_loss)
    
    # Early Stopping ve Model Kaydetme
    if avg_val_loss < best_val_loss:
        best_val_loss = avg_val_loss
        patience_counter = 0
        torch.save(model.state_dict(), 'finetuned_cnn.pth')
        print("  --> En iyi model kaydedildi (finetuned_cnn.pth)")
    else:
        patience_counter += 1
        if patience_counter >= early_stop_patience:
            print("Erken Durdurma (Early Stopping) tetiklendi!")
            break

print("Eğitim Tamamlandı. En iyi ağırlıklar finetuned_cnn.pth olarak kaydedildi.")
