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
    ensure_pdf_suffix,
    render_template,
    sanitize_filename,
    unique_output_path,
)


def _downloads() -> Path:
    downloads = Path.home() / "Downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    return downloads


def _resolve_output_dir(params: dict[str, Any], doc) -> Path:
    raw = str(params.get("output_dir") or "").strip()
    if not raw:
        stem = _stem(doc)
        return Path.home() / "Downloads" / f"{stem}_imagenes"
    path = Path(raw).expanduser()
    if not path.is_absolute() and len(path.parts) == 1:
        return Path.home() / "Downloads" / path.name
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


class PdfToImagesOperation(Operation):
    kind = "pdf-to-images"

    def __init__(self, documents, config=None) -> None:
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

        fmt = str(params.get("format") or "png").lower()
        if fmt not in {"png", "jpeg", "jpg"}:
            plan.errors.append(PlanMessage("INVALID_FORMAT", "El formato debe ser png o jpeg."))
            return plan
        ext = "jpg" if fmt == "jpeg" else fmt
        fmt = "jpeg" if fmt == "jpg" else fmt

        try:
            dpi = int(params.get("dpi", 150))
        except (TypeError, ValueError):
            plan.errors.append(PlanMessage("INVALID_DPI", "El DPI debe ser un número."))
            return plan
        if dpi < 36 or dpi > 600:
            plan.errors.append(PlanMessage("INVALID_DPI", "El DPI debe estar entre 36 y 600."))
            return plan

        quality = params.get("quality", 85)
        try:
            quality = int(quality)
        except (TypeError, ValueError):
            quality = 85

        template = str(params.get("name_template") or "{name}_p{index:03}")

        total_items = 0
        for doc in docs:
            page_count = doc.page_count or 0
            if page_count < 1:
                plan.warnings.append(PlanMessage("NO_PAGES", f"{doc.name}: sin páginas."))
                continue
            # pages selection
            pages_param = params.get("pages")
            if pages_param is None:
                pages = list(range(1, page_count + 1))
            else:
                try:
                    if isinstance(pages_param, str):
                        from app.operations.split import parse_ranges

                        pages = []
                        for item in parse_ranges(pages_param, page_count):
                            pages.extend(item.pages)
                    elif isinstance(pages_param, (list, tuple)):
                        pages = [int(x) for x in pages_param]
                    else:
                        raise ValueError("Formato de páginas inválido.")
                except Exception as exc:  # noqa: BLE001
                    plan.errors.append(PlanMessage("INVALID_PAGES", str(exc)))
                    continue
                pages = [p for p in pages if 1 <= p <= page_count]
                if not pages:
                    plan.warnings.append(PlanMessage("NO_PAGES", f"{doc.name}: sin páginas válidas."))
                    continue

            out_dir = _resolve_output_dir(params, doc)
            for page_no in pages:
                try:
                    rendered = render_template(
                        template,
                        name=_stem(doc),
                        index=page_no,
                        start=page_no,
                        end=page_no,
                        pages=1,
                    )
                except Exception as exc:  # noqa: BLE001
                    plan.errors.append(PlanMessage("INVALID_TEMPLATE", str(exc)))
                    continue
                filename, _ = sanitize_filename(f"{rendered}.{ext}")
                target = out_dir / filename
                plan.items.append(
                    PlanItem(
                        index=total_items + 1,
                        label=target.name,
                        pages=[page_no],
                        exists=target.exists(),
                        output_path=str(target),
                        source_path=doc.path,
                    )
                )
                total_items += 1
                # store params in item? We'll recompute in execute from params + page
        # stash params in plan.summary
        plan.summary = {
            "total_files": total_items,
            "total_pages": total_items,
            "source_files": len(docs),
            "format": fmt,
            "ext": ext,
            "dpi": dpi,
            "quality": quality,
            "template": template,
        }
        if not plan.items and not plan.errors:
            plan.errors.append(PlanMessage("NO_OUTPUTS", "La configuración no genera ninguna imagen."))
        return plan

    def execute(self, plan, ctx, params):
        executed = []
        errors = []
        total = len(plan.items)
        processed = 0
        published = 0
        cancelled = False
        fmt = plan.summary.get("format", "png")
        ext = plan.summary.get("ext", "png")
        dpi = int(plan.summary.get("dpi", 150))
        quality = int(plan.summary.get("quality", 85))

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
                zoom = dpi / 72.0
                matrix = pymupdf.Matrix(zoom, zoom)
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
                        page_no = (item.pages or [1])[0]
                        page = source[page_no - 1]
                        pix = page.get_pixmap(matrix=matrix)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        if fmt == "jpeg":
                            pix.save(str(target), output="jpeg", jpg_quality=quality)
                        else:
                            pix.save(str(target))
                        if not target.is_file():
                            raise RuntimeError("No se pudo guardar la imagen.")
                        published += 1
                        ctx.item(item.index, item.label, "completed", output_path=str(target))
                        executed.append(ExecutedItem(item.index, item.label, "completed", str(target)))
                    except Exception as exc:  # noqa: BLE001
                        message = _read_error(exc)
                        ctx.item(item.index, item.label, "failed", message=message)
                        executed.append(ExecutedItem(item.index, item.label, "failed", None, message))
                        errors.append({"path": source_path, "output_path": str(target), "message": message})
                    ctx.progress("exporting", 100.0 * processed / max(1, total), current=item.label, done=processed, total=total)
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
            "total_pages": published,
            "output_dirs": output_dirs,
            "output_path": output_dirs[0] if len(output_dirs) == 1 else None,
            "outputs": [item.output_path for item in executed if item.status == "completed"],
            "errors": errors,
            "cancelled": cancelled,
        }
        return OperationResult(status=status, output=output, items=executed, errors=errors, total_items=total, total_pages=published)
