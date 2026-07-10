# 01 — REST/HTTP API Design

Scope: resource modeling, method/status semantics, pagination, filtering, partial
responses, idempotency, conditional requests, hypermedia, error format, spec-first
workflow, contract testing.

## 1. Resource modeling

- Model **nouns, not verbs**. URLs identify resources; methods supply the verb.
  - Bad: `POST /createUser`, `POST /users/123/activate-account-now`
  - Good: `POST /users`, `POST /users/123/activations` (action reified as a sub-resource)
- When an operation genuinely isn't CRUD (search with a huge body, batch mutation,
  state transition), reify it as a resource: `POST /searches`, `POST /transfers`,
  `POST /orders/{id}/cancellations`. This gives the operation an ID, a status, and
  auditability for free.
- For pure reads that merely outgrow the URL, the **QUERY method** (RFC 10008, 2026)
  is the standards-track alternative — safe, idempotent, cacheable — where your
  proxies/gateways/frameworks support it; `POST /searches` stays the compatibility fallback.
- Use plural nouns consistently (`/users`, `/users/{id}`). Never mix `/user/{id}`
  and `/users`.
- Limit nesting to **two levels** (`/orgs/{org}/projects/{id}`). Deeper nesting bakes
  hierarchy into clients; prefer top-level collections with filters:
  `/comments?post_id=42` over `/posts/42/threads/7/comments/9`.
- IDs: opaque, non-enumerable (ULID/UUIDv7 or prefixed IDs like `cus_01H...`).
  Sequential integer IDs leak volume and invite IDOR scanning. Prefixed IDs
  (Stripe-style) make logs and support tickets self-describing.
- Resource representation = stable contract, not a DB row dump. Never serialize ORM
  entities directly; map through an explicit response type so schema migrations don't
  silently change the API.

## 2. HTTP method semantics

| Method | Safe | Idempotent | Use |
|---|---|---|---|
| GET | yes | yes | Read. Never mutate on GET — caches/prefetchers will trigger it. |
| HEAD | yes | yes | Metadata/existence checks. |
| QUERY | yes | yes | Safe read with a request body (RFC 10008, 2026); responses cacheable. Searches/filters too large for a URL. Ecosystem support is early — fall back to `POST /searches` (§1) where proxies/frameworks lack it. |
| PUT | no | yes | Full replace at a client-chosen or known URL. |
| PATCH | no | **no** (unless designed so) | Partial update. Prefer JSON Merge Patch (RFC 7396) for simple cases; JSON Patch (RFC 6902) when array surgery is needed. |
| POST | no | no | Create under a collection; non-idempotent actions. Pair with idempotency keys (§6). |
| DELETE | no | yes | Delete. Repeat DELETE returns 404 or 204 — both acceptable; pick one and document it. |

- `PUT` with client-generated IDs (`PUT /documents/{uuid}`) gives you idempotent
  create-or-replace for free — often better than `POST` + idempotency key.
- Don't tunnel everything through POST "because firewalls". If a gateway blocks
  PATCH, use `POST` + `X-HTTP-Method-Override` only as a documented escape hatch.
- **Per-route method allowlist** (OWASP REST): each route permits an explicit set
  of methods and returns `405` for the rest — don't let the framework expose
  `PUT`/`DELETE`/`TRACE` on a read-only route by default. Re-check authorization
  **per method**, not just per path (a user allowed to `GET` an order is not
  thereby allowed to `DELETE` it).

## 3. Status codes — the ones that matter

- `200` body returned; `201` + `Location` header on create; `202` accepted for async
  work (return a status resource URL); `204` success, no body.
- `400` malformed request (syntax, types); `422` well-formed but semantically invalid
  (validation). Pick one convention and hold it — many shops use `400` for both;
  fine, but never both interchangeably.
- `401` not authenticated (missing/bad credentials, send `WWW-Authenticate`);
  `403` authenticated but not allowed. Returning `404` instead of `403` is a valid
  **deliberate** choice to hide resource existence across tenants — document it.
- `404` not found; `409` state conflict (duplicate, version clash); `410` gone
  permanently (deprecated endpoint after sunset).
- `412` precondition failed (ETag mismatch); `428` precondition required (you demand
  `If-Match` and it's missing).
- `429` rate limited + `Retry-After`; `413` body too large; `415` wrong content type
  (request); `406` when you can't satisfy the client's `Accept` (response negotiation).
- **Content negotiation hygiene** (OWASP REST): validate `Content-Type` on writes,
  honour `Accept` for the response and `406` when unsupported — but **never reflect
  the client's `Accept` value into the response `Content-Type`** (a path to XSS /
  content sniffing). Serve JSON as `application/json`, never `application/javascript`.
- `500` your bug; `502/503/504` upstream/overload/timeout. **Never** return `200`
  with `{"error": ...}` in the body — it breaks retries, monitoring, caching, and
  every generic client.

```http
POST /users HTTP/1.1            HTTP/1.1 201 Created
Content-Type: application/json  Location: /users/usr_01HZX4
                                Content-Type: application/json
{"email":"a@b.co"}              {"id":"usr_01HZX4","email":"a@b.co"}
```

## 4. Pagination — cursor over offset

- **Offset pagination (`?page=3&per_page=50`) is broken at scale**: O(n) skip cost in
  the DB, and rows shift under the client when items are inserted/deleted mid-scan
  (skipped or duplicated records). Acceptable only for small, admin-facing,
  rarely-changing datasets.
- **Cursor (keyset) pagination is the default.** Cursor encodes the position
  (e.g., `(created_at, id)` of last item), opaque and signed/encoded:

```http
GET /orders?limit=50&cursor=eyJpZCI6Im9yZF8wMUha...
HTTP/1.1 200 OK
{
  "data": [...],
  "next_cursor": "eyJpZCI6...",   // null when exhausted
  "has_more": true
}
```

- Cursor rules: opaque (base64 of internal position — clients must not parse it),
  short-lived validity is fine, must tolerate the anchor row being deleted (seek
  semantics: `WHERE (created_at, id) < (?, ?)`), and **must embed the sort/filter**
  or reject cursors used with different query params.
- Always enforce a server-side `limit` max (e.g., 100). Reject or clamp larger values
  — document which.
- Return total counts only when cheap and genuinely needed; `COUNT(*)` on large
  tables is a self-DoS. Offer `?include_total=true` as opt-in, or an estimate.
- Stable sort always requires a unique tiebreaker (`ORDER BY created_at, id`).

## 5. Filtering, sorting, partial responses

- Filtering: flat query params for the common case (`?status=active&customer_id=...`).
  For richer needs adopt one convention and document it: bracketed operators
  (`?created_at[gte]=2026-01-01`) or a defined mini-language. Never accept raw query
  expressions you interpolate into SQL.
- Filter/search payloads too large for a URL: QUERY (RFC 10008) where supported,
  else reified `POST /searches` (§1).
- Validate every filter/sort field against an **allowlist**. `?sort=password_hash`
  or sorting on an unindexed column is an availability bug.
- Sorting: `?sort=-created_at,name` (leading `-` = desc). Multi-field allowed, all
  fields allowlisted and indexed.
- Partial responses: `?fields=id,email,profile.name` (sparse fieldsets) for large
  resources; saves bandwidth and discourages clients from coupling to fields they
  don't need. Define behavior for unknown fields (ignore or 400 — pick one).
- Expansion: `?expand=customer,items.product` to inline related resources instead of
  forcing N+1 client round-trips. Cap expansion depth.

## 6. Idempotency keys for unsafe operations

POST that creates a payment/order/email must be safely retryable — networks fail
after the server commits.

```http
POST /payments HTTP/1.1
Idempotency-Key: 6c1f6c1e-9c5a-4f7e-b2f3-1d2a3b4c5d6e
{"amount": 5000, "currency": "EUR"}
```

Server contract (Stripe semantics; the IETF `draft-ietf-httpapi-idempotency-key-header`
captured the same convention but expired without becoming an RFC):
- Key + endpoint + auth principal scope the dedupe record.
- First request: store key + request hash **before** executing; execute; store the
  response; return it.
- Retry with same key + same body: replay the **stored response** (same status, body).
- Same key + **different body**: `422`/`409` — never execute.
- Concurrent duplicate while first is in flight: `409` (or block) — never run twice.
- Keys expire (24h typical). Persist in the same transaction as the side effect or
  use an outbox; a Redis-only record that can vanish independently of the DB write
  is a false guarantee.

## 7. Conditional requests (ETags) and concurrency

- Emit `ETag` on single-resource GETs. Strong ETags from a version column or content
  hash; `Last-Modified` as a coarse fallback.
- Reads: `If-None-Match` → `304 Not Modified` (bandwidth + cache validation).
- Writes (optimistic concurrency — prevents lost updates):

```http
PUT /articles/42                 HTTP/1.1 412 Precondition Failed
If-Match: "v17"                  (someone wrote v18 meanwhile)
```

- For resources where lost updates are costly, **require** `If-Match` and return
  `428 Precondition Required` when absent.
- Cache headers are part of the design: `Cache-Control: private, max-age=0,
  must-revalidate` for per-user data; explicit `no-store` for sensitive payloads;
  `public, max-age=...` only for genuinely shared data. Unstated caching = whatever
  intermediaries feel like.

## 8. HATEOAS — pragmatic dose

Full HATEOAS (clients discover all transitions from hypermedia) rarely pays off for
machine clients with generated SDKs. The pragmatic subset that does:
- `Location` on 201/202.
- Pagination links (`next_cursor` or RFC 8288 `Link` headers).
- Status/affordance hints on workflow resources:
  `{"status":"pending_approval","actions":["approve","reject"]}` — clients render
  capabilities without hardcoding the state machine.
- Absolute or root-relative URLs in link fields; never make clients string-build URLs
  from IDs when you can hand them the URL.
Skip generic `_links` envelopes (HAL/Siren) unless your clients actually walk them.

## 9. Error format — RFC 9457 (problem+json)

One error shape across the whole API. RFC 9457 (obsoletes 7807) is the standard:

```http
HTTP/1.1 422 Unprocessable Content
Content-Type: application/problem+json
{
  "type": "https://api.example.com/errors/validation",
  "title": "Validation failed",
  "status": 422,
  "detail": "2 fields failed validation.",
  "instance": "/payments/req_01HZX4",
  "errors": [
    {"pointer": "/amount", "code": "min", "message": "must be >= 100"},
    {"pointer": "/currency", "code": "unsupported", "message": "JPY not supported"}
  ],
  "trace_id": "a1b2c3d4e5f6"
}
```

- `type` is a stable machine-readable identifier (URI; need not resolve). Clients
  branch on `type`/`code`, never on `detail` text.
- Extend with custom members (`errors`, `trace_id`, `retry_after`) — the RFC allows it.
- Include a correlation/trace ID in every error for support.
- **Never leak internals**: no stack traces, SQL, file paths, or dependency versions
  in any environment reachable by clients. 500s get a generic body + trace ID.
- Validation errors: report **all** failures in one response, not first-failure.

## 10. OpenAPI-first vs code-first; contract testing

- **Spec-first (OpenAPI 3.1+)** is the default for public/partner APIs: the spec is
  the contract, reviewed like code, before implementation. Enables parallel
  client/server work, generated SDKs, mock servers, and breaking-change detection in
  CI (e.g., `oasdiff`). OpenAPI 3.2 (released Sep 2025) is a non-breaking superset of
  3.1 adding first-class streaming (SSE/JSON-Lines via `itemSchema`), hierarchical
  tags, and custom HTTP methods; adopt it when tooling supports it. (4.0 "Moonwalk"
  is still in design — not a target.)
- **Code-first with generated spec** is acceptable for internal APIs *iff* the
  generated spec is committed, diffed in CI, and breaking diffs fail the build. A
  spec nobody diffs is documentation, not a contract.
- Either way, non-negotiable: the served API and the spec **must not drift**.
  Validate requests/responses against the schema in test (or runtime middleware in
  staging).
- Contract testing: schema validation of real responses in CI at minimum;
  consumer-driven contracts (Pact) when you control both sides and have many
  consumers; record real consumer expectations, verify provider against them in the
  provider's pipeline.
- OpenAPI hygiene: every operation has `operationId`, every response (incl. errors)
  schematized, `additionalProperties` intent explicit, enums marked extensible where
  evolution is expected (see rules/02), auth schemes declared in `securitySchemes`.

## 11. Async operations (202 pattern)

Anything that can exceed a few seconds (report generation, bulk import, video
transcode) must not hold a synchronous connection.

```http
POST /reports HTTP/1.1                  HTTP/1.1 202 Accepted
{"type":"annual","year":2025}           Location: /operations/op_01HZX9
                                        {"id":"op_01HZX9","status":"pending"}

GET /operations/op_01HZX9               HTTP/1.1 200 OK
                                        {"id":"op_01HZX9","status":"succeeded",
                                         "result_url":"/reports/rep_42",
                                         "created_at":"...","finished_at":"..."}
```

- Operation resource carries: `status` (`pending|running|succeeded|failed`),
  result link on success, problem+json-shaped `error` on failure, timestamps,
  and percentage/progress where meaningful.
- Clients poll with backoff; offer `Retry-After` on the operation GET, and/or a
  webhook (rules/06) for completion. Operations are listable per principal and
  retained long enough for slow pollers (≥24h).
- The initial POST still takes an Idempotency-Key (§6) — duplicate submissions
  must return the same operation, not start a second job.

## 12. Bulk and batch endpoints

- Prefer many small idempotent requests over bespoke batch endpoints; HTTP/2
  multiplexing removes most of the round-trip motivation.
- When batch is justified (mobile constraints, atomic multi-item writes): cap
  batch size, define atomicity explicitly (all-or-nothing vs per-item), and for
  per-item semantics return `207`-style per-item results — each entry carrying
  its own status + problem details, in input order:

```json
{"results":[
  {"status":201,"id":"usr_1"},
  {"status":422,"error":{"type":".../validation","detail":"email taken"}}
]}
```

- Never report overall `200` while hiding per-item failures the client can't
  detect without parsing prose.

## 13. Misc non-negotiables

- JSON: UTF-8, ISO 8601 / RFC 3339 timestamps **with offset** (`2026-06-12T09:30:00Z`),
  never epoch-seconds-as-float. Money as integer minor units or string decimal —
  never IEEE 754 floats.
- Field naming: pick `snake_case` or `camelCase` once, enforce with lint.
- Booleans over flag-strings; enums as strings, not magic ints.
- Nulls vs absent fields mean different things in PATCH — define it (Merge Patch:
  `null` deletes).
- Request size limit, response compression (`gzip`/`br`), and a per-request timeout
  budget exist on every endpoint (details: rules/07).

## Audit checklist

- [ ] URLs are nouns; no verbs except reified action sub-resources; consistent plural casing.
- [ ] No GET/HEAD endpoint mutates state.
- [ ] Status codes semantically correct; no `200 {"error":...}` anti-pattern anywhere.
- [ ] 201 responses include `Location`; async operations return 202 + status resource.
- [ ] Collection endpoints use cursor pagination with opaque cursors, enforced max limit, stable sort with unique tiebreaker.
- [ ] No unbounded `COUNT(*)`/total on large collections by default.
- [ ] Filter/sort fields allowlisted; sorts hit indexes; no raw query-language injection path.
- [ ] Every non-idempotent unsafe operation (payments, orders, sends) supports idempotency keys with stored-response replay and same-key-different-body rejection.
- [ ] Concurrent duplicate idempotency-key requests cannot double-execute (locking/unique constraint verified).
- [ ] ETags emitted; mutating endpoints on contended resources honor `If-Match`/412.
- [ ] Cache-Control explicitly set; sensitive responses `no-store`.
- [ ] Errors are RFC 9457 problem+json, single shape API-wide, machine-readable `type`/`code`, all validation errors batched, trace ID present.
- [ ] No stack traces / SQL / internal paths in any client-visible error.
- [ ] IDs opaque and non-enumerable; no sequential integers exposed.
- [ ] Resources mapped through explicit DTOs, not raw ORM serialization.
- [ ] OpenAPI spec exists, is in CI, breaking-change diff fails the build, and matches the served API (spot-check 3 endpoints).
- [ ] Timestamps RFC 3339 with timezone; money not floats.
