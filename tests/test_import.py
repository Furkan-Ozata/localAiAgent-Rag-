import sys
import os
sys.path.insert(0, os.path.abspath("."))
print(f"Python path: {sys.path}")
try:
    from inspareai.config.constants import MAX_DOCUMENTS
    print(f"Imported successfully! MAX_DOCUMENTS = {MAX_DOCUMENTS}")
except Exception as e:
    print(f"Import error: {e}")

