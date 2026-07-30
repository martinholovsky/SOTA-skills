# BUILD-safe — the instrument is at ceiling, and the flaw is in my spec

**Date:** 2026-07-30 · **Status: not a result. The instrument does not
discriminate, because the task over-specifies.** No lift is claimed, and this row
does **not** belong on the scoreboard as an eighth null.

## What it was for

Seven audit instruments read +0.00: a frontier model *finds* these classes
unaided. The untested question was whether the library stops them being
**written** — the shape behind every measured lift here (+0.39 completeness,
+0.53 freshness): a generative task with a hidden rubric.

`cases/build-safe/SPEC.md` describes a service; `run-build-safe.py` scores
AVOIDANCE of seven defect classes over the produced code.

## Result

| Arm | n | avoided |
|---|---|---|
| bare (verified library-free, 0 citations each) | 3 | **1.000** |

All three shipped 106–142 passing tests, an allowlisted `ORDER BY` map,
write-through cache invalidation, streamed upload caps with boundary-straddling
marker tests, real admin guards, and — unprompted — **declined to build the
`tenant.quota_exceeded` handler** because nothing dispatches that event. One went
further and made its registry *refuse* to register unemitted events, with a test
asserting the reverse gap fails CI.

With the bare arm at 1.000 the ceiling is hit and the library arms cannot
demonstrate anything. Whatever they score, the instrument is uninformative.

## Why — I leaked the answer into the spec

The pressures were meant to make the *unsafe* path tempting. Several instead
state the property to defend:

- *"Operators change roles through an admin console and expect the change to take
  effect"* — practically an instruction to invalidate the cache.
- *"a malformed or unexpected payload must never take the endpoint down"* — names
  the failure mode.

**This is the audit-vocabulary leak in a new costume.** `run-repo-audit.py` hands
the model a 21-slug menu containing all 8 answers; my spec hands it the
non-functional requirements. Both supply the consideration set, which is the one
variable that separates the +0.39 BUILD design (one-line task, judge-only rubric)
from every +0.00 instrument.

One builder said so without being asked, describing its own decisions as sitting
*"where the spec's requirements pulled against the stated guarantees"* — it read
the NFRs as tensions to resolve, because that is how they were written.

A second contributor: the spec is a page long. `completeness.jsonl`'s task is one
sentence, and its baseline is 0.59 precisely because the model must supply the
consideration set itself.

## The scorer was wrong four times, always the same direction

Every correction was a **false negative punishing a better implementation** —
recorded because the pattern generalises to any regex-based code scorer:

1. Keyed on `def get_report`; the defective method is `ReportService.get`.
2. Flagged the *correct* SQLi fix — the safe spelling is still an f-string, over
   an allowlisted variable.
3. Credited the unprotected `get()` with the ownership check that lives in
   `delete()` — the fixture's planted trap, walked into by flat concatenation.
4. Scored a build as missing an ownership check it enforces in
   `_load_visible_report`, because scoping could not follow one level of
   delegation.

Fixed with a `requires_safe` mode (absence-of-check cannot be matched
positively), AST function scoping, and callee-following. `--selftest` holds the
line: **0.000** on the defective reference, **1.000** on the fixed one, enforced
in CI.

## What would make it a real instrument

State the **feature**, not the non-functional requirement. "Search results are
sortable by a column the user picks" — without *must take effect*, *must never
5xx*, *must stay fast*. Then the tension is real and the safety judgment has to
come from the model rather than the brief.

Until that rewrite, this measures nothing, and the fixture, scorer and references
are kept only because they are the reusable half.
