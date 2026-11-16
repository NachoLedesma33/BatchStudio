from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

# Todo el proceso de tests usa un directorio de datos aislado.
os.environ["PDFBS_DATA_DIR"] = tempfile.mkdtemp(prefix="pdfbs-tests-")

import pytest  # noqa: E402

from app.services.pdf_inspector import inspect_pdf  # noqa: E402,F401


@pytest.fixture
def sample_pdf(tmp_path: Path) -> Path:
    import pymupdf

    p = tmp_path / "sample.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hola mundo")
    doc.save(p)
    doc.close()
    return p


@pytest.fixture
def three_pdfs(tmp_path: Path) -> list[Path]:
    import pymupdf

    paths = []
    for i in range(3):
        p = tmp_path / f"doc{i}.pdf"
        doc = pymupdf.open()
        for j in range(i + 1):
            page = doc.new_page()
            page.insert_text((72, 72), f"doc{i} page{j}")
        doc.save(p)
        doc.close()
        paths.append(p)
    return paths


@pytest.fixture
def ten_page_pdf(tmp_path: Path) -> Path:
    import pymupdf

    path = tmp_path / "diez.pdf"
    doc = pymupdf.open()
    for index in range(10):
        page = doc.new_page()
        page.insert_text((72, 72), f"Página {index + 1}")
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def services(tmp_path: Path):
    from app.services.container import build_services

    container = build_services(db_path=tmp_path / "test.db")
    try:
        yield container
    finally:
        container.close()


@pytest.fixture
def client(services):
    from fastapi.testclient import TestClient

    from app.main import create_app

    app = create_app(
        services=services,
        require_token=False,
        strict_host=False,
        start_worker=False,
    )
    with TestClient(app) as test_client:
        yield test_client
