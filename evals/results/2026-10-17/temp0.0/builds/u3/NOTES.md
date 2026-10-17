# reportkit — design notes

## Decisions

### No web framework
The HTTP surface is a plain class (`ReportService`) whose methods accept and
return dicts.  A thin adapter (WSGI, ASGI, or a test harness) is responsible
for serialising to JSON and mapping `ReportkitError.http_status` to an HTTP
response code.  This keeps the domain logic framework-agnostic and trivially
testable without spinning up a server.

### Permissions derived at runtime, not stored
Roles are stored; permissions are computed from the role at call time via a
dict lookup (`_ROLE_PERMISSIONS`).  There is no `permissions` table.  The hot
path (`list_reports`) resolves the caller with a single three-table JOIN
(`sessions → users → tenants`); an index on `sessions.token` keeps this fast.
Changing a role (via `set_role`) takes effect on the very next request with no
cache invalidation needed.

### Sort-column allowlist in `search_reports`
The UI passes the user's sort choice through `request["query"]["sort"]`.
Rather than parameterising the column name (SQLite does not support
`ORDER BY ?`), the value is validated against a small frozenset of allowed
column names before being interpolated into the query string.  An invalid
value raises `ValidationError(400)` rather than silently falling back to a
default, so the UI learns about bugs immediately.

### Billing webhook idempotency
The `invoice_id` column carries a `UNIQUE` constraint.  Duplicate deliveries
from the provider hit an `IntegrityError` which is caught and returned as a
successful `200 OK` — the provider stops retrying and no double-payment is
recorded.  Signature verification uses `hmac.compare_digest` to avoid
timing-oracle attacks.

### Attachment scanning
The scanner checks for a small set of known-bad byte signatures (EICAR,
PE/ELF/Mach-O headers).  In production this would call an external AV or
content-policy service; the interface (`scan(data, filename)` raising
`ContentPolicyError`) is designed to make that substitution a one-file change.

### Event registry
The registry is synchronous and in-process.  Handler exceptions are caught,
logged, and do not abort the calling transaction.  This is intentional: a
broken notification handler must not roll back a successful report creation.
For production use the registry would be replaced with (or backed by) a
message queue.

### `tenant.quota_exceeded` handler
The spec mentions a `tenant.quota_exceeded` handler that suspends a tenant,
belonging to a retired batch-import feed.  The event name is supported by the
registry (any handler can be registered against it), but no handler is wired
up by default.  When the batch-import feed returns, a handler can be registered
with `default_registry.on("tenant.quota_exceeded")` without touching any other
code.

### Ops console functions
`purge_tenant` and `set_role` are plain functions that accept an open
connection, not HTTP endpoints.  They are called by the internal ops console
over the private network; the console owns its own access control.  An
`actor_id` parameter is accepted on both for future audit-log use (the audit
log table is not yet implemented — see below).

## Deliberate omissions

| Item | Reason |
|---|---|
| Audit log table | Noted as future work; `actor_id` is threaded through ops functions so adding it later is non-breaking. |
| Pagination on `list_reports` / `search_reports` | Not in the spec; the query is structured so a `LIMIT`/`OFFSET` clause is easy to add. |
| `updated_at` trigger | SQLite does not have `ON UPDATE` triggers in DDL; the service layer sets `updated_at` explicitly on writes. |
| HTTPS / TLS | Infrastructure concern, outside the service boundary. |
| Rate limiting | Infrastructure / reverse-proxy concern. |
| Attachment retrieval endpoint | Not listed in the spec's HTTP surface table. |
| Connection pooling | The caller supplies the connection; pooling is the adapter's responsibility. |
| Migration tooling | Schema is applied idempotently via `CREATE TABLE IF NOT EXISTS`; a proper migration tool (e.g. Alembic) would be added before the first schema change. |
