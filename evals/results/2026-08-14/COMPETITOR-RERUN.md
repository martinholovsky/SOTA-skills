# Competitor benchmark, re-run (2026-08-14/15)

**The published claim holds.** The head-to-head table was measured on 2026-07-13 and
the library has changed substantially since — four rule additions this cycle alone, the
inert-control split into `rules/10`–`12`, the router activation rewrite, principle 6.
This re-runs it to find out whether the most attackable public claim in the repo survived
that churn.

**Build:** `anthropic/claude-sonnet-4.6` · **Judge:** `anthropic/claude-opus-4.8`
(blind) · **7 cases, 1 sample, temp 0.0** · **content-only** · $10.55 · 5985 s ·
raw: [competitor-rerun.json](competitor-rerun.json)

## Result

| Arm | 2026-07-13 | **2026-08-14 re-run** | Δ |
|---|---|---|---|
| **SOTA-skills** | 99% | **98.7%** | −0.3 |
| ECC | 87% | 84.9% | −2.1 |
| awesome-cursorrules | 83% | 80.0% | −3.0 |
| claude-skills | 81% | 77.0% | −4.0 |
| unguided model | 58% | 58.2% | +0.2 |

**SOTA won 17, tied 4, lost 0** of the 21 head-to-head case comparisons — the same
record as the original run.

Per case (recall against the fixed rubric):

| case | without | sota | ECC | claude-skills | cursorrules |
|---|---|---|---|---|---|
| c1 ticket_api | 0.67 | 1.00 | 1.00 | 0.83 | 0.92 |
| c2 upload | 0.55 | 1.00 | 0.91 | 0.64 | 0.64 |
| c3 emailjob | 0.73 | 1.00 | 0.73 | 1.00 | 0.82 |
| c4 login | 0.50 | 1.00 | 0.80 | 0.70 | 0.80 |
| c5 search | 0.60 | 1.00 | 0.90 | 0.80 | 1.00 |
| c6 webhook | 0.40 | 1.00 | 0.70 | 0.60 | 0.70 |
| c7 pwreset | 0.64 | 0.91 | 0.91 | 0.82 | 0.73 |

## Why this is a reproduction and not a new experiment

- **Same build model.** `git log -S 'claude-sonnet-4.6' -- evals/run-competitors.py`
  returns exactly one commit: the original benchmark commit (#98). The default was never
  changed, so library content is the only variable.
- **Same competitor content.** All three cloned at the manifest's pinned SHAs
  (`ed38744605`, `84dc5a4f6a`, `b044f956f0`), each verified to resolve with every listed
  file present — no silent substitution of today's competitor content for the pinned
  content.
- **The unguided arm is the control, and it reproduced to 0.2 points** (58% → 58.2%).
  That arm has no library dependency, so its stability across a month is evidence the
  harness and judge did not drift underneath the comparison.

## What is *not* claimed

**The competitors did not get worse.** All three moved down 2–4 points, but this is
**n=1 per arm at temp 0**, and the original was too. A 2–4 point move on a 11–12 item
rubric is one or two checklist items on one case. Nothing here supports a claim that any
competitor regressed; the defensible statement is that **the ranking and the gap are
stable across a month of library change**.

## Incident: a partial artifact reached `main`

While this run was still executing, a `git add -A` in an unrelated docs commit swept up
`competitor-rerun.json` mid-write, and it merged (PR #221). The committed file was
**valid JSON containing 2 of 7 cases**, with `means` recomputed over just those two —
`ECC` read **0.954** against a true **0.849**. Nothing in the artifact said it was
partial.

The runner saves after every case on purpose (crash-safety), so the fix is not to stop
saving but to make the artifact state its own status: it now writes `cases_done`,
`cases_total` and `complete`. A reader or scorer can refuse an incomplete file instead of
averaging it.

Two lessons worth keeping, both this repo's own doctrine turned on itself: **a valid,
plausible-looking artifact is the dangerous failure**, not a corrupt one — and
**`git add -A` while a job writes into the tree is a way to publish a half-measurement.**
