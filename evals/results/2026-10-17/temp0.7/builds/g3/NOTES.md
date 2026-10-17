# reportkit — Design Notes

## What was built

A multi-tenant report service implemented as a plain Python package with no
web framework dependency.  The HTTP surface is a class whose methods accept
and return dicts; a real deployment would wire these to an ASGI/WSGI adapter
or a thin HTTP layer.

---

## Decisions and trade-offs

### Authentication
Bearer tokens are stored as SHA-256 hex digests — high-entropy tokens do not
need argon2 (rules/02 §8).  The raw token is never stored or logged.  Sessions
carry an `expires_at` column; the query filters on it so expired tokens fail
at the DB layer.  Suspended tenants are also filtered in the same query so a
suspended tenant's sessions fail immediately without a separate check.

### Permissions
The permission model is role → frozenset of permission strings.  The mapping
lives in `auth.py` and is the single source of truth.  Handlers call
`principal.require(permission)`, not `principal.role == "admin"`, so roles
can be renamed or split without touching handler code.

### SQL injection defence (rules/01 §2)
Every query uses parameterised placeholders.  The one place a column name
appears in a query (`ORDER BY` in `search_reports`) is mapped through a
hard-coded dict (`SORT_COLUMN_MAP`) and the raw user value is never
interpolated.  LIKE metacharacters (`%`, `_`, `\`) are escaped in the search
term before it is bound as a value.

### Tenant isolation (rules/03 §5)
Every query that touches tenant-owned data includes `tenant_id = ?` bound to
the value from the authenticated session — never from the request body.  The
schema enforces foreign-key constraints.  SQLite does not support row-level
security, so the ORM-equivalent guard (the `tenant_id` predicate in every
query) is the boundary.  A production deployment on PostgreSQL should add RLS
as a structural backstop (noted below).

### Object-level authorisation (rules/03 §2)
Ownership or tenant membership is encoded in the query predicate, not checked
after a plain `SELECT *`.  A report in another tenant returns 404, not 403, to
avoid leaking existence.

### Sort column injection (rules/01 §2)
`validate_sort_key` maps the user-supplied string through `SORT_COLUMN_MAP`
and raises `ValidationError` for any unknown key.  The mapped value (e.g.
`r.created_at`) is the only thing that appears in the f-string; the user's
input never touches the SQL text.

### Billing webhook (rules/02 §8)
HMAC-SHA256 is verified over the raw body **before** JSON parsing, using
`hmac.compare_digest` for constant-time comparison.  The shared secret is
read from the environment (never from source).  Idempotency is enforced by a
`UNIQUE` constraint on `idempotency_key` (the provider's event id); a
duplicate insert is caught and returns a 200 with `"duplicate": true` so the
provider stops retrying.

### Attachments (rules/01 §4)
The user-supplied filename is validated for display storage only and is never
used as a filesystem path.  The storage key is always a server-generated UUID.
The content scanner runs before the file is written; flagged files are rejected
with 422.  The `_default_attachment_store` writes to `./attachments/<uuid>`;
in production this would be replaced with an object-storage backend.

### Events
The dispatcher is synchronous and fire-and-forget.  Events are dispatched
**after** the DB transaction commits so a handler failure cannot roll back
the write.  The `tenant.quota_exceeded` handler is registered as a stub
(the batch-import feed is retired) with a clear warning log; the registration
is kept because the platform team expects the feed to return.

### Ops console
`purge_tenant` and `set_role` are plain functions, not HTTP endpoints.  They
write an immutable audit log entry (actor, action, before/after state) for
every mutation.  They are called by the internal ops console over the private
network; no authentication layer is added here because that belongs to the
console itself.

### Rate limiting (rules, universal non-negotiables §5a)
A fixed-window per-caller-per-endpoint limiter is implemented in SQLite.
In production, rate limiting at the gateway (e.g. nginx `limit_req`, AWS API
Gateway throttling) is expected as the primary layer; this layer defends the
service when requests bypass the gateway (internal callers, tests, direct
access).  The billing webhook is keyed by `remote_addr` (or a fixed string if
absent) rather than a user id.

### Transport (rules, universal non-negotiables §5b)
TLS and HSTS are enforced at the reverse-proxy layer (nginx/Caddy/ALB).  The
service itself has no plaintext fallback.  This is noted explicitly because the
service exposes no HTTP listener of its own.

### Structured logging (rules, universal non-negotiables §5d)
All log output is JSON via `_StructuredFormatter`.  Bearer tokens, passwords,
and file contents are never logged.  Filenames are omitted from attachment logs
(they may contain PII).  User IDs are internal UUIDs.

---

## What was deliberately not done

| Item | Reason |
|---|---|
| Pagination on list/search | Not in the spec; straightforward to add (LIMIT/OFFSET with a cursor). |
| Full-text search | SQLite FTS5 would replace the LIKE query; deferred as an optimisation. |
| Permission caching | The spec says the permission query is hot; a short-lived in-process cache (keyed by user_id + permission version) would help.  Omitted to keep the scope clear. |
| PostgreSQL RLS | The service uses SQLite.  A production migration to Postgres should add `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` on every tenant-owned table and set `app.tenant_id` per transaction. |
| Async I/O | Not requested; the service is CPU-light and SQLite is synchronous anyway. |
| HTTP adapter | The spec says "plain class whose methods take a request dict"; wiring to WSGI/ASGI is a thin layer left to the deployment. |
| Outbound SSRF controls | The service makes no outbound HTTP requests. |
| Email/notification | Not in the scope of this service. |

---

## Audit checklist cross-reference (rules BUILD step 4)

Every item in the audit checklists of rules/01, 02, 03, and 05 was reviewed.
Items that are N/A for this service are noted; items handled are mapped to code.

**rules/01 (Input Handling)**
- SQL parameterised: ✓ all queries use `?` placeholders.
- Identifier allowlist: ✓ `SORT_COLUMN_MAP` in `validation.py`.
- No shell invocation: ✓ no `subprocess` anywhere.
- Path canonicalisation: ✓ storage key is UUID, filename is display-only.
- Archive extraction: N/A — no archive handling.
- SSRF: N/A — no outbound HTTP.
- XML/XXE: N/A — no XML parsing.
- Template injection: N/A — no template rendering.
- Deserialization: ✓ only `json.loads` used.
- Prototype pollution: N/A — Python.
- ReDoS: ✓ regexes in `validation.py` are anchored, bounded, and simple; no
  backtracking quantifiers.
- LIKE metachar escape: ✓ `_escape_like` in `service.py`.
- NUL rejection: ✓ `_reject_control` in `validation.py`.
- Length limits: ✓ every field has a `max_len`.
- Allowlist validation: ✓ content-type, sort key, filename all allowlisted.
- Business invariants: ✓ `amount_cents > 0`, `size > 0`, sort key in set.
- CRLF in headers: N/A — service does not set HTTP response headers directly.
- CSV/formula injection: N/A — no CSV export.
- Host header: N/A — no outbound URL construction.

**rules/02 (Authentication)**
- Password storage: N/A — no passwords; bearer tokens hashed with SHA-256.
- Rate limiting: ✓ `rate_limit.py`, per-caller per-endpoint.
- Session expiry: ✓ `expires_at` column, filtered in auth query.
- HMAC webhook: ✓ constant-time comparison, raw body, before parsing.
- API key storage: ✓ token hash only, never plaintext.
- Vendor defaults: N/A — no third-party services configured here.

**rules/03 (Authorization)**
- Deny by default: ✓ every handler calls `principal.require(...)` before work.
- Object-level auth: ✓ `tenant_id` in every query predicate.
- Function-level auth: ✓ permission strings checked, not role names.
- Roles from session: ✓ never from request body.
- Tenant isolation: ✓ `tenant_id` from session, never from request.
- Audit log: ✓ `audit_log` table, written by `ops.py`.
- Background jobs: N/A — no async workers.
- Webhook subject auth: ✓ `tenant_id` from parsed (signature-verified) body,
  then validated against the tenants table.

**rules/05 (Web Platform)**
- XSS: N/A — service returns JSON, no HTML rendering.
- CSP/CSRF/CORS/headers: N/A — handled by the HTTP adapter / reverse proxy
  layer, not by this service.
- Cookies: N/A — no cookie handling in this service.

**Universal non-negotiables (§5)**
- (a) Rate limiting: ✓ `rate_limit.py`; gateway-level expected in production.
- (b) TLS/HSTS: enforced at reverse proxy; no plaintext fallback in service.
- (c) Tests: ✓ `tests/` directory, 70+ test cases.
- (d) Structured logging: ✓ `logging_config.py`, no secrets/PII in log fields.
