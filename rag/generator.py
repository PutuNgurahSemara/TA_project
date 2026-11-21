"""
generator.py — Membangun prompt dan memanggil LLM Ollama menggunakan LangChain ChatOllama
untuk menghasilkan jawaban berbasis konteks RAG.

Mendukung:
- ChatOllama dari library resmi langchain_ollama
- LCEL pipeline standar (ChatPromptTemplate | ChatOllama | StrOutputParser)
- Generator streaming token real-time
"""

from typing import Any, Generator, Optional
from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config import OLLAMA_BASE_URL, LLM_MODEL

# ── System Prompt ─────────────────────────────────────────────────────────────
PENOLAKAN_STANDAR = (
    "Maaf, saya hanya dapat menjawab pertanyaan seputar Tugas Akhir, Kerja Praktik, "
    "dan Magang berdasarkan dokumen pedoman yang tersedia."
)
TIDAK_DITEMUKAN = "Maaf, informasi tersebut tidak ditemukan dalam dokumen yang tersedia."

SYSTEM_PROMPT = f"""Kamu adalah asisten AI yang menjawab pertanyaan mahasiswa tentang Tugas Akhir (TA), Kerja Praktik (KP), dan Magang berdasarkan dokumen pedoman.

ATURAN WAJIB:
1. Jawab HANYA berdasarkan informasi yang ada dalam konteks dokumen yang diberikan.
2. Jika informasi tidak ditemukan dalam konteks, jawab persis: "{TIDAK_DITEMUKAN}"
3. Jika pertanyaan di luar cakupan TA, KP, dan Magang, jawab persis: "{PENOLAKAN_STANDAR}"
4. JANGAN mengarang, menambah, atau mengasumsikan informasi di luar konteks.
5. Sertakan nama dokumen dan kutipan singkat sumber pada jawaban, contoh: (Sumber: <nama dokumen>, hal. <n>: "<kutipan>").
6. Jawab dalam Bahasa Indonesia yang jelas, ringkas, dan profesional.
7. Jika menyebutkan daftar jenis, kategori, klasifikasi, atau poin-poin, SELALU gunakan format bullet list markdown (- ...) atau nomor (1., 2., ...) secara konsisten untuk setiap item agar terstruktur rapi.
"""

_llm: Optional[ChatOllama] = None


def get_llm() -> ChatOllama:
    """
    Inisialisasi singleton ChatOllama dari LangChain.
    """
    global _llm
    if _llm is None:
        _llm = ChatOllama(
            base_url=OLLAMA_BASE_URL,
            model=LLM_MODEL,
            reasoning=False,
            temperature=0.1,
            top_p=0.9,
            num_predict=2048,
        )
    return _llm


def format_chunks_context(chunks: list[dict[str, Any]]) -> str:
    """
    Format list chunk menjadi string konteks terstruktur.
    """
    if not chunks:
        return "Tidak ada potongan dokumen yang relevan (tidak ditemukan di dokumen)."

    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[Dokumen {i} | File: {chunk.get('nama_dokumen', 'Unknown')} | Hal. {chunk.get('halaman') or '-'}]\n"
            f"{chunk.get('kutipan', '')}"
        )
    return "\n\n---\n\n".join(parts)


def build_prompt(question: str, chunks: list[dict[str, Any]]) -> str:
    """
    Susun user prompt RAG dengan konteks chunk dan pertanyaan user.
    """
    context_text = format_chunks_context(chunks)
    return (
        f"KONTEKS DOKUMEN:\n"
        f"{'='*60}\n"
        f"{context_text}\n"
        f"{'='*60}\n\n"
        f"PERTANYAAN: {question}\n\n"
        f"Langsung berikan jawaban berdasarkan konteks dokumen di atas secara jelas dan terstruktur:"
    )


def get_rag_chain():
    """
    Menyediakan chain LCEL standar (LangChain Expression Language)
    untuk kebutuhan pengembang berikutnya / integrasi aplikasi besar.
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "KONTEKS DOKUMEN:\n============================================================\n{context}\n============================================================\n\nPERTANYAAN: {question}\n\nLangsung berikan jawaban berdasarkan konteks dokumen di atas secara jelas dan terstruktur:"),
    ])
    llm = get_llm()
    return prompt | llm | StrOutputParser()


def riwayat_ke_messages(riwayat: Optional[list[dict[str, str]]]) -> list:
    """Ubah riwayat sesi [{peran: "user"|"asisten", isi}] menjadi pesan LangChain."""
    return [
        HumanMessage(content=r["isi"]) if r["peran"] == "user" else AIMessage(content=r["isi"])
        for r in (riwayat or [])
    ]


def generate_answer_stream(
    question: str,
    chunks: list[dict[str, Any]],
    riwayat: Optional[list[dict[str, str]]] = None,
) -> Generator[str, None, None]:
    """
    Panggil LLM Ollama via LangChain secara streaming, yield token jawaban satu per satu.

    Yields:
        Token/kata jawaban secara real-time
    """
    llm = get_llm()
    user_content = build_prompt(question, chunks)
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        *riwayat_ke_messages(riwayat),
        HumanMessage(content=user_content),
    ]

    try:
        for chunk in llm.stream(messages):
            token = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
            if token:
                yield token
    except Exception as e:
        err_msg = str(e)
        if "Connection" in err_msg or "Failed to establish" in err_msg:
            yield "\n\n❌ **Error**: Tidak bisa terhubung ke Ollama. Pastikan Ollama sedang berjalan."
        else:
            yield f"\n\n❌ **Error**: {err_msg}"


def generate_answer(question: str, chunks: list[dict[str, Any]]) -> str:
    """Generate jawaban lengkap (non-streaming). Berguna untuk testing."""
    return "".join(generate_answer_stream(question, chunks))
