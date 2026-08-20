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
   directly targets *multi-turn* decay. **Write each rule as a numbered imperative
   of equal weight** — a directive demoted to a subordinate clause is re-injected
   every turn and ignored every turn (measured in the field; see
   [the precondition section](#the-precondition-all-six-defenses-assume-measured-in-the-field-2026-08-05)).
6. **Deterministic gates for the critical few** — a lint/CI check that fails when
   an endpoint has no rate limiting or TLS moves the invariant out of "attention"
   entirely. ([README → Enforcing the gates](../README.md#enforcing-the-gates).)

## Size limits: what to actually do (settled 2026-08-02)

Every size number that governs this library, verified against three official sources
(`agentskills.io/specification`, the `platform.claude.com` Agent Skills reference and
its best-practices page, and the Claude Code memory/skills docs), with the standing
decision for each. **Nothing here is a guess; where a number is a heuristic it says so.**

| Limit | Kind | Us | Do |
|---|---|---|---|
| `name` ≤ 64 chars | **hard** | fine | nothing — gated (inv. 4) |
| `description` ≤ 1024 chars | **hard** | router at **1024/1024** | **watch it** — no slack; any new domain in the description means trimming another |
| no XML tags in `name`/`description` | **hard** | fixed 2026-08-02 | nothing — gated (inv. 4) |
| no reserved words (`anthropic`, `claude`) in `name` | **hard** | fine | nothing — gated (inv. 4) |
| `description` + `when_to_use` ≤ 1,536 in the listing | **hard** truncation | 1024, no `when_to_use` | nothing — 512 spare |
| `SKILL.md` < 500 lines | recommendation | router at **500/500** | nothing — gated (inv. 1), but **no slack: the next router addition must trim first** |
| `SKILL.md` body < 5,000 tokens | recommendation | router ≈ **9,945** (2×) | **accept, don't restructure** — see below |
| `rules/*.md` length | **no budget** — stage-3 resources | 162 over 200 lines | nothing — **long is correct by design**; the spec says move detail *into* these |
| TOC for reference files > 100 lines | recommendation | 242 without one | **skip** — tested, no retrieval benefit at 4× our longest file |
| first 5,000 tokens kept on compaction re-attach | **hard** truncation | router loses ~half | **accept** — a later invocation reloads it in full |

**Why the router stays as it is.** It is the one file exceeding a documented
recommendation, and the temptation is to restructure it into the spec's "high-level
guide with references" pattern. Three reasons not to, in order of weight:

1. **It would invalidate the flagship number.** `ROUTER_BUILD_SHA` pins the BUILD
   section that `run-completeness.py` mirrors; moving those steps into a referenced
   file breaks comparability with every historical **+0.39** run.
2. **The compaction truncation is self-healing.** It applies to the copy *carried
   forward* past a summary. A subsequent invocation reads `SKILL.md` again in full —
   and defense 5, the per-prompt routing directive, is what prompts that re-invocation.
   (Inferred from the documented behaviour; not separately observed.)
3. **The overrun costs context, not correctness.** Nothing truncates at load; all
   three sources agree there is no hard size cap.

Revisit only when the router must **grow** — it is at 500/500 lines, so growth forces
a trim regardless, and that is the moment to do both at once.

## Do long rules files need a table of contents? Tested — no (pilot, 2026-08-02)

Anthropic's skill-authoring guidance says: *"For reference files longer than 100
lines, include a table of contents at the top. This ensures Claude can see the full
scope of available information **even when previewing with partial reads**."* **242 of
this repo's rules files exceed 100 lines and none carries a TOC**, so the question is
whether that costs anything.

It was tested rather than assumed, because the claim rests on a *mechanism* — partial
reads — that may simply not occur here. Four arms, one agent each, an unguessable
canary constant (`PROBE_QUARANTINE_RUNS = 17`) planted so a correct answer proves
retrieval rather than prior knowledge. The prompt never mentions position, length or
tables of contents, and **the arm is not encoded in any path** (opaque workspace IDs),
because two agents in an earlier study read their arm out of a directory name.

| Arm | File | Canary depth | TOC | Canary found | Tool calls |
|---|---|---|---|---|---|
| A control | 434 lines | 99% | no | **yes** | 1 |
| B treatment | 446 lines | 99% | **yes** | **yes** | 1 |
| C positive control | 434 lines | **1%** | no | **yes** | 1 |
| D stress | **1,719 lines / 92 KB** | 99% | no | **yes** | 2 |

**The positive control is what makes this readable.** Arm C moved the canary to the
top; it scored identically to A, so there was no depth effect for a TOC to correct.
The agents read the files whole — two said so unprompted ("read the file in full
(434/446 lines)"), and arm D's agent reported the canary's exact line range in a
1,719-line file. Arm B's only measurable effect was **+183 tokens** of context for the
TOC itself.

**Conclusion: the 242-file TOC sweep is not justified**, and would be pure added
context cost at these lengths.

**Limits, stated because they bound the claim.** *n* = 1 per arm — a pilot, not a
result, and not on the scoreboard. It exercises one path: the `Read` tool in a Claude
Code sub-agent on a **directly named** file. The guidance's own stated trigger is
different — *"Claude may partially read files when they're referenced **from other
referenced files**"* — i.e. nested references. That condition is untested here, and it
does not arise in this library anyway, because `SKILL.md → rules/NN.md` is already the
**one level deep** structure the same guidance prescribes. Finally, the canary sat
after the `## Audit checklist` heading, which two agents flagged as anomalous; that
salience may have aided detection.

## The 500-line cap is a proxy, and a loose one (measured 2026-08-02)

The Agent Skills specification states the budget in **tokens**, not lines:

> **Progressive disclosure** — 1. Metadata (~100 tokens): `name` and `description`
> loaded at startup for all skills. 2. **Instructions (< 5000 tokens recommended)**:
> the full `SKILL.md` body is loaded when the skill is activated. 3. Resources (as
> needed).
>
> Keep your main `SKILL.md` under 500 lines.

Invariant 1 enforces the *line* half because lines are trivially checkable. But
lines predict tokens only as well as line length allows, and across this repo's
**297** skill files line density varies **3.3×** — 38 to 127 bytes per line, median
57. So, by a `bytes/4` estimate:

| A 500-line file at… | ≈ tokens | vs. the 5,000 recommendation |
|---|---|---|
| the sparsest observed density | ~4,750 | within budget |
| the **median** density | ~7,118 | **42% over** |
| the densest observed density | ~15,870 | **3× over** |

**12 of 297 files already exceed ~5,000 tokens, and 11 of them pass invariant 1
comfortably** — `sota-mobile/rules/07-swift-language.md` is 254 lines, half the cap,
and ~6,737 tokens. A line cap cannot see that.

Two things keep this from being urgent. The 5,000-token figure applies to the
`SKILL.md` **body** (stage 2); for `rules/*.md`, which are stage-3 resources, the
spec gives no number, only *"keep individual reference files focused — agents load
these on demand, so smaller files mean less use of context."* And exactly **one**
file breaches the recommendation where it actually applies: `skills/sota/SKILL.md`,
the router, at **~10,211 tokens — 2× the budget** while sitting at exactly 500/500
lines.

There is no hard cap anywhere here. The spec's only hard limits are on frontmatter
(`name` ≤ 64, `description` ≤ 1024 — invariant 4 — `compatibility` ≤ 500), and of the
body it says outright: *"There are no format restrictions."* Nothing truncates a
skill at load. What a token overrun costs is context, and — see below — survival
across compaction.

**Not gated, deliberately.** A byte-or-token check passes all three
[CONVENTIONS-LEDGER](CONVENTIONS-LEDGER.md) filters, but it would fail on `main`
today, and the only fix is trimming a router that has no line slack left. That is a
design decision, not a mechanical one; it is logged in [ROADMAP.md](ROADMAP.md).

## The precondition all six defenses assume (measured in the field, 2026-08-05)

Every defense above fights for the model's *attention* over content that is
already in context. **None of them applies if the skill never loads at all**, and
that is not a hypothetical: a real ~25-turn session doing upstream-contribution
work invoked **zero** `sota-*` skills. The router body already contained the rules
that would have caught the worst error in that session. It was never read, so its
quality was irrelevant.

The mechanism is worth stating exactly, because it decides where effort pays off.
Per the [Agent Skills docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview),
only Level 1 loads at startup — *"until a Skill is triggered, only its name and
description occupy context"* — and the `description` is *"what Claude matches your
request against when determining whether to trigger the Skill."* So:

```
auto-loaded  →  frontmatter description only   (~100 tokens, always present)
inert        →  SKILL.md body + rules/*.md     (loads only when triggered)
```

The description is therefore not a hint. It is the **entire trigger classifier**,
and the other ~40 KB is dead weight until it fires. Three things went wrong:

- **The trigger verbs assumed you own the code.** "build, design, implement,
  refactor, harden, optimize, review, or audit an application, service, or
  codebase" does not describe reading a maintainer's review, judging someone
  else's patch, or preparing an upstream contribution. Fixed by adding
  non-owned-code triggers (v1.22.0).
- **Matching is per-prompt; the session drifted.** The individual prompts were
  "we have got response \<url\>", "what's the link on lychee?", "post it". The
  engineering nature emerged across ~20 turns and no single prompt named a code
  task. There is no "this conversation became a code task" mechanism, so the
  description now names the mid-session case explicitly and the hook makes it
  recoverable.
- **Structure beat repetition in the hook, and this is the transferable finding.**
  The re-injected hook carried three rules. Two were numbered imperatives; routing
  was a subordinate clause after a semicolon in a run-on sentence. Rules (1) and
  (2) were followed **every turn**; the routing clause was dropped **every turn**.
  Same text, same per-prompt repetition, opposite outcome. Defense 5 works — but
  it works on *grammatical form*, not on presence. A directive demoted to a tail
  clause is re-injected and still ignored.

So treat activation as **defense 0**: the cheapest thing in this document is
making sure the description matches the situation, because everything else is
conditional on it. It is also the least measurable — the repo's one adjacent
instrument, the `desc-routing` eval, reads **+0.00 (saturated)** and cannot
distinguish two descriptions. Changes here are reasoned, not measured, and are
labelled that way in the CHANGELOG.

## A platform behaviour the six defenses do not cover (recorded 2026-08-02)

Auto-compaction **truncates a re-attached skill**. Per the Claude Code skills
documentation: after the conversation is summarized, Claude Code *"re-attaches the
most recent invocation of each skill after the summary, **keeping the first 5,000
tokens of each**"*, and re-attached skills *"share a combined budget of 25,000
tokens"*, filled from the most recently invoked — so older skills can be dropped
entirely after a long session.

**That 5,000 is the same 5,000 as above, and the match is not a coincidence**: a
`SKILL.md` written to the spec's recommended instruction budget survives a
compaction intact, and one written past it is silently cut in half. The budget is
sized to the format.

This interacts with the library in a way none of the six defenses addresses, because
they all fight *attention* and this is *deletion*. A rough `bytes/4` estimate of what
exceeds the per-skill 5,000-token cut:

| File | ~tokens |
|---|---|
| `skills/sota/SKILL.md` (the router) | ~10,200 |
| `sota-devsecops/rules/03-dependencies.md` | ~7,300 |
| `sota-docs-workflow/rules/01-documentation-architecture.md` | ~7,200 |

So after a compaction, a re-attached router keeps roughly its first half. **This is
unverified in practice** — it is read off the documentation and a byte-count
heuristic, not observed in a session, and the ordering inside each file decides what
actually survives. It is recorded rather than acted on: the router is at **494/500**
lines (re-counted 2026-08-20 with `grep -c ''`; this sentence previously read
"500/500 with no slack", and the number has also read 491 — never trust it in prose,
see [ROADMAP.md](ROADMAP.md) item 4), and the honest next step is to
*watch* a compaction and see what is retained before reshaping anything around a
number we have not measured.

Note it does **not** change the 500-line cap's justification. Invariant 1 exists for
incremental loading, and the Agent Skills guidance it matches is explicit that long
reference material is cheap *until used*. This is about what happens to a skill
already loaded when the window is summarized.

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
