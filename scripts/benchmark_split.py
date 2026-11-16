#!/usr/bin/env python3
"""Benchmark de la operación «Dividir PDF».

Genera un PDF de N páginas y mide tiempo, RSS pico y tamaño de salida al
dividirlo en archivos de una página (modo ``single``), el caso más costoso
en cantidad de archivos. Sirve para verificar el criterio de aceptación de
F1 (500 páginas en modo ``single`` por debajo de 250 MB de RSS).

Uso::

    python scripts/benchmark_split.py [--pages 500] [--output-dir DIR]
"""
from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import psutil  # noqa: E402

import pymupdf  # noqa: E402

from app.models.document import PdfDocument, PdfStatus  # noqa: E402
from app.operations.base import JobContext  # noqa: E402
from app.operations.split import SplitOperation  # noqa: E402


def build_pdf(path: Path, pages: int) -> None:
    doc = pymupdf.open()
    for i in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Página {i + 1} de {pages}")
    doc.save(path)
    doc.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", type=int, default=500)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    pages = args.pages
    if pages < 1:
        raise SystemExit("--pages debe ser >= 1")

    with tempfile.TemporaryDirectory(prefix="pdfbs-bench-") as tmp:
        tmp_path = Path(tmp)
        source = tmp_path / "grande.pdf"
        print(f"Generando PDF de {pages} páginas…")
        started = time.perf_counter()
        build_pdf(source, pages)
        print(f"  generado en {time.perf_counter() - started:.2f}s ({source.stat().st_size / 1024 / 1024:.1f} MB)")

        out_dir = args.output_dir or (tmp_path / "salida")
        out_dir.mkdir(parents=True, exist_ok=True)
        tmp_job = tmp_path / "jobtmp"
        tmp_job.mkdir(parents=True, exist_ok=True)

        pdf_doc = PdfDocument(
            path=str(source),
            name=source.name,
            page_count=pages,
            status=PdfStatus.READY,
        )

        class FakeDocuments:
            def included(self, session_id):
                return [pdf_doc]

        operation = SplitOperation(FakeDocuments(), config=None)
        plan = operation.plan("bench-session", {"mode": "single", "output_dir": str(out_dir)})

        process = psutil.Process()
        rss_before = process.memory_info().rss
        peak_rss = rss_before
        started = time.perf_counter()

        def progress(*_args, **_kwargs):
            nonlocal peak_rss
            peak_rss = max(peak_rss, process.memory_info().rss)

        def item(*_args, **_kwargs):
            nonlocal peak_rss
            peak_rss = max(peak_rss, process.memory_info().rss)

        ctx = JobContext(
            job_id="bench",
            session_id="bench-session",
            tmp_dir=tmp_job,
            progress=progress,
            item=item,
            cancel_requested=lambda: False,
        )
        result = operation.execute(plan, ctx, {"mode": "single", "collision_policy": "suffix", "name_template": "{name}_parte_{index}"})
        elapsed = time.perf_counter() - started
        peak_rss = max(peak_rss, process.memory_info().rss)
        ctx.cleanup()

        output_files = sorted(out_dir.glob("*.pdf"))
        total_output_bytes = sum(p.stat().st_size for p in output_files)
        print()
        print("Resultado:")
        print(f"  estado: {result.status}")
        print(f"  archivos generados: {result.output.get('total_files')}")
        print(f"  páginas totales: {result.output.get('total_pages')}")
        print(f"  tiempo: {elapsed:.2f}s")
        print(f"  RSS pico: {peak_rss / 1024 / 1024:.1f} MB")
        print(f"  tamaño de salida: {total_output_bytes / 1024 / 1024:.1f} MB")
        if result.errors:
            print(f"  errores: {len(result.errors)}")
            for error in result.errors[:5]:
                print(f"    - {error.get('message')}")

        if pages >= 500 and peak_rss / 1024 / 1024 >= 250:
            print("\nFALLO: RSS pico supera 250 MB", file=sys.stderr)
            return 1
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
