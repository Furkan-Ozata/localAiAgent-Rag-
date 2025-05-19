#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
InspareAI - Sabit değerler ve konfigürasyon.
Bu modül, uygulama genelinde kullanılan tüm sabit değerleri içerir.
"""

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

# Veri dosyaları
CACHE_FILE = "query_cache.json"
TRANSCRIPT_DIR = "transcripts"

# Kronolojik analiz anahtar kelimeleri
CHRONO_KEYWORDS = ["kronoloji", "zaman", "sıra", "gelişme", "tarihsel", "süreç"]

# Karşılaştırma analizi anahtar kelimeleri
COMPARISON_KEYWORDS = ["karşılaştır", "fark", "benzerlik", "benzer", "farklı"]
