# Result — offloading the library map does not cost routing recall

Run 2026-09-03 against the pre-registration in
[ROUTER-MAP-OFFLOAD-PREREG.md](ROUTER-MAP-OFFLOAD-PREREG.md), written and committed
before either arm ran. PR #308.

## Command

```
python3 evals/run-clean.py --cases evals/cases/router.jsonl --samples 3 --temp 0.7
```
Run twice against trees differing **only** in `skills/sota/SKILL.md` — verified by
`diff` on `run-clean.py`, `score.py` and `router.jsonl` before spending anything.
`main` ran in a `git worktree`, so both trees existed at once.
Model `anthropic/claude-sonnet-4.6`, 20 routing cases, 3 samples per arm.

## Numbers

| run | arm | recall | per-sample | precision | picks/case |
|---|---|---|---|---|---|
| BEFORE (499 lines, map inline) | without-library | 0.900 | 0.908 / 0.883 / 0.908 | 0.456 | 2.85 |
| BEFORE | **with-library** | **1.000** | 1.0 / 1.0 / 1.0 | 0.411 | 3.65 |
| AFTER (398 lines, map offloaded) | without-library | 0.900 | 0.908 / 0.883 / 0.908 | 0.456 | 2.85 |
| AFTER | **with-library** | **1.000** | 1.0 / 1.0 / 1.0 | 0.448 | 3.35 |

```
without-library  Δrecall=+0.000  Δprecision=+0.000  Δpicks/case=+0.00   <- negative control
with-library     Δrecall=+0.000  Δprecision=+0.037  Δpicks/case=-0.30   <- treatment
```

**The pre-registered falsification condition did not trigger.** It was: *with-library
recall drops in AFTER by more than the control's drift*. Recall held at **1.000** in
both, with **zero misses across 3 samples × 20 cases** in each configuration. The
prediction held and the merge is unblocked on the criterion set in advance.

## Three caveats, and one of them was nearly a false conclusion

**Recall is at ceiling, so this can only ever detect a drop.** It detected none in 120
case-samples. That is evidence of *no detected degradation*, not of *no change*.

**The control arm's Δ=0.000 is not a measured noise floor.** Its per-sample triple came
back identical in both runs, which first looked like provider-side caching returning
canned completions — the prompt is byte-identical there, since that arm never reads the
router. **Checked instead of assumed:** its predictions differ in **1 of 20** cases
across the runs, so it is genuinely sampling and merely robust. Had it been cached, the
"noise floor" would have been an artifact and the treatment's +0.000 would have rested
on it.

**The treatment arm churned far more than the control** — predictions differ in **11 of
20** cases between the runs, against 1 of 20 for the control. So `Δprecision=+0.037`
and `Δpicks/case=−0.30` are **not reportable as an effect**: they sit inside that churn
at n=3, and `evals/cases/router.jsonl` states in its own header that *"extra loads are
not penalized as errors; a MISS of an expected skill is the real signal."* The direction
is favourable and that is all that can be said.

What the churn does show: the offload changes *which extra skills get named* on half the
cases while never costing a must-load skill. Recall is the metric the golden set was
built for, and it is unmoved.

## Instrument correction

PR #308 originally proposed `run-desc-routing.py`. **That runner cannot see this
change** — it builds its catalogue from each skill's frontmatter `description`
(`parse_desc`, `catalogue`) and never reads the router body, so the arm could not have
seen the treatment and its `+0.00` would have been structural rather than a result. Its
own docstring says so: it measures the description catalogue *"as opposed to the router
table that `run-clean.py --cases router.jsonl` measures"*. The mistake was caught by
reading the runner before spending, not by the number looking wrong afterwards — a
+0.00 from it would have looked exactly like this one.

## Raw output

[router-map-offload-BEFORE.json](router-map-offload-BEFORE.json) ·
[router-map-offload-AFTER.json](router-map-offload-AFTER.json)
