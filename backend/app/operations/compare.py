from __future__ import annotations

import difflib
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


class CompareOperation(Operation):
    kind = "compare"

    def __init__(self, documents, config=None):
        super().__init__(documents)
        self.config = config

    def _selected_documents(self, session_id, params):
        docs = self.documents.included(session_id)
        return docs

    def plan(self, session_id, params):
        docs = self.documents.included(session_id)
        plan = OperationPlan(kind=self.kind)
        doc_a_id = params.get("document_id_a")
        doc_b_id = params.get("document_id_b")
        by_id = {d.id: d for d in docs}
        doc_a = by_id.get(str(doc_a_id)) if doc_a_id else (docs[0] if docs else None)
        doc_b = by_id.get(str(doc_b_id)) if doc_b_id else (docs[1] if len(docs) > 1 else None)
        if doc_a is None or doc_b is None:
            plan.errors.append(PlanMessage("NO_DOCUMENTS", "Se necesitan dos documentos para comparar."))
            return plan
        if doc_a.id == doc_b.id:
            plan.errors.append(PlanMessage("SAME_DOCUMENT", "Seleccioná dos documentos distintos."))
            return plan

        target = _downloads() / f"comparacion_{_stem(doc_a)}_{_stem(doc_b)}.txt"
        collision_policy = str(params.get("collision_policy") or DEFAULT_COLLISION_POLICY).lower()
        if collision_policy not in COLLISION_POLICIES:
            plan.errors.append(PlanMessage("INVALID_COLLISION_POLICY", f"La política «{collision_policy}» no existe."))
            return plan
        if collision_policy == "suffix":
            target = unique_output_path(target, set())
        elif collision_policy == "fail" and _is_taken(target, set()):
            plan.errors.append(PlanMessage("OUTPUT_EXISTS", f"Ya existe un archivo: {target}."))
            return plan

        plan.items.append(
            PlanItem(
                index=1,
                label=target.name,
                pages=[],
                exists=target.exists(),
                output_path=str(target),
                source_path=doc_a.path,
            )
        )
        plan.summary = {
            "total_files": 1,
            "total_pages": 0,
            "collision_policy": collision_policy,
            "doc_a": doc_a.path,
            "doc_b": doc_b.path,
            "name_a": doc_a.name,
            "name_b": doc_b.name,
        }
        return plan

    def execute(self, plan, ctx, params):
        executed = []
        errors = []
        item = plan.items[0]
        ctx.item(item.index, item.label, "processing")
        target = Path(item.output_path or "")
        policy = str(plan.summary.get("collision_policy", DEFAULT_COLLISION_POLICY))
        try:
            target = _reserve_target(target, policy)
            source_a = pymupdf.open(plan.summary["doc_a"])
            source_b = pymupdf.open(plan.summary["doc_b"])
            text_a = "\n".join(page.get_text() for page in source_a)
            text_b = "\n".join(page.get_text() for page in source_b)
            source_a.close()
            source_b.close()
            diff = difflib.unified_diff(
                text_a.splitlines(),
                text_b.splitlines(),
                fromfile=plan.summary["name_a"],
                tofile=plan.summary["name_b"],
                lineterm="",
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("\n".join(diff), encoding="utf-8")
            ctx.item(item.index, item.label, "completed", output_path=str(target))
            executed.append(ExecutedItem(item.index, item.label, "completed", str(target)))
            status = "completed"
        except Exception as exc:  # noqa: BLE001
            message = str(exc) or "No se pudo comparar."
            ctx.item(item.index, item.label, "failed", message=message)
            executed.append(ExecutedItem(item.index, item.label, "failed", None, message))
            errors.append({"path": plan.summary.get("doc_a"), "output_path": str(target), "message": message})
            status = "failed"
        output_dirs = [str(target.parent)]
        output = {
            "status": status,
            "total_files": 1 if status == "completed" else 0,
            "total_pages": 0,
            "output_dirs": output_dirs,
            "output_path": str(target) if status == "completed" else None,
            "outputs": [str(target)] if status == "completed" else [],
            "errors": errors,
            "cancelled": False,
        }
        return OperationResult(status=status, output=output, items=executed, errors=errors, total_items=1, total_pages=0)


def _reserve_target(target, policy):
    from app.operations.split import _reserve_target as _split_reserve

    return _split_reserve(target, policy)
