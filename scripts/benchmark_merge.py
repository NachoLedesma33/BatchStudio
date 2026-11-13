"""Benchmark sequential merge of many small PDFs.

Usage:
    python scripts/benchmark_merge.py --count 100 --out C:/temp/bench100
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.pdf_inspector import inspect_pdf  # noqa: E402
from app.services.pdf_merger import merge_pdfs  # noqa: E402


def run(count: int, work: Path) -> dict:
    pdf_dir = work / "pdfs"
    # generate if missing
    if not pdf_dir.exists() or len(list(pdf_dir.glob("*.pdf"))) < count:
        import generate_test_pdfs

        generate = generate_test_pdfs.generate

        generate(count, pdf_dir)

    paths = sorted(str(p) for p in pdf_dir.glob("*.pdf"))[:count]

    # inspect
    t0 = time.perf_counter()
    docs = [inspect_pdf(p) for p in paths]
    inspect_time = time.perf_counter() - t0

    out = work / "merged.pdf"
    if out.exists():
        out.unlink()

    def progress(stage, idx, total, name, pct, elapsed):
        print(f"\r[{stage}] {idx}/{total} {pct:5.1f}%  {name or ''}", end="", flush=True)

    res = merge_pdfs(paths, out, progress=progress)
    print()
    summary = {
        "count": count,
        "inspect_seconds": round(inspect_time, 3),
        "merge_seconds": round(res.elapsed_seconds, 3),
        "peak_rss_mb": round(res.peak_rss_mb, 2),
        "output_pages": res.total_pages,
        "processed_documents": res.processed_documents,
        "error_count": res.error_count,
        "errors": [e.message for e in res.errors],
        "status": res.status,
        "output_size_bytes": out.stat().st_size if out.exists() else 0,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--out", type=str, required=True)
    args = parser.parse_args()
    run(args.count, Path(args.out))


if __name__ == "__main__":
    main()
