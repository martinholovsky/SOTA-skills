# 05 — E2E & UI Testing

The most expensive tests you own: highest fidelity, highest run cost, highest
flake potential, slowest feedback. Everything here is about buying maximum
confidence with a minimum number of them.

## 5.1 A small, curated, critical-path suite

E2E exists to answer one question: **"is the system, wired together for real,
able to do the things the business cannot survive losing?"** Not to re-verify
logic ([`rules/01`](01-strategy-and-shape.md) §1.3 — push cases down).

- **Enumerate the money paths and write them down**: sign-up → first value,
  log in, search → view, add to cart → pay, the one admin action that
  unblocks customers. For most products that's 5–15 flows. That list — not
  organic accretion — defines the suite.
- **Every e2e test needs a justification** for why no lower layer can give
  the same confidence. "The unit test exists but I want to be extra sure" is
  not one; duplicate coverage at 1000× run cost is negative-ROI.
- **Edge cases live below.** E2E does one happy path + at most the one or two
  failure paths users actually hit (declined card, wrong password). Validation
  matrices, permission combinations, boundary values: API/integration layer.
- **Budget the suite, not just the test**: a wall-clock cap for the whole e2e
  stage (e.g. ≤10 min parallelized, pre-merge; anything beyond runs
  post-merge/nightly). A cap forces the prioritization conversation that
  "just add another test" avoids. See [`rules/07`](07-suite-health-and-ci.md) §7.3.

## 5.2 Selector strategy: roles and test ids, never structure

Selectors are the contract between test and UI. Structural selectors (CSS
chains, XPath, nth-child) break on every markup change and encode nothing
about user intent.

Priority order (Playwright's and Testing Library's shared guidance):

1. **Role + accessible name** — `getByRole("button", { name: "Pay now" })`.
   Matches what assistive tech sees, survives redesigns, and fails when
   accessibility breaks — a free a11y check.
2. **Label/placeholder/text** for form fields and content the user reads.
3. **Test id** (`data-testid`) when role-based lookup is genuinely ambiguous
   or the element isn't user-facing. Test ids are an explicit testing
   contract: stable across refactors by team convention.
4. **Never**: CSS class chains, XPath positional paths, auto-generated
   classnames (`.css-1x2y3z`), DOM depth (`div > div:nth-child(3) span`).

```ts
// BAD — breaks on any markup/styling refactor, meaningless on failure
await page.click("#root > div.app > div:nth-child(2) button.btn-primary");

// GOOD — intent-revealing, redesign-proof, a11y-enforcing
await page.getByRole("button", { name: "Pay now" }).click();
```

## 5.3 Auto-waiting, never sleeps

Modern drivers (Playwright; Cypress) auto-wait for elements to be actionable
(visible, stable, enabled) before acting, and have web-first/retrying
assertions that poll until timeout. Use that machinery; every hard wait is a
flake (too short under load) and a tax (too long everywhere else).

- Banned: `page.waitForTimeout(...)`, `cy.wait(3000)`, `sleep` in any form.
- Wait **on conditions**: the retrying assertion on the UI state you need
  (`await expect(page.getByText("Order confirmed")).toBeVisible()`), a
  specific response (`waitForResponse`) when the UI gives no signal, or an
  emitted event.
- **Assertions must target settled end-state**, not transient state — racing
  a spinner ("expect loading indicator visible") is inherently flaky.
- If an element is never "actionable" without a manual wait, the app has a
  real UX/race bug — file it instead of papering over it (force-clicks and
  `{force: true}` hide bugs users will hit).

## 5.4 Page objects / screenplay: abstraction with limits

Raw selector soup duplicated across tests means one UI change = fifty test
edits. Standard fix: **page objects** — one module per page/component
exposing intent-level methods (`loginAs(user)`, `addToCart(sku)`), owning all
selectors for that surface.

- Page objects expose **actions and queries, not assertions about business
  outcomes** — assertions stay in tests where the behavior is specified.
  (Cheap state queries like `isLoggedIn()` are fine.)
- Keep them flat: a page-object inheritance tree is the same maintenance trap
  with extra steps. Compose components (HeaderComponent, CartWidget) instead.
- **Screenplay pattern** (actors/tasks/questions) is the heavier alternative
  — worthwhile when many personas and reusable workflows dominate
  (`actor.attemptsTo(Checkout.withSavedCard())`); overkill for a 15-test
  critical-path suite. Choose one pattern; mixing both confuses everyone.
- App-level shortcuts beat UI grinding for *arrangement*: log in via API/
  session cookie, seed data via API, then test the UI behavior you actually
  came for. UI-driving the arrange phase makes every test pay the login
  flow's cost and flake surface. The login flow itself gets its own one test.

```ts
// BAD — 30s of UI-driven arrange before the 3s of behavior under test
test("user can cancel a subscription", async ({ page }) => {
  await page.goto("/signup");
  await page.getByLabel("Email").fill(email);        // arrange via UI
  // ...12 more lines of signup, email verify, plan selection...
  await page.getByRole("button", { name: "Cancel plan" }).click();
  await expect(page.getByText("Plan cancelled")).toBeVisible();
});

// GOOD — arrange via API/fixtures, act+assert via UI
test("user can cancel a subscription", async ({ page, api }) => {
  const user = await api.createUser(aUser().withActivePlan("pro"));
  await page.context().addCookies(await api.sessionFor(user));

  await page.goto("/account/billing");
  await page.getByRole("button", { name: "Cancel plan" }).click();

  await expect(page.getByText("Plan cancelled")).toBeVisible();
  expect((await api.getSubscription(user)).status).toBe("cancelled");
});
```

## 5.5 Visual regression: powerful, easy to drown in

Screenshot-diff testing catches what DOM assertions can't (CSS regressions,
layout breakage, z-index disasters) and false-positives on everything else
(font rendering, animations, anti-aliasing, real data).

Use it surgically:

- **Component-level snapshots in a controlled renderer** (component test
  runner / Storybook-style isolation) over full-page production screenshots
  — smaller diff surface, fewer moving pixels.
- Stabilize or mask everything dynamic: freeze time/animations, fixed
  viewport and fonts, mask user data regions. Re-baseline only through
  review, never auto-accept ([`rules/02`](02-test-design-quality.md) §2.8 applies — a baseline update IS
  a contract change).
- Cap the count. A thousand screenshot tests with a 2% false-positive rate
  is 20 human reviews per run; teams go blind and click approve. A handful
  of layout-critical pages/components, or a managed diff service with good
  triage, or don't.

## 5.6 Flake economics and the deletion discipline

E2E flakes are not a nuisance; they're a tax on every merge and a rot that
destroys signal. The economics (full policy in [`rules/07`](07-suite-health-and-ci.md) §7.1):

- Do the math on false-failure rates: per-run suite flake probability is
  `1 - (1 - p)^n`. Twenty tests at p=1% each → ~18% of runs fail falsely;
  at 200 tests → ~87%. Engineers learn to hit retry — at which point the
  suite no longer gates anything; it just delays merges. Per-test p must
  shrink as the suite grows, which is why big e2e suites are self-defeating.
- **Retry-on-failure is diagnostic, not a fix**: one auto-retry with both
  attempts logged is acceptable while the root cause is being fixed; a test
  living on retries is a quarantine candidate with a deadline.
- **Delete e2e tests when**: the flow is covered at a lower layer and the
  test has caught nothing real in N months; the flake cost exceeds the
  failure-detection value; the feature's risk has moved (flow redesigned,
  usage near-zero); or its maintenance owner is gone and nobody can say what
  it proves. Record the rationale in the deleting commit.
- Never delete a test *because it is failing* without root-causing — a
  consistently red e2e test is more often a real bug than a bad test.

## 5.7 E2E suite mechanics

- **Independent and parallel-first** ([`rules/02`](02-test-design-quality.md) §2.5): every test creates
  its own user/tenant/data with unique identifiers; no test reads another's
  state; suite passes shuffled. Serial e2e suites become the CI long pole.
- **Run against ephemeral or production-like environments** ([`rules/04`](04-integration-contract-system.md)
  §4.7) with seeded, version-controlled data — not against shared staging
  where someone else's demo data changes your test's world.
- **Artifacts on failure are mandatory**: trace/video/screenshot + console +
  network log wired into CI. An e2e failure that can only be debugged by
  rerunning locally costs hours per incident; traces cut it to minutes.
- Tag a ~1-minute smoke subset (login + one money path) for deploy gates and
  production canary checks; the full suite runs pre-merge or post-merge per
  your budget.

## Audit checklist

- [ ] Is there a written critical-path list, and does the suite map 1:1 to
      it? Suite >~2× the flow list or no list at all → Medium (accretion).
- [ ] Suite runtime vs budget: e2e stage wall-clock >15 min pre-merge →
      Medium; engineers routinely skipping/bypassing it → High.
- [ ] Structural selectors? Grep:
      `nth-child|nth-of-type|xpath=|//div|css=.*>.*>|\.css-[a-z0-9]|querySelector\(` in e2e specs → Medium each cluster; suite-wide pattern → High.
- [ ] Hard waits? Grep: `waitForTimeout|cy\.wait\([0-9]|sleep\(|page\.wait_for_timeout|Thread\.sleep` in e2e code → High each.
- [ ] Forced interactions hiding bugs? Grep `force:\s*true|{force}|dispatchEvent\(.*click` → Medium, investigate each.
- [ ] Assertions in page objects? Grep page-object dirs for
      `expect|assert|should` → Low–Medium (move to tests).
- [ ] Does each test UI-drive its own login? Grep specs for repeated
      `getBy.*(password|email).*fill` arrange blocks → Medium (use API/session
      arrangement; keep one login test).
- [ ] Test data isolation: unique-per-test users/tenants, or shared accounts?
      Grep for hardcoded credentials/emails reused across specs
      (`test@example.com` in >3 files) → High (parallel-unsafe).
- [ ] Auto-retry config: global retries enabled with no quarantine process or
      flake tracking → High (signal destroyed silently).
- [ ] Failure artifacts: are traces/videos/screenshots captured in CI on
      failure? No → Medium.
- [ ] Visual tests: baseline updates reviewed (check recent
      `git log -- '**/*.png' '**/__screenshots__/**'` for bulk auto-updates)
      → High if rubber-stamped; unmasked dynamic regions → Medium.
- [ ] When did the e2e suite last catch a real bug? No one knows and flakes
      are weekly → recommend the deletion review (5.6).
