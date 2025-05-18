#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Türkçe Metin Analizi Araçları
Bu modül, Türkçe transkriptlerin analizi için gelişmiş metin işleme araçları sağlar.
"""

import re
import math
import string
from collections import Counter, defaultdict

class TextAnalyzer:
    """Türkçe metinler için gelişmiş analiz araçları sağlar"""
    
    def __init__(self):
        """Metin analizcisini başlat ve Türkçe stopwords tanımla"""
        # Genişletilmiş Türkçe stopwords listesi
        self.stopwords = set([
            'acaba', 'altı', 'altmış', 'ama', 'ancak', 'arada', 'artık', 'asla', 
            'aslında', 'ayrıca', 'bana', 'bazen', 'bazı', 'bazıları', 'belki', 
            'ben', 'benden', 'beni', 'benim', 'beş', 'bile', 'bin', 'bir', 'biraz', 
            'birçoğu', 'birçok', 'biri', 'birisi', 'birkaç', 'birşey', 'biz', 'bizden', 
            'bize', 'bizi', 'bizim', 'böyle', 'böylece', 'bu', 'buna', 'bunda', 'bundan', 
            'bunlar', 'bunları', 'bunların', 'bunu', 'bunun', 'burada', 'çok', 'çünkü', 
            'da', 'daha', 'dahi', 'dan', 'de', 'defa', 'değil', 'diğer', 'diğeri', 
            'diğerleri', 'diye', 'doksan', 'dokuz', 'dolayı', 'dolayısıyla', 'dört', 
            'e', 'elli', 'en', 'etmesi', 'evet', 'fakat', 'falan', 'filan', 'gene', 
            'gereği', 'gerek', 'gibi', 'göre', 'hala', 'halde', 'halen', 'hangi', 
            'hangisi', 'hani', 'hatta', 'hem', 'henüz', 'hep', 'hepsi', 'her', 
            'herhangi', 'herkes', 'herkese', 'herkesi', 'herkesin', 'hiç', 'hiçbiri', 
            'hiçbirine', 'hiçbirini', 'i', 'ı', 'için', 'içinde', 'iki', 'ile', 'ilgili', 
            'ise', 'işte', 'itibaren', 'itibariyle', 'kaç', 'kadar', 'kendi', 'kendine', 
            'kendini', 'kendisi', 'kendisine', 'kendisini', 'kez', 'ki', 'kim', 'kime', 
            'kimi', 'kimin', 'kimisi', 'kırk', 'madem', 'mi', 'mı', 'milyar', 'milyon', 
            'mu', 'mü', 'nasıl', 'ne', 'neden', 'nedenle', 'nerde', 'nerede', 'nereye', 
            'nesi', 'neyse', 'niçin', 'nin', 'nın', 'niye', 'nun', 'nün', 'o', 'öbür', 
            'olan', 'olarak', 'oldu', 'olduğu', 'olduklarını', 'olmadı', 'olmadığı', 
            'olmak', 'olması', 'olmayan', 'olmaz', 'olsa', 'olsun', 'olup', 'olur', 
            'olursa', 'oluyor', 'on', 'ön', 'ona', 'önce', 'ondan', 'onlar', 'onlara', 
            'onlardan', 'onları', 'onların', 'onu', 'onun', 'orada', 'öte', 'ötürü', 
            'otuz', 'öyle', 'oysa', 'pek', 'rağmen', 'sana', 'sanki', 'sanma', 'senden', 
            'seni', 'senin', 'siz', 'sizden', 'size', 'sizi', 'sizin', 'son', 'şöyle', 
            'şu', 'şuna', 'şunda', 'şundan', 'şunlar', 'şunu', 'şunun', 'ta', 'tabii', 
            'tam', 'tamam', 'tamamen', 'tarafından', 'ten', 'tüm', 'tümü', 'u', 'ü', 
            'üç', 'un', 'ün', 'üzere', 'var', 'vardı', 've', 'veya', 'ya', 'yani', 
            'yapacak', 'yapılan', 'yapılması', 'yapıyor', 'yapmak', 'yaptı', 'yaptığı', 
            'yaptığını', 'yaptıkları', 'ye', 'yedi', 'yerine', 'yetmiş', 'yi', 'yı', 
            'yine', 'yirmi', 'yoksa', 'yu', 'yüz', 'zaten', 'zira'
        ])
        
        # Kelime kökleri önbelleği
        self.stem_cache = {}
        
        # Türkçe karakter eşleşmeleri
        self.tr_lower_map = {
            ord('I'): 'ı',
            ord('İ'): 'i',
            ord('Ç'): 'ç',
            ord('Ğ'): 'ğ',
            ord('Ö'): 'ö',
            ord('Ş'): 'ş',
            ord('Ü'): 'ü'
        }
    
    def preprocess_text(self, text):
        """
        Türkçe metni temizler, küçük harfe çevirir ve kelimeleri tokenize eder
        
        Args:
            text (str): İşlenecek metin
            
        Returns:
            list: Tokenize edilmiş kelimeler listesi
        """
        if not text or not isinstance(text, str):
            return []
        
        # Küçük harfe çevir (Türkçe karakterleri düzgün şekilde)
        text = text.translate(self.tr_lower_map).lower()
        
        # Noktalama ve gereksiz karakterleri temizle
        text = re.sub(r'[^\wçğıöşüÇĞİÖŞÜ\s]', ' ', text)
        
        # Rakamları temizle
        text = re.sub(r'\d+', ' ', text)
        
        # Fazla boşlukları temizle
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Tokenize et
        tokens = text.split()
        
        # Stopwordleri çıkar
        tokens = [token for token in tokens if token not in self.stopwords and len(token) > 2]
        
        return tokens
    
    def simple_stem(self, word):
        """
        Basit bir Türkçe stemming algoritması
        
        Args:
            word (str): Kökü bulunacak kelime
            
        Returns:
            str: Kelimenin kökü
        """
        # Önbellek kontrolü
        if word in self.stem_cache:
            return self.stem_cache[word]
            
        # Kısa kelimeler için doğrudan döndür
        if len(word) < 4:
            return word
        
        # Yaygın Türkçe sonekleri
        suffixes = [
            'ler', 'lar', 'nin', 'nın', 'nun', 'nün', 'den', 'dan', 'ten', 'tan',
            'in', 'ın', 'un', 'ün', 'a', 'e', 'da', 'de', 'ta', 'te', 'dir', 'tir',
            'dır', 'tır', 'miş', 'mış', 'muş', 'müş', 'ken', 'ile', 'ce', 'ca',
            'leyin', 'layın', 'madan', 'meden', 'arak', 'erek'
        ]
        
        original = word
        for suffix in sorted(suffixes, key=len, reverse=True):
            if word.endswith(suffix) and len(word) > len(suffix) + 2:
                word = word[:-len(suffix)]
                break
        
        # Önbelleğe kaydet
        self.stem_cache[original] = word
        return word
    
    def compute_tfidf(self, documents):
        """
        Belge koleksiyonu için TF-IDF hesaplar
        
        Args:
            documents (list): Metin belgelerinin listesi
            
        Returns:
            dict: Her belge için TF-IDF skorları
        """
        # Tokenize edilmiş belgeler oluştur
        tokenized_docs = [self.preprocess_text(doc) for doc in documents]
        
        # Terim frekanslarını hesapla
        tf_scores = []
        for doc_tokens in tokenized_docs:
            # Her terim için frekans hesapla
            tf_score = {}
            term_count = Counter(doc_tokens)
            doc_len = len(doc_tokens)
            
            for term, count in term_count.items():
                # Normalize edilmiş terim frekansı
                tf_score[term] = count / (doc_len or 1)
            
            tf_scores.append(tf_score)
        
        # IDF hesapla
        idf_scores = {}
        num_docs = len(documents)
        all_terms = set()
        
        for doc_tokens in tokenized_docs:
            unique_terms = set(doc_tokens)
            all_terms.update(unique_terms)
            
            for term in unique_terms:
                if term in idf_scores:
                    idf_scores[term] += 1
                else:
                    idf_scores[term] = 1
        
        # IDF değerlerini hesapla
        for term, count in idf_scores.items():
            idf_scores[term] = math.log(num_docs / count)
        
        # TF-IDF skorlarını hesapla
        tfidf_scores = []
        for tf_score in tf_scores:
            tfidf_score = {}
            for term, tf in tf_score.items():
                tfidf_score[term] = tf * idf_scores.get(term, 0)
            tfidf_scores.append(tfidf_score)
        
        return tfidf_scores
    
    def extract_keywords(self, text, top_n=10):
        """
        Metinden anahtar kelimeleri çıkarır
        
        Args:
            text (str): Anahtar kelimelerin çıkarılacağı metin
            top_n (int): Döndürülecek maksimum kelime sayısı
            
        Returns:
            list: (kelime, skor) tuple'larından oluşan liste
        """
        # Metni tokenize et
        tokens = self.preprocess_text(text)
        
        # Kök bulma işlemi
        stemmed_tokens = [self.simple_stem(token) for token in tokens]
        
        # Frekans hesapla
        freq = Counter(stemmed_tokens)
        
        # Metindeki toplam kelime sayısı
        total_words = len(stemmed_tokens)
        
        # Normalize edilmiş skor hesapla
        scores = {word: (count / total_words) * math.log(count + 1) 
                 for word, count in freq.items()}
        
        # Skorlara göre sırala ve en yüksek top_n kelimeyi döndür
        sorted_words = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_words[:top_n]
    
    def summarize(self, text, sentence_count=3):
        """
        Metni özetler
        
        Args:
            text (str): Özetlenecek metin
            sentence_count (int): Özet için seçilecek cümle sayısı
            
        Returns:
            str: Özetlenmiş metin
        """
        # Metni cümlelere ayır
        sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', text)
        
        # Çok kısa cümleleri filtrele
        sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
        
        if len(sentences) <= sentence_count:
            return text
        
        # Her bir cümlenin TF-IDF skorunu hesapla
        tfidf_scores = self.compute_tfidf(sentences)
        
        # Her cümle için toplam skor hesapla
        sentence_scores = []
        for i, (sentence, tfidf_score) in enumerate(zip(sentences, tfidf_scores)):
            score = sum(tfidf_score.values())
            sentence_scores.append((i, sentence, score))
        
        # Skorlara göre sırala
        sentence_scores.sort(key=lambda x: x[2], reverse=True)
        
        # En yüksek skorlu sentence_count cümleyi seç
        selected = sentence_scores[:sentence_count]
        
        # Orijinal sıralamaya göre yeniden düzenle
        selected.sort(key=lambda x: x[0])
        
        # Özet cümleleri birleştir
        summary = " ".join([s[1] for s in selected])
        
        return summary

    def find_semantic_proximity(self, text, query, window_size=100):
        """
        Metinde sorgu ile anlamsal olarak yakın bölgeleri bulur
        
        Args:
            text (str): Aranacak metin
            query (str): Sorgu metni
            window_size (int): İncelenecek pencere boyutu
            
        Returns:
            list: Yakınlık skorlarına göre sıralanmış (metin parçası, skor) listesi
        """
        # Sorgu kelimelerini çıkar
        query_tokens = self.preprocess_text(query)
        query_stems = [self.simple_stem(token) for token in query_tokens]
        
        if not query_stems:
            return []
        
        # Metni kelimelere ayır
        text_tokens = text.split()
        if len(text_tokens) < 5:
            return []
        
        # Kelime pencereleri oluştur
        windows = []
        for i in range(0, len(text_tokens), window_size // 2):
            window = text_tokens[i:i + window_size]
            if window:
                windows.append(' '.join(window))
        
        # Her pencere için anlamsal benzerlik skoru hesapla
        window_scores = []
        for i, window in enumerate(windows):
            # Pencere içindeki kelimeleri tokenize et
            window_tokens = self.preprocess_text(window)
            window_stems = [self.simple_stem(token) for token in window_tokens]
            
            if not window_stems:
                continue
                
            # Sorgu ve pencere arasındaki örtüşmeyi hesapla
            overlap = sum(1 for stem in query_stems if stem in window_stems)
            
            # Overlap skoru
            overlap_score = overlap / len(query_stems) if query_stems else 0
            
            # Pencere içinde tekrarlanan sorgu terimleri için ekstra bonus
            if overlap > 0:
                bonus = min(0.5, 0.1 * (overlap - 1))  # Maksimum 0.5 bonus
            else:
                bonus = 0
                
            # Pencere uzunluğundan ceza puanı hesapla
            length_penalty = min(1.0, 50 / len(window_stems)) if window_stems else 0
            
            # Toplam skor
            score = overlap_score + bonus - (1 - length_penalty) * 0.2
            
            if score > 0:
                window_scores.append((window, score))
        
        # Skorlara göre sırala
        window_scores.sort(key=lambda x: x[1], reverse=True)
        
        return window_scores[:5]  # En alakalı 5 pencereyi döndür

    def format_educational_response(self, content_sections, sources=None):
        """
        İçeriği eğitici ve akademik bir formatta düzenler, konuşmacı atıflarını tamamen kaldırır,
        ve nesnel, öğretici bir ton ile bilgi sentezi sunar.
        
        Args:
            content_sections (dict): Başlık-İçerik şeklinde yapılandırılmış içerik bölümleri
            sources (list): Kaynak metadatası ile birlikte belge listesi
            
        Returns:
            str: Eğitici formatta düzenlenmiş içerik
        """
        if not content_sections:
            return "Bu konu hakkında yeterli bilgi bulunamadı."
            
        # Çıktı metni oluştur
        output_text = []
        
        # Konu özeti (eğer varsa)
        if "KONU ÖZETİ" in content_sections:
            output_text.append("## KONU ÖZETİ\n")
            
            # Özetteki konuşmacı referanslarını kaldır
            summary = content_sections["KONU ÖZETİ"]
            summary = self._remove_speaker_references(summary)
            
            output_text.append(summary)
            output_text.append("\n")
            
        # Derin analiz (eğer varsa)
        if "DERİN ANALİZ" in content_sections:
            output_text.append("## DERİN ANALİZ\n")
            
            # Alt bölümleri işle
            analysis_text = content_sections["DERİN ANALİZ"]
            
            # Konuşmacı referanslarını kaldır ve daha nesnel bir ton kullan
            analysis_text = self._remove_speaker_references(analysis_text)
            
            # Alt noktalar halinde yapılandır
            if "1." in analysis_text or "1)" in analysis_text:
                output_text.append(analysis_text)
            else:
                # Alt maddelere ayır
                paragraphs = re.split(r'\n\s*\n', analysis_text)
                for i, para in enumerate(paragraphs, 1):
                    if para.strip():
                        output_text.append(f"{i}. {para.strip()}")
                        output_text.append("\n")
            
            output_text.append("\n")
            
        # Sonuç (eğer varsa)
        if "SONUÇ" in content_sections:
            output_text.append("## SONUÇ\n")
            conclusion = content_sections["SONUÇ"]
            # Konuşmacı referanslarını kaldır
            conclusion = self._remove_speaker_references(conclusion)
            output_text.append(conclusion)
            output_text.append("\n\n")
            
        # Kaynaklar ekle (eğer varsa)
        if sources:
            output_text.append("## KAYNAKLAR\n")
            sources_by_file = {}
            
            # Kaynakları dosya adına göre grupla
            for doc in sources:
                source_name = doc.metadata.get("source", "Bilinmiyor")
                if source_name not in sources_by_file:
                    sources_by_file[source_name] = []
                
                # Zaman bilgisini daha doğru şekilde al
                time_str = ""
                time_info = doc.metadata.get("time", "")
                if not time_info or time_info == "00:00:00 - 00:00:00":
                    start_time = doc.metadata.get("start_time", "")
                    end_time = doc.metadata.get("end_time", "")
                    if start_time and end_time:
                        time_info = f"{start_time} - {end_time}"
                
                if time_info and time_info != "00:00:00 - 00:00:00" and time_info != "Belirtilmemiş":
                    time_str = f", Zaman: {time_info}"
                
                sources_by_file[source_name].append(time_str)
            
            # Her dosya için kaynakları göster
            for source_name, time_strs in sources_by_file.items():
                # Dosya adından .txt uzantısını kaldır
                if source_name.endswith('.txt'):
                    display_name = source_name[:-4]
                else:
                    display_name = source_name
                    
                # Benzersiz zaman bilgilerini ekle
                unique_times = list(set([ts for ts in time_strs if ts]))
                if unique_times:
                    times_str = ', '.join(unique_times)
                    output_text.append(f"[Kaynak: {display_name}{times_str}]\n")
                else:
                    output_text.append(f"[Kaynak: {display_name}]\n")
                    
        # Son metni birleştir
        return "".join(output_text)
    
    def _remove_speaker_references(self, text):
        """
        Metinden konuşmacı referanslarını ve öznel ifadeleri kaldırır,
        daha nesnel ve öğretici bir ton elde etmek için metni düzenler.
        
        Args:
            text (str): İşlenecek metin
            
        Returns:
            str: Konuşmacı referansları kaldırılmış metin
        """
        # Konuşmacı referanslarını kaldır
        text = re.sub(r'(Konuşmacı\s+[A-Z0-9]|Konuşmacı\s+\w+)[\s,:]', '', text)
        text = re.sub(r'(konuşmacı|konuşmacının|konuşmacıya|konuşmacıdan)\s+', '', text, flags=re.IGNORECASE)
        
        # Speaker referanslarını kaldır (İngilizce)
        text = re.sub(r'(Speaker\s+[A-Z0-9]|Speaker\s+\w+)[\s,:]', '', text)
        
        # Öznel fiil yapılarını nesnel ifadelerle değiştir
        text = re.sub(r'(belirt[a-zçğıöşü]+|söyle[a-zçğıöşü]+|ifade et[a-zçğıöşü]+)', 'belirtil', text)
        text = re.sub(r'(vurgula[a-zçğıöşü]+)', 'vurgulan', text)
        text = re.sub(r'(anlat[a-zçğıöşü]+)', 'anlatıl', text)
        text = re.sub(r'(açıkla[a-zçğıöşü]+)', 'açıklan', text)
        
        # Birinci tekil/çoğul şahıs ifadelerini üçüncü tekil şahısa çevir
        text = re.sub(r'\bbiz(?:im)?\b', 'bu analiz', text, flags=re.IGNORECASE)
        text = re.sub(r'\bben(?:im)?\b', 'bu değerlendirme', text, flags=re.IGNORECASE)
        
        # "Bence", "Kanımca" gibi öznel ifadeleri kaldır
        text = re.sub(r'\b[Bb]ence\b', '', text)
        text = re.sub(r'\b[Kk]anımca\b', '', text)
        text = re.sub(r'\b[Bb]ana göre\b', '', text)
        text = re.sub(r'\b[Dd]üşünüyorum\b', 'düşünülmektedir', text)
        text = re.sub(r'\b[Ss]anıyorum\b', 'görülmektedir', text)
        
        return text
    
    def extract_factual_statements(self, text):
        """
        Metinden nesnel ve bilgi içeren ifadeleri çıkarır.
        Konuşmacı atıflarını ve kişisel görüşleri filtreleyerek,
        eğitici içerikte kullanılabilecek gerçeklere odaklanır.
        
        Args:
            text (str): İşlenecek metin
            
        Returns:
            list: Bilgi ifadeleri listesi
        """
        # Metni cümlelere ayır
        sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]
        
        factual_statements = []
        
        # Konuşmacı referanslarını içeren desen - Genişletilmiş
        speaker_patterns = [
            r'[Kk]onuşmacı\s+[A-Za-z0-9]+',
            r'[Ss]peaker\s+[A-Za-z0-9]+',
            r'[Bb]elirt[a-zşçğıöü]+',
            r'[Ss]öyl[a-zşçğıöü]+',
            r'[İi]fade\s+et[a-zşçğıöü]*',
            r'[Vv]urgula[a-zşçğıöü]*',
            r'[Dd]üşünc[a-zşçğıöü]+',
            r'[Gg]örüş[a-zşçğıöü]*',
            r'[Ss]aygı değer',
            r'[Ss]unucu'
        ]
        
        # Öznel ifadeleri içeren kalıplar - Genişletilmiş
        subjective_patterns = [
            r'[Bb]enc[a-zşçğıöü]+',
            r'[Kk]anaatim[a-zşçğıöü]*',
            r'[Ss]an[ıi]yorum',
            r'[Dd]üşünüyorum',
            r'[Tt]ahmin[a-zşçğıöü]*',
            r'[Bb]ana\s+göre',
            r'[Bb]ize\s+göre',
            r'hissed[a-zşçğıöü]+',
            r'kanı[a-zşçğıöü]+',
            r'sanıyor',
            r'inan[a-zşçğıöü]+\s+ki',
            r'\s[Hh]erhalde\s',
            r'\s[Bb]elk[ıi]\s'
        ]
        
        # Kesin bilgi ifadelerini tespit eden kalıplar
        factual_indicators = [
            r'[Gg]erçek[a-zşçğıöü]*',
            r'[Aa]raştırma[a-zşçığıöü]*',
            r'[Vv]eri[a-zşçığıöü]*',
            r'[Ii]statistik[a-zşçığıöü]*',
            r'[Rr]apor[a-zşçığıöü]*',
            r'%\s*\d+',
            r'\d+\s*%',
            r'[Öö]lçü[a-zşçığıöü]*',
            r'[Ss]onuç[a-zşçığıöü]*',
            r'[Bb]ulgu[a-zşçığıöü]*',
            r'[Aa]nali[a-zşçığıöü]*',
            r'[Tt]arih[a-zşçığıöü]*'
        ]
        
        # Her cümle için kontrol
        for sentence in sentences:
            # Konuşmacı referansı içeriyor mu?
            has_speaker_ref = any(re.search(pattern, sentence) for pattern in speaker_patterns)
            
            # Öznel ifade içeriyor mu?
            has_subjective = any(re.search(pattern, sentence) for pattern in subjective_patterns)
            
            # Kesin bilgi belirteci içeriyor mu?
            has_factual = any(re.search(pattern, sentence) for pattern in factual_indicators)
            
            # Nesnel bilgi içeren cümleleri ekle
            if (not has_speaker_ref and not has_subjective) or has_factual:
                # Daha az kişisel bir ton elde etmek için düzenleme yap
                modified_sentence = self._remove_speaker_references(sentence)
                
                # Eğitici formata uygun şekilde bilgiyi yapılandır
                if not modified_sentence.endswith(('.', '!', '?')):
                    modified_sentence += '.'
                
                factual_statements.append(modified_sentence)
        
        return factual_statements
    
    def organize_by_topic(self, statements, use_clustering=False):
        """
        Bilgi ifadelerini konularına göre gruplar.
        Tutarlı bir öğretici yapı için içeriği konusal olarak düzenler.
        
        Args:
            statements (list): Bilgi ifadeleri listesi
            use_clustering (bool): Kümeleme algoritması kullanılsın mı
            
        Returns:
            dict: Konu başlıklarına göre gruplandırılmış ifadeler
        """
        if not statements:
            return {}
            
        # Genişletilmiş konu-anahtar kelime eşleşmesi (daha kapsamlı gruplandırma için)
        topic_keywords = {
            "Ekonomik Analiz": ["ekonomi", "enflasyon", "faiz", "döviz", "kur", "merkez bankası", 
                             "piyasa", "borsa", "finansal", "bütçe", "mali", "ekonomik", 
                             "fiyat", "maliyet", "değer", "para", "paranın", "paradan"],
                             
            "Üretim ve Sanayi": ["üretim", "sanayi", "fabrika", "ihracat", "ithalat", "ticaret", 
                               "imalat", "teknoloji", "üretici", "ürün", "hammadde", "kaynak", 
                               "verimlilik", "kapasite", "tedarik", "lojistik"],
                               
            "Tasarruf ve Yatırım": ["tasarruf", "yatırım", "sermaye", "fon", "birikim", "finans", 
                                  "borçlanma", "kredi", "borsa", "hisse", "tahvil", "faiz", 
                                  "getiri", "kar", "zarar", "risk", "portföy", "banka"],
                                  
            "Para Politikası": ["para", "merkez bankası", "faiz", "emisyon", "rezerv", "likidite", 
                              "politika", "bağımsız", "enflasyon", "devalüasyon", "kur", "döviz", 
                              "swap", "parasal", "sıkılaşma", "genişleme", "sterilizasyon"],
                              
            "İş ve İstihdam": ["iş", "istihdam", "işsizlik", "çalışan", "işveren", "maaş", "ücret", 
                             "sigorta", "sendika", "iş gücü", "çalışma", "kariyer", "meslek", 
                             "personel", "insan kaynakları", "işe alım", "emeklilik"],
                             
            "Ekonomik Reform": ["reform", "yapısal", "düzenleme", "tedbir", "önlem", "kalkınma", 
                              "strateji", "politika", "dönüşüm", "iyileştirme", "yeniden yapılandırma", 
                              "sürdürülebilirlik", "sürdürülebilir", "program", "planlama"],
                              
            "Dijital Ekonomi": ["dijital", "sanal para", "kripto", "blockchain", "teknoloji", 
                              "e-ticaret", "fintech", "bitcoin", "ethereum", "token", "nft", 
                              "elektronik", "online", "dijitalleşme", "yapay zeka", "otomasyon"],
                              
            "Siyasi Gelişmeler": ["siyaset", "siyasi", "iktidar", "muhalefet", "parti", "seçim", 
                                "oy", "meclis", "hükümet", "demokrasi", "politika", "cumhurbaşkanı", 
                                "başbakan", "bakan", "diplomatik", "uluslararası"],
                                
            "Uluslararası İlişkiler": ["uluslararası", "diplomatik", "anlaşma", "küresel", "bölgesel", 
                                    "ülke", "devlet", "sınır", "ittifak", "işbirliği", "çatışma", 
                                    "ab", "nato", "birleşmiş milletler", "güvenlik", "savunma"],
                                    
            "Toplumsal Konular": ["toplum", "sosyal", "yaşam", "kültür", "değer", "aile", "eğitim", 
                               "sağlık", "adalet", "insan", "hak", "özgürlük", "eşitlik", "din", 
                               "inanç", "hukuk", "sistem", "değişim", "dönüşüm"],
                               
            "Tarih ve Geçmiş": ["tarih", "tarihsel", "geçmiş", "eski", "antik", "imparatorluk", 
                               "medeniyet", "çağ", "dönem", "devir", "yüzyıl", "war", "savaş", 
                               "barış", "anlaşma", "kuruluş", "kurucu", "miras"]
        }
        
        # Kümeleme tekniği kullan (gelişmiş gruplandırma)
        if use_clustering and len(statements) > 5:
            try:
                import numpy as np
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.cluster import KMeans
                
                # TF-IDF vektörleri oluştur
                vectorizer = TfidfVectorizer(stop_words=list(self.stopwords), 
                                            max_features=100, 
                                            ngram_range=(1, 2))
                X = vectorizer.fit_transform(statements)
                
                # Küme sayısını makul bir değere ayarla
                n_clusters = min(int(np.sqrt(len(statements))), 5)
                n_clusters = max(n_clusters, 2)  # En az 2 küme
                
                # Kümeleme uygula
                kmeans = KMeans(n_clusters=n_clusters, random_state=42)
                kmeans.fit(X)
                labels = kmeans.labels_
                
                # Her küme için önemli terimleri belirle
                cluster_keywords = {}
                order_centroids = kmeans.cluster_centers_.argsort()[:, ::-1]
                terms = vectorizer.get_feature_names_out()
                for i in range(n_clusters):
                    top_terms = [terms[ind] for ind in order_centroids[i, :5]]
                    cluster_keywords[i] = top_terms
                
                # İfadeleri kümelere göre grupla
                grouped_statements = {}
                for i, label in enumerate(labels):
                    # Küme başlığını belirle - daha anlamlı başlıklar için kontrol et
                    cluster_terms = cluster_keywords[label]
                    
                    # En uygun konu başlığını bul
                    best_topic = None
                    best_match_score = 0
                    
                    for topic, keywords in topic_keywords.items():
                        # Küme terimleri ile konu anahtar kelimeleri arasında eşleşme skoru hesapla
                        match_score = sum(1 for term in cluster_terms if any(kw in term for kw in keywords))
                        if match_score > best_match_score:
                            best_match_score = match_score
                            best_topic = topic
                    
                    # Eğer iyi bir eşleşme yoksa, küme terimlerinden başlık oluştur
                    if best_match_score < 1:
                        topic_name = f"Konu: {', '.join(cluster_terms[:3])}"
                    else:
                        topic_name = best_topic
                    
                    if topic_name not in grouped_statements:
                        grouped_statements[topic_name] = []
                    grouped_statements[topic_name].append(statements[i])
                
                return grouped_statements
                
            except (ImportError, Exception) as e:
                # Kümeleme başarısız olursa basit gruplama kullan
                print(f"Kümeleme başarısız: {e}. Basit gruplama kullanılıyor.")
                use_clustering = False
        
        # Basit anahtar kelime tabanlı gruplama
        grouped_statements = {}
        ungrouped = []
        
        for statement in statements:
            statement_lower = statement.lower()
            assigned = False
            
            # Her konu için puan hesapla
            topic_scores = {}
            
            for topic, keywords in topic_keywords.items():
                # İfadede bu konuya ait anahtar kelime var mı?
                topic_score = 0
                for keyword in keywords:
                    if keyword in statement_lower:
                        # Tam kelime eşleşmesi için regex kullan
                        pattern = r'\b' + re.escape(keyword) + r'\b'
                        matches = re.findall(pattern, statement_lower)
                        topic_score += len(matches)
                
                if topic_score > 0:
                    topic_scores[topic] = topic_score
            
            # En yüksek skora sahip konuya ata
            if topic_scores:
                best_topic = max(topic_scores.items(), key=lambda x: x[1])[0]
                if best_topic not in grouped_statements:
                    grouped_statements[best_topic] = []
                grouped_statements[best_topic].append(statement)
                assigned = True
            
            # Hiçbir konuya atanamayanlar
            if not assigned:
                ungrouped.append(statement)
        
        # Gruplanamamış ifadeleri "Diğer Konular" başlığı altında topla
        if ungrouped:
            grouped_statements["Diğer Konular"] = ungrouped
        
        return grouped_statements
