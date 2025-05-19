#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
InspareAI - CLI Komut İşlemleri.
Bu modül, komut satırı arayüzü için komut işleme fonksiyonlarını içerir.
"""

import os
import sys
import re
from datetime import datetime
import json

from inspareai.core.query import query_transcripts, quick_query
from inspareai.utils.cache import save_cache


def print_banner():
    """
    InspareAI başlık bannerını yazdırır.
    """
    banner = """
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║     ██╗███╗   ██╗███████╗██████╗  █████╗ ██████╗ ███████╗║
    ║     ██║████╗  ██║██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔════╝║
    ║     ██║██╔██╗ ██║███████╗██████╔╝███████║██████╔╝█████╗  ║
    ║     ██║██║╚██╗██║╚════██║██╔═══╝ ██╔══██║██╔══██╗██╔══╝  ║
    ║     ██║██║ ╚████║███████║██║     ██║  ██║██║  ██║███████╗║
    ║     ╚═╝╚═╝  ╚═══╝╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝║
    ║                                                          ║
    ║           Türkçe Transkript Analiz Sistemi              ║
    ║                       v3.2                              ║
    ╚══════════════════════════════════════════════════════════╝
    """
    print(banner)
    print("Komut satırı sorgu sistemine hoş geldiniz!")
    print("Çıkmak için 'q' veya 'exit' yazabilirsiniz.")
    print("='='='='='='='='='='='='='='='='='='='='='='='='='='='='='='='='='=")


def get_user_input(prompt="Sorgunuz: "):
    """
    Kullanıcıdan girdi alır.
    
    Args:
        prompt (str): Kullanıcıya gösterilecek prompt
        
    Returns:
        str: Kullanıcı girişi
    """
    try:
        return input(prompt).strip()
    except (KeyboardInterrupt, EOFError):
        print("\nProgram sonlandırılıyor...")
        sys.exit(0)


def list_transcript_files(directory="transcripts"):
    """
    Transkript dosyalarını listeler.
    
    Args:
        directory (str): Dosyaların aranacağı dizin
        
    Returns:
        list: Transkript dosyalarının listesi
    """
    if not os.path.exists(directory):
        print(f"Uyarı: {directory} dizini bulunamadı.")
        return []
    
    files = [f for f in os.listdir(directory) if f.endswith(".txt") and not f.startswith('.')]
    return files


def view_transcript(file_path):
    """
    Bir transkript dosyasını görüntüler.
    
    Args:
        file_path (str): Görüntülenecek dosyanın yolu
        
    Returns:
        str: Dosyanın içeriği, hata mesajı veya boş metin
    """
    try:
        if not os.path.exists(file_path):
            return f"Hata: {file_path} dosyası bulunamadı."
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Header ekle
        header = f"=== {os.path.basename(file_path)} ===\n"
        return header + content
    except Exception as e:
        return f"Dosya okuma hatası: {str(e)}"


def handle_interactive_mode():
    """
    Etkileşimli komut satırı modunu işler.
    """
    print_banner()
    
    # Program döngüsü
    while True:
        try:
            user_query = get_user_input("\nSorgunuz (çıkmak için 'q'): ")
            
            # Çıkış kontrolü
            if user_query.lower() in ['q', 'exit', 'quit', 'çıkış']:
                print("Program sonlandırılıyor...")
                save_cache()  # Çıkışta önbelleği kaydet
                break
                
            # Transkript listesini göster
            elif user_query.lower() in ['list', 'liste', 'dosyalar']:
                files = list_transcript_files()
                if files:
                    print("\nMevcut Transkript Dosyaları:")
                    for i, file in enumerate(files, 1):
                        print(f"{i}. {file}")
                else:
                    print("Hiç transkript dosyası bulunamadı.")
                continue
                
            # Komutları işle
            elif user_query.lower().startswith('view ') or user_query.lower().startswith('göster '):
                # Dosya görüntüleme komutu
                parts = user_query.split(' ', 1)
                if len(parts) > 1:
                    file_name = parts[1].strip()
                    file_path = os.path.join("transcripts", file_name)
                    if not file_name.endswith('.txt'):
                        file_path += '.txt'
                    print(view_transcript(file_path))
                continue
                
            # Hızlı yanıt modu
            elif user_query.lower().startswith('hızlı:') or user_query.lower().startswith('quick:'):
                query_text = user_query.split(':', 1)[1].strip()
                if query_text:
                    print("\nHızlı yanıt modu kullanılıyor...")
                    result = quick_query(query_text)
                    print("\nYANIT:\n")
                    print(result)
                else:
                    print("Geçerli bir soru girin.")
                continue
            
            # Normal sorgu
            elif user_query.strip():
                print("\nYanıt hazırlanıyor...")
                start_time = datetime.now()
                
                # Sorguyu işle
                result = query_transcripts(user_query)
                
                elapsed = (datetime.now() - start_time).total_seconds()
                print("\nYANIT:\n")
                print(result)
                print(f"\n[Yanıt süresi: {elapsed:.2f} saniye]")
                
        except KeyboardInterrupt:
            print("\nİşlem iptal edildi.")
            continue
        except Exception as e:
            print(f"\nHata oluştu: {str(e)}")
            print("Teknik detay:", traceback.format_exc())


def handle_single_query_mode(query):
    """
    Tek seferlik sorgu modunu işler.
    
    Args:
        query (str): Yanıtlanacak sorgu
    """
    try:
        result = query_transcripts(query)
        print(result)
        save_cache()  # İşlem tamamlandığında önbelleği kaydet
    except Exception as e:
        print(f"Hata: {str(e)}")
        sys.exit(1)
