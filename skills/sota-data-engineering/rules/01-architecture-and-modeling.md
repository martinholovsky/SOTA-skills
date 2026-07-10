# 01 — Architecture & Modeling

Decisions in this file are made once per platform, not once per pipeline.
When auditing, mismatches between the platform's stated architecture and what
the code actually does are findings in themselves.

## Size the problem honestly

- **Default to single-node engines below ~100 GB working set.** DuckDB (1.5.x
  as of mid-2026) or Polars on one machine outperforms a Spark cluster on
  cost, latency, and operational burden for the overwhelming majority of
  analytical workloads. "We might grow" is not a reason; migrating a
  well-modeled SQL project later is cheaper than running Spark for 5 GB now.
- **Reach for distributed engines (Spark, Trino, warehouse MPP) when:** the
  working set genuinely exceeds single-node memory+disk economics (TBs per
  query), you need concurrent heavy users on shared compute, or the
  organization already operates the platform and marginal cost is near zero.
- **AUDIT:** A Spark/EMR/Dataproc cluster processing < 50 GB/day with no
  growth trajectory is a MEDIUM cost finding. Quantify: rows/bytes per run vs
  cluster size.

```python
# BAD: 8-node Spark cluster for a 3 GB daily file
df = spark.read.parquet("s3://bucket/daily/")  # 3 GB
df.groupBy("region").agg(...).write.parquet(...)

# GOOD: same job, one process, no cluster
import duckdb
duckdb.sql("""
  COPY (SELECT region, sum(amount) FROM 's3://bucket/daily/*.parquet'
        GROUP BY region)
  TO 's3://bucket/marts/region_daily.parquet'
""")
```

## ELT over ETL — and the exceptions

- **Default: extract-load raw, transform in the warehouse/lakehouse (ELT).**
  Raw data lands unmodified; transformations are versioned SQL run where the
  data lives. This gives replayability (re-derive everything from raw),
  auditability, and lets analysts iterate without re-extraction.
- **Land raw data immutably.** The landing zone is append-only, partitioned
  by load time, retained per policy. Never "fix" raw data — fix the
  transform and rerun.
- **Transform before load (ETL) only when justified:** PII must be
  masked/tokenized before it touches the analytical store (see
  `sota-privacy-compliance`); the source format is pathological (mainframe
  copybooks, multi-GB XML) and pre-parsing is cheaper than in-warehouse
  parsing; volume reduction at the edge materially cuts transfer/storage cost.
- **Never transform-in-flight as an excuse to skip raw retention.** If the
  transform is wrong, untransformed data is gone.

## Warehouse vs lakehouse

Decide by ownership and access patterns, not fashion. Both converge: every
major warehouse reads/writes Iceberg (v3 is GA on Snowflake/Databricks and
Spark 4.0; verify your engine — Trino v3 support still lagged as of writing),
and lakehouse engines speak SQL.

- **Choose a managed warehouse (Snowflake/BigQuery/Redshift-class) when:**
  one team owns the data end-to-end, workloads are SQL-dominant, you want
  zero storage-layer ops, and per-query cost is acceptable.
- **Choose a lakehouse (Iceberg/Delta on object storage) when:** multiple
  engines must read the same tables (Spark + Trino + warehouse + Python),
  data volume makes warehouse storage pricing punitive, you need open-format
  exit options, or ML workloads need direct file access.
- **Hybrid is the 2026 norm:** lakehouse for bronze/silver bulk, warehouse
  (often via external Iceberg tables) for gold/serving. Avoid copying data
  between them when external-table access suffices.
- **Table format choice:** Iceberg if multi-engine neutrality matters (widest
  catalog/engine support, REST catalog standard); Delta if Databricks is the
  center of gravity. Do not run both as peers — pick one as the canonical
  format. DuckLake (1.0+ as of mid-2026) is viable for DuckDB-centric small
  platforms but verify engine/ecosystem fit before committing.
- **AUDIT:** Same dataset copied into both a lake and a warehouse with two
  transform stacks = HIGH (divergence is inevitable). Two table formats with
  no stated rationale = MEDIUM.

## Layered modeling (medallion / staging-core-mart)

Names differ (bronze/silver/gold ≈ raw/staging/core/mart); the contract is
what matters:

- **Raw/bronze:** source-faithful, append-only, never queried by consumers.
  Schema = whatever the source sent, plus load metadata (`_loaded_at`,
  `_source_file`).
- **Staging/silver (1:1 with source entities):** rename to house conventions,
  cast types, deduplicate, no joins, no business logic. One staging model per
  source table. This is where upstream drift breaks loudly.
- **Core/intermediate:** business entities and processes — joins, grain
  changes, business logic, dimensional models live here.
- **Mart/gold:** consumer-shaped, documented, contracted. Dashboards and
  reverse-ETL read only from here.
- **Rules:** consumers never read below mart/core; no layer reads from a
  layer above itself; no model reads raw except its own staging model.
- **AUDIT:** Dashboards querying raw/bronze = HIGH. Business logic in staging
  (joins, CASE-heavy derivations) = MEDIUM. Circular/layer-skipping refs =
  MEDIUM.

```sql
-- BAD staging model: SELECT *, business logic, a join
SELECT *, CASE WHEN o.status IN ('x','y') THEN 'churn' END AS churn_flag
FROM raw.orders o JOIN raw.customers c ON o.cust = c.id;

-- GOOD staging model: enumerate, rename, cast, dedupe. Nothing else.
SELECT
  order_id::bigint            AS order_id,
  cust                        AS customer_id,
  lower(status)               AS order_status,
  created::timestamptz        AS created_at
FROM raw.orders
QUALIFY row_number() OVER (PARTITION BY order_id ORDER BY _loaded_at DESC) = 1
```

## Dimensional modeling still matters

Star schemas remain the right core-layer shape for business processes:
cheap-to-scan fact tables plus reusable conformed dimensions. Columnar
engines did not obsolete them — they made the joins cheap.

- **Facts:** one row per business event at a declared grain. Write the grain
  in the model docs ("one row per order line per day"). Mixed-grain facts are
  a MEDIUM finding. Facts carry foreign keys + numeric measures; degenerate
  dimensions (order number) are fine inline.
- **Dimensions:** conformed and reused. One `dim_customer` shared by all
  facts, not per-mart copies that drift.
- **Surrogate keys:** deterministic hashes of the natural key
  (`md5(source || natural_key)`) beat sequence-generated keys in
  rebuild-from-raw ELT — they're stable across full rebuilds.

### Slowly changing dimensions — pick deliberately

- **Type 1 (overwrite):** default when history of the attribute doesn't
  drive analysis (fixing typos, current email). Cheapest; destroys history.
- **Type 2 (versioned rows with `valid_from`/`valid_to`/`is_current`):** use
  when facts must join to the attribute *as it was at event time* (customer
  tier at purchase, sales territory at booking). Facts join on key + date
  range, or capture the dimension surrogate key at load time.
- **Type 3 / hybrids:** narrow uses (single "previous value" column). Don't
  build elaborate Type 6 machinery on speculation.
- **In ELT, prefer snapshots over hand-rolled SCD merge logic** (dbt
  snapshots or equivalent): capture source state on schedule, derive Type 2
  ranges from snapshots. Hand-written SCD2 MERGEs are a classic source of
  silent corruption — audit their handling of deletes and reruns closely.
- **AUDIT:** Analyses that need point-in-time attributes joined against a
  Type 1 dimension = HIGH (numbers are silently wrong for any historical
  period).

## One Big Table pragmatism

Wide denormalized tables (OBT) are legitimate **mart-layer** artifacts:
build the star in core, then flatten into OBT where a BI tool or consumer
benefits. Columnar storage makes width nearly free to store and scan-prune.

- OBT as the *only* model (no dimensional core underneath) = MEDIUM: every
  new question forces re-deriving logic, and SCD handling becomes ad hoc.
- Never maintain the same metric logic in two OBTs. Derive both from one
  core model.

## Semantic layers

- Define each business metric **once** — in a semantic layer (dbt MetricFlow,
  Cube, LookML-class) if you have multiple BI/consumer surfaces, or simply in
  a single mart model if you have one. The anti-pattern is the same metric
  hand-written in five dashboards.
- A semantic layer is justified by *consumer multiplicity*, not team size.
  One BI tool + one team → mart models are your semantic layer; don't add a
  product.
- **AUDIT:** Grep dashboards/notebooks for re-implemented revenue/active-user
  definitions. Divergent definitions of one metric = HIGH (trust erosion is
  the most expensive data failure).

## Data mesh caution

Data mesh is an **org pattern** (domain ownership, data-as-a-product,
federated governance), not a technology purchase. Apply it only when multiple
domain teams *already* have engineers who can own pipelines end-to-end.

- A central 4-person data team "adopting mesh" is a red flag: it produces
  fragmentation without ownership.
- The durable, steal-able ideas regardless of mesh: producer-owned data
  contracts (rules/04), domain-aligned mart ownership, self-serve platform
  tooling.
- **AUDIT:** "Mesh" with no contracts, no per-domain owners on call for their
  data products, and one shared platform team doing all the work = the label
  is decorative; assess it as a centralized platform.

## Audit checklist

- [ ] Engine size vs data size: any distributed cluster processing < 50
      GB/day without rationale?
- [ ] Raw layer exists, is append-only/immutable, and is not queried by
      consumers or BI tools?
- [ ] Staging models: 1:1 with sources, columns enumerated (no `SELECT *`),
      typed, deduped, no joins/business logic?
- [ ] Layer discipline: no consumer reads below mart/core; no
      layer-skipping or circular references?
- [ ] Each fact table has a documented, single grain?
- [ ] Dimensions conformed (one copy) and SCD strategy explicit per
      dimension; point-in-time analyses backed by Type 2 or snapshots?
- [ ] Surrogate keys stable under full rebuild?
- [ ] Key metrics defined exactly once; no divergent copies in
      dashboards/marts?
- [ ] Single canonical table format; no unjustified duplicate storage of the
      same dataset across lake and warehouse?
- [ ] If "data mesh" is claimed: named domain owners, contracts, and
      operational responsibility actually exist?
