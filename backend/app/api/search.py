from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import get_services, get_session_id
from app.services.container import Services

router = APIRouter(prefix="/api", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    limit: int = 50


@router.post("/search")
def global_search(
    req: SearchRequest,
    session_id: str = Depends(get_session_id),
    services: Services = Depends(get_services),
):
    if not req.query.strip():
        return {"results": []}
    results = services.search.search(session_id, req.query, req.limit)
    return {"results": results}


@router.post("/search/index")
def rebuild_index(
    session_id: str = Depends(get_session_id),
    services: Services = Depends(get_services),
):
    services.search.clear(session_id)
    indexed = 0
    for doc in services.documents.list(session_id):
        if not doc.page_count:
            continue
        import pymupdf

        path = doc.path
        try:
            with pymupdf.open(path) as pdf:
                if pdf.needs_pass:
                    continue
                pages_text = []
                for i in range(pdf.page_count):
                    pages_text.append((i + 1, pdf[i].get_text()))
                services.search.index_document(session_id, doc.id, doc.name, pages_text)
                indexed += 1
        except Exception:
            continue
    return {"indexed": indexed, "total": services.search.count(session_id)}


@router.delete("/search/index")
def clear_index(
    session_id: str = Depends(get_session_id),
    services: Services = Depends(get_services),
):
    services.search.clear(session_id)
    return {"cleared": True}


@router.get("/documents/{document_id}/search")
def document_search(
    document_id: str,
    q: str = Query(..., min_length=1),
    services: Services = Depends(get_services),
    session_id: str = Depends(get_session_id),
):
    doc = None
    for d in services.documents.list(session_id):
        if d.id == document_id:
            doc = d
            break
    if doc is None:
        from app.core.errors import ApiError

        raise ApiError("DOCUMENT_NOT_FOUND", "El documento no existe en el lote.", status_code=404)
    import pymupdf

    results = []
    try:
        with pymupdf.open(doc.path) as pdf:
            if pdf.needs_pass:
                return {"results": []}
            for i in range(pdf.page_count):
                text = pdf[i].get_text()
                if q.lower() in text.lower():
                    idx = text.lower().find(q.lower())
                    start = max(0, idx - 60)
                    end = min(len(text), idx + len(q) + 60)
                    results.append({"page": i + 1, "snippet": text[start:end].replace("\n", " ")})
    except Exception:
        pass
    return {"results": results}
