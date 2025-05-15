from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import os
import time
import json
import hashlib
from datetime import datetime
from collections import defaultdict
import concurrent.futures
import re

# TurkishStemmer için güvenli import
try:
    from TurkishStemmer import TurkishStemmer
    stemmer = TurkishStemmer()
    STEMMER_AVAILABLE = True
    print("TurkishStemmer başarıyla yüklendi.")
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
try:
    from vector import retriever, vectorstore
    VECTOR_DB_AVAILABLE = True
    print("Vektör veritabanı başarıyla yüklendi.")
except ImportError:
    print("UYARI: vector.py dosyası bulunamadı veya içe aktarılamadı.")
    VECTOR_DB_AVAILABLE = False
    # Temel vector store tanımla
    retriever = None
    vectorstore = None

# Modeli oluştur - Daha iyi Türkçe yanıtlar için optimizasyonlar
model = OllamaLLM(
    model="llama3.1", 
    temperature=0.2,       # Tutarlı ama yaratıcı yanıtlar için hafif arttırıldı
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

# Konuşma geçmişi ve önbellek
conversation_history = []
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

# Sistem yönergesi - Geliştirilmiş Türkçe yanıtlar için
system_instruction = """
Sen Türkçe konuşma metinlerini analiz eden, akademik düzeyde yüksek bilgiye sahip bir yapay zeka asistanısın.
Görevin, kullanıcının sorusuna verilen belge parçalarını kullanarak en doğru, açık ve kapsamlı yanıtı oluşturmaktır.

İŞLEVSEL PRENSİPLER:
1. KESİNLİKLE SADECE verilen belgedeki içeriğe dayanarak yanıt ver.
2. ASLA kendi bilgilerine, tahminlerine veya varsayımlarına dayanma.
3. Verilen metinlerde bulunmayan bir konuda bilgi istenirse "Bu konuda metinlerde yeterli bilgi bulunmamaktadır" şeklinde dürüstçe belirt.
4. Her zaman konuşmaların bağlamını, konuşmacıyı ve zaman damgalarını (örn: 00:15:30) belirt.
5. Özel terimleri, rakamları ve alıntıları tam olarak kullan.
6. Yanıtını sunmak için aşağıdaki yapıyı kullan:
   - Özet yanıt (kısa ve öz, 1-3 cümle)
   - Detaylar ve destekleyici bilgiler (ilgili alıntılar ve zamanlar ile)
   - Konuşmacı perspektifleri (varsa farklı görüşler)
   - Varsa önemli rakamlar, tarihler veya istatistikler

ANALİZ KRİTERLERİ:
1. Türkçe transkript içeriğinde geçen bilgileri doğru şekilde özetle
2. Farklı konuşmacılar arasındaki fikir ayrılıklarını veya ortak görüşleri belirt
3. Zaman sıralamasına dikkat et, olayların/konuşmaların kronolojisini koru
4. Teknik veya özel terimleri açıkla (metinde açıklama varsa)
5. Sorulara mümkün olduğunca doğrudan ve net yanıtlar ver

KAÇINILMASI GEREKENLER:
- ASLA uydurma veya belgelerde olmayan bilgi verme (en kritik kural budur)
- Metinde olmayan kişiler, olaylar veya kavramlar hakkında yorum yapma
- Politik veya ideolojik bir taraf tutma
- Gereksiz tekrarlar ve aşırı uzatmalar
- Yanıtı bulabildiğin konularda "bilgi yok" deme
- Çok teknik veya karmaşık bir dil kullanmaktan kaçın, açık ve anlaşılır ol
"""

# Doğrudan sorgulama template - Daha net yönergeler ve Türkçe iyileştirmeler
query_template = system_instruction + """

GÖREV:
Kullanıcının sorusuna verilen belge parçalarına dayanarak kapsamlı bir yanıt hazırla.
ÖNEMLİ: Yanıtın SADECE verilen metinlerdeki bilgilere dayanmalıdır.

SORU: {question}

İLGİLİ BELGE PARÇALARI:
{context}

ANALİZ TALİMATLARI:
1. Verilen metinlere bakarak soruya en iyi yanıtı oluştur
2. Yanıtı destekleyen noktaları ve konuşmacı perspektiflerini belirt
3. Soru hakkında metinlerde bilgi yoksa açıkça belirt
4. Türkçe dilbilgisi ve sözdizimi kurallarına dikkat et
5. Yanıtta zaman damgaları ve konuşmacı bilgilerini mutlaka belirt
6. Konuşma içindeki önemli alıntıları gerektiğinde tırnak içinde göster

ÇIKTI FORMATI:
- Öz Yanıt: Sorunun özet yanıtı (1-3 cümle)
- Detaylar: Zaman damgaları ve konuşmacı bilgileriyle destekleyici bilgiler
- Konuşmacı Görüşleri: Varsa farklı perspektifler
- Özet Değerlendirme: Analizin özeti

Yanıt:
"""

# Soruyu iyileştirme - Türkçe dil desteği geliştirmeleri
def enhance_question(question):
    """Kullanıcı sorusunu model kullanarak daha net ve kapsamlı hale getir"""
    
    # Kısa sorular veya soru işaretiyle bitenler için doğrudan kabul et
    if len(question) < 10 or question.endswith('?'):
        return question
    
    # Türkçe soru yapısını iyileştir
    template = """
    {system_instruction}
    
    GÖREV: 
    Aşağıdaki ifadeyi daha etkili bir sorguya dönüştür: "{question}"
    
    İyileştirme Kriterleri:
    - Daha net ve spesifik olmalı
    - Türkçe dil bilgisi kurallarına uygun olmalı
    - Soru işareti ile bitmeli
    - Anlam korunmalı
    - Transkript analizine uygun olmalı
    
    Sadece geliştirilmiş soruyu ver, açıklama ekleme.
    """
    
    enhance_prompt = ChatPromptTemplate.from_template(template)
    
    chain = (
        RunnablePassthrough.assign(
            system_instruction=lambda _: system_instruction,
            question=lambda _: question
        )
        | enhance_prompt
        | model
        | StrOutputParser()
    )
    
    try:
        enhanced = chain.invoke({})
        enhanced = enhanced.strip()
        if enhanced and len(enhanced) > 5:
            print(f"Soru iyileştirildi: {enhanced}")
            return enhanced
    except Exception as e:
        print(f"Soru iyileştirme hatası: {e}")
    
    return question

# Türkçe anahtar kelime çıkarıcı
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
    for keyword in keywords:
        # Tam eşleşme veya kelime sınırlarında eşleşme
        pattern = r'\b' + re.escape(keyword) + r'\b'
        matches = re.findall(pattern, doc_text)
        if matches:
            # İlk eşleşmeler daha önemli
            match_count = len(matches)
            if match_count > 0:
                keyword_matches += 1
                # Bir kelime çok tekrarlanıyorsa ekstra puan verir (logaritmik)
                score += 1.0 + (0.2 * min(match_count - 1, 5))
    
    # Eğer hiç eşleşme yoksa düşük bir değer dön
    if keyword_matches == 0 and keywords:
        return 0.1
        
    # Belge uzunluğuna göre normalizasyon
    doc_len = len(doc_text)
    if doc_len > 50 and keyword_matches > 0:
        density = keyword_matches / (doc_len / 100)  # Her 100 karakter başına eşleşme
        score += min(density, 2.0)  # Maksimum 2.0 puan ekle
    
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
    
    # İçeriğin genel kalitesi - metinde soru-cevap yapısı var mı?
    if '?' in doc_text and len(doc_text) > 100:
        score += 0.5  # Muhtemelen bir soru-cevap var, bu faydalı olabilir
    
    # Sonucun pozitif olmasını sağla
    return max(score, 0.1)

# Kaynakları formatlama - Daha açıklayıcı ve okunaklı format
def format_sources(docs):
    sources_text = "=== KULLANILAN KAYNAKLAR ===\n"
    
    # Dosya adına göre dokümanları grupla
    file_docs = defaultdict(list)
    for doc in docs:
        source = doc.metadata.get("source", "Bilinmiyor")
        file_docs[source].append(doc)
    
    for file_name, file_doc_list in file_docs.items():
        sources_text += f"\n--- Dosya: {file_name} ---\n"
        
        speakers = set()
        for doc in file_doc_list:
            speakers.add(doc.metadata.get("speaker", "Bilinmiyor"))
        
        sources_text += f"Konuşmacılar: {', '.join(speakers)}\n"
        sources_text += f"Toplam Parça Sayısı: {len(file_doc_list)}\n\n"
        
        for i, doc in enumerate(file_doc_list[:3], 1):  # Sadece ilk 3 parçayı göster
            speaker = doc.metadata.get("speaker", "Bilinmiyor")
            time = doc.metadata.get("time", "Bilinmiyor")
            
            # İçeriği parse et
            content_parts = doc.page_content.split("Content: ")
            content = content_parts[1] if len(content_parts) > 1 else doc.page_content
            
            # Uzun içeriği kısalt
            if len(content) > 200:
                content = content[:197] + "..."
            
            sources_text += f"Parça {i}:\n"
            sources_text += f"Konuşmacı: {speaker}\n"
            sources_text += f"Zaman: {time}\n"
            sources_text += f"İçerik: {content}\n\n"
        
        if len(file_doc_list) > 3:
            sources_text += f"... ve {len(file_doc_list) - 3} parça daha.\n"
    
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
    if len(memory_cache) > 100:
        # En son kullanılanları sakla (50 öğe)
        sorted_keys = sorted(memory_cache.keys(), key=lambda k: memory_cache[k].get('timestamp', 0), reverse=True)
        keys_to_keep = sorted_keys[:50]
        
        new_cache = {}
        for key in keys_to_keep:
            new_cache[key] = memory_cache[key]
            
        memory_cache = new_cache
        print(f"Bellek önbelleği temizlendi. Kalan öğe sayısı: {len(memory_cache)}")

# Ana sorgulama fonksiyonu - Paralel çalışma ve önbellek iyileştirmeleri
def query_transcripts(question):
    """Ana sorgulama fonksiyonu - Artık daha verimli ve hata yönetimli"""
    print("Sorgu işleniyor...")
    start_time = time.time()
    
    # Giriş kontrolü
    if not question or len(question.strip()) < 2:
        return "Lütfen geçerli bir soru girin."
        
    # Vektör veritabanı kullanılabilir mi?
    if not VECTOR_DB_AVAILABLE:
        return "Vektör veritabanı kullanılamıyor. Lütfen vector.py dosyasının varlığını kontrol edin."
    
    # Soru önbellekte var mı kontrol et (disk ve bellek)
    question_hash = hashlib.md5(question.encode()).hexdigest()
    cache_key = f"query_{question_hash}"
    
    # Önce bellek önbelleğine bak (daha hızlı)
    if cache_key in memory_cache:
        print("Bu soru daha önce sorulmuş. Bellek önbelleğinden yanıt kullanılıyor...")
        # Kullanım bilgisini güncelle
        memory_cache[cache_key]['timestamp'] = time.time()
        memory_cache[cache_key]['hits'] = memory_cache[cache_key].get('hits', 0) + 1
        return memory_cache[cache_key]['result']
    
    # Sonra disk önbelleğine bak
    if cache_key in query_cache:
        print("Bu soru daha önce sorulmuş. Disk önbelleğinden yanıt kullanılıyor...")
        result = query_cache[cache_key]
        # Bellek önbelleğine ekle
        memory_cache[cache_key] = {'result': result, 'timestamp': time.time(), 'hits': 1}
        return result
    
    try:
        # Soruyu iyileştir
        enhanced_question = enhance_question(question)
        
        # Anahtar kelimeleri çıkar
        print("Anahtar kelimeler çıkarılıyor...")
        keywords = extract_keywords(enhanced_question)
        if keywords:
            print(f"Çıkarılan anahtar kelimeler: {', '.join(keywords)}")
        
        # İlgili dokümanları getir
        try:
            print("İlgili dokümanlar getiriliyor...")
            docs = retriever.invoke(enhanced_question)
        except Exception as e:
            print(f"Doküman getirilirken hata: {e}")
            return f"Veritabanından bilgi alınırken bir sorun oluştu: {str(e)}\nLütfen daha sonra tekrar deneyin."
        
        # Doküman bulunamadıysa bildir
        if not docs:
            no_docs_message = "Bu soruyla ilgili bilgi bulunamadı. Lütfen farklı bir soru sorun veya daha genel bir ifade kullanın."
            # Yine de önbelleğe kaydet
            query_cache[cache_key] = no_docs_message
            memory_cache[cache_key] = {'result': no_docs_message, 'timestamp': time.time(), 'hits': 1}
            return no_docs_message
        
        print(f"Toplam {len(docs)} ilgili belge parçası bulundu")
        
        # Dokümanları alaka puanına göre yeniden sırala
        if keywords:
            print("Dokümanlar alaka puanına göre sıralanıyor...")
            docs = sorted(docs, key=lambda doc: calculate_relevance(doc, keywords), reverse=True)
        
        # Doğrudan dokümanlar üzerinden sorgulama yap
        query_prompt = ChatPromptTemplate.from_template(query_template)
        
        # En alakalı dokümanları birleştir (ilk 12 doküman)
        context = "\n\n".join([doc.page_content for doc in docs[:12]])
        
        # Sorgulama zinciri
        chain = (
            RunnablePassthrough.assign(
                question=lambda _: enhanced_question,
                context=lambda _: context
            )
            | query_prompt
            | model
            | StrOutputParser()
        )
        
        print("LLM yanıtı alınıyor...")
        # LLM yanıtını al - zaman aşımı ekle
        try:
            llm_result = chain.invoke({})
        except Exception as e:
            print(f"LLM yanıtı alınırken hata: {e}")
            # Doğrudan dokümanlardan basit bir yanıt oluştur
            simple_result = f"Yanıt oluşturulurken bir sorun oluştu, ancak şu dokümanları buldum:\n\n"
            for i, doc in enumerate(docs[:5], 1):
                simple_result += f"Doküman {i}:\n{doc.page_content}\n\n"
            return simple_result
        
        # Kullanılan kaynakları ekle
        result = f"=== CEVAP ===\n\n{llm_result}\n\n{format_sources(docs[:10])}"
        
        # Konuşma geçmişine ekle
        conversation_history.append({
            "question": question,
            "result_summary": llm_result[:100] + "..." if len(llm_result) > 100 else llm_result,
            "timestamp": datetime.now().isoformat(),
            "keywords": keywords
        })
        
        # Son 20 konuşmayı tut
        if len(conversation_history) > 20:
            conversation_history.pop(0)
            
        # Önbelleğe ekle
        query_cache[cache_key] = result
        memory_cache[cache_key] = {
            'result': result, 
            'timestamp': time.time(), 
            'hits': 1,
            'keywords': keywords
        }
        
        # Periyodik olarak bellek önbelleğini temizle
        if len(memory_cache) % 10 == 0:
            clear_memory_cache()
            
        # Belirli aralıklarla önbelleği diske kaydet
        if len(query_cache) % 5 == 0:
            save_cache()
        
        # İstatistikler
        end_time = time.time()
        process_time = end_time - start_time
        print(f"Sorgu işlendi. İşlem süresi: {process_time:.2f} saniye")
        
        # Analiz sonucunu otomatik olarak kaydet
        if process_time > 1.0:  # Sadece belli bir sürenin üzerindeki yanıtları kaydet
            try:
                save_analysis(question, result)
            except Exception as e:
                print(f"Analiz kaydedilirken hata: {e}")
            
        return result
        
    except Exception as e:
        error_message = f"Sorgu işlenirken beklenmeyen bir hata oluştu: {str(e)}"
        print(error_message)
        import traceback
        traceback.print_exc()
        return error_message

# Hızlı yanıt modu - Optimize edildi
def quick_query(question):
    """Hızlı yanıt modu - daha az doküman ile hızlı yanıt"""
    print("Hızlı yanıt modu aktif...")
    
    # Mevcut ayarları sakla
    original_k = retriever.search_kwargs.get("k", 12)
    original_fetch_k = retriever.search_kwargs.get("fetch_k", 40)
    
    # Daha az dokümanla hızlı sorgu için ayarları değiştir
    retriever.search_kwargs["k"] = 5
    retriever.search_kwargs["fetch_k"] = 15
    
    # Hızlı sorgu yap
    try:
        result = query_transcripts(question)
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
    print("- 'geçmiş' veya 'history': Konuşma geçmişini gösterir.")
    print("- 'temizle' veya 'clear': Önbelleği temizler.")
    print("- 'dosyalar' veya 'files': Transcript dosyalarını listeler.")
    print("- 'oku [dosya_adı] [tümü]': Transcript dosyasını görüntüler. 'tümü' parametresi tüm içeriği gösterir.")
    print("- 'analiz [metin]': Girilen metni özetler ve analiz eder.")
    print("- 'stat' veya 'stats': İstatistikleri gösterir.")
    print("- 'bellek' veya 'memory': Bellek önbelleğini temizler.")
    print("- 'q' veya 'çıkış': Programdan çıkar.")
    print("\nSorgu İpuçları:")
    print("- Sorunun başına '!' ekleyerek hızlı yanıt alabilirsiniz.")
    print("- Spesifik sorular daha doğru yanıtlar almanızı sağlar.")
    print("- Zamanla ilgili sorularda zaman aralığı belirtmek faydalıdır.")
    print("- Konuşmacıların isimlerini veya kimliklerini (A, B, vs.) belirtebilirsiniz.")
    print("\nYeni Özellikler (v3.1):")
    print("- Transkript dosyalarını doğrudan okuma ve önizleme")
    print("- Harici metin analizi")
    print("- Geliştirilmiş Türkçe anahtar kelime çıkarma")
    print("- TurkishStemmer entegrasyonu ile daha iyi sonuçlar")
    print("- Daha akıllı belge alaka puanı hesaplama")
    print("- Daha yüksek model performansı ve bağlam penceresi")
    print("-------------------------------")

# Konuşma geçmişini göster
def show_history():
    if not conversation_history:
        print("\nHenüz konuşma geçmişi yok.")
        return
    
    print("\n=== KONUŞMA GEÇMİŞİ ===")
    for i, entry in enumerate(conversation_history, 1):
        timestamp = datetime.fromisoformat(entry["timestamp"]).strftime("%H:%M:%S")
        print(f"{i}. [{timestamp}] Soru: {entry['question'][:50]}{'...' if len(entry['question']) > 50 else ''}")
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
    
    # Konuşma geçmişi
    print(f"Konuşma Geçmişi: {len(conversation_history)} soru")
    
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
    print("Transcript Analiz Asistanı v3.1")
    print("Vektör veritabanı otomatik olarak yüklendi.")
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
                
            if question.lower() == 'geçmiş' or question.lower() == 'history':
                show_history()
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

if __name__ == "__main__":
    main()