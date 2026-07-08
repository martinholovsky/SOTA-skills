# 08 — SurrealDB & Multi-Model

Scope: building on or auditing SurrealDB (document + graph + record-link
multi-model). Engine-choice discipline from file 01 still applies: SurrealDB
as primary store is a documented decision, not a default. The security
baseline of file 06 (least privilege, TLS, credentials, PII, retention)
applies in full; this file maps it onto SurrealDB's mechanisms.

## Version & auth model

### Rule: Know which version line you run; the auth model changed at 2.0.
- Current stable line is **3.x** (verify the current release when you pin);
  2.x still receives maintenance releases. Pin and track your line — auth and
  index syntax differ across major versions.
- Since v2.0.0, authentication is defined with **`DEFINE ACCESS`**, which
  replaced the older `DEFINE SCOPE`. Any code, docs, or AI-generated snippets
  using `DEFINE SCOPE`/`scope auth` are pre-2.0 and must not be cargo-culted
  into a 2.x/3.x deployment.
- `DEFINE ACCESS @name ON [ROOT | NAMESPACE | DATABASE] TYPE [JWT | RECORD |
  BEARER]` — `RECORD` access is the end-user path (custom `SIGNUP`/`SIGNIN`
  logic, record users subject to `PERMISSIONS`); `JWT` trusts tokens from an
  external issuer; `BEARER` issues grants for system/record users.

### Rule: Token and session lifetimes are explicit, short, and validated.
- Set `DURATION FOR TOKEN` (short — minutes) and `DURATION FOR SESSION`
  (bounded — hours, not "none") on every access method. Unbounded sessions
  on a record access method: HIGH.
- Use the `AUTHENTICATE` clause for extra checks at auth time (e.g. account
  not disabled, email verified) — `THROW` on failure. Signin logic that only
  checks password equality and never re-checks account state leaves revoked
  users live until token expiry.
- `TYPE JWT` access: pin the algorithm and verification key/issuer per the
  current docs; never accept unsigned or `alg`-confusable tokens. Inside
  permissions, `$token` exposes claims and `$auth` the authenticated record
  user — authorize on `$auth`/record state, not on client-controllable claims
  you don't verify.

## Least-privilege system users

### Rule: The application never connects as root or OWNER — one scoped system user per service.
SurrealDB system users (`DEFINE USER ... ON [ROOT | NAMESPACE | DATABASE]
ROLES OWNER | EDITOR | VIEWER`) are the analogue of file 06's roles:
- The root user from `surreal start --user/--pass` is for bootstrap and
  break-glass only. An app holding root credentials: CRITICAL — root bypasses
  all namespace/database boundaries and table `PERMISSIONS`.
- System users at ROOT/NAMESPACE/DATABASE level **bypass record-level
  `PERMISSIONS`** at their level and below — so services that should be
  subject to per-record authz must authenticate as record users (via
  `DEFINE ACCESS ... TYPE RECORD`), not system users.
- Where a service does need a system user (migrations, admin jobs): scope it
  `ON DATABASE`, lowest sufficient role (`VIEWER` for read-only consumers,
  `EDITOR` for data without IAM rights; `OWNER` only for the migration/
  bootstrap path — it can edit users and access methods). One user per
  service, credentials from the secret manager (see **sota-secrets-management**),
  rotated without redeploy.

## Parameterized SurrealQL

### Rule: All SurrealQL goes through bound $parameters — never string-built queries.
```js
// Correct: value bound server-side
db.query("SELECT * FROM article WHERE status INSIDE $status AND author = $auth.id",
         { status: ["live"] });
// WRONG (SurrealQL injection): "SELECT * FROM article WHERE title = '" + input + "'"
```
- Every SDK supports named `$param` bindings; string interpolation into a
  query is injection, same severity as SQL injection (file 06) — and worse if
  the connection is a system user (full DDL like `REMOVE TABLE` is in-band).
- Protected parameters `$auth`, `$token`, `$session`, `$access` are set by
  the server and cannot be overwritten — build permissions on them.
- Record IDs from user input: bind them too (`type::thing($table, $id)` or a
  bound record id), and whitelist table names — identifiers can't be bound,
  same rule as dynamic SQL identifiers in file 06.

## Schema enforcement

### Rule: SCHEMAFULL + typed fields + ASSERT for anything integrity-critical.
`SCHEMALESS` is acceptable for genuinely open-shaped data (ingest buffers,
flexible metadata) — never for money, auth, tenancy, or anything another rule
depends on.
```surql
DEFINE TABLE order SCHEMAFULL
  PERMISSIONS
    FOR select, update WHERE customer = $auth.id
    FOR create WHERE customer = $auth.id
    FOR delete NONE;
DEFINE FIELD customer  ON order TYPE record<customer>;
DEFINE FIELD total     ON order TYPE decimal ASSERT $value >= 0dec;
DEFINE FIELD status    ON order TYPE string
  ASSERT $value INSIDE ["pending", "paid", "shipped", "cancelled"];
DEFINE FIELD created_at ON order TYPE datetime DEFAULT time::now() READONLY;
```
- `SCHEMAFULL` rejects undefined fields; on `SCHEMALESS` tables, defined
  fields still enforce their `TYPE`/`ASSERT` — so at minimum define and
  constrain the critical fields even on schemaless tables.
- `TYPE record<other_table>` is your referential typing; SurrealDB does not
  enforce cross-record existence like a SQL FK by default — add `ASSERT` /
  application checks or events where orphan links would corrupt logic, and
  audit for dangling record links in reconciliation jobs.
- `READONLY` for immutable fields (created_at, ledger amounts);
  `VALUE`/`DEFAULT` for server-computed fields so clients can't supply them.

## Record-level permissions

### Rule: Deny-by-default is the platform default — keep it that way and write explicit FOR clauses.
- Tables without a `PERMISSIONS` clause default to `PERMISSIONS NONE` for
  record users. Audit for blanket `PERMISSIONS FULL` — it's the SurrealDB
  equivalent of disabling RLS (file 06): HIGH on any table holding user data.
- Write all four verbs deliberately: `FOR select / create / update / delete`,
  each `WHERE`-scoped to `$auth` (ownership/tenancy). A `select` rule without
  matching `create`/`update` rules is the `USING`-without-`WITH CHECK`
  mistake from file 06 — users may write rows they couldn't read.
- Field-level `PERMISSIONS` on `DEFINE FIELD` for column-grade secrets
  (e.g. internal flags, PII fields readable only by the owner).
- Remember the bypass: permissions bind **record users only**; system users
  and root skip them. The cross-tenant leak test from file 01/06 applies —
  authenticate as two record users in CI and prove isolation, exercising the
  shapes that have actually bypassed permissions: graph-edge and reference
  traversals, indexed `ORDER BY` on restricted fields, and `LIVE SELECT`
  results — not just direct `SELECT`s.
- Permission enforcement has a **patch floor** — bypasses recur, so track the
  advisory feed for your line. Known floors: **CVE-2025-11060** (LIVE query
  results exposed unpermitted data; fixed in 2.1.9 / 2.2.8 / 2.3.8 /
  3.0.0-alpha.8); the **3.1.5 batch (June 2026)** — field-level SELECT
  permissions bypassed via graph/reference traversals, indexed-ORDER-BY
  ordering leak on restricted fields, deep-operator-chain DoS, and a High
  arbitrary file read via `DEFINE ANALYZER mapper()` (GHSA-cc8f-fcx3-gpjr);
  the **3.2.0 batch (July 2026)** — High custom-API namespace/database scope
  override (GHSA-848m-r628-vrxw), writes inside a `PERMISSIONS` clause
  bypassing table permissions (GHSA-66r2-5gwj-gxm2), and JWKS SSRF. On 3.x,
  run ≥ 3.1.5 at minimum, ≥ 3.2.0 where custom API routes exist.

## Capabilities hardening

### Rule: Run the server deny-by-default; allow-list only the capabilities you use.
SurrealDB has runtime capability flags; most are denied by default but
**functions are allowed by default**, and denies beat allows at equal
specificity:
```sh
surreal start --deny-all \
  --allow-funcs "array,string,time,math,type,crypto::argon2" \
  --deny-guests          # no unauthenticated queries
# scripting stays denied: embedded JS (--allow-scripting) is an RCE-adjacent
# surface — enable only with a written reason.
# outbound network from queries (--allow-net) stays denied, or allow-list
# exact hosts: --allow-net api.internal:443
```
- `--allow-all` in production: HIGH. `--allow-guests` on a database with any
  non-public data: CRITICAL. `--allow-scripting` without a documented need:
  HIGH.
- `--allow-net` is SSRF-from-the-database; if queries must call out, pin
  exact targets. Flag names and defaults evolve — verify the current
  capabilities page for your version when auditing.
- Query file access is deny-by-default since 3.1.5: with no
  `SURREAL_FILE_ALLOWLIST` configured, every path is denied. Pre-3.1.5 an
  empty allowlist meant *no* restriction — the arbitrary-file-read vector of
  GHSA-cc8f-fcx3-gpjr. Leave the allowlist unset unless queries genuinely
  need files, then pin exact directories.

## Network exposure & TLS

### Rule: Never publicly reachable; TLS everywhere; credentials from the secret manager.
- Bind to private interfaces only; reachable solely from app networks. A
  publicly listening SurrealDB — even with auth — is HIGH (same stance as
  Postgres/Redis in file 06).
- TLS for all client traffic: terminate at the server (verify current cert
  flags in the docs for your version) or front with a TLS proxy on a private
  network; never send root/system credentials or tokens over cleartext.
- Root/system/user credentials, JWT signing keys: secret manager, per-service,
  rotatable — full doctrine in **sota-secrets-management**. No `--pass` values
  in compose files, shell history, or CI logs.

## Indexes & query planner

### Rule: Same discipline as file 03 — every production query has a known index; EXPLAIN it.
- `DEFINE INDEX` types: standard, `UNIQUE` (uniqueness is a constraint here,
  same as file 01 — enforce in the DB, not the app), composite, count
  indexes, `FULLTEXT ANALYZER` (3.x name; `SEARCH ANALYZER` pre-3.0) with
  BM25, and vector indexes (`HNSW` with `M`/`EFC` tuning; `DISKANN` from
  3.1 for larger-than-RAM sets; brute force for small/exact). Vector rules
  from file 07 (recall measurement, model versioning) apply unchanged.
- Build indexes on live tables with `CONCURRENTLY`; monitor via
  `INFO FOR INDEX`.
- Verify usage with `EXPLAIN` / `EXPLAIN FULL` — look for `Iterate Index`
  rather than table scans on hot paths.

## Multi-model modeling

### Rule: Embed what's read together; reference what's shared; use edges for relationships you query both ways.
- **Embed** (nested objects/arrays on the record) data owned by and read with
  the parent: order line items, address snapshots. One read, no joins,
  schema-enforceable via nested `DEFINE FIELD`.
- **Reference** (`TYPE record<t>` links) shared or independently mutated
  data: customer ← orders, product catalogs. Record links traverse without
  explicit joins (`order.customer.name`) — fetch depth deliberately, not `*`
  expansion everywhere.
- **Graph edges** (`RELATE user->purchased->product`, edge tables with their
  own fields/permissions) when the relationship itself carries data or you
  traverse both directions. Edge tables get the same SCHEMAFULL/PERMISSIONS
  treatment as ordinary tables — they're rows, and they leak like rows.
- Don't model everything as a graph because the engine can: the file 01
  modeling questions (access patterns first) still decide the shape.

## Backups

### Rule: A SurrealDB you can't restore is file 06's "backup that isn't" — rehearse both layers.
- Logical: `surreal export` produces a `.surql` script (scope what's included:
  records, accesses, users, functions). Note the emitted `OPTION IMPORT`
  line — it disables events/side effects on import (required for
  `surreal import` on current versions); that's correct for restores, but
  means imports don't re-fire events.
- Storage-engine level: snapshot/back up the underlying datastore per your
  deployment (embedded RocksDB file copies only when consistent, or the
  backing TiKV/FoundationDB cluster's native backup) — verify the supported
  procedure for your storage engine in the current docs.
- Schedule both, encrypt them, store keys separately, and rehearse restores
  with RPO/RTO stated (file 05 discipline). Exports contain your data AND
  your access definitions — treat the files as secrets.

## Audit checklist

- [ ] Version line known and pinned; no pre-2.0 `DEFINE SCOPE` syntax in
      migrations/docs; version meets the advisory patch floor — 3.x: ≥ 3.1.5
      (June 2026 permission-bypass/file-read batch), ≥ 3.2.0 where custom API
      routes exist; 2.x: CVE-2025-11060 LIVE-query fix versions.
- [ ] Auth via `DEFINE ACCESS` (RECORD for end users); `DURATION FOR TOKEN`
      and `FOR SESSION` short and explicit; `AUTHENTICATE` re-checks account
      state; JWT access methods pin algorithm/keys.
- [ ] App never connects as root/OWNER; per-service system users scoped
      `ON DATABASE` with lowest role; services needing record-level authz use
      record users; credentials from secret manager, rotatable.
- [ ] All queries use bound `$params`; no string-built SurrealQL anywhere
      (grep SDK call sites for interpolation); dynamic identifiers whitelisted.
- [ ] Integrity-critical tables SCHEMAFULL with TYPE/ASSERT/READONLY fields;
      record links checked for orphans where it matters; no untyped critical
      fields on SCHEMALESS tables.
- [ ] No `PERMISSIONS FULL` on user-data tables; all four verbs scoped to
      `$auth`; field-level permissions on sensitive fields; cross-tenant leak
      test in CI covers LIVE queries, graph/reference traversals, and indexed
      ORDER BY on restricted fields.
- [ ] Server runs deny-by-default capabilities: no `--allow-all`, no
      `--allow-guests`, scripting denied, functions and outbound net
      allow-listed; flags re-verified against current docs.
- [ ] Not publicly reachable; TLS on all client connections; no credentials
      in compose files/CI logs.
- [ ] Hot-path queries EXPLAIN-verified (`Iterate Index`); uniqueness via
      UNIQUE indexes; index builds on live tables use CONCURRENTLY; vector
      indexes follow file 07 rules.
- [ ] Modeling: embed/reference/edge choices match access patterns; edge
      tables have schema + permissions.
- [ ] Both `surreal export` and storage-engine backups scheduled, encrypted,
      restore-rehearsed; export files handled as secrets.
