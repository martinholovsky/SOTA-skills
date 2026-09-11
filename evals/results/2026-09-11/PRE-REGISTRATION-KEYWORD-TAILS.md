# Pre-registration — ROADMAP 53: do the `Trigger keywords:` tails earn their characters?

**Written 2026-09-11, BEFORE any model call, and committed before the run.** The ablation
was added to `evals/run-desc-routing.py` first (`--ablate keywords`) and watched to land;
nothing has been run against it.

## Why this exists now

The tails were always a cost, and until ROADMAP 52 there was no way to price them. 52
established, by reading the shipped CLI, that Claude Code drops **whole descriptions** once
the listing corpus exceeds its budget, choosing the losers by recent usage. So a trailing
keyword list is not a cost paid by the skill carrying it — it is a cost paid by **every other
skill in the set**, because it pushes the corpus further over the budget and makes one more
entry render as a bare name. That reframes the question from "is this text tidy?" to "is this
text worth another skill's entire description?"

**Measured inputs, before the run:** 42 descriptions total **37,330** characters. **40** carry
a `Trigger keywords:`/`Triggers —` tail. Stripping them removes **12,456** characters across
the **39** the runner sees (it globs `sota-*`, excluding the router) — **34%** of the corpus.

## The question, stated so it can fail

**Does removing the trailing keyword list change description-based routing accuracy?**

## Design

- Instrument: `evals/run-desc-routing.py --ablate keywords`, which presents the **whole
  catalogue** in one prompt and asks for the single most relevant skill. Objective scoring:
  exact skill-name match, no judge.
- Cases: `evals/cases/desc-routing.jsonl`, **10** adversarially-confusable tasks.
- **3 samples per case per arm, temp 0.7, `anthropic/claude-sonnet-4.6`** — deliberately the
  same configuration as the published baseline so the treated arm doubles as a replication.
- Arms: `with-keywords` (descriptions exactly as committed) vs `without-keywords`.
- Cost: 10 × 3 × 2 = **60 calls**.

## Thresholds, fixed now

- **Primary metric:** mean correct-pick rate. **Δ = with − without.**
- **Null band ±0.03**, this project's established noise floor at temp 0.7.
- **Δ ≥ +0.05** → the tails earn their place on matching; keep them and solve the budget
  another way.
- **|Δ| ≤ 0.05** → no measurable matching value. Combined with their 34% share, that is an
  argument to cut them — but the decision still belongs to a human, because a keyword list
  can earn its place as documentation even when it buys no matching.
- **Δ ≤ −0.05** → the tails actively hurt; cut them regardless of budget.
- **Secondary metric:** distractor-pick rate. It is already **0.00** in the published
  baseline, so it is at the floor and can only detect *harm*, never improvement. Recorded,
  not used to decide.

## Prediction, recorded before seeing anything

**A null (|Δ| ≤ 0.03).** The capability sentence that opens each description already carries
the discriminating vocabulary, and the tails are largely a restatement of it. Stating this
first is the point: if the result is a null, this registration is what stops it being read as
a post-hoc rationalisation, and if it is not a null, the prediction was wrong and that is the
finding.

## Built-in control

The published baseline for this instrument is **0.80 correct / 0.00 distractor-pick** (10
cases, 3×, temp 0.7, sonnet-4.6). The `with-keywords` arm is that same measurement. If it
does not land near 0.80, something other than the ablation has moved and **the delta is not
trustworthy** — report that instead of the delta.

## What this does NOT establish, stated before the number exists

1. **It does not measure the budget effect at all.** The runner hands the model the whole
   catalogue in one prompt, so it measures matching *given the text is present*. Whether the
   text survives the listing budget is a separate, deterministic question answered by
   arithmetic, not by this eval. Do not let a null here be read as "the tails are harmless".
2. **The cases were authored for a different ablation** (the cross-refs). Checked before
   running rather than assumed: all **10** have vocabulary overlap between the task and the
   expected skill's tail (`sigma`, `securitycontext`, `kafka`, `deserialization`, `deadlock`
   …), so the treatment is genuinely visible and a null would not be structural. But they
   were not *selected* to stress keyword matching, and a set written for that purpose might
   find an effect this one cannot.
3. **10 cases, one model, one day.** A routing number is a gap between a description and a
   classifier, and the classifier side moves.
4. **Distractor-pick is at its floor**, so half the instrument can only report harm.

## Status

Not yet run. Live spend on the operator's account, authorised 2026-09-11.

---

## Amendment, written 2026-09-11 AFTER runs 1 and 2 and BEFORE run 3

Runs 1 and 2 executed as registered (60 calls each) and produced **identical** results:
`with-keywords 0.800 / without-keywords 0.900`, **Δ = −0.100**, distractor-pick 0.000 in
every arm. Run 1's artifact was lost to a `KeyError` in a *reporting* line that still
hardcoded the xref arm names — all 60 calls had already been paid for. Run 2 reproduced it
byte-for-byte after the fix.

**The registered threshold was crossed (Δ ≤ −0.05, "the tails actively hurt"), and it must
not be reported that way**, for three reasons found by looking at the per-case data rather
than the summary:

1. **The 95% CI includes zero.** SD 0.316, SE 0.100, CI **[−0.296, +0.096]**. **One case of
   ten moved**, completely (3/3 in both arms). Nine were identical.
2. **That case was mislabelled.** `q7_pod_hardening` expected `sota-kubernetes` for a task
   that is literally *"set securityContext runAsNonRoot, drop Linux capabilities, read-only
   root filesystem on the pods"*. The router's **rule 9** sends pod/container isolation
   mechanics to `sota-sandboxing`, and `sota-kubernetes`'s own description says **"NOT
   pod-level securityContext/seccomp (sota-sandboxing)"**. The `with-keywords` arm answered
   `sota-sandboxing` 3/3 — **correct by the library's own rules** — and was scored wrong.
   Corrected, the same runs read **+0.100** in favour of keeping the tails.
3. **The ablation was impure.** `Trigger keywords:` is not the end of every description: **2
   of 39** (`sota-kubernetes`, `sota-devsecops`) carry their negative cross-reference *after*
   the keyword list, so stripping to end-of-string removed **two features** and measured
   their sum. `sota-kubernetes` is exactly the skill in the case that moved, so the entire
   observed effect is attributable to losing an **exclusion clause**, not a keyword list.

So the honest reading of runs 1 and 2 is **not** "−0.100, the tails hurt". It is: *the
instrument had a mislabelled case and an impure ablation, and both landed on the single case
that produced the whole effect.* The number measures the defects.

### What changed before run 3, and why each is legitimate

- **`strip_keywords()` preserves any exclusion clause** while removing the keyword list, so
  the ablation isolates one feature. Removed text: 12,227 chars (was 12,456).
- **`q7_pod_hardening` relabelled** to `expect: sota-sandboxing`, `distractor:
  sota-kubernetes`. Justified by the two standards above — the router rule and the skill's
  own description — **not** by the outcome. Provenance recorded in the case file: the defect
  surfaced *from* a result, and that is stated rather than hidden.

### Thresholds for run 3 — unchanged, and deliberately not moved toward what was seen

Null band **±0.03**, decision at **±0.05**, primary metric mean correct-rate, Δ = with −
without. Same 10 cases, 3 samples, temp 0.7, `claude-sonnet-4.6`.

**Revised prediction:** still a **null**, and now more confident — the one case that moved is
explained by a feature the ablation no longer touches. If run 3 shows a null, the answer to
ROADMAP 53 is that the tails buy no measurable *matching* value, which is a finding about
matching only and says nothing about the budget question, per limit 1 above.

**All three runs will be reported**, including the two whose number is being set aside, and
the reason for setting it aside is written above before run 3 was started.
