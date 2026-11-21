"""
main.py — Entry point utama untuk menjalankan Chatbot RAG Server (FastAPI + Uvicorn).
"""

import sys

import uvicorn

import config

# Output ke file/log di Windows default cp1252 → print emoji crash; paksa UTF-8.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

if __name__ == "__main__":
    print(f"🚀 Memulai Chatbot RAG Server di http://{config.SERVER_HOST}:{config.SERVER_PORT} ...")
    uvicorn.run(
        "backend.main:app",
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        reload=config.DEV_RELOAD,
    )
