-- Esquema v1 de PDF Batch Studio.
-- No editar esta migración una vez aplicada: agregar 002_*.sql.

CREATE TABLE IF NOT EXISTS sessions (
  id              TEXT PRIMARY KEY,
  name            TEXT NOT NULL,
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL,
  last_opened_at  TEXT,
  state_json      TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS session_documents (
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

CREATE TABLE IF NOT EXISTS document_pages (
  document_id     TEXT NOT NULL REFERENCES session_documents(id) ON DELETE CASCADE,
  page_no         INTEGER NOT NULL,
  page_order      INTEGER NOT NULL,
  rotation        INTEGER NOT NULL DEFAULT 0,
  excluded        INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (document_id, page_no)
);

CREATE TABLE IF NOT EXISTS operations (
  id              TEXT PRIMARY KEY,
  session_id      TEXT REFERENCES sessions(id) ON DELETE SET NULL,
  kind            TEXT NOT NULL,
  params_json     TEXT NOT NULL,
  created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
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

CREATE TABLE IF NOT EXISTS job_items (
  job_id          TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  idx             INTEGER NOT NULL,
  label           TEXT NOT NULL,
  status          TEXT NOT NULL,
  output_path     TEXT,
  message         TEXT,
  PRIMARY KEY (job_id, idx)
);

CREATE TABLE IF NOT EXISTS history (
  id              TEXT PRIMARY KEY,
  job_id          TEXT REFERENCES jobs(id) ON DELETE SET NULL,
  kind            TEXT NOT NULL,
  summary         TEXT NOT NULL,
  inputs_json     TEXT NOT NULL,
  outputs_json    TEXT NOT NULL,
  created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
  key             TEXT PRIMARY KEY,
  value_json      TEXT NOT NULL,
  updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_status_created   ON jobs(status, created_at);
CREATE INDEX IF NOT EXISTS idx_history_created       ON history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_docs_session_order    ON session_documents(session_id, order_index);
CREATE INDEX IF NOT EXISTS idx_pages_document_order  ON document_pages(document_id, page_order);
