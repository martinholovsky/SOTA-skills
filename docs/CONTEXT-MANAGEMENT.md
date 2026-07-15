# Keeping the model applying the rules (context management)

**The short answer to "how do we re-inject rules so the model doesn't forget them?"**
A `UserPromptSubmit` hook in `~/.claude/settings.json` re-states the routing
directive on **every** prompt, so a rule loaded 30 turns ago is restated fresh
each turn. It's the third layer of
[README → Always-on routing](../README.md#always-on-routing-recommended), and
`scripts/install.sh --routing` sets it up. (It fires every prompt, not only when
the window is "full.") But that hook is one of **six** defenses; this page is the
whole picture in one place.

## The problem

LLMs don't apply every loaded rule equally. Two effects work against you:

- **Within a single generation** — output quality degrades as input grows *even
  below the context limit*, and semantically-similar distractors (dozens of
  look-alike rules) hurt most. Low-salience, cross-cutting items (rate limiting,
  transport, tests) fade first. Measured and root-caused in
  [WHY-COMPLETENESS-RESIDUAL.md](WHY-COMPLETENESS-RESIDUAL.md) — notably, *adding*
  more rules made it **worse**; a short salient reminder fixed it.
- **Across a long session** — the literature finds instruction adherence drops
  with turn count as a directive recedes into history (Laban et al., "LLMs Get
  Lost in Multi-Turn Conversation"). We now measure this ourselves (below).

## The six defenses (what the library actually does)

Fight the attention shape; don't out-muscle it with volume.

1. **Load lean** — open only the rules files that match the task. Extra
   look-alike guidance *measurably lowers* compliance. (Router BUILD step 2.)
2. **Plan with the checks named up front** — list the non-negotiables before
   coding, so they're a tracked artifact at the strong start of context. (BUILD step 3.)
3. **Self-audit LAST** — a terminal re-read of each rules file's Audit checklist
   exploits recency and re-surfaces faded mid-context items; for a big change, run
   it as a separate pass over the diff (fresh context, no rot). (BUILD step 4;
   [`skills/sota/SKILL.md`](../skills/sota/SKILL.md).)
4. **A short, salient universal reminder** — the router's *operating principle 5*
   (rate-limit + transport + tests + logging on any endpoint), kept deliberately
   short because a long reminder rots too. ([`skills/sota/SKILL.md`](../skills/sota/SKILL.md).)
5. **Per-prompt re-injection** — the `UserPromptSubmit` hook that re-states the
   routing directive every prompt (the answer up top;
   [README](../README.md#always-on-routing-recommended)). This is the defense that
   directly targets *multi-turn* decay.
6. **Deterministic gates for the critical few** — a lint/CI check that fails when
   an endpoint has no rate limiting or TLS moves the invariant out of "attention"
   entirely. ([README → Enforcing the gates](../README.md#enforcing-the-gates).)

## How we measure it

- **Single-call salience** — the completeness eval + five controlled experiments
  in [WHY-COMPLETENESS-RESIDUAL.md](WHY-COMPLETENESS-RESIDUAL.md). Result: with the
  full library (incl. principle 5) completeness is **0.60 → ~1.00**; the residual
  is a salience effect, not a coverage gap.
- **Multi-turn decay** — [`evals/run-decay.py`](../evals/run-decay.py) builds a
  session where guidance is loaded at turn 1, followed by K turns of unrelated
  filler, then a build task; a blind judge scores whether the guidance is still
  applied. Arms: *anchor* (guidance once), *reminder* (guidance + a generic
  per-prompt reminder, the hook's analog), *control* (none).

  **First run (2026-07-14, `c6_webhook`, K ∈ {0,15,30}):**

  | arm | K=0 | K=15 | K=30 |
  |---|---|---|---|
  | control (no guidance) | 0.40 | 0.40 | 0.40 |
  | anchor (guidance at turn 1) | 1.00 | 1.00 | 1.00 |
  | reminder (guidance + per-prompt reminder) | 1.00 | 1.00 | 1.00 |

  **No decay at this scale** — an ~18.6K-token (~72 KB) guidance block loaded at turn 1 was still
  fully applied after 30 unrelated turns. That *bounds* the problem (moderate
  sessions are safe here) but does **not** find the breaking point: the ~3.2K tokens of
  filler is small next to the guidance, so it can't dilute it. A real decay test
  needs much larger intervening context (or a smaller anchor); the harness takes
  `--depths` and a bigger filler to scale up. Logged as roadmap item 5, still open
  ([`evals/results/2026-07-13/DECAY.md`](../evals/results/2026-07-13/DECAY.md)).

## See also

- [README → Always-on routing](../README.md#always-on-routing-recommended) — set up all six layers
- [WHY-COMPLETENESS-RESIDUAL.md](WHY-COMPLETENESS-RESIDUAL.md) — the why, with experiments
- [docs/INDEX.md](INDEX.md) — find anything else
