# PRD: Chatbot RAG untuk Ekstraksi Data

## 1. Ringkasan Proyek
Aplikasi web chatbot berbasis Python yang memungkinkan pengguna bertanya dalam bahasa natural dan mendapatkan jawaban yang diekstrak dari kumpulan dokumen internal (PDF, Word, TXT). Sistem menggunakan **RAG (Retrieval-Augmented Generation)** yang dibangun sendiri (custom, bukan framework RAG siap pakai) dan model AI **lokal via Ollama**, sehingga tidak ada data yang dikirim ke API eksternal (privasi terjaga, biaya nol per-token).

Ada dua peran:
- **Admin**: mengelola basis dokumen (tambah, hapus, edit) — perlu login.
- **User**: hanya melakukan chat tanya-jawab — tanpa login, langsung akses.

## 2. Tujuan
- Memudahkan siapa saja (tanpa keahlian teknis) mencari informasi dari dokumen internal lewat chat.
- Menjamin jawaban AI berbasis fakta dari dokumen yang ada (bukan halusinasi), dengan menampilkan sumber kutipan.
- Berjalan sepenuhnya offline/lokal dari sisi model AI, agar bisa dipakai untuk dokumen sensitif.

## 3. Peran & Hak Akses

| Fitur | Admin | User |
|---|---|---|
| Login diperlukan | Ya | Tidak |
| Upload dokumen (PDF/DOCX/TXT) | Ya | Tidak |
| Hapus dokumen | Ya | Tidak |
| Edit/replace dokumen | Ya | Tidak |
| Chat tanya-jawab | Ya (opsional) | Ya |
| Melihat daftar dokumen yang tersedia | Ya | Ya (read-only, opsional) |
| Upload gambar/video di chat | Tidak | Tidak (di luar scope) |

Catatan: karena user tidak login, sistem tidak membedakan identitas user satu sama lain — chat bersifat anonim per sesi browser.

## 4. Tech Stack yang Diusulkan

| Komponen | Pilihan | Alasan |
|---|---|---|
| Bahasa | **Python 3.11** (3.12 juga aman) | Kompatibel penuh dengan semua dependency (`chromadb`, `streamlit`, `pdfplumber`, `python-docx`, `ollama`); hindari 3.13/3.14 karena sebagian dependency ChromaDB (mis. `onnxruntime`) belum selalu stabil di versi Python terbaru |
| UI Framework | **Streamlit** | Cepat dibangun, built-in session state, cocok untuk 2 halaman (admin/user), mudah di-deploy |
| LLM lokal | **Ollama** — model: `qwen3.5:9b` (sudah terinstal & siap pakai di PC user) | Tidak perlu setup/pull ulang, cukup kuat untuk tugas RAG |
| Embedding model | **`bge-m3`** (via Ollama, sudah terinstal di PC user) | Multibahasa (termasuk Indonesia), performa retrieval bagus untuk model ukurannya, tidak perlu setup ulang |
| Vector Database | **ChromaDB** (persistent, file lokal) | Ringan, tanpa server terpisah, native Python, mudah filter metadata (nama file, halaman) |
| Parsing dokumen (PDF→teks) | **`pdfplumber`** | Akurat untuk PDF dengan tabel/layout kompleks, sesuai kebutuhan dokumen TA |
| Parsing dokumen (DOCX/TXT) | `python-docx` (DOCX), native (TXT) | Standar, stabil |
| Auth admin | `streamlit-authenticator` atau session state + hash password sederhana (`bcrypt`) di file/SQLite | Simple sesuai kebutuhan (belum perlu JWT) |
| Storage metadata dokumen | SQLite | Ringan, cukup untuk daftar dokumen + tracking chunk |

### Alasan "RAG sendiri" (bukan LangChain/LlamaIndex penuh)
Karena kamu ingin kontrol penuh atas proses retrieval, kita bangun pipeline manual:
`Dokumen → Chunking → Embedding (Ollama) → Simpan di ChromaDB → Query user → Embed query → Retrieve top-k chunk → Susun prompt dengan context → Kirim ke LLM Ollama → Jawaban + sitasi`

## 5. Arsitektur & Alur Data

```
[Admin] --upload--> [Parser] --chunk--> [Embedding: Ollama] --> [ChromaDB]
                                                                     |
[User] --pertanyaan--> [Embed query: Ollama] --similarity search-->-|
                                                                     |
                        [Top-k chunks + metadata] --> [Prompt Builder]
                                                              |
                                                    [LLM: Ollama] --> [Jawaban + sitasi nama file & excerpt]
```

Untuk deployment: aplikasi Streamlit (bisa di-deploy ke server/cloud/domain publik), tapi memanggil Ollama yang tetap jalan di PC lokal melalui **port yang di-share/expose** (misalnya via reverse tunnel seperti `ngrok`/`cloudflared`, atau VPN/port forwarding jika di jaringan yang sama). Ini perlu dicatat sebagai **risiko latensi & ketersediaan**: kalau PC lokal mati/PC tidak online, chatbot yang di-deploy tidak bisa menjawab.

## 6. Fitur Detail

### Admin
1. Login (username/password, hash disimpan, session-based).
2. Upload dokumen baru (PDF/DOCX/TXT) → otomatis di-parse, di-chunk, di-embed, disimpan.
3. Lihat daftar dokumen (nama, tanggal upload, jumlah chunk).
4. Hapus dokumen → hapus entri + embedding terkait dari ChromaDB.
5. Edit/replace dokumen → hapus versi lama, upload versi baru (re-index).

### User
1. Langsung akses halaman chat tanpa login.
2. Ketik pertanyaan → sistem retrieve konteks relevan → jawaban ditampilkan.
3. Setiap jawaban menyertakan **sumber**: nama file + potongan teks (excerpt) yang jadi dasar jawaban.
4. Riwayat chat hanya ada selama sesi berjalan (hilang saat refresh/tutup tab) — sesuai keputusanmu.

## 7. Non-Functional Requirements
- **Privasi**: dokumen & embedding tidak pernah keluar dari infrastruktur milik sendiri (model lokal).
- **Bahasa**: asumsi dokumen & percakapan mayoritas Bahasa Indonesia — model & embedding yang dipilih mendukung ini.
- **Performa**: chunk size disarankan 500–800 karakter dengan overlap ~100, agar retrieval akurat tanpa membebani konteks LLM.
- **Skalabilitas awal**: cukup untuk puluhan–ratusan dokumen; jika nanti ribuan dokumen, pertimbangkan migrasi ke vector DB yang lebih besar (Qdrant/Milvus).
- **Keamanan ChromaDB**: karena aplikasi ini akan di-deploy (terpapar ke jaringan/publik), wajib menggunakan versi ChromaDB terbaru yang sudah dipatch — ada laporan celah keamanan kritis (pre-auth code injection, CVE-2026-45829) pada versi-versi tertentu. Versi ChromaDB akan di-pin secara eksplisit di `requirements.txt` dan dicek ulang sebelum deployment.

## 8. Yang Belum Diputuskan (Asumsi Sementara)
- Tidak ada rate-limiting/anti-spam untuk user tanpa login (bisa jadi bahan iterasi berikutnya).
- Tidak ada enkripsi khusus untuk dokumen yang disimpan (bisa ditambah jika dokumen sangat sensitif).

## 9. Rencana Build (Urutan Prototipe)
Catatan: Ollama beserta model `qwen3.5:9b` dan `bge-m3` sudah terinstal di PC, jadi langkah setup Ollama **dihilangkan** dari rencana build ini.

1. Susun struktur modular proyek (`parser.py`, `chunker.py`, `embedder.py`, `vectorstore.py`, `retriever.py`, `generator.py`, `pipeline.py`) agar tiap komponen custom RAG mudah diuji & diganti terpisah.
2. Bangun modul parsing dokumen (PDF via `pdfplumber`, DOCX via `python-docx`, TXT native → teks bersih).
3. Bangun modul chunking teks (chunk size + overlap).
4. Bangun modul embedding (panggil `bge-m3` via Ollama) & simpan ke ChromaDB.
5. Bangun fungsi retrieval (query → top-k chunks).
6. Bangun prompt builder + pemanggilan LLM `qwen3.5:9b` via Ollama, sertakan sitasi nama file & excerpt.
7. Bangun UI Streamlit halaman User (chat).
8. Bangun UI Streamlit halaman Admin (login + CRUD dokumen).
9. Testing end-to-end dengan beberapa dokumen contoh.
10. Siapkan cara expose Ollama (ngrok/cloudflared) untuk skenario deploy.

---
Setelah PRD ini kamu setujui, aku bisa langsung mulai bangun kode prototipenya sesuai urutan di atas.
