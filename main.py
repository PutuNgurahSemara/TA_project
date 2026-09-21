"""
main.py — Entry point utama untuk menjalankan Chatbot RAG Server (FastAPI + Uvicorn).
"""

import uvicorn

if __name__ == "__main__":
    print("🚀 Memulai Chatbot RAG Server di http://localhost:8000 ...")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
