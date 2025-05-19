import sys
import os
sys.path.insert(0, os.path.abspath("."))
import traceback
print(f"Python path: {sys.path}")
try:
    from inspareai.utils.streaming import stream_llm_response, create_academic_formatted_stream
    print("Streaming functions imported successfully!")
    from inspareai.api.streamlit_handler import get_transcript_list
    print("Streamlit API imported successfully!")
    files = get_transcript_list()
    print(f"Found {len(files)} transcript files")
except Exception as e:
    print(f"Import error: {e}")
    print(f"Traceback: {traceback.format_exc()}")

