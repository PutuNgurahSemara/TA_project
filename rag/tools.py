"""
tools.py — Tool LangChain untuk mode agentic: retrieve_dokumen dan cek_tenggat.

Kedua tool mengembalikan string JSON agar isi ToolMessage bisa dibaca LLM dan diurai
ulang oleh rag/agent.py (untuk sitasi sumber dan log evaluasi).
"""

import json
from typing import Literal, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from config import TOP_K
from rag.retriever import retrieve
from rag.tenggat import daftar_tahapan, hitung_tenggat, muat_aturan

Kategori = Literal["TA", "KP", "Magang"]
KETERANGAN_KOSONG = "tidak ditemukan di dokumen"


def _json(data) -> str:
    return json.dumps(data, ensure_ascii=False)


# ── Tool 1: retrieve_dokumen ─────────────────────────────────────────────────

class RetrieveDokumenInput(BaseModel):
    query: str = Field(description="Pertanyaan atau kata kunci yang dicari di dokumen pedoman.")
    kategori: Optional[Kategori] = Field(
        None, description="Kategori dokumen: 'TA', 'KP', atau 'Magang'. Kosongkan bila tidak jelas."
    )
    k: int = Field(TOP_K, ge=1, le=20, description="Jumlah potongan dokumen yang diambil.")


@tool("retrieve_dokumen", args_schema=RetrieveDokumenInput)
def retrieve_dokumen(query: str, kategori: Optional[str] = None, k: int = TOP_K) -> str:
    """Cari potongan dokumen pedoman yang paling relevan dari basis data.

    WAJIB dipakai untuk SETIAP pertanyaan informasi tentang Tugas Akhir (TA),
    Kerja Praktik (KP), atau Magang, misalnya syarat, prosedur, struktur laporan,
    penilaian, atau format penulisan. Isi `kategori` bila jelas dari pertanyaan
    (TA, KP, atau Magang). Jawab hanya dari hasil tool ini; jika hasilnya kosong,
    katakan informasinya tidak ditemukan di dokumen.
    """
    hasil = retrieve(query, top_k=k, kategori=kategori)
    if not hasil:
        return _json({"hasil": [], "keterangan": KETERANGAN_KOSONG})
    return _json({"hasil": hasil})


# ── Tool 2: cek_tenggat ──────────────────────────────────────────────────────

class CekTenggatInput(BaseModel):
    kegiatan: Kategori = Field(description="Kegiatan: 'TA', 'KP', atau 'Magang'.")
    id_tahapan: str = Field(description="ID tahapan, lihat daftar pada deskripsi tool.")
    # Bertipe str (bukan date) agar tanggal salah format dibalas pesan ramah oleh hitung_tenggat,
    # bukan ValidationError Pydantic berbahasa Inggris.
    tanggal_acuan: str = Field(description="Tanggal acuan yang disebutkan mahasiswa, format YYYY-MM-DD.")
    tanggal_hari_ini: Optional[str] = Field(
        None, description="Opsional, format YYYY-MM-DD. Kosongkan untuk memakai tanggal hari ini (WITA)."
    )


def _deskripsi_cek_tenggat() -> str:
    """Deskripsi tool dibangun dari aturan_tenggat.json agar daftar tahapan selalu sesuai file."""
    aturan = muat_aturan()
    baris = [
        f"- kegiatan={keg}, id_tahapan={t['id_tahapan']}: {t['nama_tahapan']} (acuan: {t['acuan']})"
        for keg in aturan["kegiatan"]
        for t in daftar_tahapan(aturan, keg)
    ]
    return (
        "Hitung tenggat kegiatan akademik berdasarkan ketentuan pedoman dan tanggal acuan "
        "yang disebutkan mahasiswa. Perhitungan dilakukan oleh kode, jangan menghitung sendiri.\n"
        "Tahapan yang tersedia:\n" + "\n".join(baris) + "\n"
        "Jika mahasiswa BELUM menyebutkan tanggal acuan, JANGAN memanggil tool ini dan JANGAN "
        "menebak tanggal; tanyakan dulu tanggal acuannya kepada mahasiswa."
    )


@tool("cek_tenggat", args_schema=CekTenggatInput, description=_deskripsi_cek_tenggat())
def cek_tenggat(
    kegiatan: str,
    id_tahapan: str,
    tanggal_acuan: str,
    tanggal_hari_ini: Optional[str] = None,
) -> str:
    """Hitung tenggat (deskripsi lengkap untuk LLM dibangun dari aturan_tenggat.json)."""
    return _json(hitung_tenggat(kegiatan, id_tahapan, tanggal_acuan, tanggal_hari_ini))


SEMUA_TOOL = [retrieve_dokumen, cek_tenggat]
