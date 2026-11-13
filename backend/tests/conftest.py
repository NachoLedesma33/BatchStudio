from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import pytest  # noqa: E402

from app.services.pdf_inspector import inspect_pdf  # noqa: E402


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    import fitz

    p = tmp_path / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hola mundo")
    doc.save(p)
    doc.close()
    return p


@pytest.fixture
def three_pdfs(tmp_path: Path) -> list[Path]:
    import fitz

    paths = []
    for i in range(3):
        p = tmp_path / f"doc{i}.pdf"
        doc = fitz.open()
        for j in range(i + 1):
            page = doc.new_page()
            page.insert_text((72, 72), f"doc{i} page{j}")
        doc.save(p)
        doc.close()
        paths.append(p)
    return paths
