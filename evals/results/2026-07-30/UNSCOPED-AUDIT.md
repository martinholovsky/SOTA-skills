# Unscoped audit — both experiments +0.00, both predictions wrong

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
| unscoped-bare (verified library-free) | 3 | **1.000** |
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

## Experiment B — also +0.00, and the sharper prediction was wronger

New fixture `cases/unscoped-audit/reportkit` (13 files, 394 lines), most of it
deliberately correct. **7 planted defects, 6 demonstrated at runtime** by
`selfcheck.py`: 2 control classes (SQLi, IDOR) as the internal validity check,
and 5 treatment classes outside the standard repertoire — a swallowed webhook
signature, a handler registered for an event nothing emits, a permission cache
keyed narrower than the behaviour it gates, authorization written as `assert`,
and a scanner that inspects 64 KB of a 25 MB allowance.

| Arm | n | control | treatment |
|---|---|---|---|
| **verified-clean bare** | **3** | **1.000** | **1.000** |
| library-loaded (incl. 2 contaminated nominal-bare) | 4 | **1.000** | **1.000** |

**Predicted treatment-bare 0.35 (0.10–0.60) and a delta of +0.45 (0.15–0.75).
Actual: 1.000 and +0.000.** The prediction missed its own lower bound by nearly
three times. Three verified-library-free agents each found all five treatment
classes unprompted, on a repo that is mostly correct code.

That was the sharper of the two hypotheses — it manipulated the question set
directly rather than the framing — and it is the one that failed hardest.

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

## Conclusion

**Seven instruments, three designs, one answer.** Recognition (snippets,
cross-file repo, precision), procedure (dead-path), and now question-set under an
unscoped brief — all +0.00. The last of these was built specifically because the
first two had a shared confound, and the confound turned out not to matter: the
bare arm found everything either way.

Two hypotheses are now dead, both of them mine, both pre-registered before the
run that killed them:

1. *The audit nulls are an artifact of leaky prompts.* No — stripping the domain
   framing and the answer vocabulary changed nothing.
2. *The library expands what the model thinks to look for.* No — verified-clean
   bare agents found a swallowed webhook signature, an unreachable handler, a
   too-narrow cache key, an `assert`-as-authz, and a truncated scanner, none of
   which they were pointed at.

**Stop building audit-recall instruments.** The honest position for the library's
audit half is that it is justified by gap analysis and by real defects it found in
this repo — not by a measured lift, and seven instruments now say so. The only
untested claim left is calibration: every library arm downgraded its own findings
on evidence and bounded its claims by what it had actually run, and no bare arm
did. That is measurable, but it measures adherence to our own reporting doctrine,
which is a far weaker claim than "finds more bugs" and must never be reported as
a lift.
