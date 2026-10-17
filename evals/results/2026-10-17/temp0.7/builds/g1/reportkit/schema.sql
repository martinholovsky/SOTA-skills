-- ============================================================
-- reportkit schema
-- ============================================================
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tenants (
    id          TEXT PRIMARY KEY,          -- UUID v4
    name        TEXT NOT NULL,
    suspended   INTEGER NOT NULL DEFAULT 0 CHECK (suspended IN (0, 1)),
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,          -- UUID v4
    tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    username    TEXT NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('viewer', 'editor', 'admin')),
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (tenant_id, username)
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash  TEXT PRIMARY KEY,          -- SHA-256 hex of the bearer token
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at  TEXT NOT NULL,             -- ISO-8601 UTC
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS reports (
    id          TEXT PRIMARY KEY,          -- UUID v4
    tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    owner_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    body        TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_reports_tenant_owner
    ON reports (tenant_id, owner_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_reports_tenant_created
    ON reports (tenant_id, created_at DESC);

CREATE TABLE IF NOT EXISTS attachments (
    id              TEXT PRIMARY KEY,      -- UUID v4
    report_id       TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    tenant_id       TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    original_name   TEXT NOT NULL,         -- display only, never used as path
    storage_key     TEXT NOT NULL UNIQUE,  -- server-generated UUID path segment
    size_bytes      INTEGER NOT NULL,
    content_type    TEXT NOT NULL,
    scan_status     TEXT NOT NULL DEFAULT 'pending'
                    CHECK (scan_status IN ('pending', 'clean', 'rejected')),
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS billing_events (
    id              TEXT PRIMARY KEY,      -- idempotency key from provider
    tenant_id       TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,
    amount_cents    INTEGER NOT NULL,
    processed_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    actor_id    TEXT,                      -- NULL for system/webhook actions
    tenant_id   TEXT,
    action      TEXT NOT NULL,
    target_type TEXT,
    target_id   TEXT,
    detail      TEXT                       -- JSON blob, no PII/secrets
);

CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_log (actor_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_audit_tenant ON audit_log (tenant_id, ts DESC);

-- Rate-limit buckets: keyed on (scope, key) where scope is e.g. 'api', 'webhook'
CREATE TABLE IF NOT EXISTS rate_limit_buckets (
    scope       TEXT NOT NULL,
    key         TEXT NOT NULL,
    window_start TEXT NOT NULL,            -- ISO-8601 UTC truncated to the minute
    count       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (scope, key, window_start)
);
