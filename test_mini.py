#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
InspareAI Test Mini - Basit LLM testi
Sadece zincir oluşturma ve çağırma işlemini test eder
"""

from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

def run_simple_test():
    print("Basit LLM testi başlatılıyor...")
    
    try:
        # Model oluştur
        model = OllamaLLM(
            model="llama3.1", 
            temperature=0.5,
            num_predict=512,
        )
        
        print("Model başarıyla oluşturuldu.")
        
        # Basit prompt ve değerler
        prompt = ChatPromptTemplate.from_template("Bu bir test sorusudur: {soru}")
        
        # Değerleri hazırla
        values = {"soru": "Türkiye'nin başkenti neresidir?"}
        
        # Doğrudan yanıt al
        response = model.invoke(prompt.format(**values))
        
        print("Yanıt alındı:")
        print(response)
        
        print("Test başarılı!")
        return True
        
    except Exception as e:
        print(f"Test sırasında hata oluştu: {e}")
        return False

if __name__ == "__main__":
    result = run_simple_test()
    print(f"Test sonucu: {'Başarılı' if result else 'Başarısız'}")
