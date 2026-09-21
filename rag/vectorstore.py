"""
vectorstore.py — Interface ke ChromaDB persistent menggunakan LangChain Chroma VectorStore.

Collection: "rag_documents"
Distance metric: cosine (hnsw:space: cosine)
"""

from typing import Any, Optional
from langchain_chroma import Chroma
from langchain_core.documents import Document
from config import CHROMA_DIR
from rag.embedder import get_embeddings

COLLECTION_NAME = "rag_documents"

_vectorstore: Optional[Chroma] = None


def get_vectorstore() -> Chroma:
    """
    Ambil atau buat singleton LangChain Chroma VectorStore.
    """
    global _vectorstore
    if _vectorstore is None:
        embeddings = get_embeddings()
        _vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=CHROMA_DIR,
            collection_metadata={"hnsw:space": "cosine"},
        )
    return _vectorstore


def get_collection():
    """
    Ambil underlying ChromaDB collection (untuk backward-compatibility).
    """
    vs = get_vectorstore()
    return vs._collection


def reset_collection_cache() -> None:
    """Reset singleton agar vectorstore di-reload."""
    global _vectorstore
    _vectorstore = None


def add_documents(documents: list[Document], ids: Optional[list[str]] = None) -> list[str]:
    """
    Menyimpan list of LangChain Document objects ke ChromaDB.
    """
    vs = get_vectorstore()
    return vs.add_documents(documents, ids=ids)


def add_chunks(
    doc_id: str,
    chunks: list[dict[str, Any]],
    embeddings: Optional[list[list[float]]] = None,
) -> None:
    """
    Simpan chunks ke ChromaDB (backward compatible).
    Mengonversi chunks ke Document objects LangChain dan menyimpannya.

    Args:
        doc_id:     ID unik dokumen (UUID)
        chunks:     List of {text, page_num, source, chunk_index}
        embeddings: Optional, dihitung otomatis oleh LangChain embedding function jika None
    """
    vs = get_vectorstore()

    ids = [f"{doc_id}__chunk_{i}" for i in range(len(chunks))]
    documents = [
        Document(
            page_content=c["text"],
            metadata={
                "doc_id":      doc_id,
                "source":      str(c.get("source", "")),
                "page_num":    int(c.get("page_num", 1)),
                "chunk_index": int(c.get("chunk_index", i)),
            },
        )
        for i, c in enumerate(chunks)
    ]

    # Jika embeddings sudah diberikan, kita bisa menggunakan collection langsung atau add_documents
    if embeddings is not None and len(embeddings) == len(chunks):
        collection = get_collection()
        collection.add(
            ids=ids,
            documents=[d.page_content for d in documents],
            embeddings=embeddings,
            metadatas=[d.metadata for d in documents],
        )
    else:
        vs.add_documents(documents=documents, ids=ids)


def delete_document(doc_id: str) -> int:
    """
    Hapus semua chunk terkait doc_id dari ChromaDB.

    Returns:
        Jumlah chunk yang dihapus
    """
    vs = get_vectorstore()
    results = vs.get(where={"doc_id": doc_id})
    ids_to_delete = results.get("ids", [])
    if ids_to_delete:
        vs.delete(ids=ids_to_delete)
    return len(ids_to_delete)


def query(
    query_embedding: list[float],
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Similarity search via vector embedding langsung (backward-compatible).
    """
    collection = get_collection()
    return collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )


def similarity_search(
    query_text: str,
    top_k: int = 5,
) -> list[tuple[Document, float]]:
    """
    Similarity search menggunakan LangChain Chroma (mengembalikan tuple (Document, distance)).
    """
    vs = get_vectorstore()
    return vs.similarity_search_with_score(query_text, k=top_k)
