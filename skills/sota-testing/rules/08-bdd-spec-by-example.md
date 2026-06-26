# BDD and specification by example

Behavior-driven development (BDD) writes acceptance criteria as concrete,
**executable examples in business language** (Given/When/Then) so non-developers
can read them and they double as tests. It is the executable end of the
acceptance criteria a spec defines (`sota-docs-workflow` rules/05). Use it where
shared understanding across roles is the bottleneck; for developer-facing unit
logic, plain tests (`rules/02`) and property tests (`rules/06`) win.

## 8.1 What BDD actually buys — and what it doesn't

The value is the **conversation and a shared, readable definition of done** — the
"three amigos" (product, dev, test) agreeing on concrete examples *before* build.
The Gherkin file is a byproduct of that agreement, not the goal.

It does **not** buy faster unit tests, more coverage, or any value on logic with
no cross-role audience. Gherkin wrapped around a pure algorithm is overhead with
a parser attached — test it with examples/properties instead. If product and QA
never read the scenarios, you have a slow, indirect unit test: delete the
ceremony and write a plain one.

## 8.2 Given / When / Then, done right

- **One When per scenario.** Given = state/context, When = the *single* action
  under test, Then = an observable outcome. Given/When/Then **is** Arrange-Act-
  Assert (`rules/02`) in business language — the same one-logical-action rule.
- **Declarative, not imperative.** "Given a signed-in admin" — not "Given I open
  /login, type…, click Submit". Imperative, click-by-click Gherkin couples every
  scenario to the UI and makes step-definition glue explode. This is the #1
  reason teams abandon BDD.
- **Ubiquitous language.** Terms match the domain, not the code or the screen. A
  scenario is a specification a non-coder can read and confirm.

## 8.3 Outside-in: the double loop with TDD

BDD and TDD compose; they don't compete:

1. Write a **failing acceptance scenario** at the feature boundary (the outer
   loop).
2. Inside it, drive the parts with **TDD unit cycles** — red → green → refactor
   (`rules/01` §1.8) — the inner loop.
3. The acceptance scenario goes green when the feature is genuinely done.

Acceptance scenarios live at the **feature/integration layer and stay few**
(critical paths only) — the thin top of the pyramid/trophy (`rules/01`). Every
scenario costs glue and runtime; do not write one per unit.

## 8.4 Anti-patterns (why BDD gets abandoned)

- **Gherkin as a UI test script** — imperative steps driving a browser →
  brittle, unreadable, zero business value. Test behavior at the API/domain
  layer; reserve UI e2e for `rules/05`.
- **Scenario explosion** — every edge case as its own scenario. Use
  `Scenario Outline`/`Examples` sparingly and push exhaustive cases down to unit
  and property tests (`rules/06`).
- **Step-definition sprawl** — duplicated, sprawling glue. Step defs are code:
  keep them DRY and reviewed.
- **No non-dev audience** — a Gherkin layer nobody outside engineering reads is
  pure indirection. Write plain tests.

## 8.5 Tooling (neutral)

Cucumber (JVM/JS), `behave` / `pytest-bdd` (Python), Reqnroll — the maintained
successor to SpecFlow — (.NET), Godog (Go). All parse Gherkin to step
definitions; the tool is interchangeable, the discipline is not. Acceptance
criteria authored in a spec (`sota-docs-workflow` rules/05) map one-to-one to
scenarios — that mapping is the SDD↔BDD bridge.

## Audit checklist

- [ ] Do the scenarios have a genuine non-developer audience (product/QA actually
      read them)? Gherkin with only engineers in the loop → Low/Medium; consider
      plain tests.
- [ ] Are scenarios declarative (domain language), not imperative UI scripts?
      `grep -rinE 'click|type |visit |press |/login|button' features/` in step
      text → High (brittle, UI-coupled).
- [ ] One action (When) per scenario, with an observable Then? Multi-When,
      multi-outcome scenarios → Medium.
- [ ] Are acceptance scenarios kept to critical paths (few, feature-level), with
      edge cases pushed to unit/property tests? Scenario count rivaling unit-test
      count → Medium (slow, redundant).
- [ ] Are step definitions DRY and reviewed like production code? Duplicated or
      giant glue files → Low.
- [ ] Do scenarios trace to spec acceptance criteria (`sota-docs-workflow`
      rules/05) and fail before the feature exists (seen red)? Scenarios written
      after the fact, never observed failing → Medium.
- [ ] Any Gherkin wrapping pure algorithmic logic with no cross-role value? →
      Low; convert to example/property tests (`rules/06`).
