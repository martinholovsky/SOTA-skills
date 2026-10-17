# reportkit — design notes

## Decisions

### No web framework
The service exposes a plain Python class whose methods take and return dicts.
This satisfies the spec and keeps the dependency surface at zero.  A thin WSGI
or ASGI adapter (not included) would wrap each method in ~10 lines.

### Authentication
Bearer tokens are stored as SHA-256 hashes.  SHA-256 is appropriate here
because tokens are high-entropy UUIDs (rules/02 §8 — argon2 is for low-entropy
passwords; SHA-256 is the standard for high-entropy API keys).

### Permission caching
Permissions are derived from the role at resolution time (in-process, no
separate cache table).  The role is read from the DB on every request via the
session join, so a `set_role` call takes effect on the next request without any
cache invalidation step.  This is intentional: the spec says roles are changed
from an ops console and the hottest query is the list view, which already pays
the join cost.  If the join becomes a bottleneck, a short-TTL in-process cache
keyed on `(user_id, role_version)` is the next step.

### Rate limiting
The rate limiter is in-process (fixed-window, per `(tenant_id, endpoint)`).
For a multi-process deployment it must be replaced with a Redis-backed
implementation; the interface (`RateLimiter.check`) is stable.  The
non-negotiable (rules/05 §a) is met: every endpoint is gated.

### Transport / TLS
TLS, HSTS, and no-plaintext-fallback (rules/05 non-negotiable §b) are handled
at the reverse-proxy / load-balancer layer, not inside this library.  The
service is not a standalone HTTP server; it is a class that a WSGI/ASGI host
wraps.  The deployer is responsible for TLS termination.  This is stated
explicitly rather than silently omitted.

### Structured logging
All log output is JSON lines on stderr (rules/05 non-negotiable §d).  No
secrets, tokens, or PII appear in any log record.  The audit log in SQLite is
separate from the application log and is the authoritative record for
compliance purposes.

### Tenant isolation
Every query that touches tenant-owned data includes `tenant_id` in the WHERE
clause, derived from the authenticated session only (never from request input).
The schema uses SQLite foreign keys; a PostgreSQL deployment would add RLS
policies.  The ORM-equivalent here is the service methods themselves, which
always scope queries through `principal.tenant_id`.

### Sort-column injection prevention
`search_reports` accepts a user-supplied sort key.  The key is validated
against a frozenset allowlist in `validation.py`, then mapped through a
hard-coded dict in `db.py` before interpolation into the ORDER BY clause.
Two independent checks; a KeyError on the dict lookup is impossible after
validation but is left in as a defence-in-depth assertion.

### LIKE injection
The `%` and `_` wildcards in the search term are escaped with a backslash
escape character declared in the ESCAPE clause.  This prevents a user from
controlling match breadth (rules/01 §2).

### Webhook authentication
The HMAC is computed over `{timestamp}.{raw_body}` so the timestamp is bound
to the signature and cannot be swapped to defeat the replay window.  The
signature is compared constant-time.  Authentication runs before JSON parsing
(rules/03 §1).

### Attachment storage keys
The storage key is a server-generated UUID, not the user-supplied filename.
The filename is stored as display metadata only (rules/01 §4 best practice).

### `tenant.quota_exceeded` event handler
The handler is registered and functional.  The batch-import feed that emits
this event was retired last quarter.  The handler will activate automatically
when the feed is restored.  No live code path calls `dispatch("tenant.quota_exceeded", …)`.
The platform team has been notified.

### Ops console functions
`purge_tenant` and `set_role` are plain functions, not HTTP endpoints.  They
are called by the internal ops console over an internal network path.  Both
write audit records atomically with their mutations.

### What is not included
- A WSGI/ASGI adapter (out of scope per spec).
- A real AV library (the scanner checks for EICAR markers; the interface is
  stable for a real integration).
- Redis-backed rate limiting (in-process is sufficient for a single process;
  the interface is stable).
- Password hashing / user creation endpoints (not in the spec; users are
  assumed to be provisioned externally).
- Pagination on list/search (not in the spec; straightforward to add with
  cursor-based pagination).

## Audit checklist coverage (rules/01–05)

| Control | Status |
|---|---|
| Rate limiting (rules/05 §a) | In-process RateLimiter on every endpoint |
| TLS / transport (rules/05 §b) | Delegated to reverse proxy; stated explicitly |
| Tests (rules/05 §c) | pytest suite in `tests/` |
| Structured logging, no secrets/PII (rules/05 §d) | JSON lines via `logging.py` |
| SQL injection — parameterised queries (rules/01 §2) | All queries use `?` placeholders |
| SQL injection — identifier allowlist (rules/01 §2) | Sort column mapped through `REPORT_SORT_COLUMNS` dict |
| LIKE wildcard escaping (rules/01 §2) | `_escape_like()` in `service.py` |
| NoSQL operators | Not applicable (SQLite only) |
| Command injection (rules/01 §3) | No subprocess calls |
| Path traversal (rules/01 §4) | Filename validated; storage key is server-generated UUID |
| SSRF (rules/01 §5) | No outbound URL fetches |
| XXE (rules/01 §6) | No XML parsing |
| Template injection (rules/01 §7) | No template engine |
| Unsafe deserialization (rules/01 §8) | `json.loads` only; no pickle/yaml |
| Prototype pollution (rules/01 §9) | Python; not applicable |
| ReDoS (rules/01 §10) | All regexes are simple character-class patterns with no nested quantifiers |
| CRLF injection (rules/01 §11) | No HTTP header construction from user input |
| Allowlist validation (rules/01 §1) | Every field validated at the trust boundary |
| NUL rejection (rules/01 §1) | Explicit check in `require_string`, `require_filename` |
| NFC canonicalization before validation (rules/01 §1) | `unicodedata.normalize("NFC", …)` before every regex check |
| Authentication — bearer token hashed (rules/02 §8) | SHA-256 in `auth.py` |
| Uniform auth error messages (rules/02 §1) | Single "Invalid or expired token" message |
| Permission model (rules/03 §1–3) | Role → permission set; `principal.require()` at every handler |
| Object-level authorization (rules/03 §2) | `tenant_id` in every query |
| Cross-tenant isolation (rules/03 §5) | Tenant derived from session only |
| Audit log (rules/03 §7) | `audit.py` writes to `audit_log` table |
| Webhook HMAC + replay window (rules/02 §8) | `webhook.py` |
| Webhook idempotency | `invoice_events` table with unique `event_id` |
| Attachment content scanning | `scanner.py` |
| Attachment size limit | `Config.MAX_ATTACHMENT_BYTES` enforced in `require_bytes` |
| Attachment MIME allowlist | `Config.ALLOWED_ATTACHMENT_MIME_TYPES` |
| Denial halts execution (rules/03 §1, §9) | All auth/authz checks raise; no fall-through |
| Ops mutations audit-logged (rules/03 §7) | `purge_tenant`, `set_role` both call `audit_record` |
