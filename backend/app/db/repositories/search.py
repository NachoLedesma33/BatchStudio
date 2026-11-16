from __future__ import annotations

from typing import Any

from app.db.connection import Database


class SearchRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def index_document(self, session_id: str, doc_id: str, name: str, pages_text: list[tuple[int, str]]) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM search_index WHERE doc_id = ? AND session_id = ?", (doc_id, session_id))
            conn.executemany(
                "INSERT INTO search_index (doc_id, session_id, page_no, name, content) VALUES (?, ?, ?, ?, ?)",
                [(doc_id, session_id, page_no, name, text) for page_no, text in pages_text],
            )

    def search(self, session_id: str, query: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.db.connect().execute(
            "SELECT doc_id, page_no, name, snippet(search_index, 4, '[', ']', '...', 12) AS snippet"
            " FROM search_index WHERE session_id = ? AND search_index MATCH ?"
            " ORDER BY rank LIMIT ?",
            (session_id, query, limit),
        ).fetchall()
        return [
            {
                "doc_id": row["doc_id"],
                "page_no": int(row["page_no"]),
                "name": row["name"],
                "snippet": row["snippet"],
            }
            for row in rows
        ]

    def clear(self, session_id: str | None = None) -> None:
        with self.db.transaction() as conn:
            if session_id is None:
                conn.execute("DELETE FROM search_index")
            else:
                conn.execute("DELETE FROM search_index WHERE session_id = ?", (session_id,))

    def count(self, session_id: str | None = None) -> int:
        if session_id is None:
            row = self.db.connect().execute("SELECT COUNT(*) AS total FROM search_index").fetchone()
        else:
            row = self.db.connect().execute("SELECT COUNT(*) AS total FROM search_index WHERE session_id = ?", (session_id,)).fetchone()
        return int(row["total"])
