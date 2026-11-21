"""
uji_pemilihan_tool.py — Cek apakah LLM memilih tool yang tepat pada mode agentic.

BUTUH OLLAMA (model LLM + bge-m3) dan ChromaDB berisi dokumen. Tidak ikut pytest default
karena berada di folder scripts/, bukan tests/.

Jalankan dari root proyek:
    python scripts/uji_pemilihan_tool.py                     # default qwen3.5:9b
    python scripts/uji_pemilihan_tool.py --model qwen2.5:3b

Hasil dicetak ke layar dan disimpan ke scripts/hasil_uji_tool_<model>.json.
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

import requests  # noqa: E402
from langchain_ollama import ChatOllama  # noqa: E402

import config  # noqa: E402
from rag.agent import jalankan_agen  # noqa: E402

# (pertanyaan, tool yang diharapkan atau None = tanpa tool, kategori retrieve yang diharapkan)
# Metrik "longgar": tool yang diharapkan ikut dipanggil (None: tidak ada tool sama sekali).
# Metrik "ketat"  : daftar tool yang dipanggil persis [tool yang diharapkan] (None: []).
KASUS = [
    ("Apa saja syarat untuk mendaftar kerja praktik?", "retrieve_dokumen", "KP"),
    ("Bagaimana struktur proposal tugas akhir?", "retrieve_dokumen", "TA"),
    ("Bagaimana prosedur pendaftaran magang keprofesian?", "retrieve_dokumen", "Magang"),
    ("Apa saja komponen penilaian kerja praktik?", "retrieve_dokumen", "KP"),
    ("Seminar proposal TA saya tanggal 2026-03-02. Kapan paling cepat saya boleh sidang TA?", "cek_tenggat", None),
    ("Seminar hasil KP saya tanggal 20 Oktober 2026, kapan batas revisi laporan KP?", "cek_tenggat", None),
    ("Saya seminar proposal tanggal 5 Januari 2026, kapan batas revisi proposal saya?", "cek_tenggat", None),
    ("Kapan batas pengumpulan laporan magang saya?", None, None),  # harus menanyakan tanggal
    ("Halo, selamat pagi!", None, None),
    ("Siapa presiden Indonesia saat ini?", None, None),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Uji pemilihan tool mode agentic (butuh Ollama).")
    parser.add_argument("--model", default="qwen3.5:9b")
    args = parser.parse_args()

    try:
        requests.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=3).raise_for_status()
    except requests.RequestException:
        sys.exit(f"Ollama tidak dapat dihubungi di {config.OLLAMA_BASE_URL}. Jalankan Ollama terlebih dahulu.")

    llm = ChatOllama(base_url=config.OLLAMA_BASE_URL, model=args.model, reasoning=False, temperature=0)
    hasil_semua, tepat_longgar, tepat_ketat, tepat_kategori, jumlah_kategori = [], 0, 0, 0, 0

    for no, (pertanyaan, tool_harap, kategori_harap) in enumerate(KASUS, 1):
        mulai = time.perf_counter()
        hasil = jalankan_agen(pertanyaan, llm=llm)
        latensi = round((time.perf_counter() - mulai) * 1000)

        dipanggil = hasil["tool_dipanggil"]
        benar = (tool_harap in dipanggil) if tool_harap else not dipanggil
        ketat = dipanggil == ([tool_harap] if tool_harap else [])
        tepat_longgar += benar
        tepat_ketat += ketat

        kategori_ok = None
        if kategori_harap:
            jumlah_kategori += 1
            argumen = next((a["argumen"] for a in hasil["argumen_tool"] if a["nama"] == "retrieve_dokumen"), {})
            kategori_ok = argumen.get("kategori") == kategori_harap
            tepat_kategori += kategori_ok

        print(f"\n[{no}] {pertanyaan}")
        print(f"    diharapkan: {tool_harap or '(tanpa tool)'} | dipanggil: {hasil['tool_dipanggil'] or '(tanpa tool)'} "
              f"| {'BENAR' if benar else 'SALAH'}{' (ada tool tambahan)' if benar and not ketat else ''}"
              + (f" | kategori {'BENAR' if kategori_ok else 'SALAH'}" if kategori_ok is not None else "")
              + f" | guard={hasil['guard_aktif']} | {latensi} ms")
        print(f"    argumen: {hasil['argumen_tool']}")
        print(f"    jawaban: {hasil['jawaban'][:300]!r}")

        hasil_semua.append({
            "no": no, "pertanyaan": pertanyaan, "tool_diharapkan": tool_harap,
            "tool_dipanggil": hasil["tool_dipanggil"], "argumen_tool": hasil["argumen_tool"],
            "tool_benar": benar, "tool_benar_ketat": ketat, "kategori_benar": kategori_ok, "guard_aktif": hasil["guard_aktif"],
            "latensi_ms": latensi, "jawaban": hasil["jawaban"],
        })

    ringkasan = {
        "model": args.model,
        "ketepatan_tool_longgar": f"{tepat_longgar}/{len(KASUS)}",
        "ketepatan_tool_ketat": f"{tepat_ketat}/{len(KASUS)}",
        "ketepatan_kategori": f"{tepat_kategori}/{jumlah_kategori}",
        "rata_latensi_ms": round(sum(h["latensi_ms"] for h in hasil_semua) / len(hasil_semua)),
    }
    print("\n=== RINGKASAN ===", json.dumps(ringkasan, ensure_ascii=False))

    berkas = Path(__file__).parent / f"hasil_uji_tool_{args.model.replace(':', '_')}.json"
    berkas.write_text(json.dumps({"ringkasan": ringkasan, "hasil": hasil_semua}, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(f"Hasil disimpan ke {berkas}")


if __name__ == "__main__":
    main()
