# 02 — RBAC & ServiceAccounts

Scope: the K8s authorization graph and workload identity — least-privilege Roles/
ClusterRoles, the privilege-escalation traps, ServiceAccount hygiene and token model, and
how to audit who-can-do-what. RBAC *role-design methodology and SSO* is
`sota-identity-access`; this file owns the **K8s RBAC mechanics and the escalation traps**.
Workload identity to cloud and secret backends is `sota-secrets-management` (rules/01).

RBAC is the cluster's authorization fabric: `Role`/`ClusterRole` (a set of allowed
verbs×resources) bound to subjects (users, groups, ServiceAccounts) by `RoleBinding`
(namespaced) / `ClusterRoleBinding` (cluster-wide). Authorization is additive and
allow-only — there is no deny rule. So the only lever is **granting less**.

---

## 1. Least privilege — the shape of a good Role

- **Enumerate verbs and resources explicitly.** Name the API groups, resources, and verbs
  the workload actually uses. Default to `get`/`list`/`watch`; add `create`/`update`/
  `patch`/`delete` only where proven.
- **Namespaced `Role` over `ClusterRole`** unless the resource is cluster-scoped or the
  subject genuinely needs all namespaces. A `ClusterRoleBinding` is cluster-wide blast radius.
- **`resourceNames`** to scope to specific objects where the API supports it (e.g. read
  one named ConfigMap, not all ConfigMaps).
- **Separate read from write**; separate by namespace/team. One mega-role bound everywhere
  is the distributed `cluster-admin`.

```yaml
# GOOD — narrow, namespaced, explicit
kind: Role
metadata: { name: orders-reader, namespace: orders }
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    resourceNames: ["orders-config"]
    verbs: ["get", "watch"]
```

## 2. The escalation traps (each a High/Critical finding)

### 2.1 Wildcards
`verbs: ["*"]`, `resources: ["*"]`, or `apiGroups: ["*"]` grant **everything that exists
now and everything added in future API versions**. A `*/*` ClusterRole is effectively
cluster-admin. Never on a workload, CI, or tenant subject.

```yaml
# BAD — this is cluster-admin with extra steps
rules:
  - apiGroups: ["*"]
    resources: ["*"]
    verbs: ["*"]
```

### 2.2 The escalation verbs: `bind`, `escalate`, `impersonate`
These are not ordinary write verbs — they let a subject **grant itself more than it has**:
- **`escalate`** (on `roles`/`clusterroles`): create/edit a role with *more* permissions
  than you hold. Normally RBAC stops you from authoring a role above your own privileges;
  `escalate` removes that guard. → self-grant cluster-admin.
- **`bind`** (on `roles`/`clusterroles`): bind an existing powerful role to yourself.
  `bind` on `cluster-admin` = `bind` yourself to cluster-admin.
- **`impersonate`** (on `users`/`groups`/`serviceaccounts`): act as another principal —
  impersonate a cluster-admin user/group, or `system:masters`. Total bypass.

Grant these only to a **named, audited human-admin path**, never to a workload or
automation SA. `impersonate` on `groups` for `system:masters` is an instant Critical.

### 2.3 ClusterRoleBinding to `cluster-admin` (or to broad subjects)
- A ClusterRoleBinding of the built-in `cluster-admin` ClusterRole to a **ServiceAccount**
  means owning that pod owns the cluster. Critical.
- Binding *any* role to the group **`system:authenticated`** grants it to every
  authenticated principal (including, if anonymous-auth is on, the bridge to anonymous);
  to **`system:unauthenticated`** grants it to the world. Both Critical.

### 2.4 Aggregated ClusterRoles
ClusterRoles with `aggregationRule` automatically absorb the rules of any ClusterRole
matching the label selector. A new operator/chart that ships a ClusterRole with the
aggregation label (e.g. `rbac.authorization.k8s.io/aggregate-to-admin: "true"`) silently
**widens the built-in `admin`/`edit`/`view` roles cluster-wide**. Audit what aggregates
into the powerful roles; a hostile or careless chart uses this to escalate quietly.

### 2.5 The secret-reader → privilege chain
`get`/`list` on `secrets` is rarely "just read a config value." Secrets hold
ServiceAccount tokens, TLS keys, kubeconfigs, cloud creds. **Read on secrets in a
namespace ≈ the union of every identity whose token/cred lives there.** Specifically:
- Read SA token Secrets → authenticate as those SAs → inherit their RBAC.
- `create` on `serviceaccounts/token` (TokenRequest) or `create pods` with a privileged SA
  → mint/borrow a stronger identity.
- `create`/`update` on `pods` lets you schedule a pod that *mounts a more-privileged SA*
  or mounts host paths/Secrets — pod-create is a classic lateral/escalation primitive.

Treat broad `secrets` read, `pods` create, and `serviceaccounts/token` create as
near-Secret-equivalent and near-impersonate-equivalent; scope them hard. Policy-engine
CRDs belong in the same class: create/update on Kyverno (namespaced) policies runs
attacker logic inside the admission-controller pod (`rules/03` §2, CVE-2026-4789).

### 2.6 The Helm-chart-grants-cluster-admin trap
Charts and operators bundle their own RBAC. A values toggle like
`rbac.clusterAdministrator: true`, `rbac.create: true` with a `*/*` ClusterRole, or a
default ServiceAccount bound to `cluster-admin` hands the workload the cluster. **Always
`helm template | grep -A20 -iE 'ClusterRole|ClusterRoleBinding'` before install** and read
the rules (`rules/07` covers chart review). A logging agent does not need cluster-admin.

## 3. ServiceAccount hygiene & the token model

- **`automountServiceAccountToken: false` by default** — on the ServiceAccount and/or pod
  spec. A pod that never calls the Kubernetes API should not carry a credential to it.
  Opt in only for pods that talk to the API. A mounted token + an SSRF/RCE in the pod =
  the attacker holds that SA's RBAC.

```yaml
# GOOD — SA carries no token unless a pod explicitly needs it
apiVersion: v1
kind: ServiceAccount
metadata: { name: web, namespace: shop }
automountServiceAccountToken: false
---
apiVersion: v1
kind: Pod
spec:
  serviceAccountName: web
  automountServiceAccountToken: true   # explicit, only because this pod calls the API
```

- **Bound, projected, short-lived tokens are the model** (bound-SA-token volumes GA since
  1.22). Pods get an auto-rotating, time-bound token (default ~1h) via a projected volume,
  audience-scoped, tied to the pod's lifetime. This is the default mount mechanism — good.
- **No long-lived Secret-based SA tokens.** Since 1.24 the API server **no longer
  auto-creates** a forever-token Secret per ServiceAccount (GA 1.26). Do not manually
  create `kubernetes.io/service-account-token` Secrets for routine use — they are
  non-expiring, non-rotating bearer credentials that leak into logs/backups/etcd. If an
  external system needs an SA token, mint a **short-lived audience-scoped token** via the
  TokenRequest API (`kubectl create token sa --audience=... --duration=...`) and refresh it.
- **Audience-scoped tokens**: a token minted for audience `vault` is rejected by the API
  server and by any verifier expecting a different audience — limits replay if leaked.
- **One ServiceAccount per workload**, never the namespace `default` SA for real
  workloads, never shared across apps. The `default` SA should have an empty token mount
  and no bindings.

## 4. Auditing RBAC

RBAC is allow-only and additive, so the real question is always "what is the transitive
closure of what subject X can do, and can it escalate?" Tools:

- **`kubectl auth can-i`** — point checks, including as another subject:
  ```bash
  kubectl auth can-i '*' '*' --as=system:serviceaccount:ci:deployer    # cluster-admin?
  kubectl auth can-i create clusterrolebindings --as=...
  kubectl auth can-i list secrets -A --as=...
  ```
- **`kubectl auth whoami`** — confirm your own identity/groups.
- **rbac-tool** (insights/aquasecurity), **krane**, **kubectl-who-can** (aquasecurity) —
  build the reverse index: *who* can `escalate`, `bind`, `impersonate`, read secrets,
  create pods, mint tokens. Run who-can on every escalation primitive:
  ```bash
  kubectl who-can create pods -A
  kubectl who-can '*' '*'
  kubectl who-can impersonate users
  ```
- **Hunt patterns** across the RBAC manifests in git / `kubectl get clusterroles -o yaml`:
  ```bash
  # wildcards in cluster roles
  kubectl get clusterroles -o json | jq -r '.items[]|select(.rules[]?|(.verbs[]?=="*") or (.resources[]?=="*"))|.metadata.name'
  # escalation verbs anywhere
  grep -rE 'escalate|impersonate|"bind"' rbac/
  # cluster-admin bound to a ServiceAccount or broad group
  kubectl get clusterrolebindings -o json | jq -r '.items[]|select(.roleRef.name=="cluster-admin")|{name:.metadata.name,subjects:.subjects}'
  ```
- **Find dead subjects**: bindings to departed users / deleted SAs accrue silently — Low,
  but they're attack surface and noise. Reconcile against the identity source.

## Audit checklist

- [ ] No wildcard `*` verbs/resources/apiGroups in any Role/ClusterRole bound to a workload, CI, or tenant? (`kubectl get clusterroles,roles -A -o json | jq` for `"*"`)
- [ ] `escalate`/`bind`/`impersonate` granted only to a named, audited admin path — never automation? (`kubectl who-can escalate clusterroles`, etc.)
- [ ] No `cluster-admin` (or any broad role) bound to a ServiceAccount, `system:authenticated`, or `system:unauthenticated`? (`kubectl get clusterrolebindings -o json | jq '...roleRef.name=="cluster-admin"'`)
- [ ] Aggregated ClusterRoles reviewed — nothing unexpected aggregates into `admin`/`edit`/`view`?
- [ ] Broad `secrets` read, `pods` create, `serviceaccounts/token` create, and policy-engine CRD writes (`rules/03`) scoped tightly (treated as escalation primitives)?
- [ ] `automountServiceAccountToken: false` is the default; only API-calling pods opt in? (`grep -rL automountServiceAccountToken` deployments; check SA spec)
- [ ] No manually-created long-lived `service-account-token` Secrets; external consumers use short-lived audience-scoped TokenRequest tokens?
- [ ] One SA per workload, `default` SA unused/unbound, no SA shared across apps?
- [ ] who-can run on every escalation primitive and the transitive closure for high-value SAs reviewed?
- [ ] Bindings reconciled against the identity source — no dead users/SAs?
