# 07 — API Security & Operations

Scope: authn scheme selection, rate limiting & quotas, request limits, timeout
budgets, CORS for APIs, audit logging, multi-tenant isolation at the API layer.

## 1. Authentication schemes — choosing

| Scheme | Use for | Notes |
|---|---|---|
| API keys | server-side partner/B2B access, simple integrations | bearer secrets: hash at rest, prefix for identification (`sk_live_…`), scoped, rotatable, never in URLs |
| OAuth2 client credentials | M2M where you want standard issuance, expiry, scopes, central revocation | short-lived JWT access tokens; the upgrade path from raw API keys |
| OAuth2 auth code + PKCE | acting on behalf of end users (third-party apps) | never password-grant; never implicit |
| mTLS | high-assurance B2B (finance/health), service mesh internal | strongest binding; cert lifecycle is the cost; pairs with OAuth (RFC 8705 cert-bound tokens) |
| Session cookies | first-party browser frontends | then CSRF defenses apply; don't mix with bearer on the same endpoints without thought |

Rules regardless of scheme:
- Credentials in the `Authorization` header (or mTLS), **never in query strings**
  (logs, referers, history).
- API keys: store only a hash (treat like passwords), display once, support
  ≥2 concurrent keys per principal for zero-downtime rotation, track `last_used_at`
  (enables dead-key cleanup and incident scoping), scope to least privilege
  (read-only vs write keys), expire or force-rotate stale keys.
- JWTs: validate `iss`, `aud`, `exp`, algorithm allowlist (no `alg:none`, no
  HS/RS confusion); access tokens ≤15–60 min; revocation story decided (short
  expiry + denylist for the rest).
- **Authn ≠ authz**: every handler authorizes object-level access
  (BOLA/IDOR — still the #1 API vulnerability class) and function-level access
  (admin routes). Centralize in middleware/policy, deny by default; a missing
  authz check should be a compile/lint/review failure, not a runtime surprise.
- Internal ≠ trusted: service-to-service calls also authenticate (mesh mTLS +
  workload identity). "It's behind the VPN" is an audit finding.

## 2. Rate limiting

- **Key by authenticated principal** (API key/account), not IP, for authed
  traffic — IPs are shared (NAT/CGNAT) and rotated by attackers. IP-based limits
  are the backstop for unauthenticated surfaces (login, signup, token endpoint).
- Algorithm: **sliding window counter** (or GCRA/token bucket) — fixed windows
  allow 2x bursts at boundaries; pure sliding logs are memory-heavy. Token bucket
  when you explicitly want burst allowances atop a sustained rate.
- Enforce in a shared store (Redis + atomic Lua / built into the gateway) —
  per-instance in-memory limits multiply by replica count and reset on deploy.
- Respond `429` with headers, both legacy and the IETF standard:

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 13
RateLimit-Policy: "default";q=100;w=60
RateLimit: "default";r=0;t=13          # IETF draft-ietf-httpapi-ratelimit-headers
Content-Type: application/problem+json

{"type":"https://api.example.com/errors/rate-limited","title":"Rate limited",
 "status":429,"detail":"Limit 100/min exceeded.","retry_after":13}
```

- Include limit headers on **successful** responses too — clients should
  self-throttle before hitting 429.
- Tiered limits: per-endpoint-class (cheap reads vs expensive writes vs auth
  endpoints), per-plan, and a global per-principal ceiling. Expensive operations
  (search, export, GraphQL) cost more than 1 unit (cost-based limiting).
- **Quotas** are a separate layer: monthly/daily entitlements (billing), enforced
  eventually-consistent, distinct error message ("quota exhausted, resets
  2026-07-01 / upgrade") vs rate ("slow down, retry in 13s"). Don't conflate them.
- Server-side concurrency caps (max in-flight per principal) catch slow-request
  abuse that req/sec limits miss.

## 3. Request size limits & input hygiene

- **Explicit max body size on every route** (gateway default e.g. 1 MB, raised
  per-route for uploads) → `413`. Also: max header size, max URL length, max
  query params, max multipart parts.
- JSON parsing limits: max depth, max keys/array length — deeply nested payloads
  are a CPU/stack DoS. Decompression limits (zip-bomb body with
  `Content-Encoding: gzip`): cap the *decompressed* size.
- Uploads: don't proxy large files through the API — issue pre-signed URLs to
  object storage; validate type by magic bytes not extension/Content-Type alone.
- Schema-validate all input at the boundary (the OpenAPI/proto schema from
  rules/01–04 is the enforcement artifact); reject unknown fields on writes
  (rules/02 §3).

## 4. Timeout budgets

Every request has an end-to-end budget; every hop fits inside it.

- Order matters: client timeout > LB timeout > app server timeout > downstream
  call timeouts (sum or max along the path) > DB statement timeout. An inner
  timeout exceeding an outer one means work continues after the caller is gone.
- Per-route, not global: `GET /users/{id}` 2s; `POST /reports` should be async
  (202 + status resource, rules/01 §3) rather than a 10-minute synchronous wait.
- Server-side: read/write/idle timeouts on the listener (slowloris), statement
  timeouts in the DB, **cancellation propagation** — client disconnect aborts
  downstream work (rules/04 §3).
- Retries (client or mesh) live *inside* the budget, idempotent routes only,
  backoff + jitter, with circuit breaking — otherwise retries amplify outages 3x.
- Return `504` (upstream) / `503 + Retry-After` (load shedding) honestly; do not
  hold connections open hoping.

## 5. CORS for APIs

- CORS is a **browser** mechanism: it doesn't protect the API (curl ignores it);
  it protects *users* from malicious origins riding their credentials. Server-side
  authz must never depend on it.
- Token-auth APIs for known frontends: explicit origin **allowlist** (exact
  origins from config), `Access-Control-Allow-Headers: Authorization,
  Content-Type`, only needed methods, `Access-Control-Max-Age: 600`+ to cut
  preflights.
- **Never** `Access-Control-Allow-Origin: *` with `Allow-Credentials: true`
  (spec forbids it — so libraries "helpfully" reflect the Origin header instead,
  which is *worse*: any site can ride cookies). Reflecting arbitrary origins with
  credentials is a critical finding.
- `*` without credentials is acceptable for genuinely public, unauthenticated,
  read-only APIs.
- Cookie-auth'd APIs additionally need CSRF defenses (`SameSite=Lax/Strict` +
  token or custom-header check) — CORS preflights don't cover
  form/simple-request CSRF.
- Don't blanket-expose headers; `Access-Control-Expose-Headers` only what clients
  read (e.g. `RateLimit`, `Sunset`, `Location`).

```text
# BAD (found in the wild constantly)
Access-Control-Allow-Origin: <echo of request Origin>   # reflection
Access-Control-Allow-Credentials: true                  # + credentials = any site rides cookies
Access-Control-Allow-Headers: *
Access-Control-Allow-Methods: *

# GOOD (token-auth SPA frontend)
Access-Control-Allow-Origin: https://app.example.com    # from explicit allowlist
Vary: Origin
Access-Control-Allow-Methods: GET, POST, PATCH, DELETE
Access-Control-Allow-Headers: Authorization, Content-Type, Idempotency-Key
Access-Control-Expose-Headers: RateLimit, Retry-After, Location
Access-Control-Max-Age: 7200
```

## 6. Audit logging

- Two streams, different lifecycles: **ops logs** (debugging, short retention)
  and the **audit trail** (security/compliance: append-only, long retention,
  integrity-protected, restricted read access).
- Audit-log these always: authn events (success/failure, key used), authz
  denials, all writes to sensitive resources (who/what/when/before-after or
  diff-ref), admin/break-glass actions, key/secret lifecycle, data exports,
  rate-limit and quota trips, webhook endpoint changes.
- Every entry: timestamp, actor (principal + acting-on-behalf-of), tenant,
  action, object type+ID, outcome, source IP, user agent, **trace/request ID**
  correlating to ops logs.
- **Never log**: credentials, bearer tokens, full API keys (log the key *prefix*),
  passwords, cookie values, full card/SSN data, raw request bodies of sensitive
  endpoints. Centralized redaction middleware, not per-handler discipline; test
  it (send a fake secret, grep the logs in CI/staging).
- Logs are an injection target: encode/escape user-controlled strings (CRLF/log
  forging); treat log viewers as XSS sinks.
- Request IDs: accept inbound `traceparent` (W3C Trace Context), generate if
  absent, return an ID header on every response (incl. errors — rules/01 §9), and
  propagate downstream.

## 7. Multi-tenant isolation at the API layer

Cross-tenant data leakage is the worst API bug class. Defense in depth:

- **Tenant from the credential, never the request**: derive tenant ID from the
  authenticated principal (token claim/key record). A `tenant_id` in the body or
  query is at most a *consistency check* against the credential — never the
  source of truth. (`X-Tenant-Id` headers trusted from clients = critical
  finding.)
- **Scope every query structurally**: tenant filter applied by a repository
  layer/ORM global scope or Postgres RLS (`SET app.tenant_id`; policies on every
  table) — not by remembering `WHERE tenant_id = ?` in each handler. RLS as a
  second enforcement layer catches the handler someone forgot.
- Resource IDs: lookups are always `(tenant_id, id)`; return `404` (not `403`)
  for other tenants' resources to avoid existence oracles — and make that
  consistent (a timing or message difference is still an oracle).
- Isolation applies to *everything*, not just primary GETs: list filters, search,
  exports, aggregations/counts, **webhooks** (events only to the owning tenant's
  endpoints), realtime channels (rules/05 — channel authz), idempotency-key
  scopes, ETag values, and cache keys (a shared cache without tenant in the key
  is a leak machine).
- Noisy-neighbor: rate limits and quotas per tenant (§2), per-tenant concurrency
  caps, fair-queuing on expensive shared resources.
- Cross-tenant admin/support access: separate audited surface with explicit
  on-behalf-of recording (§6) — not super-tenant credentials in the normal API.
- **Test it continuously**: automated suite that, for every endpoint, attempts
  access to tenant B's resources with tenant A's credentials and asserts 404 —
  the highest-ROI security test an API team can own.

## 8. Gateway placement & defense in depth

- Centralize cross-cutting controls at the gateway/edge (TLS termination, authn
  verification, rate limits, size limits, CORS, request-ID injection,
  WAF/bot rules); keep **authorization and tenant scoping in the service** —
  the gateway doesn't know your object model.
- The gateway is one layer, not the boundary: services must reject unauthenticated
  traffic even from "inside" (a path that bypasses the gateway — internal port,
  mesh misconfig, SSRF pivot — must hit a second wall). Verify: call a service
  pod directly in staging without gateway headers; it must 401.
- Never trust gateway-injected identity headers (`X-User-Id`) unless the link
  is mTLS-pinned and the header is stripped from external requests at the edge
  — header-smuggling of identity is a recurring critical.
- TLS posture: TLS 1.2+ only, HSTS on API hosts, no plaintext listeners except
  health checks on loopback.

## 9. OWASP API Security Top 10 mapping (2023 list, still canonical)

| OWASP | This skill |
|---|---|
| API1 Broken Object Level Auth | §1, §7 — credential-derived tenant, per-object checks, cross-tenant test suite |
| API2 Broken Authentication | §1 — scheme selection, JWT validation, key handling |
| API3 Object Property Level Auth | rules/01 §1 (explicit DTOs — no mass assignment/ORM dumps), §1 authz |
| API4 Unrestricted Resource Consumption | §2–4 — rate limits, quotas, size limits, timeout budgets; rules/03 §4 |
| API5 Broken Function Level Auth | §1 — deny-by-default policy, admin surface separation |
| API6 Unrestricted Access to Sensitive Business Flows | §2 cost-weighted limits + flow-specific throttles; **enforce multi-step flow order server-side** — model the flow as a state machine, validate the current state on every step, reject out-of-order/replayed steps (don't trust client sequencing). Business-logic depth: sota-code-security |
| API7 SSRF | rules/06 §8 — webhook/user-URL egress controls |
| API8 Security Misconfiguration | §5 CORS, §8 gateway/TLS; rules/03 §4 introspection |
| API9 Improper Inventory Management | rules/02 §5 — versioned, measured, sunset surfaces; spec-as-truth (rules/01 §10) |
| API10 Unsafe Consumption of APIs | rules/06 consumer role; rules/04 §3 deadlines on upstream calls |

Use this table to structure a security-focused audit report when the requester
wants OWASP-mapped findings.

## Audit checklist

- [ ] Auth scheme appropriate per consumer type; no credentials in query strings anywhere (grep logs/gateway config).
- [ ] API keys hashed at rest, prefixed, scoped, dual-key rotation supported, `last_used_at` tracked.
- [ ] JWT validation complete (iss/aud/exp/alg allowlist); access tokens short-lived; revocation story exists.
- [ ] Object-level (BOLA) and function-level authz on every handler, deny-by-default middleware/policy — sample 5 endpoints incl. one obscure one.
- [ ] Internal services mutually authenticated (mTLS/workload identity); no network-position trust.
- [ ] Rate limiting keyed per principal, sliding-window/GCRA in shared store; 429 + `Retry-After` + RateLimit headers; limits visible on successes; unauth endpoints (login/token) IP-limited.
- [ ] Quotas separate from rate limits with distinct errors; expensive ops cost-weighted; per-principal concurrency caps.
- [ ] Body/header/URL/multipart size limits explicit per route (413); JSON depth/key caps; decompressed-size caps; uploads via pre-signed URLs.
- [ ] Timeout hierarchy verified outer>inner end-to-end (client→LB→app→downstream→DB statement); long work is async 202, not long synchronous holds.
- [ ] Retries idempotent-only, budget-bounded, jittered, circuit-broken.
- [ ] CORS: explicit origin allowlist; no origin reflection with credentials; no `*`+credentials; cookie APIs have CSRF defenses; preflight cache set.
- [ ] Append-only audit trail covering authn, authz denials, sensitive writes, admin actions, exports — with actor/tenant/object/outcome/trace ID.
- [ ] No secrets/tokens/PII in logs (verified by test, not policy); log output encoded against CRLF/log injection.
- [ ] Trace/request ID on every response and propagated downstream (W3C Trace Context).
- [ ] Tenant derived from credential only; structural scoping (repo layer or RLS) — not per-handler WHERE clauses; cross-tenant probes return consistent 404.
- [ ] Tenant isolation covers search, exports, counts, webhooks, realtime channels, idempotency keys, and cache keys.
- [ ] Automated cross-tenant access test suite exists and runs in CI.
- [ ] Services reject direct (gateway-bypassing) traffic; identity headers from the gateway are mTLS-bound and stripped from external requests at the edge.
- [ ] TLS 1.2+ everywhere, HSTS on API hosts; no plaintext listeners beyond loopback health checks.
