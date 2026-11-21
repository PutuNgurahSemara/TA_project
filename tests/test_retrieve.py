"""Test tool retrieve_dokumen (vector store dipalsukan, tanpa Ollama)."""

import json

import pytest

import config
from rag.pipeline import tebak_kategori
from rag.tools import KETERANGAN_KOSONG, retrieve_dokumen

AMBANG = config.RELEVANCE_MAX_DISTANCE


def panggil(**argumen) -> dict:
    return json.loads(retrieve_dokumen.invoke(argumen))


def test_filter_kategori(toko):
    toko.tambah("kp1", "KP", AMBANG - 0.2)
    toko.tambah("ta1", "TA", AMBANG - 0.3)
    toko.tambah("mg1", "Magang", AMBANG - 0.25)

    hasil = panggil(query="syarat KP", kategori="KP")["hasil"]

    assert toko.panggilan[-1]["filter"] == {"kategori": "KP"}
    assert [h["chunk_id"] for h in hasil] == ["kp1"]
    assert all(h["kategori"] == "KP" for h in hasil)


def test_tanpa_kategori_tidak_memakai_filter(toko):
    toko.tambah("kp1", "KP", AMBANG - 0.2)
    panggil(query="apa saja")
    assert toko.panggilan[-1]["filter"] is None


def test_jumlah_hasil_sesuai_k_dan_urut(toko):
    for i, jarak in enumerate([0.40, 0.10, 0.30, 0.20, 0.35]):
        toko.tambah(f"c{i}", "TA", min(jarak, AMBANG - 0.01))

    hasil = panggil(query="struktur proposal", k=3)["hasil"]

    assert len(hasil) == 3
    assert [h["peringkat"] for h in hasil] == [1, 2, 3]
    assert [h["jarak"] for h in hasil] == sorted(h["jarak"] for h in hasil)
    assert set(hasil[0]) == {"chunk_id", "nama_dokumen", "kategori", "halaman", "kutipan", "jarak", "peringkat"}


def test_k_default_dari_config(toko):
    toko.tambah("c1", "TA", AMBANG - 0.1)
    panggil(query="apa saja")
    assert toko.panggilan[-1]["top_k"] == config.TOP_K


def test_potongan_di_atas_ambang_dibuang(toko):
    toko.tambah("dekat", "KP", AMBANG - 0.1)
    toko.tambah("tepat", "KP", AMBANG)            # tepat di ambang masih lolos
    toko.tambah("jauh", "KP", AMBANG + 0.05)

    hasil = panggil(query="penilaian KP")["hasil"]

    assert [h["chunk_id"] for h in hasil] == ["dekat", "tepat"]


def test_pertanyaan_di_luar_cakupan_hasil_kosong(toko):
    toko.tambah("a", "TA", AMBANG + 0.1)
    toko.tambah("b", "KP", AMBANG + 0.3)

    keluaran = panggil(query="Siapa presiden Indonesia?")

    assert keluaran == {"hasil": [], "keterangan": KETERANGAN_KOSONG}


@pytest.mark.parametrize("nama, kategori", [
    ("[2025] A PANDUAN KERJA PRAKTIK ITK.pdf", "KP"),
    ("Pedoman KP 2025.pdf", "KP"),
    ("[2025] B PANDUAN KEPENULISAN TUGAS AKHIR ITK_split.pdf", "TA"),
    ("Panduan TA SI 2026.pdf", "TA"),
    ("[2025] 6 BUKU PANDUAN MAGANG KEPROFESIAN.pdf", "Magang"),
    ("DATA STATISTIK.pdf", "Umum"),   # "TA" di dalam kata tidak dihitung
    ("SKPI.pdf", "Umum"),             # "KP" di dalam kata tidak dihitung
])
def test_tebak_kategori_dari_nama_dokumen(nama, kategori):
    assert tebak_kategori(nama) == kategori
