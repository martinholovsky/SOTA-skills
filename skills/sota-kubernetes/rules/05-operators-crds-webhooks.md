# 05 — Operators, CRDs & Admission Webhooks

Scope: extension components that run with cluster privilege — operators (controllers
reconciling CRDs), the CRDs themselves, and admission webhooks (validating/mutating). These
are the third-party code you grant standing power inside the cluster; each is both a
control and an attack surface. Trusted-controller examples: ExternalSecrets Operator (ESO),
cert-manager. Secret *backends/ESO usage* is `sota-secrets-management` (rules/02); this
file owns *vetting the operator's cluster privilege and webhook surface*.

---

## 1. The operator privilege problem

An operator is a long-running controller with a ServiceAccount that, by design, holds broad
RBAC: it watches and mutates the resources it manages, often cluster-wide, often including
**Secrets, RBAC objects, or pods**. That makes every installed operator a standing,
privileged principal — and **CRD-mediated escalation** the recurring risk:

- The operator reads a CRD (a custom resource you or a tenant created) and *acts* with its
  own (broad) privileges. So **anyone who can create/edit that CRD can often induce the
  operator to do something privileged on their behalf** — a confused-deputy. Example: a
  CRD field that becomes a pod's `serviceAccountName`, `hostPath` mount, image, or RBAC
  binding lets a CRD-author escalate via the operator's hands.
- An operator with `clusterroles`/`clusterrolebindings` write, or `secrets` cluster-wide,
  or `pods` create with arbitrary SA, is effectively cluster-admin-adjacent. Owning the
  operator pod (its image, its dependencies, an RCE) = owning that power.

**Mitigations:**
- **Vet the operator's RBAC before install.** `helm template` / read the bundled
  ClusterRole (`rules/07`, `rules/02`). Reject or scope wildcard verbs, cluster-wide
  `secrets:*`, and RBAC-write unless the operator genuinely needs them. Prefer
  **namespaced-scoped operators** (watch one/few namespaces via OLM `OperatorGroup` or the
  operator's `--namespace` flag) over cluster-wide where the operator supports it.
- **Limit who can create the operator's CRs.** RBAC on the CRD's API group is an
  escalation primitive — treat `create`/`update` on a CRD whose fields drive pods/RBAC/
  secrets like `pods` create (`rules/02` §2.5). Don't hand tenants CR-create on a CRD the
  operator turns into privileged actions.
- **Pin and patch the operator** like any privileged software (image digest, CVE feed).
- **Watch what the operator mutates**: an operator that injects sidecars or modifies pod
  specs is doing admission-time mutation — audit it like a mutating webhook (§3).

Trusted, widely-used operators still need scoping: **ESO** holds creds to your secret
backend and writes Secrets — scope its `SecretStore`/`ClusterSecretStore` and the
namespaces it serves; **cert-manager** can issue certs and holds issuer credentials —
scope `ClusterIssuer` usage and ACME/CA access. "Popular" is not "harmless when
over-privileged."

## 2. CRD validation & security

CRDs extend the API; a sloppy CRD is an injection and DoS vector into the operator.
- **Structural schema with strict validation.** Define `openAPIV3Schema` with types,
  enums, patterns, and `x-kubernetes-validations` (CEL) for cross-field rules. A CRD that
  accepts arbitrary fields (`x-kubernetes-preserve-unknown-fields: true`) lets attackers
  smuggle data the operator may mishandle — avoid except where genuinely needed.
- **Validate fields that become privileged.** If a CR field becomes a container image, an
  SA name, a host path, a command, or an RBAC subject, the CRD schema (and/or an admission
  policy) must constrain it — don't trust the operator to sanitize.
- **CRD scope**: cluster-scoped CRDs are visible/creatable per cluster-wide RBAC;
  namespaced CRDs are easier to delegate safely. Prefer namespaced unless the resource is
  genuinely global.
- **Conversion webhooks** (for multi-version CRDs) are admission-webhook-class surface —
  same hardening as §3.
- Removing/replacing a CRD with `deletionPolicy` implications can cascade-delete CRs and
  the operator-managed resources — review before applying CRD changes via GitOps.

## 3. Admission webhooks as attack surface AND single point of failure

Validating/mutating webhooks are external HTTPS endpoints the API server calls on every
matching request. They are powerful (they can reject or rewrite any object) and fragile (if
they're down or misconfigured, they can wedge the cluster). Configure deliberately:

```yaml
# Knobs that matter on a (Validating|Mutating)WebhookConfiguration
webhooks:
  - name: policy.example.com
    failurePolicy: Fail            # Fail = secure (reject if webhook down) for SECURITY gates
                                   # Ignore = available (allow if down) — only for non-security mutators
    timeoutSeconds: 5              # short; a slow/hung webhook stalls every API write
    namespaceSelector:             # EXCLUDE kube-system / the webhook's own ns to avoid deadlock
      matchExpressions:
        - { key: kubernetes.io/metadata.name, operator: NotIn, values: ["kube-system","webhook-system"] }
    matchPolicy: Equivalent
    sideEffects: None
    admissionReviewVersions: ["v1"]
    clientConfig:
      caBundle: <pinned CA>        # TLS verified; rotate before expiry
```

The hard tradeoffs and traps:
- **`failurePolicy`**: `Fail` is correct for **security** webhooks (an unavailable policy
  engine must not mean "allow everything") — but a `Fail` webhook that covers its own
  namespace or kube-system can **deadlock the cluster** (you can't restart the webhook
  because admission needs the webhook). Always set a `namespaceSelector`/`objectSelector`
  that **excludes the webhook's own namespace and kube-system**. Run the webhook HA
  (multiple replicas, PDB — `rules/06`) so `Fail` doesn't take you down on a single pod
  restart. Non-security convenience mutators may use `Ignore`, but know that means
  fail-open.
- **`timeoutSeconds`**: keep it small (≤5–10s). Every matching API write blocks on the
  webhook; a hung webhook is a cluster-wide write outage.
- **TLS**: the `caBundle` must be valid and **rotated before expiry** — an expired webhook
  cert with `failurePolicy: Fail` is a self-inflicted outage; with `Ignore` it silently
  disables your control. Use cert-manager (and its CA-injector) to manage and rotate
  webhook certs; alert on cert expiry.
- **Scope (`rules`/`namespaceSelector`/`objectSelector`)**: match only what you must. An
  over-broad webhook intercepting every resource is latency + blast radius. A *malicious or
  compromised* webhook scoped to `pods`/`*` can read every spec (data exfil) and a mutating
  one can inject sidecars, hostPath mounts, or credentials into every pod — so **who can
  create/edit WebhookConfigurations is an escalation primitive** (it's cluster-wide RBAC;
  guard `admissionregistration.k8s.io` writes like RBAC writes, `rules/02`).
- Prefer **in-tree CEL policies (ValidatingAdmissionPolicy)** over a webhook where the
  logic fits (`rules/03` §2) — no external endpoint means no webhook outage/attack surface.

## Audit checklist

- [ ] Every installed operator's RBAC reviewed; no unjustified wildcard verbs, cluster-wide `secrets:*`, RBAC-write, or `pods` create with arbitrary SA? (`kubectl get clusterrole -o yaml` for each operator SA; trace its ClusterRoleBinding)
- [ ] Operators run namespaced-scoped where supported, not cluster-wide by default?
- [ ] RBAC to create/edit operator CRDs is restricted (treated as an escalation primitive when the CRD drives pods/RBAC/secrets)?
- [ ] CRDs have structural schemas with validation (`x-kubernetes-validations`), no needless `preserve-unknown-fields`; privileged-becoming fields constrained?
- [ ] Trusted controllers (ESO, cert-manager) scoped — SecretStore/Issuer usage and served namespaces limited, backend creds tight?
- [ ] Operators pinned by digest and on a tracked CVE/patch cadence?
- [ ] Security webhooks `failurePolicy: Fail` BUT with `namespaceSelector` excluding kube-system and the webhook's own ns; webhook runs HA + PDB?
- [ ] Webhook `timeoutSeconds` small; webhook scope (`rules`/selectors) minimal, not `*`?
- [ ] Webhook TLS `caBundle` valid, managed by cert-manager, rotated before expiry, expiry-alerted?
- [ ] Writes to `admissionregistration.k8s.io` (WebhookConfigurations) guarded like RBAC writes? (`kubectl auth can-i create validatingwebhookconfigurations --as=<subject>` per subject; reverse index via krane — `rules/02` §4)
- [ ] Logic that fits CEL moved to ValidatingAdmissionPolicy instead of a webhook where practical?
