# SOTA audit: Harbor `src/server` + `src/controller` + `src/go.mod` (tree `v2.5.1`)

Audit date 2026-10-06. Mode: `/sota-audit` (single context, light threat model) plus one
independent refuter agent for the Highs. No fixes were made; the workspace was not edited.

## Posture (one line)

**Not ready**: an ordinary authenticated user (default `project_creation_restriction=everyone`,
so anyone with an account can be project admin of a project they create) can read other
projects' webhook credentials, read any background-job log, and delete or tamper with other
projects' webhook, retention and immutability policies. The root cause is one class:
object IDs are not bound to the project that was authorized (BOLA, CWE-639).

Counts after triage: High 7 · Medium 9 · Low 8 · Info 4. All 7 Highs survived an independent refuter agent (confidence 0.85-0.95); two had their impact narrowed and two need only the maintainer role (section 11).

---

## 1. Scope and pinning

| Item | Value |
|---|---|
| Tree identity | `VERSION` = `v2.5.1` (no `.git`; `git rev-parse HEAD` -> `fatal: not a git repository`) |
| Dirty flag | not applicable (no git); every finding is pinned to "tree v2.5.1 as found in ws/w3 on 2026-10-06" |
| In scope | 232 non-test `.go` files, 31,877 lines (`find src/server src/controller -name '*.go' ! -name '*_test.go'`; gosec reported the same 232 files / 31,877 lines, so the two denominators reconcile) + `src/go.mod` (219 packages per osv-scanner) |
| Whole repo, for size | 8,148 files outside dot-dirs (context only) |
| Diff scope | not reachable: no git history, so no base, no branch diff, no dependents-of-a-diff |
| Excluded (stated, not widened later) | `src/pkg`, `src/lib`, `src/common`, `src/core`, `src/jobservice`, `src/portal`, `make/`, `tests/`, `.github/`. These were **read for context** (to follow a call to its DAO or to check a deployment assumption) but no finding is filed against them |
| Partitioning | crown jewels first: authn middleware (`server/middleware/security`, `v2auth`, `csrf`) -> v2.0 handlers that take object IDs (authz) -> registry/v2 middleware chain (policy enforcement) -> artifact ingestion (`controller/artifact`, `controller/icon`) -> remaining controllers (sweeps only) |
| Yardstick | OWASP API Security Top 10 2023 (API1 BOLA, API3 BOPLA, API4 resource consumption, API5 BFLA, API7 SSRF), OWASP Top 10 2021 (A01, A04, A06, A10), ASVS 4.0.3 **Level 2** (V4 access control, V5 validation, V12 files/resources, V14 config), CWE ids per finding. No LLM/agent surface exists in scope, so the LLM lists do not apply |
| Stack profile | `~/.claude/profiles/<owner>.md` exists. This is an upstream third-party codebase, not one of the profile owner's repos, so the profile is **not** applied as an audit baseline (principle 4 scopes it to the owner's repos). Its only Go clause (golangci-lint with gosec/errcheck) is noted under Info as a gap anyway |

Questions the command says to ask, recorded with the default I chose (operator unavailable):

1. *Scope* - pre-agreed; not asked.
2. *Is core reachable without the bundled nginx (Helm ingress, direct pod access)?* It decides M1's severity.
   Options: (a) nginx-only deployments, M1 stays Medium (in-cluster lateral only); (b) any ingress
   that routes `/service/` to core, M1 becomes High (unauthenticated task-state forgery);
   (c) unknown, treat as Medium and flag. **Default chosen: (c)**, because the Helm chart is
   not in this tree and I would rather leave it open than assume either way.
3. *Is `project_creation_restriction` left at its default `everyone`?* It decides whether the
   BOLA class is reachable by **any** account or only by existing project admins. Options: (a) yes,
   High stands for any authenticated user; (b) `adminonly`, still High, because any existing project
   admin can cross into every other project; (c) treat as (b). **Default: (b)/(c)**. The severity
   is High either way. The default value was read from `src/lib/config/metadata/metadatalist.go:117`.
4. *Is the cosign User-Agent bypass (M4) an accepted trade-off?* Options: (a) accepted, so downgrade to
   Low and document it; (b) not accepted, so bind the bypass to a cosign-specific token scope; (c) remove
   the bypass and require signature push without a prior gated pull. **Default: treat as unaccepted (b)**.
   Nothing in the tree documents it as accepted, and this choice materially affects security posture.

---

## 2. Coverage (per rules file, as the audit ended)

Legend: **walked** = audit checklist taken item by item; **targeted** = applied through a named sweep or
manual pass on the items with surface in scope, not item by item; **n/a** = no surface (reason given);
**not walked** = surface exists but nobody opened the checklist, which is a hole in this audit.

| Surface found | Owning skill | Rules file | Status | Reason / what ran |
|---|---|---|---|---|
| Go code (all) | sota-golang | 01-errors | targeted | gosec G104 sweep (60 unhandled-error sites); `controller/event/handler/init.go:24-70` triaged (L7) |
| | | 02-design | not walked | design idioms are not a security surface here and were deprioritized. Hole |
| | | 03-concurrency | walked | go.mod `go 1.17` means pre-1.22 loop-var semantics. Range-loop capture sweep: 1 real site of 232 files (M9); fire-and-forget `go func` in `controller/replication/execution.go:120` reviewed (recover present, own ctx, intended); `sync.Map` unbounded in icon cache (M2); `go test -race` is present in `tests/coverage4gotest.sh:32` |
| | | 04-http-services | walked | naked-server/timeouts live in `src/core/main.go` (out of scope, so **not reached**); body hygiene -> M3; path-based authz on raw path -> `oidc_cli.go:76-104`, `csrf.go:73-82` read after `mergeslash`, no bypass found; CSRF layer present (gorilla/csrf, SameSite=Strict); cookie defaults set in beego config (out of scope) |
| | | 05-security | walked | SQLi: no string-built SQL in scope (only `orm.Raw("SELECT 1")`); exec/unsafe: none; TLS InsecureSkipVerify: none in scope; SSRF -> M5; CSPRNG: `math/rand` only for health-check jitter (`controller/registry/controller.go:218`, dismissed); secrets in repo -> gitleaks clean in scope |
| | | 06-performance | n/a | no performance question in scope; resource-exhaustion items moved to M2/M3 |
| | | 07-tooling-ci | targeted | CI has golint/govet/gofmt + CodeQL, no gosec/govulncheck (I2) |
| | | 08-supply-chain | walked | go.sum present (2,157 lines); vendor/ present; SCA run (M6); GODEBUG overrides: none in scope |
| Authn/authz/session code | sota-code-security | 02-authentication | targeted | 9 security-context generators read in full (`server/middleware/security/*.go`) |
| | | 03-authorization | walked | item 2 (ownership predicate in every by-ID lookup) **not met**: H1-H7, M7, L5, L6. Item 1 (single default-deny layer) **not met**: per-handler checks, 175 ops (I1). Item "cross-tenant test suite" **not met** (I3). Item "404 not 403 for invisible objects" **not met** (L3) |
| | | 04-cryptography | targeted | robot secret PBKDF2-SHA256 4096 iters, 16-byte output (L4) |
| | | 05-web-security | targeted | CSRF only (gorilla/csrf v1.6.2, M6 advisory); CORS/headers set outside scope |
| | | 06-memory-resource-safety | targeted | M2, M3, L8 |
| | | 07-data-exposure | targeted | H1 (auth_header returned), csrf.go:57 (L1), username logging on failed login (accepted, normal) |
| | | 08-llm-ai-security | n/a | no LLM/agent surface in scope |
| | | 09-untrusted-data-ingestion | walked | image decode without `DecodeConfig` -> M2; every raw read bounded? **not met** -> M3; manifest JSON parsed by distribution (no depth cap, not verified) |
| | | 10-silent-control-failure | walked | falsification question asked of 6 credited controls (section 6 below); M2 (inert size check), M5 (inert SSRF comment), L7 (ignored subscribe errors) |
| | | 11-dead-path-diagnostics | targeted | gate denominators: gosec 232 files, gitleaks 749 KB + 914 KB, govulncheck package set (depth note in section 5) |
| | | 12-verifying-the-verifier | targeted | positive controls run for gitleaks and for every grep sweep (section 5) |
| | | 13-context-dependent-silence | not walked | Hole |
| | | 14-control-not-in-force | walked | population counts: object-scoped authz on ID-taking project handlers (section 6) |
| | | 15-instruments-and-guards | targeted | my own instruments: one zsh no-word-split failure caught and re-run (section 5) |
| | | 16-where-no-ops-hide | not walked | Hole, partly covered by 10/14 |
| | | 17-sessions-and-tokens | targeted | v2 token parse + audience check (`v2_token.go:24-31`) and bearer extraction (`utils.go:23-28`) read; JWT library advisory GO-2024-3250/GO-2025-3553 (M6) |
| | | 18-tamper-evident-logs | not walked | audit log handler is in scope only as a subscriber (L7). Hole |
| | | 19-anti-automation-and-abuse | targeted | no per-account throttle on Basic/robot auth in scope (M8); signup/CAPTCHA/payments items n/a (no such surface) |
| | | 20-browser-response-hardening | n/a | response headers are set in nginx/beego (out of scope) |
| | | 21-file-uploads | targeted | the registry blob/manifest upload path is the upload surface: M2, M3 |
| | | 22-constant-time-comparison | walked | `server/middleware/security/robot.go:57` (L4); secret/proxy-cache secret compare in `pkg/` (out of scope, not reached) |
| | | 23-llm-platform-supply-chain | n/a | no LLM surface |
| HTTP API (v2.0 + OCI v2) | sota-api-design | 01-rest-http-design | not walked | Hole (semantic REST issues are not security-blocking) |
| | | 02-versioning-evolution | n/a | not a security question at this scope |
| | | 03-graphql / 04-grpc / 05-realtime | n/a | no GraphQL/gRPC/websocket server in scope |
| | | 06-webhooks | walked | sender side: SSRF defenses **not met** (M5); auth header stored and returned in clear (H1); HMAC signing **not met** (Info, target receives a static auth header only); delivery logs present (`notification_job.go`) |
| | | 07-security-operations | targeted | rate limiting absent in scope (M8); BOLA (H-class) |
| Threat model | sota-threat-modeling | 06-audit-reconstruction | targeted | the **light** model in section 3 ran; the full reconstruction (deep audit) did not |
| | | 01-05 | n/a | design-time files, not an audit target |
| Credentials | sota-secrets-management | 03-application-patterns, 04-detection | targeted | gitleaks over scope (clean, positive control passed); webhook auth headers stored and returned in plaintext (H1); CSRF key logged (L1) |
| | | 01, 02, 05 | not walked | key storage backends are outside scope. Hole only in the sense that nobody looked |
| Identity infra | sota-identity-access | 03-authorization-models | targeted | RBAC model read (`common/rbac/project/rbac_role.go`) to establish which role reaches each H finding |
| | | 01, 02, 04-07 | n/a | OIDC/LDAP/auth-proxy client code is in `pkg/` (out of scope); in-scope generators reviewed under code-security 02 |
| Test suite (always) | sota-testing | 09-security-testing | walked | cross-tenant/IDOR test per by-ID resource **not met** (I3); SSRF tests on webhook surface **not met**; SAST+SCA in PR gate **not met** (I2) |
| | | 07-suite-health-and-ci | targeted | race detector present; 12 of 36 handler files have unit tests |
| | | 01-06, 08 | not walked | Hole |
| Personal data (user records, emails, logs with usernames/IPs) | sota-privacy-compliance | 01, 02 | targeted | usernames + client IPs logged on auth failure (`basic_auth.go:72`), legitimate; IP spoofable (L2) |
| | | 03-06 | not walked | DSAR/retention live in `pkg/` and `src/core`. Hole |
| CI / supply chain | sota-devsecops | 03-dependencies, 13-vulnerability-remediation | walked | M6 |
| | | 01, 05, 09 | targeted | I2 (context only, `.github/` out of scope for findings) |
| | | others | n/a | containers/IaC/registry-ops out of scope |
| Async/background jobs | sota-async-concurrency | 02-correctness, 07-audit-bug-catalog | targeted | M9; job-status hook ordering (M1) |
| | | others | not walked | Hole |
| Logging/metrics | sota-observability | 01-structured-logging | targeted | L1, L2; metric middleware present |
| | | others | not walked | Hole |
| Detection posture | sota-detection-engineering | all | not walked | no detection content in scope; noted as a hole, not as clean |
| Architecture | sota-architecture | 07-anti-patterns | targeted | decision ledger (section 7) |
| DB access | sota-databases | 03, 06 | targeted | queries go through beego ORM + `q.Query` keywords; no raw SQL in scope; tenant predicate absence is the H class |
| My own commands | sota-shell-scripting | 06 | walked | see section 5 (one sweep failed loudly on zsh word splitting and was re-run through `xargs`) |
| Performance | sota-performance | all | n/a | no performance question in the agreed scope |
| Frontend, mobile, data-eng, ML, LLM, k8s, cloud, network, confidential, sandboxing | (various) | all | n/a | no such surface in the scoped files |

**Not reached (stated plainly):** naked-server timeouts and session-cookie flags live in `src/core/main.go`
and beego config, outside scope, so they were not checked. The swagger-generated `server/v2.0/restapi`
package is absent from the tree (it is generated at build time), so nothing that runs the v2.0 handlers
was exercised; every handler finding is static. No git history, so no history scan, no `git log -G` and
no churn ordering.

---

## 3. Light threat model (boundary map built from code)

| Entry point | Authn / authz checkpoint | Asset reached | Privilege it runs with |
|---|---|---|---|
| `/api/v2.0/**` (go-swagger handlers) | `server/middleware/security/security.go:47-67` picks the first matching generator (secret, oidcCli, v2Token, idToken, authProxy, robot, basicAuth, session, proxyCacheSecret); authz is **per handler**: `server/v2.0/handler/base.go:105-117` `RequireProjectAccess(projectFromPathOrBody)` | Postgres (all projects), jobservice task logs, Redis | core DB role (all tenants) |
| `/v2/**` OCI registry | `server/middleware/v2auth/auth.go:47-82` (project derived from repo path in `artifactinfo`), then policy middlewares (`vulnerable`, `contenttrust`, `immutable`, `quota`) | registry storage via proxy | core + registry credentials |
| `/service/notifications/**` job status hooks | **none in application** (`server/handler/job_status_hook.go:38-59`); only nginx `location /service/notifications { return 404; }` (`make/photon/prepare/templates/nginx/nginx.http.conf.jinja:200`) | task/execution status, scan check-in data (`pkg/task/hook.go:47-80`) | core DB role |
| `/api/v2.0/icons/{digest}` | none (`server/v2.0/handler/icon.go:37`) | registry blobs of any repo | core |
| Webhook senders (outbound) | target address set by project admin (`notification_policy.go:223-241`) | any network address jobservice can reach | jobservice network position |
| CSRF boundary | `server/middleware/csrf/csrf.go:53-82` (skipped for API paths without a session cookie) | session-authenticated mutations | n/a |

Assumptions the code implies, and what checking them found:

1. *"A caller authorized for project A only touches project A's objects."* **Broken.** At least 8 handlers
   fetch or mutate objects by raw ID after authorizing the caller's own project (H1-H7, M7).
2. *"Only jobservice can reach `/service/notifications`."* **Unverified.** It is true only behind the
   bundled nginx, and nothing in core enforces it (M1).
3. *"Vulnerability prevention and content trust gate every pull."* **Broken for push-capable principals**,
   who can set a `cosign` User-Agent (M4).
4. *"Icons are at most 1 MB."* **Broken.** The check is inert (M2, reproduced).
5. *"Webhooks cannot be used for SSRF (#3755)."* **Broken.** The only mitigation drops the query string and
   fragment; it does not block internal addresses (M5).
6. *"The CSRF key comes from the environment."* Holds; a wrong-length key is logged in clear (L1).

---

## 4. Findings (working table)

Pinned to tree `v2.5.1`. All paths are relative to `src/`. Every `file:line` was re-resolved against the
tree at the end of the audit (section 9).

| # | file:line | rule violated | severity | effort | fix |
|---|---|---|---|---|---|
| H1 | server/v2.0/handler/notification_policy.go:155 | code-security rules/03 (ownership predicate); API1 BOLA; CWE-639 | High | small | load the policy, require `policy.ProjectID == projectID` (404 otherwise); stop returning `auth_header` (write-only field) |
| H2 | server/v2.0/handler/notification_policy.go:143 | same | High | trivial | same ownership check before `Delete` |
| H3 | server/v2.0/handler/notification_policy.go:115-130 | same + API3 (body ID trusted over path ID) | High | small | `policy.ID = params.WebhookPolicyID`; verify the stored policy belongs to `projectID` before `Update` |
| H4 | server/v2.0/handler/preheat.go:725 (also :581, :650, :693, :267) | same | High | small | resolve task -> execution -> policy -> project, and require that project be the authorized one; take policy ID/project from path, not body |
| H5 | server/v2.0/handler/retention.go:353 (also :277, :326, :198-205) | same (maintainer suffices) | High | small | require `task.ExecutionID == Eid` and `execution.VendorID == policyID`; on update, authorize against the **stored** policy's scope, not the body's |
| H6 | server/v2.0/handler/immutable.go:62, :84; controller/immutable/controller.go:60-70 | same (maintainer suffices) | High | small | load the rule, require `rule.ProjectID == projectID` before delete/enable/update |
| H7 | server/v2.0/handler/robot.go:287 | same + API5 (authz on attacker-chosen namespace) | High | small | authorize against the stored robot (`r.Level`, `r.ProjectID`) and require body namespace == stored project |
| M1 | server/handler/job_status_hook.go:45; server/route.go:53-59 | code-security rules/03 item "internal services require service identity"; ASVS V4.1.1 | Medium (High if core is reachable without the nginx rule; needs verification) | medium | require the jobservice secret (`Authorization: Harbor-Secret`) and a solution-user context on all status-hook routes |
| M2 | controller/icon/controller.go:136; controller/artifact/annotation/v1alpha1.go:83-87; server/v2.0/handler/icon.go:37 | code-security rules/09 (DecodeConfig before Decode), rules/10 (inert size check); API4; CWE-400, CWE-770 | Medium | small | `image.DecodeConfig` with a pixel budget before `Decode`; fix the size check (read `1<<20 + 1` and reject on `len > 1<<20`); bound the cache; require authn on `GetIcon` |
| M3 | server/middleware/blob/put_manifest.go:37, :67; server/middleware/quota/util.go:52; server/middleware/cosign/cosign.go:77 | code-security rules/09 (every raw read bounded); API4; CWE-770 | Medium | small | wrap `r.Body` in `http.MaxBytesReader` (manifest cap, for example 4 MiB) once, before the first reader |
| M4 | server/middleware/util/util.go:69-72 | code-security rules/10 and rules/14 (control not in force for a class of principals); CWE-807 | Medium | medium | do not key a policy bypass on `User-Agent`; scope it to the signature-push flow (for example, only the cosign subject-manifest HEAD/GET inside a token that also carries push for the `.sig` tag) |
| M5 | server/v2.0/handler/notification_policy.go:228-233 | api-design rules/06 (SSRF defenses); golang rules/05 §4c; API7; CWE-918 | Medium | medium | resolve-then-pin and block private, loopback, link-local and metadata ranges in the webhook sender; HTTPS-only option; no redirects |
| M6 | go.mod:3 (go 1.17), go.mod:35 (gorilla/csrf v1.6.2), go.mod:31 (golang-jwt v4.1.0), go.mod:71 (helm v3.7.1), go.mod:66 (x/net), Makefile:160 (golang:1.17.7) | devsecops rules/03, rules/13; A06; CWE-1104 | Medium (per-advisory severity needs verification in the full core binary) | large | move to a supported Go toolchain; upgrade the 10 modules govulncheck shows as reachable |
| M7 | server/v2.0/handler/notification_job.go:34 | code-security rules/03; API1 | Medium | trivial | require `policy.ProjectID == projectID` |
| M8 | server/middleware/security/basic_auth.go:59-79; server/middleware/security/robot.go:39-72 | code-security rules/19, api-design rules/07 (rate limiting); ASVS V2.2.1 | Medium (needs verification: `src/core/auth` may hold a per-user lock) | medium | per-account and per-source throttling on failed Basic/robot auth; cache successful robot verification |
| M9 | controller/event/handler/util/util.go:35 | golang rules/03 item 1 (go.mod < 1.22, address of loop variable escaping to async handlers) | Medium (the golang table rates HIGH; router §1 rates Medium because the misrouting stays inside one policy) | trivial | `target := target` before taking `&target`, or raise go.mod to >= 1.22 |
| L1 | server/middleware/csrf/csrf.go:57 | secrets-management rules/03 / code-security rules/07 (secret in logs); CWE-532 | Low | trivial | log the length only |
| L2 | server/middleware/security/basic_auth.go:45 | observability rules/01; CWE-348 | Low | small | take the client IP from the trusted-proxy chain (rightmost untrusted hop), not the raw header |
| L3 | server/middleware/v2auth/auth.go:71-74 | code-security rules/03 (404 vs 403 consistency); CWE-204 | Low | trivial | return the same challenge or error for a missing project as for an unauthorized one |
| L4 | server/middleware/security/robot.go:57 | code-security rules/22, rules/04; CWE-208 | Low | trivial | `subtle.ConstantTimeCompare`; raise the PBKDF2 cost on next secret refresh |
| L5 | server/v2.0/handler/artifact.go:459 | code-security rules/03 | Low | small | require the label to be global or `label.ProjectID == project.ProjectID` |
| L6 | server/v2.0/handler/scan.go:102 | code-security rules/03 | Low (report UUIDs are unguessable) | small | verify that the report belongs to the artifact just resolved |
| L7 | controller/event/handler/init.go:24-70 | code-security rules/10 (control failure is silent); golang rules/01 | Low | trivial | check `notifier.Subscribe` errors and fail startup, especially for the audit-log handler |
| L8 | server/registry/catalog.go:87 | golang rules/05 (integer overflow); CWE-190 | Low (sysadmin-only path) | trivial | clamp `n` to a sane maximum before the arithmetic |
| I1 | server/v2.0/handler/base.go:105-117 (design) | code-security rules/03 item 1 | Info | large | add a resource-loader helper that takes `(projectID, objectID)` and is the only way handlers fetch project-scoped objects |
| I2 | .github/workflows/CI.yml, codeql-analysis.yml (context only) | devsecops rules/05, rules/09 | Info | small | add govulncheck + gosec (or golangci-lint with gosec) to the PR gate; pin actions by SHA |
| I3 | server/v2.0/handler/*_test.go | testing rules/09 (cross-tenant test per by-ID resource) | Info (it is the reason H1-H7 shipped) | medium | one table-driven cross-project test per by-ID route |
| I4 | server/middleware/security/auth_proxy.go:72, :77 | golang rules/01 | Info | trivial | log `err2`, not `err` |

---

## 5. Scanners and instruments

| Tool | Version | Exact command | Result | Depth reached |
|---|---|---|---|---|
| gitleaks | 8.30.1 | `gitleaks dir --redact --no-banner --report-format json --report-path <out> src/server` and the same for `src/controller` | 0 leaks over 749 KB + 914 KB | Working tree only. There is no git history, so **the history scan was not reached** and this is not a claim about past commits. **Positive control:** the same command over a scratch dir holding a planted RSA key + AKIA string -> `leaks found: 2`. A first run with two path arguments silently scanned the whole workspace (13.59 MB, 21 hits, all out of scope: test keys and fixtures); it was discarded and re-run per directory |
| govulncheck | v1.8.0, Go go1.27.1, DB vuln.go.dev | `GOFLAGS=-mod=vendor GOPROXY=off GOTOOLCHAIN=local govulncheck ./controller/... ./server/middleware/... ./server/registry/... ./server/handler/... ./server/router/...` | exit 3: **35 reachable vulnerabilities from 10 modules**; 30 more in imported packages that are not called, 62 in required modules | **Partial.** (1) `server/v2.0/handler` and `server/v2.0/route` do not compile without the generated `restapi` package, so they were excluded and their call paths were **not** analysed. (2) It analysed against the local go1.27.1 standard library, so **standard-library advisories for the shipped go1.17.7 toolchain are not in this number**. osv-scanner covers that gap |
| osv-scanner | 1.9.2 | `osv-scanner --lockfile=go.mod:src/go.mod` | 243 unique advisory ids, 338 rows; 96 against `stdlib` at the `go 1.17` directive | Manifest-level, not reachability. Its own govulncheck call-analysis step failed (Go version mismatch), so there is no reachability from this tool |
| trivy | 0.72.0 | `trivy fs --scanners vuln --skip-dirs vendor --format table src/go.mod` | 128 (CRITICAL 4, HIGH 55, MEDIUM 61, LOW 6, UNKNOWN 2) | Manifest-level. Criticals: beego CVE-2022-31836 (path traversal), docker CVE-2024-41110, grpc CVE-2026-33186, plus one more. None of the three named was shown as reachable from in-scope packages by govulncheck; beego's router is driven from `src/core` (out of scope). **needs verification** |
| gosec | 2.29.0 | `gosec -fmt text -exclude-generated ./server/... ./controller/...` | 66 issues over 232 files / 31,877 lines, Nosec 0 | 35 files reported type-check errors (missing generated `restapi` package); AST rules still ran on them. Triage: G104 x60 -> L7 (init.go) + noise; G101 csrf.go:21 (header **name**, false positive); G404 registry/controller.go:218 (jitter, false positive); G118 replication/execution.go:120 (intentional detached job, reviewed); G601 util.go:35 -> M9 |
| syft, golangci-lint | installed | not run | | golangci-lint would have duplicated gosec. No SBOM needed for this scope |
| semgrep/opengrep, staticcheck, trufflehog, grype | not installed | not run | **not reached** (not counted as clean) | |

**Raw outputs** are kept outside the workspace in `scratchpad/auditeval/w3out/` (`govulncheck.txt`,
`osv.txt`, `trivy.txt`, `gosec.txt`, `gl-*.json`, `repro/`).

**My own sweeps and their controls** (sota-shell-scripting rules/06):
- The secret-in-log sweep first ran as `grep ... $F` under zsh, which passed the whole file list as **one**
  argument. It failed loudly (`File name too long`) rather than silently, and was re-run as `xargs grep < files.txt`.
  **Positive control:** `Invalid CSRF key` at csrf.go:57 was found by the same invocation.
- Handler-authz sweep: 175 handler operations; 9 have no `Require*`/`requireAccess`/`HasPermission`/`.Can(` call
  (health, ping, systeminfo x2, icon, ListProjects, ListAllRepositories, Search, GetRentenitionMetadata).
  Three of those filter by security context internally (read for ListAllRepositories at `repository.go:71-91`).
  Icon is a finding (M2). A second, independent method (reading by hand every handler that takes an object ID)
  produced H1-H7, M7, L5 and L6. The awk sweep cannot see those, because each of them *does* call `Require*`, just on the wrong object.
- Loop-variable sweep: `for ... range` followed within 6 lines by `&ident` or `go func()`. 6 hits over 232 files;
  1 real (util.go:35, also flagged independently by gosec G601).

**Reproduction run:** `scratchpad/auditeval/w3out/repro/main.go` (go1.27.1, stdlib only) executes the
`v1alpha1.go:83-87` size-check shape on a 3 MiB PNG-magic input:
`size-check: len=1048576 err=<nil> errIsEOF=false -> rejected=false, contentType=image/png`. The same run shows
a 20000x20000 grayscale PNG declaring 400,000,000 pixels in 2,836,027 bytes. Ran 1/1; deterministic stdlib
semantics (`io.ReadAll` never returns `io.EOF`).

---

## 6. Present is not applied (falsification pass)

| Control credited | If it were a no-op, would anything differ? | Verdict |
|---|---|---|
| Icon 1 MB limit (`v1alpha1.go:83-87`) | No: no log, no metric, no test; reproduced as never firing | **Inert** -> M2 |
| Webhook "Prevent SSRF #3755" (`notification_policy.go:232-233`) | No for internal targets: it only strips query and fragment | **Inert for its stated purpose** -> M5 |
| Vulnerability prevention / content trust (`vulnerable.go`, `notary.go`) | Yes for most principals (pull rejected with PROJECTPOLICYVIOLATION). **Population:** bypassed for every v2token holder with push when User-Agent contains `cosign` (`util.go:69-72`) | **Applied to fewer principals than credited** -> M4 |
| Project-scoped authorization (`RequireProjectAccess`) | Yes for the project in the URL. **Population:** of the 23 project-scoped handler operations in scope that take a second object ID, I counted 11 that bind the object to the project (robotV1 x3, member x3 via a project-scoped controller, label x3 via the stored label, replication task-in-execution, preheat GetPolicy/DeletePolicy/ListExecutions by `(projectID, name)`) and **12 that do not** (H1-H7 sites, M7, L5, L6). Counted by hand (I could not run a call-graph tool on the uncompiled handler package), so treat the split as approximate | **Real control, applied to about half its surface** -> H class |
| Notifier subscriptions incl. audit log (`init.go:24-70`) | A failed `Subscribe` is discarded, so the audit-log handler can be missing with no signal | **Silently fallible** -> L7 |
| v2auth default deny (`auth.go:52-55`) | Yes: an unrecognized `/v2` path gets 401 (`accessList` empty -> error) | **Effective** (positive) |

Enforcement depth: the repo's CI gate is golint/govet/gofmt + unit tests with `-race` + weekly CodeQL. None
of these can see a BOLA (it type-checks and lints clean), and none runs SCA, so the gates being green says
nothing about H1-H7 or M6.

---

## 7. Decisions and history

No git history (`.git` removed), so commit archaeology, `git log -G` guard-idiom search and complexity x churn
ordering were **not reached**. The decisions below were reconstructed from the code, the Makefile and the
nginx templates.

| Decision | Evidence | Verdict |
|---|---|---|
| Authorization is done per handler against the path/body project, with no shared object loader | base.go:105-117; 175 handler ops | **UNJUSTIFIED** at this scale: the same omission recurs in at least 8 handlers (H class), and robotV1/label already show the correct pattern |
| Job-status hooks carry no in-app authn; exposure is blocked at nginx | job_status_hook.go:38-59; nginx templates `:200` / `:227` | **UNVERIFIABLE here**: it holds for the bundled nginx and depends on every other ingress copying the rule (Helm chart not in the tree) |
| Build toolchain `golang:1.17.7` (Makefile:160), `go 1.17` directive | 96 stdlib advisories (osv); pre-1.22 loop semantics (M9) | **STALE** (Go 1.17 is long out of support; the exact EOL date is from memory, not re-checked: needs verification) |
| Cosign signature push needs a policy-bypassing pull, recognised by User-Agent | util.go:66-72 comment | **UNJUSTIFIED** as implemented: the need is real, but the discriminator is client-controlled |
| CSRF via gorilla/csrf, SameSite=Strict, header token | csrf.go:53-70 | **JUSTIFIED** in design; the pinned version carries GO-2025-3607 (Referer check), which is mitigated in practice by the custom-header token |

**Knowledge in agent memory:** this workspace has no agent files (`CLAUDE.md`/`AGENTS.md`/`.cursorrules`
absent in the top 3 levels), and no agent project-memory directory matches this workspace. The library
checkout's memory mentions "Harbor" in three files. Those notes are about running evaluations on Harbor,
not facts about Harbor's code, so they are not a finding. Positive control: the same search found
`sota-agent-evals` in the memory index. **Day zero:** not applicable. LICENSE and CI exist and the project is
mature (v2.5.1, CHANGELOG), though history length could not be checked.

---

## 8. Evidence blocks (surviving findings)

Each block carries the eight fields of router rules/03 §2 plus a reproduction (read path).

Common to H1-H7: **reach**: any authenticated account creates its own project A (default `everyone`, `lib/config/metadata/metadatalist.go:117`) and is its projectAdmin (`common/rbac/project/rbac_role.go:93-125`). **Primitive**: a read or write by a raw, sequential int64 ID. **Boundary crossed**: from tenant A to tenant B (another project, or system-wide job data). **Channel**: the HTTP response body. Standard mapping: CWE-639, OWASP API1:2023 (BOLA), A01:2021, ASVS 4.0.3 V4.2.1. Every one is a **static** read-path finding: the handler package does not compile without generated code, so none was exercised over HTTP.

**H1. Cross-project read of webhook policies, including target `auth_header` secrets (High)**
- Location: `server/v2.0/handler/notification_policy.go:155`.
- Evidence: authz is on the path project (`:151`), then `webhookPolicyMgr.Get(ctx, params.WebhookPolicyID)`. The DAO reads `&Policy{ID:id}` with no project predicate (`pkg/notification/policy/dao/dao.go:41-56`). The response copies `AuthHeader` (`server/v2.0/handler/model/notification_policy.go:37`).
- Impact: reads B's webhook endpoints and their credentials, by enumerating IDs.
- Severity: High. It is cross-tenant credential disclosure; Critical was not chosen because a project-admin account is required.
- Fix: load, compare `policy.ProjectID` with the authorized project ID (404 on mismatch), and make `auth_header` write-only. Effort: small.
- Reproduction (read path): `GET /api/v2.0/projects/A/webhook/policies/{id of B}` -> `notification_policy.go:151` (passes for A) -> `:155` -> `dao.go:49` -> `model/notification_policy.go:37`.
- Refuter: SURVIVES 0.95.

**H2. Cross-project delete of webhook policies (High)**
- Location: `notification_policy.go:143`.
- Evidence: `Delete(params.WebhookPolicyID)` reaches `dao.go:131` `ormer.Delete(&Policy{ID:id})`.
- Impact: silences B's notifications (integrity and availability).
- Fix: ownership check before the delete. Effort: trivial.
- Reproduction: `DELETE /api/v2.0/projects/A/webhook/policies/{B id}` -> `:139` -> `:143` -> `dao.go:131`.
- Refuter: SURVIVES 0.95.

**H3. Overwrite and reassign any webhook policy through a body-supplied ID (High)**
- Location: `notification_policy.go:115-130`.
- Evidence: path `WebhookPolicyID` is never read. `lib.JSONCopy` copies `id` from the body, `ProjectID` is set to A, and `ormer.Update(policy)` updates all columns by ID (`dao.go:89`).
- Impact: B's policy is replaced and moved to A, so B loses its notifications.
- Correction from the refuter: the body must carry a non-zero `id`.
- Fix: `policy.ID = params.WebhookPolicyID`, plus an ownership check on the stored row. Effort: small.
- Refuter: SURVIVES 0.9.

**H4. Preheat endpoints act on any task, execution or policy system-wide (High)**
- Locations: `preheat.go:725` (GetPreheatLog), `:581` (GetExecution), `:650` (StopExecution), `:693` (ListTasks), `:267` (UpdatePolicy).
- Evidence: `taskCtl.GetLog(TaskID)` -> `controller/task/controller.go:76` -> `pkg/task/task.go:233-238` (by ID, then the jobservice log). There is no vendor or project filter. UpdatePolicy takes `id` and `project_id` from the body (`preheat.go:454-479`) and updates by ID.
- Impact: reads the job log of **any** background task (replication, GC, scan, retention, webhook). Those logs can carry registry endpoints, repository names and error details. The attacker can also stop any execution and overwrite any preheat policy.
- Fix: resolve task -> execution -> vendor policy -> project and require the authorized project; take IDs from the path. Effort: small.
- Refuter: SURVIVES 0.9.

**H5. Retention endpoints: any task log, stop any execution, neutralise another project's retention policy (High)**
- Locations: `retention.go:353`, `:277`, `:198-205` (and `:326`).
- Evidence: `GetRetentionExecTaskLog(params.Tid)` -> `controller/retention/controller.go:363` -> `taskMgr.GetLog` (unfiltered). `OperateRetentionExec(params.Eid)` -> `controller.go:257-267` -> `launcher.Stop` (any vendor). On UpdateRetention the ID comes from the path while authorization uses the body's `scope.reference`.
- Impact: the same log disclosure as H4; stopping GC or replication runs; overwriting B's retention rules.
- Refuter correction: the overwritten policy then scopes to A's repositories, so it cannot be turned into deleting B's images.
- **Role: maintainer of A suffices** (`rbac_role.go:157-162`).
- Fix: bind Tid -> Eid -> policy ID, and authorize UpdateRetention on the stored scope. Effort: small.
- Refuter: SURVIVES 0.9.

**H6. Delete, disable or rewrite another project's tag-immutability rules (High)**
- Locations: `immutable.go:62`, `:84`; `controller/immutable/controller.go:60-70`.
- Evidence: delete by ID (`pkg/immutable/dao/dao.go:119-134`). Update takes the ID from the body, toggles by ID, or updates `TagFilter` by ID, with no project check.
- Impact: removes B's tag-immutability protection. Overwriting B's tags afterwards still needs push to B, so this strips a control rather than granting access.
- **Role: maintainer of A suffices** (`rbac_role.go:166-168`).
- Fix: ownership check on the stored rule; ID from the path. Effort: small.
- Refuter: SURVIVES 0.9.

**H7. Update another project's robot account, authorized against a body-chosen namespace (High; impact narrowed)**
- Location: `robot.go:287`.
- Evidence: authorization uses `params.Robot.Permissions[0].Namespace` (attacker's A), while DeleteRobot and RefreshSec correctly use the stored `r.ProjectID` (`:90`, `:220`).
- Impact (refuter-narrowed): the attacker can disable B's robot, re-enable a robot B disabled, set it to never expire, or replace its permissions with A-scoped ones. That breaks B's pipelines. It gives no access into B: the secret is not exposed and permissions cannot be widened into B.
- Preconditions: a project-level robot, and the attacker must know its full name `robot$<B>+<name>`.
- Fix: authorize on `r.Level`/`r.ProjectID` and require the body namespace to equal it. Effort: small.
- Refuter: SURVIVES 0.85.

**Medium findings** are carried in the working table with location, rule, fix and effort. Their evidence is quoted in sections 3, 5 and 6:
- M2 has an executable reproduction (`w3out/repro/main.go`, output quoted in section 5).
- M1's read path is `server/route.go:59` -> `server/handler/job_status_hook.go:45` -> `pkg/task/hook.go:47-80`.
- M4's read path is `server/registry/route.go:51-58` (vulnerable/contenttrust middleware) -> `server/middleware/vulnerable/vulnerable.go:71` -> `server/middleware/util/util.go:69-72` (User-Agent test).

M1 refuter verdict: about 0.95 that there is no in-app authentication, but only 0.35 that "any caller can change task status" holds in practice. The JobID is 96-bit random (`jobservice/common/utils/utils.go:41-48`), no API was found that returns it, and nginx returns 404 on the path by default. M1 therefore stays **Medium**, with the Helm/ingress question open.

---

## 9. Remediation roadmap (risk reduction per effort)

1. **One work item, closes H1-H7, M7, L5, L6 (small to medium):** add `requireProjectObject(projectID, obj.ProjectID)`
   after every by-ID load in notification_policy, notification_job, preheat (execution/task/log), retention
   (task/exec), immutable, robot (v2 update), artifact AddLabel and scan report log. Take IDs from the path, never
   the body. Add one cross-project table test per route (I3). This is the release blocker.
2. **Stop returning webhook `auth_header`** (part of H1): make it write-only.
3. **Authenticate status hooks** (M1): require the jobservice secret in core, not only at nginx.
4. **Bound inputs** (M2, M3): `MaxBytesReader` on manifest PUT; `DecodeConfig` pixel budget; fix the inert size
   check; require authn on GetIcon.
5. **Replace the User-Agent bypass** (M4) and **add SSRF egress rules for webhooks** (M5).
6. **Toolchain + dependency upgrade** (M6), with govulncheck in CI (I2) so it cannot drift again.
7. Hygiene: M8, M9, L1-L4, L7, L8, I4.

## 10. Positive observations (keep through remediation)

- `robotV1.go:122,192,215` binds `ProjectID` **and** `ID` in the query. This is the pattern H1-H7 need.
- `label.go:58-69, 123-137, 154-160` authorizes against the **stored** label's scope.
- `replication.go:396-409` checks that the task belongs to the execution before returning its log.
- `v2auth` denies unrecognized `/v2` paths by default and checks pull access on cross-repo blob mounts (`access.go:91-97`).
- CSRF uses SameSite=Strict plus a header token, and is skipped only for sessionless API calls.
- Unit tests run under `-race`.

## 11. Refutation

**Stronger form than a self-refutation, for the Highs only.** One independent general-purpose agent in a fresh context got the code root and eight claims. It was told to default to REFUTED and to return a number for each claim. It opened about 35 files and used 34 tool calls (its stated and measured counts).

| Claim | Verdict | Confidence | Change it made |
|---|---|---|---|
| H1 | SURVIVES | 0.95 | none |
| H2 | SURVIVES | 0.95 | none |
| H3 | SURVIVES | 0.9 | body needs a non-zero `id` |
| H4 | SURVIVES | 0.9 | added the preheat UpdatePolicy overwrite detail |
| H5 | SURVIVES | 0.9 | UpdateRetention cannot be used to delete B's images; maintainer suffices |
| H6 | SURVIVES | 0.9 | maintainer suffices |
| H7 | SURVIVES | 0.85 | narrowed to availability/integrity of B's robot, no access gain |
| M1 (C8) | narrowed | 0.35 practical / 0.95 no in-app authn | 96-bit JobID + nginx 404, so it stays Medium |

Caveats:
- The refuter received my claims rather than only the code, so it was not blind to my framing.
- It did not run anything.
- The Mediums and Lows got **only my own self-refutation**: M2-M9 and L1-L8.

**Pattern sweep after refutation:** I re-swept the class to look for more sites. It added M7 (notification_job), L5 (AddLabel) and L6 (scan report log). Correctly bound counter-examples (robotV1, label, member, replication task log) are listed in section 10.

All `file:line` citations in this report were re-resolved against the tree with `grep -n` after the last read. No file in the tree changed during the audit: there were no edits, and there is no git to compare against.

## 12. Evidence not obtained (what would move a verdict)

- **Helm/ingress routing for `/service/notifications`**: moves M1 between Medium and High.
- **The generated `restapi` package / a running instance**: would let H1-H7 be reproduced as HTTP requests (all are static read-path findings today) and let govulncheck reach the v2.0 handlers.
- **`src/core/auth` lockout behaviour**: settles M8.
- **Go history** (`git log`): would show whether any of the H class was fixed upstream later. That bears on the patch, not on whether v2.5.1 is vulnerable.
- **Reachability of trivy's Criticals in the full `core` binary**: settles M6's per-advisory severity.

A rule that let this codebase down: code-security rules/03's "ownership predicate in every by-ID lookup" was
the one that would have caught all seven Highs. Run `/sota-report` to tell the library whether its audit-half
probe (grep for by-ID loads after a `Require*` on a different identifier) is concrete enough.
