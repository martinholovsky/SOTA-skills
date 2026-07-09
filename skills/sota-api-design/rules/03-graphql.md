# 03 — GraphQL

Scope: when (not) to use it, schema design, N+1/dataloaders, query cost controls,
persisted queries, error handling, security, evolution.

## 1. When GraphQL is the wrong choice

Choose GraphQL when: many heterogeneous clients (web + mobile + partners) with
divergent data shapes; aggregation over multiple backends (BFF/federation); rapid
frontend iteration where the server team is a bottleneck.

It is the **wrong** choice when:
- **Server-to-server APIs** — fixed call shapes; REST/gRPC are simpler, cacheable,
  and have better tooling for this.
- **One client, one team** — you pay the complexity tax (resolvers, dataloaders,
  cost limits, caching workarounds) without the flexibility benefit.
- **File upload/download heavy** — multipart-over-GraphQL is a hack; use signed
  URLs + REST.
- **HTTP-cache-dependent** — POST-based queries bypass CDN/browser caches; if your
  win is `Cache-Control: public`, GraphQL erases it (GET + persisted queries
  partially restores it, §5).
- **Hard latency/throughput budgets** — resolver fan-out and JSON weight lose to
  gRPC.
- **Public unauthenticated APIs without resourcing** — you are signing up for
  cost-analysis, depth limits, and abuse engineering; if you can't staff that,
  expose REST.

A GraphQL layer that fronts exactly one REST API 1:1 is pure overhead — delete it
or give it a real aggregation job.

## 2. Schema design

- **Schema-first, design-reviewed**: the SDL is the contract; review it like an
  OpenAPI spec. Run schema checks (Apollo/Hive/`graphql-inspector`) in CI against
  production traffic to catch breaking changes.
- Nullability is a promise: **non-null (`!`) only when the server can always
  deliver**, because a null in a non-null field destroys the whole parent selection
  (error bubbling). Nullable-by-default on object fields backed by other services;
  non-null for IDs and intrinsic scalars.
- Connections, not naked lists: Relay connection spec (`edges/node/pageInfo`,
  `first/after`) for anything that can grow. Naked `[Order!]!` is an unbounded
  query waiting to happen. Enforce a max `first`.
- Mutations: one **input object** per mutation (`input PlaceOrderInput`), one
  **payload type** per mutation containing the changed entity + `userErrors:
  [UserError!]!` (§6). Name mutations verb-first: `placeOrder`, `cancelSubscription`.
- Mutually exclusive input variants: use a **`@oneOf` input object** (standardized
  in the September 2025 spec edition) — exactly one field set, enforced by the type
  system — instead of multiple nullable fields plus runtime validation.
- Global object identification: `id: ID!` globally unique (encode type+id),
  `node(id:)` lookup — enables client-side normalized caching.
- Model relationships as fields, not foreign keys: `order.customer: Customer`, not
  `order.customerId: ID` (expose the ID too if clients need it cheaply).
- Custom scalars for semantics: `DateTime`, `EmailAddress`, `Money`/`BigInt` — not
  stringly-typed `String`.
- Avoid god-queries (`viewer { everything }`) and generic JSON scalars — `JSON`
  fields are contract escape hatches that defeat the type system.

## 3. N+1 and dataloaders

The default resolver execution model is N+1 by construction: a list of 100 orders
each resolving `customer` issues 100 queries.

- **Every field resolver that hits a data source goes through a batch loader**
  (DataLoader pattern: per-request cache + batch window). No exceptions for
  "small" fields — query shapes you didn't predict will combine them.
- Loaders are **per-request** (auth context, no cross-user cache leaks). Never
  process-global with user data.
- Batch by the access pattern: `userById`, `ordersByCustomerId` (one loader per
  key shape). For SQL backends, loaders translate to `WHERE id = ANY($1)`.
- Lookahead optimization where it pays: inspect the selection set to JOIN/preload
  instead of loading lazily — but only after loaders, not instead of them.
- **Test it**: assert query counts in integration tests (e.g., run a 2-level query
  over a list of 50, assert ≤ small constant DB calls). N+1 regressions are silent
  until production.

```text
BAD : resolve Customer per order  -> SELECT * FROM customers WHERE id = $1   x100
GOOD: DataLoader batches one tick -> SELECT * FROM customers WHERE id = ANY($1) x1
```

## 4. Query cost controls — non-negotiable on any exposed endpoint

A single unauthenticated query can be a DoS (`{ users { friends { friends {
friends ... }}}}`). Layered defenses, all of them:

1. **Depth limit** (typically 8–12) — blocks recursive nesting.
2. **Complexity/cost analysis** — assign cost per field (list fields multiply by
   `first`), reject above budget *before execution*; charge cost against
   rate-limit quotas (points/minute, à la GitHub/Shopify).
3. **Breadth/alias limits** — cap aliases and root fields per document
   (alias-based amplification: `a1: heavyField a2: heavyField ...` defeats naive
   depth limits).
4. **Paginate everything** + max page size (§2).
5. **Timeout per request** and per resolver; cancel downstream work on abort.
6. **Disable introspection and GraphiQL in production** for non-public schemas;
   disable field suggestions ("Did you mean `creditCard`?") which leak schema.
7. **Reject batched arrays of operations** or cap batch size — batching multiplies
   everything above and bypasses per-request rate limits. Beyond cost-DoS this is a
   **rate-limit-bypass brute-force vector**: aliases/batches let one HTTP request
   carry hundreds of `login`/OTP/token/password-reset attempts past per-request
   throttles. Disable aliasing/batching on auth operations and rate-limit those
   fields **per object/account**, not just per request.

## 5. Persisted queries

Two distinct tools — know which you're deploying:

- **APQ (automatic persisted queries)**: client sends SHA-256 hash, falls back to
  full text on miss. A bandwidth/cache optimization only — **not** security; anyone
  can register any query.
- **Persisted-query allowlist (trusted documents)**: queries extracted from client
  code at build time, registered server-side; production endpoint **rejects
  arbitrary query text** and accepts only known document IDs. This is the SOTA
  posture for first-party-client APIs: kills query-shape abuse, most cost-attack
  surface, and enables GET + CDN caching of hot queries.
- Default for apps you control: allowlist in production, free-form only in dev.
  Public third-party APIs can't allowlist — that's when §4 must carry the load.

## 6. Error handling

GraphQL transports over HTTP 200; do not let that destroy observability.

- **Two error channels, used deliberately**:
  - Top-level `errors` array: *exceptional/system* failures (auth, downstream
    outage, cost-limit). Include machine-readable `extensions.code`
    (`UNAUTHENTICATED`, `FORBIDDEN`, `RATE_LIMITED`, `BAD_USER_INPUT`, `INTERNAL`).
  - **Domain errors as schema**: expected business failures are data, not errors —
    `userErrors: [UserError!]!` on mutation payloads, or union result types
    (`PlaceOrderResult = Order | InsufficientFunds | OutOfStock`). Clients get
    typed, exhaustive handling; your error contract evolves with schema checks.
- Mask internals: never propagate raw exception messages/stack traces into
  `errors[].message`; log server-side with a `trace_id` echoed in `extensions`.
- Partial data is a feature: nullable field fails → field is null + entry in
  `errors` with `path`; clients render the rest. This is why §2 nullability matters.
- Use `application/graphql-response+json` (GraphQL-over-HTTP spec): request errors
  (parse/validation) may use 4xx; field errors stay 200 with `errors`. Ensure your
  monitoring counts GraphQL errors, not just HTTP 5xx — otherwise outages look
  like 100% success.

## 7. Authorization & multi-tenancy

- Authenticate at the transport (HTTP middleware), **authorize per field/object in
  resolvers** (or directive/policy layer). The graph is reachable from many roots
  — `node(id:)`, nested relations — so object-level checks must live with the
  object, not the entry point.
- Never trust IDs from arguments: `order(id:)` must verify tenant/ownership
  (classic GraphQL IDOR).
- `node(id:)` global lookup is an IDOR superhighway if type-level authz is missing.
- Don't expose internal mutations/fields on the public schema — split schemas
  (public vs admin) rather than relying on authz alone; what's not in the schema
  can't be probed.

## 8. Schema snippets — good/bad

```graphql
# BAD
type Query {
  orders: [Order]                    # unbounded, nullable-soup list
}
type Order {
  customerId: String!                # FK instead of relationship
  status: Boolean!                   # can't evolve; meaningless name
  meta: JSON                         # contract escape hatch
}
type Mutation {
  updateOrder(id: String!, status: Boolean, note: String): Order  # arg sprawl
}

# GOOD
type Query {
  orders(first: Int! = 50, after: String, filter: OrderFilter): OrderConnection!
  node(id: ID!): Node
}
type Order implements Node {
  id: ID!
  customer: Customer                 # relationship; nullable: separate service
  status: OrderStatus!               # enum, documented open
  createdAt: DateTime!
}
type Mutation {
  cancelOrder(input: CancelOrderInput!): CancelOrderPayload!
}
type CancelOrderPayload {
  order: Order
  userErrors: [UserError!]!          # domain failures as data
}
```

## 9. Subscriptions

- Transport: GraphQL-over-WebSocket (`graphql-ws` protocol — not the legacy
  `subscriptions-transport-ws`) or **GraphQL over SSE** (`graphql-sse`) — prefer
  SSE for server-push-only subscriptions per rules/05 §1. Everything in rules/05
  applies: auth (`connection_init` payload = first-message auth, with timeout),
  heartbeats, reconnect/backoff, backpressure.
- Subscriptions are for **small, fast deltas** ("order 42 changed"), not data
  transfer: push the ID/patch, let the client query for the full shape, or
  resolve a narrow selection. Fat subscription payloads multiply resolver fanout
  by subscriber count.
- Each subscription field maps to a pub/sub topic with object-level authz at
  subscribe time **and** per-event filtering (the topic may carry other tenants'
  events; filter before resolve).
- Server restarts drop all subscriptions silently — clients must treat
  subscription data as a cache over a re-fetchable source (snapshot on
  reconnect), never the system of record. No replay buffer exists by default;
  if gaps matter, add sequence numbers + re-query (rules/05 §2.3).
- Cap concurrent subscriptions per connection and per principal; subscription
  resolvers go through the same cost analysis as queries.

## 10. Caching and federation notes

- Lose HTTP caching, replace deliberately: persisted queries over GET for
  CDN-cacheable public reads; `@cacheControl`-style hints feeding a response
  cache keyed by (document, variables, auth scope) — never share cached
  responses across principals; entity-level caching inside dataloaders.
- Client caches normalize by `id` — another reason for global object IDs (§2).
- Federation (multiple subgraphs behind one router) only when multiple teams own
  distinct subdomains of one graph. It buys ownership boundaries and costs: a
  router on the hot path, cross-subgraph N+1 (entity resolution must be
  batched), and composition checks that **must** run in CI (a subgraph deploy
  can break the supergraph). Don't federate a single-team schema; modularize the
  codebase instead.

## 11. Evolution

- Additive is easy (new fields/types). Removal: `@deprecated(reason:)` →
  field-level usage metrics (which clients, which operations) → contact → remove
  when traffic is zero. Schema registries give you this; without per-field usage
  data you can never delete anything.
- Never change a field's type or nullability in place — add `fieldV2`/new name,
  deprecate old.
- Enums: same open-enum discipline as REST (rules/02 §6) — clients must tolerate
  unknown values.

## Audit checklist

- [ ] GraphQL is earning its keep (multiple clients/aggregation) — flag 1:1 REST-wrapper deployments.
- [ ] Schema checks run in CI against real traffic; breaking changes blocked.
- [ ] All list fields paginated (connections) with enforced max page size; no unbounded lists.
- [ ] Non-null used deliberately; cross-service-backed fields nullable (error-bubbling blast radius understood).
- [ ] Every data-fetching resolver goes through per-request DataLoaders; integration test asserts query counts (no N+1).
- [ ] Depth limit, cost analysis (with list multipliers), and alias/root-field caps active in production — verify by sending a hostile query in staging over **both** the HTTP path and the WebSocket/SSE subscription path (cf. CVE-2026-30241: Mercurius enforced queryDepth on HTTP but not WS subscriptions; fixed in 16.8.0).
- [ ] Operation batching capped or disabled; cost charged against rate limits.
- [ ] Introspection + field suggestions disabled in production for private schemas; no GraphiQL exposed.
- [ ] First-party clients use a persisted-query allowlist (trusted documents); APQ not mistaken for security.
- [ ] Mutations use input objects + payload types with `userErrors`/result unions; domain errors are schema, not exceptions.
- [ ] `errors[].extensions.code` machine-readable; raw exception messages masked; trace ID present.
- [ ] Monitoring counts GraphQL-level errors (200-with-errors), not just HTTP status.
- [ ] Object-level authorization in resolvers (incl. `node(id:)` and nested paths); tenant checks on every ID argument.
- [ ] Public vs admin schema split; no internal fields on public schema.
- [ ] Deprecations carry reasons + removal dates; per-field usage metrics exist before removals.
- [ ] Subscriptions use `graphql-ws`/`graphql-sse` (not legacy protocol), authz at subscribe + per-event filtering, small delta payloads, client snapshot-on-reconnect; concurrent subscriptions capped.
- [ ] Response caches keyed by auth scope (no cross-principal cache hits); federation (if present) has CI composition checks and batched entity resolution.
