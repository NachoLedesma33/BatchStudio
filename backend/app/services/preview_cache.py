from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pymupdf

from app.core.config import AppConfig


class PreviewCache:
    """Miniaturas PNG en disco, con clave por archivo, versión y página."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        config.thumbnail_cache.mkdir(parents=True, exist_ok=True)

    def render(self, path: str | Path, page: int, scale: float = 2.0) -> Path:
        source = Path(path)
        stat = source.stat()
        key = hashlib.sha256(
            f"{source.resolve(strict=False)}|{stat.st_mtime_ns}|{stat.st_size}|{page}|{scale:.3f}".encode()
        ).hexdigest()
        target = self.config.thumbnail_cache / f"{key}.png"
        if target.is_file():
            try:
                os.utime(target)
            except OSError:
                pass
            return target

        with pymupdf.open(str(source)) as document:
            if page < 1 or page > document.page_count:
                raise ValueError(f"Página fuera de rango: {page} de {document.page_count}.")
            pixmap = document[page - 1].get_pixmap(matrix=pymupdf.Matrix(scale, scale))
            png = pixmap.tobytes("png")

        tmp = target.with_suffix(".png.tmp")
        tmp.write_bytes(png)
        os.replace(tmp, target)
        self._enforce_budget()
        return target

    def _enforce_budget(self) -> None:
        budget = self.config.thumb_cache_mb * 1024 * 1024
        files = []
        total = 0
        for item in self.config.thumbnail_cache.glob("*.png"):
            try:
                stat = item.stat()
            except OSError:
                continue
            total += stat.st_size
            files.append((stat.st_mtime_ns, stat.st_size, item))
        if total <= budget:
            return
        for _, size, item in sorted(files):
            try:
                item.unlink()
                total -= size
            except OSError:
                pass
            if total <= budget:
                break
