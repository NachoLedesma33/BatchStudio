from __future__ import annotations

import hmac
import secrets
from urllib.parse import urlsplit

from fastapi import Request
from fastapi.responses import JSONResponse

LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def new_token() -> str:
    """Token por ejecución. Se entrega a la UI por el fragmento de la URL."""
    return secrets.token_urlsafe(32)


def _http_error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": {"code": code, "message": message, "hint": None, "context": {}}},
    )


def _is_loopback_origin(origin: str) -> bool:
    try:
        parts = urlsplit(origin)
    except ValueError:
        return False
    if parts.scheme not in {"http", "https"}:
        return False
    return (parts.hostname or "").lower() in LOOPBACK_HOSTS


def _is_loopback_host(host_header: str) -> bool:
    if not host_header:
        return False
    host = host_header.strip()
    if host.startswith("["):
        # IPv6 literal: [::1]:8765
        host = host[1:].split("]", 1)[0]
    else:
        host = host.rsplit(":", 1)[0] if host.count(":") == 1 else host
    return host.lower() in LOOPBACK_HOSTS


def _request_token(request: Request) -> str | None:
    token = request.headers.get("x-pdfbs-token")
    if token:
        return token.strip()
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.query_params.get("token")


def install_security_middleware(
    app,
    *,
    token: str,
    require_token: bool,
    strict_host: bool,
) -> None:
    """Protege `/api` con token local y rechaza orígenes/hosts ajenos.

    - Sin token (o token incorrecto) → 401.
    - `Origin` que no sea loopback → 403.
    - `Host` que no sea loopback (cuando `strict_host`) → 403.
    - Los preflight CORS y los archivos estáticos no se bloquean.
    """

    @app.middleware("http")
    async def _security(request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)

        origin = request.headers.get("origin")
        if origin and not _is_loopback_origin(origin):
            return _http_error(403, "ORIGIN_NOT_ALLOWED", "El origen de la petición no está permitido.")

        if strict_host and not _is_loopback_host(request.headers.get("host", "")):
            return _http_error(403, "HOST_NOT_ALLOWED", "El host de la petición no está permitido.")

        if request.url.path.startswith("/api"):
            if request.url.path == "/api/health":
                return await call_next(request)
            if require_token:
                supplied = _request_token(request)
                if not supplied or not hmac.compare_digest(supplied, token):
                    return _http_error(
                        401,
                        "TOKEN_REQUIRED",
                        "Falta el token local o no es válido. Abrí la aplicación desde el acceso directo.",
                    )

        return await call_next(request)
