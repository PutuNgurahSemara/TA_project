"""
main.py — Entry point utama untuk menjalankan Chatbot RAG Server (FastAPI + Uvicorn).
"""

import uvicorn

import config

if __name__ == "__main__":
    print(f"🚀 Memulai Chatbot RAG Server di http://{config.SERVER_HOST}:{config.SERVER_PORT} ...")
    uvicorn.run(
        "backend.main:app",
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        reload=config.DEV_RELOAD,
    )
