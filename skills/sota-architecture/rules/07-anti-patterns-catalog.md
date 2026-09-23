# 07 — Anti-Patterns Catalog

Named failure modes with detection signals and remediation. In AUDIT mode, use
the detection signals as grep/inspection targets; in BUILD mode, treat each as a
"never do this" with the listed alternative.

## 1. Distributed monolith

**What:** Microservices' costs (network, ops, versioning) with a monolith's
coupling (lockstep deploys, shared data, synchronous chains).

**Detection signals:**
- Release notes/pipelines deploy multiple services together "because they have to".
- Service A's PR requires a matching PR in service B to not break (no contract versioning, rules/03 §8).
- Synchronous call chains ≥ 3 services deep on the request path; availability = product of every link.
- Shared libraries containing *domain* logic that force coordinated upgrades.

**Fix:** Either merge them back (modular monolith — usually right) or make them
actually independent: versioned contracts + consumer tests, async where the
semantics allow, kill deep sync chains via composition at the edge (BFF/gateway)
or data replication into the caller.

**Severity default:** Critical (it's all of the cost, none of the benefit).

## 2. Shared database integration

**What:** Two or more services/modules read or write the same tables.

**Why it's fatal:** The schema becomes an unversionable public API; no one can
migrate without breaking unknown others; invariants are enforced nowhere;
ownership is fiction.

**Detection signals:** multiple services with credentials to the same schema;
cross-service foreign keys; "read-only access to their DB for reporting";
views shared as integration interfaces.

**Fix:** One writer-owner per table/schema. Other consumers integrate via the
owner's API, published events + their own projection, or CDC into an analytics
store (for reporting). Strangle existing shared access: inventory consumers,
give each a sanctioned path, then revoke credentials.

**Severity default:** Critical for shared writes; High for shared reads.

## 3. God service / god module / god aggregate

**What:** One component that accretes every new feature (often named `core`,
`common`, `platform`, `UserService`, or the original monolith in a "micro-
services" system).

**Detection signals:** disproportionate size/churn (one service receives 60% of
all commits); every cross-team change touches it; its test suite dominates CI
time; every other service depends on it synchronously; aggregates loading
hundreds of rows to change one field.

**Fix:** Split along bounded contexts (rules/02 §1) using strangler extraction
(rules/01 §8). For god aggregates: re-interrogate true invariants and split into
smaller aggregates linked by events (rules/02 §3).

**Severity default:** High.

## 4. Premature microservices

**What:** Decomposing into services before the domain is understood or the team
can operate them. Wrong boundaries in a distributed system are 10x costlier to
move than module boundaries.

**Detection signals:** more services than engineers; "we'll need it at scale"
with no load data; nano-services (an entity-per-service, services that only
CRUD one table); local dev requires running 12 containers; no platform
engineering yet plenty of services.

**Fix:** Consolidate into a modular monolith with enforced boundaries
(rules/01 §1–2); keep events/contracts at module seams so future extraction
stays cheap.

**Severity default:** High.

## 5. Leaky abstraction / vendor bleed-through

**What:** Infrastructure or vendor details escaping their boundary: ORM
entities as API DTOs, vendor SDK types in domain signatures, HTTP status logic
in domain code, broker-specific headers in business logic.

**Detection signals:** importing the database/ORM/cloud SDK package in domain
or use-case layers (architecture test catches this, rules/02 §5); API responses
that change when an internal column is renamed; "port" interfaces that mirror a
vendor API one-to-one (rules/02 §4).

**Fix:** DTOs at every boundary, consumer-shaped ports, mapping in adapters.
Cheapest enforced as an import-rule fitness function.

**Severity default:** Medium (High when public API = DB schema, since clients
now pin your internals).

## 6. Sync chain of doom / temporal coupling

**What:** Request-path workflows requiring N services up simultaneously;
availability multiplies (0.99^5 ≈ 0.95) and tail latency compounds.

**Detection signals:** traces showing deep sequential fan-out per user request;
a "simple" page making 30 internal calls; timeout budgets that can't fit
(rules/04 §1); incident reports where an unrelated service's outage broke checkout.

**Fix:** Replicate the data you need (event-carried state transfer), accept
staleness; collapse hops (merge services or compose at the edge); make non-
essential steps async (queue, saga). Set a fitness function: max sync depth ≤ 2
on critical paths.

**Severity default:** High on revenue-critical paths.

## 7. Event spaghetti / hidden workflow

**What:** Choreographed events forming a workflow nobody can see: cycles
(A's event triggers B, whose event re-triggers A), side-effect cascades, and
"why did this run?" archaeology.

**Detection signals:** no diagram or registry of who consumes what; event
cycles; an innocuous event causing a 9-hop cascade; debugging requires grepping
all consumers for a topic name; commands disguised as events (rules/03 §6).

**Fix:** Event catalog (producer, consumers, schema, purpose) generated from
code/registry; orchestrate multi-step workflows explicitly (rules/03 §5);
detect and break cycles.

**Severity default:** Medium; High once a cycle exists.

## 8. Cache as source of truth (accidental database)

**What:** Data that exists only in Redis/Memcached, or correctness depending on
cache content (rules/05 §4).

**Detection signals:** writes that go to cache without a durable backing write;
"don't restart Redis, we'll lose X"; missing or infinite TTLs on entries nobody
can rebuild; cache-down = wrong answers rather than slow answers.

**Fix:** Make the durable store authoritative and the cache rebuildable, or
promote the data to a real durable store (Redis with AOF/replication *declared*
as a database, with backup/DR treated accordingly).

**Severity default:** Critical when business data is cache-only.

## 9. Distributed big ball of mud via shared "common" libraries

**What:** A `common`/`shared-utils` library hoarding domain types, clients, and
helpers, version-pinned by every service — coupling all services through the
dependency graph instead of the network.

**Detection signals:** bumping `common` requires releasing everything; domain
entities defined in the shared lib; teams blocked on another team's lib release.

**Fix:** Share only truly generic, stable code (logging, telemetry, auth
middleware) with strict semver. Domain types are duplicated per context
(rules/02 §1) or shared via *schemas* (protobuf/OpenAPI), not via code libraries.

**Severity default:** Medium; High when domain logic lives in the shared lib.

## 10. Resume-driven and dogma-driven architecture

**What:** Technology chosen for novelty or ideology, not problem fit: Kafka for
10 msg/s, Kubernetes for one container, event sourcing for a CRUD app, "no
foreign keys because microservices" inside a single schema.

**Detection signals:** infrastructure whose capacity exceeds need by 100x; no
ADR with rejected alternatives (rules/01 §4); ops burden dominated by tools
serving no measured requirement; the only justification on record is an analogy
to a FAANG blog post.

**Fix:** Demand the ADR with load numbers and consequences; downgrade to boring
technology (managed Postgres, a simple queue, one deployable) where the numbers
say so.

**Severity default:** Medium (High when ops burden causes incidents).

## 11. Lava layer / strangler that never strangles

**What:** Successive half-finished migrations sedimented in the codebase: three
HTTP clients, two ORMs, "old auth" and "new auth" both live, a strangler fig
whose old path was never deleted. Every new engineer adds a fourth pattern
because no one can tell which is canonical.

**Detection signals:** multiple frameworks/libraries serving the same purpose
with no deprecation markers; migration ADRs/tickets open > 2 quarters with both
paths in prod; `_v2`/`_new`/`_legacy` suffixes older than a year; nobody can
answer "which one do I use?" without asking in chat.

**Fix:** Every migration gets a kill date and a completion definition ("old path
deleted") tracked like a feature; freeze new usages of the deprecated pattern
mechanically (lint rule failing on new imports of the old module); finish or
explicitly abandon — a documented "we keep both because X" beats sediment.

**Severity default:** Medium; High when the duplicated layer is security-
relevant (two auth paths = the attacker picks the weaker one).

## 12. Snowflake environments and config sprawl

**What:** Production works because of hand-applied settings nobody recorded;
hundreds of config keys with unknown consumers; per-environment behavior that
exists nowhere in git.

**Detection signals:** "don't touch that box"; IaC plan/apply shows permanent
diff (drift); config keys grep to zero readers; staging incident playbooks
differ from prod's; restoring an environment from code has never been done.

**Fix:** Import live state into IaC, enable drift detection alarms (rules/06
§2, §11); delete config keys with no readers (after a deprecation log-on-read
period); rebuild one environment from code per quarter as a fitness function.

**Severity default:** High (it's unrecoverability in disguise — DR depends on
rebuildability).

## 13. Smaller but deadly (quick list)

- **Fan-out N+1 over the network:** per-item remote calls in a loop → batch APIs / data replication. High on hot paths.
- **Chatty two-way coupling:** A calls B and B calls A → merge them or invert one direction with events. High.
- **Timeout-free integration / retry-everywhere:** see rules/04 §1–2. Critical/High.
- **Config-in-code, env conditionals, secrets in git:** see rules/06 §2. Critical for secrets.
- **Anemic domain + transaction-script-everywhere in a complex core domain:** rules/02 §3. Medium.
- **Entity services (`UserService`, `OrderService` as bags of CRUD)** instead of capability-oriented boundaries → re-cut along use cases/contexts. Medium.
- **Queue as database / years of retention in the broker** for operational reads → project into a store; brokers are transport. Medium.
- **Unowned components:** no team on-call for a prod service (rules/01 §7). Critical.

## Audit checklist

- [ ] Do any two services deploy in lockstep or require synchronized PRs (distributed monolith)?
- [ ] Does more than one service write — or read without a sanctioned contract — the same tables (shared database)?
- [ ] Is there a god component (top of churn + dependency in-degree + size by a wide margin)?
- [ ] Are there more services than the team can independently deploy, operate, and debug (premature microservices)? Could the system collapse to fewer deployables?
- [ ] Do domain/use-case layers import ORM, transport, or vendor SDK types (leaky abstraction)? Are API DTOs the same classes as DB entities?
- [ ] What is the maximum synchronous call depth on revenue-critical paths? Is it > 2?
- [ ] Is there an event catalog? Are there event cycles or multi-hop cascades nobody documented?
- [ ] Is any business data stored only in a cache? Would a cache flush cause wrong answers?
- [ ] Does a shared `common` library contain domain types or force coordinated releases?
- [ ] Is every heavyweight technology (broker, orchestrator, event sourcing) justified by an ADR with measured load, or by fashion?
- [ ] Are there per-item remote calls in loops on hot paths (network N+1)?
- [ ] Does every production component have an owning, on-call team?
- [ ] Are there sedimented half-migrations (duplicate clients/ORMs/auth paths, `_v2`/`_legacy` older than a year) without kill dates?
- [ ] Can every environment be rebuilt from git, or does production depend on hand-applied, unrecorded state (drift in IaC plans)?
