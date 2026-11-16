from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_services
from app.services.container import Services

router = APIRouter(prefix="/api", tags=["capabilities"])


@router.get("/capabilities")
def capabilities(
    refresh: bool = False,
    services: Services = Depends(get_services),
):
    return services.capabilities.detect(force=refresh)
