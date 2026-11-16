from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from app.core.errors import ApiError
from app.db.repositories.history import HistoryRepository
from app.db.repositories.jobs import JobRepository
from app.operations.base import JobContext, OperationPlan
from app.operations.registry import OperationRegistry
from app.services.event_bus import EventBus

logger = logging.getLogger(__name__)

FINAL_ITEM_STATUSES = {"completed", "failed", "cancelled", "skipped"}


class JobWorker:
    """Cola persistente con un único worker.

    El estado vive en SQLite; el thread solo ejecuta. Al iniciar, los jobs que
    quedaron `running` pasan a `interrupted` y los `queued` se retoman solos.
    """

    def __init__(
        self,
        *,
        jobs: JobRepository,
        history: HistoryRepository,
        registry: OperationRegistry,
        tmp_root: Path,
        bus: EventBus | None = None,
        poll_interval: float = 0.15,
    ) -> None:
        self.jobs = jobs
        self.history = history
        self.registry = registry
        self.tmp_root = Path(tmp_root)
        self.bus = bus or EventBus()
        self.tmp_root.mkdir(parents=True, exist_ok=True)
        self.poll_interval = poll_interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._start_lock = threading.Lock()

    def start(self) -> None:
        with self._start_lock:
            if self._thread is not None and self._thread.is_alive():
                return
            interrupted = self.jobs.recover_interrupted()
            if interrupted:
                logger.warning("Jobs interrumpidos marcados para reintento: %s", interrupted)
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, name="pdfbs-job-worker", daemon=True)
            self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=timeout)
        self._thread = None

    def run_once(self) -> bool:
        """Procesa como máximo un job. Útil para tests deterministas."""
        job = self.jobs.claim_next()
        if job is None:
            return False
        self._run(job)
        return True

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                job = self.jobs.claim_next()
            except Exception:  # noqa: BLE001
                logger.exception("No se pudo consultar la cola de trabajos.")
                self._stop.wait(1.0)
                continue
            if job is None:
                self._stop.wait(self.poll_interval)
                continue
            try:
                self._run(job)
            except Exception:  # noqa: BLE001
                logger.exception("El worker falló ejecutando el job %s", job.get("id"))

    def _run(self, job: dict[str, Any]) -> None:
        job_id = job["id"]
        kind = job["kind"]
        params = job.get("params") or {}
        session_id = self.jobs.session_id(job_id) or "local"
        tmp_dir = self.tmp_root / job_id

        if job.get("cancel_requested"):
            self.jobs.finish(job_id, status="cancelled", progress=0)
            self._emit_done(job_id, "cancelled")
            return

        operation = self.registry.get(kind)
        if operation is None:
            self.jobs.finish(
                job_id,
                status="failed",
                errors=[{"code": "UNKNOWN_OPERATION", "message": f"Operación desconocida: {kind}"}],
            )
            self._emit_done(job_id, "failed")
            return

        self.bus.publish(job_id, {"type": "status", "status": "running"})

        item_statuses: dict[int, str] = {}

        def on_progress(
            stage: str,
            percent: float,
            current: str | None,
            done: int | None,
            total: int | None,
        ) -> None:
            self.jobs.set_progress(
                job_id,
                progress=percent,
                stage=stage,
                done_items=sum(1 for status in item_statuses.values() if status in FINAL_ITEM_STATUSES),
                total_items=total,
            )
            self.bus.publish(
                job_id,
                {
                    "type": "progress",
                    "stage": stage,
                    "progress": percent,
                    "percent": percent,
                    "file": current,
                    "current": current,
                    "index": done,
                    "done": done,
                    "total": total,
                },
            )

        def on_item(
            index: int,
            label: str,
            status: str,
            output_path: str | None,
            message: str | None,
        ) -> None:
            item_statuses[index] = status
            self.jobs.set_item(
                job_id, index, label, status, output_path=output_path, message=message
            )
            self.jobs.set_progress(
                job_id,
                progress=max(0.0, min(100.0, (index / max(1, len(plan.items))) * 100.0))
                if status != "processing" else 0.0,
                done_items=sum(1 for value in item_statuses.values() if value in FINAL_ITEM_STATUSES),
            )
            self.bus.publish(
                job_id,
                {
                    "type": "item",
                    "index": index,
                    "label": label,
                    "status": status,
                    "output_path": output_path,
                    "message": message,
                },
            )

        try:
            plan = operation.plan(session_id, params)
            if plan.errors:
                errors = [message.to_dict() for message in plan.errors]
                self.jobs.replace_items(job_id, [])
                self.jobs.update(job_id, stage="failed", total_items=0)
                self.jobs.finish(job_id, status="failed", errors=errors, progress=0)
                self._record_history(job_id, kind, plan, params, status="failed", outputs=[])
                self._emit_done(job_id, "failed")
                return

            self.jobs.update(
                job_id,
                total_items=len(plan.items),
                stage="preparing",
            )
            self.jobs.replace_items(
                job_id,
                [
                    {
                        "index": item.index,
                        "label": item.label,
                        "status": "pending",
                        "output_path": None,
                        "message": None,
                    }
                    for item in plan.items
                ],
            )

            ctx = JobContext(
                job_id=job_id,
                session_id=session_id,
                tmp_dir=tmp_dir,
                progress=on_progress,
                item=on_item,
                cancel_requested=lambda: self.jobs.is_cancel_requested(job_id),
            )
            try:
                result = operation.execute(plan, ctx, params)
            finally:
                ctx.cleanup()

            status = result.status
            if status not in {
                "completed",
                "completed_with_errors",
                "failed",
                "cancelled",
            }:
                status = "failed"
            progress = 100.0 if status.startswith("completed") else None
            self.jobs.finish(
                job_id,
                status=status,
                output=result.output,
                errors=result.errors,
                progress=progress,
                error_count=len(result.errors),
            )
            self._record_history(
                job_id,
                kind,
                plan,
                params,
                status=status,
                outputs=[result.output],
                errors=result.errors,
            )
            self._emit_done(job_id, status, result.output)
        except ApiError as exc:
            self.jobs.finish(
                job_id,
                status="failed",
                errors=[{"code": exc.code, "message": exc.message, "hint": exc.hint}],
            )
            self._emit_done(job_id, "failed")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Job %s falló", job_id)
            self.jobs.finish(
                job_id,
                status="failed",
                errors=[{"code": "JOB_FAILED", "message": "El trabajo falló.", "detail": str(exc)}],
            )
            self._emit_done(job_id, "failed")

    def _emit_done(
        self, job_id: str, status: str, output: dict[str, Any] | None = None
    ) -> None:
        if output is not None:
            self.bus.publish(job_id, {"type": "result", "result": output})
        self.bus.publish(job_id, {"type": "done", "status": status})

    def _record_history(
        self,
        job_id: str,
        kind: str,
        plan: OperationPlan,
        params: dict[str, Any],
        *,
        status: str,
        outputs: list[Any],
        errors: list[dict[str, Any]] | None = None,
    ) -> None:
        summary = f"{kind}: {status}"
        if plan.summary.get("total_files") is not None:
            summary += f" ({plan.summary['total_files']} archivo(s))"
        try:
            self.history.add(
                job_id=job_id,
                kind=kind,
                summary=summary,
                inputs={"params": params, "summary": plan.summary},
                outputs={"outputs": outputs, "errors": errors or []},
            )
        except Exception:  # noqa: BLE001
            logger.exception("No se pudo registrar el historial del job %s", job_id)
