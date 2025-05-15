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

# Türkçe NLP için gerekli bileşenleri yükle
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

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

# Embeddings oluştur - Gelişmiş ücretsiz model yapılandırması
def create_embeddings(model_name="nomic-embed-text"):
    """
    Embedding modelini oluşturur ve yapılandırır
    Desteklenen modeller: 'nomic-embed-text', 'mistral-embed' veya 'llama3-embed'
    """
    print(f"Embedding modeli oluşturuluyor: {model_name}")
    
    # CPU ve RAM durumunu kontrol et
    cpu_count = psutil.cpu_count(logical=False)
    ram_gb = psutil.virtual_memory().total / (1024*1024*1024)
    
    # Kaynaklara göre uygun thread sayısı belirle
    if cpu_count >= 8 and ram_gb >= 16:
        num_thread = 8
    elif cpu_count >= 4 and ram_gb >= 8: 
        num_thread = 4
    else:
        num_thread = 2
        
    print(f"Sistem kaynakları: {cpu_count} çekirdek, {ram_gb:.1f} GB RAM. {num_thread} thread kullanılacak.")
        
    # Modele göre uygun ayarları belirle
    if model_name == "nomic-embed-text":
        embedding_model = OllamaEmbeddings(
            model=model_name,        # Nomic AI'nin yüksek performanslı embedding modeli
            temperature=0.0,         # Tutarlı gömme için sıcaklığı 0 yap
            num_ctx=4096,            # Daha büyük içerik penceresi 
            num_thread=num_thread,   # Thread sayısı
        )
    elif model_name in ["mistral-embed", "llama3-embed"]:
        embedding_model = OllamaEmbeddings(
            model=model_name,
            temperature=0.0,
            num_ctx=8192,          # Bu modeller için daha büyük bağlam penceresi
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
        
    # Eğer format zaten doğruysa (00:00:00)
    if re.match(r'^\d{2}:\d{2}:\d{2}$', time_str):
        return time_str
        
    # xx:xx formatındaysa başına 00: ekle
    if re.match(r'^\d{2}:\d{2}$', time_str):
        return f"00:{time_str}"
        
    # Diğer durumlar - varsayılan değer döndür
    return "00:00:00"

def parse_transcript(content):
    """Konuşma yapısını parse et - Daha esnek regex desenleriyle"""
    if not content or not isinstance(content, str):
        return []
        
    # Desteklenen format desenleri (çeşitli formatları destekler)
    patterns = [
        # Standart format: 00:00:00 - 00:00:00 Speaker X: Konuşma
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

def load_transcripts(chunk_size=350, chunk_overlap=40, parallelize=True):
    """
    Transcripts klasöründeki tüm txt dosyalarını yükler ve işler
    Args:
        chunk_size: Metin parçalarının boyutu
        chunk_overlap: Parçalar arası örtüşme
        parallelize: Paralel işleme yapılsın mı
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
                    splits = text_splitter.create_documents(
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

def create_vectorstore(collection_name="turkce_transkript", force_recreate=False, chunk_size=350, chunk_overlap=40):
    """
    Vektör veritabanını oluşturur veya günceller
    Args:
        collection_name: Koleksiyonun adı
        force_recreate: True ise varolan veritabanını siler ve yeniden oluşturur
        chunk_size: Metin parçalarının boyutu
        chunk_overlap: Parçalar arası örtüşme
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
    transcript_docs = load_transcripts(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    
    if not transcript_docs:
        print("HATA: Vektör veritabanı oluşturulamadı çünkü doküman bulunamadı.")
        return None
    
    # İlerleme göstergesi için toplam doküman sayısı
    total_docs = len(transcript_docs)
    print(f"Toplam {total_docs} doküman vektörleştirilecek...")
    
    # İşleme performansı için parçalara ayırarak işleme
    batch_size = 500  # Her seferde işlenecek doküman sayısı
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
        chunk_overlap=args.chunk_overlap
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
            "k": 12,               # Türkçe için optimize edildi (daha az ama daha alakalı sonuçlar)
            "fetch_k": 40,         # Daha az aday (daha hızlı işleme)
            "lambda_mult": 0.8,    # Türkçe için optimize edildi (daha fazla alaka ağırlığı)
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