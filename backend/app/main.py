from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from app.core.config import CONFIG
from app.models.document import PdfDocument, PdfStatus
from app.schemas.api import (
    ImportFolderRequest,
    ImportPathsRequest,
    MergeJobRequest,
    ReorderRequest,
    UpdateDocumentRequest,
)
from app.services.job_manager import JOB_MANAGER
from app.services.pdf_inspector import inspect_pdf, inspect_folder
from app.services.pdf_merger import merge_pdfs
from app.services.session_store import STORE

app = FastAPI(title="PDF Batch Studio", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

IMPORT_DIR = CONFIG.temp_dir / "imports"
IMPORT_DIR.mkdir(parents=True, exist_ok=True)


def _doc_to_dict(d: PdfDocument) -> dict:
    return d.to_dict()


@app.get("/api/health")
def health():
    return {"status": "ok"}


class RevealRequest(BaseModel):
    path: str


class SavePathRequest(BaseModel):
    initial_dir: Optional[str] = None
    initial_name: Optional[str] = None


# El diálogo nativo corre en un PROCESO aparte: así no bloquea el hilo del
# servidor con el bucle de Tk y siempre aparece en primer plano sobre el navegador.
_DIALOG_SCRIPT = r"""
import json
import sys

import tkinter as tk
from tkinter import filedialog

kind = sys.argv[1]
initial_dir = sys.argv[2] or None
initial_name = sys.argv[3] or None

root = tk.Tk()
root.withdraw()
root.update_idletasks()
try:
    root.attributes("-topmost", True)
except Exception:
    pass
root.lift()
try:
    root.focus_force()
except Exception:
    pass

if kind == "save":
    result = filedialog.asksaveasfilename(
        parent=root,
        title="Guardar PDF como",
        initialdir=initial_dir,
        initialfile=initial_name or "documentos_unidos.pdf",
        defaultextension=".pdf",
        filetypes=[("Documento PDF", "*.pdf"), ("Todos los archivos", "*.*")],
    )
else:
    result = filedialog.askdirectory(
        parent=root,
        title="Elegí la carpeta de destino",
        initialdir=initial_dir,
        mustexist=True,
    )

root.destroy()
sys.stdout.write(json.dumps({"path": result or None}))
"""


def _default_dir() -> str:
    """Carpeta donde abrir el diálogo si no se indica otra."""
    downloads = Path.home() / "Downloads"
    return str(downloads if downloads.is_dir() else Path.home())


def _native_dialog(kind: str, initial_dir: Optional[str], initial_name: Optional[str]) -> Optional[str]:
    start = _default_dir()
    if initial_dir:
        cand = Path(initial_dir).expanduser()
        if cand.is_dir():
            start = str(cand)

    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    proc = subprocess.run(
        [sys.executable, "-c", _DIALOG_SCRIPT, kind, start, initial_name or ""],
        capture_output=True,
        text=True,
        creationflags=creationflags,
    )
    if proc.returncode != 0:
        raise HTTPException(500, f"No se pudo abrir el diálogo del sistema: {proc.stderr.strip()}")
    try:
        return json.loads(proc.stdout.strip() or "{}").get("path")
    except json.JSONDecodeError:
        return None


@app.post("/api/system/pick-folder")
def pick_folder(initial_dir: Optional[str] = None):
    """Abre el diálogo nativo de carpetas y devuelve la ruta elegida."""
    return {"path": _native_dialog("folder", initial_dir, None)}


@app.post("/api/system/pick-save-path")
def pick_save_path(req: SavePathRequest):
    """Abre el diálogo nativo 'Guardar como' y devuelve la ruta completa elegida."""
    return {"path": _native_dialog("save", req.initial_dir, req.initial_name)}


@app.post("/api/system/reveal")
def reveal_path(req: RevealRequest):
    """Abre un archivo o carpeta en el explorador del sistema operativo."""
    p = Path(req.path).expanduser()
    if not p.exists():
        raise HTTPException(404, "La ruta no existe")
    try:
        if sys.platform.startswith("win"):
            if p.is_dir():
                os.startfile(str(p))  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["explorer", "/select,", str(p)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", str(p)] if p.is_file() else ["open", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p.parent if p.is_file() else p)])
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"No se pudo abrir la ruta: {exc}")
    return {"ok": True}


@app.post("/api/files/import")
def import_paths(req: ImportPathsRequest):
    results = []
    for p in req.paths:
        doc = inspect_pdf(p)
        STORE.add(doc)
        results.append(_doc_to_dict(doc))
    return {"documents": results}


@app.post("/api/folders/import")
def import_folder(req: ImportFolderRequest):
    docs = inspect_folder(req.folder, req.recursive)
    out = []
    for d in docs:
        STORE.add(d)
        out.append(_doc_to_dict(d))
    return {"documents": out}


@app.post("/api/files/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    results = []
    for uf in files:
        if not uf.filename or not uf.filename.lower().endswith(".pdf"):
            continue
        dest = IMPORT_DIR / f"{uuid.uuid4()}_{Path(uf.filename).name}"
        with dest.open("wb") as f:
            shutil.copyfileobj(uf.file, f)
        doc = inspect_pdf(dest)
        doc.metadata["original_name"] = uf.filename
        STORE.add(doc)
        results.append(_doc_to_dict(doc))
    return {"documents": results}


@app.get("/api/documents")
def list_documents():
    return {"documents": STORE.to_list_dict()}


@app.get("/api/documents/{doc_id}")
def get_document(doc_id: str):
    d = STORE.get(doc_id)
    if not d:
        raise HTTPException(404, "Documento no encontrado")
    return _doc_to_dict(d)


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: str):
    ok = STORE.remove(doc_id)
    if not ok:
        raise HTTPException(404, "Documento no encontrado")
    return {"ok": True}


@app.patch("/api/documents/order")
def reorder_documents(req: ReorderRequest):
    ok = STORE.reorder(req.ids)
    if not ok:
        raise HTTPException(400, "Orden inválido")
    return {"documents": STORE.to_list_dict()}


@app.patch("/api/documents/{doc_id}")
def update_document(doc_id: str, req: UpdateDocumentRequest):
    kwargs = {}
    if req.included is not None:
        kwargs["included"] = req.included
    if req.name is not None:
        kwargs["name"] = req.name
    d = STORE.update(doc_id, **kwargs)
    if not d:
        raise HTTPException(404, "Documento no encontrado")
    return _doc_to_dict(d)


@app.get("/api/documents/{doc_id}/preview/{page}")
def preview_page(doc_id: str, page: int, scale: float = 2.0):
    d = STORE.get(doc_id)
    if not d:
        raise HTTPException(404, "Documento no encontrado")
    p = Path(d.path)
    if not p.exists():
        raise HTTPException(404, "Archivo no encontrado")
    try:
        import fitz

        doc = fitz.open(str(p))
        if page < 1 or page > doc.page_count:
            doc.close()
            raise HTTPException(400, "Página fuera de rango")
        pg = doc[page - 1]
        pix = pg.get_pixmap(matrix=fitz.Matrix(scale, scale))
        png = pix.tobytes("png")
        doc.close()
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Error al renderizar: {exc}")
    return StreamingResponse(iter([png]), media_type="image/png")


@app.post("/api/merge-jobs")
def create_merge_job(req: MergeJobRequest):
    docs = [d for d in STORE.list() if d.included]
    ordered = sorted(docs, key=lambda d: d.order_index)
    paths = [d.path for d in ordered]
    if len(paths) < 1:
        raise HTTPException(400, "No hay documentos incluidos")
    if req.output_path:
        raw = req.output_path.strip()
        p = Path(raw)
        # If user gives only a file name, save it to Downloads for convenience.
        if not p.is_absolute() and len(p.parts) == 1:
            downloads = Path.home() / "Downloads"
            downloads.mkdir(parents=True, exist_ok=True)
            out = downloads / p.name
        else:
            out = p
            out.parent.mkdir(parents=True, exist_ok=True)
    else:
        downloads = Path.home() / "Downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        out = downloads / "documentos_unidos.pdf"
    job = JOB_MANAGER.create(paths, str(out), overwrite=req.overwrite)
    return {"job_id": job.job_id}


@app.get("/api/merge-jobs/{job_id}")
def get_merge_job(job_id: str):
    job = JOB_MANAGER.get(job_id)
    if not job:
        raise HTTPException(404, "Trabajo no encontrado")
    return job.snapshot()


@app.get("/api/merge-jobs/{job_id}/events")
def merge_job_events(job_id: str):
    job = JOB_MANAGER.get(job_id)
    if not job:
        raise HTTPException(404, "Trabajo no encontrado")

    def gen():
        idx = 0
        while True:
            with job._lock:
                events = list(job.events[idx:])
                idx = len(job.events)
                status = job.status
            for ev in events:
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
            if status in ("completed", "completed_with_errors", "failed", "cancelled"):
                # send final snapshot
                yield f"data: {json.dumps({'type': 'done', 'status': status}, ensure_ascii=False)}\n\n"
                break
            time.sleep(0.2)

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/api/merge-jobs/{job_id}/cancel")
def cancel_merge_job(job_id: str):
    ok = JOB_MANAGER.cancel(job_id)
    if not ok:
        raise HTTPException(404, "Trabajo no encontrado")
    return {"ok": True}


@app.get("/api/merge-jobs/{job_id}/report")
def merge_job_report(job_id: str):
    job = JOB_MANAGER.get(job_id)
    if not job:
        raise HTTPException(404, "Trabajo no encontrado")
    return job.result or job.snapshot()


@app.post("/api/sessions/save")
def save_session(req: dict = None):
    import json

    path = CONFIG.session_dir / f"session_{uuid.uuid4().hex[:8]}.json"
    data = {"documents": STORE.to_list_dict()}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"path": str(path)}


@app.post("/api/sessions/load")
def load_session(req: dict):
    import json

    path = Path(req.get("path", ""))
    if not path.exists():
        raise HTTPException(404, "Archivo no encontrado")
    data = json.loads(path.read_text(encoding="utf-8"))
    STORE.clear()
    for d in data.get("documents", []):
        doc = PdfDocument(**{k: v for k, v in d.items() if k in PdfDocument.__dataclass_fields__})
        # status enum
        try:
            doc.status = PdfStatus(d.get("status", "pending"))
        except Exception:  # noqa: BLE001
            doc.status = PdfStatus.PENDING
        STORE.add(doc)
    return {"documents": STORE.to_list_dict()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=CONFIG.port, reload=True)
