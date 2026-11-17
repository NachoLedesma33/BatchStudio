from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import get_services, get_session_id
from app.core.errors import ApiError
from app.models.document import PdfDocument
from app.schemas.api import (
    ImportFolderRequest,
    ImportPathsRequest,
    ReorderRequest,
    UpdateDocumentRequest,
)
from app.services.container import Services
from app.services.pdf_inspector import inspect_folder, inspect_pdf

router = APIRouter(prefix="/api", tags=["documents"])


@router.get("/documents/{document_id}/blank-pages")
def detect_blank_pages(
    document_id: str,
    threshold: float = 0.01,
    session_id: str = Depends(get_session_id),
    services: Services = Depends(get_services),
):
    doc = None
    for d in services.documents.list(session_id):
        if d.id == document_id:
            doc = d
            break
    if doc is None:
        raise ApiError("DOCUMENT_NOT_FOUND", "El documento no existe en el lote.", status_code=404)
    import pymupdf

    blank = []
    try:
        with pymupdf.open(doc.path) as pdf:
            if pdf.needs_pass:
                raise ApiError("PROTECTED", "El PDF está protegido.", status_code=400)
            for i in range(pdf.page_count):
                page = pdf[i]
                text = page.get_text().strip()
                if text:
                    continue
                pix = page.get_pixmap(matrix=pymupdf.Matrix(0.5, 0.5))
                samples = pix.samples
                # count non-white pixels
                total = pix.width * pix.height
                non_white = 0
                # samples may be RGB/RGBA; check brightness
                for j in range(0, len(samples), pix.n):
                    # if any channel < 250 consider ink
                    if any(samples[j + c] < 250 for c in range(min(3, pix.n))):
                        non_white += 1
                ratio = non_white / max(1, total)
                if ratio < threshold:
                    blank.append(i + 1)
    except ApiError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ApiError("BLANK_DETECT_FAILED", "No se pudieron analizar las páginas.", context={"detail": str(exc)})
    return {"document_id": document_id, "blank_pages": blank, "threshold": threshold}


def _to_dict(doc: PdfDocument) -> dict:
    return doc.to_dict()


@router.get("/documents")
def list_documents(
    session_id: str = Depends(get_session_id),
    services: Services = Depends(get_services),
):
    return {"documents": [doc.to_dict() for doc in services.documents.list(session_id)]}


@router.post("/files/import")
def import_paths(
    req: ImportPathsRequest,
    session_id: str = Depends(get_session_id),
    services: Services = Depends(get_services),
):
    if len(req.paths) > services.config.max_files:
        raise ApiError(
            "TOO_MANY_FILES",
            f"Se superó el máximo de {services.config.max_files} archivos.",
        )
    results = []
    for raw in req.paths:
        if len(str(raw)) > services.config.max_path_length:
            raise ApiError(
                "PATH_TOO_LONG",
                f"La ruta supera el máximo de {services.config.max_path_length} caracteres.",
                context={"path": str(raw)[:200]},
            )
        doc = inspect_pdf(raw)
        saved = services.documents.upsert(session_id, doc)
        results.append(_to_dict(saved))
    services.sessions.touch(session_id)
    return {"documents": results}


@router.post("/folders/import")
def import_folder(
    req: ImportFolderRequest,
    session_id: str = Depends(get_session_id),
    services: Services = Depends(get_services),
):
    folder = services.path_policy.validate_folder(req.folder)
    docs = inspect_folder(str(folder), req.recursive)
    if len(docs) > services.config.max_files:
        raise ApiError(
            "TOO_MANY_FILES",
            f"La carpeta supera el máximo de {services.config.max_files} archivos.",
        )
    results = [
        _to_dict(services.documents.upsert(session_id, doc)) for doc in docs
    ]
    services.sessions.touch(session_id)
    return {"documents": results}


@router.post("/files/upload")
async def upload_files(
    files: list[UploadFile] = File(...),
    session_id: str = Depends(get_session_id),
    services: Services = Depends(get_services),
):
    if len(files) > services.config.max_files:
        raise ApiError(
            "TOO_MANY_FILES", f"Se superó el máximo de {services.config.max_files} archivos."
        )
    results = []
    for upload in files:
        if not upload.filename or not upload.filename.lower().endswith(".pdf"):
            continue
        safe_name = Path(upload.filename).name
        dest = services.config.imports_dir / f"{uuid.uuid4()}_{safe_name}"
        with dest.open("wb") as target:
            shutil.copyfileobj(upload.file, target)
        doc = inspect_pdf(dest)
        doc.metadata["original_name"] = upload.filename
        saved = services.documents.upsert(session_id, doc, managed_copy=True)
        results.append(_to_dict(saved))
    services.sessions.touch(session_id)
    return {"documents": results}


@router.patch("/documents/order")
def reorder_documents(
    req: ReorderRequest,
    session_id: str = Depends(get_session_id),
    services: Services = Depends(get_services),
):
    if not services.documents.reorder(session_id, req.ids):
        raise ApiError(
            "INVALID_ORDER",
            "El orden enviado no coincide con los documentos de la sesión.",
            status_code=400,
        )
    return {"documents": [doc.to_dict() for doc in services.documents.list(session_id)]}


@router.delete("/documents")
def clear_documents(
    session_id: str = Depends(get_session_id),
    services: Services = Depends(get_services),
):
    removed = services.documents.clear(session_id)
    return {"ok": True, "removed": removed}


@router.get("/documents/{doc_id}")
def get_document(doc_id: str, services: Services = Depends(get_services)):
    doc = services.documents.get(doc_id)
    if doc is None:
        raise ApiError("DOCUMENT_NOT_FOUND", "El documento no existe.", status_code=404)
    return _to_dict(doc)


@router.delete("/documents/{doc_id}")
def delete_document(doc_id: str, services: Services = Depends(get_services)):
    if not services.documents.remove(doc_id):
        raise ApiError("DOCUMENT_NOT_FOUND", "El documento no existe.", status_code=404)
    return {"ok": True}


@router.patch("/documents/{doc_id}")
def update_document(
    doc_id: str,
    req: UpdateDocumentRequest,
    services: Services = Depends(get_services),
):
    if services.documents.get(doc_id) is None:
        raise ApiError("DOCUMENT_NOT_FOUND", "El documento no existe.", status_code=404)
    fields = {}
    if req.included is not None:
        fields["included"] = req.included
    if req.name is not None:
        fields["name"] = req.name
    doc = services.documents.update(doc_id, **fields)
    if doc is None:
        raise ApiError("DOCUMENT_NOT_FOUND", "El documento no existe.", status_code=404)
    return _to_dict(doc)


@router.get("/documents/{doc_id}/preview/{page}")
def preview_page(
    doc_id: str,
    page: int,
    scale: float = Query(default=2.0, ge=0.25, le=6.0),
    services: Services = Depends(get_services),
):
    doc = services.documents.get(doc_id)
    if doc is None:
        raise ApiError("DOCUMENT_NOT_FOUND", "El documento no existe.", status_code=404)
    source = Path(doc.path)
    if not source.is_file():
        raise ApiError("FILE_NOT_FOUND", "El archivo del documento ya no existe.", status_code=404)
    try:
        preview = services.previews.render(source, page, scale)
    except ValueError as exc:
        raise ApiError("PAGE_OUT_OF_RANGE", str(exc), status_code=400) from exc
    except Exception as exc:  # noqa: BLE001
        raise ApiError(
            "PREVIEW_FAILED",
            "No se pudo renderizar la página.",
            status_code=500,
            context={"detail": str(exc)},
        ) from exc
    return FileResponse(preview, media_type="image/png")
