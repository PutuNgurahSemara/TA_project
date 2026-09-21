"""
view_parsed.py — Script pembantu untuk melihat hasil parsing teks & tabel dokumen secara langsung.
Jalankan: python view_parsed.py
"""

import glob
import os
from rag.parser import parse_document

DOCS_DIR = os.path.join(os.path.dirname(__file__), "uploaded_docs")
files = glob.glob(os.path.join(DOCS_DIR, "*.*"))

if not files:
    print(f"❌ Tidak ada file dokumen di folder '{DOCS_DIR}'.")
    exit(0)

print("=" * 65)
print("📄 DAFTAR DOKUMEN YANG ADA DI SISTEM:")
print("=" * 65)
for idx, f in enumerate(files, 1):
    print(f"[{idx}] {os.path.basename(f)}")
print("=" * 65)

try:
    pilihan = input("\nPilih nomor dokumen yang ingin dilihat (misal: 1): ").strip()
    idx_pilih = int(pilihan) - 1
    selected_file = files[idx_pilih]
except (ValueError, IndexError):
    print("Pilihan default: membuka dokumen pertama...")
    selected_file = files[2]

print(f"\n🔍 Mem-parsing file: {os.path.basename(selected_file)} ...\n")
pages = parse_document(selected_file)

print(f"✅ Total halaman: {len(pages)}\n")

try:
    hal_input = input(f"Ingin lihat halaman berapa? (1 - {len(pages)}, default 1): ").strip()
    hal_idx = int(hal_input) - 1
    if hal_idx < 0 or hal_idx >= len(pages):
        hal_idx = 0
except ValueError:
    hal_idx = 0

print("\n" + "=" * 65)
print(f"📖 HASIL PARSING HALAMAN {hal_idx + 1}:")
print("=" * 65)
print(pages[hal_idx]["text"])
print("=" * 65)
