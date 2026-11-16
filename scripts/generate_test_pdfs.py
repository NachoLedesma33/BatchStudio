"""Generate small test PDFs for benchmarks.

Usage:
    python scripts/generate_test_pdfs.py --count 100 --out C:/temp/pdfs100
"""
from __future__ import annotations

import argparse
import random
from pathlib import Path

import pymupdf


def generate(count: int, out_dir: Path, pages_per_doc: int = 1) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        doc = pymupdf.open()
        for p in range(pages_per_doc):
            page = doc.new_page()
            page.insert_text((72, 72), f"Documento de prueba {i} - pagina {p + 1}")
            # add a small image-like rectangle
            page.draw_rect(pymupdf.Rect(100, 100, 200, 200), color=(0.2, 0.4, 0.8))
        name = f"doc_{i:05d}.pdf"
        doc.save(out_dir / name)
        doc.close()
    print(f"Generados {count} PDF en {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--out", type=str, required=True)
    parser.add_argument("--pages", type=int, default=1)
    args = parser.parse_args()
    generate(args.count, Path(args.out), args.pages)


if __name__ == "__main__":
    main()
