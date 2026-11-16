from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import capabilities as capabilities_api
from app.api import documents as documents_api
from app.api import jobs as jobs_api
from app.api import legacy_merge as legacy_merge_api
from app.api import operations as operations_api
from app.api import pages as pages_api
from app.api import rename as rename_api
from app.api import sessions as sessions_api
from app.api import settings as settings_api
from app.api import system as system_api
from app.core.config import CONFIG
from app.core.errors import ApiError, api_error_handler
from app.core.security import install_security_middleware, new_token
from app.services.container import Services, build_services
from app.services.native_dialog import DIALOG_SCRIPT as _DIALOG_SCRIPT  # noqa: F401

UI_DIR_NAME = "ui"


def _ui_dir() -> Optional[Path]:
    """Carpeta con la interfaz compilada (frontend/dist), si existe."""
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        bundle = getattr(sys, "_MEIPASS", None)
        if bundle:
            candidates.append(Path(bundle) / UI_DIR_NAME)
        candidates.append(Path(sys.executable).resolve().parent / UI_DIR_NAME)
    candidates.append(Path(__file__).resolve().parents[2] / "frontend" / "dist")
    for candidate in candidates:
        if (candidate / "index.html").is_file():
            return candidate
    return None


def create_app(
    *,
    services: Services | None = None,
    require_token: bool | None = None,
    strict_host: bool = True,
    start_worker: bool = True,
    token: str | None = None,
) -> FastAPI:
    container = services or build_services()
    token_value = token or new_token()
    token_required = (not container.config.dev_no_token) if require_token is None else require_token

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if start_worker:
            container.worker.start()
        try:
            yield
        finally:
            container.worker.stop()

    app = FastAPI(
        title="PDF Batch Studio",
        version="0.2.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.services = container
    app.state.token = token_value
    app.state.require_token = token_required

    app.add_exception_handler(ApiError, api_error_handler)  # type: ignore[arg-type]

    install_security_middleware(
        app,
        token=token_value,
        require_token=token_required,
        strict_host=strict_host,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(system_api.router)
    app.include_router(capabilities_api.router)
    app.include_router(sessions_api.router)
    app.include_router(settings_api.router)
    app.include_router(documents_api.router)
    app.include_router(pages_api.router)
    app.include_router(rename_api.router)
    app.include_router(operations_api.router)
    app.include_router(jobs_api.router)
    app.include_router(legacy_merge_api.router)

    ui_dir = _ui_dir()
    if ui_dir is not None:
        app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="ui")
    return app


app = create_app()
_UI_DIR = _ui_dir()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=CONFIG.host, port=CONFIG.port, reload=True)
