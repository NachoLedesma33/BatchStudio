"""Arranca PDF Batch Studio como aplicación de escritorio local.

Un único proceso: el backend sirve la interfaz compilada y abre el navegador
del sistema. No requiere levantar Vite ni escribir comandos.

Uso:
    python -m app.desktop
"""

from __future__ import annotations

import socket
import sys
import threading
import webbrowser

import uvicorn

from app.core.config import CONFIG


def _configure_stdio() -> None:
    """Evita que la consola de Windows (cp1252) rompa al imprimir acentos."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            pass


def _log(message: str, *, error: bool = False) -> None:
    """Imprime solo si hay consola (un ejecutable sin consola no la tiene)."""
    stream = sys.stderr if error else sys.stdout
    if stream is None:
        return
    try:
        print(message, file=stream)
    except Exception:  # noqa: BLE001
        pass


def _alert(message: str) -> None:
    """Aviso visible incluso sin consola (ejecutable empaquetado)."""
    _log(message, error=True)
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("PDF Batch Studio", message)
        root.destroy()
    except Exception:  # noqa: BLE001
        pass


def _free_port(preferred: int) -> int:
    """Devuelve `preferred` si está libre; si no, un puerto libre cualquiera."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((CONFIG.host, preferred))
            return preferred
        except OSError:
            pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((CONFIG.host, 0))
        return int(sock.getsockname()[1])


def _open_browser_when_ready(port: int, url: str) -> None:
    for _ in range(100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex((CONFIG.host, port)) == 0:
                webbrowser.open(url)
                return
        threading.Event().wait(0.1)
    _log(f"No se pudo confirmar el arranque. Abrí {url} a mano.", error=True)


def _run_native_dialog() -> int:
    """Subcomando interno: abre el diálogo nativo (usado desde el ejecutable)."""
    from app.services.native_dialog import DIALOG_SCRIPT

    # El script espera (kind, initial_dir, initial_name, out_file) en argv[1:5].
    sys.argv = [sys.argv[0]] + sys.argv[2:6]
    namespace: dict = {"__name__": "__main__"}
    exec(compile(DIALOG_SCRIPT, "<native-dialog>", "exec"), namespace)  # noqa: S102
    return 0


def main() -> int:
    _configure_stdio()

    if len(sys.argv) > 1 and sys.argv[1] == "--native-dialog":
        return _run_native_dialog()

    from app.main import _UI_DIR, app

    if _UI_DIR is None:
        _alert(
            "Falta la interfaz compilada.\n\n"
            "Ejecutá primero:\n    cd frontend && npm install && npm run build"
        )
        return 1

    port = _free_port(CONFIG.port)
    # El token viaja en el fragmento: no se registra en logs ni en el historial
    # del navegador como parte de la ruta.
    url = f"http://{CONFIG.host}:{port}/#token={app.state.token}"
    _log(f"PDF Batch Studio -> {url}\nCerrá esta ventana para salir.")

    threading.Thread(
        target=_open_browser_when_ready, args=(port, url), daemon=True
    ).start()
    uvicorn.run(app, host=CONFIG.host, port=port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
