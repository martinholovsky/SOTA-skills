# ROADMAP 53 — do the `Trigger keywords:` tails earn their characters?

**2026-09-11** · `evals/run-desc-routing.py --ablate keywords --samples 3 --temp 0.7` ·
`anthropic/claude-sonnet-4.6` · 10 cases from `desc-routing.jsonl` ·
**pre-registered** in [PRE-REGISTRATION-KEYWORD-TAILS.md](PRE-REGISTRATION-KEYWORD-TAILS.md),
committed before any call, and **amended before run 3** with the reason written down first.

## Status: ANSWERED — **Δ = +0.000**, a clean null, on the registered 10 cases

`with-keywords 0.900 / without-keywords 0.900`, distractor-pick **0.000** in both arms,
**0 of 10 cases moved**, SD 0.000. Inside the pre-registered **±0.03** null band, and the
pre-registered **prediction of a null was correct**.

**The tails buy no measurable matching value.** Not one of 60 calls across ten
independently-authored, adversarially-confusable tasks picked a different skill when 12,227
characters of `Trigger keywords:` were removed from the catalogue.

**State the detection limit rather than claiming zero.** SD 0.000 means this instrument could
not separate the arms *at all*, not that the effect is provably nil: with **0 of 10** cases
moving, the rule of three puts the 95% upper bound on the per-case flip rate at roughly
**3/10 ≈ 0.26**. A larger or differently-chosen set could still find something this one cannot.

### How the 10 were assembled, stated plainly

Run 3 completed **9 of 10** before a provider-side `HTTP 402`. The registered denominator was finished on
2026-09-11 by re-running **only `q10_ui_microcopy`** at identical settings (1 case × 3 samples
× 2 arms = 6 calls) and splicing it in. That is completing a fixed denominator, not choosing
between values: the cases are independent prompts, the settings are byte-identical, and the
case was registered before any of this. `q10` read **1.00/1.00**, the same as it had in runs 1
and 2 — which is why it was deliberately *not* imputed earlier even though the value was
predictable. Combined artifact:
[`keyword-tails-final.json`](keyword-tails-final.json).

## The road there: three runs, 186 paid calls, and two defects in the instrument

That is the honest headline, and the runs were still worth their money: they found **two
defects in the instrument**, both of which had been silently shaping the result.

| run | instrument | outcome |
|---|---|---|
| 1 | as registered | `with 0.800 / without 0.900`, **Δ −0.100** — artifact lost to a `KeyError` in a *reporting* line after all 60 calls were paid |
| 2 | reporting fixed | **identical**: `0.800 / 0.900`, Δ −0.100, artifact written |
| 3 | ablation purified + one case relabelled | **aborted at 9 of 10 cases — `HTTP 402` from the provider (see the correction below: *not* exhausted credit)** |

## Why runs 1 and 2 are set aside rather than published

They crossed the registered threshold (Δ ≤ −0.05 → "the tails actively hurt"). Reporting that
would have been wrong, for three reasons visible only in the per-case data:

1. **The CI includes zero.** SD 0.316, SE 0.100, 95% CI **[−0.296, +0.096]**. **One case of
   ten** moved; nine were byte-identical across arms.
2. **That case was mislabelled.** `q7_pod_hardening` expected `sota-kubernetes` for a task
   that is literally *"set securityContext runAsNonRoot, drop Linux capabilities, read-only
   root filesystem on the pods"*. The router's **rule 9** routes pod/container isolation
   mechanics to `sota-sandboxing`, and `sota-kubernetes`'s own description says **"NOT
   pod-level securityContext/seccomp (sota-sandboxing)"**. The `with-keywords` arm answered
   `sota-sandboxing` **3/3 — correct by the library's own rules — and was scored wrong.**
   Corrected, the same two runs read **+0.100 in favour of keeping the tails.** The sign of
   the effect depended entirely on a bad label.
3. **The ablation was impure.** `Trigger keywords:` is not the end of every description: **2
   of 39** (`sota-kubernetes`, `sota-devsecops`) place their negative cross-reference *after*
   the keyword list, so stripping to end-of-string removed **two features** and measured
   their sum. `sota-kubernetes` is the skill in the case that moved — so the whole observed
   effect is attributable to deleting an **exclusion clause**, not a keyword list.

Both defects landed on the single case that produced the entire effect. The number measured
the instrument.

## What run 3 shows, and the line it must not cross

With the ablation isolating one feature (12,227 chars removed, exclusion clauses preserved)
and `q7` relabelled, **0 of the 9 completed cases moved** — every pair identical, including
`q7`, now `1.00/1.00` with `sota-sandboxing` picked 3/3 in both arms.

**That is not the registered number and is not quoted as one.** The registration fixed the
denominator at 10 cases; `q10_ui_microcopy` never ran because the provider returned
`HTTP 402` mid-run. Quoting a rate over a denominator chosen by when the money ran out is exactly what
[RUNS-BLOCKED-ON-CREDIT](../2026-09-09/RUNS-BLOCKED-ON-CREDIT.md) refused to do on
2026-09-09, and `q10` read `1.00/1.00` in runs 1 and 2 — so imputing it would mean picking
the value that confirms the prediction. **The guard aborted rather than dividing by 9, which
is the instrument working.**

## Where that leaves ROADMAP 53

**The matching half is answered and closed: Δ = +0.000.** What remains is a *decision*, not a
measurement, and it belongs to a human — the registration said so before the number existed.

**The two halves now say different things, and both are true:**

| half | answer | basis |
|---|---|---|
| Do the tails help *matching*? | **No measurable effect** (Δ +0.000, 0/10 moved) | this eval |
| Do they *cost* anything? | **12,227 of 37,330 chars — 33% of the corpus** | arithmetic, no calls |

Under ROADMAP 52's mechanism the cost is not paid by the skill carrying the tail: over budget,
whole descriptions are dropped by usage rank, so a tail pushes *some other* skill's entire
description out of the listing. Cutting the tails would take the corpus to ~25k and let far
more entries keep a description at a default budget.

**The argument against cutting is not about matching.** A keyword list can earn its place as
documentation, as a drafting aid, or against a future model that weights it differently — and
this measured one model, one day, ten cases. That trade is the operator's call.

**If they are cut, it is a routing change**: it edits 40 `description` fields, which is the
entire auto-load classifier, so invariant 29 applies and the release must declare a routing
check against `desc-routing-regressions.jsonl`.

**And the deterministic half needs no model calls at all**, so it stands regardless: the
tails are **12,227 of 37,330 characters (33%)** of the description corpus, and ROADMAP 52
established that the listing budget drops **whole descriptions** once the corpus is over it.
Whatever the matching answer turns out to be, that arithmetic is the reason the question is
worth asking — and it is not what this eval measures.

## Corrections this produced elsewhere

- `evals/cases/desc-routing.jsonl` — `q7_pod_hardening` relabelled to `expect:
  sota-sandboxing`, `distractor: sota-kubernetes`, justified by the router rule and the
  skill's own description rather than by the outcome, with that provenance written into the
  case file.
- **The published §5 xref number is not invalidated**: both arms carried the same wrong
  label, so the **Δ is unaffected**. What was understated is the absolute correct-rate,
  reported as `0.80` when one of the ten "misses" was the model being right.
- `run-desc-routing.py` — arm names no longer hardcoded in the reporting line (run 1 paid for
  60 calls and lost its artifact to it), and `--ablate keywords` preserves exclusion clauses.

## One bounded observation, recorded and not acted on

`q4_data_race` reads **0.00 in both arms**: the model answers `sota-golang` 3/3 for *"data
races and an occasional deadlock between two goroutines"*, while the case expects
`sota-async-concurrency` and names `sota-performance` as the distractor. Both skills
legitimately apply — the router's cross-cutting rule 1 says language skills *stack on* domain
skills — so this is a forced single pick between two defensible answers, not obviously a
mislabelling like `q7` was. It is identical in both arms and therefore cannot affect this
delta. Left alone deliberately: having just corrected one case after it produced an
inconvenient result, changing a second on weaker grounds is how a case set drifts toward the
answers its maintainer expects.

## Correction (2026-09-12): the 402 was not exhausted credit

**Written up wrongly first, and the repo had already warned about exactly this.** Run 3's
abort was recorded as *"out of credit"*. The operator confirms there was sufficient balance
at the time, so the `HTTP 402` was a **provider-side fault**. Checked afterwards against
`GET /api/v1/key`, asserting the status before reading any field: **HTTP 200**, key `limit:
null` — uncapped — and authentication healthy.

`evals/DESIGN-real-repo-audit.md` already carries the warning, from an earlier incident where
a credit check parsed an auth failure into *"remaining: $0.00"*: **"A reader would have
concluded 'out of credit' and topped up an account that was never the problem."** That is
precisely what this write-up did — inferring a cause from an error code rather than reading
the balance — and it is the same shape as attributing a symptom to the most available
explanation instead of checking parentage.

**What does not change:** the guard behaviour, which is the only thing the run's abort was
ever evidence for. It refused to divide by 9 and it was right to. **What does change:** the
attributed cause, and the conclusion drawn from it — a 402 is a *transport* failure until
the balance is read, and the remedy for a provider fault is a retry, not a top-up.

**Not re-verified here:** the separate `RUNS-BLOCKED-ON-CREDIT.md` incident of 2026-09-09,
which attributes two other aborts to exhausted credit. That is a different run on a different
day and this correction says nothing about it; it is flagged rather than silently amended.
