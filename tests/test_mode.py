"""Test mode retrieval: linier selalu retrieve; agentic menolak jawaban informasi tanpa tool."""

import json

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from rag import agent, pipeline
from rag.agent import jalankan_agen, terapkan_guard
from rag.generator import PENOLAKAN_STANDAR
from rag.tenggat import DISCLAIMER, hitung_tenggat


# ── Mode linier ──────────────────────────────────────────────────────────────

@pytest.fixture
def linier_palsu(monkeypatch):
    panggilan = []

    def retrieve_palsu(query, top_k=5, kategori=None):
        panggilan.append(query)
        return []

    monkeypatch.setattr(pipeline, "retrieve", retrieve_palsu)
    monkeypatch.setattr(pipeline, "generate_answer_stream", lambda q, c, riwayat=None: iter(["ok"]))
    return panggilan


@pytest.mark.parametrize("pertanyaan", ["Halo", "Apa syarat KP?", "Siapa presiden Indonesia?"])
def test_linier_selalu_memanggil_retrieval(linier_palsu, pertanyaan):
    hasil = pipeline.query_rag(pertanyaan, mode="linier")
    list(hasil["answer_stream"])
    assert linier_palsu == [pertanyaan]
    assert hasil["tool_dipanggil"] == ["retrieve_dokumen"]
    assert hasil["guard_aktif"] is False


# ── Mode agentic (agen dipalsukan, tanpa Ollama) ─────────────────────────────

class AgenPalsu:
    def __init__(self, balasan):
        self.balasan = balasan

    def invoke(self, masukan, config=None):
        return {"messages": masukan["messages"] + self.balasan}


def pasang_agen(monkeypatch, balasan):
    monkeypatch.setattr(agent, "create_agent", lambda **kw: AgenPalsu(balasan))


def test_agentic_menolak_jawaban_informasi_tanpa_tool(monkeypatch):
    pasang_agen(monkeypatch, [AIMessage(content="Sidang TA paling cepat 14 minggu setelah seminar proposal.")])
    hasil = jalankan_agen("Kapan paling cepat sidang TA?", llm=object())
    assert hasil["jawaban"] == PENOLAKAN_STANDAR
    assert hasil["guard_aktif"] is True
    assert hasil["tool_dipanggil"] == []


def test_agentic_meloloskan_jawaban_dengan_retrieve(monkeypatch):
    chunk = {"chunk_id": "doc__chunk_3", "nama_dokumen": "Panduan KP.pdf", "kategori": "KP",
             "halaman": 28, "kutipan": "Proposal KP memiliki struktur...", "jarak": 0.31, "peringkat": 1}
    pasang_agen(monkeypatch, [
        AIMessage(content="", tool_calls=[{"name": "retrieve_dokumen", "args": {"query": "struktur proposal KP", "kategori": "KP"}, "id": "t1"}]),
        ToolMessage(content=json.dumps({"hasil": [chunk]}), name="retrieve_dokumen", tool_call_id="t1"),
        AIMessage(content="Struktur proposal KP: cover, ... (Sumber: Panduan KP.pdf, hal. 28)"),
    ])
    hasil = jalankan_agen("Apa struktur proposal KP?", llm=object())
    assert hasil["guard_aktif"] is False
    assert hasil["jawaban"].startswith("Struktur proposal KP")
    assert hasil["tool_dipanggil"] == ["retrieve_dokumen"]
    assert hasil["hasil_retrieval"] == [{**chunk, "panggilan": 1}]


def test_query_rag_agentic_tidak_memanggil_retrieval_langsung(monkeypatch, linier_palsu):
    pasang_agen(monkeypatch, [AIMessage(content="Halo! Ada yang bisa saya bantu?")])
    monkeypatch.setattr(agent, "get_llm", lambda: object())
    hasil = pipeline.query_rag("Halo", mode="agentic")
    assert "".join(hasil["answer_stream"]) == "Halo! Ada yang bisa saya bantu?"
    assert linier_palsu == []
    assert hasil["mode"] == "agentic"


# ── Guard (fungsi murni) ─────────────────────────────────────────────────────

@pytest.mark.parametrize("jawaban", [
    "Halo! Ada yang bisa saya bantu terkait TA, KP, atau Magang?",
    "Selamat pagi, silakan ajukan pertanyaan Anda.",
    "Kapan tanggal seminar hasil KP Anda?",
])
def test_guard_meloloskan_sapaan_dan_klarifikasi(jawaban):
    assert terapkan_guard(jawaban, []) == (jawaban, False)


def test_guard_menormalkan_penolakan():
    assert terapkan_guard(f"Mohon maaf. {PENOLAKAN_STANDAR}", []) == (PENOLAKAN_STANDAR, False)


@pytest.mark.parametrize("jawaban", [
    "Revisi laporan KP paling lambat 3 minggu, bukan?",   # klarifikasi palsu berisi angka
    "Proposal TA terdiri atas cover, lembar pengesahan, kata pengantar, dan daftar isi.",
])
def test_guard_menolak_informasi_tanpa_tool(jawaban):
    assert terapkan_guard(jawaban, []) == (PENOLAKAN_STANDAR, True)


HASIL_KP = hitung_tenggat("KP", "revisi_laporan", "2026-10-20", "2026-11-21")  # tenggat 2026-11-10


def test_guard_hasil_tenggat_ditulis_kode_bukan_salinan_llm():
    # Regresi: qwen2.5:3b pernah menyalin tenggat 2026-11-10 sebagai "20 November 2026"
    jawaban, aktif = terapkan_guard(
        "Batas revisi laporan KP Anda adalah pada tanggal 20 November 2026.", ["cek_tenggat"], [HASIL_KP]
    )
    assert "20 November" not in jawaban
    assert "Tenggat: 2026-11-10" in jawaban and "Sisa hari: -11" in jawaban
    assert DISCLAIMER in jawaban and aktif is False


def test_guard_hasil_tenggat_menang_atas_teks_retrieve():
    jawaban, _ = terapkan_guard("Teks LLM dari dokumen.", ["retrieve_dokumen", "cek_tenggat"], [HASIL_KP])
    assert jawaban.startswith("**Revisi laporan KP**")


def test_guard_cek_tenggat_gagal_diperlakukan_tanpa_tool():
    gagal = [{"error": "Tanggal pada 'tanggal_acuan' tidak valid: ''."}]
    klarifikasi = "Kapan tanggal seminar hasil magang Anda?"
    assert terapkan_guard(klarifikasi, ["cek_tenggat"], gagal) == (klarifikasi, False)
    assert terapkan_guard("Laporan magang paling lambat 2 minggu.", ["cek_tenggat"], gagal) == (PENOLAKAN_STANDAR, True)


def test_agentic_merender_hasil_cek_tenggat(monkeypatch):
    pasang_agen(monkeypatch, [
        AIMessage(content="", tool_calls=[{"name": "cek_tenggat", "args": {"kegiatan": "KP"}, "id": "t1"}]),
        ToolMessage(content=json.dumps(HASIL_KP), name="cek_tenggat", tool_call_id="t1"),
        AIMessage(content="Batasnya 20 November 2026."),
    ])
    hasil = jalankan_agen("Seminar hasil KP 20 Oktober 2026, kapan batas revisi?", llm=object())
    assert "Tenggat: 2026-11-10" in hasil["jawaban"]
    assert hasil["tool_dipanggil"] == ["cek_tenggat"]
    assert hasil["guard_aktif"] is False


def test_agentic_cek_tenggat_error_validasi_lalu_klarifikasi(monkeypatch):
    # ToolNode membalas teks error (bukan JSON) bila argumen wajib tidak diisi LLM
    pasang_agen(monkeypatch, [
        AIMessage(content="", tool_calls=[{"name": "cek_tenggat", "args": {"kegiatan": "Magang"}, "id": "t1"}]),
        ToolMessage(content="Error invoking tool 'cek_tenggat': field required", name="cek_tenggat", tool_call_id="t1"),
        AIMessage(content="Kapan tanggal seminar hasil magang Anda?"),
    ])
    hasil = jalankan_agen("Kapan batas laporan magang saya?", llm=object())
    assert hasil["jawaban"] == "Kapan tanggal seminar hasil magang Anda?"
    assert DISCLAIMER not in hasil["jawaban"]
