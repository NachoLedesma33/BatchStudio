from __future__ import annotations

import hashlib
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


def test_extract_discontinuous_pages(client: TestClient, services, tmp_path: Path) -> None:
    source = tmp_path / "cinco.pdf"
    doc = pymupdf.open()
    for index in range(5):
        page = doc.new_page()
        page.insert_text((72, 72), f"Página {index + 1}")
    doc.save(source)
    doc.close()

    imported = _import_paths(client, [source])
    doc_id = imported[0]["id"]

    out_dir = tmp_path / "extraido"
    params = {
        "document_id": doc_id,
        "pages": [1, 3, 5, 2, 4],
        "output_dir": str(out_dir),
        "name_template": "extraido",
    }
    preview = client.post("/api/operations/preview", json={"kind": "extract", "params": params})
    assert preview.status_code == 200, preview.text
    assert preview.json()["summary"]["total_pages"] == 5

    report = _run_job(client, services, "extract", params)
    assert report["status"] == "completed", report
    output = report["items"][0]["output_path"]
    assert Path(output).is_file()
    with pymupdf.open(output) as out_doc:
        assert out_doc.page_count == 5
        assert [p.get_text().strip() for p in out_doc] == [
            "Página 1",
            "Página 3",
            "Página 5",
            "Página 2",
            "Página 4",
        ]


def test_rotate_selected_pages(client: TestClient, services, tmp_path: Path) -> None:
    source = tmp_path / "tres.pdf"
    doc = pymupdf.open()
    for index in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), f"Página {index + 1}")
    doc.save(source)
    doc.close()

    imported = _import_paths(client, [source])
    doc_id = imported[0]["id"]

    params = {
        "document_id": doc_id,
        "pages": [2],
        "angle": 90,
        "output_dir": str(tmp_path / "rotado"),
        "name_template": "rotado",
    }
    report = _run_job(client, services, "rotate", params)
    assert report["status"] == "completed", report
    output = report["items"][0]["output_path"]
    with pymupdf.open(output) as out_doc:
        assert out_doc.page_count == 1
        assert out_doc[0].rotation == 90


def test_extract_ranges_string(client: TestClient, services, tmp_path: Path) -> None:
    source = tmp_path / "cuatro.pdf"
    doc = pymupdf.open()
    for index in range(4):
        doc.new_page().insert_text((72, 72), f"P{index + 1}")
    doc.save(source)
    doc.close()

    imported = _import_paths(client, [source])
    doc_id = imported[0]["id"]

    params = {
        "document_id": doc_id,
        "ranges": "2-4",
        "output_dir": str(tmp_path / "rangos"),
    }
    report = _run_job(client, services, "extract", params)
    assert report["status"] == "completed", report
    output = report["items"][0]["output_path"]
    with pymupdf.open(output) as out_doc:
        assert out_doc.page_count == 3
