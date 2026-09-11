# ROADMAP 53 — do the `Trigger keywords:` tails earn their characters?

**2026-09-11** · `evals/run-desc-routing.py --ablate keywords --samples 3 --temp 0.7` ·
`anthropic/claude-sonnet-4.6` · 10 cases from `desc-routing.jsonl` ·
**pre-registered** in [PRE-REGISTRATION-KEYWORD-TAILS.md](PRE-REGISTRATION-KEYWORD-TAILS.md),
committed before any call, and **amended before run 3** with the reason written down first.

## Status: NOT ANSWERED. Three runs, 180 paid calls, and no quotable number.

That is the honest headline, and the runs were still worth their money: they found **two
defects in the instrument**, both of which had been silently shaping the result.

| run | instrument | outcome |
|---|---|---|
| 1 | as registered | `with 0.800 / without 0.900`, **Δ −0.100** — artifact lost to a `KeyError` in a *reporting* line after all 60 calls were paid |
| 2 | reporting fixed | **identical**: `0.800 / 0.900`, Δ −0.100, artifact written |
| 3 | ablation purified + one case relabelled | **aborted at 9 of 10 cases — HTTP 402, out of credit** |

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
denominator at 10 cases; `q10_ui_microcopy` never ran because the account hit `HTTP 402`
mid-run. Quoting a rate over a denominator chosen by when the money ran out is exactly what
[RUNS-BLOCKED-ON-CREDIT](../2026-09-09/RUNS-BLOCKED-ON-CREDIT.md) refused to do on
2026-09-09, and `q10` read `1.00/1.00` in runs 1 and 2 — so imputing it would mean picking
the value that confirms the prediction. **The guard aborted rather than dividing by 9, which
is the instrument working.**

## Where that leaves ROADMAP 53

**Open, with a provisional direction and a cheap finish.** The registered prediction was a
null; nine of ten cases are consistent with it on a corrected instrument. One case and a
top-up separate this from an answer.

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
