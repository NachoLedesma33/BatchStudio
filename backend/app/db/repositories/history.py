from __future__ import annotations

import uuid
from typing import Any

from app.db.connection import Database
from app.db.repositories._common import dumps, loads, now_iso


class HistoryRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(
        self,
        *,
        job_id: str | None,
        kind: str,
        summary: str,
        inputs: list[Any] | dict[str, Any],
        outputs: list[Any] | dict[str, Any],
    ) -> dict[str, Any]:
        history_id = str(uuid.uuid4())
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO history (id, job_id, kind, summary, inputs_json, outputs_json, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    history_id,
                    job_id,
                    kind,
                    summary,
                    dumps(inputs),
                    dumps(outputs),
                    now_iso(),
                ),
            )
        return self.get(history_id)  # type: ignore[return-value]

    def get(self, history_id: str) -> dict[str, Any] | None:
        row = self.db.connect().execute("SELECT * FROM history WHERE id = ?", (history_id,)).fetchone()
        return self._row(row) if row else None

    def list(self, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.db.connect().execute(
            "SELECT * FROM history ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [self._row(row) for row in rows]

    @staticmethod
    def _row(row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "job_id": row["job_id"],
            "kind": row["kind"],
            "summary": row["summary"],
            "inputs": loads(row["inputs_json"], []),
            "outputs": loads(row["outputs_json"], []),
            "created_at": row["created_at"],
        }
