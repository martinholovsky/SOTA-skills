# 04 — Transactions & Concurrency

## Isolation levels — what actually goes wrong

### Rule: Know the anomalies your isolation level permits; default READ COMMITTED is weaker than your intuition.
Postgres READ COMMITTED (the default) takes a fresh snapshot per statement.
Real anomalies you will ship if you don't design for them:

- **Lost update:** two transactions read balance=100, both write
  balance=100−10 → one decrement vanishes. READ COMMITTED allows this.
  Fix: atomic update (`SET balance = balance - 10`), `SELECT ... FOR UPDATE`,
  or optimistic version check — never read-modify-write across statements.
- **Read-check-write races:** "check no row exists, then insert" double-inserts
  under concurrency. Fix: UNIQUE constraint + `ON CONFLICT`, never an
  application-level existence check alone.
- **Write skew (REPEATABLE READ still allows shadows of it; SERIALIZABLE
  doesn't):** two doctors both go off-call because each saw the other on-call.
  Constraints can't express it → SERIALIZABLE or explicit locking on a common
  row.
- REPEATABLE READ in Postgres = snapshot isolation: consistent snapshot per
  transaction, blocks lost updates on the same row (serialization failure
  error 40001 instead), still allows write skew.
- SERIALIZABLE (SSI): true serializability via predicate locking; aborts with
  40001 under contention. Cost: tracking overhead + retry obligation.

### Rule: Choose per workload, not globally.
- Default READ COMMITTED + explicit row locking/constraints/atomic updates
  for OLTP — this is the well-trodden road.
- REPEATABLE READ for multi-statement reads needing one consistent snapshot
  (reports, exports).
- SERIALIZABLE for invariants spanning multiple rows that constraints can't
  enforce (scheduling, budget caps) — only with retry-on-40001 wired in.
  **Using REPEATABLE READ/SERIALIZABLE without 40001 retry logic is a HIGH
  finding: those levels signal conflicts by erroring.**

## Locking

### Rule: Lock rows you're about to update; pick the weakest sufficient mode.
```sql
BEGIN;
SELECT * FROM accounts WHERE id = $1 FOR UPDATE;   -- exclusive row lock
-- compute...
UPDATE accounts SET balance = $2 WHERE id = $1;
COMMIT;
```
- `FOR UPDATE` to update/delete the row; `FOR NO KEY UPDATE` if you won't
  touch key columns (doesn't block others' FK checks — prefer it for balance-
  style updates); `FOR SHARE`/`FOR KEY SHARE` to prevent changes without
  exclusivity.
- Lock in a **consistent global order** (e.g. ascending PK) everywhere:
  `WHERE id IN (...) ORDER BY id FOR UPDATE` — unordered multi-row locking is
  the canonical deadlock factory.
- `FOR UPDATE NOWAIT` to fail fast; `SKIP LOCKED` to take what's available.

### Rule: Job queues in SQL = `FOR UPDATE SKIP LOCKED`. Period.
```sql
WITH job AS (
  SELECT id FROM jobs
  WHERE status = 'pending' AND run_at <= now()
  ORDER BY priority DESC, run_at
  LIMIT 1
  FOR UPDATE SKIP LOCKED            -- workers never block each other
)
UPDATE jobs j SET status = 'running', started_at = now(), attempts = attempts + 1
FROM job WHERE j.id = job.id
RETURNING j.*;
```
Pair with: partial index `(priority DESC, run_at) WHERE status='pending'`
(file 03); a reaper for stuck 'running' jobs (worker died mid-lock — lock
vanished with its connection but status says running); `max_attempts` +
dead-letter status; completion in a separate transaction from the work if the
work has external effects (then the work must be idempotent).
Don't hold the job lock for the duration of long work — claim via status
flip and short transaction instead.

### Rule: Advisory locks for app-level mutual exclusion — with discipline.
`pg_advisory_xact_lock(key)` (transaction-scoped — auto-released, prefer it)
vs `pg_advisory_lock` (session-scoped — leaks on connection reuse through a
pool; if you must, guarantee unlock in finally AND pin the session). Uses:
singleton cron/migration runners, per-entity serialization without locking
rows (`pg_advisory_xact_lock(hashtext('invoice:' || $1))`). Key collisions:
derive from a (namespace int, id int) pair or hashtext — document the keyspace.

### Rule: Optimistic vs pessimistic — choose by contention.
- **Optimistic (version column):** low contention, human-edit workflows,
  long "think time" (never hold a DB lock across user think time):
```sql
UPDATE documents SET body = $1, version = version + 1
WHERE id = $2 AND version = $3;   -- rowcount 0 ⇒ conflict ⇒ reload/merge/409
```
  ORMs: Hibernate `@Version`, ActiveRecord `lock_version`, SQLAlchemy
  `version_id_col`. The check must be in the UPDATE's WHERE, not a prior SELECT.
- **Pessimistic (FOR UPDATE):** hot rows, must-succeed operations (inventory,
  balances), short transactions. Retrying optimistic conflicts on a hot row
  livelocks — lock instead.

## Idempotency & retries

### Rule: Every retryable write path is idempotent — enforced by the database.
Queues redeliver, webhooks re-fire, clients re-POST, your own deadlock-retry
re-executes. Patterns:
```sql
-- Natural idempotency via unique key:
INSERT INTO payments (idempotency_key, amount_cents, ...)
VALUES ($1, $2, ...)
ON CONFLICT (idempotency_key) DO NOTHING
RETURNING id;                      -- no row returned ⇒ fetch existing by key
-- State machines: guarded transitions, not blind writes
UPDATE orders SET status = 'shipped', shipped_at = now()
WHERE id = $1 AND status = 'paid'; -- rowcount 0 ⇒ already done or invalid; don't error blindly
```
- Idempotency keys: client-supplied per logical operation, UNIQUE-constrained,
  stored with the response if the caller needs replay semantics.
- `ON CONFLICT DO UPDATE` only when "overwrite with latest" is genuinely the
  semantics; DO NOTHING + read otherwise.
- Counters are not idempotent (`count = count + 1` double-fires on retry) —
  ledger rows with unique keys, aggregate via SUM or maintained rollup.

### Rule: Retry serialization failures and deadlocks at the transaction level, bounded.
Retry **the whole transaction** (fresh BEGIN, re-read everything) on SQLSTATE
40001 (serialization_failure) and 40P01 (deadlock_detected): 3–5 attempts,
exponential backoff + jitter. Never retry inside the failed transaction; never
retry non-transient errors (constraint violations are answers, not glitches).
Deadlocks at low rates are normal in concurrent systems — log them, retry
them; rising rates mean inconsistent lock ordering (fix that, see above).

## Long transactions — the silent killer

### Rule: No transaction outlives ~1s on the OLTP path; nothing slow happens inside BEGIN.
An open transaction pins its snapshot → vacuum cannot remove any dead tuple
newer than it, **database-wide** → bloat, index degradation, Heap Fetches on
index-only scans; plus it holds every lock it acquired, queuing other work,
and stalls hot standby replicas (or forces query cancellation there).

Forbidden inside a transaction: HTTP/API calls, queue publishes (use the
transactional outbox pattern: write an `outbox` row in the txn, deliver from
a poller), emails, file/S3 I/O, user interaction, unbatched loops, `sleep`.

Guardrails — set them, don't just intend them:
```sql
ALTER ROLE app SET idle_in_transaction_session_timeout = '10s';
ALTER ROLE app SET statement_timeout = '15s';
-- monitor: SELECT pid, now()-xact_start, state, query FROM pg_stat_activity
--          WHERE xact_start < now() - interval '1 minute';
```
`idle in transaction` connections in pg_stat_activity = an app bug (leaked
transaction scope), always. Alert on transaction age (file 05).

### Rule: Savepoints/subtransactions are a scalability trap — audit ORMs that spray them.
Each `SAVEPOINT` creates a subtransaction. Past **64 subtransaction IDs per
backend**, Postgres spills to the shared `pg_subtrans` SLRU — under load this
causes sudden, severe, cluster-wide latency collapse (the infamous
subtrans-SLRU contention), worsened by any long transaction. Sources that
look innocent:
- Django `transaction.atomic` nested blocks (each nested level = savepoint);
  SQLAlchemy `begin_nested()`; Rails nested `transaction(requires_new: true)`.
- "Savepoint per statement" error-recovery modes (PgBouncer-adjacent tools,
  some JDBC/ORM retry wrappers, `psqlrc`-style ON_ERROR_ROLLBACK in scripts).
- Exception-swallowing loops inside a transaction (catch → savepoint rollback
  → continue) iterating hundreds of times.
Rules: keep nesting ≤ 2; never savepoint-per-row in a loop (restructure to
batch validation or per-row transactions); monitor with `pg_stat_slru`
(PG13+) for Subtrans pressure.

### Rule: Don't poll the database for work or state changes when LISTEN/NOTIFY or the queue fits.
Tight polling loops (`SELECT ... every 100ms` × N workers) burn connections
and CPU. Use `LISTEN`/`NOTIFY` to wake workers (note: incompatible with
PgBouncer transaction mode — dedicate a direct connection), or back off
polling intervals adaptively. NOTIFY payloads are advisory only — the worker
still claims work via SKIP LOCKED (notification delivery is not transactional
work assignment, and notifications are lost on disconnect).

## Connection pooling

### Rule: A pooler is mandatory; size pools small.
Each Postgres connection is a process (~MBs, scheduler load). Throughput
peaks at low connection counts: start near `cores × 2 + effective spindles`
(often 20–50 active server connections even for large apps) and load-test;
thousands of direct connections is an anti-pattern. App-side pools
(HikariCP, etc.) cap per-instance; with many app instances/serverless, add a
server-side pooler (PgBouncer / pgcat / RDS Proxy / Supavisor).

Sizing math sanity check: required server connections ≈
`peak_tps × avg_txn_duration_s`. 2000 tps × 10ms transactions = 20 busy
connections. If your pool "needs" 500, the real problem is transaction
duration (see above) or queries needing indexes (file 03) — fix that, don't
raise the pool. Oversized pools convert overload into lock contention,
context switching, and memory pressure instead of a clean queue.

### Diagnosing lock waits (keep this query handy)
```sql
SELECT blocked.pid AS blocked_pid, blocked.query AS blocked_query,
       blocking.pid AS blocking_pid, blocking.query AS blocking_query,
       now() - blocked.query_start AS waiting
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking
  ON blocking.pid = ANY(pg_blocking_pids(blocked.pid))
WHERE blocked.wait_event_type = 'Lock';
```
The blocking query is the bug more often than the blocked one — look for
`idle in transaction` blockers (leaked scope) and DDL without lock_timeout
(file 02).

### Rule: PgBouncer mode dictates what your code may do.
- **session:** 1 client = 1 server connection until disconnect. Safe for all
  features; pools poorly (idle clients hold servers).
- **transaction (the standard choice):** server connection borrowed per
  transaction. **Breaks anything session-stateful:** session-level advisory
  locks, `SET` (use `SET LOCAL`), session prepared statements (need PgBouncer
  ≥1.21 + `max_prepared_statements`, or disable driver-level preparing),
  `LISTEN`, session-lifetime temp tables, cursors WITH HOLD. Audit any of these used with
  transaction pooling: HIGH.
- **Three distinctions PgBouncer's own matrix draws that a blanket finding gets wrong**
  (verified 2026-09-16, [feature matrix](https://www.pgbouncer.org/features.html)):
  `LISTEN` is *Never* supported in transaction mode but **`NOTIFY` is supported**;
  `PRESERVE/DELETE ROWS` temp tables are *Never* supported but **`ON COMMIT DROP` temp
  tables are**; and *protocol-level* prepared plans (what your driver does) are the ones
  `max_prepared_statements` rescues — SQL-level `PREPARE`/`DEALLOCATE` is session state and
  stays unsupported at any version. Condition the finding on the actual operation and the
  pool configuration, or you will report working code as broken.
- **statement:** breaks multi-statement transactions entirely; niche.

Settings that matter: `default_pool_size` (per user+db!), `max_client_conn`,
`server_idle_timeout`, `query_wait_timeout` (bound the queue — fail fast
beats piling up). Monitor `cl_waiting` and pool saturation. Keep a separate,
small pool/role for migrations and admin so app saturation can't block them.

### Rule: Per-tenant/per-request session state must be SET LOCAL inside the transaction.
With transaction pooling, plain `SET app.tenant_id` leaks to the next
borrower — a tenant-isolation breach (CRITICAL). `SET LOCAL` resets at
COMMIT. Verify RLS context (file 01/06) uses SET LOCAL exclusively.
- **SET LOCAL only works inside a transaction.** Outside one, PostgreSQL
  prints a WARNING and ignores it, so a tenant-scoped query then runs with no
  context (or whatever a leaked `SET` left). Open the transaction first, set
  the context, run the work, end it.
- **Every transaction commits or rolls back before its connection returns
  to the pool** — on the error path too (a `finally`/scope guard, not a
  happy-path `commit()`). Do not rely on the pooler to scrub state:
  PgBouncer's `server_reset_query` (`DISCARD ALL`) runs only in session
  mode unless `server_reset_query_always` is set.
- **Test it:** force a pool of one connection, run tenant A's request, then
  tenant B's on the same connection, and assert B sees neither A's rows nor
  A's context. Measured on PostgreSQL 17: after a committed `SET LOCAL`,
  `current_setting('app.tenant_id', true)` returns an empty string (not NULL)
  on that session; after a plain `SET` it still returns A's value — the
  test must fail on the second case.
OWASP: Multi Tenant Security cheat sheet.

## Audit checklist

- [ ] No read-modify-write across statements without FOR UPDATE / atomic
      SET expr / optimistic version in the UPDATE's WHERE; no app-level
      uniqueness checks standing in for UNIQUE constraints.
- [ ] REPEATABLE READ / SERIALIZABLE usage paired with whole-transaction
      retry on 40001; deadlock (40P01) retry bounded with backoff; multi-row
      locks acquired in consistent order.
- [ ] DB-backed job queues use FOR UPDATE SKIP LOCKED + partial index +
      stuck-job reaper + attempt caps; no lock held across long work.
- [ ] Advisory locks transaction-scoped (xact variants) or provably released;
      keyspace documented; none session-scoped behind transaction pooling.
- [ ] All retryable writes (webhooks, queue consumers, POSTs) idempotent via
      unique keys / guarded state transitions; no bare counters on retry paths.
- [ ] No network I/O, user waits, or unbatched loops inside transactions;
      outbox pattern for txn-coupled messaging; idle_in_transaction_session_timeout
      and statement_timeout set per role; alerting on old transactions.
- [ ] Pooler present; pool sizes load-tested and small; PgBouncer mode known
      and code audited against its restrictions (SET LOCAL only, prepared
      statements compatible, no session advisory locks/LISTEN in txn mode).
- [ ] Separate admin/migration pool; query_wait_timeout bounds queueing.
- [ ] CRITICAL: tenant context never outlives its transaction — every
      transaction ends (commit or rollback, error path included) before the
      connection is released, and a one-connection pool test proves tenant
      B cannot see tenant A's context. Probe for session-level context:
      ``grep -rniE "(^|[\"'\`(])[[:space:]]*SET[[:space:]]+(SESSION[[:space:]]+)?[[:alnum:]_]+\.[[:alnum:]_]+[[:space:]]*(=|TO)|set_config\([^,]+,[^,]+,[[:space:]]*false" .``
      (a MySQL multi-line `UPDATE ... SET alias.col` can hit; discard it).
- [ ] No deep/looped savepoint usage (nested atomic blocks, per-row error
      recovery); subtransaction SLRU pressure monitored on busy systems.
- [ ] Workers wake via LISTEN/NOTIFY or adaptive backoff (not tight polling),
      and still claim work via SKIP LOCKED, not via notification payloads.
