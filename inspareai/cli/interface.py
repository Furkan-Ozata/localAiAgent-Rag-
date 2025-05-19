#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
InspareAI - CLI Ana Arayüz Modülü.
Bu modül, komut satırı arayüzünün giriş noktasını içerir.
"""

import sys
import argparse
from inspareai.cli.command_handler import handle_interactive_mode, handle_single_query_mode


def parse_args():
    """
    Komut satırı argümanlarını ayrıştırır.
    
    Returns:
        argparse.Namespace: Ayrıştırılmış komut satırı argümanları
    """
    parser = argparse.ArgumentParser(
        description='InspareAI - Türkçe Transkript Analiz Sistemi',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '-q', '--query', 
        type=str,
        help='Tek seferlik sorgu. Bu parametre verildiğinde etkileşimli mod çalışmaz.'
    )
    
    parser.add_argument(
        '--version', 
        action='version', 
        version='InspareAI v3.2'
    )
    
    return parser.parse_args()


def main():
    """
    CLI ana giriş noktası.
    """
    args = parse_args()
    
    # Tek seferlik sorgu modu
    if args.query:
        handle_single_query_mode(args.query)
    # Etkileşimli mod
    else:
        handle_interactive_mode()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram sonlandırıldı.")
        sys.exit(0)
