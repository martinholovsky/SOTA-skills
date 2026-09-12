# Pre-registration — ROADMAP 49: multi-turn decay against an anchor the filler can dilute

**Written 2026-09-12, BEFORE any model call**, committed before the run. `--lean-anchor` was
added to `run-decay.py` first and the ratio verified; nothing has been scored with it.

## Why the first run could not have answered this

2026-07-14 found **no decay** at K=30 (anchor 1.00 at every depth, control 0.40) and was read
as bounding the problem. It did not bound anything, because the instrument could not have
detected decay at any depth: the anchor is **83,958 characters** and the whole filler corpus
**12,997** — a ratio of **0.15:1**. Thirty turns of trivia cannot dilute an anchor six times
their size.

The item recorded the fix as *"author a bigger filler corpus"*. Priced on 2026-09-12, that is
**~580 additional filler pairs** to reach even 3:1 — which is why it sat since July. The
item's *other* option, "or a deliberately smaller anchor", had never been priced.

## What changed, and it was verified before registering

`--lean-anchor` anchors on **principle 5 alone** — 3,155 characters — instead of the case's
five rules files. **Ratio 0.15:1 → 4.12:1**, using the filler that already exists, for the
cost of one flag. Asserted rather than assumed: the turn-1 message drops from 83,958 to
3,275 characters (**3%**).

**It is also the better question.** Principle 5 is what a routed session carries *before* it
opens any rules file, and it is the component this project credits with the bulk of the
completeness lift. "Does that survive thirty turns of unrelated conversation?" matters more
than the same question about an 84k anchor nobody loads.

## Design

`python3 evals/run-decay.py --lean-anchor --depths 0,12,30` · `c6_webhook` · arms
**anchor / reminder / control** · build `claude-sonnet-4.6`, blind judge `claude-opus-4.8`,
scored against the case's 10-item rubric. 3 arms × 3 depths = **9 generations + 9 judge
calls**.

## Metrics and thresholds, fixed now

- **DECAY = anchor@K0 − anchor@K30.** The headline.
- **REMINDER RECOVERY = reminder@K30 − anchor@K30** — whether the per-prompt hook analog
  recovers what depth costs. This is the arm that matters for the shipped product, since the
  re-injection hook is exactly that mechanism.
- **Null band ±0.10** on a 10-item rubric at n=1 per cell: one rubric item is 0.10, so
  nothing smaller than a single criterion is interpretable. Deliberately wider than the
  ±0.03 used on multi-sample evals, because this is **n=1 per cell** and pretending otherwise
  would be the error this project keeps catching.

## Predictions, recorded before seeing anything

1. **DECAY > 0.10** — i.e. decay becomes visible now that the filler can dilute. This is the
   whole reason for the change and is the falsifiable claim.
2. **Reminder recovers most of it** (reminder@K30 ≥ anchor@K30). If the re-injection hook
   analog does *not* recover, that is a finding about a shipped mechanism and outranks
   prediction 1.

## The risk that would void the run, stated first

**A floor effect.** If the lean anchor scores at or near the control (0.40) already at K=0,
there is no headroom to lose and DECAY ≈ 0 would mean nothing. **Check `anchor@K0` against
`control@K0` before reading DECAY at all**: if that gap is under ~0.20, the run bounds
nothing and must be reported as inconclusive rather than as a null. The 2026-07-14 run had a
1.00/0.40 gap with the full anchor; principle 5 alone is 3% of that text and may not hold it.

## What this will not establish

- **n=1 per cell**, one case, one model, one day. It can show a direction, not a magnitude.
- **One case (`c6_webhook`)**, so "decay" here means decay on this rubric.
- The filler is *trivia*, deliberately off-topic. Semantically-close distractors would
  plausibly hurt more, and this says nothing about them.

## Status

Not yet run.
