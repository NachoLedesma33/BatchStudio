from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

import pymupdf

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
    sanitize_filename,
    unique_output_path,
)


def _downloads() -> Path:
    downloads = Path.home() / "Downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    return downloads


def _stem(doc) -> str:
    metadata = getattr(doc, "metadata", None) or {}
    raw = ""
    if isinstance(metadata, dict):
        raw = str(metadata.get("original_name") or "")
    raw = raw or getattr(doc, "name", "") or Path(getattr(doc, "path", "")).name
    base = Path(raw.replace("\\", "/")).name
    stem = base[:-4] if base.lower().endswith(".pdf") else base
    return stem or "documento"


class WatermarkOperation(Operation):
    kind = "watermark"

    def __init__(self, documents, config=None):
        super().__init__(documents)
        self.config = config

    def _selected_documents(self, session_id, params):
        docs = self.documents.included(session_id)
        requested = params.get("document_ids") or params.get("document_id")
        if requested:
            if isinstance(requested, str):
                requested = [requested]
            wanted = [str(x) for x in requested]
            by_id = {d.id: d for d in docs}
            docs = [by_id[x] for x in wanted if x in by_id]
        return docs

    def plan(self, session_id, params):
        docs = self._selected_documents(session_id, params)
        plan = OperationPlan(kind=self.kind)
        if not docs:
            plan.errors.append(PlanMessage("NO_DOCUMENTS", "No hay documentos incluidos en el lote."))
            return plan

        collision_policy = str(params.get("collision_policy") or DEFAULT_COLLISION_POLICY).lower()
        if collision_policy not in COLLISION_POLICIES:
            plan.errors.append(PlanMessage("INVALID_COLLISION_POLICY", f"La política «{collision_policy}» no existe."))
            return plan

        text = str(params.get("text") or "CONFIDENCIAL")
        if not text.strip():
            plan.errors.append(PlanMessage("INVALID_TEXT", "Indicá el texto de la marca de agua."))
            return plan

        for doc in docs:
            page_count = doc.page_count or 0
            if page_count < 1:
                plan.warnings.append(PlanMessage("NO_PAGES", f"{doc.name}: sin páginas."))
                continue
            target = _downloads() / f"{_stem(doc)}_marca.pdf"
            if collision_policy == "suffix":
                target = unique_output_path(target, set())
            elif collision_policy == "fail" and _is_taken(target, set()):
                plan.errors.append(PlanMessage("OUTPUT_EXISTS", f"Ya existe un archivo: {target}."))
                continue
            plan.items.append(
                PlanItem(
                    index=len(plan.items) + 1,
                    label=target.name,
                    pages=list(range(1, page_count + 1)),
                    exists=target.exists(),
                    output_path=str(target),
                    source_path=doc.path,
                )
            )

        plan.summary = {
            "total_files": len(plan.items),
            "total_pages": sum(len(item.pages or []) for item in plan.items),
            "collision_policy": collision_policy,
            "text": text,
            "opacity": float(params.get("opacity", 0.3)),
            "angle": int(params.get("angle", 45)),
            "fontsize": int(params.get("fontsize", 48)),
        }
        if not plan.items and not plan.errors:
            plan.errors.append(PlanMessage("NO_OUTPUTS", "La configuración no genera ningún archivo."))
        return plan

    def execute(self, plan, ctx, params):
        executed = []
        errors = []
        total = len(plan.items)
        processed = 0
        published = 0
        cancelled = False
        policy = str(plan.summary.get("collision_policy", DEFAULT_COLLISION_POLICY))
        text = str(plan.summary.get("text", "CONFIDENCIAL"))
        opacity = float(plan.summary.get("opacity", 0.3))
        angle = int(plan.summary.get("angle", 45))
        fontsize = int(plan.summary.get("fontsize", 48))

        by_source = {}
        for item in plan.items:
            by_source.setdefault(item.source_path or "", []).append(item)

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
                        tmp = target.with_name(f".{uuid.uuid4().hex}.pdf")
                        target.parent.mkdir(parents=True, exist_ok=True)
                        for page_no in (item.pages or []):
                            page = source[page_no - 1]
                            rect = page.rect
                            # centrar texto
                            tw = pymupdf.get_text_length(text, fontsize=fontsize)
                            x = (rect.width - tw) / 2
                            y = rect.height / 2
                            page.insert_text(
                                (x, y),
                                text,
                                fontsize=fontsize,
                                color=(0.5, 0.5, 0.5),
                                fill_opacity=opacity,
                                rotate=angle,
                                overlay=True,
                            )
                        source.save(tmp, garbage=4, deflate=True)
                        os.replace(tmp, target)
                        tmp.unlink(missing_ok=True)
                        _verify_pdf(target, len(item.pages or []))
                        published += 1
                        ctx.item(item.index, item.label, "completed", output_path=str(target))
                        executed.append(ExecutedItem(item.index, item.label, "completed", str(target)))
                    except Exception as exc:  # noqa: BLE001
                        message = _read_error(exc)
                        ctx.item(item.index, item.label, "failed", message=message)
                        executed.append(ExecutedItem(item.index, item.label, "failed", None, message))
                        errors.append({"path": source_path, "output_path": str(target), "message": message})
                    ctx.progress("watermarking", 100.0 * processed / max(1, total), current=item.label, done=processed, total=total)
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
            "total_pages": sum(len(item.pages or []) for item in plan.items),
            "output_dirs": output_dirs,
            "output_path": output_dirs[0] if len(output_dirs) == 1 else None,
            "outputs": [item.output_path for item in executed if item.status == "completed"],
            "errors": errors,
            "cancelled": cancelled,
        }
        return OperationResult(status=status, output=output, items=executed, errors=errors, total_items=total, total_pages=sum(len(item.pages or []) for item in plan.items))


def _reserve_target(target, policy):
    from app.operations.split import _reserve_target as _split_reserve

    return _split_reserve(target, policy)
