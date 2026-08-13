# Security audit — `src/server/` + `src/controller/` (Go)

Repository root: `/private/tmp/claude-501/registry-svc-b0506782/svc`
Subject: Harbor v2.5.1 container registry (module path `github.com/goharbor/harbor`, `VERSION` = `v2.5.1`).
Scope: 232 non-test `.go` files under `src/server/` and `src/controller/`.

**Enforcement model (established first, because every authz finding depends on it):**
the global middleware chain (`src/core/middlewares/middlewares.go:80-96`) is
`mergeslash, trace, metric, requestid, log, session, csrf, orm, notification, transaction,
artifactinfo, security.Middleware, security.UnauthorizedMiddleware, readonly`. It only *builds*
a security context — there is **no authorization middleware**, and `BaseAPI.Prepare`
(`src/server/v2.0/handler/base.go:50`) returns `nil` (= allow). Handler-level `Require*Access`
calls are therefore the *only* enforcement point, so a missing or misdirected call is covered
nowhere else. This refutation was run against every finding below.

The recurring defect shape: the handler authorizes against the **project in the URL path** (or a
project supplied in the **request body**), then acts on a **primary-key ID taken from the request**
that is never verified to belong to that project.

---

## Findings

```
src/server/v2.0/handler/notification_policy.go:155 | GetWebhookPolicyOfProject authorizes on {project_name_or_id} (:151) but then fetches the policy by params.WebhookPolicyID with no project binding; the response serializes the target's auth_header verbatim (src/server/v2.0/handler/model/notification_policy.go:37) | Critical | any user holding webhook-read in any one project — including a project they created themselves — iterates integer policy IDs and reads every other project's webhook endpoint URL together with its auth_header, which is a live bearer credential for the victim's notification receiver. Cross-tenant credential theft, scriptable, no precondition beyond one project membership.
src/server/v2.0/handler/notification_policy.go:130 | UpdateWebhookPolicyOfProject copies the policy from the request body (lib.JSONCopy at :116) — including its ID — and overwrites only ProjectID (:129) before webhookPolicyMgr.Update; the stored policy's project is never checked | High | a project admin passes another project's policy ID and re-parents that policy into their own project while rewriting its target URL, auth header and event types — silently redirecting the victim's security/audit notifications to an attacker-controlled endpoint.
src/server/v2.0/handler/notification_policy.go:143 | DeleteWebhookPolicyOfProject deletes params.WebhookPolicyID after authorizing only on the path project; the manager filters on ID alone | High | cross-tenant destruction: an attacker with webhook-delete in their own project removes another project's webhook policies, blinding that tenant's notification/alerting before further abuse.
src/server/v2.0/handler/preheat.go:267 | UpdatePolicy authorizes on params.ProjectName, then passes a policy built entirely from the request body to preheatCtl.UpdatePolicy; convertParamPolicyToModelPolicy carries the client-supplied ID (:469) and ProjectID (:472) straight through, and the path policy name is ignored | High | a maintainer of one project overwrites any preheat (P2P distribution) policy in any project — provider, filters, cron trigger, enabled flag — redirecting another tenant's image distribution to an attacker-chosen provider.
src/server/v2.0/handler/preheat.go:725 | GetPreheatLog authorizes on the path project, then calls taskCtl.GetLog(ctx, params.TaskID) on the global task controller with no task→execution→project binding | High | any project maintainer reads the raw job log of any task in the system by ID — replication, GC, retention and scan tasks belonging to other tenants — which enumerates their repositories, tags and registry endpoints.
src/server/middleware/util/util.go:71 | SkipPolicyChecking bypasses deployment-security policy when strings.Contains(r.UserAgent(), "cosign") is true; the User-Agent header is entirely client-controlled and is the only thing distinguishing cosign from an attacker (the accompanying ActionPush check is satisfied by requesting a push-scoped token from /service/token) | High | a caller with push rights on a repository sets `User-Agent: cosign` on a manifest GET and bypasses all three pull-time gates that call this helper — vulnerability prevention (src/server/middleware/vulnerable/vulnerable.go:71), Notary content trust (src/server/middleware/contenttrust/notary.go:56) and Cosign content trust (src/server/middleware/contenttrust/cosign.go:41). A security decision taken on an untrusted input (CWE-807).
src/server/middleware/contenttrust/cosign.go:56 | the "Cosign content trust" gate is satisfied by the mere existence of an accessory row of type TypeCosignSignature; no signature is ever verified against a key. That row is created by src/server/middleware/cosign/cosign.go:91 purely because a pushed manifest declares a layer mediaType of application/vnd.dev.cosign.simplesigning.v1+json — the signature bytes and annotation are never validated | High | any user with push rights to the project pushes a fabricated `sha256-<digest>.sig` manifest containing one layer with that media type, and the project's "images must be signed" policy is permanently satisfied for that artifact. A control that is present and inert (CWE-347).
src/controller/icon/controller.go:136 | image.Decode on a blob pulled from the registry with no size and no dimension bound. The only limit anywhere on this path is the 1 MB LimitReader at src/controller/artifact/annotation/v1alpha1.go:83, which is applied to a different read (the push-time content sniff) and, per the finding below, truncates rather than rejects | High | a small, valid PNG whose IHDR declares e.g. 30000x30000 is a few KB — it passes the push-time content-type sniff at v1alpha1.go:94 and is recorded as the artifact icon (v1alpha1.go:97). GET /api/v2.0/icons/{digest} then decodes it into a ~3.6 GB pixel buffer and OOMs harbor-core. The read endpoint (src/server/v2.0/handler/icon.go:38) performs no authorization at all, so the trigger is unauthenticated once the icon exists.
src/controller/artifact/processor/chart/chart.go:87 | ioutil.ReadAll of a chart layer with no limit of any kind | High | reachable by a low-privileged reader: GET .../artifacts/{ref}/additions/values.yaml needs only ActionRead on ResourceArtifactAddition (src/server/v2.0/handler/artifact.go:431). An attacker pushes an artifact whose config mediaType is application/vnd.cncf.helm.config.v1+json (chart.go:41) with an arbitrarily large second layer, then requests the addition. Computed per request and not cached, so concurrent requests multiply the allocation.
src/controller/artifact/processor/chart/chart.go:92 | chartOperator.GetDetails(content) hands attacker bytes to helm's LoadArchive, which gzip/tar-expands via io.Copy with no cap (vendored helm v3.7.1) | High | decompression bomb stacked on the previous finding — a ~1 MB gzip layer that passes any input-side size check expands to gigabytes inside core's heap, via the same low-privilege addition endpoint.
src/controller/artifact/processor/base/manifest.go:99 | json.NewDecoder(blob).Decode(v) on an attacker-pushed config blob with no size bound; mani.Config.Size (:88) is only tested for ==0, never used as a limit | High | reached on every manifest PUT (putManifest → artifact.Ctl.Ensure → abstractor.go:83 → AbstractMetadata). Any user with push rights to their own project uploads a multi-GB JSON config blob plus a manifest referencing it; core decodes it whole into Go objects (JSON→map inflates several-fold) and OOMs.
src/controller/artifact/processor/default.go:112 | the same unbounded json.NewDecoder(blob).Decode(&metadata), and the result is then assigned to artifact.ExtraAttrs (:117) and persisted to Postgres | High | easier to reach than the previous one: defaultProcessor handles any *unregistered* config mediaType (processor.go:68-71), so the attacker simply names their config "application/vnd.anything.config.v1+json". Adds unbounded DB row growth to the memory exhaustion.
src/server/v2.0/handler/robot.go:287 | updateV2Robot authorizes with requireAccess(params.Robot.Level, params.Robot.Permissions[0].Namespace, ...) — i.e. against the level and namespace in the request body, not against the robot fetched at :191. Contrast DeleteRobot (:90) and RefreshSec (:220), which correctly use r.Level/r.ProjectID | High | any authenticated user creates their own project (so becomes its admin), then submits another project's robot ID with level=project and namespace=<own project>. requireAccess passes, and the victim robot's permissions are wiped and re-created, or it is disabled / re-dated. The only remaining barrier is the name equality check at :291, which needs the victim robot's name — guessable for human-named robots (`robot$victimproj+ci`).
src/server/v2.0/handler/preheat.go:650 | StopExecution authorizes on the path project, then calls executionCtl.Stop(ctx, params.ExecutionID) on the shared execution controller | Medium | any project maintainer aborts arbitrary system executions by ID — garbage collection, replication runs, scan-all, retention — a cross-tenant and system-level denial of service.
src/server/v2.0/handler/preheat.go:581 | GetExecution returns executionCtl.Get(ctx, params.ExecutionID) with no check that the execution belongs to the path project or policy; ListTasks (:693) likewise queries on execution_id alone | Medium | ID enumeration discloses other tenants' execution and task metadata — vendor type, status and extra_attrs, which carry resource names.
src/server/v2.0/handler/retention.go:205 | UpdateRetention builds the policy from the request body (:196, with only p.ID forced to params.ID) and then authorizes via requireAccess(ctx, p, ...) — which switches on p.Scope, a project reference the attacker chose | Medium | a user with retention rights in their own project supplies scope=<own project> plus another project's policy ID, and overwrites that project's tag-retention rules and scope — destroying or hijacking the victim's retention configuration.
src/server/v2.0/handler/retention.go:353 | GetRetentionTaskLog authorizes against the policy identified by params.ID, then reads the log of params.Tid, an unrelated task ID (same shape at ListRetentionTasks :326 and OperateRetentionExecution :277) | Medium | with retention-read on any one policy, an attacker reads any retention task log — which enumerates the repositories and tags deleted in other projects — and can stop other projects' retention executions.
src/server/v2.0/handler/immutable.go:62 | DeleteImmuRule authorizes on the path project, then deletes params.ImmutableRuleID; the controller and manager delete by ID only | Medium | an attacker with immutable-tag rights in their own project deletes another project's immutable-tag rules, stripping the tamper-protection that prevents release tags being overwritten there.
src/controller/immutable/controller.go:64 | UpdateImmutableRule receives projectID but, when m0.Disabled != m.Disabled, routes to EnableImmutableRule(ctx, m.ID, m.Disabled) — keyed on the client-supplied rule ID alone, discarding projectID entirely | Medium | reached from src/server/v2.0/handler/immutable.go:84, which copies the rule ID out of the request body (:75). A project admin disables any other project's immutable-tag rule by ID, then overwrites that project's protected tags.
src/server/handler/job_status_hook.go:37 | the job-status hook handler performs no authentication or authorization whatsoever — it decodes the body and calls task.HkHandler.Handle, which looks up a task by the attacker-supplied JobID and writes the attacker-supplied Status (src/pkg/task/hook.go:50-86). The `secret` security generator (src/server/middleware/security/secret.go:29) exists for exactly this caller but is never required. Routed at src/server/route.go:53-59 | Medium | anyone who can reach harbor-core directly forges task/execution status transitions and check-in payloads for replication, GC, retention and scheduler tasks. Deciding assumption: the bundled nginx returns 404 for /service/notifications (make/photon/prepare/templates/nginx/nginx.http.conf.jinja:200), so this is not externally reachable in the default deployment — it is High for any deployment behind a different ingress, or for an attacker with pod-network access to core, since network position is not identity.
src/server/v2.0/handler/scan.go:102 | GetReportLog checks project access and resolves the artifact, then calls scanCtl.GetScanLog(ctx, params.ReportID) with a report UUID that is never bound to that artifact; the controller (src/controller/scan/base_controller.go:635) resolves UUID→task with no ownership check | Medium | a user with scan-read in any project reads the scan job log of any artifact system-wide — package inventory and vulnerability detail of other tenants' private images. Rated Medium rather than High only because report UUIDs are random: exploitation needs a leaked ID (retained from prior access, or from a shared report link).
src/server/v2.0/handler/notification_job.go:34 | ListWebhookJobs authorizes on the path project, then fetches the policy by params.PolicyID with no check that it belongs to that project | Medium | lists webhook delivery jobs — status and event payload metadata — for any other project's policy.
src/controller/proxy/controller.go:229 | the proxy-cache trusts the upstream registry's self-reported Docker-Content-Digest and never recomputes it from the payload; that unverified value becomes artInfo.Digest and the manifest cache key (:172, manifestcache.go:70-76). digest.FromBytes is used only for the trimmed list (manifestcache.go:147), never to validate the cached original | Medium | a hostile or compromised upstream returns payload P under header digest D where sha256(P) != D; Harbor caches and re-serves P under D and records the artifact under D in its own DB and UI. Deciding assumption: requires a hostile upstream or MITM on an endpoint configured Insecure/http — docker and containerd verify manifest digests themselves, so client-side impact is bounded; Harbor's own metadata is not.
src/server/middleware/immutable/pushmf.go:52 | handlePush returns nil — i.e. allows the push — on *any* error from artifact.Ctl.GetByReference, not just NotFound; DB errors, timeouts and context cancellation all fail open | Medium | immutable-tag protection silently lapses whenever the artifact lookup errors, letting a protected release tag be overwritten. Fail-open enforcement (CWE-636); the not-found case needs the allow, the rest do not.
src/server/middleware/csrf/csrf.go:57 | log.Warningf("Invalid CSRF key from environment: %s, ...", key) writes the raw CSRF_KEY environment value into the application log whenever its length is not exactly 32 | Low | secret material in logs (CWE-532). Impact is bounded because the malformed key is then discarded in favour of a generated one, so the logged value is not the key in use — but the operator-supplied secret still lands in log aggregation.
src/controller/artifact/annotation/v1alpha1.go:85 | dead error branch: io.ReadAll never returns io.EOF (it is documented to return nil at EOF), so the "the maximum size of the icon is 1MB" rejection can never fire | Low | silent control failure (CWE-561). The LimitReader on :83 does bound this particular read, so it is not itself a DoS — but an oversized icon layer is silently TRUNCATED to 1 MB, content-sniffed on the truncated head and accepted, instead of being rejected as the code intends. This is the check that would otherwise have constrained the icon pixel-bomb above.
src/controller/registry/controller.go:91 | lib.ValidateHTTPURL applies no SSRF control at all — it checks the scheme only (src/lib/endpoint.go:40) and strips query/fragment — while the comment at src/lib/endpoint.go:43 claims "To avoid SSRF security issue" | Low | 127.0.0.1, 169.254.169.254 (cloud IMDS) and all RFC1918 addresses are accepted; :97 then calls IsHealthy against the URL and returns healthy/unhealthy plus error text, giving a working SSRF probe oracle. Low because the endpoint is system-admin gated (src/server/v2.0/handler/registry.go:45) and pointing a registry endpoint somewhere is the feature's purpose — the defect worth fixing is the comment asserting a control that does not exist.
src/server/middleware/repoproxy/proxy.go:80 | setHeaders is called after io.CopyN (:73) has already written the response body, so every header it sets is a no-op | Low | proxy-cache blob responses ship with no Docker-Content-Digest and no Content-Length. Not directly exploitable — clients verify blobs against the manifest digest — but it silently removes the integrity header the code believes it is sending.
src/server/middleware/repoproxy/proxy.go:170 | setHeaders(..., art.Digest) where art.Digest is empty on a pull by tag; confirmed at src/server/middleware/artifactinfo/artifact_info.go:128-132, where a reference matching the tag regexp sets Tag and leaves Digest empty | Low | GET by tag through a proxy project returns Docker-Content-Digest: "" and Etag: "" — a broken integrity and cache-validation header rather than a wrong one.
src/controller/artifact/processor/chart/chart.go:91 | blob.Close() is not deferred, so the reader leaks on the ReadAll error path at :88-90 | Low | an attacker who aborts or stalls the layer read leaks a connection and a file descriptor per request; repeatable, so it is a slow resource-exhaustion primitive against core.
```

---

## Explicitly refuted — recorded so they are not re-raised

- **`SkipPolicyChecking` accessory branch (util.go:76-82) is *not* a universal policy bypass.**
  It lists accessories by `ArtifactID`, and `src/server/middleware/cosign/cosign.go:111-113` stores
  the *signature* artifact's ID there (the signed image goes in `SubArtifactID`). So the branch
  fires only when the signature artifact itself is being pulled, which is the documented intent.
- **`math/rand` at `src/controller/registry/controller.go:218`** — real, but it only jitters an HA
  health-check start time. Nothing security-bearing depends on it. `src/common/utils/utils.go:18`
  imports `crypto/rand`, so robot secrets, salts and the generated CSRF key are CSPRNG-derived.
- **Path traversal** — repository names are constrained by `reference.NameRegexp` and digests by
  `digest.DigestRegexp` (`src/lib/patterns.go:22-28`). Second, independent method: a grep for
  `filepath.Join`, `os.Open`, `os.Create`, `os.ReadFile` across the whole scope returned three hits,
  all verified safe — `src/server/router/router.go:77` (route registration, not request data),
  `src/controller/systeminfo/controller.go:146` (constant `defaultRootCert` path) and
  `src/controller/icon/controller.go:110` (path from the hardcoded `builtInIcons` map).
- **SQL injection** — zero hits for string-built SQL across the scope
  (`(Query|Exec|QueryRow|Raw|Filter|Where)\(("…"\s*\+|fmt\.Sprintf)`); all DB access goes through
  `q.Query` keyword maps into the beego ORM.
- **`InsecureSkipVerify` / disabled TLS verification** — zero hits in scope. The `true` at
  `src/controller/proxy/local.go:93` is the insecure flag on a client pointed at
  `config.LocalCoreURL()` (loopback, in-process), which is deliberate and commented.
- **Registry credentials are redacted** on the API — `convertRegistry` sets `AccessSecret = "*****"`
  (`src/server/v2.0/handler/replication.go:478`).
- **Proxy-cache does honour caller permissions** — both proxy middlewares sit behind
  `v2auth.Middleware()` on the `/v2` root route (`src/server/registry/route.go:34-36`), so
  local-project authorization runs before any upstream fetch.
- **Correct handlers** (checked and clean): `label.go:177` authorizes against the label's own scope;
  `robotV1.go` scopes every lookup by `{ProjectID, ID}`; `member.go`, `project_metadata.go`,
  `repository.go`, `artifact.go` (including the source-project check on `CopyArtifact` at :170)
  resolve everything from the path project; `user.go` has no self-promotion path
  (`UpdateUserProfile` sets only realname/email/comment, and `SetUserSysAdmin` requires
  `RequireSystemAccess`); `auditlog.go`, `statistic.go`, `search.go`, `project.go:ListProjects` and
  `repository.go:ListAllRepositories` all constrain results to member/public projects for non-admins.
- **Not reported for lack of demonstrable impact:** `src/server/middleware/artifactinfo/artifact_info.go:113`
  iterates `urlPatterns` as a Go map, so route classification is nondeterministic when a path matches
  more than one pattern — real, but the project name is always the first path component under every
  pattern, so the authorization decision (which keys on project) is unaffected.
  `src/server/middleware/security/robot.go:57` compares the robot secret hash with `!=` rather than a
  constant-time compare — a hash comparison, not a secret comparison, with no practical remote oracle.

## One denominator worth stating

Grepping the entire non-vendor `controller/`, `server/`, `pkg/registry/` and `pkg/artifact/` tree for
any read limit (`LimitReader`, `MaxBytesReader`, `MaxSize`, `1<<20`) returns **exactly one hit** — the
inert icon limit above. There is no size ceiling on attacker-supplied manifest or config content
anywhere on this path. The quota middleware (`src/server/middleware/quota/put_manifest.go:59-77`)
accounts storage against a project quota that is unlimited by default and, when set, orders of
magnitude above what exhausts the process.

## Coverage — what was actually examined

**Read in full (me):** `server/route.go`, `server/server.go`, `core/middlewares/middlewares.go`,
all 11 files of `server/middleware/security/`, `server/middleware/v2auth/{auth,access}.go`,
`server/middleware/csrf/csrf.go`, `server/middleware/session/session.go`,
`server/middleware/{middleware,skipper}.go`, `server/middleware/artifactinfo/artifact_info.go`,
`server/middleware/{mergeslash,readonly}/`, `server/middleware/util/util.go`,
`server/middleware/contenttrust/{cosign,notary}.go`, `server/middleware/vulnerable/vulnerable.go`,
`server/middleware/immutable/pushmf.go`, `server/middleware/cosign/cosign.go`,
`server/middleware/quota/util.go`, `server/handler/job_status_hook.go`,
`server/v2.0/handler/{base,config,health,icon,robot,scan}.go`,
`controller/{config,health,icon,immutable,ldap,robot}/`, `controller/health/checker.go`,
`controller/scan/{base_controller,callback}.go` (credential-handling sections),
`controller/proxy/controller.go` (manifest path).

**Read in full (delegated, then re-verified by me at every cited line):** all 36 non-test files of
`server/v2.0/handler/`; `controller/proxy/*`; `server/middleware/repoproxy/*`; `server/registry/*`;
`controller/artifact/processor/**`; `controller/artifact/annotation/*`;
`controller/replication/transfer/**`; `controller/registry/controller.go`.

**Swept by grep only, not read line-by-line:** `controller/event/**` (metadata, webhook and audit-log
handlers), `controller/replication/{execution,policy,flow}`, `controller/quota/**`,
`controller/{member,user,usergroup,retention,task,tag,repository,project}/`,
`server/middleware/{blob,quota,orm,transaction,trace,log,metric,requestid,apiversion,notification}/`.
The greps run over these were: string-built SQL, `exec.Command`, `InsecureSkipVerify`, `math/rand`,
`filepath.Join`/`os.Open`/`os.Create`/`os.ReadFile`, `io.ReadAll`/`ioutil.ReadAll`,
`LimitReader`/`MaxBytesReader`, `http.Get`/`http.NewRequest`/`http.DefaultClient`, and `go func`.
Nothing in those directories is claimed clean — only that these specific sink classes are absent there.
