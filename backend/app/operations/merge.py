from __future__ import annotations

from pathlib import Path
from typing import Any

from app.operations.base import (
    CancelProxy,
    ExecutedItem,
    JobContext,
    Operation,
    OperationPlan,
    OperationResult,
    PlanItem,
    PlanMessage,
)
from app.services.pdf_merger import merge_pdfs


def _downloads() -> Path:
    downloads = Path.home() / "Downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    return downloads


def resolve_output_path(params: dict[str, Any]) -> Path:
    """Misma regla histórica de la UI: nombre suelto → Descargas."""
    raw = str(params.get("output_path") or "").strip()
    if not raw:
        return _downloads() / "documentos_unidos.pdf"
    path = Path(raw).expanduser()
    if not path.is_absolute() and len(path.parts) == 1:
        return _downloads() / path.name
    return path


class MergeOperation(Operation):
    kind = "merge"

    def _selected_documents(self, session_id: str, params: dict[str, Any]):
        docs = self.documents.included(session_id)
        requested = params.get("document_ids")
        if requested:
            wanted = [str(doc_id) for doc_id in requested]
            by_id = {doc.id: doc for doc in docs}
            docs = [by_id[doc_id] for doc_id in wanted if doc_id in by_id]
        return docs

    def plan(self, session_id: str, params: dict[str, Any]) -> OperationPlan:
        docs = self._selected_documents(session_id, params)
        output = resolve_output_path(params)
        overwrite = bool(params.get("overwrite", False))
        total_pages = sum(doc.page_count or 0 for doc in docs)
        summary = {
            "total_files": len(docs),
            "total_pages": total_pages,
            "total_bytes_estimate": sum(doc.size_bytes for doc in docs),
        }
        plan = OperationPlan(kind=self.kind, summary=summary)
        if not docs:
            plan.errors.append(
                PlanMessage("NO_DOCUMENTS", "No hay documentos incluidos en el lote.")
            )
            return plan

        invalid = [doc for doc in docs if doc.status.value in {"invalid", "failed"}]
        if invalid:
            plan.warnings.append(
                PlanMessage(
                    "INVALID_DOCUMENTS",
                    f"{len(invalid)} documento(s) del lote tienen problemas y podrían fallar.",
                )
            )
        if output.exists() and not overwrite:
            plan.warnings.append(
                PlanMessage(
                    "OUTPUT_EXISTS",
                    f"El archivo de destino ya existe: {output}. Activá «Sobrescribir» para reemplazarlo.",
                )
            )
        plan.items.append(
            PlanItem(
                index=1,
                label=output.name,
                pages=list(range(1, total_pages + 1)),
                exists=output.exists(),
                output_path=str(output),
            )
        )
        return plan

    def execute(
        self, plan: OperationPlan, ctx: JobContext, params: dict[str, Any]
    ) -> OperationResult:
        docs = self._selected_documents(ctx.session_id or "", params)
        output = resolve_output_path(params)
        overwrite = bool(params.get("overwrite", False))
        label = output.name

        if not docs:
            return OperationResult(
                status="failed",
                errors=[{"code": "NO_DOCUMENTS", "message": "No hay documentos incluidos en el lote."}],
                items=[ExecutedItem(1, label, "failed", message="No hay documentos.")],
                total_items=1,
            )
        if output.exists() and not overwrite:
            message = "El archivo de destino ya existe."
            return OperationResult(
                status="failed",
                errors=[{"code": "OUTPUT_EXISTS", "message": message, "path": str(output)}],
                items=[ExecutedItem(1, label, "failed", output_path=str(output), message=message)],
                total_items=1,
            )

        ctx.item(1, label, "processing")

        last_emit = {"percent": -10.0}

        def on_progress(stage: str, idx: int, total: int, name, percent: float, elapsed: float) -> None:
            # No saturar SQLite: como máximo un update cada 1 %.
            if percent - last_emit["percent"] < 1.0 and stage not in {"saving", "verifying", "done"}:
                return
            last_emit["percent"] = percent
            ctx.progress(stage, percent, current=name, done=idx, total=total)

        result = merge_pdfs(
            [doc.path for doc in docs],
            output,
            overwrite=overwrite,
            progress=on_progress,
            cancel_event=CancelProxy(lambda: ctx.cancelled),  # type: ignore[arg-type]
            document_ids=[doc.id for doc in docs],
        )

        errors = [
            {
                "document_id": error.document_id,
                "path": error.path,
                "message": error.message,
                "detail": error.detail,
            }
            for error in result.errors
        ]

        if result.status in {"completed", "completed_with_errors"}:
            item_status = "completed"
            message = None
        elif result.status == "cancelled":
            item_status = "cancelled"
            message = "Cancelado por el usuario."
        else:
            item_status = "failed"
            message = errors[0]["message"] if errors else "La unión falló."
        ctx.item(1, label, item_status, output_path=result.output_path, message=message)

        return OperationResult(
            status=result.status,
            output=result.to_dict(),
            items=[ExecutedItem(1, label, item_status, result.output_path, message)],
            errors=errors,
            total_items=1,
            total_pages=result.total_pages,
            elapsed_seconds=result.elapsed_seconds,
        )
