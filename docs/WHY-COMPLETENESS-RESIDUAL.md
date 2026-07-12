# Why a with-library build still drops rate limiting / transport — and the fix

The completeness eval (see [WHY-IT-WORKS.md](WHY-IT-WORKS.md)) showed a residual:
even with the rules in context and a self-audit step, a "build X" run sometimes
still omits **rate limiting** and **transport enforcement** (measured: transport
in 3 of 7 tasks, rate limiting in 2 of 7). This documents *why* — the cause is
**not** what an early version of these docs claimed ("a coverage gap"). It is a
**salience / context-length attention effect**, and it is well studied.

## What it is NOT: a coverage gap

The first hypothesis was that the forgotten rule simply wasn't loaded. **The data
refutes this.** In all 7 completeness tasks, transport *and* rate-limiting were
mentioned **and** appeared in a pasted `## Audit checklist` — the guidance was in
scope, with a checklist item — and the model still dropped it. In `c6_webhook`
the model implemented the *body-size-limit* from `webhooks.md:177` and dropped
the *rate-limit* clause **from the same sentence**. That is selective
instruction-following, not missing coverage.

## What it is: attention degrades with context length + constraint count

Two well-replicated findings explain it:

- **Context rot** — LLM output quality degrades as input grows, *even below the
  context-window limit*; every one of 18 frontier models tested (incl. Claude
  Opus 4) shows it, and *semantically-close distractors* (our dozens of similar
  security checklist items) hurt more than generic text. It is an architectural
  property of transformer attention, not a training gap.
  ([Chroma, 2025](https://www.trychroma.com/research/context-rot);
  [Liu et al. 2023, "Lost in the Middle"](https://cs.stanford.edu/~nfliu/papers/lost-in-the-middle.arxiv2023.pdf)
  — U-shaped recall, mid-context items lose 15–25 points.)
- **Instruction-count degradation** — the probability of satisfying *every*
  instruction decays ~exponentially with the number of constraints; models
  "overweight what's most recent or salient … satisfying one rule while quietly
  violating another." A **reminder sentence recovers compliance to 90–100 %.**
  ([arXiv 2507.11538](https://arxiv.org/html/2507.11538v1))

In multi-turn / agentic use it gets *worse* (not different): instruction
adherence drops monotonically with turn count and the system prompt's influence
gets diluted ([Laban et al., "LLMs Get Lost in Multi-Turn Conversation"](https://arxiv.org/pdf/2505.06120)).
But note: our eval measures a **single call**, so the effect originates without
any workflow, subagent, or chain — those only amplify it.

## The experiments (c6_webhook, the worst case; `results/2026-07-13/`)

| variant | context | result |
|---|---|---|
| baseline (rules + self-audit) | 72 KB | drops rate-limit + transport |
| **+ explicit "MUST rate-limit + enforce TLS"** | 72 KB | **both present (1.00)** — salience fixes it |
| **+ the actual missing rule files** | 100 KB | **worse — both still absent** (context rot) |
| Opus 4.8 instead of Sonnet | 72 KB | different subset dropped (architectural) |
| minimal context (one file) | 12 KB | low-salience clause still dropped |
| **+ the shipped operating principle 5** | 73 KB | c2/c5/c6 → **1.00**, c7 → 0.91 |

The decisive pair: **adding more guidance made it worse** (context rot), while a
**short, salient reminder made it perfect**. The library's shipped *operating
principle 5* (a short "every endpoint: rate-limit + TLS + tests + logging"
reminder) recovers the residual in 3 of 4 cases; the 4th recovers the target item
but drops a *different* one — evidence of a finite "constraint budget" that no
single reminder fully removes.

## What the library does about it (`skills/sota/SKILL.md`)

Fight the attention shape, don't ignore it — put constraints where attention is
strong (start + end) and keep context lean:

1. **Load lean** (BUILD step 2) — open only the matching rules files; extra,
   similar-looking guidance *measurably lowers* compliance. Lean is correctness.
2. **Plan with the checks in the plan** (BUILD step 3) — name the non-negotiables
   up front (start-of-context strength) so they become a tracked artifact.
3. **Self-audit LAST, re-reading the checklists** (BUILD step 4) — a terminal
   re-read exploits recency and re-surfaces the faded mid-context items; for a
   large build, run it as a **separate pass over the diff** (a fresh, minimal
   context has no rot).
4. **Short, salient universal non-negotiables** (operating principle 5) — kept
   deliberately short; a long principle rots too.
5. **Deterministic gates for the critical few** — a lint/CI check that fails when
   an endpoint has no rate-limiting or TLS moves the invariant out of "attention"
   entirely (recommended; the host, not this library, runs it).

## Consequence for the measured number

The eval originally pasted the domain rules + self-audit but **not** principle 5,
so it under-measured the real library. With principle 5 included (what a real
agent loads via the router), 7-task completeness is **0.60 → 0.99 (+0.39)**, 6 of
7 tasks perfect — up from the **0.93** measured without it. `run-completeness.py`
now includes principle 5 so the number reflects real usage. The lone non-perfect
case (`c1`, 0.92) is telling: it was 1.00 *before* principle 5 and now drops
request-body-size-limit — the finite constraint budget in action (a salient
reminder recovers the reminded items but can nudge out a different low-salience
one). That is also why the number isn't gamed: the rubric items principle 5 names
are not automatically satisfied.
