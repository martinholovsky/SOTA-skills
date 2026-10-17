# reportkit — Design Notes

## What was built

A multi-tenant report service implemented as a plain Python class (`ReportService`)
whose methods take and return dicts.  No web framework; the HTTP surface is the
class interface.  Persistence is SQLite via `sqlite3`.

---

## Decisions and trade-offs

### Transport enforcement (TLS / HSTS)
The service is a plain class, not an HTTP server.  TLS termination and HSTS
(`Strict-Transport-Security: max-age=63072000; includeSubDomains; preload`) must
be enforced at the reverse proxy / load balancer in front of this service.  This
is the standard split for a Python service behind nginx/Caddy/AWS ALB.  The
service itself cannot set response headers; the proxy layer must.

### Rate limiting
An in-process token-bucket limiter (`reportkit/rate_limit.py`) is included and
keyed on `user_id` per endpoint.  It is a defence-in-depth floor.  In a
multi-worker deployment, limits are per-process.  The production control should
be at the gateway (nginx `limit_req`, AWS API Gateway throttling, etc.).  The
in-process limiter is documented as secondary in `rate_limit.py`.

### Permission caching
Permissions are derived from the role on every request (no session-level cache).
The `resolve_principal` query joins `sessions → users → tenants` in one round
trip, so role changes made by the ops console take effect on the next request
without requiring a session invalidation.  This is the correct trade-off for a
service where roles are changed infrequently but correctness matters.

### Sort column injection
`search_reports` accepts a `sort` query parameter.  SQLite does not support
parameterised `ORDER BY`.  The value is mapped through `SORT_COLUMN_MAP` (a
hardcoded dict) and the resulting string — a literal from the dict, never user
input — is interpolated into the SQL.  A `KeyError` on an unknown key raises
`BadRequest`.  This is the standard allowlist-identifier pattern from rules/01 §2.

### LIKE metacharacter escaping
`validate_search_query` escapes `%`, `_`, and `\` in the search term before it
is used as a `LIKE` parameter.  The query uses `ESCAPE '\\'` so SQLite honours
the escapes.  This prevents a query of `%` from matching every row.

### Multi-tenant isolation
Every query that touches `reports` or `attachments` includes `tenant_id = ?`
bound to the value from the authenticated session, never from the request body.
The schema uses `REFERENCES tenants(id) ON DELETE CASCADE` as a structural
backstop.  Full Postgres RLS is not available in SQLite; the application-layer
filter is the boundary here.  A migration to Postgres should add RLS policies.

### Attachment storage
Attachments are stored with a server-generated UUID as the `storage_key`.  The
user-supplied filename is stored only as display metadata in the `attachments`
table.  No path is constructed from user input.  In a real deployment the
`storage_key` would be the object-storage key (S3/GCS); the actual bytes are not
persisted to disk in this implementation (the service records metadata only).

### Content scanning
`content_scan.py` checks magic bytes for a small set of known-bad signatures
(PE, ELF, Mach-O, shebang, ZIP).  This is a defence-in-depth layer.  A
production deployment should route attachments through a dedicated AV/malware
service (ClamAV, cloud-native scanning).  ZIP files are rejected conservatively
here; a real policy would allow them after deeper inspection.

### Billing webhook authentication
HMAC-SHA256 over `{timestamp}.{raw_body}` with a 5-minute replay window.
Verification happens **before** JSON parsing.  The secret comes from the
environment variable `BILLING_WEBHOOK_SECRET`.  Duplicate `event_id` values are
silently accepted (idempotent insert) to handle provider retries.

### `tenant.quota_exceeded` event handler
The batch-import feed that emits this event was retired in Q1 2025.  A stub
handler is registered so the event does not silently disappear if the feed is
reinstated.  The stub logs a warning.  The platform team should replace it with
real suspension logic when the feed returns.  See `reportkit/events.py`.

### Ops console functions
`purge_tenant` and `set_role` are plain functions, not HTTP endpoints.  They are
called by the internal ops console over the private network.  Input validation
and audit logging are applied regardless.  Network/mTLS authentication is the
responsibility of the ops console infrastructure.

### Audit log
Every mutating operation writes a row to `audit_log`.  The `detail` column is
JSON with no PII or secrets (scrubbed by `logging_utils._scrub`).

### Error responses
All error responses return a generic `{"error": code, "message": message}` body.
Driver error text is never forwarded to the caller (no oracle).  `404` is
returned for objects that exist in another tenant (no 403 vs 404 existence leak).

### Password / session hashing
Bearer tokens are stored as SHA-256 hashes.  Tokens are high-entropy
(`tok_{uuid4().hex}` in tests; production tokens should be ≥ 256-bit CSPRNG).
SHA-256 is appropriate for high-entropy tokens (no argon2 needed).

---

## Deliberately not done

- **HTTP server**: out of scope per the spec ("plain class whose methods take a
  request dict").
- **Actual file storage**: attachment bytes are not written to disk or object
  storage; only metadata is persisted.  The storage_key is the hook for a real
  implementation.
- **Password authentication**: the spec uses bearer tokens; no password hashing
  is needed here.
- **Email / notification**: no outbound messaging.
- **Pagination**: list and search endpoints return all matching rows.  A
  production service would add cursor-based pagination.
- **OpenAPI / schema**: no generated schema; the interface is the class methods.

---

## Non-negotiables cross-check (rules §5)

| Control | Status |
|---|---|
| Abuse control / rate limiting | In-process token bucket per user+endpoint; gateway layer noted as primary |
| Transport enforcement (TLS/HSTS) | Delegated to reverse proxy; documented above |
| Tests | 60+ assertions across auth, CRUD, webhook, ops, validation, rate limit, events, logging |
| Structured logging without secrets/PII | `logging_utils.py` with `_scrub`; JSON lines |
