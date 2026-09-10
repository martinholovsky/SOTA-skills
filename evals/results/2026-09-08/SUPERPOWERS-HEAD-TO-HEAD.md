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

## Audited 2026-09-10: is the low score OUR bug? No — and here is the check

A number this shape, about someone else's project, on a public README, deserves an audit
rather than a defence. Five ways it could have been our defect, each checked:

| failure mode | finding |
|---|---|
| the arm got the wrong or unpinned content | the runner **refuses to run** unless the clone's `HEAD` matches the pinned SHA — a guard added 2026-08-16 after every earlier competitor number turned out to rest on an unverified clone |
| the arm got nothing, or a fragment | the bundle is **30,394 bytes** over four files. Not starved |
| we picked unrepresentative files | **see below — this is the decisive one** |
| the judge knew which arm it was scoring | the judge receives `(artifact, rubric)` only; no arm label, no library name |
| the interpretation was invented afterwards | the manifest's `_caveat` was written **2026-09-06, two days before the run**, and says exactly what the result turned out to be |

**On file selection — the repo has no domain content to omit.** At the pinned SHA,
`skills/` holds **14** skills: `brainstorming`, `dispatching-parallel-agents`,
`executing-plans`, `finishing-a-development-branch`, `receiving-code-review`,
`requesting-code-review`, `subagent-driven-development`, `systematic-debugging`,
`test-driven-development`, `using-git-worktrees`, `using-superpowers`,
`verification-before-completion`, `writing-plans`, `writing-skills`.

**Not one is about domain best practice** — no security, API design, rate limiting,
transport or logging skill exists in the repo. So there is no file we left out that could
have raised this score, and the four we did take (TDD, writing good tests, verification,
systematic debugging) are the four most likely to help on a "build X well" task. The
selection was, if anything, generous.

The contrast with the highest-scoring competitor makes the mechanism plain: **ECC's four
files include `the-security-guide.md` and three reviewer agents; Superpowers' four are a
TDD loop and a debugging method.** The rubric scores whether the built artifact carries
rate limiting, transport hardening, tests and structured logging. One library contains
that material; the other is not trying to.

**What this changes in how the number is stated.** "Scored below an unguided model" was
never supportable — −0.04 sits inside a measured ±0.03 noise floor at n=1. The supportable
claim is **"indistinguishable from no guidance on this rubric"**, and the README chart
states it that way: a single unguided band of 58–64% with Superpowers inside it, rather
than two baseline bars implying it lost to one of them.

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
