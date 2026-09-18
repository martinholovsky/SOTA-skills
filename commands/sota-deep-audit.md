---
description: The heavy audit — a hostile review of a whole repository by someone who will inherit it: code, history, decisions, results and forward plan, fanned out across independent agents, every load-bearing claim re-measured this session, every serious finding handed to a refuter that is not you. Expensive; run it at a milestone, an inheritance or a go/no-go, not routinely.
---

A hostile review of this repository by someone who will inherit it and distrusts every prior
claim. Discover the domain, stack and conventions yourself — read the agent file, README, docs
and config first. Assume nothing about what this project does.

**This is expensive.** It fans work out across many agents, re-runs suites, and can re-measure
benchmarks in heavyweight environments. That is the point of it, and it is the reason not to
reach for it by default: [`/sota-audit`](sota-audit.md) answers *were the rules that own this
surface applied?* in one context, cheaply enough to run repeatedly. **Tell me the plan and the
split before you fan anything out**, so I can stop it if the scope is wrong.

## What this adds that `/sota-audit` structurally cannot

Four things, and only these four justify the cost. If none of them is what I need, say so and
point me back at the cheap command.

1. **Independence.** `/sota-audit` refutes its own findings from the context that produced
   them, which still holds the reasoning that produced them. Here every serious finding goes to
   an agent that did not find it, prompted to kill it.
2. **Scale.** A repository too large to hold at once is partitioned across agents rather than
   skimmed by one (`sota` router `rules/01` §1a).
3. **Decisions re-measured, not just reconstructed.** Where a past decision rests on a number,
   that number is produced again *this session*, including in environments that are slow or
   awkward to stand up.
4. **A forward look.** Whether the current plan is still the right one, given what the audit
   actually found.

## Ground rules

**Validate; never trust the prose.** Docs, comments, commit messages, roadmaps and any
memory or notes describe *intent* or *the past*. Every load-bearing claim is verified against
the code, the data and a real run this session, quoted as evidence — test counts, measured
numbers, command output, `file:line`. A claim you cannot back with evidence you produced is
labelled **UNVERIFIED**, with the thing that would confirm it named.

**Run what matters.** Execute the test suite and the cheap local checks. Where a decision
hinges on a measured result — a benchmark, a recall or false-positive rate, a latency, any
"this is faster/safer" — re-measure it, including in heavyweight or special environments
(containers, GPUs, integration harnesses) when that is the only way to confirm it. Respect
this project's documented environment constraints and teardown rules: destroy what you rent,
commit no secrets. If you genuinely cannot run something, say so and mark everything that
depends on it UNVERIFIED.

**Watch a check fail before believing it passed.** A suite that matched zero files exits 0 and
prints `ok`; a gate whose environment cannot reach the defect is green and proves nothing. Say
what depth each check actually reached (`sota-devsecops` rules/09 §2a, §2b).

**Report faithfully.** Failures, skips and uncertainty are stated plainly with the evidence.
No confident summary papering over a gap.

## Route before you fan out

Recon first — languages, entry points, data stores, CI, IaC, LLM surfaces, anything an agent
loads as instructions — then map what you found onto the domain skills with the `sota` router's
routing table. Those skills' AUDIT sections and per-rules-file Audit checklists are the **what**
of lenses 2 and 3; the lenses are the **how**. Load lean: only the rules files with real surface
area here.

**Record which domains you skipped and why.** A domain with no matching surface is a legitimate
skip. A domain nobody opened is a hole in the audit and is reported as one.

Run the router's silent-control pass over every control the domain passes confirm exists — a
control that is present and inert is invisible to all four lenses below
(`sota-code-security` rules/10 §1, and `rules/14` §6 for the one that guards part of its
population).

## The four lenses — cover all, weight by what this project actually is

1. **Correctness, decisions and results.** Reconstruct the load-bearing decisions from the
   commit history, ADRs and any results ledger. For each: what was claimed, what evidence
   supported it, and does that evidence still hold when you check it *now*? Classify
   **JUSTIFIED · STALE · UNJUSTIFIED · UNVERIFIABLE**, and flag every result that does not
   reproduce. Full procedure — `sota` router `rules/03` §3. Then ask where else this
   project's knowledge lives: a fact about the repository that exists only in an agent's
   memory store or a chat log is invisible to review and absent from a fresh clone
   (`sota` router `rules/01` §4a).
2. **Code quality and architecture.** Correctness bugs, dead and duplicated code, weak or
   missing coverage, leaky abstractions, and violations of the project's *own* stated
   invariants and conventions. Distinguish a real defect from a style preference. Driven by
   the routed language and domain skills.
3. **Security posture.** The system's attack surface and failure modes: input handling,
   injection and abuse paths, resource exhaustion, secrets handling, dependency and supply
   chain, fail-open versus fail-closed. Scope to what is authorised and defensive. Each
   routed skill's Audit checklist is the completeness gate — walked item by item, not skimmed.
4. **Strategy and forward plan.** Is the current plan sound given what you found? Which levers
   are exhausted or dead ends, and is the plan still chasing them? Which promising directions
   were never explored? Where do the stated priorities diverge from where the real risk and
   value sit?

## Orchestration

**If this harness offers multi-agent orchestration, use it**; if it does not, run the lenses
sequentially in fresh contexts and say which you did, because the independence below is the
thing being bought and a single context cannot provide it.

Fan independent auditors across the four lenses, sub-splitting a large lens by subsystem. Then
run an **adversarial verification pass**: every non-trivial finding, and every "this decision
was unjustified" verdict, goes to a separate agent prompted to refute it, working from the code
at the pinned commit rather than from the finder's write-up, defaulting to REFUTED where the
evidence is ambiguous. Bound what the refuter receives and make its verdict a number
(`sota` router `rules/03` §4, §4a). Only survivors ship; the rest are dropped or downgraded
**with the refutation recorded**, and the refuted pattern is swept elsewhere either way — that
sweep is routinely where the strongest finding comes from.

Absence claims get a refuter too, and carry the heavier burden: a negative needs a positive
control in the same invocation, or a denominator where no control is available
(`sota-shell-scripting` rules/06 §2, `sota-code-security` rules/11 §2.2).

Scale depth to what you find — loop on the lenses turning up real issues until new findings dry
up. **Log what you deliberately did not cover.** No silent truncation.

## Deliverables

Report in the session by default. **Write files only if I ask for them** — most repositories
this runs in are not yours to leave artifacts in. When I do ask, two:

**A. A dated audit report** at this project's docs location. Executive summary and health
verdict · the decision ledger with each verdict and its re-checked evidence · findings by lens
in the canonical format `file:line | rule | severity | effort | fix`, severity resolved on
`sota` router `rules/03` §1, noting which domain skill each came from · domain coverage, including
what was skipped and why · reproduction status, including what stayed UNVERIFIED · unexplored
directions · the roadmap assessment.

**B. A plan patch** — specific, scoped edits to this project's roadmap or next-steps docs so
they reflect what the audit concluded: re-prioritised, dead ends removed, new directions slotted
in with their justification. **Show the before and after and let me approve.** Never rewrite a
plan silently.

## Constraints

- **Tell me the plan and the split first**, then proceed. A fan-out I did not see coming is a
  cost I did not agree to.
- **Every claim in the final report is one you produced evidence for this session**, or it is
  labelled UNVERIFIED with the confirming step named.
- **Never report a suite as passing that you did not watch pass**, and name the depth each
  check reached.
- **A rule that let this codebase down is worth one line at the end**, pointing me at
  `/sota-report` — the library learns nothing from this pass otherwise.

$ARGUMENTS
