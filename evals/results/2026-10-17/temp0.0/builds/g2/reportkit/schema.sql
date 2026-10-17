-- reportkit schema
-- All DDL is idempotent (IF NOT EXISTS).

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tenants (
    id          TEXT PRIMARY KEY,          -- UUID
    suspended   INTEGER NOT NULL DEFAULT 0 CHECK (suspended IN (0, 1)),
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,          -- UUID
    tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role        TEXT NOT NULL CHECK (role IN ('viewer', 'editor', 'admin')),
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash  TEXT PRIMARY KEY,          -- SHA-256 hex of the bearer token
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at  TEXT NOT NULL,             -- ISO-8601 UTC
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

CREATE TABLE IF NOT EXISTS reports (
    id          TEXT PRIMARY KEY,          -- UUID
    tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    owner_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 500),
    body        TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_reports_tenant_owner ON reports(tenant_id, owner_id);
CREATE INDEX IF NOT EXISTS idx_reports_created      ON reports(tenant_id, created_at DESC);

CREATE TABLE IF NOT EXISTS attachments (
    id          TEXT PRIMARY KEY,          -- UUID
    tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    owner_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    report_id   TEXT REFERENCES reports(id) ON DELETE SET NULL,
    filename    TEXT NOT NULL CHECK (length(filename) BETWEEN 1 AND 255),
    size_bytes  INTEGER NOT NULL CHECK (size_bytes >= 0),
    scan_status TEXT NOT NULL DEFAULT 'pending'
                     CHECK (scan_status IN ('pending', 'clean', 'rejected')),
    storage_key TEXT NOT NULL UNIQUE,      -- server-generated UUID path
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_attachments_tenant ON attachments(tenant_id);

CREATE TABLE IF NOT EXISTS invoice_events (
    event_id    TEXT PRIMARY KEY,          -- idempotency key from provider
    tenant_id   TEXT NOT NULL,
    amount      INTEGER NOT NULL,          -- cents
    currency    TEXT NOT NULL CHECK (length(currency) = 3),
    processed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    actor_id    TEXT,                      -- NULL for system/webhook events
    tenant_id   TEXT,
    action      TEXT NOT NULL,
    target_type TEXT,
    target_id   TEXT,
    detail      TEXT                       -- JSON, no PII/secrets
);

CREATE INDEX IF NOT EXISTS idx_audit_actor  ON audit_log(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_tenant ON audit_log(tenant_id);
CREATE INDEX IF NOT EXISTS idx_audit_ts     ON audit_log(ts);
