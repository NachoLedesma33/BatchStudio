# PDF Batch Studio — Plan de implementación

**Tipo:** Plan técnico de ejecución derivado de `Plan_Maestro_Mejoras_PDF_Batch_Studio.md`
**Estado:** Listo para arrancar Fase 0
**Fecha de revisión:** 2026-11-16
**Base del repositorio:** HEAD `472fbf4`; planes maestro y de implementación sin trackear
**Stack actual:** Python 3.12.10 + FastAPI + PyMuPDF 2.1 (MuPDF 1.28.6) · React 19 + TypeScript 7 + Vite 8

---

## 1. Veredicto de la revisión

El plan maestro es **viable y coherente** con el producto: local-first, gratuito, privado, Windows-first y orientado a lotes. No hay que descartar ninguna iniciativa, pero **no se puede empezar por funcionalidades**: hoy la aplicación es un MVP de unión de PDFs con estado en memoria y un frontend monolítico. Si se agregan "Dividir", "Organizador visual" u "OCR" antes de resolver los cimientos, cada función va a inventar su propia persistencia, su propio manejo de trabajos y su propio modelo de páginas, y el costo de mantenimiento se vuelve prohibitivo.

La revisión arroja cuatro faltantes estructurales y una deuda de pruebas:

1. **No hay persistencia.** `STORE` es un diccionario en memoria (`backend/app/services/session_store.py`). Reiniciar el backend borra documentos, orden, inclusiones y cualquier sesión. `/api/sessions/save` escribe un JSON suelto y `/api/sessions/load` exige una ruta; no existe listado, carga ni autoguardado.
2. **No hay núcleo genérico de operaciones.** Solo existe `merge_pdfs`. Cada función nueva tendería a duplicar endpoints, progreso, cancelación y reporte.
3. **No hay cola de trabajos real.** `JobManager` lanza un hilo por trabajo, sin límite, sin persistencia y sin recuperación ante cierre. No hay estado `queued`, ni pausa, ni reintento, ni historial.
4. **No hay modelo de páginas.** El documento es la unidad mínima. Sin páginas no se pueden implementar dividir, organizador visual, rotación, extracción, páginas en blanco, numeración ni marcas de agua.
5. **No hay infraestructura de pruebas de interfaz.** Hay 9 tests de backend y ningún test de frontend, integración de API ni e2e. El plan exige pruebas por función; sin base, no se puede cumplir.

Además, la importación actual **pierde la ruta original**: el frontend sube archivos, el backend los copia a `~/.pdf-batch-studio/temp/imports` y guarda esa ruta temporal. Los endpoints de importación por ruta (`/api/files/import`, `/api/folders/import`) existen pero la UI no los usa. Para una app de escritorio, eso es al revés: la ruta real debe ser el camino principal y la copia administrada, el respaldo.

**Conclusión:** el plan maestro se acepta como hoja de ruta, pero la ejecución debe empezar por una fase de cimientos y una primera rebanada vertical que los pruebe de punta a punta. La rebanada recomendada es **"Cimientos + Dividir PDF"**, no el organizador visual completo.

---

## 2. Auditoría verificada contra el código

| Área | Estado real hoy | Consecuencia para el plan |
|---|---|---|
| Persistencia | `STORE` en memoria; sesiones JSON sin índice | F0 debe introducir SQLite y repositorios antes de cualquier feature |
| Operaciones | Solo `merge_pdfs` con progreso, cancelación, verificación y rename atómico | Extraer el patrón a un registro genérico sin romper unión |
| Trabajos | Hilo por job, sin cola ni persistencia; SSE por sondeo de 200 ms | F0 debe crear cola persistente de un worker y recuperación |
| Documentos | Modelo plano `PdfDocument`; `sha256` ya calculado al importar | Base lista para deduplicar y cachear miniaturas |
| Páginas | No existen como entidad | F1 debe crear el plan de páginas y materialización perezosa |
| Importación | Upload copia a temp; import por ruta existe pero la UI no lo usa | F0 debe priorizar selector nativo de archivos y conservar ruta |
| Previews | Render on-demand en `/api/documents/{id}/preview/{page}`; sin caché | F2 necesita caché en disco y miniaturas; F1 puede seguir con render directo |
| Frontend | `App.tsx` de 1053 líneas, un solo flujo (unir) | F0 debe separar en módulos y features antes de agregar vistas |
| API | `/api` monolítico en `main.py` (433 líneas), CORS amplio, sin token | F0 debe dividir routers y cerrar seguridad |
| Historial | No existe | Esquema en F0; UI en F4 |
| Preferencias | Solo tema en `localStorage` | F0 crea tabla `settings`; UI en F4 |
| OCR / Office / qpdf / Ghostscript | **No instalados** (`tesseract`, `soffice`, `qpdf`, `gswin64c` ausentes) | Detectar en runtime; nunca simular soporte |
| Pruebas | `pytest`: 9 passed; `oxlint`: 0 errores / 3 warnings; `tsc -b`: limpio | Línea base congelada como gate de F0 |

**Línea base medida el 2026-11-16:**

- `pytest -q` → 9 passed, 1 warning (`fitz` deprecado).
- `npm run lint` → 0 errores, 3 warnings preexistentes (`only-export-components` ×2, `incompatible-library` en `App.tsx`).
- `npx tsc -b` → exit 0.
- `pymupdf.version` → 2.1 / MuPDF 1.28.6.

---

## 3. Decisiones de arquitectura (ADR resumidas)

Cada decisión queda registrada en `docs/adr/` al implementarse. Estas son las que condicionan todo lo demás.

### D-01 · SQLite con `sqlite3` de la stdlib

- **Decisión:** usar `sqlite3`, WAL, `foreign_keys=ON`, `busy_timeout=5000` y migraciones por `PRAGMA user_version`.
- **Motivo:** cero dependencias nuevas, archivo único, backup trivial, funciona offline y en Windows sin instalación.
- **Ubicación:** `~/.pdf-batch-studio/app.db` (respetando `PDFBS_DATA_DIR` para tests y modo portable).
- **Regla:** una conexión por request/hilo, transacciones cortas, nunca mantener una transacción abierta mientras se renderiza o se escribe un PDF.
- **Alternativa descartada:** ORM completo (SQLAlchemy/Alembic) por peso y por el tamaño real del dominio.

### D-02 · Núcleo genérico de operaciones

- **Decisión:** toda función es una `Operation` con `id`, `validate(params)`, `plan(params) -> OperationPlan` y `execute(plan, ctx) -> JobResult`.
- **Motivo:** dividir, comprimir, rotar, exportar imágenes y OCR comparten progreso, cancelación, errores por ítem y reporte.
- **Regla:** la UI nunca llama a una función interna; llama a `POST /api/jobs` con `kind` + `params`.
- **Compatibilidad:** `/api/merge-jobs*` se mantiene como alias deprecado durante una versión, implementado sobre el nuevo núcleo. La unión actual debe seguir pasando sus tests sin cambios de comportamiento.

### D-03 · Cola persistente de un worker

- **Decisión:** un único worker (configurable a más en el futuro) que toma jobs `queued` de SQLite en orden FIFO. Estados: `queued`, `running`, `completed`, `completed_with_errors`, `failed`, `cancelled`, `interrupted`.
- **Motivo:** el procesamiento es intensivo en CPU y disco; paralelizar multiplica memoria y empeora la experiencia. Un worker hace el progreso predecible y el consumo medible.
- **Regla:** al iniciar, todo job `running` pasa a `interrupted` con los ítems ya completados conservados. La UI ofrece reintentar lo pendiente.
- **SSE:** los eventos viven en un buffer en memoria por job; la base guarda estado e ítems, no cada evento. Si el cliente se reconecta, recibe snapshot + eventos nuevos.

### D-04 · Modelo de páginas con materialización perezosa

- **Decisión:** `session_documents` guarda orden e inclusión a nivel documento. `document_pages` se llena **solo cuando un documento se edita a nivel página** (rotar, excluir, reordenar páginas). Mientras no se edite, las páginas se derivan de `page_count`.
- **Motivo:** importar 1.000 PDFs de 100 páginas crearía 100.000 filas sin que el usuario haya tocado una página.
- **Regla:** toda operación que necesite páginas llama a `ensure_pages(document_id)` antes de leer. El orden de páginas dentro de un documento se guarda en `document_pages.page_order`.
- **Consecuencia:** el organizador visual de F2 materializa solo el documento abierto, no la sesión completa.

### D-05 · Importación por ruta real primero

- **Decisión:** el camino principal es el selector nativo de archivos múltiple (`/api/system/pick-files`) y la importación por ruta. El upload queda como respaldo explícito, marcado `managed_copy=1`.
- **Motivo:** el producto es de escritorio y local-first; copiar cada PDF a una carpeta temporal duplica disco y rompe la relación con el archivo original.
- **Regla:** nunca se escribe en la carpeta de origen. Si el usuario elige "misma carpeta", la salida va a una subcarpeta `<nombre>_partes` o a la carpeta configurada.
- **Drag & drop:** en navegador no expone rutas reales; se acepta como upload administrado y se informa. No se promete lo que el navegador no puede dar.

### D-06 · Preview y miniaturas renderizadas por backend

- **Decisión:** seguir usando PyMuPDF para renderizar y agregar caché en disco con clave `sha256 + page + scale + rotation`.
- **Motivo:** ya funciona, no agrega PDF.js ni un segundo motor, y mantiene una sola fuente de verdad.
- **Regla:** `ETag` + `Cache-Control: immutable` para miniaturas; presupuesto de caché configurable (por defecto 512 MB) con evicción LRU; limpieza al iniciar.
- **Futuro:** si se necesita selección de texto o búsqueda visual en el visor, se evalúa PDF.js en F5, no antes.

### D-07 · Seguridad de una app local

- **Decisión:** token aleatorio por ejecución, enviado en `X-PDFBS-Token` en toda llamada `/api` que muta estado; validación de `Origin`/`Host`; CORS limitado a loopback; rutas permitidas solo si están registradas o vienen del selector nativo.
- **Motivo:** el backend escucha en `127.0.0.1`, pero cualquier página web abierta en el mismo equipo puede intentar `fetch` contra el puerto local. Loopback no es autenticación.
- **Implementación:** el lanzador abre `http://127.0.0.1:<puerto>/#token=<token>`; el fragmento no viaja al servidor ni al `Referer`. El frontend lo lee al arrancar, lo guarda en `sessionStorage` y lo borra de la barra de direcciones. En desarrollo se permite `PDFBS_DEV_NO_TOKEN=1` con advertencia visible.
- **Rutas:** `/api/system/reveal` deja de aceptar rutas arbitrarias; solo acepta IDs de documento, IDs de job o rutas devueltas por un diálogo nativo en la misma sesión.

### D-08 · Capacidades detectadas, nunca simuladas

- **Decisión:** `GET /api/capabilities` informa presencia y versión de `tesseract`, `soffice`, `qpdf`, `gs`, motores de OCR y límites configurados.
- **Motivo:** hoy no están instalados. Una UI que muestra "OCR" y falla al ejecutar es peor que una UI que dice "No disponible" con instrucciones.
- **Regla:** ninguna función dependiente de una herramienta externa se muestra habilitada si la detección falla. No se empaquetan Tesseract, LibreOffice, qpdf ni Ghostscript.

### D-09 · Frontend por features, no por componentes sueltos

- **Decisión:** dividir `App.tsx` en `app/` (shell, layout, providers), `features/` (merge, split, pages, jobs, history) y `lib/api/` (cliente tipado por dominio).
- **Motivo:** el archivo actual mezcla estado de sesión, selección, atajos, duplicados, preview y diálogos. Agregar una segunda operación ahí multiplica el riesgo.
- **Regla:** la división de F0 **no cambia la UI visible**. Es refactor con pruebas de regresión, no rediseño.

### D-10 · Licencias y distribución

- **PyMuPDF:** AGPL-3.0 o licencia comercial. El repositorio es público, así que por ahora se mantiene AGPL y se publica el código; si se distribuye un binario sin cumplir AGPL, hay que comprar licencia. **Decisión pendiente del usuario** antes de publicar releases.
- **pypdf:** BSD. **SQLite:** dominio público. **Tesseract:** Apache-2.0. **LibreOffice:** MPL-2.0. **qpdf:** Apache-2.0. **Ghostscript:** AGPL/comercial (solo opcional, nunca requerido).
- **Regla:** toda herramienta opcional se documenta con licencia, tamaño y método de instalación en `docs/dependencias-externas.md`.

---

## 4. Arquitectura objetivo

### 4.1 Estructura de carpetas

```text
backend/
  app/
    main.py                 # solo crea la app, monta routers y UI
    api/
      __init__.py
      sessions.py
      documents.py
      operations.py
      jobs.py
      system.py
      capabilities.py
    core/
      config.py             # rutas, límites, data_dir
      security.py           # token, Origin/Host, path policy
      errors.py             # envelope de error único
      logging.py
    db/
      connection.py
      migrate.py
      migrations/
        001_init.sql
      repositories/
        sessions.py
        documents.py
        pages.py
        jobs.py
        history.py
        settings.py
    operations/
      base.py               # Operation, OperationPlan, JobContext
      registry.py
      merge.py
      split.py
    services/
      pdf_inspector.py
      preview_cache.py
      capabilities.py
      job_worker.py
      path_policy.py
    models/
    schemas/
  tests/
    unit/
    integration/
    fixtures/
frontend/src/
  app/
    AppShell.tsx
    routes.ts
    providers/
  features/
    merge/
    split/
    pages/
    jobs/
    history/
  components/
  lib/
    api/
      client.ts
      types.ts
      sessions.ts
      operations.ts
      system.ts
    utils.ts
    theme.ts
    shortcuts.ts
```

### 4.2 Esquema SQLite v1

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE sessions (
  id              TEXT PRIMARY KEY,
  name            TEXT NOT NULL,
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL,
  last_opened_at  TEXT,
  state_json      TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE session_documents (
  id              TEXT PRIMARY KEY,
  session_id      TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
  path            TEXT NOT NULL,
  original_name   TEXT NOT NULL,
  size_bytes      INTEGER NOT NULL,
  page_count      INTEGER,
  sha256          TEXT,
  status          TEXT NOT NULL,
  error_message   TEXT,
  included        INTEGER NOT NULL DEFAULT 1,
  order_index     INTEGER NOT NULL,
  managed_copy    INTEGER NOT NULL DEFAULT 0,
  metadata_json   TEXT NOT NULL DEFAULT '{}',
  UNIQUE (session_id, path)
);

CREATE TABLE document_pages (
  document_id     TEXT NOT NULL REFERENCES session_documents(id) ON DELETE CASCADE,
  page_no         INTEGER NOT NULL,          -- página de origen, 1-based
  page_order      INTEGER NOT NULL,          -- orden de salida
  rotation        INTEGER NOT NULL DEFAULT 0,
  excluded        INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (document_id, page_no)
);

CREATE TABLE operations (
  id              TEXT PRIMARY KEY,
  session_id      TEXT REFERENCES sessions(id) ON DELETE SET NULL,
  kind            TEXT NOT NULL,
  params_json     TEXT NOT NULL,
  created_at      TEXT NOT NULL
);

CREATE TABLE jobs (
  id              TEXT PRIMARY KEY,
  operation_id    TEXT REFERENCES operations(id) ON DELETE SET NULL,
  kind            TEXT NOT NULL,
  status          TEXT NOT NULL,
  params_json     TEXT NOT NULL,
  output_json     TEXT,
  progress        REAL NOT NULL DEFAULT 0,
  stage           TEXT,
  total_items     INTEGER NOT NULL DEFAULT 0,
  done_items      INTEGER NOT NULL DEFAULT 0,
  error_count     INTEGER NOT NULL DEFAULT 0,
  errors_json     TEXT NOT NULL DEFAULT '[]',
  created_at      TEXT NOT NULL,
  started_at      TEXT,
  finished_at     TEXT,
  cancel_requested INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE job_items (
  job_id          TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  idx             INTEGER NOT NULL,
  label           TEXT NOT NULL,
  status          TEXT NOT NULL,
  output_path     TEXT,
  message         TEXT,
  PRIMARY KEY (job_id, idx)
);

CREATE TABLE history (
  id              TEXT PRIMARY KEY,
  job_id          TEXT REFERENCES jobs(id) ON DELETE SET NULL,
  kind            TEXT NOT NULL,
  summary         TEXT NOT NULL,
  inputs_json     TEXT NOT NULL,
  outputs_json    TEXT NOT NULL,
  created_at      TEXT NOT NULL
);

CREATE TABLE settings (
  key             TEXT PRIMARY KEY,
  value_json      TEXT NOT NULL,
  updated_at      TEXT NOT NULL
);

CREATE INDEX idx_jobs_status_created   ON jobs(status, created_at);
CREATE INDEX idx_history_created       ON history(created_at DESC);
CREATE INDEX idx_docs_session_order    ON session_documents(session_id, order_index);
CREATE INDEX idx_pages_document_order  ON document_pages(document_id, page_order);
```

Migraciones: archivos `NNN_*.sql` ordenados; cada uno corre en una transacción y actualiza `user_version`. Nunca se edita una migración ya aplicada.

### 4.3 Contrato genérico de operaciones

```json
POST /api/operations/preview
{
  "kind": "split",
  "session_id": "…",
  "params": { }
}
```

Respuesta:

```json
{
  "kind": "split",
  "summary": { "total_files": 3, "total_pages": 10, "total_bytes_estimate": 1234567 },
  "items": [
    { "index": 1, "label": "documento_parte_01.pdf", "pages": [1, 2, 3], "exists": false }
  ],
  "warnings": [{ "code": "OVERLAP", "message": "Las páginas 3 se repiten en dos salidas." }],
  "errors": []
}
```

El preview **no escribe nada**. El job recalcula el plan en el servidor: nunca confía en un plan enviado por el cliente. Cada `POST /api/jobs` inserta una fila en `operations` y otra en `jobs` en la misma transacción: `operations.params_json` conserva el pedido original y `jobs` el estado de ejecución.

```json
POST /api/jobs
{ "kind": "split", "session_id": "…", "params": { } }
→ 202 { "job_id": "…" }

GET  /api/jobs?status=queued,running&limit=50
GET  /api/jobs/{id}
GET  /api/jobs/{id}/events        # SSE
POST /api/jobs/{id}/cancel
GET  /api/jobs/{id}/report
```

Eventos SSE:

```json
{"type":"status","status":"running"}
{"type":"progress","stage":"writing","done":2,"total":3,"current":"documento_parte_02.pdf","percent":66.7}
{"type":"item","index":2,"status":"failed","message":"Permiso denegado"}
{"type":"done","status":"completed_with_errors"}
```

### 4.4 Envelope de error

Formato único para toda la API:

```json
{
  "detail": {
    "code": "DOCUMENT_NOT_FOUND",
    "message": "El documento no existe en la sesión.",
    "hint": "Volvé a agregarlo desde el selector de archivos.",
    "context": {}
  }
}
```

El cliente muestra `message` y, si existe, `hint`. Los códigos son estables y se documentan en `docs/api-errores.md`.

### 4.5 Reglas de operación

1. Toda operación valida rutas contra el registro de la sesión; jamás acepta una ruta arbitraria del cliente.
2. Toda salida se escribe en un temporal del mismo volumen y se publica con `os.replace` (patrón ya probado en `pdf_merger.py`).
3. La cancelación se verifica entre ítems y entre páginas en operaciones largas; al cancelar se borran los temporales, no los resultados ya publicados.
4. Un fallo por ítem no cancela el job salvo dependencia explícita; se acumula en `job_items` y en `errors`.
5. El original nunca se modifica. `overwrite` solo aplica al archivo de salida y requiere confirmación explícita en UI.
6. Todo job deja un reporte consultable y una entrada de historial.

---

## 5. Fases

Cada fase termina con gates verificables y una entrada en `README.md` + `memory.md`. Ninguna fase se considera cerrada por tener UI: se cierra cuando la operación es real, verificable y probada.

### Fase 0 — Cimientos (estimación: 1,5 a 2 semanas)

**Objetivo:** que cualquier función futura se pueda implementar sin inventar persistencia, trabajos, seguridad ni estructura de frontend.

Entregables:

1. **Configuración y datos**
   - `PDFBS_DATA_DIR` con default `~/.pdf-batch-studio`; subrutas `db/`, `cache/thumbs/`, `imports/`, `tmp/`.
   - `AppConfig` con límites reales usados: `max_files`, `max_path_length`, `worker_count=1`, `thumb_cache_mb=512`.
2. **SQLite + migraciones**
   - `db/connection.py`: conexión por hilo, WAL, `busy_timeout`, `row_factory`.
   - `db/migrate.py` + `001_init.sql` con el esquema de §4.2.
   - Test: base vacía → v1; reejecutar migraciones es idempotente.
3. **Repositorios**
   - `sessions`, `documents`, `pages`, `jobs`, `history`, `settings`.
   - `DocumentStore` en memoria se reemplaza por `SessionRepository` + `DocumentRepository`; SQLite es la única fuente de verdad (sin caché paralela).
4. **Núcleo de operaciones**
   - `operations/base.py`: `Operation`, `OperationPlan`, `JobContext` (progreso, cancelación, rutas temporales).
   - `operations/registry.py`.
   - `operations/merge.py`: adaptador de `merge_pdfs` con el mismo comportamiento y resultados.
   - Migrar `import fitz` → `import pymupdf` en `main.py`, `pdf_inspector.py`, `pdf_merger.py`, tests y scripts; fijar `PyMuPDF>=2.1,<3` en `requirements.txt`. Gate: sin `FutureWarning` y mismos resultados.
5. **Cola persistente**
   - `services/job_worker.py`: un thread, toma `queued`, actualiza estado, escribe `job_items`, publica eventos.
   - Recuperación al iniciar: `running` → `interrupted`.
   - Cancelación cooperativa y limpieza de temporales.
6. **API v2**
   - Routers separados: `sessions`, `documents`, `operations`, `jobs`, `system`, `capabilities`.
   - Alias deprecado de `/api/merge-jobs` sobre el nuevo núcleo.
   - Envelope de error y códigos documentados.
7. **Seguridad local**
   - Token por ejecución, middleware, `Origin`/`Host` estrictos, CORS loopback.
   - `path_policy`: solo documentos de la sesión, salidas de jobs y rutas de diálogos nativos.
   - `pick-files` múltiple + `reveal` restringido.
8. **Capacidades**
   - `services/capabilities.py` con detección y timeout corto (≤1,5 s por herramienta, en paralelo).
   - `GET /api/capabilities`.
9. **Frontend**
   - Split de `App.tsx` en `AppShell`, `features/merge`, hooks de sesión/selección/atajos y `lib/api/` tipado.
   - **Sin cambio visual ni de comportamiento.** Prueba de regresión: mismas acciones, mismos textos, mismos atajos.
10. **Pruebas**
    - Backend: unitarias de rango/validación, integración de API con `TestClient`, migraciones, cola y recuperación.
    - Frontend: Vitest + Testing Library + MSW; primeros tests de hooks y de `Merge` (no snapshots masivos).
    - CI Windows: `pytest`, `oxlint`, `tsc -b`, `vitest run`, `vite build`.

**Criterios de aceptación de F0:**

- Reiniciar el backend conserva sesión, documentos, orden e inclusiones.
- Un merge creado antes de reiniciar aparece como `interrupted` y puede reintentarse.
- `GET /api/capabilities` responde en menos de 3 s y reporta ausencia de Tesseract/LibreOffice/qpdf/Ghostscript en este equipo.
- Una llamada `/api` sin token desde otro origen falla con 401/403.
- `pytest`, `vitest`, `oxlint`, `tsc -b`, `vite build` pasan.
- La UI de unión se ve y se comporta igual que en `472fbf4`.

### Fase 1 — Primera rebanada vertical: Dividir PDF (estimación: 1,5 a 2 semanas)

**Objetivo:** probar de punta a punta la nueva arquitectura con una operación real, masiva y con resultados múltiples.

Alcance:

- Modos: `ranges` (grupos separados por coma), `every` (cada N páginas), `single` (una página por archivo).
- Sintaxis: `1-3, 5, 8-10`; 1-based, inclusivo. `7-` significa "hasta el final"; `-3` significa "desde el inicio".
- Estimación previa: cantidad de archivos, páginas por archivo, nombres, colisiones, advertencias por solapamiento.
- Plantilla de nombre con tokens `{name}`, `{index}`, `{start}`, `{end}`, `{pages}`, `{date}` y formato numérico `{index:02}`.
- Política de colisión: `suffix` (recomendada), `fail`, `overwrite`.
- Carpeta de salida por selector nativo; default `carpeta_origen/<nombre>_partes`.
- Ejecución como job con progreso real por archivo, cancelación y reporte.
- Resultado: lista de archivos generados, abrir ubicación, abrir PDF, reintentar fallidos.
- Manejo explícito de PDFs protegidos, corruptos, páginas fuera de rango y nombres inválidos en Windows.

**Criterios de aceptación:**

- Un PDF de 10 páginas con `1-3, 4, 5-10` genera 3 archivos de 3, 1 y 6 páginas; cada uno se reabre y se verifica.
- Los originales quedan intactos (hash y mtime sin cambios).
- `single` sobre 500 páginas genera 500 archivos sin superar 250 MB de RSS.
- Cancelar a mitad deja 0 archivos temporales y conserva los ya publicados, informados como completados.
- Un PDF con contraseña produce un error por ítem claro, sin abortar el resto.
- Dos salidas con el mismo nombre aplican `_2` o fallan según la política elegida.
- El preview y la ejecución real coinciden en cantidad de archivos y páginas.
- Tests unitarios de rangos (tabla de casos), nombres y colisiones; test de integración de job; un e2e de dividir.

### Fase 2 — Organizador visual, rotación y extracción (estimación: 2,5 a 3 semanas)

**Objetivo:** convertir el modelo de páginas en una experiencia visual.

Alcance:

- Grilla de miniaturas para el documento activo, con virtualización y caché en disco.
- Reordenar páginas con dnd-kit, excluir, duplicar, rotar 90/180/270 y restaurar.
- Selección de páginas por clic, Ctrl y Shift; selección de rangos discontinuos.
- Extraer páginas seleccionadas a un PDF nuevo.
- Rotación manual desde el organizador y desde la lista de documentos.
- Deshacer/rehacer acotado a acciones de sesión (orden, exclusión, rotación); nunca borra archivos.
- Guardado del estado de páginas en `document_pages`.

**Criterios de aceptación:**

- Reordenar 200 páginas se refleja en la salida y persiste tras reiniciar.
- La rotación se aplica a la página correcta y se puede deshacer.
- Extraer 5 páginas discontinuas genera un PDF con exactamente esas páginas, en ese orden.
- La caché de miniaturas no supera el presupuesto y se limpia correctamente.
- Arrastrar con búsqueda u orden activo no reordena el documento equivocado (bug actual: el mapeo usa `docs` sin filtrar).

### Fase 3 — Conversión y optimización (estimación: 3 a 4 semanas)

Alcance:

- Exportar PDF a imágenes (PNG/JPEG; páginas, DPI, calidad, nombres).
- Crear PDF desde imágenes (orden, rotación, tamaño, orientación, ajuste, márgenes).
- Extraer texto a TXT, distinguiendo texto nativo de escaneo.
- Detección conservadora de páginas en blanco con revisión previa.
- Compresión en dos niveles: estructural sin pérdida (limpieza, deduplicación de objetos, deflate) y rasterización con pérdida claramente etiquetada.
- Edición de metadatos (título, autor, asunto, palabras clave; limpiar seleccionados).
- OCR **solo si Tesseract está detectado**; si no, estado "No disponible" con instrucciones.
- Office → PDF **solo si LibreOffice está detectado**; si no, "No disponible".

**Criterios de aceptación:**

- Exportar 100 páginas a 150 DPI produce 100 imágenes verificables y no bloquea la UI.
- Imágenes → PDF conserva orden, orientación y tamaño elegido.
- La compresión informa tamaño antes/después y advierte si es con pérdida.
- La detección de páginas en blanco nunca elimina automáticamente; solo sugiere.
- OCR y Office→PDF no aparecen habilitados si la herramienta no está presente.

### Fase 4 — Productividad y trabajo por lotes (estimación: 2 a 3 semanas)

Alcance:

- UI de cola de trabajos: listar, filtrar, cancelar, reintentar, ver detalle por ítem.
- Historial de operaciones con filtros, apertura de resultados y exportación.
- Autoguardado de sesión y restauración al iniciar; detección de trabajos interrumpidos.
- Procesamiento por lotes sobre varios documentos para operaciones compatibles.
- Ordenamiento automático (nombre, fecha, tamaño, páginas) y agrupación por patrones.
- Renombrado masivo con preview y detección de conflictos.
- Reportes de lote en TXT/CSV/JSON.
- Preferencias: carpeta de salida, confirmaciones, límites, tema, idioma OCR, comportamiento de importación.
- Marca de agua y numeración/encabezados/pies (comparten motor de composición de página).

**Criterios de aceptación:**

- La cola sobrevive reinicios y muestra trabajos interrumpidos con opción de reintento.
- Un lote de 100 archivos con 3 fallos termina en `completed_with_errors` y reporta los 3.
- El reporte exportado coincide con lo que muestra la UI.
- Las preferencias persisten y afectan el comportamiento real.

### Fase 5 — Búsqueda y biblioteca local (estimación: 4 a 6 semanas)

Alcance:

- Búsqueda dentro de un PDF con número de página y fragmento; apertura en la página.
- Índice local FTS5 de metadatos y, opcionalmente, texto extraído/OCR.
- Búsqueda global con documento, página y fragmento.
- Biblioteca: carpetas favoritas, recientes, etiquetas, colecciones, favoritos, filtros combinables.
- Reconstrucción, actualización y eliminación del índice; detección de archivos movidos o desaparecidos.
- Indexación incremental en segundo plano con la misma cola.

**Criterios de aceptación:**

- La búsqueda global encuentra una frase en 500 PDFs indexados en menos de 1 s.
- El índice se puede borrar y reconstruir sin perder documentos ni originales.
- Un archivo movido se marca como no disponible, no se elimina de la biblioteca.
- Nada se envía fuera del equipo.

### Fase 6 — Automatización y perfiles (estimación: 4 a 6 semanas)

Alcance:

- Reglas reutilizables con preview y ejecución explícita; nada destructivo silencioso.
- Vigilancia de carpetas con activar/pausar/desactivar y detección de archivos nuevos.
- Unión automática por reglas: carpeta, orden, filtros, exclusión de duplicados, salida y errores.
- Perfiles predefinidos (académico, profesional, escaneados, archivo) y constructor personalizado.
- Orden de ejecución visible, dependencias advertidas y validación de combinaciones.

**Criterios de aceptación:**

- Una regla guardada se puede duplicar, editar y ejecutar sin repetir configuración.
- La carpeta vigilada no procesa dos veces el mismo archivo y respeta pausa.
- Un perfil muestra exactamente qué va a hacer antes de ejecutar.
- Ninguna regla mueve ni borra originales sin confirmación.

### Fase 7 — Avanzado y condicional (sin estimar hasta validar demanda)

Iniciativas que dependen de decisiones, licencias o motores externos:

- PDF → DOCX, PDF → HTML, PDF/A, anotaciones, firma visual, recorte, comparación de versiones, desbloqueo autorizado, similitud documental, clasificación automática, rotación inteligente.
- Cada una requiere su propio plan detallado y una validación de fidelidad.
- No se declara compatibilidad PDF/A sin validador; no se declara firma legal sin criptografía; no se promete OCR de calidad sin Tesseract.

---

## 6. Trazabilidad completa del plan maestro

Complejidad: **S** ≤ 3 días · **M** ≤ 1 semana · **L** ≤ 3 semanas · **XL** > 3 semanas.

| Ítem | Función | Fase | Complejidad | Depende de |
|---|---|---|---|---|
| A.1 | Dividir PDF | F1 | M | F0, modelo de páginas |
| A.2 | Organizador visual de páginas | F2 | L | F1, caché de miniaturas |
| A.3 | Compresión | F3 | L | F0, preview de tamaño |
| A.4 | Rotación inteligente | F2 manual / F7 auto | L | F2, heurística de orientación |
| A.5 | Páginas en blanco | F3 | M | F2, análisis de píxeles/texto |
| A.6 | Recorte de páginas | F7 | M | F2, preview visual |
| A.7 | Duplicados | Ya existe (hash) / F4 carpeta / F7 similitud | S / M / XL | Índice de hashes; texto para similitud |
| B.1 | PDF → imágenes | F3 | M | Núcleo de operaciones |
| B.2 | Imágenes → PDF | F3 | M | Núcleo de operaciones |
| B.3 | Texto → TXT | F3 | S | PyMuPDF |
| B.4 | PDF → DOCX | F7 | XL | Motor de conversión, decisión |
| B.5 | PDF → HTML | F7 | XL | Motor de conversión, decisión |
| B.6 | Office → PDF | F3 condicional / F7 | L | LibreOffice detectado |
| B.7 | PDF/A | F7 | L | Validador PDF/A |
| C.1 | OCR local | F3 condicional | L | Tesseract detectado |
| C.2 | Búsqueda en PDF | F5 | M | Extracción de texto |
| C.3 | Búsqueda global | F5 | L | FTS5, biblioteca |
| C.4 | Clasificación automática | F6 / F7 | L | Texto/metadatos, reglas |
| C.5 | Metadatos | F3 | S | PyMuPDF |
| C.6 | Similitud documental | F7 | XL | Texto, estructura, visión |
| D.1 | Marca de agua | F4 | M | Composición de página |
| D.2 | Numeración | F4 | M | Composición de página |
| D.3 | Encabezados/pies | F4 | M | Comparte motor con D.2 |
| D.4 | Firma visual | F7 | M | Composición de página |
| D.5 | Contraseña | F4 | M | PyMuPDF `save(encryption=…)` |
| D.6 | Desbloqueo autorizado | F7 | S | Contraseña válida |
| D.7 | Anotaciones | F7 | L | Modelo de anotaciones |
| D.8 | Comparación de versiones | F7 | L | Texto + render |
| E.1 | Procesamiento por lotes | F0 motor / F4 UI | M | Cola, `job_items` |
| E.2 | Vigilar carpetas | F6 | L | Reglas, worker |
| E.3 | Unión automática | F6 | M | Reglas, operación merge |
| E.4 | Ordenamiento automático | F4 | S | Metadatos de documentos |
| E.5 | Agrupación por patrones | F4 | S | Nombres de archivo |
| E.6 | Renombrado masivo | F4 | M | Preview + colisiones |
| E.7 | Reglas reutilizables | F6 | M | Perfiles/reglas |
| E.8 | Cola de trabajos | F0 motor / F4 UI | M | SQLite |
| F.1 | Historial | F0 esquema / F4 UI | M | Jobs, resultados |
| F.2 | Deshacer/rehacer | F2 | M | Estado de páginas |
| F.3 | Autoguardado | F0 esquema / F4 UI | M | Sesiones |
| F.4 | Atajos | Existe / ampliar F2–F4 | S | Shell de UI |
| F.5 | Abrir ubicación | Existe / restringir F0 | S | Path policy |
| F.6 | Recuperación | F0 motor / F4 UI | M | Cola persistente |
| F.7 | Reportes | F4 | S | `job_items` |
| F.8 | Tema claro/oscuro | Hecho | — | — |
| F.9 | Preferencias | F4 | M | `settings` |
| G.1 | Carpetas favoritas | F5 | S | Biblioteca |
| G.2 | Recientes | F5 | S | Historial |
| G.3 | Etiquetas/colecciones | F5 | M | Biblioteca |
| G.4 | Filtros | F5 | M | Metadatos |
| G.5 | Índice local | F5 | L | FTS5 |
| G.6 | Favoritos | F5 | S | Biblioteca |
| H.1 | Perfiles de trabajo | F6 | M | Operaciones, settings |
| H.2 | Perfil académico | F6 | S | Perfiles |
| H.3 | Perfil profesional | F6 | S | Perfiles |
| H.4 | Perfil escaneados | F6 | S | OCR condicional |
| H.5 | Perfil archivo | F6 | S | PDF/A condicional |
| H.6 | Constructor de perfiles | F6 | M | Registro de operaciones |

**Cobertura:** 57 de 57 ítems del plan maestro mapeados (A:7, B:7, C:6, D:8, E:8, F:9, G:6, H:6). Ninguno queda "sin fase".

---

## 7. Sprint 1 — "Cimientos + Dividir PDF"

Duración sugerida: 4 semanas para una persona (3 si F0 cierra en una semana). Corte natural: **semanas 1–2 = F0**, **semana 3 = F1 backend**, **semana 4 = F1 frontend + cierre**.

### Semanas 1–2 — F0

| # | Tarea | Archivos principales | Hecho cuando |
|---|---|---|---|
| 1.1 | Congelar baseline y crear rama | — | `472fbf4` + gates verdes documentados |
| 1.2 | Configuración de datos y límites | `core/config.py` | `PDFBS_DATA_DIR` funciona en tests y en dev |
| 1.3 | Conexión SQLite y migrador | `db/connection.py`, `db/migrate.py` | Test de migración idempotente |
| 1.4 | Esquema v1 | `db/migrations/001_init.sql` | Tablas e índices creados |
| 1.5 | Repositorios | `db/repositories/*.py` | CRUD probado con `tmp_path` |
| 1.6 | Núcleo de operaciones | `operations/base.py`, `registry.py`, `merge.py` | Merge actual pasa sin cambios |
| 1.7 | Cola persistente + worker | `services/job_worker.py` | Job sobrevive reinicio; `interrupted` correcto |
| 1.8 | Routers y errores | `api/*.py`, `core/errors.py` | `/api/merge-jobs` sigue funcionando como alias |
| 1.9 | Token y path policy | `core/security.py`, `services/path_policy.py` | Request sin token rechazado; reveal restringido |
| 1.10 | Capacidades | `services/capabilities.py` | Reporta ausencias reales en <3 s |
| 1.11 | Split de frontend | `app/`, `features/merge/`, `lib/api/` | UI idéntica; gates verdes |
| 1.12 | Migrar `fitz` → `pymupdf` y fijar versión | `main.py`, `pdf_inspector.py`, `pdf_merger.py`, tests, `requirements.txt` | Sin `FutureWarning`; 9 tests verdes |
| 1.13 | Tests y CI | `backend/tests/`, `frontend/src/**/*.test.tsx`, `.github/workflows/ci.yml` | Pipeline Windows verde |

### Semana 3 — F1 backend

| # | Tarea | Archivos principales | Hecho cuando |
|---|---|---|---|
| 2.1 | Parser de rangos | `operations/split.py` + tests | Tabla de casos: válidos, solapados, fuera de rango, abiertos |
| 2.2 | Plantilla de nombres | `operations/split.py` | Tokens, sanitización Windows, `{index:02}` |
| 2.3 | Plan y preview | `operations/split.py`, `api/operations.py` | Preview no escribe; cuenta y colisiones correctas |
| 2.4 | Ejecución y verificación | `operations/split.py` | Cada salida se reabre y se valida |
| 2.5 | Política de colisión | `operations/split.py` | `suffix`, `fail`, `overwrite` probados |
| 2.6 | Progreso y cancelación | `operations/split.py`, `job_worker.py` | Cancelar limpia temporales |
| 2.7 | Reporte e historial | `db/repositories/history.py` | Job deja reporte consultable |
| 2.8 | Tests de integración | `tests/integration/test_split_api.py` | Flujo preview → job → resultado |

### Semana 4 — F1 frontend + cierre

| # | Tarea | Archivos principales | Hecho cuando |
|---|---|---|---|
| 3.1 | Selector de modo | `features/split/` | `ranges`, `every`, `single` |
| 3.2 | Editor de rangos | `features/split/` | Chips válidos, error inline, estimación en vivo |
| 3.3 | Salida y nombres | `features/split/` | Carpeta nativa, plantilla, colisiones visibles |
| 3.4 | Progreso y resultado | `features/split/` | Barra real, cancelar, abrir archivo/carpeta |
| 3.5 | Navegación Unir/Dividir | `app/AppShell.tsx` | Conserva atajos y tema; `aria` correcto |
| 3.6 | Tests de UI | `features/split/*.test.tsx` | Parser, preview y errores cubiertos |
| 3.7 | E2E | `e2e/split.spec.ts` | 3 archivos reales desde la UI |
| 3.8 | Documentación | `README.md`, `docs/adr/`, plan maestro | Gates + desviaciones actualizadas |

### Detalle funcional de "Dividir PDF"

**Modos**

- `ranges`: cada grupo separado por coma genera un archivo. `1-3, 5, 8-10`.
- `every`: un archivo cada N páginas. `N=1` equivale a una página por archivo.
- `single`: atajo de `every=1`.

**Validaciones**

- Rango fuera de `1..page_count` → error con página y máximo.
- Grupo vacío (`1-3,,5`) → error de sintaxis.
- Inicio mayor que fin → error.
- Solapamiento → advertencia, no error; la UI lo muestra antes de ejecutar.
- Documento protegido → error de ítem, no de job.
- Nombre resultante inválido en Windows (`<>:"/\|?*`, reservados `CON`, `PRN`, `AUX`, `NUL`, `COM1`…`LPT9`, punto final) → sanitización + aviso.
- Ruta de salida sin permisos → error claro con la ruta.

**Nombres**

- Default: `{name}_parte_{index:02}`.
- `{name}` = nombre del PDF sin extensión, sanitizado.
- `{date}` = `YYYYMMDD`.
- Extensión `.pdf` se agrega si falta.
- Longitud total ≤ 240 caracteres para margen de path de Windows.

**Salida**

- Default: `<carpeta_del_origen>/<nombre>_partes/`.
- Si el origen es una copia administrada (upload), default `Downloads/<nombre>_partes/`.
- Nunca se escribe dentro de la carpeta de origen sin subcarpeta.

**Resultado**

- Éxito: cantidad de archivos, páginas totales, ruta de salida, duración.
- Parcial: lista de fallidos con motivo y botón "Reintentar fallidos".
- Cancelado: archivos publicados + temporales eliminados.

---

## 8. Estrategia de pruebas

### Backend

- **Unitarias:** parser de rangos, plantilla de nombres, sanitización, política de colisión, migraciones, path policy.
- **Integración:** `TestClient` + base temporal, flujo completo de sesión → preview → job → SSE → reporte.
- **Cola:** job sobrevive reinicio, cancelación, fallo aislado, `interrupted`.
- **PDF real:** fixtures generadas con PyMuPDF (1, 3, 10, 100 páginas; con texto; con imagen; protegido). Nada descargado.
- **Rendimiento:** script `scripts/benchmark_split.py`; medir 1, 100, 500, 1000 páginas; registrar tiempo, RSS y tamaño.

### Frontend

- **Vitest + Testing Library + MSW** para hooks, cliente API y features.
- **Regresión de F0:** mismas acciones de unión, mismos textos, mismos atajos.
- **Accesibilidad:** mantener `axe-core` sin violaciones en las vistas nuevas.
- **E2E Playwright:** flujo unir (existente) y dividir (nuevo), contra el build servido por el backend.

### Gates por fase

```text
backend:   pytest -q                     → 0 fallos
frontend:  npm run lint                  → 0 errores
           npx tsc -b                    → exit 0
           npm run test -- --run         → 0 fallos
           npm run build                 → OK
e2e:       playwright test               → OK
packaged:  smoke del .exe (health, UI, operación) → OK
```

Ningún gate se relaja "temporalmente". Si una fase rompe un gate, no se mergea.

---

## 9. Rendimiento y recursos

- **Un worker** por defecto; el límite se mide, no se adivina.
- **Memoria:** objetivo < 250 MB de RSS en lotes de 500 páginas; se mide con `psutil` en cada job (ya existe el patrón).
- **Miniaturas:** cache en disco, no en memoria; presupuesto 512 MB; evicción LRU.
- **SQLite:** transacciones cortas; nunca dentro del loop de render.
- **PDFs grandes:** abrir, procesar y cerrar por documento; no mantener todos abiertos.
- **Progreso:** actualizar la fila del job como máximo cada 250 ms o en cambios de estado; los eventos SSE pueden ser más frecuentes.
- **Benchmarks obligatorios:** merge (existente), split, extracción de imágenes, OCR (si está disponible).

---

## 10. Seguridad e integridad

- Token obligatorio en app empaquetada; dev con bypass explícito.
- `Origin`/`Host` limitados a loopback; CORS solo orígenes de desarrollo.
- Sin rutas arbitrarias: el backend resuelve rutas desde IDs registrados.
- `reveal` solo para documentos, salidas o rutas de diálogo de la sesión.
- Salidas siempre por temporal + `os.replace`.
- Originales intactos; hash y mtime verificados en tests.
- Logs sin rutas completas ni contenido de documentos; nivel configurable.
- Datos en el perfil del usuario; nada en el directorio de instalación.
- Sin telemetría, sin red saliente, sin servicios pagos.

---

## 11. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Licencia AGPL de PyMuPDF | Alto si se distribuye binario | Decidir antes de releases: mantener AGPL + código público o comprar licencia |
| Crecimiento del modelo de páginas | Alto | Materialización perezosa + límites medidos |
| Scope creep por 57 ítems | Muy alto | Fases cerradas con gates; F7 condicional |
| SQLite con hilos y jobs | Medio | Un worker, transacciones cortas, WAL, tests de concurrencia |
| Token en app servida por `StaticFiles` | Medio | Token por fragmento + `sessionStorage`; dev bypass documentado |
| Drag & drop sin ruta real en navegador | Medio | Selector nativo como camino principal; upload informado |
| Herramientas externas ausentes | Medio | Capacidades + "No disponible" honesto |
| Rutas Windows largas, permisos, antivirus | Medio | Sanitización, límite 240, errores claros, smoke en máquina limpia |
| Memoria en lotes grandes | Medio | Benchmarks por fase; abortar con mensaje, no con crash |
| Fidelidad de conversiones | Alto | Advertencias explícitas; no prometer paridad |

---

## 12. Decisiones pendientes del usuario

| ID | Pregunta | Recomendación |
|---|---|---|
| P-01 | ¿PyMuPDF se mantiene bajo AGPL con código público o se compra licencia comercial antes de distribuir? | Mantener AGPL y publicar el código; decidir antes del primer release público del binario |
| P-02 | ¿Salida por defecto de dividir: subcarpeta `<nombre>_partes` junto al origen o `Downloads`? | Subcarpeta junto al origen; respeta la relación con el archivo |
| P-03 | ¿Modelo de sesión: una sesión actual autoguardada + sesiones guardadas explícitas? | Sí; es el modelo mental más simple y cubre F.3 |
| P-04 | ¿Colisión de nombres: auto-sufijo `_2`, fallar o preguntar? | Auto-sufijo con aviso en el preview |
| P-05 | ¿Se acepta que OCR/Office/PDF-A queden "No disponible" hasta que el usuario instale la herramienta? | Sí; nunca simular |
| P-06 | ¿La app sigue siendo navegador + backend local o se evalúa Electron/Tauri más adelante? | Mantener navegador + backend; el .exe ya funciona y evita un runtime extra |

Ninguna de estas bloquea F0. P-01 y P-02 conviene resolverlas antes de F1.

---

## 13. Qué no se hace en este plan

- No se implementan las 57 funciones en paralelo.
- No se agrega PDF.js mientras el render de PyMuPDF alcance.
- No se agrega Electron/Tauri.
- No se agregan servicios en la nube, telemetría ni APIs pagas.
- No se empaquetan Tesseract, LibreOffice, qpdf ni Ghostscript.
- No se simula OCR, conversión de Office ni conformidad PDF/A.
- No se reemplaza el rediseño de UI existente: se preserva y se extiende.

---

## 14. Próximo paso concreto

1. Aprobar este plan y responder P-01/P-02 (las demás pueden quedar con el default recomendado).
2. Abrir rama `feat/f0-cimientos`.
3. Ejecutar las Semanas 1–2 (F0) del Sprint 1 en el orden de la tabla §7.
4. Al cerrar F0: congelar gates, actualizar `README.md`, `docs/adr/` y `memory.md`.
5. Recién entonces abrir `feat/f1-dividir`.

**Definición de terminado del plan:** F0 y F1 cerradas con gates verdes, app empaquetada funcionando, dividir PDF operativo de punta a punta y documentación actualizada.
