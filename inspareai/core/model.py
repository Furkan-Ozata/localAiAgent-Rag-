#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
InspareAI - LLM Model Yapılandırması.
Bu modül, LLM modellerin yapılandırmasını ve yönetimini içerir.
"""

from langchain_ollama import OllamaLLM

def create_model(model_name="llama3.1", temperature=0.5, num_threads=8):
    """
    Ana LLM modelini oluşturur.
    
    Args:
        model_name (str): Kullanılacak modelin adı
        temperature (float): Oluşturulan metinlerin çeşitliliği için sıcaklık değeri
        num_threads (int): Paralel işlem için kullanılacak thread sayısı
        
    Returns:
        OllamaLLM: Yapılandırılmış LLM modeli
    """
    return OllamaLLM(
        model=model_name, 
        temperature=temperature,      # Tutarlı ama yaratıcı yanıtlar için hafif arttırıldı
        top_p=0.92,                   # Top-p örnekleme - biraz arttırıldı
        top_k=40,                     # Top-k eklenedi - daha tutarlı yanıtlar için
        num_predict=2048,             # Yanıt uzunluğu
        num_ctx=8192,                 # Bağlam penceresi arttırıldı
        repeat_penalty=1.18,          # Tekrarları engelleme - biraz arttırıldı
        mirostat=2,                   # Üretkenlik-tutarlılık dengesi için
        mirostat_tau=5.0,             # Üretken yaratıcılık
        mirostat_eta=0.1,             # Kararlılık faktörü
        num_thread=num_threads        # CPU thread sayısı belirtildi - paralel işlem için
    )

def create_emergency_model():
    """
    Acil durum modeli oluşturur - daha basit ve hızlı yanıtlar için.
    
    Returns:
        OllamaLLM: Acil durum için yapılandırılmış basit model
    """
    return OllamaLLM(
        model="llama3.1", 
        temperature=0.3,
        num_predict=1024, 
        num_ctx=4096,
        repeat_penalty=1.1,
        num_thread=4
    )

# Varsayılan model örneği
default_model = create_model()
emergency_model = create_emergency_model()
