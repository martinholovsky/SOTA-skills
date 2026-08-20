# 02 — Versioning, Evolution & Deprecation

Scope: additive-change discipline, what counts as breaking, version placement
tradeoffs, tolerant readers, deprecation lifecycle (Deprecation/Sunset headers),
enum and schema evolution.

## 1. The prime directive: evolve, don't version

A new major version is a **failure mode**, not a tool. Every major version doubles
maintenance, splits traffic and docs, and strands clients. Design v1 so that years
of change stay additive. Teams that internalize this ship `v1` forever (Stripe runs
one URL version + dated changes); teams that don't accumulate `v1`–`v4` zombies.

## 2. What is breaking vs additive

**Additive (safe, ship anytime):**
- New optional request field, new request header, new query param (with default).
- New response field. New endpoint. New optional enum *input* value.
- Relaxing validation (accepting more than before).
- New error `code` under the existing error shape.

**Breaking (requires deprecation cycle or new version):**
- Removing/renaming any field, endpoint, or query param.
- Type change (`string`→`int`), format change (epoch→ISO), semantic change of an
  existing field ("amount" switches units).
- Tightening validation (rejecting what used to pass).
- New **required** request field. Changing defaults. Changing auth requirements.
- Changing status codes for existing situations (404→410 is breaking for clients
  that branch on it).
- New value in a response enum **is breaking for clients that switch exhaustively**
  — see §6.
- URL structure changes, pagination scheme changes, error shape changes.

Gray zone — treat as breaking unless contract says otherwise: field ordering
(never promise it), response timing/latency characteristics clients depend on,
rate-limit reductions.

Enforce mechanically: OpenAPI/proto diff in CI (`oasdiff`, `buf breaking`) that
fails the pipeline on breaking diffs. Human review alone misses these.

## 3. Tolerant reader / never break parsers

Both sides of the contract:

**Servers must promise:** unknown response fields may appear at any time. Document
this loudly: *"Clients MUST ignore unknown fields."* This single sentence is what
makes additive evolution legal.

**Clients you write must:**
- Ignore unknown JSON fields (configure deserializers: don't `FAIL_ON_UNKNOWN_PROPERTIES`,
  don't `additionalProperties: false` on response validation).
- Handle unknown enum values (map to `UNKNOWN`, don't crash — §6).
- Never depend on field order or absence-vs-null distinctions not in the contract.

**Servers receiving requests:** decide and document unknown-request-field policy.
Ignoring is lenient and traditional; rejecting (`400`) catches client typos
(`"ammount"` silently ignored = money bug). Best practice 2026: **reject unknown
request fields on write operations**, ignore on reads/filters. Either way: explicit.

## 4. Version placement: URL vs header

| | URL (`/v1/users`) | Header (`Api-Version: 2026-06-01`) |
|---|---|---|
| Visibility | obvious in logs, curl, docs | hidden; needs tooling |
| Caching/routing | trivial (path-based) | needs `Vary: Api-Version` |
| "REST purity" | one resource, many URLs | one URL, content negotiation |
| Granularity | big-bang major versions | per-change dates possible |
| Client mistake mode | can't forget it | forgot header → which default? |

**Recommendation:**
- Public API: coarse URL major (`/v1/`) that you intend never to bump, **plus**
  date-based header versioning for behavioral changes (Stripe model:
  `Stripe-Version: 2026-06-12`; account pinned to first-seen date; upgrades opt-in
  per account). This combines discoverability with fine-grained evolution.
- Internal/service-to-service: no URL version; additive-only + tolerant readers +
  CI breaking-change gates. gRPC: package version in proto (`package billing.v1`).
- Never: version in query param (`?v=2`) — cache-key and default ambiguity; per-endpoint
  version mixing (`/v1/users` calls `/v2/orders` semantics) without explicit design.
- If header-versioned: an **explicit, documented default** for missing header
  (oldest-supported or account-pinned — never "latest", which breaks clients on
  every release).

## 5. Deprecation lifecycle

Killing anything (field, endpoint, version, auth scheme) follows a pipeline:

1. **Announce** — changelog, email to affected key owners, migration guide with
   before/after examples.
2. **Mark in spec** — OpenAPI `deprecated: true`; proto `[deprecated = true]`;
   GraphQL `@deprecated(reason: "Use X. Removed 2026-12-01.")`.
3. **Signal in responses** — standard headers:

```http
HTTP/1.1 200 OK
Deprecation: @1767225600                     # RFC 9745: deprecated as of (unix ts)
Sunset: Mon, 01 Jun 2027 00:00:00 GMT        # RFC 8594: will stop working at
Link: <https://api.example.com/docs/migrate-orders-v2>; rel="deprecation"
```

4. **Measure** — per-key metrics on deprecated-surface usage. You cannot sunset
   what you can't attribute. Dashboards by API key/account. If that telemetry does
   not exist, the substitute — counting stored data that carries the feature's shape
   — answers a *different* question and errs toward keep-it: `sota-observability`
   rules/05 §7a.
5. **Nag** — targeted emails to remaining callers; for stragglers, scheduled
   **brownouts** (return `410`/`503` for 5 minutes, then 1 hour, announced in
   advance) — converts ignored emails into pager alerts on the client side.
6. **Remove** — after the sunset date, return `410 Gone` with a problem+json body
   pointing at the migration guide. Not `404` (looks like a client bug).

Minimum runway: 6 months public APIs (12 for auth/breaking-payment changes),
1–3 months internal with known consumers. Put the policy in your docs *before*
you need it.

## 6. Enum and schema evolution

Enums are the most common evolution trap.

- **Response enums**: adding a value breaks exhaustive-matching clients. Options:
  (a) document from day one that enums are **open** — clients must treat unknown
  values as a defined fallback (`"other"`/ignore); (b) gate new values behind the
  version/date header so only opted-in clients see them. Do (a) always, (b) for
  high-impact enums like `status`.
- **Request enums**: adding accepted values is safe.
- Booleans become enums: model tri-state-prone fields as string enums from the start
  (`"state": "active"` not `"is_active": true`) — you cannot evolve a boolean.
- Nullable changes: optional→required on responses is safe; anything→nullable on
  responses is breaking. On requests, the reverse.
- Width/format: never repurpose a field. New semantics ⇒ new field name
  (`amount_cents` alongside deprecated `amount`), dual-write during transition,
  sunset the old one via §5.
- Proto specifics (field numbers, `reserved`) in rules/04. GraphQL deprecation in
  rules/03.

## 7. Running multiple versions

If you do end up with versions:
- **Translate at the edge, one core**: maintain a single internal model; each
  version is a request/response transformation layer (Stripe's
  version-change-modules pattern). Never fork business logic per version.
- Version compatibility tests: golden request/response fixtures per supported
  version, run in CI forever.
- Cap concurrent supported versions (2–3). Each old version must have an owner, a
  metric, and a sunset date the day its successor ships.
- New features land **only** in the newest version — carrot for migration.

## 8. Date-based header versioning — concrete mechanics

The Stripe model, since it's the one worth copying:

```http
GET /v1/subscriptions/sub_9 HTTP/1.1
Authorization: Bearer sk_live_...
Api-Version: 2026-06-01
```

- Each dated version = a small, named change module ("2026-06-01: `status`
  gains value `paused`; `discount` becomes a list"). The core serves only the
  newest shape; modules transform responses backwards (and requests forwards)
  in a chain. New version = new module; old modules are never edited.
- Account pinning: the first version an account ever uses becomes its default;
  requests without the header get the pinned version. Upgrading the pin is an
  explicit, reversible dashboard/API action — ideally with a "preview newest
  against my recent traffic" diff.
- Each module ships with: changelog entry, migration note, and a pair of
  round-trip tests (new-shape → module → old-shape fixtures).
- This machinery costs real engineering. If you can't fund it, the honest
  alternative is: strict additive-only forever + the §5 deprecation pipeline —
  which is what most internal APIs should do anyway.

## 9. Compatibility testing in practice

Breaking-change CI diffs (§2) catch *schema* breaks; behavioral breaks need
golden fixtures:

```text
tests/contract/
  2025-09-01/
    list-orders.request.json      # frozen real request
    list-orders.response.json     # frozen expected response (shape-asserted)
  2026-06-01/
    list-orders.request.json
    list-orders.response.json
```

- Replay every supported version's fixtures against every release; assert shape
  and semantics (field present, type, enum within documented set) — not
  byte-equality (timestamps/IDs vary; over-strict goldens rot).
- Add a fixture the day a version ships; delete it the day the version sunsets.
  The fixture set *is* your supported-version inventory.
- For consumer-driven contracts (Pact et al.): consumer teams publish
  expectations from their actual usage; provider CI verifies before deploy.
  This beats golden files when you control the consumers — it tests what's
  *used*, enabling deletion of what isn't.

## 10. Changelogs and client communication

- Machine-readable changelog (one entry per change: date, surface affected,
  additive/deprecation/breaking, link). Generated from spec diffs where
  possible; hand-written prose drifts.
- Every API key/app has a registered owner contact; deprecation mail goes to
  owners of keys that *actually called* the deprecated surface in the last 90
  days (from §5 metrics) — not a newsletter blast everyone filters.
- SDKs are part of the contract: regenerate and release SDKs with every spec
  change; an SDK that lags the API teaches clients to bypass it. Pin SDK major
  versions to API behavior expectations and document the mapping.
- Sandbox mirrors production versioning — clients must be able to test against
  the version they'll be pinned to, and against the newest, in sandbox.

## Good/bad example

```jsonc
// BAD v1 design (forces v2 later)
{
  "name": "Ada Lovelace",          // can't split into first/last additively
  "is_active": true,               // boolean — can't add "suspended"
  "created": 1718180000,           // epoch int; tz-ambiguous
  "type": 2                        // magic int enum
}

// GOOD v1 design (evolves forever)
{
  "display_name": "Ada Lovelace",
  "given_name": "Ada",
  "family_name": "Lovelace",
  "status": "active",              // open string enum, documented fallback
  "created_at": "2026-06-12T09:33:20Z",
  "type": "organization"
}
```

```jsonc
// BAD deprecation (silent breakage)
//   v1.1 release notes: "renamed `name` to `display_name`"  -> 500s for everyone

// GOOD deprecation (dual-field transition)
{
  "name": "Ada Lovelace",          // still served; marked deprecated in spec,
                                   // Deprecation/Sunset headers on responses
  "display_name": "Ada Lovelace"   // new field, added 2026-06; docs updated
}
// ...usage metric for `name` readers -> 0 -> remove after Sunset date
```

## Audit checklist

- [ ] Documented compatibility policy exists: what's additive vs breaking, unknown-field rules for both directions.
- [ ] Clients-must-ignore-unknown-fields stated in docs; server is free to add response fields.
- [ ] Server's unknown-request-field policy explicit (reject on writes recommended); typo'd field names cannot be silently dropped on money/critical writes.
- [ ] CI runs spec diff (oasdiff / buf breaking / GraphQL schema check) and fails on breaking changes.
- [ ] Version scheme is deliberate: URL major never bumped casually; header/date versioning has a safe documented default (never implicit "latest").
- [ ] No business logic forked per version — version adapters at the edge only.
- [ ] Deprecated surface marked in spec AND signaled at runtime (`Deprecation`, `Sunset`, `Link` headers).
- [ ] Per-key usage metrics exist for deprecated endpoints/fields; sunset decisions are data-driven.
- [ ] Published deprecation runway (≥6mo public) with migration guides; removed endpoints return `410` + pointer, not `404`.
- [ ] Response enums documented as open; client SDKs you ship tolerate unknown enum values and unknown fields.
- [ ] No repurposed fields in history (same name, changed semantics) — grep changelog/spec history.
- [ ] State-like fields are string enums, not booleans; timestamps RFC 3339; no magic-int enums.
- [ ] Old supported versions have golden contract tests, owners, and sunset dates.
