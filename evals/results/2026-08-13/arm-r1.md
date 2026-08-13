# Security audit — Go service at `/private/tmp/claude-501/registry-svc-b0506782/svc`

Target: Harbor v2.5.1 (`VERSION` = `v2.5.1`). Scope: non-test Go under `src/server/` and `src/controller/` (232 files).
Every finding below was read at the exact `file:line` cited, and each authorization finding was traced into the
controller/manager/DAO layer to confirm no compensating check exists downstream.

Context on actors: in default Harbor any authenticated user may create a project and becomes its projectAdmin, so
"projectAdmin of some project" is effectively "any authenticated user".

## Findings

`src/server/middleware/vulnerable/vulnerable.go:110-118` | "Prevent vulnerable images from running" is skipped for every multi-arch image | Critical | `art.IsImageIndex()` is true for any OCI index / Docker manifest list, and the index processor returns `ArtifactTypeImage` = `"IMAGE"` (`src/controller/artifact/processor/image/index.go:33-47`), which is in `skippingAllowlist`, so `return nil` fires before the `IsScanSuccess()` (line 122) and `Severity.Code() >= projectSeverity.Code()` (line 129) gates — anyone with push rights wraps a Critical-CVE image in a one-entry manifest list and pulls it through a project configured to block it.

`src/server/middleware/util/util.go:70-71` | Attacker-set `User-Agent: cosign` disables content trust, cosign verification and CVE blocking | High | `SkipPolicyChecking` returns true for any `v2token` principal that has `ActionPush` on the repository and whose `strings.Contains(r.UserAgent(), "cosign")` matches; the header is never cross-checked against the request actually being a signature upload, so a project developer pulling with a forged UA bypasses all three pull-time policies (`contenttrust/notary.go:56`, `contenttrust/cosign.go:41`, `vulnerable/vulnerable.go:71`).

`src/server/v2.0/handler/retention.go:197-210` | Tag-retention policy update authorizes against the request body's scope, then writes the policy named by the URL ID | High | `p` is built from `params.Policy` (body) and `p.ID = params.ID`; `requireAccess` (line 205) resolves the project from the attacker-supplied `p.Scope.Reference`, so a projectAdmin of their own project A sends `PUT /retentions/{victim policy id}` with `scope.reference = A` and rewrites another project's retention rules — retention deletes images, so this is arbitrary cross-tenant image deletion.

`src/server/v2.0/handler/immutable.go:62` | Immutable-tag rule deleted by ID with no project ownership check | High | `RequireProjectAccess` is evaluated on the URL project but `immuCtl.DeleteImmutableRule(ctx, params.ImmutableRuleID)` deletes by primary key only (`src/controller/immutable/controller.go:49-51` → `dao` delete by PK), so any projectAdmin/maintainer enumerates small sequential rule IDs and strips another project's tag-immutability protection.

`src/controller/immutable/controller.go:59-71` | Immutable-tag rule updated/toggled by body-supplied ID without comparing the rule's project to the caller's | High | `m0, _ := r.manager.GetImmutableRule(ctx, m.ID)` is fetched and then `EnableImmutableRule(ctx, m.ID, m.Disabled)` / `UpdateImmutableRule(ctx, projectID, m)` run without ever checking `m0.ProjectID == projectID`; the handler at `src/server/v2.0/handler/immutable.go:76-84` copies `id` straight out of the JSON body (`lib.JSONCopy`) and ignores `params.ImmutableRuleID`, so any projectAdmin disables another project's immutability rule and then overwrites its "immutable" tags.

`src/server/v2.0/handler/notification_policy.go:155` | Webhook policy of any project readable via `GET`, leaking the target URL **and** its auth header | High | `webhookPolicyMgr.Get(ctx, params.WebhookPolicyID)` is called after authorizing only on the URL project, and the response includes `AuthHeader` (`src/server/v2.0/handler/model/notification_policy.go:37`), so any project member with `notification-policy:read` in any project steals another tenant's webhook endpoint and its bearer/secret header by iterating policy IDs.

`src/server/v2.0/handler/notification_policy.go:129-130` | Webhook policy update takes its ID from the request body and force-reassigns the project | High | `lib.JSONCopy(policy, params.Policy)` supplies `policy.ID` from the body (`params.WebhookPolicyID` is never used) and line 129 then sets `policy.ProjectID` to the caller's project, so a projectAdmin re-points another project's webhook policy at a URL they control and moves it into their own project.

`src/server/v2.0/handler/notification_policy.go:143` | Webhook policy deleted by ID with no project ownership check | High | `webhookPolicyMgr.Delete(ctx, params.WebhookPolicyID)` runs after an authorization check bound to the URL project only, letting any projectAdmin delete other projects' webhook policies (silently disabling their security/audit notifications).

`src/server/v2.0/handler/preheat.go:262-267` | P2P preheat policy update accepts `id` and `project_id` from the body with no ownership check | High | `convertParamPolicyToModelPolicy` copies `ID` and `ProjectID` verbatim (`preheat.go:468-473`) and `UpdatePolicy` is called with them after an authorization check bound only to `params.ProjectName`, so a projectAdmin rewrites another project's preheat policy — including its provider and repository/tag filters — causing that project's private images to be distributed to a P2P provider.

`src/server/v2.0/handler/model/scanner.go:43` | Scanner adapter credential returned in the API payload to the lowest-privileged project role | High | `AccessCredential: s.AccessCredential` is emitted by the converter used at `src/server/v2.0/handler/project.go:581` (`GetScannerOfProject`), which requires only project-level `ResourceScanner:read` — a permission granted to guest and limitedGuest (`src/common/rbac/project/rbac_role.go:295,323`); the value is stored in cleartext (`src/pkg/scan/dao/scanner/model.go:50`) and Harbor itself redacts it elsewhere (`src/pkg/scan/job.go:416` writes `"[HIDDEN]"`), so a read-only guest of any project can lift the system-wide scanner Basic/Bearer credential.

`src/server/v2.0/handler/preheat.go:725` | Preheat task log fetched by arbitrary task ID | Medium | `taskCtl.GetLog(ctx, params.TaskID)` is called after authorizing only on `params.ProjectName`; task IDs are sequential integers, so any projectAdmin reads other projects' preheat job logs, which enumerate private repository names, tags and digests.

`src/server/v2.0/handler/preheat.go:581` | Preheat execution of any project readable | Medium | `executionCtl.Get(ctx, params.ExecutionID)` is unconstrained by the authorized project; same for `ListTasks` at `preheat.go:693` (`query.Keywords["execution_id"] = params.ExecutionID`) — both expose another tenant's execution metadata and task inventory.

`src/server/v2.0/handler/preheat.go:650` | Preheat execution of any project can be stopped | Medium | `executionCtl.Stop(ctx, params.ExecutionID)` runs after an authorization check bound to the caller's own project name, giving any projectAdmin a cross-tenant DoS of running preheat jobs.

`src/server/v2.0/handler/retention.go:353` | Retention task log fetched by arbitrary task ID | Medium | Access is checked against retention policy `params.ID` but the log is read for `params.Tid` (`retentionCtl.GetRetentionExecTaskLog` is a bare `taskMgr.GetLog`, `src/controller/retention/controller.go:363`), exposing other projects' full repository/tag deletion inventories.

`src/server/v2.0/handler/retention.go:326` | Retention tasks listed for an execution ID unrelated to the authorized policy | Medium | `ListRetentionExecTasks(ctx, params.Eid, query)` filters on `ExecutionID` only, so any projectAdmin who owns one retention policy enumerates `eid` values and reads other projects' retention task results.

`src/server/v2.0/handler/retention.go:277` | Retention execution stopped using `eid` after authorizing on an unrelated policy `id` | Medium | `OperateRetentionExec(ctx, params.Eid, ...)` never verifies the execution belongs to policy `params.ID`, allowing cross-tenant interruption of a running retention job.

`src/server/v2.0/handler/notification_job.go:34-43` | Webhook job history listed for a policy belonging to another project | Medium | `policy, _ := n.webhookPolicyMgr.Get(ctx, params.PolicyID)` is fetched with no check that `policy.ProjectID` matches the authorized project, and the response carries `JobDetail` — the full webhook payload with repository names, tags, digests and operator usernames.

`src/server/handler/job_status_hook.go:37-45` | Job status hook accepts and acts on unauthenticated, unsigned status changes | Medium | The handler decodes `job.StatusChange` and calls `task.HkHandler.Handle` with no `security.FromContext` check, and it is mounted on six routes with no middleware (`src/server/route.go:53-59`); `src/pkg/task/hook.go:47-82` then uses the attacker-supplied `JobID`/`UpstreamJobID` to `UpdateStatus` and to dispatch check-in processors, so any workload that can reach core's HTTP port directly can forge task/execution outcomes (e.g. mark a failed scan "Success"). The only control is the reverse proxy: `make/photon/prepare/templates/nginx/nginx.https.conf.jinja:227` returns 404 for `/service/notifications`, so this is a trust-boundary/defense-in-depth defect rather than an internet-facing one — it becomes directly exploitable under any custom ingress that does not replicate that rule.

`src/server/middleware/immutable/pushmf.go:49-50` | Immutable-tag enforcement fails open on every error class | Medium | Only "not found" legitimately permits the push, but any error from `artifact.Ctl.GetByReference` (DB error, context cancellation, pool exhaustion) is logged at debug and returns `nil`, which the caller at line 20 treats as "no violation" and forwards the `PUT .../manifests/<tag>` — an attacker who can induce transient DB pressure overwrites a tag the project marked immutable.

`src/server/middleware/blob/put_manifest.go:37` | Manifest `PUT` body buffered entirely in memory before any size check | Medium | `lib.NopCloseRequest(r)` copies the body with a bare `io.Copy` (`src/lib/request.go:53-56`, no `io.LimitReader`) and this line then `ioutil.ReadAll`s it again; the same pattern is at `src/server/middleware/quota/util.go:52`. Both run in core *before* the request is proxied to distribution, which is the component that enforces the 4 MiB manifest cap, so any principal with push rights on one repository OOMs harbor-core with a single multi-gigabyte manifest PUT.

`src/controller/scan/base_controller.go:333-343` | Scan stop resolves the execution by artifact digest alone, ignoring project | Medium | `q.New(q.KeyWords{"extra_attrs.artifact.digest": artifact.Digest})` has no project or repository predicate and `executions[0]` is stopped unconditionally; the handler (`src/server/v2.0/handler/scan.go:50-63`) only verified access to the caller's own copy, so pushing an identical image into a project you control lets you terminate another tenant's in-flight scan for that digest.

`src/server/v2.0/handler/robot.go:287` | Robot update authorizes against a namespace supplied in the request body instead of the robot's own project | Medium | `r` was loaded by `params.RobotID` (path), but `requireAccess(ctx, params.Robot.Level, params.Robot.Permissions[0].Namespace, ActionUpdate)` checks a body value — the sibling handlers `DeleteRobot` (`robot.go:90`) and `RefreshSec` (`robot.go:220`) correctly use `r.Level, r.ProjectID`; a projectAdmin of project A can therefore disable, re-scope or wipe the permissions of another project's robot, gated only by having to echo the target's exact `name` and `level` (checked at `robot.go:291`).

`src/controller/artifact/controller.go:586` | Artifact label attachment performs no label-scope validation | Medium | `c.labelMgr.AddTo(ctx, labelID, artifactID)` inserts a bare `Reference{LabelID, ArtifactID}` row (`src/pkg/label/manager.go:95-104`) and the handler (`src/server/v2.0/handler/artifact.go:459`) only checked project access on the *artifact*, so any developer attaches another project's private label to their own artifact and reads its name/description/colour back via `?with_label=true`.

`src/controller/artifact/processor/chart/chart.go:87` | Unbounded `ReadAll` plus in-memory archive expansion of an attacker-supplied blob | Medium | The chart layer is read with `ioutil.ReadAll(blob)` and handed to `GetDetails` → `loader.LoadArchive`, which gunzips/untars the same bytes; the sibling icon path shows the correct pattern (`src/controller/artifact/annotation/v1alpha1.go:83` wraps its read in `io.LimitReader(icon, 1<<20)`), so any user with push rights uploads a large or highly compressible chart layer and exhausts core's memory via `GET .../additions/values`.

`src/server/v2.0/handler/scan.go:102` | Scan report log fetched by report UUID with no binding to the authorized artifact | Low | The artifact resolved at line 97 is discarded and `scanCtl.GetScanLog(ctx, params.ReportID)` resolves the report globally (`src/controller/scan/base_controller.go:635-645`), so a caller holding `scan:read` in any project can read the scan log of an artifact in a project they cannot access; report IDs are v4 UUIDs, so this needs a leaked/retained identifier rather than brute force.

`src/server/v2.0/handler/icon.go:37-38` | Icon retrieval has no authentication or project check at all | Low | `GetIcon` calls `i.ctl.Get(ctx, params.Digest)` with no `Prepare`, no `RequireAuthenticated` and no project scoping, and the controller resolves the digest across *all* projects and pulls that blob (`src/controller/icon/controller.go:116-126`), so knowing an icon layer digest returns that blob's content re-encoded as a 50×50 PNG from a project the caller has no membership in.

`src/server/middleware/csrf/csrf.go:57` | The configured CSRF HMAC key is written verbatim to the log | Low | `log.Warningf("Invalid CSRF key from environment: %s, ...", key)` prints the real `CSRF_KEY` whenever its length is not exactly 32, publishing it to whatever log sink core ships to — an audience typically wider than the container environment. (The random fallback itself is sound, and `secureCookie()` fails closed to `Secure`/`SameSite=Strict`.)

`src/server/v2.0/handler/gc.go:70` | The Redis connection URL, password included, is persisted into GC job parameters and echoed by the API | Low | `parameters["redis_url_reg"] = os.Getenv("_REDIS_URL_REG")` is carried into the execution's `ExtraAttrs` (`src/controller/gc/controller.go:79` → `exeMgr.Create`) and returned verbatim as `job_parameters` at `src/server/v2.0/handler/gc.go:165` and `:204`; only a system administrator can read those endpoints, so this is credential-hygiene (the secret also lands in DB rows and job logs) rather than a privilege-boundary crossing.

`src/server/v2.0/handler/scan.go:43-45` | `Prepare` computes an error responder and discards it, so the request proceeds on a failed path-unescape | Low | `if err := unescapePathParams(params, "RepositoryName"); err != nil { s.SendError(ctx, err) }` never `return`s the responder; identical bugs at `src/server/v2.0/handler/artifact.go:71-73` and `src/server/v2.0/handler/repository.go:58-60`. Impact is limited (the handler then operates on a still-escaped repository name and fails the lookup), but it is a silently swallowed error on the request-normalisation path.

## Provenance note

All three sweeps independently diffed the in-scope files against `raw.githubusercontent.com/goharbor/harbor/v2.5.1/...`
and found them byte-identical (the diff harness was sanity-checked against v2.6.0, which does produce output).
There is no injected/backdoored patch in this tree — every finding above is a genuine upstream v2.5.1 defect.

## Claims checked and rejected

- **Robot secret hashing is not weak.** `utils.Encrypt` is `pbkdf2.Key(..., 4096, 16, sha256)` (`src/common/utils/encrypt.go:49-51`), not a single unstretched SHA-256; the non-constant-time `!=` at `src/server/middleware/security/robot.go:57` compares derived keys and is not practically timing-exploitable. Not reported.
- **`math/rand` at `src/controller/registry/controller.go:218`** is HA start-up jitter, not secret material. Not reported.
- **`convertRegistry`** masks `AccessSecret` as `*****` (`src/server/v2.0/handler/replication.go:478-480`); registry credentials are not leaked. Not reported.
- **v2 registry authorization** (`src/server/middleware/v2auth/auth.go`, `access.go`) authorizes the same normalized repository the downstream handlers read, fails closed on project-lookup errors, and issues a separate `ActionPull` entry for blob mounts. No defect found.
- **Search** (`src/server/v2.0/handler/search.go:74-85`) falls back to `public: true` for non-local security contexts — restrictive, not permissive. No defect.
- **SQL injection / SSRF / `InsecureSkipVerify` / `exec.Command`**: none present in scope; sorts are filtered against model metadata in `src/lib/orm/query.go` and keywords are parameterized.

## Coverage — what was actually examined

**Read in full:** all 63 non-test files under `src/server/middleware/**`, `src/server/registry/**`, `src/server/router/`,
`src/server/handler/`; all 34 non-test files in `src/server/v2.0/handler/` plus `handler/model/*` and `handler/assembler/`;
`src/controller/` — `proxy/`, `scan/`, `scanner/`, `robot/`, `user/`, `usergroup/`, `member/`, `project/`, `registry/`,
`retention/`, `quota/`, `blob/`, `gc/`, `config/`, `ldap/`, `immutable/`, `health/`, `icon/`, `systeminfo/`, `tag/`,
`task/`, `repository/`, `artifact/controller.go` + `annotation/` + `processor/{base,chart,image/manifest_v1}`,
`replication/{policy,execution}.go` + `flow/stage.go` + `transfer/image/transfer.go`, and the `event/handler/` subtree
entry points.

**Covered by targeted pattern sweep rather than full read** (TLS/crypto/randomness/exec/unbounded-read/authorization
patterns; nothing flagged beyond what is reported): `src/controller/event/{topic,metadata,model,operator}`, the remaining
`event/handler/webhook/*` and `event/handler/replication/*` files, `src/controller/replication/flow/{controller,copy,deletion}.go`,
`src/controller/replication/transfer/chart/`, `src/controller/artifact/{abstractor,helper,model}.go` and
`processor/{processor,default,base/index,image/index,image/manifest_v2,cnab}.go`, and the `*/options.go` /
`*/model.go` files across `src/controller/`.

**Out of scope but read for exploitability confirmation only:** `src/lib/request.go`, `src/lib/orm/query.go`,
`src/common/rbac/project/rbac_role.go`, `src/common/utils/encrypt.go`, `src/pkg/task/hook.go`,
`src/pkg/immutable/{manager,dao}`, `src/pkg/label/{manager,dao}`, `src/pkg/scan/{job.go,dao/scanner/model.go}`,
`src/pkg/notification/policy/model/model.go`, `src/core/middlewares/middlewares.go`, `src/server/route.go`,
`make/photon/prepare/templates/nginx/nginx.https.conf.jinja`.

**Not examined:** all `*_test.go` (excluded by scope).
