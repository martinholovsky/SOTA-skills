# reportkit — Design Notes

## Decisions

### No web framework
The service exposes a plain Python class whose methods accept and return dicts.
Transport concerns (parsing HTTP, TLS, routing) belong to the caller's layer.
This is intentional per the spec.

### Standard library only
`sqlite3`, `hashlib`, `hmac`, `secrets`, `unicodedata`, `re`, `json`, `logging`.
No third-party dependencies.

### Authentication
Bearer tokens are high-entropy (≥ 32 URL-safe base64 chars).  SHA-256 is used
to hash them at rest — no KDF needed because the tokens are already
high-entropy (unlike passwords).  Passwords are out of scope for this service;
if added they would require argon2id.

### Permission cache
`resolve_session` re-reads the role from the DB on every call (the JOIN is
fast), then caches the derived permission set for 30 seconds per user_id.  The
cache is invalidated immediately by `ops.set_role`.  The 30-second TTL means a
role revocation takes effect within half a minute on the hot list path without
a DB round-trip on every request.  For immediate revocation requirements, lower
the TTL or remove the cache.

### SQL identifier injection (sort column)
Sort column names cannot be parameterized in SQL.  `validate_sort_col` maps the
user-supplied string through a hardcoded allowlist dict; any value not in the
dict raises `ValidationError` before the query is built.  The mapped value (e.g.
`r.created_at`) is a string literal from the allowlist, not user input.

### LIKE metacharacter escaping
`%` and `_` in search terms are escaped with `\` before being passed as a SQL
parameter.  Parameterization alone does not prevent a bare `%` from matching
every row.

### Tenant isolation
Every query that touches report data filters on `tenant_id` derived from the
authenticated session, never from request input.  The ownership check is part
of the SQL WHERE clause (not a fetch-then-check), so a cross-tenant ID returns
404 rather than 403, avoiding existence leakage.

### Attachment storage keys
The `storage_key` column is a server-generated 128-bit random hex string.  The
user-supplied filename is stored only in `original_name` (display metadata) and
is never used as a filesystem path.  Path traversal characters in filenames are
rejected by the validator as a defence-in-depth measure even though the filename
is never used as a path.

### Content scanner
`scanner.py` checks for the EICAR test string and a configurable list of byte
signatures.  In production this would call an AV/DLP service (ClamAV, cloud
scanning API).  The interface is synchronous and returns a bool so it can be
swapped without changing the handler.

### Billing webhook idempotency
The `billing_events` table uses the provider's event `id` as the primary key.
A duplicate delivery (provider retry) is detected by a SELECT before INSERT and
returns 200 without writing a second row.  HMAC verification runs before any
body parsing.

### `tenant.quota_exceeded` event
The event name constant is declared in `events.py`.  No handler is registered
because the batch-import feed that emits it was retired last quarter.  The
registry is ready: when the feed returns, the platform team registers a handler
with `events.register(EVENT_QUOTA_EXCEEDED, suspend_tenant_handler)` without
touching the dispatcher.

### Ops console functions
`purge_tenant` and `set_role` are plain functions, not HTTP endpoints.  They
are called by the internal ops console, which is responsible for its own
authentication (SSO + MFA + step-up) and network restriction.  Both write
audit records.

### Rate limiting
Application-level rate limiting is implemented in `rate_limit.py` using a
fixed-window counter per minute stored in SQLite.  Two scopes:
- `api` — 120 requests/minute per authenticated user_id.
- `webhook` — 60 requests/minute per remote IP.

If a gateway (nginx, AWS API Gateway, Cloudflare) provides rate limiting, the
application-level control is defence in depth.  Both should be present.

### TLS / transport
TLS and HSTS are enforced at the transport/reverse-proxy layer (nginx, AWS ALB,
etc.).  The service class has no socket-level code; it receives already-parsed
request dicts.  The operator must configure TLS termination with HSTS
(`max-age=63072000; includeSubDomains`) before exposing the service.

### Structured logging
All log output is JSON (see `logging_cfg.py`).  Fields containing PII or
secrets are never logged:
- Bearer tokens: never logged, not even hashed.
- User IDs: logged as opaque identifiers only.
- Tenant IDs: logged as opaque identifiers only.
- Report titles: logged only as lengths (`title_len`).
- Request bodies: never logged.
- Attachment data: never logged.

### No plaintext passwords / secrets in config
The webhook secret is passed as `bytes` to `ReportService.__init__`, sourced
from the environment at startup.  It is never logged.

## Deliberate omissions / trade-offs

- **No HTTP transport layer**: the spec says "plain class whose methods take a
  request dict".  A real deployment would wrap this in a WSGI/ASGI adapter.
- **No password hashing**: users are authenticated via pre-issued bearer tokens;
  the password storage rules (argon2id) apply if a login endpoint is added.
- **No pagination**: list/search endpoints return all matching rows.  In
  production, add `LIMIT`/`OFFSET` or cursor-based pagination.
- **SQLite only**: suitable for single-process deployment.  For multi-process or
  multi-host, replace with PostgreSQL + Row-Level Security policies.
- **In-process permission cache**: not shared across processes.  For
  multi-process deployments, use Redis or accept the DB round-trip on every
  request.
- **Scanner is a stub**: real deployments must integrate a proper AV/DLP service.
- **No MFA / passkeys**: out of scope for this service layer.
- **No email verification / OAuth**: out of scope.
- **Attachment data is not persisted to disk or object storage**: the handler
  records metadata only.  A real implementation would write `data` to a
  storage backend (S3, GCS) using the `storage_key` as the object key.

## Audit checklist results (rules/01 §audit)

- ✅ SQL queries parameterized; sort column mapped through allowlist dict.
- ✅ No shell invocations.
- ✅ Filenames validated; never used as filesystem paths; storage keys are server-generated UUIDs.
- ✅ No URL fetching in this service.
- ✅ No XML parsing.
- ✅ No template rendering.
- ✅ No pickle/ObjectInputStream/yaml.load.
- ✅ No deep-merge of request data into objects.
- ✅ No regexes on unbounded untrusted input; all patterns use `fullmatch` with bounded quantifiers.
- ✅ Validation is allowlist-based, server-side, after NFC canonicalization, with length limits.
- ✅ No header construction from user input.
- ✅ LIKE metacharacters escaped in search terms.
- ✅ NUL bytes rejected in every field.

## Audit checklist results (rules/02 §audit)

- ✅ Bearer tokens are high-entropy; stored as SHA-256 hashes.
- ✅ Session expiry enforced in the DB query.
- ✅ No hand-rolled token schemes.
- ✅ Webhook HMAC verified constant-time over raw body.
- ✅ No default credentials in code.

## Audit checklist results (rules/03 §audit)

- ✅ Single default-deny enforcement: `require_permission` must be called before any data access; missing call = no access.
- ✅ Every object lookup includes `tenant_id` predicate in the query.
- ✅ Roles come from the DB session join, never from request bodies.
- ✅ `purge_tenant` and `set_role` write audit records.
- ✅ Denial halts: every `AuthError` / `ValidationError` handler returns immediately (all paths use `return _err(...)`).
- ✅ Cross-tenant IDs return 404, not 403.

## Non-negotiables status (operating principle 5)

(a) **Rate limiting**: implemented in `rate_limit.py`, applied on every service
    method and on the webhook endpoint.  Gateway-level rate limiting is
    recommended as an additional layer.

(b) **Transport / TLS**: enforced at the reverse-proxy layer.  The service class
    has no socket code.  Operator must configure TLS + HSTS.

(c) **Tests**: `tests/` covers auth, validation, CRUD, attachments, webhook
    HMAC/idempotency, rate limiting, events, audit, and ops functions.

(d) **Structured logging without secrets/PII**: `logging_cfg.py` emits JSON;
    no tokens, passwords, titles, or bodies are logged.
