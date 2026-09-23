# P7 — does a collaboration task reach `sota-docs-workflow` from its description? (not reproduced)

**2026-09-23** · `evals/run-desc-routing.py --cases evals/cases/desc-routing-collab.jsonl
--samples 3 --temp 0.7` · `anthropic/claude-sonnet-4.6` · 6 cases × 2 arms × 3 samples ·
objective name-match, no judge · **pre-registered** in
[PRE-REGISTRATION-P7-COLLAB-ROUTING.md](PRE-REGISTRATION-P7-COLLAB-ROUTING.md), committed before
any call · artifact `desc-routing-collab.json`

## Result

| arm | correct | distractor-pick |
|---|---|---|
| **with-xref** (descriptions as committed, the verdict arm) | **18 / 18 = 1.000** | 0.000 |
| without-xref | 18 / 18 = 1.000 | 0.000 |

Every case scored 3 of 3 in both arms: commit message and PR body, replying to review, PR-size
policy, cleaning up history, an upstream contribution, and stacked PRs. No case scored 0.

## Verdict against the registered thresholds

The "not reproduced" threshold was **≥ 15 of 18**, and the result is **18 of 18**. **P7 is
rejected on measurement**: from its description alone, `sota-docs-workflow` is picked for the
collaboration half the proposal said it hides. No description change is made, and invariant 29
is not triggered.

## What this does not show, stated before anyone cites it

- **A 1.00 is a ceiling, not a margin.** These tasks name "pull request" and "commit" outright,
  and the description carries those words. The run shows the description is *sufficient* for a
  plainly worded collaboration task. It cannot say how much slack there is for an oblique one.
- **The original miss is not explained by this.** The 2026-08-05 session did the collaboration
  work alongside other work. A skill already loaded, or a change of task shape mid-session, is
  the more likely mechanism, and it is the one ROADMAP 48 measured: correct routing **0.750
  fresh vs 0.500 after two turns of other work** ([ROUTING-SHIFT](../2026-09-12/ROUTING-SHIFT.md)).
  That is a property of the session, not of this description, and rewriting the description
  would not have fixed it.
