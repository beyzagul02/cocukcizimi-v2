import cv2
import glob
import os
import math
import numpy as np

# Dataset paths
BASE_DIR = r"c:\Users\ranas\OneDrive\Masaüstü\CocukDuyguProje\child-drawing-person.v3i.yolov8\train"
IMG_DIR = os.path.join(BASE_DIR, "images")
LABEL_DIR = os.path.join(BASE_DIR, "labels")

def read_image(path, flags=cv2.IMREAD_COLOR):
    """Reads image with unicode path support."""
    try:
        # buf = np.fromfile(path, dtype=np.uint8) # numpy fromfile also has issues sometimes but usually better? 
        # Actually standard python open used by np.fromfile is fine.
        with open(path, "rb") as f:
            bytes_data = f.read()
        buf = np.frombuffer(bytes_data, np.uint8)
        return cv2.imdecode(buf, flags)
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return None

def get_yolo_fill_ratio(label_path):
    """Calculates the sum of areas of all YOLO bounding boxes (normalized)."""
    if not os.path.exists(label_path):
        return 0.0
    
    total_area = 0.0
    with open(label_path, 'r') as f:
        lines = f.readlines()
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 5:
                # YOLO format: class x_center y_center width height
                w = float(parts[3])
                h = float(parts[4])
                total_area += w * h
                
    # Cap at 1.0 just in case of overlaps summing > 100% (though technically sum of areas can be > 1 if overlaps exist, 
    # but for "paper coverage" concept, let's keep it raw sum or maybe cap. Raw sum represents "total object magnitude".
    # Let's return raw sum, user can interpret.
    return total_area

def get_object_distances(label_path, img_width, img_height):
    """Calculates distances between centers of all objects in the label file."""
    if not os.path.exists(label_path):
        return []

    centers = []
    with open(label_path, 'r') as f:
        lines = f.readlines()
        for line in lines:
            parts = line.strip().split()
            if len(parts) >= 5:
                # YOLO format: class x_center y_center width height (normalized)
                x_c = float(parts[1]) * img_width
                y_c = float(parts[2]) * img_height
                centers.append((x_c, y_c))
    
    distances = []
    if len(centers) < 2:
        return distances # No pairs to measure
    
    for i in range(len(centers)):
        for j in range(i + 1, len(centers)):
            p1 = centers[i]
            p2 = centers[j]
            dist = math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
            distances.append(dist)
            
    return distances

def main():
    image_files = glob.glob(os.path.join(IMG_DIR, "*.jpg")) + glob.glob(os.path.join(IMG_DIR, "*.png"))
    output_path = "analysis_results_utf8.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        msg = f"Found {len(image_files)} images in {IMG_DIR}\n"
        print(msg)
        f.write(msg)
        
        header = f"{'Image Name':<30} | {'YOLO Box Area (%)':<20} | {'Avg Distance (px)':<20} | {'Num Objects':<10}\n"
        print(header)
        f.write(header)
        f.write("-" * 85 + "\n")
        
        count = 0
        for img_path in image_files:
            if count >= 20: break 
            
            filename = os.path.basename(img_path)
            label_filename = os.path.splitext(filename)[0] + ".txt"
            label_path = os.path.join(LABEL_DIR, label_filename)
            
            # 1. Fill Ratio (YOLO Area)
            ratio = get_yolo_fill_ratio(label_path)
            percent = ratio * 100
            
            # 2. Distances
            img = read_image(img_path)
            if img is None: 
                f.write(f"Failed to read {filename}\n")
                continue
            h, w = img.shape[:2]
            
            dists = get_object_distances(label_path, w, h)
            avg_dist = sum(dists) / len(dists) if dists else 0
            
            dist_str = f"{avg_dist:.1f}" if dists else "N/A"
            
            # Count objects reliably for display
            num_real_objects = 0
            if os.path.exists(label_path):
                 with open(label_path, 'r') as lf: 
                    num_real_objects = len(lf.readlines())

            line = f"{filename[:28]:<30} | {percent:<20.2f} | {dist_str:<20} | {num_real_objects:<10}\n"
            print(line, end='')
            f.write(line)
            count += 1

if __name__ == "__main__":
    main()
