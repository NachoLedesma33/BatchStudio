from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import get_services, get_session_id
from app.core.errors import ApiError
from app.services.container import Services

router = APIRouter(prefix="/api", tags=["rename"])


class RenameRequest(BaseModel):
    find: str = ""
    replace: str = ""
    use_regex: bool = False
    scope: str = "included"  # included | all


class RenameItem(BaseModel):
    id: str
    old_name: str
    new_name: str
    conflict: bool = False


class RenamePreviewResponse(BaseModel):
    items: list[RenameItem] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)


def _target_docs(services: Services, session_id: str, scope: str):
    docs = services.documents.list(session_id)
    if scope == "included":
        docs = [d for d in docs if d.included]
    return docs


def _new_name(name: str, find: str, replace: str, use_regex: bool) -> str:
    if not find:
        return name
    if use_regex:
        try:
            return re.sub(find, replace, name)
        except re.error:
            return name
    return name.replace(find, replace)


@router.post("/rename/preview")
def rename_preview(
    req: RenameRequest,
    session_id: str = Depends(get_session_id),
    services: Services = Depends(get_services),
):
    docs = _target_docs(services, session_id, req.scope)
    proposed: list[dict[str, Any]] = []
    names: dict[str, int] = {}
    for doc in docs:
        new = _new_name(doc.name, req.find, req.replace, req.use_regex)
        proposed.append({"id": doc.id, "old_name": doc.name, "new_name": new})
        names[new] = names.get(new, 0) + 1

    conflicts = [name for name, count in names.items() if count > 1]
    items = [
        {"id": p["id"], "old_name": p["old_name"], "new_name": p["new_name"], "conflict": p["new_name"] in conflicts}
        for p in proposed
    ]
    return {"items": items, "conflicts": conflicts}


@router.post("/rename/apply")
def rename_apply(
    req: RenameRequest,
    session_id: str = Depends(get_session_id),
    services: Services = Depends(get_services),
):
    docs = _target_docs(services, session_id, req.scope)
    proposed = []
    names: dict[str, int] = {}
    for doc in docs:
        new = _new_name(doc.name, req.find, req.replace, req.use_regex)
        proposed.append((doc, new))
        names[new] = names.get(new, 0) + 1
    conflicts = {name for name, count in names.items() if count > 1}
    if conflicts:
        raise ApiError(
            "RENAME_CONFLICT",
            "Hay nombres duplicados tras el renombrado. Ajustá el patrón.",
            status_code=409,
            context={"conflicts": sorted(conflicts)},
        )

    updated = 0
    for doc, new in proposed:
        if new and new != doc.name:
            services.documents.update(doc.id, name=new)
            updated += 1
    return {"updated": updated, "conflicts": []}
