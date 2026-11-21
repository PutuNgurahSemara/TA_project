"""
tenggat.py — Perhitungan tenggat kegiatan akademik (TA, KP, Magang) secara deterministik.

Ketentuan dibaca dari aturan_tenggat.json di root proyek, sehingga bila pedoman direvisi
pengembang cukup memperbarui file tersebut tanpa mengubah kode. Perhitungan TIDAK memakai
kalender akademik.

Aturan penghitungan:
  - tenggat = tanggal acuan + durasi; tanggal acuan sendiri tidak ikut dihitung.
  - Hari tenggat itu sendiri masih dianggap BELUM lewat.
  - Satuan "hari" dan "minggu" dihitung sebagai hari kalender (hari libur tidak dilewati).
  - Satuan "hari_kerja" hanya menghitung Senin–Jumat dan melewati tanggal di `hari_libur`.
    Jika daftar `hari_libur` kosong, hasilnya bisa LEBIH AWAL dari tenggat sebenarnya.
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional
from zoneinfo import ZoneInfo

from config import BASE_DIR

BERKAS_ATURAN = Path(BASE_DIR) / "aturan_tenggat.json"
ZONA_WAKTU = ZoneInfo("Asia/Makassar")
DISCLAIMER = (
    "Hasil ini merupakan pemeriksaan mandiri berdasarkan pedoman, "
    "bukan keputusan resmi program studi."
)


_LABEL_STATUS = {
    "belum_lewat": "belum lewat",
    "hari_ini": "hari ini adalah hari tenggat (belum lewat)",
    "lewat": "sudah lewat",
    "belum_bisa": "belum bisa (sebelum batas paling cepat)",
    "dalam_rentang": "dalam rentang yang diperbolehkan",
}


def muat_aturan(path: Path = BERKAS_ATURAN) -> dict[str, Any]:
    """Baca file aturan tenggat (dibaca ulang setiap panggilan agar revisi langsung berlaku)."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _ke_tanggal(nilai: date | str | None, nama_field: str) -> date:
    """Ubah string ISO (YYYY-MM-DD) menjadi date; lempar ValueError dengan pesan ramah."""
    if isinstance(nilai, date):
        return nilai
    try:
        return date.fromisoformat(str(nilai).strip())
    except (ValueError, TypeError):
        raise ValueError(
            f"Tanggal pada '{nama_field}' tidak valid: '{nilai}'. "
            f"Gunakan format TAHUN-BULAN-TANGGAL, contoh 2026-03-02."
        )


def tambah_durasi(acuan: date, jumlah: int, satuan: str, hari_libur: set[date]) -> date:
    """Hitung tanggal acuan + durasi sesuai satuan ("hari", "hari_kerja", "minggu")."""
    if satuan == "hari":
        return acuan + timedelta(days=jumlah)
    if satuan == "minggu":
        return acuan + timedelta(weeks=jumlah)
    if satuan == "hari_kerja":
        tanggal, terhitung = acuan, 0
        while terhitung < jumlah:
            tanggal += timedelta(days=1)
            if tanggal.weekday() < 5 and tanggal not in hari_libur:  # 0–4 = Senin–Jumat
                terhitung += 1
        return tanggal
    raise ValueError(f"Satuan durasi tidak dikenal di aturan_tenggat.json: '{satuan}'.")


def daftar_tahapan(aturan: dict[str, Any], kegiatan: str) -> list[dict[str, str]]:
    """Daftar tahapan valid untuk satu kegiatan beserta tanggal acuannya."""
    return [
        {"id_tahapan": id_t, "nama_tahapan": t["nama"], "acuan": t["acuan"]}
        for id_t, t in aturan["kegiatan"].get(kegiatan, {}).items()
    ]


def hitung_tenggat(
    kegiatan: str,
    id_tahapan: str,
    tanggal_acuan: date | str,
    tanggal_hari_ini: Optional[date | str] = None,
    aturan: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Hitung tenggat satu tahapan kegiatan.

    tenggat = tanggal acuan + durasi; hari tenggat itu sendiri masih dianggap belum lewat.
    Jika `tanggal_hari_ini` kosong, dipakai tanggal hari ini zona Asia/Makassar (WITA).
    Jika daftar hari libur kosong, tenggat hari kerja bisa lebih awal dari tenggat sebenarnya.

    Returns:
        Aturan paling lambat: tenggat, sisa_hari, status ("belum_lewat" | "hari_ini" | "lewat").
        Aturan rentang: paling_cepat, paling_lambat, status ("belum_bisa" | "dalam_rentang" | "lewat").
        Selalu menyertakan sumber_dokumen dan disclaimer.
        Jika input tidak valid: {"error": ..., (opsional) "tahapan_valid"/"kegiatan_valid": ...}.
    """
    aturan = aturan if aturan is not None else muat_aturan()
    semua_kegiatan = aturan["kegiatan"]

    if kegiatan not in semua_kegiatan:
        return {
            "error": f"Kegiatan '{kegiatan}' tidak dikenali.",
            "kegiatan_valid": {k: daftar_tahapan(aturan, k) for k in semua_kegiatan},
        }
    tahapan = semua_kegiatan[kegiatan].get(id_tahapan)
    if tahapan is None:
        return {
            "error": f"Tahapan '{id_tahapan}' tidak dikenali untuk kegiatan {kegiatan}.",
            "tahapan_valid": daftar_tahapan(aturan, kegiatan),
        }

    try:
        acuan = _ke_tanggal(tanggal_acuan, "tanggal_acuan")
        hari_ini = (
            datetime.now(ZONA_WAKTU).date()
            if tanggal_hari_ini in (None, "")
            else _ke_tanggal(tanggal_hari_ini, "tanggal_hari_ini")
        )
        libur = {_ke_tanggal(t, "hari_libur") for t in aturan.get("hari_libur", [])}
    except ValueError as e:
        return {"error": str(e)}

    def _batas(kunci: str) -> date:
        return tambah_durasi(acuan, tahapan[kunci]["jumlah"], tahapan[kunci]["satuan"], libur)

    hasil: dict[str, Any] = {
        "kegiatan": kegiatan,
        "nama_tahapan": tahapan["nama"],
        "tanggal_acuan": acuan.isoformat(),
    }

    paling_lambat = _batas("paling_lambat")
    if "paling_cepat" in tahapan:
        paling_cepat = _batas("paling_cepat")
        if hari_ini < paling_cepat:
            status = "belum_bisa"
        elif hari_ini <= paling_lambat:
            status = "dalam_rentang"
        else:
            status = "lewat"
        hasil.update(
            paling_cepat=paling_cepat.isoformat(),
            paling_lambat=paling_lambat.isoformat(),
            status=status,
        )
    else:
        sisa = (paling_lambat - hari_ini).days
        hasil.update(
            tenggat=paling_lambat.isoformat(),
            sisa_hari=sisa,
            status="belum_lewat" if sisa > 0 else ("hari_ini" if sisa == 0 else "lewat"),
        )

    hasil.update(sumber_dokumen=tahapan["sumber"], disclaimer=DISCLAIMER)
    return hasil


def format_hasil_tenggat(daftar_hasil: list[dict[str, Any]]) -> str:
    """
    Susun teks jawaban dari hasil hitung_tenggat() yang berhasil (tanpa "error").
    Dipakai agar tanggal dan status ditampilkan apa adanya oleh kode, bukan disalin ulang LLM.
    Disclaimer ditulis sekali di akhir.
    """
    bagian = []
    for h in daftar_hasil:
        baris = [f"**{h['nama_tahapan']}** ({h['kegiatan']})", f"- Tanggal acuan: {h['tanggal_acuan']}"]
        if "paling_cepat" in h:
            baris += [f"- Paling cepat: {h['paling_cepat']}", f"- Paling lambat: {h['paling_lambat']}"]
        else:
            baris += [f"- Tenggat: {h['tenggat']}", f"- Sisa hari: {h['sisa_hari']}"]
        baris += [
            f"- Status: {_LABEL_STATUS.get(h['status'], h['status'])}",
            f"- Sumber: {h['sumber_dokumen']}",
        ]
        bagian.append("\n".join(baris))
    return "\n\n".join(bagian) + f"\n\n_{DISCLAIMER}_"
