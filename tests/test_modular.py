#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
InspareAI - Modüler Yapı Testi
Bu script, InspareAI'nin yeni modüler yapısını test eder.
"""

import os
import sys

# Ana dizini ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Temel bileşenleri içe aktar
from inspareai.config import constants, prompts
from inspareai.core import model, query, retrieval
from inspareai.utils import cache, text, streaming
from inspareai.cli import command_handler
from inspareai.api import streamlit_handler

def test_imports():
    """Modül içe aktarmalarını test eder ve başarılı olduklarını raporlar."""
    
    # İçe aktarılan modüllerin varlığını kontrol et
    components = {
        "config.constants": constants,
        "config.prompts": prompts,
        "core.model": model,
        "core.query": query,
        "core.retrieval": retrieval,
        "utils.cache": cache,
        "utils.text": text,
        "utils.streaming": streaming,
        "cli.command_handler": command_handler,
        "api.streamlit_handler": streamlit_handler
    }
    
    # Her modülü test et
    success_count = 0
    print("📋 InspareAI Modüler Yapı Testi")
    print("=" * 40)
    
    for name, module in components.items():
        if module:
            print(f"✅ {name}: Başarıyla yüklendi")
            success_count += 1
        else:
            print(f"❌ {name}: Yüklenemedi")
    
    # Özet
    print("=" * 40)
    print(f"📊 Sonuç: {success_count}/{len(components)} modül başarıyla yüklendi")
    
    if success_count == len(components):
        print("🎉 Tüm modüller başarıyla yüklendi! Modüler yapı doğru çalışıyor!")
        return True
    else:
        print("⚠️ Bazı modüller yüklenemedi. Lütfen hataları gözden geçirin.")
        return False

def test_functionality():
    """Temel işlevlerin çalıştığını test eder."""
    
    print("\n🧪 İşlevsellik Testi")
    print("=" * 40)
    
    try:
        # Model oluşturma testi
        test_model = model.create_model("llama3.1", 0.1, 2)
        print("✅ Model oluşturma: Başarılı")
        
        # Sabitler ve yapılandırmalar
        print(f"✅ Maksimum döküman sayısı: {constants.MAX_DOCUMENTS}")
        
        # Önbellek
        cache_loaded = isinstance(cache.query_cache, dict)
        print(f"✅ Önbellek yükleme: {'Başarılı' if cache_loaded else 'Başarısız'}")
        
        # Text işleme
        keywords = text.extract_keywords("Bu bir test cümlesidir")
        print(f"✅ Anahtar kelime çıkarma: {keywords}")
        
        return True
    except Exception as e:
        print(f"❌ İşlevsellik hatası: {str(e)}")
        return False

if __name__ == "__main__":
    imports_ok = test_imports()
    if imports_ok:
        test_functionality()
