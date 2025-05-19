from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from utils.streaming import stream_llm_response, create_academic_formatted_stream
import os
import time
import json
import hashlib
from datetime import datetime
from collections import defaultdict
import concurrent.futures
import re
import subprocess
import numpy as np
import traceback

# ========== SABITLER ==========
# Maksimum döküman sayısı ve filtreleme limitleri
MAX_DOCUMENTS = 70  # İşlenecek maksimum döküman sayısı
MAX_DOCS_PER_SPEAKER = 15  # Konuşmacı başına maksimum döküman sayısı
OTHER_DOCS_LIMIT = 35  # Konuşmacıya özel olmayan maksimum döküman sayısı

# İçerik sınırlamaları
CONTENT_MAX_LENGTH = 1000  # Belge içeriği maksimum karakter sayısı
CONTEXT_TRUNCATION = 4000  # Bağlam kesme limiti
FALLBACK_CONTEXT_LIMIT = 2000  # Yedek yöntem maksimum bağlam limiti
EMERGENCY_CONTEXT_LIMIT = 1000  # Acil durum maksimum bağlam limiti
FILENAME_MAX_LENGTH = 40  # Dosya adı maksimum karakter sayısı
MIN_RESPONSE_LENGTH = 20  # Minimum LLM yanıt uzunluğu

# Zaman aşımı değerleri
PRIMARY_TIMEOUT = 30  # İlk LLM yanıt zaman aşımı (saniye)
SECONDARY_TIMEOUT = 30  # İkincil LLM yanıt zaman aşımı (saniye)
EMERGENCY_TIMEOUT = 15  # Acil durum LLM yanıt zaman aşımı (saniye)

# Önbellek parametreleri
CACHE_CLEAN_THRESHOLD = 100  # Bellek önbelleği temizleme eşiği
CACHE_KEEP_COUNT = 50  # Bellek önbelleğinde tutulacak öğe sayısı
DISK_CACHE_SAVE_INTERVAL = 5  # Önbelleğin diske kaydedilme sıklığı

# Kronolojik analiz anahtar kelimeleri
CHRONO_KEYWORDS = ["kronoloji", "zaman", "sıra", "gelişme", "tarihsel", "süreç"]

# Karşılaştırma analizi anahtar kelimeleri
COMPARISON_KEYWORDS = ["karşılaştır", "fark", "benzerlik", "benzer", "farklı"]

# TurkishStemmer için güvenli import
try:
    from TurkishStemmer import TurkishStemmer
    stemmer = TurkishStemmer()
    STEMMER_AVAILABLE = True
    print("TurkishStemmer başarıyla yüklendi.")
    print("Program çalışmaya devam ediyor...")
except ImportError:
    print("TurkishStemmer bulunamadı. Basit stemming kullanılacak.")
    # Basit bir stemmer tanımla
    class DummyStemmer:
        def stem(self, word):
            # Çok basit bir stemming - sadece yaygın Türkçe ekleri çıkar
            suffixes = ['lar', 'ler', 'leri', 'ları', 'dan', 'den', 'tan', 'ten', 
                       'a', 'e', 'i', 'ı', 'in', 'ın', 'un', 'ün', 'da', 'de', 'ta', 'te']
            result = word
            for suffix in suffixes:
                if word.endswith(suffix) and len(word) > len(suffix) + 2:
                    result = word[:-len(suffix)]
                    break
            return result
    stemmer = DummyStemmer()
    STEMMER_AVAILABLE = False

# Vector modülünü güvenli şekilde import et
print("Vector modülü yükleniyor...")
try:
    from vector import retriever, vectorstore
    VECTOR_DB_AVAILABLE = True
    print("Vektör veritabanı başarıyla yüklendi.")
except ImportError as e:
    print(f"UYARI: vector.py dosyası bulunamadı veya içe aktarılamadı: {str(e)}")
    VECTOR_DB_AVAILABLE = False
    # Temel vector store tanımla
    retriever = None
    vectorstore = None
except Exception as e:
    print(f"UYARI: Vektör veritabanı yüklenirken hata oluştu: {str(e)}")
    if "not found" in str(e) and "model" in str(e):
        print("Embedding modeli bulunamadı. Lütfen vector.py dosyasını düzenleyerek uygun bir model seçin.")
        print("Mevcut modelleri görmek için terminal'de 'ollama list' komutunu çalıştırın.")
    VECTOR_DB_AVAILABLE = False
    retriever = None
    vectorstore = None
    
print("Vector modülü yükleme tamamlandı.")

# Modeli oluştur - Daha iyi Türkçe yanıtlar için optimizasyonlar
model = OllamaLLM(
    model="llama3.1", 
    temperature=0.5,       # Tutarlı ama yaratıcı yanıtlar için hafif arttırıldı
    top_p=0.92,            # Top-p örnekleme - biraz arttırıldı
    top_k=40,              # Top-k eklenedi - daha tutarlı yanıtlar için
    num_predict=2048,      # Yanıt uzunluğu
    num_ctx=8192,          # Bağlam penceresi arttırıldı
    repeat_penalty=1.18,   # Tekrarları engelleme - biraz arttırıldı
    mirostat=2,            # Üretkenlik-tutarlılık dengesi için
    mirostat_tau=5.0,      # Üretken yaratıcılık
    mirostat_eta=0.1,      # Kararlılık faktörü
    num_thread=8           # CPU thread sayısı belirtildi - paralel işlem için
)

# Önbellek
query_cache = {}
memory_cache = {}  # Hafıza önbelleği eklendi

# Önbellek dosyası
CACHE_FILE = "query_cache.json"

# Önbelleği yükle
def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Önbellek yüklenemedi: {e}")
    return {}

# Önbelleği kaydet
def save_cache():
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(query_cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Önbellek kaydedilemedi: {e}")

# Önbelleği başlangıçta yükle
query_cache = load_cache()

# DERİN ANALİZ VE ÇOK KONULU, ESNEK YANIT PROMPTU
system_instruction = """
Sen bir çok disiplinli transkript analiz uzmanısın. Görevin, SADECE verilen transkript belgelerindeki içeriklere dayanarak, çeşitli alanlarda sorulabilecek HER TÜRLÜ SORU için derinlemesine, düşündürücü ve öğretici bir analiz ile sentez sunmaktır.

KONU UZMANLIKLARIN:
- EKONOMİ ve FİNANS: Makroekonomi, mikroekonomi, finansal piyasalar, kriptopara, borsa, yatırım analizleri
- POLİTİKA ve ULUSLARARASI İLİŞKİLER: Siyasi gelişmeler, diplomatik ilişkiler, jeopolitik stratejiler, uluslararası kuruluşlar
- TARİH ve TOPLUM: Tarihsel olaylar, toplumsal değişimler, kültürel dönüşümler, sosyal hareketler
- BİLİM ve TEKNOLOJİ: Bilimsel gelişmeler, teknolojik yenilikler, inovasyon, yapay zeka, dijital dönüşüm
- SANAT ve KÜLTÜR: Müzik, sinema, edebiyat, sanat akımları, eserler, sanatçılar, kültürel analizler
- SAĞLIK ve PSİKOLOJİ: Tıbbi gelişmeler, sağlık tavsiyeleri, ruh sağlığı, psikolojik analizler
- DİN ve FELSEFİ DÜŞÜNCE: Dini yorumlar, felsefi akımlar, etik tartışmalar, varoluşsal sorular
- EĞİTİM ve KİŞİSEL GELİŞİM: Öğrenme metotları, kişisel gelişim stratejileri, beceri geliştirme

YAKLAŞIM KURALLARIM:
- Her türlü soruyu (analiz, tahmin, karşılaştırma, eleştiri, yorumlama, açıklama) transkriptlerdeki bilgilere dayanarak cevaplayacağım.
- YALNIZCA transkriptlerde geçen bilgilerle yanıt vereceğim. Dışarıdan bilgi, tahmin, genel kültür eklemeyeceğim.
- Bilgileri sentezleyerek, karşılaştırarak, çelişkileri veya eksikleri belirterek detaylı analiz yapacağım.
- Neden-sonuç ilişkisi, önemli noktalar, tekrar eden temalar, örtük anlamlar ve bağlamsal ipuçlarını vurgulayacağım.
- Bilgi doğrudan yoksa, ilgili tüm bölümleri, dolaylı ve parçalı bilgileri birleştirerek mantıklı ve gerekçeli analiz sunacağım.
- Kronolojik analiz gerektiren sorularda, olayların zaman sırasını ve gelişimini açıkça belirteceğim.
- Kişisel görüş katmadan, objektif bir analizle yanıt vereceğim ve doğrudan alıntı kullanmayacağım.
- Yanıtım her zaman şu yapıda olacak:
  1. KONU ÖZETİ (Ana fikir ve kapsamı kısa sunma)
  2. DERİN ANALİZ (Detaylı inceleme, karşılaştırma ve sentez)
  3. SONUÇ (Kapsamlı çıkarım ve değerlendirme)
  4. KAYNAKLAR [Kaynak: DOSYA_ADI, Zaman: ZAMAN_ARALIĞI]
- Yeterli bilgi yoksa, "Bu konuda transkriptlerde yeterli bilgi bulunmamaktadır." diyeceğim.
"""

# SORGULAMA (YANIT ÜRETME) PROMPTU
query_template = """
{system_instruction}

ANALİZ GÖREVİ:
Kullanıcının sorduğu soruyu çok disiplinli bir analiz uzmanı olarak cevaplayacaksın. Aşağıdaki transkript parçaları senin bilgi kaynağındır. YALNIZCA bu kaynaklarda bulunan bilgileri kullanarak kapsamlı ve derinlemesine bir analiz sun. Doğrudan ve örtülü/dolaylı bilgileri sentezlemeye özen göster.

SORU: {question}

TRANSKRİPT PARÇALARI:
{context}

YANIT FORMATI:
1. KONU ÖZETİ: Sorunu ve ana konuyu net şekilde tanımla.
2. DERİN ANALİZ: Konuyu derinlemesine incele, farklı açılardan değerlendir, ilişkiler kur.
3. SONUÇ: Bulgularını ve çıkarımlarını kapsamlı olarak özetle.
4. KAYNAKLAR: Kullandığın transkript parçalarını dosya adı ve zaman bilgileriyle belirt.
"""

# Soruyu iyileştirme - Türkçe dil desteği geliştirmeleri
def extract_keywords(text):
    """Sorgudan anahtar kelimeleri çıkar ve kök haline dönüştür"""
    try:
        # Genişletilmiş Türkçe stopwords listesi
        stopwords = [
            've', 'veya', 'ile', 'bu', 'şu', 'o', 'bir', 'için', 'gibi', 'kadar', 'de', 'da',
            'ne', 'ki', 'ama', 'fakat', 'lakin', 'ancak', 'hem', 'ya', 'ise', 'mi', 'mu', 'mı', 'mü',
            'nasıl', 'neden', 'niçin', 'hangi', 'kim', 'kime', 'kimi', 'ne', 'nerede', 'her', 'tüm',
            'bütün', 'hep', 'hiç', 'çok', 'daha', 'en', 'pek', 'sadece', 'yalnız', 'dolayı', 'üzere'
        ]
        
        # Daha gelişmiş kelime ayırma (noktalama işaretlerini de dikkate alır)
        words = re.findall(r'\b[\wçğıöşüÇĞİÖŞÜ]+\b', text.lower())
        
        # Kök bulma işlemini daha güvenli hale getir
        keywords = []
        for word in words:
            if word not in stopwords and len(word) > 2:
                try:
                    # Stemmer ile kök bul
                    stemmed = stemmer.stem(word)
                    keywords.append(stemmed)
                except Exception:
                    # Stemmer başarısız olursa kelimeyi olduğu gibi kullan
                    keywords.append(word)
        
        # Anahtar kelimelerin ağırlıklandırılması
        keyword_counts = {}
        for keyword in keywords:
            if keyword in keyword_counts:
                keyword_counts[keyword] += 1
            else:
                keyword_counts[keyword] = 1
        
        # En az iki kez geçen kelimeleri önemli kabul et
        important_keywords = [k for k, v in keyword_counts.items() if v >= 1]
        
        # Sonuç boşsa tüm anahtar kelimeleri kullan
        if not important_keywords and keywords:
            return list(set(keywords))
            
        return list(set(important_keywords))
        
    except Exception as e:
        print(f"Anahtar kelime çıkarma hatası: {e}")
        # Hata durumunda basit bir yöntemle devam et
        words = text.lower().split()
        return list(set([w for w in words if len(w) > 2 and w not in ['ve', 'ile', 'bu', 'şu', 'o']]))

# Belge alaka puanı hesaplayıcı
def calculate_relevance(doc, keywords):
    """Belge ve anahtar kelimeler arasındaki alakayı hesapla - Geliştirilmiş versiyon"""
    doc_text = doc.page_content.lower()
    speaker = doc.metadata.get("speaker", "")
    time_info = doc.metadata.get("time", "")
    score = 0.0
    
    # Anahtar kelime bazlı puanlama - geliştirilmiş
    keyword_matches = 0
    keyword_match_positions = []
    
    for keyword in keywords:
        # Tam eşleşme veya kelime sınırlarında eşleşme
        pattern = r'\b' + re.escape(keyword) + r'\b'
        matches = re.finditer(pattern, doc_text)
        
        match_count = 0
        for match in matches:
            match_count += 1
            keyword_match_positions.append(match.start())
        
        if match_count > 0:
            keyword_matches += 1
            # İlk eşleşmeler daha önemli
            # Bir kelime çok tekrarlanıyorsa ekstra puan verir (logaritmik)
            score += 1.0 + (0.2 * min(match_count - 1, 5))
            
            # Fiil kökü ise daha fazla puan ver
            if hasattr(stemmer, '_check_verb_root') and callable(getattr(stemmer, '_check_verb_root')):
                try:
                    if stemmer._check_verb_root(keyword):
                        score += 0.5  # Fiil kökleri daha önemli
                except:
                    pass
    
    # Eğer hiç eşleşme yoksa düşük bir değer dön
    if keyword_matches == 0 and keywords:
        return 0.1
        
    # Belge uzunluğuna göre normalizasyon
    doc_len = len(doc_text)
    if doc_len > 50 and keyword_matches > 0:
        density = keyword_matches / (doc_len / 100)  # Her 100 karakter başına eşleşme
        score += min(density, 2.0)  # Maksimum 2.0 puan ekle
    
    # Eşleşen kelimelerin yakınlığı - birbirine yakın eşleşmeler daha değerli
    if len(keyword_match_positions) > 1:
        # Pozisyonları sırala
        keyword_match_positions.sort()
        
        # Ardışık eşleşmeler arasındaki mesafeleri hesapla
        distances = []
        for i in range(1, len(keyword_match_positions)):
            distance = keyword_match_positions[i] - keyword_match_positions[i-1]
            distances.append(distance)
        
        # Ortalama mesafe - küçük olması daha iyi
        avg_distance = sum(distances) / len(distances)
        proximity_score = 1.0 / (1.0 + avg_distance / 100)  # Normalize edilmiş yakınlık puanı
        score += proximity_score
    
    # Zamansal bilgiler
    if re.search(r'\d+:\d+:\d+', time_info):
        score += 0.5
    
    # Konuşmacı bilgisinin varlığı
    if speaker and len(speaker.strip()) > 0:
        score += 0.3
    
    # Daha uzun ve anlamlı cümleler için puan (çok kısa yanıtlar genelde iyi değil)
    sentences = re.split(r'[.!?]+', doc_text)
    mean_sentence_len = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
    if 5 <= mean_sentence_len <= 20:  # İdeal cümle uzunluğu
        score += 0.5
    
    # İçeriğin genel kalitesi - metin içinde soru-cevap yapısı var mı?
    if '?' in doc_text and len(doc_text) > 100:
        score += 0.5  # Muhtemelen bir soru-cevap var, bu faydalı olabilir
    
    # Sonucun pozitif olmasını sağla
    return max(score, 0.1)

# Kaynakları formatlama - Daha açıklayıcı ve okunaklı format
def format_sources(docs):
    sources_text = "=== KULLANILAN KAYNAKLAR ===\n"
    
    # Kullanılan dosyaları toplama ve grupla
    source_groups = {}
    
    # Her bir dokümanı işle ve dosyalara göre grupla
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "Bilinmiyor")
        
        # Zaman bilgisini doğrudan metadata'dan al
        time_info = doc.metadata.get("time", "")
        
        # Eğer time bilgisi yoksa veya varsayılan değerse, start_time ve end_time'ı kontrol et
        if not time_info or time_info == "Bilinmiyor" or time_info == "00:00:00 - 00:00:00":
            start_time = doc.metadata.get("start_time", "")
            end_time = doc.metadata.get("end_time", "")
            if start_time and end_time:
                # Varsayılan değerleri kontrol et
                if start_time != "00:00:00" or end_time != "00:00:00":
                    time_info = f"{start_time} - {end_time}"
                else:
                    # İçerikte zaman bilgisi var mı kontrol et
                    content = doc.page_content
                    time_match = re.search(r"Time:\s*(\d+:\d+:\d+\s*-\s*\d+:\d+:\d+)", content)
                    if time_match:
                        time_info = time_match.group(1)
                    else:
                        time_info = "Zaman bilgisi yok"
            else:
                time_info = "Zaman bilgisi yok"
        
        # Konuşmacı bilgisini al
        speaker = doc.metadata.get("speaker", "Bilinmiyor")
        if speaker == "Bilinmiyor":
            # İçerikte konuşmacı bilgisi var mı kontrol et
            content = doc.page_content
            speaker_match = re.search(r"Speaker:\s*([A-Za-z0-9]+)", content)
            if speaker_match:
                speaker = speaker_match.group(1)
        
        # İçerik örneği (ilk 50 karakter)
        content = doc.page_content.split('Content: ')[-1] if 'Content: ' in doc.page_content else doc.page_content
        content_preview = content[:50] + "..." if len(content) > 50 else content
        
        # Dosya bazlı gruplama
        if source not in source_groups:
            source_groups[source] = []
        
        source_groups[source].append({
            "index": i,
            "time": time_info,
            "speaker": speaker,
            "content_preview": content_preview.replace("\n", " ")
        })
    
    # Grupları formatlayarak göster
    for source_name, entries in source_groups.items():
        # Dosya başlığını göster
        sources_text += f"\n📄 {source_name} ({len(entries)} parça):\n"
        
        # Her bir parçayı listele
        for entry in entries:
            sources_text += f"  {entry['index']}. Zaman: {entry['time']}, Konuşmacı: {entry['speaker']}\n"
        
        sources_text += "\n"
    
    # Toplam istatistik ekle
    sources_text += f"\nToplam {len(docs)} transkript parçası kullanıldı, {len(source_groups)} farklı dosyadan."
    
    return sources_text

# Analiz sonucunu kaydet
def save_analysis(question, result):
    # Kaydedilecek klasörü oluştur
    save_dir = "analysis_results"
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    # Dosya adını oluştur
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_question = "".join(c if c.isalnum() else "_" for c in question[:30])
    filename = f"{save_dir}/analiz_{timestamp}_{safe_question}.txt"
    
    # Dosyayı oluştur ve analizi kaydet
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"Soru: {question}\n\n")
        f.write(f"Analiz Zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("="*50 + "\n\n")
        f.write(result)
    
    print(f"Analiz sonucu kaydedildi: {filename}")
    return filename

# Bellek önbelleği temizleyici
def clear_memory_cache():
    """Bellek önbelleğini temizler ve periyodik olarak çağrılmalıdır"""
    global memory_cache
    
    # 100'den fazla öğe varsa eskilerini temizle 
    if len(memory_cache) > CACHE_CLEAN_THRESHOLD:
        # En son kullanılanları sakla (50 öğe)
        sorted_keys = sorted(memory_cache.keys(), key=lambda k: memory_cache[k].get('timestamp', 0), reverse=True)
        keys_to_keep = sorted_keys[:CACHE_KEEP_COUNT]
        
        new_cache = {}
        for key in keys_to_keep:
            new_cache[key] = memory_cache[key]
            
        memory_cache = new_cache
        print(f"Bellek önbelleği temizlendi. Kalan öğe sayısı: {len(memory_cache)}")

# Ana sorgulama fonksiyonu - Paralel çalışma ve önbellek iyileştirmeleri
def query_transcripts(question, stream_callback=None):
    """Ana sorgulama fonksiyonu - Performans optimizasyonlu
    
    Args:
        question: Kullanıcı sorusu
        stream_callback: Yanıtı parça parça işlemek için callback fonksiyonu
    """
    global system_instruction  # Global sistem talimatını kullan
    print(f"Sorgu işleniyor: \"{question}\"")
    start_time = time.time()
    
    # Giriş kontrolü
    if not question or len(question.strip()) < 2:
        return "Lütfen geçerli bir soru girin."
        
    # Vektör veritabanı kullanılabilir mi?
    if not VECTOR_DB_AVAILABLE or retriever is None:
        return "Vektör veritabanı kullanılamıyor. Lütfen vector.py dosyasının varlığını kontrol edin ve uygun bir embedding modeli seçin."
    
    try:
        # Performans izleme
        stage_times = {}
        
        # Anahtar kelimeleri çıkar
        kw_start = time.time()
        print("Anahtar kelimeler çıkarılıyor...")
        keywords = extract_keywords(question)
        if keywords:
            print(f"Çıkarılan anahtar kelimeler: {', '.join(keywords)}")
        stage_times["anahtar_kelimeler"] = time.time() - kw_start
            
        # İlgili dokümanları getir
        retrieval_start = time.time()
        print("İlgili dokümanlar getiriliyor...")
        try:
            # Retriever'ı optimize et - paralelleştirme ve geliştirilmiş sorgu ile
            # MMR (Maximum Marginal Relevance) kullanarak çeşitliliği artır
            search_type = retriever.search_kwargs.get("search_type", None)
            fetch_k = retriever.search_kwargs.get("fetch_k", 50)
            
            if search_type != "mmr":
                # MMR'yi etkinleştir - çeşitliliği artırır
                retriever.search_kwargs["search_type"] = "mmr"
                retriever.search_kwargs["fetch_k"] = max(fetch_k, 50)  # En az 50 doküman getir
                retriever.search_kwargs["lambda_mult"] = 0.8  # Alaka-çeşitlilik dengesi
            
            # Dokümanları getir
            docs = retriever.invoke(question)
            
            # --- GELİŞMİŞ ve OPTİMİZE EDİLMİŞ SIRALAMA: Anahtar kelime + embedding tabanlı semantik sıralama ---
            def cosine_similarity(vec1, vec2):
                import numpy as np
                vec1 = np.array(vec1)
                vec2 = np.array(vec2)
                if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
                    return 0.0
                return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))
            
            # Paralelleştirme ile performans artışı
            def parallel_score_documents():
                # Belgeleri paralel olarak puanla
                if keywords and hasattr(vectorstore, 'embed_query') and hasattr(vectorstore, 'embed_documents'):
                    try:
                        question_emb = vectorstore.embed_query(question)
                        doc_texts = [doc.page_content for doc in docs]
                        doc_embs = vectorstore.embed_documents(doc_texts)
                        
                        # Her belge için alaka puanını hesapla
                        for i, doc in enumerate(docs):
                            kw_score = calculate_relevance(doc, keywords)
                            emb_score = cosine_similarity(question_emb, doc_embs[i])
                            emb_score = max(emb_score, 0.0)
                            kw_score_norm = min(max(kw_score / 2.0, 0.0), 1.0)
                            
                            # Optimize edilmiş puanlama formülü
                            # Anahtar kelime ağırlığını artır ve benzerlik ağırlığını dengeleyerek daha iyi sonuç
                            doc.final_score = 0.75 * kw_score_norm + 0.25 * emb_score
                            
                            # Konuşmacı puanlaması - eğer soruda belirli bir konuşmacı belirtilmişse
                            if "speaker" in question.lower() and doc.metadata.get("speaker", "").lower() in question.lower():
                                doc.final_score *= 1.5  # Konuşmacı eşleşirse fazladan puan
                        
                        return sorted(docs, key=lambda d: getattr(d, 'final_score', 0), reverse=True)
                    except Exception as e:
                        print(f"Gelişmiş sıralama uygulanamadı: {e}")
                        return sorted(docs, key=lambda doc: calculate_relevance(doc, keywords), reverse=True) if keywords else docs
                elif keywords:
                    return sorted(docs, key=lambda doc: calculate_relevance(doc, keywords), reverse=True)
                return docs
            
            # Sıralamayı uygula
            docs = parallel_score_documents()
            # --- SONU GELİŞMİŞ SIRALAMA ---
        except Exception as e:
            print(f"Doküman getirilirken hata: {e}")
            error_msg = f"Veritabanından bilgi alınırken bir sorun oluştu: {str(e)}"
            if "not found" in str(e) and "model" in str(e):
                error_msg += "\n\nBu hata embedding modelinin bulunamadığını gösteriyor."
                error_msg += "\nLütfen şu adımları izleyin:"
                error_msg += "\n1. Terminal'de 'ollama list' komutu ile mevcut modelleri kontrol edin"
                error_msg += "\n2. vector.py dosyasında kullanılan embedding modelini mevcut bir modelle değiştirin"
                try:
                    result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
                    if result.returncode == 0 and result.stdout:
                        error_msg += "\n\nMevcut modeller:"
                        for line in result.stdout.split('\n')[:5]:
                            if line.strip():
                                error_msg += f"\n  {line}"
                except Exception:
                    pass
            return error_msg
        
        stage_times["dokuman_getirme"] = time.time() - retrieval_start
        
        # Doküman bulunamadıysa bildir
        if not docs:
            no_docs_message = "Bu soruyla ilgili bilgi bulunamadı. Lütfen farklı bir soru sorun veya daha genel bir ifade kullanın."
            return no_docs_message
        
        print(f"Toplam {len(docs)} ilgili belge parçası bulundu")
        
        # Belge filtreleme ve hazırlama
        filtering_start = time.time()
        
        # Filtreleme ve çeşitleme stratejileri uygula
        # İlk 70 dokümanı al (en alakalı olanları)
        filtered_docs = docs[:MAX_DOCUMENTS]
        
        # Sorgu tipini algılama - özel işleme stratejileri
        is_chronological = any(word in question.lower() for word in CHRONO_KEYWORDS)
        is_speaker_specific = "speaker" in question.lower() or "konuşmacı" in question.lower()
        is_comparison = any(word in question.lower() for word in COMPARISON_KEYWORDS)
        
        # Kronolojik analiz için belgeleri zaman sırasına diz
        if is_chronological:
            print("Kronolojik analiz yapılıyor...")
            filtered_docs = sort_documents_chronologically(filtered_docs)
        
        # Konuşmacı spesifik analiz için filtreleme
        if is_speaker_specific:
            speaker_matches = []
            for speaker_letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                if f"speaker {speaker_letter.lower()}" in question.lower() or f"speaker {speaker_letter}" in question.lower():
                    speaker_matches.append(speaker_letter)
            
            if speaker_matches:
                print(f"Konuşmacı analizi yapılıyor: {', '.join(speaker_matches)}")
                # İlgili konuşmacıların belgelerini başa al
                speaker_docs = [doc for doc in filtered_docs if doc.metadata.get("speaker", "").upper() in speaker_matches]
                other_docs = [doc for doc in filtered_docs if doc.metadata.get("speaker", "").upper() not in speaker_matches]
                filtered_docs = speaker_docs + other_docs[:max(OTHER_DOCS_LIMIT, MAX_DOCUMENTS-len(speaker_docs))]
        
        # Karşılaştırma analizi için belge çeşitliliğini artır
        if is_comparison:
            print("Karşılaştırma analizi yapılıyor...")
            # Farklı konuşmacılardan belgeleri dengeli şekilde dahil et
            speaker_groups = {}
            for doc in filtered_docs:
                speaker = doc.metadata.get("speaker", "Unknown")
                if speaker not in speaker_groups:
                    speaker_groups[speaker] = []
                speaker_groups[speaker].append(doc)
            
            # Her konuşmacıdan dengeli sayıda belge seç
            balanced_docs = []
            max_per_speaker = MAX_DOCS_PER_SPEAKER  # Her konuşmacıdan maksimum belge sayısı
            
            # En alakalı konuşmacıları sırala (belge sayısına göre)
            sorted_speakers = sorted(speaker_groups.keys(), key=lambda s: len(speaker_groups[s]), reverse=True)
            
            for speaker in sorted_speakers:
                # Her konuşmacıdan en alakalı belgeleri ekle
                balanced_docs.extend(speaker_groups[speaker][:max_per_speaker])
            
            # Maksimum belge sayısına kadar doldur
            filtered_docs = balanced_docs[:MAX_DOCUMENTS]
            
        stage_times["filtreleme"] = time.time() - filtering_start
            
        # Prompt hazırlama
        prompt_start = time.time()
        
        # Doğrudan dokümanlar üzerinden sorgulama yap
        query_prompt = ChatPromptTemplate.from_template(query_template)
        
        # Çeşitliliği artırılmış, en alakalı dokümanları birleştir
        # Geliştirilmiş içerik formatlama - dokümanları daha düzenli hale getir
        context_parts = []
        for i, doc in enumerate(filtered_docs, 1):
            # Dosya adını kısalt
            source = doc.metadata.get('source', 'Bilinmiyor')
            if len(source) > FILENAME_MAX_LENGTH:  # Uzun dosya adlarını kısalt
                source = source[:FILENAME_MAX_LENGTH-3] + "..."
            
            # Zaman bilgisini doğru şekilde biçimlendir
            time_info = doc.metadata.get('time', '')
            if not time_info or time_info == "00:00:00 - 00:00:00":
                start_time = doc.metadata.get('start_time', '')
                end_time = doc.metadata.get('end_time', '')
                if start_time and end_time:
                    time_info = f"{start_time} - {end_time}"
              # İçeriği temizle ve biçimlendir - güvenli şekilde
            try:
                # İçerik alınamadığında varsayılan değerler kullan
                if not hasattr(doc, 'page_content') or doc.page_content is None:
                    content = "Belge içeriği alınamadı"
                else:
                    content = doc.page_content
                    if 'Content: ' in content:
                        content = content.split('Content: ')[-1]
                    content = content.strip()
                
                # İçeriği belirli bir uzunluğa kısalt (çok uzun belgeleri kırp)
                if len(content) > CONTENT_MAX_LENGTH:
                    content = content[:CONTENT_MAX_LENGTH-3] + "..."
            except Exception as content_e:
                print(f"İçerik işlenirken hata: {content_e}")
                # Hata durumunda varsayılan bir değer belirle
                content = "Belge içeriği işlenirken hata oluştu"
            
            # Belge parçasını biçimlendir
            context_part = f"[Belge {i}]\nDosya: {source}\nZaman: {time_info}\nKonuşmacı: {doc.metadata.get('speaker', 'Bilinmiyor')}\nİçerik: {content}"
            context_parts.append(context_part)
          # Bağlamı birleştir
        context = "\n\n".join(context_parts)
        
        stage_times["prompt_hazirlama"] = time.time() - prompt_start
        
        # Her sorgu için sistem talimatının bir kopyasını oluştur
        # Bu şekilde global değişken değiştirilmeyecek
        query_system_instruction = system_instruction
          # Özel sorgu tipi algılama ve prompt özelleştirme
        if is_chronological:
            # Kronolojik analiz için sistem talimatını güçlendir
            query_system_instruction += "\n\nBu sorguda KRONOLOJİK ANALİZ yapmalısın. Olayların zaman sırasına göre gelişimini adım adım açıkla. Her aşamayı tarih/zaman bilgisiyle birlikte sunarak olayların nasıl ilerlediğini göster."
        
        if is_speaker_specific:
            # Konuşmacı analizi için sistem talimatını özelleştir
            query_system_instruction += f"\n\nBu sorguda KONUŞMACI ANALİZİ yapmalısın. Belirtilen konuşmacının (Speaker) görüşlerini, ifadelerini ve yaklaşımlarını detaylı olarak ele al. Konuşmacının bakış açısını ve diğerlerinden farkını vurgula."
            
        if is_comparison:
            # Karşılaştırma analizi için sistem talimatını özelleştir
            query_system_instruction += f"\n\nBu sorguda KARŞILAŞTIRMA ANALİZİ yapmalısın. Farklı fikirleri, yaklaşımları veya konuşmacıları karşılaştırarak benzerlik ve farklılıkları ortaya koy. Ortak noktaları ve ayrışmaları tablolama yapmadan açıkça belirt."
              # Sorgulama zinciri - Değişken kapanma (closure) sorununu önlemek için güvenli yaklaşım
        # Lambda yerine doğrudan değerleri kullan
        input_values = {
            "system_instruction": query_system_instruction,
            "question": question,
            "context": context
        }
        
        # Basitleştirilmiş zincir oluşturma - pipe operator kullanmadan
        try:
            # Zincir fonksiyonu oluştur
            def execute_chain():
                try:
                    # Streaming desteği ile akademik formatı kullan
                    print("Akademik formatlı streaming yanıt oluşturuluyor...")
                    if stream_callback:
                        # Stream modunda çalış
                        formatted_prompt = query_prompt.format(**input_values)
                        create_academic_formatted_stream(
                            model=model,
                            prompt=formatted_prompt,
                            system_instruction=query_system_instruction,
                            question=question,
                            context=context,
                            callback=stream_callback
                        )
                        # Stream callback kullanıldığında None döndür
                        return None
                    else:
                        # Normal modda prompt'u önceden formatla
                        print("Birinci zincir yöntemi deneniyor...")
                        formatted_prompt = query_prompt.format(**input_values)
                        response = model.invoke(formatted_prompt)
                        return StrOutputParser().parse(response)
                    
                except Exception as e1:
                    print(f"Birinci zincir yöntemi başarısız: {e1}")
                    
                    try:
                        # İkinci yöntem: Daha açık yaklaşım
                        print("İkinci zincir yöntemi deneniyor...")
                        prompt_text = query_prompt.format(
                            system_instruction=system_instruction,
                            question=question,
                            context=context
                        )
                        response = model.invoke(prompt_text)
                        return StrOutputParser().parse(response)
                        
                    except Exception as e2:
                        print(f"İkinci zincir yöntemi başarısız: {e2}")
                        
                        # Son çare yöntemi
                        print("Son çare yöntemi deneniyor...")
                        direct_prompt = f"Sistem: {system_instruction}\n\nSoru: {question}\n\nBağlam: {context[:5000]}\n\nYanıt:"
                        response = model.invoke(direct_prompt)
                        return str(response)
            
            # Zincir fonksiyonunu tanımla
            def chain():
                return execute_chain()
            
        except Exception as outer_e:
            print(f"Zincir oluşturma tamamen başarısız: {outer_e}")
            raise outer_e
        
        # LLM yanıtını al
        llm_start = time.time()
        print("LLM yanıtı alınıyor...")
        
        try:
            # Zaman aşımı ekleyerek LLM yanıtını al
            from concurrent.futures import ThreadPoolExecutor, TimeoutError            # LLM yanıt fonksiyonu - güvenlik kontrolleri ve hata yönetimi güçlendirildi
            def get_llm_response():
                try:
                    # Zinciri çağır - artık parametresiz
                    response = chain()
                    
                    # Boş yanıt kontrolü - geliştirilmiş kontrol yapısı
                    if response is None or len(str(response).strip()) == 0:
                        raise ValueError("LLM boş yanıt döndürdü")
                    
                    return response
                    
                except ValueError as ve:
                    # Zaten hata değerlendirilmiş, detaylı loglama ile
                    print(f"LLM değer hatası: {str(ve)}")
                    # ValueError durumunda yeniden denemeden önce bekleme ekle
                    time.sleep(0.5)
                    # Fallback mekanizmasını başlat
                    raise ve
                    
                except Exception as inner_e:
                    error_str = str(inner_e)
                    print(f"LLM çağrısında hata: {error_str}")
                    
                    # Çeşitli hata türlerine özel çözümler
                    if "Cell is empty" in error_str or "NoneType" in error_str or "empty" in error_str:
                        print("İçerik temelli hata tespit edildi, alternatif yaklaşımlar deneniyor...")
                        
                        # Birinci düzeltme - Doğrudan prompt yöntemi
                        try:
                            print("1. alternatif: Doğrudan prompt yöntemi")
                            direct_prompt = f"""Sistem: {system_instruction}
                            
                            Soru: {question}
                            
                            İlgili bilgi parçaları:
                            {context[:4000]}
                            
                            Yukarıdaki bilgilere dayanarak soruyu yanıtla:"""
                            
                            direct_response = model.invoke(direct_prompt)
                            if direct_response and len(str(direct_response).strip()) > MIN_RESPONSE_LENGTH:
                                print("Doğrudan prompt yöntemi başarılı")
                                return direct_response
                        except Exception as alt1_e:
                            print(f"1. alternatif başarısız: {str(alt1_e)}")
                        
                        # İkinci düzeltme - Daha basit prompt ve daha az bağlam
                        try:
                            print("2. alternatif: Basitleştirilmiş model çağrısı")
                            simple_input = f"Lütfen şu soruyu cevapla: {question}\n\nKullanılabilecek bilgiler:\n{context[:FALLBACK_CONTEXT_LIMIT]}"
                            direct_response = model.invoke(simple_input)
                            if direct_response and len(str(direct_response).strip()) > MIN_RESPONSE_LENGTH:
                                print("Basitleştirilmiş model çağrısı başarılı")
                                return direct_response
                        except Exception as alt2_e:
                            print(f"2. alternatif başarısız: {str(alt2_e)}")
                        
                        # Üçüncü düzeltme - Minimum parametreli model
                        try:
                            print("3. alternatif: Acil durum modeli")
                            emergency_model = OllamaLLM(
                                model="llama3.1", 
                                temperature=0.2,
                                top_p=0.8,
                                num_predict=512
                            )
                            minimal_prompt = f"SORU: {question}\nBİLGİLER: {context[:EMERGENCY_CONTEXT_LIMIT]}\nYANIT:"
                            emergency_response = emergency_model.invoke(minimal_prompt)
                            if emergency_response:
                                print("Acil durum modeli başarılı")
                                return emergency_response
                        except Exception as alt3_e:
                            print(f"3. alternatif başarısız: {str(alt3_e)}")
                    
                    # Tüm alternatifler başarısız olduğunda hatayı yükselt
                    print("Tüm LLM yanıt alternatifleri başarısız oldu")
                    raise inner_e
                    
            # Streaming işlev kullanılıyorsa farklı işle
            if stream_callback:
                try:
                    # Stream modunda ThreadPool kullanma, çünkü stream_callback zaten paralel işleyecek
                    llm_result = get_llm_response()
                    # Stream modunda get_llm_response() None döndürecek, bu normal
                    stage_times["llm_yaniti"] = time.time() - llm_start
                except Exception as stream_e:
                    print(f"Stream modunda LLM yanıtı alınırken hata: {stream_e}")
                    raise stream_e
            else:                # Normal mod - Paralel işleme ile zaman aşımı kontrolü
                with ThreadPoolExecutor() as executor:
                    future = executor.submit(get_llm_response)
                    try:
                        # Gelişmiş zaman aşımı kontrolü - progressif bekletme
                        try:
                            # İlk 30 saniye içinde yanıt gelirse hemen döndür
                            llm_result = future.result(timeout=PRIMARY_TIMEOUT)
                        except TimeoutError:
                            # 30 saniye içinde yanıt gelmezse kullanıcıya bilgi ver ve biraz daha bekle
                            print("İlk 30 saniyelik yanıt süresi aşıldı, 30 saniye daha bekleniyor...")
                            
                            # Ana sistemi yavaşlatmamak için zaman aşımı sonrası kullanıcıya geri bildirim vermeye devam et
                            try:
                                llm_result = future.result(timeout=SECONDARY_TIMEOUT)  # 30 saniye daha bekle
                            except TimeoutError:
                                print("Toplam 60 saniyelik zaman aşımı - LLM yanıtı alınamadı")
                                raise TimeoutError("LLM yanıtı için maksimum süre (60 saniye) aşıldı.")
                        
                        # Yanıt kontrolü - geliştirilmiş güvenlik kontrolleri
                        if llm_result is None:
                            raise ValueError("LLM yanıtı None olarak döndü")
                          # Boş ya da çok kısa yanıtlar için kontrol
                        llm_result_str = str(llm_result).strip()
                        if len(llm_result_str) < MIN_RESPONSE_LENGTH:
                            raise ValueError(f"LLM geçersiz yanıt döndürdü (çok kısa yanıt: '{llm_result_str}')")
                        
                        stage_times["llm_yaniti"] = time.time() - llm_start
                    except TimeoutError:
                        print("LLM yanıtı zaman aşımına uğradı.")
                        raise Exception("Yanıt zaman aşımına uğradı. Lütfen tekrar deneyin veya hızlı yanıt modunu kullanın. Bu genellikle sistem yoğun olduğunda meydana gelir.")
        except Exception as e:
            print(f"LLM yanıtı alınırken hata: {e}")
            import traceback
            print("=== HATA DETAYLARI ===")
            traceback.print_exc()
            print("=====================")
            
            # Doğrudan dokümanlardan daha gelişmiş bir yanıt oluştur
            simple_result = f"Yanıt oluşturulurken bir sorun oluştu ({str(e)}), ancak şu ilgili bilgileri buldum:\n\n"
            
            # Hata durumunda daha bilgilendirici ve yapılandırılmış yanıt
            simple_result += "### İlgili Bilgi Parçaları\n\n"
            
            for i, doc in enumerate(docs[:7], 1):  # İlk 7 en alakalı belgeyi göster
                source = doc.metadata.get('source', 'Bilinmiyor')
                if len(source) > FILENAME_MAX_LENGTH:  # Uzun dosya adlarını kısalt
                    source = source[:FILENAME_MAX_LENGTH-3] + "..."
                
                # Zaman bilgisini doğru şekilde al
                time_info = doc.metadata.get('time', '')
                if not time_info or time_info == "00:00:00 - 00:00:00":
                    start_time = doc.metadata.get('start_time', '')
                    end_time = doc.metadata.get('end_time', '')
                    if start_time and end_time:
                        time_info = f"{start_time} - {end_time}"
                    else:
                        content = doc.page_content
                        time_match = re.search(r"Time:\s*(\d+:\d+:\d+)", content)
                        if time_match:
                            time_info = time_match.group(1)
                        else:
                            time_info = "Zaman bilgisi yok"
                
                speaker = doc.metadata.get('speaker', 'Bilinmiyor')
                if speaker == "Bilinmiyor":
                    content = doc.page_content
                    speaker_match = re.search(r"Speaker:\s*([A-Za-z0-9]+)", content)
                    if speaker_match:
                        speaker = speaker_match.group(1)
                  # İçeriği kısalt - güvenli bir şekilde
                try:
                    content = doc.page_content.split('Content: ')[-1] if 'Content: ' in doc.page_content else doc.page_content
                    content = content.strip() if content else ""
                    if len(content) > 500:
                        content = content[:497] + "..."
                except Exception as content_e:
                    print(f"İçerik işlenirken hata: {content_e}")
                    content = str(doc.page_content)[:500] if hasattr(doc, 'page_content') else "İçerik alınamadı"
                
                simple_result += f"**Bilgi {i}**\n\n📄 **Dosya:** {source}\n⏱️ **Zaman:** {time_info}\n👤 **Konuşmacı:** {speaker}\n\n{content}\n\n---\n\n"
            simple_result += "\nSorununuzla ilgili daha fazla bilgi için lütfen tekrar deneyin veya hızlı yanıt modunu kullanın."
              # Hata durumunda daha basit bir prompt ile tekrar deneyelim
            # Son çare yaklaşımı - tüm önceki yaklaşımlar başarısız olduğunda
            try:
                print("Basit fallback mekanizması ile tekrar deneniyor...")
                
                # "Cell is empty" hatası için daha dirençli bir yaklaşım
                # 1. Doğrudan değişken geçişi - lambda kullanmadan
                # 2. Daha basit prompt yapısı
                # 3. Daha az belge ile deneme
                
                # Basit bir prompt şablonu
                simple_prompt = """Aşağıdaki doküman parçalarını kullanarak bu soruya yanıt ver: 
                
                SORU: {soru}
                
                DOKÜMANLAR:
                {belgeler}
                
                ÖZET YANIT:"""
                
                # Değişkenleri doğrudan hazırla
                fallback_context = "\n\n".join([doc.page_content for doc in docs[:3]])  # Daha az belge
                
                # Prompt'u oluştur
                fallback_prompt = ChatPromptTemplate.from_template(simple_prompt)
                
                # Değişkenleri doğrudan dictionary olarak geçir - lambda kullanmadan
                input_map = {"soru": question, "belgeler": fallback_context}
                
                # Doğrudan modele gönder
                try:
                    # İlk fallback yöntemi
                    formatted_prompt = fallback_prompt.format(**input_map)
                    fallback_result = model.invoke(formatted_prompt)
                except Exception as e1:
                    print(f"İlk fallback yöntemi başarısız: {e1}")
                    try:
                        # İkinci fallback yöntemi - çok daha basit bir yaklaşım
                        direct_prompt = f"Soru: {question}\n\nBelgeler: {fallback_context[:FALLBACK_CONTEXT_LIMIT]}\n\nLütfen bu soruya belgelerden alınan bilgilere dayanarak özet bir yanıt ver:"
                        fallback_result = model.invoke(direct_prompt)
                    except Exception as e2:
                        print(f"İkinci fallback yöntemi de başarısız: {e2}")                        # Belgeleri doğrudan göster
                        return simple_result
                
                if fallback_result and len(str(fallback_result).strip()) > MIN_RESPONSE_LENGTH:
                    return f"{fallback_result}\n\n[Not: Bu yanıt basitleştirilmiş bir yaklaşımla oluşturulmuştur. Detaylar için lütfen tekrar deneyin.]"
                else:
                    print("Fallback yanıtı çok kısa veya boş")
                    return simple_result
                    
            except Exception as fallback_e:
                print(f"Fallback mekanizması başarısız: {fallback_e}")
                print("=== FALLBACK HATA DETAYLARI ===")
                traceback.print_exc()
                print("================================")
            
            # BASAMAKLI KURTARMA SİSTEMİ - son çare yaklaşımları
            # Safha 1: Daha sağlam doküman işleme ile acil durum modeli
            try:
                print("Son çare yaklaşımı 1: Güvenli doküman işleme ile acil durum modeli...")
                
                # Güvenli bir şekilde doküman içeriklerini al
                content_samples = []
                for i, doc in enumerate(docs[:5]):
                    try:
                        if hasattr(doc, 'page_content') and doc.page_content:
                            content = doc.page_content[:150] + "..."
                        else:
                            content = f"Belge {i+1} içeriği okunamadı"
                        content_samples.append(f"Belge {i+1}: {content}")
                    except Exception as doc_e:
                        print(f"Belge {i+1} işlenirken hata: {doc_e}")
                        content_samples.append(f"Belge {i+1}: İçerik işlenemedi")
                
                content_text = "\n\n".join(content_samples)
                
                # Basit ve sağlam prompt ile acil durum modeli
                emergency_prompt = f"""SORU: {question}
                
                BAZI İLGİLİ BİLGİLER:
                {content_text}
                
                Lütfen yukarıdaki bilgilere dayanarak soruya kısa ve öz bir yanıt ver:"""
                
                # Düşük parametre değerleriyle çağırarak başarı şansını artır
                emergency_model = OllamaLLM(
                    model="llama3.1", 
                    temperature=0.3,
                    top_p=0.8,
                    top_k=30,
                    num_predict=1024,
                    repeat_penalty=1.2
                )
                  # Stream desteği ile emergency response
                emergency_response = "[Not: Bu yanıt acil durum mekanizması ile oluşturulmuştur. Tam kapsamlı yanıt için lütfen tekrar deneyin.]"
                
                # Stream callback varsa sonucu ilet ve None döndür
                if stream_callback:
                    emergency_result = stream_llm_response(emergency_model, emergency_prompt, stream_callback)
                    stream_callback(emergency_response)
                    return None
                else:
                    # Normal mod
                    emergency_result = emergency_model.invoke(emergency_prompt)
                    if emergency_result and len(emergency_result.strip()) > MIN_RESPONSE_LENGTH:
                        print("Son çare yaklaşımı 1 başarılı")
                        return f"{emergency_result}\n\n{emergency_response}"
            except Exception as last_e:
                print(f"Son çare yaklaşımı 1 başarısız: {str(last_e)}")
            
            # Safha 2: Doküman içeriklerini tamamen atlayarak yalnızca soruya odaklanma
            try:
                print("Son çare yaklaşımı 2: Minimum parametre ve doğrudan soru...")
                
                # En düşük parametre ve en basit prompt
                minimal_model = OllamaLLM(
                    model="llama3.1", 
                    temperature=0.2,
                    num_predict=512
                )
                
                minimal_prompt = f"Şu soruyu yanıtla: {question}"                # Stream desteği ile minimal response
                minimal_note = "\n\n[Not: Bu yanıt doğrudan soru yanıtlama mekanizması ile oluşturulmuştur. Belgelere dayalı yanıt için lütfen tekrar deneyin.]"
                
                # Stream callback varsa sonucu ilet ve None döndür
                if stream_callback:
                    stream_llm_response(minimal_model, minimal_prompt, stream_callback)
                    stream_callback(minimal_note)
                    return None
                else:
                    # Normal mod
                    minimal_result = minimal_model.invoke(minimal_prompt)
                    
                    if minimal_result and len(minimal_result.strip()) > MIN_RESPONSE_LENGTH:
                        print("Son çare yaklaşımı 2 başarılı")
                        return f"{minimal_result}{minimal_note}"
            except Exception as last2_e:
                print(f"Son çare yaklaşımı 2 başarısız: {str(last2_e)}")
                
            # Safha 3: Raw string ve basit bir talimat ile deneme
            try:
                print("Son çare yaklaşımı 3: Bağlam dışı raw string yanıtı...")
                
                # Tamamen ham bir yaklaşım
                try:
                    result = subprocess.run(
                        ["ollama", "run", "llama3.1", f"'{question}' sorusunu yanıtla"],
                        capture_output=True, 
                        text=True, 
                        timeout=EMERGENCY_TIMEOUT
                    )
                    if result.stdout and len(result.stdout) > MIN_RESPONSE_LENGTH:
                        print("Son çare yaklaşımı 3 başarılı")
                        return f"{result.stdout}\n\n[Not: Bu yanıt acil durum komut satırı mekanizması ile oluşturulmuştur.]"
                except Exception as cmd_e:
                    print(f"Komut satırı denemesi başarısız: {cmd_e}")
            except Exception as last3_e:
                print(f"Son çare yaklaşımı 3 başarısız: {str(last3_e)}")
            
            # Tüm yaklaşımlar başarısız olduğunda basit bir mesaj döndür
            return simple_result + "\n\nSistem şu anda yanıt üretmekte zorlanıyor. Lütfen sorunuzu daha açık bir şekilde yeniden sormayı deneyin."
        
        # Yanıt sonlandırma ve formatlamayı iyileştir
        formatting_start = time.time()
        
        # Stream modunda kaynak bilgilerini gönder
        source_info = format_sources(docs[:15])
        
        # Stream callback varsa ve henüz döndürülmediyse kaynakları ekle
        if stream_callback:
            stream_callback(f"\n\n{source_info}")
            # Periyodik olarak bellek önbelleğini temizle
            if len(memory_cache) % 10 == 0:
                clear_memory_cache()
            
            # Belirli aralıklarla önbelleği diske kaydet
            if len(query_cache) % DISK_CACHE_SAVE_INTERVAL == 0:
                save_cache()
            
            # İstatistikler
            end_time = time.time()
            process_time = end_time - start_time
            
            # Sorgu performans analizini göster
            print(f"Sorgu işlendi. Toplam süre: {process_time:.2f} saniye")
            print("İŞLEM SÜRELERİ:")
            for stage, duration in stage_times.items():
                print(f" - {stage}: {duration:.2f} saniye")
            
            # Stream modunda None döndür
            return None
        else:
            # Normal mod - Kullanılan kaynakları ekle - geliştirilmiş formatla
            result = f"{llm_result}\n\n{source_info}"
            
            # Periyodik olarak bellek önbelleğini temizle
            if len(memory_cache) % 10 == 0:
                clear_memory_cache()
            
            # Belirli aralıklarla önbelleği diske kaydet
            if len(query_cache) % DISK_CACHE_SAVE_INTERVAL == 0:
                save_cache()
            
            stage_times["sonlandirma"] = time.time() - formatting_start
            
            # İstatistikler
            end_time = time.time()
            process_time = end_time - start_time
            
            # Sorgu performans analizini göster
            print(f"Sorgu işlendi. Toplam süre: {process_time:.2f} saniye")
            print("İŞLEM SÜRELERİ:")
            for stage, duration in stage_times.items():
                print(f" - {stage}: {duration:.2f} saniye")
                
            # Sonuç içeriği analizi
            result_length = len(result)
            source_count = result.count("📄")
            print(f"Yanıt uzunluğu: {result_length} karakter, {source_count} kaynak kullanıldı")
            
            return result
        
    except Exception as e:
        error_message = f"Sorgu işlenirken beklenmeyen bir hata oluştu: {str(e)}"
        print(error_message)
        import traceback
        traceback.print_exc()
        return error_message

# Hızlı yanıt modu - Optimize edildi
def quick_query(question, stream_callback=None):
    """Hızlı yanıt modu - daha az doküman ile hızlı yanıt
    
    Args:
        question: Kullanıcı sorusu
        stream_callback: Yanıtı parça parça işlemek için callback fonksiyonu
    """
    print("Hızlı yanıt modu aktif...")
    # Mevcut ayarları sakla
    original_k = retriever.search_kwargs.get("k", 12)
    original_fetch_k = retriever.search_kwargs.get("fetch_k", 40)
    
    # Yine yeterli sayıda dokümanla hızlı sorgu için ayarları değiştir
    retriever.search_kwargs["k"] = 25
    retriever.search_kwargs["fetch_k"] = 50
    
    # Hızlı sorgu yap
    try:
        result = query_transcripts(question, stream_callback=stream_callback)
    finally:
        # Eski ayarları geri yükle
        retriever.search_kwargs["k"] = original_k
        retriever.search_kwargs["fetch_k"] = original_fetch_k
        
    return result

# Paralel sorgu işleyici
def parallel_query(questions):
    """Birden fazla soruyu paralel olarak işleyebilir"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        # Sorguları paralel olarak gönder
        future_to_question = {executor.submit(query_transcripts, q): q for q in questions}
        results = {}
        
        # Sonuçları topla
        for future in concurrent.futures.as_completed(future_to_question):
            question = future_to_question[future]
            try:
                result = future.result()
                results[question] = result
            except Exception as e:
                results[question] = f"Sorgu işlenirken hata: {str(e)}"
                
    return results

# Yardım ekranını göster
def show_help():
    print("\n=== YARDIM ===")
    print("Kullanılabilir komutlar:")
    print("- 'yardım' veya 'help': Bu ekranı gösterir.")
    print("- 'temizle' veya 'clear': Önbelleği temizler.")
    print("- 'dosyalar' veya 'files': Transcript dosyalarını listeler.")
    print("- 'oku [dosya_adı] [tümü]': Transcript dosyasını görüntüler. 'tümü' parametresi tüm içeriği gösterir.")
    print("- 'analiz [metin]': Girilen metni özetler ve analiz eder.")
    print("- 'stat' veya 'stats': İstatistikleri gösterir.")
    print("- 'bellek' veya 'memory': Bellek önbelleğini temizler.")
    print("- 'vektör-yenile': Vektör veritabanını yeniden oluşturur (dinamik chunking ile).")
    print("- 'q' veya 'çıkış': Programdan çıkar.")
    print("\nSorgu İpuçları:")
    print("- Sorunun başına '!' ekleyerek hızlı yanıt alabilirsiniz.")
    print("- Spesifik sorular daha doğru yanıtlar almanızı sağlar.")
    print("- Zamanla ilgili sorularda zaman aralığı belirtmek faydalıdır.")
    print("- Konuşmacıların isimlerini veya kimliklerini (Speaker A, Speaker B, vs.) belirtebilirsiniz.")
    print("\nSistem Özellikleri:")
    print("- Transkript Analizi: Sistem yalnızca transkriptlerdeki bilgilere dayanarak yanıt verir.")
    print("- Akademik Yanıtlar: Yanıtlar ansiklopedik bir dille, alıntı yapmadan sentezlenir.")
    print("- Kaynak Gösterimi: Her yanıt sonunda dosya adı ve zaman aralığı belirtilir.")
    print("- Konuşmacı Bilgisi: Farklı konuşmacıların (Speaker A, B, vs.) perspektifleri belirtilir.")
    print("- Dinamik Chunking: Metin içeriğine göre otomatik ayarlanan chunk boyutları.")
    print("-------------------------------")

# Transcript dosyalarını listele
def list_transcript_files():
    transcript_dir = "transcripts"
    if not os.path.exists(transcript_dir):
        print("\nHata: 'transcripts' klasörü bulunamadı.")
        return
        
    files = [f for f in os.listdir(transcript_dir) if f.endswith(".txt") and not f.startswith('.')]
    
    if not files:
        print("\nHiç transcript dosyası bulunamadı.")
        return
        
    print("\n=== TRANSCRIPT DOSYALARI ===")
    for i, filename in enumerate(files, 1):
        file_path = os.path.join(transcript_dir, filename)
        file_size = os.path.getsize(file_path) / 1024  # KB cinsinden
        print(f"{i}. {filename} ({file_size:.1f} KB)")
    print("-------------------------------")

# İstatistikleri göster
def show_stats():
    print("\n=== SİSTEM İSTATİSTİKLERİ ===")
    
    # Vektör veritabanı istatistikleri
    try:
        collection_count = vectorstore._collection.count()
        print(f"Vektör Veritabanı Boyutu: {collection_count} doküman parçası")
    except:
        print("Vektör veritabanı boyutu alınamadı.")
        
    # Önbellek istatistikleri
    print(f"Disk Önbellek Boyutu: {len(query_cache)} sorgu")
    print(f"Bellek Önbellek Boyutu: {len(memory_cache)} sorgu")
    
    # Transcript dosyaları
    transcript_dir = "transcripts"
    if os.path.exists(transcript_dir):
        files = [f for f in os.listdir(transcript_dir) if f.endswith(".txt") and not f.startswith('.')]
        print(f"Transcript Dosyaları: {len(files)} dosya")
        
    # Model bilgileri
    print(f"Kullanılan Model: {model.model}")
    print(f"Kontekst Penceresi: {model.num_ctx} token")

    # Sistem yükleme istatistikleri
    try:
        import psutil
        cpu_percent = psutil.cpu_percent()
        mem = psutil.virtual_memory()
        print(f"CPU Kullanımı: {cpu_percent}%")
        print(f"Bellek Kullanımı: {mem.percent}% ({mem.used / (1024**3):.1f} GB / {mem.total / (1024**3):.1f} GB)")
    except:
        print("Sistem yükü istatistikleri alınamadı veya psutil kurulu değil.")
    
    print("-------------------------------")

# Transkript dosyalarını önizleme ve okuma fonksiyonu
def view_transcript(filename=None, show_all=False):
    """Transkript dosyalarını görüntüler ve özetler"""
    transcript_dir = "transcripts"
    
    # Klasör kontrolü
    if not os.path.exists(transcript_dir):
        return "Hata: 'transcripts' klasörü bulunamadı."
    
    # Mevcut dosyaları listele
    files = [f for f in os.listdir(transcript_dir) if f.endswith(".txt") and not f.startswith('.')]
    
    if not files:
        return "Hiç transcript dosyası bulunamadı."
    
    # Dosya belirtilmemişse liste göster
    if not filename:
        result = "=== MEVCUT TRANSKRİPT DOSYALARI ===\n"
        for i, f in enumerate(files, 1):
            file_path = os.path.join(transcript_dir, f)
            file_size = os.path.getsize(file_path) / 1024  # KB cinsinden
            result += f"{i}. {f} ({file_size:.1f} KB)\n"
        result += "\nDosya içeriğini görüntülemek için 'oku dosya_adı' komutunu kullanın."
        return result
    
    # Dosya adı kontrolü
    if not filename.endswith('.txt'):
        filename += '.txt'
    
    file_path = os.path.join(transcript_dir, filename)
    if not os.path.exists(file_path):
        # Dosyayı bulamadık, benzer dosyaları öner
        suggestions = [f for f in files if filename.lower() in f.lower()]
        result = f"Hata: '{filename}' dosyası bulunamadı.\n"
        if suggestions:
            result += "Benzer dosyalar:\n"
            for i, sugg in enumerate(suggestions, 1):
                result += f"{i}. {sugg}\n"
        return result
    
    # Dosyayı oku
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Dosya çok büyükse ve show_all False ise ilk ve son kısımları göster
        if len(content) > 2000 and not show_all:
            # Konuşmaları parse et
            conversations = parse_transcript(content)
            total_convs = len(conversations)
            
            result = f"=== {filename} ===\n"
            result += f"Toplam {total_convs} konuşma içeriyor.\n\n"
            
            # İlk 3 konuşma
            result += "İLK KONUŞMALAR:\n"
            for i, conv in enumerate(conversations[:3], 1):
                result += f"{i}. Zaman: {conv['time']}, Konuşmacı: {conv['speaker']}\n"
                result += f"   {conv['content'][:150]}{'...' if len(conv['content']) > 150 else ''}\n\n"
            
            # Son 3 konuşma
            if total_convs > 6:
                result += "...\n\n"
                result += "SON KONUŞMALAR:\n"
                for i, conv in enumerate(conversations[-3:], total_convs-2):
                    result += f"{i}. Zaman: {conv['time']}, Konuşmacı: {conv['speaker']}\n"
                    result += f"   {conv['content'][:150]}{'...' if len(conv['content']) > 150 else ''}\n\n"
            
            result += f"\nTüm içeriği görmek için 'oku {filename} tümü' komutunu kullanın."
            return result
        else:
            # Tüm içeriği göster
            return f"=== {filename} ===\n\n{content[:40000]}{'...(devamı var)' if len(content) > 40000 else ''}"
    
    except Exception as e:
        return f"Dosya okunurken hata oluştu: {str(e)}"

def main():
    print("\n=== Türkçe Konuşma Analiz Sistemi ===")
    print("Transcript Analiz Asistanı v3.2")
    
    # Vektör veritabanı durumunu kontrol et
    if VECTOR_DB_AVAILABLE:
        print("Vektör veritabanı başarıyla yüklendi.")
    else:
        print("UYARI: Vektör veritabanı yüklenemedi!")
        print("Sorgu işlevi kullanılamayacak. Lütfen aşağıdaki adımları izleyin:")
        print("1. Terminal'de 'ollama list' komutu ile mevcut modelleri kontrol edin")
        print("2. vector.py dosyasında kullanılan embedding modelini mevcut bir modelle değiştirin")
        print("3. Programı yeniden başlatın")
        
        # Mevcut modelleri kontrol et ve göster
        try:
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout:
                print("\nMevcut modeller:")
                for line in result.stdout.split('\n')[:10]:  # İlk 10 satırı göster
                    if line.strip():
                        print(f"  {line}")
        except Exception:
            pass
            
    print("Sorularınızı sorabilirsiniz.")
    print("Yardım için 'yardım' yazın. Çıkmak için 'q' yazın.")
    print("Hızlı yanıt için soru başına '!' ekleyin.")
    
    # Ana döngü
    try:
        while True:
            print("\n-------------------------------")
            question = input("\nSorunuz (çıkmak için q): ").strip()
            print("\n")
            
            if question.lower() in ['q', 'çıkış', 'quit', 'exit']:
                break
            
            if question.lower() == 'yardım' or question.lower() == 'help':
                show_help()
                continue
                
            if question.lower() == 'temizle' or question.lower() == 'clear':
                query_cache.clear()
                print("Önbellek temizlendi.")
                save_cache()
                continue
                
            if question.lower() == 'bellek' or question.lower() == 'memory':
                memory_cache.clear()
                print("Bellek önbelleği temizlendi.")
                continue
                
            if question.lower() == 'dosyalar' or question.lower() == 'files':
                list_transcript_files()
                continue
                
            if question.lower() == 'stat' or question.lower() == 'stats':
                show_stats()
                continue
                
            if question.lower() == 'vektör-yenile' or question.lower() == 'vektor-yenile':
                print("Vektör veritabanı yeniden oluşturuluyor (dinamik chunking ile)...")
                try:
                    # Vector modülünden create_vectorstore fonksiyonunu çağır
                    from vector import create_vectorstore
                    create_vectorstore(force_recreate=True, dynamic_chunking=True)
                    print("Vektör veritabanı başarıyla yenilendi. Programı yeniden başlatın.")
                except Exception as e:
                    print(f"Vektör veritabanı yenilenirken hata oluştu: {e}")
                continue
            
            # Transkript okuma komutları
            if question.lower().startswith('oku ') or question.lower() == 'oku':
                parts = question.split(maxsplit=2)
                filename = parts[1] if len(parts) > 1 else None
                show_all = len(parts) > 2 and 'tümü' in parts[2].lower()
                result = view_transcript(filename, show_all)
                print(result)
                continue
            
            # Analiz modunu etkinleştir
            if question.lower().startswith('analiz '):
                text = question[7:].strip()
                if not text:
                    print("Lütfen analiz edilecek metni girin.")
                    continue
                
                print("Metin analiz ediliyor...")
                # Anahtar kelimeleri çıkar ve önemli noktaları belirle
                keywords = extract_keywords(text)
                print(f"Anahtar kelimeler: {', '.join(keywords) if keywords else 'Bulunamadı'}")
                
                # Bu metni analiz etme özel promptu
                analyze_prompt = f"""
                {system_instruction}
                
                GÖREV: Aşağıdaki Türkçe metni analiz et ve önemli noktaları özetle.
                
                METİN:
                {text}
                
                Lütfen şu yapıda analiz sağla:
                1. Ana konu ve temalar
                2. Önemli noktalar ve bulgular
                3. Varsa zaman ve konuşmacı perspektifleri
                """
                
                # LLM ile analiz et
                try:
                    result = model.invoke(analyze_prompt)
                    print(f"=== ANALİZ SONUCU ===\n\n{result}")
                except Exception as e:
                    print(f"Analiz sırasında hata: {e}")
                
                continue
            
            if not question.strip():
                continue
                
            # Vektör veritabanı kullanılabilir mi kontrol et
            if not VECTOR_DB_AVAILABLE:
                print("HATA: Vektör veritabanı yüklenemediği için sorgu işlevi kullanılamıyor.")
                print("Lütfen vector.py dosyasını düzenleyerek uygun bir embedding modeli seçin ve programı yeniden başlatın.")
                continue
            
            # Hızlı yanıt isteniyor mu?
            quick = False
            if question.startswith('!'):
                quick = True
                question = question[1:].strip()
            
            # Soruyu analiz et ve cevapla
            try:
                if quick:
                    print("Hızlı yanıt modu aktif...")
                    result = quick_query(question)
                else:
                    result = query_transcripts(question)
                print(result)
            except Exception as e:
                print(f"Hata oluştu: {e}")
                import traceback
                traceback.print_exc()
    finally:
        # Programdan çıkarken önbelleği kaydet
        print("Önbellek kaydediliyor...")
        save_cache()
        print("Çıkış yapılıyor...")

# Belgeleri kronolojik olarak sıralama fonksiyonu
def sort_documents_chronologically(docs):
    """Belgeleri zaman bilgisine göre kronolojik olarak sıralar"""
    import re
    
    def extract_time_info(doc):
        # Dokümanın zamanını çıkar
        time_info = doc.metadata.get("time", "")
        
        # Eğer time bilgisi yoksa veya varsayılan değerse, start_time ve end_time'ı kontrol et
        if not time_info or time_info == "Bilinmiyor" or time_info == "00:00:00 - 00:00:00":
            start_time = doc.metadata.get("start_time", "")
            end_time = doc.metadata.get("end_time", "")
            if start_time and end_time:
                time_info = f"{start_time} - {end_time}"
            
        # İçerikten zaman bilgisi çıkarmayı dene
        if not time_info or time_info == "Bilinmiyor":
            content = doc.page_content
            time_match = re.search(r"Time:\s*(\d+:\d+:\d+)", content)
            if time_match:
                time_info = time_match.group(1)
        
        # Zaman formatını analiz et
        time_parts = re.findall(r'(\d+):(\d+):(\d+)', time_info)
        if time_parts:
            # İlk zaman değerini al (başlangıç zamanı)
            h, m, s = map(int, time_parts[0])
            # Zamanı saniyeye çevir
            return h * 3600 + m * 60 + s
        
        # Zaman bilgisi yoksa veya analiz edilemiyorsa sona koy
        return float('inf')
    
    # Zamanlarına göre belgeleri sırala
    return sorted(docs, key=extract_time_info)

# Ana programı çalıştır
if __name__ == "__main__":
    # Gerekli tüm modüllerin import edildiğinden emin ol
    import os
    import re
    import json
    import time
    import traceback
    import subprocess
    import numpy as np
    
    try:
        import psutil
    except ImportError:
        print("psutil modülü bulunamadı. Sistem istatistikleri gösterilmeyecek.")
    
    try:
        import concurrent.futures
    except ImportError:
        print("concurrent.futures modülü bulunamadı. Paralel işleme kullanılamayacak.")
    
    # Vektör veritabanı kullanılabilir mi kontrol et ve varlığını göster
    if VECTOR_DB_AVAILABLE:
        print(f"Vektör veritabanı başarıyla yüklendi. {len(retriever.vectorstore.get())} doküman parçası mevcut.")

    # Ana fonksiyonu çağır
    main()