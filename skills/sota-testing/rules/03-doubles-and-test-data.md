# 03 — Test Doubles & Test Data

The two ways suites rot from the inside: doubles that detach tests from
reality, and data setups nobody can read or change.

## 3.1 Doubles taxonomy — use the words precisely

- **Dummy**: passed but never used; satisfies a signature.
- **Stub**: returns canned answers to calls made during the test. Drives the
  SUT down a path. No assertions on it.
- **Spy**: a stub that also records calls so the *test* can assert what was
  sent across a boundary (use for outputs you can't observe otherwise:
  "email gateway received one message to ada@…").
- **Mock** (strict sense): pre-programmed with expectations about calls;
  the test fails if interactions differ. Interaction testing.
- **Fake**: a real, simplified implementation — in-memory repository,
  local filesystem blob store, embedded broker. Has actual behavior.

Decision discipline:

- **Querying a dependency for data → stub it.** Asserting how it was called
  adds brittleness, not confidence.
- **Commanding a dependency to cause an external effect → spy/mock it.**
  The call IS the observable outcome (charge the card, send the email,
  publish the event). Assert the message, not the mechanics: assert payload
  fields that matter, not argument-by-argument `called_once_with` over a
  10-field struct, not call ordering unless ordering is the contract.
- **Stateful dependency used across many tests → write a fake once.** Tests
  read naturally ("save then find returns the user") and survive refactors.

## 3.2 Mock only at architectural boundaries

A double replaces a *port* — the seam where your system talks to another
system (DB, HTTP API, broker, clock, filesystem, payment provider). Doubling
anything inside the hexagon couples tests to internal structure (`rules/02`
§2.1) and turns every refactor into test archaeology.

```java
// BAD — mocks an in-process collaborator we own; refactor-hostile, proves nothing
PriceCalculator calc = mock(PriceCalculator.class);
when(calc.priceFor(any())).thenReturn(new Money(100));
CheckoutService svc = new CheckoutService(calc, paymentGateway);

// GOOD — real domain objects; double only the true boundary
CheckoutService svc = new CheckoutService(new PriceCalculator(catalog),
                                          paymentGatewaySpy);
svc.checkout(cartWith(item("sku-1", 100)));
assertThat(paymentGatewaySpy.charges()).containsExactly(chargeOf(100, "EUR"));
```

If unit tests are drowning in mocks, the fix is architectural, not test-side:
separate computation from I/O (functional core, imperative shell). Pure logic
needs zero doubles; the thin shell gets a few integration tests with real
dependencies (`rules/04`).

## 3.3 Don't mock what you don't own

Never stub/mock a third-party SDK's types directly (`stripe.Client`,
`S3Client`, an ORM session). Two failure modes: your stub encodes a guess
about the SDK's behavior that drifts from reality, and the SDK's interface is
shaped for them, not you, so mocks of it are sprawling and fragile.

Instead:

1. **Wrap it**: define your own narrow port (`PaymentGateway.charge(order)`)
   shaped by what *your* domain needs.
2. **Double the port** in unit tests (trivially small surface).
3. **Test the adapter for real**: a thin integration suite runs the real
   adapter against the real dependency (sandbox account, containerized
   service, recorded-and-verified HTTP) — see `rules/04`.

## 3.4 Fakes must be verified against the real thing

An unverified fake is a parallel universe. Run **the same contract test suite
against the fake and the real implementation** (same test class/fixture,
parameterized over implementations). When the real DB rejects a duplicate key
and your in-memory fake happily overwrites, the contract suite catches the
drift before production does.

```python
# One contract suite, two implementations — drift becomes a failing test
class UserRepoContract:
    repo: UserRepo  # set by subclass fixture

    def test_save_then_find_returns_user(self):
        self.repo.save(a_user(email="ada@example.com").build())
        assert self.repo.find_by_email("ada@example.com") is not None

    def test_duplicate_email_is_rejected(self):
        self.repo.save(a_user(email="dup@example.com").build())
        with pytest.raises(DuplicateUserError):
            self.repo.save(a_user(email="dup@example.com").build())

class TestInMemoryUserRepo(UserRepoContract):   # fast, used by unit tests
    repo = InMemoryUserRepo()

class TestPostgresUserRepo(UserRepoContract):   # containerized, integration lane
    repo = postgres_repo_fixture()
```

Corollary: **in-memory lookalikes of infrastructure are fakes you didn't
write and can't verify.** SQLite standing in for Postgres, a fake Redis, an
"embedded-compatible" broker — different SQL dialects, transaction semantics,
ordering guarantees. Use them only for pure-logic speed wins where semantics
provably don't matter; otherwise containerize the real one (`rules/04` §4.1).

## 3.5 Test data: builders/factories over fixture files

Shared fixture files (the 600-line `seed.sql`, the `fixtures/users.json` that
40 tests depend on) are the mystery-guest factory: nobody can tell which
fields matter to which test, and every edit is a game of Jenga.

```json
// BAD — fixtures/users.json: which of these 11 fields does any given test
// need? Nobody knows; every change breaks an unknown subset of 40 tests.
{ "id": 7, "email": "test@test.com", "tier": "premium", "country": "DE",
  "created": "2019-03-04", "verified": true, "marketing_opt_in": false,
  "orders": 3, "ltv": 412.5, "referrer": "campaign-x", "locale": "de_DE" }
```

**Builder/factory pattern** — every object the suite needs gets a builder
with *valid defaults*, and each test overrides only what its behavior
depends on:

```rust
// builder with safe defaults
fn an_order() -> OrderBuilder { OrderBuilder::default() } // valid, paid, 1 item, EUR

#[test]
fn refuses_refund_after_30_days() {
    let order = an_order().paid_at(days_ago(31)).build();
    assert_eq!(refund(&order, now()), Err(RefundError::WindowExpired));
}
```

The test reads as its own specification: the only visible field is the one
the rule is about. Rules:

- **Defaults are valid and boring.** A builder whose default object fails
  validation poisons every test using it.
- **Minimal data principle**: arrange the least data that makes the behavior
  reachable. Three orders when one suffices means a reader must figure out
  why three; required-but-irrelevant fields stay in defaults.
- **Mother objects** (`PremiumCustomer()`, `ExpiredCard()`) — named canonical
  instances — are fine as a thin layer *over* builders for ubiquitous cases.
  Keep them few and immutable; a mother object that grows 30 variants is a
  fixture file with a nicer name. Compose: `a_customer().premium()` scales,
  `PremiumCustomerWithTwoOrdersInGermany()` does not.
- **Randomize what must not matter** (names, emails via faker libs) only with
  a per-test logged seed; never randomize what the assertion depends on.
- Factory libs (factory_boy, FactoryBot, Fishery, etc.) implement this
  pattern; per-language picks live in the language skills.

## 3.6 Seeding strategies and referential integrity

For integration suites against a real DB:

- **Seed reference data once, entity data per test.** Static lookup tables
  (countries, currencies, plans) can load once per suite, treated as
  immutable. Anything a test mutates must be created by that test in its own
  scope (transaction/schema/unique keys — isolation mechanics in
  `rules/04` §4.3).
- **Satisfy referential integrity inside builders**, not by disabling it.
  Turning off FK checks in tests means tests pass against a database that
  production will refuse. `an_invoice()` should transparently create (or
  attach to) its customer; the test only mentions the customer when the
  behavior is about the customer.
- **Unique-per-test identifiers** (UUID/test-name prefixes) beat global
  cleanup: parallel-safe, and orphaned data from crashed runs can't collide
  with future runs.
- **Never assert on auto-increment ids or insertion order** unless ordering
  is the contract; both change under parallelism and seeding refactors.

## 3.7 Production data in tests — caveats first

Real production data finds bugs synthetic data can't (encoding horrors, edge
distributions, scale). But:

- **Anonymization is hard and pseudonymization is not anonymization.**
  Re-identification via joins/rare-values is real; GDPR-style obligations
  follow personal data into your test environment. Treat "anonymized" prod
  dumps as restricted unless a documented, reviewed anonymization pipeline
  exists (defer specifics to `sota-databases` / privacy policy; do not
  hand-roll one inside a test PR).
- **Never load prod dumps into the per-PR test path.** Size kills speed;
  drift kills determinism; a refreshed dump silently changes test outcomes.
- The right use: out-of-band jobs — migration rehearsal against a masked
  snapshot, performance tests, data-quality checks — not assertions in CI
  unit/integration suites.
- **Synthesize from production's *shape*** instead where possible: use prod
  to learn the distributions and edge cases, encode them as builder cases or
  property-based generators (`rules/06`).

## 3.7a Fixtures must cross the thresholds the code branches on

Test data is usually small because small is fast to write and read. That makes
every **size-gated** code path — chunking, sharding, pagination, streaming,
multi-part upload, a batching or budget cap — effectively untested: the branch
exists, the suite is green, and the branch only ever runs in production.

- Find the literals the code compares sizes against, and make **one fixture cross
  each** (`CHUNK_SIZE + 1` rows, one byte over the streaming threshold). One case
  per threshold is enough; the point is that the branch has executed at least once.
- Where a builder makes volume cheap (§3.5), generating 10k rows is a few lines —
  the reason this gets skipped is habit, not cost.
- If crossing the threshold is genuinely too expensive for the default suite, tag
  the case and run it on a schedule, but **record that the branch is untested in
  CI** rather than leaving it implied.

The failure class this belongs to — correct on small inputs, broken or
pathological on large, with nothing in the output saying so — is
`sota-code-security` rules/13 §1.

## 3.8 Doubles hygiene

- **Strict by default**: unmatched calls on a mock should fail the test, not
  return nulls/zero-values that propagate as confusing downstream failures.
- **Don't stub what the test doesn't need.** Every `when(...)` is a claim the
  reader must process; unused stubbings are noise (enable the framework's
  unnecessary-stubbing detection where available).
- **No doubles of value objects** — construct real ones. Mocking a `Money` or
  a DTO is pure ceremony.
- **One double style per boundary across the suite.** If the payment gateway
  is a hand-written spy in 30 tests and a mockito mock in 20, consolidate —
  divergent doubles drift into contradictory assumptions.

## Audit checklist

- [ ] Are mocks confined to architectural boundaries? Sample 10 mock usages:
      each replaces I/O/time/external service? In-process owned collaborators
      mocked → High.
- [ ] Mocked types you don't own? Grep for doubles of vendor types:
      `mock.*(Stripe|S3|Twilio|redis|Session|HttpClient)|jest\.mock\(['"](?!\.)/` (mocking non-relative module paths) → High; fix = wrap + adapter test.
- [ ] Interaction-asserting queries? Grep `verify\(|assert_called` on
      read/query methods (`get|find|fetch|load`) → Medium (convert to stub +
      state assertion).
- [ ] Fakes verified? For each hand-written fake (`Fake[A-Z]|InMemory[A-Z]`),
      does a shared contract suite run against fake AND real? No → High.
- [ ] In-memory DB standing in for the real engine? Grep
      `sqlite::memory:|:memory:|H2|jdbc:h2` in integration config of a
      Postgres/MySQL system → High.
- [ ] Fixture-file gravity: any fixture/seed file referenced by >10 tests
      (`grep -rl 'fixtures/users' tests/ | wc -l`)? → Medium; migrate to
      builders incrementally.
- [ ] Mystery data: open 5 data-dependent tests — can you tell which arranged
      fields the assertion depends on without opening another file? No →
      Medium (mystery guest).
- [ ] Builder defaults valid? Construct each builder's default and run it
      through validation; invalid default → High (poisoned baseline).
- [ ] FK checks disabled in test setup? Grep
      `SET FOREIGN_KEY_CHECKS=0|PRAGMA foreign_keys=OFF|DISABLE TRIGGER|session_replication_role` in test/CI setup → High.
- [ ] Auto-increment/order assertions? Grep `assert.*id == [0-9]+\b|first\(\)\.id|\.id, 1\)` in DB tests → Medium.
- [ ] Production data in the repo or CI path? Grep CI config and test setup
      for prod snapshot/dump references (`prod.*dump|snapshot.*restore|pg_restore`); personal data without documented anonymization → Critical (escalate
      to security/privacy).
- [ ] Unused stubbings / lenient mocks everywhere? Framework strictness off
      globally (`lenient\(\)|RETURNS_DEFAULTS|mock.Anything` saturation) → Medium.
