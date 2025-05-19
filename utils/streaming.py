"""
Streaming işlemleri için yardımcı fonksiyonlar
Bu modül, InspareAI'nin streaming yanıt oluşturma yeteneklerini yönetir.
"""

from langchain_ollama import OllamaLLM
from langchain_core.output_parsers import StrOutputParser

class StreamHandler:
    """
    Streaming yanıtları yönetmek için kullanılan sınıf.
    Bu sınıf, farklı modellerin streaming yanıtlarını standart bir şekilde işler.
    """
    
    def __init__(self, callback_fn=None):
        """
        Args:
            callback_fn: Her yeni metin parçası için çağrılacak fonksiyon
        """
        self.callback_fn = callback_fn
        self.full_response = ""
    
    def handle_chunk(self, chunk):
        """Bir metin parçasını işler ve callback fonksiyonuna iletir.
        
        Args:
            chunk: Modelden gelen metin parçası
        """
        chunk_text = str(chunk)
        self.full_response += chunk_text
        
        if self.callback_fn:
            self.callback_fn(chunk_text)
    
    def get_response(self):
        """Toplam yanıtı döndürür."""
        return self.full_response


def stream_llm_response(model, prompt, callback=None):
    """
    Bir LLM modelin yanıtını stream eder.
    
    Args:
        model: Yanıt alınacak LLM modeli
        prompt: LLM'e gönderilecek prompt
        callback: Her metin parçası için çağrılacak fonksiyon
        
    Returns:
        None: Eğer callback belirtilmişse
        str: Callback belirtilmemişse tam yanıt metni
    """
    handler = StreamHandler(callback)
    
    # Modelin streaming özelliği var mı kontrol et
    if hasattr(model, 'stream') and callable(model.stream):
        try:
            # Stream modunda yanıt al
            for chunk in model.stream(prompt):
                handler.handle_chunk(chunk)
            return None if callback else handler.get_response()
            
        except Exception as e:
            print(f"Streaming sırasında hata oluştu: {e}")
            
            # Streaming başarısız olduysa normal modda dene
            try:
                response = model.invoke(prompt)
                result = StrOutputParser().parse(response)
                if callback:
                    callback(result)
                    return None
                return result
            except Exception as e2:
                print(f"Normal mod da başarısız oldu: {e2}")
                raise e2
    else:
        # Model streaming desteklemiyorsa normal yanıt al
        print("Model streaming desteklemiyor, normal yanıt kullanılacak")
        response = model.invoke(prompt)
        result = StrOutputParser().parse(response)
        
        if callback:
            callback(result)
            return None
        
        return result


def create_academic_formatted_stream(model, prompt, system_instruction, question, context, callback=None):
    """
    Akademik formatlı streaming yanıtlar oluşturur.
    
    Args:
        model: Kullanılacak LLM modeli
        prompt: Prompt şablonu
        system_instruction: Sistem talimatları
        question: Kullanıcı sorusu
        context: Yanıt için kullanılacak bağlam
        callback: Stream için callback fonksiyonu
        
    Returns:
        None: Eğer streaming kullanılıyorsa
        str: Streaming kullanılmıyorsa tam yanıt
    """
    # Prompt değerlerini hazırla
    input_values = {
        "system_instruction": system_instruction,
        "question": question,
        "context": context
    }
    
    formatted_prompt = prompt.format(**input_values)
    return stream_llm_response(model, formatted_prompt, callback)
