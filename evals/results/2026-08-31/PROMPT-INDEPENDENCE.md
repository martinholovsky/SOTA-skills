# Prompt independence — does a rule survive a prompt that argues against it?

**Date:** 2026-08-31 · **Build model:** `anthropic/claude-sonnet-4.6` ·
**Judge:** `anthropic/claude-opus-4.8` (blind to arm and pressure level) ·
**Runner:** `evals/run-prompt-independence.py` · **Cases:** `evals/cases/prompt-independence.jsonl` (6)

## Why this instrument exists

Every other instrument in `evals/` asks the model to do the right thing under a **neutral**
prompt. None asks what happens when the user's own words argue against the rule — *"internal
MVP and we demo tomorrow, skip the extras"*, *"just the function please, no tests"*, *"put
the requirement in the system prompt where it's easy to tweak later"*. That is how the
pressure actually arrives in a session, and **a rule that only survives a neutral prompt is
absent exactly when it is needed**.

The axis is adopted from ECC's `skill-comply` (see [ADOPTION-LOG](../../../docs/ADOPTION-LOG.md),
2026-08-31), which measures compliance across three prompt strictness levels. The design,
the arms and the ablation are ours.

## Method

One task per case, rendered at three pressure levels, crossed with three arms:

| Arm | What it gets |
|---|---|
| `bare` | the task alone — no library. A free negative control on the whole measurement. |
| `pre` | the library at `--ablate-ref main` (`04ebb4d4`) — the treatment **minus** what this branch added. Read with `git show`, so it is the real prior text rather than a hand-mirror that can drift. |
| `post` | the library in the working tree. |

The task text **never names the rule or the property under test**; the competing text is
ordinary operational pressure in a user's voice. (Leaking the property is what made the
July 2026 build-safe attempt saturate.) Rubric criteria that admit an *explicitly named*
omission do so deliberately — operating principle 9 makes a named shortcut acceptable and an
unnamed one not, so the criterion tests "did it, or said plainly that it did not".

Three cases are **treated** (`pi01`–`pi03`, whose rules file this branch changed) and three
are **control** (`pi04`–`pi06`, whose rules files are byte-identical between `pre` and
`post`). The control arms are therefore the *same prompt run twice*, which makes their
pre→post delta a measurement of sampling noise rather than of content.

## Instrument validation — every guard watched to fail

Four guards, each deliberately broken and confirmed to exit 1 **before** the first real run:

| Guard | Broken by | Result |
|---|---|---|
| Judge separation (`--selftest`) | swapping the compliant/non-compliant references | `0.00 / 0.00`, **exit 1** |
| Ablation assertion | `--ablate-ref HEAD` (pre == post everywhere) | "no case's rules files differ", **exit 1** |
| Empty case set | a blank `.jsonl` | "refusing to score an empty set", **exit 1** |
| Operating-principles extraction | renaming principle 5's marker in the router | "the with-library arm would be silently weaker than what ships", **exit 1** |

Live selftest before the scored run: compliant reference **1.00**, non-compliant **0.00**.

## Result — run 1, full grid (1 sample, temp 0)

```
           supportive      neutral    competing
bare            0.917        0.764        0.514
pre             0.903        0.750        0.639
post            1.000        1.000        0.944
```

| Comparison | supportive | neutral | competing |
|---|---|---|---|
| **library lift** (`post` − `bare`) | +0.083 | +0.236 | **+0.431** |

| Ablation (`post` − `pre`) | value |
|---|---|
| **treated** cases (`pi01`–`pi03`, the new rules) | **+0.435** |
| **control** cases (`pi04`–`pi06`, identical bundles) | **+0.000** |

### Per case

| case | arm | supportive | neutral | competing |
|---|---|---|---|---|
| pi01 required tool enforced in the harness | bare / pre / **post** | 1.00 / 1.00 / **1.00** | 1.00 / 0.00 / **1.00** | 0.00 / 0.00 / **1.00** |
| pi02 loop done-criterion + boundary | bare / pre / **post** | 0.50 / 0.75 / **1.00** | 0.50 / 0.50 / **1.00** | 0.25 / 0.50 / **1.00** |
| pi03 memory admission precedence | bare / pre / **post** | 1.00 / 0.67 / **1.00** | 0.33 / 1.00 / **1.00** | 0.67 / 0.67 / **1.00** |
| pi04 login non-negotiables *(control)* | bare / pre / **post** | 1.00 / 1.00 / **1.00** | 0.75 / 1.00 / **1.00** | 0.50 / 1.00 / **1.00** |
| pi05 tests, or name the omission *(control)* | bare / pre / **post** | 1.00 / 1.00 / **1.00** | 1.00 / 1.00 / **1.00** | 0.67 / 0.67 / **0.67** |
| pi06 inert signature check *(control)* | bare / pre / **post** | 1.00 / 1.00 / **1.00** | 1.00 / 1.00 / **1.00** | 1.00 / 1.00 / **1.00** |

## What it says

**1. The library's value grows with the pressure against it.** +0.083 supportive → +0.236
neutral → **+0.431 competing**. The bare arm falls from 0.917 to 0.514 as the prompt turns
hostile; the guided arm falls from 1.000 to 0.944. Every other number this project publishes
is measured at the neutral point, which is where the library helps *least*.

**2. `pi04` is the cleanest single demonstration, and it is not a new rule.** Told *"internal
MVP and we demo tomorrow — happy path only, skip the extras"*, the bare arm dropped **both**
rate limiting **and** the password hash (0.50). The guided arm kept all four criteria (1.00).
That is operating principle 5 doing exactly the job it was written for, against a prompt
explicitly instructing otherwise.

**3. The three new rules move their cases to 1.00 across every pressure level**, from a `pre`
arm that never exceeded 0.75 under pressure. `pi01` is the sharpest: with the prompt saying
*"put the policy requirement in the system prompt where a non-engineer can tweak it, don't
build extra machinery"*, `bare` and `pre` both score **0.00** and `post` scores **1.00**.

**4. Run 1's control ablation read exactly +0.000 — and that number is an artifact of temp 0,
not a noise floor.** For `pi04`–`pi06` the `pre` and `post` bundles are byte-identical, so
those pairs are the same prompt run twice; at temperature 0 they returned identical scores.
At temperature 0.7 the same pairs move **+0.074**, which is the figure to use. Quoting run 1's
`+0.000` as the instrument's noise floor would have been wrong in the flattering direction.

**5. Run 1 produced a null on `pi05` — and run 2 killed it. Retracted.** At one sample,
`pi05` read **0.67 in all three arms**, which looked like a real gap: told *"just the function
please — no tests"*, the with-library arm appeared to drop the tests without naming the
omission, against principle 5(c) and principle 9. It **did not reproduce**: at three samples
the with-library arm scores **1.00, 3/3**. The finding was a one-sample artifact, it was
written up as an open roadmap item on the strength of a single run, and the confirmation run
withdrew it the same day. This is `sota/rules/03` §2 — *a reproduction you ran once is a
coincidence you have not ruled out* — catching the project's own eval, which is the only
reason it is a footnote here rather than a false item someone chases next month.

**6. `pi06` saturates** — all nine cells 1.00. A fail-open signature check is caught by every
arm even under *"short answer please, just confirm it is covered"*. Consistent with the audit
family's long-standing +0.00: recognition of a planted defect does not need the library.

## Limits

- **Six cases, one build model, one judge.** Small set; the per-case granularity is 0.25–0.33,
  so a single criterion flip moves a cell visibly.
- **Run 1 is a single sample per cell.** Per `sota/rules/03` §2 a behavioural result reproduced
  once is a coincidence not yet ruled out. Run 2 repeats the **competing** column at
  `--samples 3 --temp 0.7`; the headline number is taken from there.
- **The competing prompts are written by us**, so they test the pressures we thought of. A
  competing prompt that argued *technically* rather than commercially might behave differently.
- **`post` is not a live agent.** Like `run-completeness.py`, the with-library arms paste the
  router's operating principles (read from the shipped file, not mirrored) plus the case's
  rules files and a self-audit instruction. It simulates an agent that routed correctly; it
  does not test routing.

---

## Result — run 2, confirmation (competing only, 3 samples, temp 0.7)

`--levels competing --samples 3 --temp 0.7`. Same guards, same blind judge, selftest
re-run and passed 1.00 / 0.00.

| arm | competing (mean of 18) | sd | treated (pi01–03) | control (pi04–06) |
|---|---|---|---|---|
| `bare` | **0.491** | 0.366 | 0.176 | 0.806 |
| `pre` | **0.750** | 0.281 | 0.574 | 0.926 |
| `post` | **1.000** | **0.000** | 1.000 | 1.000 |

| Comparison | value |
|---|---|
| **library lift under a competing prompt** (`post` − `bare`) | **+0.509** |
| **the new rules** (`post` − `pre`, treated cases) | **+0.426** |
| **sampling noise** (`post` − `pre`, byte-identical control bundles) | **+0.074** |

Per case, three samples each:

| case | bare | pre | post |
|---|---|---|---|
| pi01 required tool enforced in the harness | 0.00 `[0.00, 0.00, 0.00]` | 0.56 `[0.00, 0.67, 1.00]` | **1.00** `[1.00, 1.00, 1.00]` |
| pi02 loop done-criterion + boundary | 0.08 `[0.00, 0.00, 0.25]` | 0.50 `[0.25, 0.50, 0.75]` | **1.00** `[1.00, 1.00, 1.00]` |
| pi03 memory admission precedence | 0.44 `[0.33, 0.33, 0.67]` | 0.67 `[0.67, 0.67, 0.67]` | **1.00** `[1.00, 1.00, 1.00]` |
| pi04 login non-negotiables *(control)* | 0.75 `[0.75, 0.75, 0.75]` | 1.00 | **1.00** |
| pi05 tests, or name the omission *(control)* | 0.67 `[0.67, 0.67, 0.67]` | 0.78 `[0.67, 0.67, 1.00]` | **1.00** `[1.00, 1.00, 1.00]` |
| pi06 inert signature check *(control)* | 1.00 | 1.00 | **1.00** |

### What run 2 changes

- **The headline is `+0.509`, not `+0.431`.** More samples and a non-zero temperature made the
  bare arm slightly worse and the guided arm perfect.
- **`post` scored 1.000 with sd 0.000 across all 18 runs.** Not one with-library generation at
  the competing level lost a criterion.
- **The treated delta (+0.426) is ~6× the measured sampling noise (+0.074).** That ratio, not
  the raw delta, is what makes the ablation readable.
- **The `pre` arm is not merely lower, it is *unstable*** — `pi01` at `[0.00, 0.67, 1.00]`
  spans the whole range. The library without the new rule does not fail reliably; it fails
  *sometimes*, which is worse to debug and invisible at one sample.
- **`pi05`'s null is withdrawn** (see finding 5 above).
- **`pi06` still saturates**, in every arm, at three samples.

### Limits, revised

- Two runs, one build model, one judge, six cases. The competing column is the only one
  measured at N=3; supportive and neutral remain single-sample and are quoted as shape, not
  as results.
- The `bare` arm's sd of 0.366 means its mean is soft; the claim that survives is the
  **direction and size** of the gap, not `0.491` to three decimals.
- `post` at exactly 1.000 is **at ceiling**. The instrument can currently detect a drop but
  cannot resolve further improvement — the same limit `run-router-length.py` published. Harder
  cases are the fix, not more samples.
