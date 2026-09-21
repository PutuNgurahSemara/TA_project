"""
embedder.py — Menghasilkan vector embedding teks menggunakan LangChain OllamaEmbeddings.

Model: bge-m3 (via Ollama)
Akselerasi: Otomatis GPU via Ollama (NVIDIA CUDA)
"""

from __future__ import annotations

from typing import Optional
from langchain_ollama import OllamaEmbeddings
from config import OLLAMA_BASE_URL, EMBED_MODEL

_embeddings: Optional[OllamaEmbeddings] = None


def get_embeddings() -> OllamaEmbeddings:
    """
    Mengambil atau membuat singleton OllamaEmbeddings (bge-m3).
    Berjalan langsung di GPU melalui backend Ollama.
    Kompatibel langsung dengan LangChain Chroma VectorStore.
    """
    global _embeddings
    if _embeddings is None:
        print(f"[Embedder] Initializing LangChain OllamaEmbeddings ({EMBED_MODEL}) on Ollama GPU...")
        _embeddings = OllamaEmbeddings(
            base_url=OLLAMA_BASE_URL,
            model=EMBED_MODEL,
        )
        print(f"[Embedder] OllamaEmbeddings ({EMBED_MODEL}) ready.")
    return _embeddings


def embed_text(text: str) -> list[float]:
    """
    Embed satu teks menjadi vector float (dimensi 1024).
    """
    embeddings = get_embeddings()
    return embeddings.embed_query(text)


def embed_batch(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    """
    Embed list teks secara batch menggunakan LangChain Embeddings interface.
    """
    if not texts:
        return []
    embeddings = get_embeddings()
    return embeddings.embed_documents(texts)
