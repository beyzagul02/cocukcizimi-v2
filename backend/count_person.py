from ultralytics import YOLO
import cv2
import os

model = YOLO("yolov8n.pt")

happy_path = "dataset_all/Happy"

for img_name in os.listdir(happy_path):
    img_path = os.path.join(happy_path, img_name)

    img = cv2.imread(img_path)
    if img is None:
        continue

    results = model(img)

    person_count = 0
    for r in results:
        for box in r.boxes:
            cls = int(box.cls[0])
            if model.names[cls] == "person":
                person_count += 1

    print(f"{img_name} → Figür sayısı: {person_count}")
