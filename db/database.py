"""
database.py — SQLite database untuk metadata dokumen.

Tabel: documents
  id          TEXT PRIMARY KEY   — UUID dokumen
  name        TEXT               — Nama file asli
  file_path   TEXT               — Path file yang disimpan
  upload_date TEXT               — ISO-8601 timestamp
  chunk_count INTEGER            — Jumlah chunk yang diindeks

Semua operasi menggunakan context manager agar koneksi otomatis di-commit/close.
"""

import sqlite3
from datetime import datetime
from typing import Any, Optional
from config import DB_PATH


def _get_conn() -> sqlite3.Connection:
    """Buka koneksi SQLite dengan row_factory untuk akses kolom by name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db() -> None:
    """
    Buat tabel `documents` jika belum ada.
    Dipanggil sekali saat aplikasi pertama kali start.
    """
    with _get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id          TEXT PRIMARY KEY,
                name        TEXT    NOT NULL,
                file_path   TEXT    NOT NULL,
                upload_date TEXT    NOT NULL,
                chunk_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()


def add_document_record(
    doc_id: str,
    name: str,
    file_path: str,
    chunk_count: int,
) -> None:
    """
    Tambah atau ganti record dokumen.
    Menggunakan INSERT OR REPLACE agar aman untuk re-index.
    """
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO documents
                (id, name, file_path, upload_date, chunk_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            (doc_id, name, file_path, datetime.now().isoformat(), chunk_count),
        )
        conn.commit()


def get_all_documents() -> list[dict[str, Any]]:
    """Ambil semua dokumen, diurutkan dari paling baru."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM documents ORDER BY upload_date DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def get_document(doc_id: str) -> Optional[dict[str, Any]]:
    """Ambil satu dokumen berdasarkan ID. Return None jika tidak ada."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ).fetchone()
        return dict(row) if row else None


def delete_document_record(doc_id: str) -> None:
    """Hapus record dokumen dari SQLite."""
    with _get_conn() as conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        conn.commit()


def get_stats() -> dict[str, int]:
    """Hitung statistik: total dokumen dan total chunk."""
    with _get_conn() as conn:
        doc_count = conn.execute(
            "SELECT COUNT(*) AS n FROM documents"
        ).fetchone()["n"]
        chunk_sum = conn.execute(
            "SELECT COALESCE(SUM(chunk_count), 0) AS n FROM documents"
        ).fetchone()["n"]
        return {"document_count": doc_count, "total_chunks": chunk_sum}
