from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient


def _import_paths(client: TestClient, paths: list[Path]) -> list[dict]:
    response = client.post("/api/files/import", json={"paths": [str(path) for path in paths]})
    assert response.status_code == 200, response.text
    return response.json()["documents"]


def _make_pdf(path: Path, text: str) -> None:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()


def test_search_within_document(client: TestClient, tmp_path: Path) -> None:
    source = tmp_path / "doc.pdf"
    _make_pdf(source, "El zorro marrón salta sobre el perro perezoso.")
    imported = _import_paths(client, [source])
    doc_id = imported[0]["id"]

    r = client.get(f"/api/documents/{doc_id}/search", params={"q": "zorro"})
    assert r.status_code == 200, r.text
    results = r.json()["results"]
    assert len(results) == 1
    assert results[0]["page"] == 1
    assert "zorro" in results[0]["snippet"].lower()


def test_global_search_index(client: TestClient, services, tmp_path: Path) -> None:
    source = tmp_path / "doc.pdf"
    _make_pdf(source, "Texto único para búsqueda global.")
    _import_paths(client, [source])

    r = client.post("/api/search/index")
    assert r.status_code == 200, r.text
    assert r.json()["indexed"] == 1

    r = client.post("/api/search", json={"query": "único"})
    assert r.status_code == 200, r.text
    results = r.json()["results"]
    assert len(results) >= 1
    assert "único" in results[0]["snippet"]

    r = client.delete("/api/search/index")
    assert r.status_code == 200, r.text
