# 04 — GitOps Controller Security (Argo CD, Flux)

Scope: the controller that reconciles git into the cluster — Argo CD and Flux. Its own
privileges and self-management risk, project/tenant scoping (the `clusterResourceWhitelist`
escalation trap), SSO/RBAC, repo/credential scoping, ApplicationSet/templating injection,
sync strategy, drift, recent CVEs, and promotion/rollback as git operations. CI/CD
*pipeline* and deployment *strategy* are `sota-devsecops` (rules/06); this file owns the
in-cluster controller's security model. SSO/OIDC *design* is `sota-identity-access`.

**Core principle:** GitOps is the *only* write path to the cluster. Humans don't `kubectl
apply` to prod — they open a PR; the controller reconciles the merged state. This makes
git the audit log and review gate, and makes the **controller a cluster-admin-class
component** whose compromise = cluster compromise. Scope it accordingly.

---

## 1. The controller is privileged — treat it as crown jewels

Argo CD's application-controller / Flux's controllers apply arbitrary manifests, so they
hold broad (often cluster-admin-equivalent) RBAC by design. Therefore:
- **The git repo + the controller's RBAC + who can change either = your real attack
  surface.** Anyone who can merge to the watched branch, or who can edit the controller's
  config, can deploy anything the controller can apply.
- **Branch protection + required review + signed commits** on GitOps repos are not
  optional (`sota-devsecops` rules/01). A self-approved merge to `main` is a deploy.
- **Self-management risk**: if the controller manages *its own* manifests (RBAC, config,
  the App that defines other Apps — "app-of-apps"), a malicious PR can widen its own
  privileges or repoint it at a hostile repo. Put the controller's own bootstrap under
  extra-tight review, or manage it out-of-band.
- Run the controller in its own namespace; restrict who has RBAC *to* Argo CD/Flux
  resources (Applications, AppProjects, GitRepositories, Kustomizations) — editing an
  Application is editing a deployment.

## 2. Argo CD AppProject scoping — the `clusterResourceWhitelist` trap

`AppProject` is Argo CD's tenancy/blast-radius boundary. It constrains which repos, which
destination clusters/namespaces, and which **resource kinds** an Application may deploy.
The traps:

```yaml
# BAD — a project that can deploy anything, anywhere, from any repo
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata: { name: team-a, namespace: argocd }
spec:
  sourceRepos: ["*"]
  destinations: [{ server: "*", namespace: "*" }]
  clusterResourceWhitelist: [{ group: "*", kind: "*" }]   # can create ClusterRoles, etc.
```

- **`clusterResourceWhitelist: [{group:'*',kind:'*'}]`** lets the project create *cluster-
  scoped* resources of any kind — including `ClusterRole`/`ClusterRoleBinding`. A tenant
  who can commit to that project's repo can bind themselves cluster-admin via a manifest.
  **Combined with broad SSO/RBAC into the project, this is Critical.** Allow only the
  specific cluster-scoped kinds the tenant legitimately needs (often *none* — leave it
  empty/unset so cluster resources are denied).
- **`sourceRepos: ["*"]`** lets the project deploy from any repo, defeating provenance.
  Pin to the exact repos.
- **`destinations` with `*`** lets one project write to every cluster/namespace. Pin to the
  tenant's clusters and namespaces.
- The **`default` AppProject is wide open** — don't run production Apps in it; lock it down
  (empty sourceRepos/destinations) and use named projects.
- Use `namespaceResourceBlacklist` / `clusterResourceBlacklist` to forbid dangerous kinds
  (e.g. `ResourceQuota`, `LimitRange`, RBAC) even within an otherwise-scoped project.

```yaml
# GOOD — scoped project; no cluster-scoped kinds, pinned repo + destination
spec:
  sourceRepos: ["https://github.com/org/team-a-config.git"]
  destinations: [{ server: "https://kubernetes.default.svc", namespace: "team-a-*" }]
  clusterResourceWhitelist: []        # cluster-scoped resources denied
  namespaceResourceBlacklist: [{ group: "rbac.authorization.k8s.io", kind: "*" }]
```

## 3. SSO, RBAC, and credentials

- **SSO over local accounts.** Disable the built-in `admin` account in prod (`admin.
  enabled: false`) after bootstrap, or scope it to break-glass; rotate its secret. Wire
  OIDC/SSO (design → `sota-identity-access`).
- **Argo CD RBAC** (`policy.csv`): map SSO groups to roles; default policy `role:''`
  (no access). Scope roles to specific projects/Applications — not `role:admin` for
  everyone. The `g, <group>, role:admin` line is the equivalent of a cluster-admin binding.
- **Repository credentials are secrets**: scope read-only deploy keys / fine-grained PATs
  per-repo, store them as Argo CD repo Secrets (or via ESO — `sota-secrets-management`),
  never embed write creds. A controller with org-write git creds can poison source.
- **Cluster credentials**: when one Argo CD manages multiple clusters, each cluster
  credential is a foothold; scope and rotate them.

## 4. ApplicationSet & templating injection

ApplicationSet generates Applications from generators (git directories, PR/SCM, lists,
clusters). Generated fields are **templated** — untrusted input in a generator can inject
into the Application spec:
- **PR/SCM generators reading fork PRs** can let an external contributor influence
  generated Applications (repo URL, path, namespace) — treat like the `pull_request_target`
  problem (`sota-devsecops` rules/01). Restrict generators to trusted repos/branches; don't
  template attacker-controlled fields into `project`, `destination`, or `source`.
- Keep ApplicationSet `templatePatch`/Go-template values constrained; an injected
  `project:` field can move an App into a more-privileged AppProject.

## 5. Sync strategy & drift

- **Auto-sync vs sync-with-approval**: auto-sync makes a merge an immediate deploy — good
  for low-risk envs, paired with strong PR review. For prod, gate with manual sync /
  **sync windows** / approval so a merge doesn't instantly hit prod without a release step.
- **`selfHeal: true`** reverts out-of-band `kubectl` changes back to git — this is the
  point of GitOps (it kills drift and unaudited changes). Pair with **`prune: true`**
  carefully (prune deletes resources removed from git; a bad git change can delete prod).
- **Drift detection is a security signal**: an OutOfSync resource nobody changed in git
  means someone wrote to the cluster directly (or a controller is fighting). Alert on
  unexpected drift; investigate it as a possible intrusion, not just noise.
- **Promotion and rollback are git operations**: promote by moving a verified digest
  through environment overlays/branches (build-once-promote-many, `sota-devsecops`
  rules/06); roll back by reverting the git commit, not by hand-editing the cluster.

## 6. Patch the controller — recent Argo CD CVEs

The GitOps controller is high-value and has a live CVE stream; track and patch it like the
control plane (`rules/01` §7). Recent examples (verify against the Argo CD security
advisories before citing exact IDs/versions):
- **GHSA-3v3m-wc6v-x4x3 (CVE-2026-42880), ~May 2026, Critical** — Kubernetes Secret
  extraction via the ServerSideDiff feature: a low-privilege/read-only user could obtain
  plaintext Secret data. Patched in the then-current 3.2.x/3.3.x patch releases; upgrade.
- **GHSA-786q-9hcg-v9ff (CVE-2025-55190), Sep 2025, Critical (CVSS ~10)** — project API
  tokens with even `get` permission could retrieve repository credentials. Patched in
  2.13.9 / 2.14.16 / 3.0.14 / 3.1.2.
- Plus assorted webhook-parser DoS and stored-XSS (annotation) advisories.

Current Argo CD line is ~3.4.x (verify). Stay on a supported minor, watch the advisories
feed, and patch Critical auth/secret-exposure issues on the emergency track. Flux likewise
publishes advisories — track its controllers' CVEs.

## 7. Write-back controllers — the success log is not the commit

§1–§6 cover what the controller may do *inward*: git → cluster. A controller that
also writes **outward** — an image-update controller, a PR bot, config sync
committing rendered manifests back — is an instrument reporting on itself, so
`sota-code-security` rules/12 §2 applies to it in full. Its log describes the
update it *decided* to make, not the write landing.

**R7.1 — Verify at the remote, never from the controller's own counters.**
`git ls-remote` the branch, read the file on `origin`, or diff the rendered
manifest. A line like `images_considered=2 images_skipped=0 images_updated=1
errors=0` reports decisions taken in memory, and is emitted independently of any
commit.

Measured (2026-08-18, a GitOps image-update controller on a private cluster).
A second image alias was added to one custom resource so that two images built
from the same commit would move in lockstep. The controller then logged
`Committing 1 parameter update(s)` and `Successfully updated the live application
spec` **every reconcile cycle for ~15 minutes across ~7 cycles**, while making no
`git commit` or `git push` at all — nothing in its own log, and the remote branch
never moved. Net effect: the primary application silently stopped auto-deploying
and the two images skewed apart, which is the exact invariant the second alias
existed to guarantee. Removing the alias, with the primary image deliberately left
on the old tag so the next reconcile was a clean experiment, produced a commit
within **84 seconds** — that is what established cause rather than correlation.
The controller-side root cause was never found and did not need to be: the
operator has to check the remote, not explain the bug.

**R7.2 — A per-object counter counts decisions; an aggregate hides the failure.**
Both traps are in that incident. `updated=1` counts what the reconciler resolved
to do. And where a controller manages N objects, one object's success masks
another's silent failure in any rolled-up total — the write kept working for one
image and stopped for the other while the aggregate stayed healthy. **Assert on
all N, not on the sum.** Alert on the **age of the last observed remote change**,
which goes stale by itself when writes stop; a counter of successes never will.

**R7.3 — This is a liveness gap, not an integrity one.** Nothing was corrupted and
no alarm was wrong: a write that should have happened did not, and every signal
reporting on it was a signal about intent. Freshness is the only observable that
degrades when an outbound write stops — the same distinction `sota-code-security`
rules/04 §8 draws between integrity and completeness for audit ledgers.

## Audit checklist

- [ ] GitOps is the only write path to prod (no routine human `kubectl apply`); GitOps repos have branch protection + required review + signed commits?
- [ ] Controller runs least-privilege where possible; RBAC *to* Argo CD/Flux resources (Applications/AppProjects/Kustomizations) is restricted; self-management/bootstrap under extra review?
- [ ] No AppProject with `clusterResourceWhitelist: [{group:'*',kind:'*'}]` (or it's justified + tightly access-controlled)? (`kubectl get appprojects -A -o yaml | grep -A3 clusterResourceWhitelist`)
- [ ] AppProjects pin `sourceRepos` and `destinations` (no `*`); `default` project locked down; RBAC-creating kinds blacklisted where not needed?
- [ ] Argo CD SSO wired, built-in admin disabled/break-glass, RBAC `policy.csv` scoped per project (no blanket `role:admin`)?
- [ ] Repo/cluster credentials scoped (read-only deploy keys, per-repo), stored as secrets/ESO, rotated — no org-write creds in the controller?
- [ ] ApplicationSet generators restricted to trusted repos/branches; no untrusted input templated into `project`/`destination`/`source`?
- [ ] Prod sync gated (approval/sync windows), not blind auto-sync; `prune`/`selfHeal` reviewed; drift alerted and triaged as a security signal?
- [ ] Promotion = move verified digest through git; rollback = git revert (not hand-edits)?
- [ ] Argo CD/Flux on a supported version, CVE feed tracked, recent Critical advisories (Secret-extraction, cred-exposure) patched? (`argocd version`)
- [ ] Any controller that writes **outward** (image updater, PR bot, config sync committing back) is verified **at the remote** — `git ls-remote` / the file on `origin` / a rendered-manifest diff — not from its own `updated=N errors=0`; freshness of the last remote change is alerted, and a controller managing N objects asserts on all N rather than an aggregate? (§7)
