# Design — the real-repo audit eval (RUN 2026-08-13/14; question closed)

**Status: EXECUTED. Results supersede this file's planning language.** The eval was
run against `goharbor/harbor` v2.5.1 over 16 real BOLA sites: recall **15/16 = 15/16**,
precision **1.00 = 1.00** over 59 blinded findings, adjudicator controlled at 4/4 —
**+0.00 on both**, half the run discarded for a contamination vector the design had not
anticipated. Read the outcome, not the plan:
[results/2026-08-13/REAL-REPO-AUDIT.md](results/2026-08-13/REAL-REPO-AUDIT.md).

This file is kept for its **method** — subject selection, the precondition that killed
the previous candidate, and the blinding scheme — all of which held up and are reusable.
Its forward-looking sentences ("nothing measured yet", "needs an explicit go") are
historical. **Do not build a tenth accuracy instrument**: audit recall and precision are
both closed at nine instruments across four designs, and only a different *dependent
variable* (time-to-find, report usability, reach for a non-expert) remains untested.

## Why this existed

At design time the AUDIT arm read **+0.00 across seven instruments and three designs**
(`results/2026-07-30/UNSCOPED-AUDIT.md`, `DEAD-PATH.md`) — now nine and four, with this
eval supplying the fourth design and the last two instruments. Two of those designs
used *synthetic* fixtures, and on 2026-08-03 the synthetic route was ruled out
twice: a planted defect is a **deviation from generated filler**, and agents find
deviations structurally, without security reasoning — the bare arm scored 6/6.
What is left is a **real repository at a real vulnerable commit**, where the
defect is indistinguishable from the code around it because it *is* the code
around it.

## The precondition that killed the last candidate

Check this **first**, before reading a line of the candidate's source:

> Is the vulnerable commit actually in the public history?

An earlier candidate (2026-08-11, [ADOPTION-LOG](../docs/ADOPTION-LOG.md)) had an
exemplary written account of its own pre-fix defect and a public repo — but 18
commits starting from a squashed `Initial release`. The defect existed only in
the narrative. Cost of the check: one `gh api` call. Cost of skipping it: reading
an entire architecture before discovering there is nothing to audit.

## Selected candidate — Harbor at v2.5.1

[goharbor/harbor](https://github.com/goharbor/harbor), CNCF graduated, Go,
Apache-2.0, ~259 MB, 29k stars *(verified via the GitHub API, 2026-08-13)*.

**Vulnerable state:** tag `v2.5.1` (`b0506782b4`). **Fixed state:** `v2.5.2`
(`6688271792`). Both tags resolve in public history; `v2.4.2` → `v2.4.3` is the
parallel window on the older line. The fix window is **17 commits / 33 files** —
small enough to extract ground truth by hand and verify every item.

### Ground truth — 8 advisories, 5 CVEs, one class, published the same day

All published **2022-08-29** (verified: `distinct_cves: 5`, `advisories: 8`,
single publication date), every one of the form *"fails to validate the user
permissions when …"*. Three advisories share CVE-2022-31666 and two share
CVE-2022-31671, so **count recall over the 8 advisories, not the 5 CVE IDs** —
they are 8 distinct code sites:

| GHSA | CVE | Severity | Surface |
|---|---|---|---|
| GHSA-3wpx-625q-22j7 | CVE-2022-31671 | high | p2p preheat policy — update |
| GHSA-jf8p-3vjh-pq94 | CVE-2022-31666 | high | webhook policy — view |
| GHSA-8hwq-5f22-jfr3 | CVE-2022-31666 | high | webhook policy — update |
| GHSA-wqpf-jx24-7hmp | CVE-2022-31666 | medium | webhook policy — delete |
| GHSA-3637-v6vq-xqqw | CVE-2022-31670 | high | tag retention policy — update |
| GHSA-8c6p-v837-77f6 | CVE-2022-31669 | medium | tag immutability policy — update |
| GHSA-xx9w-464f-7h6f | CVE-2022-31667 | medium | robot account — update |
| GHSA-q76q-q8hw-hmpw | CVE-2022-31671 | medium | job execution log — read |

The fixes land in six handler files under `src/server/v2.0/handler/`
(`preheat.go` +115, `retention.go` +92, `notification_policy.go` +49,
`immutable.go` +31, `robot.go` +24, `notification_job.go` +24) and they add
exactly what was missing — verified in the patch, not inferred from the filename:

```go
// v2.5.2, src/server/v2.0/handler/notification_policy.go
+ if err := n.RequireProjectAccess(ctx, projectID, rbac.ActionRead, rbac.ResourceNotificationPolicy); err != nil {
```

plus new `requirePolicyAccess` / `requireRuleAccess` helpers in the preheat and
immutability handlers.

### Why this candidate and not a memory-safety CVE

1. **The authorization check is present, passes, and authorizes the wrong
   object.** *(Corrected 2026-08-13 — the first version of this file said "a
   check that should exist does not". That was wrong, and reading the v2.5.1
   tree rather than the filenames is what caught it.)* At v2.5.1 the handlers
   already call `requireAccess(ctx, p, rbac.ActionUpdate)`; `retention.go` has
   11 checks for 11 exported handlers and `immutable.go` 4 for 4. What is
   missing is the **binding of the object to the tenant** — that the policy,
   execution or robot named in the URL actually belongs to the project the
   caller was just authorized against. The v2.5.2 patch adds exactly that:

   ```go
   // v2.5.2, notification_policy.go — the whole defect, stated positively
   + if projectID != l.ProjectID {
   +     return errors.NotFoundError(fmt.Errorf("project id:%d, webhook policy id: %d not found", projectID, policyID))
   + }
   ```

   Counting added lines across the six handlers: **34 object-binding checks vs 1
   project-access check**. So this is OWASP **API1:2023 Broken Object Level
   Authorization**, and it is a *silent control* in the `rules/10` sense — the
   guard runs, returns nil, and everyone downstream believes authorization
   happened. A grep for "is there an authz call on this handler" answers **yes**
   on every vulnerable site. That makes it a far better subject than a missing
   check would have been: the only way to find it is to reason about *which
   object* was authorized, which is the claim `sota-code-security` rules/03 and
   `sota-api-design` rules/07 actually make.
2. **Eight items, not one.** Recall over a set is a measurement; finding one
   planted bug is an anecdote. It also permits partial credit and a per-item
   refutation pass.
3. **One class, many surfaces.** An arm that finds the webhook handler and stops
   is visibly different from one that sweeps *every* handler for the missing
   check — which is precisely the "did you enumerate the population?" discipline
   in `rules/12` §3.
4. **It exercises the library broadly**, which no previous audit instrument did:
   `sota-golang` (handler idioms), `sota-api-design` rules/07 (tenant isolation
   on every endpoint), `sota-code-security` rules/03 (authorization) and
   rules/12 §3 (per-target verification), and `sota-devsecops` rules/08 — Harbor
   *is* a registry, so the registry-security rules apply to the subject itself.

### Known biases to control for, stated before the run

- **Contamination.** Harbor is public, popular, and these CVEs predate every
  candidate model's cutoff. A model may recall them. Mitigations: run the bare
  arm first; ask both arms for *file:line + the missing check*, not the CVE ID;
  score an item only when the location is right; and treat any arm that names a
  CVE number without the location as **contaminated, not skilled** — record it.
- **Scope framing leaks the answer.** Pointing an arm at
  `src/server/v2.0/handler/` telegraphs the population. Scope must be the
  service (or the repo) with the handler directory merely inside it.
- **Ground truth is what the patch changed**, not what an auditor thinks should
  change. Extra findings are neither credited nor penalised — record them
  separately as a precision signal, since a 40-finding report that includes all
  8 is not the same result as an 8-finding report.
- **v2.5.1 contains other, unrelated defects** fixed later. Recall is measured
  against the 8; anything else found is out-of-scope, not a false positive.

## What is still unbuilt

1. A runner (`run-real-repo-audit.py`) that pins the subject at
   `b0506782b4`, bounds the scope, and declares its denominator per the harness
   conventions in [README](README.md).
2. A ground-truth file: 8 items as `{ghsa, cve, file, symbol, missing_check}`,
   extracted from the v2.5.1→v2.5.2 patches.
3. The arms: bare vs library-guided, ≥3 samples each — one sample of an agentic
   audit is noise.
4. A decision, **written before the run**, on what result would falsify the
   claim. The seven previous instruments all read +0.00; the honest prior is
   that this one does too, and the design is worth running because it is the
   only untried shape left, not because it is expected to win.

## Dry run, 2026-08-13 — what ran and what did not

**The model arm did not run.** The stored `OPENROUTER_API_KEY` returns
`HTTP 401 {"error":{"message":"User not found."}}` on both `/api/v1/credits` and
`/api/v1/key`. No sample was taken, so there is still no number of any kind.

*Instrument note, in the spirit of `rules/12` §2:* the first credit check parsed
the response with `.get('data',{})` and printed **"remaining: $0.00"** — turning
an authentication failure into a plausible balance. A reader would have concluded
"out of credit" and topped up an account that was never the problem. The parser
was the thing that failed, and it failed *quietly and legibly*, which is the
whole failure mode this library documents. Any replacement must assert the HTTP
status before reading a field.

**What was measured instead** — the subject at the pinned commit
`b0506782b4`, `*.go` excluding `*_test.go`, token column is `bytes / 4` and is an
**estimate**, not a measurement:

| Scope | Files | LOC | Bytes | ~Tokens |
|---|---|---|---|---|
| `src/server/v2.0/handler` | 55 | 9,576 | 300,758 | ~75k |
| `src/server` | 123 | 15,017 | 472,592 | ~118k |
| `src/controller` | 109 | 16,860 | 507,716 | ~127k |
| `src` (whole) | 5,431 | 1,641,671 | 54,139,135 | ~13.5M |

Three design consequences fall straight out of those numbers:

1. **Whole-`src` cannot be read.** At ~13.5M estimated tokens it exceeds every
   context window on the market, so the audit is necessarily **agentic and
   selective** — which is the shape the roadmap always said was the real
   frontier, now with a number attached.
2. **`src/server` + `src/controller` ≈ 245k estimated tokens** read
   exhaustively. That fits a 1M-context model in a single pass and does not fit
   a 200k one, so the arms must either be matched on context size or the scope
   bounded identically for both. Record which.
3. **The handler directory alone (~75k) is too small to be the scope.** It
   contains the answer set; pointing an arm at it telegraphs the population
   (see the bias note above). Scope at `src/server` or wider.

**Still unmeasured:** actual token consumption of an agentic run (input depends
on what the arm chooses to read), wall-clock, and dollar cost. A single sample
produces all three, and needs a working key.
