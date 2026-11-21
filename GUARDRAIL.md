# Guardrail Sistem Chatbot RAG

Dokumen ini menjelaskan setiap **guardrail** (pagar pengaman) di sistem: apa yang dijaga,
bagaimana caranya, di mana kodenya, dan apa yang **tidak** bisa ditangkapnya.

Guardrail dibagi menjadi empat lapis:

| Lapis | Tujuan | Ditegakkan oleh |
|---|---|---|
| A. Kualitas retrieval | Hanya potongan dokumen yang relevan yang sampai ke LLM | Kode (deterministik) |
| B. Jawaban LLM | Jawaban berdasarkan dokumen dan tool, bukan karangan | Prompt + guard kode |
| C. Privasi data | Data mahasiswa tidak tersimpan permanen | Kode (deterministik) |
| D. Akses & keamanan | Mencegah penyalahgunaan endpoint | Kode (deterministik) |

> Prinsip umum: aturan yang **harus** dipatuhi ditegakkan oleh **kode**. Prompt hanya
> mengarahkan perilaku LLM, karena LLM (terutama model kecil) tidak selalu patuh.

---

## A. Guardrail Kualitas Retrieval

### A1. Ambang relevansi (jarak maksimum)
- **Apa:** potongan dokumen dengan jarak cosine di atas `RELEVANCE_MAX_DISTANCE`
  (default `0.50`, di `config.py` / `.env`) dibuang sebelum diberikan ke LLM.
- **Mengapa:** ChromaDB selalu mengembalikan *k* potongan terdekat, sekalipun tidak relevan.
  Tanpa ambang, pertanyaan di luar cakupan tetap mendapat "konteks" yang bisa disalahgunakan LLM.
- **Catatan:** ChromaDB mengembalikan **jarak** (1 − kemiripan cosine). Makin kecil, makin relevan.
- **Berlaku di:** kedua mode (linier dan agentic), karena keduanya memakai fungsi yang sama.
- **Kode:** `rag/retriever.py` → `retrieve()`

### A2. Filter kategori dokumen
- **Apa:** jika kategori diisi (`TA` / `KP` / `Magang`), pencarian hanya dilakukan pada
  potongan dengan metadata `kategori` yang sama.
- **Mengapa:** mencegah jawaban tentang KP diambil dari panduan Magang, dan sebaliknya.
- **Kategori ditentukan otomatis** dari nama file saat upload (`rag/pipeline.py` →
  `tebak_kategori`). File yang tidak dikenali diberi `Umum` dan tidak ikut terfilter.
- **Kode:** `rag/retriever.py`, `rag/vectorstore.py`, `rag/pipeline.py`

### A3. Pembuangan potongan terlalu pendek
- **Apa:** saat dokumen diindeks, potongan yang lebih pendek dari `MIN_CHUNK_CHARS = 40`
  karakter dibuang.
- **Mengapa:** potongan yang isinya hanya footer halaman (misalnya `"PANDUAN KERJA PRAKTIK 35"`)
  sempat memenuhi hasil pencarian dan membuat jawaban menjadi "tidak ditemukan".
- **Kode:** `rag/chunker.py`

---

## B. Guardrail Jawaban LLM

### B1. System prompt
Kedua mode memakai system prompt yang mewajibkan LLM:
1. menjawab **hanya** berdasarkan konteks dokumen atau hasil tool;
2. memakai teks baku saat informasi tidak ada:
   *"Maaf, informasi tersebut tidak ditemukan dalam dokumen yang tersedia."*;
3. menolak pertanyaan di luar TA, KP, dan Magang dengan **penolakan standar**:
   *"Maaf, saya hanya dapat menjawab pertanyaan seputar Tugas Akhir, Kerja Praktik, dan Magang
   berdasarkan dokumen pedoman yang tersedia."*;
4. menyertakan nama dokumen dan kutipan sumber;
5. (agentic) menanyakan tanggal acuan bila belum disebutkan, bukan menebaknya.

- **Kode:** `rag/generator.py` (`SYSTEM_PROMPT`, mode linier), `rag/agent.py` (`SYSTEM_PROMPT_AGEN`)
- **Keterbatasan:** ini hanya arahan. Model kecil (qwen2.5:3b) sering tidak menyertakan sitasi.

### B2. Guard mode agentic: "tidak boleh menjawab informasi tanpa tool"
Setelah agen selesai, fungsi `terapkan_guard()` memeriksa tool apa saja yang dipanggil,
lalu memutuskan jawaban final. Aturannya diperiksa **berurutan**:

| # | Kondisi | Tindakan |
|---|---|---|
| 1 | `cek_tenggat` berhasil (hasil tanpa `error`) | Jawaban LLM **diganti** teks hasil tenggat yang disusun kode (lihat B3) |
| 2 | `retrieve_dokumen` dipanggil | Jawaban LLM diloloskan |
| 3 | Tidak ada tool, atau `cek_tenggat` gagal, dan jawaban memuat penolakan standar | Diloloskan sebagai penolakan standar |
| 4 | Sama seperti #3, tetapi jawaban ≤ 250 karakter, mengandung `?`, dan **tanpa angka** | Diloloskan sebagai **pertanyaan klarifikasi** |
| 5 | Sama seperti #3, tetapi jawaban ≤ 150 karakter dan mengandung kata sapaan (halo, hai, selamat pagi/siang/sore/malam, terima kasih, …) | Diloloskan sebagai **sapaan** |
| 6 | Selain itu | Diganti **penolakan standar**, dan `guard_aktif = 1` dicatat di log evaluasi |

**Mengapa klarifikasi tidak boleh mengandung angka?** Isi pedoman hampir selalu memuat
angka (minggu, SKS, halaman). Jawaban seperti *"Revisi laporan KP paling lambat 3 minggu, bukan?"*
adalah informasi pedoman yang disamarkan sebagai pertanyaan, sehingga ditolak.

**Contoh:**

| Jawaban LLM (tanpa tool) | Hasil guard |
|---|---|
| "Halo! Ada yang bisa saya bantu?" | Lolos (sapaan) |
| "Kapan tanggal seminar hasil KP Anda?" | Lolos (klarifikasi) |
| "Sidang TA paling cepat 14 minggu setelah seminar proposal." | **Diganti penolakan** |
| "Revisi laporan KP paling lambat 3 minggu, bukan?" | **Diganti penolakan** |

- **Kode:** `rag/agent.py` → `terapkan_guard()`, `jalankan_agen()`
- **Test:** `tests/test_mode.py`

### B3. Hasil tenggat dihitung **dan ditampilkan** oleh kode
- **Perhitungan:** tool `cek_tenggat` menghitung tenggat secara deterministik di Python
  (`rag/tenggat.py`), bukan oleh LLM. Ketentuannya dibaca dari `aturan_tenggat.json`.
  - Tenggat = tanggal acuan + durasi; tanggal acuan sendiri tidak dihitung.
  - Hari tenggat itu sendiri masih dianggap **belum lewat**.
  - `hari_kerja` = Senin–Jumat dan melewati tanggal di `hari_libur`. Jika `hari_libur` kosong,
    hasilnya bisa lebih awal dari tenggat sebenarnya.
- **Penampilan:** jika `cek_tenggat` berhasil, jawaban final disusun oleh
  `format_hasil_tenggat()`, bukan disalin ulang oleh LLM.
  Kasus nyata yang mendasari aturan ini: qwen2.5:3b pernah menulis tenggat *"20 November 2026"*,
  padahal tool mengembalikan `2026-11-10`.
- **Disclaimer tetap** selalu disertakan: *"Hasil ini merupakan pemeriksaan mandiri berdasarkan
  pedoman, bukan keputusan resmi program studi."*
- **Input tidak valid:** kegiatan atau tahapan yang tidak dikenal mengembalikan daftar tahapan yang valid.
  Tanggal salah format mengembalikan pesan ramah (bukan error teknis).
- **Kode:** `rag/tenggat.py`, `rag/tools.py`, `rag/agent.py` · **Test:** `tests/test_tenggat.py`, `tests/test_mode.py`

### B4. Batas langkah agen
- **Apa:** agen dihentikan setelah `BATAS_LANGKAH = 12` langkah (recursion limit LangGraph).
- **Mengapa:** mencegah agen berputar memanggil tool tanpa henti.
- **Kode:** `rag/agent.py`

---

## C. Guardrail Privasi Data

### C1. Log evaluasi tanpa data mahasiswa
Jika `EVAL_LOGGING=true`, setiap pertanyaan dicatat di tabel `eval_log` (`data.db`). Isinya:

| Dicatat | **Tidak** dicatat |
|---|---|
| `id_pertanyaan` (id soal uji, opsional) | Teks pertanyaan dan jawaban |
| Mode retrieval | Argumen tool (mis. tanggal seminar) |
| Nama tool sesuai urutan | Data akademik (tanggal, SKS, IPK) |
| `chunk_id` dan peringkat hasil retrieval | Alamat IP |
| Latensi total (ms), `guard_aktif` | |

- **Kode:** `db/database.py` → `add_eval_log()`, `backend/main.py`

### C2. Riwayat percakapan hanya selama sesi
- Riwayat disimpan **di memori tab browser** (`frontend/js/chat.js`) dan hilang saat halaman
  ditutup atau tombol hapus chat ditekan. Server tidak pernah menyimpannya.
- Server menolak riwayat lebih dari **6 pesan** atau pesan lebih dari **4000 karakter** (HTTP 422).
- **Kode:** `backend/main.py` (`ChatRequest`, `PesanRiwayat`)

---

## D. Guardrail Akses & Keamanan

| Guardrail | Nilai | Kode |
|---|---|---|
| Rate limit chat per IP | `RATE_LIMIT_CHAT_PER_MINUTE` (default 10/menit) → HTTP 429 | `backend/security.py`, `backend/main.py` |
| Rate limit login admin per IP | 5 percobaan/menit → HTTP 429 | `backend/main.py` |
| Kode akses chat (opsional) | `CHAT_ACCESS_KEY` di `.env`; kosong = chat terbuka | `backend/main.py` |
| Resolusi IP klien | Header `cf-connecting-ip` / `x-forwarded-for` hanya dipercaya dari localhost (cloudflared) | `backend/security.py` |
| Autentikasi admin | Token Bearer, password bcrypt, sesi kedaluwarsa 12 jam; role dibaca ulang dari DB setiap request | `auth.py` |
| Otorisasi | Manajemen akun hanya Super Admin; Super Admin terakhir tidak bisa dihapus/diturunkan | `backend/main.py` |
| Validasi upload | Hanya `.pdf`, `.docx`, `.txt`; maksimal 50 MB; komponen direktori di nama file dibuang | `backend/main.py` |
| Dokumentasi API | Swagger, ReDoc, dan OpenAPI dimatikan | `backend/main.py` |

---

## E. Yang **Tidak** Ditangkap Guardrail (Keterbatasan)

Temuan dari uji `scripts/uji_pemilihan_tool.py`:

1. **Penolakan palsu.** qwen2.5:3b menolak 3 dari 4 pertanyaan pedoman tanpa memanggil tool.
   Guard meloloskannya karena penolakan memang diizinkan. Ini terlihat di log evaluasi
   (tool kosong untuk pertanyaan dalam cakupan), bukan dicegah.
2. **Sumber dikarang setelah retrieval.** Jika `retrieve_dokumen` dipanggil, isi jawaban
   tidak diperiksa ulang. Kalimat atau nomor halaman karangan LLM bisa lolos.
3. **Heuristik klarifikasi dan sapaan.** Klarifikasi yang memuat angka ikut tertolak,
   sedangkan informasi pendek tanpa angka yang diakhiri `?` bisa lolos.
4. **Penjelasan LLM pada jawaban tenggat terbuang** (konsekuensi B3). Lihat opsi perbaikan
   di `CATATAN_PERBAIKAN.md`.
5. **Rate limiter dan sesi admin disimpan di memori.** Keduanya terhapus saat server dimulai ulang.

---

## F. Cara Memverifikasi

```powershell
python -m pytest
```

Test berjalan tanpa Ollama dan mencakup ambang jarak, filter kategori, guard agentic,
perhitungan tenggat, dan nilai batasnya.

```powershell
python scripts/uji_pemilihan_tool.py --model qwen2.5:3b
```

Butuh Ollama. Mengukur apakah model memilih tool yang tepat dan seberapa sering guard aktif.
