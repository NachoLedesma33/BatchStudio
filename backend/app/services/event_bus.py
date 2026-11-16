from __future__ import annotations

import threading
from typing import Any


class EventBus:
    """Eventos efímeros por job para SSE.

    El estado durable sigue en SQLite. Si la app se reinicia, el SSE reconstruye
    el estado desde la base y no depende de este bus.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: dict[str, list[dict[str, Any]]] = {}

    def publish(self, job_id: str, event: dict[str, Any]) -> None:
        with self._lock:
            self._events.setdefault(job_id, []).append(event)

    def since(self, job_id: str, index: int) -> tuple[list[dict[str, Any]], int]:
        with self._lock:
            events = self._events.get(job_id, [])
            return list(events[index:]), len(events)

    def clear(self, job_id: str) -> None:
        with self._lock:
            self._events.pop(job_id, None)
