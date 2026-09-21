"""
backend/main.py — FastAPI Application untuk Chatbot RAG Tugas Akhir.

Menyediakan:
  - REST API untuk Chat (SSE streaming response dari Ollama qwen3.5:9b)
  - REST API untuk Admin (Autentikasi, Upload Dokumen, Manajemen Dokumen, Statistik)
  - Static file serving untuk Frontend (HTML, CSS, JS) di port tetap 8000
"""

import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
from auth import (
    create_session_token,
    revoke_session_token,
    verify_admin_credentials,
    verify_session_token,
)
from db.database import (
    delete_document_record,
    get_all_documents,
    get_document,
    get_stats,
    initialize_db,
)
from rag.pipeline import delete_document, ingest_document, query_rag

# Inisialisasi DB SQLite saat startup
initialize_db()

app = FastAPI(
    title="Chatbot RAG API",
    description="Backend API untuk Chatbot RAG Tugas Akhir",
    version="2.0.0",
)

# CORS Middleware (mendukung jika frontend dibuka dari origin berbeda)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_cache_control_headers(request: Request, call_next):
    """Cegah caching browser yang membuat kode JS/CSS lama tetap aktif."""
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/static") or path in ["/", "/admin"]:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


# ── Dependency: Admin Auth ───────────────────────────────────────────────────

def require_admin(authorization: Optional[str] = Header(None)) -> str:
    """Validasi Bearer token pada header Authorization."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Header Authorization dibutuhkan.",
        )
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Format Authorization harus: Bearer <token>",
        )
    
    token = parts[1]
    if not verify_session_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesi tidak valid atau telah kedaluwarsa. Silakan login kembali.",
        )
    return token


# ── Schemas ──────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str
    top_k: Optional[int] = config.TOP_K


class LoginRequest(BaseModel):
    username: str
    password: str


# ── Health & Status Endpoints ────────────────────────────────────────────────

@app.get("/api/health")
def get_health():
    """Cek kesehatan sistem dan koneksi dependensi."""
    import requests

    ollama_ok = False
    try:
        r = requests.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=3)
        ollama_ok = r.status_code == 200
    except Exception:
        ollama_ok = False

    stats = get_stats()

    return {
        "status": "online",
        "ollama": {
            "connected": ollama_ok,
            "base_url": config.OLLAMA_BASE_URL,
            "llm_model": config.LLM_MODEL,
            "embed_model": config.EMBED_MODEL,
        },
        "database": {
            "documents_count": stats["document_count"],
            "total_chunks": stats["total_chunks"],
        },
    }


# ── Chat Endpoint (Streaming SSE) ────────────────────────────────────────────

@app.post("/api/chat")
def chat_stream(req: ChatRequest):
    """
    Streaming response RAG menggunakan Server-Sent Events (SSE).
    Mengirimkan event:
      1. 'status': progres tahapan AI (pencarian context, inisialisasi model)
      2. 'sources': metadata chunk yang ditemukan & sitasi dokumen rujukan
      3. 'token': potongan kata/token dari qwen3.5:9b secara real-time
      4. 'done': penanda selesai dengan statistik
    """
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Pertanyaan tidak boleh kosong.")

    def event_generator():
        try:
            # 1. Beritahu klien bahwa proses pencarian di ChromaDB dimulai
            status_init = json.dumps({"stage": "retrieving", "message": "Mencari konteks di database..."})
            yield f"event: status\ndata: {status_init}\n\n"

            rag_res = query_rag(question, top_k=req.top_k or config.TOP_K)
            sources = rag_res.get("sources", [])
            chunks_found = rag_res.get("chunks_found", 0)

            # 2. Beritahu status setelah dokumen ditemukan
            status_retrieved = json.dumps({
                "stage": "generating",
                "message": f"Ditemukan {chunks_found} referensi relevan. Merumuskan jawaban...",
            })
            yield f"event: status\ndata: {status_retrieved}\n\n"

            # Kirim sitasi sumber
            sources_payload = json.dumps({
                "sources": sources,
                "chunks_found": chunks_found,
            })
            yield f"event: sources\ndata: {sources_payload}\n\n"

            # Stream token jawaban dari model
            token_count = 0
            for token in rag_res["answer_stream"]:
                token_count += 1
                token_payload = json.dumps({"token": token})
                yield f"event: token\ndata: {token_payload}\n\n"

            # Kirim sinyal selesai
            done_payload = json.dumps({"token_count": token_count})
            yield f"event: done\ndata: {done_payload}\n\n"

        except Exception as e:
            err_payload = json.dumps({"error": str(e)})
            yield f"event: error\ndata: {err_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Admin Endpoints ──────────────────────────────────────────────────────────

@app.post("/api/admin/login")
def admin_login(body: LoginRequest):
    """Login admin menggunakan kredensial .env."""
    if verify_admin_credentials(body.username, body.password):
        token = create_session_token()
        return {"success": True, "token": token, "username": body.username}
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Username atau password admin salah.",
    )


@app.post("/api/admin/logout")
def admin_logout(token: str = Depends(require_admin)):
    """Logout admin dan hapus sesi."""
    revoke_session_token(token)
    return {"success": True, "message": "Berhasil logout."}


@app.get("/api/admin/check-session")
def check_session(token: str = Depends(require_admin)):
    """Cek apakah sesi admin masih valid."""
    return {"valid": True, "username": config.ADMIN_USERNAME}


@app.get("/api/admin/stats")
def admin_stats(_: str = Depends(require_admin)):
    """Ambil statistik sistem untuk dashboard admin."""
    return get_stats()


@app.get("/api/admin/documents")
def list_documents(_: str = Depends(require_admin)):
    """Daftar seluruh dokumen yang tersimpan di sistem."""
    return {"documents": get_all_documents()}


@app.post("/api/admin/upload")
async def upload_document(
    file: UploadFile = File(...),
    _: str = Depends(require_admin),
):
    """
    Upload dokumen (PDF, DOCX, TXT) dan jalankan pipeline ingest RAG.
    """
    filename = file.filename
    ext = Path(filename).suffix.lower()
    if ext not in [".pdf", ".docx", ".txt"]:
        raise HTTPException(
            status_code=400,
            detail=f"Tipe file '{ext}' tidak didukung. Harap upload PDF, DOCX, atau TXT.",
        )

    # Simpan file ke direktori uploaded_docs
    os.makedirs(config.DOCS_DIR, exist_ok=True)
    doc_id = str(uuid.uuid4())
    save_filename = f"{doc_id}_{filename}"
    file_path = os.path.join(config.DOCS_DIR, save_filename)

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Jalankan ingest dokumen
        chunk_count = ingest_document(
            file_path=file_path,
            doc_id=doc_id,
            doc_name=filename,
        )

        return {
            "success": True,
            "message": f"Dokumen '{filename}' berhasil diindeks ke dalam {chunk_count} chunk.",
            "doc_id": doc_id,
            "name": filename,
            "chunk_count": chunk_count,
        }
    except Exception as e:
        # Bersihkan file jika gagal
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        raise HTTPException(status_code=500, detail=f"Gagal memproses dokumen: {str(e)}")


@app.delete("/api/admin/documents/{doc_id}")
def remove_document(doc_id: str, _: str = Depends(require_admin)):
    """Hapus dokumen dari ChromaDB dan database SQLite."""
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan.")

    try:
        # Hapus vector & database record
        delete_document(doc_id)

        # Hapus file fisik jika masih ada
        file_path = doc.get("file_path")
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass

        return {"success": True, "message": f"Dokumen '{doc['name']}' berhasil dihapus."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menghapus dokumen: {str(e)}")


# ── Frontend HTML Routes & Static Files ──────────────────────────────────────

@app.get("/")
def serve_chat_page():
    """Halaman Utama User Chat (Tampilan Gemini)."""
    index_file = FRONTEND_DIR / "index.html"
    if not index_file.exists():
        return JSONResponse({"message": "Frontend belum di-deploy."}, status_code=404)
    return FileResponse(index_file)


@app.get("/admin")
def serve_admin_page():
    """Halaman Admin Panel Dokumen."""
    admin_file = FRONTEND_DIR / "admin.html"
    if not admin_file.exists():
        return JSONResponse({"message": "Admin page belum di-deploy."}, status_code=404)
    return FileResponse(admin_file)


# Mount static assets (css, js, images)
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
