# Pre-registration — ROADMAP item 21, the refreshed freshness set

**Written and committed BEFORE the run**, per operating principle 0 and the precedent
set by [item 20's pre-registration](PREREGISTRATION.md).

## What is being tested

`cases/freshness-2026.jsonl` — 10 cases, authored 2026-08-25. Item 20 showed the
original 32-case set is **ageing**: 8 of its facts moved inside `claude-sonnet-5`'s
training window in four months, dropping the measured lift +0.53 → +0.30 while the
with-library arm *rose* (0.97 → 0.99). Item 21 asks whether re-authoring restores it.

**The selection rule was fixed before any model ran** (and is written into the case
file's header): the fact is stated in the library with a checkable marker; its primary
source was published or changed Sept 2025 – Aug 2026; it is not already an answer in the
old set. **Cases were not chosen by model performance.** That shortcut was available —
10 of the old 32 still discriminate — and was deliberately not taken, because selecting
cases a model fails guarantees a large lift and measures nothing.

Every one of the 10 facts was verified against its primary source at authoring time
(rfc-editor.org, postgresql.org, github.com/microsoft/TypeScript, php.net, doc.rust-lang.org,
developer.apple.com, github.com/prometheus). One candidate was **dropped** because the
library does not state it (PostgreSQL 18 as latest stable major). One library claim was
found **stale** in the same pass (Cilium "1.19, verified current line" — the GitHub API
gives v1.20.1, published 2026-08-18) and fixed separately; **no case was authored on it**,
because a set must not measure content written alongside it.

## Protocol

`evals/run-clean.py --cases evals/cases/freshness-2026.jsonl --model anthropic/claude-sonnet-5
--samples 3 --temp 0.7` — identical to the item-20 protocol, so the two are comparable.

## Predictions and falsifiers

**Predict: the lift is restored** — the erosion in item 20 was the *set* ageing, not the
library weakening, so a set built from recent facts should read close to the original +0.53.

- without-arm **≤ 0.55** (below the aged set's 0.69, since these facts are newer)
- with-arm **≥ 0.90**
- lift **≥ +0.35**
- **FALSIFIED IF lift < 0.20.** That would mean re-authoring does *not* restore the lift,
  and the "ageing instrument" explanation for item 20 is wrong — the more interesting
  outcome, and a real possibility: several of these facts (RFC 9842 Sept 2025, Prometheus
  3.8.0 Nov 2025) may already sit inside the cutoff.
- **SEPARATE alarm, not to be confused with the above:** with-arm **< 0.85** means the
  library does not carry these facts as reliably as authoring-time verification suggested
  — a library problem, to be reported as such and never folded into the lift.

**Granularity, stated up front:** 10 cases, so **one case is 0.10**. This set is coarser
than the 32-case one and cannot resolve small differences; it will be reported with that
caveat and is not a replacement for the original series, which is kept for continuity.
