from __future__ import annotations

import shutil
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional


@dataclass
class PlanItem:
    index: int
    label: str
    pages: list[int] | None = None
    exists: bool = False
    output_path: str | None = None
    source_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "label": self.label,
            "pages": self.pages,
            "exists": self.exists,
            "output_path": self.output_path,
            "source_path": self.source_path,
        }


@dataclass
class PlanMessage:
    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


@dataclass
class OperationPlan:
    kind: str
    summary: dict[str, Any] = field(default_factory=dict)
    items: list[PlanItem] = field(default_factory=list)
    warnings: list[PlanMessage] = field(default_factory=list)
    errors: list[PlanMessage] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "summary": self.summary,
            "items": [item.to_dict() for item in self.items],
            "warnings": [message.to_dict() for message in self.warnings],
            "errors": [message.to_dict() for message in self.errors],
        }


@dataclass
class ExecutedItem:
    index: int
    label: str
    status: str
    output_path: str | None = None
    message: str | None = None


@dataclass
class OperationResult:
    status: str
    output: dict[str, Any] = field(default_factory=dict)
    items: list[ExecutedItem] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    total_items: int = 0
    total_pages: int = 0
    elapsed_seconds: float = 0.0


ProgressCallback = Callable[..., None]
ItemCallback = Callable[..., None]


class JobContext:
    """Contexto de ejecución: progreso, cancelación y temporales del job."""

    def __init__(
        self,
        *,
        job_id: str,
        session_id: str | None,
        tmp_dir: Path,
        progress: ProgressCallback,
        item: ItemCallback,
        cancel_requested: Callable[[], bool],
    ) -> None:
        self.job_id = job_id
        self.session_id = session_id
        self.tmp_dir = tmp_dir
        self._progress = progress
        self._item = item
        self._cancel_requested = cancel_requested

    @property
    def cancelled(self) -> bool:
        return self._cancel_requested()

    def progress(
        self,
        stage: str,
        percent: float,
        *,
        current: str | None = None,
        done: int | None = None,
        total: int | None = None,
    ) -> None:
        self._progress(stage, percent, current, done, total)

    def item(
        self,
        index: int,
        label: str,
        status: str,
        *,
        output_path: str | None = None,
        message: str | None = None,
    ) -> None:
        self._item(index, label, status, output_path, message)

    def cleanup(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)


class Operation(ABC):
    """Operación real y verificable. El preview nunca escribe."""

    kind: str = ""

    def __init__(self, documents) -> None:
        self.documents = documents

    @abstractmethod
    def plan(self, session_id: str, params: dict[str, Any]) -> OperationPlan:
        """Calcula el plan en el servidor sin escribir nada."""

    @abstractmethod
    def execute(self, plan: OperationPlan, ctx: JobContext, params: dict[str, Any]) -> OperationResult:
        """Ejecuta el plan recalculado por el servidor."""


class CancelProxy:
    """Adaptador duck-typed para APIs que esperan `threading.Event`."""

    def __init__(self, callback: Callable[[], bool]) -> None:
        self._callback = callback

    def is_set(self) -> bool:
        return bool(self._callback())


def is_cancelled(event: Optional[threading.Event | CancelProxy]) -> bool:
    return bool(event is not None and event.is_set())
