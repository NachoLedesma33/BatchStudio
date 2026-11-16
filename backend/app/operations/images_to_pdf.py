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


def _resolve_output_path(params, default_name):
    raw = str(params.get("output_path") or "").strip()
    if not raw:
        return _downloads() / ensure_pdf_suffix(default_name)
    path = Path(raw).expanduser()
    if not path.is_absolute() and len(path.parts) == 1:
        return _downloads() / path.name
    return path


class ImagesToPdfOperation(Operation):
    kind = "images-to-pdf"

    def __init__(self, documents, config=None):
        super().__init__(documents)
        self.config = config

    def plan(self, session_id, params):
        plan = OperationPlan(kind=self.kind)
        images = params.get("images") or params.get("paths") or []
        if isinstance(images, str):
            images = [images]
        images = [str(p) for p in images]
        if not images:
            # try from documents included? images stored as documents? no
            plan.errors.append(PlanMessage("NO_IMAGES", "Indicá al menos una imagen."))
            return plan
        for p in images:
            if not Path(p).is_file():
                plan.errors.append(PlanMessage("IMAGE_NOT_FOUND", f"No existe el archivo: {p}"))
        if plan.errors:
            return plan

        collision_policy = str(params.get("collision_policy") or DEFAULT_COLLISION_POLICY).lower()
        if collision_policy not in COLLISION_POLICIES:
            plan.errors.append(PlanMessage("INVALID_COLLISION_POLICY", f"La política «{collision_policy}» no existe."))
            return plan

        target = _resolve_output_path(params, "imagenes_unidas")
        if collision_policy == "suffix":
            target = unique_output_path(target, set())
        elif collision_policy == "fail" and _is_taken(target, set()):
            plan.errors.append(PlanMessage("OUTPUT_EXISTS", f"Ya existe un archivo: {target}."))
            return plan

        plan.items.append(
            PlanItem(
                index=1,
                label=target.name,
                pages=list(range(1, len(images) + 1)),
                exists=target.exists(),
                output_path=str(target),
            )
        )
        plan.summary = {
            "total_files": 1,
            "total_pages": len(images),
            "images": images,
            "collision_policy": collision_policy,
            "rotation": int(params.get("rotation", 0)),
        }
        return plan

    def execute(self, plan, ctx, params):
        executed = []
        errors = []
        total = len(plan.items)
        processed = 0
        published = 0
        cancelled = False
        images = plan.summary.get("images", [])
        rotation = int(plan.summary.get("rotation", 0)) % 360
        policy = str(plan.summary.get("collision_policy", DEFAULT_COLLISION_POLICY))

        for item in plan.items:
            if cancelled:
                break
            if ctx.cancelled:
                cancelled = True
                ctx.item(item.index, item.label, "cancelled", message="Cancelado por el usuario.")
                executed.append(ExecutedItem(item.index, item.label, "cancelled", None, "Cancelado por el usuario."))
                continue
            processed += 1
            ctx.item(item.index, item.label, "processing")
            target = Path(item.output_path or "")
            try:
                target = _reserve_target(target, policy)
                doc = pymupdf.open()
                try:
                    for img_path in images:
                        with pymupdf.open(img_path) as im:
                            pix = im[0] if im.page_count else None
                        # fallback: use pixmap from image
                        pm = pymupdf.Pixmap(img_path)
                        page = doc.new_page(width=pm.width, height=pm.height)
                        page.insert_image(page.rect, filename=img_path)
                        if rotation:
                            page.set_rotation(rotation)
                    tmp = target.with_name(f".{uuid.uuid4().hex}.pdf")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    doc.save(tmp, garbage=3, deflate=True)
                    doc.close()
                    os.replace(tmp, target)
                    tmp.unlink(missing_ok=True)
                finally:
                    try:
                        doc.close()
                    except Exception:
                        pass
                _verify_pdf_simple(target, len(images))
                published += 1
                ctx.item(item.index, item.label, "completed", output_path=str(target))
                executed.append(ExecutedItem(item.index, item.label, "completed", str(target)))
            except Exception as exc:  # noqa: BLE001
                message = _read_error(exc)
                ctx.item(item.index, item.label, "failed", message=message)
                executed.append(ExecutedItem(item.index, item.label, "failed", None, message))
                errors.append({"path": None, "output_path": str(target), "message": message})
            ctx.progress("creating", 100.0 * processed / max(1, total), current=item.label, done=processed, total=total)

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
            "total_pages": len(images) if published else 0,
            "output_dirs": output_dirs,
            "output_path": output_dirs[0] if len(output_dirs) == 1 else None,
            "outputs": [item.output_path for item in executed if item.status == "completed"],
            "errors": errors,
            "cancelled": cancelled,
        }
        return OperationResult(status=status, output=output, items=executed, errors=errors, total_items=total, total_pages=len(images) if published else 0)


def _verify_pdf_simple(path, expected):
    import pymupdf

    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("El archivo generado está vacío.")
    with pymupdf.open(path) as doc:
        if doc.page_count != expected:
            raise RuntimeError(f"Se esperaban {expected} páginas y se generaron {doc.page_count}.")


def _reserve_target(target, policy):
    from app.operations.split import _reserve_target as _split_reserve

    return _split_reserve(target, policy)
