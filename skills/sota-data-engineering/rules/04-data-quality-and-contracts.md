# 04 — Data Quality & Contracts

Bad data that flows is worse than no data: dashboards stay green, decisions
get made, and trust — the only real product of a data platform — erodes.
Quality is enforced at boundaries and tiered by consequence.

## Data contracts at the producer boundary

A contract is **schema + semantics + SLOs**, owned by the producer, enforced
mechanically. Schema alone is half a contract.

- **Schema:** field names, types, nullability, enums — registered and
  compatibility-checked (registry for streams, declared source schemas or
  dbt model contracts for batch).
- **Semantics:** grain ("one row per order line"), key uniqueness, units and
  timezone (`amount` in cents? `created_at` in UTC?), enum meanings,
  delete behavior (hard/soft/tombstone).
- **SLOs:** freshness ("available by 06:00 UTC", "p99 event lag < 5 min"),
  completeness, and a deprecation policy (notice period for breaking
  changes).
- **Enforcement beats documentation:** CI on the producer side fails builds
  that break the contract (schema registry compat check, dbt `contract:
  enforced`, contract-test suites). A contract in a wiki nobody's CI reads =
  LOW-value; consumers breaking on producer deploys despite a "contract" =
  HIGH.
- Contracts go where ownership changes hands: source→platform and
  mart→consumer. Don't contract every internal model — that's change
  friction without protection.

```yaml
# GOOD: dbt model contract on a mart boundary
models:
  - name: fct_orders
    config:
      contract: {enforced: true}
    columns:
      - name: order_line_id
        data_type: bigint
        constraints: [{type: not_null}]
        tests: [unique]
      - name: amount_usd_cents   # unit in the name beats unit in the wiki
        data_type: bigint
```

## Expectation testing — the core battery

Every core/mart model carries checks from this battery; critical ones carry
all that apply.

- **Freshness:** `max(loaded_at)` within SLO. The single highest-value
  check — most data incidents are "it silently stopped."
- **Volume:** row count of the latest interval within expected band
  (absolute bounds or relative to trailing window, e.g. ±50% of 7-day
  median; use week-over-week comparisons for weekly-seasonal data).
  Zero-row intervals almost always block.
- **Nulls:** `not_null` on keys and critical measures. Watch *null-rate
  jumps* on optional columns too — a field going 2%→40% null is an upstream
  break that `not_null` won't catch.
- **Uniqueness:** primary/grain key unique. Duplicate grain = every
  downstream aggregate inflated = block-tier, always.
- **Referential integrity:** facts' FKs resolve to dimensions (or to an
  explicit `unknown` member). Orphaned facts silently vanish from
  inner-join dashboards.
- **Accepted values / ranges:** enums in the known set; amounts within sane
  bounds; dates not in the future (a `2106-02-07` timestamp is an epoch bug,
  not a fact).
- **Distribution drift:** track means/quantiles/category mix on
  business-critical columns; alert on significant shift. Warn-tier — drift
  is a question, not a verdict.
- **Reconciliation / control totals:** a row count alone passes a load that
  truncated a column, zeroed an amount or swapped keys. For every data set
  moved between systems (extract, replication, cross-engine copy), compute
  at the source *and* at the destination: the row count, a sum over each
  key numeric measure, and an order-independent fingerprint of the key
  columns (per-row hash of a canonical text form, summed modulo a large
  prime). Compare before publishing; a mismatch is block-tier. Pin the
  canonical form (NULL token, float/decimal scale, timestamp zone) so both
  engines hash the same bytes. Aggregate with a sum, not XOR: XOR is also
  order-free but an even number of duplicated rows cancels out. OWASP:
  Go-SCP (validation).

```yaml
# GOOD: minimum battery on a critical mart, tiered (dbt syntax; Soda/GX
# equivalents exist for all of these)
models:
  - name: fct_orders
    tests:
      - dbt_utils.recency:            # freshness — blocks
          datepart: hour, field: loaded_at, interval: 26
      - dbt_utils.expression_is_true: # volume — warns, human triages
          expression: >
            (SELECT count(*) FROM {{ this }} WHERE order_date = current_date - 1)
            BETWEEN 0.5 * {{ var("orders_daily_median") }}
                AND 2.0 * {{ var("orders_daily_median") }}
          config: {severity: warn}
    columns:
      - name: order_line_id
        tests: [unique, not_null]     # grain — blocks, always
      - name: customer_id
        tests:
          - relationships: {to: ref('dim_customer'), field: customer_id}
```

## Severity tiers: block vs warn

Two failure modes to avoid: everything blocks (one flaky check halts the
platform nightly, team starts ignoring red) and nothing blocks (corrupt data
flows downstream while a Slack channel nobody reads fills up).

- **Block (fail task, stop downstream):** contract violations, duplicate
  keys, null keys, zero-row loads, broken referential integrity on critical
  marts. Criterion: *would you rather show stale data than this data?* If
  yes → block. Stale + alert beats wrong + silent.
- **Warn (alert, let flow):** drift, moderate volume anomalies, null-rate
  shifts on non-key columns, slow-burn issues.
- Every warn goes to an **owned** channel with a triage expectation. A
  warn-tier check failing for 3+ weeks untriaged = the check is dead;
  fix it or delete it (MEDIUM finding).
- Implement tiers natively: dbt test `severity: error|warn`, Great
  Expectations / Soda / pandera equivalents all support it.

## Anomaly detection caution

ML-based anomaly detection on data metrics (auto-thresholds on volume,
freshness, distributions) is a **supplement, not a substitute** for explicit
checks.

- It cannot block (too many false positives) and it can't encode semantics
  ("orders must never be negative").
- Untuned anomaly monitors produce alert fatigue that kills the *real*
  alerts. Budget alerts-per-week per owner; tune or cut anything over.
- Right order: explicit battery on what you know must hold → anomaly
  detection for the unknown-unknowns on a *small* set of business-critical
  tables.

## Lineage

- Table-level lineage is table stakes — it falls out of dbt/orchestrator
  graphs. Use it for impact analysis ("what breaks if I change this?") and
  incident blast-radius.
- **Column-level lineage pays where:** PII propagation must be traced
  (which marts contain `email`? — see `sota-privacy-compliance`),
  regulated-metric provenance, and deprecating wide legacy tables. Don't
  buy/maintain column-level everywhere for its own sake.
- Lineage that requires manual upkeep will rot; derive it from code
  (parsed SQL, orchestrator metadata) or don't claim it.

## Data incident response

When bad data ships, the order is: **stop the spread → communicate →
quarantine → fix → reprocess → verify → postmortem.**

1. **Stop the spread:** pause downstream pipelines/reverse-ETL consuming the
   bad data. Blocking checks should have done this; do it manually if not.
2. **Communicate first, fix second:** notify downstream owners and stamp
   affected dashboards ("data since DATE under investigation") *before*
   debugging. Consumers acting on known-bad data is the real damage.
3. **Quarantine:** snapshot/copy bad partitions for forensics; with
   Iceberg/Delta, note the pre-incident snapshot ID — time travel is your
   forensic record (until retention expires it; act fast, see rules/05).
4. **Fix and reprocess** through the normal backfill path (rules/02) —
   never hand-`UPDATE` a mart; if raw is intact, re-derive. This is where
   idempotency pays its rent.
5. **Verify** with the same checks that should have caught it — and add the
   check that was missing.
6. **Postmortem** for trust-damaging incidents: which boundary lacked which
   check; fix the class, not the instance.
- **AUDIT:** No documented incident path / no way to mark data as
  known-bad to consumers = MEDIUM; becomes HIGH for platforms feeding
  financial or operational decisions.

## Testing pipelines (CI)

Quality checks validate *data in production*; tests validate *logic before
merge*. You need both — a check can't catch a bug that produces plausible
numbers.

- **Unit-test transforms with fixture data:** tiny handcrafted inputs +
  expected outputs, covering edge cases (nulls, duplicates, late rows,
  timezone boundaries, empty input). dbt unit tests (1.8+), pytest +
  DuckDB/Polars for Python transforms, or framework-native harnesses for
  streaming (e.g. topology test drivers).

```yaml
# GOOD: dbt unit test — logic verified pre-merge, no warehouse data needed
unit_tests:
  - name: dedupe_keeps_latest_version
    model: stg_orders
    given:
      - input: source('shop', 'orders')
        rows:
          - {order_id: 1, status: "open",   _loaded_at: "2026-01-01"}
          - {order_id: 1, status: "closed", _loaded_at: "2026-01-02"}
    expect:
      rows:
        - {order_id: 1, order_status: "closed"}
```
- **DuckDB as the CI workhorse:** runs most ANSI-ish SQL in-process — fast
  warehouse-free tests for portable SQL. Dialect-specific SQL still needs a
  dev schema in the real engine (cheap, ephemeral, per-PR).
- **CI on sample data:** build changed models + downstream against
  representative samples; full-volume runs are for staging, not per-PR.
- Pure functions are testable functions: keep transforms free of hidden
  `NOW()`/env reads (rules/02's logical-time rule makes this automatic).
- **AUDIT:** A transform repo with zero tests where a one-character SQL
  change can silently flip a company metric = HIGH.

## Audit checklist

- [ ] Producer-boundary contracts exist (schema + semantics + SLOs) and are
      CI-enforced, not wiki-only?
- [ ] Every core/mart model: freshness, volume, unique-key, not-null-key
      checks at minimum?
- [ ] Checks explicitly tiered; block-tier actually stops downstream
      (not just alerts)?
- [ ] Zero-row and duplicate-key conditions block on critical marts?
- [ ] Warn alerts owned and triaged — no weeks-old ignored failures?
- [ ] Referential integrity checked between facts and dimensions?
- [ ] HIGH: data sets moved between systems reconciled on control totals
      (count + key-measure sums + order-independent key hash), block-tier —
      not on row count alone? Probe (lists reconciliation files with no
      sum/hash):
      `grep -rliE 'reconcil|row_?count' --include='*.sql' --include='*.py' --include='*.yml' . | xargs grep -LiE 'sum\(|hash|checksum|md5|sha'`
- [ ] Anomaly detection (if any) supplements explicit checks and isn't an
      alert-fatigue source?
- [ ] Lineage derivable from code; column-level where PII/regulatory needs
      it?
- [ ] Incident path documented: pause downstream, notify, quarantine,
      reprocess via backfill, verify?
- [ ] Transform logic unit-tested with fixtures; CI builds changed models
      pre-merge?