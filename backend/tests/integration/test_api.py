from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.services.container import build_services


def _import_paths(client: TestClient, paths: list[Path]) -> list[dict]:
    response = client.post("/api/files/import", json={"paths": [str(path) for path in paths]})
    assert response.status_code == 200, response.text
    return response.json()["documents"]


def test_health_and_capabilities(client: TestClient) -> None:
    assert client.get("/api/health").json() == {"status": "ok"}
    started = time.perf_counter()
    response = client.get("/api/capabilities")
    assert response.status_code == 200
    assert time.perf_counter() - started < 3.0
    assert response.json()["pdf_engine"]["name"] == "PyMuPDF"


def test_documents_flow_and_persistence(client: TestClient, services, three_pdfs) -> None:
    documents = _import_paths(client, three_pdfs)
    assert len(documents) == 3
    assert [doc["order_index"] for doc in documents] == [0, 1, 2]

    listed = client.get("/api/documents").json()["documents"]
    assert [doc["id"] for doc in listed] == [doc["id"] for doc in documents]

    first_id = documents[0]["id"]
    assert client.patch(f"/api/documents/{first_id}", json={"included": False}).status_code == 200
    assert client.get("/api/documents").json()["documents"][0]["included"] is False

    reordered = [documents[2]["id"], documents[1]["id"], first_id]
    response = client.patch("/api/documents/order", json={"ids": reordered})
    assert response.status_code == 200
    assert [doc["id"] for doc in response.json()["documents"]] == reordered

    preview = client.get(f"/api/documents/{first_id}/preview/1")
    assert preview.status_code == 200
    assert preview.headers["content-type"] == "image/png"
    assert preview.content.startswith(b"\x89PNG")

    # "Reiniciar": una instancia nueva sobre la misma base conserva todo.
    restarted = build_services(db_path=services.db.path)
    try:
        persisted = restarted.documents.list("local")
        assert [doc.id for doc in persisted] == reordered
        assert persisted[-1].included is False
    finally:
        restarted.close()


def test_preview_does_not_write(client: TestClient, three_pdfs, tmp_path: Path) -> None:
    _import_paths(client, three_pdfs)
    output = tmp_path / "no-debe-existir.pdf"
    response = client.post(
        "/api/operations/preview",
        json={"kind": "merge", "params": {"output_path": str(output)}},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["kind"] == "merge"
    assert payload["summary"]["total_files"] == 3
    assert payload["summary"]["total_pages"] == 6
    assert payload["items"][0]["label"] == output.name
    assert not output.exists()


def test_merge_job_end_to_end(client: TestClient, services, three_pdfs, tmp_path: Path) -> None:
    _import_paths(client, three_pdfs)
    output = tmp_path / "unido.pdf"
    response = client.post(
        "/api/merge-jobs",
        json={"output_path": str(output), "overwrite": False},
    )
    assert response.status_code == 200, response.text
    job_id = response.json()["job_id"]

    assert services.worker.run_once() is True

    report = client.get(f"/api/merge-jobs/{job_id}/report")
    assert report.status_code == 200
    payload = report.json()
    assert payload["status"] == "completed", payload
    assert payload["total_pages"] == 6
    assert Path(payload["output_path"]).is_file()

    generic = client.get(f"/api/jobs/{job_id}/report").json()
    assert generic["status"] == "completed"
    assert generic["result"]["total_pages"] == 6
    assert generic["items"][0]["status"] == "completed"

    with client.stream("GET", f"/api/merge-jobs/{job_id}/events") as stream:
        body = "".join(stream.iter_text())
    assert '"type": "done"' in body
    assert "completed" in body

    history = client.get("/api/history").json()["history"]
    assert history and history[0]["job_id"] == job_id


def test_merge_rejects_empty_lot(client: TestClient) -> None:
    response = client.post("/api/merge-jobs", json={})
    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "NO_DOCUMENTS"


def test_token_and_origin_enforced(services) -> None:
    app = create_app(
        services=services,
        require_token=True,
        strict_host=False,
        start_worker=False,
        token="secreto",
    )
    with TestClient(app) as client:
        assert client.get("/api/documents").status_code == 401
        assert (
            client.get("/api/documents", headers={"X-PDFBS-Token": "mal"}).status_code == 401
        )
        assert (
            client.get("/api/documents", headers={"X-PDFBS-Token": "secreto"}).status_code == 200
        )
        forbidden = client.get(
            "/api/documents",
            headers={"X-PDFBS-Token": "secreto", "Origin": "https://ejemplo-ajeno.test"},
        )
        assert forbidden.status_code == 403
        assert forbidden.json()["detail"]["code"] == "ORIGIN_NOT_ALLOWED"
