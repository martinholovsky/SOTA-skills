# 03 — Query & Index Craft

## Reading EXPLAIN ANALYZE

### Rule: Tune from `EXPLAIN (ANALYZE, BUFFERS)`, never from the query text.
Always include BUFFERS; `shared read` vs `shared hit` tells you whether you're
I/O-bound. What to look for, in priority order:

1. **Estimated vs actual rows off by >10×** → stale/insufficient statistics or
   correlated predicates. Fix: `ANALYZE table`, raise the column's statistics
   target, or `CREATE STATISTICS` (extended stats) on correlated columns.
   Every bad plan starts with a bad estimate — fix estimates before adding
   indexes.
2. **Seq Scan on a large table with a selective filter** → missing index. Seq
   scan on a small table or non-selective predicate (>~5–10% of rows) is
   correct, not a bug.
3. **`Rows Removed by Filter` large on an Index Scan** → index isn't selective
   for this query; needs a composite/partial index matching the full predicate.
4. **Sort with `Sort Method: external merge Disk`** → work_mem too small for
   this sort, or an index should provide the order.
5. **Nested Loop with thousands of iterations of an inner Index Scan** → fine
   if loops are small, disastrous if estimates were wrong (see #1). Hash Join
   expected for large unordered joins.
6. **`Heap Fetches` high on Index Only Scan** → table needs vacuum (visibility
   map stale) — file 05.
7. **`lossy` heap blocks in a Bitmap Heap Scan** → work_mem too small for the
   bitmap.

Use `auto_explain` (log_min_duration) in production to capture real slow plans
— dev-machine plans lie because data volume and cache state differ.
`pg_stat_statements` is the entry point: optimize by total time, not by
single-query latency.

## Index types — pick by operator, not habit

| Type | Use for | Notes |
|---|---|---|
| btree | `=`, `<`, `>`, BETWEEN, ORDER BY, uniqueness | Default. ~99% of indexes. |
| GIN | JSONB `@>`/`?`, arrays `&&`/`@>`, full-text | Slower writes; `fastupdate` batches; `jsonb_path_ops` if only `@>`. |
| GiST | Ranges `&&`, geometry, exclusion constraints, KNN `<->` | The only index for EXCLUDE constraints. |
| BRIN | Huge append-only tables, range filters on naturally ordered cols (`created_at`) | Tiny (MBs for TB tables); useless if physical order ≠ column order. |
| Hash | `=` only | Rarely beats btree; skip unless measured. |
| Partial | `WHERE` clause subsets (live rows, pending jobs) | Query predicate must imply the index predicate verbatim. |
| Covering (`INCLUDE`) | Index-only scans | `(user_id) INCLUDE (email, name)` — payload without widening the key. |
| Expression | `lower(email)`, `(payload->>'k')`, date_trunc | Query must use the exact expression; keeps stats on the expression too. |

```sql
-- Job queue: tiny index over only the rows that matter
CREATE INDEX jobs_pending ON jobs (priority DESC, created_at)
  WHERE status = 'pending';

-- Case-insensitive lookup without citext
CREATE UNIQUE INDEX users_email_lower ON users (lower(email));
-- query MUST write: WHERE lower(email) = lower($1)
```

## Composite index design

### Rule: Column order = equality columns first, then the one range/sort column. ERS.
**E**quality, **R**ange, **S**ort. A btree serves the leftmost prefix; after
the first range/inequality column, remaining columns can't narrow the scan
(they only filter in-index).

```sql
-- Query: WHERE tenant_id = $1 AND status = $2 AND created_at > $3 ORDER BY created_at
-- GOOD: equalities first, range/sort last — one continuous index range
CREATE INDEX ON orders (tenant_id, status, created_at);

-- BAD: range column first — equality columns become in-index filters
CREATE INDEX ON orders (created_at, tenant_id, status);
```
- Among equality columns, order doesn't matter for this query — order them to
  maximize reuse by other queries (most-shared prefix first).
- `(a, b)` makes a separate `(a)` index redundant — drop it. `(b)` alone is
  NOT served (no skip-scan reliance; PG18 adds limited skip scan, don't design
  for it).
- ORDER BY can be served only if the index order matches after all equality
  prefix columns: `(tenant_id, created_at DESC)` serves
  `WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT 20` with zero sort.

### Rule: When indexes hurt — and they always cost something.
Every index taxes every INSERT/UPDATE/DELETE, consumes cache, and blocks HOT
updates if it covers a frequently-updated column (forcing full index-entry
churn). Symptoms of over-indexing: write latency, WAL volume, bloat.
- Audit with `pg_stat_user_indexes.idx_scan = 0` over a representative window
  → drop (after checking it's not a unique/constraint index or replica-only).
- Redundant prefixes (`(a)` next to `(a,b)`) → drop the prefix.
- Don't index low-cardinality columns alone (`status`, booleans) — partial
  index on the rare value instead.
- Bulk loads: drop/recreate non-constraint indexes around the load.

## ORM pitfalls & N+1

### Rule: N+1 is the default ORM behavior; eradicate it explicitly.
```python
# BAD: 1 + N queries (lazy loading per iteration)
for order in Order.objects.filter(user=u):
    print(order.customer.name)

# GOOD: Django
Order.objects.filter(user=u).select_related("customer")          # JOIN
Order.objects.filter(user=u).prefetch_related("items")           # 2nd query, IN (...)
```
```ruby
Order.where(user: u).includes(:customer)   # Rails
```
```ts
prisma.order.findMany({ where: {...}, include: { customer: true } })
```
- Turn on N+1 detection in dev/CI: Rails `strict_loading`, Django
  `django-zeal`/assertNumQueries, Hibernate statistics + `@BatchSize`,
  SQLAlchemy `raiseload('*')` as the default relationship strategy.
- AUDIT: any loop whose body touches a lazy relation or issues a query is a
  MEDIUM (HIGH on hot paths).

### Rule: No `SELECT *` (and no ORM full-entity hydration on hot reads).
`SELECT *` breaks index-only scans, drags TOASTed large columns over the wire,
couples code to column order, and hydrates objects you don't need. Select the
columns the code uses (`only()`, `values_list()`, `select: {...}`, projection
DTOs).

### Rule: Know your ORM's transaction defaults — "implicit" is where the bugs live.
- Autocommit per statement is the typical default — multi-statement business
  operations need an explicit transaction (`transaction.atomic`,
  `prisma.$transaction`, `sequelize.transaction`) or you ship partial writes.
- Inverse trap: frameworks that open a transaction per request and hold it
  across template rendering/external calls — see long-transaction rules,
  file 04.
- `save()` writing every column (not just changed ones) clobbers concurrent
  updates — use changed-field updates or optimistic locking (file 04).
- ORM-generated `IN (...)` lists with thousands of IDs: switch to `= ANY($1)`
  with an array param, or a temp join table.

### Rule: Drop to SQL when the query is the feature.
Reporting, bulk updates (`UPDATE ... FROM`), upserts, window functions,
recursive CTEs: write SQL (with the ORM's raw escape hatch, still
parameterized). An ORM loop of `save()` calls for a bulk update is a MEDIUM
finding: one `UPDATE ... WHERE id = ANY(...)` or `INSERT ... ON CONFLICT`
replaces thousands of round trips.

## Geospatial: the three ways the index is lost

Geometry is one word in the GiST row above and three distinct traps in practice. All
verified against the PostGIS documentation:

- **Pick the type deliberately, and know its units.** `geometry` measures in the **SRID's**
  units — for EPSG:4326 that is *degrees*, so a Cartesian distance over lat/long is
  meaningless. `geography` always measures in **metres** and assumes EPSG:4326. PostGIS's
  own guidance: geographically **compact** data (a city, a county) → `geometry` in a
  projection that suits it; **globally dispersed** data → `geography`. The costs of
  `geography` are real — spherical maths uses trigonometric functions rather than
  Pythagoras, and **fewer functions support it natively**; casting to `geometry` buys
  those functions back at the price of accuracy.
- **`ST_DWithin`, not `ST_Distance`, in `WHERE`.** `ST_DWithin` "includes a bounding box
  comparison that makes use of any indexes that are available"; `ST_Distance` is
  explicitly **non-indexable**, so `WHERE ST_Distance(...) < r` computes a distance for
  every row. Same answer, whole-table scan.
- **A hand-rolled haversine in `WHERE` is the same mistake wearing maths.** Any expression
  the planner cannot match to an index — haversine, a manual bounding box built from
  `cos(lat)`, a distance computed in the `SELECT` and filtered in an outer query — is a
  sequential scan. If you must express it yourself, express it as an **indexable
  predicate** first (`ST_DWithin` or `&&` against an expanded box) and use the exact
  distance only to refine the candidates.
- Mixing SRIDs is an error, not a coercion: `geometry` operations require **both operands
  in the same SRID**. Store the SRID you intend, and constrain it (`geometry(Point,4326)`)
  rather than leaving the column untyped.

**Audit it with `EXPLAIN`, not by reading the SQL** — every trap above produces correct
results and a `Seq Scan`.

## Pagination

### Rule: Keyset (seek) pagination for anything that scrolls deep; OFFSET only for shallow, bounded UIs.
`OFFSET n` reads and discards n rows — page 1000 costs 1000× page 1, and rows
shift between pages under concurrent writes (skipped/duplicated items).

```sql
-- BAD: O(offset), inconsistent under writes
SELECT * FROM orders ORDER BY created_at DESC LIMIT 20 OFFSET 20000;

-- GOOD: keyset — O(1) per page, stable, uses (tenant_id, created_at, id) index
SELECT id, created_at, total_cents FROM orders
WHERE tenant_id = $1
  AND (created_at, id) < ($2, $3)          -- cursor from last row of prev page
ORDER BY created_at DESC, id DESC
LIMIT 20;
```
- Always add the PK as the tiebreaker column — sort keys must be unique or
  pages tear on duplicates.
- Cursor = opaque encoding of the last row's sort key values, not a page number.
- Need total counts? Estimate (`reltuples`, or count with a cap:
  `SELECT count(*) FROM (... LIMIT 1001) t`) — exact counts on big tables are
  a seq scan per page view.

## CTEs, window functions, set-based thinking

### Rule: CTEs are not optimization fences anymore — but know when they materialize.
Since PG12, single-referenced CTEs are inlined. A CTE referenced more than
once, or containing volatile functions, **materializes** (no predicate
pushdown into it). Control explicitly when it matters:
`WITH x AS MATERIALIZED (...)` to cache an expensive subresult used twice;
`AS NOT MATERIALIZED` to force inlining. Data-modifying CTEs
(`WITH deleted AS (DELETE ... RETURNING ...)`) always materialize — they're
the right tool for move-rows-and-log patterns.

### Rule: Window functions over self-joins for per-group rankings/aggregates.
```sql
-- BAD: self-join / correlated subquery per row for "latest order per customer"
SELECT o.* FROM orders o
WHERE o.created_at = (SELECT max(created_at) FROM orders WHERE customer_id = o.customer_id);

-- GOOD: one scan
SELECT * FROM (
  SELECT o.*, row_number() OVER (PARTITION BY customer_id ORDER BY created_at DESC) rn
  FROM orders o) t
WHERE rn = 1;
-- Postgres-specific alternative, often fastest with (customer_id, created_at DESC) index:
SELECT DISTINCT ON (customer_id) * FROM orders ORDER BY customer_id, created_at DESC;
```
Same applies to running totals, gaps-and-islands, deduplication
(`row_number()` + delete rn>1), and "previous row" (`lag()`).

## Prepared statements & plan management

### Rule: Parameterized always (security, file 06); prepared with eyes open.
- Drivers parameterize by default — never interpolate values, including
  ORDER BY directions and LIMIT (whitelist those).
- Prepared statements skip re-parse/re-plan; after 5 executions Postgres may
  switch to a **generic plan** that ignores parameter values — catastrophic
  for skewed data (e.g. one tenant with 90% of rows). Symptoms: query fast in
  psql, slow in app. Fix: `SET plan_cache_mode = force_custom_plan` for that
  statement/role, or restructure.
- PgBouncer transaction mode breaks session-level prepared statements unless
  PgBouncer ≥1.21 with `max_prepared_statements` set — verify (file 04).

## Workload hygiene

- Set `statement_timeout` per role (e.g. 5–30s app, longer for reporting role)
  so one runaway query can't occupy a connection forever.
- `count(*)` is not free; `EXISTS (SELECT 1 ...)` beats `count(*) > 0`.
- Functions in WHERE on the column side (`WHERE date(created_at) = $1`) defeat
  indexes — rewrite as range predicates (`created_at >= $1 AND created_at < $1
  + interval '1 day'`) or use an expression index.
- Implicit type mismatches (`text_col = 123`, numeric vs int in joins) defeat
  indexes — match types exactly.
- `LIKE '%term%'` can't use btree; use trigram GIN (`pg_trgm`) or full-text
  search.

## Audit checklist

- [ ] Geospatial: `grep -rniE 'ST_Distance\\(|haversine|acos\\(sin\\(' --include='*.sql' --include='*.py' .`
      — a distance in a `WHERE` clause is a sequential scan; the indexable form is
      `ST_DWithin`. Confirm with `EXPLAIN`, since every one of these returns the *right
      answer* while scanning the table.
- [ ] Geospatial columns declare their SRID (`geometry(Point,4326)`), and the
      geometry-vs-geography choice matches the data's extent — degrees-as-distance on a
      `geometry` lat/long column is meaningless, not merely imprecise.

- [ ] Slow-query capture exists (pg_stat_statements + auto_explain); tuning
      evidence is EXPLAIN (ANALYZE, BUFFERS), with estimate-vs-actual checked.
- [ ] Every hot query maps to a named index; composite indexes follow
      equality→range/sort order; ORDER BY+LIMIT paths are sort-free.
- [ ] No unused (`idx_scan=0`), redundant-prefix, or lone low-cardinality
      indexes; partial indexes used for skewed predicates (soft delete, queues).
- [ ] JSONB/array/full-text predicates use GIN with the right opclass;
      append-only time filters considered for BRIN; expression indexes match
      query expressions exactly.
- [ ] No N+1: eager loading explicit, N+1 detection wired into dev/CI; no
      query-in-loop patterns.
- [ ] No `SELECT *` on hot paths; projections used; bulk writes are set-based
      SQL, not ORM save-loops.
- [ ] Pagination is keyset with a unique tiebreaker on all deep/scrolling
      lists; no exact `count(*)` per page on large tables.
- [ ] Multi-referenced expensive CTEs deliberately MATERIALIZED (or not);
      per-group latest/rank uses window functions or DISTINCT ON, not
      correlated subqueries.
- [ ] All SQL parameterized; generic-plan risk assessed for skewed params;
      statement_timeout set per role; no index-defeating expressions or type
      mismatches in hot predicates.
