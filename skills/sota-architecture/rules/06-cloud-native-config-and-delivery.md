# 06 — Cloud-Native Operations, Config & Delivery (12-Factor, 2026 Edition)

The 12-factor principles, updated for containers, orchestrators, and modern
delivery. These are the operational contract every service must satisfy
regardless of architecture style.

## 1. Build/release/run: one artifact, promoted everywhere

**Rule:** Build one immutable artifact (container image, digest-pinned) per
commit; promote that exact artifact through dev → staging → prod. Environment
differences live entirely in config (§2). Rebuilding per environment means you
test one binary and ship another.

**Rule:** Releases are versioned and rollback-able: previous release = previous
(artifact, config) pair, redeployable in minutes (rules/04 §9). Tag images with
commit SHA; `latest` in any deployment manifest is a High finding.

**Rule:** Declare all dependencies explicitly with lockfiles; build in clean
environments. Anything "installed on the host" that the app needs is an
undeclared dependency and will bite during scale-out or migration.

## 2. Config: environment-injected, schema-validated, secrets separate

**Rule:** Config that varies by environment (URLs, pool sizes, flags defaults,
credentials) is injected at runtime (env vars, mounted files, config service) —
never compiled in, never `if env == "prod"` branches in code. Code with
environment-name conditionals can't be tested for prod behavior outside prod.

**Rule:** Validate all config at startup against a typed schema and **fail fast**
with a message naming the bad key. A service that boots with a missing config
and fails on first use turns a deploy-time error into a 3 a.m. incident.

**Rule:** Secrets are not config: they come from a secret manager (Vault, cloud
secret stores) or orchestrator secrets with rotation support — never in env-var
dumps in CI logs, never in the image, never in git (enforce with secret-scanning
in CI). Support rotation without redeploy where feasible (file-mounted, reloaded).

**Rule:** Keep declarative deployment config (manifests, IaC) in git, reviewed
like code (GitOps). Live-mutated infrastructure ("someone changed it in the
console") is configuration drift; drift detection should alarm.

## 3. Processes, disposability, and concurrency

**Rule:** Processes are stateless and share-nothing (rules/05 §1); scale via
process/replica count, not threads-per-giant-instance alone. Start fast
(seconds), shut down gracefully on SIGTERM (drain, then exit; rules/04 §9),
and tolerate sudden death (orchestrators kill freely).

**Rule:** Run one concern per process: web serving, queue workers, and schedulers
are separate deployments with separate scaling (rules/05 §8). Cron-in-a-web-pod
runs N times on N replicas — use the platform scheduler or a leader-elected/
distributed-locked runner, designed idempotent (rules/03 §2).

**Rule:** Logs go to stdout/stderr as structured JSON events; the platform
ships them. Apps never manage log files, rotation, or destinations.

## 4. Observability is a launch requirement (the 13th factor)

**Rule:** Every service ships with, before first prod deploy:
- **Structured logs** with correlation/trace IDs and tenant/user context (no PII/secrets — enforce with log scrubbing).
- **Metrics**: RED (rate, errors, duration) per endpoint/consumer + key business metrics + saturation (pools, queues).
- **Distributed traces** (OpenTelemetry), context propagated across HTTP *and* queues (rules/03 §9).
- **SLOs with alerts on burn rate** — alert on user-impacting symptoms (SLO burn), page on those; cause-based alerts are tickets, not pages.

**Rule:** If you can't answer "what did request X do across services, and why was
it slow?" from telemetry alone, observability is insufficient — that's a High
finding regardless of how the dashboards look.

## 5. Backing services are attached, swappable resources

**Rule:** Treat every backing service (DB, cache, broker, email, third-party
API) as an attached resource addressed by config and accessed through a port/
adapter (rules/02 §4). Swapping prod Postgres for a different instance — or a
local container in dev — must require only a config change.

**Rule:** Dev/prod parity: develop and CI-test against the same *kind* of
backing services as production (Postgres in a container, real broker via
testcontainers), not in-memory fakes of databases. SQLite-in-dev/Postgres-in-
prod ships query bugs straight to production.

## 6. Feature flags: decouple deploy from release

**Rule:** Deploy continuously; release via flags. Every risky or user-visible
change ships dark behind a flag, then rolls out progressively (1% → 10% → 50% →
100%) with metrics watched per cohort and instant kill-switch rollback. This —
not deploy rollback — is your primary mitigation lever.

**Rule:** Flag discipline, enforced:
- Every flag has an owner, a description, and an **expiry/removal ticket** at creation. Permanent "flags" (ops kill switches, entitlements) are explicitly marked as such; everything else is temporary.
- Remove flags within weeks of 100% rollout. A codebase with hundreds of stale flags has 2^N untested configuration states — that's the anti-pattern, not a capability.
- Flag evaluation is local/SDK-cached with a hard default if the flag service is down (flag service must never be a request-path single point of failure).
- Flag checks live at the smallest number of choke points (one branch at the use-case boundary), not sprinkled through every layer.
- Flag changes are audited (who flipped what when) — they are production changes.

**Rule:** Use flags for operational levers too: load-shedding tiers (rules/04
§6), degradation switches (rules/04 §5), and migration cutovers (rules/01 §8).
Test both states of every active flag in CI for critical paths.

**Rule:** A progressive rollout means **two versions of the application are running at
once**, so both flag states must be compatible with the schema *as it is right now* —
not with the schema either version was written against. The flag rule and the migration
rule interact and neither is sufficient alone: expand/contract makes the *schema* safe
for two readers (`sota-databases` rules/02), and the flag makes the *behaviour*
switchable, but nothing checks that the off-state still works after the contract step
has run. Order it: expand → deploy both-compatible code → roll the flag → **remove the
flag** → contract. Contracting while a flag can still route traffic to the old path is
the version-skew outage, and it presents as "the rollback made it worse" because the
rollback target no longer matches the data.

## 7. Delivery pipeline and environments

**Rule:** Trunk-based development with small PRs; every merge produces a
deployable artifact passing: unit + contract tests (rules/03 §8), architecture
fitness functions (rules/01 §5), security and secret scans, and migration lint.
Long-lived feature branches are inventory and merge risk; flags (§6) replace them.

**Rule:** Deploys are progressive (canary or rolling with automated rollback on
SLO regression) and boring: no scheduled "deployment windows," no manual steps.
Deploy frequency is a health metric; if deploys are scary, fix the pipeline, not
the calendar.

**Rule:** Database migrations are decoupled from code deploys and always
expand/contract (additive change → deploy code reading both → backfill →
contract). Any migration that would break the *previous* code version blocks
rollback and is a High finding.

## 8. Admin processes and operational surface

**Rule:** One-off admin tasks (backfills, fixes, replays) run as versioned,
reviewed code (jobs/scripts in the repo) in the same environment/config as the
app — never as ad-hoc SQL in a prod console. Make the dangerous path inconvenient
and the safe path easy.

**Rule:** Every service exposes a minimal operational surface: health endpoints
(rules/04 §7), build/version info endpoint, and runtime-adjustable log level.
Every service has a runbook covering: dashboards, common failure modes, DLQ
redrive, scaling levers, and rollback.

## 9. Cost and sustainability as architectural signals

**Rule:** Tag every resource with service + team + (where applicable) tenant;
review cost per service monthly. Cost anomalies are architecture smells: an
unexpectedly expensive service usually has a chatty integration, a missing
cache, unbounded retention (rules/05 §6), or over-provisioned idle capacity.

**Rule:** Set cost fitness functions for the big levers (egress, storage growth,
per-request compute) with alerts — treat a 2x cost regression like a 2x latency
regression.

## 10. Supply-chain integrity

**Rule:** Pin and verify everything that enters the artifact: lockfiles for app
dependencies, digest-pinned base images, dependency update automation
(Renovate/Dependabot) with CI gates rather than hand-rolled upgrades twice a
year. Generate an SBOM per build and scan images for known vulnerabilities as a
pipeline gate (severity threshold, with an expiring-exception process — not a
permanent ignore file).

**Rule:** Sign artifacts (e.g., Sigstore/cosign) and verify signatures at
deploy/admission time, so "what's running" provably equals "what CI built".
Build provenance (SLSA-style) matters most for anything handling money or PII.

**Rule:** Third-party base images and Helm charts are dependencies too: mirror
them into your registry; never deploy straight from a public registry that can
change or vanish under you.

## 11. Environments: ephemeral over snowflake

**Rule:** Environments are created and destroyed from code (IaC + seeded data),
not curated by hand. Prefer ephemeral per-PR preview environments for
integration verification over one perpetually-broken shared "staging" that
serializes every team.

**Rule:** Staging-like environments earn their cost only if they're
production-shaped where it matters: same topology (real broker, real DB engine,
same proxy chain), scaled down. A staging that differs in kind, not just size,
validates nothing — pair it with progressive prod delivery (§7) and testing in
production behind flags (§6) instead of pretending.

**Rule:** Never let environments share backing state (queues, buckets, third-
party sandboxes) without namespacing — cross-environment bleed produces the
least reproducible bug class there is.

## 12. Telemetry cost and cardinality discipline

**Rule:** Metrics labels are a contract with your bill and your query latency:
never label by unbounded dimensions (user ID, request ID, full URL). Tenant ID
as a label is acceptable only below a known tenant-count ceiling; beyond it,
use exemplars or logs.

**Rule:** Trace-sample deliberately: head-sample a base rate, tail-sample
errors and slow requests at 100%. Log levels are runtime-adjustable (§8);
DEBUG-in-prod-by-default is a cost incident and occasionally a PII incident.

**Rule:** Telemetry pipelines are backpressure-aware and lossy-by-design for
the app: dropping a span must never block or crash request serving (bounded
buffers, drop-and-count).

## Audit checklist

- [ ] For any flag rolled out across a schema change: is the **contract step ordered after
      flag removal**, and does the off-state still work against the current schema? Two app
      versions run during a rollout, and contracting while the old path is still reachable is
      the version-skew outage that presents as "the rollback made it worse" (§6).

- Is exactly one immutable, digest-pinned artifact built per commit and promoted across environments? Any `latest` tags or per-env rebuilds?
- Is all environment-varying config injected at runtime, schema-validated at startup with fail-fast? Any `if env == "prod"` branches?
- Are secrets sourced from a secret manager with rotation, absent from git/images/CI logs, with scanning enforced in CI?
- Are deployment manifests/IaC in git with drift detection?
- Do processes start in seconds, drain on SIGTERM, and survive sudden kill? Are web/workers/schedulers separate deployments?
- Are scheduled jobs single-run-safe (leader election/locks) and idempotent?
- Do logs go to stdout as structured events with trace and tenant context, scrubbed of secrets/PII?
- Are RED metrics, OTel traces (propagated through queues), and burn-rate SLO alerts in place? Do pages fire on symptoms, not causes?
- Does dev/CI use production-kind backing services (real DB/broker in containers)?
- Does every flag have an owner and expiry? Are stale flags (>100% rollout for months) present? Does flag evaluation have local defaults if the flag service dies?
- Are releases progressive (canary + auto-rollback) and decoupled from deploys via flags?
- Are all migrations expand/contract such that the previous code version still runs (rollback-safe)?
- Do admin/backfill tasks run as reviewed, versioned jobs rather than console surgery?
- Are resources cost-tagged per service/team with anomaly alerting?
- Are base images digest-pinned and mirrored, SBOMs generated, image scans gating CI with expiring exceptions, and artifacts signed + verified at admission?
- Can a full environment be recreated from code? Are preview/ephemeral environments available, and is shared backing state namespaced per environment?
- Do metric labels avoid unbounded cardinality, is trace sampling tail-biased toward errors/slow requests, and can telemetry loss never block request serving?
