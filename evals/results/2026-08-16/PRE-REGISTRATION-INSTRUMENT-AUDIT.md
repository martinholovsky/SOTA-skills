# Pre-registration — instrument audit (written 2026-08-16, before any finding)

This file is committed **before** the auditors report. If it is edited after the
findings land, the git history will show it, and the prediction is void.

## Why this audit exists

A session on 2026-08-14/15 produced an unusual number of self-inflicted measurement
failures. Their distribution is the hypothesis:

| Defect | Where it lived |
|---|---|
| Null completion counted as a successful call (5 runners) | `evals/*.py` |
| Partial artifact written with no completeness marker; 2-of-7 means merged to `main` | `evals/*.py` |
| "15 probes" / "exactly 500 lines" stale | `AGENTS.md` |
| A falsified hypothesis still offered as the explanation for audit +0.00 | `docs/WHY-IT-WORKS.md` |
| zsh word-splitting stated as universal; "no linter for zsh" overclaim | `skills/` |
| Three probe false-positives, a scorer racing a file mid-write, HTTP 401 rendered as `$0.00` | ad-hoc shell, not in the repo |

## The structural claim being tested

Enforcement in this repo is aimed at content, not at the instruments that measure
content (counted at `cc1529b`):

| Area | Size | Invariants gating it |
|---|---|---|
| `skills/**` | 298 files, 61,960 lines | 15 of 16 |
| `evals/*.py` | 67 files, 4,692 lines | **1** (#13, scoreboard sample cells) |
| `scripts/*.sh` | 11 files, 3,031 lines | **0** |

## Prediction

**The highest-severity findings will be in `evals/` and `scripts/`, not in `skills/`.**

Concretely, before seeing any result:

1. At least one more runner computes a summary over a partial or filtered set, or
   writes an artifact that cannot be distinguished from an interrupted run.
2. At least one guard in the repo has never been watched to fail, and the
   negative-control harness does **not** cover every invariant.
3. Shell findings will be about *gates failing to block*, not style.

## What would falsify it

- Auditors return **no** High/Critical findings in `evals/` or `scripts/` → the
  instruments are fine and this audit was the wrong scope; say so.
- The most severe finding is in `skills/` content → the hypothesis is backwards, and
  the enforcement asymmetry is not where the risk is.
- Every guard already has a probe and the negative-control coverage is complete →
  prediction 2 is wrong; record it.

An audit that cannot come back empty is theatre. This one can: the honest outcome
"the instruments are sound, the failures were operator error" is available and would
be reported as the result.

## Method

Three independent auditors at commit `cc1529b`, each loading the matching `sota-*`
skills: (a) `evals/*.py` for silent-failure/dead-path, (b) `evals/*.py` +
`scripts/*.sh` for unproven and inert guards, (c) `scripts/*.sh` for shell safety.
Every finding must cite `file:line` verified by reading. Critical/High findings get
an independent refutation pass before anything is fixed or published.

**Not in scope:** `skills/**` content. Not because it is above suspicion — the
invariants already gate it, and this audit is testing the *unguarded* half.
