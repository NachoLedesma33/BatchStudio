from __future__ import annotations

import json
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


class ExtractAnnotationsOperation(Operation):
    kind = "extract-annotations"

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

        for doc in docs:
            page_count = doc.page_count or 0
            if page_count < 1:
                plan.warnings.append(PlanMessage("NO_PAGES", f"{doc.name}: sin páginas."))
                continue
            target = _downloads() / f"{_stem(doc)}_anotaciones.txt"
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

        by_source = {}
        for item in plan.items:
            by_source.setdefault(item.source_path or "", []).append(item)

        for source_path, items in by_source.items():
            if cancelled:
                break
            try:
                source = _open_source(source_path)
            except Exception as exc:  # noqa: BLE001
                message = str(exc) or "No se pudo abrir el PDF."
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
                        lines = []
                        count = 0
                        for page_no in (item.pages or []):
                            page = source[page_no - 1]
                            for annot in page.annots() or []:
                                count += 1
                                info = annot.info or {}
                                lines.append(f"[Página {page_no}] {annot.type[1]}: {info.get('content') or info.get('title') or ''}")
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_text("\n".join(lines) if lines else "Sin anotaciones.", encoding="utf-8")
                        published += 1
                        ctx.item(item.index, item.label, "completed", output_path=str(target))
                        executed.append(ExecutedItem(item.index, item.label, "completed", str(target)))
                    except Exception as exc:  # noqa: BLE001
                        message = str(exc) or "No se pudo generar el archivo."
                        ctx.item(item.index, item.label, "failed", message=message)
                        executed.append(ExecutedItem(item.index, item.label, "failed", None, message))
                        errors.append({"path": source_path, "output_path": str(target), "message": message})
                    ctx.progress("extracting", 100.0 * processed / max(1, total), current=item.label, done=processed, total=total)
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

        published_count = sum(1 for e in executed if e.status == "completed")
        output_dirs = sorted({str(Path(item.output_path).parent) for item in plan.items if item.output_path})
        output = {
            "status": status,
            "total_files": published_count,
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
