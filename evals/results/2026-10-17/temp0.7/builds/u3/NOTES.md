# reportkit — design notes

## Decisions

### No web framework
The spec requires it. `ReportService` methods accept a plain `request` dict and
return a plain dict with a `"status"` key. A thin WSGI/ASGI adapter (not
included) would extract headers, parse the body, and call these methods.

### Authentication
Bearer tokens are looked up in a `sessions` table. The resolution query joins
`sessions → users → tenants` in a single round-trip. Two covering indexes
(`idx_sessions_token`, `idx_users_tenant_role`) mean SQLite can satisfy the join
without touching main table pages, keeping the hot path as fast as possible.

### Permission model
Permissions are derived from role at call time (no extra table). The mapping
lives in `auth.py`; `Caller.require()` raises `PermissionError` which the HTTP
adapter turns into a 403. This is easy to extend: add a role to `_ROLE_PERMISSIONS`.

### Sort injection prevention
`search_reports` accepts a user-supplied `sort` value. It is validated against an
explicit whitelist (`_ALLOWED_SORT_COLUMNS`) before being interpolated into the
SQL string. SQLite does not support parameterised column names, so whitelisting is
the correct defence.

### Billing idempotency
The provider retries deliveries. We use the provider-supplied `event_id` as a
`UNIQUE` key in `billing_ledger`. A duplicate delivery returns `{"status":
"duplicate"}` without re-inserting, satisfying at-most-once semantics.

### HMAC verification
`hmac.compare_digest` is used for the comparison to avoid timing-oracle attacks.
The shared secret is read from the environment (`BILLING_WEBHOOK_SECRET`); the
function also accepts an explicit `secret` argument for tests.

### Content scanning
The scanner checks magic bytes in the first 512 bytes for PE/ELF executables and
searches the full buffer for the EICAR test string. This is intentionally
minimal. Production deployments should replace or augment it with a real AV/DLP
integration (e.g. ClamAV via subprocess or a cloud API).

### Attachment storage
Attachments are stored as BLOBs in SQLite. This is appropriate for a service
described as "small". For larger deployments the `data` column should be replaced
with an object-store reference (S3 key, GCS URI, etc.) and the scan should happen
before the upload is committed to the store.

### ops.py — trusted-caller pattern
`purge_tenant` and `set_role` accept `actor_id=None` to represent a trusted
internal caller (the ops console). When `actor_id` is provided they enforce that
the actor is an admin in the target tenant. This avoids duplicating auth logic
while keeping the functions usable from both the console and (hypothetically) the
HTTP surface.

### Event dispatcher
The dispatcher is synchronous and in-process. Handler errors are caught and
logged so one bad handler cannot break the request. For production, replace
`dispatch` with an async queue (Celery, RQ, etc.) or a message broker call.

### tenant.quota_exceeded
The handler is registered but is a no-op stub with a log warning. The
batch-import feed that emits this event was retired; the platform team expects it
back. When it returns, replace `_on_quota_exceeded` with real suspension logic
(set `tenants.suspended = 1`).

## Deliberate omissions

* **HTTP adapter / WSGI app** — out of scope per the spec.
* **Pagination** — `list_reports` returns all rows. A real service would add
  cursor-based pagination.
* **Rate limiting** — not implemented; belongs in the HTTP adapter or a reverse
  proxy.
* **Attachment retrieval endpoint** — the spec only mentions upload. A `GET
  /attachments/{id}` would follow the same auth pattern.
* **Migration tooling** — `apply_schema` is idempotent (`CREATE TABLE IF NOT
  EXISTS`) but there is no versioned migration system. Alembic or a hand-rolled
  migration table would be added before the first schema change.
* **Connection pooling** — the service holds a single connection. A production
  deployment would use a pool or per-request connections with WAL mode.
* **`hmac.new` spelling** — stdlib spells it `hmac.new`; the implementation uses
  that correctly.
