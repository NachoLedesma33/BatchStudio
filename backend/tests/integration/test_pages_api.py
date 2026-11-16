from __future__ import annotations

from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient


def _import_paths(client: TestClient, paths: list[Path]) -> list[dict]:
    response = client.post("/api/files/import", json={"paths": [str(path) for path in paths]})
    assert response.status_code == 200, response.text
    return response.json()["documents"]


def test_pages_ensure_list_replace_patch(client: TestClient, tmp_path: Path) -> None:
    source = tmp_path / "tres.pdf"
    doc = pymupdf.open()
    for index in range(3):
        doc.new_page().insert_text((72, 72), f"P{index + 1}")
    doc.save(source)
    doc.close()

    imported = _import_paths(client, [source])
    doc_id = imported[0]["id"]

    r = client.get(f"/api/documents/{doc_id}/pages")
    assert r.status_code == 200, r.text
    pages = r.json()["pages"]
    assert [p["page_no"] for p in pages] == [1, 2, 3]
    assert [p["page_order"] for p in pages] == [0, 1, 2]

    r = client.patch(f"/api/documents/{doc_id}/pages/2", json={"rotation": 90, "excluded": True})
    assert r.status_code == 200, r.text

    r = client.put(
        f"/api/documents/{doc_id}/pages",
        json={"pages": [{"page_no": 3, "page_order": 0}, {"page_no": 1, "page_order": 1}]},
    )
    assert r.status_code == 200, r.text
    pages = r.json()["pages"]
    assert [p["page_no"] for p in pages] == [3, 1]
