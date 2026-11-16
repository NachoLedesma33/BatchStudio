from __future__ import annotations

import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import pymupdf

from app.models.document import PdfDocument, PdfStatus


def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect_pdf(path: str | Path, compute_hash: bool = True) -> PdfDocument:
    """Inspect a single PDF and return a PdfDocument with status."""
    p = Path(path)
    doc = PdfDocument(path=str(p), name=p.name)

    if not p.exists():
        doc.status = PdfStatus.INVALID
        doc.error_message = "El archivo no existe."
        return doc
    if not p.is_file():
        doc.status = PdfStatus.INVALID
        doc.error_message = "La ruta no es un archivo."
        return doc
    if p.suffix.lower() != ".pdf":
        doc.status = PdfStatus.INVALID
        doc.error_message = "La extensión no es .pdf."
        return doc

    try:
        doc.size_bytes = p.stat().st_size
    except OSError as exc:
        doc.status = PdfStatus.INVALID
        doc.error_message = f"Sin permisos de lectura: {exc}"
        return doc

    if doc.size_bytes == 0:
        doc.status = PdfStatus.INVALID
        doc.error_message = "El archivo está vacío."
        return doc

    doc.status = PdfStatus.INSPECTING
    fitz_doc = None
    try:
        fitz_doc = pymupdf.open(str(p))
        if fitz_doc.is_closed:
            raise RuntimeError("No se pudo abrir el documento.")
        if fitz_doc.needs_pass:
            doc.status = PdfStatus.PROTECTED
            doc.error_message = "El PDF está protegido con contraseña."
            doc.page_count = None
            return doc
        # Try empty password only if required? No: do not bypass protection.
        doc.page_count = fitz_doc.page_count
        meta = fitz_doc.metadata or {}
        doc.metadata = {
            "title": meta.get("title") or None,
            "author": meta.get("author") or None,
            "creator": meta.get("creator") or None,
            "producer": meta.get("producer") or None,
            "format": meta.get("format") or None,
            "encrypted": bool(fitz_doc.is_encrypted),
        }
        if doc.page_count == 0:
            doc.status = PdfStatus.WARNING
            doc.error_message = "El PDF no contiene páginas."
        else:
            doc.status = PdfStatus.READY
    except Exception as exc:  # noqa: BLE001
        doc.status = PdfStatus.INVALID
        doc.error_message = f"PDF corrupto o no válido: {exc}"
        doc.page_count = None
    finally:
        if fitz_doc is not None:
            try:
                fitz_doc.close()
            except Exception:  # noqa: BLE001
                pass

    if compute_hash and doc.status in (PdfStatus.READY, PdfStatus.WARNING):
        try:
            doc.sha256 = _sha256_file(p)
        except OSError as exc:
            doc.status = PdfStatus.INVALID
            doc.error_message = f"No se pudo calcular el hash: {exc}"

    return doc


def inspect_folder(folder: str | Path, recursive: bool = True) -> list[PdfDocument]:
    """Inspect all PDFs in a folder."""
    root = Path(folder)
    results: list[PdfDocument] = []
    if not root.is_dir():
        return results
    pattern = "**/*.pdf" if recursive else "*.pdf"
    for p in sorted(root.glob(pattern)):
        if p.is_file():
            results.append(inspect_pdf(p))
    return results


def detect_duplicates(docs: list[PdfDocument]) -> dict[str, list[str]]:
    """Return map sha256 -> list of document ids for duplicates."""
    groups: dict[str, list[str]] = {}
    for d in docs:
        if d.sha256:
            groups.setdefault(d.sha256, []).append(d.id)
    return {h: ids for h, ids in groups.items() if len(ids) > 1}
