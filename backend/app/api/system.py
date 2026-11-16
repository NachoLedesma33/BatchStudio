from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_services
from app.core.errors import ApiError
from app.schemas.api import PickFilesRequest, RevealRequest, SavePathRequest
from app.services.container import Services
from app.services.native_dialog import run_native_dialog

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.post("/system/pick-folder")
def pick_folder(
    initial_dir: str | None = Query(default=None),
    services: Services = Depends(get_services),
):
    result = run_native_dialog("folder", initial_dir, None)
    if result.get("path"):
        services.path_policy.approve_dialog_path(str(result["path"]))
    return {"path": result.get("path")}


@router.post("/system/pick-save-path")
def pick_save_path(req: SavePathRequest, services: Services = Depends(get_services)):
    result = run_native_dialog("save", req.initial_dir, req.initial_name)
    if result.get("path"):
        services.path_policy.approve_dialog_path(str(result["path"]))
    return {"path": result.get("path")}


@router.post("/system/pick-files")
def pick_files(req: PickFilesRequest, services: Services = Depends(get_services)):
    result = run_native_dialog("files", req.initial_dir, None)
    paths = [str(path) for path in (result.get("paths") or []) if path]
    for path in paths:
        services.path_policy.approve_dialog_path(path)
    return {"paths": paths}


@router.post("/system/reveal")
def reveal_path(req: RevealRequest, services: Services = Depends(get_services)):
    path: Path = services.path_policy.assert_revealable(req.path)
    try:
        if sys.platform.startswith("win"):
            if path.is_dir():
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["explorer", "/select,", str(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(path)] if path.is_file() else ["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path.parent if path.is_file() else path)])
    except Exception as exc:  # noqa: BLE001
        raise ApiError(
            "REVEAL_FAILED",
            "No se pudo abrir la ruta.",
            status_code=500,
            context={"detail": str(exc)},
        ) from exc
    return {"ok": True}


@router.get("/history")
def list_history(
    limit: int = Query(default=50, ge=1, le=500),
    services: Services = Depends(get_services),
):
    return {"history": services.history.list(limit)}


@router.get("/history/export")
def export_history(
    format: str = Query(default="json"),
    limit: int = Query(default=500, ge=1, le=5000),
    services: Services = Depends(get_services),
):
    history = services.history.list(limit)
    if format.lower() == "json":
        return {"format": "json", "items": history}
    if format.lower() == "csv":
        import csv
        import io

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["id", "job_id", "kind", "summary", "created_at"])
        for item in history:
            writer.writerow([item.get("id"), item.get("job_id"), item.get("kind"), item.get("summary"), item.get("created_at")])
        return {"format": "csv", "content": buffer.getvalue()}
    lines = [f"{item.get('created_at')} - {item.get('kind')} - {item.get('summary')}" for item in history]
    return {"format": "txt", "content": "\n".join(lines)}
