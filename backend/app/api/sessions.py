from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends

from app.api.deps import get_services, get_session_id
from app.core.errors import ApiError
from app.db.repositories.sessions import DEFAULT_SESSION_ID
from app.models.document import PdfDocument, PdfStatus
from app.schemas.api import CreateSessionRequest, LoadSessionRequest, UpdateSessionRequest
from app.services.container import Services

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("")
def list_sessions(services: Services = Depends(get_services)):
    return {"sessions": services.sessions.list()}


@router.post("")
def create_session(req: CreateSessionRequest, services: Services = Depends(get_services)):
    session = services.sessions.create(req.name or "Sesión sin nombre")
    return session


@router.post("/save")
def save_session_export(
    session_id: str = Depends(get_session_id),
    services: Services = Depends(get_services),
):
    path = services.config.session_dir / f"session_{uuid.uuid4().hex[:8]}.json"
    data = {
        "version": 1,
        "session_id": session_id,
        "documents": [doc.to_dict() for doc in services.documents.list(session_id)],
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"path": str(path)}


@router.post("/load")
def load_session_export(
    req: LoadSessionRequest,
    session_id: str = Depends(get_session_id),
    services: Services = Depends(get_services),
):
    path = Path(req.path).expanduser()
    if not path.is_file():
        raise ApiError("SESSION_FILE_NOT_FOUND", "El archivo de sesión no existe.", status_code=404)
    if len(str(path)) > services.config.max_path_length:
        raise ApiError("PATH_TOO_LONG", "La ruta del archivo de sesión es demasiado larga.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ApiError(
            "SESSION_FILE_INVALID", "El archivo de sesión no es válido.", context={"detail": str(exc)}
        ) from exc

    documents = data.get("documents") if isinstance(data, dict) else None
    if not isinstance(documents, list):
        raise ApiError("SESSION_FILE_INVALID", "El archivo no contiene una lista de documentos.")

    services.documents.clear(session_id)
    for raw in documents:
        if not isinstance(raw, dict):
            continue
        fields = {k: v for k, v in raw.items() if k in PdfDocument.__dataclass_fields__}
        doc = PdfDocument(**fields)
        try:
            doc.status = PdfStatus(raw.get("status", "pending"))
        except ValueError:
            doc.status = PdfStatus.PENDING
        services.documents.upsert(session_id, doc)
    services.sessions.touch(session_id)
    return {"documents": [doc.to_dict() for doc in services.documents.list(session_id)]}


@router.get("/{session_id}")
def get_session(session_id: str, services: Services = Depends(get_services)):
    session = services.sessions.get(session_id)
    if session is None:
        raise ApiError("SESSION_NOT_FOUND", "La sesión no existe.", status_code=404)
    session["documents"] = [doc.to_dict() for doc in services.documents.list(session_id)]
    return session


@router.patch("/{session_id}")
def update_session(
    session_id: str,
    req: UpdateSessionRequest,
    services: Services = Depends(get_services),
):
    if services.sessions.get(session_id) is None:
        raise ApiError("SESSION_NOT_FOUND", "La sesión no existe.", status_code=404)
    if req.name is not None:
        services.sessions.rename(session_id, req.name)
    if req.state is not None:
        services.sessions.update_state(session_id, req.state)
    return services.sessions.get(session_id)


@router.delete("/{session_id}")
def delete_session(session_id: str, services: Services = Depends(get_services)):
    if session_id == DEFAULT_SESSION_ID:
        raise ApiError(
            "DEFAULT_SESSION",
            "La sesión local no se puede eliminar.",
            status_code=400,
        )
    if not services.sessions.delete(session_id):
        raise ApiError("SESSION_NOT_FOUND", "La sesión no existe.", status_code=404)
    return {"ok": True}
