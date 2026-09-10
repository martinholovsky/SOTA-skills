# 04 — Integration, Contract & System Testing

Testing your code against the real things it talks to — and proving services
agree with each other without booting the whole company.

## 4.1 Real dependencies in containers, not lookalikes

For any dependency with semantics you rely on (SQL dialect, transaction
isolation, broker ordering/ack semantics, cache eviction), integration tests
run against **the real engine, containerized and test-managed** —
Testcontainers-style libraries exist across major ecosystems (Java, Go, .NET,
Node.js, Python, Rust, Ruby, PHP and more; per-language wiring in the
language skills).

Rules:

- **The test owns the lifecycle.** The suite starts the container, waits for
  readiness (the library's wait strategies, never `sleep`), and gets a unique
  port. Tests that assume "a Postgres is running on 5432" are
  machine-coupled and collide under parallelism.
- **Pin the image version to production's version.** `postgres:latest` in
  tests + Postgres 14 in prod = testing a different database. Same goes for
  broker and cache versions.
- **Reuse per suite, isolate per test.** Container startup costs seconds —
  amortize with one container per suite/session; get per-test isolation via
  transactions/schemas/keys (4.3), not per-test containers.
- **Mock the third parties you can't containerize** at your adapter port
  (`rules/03` §3.3) or run their official emulators/sandboxes in the same
  container-per-suite pattern — and keep a small non-blocking live-sandbox
  suite to catch emulator drift.

## 4.2 Database testing

Two distinct targets — don't conflate them:

**(a) Your queries/repositories work** — covered by 4.1 + isolation below.

**(b) Your migrations work** — its own test class:

- Every migration runs **forward from an empty schema in CI** on the real
  engine; the integration suite then runs against the *migrated* schema —
  never against a parallel `schema.sql` that drifts from the migration chain.
- Destructive/data migrations get a rehearsal: apply to a snapshot with
  representative (masked) data, assert row counts/invariants after. Verify
  the rollback path actually restores (or document it as forward-only —
  expand-contract; see `sota-databases` for online-migration patterns).
- Test the failure mode that matters: migration applied to a DB that's mid
  old-version traffic (expand/contract compatibility), not just the clean lab
  case.

### 4.3 Per-test isolation: transaction rollback vs truncate

| Strategy | Speed | Limits |
|---|---|---|
| **Wrap each test in a transaction, roll back** | fastest | invisible to code that opens its own transactions/connections; can't test commit-dependent behavior (triggers-on-commit, READ COMMITTED visibility across connections, listen/notify) |
| **Truncate/delete between tests** | slower | serializes tests sharing the DB unless namespaced |
| **Schema/database per test worker** | fast after setup | per-worker migration cost; best base for parallel runners |
| **Unique keys per test, never clean** | fast, parallel-safe | suite must never assert on global counts/absence |

Default stack: schema-per-worker + transaction-rollback per test, and a small
explicitly-marked subset using truncate for the commit-semantics tests the
rollback trick can't express. Whatever you choose: the mechanism lives in ONE
shared fixture/helper, not copy-pasted setup per file.

```go
// BAD — per-file cleanup ritual; misses tables, breaks under parallelism
func TestOrders(t *testing.T) {
    db.Exec("DELETE FROM orders; DELETE FROM users;") // forgot order_items
    ...
}

// GOOD — one helper owns isolation; tests just declare they need a DB
func TestOrders(t *testing.T) {
    db := testdb.New(t) // schema-per-worker, tx-per-test, rollback in t.Cleanup
    ...
}
```

## 4.4 API testing strategy (your own API)

- Test through the real HTTP stack (in-process test server or the
  framework's test client that exercises routing/middleware/serialization) —
  this is where auth middleware ordering and content-negotiation bugs live,
  and unit tests structurally can't see them.
- Cover per endpoint: happy path, **authn/authz failure** (the most expensive
  bug class — assert 401/403 for every protected route as a table test),
  validation failure (400 with stable error codes), not-found vs forbidden
  distinction, and idempotency where claimed (send it twice, assert once).
- Assert on **status + contract-relevant body fields**, not whole-body
  equality (additive fields shouldn't break consumers or tests). If you
  publish an OpenAPI spec, validate responses against the schema in tests so
  the spec can't drift from the implementation.
- Error responses are API surface: assert the error *shape* (code, type
  field), not the human-readable message.

## 4.5 Contract testing between services

The honeycomb's load-bearing wall (`rules/01` §1.1): each consumer–provider
edge is verified **in isolation, asynchronously**, replacing combinatorial
cross-service e2e.

**Consumer-driven contracts (Pact model):**

1. Consumer tests run against a mock provider and *record* the interactions
   they actually need → a pact file (the contract).
2. The contract is published to a **broker** (versioned per consumer/provider
   version + branch/environment tags).
3. Provider CI **replays** every consumer's interactions against the real
   provider service (with provider states seeding the needed data) and
   publishes verification results.
4. Deployments gate on the broker's compatibility matrix (Pact's
   `can-i-deploy`): "is the version I'm deploying verified against every
   counterpart currently in this environment?"

```ts
// Consumer side (Pact-style): record ONLY what this consumer reads.
// Matchers assert shape; exact values only where the value IS the contract.
await provider.addInteraction({
  states: [{ description: "an order 42 exists and is paid" }],
  uponReceiving: "a request for order 42",
  withRequest: { method: "GET", path: "/orders/42" },
  willRespondWith: {
    status: 200,
    body: {
      id: MatchersV3.integer(42),
      status: "paid",                      // exact: consumer branches on it
      total: MatchersV3.decimal(19.99),    // shape: any decimal is fine
      // note: NOT the other 14 fields the provider happens to return
    },
  },
});
```

Discipline that makes it work:

- **Consumers record only what they use.** A contract asserting fields the
  consumer never reads blocks provider evolution for nothing. Use matchers
  (type/shape) over exact values wherever the value isn't the contract.
- **Provider states are part of the provider's test code** ("a user 42
  exists") — keep them thin, built on the same builders as other tests
  (`rules/03`).
- Contract tests verify *schema and semantics of the edge*, not provider
  business logic — that's the provider's own unit/integration suites.

**Schema-based / bi-directional alternative:** provider publishes its schema
(typically OpenAPI); the broker statically checks consumer pacts against it
instead of replaying against a running provider. Cheaper, weaker (no
provider-state semantics, only shape compatibility). Reasonable for: public
APIs with many unknown consumers, org boundaries where CDC coordination won't
happen, GraphQL/gRPC where the schema is first-class (then: schema-diff
checks for breaking changes in CI are the minimum bar, e.g. buf-style
breaking-change detection for protobuf).

**Event contracts:** async messages need contracts too — schema registry with
enforced compatibility mode (backward/forward) for Avro/Protobuf/JSON-schema
topics, or Pact's message-pact flavor. An eventing system without schema
governance is integration-tested by production incidents.

## 4.6 Message/queue testing

- **Split the logic from the plumbing.** Handler logic = unit tests on a pure
  function `(message, state) -> (state, effects)`. Plumbing (serialization,
  routing keys, ack/nack, retries, DLQ) = a small integration suite against
  a real containerized broker (4.1).
- Test the ugly paths, they're the point of queues: **redelivery** (handler
  must be idempotent — deliver twice, assert once), **poison message** (goes
  to DLQ after N attempts, doesn't wedge the partition), **out-of-order**
  where ordering isn't guaranteed.
- Consume-side assertions need polling-with-timeout helpers ("eventually,
  within 5s, exactly one OrderShipped"), never fixed sleeps, and uniquely
  identified messages (test-run id in payload) so parallel runs don't read
  each other's traffic.

## 4.7 Test environments: ephemeral over shared

The shared, long-lived "staging" that's perpetually broken, drifted, and
queued-for is an anti-pattern. Modern default:

- **Ephemeral preview environments per PR** (namespace/stack spun from the
  same IaC as production, seeded by script) for e2e and exploratory testing;
  destroyed on merge. Determinism comes from creation-from-scratch.
- Keep ONE shared environment at most, as a production-mirror for
  release-candidate soak — not as everyone's integration playground.
- Environment seeding uses the same builders/seed scripts as tests
  (`rules/03`), version-controlled. Hand-curated environment data is
  unreproducible by definition.
- If full ephemeral envs are too heavy, the in-repo answer is 4.1: most
  "needs staging" tests are really "needs a real DB/broker", which
  containers give you per-CI-job.

## 4.8 A harness that could not start looks exactly like one that found nothing

Whenever the subject under test runs somewhere else — a container, a VM, a subprocess, a
remote worker — there are two ways to get an empty result, and the assertion cannot tell
them apart. *"No vulnerability reproduced"* and *"the runtime refused to start a container"*
produce the same red or green, and **the first is a scientific conclusion about the target**
while the second is a broken bench.

Field-reported: after a `prune`/`fstrim` corrupted a container runtime
(`sota-devsecops` rules/07 §7.7), an exploit-validation file went from 3 passed to 1 passed
/ 2 failed with a missing-envelope error. Nothing in the failure said *the container never
ran*; it read as the target not being exploitable.

- **Assert liveness before the assertion, and fail on it separately and loudly.** "The
  runtime produced a result at all" is a different question from "the result is X", and it
  must have its own failure message. A fixture that starts one throwaway container and
  asserts it emitted a known marker is enough, and it runs once per session.
- **A green run that ran FEWER TESTS is the same failure wearing the safest possible
  colour.** §4.8's other bullets describe a bench that produces nothing; this one produces
  a pass. Where tests skip themselves when a dependency is absent — the standard
  `skipif(not docker_available)` shape — a stopped container runtime does not fail them, it
  **removes** them: field-reported 2026-09-10, a stopped machine turned exactly 30 tests
  into skips while the suite reported **0 failed**. The only moving number was the skip
  count (30 → 60). So **assert the count, not just the colour**: pin an expected number of
  collected/executed tests for any lane with environment-gated skips, or fail the lane when
  skips exceed a recorded baseline. (`rules/07` §7.6 treats a *drifting* skip count as slow
  rot; this is the acute version, and it is invisible in one run.)
- **Empty is not a result.** An empty output file, an empty stdout, a zero-length report is
  a **failed measurement until proven otherwise** — assert the artefact is non-empty *and*
  contains the summary line you expect before reading anything into it. (The pipe version of
  this — a filter destroying the evidence — is `sota-shell-scripting` rules/01 §3.)
- **Name the subject in the message.** *"exploit not reproduced"* is a claim about the
  target; *"no envelope returned — harness did not start"* is a claim about the bench. The
  general form is `sota/rules/03` §2: when a check reports, say what it is reporting about.
- Distinguish this from a *flaky* dependency. Flakiness is intermittent and the retry is the
  usual answer; this is a bench that is uniformly broken while still looking healthy from
  outside, and retrying it produces the same confident wrong answer every time.

## Audit checklist

- [ ] **Does any lane skip tests when a dependency is missing, and does anything notice?**
      (§4.8) A stopped container runtime converts tests to skips, not failures — the run is
      green and 30 tests never ran. Pin an expected collected count, or baseline the skip
      count and fail on an increase.

- [ ] Do integration tests run the real engine? Grep test config for
      lookalikes: `:memory:|sqlite|H2|fakeredis|embedded` standing in for a
      different prod engine → High.
- [ ] Container images pinned to prod versions? Grep `latest` in
      testcontainers setup / docker-compose.test → Medium.
- [ ] Hardcoded host/ports? Grep `localhost:(5432|3306|6379|9092|27017)` in
      tests → High (machine-coupled, parallel-unsafe).
- [ ] Readiness by sleep? Grep `sleep` between container start and first use
      → High; replace with wait strategies.
- [ ] Does CI run migrations from empty and test against the migrated schema?
      A separate drifting `schema.sql` loaded directly → High.
- [ ] Is per-test DB isolation centralized and matched to needs? Rollback
      strategy + tests asserting cross-connection visibility/commit hooks →
      those tests are lying (High). Copy-pasted cleanup SQL across files →
      Medium.
- [ ] Auth coverage: for each protected route, is there a 401/403 test?
      Spot-check 5 routes; missing on sensitive routes → High.
- [ ] Whole-body equality on API responses? Grep
      `assertEquals.*responseBody|toEqual\(.*body\)|json\(\) == ` → Medium
      (brittle to additive change).
- [ ] Service edges: does every consumer–provider pair have a contract
      (pact/broker, schema-diff CI for gRPC/GraphQL, registry compatibility
      for events)? Uncovered edge between independently-deployed services →
      High.
- [ ] Is deployment gated on contract compatibility (can-i-deploy or
      equivalent), or do contracts exist but gate nothing → Medium (theater).
- [ ] Queue tests: is there a redelivery/idempotency test and a DLQ test for
      each consumer? None → High for money/state-changing handlers.
- [ ] Eventually-consistent assertions: polling helpers with timeout, or raw
      sleeps? Grep `sleep` in queue/e2e test paths → High.
- [ ] Shared staging as the only integration venue, hand-maintained data →
      Medium, recommend ephemeral envs or containerized deps.
- [ ] **Does every out-of-process test assert liveness separately from its result?** (§4.8) A
      harness that could not start and one that ran and found nothing produce the same output,
      and only the second is a conclusion about the target. Empty artefacts are failed
      measurements until proven otherwise.

