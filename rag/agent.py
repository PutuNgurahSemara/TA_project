"""
agent.py — Mode agentic: LLM memilih tool (retrieve_dokumen, cek_tenggat) lewat
langchain.agents.create_agent, lalu jawabannya diperiksa oleh guard deterministik.

Aturan guard (berlaku hanya di mode agentic):
  - cek_tenggat berhasil (hasil tanpa "error") → jawaban LLM DIGANTI teks hasil tenggat yang
                                                 disusun kode (format_hasil_tenggat), agar tanggal
                                                 tidak salah disalin ulang oleh LLM.
  - Ada panggilan retrieve_dokumen          → jawaban diloloskan.
  - Tidak ada tool yang berhasil dipakai     → hanya boleh berupa:
        * penolakan  : mengandung PENOLAKAN_STANDAR,
        * klarifikasi: ≤ 250 karakter, mengandung "?", dan tanpa angka
                       (isi pedoman hampir selalu memuat angka: minggu, SKS, halaman),
        * sapaan     : ≤ 150 karakter dan mengandung kata sapaan.
    Selain itu jawaban diganti PENOLAKAN_STANDAR (guard_aktif = True).
"""

import json
import re
from typing import Any, Optional

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from rag.generator import PENOLAKAN_STANDAR, TIDAK_DITEMUKAN, get_llm, riwayat_ke_messages
from rag.tenggat import format_hasil_tenggat
from rag.tools import SEMUA_TOOL

BATAS_LANGKAH = 12  # recursion_limit LangGraph, mencegah agen berputar tanpa henti
MAKS_KLARIFIKASI = 250
MAKS_SAPAAN = 150
_POLA_SAPAAN = re.compile(
    r"\b(halo|hai|hi|hello|selamat (pagi|siang|sore|malam)|terima kasih|sama-sama|salam)\b",
    re.IGNORECASE,
)

SYSTEM_PROMPT_AGEN = f"""Kamu adalah asisten AI untuk mahasiswa tentang Tugas Akhir (TA), Kerja Praktik (KP), dan Magang.

TOOL:
- retrieve_dokumen: WAJIB dipanggil untuk setiap pertanyaan informasi tentang TA, KP, atau Magang. Isi kategori bila jelas.
- cek_tenggat: dipanggil untuk menghitung tenggat bila mahasiswa sudah menyebutkan tanggal acuannya.

ATURAN WAJIB:
1. Jawab HANYA berdasarkan hasil retrieve_dokumen dan hasil cek_tenggat. Jangan memakai pengetahuanmu sendiri.
2. Jika hasil retrieve_dokumen kosong, jawab persis: "{TIDAK_DITEMUKAN}"
3. Pertanyaan di luar cakupan TA, KP, dan Magang ditolak dengan sopan, jawab persis: "{PENOLAKAN_STANDAR}"
4. Pada jawaban dari dokumen, sertakan nama dokumen dan kutipan singkat sumbernya, contoh: (Sumber: <nama dokumen>, hal. <n>: "<kutipan>").
5. Tampilkan hasil cek_tenggat apa adanya (tanggal, sisa hari, status, sumber) beserta disclaimer-nya. JANGAN menghitung ulang tanggal.
6. Jika mahasiswa menanyakan tenggat tetapi belum menyebutkan tanggal acuan, tanyakan tanggalnya dalam satu kalimat pertanyaan singkat tanpa contoh angka. Jangan menebak tanggal.
7. Tanpa memanggil tool, kamu HANYA boleh: membalas sapaan secara singkat, mengajukan pertanyaan klarifikasi, atau menolak dengan teks pada aturan 3.
8. Jawab dalam Bahasa Indonesia yang jelas, ringkas, dan profesional.
"""


def terapkan_guard(
    jawaban: str,
    tool_dipanggil: list[str],
    hasil_tenggat: Optional[list[dict[str, Any]]] = None,
) -> tuple[str, bool]:
    """
    Tegakkan aturan "mode agentic tidak boleh menjawab informasi tanpa tool".

    Args:
        hasil_tenggat: hasil semua panggilan cek_tenggat (dict dari hitung_tenggat).

    Returns:
        (jawaban_final, guard_aktif) — guard_aktif True jika jawaban diganti penolakan standar.
    """
    teks = (jawaban or "").strip()

    tenggat_berhasil = [h for h in (hasil_tenggat or []) if "error" not in h]
    if tenggat_berhasil:
        return format_hasil_tenggat(tenggat_berhasil), False
    if "retrieve_dokumen" in tool_dipanggil:
        return teks, False
    # cek_tenggat yang gagal (mis. tanggal belum disebut) diperlakukan seperti tanpa tool

    if PENOLAKAN_STANDAR in teks:
        return PENOLAKAN_STANDAR, False
    if len(teks) <= MAKS_KLARIFIKASI and "?" in teks and not re.search(r"\d", teks):
        return teks, False
    if len(teks) <= MAKS_SAPAAN and _POLA_SAPAAN.search(teks):
        return teks, False
    return PENOLAKAN_STANDAR, True


def jalankan_agen(
    pertanyaan: str,
    riwayat: Optional[list[dict[str, str]]] = None,
    llm: Optional[BaseChatModel] = None,
) -> dict[str, Any]:
    """
    Jalankan agen sampai selesai, lalu terapkan guard.

    Returns:
        {
          "jawaban":         str  — jawaban final setelah guard,
          "tool_dipanggil":  list[str] — nama tool sesuai urutan pemanggilan,
          "argumen_tool":    list[{nama, argumen}] — HANYA untuk skrip uji, jangan dicatat ke log,
          "hasil_retrieval": list[dict] — hasil semua panggilan retrieve_dokumen (+ field "panggilan"),
          "guard_aktif":     bool,
        }
    """
    agen = create_agent(model=llm or get_llm(), tools=SEMUA_TOOL, system_prompt=SYSTEM_PROMPT_AGEN)
    masukan = [*riwayat_ke_messages(riwayat), HumanMessage(content=pertanyaan)]
    state = agen.invoke({"messages": masukan}, config={"recursion_limit": BATAS_LANGKAH})
    keluaran = state["messages"][len(masukan):]

    tool_dipanggil: list[str] = []
    argumen_tool: list[dict[str, Any]] = []
    hasil_retrieval: list[dict[str, Any]] = []
    hasil_tenggat: list[dict[str, Any]] = []
    panggilan_retrieve = 0
    for pesan in keluaran:
        if isinstance(pesan, AIMessage):
            for tc in pesan.tool_calls:
                tool_dipanggil.append(tc["name"])
                argumen_tool.append({"nama": tc["name"], "argumen": tc["args"]})
        elif isinstance(pesan, ToolMessage) and pesan.name == "retrieve_dokumen":
            panggilan_retrieve += 1
            try:
                hasil = json.loads(pesan.text).get("hasil", [])
            except (ValueError, AttributeError):
                hasil = []  # mis. pesan error validasi argumen dari ToolNode
            hasil_retrieval.extend({**h, "panggilan": panggilan_retrieve} for h in hasil)
        elif isinstance(pesan, ToolMessage) and pesan.name == "cek_tenggat":
            try:
                hasil_tenggat.append(json.loads(pesan.text))
            except ValueError:
                pass  # error validasi argumen dari ToolNode (bukan JSON) = tool gagal

    jawaban_mentah = keluaran[-1].text if keluaran else ""
    jawaban, guard_aktif = terapkan_guard(jawaban_mentah, tool_dipanggil, hasil_tenggat)
    return {
        "jawaban": jawaban,
        "tool_dipanggil": tool_dipanggil,
        "argumen_tool": argumen_tool,
        "hasil_retrieval": hasil_retrieval,
        "guard_aktif": guard_aktif,
    }
