"""
retriever.py — Mengambil chunk paling relevan berdasarkan query user
menggunakan LangChain Chroma Retriever.

Mendukung:
- retrieve(query_text, top_k) -> format list of dict (text, source, page_num, distance)
- get_langchain_retriever(top_k) -> instance BaseRetriever LangChain untuk chain lanjutan
"""

from typing import Any
from langchain_core.retrievers import BaseRetriever
from rag import vectorstore
from config import TOP_K


def get_langchain_retriever(top_k: int = TOP_K) -> BaseRetriever:
    """
    Mengembalikan instance BaseRetriever bawaan LangChain.
    Sangat berguna jika programmer berikutnya ingin membuat LCEL chain / LangGraph.
    """
    vs = vectorstore.get_vectorstore()
    return vs.as_retriever(
        search_type="similarity",
        search_kwargs={"k": top_k},
    )


def retrieve(
    query_text: str,
    top_k: int = TOP_K,
) -> list[dict[str, Any]]:
    """
    Cari top-k chunk paling relevan di vector database menggunakan LangChain.

    Args:
        query_text: Pertanyaan user dalam bahasa natural
        top_k:      Jumlah chunk yang dikembalikan

    Returns:
        List of {text, source, page_num, distance}
        Diurutkan dari paling relevan (distance terkecil).
    """
    # similarity_search_with_score returns list of (Document, score)
    results = vectorstore.similarity_search(query_text, top_k=top_k)

    chunks: list[dict[str, Any]] = []
    for doc, score in results:
        meta = doc.metadata or {}
        chunks.append(
            {
                "text":     doc.page_content,
                "source":   meta.get("source", "Unknown"),
                "page_num": meta.get("page_num", 1),
                "distance": round(float(score), 4),
            }
        )

    return chunks
