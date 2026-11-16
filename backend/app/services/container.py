from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.config import CONFIG, AppConfig
from app.db.connection import Database
from app.db.migrate import migrate
from app.db.repositories.documents import DocumentRepository
from app.db.repositories.history import HistoryRepository
from app.db.repositories.jobs import JobRepository
from app.db.repositories.pages import PageRepository
from app.db.repositories.sessions import DEFAULT_SESSION_ID, SessionRepository
from app.db.repositories.settings import SettingsRepository
from app.operations.extract import ExtractOperation
from app.operations.merge import MergeOperation
from app.operations.registry import OperationRegistry
from app.operations.rotate import RotateOperation
from app.operations.split import SplitOperation
from app.services.capabilities import CapabilityService
from app.services.event_bus import EventBus
from app.services.job_worker import JobWorker
from app.services.path_policy import PathPolicy
from app.services.preview_cache import PreviewCache


@dataclass
class Services:
    config: AppConfig
    db: Database
    sessions: SessionRepository
    documents: DocumentRepository
    pages: PageRepository
    jobs: JobRepository
    history: HistoryRepository
    settings: SettingsRepository
    registry: OperationRegistry
    worker: JobWorker
    events: EventBus
    path_policy: PathPolicy
    previews: PreviewCache
    capabilities: CapabilityService

    def close(self) -> None:
        self.worker.stop()
        self.db.close()


def build_services(config: AppConfig | None = None, *, db_path: str | Path | None = None) -> Services:
    cfg = config or CONFIG
    cfg.ensure_dirs()
    db = Database(db_path or cfg.db_path)
    migrate(db, cfg.migrations_dir)

    sessions = SessionRepository(db)
    documents = DocumentRepository(db)
    pages = PageRepository(db)
    jobs = JobRepository(db)
    history = HistoryRepository(db)
    settings = SettingsRepository(db)
    sessions.ensure_default()

    registry = OperationRegistry()
    registry.register(MergeOperation(documents))
    registry.register(SplitOperation(documents, cfg))
    registry.register(ExtractOperation(documents, cfg))
    registry.register(RotateOperation(documents, cfg))

    events = EventBus()
    worker = JobWorker(
        jobs=jobs,
        history=history,
        registry=registry,
        tmp_root=cfg.temp_dir,
        bus=events,
    )
    return Services(
        config=cfg,
        db=db,
        sessions=sessions,
        documents=documents,
        pages=pages,
        jobs=jobs,
        history=history,
        settings=settings,
        registry=registry,
        worker=worker,
        events=events,
        path_policy=PathPolicy(cfg, documents, jobs),
        previews=PreviewCache(cfg),
        capabilities=CapabilityService(cfg),
    )


__all__ = ["Services", "build_services", "DEFAULT_SESSION_ID"]
