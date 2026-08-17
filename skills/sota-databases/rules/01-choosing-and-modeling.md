# 01 — Choosing the Engine & Modeling the Data

## Engine selection

### Rule: Postgres is the default. Deviation requires a written justification.
Postgres circa 2026 covers relational, document (JSONB), key-value (UNLOGGED
tables, hstore), pub/sub (LISTEN/NOTIFY), job queues (SKIP LOCKED),
time-series (native partitioning, BRIN; TimescaleDB extension), full-text
search, and vectors (pgvector). One engine means one backup story, one
security model, one operational skillset, and real transactions across all of
it. Every additional datastore multiplies failure modes and removes
cross-store transactional consistency.

A second engine is justified only when a concrete, measured requirement
exceeds what Postgres does, not when a category label sounds appealing.

### Rule: Know the genuine win conditions for each alternative.
- **Document DB (MongoDB, DynamoDB doc mode):** wins only when the access
  pattern is truly aggregate-oriented (always read/write whole documents, no
  cross-document joins or transactions) AND scale exceeds a single Postgres
  primary. Schema flexibility alone is not a reason — JSONB gives you that.
- **Key-value (DynamoDB, Redis-as-store):** wins for known-key lookups at
  extreme throughput with single-digit-ms SLOs and simple access patterns
  designed up front. DynamoDB punishes access patterns you didn't model.
- **Columnar/OLAP (ClickHouse, BigQuery, DuckDB):** wins for analytical scans
  over billions of rows. Do not run analytics on the OLTP primary; do not run
  OLTP on a columnar store (no fast point updates). DuckDB for embedded/local
  analytics over files.
- **Time-series (TimescaleDB, ClickHouse, InfluxDB):** wins at high ingest
  rates (>~100k rows/s sustained) with time-bucketed queries, retention, and
  downsampling. Below that, partitioned Postgres tables with BRIN indexes are
  fine — prefer TimescaleDB (stays in Postgres) over a separate system.
- **Dedicated vector DB:** see `07-vector-and-ai.md`. Short version: pgvector
  until >~10–50M vectors or hard multi-tenant isolation/recall requirements.
- **Redis (or Valkey, the BSD-licensed fork):** cache, ephemeral state, rate
  limiting, leaderboards, streams. Not a system of record. See
  `05-reliability-and-scale.md`.
- **Graph DB:** wins only for deep variable-length traversals (4+ hops) as the
  core workload. Friend-of-friend (≤2–3 hops) is a recursive CTE in Postgres.

### Rule: Never introduce a datastore to dodge learning the current one.
"Postgres is slow" is almost always a missing index, a missing partition, an
N+1, or bloat — audit those (files 03, 05) before proposing migration.

## Normalization vs pragmatic denormalization

### Rule: Model in 3NF first; denormalize only with a measured reason.
Start normalized: every fact stored once, updates touch one row, constraints
enforceable. Denormalization is an optimization with a maintenance contract —
every duplicated value needs a documented owner (trigger, application code, or
batch job) that keeps it consistent, and an audit query that detects drift.

Acceptable denormalizations:
- Cached aggregates (`order.total_cents`, `post.comment_count`) maintained by
  trigger or transactionally in the same write path. Always keep the source
  rows so the value is recomputable.
- Snapshot copies where history must not change: `order_items.unit_price_cents`
  copied from `products.price_cents` at order time. This is not denormalization
  — it is correct temporal modeling. Never join to current price for an old order.
- Read-model tables/materialized views for reporting, refreshed on a schedule.

```sql
-- BAD: customer name duplicated onto orders "to avoid a join"
CREATE TABLE orders (id ..., customer_name text, customer_email text, ...);

-- GOOD: join for mutable facts, snapshot immutable-at-time facts
CREATE TABLE orders (id ..., customer_id bigint NOT NULL REFERENCES customers(id),
                     shipping_address jsonb NOT NULL, ...); -- address frozen at order time
```

### Rule: Arrays and JSONB do not exempt you from first normal form for relational data.
If you ever need to query, join, constrain, or update an element individually,
it is a child table, not an array column.

## JSONB usage rules

### Rule: JSONB is for data whose shape you don't control or don't query relationally.
Legitimate: external API payloads, webhook bodies, user-defined custom fields,
sparse per-type attributes, raw event capture. Illegitimate: fields your own
application defines and queries — those are columns.

Hard rules:
- Any JSONB key used in a WHERE clause, JOIN, or ORDER BY of a hot query gets
  promoted to a real (or generated) column:
  ```sql
  ALTER TABLE events ADD COLUMN user_id bigint
    GENERATED ALWAYS AS ((payload->>'user_id')::bigint) STORED;
  CREATE INDEX ON events (user_id);
  ```
- Index JSONB with GIN only for containment (`@>`) / existence queries; use
  `jsonb_path_ops` opclass for `@>`-only workloads (smaller, faster).
- Validate shape with CHECK constraints where structure is required:
  `CHECK (jsonb_typeof(payload->'items') = 'array')`.
- Never store money, foreign keys, or status enums inside JSONB.
- JSONB columns are updated by full-value rewrite; high-frequency partial
  updates to large documents cause write amplification and bloat — split hot
  mutable fields out.

## Primary key strategy

### Rule: Surrogate keys only. Never natural keys.
Emails change, SSNs are PII and get corrected, slugs get renamed, "unique"
business codes collide after the next acquisition. Natural keys also cascade
into every child table and index. Enforce natural uniqueness with a UNIQUE
constraint, not the PK.

```sql
-- BAD
CREATE TABLE users (email text PRIMARY KEY, ...);
-- GOOD
CREATE TABLE users (
  id   bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  email citext NOT NULL UNIQUE,
  ...);
```

### Rule: bigint identity by default; UUIDv7 when IDs leave the system.
- `bigint GENERATED ALWAYS AS IDENTITY`: 8 bytes, perfectly ordered (dense
  btree, good locality), human-debuggable. Default for internal tables.
  Never `serial` (legacy, weaker permissions semantics); never `int` (you will
  hit 2^31 at the worst time).
- **UUIDv7** when: IDs are generated client-side/offline, exposed in URLs or
  APIs (avoids enumeration and count leakage), or rows merge across regions.
  UUIDv7 is time-ordered — it avoids UUIDv4's random-insert btree thrashing
  and WAL bloat. Postgres 18+: native `uuidv7()`; earlier: generate in app or
  via extension. **Never UUIDv4 as PK on a high-insert table.**
- Hybrid pattern is fine: bigint PK internally + `public_id uuid NOT NULL
  UNIQUE DEFAULT uuidv7()` for the API surface.
- Note: UUIDv7 encodes creation time — if creation time is sensitive, that is
  an information leak; use opaque random external IDs in that rare case.

### Rule: Composite PKs only on pure join/child tables.
`(parent_id, child_id)` on a join table is correct and gives you the FK index
for free in one direction (add the reverse-order index explicitly). Anything
with its own lifecycle gets a surrogate key.

## Soft delete

### Rule: Don't default to soft delete. Choose per table, and pay the full cost if you do.
Soft delete (`deleted_at timestamptz`) costs: every query must filter it
(ORMs forget; raw SQL forgets more), unique constraints break (deleted row
still holds the email), FKs still point at "deleted" rows, indexes bloat with
dead-to-the-business rows, and GDPR deletion still requires real deletion.

If you soft delete, all of the following are mandatory:
```sql
ALTER TABLE users ADD COLUMN deleted_at timestamptz; -- NULL = live
-- uniqueness only among live rows:
CREATE UNIQUE INDEX users_email_live ON users (email) WHERE deleted_at IS NULL;
-- hot-path indexes are partial:
CREATE INDEX users_org_live ON users (org_id) WHERE deleted_at IS NULL;
```
- Filtering is enforced centrally (ORM default scope / view / RLS policy), not
  per query.
- A purge job hard-deletes after the retention window.
- Decide FK behavior explicitly: does deleting a user soft-delete their posts?

Alternatives that are usually better: hard delete + audit/history table
(below); move rows to an `archived_*` table; status column when "deleted" is
really a business state (`cancelled`, `disabled`) — don't conflate the two.

## Audit & history tables (temporal patterns)

### Rule: When "who changed what, when" is a requirement, use an append-only audit table written by trigger.
Application-level audit logging misses ad hoc fixes, backfills, and other code
paths. Triggers don't.

```sql
CREATE TABLE audit_log (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  table_name  text NOT NULL,
  row_pk      text NOT NULL,
  action      text NOT NULL CHECK (action IN ('I','U','D')),
  old_row     jsonb,
  new_row     jsonb,
  actor       text NOT NULL DEFAULT current_setting('app.actor', true),
  at          timestamptz NOT NULL DEFAULT now()
) PARTITION BY RANGE (at);
```
- App sets `SET LOCAL app.actor = '<user-id>'` per transaction so the trigger
  can attribute changes.
- Partition by month; retention = drop old partitions (file 05).
- No UPDATE/DELETE grants on audit tables for the app role.

### Rule: For "what did this row look like at time T" queries, use a history table (SCD2-style), not audit-log archaeology.
`valid_from`/`valid_to` ranges with an exclusion constraint
(`EXCLUDE USING gist (id WITH =, validity WITH &&)`) guarantee non-overlap.
Use trigger-maintained history tables or a temporal extension; query with
`WHERE id = $1 AND validity @> $2::timestamptz`. Reserve full event sourcing
for domains that genuinely replay events — it is an architecture, not a table
pattern.

## Ledgers: money and consumable balances

### Rule: The balance is derived from append-only entries, never a column you UPDATE.
A mutable `accounts.balance` records the result of every past write and the
reason for none of them. It drifts silently when one side of a transfer fails,
and a retried `balance = balance - $1` is indistinguishable from a second
payment (file 04: counters are not idempotent). Model the movement instead:

```sql
CREATE TABLE journals (              -- one row per movement
  id          uuid PRIMARY KEY,
  external_id text UNIQUE,           -- the operation this posts for; a retry conflicts
  reason      text NOT NULL,
  posted_at   timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE ledger_entries (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  journal_id  uuid   NOT NULL REFERENCES journals(id),
  account_id  bigint NOT NULL REFERENCES accounts(id),
  amount      bigint NOT NULL,       -- signed minor units: negative debit, positive credit
  currency    text   NOT NULL CHECK (currency ~ '^[A-Z]{3}$')
);
CREATE INDEX ledger_balance ON ledger_entries (account_id, currency) INCLUDE (amount);
```
- **Every movement posts at least two entries summing to zero**, in one
  transaction, under one `journal_id`. That is the whole point: a one-sided
  write becomes an invariant the database rejects, rather than drift you learn
  about months later from a customer.
- Nothing UPDATEs or DELETEs an entry. A mistake is corrected by posting the
  reversing entry, which preserves the history of the mistake.
- `external_id UNIQUE` on the journal, not the entry, is the idempotency key —
  one movement, one external operation, however many legs. NULL repeats freely,
  so internal journals need no synthetic value.
- Balance = `SUM(amount)`. When that gets slow, add a rollup (or a per-period
  closing balance and sum only entries since). The rollup is a **cache** — a job
  that re-derives it from the entries and compares is the cheapest correctness
  alarm you will ever own; a rollup that cannot be re-derived is just the
  mutable column again.

### Rule: Enforce sum-zero in the database, not in the service that writes it.
`CHECK` cannot span rows, so the invariant needs a constraint that runs once the
whole journal is written. In Postgres that is a deferred constraint trigger —
per the [CREATE TRIGGER
reference](https://www.postgresql.org/docs/current/sql-createtrigger.html), a
constraint trigger may only be `AFTER` and `FOR EACH ROW`, and
`DEFERRABLE INITIALLY DEFERRED` moves the check from end-of-statement to
end-of-transaction:

```sql
CREATE CONSTRAINT TRIGGER ledger_balanced
  AFTER INSERT ON ledger_entries
  DEFERRABLE INITIALLY DEFERRED
  FOR EACH ROW EXECUTE FUNCTION assert_journal_sums_to_zero();
-- the function: SUM(amount) per (journal_id, currency) must be 0, else RAISE
```
Enforced in application code only, the invariant holds for the code paths that
remembered it. Group by **currency**: a journal netting to zero across two
currencies is two unbalanced journals: cross-currency movement posts through an
explicit FX account so both sides balance in their own unit.

## Multi-tenancy

### Rule: Default to shared tables with `tenant_id` + Row-Level Security.
Scales to millions of tenants, one migration path, normal pooling.
Requirements (all mandatory — partial implementation is a CRITICAL audit
finding):
```sql
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices FORCE ROW LEVEL SECURITY;  -- applies to table owner too
CREATE POLICY tenant_isolation ON invoices
  USING (tenant_id = current_setting('app.tenant_id')::bigint);
```
- `tenant_id bigint NOT NULL` on every tenant-scoped table, FK to tenants.
- App sets `SET LOCAL app.tenant_id = ...` at transaction start (SET LOCAL,
  not SET — pooled connections leak session settings; see file 04).
- App connects as a non-owner, non-BYPASSRLS role.
- Composite indexes lead with `tenant_id`: `(tenant_id, created_at)`, etc.
- Wrap `current_setting` policies so the planner inlines them; benchmark RLS
  overhead on hot queries (usually negligible with correct indexes).

### Rule: Schema-per-tenant only for few (≲100), large, compliance-isolated tenants.
Per-schema gives stronger isolation, per-tenant restore, and per-tenant
customization — at the cost of N× migrations, catalog bloat at scale,
connection/search_path management, and painful cross-tenant analytics. Past a
few hundred schemas, migrations and `pg_dump` become operational hazards.
Database-per-tenant is the same tradeoff, stronger and more expensive —
reserve for regulated enterprise tenants. Hybrid (RLS for the long tail,
dedicated DB for whale tenants) is a legitimate end state; design IDs and
migrations so a tenant can be extracted.

### Rule: Tenant isolation is tested, not assumed.
Ship an automated test that sets tenant A's context and asserts zero rows
from tenant B across every tenant-scoped table. Missing isolation tests on a
multi-tenant system: HIGH.

## Modeling hygiene (defaults unless justified)

- `timestamptz`, never `timestamp` (naive timestamps corrupt across zones).
  Store UTC; convert at the edge.
- Money: `bigint` minor units (cents) or `numeric(19,4)`. Never `float`/`real`
  for money or anything summed.
- Text: `text` with CHECK length limits where needed; `varchar(255)` is cargo
  cult. `citext` for case-insensitive uniqueness (emails, usernames).
- Enum-like states: `text` + CHECK constraint, or a lookup table. Native
  `ENUM` types complicate value removal/rename in migrations.
- Every table: `created_at timestamptz NOT NULL DEFAULT now()`; `updated_at`
  maintained by trigger if used.
- `NOT NULL` by default; a nullable column is a decision with a meaning
  ("unknown" vs "not applicable") — document it.
- Every FK column gets an index (Postgres does not create one automatically);
  every FK declares `ON DELETE` behavior explicitly (RESTRICT default;
  CASCADE only when the child is meaningless without the parent).
- Booleans that will grow a third state are status columns; model them as
  such the first time.

## Audit checklist

- [ ] Engine choice justified; no second datastore without a written reason
      Postgres can't satisfy; no analytics workload on the OLTP primary.
- [ ] No natural primary keys; no UUIDv4 PKs on high-insert tables; no `int`
      PKs on growing tables; exposed IDs are non-enumerable (UUIDv7/public_id).
- [ ] No mutable business facts duplicated without a documented sync mechanism;
      temporal snapshots (prices, addresses) frozen at event time.
- [ ] No JSONB keys used in hot WHERE/JOIN/ORDER BY without a generated column
      + index; no money/FKs/status inside JSONB.
- [ ] Soft-delete tables have partial unique + partial hot-path indexes,
      centralized filtering, and a purge job; "deleted" is not conflated with
      business states.
- [ ] Audit/history requirements met by trigger-based append-only tables with
      actor attribution and partitioned retention — not ad hoc app logging.
- [ ] Money and consumable balances: append-only entries, at least two per
      movement summing to zero, with sum-zero enforced by a **deferred DB
      constraint** rather than app code; balance derived (or a rollup that a job
      re-derives and compares); corrections posted as reversing entries. A
      mutable `balance` column UPDATEd in place on a money path is CRITICAL —
      `grep -rn "balance *= *balance\|SET balance" migrations/ src/`.
- [ ] Multi-tenant: RLS enabled AND forced on every tenant-scoped table,
      SET LOCAL tenant context, non-BYPASSRLS app role, tenant_id-leading
      indexes, automated cross-tenant isolation test.
- [ ] Types: timestamptz everywhere, no float money, FK columns indexed,
      ON DELETE explicit, NOT NULL default, citext for case-insensitive
      unique text.
