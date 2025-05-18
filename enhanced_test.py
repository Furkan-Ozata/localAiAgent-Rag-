#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Türkçe Transkript Analiz Sistemi - Kapsamlı Test Betiği v2.0
Bu betik, sistemin RAG yeteneklerini ve farklı konu alanlarındaki performansını test eder.
"""

import os
import sys
import time
import importlib
import unittest
import subprocess
from typing import List, Dict, Any

# Ana sistem modüllerini içe aktar (varsa)
try:
    from main import query_transcripts, extract_keywords, calculate_relevance, format_sources
    from vector import retriever, vectorstore
    SYSTEM_MODULES_LOADED = True
    print("✓ Ana sistem modülleri başarıyla yüklendi")
except ImportError as e:
    SYSTEM_MODULES_LOADED = False
    print(f"✗ Ana sistem modüllerini yükleme başarısız: {e}")

# Gelişmiş modülleri içe aktar (varsa)
try:
    from text_analyzer import TextAnalyzer
    TEXT_ANALYZER_LOADED = True
    print("✓ Metin analiz modülü başarıyla yüklendi")
except ImportError:
    TEXT_ANALYZER_LOADED = False
    print("✗ Metin analiz modülü bulunamadı")

try:
    from topic_classifier import TopicClassifier
    TOPIC_CLASSIFIER_LOADED = True
    print("✓ Konu sınıflandırıcı modülü başarıyla yüklendi")
except ImportError:
    TOPIC_CLASSIFIER_LOADED = False
    print("✗ Konu sınıflandırıcı modülü bulunamadı")

try:
    from semantic_search import SemanticSearchEnhancer
    SEMANTIC_SEARCH_LOADED = True
    print("✓ Semantik arama modülü başarıyla yüklendi")
except ImportError:
    SEMANTIC_SEARCH_LOADED = False
    print("✗ Semantik arama modülü bulunamadı")

class SystemConfig:
    """Sistem ayarlarını ve durumunu takip eder"""
    def __init__(self):
        self.transcripts_dir = "transcripts"
        self.vectordb_dir = "chrome_langchain_db"
        self.has_transcripts = os.path.exists(self.transcripts_dir) and len(os.listdir(self.transcripts_dir)) > 0
        self.has_vectordb = os.path.exists(self.vectordb_dir)
        self.ollama_installed = self._check_ollama()
        self.model_loaded = self._check_model()
        
    def _check_ollama(self):
        """Ollama'nın yüklü olup olmadığını kontrol eder"""
        try:
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
            
    def _check_model(self):
        """Llama modelinin yüklü olup olmadığını kontrol eder"""
        if not self.ollama_installed:
            return False
            
        try:
            result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
            return "llama3.1" in result.stdout
        except:
            return False
            
    def print_status(self):
        """Sistem durumunu gösterir"""
        print("\n=== Sistem Durumu ===")
        print(f"Transkript Klasörü: {'✓ Mevcut' if self.has_transcripts else '✗ Eksik'}")
        print(f"Vektör Veritabanı: {'✓ Mevcut' if self.has_vectordb else '✗ Eksik'}")
        print(f"Ollama: {'✓ Kurulu' if self.ollama_installed else '✗ Kurulu değil'}")
        print(f"LLama3.1 Modeli: {'✓ Yüklü' if self.model_loaded else '✗ Yüklü değil'}")
        print(f"Ana Modüller: {'✓ Yüklü' if SYSTEM_MODULES_LOADED else '✗ Yüklü değil'}")
        print(f"Gelişmiş Modüller: "
              f"{'✓' if TEXT_ANALYZER_LOADED else '✗'} TextAnalyzer, "
              f"{'✓' if TOPIC_CLASSIFIER_LOADED else '✗'} TopicClassifier, "
              f"{'✓' if SEMANTIC_SEARCH_LOADED else '✗'} SemanticSearchEnhancer")
        
        print("\nKurulum Durumu: ", end="")
        if (self.has_transcripts and self.has_vectordb and
            self.ollama_installed and self.model_loaded and
            SYSTEM_MODULES_LOADED):
            print("✓ Sistem çalışmaya hazır")
        else:
            print("✗ Bazı bileşenler eksik")

class TestQueryEngine(unittest.TestCase):
    """Sorgu motorunun temel işlevlerini test eder"""
    
    @unittest.skipIf(not SYSTEM_MODULES_LOADED, "Ana modüller yüklü değil")
    def test_keyword_extraction(self):
        """Anahtar kelime çıkarma işlevini test eder"""
        test_queries = [
            "Ekonomik kriz ne zaman başladı?",
            "Müzik türlerinin tarihsel gelişimi nasıldır?",
            "Siyasi partilerin seçim stratejileri nelerdir?"
        ]
        
        for query in test_queries:
            keywords = extract_keywords(query)
            self.assertIsNotNone(keywords, f"{query} için anahtar kelimeler None")
            self.assertGreater(len(keywords), 0, f"{query} için anahtar kelime bulunamadı")
            print(f"'{query}' için bulunan anahtar kelimeler: {keywords}")
    
    @unittest.skipIf(not SYSTEM_MODULES_LOADED or not 'retriever' in globals(), "Retriever kullanılamıyor")
    def test_document_retrieval(self):
        """Belge getirme işlevini test eder"""
        if not retriever:
            self.skipTest("Retriever nesnesi tanımlı değil")
            
        test_query = "ekonomi"
        try:
            docs = retriever.invoke(test_query)
            self.assertIsNotNone(docs, "Getirilen dokümanlar None")
            self.assertGreater(len(docs), 0, "Hiç doküman getirilemedi")
            print(f"'{test_query}' sorgusu için {len(docs)} doküman getirildi")
        except Exception as e:
            self.fail(f"Doküman getirme başarısız: {e}")

class TestEnhancedFeatures(unittest.TestCase):
    """Gelişmiş özellikleri test eder"""
    
    @unittest.skipIf(not TEXT_ANALYZER_LOADED, "TextAnalyzer modülü yüklü değil")
    def test_text_analyzer(self):
        """Metin analiz modülünü test eder"""
        analyzer = TextAnalyzer()
        test_text = "Türkiye'de ekonomik durum son yıllarda çeşitli dalgalanmalar gösterdi."
        
        # Metin ön işleme testi
        preprocessed = analyzer.preprocess_text(test_text)
        self.assertIsNotNone(preprocessed, "Ön işlenmiş metin None")
        self.assertGreater(len(preprocessed), 0, "Ön işlenmiş metin boş")
        
        # Anahtar kelime çıkarma testi
        keywords = analyzer.extract_keywords(test_text)
        self.assertIsNotNone(keywords, "Anahtar kelimeler None")
        self.assertGreater(len(keywords), 0, "Anahtar kelimeler boş")
        
        print(f"TextAnalyzer testleri başarılı: {len(keywords)} anahtar kelime bulundu")
    
    @unittest.skipIf(not TOPIC_CLASSIFIER_LOADED, "TopicClassifier modülü yüklü değil")
    def test_topic_classifier(self):
        """Konu sınıflandırıcı modülünü test eder"""
        classifier = TopicClassifier()
        test_texts = {
            "ekonomi": "Enflasyon rakamları son açıklandığında piyasalar sert tepki verdi.",
            "siyaset": "Parti liderleri seçim öncesi son mitinglerini düzenliyor.",
            "müzik": "Konserde yeni albümün şarkıları ilk kez seslendirildi."
        }
        
        for expected_topic, text in test_texts.items():
            topics = classifier.classify(text)
            self.assertIsNotNone(topics, f"{expected_topic} için konular None")
            self.assertGreater(len(topics), 0, f"{expected_topic} için konular boş")
            
            topic_names = [t[0] for t in topics]
            print(f"'{text}' için tespit edilen konular: {topic_names}")
    
    @unittest.skipIf(not SEMANTIC_SEARCH_LOADED, "SemanticSearchEnhancer modülü yüklü değil")
    def test_semantic_search(self):
        """Semantik arama modülünü test eder"""
        enhancer = SemanticSearchEnhancer()
        test_queries = [
            "ekonomi nasıl etkilendi",
            "siyasi görüşler",
            "müzik festivallerinin etkisi"
        ]
        
        for query in test_queries:
            enhanced = enhancer.enhance_query(query)
            self.assertIsNotNone(enhanced, f"{query} için geliştirilmiş sorgu None")
            self.assertGreaterEqual(len(enhanced), len(query), 
                                   f"{query} için geliştirilmiş sorgu kısaldı")
            print(f"'{query}' için geliştirilmiş sorgu: '{enhanced}'")

class TestEndToEnd(unittest.TestCase):
    """Uçtan uca sistem testleri"""
    
    @classmethod
    def setUpClass(cls):
        """Test sınıfı başlamadan önce çalışır"""
        cls.config = SystemConfig()
        if not cls.config.has_transcripts or not cls.config.has_vectordb:
            cls.skipTest(cls, "Gerekli dosyalar mevcut değil")
    
    @unittest.skipIf(not SYSTEM_MODULES_LOADED, "Ana modüller yüklü değil")
    def test_basic_query(self):
        """Temel sorgu işlevini test eder"""
        if not 'query_transcripts' in globals():
            self.skipTest("query_transcripts fonksiyonu tanımlı değil")
            
        # Çok basit bir sorgu - hata vermeden çalışması gerekir
        try:
            result = query_transcripts("test")
            self.assertIsNotNone(result, "Sorgu sonucu None")
            print("Temel sorgu testi başarılı")
        except Exception as e:
            self.fail(f"Temel sorgu başarısız: {e}")
    
    @unittest.skipIf(not SYSTEM_MODULES_LOADED, "Ana modüller yüklü değil")
    def test_common_topics(self):
        """Yaygın konu alanlarında sorguları test eder"""
        if not 'query_transcripts' in globals():
            self.skipTest("query_transcripts fonksiyonu tanımlı değil")
            
        # Farklı konu alanlarından sorular
        topic_queries = {
            "ekonomi": "ekonomik durum nedir",
            "siyaset": "siyasi partilerin görüşleri",
            "teknoloji": "teknolojik gelişmeler",
            "sanat": "sanatsal etkinlikler",
            "spor": "spor müsabakaları"
        }
        
        for topic, query in topic_queries.items():
            try:
                print(f"\n--- {topic.upper()} KONUSU TEST EDİLİYOR ---")
                start_time = time.time()
                # Kısa cevap için sınırlandırılmış sorgu
                result = query_transcripts(f"{query} kısaca")
                duration = time.time() - start_time
                
                self.assertIsNotNone(result, f"{topic} sorgusu sonucu None")
                print(f"{topic} sorgusu başarılı ({duration:.2f} saniye)")
                
                # Cevabın ilk 100 karakterini göster
                preview = result[:100] + "..." if len(result) > 100 else result
                print(f"Önizleme: {preview}")
                
            except Exception as e:
                print(f"{topic} sorgusu başarısız: {e}")

def run_tests():
    """Testleri çalıştır"""
    # Önce sistem durumunu göster
    config = SystemConfig()
    config.print_status()
    
    # Testleri çalıştır
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

if __name__ == "__main__":
    run_tests()
