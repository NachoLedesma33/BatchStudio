from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import get_services, get_session_id
from app.api.jobs import _legacy_snapshot, _stream_job
from app.core.errors import ApiError
from app.schemas.api import MergeJobRequest
from app.services.container import Services

router = APIRouter(prefix="/api/merge-jobs", tags=["legacy-merge"])


@router.post("")
def create_merge_job(
    req: MergeJobRequest,
    session_id: str = Depends(get_session_id),
    services: Services = Depends(get_services),
):
    if not services.documents.included(session_id):
        raise ApiError("NO_DOCUMENTS", "No hay documentos incluidos en el lote.")
    job = services.jobs.create(
        kind="merge",
        session_id=session_id,
        params={
            "output_path": req.output_path,
            "overwrite": req.overwrite,
        },
        total_items=0,
    )
    return {"job_id": job["id"]}


@router.get("/{job_id}")
def get_merge_job(job_id: str, services: Services = Depends(get_services)):
    job = services.jobs.get(job_id)
    if job is None:
        raise ApiError("JOB_NOT_FOUND", "El trabajo no existe.", status_code=404)
    return _legacy_snapshot(job)


@router.get("/{job_id}/events")
def merge_job_events(job_id: str, services: Services = Depends(get_services)):
    if services.jobs.get(job_id) is None:
        raise ApiError("JOB_NOT_FOUND", "El trabajo no existe.", status_code=404)
    return StreamingResponse(
        _stream_job(job_id, services),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{job_id}/cancel")
def cancel_merge_job(job_id: str, services: Services = Depends(get_services)):
    if not services.jobs.request_cancel(job_id):
        raise ApiError("JOB_NOT_FOUND", "El trabajo no existe.", status_code=404)
    return {"ok": True}


@router.get("/{job_id}/report")
def merge_job_report(job_id: str, services: Services = Depends(get_services)):
    job = services.jobs.get(job_id)
    if job is None:
        raise ApiError("JOB_NOT_FOUND", "El trabajo no existe.", status_code=404)
    return job.get("output") or _legacy_snapshot(job)
