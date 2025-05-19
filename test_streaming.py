#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
InspareAI Test Streaming - Akademik Format Streaming Testi
"""

from main import query_transcripts

def print_chunk(chunk):
    """Stream edilen her parçayı ekrana yazdır"""
    print(chunk, end="", flush=True)

def test_streaming():
    """Streaming özelliğini test et"""
    print("Streaming özelliği test ediliyor...")
    print("-----------------------------------")
    
    # Test sorusu
    test_question = "Türkiye'nin dış politikası nedir?"
    
    # Streaming callback ile sorgu yap
    print("Yanıt:\n")
    query_transcripts(test_question, stream_callback=print_chunk)
    
    print("\n-----------------------------------")
    print("Test tamamlandı.")

if __name__ == "__main__":
    test_streaming()
