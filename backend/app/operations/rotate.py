from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from app.operations.base import (
    ExecutedItem,
    JobContext,
    Operation,
    OperationPlan,
    OperationResult,
    PlanItem,
    PlanMessage,
)
from app.operations.split import (
    COLLISION_POLICIES,
    DEFAULT_COLLISION_POLICY,
    _is_taken,
    _open_source,
    _close_source,
    _read_error,
    _verify_pdf,
    ensure_pdf_suffix,
    render_template,
    sanitize_filename,
    unique_output_path,
)


def _downloads() -> Path:
    downloads = Path.home() / "Downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    return downloads


def _resolve_output_path(params: dict[str, Any], doc, default_stem: str) -> Path:
    raw = str(params.get("output_path") or "").strip()
    if not raw:
        return _downloads() / ensure_pdf_suffix(default_stem)
    path = Path(raw).expanduser()
    if not path.is_absolute() and len(path.parts) == 1:
        return _downloads() / path.name
    return path


def _stem(doc) -> str:
    metadata = getattr(doc, "metadata", None) or {}
    raw = ""
    if isinstance(metadata, dict):
        raw = str(metadata.get("original_name") or "")
    raw = raw or getattr(doc, "name", "") or Path(getattr(doc, "path", "")).name
    base = Path(raw.replace("\\", "/")).name
    stem = base[:-4] if base.lower().endswith(".pdf") else base
    return stem or "documento"


class RotateOperation(Operation):
    kind = "rotate"

    def __init__(self, documents, config=None) -> None:
        super().__init__(documents)
        self.config = config

    def _selected_documents(self, session_id: str, params: dict[str, Any]):
        docs = self.documents.included(session_id)
        requested = params.get("document_ids") or params.get("document_id")
        if requested:
            if isinstance(requested, str):
                requested = [requested]
            wanted = [str(doc_id) for doc_id in requested]
            by_id = {doc.id: doc for doc in docs}
            docs = [by_id[doc_id] for doc_id in wanted if doc_id in by_id]
        return docs

    def plan(self, session_id: str, params: dict[str, Any]) -> OperationPlan:
        docs = self._selected_documents(session_id, params)
        plan = OperationPlan(kind=self.kind)
        if not docs:
            plan.errors.append(PlanMessage("NO_DOCUMENTS", "No hay documentos incluidos en el lote."))
            return plan

        doc = docs[0]
        page_count = doc.page_count or 0
        if page_count < 1:
            plan.errors.append(PlanMessage("NO_PAGES", f"{doc.name}: el documento no tiene páginas."))
            return plan

        try:
            angle = int(params.get("angle", 90))
        except (TypeError, ValueError):
            plan.errors.append(PlanMessage("INVALID_ANGLE", "El ángulo debe ser 90, 180 o 270."))
            return plan
        if angle not in {90, 180, 270, -90, -180, -270}:
            plan.errors.append(PlanMessage("INVALID_ANGLE", "El ángulo debe ser 90, 180 o 270."))
            return plan
        angle = angle % 360

        pages_param = params.get("pages")
        if pages_param is None:
            pages = list(range(1, page_count + 1))
        else:
            try:
                pages = []
                if isinstance(pages_param, str):
                    from app.operations.split import parse_ranges

                    for item in parse_ranges(pages_param, page_count):
                        pages.extend(item.pages)
                elif isinstance(pages_param, (list, tuple)):
                    for value in pages_param:
                        number = int(value)
                        if number < 1 or number > page_count:
                            raise ValueError(f"La página {number} no existe.")
                        pages.append(number)
                else:
                    raise ValueError("Formato de páginas inválido.")
            except Exception as exc:  # noqa: BLE001
                plan.errors.append(PlanMessage("INVALID_PAGES", str(exc)))
                return plan
        if not pages:
            plan.errors.append(PlanMessage("NO_PAGES", "Indicá al menos una página para rotar."))
            return plan

        collision_policy = str(params.get("collision_policy") or DEFAULT_COLLISION_POLICY).lower()
        if collision_policy not in COLLISION_POLICIES:
            plan.errors.append(PlanMessage("INVALID_COLLISION_POLICY", f"La política «{collision_policy}» no existe."))
            return plan

        template = str(params.get("name_template") or "{name}_rotado")
        try:
            rendered = render_template(
                template,
                name=_stem(doc),
                index=1,
                start=pages[0],
                end=pages[-1],
                pages=len(pages),
            )
        except Exception as exc:  # noqa: BLE001
            plan.errors.append(PlanMessage("INVALID_TEMPLATE", str(exc)))
            return plan

        filename, _ = sanitize_filename(ensure_pdf_suffix(rendered))
        target = _resolve_output_path(params, doc, filename)
        if collision_policy == "suffix":
            target = unique_output_path(target, set())
        elif collision_policy == "fail" and _is_taken(target, set()):
            plan.errors.append(PlanMessage("OUTPUT_EXISTS", f"Ya existe un archivo con ese nombre: {target}."))
            return plan

        plan.items.append(
            PlanItem(
                index=1,
                label=target.name,
                pages=pages,
                exists=target.exists(),
                output_path=str(target),
                source_path=doc.path,
            )
        )
        plan.summary = {
            "total_files": 1,
            "total_pages": len(pages),
            "source_files": 1,
            "output_path": str(target),
            "angle": angle,
            "collision_policy": collision_policy,
            "mode": "rotate",
        }
        # guardar el ángulo en params del plan no es posible; se relee en execute
        plan.summary["_angle"] = angle
        return plan

    def execute(self, plan: OperationPlan, ctx: JobContext, params: dict[str, Any]) -> OperationResult:
        executed: list[ExecutedItem] = []
        errors: list[dict[str, Any]] = []
        total_pages = 0
        published = 0
        cancelled = False
        total = len(plan.items)
        policy = str(params.get("collision_policy") or DEFAULT_COLLISION_POLICY).lower()
        angle = int(plan.summary.get("_angle", params.get("angle", 90))) % 360

        by_source: dict[str, list[PlanItem]] = {}
        for item in plan.items:
            by_source.setdefault(item.source_path or "", []).append(item)

        processed = 0
        for source_path, items in by_source.items():
            if cancelled:
                break
            try:
                source = _open_source(source_path)
            except Exception as exc:  # noqa: BLE001
                message = _read_error(exc)
                for item in items:
                    processed += 1
                    ctx.item(item.index, item.label, "failed", message=message)
                    executed.append(ExecutedItem(item.index, item.label, "failed", None, message))
                    errors.append({"path": source_path, "output_path": item.output_path, "message": message})
                continue
            try:
                for item in items:
                    if ctx.cancelled:
                        cancelled = True
                        ctx.item(item.index, item.label, "cancelled", message="Cancelado por el usuario.")
                        executed.append(ExecutedItem(item.index, item.label, "cancelled", None, "Cancelado por el usuario."))
                        break
                    processed += 1
                    ctx.item(item.index, item.label, "processing")
                    target = Path(item.output_path or "")
                    try:
                        target = _reserve_target(target, policy)
                        _rotate_pages(source, item.pages or [], angle, target, ctx.tmp_dir)
                        _verify_pdf(target, len(item.pages or []))
                        published += 1
                        total_pages += len(item.pages or [])
                        ctx.item(item.index, item.label, "completed", output_path=str(target))
                        executed.append(ExecutedItem(item.index, item.label, "completed", str(target)))
                    except Exception as exc:  # noqa: BLE001
                        message = _read_error(exc)
                        ctx.item(item.index, item.label, "failed", message=message)
                        executed.append(ExecutedItem(item.index, item.label, "failed", None, message))
                        errors.append({"path": source_path, "output_path": str(target), "message": message})
                    ctx.progress("rotating", 100.0 * processed / max(1, total), current=item.label, done=processed, total=total)
            finally:
                _close_source(source)

        if cancelled:
            status = "cancelled"
        elif errors and published == 0:
            status = "failed"
        elif errors:
            status = "completed_with_errors"
        else:
            status = "completed"

        output_dirs = sorted({str(Path(item.output_path).parent) for item in plan.items if item.output_path})
        output = {
            "status": status,
            "total_files": published,
            "total_pages": total_pages,
            "output_dirs": output_dirs,
            "output_path": output_dirs[0] if len(output_dirs) == 1 else None,
            "outputs": [item.output_path for item in executed if item.status == "completed"],
            "errors": errors,
            "cancelled": cancelled,
            "angle": angle,
        }
        return OperationResult(status=status, output=output, items=executed, errors=errors, total_items=total, total_pages=total_pages)


def _rotate_pages(source, pages, angle, target, tmp_dir):
    import pymupdf

    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    partial = tmp_dir / f".{uuid.uuid4().hex}.pdf"
    doc = pymupdf.open()
    try:
        for page_no in pages:
            doc.insert_pdf(source, from_page=page_no - 1, to_page=page_no - 1)
            new_page = doc[-1]
            if angle:
                new_page.set_rotation(angle)
        doc.save(partial, garbage=3, deflate=True)
    finally:
        doc.close()
    try:
        os.replace(partial, target)
    finally:
        partial.unlink(missing_ok=True)

def _reserve_target(target, policy):
    from app.operations.split import _reserve_target as _split_reserve

    return _split_reserve(target, policy)
