# BUILD-safe — the instrument is at ceiling, and the flaw is in my spec

> **Superseded 2026-08-21 — the diagnosis below was right and the fix worked.**
> The spec was rewritten to state features and facts rather than the property to
> preserve, and on re-run the bare arm **no longer saturates** (0.809 mean, one run
> at 1.000) while the with-library arm reaches 1.000 × 3. The instrument
> discriminates. See [2026-08-21/BUILD-SAFE.md](../2026-08-21/BUILD-SAFE.md). This
> page is kept unedited as the record of the failed first attempt.

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
| library (46–90 citations each) | 3 | 0.857 / 1.000 / 0.857 |

The library arm's two sub-1.000 scores are **scorer false positives, not deficits**
— one is a chunked scan (`payload[:CHUNK]` in a loop, the *safe* implementation)
matching a prefix-slice pattern. They are not evidence of anything and are not
reported as such. With the bare arm at ceiling, no lift is measurable either way.

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

## The scorer was wrong eight times

**A fifth class, found last and worst: unbounded scope.** The scorer printed
"851 .py files" for a ten-module service — it was reading a vendored virtualenv,
third-party packages, the project's own `assert user.has(permission)` test lines,
and one agent's mutation-probe tooling. That made the *library* arm look worse
than bare. **The denominator was printed and I did not read it** — precisely the
failure rules/11 §2.2 exists to prevent, committed by the person who wrote it.
Scope is now bounded to product code (tests, tools, vendored envs excluded).

## The first four, and they did not all run one way

Correction to an earlier characterisation of these: I described all four as false
negatives punishing better implementations. **That was wrong — #3 ran the other
way**, making the *defective* reference look safe. Errors in both directions is
worse than one-directional bias, because only the excusing direction agrees with
the hoped-for result and so nobody chases it.

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

## The rewrite (2026-07-30, same day)

`SPEC.md` was rewritten to the rule *state features and facts, never the property
to preserve*. Removed: "operators expect the change to take effect", "must never
take the endpoint down", "must stay fast enough to run inline", "keep their guards
cheap". Kept: the product tensions that create the pressure without disclosing the
resolution — the hottest query, a provider that retries, a 25 MB cap, an ops
console on the private network, a retired feed the team expects back.

Verified after the rewrite: **0** occurrences of any "must …" quality clause or
defect name in the spec, and all six pressure points still present.

**One thing the rewrite nearly broke.** The maintainer note explaining the leak was
first written *into* `SPEC.md` as an HTML comment — which is still text the agent
reads, and it named all three leaked properties plus the defect classes. That would
have been a worse leak than the original. It now lives in the header of
`cases/build-safe.jsonl`, which never travels to a subject. General form: **keep
guidance about the instrument out of the artifact the subject sees.**

**The thinner spec did not restore discriminating power.** Two bare agents on the
rewritten spec, both verified library-free: **1.000 and 1.000**. Same ceiling.

One of them went past the reference answer: it noticed permissions are a pure
function of role, so the "three-table join" computes a constant — and **deleted the
cache** instead of adding invalidation. No cache, no staleness window. The other
mutation-checked its own suite across nine controls and fixed two false claims it
had written in its own comments after `EXPLAIN QUERY PLAN` contradicted them.

## Conclusion: these classes are not elicitable from a spec at this tier

Fat spec or thin, a capable agent asked to *build this service* writes an
allowlisted sort, an ownership predicate, a non-swallowing webhook, a full-payload
scan and real admin guards, and declines to wire a handler nothing emits. Five
bare builds across two spec versions, all 1.000.

**This is worth contrasting with the +0.39 completeness result rather than filed
next to it.** Those rubric items are **cross-cutting omissions** under a
one-sentence prompt — rate limiting, structured logging, TLS, tests — things a
model drops because nobody named them and the task did not imply them. The seven
classes here are **local correctness decisions inside a feature the model is
actively writing**, and it makes them well.

So defect-**avoidance** and practice-**completeness** are different measurement
targets, and only the second has ever shown a gap in this project. That is the
useful finding from this instrument, and it is a finding about *where a lift can
exist at all* — not a result about the library, which never got a comparable arm
because the bare arm never left the ceiling.

**Do not rebuild this instrument.** A third spec version is not the missing piece.

The fixture, scorer and both references are unchanged and reusable.
