# Coverage & depth audit — business-logic flaws (2026-08-13)

**This is a coverage claim, never a detection claim.** The library's audit lift is
**+0.00 across every instrument** (eight of them, `evals/results/RESULTS.md` §1),
and the one planted business-logic defect in the cross-file set (`p6`,
[REPO-AUDIT](../evals/results/2026-07-13/REPO-AUDIT.md)) was found by the
**unguided** arm on both models. Nothing below claims the library detects
business-logic flaws better than an unguided model. It does not measure anything.

## Falsification criterion, fixed before the audit began

> If every WSTG-BUSL sub-test and API6:2023 maps to a library location scoring
> **≥3** (BUILD rule *plus* an item in that file's `## Audit checklist`), and the
> routing trace loads those files for prompts a user would actually type, then
> coverage is adequate — report "no edits warranted" and change nothing.

**Met, for content — 10 of 10 sub-tests reach ≥3 once refutation is applied.**
The two content gaps this audit first drafted were **both killed by the refuter**,
with evidence I then re-verified line by line (below). The falsification criterion
did its job: the only edit this audit warrants is the **routing** one, because
routing was the only part that actually failed.

That is the result. An earlier draft of this file proposed two rules edits; they
are not in this change, because the claims behind them did not survive.

## Sources (fetched 2026-08-13)

| Source | URL | Note |
|---|---|---|
| OWASP WSTG, Business Logic Testing | `owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/10-Business_Logic_Testing/` | **10** sub-tests, not 9 |
| WSTG IDs (authoritative) | `github.com/OWASP/wstg` → `document/4-Web_Application_Security_Testing/10-Business_Logic_Testing/` | IDs read from the files themselves |
| OWASP API Security Top 10 2023, API6 | `owasp.org/API-Security/editions/2023/en/0xa6-unrestricted-access-to-sensitive-business-flows/` | prevention = business layer + engineering layer |
| CWE-840 Business Logic Errors | `cwe.mitre.org/data/definitions/840.html` | category, **prohibited for mapping**; children below |

**The task's own recollection was wrong and is corrected here:** it stated 9
sub-tests (BUSL-01..09). There are **10**. `WSTG-BUSL-10 Test Payment
Functionality` exists and was missing from that list — and it is one of the two
gaps this audit found. The instruction to verify rather than trust recall is what
surfaced it.

CWE-840's children, read from the primary source: CWE-283 Unverified Ownership ·
CWE-639 Authorization Bypass Through User-Controlled Key · CWE-640 Weak Password
Recovery · CWE-708 Incorrect Ownership Assignment · CWE-770 Allocation of
Resources Without Limits · CWE-826 Premature Release of Resource · CWE-837
Improper Enforcement of a Single, Unique Action · CWE-841 Improper Enforcement of
Behavioral Workflow.

## Taxonomy → library map, with depth

Depth: 0 absent · 1 named only · 2 BUILD rule · 3 + audit-checklist item ·
4 + concrete detection method (grep/command/test or BAD/GOOD pair).

| ID | Sub-test | Covered at | Depth |
|---|---|---|---|
| BUSL-01 | Business Logic Data Validation | `sota-code-security/rules/01-input-injection.md:26-27` semantic/cross-field invariants (`checkout` after `checkin`); test in `sota-testing/rules/09:102` | **4** |
| BUSL-02 | Ability to Forge Requests | `sota-code-security/rules/01-input-injection.md:203` explicit DTOs; checklist `:277`; `sota-api-design/rules/07:208` API3 mass-assignment | **3** |
| BUSL-03 | Integrity Checks | `sota-code-security/rules/07-data-exposure.md:130-131` server-side re-derivation of price/subtotal/tax/total/balance/discount/quota | **4** |
| BUSL-04 | Process Timing | `sota-async-concurrency/rules/02:68,213` check-then-act/TOCTOU + audit sweep; `sota-code-security/rules/06:183-199` race-driven logic bypass with atomic-claim SQL | **4** |
| BUSL-05 | Function-Use Limits | `sota-code-security/rules/03-authorization.md:91-92` one-time operations marked consumed; `rules/06:198` atomic claim | **4** |
| BUSL-06 | Circumvention of Work Flows | `sota-code-security/rules/03-authorization.md:89-94` state machine, reject out-of-order, expire abandoned state, never store position client-side | **4** |
| BUSL-07 | Defenses Against Application Misuse | out-of-sequence/replay: `sota-code-security/rules/03:89-92` + test spec `sota-testing/rules/09:99` + atomic-claim SQL `rules/06:191-197`; detect-and-respond: `rules/07-data-exposure.md:96-99` (log authz denials/validation rejections, **alerting on anomalies**) + checklist `:230`; abuse signals audit-logged incl. **rate-limit and quota trips** `sota-api-design/rules/07:152`; escalating friction `rules/02-authentication.md:213`; non-human clients + step-up decision table `sota-mobile/rules/04:94-99`; router non-negotiable (a) `sota/SKILL.md:68` | **4 / 3** |
| BUSL-08 | Upload of Unexpected File Types | `sota-code-security/rules/09:246` magic-byte typing, polyglot rejection, AV scan | **4** |
| BUSL-09 | Upload of Malicious Files | same, plus `:81-99` archive bombs, `:167` polyglots | **4** |
| BUSL-10 | Payment Functionality | price/total re-derivation `rules/07-data-exposure.md:130-131`; **money as integer minor units** `sota-javascript-typescript/rules/02:183`, `sota-databases/rules/01:232`, `sota-api-design/rules/01:285`; **rounding/allocation rule** `js-ts rules/02:191` + grep starter `:244`; negative/zero amounts `rules/06:226` + test `sota-testing/rules/09:102`; **insufficient-funds bypass** `rules/06:183-197` (BAD/GOOD atomic-claim SQL) + grep `:218`; refund authz `rules/03:82`; capture consumed once `rules/03:91`; double-charge/idempotency `sota-api-design/rules/01:302-303`; currency-matches-account invariant `rules/01-input-injection.md:28`; PCI tokenization `sota-privacy-compliance/rules/02:110-124` | **4** |
| API6:2023 | Sensitive Business Flows | `sota-api-design/rules/07:211` cost-weighted limits, flow throttles, server-side flow order | **3** |

The task asked specifically whether `sota-testing` rules/09 §4's business-logic
set silently drops sub-tests. It does not drop the ones it claims: its five items
(`:99-104`) map cleanly onto BUSL-06, BUSL-01/03, BUSL-05, BUSL-01 and BUSL-04.
It has no item for BUSL-07 or BUSL-10 — consistent with the two findings below.

## Findings

One finding survived. Two were refuted and are recorded so they are not re-raised.

```
skills/*/SKILL.md (frontmatter descriptions, all 41) | The class was unreachable by its own name: "business logic", "business flow", "logic flaw", "checkout", "refund" and "state machine" appeared in ZERO descriptions, and "workflow" appeared in three — sota-detection-engineering, sota-devsecops, sota-docs-workflow — all the WRONG sense (SOC workflow, CI workflow, docs workflow), so the one word a user is likely to type routes actively away from the coverage | Medium | trivial | FIXED in this change: "business logic" appended to sota-code-security's description (998 -> 1014 of the 1024 cap)
```

Severity **Medium**, deliberately: this is guidance reachability, not a live
vulnerability. The content was always there; nothing pointed at it.

### Refuted — do not re-raise

Both were sent to an independent fresh-context pass prompted to **kill** them,
defaulting to REFUTED. Both died, and I re-verified the decisive citations myself
rather than accepting the verdict.

**BL-1 · "no BUILD rule or probe for BUSL-07 application misuse" — REFUTED.**
The concept is covered under three other names: API6 flow-specific throttling
(`sota-api-design/rules/07:211`, explicitly distinguished from generic rate
limiting), security-event logging with **alerting on anomalies** including
authz denials, validation rejections and rate-limit/quota trips
(`rules/07-data-exposure.md:96-99` + checklist `:230`, `sota-api-design/rules/07:152`),
escalating friction under abuse on a non-login flow
(`rules/02-authentication.md:213`), and a server-side verified decision table for
non-human clients on promotions/scraping-prone endpoints
(`sota-mobile/rules/04:94-99`). Residual: no `WSTG-BUSL-07` identifier and no
single consolidated "application-layer intrusion detection" section. That is a
**naming/consolidation** observation, not a coverage gap, and consolidating for
its own sake is the kind of churn `docs/CONVENTIONS-LEDGER.md` argues against.

**BL-2 · "BUSL-10 payment covered only by price re-derivation" — REFUTED, and the
refuter's own residual then fell too.** Integer minor units in three skills,
rounding/allocation with a committed grep starter
(`sota-javascript-typescript/rules/02:191,244`), negative/zero amounts
(`rules/06:226`), insufficient-funds bypass with a BAD/GOOD atomic-claim SQL pair
and a grep (`rules/06:183-197,218`), refund authorization (`rules/03:82`),
capture-consumed-once (`rules/03:91`) and idempotent double-charge protection
(`sota-api-design/rules/01:302-303`). The refuter proposed "currency mismatch"
as a surviving standalone gap; that is **also wrong** —
`rules/01-input-injection.md:28` already carries *"currency matches account"* as a
worked cross-field business invariant. The refuter missed it, which is why a
refutation gets verified too.

## Search methods used (per operating principle 3, for the absence claims)

Three independent methods, all over `skills/**`:
1. **The term**: `business[- ]logic` — 40 hits, all read.
2. **The mechanism**: `coupon|voucher|promo`, `refund|chargeback|price`,
   `negative (quantity|amount)`, `state machine|workflow (position|order|state)`,
   `one-time|single-use|consume`, `quota|cost-weighted`, `check-then-act|TOCTOU`,
   `idempoten`, `abuse case`, `re-derive|server-side (price|total)`.
3. **The defence**: `lockout|velocity|too many|tarpit|honeytoken|step-up`,
   `currency|rounding|integer cents|negative amount`.

Every description was parsed with a YAML-aware reader (41 of 41 parsed) rather
than grepped, because a `grep` over `SKILL.md` matches body text and would have
produced a false negative on the routing finding.

## What was NOT checked

- **No eval, no measurement.** Depth scores are a reading of the text, not a
  demonstration that anything is applied.
- **`sota-databases`, `sota-architecture` and the language skills** were searched
  by term and mechanism but not read end-to-end for implicit coverage.
- **BUSL-02** scored 3 on the mass-assignment/DTO path only; the "forge a request
  the UI never offers" case (hidden fields, disabled options, undocumented
  parameters) was not separately traced.
- **API6's engineering layer** — device fingerprinting, human detection, Tor/proxy
  blocking — was checked only in `sota-api-design`; whether it belongs there or in
  `sota-detection-engineering` is unresolved and no edit is proposed.
- The CWE children were mapped by name, not by tracing each to a file:line.
