from __future__ import annotations

import os
from pathlib import Path

from app.core.config import AppConfig
from app.core.errors import ApiError


class PathPolicy:
    """Política de rutas para una app local.

    - Importar: cualquier PDF real del equipo, dentro del largo máximo.
    - Mostrar/revelar: solo documentos de la sesión, salidas de jobs, rutas
      elegidas por un diálogo nativo o rutas bajo la carpeta del usuario.
    """

    def __init__(self, config: AppConfig, documents, jobs) -> None:
        self.config = config
        self.documents = documents
        self.jobs = jobs
        self._dialog_paths: set[str] = set()

    # -- diálogos nativos ---------------------------------------------------
    def approve_dialog_path(self, path: str | Path | None) -> None:
        if not path:
            return
        try:
            resolved = Path(path).expanduser().resolve(strict=False)
        except OSError:
            return
        self._dialog_paths.add(self._key(resolved))
        self._dialog_paths.add(self._key(resolved.parent))

    # -- importación --------------------------------------------------------
    def validate_import(self, raw: str | Path) -> Path:
        text = str(raw).strip()
        if not text:
            raise ApiError("INVALID_PATH", "La ruta está vacía.")
        if len(text) > self.config.max_path_length:
            raise ApiError(
                "PATH_TOO_LONG",
                f"La ruta supera el máximo de {self.config.max_path_length} caracteres.",
            )
        path = Path(text).expanduser()
        if not path.exists():
            raise ApiError("PATH_NOT_FOUND", "El archivo no existe.", context={"path": str(path)})
        if not path.is_file():
            raise ApiError("NOT_A_FILE", "La ruta no es un archivo.", context={"path": str(path)})
        if path.suffix.lower() != ".pdf":
            raise ApiError("NOT_A_PDF", "El archivo no tiene extensión .pdf.", context={"path": str(path)})
        return path

    def validate_folder(self, raw: str | Path) -> Path:
        path = Path(str(raw).strip()).expanduser()
        if not path.exists() or not path.is_dir():
            raise ApiError("FOLDER_NOT_FOUND", "La carpeta no existe.", context={"path": str(path)})
        return path

    # -- reveal -------------------------------------------------------------
    def assert_revealable(self, raw: str | Path) -> Path:
        path = Path(str(raw).strip()).expanduser()
        try:
            resolved = path.resolve(strict=False)
        except OSError:
            resolved = path
        if not resolved.exists():
            raise ApiError("PATH_NOT_FOUND", "La ruta no existe.", status_code=404)
        if self._is_allowed(resolved):
            return resolved
        raise ApiError(
            "PATH_NOT_ALLOWED",
            "Por seguridad, solo se pueden abrir rutas de esta aplicación.",
            status_code=403,
            hint="Usá «Abrir carpeta» sobre un resultado generado o elegí la ruta con el diálogo del sistema.",
        )

    def _is_allowed(self, path: Path) -> bool:
        if self._key(path) in self._dialog_paths:
            return True
        try:
            home = Path.home().resolve(strict=False)
        except OSError:
            home = Path.home()
        roots = [self.config.data_dir, home / "Downloads"]
        for root in roots:
            if self._within(path, root):
                return True

        outputs = set()
        for output in self.jobs.all_output_paths():
            candidate = Path(output).expanduser()
            try:
                candidate = candidate.resolve(strict=False)
            except OSError:
                pass
            outputs.add(self._key(candidate))
            outputs.add(self._key(candidate.parent))
            if self._within(path, candidate.parent):
                return True
        if self._key(path) in outputs:
            return True

        for doc_path in self.documents.all_paths():
            doc = Path(doc_path).expanduser()
            try:
                doc = doc.resolve(strict=False)
            except OSError:
                pass
            if path == doc or path == doc.parent:
                return True
        return False

    @staticmethod
    def _key(path: Path) -> str:
        return os.path.normcase(str(path))

    def _within(self, path: Path, root: Path) -> bool:
        try:
            root = root.resolve(strict=False)
        except OSError:
            pass
        if path == root:
            return True
        return self._key(path).startswith(self._key(root) + os.sep)
