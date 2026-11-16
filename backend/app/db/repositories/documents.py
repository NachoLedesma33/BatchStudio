from __future__ import annotations

from typing import Any, Iterable

from app.db.connection import Database
from app.db.repositories._common import dumps, loads
from app.models.document import PdfDocument, PdfStatus

_UPDATABLE = {
    "name": "original_name",
    "path": "path",
    "size_bytes": "size_bytes",
    "page_count": "page_count",
    "sha256": "sha256",
    "status": "status",
    "error_message": "error_message",
    "included": "included",
    "order_index": "order_index",
    "managed_copy": "managed_copy",
}


class DocumentRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def upsert(self, session_id: str, doc: PdfDocument, *, managed_copy: bool = False) -> PdfDocument:
        """Inserta o actualiza por (sesión, ruta), conservando id, orden e inclusión."""
        conn = self.db.connect()
        existing = conn.execute(
            "SELECT id FROM session_documents WHERE session_id = ? AND path = ?",
            (session_id, doc.path),
        ).fetchone()
        with self.db.transaction() as tx:
            if existing:
                tx.execute(
                    "UPDATE session_documents SET original_name = ?, size_bytes = ?, page_count = ?,"
                    " sha256 = ?, status = ?, error_message = ?, metadata_json = ?, managed_copy = ?"
                    " WHERE id = ?",
                    (
                        doc.name,
                        doc.size_bytes,
                        doc.page_count,
                        doc.sha256,
                        doc.status.value,
                        doc.error_message,
                        dumps(doc.metadata),
                        int(managed_copy),
                        existing["id"],
                    ),
                )
                doc_id = existing["id"]
            else:
                row = tx.execute(
                    "SELECT COALESCE(MAX(order_index) + 1, 0) AS next_order"
                    " FROM session_documents WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
                order_index = int(row["next_order"])
                tx.execute(
                    "INSERT INTO session_documents (id, session_id, path, original_name, size_bytes,"
                    " page_count, sha256, status, error_message, included, order_index, managed_copy,"
                    " metadata_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        doc.id,
                        session_id,
                        doc.path,
                        doc.name,
                        doc.size_bytes,
                        doc.page_count,
                        doc.sha256,
                        doc.status.value,
                        doc.error_message,
                        int(doc.included),
                        order_index,
                        int(managed_copy),
                        dumps(doc.metadata),
                    ),
                )
                doc_id = doc.id
        return self.get(doc_id)  # type: ignore[return-value]

    def get(self, document_id: str) -> PdfDocument | None:
        row = self.db.connect().execute(
            "SELECT * FROM session_documents WHERE id = ?", (document_id,)
        ).fetchone()
        return self._row(row) if row else None

    def get_with_session(self, document_id: str) -> tuple[str, PdfDocument] | None:
        row = self.db.connect().execute(
            "SELECT * FROM session_documents WHERE id = ?", (document_id,)
        ).fetchone()
        if not row:
            return None
        return row["session_id"], self._row(row)

    def find_by_path(self, session_id: str, path: str) -> PdfDocument | None:
        row = self.db.connect().execute(
            "SELECT * FROM session_documents WHERE session_id = ? AND path = ?",
            (session_id, path),
        ).fetchone()
        return self._row(row) if row else None

    def list(self, session_id: str) -> list[PdfDocument]:
        rows = self.db.connect().execute(
            "SELECT * FROM session_documents WHERE session_id = ? ORDER BY order_index, id",
            (session_id,),
        ).fetchall()
        return [self._row(row) for row in rows]

    def update(self, document_id: str, **fields: Any) -> PdfDocument | None:
        assignments: list[str] = []
        values: list[Any] = []
        for key, value in fields.items():
            column = _UPDATABLE.get(key)
            if column is None or value is None and key != "error_message":
                continue
            if key == "status":
                value = value.value if isinstance(value, PdfStatus) else str(value)
            elif key == "included":
                value = int(bool(value))
            elif key == "managed_copy":
                value = int(bool(value))
            assignments.append(f"{column} = ?")
            values.append(value)
        if not assignments:
            return self.get(document_id)
        values.append(document_id)
        with self.db.transaction() as conn:
            conn.execute(
                f"UPDATE session_documents SET {', '.join(assignments)} WHERE id = ?", values
            )
        return self.get(document_id)

    def remove(self, document_id: str) -> bool:
        row = self.db.connect().execute(
            "SELECT session_id FROM session_documents WHERE id = ?", (document_id,)
        ).fetchone()
        if not row:
            return False
        with self.db.transaction() as conn:
            cur = conn.execute("DELETE FROM session_documents WHERE id = ?", (document_id,))
        if cur.rowcount > 0:
            self._reindex_session(row["session_id"])
            return True
        return False

    def clear(self, session_id: str) -> int:
        with self.db.transaction() as conn:
            cur = conn.execute("DELETE FROM session_documents WHERE session_id = ?", (session_id,))
        return cur.rowcount

    def reorder(self, session_id: str, ids: Iterable[str]) -> bool:
        ordered = list(ids)
        current = [doc.id for doc in self.list(session_id)]
        if len(ordered) != len(current) or set(ordered) != set(current):
            return False
        with self.db.transaction() as conn:
            for index, document_id in enumerate(ordered):
                conn.execute(
                    "UPDATE session_documents SET order_index = ? WHERE id = ? AND session_id = ?",
                    (index, document_id, session_id),
                )
        return True

    def count(self, session_id: str) -> int:
        row = self.db.connect().execute(
            "SELECT COUNT(*) AS total FROM session_documents WHERE session_id = ?", (session_id,)
        ).fetchone()
        return int(row["total"])

    def all_paths(self) -> list[str]:
        rows = self.db.connect().execute("SELECT path FROM session_documents").fetchall()
        return [row["path"] for row in rows]

    def included(self, session_id: str) -> list[PdfDocument]:
        return [doc for doc in self.list(session_id) if doc.included]

    def _reindex_session(self, session_id: str) -> None:
        with self.db.transaction() as conn:
            rows = conn.execute(
                "SELECT id FROM session_documents WHERE session_id = ? ORDER BY order_index, id",
                (session_id,),
            ).fetchall()
            for index, item in enumerate(rows):
                conn.execute(
                    "UPDATE session_documents SET order_index = ? WHERE id = ?", (index, item["id"])
                )

    @staticmethod
    def _row(row) -> PdfDocument:
        try:
            status = PdfStatus(row["status"])
        except ValueError:
            status = PdfStatus.PENDING
        return PdfDocument(
            id=row["id"],
            path=row["path"],
            name=row["original_name"],
            size_bytes=int(row["size_bytes"]),
            page_count=row["page_count"],
            sha256=row["sha256"],
            status=status,
            error_message=row["error_message"],
            included=bool(row["included"]),
            order_index=int(row["order_index"]),
            metadata=loads(row["metadata_json"], {}),
        )
