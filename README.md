# 🤖 Chatbot RAG Pedoman TA, KP, dan Magang — Tugas Akhir

Aplikasi chatbot berbasis **Retrieval-Augmented Generation (RAG)** yang menjawab pertanyaan mahasiswa
Program Studi Sistem Informasi ITK tentang **Tugas Akhir (TA), Kerja Praktik (KP), dan Magang**
berdasarkan dokumen pedoman resmi (**PDF, DOCX, TXT**). Semua proses berjalan **100% lokal**
(*Zero Data Leak*) tanpa API cloud.

---

## 📌 Persoalan

Mahasiswa yang menjalani TA, KP, atau Magang harus memahami beberapa dokumen pedoman yang tebal
(puluhan halaman per dokumen). Dalam praktiknya muncul beberapa persoalan:

1. **Mencari informasi spesifik lambat.** Syarat pendaftaran, struktur laporan, atau komponen
   penilaian tersebar di banyak halaman. Pencarian `Ctrl + F` hanya mencocokkan kata yang persis
   sama, tidak memahami sinonim dan konteks, dan sulit dipakai untuk isi yang berbentuk tabel.
2. **Tenggat mudah salah hitung atau terlewat.** Ketentuan seperti "revisi proposal paling lambat
   20 hari kerja" atau "sidang TA paling cepat 14 minggu dan paling lambat 45 minggu setelah seminar
   proposal" harus dihitung sendiri oleh mahasiswa.
3. **Pertanyaan yang sama berulang** kepada dosen pembimbing dan staf program studi.
4. **Chatbot umum berbasis cloud tidak cocok.** Jawabannya bisa dikarang, tidak merujuk pedoman
   resmi program studi, dan pertanyaan mahasiswa dikirim ke server pihak ketiga.

**Solusi yang dibangun:**
- Jawaban diambil dari potongan dokumen pedoman yang relevan, lengkap dengan **sitasi** nama
  dokumen, halaman, dan kutipan.
- Perhitungan tenggat dilakukan oleh **kode Python secara deterministik**, bukan oleh LLM.
- **Guardrail** menolak pertanyaan di luar cakupan dan jawaban yang tidak berdasarkan dokumen
  (lihat [GUARDRAIL.md](GUARDRAIL.md)).
- Dua mode retrieval, **linier** (baseline) dan **agentic** (LLM memilih tool), yang memakai fungsi
  retrieval yang sama sehingga bisa dibandingkan secara adil dalam evaluasi.

---

## 👥 Pengguna

| Peran | Siapa | Akses |
|---|---|---|
| **Mahasiswa** (pengguna utama) | Mahasiswa Program Studi Sistem Informasi ITK yang sedang atau akan menjalani TA, KP, atau Magang | Halaman chat (`/`), tanpa login. Opsional memakai kode akses jika `CHAT_ACCESS_KEY` diisi |
| **Admin** | Dosen atau staf Program Studi Sistem Informasi | Panel admin (`/admin`): upload dan hapus dokumen pedoman, melihat statistik |
| **Super Admin** | Pengelola sistem di program studi | Semua akses Admin, ditambah mengelola akun admin |

---

## ✨ Fitur Utama

- **Model Lokal Penuh (Zero Data Leak):** **Ollama** dengan LLM `qwen3.5:9b` (default) atau
  `qwen2.5:3b`, serta embedder `bge-m3`. Tidak ada dokumen atau pertanyaan yang dikirim ke internet.
- **Dua Mode Retrieval** (`RETRIEVAL_MODE` di `.env`):
  - `linier`: retrieval selalu dijalankan sebelum LLM menjawab (*retrieve-then-generate*).
  - `agentic`: LLM memilih tool `retrieve_dokumen` (cari pedoman) atau `cek_tenggat` (hitung tenggat).
- **Cek Tenggat Deterministik:** menghitung tenggat sidang TA, revisi proposal TA, revisi laporan KP,
  dan laporan magang dari tanggal yang disebutkan mahasiswa. Ketentuan disimpan di
  [`aturan_tenggat.json`](aturan_tenggat.json), sehingga cukup file ini yang diperbarui bila pedoman direvisi.
- **Filter Kategori Dokumen:** kategori TA, KP, atau Magang ditentukan otomatis dari nama file saat upload.
- **Ambang Relevansi:** potongan dokumen yang terlalu jauh maknanya dari pertanyaan dibuang.
- **Ekstraksi Tabel (*Table-to-Markdown*):** tabel di PDF/DOCX dikonversi ke tabel Markdown.
- **Streaming Response (SSE)** dan **indikator waktu berpikir** real-time.
- **Sitasi Sumber:** chip nama dokumen, nomor halaman, dan jarak kemiripan pada setiap jawaban.
- **Log Evaluasi (opsional):** mencatat mode, urutan tool, peringkat chunk, dan latensi untuk
  menghitung MRR, Recall@k, ketepatan pemilihan tool, dan latensi, tanpa menyimpan data mahasiswa.
- **Admin Panel:** upload/hapus dokumen dan manajemen akun multi-admin (*Super Admin* dan *Admin*).

---

## 🏗️ Tech Stack

| Komponen | Teknologi | Keterangan |
| :--- | :--- | :--- |
| **Backend** | Python 3.11 / 3.12, FastAPI, Uvicorn | REST API & SSE streaming |
| **Orkestrasi LLM** | LangChain, LangGraph (`create_agent`) | Chain mode linier, agen dan tool mode agentic |
| **Vector Store** | ChromaDB (persistent, embedded) | Penyimpanan vektor lokal di `./chroma_db`, metrik cosine |
| **Relational DB** | SQLite (`data.db`) | Metadata dokumen, akun admin, log evaluasi |
| **AI Engine** | Ollama | LLM `qwen3.5:9b` / `qwen2.5:3b`, embedding `bge-m3` |
| **Document Parser** | `pdfplumber`, `python-docx` | Ekstraksi teks dan tabel |
| **Frontend** | Vanilla HTML5, CSS3, JavaScript | Tanpa build step / Node.js |
| **Testing** | pytest | Berjalan tanpa Ollama (vector store dan LLM dipalsukan) |

---

## 🚀 Prasyarat Sistem

1. **Python 3.11 atau 3.12** (direkomendasikan 3.11). Periksa dengan `python --version`.
2. **Ollama** terinstal dan berjalan di latar belakang (port default `11434`). Unduh dari [ollama.com](https://ollama.com).
3. **Model Ollama:**
   ```bash
   ollama pull qwen3.5:9b
   ollama pull bge-m3
   ```
   Jika RAM/VRAM terbatas, gunakan model yang lebih ringan:
   ```bash
   ollama pull qwen2.5:3b
   ```
   lalu ubah `LLM_MODEL=qwen2.5:3b` di `.env`. Perbandingan keduanya ada di bagian
   **Batas Penggunaan** di bawah.

---

## 🛠️ Instalasi

### 1. Clone repositori
```bash
git clone https://github.com/PutuNgurahSemara/TA_project.git
cd TA_project
```

### 2. (Direkomendasikan) Buat dan aktifkan virtual environment

- **Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  ```
  *(Jika muncul error Execution Policy, jalankan: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`)*
- **Windows (CMD):**
  ```cmd
  python -m venv .venv
  .\.venv\Scripts\activate.bat
  ```
- **Linux / macOS:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### 3. Install dependensi
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Konfigurasi `.env`

Salin template, lalu sesuaikan nilainya bila perlu:

- **Windows (PowerShell):** `Copy-Item .env.example .env`
- **Linux / macOS:** `cp .env.example .env`

Variabel terpenting:

```ini
# Ollama
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=qwen3.5:9b            # atau qwen2.5:3b untuk PC terbatas
EMBED_MODEL=bge-m3

# RAG
CHUNK_SIZE=600                  # panjang karakter per potongan dokumen
CHUNK_OVERLAP=100               # tumpang tindih antarpotongan
TOP_K=5                         # jumlah potongan yang diambil
RELEVANCE_MAX_DISTANCE=0.50     # jarak cosine maksimum; potongan di atasnya dibuang

# Mode & evaluasi
RETRIEVAL_MODE=linier           # linier | agentic
EVAL_LOGGING=false              # true = catat ke tabel eval_log

# Admin & keamanan
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=            # kosong = password default admin123
CHAT_ACCESS_KEY=                # kosong = chat terbuka; isi untuk mewajibkan kode akses
RATE_LIMIT_CHAT_PER_MINUTE=10
```

### 5. Atur hari libur nasional (untuk cek tenggat)

Isi daftar `hari_libur` di [`aturan_tenggat.json`](aturan_tenggat.json) dengan format `YYYY-MM-DD`,
misalnya `["2026-12-25"]`. Jika dibiarkan kosong, tenggat yang dihitung dalam hari kerja bisa lebih
awal dari tenggat sebenarnya.

---

## ⚡ Menjalankan Aplikasi (Lokal)

1. Pastikan **Ollama sedang berjalan**:
   ```bash
   curl http://localhost:11434/api/tags
   ```
2. Jalankan server:
   ```bash
   python main.py
   ```
   Saat pertama kali dijalankan, sistem otomatis membuat `data.db` dan akun Super Admin awal
   (username `admin`, password `admin123`). **Segera ganti password ini** dengan `python setup_admin.py`.
3. Buka di browser:
   - 💬 Chat mahasiswa: [http://localhost:8000](http://localhost:8000)
   - ⚙️ Panel admin: [http://localhost:8000/admin](http://localhost:8000/admin)
4. **Unggah dokumen pedoman** lewat panel admin. Agar kategori terdeteksi otomatis, nama file harus
   memuat salah satu kata berikut:

   | Kategori | Kata pada nama file |
   |---|---|
   | TA | `TUGAS AKHIR` atau `TA` |
   | KP | `KERJA PRAKTIK` atau `KP` |
   | Magang | `MAGANG` |

   Singkatan `TA` dan `KP` harus berdiri sendiri, dipisah spasi atau tanda baca selain garis bawah
   (`Panduan TA 2026.pdf` terdeteksi, `Panduan_TA.pdf` tidak). File yang tidak cocok diberi kategori
   `Umum` dan tidak ikut tersaring saat pencarian per kategori.

### Mengganti mode retrieval
Ubah `RETRIEVAL_MODE=linier` atau `RETRIEVAL_MODE=agentic` di `.env`, lalu jalankan ulang server.

### Data lama (sebelum fitur kategori ada)
Jika `chroma_db` berisi dokumen yang diindeks sebelum fitur kategori ditambahkan, jalankan sekali
(backup folder `chroma_db` terlebih dahulu):
```bash
python scripts/migrasi_kategori.py
```

---

## 🧪 Pengujian

| Perintah | Butuh Ollama | Isi |
|---|---|---|
| `python -m pytest` | Tidak | Test `retrieve_dokumen` (filter kategori, jumlah *k*, ambang jarak, hasil kosong), `cek_tenggat` (aturan 1–4, nilai batas, hari kerja dan libur, input tidak valid), dan mode (linier selalu retrieve, guard agentic) |
| `python scripts/uji_pemilihan_tool.py` | Ya | 10 contoh pertanyaan untuk mengecek apakah LLM memilih tool yang tepat. Default `qwen3.5:9b`; ganti dengan `--model qwen2.5:3b`. Hasil disimpan ke `scripts/hasil_uji_tool_<model>.json` |

**Log evaluasi:** set `EVAL_LOGGING=true`, lalu kirim pertanyaan uji ke `POST /api/chat` dengan field
opsional `id_pertanyaan`. Hasilnya tercatat di tabel `eval_log` pada `data.db`.

---

## ⚠️ Batas Penggunaan

**Cakupan dan sifat jawaban**
- Chatbot hanya menjawab seputar **TA, KP, dan Magang** berdasarkan dokumen yang diunggah admin.
  Pertanyaan di luar cakupan ditolak.
- Kualitas jawaban bergantung pada kelengkapan dokumen. Informasi yang tidak ada di dokumen akan
  dijawab "tidak ditemukan".
- LLM tetap bisa keliru atau tidak menyertakan sitasi lengkap. **Selalu periksa chip sumber** sebelum
  mengandalkan jawaban.
- Jawaban dan hasil cek tenggat **bukan keputusan resmi program studi**.

**Cek tenggat**
- Hanya untuk empat tahapan di `aturan_tenggat.json` (sidang TA, revisi proposal TA, revisi laporan KP,
  laporan magang).
- **Tidak memakai kalender akademik.** Hari libur hanya diperhitungkan jika didaftarkan di `hari_libur`.
- Hasil bergantung pada tanggal acuan yang dimasukkan mahasiswa.

**Dokumen**
- Format yang didukung: PDF (teks asli), DOCX, TXT, maksimal **50 MB**.
- PDF hasil scan (gambar tanpa lapisan teks) tidak didukung karena tidak ada OCR.
- Dioptimalkan untuk dokumen dan percakapan **berbahasa Indonesia**.

**Percakapan dan privasi**
- Chatbot hanya mengingat **6 pesan terakhir** dalam satu tab browser. Riwayat hilang saat halaman
  ditutup dan tidak disimpan di server.
- Sistem tidak menyimpan data akademik mahasiswa. Log evaluasi hanya berisi id soal, tool, chunk,
  dan latensi.

**Perangkat dan ketersediaan**
- Berjalan di **satu PC lokal**. Chatbot hanya dapat dipakai selama PC, Ollama, dan server menyala.
- Kecepatan bergantung pada perangkat. Hasil uji 10 pertanyaan mode agentic di PC pengembang:

  | Model | Ketepatan pemilihan tool | Rata-rata latensi |
  |---|---|---|
  | `qwen3.5:9b` (default) | 10/10 | ±44 detik |
  | `qwen2.5:3b` (alternatif) | 6/10 | ±4 detik |

- Batas **10 pertanyaan per menit per IP** (dapat diubah). Sesi login admin dan hitungan rate limit
  hilang saat server dimulai ulang.

---

## 🧰 Skrip Utilitas

| Skrip | Fungsi |
|---|---|
| `python setup_admin.py` | Menu CLI untuk melihat, membuat, mereset, dan menghapus akun admin |
| `python view_parsed.py` | Melihat hasil parsing teks dan tabel dari dokumen di `uploaded_docs/` |
| `python scripts/migrasi_kategori.py` | Menambahkan kategori ke chunk lama (sekali jalan) |
| `python scripts/uji_pemilihan_tool.py` | Uji pemilihan tool mode agentic (butuh Ollama) |

---

## 📁 Struktur Direktori

```text
TA_project/
├── backend/
│   ├── main.py               # FastAPI: endpoint chat (SSE), admin, dan file statis
│   └── security.py           # Rate limiter dan resolusi IP klien
├── frontend/
│   ├── index.html            # Halaman chat mahasiswa
│   ├── admin.html            # Panel admin
│   ├── css/                  # Styling
│   └── js/                   # chat.js (SSE + riwayat sesi), admin.js, config.js
├── rag/
│   ├── parser.py             # Ekstraksi PDF (teks & tabel), DOCX, TXT
│   ├── chunker.py            # Pemotongan teks rekursif
│   ├── embedder.py           # Embedding bge-m3 via Ollama
│   ├── vectorstore.py        # Antarmuka ChromaDB
│   ├── retriever.py          # Fungsi retrieval bersama (filter kategori + ambang jarak)
│   ├── generator.py          # Prompt dan streaming LLM (mode linier)
│   ├── tools.py              # Tool retrieve_dokumen dan cek_tenggat
│   ├── tenggat.py            # Perhitungan tenggat deterministik
│   ├── agent.py              # Agen mode agentic dan guard
│   └── pipeline.py           # Orkestrasi ingest dan query (pemilihan mode)
├── db/
│   └── database.py           # SQLite: dokumen, admin, eval_log
├── tests/                    # Test pytest (tanpa Ollama)
├── scripts/                  # Migrasi kategori dan uji pemilihan tool
├── aturan_tenggat.json       # Ketentuan tenggat dan daftar hari libur
├── auth.py                   # Autentikasi dan sesi admin
├── config.py                 # Konfigurasi dari .env
├── main.py                   # Entry point server
├── setup_admin.py            # CLI pengelolaan admin
├── view_parsed.py            # CLI inspeksi hasil parsing
├── GUARDRAIL.md              # Penjelasan guardrail sistem
├── CATATAN_PERBAIKAN.md      # Catatan perbaikan yang belum dikerjakan
├── requirements.txt
└── .env.example
```

Folder `uploaded_docs/`, `chroma_db/`, dan file `data.db` dibuat otomatis saat aplikasi berjalan
dan tidak ikut di-commit.

---

## ❓ Troubleshooting

### `Cannot connect to Ollama` / `Connection Refused`
- Pastikan aplikasi Ollama sudah berjalan.
- Uji dengan `curl http://localhost:11434/api/tags`.
- Jika memakai port lain, sesuaikan `OLLAMA_BASE_URL` di `.env`.

### `model "qwen3.5:9b" not found`
- Jalankan `ollama pull qwen3.5:9b`, atau ubah `LLM_MODEL` ke model yang sudah ada (misalnya `qwen2.5:3b`).

### File upload gagal atau tidak terindeks
- Pastikan ekstensi `.pdf`, `.docx`, atau `.txt` dan ukuran maksimal 50 MB.
- PDF hasil scan perlu di-OCR terlebih dahulu.

### Jawaban selalu "tidak ditemukan"
- Pastikan dokumen terkait sudah diunggah dan kategorinya benar.
- `RELEVANCE_MAX_DISTANCE` mungkin terlalu ketat. Naikkan sedikit (misalnya `0.55`) lalu uji ulang.

### `UnicodeEncodeError` saat menjalankan di Windows
- Sudah ditangani di `main.py` (output dipaksa UTF-8). Pastikan memakai versi terbaru repo ini.
