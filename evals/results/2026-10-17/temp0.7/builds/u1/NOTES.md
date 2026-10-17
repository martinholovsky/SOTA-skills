# reportkit — design notes

## Decisions

### No web framework
The HTTP surface is a plain class whose methods accept a `request` dict and
return a `{"status": int, "body": dict}` response dict.  A thin WSGI/ASGI
adapter (not included) would translate real HTTP objects into this shape.  This
keeps the core logic free of framework coupling and makes unit-testing trivial —
no HTTP client, no test server.

### SQLite + WAL mode
WAL mode is enabled so that concurrent readers do not block writers.  For a
single-process service this is sufficient; a move to PostgreSQL would require
swapping the connection factory and the `strftime` calls for `NOW()`.

### Permission resolution — hot path
The spec notes that permission resolution is the hottest query.  We resolve it
in a single three-table join (`sessions → users → tenants`) on every request.
We do **not** cache in-process: roles are changed from the ops console and the
spec says changes must take effect immediately.  The composite index
`idx_users_tenant_role` on `(tenant_id, role)` keeps the join fast.

### Sort-column whitelist
`search_reports` accepts a user-supplied sort column.  Rather than a
parameterised bind (SQLite does not support parameterised `ORDER BY`), we
validate the value against a whitelist `{"created_at", "title"}` and fall back
to `created_at` for anything else.  This prevents SQL injection while honouring
the UI control described in the spec.

### LIKE escaping
The title search uses SQLite's `LIKE … ESCAPE '\\'` so that `%` and `_` in
user-supplied search terms are treated as literals rather than wildcards.

### Billing webhook — idempotency
The provider retries deliveries it considers failed.  We use the provider's
event `id` as a `UNIQUE` key in `billing_events`.  A duplicate insert is caught
as `sqlite3.IntegrityError` and silently ignored, making the handler
idempotent.  The HMAC signature is verified before any DB write.

### Attachment scanning
Scanning checks the first 4 KB for known byte signatures (EICAR, ELF, MZ, PHP,
JSP).  This is a defence-in-depth measure, not a replacement for a real AV
engine.  The size limit (25 MB) is enforced before the scan.

### `tenant.quota_exceeded` handler
The batch-import feed that emits this event was retired last quarter.  The
handler is registered in the default event registry as a deliberate no-op with
a log line, so that:
- The registry wiring is in place for when the feed returns.
- Nothing breaks if the event is somehow dispatched in the interim.

### Ops console functions
`purge_tenant` and `set_role` are plain functions that accept a `Connection`,
not HTTP endpoints.  They are called over the private network by the ops
console.  Both accept an `actor_id` for audit logging; a proper audit table
would be the next step.

### Attachments stored as BLOBs
For simplicity, attachment bytes are stored directly in SQLite.  In production
this would be replaced by an object store (S3/GCS) with only the key stored in
the DB.

## Deliberate omissions

- **WSGI/ASGI adapter** — out of scope; the service is framework-agnostic by
  design.
- **Pagination** — `list_reports` and `search_reports` return all matching rows.
  Adding `LIMIT`/`OFFSET` or cursor-based pagination is straightforward.
- **Audit log table** — ops actions are currently only logged to the Python
  logger.
- **Session creation / user registration** — assumed to be handled by an
  identity service; the schema and fixtures support seeding sessions directly.
- **Real AV scanning** — the content scanner uses byte-signature heuristics.
  Integration with ClamAV or a cloud scanning API is a production concern.
- **Migrations** — the schema uses `CREATE TABLE IF NOT EXISTS`; a migration
  tool (e.g. Alembic) would be needed for schema evolution in production.
