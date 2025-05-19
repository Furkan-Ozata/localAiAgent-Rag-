#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
InspareAI - Vector veritabanı yönetim arayüzü
Bu script, transkript dosyalarını vektör veritabanına dönüştürmek için kullanılır.
"""

import sys
import os
import argparse

# Ana dizini ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Vektör veritabanı oluşturma ve yönetme işlevlerine erişim için
# inspareai paketini içe aktar 
from inspareai.core import retrieval

def main():
    """
    Vektör veritabanını oluşturma ve yönetme işlevlerini yürütür.
    """
    parser = argparse.ArgumentParser(
        description='Transkript dosyalarını vektör veritabanına dönüştürme aracı',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--force', 
        action='store_true',
        help='Mevcut veritabanını yeniden oluştur'
    )
    
    parser.add_argument(
        '--dynamic-chunking', 
        action='store_true',
        help='Dinamik bölümleme kullan'
    )
    
    parser.add_argument(
        '--no-cache', 
        action='store_true',
        help='Önbellek kullanma'
    )
    
    parser.add_argument(
        '--parallel', 
        action='store_true',
        help='Paralel işleme kullan'
    )
    
    parser.add_argument(
        '--chunk-size', 
        type=int,
        default=1000,
        help='Bölümleme boyutu'
    )
    
    parser.add_argument(
        '--overlap', 
        type=int,
        default=200,
        help='Bölüm örtüşme uzunluğu'
    )
    
    args = parser.parse_args()
    
    # Gerçek vector.py dosyasını modüler kullanarak çağır
    # Ana işlevsellik retrieval modülüne taşınmalı
    # Ancak bu olmadan eski vector.py korunmalı
    
    # Bu dosya şu an için kullanıcılara modüler sistemle entegre bir arabirim sunuyor
    print("InspareAI Vektör Veritabanı Yönetim Aracı\n")
    print("Modüler yapıyı kullanmak için, lütfen retrieveal modülünde")
    print("vector.py içeriğini bir veritabanı oluşturma işlevine dönüştürün.\n")
    print("Şimdilik, eski vector.py dosyası kullanılacak.\n")
    
    # Mevcut vector.py dosyasını çalıştır
    import vector
    if hasattr(vector, "main"):
        vector.main()
    else:
        print("vector.py dosyasında main() fonksiyonu bulunamadı.")
        print("Lütfen doğru vector.py dosyasını kullandığınızdan emin olun.")

if __name__ == "__main__":
    main()
