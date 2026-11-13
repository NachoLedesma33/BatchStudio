from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.services.pdf_merger import merge_pdfs, ProgressCallback


@dataclass
class JobState:
    job_id: str
    status: str = "pending"
    progress: float = 0.0
    stage: str = "pending"
    current_document: Optional[str] = None
    total: int = 0
    processed: int = 0
    total_pages: int = 0
    error_count: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    output_path: Optional[str] = None
    elapsed_seconds: float = 0.0
    peak_rss_mb: float = 0.0
    cancelled: bool = False
    events: List[Dict[str, Any]] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def push(self, event: Dict[str, Any]) -> None:
        with self._lock:
            self.events.append(event)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "job_id": self.job_id,
                "status": self.status,
                "progress": self.progress,
                "stage": self.stage,
                "current_document": self.current_document,
                "total": self.total,
                "processed": self.processed,
                "total_pages": self.total_pages,
                "error_count": self.error_count,
                "errors": list(self.errors),
                "output_path": self.output_path,
                "elapsed_seconds": round(self.elapsed_seconds, 3),
                "peak_rss_mb": round(self.peak_rss_mb, 2),
                "cancelled": self.cancelled,
            }


class JobManager:
    def __init__(self) -> None:
        self._jobs: Dict[str, JobState] = {}
        self._lock = threading.Lock()

    def create(self, paths: List[str], output_path: str, overwrite: bool = False) -> JobState:
        job_id = str(uuid.uuid4())
        job = JobState(job_id=job_id)
        job.total = len(paths)
        with self._lock:
            self._jobs[job_id] = job

        def worker() -> None:
            cancel_event = threading.Event()
            job._cancel_event = cancel_event  # type: ignore[attr-defined]
            start = time.perf_counter()

            def progress(stage: str, idx: int, total: int, name, pct: float, elapsed: float) -> None:
                with job._lock:
                    job.stage = stage
                    job.progress = pct
                    job.current_document = name
                    job.processed = idx
                    job.total = total
                    job.elapsed_seconds = elapsed
                job.push({"type": "progress", "stage": stage, "index": idx, "total": total, "file": name, "progress": pct, "elapsed": round(elapsed, 3)})

            try:
                job.status = "running"
                job.push({"type": "status", "status": "running"})
                res = merge_pdfs(
                    paths,
                    output_path,
                    overwrite=overwrite,
                    progress=progress,
                    cancel_event=cancel_event,
                )
                with job._lock:
                    job.status = res.status
                    job.progress = 100.0 if res.status.startswith("completed") else job.progress
                    job.output_path = res.output_path
                    job.total_pages = res.total_pages
                    job.processed = res.processed_documents
                    job.error_count = res.error_count
                    job.errors = [e.__dict__ if hasattr(e, "__dict__") else {} for e in res.errors]
                    # normalize errors to dict
                    job.errors = []
                    for e in res.errors:
                        job.errors.append({"document_id": e.document_id, "path": e.path, "message": e.message, "detail": e.detail})
                    job.elapsed_seconds = res.elapsed_seconds
                    job.peak_rss_mb = res.peak_rss_mb
                    job.cancelled = res.cancelled
                    job.result = res.to_dict()
                job.push({"type": "result", "result": res.to_dict()})
            except Exception as exc:  # noqa: BLE001
                with job._lock:
                    job.status = "failed"
                    job.errors.append({"message": str(exc)})
                job.push({"type": "error", "message": str(exc)})

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        return job

    def get(self, job_id: str) -> Optional[JobState]:
        with self._lock:
            return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        job = self.get(job_id)
        if not job:
            return False
        ev = getattr(job, "_cancel_event", None)
        if ev is not None:
            ev.set()
        with job._lock:
            job.cancelled = True
        job.push({"type": "cancel", "message": "Cancelación solicitada"})
        return True


JOB_MANAGER = JobManager()
