from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

import pymupdf

from app.core.config import AppConfig

TOOL_CANDIDATES: dict[str, list[str]] = {
    "tesseract": ["tesseract"],
    "libreoffice": ["soffice", "libreoffice"],
    "qpdf": ["qpdf"],
    "ghostscript": ["gswin64c", "gswin32c", "gs"],
}

TOOL_NOTES = {
    "tesseract": "Necesario para OCR. Sin Tesseract, OCR queda «No disponible».",
    "libreoffice": "Necesario para convertir Office a PDF. Sin LibreOffice, esa función queda «No disponible».",
    "qpdf": "Opcional para reparaciones y validaciones avanzadas.",
    "ghostscript": "Opcional para compresión avanzada con Ghostscript.",
}


def _pymupdf_version() -> str:
    version = getattr(pymupdf, "__version__", None)
    if isinstance(version, str) and version:
        return version
    version = getattr(pymupdf, "VersionBind", None)
    if isinstance(version, str) and version:
        return version
    try:
        return metadata.version("PyMuPDF")
    except metadata.PackageNotFoundError:
        return "desconocida"


def _ghostscript_glob() -> list[str]:
    if not sys.platform.startswith("win"):
        return []
    candidates: list[str] = []
    for base in (Path("C:/Program Files/gs"), Path("C:/Program Files (x86)/gs")):
        if base.is_dir():
            candidates.extend(str(path) for path in base.glob("gs*/bin/gswin64c.exe"))
    return candidates


def _find_executable(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    if name in {"gswin64c", "gswin32c"}:
        for candidate in _ghostscript_glob():
            if Path(candidate).name.lower() == f"{name.lower()}.exe":
                return candidate
    return None


def _detect_tool(name: str) -> dict[str, Any]:
    executable = _find_executable(name)
    if not executable:
        return {
            "available": False,
            "path": None,
            "version": None,
            "note": TOOL_NOTES[name],
        }
    command = [executable]
    if name == "libreoffice":
        command.append("--version")
    else:
        command.append("--version")
    kwargs: dict[str, Any] = {
        "capture_output": True,
        "text": True,
        "timeout": 1.5,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        proc = subprocess.run(command, **kwargs)
        output = (proc.stdout or proc.stderr or "").strip().splitlines()
        version = output[0][:200] if output else None
        available = proc.returncode == 0 or bool(version)
    except (OSError, subprocess.TimeoutExpired):
        available = True  # existe, pero no respondió a --version a tiempo
        version = None
    return {
        "available": available,
        "path": executable,
        "version": version,
        "note": TOOL_NOTES[name],
    }


class CapabilityService:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._lock = threading.Lock()
        self._cached: dict[str, Any] | None = None
        self._cached_at = 0.0

    def detect(self, *, force: bool = False) -> dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            if (
                not force
                and self._cached is not None
                and now - self._cached_at < self.config.capabilities_ttl_seconds
            ):
                return self._cached
            with ThreadPoolExecutor(max_workers=len(TOOL_CANDIDATES)) as pool:
                futures = {name: pool.submit(_detect_tool, name) for name in TOOL_CANDIDATES}
                tools = {name: future.result() for name, future in futures.items()}
            payload = {
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "platform": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "python": platform.python_version(),
                },
                "pdf_engine": {
                    "name": "PyMuPDF",
                    "available": True,
                    "version": _pymupdf_version(),
                },
                "tools": tools,
            }
            self._cached = payload
            self._cached_at = now
            return payload
