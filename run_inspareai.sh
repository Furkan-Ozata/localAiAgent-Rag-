#!/bin/bash

# InspareAI - Başlatma Scripti
# Bu script, InspareAI sistemini kolayca başlatır

# Renkli çıktılar için ANSI kodları
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== InspareAI Türkçe Konuşma Analiz Sistemi ===${NC}"
echo -e "${BLUE}Sürüm 3.2 - Geliştirici: InspareAI Ekibi${NC}\n"

# Ollama'nın çalışıp çalışmadığını kontrol et
echo -e "${YELLOW}Ollama servisi kontrol ediliyor...${NC}"
if ! command -v ollama &> /dev/null; then
    echo -e "${RED}Hata: Ollama bulunamadı! Lütfen Ollama'yı yükleyin.${NC}"
    echo "İndirme adresi: https://ollama.ai"
    exit 1
fi

# Ollama'nın çalışıp çalışmadığını kontrol et
if ! ollama list &> /dev/null; then
    echo -e "${RED}Hata: Ollama servisi çalışmıyor! Lütfen Ollama'yı başlatın.${NC}"
    echo "Terminal'de 'ollama serve' komutunu çalıştırın."
    exit 1
fi

echo -e "${GREEN}✓ Ollama servisi çalışıyor${NC}\n"

# Gerekli modellerin var olup olmadığını kontrol et
echo -e "${YELLOW}Gerekli modeller kontrol ediliyor...${NC}"
MODELS=$(ollama list)

# LLM modeli kontrolü
if echo "$MODELS" | grep -q "llama3.1"; then
    echo -e "${GREEN}✓ llama3.1 modeli mevcut${NC}"
else
    echo -e "${YELLOW}llama3.1 modeli indiriliyor...${NC}"
    ollama pull llama3.1
fi

# Embedding modeli kontrolü
EMBEDDING_FOUND=false
for MODEL in "nomic-embed-text" "mxbai-embed-large" "mistral-embed"; do
    if echo "$MODELS" | grep -q "$MODEL"; then
        echo -e "${GREEN}✓ $MODEL embedding modeli mevcut${NC}"
        EMBEDDING_FOUND=true
        break
    fi
done

if [ "$EMBEDDING_FOUND" = false ]; then
    echo -e "${YELLOW}Embedding modeli indiriliyor (nomic-embed-text)...${NC}"
    ollama pull nomic-embed-text
fi

echo ""

# Bağımlılıkların kontrolü
echo -e "${YELLOW}Bağımlılıklar kontrol ediliyor...${NC}"
if ! pip show streamlit &> /dev/null || ! pip show gradio &> /dev/null; then
    echo -e "${YELLOW}Eksik bağımlılıklar tespit edildi. Kurulum yapılıyor...${NC}"
    pip install -r requirements.txt
else
    echo -e "${GREEN}✓ Gerekli Python bağımlılıkları kurulu${NC}"
fi

echo ""

# Vektör veritabanı kontrolü
if [ ! -d "chrome_langchain_db" ]; then
    echo -e "${YELLOW}Vektör veritabanı bulunamadı. Oluşturuluyor...${NC}"
    echo -e "${YELLOW}Bu işlem biraz zaman alabilir...${NC}"
    python vector.py
else
    echo -e "${GREEN}✓ Vektör veritabanı mevcut${NC}"
fi

echo ""

# Arayüz seçimi
echo -e "${BLUE}InspareAI'yi hangi arayüzle başlatmak istersiniz?${NC}"
echo "1) Komut Satırı (Terminal)"
echo "2) Gradio Web Arayüzü"
echo "3) Streamlit Chat Arayüzü"
echo "4) Çıkış"

read -p "Seçiminiz (1-4): " choice

case $choice in
    1)
        echo -e "\n${GREEN}Komut satırı arayüzü başlatılıyor...${NC}"
        python main.py
        ;;
    2)
        echo -e "\n${GREEN}Gradio web arayüzü başlatılıyor...${NC}"
        python helpers.py
        ;;
    3)
        echo -e "\n${GREEN}Streamlit chat arayüzü başlatılıyor...${NC}"
        streamlit run streamlit_app.py
        ;;
    4)
        echo -e "\n${YELLOW}İyi günler!${NC}"
        exit 0
        ;;
    *)
        echo -e "\n${RED}Geçersiz seçenek. Çıkılıyor.${NC}"
        exit 1
        ;;
esac
