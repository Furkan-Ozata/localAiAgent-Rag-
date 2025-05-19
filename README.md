# InspareAI Türkçe Transkript Analiz Sistemi

<div align="center">
  <img src="https://img.shields.io/badge/Sürüm-3.2-blue" alt="Sürüm">
  <img src="https://img.shields.io/badge/Python-3.8+-green" alt="Python">
  <img src="https://img.shields.io/badge/LLM-Llama3.1-orange" alt="LLM">
  <img src="https://img.shields.io/badge/Dil-Türkçe-red" alt="Language">
</div>

## 📚 Genel Bakış

InspareAI, Türkçe konuşma metinlerini (transkriptleri) analiz eden ve kullanıcı sorularına kapsamlı yanıtlar veren gelişmiş bir yapay zeka sistemidir. Sistem, vektör tabanlı arama ve semantik analiz kullanarak transkriptlerdeki bilgilere dayanarak yanıtlar üretir.

### ✨ Özellikler

- **Çok Disiplinli Analiz:** Ekonomi, politika, tarih, bilim, sanat ve diğer disiplinlerde kapsamlı analiz
- **Anahtar Kelime Bazlı Ayıklama:** Sorulardan anahtar kelimeleri çıkararak daha doğru sonuçlar
- **Vektör Tabanlı Arama:** Semantik benzerliğe göre en alakalı içerikleri bulma
- **Kronolojik Analiz:** Zaman sırasına göre olayların gelişimini izleme
- **Konuşmacı Analizi:** Belirli konuşmacıların görüşlerini analiz etme
- **Üç Farklı Arayüz:** Komut satırı, web tabanlı ve sohbet arayüzü seçenekleri
- **Yerel Çalışma:** Tüm işlemler yerel olarak çalışır, internet bağlantısı gerektirmez
- **Önbellek Desteği:** Hızlı yanıt için önbellek sistemi

## 🔧 Sistem Gereksinimleri

- **İşletim Sistemi:** Windows 10/11, macOS veya Linux
- **Python:** 3.8 veya üzeri
- **Ollama:** Yerel AI modelleri için gereken uygulama
- **Bellek:** Minimum 8GB RAM (16GB önerilir)
- **Depolama:** 10GB disk alanı (transkript sayısına göre değişebilir)
- **İşlemci:** Çok çekirdekli işlemci (8+ çekirdek önerilir)

## ⚙️ Kolay Kurulum ve Çalıştırma

Sistemi kolayca kurmak ve çalıştırmak için başlatma scriptini kullanabilirsiniz:

```bash
./run_inspareai.sh
```

Bu script otomatik olarak:

- Ollama servisini kontrol eder
- Gerekli AI modellerini kontrol eder ve eksik olanları indirir
- Python bağımlılıklarını kontrol eder ve eksik olanları kurar
- Vektör veritabanını kontrol eder ve gerekirse oluşturur
- Başlatmak için hangi arayüzü kullanmak istediğinizi sorar

## ⚙️ Manuel Kurulum Adımları

### 1. Bağımlılıkların Kurulumu

Gerekli Python paketlerini kurmak için aşağıdaki komutu çalıştırın:

```bash
pip install -r requirements.txt
```

veya hazır kurulum scriptini kullanabilirsiniz:

```bash
bash install_dependencies.sh
```

### 2. Ollama Kurulumu

Sistem, [Ollama](https://ollama.ai/) aracılığıyla yerel AI modellerini çalıştırır.

1. [ollama.ai](https://ollama.ai/) adresinden Ollama'yı işletim sisteminize uygun olarak indirin ve kurun.
2. Aşağıdaki modelleri indirmek için terminal komutlarını çalıştırın:

```bash
ollama pull llama3.1
ollama pull nomic-embed-text
```

### 3. Transkript Dosyaları

Analiz etmek istediğiniz transkript dosyalarını `transcripts` klasörüne `.txt` formatında ekleyin. Sistem aşağıdaki formatları destekler:

```
0:00:00 - 0:01:30 Speaker A: Konuşma metni...
0:01:31 - 0:02:15 Speaker B: Yanıt metni...
```

veya

```
[00:00:00] Speaker X: Konuşma metni...
[00:01:31] Speaker Y: Yanıt metni...
```

### 4. Vektör Veritabanı Oluşturma

Transkriptleri vektör veritabanına dönüştürmek için aşağıdaki komutu çalıştırın:

```bash
python vector.py
```

Özel seçeneklerle çalıştırma:

```bash
# Dinamik chunking ile yeniden oluşturma
python vector.py --force --dynamic-chunking

# Önbellek kullanmadan ve paralel işleme ile
python vector.py --no-cache --parallel
```

## 🚀 Kullanım

### Kolay Başlatma

Sistemi başlatmak için basitçe:

```bash
./run_inspareai.sh
```

Bu, size iki farklı arayüz seçeneği sunar:

1. Komut Satırı (Terminal) Arayüzü
2. Streamlit Chat Arayüzü

### Manuel Başlatma

#### Komut Satırı Arayüzü

Sistemi komut satırı arayüzü ile kullanmak için:

```bash
python main.py
```

#### Web Arayüzü (Streamlit)

Modern, sohbet tabanlı bir arayüzle kullanmak için:

```bash
streamlit run streamlit_app.py
```

## 🛠 Kullanılabilir Komutlar

Komut satırı arayüzünde şu komutları kullanabilirsiniz:

| Komut                    | Alternatif      | Açıklama                              |
| ------------------------ | --------------- | ------------------------------------- |
| `yardım`                 | `help`          | Yardım ekranını gösterir              |
| `temizle`                | `clear`         | Önbelleği temizler                    |
| `dosyalar`               | `files`         | Transcript dosyalarını listeler       |
| `oku [dosya_adı] [tümü]` | -               | Transkript dosyasını görüntüler       |
| `analiz [metin]`         | -               | Girilen metni analiz eder             |
| `stat`                   | `stats`         | Sistem istatistiklerini gösterir      |
| `bellek`                 | `memory`        | Bellek önbelleğini temizler           |
| `vektör-yenile`          | `vektor-yenile` | Vektör veritabanını yeniden oluşturur |
| `q`                      | `çıkış`         | Programdan çıkar                      |

## 📝 Sorgu İpuçları ve Optimizasyonlar

### Temel İpuçları

- Spesifik sorular daha doğru cevaplar almanızı sağlar
- Sorunuzun başına `!` ekleyerek hızlı yanıt modunu kullanabilirsiniz
- Tarih, zaman aralığı veya konuşmacı belirtmek sonuçların kalitesini artırır

### Gelişmiş Sorgu Teknikleri

- **Kronolojik Analiz:** "kronoloji", "zaman sırası", "gelişme" veya "tarihsel süreç" kelimelerini içeren sorular otomatik olarak zaman sırasına göre analiz edilir
- **Konuşmacı Analizi:** "Speaker A'nın görüşleri" gibi sorularınızda belirli konuşmacıların ifadelerine öncelik verilir
- **Karşılaştırma Analizi:** "karşılaştır", "benzerlik", "fark" gibi kelimeler içeren sorular farklı görüşleri karşılaştırmak için optimize edilir
- **Tema Analizi:** Ekonomi, politika, tarih gibi alanlarda spesifik konular belirtmek daha odaklı yanıtlar almanızı sağlar

## 🔍 Örnek Sorgular

**Temel Sorgular:**

```
NATO ile Türkiye ilişkileri nasıl gelişti?
!Ekonomik krizin aşılması için neler öneriliyor?
Türkiye'nin dış politikadaki vizyonu nedir?
```

**Gelişmiş Sorgular:**

```
Kronolojik olarak Suriye krizi nasıl gelişti?
Speaker A ile Speaker B'nin eğitim hakkındaki görüşlerini karşılaştır.
2020-2022 arası ekonomi politikalarında nasıl bir değişim yaşandı?
Dış politikada Batı ve Doğu eksenlerinin karşılaştırılması nasıl yapılabilir?
```

## 🔧 Performans İyileştirmeleri

Sistem performansını artırmak için:

- **Önbellek Kullanımı:** Sık sorulan sorular ve gömme işlemleri için önbellek otomatik kullanılır
- **Paralel İşleme:** Büyük doküman koleksiyonlarında çoklu işlem desteği
- **Dinamik Chunking:** Belgelere optimum bölme stratejileri uygulanır
- **Metin Normalizasyonu:** Türkçe dil özelliklerine göre metin temizleme ve normalizasyon

## ⚠️ Sorun Giderme

- **Hata: Vektör veritabanı bulunamadı**: `./run_inspareai.sh` veya `python vector.py` komutunu çalıştırarak veritabanını oluşturun
- **Embedding modeli hatası**: Terminal'de `ollama list` komutu ile mevcut modelleri kontrol edin ve eksik modelleri indirin
- **Boş yanıtlar**: Sorularınızı daha spesifik hale getirin veya `temizle` komutuyla önbelleği temizleyin
- **Yavaş yanıtlar**: `!` ile başlayan hızlı yanıt modunu kullanın veya Gradio/Streamlit arayüzünde "Hızlı yanıt modu" seçeneğini etkinleştirin
- **Bellek Yetersizliği**: `vector.py` çalıştırırken bellek hatası alıyorsanız, `python vector.py --chunk-size 600 --overlap 100` ile daha küçük chunk boyutlarıyla çalıştırın

## 🔄 Güncelleme ve Bakım

Sistem güncellemelerinden sonra:

1. Önce güncel kodu çekin veya indirin
2. Bağımlılıkları güncelleyin: `pip install -r requirements.txt --upgrade`
3. Vektör veritabanını yenileyin: `python vector.py --force`
4. Önbellekleri temizleyin: Terminal'de `rm -rf embedding_cache` ve ardından uygulamada `temizle` komutu ile

## 🔒 Güvenlik ve Gizlilik

- Tüm işleme yerel olarak yapılır, veriler dışarı gönderilmez
- Transkript dosyalarınız yalnızca kendi bilgisayarınızda işlenir
- Herhangi bir internet bağlantısı gerektirmez (modelleriniz zaten indirilmişse)

---

© 2023-2025 InspareAI - Türkçe Transkript Analiz Sistemi
