from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_services, get_session_id
from app.services.container import Services

router = APIRouter(prefix="/api", tags=["settings"])


class SettingValue(BaseModel):
    value: Any


@router.get("/settings")
def get_settings(services: Services = Depends(get_services)):
    # Devuelve todas las claves conocidas? El repo no lista; guardamos un índice.
    keys = services.settings.get("__keys__", [])
    result = {}
    for key in keys:
        result[key] = services.settings.get(key)
    return {"settings": result}


@router.get("/settings/{key}")
def get_setting(key: str, services: Services = Depends(get_services)):
    return {"key": key, "value": services.settings.get(key)}


@router.put("/settings/{key}")
def put_setting(key: str, req: SettingValue, services: Services = Depends(get_services)):
    services.settings.set(key, req.value)
    keys = services.settings.get("__keys__", [])
    if key not in keys:
        keys = [*keys, key]
        services.settings.set("__keys__", keys)
    return {"key": key, "value": req.value}


@router.delete("/settings/{key}")
def delete_setting(key: str, services: Services = Depends(get_services)):
    ok = services.settings.delete(key)
    keys = [k for k in services.settings.get("__keys__", []) if k != key]
    services.settings.set("__keys__", keys)
    return {"key": key, "deleted": ok}
