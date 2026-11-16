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


def _parse_pages(params: dict[str, Any], page_count: int) -> list[int]:
    if "pages" in params and params.get("pages") is not None:
        raw = params.get("pages")
        if isinstance(raw, str):
            # permitir "1,3,5-7"
            from app.operations.split import parse_ranges

            ranges = parse_ranges(raw, page_count)
            pages: list[int] = []
            for item in ranges:
                pages.extend(item.pages)
            return pages
        if isinstance(raw, (list, tuple)):
            result = []
            for value in raw:
                try:
                    number = int(value)
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Página inválida: {value!r}.") from exc
                if number < 1 or number > page_count:
                    raise ValueError(
                        f"La página {number} no existe: el documento tiene {page_count}."
                    )
                result.append(number)
            if not result:
                raise ValueError("Indicá al menos una página para extraer.")
            return result
    if "ranges" in params and params.get("ranges"):
        from app.operations.split import parse_ranges

        ranges = parse_ranges(str(params.get("ranges")), page_count)
        pages = []
        for item in ranges:
            pages.extend(item.pages)
        if not pages:
            raise ValueError("Indicá al menos una página para extraer.")
        return pages
    # default: todas las páginas
    return list(range(1, page_count + 1))


class ExtractOperation(Operation):
    kind = "extract"

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

        # La extracción trabaja sobre el primer documento seleccionado.
        doc = docs[0]
        page_count = doc.page_count or 0
        if page_count < 1:
            plan.errors.append(
                PlanMessage("NO_PAGES", f"{doc.name}: el documento no tiene páginas.")
            )
            return plan

        try:
            pages = _parse_pages(params, page_count)
        except Exception as exc:  # noqa: BLE001
            plan.errors.append(PlanMessage("INVALID_PAGES", str(exc)))
            return plan

        # deduplicar preservando orden
        seen: set[int] = set()
        ordered: list[int] = []
        for page in pages:
            if page not in seen:
                seen.add(page)
                ordered.append(page)
        pages = ordered

        collision_policy = str(params.get("collision_policy") or DEFAULT_COLLISION_POLICY).lower()
        if collision_policy not in COLLISION_POLICIES:
            plan.errors.append(
                PlanMessage("INVALID_COLLISION_POLICY", f"La política «{collision_policy}» no existe.")
            )
            return plan

        template = str(params.get("name_template") or "{name}_extraido")
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

        filename, changed = sanitize_filename(ensure_pdf_suffix(rendered))
        target = _resolve_output_path(params, doc, filename)
        if len(str(target)) > 240:
            plan.errors.append(PlanMessage("OUTPUT_PATH_TOO_LONG", f"La ruta supera 240 caracteres: {target}"))
            return plan

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
            "collision_policy": collision_policy,
            "mode": "extract",
        }
        return plan

    def execute(self, plan: OperationPlan, ctx: JobContext, params: dict[str, Any]) -> OperationResult:
        executed: list[ExecutedItem] = []
        errors: list[dict[str, Any]] = []
        total_pages = 0
        published = 0
        cancelled = False
        total = len(plan.items)
        policy = str(params.get("collision_policy") or DEFAULT_COLLISION_POLICY).lower()

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
                        _extract_pages(source, item.pages or [], target, ctx.tmp_dir)
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
        }
        return OperationResult(status=status, output=output, items=executed, errors=errors, total_items=total, total_pages=total_pages)


def _stem(doc) -> str:
    metadata = getattr(doc, "metadata", None) or {}
    raw = ""
    if isinstance(metadata, dict):
        raw = str(metadata.get("original_name") or "")
    raw = raw or getattr(doc, "name", "") or Path(getattr(doc, "path", "")).name
    base = Path(raw.replace("\\", "/")).name
    stem = base[:-4] if base.lower().endswith(".pdf") else base
    return stem or "documento"


def _extract_pages(source, pages, target, tmp_dir):
    from app.operations.split import _extract_pages as _split_extract

    _split_extract(source, pages, target, tmp_dir)


def _reserve_target(target, policy):
    from app.operations.split import _reserve_target as _split_reserve

    return _split_reserve(target, policy)
