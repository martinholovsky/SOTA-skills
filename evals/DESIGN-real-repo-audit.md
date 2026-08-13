# Design — the real-repo audit eval (candidate selected, nothing measured yet)

**Status: design + verified candidate. No run, no number, no lift.** Running it
costs money (roadmap item "paid eval runs") and needs an explicit go. Nothing in
this file may be cited as a result.

## Why this exists

The AUDIT arm reads **+0.00 across seven instruments and three designs**
(`results/2026-07-30/UNSCOPED-AUDIT.md`, `DEAD-PATH.md`). Two of those designs
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

1. **The defect is an absence.** Nothing is wrong on the line; a check that
   should exist does not. Pattern-based SAST is structurally poor at this, and
   it is the exact claim `sota-code-security` rules/03 makes.
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

**Cost estimate: unverified.** No token count has been measured for an agentic
audit of a repo this size; do not quote one until a dry run produces it.
