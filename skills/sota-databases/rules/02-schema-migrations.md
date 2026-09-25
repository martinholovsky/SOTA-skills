# 02 — Schema Evolution & Migrations

## Core invariants

### Rule: A migration must never break the currently deployed application.
During any deploy there is a window where old code runs against the new schema
(and, with rollbacks, new code against the old schema). Every migration must
be compatible with both adjacent application versions. This forces
**expand/contract**:

1. **Expand** — additive, backward-compatible change (new column, new table,
   new index, new nullable constraint). Deploy.
2. **Migrate code** — application writes both/new, reads with fallback. Deploy.
3. **Backfill** — batched data migration, separate from DDL.
4. **Contract** — remove the old column/table/code path. Separate deploy,
   only after verifying nothing reads the old shape.

Each phase is its own migration + deploy. Collapsing them into one "rename
column" migration is a HIGH audit finding regardless of table size — table
size changes; the pattern shouldn't.

```sql
-- BAD: breaks old code instantly, rewrites nothing but kills every in-flight query plan
ALTER TABLE users RENAME COLUMN username TO handle;

-- GOOD: expand/contract rename
-- M1 (expand):    ALTER TABLE users ADD COLUMN handle text;
--                 + trigger or dual-write in app keeping both in sync
-- M2 (backfill):  batched UPDATE ... WHERE handle IS NULL
-- M3 (validate):  ALTER TABLE users ADD CONSTRAINT handle_nn CHECK (handle IS NOT NULL) NOT VALID;
--                 ALTER TABLE users VALIDATE CONSTRAINT handle_nn;
-- M4 (contract):  ALTER TABLE users DROP COLUMN username;   -- after code stops reading it
```

### Rule: Reversible, or the irreversibility is documented in the migration itself.
Every migration has a `down`/rollback, OR an explicit comment: why it cannot
be reversed and what the recovery plan is (restore from PITR, re-run backfill,
etc.). `down` methods that were never run are theater — what actually matters:
- Destructive migrations (DROP COLUMN/TABLE, lossy type change) are deployed
  only after a release where nothing references the object, so "rollback" of
  the app never needs the schema rolled back.
- Data-destroying migrations note the backup/PITR point to restore from.

### Rule: Migrations are immutable once merged.
Never edit an applied migration; write a new one. Checksums (Flyway/most tools
enforce this) catch drift. Editing history breaks every environment that
already ran it.

### Rule: One logical change per migration; DDL and large data changes never share a transaction.
Migration tools wrap files in a transaction (good for atomic DDL in Postgres),
but a million-row UPDATE inside that transaction holds locks and bloats for
its whole duration. DDL migration files stay tiny; backfills are separate,
batched, and non-transactional as a whole (see Backfills).

## Lock-aware DDL on hot tables

### Rule: Know which DDL blocks, and never let it queue behind traffic.
Postgres lock facts that decide everything:
- Any `ALTER TABLE` takes ACCESS EXCLUSIVE — it blocks all reads/writes AND,
  worse, **queues behind any long-running query**, and everything else queues
  behind it. A 5ms ALTER behind a 10-minute report = 10 minutes of full outage.
- Therefore every DDL migration sets a lock timeout and retries:
```sql
SET lock_timeout = '3s';
SET statement_timeout = '15s';  -- belt and suspenders for the DDL itself
-- migration runner retries on lock_timeout failure (with backoff)
```
Missing `lock_timeout` in migrations on a production system: HIGH.

### Rule: Fast vs rewrite — know the table per operation (Postgres 14+).
**Metadata-only (fast, still needs lock_timeout):** ADD COLUMN (nullable, or
NOT NULL with constant default — default stored lazily since PG11), DROP
COLUMN, SET/DROP DEFAULT, most type widenings that are binary-coercible
(`varchar(50)→text`, `varchar(n)→varchar(m>n)`), `numeric` precision increase.

**Full table rewrite or scan (dangerous on hot tables — use the safe pattern):**
- `ALTER COLUMN TYPE` (non-coercible, e.g. `int→bigint`): rewrites table +
  indexes. Safe pattern: new column → dual-write trigger → backfill → swap
  names in one fast transaction → drop old.
- `SET NOT NULL` (scans): add `CHECK (col IS NOT NULL) NOT VALID`, then
  `VALIDATE CONSTRAINT` (takes only SHARE UPDATE EXCLUSIVE), then `SET NOT
  NULL` (PG12+ uses the validated check to skip the scan), then drop the check.
- `ADD FOREIGN KEY` / `ADD CHECK`: always `NOT VALID` first, `VALIDATE
  CONSTRAINT` in a later migration.
- `ADD COLUMN ... DEFAULT <volatile fn>` (e.g. `uuidv7()`): rewrites. Add
  nullable, backfill, then set default for new rows.

### Rule: Indexes on live tables: CONCURRENTLY, outside a transaction, check for invalid leftovers.
```sql
-- BAD on any table with traffic: blocks writes for the whole build
CREATE INDEX orders_user_idx ON orders (user_id);

-- GOOD
CREATE INDEX CONCURRENTLY orders_user_idx ON orders (user_id);
DROP INDEX CONCURRENTLY old_idx;
```
- CONCURRENTLY cannot run inside a transaction — mark the migration
  non-transactional (`disable_ddl_transaction!`, `-- migrate:no-transaction`,
  `atomic = False`, tool-equivalent).
- A failed CONCURRENTLY build leaves an INVALID index that still costs write
  overhead: detect (`pg_index.indisvalid = false`) and drop+rebuild. Make the
  migration idempotent: drop invalid index if present, then create.
- Unique constraints on live tables: `CREATE UNIQUE INDEX CONCURRENTLY` then
  `ALTER TABLE ... ADD CONSTRAINT ... UNIQUE USING INDEX ...`.

### Worked example: `int` → `bigint` PK on a hot table (the full sequence)
The most common forced rewrite. Memorize the shape; it generalizes to any
type change.
```sql
-- M1 (expand): new column, synced going forward
ALTER TABLE orders ADD COLUMN id_new bigint;            -- metadata-only
CREATE OR REPLACE FUNCTION orders_sync_id() RETURNS trigger AS $$
BEGIN NEW.id_new := NEW.id; RETURN NEW; END $$ LANGUAGE plpgsql;
CREATE TRIGGER orders_sync_id BEFORE INSERT OR UPDATE ON orders
  FOR EACH ROW EXECUTE FUNCTION orders_sync_id();

-- M2 (backfill, script not migration): batched
UPDATE orders SET id_new = id
WHERE id > $last AND id <= $last + 10000 AND id_new IS NULL;

-- M3: enforce + index, all lock-friendly
ALTER TABLE orders ADD CONSTRAINT id_new_nn CHECK (id_new IS NOT NULL) NOT VALID;
ALTER TABLE orders VALIDATE CONSTRAINT id_new_nn;
CREATE UNIQUE INDEX CONCURRENTLY orders_id_new_key ON orders (id_new);

-- M4 (swap, one fast transaction with lock_timeout + retry):
BEGIN;
SET LOCAL lock_timeout = '3s';
ALTER TABLE orders DROP CONSTRAINT orders_pkey;
ALTER TABLE orders ADD CONSTRAINT orders_pkey PRIMARY KEY USING INDEX orders_id_new_key;
ALTER TABLE orders ALTER COLUMN id_new SET NOT NULL;   -- uses validated check
ALTER TABLE orders RENAME COLUMN id TO id_old;
ALTER TABLE orders RENAME COLUMN id_new TO id;
ALTER TABLE orders ALTER COLUMN id ADD GENERATED ALWAYS AS IDENTITY
  (START WITH <max_id + safety_gap>);
DROP TRIGGER orders_sync_id ON orders;
COMMIT;
-- M5 (contract, after soak): drop id_old; repeat pattern for every FK column
-- referencing orders.id (each FK column is its own expand/contract cycle).
```
Sequence/identity restart value must exceed max(id) plus headroom for rows
inserted during the swap window. FKs referencing the column make this a
multi-table project — schedule it before the int is 50% exhausted (alert on
sequence exhaustion: `last_value / 2147483647`).

## Backfills

### Rule: Backfills are batched, keyset-driven, throttled, and resumable.
```sql
-- BAD: one statement, hours of lock/bloat/replication lag
UPDATE events SET tenant_id = u.tenant_id FROM users u WHERE events.user_id = u.id;

-- GOOD: driver loop (app/script), each batch its own transaction
UPDATE events SET tenant_id = u.tenant_id
FROM users u
WHERE events.user_id = u.id
  AND events.id > $last_id AND events.id <= $last_id + 10000
  AND events.tenant_id IS NULL;          -- idempotent: re-runnable from anywhere
-- commit; record $last_id; sleep adaptively (watch replication lag); repeat
```
- Batch by PK range (keyset), not OFFSET.
- Idempotent predicate so a crashed backfill resumes safely.
- Monitor replica lag and bloat during the run; pause when lag grows.
- Run as a script/job with progress logging — not as a "migration" that a
  deploy pipeline times out on.

## Zero-downtime cheat sheet

| Change | Safe pattern |
|---|---|
| Add column | ADD COLUMN nullable or with constant default |
| Drop column | Stop reading in code → deploy → DROP COLUMN (lock_timeout) |
| Rename column/table | Expand/contract dual-write (never RENAME on hot path); views can bridge reads |
| Change type | New column + trigger dual-write + backfill + swap |
| Add NOT NULL | CHECK NOT VALID → VALIDATE → SET NOT NULL |
| Add FK/CHECK | NOT VALID → VALIDATE CONSTRAINT |
| Add index | CREATE INDEX CONCURRENTLY (non-transactional migration) |
| Add unique | UNIQUE INDEX CONCURRENTLY → ADD CONSTRAINT USING INDEX |
| Drop default / change default | Safe, metadata only |
| Partitioning an existing table | New partitioned table + dual-write + backfill + swap, or pg_partman/logical replication route |
| New required column on insert-heavy table | Add nullable + app writes it → backfill → NOT NULL via check pattern |

## Migration tooling & testing

### Rule: Migrations live in version control, run automatically, and exactly one tool owns the schema.
- One migration framework (Flyway, dbmate, Alembic, Rails/AR, Prisma, golang-
  migrate, Atlas...) — never hand-applied DDL in prod. Any schema drift
  between environments is a HIGH finding; verify with a schema diff (e.g.
  `migra`, `atlas schema diff`) in CI.
- Migrations run in the deploy pipeline before (expand) or after (contract)
  the code rollout — the ordering is part of the migration's design notes.
- A linter in CI (e.g. squawk for Postgres) catches blocking DDL patterns
  automatically.

### Rule: Test migrations against realistic data, both directions, before prod.
Minimum bar:
- CI applies all migrations to a clean DB **and** to a schema snapshot of
  production (structure + statistically similar volume for hot tables).
- Time the migration against prod-sized data; anything that scales with table
  size gets reviewed for the lock-aware pattern above.
- Staging runs the migration against a recent prod restore (this doubles as
  your backup-restore test — file 05).
- For risky migrations: rehearse the rollback path explicitly.
- Multi-tenant schemas: after migrating, run the catalog tenancy gate
  (file 06, Row-Level Security) so a new table ships classified and, if
  tenant-scoped, with RLS forced and a policy.

### Rule: Migrations are forward-compatible with concurrent deploys.
If two app instances deploy at once, or a migration runs while old pods serve
traffic, nothing may corrupt. Migration lock (tools provide one — e.g.
advisory-lock based) prevents concurrent migration runs; verify it's enabled.

### Rule: Seed/reference data changes are migrations too — and idempotent.
`INSERT ... ON CONFLICT DO UPDATE` for lookup rows. Never assume an empty
table; never duplicate rows on re-run.

### Rule: Deploy ordering is part of the migration's contract — write it down.
- **Expand migrations** run before the code that uses them ships.
- **Contract migrations** run after the code that stopped using the old shape
  is fully rolled out everywhere (all regions, all canaries, mobile clients
  if they query directly via an API contract change).
- If a migration and a code change must ship together atomically, the design
  is wrong — split it until each step is independently safe.
- Feature flags don't change this: schema must support both flag states.

## MySQL differences (when the project is MySQL/MariaDB)

The expand/contract and lock-timeout doctrines are identical; mechanics differ:
- No transactional DDL: a failed multi-statement migration leaves a half-
  applied state — one DDL statement per migration file, idempotent re-runs.
- `ALGORITHM=INSTANT` (8.0+) covers ADD/DROP COLUMN and more; always specify
  `ALGORITHM=INSTANT|INPLACE, LOCK=NONE` explicitly so the migration **fails
  loudly** instead of silently rewriting the table.
- For real rewrites on hot tables use `gh-ost` or `pt-online-schema-change`
  (shadow-table + trailing changelog), not naive ALTER.
- Adding an index is online (INPLACE) but still I/O-heavy — off-peak.
- Foreign keys + gh-ost don't mix well; check tool constraints first.

## ORM-specific traps

- **Prisma/Django/Rails auto-generated migrations:** review the generated SQL,
  not the DSL. Auto-generated `ALTER COLUMN TYPE`, implicit index drops on
  unique changes, and non-CONCURRENT index creation are common. Print SQL
  (`prisma migrate diff`, `sqlmigrate`, `rails db:migrate:status` + manual
  inspection) in code review.
- **Django:** set `atomic = False` for CONCURRENTLY; beware `AlterField`
  silently rewriting; use `SeparateDatabaseAndState` for swap tricks.
- **Rails:** `strong_migrations` gem in every Rails project, not optional.
- **Alembic:** autogenerate misses CHECK constraints and some index changes —
  diff against the real schema periodically.

## Audit checklist

- [ ] No migration breaks the previously deployed app version; renames/type
      changes/drops follow expand → migrate code → backfill → contract across
      separate deploys.
- [ ] Every migration reversible or carries an explicit irreversibility note
      with recovery plan; applied migrations never edited.
- [ ] All DDL migrations set `lock_timeout` (and the runner retries); no
      ACCESS EXCLUSIVE operation can queue behind long queries unbounded.
- [ ] No table-rewrite DDL (type change, volatile default, naive SET NOT
      NULL) on hot tables; NOT VALID → VALIDATE used for new constraints.
- [ ] All index builds on live tables use CONCURRENTLY in non-transactional
      migrations; no INVALID indexes present in the catalog.
- [ ] Backfills batched by keyset, idempotent, resumable, throttled against
      replication lag; never inside the DDL migration's transaction.
- [ ] One migration tool owns the schema; CI detects drift vs prod; migration
      linter (squawk/strong_migrations) wired in.
- [ ] Migrations tested against prod-sized/prod-shaped data and timed; risky
      rollbacks rehearsed; concurrent-migration lock enabled.
- [ ] ORM-generated migrations reviewed as SQL, not as DSL.
