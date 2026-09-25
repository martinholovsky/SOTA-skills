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
- **Links to other databases cross a trust boundary** — Postgres
  `postgres_fdw`/`dblink`, SQL Server linked servers, Oracle database links.
  None by default; each one needs a written reason. When one exists, it logs
  in to the remote side as a dedicated account holding only what the link
  reads, never a superuser or `sa`. Map it per local role: a Postgres
  `CREATE USER MAPPING FOR PUBLIC` is used by any role with no mapping of its
  own, and `sp_addlinkedsrvlogin` with `@locallogin` left NULL covers every
  local login. Postgres hides mapping passwords in `pg_user_mappings` from
  other roles, but only a superuser may set `password_required 'false'` —
  never on a PUBLIC mapping. Keep link credentials out of readable places
  (plain tables, SQL files in the repo, connection strings in view bodies).
  OWASP: Database Security cheat sheet.
- **Alternative model: an API-only role.** When the data layer is its own
  security boundary (several apps share it, or every write must go through
  reviewed code), the app role gets `EXECUTE` on named functions or
  procedures and `SELECT` on purpose-built views — and **no** grant on any
  base table. Postgres grants `EXECUTE` on every new function to `PUBLIC`, so
  revoke it (`ALTER DEFAULT PRIVILEGES FOR ROLE <owner> REVOKE EXECUTE ON
  FUNCTIONS FROM PUBLIC` — it cannot be scoped `IN SCHEMA`) and grant by
  name. Functions are `SECURITY DEFINER`, owned by a non-login role, with a
  pinned `search_path` (SQL injection section). Views and definer functions
  run with their owner's rights, so row rules live in their bodies. SQL
  Server: `GRANT EXECUTE` on the procedures' schema; the app login is never
  in `db_owner` (it can reconfigure and drop the database). Prefer it over
  table grants + RLS when the operation set is small and stable and an
  injected query must not reach arbitrary rows; each new query then costs a
  migration. Verified on PostgreSQL 17 (2026-09-25): no base-table grant
  must show for the app role —
  `SELECT c.oid::regclass FROM pg_class c WHERE c.relkind IN ('r','p') AND
  c.relnamespace::regnamespace::text NOT IN ('pg_catalog','information_schema')
  AND has_table_privilege('app_exec', c.oid, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE');`
  OWASP: Database Security cheat sheet; Go-SCP (stored procedures); SQL
  Injection Prevention cheat sheet; Secure Coding Practices QRG.

### Rule: Per-role guardrails are security controls too.
`statement_timeout`, `idle_in_transaction_session_timeout` (file 04), and
`connection limit` per role bound the blast radius of both bugs and abuse
(a leaked reporting credential shouldn't be able to hold 500 connections).

## Server baseline (install time)

### Rule: No vendor default survives install — accounts, passwords, sample and test databases.
The general rule (every deployed product, not only databases) is in
`sota-code-security` rules/02 §8; the database-specific steps are:
- **Make hardening a scripted install step**, not a memory. Some engines ship
  one: `mysql_secure_installation` sets the root password, removes anonymous
  accounts, removes remote-capable root accounts and drops the `test` database
  that anonymous users can reach. Where an engine has none, the provisioning
  code carries the equivalent SQL.
- **Bootstrap superuser:** set its password at init (`initdb --pwfile`) and
  never leave `trust` in place — `trust` is initdb's documented default for
  local connections. Use it for break-glass only; the app never connects as it.
- **Containers skip the script.** The official MySQL image creates
  `root@'%'` (remote-capable) unless `MYSQL_ROOT_HOST` narrows it. It and the
  MariaDB image enable an empty root password when
  `MYSQL_ALLOW_EMPTY_PASSWORD` / `MARIADB_ALLOW_EMPTY_ROOT_PASSWORD` holds
  **any non-empty value** (`=no` included — the entrypoints only test `-n`).
  Postgres' `POSTGRES_HOST_AUTH_METHOD=trust` disables passwords for every
  host. Any of these outside a throwaway local setup: HIGH.
- **Drop, don't just ignore:** sample schemas, demo databases and vendor
  default accounts the app does not use. MongoDB runs with
  `security.authorization` **disabled** by default — enable it at install.
- **Prefer integrated or certificate auth over passwords where available**:
  SQL Server's Windows-only mode leaves the `sa` login disabled, and Microsoft
  says to use Windows authentication when possible; choose mixed mode only
  for a documented need, then keep `sa` disabled or renamed.
- **Audit against an inventory, not a memory:** list the catalog's login
  roles and databases (`pg_roles WHERE rolcanlogin`, `pg_database`; MySQL
  `mysql.user`, `SHOW DATABASES`) and diff them against the expected list
  kept in the repo. Any extra login, anonymous (`user=''`) row, or `test`/
  sample database is a finding.
OWASP: Database Security cheat sheet; Go-SCP (database security); NoSQL
Security cheat sheet; Secure Coding Practices QRG.

### Rule: Minimal feature surface — in-server code execution and extras are off unless documented.
The per-engine examples elsewhere (SurrealDB `--allow-scripting`, rules/08;
Redis `EVAL`, below; dangerous Postgres functions, above) are one rule:
deny by default, enable with a written reason.
- **Extensions and languages:** install only what the schema uses; keep an
  expected list and diff `pg_extension` against it. Untrusted procedural
  languages (`plpython3u`, `plperlu`) run with the database server's OS
  rights — only superusers may create functions in them, and a need for one
  is a design review item. Trusted extensions (PG13+) are installable by
  anyone with `CREATE` on the database, so that grant is itself surface.
- **Hosted runtimes and shell escapes:** SQL Server `clr enabled` and
  `xp_cmdshell` stay 0 (`xp_cmdshell` is off on new installs; turn it on
  only for the task that needs it). MongoDB `security.javascriptEnabled`
  defaults to **true** — set it false unless `$where`, `$function`,
  `$accumulator` or `mapReduce` are used (all deprecated server-side JS).
- **Admin commands and auxiliary services:** Redis `enable-debug-command` and
  `enable-module-command` default to `no` — keep them there (`local` is
  loopback-only, `yes` is anyone). Disable discovery listeners you do not
  need (e.g. SQL Server Browser on UDP 1434 when instances use fixed ports).
- **Drop unused stored procedures and utility packages** rather than
  leaving them for an attacker's SQLi to find.
OWASP: Database Security cheat sheet; Go-SCP (database security); NoSQL
Security cheat sheet; Secure Coding Practices QRG.

### Rule: Self-managed servers run as a dedicated unprivileged OS account on a baseline-hardened host.
Anything that turns into OS execution (an untrusted PL language, `COPY ...
PROGRAM`, `xp_cmdshell`, an engine CVE) runs as the server's OS user, so
that user decides the blast radius.
- A dedicated account per engine — never root/SYSTEM, never a shared
  account such as `nobody`. The PostgreSQL docs add that it should own only
  the data directory, **not** the server binaries, so a compromised server
  cannot rewrite them. MySQL's docs likewise say not to run `mysqld` as root.
- Containers: the image's own non-root user, not `user: root`/`0`.
- systemd units: `User=` set to that account plus the sandboxing directives in
  `sota-sandboxing` rules/02 R7.4 (check with `systemd-analyze security`).
- Harden the host from a published baseline (the CIS Benchmark for the OS,
  and for the engine where one exists) or the vendor's hardening guide, and
  keep the deviations in the repo. Managed services cover this layer for you.
OWASP: Database Security cheat sheet; SQL Injection Prevention cheat sheet.

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
- **Bind the listener narrowly, for every engine.** Defaults differ:
  Postgres `listen_addresses` defaults to `localhost` and MongoDB binds to
  localhost, but MySQL `bind_address` defaults to `*`, and a `redis-server`
  started without the shipped `redis.conf` (which sets `bind 127.0.0.1 -::1`)
  listens on every interface. Set a private interface explicitly. When the app
  runs on the same host, turn TCP off: Postgres `listen_addresses = ''`
  (Unix socket only), MySQL `skip_networking` (socket, or named pipe/shared
  memory on Windows).
- **Superuser logins are local-only.** Postgres: `local all postgres peer`
  plus a `host`/`hostssl ... postgres ... reject` line; MySQL: `root` exists
  only `@'localhost'`. Remote administration goes through the break-glass
  path (bastion, time-boxed role), not a network login for the superuser.
  MySQL `admin_address` (no default) puts admin connections on a dedicated
  interface.
- **Admin consoles are part of the attack surface.** Web UIs and management
  endpoints (pgAdmin, Mongo Express, RedisInsight, vendor consoles) get the
  same TLS, authentication and private-network rule as the driver port —
  an unauthenticated console on a reachable port is the database. HIGH.
  OWASP: Database Security cheat sheet; Go-SCP (database security); NoSQL
  Security cheat sheet.
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
- **Verify the deployed catalog, not the migration source.** A CI/deploy
  check connects to the migrated database and fails when (a) the request role
  has `rolsuper` or `rolbypassrls` in `pg_roles`, or (b) any table lacks a
  tenancy classification, or a table classified tenant-scoped lacks
  `relrowsecurity`, `relforcerowsecurity` or a `pg_policies` row. Classify
  every table as `tenant`, `shared` or `isolated` in the schema itself (e.g. a
  `COMMENT ON TABLE ... IS 'tenancy: tenant'`) so a new table with no
  classification fails the gate (wired into migrations, file 02):
```sql
SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE c.relkind IN ('r','p') AND n.nspname = 'app'
  AND (substring(obj_description(c.oid,'pg_class') FROM 'tenancy: (\w+)') IS NULL
    OR (substring(obj_description(c.oid,'pg_class') FROM 'tenancy: (\w+)') = 'tenant'
        AND NOT (c.relrowsecurity AND c.relforcerowsecurity AND EXISTS (
          SELECT 1 FROM pg_policies p
          WHERE p.schemaname = n.nspname AND p.tablename = c.relname))));
-- any row = gate fails (checked 2026-09-25 on PostgreSQL 17)
```
  OWASP: Multi Tenant Security cheat sheet.

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

### Rule: Embedded SQLite — zero deleted content, keep temp data in memory, create files 0600.
An embedded database has no server account between the file and every other
local user, so the file's own settings are the control (measured 2026-09-25,
SQLite 3.53.4, umask 022):
- `PRAGMA secure_delete = ON` per connection (default off unless built with
  `SQLITE_SECURE_DELETE`): deleted rows are overwritten with zeros rather than
  left in free pages. `FAST` still leaves traces on freelist pages, and FTS
  shadow tables can keep deleted text either way — `VACUUM` after bulk erasure.
- `PRAGMA temp_store = MEMORY` keeps temp tables and indices out of temp
  files. A build with `SQLITE_TEMP_STORE=0` ignores the pragma (always file);
  `=3` forces memory.
- The database is created `0644` (compiled default, minus umask) and its
  `-wal`, `-shm` and `-journal` files copy the database file's mode. Create it
  with a `0077` umask or `chmod 0600` before first use, in a directory only the
  service account can read.
OWASP: C-Based Toolchain Hardening cheat sheet.

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
  engine in use. **Redis/Valkey:** never build `EVAL`/`EVALSHA` Lua bodies or
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
- [ ] HIGH: under an API-only model the app role holds no base-table grant
      (catalog query above returns no rows), function `EXECUTE` is revoked
      from PUBLIC, and no app login is in `db_owner`. Probe:
      `grep -rniE "sp_addrolemember[[:space:]]+N?'db_owner'|ALTER[[:space:]]+ROLE[[:space:]]+\[?db_owner\]?[[:space:]]+ADD[[:space:]]+MEMBER" .`
- [ ] HIGH: each FDW/dblink/linked server/database link has a written reason
      and a dedicated least-privilege remote account; no PUBLIC or all-logins
      mapping, no `sa`/superuser remote login. Probe:
      `grep -rniE "USER[[:space:]]+MAPPING[[:space:]]+FOR[[:space:]]+PUBLIC|password_required[[:space:]]+'false'|sp_addlinkedsrvlogin.*(@rmtuser[[:space:]]*=[[:space:]]*N?'sa'|,[[:space:]]*NULL[[:space:]]*,)" .`
- [ ] Per-role connection limits and timeouts; individual (not shared) human
      logins; break-glass write access time-boxed.
- [ ] HIGH: no vendor default survives install — catalog login roles and
      databases match the repo's expected inventory (no anonymous user, no
      `test`/sample DB, bootstrap superuser password set, MongoDB
      authorization on). Config probe:
      `grep -rniE 'POSTGRES_HOST_AUTH_METHOD[=:][[:space:]]*"?trust|(MYSQL_ALLOW_EMPTY_PASSWORD|MARIADB_ALLOW_EMPTY_ROOT_PASSWORD)[=:][[:space:]]*"?[^"[:space:]]|authorization:[[:space:]]*"?disabled' .`
- [ ] HIGH: in-server code execution off unless documented — no untrusted PL
      languages, CLR/xp_cmdshell 0, MongoDB javascriptEnabled false, Redis
      debug/module commands not `yes`; `pg_extension` matches the expected list.
      Probe: `grep -rniE "(EXTENSION|LANGUAGE)[[:space:]]+(IF[[:space:]]+NOT[[:space:]]+EXISTS[[:space:]]+)?\"?(plpython3u|plperlu|pltclu)|'(clr enabled|xp_cmdshell)',[[:space:]]*'?1|enable-(debug|module)-command[[:space:]]+\"?yes|javascriptEnabled:[[:space:]]*true|--allow-scripting" .`
      (config that relies on MongoDB's default `true` has no line to hit —
      check the running `getCmdLineOpts` too).
- [ ] HIGH: self-managed server runs as a dedicated non-root OS account that
      does not own the binaries; host hardened from a CIS/vendor baseline with
      deviations recorded. Probe (unit files, my.cnf, compose, Dockerfiles):
      `grep -rniE "^[[:space:]]*user[[:space:]]*[=:][[:space:]]*[\"']?(root|0)([\"':]|$)|^USER[[:space:]]+(root|0)([[:space:]:]|$)" .`
- [ ] Credentials from secret manager/workload identity, rotatable without
      deploy, one per service; DB not publicly reachable; pg_hba explicit;
      no secrets in repos/images/CI logs.
- [ ] HIGH: every engine's listener bound to localhost/private interfaces (TCP
      off when co-located), superuser login local-only, admin consoles behind
      TLS + auth. Probe:
      `grep -rniE "listen_addresses[[:space:]]*=[[:space:]]*'(\*|0\.0\.0\.0|::)'|bind[-_]address[[:space:]]*=[[:space:]]*(\*|0\.0\.0\.0|::)|bindIp(All)?:[[:space:]]*\"?(0\.0\.0\.0|true)|^bind[[:space:]]+(\*|0\.0\.0\.0)|'root'@'%'|^host(ssl)?[[:space:]]+[^[:space:]]+[[:space:]]+postgres[[:space:]]+[^[:space:]]+[[:space:]]+(scram|md5|password|trust|cert)" .`
      (MySQL and a config-less Redis listen on all interfaces with no line to
      hit — check `SHOW VARIABLES LIKE 'bind_address'` / `CONFIG GET bind`).
- [ ] pgaudit (or equivalent) on DDL/roles/sensitive writes, logs shipped
      off-host; no log_statement='all' in prod; connection logging on.
- [ ] RLS enabled AND forced on protected tables; policies have WITH CHECK,
      fail closed on missing context, use SET LOCAL; security_invoker views;
      SECURITY DEFINER functions pin search_path; cross-tenant leak test in CI.
- [ ] CRITICAL: a catalog tenancy gate runs against the migrated database —
      request role not `rolsuper`/`rolbypassrls`, every table classified,
      tenant tables RLS-enabled, forced and with a policy (query above).
      Migration probe:
      `grep -rniE '(CREATE|ALTER)[[:space:]]+(ROLE|USER)[[:space:]].*[[:space:]](SUPERUSER|BYPASSRLS)|NO[[:space:]]+FORCE[[:space:]]+ROW[[:space:]]+LEVEL' .`
- [ ] TLS enforced server-side (hostssl, scram-sha-256) and verified
      client-side (verify-full); Redis has TLS+auth and no public binding.
- [ ] Disk encryption on; targeted column encryption (KMS keys, never in-DB,
      never in SQL text) for secrets/regulated fields, with blind indexes
      where lookup is needed; encrypted backups with separated keys.
- [ ] MEDIUM: embedded SQLite holding sensitive data sets `secure_delete`
      ON and `temp_store` MEMORY, and its db/-wal/-shm/-journal files are
      0600 (`ls -l app.db*`). Probe for explicit weakening:
      `grep -rniE "secure_delete[[:space:]]*=[[:space:]]*[\"']?(0|off|false|no)|temp_store[[:space:]]*=[[:space:]]*[\"']?(1|file)|SQLITE_TEMP_STORE=0" .`
- [ ] No string-built SQL anywhere (including raw ORM escape hatches and
      PL/pgSQL EXECUTE); identifier whitelist for dynamic ORDER BY/columns.
- [ ] PII inventory exists; no PII in logs/error trackers; non-prod
      environments use masked or synthetic data; BI roles see masking views,
      not base tables.
- [ ] Automated retention jobs per data category; RTBF flow enumerates all
      stores (cache, search, vector, queues, logs) with deadline tracking;
      backup expiry or crypto-shredding documented; soft-deleted rows purged.
