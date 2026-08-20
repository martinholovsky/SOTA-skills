# 02 — Test Design & Quality

What makes one test good. Apply to every test at every layer.

## 2.1 Test behavior, not implementation

The contract: **a pure refactor must not break tests; a behavior change must
break exactly the tests that describe that behavior.** Tests that fail on
refactors train the team to update tests mechanically — at which point the
suite verifies nothing except "the code is what the code is."

- Drive the subject through its public interface (exported function, HTTP
  endpoint, component props/user events) — the same door production uses.
- Assert on observable outcomes: return values, state changes visible through
  the public API, messages emitted across a boundary. Not on private fields,
  call counts of internal helpers, or internal ordering.
- If you need to reach into privates to assert, the design is hiding an
  output. Fix the design (return it, emit it, expose a query) or assert on
  the eventual observable effect.

```ts
// BAD — asserts the mechanism; any internal reshuffle breaks it
it("calls normalize then validate then save", () => {
  const spyN = vi.spyOn(svc as any, "normalize");
  const spyV = vi.spyOn(svc as any, "validate");
  svc.register(input);
  expect(spyN).toHaveBeenCalledBefore(spyV);
});

// GOOD — asserts the outcome; internals are free to change
it("registers a user with a normalized email", async () => {
  await svc.register({ email: "  Ada@Example.COM " });
  expect(await users.findByEmail("ada@example.com")).toBeDefined();
});
```

## 2.2 Arrange–Act–Assert, visibly

Every test has three phases in order, ideally separated by blank lines:
**Arrange** (build the world), **Act** (one call to the subject), **Assert**
(verify the outcome). Given/When/Then is the same discipline.

- **One Act per test.** Multiple act-assert cycles in one test = multiple
  tests trench-coated as one; the first failure hides the rest, and the name
  can't describe what's verified.

```rust
// BAD — phases interleaved; reader must simulate the test to understand it
#[test]
fn cart() {
    let mut c = Cart::new();
    c.add(item("a", 10));
    assert_eq!(c.total(), 10);
    c.add(item("b", 5));
    c.apply_coupon("HALF");
    assert_eq!(c.total(), 8); // 8? from what? half of which subtotal?
}

// GOOD — one behavior, phases visible, expectation derivable by the reader
#[test]
fn coupon_halves_the_cart_total() {
    let cart = a_cart().with_items(&[item("a", 10), item("b", 6)]).build();

    let total = cart.with_coupon("HALF").total();

    assert_eq!(total, 8); // (10 + 6) / 2
}
```
- Arrange noise belongs in builders/helpers (`rules/03`), not inline — but
  the *relevant* arrangement must stay visible in the test (see 2.7 mystery
  guest).
- Assert phase contains no logic. If you're computing the expected value with
  the same algorithm as the SUT, you've tested `x == x` (see 2.7
  tautological tests). Use literals or independently-derived expectations.

## 2.3 One logical assertion per test

One test verifies one *behavior*. That may take several `assert` lines (a
single logical assertion about one outcome object is fine); it may not verify
several *behaviors*.

```go
// FINE — many assert lines, one logical assertion: "parse yields this struct"
cfg, err := Parse(input)
require.NoError(t, err)
assert.Equal(t, "prod", cfg.Env)
assert.Equal(t, 5*time.Second, cfg.Timeout)

// BAD — three behaviors in one test; name lies about at least two of them
func TestUser(t *testing.T) {
    u := New("ada")
    assert.Equal(t, "ada", u.Name)        // creation
    u.Deactivate()
    assert.False(t, u.Active)             // deactivation
    assert.Error(t, u.Charge(10))         // billing rule for inactive users
}
```

Heuristic: if the test name needs "and", split it. Parameterize near-duplicate
behaviors (table tests) instead of cloning test bodies.

## 2.4 Naming is specification

The failing test name alone — in a CI log, without opening the file — must
tell the reader *what behavior broke under what condition*. Pattern:
`subject_scenario_expectation` or a readable sentence.

```
BAD:  test1, testCharge, test_charge_2, it("works"), TestProcess_Error
GOOD: charge_declines_when_card_expired
      Withdraw_returns_InsufficientFunds_when_amount_exceeds_balance
      it("retries idempotent requests at most 3 times on 503")
```

A name you can't write precisely is a sign the test verifies nothing precise.
The suite's names, read top to bottom, should read as the module's spec:

```text
RateLimiter
  ✓ allows requests under the limit
  ✓ rejects the request that exceeds the limit within the window
  ✓ resets the budget when the window elapses
  ✓ tracks limits per API key, not globally
  ✓ fails open when the backing store is unreachable   ← policy made visible
```

That last line is why names matter: a reviewer can challenge "fails open" as
a *decision* without reading any code.

## 2.5 Independence and isolation

Every test must pass: alone, in any order, repeated twice in a row, and in
parallel with its siblings. Violations are High-severity — they manifest as
"passes locally, fails in CI" and block parallelization (`rules/07`).

- **No shared mutable state**: no test mutating module-level/static/global
  variables, no shared fixture object reused across tests by mutation, no
  shared rows in a shared DB without per-test scoping (`rules/04` §4.3).
- **No ordering dependence**: never rely on a previous test having created
  data. Each test arranges its own world; cleanup is the *arranging* test's
  job (better: unique-per-test namespaces/transactions so cleanup is moot).
- **No leakage outward**: tests must not leave env vars, temp files, global
  config, or singletons modified. Use the framework's scoped setup/teardown
  that runs even on failure.
- Smell: a `clearAll()`/`resetDatabase()` at the top of *other* tests means
  someone is leaking. Find the leaker; don't institutionalize the mop.
- Verify mechanically: run the suite shuffled (`pytest -p randomly`,
  `go test -shuffle=on`, jest `--randomize` or sequencer) in CI. Order bugs
  found at introduction time cost minutes; found later, days.

## 2.6 Determinism: inject clock, randomness, and network

A test may consume only inputs it controls. The big three leaks:

- **Time.** Never `now()` in code under test reached by assertions. Inject a
  clock (parameter, constructor, or the language's fake-time facility) and
  pin it. Bugs that only appear at month/DST/leap boundaries become testable;
  "fails every Feb 29 / midnight UTC" flakes become impossible.
- **Randomness.** Inject the RNG or seed it per test. For property-based
  tests, the framework owns the seed and prints it on failure (`rules/06`).
  UUIDs in assertions: inject the generator or assert on shape, not value.
- **Network.** Unit tests touch no sockets. Integration tests touch only
  dependencies the test started itself (`rules/04`). Tests against
  third-party live endpoints belong in a separate, non-blocking suite.
  **Prove this rather than asserting it: block egress and run the suite.**
  Anything that fails was not the unit test it claimed to be. What this catches
  is not a slow test — it is a test that *passes for the wrong reason*, because
  a real call succeeded where the assertion was supposed to do the work. The
  usual mechanism is a config object the code under test never reads: the test
  constructs `Config(providers=[])` while the SUT resolves providers from the
  environment (`sota-code-security` rules/11 §6.7 — a setting counts as applied
  only when you have traced it end-to-end). While you are there, check each
  surviving assertion against the test's own **name**: a test called
  `test_no_providers` asserting `healthy is True` is telling you that one of the
  two is wrong, and the real calls are why nobody noticed.
- **Concurrency.** Never assert on timing ("done within 50ms") as a proxy for
  correctness. Synchronize on events/promises/channels; use the runtime's
  virtual-time tools for timeout logic. `sleep(100ms)` is a flake with a fuse:
  too short on a loaded CI runner, pure waste everywhere else.
- **Iteration order.** Don't assert ordered equality on values harvested from
  unordered structures (hash maps/sets); sort first or compare as sets.

```python
# BAD — breaks at year boundaries, untestable for the interesting cases
def is_expired(card):
    return card.expiry < datetime.now()

# GOOD — clock is an input; boundary cases become one-line tests
def is_expired(card, *, now: datetime) -> bool:
    return card.expiry < now

def test_card_expiring_today_is_not_expired():
    noon = datetime(2026, 6, 12, 12, 0, tzinfo=UTC)
    assert not is_expired(card(expiry=datetime(2026, 6, 12, 23, 59, tzinfo=UTC)), now=noon)
```

## 2.7 Test smells catalog

Name the smell in audit findings; each has a standard fix.

- **Assertion-free test** (Critical): exercises code, asserts nothing — only
  proves "doesn't throw". If no-throw IS the behavior, say so explicitly
  (`assert_does_not_raise`-style) and name it that; otherwise add the real
  assertion. Grep: test bodies with zero `assert|expect|require|should`.
- **Tautological test** (Critical): expected value computed by the same logic
  as the SUT (`assert sut.f(x) == helper_that_reimplements_f(x)`), or
  asserting a mock returns what you stubbed it to return. Verifies nothing.
- **Mockery / excessive mocking** (High): more lines configuring doubles than
  asserting outcomes; asserting interactions with internals. Fix via 2.1 and
  `rules/03` boundary discipline.
- **Mystery guest** (Medium): the assertion depends on something outside the
  test the reader can't see — a 400-line shared fixture, a magic row in
  `seed.sql`, file #47 in `testdata/`, or (the original sense of the name in the
  standard catalog) an *external resource* the test reaches for: a file on disk,
  a database, a host. Fix: builders with only the relevant fields explicit
  (`rules/03` §3.5); keep shared fixtures immutable and tiny; replace the
  external resource with a double or move the test to `rules/04`.
- **Resource optimism** (High): the test assumes an external resource is
  *present* — a path, a mount, a reachable endpoint — so its outcome is a
  property of the machine, not of the code. It passes where the resource exists
  and fails, or worse passes vacuously, where it does not. Mystery guest is a
  readability defect; this one is a hermeticity defect, and §2.6's egress block
  is how you find the network half of it.
- **Conditional logic in tests** (Medium→High): `if/else`, `try/except`-and-
  continue, loops with branch-dependent assertions. A test with branches has
  untested branches of itself. Fix: split into one straight-line test per
  case; parameterize.
- **The liar / always-green** (Critical): cannot fail — assertions inside a
  callback that never runs, `expect` inside an `if`, async test missing its
  await so it passes before assertions execute, swallowed assertion
  exceptions. Detect: mutate the SUT, test stays green.
- **Eager test** (Medium): asserts the whole world after one act — 30
  assertions over every field including ones irrelevant to the behavior.
  Brittleness without information. Assert the deltas that define the behavior.
- **Slow-poke at the wrong layer** (Medium): a 5s "unit" test booting a
  framework. Reclassify or rewrite (`rules/01` §1.2).
- **Sleeping test** (High): `sleep`/`waitFor(fixed_ms)` as synchronization.
  Fix: event-based waits, polling-with-timeout helpers, fake time. Grep:
  `sleep\(|Thread\.sleep|time\.Sleep|setTimeout.*done|waitForTimeout`.
- **Hidden retry** (High): `@retry`/`flaky`/rerun annotations on a test
  instead of a root-cause label and quarantine (`rules/07` §7.1).
- **Print-debug residue** (Low): `console.log`/`print` in committed tests.

## 2.8 Snapshot testing discipline

Snapshots (golden files) are legitimate for output whose *exact full form is
the contract*: serialized API responses, generated code/SQL, CLI output,
rendered emails. They are a trap as a default assertion.

- **Small, named, reviewed.** A snapshot a human can't review in a diff is a
  change-detector, not a test. 1000-line component-tree dumps get rubber-
  stamped (`--update` reflex) and then the suite verifies nothing. Prefer
  inline snapshots for anything under ~20 lines so the expectation lives in
  the test.
- **Normalize volatile fields** (timestamps, ids, hostnames, versions) before
  snapshotting, or the snapshot flakes / forces constant updates.
- **One snapshot per behavior**, named for the behavior, never auto-numbered
  (`mismatch-3.snap` tells a reviewer nothing).
- **Updating a snapshot is changing a contract** — the diff must be reviewed
  with exactly that gravity. Bulk `update-snapshots` commits mixing dozens of
  files are a High audit finding.
- For deliberate large goldens (legacy characterization), see approval
  testing in `rules/06` §6.4 — same mechanics, explicit intent.

## 2.9 Comments and structure in tests

- Tests need *why* comments even less than production code — a test whose
  intent isn't obvious from name + body should be rewritten, not annotated.
  The exception: non-obvious magic values (`// 86401 = one day + leap second`)
  and links to the bug a regression test pins (`// regression: #4521`).
- Keep helper indirection shallow: one level of builder/helper. A test you
  can only understand by chasing four helper files has the mystery-guest
  smell with extra steps.

## 2.10 Which method a durable guard is written in

Auditing and authoring are different activities with different lifetimes, and the
library states a default for the first but not the second. An **audit search** is
discarded the day it runs — grep is often the right tool, and `sota-code-security`
rules/10's absence rule already governs it (widen the search, use a second independent
method, state what you ran). A **guard** is a permanent claim that a property holds,
re-evaluated on every commit by people who will not re-derive it. It deserves a stronger
default:

| method | establishes | cannot establish |
|---|---|---|
| text / regex | nothing durable | code vs. a *comment about* code; per-site scope |
| **AST** | structure — call sites, arguments, definitions | dynamic access, types, runtime values |
| **execution / interception** | behaviour — the value actually arrives | only what the test exercises |
| **mutation** | that the guard *can* fail | that the mutation took — assert it |

- **Author structural guards in AST, not text.** Two failure modes are specific to text
  and neither is prevented by care. A guard for `Scanner\s*\(` flagged the file that
  documented *in a comment* that the call had been removed — text cannot tell code from
  prose about code. And a file-scope check ("does this file mention the factory
  anywhere?") lets **one compliant site excuse every other site in the same file**; a
  real regression passed. Inspect the node: for a call, its own keyword arguments.
- **A structural guard cannot carry a behavioural claim.** *"The argument is forwarded"*
  is structure; *"the configured value arrives"* is behaviour, and needs interception or
  execution. Reported case: AST proved a `depth` argument was forwarded and could not
  show whether the forwarded value was the configured `16` or a stale `4`.
- **Mutation-test the guard, then verify the mutation took** (rules/06 §6.3).
- **Regex only where no parser exists** — a DSL, a log format, a config dialect, prose.
  Name which, in a comment, so the exception does not spread by imitation.
- **Name the parser, or the rule gets ignored exactly where it is least convenient.**
  AST is free in some ecosystems (Python `ast`, Ruby `Prism`, Go `go/ast`, Rust `syn`,
  TS `typescript` compiler API / `ts-morph`, Java `JavaParser`, PHP `nikic/PHP-Parser`)
  and an install away in others — and "no parser at hand" is the moment people reach for
  regex. Decide the parser once, per language, at the same time you decide the guard.

**The honest limit, which the guidance must state or it manufactures the false
confidence the rest of this library exists to prevent: AST does not resolve types.** A
field audit still counts `.timeout_sec` on *any* object, so a name collision with an
unrelated attribute reads as live — a **false negative**, the more dangerous direction.
AST removes string-and-comment noise; it does not remove name ambiguity. The output of a
structural sweep is a **candidate list to verify**, never a verdict, and "AST-based" is
exactly the phrase that tempts a reader to treat it as one.

Measured on one 38k-test Python codebase: the same audit rewritten from `grep` to
`ast.walk` went from **74 orphan candidates to 61**. The thirteen were fields read via
`getattr(cfg, "name")` with a string literal — which the AST pass sees and grep does not.
More precise *and* more sensitive, not a trade.

## Audit checklist

- [ ] Durable guards written in **AST** where the claim is structural, not regex over
      source? Two tells that a text guard is in place: it can match a *comment about*
      the code, and it checks file scope rather than the offending node, so one
      compliant site excuses the rest of the file (§2.10).
- [ ] Any structural guard carrying a **behavioural** claim ("the configured value
      arrives") that only execution or interception can support (§2.10)?
- [ ] Does any structural sweep get reported as a **verdict** rather than a candidate
      list? AST does not resolve types, so a name collision reads as live — a false
      negative (§2.10).
- [ ] Assertion-free tests? Mechanical sweep: list test functions lacking any
      assert/expect/require/verify token → Critical each.
- [ ] Can flagship tests fail? Invert one assertion or `return` early in the
      SUT for 2–3 core tests; still green → Critical (the liar).
- [ ] Async tests missing await on the asserted action?
      Grep: `it\(.*async` bodies with un-awaited promises; Python `async def test` without awaited call → Critical.
- [ ] Refactor-brittleness: do tests spy on internal/private methods?
      Grep: `spyOn\(.*(as any)|verify\(.*internal|assert_called.*_private|reflect` in tests → High.
- [ ] Real time in tests/SUT under test? Grep:
      `datetime\.now|time\.Now\(\)|Date\.now|new Date\(\)|System\.currentTimeMillis|Instant\.now` in test paths and in modules with boundary-condition tests → High.
- [ ] **Unit suite run with egress blocked** — any new failure is a test that
      was passing because a real call succeeded → High each; then re-read those
      tests' names against their assertions, and check whether the config they
      construct is the config the SUT actually reads (§2.6).
- [ ] Sleeps as sync? Grep: `time\.sleep|time\.Sleep|Thread\.sleep|setTimeout|waitForTimeout|page\.wait_for_timeout` in tests → High each.
- [ ] Order/parallel safety: does CI run the suite shuffled and parallel?
      Run shuffled once during audit; any new failure → High.
- [ ] Shared mutable state? Grep tests for writes to globals/statics/env:
      `os\.environ\[|process\.env\.[A-Z_]+ *=|static .* =|var [A-Z]` (lang-adjust) without scoped teardown → High.
- [ ] Conditional logic in tests? Grep: `^\s+(if|for|while|try)\b` inside test
      bodies (exclude table-test loops over cases) → Medium.
- [ ] Names as spec: sample 20 names; can you state the behavior from the name
      alone? `test\d|_works|_ok\b|misc|stuff` patterns → Low–Medium.
- [ ] Snapshots: any snapshot file >100 lines, auto-numbered, or updated in
      bulk commits (`git log --oneline -- '**/__snapshots__/**' | head`)?
      Unreviewable snapshots → Medium; routine bulk updates → High.
- [ ] Hidden retries: grep `@pytest.mark.flaky|retries:|jest.retryTimes|@Retry|FlakyTest` → High unless tied to a tracked quarantine (`rules/07`).
