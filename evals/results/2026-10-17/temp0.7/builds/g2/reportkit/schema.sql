-- ============================================================
-- reportkit schema
-- All timestamps are UTC Unix epoch integers.
-- ============================================================

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ----------------------------------------------------------
-- tenants
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenants (
    id         TEXT PRIMARY KEY,          -- UUID v4
    name       TEXT NOT NULL,
    suspended  INTEGER NOT NULL DEFAULT 0 -- 0 = active, 1 = suspended
);

-- ----------------------------------------------------------
-- users
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id         TEXT PRIMARY KEY,          -- UUID v4
    tenant_id  TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    username   TEXT NOT NULL,
    role       TEXT NOT NULL CHECK(role IN ('viewer', 'editor', 'admin')),
    created_at INTEGER NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_users_tenant_username
    ON users(tenant_id, username);

-- ----------------------------------------------------------
-- sessions  (bearer-token store)
-- stored value is SHA-256(raw_token) so a DB dump cannot be
-- replayed directly; the raw token is shown once at creation.
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,          -- hex(SHA-256(raw_token))
    user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id  TEXT NOT NULL,
    expires_at INTEGER NOT NULL           -- Unix epoch
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

-- ----------------------------------------------------------
-- permission_cache
-- Materialised view of (user_id → permissions).
-- Invalidated by set_role; rebuilt on next request.
-- Stored as a JSON array of permission strings.
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS permission_cache (
    user_id     TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    permissions TEXT NOT NULL,            -- JSON array
    role_at     TEXT NOT NULL             -- role snapshot; stale-detection
);

-- ----------------------------------------------------------
-- reports
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS reports (
    id         TEXT PRIMARY KEY,          -- UUID v4
    tenant_id  TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    owner_id   TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title      TEXT NOT NULL,
    body       TEXT NOT NULL DEFAULT '',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_reports_tenant_owner
    ON reports(tenant_id, owner_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_reports_tenant_title
    ON reports(tenant_id, owner_id, title);

-- ----------------------------------------------------------
-- attachments
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS attachments (
    id          TEXT PRIMARY KEY,         -- UUID v4
    tenant_id   TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    owner_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    report_id   TEXT REFERENCES reports(id) ON DELETE SET NULL,
    filename    TEXT NOT NULL,            -- display name only; never used as path
    storage_key TEXT NOT NULL UNIQUE,     -- UUID-based key; no user input
    size_bytes  INTEGER NOT NULL,
    mime_type   TEXT NOT NULL,
    scan_status TEXT NOT NULL DEFAULT 'pending'
                CHECK(scan_status IN ('pending', 'clean', 'rejected')),
    created_at  INTEGER NOT NULL
);

-- ----------------------------------------------------------
-- billing_events  (idempotency log)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS billing_events (
    event_id   TEXT PRIMARY KEY,          -- provider's event id
    tenant_id  TEXT NOT NULL,
    amount     INTEGER NOT NULL,          -- cents
    currency   TEXT NOT NULL,
    processed_at INTEGER NOT NULL
);

-- ----------------------------------------------------------
-- audit_log  (immutable; INSERT only)
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         INTEGER NOT NULL,          -- Unix epoch
    actor_id   TEXT,                      -- NULL for system/webhook
    tenant_id  TEXT,
    action     TEXT NOT NULL,
    target_id  TEXT,
    detail     TEXT                       -- JSON; no secrets/PII
);

CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts);
