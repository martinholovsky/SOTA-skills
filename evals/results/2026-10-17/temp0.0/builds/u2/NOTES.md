# reportkit — design notes

## Decisions

### No web framework
The spec requires a plain class whose methods take a `request` dict.
`ReportHandlers` is that class.  It can be wrapped by any WSGI/ASGI adapter
(e.g. a two-line `wsgiref` shim) without touching business logic.

### SQLite + WAL mode
WAL mode allows concurrent readers alongside a single writer, which is
appropriate for a service that is read-heavy (list/search) and write-light.
Foreign keys are enforced at the connection level (`PRAGMA foreign_keys = ON`).

### Hot permissions query
The spec calls out the permissions join as the hottest query.  The schema
carries a covering index `idx_roles_user_tenant ON roles(user_id, tenant_id)`.
`resolve_caller` performs a single three-table join (sessions → users → roles)
per request rather than separate round-trips.  If the service were to scale
beyond a single process, this is the first candidate for a short-lived
in-process cache keyed on `(token, expires_at)`.

### Sort-column injection defence
`search_reports` accepts a user-supplied sort column.  SQLite parameterised
queries cannot bind column names, so the value is validated against a
`frozenset` allowlist in `db.validate_sort_column` before string interpolation.
An invalid value returns HTTP 400.  This is the only place in the codebase
where a user value is interpolated into SQL.

### Billing idempotency
The billing provider retries deliveries.  The `ledger` table has a `UNIQUE`
constraint on `idempotency_key` (the provider's event ID).  A duplicate
`INSERT` raises `sqlite3.IntegrityError`, which is caught and silently ignored;
the endpoint returns 200 so the provider stops retrying.

### HMAC verification
`billing.verify_signature` uses `hmac.compare_digest` to avoid timing attacks.
The shared secret is read from the environment variable
`BILLING_WEBHOOK_SECRET`; the function raises `EnvironmentError` at call time
(not import time) if the variable is absent, so the rest of the service starts
normally even if billing is not configured.

### Content scanning
`content_scanner.scan` checks for a tuple of byte-string signatures before
persistence.  The interface is a single `scan(data, filename)` function that
raises typed exceptions (`ContentViolation`, `ValueError`).  Swapping in a
real AV service means replacing the body of `scan` without changing any
call-site.

### tenant.quota_exceeded handler
The event is registered and the handler is a documented no-op stub.  The
batch-import feed that emits it was retired; keeping the registration means
the platform team can activate it by replacing the stub body rather than
touching the registry wiring.

### Ops console functions
`purge_tenant` and `set_role` are plain functions in `ops.py`, not HTTP
endpoints.  They are called directly by the internal console over the private
network.  Cascading deletes in the schema (`ON DELETE CASCADE`) mean
`purge_tenant` only needs to delete from `reports`; attachments follow
automatically.

### Attachments stored as BLOBs
For simplicity, attachment bytes are stored directly in SQLite.  At 25 MB per
file this is workable for low-to-moderate volume.  The natural upgrade path is
to store a reference (e.g. an S3 key) instead of the bytes; the
`upload_attachment` handler is the only place that would change.

## Deliberate omissions

- **Pagination** — `list_reports` and `search_reports` return all matching
  rows.  A `LIMIT`/`OFFSET` or cursor-based scheme would be added before
  production.
- **Audit log** — `purge_tenant` and `set_role` log to the Python logger.  A
  proper audit table is the obvious next step.
- **Rate limiting** — not implemented; belongs in a gateway layer.
- **HTTPS / TLS** — the class is transport-agnostic; TLS is the adapter's
  responsibility.
- **Migrations** — `apply_schema` is idempotent (`CREATE TABLE IF NOT EXISTS`)
  but is not a migration system.  Alembic or a hand-rolled migration table
  would be needed for schema evolution.
- **`ExceptionGroup`** — used in `events.py`; requires Python 3.11+.  On
  3.10 this can be replaced with a plain `RuntimeError` wrapping the list of
  causes.
