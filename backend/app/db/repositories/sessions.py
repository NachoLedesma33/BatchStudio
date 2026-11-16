from __future__ import annotations

import uuid
from typing import Any

from app.db.connection import Database
from app.db.repositories._common import dumps, loads, now_iso

DEFAULT_SESSION_ID = "local"


class SessionRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def ensure_default(self) -> dict[str, Any]:
        existing = self.get(DEFAULT_SESSION_ID)
        if existing:
            return existing
        return self.create(name="Sesión local", session_id=DEFAULT_SESSION_ID)

    def create(self, name: str, session_id: str | None = None) -> dict[str, Any]:
        sid = session_id or str(uuid.uuid4())
        stamp = now_iso()
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO sessions (id, name, created_at, updated_at, last_opened_at, state_json)"
                " VALUES (?, ?, ?, ?, ?, '{}')",
                (sid, name or "Sesión sin nombre", stamp, stamp, stamp),
            )
        return self.get(sid)  # type: ignore[return-value]

    def get(self, session_id: str) -> dict[str, Any] | None:
        row = self.db.connect().execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return self._row(row) if row else None

    def list(self) -> list[dict[str, Any]]:
        rows = self.db.connect().execute("SELECT * FROM sessions ORDER BY created_at").fetchall()
        return [self._row(row) for row in rows]

    def touch(self, session_id: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE sessions SET updated_at = ?, last_opened_at = ? WHERE id = ?",
                (now_iso(), now_iso(), session_id),
            )

    def update_state(self, session_id: str, state: dict[str, Any]) -> bool:
        with self.db.transaction() as conn:
            cur = conn.execute(
                "UPDATE sessions SET state_json = ?, updated_at = ? WHERE id = ?",
                (dumps(state), now_iso(), session_id),
            )
        return cur.rowcount > 0

    def rename(self, session_id: str, name: str) -> bool:
        with self.db.transaction() as conn:
            cur = conn.execute(
                "UPDATE sessions SET name = ?, updated_at = ? WHERE id = ?",
                (name, now_iso(), session_id),
            )
        return cur.rowcount > 0

    def delete(self, session_id: str) -> bool:
        with self.db.transaction() as conn:
            cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        return cur.rowcount > 0

    @staticmethod
    def _row(row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "last_opened_at": row["last_opened_at"],
            "state": loads(row["state_json"], {}),
        }
