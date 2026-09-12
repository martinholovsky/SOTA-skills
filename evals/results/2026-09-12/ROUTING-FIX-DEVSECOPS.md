# ROADMAP 48 — fixing the trigger defect, and the routing check that caught a regression

**2026-09-12.** The measurement found that *"the pre-commit hook passes locally but the same
check fails in CI"* routed to `sota-shell-scripting` **3/3 from a cold start**, never
reaching `sota-devsecops`, whose rules/09 §5 owns exactly that topic. This is the fix, and
the check that made it safe.

## Before → after, three instruments

| set | before | after |
|---|---|---|
| `desc-routing-regressions.jsonl` (3 cases) | **0.667** — r3 at 0.00, distractor-pick 1.00 | **1.000** |
| `desc-routing.jsonl` (10 cases, collateral) | 0.900 | **0.900** — unchanged |
| `run-routing-shift.py` fresh arm | 0.750 | **1.000** |

`r3_local_vs_ci_gate` goes from `sota-shell-scripting` 3/3 to **`sota-devsecops` 3/3**.
`q8_bash_review` — the case most at risk of being stolen — stays `sota-shell-scripting` 3/3.

## The edit

Two additions to `sota-devsecops`'s `description`, 915 → 995 characters (cap 1024):

- to the applies-when list: *"and a pre-commit hook that passes locally but fails in CI"*
- to the trigger keywords: *"pre-commit, local vs CI"*

Checked first, not assumed: **neither** skill's description previously contained
"pre-commit", "hook" or "local". The model was not choosing shell because shell *claimed*
these words — it was choosing shell because the prompt's surface vocabulary (hook, check,
passes, locally) is shell-flavoured and nothing contested it. The edit is additive, not a
tug-of-war.

## The routing check caught a regression, which is the point of having one

The **first** version of this edit read *"a pre-commit hook **or gate** that passes locally
but fails in CI"*. It fixed s3 — and **broke s4**, whose fresh arm fell 1.00 → 0.00:

> *"our attestation script writes a signed record after every **gate run**, and its self-test
> has been green since it was written — does that self-test actually prove anything?"*

That belongs to `sota-code-security` (rules/15, the guard that is an instance of what it
guards; router rule 17 sends evidence-producing scripts there). With a second "gate" in the
devsecops description, it went to `sota-devsecops` **3/3 in both arms**.

Removing one word — *"or gate"*, taking the description's "gate" count from 2 to 1 —
restored s4 to 1.00 and left s3 fixed. **A single token moved a case 3/3 in both arms.**

**The two `desc-routing` sets did not catch it.** s4 exists only in `routing-shift.jsonl`.
Had the routing check been only the set invariant 29 names, this would have shipped — which
is the v1.35.0 pattern exactly, where one description edit inverted a regression case and ran
live for a day. **Run every routing instrument you have, not only the declared one.**

## For the next release

A skill `description` changed, so invariant 29 fires on the next version bump and the
CHANGELOG entry must carry:

```
**Routing checked:** evals/results/2026-09-12/ROUTING-FIX-DEVSECOPS.md
```

## What this does not establish

- The fix is verified on **13 cases across two sets plus 4 in a third**, one model, one day.
  Nothing says another phrasing of the same question routes correctly.
- `q4_data_race` remains 0.00 in both arms and is untouched by this — a forced single pick
  between `sota-golang` and `sota-async-concurrency`, both defensible.
