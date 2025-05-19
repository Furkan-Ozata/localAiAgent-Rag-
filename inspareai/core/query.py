#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
InspareAI - Sorgu İşleme ve LLM Yanıt Oluşturma.
Bu modül, kullanıcı sorgusunu işleme ve LLM yanıtı oluşturma fonksiyonlarını içerir.
"""

import time
import traceback
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from inspareai.core.model import default_model, emergency_model
from inspareai.core.retrieval import (retrieve_relevant_documents, 
                                     filter_and_prepare_documents, 
                                     format_context, format_sources, 
                                     save_analysis, VECTOR_DB_AVAILABLE)
from inspareai.utils.text import extract_keywords
from inspareai.utils.streaming import create_academic_formatted_stream, stream_llm_response
from inspareai.utils.cache import save_cache, clear_memory_cache, query_cache, memory_cache
from inspareai.config.constants import (MIN_RESPONSE_LENGTH, PRIMARY_TIMEOUT,
                                      SECONDARY_TIMEOUT, EMERGENCY_TIMEOUT,
                                      DISK_CACHE_SAVE_INTERVAL)
from inspareai.config.prompts import (SYSTEM_INSTRUCTION, QUERY_TEMPLATE,
                                    CHRONOLOGICAL_INSTRUCTION,
                                    SPEAKER_ANALYSIS_INSTRUCTION,
                                    COMPARISON_ANALYSIS_INSTRUCTION)


def query_transcripts(question, stream_callback=None):
    """
    Ana sorgulama fonksiyonu - Performans optimizasyonlu
    
    Args:
        question: Kullanıcı sorusu
        stream_callback: Yanıtı parça parça işlemek için callback fonksiyonu
    """
    print(f"Sorgu işleniyor: \"{question}\"")
    start_time = time.time()
    
    # Giriş kontrolü
    if not question or len(question.strip()) < 2:
        return "Lütfen geçerli bir soru girin."
        
    # Vektör veritabanı kullanılabilir mi?
    if not VECTOR_DB_AVAILABLE:
        return "Vektör veritabanı kullanılamıyor. Lütfen vector.py dosyasının varlığını kontrol edin ve uygun bir embedding modeli seçin."
    
    try:
        # Performans izleme
        stage_times = {}
        
        # Önbellekte bu soru var mı?
        cache_key = question.strip().lower()
        if cache_key in query_cache:
            print("Önbellekten yanıt alınıyor...")
            return query_cache[cache_key]
        
        # Bellek önbelleğinde var mı?
        if cache_key in memory_cache:
            print("Bellek önbelleğinden yanıt alınıyor...")
            memory_cache[cache_key]["timestamp"] = time.time()
            return memory_cache[cache_key]["response"]
        
        # Anahtar kelimeleri çıkar
        kw_start = time.time()
        print("Anahtar kelimeler çıkarılıyor...")
        keywords = extract_keywords(question)
        if keywords:
            print(f"Çıkarılan anahtar kelimeler: {', '.join(keywords)}")
        stage_times["anahtar_kelimeler"] = time.time() - kw_start
            
        # İlgili dokümanları getir
        retrieval_start = time.time()
        print("İlgili dokümanlar getiriliyor...")
        
        try:
            docs = retrieve_relevant_documents(question, keywords)
            stage_times["dokuman_getirme"] = time.time() - retrieval_start
        except Exception as e:
            print(f"Doküman getirilirken hata: {e}")
            error_msg = f"Veritabanından bilgi alınırken bir sorun oluştu: {str(e)}"
            return error_msg
        
        # Doküman bulunamadıysa bildir
        if not docs:
            no_docs_message = "Bu soruyla ilgili bilgi bulunamadı. Lütfen farklı bir soru sorun veya daha genel bir ifade kullanın."
            return no_docs_message
        
        print(f"Toplam {len(docs)} ilgili belge parçası bulundu")
        
        # Belge filtreleme ve hazırlama
        filtering_start = time.time()
        print("Belgeler filtreleniyor ve hazırlanıyor...")
        filtered_docs = filter_and_prepare_documents(docs, question)
        stage_times["filtreleme"] = time.time() - filtering_start
            
        # Prompt hazırlama
        prompt_start = time.time()
        print("Prompt hazırlanıyor...")
        
        # Doğrudan dokümanlar üzerinden sorgulama yap
        query_prompt = ChatPromptTemplate.from_template(QUERY_TEMPLATE)
        
        # Bağlamı oluştur
        context = format_context(filtered_docs)
        stage_times["prompt_hazirlama"] = time.time() - prompt_start
        
        # Her sorgu için sistem talimatının bir kopyasını oluştur
        query_system_instruction = SYSTEM_INSTRUCTION
        
        # Özel sorgu tipi algılama ve prompt özelleştirme
        
        # Kronolojik analiz
        is_chronological = any(word in question.lower() for word in ["kronoloji", "zaman", "sıra", "gelişme", "tarihsel", "süreç"])
        if is_chronological:
            query_system_instruction += CHRONOLOGICAL_INSTRUCTION
        
        # Konuşmacı analizi
        is_speaker_specific = "speaker" in question.lower() or "konuşmacı" in question.lower()
        if is_speaker_specific:
            query_system_instruction += SPEAKER_ANALYSIS_INSTRUCTION
            
        # Karşılaştırma analizi
        is_comparison = any(word in question.lower() for word in ["karşılaştır", "fark", "benzerlik", "benzer", "farklı"])
        if is_comparison:
            query_system_instruction += COMPARISON_ANALYSIS_INSTRUCTION
        
        # Giriş değerlerini hazırla
        input_values = {
            "system_instruction": query_system_instruction,
            "question": question,
            "context": context
        }
        
        # LLM yanıtını al
        llm_start = time.time()
        print("LLM yanıtı alınıyor...")
        
        # Zincir fonksiyonu
        def execute_chain():
            try:
                # Streaming desteği ile akademik formatı kullan
                print("Akademik formatlı streaming yanıt oluşturuluyor...")
                if stream_callback:
                    # Stream modunda çalış
                    formatted_prompt = query_prompt.format(**input_values)
                    create_academic_formatted_stream(
                        model=default_model,
                        prompt=formatted_prompt,
                        system_instruction=query_system_instruction,
                        question=question,
                        context=context,
                        callback=stream_callback
                    )
                    return None
                else:
                    # Normal modda prompt'u önceden formatla
                    print("Birinci zincir yöntemi deneniyor...")
                    formatted_prompt = query_prompt.format(**input_values)
                    response = default_model.invoke(formatted_prompt)
                    return StrOutputParser().parse(response)
                
            except Exception as e1:
                print(f"Birinci zincir yöntemi başarısız: {e1}")
                
                try:
                    # İkinci yöntem: Daha açık yaklaşım
                    print("İkinci zincir yöntemi deneniyor...")
                    prompt_text = query_prompt.format(
                        system_instruction=SYSTEM_INSTRUCTION,
                        question=question,
                        context=context
                    )
                    response = default_model.invoke(prompt_text)
                    return StrOutputParser().parse(response)
                    
                except Exception as e2:
                    print(f"İkinci zincir yöntemi başarısız: {e2}")
                    
                    # Son çare yöntemi
                    print("Son çare yöntemi deneniyor...")
                    direct_prompt = f"Sistem: {SYSTEM_INSTRUCTION}\n\nSoru: {question}\n\nBağlam: {context[:5000]}\n\nYanıt:"
                    response = default_model.invoke(direct_prompt)
                    return str(response)
        
        try:
            # Streaming işlev kullanılıyorsa farklı işle
            if stream_callback:
                try:
                    # Stream modunda ThreadPool kullanma, çünkü stream_callback zaten paralel işleyecek
                    llm_result = execute_chain()
                    # Stream modunda execute_chain() None döndürecek
                    stage_times["llm_yaniti"] = time.time() - llm_start
                except Exception as stream_e:
                    print(f"Stream modunda hata: {stream_e}")
                    # Acil durum yanıtı oluştur
                    emergency_prompt = f"Soru: {question}\n\nYanıt: "
                    emergency_result = stream_llm_response(emergency_model, emergency_prompt, stream_callback)
                    stage_times["llm_yaniti"] = time.time() - llm_start
                    return emergency_result
            else:
                # Normal mod - Paralel işleme ile zaman aşımı kontrolü
                with ThreadPoolExecutor() as executor:
                    future = executor.submit(execute_chain)
                    try:
                        llm_result = future.result(timeout=PRIMARY_TIMEOUT)
                        
                        # Yanıt kalitesini kontrol et
                        if not llm_result or len(llm_result.strip()) < MIN_RESPONSE_LENGTH:
                            raise ValueError("Yetersiz yanıt uzunluğu")
                        
                    except TimeoutError:
                        print(f"LLM yanıt zaman aşımı ({PRIMARY_TIMEOUT}s). İkincil yöntem deneniyor...")
                        # İkinci deneme - daha basit prompt ile
                        try:
                            simple_prompt = f"Sistem talimatı: Sen bir transkript analiz uzmanısın. \nSoru: {question}\n\nTranskriptler:\n{context[:5000]}\n\nÖzet bir analiz yap:"
                            future2 = executor.submit(lambda: default_model.invoke(simple_prompt))
                            llm_result = future2.result(timeout=SECONDARY_TIMEOUT)
                            llm_result = str(llm_result)
                            
                        except (TimeoutError, Exception) as e3:
                            print(f"İkincil deneme başarısız: {e3}")
                            # Son çare - acil durum prompt
                            emergency_prompt = f"Soru: {question}\n\nYanıt ver:"
                            future3 = executor.submit(lambda: emergency_model.invoke(emergency_prompt))
                            try:
                                llm_result = future3.result(timeout=EMERGENCY_TIMEOUT)
                                llm_result = str(llm_result)
                            except Exception as e4:
                                print(f"Acil durum yanıtı alınamadı: {e4}")
                                return "Şu anda yanıt oluşturulamıyor. Lütfen daha sonra tekrar deneyin."
                    
                    except Exception as e:
                        print(f"LLM yanıt hatası: {e}")
                        # Acil durum yanıtı
                        try:
                            emergency_prompt = f"Soru: {question}\n\nYanıt ver:"
                            llm_result = emergency_model.invoke(emergency_prompt)
                            llm_result = str(llm_result)
                        except Exception as ee:
                            print(f"Acil durum yanıtı alınamadı: {ee}")
                            return "Şu anda yanıt oluşturulamıyor. Lütfen daha sonra tekrar deneyin."
                
                stage_times["llm_yaniti"] = time.time() - llm_start
                
                # Yanıt sonlandırma ve formatlamayı iyileştir
                formatting_start = time.time()
                
                # Kaynakları formatla
                source_info = format_sources(filtered_docs[:15])
                
                # Normal mod - Kullanılan kaynakları ekle
                result = f"{llm_result}\n\n{source_info}"
                
                # Bellek önbelleğine kaydet
                memory_cache[cache_key] = {
                    "response": result, 
                    "timestamp": time.time()
                }
                
                # Disk önbelleğine kaydet
                query_cache[cache_key] = result
                if len(query_cache) % DISK_CACHE_SAVE_INTERVAL == 0:
                    save_cache()
                
                # Periyodik olarak bellek önbelleğini temizle
                if len(memory_cache) % 10 == 0:
                    clear_memory_cache()
                
                stage_times["sonlandirma"] = time.time() - formatting_start
                
                # İstatistikler
                end_time = time.time()
                process_time = end_time - start_time
                
                # Sorgu performans analizini göster
                print(f"Sorgu işlendi. Toplam süre: {process_time:.2f} saniye")
                print("İŞLEM SÜRELERİ:")
                for stage, duration in stage_times.items():
                    print(f" - {stage}: {duration:.2f} saniye")
                
                return result
            
        except Exception as e:
            print(f"LLM yanıtı alınırken hata: {e}")
            print("=== HATA DETAYLARI ===")
            traceback.print_exc()
            print("=====================")
            
            # Doğrudan dokümanlardan daha gelişmiş bir yanıt oluştur
            simple_result = f"Yanıt oluşturulurken bir sorun oluştu ({str(e)}), ancak şu ilgili bilgileri buldum:\n\n"
            
            # Hata durumunda daha bilgilendirici ve yapılandırılmış yanıt
            simple_result += "### İlgili Bilgi Parçaları\n\n"
            
            for i, doc in enumerate(docs[:7], 1):
                source = doc.metadata.get('source', 'Bilinmiyor').split('/')[-1]
                time_info = doc.metadata.get('time', 'Zaman bilgisi yok')
                speaker = doc.metadata.get('speaker', 'Bilinmiyor')
                
                content = doc.page_content
                if 'Content: ' in content:
                    content = content.split('Content: ')[-1]
                
                # Metni kısalt
                content = content[:300] + ("..." if len(content) > 300 else "")
                
                simple_result += f"**{i}. Bilgi Parçası:**\n"
                simple_result += f"- Kaynak: {source}\n"
                simple_result += f"- Zaman: {time_info}\n"
                simple_result += f"- Konuşmacı: {speaker}\n"
                simple_result += f"- İçerik: {content}\n\n"
            
            return simple_result + "\nSistem şu anda yanıt üretmekte zorlanıyor. Lütfen sorunuzu daha açık bir şekilde yeniden sormayı deneyin."
        
    except Exception as e:
        print(f"Genel hata: {e}")
        traceback.print_exc()
        return f"İşlem sırasında bir hata oluştu: {str(e)}"


def quick_query(question, stream_callback=None):
    """
    Hızlı yanıt modu - Optimize edilmiş ve basitleştirilmiş sorgu fonksiyonu
    
    Args:
        question: Kullanıcı sorusu
        stream_callback: Yanıtı parça parça işlemek için callback fonksiyonu
        
    Returns:
        str: Oluşturulan yanıt
    """
    print(f"Hızlı yanıt modu: \"{question}\"")
    
    # Hızlı yanıt için daha kısa ve basit bir sistem talimatı
    quick_system = "Transkript dosyalarındaki bilgilere dayanarak kısa ve öz yanıtlar ver. Sadece ilgili bilgileri kullan."
    
    # "!" işareti varsa kaldır
    if question.startswith("!"):
        question = question[1:].strip()
        
    try:
        # Normal sorgudan daha basit ve hızlı bir işlem
        keywords = extract_keywords(question)
        docs = retrieve_relevant_documents(question, keywords)
        
        # Daha az sayıda belge kullan
        filtered_docs = docs[:10]
        context = format_context(filtered_docs)
        
        # Daha basit prompt
        quick_prompt = f"Sistem: {quick_system}\nSoru: {question}\nBağlam:\n{context}\n\nYanıt:"
        
        # Stream modunda veya normal modda çalıştır
        if stream_callback:
            stream_llm_response(default_model, quick_prompt, stream_callback)
            return None
        else:
            response = default_model.invoke(quick_prompt)
            result = str(response)
            
            # Kaynakları ekle
            sources = format_sources(filtered_docs[:5])
            return f"{result}\n\n{sources}"
            
    except Exception as e:
        print(f"Hızlı yanıt hatası: {e}")
        return f"Hızlı yanıt oluşturulamadı: {str(e)}"


def parallel_query(questions):
    """
    Birden fazla soruyu paralel olarak işleyebilir
    
    Args:
        questions: Sorulacak soruların listesi
        
    Returns:
        list: Yanıtların listesi
    """
    results = []
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(quick_query, q) for q in questions]
        for future in futures:
            try:
                results.append(future.result(timeout=60))
            except Exception as e:
                results.append(f"Yanıt oluşturulamadı: {str(e)}")
                
    return results
