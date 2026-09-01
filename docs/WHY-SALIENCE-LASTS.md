# Why some measured lifts survive model progress and others evaporate

*Written 2026-09-01. Every number here is dated to the model it was measured on, and
links to the run that produced it.*

A guidance library is only worth what it adds to the model you actually have. That is an
uncomfortable standard, because the model keeps improving and the library does not
automatically become more valuable — it can quietly become worth nothing while every
sentence in it stays true.

This project has measured five things. Over four months of model progress they behaved
**differently**, and the difference turns out to be predictable. That prediction is the
most useful thing here, because it tells you which parts of a guidance library to invest
in and which to expect to expire.

## The observation

| Axis | Established | Re-measured on a later flagship | Verdict |
|---|---|---|---|
| **Defect avoidance** — the model must not *write* a known defect | +0.19 (0.81 → 1.00) `sonnet-4.6` | **+0.000** on `sonnet-5` and `gpt-5.1` | **expired** |
| **Completeness** — best practices embedded from a bare "build X" prompt | +0.39 (0.59 → 0.98) `sonnet-4.6` | **+0.38** (0.62 → 1.00) on `sonnet-5` | **held** |
| **Routing** — the right skills load for the task | +0.10 `sonnet-4.6` | **+0.13** on `sonnet-5` | **held** |
| **Freshness** — current 2026 facts | +0.53 `sonnet-4.6` | **+0.30** on `sonnet-5`, same set | **eroded — but see below** |
| **Prompt independence** — the same tasks under a prompt arguing *against* the rule | — | **+0.509** on `sonnet-4.6` | new, 2026-08-31 |

The first row is the one that should worry a library author. In four months, model progress
delivered exactly what the library had been delivering. The sharpest form of it:
**`sonnet-5` unguided scores 0.619 on the strict defect measure — precisely what
`sonnet-4.6` scored *with* the library** ([BUILD-SAFE](../evals/results/2026-08-21/BUILD-SAFE.md)).
The guidance did not get worse. The floor came up to meet it.

So why did completeness, measured on the same model pair over the same window, not move at
all?

## The mechanism: a knowledge gap closes, a salience gap does not

**A knowledge gap** is *the model does not know this*. Defect avoidance was a knowledge
gap. Earlier models wrote string-concatenated SQL because the pattern was in their training
distribution and nothing had pushed it out. Later models do not. Training closed it, and no
amount of good writing in a rules file can compete with that — nor should it want to.

**A salience gap** is *the model knows this perfectly well and does not do it here*. This
is the interesting one, because it is not a fact the model is missing. It is an allocation
of attention at the moment of writing.

The evidence is blunt: on the completeness tasks, **`sonnet-5` unguided still omits tests in
7 of 7 tasks**, transport in 5, and rate limiting in 5
([WHY-IT-WORKS](WHY-IT-WORKS.md)). No one thinks a frontier model in 2026 is unaware that
login endpoints need rate limiting. Ask it directly and it will tell you, at length. Ask it
to *build a login endpoint* and it builds a login endpoint. The task in front of it is the
task it does.

That is why the two axes came apart. Training data fixes what a model *knows*. It does not
fix what a model *attends to* when it is halfway through writing a handler and the
cross-cutting concern is not the thing being written.

## The experiment that makes this concrete

If the residual were a coverage gap, adding the missing rule would close it. We tried that.
**Adding the rule made it worse.** A short, salient reminder fixed it
([WHY-COMPLETENESS-RESIDUAL](WHY-COMPLETENESS-RESIDUAL.md)).

That result is only strange until you accept the mechanism. A longer context of
similar-looking guidance means more competition for the same attention, so the specific rule
that mattered lands with less weight than it did when the file was shorter. More coverage,
less application.

It has a direct design consequence, and this library is built on it:

- **Load lean.** Open the files that match the work, not everything. Note the honest limit
  here: when we finally *tested* whether irrelevant context costs applied rules — 400 extra
  lines of genuine rules prose — the answer was **−0.01**, a null
  ([COMPLETENESS-PADDING](../evals/results/2026-09-01/COMPLETENESS-PADDING.md)). Lean is
  cheaper and measures no worse; the stronger claim this project used to make was not
  supported and has been withdrawn.
- **Re-read last, not first.** The self-audit gate runs *after* the diff exists, because
  before that there is no diff to audit. On the ablation — base 0.60 → +rules 0.89 →
  +self-audit 0.93 → +principle 5 **0.99** — the rules carry the largest single step, and
  the last two close **0.10 of the 0.11 that remained**. (This project overstated that for
  a while, crediting the re-read with "the bulk" of the lift on the strength of a *two-arm*
  run that cannot apportion anything; corrected 2026-09-01.)
- **Keep the cross-cutting list short and repeat it late.** Operating principle 5 is four
  items long on purpose. It is not there to teach anything. It is there to be *salient* at
  the moment the model would otherwise drop them.

None of that is knowledge transfer. All of it is attention management.

## The sharpest evidence yet, and it arrived last

If the thesis is right, then the library's value should be **largest where attention is
under the most competition** — and the strongest competition is not a long context, it is
the user actively arguing the other way.

Measured 2026-08-31: the same six tasks at three prompt pressures.

| pressure | unguided | with library | lift |
|---|--:|--:|--:|
| supportive | 0.917 | 1.000 | +0.083 |
| neutral | 0.764 | 1.000 | +0.236 |
| **competing** | **0.491** | **1.000** | **+0.509** |

The lift **grows with the pressure against it**
([PROMPT-INDEPENDENCE](../evals/results/2026-08-31/PROMPT-INDEPENDENCE.md)). Told
*"internal MVP and we demo tomorrow — happy path only, skip the extras"*, the unguided arm
dropped **both** rate limiting **and** the password hash. It has not forgotten how password
hashing works. It was told the priority was speed, and it complied.

That is a salience failure in its purest form, and it is the one model progress has the
least reason to fix — because from the model's point of view, following the user's stated
priority is not an error.

## The third shape: when the *instrument* ages instead

Freshness looked like erosion: +0.53 → +0.30 on the same 32 questions. The tempting reading
is that the library's freshness value is decaying.

It is not, and we caught this by re-authoring rather than re-arguing. A fresh 10-question
set built from *recent* facts, chosen by a rule fixed before any model ran, reads **+0.67**
on the same model **an hour later** ([ITEM-21](../evals/results/2026-08-25/ITEM-21-REFRESHED-FRESHNESS.md)) —
higher than the original +0.53. The guidance did not improve between two runs. The questions
got newer.

So freshness is a **knowledge-renewable** gap: it closes as the training cutoff advances
into your fixed question set, and it reopens as the world moves on. Its lift decays *from
the date its questions were written*, not from the date the library was written — which is
why a freshness number here is always quoted with that date.

## What this predicts, and what would falsify it

**The prediction:** a lift that is knowledge-shaped expires with model progress; a lift that
is salience-shaped does not.

**What would falsify it:** a frontier model whose *unguided* arm scores at or near 1.00 on
completeness — that is, one that spontaneously writes the tests, the rate limiting, the
transport enforcement and the structured logging when asked only to "build a login
endpoint". If that model ships, the completeness lift is a knowledge lift after all and this
whole argument was wrong. We re-measure on each flagship for exactly this reason; the check
that killed defect avoidance is the same check that has so far spared completeness.

**What is not evidence:** the library getting longer, more skills, or better prose. None of
those bear on the question.

## Honest limits

- Five axes, a small number of models, and single-digit case counts on some sets. These are
  regression signals, not population estimates.
- The knowledge/salience split is a *model* that explains five observations. It is not
  itself measured, and a different mechanism could produce the same table.
- Completeness has held across one four-month window and one model transition. That is one
  data point about durability, not a law.
- The competing-prompt result is at ceiling on the guided side (1.000, sd 0.000 over 18
  runs), so the instrument can currently detect a regression but not resolve further
  improvement.

Everything above is reproducible: [evals/README.md](../evals/README.md) has the commands,
and [RESULTS.md](../evals/results/RESULTS.md) has every number including the ones that came
back +0.00.
