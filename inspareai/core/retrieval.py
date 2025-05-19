#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
InspareAI - Belge İşleme ve Vektör Veritabanı Erişimi.
Bu modül, vektör veritabanı sorgulama ve belgeleri işleme fonksiyonlarını içerir.
"""

import re
import numpy as np
from datetime import datetime
import os
import concurrent.futures
from typing import List, Dict, Any

# Hata durumunda vector modülünü güvenli şekilde import et
try:
    from vector import retriever, vectorstore
    VECTOR_DB_AVAILABLE = True
except ImportError as e:
    print(f"UYARI: vector.py dosyası bulunamadı veya içe aktarılamadı: {str(e)}")
    VECTOR_DB_AVAILABLE = False
    retriever = None
    vectorstore = None
except Exception as e:
    print(f"UYARI: Vektör veritabanı yüklenirken hata oluştu: {str(e)}")
    VECTOR_DB_AVAILABLE = False
    retriever = None
    vectorstore = None

from inspareai.config.constants import (MAX_DOCUMENTS, MAX_DOCS_PER_SPEAKER, 
                                      OTHER_DOCS_LIMIT, CONTENT_MAX_LENGTH, 
                                      FILENAME_MAX_LENGTH, CHRONO_KEYWORDS, 
                                      COMPARISON_KEYWORDS)
from inspareai.utils.text import calculate_relevance, extract_keywords


def retrieve_relevant_documents(question, keywords=None):
    """
    Sorguyla ilgili dokümanları vektör veritabanından getirir.
    
    Args:
        question (str): Kullanıcı sorusu
        keywords (list, optional): Önceden çıkarılmış anahtar kelimeler
        
    Returns:
        list: İlgili belgelerin listesi
    """
    if not VECTOR_DB_AVAILABLE or retriever is None:
        raise ValueError("Vektör veritabanı kullanılamıyor.")
    
    if keywords is None:
        keywords = extract_keywords(question)
        
    try:
        # Retriever'ı optimize et
        if hasattr(retriever, 'search_kwargs'):
            if retriever.search_kwargs.get("search_type", None) != "mmr":
                # MMR'yi etkinleştir - çeşitliliği artırır
                retriever.search_kwargs["search_type"] = "mmr"
                retriever.search_kwargs["fetch_k"] = max(retriever.search_kwargs.get("fetch_k", 50), 50)
                retriever.search_kwargs["lambda_mult"] = 0.8  # Alaka-çeşitlilik dengesi
        
        # Dokümanları getir
        docs = retriever.invoke(question)
        
        # Optimize edilmiş sıralama için belgeleri puanlandır
        docs = score_and_sort_documents(docs, question, keywords)
        
        return docs
    except Exception as e:
        print(f"Doküman getirilirken hata: {e}")
        raise e


def score_and_sort_documents(docs, question, keywords):
    """
    Belgeleri alakalarına göre puanlandırır ve sıralar.
    
    Args:
        docs (list): Belgeler listesi
        question (str): Kullanıcı sorusu
        keywords (list): Anahtar kelimeler
        
    Returns:
        list: Sıralanmış belgeler
    """
    def cosine_similarity(vec1, vec2):
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        if np.linalg.norm(vec1) == 0 or np.linalg.norm(vec2) == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))
    
    # Paralel puanlama için
    if keywords and hasattr(vectorstore, 'embed_query') and hasattr(vectorstore, 'embed_documents'):
        try:
            # Soru ve belge vektörlerini oluştur
            question_emb = vectorstore.embed_query(question)
            doc_texts = [doc.page_content for doc in docs]
            doc_embs = vectorstore.embed_documents(doc_texts)
            
            # Her belge için alaka puanını hesapla
            for i, doc in enumerate(docs):
                kw_score = calculate_relevance(doc, keywords)
                emb_score = cosine_similarity(question_emb, doc_embs[i])
                emb_score = max(emb_score, 0.0)
                kw_score_norm = min(max(kw_score / 2.0, 0.0), 1.0)
                
                # Puanlama formülü
                doc.final_score = 0.75 * kw_score_norm + 0.25 * emb_score
                
                # Konuşmacı puanlaması
                if "speaker" in question.lower() and doc.metadata.get("speaker", "").lower() in question.lower():
                    doc.final_score *= 1.5  # Konuşmacı eşleşirse fazladan puan
            
            return sorted(docs, key=lambda d: getattr(d, 'final_score', 0), reverse=True)
        except Exception as e:
            print(f"Gelişmiş sıralama uygulanamadı: {e}")
    
    # Varsayılan sıralama
    return sorted(docs, key=lambda doc: calculate_relevance(doc, keywords), reverse=True) if keywords else docs


def filter_and_prepare_documents(docs, question):
    """
    Belgeleri filtreler ve sorgu tipine göre özel hazırlamalar yapar.
    
    Args:
        docs (list): Belgeler listesi
        question (str): Kullanıcı sorusu
        
    Returns:
        list: Filtrelenmiş belgeler
    """
    # İlk MAX_DOCUMENTS belgeyi al
    filtered_docs = docs[:MAX_DOCUMENTS]
    
    # Sorgu tipini algılama
    is_chronological = any(word in question.lower() for word in CHRONO_KEYWORDS)
    is_speaker_specific = "speaker" in question.lower() or "konuşmacı" in question.lower()
    is_comparison = any(word in question.lower() for word in COMPARISON_KEYWORDS)
    
    # Kronolojik analiz için belgeleri sırala
    if is_chronological:
        filtered_docs = sort_documents_chronologically(filtered_docs)
    
    # Konuşmacı spesifik analiz
    if is_speaker_specific:
        speaker_matches = []
        for speaker_letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if f"speaker {speaker_letter.lower()}" in question.lower() or f"speaker {speaker_letter}" in question.lower():
                speaker_matches.append(speaker_letter)
        
        if speaker_matches:
            # İlgili konuşmacıların belgelerini başa al
            speaker_docs = [doc for doc in filtered_docs if doc.metadata.get("speaker", "").upper() in speaker_matches]
            other_docs = [doc for doc in filtered_docs if doc.metadata.get("speaker", "").upper() not in speaker_matches]
            filtered_docs = speaker_docs + other_docs[:max(OTHER_DOCS_LIMIT, MAX_DOCUMENTS-len(speaker_docs))]
    
    # Karşılaştırma analizi için belge çeşitliliği
    if is_comparison:
        # Farklı konuşmacılardan belgeleri dengeli şekilde dahil et
        speaker_groups = {}
        for doc in filtered_docs:
            speaker = doc.metadata.get("speaker", "Unknown")
            if speaker not in speaker_groups:
                speaker_groups[speaker] = []
            speaker_groups[speaker].append(doc)
        
        # Her konuşmacıdan dengeli sayıda belge seç
        balanced_docs = []
        max_per_speaker = MAX_DOCS_PER_SPEAKER
        
        # En alakalı konuşmacıları sırala
        sorted_speakers = sorted(speaker_groups.keys(), key=lambda s: len(speaker_groups[s]), reverse=True)
        
        for speaker in sorted_speakers:
            balanced_docs.extend(speaker_groups[speaker][:max_per_speaker])
        
        filtered_docs = balanced_docs[:MAX_DOCUMENTS]
    
    return filtered_docs


def format_context(docs):
    """
    Belgeleri bağlam olarak formatlar.
    
    Args:
        docs (list): Belgeler listesi
        
    Returns:
        str: Formatlanmış bağlam metni
    """
    context_parts = []
    
    for i, doc in enumerate(docs, 1):
        # Dosya adını kısalt
        source = doc.metadata.get('source', 'Bilinmiyor')
        if len(source) > FILENAME_MAX_LENGTH:
            source = source[:FILENAME_MAX_LENGTH-3] + "..."
        
        # Zaman bilgisini doğru şekilde biçimlendir
        time_info = doc.metadata.get('time', '')
        if not time_info or time_info == "00:00:00 - 00:00:00":
            start_time = doc.metadata.get('start_time', '')
            end_time = doc.metadata.get('end_time', '')
            if start_time and end_time:
                time_info = f"{start_time} - {end_time}"
        
        # İçeriği temizle ve biçimlendir
        try:
            if not hasattr(doc, 'page_content') or doc.page_content is None:
                content = "Belge içeriği alınamadı"
            else:
                content = doc.page_content
                if 'Content: ' in content:
                    content = content.split('Content: ')[-1]
                content = content.strip()
            
            # İçeriği belirli bir uzunluğa kısalt
            if len(content) > CONTENT_MAX_LENGTH:
                content = content[:CONTENT_MAX_LENGTH-3] + "..."
        except Exception as e:
            print(f"İçerik işlenirken hata: {e}")
            content = "Belge içeriği işlenirken hata oluştu"
        
        # Belge parçasını biçimlendir
        context_part = f"[Belge {i}]\nDosya: {source}\nZaman: {time_info}\nKonuşmacı: {doc.metadata.get('speaker', 'Bilinmiyor')}\nİçerik: {content}"
        context_parts.append(context_part)
    
    return "\n\n".join(context_parts)


def sort_documents_chronologically(docs):
    """
    Belgeleri kronolojik olarak sıralar.
    
    Args:
        docs (list): Belgeler listesi
        
    Returns:
        list: Kronolojik olarak sıralanmış belgeler
    """
    def extract_time(doc):
        """Belgeden zaman bilgisini çıkarır"""
        time_str = doc.metadata.get('time', '')
        
        if not time_str or time_str == "00:00:00 - 00:00:00":
            start_time = doc.metadata.get('start_time', '00:00:00')
            return start_time
        
        # Zaman bilgisini ayrıştır
        match = re.search(r'(\d+:\d+:\d+)', time_str)
        if match:
            return match.group(1)
        return "00:00:00"
    
    # Belgeleri zamanına göre sırala
    try:
        # Zaman formatını düzgün bir şekilde ayrıştır
        time_sorted = sorted(docs, key=extract_time)
        return time_sorted
    except Exception as e:
        print(f"Kronolojik sıralama hatası: {e}")
        return docs  # Hata durumunda orijinal sıralama korunur


def format_sources(docs):
    """
    Kaynakları formatlar.
    
    Args:
        docs (list): Belgeler listesi
        
    Returns:
        str: Formatlanmış kaynak bilgileri
    """
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


def save_analysis(question, result):
    """
    Analiz sonucunu kaydeder.
    
    Args:
        question (str): Kullanıcı sorusu
        result (str): Analiz sonucu
        
    Returns:
        str: Kaydedilen dosyanın adı
    """
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
