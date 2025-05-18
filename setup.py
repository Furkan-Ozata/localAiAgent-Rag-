from setuptools import setup, find_packages

setup(
    name="inspareAI-localagent",
    version="3.5.0",
    packages=find_packages(),
    install_requires=[
        "langchain_chroma>=0.1.0",
        "langchain_ollama>=0.1.0",
        "langchain_community>=0.0.15",
        "langchain_text_splitters>=0.1.0",
        "langchain_core>=0.2.0",
        "nltk>=3.8.1",
        "psutil>=5.9.5",
        "numpy>=1.24.0",
        "pandas>=2.0.0",
        "scikit-learn>=1.3.0",
        "snowballstemmer>=2.2.0",  # Türkçe stemming için
        "TurkishStemmer>=1.3",     # Alternatif Türkçe stemming için
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=23.3.0",
            "matplotlib>=3.7.2",
        ],
        "embeddings": [
            "sentence-transformers>=2.2.2",
            "peft>=0.5.0",
            "accelerate>=0.23.0",
            "bitsandbytes>=0.41.1",
        ],
    },
    author="Furkan Ozata",
    author_email="furkanozata@example.com",
    description="Türkçe Transkript Analiz Sistemi - Gelişmiş RAG Özellikleri",
    keywords="nlp, turkish, transcript, analysis, rag, semantic-search, text-analysis",
    python_requires=">=3.8",
) 