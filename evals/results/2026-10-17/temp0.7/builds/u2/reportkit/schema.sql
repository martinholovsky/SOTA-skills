-- reportkit schema
-- Apply with: sqlite3 reportkit.db < reportkit/schema.sql

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
    email       TEXT NOT NULL,
    role        TEXT NOT NULL CHECK(role IN ('viewer', 'editor', 'admin')),
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(tenant_id, email)
);

CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);

-- ------------------------------------------------------------
-- Sessions  (bearer-token → user)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    token       TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

-- ------------------------------------------------------------
-- Reports
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS reports (
    id          TEXT PRIMARY KEY,
    tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    owner_id    TEXT NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    title       TEXT NOT NULL,
    body        TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_reports_owner   ON reports(owner_id);
CREATE INDEX IF NOT EXISTS idx_reports_tenant  ON reports(tenant_id);
CREATE INDEX IF NOT EXISTS idx_reports_created ON reports(owner_id, created_at DESC);

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

CREATE INDEX IF NOT EXISTS idx_attachments_report ON attachments(report_id);

-- ------------------------------------------------------------
-- Billing ledger
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS billing_events (
    id              TEXT PRIMARY KEY,   -- provider's event id
    tenant_id       TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,
    amount_cents    INTEGER NOT NULL DEFAULT 0,
    payload         TEXT NOT NULL,      -- raw JSON from provider
    received_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Unique on provider id prevents double-application on retry
CREATE UNIQUE INDEX IF NOT EXISTS idx_billing_events_id ON billing_events(id);

-- ------------------------------------------------------------
-- Permissions view  (hot path — covered by indexes above)
-- ------------------------------------------------------------
-- Joining here keeps permission logic in one place; the query
-- planner uses idx_sessions_user + idx_users_tenant.
CREATE VIEW IF NOT EXISTS v_caller_permissions AS
SELECT
    s.token,
    u.id          AS user_id,
    u.tenant_id,
    u.role,
    t.suspended   AS tenant_suspended,
    CASE u.role
        WHEN 'viewer' THEN 'report:read'
        WHEN 'editor' THEN 'report:read,report:write'
        WHEN 'admin'  THEN 'report:read,report:write,report:delete,user:manage'
    END           AS permissions_csv,
    s.expires_at
FROM sessions s
JOIN users   u ON u.id        = s.user_id
JOIN tenants t ON t.id        = u.tenant_id;
