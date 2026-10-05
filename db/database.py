"""
database.py — SQLite database untuk metadata dokumen & autentikasi multi-admin.

Tabel:
1. documents
   id          TEXT PRIMARY KEY   — UUID dokumen
   name        TEXT               — Nama file asli
   file_path   TEXT               — Path file yang disimpan
   upload_date TEXT               — ISO-8601 timestamp
   chunk_count INTEGER            — Jumlah chunk yang diindeks

2. admins
   id            INTEGER PRIMARY KEY AUTOINCREMENT
   username      TEXT UNIQUE NOT NULL
   password_hash TEXT NOT NULL
   role          TEXT NOT NULL DEFAULT 'admin'  -- 'superadmin' | 'admin'
   created_at    TEXT NOT NULL

Semua operasi menggunakan context manager agar koneksi otomatis di-commit/close.
"""

import sqlite3
from datetime import datetime
from typing import Any, Optional
import bcrypt
from config import DB_PATH, ADMIN_USERNAME, ADMIN_PASSWORD_HASH


def _get_conn() -> sqlite3.Connection:
    """Buka koneksi SQLite dengan row_factory untuk akses kolom by name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db() -> None:
    """
    Buat tabel `documents` dan `admins` jika belum ada.
    Dipanggil sekali saat aplikasi start.
    """
    with _get_conn() as conn:
        # Tabel dokumen
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
        # Tabel admin
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role          TEXT NOT NULL DEFAULT 'admin',
                created_at    TEXT NOT NULL
            )
            """
        )
        conn.commit()

    # Seed akun Super Admin awal jika tabel admins masih kosong
    _seed_initial_superadmin()


def _seed_initial_superadmin() -> None:
    """Jika belum ada akun admin sama sekali, buatkan akun Super Admin awal."""
    with _get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) AS n FROM admins").fetchone()["n"]
        if count == 0:
            username = ADMIN_USERNAME or "admin"
            if ADMIN_PASSWORD_HASH:
                pwd_hash = ADMIN_PASSWORD_HASH
            else:
                # Default password jika .env belum diisi sama sekali
                pwd_hash = bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                """
                INSERT INTO admins (username, password_hash, role, created_at)
                VALUES (?, ?, 'superadmin', ?)
                """,
                (username, pwd_hash, now),
            )
            conn.commit()
            print(f"[*] Akun Super Admin awal otomatis dibuat: '{username}' (role: superadmin)")


# ── Operasi Dokumen ──────────────────────────────────────────────────────────

def add_document_record(
    doc_id: str,
    name: str,
    file_path: str,
    chunk_count: int,
) -> None:
    """Tambah atau ganti record dokumen."""
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


# ── Operasi Admin Multi-User & Role ──────────────────────────────────────────

def get_admin_by_username(username: str) -> Optional[dict[str, Any]]:
    """Cari akun admin berdasarkan username (termasuk hash untuk verifikasi login)."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM admins WHERE username = ?", (username.strip(),)
        ).fetchone()
        return dict(row) if row else None


def get_admin_by_id(admin_id: int) -> Optional[dict[str, Any]]:
    """Cari akun admin berdasarkan ID."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT id, username, role, created_at FROM admins WHERE id = ?", (admin_id,)
        ).fetchone()
        return dict(row) if row else None


def get_all_admins() -> list[dict[str, Any]]:
    """Ambil daftar semua admin (tanpa password_hash untuk keamanan)."""
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT id, username, role, created_at FROM admins ORDER BY id ASC"
        ).fetchall()
        return [dict(row) for row in rows]


def create_admin(username: str, password_hash: str, role: str = "admin") -> dict[str, Any]:
    """Tambah akun admin baru."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO admins (username, password_hash, role, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (username.strip(), password_hash, role, now),
        )
        conn.commit()
        return {
            "id": cursor.lastrowid,
            "username": username.strip(),
            "role": role,
            "created_at": now,
        }


def update_admin(
    admin_id: int,
    role: Optional[str] = None,
    password_hash: Optional[str] = None,
) -> bool:
    """Perbarui role dan/atau password admin."""
    updates = []
    params = []
    if role is not None:
        updates.append("role = ?")
        params.append(role)
    if password_hash is not None:
        updates.append("password_hash = ?")
        params.append(password_hash)

    if not updates:
        return False

    params.append(admin_id)
    with _get_conn() as conn:
        cursor = conn.execute(
            f"UPDATE admins SET {', '.join(updates)} WHERE id = ?",
            tuple(params),
        )
        conn.commit()
        return cursor.rowcount > 0


def delete_admin(admin_id: int) -> bool:
    """Hapus akun admin berdasarkan ID."""
    with _get_conn() as conn:
        cursor = conn.execute("DELETE FROM admins WHERE id = ?", (admin_id,))
        conn.commit()
        return cursor.rowcount > 0


def count_superadmins() -> int:
    """Hitung berapa banyak superadmin yang tersisa di sistem."""
    with _get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) AS n FROM admins WHERE role = 'superadmin'"
        ).fetchone()["n"]
