from __future__ import annotations

import uuid
from typing import Any, Iterable

from app.db.connection import Database
from app.db.repositories._common import dumps, loads, now_iso

FINAL_STATUSES = ("completed", "completed_with_errors", "failed", "cancelled", "interrupted")
_RETRYABLE = ("interrupted", "failed", "cancelled", "completed_with_errors")


class JobRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def create(
        self,
        *,
        kind: str,
        session_id: str | None,
        params: dict[str, Any],
        total_items: int = 0,
        items: Iterable[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Inserta `operations` y `jobs` en la misma transacción."""
        job_id = str(uuid.uuid4())
        operation_id = str(uuid.uuid4())
        stamp = now_iso()
        with self.db.transaction(immediate=True) as conn:
            conn.execute(
                "INSERT INTO operations (id, session_id, kind, params_json, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (operation_id, session_id, kind, dumps(params), stamp),
            )
            conn.execute(
                "INSERT INTO jobs (id, operation_id, kind, status, params_json, progress, stage,"
                " total_items, done_items, error_count, errors_json, created_at, cancel_requested)"
                " VALUES (?, ?, ?, 'queued', ?, 0, 'queued', ?, 0, 0, '[]', ?, 0)",
                (job_id, operation_id, kind, dumps(params), total_items, stamp),
            )
            if items:
                self._insert_items(conn, job_id, items)
        return self.get(job_id)  # type: ignore[return-value]

    def get(self, job_id: str) -> dict[str, Any] | None:
        row = self.db.connect().execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return None
        job = self._row(row)
        job["items"] = self.items(job_id)
        return job

    def list(self, *, statuses: Iterable[str] | None = None, limit: int = 50) -> list[dict[str, Any]]:
        params: list[Any] = []
        query = "SELECT * FROM jobs"
        if statuses:
            values = [status for status in statuses if status]
            if values:
                placeholders = ",".join("?" for _ in values)
                query += f" WHERE status IN ({placeholders})"
                params.extend(values)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = self.db.connect().execute(query, params).fetchall()
        return [self._row(row) for row in rows]

    def items(self, job_id: str) -> list[dict[str, Any]]:
        rows = self.db.connect().execute(
            "SELECT idx, label, status, output_path, message FROM job_items"
            " WHERE job_id = ? ORDER BY idx",
            (job_id,),
        ).fetchall()
        return [
            {
                "index": int(row["idx"]),
                "label": row["label"],
                "status": row["status"],
                "output_path": row["output_path"],
                "message": row["message"],
            }
            for row in rows
        ]

    def claim_next(self) -> dict[str, Any] | None:
        with self.db.transaction(immediate=True) as conn:
            row = conn.execute(
                "SELECT id FROM jobs WHERE status = 'queued' ORDER BY created_at, id LIMIT 1"
            ).fetchone()
            if not row:
                return None
            job_id = row["id"]
            conn.execute(
                "UPDATE jobs SET status = 'running', stage = 'starting', progress = 0,"
                " started_at = ?, errors_json = '[]', error_count = 0 WHERE id = ?",
                (now_iso(), job_id),
            )
        return self.get(job_id)

    def update(self, job_id: str, **fields: Any) -> None:
        assignments: list[str] = []
        values: list[Any] = []
        for key, value in fields.items():
            if key == "errors":
                key, value = "errors_json", dumps(value)
            elif key == "output":
                key, value = "output_json", dumps(value)
            elif key == "params":
                key, value = "params_json", dumps(value)
            elif key == "cancel_requested":
                value = int(bool(value))
            if key not in {
                "status",
                "progress",
                "stage",
                "total_items",
                "done_items",
                "error_count",
                "errors_json",
                "output_json",
                "params_json",
                "started_at",
                "finished_at",
                "cancel_requested",
            }:
                continue
            assignments.append(f"{key} = ?")
            values.append(value)
        if not assignments:
            return
        values.append(job_id)
        with self.db.transaction() as conn:
            conn.execute(f"UPDATE jobs SET {', '.join(assignments)} WHERE id = ?", values)

    def set_progress(
        self,
        job_id: str,
        *,
        progress: float,
        stage: str | None = None,
        done_items: int | None = None,
        total_items: int | None = None,
    ) -> None:
        fields: dict[str, Any] = {"progress": max(0.0, min(100.0, float(progress)))}
        if stage is not None:
            fields["stage"] = stage
        if done_items is not None:
            fields["done_items"] = int(done_items)
        if total_items is not None:
            fields["total_items"] = int(total_items)
        self.update(job_id, **fields)

    def set_item(
        self,
        job_id: str,
        index: int,
        label: str,
        status: str,
        *,
        output_path: str | None = None,
        message: str | None = None,
    ) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO job_items (job_id, idx, label, status, output_path, message)"
                " VALUES (?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(job_id, idx) DO UPDATE SET label = excluded.label,"
                " status = excluded.status, output_path = excluded.output_path,"
                " message = excluded.message",
                (job_id, index, label, status, output_path, message),
            )

    def replace_items(self, job_id: str, items: Iterable[dict[str, Any]]) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM job_items WHERE job_id = ?", (job_id,))
            self._insert_items(conn, job_id, items)

    def finish(
        self,
        job_id: str,
        *,
        status: str,
        output: dict[str, Any] | None = None,
        errors: list[dict[str, Any]] | None = None,
        progress: float | None = None,
        error_count: int | None = None,
    ) -> None:
        error_list = errors or []
        fields: dict[str, Any] = {
            "status": status,
            "finished_at": now_iso(),
            "errors": error_list,
            "error_count": len(error_list) if error_count is None else error_count,
        }
        if output is not None:
            fields["output"] = output
        if progress is not None:
            fields["progress"] = max(0.0, min(100.0, float(progress)))
        self.update(job_id, **fields)

    def request_cancel(self, job_id: str) -> bool:
        row = self.db.connect().execute("SELECT status FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return False
        if row["status"] in FINAL_STATUSES:
            return True
        self.update(job_id, cancel_requested=1)
        return True

    def is_cancel_requested(self, job_id: str) -> bool:
        row = self.db.connect().execute(
            "SELECT cancel_requested FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
        return bool(row and row["cancel_requested"])

    def recover_interrupted(self) -> int:
        """Marca como `interrupted` los jobs que quedaron `running` tras un cierre."""
        with self.db.transaction(immediate=True) as conn:
            cur = conn.execute(
                "UPDATE jobs SET status = 'interrupted', stage = 'interrupted', finished_at = ?"
                " WHERE status = 'running'",
                (now_iso(),),
            )
        return cur.rowcount

    def requeue(self, job_id: str) -> bool:
        row = self.db.connect().execute("SELECT status FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row or row["status"] not in _RETRYABLE:
            return False
        with self.db.transaction(immediate=True) as conn:
            conn.execute("DELETE FROM job_items WHERE job_id = ?", (job_id,))
            conn.execute(
                "UPDATE jobs SET status = 'queued', stage = 'queued', progress = 0,"
                " total_items = 0, done_items = 0, error_count = 0, errors_json = '[]',"
                " output_json = NULL, started_at = NULL, finished_at = NULL, cancel_requested = 0"
                " WHERE id = ?",
                (job_id,),
            )
        return True

    def session_id(self, job_id: str) -> str | None:
        row = self.db.connect().execute(
            "SELECT o.session_id FROM jobs j JOIN operations o ON o.id = j.operation_id"
            " WHERE j.id = ?",
            (job_id,),
        ).fetchone()
        return row["session_id"] if row else None

    def all_output_paths(self, limit: int = 500) -> list[str]:
        rows = self.db.connect().execute(
            "SELECT output_json FROM jobs WHERE output_json IS NOT NULL"
            " ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        paths: list[str] = []
        for row in rows:
            output = loads(row["output_json"], {})
            if isinstance(output, dict) and output.get("output_path"):
                paths.append(str(output["output_path"]))
        return paths

    @staticmethod
    def _insert_items(conn, job_id: str, items: Iterable[dict[str, Any]]) -> None:
        conn.executemany(
            "INSERT INTO job_items (job_id, idx, label, status, output_path, message)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    job_id,
                    int(item["index"]),
                    item.get("label", ""),
                    item.get("status", "pending"),
                    item.get("output_path"),
                    item.get("message"),
                )
                for item in items
            ],
        )

    @staticmethod
    def _row(row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "job_id": row["id"],
            "operation_id": row["operation_id"],
            "kind": row["kind"],
            "status": row["status"],
            "params": loads(row["params_json"], {}),
            "output": loads(row["output_json"], None),
            "progress": float(row["progress"]),
            "stage": row["stage"],
            "total_items": int(row["total_items"]),
            "done_items": int(row["done_items"]),
            "error_count": int(row["error_count"]),
            "errors": loads(row["errors_json"], []),
            "created_at": row["created_at"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "cancel_requested": bool(row["cancel_requested"]),
        }
