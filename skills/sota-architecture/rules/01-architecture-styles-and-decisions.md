# 01 — Architecture Styles & Decision-Making

Rules for choosing an architecture style, recording decisions, and keeping the
architecture evolvable. Apply before writing the first service; re-apply at every
major boundary change.

## 1. Default to a modular monolith

**Rule:** Start every new system as a modular monolith: one deployable, internal
modules with explicit boundaries, separate schemas-per-module inside one database.
Extract services only when a *measured* force demands it.

**Rationale:** Network boundaries are the most expensive boundaries you can buy.
They convert function calls into failure modes (latency, partial failure, retries,
versioning). A modular monolith gives you boundary discipline at refactor cost,
not distributed-systems cost.

**Forces that justify extraction (need at least one, measured):**
- Independent scaling: one module needs 50x the replicas of the rest.
- Independent deployment cadence blocked by org structure (multiple teams stepping on one release train).
- Divergent runtime needs (GPU inference vs CRUD; different language/runtime).
- Hard fault isolation requirements (a crash in module A must not take down module B).
- Regulatory isolation (data residency, PCI scope reduction).

**Never extract because:** "microservices are best practice", résumé pressure,
"we might need to scale later", or to fix a tangled codebase (you'll get a
tangled distributed system — see rules/07, distributed monolith).

```text
GOOD: one repo, one deploy
  app/
    billing/      (public API: billing/api.*, everything else internal)
    catalog/
    shipping/
  Module imports only other modules' api/ surface. CI fails on deep imports.

BAD: 14 services, one team of 5, shared DB, lockstep deploys.
```

## 2. Enforce module boundaries mechanically

**Rule:** Boundaries that aren't enforced by tooling don't exist. Use import
linting / architecture tests (dependency-cruiser, ArchUnit, deptrac, Nx tags,
Go internal/ packages, or equivalent) in CI. A human code-review rule is not
enforcement.

**Rule:** Each module exposes exactly one public surface (an `api`/facade
package and/or published events). Cross-module calls go through that surface.
Cross-module data access goes through that surface — never through the other
module's tables.

## 3. Choose style by problem shape, not fashion

| Style | Wins when | Loses when |
|---|---|---|
| Modular monolith | Small/medium team, evolving domain, unknown load profile | Genuinely independent scaling/deploy needs across teams |
| Microservices | Many teams, independent deploy cadence, per-service scaling, mature platform (CI/CD, observability, on-call) | Team < ~3 squads, no platform engineering, chatty domain |
| Serverless (FaaS) | Spiky/bursty load, event glue, low ops budget, embarrassingly stateless handlers | Long-lived connections, latency-critical p99 (cold starts), heavy local state, cost at sustained high throughput |
| Event-driven backbone | Many consumers per fact, audit/replay needs, temporal decoupling | Request/response semantics forced through events (see rules/03) |

**Rule:** Serverless is an operational model, not an architecture. You still owe
module boundaries, idempotency, and observability. A pile of 200 lambdas sharing
a database is a distributed monolith with cold starts.

**Rule:** Never mix request/response and event-driven semantics blindly. Decide
per interaction: does the caller need an answer now (sync), or is it publishing
a fact (async)? Commands that need answers are sync or async-with-correlation;
facts are events.

## 4. Record every significant decision as an ADR

**Rule:** Any decision that is expensive to reverse (datastore, message broker,
service boundary, auth model, multi-tenancy model, sync vs async for a flow)
gets an Architecture Decision Record before implementation. Store ADRs in the
repo (`docs/adr/NNNN-title.md`), immutable once accepted; supersede, never edit
history.

**Minimum ADR format:**

```text
# NNNN: Use outbox pattern for order events
Status: Accepted (2026-03-02)  Supersedes: 0007
Context: Orders must emit events; dual-write to DB + broker loses events on crash.
Decision: Write events to outbox table in the same TX; relay publishes async.
Consequences: + atomicity, + replay; - eventual consistency (~1s lag), - relay to operate.
Alternatives considered: CDC (Debezium) — rejected: no ops capacity for Kafka Connect.
```

**Rationale:** ADRs are the only durable defense against re-litigating decisions
and against cargo-culting old constraints after they expire. "Why is it like
this?" must have a greppable answer.

**Rule:** An ADR without a *Consequences* section listing at least one downside
is marketing, not a decision record. Reject it in review.

**Directory discipline.** Sequential kebab-case filenames
(`0012-use-outbox-for-order-events.md`) plus an `index.md` holding one row per
ADR — number, title, status, date. The index is what makes the practice
auditable at a glance: a status column that is all `proposed` is a stalled
process, and a superseded chain is legible without opening a file. Commit the
ADR **in the PR that implements the decision** where one exists, so rationale
and code land together; a pre-implementation decision lands on its own.

## 4a. A control's cost profile must be checked against decisions already in force

A new control that consumes a **scarce resource on every use** — a hardware touch, a human
approval, an interactive prompt, a rate-limited or paid API call — can silently reintroduce
the exact friction an earlier decision removed. Both artifacts are locally correct; the
contradiction lives in the gap between them, and no test sees it.

Field-reported: a repository decided, with the reasoning written into `CONTRIBUTING`, to
stop signing every commit because the key sat on a touch-required token and the tap per
commit blocked automated work. About an hour later, in the same session, a gate ledger was
built whose `anchor` command signed its chain head with that same key — and anchoring was
recommended after every push. Every gate passed, every test passed, and the user found it.

**At the point of adding the control, write one line: *this costs X, Y times per Z*. Then
grep the repo's own decision records (§4) for X.** If a decision already rejected X at that
frequency, either the new control is wrong or the old decision needs revisiting — the two
cannot both stand unexamined. The tell that you missed it is a user asking *"why am I being
asked for this again?"*, which is late and expensive.

This is a **coherence** failure, not a code defect, so it is invisible per-artifact and to
per-file review. It is worst in agent-authored work: an agent can hold both decisions in
one context and still miss the interaction, because attention is on the artifact being
built, not on the policy it lands inside.

## 5. Practice evolutionary architecture with fitness functions

**Rule:** Encode architectural qualities as automated, continuously-run checks
(fitness functions). If a quality matters, test it; if you can't test it, you
can't claim it.

**Examples of fitness functions (run in CI or scheduled):**
- Dependency direction: "no module imports `billing/internal`" — architecture test.
- Coupling budget: cyclic dependencies between modules = build failure.
- Latency: p99 of checkout API < 300 ms under k6 load profile — perf gate on main.
- Resilience: weekly chaos run kills one replica of each service; SLOs must hold (see rules/04).
- Cost: per-tenant infra cost stays under $X — scheduled report with alert.
- Schema safety: migration linter forbids destructive DDL without expand/contract.

**Rule:** When two qualities conflict (e.g., consistency vs availability), the
ADR picks the winner per context; the fitness function enforces the chosen
trade-off, not both.

## 6. Plan for reversibility; classify decisions by exit cost

**Rule:** Classify every decision: **Type 1** (hard to reverse: datastore,
broker, cloud provider, tenancy model, public API contract) vs **Type 2**
(cheap to reverse: library, internal interface, queue topology detail).
Spend design effort proportionally. Type 2 decisions get minutes and a code
comment; Type 1 decisions get an ADR, a spike, and an exit strategy.

**Rule:** For every Type 1 dependency, write down the exit strategy in the ADR
("we wrap the broker behind `EventBus` port; migration = reimplement adapter +
dual-publish for N days"). Don't build a full abstraction layer preemptively —
a thin port is enough (see rules/02 on ports).

## 7. Conway's law: design team and system boundaries together

**Rule:** Service boundaries that cross team boundaries will erode. Align one
service (or module) to one owning team; shared ownership means no ownership.
If the org chart and the architecture disagree, change one of them deliberately
(inverse Conway maneuver) — don't let the disagreement fester.

**Rule:** Each module/service has a single on-call/owning team recorded in a
machine-readable catalog (`catalog-info.yaml`, CODEOWNERS, or equivalent).
"Orphaned service" is a Critical audit finding.

## 8. Extraction playbook (monolith → service)

**Rule:** Extract via strangler fig, never big-bang rewrite:
1. Harden the module boundary in-process (own schema, api-only access, events).
2. Add an anti-corruption layer at the seam if models differ.
3. Route a slice of traffic to the new service behind a flag; compare outputs (shadow/dark launch).
4. Migrate data with expand/contract: dual-write or CDC, backfill, verify, cut over, contract.
5. Delete the old path. Extraction isn't done until the old code is deleted.

**Rule:** Never extract two things at once (e.g., new service AND new datastore
AND new language). One variable per migration.

## 9. Buy/adopt vs build

**Rule:** Build only what differentiates the business. Auth, payments, search,
feature flags, observability, workflow engines: adopt proven solutions and wrap
them behind a thin port. Building commodity infrastructure is a Type 1 decision
disguised as a weekend project.

**Rule:** Adopted dependencies still get an ADR (lock-in is a consequence) and
a fitness function (e.g., "all calls to vendor X go through adapter Y" —
architecture test).

## 10. Edge composition: gateways and BFFs

**Rule:** Clients never call internal services directly. Put an API gateway at
the edge for cross-cutting concerns (authn, rate limiting, TLS, routing) and —
when client needs diverge (mobile vs web vs partner API) — a Backend-for-
Frontend per client class that composes internal calls into client-shaped
responses.

**Rule:** Keep business logic out of the gateway. A gateway that transforms
payloads, enforces domain rules, or orchestrates workflows is an unowned god
service (rules/07 §3) written in YAML. Gateways route and protect; BFFs compose;
services decide.

**Rule:** Each BFF is owned by the client team it serves. A shared BFF for all
clients recreates the coupling BFFs exist to remove.

## 11. Diagrams and design docs as code

**Rule:** Maintain a current C4-style picture: one system-context diagram and
one container diagram minimum, stored in the repo as text (Mermaid, Structurizr
DSL, PlantUML) so diffs are reviewable and rot is visible in PRs. A diagram in a
wiki dies in a quarter; a diagram in the repo dies in review.

**Rule:** Significant designs get a short RFC/design doc *before* implementation
(problem, constraints, options, recommendation), circulated to affected teams
with a comment deadline. The ADR (§4) records the outcome; the RFC records the
debate. Skip the RFC for Type 2 decisions — process must be proportional too.

## 12. Sacrificial architecture and rewrite discipline

**Rule:** Accept that successful systems outgrow their architecture (~10x scale
changes the right design). Write code expecting parts to be replaced: boundaries
and contracts are the durable assets, implementations are sacrificial. Optimize
boundary quality over implementation polish.

**Rule:** Never green-light a full rewrite while the old system keeps taking
features ("second-system" trap). A rewrite must be: scoped to one bounded
context at a time, strangler-style (§8), with a feature freeze on the replaced
slice and a kill date for the old path. "Big rewrite, both evolve in parallel"
fails at a rate that rounds to always.

## 13. Architecture review cadence

**Rule:** Review the architecture on triggers, not just calendars: 10x traffic
growth, new compliance regime, team doubling, p99 SLO erosion two quarters
running, or a third incident with the same structural cause. Each review:
re-validate prior ADRs' assumptions (load numbers, team size, vendor constraints)
and explicitly supersede the ones whose context expired.

**Rule:** Track architecture debt in the same backlog as features, each item
tied to a measurable symptom (incident class, lead-time drag, cost line).
"Refactor someday" items without symptoms get deleted, not hoarded.

## Audit checklist

- [ ] **Every control that spends a scarce resource per use states its cost profile**
      (*what, how often*), and that frequency was checked against the ADRs and contributor
      docs (§4). A control whose per-use cost contradicts a decision already in force is a
      finding even though it works.

- Is there a written rationale (ADR) for the current architecture style, with consequences and alternatives?
- Could this system be a modular monolith? If it's microservices, can the team name the measured force that justified each extraction?
- Are module/service boundaries enforced by CI tooling (import rules, architecture tests), not just convention?
- Does any module reach into another module's internals or tables directly?
- Do services deploy independently in practice (check release history), or do they ship in lockstep?
- Is every Type 1 decision (datastore, broker, tenancy, public contracts) covered by an ADR with an exit strategy?
- Are ADRs immutable and superseded rather than edited? Is the most recent ADR less than ~3 months old (i.e., is the practice alive)?
- Are architectural qualities (latency, coupling, resilience, cost) encoded as automated fitness functions that run in CI or on a schedule?
- Does every service/module have exactly one owning team, recorded machine-readably?
- Were recent extractions done strangler-style with a deleted old path, or do zombie code paths remain?
- Is any commodity capability (auth, flags, queues, search) hand-built without an ADR justifying it?
- Do sync vs async interaction choices match the semantics (answers vs facts), or are request/response flows tunneled through events?
- Do clients reach internal services directly, or through a gateway/BFF? Does the gateway contain business logic?
- Are context/container diagrams stored as text in the repo and current (spot-check three services against the diagram)?
- Is any rewrite running big-bang style with parallel feature development on old and new?
- Do superseded ADRs exist (evidence assumptions get re-validated), or has nothing been revisited since launch?
