# Re-authoring the freshness set restores the lift — ROADMAP item 21 (2026-08-25)

**Predictions were [pre-registered](ITEM-21-PREREGISTRATION.md) and committed at `024abb9`,
before the first API call.** All of them held; neither falsifier triggered.

## Result

`evals/run-clean.py --cases evals/cases/freshness-2026.jsonl --model anthropic/claude-sonnet-5
--samples 3 --temp 0.7` — the same protocol as item 20, on the same model, the same day.

| set | without | with | lift |
|---|---|---|---|
| `freshness.jsonl` — 32 cases, authored ~Jul 2026 (**aged**) | 0.69 | 0.99 | **+0.30** |
| **`freshness-2026.jsonl` — 10 cases, authored 2026-08-25** | **0.33** `[0.30/0.40/0.33]` | **1.00** `[1.00×3]` | **+0.67** |
| *(historical: the same 32-case set on `claude-sonnet-4.6`, Jul 2026)* | 0.44 | 0.97 | +0.53 |

Raw: [`freshness-2026-sonnet5-3x.json`](freshness-2026-sonnet5-3x.json).

## What this settles

Item 20 found the freshness lift had fallen +0.53 → +0.30 and argued the cause was **the
instrument ageing, not the library weakening** — 8 of the 32 facts had moved inside the
newer model's training window, while the with-library arm *rose* (0.97 → 0.99).

**That explanation is now confirmed by construction.** Built from recent facts, the same
model on the same day reads **+0.67** — higher than the original +0.53. The guidance did
not get better between two runs an hour apart; the questions got newer.

So the three-shape frame from item 20 needs one refinement. Freshness is a **renewable**
knowledge gap, and the renewal is real: the lift a freshness set measures is a function of
**how recently the set was authored**, and decays from that date. It does not decay toward
zero as long as someone keeps authoring — which is precisely what a maintained library is
for. The number is a property of *set age*, not of guidance quality, and must be quoted
with its authoring date the way every other number here is quoted with its model.

**The with-library arm is a perfect 1.00 with zero variance across 3 samples.** That is an
independent corroboration of the authoring-time verification: the library demonstrably
carries all ten facts, having been checked against ten primary sources by hand first.

## The unguided arm is confidently wrong, not merely ignorant

This is the part the freshness claim has always rested on, and this set shows it cleanly.
Six of the ten misses are **fabrications with the right shape**:

| case | truth | unguided answer |
|---|---|---|
| g09 DMARC Aggregate Reporting | RFC **9990** | "RFC 9840" |
| g10 DMARC Failure Reporting | RFC **9991** | "RFC 9841" |
| g06 `assert_matches!` stabilized | Rust **1.96** | "1.87" |
| g08 Prometheus native histograms stable | **3.8**.0 | "3.5" |
| g05 PHP 8.2 security support ends | **31 Dec 2026** | "2026-12-08" |
| g07 iOS 26 SDK required since | **April 28, 2026** | "2026-04-24" |

None of these is an "I don't know". They are well-formed RFC numbers, plausible version
numbers and dates off by days — answers that would survive a skim in a design document
and be wrong in the specific way that matters.

## Limits — including a question-design weakness

- **10 cases: one case is 0.10.** This set is coarser than the 32-case one and cannot
  resolve small differences. It does **not** replace the original series, which is kept
  for continuity; the two are reported side by side.
- **Two of the ten questions partly telegraph each other.** `g03` ("which major version is
  the Go-native port") and `g04` ("which is the last release on the JavaScript codebase")
  are a matched pair about TypeScript 6.0/7.0, and a model that knows either can infer the
  other. Both were answered correctly unaided, so they inflate the *without* arm rather
  than the lift — the bias runs against the result being reported, not for it. Worth
  splitting in a future revision.
- **4 of 10 were answerable unaided** (`g01` RFC 9842, Sept 2025; `g02` PostgreSQL 19 beta;
  `g03`/`g04` TypeScript). RFC 9842 in particular predates the others by a year and is
  probably inside the cutoff. The set is not uniformly "post-cutoff", and is not claimed
  to be — it is uniformly *recent*, which is the rule that was fixed in advance.
- One model, one run, 3 samples, `temp 0.7`. Harness noise floor ≈±0.03 at n=1.

## A library defect found while authoring

Verification is a sweep whether or not you intend one. `sota-network-security` rules/02
pinned *"Cilium 1.19 (verified current line, 2026)"*; the GitHub API returns **v1.20.1,
published 2026-08-18**. Two things were wrong with that line and both are fixed:

1. **The pin itself violates the repo's own policy** — skills must never claim "the current
   release is X.Y" precisely because it rots. Fixed by *removing* the pin, not bumping it.
2. It said Cilium *"is the user's CNI"*, phrasing guidance as an assumption about the
   reader's setup, which the contribution conventions forbid.

**No freshness case was authored on this fact**, deliberately: a set must not measure
content written alongside it.
