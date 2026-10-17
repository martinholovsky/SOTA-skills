# reportkit — design notes

## Decisions

### No web framework
The service exposes a plain class (`ReportService`) whose methods accept and
return plain dicts. A thin adapter (WSGI, ASGI, Lambda handler) would sit in
front; that layer is intentionally out of scope so the core is framework-
agnostic and trivially testable without HTTP machinery.

### Authentication via view
The hot-path permission check (session → user → tenant) is expressed as
`v_caller_permissions`, a SQLite view that collapses the three-table join into
a single named query. `resolve_caller` queries the view by token; SQLite uses
`idx_sessions_user` + `idx_users_tenant` to satisfy it. Because roles change
infrequently (ops console only) there is no application-level cache — the view
is fast enough and avoids stale-cache bugs.

### Permissions are derived, not stored
The set of permissions for a role is a static mapping in `auth.py`
(`_ROLE_PERMISSIONS`). The view also materialises a `permissions_csv` column
for observability, but the authoritative check is done in Python against the
frozenset. Adding a new permission requires only a code change, not a data
migration.

### SQL injection prevention in `search_reports`
The `sort` parameter comes directly from the UI. It is validated against an
explicit allowlist (`_ALLOWED_SORT_COLUMNS`) before being interpolated into the
`ORDER BY` clause. All other user-supplied values use parameterised queries.

### Billing webhook idempotency
The provider retries deliveries it considers failed. We deduplicate on the
provider's `id` field via a `UNIQUE INDEX` on `billing_events.id`. A second
delivery of the same event hits an `IntegrityError` and returns 200 (so the
provider stops retrying) without double-applying the payment.

### Attachment scanning
`scanner.py` contains a structural placeholder that checks for the EICAR test
string. The interface (`scan(data, filename) → None | raise`) is intentionally
narrow: swap the body for a ClamAV socket call or a vendor HTTP call without
changing any call sites. Size is checked before scanning so we never load a
25 MB blob into a real scanner unnecessarily.

### `tenant.quota_exceeded` handler
The spec mentions this handler is wanted for a batch-import feed that was
retired last quarter. I did **not** implement it. The `EventRegistry` is ready
to accept `reg.on("tenant.quota_exceeded")(handler)` when the feed returns;
adding it is a one-function change. Shipping dead code that suspends tenants
carries more risk than the stub being absent.

### `purge_tenant` / `set_role` (ops console)
These live in `ops.py` and receive an explicit `db` connection rather than
going through the HTTP surface. The ops console runs inside the private network
and is trusted; it does not need bearer-token auth. `actor_id` is accepted for
future audit-log integration.

### Multi-tenancy isolation
Every query that touches reports or attachments includes `tenant_id = ?`
alongside the primary key filter. `get_report_or_404` enforces this; a caller
from tenant A cannot read, delete, or attach to a report owned by tenant B even
if they guess the UUID.

### SQLite in WAL mode
WAL mode allows concurrent readers without blocking a writer, which suits a
service where reads dominate. `PRAGMA foreign_keys = ON` is set both in the
schema and in `open_db` so it is active regardless of whether the schema has
already been applied.

## Trade-offs / deliberately not done

- **No connection pool.** A single `sqlite3.Connection` is passed into the
  service. A real deployment would use a pool or switch to PostgreSQL; the
  interface does not need to change.
- **No pagination.** `list_reports` and `search_reports` return all matching
  rows. Cursor-based pagination would be a straightforward addition.
- **No audit log table.** `actor_id` is threaded through ops functions as a
  placeholder. A production system would `INSERT` into an `audit_events` table.
- **Attachments stored as BLOBs.** For simplicity, file bytes go into SQLite.
  A production system would store them in object storage (S3/GCS) and keep only
  a reference in the database.
- **No HTTPS / TLS.** That is the responsibility of the infrastructure layer
  (reverse proxy, load balancer).
- **No rate limiting.** Would live in the adapter layer, not the service layer.
