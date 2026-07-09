# 02 — Pipelines & Orchestration

The prime directive: **every pipeline run is safe to repeat.** Retries,
backfills, and "just rerun it" are how data platforms are actually operated;
a pipeline that corrupts on rerun is broken even if its happy path is
perfect.

## Idempotency — the prime directive

A task given the same logical interval must produce the same stored result
no matter how many times it runs, and a partial failure mid-run must not
leave double-counted or half-written data.

- **Choose the write strategy before the transform:**
  - *Partition overwrite* (delete-insert or `INSERT OVERWRITE` /
    `replace_where`): default for interval-partitioned facts. The task owns
    exactly its interval's partition(s) and replaces them wholesale.
  - *MERGE on a unique key:* for upserted entities/dimensions and late-data
    cases where the interval doesn't bound the affected rows.
  - *Full rebuild:* fine for small dimensions/marts — simplest possible
    idempotency.
  - *Blind append:* only into the immutable raw landing zone keyed by a
    unique load ID, never into modeled layers. **A scheduled `INSERT INTO ...
    SELECT` against a modeled table is a CRITICAL finding** — every retry
    duplicates rows.
- **Writes must be atomic per run.** Table formats (Iceberg/Delta) give
  atomic commits; on plain Parquet, write to a temp prefix and swap. Never
  delete-then-insert as two separately failable steps without a transaction
  or atomic swap.
- **Side effects too:** notifications, reverse-ETL pushes, API calls inside
  pipelines need idempotency keys, or must move to a terminal step that runs
  only after the data write commits.

```sql
-- BAD: duplicates on every retry/rerun
INSERT INTO fct_orders
SELECT ... FROM stg_orders WHERE order_date = '{{ ds }}';

-- GOOD: rerun-safe partition replacement (engine-equivalents: Iceberg
-- INSERT OVERWRITE, Delta replaceWhere, BigQuery MERGE/partition decorator)
DELETE FROM fct_orders WHERE order_date = '{{ ds }}';
INSERT INTO fct_orders SELECT ... FROM stg_orders WHERE order_date = '{{ ds }}';
-- (as one transaction / atomic commit)

-- GOOD: keyed merge when rows aren't bounded by the interval
MERGE INTO dim_customer t USING batch s ON t.customer_id = s.customer_id
WHEN MATCHED THEN UPDATE SET ...
WHEN NOT MATCHED THEN INSERT ...;
```

## Logical time, not wall-clock time

- **The orchestrator supplies the interval; the task uses only that.**
  `WHERE created_at >= NOW() - INTERVAL '1 day'` is a HIGH finding: results
  depend on when the task ran, reruns produce different data, and backfills
  are impossible.
- Parameterize every extraction and transform by `[interval_start,
  interval_end)`. Half-open intervals; never overlap, never gap.
- Late-arriving data: don't widen the window with fudge factors ("reprocess
  last 3 days just in case") as the *only* mechanism — that's a cost/cover
  tradeoff that still misses data later than the fudge. Prefer watermark
  columns (below) or merge-based reprocessing of affected keys.

```python
# BAD: wall-clock-relative — rerun tomorrow, get different data
@task
def extract():
    df = read_sql(f"SELECT * FROM orders WHERE created_at > "
                  f"'{datetime.now() - timedelta(days=1)}'")

# GOOD: orchestrator-supplied logical interval — rerunnable forever
@task
def extract(data_interval_start, data_interval_end):
    df = read_sql(
        "SELECT ... FROM orders WHERE created_at >= %s AND created_at < %s",
        (data_interval_start, data_interval_end),
    )
```

## Incremental processing & watermarks

- **Incremental by default for large sources.** Track a high-water mark on a
  monotonic column (`updated_at`, log sequence number, ingestion time) and
  select `> last_watermark AND <= new_watermark`. Persist the watermark
  transactionally **with** the load — watermark stored in a separate system
  updated after the write is a classic double/miss bug.

```sql
-- BAD: watermark = "whatever was max at read time", stored elsewhere later.
-- Crash between load and watermark-update => reprocess or skip.

-- GOOD: bounded window, watermark committed with the data
BEGIN;
INSERT INTO staging_orders
  SELECT * FROM src.orders
  WHERE updated_at > (SELECT wm FROM etl.watermarks WHERE tbl='orders')
    AND updated_at <= :new_wm;          -- bounded above: deterministic
UPDATE etl.watermarks SET wm = :new_wm WHERE tbl='orders';
COMMIT;
```
- `updated_at` maintained by application code is unreliable (bulk fixes skip
  it, clock skew). Prefer DB-generated change tracking or CDC (rules/03)
  for correctness-critical syncs; periodically reconcile row counts against
  the source either way.
- **Late data policy is explicit per table:** how late is accepted (e.g.
  reprocess partitions up to 7 days back via merge), and what happens after
  (corrections batch, or documented "closed" partitions).
- In dbt: incremental models must define `unique_key` (or use
  insert-overwrite strategy) and handle the full-refresh path; an
  incremental model that appends without a key is the same CRITICAL as
  above.

## Backfill design

Backfills are a feature you design, not an emergency you improvise.

- Every pipeline is runnable for an **arbitrary historical interval** with
  the same code path as the scheduled run (this falls out of logical-time
  parameterization).
- **Bound parallelism.** Backfilling 3 years of daily partitions must not
  fire 1,000 concurrent tasks at the source DB or warehouse. Cap concurrency
  (e.g. Airflow `max_active_runs`/pools) and consider chunked
  ranges (monthly chunks of daily logic) for efficiency.
- Order matters when models depend on prior intervals (cumulative tables,
  SCDs): declare `depends_on_past`-style constraints; otherwise allow
  parallel intervals.
- Quality checks run on backfilled partitions too — a backfill that bypasses
  checks is how bad history gets written.
- **AUDIT:** Ask "how would you reload March?" If the answer involves editing
  code or manual SQL, that's a HIGH finding.

## Orchestration discipline

Applies to Airflow (3.x as of 2026), Dagster, Prefect, and kin.

- **The DAG declares ALL dependencies.** Hidden coupling — task B reads a
  table task A writes, but no edge exists and B just runs "later by cron" —
  is a HIGH finding (cron-spaghetti). Prefer dataset/asset-aware scheduling
  (Airflow assets, Dagster assets): downstream runs *because* upstream
  produced, not because it's 6am. Partitioned assets (Airflow 3.2+) extend
  this per logical interval — downstream triggers per partition, unifying
  asset scheduling with the logical-time rule above.

```python
# BAD: coupled by cron offsets and hope
ingest_dag  = DAG("ingest",  schedule="0 5 * * *")
mart_dag    = DAG("marts",   schedule="0 6 * * *")  # "ingest is done by 6, right?"

# GOOD: data-aware — marts run when the asset is actually updated
orders_stg = Asset("warehouse://staging/orders")
ingest_dag = DAG("ingest", schedule="0 5 * * *")    # producer task outlets=[orders_stg]
mart_dag   = DAG("marts",  schedule=[orders_stg])   # consumer triggered by production
```
- **Tasks are stateless and idempotent**; orchestrator metadata is not a data
  store. No XCom-ing dataframes; pass references (paths, table names,
  intervals).
- **Retries: limited and meaningful.** 2–3 retries with exponential backoff
  for transient failures. Retrying a deterministic transform error 10 times
  is noise; retrying forever masks outages. Alert on final failure, always.
- **Timeouts on every task** sized from observed duration; a hung extraction
  blocking the daily run for 12 silent hours is an availability incident.
- **SLAs/freshness alerts on outcomes, not just task failure:** "mart X not
  updated by 7am" pages someone even if no task technically failed (e.g.
  scheduler outage, upstream never triggered).
- **No logic in the orchestrator that belongs in the transform.** Operators
  orchestrate; SQL/code transforms. Business logic hidden in DAG Python is
  untestable and invisible to lineage.
- **Dependency-aware vs event-driven scheduling:** time-based schedules suit
  source-pull batch; asset/event-driven suits multi-team chains (no
  guessed cron offsets) and arrival-driven loads (file lands → run).
  Event-driven chains still need end-to-end freshness SLAs, since "nothing
  triggered" looks like success.

## dbt-style transformation discipline

(Applies to dbt and equivalents — SQLMesh, etc. dbt note: the Fusion engine is
in preview (preparing for GA) and dbt Core 2.0, built on the Fusion foundation,
is in alpha as of mid-2026; don't hard-require Fusion-only features yet.)

- **Tests on every model that matters:** at minimum `unique` + `not_null` on
  the primary key of every core/mart model, relationship tests on critical
  FKs, accepted-values on enums. Severity-tier them (rules/04).
- **No `SELECT *` crossing model boundaries** (staging enumerates; marts
  list final columns). `*` within a CTE chain of one model is fine.
- **Documentation is part of the model:** description + column docs on all
  mart models; exposures declared for dashboards/consumers so impact
  analysis works.
- One model = one purpose; no 1,500-line mega-models. Use intermediate
  models; materialize hot paths as tables, cheap glue as views/ephemeral.
- **CI runs build + tests on changed models and their downstream**
  (state/defer-based selection) against a non-prod target before merge.
  rules/06 covers deployment.
- Pin package and adapter versions; reproducible builds.

## Audit checklist

- [ ] Every scheduled write is partition-overwrite, MERGE, or full
      rebuild — zero blind appends outside raw landing?
- [ ] Writes atomic per run (no separately-failable delete-then-insert)?
- [ ] All tasks parameterized by logical interval; no `NOW()`-relative
      filters in scheduled code?
- [ ] Watermarks persisted atomically with the data they describe?
- [ ] Late-data policy documented per incremental table?
- [ ] Backfill: arbitrary interval, same code path, bounded parallelism,
      checks still run?
- [ ] DAG edges match actual data dependencies (no cron-offset coupling)?
- [ ] Retries bounded with backoff; timeouts set; final-failure alerts
      routed to an owner?
- [ ] Freshness/SLA alerting on outputs, independent of task success?
- [ ] dbt (or equivalent): key tests on every core/mart model, no
      cross-model `SELECT *`, exposures declared, CI builds changed models
      before merge?