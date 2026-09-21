"""
pipeline.py — Orchestrator untuk proses ingest dokumen dan RAG query.

Fungsi utama:
  ingest_document() → parse → chunk → embed → ChromaDB + SQLite
  query_rag()       → embed query → retrieve → streaming generate → sumber

Semua langkah dilaporkan melalui optional progress_callback agar caller / UI bisa
menampilkan status real-time (progress bar / status text).
"""

from typing import Any, Callable, Generator, Optional
from rag.parser import parse_document
from rag.chunker import chunk_pages
from rag.embedder import embed_batch
from rag import vectorstore
from rag.retriever import retrieve
from rag.generator import generate_answer_stream
from db.database import add_document_record, delete_document_record
from config import CHUNK_SIZE, CHUNK_OVERLAP, TOP_K, EMBED_MODEL


# ── Ingest ────────────────────────────────────────────────────────────────────

def ingest_document(
    file_path: str,
    doc_id: str,
    doc_name: str,
    progress_callback: Optional[Callable[[str, float], None]] = None,
) -> int:
    """
    Pipeline lengkap ingest dokumen ke dalam RAG system.

    Tahap:
      1. Parse dokumen (PDF/DOCX/TXT) → halaman-halaman teks
      2. Chunking teks → potongan-potongan kecil dengan overlap
      3. Embedding setiap chunk via Ollama (bge-m3)
      4. Simpan embedding + metadata ke ChromaDB
      5. Simpan record dokumen ke SQLite

    Args:
        file_path:          Path file yang sudah disimpan ke disk
        doc_id:             UUID unik untuk dokumen ini
        doc_name:           Nama tampilan dokumen (nama file asli)
        progress_callback:  fn(status_text: str, progress_pct: float)

    Returns:
        Jumlah chunk yang berhasil diindeks

    Raises:
        ValueError: Jika dokumen tidak mengandung teks
        RuntimeError: Jika ada error saat embedding
    """

    def _update(msg: str, pct: float = 0.0) -> None:
        if progress_callback:
            progress_callback(msg, pct)

    # Step 1: Parse
    _update("📄 Parsing dokumen...", 0.05)
    pages = parse_document(file_path)
    if not pages:
        raise ValueError("Dokumen tidak mengandung teks yang bisa diekstrak.")

    # Step 2: Chunk
    _update(f"✂️ Memecah teks ({len(pages)} halaman) menjadi chunks...", 0.20)
    chunks = chunk_pages(pages, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
    if not chunks:
        raise ValueError("Tidak ada chunk yang dihasilkan dari dokumen.")

    # Step 3: Embed
    _update(f"🔢 Membuat embedding {len(chunks)} chunks via {EMBED_MODEL} (harap tunggu)...", 0.35)
    texts = [c["text"] for c in chunks]
    embeddings = embed_batch(texts)

    # Step 4: Simpan ke ChromaDB
    _update("💾 Menyimpan ke vector database (ChromaDB)...", 0.85)
    vectorstore.add_chunks(doc_id, chunks, embeddings)

    # Step 5: Simpan metadata ke SQLite
    _update("📝 Mencatat metadata dokumen...", 0.95)
    add_document_record(doc_id, doc_name, file_path, len(chunks))

    _update(f"✅ Selesai! {len(chunks)} chunks dari '{doc_name}' berhasil diindeks.", 1.0)
    return len(chunks)


# ── Delete ────────────────────────────────────────────────────────────────────

def delete_document(doc_id: str) -> None:
    """
    Hapus dokumen dari ChromaDB dan SQLite.

    Args:
        doc_id: UUID dokumen yang akan dihapus
    """
    vectorstore.delete_document(doc_id)
    vectorstore.reset_collection_cache()
    delete_document_record(doc_id)


# ── Query ─────────────────────────────────────────────────────────────────────

def query_rag(
    user_question: str,
    top_k: int = TOP_K,
) -> dict[str, Any]:
    """
    Pipeline query RAG lengkap.

    Tahap:
      1. Embed pertanyaan user
      2. Retrieve top-k chunk relevan dari ChromaDB
      3. Susun prompt + panggil LLM secara streaming

    Args:
        user_question: Pertanyaan user dalam bahasa natural
        top_k:         Jumlah chunk konteks yang diambil

    Returns:
        {
          "answer_stream": Generator[str] — streaming tokens jawaban LLM,
          "sources":       List[{source, page_num, excerpt}] — sumber kutipan,
          "chunks_found":  int — jumlah chunk yang ditemukan,
        }
    """
    # Retrieve chunk relevan
    chunks = retrieve(user_question, top_k=top_k)

    # Buat daftar sumber (deduplicated by file+page)
    sources: list[dict[str, Any]] = []
    seen: set[tuple] = set()
    for chunk in chunks:
        key = (chunk["source"], chunk["page_num"])
        if key not in seen:
            seen.add(key)
            excerpt = chunk["text"]
            if len(excerpt) > 250:
                excerpt = excerpt[:250] + "..."
            sources.append(
                {
                    "source":   chunk["source"],
                    "page_num": chunk["page_num"],
                    "excerpt":  excerpt,
                    "distance": chunk["distance"],
                }
            )

    # Stream jawaban dari LLM
    answer_stream: Generator[str, None, None] = generate_answer_stream(
        user_question, chunks
    )

    return {
        "answer_stream": answer_stream,
        "sources":       sources,
        "chunks_found":  len(chunks),
    }
