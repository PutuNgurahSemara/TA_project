"""
rag package — Retrieval-Augmented Generation module built with LangChain.
"""

from rag.pipeline import ingest_document, delete_document, query_rag
from rag.vectorstore import get_vectorstore, add_chunks
from rag.retriever import get_langchain_retriever, retrieve
from rag.generator import get_llm, get_rag_chain, generate_answer_stream, generate_answer
from rag.embedder import get_embeddings, embed_text, embed_batch
from rag.chunker import get_text_splitter, chunk_pages_to_documents, chunk_pages

__all__ = [
    "ingest_document",
    "delete_document",
    "query_rag",
    "get_vectorstore",
    "add_chunks",
    "get_langchain_retriever",
    "retrieve",
    "get_llm",
    "get_rag_chain",
    "generate_answer_stream",
    "generate_answer",
    "get_embeddings",
    "embed_text",
    "embed_batch",
    "get_text_splitter",
    "chunk_pages_to_documents",
    "chunk_pages",
]
