"""
config.py — Konfigurasi global aplikasi Chatbot RAG.
Semua nilai diambil dari environment variable (.env) dengan fallback default.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Direktori root proyek (folder tempat config.py berada)
BASE_DIR = Path(__file__).parent.absolute()

# Load .env dari root proyek
load_dotenv(BASE_DIR / ".env")

# ── Ollama ──────────────────────────────────────────────────
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LLM_MODEL: str      = os.getenv("LLM_MODEL", "qwen3.5:9b")
EMBED_MODEL: str    = os.getenv("EMBED_MODEL", "bge-m3")

# ── RAG Parameters ──────────────────────────────────────────
CHUNK_SIZE: int    = int(os.getenv("CHUNK_SIZE", "600"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "100"))
TOP_K: int         = int(os.getenv("TOP_K", "5"))

# ── Paths ────────────────────────────────────────────────────
CHROMA_DIR:  str = str(BASE_DIR / "chroma_db")
UPLOAD_DIR:  str = str(BASE_DIR / "uploaded_docs")
DOCS_DIR:    str = UPLOAD_DIR
DB_PATH:     str = str(BASE_DIR / "data.db")

# ── Admin Auth ───────────────────────────────────────────────
ADMIN_USERNAME:      str = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH: str = os.getenv("ADMIN_PASSWORD_HASH", "")
