# VECTOR.PY - TÜRKÇE TRANSKRİPT VEKTÖR VERİTABANI OLUŞTURMA (v2.0)
# Bu dosya, transkript verilerini vektörleştirerek veritabanına kaydeder.
# Vektör veritabanı oluşturmak için doğrudan bu dosyayı çalıştırın: python vector.py
# Vektör veritabanı güncellemek için de aynı komut kullanılabilir.

# Eski vector.py içeriği:
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
import re
import time
import nltk
import concurrent.futures
import psutil
import sys
import argparse
import subprocess

# Türkçe NLP için gerekli bileşenleri yükle
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Gelişmiş Türkçe kök bulma için TurkishStemmer'ı dene
try:
    from TurkishStemmer import TurkishStemmer
    stemmer = TurkishStemmer()
    STEMMER_AVAILABLE = True
    print("TurkishStemmer başarıyla yüklendi.")
except ImportError:
    try:
        # Alternatif olarak snowballstemmer'ı dene
        from snowballstemmer import TurkishStemmer
        stemmer = TurkishStemmer()
        STEMMER_AVAILABLE = True
        print("Snowball TurkishStemmer başarıyla yüklendi.")
    except ImportError:
        print("TurkishStemmer bulunamadı. Geliştirilmiş basit stemming kullanılacak.")
        # Geliştirilmiş basit stemmer tanımla
        class DummyStemmer:
            def __init__(self):
                # İsim çekimleri için ekler
                self.noun_suffixes = [
                    'lar', 'ler', 'leri', 'ları', 'dan', 'den', 'tan', 'ten', 
                    'a', 'e', 'i', 'ı', 'in', 'ın', 'un', 'ün', 'da', 'de', 'ta', 'te',
                    'nın', 'nin', 'nun', 'nün', 'ya', 'ye', 'yu', 'yü',
                    'nda', 'nde', 'nta', 'nte', 'ndan', 'nden', 'ki', 'lık', 'lik'
                ]
                
                # Fiil çekimleri için ekler
                self.verb_suffixes = [
                    'mak', 'mek', 'yor', 'iyor', 'ıyor', 'uyor', 'üyor',
                    'acak', 'ecek', 'acağ', 'eceğ', 'miş', 'mış', 'muş', 'müş',
                    'di', 'dı', 'du', 'dü', 'ti', 'tı', 'tu', 'tü',
                    'sa', 'se', 'malı', 'meli', 'abil', 'ebil',
                    'ar', 'er', 'ır', 'ir', 'ur', 'ür', 
                    'dik', 'dık', 'duk', 'dük', 'tik', 'tık', 'tuk', 'tük'
                ]
                
                # Sık kullanılan fiil kökleri
                self.common_verb_roots = [
                    'gel', 'git', 'ol', 'yap', 'et', 'de', 'ver', 'al', 'kal', 'bak',
                    'gör', 'bil', 'dur', 'bul', 'çık', 'geç', 'iste', 'söyle', 'başla',
                    'anla', 'çalış', 'düşün', 'konuş', 'oku', 'yaz', 'sev', 'bekle',
                    'gir', 'var', 'yok', 'aç', 'kapat', 'otur', 'koş', 'yürü', 'uyu',
                    'uyan', 'ye', 'iç', 'dinle', 'izle', 'kullan', 'yaşa', 'öl'
                ]
                
                # Ünlü uyumu için sesli harfler
                self.vowels = 'aeıioöuü'
                
                # Yumuşama kuralı için son harf değişimleri
                self.softening_map = {
                    'p': 'b', 'ç': 'c', 't': 'd', 'k': 'ğ'
                }
                
            def _is_vowel(self, char):
                """Bir karakterin sesli harf olup olmadığını kontrol eder"""
                return char.lower() in self.vowels
                
            def _has_turkish_vowel_harmony(self, word, suffix):
                """Türkçe ünlü uyumuna göre ekin kelimeye uyup uymadığını kontrol eder"""
                if not word or not suffix:
                    return False
                    
                # Kelime ve ekteki son sesli harfleri bul
                word_last_vowel = None
                for char in reversed(word):
                    if self._is_vowel(char):
                        word_last_vowel = char.lower()
                        break
                        
                suffix_first_vowel = None
                for char in suffix:
                    if self._is_vowel(char):
                        suffix_first_vowel = char.lower()
                        break
                
                if not word_last_vowel or not suffix_first_vowel:
                    return False
                    
                # Kalın ünlü uyumu
                thick_vowels = 'aıou'
                thin_vowels = 'eiöü'
                
                # Ünlü uyumu kontrolü
                if word_last_vowel in thick_vowels and suffix_first_vowel in thick_vowels:
                    return True
                if word_last_vowel in thin_vowels and suffix_first_vowel in thin_vowels:
                    return True
                    
                return False
            
            def _check_verb_root(self, word):
                """Kelimenin bilinen bir fiil kökü olup olmadığını kontrol eder"""
                return word in self.common_verb_roots
                
            def _apply_softening_rule(self, word):
                """
                Yumuşama kuralını uygular
                Örneğin: kitap -> kitab, ağaç -> ağac
                """
                if not word or len(word) < 2:
                    return word
                    
                last_char = word[-1]
                if last_char in self.softening_map:
                    return word[:-1] + self.softening_map[last_char]
                    
                return word
                
            def _reverse_softening_rule(self, word):
                """
                Yumuşama kuralını tersine çevirir
                Örneğin: kitab -> kitap, ağac -> ağaç
                """
                if not word or len(word) < 2:
                    return word
                    
                reverse_map = {v: k for k, v in self.softening_map.items()}
                last_char = word[-1]
                if last_char in reverse_map:
                    return word[:-1] + reverse_map[last_char]
                    
                return word
                
            def stem(self, word):
                """
                Geliştirilmiş stemming - isim ve fiil çekimlerini destekler
                Türkçe ünlü uyumu kurallarını da göz önünde bulundurur
                """
                if not word or len(word) < 3:
                    return word
                    
                original_word = word
                word = word.lower()
                
                # Önce yumuşama kuralını uygula
                word_softened = self._apply_softening_rule(word)
                
                # Önce fiil kökü olup olmadığını kontrol et
                for verb_root in self.common_verb_roots:
                    if word_softened.startswith(verb_root) and len(word_softened) > len(verb_root):
                        # Fiil kökü bulundu, çekim eki olabilir
                        return verb_root
                
                # Fiil ekleri için kontrol
                for suffix in sorted(self.verb_suffixes, key=len, reverse=True):
                    if word_softened.endswith(suffix) and len(word_softened) > len(suffix) + 2:
                        stem_candidate = word_softened[:-len(suffix)]
                        
                        # Ünlü uyumu kontrolü
                        if self._has_turkish_vowel_harmony(stem_candidate, suffix):
                            # Eğer kalan kısım bir fiil kökü ise veya 2 harften uzunsa
                            if self._check_verb_root(stem_candidate) or len(stem_candidate) > 2:
                                return self._reverse_softening_rule(stem_candidate)
                
                # İsim ekleri için kontrol
                for suffix in sorted(self.noun_suffixes, key=len, reverse=True):
                    if word_softened.endswith(suffix) and len(word_softened) > len(suffix) + 2:
                        stem_candidate = word_softened[:-len(suffix)]
                        
                        # Ünlü uyumu kontrolü
                        if self._has_turkish_vowel_harmony(stem_candidate, suffix):
                            return self._reverse_softening_rule(stem_candidate)
                
                # Hiçbir ek bulunamadıysa kelimeyi olduğu gibi döndür
                return self._reverse_softening_rule(word_softened)
        
        stemmer = DummyStemmer()
        STEMMER_AVAILABLE = False

# Modelin varlığını kontrol eden fonksiyon
def check_model_availability(model_name):
    """Ollama modelinin varlığını kontrol eder"""
    try:
        result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
        if result.returncode == 0:
            return model_name in result.stdout
        return False
    except Exception:
        return False

# Embeddings oluştur - Optimize edilmiş model yapılandırması ve önbellek desteği
def create_embeddings(model_name="nomic-embed-text", use_cache=True):
    """
    Embedding modelini oluşturur, yapılandırır ve önbellek desteği ekler
    
    Args:
        model_name: Kullanılacak model adı ('nomic-embed-text', 'mistral-embed' veya 'mxbai-embed-large')
        use_cache: Önbellek kullanılsın mı
        
    Desteklenen modeller: 'nomic-embed-text', 'mistral-embed' veya 'mxbai-embed-large'
    """
    print(f"Embedding modeli oluşturuluyor: {model_name}")
    
    # Model varlığını kontrol et
    if not check_model_availability(model_name):
        print(f"UYARI: {model_name} modeli bulunamadı. Alternatif modelleri kontrol ediliyor...")
        
        # Alternatif modelleri dene - modelleri kaliteye göre sırala
        alternatives = ["nomic-embed-text", "mxbai-embed-large", "mistral-embed"]
        for alt_model in alternatives:
            if check_model_availability(alt_model) and alt_model != model_name:
                print(f"Alternatif model bulundu: {alt_model}")
                model_name = alt_model
                break
        else:
            print("UYARI: Hiçbir embedding modeli bulunamadı. 'nomic-embed-text' kullanılmaya çalışılacak.")
            model_name = "nomic-embed-text"
    
    # CPU ve RAM durumunu kontrol et
    cpu_count = psutil.cpu_count(logical=False)
    ram_gb = psutil.virtual_memory().total / (1024*1024*1024)
    
    # Kaynaklara göre uygun thread sayısı belirle
    if cpu_count >= 12 and ram_gb >= 32:
        num_thread = 12
    elif cpu_count >= 8 and ram_gb >= 16:
        num_thread = 8
    elif cpu_count >= 4 and ram_gb >= 8: 
        num_thread = 4
    else:
        num_thread = 2
        
    print(f"Sistem kaynakları: {cpu_count} çekirdek, {ram_gb:.1f} GB RAM. {num_thread} thread kullanılacak.")
    
    # Önbellek dizini oluştur
    embedding_cache_dir = "embedding_cache"
    if use_cache and not os.path.exists(embedding_cache_dir):
        try:
            os.makedirs(embedding_cache_dir)
            print(f"Önbellek dizini oluşturuldu: {embedding_cache_dir}")
        except Exception as e:
            print(f"Önbellek dizini oluşturulamadı: {e}")
            use_cache = False
    
    # Embedding modelini yapılandırma optimizasyonları
    # Modele göre uygun ayarları belirle
    if model_name == "nomic-embed-text":
        embedding_model = OllamaEmbeddings(
            model=model_name,        # Nomic AI'nin yüksek performanslı embedding modeli
            temperature=0.0,         # Tutarlı gömme için sıcaklığı 0 yap
            num_ctx=4096,            # Daha büyük içerik penceresi 
            num_thread=num_thread,   # Thread sayısı
        )
    elif model_name == "mxbai-embed-large":
        # MxbAI modeli için en iyi ayarlar
        embedding_model = OllamaEmbeddings(
            model=model_name,
            temperature=0.0,
            num_ctx=8192,          # Bu model için daha büyük bağlam penceresi
            num_thread=num_thread,
            num_gpu=1,             # GPU kullanımını etkinleştir (varsa)
        )
    elif model_name == "mistral-embed":
        embedding_model = OllamaEmbeddings(
            model=model_name,
            temperature=0.0,
            num_ctx=4096,          # Orta seviye bağlam penceresi
            num_thread=num_thread,
        )
    else:
        print(f"UYARI: Bilinmeyen model: {model_name}, varsayılan ayarlar kullanılacak")
        embedding_model = OllamaEmbeddings(
            model="nomic-embed-text",
            temperature=0.0,
            num_ctx=2048,
            num_thread=num_thread,
        )
    
    # Önbellek sistemi ekleme - embedding işlemlerini hızlandırmak için
    if use_cache:
        try:
            import hashlib
            import pickle
            import time
            
            # Orjinal embed_documents fonksiyonunu sakla
            original_embed_documents = embedding_model.embed_documents
            original_embed_query = embedding_model.embed_query
            
            # Önbellekli embed_documents fonksiyonu
            def cached_embed_documents(texts):
                """Önbellekli doküman gömme fonksiyonu"""
                results = []
                uncached_texts = []
                uncached_indices = []
                
                # Önbellekteki dokümanları kontrol et
                for i, text in enumerate(texts):
                    # Doküman içeriğinden hash oluştur
                    text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
                    cache_path = os.path.join(embedding_cache_dir, f"doc_{text_hash}.pkl")
                    
                    if os.path.exists(cache_path):
                        # Önbellekten yükle
                        try:
                            with open(cache_path, 'rb') as f:
                                embedding = pickle.load(f)
                            results.append(embedding)
                        except Exception:
                            # Önbellekten yüklenemezse yeniden hesapla
                            uncached_texts.append(text)
                            uncached_indices.append(i)
                    else:
                        uncached_texts.append(text)
                        uncached_indices.append(i)
                
                # Önbellekte olmayan dokümanları göm
                if uncached_texts:
                    uncached_embeddings = original_embed_documents(uncached_texts)
                    
                    # Sonuçları birleştir ve önbelleğe kaydet
                    for j, (idx, embedding) in enumerate(zip(uncached_indices, uncached_embeddings)):
                        # Doküman içeriğinden hash oluştur
                        text_hash = hashlib.md5(uncached_texts[j].encode('utf-8')).hexdigest()
                        cache_path = os.path.join(embedding_cache_dir, f"doc_{text_hash}.pkl")
                        
                        try:
                            with open(cache_path, 'wb') as f:
                                pickle.dump(embedding, f)
                        except Exception:
                            # Önbelleğe kaydedilemezse devam et
                            pass
                        
                        # Sonuç listesinde doğru konuma ekle
                        results.insert(idx, embedding)
                
                return results
            
            # Önbellekli embed_query fonksiyonu
            def cached_embed_query(text):
                """Önbellekli sorgu gömme fonksiyonu"""
                # Sorgu içeriğinden hash oluştur
                text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
                cache_path = os.path.join(embedding_cache_dir, f"query_{text_hash}.pkl")
                
                if os.path.exists(cache_path):
                    # Önbellekten yükle
                    try:
                        with open(cache_path, 'rb') as f:
                            embedding = pickle.load(f)
                        return embedding
                    except Exception:
                        # Önbellekten yüklenemezse yeniden hesapla
                        pass
                
                # Yeni gömme hesapla
                embedding = original_embed_query(text)
                
                # Önbelleğe kaydet
                try:
                    with open(cache_path, 'wb') as f:
                        pickle.dump(embedding, f)
                except Exception:
                    # Önbelleğe kaydedilemezse devam et
                    pass
                
                return embedding
            
            # Fonksiyonları değiştir
            embedding_model.embed_documents = cached_embed_documents
            embedding_model.embed_query = cached_embed_query
            
            print("Embedding önbellek sistemi etkinleştirildi.")
            
        except Exception as e:
            print(f"Önbellek sistemi etkinleştirilemedi: {e}")
    
    return embedding_model

# Embedding modelini oluştur
embeddings = create_embeddings("nomic-embed-text")

# Türkçe için özel metin temizleme fonksiyonu
def clean_turkish_text(text):
    """Türkçe metni temizler ve gelişmiş normalizasyon uygular"""
    if not text or not isinstance(text, str):
        return ""
        
    # Gereksiz boşlukları kaldır
    text = re.sub(r'\s+', ' ', text)
    
    # URL'leri temizle veya basitleştir
    text = re.sub(r'https?://\S+', '[URL]', text)
    
    # Birden fazla noktalama işaretlerini normalleştir
    text = re.sub(r'[.]{2,}', '...', text)
    text = re.sub(r'[!]{2,}', '!', text)
    text = re.sub(r'[?]{2,}', '?', text)
    
    # Emojileri ve özel karakterleri temizle ama Türkçe karakterleri koru
    text = re.sub(r'[^\w\s\.,?!;:\-\'\"()çğıöşüÇĞİÖŞÜ]', '', text)
    
    # Rakamları standardize et (telefon numaraları, tarihler vb.)
    # Telefon numaraları: 5xx xxx xx xx formatına dönüştür
    text = re.sub(r'(\+90|0)?\s*?5\d{2}\s*?\d{3}\s*?\d{2}\s*?\d{2}', '5XX XXX XX XX', text)
    
    # Kelimeler arasındaki tek harfleri temizle (genellikle hata)
    text = re.sub(r'\s[bcdfghjklmnpqrstvwxyzçğşBCDFGHJKLMNPQRSTVWXYZÇĞŞ]\s', ' ', text)
    
    # Fazla tekrarlayan harfleri normalleştir (örn: "çooook" -> "çok")
    text = re.sub(r'([bcdfghjklmnpqrstvwxyzçğşBCDFGHJKLMNPQRSTVWXYZÇĞŞ])\1{2,}', r'\1', text)
    
    return text.strip()

def normalize_time_format(time_str):
    """Zaman formatını standartlaştırır (00:00:00 formatına dönüştürür)"""
    if not time_str or not isinstance(time_str, str):
        return "00:00:00"
    
    # Boşlukları temizle
    time_str = time_str.strip()
    
    # Eğer format zaten doğruysa (00:00:00)
    if re.match(r'^\d{2}:\d{2}:\d{2}$', time_str):
        return time_str
    
    # 0:00:00 formatındaysa başa 0 ekle
    if re.match(r'^\d:\d{2}:\d{2}$', time_str):
        return f"0{time_str}"
    
    # xx:xx formatındaysa başına 00: ekle
    if re.match(r'^\d{1,2}:\d{2}$', time_str):
        return f"00:{time_str}"
    
    # Diğer durumlar - varsayılan değer döndür
    return "00:00:00"

def parse_transcript(content):
    """Konuşma yapısını parse et - Daha esnek regex desenleriyle"""
    if not content or not isinstance(content, str):
        return []
        
    # Desteklenen format desenleri (çeşitli formatları destekler)
    patterns = [
        # Standart format: 0:00:00 - 0:00:44 Speaker A: Konuşma (başta sıfır olabilir veya olmayabilir)
        r"(\d+:\d+:\d+)\s*-\s*(\d+:\d+:\d+)\s*Speaker\s*([A-Za-z0-9]+):\s*(.*?)(?=\d+:\d+:\d+\s*-|\Z)",
        
        # Alt format: 00:00:00 Konuşmacı: Konuşma
        r"(\d+:\d+:\d+)\s*([A-Za-z0-9]+):\s*(.*?)(?=\d+:\d+:\d+|\Z)",
        
        # Başka bir format: [00:00:00] Speaker X: Konuşma
        r"\[(\d+:\d+:\d+)\]\s*([A-Za-z0-9]+):\s*(.*?)(?=\[|\Z)"
    ]
    
    conversations = []
    
    # Her bir deseni sırayla dene
    for pattern_idx, pattern in enumerate(patterns):
        matches = list(re.finditer(pattern, content, re.DOTALL))
        
        # Eğer eşleşme bulunduysa bu deseni kullan
        if matches:
            print(f"Transkript deseni {pattern_idx+1} kullanılıyor. {len(matches)} konuşma bulundu.")
            
            for match in matches:
                if pattern_idx == 0:  # Standart format
                    start_time = normalize_time_format(match.group(1))
                    end_time = normalize_time_format(match.group(2))
                    speaker = match.group(3)
                    content = match.group(4).strip()
                elif pattern_idx == 1:  # Alt format
                    start_time = normalize_time_format(match.group(1))
                    end_time = start_time  # Aynı zaman
                    speaker = match.group(2)
                    content = match.group(3).strip()
                else:  # Diğer format
                    start_time = normalize_time_format(match.group(1))
                    end_time = start_time  # Aynı zaman
                    speaker = match.group(2)
                    content = match.group(3).strip()
                
                # Boş içeriği filtrele
                if not content:
                    continue
                    
                # Metni temizle
                content = clean_turkish_text(content)
                
                # Hala içerik varsa ekle
                if content:
                    conversations.append({
                        "time": f"{start_time} - {end_time}",
                        "speaker": speaker,
                        "content": content
                    })
            
            # Eğer eşleşme bulduysan diğer desenleri deneme
            if conversations:
                break
    
    # Hiçbir desen eşleşmediyse
    if not conversations:
        print("UYARI: Transkript deseni bulunamadı. Metin tam metinden ayrıştırılacak.")
        # Metin içindeki her bir satırı konuşma olarak kabul et
        lines = content.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if len(line) > 10:  # Kısa satırları atla
                conversations.append({
                    "time": "00:00:00 - 00:00:00",
                    "speaker": "Unknown",
                    "content": clean_turkish_text(line)
                })
    
    return conversations

def calculate_time_difference(start_time, end_time):
    """İki zaman arasındaki farkı saniye cinsinden hesaplar"""
    def time_to_seconds(time_str):
        h, m, s = map(int, time_str.split(':'))
        return h * 3600 + m * 60 + s
        
    start_seconds = time_to_seconds(start_time)
    end_seconds = time_to_seconds(end_time)
    return end_seconds - start_seconds

# Dinamik chunk_size ve overlap hesaplama fonksiyonu
def calculate_dynamic_chunking(content, base_chunk_size=350, base_overlap=40):
    """
    İçerik uzunluğuna ve karmaşıklığına göre dinamik chunk_size ve overlap hesaplar
    
    Args:
        content: İşlenecek metin içeriği
        base_chunk_size: Temel chunk boyutu
        base_overlap: Temel örtüşme boyutu
    
    Returns:
        tuple: (chunk_size, chunk_overlap)
    """
    # İçerik uzunluğu
    content_length = len(content)
    
    # Cümle sayısı (kabaca noktalama işaretlerine göre)
    sentences = re.split(r'[.!?]+', content)
    sentence_count = len([s for s in sentences if len(s.strip()) > 0])
    
    # Ortalama cümle uzunluğu
    if sentence_count > 0:
        avg_sentence_length = content_length / sentence_count
    else:
        avg_sentence_length = 20  # Varsayılan değer
    
    # İçerik karmaşıklığı göstergeleri
    complexity_indicators = {
        'uzun_cümleler': sum(1 for s in sentences if len(s.split()) > 20) / max(sentence_count, 1),
        'teknik_terimler': len(re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', content)) / max(content_length / 100, 1),
        'noktalama_yoğunluğu': len(re.findall(r'[,;:\(\)\[\]\{\}]', content)) / max(content_length / 100, 1)
    }
    
    # Karmaşıklık skoru (0-1 arası)
    complexity_score = (
        0.4 * complexity_indicators['uzun_cümleler'] + 
        0.3 * complexity_indicators['teknik_terimler'] + 
        0.3 * complexity_indicators['noktalama_yoğunluğu']
    )
    complexity_score = min(max(complexity_score, 0), 1)  # 0-1 aralığına sınırla
    
    # İçerik uzunluğuna göre ayarlama
    length_factor = 1.0
    if content_length > 10000:  # Uzun dokümanlar
        length_factor = 1.3
    elif content_length < 1000:  # Kısa dokümanlar
        length_factor = 0.8
    
    # Cümle uzunluğuna göre ayarlama
    sentence_factor = 1.0
    if avg_sentence_length > 30:  # Uzun cümleler
        sentence_factor = 1.2
    elif avg_sentence_length < 10:  # Kısa cümleler
        sentence_factor = 0.9
    
    # Dinamik chunk_size hesaplama
    chunk_size = int(base_chunk_size * length_factor * sentence_factor * (1 + 0.5 * complexity_score))
    
    # Dinamik overlap hesaplama - karmaşıklık arttıkça overlap artar
    overlap_ratio = 0.12 + (0.08 * complexity_score)  # %12-%20 arası
    chunk_overlap = int(chunk_size * overlap_ratio)
      # Minimum ve maksimum değerleri kontrol et
    chunk_size = max(500, min(chunk_size, 1000))  # 500-1000 arası (daha büyük chunks)
    chunk_overlap = max(100, min(chunk_overlap, 250))  # 100-250 arası (daha büyük overlap)
    
    print(f"Dinamik chunking: size={chunk_size}, overlap={chunk_overlap} (Karmaşıklık skoru: {complexity_score:.2f})")
    return chunk_size, chunk_overlap

def load_transcripts(chunk_size=800, chunk_overlap=180, parallelize=True, dynamic_chunking=True):
    """
    Transcripts klasöründeki tüm txt dosyalarını yükler ve işler
    Args:
        chunk_size: Metin parçalarının boyutu (varsayılan: 800)
        chunk_overlap: Parçalar arası örtüşme (varsayılan: 180)
        parallelize: Paralel işleme yapılsın mı
        dynamic_chunking: Dinamik chunk boyutu kullanılsın mı
    """
    transcript_docs = []
    transcript_dir = "transcripts"
    
    # Metin bölme stratejisini oluştur - Optimize edilmiş ayarlar
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,        # Türkçe için optimize edilmiş boyut
        chunk_overlap=chunk_overlap,  # Türkçe için optimize edilmiş örtüşme
        length_function=len,
        separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""]
    )
    
    if not os.path.exists(transcript_dir):
        print(f"HATA: {transcript_dir} klasörü bulunamadı.")
        print("Lütfen 'transcripts' adında bir klasör oluşturun ve içine txt dosyalarını ekleyin.")
        return []
    
    print(f"'{transcript_dir}' klasöründeki dosyalar taranıyor...")
    
    # Önce dosyaların listesini al
    files = [f for f in os.listdir(transcript_dir) if f.endswith(".txt") and not f.startswith('.')]
    total_files = len(files)
    
    if total_files == 0:
        print("UYARI: Hiç transcript dosyası bulunamadı.")
        print("Lütfen 'transcripts' klasörüne .txt uzantılı dosyalar ekleyin.")
        return []
    
    print(f"Toplam {total_files} transcript dosyası bulundu.")
    
    # Maksimum thread sayısı belirle (CPU çekirdek sayısı veya dosya sayısı, hangisi daha azsa)
    max_workers = min(os.cpu_count() or 2, total_files)
    
    # Fonksiyon: Tek bir dosyayı yükle ve işle
    def process_file(filename):
        file_path = os.path.join(transcript_dir, filename)
        file_docs = []
        
        # Metadata'ya dosya adını ekle
        metadata = {
            "source": filename,
            "file_path": file_path,
            "file_type": "transcript",
        }
        
        # Dosyayı yükle
        try:
            print(f"Dosya işleniyor: {filename}")
            loader = TextLoader(file_path, encoding="utf-8")  # UTF-8 encoding
            docs = loader.load()
            
            # Her bir dokümanı işle ve konuşma yapısını ayır
            for doc in docs:
                content = doc.page_content
                
                # Dinamik chunking kullanılıyorsa, dosya içeriğine göre chunk_size ve overlap ayarla
                local_chunk_size = chunk_size
                local_chunk_overlap = chunk_overlap
                
                if dynamic_chunking:
                    local_chunk_size, local_chunk_overlap = calculate_dynamic_chunking(content, chunk_size, chunk_overlap)
                    # Dosyaya özel text_splitter oluştur
                    text_splitter_local = RecursiveCharacterTextSplitter(
                        chunk_size=local_chunk_size,
                        chunk_overlap=local_chunk_overlap,
                        length_function=len,
                        separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""]
                    )
                else:
                    text_splitter_local = text_splitter
                
                # Konuşmaları parçala
                conversations = parse_transcript(content)
                
                print(f"{filename} içinde {len(conversations)} konuşma bulundu")
                
                # Konuşmaların toplam süresini hesapla
                total_duration = 0
                for conv in conversations:
                    time_parts = conv["time"].split(" - ")
                    if len(time_parts) == 2:
                        try:
                            duration = calculate_time_difference(time_parts[0], time_parts[1])
                            total_duration += duration
                        except:
                            pass
                
                print(f"Toplam konuşma süresi: {total_duration//60} dakika {total_duration%60} saniye")
                
                # Her bir konuşmayı ayrı bir doküman olarak ekle
                for i, conv in enumerate(conversations):
                    # Metadata'yı her konuşma için güncelle
                    conv_metadata = metadata.copy()
                    
                    # Zamanı ayrıştır
                    time_parts = conv["time"].split(" - ")
                    start_time = time_parts[0] if len(time_parts) > 0 else "00:00:00"
                    end_time = time_parts[1] if len(time_parts) > 1 else "00:00:00"
                    
                    conv_metadata.update({
                        "time": conv["time"],
                        "speaker": conv["speaker"],
                        "conversation_id": i,
                        "start_time": start_time,
                        "end_time": end_time,
                        "title": f"{filename} - Konuşma {i+1} - {conv['speaker']} ({conv['time']})",
                        "language": "Turkish",
                        "content_length": len(conv["content"])
                    })
                    
                    # Konuşma içeriğini formatlı şekilde oluştur
                    content = f"Time: {conv['time']}\nSpeaker: {conv['speaker']}\nContent: {conv['content']}"
                    
                    # İçerik çok kısaysa atla (gürültü olabilir)
                    if len(conv["content"]) < 10:
                        continue
                    
                    # Dokümanı böl ve her parçayı ayrı ayrı ekle
                    splits = text_splitter_local.create_documents(
                        texts=[content],
                        metadatas=[conv_metadata]
                    )
                    file_docs.extend(splits)
        
        except Exception as e:
            print(f"HATA: {filename} dosyası yüklenirken bir sorun oluştu: {e}")
            return []
            
        return file_docs
    
    start_time = time.time()
    processed_count = 0
    
    # Paralel işleme yapılsın mı?
    if parallelize and max_workers > 1:
        print(f"Dosyalar {max_workers} thread ile paralel işlenecek...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Dosyaları paralel olarak işle
            futures = {executor.submit(process_file, filename): filename for filename in files}
            
            # Sonuçları topla
            for future in concurrent.futures.as_completed(futures):
                filename = futures[future]
                try:
                    result = future.result()
                    processed_count += 1
                    transcript_docs.extend(result)
                    print(f"İşlenen dosyalar: {processed_count}/{total_files} - {filename} tamamlandı.")
                except Exception as e:
                    print(f"Dosya işlenirken hata: {filename} - {e}")
    else:
        # Sıralı (tek thread) işleme
        print("Dosyalar sıralı olarak işlenecek...")
        for filename in files:
            result = process_file(filename)
            transcript_docs.extend(result)
            processed_count += 1
            print(f"İşlenen dosyalar: {processed_count}/{total_files}")
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    print(f"Tüm dosyalar işlendi. Toplam süre: {processing_time:.1f} saniye")
    print(f"Toplam {len(transcript_docs)} doküman parçası yüklendi")
    
    return transcript_docs

def create_vectorstore(collection_name="turkce_transkript", force_recreate=False, chunk_size=800, chunk_overlap=180, dynamic_chunking=True):
    """
    Vektör veritabanını oluşturur veya günceller
    Args:
        collection_name: Koleksiyonun adı
        force_recreate: True ise varolan veritabanını siler ve yeniden oluşturur
        chunk_size: Metin parçalarının boyutu (varsayılan: 800)
        chunk_overlap: Parçalar arası örtüşme (varsayılan: 180)
        dynamic_chunking: Dinamik chunk boyutu kullanılsın mı
    """
    start_time = time.time()
    print("Vektör veritabanı oluşturuluyor...")
    
    # Veritabanını yeniden oluşturmak için kontrol et
    if force_recreate and os.path.exists("chrome_langchain_db"):
        import shutil
        print("Mevcut vektör veritabanı siliniyor...")
        shutil.rmtree("chrome_langchain_db")
        print("Vektör veritabanı silindi. Yeniden oluşturuluyor...")
    
    # Transcript verilerini yükle
    transcript_docs = load_transcripts(chunk_size=chunk_size, chunk_overlap=chunk_overlap, dynamic_chunking=dynamic_chunking)
    
    if not transcript_docs:
        print("HATA: Vektör veritabanı oluşturulamadı çünkü doküman bulunamadı.")
        return None
    
    # İlerleme göstergesi için toplam doküman sayısı
    total_docs = len(transcript_docs)
    print(f"Toplam {total_docs} doküman vektörleştirilecek...")
    
    # İşleme performansı için parçalara ayırarak işleme
    batch_size = 2000  # Her seferde işlenecek doküman sayısı
    all_batches = [transcript_docs[i:i + batch_size] for i in range(0, len(transcript_docs), batch_size)]
    
    # İlk batch ile veritabanını oluştur
    print(f"İlk {min(batch_size, len(transcript_docs))} doküman vektörleştiriliyor...")
    
    # Vektör veritabanı yapılandırması
    vectorstore = Chroma.from_documents(
        documents=all_batches[0],
        embedding=embeddings,
        persist_directory="chrome_langchain_db",
        collection_name=collection_name,
        collection_metadata={
            "hnsw:space": "cosine",           # Benzerlik metriği
            "hnsw:construction_ef": 100,      # İnşa kalite parametresi
            "hnsw:search_ef": 50,             # Arama kalite parametresi
            "hnsw:M": 16,                     # Her düğüm başına bağlantı sayısı
            "chroma_db:version": "2.0",       # Veritabanı sürümü
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"), # Oluşturma tarihi
            "document_language": "Turkish"    # Belge dili
        }
    )
    
    # Kalan batch'leri ekle (eğer varsa)
    remaining_batches = all_batches[1:]
    for i, batch in enumerate(remaining_batches, 1):
        print(f"Batch {i+1}/{len(all_batches)} vektörleştiriliyor... ({len(batch)} doküman)")
        vectorstore.add_documents(documents=batch)
    
    # Not: Yeni versiyonlarda persist() metodu olmayabilir
    # vectorstore.persist() metodu yerine direkt olarak diske kaydedilir
    
    end_time = time.time()
    print(f"Vektör veritabanı oluşturuldu. İşlem süresi: {end_time - start_time:.2f} saniye")
    print(f"Toplam {total_docs} doküman parçası vektörleştirildi.")
    
    return vectorstore

def load_vectorstore(collection_name="turkce_transkript"):
    """
    Var olan vektör veritabanını yükler
    Args:
        collection_name: Koleksiyonun adı
    """
    # Vektör veritabanı var mı kontrol et
    if not os.path.exists("chrome_langchain_db"):
        print("UYARI: Vektör veritabanı bulunamadı. Yeni veritabanı oluşturuluyor...")
        return create_vectorstore(collection_name=collection_name)
    
    # Var olan vektör veritabanını yükle
    print("Var olan vektör veritabanı yükleniyor...")
    try:
        vectorstore = Chroma(
            persist_directory="chrome_langchain_db",
            embedding_function=embeddings,
            collection_name=collection_name,
            collection_metadata={
                "hnsw:space": "cosine",           # Benzerlik metriği
                "hnsw:construction_ef": 100,      # İnşa kalite parametresi
                "hnsw:search_ef": 50,             # Arama kalite parametresi
                "hnsw:M": 16                      # Her düğüm başına bağlantı sayısı
            }
        )
        
        # Veritabanı boyutunu kontrol et
        collection_count = vectorstore._collection.count()
        if collection_count == 0:
            print("UYARI: Vektör veritabanı boş. Yeni vektör veritabanı oluşturuluyor...")
            return create_vectorstore(collection_name=collection_name)
            
        print(f"Vektör veritabanı başarıyla yüklendi. {collection_count} doküman parçası mevcut.")
        
        # Veritabanı metadata'sını görüntüle
        try:
            metadata = vectorstore._collection.get()
            if "collection_metadata" in metadata and metadata["collection_metadata"]:
                version = metadata["collection_metadata"].get("chroma_db:version", "Bilinmiyor")
                created_at = metadata["collection_metadata"].get("created_at", "Bilinmiyor")
                print(f"Veritabanı Sürümü: {version}, Oluşturma Tarihi: {created_at}")
        except:
            pass
            
        return vectorstore
        
    except Exception as e:
        print(f"HATA: Vektör veritabanı yüklenirken bir sorun oluştu: {e}")
        print("Vektör veritabanı yeniden oluşturuluyor...")
        # Veritabanını temizle ve yeniden oluştur
        import shutil
        if os.path.exists("chrome_langchain_db"):
            shutil.rmtree("chrome_langchain_db")
        return create_vectorstore(collection_name=collection_name)

# Bu dosya doğrudan çalıştırıldığında vektör veritabanı oluştur
if __name__ == "__main__":
    import argparse
    
    # Komut satırı argümanlarını ayarla
    parser = argparse.ArgumentParser(description="Türkçe Transkript Vektör Veritabanı Oluşturma Aracı")
    parser.add_argument("--force", action="store_true", help="Mevcut veritabanını silip yeniden oluştur")
    parser.add_argument("--collection", type=str, default="turkce_transkript", help="Koleksiyon adı")
    parser.add_argument("--chunk-size", type=int, default=350, help="Metin parça boyutu")
    parser.add_argument("--chunk-overlap", type=int, default=40, help="Metin parça örtüşmesi")
    parser.add_argument("--model", type=str, default="nomic-embed-text", help="Kullanılacak embedding modeli")
    parser.add_argument("--sequential", action="store_true", help="Paralel işleme yerine sıralı işleme kullan")
    parser.add_argument("--dynamic", action="store_true", help="Dinamik chunk boyutu kullanılsın mı")
    
    args = parser.parse_args()
    
    print("=== TÜRKÇE TRANSKRİPT VEKTÖR VERİTABANI OLUŞTURMA ===")
    print("Bu işlem tüm belgeleri okuyup vektör veritabanına dönüştürecek.")
    print("İşlem, belge sayısına göre zaman alabilir.")
    print("İşlem tamamlandıktan sonra main.py'yi çalıştırarak hızlı sorgulama yapabilirsiniz.")
    print("=" * 60)
    
    # Argümanları görüntüle
    print(f"Kullanılan ayarlar:")
    print(f"- Koleksiyon adı: {args.collection}")
    print(f"- Zorla yeniden oluştur: {args.force}")
    print(f"- Metin parça boyutu: {args.chunk_size}")
    print(f"- Metin parça örtüşmesi: {args.chunk_overlap}")
    print(f"- Embedding modeli: {args.model}")
    print(f"- Paralel işleme: {not args.sequential}")
    print(f"- Dinamik chunking: {args.dynamic}")
    print("=" * 60)
    
    # Embedding modelini oluştur (eğer farklı model seçildiyse)
    if args.model != "nomic-embed-text":
        # embeddings değişkeni daha önce tanımlandığı için global kullanmıyoruz
        embeddings = create_embeddings(args.model)
    
    # Vektör veritabanını oluştur
    create_vectorstore(
        collection_name=args.collection,
        force_recreate=args.force,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        dynamic_chunking=args.dynamic
    )
    
    print("\n" + "=" * 60)
    print("Vektör veritabanı başarıyla oluşturuldu!")
    print("Artık main.py'yi çalıştırarak hızlı sorgu yapabilirsiniz.")
    print("Not: Yeni dosyalar eklerseniz, bu dosyayı tekrar çalıştırarak vektör veritabanını güncelleyin.")
    print("=" * 60)
# Import edildiğinde hazır bir retriever objesi sağlar
else:
    # Vektör veritabanını yükle
    vectorstore = load_vectorstore()
    
    # Retriever'ı oluştur - Optimize edilmiş parametreler
    retriever = vectorstore.as_retriever(
        search_type="mmr",        # Maximum Marginal Relevance - hem alakalı hem de çeşitli sonuçlar
        search_kwargs={
            "k": 8,                # Transkriptlerden 8 en alakalı sonuç
            "fetch_k": 30,         # Daha az aday (daha hızlı işleme)
            "lambda_mult": 0.7,    # Çeşitlilik için lambda değeri düşürüldü
            "filter": None         # Gerektiğinde filtre eklemek için hazır
        }
    )
    
    # Doğrudan çağrılabilir sorgulama fonksiyonu
    def search_by_keywords(keywords, limit=5):
        """
        Anahtar kelimelere göre vektör veritabanında arama yapar.
        Args:
            keywords: Aranacak anahtar kelimeler listesi veya string
            limit: Döndürülecek maksimum sonuç sayısı
        Returns:
            Metin parçalarının listesi
        """
        if isinstance(keywords, str):
            keywords = keywords.split()
            
        # Anahtar kelimeleri birleştir
        query = " ".join(keywords)
        
        # Vektör veritabanında ara
        results = retriever.invoke(query)
        
        # Sonuçları limit ile sınırla
        return results[:limit]