# Catatan Perbaikan — Chatbot RAG TA

Dicatat: 21 November 2026. Status: **belum dikerjakan**, menunggu keputusan.

---

## 1. Penjelasan LLM terbuang pada jawaban tenggat (mode agentic)

**Masalah**
Sejak guard diubah (`rag/agent.py` → `terapkan_guard`), setiap kali `cek_tenggat` berhasil,
seluruh teks jawaban LLM diganti dengan hasil tenggat yang disusun kode
(`rag/tenggat.py` → `format_hasil_tenggat`). Tujuannya agar tanggal tidak salah disalin LLM
(kasus nyata: qwen2.5:3b menulis "20 November 2026" padahal tool mengembalikan 2026-11-10).

Efek sampingnya: penjelasan tambahan dan kutipan pedoman dari LLM ikut terbuang.

**Cakupan**
- Berlaku untuk **semua model** karena berasal dari desain guard, bukan dari model.
- Paling terasa di **qwen3.5:9b**, yang biasanya memanggil `retrieve_dokumen` dulu baru
  `cek_tenggat`, sehingga kutipan pedoman yang sudah diambil ikut hilang.
- Di **qwen2.5:3b** yang hilang hanya kalimat pengantar, karena model ini langsung memanggil `cek_tenggat`.
- Chip sumber di frontend tetap tampil.

**Opsi perbaikan**

| Opsi | Cara | Kelebihan | Kekurangan |
|---|---|---|---|
| **B (rekomendasi)** | Jika `retrieve_dokumen` juga dipanggil, kode menempelkan 1–2 potongan teratas (nama dokumen, halaman, kutipan) di bawah hasil tenggat | Tetap 100% deterministik; kutipan = teks asli ChromaDB yang lolos ambang; memenuhi syarat sitasi (nama dokumen + kutipan) | Potongan teratas belum tentu yang paling pas dengan pertanyaan tenggat |
| **C** | Teks LLM dipertahankan **hanya jika tidak memuat tanggal** (format ISO atau angka + nama bulan); hasil tenggat dari kode ditempel di bawahnya | Penjelasan LLM yang lebih luwes tetap tampil | "maksimal 4 minggu" atau tanggal dengan format lain bisa lolos, sehingga kesalahan sejenis bisa terulang |
| Tidak disarankan | Panggilan LLM kedua untuk "memperbaiki" jawaban | — | Tidak deterministik, menambah latensi, merusak keadilan perbandingan antarmode |

**Lokasi kode yang akan diubah**: `rag/agent.py` (`terapkan_guard`, `jalankan_agen`),
`rag/tenggat.py` (`format_hasil_tenggat`), dan test di `tests/test_mode.py`.

---

## 2. Temuan terbuka lain (dari uji Tahap 2)

1. **qwen2.5:3b lemah dalam pemilihan tool**: 6/10 tepat, kategori 1/4. Model ini menolak
   3 dari 4 pertanyaan pedoman tanpa memanggil tool, dengan menyalin teks penolakan.
   Guard tidak menangkapnya karena penolakan memang diizinkan. qwen3.5:9b: 10/10
   (longgar), 7/10 (ketat), kategori 4/4, tetapi latensi rata-rata ±44 detik.
   → Perlu diputuskan model untuk mode agentic (`LLM_MODEL` di `.env`).
2. **Sumber dikarang**: qwen3.5:9b pernah menulis "hal. terkait tenggat waktu" dari panduan
   yang tidak ada di database.
3. **Sitasi tidak lengkap di mode linier**: qwen2.5:3b sering tidak menyertakan nama dokumen
   dan kutipan walaupun prompt memintanya.
4. **Data yang perlu diisi**:
   - `hari_libur` di `aturan_tenggat.json` masih kosong (tenggat hari kerja bisa lebih awal).
   - `RELEVANCE_MAX_DISTANCE=0.50` perlu dikalibrasi dengan soal uji berlabel.
   - Unggah "Panduan TA Program Studi Sistem Informasi 2026" (belum ada di database).
   - Siapkan set soal evaluasi dengan `id_pertanyaan`, serta skrip penghitung MRR dan Recall@k dari `eval_log`.
5. **Kosmetik**: pesan status SSE di mode agentic masih "Mencari konteks di database..."
   meskipun agen belum tentu memanggil retrieval.
