#!/bin/bash

echo "Türkçe Transkript Analiz Sistemi için bağımlılıklar yükleniyor..."

# Python paketlerini yükle
pip install -e .

# Eğer yukarıdaki komut başarısız olursa, manuel olarak yükle
if [ $? -ne 0 ]; then
    echo "Manuel kurulum yapılıyor..."
    pip install langchain_chroma langchain_ollama langchain_community langchain_text_splitters langchain_core nltk psutil
fi

# Türkçe stemming kütüphanelerini yükle
echo "Türkçe stemming kütüphaneleri yükleniyor..."
pip install snowballstemmer

# TurkishStemmer'ı yüklemeyi dene
pip install TurkishStemmer || echo "TurkishStemmer yüklenemedi, snowballstemmer kullanılacak."

# NLTK veri setlerini indir
echo "NLTK veri setleri indiriliyor..."
python -c "import nltk; nltk.download('punkt')"

echo "Ollama modelleri kontrol ediliyor..."
# Ollama yüklü mü kontrol et
if command -v ollama &> /dev/null; then
    echo "Ollama bulundu. Gerekli modeller kontrol ediliyor..."
    
    # Modelleri kontrol et ve gerekirse indir
    if ! ollama list | grep -q "llama3.1"; then
        echo "llama3.1 modeli indiriliyor..."
        ollama pull llama3.1
    else
        echo "llama3.1 modeli zaten yüklü."
    fi
    
    if ! ollama list | grep -q "nomic-embed-text"; then
        echo "nomic-embed-text modeli indiriliyor..."
        ollama pull nomic-embed-text
    else
        echo "nomic-embed-text modeli zaten yüklü."
    fi
else
    echo "Ollama bulunamadı. Lütfen Ollama'yı yükleyin: https://ollama.ai/"
fi

echo "Kurulum tamamlandı!"
echo "Sistemi başlatmak için:"
echo "1. Transkript dosyalarını 'transcripts' klasörüne yerleştirin"
echo "2. 'python vector.py --dynamic' komutu ile vektör veritabanını oluşturun"
echo "3. 'python main.py' komutu ile sistemi başlatın" 