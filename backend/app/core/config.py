from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_DATA_DIR = Path.home() / ".pdf-batch-studio"


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name, "").strip()
    return Path(raw).expanduser() if raw else default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass
class AppConfig:
    """Rutas y límites reales que usa la aplicación.

    `PDFBS_DATA_DIR` es la única raíz de datos: base de datos, caché,
    importaciones administradas y temporales viven debajo de ella.
    """

    host: str = "127.0.0.1"
    port: int = 8765
    data_dir: Path = field(default_factory=lambda: _env_path("PDFBS_DATA_DIR", DEFAULT_DATA_DIR))
    db_name: str = "app.db"
    worker_count: int = field(default_factory=lambda: max(1, _env_int("PDFBS_WORKER_COUNT", 1)))
    max_files: int = field(default_factory=lambda: _env_int("PDFBS_MAX_FILES", 10000))
    max_path_length: int = field(default_factory=lambda: _env_int("PDFBS_MAX_PATH_LENGTH", 4096))
    thumb_cache_mb: int = field(default_factory=lambda: _env_int("PDFBS_THUMB_CACHE_MB", 512))
    capabilities_ttl_seconds: float = 60.0
    dev_no_token: bool = field(default_factory=lambda: os.environ.get("PDFBS_DEV_NO_TOKEN") == "1")

    # Rutas derivadas -------------------------------------------------------
    @property
    def db_dir(self) -> Path:
        return self.data_dir / "db"

    @property
    def db_path(self) -> Path:
        return self.db_dir / self.db_name

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def thumbnail_cache(self) -> Path:
        return self.cache_dir / "thumbs"

    @property
    def imports_dir(self) -> Path:
        return self.data_dir / "imports"

    @property
    def temp_dir(self) -> Path:
        return self.data_dir / "tmp"

    @property
    def session_dir(self) -> Path:
        return self.data_dir / "sessions"

    @property
    def migrations_dir(self) -> Path:
        return Path(__file__).resolve().parents[1] / "db" / "migrations"

    def ensure_dirs(self) -> None:
        for path in (
            self.data_dir,
            self.db_dir,
            self.cache_dir,
            self.thumbnail_cache,
            self.imports_dir,
            self.temp_dir,
            self.session_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


def build_config() -> AppConfig:
    config = AppConfig()
    config.ensure_dirs()
    return config


CONFIG = build_config()
