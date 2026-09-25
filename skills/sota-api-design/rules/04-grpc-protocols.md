# 04 — gRPC, Protobuf Evolution & Protocol Choice

Scope: proto evolution rules, deadlines/cancellation, streaming patterns, errors,
gRPC-Web/Connect, load balancing, and the REST vs GraphQL vs gRPC decision.

## 1. Choosing the protocol

| Criterion | REST/HTTP+JSON | GraphQL | gRPC |
|---|---|---|---|
| Public/partner API | **default** | many diverse clients | rarely (tooling burden on partners) |
| Service-to-service | fine | wrong tool | **default** (perf, codegen, deadlines) |
| Browser clients | native | native | needs gRPC-Web/Connect proxy layer |
| Streaming | SSE/WS bolt-on | subscriptions bolt-on | first-class (4 modes) |
| Payload efficiency | verbose | verbose | binary, ~5-10x smaller, cheap parse |
| HTTP caching/CDN | excellent | poor | none |
| Human debuggability | curl-able | tooling | needs grpcurl/buf curl |
| Contract | OpenAPI (optional) | SDL (intrinsic) | proto (intrinsic, enforced) |

Practical rule: **gRPC inside the datacenter, REST at the edge, GraphQL only when
client-shape diversity demands it.** Mixed estates are normal; transcode at the
gateway (grpc-gateway / Connect / Envoy gRPC-JSON transcoder) rather than
hand-maintaining parallel APIs. Consider Connect-RPC where you want gRPC semantics
plus curl-able JSON over plain HTTP without a proxy.

## 2. Proto evolution — the field-number contract

Wire compatibility lives in **field numbers and types**, not names.

- **Never change a field number. Never reuse one.** A reused number deserializes
  old data into the wrong field — silent corruption, not an error.
- **Never change a field's type** (except documented wire-compatible sets like
  int32/uint32/int64/bool — and even those change language-level semantics; avoid).
- Renaming a field is wire-safe but breaks JSON transcoding and generated code —
  treat as breaking if protojson or codegen consumers exist.
- **Deleting a field: `reserved` the number AND the name**, forever:

```protobuf
message User {
  reserved 4, 9 to 11;
  reserved "ssn", "internal_score";
  string id = 1;
  string display_name = 2;
}
```

- New fields: optional semantics, new unique number. Required fields don't exist
  in proto3 — and proto2's `required` was removed for a reason: required is forever.
- **Enums: entry 0 is `FOO_UNSPECIFIED`** always; never renumber; `reserved`
  removed values. Open enums: receivers keep unknown values (proto3) — code must
  `default:` handle them.
- Scalars have no presence in proto3 (0/""/false ≡ unset). When "unset vs zero"
  matters (PATCH-like updates, money), use `optional` (proto3 field presence) or
  wrapper types, plus `google.protobuf.FieldMask` for partial updates.
- Don't repurpose semantics under the same field; add a new field, deprecate old
  (`[deprecated = true]`) and follow rules/02 §5.
- **Enforce with `buf breaking` in CI** against the previous commit/main. Protos
  live in one schema repo/module with code review; consumers pin generated
  artifacts. Hand-edited generated code is an audit finding.
- Package versioning: `package billing.v1;` — a true breaking change means
  `billing.v2` side-by-side, both served during migration.

Evolution example — the corruption trap:

```protobuf
// v1                                  // v2 — WRONG
message Payment {                      message Payment {
  string id = 1;                         string id = 1;
  int64 amount_cents = 2;                string customer_note = 2;  // reused #2!
}                                      }
// Old senders' amount_cents bytes now parse as customer_note garbage —
// or worse, varint-compatible types silently produce wrong values. No error.

// v2 — RIGHT
message Payment {
  reserved 2;
  reserved "amount_cents";
  string id = 1;
  Money amount = 3;          // new field, new number, richer type
}
```

## 3. Deadlines everywhere

gRPC's killer operational feature — and the most commonly omitted.

- **Every client call sets a deadline.** No deadline = infinite default = threads
  and connections wedged behind a slow dependency until restart.
- Propagate, don't reset: deadlines flow with the context across hops. A service
  with 200ms left gives its downstream ≤200ms (gRPC propagates `grpc-timeout`
  automatically when you pass the inbound context — so *pass the inbound context*).
- Budget top-down: edge sets the total (e.g. 1s); interior hops inherit the
  remainder. Per-hop floors guard against doing pointless work: if remaining
  budget < your P99, fail fast with `DEADLINE_EXCEEDED`.
- **Servers must check cancellation** (`ctx.Done()` / `context.isCancelled()`)
  before/within expensive work and abort DB queries — otherwise clients give up
  but servers keep burning, the classic cascading-overload pattern.
- Retries: only on idempotent methods, only with backoff + jitter, only within the
  original deadline; honor `RESOURCE_EXHAUSTED`/pushback. Use gRPC service config
  retry policy or a mesh — not hand-rolled loops. Hedging only for read-only calls.

```go
// BAD: no deadline, background context
resp, err := client.GetUser(context.Background(), req)

// GOOD: propagated inbound ctx + explicit ceiling
ctx, cancel := context.WithTimeout(inboundCtx, 300*time.Millisecond)
defer cancel()
resp, err := client.GetUser(ctx, req)
```

## 4. Streaming patterns

Four modes; pick the simplest that works — unary is right ~90% of the time.

- **Server streaming**: large result sets (chunked instead of giant unary
  responses — keep messages < ~1-4 MB; set `maxReceiveMessageSize` deliberately),
  watch/subscribe feeds, progress updates.
- **Client streaming**: uploads, batched telemetry ingestion.
- **Bidirectional**: chat-like sessions, interactive sync protocols. Costly to get
  right (ordering, flow control, app-level acks) — require justification.
- Rules for any stream:
  - Deadlines still apply; long-lived streams need an explicit max age + graceful
    re-establish (also re-balances load after topology changes).
  - Cap the **number of messages** a client may send on one stream, alongside
    per-message size and max age: a stream of many small messages passes a
    size limit. Over the cap, end the stream with `RESOURCE_EXHAUSTED`, the
    canonical code for an exhausted per-user resource. The cap is enforced in
    the handler or a stream interceptor; server options bound message size and
    connection age, not message count (grpc-go's `ServerOption` set has no
    per-stream message limit). OWASP: gRPC Security cheat sheet.
  - **Flow control is real backpressure** — never buffer unboundedly around a
    slow receiver; respect the write-availability signal (`onReady`/blocking send).
  - Design resumability at the app layer (resume tokens / cursors in the request)
    — streams will drop; reconnect must not re-send or skip data.
  - Heartbeat long quiet streams (HTTP/2 PING via keepalive config — respect
    server `keepalive` enforcement policy or get `GOAWAY ENHANCE_YOUR_CALM`).
- Don't use streaming as a database replication protocol or for >minutes-long
  transfers where object storage + signed URL is simpler and restartable.

## 5. Service design patterns (steal from AIPs)

Google's API Improvement Proposals (aip.dev) are the de-facto style guide for
resource-oriented gRPC; follow them unless you have a reason:

```protobuf
service OrderService {
  rpc GetOrder(GetOrderRequest) returns (Order);
  rpc ListOrders(ListOrdersRequest) returns (ListOrdersResponse);
  rpc CreateOrder(CreateOrderRequest) returns (Order);
  rpc UpdateOrder(UpdateOrderRequest) returns (Order);   // uses FieldMask
  rpc CancelOrder(CancelOrderRequest) returns (Order);   // custom verb, reified
}

message ListOrdersRequest {
  int32 page_size = 1;        // server clamps; 0 => default
  string page_token = 2;      // opaque cursor — same rules as REST (01 §4)
  string filter = 3;          // constrained filter expression, allowlisted fields
  string order_by = 4;
}
message ListOrdersResponse {
  repeated Order orders = 1;
  string next_page_token = 2; // empty => done
}
```

- Standard verbs (`Get/List/Create/Update/Delete`) + reified custom verbs;
  request/response message per RPC (never share request messages across RPCs —
  they evolve independently; never return bare scalars — you can't add fields
  to an `int64`).
- `Update` takes `google.protobuf.FieldMask update_mask` — explicit partial
  update beats "absent means unchanged" guessing (§2 presence).
- Long-running work returns `google.longrunning.Operation` (the gRPC analogue
  of REST's 202 pattern, rules/01 §11) — pollable, cancellable, with typed
  metadata/result.
- `buf lint` in CI for naming/package/style; one lint config org-wide.
- Pagination, idempotency (request IDs on Create), and tenant scoping rules
  from 01/07 apply unchanged — the wire format doesn't exempt you.

## 6. Errors and metadata

- Use canonical codes correctly; clients branch on code:
  `INVALID_ARGUMENT` (bad request), `NOT_FOUND`, `ALREADY_EXISTS`,
  `FAILED_PRECONDITION` (state conflict), `PERMISSION_DENIED` vs
  `UNAUTHENTICATED`, `RESOURCE_EXHAUSTED` (rate/quota), `UNAVAILABLE`
  (retryable infra), `DEADLINE_EXCEEDED`, `INTERNAL` (your bug).
  **Never** stuff app errors into `UNKNOWN` or encode them in message strings.
- Rich detail: `google.rpc.Status` + `error_details.proto` types —
  `BadRequest.FieldViolation` for validation, `RetryInfo` for pushback,
  `ErrorInfo{reason, domain, metadata}` for machine-readable causes. This is the
  gRPC analogue of RFC 9457.
- Don't leak internals in messages (mirrors rules/01 §9). Include trace IDs via
  metadata/interceptors.
- Interceptors (client+server) are the standard home for auth, deadline floors,
  logging, metrics, panic-to-`INTERNAL` conversion — not per-method copy-paste.

## 7. gRPC-Web, Connect, and the browser

- Browsers can't speak native gRPC (no control over HTTP/2 frames/trailers).
  Options: **gRPC-Web** (Envoy/in-process proxy; no client streaming, server
  streaming is text/binary framed), **Connect protocol** (POST/JSON or binary,
  curl-able, no proxy needed, interops with gRPC servers), or **JSON transcoding**
  at the gateway (`google.api.http` annotations → REST surface).
- Public-facing rule: don't hand partners raw gRPC unless they asked for it —
  transcode to REST at the gateway from the same protos so there's one source of
  truth.

## 8. Load balancing & operations

- gRPC's persistent HTTP/2 connections defeat L4 load balancers: all RPCs from a
  client ride one connection to one backend. Use **client-side LB** (resolver +
  `round_robin`/weighted), a **service mesh** (Envoy/linkerd L7 per-RPC balancing),
  or an L7 proxy. Audit flag: gRPC behind a plain TCP/L4 LB with hot-spotting.
- Set `MAX_CONNECTION_AGE` (+ grace) on servers so connections cycle and rebalance.
- Health: standard `grpc.health.v1.Health` service wired into LB/mesh checks;
  reflection enabled in non-prod for grpcurl, deliberate decision for prod.
- Keepalive tuned on both sides and consistent with proxy idle timeouts (the #1
  cause of mysterious `UNAVAILABLE` storms).
- TLS everywhere; mTLS for service-to-service is the 2026 default (mesh-issued
  certs). Per-call auth (JWT/OAuth) in metadata via interceptors, validated
  server-side — transport identity ≠ caller authorization.
- Observability: standard interceptor stack exporting per-method RPC metrics
  (rate, error-by-code, latency histograms) and trace propagation
  (W3C `traceparent` / OpenTelemetry gRPC instrumentation). `DEADLINE_EXCEEDED`
  and `UNAVAILABLE` rates are your two most important alerts — they precede
  user-visible outages. For security, break metrics down **per client identity**
  too (request rate, and `UNAUTHENTICATED`/`PERMISSION_DENIED` rates) and alert on
  a spike in authn/authz failures, calls to unknown methods (`UNIMPLEMENTED`)
  and `RESOURCE_EXHAUSTED` bursts. Per-method totals hide one client probing.
  Keep the client label bounded (service or tenant ID, not raw IP) so metric
  cardinality stays manageable. OWASP: gRPC Security cheat sheet.

Reference keepalive alignment (mismatches cause `UNAVAILABLE` storms):

```text
client keepalive_time            60s   # >= server's min allowed (else GOAWAY)
server KEEPALIVE_ENFORCEMENT min 30s
server MAX_CONNECTION_IDLE       5m
server MAX_CONNECTION_AGE        30m (+5m grace)
LB / proxy idle timeout          > client keepalive_time  (e.g. 350s ALB default — check!)
```

## Audit checklist

- [ ] Protocol choice justified: gRPC internal / REST edge / GraphQL only for client diversity; no raw gRPC forced on unwilling partners.
- [ ] `buf breaking` (or equivalent) gates proto changes in CI; protos versioned in a shared module; no hand-edited generated code.
- [ ] No field number ever reused; removed fields have `reserved` numbers AND names (check git history of .proto files).
- [ ] Enums have `*_UNSPECIFIED = 0`; consumer code handles unknown enum values with a default branch.
- [ ] Field presence handled deliberately (proto3 `optional`/FieldMask) where unset≠zero matters — especially money and PATCH-style updates.
- [ ] Every outbound RPC sets a deadline derived from the inbound context; grep for `context.Background()`/missing `withDeadline` at call sites.
- [ ] Servers check cancellation in expensive paths and propagate aborts to DB/downstream calls.
- [ ] Retry policy: idempotent-only, backoff+jitter, deadline-bounded, via service config/mesh — no naive retry loops.
- [ ] Status codes used canonically; rich errors via `error_details.proto`; no app errors in `UNKNOWN`/message-string parsing; no internal leak in messages.
- [ ] Max message sizes configured; large transfers use streaming chunks or signed URLs, not giant unary messages.
- [ ] Streams: bounded buffering honoring flow control, app-level resume tokens, max stream age, keepalive config consistent with proxies.
- [ ] Client-streaming and bidi handlers cap messages per stream and end over-cap streams with `RESOURCE_EXHAUSTED` — MEDIUM. Read each handler's receive loop (`Recv()`, `onNext`, `async for`) for a counter.
- [ ] Metrics per client identity with alerts on authn/authz-failure spikes, `UNIMPLEMENTED` probing and `RESOURCE_EXHAUSTED` bursts — MEDIUM.
- [ ] Per-RPC L7 load balancing (client-side/mesh/proxy) — not a bare L4 LB; `MAX_CONNECTION_AGE` set.
- [ ] Standard health service wired to infra; reflection disabled or justified in prod.
- [ ] TLS/mTLS on all links; per-call authn validated in server interceptors; authz not inferred from transport alone.
- [ ] Browser/partner access goes through gRPC-Web/Connect/transcoding generated from the same protos.
- [ ] AIP-style hygiene: per-RPC request/response messages (none shared, no bare scalar returns), `page_size`/`page_token` listing, `FieldMask` updates, LRO `Operation` for long work, `buf lint` in CI.
- [ ] Create/mutating RPCs carry request IDs (idempotency) where retries are configured.
