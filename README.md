# PDF Batch Studio

Aplicación local para unir grandes lotes de archivos PDF. Procesamiento 100 % local.

## Estructura

- `backend/` — FastAPI + PyMuPDF (Python 3.12)
- `frontend/` — React + TypeScript + Vite
- `scripts/` — generación de PDFs de prueba y benchmark
- `docs/` — SDD y resultados de benchmark

## Requisitos

- Python 3.12
- Node.js 20+

## Backend

```bash
cd backend
pip install -r requirements.txt  # o instalar manualmente
python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Abrir http://localhost:5173 (el proxy redirige /api al backend).

## Modo aplicación (un solo proceso)

Compilá la interfaz una vez y el backend la sirve desde el mismo proceso; se
abre en el navegador sin necesidad de levantar Vite:

```bash
cd frontend
npm install
npm run build

cd ../backend
python -m app.desktop
```

Si el puerto 8765 está ocupado, elige uno libre automáticamente.

## Ejecutable de escritorio

Genera un ejecutable autónomo (no requiere Python instalado):

```bash
cd frontend && npm install && npm run build && cd ..
pip install pyinstaller
python scripts/build_desktop.py
```

El resultado queda en `packaging/build/dist/PDF Batch Studio/`.

## Datos y configuración

- Directorio de datos: `~/.pdf-batch-studio` (configurable con `PDFBS_DATA_DIR`).
  Ahí viven `db/app.db` (SQLite en WAL), `cache/thumbs/`, `imports/`, `tmp/`.
- El backend expone la API v2 (`/api/sessions`, `/api/documents`, `/api/jobs`,
  `/api/system/capabilities`) y mantiene `/api/merge-jobs` como alias compatible.
- Al abrirse la app se genera un token local que viaja en `#token=…`; la interfaz
  lo guarda en `sessionStorage` y lo manda en `X-PDFBS-Token`.
- Las capacidades externas (Tesseract, LibreOffice, qpdf, Ghostscript) se detectan
  en tiempo real: `/api/system/capabilities` informa cuáles faltan, sin simularlas.

## Ejecución rápida

```bash
npm run all        # backend (8765) + frontend (5173) en desarrollo (sin token)
npm run prod       # compila el frontend y abre la app en un solo proceso
```

## Tests
Backend:

```bash
cd backend
python -m pytest -q
```

Frontend:

```bash
cd frontend
npm run lint
npx tsc -b
npm run test:run
npm run build
```

CI (`.github/workflows/ci.yml`) corre ambos gates en `windows-latest` para cada PR.

## Benchmark

```bash
python scripts/benchmark_split.py --pages 500
```


## Desviaciones del SDD

- Token de sesión del backend: implementado en F0 (token local en `#token=…`, header
  `X-PDFBS-Token`, verificación de `Origin`/`Host`, `/api/health` exento).
- La importación en el frontend se realiza por carga de archivos (upload) a una carpeta temporal controlada, porque el navegador no expone rutas absolutas.
- El reordenamiento se hace con dnd-kit (drag & drop) además de la lista.
- Se usa renderizado de páginas en el backend (PNG) en lugar de PDF.js en el frontend.
- Los diálogos nativos de carpeta y "Guardar como" corren en un proceso aparte (tkinter) porque el navegador no puede abrir el selector del sistema operativo.
- La detección de duplicados compara `sha256` (contenido idéntico byte a byte): nunca marca archivos distintos. Solo excluye/incluye documentos del lote; no borra archivos.
- El ejecutable de escritorio abre la interfaz en el navegador del sistema (no incluye un WebView propio).