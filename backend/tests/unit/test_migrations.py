from __future__ import annotations

from pathlib import Path

from app.db.connection import Database
from app.db.migrate import migrate, schema_versions


def test_migrations_create_schema(tmp_path: Path, services) -> None:
    db = Database(tmp_path / "fresh.db")
    try:
        version = migrate(db, services.config.migrations_dir)
        assert version == 1
        assert db.user_version() == 1
        tables = {
            row[0]
            for row in db.connect()
            .execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            .fetchall()
        }
        assert {
            "sessions",
            "session_documents",
            "document_pages",
            "operations",
            "jobs",
            "job_items",
            "history",
            "settings",
        } <= tables
        indexes = {
            row[0]
            for row in db.connect()
            .execute("SELECT name FROM sqlite_master WHERE type = 'index'")
            .fetchall()
        }
        assert "idx_jobs_status_created" in indexes
        assert "idx_history_created" in indexes
    finally:
        db.close()


def test_migrations_are_idempotent(tmp_path: Path, services) -> None:
    db = Database(tmp_path / "again.db")
    try:
        first = migrate(db, services.config.migrations_dir)
        second = migrate(db, services.config.migrations_dir)
        assert first == second == 1
        assert db.user_version() == 1
        assert schema_versions(services.config.migrations_dir) == [1]
    finally:
        db.close()
