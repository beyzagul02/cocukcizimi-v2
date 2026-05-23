
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import StratifiedKFold
from sklearn.utils.class_weight import compute_class_weight
from sklearn.decomposition import PCA
from sklearn.metrics import confusion_matrix, classification_report
import seaborn as sns
import matplotlib.pyplot as plt
import json
import os

# --- AYARLAR ---
feature_file = "fusion_features.npy"
label_file = "fusion_labels.npy"
classes = ["Angry", "Fear", "Happy", "Sad"]

# MLP Modeli Tanımı (Eğitimdeki ile AYNI olmalı)
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

def evaluate_model():
    print("Veri yükleniyor...")
    if not (os.path.exists(feature_file) and os.path.exists(label_file)):
        print("HATA: Özellik dosyaları bulunamadı.")
        return

    X = np.load(feature_file).astype(np.float32)
    y = np.load(label_file).astype(np.int64)
    
    # Stratified K-Fold Cross Validation
    k_folds = 5
    skf = StratifiedKFold(n_splits=k_folds, shuffle=True, random_state=42)
    
    fold_accuracies = []
    all_preds = []
    all_labels = []
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Başlatılıyor: {k_folds}-Fold Cross Validation (Cihaz: {device})")
    
    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        print(f"Fold {fold+1}/{k_folds}...")
        
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]
        
        # Scaling
        mean = X_train.mean(axis=0)
        std = X_train.std(axis=0) + 1e-8
        X_train = (X_train - mean) / std
        X_val = (X_val - mean) / std
        
        # PCA Transform
        pca = PCA(n_components=128, random_state=42)
        X_train = pca.fit_transform(X_train)
        X_val = pca.transform(X_val)
        
        # Tensor
        train_dataset = TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train))
        val_dataset = TensorDataset(torch.from_numpy(X_val), torch.from_numpy(y_val))
        
        train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=32)
        
        # Model Init
        input_dim = X_train.shape[1]
        model = FusionMLP(input_dim, len(classes)).to(device)
        
        class_w = compute_class_weight('balanced', classes=np.unique(y_train), y=y_train)
        class_w_tensor = torch.tensor(class_w, dtype=torch.float32).to(device)
        
        criterion = nn.CrossEntropyLoss(weight=class_w_tensor)
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=0.5, patience=5)
        
        # Training Loop
        epochs = 60
        best_fold_acc = 0.0
        best_model_state = None
        patience = 15
        patience_counter = 0

        for epoch in range(epochs):
            model.train()
            for inputs, labels in train_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                optimizer.zero_grad()
                outputs = model(inputs)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()
                
            model.eval()
            corr = 0
            tot = 0
            with torch.no_grad():
                for inputs, labels in val_loader:
                    inputs, labels = inputs.to(device), labels.to(device)
                    out = model(inputs)
                    _, pred = torch.max(out.data, 1)
                    tot += labels.size(0)
                    corr += (pred == labels).sum().item()
            v_acc = 100 * corr / tot
            scheduler.step(v_acc)
            
            if v_acc > best_fold_acc:
                best_fold_acc = v_acc
                best_model_state = model.state_dict().copy()
                patience_counter = 0
            else:
                patience_counter += 1
                
            if patience_counter >= patience:
                break
                
        # En iyi modeli yükle
        if best_model_state is not None:
             model.load_state_dict(best_model_state)
        
        # Validation
        model.eval()
        fold_preds = []
        fold_labels = []
        correct = 0
        total = 0
        
        with torch.no_grad():
            for inputs, labels in val_loader:
                inputs, labels = inputs.to(device), labels.to(device)
                outputs = model(inputs)
                _, predicted = torch.max(outputs.data, 1)
                
                total += labels.size(0)
                correct += (predicted == labels).sum().item()
                
                fold_preds.extend(predicted.cpu().numpy())
                fold_labels.extend(labels.cpu().numpy())
                
        acc = 100 * correct / total
        fold_accuracies.append(acc)
        
        # Store for global confusion matrix
        all_preds.extend(fold_preds)
        all_labels.extend(fold_labels)
        
    # Results
    print("\n" + "="*40)
    print(f"ORTALAMA DOĞRULUK: %{np.mean(fold_accuracies):.2f} (+/- %{np.std(fold_accuracies):.2f})")
    print("="*40)
    
    print("\nSINIFLANDIRMA RAPORU:")
    print(classification_report(all_labels, all_preds, target_names=classes))
    
    print("\nKARMAŞIKLIK MATRİSİ (Confusion Matrix):")
    cm = confusion_matrix(all_labels, all_preds)
    print(cm)
    
    # Save Matrix Plot (Optional ascii representation above is enough for terminal, but let's be fancy nicely)
    # Actually just text is safer for now.
    
if __name__ == "__main__":
    evaluate_model()
