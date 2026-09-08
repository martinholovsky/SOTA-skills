# The Superpowers head-to-head — ROADMAP item 40

**Date:** 2026-09-08 · **Build model:** `anthropic/claude-sonnet-4.6` · **Judge:**
`anthropic/claude-opus-4.8` (blind) · **Cases:** 7 completeness build tasks ·
**Samples:** 1 per arm per case, temp 0.0 · **Competitor pinned at:**
`obra/superpowers` @ `b36e0829c6d0140e93cfef2ca599b1b07d4a7797` (MIT), clone verified
at that exact SHA by the runner before any call · **Elapsed:** 2814 s

Two external assessments called Superpowers *"a complete agentic software-development
methodology, not merely a best-practices library"*, and rested a *"not yet a complete
methodology"* verdict about this library on that comparison. We had a head-to-head
instrument pointed at three other repos and never at this one. This closes that.

## Result

| case | without | SOTA | Superpowers |
|---|---:|---:|---:|
| `c1_ticket_api` | 0.67 | **1.00** | 0.67 |
| `c2_upload` | 0.64 | **0.91** | 0.45 |
| `c3_emailjob` | 0.82 | **1.00** | 0.64 |
| `c4_login` | 0.50 | **1.00** | 0.60 |
| `c5_search` | 0.60 | **1.00** | 0.50 |
| `c6_webhook` | 0.60 | **1.00** | 0.70 |
| `c7_pwreset` | 0.64 | **1.00** | 0.64 |
| **mean** | **0.637** | **0.987** | **0.599** |

Deltas: Superpowers **−0.39 vs SOTA**, **−0.04 vs unguided**.

## Read this before quoting any of it

**The manifest's caveat is the point, not a disclaimer.** Superpowers is *process and
methodology* guidance — a TDD loop, systematic debugging, verification before completion.
These cases score whether a **built artifact embeds domain best practices**: is the endpoint
authenticated, is the query parameterised, is there a rate limit, are there tests. Those are
different questions. **A low score here is evidence about fit to THIS measure, not about
that project**, and publishing it otherwise would be exactly the unfair comparison this
repo's own conventions forbid.

**The honest headline is the one that is least flattering to us:** on this measure,
Superpowers is **indistinguishable from no guidance at all** (−0.04 at n=1, temp 0, against
a noise floor this repo has measured at **±0.03**). That is not a finding about Superpowers.
It is a finding about the instrument: *our completeness cases cannot see what Superpowers
does.* An instrument that returns "no different from nothing" for a well-regarded project is
reporting its own blind spot as much as anything else.

**What it does and does not settle.** It settles that the two libraries are not substitutes
and are not measured by the same yardstick. It does **not** adjudicate the assessments'
actual claim — that a methodology (how the agent works) is a more complete offering than a
best-practices corpus (what the agent should know). Nothing here measures process adherence,
which is what Superpowers is for; measuring that fairly would need a different instrument
that we do not have, and building one to score a competitor is not a neutral act.

## Limits, stated plainly

- **n=1 per arm per case, temp 0.** Not deterministic: this repo measured a **±0.03** noise
  floor at n=1, so the −0.04 gap between Superpowers and unguided is at that floor and
  should be read as *no measurable difference*, not as a deficit.
- **Content-only.** Both arms get a bundle of Markdown pasted into the prompt; neither is
  run as an installed, routed, tool-using system. As-deployed comparison was rejected on
  2026-08-16 as measuring corpus size and a saturated retrieval path (ROADMAP 3).
- **Four files.** Superpowers' bundle is the four files its manifest entry names, chosen
  2026-09-06 as the closest-fitting subset. A different four might score differently.
- **The SOTA arm is at ceiling** (0.987, six of seven at 1.00), so this run can detect a
  competitor scoring lower and cannot resolve anything above us.
