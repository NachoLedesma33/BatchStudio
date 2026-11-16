from __future__ import annotations

from pathlib import Path

from app.models.document import PdfDocument, PdfStatus


def _doc(path: Path, order: int = 0) -> PdfDocument:
    return PdfDocument(
        path=str(path),
        name=path.name,
        size_bytes=10,
        page_count=2,
        sha256="a" * 64,
        status=PdfStatus.READY,
        order_index=order,
    )


def test_sessions_default(services) -> None:
    session = services.sessions.ensure_default()
    assert session["id"] == "local"
    assert services.sessions.get("local")["name"] == "Sesión local"
    assert [item["id"] for item in services.sessions.list()] == ["local"]


def test_documents_upsert_preserves_identity_and_order(services, tmp_path: Path) -> None:
    first = services.documents.upsert("local", _doc(tmp_path / "a.pdf"))
    second = services.documents.upsert("local", _doc(tmp_path / "b.pdf"))
    services.documents.update(first.id, included=False)

    again = services.documents.upsert("local", _doc(tmp_path / "a.pdf"))
    assert again.id == first.id
    assert again.included is False
    assert again.order_index == first.order_index

    assert [doc.id for doc in services.documents.list("local")] == [first.id, second.id]
    assert [doc.id for doc in services.documents.included("local")] == [second.id]


def test_documents_reorder_and_remove(services, tmp_path: Path) -> None:
    a = services.documents.upsert("local", _doc(tmp_path / "a.pdf"))
    b = services.documents.upsert("local", _doc(tmp_path / "b.pdf"))
    c = services.documents.upsert("local", _doc(tmp_path / "c.pdf"))

    assert services.documents.reorder("local", [c.id, a.id, b.id]) is True
    assert [doc.id for doc in services.documents.list("local")] == [c.id, a.id, b.id]
    assert services.documents.reorder("local", [a.id]) is False

    assert services.documents.remove(a.id) is True
    remaining = services.documents.list("local")
    assert [doc.id for doc in remaining] == [c.id, b.id]
    assert [doc.order_index for doc in remaining] == [0, 1]


def test_pages_repository(services, tmp_path: Path) -> None:
    doc = services.documents.upsert("local", _doc(tmp_path / "pages.pdf"))
    services.pages.ensure_default(doc.id, 3)
    services.pages.ensure_default(doc.id, 3)  # no duplica
    assert services.pages.count(doc.id) == 3
    assert [page["page_no"] for page in services.pages.list(doc.id)] == [1, 2, 3]

    services.pages.set_page(doc.id, 1, page_order=5)
    services.pages.set_page(doc.id, 2, page_order=0, rotation=90)
    assert services.pages.list(doc.id)[0]["page_no"] == 2
    services.pages.replace(doc.id, [{"page_no": 3, "rotation": 180}])
    assert services.pages.count(doc.id) == 1
    assert services.pages.list(doc.id)[0]["rotation"] == 180


def test_jobs_lifecycle(services) -> None:
    job = services.jobs.create(kind="merge", session_id="local", params={"x": 1}, total_items=1)
    assert job["status"] == "queued"
    assert services.jobs.session_id(job["id"]) == "local"

    claimed = services.jobs.claim_next()
    assert claimed is not None and claimed["status"] == "running"
    services.jobs.set_item(job["id"], 1, "out.pdf", "completed", output_path="C:/out.pdf")
    services.jobs.set_progress(job["id"], progress=50, stage="saving", done_items=1)
    services.jobs.finish(job["id"], status="completed", output={"output_path": "C:/out.pdf"})

    saved = services.jobs.get(job["id"])
    assert saved["status"] == "completed"
    assert saved["progress"] == 50
    assert saved["items"][0]["output_path"] == "C:/out.pdf"
    assert "C:/out.pdf" in services.jobs.all_output_paths()
    assert services.jobs.requeue(job["id"]) is False  # completed no se reintenta solo
    services.jobs.update(job["id"], status="interrupted")
    assert services.jobs.requeue(job["id"]) is True
    assert services.jobs.get(job["id"])["status"] == "queued"


def test_jobs_recovery_and_history(services) -> None:
    job = services.jobs.create(kind="merge", session_id="local", params={})
    services.jobs.update(job["id"], status="running")
    assert services.jobs.recover_interrupted() == 1
    assert services.jobs.get(job["id"])["status"] == "interrupted"

    entry = services.history.add(
        job_id=job["id"], kind="merge", summary="merge: completed", inputs=[], outputs=[]
    )
    assert services.history.get(entry["id"])["summary"] == "merge: completed"
    assert services.history.list()[0]["id"] == entry["id"]
