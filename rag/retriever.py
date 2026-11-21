"""
retriever.py — Mengambil chunk paling relevan berdasarkan query user
menggunakan LangChain Chroma Retriever.

Mendukung:
- retrieve(query_text, top_k, kategori) -> fungsi retrieval BERSAMA untuk mode linier dan
  tool retrieve_dokumen (mode agentic), agar hasil kedua mode bisa dibandingkan secara adil.
- get_langchain_retriever(top_k) -> instance BaseRetriever LangChain untuk chain lanjutan
"""

from typing import Any, Optional
from langchain_core.retrievers import BaseRetriever
from rag import vectorstore
from config import TOP_K, RELEVANCE_MAX_DISTANCE


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
    kategori: Optional[str] = None,
    max_distance: float = RELEVANCE_MAX_DISTANCE,
) -> list[dict[str, Any]]:
    """
    Cari top-k chunk paling relevan di ChromaDB (koleksi memakai metrik cosine).

    ChromaDB mengembalikan JARAK cosine (= 1 - kemiripan cosine), bukan skor kemiripan:
    makin kecil jaraknya, makin relevan potongannya. Potongan dengan jarak di atas
    `max_distance` (RELEVANCE_MAX_DISTANCE di config.py) dibuang.

    Args:
        query_text:   Pertanyaan user dalam bahasa natural
        top_k:        Jumlah maksimum chunk yang dikembalikan
        kategori:     "TA" | "KP" | "Magang" untuk menyaring metadata `kategori`; None = semua
        max_distance: Ambang jarak maksimum

    Returns:
        List of {chunk_id, nama_dokumen, kategori, halaman, kutipan, jarak, peringkat},
        urut dari paling relevan (peringkat 1). List kosong jika tidak ada yang lolos ambang.
    """
    filter_meta = {"kategori": kategori} if kategori else None
    results = vectorstore.similarity_search(query_text, top_k=top_k, filter=filter_meta)

    chunks: list[dict[str, Any]] = []
    for doc, score in sorted(results, key=lambda r: r[1]):
        if score > max_distance:
            continue
        meta = doc.metadata or {}
        chunks.append(
            {
                "chunk_id":     doc.id or f"{meta.get('doc_id')}__chunk_{meta.get('chunk_index')}",
                "nama_dokumen": meta.get("source", "Unknown"),
                "kategori":     meta.get("kategori"),
                "halaman":      meta.get("page_num"),
                "kutipan":      doc.page_content,
                "jarak":        round(float(score), 4),
                "peringkat":    len(chunks) + 1,
            }
        )

    return chunks
