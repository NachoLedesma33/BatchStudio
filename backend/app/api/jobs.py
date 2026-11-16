from __future__ import annotations

import json
import time
from typing import Any, Iterator

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.deps import get_services, get_session_id
from app.core.errors import ApiError
from app.db.repositories.jobs import FINAL_STATUSES
from app.schemas.api import CreateJobRequest
from app.services.container import Services

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _legacy_snapshot(job: dict[str, Any]) -> dict[str, Any]:
    output = job.get("output") or {}
    current_item = next(
        (item for item in job.get("items", []) if item.get("status") == "processing"),
        None,
    )
    return {
        "job_id": job["id"],
        "status": job["status"],
        "progress": job["progress"],
        "stage": job["stage"],
        "current_document": current_item["label"] if current_item else None,
        "total": job["total_items"],
        "processed": job["done_items"],
        "total_pages": output.get("total_pages", 0),
        "error_count": job["error_count"],
        "errors": job["errors"],
        "output_path": output.get("output_path"),
        "elapsed_seconds": output.get("elapsed_seconds", 0.0),
        "peak_rss_mb": output.get("peak_rss_mb", 0.0),
        "cancelled": bool(output.get("cancelled", job["status"] == "cancelled")),
    }


def _sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _stream_job(job_id: str, services: Services) -> Iterator[str]:
    index = 0
    emitted_done = False
    while True:
        job = services.jobs.get(job_id)
        if job is None:
            yield _sse({"type": "error", "message": "El trabajo no existe."})
            return

        events, index = services.events.since(job_id, index)
        for event in events:
            if event.get("type") == "done":
                emitted_done = True
            if event.get("type") == "result" and not event.get("result"):
                event = {**event, "result": job.get("output")}
            yield _sse(event)

        if job["status"] in FINAL_STATUSES:
            if not emitted_done:
                if job.get("output") is not None:
                    yield _sse({"type": "result", "result": job["output"]})
                yield _sse({"type": "done", "status": job["status"]})
            return
        time.sleep(0.2)


@router.post("", status_code=202)
def create_job(
    req: CreateJobRequest,
    session_id: str = Depends(get_session_id),
    services: Services = Depends(get_services),
):
    operation = services.registry.get(req.kind)
    if operation is None:
        raise ApiError(
            "UNKNOWN_OPERATION",
            f"La operación «{req.kind}» no existe.",
            status_code=404,
        )
    job = services.jobs.create(
        kind=req.kind,
        session_id=session_id,
        params=req.params or {},
        total_items=0,
    )
    return {"job_id": job["id"], "status": job["status"]}


@router.get("")
def list_jobs(
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    services: Services = Depends(get_services),
):
    statuses = [part.strip() for part in status.split(",")] if status else None
    return {"jobs": services.jobs.list(statuses=statuses, limit=limit)}


@router.get("/{job_id}")
def get_job(job_id: str, services: Services = Depends(get_services)):
    job = services.jobs.get(job_id)
    if job is None:
        raise ApiError("JOB_NOT_FOUND", "El trabajo no existe.", status_code=404)
    return job


@router.get("/{job_id}/events")
def job_events(job_id: str, services: Services = Depends(get_services)):
    if services.jobs.get(job_id) is None:
        raise ApiError("JOB_NOT_FOUND", "El trabajo no existe.", status_code=404)
    return StreamingResponse(
        _stream_job(job_id, services),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str, services: Services = Depends(get_services)):
    if not services.jobs.request_cancel(job_id):
        raise ApiError("JOB_NOT_FOUND", "El trabajo no existe.", status_code=404)
    return {"ok": True}


@router.post("/{job_id}/retry", status_code=202)
def retry_job(job_id: str, services: Services = Depends(get_services)):
    if services.jobs.get(job_id) is None:
        raise ApiError("JOB_NOT_FOUND", "El trabajo no existe.", status_code=404)
    if not services.jobs.requeue(job_id):
        raise ApiError(
            "JOB_NOT_RETRYABLE",
            "El trabajo no se puede reintentar en su estado actual.",
            status_code=409,
        )
    return {"job_id": job_id, "status": "queued"}


@router.get("/{job_id}/report/export")
def export_job_report(
    job_id: str,
    format: str = Query(default="json"),
    services: Services = Depends(get_services),
):
    job = services.jobs.get(job_id)
    if job is None:
        raise ApiError("JOB_NOT_FOUND", "El trabajo no existe.", status_code=404)
    report = {
        "job_id": job["id"],
        "kind": job["kind"],
        "status": job["status"],
        "result": job.get("output"),
        "items": job.get("items", []),
        "errors": job.get("errors", []),
    }
    if format.lower() == "json":
        return report
    if format.lower() == "csv":
        import csv
        import io

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["index", "label", "status", "output_path", "message"])
        for item in job.get("items", []):
            writer.writerow(
                [
                    item.get("index"),
                    item.get("label"),
                    item.get("status"),
                    item.get("output_path"),
                    item.get("message"),
                ]
            )
        return {"format": "csv", "content": buffer.getvalue()}
    # txt
    lines = [f"Job {job['id']} - {job['kind']} - {job['status']}"]
    for item in job.get("items", []):
        lines.append(f"{item.get('index')}. {item.get('label')} - {item.get('status')} {item.get('output_path') or ''}")
    if job.get("errors"):
        lines.append("Errores:")
        for err in job.get("errors", []):
            lines.append(f"- {err.get('message')}")
    return {"format": "txt", "content": "\n".join(lines)}
@router.get("/{job_id}/report")
def job_report(job_id: str, services: Services = Depends(get_services)):
    job = services.jobs.get(job_id)
    if job is None:
        raise ApiError("JOB_NOT_FOUND", "El trabajo no existe.", status_code=404)
    return {
        "job_id": job["id"],
        "kind": job["kind"],
        "status": job["status"],
        "result": job.get("output"),
        "items": job.get("items", []),
        "errors": job.get("errors", []),
        "created_at": job["created_at"],
        "started_at": job["started_at"],
        "finished_at": job["finished_at"],
    }
