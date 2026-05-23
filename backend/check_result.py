
import numpy as np
import torch
import torch.nn as nn
from ultralytics import YOLO
from torchvision import models, transforms
from PIL import Image
from pathlib import Path

# Config
classes = ["Angry", "Fear", "Happy", "Sad"]
feature_file = "fusion_features.npy"
model_path = "fusion_mlp_model.pth"
stats_path = "fusion_stats.json"
img_size = (224, 224)

# Model Definition
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

def get_best_yolo_model():
    return "yolov8n.pt" # Simplified for check

def extract_yolo_features(model, img_path):
    results = model.predict(img_path, verbose=False, conf=0.25)
    r = results[0]
    person_boxes = []
    for box in r.boxes:
        cls_id = int(box.cls[0])
        if model.names[cls_id] == "person":
            person_boxes.append(box)
    
    person_count = len(person_boxes)
    has_person = 1 if person_count > 0 else 0
    
    if has_person:
        confs = [float(box.conf[0]) for box in person_boxes]
        areas = [float(box.xywhn[0][2] * box.xywhn[0][3]) for box in person_boxes]
        centers_x = [float(box.xywhn[0][0]) for box in person_boxes]
        centers_y = [float(box.xywhn[0][1]) for box in person_boxes]
        max_conf = max(confs)
        max_area = max(areas)
        mean_area = sum(areas) / person_count
        max_area_idx = areas.index(max_area)
        main_center_x = centers_x[max_area_idx]
        main_center_y = centers_y[max_area_idx]
    else:
        max_conf, max_area, mean_area, main_center_x, main_center_y = 0.0, 0.0, 0.0, 0.5, 0.5
        
    return np.array([person_count, max_conf, max_area, mean_area, main_center_x, main_center_y, has_person], dtype=np.float32)

def main():
    import json
    import sys
    
    img_path = sys.argv[1]
    
    # Load Stats
    with open(stats_path, "r") as f:
        stats = json.load(f)
    mean = np.array(stats["mean"])
    std = np.array(stats["std"])
    
    # Models
    device = torch.device("cpu")
    yolo = YOLO(get_best_yolo_model())
    cnn = models.mobilenet_v2(weights=models.MobileNet_V2_Weights.IMAGENET1K_V1)
    cnn.classifier = nn.Identity()
    cnn.eval()
    
    # Extract
    yolo_feat = extract_yolo_features(yolo, img_path)
    
    transform = transforms.Compose([
        transforms.Resize(img_size),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    img = Image.open(img_path).convert('RGB')
    img_t = transform(img).unsqueeze(0)
    with torch.no_grad():
        cnn_feat = cnn(img_t).numpy().flatten()
        
    combined = np.concatenate([cnn_feat, yolo_feat])
    normalized = (combined - mean) / std
    
    # Predict
    # Need to load model architecture properly.
    # We need to know input_dim.
    input_dim = len(normalized)
    model = FusionMLP(input_dim, 4)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()
    
    with torch.no_grad():
        out = model(torch.from_numpy(normalized).float().unsqueeze(0))
        probs = torch.softmax(out, 1)
        conf, pred = torch.max(probs, 1)
        
    result = classes[pred.item()]
    print(f"RESULT:{result}")
    with open("result.txt", "w") as f:
        f.write(result)

if __name__ == "__main__":
    main()
