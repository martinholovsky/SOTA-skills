# SOTA audit: Harbor `v2.5.1` (workspace w1)

- **Tree identity:** `cat VERSION` returns `v2.5.1`.
- **Git history:** none, because `.git` was removed. Every step that needs history or a commit is **not reached**: guard history, `git log -S`, diff baseline, merge-base, PR-level decision provenance.
- **Mode:** AUDIT. Read-only. Nothing in the workspace was edited, and step 8 (fix) was skipped as instructed.

## 1. Scope (agreed in advance) and denominators

| Candidate | Size | Chosen? |
|---|---|---|
| `src/server/**` and `src/controller/**`, non-test `.go` | **232 files / 31,877 lines** (`find … ! -name '*_test.go'`; gosec independently reports Files 232, Lines 31877) | yes |
| `src/go.mod` | 235 lines (`require` block plus a 4-line `replace`) | yes |
| `git status` / branch diff | not sizeable: no `.git` in the workspace | n/a, reported as not reached |
| Whole workspace | 8,382 files | no (context only) |

**Partitions, each finished before the next:**

| Partition | Lines | Files |
|---|---|---|
| A: `server/middleware`, `server/registry`, `server/router`, `server/route.go`, `server/handler`, `server/version.go` | about 5.1k | 65 |
| B: `server/v2.0/**` | 9,645 | 57 |
| C: `controller/**` | 16,860 | 109 |
| D (me): `go.mod`, scanners, CI gate reach, decision ledger, cross-cutting sweep | | |

A, B and C were each read by a separate agent against the named rules files. I then spot-checked their load-bearing findings against the code myself (listed in §6).

**Excluded:** everything else in the workspace. That covers `src/core`, `src/pkg`, `src/lib`, `src/common`, `src/jobservice`, `src/chartserver`, `src/registryctl`, `src/portal`, tests, `make/`, `.github/`, the nginx templates and the Makefile.
- These were read only to trace a data flow or a mitigation. No finding is anchored in them.
- Where a cause lives there, the finding is anchored at the in-scope call site and the out-of-scope location is named.

## 2. Coverage (routing from surfaces)

| Surface found | Owning skill | Loaded? | If not, why |
|---|---|---|---|
| Go source (232 files) | sota-golang | yes: rules 01, 02, 03, 04, 05 (checklists), 07, 08 (checklists) | 06 performance not loaded: no performance question in scope |
| HTTP API handlers (178 operations), registry `/v2/` routes, middleware chain, authn generators | sota-code-security | yes: 01, 02, 03, 04, 05, 06, 07, 09, 10, 17, 22 (14 cited from the command text) | 08/23 (LLM) N/A; 18 (tamper-evident logs) N/A; 19 (bot abuse of business flows) not loaded; 20 (headers) not loaded, because headers are set by nginx, out of scope; 21 (uploads) not loaded separately, because blob upload is covered under 06/09 |
| REST semantics, pagination, API security operations | sota-api-design | yes: 01, 07 | 06 (webhooks) **not loaded**. That is a hole: outbound webhooks are in scope (`controller/event/handler/webhook`, `notification_policy.go`). Partially covered via code-security 01 (SSRF) and 07 (secrets) |
| Goroutines, channels, background jobs | sota-async-concurrency | **no** | Covered only through sota-golang rules/03. The cross-runtime backpressure rules were not walked: a hole, partially mitigated |
| `go.mod` dependencies | sota-golang 08 + sota-devsecops | golang 08 yes; devsecops **no** | devsecops rules/03 and 09 were cited from the command text only, not walked item by item |
| Untrusted artifact parsing (manifests, chart tgz, icon images, CNAB) | sota-code-security 09 (+ sota-sandboxing 04) | 09 yes; sandboxing **no** | Parser isolation not walked: a hole |
| OIDC / LDAP / robot accounts / RBAC model | sota-identity-access | **no** | App-level authn/authz was walked under code-security 02/03/17. IdP and role-design rules were not walked: a hole |
| DB access via ORM (`q.Query`, beego orm) | sota-databases | **no** | Only the query-construction risk was walked (code-security 01; B's M3). Schema, transactions and isolation were not walked: a hole |
| Logging, metrics, health endpoints | sota-observability | **no** | Only data exposure in logs was walked (code-security 07). A hole |
| Test suite (142 `_test.go` in scope dirs) | sota-testing | **no** | Suite-health pass not run (tests are out of scope for findings). Cross-tenant test absence was noted by B. A hole |
| Threat model | sota-threat-modeling 06 | **no** (not run as a pass) | The trust boundaries were reconstructed implicitly per partition, but no DFD or threat model was produced. A hole |
| Secrets in code | sota-secrets-management | no | gosec G101 found 1 hit, a false positive (a header name). The command's secret grep in partition C found 0, with a positive control. Swept, rules not walked |
| Agent instruction files | sota-skill-security | N/A | 0 found (find over hidden directories; positive control: `.github` found = 1) |
| Frontend / LLM / mobile / data pipelines / K8s / IaC | various | N/A | No matching surface in scope |

**Stack profile:**
- `~/.claude/profiles/*.md` exists and was read.
- It states it is the baseline "in one of [the profile owner's] repos". This is an upstream project the owner does not own, so I treated **profile deviations as not findings**.
- One overlap is noted anyway as Info: the profile expects golangci-lint with gosec/errcheck as a gate, and this repo has neither as a gate (§5).

**Project's own conventions:**
- Read: `CONTRIBUTING.md` and the Makefile's `go_check` target (gofmt, golint, govet, misspell).
- None of them conflicts with a library rule I applied, so there was no collision to resolve.

**Day zero:** does not fire.
- `LICENSE` is present.
- History length cannot be read, but the project is at v2.5.1 with a 2019-era CHANGELOG, so it is a mature repository.
- Evidence gathered: no secret scan in CI (gitleaks/trufflehog/detect-secrets: 0 hits in `.github`/Makefile; positive control: codeql = 1 workflow), and no agent file.
- Not offered: `init-gates.sh` is not applicable to an upstream repo you do not own.

## 3. Findings

**Rating rules used:**
- Severity follows `sota/rules/03` §1, and each Critical/High names its chain.
- The baseline is the code as it stands, since there is no diff.
- Attacker model for the IDOR findings: "any authenticated user". This was verified in code:
  - `ProCrtRestrEveryone` is the default (`src/lib/config/metadata/metadatalist.go:117`).
  - A project creator becomes ProjectAdmin (`src/pkg/project/dao/dao.go:75-76`).
- **Deciding assumption for every High:** Harbor's role as a multi-tenant registry in which projects are the tenant boundary. If a deployment has exactly one trusted team, the IDORs fall to Medium.

### High

| # | file:line | rule violated | severity | effort | fix |
|---|---|---|---|---|---|
| H1 | `src/server/v2.0/handler/notification_policy.go:149-161` (+ `model/notification_policy.go:37/41`) | code-security 03 (object-level authz, CWE-639) + 07 (secrets in responses) | **High** | S | Load the policy, require `policy.ProjectID == projectID`, and return 404 otherwise. Make `auth_header` write-only or masked. |
| H2 | `src/server/v2.0/handler/retention.go:196-214` (UpdateRetention), `:265-281` / `:313-358` (OperateRetentionExecution, ListRetentionTasks, GetRetentionTaskLog) | code-security 03 §2/§3 (nested/job IDs) | **High** | M | Authorize on the stored policy's scope rather than the body's. Check that `Eid`/`Tid` belong to that policy and that the vendor type is Retention. |
| H3 | `src/server/v2.0/handler/preheat.go:644-659` (StopExecution), `:720-731` (GetPreheatLog), `:576-592`, `:682-717` | code-security 03 §3 (job IDs) | **High** | S | Require `execution.VendorType == P2PPreheat && VendorID == policy.ID && policy.ProjectID == project` before Stop, Get or Log. |
| H4 | `src/server/v2.0/handler/notification_policy.go:115-130` (update), `:137-147` (delete) | code-security 03 (BOLA) + 07 (mass assignment of `id`) | **High** | S | Set `policy.ID = params.WebhookPolicyID` and verify ownership before Update/Delete. Copy only allowlisted fields. |
| H5 | `src/server/v2.0/handler/immutable.go:39/69-89` (update via body `id`), `:56-67` (delete via path id) | code-security 03 (BOLA) | **High** | S | Use the path `ImmutableRuleID`, fetch the rule and check its ProjectID before Update, Enable or Delete. |
| H6 | `src/server/v2.0/handler/preheat.go:257-272` + `:454-479` (`convertParamPolicyToModelPolicy` copies `ID`/`ProjectID` from the body) | code-security 03 + 07 (privileged fields writable) | **High** | S | Look the policy up by name inside the path project, as `DeletePolicy` does, and ignore body `id`/`project_id`. |
| H7 | `src/controller/icon/controller.go:136` (`image.Decode(iconFile)`), reached from unauthenticated `src/server/v2.0/handler/icon.go:37-46`; planted via `src/controller/artifact/annotation/v1alpha1.go:75-95` | code-security 09 (image `DecodeConfig` first; pixel limits) / 06 (allocation caps), CWE-789/400 | **High** | S | Call `image.DecodeConfig` and reject when width × height exceeds a cap (e.g. 1024²) before decoding. Bound the blob read. Cache negative results. |
| H8 | `src/controller/artifact/processor/chart/chart.go:87` (`ioutil.ReadAll(blob)`, then helm `loader.LoadArchive` via `src/pkg/chart/operator.go:91`) | code-security 09 (archive caps), 06 (decompression bombs), CWE-409 | **High** | M | Cap the read at the descriptor size and an absolute limit, cap decompressed bytes and entry count, cache the parsed result per digest, upgrade helm (GO-2025-3601), and close `blob` with `defer`. |

**H1, cross-project webhook secret read.**
- Code: `policy, err := n.webhookPolicyMgr.Get(ctx, params.WebhookPolicyID)` follows `RequireProjectAccess(projectNameOrID, …)`.
- Chain:
  - Source: the path policy ID, sequential and enumerable.
  - Acts: `pkg/notification/policy/manager.go` Get(id), which has no project predicate.
  - Crosses: another project.
  - Channel: the response returns `targets[].auth_header`, the webhook receiver's secret.
- Related at Medium: `notification_job.go:34` lists any policy's jobs.

**H2, retention.**
- UpdateRetention authorizes on the body's `scope.reference`, sets `p.ID = params.ID`, and rewrites the victim's policy.
- `OperateRetentionExecution` passes `Eid` straight to `execMgr.Get` and Stop with no vendor check (`controller/retention/controller.go:257-267`), so it stops **any** execution, including GC, replication and scan-all.
- `GetRetentionTaskLog` passes `Tid` to `taskMgr.GetLog` with **any** vendor type, so it reads any job's log.
- The task listing leaks other projects' repository names and jobservice JobIDs.

**H3, preheat execution IDs.**
- The same shape as H2, through `controller/task/execution_controller.go:56-67`, which is a pass-through.
- Execution and task IDs are sequential and shared across all job types.

**H4, webhook update/delete.**
- Update: `lib.JSONCopy(policy, params.Policy)`, then `policy.ProjectID = projectID`, then `Update(ctx, policy)`. The DAO runs `ormer.Update` on all columns, using the PK from the body.
- Effect: the victim's policy is overwritten and moved into the attacker's project.
- Delete: removes by path ID with no project predicate (`pkg/notification/policy/dao/dao.go:126-140`).

**H5, immutable rules.**
- Effect: the attacker can rewrite or disable another project's tag-immutability rule, or delete it (`pkg/immutable/dao/dao.go:53, 69-70, 124-126`).
- Consequence: the victim's protected tags become overwritable, which is a supply-chain integrity risk.

**H6, preheat policy.**
- `pkg/p2p/preheat/dao/policy/dao.go:89` updates every column, `project_id` included.
- Effect: the attacker can rewrite any preheat policy, or repoint one at a victim project.

**H7, icon decode DoS.**
- Chain:
  1. A pusher in **any** project pushes a manifest whose layer carries `io.goharbor.artifact.v1alpha1.icon`. The push-time check reads 1 MiB and sniffs the content type only.
  2. Anyone, **unauthenticated**, calls `GET /api/v2.0/icons/{digest}`. The handler makes no authz call, and the swagger global security is `basic` or `{}`.
  3. `image.Decode` runs.
- **Measured this session:** a **75-byte** PNG declaring 10000×10000 made `image.Decode` allocate **381 MB** before failing (go1.27.1 stdlib, scratch program outside the workspace). Harbor builds with go1.17.7, and the PNG allocation behaviour there is **needs verification**.
- Failed decodes are not cached (the `sync.Map` stores only successes), so every request re-allocates.

**H8, chart decompression bomb.**
- Each `GET …/additions/{values.yaml,readme.md,dependencies}` re-pulls the layer, reads it whole, and inflates every tar entry into a `bytes.Buffer`. The vendored helm v3.7.1 `loader/archive.go:105-174` has no decompressed-size cap.
- Who can trigger it: a pusher plants the bomb. Readers trigger it, including anonymous readers on a public project (`common/rbac/project/rbac_util.go:46` grants addition read).
- govulncheck independently reports **GO-2025-3601** ("crafted chart archive → OOM"), fixed in helm 3.17.3, as reachable.

### Medium

| # | file:line | rule violated | severity | effort | fix |
|---|---|---|---|---|---|
| M1 | `src/server/v2.0/handler/project.go:561-618` + `model/scanner.go:30-43` | code-security 07 (secrets in responses) | **Medium**. High if a scanner is registered with an `access_credential` | S | Never serialize `AccessCredential`; mask it as `replication.go:478-480` does for registry secrets. |
| M2 | `src/server/v2.0/handler/robot.go:186-208, 282-319` | code-security 03 (authz on the body namespace, not the stored robot) | **Medium** (refuter: needs the victim's robot name; integrity/DoS only, no escalation) | S | Authorize on the stored `r.ProjectID` (as `RefreshSec` does) and require the body namespace to equal it. |
| M3 | `src/server/v2.0/handler/notification_policy.go:228-232` | code-security 10 §1 (inert control) + 01 §5 (SSRF) | **Medium** | M | Write back through an index (`policy.Targets[i].Address = …`) and add post-resolution private/link-local/metadata IP blocking at dial time. |
| M4 | `src/server/middleware/quota/put_blob_upload.go:40-52` (+ `middleware/blob/put_blob_upload.go:51-53`) | code-security 03 / 10 (client-supplied accounting; attacker-triggered early return) | **Medium** (refuter: survives at 80; end-to-end chunked PUT not reproduced) | M | Charge from the registry-reported size after commit, and treat an absent `Content-Length` as unknown rather than 0. |
| M5 | `src/server/middleware/util/util.go:68-73` | code-security 03 (privilege from a client header) / 10 (proxy predicate) | **Medium** | S | Drop the `strings.Contains(r.UserAgent(), "cosign")` clause and use a server-side scoped action. |
| M6 | `src/server/registry/manifest.go:55-56` | code-security 07 §2.1 (caller-suppressible security event) | **Medium** | S | Identify replication by security context, not by `User-Agent == "harbor-registry-client"`. |
| M7 | `src/controller/event/handler/util/util.go:28-35` | sota-golang 03 §5 (go directive below 1.22 + address of loop var), CWE-362 | **Medium** | trivial | `t := target; Target: &t`, or raise the `go` line to 1.22 or later. |
| M8 | `src/server/v2.0/handler/base.go:157-177` (BuildQuery) | api-design 01 (pagination max, filter allowlist) / code-security 06 | **Medium** | M | Clamp `1 ≤ page_size ≤ 100` server-side. Add a per-endpoint allowlist of filter/sort keys, and exclude `secret`, `salt`, `password`. |
| M9 | `src/server/v2.0/handler/search.go:140-187` | code-security 06 (unbounded) / api-design 01 | **Medium** | M | Paginate and push the project filter into SQL. |
| M10 | `src/controller/ldap/controller.go:63-74` (handler `server/v2.0/handler/ldap.go:29-38`) | code-security 04 (stored secret to a caller-chosen endpoint) / 01 (SSRF) | **Medium** | S | Use the stored password only when the URL and DN equal the stored ones. |
| M11 | `src/controller/registry/controller.go:168-177` (from `server/v2.0/handler/registry.go:204-251`) | code-security 04 / 01 | **Medium**, needs verification | S | When `ID` is given, refuse a changed URL or drop the stored credential. |
| M12 | `src/controller/proxy/controller.go:219-244` (+ `manifestcache.go:127-174`) | golang 03 (fire-and-forget, unbounded fan-out); code-security 06 | **Medium** | M | Deduplicate before spawning (singleflight), use a bounded pool, and a detached ctx with a timeout. |
| M13 | `src/controller/proxy/controller.go:263-274` | code-security 06 (double upstream fetch, no backpressure) | **Medium** | M | Tee the client stream into the local push, or deduplicate before the second read. |
| M14 | `src/controller/replication/transfer/image/transfer.go:254` (+ `proxy/controller.go:204,226-229`) | code-security 09 (feed integrity) / 06 | **Medium**, needs verification | M | Verify `digest.FromBytes(payload)` against the requested digest, and bound recursion depth. |
| M15 | `src/controller/replication/transfer/chart/transfer.go:66-68,158` | code-security 01 (SSRF from a third-party-supplied URL) | **Medium**, needs verification | S | Allowlist the contentURL host. Use a comma-ok type assertion. |
| M16 | `src/controller/config/controller.go:137-147` | code-security 07 (secret in responses: `uaa_client_secret` is a `StringType`) | **Medium**, needs verification | S | Mark it `PasswordType`, or redact by name. |
| M17 | `src/controller/artifact/annotation/v1alpha1.go:83-87` | code-security 10 §1 (inert check: `ReadAll` never returns `io.EOF`, so the "max 1MB" branch is dead) | **Medium** | S | Use `LimitReader(n+1)` and reject when `len > n`. Close the `icon` reader. |
| M18 | `src/server/middleware/security/oidc_cli.go:77,92-103` | golang 04 (authz on the raw path; router cleans later) | **Medium**. High if core is reachable without the normalising nginx | S | Run `path.Clean` before matching, and anchor the regex segments with `[^/]+`. |
| M19 | `src/server/middleware/quota/util.go:52`, `middleware/blob/put_manifest.go:37,67`, `middleware/cosign/cosign.go:77` | golang 04 body hygiene (unbounded `ReadAll`, no `MaxBytesReader`: 0 of 65 files in partition A, 2 in all of src) | **Medium** (authenticated memory DoS) | S | Apply `http.MaxBytesReader` at the manifest limit once, before the first read. |
| M20 | `src/go.mod:3` (`go 1.17`) + Makefile `GOBUILDIMAGE=golang:1.17.7` | golang 08 §1/§2 (toolchain current; the `go` line sets GODEBUG and loop-var semantics) | **Medium** | M | Move to a supported Go release. Raising the `go` line to 1.22 or later also removes the M7 class. |
| M21 | `src/go.mod` (requires) | golang 08 / devsecops (vulnerable dependencies) | **Medium** (the individual reachable items are rated in H8, M22 and §5) | M | Upgrade: `gorilla/csrf` ≥ 1.7.3 (GO-2025-3607), `golang-jwt/jwt/v4` ≥ 4.5.2 (GO-2025-3553, GO-2024-3250), `helm` ≥ 3.17.3, `x/net`, `prometheus/client_golang` ≥ 1.11.1, docker/containerd. |
| M22 | `src/server/middleware/csrf/csrf.go:61-66` (gorilla/csrf v1.6.2) | code-security 05 (CSRF) via GO-2025-3607 (broken Referer validation; trace `csrf.go:68`) | **Medium**. Low given the `SameSite=Strict` cookie in the same call | S | Upgrade gorilla/csrf. |
| M23 | All 232 in-scope files (0 rate limiters on request paths) | Router principle 5(a), abuse control | **Medium** | M | Per-principal limits on authn (Basic auth to `/v2`, `/api`) and on expensive endpoints (search, icons, additions). |

**M23 detail:**
- The search pattern `rate\.NewLimiter|ratelimit|RateLimit|throttle` matched 1 file, `replication/transfer/iothrottler.go`, which is a bandwidth throttle.
- Positive control in the same run: the logging pattern matched 100 files.
- `core/auth` has a 1.5 s per-username login lock (out of scope).
- **Needs verification:** whether nginx or the ingress limits requests. Nothing in the tree says so.

### Low

| # | file:line | rule violated | severity | effort | fix |
|---|---|---|---|---|---|
| L1 | `src/server/handler/job_status_hook.go:37-45` + `src/server/route.go:53-59` | code-security 03 (internal callers need an identity) | **Low as shipped**: nginx returns 404 for `/service/notifications`. Medium/High if core's `/service/` is routed without that nginx | M | Require the jobservice `Harbor-Secret` identity. Add `MaxBytesReader`. |
| L2 | `src/server/middleware/immutable/pushmf.go:46-53` | code-security 07/10 (non-allow exit allows) | Low | S | Return nil only on NotFound; deny on any other error. |
| L3 | `src/server/middleware/v2auth/auth.go:70-73,168` | code-security 07 (existence oracle; bypasses 5xx scrubbing) | Low | S | Return a generic 401 and log the detail. |
| L4 | `src/server/middleware/csrf/csrf.go:57` | code-security 07 / golang 04 (secret value logged) | Low | S | Log the length, not the key. A per-replica random fallback also breaks HA CSRF: fail closed instead. |
| L5 | `src/server/middleware/security/robot.go:57` | code-security 22 (non-constant-time secret compare) | Low | S | `subtle.ConstantTimeCompare`. |
| L6 | `src/server/middleware/repoproxy/proxy.go:203-212` | code-security 03 (identity by username string) | Low, needs verification | S | Check `sc.Name()=="proxycachesecret"`. |
| L7 | `src/server/middleware/security/basic_auth.go:30-50,72` | code-security 07 (spoofable `X-Forwarded-For` in security logs) | Low | S | Log `RemoteAddr` too, and trust only configured proxies. |
| L8 | `src/server/v2.0/handler/robot.go:119,122,127` | golang 01 (reachable panic: unchecked type assertion on `q=`; 0 `recover()` in server/core) | Low | S | Use the comma-ok form. |
| L9 | `src/server/v2.0/handler/user.go:291-325` | code-security 03 §7 / golang 01 (compares the new password against the *caller's*; logs and sends the nil `err` instead of `err2`) | Low/Medium (admin-only) | S | Compare against the target user, and return `err2`. |
| L10 | `src/server/v2.0/handler/artifact.go:451-463` | code-security 03 §3 (label scope) | Low/Medium | S | Require the label to be global or in the artifact's project. |
| L11 | `src/controller/scan/base_controller.go:822-845` | least privilege: the scanner robot gets project-wide pull and the default 30-day lifetime | Low | S | Scope it to the repository, with a short Duration. |
| L12 | `src/controller/robot/controller.go:101-103` → `common/utils/utils.go:72-75` | code-security 04 (CSPRNG failure fails open to a constant secret) | Low | S | Return an error. |
| L13 | `src/controller/proxy/local.go:93` | code-security 04 (hard-coded `insecure=true` on core→registry; client without a timeout) | Low | S | Use the internal CA, and set a timeout. |
| L14 | `src/controller/health/checker.go:178-185` | code-security 10 (Redis health check never pings: inert) | Low | S | `conn.Do("PING")`. |
| L15 | `src/controller/health/controller.go:69-81` / `checker.go:60-64` | golang 03 (unbuffered channel leaks on timeout); code-security 07 (raw component errors to unauthenticated `/health`) | Low | S | Use a buffered channel and generic errors. |
| L16 | `src/controller/event/handler/internal/artifact.go:121-139` | golang 03/01 (possible nil-map write in an unrecovered goroutine) | Low, needs verification | S | Initialise the maps unconditionally. |
| L17 | `src/controller/artifact/processor/default.go:111`, `processor/base/manifest.go:98` | code-security 09 (unbounded JSON decode of the config blob) | Low | S | `io.LimitReader(blob, min(Config.Size, cap))`. |
| L18 | `src/server/v2.0/handler/member.go:154-171` / `controller/member/controller.go:95-104` | code-security 01 (role not validated on update) | Low | S | `isValidRole`. |
| L19 | `src/controller/artifact/helper.go:37-40` | code-security 10 (iterator swallows list errors; ScanAll treats a partial set as complete) | Low | S | Add an error channel. |
| L20 | `src/server/v2.0/handler/artifact.go:71-73`, `repository.go:58-60`, `scan.go:43-45`, `config.go:68-69` | golang 01 (`SendError` result discarded: 4 of 644 calls) | Low | trivial | `return` it. |
| L21 | `src/controller/replication/transfer/iothrottler.go:28` | code-security 06 (int32 overflow, admin-set) | Low | S | Compute in int64/float64. |

**Info** (one line each, not tabled):
- `server/v2.0/handler/scan.go:89-112` / `controller/scan/base_controller.go:635-687`: report UUID not bound to the artifact (v4 UUID, so not enumerable).
- `project.go:206/552`: `retention_id` writable via Metadata JSONCopy.
- `systeminfo` returns the version unauthenticated.
- 62 gosec G104 discarded errors, 32 of them `notifier.Subscribe` in `controller/event/handler/init.go`.
- G404 at `controller/registry/controller.go:218` is health-check jitter: a gosec false positive, not CSPRNG use.
- G101 at `csrf.go:21` is a header name: a false positive.
- `auth_proxy.go:72,77` logs the wrong error.
- `cosign` content trust checks presence only, never verifies a signature (`contenttrust/cosign.go:50-64`).
- The API uses no RFC 9457 problem+json, no ETag/If-Match, and offset pagination. These are idiom gaps only.

## 4. Present is not applied (silent-control pass)

**Inert controls confirmed by reading:**

| Finding | Why the control does nothing |
|---|---|
| M3 | The SSRF rewrite assigns to the range copy of a `[]EventTarget` value slice (`pkg/notification/policy/model/model.go:21`), so the write is discarded |
| M17 | The 1 MB icon check is dead code |
| L14 | Redis health always reports OK |
| L2 | The immutable check fails open on any lookup error |
| M5, M6 | The User-Agent stands in for an identity |
| M4 | The client header stands in for the stored size |

**Population counts:**
- **Authz census, partition B:** 178 operation handlers. 169 call an authz helper and 9 do not.
  - Of the 9: 5 are intended public, 3 filter inline, and 1 returns static metadata.
  - **But 13 of the 169** call the helper on the path project and then act on an unscoped ID (H1–H6, M2, L10).
  - So the credited control guards about 156 of 169 sites as claimed. The safe pattern exists and is used in member, robotV1, robot Get/Delete/RefreshSec, label and retention Get/Delete.
- **Goroutines in controller/:** 18 `go` statements, **0 of 18** select on `ctx.Done()`.
- **`io.ReadAll` in controller/:** 3 sites, 1 bounded.
- **`image.Decode`:** 1 site, 0 `DecodeConfig` guards.
- **`MaxBytesReader`:** 0 in the 65 files of partition A.

**Enforcement depth of the project's own gates (context; out of scope for findings):**

| Gate | What it actually does | Effect |
|---|---|---|
| `Makefile:509-516` `gosec` target | Runs `gosec … ./... \| true` | Cannot fail. No CI workflow references it (0 hits in `.github`/`tests/ci`; positive control: `go_check` = 1) |
| `govulncheck` | Not in CI | A dependency scan gate is absent |
| `golangci-lint` | Absent | Lint gate absent |
| CI `go test -race` | Present (`tests/coverage4gotest.sh:32`) | Real gate |
| CodeQL workflow | Present (`codeql-analysis.yml`) | Present; `autobuild` is commented out (line 37), so whether Go is analysed needs verification |

Rules: sota-golang 07 (no govulncheck in CI = HIGH per that checklist; Medium here, because the target is outside scope) and sota-devsecops 09 §2a.

## 5. Decisions (decision ledger)

| Decision | Evidence | Verdict |
|---|---|---|
| Go toolchain 1.17 (`go 1.17`; `golang:1.17.7` build image) | The local toolchain is go1.27.1, so 1.17 is 10 minors behind. Under "the two latest majors are supported", it is unsupported. The EOL date is from recall (≈2022-08), **needs verification** (no network) | **STALE** (M20) |
| `replace google.golang.org/api => v0.0.0-20160322025152-9bf6e6e569ff` | A 2016 pseudo-version; no reason recorded anywhere in the tree (search over CONTRIBUTING, docs and the CHANGELOG found 0 mentions) | **UNVERIFIABLE** |
| `replace github.com/docker/distribution => distribution/distribution v2.8.0` | Upstream rename; justified by the module move | JUSTIFIED (version currency not checked) |
| beego v1.12.9 as the router (`server/router/router.go`) | govulncheck: GO-2025-3585 and GO-2024-3331 with "Fixed in: N/A"; whether beego v1 is maintained **needs verification** | **STALE**, needs verification |
| helm v3.7.1 in-process chart parsing in core | GO-2025-3601/3602 reachable; no decompression cap (H8) | **STALE** |
| gorilla/csrf v1.6.2, golang-jwt v4.1.0 | govulncheck reachable from `csrf.go:68` and `pkg/token/token.go:52` | **STALE** |
| SAST run non-blocking (`gosec \| true`, not in CI) | Makefile:514-516 | **UNJUSTIFIED**: a control that cannot fail |
| CHANGELOG ends at v1.8.0 (2019) while VERSION is v2.5.1 | `CHANGELOG.md` | **STALE** documentation: no decision record covers v1.9 through v2.5 |

**Where else the knowledge lives:**
- No agent or IDE store was found in the workspace: 0 hits for `.claude`, `.cursor*`, `.idea`, `.vscode` or agent files under a `find` that does enter hidden directories (positive control: `.github` = 1).
- No auto-memory directory exists for this path under `~/.claude/projects`.
- Rationale for the replaces and the stale toolchain is therefore not recorded anywhere reachable: **UNVERIFIABLE**.

## 6. Questions I would have asked (operator unavailable; default chosen, audit continued)

**Q1. Is Harbor deployed multi-tenant, with projects as a security boundary between mutually untrusted teams, and is self-service project creation on?**

| Option | Consequence |
|---|---|
| (a) Yes | H1–H6 stay High |
| (b) Single trusted team | They drop to Medium, and creation can be restricted to admins as a compensating control (`project_creation_restriction`) |
| (c) Mixed | |

- **Default used: (a).** Reason: the code's default is `everyone`, and a registry's purpose is to separate projects.
- **Recommendation:** treat it as (a) and fix the 13 unscoped-ID handlers. That costs one ownership check each, and the pattern already exists in the codebase.

**Q2. Is core ever reachable without the bundled nginx (Helm ingress, a service mesh, direct port 8080)?**
- If yes: L1 → Medium/High, and M18 → High.
- **Default used: no** (the bundled compose topology).
- **Recommendation:** add authentication to the hooks anyway. A path-prefix 404 in another component is not a control the core binary carries.

**Q3. Is a scanner registered with an `access_credential`, and are any projects public?**
- If both are true: M1 → High.
- **Default used:** unknown, so Medium.

**Q4. Is rate limiting enforced at the edge?**
- If yes: M23 drops to Low, documented as "handled at the gateway".
- **Default used:** no evidence of it, so Medium.

## 7. Depth reached

**govulncheck v1.8.0, symbol mode:**
- Ran over **84 of 89** in-scope packages, with DB updated 2026-10-01.
- The 5 not loadable: `server`, `server/v2.0/handler`, `…/assembler`, `…/model` and `…/route`. They import go-swagger generated code (`server/v2.0/models`, `restapi`), which is absent from the tree because `make gen_apis` needs Docker.
- Result: 35 vulnerabilities from 10 modules reported as called, plus 30 in imported packages and 62 in required modules that are not called.
- Many traces are init-only reachability (containerd, docker, x/crypto/openpgp via `chartserver` init). I treated those as Info inside M21. Only the request-path traces (csrf, jwt, helm, client_golang via `quota.go:114`, x/net http2 client) were weighed.
- **Stdlib vulns are invisible:** govulncheck checked against the local go1.27.1 stdlib, not the shipped go1.17.7.
- `-scan module` failed ("no Go files" at the module root) and was not retried with another invocation.

**go vet (go1.27.1) over the same 84 packages:**
- Exit 0, no output.
- Positive control: a scratch go1.17 module with a goroutine loop-closure bug was flagged.
- Limit: the control showed vet does **not** flag address-of-loop-variable (`&t.x`), the M7 shape. That site was found by gosec G601 and confirmed by reading.

**gosec 2.29.0:** ran over all 232 files and 31,877 lines (the denominator matches), and reported 66 issues. Triage: 62 G104, plus G601 (real, M7), G118 (replication worker; partition C judged it bounded by the worker pool), G404 and G101 (false positives).

**Partition agents:** read-only code review, with these tool-call counts:

| Partition | Tool calls |
|---|---|
| A | 39 |
| B | about 77 |
| C | about 55 Bash calls (84 tool uses) |

- Every absence claim they made carries a positive control in the same command, and each reported a self-caught harness slip (a zsh `==` parse error; zsh no-word-split), re-run.
- Nothing was exercised against a running Harbor. M4, M14, M15, M18, L1 and L6 especially need runtime reproduction.

**My own spot-checks against the code:**
- From partition A: M5/util.go, M6/manifest.go, M4/put_blob_upload.go, L2/pushmf.go, L5/robot.go, M22/csrf.go.
- From partition C: H7/icon and annotation, H8/chart.go and the vendored helm loader, M7 traced through `pkg/notifier/event/event.go:48-58` into `notifier.go`'s goroutine dispatch.
- Across partitions: H4/notification_policy.go, H3/preheat.go, M1/model/scanner.go, M3/model.go value slice.
- Measured: the H7 PNG allocation.

## 8. Refutation

**Highs and borderline items:**
- Every High, plus borderline M1, M2, M4 and L1, went to an **independent refuter agent** in a fresh context, prompted to kill each claim, default REFUTED, with verdicts returned as numbers.
- It read about 30 files of code at this tree.
- **This was weaker than the standard in one respect:** it was handed a one-sentence statement of each claim with its file:line (bounded, but written by me), not the code alone.

| Claim | Verdict | Confidence |
|---|---|---|
| H4 update/delete | SURVIVES | 92 / 95 |
| H1 | SURVIVES | 95 |
| H5 | SURVIVES | 90 |
| H2 | SURVIVES | 88 |
| H6 | SURVIVES | 88 |
| H3 | SURVIVES | 90 |
| H7 | SURVIVES | 85 |
| H8 | SURVIVES | 80 |
| M4 | SURVIVES | 80 |
| Robot update (M2) | PARTIAL | 75 |
| Scanner credential (M1) | PARTIAL | 70 |
| Job hooks (L1) | PARTIAL | 55 |

**Downgrades from refutation:**
- Robot update fell from High to **M2**: it needs the victim robot's name, and it is integrity/DoS only.
- Scanner credential fell from High to **M1**, conditional on a credential being configured.
- Job hooks fell from Medium to **L1**: shipped nginx blocks them, and the task hooks need a random JobID.

**Sweep of the refuted and partial patterns:**
- The "authorize the path or body project, then act on an unscoped ID" pattern was swept across all 178 handlers in partition B's census. It closes in 13 handlers, all listed above.
- The same pattern in middleware (User-Agent and username identity) produced M5, M6 and L6.

**Self-refutation only (no independent refuter):** all Mediums except M1, M2 and M4, and all Lows. Their severity rests on the partition agent's reading plus my spot-checks.

**Escalation:** H1–H8 are load-bearing. The refuter recalled H1/H4–H6 as the July 2022 Harbor IDOR advisories fixed after 2.5.1, but that is from memory, not verified (no network). If these feed a go/no-go, escalate to `/sota-deep-audit` and confirm against the vendor advisories.

## 9. Not reached

- **Anything needing git history:** guard history, diff baseline, PRs behind decisions.
- **Five packages that do not compile** without the generated go-swagger code: about 9.6k lines of `server/v2.0` were reviewed by reading only, with no symbol-level vuln reachability, no vet, and only syntax-level gosec.
- **Runtime reproduction** of any finding except the PNG allocation.
- **Skills not walked** (§2): sota-async-concurrency, sota-api-design rules/06 (webhooks), sota-sandboxing rules/04, sota-identity-access, sota-databases, sota-observability, sota-testing suite health, sota-devsecops item-by-item, sota-threat-modeling reconstruction.
- **Partially read in partition C:** `artifact/controller.go` (grep only), `tag`, `retention/controller.go`, `gc/controller.go`, `project/controller.go`, `usergroup`, `immutable`, `task`, `event/metadata/*`, `replication/flow/*`, `quota/driver/*`.
- **Partially read in partition A:** `quota/copy_artifact.go`, `refresh_project.go`, `blob/copy_artifact.go`, `head_blob.go`, `registry/util/util.go`, metric/trace/orm/notification middlewares.
- **Partially read in partition B:** `replication.go`, `gc.go`, `scan_all.go`, `ldap.go`, `usergroup.go`, read only for the authz census and the secret-field grep.
- **Not verified by any primary source:**
  - CVE/advisory mapping
  - Go 1.17 EOL date
  - beego maintenance status
  - whether a system robot can hold registry read only (M11)
  - whether the edge enforces rate limits

**Library note (one line):** sota-golang rules/03 frames the below-1.22 loop-variable hazard as *closures* and points at `go vet` loopclosure. In this session vet demonstrably missed the address-of-loop-variable shape (`&target`) that produced M7, so the guidance is adjacent but would not have found it. Worth a `/sota-report`.
