# Unscoped audit — experiment A answered, my prediction wrong; B pending its clean arm

**Date:** 2026-07-30 · **Pre-registration:** [PRE-REGISTRATION.md](PRE-REGISTRATION.md)
(committed `754bf87`, pushed **before** either experiment ran).

## The hypothesis

Every audit instrument returning +0.00 **hands the model its search space**; the
BUILD instrument returning +0.39 does not. `run-repo-audit.py` names the domain
*and* supplies a 21-slug category vocabulary containing all 8 planted answers.
So "the library does not help an audit" had never been tested — only recognition,
with the question supplied.

## Experiment A — the vocabulary was NOT the crutch

Same fixture (`cases/repo-audit/orderdesk`, 16 files, 8 planted defects), brief
reduced to *"Audit this repository and report every defect you find."* No domain,
no vocabulary.

| Arm | n | Recall (8 classic defects) |
|---|---|---|
| unscoped-bare (verified library-free) | 2 | **1.000** |
| unscoped-library | 4 | **1.000** |

**Predicted 0.65 for unscoped-bare (range 0.40–0.85). Actual 1.000. The
prediction is wrong and the diagnosis it rested on is refuted for this fixture.**
Stripping the vocabulary and the framing did not cost the bare arm a single
defect. Our published cross-file +0.00 is **not** a prompt artifact.

A sub-suspicion was also **refuted**: the fixture's `README.md` says
"INTENTIONALLY VULNERABLE" and names the ground-truth path, but
`run-repo-audit.py` globs only `*.py`, so it was never sent to a model. The
existing measurement is uncontaminated by it. (It *was* stripped from the live
copies here, where agents see the directory.)

## Experiment B — instrument built, decisive arm still pending

New fixture `cases/unscoped-audit/reportkit` (13 files, 394 lines), most of it
deliberately correct. **7 planted defects, 6 demonstrated at runtime** by
`selfcheck.py`: 2 control classes (SQLi, IDOR) as the internal validity check,
and 5 treatment classes outside the standard repertoire — a swallowed webhook
signature, a handler registered for an event nothing emits, a permission cache
keyed narrower than the behaviour it gates, authorization written as `assert`,
and a scanner that inspects 64 KB of a 25 MB allowance.

Results so far (all arms that loaded the library, plus contaminated "bare"):

| Arm | n | control | treatment |
|---|---|---|---|
| library-loaded (incl. 2 contaminated nominal-bare) | 4 | **1.000** | **1.000** |
| **verified-clean bare** | **0** | — | — |

**No conclusion is available for B.** The clean bare arm is re-running.

## The harness defects — three, all mine

1. **No knowledge-scope instruction.** `run-repo-audit.py` tells its bare arm
   *"Use only your own security knowledge"*; I omitted that when lifting the
   design to live agents. Sub-agents inherit a global `CLAUDE.md` rule telling
   them to consult the SOTA router for audits — so the bare arm was never bare.
2. **Directory names leaked the arm** (`ub`/`ul`, `bb`/`bl`). Two agents said
   outright they inferred "unguided" from the path and behaved accordingly:
   demand characteristics, and the reason contamination came out *inconsistent*
   (ub1/ub2 clean, ub3/bb1/bb2 loaded the library anyway).
3. **The scratchpad path contains `SOTA-skills`.** Unavoidable here; recorded.

Contamination is therefore established **per agent from evidence** — library
citations in the text — never from the prompt or the agent's own account.
`run-unscoped-audit.py --selftest` locks the adjudicator; its contamination check
needed two corrections, both recorded in the code: it first flagged a clean report
on one occurrence of "blast radius" and on the *path string*, then a fix
over-stripped and produced a **false negative on a known-contaminated report** —
the more dangerous direction.

## What is consistent across every arm, and measured by nothing

Recall is identical. What differs is calibration. Library-loaded agents ran
adversarial refutation passes that **downgraded their own findings on evidence** —
weak-PRNG Critical→High after computing that state recovery needs ~3,300
contiguous token characters; SQL injection Critical→High after a probe proved the
blind oracle is silent with zero owned rows; a self-described "partly circular"
proof withdrawn because the reproduction used a schema the agent had written
itself. Several volunteered that the fixture cannot serve a request as shipped,
so every finding is static-only.

The clean bare agents found the same defects and shipped the scarier ratings
without that scrutiny. This is now the **fourth** setting showing the same shape:
**equal detection, unequal calibration** — and none of the seven instruments in
this harness scores calibration.
