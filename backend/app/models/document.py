from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


class PdfStatus(str, enum.Enum):
    PENDING = "pending"
    INSPECTING = "inspecting"
    READY = "ready"
    WARNING = "warning"
    INVALID = "invalid"
    PROTECTED = "protected"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PdfDocument:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    path: str = ""
    name: str = ""
    size_bytes: int = 0
    page_count: Optional[int] = None
    sha256: Optional[str] = None
    status: PdfStatus = PdfStatus.PENDING
    error_message: Optional[str] = None
    included: bool = True
    order_index: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "path": self.path,
            "name": self.name,
            "size_bytes": self.size_bytes,
            "page_count": self.page_count,
            "sha256": self.sha256,
            "status": self.status.value,
            "error_message": self.error_message,
            "included": self.included,
            "order_index": self.order_index,
            "metadata": self.metadata,
        }


@dataclass
class MergeError:
    document_id: Optional[str] = None
    path: Optional[str] = None
    message: str = ""
    detail: Optional[str] = None


@dataclass
class MergeResult:
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: str = "pending"
    output_path: Optional[str] = None
    total_pages: int = 0
    processed_documents: int = 0
    error_count: int = 0
    errors: list[MergeError] = field(default_factory=list)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    elapsed_seconds: float = 0.0
    peak_rss_mb: float = 0.0
    cancelled: bool = False

    def to_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "output_path": self.output_path,
            "total_pages": self.total_pages,
            "processed_documents": self.processed_documents,
            "error_count": self.error_count,
            "errors": [
                {
                    "document_id": e.document_id,
                    "path": e.path,
                    "message": e.message,
                    "detail": e.detail,
                }
                for e in self.errors
            ],
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "peak_rss_mb": round(self.peak_rss_mb, 2),
            "cancelled": self.cancelled,
        }
