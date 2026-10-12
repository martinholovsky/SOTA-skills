# 01 — Strategy & Suite Shape

Decide the shape of the suite before writing test #1. Most bad suites are not
bad tests — they are good tests at the wrong layer.

## 1.1 Choose the shape by architecture, not by fashion

The pyramid/trophy/honeycomb debate is a proxy for one question: **where does
your risk live?** Put the bulk of tests at the layer where your bugs are born
and where tests are cheapest to keep honest.

| Shape | Bulk of tests at | Fits when |
|-------|------------------|-----------|
| **Pyramid** (many unit, fewer integration, few e2e) | unit | domain-heavy code: parsers, pricing engines, compilers, business rules — logic dominates, I/O is thin |
| **Trophy** (most at integration, thin unit + e2e caps) | integration | UI components and glue-heavy apps: the unit layer would be all mocks; integration tests (component + real-ish collaborators) catch what users hit |
| **Honeycomb** (per-service: thick integration, thin unit, minimal cross-service) | service integration | microservices: each service is mostly orchestration around I/O; in-service integration tests + contract tests replace cross-service e2e |

Rules of thumb:

- **Logic-to-glue ratio decides.** Code that computes → pyramid. Code that
  coordinates → trophy/honeycomb. Most real systems need both shapes in
  different modules; pick per-module, not per-company.
- **A microservice fleet must NOT lean on cross-service e2e.** Combinatorial
  environments, slow feedback, ownership ambiguity. Use in-service integration
  tests with containerized dependencies ([`rules/04`](04-integration-contract-system.md)) plus contract tests at
  every service edge, and keep cross-service e2e to a handful of smoke flows.
- **Whatever the shape, the e2e tip stays small** (see [`rules/05`](05-e2e-and-ui.md)). The shape
  argument is about the middle and bottom, never about growing the top.
- **Write the decision down.** One paragraph in CONTRIBUTING.md: "In this repo
  a unit is X, integration tests run against Y, e2e covers flows Z1..Zn."
  Undocumented shape decays into "every PR adds a test wherever it's easiest."

## 1.2 Define the unit/integration boundary explicitly

Teams burn weeks arguing "is this a unit test?" because the boundary was never
defined. Define it operationally:

- **Unit test**: runs entirely in-process, no real I/O (disk/network/DB), no
  real clock, finishes in milliseconds, parallel-safe by construction.
- **Integration test**: exercises your code against at least one real
  out-of-process dependency (DB, broker, filesystem, another service) or a
  real framework runtime (HTTP stack, DI container).
- **E2E test**: drives the deployed system through the same interface a user
  or client uses.

The classification is about *what runs*, not directory names. A "unit test"
that hits localhost Postgres is an integration test with a misleading label
and a misleading runtime budget.

### Sociable vs solitary units

A "unit" is a unit of *behavior*, not a class/function. Two valid styles:

- **Sociable (default)**: the test exercises the subject *with its real
  in-process collaborators*; only architectural boundaries (I/O, time,
  external services) are doubled. Survives refactoring because internals can
  be reshaped freely.
- **Solitary**: every collaborator is doubled. Justified only when the
  collaborator is itself a boundary, is nondeterministic, or is genuinely
  expensive in-process (rare).

```python
# BAD — solitary by reflex: refactoring TaxCalculator breaks this test
def test_order_total():
    tax = Mock(TaxCalculator)
    tax.rate_for.return_value = Decimal("0.20")
    order = Order(items=[item(price=100)], tax_calculator=tax)
    assert order.total() == Decimal("120")
    tax.rate_for.assert_called_once_with("GB")   # implementation detail

# GOOD — sociable: real TaxCalculator, real Money; only boundaries are real-world
def test_order_total_includes_gb_vat():
    order = Order(items=[item(price=100)], tax_calculator=TaxCalculator(region="GB"))
    assert order.total() == Decimal("120")
```

Mock-everything solitary suites are the #1 cause of "all tests pass, prod is
down" and "rename a method, fix 400 tests."

## 1.3 What NOT to test

Every test costs forever (1.6). Spend nothing on:

- **The framework/stdlib.** Don't test that your ORM saves, that the router
  routes, that `serde`/`Jackson` serializes a plain struct. Test *your*
  configuration of it only where you can plausibly misconfigure it.
- **Trivial accessors and pass-throughs.** Getters, setters, one-line
  delegations, DTOs. They have no behavior; they're covered incidentally by
  the behaviors that use them.
- **Private functions directly.** Test through the public surface. If a
  private helper is so complex it begs for its own tests, that's a design
  signal: extract it into its own module with a public interface.
- **Generated code and vendored code.** Test the generator's config or the
  contract, not the output line-by-line.
- **Third-party API behavior.** You can't fix it and the test will flake.
  Pin your *assumptions* about it instead with a thin contract test you run
  separately (see [`rules/03`](03-doubles-and-test-data.md) "don't mock what you don't own").
- **Log message wording, exact error prose, UI copy** — unless it IS the
  contract (CLIs, public APIs, i18n keys). Assert on error *types/codes*.
- **The same behavior at multiple layers.** If a unit test proves the
  discount math, the integration test only needs to prove the discount is
  *applied*, and e2e doesn't need it at all. Duplicate coverage = duplicate
  maintenance with zero added confidence.

## 1.4 Risk-based prioritization

Test depth must follow risk, not module enumeration. Score each area by
`impact-of-failure × likelihood-of-failure` and spend accordingly:

- **High impact, high likelihood** (payment calculation, authz checks, data
  migrations, concurrency-sensitive code): exhaustive unit + integration,
  property-based where inputs are open-ended ([`rules/06`](06-property-fuzzing-mutation.md)), negative paths
  mandatory.
- **High impact, low likelihood** (rarely-changed core invariants): solid
  tests once, then mutation-test the area occasionally to confirm the tests
  still bite ([`rules/06`](06-property-fuzzing-mutation.md)).
- **Low impact, high likelihood** (admin screens, formatting): thin happy-path
  coverage; rely on types/lint.
- **Low impact, low likelihood**: consciously untested. Write the decision
  down so an auditor sees a choice, not an oversight.

Likelihood signals to mine: churn (`git log --since=1.year --format= --name-only
| sort | uniq -c | sort -rn | head -30`), past incidents/bug clusters,
cyclomatic complexity, number of authors, "here be dragons" comments.

```text
# Risk-spend worksheet (do this before writing tests for a feature)
area: refund processing
impact: HIGH    — wrong refunds = money loss + support load
likelihood: HIGH — 14 commits last quarter, 2 past incidents
decision: unit-test every rule incl. negative paths; property test on
          amount arithmetic; integration test refund→ledger write;
          contract test with payments service; NO e2e (covered by
          existing checkout smoke flow)
```

**Negative paths are where the risk is.** Auth failures, quota exhaustion,
malformed input, downstream timeouts, partial failures mid-transaction. A
suite with 95% happy-path tests is a low-coverage suite wearing a high number.

## 1.5 Testing quadrants — coverage of *kinds*, not just layers

The Agile Testing Quadrants (Marick/Crispin/Gregory) catch a different gap
than the pyramid: whole categories of testing nobody owns.

- **Q1 — technology-facing, supporting the team**: unit + component tests.
  Automated. This skill's [`rules/02`](02-test-design-quality.md)–`03`.
- **Q2 — business-facing, supporting the team**: acceptance/API/contract
  tests expressing requirements as examples. Automated. [`rules/04`](04-integration-contract-system.md)–`05`.
- **Q3 — business-facing, critiquing the product**: exploratory testing,
  usability, UAT. *Human* — do not pretend automation covers this; schedule
  exploratory sessions for risky releases.
- **Q4 — technology-facing, critiquing the product**: performance, load,
  security, chaos/fault-injection. Tooling, run out-of-band from the PR
  suite. Pointers: [`rules/06`](06-property-fuzzing-mutation.md) §6.5, [`sota-performance`](../../sota-performance/SKILL.md), [`sota-code-security`](../../sota-code-security/SKILL.md).

Audit question: name the artifact covering each quadrant. "None for Q4" is a
finding (High for systems with availability/latency SLOs).

## 1.6 The cost model: write + run + maintain

A test's cost is `write_cost + (run_cost × runs) + (maintain_cost × years)`.
The first term is the smallest and the only one people budget for.

- **Run cost compounds brutally.** A 2-second test in a 50-engineer repo
  running 200 CI builds/day costs ~28 machine-hours/month *and* sits inside
  every human feedback loop. Speed budgets per layer in [`rules/07`](07-suite-health-and-ci.md).
- **Maintain cost is dominated by coupling.** Tests coupled to implementation
  (solitary mocks, snapshot dumps, CSS selectors) levy a tax on every
  refactor. Behavior-coupled tests are near-free to maintain.
- **A test must pay rent.** Each test should be able to answer: "what bug
  would I catch that no cheaper test catches?" If the answer is none, delete
  it. Deleting a redundant or perma-flaky test is suite maintenance, not
  coverage loss — but record why (commit message), and never delete a
  *failing* test as the "fix" for the failure.
- **Prefer the cheapest layer that can express the behavior.** Each rung up
  (unit → integration → e2e) costs roughly an order of magnitude more to run
  and to debug. Push every case down until it loses meaning.

## 1.7 Fixing an inverted suite (ice-cream cone)

The pathological shape: hundreds of slow e2e/UI tests, a thin brittle unit
layer, QA-automation owned, 2-hour pipeline. Don't fix it test-by-test; fix
it flow-by-flow:

1. **Freeze the top**: no new e2e tests without a [`rules/05`](05-e2e-and-ui.md) §5.1
   justification; cap the e2e stage's wall-clock now.
2. **Pick the highest-churn flow** and build its lower-layer coverage first
   (unit for the logic, one integration test for the wiring) — *then* delete
   the redundant e2e variants of that flow (keep one happy path).
3. **Repeat by churn order.** Migrating by churn means each unit of effort
   immediately reduces flake exposure and CI time where changes actually
   happen; migrating alphabetically pays off never.
4. Track the ratio (tests per layer + stage wall-clock) monthly so the
   migration is visible and doesn't silently stall.

The inverse pathology — thousands of mock-heavy "unit" tests and zero
integration confidence — is fixed the same way in reverse: add containerized
integration tests for the riskiest I/O paths ([`rules/04`](04-integration-contract-system.md)), then delete the
mock choreography that duplicates them ([`rules/03`](03-doubles-and-test-data.md) §3.2).

## 1.8 TDD: when it pays, what actually matters

TDD (red → green → refactor) is the highest-leverage way to get tests that
can fail (you watched them fail) and designs that are testable (the test came
first). It pays most for: algorithmic/domain logic, bug fixes (failing test
first, always), and public API design. It pays least for: exploratory spikes
(spike, throw away, then TDD the real thing) and thin glue.

If not doing strict TDD, keep the two load-bearing habits:
1. **See every new test fail** against broken/absent code before trusting it.
2. **Tests merge in the same PR as the behavior** — "tests in a follow-up"
   is how untested code ships.

## Audit checklist

- [ ] Is there a written statement of suite shape and unit/integration
      boundary? (Look in CONTRIBUTING.md, docs/testing.md, test READMEs.
      Missing → Medium.)
- [ ] Does the actual distribution match the architecture? Count tests per
      layer (`find . -path '*e2e*' -name '*test*' | wc -l` vs unit dirs).
      Microservices with a giant cross-service e2e suite → High.
- [ ] Are "unit" tests actually units? Grep unit-test dirs for I/O:
      `grep -rE 'localhost|127\.0\.0\.1|Connect\(|connect\(|requests\.|http\.Client|fetch\(' test/unit/` → mislabeled
      integration tests (Medium; High if they make the unit suite >seconds).
- [ ] Solitary-by-reflex? Ratio of mock constructions to test files —
      `grep -rcE 'Mock\(|mock\.|jest\.mock|@Mock|mockk|gomock' tests/` ;
      mocks of *in-process, owned* collaborators → High (refactor-hostile).
- [ ] Framework/getter tests present? Grep for tests asserting trivial
      delegation or ORM basics (`assert.*getId\(\)|test.*getter|save.*find.*assert equal` patterns) → Low, delete.
- [ ] Do the riskiest modules (top churn × past incidents) have the deepest
      tests, including negative paths? Sample 3 critical modules; happy-path-only
      on a money/auth path → High.
- [ ] Is any behavior tested at 3+ layers? Pick one business rule and grep for
      its assertions across unit/integration/e2e → Medium (consolidate down).
- [ ] Quadrant gaps: is there *anything* for performance/security/chaos (Q4)
      and exploratory (Q3)? None for a system with SLOs → High.
- [ ] Are bug fixes accompanied by a regression test? Sample 5 recent
      fix-commits (`git log --grep='fix' --oneline | head`) and check each
      touched a test → missing pattern is Medium.
- [ ] Any test that cannot fail? Spot-check: invert a core `assert` or stub
      the SUT in 2–3 important tests and rerun — still green → Critical.
