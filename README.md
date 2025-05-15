# Türkçe Konuşma Metni Analiz Sistemi (İyileştirilmiş Sürüm)

Bu sistem, Türkçe konuşma metinlerini analiz etmek ve kullanıcı sorularına hızlı, doğru ve kapsamlı yanıtlar sağlamak için geliştirilmiştir. Son iyileştirmelerle daha verimli çalışmakta ve daha kaliteli yanıtlar üretmektedir.

## Temel Özellikler

- **Gelişmiş Vektör Veritabanı**: Belgeler önceden işlenir ve optimize edilmiş vektör veritabanına kaydedilir
- **Türkçe Dil Optimizasyonu**: Türkçe metinler için özel geliştirilen temizleme ve normalleştirme özellikleri
- **Çift Katmanlı Önbellek**: Hem disk hem bellek tabanlı önbellek ile ultra hızlı yanıtlar
- **Anahtar Kelime Analizi**: Sorguları analiz ederek en alakalı dokümanları bulma
- **Paralel İşleme**: Çoklu sorguları eşzamanlı yanıtlama
- **Fine-Tuning Desteği**: Llama modelini Türkçe için özelleştirme araçları
- **Hızlı Yanıt Modu**: Daha az doküman kullanarak "!" ön ekli hızlı yanıtlar

## Sistem Mimarisi

Sistem üç ana bileşenden oluşur:

1. **vector.py**: Belgeleri vektörleştirir ve Chroma veritabanında saklar (bir kez çalıştırılır)
2. **main.py**: Kullanıcı sorularını yanıtlamak için vektör veritabanını kullanır
3. **Modelfile**: Llama modelini Türkçe için fine-tune etmek amacıyla kullanılır

## Kurulum ve Kullanım

### Gerekli Bağımlılıklar

```bash
pip install -r requirements.txt
```

### Belgeleri Vektörleştirme (Tek Seferlik)

1. Transkript dosyalarınızı `transcripts` klasörüne `.txt` formatında ekleyin
2. Vektörleştirme işlemini başlatın:

```bash
python vector.py
```

Bu işlem, dosya sayısına ve boyutuna bağlı olarak zaman alabilir. İşlem tamamlandıktan sonra, bir `chrome_langchain_db` klasörü oluşturulacaktır.

### Sorgulama Sistemi Kullanımı

Vektörleştirme tamamlandıktan sonra, sistem hızlı bir şekilde sorularınızı yanıtlamaya hazırdır:

```bash
python main.py
```

### Türkçe Fine-Tuning (İsteğe Bağlı)

Daha iyi Türkçe yanıtlar için modelinizi fine-tune edebilirsiniz:

1. Modelfile dosyasını kullanarak yeni bir model oluşturun:

```bash
ollama create turkce-llama -f Modelfile
```

2. Fine-tuning örneklerini kullanarak modeli Türkçe için eğitin:

```bash
ollama create turkce-llama-ft -f Modelfile --from turkce-llama fine_tune_samples.json
```

3. Fine-tune edilmiş modeli kullanmak için `main.py` dosyasını düzenleyin:

```python
model = OllamaLLM(
    model="turkce-llama-ft",  # Türkçe için fine-tune edilmiş model
    # diğer parametreler...
)
```

## Kullanım İpuçları

- Yeni belgeler eklediğinizde, `vector.py` dosyasını tekrar çalıştırın
- Spesifik sorular daha doğru yanıtlar sağlar
- Hızlı yanıt için sorularınızın başına `!` ekleyin
- Konuşmacı isimleri veya zaman aralıkları belirterek daha hedefli sonuçlar alabilirsiniz
- Bellek önbelleği temizlemek için 'bellek' veya 'memory' komutunu kullanın

## Özel Komutlar

Program içinde kullanabileceğiniz özel komutlar:

- `yardım` veya `help`: Yardım menüsü
- `geçmiş` veya `history`: Konuşma geçmişini görüntüler
- `temizle` veya `clear`: Disk önbelleğini temizler
- `bellek` veya `memory`: Bellek önbelleğini temizler
- `dosyalar` veya `files`: Transcript dosyalarını listeler
- `stat` veya `stats`: Sistem istatistiklerini gösterir
- `q` veya `çıkış`: Programdan çıkar

## Performans İyileştirmeleri

Son güncellemelerle yapılan performans iyileştirmeleri:

1. **Daha İyi Vektör Parametreleri**: HNSW ile cosine benzerliği, optimize edilmiş constructor ve search parametreleri
2. **Türkçe Metin İşleme**: Özel geliştirilen temizleme ve normalleştirme
3. **Bellek Yönetimi**: Akıllı önbellek ve bellek temizleme
4. **Anahtar Kelime Çıkarma**: Sorguları daha iyi anlamak için kök analizi
5. **Paralel İşleme**: Çoklu sorguları aynı anda işleme

## Fine-Tuning Hakkında

Fine-tuning, Llama modelinin Türkçe metinleri daha iyi anlaması ve yanıtlaması için önemlidir. Bu süreçte:

1. Modelfile, Türkçe diline özgü sistem talimatları içerir
2. fine_tune_samples.json dosyası eğitim için örnek verileri içerir
3. Eğitim süreci, modelin Türkçe metinleri daha iyi anlamasını sağlar

Fine-tuning sürecinin etkinliği, örnek verilerin kalitesine ve miktarına bağlıdır. Eğitim verilerini zenginleştirerek daha iyi sonuçlar elde edebilirsiniz.

## Sorun Giderme

- **Hata: Vektör veritabanı bulunamadı**: `python vector.py` komutunu çalıştırarak veritabanını oluşturun
- **Beklenmeyen yanıtlar**: Önbelleği `temizle` komutuyla temizleyin ve soruyu yeniden sorun
- **Yavaş yanıt süreleri**: `!` ön ekiyle hızlı yanıt modunu kullanın
- **Bellek sorunları**: `bellek` komutuyla bellek önbelleğini temizleyin

## Gelecek Geliştirmeler

- Türkçe doğal dil işleme modüllerinin daha derin entegrasyonu
- Konuşma metinlerinden otomatik özet çıkarma
- Çok dilli destek (Türkçe odaklı kalarak)
- Sesli soru-cevap desteği
