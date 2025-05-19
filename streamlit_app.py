
import streamlit as st
import time
import os
from main import query_transcripts, quick_query, view_transcript, list_transcript_files

def main():
    """InspareAI için geliştirilmiş Streamlit tabanlı web arayüzü"""
    
    st.set_page_config(
        page_title="InspareAI - Türkçe Konuşma Analiz Sistemi",
        page_icon="📚",
        layout="wide"
    )
    
    # Sayfa stilleri
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #424242;
        margin-bottom: 2rem;
    }
    .info-box {
        padding: 1rem;
        background-color: #f0f8ff;
        border-left: 4px solid #1E88E5;
        margin-bottom: 1rem;
    }
    .stButton button {
        width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Başlık
    st.markdown("<h1 class='main-header'>📚 InspareAI - Türkçe Konuşma Analiz Sistemi</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>Transkriptlerdeki bilgilere dayanarak sorularınızı cevaplayacak gelişmiş yapay zeka sistemi</p>", unsafe_allow_html=True)
    
    # Yan menü
    with st.sidebar:
        st.title("⚙️ Ayarlar")
        hizli_mod = st.checkbox("Hızlı yanıt modu", help="Daha az doküman kullanarak hızlı yanıtlar alın")
        dusunme_sureci = st.checkbox("Düşünme sürecini göster", help="Yapay zekanın yanıt oluşturma aşamalarını görün")
        
        st.divider()
        st.subheader("🧭 Navigasyon")
        secim = st.radio(
            "Görünüm seçin:",
            options=["💬 Sohbet", "📂 Transkript Yönetimi", "ℹ️ Yardım"],
            index=0
        )
        
        st.divider()
        st.markdown("### 📊 Sistem Bilgileri")
        
        # Transkript sayısını göster
        try:
            transcript_dir = "transcripts"
            if os.path.exists(transcript_dir):
                files = [f for f in os.listdir(transcript_dir) if f.endswith(".txt") and not f.startswith('.')]
                st.info(f"Toplam {len(files)} transkript dosyası")
            else:
                st.warning("Transkript klasörü bulunamadı")
        except:
            st.warning("Transkript bilgileri yüklenemedi")
            
        st.markdown("### 🔍 Hakkında")
        st.info("InspareAI v3.2 - Türkçe Konuşma Analiz Sistemi")
    
    # SOHBET GÖRÜNÜMÜ
    if secim == "💬 Sohbet":
        # Konuşma geçmişini oturum durumunda sakla
        if "messages" not in st.session_state:
            st.session_state.messages = []
            # Karşılama mesajı ekle
            st.session_state.messages.append({
                "role": "assistant", 
                "content": "👋 Merhaba! Ben InspareAI, transkriptlerdeki bilgilere dayanarak sorularınızı yanıtlayabilirim. Nasıl yardımcı olabilirim?"
            })
        
        # Akademik formatlı akış yanıt fonksiyonu
        def yapay_zeka_yaniti(prompt, hizli, dusunme):
            try:
                full_response = []
                
                # Streamlit için streaming callback
                def stream_to_streamlit(chunk):
                    full_response.append(chunk)
                    full_text = "".join(full_response)
                    message_placeholder.markdown(full_text + "▌")
                
                if dusunme:
                    message_placeholder.markdown("🔍 Anahtar kelimeler analiz ediliyor...")
                    time.sleep(0.5)
                    message_placeholder.markdown("🔍 Anahtar kelimeler analiz ediliyor...\n📑 İlgili dokümanlar aranıyor...")
                    time.sleep(0.7)
                    message_placeholder.markdown("🔍 Anahtar kelimeler analiz ediliyor...\n📑 İlgili dokümanlar aranıyor...\n🧠 Yanıt oluşturuluyor...")
                    time.sleep(0.5)
                
                # Streaming yanıt alın
                if hizli:
                    quick_query(prompt, stream_callback=stream_to_streamlit)
                else:
                    query_transcripts(prompt, stream_callback=stream_to_streamlit)
                
                # Stream tamamlandığında kürsörü kaldır
                full_text = "".join(full_response)
                message_placeholder.markdown(full_text)
                
                return full_text
                
            except Exception as e:
                error_message = f"⚠️ Hata: {str(e)}"
                message_placeholder.markdown(error_message)
                return error_message
        
        # Örnek sorular
        st.subheader("📝 Örnek Sorular")
        col1, col2 = st.columns(2)
        
        with col1:
            example_q1 = st.button("Türkiye'nin dış politika vizyonu nedir?", key="ex1", use_container_width=True)
            example_q2 = st.button("NATO ile ilişkiler nasıl ilerliyor?", key="ex2", use_container_width=True)
        
        with col2:
            example_q3 = st.button("Ekonomik kriz nasıl aşılır?", key="ex3", use_container_width=True)
            example_q4 = st.button("Eğitim sistemindeki sorunlar nelerdir?", key="ex4", use_container_width=True)
        
        # Örnek soruyu seçme
        if example_q1:
            st.session_state.user_input = "Türkiye'nin dış politika vizyonu nedir?"
        elif example_q2:
            st.session_state.user_input = "NATO ile ilişkiler nasıl ilerliyor?"
        elif example_q3:
            st.session_state.user_input = "Ekonomik kriz nasıl aşılır?"
        elif example_q4:
            st.session_state.user_input = "Eğitim sistemindeki sorunlar nelerdir?"
        
        st.divider()
        
        # Önceki mesajları göster
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Kullanıcı girişi
        if prompt := st.chat_input("Sorunuzu yazın...", key="user_input"):
            # Kullanıcı mesajını ekle
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
                
            # Yapay zeka yanıtı
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                response = yapay_zeka_yaniti(prompt, hizli_mod, dusunme_sureci)
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Seçilen örnek soruyu işleme
        elif "user_input" in st.session_state and st.session_state.user_input:
            prompt = st.session_state.user_input
            st.session_state.user_input = ""  # Tek seferlik kullan
            
            # Kullanıcı mesajını ekle
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
                
            # Yapay zeka yanıtı
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                response = yapay_zeka_yaniti(prompt, hizli_mod, dusunme_sureci)
                st.session_state.messages.append({"role": "assistant", "content": response})
    
    # TRANSKRİPT YÖNETİMİ GÖRÜNÜMÜ
    elif secim == "📂 Transkript Yönetimi":
        st.subheader("📂 Transkript Dosyaları")
        
        # Dosya listesi
        transcript_dir = "transcripts"
        if os.path.exists(transcript_dir):
            files = [f for f in os.listdir(transcript_dir) if f.endswith(".txt") and not f.startswith('.')]
            
            if files:
                st.success(f"{len(files)} transkript dosyası bulundu")
                
                # Dosya seçimi
                selected_file = st.selectbox(
                    "Görüntülemek istediğiniz dosyayı seçin:",
                    options=files,
                    format_func=lambda x: x
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    show_full = st.checkbox("Tüm içeriği göster", value=False)
                
                with col2:
                    if st.button("Dosyayı Görüntüle", type="primary"):
                        st.divider()
                        st.subheader(f"📄 {selected_file}")
                        file_content = view_transcript(selected_file, show_all=show_full)
                        st.markdown(file_content)
            else:
                st.warning("Hiç transkript dosyası bulunamadı")
        else:
            st.error("Transkript klasörü bulunamadı")
    
    # YARDIM GÖRÜNÜMÜ
    else:
        st.subheader("ℹ️ InspareAI Kullanım Kılavuzu")
        
        with st.expander("📌 Temel Kullanım", expanded=True):
            st.markdown("""
            - **Sohbet** bölümünde sorularınızı yazarak yapay zeka ile etkileşime geçebilirsiniz
            - **Hızlı yanıt modu** ile daha az doküman kullanarak daha hızlı yanıtlar alabilirsiniz
            - **Düşünme sürecini göster** seçeneği ile yapay zekanın çalışma adımlarını görebilirsiniz
            - Örnek soruları kullanarak sistemi test edebilirsiniz
            """)
            
        with st.expander("💡 İpuçları"):
            st.markdown("""
            - Spesifik sorular daha doğru yanıtlar almanızı sağlar
            - Tarih, zaman aralığı veya konuşmacı belirtmek sonuçların kalitesini artırır
            - Kronolojik analiz için soruda "kronoloji" veya "zaman sırası" ifadeleri kullanın
            - Konuşmacıların görüşlerini öğrenmek için "Speaker A'nın ... hakkındaki görüşleri nedir?" formatını kullanın
            """)
            
        with st.expander("📂 Transkript Dosyaları"):
            st.markdown("""
            - **Transkript Yönetimi** bölümünden mevcut dosyaları listeleyebilir ve görüntüleyebilirsiniz
            - Yeni transkript eklemek için `transcripts` klasörüne `.txt` uzantılı dosyalar ekleyin
            - Transkript dosyalarının formatı aşağıdaki gibi olmalıdır:
            ```
            0:00:00 - 0:01:30 Speaker A: Konuşma metni...
            0:01:31 - 0:02:15 Speaker B: Yanıt metni...
            ```
            """)
            
        with st.expander("⚠️ Sorun Giderme"):
            st.markdown("""
            - **Yanıt alınamadığında** sorunuzu daha açık ifade etmeyi deneyin
            - **Yavaş yanıtlar için** hızlı yanıt modunu kullanın
            - **Hata mesajlarında** belirtilen sorunları giderin (model yüklenememe, veri bulunamama vb.)
            - **Sistem çalışmazsa** terminal üzerinden `python main.py` komutu ile çalıştırın ve hata mesajlarını kontrol edin
            """)

if __name__ == "__main__":
    main()
