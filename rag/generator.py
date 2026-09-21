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
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config import OLLAMA_BASE_URL, LLM_MODEL

# ── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Kamu adalah asisten AI yang membantu menjawab pertanyaan berdasarkan dokumen internal.

ATURAN WAJIB:
1. Jawab HANYA berdasarkan informasi yang ada dalam konteks dokumen di bawah.
2. Jika informasi tidak ditemukan dalam konteks, katakan dengan jelas:
   "Maaf, informasi tersebut tidak ditemukan dalam dokumen yang tersedia."
3. JANGAN mengarang, menambah, atau mengasumsikan informasi di luar konteks.
4. Jawab dalam Bahasa Indonesia yang jelas, ringkas, dan profesional.
5. Jika menyebutkan daftar jenis, kategori, klasifikasi, atau poin-poin, SELALU gunakan format bullet list markdown (- ...) atau nomor (1., 2., ...) secara konsisten untuk setiap item agar terstruktur rapi.
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
        return "Tidak ada dokumen yang tersedia dalam basis data."

    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[Dokumen {i} | File: {chunk.get('source', 'Unknown')} | Hal. {chunk.get('page_num', 1)}]\n"
            f"{chunk.get('text', '')}"
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


def generate_answer_stream(
    question: str,
    chunks: list[dict[str, Any]],
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
