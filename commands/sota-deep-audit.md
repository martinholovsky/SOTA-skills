---
description: The heavy audit — a hostile review of a whole repository by someone who will inherit it: the threat model reconstructed from the code and a control-presence matrix built against it, then code, history, decisions, results and forward plan, fanned out across independent agents, load-bearing claims re-measured this session or labelled unverified, every serious finding handed to a refuter that is not you. Expensive; run it at a milestone, an inheritance or a go/no-go, not routinely.
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

Five things, and only these five justify the cost. If none of them is what I need, say so and
point me back at the cheap command.

1. **Independence.** `/sota-audit` refutes its own findings from the context that produced
   them, which still holds the reasoning that produced them. Here every serious finding goes to
   an agent that did not find it, prompted to kill it.
2. **Scale.** `/sota-audit` also partitions a scope too large to hold at once, but it does so
   *within one context*, finishing each partition before the next — so the last partition is
   read by a context already full of the first. Here the partitions go to **separate agents**,
   each starting clean (`sota` router `rules/01` §1a).
3. **Decisions re-measured, not just reconstructed.** Where a past decision rests on a number,
   that number is produced again *this session*, including in environments that are slow or
   awkward to stand up.
4. **A forward look.** Whether the current plan is still the right one, given what the audit
   actually found.
5. **A reconstructed threat model.** `/sota-audit` checks the code against rules that already
   exist; it never asks what this system is *worth attacking for*. That reconstruction is a
   timeboxed pass of its own, run ahead of the lenses because its output decides what
   everything after it weights.

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

## Reconstruct the threat model first — its output prioritises everything below

This comes **before** the lenses, not inside lens 3, because a finding rated without trust
boundaries is rated in a vacuum (router AUDIT step 2). Timebox each phase and say which you
cut short (`sota-threat-modeling` rules/06 §1).

1. **Collect, and record what you were not given.** Repos, lockfiles, IaC, CI configs,
   container and cluster manifests, any existing architecture or threat-model docs,
   `.env.example`, OpenAPI/proto specs. **Surface you could not audit goes in the report as
   un-auditable** — never silently dropped.
2. **Extract the system model from the code, not from the docs** — entry points by mechanism,
   stores and assets, the actor and privilege table, and the trust boundaries the system
   *actually* has rather than the ones it claims (`sota-threat-modeling` rules/02 §5, §7, §8).
   **Output the reconstructed DFD.** It is deliverable one even if nothing else is found: most
   teams have never seen their real attack surface drawn.
3. **Write down the implied assumptions**, from auth middleware, IaC structure, old ADRs,
   comments. *Services trust the gateway's headers. That bucket is private. Only the worker
   reaches the queue.* Each one becomes a test target.
4. **Run the component catalogs** against everything step 2 found — web frontend, API, data
   tier, queue, upload pipeline, CI/CD, mobile, cloud and IAM (`sota-threat-modeling`
   rules/03). An LLM or agent surface is not an exception to this: it has its own catalog
   (`sota-threat-modeling` rules/03 §8).
5. **Test every assumption from step 3 against the code or config that makes it true.** No
   evidence is not *probably fine* — it is a broken assumption, and these are usually the
   Criticals.
6. **Build the control-presence matrix**, one row per component × catalog item, each marked
   **Present · Partial · Absent · N/A · Unverifiable** and carrying the evidence its state
   demands: `file:line` for Present, *both* sides for Partial, **the searches you ran** for
   Absent, and the artifact that would settle it for Unverifiable
   (`sota-threat-modeling` rules/06 §2).

Three things decide whether that matrix is worth anything:

- **Partial is the most important state.** One authorization-checked endpoint proves the team
  knows the pattern; the seventeen unchecked ones are the finding — and they tell you the
  remediation is *adoption*, not invention.
- **Check the negative space.** Middleware exclusion lists, `TODO: auth`, skip-auth decorators,
  `count = 0` and commented-out IaC blocks, disabled tests with *security* in the name,
  allowlist files. **A disabled control is a stronger finding than one never built** — someone
  decided.
- **Sample honestly and state the rule.** On a repetitive surface, sample a declared fraction
  *plus* every path touching a top asset, and put that rule in the report. A matrix built from
  an unstated sample is a claim about the sample wearing the whole system's clothes.

**Then falsify the Present rows** — this is the router's silent-control pass, and the matrix is
what tells it where to look. A control is marked Present because you *found* it, which is not
the same as it doing anything. Ask of each: if this were silently a no-op, would anything
observable differ? No log, no metric, no failing test means it is not a control
(`sota-code-security` rules/10 §1). Then ask whether it covers its whole population or only the
paths you happened to sample (`sota-code-security` rules/14 §6).

Rate what falls out of this in **deployment context** rather than in the abstract
(`sota-threat-modeling` rules/04 §3), and hand the reconstructed model back as the team's new
baseline — `sota-threat-modeling` rules/06 §1 calls that the audit's lasting value, and for a
team that has never had one drawn it usually is.

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
3. **Security posture.** Driven by the matrix above: every **Absent** and **Partial** row
   becomes a threat sentence, rated in deployment context, ranked
   (`sota-threat-modeling` rules/06 §3). Then the code-level surface the matrix does not
   reach — input handling, injection and abuse paths, resource exhaustion, secrets handling,
   dependency and supply chain, fail-open versus fail-closed. Scope to what is authorised and
   defensive. Each routed skill's Audit checklist is the completeness gate, walked item by
   item, not skimmed.
4. **Strategy and forward plan.** Is the current plan sound given what you found? Which levers
   are exhausted or dead ends, and is the plan still chasing them? Which promising directions
   were never explored? Where do the stated priorities diverge from where the real risk and
   value sit?

## Orchestration

**If this harness offers multi-agent orchestration, use it**; if it does not, run the lenses
sequentially and start a **fresh context for the refutation pass** — say which of the two you
did. Independence is the thing being bought here, and a context that already holds the finding
cannot supply it.

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
verdict · **the reconstructed DFD and the control-presence matrix**, with the sampling rule
stated · the decision ledger with each verdict and its re-checked evidence · findings by lens
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
