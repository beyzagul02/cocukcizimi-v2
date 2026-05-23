
import streamlit as st
from PIL import Image
import os
import predict_fusion
import tempfile

st.set_page_config(page_title="Çocuk Resim Analizi", layout="wide")

st.title("🎨 Çocuk Resim Duygu ve İlişki Analizi")
st.markdown("""
Bu sistem, çocukların çizdiği aile resimlerini analiz ederek:
- **Duygu Durumu** (Mutlu, Üzgün, Korku, Öfkeli)
- **KFD (Kinetik Aile Çizimi) Analizi** (Yerleşim, Etkileşimler)
hakkında öngörüler sunar.
""")

# Sidebar
st.sidebar.header("Resim Yükle")
uploaded_file = st.sidebar.file_uploader("Bir resim seçin...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Save temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    # Display Image
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Yüklenen Resim")
        image = Image.open(uploaded_file)
        st.image(image, use_column_width=True)
        
    with col2:
        st.subheader("Analiz Sonuçları")
        if st.button("Analiz Et"):
            with st.spinner('Yapay zeka resmi inceliyor...'):
                try:
                    # Run Analysis
                    result = predict_fusion.predict(tmp_path)
                    
                    # 1. Main Prediction
                    st.success(f"**Tespit Edilen Duygu:** {result['prediction']}")
                    st.progress(result['confidence'] / 100)
                    st.caption(f"Güven Skoru: %{result['confidence']:.2f}")
                    
                    with st.expander("Diğer Olasılıklar"):
                        for emo, prob in result['probabilities'].items():
                            st.write(f"{emo}: %{prob:.2f}")

                    # 2. Integrated Summary (New Feature)
                    st.markdown("### 📝 Yapay Zeka Özeti")
                    st.info(result.get('psychological_summary', 'Özet oluşturulamadı.'))
                    
                    if result.get("warnings"):
                        for w in result["warnings"]:
                            st.warning(f"⚠️ {w}")

                    # 3. Key Metrics & Details
                    st.markdown("### 🔍 Detaylı Analiz")
                    
                    m1, m2 = st.columns(2)
                    m1.metric("Figür Sayısı", result['person_count'])
                    
                    # KFD Details
                    style = result.get('style', {})
                    if style:
                        st.text(f"Yerleşim: {style.get('placement', 'N/A')}")
                        st.text(f"Hiyerarşi: {style.get('hierarchy', 'N/A')}")
                    
                    movement = result.get('movement', [])
                    if movement:
                        st.write("**İlişkiler:**")
                        for m in movement:
                            pair = m['pair']
                            comment = m['comment']
                            st.caption(f"👤 {pair[0]} ↔ {pair[1]}: {comment}")
                    
                    # Animal Analysis
                    animals = result.get('animals', [])
                    if animals:
                        st.write("**Tespit Edilen Nesne/Canlılar:**")
                        for animal in animals:
                            st.image(image, caption=f"{animal['type']} (%{animal['confidence']*100:.0f})", width=100)
                            
                    # 4. Color Analysis
                    colors = result.get('colors', [])
                    if colors:
                        st.markdown("#### Baskın Renkler")
                        for c in colors[:3]:
                            color_hex = '#%02x%02x%02x' % (int(c['color_rgb'][0]), int(c['color_rgb'][1]), int(c['color_rgb'][2]))
                            st.markdown(f"""
                            <div style="display: flex; align_items: center; margin-bottom: 5px;">
                                <div style="width: 20px; height: 20px; background-color: {color_hex}; margin-right: 10px; border: 1px solid #ccc;"></div>
                                <div style="font-size: 0.9em;">
                                    <strong>{c['name']}</strong>: {c['meaning']}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                except Exception as e:
                    st.error(f"Hata oluştu: {e}")
                    import traceback
                    st.text(traceback.format_exc())
                
    # Cleanup
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
else:
    st.info("Lütfen sol menüden bir resim yükleyin.")

st.markdown("---")
st.caption("Not: Bu analizler bir tarama aracıdır ve kesin tanı koymaz. Uzman görüşü yerini tutmaz.")
