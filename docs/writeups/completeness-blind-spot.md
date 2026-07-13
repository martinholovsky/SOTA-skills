# The completeness blind spot: why a top model drops rate limiting — and adding more rules makes it worse

*Draft for publication (LinkedIn / blog). Every number here is reproducible from
[`evals/`](../../evals/) in this repo; sources are linked inline. Framing is
deliberately **library vs. an unguided model** — not vs. any other library, which
we have not benchmarked.*

---

## The one-paragraph version

Ask a state-of-the-art model to "build a webhook receiver" or "build a profile-picture
upload," with no security hints, and it writes clean, working code that is
**missing about half of the production essentials** — rate limiting, transport
enforcement, idempotency, tests. Not because it doesn't know them. Because they
are *cross-cutting*, low-salience details that fade in a long generation. We
measured this, tried to fix it by giving the model **more** guidance, and it got
**worse**. What actually fixed it was a *short* reminder in the right place. Here
is the data and the mechanism.

## The measurement

We ran a clean, blind eval: raw model API (no assistant config), a minimal
"build X for my app" prompt with **no** security or logging cues, and a
**different** model grading each result blind to how it was produced. Coverage =
fraction of a fixed rubric of universal best practices the code actually
implements. ([harness](../../evals/run-completeness.py);
[method](../WHY-IT-WORKS.md))

Two real examples, base model with nothing added:

| Task | Base-model coverage | What it silently dropped |
|---|---|---|
| Payment **webhook receiver** | **0.50** | idempotency, body-size limit, rate limiting, transport/TLS, tests |
| Profile-picture **upload** | **0.55** | safe storage location, decompression-bomb defense, rate limiting, error hygiene, tests |

Across 7 such tasks the base model averages **0.60** — it embeds ~60% of best
practices and *systematically* skips the same peripheral four: tests, rate
limiting, structured logging, transport hardening. These aren't exotic. They're
the difference between a demo and a service.

## The surprise: more guidance made it worse

The obvious fix is "give the model the rules." We did — pasted the relevant
security rules into the prompt. Coverage rose, but a residual stuck: even with
the rule *in context*, and even with a checklist item naming it, the model still
dropped rate limiting and TLS on some tasks.

So we tested the coverage hypothesis directly. On the worst case (the webhook),
we **added the full missing rule files** to the context. Result: **worse — both
still absent.** Then we replaced all that with **one short line** — "every
endpoint: rate-limit + enforce TLS" — and it went to **perfect**.

| Variant | Context size | Result |
|---|---|---|
| rules + self-audit | 72 KB | drops rate-limit + transport |
| **+ the actual missing rule files** | 100 KB | **worse — still absent** |
| **+ one short salient reminder** | 72 KB | **both present** |

([experiments + sources](../WHY-COMPLETENESS-RESIDUAL.md))

## Why — it's an attention effect, not a knowledge gap

Two well-replicated findings explain it:

- **Context rot.** LLM output quality degrades as input grows, *even below the
  context-window limit*, and **semantically similar distractors** (dozens of
  look-alike security checklist items) hurt more than generic filler. It's a
  property of transformer attention.
  ([Chroma 2025](https://www.trychroma.com/research/context-rot);
  ["Lost in the Middle", Liu et al. 2023](https://cs.stanford.edu/~nfliu/papers/lost-in-the-middle.arxiv2023.pdf))
- **Instruction-count decay.** The odds of satisfying *every* instruction fall
  roughly exponentially with the number of constraints; a single reminder
  recovers compliance to 90–100%.
  ([arXiv 2507.11538](https://arxiv.org/html/2507.11538v1))

That is exactly the shape we saw: piling on rules adds distractors (rot); a short
reminder restores salience. In multi-turn / agentic use it gets *worse*, not
different — our number is from a **single call**, so chains only amplify it.

## Why this is the most useful thing a skill library can fix

Note which failure this is. A tool-using agent can recover a **freshness** gap by
searching the web. It cannot recover this one: **an agent will not search "should
I add rate limiting"** — it just omits it. Completeness is the gap that web access
doesn't close, which makes it the highest-value thing to engineer against.

## What actually fixes it (the design, not a bigger prompt)

You fight the attention shape; you don't out-muscle it with volume:

1. **Load lean** — only the rules that match the task. Extra look-alike guidance
   *measurably lowers* compliance. Lean is correctness, not economy.
2. **Plan with the checks named up front** — constraints stated at the start of
   context (where attention is strong) and turned into a tracked artifact.
3. **Self-audit LAST** — a terminal re-read of the checklist exploits recency and
   re-surfaces the faded mid-context items; for a big change, run it as a separate
   pass over the diff (a fresh context has no rot).
4. **Keep the universal reminder short** — a long "non-negotiables" list rots too.
5. **Make the critical few deterministic** — a lint/CI check that fails when an
   endpoint has no rate limit or TLS moves the invariant out of "attention"
   entirely.

Measured effect of applying this: coverage **0.60 → 0.99** across the 7 tasks,
6 of 7 perfect — the webhook and upload above both go to **1.00**.
([ablation](../WHY-IT-WORKS.md))

## It holds up in a real agent, not just a prompt

We just re-checked this outside the simulation: seven live agents built these same
tasks through the full workflow (load-lean → plan → terminal self-audit). The
self-audit step didn't just re-surface the cross-cutting items — it **caught and
fixed real bugs the first pass introduced**: a webhook build found its own
`/docs` endpoint exposed in production and an unbounded DB critical section that
could hang a request; a queue-worker build found a task-cancellation bug that
would have orphaned in-flight work.
([validation](../../evals/results/2026-07-13/LIVE-BUILD.md))

## The honest boundary

This is a **completeness** result — building software from a bare prompt. On
*recognizing* a textbook vulnerability in existing code, the same measurement
shows the library adds **nothing** (+0.00): a capable model already spots isolated
vulns, and — as we found this week — even spots **cross-file** ones when the whole
repo fits in its context.
([repo-audit result](../../evals/results/2026-07-13/REPO-AUDIT.md)) We report that
too, because a number you only quote when it's flattering isn't a measurement.

---

*Reproduce every figure: `python3 evals/run-completeness.py` (set
`OPENROUTER_API_KEY`). Harness, cases, and per-run data are in
[`evals/`](../../evals/).*
