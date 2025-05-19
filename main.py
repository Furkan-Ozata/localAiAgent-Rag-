#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
InspareAI - Ana Modül
Bu modül, InspareAI uygulamasının ana giriş noktasıdır ve eski kodu yeni modüler yapıya yönlendirir.
"""

import sys
import os

# Modüler yapıyı kullanılabilir hale getirmek için dizin ekle
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# CLI arayüzünü çağır
from inspareai.cli.interface import main

# Geriye uyumluluk için ana fonksiyonları doğrudan dışa aktar
from inspareai.core.query import query_transcripts, quick_query
from inspareai.cli.command_handler import view_transcript, list_transcript_files

if __name__ == "__main__":
    main()
