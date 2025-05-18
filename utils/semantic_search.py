#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Türkçe Semantik Arama Geliştirici
Bu modül, vektör veritabanı sorgularının semantik kalitesini artırır.
"""

import re
import numpy as np
from typing import List, Dict, Any, Tuple, Union

class SemanticSearchEnhancer:
    """
    Semantik aramaları iyileştiren ve çeşitlendiren sınıf.
    Sorgu genişletme, yeniden sıralama ve filtreleme özellikleri içerir.
    """
    
    def __init__(self, vectorstore=None, retriever=None):
        """
        Semantik arama güçlendiricisini başlatır
        
        Args:
            vectorstore: Vektör veritabanı
            retriever: Retriever objesi
        """
        self.vectorstore = vectorstore
        self.retriever = retriever
        
        # Yüksek kaliteli arama sonuçları için minimum benzerlik eşiği
        self.similarity_threshold = 0.2
        
        # Sorgu genişletme için yaygın Türkçe konuları ve ilişkili terimler
        self.topic_expansion = {
            # Ekonomi
            "ekonomi": ["finans", "piyasa", "enflasyon", "faiz", "ticaret"],
            "finans": ["ekonomi", "yatırım", "borsa", "para", "banka"],
            "para": ["ekonomi", "döviz", "kur", "finans", "banka"],
            "enflasyon": ["fiyat", "artış", "ekonomi", "faiz", "pahalılık"],
            
            # Siyaset
            "siyaset": ["politik", "hükümet", "parti", "seçim", "iktidar"],
            "hükümet": ["devlet", "iktidar", "politika", "yönetim", "kabine"],
            "parti": ["siyasi", "muhalefet", "iktidar", "seçim", "teşkilat"],
            
            # Teknoloji
            "teknoloji": ["dijital", "yazılım", "internet", "bilişim", "yapay zeka"],
            "yazılım": ["program", "uygulama", "kod", "geliştirme", "teknoloji"],
            "internet": ["web", "çevrimiçi", "site", "teknoloji", "dijital"],
            
            # Sanat ve Kültür
            "sanat": ["kültür", "estetik", "müze", "sergi", "eser"],
            "müzik": ["şarkı", "sanatçı", "konser", "albüm", "beste"],
            "sinema": ["film", "yönetmen", "oyuncu", "senaryo", "festival"],
            
            # Din ve Felsefe
            "din": ["inanç", "allah", "ibadet", "dini", "kutsal"],
            "islam": ["müslüman", "kuran", "namaz", "din", "ibadet"],
            "felsefe": ["düşünce", "filozof", "etik", "metafizik", "mantık"]
        }
    
    def enhance_query(self, query: str) -> str:
        """
        Sorguyu zenginleştirir
        
        Args:
            query: Orijinal sorgu metni
            
        Returns:
            Geliştirilmiş sorgu metni
        """
        # Sorgu çok kısaysa doğrudan döndür
        if len(query) < 5:
            return query
            
        # Sorguyu küçük harfe çevir
        query_lower = query.lower()
        
        # Noktalama işaretleri ve özel karakterlerin kaldırılması
        query_clean = re.sub(r'[^\wçğıöşüÇĞİÖŞÜ\s]', ' ', query_lower)
        
        # Sorgu kelimelerini çıkar
        query_terms = query_clean.split()
        
        # Genişletilmiş sorgu için ek terimler
        expansion_terms = set()
        
        # Sorgu terimlerini topic_expansion sözlüğünde ara
        for term in query_terms:
            if term in self.topic_expansion:
                # Her terim için en fazla 2 genişletme terimi ekle (ilk ikisi)
                expansion_terms.update(self.topic_expansion[term][:2])
        
        # Genişletme terimleri ekle, çok uzun bir sorgu oluşturmaktan kaçın
        if expansion_terms and len(query_terms) < 8:
            # Toplam genişletme terimi sayısını sınırla
            expansion_list = list(expansion_terms)[:3]  # En fazla 3 terim ekle
            enhanced_query = f"{query} {' '.join(expansion_list)}"
            print(f"Sorgu genişletildi: {query} → {enhanced_query}")
            return enhanced_query
        
        return query
    
    def rerank_results(self, query: str, results: List[Any]) -> List[Any]:
        """
        Arama sonuçlarını yeniden sıralar
        
        Args:
            query: Sorgu metni
            results: Orijinal arama sonuçları listesi
            
        Returns:
            Yeniden sıralanmış sonuçlar listesi
        """
        if not results:
            return []
        
        # Sonuçların zaten final_score niteliği varsa, sıralama gerekli değil
        if hasattr(results[0], 'final_score') and not all(getattr(r, 'final_score', 0) == 0 for r in results):
            return sorted(results, key=lambda r: getattr(r, 'final_score', 0), reverse=True)
        
        # Temel anlamsal benzerlikleri koru
        # Bu, orijinal benzerlik skorlarını hesaplamak için kullanılabilir
        return results
    
    def hybrid_search(self, query: str, k: int = 10, filter_metadata: Dict = None, fetch_k: int = 50) -> List[Any]:
        """
        Çoklu arama stratejileriyle hibrit bir arama gerçekleştirir
        
        Args:
            query: Arama sorgusu
            k: Döndürülecek sonuç sayısı
            filter_metadata: Filtreleme için metadata kriterleri
            fetch_k: İlk arama için alınacak sonuç sayısı
            
        Returns:
            İyileştirilmiş sonuçlar listesi
        """
        if not self.vectorstore or not self.retriever:
            print("Vektör veritabanı veya retriever tanımlanmamış")
            return []
        
        # Sorguyu zenginleştir
        enhanced_query = self.enhance_query(query)
        
        try:
            # Geçici olarak retriever parametrelerini kaydet
            original_k = self.retriever.search_kwargs.get("k", k)
            original_fetch_k = self.retriever.search_kwargs.get("fetch_k", fetch_k)
            
            # Arama parametrelerini ayarla
            self.retriever.search_kwargs["k"] = k
            self.retriever.search_kwargs["fetch_k"] = fetch_k
            
            if filter_metadata:
                original_filter = self.retriever.search_kwargs.get("filter", None)
                self.retriever.search_kwargs["filter"] = filter_metadata
            
            # Temel semantik arama (geliştirilmiş sorgu ile)
            basic_results = self.retriever.invoke(enhanced_query)
            
            # Orijinal parametreleri geri yükle
            self.retriever.search_kwargs["k"] = original_k
            self.retriever.search_kwargs["fetch_k"] = original_fetch_k
            
            if filter_metadata:
                self.retriever.search_kwargs["filter"] = original_filter
            
            # Sonuçları yeniden sırala
            ranked_results = self.rerank_results(query, basic_results)
            
            return ranked_results
            
        except Exception as e:
            print(f"Hibrit arama sırasında hata: {e}")
            # Basit bir arama yap
            return self.retriever.invoke(query)
    
    def search_with_context(self, query: str, context_query: str = None, k: int = 10) -> List[Any]:
        """
        Ek bağlam bilgisiyle birlikte arama yapar
        
        Args:
            query: Ana sorgu
            context_query: Önceki sorgu veya bağlam bilgisi
            k: Döndürülecek sonuç sayısı
            
        Returns:
            İyileştirilmiş sonuçlar listesi
        """
        if not context_query:
            return self.hybrid_search(query, k=k)
        
        # Ana sorgu ve bağlam sorgusunu birleştir
        combined_query = f"{query} {context_query}"
        
        # Birleştirilmiş sorgu ile arama yap
        results = self.hybrid_search(combined_query, k=k//2, fetch_k=k*3)
        
        # Ana sorgu ile de arama yap
        primary_results = self.hybrid_search(query, k=k//2, fetch_k=k*2)
        
        # Sonuçları birleştir ve yinelemeleri kaldır
        seen_ids = set()
        merged_results = []
        
        # Önce birincil sonuçları ekle
        for res in primary_results:
            doc_id = getattr(res, "id", None) or id(res)
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                merged_results.append(res)
        
        # Sonra bağlam aramasını ekle
        for res in results:
            doc_id = getattr(res, "id", None) or id(res)
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                merged_results.append(res)
        
        # Son olarak k sonuç olana kadar kes
        return merged_results[:k]
        
# Test için direkt çalıştırma
if __name__ == "__main__":
    print("SemanticSearchEnhancer test ediliyor...")
    # Varsayılan nesneyi oluştur (vektör veritabanı yok)
    enhancer = SemanticSearchEnhancer()
    
    # Sorgu geliştirmeyi test et
    test_queries = [
        "ekonomide enflasyon nasıl etkiledi",
        "siyasi partilerin görüşleri",
        "teknoloji şirketleri"
    ]
    
    for query in test_queries:
        enhanced = enhancer.enhance_query(query)
        print(f"Orijinal: '{query}' → Geliştirilmiş: '{enhanced}'")
