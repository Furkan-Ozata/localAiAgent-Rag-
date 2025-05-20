#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
InspareAI - API Ana Modül.
Bu modül, Streamlit arayüzünden kullanılan API fonksiyonlarını içerir.
"""

import time
from typing import Callable, List, Dict, Any

from inspareai.core.query import query_transcripts, quick_query
from inspareai.cli.command_handler import list_transcript_files, view_transcript


def stream_query(prompt: str, callback: Callable, hizli_mod: bool = False, dusunme_sureci: bool = False) -> str:
    """
    Sorguyu akış şeklinde yanıtlar ve aşamaları gösterir.
    
    Args:
        prompt (str): Kullanıcı sorusu veya konuşma geçmişiyle birlikte bağlamlı soru
        callback (Callable): Her bir aşama için çağrılacak callback fonksiyonu
        hizli_mod (bool): Hızlı yanıt modu aktif mi
        dusunme_sureci (bool): Düşünme sürecinin gösterilip gösterilmeyeceği
        
    Returns:
        str: Tam yanıt metni
    """
    full_response = []
    
    # İmleç karakteri tanımla
    cursor_character = "▌"
    
    # Akış callback tanımı
    def stream_to_callback(chunk):
        full_response.append(chunk)
        full_text = "".join(full_response)
        callback(full_text + cursor_character)
        
    # Bağlamlı soru mu kontrol et
    has_conversation_context = "konuşma geçmişini dikkate alarak" in prompt.lower()
    
    # Düşünme süreci aşamaları
    if dusunme_sureci:
        if has_conversation_context:
            callback("💬 Konuşma geçmişi analiz ediliyor...")
            time.sleep(0.5)
            callback("💬 Konuşma geçmişi analiz ediliyor...\n🔄 Bağlam ilişkilendiriliyor...")
            time.sleep(0.5)
        
        callback("🔍 Anahtar kelimeler analiz ediliyor...")
        time.sleep(0.5)
        callback(("🔍 Anahtar kelimeler analiz ediliyor...\n"
                "📑 İlgili dokümanlar aranıyor..."))
        time.sleep(0.5)
        callback(("🔍 Anahtar kelimeler analiz ediliyor...\n"
                "📑 İlgili dokümanlar aranıyor...\n"
                "📋 Dokümanlar filtreleniyor..."))
        time.sleep(0.5)
        
        if has_conversation_context:
            callback(("🔍 Anahtar kelimeler analiz ediliyor...\n"
                    "📑 İlgili dokümanlar aranıyor...\n"
                    "📋 Dokümanlar filtreleniyor...\n"
                    "🧠 Önceki konuşma bağlamıyla yanıt oluşturuluyor...\n\n"))
        else:
            callback(("🔍 Anahtar kelimeler analiz ediliyor...\n"
                    "📑 İlgili dokümanlar aranıyor...\n"
                    "📋 Dokümanlar filtreleniyor...\n"
                    "🧠 Yanıt oluşturuluyor...\n\n"))
        time.sleep(0.5)
    
    # Sorgu işleme
    if hizli_mod:
        result = quick_query(prompt, stream_callback=stream_to_callback)
    else:
        result = query_transcripts(prompt, stream_callback=stream_to_callback)
    
    # Akış yoksa direkt yanıtı döndür
    if not full_response:
        callback(result)
        return result
    
    # Son yanıtı, imleç karakteri olmadan göndererek işlemi tamamla
    final_response = "".join(full_response)
    callback(final_response)  # İmleçsiz son halini göster
    
    return final_response


def get_transcript_list() -> List[str]:
    """
    Transkript dosyalarının listesini döndürür.
    
    Returns:
        List[str]: Transkript dosyalarının listesi
    """
    return list_transcript_files()


def get_transcript_content(file_path: str) -> str:
    """
    Belirli bir transkript dosyasının içeriğini döndürür.
    
    Args:
        file_path (str): Transkript dosyasının yolu
        
    Returns:
        str: Dosyanın içeriği
    """
    return view_transcript(file_path)
