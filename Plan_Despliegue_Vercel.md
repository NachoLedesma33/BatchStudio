# Plan: Despliegue completo en Vercel (sin perder funcionalidad local)

## Objetivo
Permitir que la misma aplicación se ejecute:
- en modo local (como hoy: SQLite, archivos locales, diálogos nativos, worker persistente), y
- en modo nube (Vercel + almacenamiento/DB externos), sin romper el modo local.

No se borra el backend actual: se agrega un "modo nube" detrás de flags y adaptadores.

## Principio
- `PDFBS_MODE=local` (default) → comportamiento actual, sin cambios.
- `PDFBS_MODE=cloud` → usa adaptadores de almacenamiento/DB y desactiva capacidades del sistema operativo.

## Limitaciones de Vercel (importantes)
- Sin sistema de archivos persistente (solo `/tmp` efímero).
- Sin procesos en segundo plano persistentes (el worker actual no sobrevive).
- Timeouts: 10 s (Hobby) / 60 s (Pro) por invocación.
- Sin diálogos nativos.
Consecuencia: los trabajos pesados deben ser síncronos y acotados, o delegarse a un proveedor con workers.

## Arquitectura propuesta (doble modo)

### 1. Almacenamiento abstracto
Crear `app/storage/base.py` con interfaz:
- `save_upload(session_id, file) -> key`
- `open(key) -> bytes/stream`
- `save_output(key, bytes) -> url`
- `delete(key)`

Implementaciones:
- `LocalStorage` (actual, rutas en disco)
- `CloudStorage` (Cloudflare R2 / S3 / Vercel Blob)

En modo local se usan rutas; en nube se usan keys. Los repositorios guardan `storage_key` en lugar de path absoluto cuando `mode=cloud`.

### 2. Base de datos
- Local: SQLite (actual).
- Nube: Postgres (Neon/Supabase) con las mismas migraciones adaptadas.
- Abstracción: `Database` actual ya encapsula conexión; crear `PostgresDatabase` con la misma interfaz o usar SQLAlchemy.
- Migraciones: mantener `001_init.sql` para SQLite y `001_init_pg.sql` para Postgres.

### 3. Jobs / cola
Opciones:
- A) Síncrono: los endpoints `/api/jobs` ejecutan la operación en la misma request y devuelven el resultado. Apto para PDFs pequeños; riesgo de timeout.
- B) Asíncrono con proveedor externo: Vercel Cron + tabla de jobs en Postgres; un worker serverless procesa por lotes.
- C) Usar un proveedor con workers persistentes (Fly.io/Railway) solo para el backend, manteniendo Vercel para el frontend.

Recomendación: C para no romper funcionalidad; A/B solo si se acepta el límite de tiempo.

### 4. Archivos y diálogos
- Modo local: pick-folder/pick-files nativos (actual).
- Modo nube: upload por navegador (multipart) y descarga de resultados; deshabilitar botones nativos con "No disponible en modo nube".

### 5. Capacidades (Tesseract/LibreOffice)
- En nube, solo disponibles si el contenedor/serverless las incluye (no en Vercel puro).
- `/api/system/capabilities` ya reporta ausencias reales; mantener.

### 6. Seguridad
- Token local sigue siendo válido en local.
- En nube: token fijo por entorno (`PDFBS_TOKEN`) o JWT de sesión; validar `Origin` contra el dominio de Vercel.

### 7. Detección de modo
- Backend: `PDFBS_MODE=local|cloud`.
- Frontend: `VITE_API_BASE` y `VITE_MODE`. Si `VITE_MODE=cloud`, oculta acciones locales y usa upload web.

## Plan por etapas (sin romper local)

Etapa 1 — Abstracciones (1 semana)
- Crear `app/storage/base.py` + `LocalStorage`.
- Reemplazar accesos directos a `Path` en operaciones por `storage` (solo en cloud; local sigue igual).
- Tests: que modo local no cambie (88 tests actuales siguen verdes).

Etapa 2 — DB cloud (1 semana)
- Implementar `PostgresDatabase` + migraciones PG.
- Repositorios usan la abstracción DB (ya la tienen).
- Config: `PDFBS_DATABASE_URL`.

Etapa 3 — Cloud storage (1 semana)
- Implementar `CloudStorage` (R2/S3).
- Endpoints de upload/download usan storage.

Etapa 4 — Jobs en nube (1-2 semanas)
- Decidir síncrono vs worker externo.
- Si síncrono: endpoints devuelven resultado directo y el frontend muestra progreso estimado.
- Si asíncrono: tabla de jobs + cron.

Etapa 5 — Frontend dual (1 semana)
- `runtime.ts` con `isLocalMode`.
- Ocultar diálogos nativos en nube.
- Upload por navegador.

Etapa 6 — Despliegue (3-5 días)
- `vercel.json` para frontend.
- Backend en Vercel Serverless Functions (si síncrono) o en proveedor con workers.
- Variables de entorno.

## Archivos nuevos sugeridos
- `backend/app/storage/base.py`
- `backend/app/storage/local.py`
- `backend/app/storage/cloud.py`
- `backend/app/db/postgres.py`
- `backend/app/db/migrations/001_init_pg.sql`
- `frontend/src/lib/runtime.ts`
- `vercel.json`
- `.env.cloud.example`

## Riesgos
- Timeouts en Vercel para PDFs grandes.
- Costo/complejidad de R2/Neon.
- Pérdida de "local-first" (privacidad).

## Recomendación final
Si el objetivo es "subir y que ande igual", Vercel puro no alcanza por los workers y el sistema de archivos. La opción más segura sin romper nada es:
- mantener el modo local actual, y
- agregar un modo nube opcional con las abstracciones anteriores, aceptando límites de tiempo.

Si querés, puedo empezar por la Etapa 1 (abstracción de storage) sin tocar el comportamiento local.
