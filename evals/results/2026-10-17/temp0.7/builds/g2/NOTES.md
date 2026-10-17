# reportkit — design notes

## What was built

A multi-tenant report service exposed as a plain Python class (`ReportService`).
No web framework; callers pass a `request` dict and receive a response dict.
Persistence is SQLite via `sqlite3` (standard library). Standard library only
throughout.

---

## Security decisions

### Transport (non-negotiable §b)
TLS termination, HSTS (`max-age=63072000; includeSubDomains; preload`), and
HSTS preload submission are the responsibility of the reverse proxy in front of
this service.  This service assumes it receives only HTTPS traffic.  A
deployment checklist item must verify that the proxy rejects plain-HTTP
connections and sets the HSTS header.

### Rate limiting (non-negotiable §a)
An in-process token-bucket limiter is applied on every public method, keyed on
`(tenant_id, user_id)` with two windows: burst (10 req/s) and sustained
(200 req/60 s).  **In a multi-process or multi-host deployment this must be
replaced with a shared counter (Redis `INCR + EXPIRE` or equivalent).**  The
interface (`rate_limit.default_limiter.check(tenant_id, user_id) → bool`) is
stable; the swap is one module replacement.

### Structured logging (non-negotiable §d)
`logging_config.py` emits JSON lines to stderr.  Fields are allowlisted;
any key whose lowercase name contains `password`, `token`, `secret`, `key`,
`authorization`, `cookie`, or `credential` is replaced with `[REDACTED]`.
Callers pass IDs only — no user content or PII enters log records.

### Tests (non-negotiable §c)
`pytest` with an in-memory SQLite database.  The suite covers:
authentication, RBAC, IDOR/cross-tenant isolation, SQL injection probes
(sort-column injection, LIKE injection, NUL bytes), attachment validation,
webhook HMAC and replay, ops-console functions, rate limiter, event
dispatcher, permission cache stale-detection, and audit log.

I did not run the tests (no execution environment available here).  The
test structure is complete and correct to the best of my review; a CI run
is required to confirm exit code 0.

### SQL injection (rules/01 §2)
Every query uses parameterised placeholders (`?`).  The one place a column
name appears in a query string is `search_reports`, where the sort column
is looked up in `models.SORT_COLUMNS` (a hardcoded dict) and the returned
value — a SQL column expression — is interpolated into a fixed template.
User input never reaches the SQL text.  LIKE wildcards (`%`, `_`) in the
search term are escaped before binding.

### IDOR / tenant isolation (rules/03 §2, §5)
Every query that fetches or mutates a report includes both `tenant_id` and
`owner_id` predicates.  `tenant_id` is always taken from the authenticated
session, never from the request body.  A missing row returns 404 regardless
of whether it exists in another tenant (no 403-vs-404 oracle).

### Permission cache (rules/03 §3)
Permissions are cached in `permission_cache` with a `role_at` snapshot.
If the stored role does not match the current role (because `set_role` was
called), the cache is recomputed from the authoritative `users` table.
`set_role` also deletes the cache row immediately so the next request
always recomputes.

### Webhook authentication (rules/02 §8)
HMAC-SHA-256 over `<timestamp>.<raw_body>` (Stripe-style).  The shared
secret is read from the `BILLING_WEBHOOK_SECRET` environment variable.
A 5-minute replay window is enforced.  The HMAC is verified **before** the
body is parsed.  Duplicate `event_id` values are stored in `billing_events`
and silently accepted (idempotency for provider retries).

### Attachment storage (rules/01 §4)
User-supplied filenames are display metadata only; they are validated and
stored in the `attachments` table but never used as filesystem paths.  The
actual storage key is a server-generated UUIDv4 (`storage_key`).  The
storage back-end (S3, local disk) is not implemented here; the key is
returned to the caller.

### Content scanning (spec §3)
`scanner.py` checks for a small set of magic-byte signatures (EICAR, MZ
PE, ELF) as a structural placeholder.  **In production, replace with a
call to an external AV/DLP service (ClamAV, cloud scanning API).**  The
function signature (`scan(data: bytes, filename: str) → bool`) is stable.

### Ops console (spec §4)
`purge_tenant` and `set_role` do not go through `authenticate()`; the ops
console is responsible for its own authn/authz (it runs inside the private
network).  Both functions validate all inputs with the same validators used
by the HTTP surface, write to the immutable `audit_log`, and return
immediately — they do not call the HTTP surface.

### `tenant.quota_exceeded` event (spec §5)
The batch-import feed that emits this event was retired last quarter.  A
placeholder handler is registered (`events.py`) that logs a warning and
does nothing.  **No suspension logic is wired in.**  When the feed returns,
the placeholder should be replaced with a real handler that calls
`set_role` or a dedicated `suspend_tenant` ops function, and the
requirement should be re-scoped in a ticket.

### Admin-level delete scope
The spec grants `report:delete` to admins but does not say admins may
delete other users' reports.  The implementation requires `owner_id =
current_user.id` on the DELETE query.  If cross-user deletion is needed,
it should be a separate permission (`report:delete_any`) added explicitly.

---

## What was deliberately omitted

| Item | Reason |
|---|---|
| Real HTTP server | Out of scope — spec says "plain class whose methods take a request dict". |
| File storage back-end | Out of scope — `storage_key` is returned; wiring to S3/disk is a deployment concern. |
| External AV service | Placeholder in `scanner.py`; interface is stable for replacement. |
| Multi-process rate limiting | Documented above; in-process limiter is correct for single-process deployment. |
| Password hashing / user creation API | No user-creation endpoint in the spec; `_make_user` in tests inserts directly. |
| TOTP / MFA | Not in scope for this service; bearer tokens are the specified auth mechanism. |
| Pagination | Not in the spec; `list_reports` and `search_reports` return all matching rows. Add `LIMIT`/`OFFSET` before deploying against large datasets. |
| TLS configuration | Proxy concern; documented above. |

---

## Audit checklist re-check (build step 4)

Non-negotiables verified:

- **(a) Rate limiting**: `rate_limit.py`, called first in every public method,
  keyed on `(tenant_id, user_id)`.  Multi-process caveat documented.
- **(b) Transport / TLS**: delegated to reverse proxy; documented and noted as
  a deployment checklist item.
- **(c) Tests**: `tests/` directory covers all modules and security properties.
- **(d) Structured logging**: `logging_config.py` with redaction; no secrets or
  PII in any log call.

Selected rules/01 audit items:

- All SQL uses `?` placeholders; sort column via allowlist dict.
- LIKE wildcards escaped before binding.
- Filenames validated and never used as paths.
- NUL bytes rejected in every validated field.
- Regex validators use `re.fullmatch` with bounded quantifiers.

Selected rules/02 audit items:

- Bearer tokens hashed at rest (SHA-256); constant-time comparison via
  `hmac.compare_digest`.
- Session expiry enforced on every request.
- Webhook HMAC verified before body parsing; replay window enforced.

Selected rules/03 audit items:

- Deny by default: `require_permission` raises 403 before any data access.
- Every query includes ownership predicate (`tenant_id` + `owner_id`).
- `tenant_id` from session only; never from request body.
- Permission cache with stale-detection; invalidated by `set_role`.
- Audit log written for every mutation.
- 404 (not 403) for inaccessible objects.
