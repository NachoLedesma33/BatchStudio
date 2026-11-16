from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from app.operations.base import (
    ExecutedItem,
    JobContext,
    Operation,
    OperationPlan,
    OperationResult,
    PlanItem,
    PlanMessage,
)

DEFAULT_TEMPLATE = "{name}_parte_{index:02}"
DEFAULT_COLLISION_POLICY = "suffix"
COLLISION_POLICIES = {"suffix", "fail", "overwrite"}
MODES = {"ranges", "every", "single"}

MAX_OUTPUT_PATH_LENGTH = 240
MAX_FILENAME_STEM = 120
INVALID_CHARS = set('<>:"/\\|?*')
RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

_TOKEN_RE = re.compile(r"\{(name|index|start|end|pages|date)(?::([^}]*))?\}")


class SplitSpecError(ValueError):
    """Error de especificación de la operación (sintaxis, rangos o plantilla)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class PageRange:
    start: int
    end: int

    @property
    def pages(self) -> list[int]:
        return list(range(self.start, self.end + 1))

    @property
    def label(self) -> str:
        return str(self.start) if self.start == self.end else f"{self.start}-{self.end}"


def parse_ranges(spec: str, page_count: int) -> list[PageRange]:
    """Convierte `1-3, 5, 8-` en rangos 1-based inclusivos.

    `7-` llega hasta el final; `-3` empieza en la página 1. Los rangos abiertos
    se resuelven con `page_count`, así que el máximo siempre se valida.
    """
    text = (spec or "").strip()
    if not text:
        raise SplitSpecError("EMPTY_RANGES", "Escribí al menos un rango de páginas.")
    if page_count < 1:
        raise SplitSpecError("NO_PAGES", "El documento no tiene páginas para dividir.")

    ranges: list[PageRange] = []
    for raw in text.split(","):
        token = raw.strip()
        if not token:
            raise SplitSpecError(
                "EMPTY_GROUP",
                "Hay un grupo vacío en los rangos (por ejemplo «1-3,,5»).",
            )
        ranges.append(_parse_token(token, page_count))
    return ranges


def _parse_token(token: str, page_count: int) -> PageRange:
    if "-" not in token:
        page = _parse_int(token, token)
        _check_page(page, page_count)
        return PageRange(page, page)

    parts = token.split("-")
    if len(parts) != 2:
        raise SplitSpecError(
            "INVALID_RANGE",
            f"El rango «{token}» no es válido. Usá «inicio-fin».",
        )
    raw_start, raw_end = parts[0].strip(), parts[1].strip()
    start = 1 if raw_start == "" else _parse_int(raw_start, token)
    end = page_count if raw_end == "" else _parse_int(raw_end, token)
    _check_page(start, page_count)
    _check_page(end, page_count)
    if start > end:
        raise SplitSpecError(
            "RANGE_REVERSED",
            f"El rango «{token}» empieza en {start} y termina en {end}: el inicio no puede ser mayor que el fin.",
        )
    return PageRange(start, end)


def _parse_int(raw: str, token: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise SplitSpecError(
            "INVALID_RANGE",
            f"«{token}» no contiene números de página válidos.",
        ) from exc
    if value < 1:
        raise SplitSpecError(
            "PAGE_OUT_OF_RANGE",
            f"La página {value} no existe: las páginas empiezan en 1.",
        )
    return value


def _check_page(page: int, page_count: int) -> None:
    if page > page_count:
        raise SplitSpecError(
            "PAGE_OUT_OF_RANGE",
            f"La página {page} no existe: el documento tiene {page_count} página(s).",
        )


def every_ranges(page_count: int, chunk: int) -> list[PageRange]:
    if chunk < 1:
        raise SplitSpecError("INVALID_CHUNK", "El tamaño del grupo debe ser 1 o más.")
    if page_count < 1:
        raise SplitSpecError("NO_PAGES", "El documento no tiene páginas para dividir.")
    return [
        PageRange(start, min(start + chunk - 1, page_count))
        for start in range(1, page_count + 1, chunk)
    ]


def find_overlaps(ranges: Iterable[PageRange]) -> list[int]:
    """Páginas que aparecen en más de un grupo (advertencia, no error)."""
    seen: set[int] = set()
    repeated: set[int] = set()
    for item in ranges:
        for page in item.pages:
            if page in seen:
                repeated.add(page)
            seen.add(page)
    return sorted(repeated)


def sanitize_filename(name: str) -> tuple[str, bool]:
    """Devuelve un nombre seguro para Windows y si hubo que cambiarlo."""
    original = name
    cleaned = "".join("_" if ch in INVALID_CHARS or ord(ch) < 32 else ch for ch in name)
    cleaned = cleaned.strip().rstrip(". ")
    if not cleaned:
        cleaned = "documento"
    stem, dot, suffix = cleaned.rpartition(".")
    if dot and stem and stem.upper() in RESERVED_NAMES:
        cleaned = f"_{cleaned}"
    elif not dot and cleaned.upper() in RESERVED_NAMES:
        cleaned = f"_{cleaned}"
    if len(cleaned) > MAX_FILENAME_STEM:
        root, dot, ext = cleaned.rpartition(".")
        if dot and len(ext) <= 8:
            cleaned = root[: MAX_FILENAME_STEM - len(ext) - 1] + "." + ext
        else:
            cleaned = cleaned[:MAX_FILENAME_STEM]
        cleaned = cleaned.rstrip(". ")
    return cleaned or "documento", cleaned != original


def render_template(
    template: str,
    *,
    name: str,
    index: int,
    start: int,
    end: int,
    pages: int,
    today: date | None = None,
) -> str:
    """Resuelve `{name}`, `{index}`, `{start}`, `{end}`, `{pages}` y `{date}`.

    `{index:02}` usa el formato de Python (dos dígitos); `{date}` es `YYYYMMDD`.
    """
    text = (template or "").strip() or DEFAULT_TEMPLATE
    unknown = [
        match.group(0)
        for match in re.finditer(r"\{[^}]*\}", text)
        if not _TOKEN_RE.fullmatch(match.group(0))
    ]
    if unknown:
        raise SplitSpecError(
            "INVALID_TEMPLATE",
            f"La plantilla usa un token desconocido: {unknown[0]}. "
            "Tokens válidos: {name}, {index}, {start}, {end}, {pages}, {date}.",
        )

    values = {
        "name": name,
        "index": index,
        "start": start,
        "end": end,
        "pages": pages,
        "date": (today or date.today()).strftime("%Y%m%d"),
    }

    def replace(match: re.Match[str]) -> str:
        key, spec = match.group(1), match.group(2)
        value = values[key]
        if spec:
            try:
                value = format(value, spec)
            except (ValueError, TypeError) as exc:
                raise SplitSpecError(
                    "INVALID_TEMPLATE",
                    f"El formato «:{spec}» no se puede aplicar a {{{key}}}.",
                ) from exc
        return str(value)

    rendered = _TOKEN_RE.sub(replace, text)
    if not rendered.strip():
        raise SplitSpecError("INVALID_TEMPLATE", "La plantilla quedó vacía.")
    return rendered


def ensure_pdf_suffix(name: str) -> str:
    return name if name.lower().endswith(".pdf") else f"{name}.pdf"


def unique_output_path(target: Path, used: set[str]) -> Path:
    """Sufijo `_2`, `_3`… sin pisar archivos ni nombres ya planificados."""
    stem, suffix = target.stem, target.suffix
    candidate = target
    counter = 1
    while _is_taken(candidate, used):
        counter += 1
        candidate = target.with_name(f"{stem}_{counter}{suffix}")
    used.add(str(candidate).casefold())
    return candidate


def _is_taken(path: Path, used: set[str]) -> bool:
    return str(path).casefold() in used or path.exists()


def _skip_reason(doc, page_count: int) -> str:
    if doc.status.value == "protected":
        return "El PDF está protegido con contraseña."
    if page_count < 1:
        return "El documento no tiene páginas para dividir."
    return "El documento tiene problemas y no se puede dividir."


def source_stem(doc) -> str:
    raw = ""
    metadata = getattr(doc, "metadata", None) or {}
    if isinstance(metadata, dict):
        raw = str(metadata.get("original_name") or "")
    raw = raw or getattr(doc, "name", "") or Path(getattr(doc, "path", "")).name
    base = Path(raw.replace("\\", "/")).name
    stem = base[:-4] if base.lower().endswith(".pdf") else base
    return stem or "documento"


def default_output_dir(doc, imports_dir: Path | None = None) -> Path:
    """Subcarpeta `<nombre>_partes` junto al origen, o en Descargas si es copia administrada."""
    source = Path(doc.path).expanduser()
    stem = source_stem(doc)
    managed = False
    if imports_dir is not None:
        try:
            managed = source.resolve(strict=False).is_relative_to(imports_dir.resolve(strict=False))
        except (OSError, AttributeError):
            managed = False
    root = (Path.home() / "Downloads") if managed else source.parent
    return root / f"{stem}_partes"


def _resolve_output_dir(
    doc, raw: str, imports_dir: Path | None
) -> Path:
    text = (raw or "").strip()
    if not text:
        return default_output_dir(doc, imports_dir)
    path = Path(text).expanduser()
    if not path.is_absolute() and len(path.parts) == 1:
        return Path.home() / "Downloads" / path.name
    return path


def _mode_ranges(mode: str, params: dict[str, Any], page_count: int) -> list[PageRange]:
    if mode == "ranges":
        return parse_ranges(str(params.get("ranges") or ""), page_count)
    if mode == "every":
        chunk = params.get("every")
        try:
            chunk = int(chunk)
        except (TypeError, ValueError) as exc:
            raise SplitSpecError(
                "INVALID_CHUNK", "Indicá cada cuántas páginas dividir (1 o más)."
            ) from exc
        return every_ranges(page_count, chunk)
    if mode == "single":
        return every_ranges(page_count, 1)
    raise SplitSpecError(
        "INVALID_MODE",
        f"El modo «{mode}» no existe. Usá ranges, every o single.",
    )


class SplitOperation(Operation):
    kind = "split"

    def __init__(self, documents, config=None) -> None:
        super().__init__(documents)
        self.config = config

    # -- helpers -----------------------------------------------------------
    def _selected_documents(self, session_id: str, params: dict[str, Any]):
        docs = self.documents.included(session_id)
        requested = params.get("document_ids")
        if requested:
            wanted = [str(doc_id) for doc_id in requested]
            by_id = {doc.id: doc for doc in docs}
            docs = [by_id[doc_id] for doc_id in wanted if doc_id in by_id]
        return docs

    def _imports_dir(self) -> Path | None:
        if self.config is None:
            return None
        return Path(self.config.imports_dir)

    def _validate_common(self, params: dict[str, Any]) -> tuple[str, str, str]:
        mode = str(params.get("mode") or "ranges").strip().lower()
        policy = str(params.get("collision_policy") or DEFAULT_COLLISION_POLICY).strip().lower()
        template = str(params.get("name_template") or DEFAULT_TEMPLATE)
        if mode not in MODES:
            raise SplitSpecError(
                "INVALID_MODE",
                f"El modo «{mode}» no existe. Usá ranges, every o single.",
            )
        if policy not in COLLISION_POLICIES:
            raise SplitSpecError(
                "INVALID_COLLISION_POLICY",
                f"La política «{policy}» no existe. Usá suffix, fail u overwrite.",
            )
        return mode, policy, template

    # -- plan --------------------------------------------------------------
    def plan(self, session_id: str, params: dict[str, Any]) -> OperationPlan:
        docs = self._selected_documents(session_id, params)
        plan = OperationPlan(kind=self.kind)
        summary: dict[str, Any] = {
            "total_files": 0,
            "total_pages": 0,
            "source_files": len(docs),
            "output_dirs": [],
            "template": str(params.get("name_template") or DEFAULT_TEMPLATE),
            "collision_policy": str(
                params.get("collision_policy") or DEFAULT_COLLISION_POLICY
            ),
            "mode": str(params.get("mode") or "ranges"),
        }
        plan.summary = summary
        if not docs:
            plan.errors.append(
                PlanMessage("NO_DOCUMENTS", "No hay documentos incluidos en el lote.")
            )
            return plan

        try:
            mode, policy, template = self._validate_common(params)
        except SplitSpecError as exc:
            plan.errors.append(PlanMessage(exc.code, exc.message))
            return plan
        summary["mode"] = mode
        summary["template"] = template
        summary["collision_policy"] = policy
        if mode == "ranges":
            summary["ranges"] = str(params.get("ranges") or "")
        elif mode == "every":
            summary["every"] = params.get("every")

        invalid = [doc for doc in docs if doc.status.value in {"invalid", "failed"}]
        if invalid:
            plan.warnings.append(
                PlanMessage(
                    "INVALID_DOCUMENTS",
                    f"{len(invalid)} documento(s) del lote tienen problemas y podrían fallar.",
                )
            )

        explicit_dir = str(params.get("output_dir") or "").strip()
        imports_dir = self._imports_dir()
        used: set[str] = set()
        index = 0
        output_dirs: list[str] = []
        skipped: list[dict[str, str]] = []

        for doc in docs:
            page_count = doc.page_count or 0
            if page_count < 1 or doc.status.value in {"protected", "invalid", "failed"}:
                reason = _skip_reason(doc, page_count)
                skipped.append(
                    {
                        "name": source_stem(doc),
                        "path": doc.path,
                        "reason": reason,
                    }
                )
                plan.warnings.append(
                    PlanMessage("SKIPPED_SOURCE", f"{source_stem(doc)}.pdf: {reason}")
                )
                continue
            try:
                ranges = _mode_ranges(mode, params, page_count)
            except SplitSpecError as exc:
                plan.errors.append(
                    PlanMessage(
                        exc.code,
                        f"{source_stem(doc)}.pdf: {exc.message}",
                    )
                )
                continue

            overlaps = find_overlaps(ranges)
            if overlaps:
                shown = ", ".join(str(page) for page in overlaps[:10])
                extra = f" y {len(overlaps) - 10} más" if len(overlaps) > 10 else ""
                plan.warnings.append(
                    PlanMessage(
                        "OVERLAP",
                        f"{source_stem(doc)}.pdf: las páginas {shown}{extra} aparecen en más de un archivo.",
                    )
                )

            out_dir = _resolve_output_dir(doc, explicit_dir, imports_dir)
            output_dirs.append(str(out_dir))

            for position, page_range in enumerate(ranges, start=1):
                index += 1
                try:
                    rendered = render_template(
                        template,
                        name=source_stem(doc),
                        index=position,
                        start=page_range.start,
                        end=page_range.end,
                        pages=len(page_range.pages),
                    )
                except SplitSpecError as exc:
                    plan.errors.append(PlanMessage(exc.code, exc.message))
                    continue
                filename, changed = sanitize_filename(ensure_pdf_suffix(rendered))
                if changed:
                    plan.warnings.append(
                        PlanMessage(
                            "NAME_SANITIZED",
                            f"«{ensure_pdf_suffix(rendered)}» no es un nombre válido en Windows; se usará «{filename}».",
                        )
                    )
                target = out_dir / filename
                if len(str(target)) > MAX_OUTPUT_PATH_LENGTH:
                    plan.errors.append(
                        PlanMessage(
                            "OUTPUT_PATH_TOO_LONG",
                            f"La ruta de salida supera {MAX_OUTPUT_PATH_LENGTH} caracteres: {target}",
                        )
                    )
                    continue
                if policy == "suffix":
                    target = unique_output_path(target, used)
                elif policy == "fail" and _is_taken(target, used):
                    plan.errors.append(
                        PlanMessage(
                            "OUTPUT_EXISTS",
                            f"Ya existe un archivo con ese nombre: {target}. "
                            "Cambiá la plantilla o usá la política «suffix».",
                        )
                    )
                    continue
                else:
                    used.add(str(target).casefold())
                plan.items.append(
                    PlanItem(
                        index=index,
                        label=target.name,
                        pages=page_range.pages,
                        exists=target.exists(),
                        output_path=str(target),
                        source_path=doc.path,
                    )
                )
                summary["total_files"] += 1
                summary["total_pages"] += len(page_range.pages)

        summary["output_dirs"] = sorted(set(output_dirs))
        summary["skipped"] = skipped
        if not plan.items and not plan.errors and not skipped:
            plan.errors.append(
                PlanMessage("NO_OUTPUTS", "La configuración no genera ningún archivo.")
            )
        return plan

    # -- execute -----------------------------------------------------------
    def execute(
        self, plan: OperationPlan, ctx: JobContext, params: dict[str, Any]
    ) -> OperationResult:
        policy = str(params.get("collision_policy") or DEFAULT_COLLISION_POLICY).lower()
        executed: list[ExecutedItem] = []
        errors: list[dict[str, Any]] = []
        total_pages = 0
        published = 0
        cancelled = False
        total = len(plan.items)

        for entry in plan.summary.get("skipped") or []:
            errors.append(
                {
                    "code": "SKIPPED_SOURCE",
                    "path": entry.get("path"),
                    "message": f"{entry.get('name')}.pdf: {entry.get('reason')}",
                }
            )

        by_source: dict[str, list[PlanItem]] = {}
        for item in plan.items:
            by_source.setdefault(item.source_path or "", []).append(item)

        processed_index = 0
        for source_path, items in by_source.items():
            if cancelled:
                break
            try:
                source = _open_source(source_path)
            except Exception as exc:  # noqa: BLE001
                message = _read_error(exc)
                for item in items:
                    processed_index += 1
                    ctx.item(item.index, item.label, "failed", message=message)
                    executed.append(
                        ExecutedItem(item.index, item.label, "failed", None, message)
                    )
                    errors.append(
                        {
                            "path": source_path,
                            "output_path": item.output_path,
                            "message": message,
                        }
                    )
                continue

            try:
                for item in items:
                    if ctx.cancelled:
                        cancelled = True
                        ctx.item(item.index, item.label, "cancelled", message="Cancelado por el usuario.")
                        executed.append(
                            ExecutedItem(item.index, item.label, "cancelled", None, "Cancelado por el usuario.")
                        )
                        break

                    processed_index += 1
                    ctx.item(item.index, item.label, "processing")
                    target = Path(item.output_path or "")
                    try:
                        target = _reserve_target(target, policy)
                        _extract_pages(source, item.pages or [], target, ctx.tmp_dir)
                        _verify_pdf(target, len(item.pages or []))
                        published += 1
                        total_pages += len(item.pages or [])
                        ctx.item(item.index, item.label, "completed", output_path=str(target))
                        executed.append(
                            ExecutedItem(item.index, item.label, "completed", str(target))
                        )
                    except Exception as exc:  # noqa: BLE001
                        message = _read_error(exc)
                        ctx.item(item.index, item.label, "failed", message=message)
                        executed.append(
                            ExecutedItem(item.index, item.label, "failed", None, message)
                        )
                        errors.append(
                            {
                                "path": source_path,
                                "output_path": str(target),
                                "message": message,
                            }
                        )
                    done = processed_index
                    ctx.progress(
                        "splitting",
                        100.0 * done / max(1, total),
                        current=item.label,
                        done=done,
                        total=total,
                    )
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

        output_dirs = sorted(
            {
                str(Path(item.output_path).parent)
                for item in plan.items
                if item.output_path
            }
        )
        output = {
            "status": status,
            "total_files": published,
            "total_pages": total_pages,
            "output_dirs": output_dirs,
            "output_path": output_dirs[0] if len(output_dirs) == 1 else None,
            "outputs": [item.output_path for item in executed if item.status == "completed"],
            "errors": errors,
            "cancelled": cancelled,
            "policy": policy,
        }
        return OperationResult(
            status=status,
            output=output,
            items=executed,
            errors=errors,
            total_items=total,
            total_pages=total_pages,
        )


# -- PyMuPDF helpers --------------------------------------------------------


def _open_source(path: str):
    import pymupdf

    if not path or not Path(path).is_file():
        raise FileNotFoundError(f"El archivo de origen no existe: {path}")
    doc = pymupdf.open(path)
    if doc.needs_pass:
        doc.close()
        raise PermissionError("El PDF está protegido con contraseña.")
    return doc


def _close_source(doc) -> None:
    try:
        doc.close()
    except Exception:  # noqa: BLE001
        pass


def _extract_pages(source, pages: list[int], target: Path, tmp_dir: Path) -> None:
    import pymupdf

    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    partial = tmp_dir / f".{uuid.uuid4().hex}.pdf"
    doc = pymupdf.open()
    try:
        for page in pages:
            doc.insert_pdf(source, from_page=page - 1, to_page=page - 1)
        doc.save(partial, garbage=3, deflate=True)
    finally:
        doc.close()
    try:
        os.replace(partial, target)
    finally:
        partial.unlink(missing_ok=True)


def _verify_pdf(path: Path, expected_pages: int) -> None:
    import pymupdf

    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("El archivo generado está vacío.")
    check = pymupdf.open(path)
    try:
        if check.page_count != expected_pages:
            raise RuntimeError(
                f"El archivo generado tiene {check.page_count} página(s) y se esperaban {expected_pages}."
            )
        if not check.is_pdf:
            raise RuntimeError("El archivo generado no es un PDF válido.")
    finally:
        check.close()


def _reserve_target(target: Path, policy: str) -> Path:
    if policy == "overwrite" or not target.exists():
        return target
    if policy == "fail":
        raise FileExistsError(f"El archivo ya existe: {target}")
    return unique_output_path(target, set())


def _read_error(exc: Exception) -> str:
    if isinstance(exc, PermissionError):
        return str(exc) or "El PDF está protegido con contraseña."
    if isinstance(exc, FileNotFoundError):
        return str(exc) or "El archivo ya no existe."
    text = str(exc).strip()
    return f"No se pudo generar el archivo: {text}" if text else "No se pudo generar el archivo."
