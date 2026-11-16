from __future__ import annotations

from typing import Iterable

from app.operations.base import Operation


class OperationRegistry:
    def __init__(self) -> None:
        self._operations: dict[str, Operation] = {}

    def register(self, operation: Operation) -> None:
        if not operation.kind:
            raise ValueError("La operación no declara `kind`.")
        self._operations[operation.kind] = operation

    def register_many(self, operations: Iterable[Operation]) -> None:
        for operation in operations:
            self.register(operation)

    def get(self, kind: str) -> Operation | None:
        return self._operations.get(kind)

    def require(self, kind: str) -> Operation:
        operation = self.get(kind)
        if operation is None:
            raise KeyError(f"Operación desconocida: {kind}")
        return operation

    def kinds(self) -> list[str]:
        return sorted(self._operations)
