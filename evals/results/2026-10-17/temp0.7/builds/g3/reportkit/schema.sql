-- reportkit schema
-- All DDL is idempotent (CREATE TABLE IF NOT EXISTS).

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tenants (
    id          TEXT PRIMARY KEY,          -- UUID
    suspended   INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,          -- UUID
    tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    role        TEXT NOT NULL CHECK(role IN ('viewer', 'editor', 'admin')),
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);

-- Sessions: bearer tokens are stored as SHA-256 hex digests.
CREATE TABLE IF NOT EXISTS sessions (
    token_hash  TEXT PRIMARY KEY,          -- SHA-256(raw_token) hex
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at  TEXT NOT NULL,             -- ISO-8601 UTC
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

CREATE TABLE IF NOT EXISTS reports (
    id          TEXT PRIMARY KEY,          -- UUID
    tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    owner_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    body        TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_reports_tenant_owner ON reports(tenant_id, owner_id);
CREATE INDEX IF NOT EXISTS idx_reports_tenant_created ON reports(tenant_id, created_at);

CREATE TABLE IF NOT EXISTS attachments (
    id              TEXT PRIMARY KEY,      -- UUID
    report_id       TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    tenant_id       TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    filename        TEXT NOT NULL,         -- display name only, never used as path
    storage_key     TEXT NOT NULL UNIQUE,  -- server-generated UUID used as file key
    size_bytes      INTEGER NOT NULL,
    content_type    TEXT NOT NULL,
    scan_status     TEXT NOT NULL CHECK(scan_status IN ('clean', 'flagged')) DEFAULT 'clean',
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_attachments_report ON attachments(report_id);

-- Billing ledger entries (from invoice.paid webhook events)
CREATE TABLE IF NOT EXISTS ledger_entries (
    id              TEXT PRIMARY KEY,      -- UUID
    tenant_id       TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    invoice_id      TEXT NOT NULL,
    amount_cents    INTEGER NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,  -- provider event id; prevents replay
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_ledger_tenant ON ledger_entries(tenant_id);

-- Immutable audit log for ops mutations (purge_tenant, set_role).
CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    actor_id    TEXT NOT NULL,
    action      TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id   TEXT NOT NULL,
    detail      TEXT NOT NULL DEFAULT '{}',  -- JSON, no secrets/PII
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Rate-limit counters (rolling window, keyed by caller + endpoint).
-- Cleaned up lazily on reads.
CREATE TABLE IF NOT EXISTS rate_limit_counters (
    bucket_key  TEXT NOT NULL,
    window_start TEXT NOT NULL,
    count       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (bucket_key, window_start)
);
