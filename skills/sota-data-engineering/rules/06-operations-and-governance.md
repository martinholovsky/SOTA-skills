# 06 — Operations & Governance

A pipeline that works is a prototype; a pipeline that is deployable,
observable, recoverable, and access-controlled is a product. This file
covers the gap.

## 1. Environments for data

Code environments are easy; **data** environments are where platforms cheat.

- **Three-way isolation as the baseline:** dev (engineers iterate), staging/
  CI (automated validation), prod (consumers). Separate
  databases/schemas/buckets *and* separate credentials — dev code holding
  prod write credentials is a CRITICAL finding waiting for a `--target`
  typo.
- **Dev reads (a copy or view of) prod-shaped data, never writes prod.**
  Patterns, best first:
  - *Zero-copy clones / shallow copies* (warehouse clones, table-format
    snapshots): instant, cheap, real data shape.
  - *Sampled subsets* refreshed on schedule: fast dev iteration; document
    the sampling so devs don't "discover" sampling artifacts.
  - *Masked copies* where PII rules require (PII handling itself:
    [`sota-privacy-compliance`](../../sota-privacy-compliance/SKILL.md)). Production PII in dev environments = HIGH.
- Synthetic-only dev data is a trap: pipelines pass on clean synthetic rows
  and die on real-world nulls/dupes/encodings. Use sampled-real (masked)
  where at all possible.
- **Schema parity:** dev/staging schemas built by the same code path
  (migrations / dbt) as prod — never hand-maintained copies that drift.
- Per-PR ephemeral schemas (e.g. `pr_1234` in a CI database) beat one
  shared, perpetually-dirty "staging" everyone fights over.

## 2. Deploying pipeline changes

Pipeline code is software: version control, review, CI ([rules/02](02-pipelines-and-orchestration.md), 04). The
extra dimension is that deploys change *tables others read*.

### Write-Audit-Publish (WAP) — default for risky changes

Never let unvalidated data become visible to consumers.

1. **Write** the new run's output to an unpublished location: a staging
   table, an Iceberg branch (engine support varies — verify yours), or an
   unswapped table version.
2. **Audit:** run the block-tier quality battery ([rules/04](04-data-quality-and-contracts.md)) against the
   unpublished output — plus diff-vs-current checks for logic changes (row
   counts, key metric deltas within tolerance).
3. **Publish** atomically only on pass: branch fast-forward, partition
   swap, view-pointer flip, or atomic table swap.

Failed audit = nothing published, consumers see last good data + a freshness
note. This converts "we shipped wrong numbers" into "we shipped late."

```sql
-- BAD: write directly to the consumer-facing table, validate afterwards
INSERT OVERWRITE fct_orders PARTITION (ds='2026-06-11') SELECT ...;
-- (checks run later; consumers already saw whatever landed)

-- GOOD: WAP — write unpublished, audit, publish atomically
INSERT OVERWRITE fct_orders__wap PARTITION (ds='2026-06-11') SELECT ...;
-- run block-tier checks against fct_orders__wap; only then:
ALTER TABLE fct_orders REPLACE PARTITION (ds='2026-06-11')
  FROM fct_orders__wap;   -- engine-specific: Iceberg branch fast-forward,
                          -- partition exchange, or atomic view re-point
```

### Blue-green tables for breaking rebuilds

For logic changes that rewrite a whole mart: build `fct_orders__v2`
alongside, validate (full quality battery + reconciliation against v1 with
expected-diff documentation), then repoint the consumer-facing **view** to
v2. Keep v1 queryable through the agreed deprecation window for rollback and
consumer comparison.

- Corollary: **consumers read views, not physical tables.** The
  view layer is your indirection for blue-green, refactors, and renames.
- Rollback plan is part of the deploy: previous table/snapshot retained
  until the change has survived N cycles.
- **AUDIT:** Logic changes that rewrite consumer-facing tables in place
  with no validation gate = HIGH; with no rollback artifact = HIGH.

## 3. Access control

(Mechanics of RBAC/row policies live with the engine — [`sota-databases`](../../sota-databases/SKILL.md);
PII classification and lawful basis — [`sota-privacy-compliance`](../../sota-privacy-compliance/SKILL.md). This is the
data-platform layer.)

- **Grant to roles per layer, least privilege:** consumers get read on
  marts only (raw/staging contain unmodeled PII and un-cleaned data);
  pipelines get write only to their layer; humans don't share the service
  account. BI service accounts with `SELECT ANY` on raw = HIGH.
- **Column-level controls** (masking policies, secure views) for PII columns
  that must coexist with analytics — masked by default, unmasked for an
  audited role. **Row-level** policies for multi-tenant or
  regional-restriction marts.
- Tag/classify PII columns in the catalog at ingestion and let policies key
  off tags — per-column manual grants don't survive schema growth.
- Audit logging on access to sensitive marts; review grants on a schedule
  (orphaned humans, over-privileged services).

## 4. Retention & GDPR deletion in immutable-ish stores

"Immutable raw forever" collides with deletion duties. Design for erasure
up front; retrofitting is brutal.

- **Know where every subject's data lives:** PII column tags + lineage
  ([rules/04](04-data-quality-and-contracts.md)) make "find all copies" answerable. Copies include: raw,
  staging, marts, snapshots/time-travel, DLQs, dev clones, BI extracts.
- **Lakehouse deletion that actually deletes:** `DELETE`/`MERGE` on
  Iceberg/Delta marks rows deleted in the *current* snapshot — the bytes
  live on in old snapshots/files until **snapshot expiry + compaction/
  vacuum** run. The erasure SLA must account for the full chain: delete →
  expire snapshots → rewrite/vacuum files. Deletion-vector/merge-on-read
  tables additionally need compaction to physically drop the rows.
- **Kafka:** compacted topics honor tombstones (eventually — compaction
  lag); time-retention topics age data out. Long/infinite-retention topics
  containing PII need a deletion story or pseudonymization at produce time.
- **Crypto-shredding** (per-subject encryption keys; erase the key to erase
  the data) is the pragmatic answer for deep-archive/backup layers where
  rewriting is infeasible — key management discipline required
  ([`sota-secrets-management`](../../sota-secrets-management/SKILL.md)).
- Retention policies are **enforced by scheduled jobs, not by policy
  documents**: raw N months, snapshots N days, DLQs N days, dev clones
  auto-expire. Unbounded-retention PII stores = HIGH.
- Deletion requests are pipelines too: idempotent, monitored, with
  completion SLO and verification query.

## 5. Observability for pipelines

(Generic telemetry stack: [`sota-observability`](../../sota-observability/SKILL.md). Data-specific layer here.)

- **The four golden signals of data:** freshness (did it land on time?),
  volume (the right amount?), quality (checks green?), lineage-aware status
  (what's blocked downstream?). One dashboard, all critical marts,
  red/green per signal.
- **Alert on consumer-facing symptoms, route to the owning team:** "mart X
  stale > SLO" beats 14 task-level alerts that all mean the same outage.
  Task-level detail belongs in the runbook drill-down, not the page.
- Every alert has an **owner and a runbook link**. Unrouted alerts and
  alert channels with >daily noise = the platform is unmonitored in
  practice (MEDIUM, HIGH for critical marts).
- Track **cost** as a first-class signal ([rules/05](05-storage-and-performance.md)): per-pipeline spend
  trend on the same dashboard — cost regressions are incidents too.
- SLOs documented per critical mart (freshness target + measurement) and
  reviewed; an SLO nobody measures is decoration.

## 6. Runbook discipline

- Every production pipeline has a runbook answering: what it produces and
  for whom (links to contracts/SLOs); how to rerun/backfill an interval
  (exact command); known failure modes and fixes; upstream/downstream
  contacts; escalation path.
- Runbooks live next to the code (repo `runbooks/` or per-DAG docs), are
  linked from every alert, and are updated as part of incident postmortems
  ([rules/04](04-data-quality-and-contracts.md)). A runbook last touched two years before the last incident is
  fiction.
- Test the runbook: a new on-call engineer should be able to execute a
  rerun from it without tribal knowledge. If only one person can operate a
  pipeline, that's a HIGH operational finding regardless of code quality.

## Audit checklist

- [ ] Dev/staging/prod separated in storage *and* credentials; dev cannot
      write prod (dev holding prod write credentials = CRITICAL) (§1)?
- [ ] Dev data is cloned/sampled (masked where PII; production PII in dev =
      HIGH), refreshed by automation, not synthetic-only; schemas built from
      the same code as prod (§1)?
- [ ] Risky changes gated by WAP (publish atomically only on a passed
      block-tier audit) or blue-green + reconciliation; consumers read through
      views? In-place rewrite with no validation gate = HIGH (§2)
- [ ] Rollback artifact (previous table/snapshot) retained for every
      consumer-facing change until it has survived N cycles (none = HIGH)
      (§2)?
- [ ] Layer-based grants: no consumer/BI access to raw (BI `SELECT ANY` on
      raw = HIGH); pipelines write only to their layer; no shared human use of
      service accounts (§3)?
- [ ] PII columns tagged; masking/row policies keyed off tags; access to
      sensitive marts audit-logged; grants reviewed on a schedule (§3)?
- [ ] GDPR erasure path covers snapshots, compaction, DLQs, dev clones,
      and Kafka retention — with a measured SLA; deletion requests run as
      idempotent, monitored pipelines with a verification query (§4)?
- [ ] Retention enforced by scheduled jobs for every layer (raw, snapshots,
      DLQ, dev clones)? Unbounded-retention PII stores = HIGH (§4)
- [ ] Freshness/volume/quality dashboard for critical marts; alerts
      symptom-based, owned, runbook-linked, low-noise (unrouted or >daily noise
      = MEDIUM, HIGH for critical marts); freshness SLO documented and measured
      per critical mart (§5)?
- [ ] Per-pipeline cost visible with trend alerts (§5)?
- [ ] Runbooks current, co-located with code, linked from every alert,
      executable by a newcomer (rerun/backfill command, failure modes,
      contacts, escalation)? A pipeline only one person can operate = HIGH (§6)