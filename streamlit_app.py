
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
InspareAI - Streamlit Web Arayüzü.
Bu modül, InspareAI'nin web tabanlı kullanıcı arayüzünü sağlar.
"""

import streamlit as st
import time
import os
import sys

# Modüler yapıyı kullanılabilir hale getirmek için dizin ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Modüler API fonksiyonlarını içe aktar
from inspareai.api.streamlit_handler import stream_query, get_transcript_list, get_transcript_content
from inspareai.cli.command_handler import view_transcript as get_transcript_text

# Transkript görüntüleme fonksiyonu
def view_transcript(file_name, show_all=False):
    """Transkript dosyasını görüntüleme fonksiyonu"""
    file_path = os.path.join("transcripts", file_name)
    content = get_transcript_text(file_path)
    
    # İçerik uzunsa ve tümünü gösterme seçeneği aktif değilse, kısalt
    if not show_all and len(content.split('\n')) > 20:
        lines = content.split('\n')
        content = '\n'.join(lines[:20]) + '\n\n... (devamı için "Tüm içeriği göster" seçeneğini işaretleyin)'
    
    return content

def main():
    """InspareAI için geliştirilmiş Streamlit tabanlı web arayüzü"""
    
    st.set_page_config(
        page_title="InspareAI - Türkçe Konuşma Analiz Sistemi",
        page_icon="📚",
        layout="wide"
    )
    
    # Koyu/Açık tema tercihini al (varsayılan olarak koyu tema)
    if 'theme' not in st.session_state:
        st.session_state.theme = "dark"  # Varsayılan olarak koyu tema
        
    # Tema değiştirme fonksiyonu
    def toggle_theme():
        if st.session_state.theme == "light":
            st.session_state.theme = "dark"
        else:
            st.session_state.theme = "light"
    
    # Sayfa stilleri
    st.markdown("""
    <style>
    /* CSS Değişkenler - Tema Renkleri */
    :root {
        --user-msg-bg: #f7f7f8;
        --assistant-msg-bg: #ffffff;
        --msg-border: #e5e5e5;
        --msg-text: #333333;
        --code-bg: #f0f0f0;
        --input-bg: #f9f9fa;
        --examples-bg: #f9f9fa;
    }
    
    /* Dark tema renkleri */
    .dark {
        --user-msg-bg: #2a2b32;
        --assistant-msg-bg: #343541;
        --msg-border: rgba(255,255,255,0.1);
        --msg-text: #ffffff;
        --code-bg: #1e1e2e;
        --input-bg: #40414f;
        --examples-bg: #2a2b32;
    }
    
    
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
    /* Örnek soru butonları */
    div[data-testid="column"] .stButton > button {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        color: #333;
        border-radius: 6px;
        padding: 12px 16px;
        font-size: 0.9rem;
        transition: all 0.2s ease;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        height: 100%;
        white-space: normal;
        text-align: left;
    }
    div[data-testid="column"] .stButton > button:hover {
        background-color: #f5f5f5;
        border-color: #d0d0d0;
    }
    /* ChatGPT benzeri stil - Düzeltilmiş arayüz */
    .chat-sidebar {
        background-color: #202123;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    /* Sidebar içindeki butonları düzelt */
    .chat-sidebar .stButton > button {
        border: 1px solid #444654;
        background-color: transparent;
        color: #ffffff;
        text-align: left;
        width: 100%;
        padding: 10px;
        margin-bottom: 8px;
        border-radius: 5px;
        font-weight: 500;
    }
    .chat-sidebar .stButton > button:hover {
        background-color: #343541;
    }
    /* Sidebar boşluklarını ayarla */
    .css-1d391kg {
        padding-top: 3rem;
    }
    /* Başlığı ortalama ve düzenleme */
    .sidebar-title {
        text-align: center;
        color: #ffffff;
        font-size: 1.5rem;
        margin-bottom: 20px;
        padding: 10px;
        font-weight: bold;
    }
    /* Sidebar içeriğindeki tüm metinlerin rengini düzelt */
    .st-emotion-cache-16idsys p, .st-emotion-cache-16idsys span, .st-emotion-cache-16idsys label, .st-emotion-cache-16idsys div {
        color: #ffffff !important;
    }
    /* Sidebar radio ve checkbox etiketleri */
    .st-emotion-cache-16idsys .st-bq .st-aj {
        color: #ffffff !important;
    }
    /* Yeni sohbet butonu */
    .new-chat-button {
        border: 1px solid #565869 !important;
        background-color: #343541 !important;
        color: #ffffff !important;
        text-align: left !important;
        width: 100% !important;
        padding: 12px !important;
        margin-bottom: 20px !important;
        border-radius: 5px !important;
        font-size: 1rem !important;
    }
    /* Çöp kutusu stilini düzenleme */
    .delete-btn {
        background-color: transparent !important;
        color: #ff4d4f !important;
        border: none !important;
        float: right !important;
    }
    /* Mesaj Stilleri */
    .chat-message {
        padding: 1.5rem;
        margin: 0 0 1px 0;
        animation: fadein 0.5s;
        border-radius: 0;
        display: flex;
        flex-direction: column;
    }
    /* Theme uyumlu mesaj arkaplanları */
    .chat-message.user {
        background-color: var(--user-msg-bg);
        color: var(--msg-text);
    }
    .chat-message.assistant {
        background-color: var(--assistant-msg-bg);
        color: var(--msg-text);
    }
    .chat-message .message-header {
        margin-bottom: 0.75rem;
        font-weight: 500;
    }
    .chat-message .message-content {
        font-size: 1rem;
        line-height: 1.6;
    }
    /* Mesaj içindeki kod bloklarını tema uyumlu düzelt */
    .chat-message pre {
        background-color: var(--code-bg);
        padding: 0.75rem;
        border-radius: 4px;
        overflow-x: auto;
        border: 1px solid var(--msg-border);
    }
    /* Mesajların içindeki listeleme için boşluk ekle */
    .chat-message ul, .chat-message ol {
        margin-left: 1.5rem;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    /* Başlık rengini tema ile uyumlu hale getir */
    .message-header {
        color: var(--msg-text);
    }
    @keyframes fadein {
        from { opacity: 0; }
        to   { opacity: 1; }
    }
    /* Chat konteyner düzenlemesi */
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 1px;
        margin-bottom: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Dark tema ayarlarını zorla uygula - Streamlit'in tema sistemini geçersiz kılar
    st.markdown("""
    <style>
    /* Dark tema ayarları */
    body {
        color: #fff;
        background-color: #0e1117;
    }
    
    /* Streamlit dark modu ile uyumlu değişkenler */
    :root {
        --user-msg-bg: #2a2b32;
        --assistant-msg-bg: #343541;
        --msg-border: rgba(255,255,255,0.1);
        --msg-text: #ffffff;
        --code-bg: #1e1e2e;
        --input-bg: #40414f;
        --examples-bg: #2a2b32;
    }
    
    /* Streamlit chat container ve mesajların düzenlemesi */
    .stChatMessageContent {
        background-color: #343541 !important;
        color: white !important;
        border-radius: 0 !important;
        padding: 1rem !important;
    }        /* Kullanıcı ve asistan mesaj kutularını düzeltme */
        [data-testid="stChatMessage"] {
            background-color: transparent !important;
            border-radius: 0 !important;
        }
        
        /* Kullanıcı mesajları için farklı arkaplan */
        [data-testid="stChatMessage"][data-testid*="user"] .stChatMessageContent {
            background-color: #2a2b32 !important;
            border-left: 3px solid #565869 !important;
        }
        
        /* Asistan mesajları için farklı stil */
        [data-testid="stChatMessage"][data-testid*="assistant"] .stChatMessageContent {
            background-color: #343541 !important;
            border-left: 3px solid #26c6da !important;
        }
    
    /* Streamlit konteynırları için arkaplan düzeltmesi */
    .st-emotion-cache-uf99v8 {
        background-color: #343541 !important;
    }
    
    /* Streamlit ana içerik alanı için koyu tema düzeltmesi */
    .main .block-container {
        background-color: #0e1117 !important;
    }
    
    /* Başlıklar ve metinler için koyu tema renk düzeltmesi */
    h1, h2, h3, h4, h5, h6, p, span, div {
        color: #ffffff;
    }
    
    /* Chat giriş alanı için koyu tema düzeltmesi */
    .stChatFloatingInputContainer {
        background-color: #343541 !important;
        border-top: 1px solid rgba(255,255,255,0.1) !important;
    }
    .stChatInputContainer {
        background-color: #40414f !important;
    }
    textarea {
        color: white !important;
    }
    
    /* Örnek soru butonları için koyu tema */
    div[data-testid="column"] .stButton > button {
        background-color: #2a2b32 !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        color: white !important;
    }
    div[data-testid="column"] .stButton > button:hover {
        background-color: #343541 !important;
    }
    
    /* Mesaj arkaplanlarını zorla */
    .chat-message.user {
        background-color: #2a2b32 !important;
        border-bottom: 1px solid rgba(255,255,255,0.1) !important;
        color: #ffffff !important;
    }
    .chat-message.assistant {
        background-color: #343541 !important;
        border-bottom: 1px solid rgba(255,255,255,0.1) !important;
        color: #ffffff !important;
    }
    .chat-message pre {
        background-color: #1e1e2e !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
    }
    .chat-message code {
        color: #e0e0e0 !important;
        background-color: #2a2b32 !important;
        padding: 0.2rem 0.4rem !important;
        border-radius: 3px !important;
    }
    
    /* Chat container ve içerisindeki tüm metin öğelerini beyaz yap */
    .chat-container * {
        color: #ffffff !important;
    }
    
    /* Örnek soru konteynerı için koyu tema */
    .example-questions-container {
        background-color: #2a2b32 !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
    }
    .example-questions-container h4 {
        color: #ffffff !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Yan menü - ChatGPT Benzeri Sol Sidebar
    with st.sidebar:
        # Başlık ve logo
        st.markdown("""
        <div style="text-align: center; margin-bottom: 3rem; padding-bottom: 1rem; border-bottom: 1px solid rgba(255,255,255,0.2);">
            <h3 style="color: white; font-weight: 600; font-size: 1.8rem;">InspareAI</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Yeni sohbet butonu
        if "chats" not in st.session_state:
            st.session_state.chats = {
                "Ana Sohbet": [{
                    "role": "assistant", 
                    "content": "👋 Merhaba! Ben InspareAI, transkriptlerdeki bilgilere dayanarak sorularınızı yanıtlayabilirim. Nasıl yardımcı olabilirim?"
                }]
            }
            
        if "active_chat_id" not in st.session_state:
            st.session_state.active_chat_id = "Ana Sohbet"
            
        # Son soru takibi için session state
        if "last_question" not in st.session_state:
            st.session_state.last_question = None
            
        # Yeni sohbet butonu - özel stil ile
        st.markdown("""
        <style>
        div[data-testid="stButton"] > button:first-child {
            background-color: #343541;
            color: white;
            border: 1px solid #565869;
            border-radius: 6px;
            padding: 0.5rem 0.5rem;
            padding-bottom: 1rem;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 0.5rem;
    
        }
        div[data-testid="stButton"] > button:first-child:hover {
            background-color: #444654;
            border-color: #666;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Yeni sohbet butonu
        if st.button("➕ Yeni Sohbet", key="new_chat_btn"):
            import datetime
            chat_id = f"Sohbet {len(st.session_state.chats) + 1}"
            st.session_state.chats[chat_id] = [{
                "role": "assistant", 
                "content": "👋 Merhaba! Bu yeni bir sohbettir. Nasıl yardımcı olabilirim?"
            }]
            st.session_state.active_chat_id = chat_id
            st.rerun()
            
        # Sohbetler ile yeni sohbet butonu arasına ayraç ve boşluk ekle
        st.markdown("""
                    
        <div style="text-align: center; margin: 10px ; margin-bottom: 3rem; padding-bottom: 1rem; border-bottom: 1px solid rgba(255,255,255,0.2);">

        """, unsafe_allow_html=True)
        
        # Sohbet geçmişi
        
        # Sohbetleri listele
        for chat_id in st.session_state.chats:
            # İlk kısa mesajı al
            first_user_msg = "Yeni sohbet"
            for msg in st.session_state.chats[chat_id]:
                if msg["role"] == "user":
                    first_user_msg = msg["content"][:20] + ("..." if len(msg["content"]) > 20 else "")
                    break
            
            # Aktif sohbet vurgusu
            is_active = chat_id == st.session_state.active_chat_id
            active_class = "active" if is_active else ""
            
            # Stil eklemeleri
            button_style = "active-chat" if chat_id == st.session_state.active_chat_id else ""
            
            # Buton satırı için özel stil
            st.markdown(f"""
            <style>
            div[key="chat_{chat_id}"] button {{
                text-align: left;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                background-color: {("#444654" if chat_id == st.session_state.active_chat_id else "transparent")};
            }}
            </style>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns([5, 1])
            with col1:
                if st.button(f"💬 {first_user_msg}", key=f"chat_{chat_id}", 
                          help=chat_id, use_container_width=True):
                    st.session_state.active_chat_id = chat_id
                    st.rerun()
            
            with col2:
                if len(st.session_state.chats) > 1:  # En az bir sohbet kalmalı
                    # Çöp kutusu butonu için özel stil
                    st.markdown("""
                    <style>
                    div[data-testid="column"] + div[data-testid="column"] button {
                        background-color: transparent !important;
                        border: none !important;
                        color: #ff4d4f !important;
                        min-width: 30px !important;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    if st.button("🗑️", key=f"delete_{chat_id}"):
                        del st.session_state.chats[chat_id]
                        if chat_id == st.session_state.active_chat_id:
                            st.session_state.active_chat_id = next(iter(st.session_state.chats))
                        st.rerun()
                        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Ayarlar
        st.divider()
        st.markdown("""
        <div style="color: white; margin-bottom: 1rem;">
            <h2 style="font-size: 1.5rem; font-weight: 600;">⚙️ Ayarlar</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Checkbox'lar için stil
        st.markdown("""
        <style>
        div[data-testid="stCheckbox"] label {
            color: white !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Checkbox'ları iyileştirilmiş stil ile göster
        hizli_mod = st.checkbox("Hızlı yanıt modu", help="Daha az doküman kullanarak hızlı yanıtlar alın")
        # Düşünme süreci varsayılan olarak aktif
        dusunme_sureci = st.checkbox("Düşünme sürecini göster", value=True, help="Yapay zekanın yanıt oluşturma aşamalarını görün")
        
        # Geçiş seçenekleri
        st.divider()
        st.markdown("""
        <div style="color: white; margin-bottom: 1rem;">
            <h3 style="font-size: 1.3rem; font-weight: 600;">🧭 Navigasyon</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Radio butonları için stil
        st.markdown("""
        <style>
        /* Radio buton metinlerini beyaz yap */
        div[data-testid="stRadio"] label {
            color: white !important;
        }
        /* Radio seçeneklerinin metinlerini beyaz yap */
        .st-emotion-cache-2q2jyk {
            color: white !important;
        }
        /* Radio etiketlerini beyaz yap */
        .st-emotion-cache-ue6h4q {
            color: white !important;
        }
        /* Yardım butonunun rengini düzenle */
        .st-emotion-cache-16idsys button[aria-label="More info"] {
            color: rgba(255, 255, 255, 0.7) !important;
        }
        /* Radio buton işaretlerini belirginleştir */
        .st-emotion-cache-1gx9yot {
            background-color: #4a8eff !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        secim = st.radio(
            "Görünüm seçin:",
            options=["💬 Sohbet", "📂 Transkript Yönetimi", "ℹ️ Yardım"],
            index=0
        )
        
        # Sistem bilgileri
        st.divider()
        st.markdown("""
        <div style="color: white;">
            <h3>📊 Sistem Bilgileri</h3>
        </div>
        """, unsafe_allow_html=True)
        
        try:
            transcript_dir = "transcripts"
            if os.path.exists(transcript_dir):
                files = [f for f in os.listdir(transcript_dir) if f.endswith(".txt") and not f.startswith('.')]
                st.markdown(f"""
                <div style="background-color: rgba(38, 198, 218, 0.2); border-left: 3px solid #26c6da; 
                     padding: 10px; border-radius: 4px; margin-top: 10px; color: white;">
                    ℹ️ Toplam {len(files)} transkript dosyası
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background-color: rgba(255, 171, 64, 0.2); border-left: 3px solid #ffab40; 
                     padding: 10px; border-radius: 4px; margin-top: 10px; color: white;">
                    ⚠️ Transkript klasörü bulunamadı
                </div>
                """, unsafe_allow_html=True)
        except:
            st.markdown(f"""
            <div style="background-color: rgba(255, 171, 64, 0.2); border-left: 3px solid #ffab40; 
                 padding: 10px; border-radius: 4px; margin-top: 10px; color: white;">
                ⚠️ Transkript bilgileri yüklenemedi
            </div>
            """, unsafe_allow_html=True)
    
    # SOHBET GÖRÜNÜMÜ
    if secim == "💬 Sohbet":
      
        # Daha iyi görünüm için konteynır stilini ayarla
        st.markdown("""
        <style>
        /* Ana içeriği ortala ve maksimum genişliği sınırla */
        .main .block-container {
            max-width: 900px !important;
            padding-top: 1rem;
            padding-bottom: 3rem;
            margin: 0 auto;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Aktif sohbet için mesajları al
        active_messages = st.session_state.chats[st.session_state.active_chat_id]
        
        # Yanıt fonksiyonu - modüler API kullanarak
        def yapay_zeka_yaniti(prompt, hizli, dusunme):
            try:
                # Streamlit için callback tanımı
                def update_ui(text):
                    message_placeholder.markdown(text)
                
                # Modüler API fonksiyonunu kullan
                result = stream_query(prompt, update_ui, hizli, dusunme)
                
                # İmleç karakterini temizle
                if result and "▌" in result:
                    result = result.replace("▌", "")
                
                return result
                
            except Exception as e:
                error_message = f"⚠️ Hata: {str(e)}"
                message_placeholder.markdown(error_message)
                return error_message
        
        # Örnek sorular - ChatGPT benzeri üstte örnek kartlar
        if not any(msg["role"] == "user" for msg in active_messages):  # Sadece ilk açılışta göster
            st.markdown("""
            <style>
            /* Tema uyumlu örnek soru başlığı */
            .example-questions-container {
                padding: 1.5rem;
                margin-bottom: 1.5rem;
                background-color: var(--examples-bg);
                border-radius: 8px;
                border: 1px solid var(--msg-border);
            }
            .example-questions-container h4 {
                color: var(--msg-text) !important;
            }
            </style>
 
            """, unsafe_allow_html=True)
            
            # col1, col2, col3 = st.columns(3)
            # with col1:
            #     if st.button("Türkiye'nin dış politika vizyonu nedir?", key="ex1", use_container_width=True):
            #         st.session_state.user_input = "Türkiye'nin dış politika vizyonu nedir?"
            
            # with col2:
            #     if st.button("NATO ile ilişkiler nasıl ilerliyor?", key="ex2", use_container_width=True):
            #         st.session_state.user_input = "NATO ile ilişkiler nasıl ilerliyor?"
            
            # with col3:
            #     if st.button("Ekonomik kriz nasıl aşılır?", key="ex3", use_container_width=True):
            #         st.session_state.user_input = "Ekonomik kriz nasıl aşılır?"
        
        # ChatGPT benzeri mesaj gösterimi için düzenlenmiş stil
        st.markdown("""
        <style>
        /* Streamlit chat container ve mesajları için iyileştirmeler */
        [data-testid="stChatMessageContent"] {
            padding: 1.2rem !important;
            border-radius: 6px !important;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1) !important;
            margin-top: 5px !important;
            margin-bottom: 20px !important;
        }
        [data-testid="stChatMessage"] {
            margin-bottom: 15px !important;
            padding-bottom: 10px !important;
        }
        .stChatMessageContent div {
            word-break: break-word;
        }
        /* Chat mesaj alanı için genel stil düzenlemeleri */
        [data-testid="stChatFloatingInputContainer"] {
            position: sticky;
            bottom: 0;
            z-index: 100;
            background-color: var(--assistant-msg-bg);
            border-top: 1px solid var(--msg-border);
        }
        /* Tüm chat alanı için scroll düzeltmesi */
        .main .block-container {
            overflow-y: auto;
            display: flex;
            flex-direction: column;
        }
        
        /* Ortadaki boşluğu kaldır ve sohbeti kesintisiz göster */
        [data-testid="stVerticalBlock"] {
            gap: 0 !important;
        }
        /* Streamlit'in chat konteyner düzenlemesi iyileştirme */
        div[data-testid="stChatMessageContainer"] {
            display: flex;
            flex-direction: column;
            overflow-y: auto;
            padding: 0 1rem;
            flex: 1;
            gap: 1px;
            margin-bottom: 1rem;
            border: 1px solid var(--msg-border);
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            background-color: var(--assistant-msg-bg);
        }
        
        /* Boş kutuları gizle */
        .element-container:empty {
            display: none !important;
        }
        
        /* Mesajları tam genişlikte göster ve aralarında belirgin boşluk bırak */
        [data-testid="stChatMessage"] {
            width: 100%;
            margin-bottom: 25px !important;
            padding: 12px 0 !important;
        }
        /* Kullanıcı ve yapay zeka mesajları arasındaki ayrımı belirginleştir */
        [data-testid="stChatMessageAvatar"] {
            margin-top: 6px !important;
        }
        /* Son mesaj için daha fazla alt boşluk */
        [data-testid="stChatMessageContainer"] > div:last-child [data-testid="stChatMessage"] {
            margin-bottom: 35px !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Mesajlar için özel stil uygula
        st.markdown("""
        <style>
        /* Mesaj geçmişi container için stil */
        .messages-history-container {
            padding: 10px 0;
            margin-bottom: 30px;
            display: flex;
            flex-direction: column;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Tüm mesajları tutarlı bir şekilde gösterecek scroll edilebilir konteyner
        # Doğrudan Streamlit'in native chat message sistemini kullanalım
        messages_container = st.container()
        
        # Tüm mesajları göster - her mesaj için ayrı bir chat_message çağrısı yapalım
        with messages_container:
            st.markdown('<div class="messages-history-container">', unsafe_allow_html=True)
            for idx, message in enumerate(active_messages):
                # İmleç karakterini temizle
                content = message["content"]
                if content and "▌" in content:
                    content = content.replace("▌", "")
                
                with st.chat_message(message["role"]):
                    st.markdown(content)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Tema uyumlu kullanıcı girişi
        st.markdown("""
        <style>
        /* Tema uyumlu giriş alanı */
        .stChatFloatingInputContainer {
            padding: 10px;
            border-top: 1px solid var(--msg-border);
            background-color: var(--assistant-msg-bg) !important;
        }
        .stChatInputContainer {
            background-color: var(--input-bg) !important;
            border-radius: 8px !important;
            padding: 8px 10px !important;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05) !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Kullanıcı girişi - daha sade ve etkili yaklaşımla
        if prompt := st.chat_input("Sorunuzu yazın...", key=f"user_input_{len(active_messages)}"):
            # Tekrarları önlemek için son soruyu kontrol et
            last_question = None
            if "last_question" not in st.session_state:
                st.session_state.last_question = None
                
            last_question = st.session_state.last_question
            
            # Eğer bu yeni bir soru ise (tekrar değilse) işle
            if last_question != prompt:
                # Son soruyu kaydet
                st.session_state.last_question = prompt
                
                # Kullanıcı mesajını göster
                with st.chat_message("user"):
                    st.markdown(prompt)
                    
                # Kullanıcı mesajını session state'e kaydet
                active_messages.append({"role": "user", "content": prompt})
            
            # Konuşma geçmişini hazırla (Bağlam için)
            context = ""
            for message in active_messages[:-1]:  # Son mesajı (yeni kullanıcı mesajı) hariç tut
                prefix = "Kullanıcı: " if message["role"] == "user" else "InspareAI: "
                context += f"{prefix}{message['content']}\n\n"
            
            # Bağlamlı soru oluştur
            enhanced_prompt = f"{context}Kullanıcı: {prompt}\n\nYukarıdaki konuşma geçmişini dikkate alarak, son soruyu cevaplayın."
                
            # Yapay zeka yanıtı
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                response = yapay_zeka_yaniti(enhanced_prompt, hizli_mod, dusunme_sureci)
                
                # İmleç karakterini temizle
                if response and "▌" in response:
                    response = response.replace("▌", "")
                
                active_messages.append({"role": "assistant", "content": response})
                
            # Sayfayı yeniden yükle (tekrarı önlemek için)
            st.rerun()
        
        # Seçilen örnek soruyu işleme
        elif "user_input" in st.session_state and st.session_state.user_input:
            prompt = st.session_state.user_input
            st.session_state.user_input = ""  # Tek seferlik kullan
            
            # Tekrarları önle
            if st.session_state.last_question != prompt:
                # Son soruyu kaydet
                st.session_state.last_question = prompt
                
                # Kullanıcı mesajını göster
                with st.chat_message("user"):
                    st.markdown(prompt)
                    
                # Kullanıcı mesajını ekle
                active_messages.append({"role": "user", "content": prompt})
            
            # Konuşma geçmişini hazırla (Bağlam için) 
            context = ""
            for message in active_messages[:-1]:  # Son mesajı (yeni kullanıcı mesajı) hariç tut
                prefix = "Kullanıcı: " if message["role"] == "user" else "InspareAI: "
                context += f"{prefix}{message['content']}\n\n"
            
            # Bağlamlı soru oluştur
            enhanced_prompt = f"{context}Kullanıcı: {prompt}\n\nYukarıdaki konuşma geçmişini dikkate alarak, son soruyu cevaplayın."
                
            # Yapay zeka yanıtı
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                response = yapay_zeka_yaniti(enhanced_prompt, hizli_mod, dusunme_sureci)
                
                # İmleç karakterini temizle
                if response and "▌" in response:
                    response = response.replace("▌", "")
                
                active_messages.append({"role": "assistant", "content": response})
                
            # Sayfayı güncelle
            st.rerun()
    
    # TRANSKRİPT YÖNETİMİ GÖRÜNÜMÜ
    elif secim == "📂 Transkript Yönetimi":
        st.subheader("📂 Transkript Dosyaları")
        
        # Transkript yöneticisi için koyu tema uyumlu stiller
        st.markdown("""
        <style>
        /* Selectbox ve diğer giriş alanları için koyu tema */
        .stSelectbox [data-baseweb="select"] {
            background-color: #2a2b32 !important;
        }
        .stSelectbox [data-baseweb="select"] > div {
            background-color: #2a2b32 !important;
            color: white !important;
            border-color: rgba(255,255,255,0.1) !important;
        }
        .stSelectbox [data-baseweb="select"] svg {
            color: white !important;
        }
        
        /* Butonların koyu temaya uygun stillendirilmesi */
        .element-container button[kind="primary"] {
            background-color: #4a8eff !important;
            color: white !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Dosya listesi
        transcript_dir = "transcripts"
        if os.path.exists(transcript_dir):
            files = [f for f in os.listdir(transcript_dir) if f.endswith(".txt") and not f.startswith('.')]
            
            if files:
                st.markdown(f"""
                <div style="background-color: rgba(38, 198, 218, 0.2); border-left: 3px solid #26c6da; 
                     padding: 15px; border-radius: 4px; margin: 10px 0; color: white;">
                    ✅ {len(files)} transkript dosyası bulundu
                </div>
                """, unsafe_allow_html=True)
                
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
                st.markdown(f"""
                <div style="background-color: rgba(255, 171, 64, 0.2); border-left: 3px solid #ffab40; 
                     padding: 15px; border-radius: 4px; margin: 10px 0; color: white;">
                    ⚠️ Hiç transkript dosyası bulunamadı
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background-color: rgba(255, 59, 48, 0.2); border-left: 3px solid #ff3b30; 
                 padding: 15px; border-radius: 4px; margin: 10px 0; color: white;">
                ❌ Transkript klasörü bulunamadı
            </div>
            """, unsafe_allow_html=True)
    
    # YARDIM GÖRÜNÜMÜ
    else:
        st.subheader("ℹ️ InspareAI Kullanım Kılavuzu")
        
        # Dark tema için expander'ları düzelt
        st.markdown("""
        <style>
        /* Expander başlığı ve içeriği için tema uyumlu stil */
        .streamlit-expanderHeader {
            background-color: #2a2b32 !important;
            color: white !important;
        }
        .streamlit-expanderContent {
            background-color: #343541 !important;
            color: #e0e0e0 !important;
        }
        
        /* Markdown içeriklerini koyu temada düzgün göster */
        .element-container .stMarkdown p {
            color: #e0e0e0 !important;
        }
        .stMarkdown ul li, .stMarkdown ol li {
            color: #e0e0e0 !important;
        }
        .stMarkdown code {
            background-color: #1e1e2e !important;
            color: #e0e0e0 !important;
            padding: 2px 5px;
            border-radius: 3px;
        }
        </style>
        """, unsafe_allow_html=True)
        
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
