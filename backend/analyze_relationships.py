import numpy as np
from ultralytics import YOLO
from pathlib import Path
import math

def get_best_yolo_model():
    """Mevcut en iyi YOLO modelini bulur."""
    runs_dir = Path("runs/detect")
    if not runs_dir.exists():
        return "yolov8n.pt"
        
    def get_run_number(p):
        name = p.name
        suffix = name.replace("yolo_person_model", "")
        return int(suffix) if suffix.isdigit() else 0

    candidates = sorted(list(runs_dir.glob("yolo_person_model*")), key=get_run_number, reverse=True)
    if candidates:
        weights_path = candidates[0] / "weights" / "best.pt"
        if weights_path.exists():
            return str(weights_path)
    return "yolov8n.pt"

class RelationshipAnalyzer:
    def __init__(self, model_path=None, model=None):
        if model is not None:
            self.model = model
        else:
            if model_path is None:
                model_path = get_best_yolo_model()
            print(f"Model yükleniyor: {model_path}")
            self.model = YOLO(model_path)

    def analyze_image(self, image_path):
        """Resimdeki figürler arası ilişkileri KFD boyutlarına göre analiz eder."""
        # False positive engellemek için confidence artırıldı (0.25 -> 0.45)
        results = self.model.predict(image_path, conf=0.45, verbose=False)
        r = results[0]
        
        persons = []
        for box in r.boxes:
            cls_id = int(box.cls[0])
            if self.model.names[cls_id] == "person":
                x, y, w, h = box.xywhn[0].tolist()
                conf = float(box.conf[0])
                persons.append({
                    "id": len(persons),
                    "center": (x, y),
                    "size": (w, h),
                    "area": w * h,
                    "confidence": conf,
                    "box_raw": box.xyxy[0].tolist()
                })
        
        # Filtreleme: İç içe geçmiş veya çok örtüşen kutuları temizle
        persons = self._filter_overlapping_boxes(persons)
        
        # Filtreleme: Güneş, Lamba vb. Köşe Nesnelerini Temizle (Heuristic)
        persons = self._filter_sun_and_artifacts(persons)
        
        # Figürleri Soldan Sağa Sırala (Okunabilir Mantıklı ID'ler için)
        persons = sorted(persons, key=lambda p: p["center"][0])
        
        # ID'leri yeniden düzenle
        for i, p in enumerate(persons):
            p["id"] = i

        if len(persons) < 1:
            return {"error": "Resimde hiç kişi bulunamadı."}
        
        # KFD Literatürüne Göre Gruplandırma
        style_analysis = self._analyze_style_dimensions(persons)
        movement_analysis = self._analyze_movement_dimensions(persons)
        
        # Hayvan Tespiti (Ekstra Bağlam)
        animals = self.detect_animals(image_path)

        analysis_report = {
            "person_count": len(persons),
            "style_dimensions": style_analysis,
            "movement_dimensions": movement_analysis,
            "animals": animals,
            "details": persons
        }
        
        return analysis_report

    def detect_animals(self, image_path):
        """Standard YOLO modeli ile hayvanları tespit eder (Kedi, Köpek vb.)."""
        try:
            results = self.model.predict(image_path, verbose=False, conf=0.3)
            
            detected = []
            animal_classes = ["cat", "dog", "bird", "horse", "sheep", "cow", "bear"]
            tr_names = {
                "cat": "Kedi", "dog": "Köpek", "bird": "Kuş", 
                "horse": "At", "sheep": "Koyun", "cow": "İnek", "bear": "Ayı"
            }
            
            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                name = self.model.names[cls_id]
                
                if name in animal_classes:
                    detected.append({
                        "type": tr_names.get(name, name),
                        "confidence": float(box.conf[0])
                    })
            return detected
            
        except Exception as e:
            print(f"Hayvan tespiti hatası: {e}")
            return []

    def _filter_sun_and_artifacts(self, persons):
        """
        Sol/Sağ üst köşedeki ve küçük boyutlu 'Person' tespitlerini (Güneş vb.) eler.
        """
        filtered = []
        for p in persons:
            x, y = p["center"]
            w, h = p["size"]
            area = p["area"]
            
            # Kriterler:
            # 1. Y konumu: Üst %20'lik dilimde (y < 0.20)
            # 2. X konumu: Sol veya Sağ kenara yakın (x < 0.20 veya x > 0.80)
            # 3. Boyut: Nispeten küçük (area < 0.10) - Ana figürler genellikle daha büyüktür.
            
            is_top_corner = (y < 0.20) and (x < 0.20 or x > 0.80)
            is_small = (area < 0.10)
            
            if is_top_corner and is_small:
                print(f"DEBUG: Filtrelenen Nesne (Güneş/Artifact Şüphesi): Konum=({x:.2f}, {y:.2f}), Alan={area:.2f}")
                continue # Listeye ekleme
            
            filtered.append(p)
            
        return filtered
        
    def _filter_overlapping_boxes(self, persons, iou_threshold=0.5):
        """Yüksek oranda örtüşen kutulardan düşük güvenli olanı eler."""
        if not persons: return []
        
        keep = [True] * len(persons)
        for i in range(len(persons)):
            if not keep[i]: continue
            for j in range(i + 1, len(persons)):
                if not keep[j]: continue
                
                box1 = persons[i]["box_raw"]
                box2 = persons[j]["box_raw"]
                
                # Intersection
                x1 = max(box1[0], box2[0])
                y1 = max(box1[1], box2[1])
                x2 = min(box1[2], box2[2])
                y2 = min(box1[3], box2[3])
                
                inter_area = max(0, x2 - x1) * max(0, y2 - y1)
                
                if inter_area > 0:
                    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
                    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
                    union_area = area1 + area2 - inter_area
                    
                    iou = inter_area / union_area
                    # Kapsama oranı (küçük olanın ne kadarı büyük olanın içinde)
                    overlap1 = inter_area / area1
                    overlap2 = inter_area / area2
                    
                    # Debug
                    # print(f"Compare {i} vs {j}: IoU={iou:.2f}, Over1={overlap1:.2f}, Over2={overlap2:.2f}")

                    # Eğer IoU yüksekse VEYA biri diğerinin içine %80'den fazla girmişse
                    if iou > iou_threshold or overlap1 > 0.8 or overlap2 > 0.8:
                        # Düşük güvenli olanı sil
                        if persons[i]["confidence"] < persons[j]["confidence"]:
                            keep[i] = False
                            print(f"DEBUG: Removed ID {persons[i]['id']} (Conf {persons[i]['confidence']:.2f}) due to overlap with ID {persons[j]['id']}")
                            break
                        else:
                            keep[j] = False
                            print(f"DEBUG: Removed ID {persons[j]['id']} (Conf {persons[j]['confidence']:.2f}) due to overlap with ID {persons[i]['id']}")
                            
        return [p for k, p in zip(keep, persons) if k]

    def _analyze_style_dimensions(self, persons):
        """
        STİL BOYUTLARI (Style Dimensions):
        - Figürlerin düzenlenmesi, boyutları, kağıt üzerindeki yerleşimi.
        """
        # 1. Yerleşim (Placement)
        centers_x = [p["center"][0] for p in persons]
        avg_x = sum(centers_x) / len(centers_x)
        centers_y = [p["center"][1] for p in persons]
        avg_y = sum(centers_y) / len(centers_y)
        
        placement = []
        if avg_x < 0.4: placement.append("Sola Yatkın (Geçmiş Odaklılık): Koppitz'e göre figürlerin sola yerleştirilmesi, çocuğun geçmişe bağlılığını, içe dönüklüğünü veya potansiyel bir güvensizlik duygusunu işaret edebilir.")
        elif avg_x > 0.6: placement.append("Sağa Yatkın (Gelecek Odaklılık): Koppitz literatüründe sağa eğilim, dışa dönüklük, çevreyle etkileşime girme arzusu veya geleceğe dönük aktif bir tutum olarak yorumlanır.")
        else: placement.append("Merkezi Yerleşim (Denge): Merkezde yer alan figürler, kendini yönlendirebilen, gerçeklik algısı güçlü ve uyumlu bir bireysellik profilini yansıtır (Koppitz).")
        
        # Dikey (Yükseltilmiş Figürler - Style Dimension)
        if avg_y < 0.35: placement.append("Üst Kısım (İyimserlik/Hayal Dünyası): Burns ve Kaufman'a göre yüksek yerleşim, çocuğun yüksek hedefleri olduğunu, iyimserliğini veya bazen gerçeklikten kaçıp hayal dünyasına sığındığını gösterebilir.")
        elif avg_y > 0.65: placement.append("Alt Kısım (Güven Arayışı/Depresif Eğilim): Alt kenara yakınlık, sağlam bir zemin arayışını, güvensizliği veya depresif/somut düşünce kalıplarını simgeleyebilir (Burns).")
        else: placement.append("Dikey Merkez: Gündelik gerçeklikle bağlantının kopmadığı, dengeli bir duygusal zemin.")
        
        # 2. Hiyerarşi / Göreli Boyut (Size/Hierarchy)
        sorted_by_size = sorted(persons, key=lambda p: p["area"], reverse=True)
        largest = sorted_by_size[0]
        smallest = sorted_by_size[-1]
        
        size_ratio = largest["area"] / (smallest["area"] + 1e-6)
        hierarchy_note = "Normal Boyut Dağılımı: Aile içi güç dağılımı olağan ve eşit görünüyor."
        if size_ratio > 2.5:
            hierarchy_note = "Belirgin Boyut Farkı (Hiyerarşi): En büyük figür güçlü bir otorite/baskı kaynağı olarak algılanırken, en küçük figür kendini değersizleştirilmiş veya ezilmiş hissediyor olabilir (Machover/Koppitz)."
        elif size_ratio > 1.5:
             hierarchy_note = "Orta Düzey Boyut Farkı: Aile içinde güç dengesizlikleri veya belirli bir üyeye atfedilen belirgin bir önem göze çarpıyor."
            
        return {
            "placement": ", ".join(placement),
            "hierarchy": hierarchy_note,
            "details": f"En büyük figür ID: {largest['id']}, En küçük figür ID: {smallest['id']} (Oran: {size_ratio:.2f})"
        }

    def _analyze_movement_dimensions(self, persons):
        """
        HAREKET BOYUTLARI (Movement Dimensions):
        - Etkileşim, yakınlık, bariyerler.
        """
        interactions = []
        for i, p1 in enumerate(persons):
            for j, p2 in enumerate(persons):
                if i >= j: continue 
                
                # Sadece yan yana olan komşuları analiz et (hata azaltır)
                if j != i + 1: continue
                
                c1 = p1["center"]
                c2 = p2["center"]
                dist = math.sqrt((c1[0]-c2[0])**2 + (c1[1]-c2[1])**2)
                
                # Mesafe Yorumu (Movement analizi için kritik)
                if dist < 0.15:
                    interp = "Aşırı Yakın/Temas Halinde: Güçlü bir duygusal bağ, bağımlılık veya iç içe geçmiş sınır problemleri."
                elif dist < 0.35:
                     interp = "Sağlıklı Etkileşim Mesafesi: Normal, erişilebilir ve etkileşime açık (KFD)."
                elif dist > 0.60:
                    interp = "Duygusal ve Fiziksel Kopukluk (İzolasyon): İletişim eksikliğini, bastırılmış çatışmaları veya izolasyon hissini temsil edebilir."
                else:
                    interp = "Nötr Mesafe: Standart bir boşluk, belirgin bir çekim ya da itilim yok."
                    
                interactions.append({
                    "pair": (p1["id"], p2["id"]),
                    "distance": dist,
                    "comment": interp,
                    "citation": "Burns & Kaufman (1970) - Hareket/Mesafe Boyutu"
                })
        return interactions

    # Eski metodların yerine yukarıdakiler geçtiği için helper metodları kaldırabiliriz veya tutabiliriz.
    # Temizlik açısından eskileri siliyorum.

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("image", nargs="?", help="Analiz edilecek resim yolu")
    args = parser.parse_args()

    # Varsayılan veya argüman
    test_img = args.image if args.image else "C:/Users/ranas/.gemini/antigravity/brain/30793933-0e42-4ebd-b9b9-d1b65014cdd5/uploaded_image_1770101543283.png"

    analyzer = RelationshipAnalyzer()
    
    if Path(test_img).exists():
        print(f"Analiz ediliyor: {test_img}")
        report = analyzer.analyze_image(test_img)
        
        import json
        output_path = "relationship_report.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"Rapor kaydedildi: {output_path}")
        
        # Konsola Detaylı Rapor Bas (KFD Formatı)
        print("\n" + "="*50)
        print(f"KİNETİK AİLE ÇİZİM ANALİZİ (KFD)")
        print("-" * 30)
        print(f"Tespit Edilen Kişi Sayısı: {report.get('person_count')}")
        
        style = report.get('style_dimensions', {})
        print(f"\n[1] STİL BOYUTLARI (Style Dimensions):")
        print(f"  * Yerleşim: {style.get('placement')}")
        print(f"  * Hiyerarşi: {style.get('hierarchy')}")
        print(f"  * Detay: {style.get('details')}")
        
        movement = report.get('movement_dimensions', [])
        print(f"\n[2] HAREKET BOYUTLARI (Movement/Interaction):")
        if movement:
            for interaction in movement:
                p1, p2 = interaction['pair']
                comm = interaction['comment']
                dist = interaction['distance']
                print(f"  * Figür {p1} <-> Figür {p2}:")
                print(f"    - Durum: {comm}")
                print(f"    - Mesafe: {dist:.2f}")
        else:
            print("  Tek kişilik çizim - Kişilerarası hareket analizi yapılamaz.")
            
        print("="*50 + "\n")
    else:
        print("Test resmi bulunamadı.")
