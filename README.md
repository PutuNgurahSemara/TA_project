# Chatbot RAG — Tugas Akhir

Aplikasi Chatbot berbasis **Retrieval-Augmented Generation (RAG)** untuk mengekstrak dan menjawab pertanyaan berdasarkan dokumen internal (PDF, DOCX, TXT) secara cerdas, akurat, dan lokal.

---

## ✨ Fitur Utama

- **Model Lokal Penuh (Zero Data Leak):** Menggunakan Ollama dengan LLM `qwen3.5:9b` dan Embedder `bge-m3`.
- **Ekstraksi Tabel Cerdas (Table-to-Markdown):** Otomatis mendeteksi tabel dokumen dan mengubahnya menjadi format Markdown Table (`| Kolom 1 | Kolom 2 |`) sehingga relasi baris dan kolom dipahami secara presisi oleh AI.
- **Indikator Waktu Berpikir Real-Time:** Menampilkan stopwatch real-time saat AI mencari referensi dan merumuskan jawaban, serta mengunci durasi berpikir (*Time to First Token*).
- **Streaming Response (SSE):** Respon kata per kata mengalir langsung (*real-time typewriter streaming*).
- **Sitasi Sumber Referensi:** Setiap jawaban dilengkapi chip sumber dokumen, nomor halaman, dan jarak kemiripan (*similarity distance*).
- **Admin Panel Dokumen:** Dashboard untuk upload, indeks ulang, memantau statistik chunk, dan menghapus dokumen dengan autentikasi berbasis sesi.

---

## 🚀 Prasyarat Sistem

1. **Python 3.11 / 3.12 / 3.14**
2. **Ollama** terinstal dan berjalan:
   ```bash
   ollama pull qwen3.5:9b
   ollama pull bge-m3
   ```

---

## 🛠️ Instalasi & Menjalankan

1. **Clone Repositori:**
   ```bash
   git clone <URL_REPOSITORY_ANDA>
   cd TA
   ```

2. **Install Dependensi:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Konfigurasi Environment:**
   Salin file `.env.example` menjadi `.env`:
   ```bash
   cp .env.example .env
   ```
   Buat password admin dengan menjalankan:
   ```bash
   python setup_admin.py
   ```

4. **Jalankan Aplikasi:**
   ```bash
   python main.py
   ```
   Buka browser di:
   - **User Chat:** [http://localhost:8000](http://localhost:8000)
   - **Admin Panel:** [http://localhost:8000/admin](http://localhost:8000/admin)

---

## 📁 Struktur Direktori

```text
├── backend/            # FastAPI app, routing SSE chat, dan REST API admin
├── frontend/           # Antarmuka HTML, CSS, JS (Tema Modern Gemini)
├── rag/                # Pipeline RAG (Parser, Chunker, Embedder, Retriever, Generator)
├── db/                 # Manajemen SQLite database
├── setup_admin.py      # Utility setup password admin
├── view_parsed.py      # Utility CLI untuk inspeksi teks & tabel hasil parsing
└── main.py             # Entry point server Uvicorn
```
