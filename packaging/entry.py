"""Punto de entrada del ejecutable empaquetado con PyInstaller."""

from __future__ import annotations

import multiprocessing
import sys

from app.desktop import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
