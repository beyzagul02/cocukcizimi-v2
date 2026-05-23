import os
import json
import predict_fusion
import numpy as np
from pathlib import Path

# Representative images selected for analysis
IMAGES_TO_ANALYZE = {
    "Angry": r"c:\Users\ranas\OneDrive\Masaüstü\CocukDuyguProje\dataset_all\Angry\a1.jpg",
    "Fear": r"c:\Users\ranas\OneDrive\Masaüstü\CocukDuyguProje\dataset_all\Fear\f1.jpg",
    "Happy": r"c:\Users\ranas\OneDrive\Masaüstü\CocukDuyguProje\dataset_all\Happy\h1.jpg",
    "Sad": r"c:\Users\ranas\OneDrive\Masaüstü\CocukDuyguProje\dataset_all\Sad\s1.jpg"
}

def run_batch_analysis():
    results = {}
    
    for category, img_path in IMAGES_TO_ANALYZE.items():
        if not os.path.exists(img_path):
            print(f"Warning: {img_path} not found.")
            continue
            
        print(f"Analyzing {category} image: {img_path}...")
        try:
            res = predict_fusion.predict(img_path)
            if res:
                results[category] = res
        except Exception as e:
            print(f"Error analyzing {category}: {e}")
            
    # Custom JSON encoder to handle NumPy types
    class MyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            if isinstance(obj, np.float32) or isinstance(obj, np.float64):
                return float(obj)
            if isinstance(obj, np.int64) or isinstance(obj, np.int32):
                return int(obj)
            return super(MyEncoder, self).default(obj)

    # Save results to a JSON file for report generation
    output_path = "batch_analysis_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, cls=MyEncoder)
        
    print(f"Batch analysis complete. Results saved to {output_path}")

if __name__ == "__main__":
    run_batch_analysis()
