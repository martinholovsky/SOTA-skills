# 07 — API Security & Operations

Scope: authn scheme selection, request signing, rate limiting & quotas, bot
management, request limits, timeout budgets, CORS for APIs, audit logging,
multi-tenant isolation at the API layer, API response headers, API inventory.

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
- An API key identifies and meters a caller; it is not a whole access-control
  story. It is never the only guard on a sensitive or high-value resource (add
  OAuth scopes, mTLS or per-object authz), and it is revoked when the holder
  breaks the usage terms or abuses the API, not only when it leaks. HTTP Basic
  auth resends a reusable secret, only base64-encoded, on every call: avoid it,
  and where a legacy client forces it, serve it over TLS only (§8 on plaintext).
  OWASP: REST Security and Web Service Security cheat sheets.
- JWTs: validate `iss`, `aud`, `exp`, algorithm allowlist (no `alg:none`, no
  HS/RS confusion); access tokens ≤15–60 min; revocation story decided (short
  expiry + denylist for the rest).
- **Authn ≠ authz**: every handler authorizes object-level access
  (BOLA/IDOR — still the #1 API vulnerability class) and function-level access
  (admin routes). Centralize in middleware/policy, deny by default; a missing
  authz check should be a compile/lint/review failure, not a runtime surprise.
- Internal ≠ trusted: service-to-service calls also authenticate (mesh mTLS +
  workload identity). "It's behind the VPN" is an audit finding.
- **Sign the message, not only the channel, when one request moves money or
  authority or crosses several hops** (B2B writes, payment and settlement calls,
  agent/MCP JSON-RPC traffic): TLS ends at each proxy, a signature does not. This
  is the rules/06 §2 webhook model applied to requests. With HTTP Message
  Signatures (RFC 9421), the receiver requires a minimum covered set: `@method`,
  `@target-uri` (or `@authority` + `@path`), the tenant and audience fields,
  `created`/`expires`, and `content-digest`. RFC 9421 does not cover the body by
  itself (Section 7.2.8), so the sender adds an RFC 9530 `Content-Digest` and the
  receiver recomputes it over the bytes it actually received. A digest header
  that verifies but is never recomputed still allows the body to be swapped.
  Prefer asymmetric keys whose `keyid` maps to one registered sender, reject
  replays by nonce or `created` window (rules/06 §3), and fail closed when a
  signature is missing. Any field outside the covered set that can change an
  amount or an authorisation decision is a defect. OWASP: ASVS 5.0 V4.1.5; MCP
  Security, AI-Powered Advertising Systems Security, Bot Management and
  Anti-Automation, Multi Tenant Security cheat sheets.

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
- **Carve-out: credential, signup and other anti-automation surfaces** (login,
  token, password reset, OTP, gift-card or voucher checks). Answer an exceeded
  limit with a plain `429` and a generic body: no bucket name, no attempts
  remaining, and no `Retry-After` or `RateLimit` reset precise enough to schedule
  the next burst against. Precise counters on these routes let an attacker tune
  a credential-stuffing run to stay just under the threshold. OWASP: Bot
  Management and Anti-Automation cheat sheet.
- Tiered limits: per-endpoint-class (cheap reads vs expensive writes vs auth
  endpoints), per-plan, and a global per-principal ceiling. Expensive operations
  (search, export, GraphQL) cost more than 1 unit (cost-based limiting).
- **Quotas** are a separate layer: monthly/daily entitlements (billing), enforced
  eventually-consistent, distinct error message ("quota exhausted, resets
  2026-07-01 / upgrade") vs rate ("slow down, retry in 13s"). Don't conflate them.
- Server-side concurrency caps (max in-flight per principal) catch slow-request
  abuse that req/sec limits miss.
- **Key set and identity cost.** Beyond principal, IP and endpoint, key buckets
  on session and on ASN or geography where datacenter traffic is unexpected.
  Login uses two independent buckets, per account and per source, never one
  bucket on the `(ip, user)` pair, which lets one IP try every username. Cut a
  client's allocation automatically when its behaviour turns anomalous (a sudden
  spike, unusual target patterns), and restore it by policy, not by hand. A limit
  per identity is only as strong as the cost of a new identity: tie API and agent
  identities to a verified operator or account, so minting many keys does not
  multiply the allowance.
- **A per-route override that weakens the global limit is a finding.** Framework
  defaults are often empty: Django REST Framework's `DEFAULT_THROTTLE_CLASSES`
  is empty unless configured, and a view setting `throttle_classes = []` or
  `@throttle_classes([])` runs with no throttle. Every override needs a reason
  in review. OWASP: AML Sanctions AI Agent Payments, Bot Management and
  Anti-Automation, Django REST Framework cheat sheets.
- **Bot management is layered; rate limits are one layer.** Edge: IP and ASN
  reputation, TLS (JA3/JA4) and HTTP/2 fingerprints. Application: session-aware
  limits, honeypot fields and bait paths, challenges escalated by risk.
  Business: velocity rules, fraud scoring, review queues. A request can pass one
  layer and fail the next (ten checkouts in thirty seconds, each with a good IP
  and a solved challenge). Business flows enforce a minimum realistic interval
  between steps (a checkout or signup completed faster than a person could is
  rejected or stepped up). User-generated content goes through submitter
  reputation and delayed publishing. The aim is to raise attacker cost, not to
  block every bot: search crawlers, uptime monitors and accessibility tools
  must keep working, and responses are graduated (log, step up, tarpit, block)
  rather than all-or-nothing. Depth: `sota-code-security` rules/02 (signup) and
  rules/07 §2.1 (detection points). OWASP: ASVS 5.0 V2.4.2; Bot Management and
  Anti-Automation cheat sheet.

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

### 3a. HTTP message framing & request smuggling

Smuggling lives in the gap between two hops that disagree on where one request
ends and the next begins; the front hop's checks see one request, the back hop
runs two. Treat ambiguous framing as an attack, not as something to be lenient about.

- **HTTP/1.1**: a request carrying both `Transfer-Encoding` and `Content-Length`
  gets rejected (`400`) and the connection closed. RFC 9112 Section 6.1 permits
  processing it by `Transfer-Encoding` alone but requires the connection close
  either way, and its Section 6.3 says such a message "ought to be handled as an error". The
  same goes for a request whose `Transfer-Encoding` does not end in `chunked`, and
  for an invalid or self-contradicting `Content-Length` list (Section 6.3 makes
  both a `400`-and-close).
- **HTTP/2 and HTTP/3**: a message carrying a connection-specific field
  (`Transfer-Encoding`, `Connection`, `Keep-Alive`, `Upgrade`, `Proxy-Connection`;
  `TE` only as `trailers`) is malformed, and so is a `content-length` that differs
  from the sum of the DATA frame payloads (RFC 9113 Sections 8.1.1 and 8.2.2, RFC
  9114 Sections 4.1.2 and 4.2). An intermediary must not forward either. This matters most where
  an HTTP/2 edge **downgrades** to HTTP/1.1 towards the origin: a field that the
  binary framing carried harmlessly becomes framing again on the old wire (the
  CR/LF/NUL variant: `sota-code-security` rules/01 §11).
- **Generating**: never emit a `Content-Length` that disagrees with what the
  framing actually sends, and never both headers on one message (RFC 9112 Section 6.2).
  Hand-set length headers on a streamed or compressed body are the usual source.
- **One parser posture on every hop**: LB, CDN, WAF, gateway and app server must
  all be strict. A relaxed-parsing switch on any one of them reopens the gap,
  e.g. Node's `insecureHTTPParser: true` / `--insecure-http-parser` (whose docs
  list accepting both headers among its leniencies) or HAProxy's
  `option accept-unsafe-violations-in-http-request` (formerly
  `accept-invalid-http-request`, now deprecated). Prefer HTTP/2 end to end to an
  HTTP/1.1 backend link, and do not reuse a backend connection after a framing error.
- Audit by pairing hops, not by reading one config: list every hop's server and
  version, find where the protocol changes (h2 in front, h1 behind), and run a
  desync scanner against staging through the real edge. (Needs verification
  per stack: which exact inputs each proxy normalises differs by product and version.)

OWASP: ASVS 5.0 V4.2.1, V4.2.2, V4.2.3.

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
  rate-limit and quota trips, webhook endpoint changes. Also, often missed:
  service or API token creation with the **scopes/entitlements granted**; explicit
  logout (with a hash of the session ID, never the ID itself); file and upload
  deletion; data imports; creation and deletion of system-level objects
  (tenants, projects, API clients); receipt and processing of user-generated
  content and uploads; out-of-sequence steps in a multi-step flow and fraud
  signals. Event names: `sota-code-security` rules/07 §2.1.
- **High-risk operations write two entries**: an intent record before the action
  (who, what, which object, request ID) and an outcome record after it. An
  action that crashes, times out or is killed midway then still leaves a trace,
  and an intent with no outcome is itself an alertable signal. OWASP: Logging
  Vocabulary, Logging and REST Security cheat sheets.
- **WebSocket and other long-lived channels** (rules/05): the HTTP access log
  sees only the upgrade. Log connection open and close (user, IP, `Origin`),
  auth and authz decisions at the handshake and per message, rate-limit and
  message-validation violations, abnormal disconnects and protocol errors, never
  message bodies or tokens. OWASP: WebSocket Security cheat sheet.
- Every entry: timestamp, actor (principal + acting-on-behalf-of), tenant,
  action, object type+ID, outcome, source IP, user agent, **trace/request ID**
  correlating to ops logs. Plus the "where": application ID and version,
  hostname, protocol and port, request method and URI, region, and client port
  (behind NAT or CGNAT the source IP alone does not identify a client; RFC 6302
  recommends logging the source port with a traceable timestamp). Clocks on
  every node are time-synced and drift is alerted on, or events from two hosts
  cannot be ordered (`sota-observability` rules/01 §1). On sensitive and
  anti-automation endpoints, add ASN, country, TLS/HTTP2 fingerprint, a hashed
  session ID, and the bot or risk decision **with the signals behind it**
  (`bot_score`, rule name). An unlogged anti-bot decision cannot be tuned.
  Hash or truncate fingerprints before storage. OWASP: Logging Vocabulary and
  Bot Management and Anti-Automation cheat sheets.
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
- **A shared audit store is tenant data too.** Reads filter by the caller's
  tenant, taken from the credential. Reading across tenants needs a separate
  platform-auditor permission that no tenant admin role holds, and that access is
  itself audited. Writes take the tenant from the verified context: a tenant, or
  a service acting for one, cannot append entries to another tenant's stream,
  which would let it plant or bury evidence. OWASP: Multi Tenant Security cheat
  sheet.
- **Test it continuously**: automated suite that, for every endpoint, attempts
  access to tenant B's resources with tenant A's credentials and asserts 404 —
  the highest-ROI security test an API team can own.

## 8. Gateway placement & defense in depth

- Centralize cross-cutting controls at the gateway/edge (TLS termination, authn
  verification, rate limits, size limits, CORS, request-ID injection,
  WAF/bot rules); keep **authorization and tenant scoping in the service** —
  the gateway doesn't know your object model. The gateway may still do
  **coarse** authorisation as the first layer: route or scope checks such as
  "`POST /admin/*` needs `admin:write`" or "this client may call only these
  operations". That drops obviously unauthorised traffic early, but it adds to
  the service-level and object-owner checks and never replaces them. OWASP:
  Microservices Security cheat sheet.
- The gateway is one layer, not the boundary: services must reject unauthenticated
  traffic even from "inside" (a path that bypasses the gateway — internal port,
  mesh misconfig, SSRF pivot — must hit a second wall). Verify: call a service
  pod directly in staging without gateway headers; it must 401.
- Never trust gateway-injected identity headers (`X-User-Id`) unless the link
  is mTLS-pinned and the header is stripped from external requests at the edge
  — header-smuggling of identity is a recurring critical.
- **mTLS that ends at an LB or CDN stops being mTLS at that hop.** Behind it the
  service holds no certificate, only a forwarded client-certificate header, and
  RFC 8705 Section 6.5 explicitly leaves how that metadata travels safely out of scope.
  So the header gets the `X-User-Id` treatment above: honoured only on the link
  from the terminating proxy (itself authenticated), with any client-sent copy
  removed at the edge (the proxy-side settings: `sota-code-security` rules/04 §5).
  Where the caller's identity *is* the authorisation (payments, agent-initiated
  actions, B2B writes), do not let the header carry it alone: bind identity into
  the message, e.g. a sender-constrained token whose `cnf` thumbprint
  (RFC 8705 `x5t#S256`, or DPoP, RFC 9449) the service checks itself, or a signed
  request (HTTP Message Signatures, RFC 9421); or pass TLS through to the service.
  OWASP: AML Sanctions AI Agent Payments cheat sheet.
- TLS posture: TLS 1.2+ only, HSTS on API hosts, no plaintext listeners except
  health checks on loopback.
- **No transparent HTTP-to-HTTPS redirect on API endpoints.** Only hosts that
  people open in a browser redirect. An API host answers plaintext with an error
  (or does not listen on port 80). A client misconfigured to `http://` has
  already sent its token in cleartext, and a silent redirect makes it work, so
  nobody notices the leak. OWASP: ASVS 5.0 V4.1.2.
- **Defensive headers on JSON responses** a browser may fetch, as defence in
  depth: `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`
  (nothing in an API response should load, run or be framed),
  `Permissions-Policy` with empty allowlists (`camera=(), geolocation=()`…),
  `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`, and
  `Cache-Control: no-store` on sensitive data. This differs from HTML pages
  on purpose. A page links to other sites and needs `strict-origin-when-cross-origin`
  (the browser default per the W3C Referrer Policy spec) plus a real CSP. An API
  response should trigger no further requests, so it can refuse everything.
  Non-browser clients ignore these headers; they cost nothing. Page baseline:
  `sota-code-security` rules/05. OWASP: REST Security cheat sheet.

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

**API9 inventory, concretely.** Each API host has an inventory row with host,
version, environment (production, staging, test, development) and intended
audience (public, partner, internal), plus its auth, rate-limit and CORS posture.
To audit it, compare three lists: the endpoints and parameters the server code
routes (extract from routing code, OWASP Noir is one extractor), the published
spec, and the URLs that shipped client JS/HTML bundles reveal (LinkFinder and
jsluice are examples). An entry on one list and missing from another is an
undocumented or orphaned surface. Also check the server URLs a published
description advertises (OpenAPI `servers`, WSDL `soap:address`): each must be
intended and live, with no staging, localhost or private-range host.
OWASP: WSTG-APIT-01; Django REST Framework cheat sheet.

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
- [ ] **Framing (§3a) — HIGH**: every hop strict; a relaxed HTTP parser anywhere on the path is a finding:
      `grep -rnE 'insecureHTTPParser[[:space:]]*:[[:space:]]*true|--insecure-http-parser|accept-(invalid-http|unsafe-violations-in-http)-request' .`
      — then walk the hop chain for an h2-front/h1-back downgrade and for hand-set `Content-Length` on streamed bodies.
- [ ] **API keys and Basic auth (§1) — MEDIUM**: no high-value resource guarded by an API key alone; abuse leads to revocation; Basic auth absent or TLS-only. Locator:
      `grep -rnE 'Authorization:[[:space:]]*Basic|WWW-Authenticate:[[:space:]]*Basic|HTTPBasicAuth|BasicAuthentication' .`
- [ ] **Message signing (§1) — HIGH on money or authority paths**: high-value, B2B and agent requests signed with a receiver-enforced minimum covered set including `content-digest`, digest recomputed over received bytes. Verifiers that never mention the digest:
      `grep -rliE 'signature-input' . | while IFS= read -r f; do grep -qi 'content-digest' "$f" || echo "$f"; done`
- [ ] **Login-surface 429s (§2) — MEDIUM**: generic body, no bucket name, attempt count or precise reset on credential/signup/OTP routes:
      `grep -rniE 'remaining[_ -]?attempts|attempts[_ -]?(left|remaining)' .`
- [ ] **Throttle overrides (§2) — HIGH on auth or expensive routes**: a global default is configured and no view disables it:
      `grep -rnE 'throttle_classes[[:space:]]*=[[:space:]]*(\[[[:space:]]*\]|\([[:space:]]*\)|None)|@throttle_classes\([[:space:]]*(\[[[:space:]]*\]|\([[:space:]]*\))[[:space:]]*\)' --include='*.py' .`
- [ ] Rate-limit keys include session and ASN/geo where relevant; login uses separate per-account and per-source buckets; anomalous clients auto-downgraded; new identities cost a verified operator. Bot defence layered (edge, app, business), with minimum-realistic-interval checks on business flows and reputation plus delayed publishing for UGC — MEDIUM.
- [ ] Audit events (§6) include token issuance with scopes, logout (hashed session ref), file deletion, imports, system-object create/delete, UGC processing, sequence and fraud signals, and WebSocket open/close, decisions and violations; high-risk operations log intent before and outcome after — MEDIUM.
- [ ] Log records carry app ID, hostname, protocol/port, method/URI, region and client port; nodes time-synced with drift alerting; anti-bot decisions logged with their signals and hashed fingerprints — MEDIUM.
- [ ] **Shared audit store (§7) — HIGH**: reads tenant-filtered, cross-tenant reads need a platform-auditor permission no tenant admin has, and writes cannot target another tenant's stream. Audit-table reads with no tenant term on the line (a lead to read):
      `grep -rniE 'from[[:space:]]+audit_?(log|events?|trail)' . | grep -viE 'tenant'`
- [ ] Gateway does coarse route/scope authz as a first layer only; service-level and object checks still present (§8) — MEDIUM.
- [ ] **Plaintext on API hosts (§8) — MEDIUM**: `curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' http://<api-host>/<path>` returns an error or refuses the connection; a 301/302/307/308 to `https://` is the finding.
- [ ] JSON responses a browser can reach carry `default-src 'none'; frame-ancestors 'none'`, empty-allowlist `Permissions-Policy`, `Referrer-Policy: no-referrer`, `nosniff` (check with `curl -sI`) — LOW.
- [ ] **Inventory (§9) — MEDIUM**: every host has version, environment and audience; routed vs spec vs client-bundle endpoint lists reconciled; no stray published server URL:
      `grep -rnE 'url"?[[:space:]]*:[[:space:]]*"?https?://[^"[:space:]]*(staging|localhost|127\.0\.0\.1|internal|\.local[:/"]|10\.[0-9]+\.|192\.168\.)' --include='*.yaml' --include='*.yml' --include='*.json' .`
- [ ] **Forwarded client certificate (§8) — HIGH**: every read of a forwarded cert header is honoured only from the terminating proxy, stripped at the edge, and not the sole basis of an identity-authorised write. Locator:
      `grep -rniE 'forwarded-client-cert|ssl[-_]client[-_](cert|escaped)|client[-_]cert(ificate)?[-_]?header|x-client-cert' .`
