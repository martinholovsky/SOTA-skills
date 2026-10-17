-- reportkit schema
-- Run once to initialise a fresh database.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------
-- Tenants
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenants (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    suspended   INTEGER NOT NULL DEFAULT 0,  -- 0=active, 1=suspended
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- ------------------------------------------------------------
-- Users
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    username    TEXT NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('viewer', 'editor', 'admin')),
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE (tenant_id, username)
);

-- ------------------------------------------------------------
-- Sessions  (bearer-token → user)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    token       TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at  TEXT NOT NULL
);

-- ------------------------------------------------------------
-- Reports
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reports (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    owner_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    body        TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- ------------------------------------------------------------
-- Attachments
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attachments (
    id          TEXT PRIMARY KEY,
    report_id   TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    filename    TEXT NOT NULL,
    mime_type   TEXT NOT NULL DEFAULT 'application/octet-stream',
    size_bytes  INTEGER NOT NULL,
    data        BLOB NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- ------------------------------------------------------------
-- Billing ledger
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS billing_events (
    id              TEXT PRIMARY KEY,   -- provider's event id
    tenant_id       TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,
    amount_cents    INTEGER NOT NULL DEFAULT 0,
    raw_payload     TEXT NOT NULL,
    received_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- ------------------------------------------------------------
-- Indexes
-- ------------------------------------------------------------

-- Hot path: resolve permissions (sessions → users → tenants)
CREATE INDEX IF NOT EXISTS idx_sessions_token     ON sessions(token);
CREATE INDEX IF NOT EXISTS idx_users_tenant_role  ON users(tenant_id, role);

-- Report listing / search
CREATE INDEX IF NOT EXISTS idx_reports_owner      ON reports(owner_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_tenant     ON reports(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_reports_title      ON reports(owner_id, title);

-- Attachments
CREATE INDEX IF NOT EXISTS idx_attachments_report ON attachments(report_id);

-- Billing idempotency
CREATE UNIQUE INDEX IF NOT EXISTS idx_billing_event_id ON billing_events(id);
