# 07 — Helm/Kustomize Supply Chain & K8s Audit Logging

Scope: two platform concerns the other files lean on — (a) reviewing what a chart/overlay
actually applies before it hits the cluster, plus chart/image provenance enforced **at
admission**; and (b) producing and shipping the Kubernetes API audit log. Image *signing
production* and *CI provenance* are `sota-devsecops` (rules/02, rules/04); admission
*verification mechanics* are `rules/03`; **detection content on the audit stream and
runtime detection (Falco/Tetragon) are `sota-detection-engineering`** — this file owns
*generating and shipping* the stream, not writing the detections.

---

## 1. `helm template` review before apply

A Helm chart is arbitrary templated YAML that becomes live cluster objects. Treat
installing a third-party chart like running third-party code with the controller's
privileges. **Always render and review before apply** — never `helm install` an unread
chart into a privileged cluster:

```bash
helm template rel chart/ -f values.yaml > rendered.yaml
# what RBAC does this chart grant?
grep -nE 'kind:\s*(ClusterRole|ClusterRoleBinding|Role|RoleBinding)' rendered.yaml
# privilege-granting values / specs (last alternative: a wildcard quoted "*" or '*')
grep -nE "privileged:\s*true|hostPID|hostNetwork|hostPath|cluster-admin|automountServiceAccountToken:\s*true|[\"']\*[\"']" rendered.yaml
# images and tags (are they pinned? from your registry?)
grep -nE 'image:' rendered.yaml
```

Then diff against the running state (`helm diff upgrade`, or render-and-`kubectl diff`) so
an upgrade can't silently widen privileges. In GitOps (`rules/04`), the rendered output is
what the controller applies — review the chart version bump like code.

## 2. The RBAC-in-charts / privilege-values trap

(Cross-ref `rules/02` §2.6.) Charts ship their own RBAC and expose values that grant
privilege. The recurring traps:
- **`rbac.create: true` paired with a `*/*` ClusterRole**, or a values toggle like
  `rbac.clusterAdministrator: true` / `clusterRole.rules: [{apiGroups:["*"],...}]` — the
  chart hands its ServiceAccount the cluster. A logging/monitoring agent that "needs to see
  everything" rarely needs *write* on everything; scope it.
- **`securityContext`/`podSecurityContext` values defaulting to root/privileged**, or
  `hostNetwork`/`hostPID`/`hostPath` toggles. Override to non-root, no host namespaces;
  admission (`rules/03`) should reject these anyway — if the chart can't deploy under PSA
  `restricted`, that's a signal.
- **`serviceAccount.create` + a powerful binding** — confirm the SA it creates isn't bound
  to a built-in `admin`/`cluster-admin` role.
- **Operators bundled in charts** — apply `rules/05` (vet the operator RBAC and CRDs).

Don't disable your own admission policies to make a chart install. If a vendor chart
demands cluster-admin or privileged pods, push back, scope it, or sandbox it — vendor
convenience is not a risk acceptance.

## 3. Chart & image provenance — enforced at admission

- **Sign and verify Helm charts.** OCI-registry charts can be **cosign-signed**; verify the
  signature/provenance before install (`cosign verify --certificate-identity <signer> --certificate-oidc-issuer <issuer> <oci-chart-ref>` for keyless, or `--key <pub>`: without an identity cosign refuses a keyless verify, and pinning the signer is the point), and pin the chart
  by **digest**, not a mutable version tag, in your GitOps source. An unsigned chart pulled
  by floating version is mutable supply-chain surface.
- **Only-signed-images enforcement** is the admission control from `rules/03` §4 — the
  manifests a chart produces must reference images that pass signature/provenance
  verification (Kyverno `ImageValidatingPolicy` / sigstore policy-controller). Signing without admission
  enforcement is theater (`sota-devsecops` rules/02 produces the signatures; this is where
  they're checked).
- **Digest-pin images at the manifest layer.** Deploy manifests reference
  `image@sha256:<digest>` (or a signed tag your admission policy mutates to a verified
  digest), never `:latest` or a floating tag — build-once-promote-many
  (`sota-devsecops` rules/06). Mutable tags admit a different artifact than you reviewed.
- **Kustomize**: pin `images:` with `digest:`; review `patches`/`patchesStrategicMerge`
  for privilege escalation the same way (a patch can add `privileged: true` or a hostPath);
  beware remote bases (`resources:` pointing at a URL) — pin and review them like remote
  charts.

## 4. Kubernetes API audit logging — produce the stream

The API server audit log is the authoritative record of *who did what to the cluster* —
the basis for forensics and the detections in `sota-detection-engineering`. Without it, a
cluster compromise is uninvestigable. (On managed clusters, enable the provider's
control-plane audit logging — you configure the policy via the provider, e.g. EKS audit
logs to CloudWatch, GKE audit logs to Cloud Logging, AKS to the diagnostic settings.)

**Audit levels** (per rule, least→most): `None` → `Metadata` (who/what/when, no bodies) →
`Request` (+ request body) → `RequestResponse` (+ response body). Tune per sensitivity —
log everything at `Metadata`, escalate sensitive verbs/resources to `RequestResponse`, and
drop noise (read-only system loops) to `None`.

```yaml
# audit-policy.yaml — log sensitive things richly, drop noise, default to Metadata
apiVersion: audit.k8s.io/v1
kind: Policy
omitStages: ["RequestReceived"]
rules:
  # Secrets/configmaps: log requests but DON'T capture bodies (would log secret values)
  - level: Metadata
    resources: [{ group: "", resources: ["secrets","configmaps"] }]
  # RBAC and admission changes: full bodies — these are escalation actions
  - level: RequestResponse
    resources:
      - { group: "rbac.authorization.k8s.io", resources: ["*"] }
      - { group: "admissionregistration.k8s.io", resources: ["*"] }
  # exec/attach/portforward into pods: high-signal, log them
  - level: Request
    resources: [{ group: "", resources: ["pods/exec","pods/attach","pods/portforward"] }]
  # drop noisy authenticated read loops from system components
  - level: None
    users: ["system:kube-scheduler","system:kube-controller-manager"]
    verbs: ["get","list","watch"]
  - level: Metadata           # default for everything else
```

Note: **don't log Secret/ConfigMap bodies** (`Request`/`RequestResponse` on `secrets`)
or you write secret values into the audit log — keep them at `Metadata`.

## 5. Ship the stream (tamper-resistant, retained)

- **Forward audit logs off the control-plane node** to tamper-resistant, append-only
  storage in a **separate trust domain** — credentials that can compromise the cluster must
  not be able to delete its audit trail. Retention ≥1 year (align with compliance —
  `sota-privacy-compliance`).
- Pipe to your SIEM / log platform; the **plumbing** is `sota-observability` territory, the
  **detections** (privilege escalation, anonymous access, exec into prod, token abuse,
  policy disable) are `sota-detection-engineering`.
- **Pipeline/controller identities are alertable principals**: an action by the Argo CD SA
  outside a sync, or by a CI SA at an odd time, is a signal.

## 6. Runtime security pointer

Audit logs capture the *API* surface; they don't see in-container behavior (a process that
never calls the API). For runtime detection — anomalous syscalls, unexpected egress,
process execution, container drift — deploy **Falco** or **Tetragon (eBPF)**. Their
deployment-as-privileged-DaemonSet hardening overlaps `sota-sandboxing`, and the
**detection rules/content are `sota-detection-engineering`**. This skill's job is to ensure
the audit-log source exists and is shipped; pair it with runtime detection there.

## Audit checklist

- [ ] Third-party charts rendered (`helm template`) and reviewed for RBAC, privileged/host-* specs, and images BEFORE install; upgrades diffed so privilege can't silently widen?
- [ ] No chart values granting cluster-admin / `*/*` ClusterRole / root-privileged pods accepted unscoped (RBAC-in-charts trap)? Admission policies not disabled to force an install?
- [ ] Charts signed (cosign) and pinned by digest; remote Kustomize bases pinned + reviewed?
- [ ] Images digest-pinned at the manifest layer (no `:latest`/floating tags); only-signed-images enforced at admission (rules/03)?
- [ ] API server audit logging enabled with a tuned policy: Metadata default, RequestResponse on RBAC/admission changes, Request on exec/attach, secrets/configmaps NOT capturing bodies, system read-loops dropped? (`grep -E 'audit-policy-file|audit-log' kube-apiserver.yaml`; managed → provider audit logging on)
- [ ] Audit logs shipped off-node to tamper-resistant, append-only storage in a separate trust domain, retained ≥1y, not deletable by cluster-compromising creds?
- [ ] Audit stream wired to SIEM; controller/CI/automation SAs treated as alertable principals (detections → sota-detection-engineering)?
- [ ] Runtime detection (Falco/Tetragon) deployed to cover in-container behavior the audit log can't see (content → sota-detection-engineering)?
