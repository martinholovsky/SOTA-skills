# 06 — Security & Compliance

## Roles & least privilege

### Rule: The application role can do exactly what the application does — nothing more.
Separate roles with separate credentials:
- **Owner/migration role:** owns schemas and tables, runs DDL. Used only by
  the migration pipeline (file 02), never by the app at runtime.
- **App role:** `SELECT/INSERT/UPDATE/DELETE` on exactly the tables it uses;
  no DDL, no ownership. Split further when it pays: a read-only role for
  reporting endpoints, a queue-worker role touching only queue tables.
- **Human roles:** individual logins (audit attribution), read-only by
  default, write access time-boxed/break-glass via group role membership.

```sql
-- Baseline hardening (run once per database):
REVOKE ALL ON DATABASE app FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;        -- default-secure in PG15+
CREATE ROLE app_rw LOGIN PASSWORD '...' NOSUPERUSER NOCREATEDB NOCREATEROLE;
GRANT USAGE ON SCHEMA app TO app_rw;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO app_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE migrator IN SCHEMA app
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_rw;  -- future tables
```
- Without `ALTER DEFAULT PRIVILEGES`, every migration "works in staging,
  permission-denied in prod" — or someone "fixes" it with GRANT ALL. Audit
  for that fix.
- The app connecting as superuser, the table owner, or a BYPASSRLS role:
  CRITICAL (it nullifies RLS and makes SQLi total).
- No `DELETE`/`UPDATE`/`TRUNCATE` grants on append-only tables (audit_log,
  ledgers) for the app role — append-only enforced by grants, not convention.
- Revoke `EXECUTE` on dangerous functions from app roles where present
  (`pg_read_file`, `lo_import`, `dblink`, `COPY ... PROGRAM` is superuser-only
  but verify no `pg_execute_server_program` membership).

### Rule: Per-role guardrails are security controls too.
`statement_timeout`, `idle_in_transaction_session_timeout` (file 04), and
`connection limit` per role bound the blast radius of both bugs and abuse
(a leaked reporting credential shouldn't be able to hold 500 connections).

## Credentials & connection security

### Rule: Database credentials are short-lived, scoped, and never in code or images.
- Connection strings come from a secret manager / workload identity (IAM
  auth, Vault dynamic credentials, cert auth) — not env files in git, not
  baked into images, not in CI logs. Rotation must not require a deploy
  (re-read at connect time).
- One credential per service/role pair; a leaked credential's blast radius =
  that role's grants (see above) — which is why the app role isn't the owner.
- `pg_hba.conf` discipline: explicit `hostssl` lines per network/role; no
  `0.0.0.0/0` rows for write roles; `reject` lines documented. Database
  reachable only from app networks (security groups / private subnets) —
  a publicly listening Postgres is HIGH even with strong auth.
- Audit for credentials in: `docker-compose.yml`, test fixtures, migration
  tool configs, ORM config defaults, and shell history of deploy scripts.

## Audit logging (the security kind)

### Rule: Privileged and write activity is logged in a way the app role can't erase.
- `pgaudit` (or managed equivalent: RDS/Cloud SQL audit flags) for DDL,
  role/grant changes, and writes to sensitive tables; `log_connections` +
  `log_disconnections` for session attribution.
- Logs ship off-host (the DB host compromising its own audit trail must not
  be possible); retention per compliance needs.
- `log_statement = 'all'` is not an audit strategy: it leaks bind-less query
  text (PII), kills performance, and drowns signal. Scope auditing by
  role/object via pgaudit settings.
- Application-level audit tables (file 01) cover business attribution;
  pgaudit covers out-of-band access (psql sessions, compromised creds) — you
  need both.

## Row-Level Security

### Rule: RLS for tenant/ownership isolation enforced in the database; FORCE it; test it.
Full pattern in file 01 (multi-tenancy). Security-specific additions:
- `FORCE ROW LEVEL SECURITY` on every protected table — without it the table
  owner bypasses policies silently.
- Policies must cover **all** commands: a `USING` clause filters
  SELECT/UPDATE/DELETE visibility, but INSERT/UPDATE need `WITH CHECK` or a
  tenant can write rows into another tenant (`CREATE POLICY ... USING (...)
  WITH CHECK (...)`). USING-only policies on writable tables: HIGH.
- Context via `SET LOCAL` only (transaction pooling leaks `SET` — file 04).
  A missing/empty setting must fail closed: `current_setting('app.tenant_id')`
  without the `missing_ok` flag errors — that's the correct default; the
  two-arg form `current_setting(x, true)` returns NULL and the policy must
  then evaluate to false, not true.
- Functions used by policies: `STABLE`, and beware `SECURITY DEFINER`
  functions that read protected tables — they bypass RLS unless they set
  their own context. Views: define with `security_invoker = true` (PG15+) or
  the view owner's privileges bypass RLS under it.
- Automated cross-tenant leak test in CI (file 01) — RLS misconfigurations
  are invisible until breached.

## Encryption

### Rule: In transit — TLS required and verified, both directions.
- Server: `ssl = on`, certificates managed/rotated; `hostssl` rules in
  `pg_hba.conf`, no `host` lines permitting cleartext from app networks;
  `scram-sha-256` auth only (no `md5`, never `trust`/`password`).
- Client: `sslmode=verify-full` — `require` (the common default people stop
  at) does **not** verify the server cert, allowing MITM. `sslmode=require`
  in production connection strings: MEDIUM, HIGH across untrusted networks.
- Redis: TLS + AUTH (`requirepass`/ACLs); Redis bound to a public interface
  without auth is CRITICAL (it's an RCE primitive, not just data exposure).

### Rule: At rest — disk/volume encryption is table stakes; column encryption is for targeted secrets.
- Full-disk/volume encryption (LUKS, EBS/Cloud KMS, TDE-equivalent) protects
  against stolen disks/snapshots — enable always; it does NOT protect against
  SQL-level access.
- **Column-level encryption** (application-side, e.g. AES-GCM via KMS-held
  keys; or pgcrypto with keys NOT stored in the DB) for the small set of
  high-value fields: government IDs, bank/card data (or better: tokenize via
  the payment provider and store only tokens), API keys/OAuth tokens, health
  details. Encrypted columns can't be indexed/searched directly — store a
  separate HMAC/blind-index column when equality lookup is required.
- Key management: keys in KMS/secret manager, rotation procedure documented,
  key-id stored alongside ciphertext for rotation. pgcrypto with the key in a
  table or in the SQL text (it then appears in logs/pg_stat_statements):
  CRITICAL.
- Backups inherit the requirement: encrypted, keys separate from backup
  storage (file 05).

## SQL injection

### Rule: Parameterize everything; injection is structural, not a sanitization problem.
Full injection doctrine lives in the **code-security skill** — defer there
for app-side review. Database-layer obligations:
- All SQL through bind parameters, including in ORMs' raw escape hatches
  (`whereRaw`, `extra()`, `$queryRawUnsafe` — audit these by name).
  Identifiers (column/table names, ORDER BY direction) can't be bound —
  whitelist-map them; never concatenate user input into identifiers.
- Dynamic SQL inside PL/pgSQL: `EXECUTE ... USING $1` + `format()` with
  `%I`/`%L`, never `||` concatenation. `SECURITY DEFINER` functions get extra
  scrutiny: they run with owner privileges and must `SET search_path` to a
  fixed value (search_path hijacking is a real escalation path).
- Defense in depth: least-privilege roles (above) cap what injection can do;
  RLS caps which rows; `statement_timeout` caps exfil-by-batch.
- LIKE inputs: escape `%`/`_` even when parameterized (DoS/filter-bypass, not
  injection, but same review).
- NoSQL/operator injection isn't only a SQL problem — parameterize for every
  engine DN runs. **Redis/Valkey:** never build `EVAL`/`EVALSHA` Lua bodies or
  `KEYS`/command names from untrusted input; pass user data only as `ARGV`/key
  args (the client builds the command as an arg vector, so values stay inert).
  **Qdrant:** assemble filters from a typed allowlist of fields/operators, never
  by templating user JSON into the filter — a client-controlled `must`/`should`
  is a cross-tenant read if it can overwrite the server's tenant filter
  (server-enforced tenant filter is non-negotiable, rules/07).

## PII handling

### Rule: Know where PII lives; minimize, mask, and control access to it.
- Maintain a PII inventory: which tables/columns hold personal data, lawful
  basis, retention period. In schema terms: `COMMENT ON COLUMN users.dob IS
  'PII: ...'` or a tracked data catalog — auditors and deletion jobs both
  need it. Greppable beats tribal knowledge.
- Don't collect what you don't use; don't copy PII into logs,
  `pg_stat_statements` (bind params keep values out of statement text —
  another reason for parameterization), analytics events, or error trackers.
- **Masking for non-production:** production data never lands in dev/staging
  unmasked. Use anonymized restores (masking step in the restore pipeline —
  e.g. PostgreSQL Anonymizer) or synthetic data. Prod-dump-to-laptop is a
  breach in waiting: HIGH.
- Reporting/BI access goes through views that exclude or mask PII columns
  (`SELECT id, left(email, 1) || '***' ...`), granted to the reporting role
  instead of base-table access.
- Replicas, backups, caches, and search indexes (Elasticsearch, Redis,
  vector stores — file 07) are all PII surfaces: retention and deletion must
  reach them too.

## Retention & deletion (GDPR-style)

### Rule: Deletion is a designed, tested data flow — not a DELETE statement someone runs.
- Per-category retention schedule, enforced by automated jobs: partition
  drops for time-series/audit (file 05), batched deletes (file 02) elsewhere.
  Data with no retention policy is data you keep forever and must defend
  forever.
- **Erasure requests (RTBF):** a single entry point that enumerates every
  location for a subject's data — primary tables, audit/history tables,
  outbox/queue payloads, caches (delete keys), search/vector indexes, logs,
  backups. Track request → completion with a deadline (30 days GDPR).
- Backups: industry-accepted approach is documented backup-expiry windows
  (deleted data ages out of backups within N days) plus re-deletion on
  restore; **crypto-shredding** (per-user encryption keys; destroy the key to
  erase the data everywhere at once, including backups) where strict
  erasure-from-backups is required.
- **Anonymization beats deletion** when aggregates must survive: nulling/
  hashing identifying columns while keeping the row is acceptable only if
  genuinely irreversible (no quasi-identifier re-identification).
- Soft delete is not erasure (file 01): `deleted_at` rows still hold the PII.
  The purge job is the compliance control; verify it exists and runs.
- Audit-log immutability vs erasure tension: keep identity out of audit
  payloads (store IDs, not emails/names) so erasing the referenced row
  suffices.

## Audit checklist

- [ ] Separate migration/app/human roles; app role non-superuser, non-owner,
      NOBYPASSRLS, table-scoped grants only; ALTER DEFAULT PRIVILEGES set; no
      GRANT ALL fixes; append-only tables lack UPDATE/DELETE grants.
- [ ] Per-role connection limits and timeouts; individual (not shared) human
      logins; break-glass write access time-boxed.
- [ ] Credentials from secret manager/workload identity, rotatable without
      deploy, one per service; DB not publicly reachable; pg_hba explicit;
      no secrets in repos/images/CI logs.
- [ ] pgaudit (or equivalent) on DDL/roles/sensitive writes, logs shipped
      off-host; no log_statement='all' in prod; connection logging on.
- [ ] RLS enabled AND forced on protected tables; policies have WITH CHECK,
      fail closed on missing context, use SET LOCAL; security_invoker views;
      SECURITY DEFINER functions pin search_path; cross-tenant leak test in CI.
- [ ] TLS enforced server-side (hostssl, scram-sha-256) and verified
      client-side (verify-full); Redis has TLS+auth and no public binding.
- [ ] Disk encryption on; targeted column encryption (KMS keys, never in-DB,
      never in SQL text) for secrets/regulated fields, with blind indexes
      where lookup is needed; encrypted backups with separated keys.
- [ ] No string-built SQL anywhere (including raw ORM escape hatches and
      PL/pgSQL EXECUTE); identifier whitelist for dynamic ORDER BY/columns.
- [ ] PII inventory exists; no PII in logs/error trackers; non-prod
      environments use masked or synthetic data; BI roles see masking views,
      not base tables.
- [ ] Automated retention jobs per data category; RTBF flow enumerates all
      stores (cache, search, vector, queues, logs) with deadline tracking;
      backup expiry or crypto-shredding documented; soft-deleted rows purged.
