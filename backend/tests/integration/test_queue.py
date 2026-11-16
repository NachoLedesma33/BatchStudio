from __future__ import annotations

from pathlib import Path

from app.services.container import build_services
from app.services.pdf_inspector import inspect_pdf


def test_running_job_becomes_interrupted_and_retries(tmp_path: Path, three_pdfs) -> None:
    db_path = tmp_path / "queue.db"
    first = build_services(db_path=db_path)
    try:
        for path in three_pdfs:
            first.documents.upsert("local", inspect_pdf(path))
        output = tmp_path / "reanudado.pdf"
        job = first.jobs.create(
            kind="merge",
            session_id="local",
            params={"output_path": str(output), "overwrite": False},
        )
        first.jobs.update(job["id"], status="running")
    finally:
        first.close()

    second = build_services(db_path=db_path)
    try:
        second.worker.start()
        second.worker.stop()
        assert second.jobs.get(job["id"])["status"] == "interrupted"

        assert second.jobs.requeue(job["id"]) is True
        assert second.worker.run_once() is True
        finished = second.jobs.get(job["id"])
        assert finished["status"] == "completed", finished
        assert output.is_file()
    finally:
        second.close()


def test_cancel_queued_job(tmp_path: Path) -> None:
    services = build_services(db_path=tmp_path / "cancel.db")
    try:
        job = services.jobs.create(kind="merge", session_id="local", params={})
        assert services.jobs.request_cancel(job["id"]) is True
        assert services.worker.run_once() is True
        assert services.jobs.get(job["id"])["status"] == "cancelled"
    finally:
        services.close()


def test_unknown_operation_fails_without_crashing(tmp_path: Path) -> None:
    services = build_services(db_path=tmp_path / "unknown.db")
    try:
        job = services.jobs.create(kind="inexistente", session_id="local", params={})
        assert services.worker.run_once() is True
        saved = services.jobs.get(job["id"])
        assert saved["status"] == "failed"
        assert saved["errors"][0]["code"] == "UNKNOWN_OPERATION"
    finally:
        services.close()
