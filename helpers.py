
import gradio as gr
import time
import os
from main import query_transcripts, quick_query, list_transcript_files, view_transcript

def gradio_interface():
    """Gradio arayüzünü başlatır ve Türkçe yapay zeka modelini kullanır."""
    
    def process_query(text, use_quick_mode=False, show_thinking=False):
        """Kullanıcı sorgusunu işler ve AI yanıtını döndürür"""
        if not text.strip():
            return "Lütfen bir soru girin."
        
        # Düşünme sürecini gösterme seçeneği
        if show_thinking:
            yield "🔍 Anahtar kelimeler analiz ediliyor...\n\n"
            time.sleep(0.5)
            yield "🔍 Anahtar kelimeler analiz ediliyor...\n📑 İlgili dokümanlar aranıyor...\n\n"
            time.sleep(0.7)
            yield "🔍 Anahtar kelimeler analiz ediliyor...\n📑 İlgili dokümanlar aranıyor...\n🧠 Yanıt oluşturuluyor...\n\n"
            time.sleep(0.5)
        
        # Asıl yanıtı döndür
        if use_quick_mode:
            result = quick_query(text)
        else:
            result = query_transcripts(text)
            
        if show_thinking:
            yield "🔍 Anahtar kelimeler analiz ediliyor...\n📑 İlgili dokümanlar aranıyor...\n🧠 Yanıt oluşturuluyor...\n✅ Tamamlandı!\n\n" + result
        else:
            yield result
    
    def list_files():
        """Mevcut transcript dosyalarını listeler"""
        transcript_dir = "transcripts"
        if not os.path.exists(transcript_dir):
            return "Transcripts klasörü bulunamadı."
        
        files = [f for f in os.listdir(transcript_dir) if f.endswith(".txt") and not f.startswith('.')]
        if not files:
            return "Hiç transcript dosyası bulunamadı."
        
        result = "### Mevcut Transkript Dosyaları\n\n"
        for i, filename in enumerate(files, 1):
            file_path = os.path.join(transcript_dir, filename)
            file_size = os.path.getsize(file_path) / 1024  # KB cinsinden
            result += f"{i}. {filename} ({file_size:.1f} KB)\n"
            
        return result
    
    def preview_file(filename):
        """Seçilen dosyanın önizlemesini gösterir"""
        if not filename:
            return "Lütfen bir dosya seçin."
        return view_transcript(filename, show_all=False)
    
    # Arayüz tanımı - Modern ve kullanıcı dostu
    with gr.Blocks(title="InspareAI - Türkçe Yapay Zeka Analiz Sistemi", theme=gr.themes.Soft()) as demo:
        gr.Markdown(
            """
            # 📚 InspareAI - Türkçe Konuşma Analiz Sistemi
            ### Transkriptlerdeki bilgilere dayanarak sorularınızı cevaplayacak gelişmiş yapay zeka sistemi
            """
        )
        
        # Sekmeler ile düzenlenmiş arayüz
        with gr.Tabs():
            # Ana soru-cevap sekmesi
            with gr.Tab("💬 Soru & Cevap"):
                with gr.Row():
                    with gr.Column(scale=4):
                        question_input = gr.Textbox(
                            label="Sorunuz", 
                            placeholder="Transkriptlerle ilgili sorularınızı buraya yazın...", 
                            lines=3
                        )
                    
                    with gr.Column(scale=1):
                        with gr.Row():
                            quick_mode = gr.Checkbox(label="Hızlı yanıt modu", value=False)
                            show_thinking = gr.Checkbox(label="Düşünme sürecini göster", value=False)
                        
                        submit_btn = gr.Button("Gönder 🚀", variant="primary")
                        clear_btn = gr.ClearButton([question_input], value="Temizle 🧹")
                
                answer_output = gr.Markdown(label="Yanıt")
                
                gr.Markdown("### Önerilen Sorular")
                with gr.Row():
                    ex1 = gr.Button("Türkiye'nin dış politika vizyonu nedir?")
                    ex2 = gr.Button("Ekonomik kriz nasıl aşılır?")
                
                with gr.Row():
                    ex3 = gr.Button("NATO ile ilişkiler nasıl ilerliyor?")
                    ex4 = gr.Button("Eğitim sistemindeki sorunlar nelerdir?")
            
            # Dosya yönetimi sekmesi
            with gr.Tab("📂 Transkript Dosyaları"):
                list_btn = gr.Button("Dosyaları Listele")
                file_list = gr.Markdown("Dosya listesini görmek için 'Dosyaları Listele' düğmesine tıklayın.")
                
                with gr.Row():
                    filename_input = gr.Textbox(label="Dosya Adı", placeholder="Önizlemek istediğiniz dosya adını girin")
                    preview_btn = gr.Button("Önizleme Göster")
                
                file_preview = gr.Markdown("Dosya önizlemesi burada görünecek...")
            
            # Yardım ve bilgi sekmesi
            with gr.Tab("ℹ️ Yardım"):
                gr.Markdown(
                    """
                    ## InspareAI Kullanım Kılavuzu
                    
                    ### Temel Kullanım
                    - Sorularınızı **Soru & Cevap** sekmesine yazıp "Gönder" düğmesine basın
                    - **Hızlı yanıt modu** ile daha az doküman kullanarak hızlı yanıtlar alabilirsiniz
                    - **Düşünme sürecini göster** seçeneği ile yapay zekanın çalışma adımlarını görebilirsiniz
                    
                    ### İpuçları
                    - Spesifik sorular daha doğru yanıtlar almanızı sağlar
                    - Tarih, zaman aralığı veya konuşmacı belirtmek sonuçların kalitesini artırır
                    - Kronolojik analiz için soruda "kronoloji" veya "zaman sırası" ifadeleri kullanın
                    
                    ### Transkript Dosyaları
                    - **Transkript Dosyaları** sekmesinden mevcut dosyaları listeleyebilir ve önizleyebilirsiniz
                    - Yeni transkript eklemek için `transcripts` klasörüne `.txt` uzantılı dosyalar ekleyin
                    
                    ### Sorun Giderme
                    - Yanıt alınamadığında sorunuzu daha açık ifade etmeyi deneyin
                    - Sistem zaman zaman yavaş yanıt verebilir, sabırlı olun
                    """
                )
        
        # Düğme işlevleri
        submit_btn.click(
            fn=process_query, 
            inputs=[question_input, quick_mode, show_thinking], 
            outputs=answer_output
        )
        
        question_input.submit(
            fn=process_query, 
            inputs=[question_input, quick_mode, show_thinking], 
            outputs=answer_output
        )
        
        # Örnek sorular için işlevler
        ex1.click(lambda: "Türkiye'nin dış politika vizyonu nedir?", outputs=question_input)
        ex2.click(lambda: "Ekonomik kriz nasıl aşılır?", outputs=question_input)
        ex3.click(lambda: "NATO ile ilişkiler nasıl ilerliyor?", outputs=question_input)
        ex4.click(lambda: "Eğitim sistemindeki sorunlar nelerdir?", outputs=question_input)
        
        # Dosya yönetimi işlevleri
        list_btn.click(fn=list_files, outputs=file_list)
        preview_btn.click(fn=preview_file, inputs=filename_input, outputs=file_preview)
    
    # Arayüzü başlat
    print("InspareAI Gradio arayüzü başlatılıyor...")
    demo.launch(share=False, inbrowser=True)

if __name__ == "__main__":
    print("Gradio arayüzü başlatılıyor...")
    gradio_interface()