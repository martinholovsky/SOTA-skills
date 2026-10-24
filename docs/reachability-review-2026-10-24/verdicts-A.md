# Verdicts — batch A (refuter)

Tree: `<repo>` at `f2cd26f9`. Read-only.

### F1 — Ray / notebook / pipeline-UI control planes: HIGH rule, no probe

- **verdict:** CONFIRMED (High)
- **evidence:** `skills/sota-ml-engineering/rules/01-ml-systems-architecture.md:79-85` holds the rule as quoted ("HIGH on sight when exposed"). The only §6 checklist item, `:129-132` "Trust-domain separation (§6) — HIGH", probes `grep -rnE 'mlflow (server|ui)' . | grep -v 'app-name'` plus a manual question about training-job credentials. Nothing in it names Ray, notebooks, Kubeflow or `RAY_AUTH_MODE`. `git grep -n -iE 'notebook server|jupyter|\bray\b|dashboard.*(unauth|expos)' -- skills/` hits only `ml/01:80`, the Kubernetes Dashboard item (`sota-kubernetes/rules/01:283`, which is not Ray) and a generic severity-table row (`sota-network-security/SKILL.md:88`, "admin/dashboard reachable unauthenticated from outside"). That row is a severity example, not a probe. `sota-cloud-infrastructure/rules/04:36` mentions Ray only as a compute choice. Attempted kill: the item cites "(§6)", so an auditor might go back and re-read the section. Rejected, because the item's wording ("trackers started without auth") and its probe scope it to MLflow.
- **if confirmed, minimal fix:** extend the `ml/01` §6 checklist item with a control-plane locator, `grep -rnE 'ray (start|job)|ray\.init|RayCluster|dashboard-host|jupyter-  (`lab|notebook|server`)|kubeflow' .`, plus a check that `RAY_AUTH_MODE=token` is set. Add a manual check that no control plane is reachable from outside its trust domain (HIGH).

### F1 — Secrets AUDIT procedure never selects four of its five rules files

- **verdict:** DOWNGRADED (High → Medium)
- **evidence:** The finding is real at the skill level. `skills/sota-secrets-management/SKILL.md:65-95` sweeps tooling, grep, history, handling and triage, and never says to walk the rules files' checklists. BUILD step 7 (`:63`) does say it. The same skill scopes AUDIT to "find secret leaks/misuse" (`:67`), so lifecycle and storage probes sit partly outside the mode's declared scope. The severity is inflated because the router's full-audit path requires the checklists:
  - `skills/sota/SKILL.md:405-406`: "For each applicable skill, follow its AUDIT mode **and audit checklists**. Suggested order: secrets sweep…"
  - `skills/sota/rules/01-audit-methodology.md:7-9`: "**what** to check comes from each domain skill's AUDIT mode and the Audit checklist at the end of every rules file".

  So the gap bites only on a secrets-only audit entered directly through this skill.
- **if confirmed, minimal fix:** add AUDIT step 6 to `sota-secrets-management/SKILL.md`: "Walk the Audit checklist at the end of rules/01–05; rules/04 covers leaks, not lifecycle, storage or credential-type handling."

### F2 — Embedded device rules (secure boot, debug lock, OTA anti-rollback) are unreachable from a firmware task

- **verdict:** CONFIRMED (High)
- **evidence:**
  - The rule exists: `sota-security-compliance/rules/05-iec-62443-ot-ics.md:120-124` opens §6 with "The library has **no owner for the embedded systems layer**".
  - `sota-c-cpp/SKILL.md:46-56` says the systems layer is unowned ("No skill in this library owns those today. Say so…") and links nowhere into compliance.
  - `git grep -n -E 'sota-security-compliance/rules/0[45]' -- skills/ | grep -v '^skills/sota-security-compliance/'` returned nothing.
  - `git grep -n -iE 'anti-rollback|secure boot|eFuse|JTAG|firmware update|\bOTA\b' -- skills/ | grep -v '^skills/sota-security-compliance/'` returned only false positives on "refuse".
  - Router: `git grep -n -iE 'firmware|device|IoT|over-the-air|anti-rollback|62443|security-compliance' -- skills/sota/` hits only the compliance row (`SKILL.md:194`, "signed updates" in a CRA/regime frame), a FIPS line (`:305`) and the library map.
  - Positive control: `git grep -c sota-shell-scripting -- skills/sota/SKILL.md` = 6.

  The compliance description's "(OT/ICS/embedded)" sits in a regime clause, and its trigger keywords are all regime words. Attempted kill: c-cpp's list of unowned topics (ISRs, DMA, MMIO, RTOS, WCET, linker scripts) does not literally include secure boot. Rejected, because nothing routes a bootloader/OTA task to the rule either way.
- **if confirmed, minimal fix:** in the `sota-c-cpp/SKILL.md` embedded paragraph, add "Device boot chain, debug-port lock, OTA update integrity/anti-rollback and decommissioning: `sota-security-compliance` rules/05 §6 and rules/04 §2".

### F3 — Cross-org mTLS peer pinning (never CN, private-CA client certs) has no inbound pointer

- **verdict:** CONFIRMED (High)
- **evidence:** The reviewer's search method was flawed. `grep 'sota-network-security/rules/04'` cannot match relative links, and network-security's own files do link it: `rules/01:29,59,79`, `rules/02:78`, `rules/03:159`, `rules/05:174`, and `rules/06:218` "…from a private CA scoped to client auth (rules/04 R4.1)". The conclusion holds outside the skill, though. Neither `sota-api-design/rules/07:14` (mTLS row) nor `sota-code-security/rules/04:277-286` points to R4.1. Worse, code-security §5 reads "chain-validate the client certificate against the CA you expect **before its subject becomes an identity**" (`:277-278`), which implies the subject is the identity. That is the CN anti-pattern R4.1 forbids. The checklist item `code-security/04:454-458` probes only chain-validation opt-outs, not peer pinning.
- **if confirmed, minimal fix:** add one clause to `sota-code-security/rules/04` §5's mTLS bullet: "…and authorise the peer by a pinned typed SAN or SPKI, never CN/DN (`sota-network-security` rules/04 R4.1)". Add the same pointer beside the mTLS row in `sota-api-design/rules/07`.

### F4 — "Sign what you selected" (fork artifact signed by name) has no audit probe

- **verdict:** CONFIRMED (High)
- **evidence:**
  - `skills/sota-devsecops/rules/02-provenance-signing.md:195-208` holds the rule, which rates the verified case Critical.
  - The `rules/02` Audit checklist (`:326-336`) has no item on how a signing input is selected.
  - `awk '/^## Audit checklist/{f=1} f' skills/sota-devsecops/rules/01-pipeline-security.md | grep -iE 'artifact|fork'` returned nothing.
  - `git grep -n -iE '\- \[ \].*(artifact).*(fork|hostile|untrusted)|\- \[ \].*fork.*artifact' -- skills/` hits only an IaC plan-artifact item (`rules/06:312`).
  - `git grep -n -iE 'head_repository|same-named' -- skills/` hits only `rules/02:203-207`.
  - The nearest checklist line, `rules/01:488`, is about checking out PR head content, not artifact selection. `rules/01:178` cites §2.5.2 only for severity.
- **if confirmed, minimal fix:** add a `rules/02` checklist item, "Signing input bound to producer (§2.5.2) — Critical". Locator: `grep -rnE 'actions/artifacts\?name=|sort_by\(\.created_at\)|download-artifact' .github/workflows`. Each hit that feeds a sign/publish step must check `workflow_run.head_repository.full_name` per artifact, not from the list endpoint.

### F-R2-1 — The identity AUDIT sweep enumerates rules 01–06 and never reaches rules/07 (Active Directory / ADCS)

- **verdict:** CONFIRMED (High)
- **evidence:**
  - `skills/sota-identity-access/SKILL.md:90-92` sweeps 01–06 only.
  - AUDIT step 1 (`:82-85`) enumerates only the IdP.
  - BUILD steps 1–6 (`:58-75`) also omit 07.
  - The only routes into 07 are the index row (`:133`, "Hardening on-prem Active Directory…") and detection-engineering's pointers (`sota-detection-engineering/SKILL.md:130`, `rules/07:11,153`). Narrow inbound links exist as well.

  An explicitly AD-framed task reaches 07 through the index. A generic "audit our identity estate" sweep over a hybrid estate does not, and 07's probes are absence checks (MAQ default 10, `krbtgt` never rotated) that no other file runs.
- **if confirmed, minimal fix:** add to sweep step 3 "07 (on-prem AD/Kerberos/ADCS — whenever the estate has a domain, ADCS or a sync server)", and to step 1 "enumerate AD domains, ADCS CAs, sync server".

### F-R3-1 — Observability's own correlation snippet binds `tenant_id`/`user_id` into logger context with no reset, and links nowhere to the cross-tenant-leak rules

- **verdict:** DOWNGRADED (High → Medium)
- **evidence:**
  - The defect is real. `sota-observability/rules/01-structured-logging.md:112-126` binds contextvars with no clear, and `:134-136` tells the reader to bind `user_id`/`tenant_id` the same way.
  - `grep -n -iE 'clear|reset|MDC|ThreadLocal|contextvars' skills/sota-observability/rules/*.md` finds no reset rule. The nearest is `rules/03:157`, which restores context in async work, a different concern.
  - `git grep -n clear_contextvars -- skills/` hits only `sota-python/rules/04:152,284`. The JVM counter-rule is at `sota-jvm/rules/03:60-70`.

  Severity is inflated. `sota-python/rules/04:146-147` records that "each asyncio task … runs in a copied context, so a value set there does not escape", so the snippet leaks only under reused threads (threaded WSGI, pools). The consequence is mis-attributed internal log lines, a log-integrity and privacy issue. It exposes no data across tenants. The language skills catch it whenever the matching one is loaded.
- **if confirmed, minimal fix:** add `structlog.contextvars.clear_contextvars()` as the snippet's first middleware line. Add one bullet: "request-scoped logger context is reset per request (`clear_contextvars` / MDC `clear` in `finally`) — `sota-python` rules/04 §6, `sota-jvm` rules/03".

### F5 — FPM runtime user and a non-writable webroot are never checked

- **verdict:** CONFIRMED (High)
- **evidence:**
  - Rule: `sota-php/rules/04-sessions-auth-web-hardening.md:254-257`.
  - `rules/04` checklist: grepping it for `fpm|user|root|writ|docroot|webroot` hits only the §5c handoff item (`:452-463`: docroot, `vendor/`, `limit_extensions`, `fix_pathinfo`), the resource-caps item (`:425-430`) and session save-path lines. None checks the pool user or write permission.
  - `rules/06` checklist: FPM sizing only (`:174-175`), plus the worker-mode item.
  - `grep -n -iE 'writable|non-root|pool.*user|user =' skills/sota-php/...` hits only prose: `04:214`, `04:254`, `06:82`.

  Attempted kill: generic container non-root checks in sandboxing or devsecops might cover it. Rejected. They are not pointed to from PHP, and they do not test whether the FPM pool user can write the webroot.
- **if confirmed, minimal fix:** add a §5 item to the `rules/04` checklist:
  - `php-fpm -tt 2>&1 | grep -E '^\s*(user|group) ='` per pool; root = HIGH.
  - Shared pool users across apps = MEDIUM.
  - On the image, run `find <app-root> -writable` as the pool user. Only cache, upload and session dirs may appear.

### F6 — auth and session code never learns that worker mode leaks the previous request's user

- **verdict:** REFUTED (low residual at most)
- **evidence:** `skills/sota-php/SKILL.md:103`, the rules index row for 06, names the exact trigger: "**worker mode** (Octane, FrankenPHP, RoadRunner, Swoole): request state that leaks into the next request". The finding's example task ("add per-tenant scoping to our Laravel Octane API") contains "Octane", which matches that row directly. In AUDIT, `SKILL.md:64-65` runs "the 'Audit checklist' blocks at the end of every relevant rules file", which reaches the HIGH worker-mode item at `rules/06:185-192`. A builder in a worker-mode project sees Octane, FrankenPHP or RoadRunner in `composer.json` or the deploy config, which is the routing signal the index row keys on. The reviewer marked this UNSURE for the same reason. A cross-pointer from `rules/04` would be nice-to-have, not a reachability defect.
- **if confirmed, minimal fix:** (optional) one bullet in `rules/04` §1: "under a worker-mode runtime, request user/tenant state is reset per request — `rules/06` §4a".

### F1 — api-design never points to sota-testing; the tenant-isolation test trap is unreachable from where API authz tests get written

- **verdict:** DOWNGRADED (High → Medium)
- **evidence:**
  - The link absence is real. `git grep -c 'sota-testing' -- skills/sota-api-design/` returned nothing (exit 1). The positive control `git grep -c sota-code-security` returned `01:2, 05:1, 07:7`.
  - `sota-api-design/rules/07:316-318` ("Test it continuously…") carries no link at all. A link extraction over lines 270-318 found none.
  - The trap is real, at `sota-testing/rules/09:158-168`.

  Severity is inflated on two counts. First, the production-path control (the app role is not BYPASSRLS/superuser) is covered on the API build path through `sota-code-security/rules/03:205` and `sota-databases/rules/06:28`. The missing item is the validity of the test suite, a false-assurance defect rather than a direct vulnerability. Second, the moment the agent writes that suite, the `sota-testing` description triggers on "IDOR test, authz test", so a test-writing task has its own route.
- **if confirmed, minimal fix:** append to `api-design/rules/07` §7 "Test it continuously": "run it as the production DB role and pooler, deny + allow per RLS operation — `sota-testing` rules/09 §3/§3a".

---

Tally: 10 findings: 6 CONFIRMED, 3 DOWNGRADED, 1 REFUTED.

- CONFIRMED: ML F1, compliance F2, mTLS F3, devsecops F4, identity F-R2-1, PHP F5.
- DOWNGRADED: secrets F1, observability F-R3-1, api-design/testing F1.
- REFUTED: PHP worker-mode F6.
