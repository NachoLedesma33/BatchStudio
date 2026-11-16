from __future__ import annotations

from typing import Iterable

from app.db.connection import Database


class PageRepository:
    """Estado de páginas por documento.

    Las filas se materializan de forma perezosa: `ensure_default` solo se llama
    cuando el organizador visual necesita el modelo completo.
    """

    def __init__(self, db: Database) -> None:
        self.db = db

    def ensure_default(self, document_id: str, page_count: int | None) -> None:
        if not page_count or page_count < 1:
            return
        with self.db.transaction() as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO document_pages (document_id, page_no, page_order, rotation, excluded)"
                " VALUES (?, ?, ?, 0, 0)",
                [(document_id, page_no, page_no - 1) for page_no in range(1, page_count + 1)],
            )

    def list(self, document_id: str) -> list[dict]:
        rows = self.db.connect().execute(
            "SELECT page_no, page_order, rotation, excluded FROM document_pages"
            " WHERE document_id = ? ORDER BY page_order",
            (document_id,),
        ).fetchall()
        return [
            {
                "page_no": int(row["page_no"]),
                "page_order": int(row["page_order"]),
                "rotation": int(row["rotation"]),
                "excluded": bool(row["excluded"]),
            }
            for row in rows
        ]

    def replace(self, document_id: str, pages: Iterable[dict]) -> None:
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM document_pages WHERE document_id = ?", (document_id,))
            conn.executemany(
                "INSERT INTO document_pages (document_id, page_no, page_order, rotation, excluded)"
                " VALUES (?, ?, ?, ?, ?)",
                [
                    (
                        document_id,
                        int(page["page_no"]),
                        int(page.get("page_order", index)),
                        int(page.get("rotation", 0)),
                        int(bool(page.get("excluded", False))),
                    )
                    for index, page in enumerate(pages)
                ],
            )

    def set_page(self, document_id: str, page_no: int, **fields) -> bool:
        allowed = {"page_order", "rotation", "excluded"}
        assignments: list[str] = []
        values: list[object] = []
        for key, value in fields.items():
            if key not in allowed:
                continue
            assignments.append(f"{key} = ?")
            values.append(int(value) if key != "rotation" else int(value))
        if not assignments:
            return False
        values.extend([document_id, page_no])
        with self.db.transaction() as conn:
            cur = conn.execute(
                f"UPDATE document_pages SET {', '.join(assignments)}"
                " WHERE document_id = ? AND page_no = ?",
                values,
            )
        return cur.rowcount > 0

    def count(self, document_id: str) -> int:
        row = self.db.connect().execute(
            "SELECT COUNT(*) AS total FROM document_pages WHERE document_id = ?", (document_id,)
        ).fetchone()
        return int(row["total"])
