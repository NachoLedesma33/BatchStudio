from __future__ import annotations

from typing import Any

from app.db.connection import Database
from app.db.repositories._common import dumps, loads, now_iso


class SettingsRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get(self, key: str, default: Any = None) -> Any:
        row = self.db.connect().execute(
            "SELECT value_json FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return loads(row["value_json"], default) if row else default

    def set(self, key: str, value: Any) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO settings (key, value_json, updated_at) VALUES (?, ?, ?)"
                " ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json,"
                " updated_at = excluded.updated_at",
                (key, dumps(value), now_iso()),
            )

    def delete(self, key: str) -> bool:
        with self.db.transaction() as conn:
            cur = conn.execute("DELETE FROM settings WHERE key = ?", (key,))
        return cur.rowcount > 0
