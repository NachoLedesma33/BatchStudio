from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_services, get_session_id
from app.core.errors import ApiError
from app.schemas.api import PreviewRequest
from app.services.container import Services

router = APIRouter(prefix="/api/operations", tags=["operations"])


@router.get("/kinds")
def operation_kinds(services: Services = Depends(get_services)):
    return {"kinds": services.registry.kinds()}


@router.post("/preview")
def preview_operation(
    req: PreviewRequest,
    session_id: str = Depends(get_session_id),
    services: Services = Depends(get_services),
):
    operation = services.registry.get(req.kind)
    if operation is None:
        raise ApiError(
            "UNKNOWN_OPERATION",
            f"La operación «{req.kind}» no existe.",
            status_code=404,
            hint=f"Operaciones disponibles: {', '.join(services.registry.kinds())}.",
        )
    plan = operation.plan(session_id, req.params or {})
    return plan.to_dict()
