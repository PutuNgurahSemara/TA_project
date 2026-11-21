"""Fixture bersama: vector store palsu agar test berjalan tanpa Ollama dan tanpa ChromaDB asli."""

import pytest
from langchain_core.documents import Document

from rag import vectorstore


class TokoPalsu:
    """Pengganti rag.vectorstore.similarity_search; mencatat argumen panggilan terakhir."""

    def __init__(self):
        self.data: list[tuple[Document, float]] = []
        self.panggilan: list[dict] = []

    def tambah(self, chunk_id: str, kategori: str, jarak: float, halaman: int = 1, teks: str = "isi"):
        doc = Document(
            id=chunk_id,
            page_content=teks,
            metadata={"source": f"Panduan {kategori}.pdf", "kategori": kategori, "page_num": halaman},
        )
        self.data.append((doc, jarak))

    def __call__(self, query_text, top_k=5, filter=None):
        self.panggilan.append({"query": query_text, "top_k": top_k, "filter": filter})
        hasil = [
            (d, s) for d, s in self.data
            if not filter or d.metadata.get("kategori") == filter.get("kategori")
        ]
        return sorted(hasil, key=lambda r: r[1])[:top_k]


@pytest.fixture
def toko(monkeypatch):
    palsu = TokoPalsu()
    monkeypatch.setattr(vectorstore, "similarity_search", palsu)
    return palsu
