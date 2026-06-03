import os
import tempfile
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageOps  # 👈 PIL kütüphanelerini ekledik
import predict_fusion

app = Flask(__name__)
CORS(app)

def make_serializable(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, np.generic):
        return obj.item()
    elif isinstance(obj, dict):
        return {k: make_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_serializable(v) for v in obj]
    elif isinstance(obj, tuple):
        return tuple(make_serializable(v) for v in obj)
    return obj

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "message": "Child Drawing Analysis API is running"}), 200

@app.route('/analyze', methods=['POST'])
def analyze_image():
    if 'image' not in request.files:
        return jsonify({"error": "Resim dosyası yüklenmedi."}), 400
        
    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "Dosya adı boş."}), 400
        
    try:
        # 1. Resmi açıyoruz ve EXIF (yön) bilgisini düzeltiyoruz 👈
        image = Image.open(file.stream)
        image = ImageOps.exif_transpose(image)
        
        # 2. Geçici bir dosya yolu oluşturuyoruz 👈
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            
        # 3. Yönü düzeltilmiş resmi geçici dosyaya kaydediyoruz 👈
        image.save(tmp_path)
        
        print(f"Resim yönü düzeltilerek geçici dosyaya kaydedildi: {tmp_path}")
        
        # Run prediction
        result = predict_fusion.predict(tmp_path)
        
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
            
        if result is None:
            return jsonify({"error": "Analiz sırasında bilinmeyen bir hata oluştu."}), 500
            
        # Serialize numpy types
        serializable_result = make_serializable(result)
        return jsonify(serializable_result)
        
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"Sunucu hatası:\n{tb}")
        return jsonify({"error": str(e), "traceback": tb}), 500

if __name__ == '__main__':
    # Run Flask server
    app.run(host='0.0.0.0', port=5000, debug=True)