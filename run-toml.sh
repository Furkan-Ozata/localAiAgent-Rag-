#!/usr/bin/env bash

# run-toml.sh - pyproject.toml komut çalıştırıcısı
# Bu script, pyproject.toml içindeki komutları çalıştırmak için kullanılır

# Renk kodları
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Başlık yazdır
echo -e "${CYAN}╔══════════════════════════════════════╗"
echo -e "║      InspareAI Script Runner       ║"
echo -e "╚══════════════════════════════════════╝${NC}"
echo ""

# pyproject.toml dosyasını kontrol et
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Hata: pyproject.toml dosyası bulunamadı.${NC}"
    exit 1
fi

# Yardım fonksiyonu
print_help() {
    echo -e "${BLUE}Kullanım:${NC} ./run-toml.sh <komut>"
    echo ""
    echo -e "${YELLOW}Kullanılabilir komutlar:${NC}"
    echo ""
    
    # pyproject.toml dosyasından komutları çıkar ve formatla
    local scripts=$(grep -A 20 "\[tool.inspareai.scripts\]" pyproject.toml | grep -v "\[tool.inspareai.scripts\]" | grep "=" | sed 's/\"//g' | sed 's/^[[:space:]]*//')
    
    while IFS= read -r line; do
        if [[ "$line" == *"="* ]]; then
            local name=$(echo "$line" | cut -d '=' -f 1 | xargs)
            local command=$(echo "$line" | cut -d '=' -f 2- | xargs)
            echo -e "  ${GREEN}${name}${NC}"
            echo -e "    └─ ${BLUE}${command}${NC}"
        fi
    done <<< "$scripts"
    
    echo ""
}

# Komut bulma ve çalıştırma fonksiyonu
run_command() {
    local script_name=$1
    local script_cmd=""
    
    # Komutu pyproject.toml dosyasında ara
    script_cmd=$(grep -A 20 "\[tool.inspareai.scripts\]" pyproject.toml | grep "^${script_name} =" | head -1 | cut -d '=' -f 2- | tr -d '"' | xargs)
    
    if [[ -z "$script_cmd" ]]; then
        echo -e "${RED}Hata:${NC} '$script_name' komutu pyproject.toml dosyasında bulunamadı."
        print_help
        exit 1
    fi
    
    echo -e "${CYAN}Çalıştırılıyor: ${YELLOW}${script_cmd}${NC}"
    echo -e "${CYAN}─────────────────────────────────────────────${NC}"
    echo ""
    
    # Komutu çalıştır
    eval "$script_cmd"
    
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo -e "${RED}Komut başarısız oldu (kod: $exit_code)${NC}"
        exit $exit_code
    fi
}

# Ana kod
if [[ "$1" == "--help" || "$1" == "-h" || "$1" == "" ]]; then
    print_help
else
    run_command "$1"
fi
