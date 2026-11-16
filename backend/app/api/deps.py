from __future__ import annotations

from fastapi import Header, Query, Request

from app.db.repositories.sessions import DEFAULT_SESSION_ID
from app.services.container import Services


def get_services(request: Request) -> Services:
    return request.app.state.services


def get_session_id(
    request: Request,
    session_id: str | None = Query(default=None),
    x_session_id: str | None = Header(default=None),
) -> str:
    candidate = session_id or x_session_id or DEFAULT_SESSION_ID
    services: Services = request.app.state.services
    if services.sessions.get(candidate) is None:
        from app.core.errors import ApiError

        raise ApiError("SESSION_NOT_FOUND", "La sesión no existe.", status_code=404)
    return candidate
