# Pre-registration — ROADMAP 47: the conflict rate at LEAN loading

**Written 2026-09-12, BEFORE any model call**, and committed before the run. The `--lean`
flag was added to `evals/run-conflict-rate.py` first and its corpus verified (8% of full);
nothing has been scored with it.

## The two design questions the item was parked on, and how they are settled

**(a) What does a lean session load?** ROADMAP 47 suggested *"the case's own `expect` plus
the files each `SKILL.md` index names for that task"*. **Rejected**, for a reason that
matters more than the convenience: deciding which rules files a given task would open is the
**measurer's judgement**, and the measurer holds the hypothesis. Instead, lean = **`SKILL.md`
only** — the strict **floor** of BUILD step 2, which opens the skill's `SKILL.md` and only
then the matching rules files. The floor and the existing full-corpus ceiling **bracket** the
lived rate with nobody's judgement in between. Verified before registering: lean is **8%** of
the full corpus (a pair drops from ~319k to ~26k characters of judge input).

**(b) Does the judge see the router?** **No.** Keeping it blind preserves comparability with
the published ceiling, and the router arm answers a *different* question — *does the
conflict-resolution clause work?* — which deserves its own registration rather than being
folded in here. Stated out loud because the known consequence is that this judge
**over-reports by construction** on exactly the classes the router resolves (finding format,
scoped severity), as ROADMAP 39 documented.

## The confound this design exists to remove

The published ceiling, **0.176 verified**, was measured **2026-09-09 — before v1.40.2 fixed
the three conflicts it confirmed**. A lean run today would therefore differ from it on **two
axes at once**: lean-vs-full *and* pre-fix-vs-post-fix. A drop could not be attributed.

So **both arms run on the same tree, on the same day**:

| arm | corpus | what it gives |
|---|---|---|
| `full` | `SKILL.md` + every `rules/*.md` | the ceiling **re-measured post-fix** — independently useful: did fixing three conflicts move it? |
| `lean` | `SKILL.md` only | the floor, ROADMAP 47's actual question |

Same 17 pairs from 8 multi-skill gold cases, **3 samples, temp 0.0**, judge
`anthropic/claude-sonnet-5` — every parameter identical to the 2026-09-09 run so the full arm
is a genuine replication.

## Thresholds and predictions, fixed now

- **Primary:** hand-verified conflict rate per arm (judge-reported is recorded but is *not*
  the quotable number — ROADMAP 39's rule, kept).
- **Prediction 1:** the **lean floor is near zero** — of the three conflicts confirmed at the
  ceiling, two lived in `rules/*.md` (`sota-sandboxing` rules/03's `ipBlock`,
  `sota-frontend-design` rules/03's `...rest`) and are simply **not present** in a
  SKILL.md-only corpus. If lean still reports ≥ 0.10, my model of where conflicts live is
  wrong and that is the finding.
- **Prediction 2:** the **full arm drops below 0.176**, because three of its confirmed
  conflicts were repaired. If it does **not** drop, either the repairs did not take or the
  judge's verified findings were not the ones that moved the rate — both worth knowing.
- **Null band ±0.03**, this project's established noise floor.

## Cost, stated before spending

~51 judge calls per arm. The full arm carries ~319k characters of corpus per call and is the
expensive one; the lean arm is ~8% of that. Estimated **$10–15 total**, dominated by the full
arm. Recorded so the number is not discovered afterwards.

## What this will NOT establish

1. **It is a floor, not the lived rate.** A real lean session opens *some* rules files; this
   opens none. The lived rate sits between the two arms, and neither arm is it.
2. **The judge cannot see the router**, so both arms over-report the classes the router
   resolves. That is a constant across arms, so the *difference* is still meaningful even
   though each level is inflated.
3. **17 pairs, one model, one day.**

## Status

Not yet run.
