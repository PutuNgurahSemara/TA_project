# 🤖 Chatbot RAG — Tugas Akhir

Aplikasi Chatbot berbasis **Retrieval-Augmented Generation (RAG)** untuk mengekstrak dan menjawab pertanyaan berdasarkan dokumen internal (**PDF, DOCX, TXT**) secara cerdas, akurat, dan **100% lokal** (*Zero Data Leak*).

---

## ✨ Fitur Utama

- **Model Lokal Penuh (Zero Data Leak):** Menggunakan **Ollama** dengan LLM (`qwen3.5:9b` / `qwen2.5:3b`) dan Embedder (`bge-m3`). Tidak ada data atau dokumen yang dikirim ke internet/cloud luar.
- **Ekstraksi Tabel Cerdas (*Table-to-Markdown*):** Mendeteksi tabel dalam dokumen secara otomatis dan mengonversinya menjadi format tabel Markdown (`| Kolom 1 | Kolom 2 |`) agar konteks struktural dibaca presisi oleh LLM.
- **Indikator Waktu Berpikir Real-Time:** Menampilkan stopwatch real-time saat AI memproses pencarian konteks di vector store dan merumuskan jawaban (*Time to First Token*).
- **Streaming Response (SSE):** Respon AI mengalir kata per kata (*real-time typewriter streaming*) menggunakan Server-Sent Events.
- **Sitasi Sumber Referensi:** Setiap jawaban dilengkapi chip nama dokumen, nomor halaman asal, dan skor jarak kemiripan (*similarity distance*).
- **Admin Panel & Manajemen Hak Akses:** Dashboard berbasis sesi web untuk upload dokumen, re-indeks vektor, inspeksi statistik chunk, serta manajemen akun multi-admin (*Super Admin* & *Admin*).
- **Embedded Vector Database:** Menggunakan ChromaDB persistent lokal, tanpa memerlukan instalasi server database eksternal.

---

## 🏗️ Tech Stack

| Komponen | Teknologi | Keterangan |
| :--- | :--- | :--- |
| **Backend** | Python 3.11 / 3.12, FastAPI, Uvicorn | Asynchronous REST & SSE API |
| **Vector Store** | ChromaDB (Persistent Embedded) | Penyimpanan vektor lokal di `./chroma_db` |
| **Relational DB** | SQLite (`data.db`) | Metadata dokumen dan akun admin |
| **AI Engine** | Ollama | LLM Runner & Embedding Generator lokal |
| **Document Parser** | `pdfplumber`, `python-docx` | Ekstraksi teks & tabel dokumen |
| **Frontend** | Vanilla HTML5, CSS3, Modern JavaScript | Antarmuka responsif tanpa dependensi framework Node.js |

---

## 🚀 Prasyarat Sistem

Sebelum memulai instalasi, pastikan sistem Anda memenuhi prasyarat berikut:

1. **Python:** Versi **3.11** atau **3.12** (Direkomendasikan 3.11).
   - Periksa versi dengan: `python --version`
2. **Ollama:** Terinstal dan dapat diakses dari terminal/CMD.
   - Unduh dari: [ollama.com](https://ollama.com)
   - Pastikan aplikasi Ollama sedang berjalan di latar belakang (default port: `11434`).
3. **Model Ollama:** Unduh model LLM dan Embedder berikut melalui terminal:
   ```bash
   ollama pull qwen3.5:9b
   ollama pull bge-m3
   ```
   *(Catatan: Jika spesifikasi RAM/VRAM terbatas, Anda dapat menggunakan model yang lebih ringan seperti `qwen2.5:3b`)*.

---

## 🛠️ Panduan Instalasi Langkah Demi Langkah

### 1. Clone Repositori & Buka Direktori
```bash
git clone <URL_REPOSITORY_ANDA>
cd TA
```

---

### 2. (Direkomendasikan) Buat & Aktifkan Virtual Environment

Menggunakan virtual environment sangat disarankan agar paket Python terisolasi dan tidak konflik dengan proyek lain:

- **Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  ```
  *(Jika muncul pesan error Execution Policy di PowerShell, jalankan: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)*

- **Windows (Command Prompt / CMD):**
  ```cmd
  python -m venv .venv
  .\.venv\Scripts\activate.bat
  ```

- **Linux / macOS:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

---

### 3. Install Dependensi Python

Pastikan pip diperbarui ke versi terbaru, lalu pasang paket dari `requirements.txt`:
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### 4. Konfigurasi Environment (`.env`)

Salin file template `.env.example` menjadi `.env`:

- **Windows (PowerShell):**
  ```powershell
  Copy-Item .env.example .env
  ```
- **Linux / macOS:**
  ```bash
  cp .env.example .env
  ```

Buka file `.env` dan sesuaikan nilainya bila diperlukan:

```ini
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=qwen3.5:9b          # Atau qwen2.5:3b jika RAM/VRAM lebih kecil
EMBED_MODEL=bge-m3

# RAG Hyperparameters
CHUNK_SIZE=600               # Panjang karakter per chunk dokumen
CHUNK_OVERLAP=100            # Karakter tumpang tindih antar-chunk
TOP_K=5                      # Jumlah referensi chunk yang diambil untuk prompt

# Admin Credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=         # Dikosongkan untuk default, atau atur via setup_admin.py

# Security & Access Protection (Opsional)
CHAT_ACCESS_KEY=             # Kosongkan jika chat terbuka bebas; isi string jika ingin PIN akses
RATE_LIMIT_CHAT_PER_MINUTE=10
```

---

### 5. Inisialisasi Database & Akun Admin

Saat aplikasi pertama kali dijalankan, sistem otomatis membuat database `data.db` dan akun Super Admin awal:
- **Default Username:** `admin`
- **Default Password:** `admin123`

Untuk mengubah password admin atau menambah akun admin baru, jalankan CLI manajemen admin:
```bash
python setup_admin.py
```
Ikuti instruksi di layar untuk:
- Mengubah/Reset password Super Admin
- Menambahkan akun Admin baru
- Menghapus akun admin

---

## ⚡ Menjalankan Aplikasi

Jalankan server aplikasi menggunakan:
```bash
python main.py
```

Setelah server aktif, buka browser Anda di:
- 💬 **Antarmuka Chat User:** [http://localhost:8000](http://localhost:8000)
- ⚙️ **Admin Panel Dokumen:** [http://localhost:8000/admin](http://localhost:8000/admin) *(Masuk dengan kredensial admin)*

---

## 🧰 Skrip Utilitas Tambahan

### 1. Pengelolaan Akun Admin (`setup_admin.py`)
```bash
python setup_admin.py
```
Menu CLI interaktif untuk mengelola pengguna admin SQLite (melihat daftar akun, reset password superadmin, menambah akun, atau menghapus akun).

### 2. Inspeksi Hasil Parsing Dokumen (`view_parsed.py`)
```bash
python view_parsed.py
```
Skrip terminal untuk menguji dan melihat bagaimana parser mengekstrak halaman dan tabel dari dokumen yang diunggah ke format teks/markdown.

---

## 📁 Struktur Direktori

```text
TA/
├── backend/                  # Server FastAPI & Logic
│   ├── auth_routes.py        # Endpoint login, logout, dan manajemen sesi admin
│   ├── chat_routes.py        # Endpoint streaming SSE untuk tanya-jawab chatbot
│   ├── document_routes.py    # Endpoint REST untuk upload, indeks, dan hapus file
│   └── main.py               # Konfigurasi app FastAPI, middleware CORS, dan static mounts
│
├── frontend/                 # Tampilan Pengguna & Admin
│   ├── index.html            # Antarmuka Chatbot User
│   ├── admin.html            # Dashboard Admin Dokumen & Pengaturan
│   ├── css/                  # File styling (Tema modern, dark/light mode)
│   └── js/                   # Logika SSE client, renderer markdown, dan handler upload
│
├── rag/                      # RAG Core Engine
│   ├── parser.py             # Ekstraksi PDF (teks & tabel), DOCX, dan TXT
│   ├── chunker.py            # Pemotongan teks rekursif dengan chunk overlap
│   ├── embedder.py           # Komunikasi embedding dengan Ollama (bge-m3)
│   ├── vectorstore.py        # Antarmuka ChromaDB lokal persistent
│   ├── retriever.py          # Similarity search pencarian top-k referensi
│   ├── generator.py          # Generator streaming prompt ke LLM Ollama
│   └── pipeline.py           # Orkestrasi alur RAG end-to-end
│
├── db/
│   └── database.py           # SQLite connection & CRUD untuk metadata & akun
│
├── uploaded_docs/            # Direktori penyimpanan file asli yang diunggah
├── chroma_db/                # Direktori penyimpanan data vektor ChromaDB lokal
├── data.db                   # Database SQLite lokal (metadata dokumen & admin)
├── .env.example              # Contoh template konfigurasi environment
├── config.py                 # Pemuat variabel konfigurasi global
├── setup_admin.py            # CLI helper pengelolaan admin
├── view_parsed.py            # CLI helper inspeksi dokumen hasil parsing
├── requirements.txt          # Daftar pustaka Python
└── main.py                   # Entry point server Uvicorn
```

---

## ❓ Troubleshooting & Pertanyaan Umum (FAQ)

### 1. `Cannot connect to Ollama` / `Connection Refused`
- Pastikan aplikasi Ollama sudah dibuka dan aktif di komputer Anda.
- Uji koneksi terminal dengan: `curl http://localhost:11434/api/tags`
- Jika memakai port selain default, sesuaikan nilai `OLLAMA_BASE_URL` di file `.env`.

### 2. `model "qwen3.5:9b" not found`
- Jalankan perintah: `ollama pull qwen3.5:9b`
- Atau ubah `LLM_MODEL` pada file `.env` ke model yang sudah Anda miliki (contoh: `qwen2.5:3b`).

### 3. File upload gagal atau tidak terindeks
- Pastikan ekstensi file adalah `.pdf`, `.docx`, atau `.txt`.
- Jika dokumen berformat PDF hasil scan (gambar tanpa teks asli), disarankan menggunakan dokumen dengan teks asli atau melakukan OCR terlebih dahulu.
