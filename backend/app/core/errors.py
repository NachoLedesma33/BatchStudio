from __future__ import annotations

from typing import Any, Optional

from fastapi import Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """Error de API con código estable y mensaje en español."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        hint: Optional[str] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.hint = hint
        self.context = context or {}

    def payload(self) -> dict[str, Any]:
        return {
            "detail": {
                "code": self.code,
                "message": self.message,
                "hint": self.hint,
                "context": self.context,
            }
        }


async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.payload())
