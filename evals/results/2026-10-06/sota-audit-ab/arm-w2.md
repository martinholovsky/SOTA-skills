# /sota-audit report: Harbor `src/server`, `src/controller`, `src/go.mod`

**Posture: not ready.** Two High findings are open. Both are broken object-level authorization (BOLA) that any authenticated user can reach, given the default `project_creation_restriction=everyone`. Through them, any user can read another project's webhook credentials, read any background job's log, and stop any job execution on the instance. A third High lets the same user change or delete another project's security policies.

---

## 1. Executive summary

The audited tree is Harbor `v2.5.1` (`VERSION`). It covers 232 non-test Go files (31,877 lines) in `src/server` and `src/controller`, plus `src/go.mod`.

The main problem is one repeated authorization pattern. Handlers check the caller's role on the project named in the URL, then act on an object picked by an ID from the path or the request body. Nothing confirms that the object belongs to that project. Any user can create their own project and become its admin, so a low-trust user gets admin-level reach into every other project's webhooks, retention, immutability, preheat and robot objects. They also reach every background job (replication, GC, scan, retention, preheat) through the generic execution and task APIs.

Severity counts (21 findings): **Critical 0 · High 3 · Medium 10 · Low 7 · Info 1**.

Top risks:
1. **Webhook credentials across projects (H1).** Any user can read another project's webhook target and its `auth_header` secret, re-point that webhook into their own project, or delete it.
2. **Jobs across the whole instance (H2).** Any user can read the log of any background job, list any execution's tasks, and stop any running execution, including system GC, scan-all and replication.
3. **Policy tampering across projects (H3).** Any user can delete or edit another project's tag-immutability rules, retention policy, preheat policy, or a robot account's state.
4. **Availability.** One authenticated pusher can exhaust core's memory (M1: unbounded reads of manifests and charts). Reachable vulnerable dependencies include a pre-auth JWT allocation bug (M2).
5. **Detection.** Failed audit-log writes are dropped at Debug level. Privilege-changing actions (sysadmin grant, member role, robot, config, password set) are not audited at all (M4).

---

## 2. Scope and methodology

- **Pin.** There is no git history (`.git` removed), so there is no commit SHA. The tree is identified by `VERSION` = `v2.5.1`. A sha256 manifest of all 375 files under `server/` and `controller/` plus `go.mod` is kept outside the workspace (`auditeval/w2out/scope.sha256`, digest prefix `03bd2c47727aeb76`). Every `file:line` below is relative to `src/` and bound to that manifest. The workspace was never modified.
- **Scope (agreed in advance).** Non-test Go under `src/server` (123 files, 15,017 lines) and `src/controller` (109 files, 16,860 lines), plus `src/go.mod`. Other directories (`pkg/`, `lib/`, `core/`, `common/`, `make/`, `.github/`) were read only to follow call paths and settle chain legs. Defects there are not counted as findings and are listed separately in §11.
- **Scope type.** A baseline of named directories, not a diff, so the dependents rule (diff plus callers) does not apply.
- **Excluded.** Test files, the portal UI, `jobservice`, `core` (beego controllers, auth backends), `pkg` managers and DAOs, deployment templates, and CI. Generated swagger code (`server/v2.0/restapi`, `server/v2.0/models`) is not present: it is built at `make gen_apis` and was not generated, because nothing may be installed.
- **Yardsticks.** OWASP API Security Top 10 (2023; API1 BOLA, API3 BOPLA, API4 resource consumption, API5 BFLA, API7 SSRF), CWE, and OWASP ASVS 4.0.3 Level 2 (V4 access control, V2 authentication, V7 logging, V12 files and resources). The LLM/agent lists do not apply: there is no such surface in scope.
- **Threat model.** The light model (§4), built from the code. The full `sota-threat-modeling` rules/06 reconstruction was **not** run.
- **Stack profile.** `~/.claude/profiles/<owner>.md` exists, but it is the baseline for the operator's own repositories. This is upstream Harbor, so the profile was **not** applied as the AUDIT baseline. (Decision recorded in §9 because the operator was unavailable.) The project's own conventions (`CONTRIBUTING.md`: golint, `go test`, unit tests for new code, a claimed gosec run) were used, and are checked in §11.
- **Day-zero check.** Did not fire. The repo has LICENSE, CONTRIBUTING, SECURITY.md and CI workflows, and is a long-lived project.
- **Audit date.** 2026-10-06. Single auditor context. The refutation pass was a self-refutation (see §8).

### Scanners (all run against the pinned tree, output kept in `auditeval/w2out/`)

| tool | version | exact command | reach / denominator | result |
|---|---|---|---|---|
| gitleaks | 8.30.1 | `gitleaks dir --redact --no-banner -r <out> server` (and `controller`) | working tree only, about 1.66 MB. **History not reached** (no `.git`). Positive control: two synthetic tokens in a scratch dir were caught (`leaks found: 2`). | 0 leaks in scope. `go.mod`/`go.sum` showed "scanned ~0 bytes" (gitleaks' default path allowlist), so manifests were **not** scanned by it. |
| trivy | 0.72.0 (DB fetched by the tool) | `trivy fs --scanners vuln --format json .` over a copy of `go.mod` + `go.sum` | 1 lockfile, module-level (no reachability) | 128 advisories in 28 modules: 4 Critical, 55 High, 61 Medium, 6 Low, 2 Unknown |
| govulncheck | v1.8.0, DB modified 2026-10-01, go1.27.1 | `GOFLAGS=-mod=vendor govulncheck -format json <84 packages>` | **84 of 89** in-scope packages. 5 could not build because generated swagger code is missing: `server`, `server/v2.0/handler`, `.../assembler`, `.../model`, `.../route`. | 350 OSV entries matched. 35 at symbol level. Triaged in M2; about 20 are reachable only through package `init`. |
| gosec | 2.29.0 | `gosec -quiet -tests=false -fmt json ./server/... ./controller/...` (vendor mode) | 232 files, 31,877 lines. 66 packages had type errors, so taint analyzers were degraded. | 65 issues: 62×G104, 1×G404, 1×G101, 1×G601 |
| golangci-lint | 2.13.2 | `golangci-lint run --no-config --default=none -E gosec,errcheck,bodyclose --tests=false <buildable pkgs>` | buildable packages only | 35 issues. **This is a page, not a total.** Default `max-same-issues=3` truncates; gosec alone reported 32 discarded `notifier.Subscribe` errors where golangci printed 3. |
| semgrep/opengrep, osv-scanner, trufflehog, staticcheck | not installed | — | **not reached** | — |

Nothing was installed. No scanner was pointed at a live system. trufflehog verification did not apply because it is not installed.

### Evidence not obtained, and what it would change

- **Running instance.** None was available, so every High is a static read path, not an executed exploit. A two-project, two-user run of the §6 reproductions on a v2.5.1 instance would confirm or kill H1–H3 directly.
- **Deployment topology** (Helm/ingress vs the bundled nginx). This decides whether M5 (unauthenticated job-status hooks) is reachable from outside the cluster. A `curl -X POST https://<ext>/service/notifications/tasks/1` returning anything other than 404 would raise M5 to High.
- **Git history.** Without it, the history scan, `git log -G` variant hunting, churn ordering and decision provenance were all not reached.
- **Upstream advisories.** Network access was forbidden. Whether H1–H3 match published Harbor advisories fixed after 2.5.1 is **not verified**. Do not quote CVE IDs for them from this report.

---

## 3. Coverage: per rules file

Rules were walked by running each checklist's probes over the 232-file scope with a positive control in the same invocation (`RequireProjectAccess(` → 73 hits), plus manual reads ordered by the boundary map. "Partial" means the named items were walked and the rest were not.

| surface found | owning skill | rules file | walked? | if not, why |
|---|---|---|---|---|
| Go code (go 1.17 module) | sota-golang | 01 errors | walked (discarded errors, panics, log.Fatal) | — |
| | sota-golang | 02 design | **not walked** | Design idioms; low security yield. Budget went to authz. |
| | sota-golang | 03 concurrency | walked (go.mod version, `go func` ×20, time.After ×4, sync.Map) | — |
| | sota-golang | 04 http services | partial (body hygiene, path-based authz, cookies, logging) | Servers are constructed in `core/main.go` (out of scope): 0 `ListenAndServe` in scope, so the timeouts item is N/A here |
| | sota-golang | 05 security | walked (all greps; SQL 0, exec 0, InsecureSkipVerify 0, math/rand 1, text/template 0, unsafe 0) | — |
| | sota-golang | 06 performance | **not walked** | Out of the security-first budget |
| | sota-golang | 07 tooling/CI | partial (golangci, race flag, gosec target) | CI is out of scope; read for context only |
| | sota-golang | 08 supply chain | walked (`go.sum` present, govulncheck, no `replace` in scope) | `go mod verify` needs network or module cache, so not run |
| HTTP API, authn/z, sessions | sota-code-security | 01 input/injection | partial (SQL/exec greps) | The `lib/q` query builder that consumes user `q=` and `sort=` is out of scope: **not reached** |
| | sota-code-security | 02 authentication | walked (all 9 generators in `security.go`, KDF, lockout) | — |
| | sota-code-security | 03 authorization | **walked item by item** (§2 census in §6) | — |
| | sota-code-security | 04 cryptography | partial (KDF, PRNG) | — |
| | sota-code-security | 05 web security | partial (CSRF middleware) | Response headers belong to the portal/nginx (out of scope) |
| | sota-code-security | 06 memory/resource | walked (unbounded reads) | — |
| | sota-code-security | 07 data exposure | walked (secrets in responses and logs) | — |
| Untrusted ingestion (pushed manifests, charts, cosign sigs, webhook bodies) | sota-code-security | 09 untrusted ingestion | walked | — |
| Present-not-applied | sota-code-security | 10 silent control failure | walked (§7) | — |
| | sota-code-security | 11 dead-path / 16 where no-ops hide | **not walked** | Budget; 10 and 14 were used instead |
| | sota-code-security | 14 control not in force | walked (population census of the authz control) | — |
| | sota-code-security | 17 sessions/tokens | partial (v2 token, session, ID token) | OIDC verification lives in `pkg/oidc` (out of scope) |
| | sota-code-security | 18 tamper-evident logs | partial (audit write path) | — |
| | sota-code-security | 19 anti-automation | walked (no rate limiting anywhere in scope) | — |
| | sota-code-security | 20 browser hardening, 21 uploads | **not walked** / partial (artifact push = upload, via 06/09) | UI out of scope |
| | sota-code-security | 22 constant-time | walked (1 site) | — |
| | sota-code-security | 08, 23 LLM; 12, 13, 15 evidence scripts | N/A | No LLM surface and no evidence-producing scripts in scope |
| REST API, webhooks (provider role) | sota-api-design | 06 webhooks | walked (provider half) | Consumer half N/A |
| | sota-api-design | 07 security/ops | partial (rate limits, tenant isolation) | — |
| | sota-api-design | 01 REST, 02 versioning | **not walked** | Budget. This is a hole, not a clean result. |
| | sota-api-design | 03 GraphQL, 04 gRPC, 05 realtime | N/A | No such surface |
| RBAC model, OIDC/auth-proxy federation | sota-identity-access | 03 authorization models | walked (role map `common/rbac/project/rbac_role.go`) | — |
| | sota-identity-access | 01 federation | partial | Token verification is out of scope |
| | sota-identity-access | 02, 04–07 | N/A in scope | IdP ops and lifecycle are not in this code |
| Credentials in payloads and logs | sota-secrets-management | (rules index) | partial (webhook auth_header, preheat auth_info, OIDC CLI secret, CSRF key) | — |
| Trust boundaries | sota-threat-modeling | 06 (light only) | light model ran (§4) | Full reconstruction not run |
| Suite health | sota-testing | suite-health pass | partial (counts and authz-test census, §6 M10) | Tests not executed (no DB/registry fixtures) |
| Personal data (users: email, realname; audit log usernames) | sota-privacy-compliance | minimization/retention | partial (§6 M4, L6) | — |
| `go.mod` dependencies | sota-devsecops | 03 SCA | walked | — |
| Goroutines, notifier fan-out | sota-async-concurrency | — | covered via sota-golang 03 | Not walked separately |
| ORM/DAO | sota-databases | — | **not reached** | DAOs are in `pkg/` (out of scope) |
| Logging, metrics, tracing | sota-observability | — | **not walked** | Budget. This is a hole: only the audit-log path was examined. |
| Architecture | sota-architecture | — | **not walked** | "Audit what is here"; decision ledger only (§10) |
| Own verification commands | sota-shell-scripting | 06 | applied (positive controls, denominators, unpiped exit codes) | — |

**Skill-level halves.** The AUDIT workflow and top-10 non-negotiables were checked for sota-golang (go.mod <1.22 with loop closures: **not met**, M7; govulncheck in CI: **not met**; race in CI: **met**, `tests/coverage4gotest.sh:32`) and for sota-code-security (object-level authz: **not met**; rate limiting: **not met**; secrets out of logs: **not met**, L1).

**Router principle 5, re-checked last:**
- (a) Abuse control: **not met** (M6; zero limiter sites in scope).
- (b) Transport: TLS terminates at nginx (out of scope); no plaintext-fallback code in scope. N/A here.
- (c) Tests for the logic: **not met** for the affected handlers (M10).
- (d) Structured logs without secrets: mostly met; **not met** at `csrf.go:57` (L1).

---

## 4. Light threat model: trust-boundary map (built from the code)

| entry point | authn / authz checkpoint | asset or store reached | privilege it runs with |
|---|---|---|---|
| `/api/v2.0/**` (go-swagger handlers) | `server/middleware/security/security.go:56-61` (first generator wins), then per-handler `Require*Access` (`server/v2.0/handler/base.go:105-133`) | Postgres via `pkg` DAOs, jobservice, registry | core DB role (all projects) |
| `/v2/**` registry API | `server/middleware/v2auth/auth.go:47-80` (`accessList` incl. blob-mount pull, `access.go:66-98`) | distribution registry (`server/registry/proxy.go`) | core → registry credentials |
| `/service/notifications/**` job-status hooks | **none in code** (`server/handler/job_status_hook.go:37-56`); nginx `return 404` (`make/.../nginx.https.conf.jinja:227-229`) | task/execution status rows | core DB role |
| Robot basic auth | `server/middleware/security/robot.go:33-71` (PBKDF2 compare, no throttle) | as robot permissions | robot scope |
| OIDC CLI secret / ID token | `oidc_cli.go:47-73`, `idtoken.go` | as user | user |
| Session cookie | `session.go`; CSRF `server/middleware/csrf/csrf.go:53-80` only when the session is carried | as user | user |
| Event handlers (in-process notifier) | none needed (internal) | webhooks out, audit log, replication, preheat | core |
| Outbound webhooks (`controller/event/handler/util/util.go:27-47` → jobservice) | target URL chosen by the project admin (`notification_policy.go:223-240`) | **any reachable host** (SSRF) | jobservice network position |

**Assumptions the code implies, and their checks:**
1. *"The project in the URL owns the object the ID names."* **Broken.** No predicate binds them at the 18 sites in §6 (H1–H3).
2. *"Only jobservice can reach `/service/notifications`."* **Unverified.** True for the bundled nginx (404). Unknown for Helm/ingress deployments, and nothing in-process enforces it (M5).
3. *"Project admins are trusted tenants."* **Broken by the default.** `lib/config/metadata/metadatalist.go:117` defaults `project_creation_restriction` to `everyone`, and the creator becomes `projectAdmin`. So "project admin" means "any authenticated user".
4. *"Webhook targets are sanitized against SSRF (#3755)."* **Broken.** The sanitizer is a no-op (M3).
5. *"Audit log is complete."* **Broken.** Write failures are dropped silently, and the scope of audited events excludes privilege changes (M4).

---

## 5. Findings table (working format)

| # | file:line | rule violated | severity | effort | fix |
|---|---|---|---|---|---|
| H1 | server/v2.0/handler/notification_policy.go:155, :143, :130; notification_job.go:34 | sota-code-security rules/03 §2 (BOLA, CWE-639) | **High** | small | Load the policy and require `policy.ProjectID == projectID` (404 otherwise); set `policy.ID = params.WebhookPolicyID` on update |
| H2 | server/v2.0/handler/retention.go:277, :326, :353; preheat.go:581, :650, :693, :725 | rules/03 §2 (CWE-639) | **High** | small | Resolve execution/task, require vendor type and vendor ID to match the authorized policy/project |
| H3 | immutable.go:62, :84; retention.go:198-212; preheat.go:257-268; robot.go:287 | rules/03 §2 + §9 (authz on one object, act on another) | **High** | small | Authorize against the **stored** object's project, never body fields; pin IDs from the path |
| M1 | server/middleware/blob/put_manifest.go:37, :67; quota/util.go:52; cosign/cosign.go:77; controller/artifact/processor/chart/chart.go:87 | sota-golang rules/04 (unbounded body read); sota-code-security rules/06, 09 | Medium | small | `io.LimitReader` / `http.MaxBytesReader` (manifest ≤ 4 MiB; chart layer cap) |
| M2 | go.mod:3, :29, :34, and others | sota-golang rules/08; sota-devsecops rules/03 | Medium | medium | Upgrade jwt/v4 ≥4.5.2, gorilla/csrf ≥1.7.3, helm ≥3.17.3, x/net, prometheus ≥1.11.1, beego ≥1.12.11; raise `go` directive |
| M3 | server/v2.0/handler/notification_policy.go:227-233 | sota-code-security rules/10 (inert control); api-design rules/06 SSRF | Medium | small | Iterate by index; add a resolve-pin-connect private-range block in the sender |
| M4 | controller/event/handler/auditlog/auditlog.go:66; controller/event/handler/init.go:50-58 | sota-code-security rules/10, rules/18; rules/03 checklist (immutable audit trail) | Medium | medium | Log failures at Error with a metric; audit sysadmin/member/robot/config/password changes |
| M5 | server/route.go:53-59; server/handler/job_status_hook.go:37-45 | rules/03 §6 (service-to-service identity) | Medium (needs verification) | small | Require the core/jobservice shared secret (`IsSolutionUser`) on the hook routes |
| M6 | server/middleware/security/robot.go:33-57; oidc_cli.go:47-60 | sota-code-security rules/19; router principle 5(a) | Medium | medium | Per-principal + per-IP throttle on all credential generators, shared store |
| M7 | controller/event/handler/util/util.go:35 (+ go.mod:3) | sota-golang rules/03 (go <1.22 + pointer to loop var) | Medium | trivial | `t := target; Target: &t` (or bump `go` ≥1.22) |
| M8 | server/v2.0/handler/robot.go:227-230 (via common/utils/encrypt.go:50) | sota-code-security rules/02 §1 / rules/04 (PBKDF2-SHA256 ≥600,000) | Medium | medium | Argon2id or PBKDF2 ≥600k with re-hash on login |
| M9 | server/v2.0/handler/user.go:291-325 | sota-code-security rules/03 checklist "Admin password reset" | Medium | medium | Admin triggers a reset flow; at least audit and notify on admin-set password |
| M10 | server/v2.0/handler/ (no `notification_policy_test.go`, `retention_test.go`, `immutable_test.go`; `robot_test.go` lacks cross-project cases) | sota-testing suite health; rules/03 checklist (cross-tenant deny matrix) | Medium | medium | Table-driven cross-project deny tests for every ID-bearing route |
| L1 | server/middleware/csrf/csrf.go:57 | sota-code-security rules/07 (secrets in logs) | Low | trivial | Log the key's length, never its value |
| L2 | server/middleware/security/robot.go:57 | sota-code-security rules/22 | Low | trivial | `subtle.ConstantTimeCompare` |
| L3 | server/v2.0/handler/artifact.go:72; repository.go:59; scan.go:44; config.go:69 | sota-golang rules/01; sota-code-security rules/10 (fail-open on error) | Low | trivial | `return a.SendError(ctx, err)` |
| L4 | server/v2.0/handler/artifact.go:459 | rules/03 §2 (nested ID) | Low | small | Require label global, or label.ProjectID == artifact's project |
| L5 | server/v2.0/handler/scan.go:102 | rules/03 §2 (random ID is not authz) | Low | small | Bind report UUID to the resolved artifact |
| L6 | server/v2.0/handler/preheat.go:492; handler/model/user.go:49 | sota-code-security rules/07; secrets write-only | Low | small | Redact `auth_info`; return the CLI secret only to its owner |
| L7 | server/middleware/log/log.go:27; security/basic_auth.go:41-48 | sota-code-security rules/07 / rules/18 (log integrity) | Low | trivial | Bound and validate `X-Request-ID`; trust XFF only from configured proxies |
| I1 | controller/event/handler/init.go:24-61 (32 discarded `notifier.Subscribe` errors) | sota-golang rules/01 | Info | trivial | Check errors; fail start-up on a failed subscription |

---

## 6. Findings: full evidence blocks

### H1: Webhook policies readable, re-pointable and deletable across projects
- **Severity:** High. Impact: cross-tenant credential disclosure (`auth_header`) and hijack. Likelihood: any authenticated user, with sequential integer IDs.
- **Location:** `server/v2.0/handler/notification_policy.go:149-161` (Get), `:137-147` (Delete), `:109-135` (Update); `server/v2.0/handler/notification_job.go:28-37`.
- **Evidence:**
  ```go
  // notification_policy.go:151-155
  if err := n.RequireProjectAccess(ctx, projectNameOrID, rbac.ActionRead, rbac.ResourceNotificationPolicy); err != nil { ... }
  policy, err := n.webhookPolicyMgr.Get(ctx, params.WebhookPolicyID)   // no ProjectID check
  // :143  n.webhookPolicyMgr.Delete(ctx, params.WebhookPolicyID)
  // :129-130 policy.ProjectID = projectID; n.webhookPolicyMgr.Update(ctx, policy) // policy.ID from body
  ```
  The DAO uses `ormer.Read(&Policy{ID: id})` and `ormer.Update(policy)` keyed on ID only (`pkg/notification/policy/dao/dao.go:41-55, 80-99`). The response includes `AuthHeader` (`server/v2.0/handler/model/notification_policy.go:37`).
- **Chain:**
  - Reach: any user creates project A (`metadatalist.go:117` default `everyone`) and becomes projectAdmin, which has `ResourceNotificationPolicy` read/update/delete (`common/rbac/project/rbac_role.go:93-97`).
  - Primitive: read, update or delete by ID.
  - Boundary: project B's row.
  - Channel: the API response.
- **Mapping:** CWE-639, CWE-200. OWASP API1:2023. ASVS 4.0.3 V4.2.1.
- **Impact:** The user reads project B's webhook endpoint and its `Authorization` header value (the credential for B's receiver). They can move B's policy into project A (the update rewrites `project_id`), which silences B's notifications and redirects them, or delete it. `ListWebhookJobs` exposes B's delivery history (`job_detail` payloads).
- **Remediation:** After `RequireProjectAccess`, `pid := getProjectID(...)`; `p := mgr.Get(id)`; `if p.ProjectID != pid { return 404 }`. On update, set `policy.ID = params.WebhookPolicyID` and apply the same check. Add the same check in `ListWebhookJobs`.
- **Effort:** small.
- **Reproduction (static read path):**
  1. `GET /api/v2.0/projects/A/webhook/policies/{B_policy_id}`.
  2. `notification_policy.go:150` authorizes against A (passes).
  3. `:155` `Get(B_policy_id)`, then `dao.go:41-55` with no project predicate.
  4. `:160` responds with `NewNotifiactionPolicy(policy).ToSwagger()`, then `model/notification_policy.go:37` `AuthHeader`.
- **Self-refutation:** Checked that `Prepare` (`:38-40`) adds no check, that the DAO adds no predicate, and that no middleware scopes ORM queries by project. Verdict: **survives (0.9 against a 0.7 threshold)**.

### H2: Any job's execution, tasks and logs readable and stoppable through retention and preheat endpoints
- **Severity:** High. Impact: cross-tenant and system job-log disclosure, plus stop/DoS of any job (GC, scan-all, replication). Likelihood: any authenticated user, with sequential IDs.
- **Location:** `server/v2.0/handler/retention.go:265-281` (stop `Eid`), `:313-326` (list tasks of `Eid`), `:343-353` (log of `Tid`); `server/v2.0/handler/preheat.go:576-581` (get execution), `:644-650` (stop), `:682-693` (list tasks), `:720-725` (task log).
- **Evidence:** Each handler authorizes the URL's policy or project, then passes a raw ID to vendor-agnostic managers:
  - `retentionCtl.GetRetentionExecTaskLog(ctx, params.Tid)` → `controller/retention/controller.go:363-364` → `taskMgr.GetLog(ctx, taskID)`, which has no vendor filter (`pkg/task/task.go:233-238`).
  - `OperateRetentionExec(ctx, params.Eid, ...)` → `controller/retention/controller.go:257-267` → `launcher.Stop` → `execMgr.Stop(eid)`, which has no vendor check (`pkg/task/execution.go:249-280`).
  - `api.executionCtl.Get/Stop(ctx, params.ExecutionID)` and `api.taskCtl.GetLog(ctx, params.TaskID)` go to `controller/task/{execution_controller,controller}.go`, which are pass-throughs.
- **Chain:**
  - Reach: projectAdmin of own project A (retention: `rbac_role.go:59-64`; preheat: `:121-125`). For retention, A must also have a retention policy, which the attacker creates.
  - Primitive: read a log, list tasks, stop an execution by ID.
  - Boundary: other projects' jobs and system jobs.
  - Channel: the response body.
- **Mapping:** CWE-639, CWE-285. OWASP API1:2023 and API5:2023. ASVS V4.2.1.
- **Impact:**
  - Reads the job log of any task on the instance: replication (remote registry endpoints, private repository names), scan, GC, retention, preheat.
  - Lists retention tasks (repository names) of other projects' executions.
  - Stops any execution, including GC and scan-all. Whether stopping a scheduler execution also unschedules the periodic job persistently is **needs verification**: the comment at `pkg/task/execution.go:255-256` suggests periodic jobs are stopped.
- **Remediation:** Fetch the execution (and the task, then its execution). Require `VendorType == job.Retention/job.P2PPreheat` **and** `VendorID == policy.ID` of the already-authorized policy. Return 404 on mismatch. Add a vendor-scoped accessor to the task controller so the unscoped one cannot be misused.
- **Effort:** small.
- **Reproduction:**
  1. `GET /api/v2.0/retentions/{A_policy}/executions/1/tasks/{any_task_id}/log`.
  2. `retention.go:344` loads A's policy, `:348` `requireAccess` passes.
  3. `:353` `GetRetentionExecTaskLog(Tid)` → `controller.go:364` → `task.go:233-238` → `jsClient.GetJobLog(task.JobID)`.
- **Self-refutation:** Looked for vendor checks in `launcher.Stop`, `execMgr.Stop`, `taskMgr.GetLog` and the task controllers: none. Verdict: **survives (0.9)**. The persistent-unschedule leg is downgraded to needs verification.

### H3: Another project's security policies changed or deleted through body-supplied or path IDs
- **Severity:** High. Impact: integrity of another tenant's protective controls (tag immutability, retention, robot accounts). Likelihood: any authenticated user. Deciding assumption: High on a multi-tenant instance with default project creation; Medium if `project_creation_restriction=adminonly` and every project admin is trusted.
- **Location:**
  - `server/v2.0/handler/immutable.go:56-66` (delete by path ID), `:69-89` (update: ID from body) → `controller/immutable/controller.go:59-71` → `pkg/immutable/dao/dao.go:47-60, 119-133` (update/delete keyed on ID only).
  - `retention.go:196-213` (authz on the **body's** `scope.reference`, `p.ID = params.ID` = victim policy) → `controller/retention/controller.go:126-162` (loads `p0` but never compares its scope).
  - `preheat.go:257-272` (policy ID **and ProjectID** from body, no override) → `controller/p2p/preheat/controller.go:328-400` → `pkg/p2p/preheat/dao/policy/dao.go:82-89`.
  - `robot.go:282-317` (`updateV2Robot` authorizes `params.Robot.Permissions[0].Namespace`, not the stored `r.ProjectID`).
- **Chain:** Reach: projectAdmin of own project A. Primitive: write or delete by ID. Boundary: project B's rows. Channel: n/a (integrity).
- **Mapping:** CWE-639, CWE-863. OWASP API1:2023. ASVS V4.2.1, V4.1.3.
- **Impact:**
  - Deletes, disables or rewrites B's immutability rules, which removes B's tag protection.
  - Rewrites B's retention policy (rules, schedule, and scope moved to A).
  - Re-points B's preheat policy, or points the user's own preheat policy at B's `project_id`, so B's artifacts are distributed to the P2P provider on A's filters.
  - Disables or re-enables a B robot, or changes its expiry and permissions. This needs the robot's ID and its `B+name` (`controller/robot/controller.go:105-109`).
- **Remediation:** One rule. Load the stored object by the path ID. Authorize on **its** project. Copy only mutable fields from the body. Never accept `id` or `project_id` from the body. Example for immutable: `m0 := Get(params.ImmutableRuleID); if m0.ProjectID != projectID {404}`.
- **Effort:** small.
- **Reproduction:**
  1. `PUT /api/v2.0/retentions/{B_policy}` with body `{"scope":{"level":"project","ref":<A_id>},...}`.
  2. `retention.go:197-198` sets `p.ID = B_policy`; `:205` `requireAccess` passes on A.
  3. `:210` → `controller.go:162` `UpdatePolicy(p)` overwrites B's policy.
- **Self-refutation:** For the robot sub-case, the name must equal `r.Name` (`robot.go:291`), which lowers likelihood, so that sub-case alone would be Medium. Immutable, retention and preheat have no such friction. Verdict: **survives (0.8)**.

### Census behind H1–H3 (rules/14 §6: count the population)

ID-bearing handler operations in the project-scoped handlers read:

- **Unbound (18 sites):** notification_policy ×3, notification_job ×1, retention ×4, preheat ×5, immutable ×2, robot ×1, artifact-label ×1, scan-report ×1.
- **Correctly bound, used as positive controls for the census:**
  - label `Get/Update/Delete` (loads the object, checks `label.ProjectID`, `label.go:58-189`, `requireAccess` at :177)
  - member (SQL predicate `project_id = ? and id = ?`, `pkg/member/dao/dao.go:171, 181`)
  - robotV1 (`List{ProjectID, ID}`, `robotV1.go:122, 192, 215`)
  - retention `Get/Delete/Trigger` (load, then check the stored scope)
  - robot `Get/Delete/RefreshSec` (check `r.ProjectID`)

The correct idiom exists in-tree. The defect is that it is applied inconsistently. System-level handlers (registry, replication, GC, scanner, config, LDAP) are guarded by `RequireSystemAccess` throughout. Their census: function-level authz is present in every exported handler; awk-checked, with the only "NONE" rows being `Prepare` and `user.go` helpers that call `require*` wrappers.

### M1: Unbounded in-memory reads of attacker-pushed content in core
- **Severity:** Medium. Availability of the whole registry through one authenticated pusher. High if project creation is open **and** no ingress body limit exists. The bundled nginx sets `client_max_body_size 0` (`nginx.https.conf.jinja:67`).
- **Location:** `server/middleware/blob/put_manifest.go:37, 67`; `server/middleware/quota/util.go:52`; `server/middleware/cosign/cosign.go:77`; `controller/artifact/processor/chart/chart.go:87`.
- **Evidence:** `body, err := ioutil.ReadAll(r.Body)` on manifest PUT bodies before forwarding. `content, err := ioutil.ReadAll(blob)` on a chart layer, then helm decompression (`GetDetails`). govulncheck flags GO-2025-3601 (helm OOM on a crafted archive) as reachable via `controller/retention` init only, so it is a module-level concern, not a confirmed call path. The bounded idiom exists at `controller/artifact/annotation/v1alpha1.go:83` (`io.LimitReader(icon, 1<<20)`). 1 bounded site against 5 unbounded.
- **Mapping:** CWE-400, CWE-409. OWASP API4:2023.
- **Impact:** core OOM-kill and restart. All tenants lose API and registry access.
- **Remediation:** `r.Body = http.MaxBytesReader(w, r.Body, 4<<20)` for manifests (distribution's own manifest limit is the natural bound). `io.LimitReader(blob, maxChartSize)` plus a decompressed-size cap for charts.
- **Effort:** small.
- **Reproduction:** Push a 2 GiB manifest body to `/v2/A/r/manifests/t`. The path is `put_manifest.go:37` `ReadAll`, which buffers it all. Not executed (no instance).

### M2: Reachable vulnerable dependencies and an out-of-support Go baseline (`go.mod`)
- **Severity:** Medium (aggregate). Any single item might be rated higher by a reader who verifies exploitability. Tool severity was re-rated here in context.
- **Location:** `go.mod:3` (`go 1.17`; Makefile builds with `golang:1.17.7`), `:29` `golang-jwt/jwt/v4 v4.1.0`, `:34` `gorilla/csrf v1.6.2`, `helm.sh/helm/v3 v3.7.1`, `golang.org/x/net v0.0.0-20211013…`, `prometheus/client_golang v1.11.0`, `beego v1.12.9`.
- **Evidence (govulncheck, symbol-level, entry in scope):**
  - GO-2025-3553 (`jwt.ParseUnverified`), reached **pre-auth** from `server/middleware/security/v2_token.go:50`. Fixed 4.5.2.
  - GO-2025-3607 (`gorilla/csrf` Referer validation). Fixed 1.7.3.
  - GO-2024-2554 (`helm chart.Validate`), from `controller/artifact/processor/chart/chart.go:92`. Fixed 3.14.1.
  - GO-2022-0322 (`promhttp`), from `server/registry/util/util.go:83`. Fixed 1.11.1.
  - GO-2023-1571 and GO-2024-2687 (x/net http2), via HTTP clients.
  - About 20 further symbol-level hits are reachable **only through package `init`** (docker/containerd types imported via `controller/retention`). They are triaged as non-exploitable reachability and kept in `w2out/govuln.json`, not reported.
  - trivy, module-level: 128 advisories, including beego CVE-2022-31836 (path traversal, fixed 1.12.11), which govulncheck did **not** find reachable in the 84 analysable packages.
  - Go toolchain: this machine's `go version` is go1.27.1. The module targets 1.17, ten minor releases behind and outside Go's two-release support window (EOL date not looked up: no network).
- **Mapping:** CWE-1104, CWE-1395. OWASP A06:2021.
- **Impact:** A pre-auth memory amplification on `/v2` bearer parsing. A weakened CSRF origin check. Helm parsing bugs on user-pushed charts.
- **Remediation:** Bump the listed modules to at least the fixed versions. Set `go` ≥1.22 (this also closes M7). Add `govulncheck ./...` as a failing CI gate.
- **Effort:** medium (beego v1 → v2 is large; the rest are small).
- **Reproduction:** `GOFLAGS=-mod=vendor govulncheck -format json $(cat w2out/okpkgs.txt)`.

### M3: Webhook SSRF guard is a no-op, and no egress control exists
- **Severity:** Medium. Blind SSRF from the jobservice network position by any project admin (any user by default). High on a cloud host if the metadata endpoint is reachable; unverified.
- **Location:** `server/v2.0/handler/notification_policy.go:227-233`.
- **Evidence:**
  ```go
  for _, target := range policy.Targets {        // Targets []EventTarget (values: pkg/notification/policy/model/model.go:21)
      url, err := utils.ParseEndpoint(target.Address)
      // Prevent SSRF security issue #3755
      target.Address = url.Scheme + "://" + url.Host + url.Path   // writes a copy; discarded
  ```
  Only the scheme check inside `ParseEndpoint` takes effect. There is no private or metadata range check anywhere in scope, and `SkipCertVerify` is accepted per target.
- **Falsification:** If this sanitizer were deleted, nothing observable would change. There is no `notification_policy_test.go`.
- **Mapping:** CWE-918. OWASP API7:2023.
- **Impact:** Harbor POSTs event payloads to internal hosts the attacker chooses (blind).
- **Remediation:** `for i := range policy.Targets { t := &policy.Targets[i]; ... }`. In the sender, add a dial-time private-range and link-local block (resolve, pin, connect), no redirects, and optional signing (HMAC).
- **Effort:** small (loop) / medium (egress guard).

### M4: Audit-log failures are silent, and privilege changes are never audited
- **Severity:** Medium. Detection and accountability gap; no direct exploit.
- **Location:** `controller/event/handler/auditlog/auditlog.go:64-67` (`_, err := audit.Mgr.Create(...); if err != nil { log.Debugf("add audit log err: %v", err) }`, then return nil). `controller/event/handler/init.go:50-58`: only push, pull, delete, project create/delete, repo delete and tag create/delete are subscribed.
- **Evidence:** No audit event exists for `SetUserSysAdmin` (`user.go:327`), member role changes, robot create/update/secret refresh, configuration updates, webhook policy changes, or admin password set. The only audit topics are the eight at `init.go:51-58`.
- **Falsification:** If the audit insert silently failed, nothing at default log level would differ.
- **Mapping:** CWE-778, CWE-223. ASVS V7.1.3, V7.2.2.
- **Impact:** H1–H3 abuse and insider privilege grants leave no audit trail, and audit loss is invisible. Privacy note: audit rows hold usernames with no purge path in scope (GDPR retention: needs a retention decision).
- **Remediation:** Log at Error and increment a metric on failure. Add audit events for the privilege-changing operations. Define audit retention.
- **Effort:** medium.

### M5: Job-status hook endpoints have no authentication in code
- **Severity:** Medium, **needs verification**. High if the deployment exposes core's `/service/notifications` (for example an ingress without the nginx 404 rule).
- **Location:** `server/route.go:53, 55-59`; `server/handler/job_status_hook.go:37-45`.
- **Evidence:** The handler decodes a `job.StatusChange` and calls `task.HkHandler.Handle`, with no secret, no `IsSolutionUser`, and no middleware check. The only guard found is the nginx template `location /service/notifications { return 404; }` (out of scope).
- **Mapping:** CWE-306. OWASP API2:2023.
- **Impact:** Forged task status (for example, marking scans or replications Success or Error), driving post-functions such as replication webhooks (`init.go:64-69`).
- **Remediation:** Require the core secret (the `secret` generator already exists, `security/secret.go`) and `RequireSolutionUserAccess` on these routes.
- **Effort:** small.

### M6: No abuse control on credential paths
- **Severity:** Medium.
- **Location:** `server/middleware/security/robot.go:33-71` (robot secret check, no throttle); `oidc_cli.go:47-73` (CLI secret, no throttle). The basic-auth path relies on `core/auth/authenticator.go:33-35, 151-160`: an in-memory, per-process, per-username 1.5 s freeze, which is not shared across replicas and is keyed on attacker-chosen names. Zero rate-limiter sites in scope.
- **Mapping:** CWE-307. OWASP API4:2023. Router principle 5(a).
- **Impact:** Online guessing of user-set robot secrets (minimum 8 characters, `robot.go:227`) and OIDC CLI secrets.
- **Remediation:** A shared-store limiter keyed on principal and source IP across all generators; lockout with backoff; alerting.
- **Effort:** medium.

### M7: Pointer to a loop variable published to async handlers under `go 1.17`
- **Severity:** Medium. Correctness and data race; misrouted webhook deliveries within one policy.
- **Location:** `controller/event/handler/util/util.go:35` (`Target: &target`), with `go.mod:3`.
- **Evidence:** `notifier.Notify` dispatches handlers in goroutines (`pkg/notifier/notifier.go:191-207`), and `HookMetaData.Resolve` copies the pointer (`pkg/notifier/event/event.go:52`). Reproduced the language behaviour **3/3** with the same shape under a `go 1.17` directive and toolchain 1.27.1: output `[c c c]`, against `[c b a]`/`[a b c]` under `go 1.22` (`w2out/loopvar/`). The product path itself was not executed.
- **Mapping:** CWE-362. sota-golang rules/03 rates this HIGH when <1.22 with closures. Rated Medium here because only multi-target policies are affected and no tenant boundary is crossed.
- **Impact:** For a policy with ≥2 targets, events (and the last target's `AuthHeader`) can all go to the last target.
- **Remediation:** `t := target; Target: &t`.
- **Effort:** trivial.

### M8: Weak KDF for user-settable robot secrets
- **Severity:** Medium.
- **Location:** `server/v2.0/handler/robot.go:227-230` → `common/utils/encrypt.go:50` (`pbkdf2.Key(..., 4096, 16, sha256)`).
- **Evidence:** 4,096 iterations against a library floor of 600,000 for PBKDF2-HMAC-SHA256 (sota-code-security rules/02:18, rules/04:24). The accepted secret policy is 8 characters with three classes.
- **Mapping:** CWE-916. ASVS V2.4.2 (iteration count).
- **Impact:** A DB or backup leak makes chosen robot secrets cheap to crack. The same KDF is used for user passwords (out-of-scope code, noted).
- **Remediation:** Argon2id (or PBKDF2 ≥600k) with a version prefix and re-hash on next successful auth.
- **Effort:** medium.

### M9: Sysadmin sets any user's password directly, unaudited
- **Severity:** Medium. The library checklist rates this HIGH; it is rated on the §1 chain because the actor is already tier-0, and the gap is accountability. Deciding assumption: Medium where sysadmins are few and trusted.
- **Location:** `server/v2.0/handler/user.go:291-325`. The old-password check runs only when `matchUserID` is true (`:297`). An admin sets `NewPassword` for `uid` (`:319`). Not audited (M4).
- **Mapping:** CWE-640, CWE-778.
- **Remediation:** Admin-triggered reset flow, or at least an audit event plus user notification.
- **Effort:** medium.

### M10: No cross-project deny tests for the affected handlers
- **Severity:** Medium.
- **Location:** `server/v2.0/handler/`: 12 of 36 handler files have tests. 4 test files assert Forbidden/Unauthorized at all (`user_test.go`, `quota_test.go`, `scan_all_test.go`, `scanner_test.go`). None of `notification_policy`, `notification_job`, `retention` or `immutable` has a test file. `preheat_test.go` covers converters only.
- **Mapping:** sota-testing suite health; rules/03 checklist (automated cross-tenant deny matrix).
- **Remediation:** One table-driven test per ID-bearing route: caller in project A, object in project B, expect 404.
- **Effort:** medium.

### Low and Info (abbreviated; full fields)

- **L1** `server/middleware/csrf/csrf.go:57`. An invalid `CSRF_KEY` (wrong length) is written to logs verbatim (`"Invalid CSRF key from environment: %s"`). CWE-532. Impact: a CSRF signing key that was set at the wrong length leaks to log readers. Fix: log `len(key)` only. Trivial.
- **L2** `server/middleware/security/robot.go:57`. `utils.Encrypt(secret, salt) != robot.Secret` is a variable-time string compare. It compares PBKDF2 outputs, so the timing signal is of little use. CWE-208. Fix: `subtle.ConstantTimeCompare`. Trivial.
- **L3** `artifact.go:72`, `repository.go:59`, `scan.go:44`, `config.go:69`. The responder from `SendError` is discarded, so execution continues: a path-unescape failure proceeds with the raw name, and a config conversion error returns 200 with a partial payload. Census: 4 of 644 `SendError` sites. CWE-755. Fix: `return`. Trivial.
- **L4** `artifact.go:459`. `AddLabel` attaches any `label.ID`, including another project's project-scoped label (`pkg/label/manager.go:95-103` has no scope check). Impact: another project's label metadata shown on the attacker's artifacts. CWE-639. Small.
- **L5** `scan.go:102`. The scan log is fetched by report UUID without binding it to the authorized artifact. UUIDv4 entropy mitigates, but it is not authorization. Small.
- **L6** `preheat.go:492` returns preheat instance `auth_info` (credentials) in plaintext to sysadmins. `handler/model/user.go:49` returns any OIDC user's CLI secret to sysadmins via `GetUser`. CWE-200 (write-only secret pattern). Small.
- **L7** `log/log.go:27` attaches an unbounded client `X-Request-ID` to logs. `basic_auth.go:41-48` logs client IP from spoofable `X-Forwarded-For`. CWE-117. Trivial.
- **I1** `controller/event/handler/init.go:24-61` discards 32 `notifier.Subscribe` errors. `Handle` errors on duplicate type keys (`pkg/notifier/notifier.go:82-85`). No duplicate exists today: a sed+`uniq -d` sweep over the 32 lines printed none. A future type-name collision would silently drop a handler, including audit. Trivial.

---

## 7. Present is not applied (silent-control pass)

| control credited | falsification: if it were a no-op, would anything differ? | verdict |
|---|---|---|
| Webhook SSRF normalization (`notification_policy.go:232`) | No. It already is one (copy semantics). No test. | **Inert** (M3) |
| Project RBAC `RequireProjectAccess` | Yes for the URL project. Population: guards the URL project at 73 call sites, while the object acted on is unbound at 18 ID-bearing sites. | **Partial reach** (H1–H3) |
| Audit log | Failures are visible only at Debug. | **Silent on failure** (M4) |
| Job-status hook protection | Lives entirely in an out-of-scope proxy rule. | **Not in force in code** (M5) |
| CSRF (gorilla) | Real (SameSite=Strict, header token). Only when the session is carried. Dependency CVE in M2. | present, effective (by reading; not executed) |
| Login lockout | In-process map, 1.5 s, per replica | weak (M6) |
| `make gosec` (out of scope, context) | `... ./... \| true` (`Makefile:514, 516`): the pipe into `true` discards output and always exits 0, and no workflow invokes it. `CONTRIBUTING.md:320` claims "drone CI ... checked via gosec"; no drone or travis config exists in the tree. | **Prose standing in for a control** (out of scope, §11) |

My own sweeps were controlled the same way:
- Every absence was paired with a positive control in the same run: `RequireProjectAccess(` → 73; gitleaks synthetic tokens → 2; the ioutil form → 5 hits where the library grep found 0.
- Denominators were printed: 232 files, 84/89 packages.
- golangci-lint's 35 was recognised as a capped page (`max-same-issues=3`), not a total.

---

## 8. Refutation (weaker form, stated plainly)

Every Critical/High got only a **self-refutation** in this same context:
- re-read the code at the pinned tree, not my write-up;
- looked for `Prepare` hooks, middleware or DAO predicates that would bind the object;
- defaulted to REFUTED where ambiguous.

The threshold was fixed before rating: survive at ≥0.7. Results:
- H1: 0.9
- H2: 0.9, with the "unschedules periodic jobs" leg downgraded to needs verification
- H3: 0.8, with the robot sub-case alone at Medium

The pattern sweep after refutation is the census in §6, and it produced H3 from the H1 pattern. **This is not the standard.** The standard is an independent refuter handed only the code. H1–H3 are load-bearing for the "not ready" verdict, so escalate them to `/sota-deep-audit` or an independent reviewer before any external disclosure.

---

## 9. Questions (operator unavailable: defaults chosen, audit continued)

1. **Tenancy model.** Is this instance multi-tenant with `project_creation_restriction=everyone` (the code default)?
   - (a) Yes: H1–H3 stay High; fix this sprint.
   - (b) adminonly, with trusted project admins: H3 drops to Medium, H1–H2 stay High (credential and job-log disclosure across projects is still cross-tenant).
   - **Default chosen: (a)**, because it is the shipped default and every leg is in code.
2. **Hook exposure.** Is core deployed only behind the bundled nginx?
   - (a) Yes: M5 stays Medium (defence in depth).
   - (b) Helm/ingress or direct core service exposure: M5 becomes High.
   - **Default: Medium, needs verification.** Recommendation: add the secret check regardless; it is small and removes the dependency on the proxy.
3. **Admin password set (M9).** Is it an accepted design?
   - (a) Accept, and add audit plus notification.
   - (b) Replace with a reset flow.
   - **Default: report at Medium; recommend (a)** as the cheaper step that closes the accountability gap.
4. **Stack profile.** `<owner>.md` was not applied to an upstream repository. Recorded, not asked.

---

## 10. Decision ledger (reconstructed, unconfirmed: no ADRs, no git history)

| decision | evidence re-checked this session | verdict |
|---|---|---|
| Authorize on the URL project, then act on a raw object ID | 18 unbound sites against the correct idiom in label, member and robotV1 | **UNJUSTIFIED** (root cause of H1–H3) |
| Go 1.17 language/toolchain baseline (`go.mod:3`, `Makefile:160 golang:1.17.7`) | Local toolchain is 1.27.1; loop-var semantics reproduced 3/3 (M7) | **STALE** |
| beego v1 for router, ORM and session | govulncheck: two beego advisories with no fix version on the v1 line are reachable (GO-2024-3331, GO-2025-3585) | **STALE** (maintenance of the v1 line not verified; no network) |
| PBKDF2-SHA256 at 4,096 iterations | Measured from code: 4096 against library floor 600,000 | **STALE** |
| In-process 1.5 s login freeze | Code read; not shared across replicas | **UNJUSTIFIED** for HA deployments |
| Network position as the auth for job hooks | nginx template 404; Helm topology unknown | **UNVERIFIABLE here.** Needs the deployed ingress config. |
| CHANGELOG / ROADMAP as the record | `CHANGELOG.md` tops out at v1.8.0 against `VERSION` v2.5.1; `ROADMAP.md` "Last Updated: July 2021" | **STALE** (out-of-scope docs; noted) |

**Knowledge outside the repo.** Contribution and decision history lives in GitHub PRs and issues and the Harbor project board (per `ROADMAP.md`), none of which is in this tree. No agent memory store or IDE notes exist in the workspace. Absence was checked by `ls -a` for `AGENTS.md`, `CLAUDE.md`, `.idea`, `.vscode`; it is a one-method check, so treat it as unverified.

---

## 11. Remediation roadmap (risk reduction per unit of effort)

1. **One authz fix pattern, about one day:** H1, H2, H3, L4, L5. Add `loadAndAuthorize(ctx, id) (obj, error)` helpers that bind the object to the authorized project or vendor. Never take `id` or `project_id` from bodies. Return 404. Land it together with M10's deny-matrix tests so it cannot regress.
2. **Trivial hardening, under an hour:** M7 loop var, L1 CSRF key log, L2 constant-time compare, L3 missing returns, M3 loop fix.
3. **Job hook secret (M5)** and **body limits (M1)**: small.
4. **Dependency upgrade (M2)**, with govulncheck as a failing CI gate; beego v2 migration planned separately.
5. **Audit coverage and failure visibility (M4)**, plus admin password flow (M9).
6. **Abuse control (M6)** and **KDF migration (M8)**: medium, design-bearing.
7. Low/Info hygiene: L6, L7, I1.

**Out-of-scope observations (not counted):**
- `Makefile:509-517` gosec target cannot fail (`| true`) and is not wired into CI. `CONTRIBUTING.md:317-320` describes travis/drone gates that are absent from the tree.
- No secret scanning in CI (`.github/workflows/*`: CodeQL v1 only).
- `core/auth` lock map grows with attacker-chosen usernames.
- `pkg/notification` sender has no SSRF guard or signing.

## 12. Positive observations (each evidenced by code read, not by execution)

- The correct object-scoped idioms exist: `label.go` `requireAccess(label)` on the loaded label; member DAO SQL carries `project_id`; robotV1 lists by `{ProjectID, ID}`.
- `v2auth` requires pull on the blob-mount source repository (`access.go:91-97`). Registry authz is per repository and action.
- `ListAllRepositories` and `Search` filter to the caller's authorized and public projects.
- User self-service handlers restrict to self or sysadmin (`requireReadable/Modifiable`), and self password change requires the old password.
- CSRF uses SameSite=Strict, a header token, and Secure unless the endpoint is `http://`.
- Unit tests run with `-race` (`tests/coverage4gotest.sh:32`).
- The icon annotation read is bounded (`io.LimitReader 1 MiB`).

## 13. Depth reached and not reached

**Depth reached**
- govulncheck was symbol-level over 84/89 packages. The 5 handler and route packages (where H1–H3 live) got **no** reachability analysis.
- gosec ran with type errors in 66 packages, so its taint analyzers could not see through them.
- gitleaks covered the working tree only.
- trivy was module-level, so its 128 advisories are an upper bound, not reachable exposure.
- All authz findings are static read paths; the only executed reproduction was the loop-variable semantics.

**Not reached**
- **Git history:** no secrets-in-history scan, no `git log -G` variant hunt, no churn ordering, no prior-fix review.
- **Scanners not installed:** semgrep/opengrep, osv-scanner, trufflehog, staticcheck.
- **Generated code:** the swagger code (`server/v2.0/restapi`, `models`) does not exist, so its parameter validation (max lengths, pattern constraints) was not seen.
- **Out of scope by agreement:** `lib/q` query parsing and `lib/orm` (the SQL/sort injection surface behind every `q=`/`sort=`); `pkg/oidc` token verification; `core/` auth backends.
- **Domains not walked:** sota-golang 02/06, sota-api-design 01/02, sota-observability, sota-architecture, sota-code-security 11/16/20. These are **holes in this audit**, not clean results.
- **Unverified assumptions:** deployment ingress (M5); whether stopping a scheduler execution unschedules periodic jobs (H2); cloud metadata reachability (M3); whether a case-variant path such as `/service/Notifications/…` passes nginx's case-sensitive `location` and is still routed by core (beego's case-sensitivity setting could not be read without module source).
- **No independent refuter** was used for H1–H3.

---

**Library feedback (for `/sota-report`).** The sota-golang rules/04 audit checklist's unbounded-body probe, `grep -rn 'io.ReadAll(r.Body\|io.ReadAll(req.Body'`, returned **0** on this tree. The same tree has 4 non-test `ioutil.ReadAll(r.Body)` sites (5 including tests), so a literal checklist walk would have reported M1's class as clean. The probe should also match the deprecated `ioutil.ReadAll` spelling.
