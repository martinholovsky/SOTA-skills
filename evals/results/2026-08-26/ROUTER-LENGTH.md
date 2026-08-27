# Does the router still route when it gets longer? (2026-08-26)

**Question.** `skills/sota/SKILL.md` sat at exactly **500/500 lines** from 2026-07-30, so
every addition since was paid for by compressing something else. The cap is *our*
invariant mirroring the platform's advisory *"keep `SKILL.md` under 500 lines"* — it is
**not** a loader limit; nothing truncates a skill at load. So the real question is whether
**routing degrades as the file grows**, and that had never been measured.

Predictions were fixed before the run: base ≥ 0.98, all arms within 0.05 of base,
**falsified if any arm fell ≥ 0.10 below base** (two whole cases).

## Result — flat

`evals/run-router-length.py`, `cases/router.jsonl` (20 cases), `anthropic/claude-sonnet-5`,
3 samples, temp 0.7.

| arm | lines | prompt tokens | recall | vs base |
|---|---|---|---|---|
| no-router (control) | 0 | 1,367 | 0.867 | — |
| base | 501 | 18,302 | **1.000** | — |
| +400 after | 902 | 29,005 | **1.000** | +0.000 |
| +400 before | 902 | 29,005 | **1.000** | +0.000 |
| +800 before | 1,302 | 39,772 | **1.000** | +0.000 |

**No degradation at 2.6× the length**, with the routing table pushed 800 lines deeper and
the prompt at ~40k tokens. Raw: [`router-length.json`](router-length.json).

## Two things that validate the measurement

- **The untreated arm reproduced 0.867 exactly** — the same value as the 2026-08-25
  routing run. It cannot see the router, so it is a free negative control on this
  measurement (`evals/README.md`, 2026-08-21 convention).
- **The token arithmetic closes.** `count_tokens` gives the 500-line router **16,934**
  tokens; the no-router prompt is 1,367; base came back at 18,302. 16,934 + 1,367 = 18,301.
  The Anthropic and OpenRouter figures agree to one token.

## Limits — stated before the run, not after

- **The metric is at ceiling.** Base is already 1.000, so the instrument can only detect a
  *drop*, and only one ≥ 0.05 (20 cases → one case = 0.05). A saturated measure is weak
  evidence for "no effect".
- **Filler is inert by construction** — verified to contain no skill name and no `sota`
  string. It therefore tests **length and depth**, not **competition** between real rules.
  Adding 800 lines of genuine guidance is a different experiment, and the completeness
  ablation already hints at the answer there: `+rules` alone stalled at **0.89** while a
  short salient reminder reached **0.99**.
- **Routing is the easy task** — the table is in the prompt. Rule *application* under a
  long build is the harder case and was not tested.

## What was done with it

**Not** raise the cap. The finding says length is not the binding constraint; it does not
say growth is free. The router costs **16,442 tokens** on every task that loads it
(`count_tokens`, `claude-sonnet-5`, at 484 lines) — ~3.3× the ~5k guidance — so each added
line is paid forever by every task.

So the detail was moved out instead: BUILD/AUDIT reasoning into `skills/sota/rules/`,
loaded on demand (PR #284). The router went **500 → 484 lines**, buying 16 lines of
headroom. Be precise about the size of that win: the token saving is **16,934 → 16,442,
about 3%**. The point was headroom and the end of compress-on-every-addition, not context
economy.

## Follow-up, 2026-08-27 — real rules behave exactly like inert filler

The limit stated above was that inert filler tests **length**, not **competition** between
real rules. So the padding was rebuilt from genuine rules prose with every routing signal
stripped (`sota-*` names and `rules/NN` references removed; the builder asserts no
`sota-` survives, because padding that leaked a skill name would make any drop unreadable).

| arm | lines | recall | vs base |
|---|---|---|---|
| no-router (control) | 0 | 0.853 | — |
| base | 499 | **1.000** | — |
| +400 **inert filler** | 900 | 0.992 | −0.008 |
| +400 **real rules prose** | 904 | 0.992 | −0.008 |

**Identical, and both inside the noise.** 20 cases means one case is 0.05; these deltas are
0.008. So on the routing axis, 400 lines of genuine competing guidance is indistinguishable
from 400 lines of filler *and* from no padding at all. Raw:
[`../2026-08-27/router-length-real-rules.json`](../2026-08-27/router-length-real-rules.json).

**This does not close ROADMAP 25.** Routing is a retrieval-ish task with the table in the
prompt, and it is at ceiling. The question that matters is **rule application** under a long
build — the completeness axis — and that remains unmeasured. Read this as: *the cheap axis
shows nothing, which is weak evidence and not permission to grow the router.*

**A near-miss worth recording.** This run overwrote the 5-arm artifact above, because the
output path was hardcoded to a fixed date. Restored from git; the runner now writes a dated
filename. The same edit also gave the script an `if __name__ == "__main__"` guard — its
sweep had been running at *module level*, so merely importing it made live API calls.

**A correction this run forced:** [CONTEXT-MANAGEMENT.md](../../../docs/CONTEXT-MANAGEMENT.md)
had the router at *"~10,211 tokens — 2× the budget"*, a chars/4 heuristic. Measured, it is
**16,442 — 3.3×**. The heuristic under-reported the router's context cost by ~60%.
