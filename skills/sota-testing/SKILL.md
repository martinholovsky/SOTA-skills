---
name: sota-testing
description: >-
  State-of-the-art software testing strategy and practice (2026) for designing
  test strategy, writing unit/integration/e2e tests, or auditing test suites.
  Covers suite shape (pyramid/trophy/honeycomb), test design quality
  (behavior-first, AAA, determinism, smells), test doubles
  (mocks/fakes/stubs), test data (builders over fixtures), real-dependency
  integration (Testcontainers-style), contract testing (Pact/consumer-driven),
  e2e/UI strategy (selectors, auto-waiting, flake economics), property-based
  testing, fuzzing, mutation testing, approval testing, and suite health/CI
  (flaky-test policy, coverage philosophy, sharding). Trigger keywords -
  testing, test strategy, unit test, integration test, e2e, end-to-end,
  coverage, flaky tests, TDD, contract testing, property-based, mocking,
  fixtures, snapshot test, mutation testing, fuzzing, BDD, Gherkin,
  given-when-then, acceptance criteria, security testing, WSTG, IDOR test,
  authz test, abuse case, DAST. Use for BOTH building and auditing test
  suites.
---

# SOTA Testing (2026)

Expert-level, language-agnostic rules for producing and auditing production test
suites. Per-language runner/tooling details (pytest, go test, cargo test,
vitest/jest) live in the language skills ([`sota-python`](../sota-python/SKILL.md), [`sota-golang`](../sota-golang/SKILL.md),
[`sota-rust`](../sota-rust/SKILL.md), [`sota-javascript-typescript`](../sota-javascript-typescript/SKILL.md)) — this skill defines the strategy,
design discipline, and quality bar those tools execute against. Every rule
states the *why*; every rules file ends with an audit checklist of yes/no
questions and grep-able smells.

## Purpose

Two consumers, one source of truth:

- **BUILD mode** — designing a test strategy or writing tests for new code:
  follow the rules as defaults, not suggestions. Deviate only with an explicit
  comment justifying the deviation.
- **AUDIT mode** — reviewing an existing suite: hunt violations using the audit
  checklists, classify by severity, report in the finding format below.

## BUILD mode

1. Before writing tests, read the rules files relevant to the layer you are
   testing (see index). A service touching HTTP + DB + a message queue needs
   `01`, `02`, `03`, `04`.
2. Apply the **top-10 non-negotiables** (below) unconditionally.
3. Decide the suite shape FIRST ([`rules/01`](rules/01-strategy-and-shape.md)): what counts as a unit here, where
   the integration boundary is, which 3–10 flows deserve e2e. Write that
   decision down (CONTRIBUTING.md or a test README) so the next contributor
   doesn't relitigate it.
4. New test code is production code: same review bar, same lint rules, no
   `TODO: assert something` placeholders. A merged test with no assertion is
   worse than no test — it manufactures false confidence.
5. Write tests alongside the code, not after the PR is "done". For bug fixes,
   write the failing test first — it is the only proof the fix fixes anything.
6. Default to real dependencies in containers over mocks for anything with
   I/O semantics you don't own (DBs, brokers, caches) — see [`rules/04`](rules/04-integration-contract-system.md).
7. When generating code for a test that legitimately violates a rule (e.g. a
   sleep in a test that verifies a timeout), comment why inline.

## AUDIT mode

**Coverage:** every `rules/` file's Audit checklist applies in AUDIT mode. Mark one *not applicable* only with its reason in the report — never skip a file because the thing it checks for is absent, since that absence may be the finding.

Audit the suite, not just the tests: shape, doubles discipline, data
management, CI health, and what is *missing* (untested risk) all count.

**Severity conventions:**

- **Critical** — the suite lies: assertion-free tests, tests that can't fail
  (always-green), mocks asserting mock behavior, disabled/skipped tests hiding
  known-broken production behavior, coverage gates gamed by meaningless tests.
- **High** — the suite is unreliable or unmaintainable at current trajectory:
  shared mutable state between tests, order-dependent tests, real
  time/network/randomness without injection, flaky tests un-quarantined and
  retried-to-green, e2e suite owning logic the unit layer should own,
  mocking internals so refactors break hundreds of tests.
- **Medium** — quality erosion: mystery-guest fixtures, multi-behavior tests,
  snapshot dumps nobody reviews, sleeps instead of waits, fixture data with
  irrelevant noise, missing negative-path tests on critical flows.
- **Low** — style/hygiene: weak names, redundant assertions, minor AAA
  violations, missing parameterization of near-duplicate tests.

**Finding format** (one per line):

```
file:line | rule-id | severity | finding and concrete fix
```

Example:

```
tests/orders_test.py:88 | 02-determinism | High | uses datetime.now(); inject a fixed clock so the test cannot fail at month boundaries
tests/api/user.spec.ts:12 | 03-mock-boundary | High | mocks internal UserValidator; test the real validator, mock only the HTTP gateway
```

End every audit with: findings table, top-3 risks, and a prioritized fix list
(quick wins vs structural).

## Rules index

| File | Read this when... |
|------|-------------------|
| [`rules/01-strategy-and-shape.md`](rules/01-strategy-and-shape.md) | choosing pyramid/trophy/honeycomb, defining unit vs integration boundaries, deciding what NOT to test, risk-based prioritization, budgeting test cost |
| [`rules/02-test-design-quality.md`](rules/02-test-design-quality.md) | writing or reviewing any test: behavior-over-implementation, AAA, naming, one logical assertion, determinism (clock/random/network — incl. **proving hermeticity by running the suite with egress blocked**, and tests that pass because a real call succeeded), test smells catalog (assertion-free, tautological, the liar, mystery guest, resource optimism), snapshot discipline |
| [`rules/03-doubles-and-test-data.md`](rules/03-doubles-and-test-data.md) | deciding mock vs fake vs stub, fixing over-mocked suites, building test data (builders/factories vs fixtures), seeding test DBs, using production data |
| [`rules/04-integration-contract-system.md`](rules/04-integration-contract-system.md) | testing against real DBs/brokers (Testcontainers-style), contract testing between services (Pact, schema-based), API testing, migrations, message/queue tests, ephemeral environments, and **a bench that fails silently — including a green run that quietly ran fewer tests** |
| [`rules/05-e2e-and-ui.md`](rules/05-e2e-and-ui.md) | building or pruning an e2e suite: critical-path selection, selector strategy, auto-waiting, page objects/screenplay, visual regression, when to delete e2e tests |
| [`rules/06-property-fuzzing-mutation.md`](rules/06-property-fuzzing-mutation.md) | going beyond examples: property-based testing (what properties to encode), fuzzing parsers, mutation testing ROI — **including that the revert is part of the probe**, not cleanup — approval testing for legacy code, chaos pointer |
| [`rules/07-suite-health-and-ci.md`](rules/07-suite-health-and-ci.md) | flaky-test policy and quarantine, coverage philosophy (ratchets not targets), speed budgets, parallelization correctness **and the opposite case of two independent runs sharing one database**, CI sharding, failure triage, **a threshold measured on one population and asserted over a pooled one**, **a PR-diff check that routes deleted, skipped or weakened tests to human sign-off** |
| [`rules/08-bdd-spec-by-example.md`](rules/08-bdd-spec-by-example.md) | BDD / specification by example: Given-When-Then done declaratively, the three-amigos value (and when there's no cross-role audience), outside-in double loop with TDD, scenario-explosion and UI-script anti-patterns, Gherkin tooling, and tracing scenarios to spec acceptance criteria ([`sota-docs-workflow` rules/05](../sota-docs-workflow/rules/05-spec-driven-development.md)) |
| [`rules/09-security-testing.md`](rules/09-security-testing.md) | security testing as a test type: WSTG as the verification map, the security-regression set (IDOR/BOLA, BFLA, authn/session, injection, mass-assignment, rate-limit, SSRF, tenant isolation run as the production DB role and pooler, cross-identity cache tests), **a role × method × path authz matrix, OpenAPI-derived auth negatives and a test that the enforcer is still wired**, independent authorship of security tests, business-logic/abuse-case tests from threat models, where SAST/DAST/fuzz fit and their ceiling, security-critical coverage floor, stack fingerprinting and external recon, WebSocket and message-size tests, the penetration-testing process and manual REST technique, security stress runs, logging kept on during security runs. Pairs with [`sota-code-security`](../sota-code-security/SKILL.md), [`sota-threat-modeling`](../sota-threat-modeling/SKILL.md), [`sota-devsecops` rules/05](../sota-devsecops/rules/05-analysis-gates.md) |

## Per-language detail

This skill holds test strategy and design. Each language skill carries the mechanics — its runner, fixtures, coverage, fuzzing and CI flags — in one file. Read it beside this one whenever the suite is in that language:

| Language | File |
|---|---|
| Python | [`sota-python` rules/07](../sota-python/rules/07-frameworks-testing.md) |
| Go | [`sota-golang` rules/07](../sota-golang/rules/07-tooling-ci.md) |
| Rust | [`sota-rust` rules/07](../sota-rust/rules/07-tooling-ci.md) |
| C / C++ | [`sota-c-cpp` rules/06](../sota-c-cpp/rules/06-build-tooling-ci.md) |
| Java / Kotlin | [`sota-jvm` rules/06](../sota-jvm/rules/06-build-tooling-ci.md) |
| C# / .NET | [`sota-dotnet` rules/06](../sota-dotnet/rules/06-build-tooling-ci.md) |
| JavaScript / TypeScript | [`sota-javascript-typescript` rules/07](../sota-javascript-typescript/rules/07-testing-and-tooling.md) |
| PHP | [`sota-php` rules/05](../sota-php/rules/05-composer-tooling.md) |
| Ruby | [`sota-ruby` rules/04](../sota-ruby/rules/04-supply-chain-tooling.md) |
| Swift | [`sota-swift` rules/08](../sota-swift/rules/08-tooling-ci-testing.md) |

## Top-10 non-negotiables

1. **Every test must be able to fail.** A test that passes when the code under
   test is deleted or inverted is a Critical finding. Verify the failure mode
   when writing (break the code, watch it go red — TDD gives this for free).
2. **Test behavior through public interfaces, not implementation.** If a
   pure refactor (no behavior change) breaks the test, the test is wrong.
3. **No real time, randomness, or network in unit tests.** Inject clocks,
   seed or inject RNGs, fake the network. Nondeterminism is how flakes are born.
4. **No shared mutable state between tests; no ordering dependence.** Every
   test must pass alone, in any order, and in parallel with its siblings.
5. **Mock only at architectural boundaries you own the interface to** (your
   gateway/port), never internals, and don't mock types you don't own —
   wrap them, then fake the wrapper. Verify fakes against the real thing.
6. **One logical behavior per test**, named as a specification of that
   behavior (`rejects_expired_card`, not `test_payment_2`).
7. **Integration tests use real dependencies** (containerized DB/broker/cache),
   not in-memory lookalikes with different semantics. SQLite is not Postgres.
8. **E2E is a small, curated, critical-path suite** (smoke + money paths) with
   role/testid selectors and auto-waiting — never `sleep()`, never a dumping
   ground for cases a lower layer can cover.
9. **Flaky tests are quarantined within a day, with an owner and an expiry** —
   never silently retried-to-green forever, never deleted without a
   root-cause label (ordering / async / time / infra / test bug / real bug).
10. **Coverage is a gap-finder, not a target.** Ratchet it (never decrease),
    read the uncovered lines, and never write a test whose only purpose is to
    move the number.

Security-critical paths (authn/authz, crypto, input parsing, money/quota,
tenancy, untrusted data) additionally require **negative security tests** at a
higher coverage bar — see [`rules/09`](rules/09-security-testing.md). A green functional suite proves nothing
about IDOR, injection, or broken authz.
