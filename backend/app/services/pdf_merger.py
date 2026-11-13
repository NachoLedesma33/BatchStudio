from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, Sequence

import fitz  # PyMuPDF
import psutil

from app.models.document import MergeError, MergeResult, PdfDocument, PdfStatus


ProgressCallback = Callable[[str, int, int, Optional[str], float, float], None]
# stage, current_index, total, current_file, progress_percent, elapsed_seconds


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def merge_pdfs(
    paths: Sequence[str | Path],
    output_path: str | Path,
    *,
    overwrite: bool = False,
    progress: Optional[ProgressCallback] = None,
    cancel_event: Optional[threading.Event] = None,
    document_ids: Optional[Sequence[Optional[str]]] = None,
) -> MergeResult:
    """Merge PDFs sequentially into output_path.

    Creates a temporary file in the same directory as output_path, verifies it,
    then atomically renames it to output_path.
    """
    result = MergeResult(started_at=_now_iso())
    out = Path(output_path)
    src_paths = [Path(p) for p in paths]
    ids = list(document_ids) if document_ids is not None else [None] * len(src_paths)

    if len(src_paths) == 0:
        result.status = "failed"
        result.finished_at = _now_iso()
        result.errors.append(MergeError(message="No hay documentos para unir."))
        return result

    if out.exists() and not overwrite:
        result.status = "failed"
        result.finished_at = _now_iso()
        result.errors.append(MergeError(message="El archivo de destino ya existe."))
        return result

    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".tmp")
    # avoid collision
    counter = 1
    while tmp.exists():
        tmp = out.with_name(f"{out.name}.tmp{counter}")
        counter += 1

    proc = psutil.Process(os.getpid())
    peak_rss = proc.memory_info().rss
    start = time.perf_counter()
    cancelled = False
    merged_pages = 0
    processed = 0
    errors: list[MergeError] = []
    total_estimated = 0

    # Precompute estimated pages (best effort)
    for p in src_paths:
        try:
            with fitz.open(str(p)) as d:
                total_estimated += d.page_count
        except Exception:  # noqa: BLE001
            pass

    target = None
    try:
        target = fitz.open()  # empty
        total = len(src_paths)
        for idx, (p, did) in enumerate(zip(src_paths, ids)):
            if cancel_event is not None and cancel_event.is_set():
                cancelled = True
                break

            elapsed = time.perf_counter() - start
            if progress:
                progress("processing", idx, total, p.name, (idx / total) * 100.0, elapsed)

            # validate
            if not p.exists():
                errors.append(MergeError(document_id=did, path=str(p), message="Archivo inexistente."))
                continue
            if p.suffix.lower() != ".pdf":
                errors.append(MergeError(document_id=did, path=str(p), message="Extensión no es .pdf."))
                continue

            src = None
            try:
                src = fitz.open(str(p))
                if src.needs_pass:
                    errors.append(MergeError(document_id=did, path=str(p), message="PDF protegido con contraseña."))
                    src.close()
                    src = None
                    continue
                before = target.page_count
                target.insert_pdf(src)
                added = target.page_count - before
                merged_pages += added
                processed += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(MergeError(document_id=did, path=str(p), message="Error al procesar el PDF.", detail=str(exc)))
            finally:
                if src is not None:
                    try:
                        src.close()
                    except Exception:  # noqa: BLE001
                        pass

            # update peak
            rss = proc.memory_info().rss
            if rss > peak_rss:
                peak_rss = rss

        if cancelled:
            result.status = "cancelled"
        else:
            # save
            if progress:
                progress("saving", len(src_paths), len(src_paths), None, 95.0, time.perf_counter() - start)
            target.save(str(tmp), garbage=4, deflate=True, clean=True)
            target.close()
            target = None

            # verify
            if progress:
                progress("verifying", len(src_paths), len(src_paths), None, 98.0, time.perf_counter() - start)
            with fitz.open(str(tmp)) as v:
                actual_pages = v.page_count
            # Verification: pages must equal merged_pages
            if actual_pages != merged_pages:
                raise RuntimeError(
                    f"Verificación fallida: páginas esperadas {merged_pages}, obtenidas {actual_pages}."
                )
            if merged_pages == 0 and len(src_paths) > 0:
                raise RuntimeError("No se pudo incorporar ninguna página.")

            # atomic publish
            os.replace(str(tmp), str(out))
            tmp = None  # moved
            result.status = "completed" if not errors else "completed_with_errors"
            result.output_path = str(out)
            result.total_pages = actual_pages
            result.processed_documents = processed

    except Exception as exc:  # noqa: BLE001
        result.status = "failed"
        errors.append(MergeError(message="Fallo durante la unión.", detail=str(exc)))
    finally:
        if target is not None:
            try:
                target.close()
            except Exception:  # noqa: BLE001
                pass
        # cleanup temp if exists
        if tmp is not None and Path(tmp).exists():
            try:
                Path(tmp).unlink()
            except OSError:
                pass

    result.error_count = len(errors)
    result.errors = errors

    elapsed = time.perf_counter() - start
    result.elapsed_seconds = elapsed
    result.peak_rss_mb = peak_rss / (1024 * 1024)
    result.cancelled = cancelled
    result.finished_at = _now_iso()

    if cancelled:
        result.status = "cancelled"
        # remove partial output if any
        if out.exists() and result.output_path is None:
            try:
                out.unlink()
            except OSError:
                pass

    if progress:
        progress("done", len(src_paths), len(src_paths), None, 100.0, elapsed)

    return result


def merge_documents(
    documents: Sequence[PdfDocument],
    output_path: str | Path,
    *,
    overwrite: bool = False,
    progress: Optional[ProgressCallback] = None,
    cancel_event: Optional[threading.Event] = None,
) -> MergeResult:
    included = [d for d in documents if d.included]
    ordered = sorted(included, key=lambda d: d.order_index)
    return merge_pdfs(
        [d.path for d in ordered],
        output_path,
        overwrite=overwrite,
        progress=progress,
        cancel_event=cancel_event,
        document_ids=[d.id for d in ordered],
    )
