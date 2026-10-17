-- reportkit schema
-- Run once to initialise the database.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------
-- Tenants
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenants (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    suspended   INTEGER NOT NULL DEFAULT 0,   -- boolean
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
    owner_id    TEXT NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    title       TEXT NOT NULL,
    body        TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_reports_owner_created
    ON reports (owner_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_reports_tenant_created
    ON reports (tenant_id, created_at DESC);

-- Full-text search over report titles (content table mirrors reports)
CREATE VIRTUAL TABLE IF NOT EXISTS reports_fts
    USING fts5(title, report_id UNINDEXED, owner_id UNINDEXED, tenant_id UNINDEXED);

-- Keep FTS in sync
CREATE TRIGGER IF NOT EXISTS reports_ai AFTER INSERT ON reports BEGIN
    INSERT INTO reports_fts(title, report_id, owner_id, tenant_id)
    VALUES (NEW.title, NEW.id, NEW.owner_id, NEW.tenant_id);
END;

CREATE TRIGGER IF NOT EXISTS reports_au AFTER UPDATE OF title ON reports BEGIN
    UPDATE reports_fts SET title = NEW.title
    WHERE report_id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS reports_ad AFTER DELETE ON reports BEGIN
    DELETE FROM reports_fts WHERE report_id = OLD.id;
END;

-- ------------------------------------------------------------
-- Attachments
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attachments (
    id          TEXT PRIMARY KEY,
    report_id   TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
    tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    owner_id    TEXT NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    filename    TEXT NOT NULL,
    mime_type   TEXT NOT NULL DEFAULT 'application/octet-stream',
    size_bytes  INTEGER NOT NULL,
    data        BLOB NOT NULL,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_attachments_report
    ON attachments (report_id);

-- ------------------------------------------------------------
-- Billing ledger
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS billing_events (
    id              TEXT PRIMARY KEY,   -- provider's event id
    tenant_id       TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,
    amount_cents    INTEGER NOT NULL DEFAULT 0,
    payload         TEXT NOT NULL,      -- raw JSON
    received_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Idempotency: one row per provider event id (handles retries)
CREATE UNIQUE INDEX IF NOT EXISTS idx_billing_events_id
    ON billing_events (id);

-- ------------------------------------------------------------
-- Permissions cache / hot-path index
-- Roles are stored on users; this index makes the three-table
-- join (users → tenants → role) fast for the list view.
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_users_tenant_role
    ON users (tenant_id, role);
