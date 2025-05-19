#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
InspareAI - Önbellek yönetimi için fonksiyonlar.
Bu modül, önbelleğin yüklenmesi, kaydedilmesi ve yönetilmesi için fonksiyonları içerir.
"""

import os
import json
import time
from inspareai.config.constants import CACHE_FILE, CACHE_CLEAN_THRESHOLD, CACHE_KEEP_COUNT

# Önbellek değişkenleri
query_cache = {}
memory_cache = {}

def load_cache():
    """
    Disk üzerindeki önbellek dosyasını yükler.
    
    Returns:
        dict: Yüklenen önbellek veya boş sözlük
    """
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Önbellek yüklenemedi: {e}")
    return {}

def save_cache():
    """Önbelleği disk üzerine kaydeder."""
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(query_cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Önbellek kaydedilemedi: {e}")

def clear_memory_cache():
    """Bellek önbelleğini temizler ve periyodik olarak çağrılmalıdır."""
    global memory_cache
    
    # Eşikten fazla öğe varsa eskilerini temizle 
    if len(memory_cache) > CACHE_CLEAN_THRESHOLD:
        # En son kullanılanları sakla
        sorted_keys = sorted(memory_cache.keys(), key=lambda k: memory_cache[k].get('timestamp', 0), reverse=True)
        keys_to_keep = sorted_keys[:CACHE_KEEP_COUNT]
        
        new_cache = {}
        for key in keys_to_keep:
            new_cache[key] = memory_cache[key]
            
        memory_cache = new_cache
        print(f"Bellek önbelleği temizlendi. Kalan öğe sayısı: {len(memory_cache)}")

# Önbelleği başlangıçta yükle
query_cache = load_cache()
