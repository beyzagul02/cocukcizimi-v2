import cv2
import numpy as np
from sklearn.cluster import KMeans
from collections import Counter

class ColorAnalyzer:
    def __init__(self):
        # Renk Etiketleri ve Psikolojik Anlamları (Alschuler & Hattwick)
        self.color_meanings = {
            "Kırmızı": "Yüksek Enerji, İrtibatsizlik veya Öfke/Saldirganlik Eğilimi",
            "Mavi": "Sakinlik, Kontrol, Bazen İçe Dönüklük",
            "Açık Mavi": "Huzur Arayişi, Hayal Kurma, Sakinlik",
            "Yeşil": "Denge, Büyüme, Duygusal Huzur",
            "Açık Yeşil": "Umut, Büyüme, Doğayla Bağ",
            "Sarı": "Neşe, Dişa Dönüklük, Bazen Kiskançlik/Bağimlilik",
            "Siyah": "Endişe, Korku, Bastirilmiş Duygular veya Güç İsteği",
            "Kahverengi": "Topraklanma, Güven Arayişi veya Katilik",
            "Mor": "Hayal Gücü, Fantezi Dünyasi veya Gerginlik",
            "Lila": "Hassasiyet, Ruhani Arayiş, Romantizm",
            "Turuncu": "Sosyal İletişim, Arkadaş canlisi olma",
            "Pembe": "Sevgi İhtiyaci, Hassasiyet",
            "Gri": "Nötr, Belirsizlik veya İçe Kapanma"
        }

    def analyze(self, image_path, k=5):
        """
        Resimdeki baskın renkleri analiz eder.
        """
        try:
            image = cv2.imread(image_path)
            if image is None:
                return []
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Resim boyutunu küçült (İnce boya/kalem çizgilerini kaybetmemek için 400x400)
            image = cv2.resize(image, (400, 400))
            
            # Dinamik Arka Plan Rengi Tespiti (Köşelerden örneklem al)
            h, w, _ = image.shape
            corners = [
                image[0:10, 0:10],          # Sol üst
                image[0:10, w-10:w],        # Sağ üst
                image[h-10:h, 0:10],        # Sol alt
                image[h-10:h, w-10:w]       # Sağ alt
            ]
            # Köşelerin medyan rengini "Kağıt Rengi" olarak kabul et
            corner_pixels = np.vstack([c.reshape(-1, 3) for c in corners])
            paper_color = np.median(corner_pixels, axis=0)

            pixels = image.reshape(-1, 3)

            # K-Means ile renkleri grupla, cluster artırıldı ki ince renkler erimesin
            kmeans = KMeans(n_clusters=k+2, random_state=42, n_init=10)
            kmeans.fit(pixels)
            
            # Renk oranlarını hesapla
            counts = Counter(kmeans.labels_)
            total_pixels = sum(counts.values())


            dominant_colors_temp = []
            centers = kmeans.cluster_centers_
            
            for i, count in Counter(kmeans.labels_).most_common(k+2):
                color = centers[i]
                
                # Kağıt rengi (Arka plan) filtresi: 
                # Eğer renk, tespit edilen kağıt rengine çok yakınsa (Euclidean dist < 45) yoksay.
                # VEYA Saf beyaz ise yoksay.
                dist_to_paper = np.linalg.norm(color - paper_color)
                if dist_to_paper < 45 or np.mean(color) > 230:
                    continue
                    
                color_name = self._get_color_name(color)
                
                dominant_colors_temp.append({
                    "color_rgb": color,
                    "name": color_name,
                    "count": count,
                    "meaning": self.color_meanings.get(color_name, "Tanimsiz")
                })
                
            # Gerçek renkler üzerindeki (çizilen) oransal dağılım
            valid_pixels = sum(item["count"] for item in dominant_colors_temp)
            if valid_pixels == 0: valid_pixels = 1
            
            # Aynı isimdeki renkleri (örn: Açık pembe ve koyu pembe) birleştir
            aggregated_colors = {}
            for item in dominant_colors_temp:
                name = item["name"]
                if name not in aggregated_colors:
                    aggregated_colors[name] = {"color_rgb": item["color_rgb"], "count": 0, "meaning": item["meaning"]}
                aggregated_colors[name]["count"] += item["count"]
            
            dominant_colors = []
            for name, data in aggregated_colors.items():
                percent = (data["count"] / valid_pixels) * 100
                dominant_colors.append({
                    "color_rgb": data["color_rgb"],
                    "name": name,
                    "percent": percent,
                    "meaning": data["meaning"]
                })
                
            # En yüksek oranlıları öne almak için sırala
            dominant_colors = sorted(dominant_colors, key=lambda x: x["percent"], reverse=True)
                
            return dominant_colors

            

        except Exception as e:
            print(f"Renk analizi hatası: {e}")
            return []

    def _get_color_name(self, rgb):
        """
        RGB değerine en yakın temel renk ismini döndürür (Euclidean Distance).
        """
        r, g, b = rgb
        
        # 1. Öncelikli Kontroller (Siyah/Beyaz/Gri tonları)
        # Beyaz (Kağıt)
        if r > 220 and g > 220 and b > 220:
            return "Beyaz (Kağıt)"
            
        # Gri Tonları (Renk doygunluğu düşükse)
        # Standart sapma düşükse (R, G, B birbirine yakınsa) gridir.
        if np.std([r,g,b]) < 25:
            if np.mean([r,g,b]) < 90: return "Siyah" # Koyu gri/siyah
            return "Gri"

        # 2. Renk Merkezleri ile Mesafe Hesabı
        # Aynı renk için birden fazla referans noktası eklendi (Özellikle koyu tonlar)
        color_anchors = [
            ("Kırmızı", (220, 30, 30)),
            ("Kırmızı", (255, 0, 0)),
            ("Kırmızı", (255, 60, 60)),   # Açık kırmızı (ince kalem çizgisi)
            ("Kırmızı", (255, 100, 100)), # Daha açık kırmızı
            ("Kırmızı", (240, 80, 80)),   # Soluk kırmızı
            ("Kırmızı", (170, 20, 20)),   # Koyu kırmızı v1
            ("Kırmızı", (139, 0, 0)),     # Koyu kırmızı v2
            ("Kırmızı", (200, 10, 10)),   # Kırmızı varyant
            ("Yeşil", (0, 128, 0)),
            ("Yeşil", (0, 255, 0)),
            ("Yeşil", (34, 139, 34)),
            ("Açık Yeşil", (144, 238, 144)),
            ("Mavi", (0, 0, 220)),
            ("Mavi", (0, 0, 139)),        # Koyu mavi
            ("Açık Mavi", (135, 180, 230)),
            ("Açık Mavi", (135, 206, 235)),
            ("Sarı", (255, 255, 0)),
            ("Sarı", (255, 215, 0)),
            ("Turuncu", (255, 165, 0)),
            ("Turuncu", (255, 140, 0)),
            ("Mor", (100, 0, 130)),
            ("Mor", (128, 0, 128)),
            ("Lila", (180, 130, 200)),
            ("Pembe", (255, 130, 170)),
            ("Pembe", (255, 192, 203)),
            ("Pembe", (255, 105, 180)),
            ("Kahverengi", (165, 42, 42)), # Kahverengi ve koyu Kırmızı birbirine karışabiliyordu
            ("Kahverengi", (139, 69, 19)),
            ("Kahverengi", (160, 82, 45)),
            ("Siyah", (30, 30, 30)),
            ("Siyah", (0, 0, 0))
        ]
        
        min_dist = float("inf")
        closest_name = "Karmaşık"
        
        for name, centroid in color_anchors:
            dist = np.sqrt((r - centroid[0])**2 + (g - centroid[1])**2 + (b - centroid[2])**2)
            if dist < min_dist:
                min_dist = dist
                closest_name = name
                
        return closest_name

if __name__ == "__main__":
    # Test
    analyzer = ColorAnalyzer()
    print("Renk analiz modülü hazır (Reset).")
