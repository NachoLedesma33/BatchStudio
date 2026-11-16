from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_services
from app.services.container import Services

router = APIRouter(prefix="/api", tags=["rules"])


class RuleRequest(BaseModel):
    name: str
    kind: str
    params: dict[str, Any] = {}


class ProfileRequest(BaseModel):
    name: str
    params: dict[str, Any] = {}


class WatchedRequest(BaseModel):
    path: str


class WatchedToggleRequest(BaseModel):
    active: bool


@router.get("/rules")
def list_rules(services: Services = Depends(get_services)):
    return {"rules": services.rules.list_rules()}


@router.post("/rules")
def create_rule(req: RuleRequest, services: Services = Depends(get_services)):
    return services.rules.add_rule(req.name, req.kind, req.params)


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: str, services: Services = Depends(get_services)):
    ok = services.rules.delete_rule(rule_id)
    if not ok:
        from app.core.errors import ApiError

        raise ApiError("RULE_NOT_FOUND", "La regla no existe.", status_code=404)
    return {"deleted": True}


@router.get("/profiles")
def list_profiles(services: Services = Depends(get_services)):
    return {"profiles": services.rules.list_profiles()}


@router.post("/profiles")
def create_profile(req: ProfileRequest, services: Services = Depends(get_services)):
    return services.rules.add_profile(req.name, req.params)


@router.delete("/profiles/{profile_id}")
def delete_profile(profile_id: str, services: Services = Depends(get_services)):
    ok = services.rules.delete_profile(profile_id)
    if not ok:
        from app.core.errors import ApiError

        raise ApiError("PROFILE_NOT_FOUND", "El perfil no existe.", status_code=404)
    return {"deleted": True}


@router.get("/watched")
def list_watched(services: Services = Depends(get_services)):
    return {"watched": services.rules.list_watched()}


@router.post("/watched")
def add_watched(req: WatchedRequest, services: Services = Depends(get_services)):
    return services.rules.add_watched(req.path)


@router.patch("/watched/{folder_id}")
def toggle_watched(folder_id: str, req: WatchedToggleRequest, services: Services = Depends(get_services)):
    ok = services.rules.set_watched_active(folder_id, req.active)
    if not ok:
        from app.core.errors import ApiError

        raise ApiError("WATCHED_NOT_FOUND", "La carpeta vigilada no existe.", status_code=404)
    return {"id": folder_id, "active": req.active}


@router.delete("/watched/{folder_id}")
def delete_watched(folder_id: str, services: Services = Depends(get_services)):
    ok = services.rules.delete_watched(folder_id)
    if not ok:
        from app.core.errors import ApiError

        raise ApiError("WATCHED_NOT_FOUND", "La carpeta vigilada no existe.", status_code=404)
    return {"deleted": True}
