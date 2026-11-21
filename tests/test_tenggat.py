"""Test perhitungan tenggat (aturan 1–4 dari aturan_tenggat.json, Tabel 3.3 proposal)."""

import copy
import json
from datetime import date, timedelta

import pytest

from rag.tenggat import DISCLAIMER, hitung_tenggat, muat_aturan, tambah_durasi
from rag.tools import cek_tenggat

ACUAN = date(2026, 3, 2)  # Senin


@pytest.fixture
def aturan():
    data = muat_aturan()
    data["hari_libur"] = []  # test tidak bergantung pada isi daftar libur di file
    return data


def hitung(aturan, kegiatan, tahapan, hari_ini, acuan=ACUAN):
    return hitung_tenggat(kegiatan, tahapan, acuan.isoformat(), hari_ini.isoformat(), aturan=aturan)


# ── Aturan 1: Sidang TA, rentang 14–45 minggu ────────────────────────────────

@pytest.mark.parametrize(
    "minggu_ke, status",
    [(13, "belum_bisa"), (14, "dalam_rentang"), (45, "dalam_rentang"), (46, "lewat")],
)
def test_aturan1_sidang_ta_rentang(aturan, minggu_ke, status):
    hasil = hitung(aturan, "TA", "sidang_ta", ACUAN + timedelta(weeks=minggu_ke))
    assert hasil["paling_cepat"] == "2026-06-08"   # +14 minggu
    assert hasil["paling_lambat"] == "2027-01-11"  # +45 minggu
    assert hasil["status"] == status
    assert "tenggat" not in hasil


def test_aturan1_sehari_sebelum_dan_sesudah_batas(aturan):
    cepat, lambat = date(2026, 6, 8), date(2027, 1, 11)
    assert hitung(aturan, "TA", "sidang_ta", cepat - timedelta(days=1))["status"] == "belum_bisa"
    assert hitung(aturan, "TA", "sidang_ta", lambat + timedelta(days=1))["status"] == "lewat"


# ── Aturan 2: Revisi proposal TA, 20 hari kerja ──────────────────────────────

def test_aturan2_revisi_proposal_20_hari_kerja(aturan):
    hasil = hitung(aturan, "TA", "revisi_proposal", ACUAN)
    assert hasil["tenggat"] == "2026-03-30"  # 4 minggu kerja penuh, akhir pekan dilewati
    assert hasil["sisa_hari"] == 28
    assert hasil["status"] == "belum_lewat"


def test_aturan2_hari_libur_terdaftar_tidak_dihitung(aturan):
    aturan["hari_libur"] = ["2026-03-17"]
    assert hitung(aturan, "TA", "revisi_proposal", ACUAN)["tenggat"] == "2026-03-31"


def test_hari_kerja_melewati_akhir_pekan():
    jumat = date(2026, 3, 6)
    assert tambah_durasi(jumat, 1, "hari_kerja", set()) == date(2026, 3, 9)    # Senin
    assert tambah_durasi(jumat, 6, "hari_kerja", set()) == date(2026, 3, 16)


def test_hari_kerja_melewati_akhir_pekan_dan_libur():
    jumat = date(2026, 3, 6)
    assert tambah_durasi(jumat, 1, "hari_kerja", {date(2026, 3, 9)}) == date(2026, 3, 10)


def test_satuan_hari_kalender():
    assert tambah_durasi(ACUAN, 10, "hari", set()) == date(2026, 3, 12)


# ── Aturan 3: Revisi laporan KP, 3 minggu (dengan nilai batas) ───────────────

SEMINAR_KP = date(2026, 10, 20)
TENGGAT_KP = date(2026, 11, 10)


@pytest.mark.parametrize(
    "hari_ini, sisa, status",
    [
        (TENGGAT_KP - timedelta(days=1), 1, "belum_lewat"),
        (TENGGAT_KP, 0, "hari_ini"),                       # hari tenggat belum lewat
        (TENGGAT_KP + timedelta(days=1), -1, "lewat"),
    ],
)
def test_aturan3_revisi_laporan_kp_batas(aturan, hari_ini, sisa, status):
    hasil = hitung(aturan, "KP", "revisi_laporan", hari_ini, acuan=SEMINAR_KP)
    assert hasil["tenggat"] == TENGGAT_KP.isoformat()
    assert (hasil["sisa_hari"], hasil["status"]) == (sisa, status)
    assert hasil["sumber_dokumen"] == "Panduan Kerja Praktik ITK 2025"


# ── Aturan 4: Laporan magang, 2 minggu ───────────────────────────────────────

def test_aturan4_laporan_magang(aturan):
    hasil = hitung(aturan, "Magang", "laporan_magang", date(2026, 10, 25), acuan=date(2026, 10, 20))
    assert hasil["tenggat"] == "2026-11-03"
    assert hasil["sisa_hari"] == 9
    assert hasil["status"] == "belum_lewat"
    assert hasil["nama_tahapan"] == "Laporan magang"
    assert hasil["sumber_dokumen"] == "Panduan Magang Keprofesian ITK 2025"
    assert hasil["disclaimer"] == DISCLAIMER


def test_tanggal_hari_ini_default_wita(aturan):
    hasil = hitung_tenggat("KP", "revisi_laporan", "2026-10-20", aturan=aturan)
    assert hasil["status"] in {"belum_lewat", "hari_ini", "lewat"}


# ── Input tidak valid ────────────────────────────────────────────────────────

def test_kegiatan_tidak_dikenali(aturan):
    hasil = hitung_tenggat("Skripsi", "sidang", "2026-03-02", aturan=aturan)
    assert "tidak dikenali" in hasil["error"]
    assert set(hasil["kegiatan_valid"]) == {"TA", "KP", "Magang"}


def test_tahapan_tidak_dikenali_mengembalikan_daftar_valid(aturan):
    hasil = hitung_tenggat("TA", "yudisium", "2026-03-02", aturan=aturan)
    assert "tidak dikenali" in hasil["error"]
    assert [t["id_tahapan"] for t in hasil["tahapan_valid"]] == ["sidang_ta", "revisi_proposal"]


@pytest.mark.parametrize("tanggal", ["2026-13-45", "kemarin", "02/03/2026", ""])
def test_tanggal_tidak_valid_pesan_ramah(aturan, tanggal):
    hasil = hitung_tenggat("KP", "revisi_laporan", tanggal, "2026-10-20", aturan=aturan)
    assert "tidak valid" in hasil["error"]
    assert "TAHUN-BULAN-TANGGAL" in hasil["error"]


def test_tool_cek_tenggat_tanggal_salah_tidak_melempar_error():
    hasil = json.loads(cek_tenggat.invoke(
        {"kegiatan": "KP", "id_tahapan": "revisi_laporan", "tanggal_acuan": "20 Oktober"}
    ))
    assert "tidak valid" in hasil["error"]


def test_aturan_tidak_diubah_oleh_perhitungan(aturan):
    salinan = copy.deepcopy(aturan)
    hitung(aturan, "TA", "sidang_ta", ACUAN)
    assert aturan == salinan


def test_format_hasil_tenggat_aturan_rentang_dan_paling_lambat(aturan):
    from rag.tenggat import format_hasil_tenggat

    teks = format_hasil_tenggat([
        hitung(aturan, "TA", "sidang_ta", ACUAN + timedelta(weeks=20)),
        hitung(aturan, "Magang", "laporan_magang", date(2026, 11, 3), acuan=date(2026, 10, 20)),
    ])
    assert "Paling cepat: 2026-06-08" in teks and "Paling lambat: 2027-01-11" in teks
    assert "Status: dalam rentang" in teks
    assert "Tenggat: 2026-11-03" in teks and "Sisa hari: 0" in teks and "hari tenggat (belum lewat)" in teks
    assert teks.count(DISCLAIMER) == 1
