"""
migrasi_kategori.py — Skrip sekali jalan untuk chunk yang diindeks sebelum fitur kategori ada.

Untuk setiap dokumen di tabel `documents` (SQLite):
  - menambahkan metadata `kategori` (TA/KP/Magang/Umum) yang ditebak dari nama dokumen;
  - merapikan metadata `source` menjadi nama dokumen asli (tanpa awalan UUID).
Embedding tidak dihitung ulang. Aman dijalankan berulang kali.

Jalankan dari root proyek (backup folder chroma_db terlebih dahulu):
    python scripts/migrasi_kategori.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.database import get_all_documents  # noqa: E402
from rag.pipeline import tebak_kategori  # noqa: E402
from rag.vectorstore import get_collection  # noqa: E402


def main() -> None:
    koleksi = get_collection()
    for doc in get_all_documents():
        kategori = tebak_kategori(doc["name"])
        data = koleksi.get(where={"doc_id": doc["id"]}, include=["metadatas"])
        if not data["ids"]:
            print(f"[-] {doc['name']}: tidak ada chunk di ChromaDB, dilewati.")
            continue
        metadata_baru = [{**m, "kategori": kategori, "source": doc["name"]} for m in data["metadatas"]]
        koleksi.update(ids=data["ids"], metadatas=metadata_baru)
        print(f"[+] {doc['name']}: {len(data['ids'])} chunk → kategori '{kategori}'.")


if __name__ == "__main__":
    main()
