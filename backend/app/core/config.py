from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppConfig:
    host: str = "127.0.0.1"
    port: int = 8765
    temp_dir: Path = Path(os.environ.get("PDFBS_TEMP_DIR", "") or (Path.home() / ".pdf-batch-studio" / "temp"))
    session_dir: Path = Path(os.environ.get("PDFBS_SESSION_DIR", "") or (Path.home() / ".pdf-batch-studio" / "sessions"))
    thumbnail_cache: Path = Path(os.environ.get("PDFBS_THUMB_DIR", "") or (Path.home() / ".pdf-batch-studio" / "thumbs"))
    max_files: int = 10000
    max_path_length: int = 4096

    def ensure_dirs(self) -> None:
        for p in (self.temp_dir, self.session_dir, self.thumbnail_cache):
            p.mkdir(parents=True, exist_ok=True)


CONFIG = AppConfig()
CONFIG.ensure_dirs()
