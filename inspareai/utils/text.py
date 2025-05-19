#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
InspareAI - Metin işleme için fonksiyonlar.
Bu modül, anahtar kelime çıkarma ve belge alakalılık hesaplama için fonksiyonları içerir.
"""

import re
import numpy as np

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


def extract_keywords(text):
    """Sorgudan anahtar kelimeleri çıkar ve kök haline dönüştür
    
    Args:
        text (str): İşlenecek metin
        
    Returns:
        list: Çıkarılan anahtar kelimeler
    """
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


def calculate_relevance(doc, keywords):
    """Belge ve anahtar kelimeler arasındaki alakayı hesapla
    
    Args:
        doc (Document): Alakalılığı hesaplanacak belge
        keywords (list): Anahtar kelimeler listesi
        
    Returns:
        float: Alakalılık puanı
    """
    doc_text = doc.page_content.lower()
    speaker = doc.metadata.get("speaker", "")
    time_info = doc.metadata.get("time", "")
    score = 0.0
    
    # Anahtar kelime bazlı puanlama
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
    
    # Daha uzun ve anlamlı cümleler için puan
    sentences = re.split(r'[.!?]+', doc_text)
    mean_sentence_len = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
    if 5 <= mean_sentence_len <= 20:  # İdeal cümle uzunluğu
        score += 0.5
    
    # İçeriğin genel kalitesi - metin içinde soru-cevap yapısı var mı?
    if '?' in doc_text and len(doc_text) > 100:
        score += 0.5  # Muhtemelen bir soru-cevap var, bu faydalı olabilir
    
    # Sonucun pozitif olmasını sağla
    return max(score, 0.1)
