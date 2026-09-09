# ROADMAP 43 — GATE-ABSORPTION at n=3, temp 0.7: H1 confirmed

**Run 2026-09-09 → 2026-09-10** (3h50m) · `run-completeness.py --pad-rules 400 --no-gate-arm
--samples 3 --temp 0.7` · `anthropic/claude-sonnet-4.6` build, `anthropic/claude-opus-4.8`
judge · 7 tasks × 4 arms × 3 samples · artifact `completeness-gate-absorption-n3.json`,
log `gate-absorption-n3.log` ·
**pre-registered** in [PRE-REGISTRATION-GATE-ABSORPTION-N3.md](PRE-REGISTRATION-GATE-ABSORPTION-N3.md),
committed before any call

## Result

| Arm | Rules context | `BUILD_WORKFLOW` | Mean | (item 32, n=1 temp 0) |
|---|---|---|---|---|
| `without` | none | — | 0.596 | 0.597 |
| `with` | the case's own skills | yes | **0.978** | 1.000 |
| `with+pad` | + 400 lines of unrelated rules | yes | **0.991** | 0.973 |
| `pad-nogate` | + 400 lines of unrelated rules | **no** | **0.929** | 0.933 |

```
PAD-DELTA        = +0.01   (padding costs this much WITH the gate)
NOGATE-DELTA     = -0.05   (padding costs this much WITHOUT the gate)
GATE-ABSORPTION  = +0.06   (what the terminal self-audit recovers under competing context)
```

## Verdict against the registered thresholds

**H1 is CONFIRMED.** It required `GATE-ABSORPTION ≥ +0.05`; the measurement is **+0.0616**.
That threshold was carried over unchanged from the 2026-09-06 registration and deliberately
*not* moved toward the +0.04 already observed — which is the only reason this number means
anything.

H0 required `[−0.02, +0.02]`; H2 required both padded arms ≥ 0.05 below `with`, and
`with+pad` is **above** `with`. Neither holds. **The dead zone was not entered, so the
registered stopping rule does not fire.**

### The effect is not one noise floor wide this time

| | |
|---|---|
| GATE-ABSORPTION | **+0.0616** |
| SE across the 7 case-level differences | **0.0190** |
| 95% CI | **[+0.024, +0.099]** — excludes zero |
| per-case differences | `+0.056  +0.061  +0.152  +0.100  0.000  +0.033  +0.030` |

**Six of seven cases positive, none negative.** The one zero is `c5_search`, which sits at
1.00 in all three gated arms — a ceiling, not a contradiction.

### The registered noise-band assumption held, and it was checked rather than assumed

The pre-registration derived the ±0.02 band from the sample count (±0.03 at n=1, narrowed by
√3) and said plainly that the assumption *"plausibly is"* wrong at temp 0.7, that the
artifact carries the real spread, and that a contradiction had to be reported rather than
the convenient band kept.

Checked: the observed SE of the case-level difference is **0.0190** against an assumed
**0.02**. The assumption held. Worth noting what it does *not* mean — the **within-arm,
per-sample** spread is much larger (mean max−min **0.071**, worst case **0.300**), which is
exactly why n=1 could not resolve this and n=3 could.

## What changed from item 32, and one claim that does not survive

`without` reproduces almost exactly (0.597 → 0.596) and `pad-nogate` holds (0.933 → 0.929).
Two arms moved:

- **`with` fell off the ceiling** (1.000 → 0.978), which is temperature doing what
  temperature does, and is *helpful* — item 32 registered the risk that a pinned ceiling
  would make the run uninformative.
- **`with+pad` rose** (0.973 → 0.991), and with it PAD-DELTA flipped sign: **−0.03 → +0.01**.

**So item 32's "item 25 replicates" no longer holds at this power.** Its write-up said the
padded-and-gated arm cost −0.03, same direction and order of magnitude as item 25's −0.01.
At n=3 and temp 0.7 that cost is **not measurable** — with the gate on, 400 lines of
competing rules prose cost nothing detectable. The correction is recorded here rather than
edited into item 32, whose numbers stand as published.

## What can now be said, and what still cannot

**Can:** under competing context, removing the router's terminal self-audit costs
**−0.05** against the unpadded gated arm, and the gate recovers **+0.062 [+0.024, +0.099]**
of what the padding would otherwise take. This is the first result in this repo that puts a
confidence interval excluding zero on BUILD step 4.

**Cannot:**

- **7 cases, one model, one day.** `sonnet-4.6` build / `opus-4.8` judge, chosen to stay
  comparable with items 25 and 32 rather than to be current.
- **Dilution, not conflict.** `rules_padding` refuses the case's own files but does not
  guarantee the padding *contradicts* the task. The conflict question is ROADMAP 39, and it
  now has its own number.
- **This measures the gate under padding, not the gate in general.** The unpadded ablation
  (`with` minus a hypothetical no-gate-no-pad arm) was never run and is not implied.
