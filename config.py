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
LLM_MODEL: str      = os.getenv("LLM_MODEL", "qwen2.5:3b")
EMBED_MODEL: str    = os.getenv("EMBED_MODEL", "bge-m3")

# ── RAG Parameters ──────────────────────────────────────────
CHUNK_SIZE: int    = int(os.getenv("CHUNK_SIZE", "600"))
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "100"))
TOP_K: int         = int(os.getenv("TOP_K", "5"))
# Jarak cosine maksimum (ChromaDB: makin kecil makin relevan). Potongan di atas ambang dibuang.
RELEVANCE_MAX_DISTANCE: float = float(os.getenv("RELEVANCE_MAX_DISTANCE", "0.50"))

# ── Mode Retrieval ───────────────────────────────────────────
# "linier"  : retrieve-then-generate (baseline), retrieval selalu dijalankan.
# "agentic" : LLM memilih tool (retrieve_dokumen, cek_tenggat).
RETRIEVAL_MODE: str = os.getenv("RETRIEVAL_MODE", "linier").strip().lower()
if RETRIEVAL_MODE not in ("linier", "agentic"):
    raise ValueError(f"RETRIEVAL_MODE harus 'linier' atau 'agentic', bukan '{RETRIEVAL_MODE}'.")

# ── Log Evaluasi ─────────────────────────────────────────────
# Jika True, setiap pertanyaan dicatat ke tabel SQLite `eval_log` (tanpa teks pertanyaan/data mahasiswa).
EVAL_LOGGING: bool = os.getenv("EVAL_LOGGING", "false").lower() == "true"

# ── Paths ────────────────────────────────────────────────────
CHROMA_DIR:  str = str(BASE_DIR / "chroma_db")
UPLOAD_DIR:  str = str(BASE_DIR / "uploaded_docs")
DOCS_DIR:    str = UPLOAD_DIR
DB_PATH:     str = str(BASE_DIR / "data.db")

# ── Admin Auth ───────────────────────────────────────────────
ADMIN_USERNAME:      str = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH: str = os.getenv("ADMIN_PASSWORD_HASH", "")

# ── Security & Access Protection ─────────────────────────────
CHAT_ACCESS_KEY: str = os.getenv("CHAT_ACCESS_KEY", "").strip()
RATE_LIMIT_CHAT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_CHAT_PER_MINUTE", "10"))

# ── Deployment ───────────────────────────────────────────────
# Daftar origin frontend dipisah koma, mis. "https://ta.vercel.app". Kosong = semua origin.
ALLOWED_ORIGINS: list[str] = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()] or ["*"]
SERVER_HOST: str = os.getenv("SERVER_HOST", "127.0.0.1")
SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
DEV_RELOAD: bool = os.getenv("DEV_RELOAD", "false").lower() == "true"

