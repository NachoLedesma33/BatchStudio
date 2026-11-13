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

## Tests

```bash
cd backend
python -m pytest -q
```

## Benchmark

```bash
python scripts/benchmark_merge.py --count 1000 --out C:/temp/bench1000
```

## Desviaciones del SDD

- Token de sesión del backend no implementado en el MVP (solo loopback + CORS).
- La importación en el frontend se realiza por carga de archivos (upload) a una carpeta temporal controlada, porque el navegador no expone rutas absolutas.
- El reordenamiento se hace con dnd-kit (drag & drop) además de la lista.
- Se usa renderizado de páginas en el backend (PNG) en lugar de PDF.js en el frontend.