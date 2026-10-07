# /sota-audit — Harbor v2.5.1, `src/server` + `src/controller` + `src/go.mod`

Audit date: 2026-10-07. The auditor is one agent context. Six High findings also went to one independent refuter, an Explore agent that could only read code. Fixes: none (the operator asked for none).

## Posture verdict

**Not ready.** The API's object-level authorization is broken in six handler families. By default any user can create a project and so becomes projectAdmin of it (`lib/config/metadata/metadatalist.go:117`, default `everyone`). From that position the user can do all of the following:

- read other projects' webhook credentials (`auth_header`);
- overwrite or delete other projects' webhook, preheat, immutability, retention and robot configuration;
- read job logs, and stop jobs, that belong to other projects or to the system (GC, replication, scan-all).

Counts: **High 6 · Medium 8 · Low 10 · Info 3.** Plus the dependency table in F-M6: 19 modules carry Critical/High advisories.

Top risks in plain terms:
1. A tenant can steal the secrets another tenant configured for its webhooks (H-1).
2. A tenant can switch off another tenant's tag-immutability, retention, preheat, webhook and robot controls (H-1, H-3 to H-6).
3. A tenant can stop the administrator's garbage collection, replication and scan-all jobs, and read their logs (H-2).
4. Any user who can push can take harbor-core down. An uploaded chart icon or chart layer is decoded with no size limit; the decode request itself needs no authentication. A 558 KB PNG cost 549 MiB to decode, 3 of 3 runs (M-1, M-2).
5. The dependency set is badly stale: 128 advisories (4 Critical). The vulnerable functions in golang-jwt, gorilla/csrf, x/net and helm are reachable on the call graph (M-6).

---

## 1. Scope and methodology

**Scope (agreed in advance):** the non-test Go files under `src/server` and `src/controller`, plus `src/go.mod`. Everything else in the workspace was read for context only. No finding is raised against it; out-of-scope observations are listed separately.

**Pin.** There is no git history (`git rev-parse HEAD` → `fatal: not a git repository`), so the tree is identified by content:

| what | value |
|---|---|
| `VERSION` | `v2.5.1` |
| sha256 of the concatenated, sorted, non-test scope sources (first 16 hex) | `4c8f08d4ef34f933` |
| `src/go.mod` sha256 (first 12 hex) | `4b7a0761ef75` |
| denominator | 232 non-test `.go` files, 31,877 lines (gosec's file count agrees); 173 v2.0 handler operations |

Diff scope, dependents, base branch and history: **not reached**, because there is no git history.

**Yardstick:**
- OWASP API Security Top 10 (2023): API1 BOLA, API5 BFLA, API4 unrestricted resource consumption, API7 SSRF.
- OWASP ASVS 5.0 L2, specifically V8 authorization, V7 sessions, V6 authentication and V2 validation.
- CWE ids are given per finding.

There are no LLM or agent surfaces in scope.

**Stack profile.** `~/.claude/profiles/<owner>.md` exists, but it is the baseline for the operator's own repositories. Harbor is upstream code the operator does not own, so I did not raise profile deviations (Python/SurrealDB/etc. stack, the permissive-licence policy) as findings. This is recorded under Q-5.

**Project conventions read:**
- `CONTRIBUTING.md` (present).
- `Makefile` `go_check` target: golint and govet only.
- `.github/workflows/codeql-analysis.yml`: CodeQL `@v1`.
- There is no `AGENTS.md` or `CLAUDE.md`. The search used `find` over the workspace minus vendor; a positive control found `README.md`.

**Day zero:** does not apply. The repository has a licence, CI and CodeQL; its history length is unknown.

**Threat model:** the *light* model from step 3 (boundary table below). The full reconstruction from `sota-threat-modeling` rules/06 was not done.

**Partitioning.** About 32k lines is more than one context can read line by line, so I read by crown jewels, in this order:
1. Authentication middleware (`server/middleware/security/*`, `v2auth`, `csrf`, `session`).
2. Every v2.0 handler that takes a client-supplied object ID: a census of all 173 operations, then a full read of each one that does not bind the ID to the authorized project.
3. Request-body parsers and outbound fetchers.
4. Spot reads of the controllers those paths reach.

`controller/replication/**`, `controller/scan/**` beyond `GetScanLog`, `controller/proxy/**` beyond its goroutines, `controller/quota/**`, `controller/gc/**` and `controller/event/**` were **not read line by line**. Most of them sit behind system-admin-only handlers.

### Scanners (all run at the pinned tree)

| tool | version | command | result | depth / caveat |
|---|---|---|---|---|
| govulncheck | v1.8.0, DB 2026-10-01 | `GOFLAGS=-mod=vendor govulncheck -format json <84 pkgs>` | 350 OSV entries; 35 advisories reached at symbol level | 5 packages could not be type-checked because the generated swagger code (`server/v2.0/models`, `restapi`) is absent and go-swagger is not installed: `server`, `server/v2.0/handler`, `…/assembler`, `…/model`, `…/route`. Call-graph roots therefore exclude the API handlers, so reachability is **under-reported**. The scanner ran on toolchain go1.27.1, but Harbor builds with `golang:1.17.7` (`Makefile:160`), so **stdlib advisories for the shipped binary were not assessed**. `-scan module` failed ("no Go files in src") and was not retried. |
| trivy | 0.72.0 (0.75.0 is available) | `trivy fs --scanners vuln --format json src/go.mod` | 128 vulns: C 4, H 55, M 61, L 6, unknown 2; 19 modules with C/H | Reads the manifest only; no reachability. My first invocation was malformed (several paths) and printed usage. It was re-run, exit 0. |
| gosec | 2.29.0 | `gosec -quiet -fmt json ./server/... ./controller/...` | 232 files / 31,877 lines, 66 issues: G104×62, G404, G101, G118, G601 | 35 packages had type errors (same missing generated code), so type-dependent rules are degraded. Triage is in the appendix. |
| gitleaks | 8.30.1 | `gitleaks dir --redact` on `server`, `controller`, `go.mod` | 0 leaks over ~749 KB plus ~914 KB | Positive control: a planted `ghp_` token in a scratch file was found (1 leak). The `go.mod` file argument scanned **0 bytes** (instrument gap), so go.mod was checked by reading it (no credentials). **History scan: not reached** (no `.git`). |
| go vet | go1.27.1 | `go vet <84 pkgs>` | exit 0, 0 diagnostics | Same 5 packages excluded. Loop-variable checks follow 1.27 semantics, not the module's `go 1.17`. |
| go test | go1.27.1 | `go test -count=1 ./server/middleware/... ./controller/...` | 81 packages: 44 ok, 23 FAIL, 14 without tests | All 23 failures are environmental: `POSTGRESQL_HOST is not set`. No database was available, so **the suite's real pass state is unknown**. |
| golangci-lint | 2.13.2 | not run | n/a | Needs the 5 packages that do not compile without generated code. Its errcheck/gosec coverage overlaps the gosec run. |
| own probe | go1.27.1 stdlib | `scratchpad/auditeval/w6probe/main.go` | see M-1 | 3/3 identical runs |

The refutation bar was fixed before any verdict was seen: **confidence ≥7 keeps the High**, 4–6 downgrades it to "needs verification", ≤3 drops it.

### Evidence not obtained, and what it would change
- **Deployment topology** (compose vs Helm/ingress) and whether harbor-core is reachable without the shipped nginx rule `location /service/notifications { return 404; }`. This would move M-7 between Medium and Low.
- **A live instance** to reproduce H-1 to H-6 end to end. Every one is a static read path, confirmed by a second, read-only refuter, but none was executed. A two-user test against a running v2.5.1 would close them.
- **The Go 1.17.7 stdlib advisory set** for the shipped binary. That needs govulncheck run with the 1.17 toolchain.
- **Postgres and Redis** for the unit suite (23 packages unexecuted).
- **The vendor advisory database for Harbor itself** (network was disallowed). I could not check which Harbor release fixes these classes, so "upgrade to version X" is not asserted anywhere in this report.

---

## 2. Coverage

### Recon: surfaces, and the skills that own them

| surface found | owning skill | rules file | walked? | if not, why |
|---|---|---|---|---|
| REST API, 173 ops, object IDs | sota-code-security | 03 authorization | **walked** (checklist items below) | — |
| authn middleware: basic, robot, OIDC CLI, ID token, auth-proxy, session, secret | sota-code-security | 02 authentication | **walked** (checklist read) | — |
| sessions (beego), JWT v2 tokens | sota-code-security | 17 sessions/tokens | **walked** (checklist read) | — |
| CSRF, browser headers | sota-code-security | 05 web, 20 headers | partial | the headers live in nginx (out of scope); CSRF read in code |
| untrusted blobs parsed in core (chart tgz, icons, manifests) | sota-code-security | 09 ingestion, 06 resource | walked by grep plus a probe | checklist files not opened; sinks found by `ReadAll`/`Decode` sweep |
| outbound fetch to user URLs (webhooks) | sota-code-security | 01 §SSRF | partial | the sender lives in jobservice (out of scope; read for context) |
| crypto / secret comparison | sota-code-security | 04, 22 | partial | `utils.Encrypt` PBKDF2 and `!=` compare read; checklists not opened |
| logging / data exposure | sota-code-security | 07 | partial | log-format sweep run; checklist not opened |
| present-but-inert controls | sota-code-security | 10, 11, 14, 16 | **walked** (step 6 below) | — |
| Go language | sota-golang | SKILL top-10, 04 http (checklist read), 01/03/05/08 | top-10 plus 04 walked; 01/03/05/08 via greps only | file checklists 01/03/05/06/07/08 not opened |
| webhooks (provider role) | sota-api-design | 06 webhooks | **walked** (checklist read) | — |
| REST semantics, versioning | sota-api-design | 01, 02, 07 | **not walked** | time budget; authz took priority |
| goroutines | sota-async-concurrency | 01–xx | **not walked** | goroutine sweep only (23 sites) |
| test suite | sota-testing | 07 suite health, 09 security testing | partial | suite run (environment-blocked); authz-deny test census done |
| dependencies (`go.mod`) | sota-devsecops | 03 SCA | walked (scanners plus a per-module table) | — |
| secrets | sota-secrets-management | scan | walked (gitleaks plus control) | history not available |
| personal data (user email, realname, audit-log usernames, client IP in logs) | sota-privacy-compliance | 01/retention | **not walked** | **hole**: the surface exists and no checklist was opened |
| identity infra (OIDC, LDAP onboarding, auth-proxy admin-group mapping) | sota-identity-access | all | **not walked** | **hole** |
| observability, performance, architecture | respective skills | all | **not walked** | **hole**, out of time budget |
| threat model | sota-threat-modeling | 06 (light) | light model only | — |
| DB/SQL | sota-databases | 03 | not applicable in scope | DAOs live in `pkg/` (out of scope); scope has no raw SQL (grep for `Raw(`/`Sprintf("select`: 0 hits) |
| shell, CI, Dockerfiles, IaC | shell / devsecops | — | not applicable | out of scope |
| my own verification commands | sota-shell-scripting | 06 | applied | one zsh glob failure (`--include=*.go` unquoted gave "no matches found"). I caught it and re-ran quoted. |

**An unexamined domain is not a clean one.** Privacy, identity infrastructure, observability, performance, architecture, async and API-design REST semantics are **holes in this audit**, not passes.

### Checklist items walked: code-security rules/03 (authorization)

| item | verdict |
|---|---|
| Single default-deny enforcement layer | **not met.** Authorization is per handler (`BaseAPI.RequireProjectAccess`); the global chain (`core/middlewares/middlewares.go`) only authenticates. `/v2` has deny-by-default (`v2auth/access.go`: an empty access list is rejected), which is a positive. |
| Ownership/tenant predicate inside the query for client IDs | **not met** in 6 families: H-1 to H-6 |
| Nested IDs and background-job parameters checked | **not met**: H-2 (execution/task IDs) |
| Roles from server state only | met (`local.SecurityContext` from DB or session) |
| No self-elevation | met for members (`member` DAO predicates on `project_id`) and sysadmin (`SetUserSysAdmin` requires system access) |
| Cross-tenant deny test suite | **not met** (M-8) |
| 404 for unseen objects | partial: unauthorized gives 403, missing gives 404, and missing project → 401 in v2auth (L-10) |
| Stale session privilege (§3) | **not met** (M-4) |
| Admin password reset (§7) | **not met** (L-4: checklist default High, Low on the chain) |
| Permission data reads (§4) | met: robot permissions need project robot read |
| Policy failures fail closed | met: `RequireProjectAccess` denies on lookup error |

### rules/02, rules/17 and golang rules/04 items that produced findings
- **Rate limiting on login/auth: not met** (M-3).
- PBKDF2 for user-chosen robot secrets: L-3.
- **Password change verifies the current password: met for self-service** (`user.go:297-305`).
- **Session regenerated/invalidated on privilege change: not met** (M-4).
- **JWT algorithm pinned: met** (`pkg/token/token.go` compares `token.Method.Alg()`); `exp` via `Claims.Valid`; `aud` checked in `v2_token.go`.
- **Body reads without `MaxBytesReader`: not met** (M-2). The golang rules/04 default is HIGH; it is rated Medium on the chain.
- **CSRF layer present: met** (gorilla/csrf; its advisory is listed in M-6).
- Server timeouts: not applicable in scope (`core/main.go`, out of scope).

### Webhooks checklist (provider role)
- No request signing: only an optional static `auth_header`. Raised as Info I-3.
- **SSRF defences absent** (M-5).
- **Secrets returned in API responses** (H-1). The per-project path also returns them to the policy's own projectAdmin; that is by design and not counted.

### Skill-level top-10s
**code-security:**
- #4 object-level authz: **violated** (H-1 to H-6).
- #5 password hashing: robot secrets use PBKDF2 at 4096 iterations (L-3; user passwords are out of scope).
- #6 JWT: met.
- #7 constant-time comparison: robot secret compared with `!=` on derived hashes (L-3).
- #9 SSRF: **violated** (M-5).
- #1, #2, #3, #8: no violation found in scope. #1 was checked by grep with 0 raw-SQL hits; #2 by `exec.Command` grep with 0 hits.

**golang:**
- #1 errors: **violated** (L-1, 62 G104).
- #3 goroutine ownership: L-6.
- #4 race CI: not checked.
- #5 timeouts: out of scope.
- #10 govulncheck gate: **absent** in CI (`go_check` = golint plus govet); this is consistent with M-6.

**Principle 5 re-check (done last):**
- (a) abuse control: **absent** (M-3).
- (b) transport: HSTS and TLS are delegated to nginx (`nginx.https.conf.jinja:73`). Credited as handled elsewhere, but the in-code CSRF cookie `Secure` flag comes from the scheme of `ExtEndpoint` (`csrf.go:99-106`).
- (c) tests for the logic: no authz-deny tests (M-8).
- (d) structured logs without secrets: L-2 (the CSRF key is logged) and L-9 (spoofable client IP).

---

## 3. Light threat model: boundary map (built from code)

| entry point | authn/authz checkpoint | asset reached | privilege it runs with |
|---|---|---|---|
| `/api/v2.0/**` (go-swagger) | `security.Middleware` → generator chain (`server/middleware/security/security.go:47-63`); per-handler `RequireProjectAccess`/`RequireSystemAccess` (`server/v2.0/handler/base.go:105-133`) | DB (projects, policies, robots, users), task logs | core DB credentials |
| `/v2/**` (registry) | `v2auth.Middleware` (`server/middleware/v2auth/auth.go:47-82`), deny on unknown path | blob storage via distribution proxy | core's registry credentials |
| `/service/notifications/**` job hooks | **none in process** (`server/handler/job_status_hook.go:37-60`); nginx 404 only | task/execution status, scheduler callbacks | core DB |
| `/api/v2.0/icons/{digest}` | **none** (`server/v2.0/handler/icon.go`) | blob decode in core | core |
| webhook targets (outbound) | projectAdmin sets the URL (`notification_policy.go:223-241`) | any network reachable from jobservice | jobservice network position |

Assumptions the code implies, and what checking them showed:
- *"Only system admins create projects"*: **false by default.** `metadatalist.go:117` sets `everyone`. This makes every project-scoped BOLA reachable by any authenticated user.
- *"nginx blocks `/service/notifications`"*: true in the shipped compose template (`nginx.https.conf.jinja:227-229`). **Unverified** for other deployment topologies.
- *"Object IDs in a project-scoped path belong to that project"*: **false.** It is a broken assumption (H-1 to H-6).
- *"The icon size limit holds"*: **false** (M-1).

---

## 4. Decision ledger (reconstructed; there are no ADRs: `docs/` holds only README and images)

| decision | verdict | evidence |
|---|---|---|
| Authorization enforced per handler, with a project-level check and no project predicate in the DAO | **UNJUSTIFIED as implemented** (reconstructed, unconfirmed) | No document records the choice. It depends on every handler binding every ID. Of the handler families that take a sub-object ID, 6 fail to (H-1 to H-6), while members (`pkg/member/dao/dao.go:171,181`) and v1 robots (`robotV1.go:122,192,215`) get it right. The pattern is known and inconsistently applied. |
| Web framework and sessions on beego v1 (`github.com/beego/beego v1.12.9`) | **STALE** | govulncheck reports GO-2024-3331 and GO-2025-3585 with "fixed: None" on the v1 line; trivy lists 2 Critical plus 3 High for this module. Migrating is large. |
| Language level `go 1.17`, build image `golang:1.17.7` (`Makefile:160`) | **STALE** | The library records Go's supported pair as 1.26/1.27 as of 2026-08 (verify at go.dev; not fetched). Pre-1.22 loop semantics are still in force (L-7). |
| Edge controls (HSTS, TLS, the `/service/notifications` block) delegated to nginx | **JUSTIFIED** for the compose template (`nginx.https.conf.jinja:73-75,227-229`); **UNVERIFIABLE** for other topologies | Would be settled by the deployment manifests actually used (Helm/ingress). |
| Self-service project creation on by default | JUSTIFIED as a product choice, but it is the precondition that turns H-1 to H-6 from "insider" into "any user" | `metadatalist.go:117` |

---

## 5. Findings

Working table (deduplicated across domains):

| # | file:line | rule violated | severity | effort | fix |
|---|---|---|---|---|---|
| H-1 | server/v2.0/handler/notification_policy.go:155, :143, :116+130; notification_job.go:34 | code-sec 03 §2 BOLA; top-10 #4 | High | small | load the policy, require `policy.ProjectID == projectID`, use the path ID, ignore the body ID |
| H-2 | server/v2.0/handler/preheat.go:581, :650, :693, :725; retention.go:277, :326, :353 | code-sec 03 §2 (nested IDs), BFLA | High | small | load execution/task; require vendor type and `vendor_id` equal to the authorized policy |
| H-3 | server/v2.0/handler/preheat.go:262-267 (body ID/ProjectID at :469/:472) | 03 §2 BOLA | High | small | resolve the policy by (project, path name), take the ID from the stored row, force `ProjectID` |
| H-4 | server/v2.0/handler/immutable.go:62, :76-84 | 03 §2 BOLA | High | small | load the rule, require `rule.ProjectID == projectID`, use the path rule ID |
| H-5 | server/v2.0/handler/retention.go:196-210 | 03 §2 BOLA (check against body, not stored object) | High | small | authorize against `GetRetention(params.ID)` *and* require that the body scope equals the stored scope |
| H-6 | server/v2.0/handler/robot.go:287, :313 | 03 §2 BOLA | High | small | `requireAccess(ctx, r.Level, r.ProjectID, ActionUpdate)` on the stored robot, then require body namespace == stored project |
| M-1 | controller/artifact/annotation/v1alpha1.go:83-88; controller/icon/controller.go:136; server/v2.0/handler/icon.go (GetIcon) | code-sec 09/06 decompression bomb; 10 silent control (truncation) | Medium | small | check the declared size (`LimitReader(n+1)` then `len > n`); `image.DecodeConfig` with a dimension cap before `Decode`; require authn or project read on GetIcon |
| M-2 | controller/artifact/processor/chart/chart.go:87; server/middleware/blob/put_manifest.go:37,67; cosign/cosign.go:77; quota/util.go:52 | golang 04 body hygiene (default HIGH); code-sec 09 | Medium | small | `http.MaxBytesReader`/`io.LimitReader` (manifests ≤4 MiB, chart layer cap); upgrade helm |
| M-3 | server/middleware/security/basic_auth.go (Generate), robot.go (Generate), oidc_cli.go | code-sec 02 §1 rate limiting; principle 5a; CWE-307 | Medium | medium | per-account and per-IP throttling on failed credential checks (or document that it is at the edge) |
| M-4 | server/middleware/security/session.go:37-47 | code-sec 17 §2; 03 §3 stale privilege; CWE-613 | Medium | medium | re-read the user per request (or a version stamp); revoke sessions on SetSysAdmin/Delete/UpdatePassword |
| M-5 | server/v2.0/handler/notification_policy.go:223-241 (validateTargets) | code-sec 01 SSRF; top-10 #9; api-design 06; CWE-918 | Medium | medium | resolve-and-pin with private/link-local/metadata ranges blocked at dial time; no redirects; restrict `skip_cert_verify` to admins |
| M-6 | src/go.mod | devsecops 03 SCA; golang top-10 #10 | Medium overall (per-module rows below) | medium–large | upgrade the modules in the table; add a govulncheck gate |
| M-7 | server/handler/job_status_hook.go:37-60; server/route.go (registrations) | code-sec 03 §6 internal identity; 14 control-not-in-force (network position as control) | Medium if core is reachable without nginx; Low behind the shipped nginx | small | require the jobservice secret (`IsSolutionUser`) in the handler |
| M-8 | server/v2.0/handler/*_test.go (absence) | sota-testing 09; code-sec 03 cross-tenant test | Medium | medium | table test per handler family: user of project A against project B's object IDs → 403/404 |
| L-1 | server/v2.0/handler/artifact.go:72, repository.go:59, scan.go:44, config.go:69, config.go:110, user.go:319-322; 62× G104 | golang 01 errors; code-sec 10 swallowed errors | Low | small | return the responder; check `err`; return `err2` |
| L-2 | server/middleware/csrf/csrf.go:57 | code-sec 07 secrets in logs | Low | trivial | log only the length of the invalid key |
| L-3 | server/v2.0/handler/robot.go:226-230; server/middleware/security/robot.go (compare) | code-sec 02 §1 / top-10 #5, 22 constant time; CWE-916/208 | Low | small | argon2id for user-chosen robot secrets; `subtle.ConstantTimeCompare` |
| L-4 | server/v2.0/handler/user.go:291-325 | code-sec 03 §7 (checklist default High) | Low on the chain | small | admin-triggered reset flow; compare the new password against the *target* user (line 311 uses the caller) |
| L-5 | server/v2.0/handler/artifact.go:451-463 → controller/artifact/controller.go:586 | 03 §2 (nested ID) | Low | small | require `label.Scope==global` or `label.ProjectID == artifact.ProjectID` |
| L-6 | server/middleware/repoproxy/proxy.go:244; server/v2.0/handler/project.go:501 | golang top-10 #3 goroutine ownership | Low | small | bounded worker / errgroup with limit; tie the background tag-ensure to a bounded queue |
| L-7 | controller/event/handler/util/util.go:35 | golang 03 loop-var aliasing under `go 1.17` | Low, **needs verification** | trivial | `t := target; Target: &t` |
| L-8 | server/v2.0/handler/icon.go GetIcon | 03 deny-by-default | Low | small | same fix as M-1 (authz) |
| L-9 | server/middleware/security/basic_auth.go (GetClientIP) | code-sec 07 log integrity | Low | small | use the proxy-set header only from trusted hops |
| L-10 | server/middleware/v2auth/auth.go:71-73 | 03 consistent 404 | Low | trivial | return the challenge without disclosing project existence |
| I-1 | controller/member/controller.go:95-103 | role not validated on update (create validates) | Info | trivial | call `isValidRole` |
| I-2 | server/v2.0/handler/preheat.go:482-505 | provider credentials (`AuthInfo`) returned to admins | Info | small | mask on read |
| I-3 | webhook delivery | api-design 06: no HMAC signing of deliveries | Info | medium | signed deliveries |

### Full evidence blocks: Critical/High

**H-1: Cross-project read, overwrite and delete of webhook policies, including target credentials**
- Severity: **High.** Any authenticated user (projectAdmin of their own project, C7) reads another tenant's `auth_header` secrets and tampers with its webhooks.
- Location:
  - `server/v2.0/handler/notification_policy.go:155` (Get), `:143` (Delete), `:116,:129-130` (Update: ID from the body via `lib.JSONCopy`, `ProjectID` forced to the caller's project).
  - `server/v2.0/handler/notification_job.go:34` (ListWebhookJobs by any `PolicyID`, which returns `JobDetail` payloads).
  - `server/v2.0/handler/model/notification_policy.go:37` (AuthHeader copied out).
  - DAO by primary key only: `pkg/notification/policy/dao/dao.go:46-49, 89, 131-133`.
- Evidence: `policy, err := n.webhookPolicyMgr.Get(ctx, params.WebhookPolicyID)`, called after `RequireProjectAccess(ctx, projectNameOrID, …)` on the *path* project only.
- Mapping: CWE-639, CWE-200 (credential exposure); OWASP API1:2023 BOLA; ASVS 5.0 V8.2.
- Chain:
  - reach: an authenticated user creates project A and becomes projectAdmin (`project.go:93-208`, `metadatalist.go:117`);
  - act: `GET /api/v2.0/projects/A/webhook/policies/{B's id}` (IDs are sequential DB keys);
  - boundary: tenant A to tenant B;
  - channel: the HTTP response body carries `targets[].auth_header`.
- Impact:
  - The attacker obtains the credentials B's webhook receivers expect, which can be replayed against B's systems.
  - The attacker can delete B's webhooks, or overwrite one (which also moves it into project A), so B's notifications stop silently.
  - The attacker can read B's webhook delivery payloads (repository and tag names, operators).
- Remediation (diff-level):
  ```
  policy, err := n.webhookPolicyMgr.Get(ctx, params.WebhookPolicyID)
  if err != nil { return n.SendError(ctx, err) }
  if policy.ProjectID != projectID { return n.SendError(ctx, errors.NotFoundError(nil)) }
  ```
  Apply the same pattern in Delete, Update (`policy.ID = params.WebhookPolicyID` after `JSONCopy`, then the same check on the stored row) and ListWebhookJobs.
- Effort: small.
- Reproduction (static read path): `notification_policy.go:150-151` RequireProjectAccess(A) → `:155` `Mgr.Get(id)` → `pkg/notification/policy/manager.go:96-108` → `dao.go:46-49` `ormer.Read(&Policy{ID:id})` → `:160` response → `model/notification_policy.go:37` `AuthHeader: t.AuthHeader`. Runnable form: two users U1 (project A) and U2 (project B); U2 creates a webhook with `auth_header: X`; U1 GETs `/api/v2.0/projects/A/webhook/policies/<id>`. Expected under the finding: 200 with `X`. Not executed (no live instance).
- Refutation: independent refuter, **CONFIRMED, 9/10**. Self-sweep: same pattern found in `notification_job.go:34` (added).

**H-2: Execution and task IDs not bound to the authorized policy, giving cross-project and system job log disclosure and stop**
- Severity: **High.** A projectAdmin of any project (and a maintainer, for the retention paths) reads logs of, and stops, executions of other projects *and of system jobs* (GC, replication, scan-all). This is BOLA plus function-level escalation.
- Location:
  - `server/v2.0/handler/preheat.go`: GetExecution `:581`, StopExecution `:650`, ListTasks `:693` (`execution_id` is the only filter, no vendor), GetPreheatLog `:725`.
  - `server/v2.0/handler/retention.go`: OperateRetentionExecution `:277`, ListRetentionTasks `:326`, GetRetentionTaskLog `:353`.
  - Sinks: `controller/task/controller.go` `GetLog(id)` → `c.mgr.GetLog(ctx, id)`; `pkg/task/execution.go` `Stop(id)`; `controller/retention/controller.go:257-270, 363-364`.
- Evidence: `l, err := api.taskCtl.GetLog(ctx, params.TaskID)`, after `RequireProjectAccess(ctx, params.ProjectName, rbac.ActionRead, rbac.ResourcePreatPolicy)`.
- Mapping: CWE-639, CWE-285; API1 and API5:2023 (BFLA); ASVS V8.2.
- Chain:
  - reach: as in C7;
  - act: `GET /projects/A/preheat/policies/p/executions/{eid}/tasks/{tid}/logs` with any task ID, or `PATCH …/executions/{eid}` with `{"status":"Stopped"}`;
  - boundary: the tenant boundary, and also the tenant-to-system-admin boundary, because GC and replication are admin-only functions;
  - channel: the response body.
- Impact:
  - read job logs of any project or system job;
  - stop a running GC, replication or scan-all execution started by the system admin;
  - list another project's retention tasks (repository names, counts).
- Correction from the refuter, verified at `controller/retention/controller.go:324`: ListRetentionTasks is filtered to `VendorType=Retention`, so that one endpoint reaches other projects' retention tasks only, not system jobs. The preheat ListTasks has no such filter.
- Remediation: in each handler, load the execution (and the task's execution), and require `exec.VendorType == job.P2PPreheat` (or Retention) and `exec.VendorID == policy.ID` of the policy authorized from the path, before Get, Stop, List or GetLog.
- Effort: small.
- Reproduction (static read path): `preheat.go:721` RequireProjectAccess(A) → `:725` `taskCtl.GetLog(TaskID)` → `controller/task/controller.go:76` → `pkg/task/task.go:233-238`, which reads the log by bare task ID.
- Refutation: **CONFIRMED, 8/10**, with the correction above. Self-sweep: every handler that takes `Eid`/`Tid`/`ExecutionID`/`TaskID` was checked. replication.go and gc.go take IDs too, but they are system-access only, so they are not cross-tenant.

**H-3: Preheat policy overwrite across projects**
- Severity: **High.**
- Location: `server/v2.0/handler/preheat.go:257-272`. The model takes ID and ProjectID from the body (`:469, :472`). `controller/p2p/preheat/controller.go:334, 398`. `pkg/p2p/preheat/dao/policy/dao.go:89` is `ormer.Update(schema)` with no column list, so every column is written, including `project_id`.
- Evidence: `policy, err := convertParamPolicyToModelPolicy(params.Policy)` → `api.preheatCtl.UpdatePolicy(ctx, policy)`. Neither `params.PreheatPolicyName` nor the authorized project constrains the update.
- Mapping: CWE-639; API1:2023.
- Chain: reach (C7) → `PUT /projects/A/preheat/policies/x` with body `{"id": <B's id>, "project_id": <any>, …}` → B's policy is rewritten (filters, trigger, provider, enabled, owning project) across the tenant boundary.
- Impact: another tenant's preheat policy is disabled, re-targeted, or moved out of their project; its cron schedule is changed.
- Remediation: `p, _ := GetPolicyByName(ctx, project.ProjectID, params.PreheatPolicyName)`; then `policy.ID = p.ID; policy.ProjectID = project.ProjectID`.
- Effort: small.
- Reproduction: the read path above.
- Refutation: **CONFIRMED, 9/10**.

**H-4: Immutability rules deletable and rewritable across projects**
- Severity: **High.** This disables another tenant's integrity control. Reachable by projectAdmin and also by maintainer (`rbac_role.go:166-169`).
- Location: `server/v2.0/handler/immutable.go:62` (Delete by path ID), `:76-84` (Update uses the body `ID`; the path `ImmutableRuleID` is ignored). `controller/immutable/controller.go:59-70`. `pkg/immutable/dao/dao.go:53` (`ormer.Update(ir, "TagFilter")`, so the forced ProjectID is never written or compared), `:69-70` (toggle Disabled by ID), `:124-126` (delete by ID).
- Mapping: CWE-639; API1:2023.
- Chain: reach (C7) → `DELETE /projects/A/immutabletagrules/{B's id}`, or `PUT` with a body `{"id":…, "disabled":true}` → B's rule is gone or disabled → B's protected tags become overwritable by B's own pushers. The attacker still cannot push into B; the impact is the removed control.
- Remediation: `m0 := GetImmutableRule(id); if m0.ProjectID != projectID → 404`; use `params.ImmutableRuleID`.
- Effort: small.
- Refutation: **CONFIRMED, 9/10**.

**H-5: Retention policy overwrite: authorization uses the request body, not the stored object**
- Severity: **High.** Also reachable by maintainer.
- Location: `server/v2.0/handler/retention.go:196-214`. `p.ID = params.ID` at `:198`. `requireAccess(ctx, p, …)` at `:205` reads `p.Scope.Reference` from the *body* (`:360-367`). `controller/retention/controller.go:127,162` loads p0 but never compares scopes.
- Chain: `PUT /retentions/{B's id}` with body scope = project A → the check passes for A → B's stored policy data is overwritten (rules, trigger, scope JSON).
- Impact: B's retention policy is neutralised or corrupted, and B's schedule is changed. The refuter notes, and I agree, that this does *not* let the attacker delete B's images: the rewritten scope points at A.
- Remediation: `p0, err := retentionCtl.GetRetention(ctx, params.ID)`; `requireAccess(ctx, p0, ActionUpdate)`; reject when `p.Scope != p0.Scope`.
- Effort: small.
- Refutation: **CONFIRMED, 9/10**. Sweep: the other retention handlers authorize against the *stored* policy (`:133-137, :231-235, :247-251`). Only Create and Update use the body, and Create is correct because it creates.

**H-6: Robot account update authorized against the body namespace**
- Severity: **High.** The deciding assumption is that the attacker knows or guesses the target robot's ID and stored name (`robot$<project>+<name>`). The name pattern is predictable; the error at `:291-292` is reachable only after the authorization check passes, and it gives a guessing oracle. Rate **Medium** if robot names are random.
- Location: `server/v2.0/handler/robot.go:287` (requireAccess on `params.Robot.Permissions[0].Namespace`), `:291`, `:307-313`. `controller/robot/controller.go` Update writes disabled/duration/expiresat, then deletes and recreates permissions. Contrast `RefreshSec` at `robot.go:220`, which correctly uses the stored `r.ProjectID`.
- Impact: B's CI robot is disabled, its expiry is set to never or to now, or its permissions are replaced with scope A, which strips its access to B. Escalation into B is not possible (the new namespace must be A).
- Mapping: CWE-639; API1:2023.
- Remediation: `requireAccess(ctx, r.Level, r.ProjectID, rbac.ActionUpdate)` on the stored robot, and reject when the body namespace ≠ the stored project.
- Effort: small.
- Refutation: **CONFIRMED, 8/10**.

The refuter also confirmed precondition **C7** (9/10): the default `ProCrtRestrEveryone`, and the creating owner is added as projectAdmin (`pkg/project/dao/dao.go:75-76`).

**Weaker-form disclosure.** The six Highs got one independent read-only refuter (one agent, one lens set). The standard in `sota/rules/03` §4a is several refuters with distinct lenses, and ideally a runnable PoC; neither was done. No High was executed against a live instance. If any of these is load-bearing for a decision, escalate to `/sota-deep-audit`. Every Medium and below got **self-refutation only**.

### Medium evidence

**M-1: Icon "≤1MB" size check is dead, and icons are decoded without bounds by an unauthenticated endpoint (DoS of harbor-core)**
- `controller/artifact/annotation/v1alpha1.go:83-88`: `ioutil.ReadAll(io.LimitReader(icon, 1<<20))` and then `if err == io.EOF`. `ReadAll` never returns `io.EOF`, so an oversize icon is silently truncated and accepted. This is a silent control failure (`sota-code-security` rules/10: truncation into an inspector).
- `controller/icon/controller.go:129,136`: `PullBlob` → `image.Decode(iconFile)`, with no `DecodeConfig` dimension cap.
- `server/v2.0/handler/icon.go` GetIcon: no Require* call (census: 1 of 25 operations with no visible check).
- Measured, 3/3 identical runs (`scratchpad/auditeval/w6probe/main.go`, go1.27.1 stdlib, `run1-3.txt`):
  - `limit-probe: read=1048576 err=<nil> errIsEOF=false`, so the check never fires;
  - a 4000×4000 PNG of 62,112 bytes costs 61 MiB to decode;
  - a 12000×12000 PNG of 558,244 bytes costs **549 MiB**;
  - both are under the 1 MB limit even if the limit worked.
- Chain:
  - push leg: any user who can push to a project (C7) pushes an artifact whose layer has the `v1alpha1.icon` annotation;
  - trigger leg: anyone, unauthenticated, GETs `/api/v2.0/icons/{digest}`, or the UI loads it;
  - result: core memory exhaustion, which is a cross-tenant availability impact.
- Toolchain caveat: the shipped binary uses go1.17.7, whose png decoder also allocates the full image up front. That is **needs verification on 1.17**; the probe ran on 1.27.
- CWE-409/400, API4:2023.
- Fix: `LimitReader(icon, max+1)` with `len(data) > max` treated as an error; `image.DecodeConfig` with a width×height cap before `Decode`; require authentication on GetIcon.

**M-2: Unbounded reads of attacker-controlled bodies in core**
- Sites:
  - `chart.go:87` reads the whole chart layer, then passes it to helm `loader.LoadArchive` (via `pkg/chart/operator.go:91`; helm v3.7.1, see M-6);
  - `blob/put_manifest.go:37,67`, `cosign/cosign.go:77` and `quota/util.go:52` read the PUT manifest body with no `MaxBytesReader`.
- `sota-golang` rules/04 rates an unbounded body read **HIGH by default**. I rate it **Medium on the chain**: it needs push permission, and the impact is availability only.
- Positive contrast: `v1alpha1.go:83` shows the authors use `LimitReader` elsewhere.
- Fix: cap manifests at 4 MiB and chart layers at a configurable limit, and upgrade helm.

**M-3: No abuse control on credential checks**
- `basicAuth.Generate`, `robot.Generate` (one PBKDF2 per request, `common/utils/encrypt.go:49-50`) and `oidcCli.Generate` all run on any request carrying Basic credentials, with no throttle or lockout.
- First method: a sweep for `rate.?limit|throttl|x/time/rate|lockout|too ?many` over server and controller returned 4 hits, all in `controller/replication/transfer/iothrottler.go` (replication bandwidth), none on authentication.
- Second, independent method: `limit_req|limit_conn` in the shipped nginx templates (4 files) returned 0 hits.
- Positive control for the instrument: `Bearer` returned 3 hits in the same scope.
- CWE-307, API4:2023. This is principle 5(a), and it is not documented as handled elsewhere.

**M-4: Session carries a snapshot of the user; privilege changes are not enforced on live sessions**
- `session.go:37-47` builds `local.NewSecurityContext(&user)` from `store.Get("user")`. `IsSysAdmin` reads `user.SysAdminFlag` from that snapshot (`common/security/local/context.go`).
- `SetSysAdmin`, `DeleteUser` and `UpdateUserPassword` (`user.go:177-336`; `controller/user/controller.go:200-201`) do not touch sessions (0 `session` references in `controller/user/controller.go`).
- A demoted admin, deleted user or compromised session therefore keeps the old privileges until the session expires (the session lifetime is configured in `core/main.go`, out of scope).
- CWE-613; ASVS V7.4.

**M-5: Webhook target SSRF**
- `validateTargets` (`notification_policy.go:223-241`) allows any http or https host. The comment *"Prevent SSRF security issue #3755"* only strips the query and userinfo (`:233`).
- Context, read out of scope: jobservice posts with a default `http.Client` (`jobservice/job/impl/notification/http_helper.go:27-32`). It has no dial-time IP check, follows redirects, has no timeout, and its "insecure" client is selectable by a non-admin through `skip_cert_verify`.
- Reach: any projectAdmin (C7). The SSRF is blind except for delivery status.
- CWE-918, API7:2023. The inert-comment aspect is a rules/10 "control that does not do what it says".

**M-6: Vulnerable dependency set (src/go.mod).** One row per module@version with Critical/High advisories (trivy). Reachability is from govulncheck symbol analysis over 84 of 89 in-scope packages (the API handler packages are excluded, see the scanner caveat). "Symbol" means a vulnerable function is on the call graph from in-scope code.

| module@version | C/H advisories (trivy) | fixed in (trivy) | reachable? / how checked | rating in context |
|---|---|---|---|---|
| github.com/golang-jwt/jwt/v4@v4.1.0 | H: CVE-2025-30204 (also GO-2024-3250 / CVE-2024-51744 from govulncheck) | 4.5.2 | **symbol**: `ParseWithClaims` / `Parser.ParseUnverified` from `server/middleware/security/v2_token.go:50`, pre-authentication on `/v2` bearer tokens | **High**: an unauthenticated memory-amplification DoS on every `/v2` request |
| github.com/gorilla/csrf@v1.6.2 | GO-2025-3607 / CVE-2025-24358 (govulncheck; trivy did not list it as C/H) | 1.7.3 | **symbol**: `csrf.ServeHTTP` via `server/middleware/csrf/csrf.go:68` | Medium: the Referer check is broken under TLS; needs a same-site attacker origin |
| golang.org/x/net@v0.0.0-20211013171255 | H×11: CVE-2021-44716, 2022-27664, 2022-41723, 2023-39325, 2023-45288, 2024-45338, 2026-25681, 2026-27136, 2026-33814, 2026-39821, 2026-46600 | 0.7.0 … 0.56.0 | **symbol** for CVE-2022-41723, 2023-45288, 2026-33814, 2026-39821; whether core's HTTP/2 server uses x/net or the stdlib-bundled h2 was **not checked** | High where core terminates HTTP/2 directly; Medium behind nginx |
| helm.sh/helm/v3@v3.7.1 | H: CVE-2024-26147, CVE-2025-53547 | 3.14.2 / 3.17.4 / 3.18.4 | **symbol** for CVE-2024-25620, 2025-32386, 2025-32387 (`Chart.Validate`, loader) from `controller/artifact/processor/chart/chart.go:92`; the two trivy Highs were not traced | Medium: chart-archive DoS by a pusher (joins M-2) |
| github.com/beego/beego@v1.12.9 | C: CVE-2021-27116, CVE-2021-27117 (which of the five ids is C vs H is not split here); H: CVE-2021-30080, CVE-2022-31836, CVE-2025-30223 | 1.12.11 / 2.0.2 | symbol-level for GO-2024-3331 and GO-2025-3585 via `init`/`utils.FileExists` only; vulnerable *behaviour* (RenderForm, file cache) **not shown reachable** | Medium (framework underpinning sessions; ledger D-STALE) |
| github.com/docker/docker@v20.10.9+incompatible | C: CVE-2024-41110; H: CVE-2023-28840, 2026-41567, 2026-42306 | 20.10.24 / 25.0.6 / … | govulncheck "symbol" only through package `init` or helpers (`pkg/homedir.Get` from `v2auth/auth.go:155` trace). The advisories concern the daemon/AuthZ plugin/swarm, which Harbor does not run as a client library | Low (not exploitable as used; upgrade for hygiene). Triage claim with its evidence: the trace tops out at `init`/helper symbols. |
| github.com/containerd/containerd@v1.5.10 | H: CVE-2024-25621 | 1.7.29 | symbol via `init` and `remotes/docker` helpers (trace from `controller/retention/controller.go:27`, `controller/p2p/preheat/controller.go:307`); the advisories concern the CRI server | Low |
| google.golang.org/grpc@v1.41.0 | C: one of CVE-2026-33186 / CVE-2026-84304 / CVE-2026-84445 / GHSA-hrxh-6v49-42gf / GHSA-m425-mq94-257g (trivy reports C=1, H=4 over these five ids; which is Critical was not split out) | 1.82.1 … 1.85.0-dev | package-only (imported, vulnerable symbol not called from in-scope roots) | Medium, needs verification (OTLP exporter path, out of scope) |
| golang.org/x/crypto@v0.0.0-20210921155107 | H×15: CVE-2021-43565, 2022-27191, 2024-45337, 2025-22869, 2025-47913, 2026-39828…39832, 2026-39835, 2026-42508, 2026-46595, 2026-46597, 2026-56854 | 0.43.0 / 0.52.0 / 0.55.0 | 1 symbol (GO-2026-5932 openpgp, via `init`), the rest module/package-level | Medium (SSH-server CVEs not applicable; openpgp unmaintained) |
| golang.org/x/text@v0.3.7 | H: CVE-2022-32149, CVE-2026-56852 | 0.3.8 / 0.39.0 | **symbol**: CVE-2026-56852 `norm.Form.QuickSpan` from `controller/quota/controller.go:232` | Medium (infinite loop on invalid input) |
| github.com/prometheus/client_golang@v1.11.0 | H: CVE-2022-21698 | 1.11.1 | **symbol**: `promhttp.sanitizeMethod`; the metrics middleware path was **not checked** to see whether the method is attacker-chosen | Medium, needs verification |
| github.com/jackc/pgx/v4@v4.12.0 | H: CVE-2024-27289, CVE-2024-27304 | 4.18.2 | not reached from in-scope roots (the driver is wired in out-of-scope packages) | Medium, needs verification (SQL-injection class on the DB driver) |
| github.com/jackc/pgproto3/v2@v2.1.1 | H: CVE-2026-32286, GHSA-7jwh-3vrq-q3m8 | 2.3.3 | package-only | Medium, needs verification |
| github.com/distribution/distribution@v2.8.0+incompatible | H: CVE-2026-33540, CVE-2026-35172 | none listed | module-only | Medium, needs verification |
| github.com/docker/cli@v20.10.7+incompatible | H: CVE-2025-15558 | 29.2.0 | module-only | Low |
| github.com/sirupsen/logrus@v1.8.1 | H: CVE-2025-65637 | 1.8.3 / 1.9.1 / 1.9.3 | package-only | Low |
| go.opentelemetry.io/contrib/…/otelhttp@v0.22.0 | H: CVE-2023-45142 | 0.44.0 | package-only | Medium (unbounded metric cardinality from request attributes) |
| go.opentelemetry.io/contrib/…/otelmux@v0.22.0 | H: CVE-2023-45142 | 0.44.0 | not in govulncheck output | Low |
| golang.org/x/oauth2@v0.0.0-20210628180205 | H: CVE-2025-22868 | 0.27.0 | module-only | Low |
| gopkg.in/yaml.v3@v3.0.0-20210107192922 | H: CVE-2022-28948 | 3.0.1 | package-only | Medium, needs verification |

Medium and Low advisories: 61 Medium, 6 Low and 2 unknown, summarised by count only. The fixed versions are trivy's; they were not re-verified upstream (network disallowed).

**M-7: Job status hooks unauthenticated in process**
- `job_status_hook.go:37-60` decodes and applies any `job.StatusChange`. The scheduler check-in processor (`pkg/scheduler/callback.go:35`) can trigger scheduled callbacks.
- The only control is nginx `location /service/notifications { return 404; }`. That is a network-position control.
- Precondition: knowledge of a job ID, which appears in task listings, e.g. retention tasks.
- CWE-306.

**M-8: No cross-project authorization tests**
- Handler test files exist for 12 of 36 handler files. In `preheat_test.go` and `robot_test.go`, a grep for `Forbidden|403|other project|cross` found 0 matches; the instrument works (it matched 7 `Test` functions in `preheat_test.go`). There are no test files at all for retention, immutable, notification_policy, label or member.
- API e2e (`tests/apitests/python`): 17 expected-403/404 assertions across 9 files. None asserts a cross-project object-ID denial; the webhook one is a 404 after the caller's own delete.
- This is why H-1 to H-6 could ship.

---

## 6. Present is not applied (silent-control pass)
- **Icon 1 MB limit**: present, inert (M-1, demonstrated 3/3).
- **"Prevent SSRF #3755"** (`notification_policy.go:232-233`): present, does not prevent SSRF (M-5).
- **`Prepare` error handling** (`artifact.go:72`, `repository.go:59`, `scan.go:44`): the `SendError` responder is built and discarded, so a parameter-unescape failure proceeds as success (L-1).
- **`RequireProjectAccess`, population count**: guards the path project at every project-scoped operation, but is credited by the design with guarding sub-objects. In the six families above the sub-object is unguarded. Census denominator: 173 operations. 25 have no Require* call in their first lines. Of those 25, the retention, label, robot-Create, ListAuditLogs, ListAllRepositories and GetConfigurations bodies were read in full; ListProjects, Search, ping, health and systeminfo were read only as far as their access checks. 19 authorize later or by design (retention ×8 and label ×5 after loading the object, robot Create, ListProjects, ListAllRepositories, Search, ListAuditLogs, GetConfigurations). 6 are public by design: ping, health, systeminfo ×2, retention metadata, and **icon (L-8)**.
- **The `/v2` gate**: deny-by-default verified in code; the blob-mount source repository is checked for pull (`v2auth/access.go`). The depth of that gate was not exercised at runtime.
- **CSRF**: present and active when a session cookie is carried (`session.go` → `csrfSkipper`). Its effect was not exercised; the library advisory is in M-6.

## 7. History and knowledge stores
- Git history: **not reached** (`.git` removed). No `git log -G` variant hunt was possible.
- No agent/IDE knowledge files in the workspace (`AGENTS.md`/`CLAUDE.md`/`.cursorrules`/`.idea`/`.vscode`: 0 hits; positive control `README.md`: 2 hits).

## 8. Questions (operator unavailable: defaults chosen, audit continued)
1. **Is this instance internet-facing with non-admin user accounts?**
   - Options: (a) yes, which gives the ratings as written; (b) internal, trusted users only, which makes H-1 to H-6 Medium.
   - Default and recommendation: **(a)**. Self-service project creation is on by default, so every user is a potential attacker.
2. **Is harbor-core reachable without the shipped nginx (Helm/ingress, sidecars)?**
   - Options: (a) only via the shipped nginx, so M-7 is Low; (b) reachable directly, so M-7 is Medium, plus HTTP/2 exposure for x/net.
   - Default: **(a)**. Recommendation: add in-process authentication anyway; it costs one check.
3. **Fix in place or upgrade?**
   - Options: (a) upgrade to a maintained Harbor release, which closes classes upstream, needs a migration window, and was not verified here; (b) patch the six handlers locally, which is a fork you must carry; (c) both, patching now and upgrading on schedule.
   - Recommendation: **(c)**. The fixes are small and well-bounded, and the dependency rot (M-6) cannot be patched locally.
4. **Is `project_creation_restriction` set to `adminonly` in your deployment?**
   - Default: `everyone` (the code default). If it is `adminonly`, H-1 to H-6 need an existing projectAdmin or maintainer; they remain High as insider cross-tenant attacks.
5. **Should the stack profile apply to this upstream repository?**
   - Default: no. Profile deviations are not raised.

## 9. Remediation roadmap (risk reduction per effort)
1. **One small PR, the object-binding fix across H-1 to H-6 plus L-5.** Add a helper `requireOwned(ctx, storedProjectID, authorizedProjectID)` and call it in the 14 call sites listed above. Add the M-8 deny-matrix test in the same PR, so the fix is pinned. *Small.*
2. **The M-1 and M-2 DoS caps** (`LimitReader` n+1, `DecodeConfig` cap, `MaxBytesReader` on manifests, authentication on GetIcon). *Small.*
3. **Dependency upgrades, in this order:** golang-jwt (pre-auth), x/net, helm, gorilla/csrf, x/text. Add a govulncheck CI gate (golang top-10 #10). *Medium.*
4. **Session revocation and per-request user refresh** (M-4), plus **authentication throttling** (M-3). *Medium.*
5. **Webhook SSRF guard** (dial-time IP block, no redirects, timeout) and admin-only `skip_cert_verify` (M-5). *Medium.*
6. **Hygiene:** L-1 to L-4, L-6 to L-10, and the I items. *Small each.*
7. **Strategic:** beego v1 to a maintained framework, and Go 1.17 to a supported toolchain (ledger STALE items). *Large.*

## 10. Positive observations (with evidence of effect where obtained)
- **JWT algorithm pinning** (`pkg/token/token.go`: `token.Method.Alg() != opt.SignMethod.Alg()` returns an error) and the audience check (`v2_token.go`). Read; not exercised.
- **`/v2` deny-by-default and blob-mount source check** (`v2auth/access.go`). Read.
- **The ORM query keyword allowlist** (`lib/orm/query.go:121-140` `meta.Filterable`) stops user `q=` keys reaching arbitrary columns. Read.
- **Correct object binding in members, robot v1 and the project CVE allowlist** (`pkg/member/dao/dao.go:171,181`; `robotV1.go:122`; `project.go` UpdateProject requires `CVEAllowlist.ProjectID == p.ProjectID`). These are the template for the fix.
- **The project-metadata key allowlist** (`project_metadata.go` validate).
- **5xx error bodies are generic**; details are logged only (`lib/http/error.go` SendError).
- **gitleaks found no secrets in scope**, effect-checked with a planted positive control.

## Appendix: triage of tool output
- gosec:
  - G404 at `controller/registry/controller.go:218` is a false positive: health-check jitter, not security-sensitive.
  - G101 at `csrf.go:21` is a false positive: a header name.
  - G118 at `controller/replication/execution.go:120`: intentional detached job with `recover`, Info.
  - G601 at `util.go:35` became L-7.
  - G104×62 are covered by L-1; 32 of them are `Subscribe` errors ignored in `controller/event/handler/init.go`.
  - No `#nosec` suppressions in scope (`nosec: 0`).
- govulncheck: 35 symbol-level advisories. The docker/containerd "symbol" hits whose trace starts at package `init` were triaged as not exploitable as used (evidence: the trace tops out at `init`/helper symbols; the advisories concern daemon/CRI server code).
- Out-of-scope observations, not findings:
  - gitleaks over all of `src` reported 11 hits (redacted), all in test fixtures, plus `jobservice/server.key`. Needs verification whether that is a fixture.
  - The CI CodeQL workflow uses `codeql-action@v1`.
  - jobservice's webhook client has no timeout.

---

One line for `/sota-report`. `sota-golang` rules/04 rates "unbounded body read" **HIGH** with no chain qualifier, but `sota/rules/03` §1 rates the same push-authenticated DoS Medium. The scoped-table rule (§1 rule 5) settled it, but rules/04's severity guide does not say it is a refinement. That is worth reporting.
