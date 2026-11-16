from __future__ import annotations

import re
from pathlib import Path

from app.db.connection import Database

_MIGRATION_RE = re.compile(r"^(\d{3})_.+\.sql$")


def _migration_files(directory: Path) -> list[tuple[int, Path]]:
    files: list[tuple[int, Path]] = []
    for path in sorted(directory.glob("*.sql")):
        match = _MIGRATION_RE.match(path.name)
        if not match:
            raise ValueError(f"Nombre de migración inválido: {path.name}")
        files.append((int(match.group(1)), path))
    versions = [version for version, _ in files]
    if versions != sorted(set(versions)):
        raise ValueError("Las migraciones tienen versiones duplicadas o desordenadas.")
    return files


def _split_statements(sql: str) -> list[str]:
    # El esquema v1 no usa triggers ni puntos y coma dentro de literales.
    statements: list[str] = []
    buffer: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buffer.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
    remainder = "\n".join(buffer).strip()
    if remainder:
        statements.append(remainder)
    return statements


def migrate(db: Database, migrations_dir: Path | None = None) -> int:
    """Aplica migraciones pendientes y devuelve la versión final.

    Cada archivo corre en su propia transacción y actualiza `user_version`.
    Reejecutar el migrador no hace nada si ya está al día.
    """
    directory = Path(migrations_dir) if migrations_dir else _default_migrations_dir()
    current = db.user_version()
    for version, path in _migration_files(directory):
        if version <= current:
            continue
        statements = _split_statements(path.read_text(encoding="utf-8"))
        with db.transaction(immediate=True) as conn:
            for statement in statements:
                conn.execute(statement)
            conn.execute(f"PRAGMA user_version = {version}")
        current = version
    return current


def _default_migrations_dir() -> Path:
    from app.core.config import CONFIG

    return CONFIG.migrations_dir


def schema_versions(migrations_dir: Path | None = None) -> list[int]:
    directory = Path(migrations_dir) if migrations_dir else _default_migrations_dir()
    return [version for version, _ in _migration_files(directory)]
