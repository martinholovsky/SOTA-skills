# Pre-registration — does a collaboration task reach `sota-docs-workflow` from its description?

**Registered 2026-09-23, committed before any model call.**

## The claim under test

Proposal **P7** (a local router-activation proposal, 2026-08-05) says `sota-docs-workflow`'s
description "leads with Diátaxis, READMEs, runbooks", so that its pull-request, code-review and
commit half "reads as an afterthought". The session behind the proposal did commit messages, a
PR body and review replies, and the skill never surfaced. The proposed fix was to lead with the
collaboration half, or to split the skill. It has had no verdict for seven weeks. Changing a
description moves the routing classifier (invariant 29), so the claim is **measured before
anything is changed**.

## Method

`evals/run-desc-routing.py --cases evals/cases/desc-routing-collab.jsonl --samples 3 --temp 0.7`
on `claude-sonnet-4.6`, the library's measurement baseline. The catalogue is every
`skills/sota-*` description (the router is excluded by the runner's glob). The primary arm is
**with-xref**: the descriptions exactly as committed. The without-xref arm is reported but not
used for the verdict. The 6 cases are defined in the case file, and their selection rule is
stated there.

## Thresholds (fixed now)

- **P7 not reproduced**, and recorded as rejected on measurement: `sota-docs-workflow` picked in
  **≥ 15 of 18** with-xref samples (≥ 0.83).
- **P7 confirmed**, and a description reorder is justified and must itself be re-measured:
  **≤ 9 of 18** (≤ 0.50).
- **In between: inconclusive.** Record it and re-run at n = 5 before changing anything.

**Falsifier for "not reproduced":** any case scoring 0 of 3 is reported by name whatever the
aggregate is, because a skill that fails one whole task shape has a real gap that an average
hides.

## What it cannot show

The eval tests description selection in isolation. The 2026-08-05 miss may instead have come
from the auto-loader never being consulted, or from another skill already loaded, and neither
is visible here.
