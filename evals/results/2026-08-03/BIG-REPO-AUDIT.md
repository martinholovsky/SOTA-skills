# Agentic large-repo audit — attempted, and the instrument is not viable

**Date:** 2026-08-03 · **Status:** instrument failure, not a null · **Not on the scoreboard.**

The roadmap kept one audit design open after seven +0.00 results: *"the agentic
large-repo audit — the only design that could move AUDIT off +0.00"*, on the theory
that prior instruments saturated because the code and the question both fit one
prompt. Give the model a repo too big to hold at once, and it must **choose where to
look**. This is that attempt. It does not work, for a reason that generalises.

## What was built

Two fixture generations, each a synthetic Python service repo with six planted
defects drawn from classes this library owns — `assert`-as-authorization, a swallowed
enforcement exception, a cache key narrower than the behaviour it gates, a validator
vacuous on empty scope, a handler for an event nothing emits, and a missing tenant
filter.

| | v1 | v2 |
|---|---|---|
| Files / size | 366 / ~96k tokens | 360 / ~93k tokens |
| Filler | one identical template | **340 distinct normalised shapes** |
| Defect files | 6 uniquely *named* modules | ordinary `handler_NN.py` slots |
| Bare-arm recall | **6/6, 6/6, 6/6** | **6/6, 5/6** |

## Why it fails — and why v2 did not fix it

**v1** leaked through file naming. All three agents said so outright: *"All findings
are in the 6 files that are not that template"*, *"the six seeded-looking modules"*.

**v2** removed that tell — varied filler, defects hidden in ordinary slots — and the
agents simply moved down a level:

> "I parsed every file with `ast`, normalized method bodies, and grouped them — all
> 360 `__init__`, all 360 `totals` and all 720+ accessor methods are byte-identical
> after digit normalization, so the only substantive code in the repo is **six methods
> that deviate from the template**."

**That is the structural result: in a synthetic corpus, a planted defect is by
construction a deviation from generated filler, and deviation is detectable
mechanically — without any security reasoning at all.** Scaling the repo does not
help; it makes the anomaly *cheaper* to find, because more filler means a stronger
baseline to diff against. The navigation burden the design intended to create never
materialised.

## The pre-registered prediction was wrong

Committed before any run: bare **0.30–0.50**, library **0.50–0.70**, lift **+0.10 to
+0.25**. Measured bare: **0.92–1.00**. Wrong by roughly 2×, in the direction the
repo's own prior evidence favoured and the prediction discounted.

## Why the library arm was never run

The bare arm is at ceiling with no library, so there is no headroom for a lift, and
the instrument is demonstrably confounded. A number produced here could not be
interpreted, and publishing one would be worse than having none. Stopping is the
result.

## What would actually be needed

A **real repository with real defects** — a known-vulnerable open-source project at a
known commit, where the defect is ordinary code written by someone who believed it was
correct, not a generated anomaly. Only then is finding it a test of security reasoning
rather than of diffing. That is a materially larger undertaking (licensing, ground
truth, reproducibility) and is recorded rather than attempted.

**The roadmap's claim needs qualifying:** an agentic large-repo audit may still be the
only design that could move AUDIT off +0.00, but a **synthetic** one cannot — and that
is now demonstrated twice rather than assumed.
