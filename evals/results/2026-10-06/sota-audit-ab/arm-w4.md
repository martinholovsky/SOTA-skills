# SOTA audit: w4 (`VERSION` = v2.5.1), Go `src/server` + `src/controller` + `src/go.mod`

Mode: AUDIT. The operator was unavailable, so every question is recorded with the default I chose (see §6). Nothing in the workspace was edited, and the fix step was skipped as instructed.

## 1. Scope (agreed in advance)

| candidate | size | status |
|---|---|---|
| `src/server/**/*.go` (non-test) | 123 files, 15,017 lines | in scope |
| `src/controller/**/*.go` (non-test) | 109 files, 16,860 lines | in scope |
| `src/go.mod` | 235 lines, plus `go.sum` used as scanner input | in scope |
| uncommitted work / branch diff | not sizeable: `.git` was removed | **not reached**: there is no history, base or diff |

The total is 232 files and about 31.9k lines (gosec reports `Files: 232, Lines: 31877`, which matches the file list).

**What the scope excludes.** These are read for context only and produce no findings: `src/core` (the HTTP server construction and timeouts, beego controllers, the auth providers and login lock), `src/pkg` (DAOs and managers, including the token parser), `src/common`, `src/lib`, `src/jobservice` (the webhook sender), `make/` (nginx templates, Dockerfiles), the Makefile, CI workflows and the generated swagger packages, which are absent from the tree.

**Partition.** The scope is too large to read line by line, so I did not. The pass ran in this order:
- (a) authentication middleware, read in full;
- (b) registry v2 routes, read in full;
- (c) v2.0 API handlers: a scripted authz census over all 175 handler methods, then a manual object-to-parent-binding review of every handler that takes an object ID;
- (d) controllers reached from (c);
- (e) scanner and grep sweeps over all 232 files.

Everything outside that list was not read manually (see "Not reached").

## 2. Coverage table (as it ended)

| surface found | owning skill | loaded? | if not, why |
|---|---|---|---|
| Go source (232 files) | sota-golang | yes: SKILL.md, rules/08 §2 plus its checklist, and the checklist items of rules/01, 03, 04 and 05 (walked via sweeps) | rules/02 (design), 06 (performance) and 07 (tooling) checklists not walked: time |
| HTTP API: 175 go-swagger handler methods plus `/v2` registry routes | sota-api-design / sota-code-security rules/03 (authz) | code-security rules/02, 17, 19 and 22 were consulted by section; rules/03's checklist **was not walked item by item** | the authz review was done as a population census instead (see §4) |
| AuthN middleware (basic, robot, OIDC CLI, ID token, v2 bearer JWT, session, proxy-cache secret) | sota-code-security rules/02, 17, 22; sota-identity-access | code-security sections read; identity-access **not loaded** | **hole**: the OIDC/SAML-style federation design was not assessed |
| Session / CSRF middleware | sota-code-security rules/17; sota-golang rules/04 §1, §4a | partially, by section | — |
| Webhook targets, replication/preheat/scanner endpoints (outbound URLs) | sota-golang rules/05 §4c; sota-api-design rules/06 | golang rules/05 §4c only | api-design rules/06 not loaded |
| Data stores (beego ORM through `pkg/*/dao`) | sota-databases | **not loaded** | DAOs are out of scope; in scope there is one raw query (`SELECT 1`) |
| Concurrency (20 `go func`, notifier fan-out) | sota-golang rules/03 / sota-async-concurrency | golang rules/03 checklist only | sota-async-concurrency not loaded |
| `go.mod` dependencies | sota-golang rules/08; sota-devsecops | rules/08 yes; devsecops **not loaded** | — |
| Logging (`log.G(ctx)`, secrets in logs) | sota-observability | **not loaded** | **hole**: only the secret-in-log angle was checked |
| Tests for the authz logic | sota-testing | **not loaded** | **hole**: no check whether the BOLA paths have tests |
| CI config, Dockerfiles, IaC, shell, agent files | devsecops / sandboxing / shell / skill-security | n/a | out of scope; read only as enforcement-depth context |
| Stack profile (`~/.claude/profiles/<owner>.md`) | router principle 4 | read | It describes the operator's own stack; this is a third-party tree, so it is applied only to Go baseline items (golangci-lint with gosec/errcheck). There is no golangci config here (see Depth) |
| Project conventions (`CONTRIBUTING.md`, `CLAUDE.md`/`AGENTS.md`) | — | no agent file exists; CONTRIBUTING was not read for conventions | — |
| Day zero | — | LICENSE present; CodeQL workflow present; no secret scan in CI; no agent file; history unavailable | not a day-zero repo (it is a large, established codebase); `init-gates.sh` was not offered |

## 3. Findings

Severity follows `sota/rules/03` §1. Each High names its chain. The "default config" premise used throughout is `PROJECT_CREATION_RESTRICTION` defaulting to `everyone` (`src/lib/config/metadata/metadatalist.go:117`, read this session). Under that default, **any authenticated user can create a project and becomes its projectAdmin**, so "projectAdmin of some project" means "any authenticated user".

| file:line | rule violated | severity | effort | fix |
|---|---|---|---|---|
| `server/v2.0/handler/notification_policy.go:155` (Get), `:143` (Delete), `:116`+`:130` (Update takes `id` from the **body**; `params.WebhookPolicyID` is never used); `server/v2.0/handler/notification_job.go:34` (ListWebhookJobs) | code-security rules/03 BOLA: the object is not bound to the authorized project | **High** | small | Load the policy by ID, require `policy.ProjectID == projectID(path)`, otherwise return 404. In Update, set `policy.ID = params.WebhookPolicyID` and reject a body `id` that differs |
| `server/v2.0/handler/preheat.go:581` GetExecution, `:650` StopExecution, `:693` ListTasks, `:725` GetPreheatLog | BOLA, plus no vendor-type filter | **High** | small | Resolve the execution/task, require `VendorType == P2PPreheat` and the vendor policy to belong to the path project |
| `server/v2.0/handler/retention.go:198`+`:205` (Update authorizes on the **body's** `scope.reference` but writes `params.ID`), `:277` OperateRetentionExecution (`params.Eid`), `:326` ListRetentionTasks (`params.Eid`), `:353` GetRetentionTaskLog (`params.Tid`); `controller/retention/controller.go` GetRetentionExecTaskLog calls `taskMgr.GetLog(taskID)` with no vendor check | BOLA | **High** | small | Authorize on the **stored** policy (`GetRetention(params.ID)`) before Update, and require `exec.VendorID == params.ID` and `task.ExecutionID == params.Eid` with retention vendor type |
| `server/v2.0/handler/immutable.go:62` Delete (`params.ImmutableRuleID`, unbound), `:84` Update (ID from body); `controller/immutable/controller.go:68` EnableImmutableRule toggles by bare ID | BOLA on a security control (tag immutability) | **High** | small | Fetch the rule, require `rule.ProjectID == projectID`, and use the path ID. The DAO `ormer.Update(ir,"TagFilter")` updates by primary key only, so setting `ProjectID` (pkg dao:48) does not scope it |
| `server/v2.0/handler/notification_policy.go:228-233` | golang rules/05 §4c SSRF: a caller-chosen destination with no IP-class check | Medium (High if project admins are a lower trust tier than system admins on a cloud host) | medium | Resolve and deny loopback, link-local (169.254/16), RFC1918 and the core/jobservice addresses at **dial time** (`net.Dialer.ControlContext`). The "Prevent SSRF #3755" comment only strips query and userinfo |
| `server/middleware/security/session.go:37-47` together with `controller/user/controller.go` (`SetSysAdmin`, `Delete`, `UpdatePassword`: no session revocation) | code-security rules/17 §1 (regenerate on privilege change; revoke all sessions on password change) | Medium | medium | The session stores a whole `models.User` snapshot, and `local.IsSysAdmin` reads `SysAdminFlag` from it. Demotion, deletion and password change therefore leave admin power live until the session expires. Re-load the user per request or keep a revocation epoch |
| `server/middleware/security/robot.go:42-57`, `server/middleware/security/oidc_cli.go:65` | code-security rules/02 (rate limit + lockout), rules/19 | Medium | medium | Robot secrets and OIDC CLI secrets can be **user-chosen** (8 characters minimum: `robot.go` RefreshSec / `user.go` SetCliSecret). These paths bypass `auth.Login`'s per-username 1.5 s lock (out of scope, `core/auth/authenticator.go:33`), so guessing is unthrottled. Add per-principal and per-IP throttling |
| `server/middleware/blob/put_manifest.go:37,67`; `server/middleware/quota/util.go:52`; `server/middleware/cosign/cosign.go:77` | golang rules/04 / code-security rules/06: unbounded `ioutil.ReadAll(r.Body)` | Medium | trivial | Wrap the body in `http.MaxBytesReader` (manifests: 4 MiB is distribution's own limit). There is no `MaxBytesReader` anywhere in server/core/lib, and nginx sets `client_max_body_size 0` |
| `src/go.mod` (trivy: 128 advisories, 4 Critical / 55 High); reachable example: `golang-jwt/jwt/v4 v4.1.0` (CVE-2025-30204, fixed 4.5.2) via `server/middleware/security/v2_token.go:50` → `pkg/token.Parse` → `jwt.ParseWithClaims` (vendored `parser.go:97 strings.Split`) on **any unauthenticated `/v2` bearer header** | golang rules/08 §1 | Medium for the shown chain (memory amplification, bounded by the 1 MB header cap); the other 127 are **needs verification** for reachability | large | Upgrade jwt to ≥ 4.5.2 now. Run symbol-level `govulncheck` once the swagger packages are generated (it could not load them here) and triage the beego (CVE-2022-31836 etc.), x/net, x/crypto and grpc rows |
| `src/go.mod:3` `go 1.17` (and `Makefile:160 GOBUILDIMAGE=golang:1.17.7`, context) | golang rules/08 §2, rules/03 checklist (go line < 1.22) | Medium (by §1: no attacker leg shown); the skill's checklist rates TLS/x509 GODEBUG **High**, and both ratings are stated | small–medium | Measured `go list -f '{{.DefaultGODEBUG}}' ./core` on go1.27.1: `tlssha1=1, rsa1024min=0, x509negativeserial=1, x509usepolicies=0, httpmuxgo121=1, tlsmlkem=0, panicnil=1`. The shipped toolchain 1.17.7 is EOL, so stdlib CVEs are missing from the go.mod scan entirely. Raise the `go` line and the toolchain |
| `controller/event/handler/util/util.go:35` `Target: &target` | golang rules/03 checklist (loop-var semantics under go < 1.22 with async consumers) | Medium (skill checklist: High) — **needs verification** (`-race` not run) | trivial | The pointer to the shared loop variable escapes to `notifier.Notify` goroutines (`pkg/notifier/notifier.go:191-195`), so a multi-target policy can fire with the wrong target, and it is a data race. Use `t := target; &t` |
| `server/middleware/csrf/csrf.go:57` | code-security rules/07 (secrets in logs) | Low | trivial | When `CSRF_KEY` has the wrong length the key **value** is logged. Log its length only |
| `server/middleware/security/robot.go:57` | code-security rules/22 (constant-time comparison) | Low | trivial | `subtle.ConstantTimeCompare` on the hex digests. Separately, PBKDF2 at 4096 iterations (`common/utils/encrypt.go:50`, out of scope) is far below current guidance |
| `server/middleware/security/basic_auth.go:31-43` | code-security rules/07 / observability: trusting a client-supplied header | Low | small | `GetClientIP` trusts `X-Forwarded-For` by default, so the IP in login-failure logs is attacker-chosen. Trust it only from configured proxies |
| `server/v2.0/handler/user.go:321-322` | golang rules/01 §1 | Low | trivial | It logs and returns `err` (nil) instead of `err2` when `UpdatePassword` fails. `user.go:311` also checks "new == old" against the **caller's** password, not the target user's |
| `controller/retention/controller.go:111,147,151,173,191` | golang rules/01 §5 (panic from unchecked `.(string)` on user-supplied `trigger.settings.cron`) | Low | trivial | Use comma-ok assertions. There is no in-tree recovery middleware, so net/http's per-connection recover only drops the request |
| `server/registry/catalog.go:87-90` | golang rules/05 §5 (integer overflow) | Low | trivial | `lastEntryIndex+1+maxEntries` overflows for `n` near MaxInt and panics with slice bounds out of range. It needs catalog-read (system) permission. Cap `n`. The handler also loads every repository into memory before paging |
| `server/route.go:51-57` / `server/handler/job_status_hook.go:36` | code-security rules/14 §3 (control lives outside the code) | Low (Medium if any ingress routes `/service/notifications` to core) | small | The status hooks have no in-app authentication. They rely on nginx `return 404` (`make/.../nginx.https.conf.jinja:227`) and on unguessable job IDs. Require the jobservice secret context |
| `server/v2.0/handler/search.go:248` | code-security rules/10 (comment claims a control) | Info | trivial | `panic(err) // let the recovery middleware deal with this`: no recovery middleware exists in tree |
| gosec G104 ×62 (31 `notifier.Subscribe`, 17 `lib.JSONCopy`), e.g. `notification_policy.go:86` | golang rules/01 §1 | Low | small | An ignored `JSONCopy` error on request bodies yields zero-valued models silently. Check it |

Scanner false positives I dismissed after reading the code:
- G404 at `controller/registry/controller.go:218`: health-check jitter, not security randomness.
- G101 at `csrf.go:21`: a header name.
- G118 at `replication/execution.go:120`: a deliberate background context with a worker pool and `recover`, documented in a comment.

## 4. Present vs applied

**The authz census, population against claim.** Every one of the 175 handler methods passes through a `Require*` call or a helper that wraps one. 12 have none in-body, and all 12 were reviewed: they are public endpoints (health, ping, icon, systeminfo, retention metadata) or user handlers using local helpers (`requireReadable`, `requireModifiable`, and so on). So authorization is **present on 175/175**. That is the misleading half.

**The binding census.** Among project-scoped handlers that take a child-object ID, the correct pattern ("load the object, authorize on its *stored* owner") is applied at:
- label Get/Update/Delete (3);
- robot Get/Delete/Update/RefreshSec (4);
- member Get/Update/Delete (3, scoped in the controller);
- retention Get/Delete/Trigger/ListExecutions (4);
- replication task-in-execution (1);
- preheat ListExecutions (1).

That is **16 sites**. It is **absent at 14 sites** (the four High rows above). The control exists and enforces nothing for those 14: the check authorizes the *path* project and then acts on an *unrelated* ID.

**Falsification.**
- Webhook GET returns `auth_header` (`handler/model/notification_policy.go:37`), so a cross-project read yields another tenant's webhook credential. That difference is observable.
- The "SSRF fix" at `notification_policy.go:233` would behave identically for `http://169.254.169.254/` if removed. It is a no-op against that class.

**Enforcement depth (context, out of scope):**
- CI runs `go test -race` per package (`tests/coverage4gotest.sh:32`). Met.
- There is no `govulncheck` and no golangci-lint config in the tree.
- The Makefile `gosec` target pipes to `| true` (`Makefile:514,516`), so it can never fail, and it is not invoked by CI.
- CodeQL uses `codeql-action@v1`.

**My own sweeps.**
- The first grep sweep was **invalid**: zsh passed `$F` as one argument and every grep hit "File name too long". I discarded it and re-ran from a file list.
- Every absence claim had a positive control in the same pass: `^package ` → 232; `utils.Encrypt` → 3 files; `LimitReader` over `controller/` → 1 hit before trusting 0 over server/core/lib.

## 5. Decisions

These are reconstructed from the tree only; with no git history, PR rationale is **unreachable**.

| decision | verdict | basis |
|---|---|---|
| beego v1.12.9 as router, session and ORM layer | **STALE** | trivy lists 2 Critical and 3 High advisories against it. Session-snapshot authz depends on it |
| `go 1.17` / golang:1.17.7 toolchain | **STALE** | The toolchain is EOL. GODEBUG defaults were measured weaker this session |
| Webhook URL normalization as the SSRF mitigation ("#3755") | **UNJUSTIFIED** as a complete control | It strips components and does not restrict destinations |
| `/service/notifications` protected only at nginx | **UNVERIFIABLE** | It holds for the bundled nginx. Other ingress paths were not examinable |
| `CHANGELOG.md` stops at v1.8.0 while `VERSION` is v2.5.1 | **STALE** documentation | Out of scope; noted only |

**Knowledge outside the repo.** No agent memory store references this tree: 0 of 27 project dirs under `~/.claude/projects` match `harbor|auditeval`, and there is no agent file in the tree. Nothing was found there to report.

## 6. Questions (operator unavailable, so these are the defaults I took)

1. **Are project admins a lower trust tier than system admins, i.e. multi-tenant?**
   - Options: (a) yes, then the BOLA rows are High and SSRF is High on a cloud host; (b) no, single team, then BOLA drops to Medium.
   - **Default: (a).** It matches the shipped default `PROJECT_CREATION_RESTRICTION=everyone`, which makes every authenticated user a projectAdmin somewhere.
2. **Is any deployment path other than the bundled nginx in use (Helm ingress, direct core exposure)?**
   - Options: (a) yes, then the job-hook row becomes Medium; (b) no, then it stays Low.
   - **Default: (b), Low.**
3. **For go.mod, is the target the shipped toolchain (1.17.7) or a rebuild on a current Go?**
   - The GODEBUG row matters only for (b). The EOL-stdlib row matters for (a).
   - **Default: report both.**

## 7. Depth reached

**gosec 2.29.0** ran over all 232 files.
- It printed `Lines: 31877, Issues: 66`.
- SSA analysis was **skipped** for the `model`, `assembler`, `route`, `handler` and `server` packages because of type errors: the generated `server/v2.0/restapi` and `models` packages are absent.
- Its taint and SSA-based rules therefore did not see the v2.0 handlers.

**govulncheck v1.8.0 did not run.**
- Symbol mode fails to load packages for the same reason.
- `-scan module` refuses a pattern, and without one it reports "no Go files in src".
- Reachability is therefore established only by hand, for the jwt chain.

**trivy 0.72.0** scanned only `go.mod` and `go.sum`.
- It is module-level, with no reachability.
- It does not cover stdlib (toolchain) CVEs.

**Other checks:**
- `go mod verify` failed offline (module cache absent, `GOPROXY=off`).
- `go list DefaultGODEBUG` ran successfully on `./core` with `-e`.
- The race detector was not run.

## 8. Not reached

- **The great majority of the 31.9k lines were never read by eye.** That includes the controllers for artifact, scan, replication flow, proxy cache (`controller/proxy`), p2p enforcer, quota, gc and ldap, and the middleware for repoproxy, contenttrust, vulnerable, immutable and quota. They were covered only by gosec, which lost SSA on the handler packages, and by grep sweeps.
- The project-scoped handlers in `project.go`, `scanner.go`, `artifact.go`, `repository.go`, `scan.go` and `project_metadata.go` were **not** reviewed for ID binding. The 14/30 binding count covers only label, robot, member, retention, immutable, webhook, webhook-job, preheat and replication.
- **Checklists not walked item by item:**
  - sota-code-security rules/03 (authorization) and every other code-security rules file;
  - sota-api-design;
  - sota-golang rules/02, 06 and 07.
  
  Rules/01, 03, 04 and 05 were walked as grep sweeps with counts. Items needing judgement (typed-nil, `%v` vs `%w`, cookie attributes) were not individually marked.
- **Skills never loaded:** sota-identity-access (federation and OIDC design), sota-testing (whether the BOLA paths have tests), sota-observability, sota-databases, sota-async-concurrency. These are holes, not clean domains.
- All history-dependent steps were not reached: diff baseline, decision PRs, CHANGELOG-to-commit tracing.
- **Refutation.** The Highs got only a **self-refutation**: I re-read the handler and controller source at the paths cited and found no compensating check in `Prepare` (it returns nil) or in the managers. This is the weaker form. All four High rows (webhook, preheat, retention, immutable) are load-bearing and should get an independent refuter via `/sota-deep-audit`.
- **Upstream fixes.** Whether upstream fixed these BOLA rows in a later release was **not verified**, because network access was disallowed.

A rule that let this audit down, for `/sota-report`: the sota-golang AUDIT checklists contain no "child object bound to its authorized parent" probe. The dominant High class here was found only by a population census, not by any Go checklist item.
