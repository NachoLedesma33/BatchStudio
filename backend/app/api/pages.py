from __future__ import annotations

from typing import Any, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import get_services, get_session_id
from app.core.errors import ApiError
from app.services.container import Services

router = APIRouter(prefix="/api", tags=["pages"])


class PageState(BaseModel):
    page_no: int
    page_order: int | None = None
    rotation: int | None = None
    excluded: bool | None = None


class ReplacePagesRequest(BaseModel):
    pages: List[PageState] = Field(default_factory=list)


class PatchPageRequest(BaseModel):
    page_order: int | None = None
    rotation: int | None = None
    excluded: bool | None = None


def _doc(services: Services, session_id: str, document_id: str):
    for doc in services.documents.list(session_id):
        if doc.id == document_id:
            return doc
    return None


@router.get("/documents/{document_id}/pages")
def list_pages(
    document_id: str,
    session_id: str = Depends(get_session_id),
    services: Services = Depends(get_services),
):
    doc = _doc(services, session_id, document_id)
    if doc is None:
        raise ApiError("DOCUMENT_NOT_FOUND", "El documento no existe en el lote.", status_code=404)
    services.pages.ensure_default(document_id, doc.page_count)
    return {"document_id": document_id, "pages": services.pages.list(document_id)}


@router.put("/documents/{document_id}/pages")
def replace_pages(
    document_id: str,
    req: ReplacePagesRequest,
    session_id: str = Depends(get_session_id),
    services: Services = Depends(get_services),
):
    doc = _doc(services, session_id, document_id)
    if doc is None:
        raise ApiError("DOCUMENT_NOT_FOUND", "El documento no existe en el lote.", status_code=404)
    payload = [page.model_dump(exclude_none=True) for page in req.pages]
    services.pages.replace(document_id, payload)
    return {"document_id": document_id, "pages": services.pages.list(document_id)}


@router.patch("/documents/{document_id}/pages/{page_no}")
def patch_page(
    document_id: str,
    page_no: int,
    req: PatchPageRequest,
    session_id: str = Depends(get_session_id),
    services: Services = Depends(get_services),
):
    doc = _doc(services, session_id, document_id)
    if doc is None:
        raise ApiError("DOCUMENT_NOT_FOUND", "El documento no existe en el lote.", status_code=404)
    fields = req.model_dump(exclude_none=True)
    ok = services.pages.set_page(document_id, page_no, **fields)
    if not ok:
        raise ApiError("PAGE_NOT_FOUND", "La página no existe.", status_code=404)
    return {"document_id": document_id, "page_no": page_no, "updated": True}
