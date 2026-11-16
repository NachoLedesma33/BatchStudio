from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

DIALOG_SCRIPT = r"""
import json
import sys

import tkinter as tk
from tkinter import filedialog

kind = sys.argv[1]
initial_dir = sys.argv[2] or None
initial_name = sys.argv[3] or None
out_file = sys.argv[4]

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

paths = []
if kind == "save":
    result = filedialog.asksaveasfilename(
        parent=root,
        title="Guardar PDF como",
        initialdir=initial_dir,
        initialfile=initial_name or "documentos_unidos.pdf",
        defaultextension=".pdf",
        filetypes=[("Documento PDF", "*.pdf"), ("Todos los archivos", "*.*")],
    )
    if result:
        paths = [result]
elif kind == "files":
    result = filedialog.askopenfilenames(
        parent=root,
        title="Elegí archivos PDF",
        initialdir=initial_dir,
        filetypes=[("Documento PDF", "*.pdf"), ("Todos los archivos", "*.*")],
    )
    paths = list(result or [])
else:
    result = filedialog.askdirectory(
        parent=root,
        title="Elegí la carpeta de destino",
        initialdir=initial_dir,
        mustexist=True,
    )
    if result:
        paths = [result]

root.destroy()
with open(out_file, "w", encoding="utf-8") as fh:
    fh.write(json.dumps({"path": paths[0] if paths else None, "paths": paths}))
"""


def default_dir() -> str:
    downloads = Path.home() / "Downloads"
    return str(downloads if downloads.is_dir() else Path.home())


def dialog_command(kind: str, start: str, initial_name: str, out_file: str) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--native-dialog", kind, start, initial_name, out_file]
    return [sys.executable, "-c", DIALOG_SCRIPT, kind, start, initial_name, out_file]


def run_native_dialog(
    kind: str,
    initial_dir: Optional[str] = None,
    initial_name: Optional[str] = None,
) -> dict[str, Optional[str] | list[str]]:
    start = default_dir()
    if initial_dir:
        candidate = Path(initial_dir).expanduser()
        if candidate.is_dir():
            start = str(candidate)

    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    fd, out_name = tempfile.mkstemp(prefix="pdfbs_dialog_", suffix=".json")
    os.close(fd)
    out_file = Path(out_name)
    try:
        proc = subprocess.run(
            dialog_command(kind, start, initial_name or "", str(out_file)),
            capture_output=True,
            text=True,
            creationflags=creationflags,
        )
        if proc.returncode != 0:
            raise HTTPException(
                500, f"No se pudo abrir el diálogo del sistema: {proc.stderr.strip()}"
            )
        try:
            data = json.loads(out_file.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            data = {}
        paths = data.get("paths") or []
        return {"path": data.get("path"), "paths": paths}
    finally:
        out_file.unlink(missing_ok=True)


# Alias retrocompatible: `app.main._DIALOG_SCRIPT` se usaba desde desktop.py.
_DIALOG_SCRIPT = DIALOG_SCRIPT
