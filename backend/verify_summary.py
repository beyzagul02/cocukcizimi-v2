
import predict_fusion
import sys

img_path = r"C:\Users\ranas\.gemini\antigravity\brain\30793933-0e42-4ebd-b9b9-d1b65014cdd5\uploaded_image_1770101543283.png"
try:
    res = predict_fusion.predict(img_path)
    print("--- SUMMARY START ---")
    print(res["psychological_summary"])
    print("--- SUMMARY END ---")
except Exception as e:
    print(f"Error: {e}")
