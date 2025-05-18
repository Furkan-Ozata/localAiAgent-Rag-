#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Türkçe Transkript Konu Sınıflandırıcısı
Bu modül, transkriptlerin konularını otomatik olarak sınıflandırmak için kullanılır.
"""

import re
from collections import Counter

class TopicClassifier:
    """
    Türkçe transkriptleri konu alanlarına göre sınıflandıran sınıf.
    Anahtar kelimeler ve konuşma içeriğine dayalı olarak en olası konuları belirler.
    """

    def __init__(self):
        """Konu sınıflandırıcıyı başlat ve konu kategorilerini tanımla"""
        # Konu kategorileri ve ilişkili anahtar kelimeler
        self.topic_keywords = {
            "ekonomi": [
                "ekonomi", "finans", "para", "borsa", "piyasa", "enflasyon", "faiz", "yatırım", 
                "bütçe", "vergi", "ihracat", "ithalat", "döviz", "kur", "banka", "kredi", 
                "tasarruf", "borç", "ticaret", "sermaye", "maliyet", "kâr", "zarar"
            ],
            "siyaset": [
                "siyaset", "politika", "hükümet", "devlet", "cumhuriyet", "meclis", "millet", 
                "seçim", "parti", "demokratik", "iktidar", "muhalefet", "lider", "başkan", 
                "bakan", "dış politika", "anayasa", "yasa", "kanun", "cumhurbaşkanı"
            ],
            "tarih": [
                "tarih", "tarihi", "geçmiş", "antik", "çağ", "imparatorluk", "devrim", "savaş",
                "barış", "anlaşma", "dönem", "yüzyıl", "medeniyet", "uygarlık", "saltanat",
                "hanedan", "padişah", "sultan", "arkeoloji", "tarihsel", "miras"
            ],
            "müzik": [
                "müzik", "şarkı", "beste", "konser", "nota", "melodi", "ritim", "enstrüman",
                "müzisyen", "sanatçı", "albüm", "ses", "tını", "armoni", "orkestra", "senfoni",
                "opera", "şef", "klasik", "pop", "rock", "caz", "rap", "türkü"
            ],
            "tıp_sağlık": [
                "tıp", "sağlık", "hastalık", "tedavi", "doktor", "hekim", "ilaç", "hasta",
                "hastane", "ameliyat", "cerrahi", "tanı", "terapi", "rehabilitasyon", "virüs",
                "bakteri", "pandemi", "salgın", "aşı", "bağışıklık", "genetik", "hücre"
            ],
            "din_felsefe": [
                "din", "inanç", "tanrı", "allah", "islam", "müslüman", "hristiyanlık", "yahudilik",
                "felsefe", "etik", "ahlak", "varoluş", "metafizik", "düşünce", "ruh", "bilinç",
                "maneviyat", "değer", "ibadet", "dua", "inanış", "kutsal"
            ],
            "teknoloji": [
                "teknoloji", "bilgisayar", "yazılım", "donanım", "internet", "dijital", "yapay zeka",
                "robot", "otomasyon", "veri", "bilişim", "uygulama", "ağ", "cihaz", "mobil",
                "siber", "programlama", "yenilik", "inovasyon", "elektronik", "bilgi"
            ],
            "sosyoloji_psikoloji": [
                "sosyoloji", "toplum", "kültür", "davranış", "psikoloji", "birey", "kimlik",
                "kişilik", "sosyal", "toplumsal", "ilişki", "etkileşim", "norm", "değer", "rol",
                "grup", "aidiyet", "gelişim", "travma", "terapi", "bilinç", "bilinçaltı"
            ],
            "sanat": [
                "sanat", "resim", "heykel", "mimari", "tasarım", "estetik", "sergi", "galeri",
                "sanatçı", "eser", "edebiyat", "roman", "şiir", "tiyatro", "sinema", "film",
                "yönetmen", "oyuncu", "senaryo", "gösteri", "performans", "yaratıcılık"
            ],
            "eğitim": [
                "eğitim", "öğretim", "okul", "üniversite", "öğrenci", "öğretmen", "akademik",
                "bilgi", "öğrenme", "sınav", "müfredat", "ders", "kurs", "bölüm", "fakülte",
                "kampüs", "araştırma", "bilimsel", "tez", "eğitmen", "pedagoji"
            ],
            "spor": [
                "spor", "futbol", "basketbol", "voleybol", "tenis", "yüzme", "koşu", "maraton",
                "yarış", "turnuva", "şampiyona", "olimpiyat", "madalya", "takım", "oyuncu",
                "antrenör", "teknik direktör", "maç", "lig", "fitness", "egzersiz"
            ],
            "uluslararası_ilişkiler": [
                "uluslararası", "diplomasi", "nato", "birleşmiş milletler", "ab", "avrupa birliği",
                "küresel", "jeopolitik", "stratejik", "anlaşma", "işbirliği", "çatışma", "barış",
                "güvenlik", "istihbarat", "terör", "savunma", "silah", "müttefik", "ittifak"
            ]
        }

    def classify(self, text, top_n=3):
        """
        Metni konularına göre sınıflandırır
        
        Args:
            text (str): Sınıflandırılacak metin
            top_n (int): Döndürülecek maksimum konu sayısı
            
        Returns:
            list: (konu, skor) tuple'larından oluşan liste, skora göre azalan sırada
        """
        if not text or not isinstance(text, str):
            return []
        
        # Metni küçük harfe çevir ve basit temizlik uygula
        text = text.lower()
        text = re.sub(r'[^\wçğıöşüÇĞİÖŞÜ\s]', ' ', text)
        
        # Kategorileri puan tablosuna dönüştür
        scores = {topic: 0 for topic in self.topic_keywords}
        
        # Her kategori için anahtar kelime eşleşmelerini say
        for topic, keywords in self.topic_keywords.items():
            for keyword in keywords:
                # Düzenli ifade ile kelime sınırlarında tam eşleşme ara
                # Türkçe karakterleri de dikkate alarak
                keyword_pattern = r'\b' + re.escape(keyword) + r'\b'
                matches = re.findall(keyword_pattern, text)
                
                if matches:
                    # Anahtar kelimenin önemine göre puan ver
                    # Daha spesifik kelimeler daha fazla puan alır
                    word_importance = len(keyword) / 5  # Uzun kelimeler genelde daha spesifiktir
                    scores[topic] += len(matches) * (1 + word_importance)
        
        # İçerik uzunluğuna göre normalize et
        word_count = len(text.split())
        for topic in scores:
            if word_count > 0:
                scores[topic] = scores[topic] / (word_count ** 0.5)  # Karekök ile normalize et
        
        # Sonuçları sırala ve en yüksek skorlu top_n kategoriyi döndür
        results = sorted([(topic, score) for topic, score in scores.items() if score > 0], 
                        key=lambda x: x[1], reverse=True)
        
        return results[:top_n]

    def get_topic_description(self, topic):
        """
        Konu için açıklama döndürür
        
        Args:
            topic (str): Konu adı
            
        Returns:
            str: Konu açıklaması
        """
        descriptions = {
            "ekonomi": "Ekonomi, finans, piyasalar, ticaret ve ekonomik politikalar",
            "siyaset": "Siyaset, hükümet politikaları, siyasi partiler ve yönetim",
            "tarih": "Tarihsel olaylar, dönemler, kişiler ve medeniyetler",
            "müzik": "Müzik teorisi, türleri, sanatçılar ve müzik dünyası",
            "tıp_sağlık": "Tıbbi bilgiler, sağlık konuları, hastalıklar ve tedaviler",
            "din_felsefe": "Dini inanışlar, felsefi görüşler ve düşünce sistemleri",
            "teknoloji": "Teknolojik gelişmeler, dijital yenilikler ve bilişim dünyası",
            "sosyoloji_psikoloji": "Toplumsal yapılar, davranış bilimleri ve psikoloji",
            "sanat": "Sanatsal çalışmalar, sanat tarihi, estetiği ve sanat dünyası",
            "eğitim": "Eğitim sistemleri, öğrenme metodları ve akademik konular",
            "spor": "Sportif faaliyetler, spor organizasyonları ve spor dünyası",
            "uluslararası_ilişkiler": "Ülkeler arası ilişkiler, diplomatik konular ve küresel politika"
        }
        
        return descriptions.get(topic, "Belirli bir konu kategorisi")
        
# Test için direkt çalıştırma
if __name__ == "__main__":
    # Test metni
    test_text = """
    Türkiye'nin ekonomik durumu son yıllarda ciddi dalgalanmalar yaşadı. 
    Enflasyon rakamları endişe verici seviyelere ulaştı ve döviz kurlarındaki
    değişkenlik ekonomik belirsizliği artırdı. Merkez Bankası'nın faiz politikaları
    ve hükümetin ekonomi yönetimi stratejisi sıkça tartışma konusu oldu.
    """
    
    classifier = TopicClassifier()
    topics = classifier.classify(test_text)
    
    print("Tespit Edilen Konular:")
    for topic, score in topics:
        print(f"- {topic}: {score:.4f} - {classifier.get_topic_description(topic)}")
