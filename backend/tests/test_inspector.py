from __future__ import annotations

from pathlib import Path

from app.services.pdf_inspector import inspect_pdf, PdfStatus


def test_inspect_valid(sample_pdf):
    d = inspect_pdf(sample_pdf)
    assert d.status == PdfStatus.READY
    assert d.page_count == 1
    assert d.size_bytes > 0
    assert d.sha256 is not None
    assert len(d.sha256) == 64


def test_inspect_missing(tmp_path):
    d = inspect_pdf(tmp_path / "nope.pdf")
    assert d.status == PdfStatus.INVALID
    assert "no existe" in (d.error_message or "").lower()


def test_inspect_empty(tmp_path):
    p = tmp_path / "empty.pdf"
    p.write_bytes(b"")
    d = inspect_pdf(p)
    assert d.status == PdfStatus.INVALID


def test_inspect_wrong_extension(tmp_path):
    p = tmp_path / "foo.txt"
    p.write_text("hola")
    d = inspect_pdf(p)
    assert d.status == PdfStatus.INVALID


def test_inspect_corrupt(tmp_path):
    p = tmp_path / "bad.pdf"
    p.write_bytes(b"%PDF-1.4\ngarbage")
    d = inspect_pdf(p)
    assert d.status in (PdfStatus.INVALID, PdfStatus.PROTECTED)
