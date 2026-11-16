from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db.connection import Database


class RulesRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def list_rules(self) -> list[dict[str, Any]]:
        rows = self.db.connect().execute("SELECT * FROM rules ORDER BY created_at DESC").fetchall()
        return [self._rule_row(row) for row in rows]

    def get_rule(self, rule_id: str) -> dict[str, Any] | None:
        row = self.db.connect().execute("SELECT * FROM rules WHERE id = ?", (rule_id,)).fetchone()
        return self._rule_row(row) if row else None

    def add_rule(self, name: str, kind: str, params: dict[str, Any]) -> dict[str, Any]:
        rule_id = str(uuid.uuid4())
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO rules (id, name, kind, params_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (rule_id, name, kind, json.dumps(params, ensure_ascii=False), self._now()),
            )
        return self.get_rule(rule_id)  # type: ignore[return-value]

    def delete_rule(self, rule_id: str) -> bool:
        with self.db.transaction() as conn:
            cur = conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
        return cur.rowcount > 0

    def list_profiles(self) -> list[dict[str, Any]]:
        rows = self.db.connect().execute("SELECT * FROM profiles ORDER BY created_at DESC").fetchall()
        return [self._profile_row(row) for row in rows]

    def add_profile(self, name: str, params: dict[str, Any]) -> dict[str, Any]:
        profile_id = str(uuid.uuid4())
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO profiles (id, name, params_json, created_at) VALUES (?, ?, ?, ?)",
                (profile_id, name, json.dumps(params, ensure_ascii=False), self._now()),
            )
        row = self.db.connect().execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
        return self._profile_row(row)  # type: ignore[return-value]

    def delete_profile(self, profile_id: str) -> bool:
        with self.db.transaction() as conn:
            cur = conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        return cur.rowcount > 0

    def list_watched(self) -> list[dict[str, Any]]:
        rows = self.db.connect().execute("SELECT * FROM watched_folders ORDER BY created_at DESC").fetchall()
        return [{"id": r["id"], "path": r["path"], "active": bool(r["active"]), "created_at": r["created_at"]} for r in rows]

    def add_watched(self, path: str) -> dict[str, Any]:
        fid = str(uuid.uuid4())
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT INTO watched_folders (id, path, active, created_at) VALUES (?, ?, 1, ?)",
                (fid, path, self._now()),
            )
        return {"id": fid, "path": path, "active": True, "created_at": self._now()}

    def set_watched_active(self, fid: str, active: bool) -> bool:
        with self.db.transaction() as conn:
            cur = conn.execute("UPDATE watched_folders SET active = ? WHERE id = ?", (int(active), fid))
        return cur.rowcount > 0

    def delete_watched(self, fid: str) -> bool:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM watch_state WHERE folder_id = ?", (fid,))
            cur = conn.execute("DELETE FROM watched_folders WHERE id = ?", (fid,))
        return cur.rowcount > 0

    def is_processed(self, folder_id: str, file_path: str) -> bool:
        row = self.db.connect().execute(
            "SELECT 1 FROM watch_state WHERE folder_id = ? AND file_path = ?", (folder_id, file_path)
        ).fetchone()
        return row is not None

    def mark_processed(self, folder_id: str, file_path: str) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO watch_state (folder_id, file_path, processed_at) VALUES (?, ?, ?)",
                (folder_id, file_path, self._now()),
            )

    def _rule_row(self, row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "kind": row["kind"],
            "params": json.loads(row["params_json"]),
            "created_at": row["created_at"],
        }

    def _profile_row(self, row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "params": json.loads(row["params_json"]),
            "created_at": row["created_at"],
        }
