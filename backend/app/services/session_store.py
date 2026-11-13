from __future__ import annotations

import threading
import uuid
from typing import Dict, List, Optional

from app.models.document import PdfDocument


class DocumentStore:
    def __init__(self) -> None:
        self._docs: Dict[str, PdfDocument] = {}
        self._order: List[str] = []
        self._lock = threading.Lock()

    def add(self, doc: PdfDocument) -> PdfDocument:
        with self._lock:
            if doc.id in self._docs:
                return self._docs[doc.id]
            if not doc.order_index:
                doc.order_index = len(self._order)
            self._docs[doc.id] = doc
            if doc.id not in self._order:
                self._order.append(doc.id)
            return doc

    def get(self, doc_id: str) -> Optional[PdfDocument]:
        with self._lock:
            return self._docs.get(doc_id)

    def list(self) -> List[PdfDocument]:
        with self._lock:
            return [self._docs[i] for i in self._order if i in self._docs]

    def remove(self, doc_id: str) -> bool:
        with self._lock:
            if doc_id in self._docs:
                del self._docs[doc_id]
                self._order = [i for i in self._order if i != doc_id]
                # reindex
                for idx, did in enumerate(self._order):
                    self._docs[did].order_index = idx
                return True
            return False

    def reorder(self, ids: List[str]) -> bool:
        with self._lock:
            if set(ids) != set(self._order):
                # allow subset? require exact set
                if not set(ids).issubset(set(self._order)):
                    return False
                # partial reorder not supported; require all
                if len(ids) != len(self._order):
                    return False
            self._order = list(ids)
            for idx, did in enumerate(self._order):
                if did in self._docs:
                    self._docs[did].order_index = idx
            return True

    def update(self, doc_id: str, **kwargs) -> Optional[PdfDocument]:
        with self._lock:
            d = self._docs.get(doc_id)
            if not d:
                return None
            for k, v in kwargs.items():
                if hasattr(d, k) and v is not None:
                    setattr(d, k, v)
            return d

    def clear(self) -> None:
        with self._lock:
            self._docs.clear()
            self._order.clear()

    def to_list_dict(self) -> List[dict]:
        return [d.to_dict() for d in self.list()]


STORE = DocumentStore()
