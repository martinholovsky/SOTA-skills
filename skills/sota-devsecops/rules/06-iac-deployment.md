# 06 — IaC & Deployment Security (Terraform, GitOps, progressive delivery)

Scope: infrastructure change control and the path an artifact takes into production.
Principles: state is secret, plans are reviewed and applied verbatim, git is the single
source of truth (and therefore a tier-0 system), every deploy is reversible.

## 6.1 Terraform state is secret material

State files contain resolved secrets in plaintext (DB passwords, generated keys, full
resource attributes) regardless of how carefully you wrote the HCL. Treat state like a
credentials vault:

- **Remote backend, encrypted, versioned, locked**: S3 + SSE-KMS + versioning + (modern TF)
  S3 native lockfile or DynamoDB locking; or Terraform Cloud/HCP, GCS+CMEK, azurerm with
  RBAC. Local state, or state committed to git, = Critical.
- Access to the state backend is access to every secret in it: scope IAM to the state
  key prefix per workspace; humans get read at most, and ideally nothing — plan/apply runs
  in CI and people read plan output. Broad `s3:*` on the state bucket for all engineers =
  High.
- **Keep secrets out of state where possible**: prefer `ephemeral` resources/values and
  write-only arguments (TF ≥1.10/1.11; OpenTofu ≥1.11, Dec 2025) for credentials; or have
  Terraform create the *container* (secret resource) while a separate controlled path
  writes the *value*; or reference external secret managers at runtime (ESO, rules below).
  `random_password` + direct DB resource args put the password in state forever — flag,
  with the ephemeral alternative named. On OpenTofu, also enable its native **state
  encryption** (client-side, no Terraform equivalent) as defense in depth on top of
  backend encryption.
- State backups inherit the classification: bucket replication targets and DynamoDB/lock
  tables are in scope for the audit.
- Never `terraform.tfstate*`, `*.tfvars` with secrets, or crash logs in git —
  `.gitignore` them and secret-scan for them (rules/05 §5.2).

```hcl
# GOOD — backend with encryption, locking, versioning assumed on the bucket
terraform {
  backend "s3" {
    bucket       = "acme-tf-state"
    key          = "prod/network/terraform.tfstate"
    region       = "eu-central-1"
    kms_key_id   = "arn:aws:kms:eu-central-1:123456789012:key/..."
    use_lockfile = true              # native S3 locking (TF >= 1.10)
  }
}

# GOOD — secret never enters state (TF >= 1.11 write-only argument)
ephemeral "random_password" "db" { length = 24 }
resource "aws_db_instance" "main" {
  password_wo         = ephemeral.random_password.db.result
  password_wo_version = 1            # bump to rotate
  # ...
}

# BAD — password persisted in plaintext state forever
resource "random_password" "db" { length = 24 }
resource "aws_db_instance" "main" { password = random_password.db.result }
```

## 6.2 Plan/apply separation with review

The change-control core: **what was reviewed is exactly what gets applied.**

- **PR opens → `terraform plan` runs with read-only credentials** (a plan needs read; a
  planner role with write defeats the separation — and plan output lands in PR comments,
  so the plan job itself must be treated as untrusted-adjacent: no fork PR planning with
  real creds, rules/01 §1.4).
- **Plan artifact is saved (`-out=plan.bin`) and the apply consumes that exact file.**
  Re-planning at apply time ("plan for review, fresh plan on merge") is TOCTOU: what
  applies may differ from what was approved. Store `plan.bin` as a build artifact keyed to
  the commit; apply job downloads and `terraform apply plan.bin`.
- **Apply runs only**: after merge to the protected branch, in a protected environment
  with required reviewers (rules/01 §1.7), under a separate OIDC role that has write
  (rules/01 §1.2). Two roles minimum per workspace: `tf-plan-ro`, `tf-apply`.
- Plan output in the PR (atlantis/tf-comment style) is the review surface — reviewers
  approve the *plan*, not the HCL diff alone. Train for the dangerous lines: `forces
  replacement`, `destroy`, IAM/security-group changes.
- `-detailed-exitcode` to distinguish "no changes" from "changes" in automation; never
  auto-approve applies (`-auto-approve` is fine ONLY when applying a reviewed saved plan —
  that's what the review was).
- Local applies from laptops against shared envs = High (no review, no audit, drift,
  credential sprawl). Lock it out: humans don't hold apply-capable cloud creds for
  prod; the pipeline role's trust policy only accepts the apply workflow identity.

Reference workflow split:

```yaml
# plan.yml — on: pull_request; role: tf-plan-ro (ReadOnly + state read)
permissions: { contents: read, id-token: write, pull-requests: write }
steps:
  - run: terraform plan -out=plan.bin -detailed-exitcode -input=false -lock-timeout=5m
  - uses: actions/upload-artifact@<sha>
    with: { name: plan-${{ github.sha }}, path: plan.bin }

# apply.yml — on: push: {branches: [main]}; environment: tf-prod (required reviewers)
permissions: { contents: read, id-token: write }
steps:
  - uses: actions/download-artifact@<sha>   # the SAME plan.bin reviewed on the PR
  - run: terraform apply -input=false plan.bin
    # apply fails if state changed since plan — that failure is the control working;
    # the response is re-plan + re-review, never force.
```

Atlantis/TF Cloud/Spacelift implement this pattern as a product — fine, audit the same
properties: read-only plan creds, saved-plan apply, reviewer gate, per-workspace roles.

## 6.3 Drift detection

Drift = reality diverged from code: clicky-ops, incident hand-edits, or an attacker's
changes that your next apply will either revert (outage) or silently absorb.

- **Scheduled `terraform plan -detailed-exitcode` per workspace** (nightly), alerting on
  exit code 2 with the diff. Route to the owning team; drift findings get the same
  triage discipline as vulns (owner, deadline) — an ignored drift channel is no detection.
- Drift response is binary: import/codify the change (it was a legitimate emergency fix)
  or revert it (it wasn't). Both end with main == reality.
- Reduce drift at the source: read-only consoles for humans in prod accounts (break-glass
  excepted, rules/07 §7.5); SCPs/IAM denying out-of-band mutation of TF-managed resource
  classes where practical.
- GitOps equivalents: Argo CD `selfHeal: true` auto-reverts live drift; Flux reconciles
  continuously. Self-heal is drift *prevention*; still alert on the correction events —
  the interesting question is who changed it.

## 6.4 GitOps (Flux/Argo) security model

Pull-based GitOps inverts the trust: CI never holds cluster credentials (huge win — a
compromised pipeline can't `kubectl` into prod), but **the config repo and the controller
become the deployment authority**:

- **The config repo is prod**: full rules/01 §1.7 protection (reviews, required checks,
  no direct push, CODEOWNERS per environment path), because merging to `envs/prod/` IS
  deploying. Most orgs protect the app repo and leave the manifests repo wide open —
  standing High finding.
- **Controller blast radius**: Argo CD's controller is cluster-admin-equivalent; its API
  + UI are a deployment control plane. SSO + RBAC (no local admin account in prod),
  `AppProject`s constraining each team to their namespaces/repos/clusters,
  `sourceNamespaces`/destination restrictions. A default `AppProject` with `*` everything
  = High. Treat even *read-only* Argo access as sensitive and patch the controller as
  tier-0 software: CVE-2026-42880 (CVSS 9.6, fixed in 3.3.9/3.2.11) let read-only users
  extract plaintext k8s Secrets via the ServerSideDiff endpoint.
- **Repo-server/Redis network isolation is mandatory, not optional**: the repo-server's
  internal gRPC service is unauthenticated and carries a publicly disclosed, still-unpatched
  RCE (Synacktiv, Jul 2026 — reported Jan 2025, no CVE): any compromised pod that can reach
  its port can execute commands via crafted Kustomize/Helm options, read the Redis password,
  poison cached manifests, and ride auto-sync into attacker-controlled deployments. The Helm
  chart ships NetworkPolicies but they are **off by default** (`networkPolicy.create: false`)
  — enable them so only Argo components can reach repo-server and Redis ports.
- **Auto-sync to prod only with gates in front**: auto-sync + self-heal is correct *when*
  the path into the repo is gated (reviews + verified images). Argo sync windows and
  health checks; sync waves for ordering.
- **Secrets in GitOps**: never plaintext in the repo. Preference order: External Secrets
  Operator / CSI secrets-store referencing a real secret manager (rotation, audit, nothing
  secret in git) > SOPS+KMS (encrypted-in-git, key via cloud KMS) > Sealed Secrets
  (cluster-key dependency complicates DR). Plaintext k8s `Secret` manifests in a repo =
  Critical-adjacent High, rotation required (rules/05 §5.2).
- **Image automation** (Flux image-update / Argo Image Updater) re-introduces the supply
  chain into git: constrain it to digest updates matching signed images (admission still
  verifies, rules/07 §7.1), and its write token is scoped to the one file path it bumps.
- Manifest provenance: pin remote Helm charts by version + verify chart signatures/
  digests (OCI charts by digest); a `targetRevision: HEAD` on a third-party repo is
  rules/03 unpinned-dependency, cluster edition.

```yaml
# GOOD — Argo CD AppProject as a hard boundary per team
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata: { name: payments, namespace: argocd }
spec:
  sourceRepos: ["https://github.com/acme/payments-deploy.git"]   # only this repo
  destinations:
    - server: https://kubernetes.default.svc
      namespace: "payments-*"                                    # only these namespaces
  clusterResourceWhitelist: []          # no cluster-scoped resources for app teams
  namespaceResourceBlacklist:
    - { group: "", kind: ResourceQuota }
    - { group: "rbac.authorization.k8s.io", kind: "*" }          # apps don't ship RBAC
```

Audit shortcut: `kubectl get appproject default -o yaml` — if real apps sit in the
`default` project (sourceRepos `*`, destinations `*`), every repo write anywhere becomes
potential cluster-admin (High).

## 6.5 Progressive delivery & rollback readiness

Deployment strategy is a security control: blast-radius limitation for bad code is
blast-radius limitation for compromised code.

- **Canary with automated analysis** (Argo Rollouts/Flagger): shift 5→25→50→100% gated on
  *metrics* (error rate, latency, business KPI), auto-rollback on regression. A "canary"
  that a human eyeballs and promotes by feel is a slow rollout, not a canary — define the
  AnalysisTemplate.
- **Blue/green** where canary is impractical (schema-coupled, session-heavy): keep the
  idle stack for instant rollback; the cutover and rollback are both one routing change —
  and *test the rollback path*, not just the cutover.
- **Feature flags decouple deploy from release**: dark-launch code, kill-switch risky
  features (a flag flip is your fastest "rollback"). Flag hygiene: flags have owners and
  expiry; stale flags are dead branches in prod with untested OFF paths. Flag service
  access is a prod control plane — RBAC + audit its changes.
- **Rollback readiness, tested**:
  - Previous artifact digest is retained and deployable (rules/04 §4.5 retention) and the
    rollback is a pipeline action (re-point to previous digest / `git revert` the GitOps
    commit), not an SSH session. Roll back to a *known artifact*, don't rebuild old source.
  - **DB migrations are expand/contract**: every migration is backward-compatible one
    version (add column nullable → deploy code → backfill → enforce → later drop). A
    deploy whose migration breaks version N-1 has no rollback — that's a finding even if
    the deploy succeeded.
  - Measure and drill it: if rollback hasn't been executed in anger or game-day within
    ~quarterly, assume it doesn't work.
- Maintenance reality check: deploys gated on a single human, untested rollback, or
  Friday-evening big-bang releases are availability findings (Medium) — availability is a
  security property.

```yaml
# GOOD — canary that decides on data, not vibes (Argo Rollouts)
strategy:
  canary:
    steps:
      - setWeight: 5
      - analysis: { templates: [{ templateName: error-rate }] }   # auto-abort on breach
      - setWeight: 25
      - pause: { duration: 10m }
      - analysis: { templates: [{ templateName: error-rate }, { templateName: p99-latency }] }
      - setWeight: 100
---
apiVersion: argoproj.io/v1alpha1
kind: AnalysisTemplate
metadata: { name: error-rate }
spec:
  metrics:
    - name: error-rate
      interval: 1m
      failureLimit: 2
      successCondition: result < 0.01
      provider:
        prometheus:
          query: sum(rate(http_requests_total{job="app",code=~"5.."}[2m])) / sum(rate(http_requests_total{job="app"}[2m]))
```

Expand/contract migration sequence (the only DB pattern compatible with canary AND
rollback): 1) additive migration ships alone (new column nullable / new table / dual-write
shim) — old code unaffected; 2) code reading new path ships, still writing both;
3) backfill; 4) constraints tightened, old path removed — **at least one release later**.
The audit question for any migration PR: "can version N-1 run against the post-migration
schema?" If no, rollback is fiction for that release window.

## 6.6 Environment parity — build once, promote many

- **The artifact that ran in staging is byte-identical (same digest) to what reaches
  prod.** Rebuilding "the same tag" for prod invalidates every test and every attestation
  (rules/02). Promotion = copying/approving a digest, never recompiling.
- Configuration differences between environments are **declared and diffable**: kustomize
  overlays / Helm env values / TF workspace tfvars in git — not hand-set env vars or
  console toggles. The prod-vs-staging delta should be reviewable in one screen; an
  unexplained delta is where "works in staging" incidents live.
- Same pipeline shape per env (staging deploys exercise the prod deploy mechanism); only
  approvals/gates differ. A bespoke prod-only deploy script is untested by definition.
- Ephemeral preview environments (per-PR) are great — but they multiply credentials and
  DNS: previews get isolated, low-privilege, auto-expiring infra, never shared prod
  data or prod-scoped roles (and watch rules/01 §1.2 OIDC sub-claims: PR-triggered envs
  must not be able to assume prod roles).
- Data parity without data leakage: staging uses masked/synthetic data. A prod-data dump
  in staging makes staging a prod-tier system with non-prod controls (High).

## Audit checklist

- [ ] TF state: remote encrypted versioned backend with locking; no state/tfvars in git; backend access least-privilege; secrets kept out of state via ephemeral/write-only/external-manager patterns
- [ ] Plan on PR with read-only role; saved plan artifact applied verbatim post-merge in a reviewer-gated environment with a separate apply role; no laptop applies; no fork PRs planning with real creds
- [ ] Scheduled drift detection per workspace, alerts owned and actioned (codify or revert); human prod console access read-only outside break-glass
- [ ] GitOps repo protected like prod (reviews, CODEOWNERS per env path); Argo/Flux RBAC + AppProject/destination constraints; Argo NetworkPolicies enabled — repo-server gRPC is unauthenticated with an unpatched public RCE (mid-2026); no plaintext secrets in repos (ESO/SOPS/Sealed); third-party charts/manifests pinned by version/digest
- [ ] Image automation constrained to digest bumps of signed images with a path-scoped token
- [ ] Progressive delivery with automated metric analysis and auto-rollback; blue/green rollback path tested; feature flags have owners/expiry and audited control plane
- [ ] Rollback: previous digests retained and re-deployable via pipeline; migrations expand/contract (N-1 compatible); rollback drilled within the last quarter
- [ ] Build-once-promote-many by digest; env config deltas declared in git and reviewable; previews isolated with non-prod roles; staging data masked/synthetic
