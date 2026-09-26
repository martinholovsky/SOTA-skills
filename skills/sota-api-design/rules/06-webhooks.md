# 06 — Webhooks

Scope: both roles — **provider** (you deliver webhooks to user-supplied URLs) and
**consumer** (you receive them). Signing, replay protection, retries, ordering,
idempotent consumption, SSRF defense.

## 1. Payload & contract design

- Webhook = event notification, same schema discipline as the API: versioned event
  types (`invoice.paid`), documented JSON schema, additive evolution (rules/02).
- Envelope every event:

```json
{
  "id": "evt_01HZX4K7",            // globally unique — consumer dedupe key
  "type": "invoice.paid",
  "created_at": "2026-06-12T09:30:00Z",
  "api_version": "2026-06-01",
  "data": { "object": { ... } }
}
```

- **Thin vs fat payloads**: fat (full object) is convenient but delivers stale
  state out of order and leaks data through the consumer's logs/infra. **Thin
  payloads (ID + type, consumer fetches current state via API)** are the safer
  default for sensitive domains and neutralize most ordering pain (§5). Offer fat
  payloads only where the fetch round-trip genuinely hurts.
- Never put secrets/PII you wouldn't put in an email into a fat payload — you do
  not control the receiving infrastructure.
- Let users subscribe per event type; don't firehose everything to every endpoint.

## 2. Signing — HMAC with timestamp

Unsigned webhooks are unauthenticated POSTs from the internet; any auditor flags
them instantly.

**Provider:**
- Sign `id + "." + timestamp + "." + raw_body` with HMAC-SHA256 using a per-endpoint
  secret (the Standard Webhooks signed-content format). Send id + timestamp +
  signature in headers. The **Standard Webhooks** spec is the 2026 convention —
  adopt it instead of inventing:

```http
POST /hooks/billing HTTP/1.1
webhook-id: evt_01HZX4K7
webhook-timestamp: 1781256600
webhook-signature: v1,K5oZfzN95Z9UVu1EsfQmfVNQhnkZ2pj9o9NDN/H/pI4=
```

- Sign the **raw bytes** you send. Include the timestamp **inside** the signed
  string (binds it — attacker can't re-send old body with fresh timestamp).
- Version-prefix signatures (`v1,`) and support **multiple signatures per
  delivery** — that's what makes zero-downtime secret rotation possible (sign with
  old+new during overlap; consumers verify against any of their stored secrets).
- Per-endpoint secrets (one compromised consumer ≠ all), shown once at creation,
  rotatable via API/dashboard.
- mTLS or OAuth-to-consumer are heavier alternatives for enterprise consumers;
  HMAC remains the baseline everyone must have.

**Consumer verification — the order matters:**
1. Read the **raw body bytes** (before any JSON parsing/middleware re-serialization
   — re-serialized JSON ≠ signed bytes; the most common "signature randomly fails"
   bug).
2. Check timestamp within tolerance (±5 min) → otherwise reject (replay window).
3. Compute HMAC, compare with **constant-time comparison** (`hmac.compare_digest`,
   `crypto.timingSafeEqual`) — `==` on signatures is a timing-oracle finding.
4. Only then parse and process.
- Also verify the event is *for you* (right endpoint/tenant) if the provider
  multiplexes.

Reference consumer verification (Python; pattern is language-agnostic):

```python
# BAD — three findings in four lines
body = request.json()                              # parsed before verification
expected = hmac_sha256(secret, json.dumps(body))   # re-serialized != signed bytes
if request.headers["X-Sig"] == expected: ...       # timing-unsafe ==; no timestamp check

# GOOD
raw = request.raw_body()                                   # exact bytes
ts = int(request.headers["webhook-timestamp"])
if abs(time.time() - ts) > 300: raise Reject(400)          # replay window
msg = f"{request.headers['webhook-id']}.{ts}.".encode() + raw
for secret in active_secrets:                              # rotation: try all
    digest = hmac.new(secret, msg, hashlib.sha256).digest()
    for sig in parse_v1_signatures(request.headers["webhook-signature"]):
        if hmac.compare_digest(digest, sig):               # constant-time
            return process(json.loads(raw))
raise Reject(401)
```

## 3. Replay protection

Signature alone doesn't stop re-delivery of a *validly signed* old request
(captured by a proxy, leaked from logs).

- Timestamp tolerance (§2) bounds the window.
- Within the window: **dedupe on `webhook-id`/event `id`** — store processed IDs
  with TTL ≥ tolerance window (and ideally ≥ provider's max retry horizon);
  reject/no-op duplicates. This doubles as idempotency (§4) — one mechanism, two
  jobs.
- Providers: never reuse event IDs, even across retries of the same event
  (same id on retry — that's the point), and rotate-don't-share secrets.
- **Prove the rejections in CI, not only the happy path.** The receiver's tests
  send (a) a forged callback (wrong secret, or one flipped body byte), (b) a
  correctly signed but stale one outside the tolerance, (c) a duplicate event ID
  inside the window, and (d) a callback validly signed for endpoint or tenant A
  replayed to endpoint B. Each must be rejected, and the test asserts that no
  payload field was read or acted on (no handler call, no row written).
  Verification that silently stopped enforcing (a refactor that skips it on a
  parse error, a test-mode flag left on) otherwise shows up only in production.
  OWASP: AI-Powered Advertising Systems Security cheat sheet.

## 4. Delivery, retries & idempotent consumers

**Provider:**
- Deliveries come from a **queue with persistent state**, never inline in the
  request path that generated the event (use outbox pattern: event row committed
  in the same transaction as the domain change, dispatcher drains it — otherwise
  you emit webhooks for rolled-back transactions or drop events on crash).
- Success = any 2xx within a short timeout (5–10s total, no following redirects —
  §8). Everything else (timeout, 4xx except 410, 5xx) ⇒ retry with **exponential
  backoff + jitter** over hours-to-days (e.g. 1m, 5m, 30m, 2h, 5h, 10h, 24h…
  ~3 days like Stripe).
- `410 Gone` from consumer ⇒ auto-disable the endpoint. Persistent failures
  (e.g. >95% over 3 days) ⇒ disable + notify the owner. Track per-endpoint health.
- Expose to consumers: delivery logs, manual redelivery button/API, and a
  **reconciliation API** (`GET /events?after=...`) so consumers can backfill
  gaps — webhooks are at-least-once-ish, never guaranteed; the events API is the
  source of truth.
- Don't let one dead endpoint block others: per-endpoint queues/concurrency
  isolation.

**Consumer:**
- **Ack fast, process async**: verify signature → enqueue → return `2xx` in
  <1s. Doing real work inline ⇒ provider timeout ⇒ retry storm ⇒ duplicate
  processing of slow work. Return 5xx only when you failed to durably enqueue.
- **Idempotency is mandatory** — retries guarantee duplicates. Dedupe on event
  `id` (unique constraint in DB beats best-effort cache), and make handlers safe
  to re-run anyway (upserts, state-machine guards).
- Don't trust webhook *content* for money-moving decisions when thin-fetch is
  available: signature proves origin, but fetching current state by ID closes
  staleness/ordering gaps.

Provider dispatch architecture (reference shape):

```text
domain tx ──commit──> outbox row
outbox poller ──> event store (immutable events, powers GET /events)
             └─> per-endpoint delivery queues ──> sender workers
                                                  | resolve->validate IP->pin->POST
                                                  | record attempt (status, latency)
                                                  └─ on failure: schedule retry (backoff+jitter)
```

- The event store is canonical; delivery attempts reference it. Redelivery and
  reconciliation read from it — never regenerate payloads from live data (the
  object may have changed; signatures/audits must match what was sent).
- Sender workers are stateless and horizontally scalable; per-endpoint
  concurrency = 1..N with ordering *not* guaranteed (and documented as such, §5).
- Emit provider-side metrics per endpoint: success rate, P95 delivery latency,
  retry depth, disabled-endpoint count — this is your consumer-health dashboard.

## 5. Ordering caveats

**Webhooks are unordered. Period.** Retries, parallel dispatchers, and network
races mean `invoice.paid` can arrive before `invoice.created`. Providers should
not promise ordering (per-key serial delivery throttles throughput to the slowest
consumer and still breaks on retry).

Consumer strategies:
- Treat events as triggers, **fetch current state** by ID (thin-payload mindset)
  — ordering becomes irrelevant.
- Or compare `created_at`/sequence in the event against last-applied state and
  drop stale updates (last-writer-wins per object).
- Or buffer out-of-order events briefly (park `*.paid` until `*.created` is seen,
  with a timeout that falls back to fetching).
- Never build a state machine that errors on out-of-order arrivals — that's a
  design bug, not a provider bug.

## 6. Consumer-side endpoint hygiene

- Dedicated route, **no session/cookie auth required** but signature verification
  enforced; reject unsigned/badly signed with `401`, don't reveal verification
  details in error bodies.
- Enforce body size limit before reading fully; `415` non-JSON; rate-limit per
  source as backstop.
- Log every delivery (id, type, signature result, latency, outcome) — disputes
  with providers are settled with logs.
- Secrets in a secret manager, per provider, rotated when staff leave; support
  two active secrets to absorb provider rotation (§2).

## 7. Webhooks vs alternatives — when not to webhook

- Consumer needs *every* event, in order, with replay → give them an **events
  API to poll** (`GET /events?after=evt_x`, cursor-paginated) or a streaming
  channel; webhooks alone are a notification optimization on top of that, not a
  reliable transport.
- Very high volume to one consumer (>~100/s sustained) → batch events per
  delivery, or switch to a queue/stream integration (consumer-owned SQS/Kafka
  topic, Event Grid). Per-event HTTP POSTs don't scale linearly forever.
- Consumer is inside your own estate → use the message bus directly; webhooks
  through the public internet between your own services is an architecture smell.
- Zapier-style fan-in platforms: support thin payloads + reconciliation API and
  they'll integrate fine; don't build platform-specific hacks.

## 8. SSRF — provider delivering to user-supplied URLs

A webhook sender is **an HTTP client that attackers point anywhere** ("give me
your cloud metadata, please"). Egress controls are non-negotiable:

- **Validate at registration AND at every send** (DNS changes between the two —
  rebinding): resolve the hostname, reject private/reserved ranges —
  `10/8, 172.16/12, 192.168/16, 127/8, 169.254/16` (cloud metadata!), `::1`,
  `fc00::/7`, `fe80::/10`, and IPv4-mapped IPv6 forms.
- **Pin the resolved IP for the actual connection** (resolve→check→connect to
  that IP with Host/SNI set) — checking then re-resolving is a TOCTOU rebinding
  hole.
- **Don't follow redirects** (or re-validate every hop — simpler: don't). A public
  URL 302→`http://169.254.169.254/` is the classic bypass.
- HTTPS-only endpoints (allow plain HTTP at most for explicit dev mode); modest
  timeouts; cap response bytes read (you only need the status); never include
  response bodies from consumer endpoints in your logs/UI unsanitized.
- Best: dispatch from an **isolated egress** (dedicated VPC/proxy with deny-all
  to internal ranges) so a validation bug still hits a wall.
- Prove ownership before sending real data to a new URL (challenge token echo /
  verification event) — stops using your webhook system to spam/probe third
  parties.
- Per-tenant send rate limits — your webhook sender must not be rentable DDoS
  infrastructure.

## Audit checklist

**Provider role:**
- [ ] HMAC-SHA256 over `id.timestamp.raw_body` (message id included), versioned scheme, per-endpoint secrets, multi-signature rotation support (Standard Webhooks-compatible preferred).
- [ ] Outbox/queue-backed dispatch (no inline sends, no events from rolled-back transactions); per-endpoint isolation so one dead consumer can't starve others.
- [ ] Exponential backoff + jitter retries over days; 410 auto-disables; failing endpoints disabled with owner notification.
- [ ] Delivery logs, manual redelivery, and an events reconciliation API exposed to consumers.
- [ ] Event IDs unique and stable across retries; no ordering promised in docs.
- [ ] SSRF defenses: private/metadata IP ranges blocked with resolve-pin-connect (no TOCTOU), redirects not followed, HTTPS-only, response size cap, isolated egress, URL ownership verification, per-tenant send rate limits.
- [ ] No secrets/excess PII in payloads; thin payloads for sensitive domains; per-event-type subscriptions.

**Consumer role:**
- [ ] Signature verified on raw bytes before parsing; constant-time comparison; timestamp tolerance enforced (±5 min).
- [ ] Dedupe on event ID with durable store (TTL ≥ retry horizon); handlers idempotent (unique constraints/upserts), out-of-order-safe.
- [ ] **Negative signature tests (§3) — MEDIUM**: CI proves forged, stale, duplicate and cross-endpoint callbacks are rejected before any payload field is used. Webhook test files with none of those cases (a lead to read):
      `grep -rliE 'webhook' --include='*test*' --include='*spec*' . | while IFS= read -r f; do grep -qiE 'invalid[_ -]?sig|bad[_ -]?sig|forged|tamper|stale|expired|replay' "$f" || echo "$f"; done`
- [ ] Ack-fast/process-async: 2xx only after durable enqueue, well under provider timeout.
- [ ] State derived by fetching current object where staleness matters, not from fat payload alone.
- [ ] Endpoint has body size limits, no cookie-auth dependency, full delivery logging; secrets in a manager with dual-secret rotation support.
