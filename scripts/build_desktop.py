"""Genera el ejecutable de escritorio (Windows/Linux/macOS) con PyInstaller.

Uso:
    python scripts/build_desktop.py

Requisitos:
    - Haber compilado la interfaz:  cd frontend && npm run build
    - Tener PyInstaller instalado:  pip install pyinstaller
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DIST_UI = ROOT / "frontend" / "dist"
BUILD_DIR = ROOT / "packaging" / "build"
APP_NAME = "PDF Batch Studio"

# Paquetes que PyInstaller arrastra por el análisis estático de dependencias
# opcionales (PyMuPDF -> pandas, numpy -> pytest, cadenas de test -> torch,
# tensorflow, scipy...). La app no los usa en tiempo de ejecución: sin esto el
# ejecutable pasa de ~680 MB a unos pocos MB.
EXCLUDES = [
    # frameworks de cálculo que no se usan
    "torch", "torchvision", "torchaudio", "torchgen", "triton",
    "tensorflow", "tensorboard", "keras", "tf_keras",
    "onnx", "onnxruntime",
    "pandas", "scipy", "matplotlib", "sympy", "mpmath", "networkx",
    "sklearn", "scikit-learn", "statsmodels", "numba", "llvmlite",
    "cv2", "einops", "py3nvml", "fsspec", "pyarrow", "sqlalchemy",
    "openpyxl", "xlsxwriter", "lxml",
    # herramientas de test
    "pytest", "_pytest", "py", "pluggy", "iniconfig", "unittest",
    # notebooks / consolas
    "IPython", "ipykernel", "jupyter", "jupyter_core", "jupyter_client",
    "notebook", "nbformat", "nbconvert", "traitlets",
    # imagen (PyMuPDF ya renderiza los PNG)
    "PIL", "Pillow",
]

# uvicorn resuelve sus implementaciones por nombre en tiempo de ejecución:
# PyInstaller no las ve en el análisis estático, así que hay que declararlas.
HIDDEN_IMPORTS = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "tkinter",
    "tkinter.filedialog",
    "tkinter.messagebox",
    "app.main",
    "app.desktop",
]


def main() -> int:
    if not (DIST_UI / "index.html").is_file():
        print(
            "Falta la interfaz compilada.\n"
            "Ejecutá primero:  cd frontend && npm install && npm run build",
            file=sys.stderr,
        )
        return 1

    if shutil.which("pyinstaller") is None:
        try:
            import PyInstaller  # noqa: F401
        except ImportError:
            print("Falta PyInstaller. Instalalo con:  pip install pyinstaller", file=sys.stderr)
            return 1

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        APP_NAME,
        "--paths",
        str(BACKEND),
        "--add-data",
        f"{DIST_UI}{';' if sys.platform.startswith('win') else ':'}ui",
        "--distpath",
        str(BUILD_DIR / "dist"),
        "--workpath",
        str(BUILD_DIR / "work"),
        "--specpath",
        str(BUILD_DIR),
    ]
    for mod in HIDDEN_IMPORTS:
        cmd += ["--hidden-import", mod]
    for mod in EXCLUDES:
        cmd += ["--exclude-module", mod]
    cmd.append(str(ROOT / "packaging" / "entry.py"))

    print("Ejecutando:\n  " + " ".join(cmd), flush=True)
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("La compilación falló.", file=sys.stderr)
        return result.returncode

    target = BUILD_DIR / "dist" / APP_NAME
    print(f"\nListo. Ejecutable en: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
