from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient


def _import_paths(client: TestClient, paths: list[Path]) -> list[dict]:
    response = client.post("/api/files/import", json={"paths": [str(path) for path in paths]})
    assert response.status_code == 200, response.text
    return response.json()["documents"]


def _run_job(client: TestClient, services, kind: str, params: dict) -> dict:
    response = client.post("/api/jobs", json={"kind": kind, "params": params})
    assert response.status_code == 202, response.text
    job_id = response.json()["job_id"]
    assert services.worker.run_once() is True
    report = client.get(f"/api/jobs/{job_id}/report")
    assert report.status_code == 200, report.text
    return report.json()


def _make_pdf(path: Path, pages: int = 3) -> None:
    doc = pymupdf.open()
    for index in range(pages):
        page = doc.new_page()
        page.insert_text((72, 72), f"Página {index + 1}")
    doc.save(path)
    doc.close()


def test_pdf_to_images(client: TestClient, services, tmp_path: Path) -> None:
    source = tmp_path / "tres.pdf"
    _make_pdf(source, 3)
    imported = _import_paths(client, [source])
    doc_id = imported[0]["id"]

    out_dir = tmp_path / "imgs"
    params = {"document_id": doc_id, "dpi": 72, "format": "png", "output_dir": str(out_dir)}
    report = _run_job(client, services, "pdf-to-images", params)
    assert report["status"] == "completed", report
    images = sorted(out_dir.glob("*.png"))
    assert len(images) == 3


def test_images_to_pdf(client: TestClient, services, tmp_path: Path) -> None:
    # generar 2 imagenes
    img1 = tmp_path / "a.png"
    img2 = tmp_path / "b.png"
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 10, 10), 0)
    pix.save(str(img1))
    pix.save(str(img2))

    out_dir = tmp_path / "pdf"
    params = {"images": [str(img1), str(img2)], "output_dir": str(out_dir), "output_path": str(out_dir / "out.pdf")}
    report = _run_job(client, services, "images-to-pdf", params)
    assert report["status"] == "completed", report
    output = report["items"][0]["output_path"]
    with pymupdf.open(output) as doc:
        assert doc.page_count == 2


def test_extract_text(client: TestClient, services, tmp_path: Path) -> None:
    source = tmp_path / "dos.pdf"
    _make_pdf(source, 2)
    imported = _import_paths(client, [source])
    doc_id = imported[0]["id"]

    out_dir = tmp_path / "txt"
    params = {"document_id": doc_id, "output_dir": str(out_dir)}
    # output_path default Downloads; override via output_path
    params["output_path"] = str(out_dir / "salida.txt")
    report = _run_job(client, services, "extract-text", params)
    assert report["status"] == "completed", report
    output = report["items"][0]["output_path"]
    text = Path(output).read_text(encoding="utf-8")
    assert "Página 1" in text
    assert "Página 2" in text


def test_edit_metadata(client: TestClient, services, tmp_path: Path) -> None:
    source = tmp_path / "meta.pdf"
    _make_pdf(source, 1)
    imported = _import_paths(client, [source])
    doc_id = imported[0]["id"]

    out_dir = tmp_path / "metaout"
    params = {
        "document_id": doc_id,
        "title": "Titulo de prueba",
        "author": "Autor",
        "output_path": str(out_dir / "meta.pdf"),
    }
    report = _run_job(client, services, "edit-metadata", params)
    assert report["status"] == "completed", report
    output = report["items"][0]["output_path"]
    with pymupdf.open(output) as doc:
        assert doc.metadata.get("title") == "Titulo de prueba"
        assert doc.metadata.get("author") == "Autor"


def test_compress(client: TestClient, services, tmp_path: Path) -> None:
    source = tmp_path / "comp.pdf"
    _make_pdf(source, 5)
    imported = _import_paths(client, [source])
    doc_id = imported[0]["id"]

    out_dir = tmp_path / "compout"
    params = {"document_id": doc_id, "output_path": str(out_dir / "comp.pdf")}
    report = _run_job(client, services, "compress", params)
    assert report["status"] == "completed", report
    output = report["items"][0]["output_path"]
    assert Path(output).is_file()
