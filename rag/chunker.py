"""
chunker.py — Memecah teks dokumen menjadi potongan kecil (chunks) menggunakan
LangChain RecursiveCharacterTextSplitter dengan preservasi metadata per halaman.

Mendukung:
- Pemotongan berbasis recursive character splitter (paragraf, baris, kalimat, kata)
- Preservasi metadata (source, page_num, chunk_index)
- Konversi ke format dict lama ataupun langchain Document
"""

from typing import Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


def get_text_splitter(chunk_size: int = 600, overlap: int = 100) -> RecursiveCharacterTextSplitter:
    """
    Inisialisasi RecursiveCharacterTextSplitter standar LangChain.
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", " ", ""],
        strip_whitespace=True,
    )


def chunk_text(
    text: str,
    chunk_size: int = 600,
    overlap: int = 100,
) -> list[str]:
    """
    Split satu string teks menjadi list chunk dengan overlap menggunakan LangChain.

    Args:
        text:       Teks input
        chunk_size: Ukuran chunk dalam karakter
        overlap:    Jumlah karakter yang di-overlap antar chunk berurutan

    Returns:
        List of chunk strings
    """
    if not text or not text.strip():
        return []

    splitter = get_text_splitter(chunk_size=chunk_size, overlap=overlap)
    return splitter.split_text(text)


def chunk_pages_to_documents(
    pages: list[dict[str, Any]],
    chunk_size: int = 600,
    overlap: int = 100,
) -> list[Document]:
    """
    Chunk seluruh halaman menjadi list of LangChain Document objects.
    """
    documents: list[Document] = []
    splitter = get_text_splitter(chunk_size=chunk_size, overlap=overlap)
    global_index = 0

    for page in pages:
        text = page.get("text", "")
        if not text or not text.strip():
            continue

        page_chunks = splitter.split_text(text)
        for chunk in page_chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            doc = Document(
                page_content=chunk,
                metadata={
                    "page_num": int(page.get("page_num", 1)),
                    "source": str(page.get("source", "unknown")),
                    "chunk_index": global_index,
                },
            )
            documents.append(doc)
            global_index += 1

    return documents


def chunk_pages(
    pages: list[dict[str, Any]],
    chunk_size: int = 600,
    overlap: int = 100,
) -> list[dict[str, Any]]:
    """
    Chunk semua halaman dari dokumen, pertahankan metadata per chunk (format dict kompatibel).

    Args:
        pages:      Output dari parser.parse_document()
        chunk_size: Ukuran chunk dalam karakter
        overlap:    Overlap antar chunk

    Returns:
        List of {text, page_num, source, chunk_index}
    """
    docs = chunk_pages_to_documents(pages, chunk_size=chunk_size, overlap=overlap)
    return [
        {
            "text": d.page_content,
            "page_num": d.metadata.get("page_num", 1),
            "source": d.metadata.get("source", "unknown"),
            "chunk_index": d.metadata.get("chunk_index", idx),
        }
        for idx, d in enumerate(docs)
    ]
