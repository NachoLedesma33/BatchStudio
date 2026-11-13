from __future__ import annotations

import hashlib
from pathlib import Path

import fitz

from app.services.pdf_merger import merge_pdfs, MergeResult


def _hash(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(65536), b""):
            h.update(c)
    return h.hexdigest()


def test_merge_three(three_pdfs, tmp_path):
    out = tmp_path / "out.pdf"
    hashes_before = [_hash(p) for p in three_pdfs]
    res = merge_pdfs([str(p) for p in three_pdfs], out)
    assert isinstance(res, MergeResult)
    assert res.status in ("completed", "completed_with_errors")
    assert out.exists()
    assert res.total_pages == 1 + 2 + 3
    with fitz.open(str(out)) as d:
        assert d.page_count == 6
    # originals unchanged
    assert [_hash(p) for p in three_pdfs] == hashes_before


def test_merge_cancel(three_pdfs, tmp_path):
    import threading

    out = tmp_path / "out2.pdf"
    ev = threading.Event()
    ev.set()  # cancel immediately
    res = merge_pdfs([str(p) for p in three_pdfs], out, cancel_event=ev)
    assert res.cancelled is True
    assert res.status == "cancelled"
    assert not out.exists() or res.output_path is None


def test_merge_existing_dest(three_pdfs, tmp_path):
    out = tmp_path / "out3.pdf"
    out.write_bytes(b"x")
    res = merge_pdfs([str(p) for p in three_pdfs], out, overwrite=False)
    assert res.status == "failed"
    assert "ya existe" in res.errors[0].message


def test_merge_overwrite(three_pdfs, tmp_path):
    out = tmp_path / "out4.pdf"
    out.write_bytes(b"x")
    res = merge_pdfs([str(p) for p in three_pdfs], out, overwrite=True)
    assert res.status in ("completed", "completed_with_errors")
    assert out.exists()
