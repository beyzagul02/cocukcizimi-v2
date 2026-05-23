import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.utils.class_weight import compute_class_weight
from sklearn.decomposition import PCA
import pickle
import json
import os

# --- AYARLAR ---
feature_file = "fusion_features.npy"
label_file = "fusion_labels.npy"
model_out = "fusion_mlp_model.pth"
stats_out = "fusion_stats.json"

classes = ["Angry", "Fear", "Happy", "Sad"]

# MLP Modeli Tanımı
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

def train_fusion():
    print("Veri yükleniyor...")
    if not (os.path.exists(feature_file) and os.path.exists(label_file)):
        print("HATA: Özellik dosyaları bulunamadı.")
        return

    X = np.load(feature_file).astype(np.float32)
    y = np.load(label_file).astype(np.int64)
    
    print(f"Veri boyutu: {X.shape}, Etiket boyutu: {y.shape}")
    
    # Validation split (Manual)
    indices = np.arange(len(X))
    np.random.shuffle(indices)
    split = int(0.8 * len(X))
    train_idx, val_idx = indices[:split], indices[split:]
    
    X_train, X_val = X[train_idx], X[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]
    
    # Scaling (Standardization: (x - mean) / std)
    mean = X_train.mean(axis=0)
    std = X_train.std(axis=0) + 1e-8 # avoid division by zero
    
    X_train = (X_train - mean) / std
    X_val = (X_val - mean) / std
    
    # Save stats for inference
    stats = {"mean": mean.tolist(), "std": std.tolist()}
    with open(stats_out, "w") as f:
        json.dump(stats, f)
        
    print(f"PCA uygulanıyor... (Orjinal Boyut: {X_train.shape[1]})")
    # PCA ile boyut küçültme (Overfitting'i önlemek için 128 boyuta iniyoruz)
    pca = PCA(n_components=128, random_state=42)
    X_train = pca.fit_transform(X_train)
    X_val = pca.transform(X_val)
    
    print(f"PCA tamamlandı. Yeni Boyut: {X_train.shape[1]}, Varyans Korunma Oranı: %{sum(pca.explained_variance_ratio_)*100:.2f}")
    
    # PCA modelini çıkarım (inference) için kaydet
    pca_out = "pca_model.pkl"
    with open(pca_out, "wb") as f:
        pickle.dump(pca, f)
    print(f"PCA modeli kaydedildi: {pca_out}")
    
    # Convert to Tensor
    train_dataset = TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train))
    val_dataset = TensorDataset(torch.from_numpy(X_val), torch.from_numpy(y_val))
    
    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=32)
    
    # Sınıf dengesizlikleri için Class Weights hesaplama
    class_weights = compute_class_weight(
        class_weight='balanced',
        classes=np.unique(y_train),
        y=y_train
    )
    
    # Numpy array'i Tensor'a çevir
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    class_weights_tensor = torch.tensor(class_weights, dtype=torch.float32).to(device)
    
    # Model Init (Artık input_dim = 128)
    input_dim = X_train.shape[1]
    model = FusionMLP(input_dim, len(classes)).to(device)
    
    criterion = nn.CrossEntropyLoss(weight=class_weights_tensor)
    optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4) # L2 regularization eklendi
    
    # Dinamik Learning Rate düzenleyici
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=5)
    
    print(f"Eğitim başliyor (Cihaz: {device})... Sınıf Ağırlıkları uygulandı.")
    
    best_acc = 0.0
    epochs = 150 # Early stopping olduğu için artırıldı
    patience = 20
    patience_counter = 0
    
    for epoch in range(epochs):
        model.train()
        running_loss = 0.0
        for inputs, labels in train_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item()
            
        # Validation
        model.eval()
        correct = 0
        total = 0
        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                _, predicted = torch.max(outputs.data, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
        
        val_acc = 100 * correct / total
        
        # LR Scheuler adımını validation accuracy'e göre at
        if isinstance(scheduler, optim.lr_scheduler.ReduceLROnPlateau): # Uyarı vermemesi için
             scheduler.step(val_acc)
        
        if val_acc > best_acc:
            best_acc = val_acc
            torch.save(model.state_dict(), model_out)
            patience_counter = 0 # Sayacı sıfırla
        else:
            patience_counter += 1
        
        if (epoch+1) % 5 == 0:
            current_lr = optimizer.param_groups[0]['lr']
            print(f"Epoch {epoch+1}/{epochs}, Loss: {running_loss/len(train_loader):.4f}, Val Acc: %{val_acc:.2f}, LR: {current_lr:.6f}")
            
        if patience_counter >= patience:
            print(f"\n[Early Stopping] Model {patience} epoch boyunca gelişmedi. Eğitim {epoch+1}. epoch'ta durduruldu.")
            break

    print(f"\nEğitim tamamlandı! En iyi Validation Accuracy: %{best_acc:.2f}")
    print(f"Model kaydedildi: {model_out}")
    print(f"İstatistikler kaydedildi: {stats_out}")

if __name__ == "__main__":
    train_fusion()
