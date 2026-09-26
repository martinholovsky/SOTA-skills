# 01 — Control Plane, etcd & Node/Distro Hardening

Scope: the cluster's brain — HA control plane, API server and kubelet hardening, etcd
encryption/backup/restore, node and immutable-distro hardening (Talos, k3s/k0s), version
skew and CVE response. Frame against the **CIS Kubernetes Benchmark** (CIS listed v2.0.1
as latest on 2026-09-25; use the edition matched to your minor version) and the **NSA/CISA Kubernetes Hardening Guidance** (v1.2,
Aug 2022 — still the current edition; verify before citing). On managed clusters
(EKS/GKE/AKS) the provider owns the control plane and etcd — you cannot set these flags;
audit the *managed equivalents* (provider security posture, control-plane logging,
secrets-encryption setting) and focus your effort on RBAC, admission, and nodes.

---

## 1. HA control plane

- **Three (or five) control-plane nodes** across failure domains; etcd quorum needs an
  odd count. Two nodes is *worse* than one (split-brain risk, no quorum gain).
- **API server behind a load balancer**; control-plane components talk to it via a stable
  endpoint, not a single node IP.
- **etcd: stacked vs external.** Stacked (etcd co-located with control plane) is simpler
  and fine for most; external etcd isolates blast radius and is preferred for large or
  high-security clusters. Either way etcd is the crown jewel — everything below applies.
- Control-plane nodes run **no workloads** (taint `node-role.kubernetes.io/control-plane:
  NoSchedule`). A tenant pod on a control-plane node is a node-escape away from etcd.

## 2. API server hardening

These are kube-apiserver flags (or managed-cluster equivalents). Each is a CIS control.

| Setting | Required value | Why |
|---|---|---|
| `--anonymous-auth` | `false` | Anonymous requests hit RBAC as `system:anonymous`/`system:unauthenticated`; combined with any loose binding = unauthenticated access. **Critical if true.** |
| `--authorization-mode` | `Node,RBAC` (never includes `AlwaysAllow`) | `AlwaysAllow` disables authz entirely. `Node` authorizer + `RBAC` is the baseline. |
| `--enable-admission-plugins` | includes `NodeRestriction` | Stops a compromised kubelet from editing other nodes/pods or escalating via node labels. |
| `--audit-policy-file` / `--audit-log-path` | set (see `rules/07`) | No audit log = no forensics, no detection. |
| `--encryption-provider-config` | set with KMS v2 (see §4) | Secrets at rest. |
| `--service-account-lookup` | `true` | Revoked SA tokens stop working. |
| `--tls-min-version` | `VersionTLS12`+ ; strong cipher suites | Defense in depth on the API. |
| `--profiling` | `false` in prod | `/debug/pprof` leaks data and is a DoS vector. |
| `--request-timeout`, `--max-requests-inflight` | tuned | API server DoS resistance. |
| `--enable-priority-and-fairness` | `true` (the default) | API Priority & Fairness — never set `false`. |

**API Priority & Fairness (APF)** is stable since v1.29 and **on by default**; it
supersedes the raw `--max-requests-inflight` limits by splitting that total
concurrency across priority levels via `FlowSchema` + `PriorityLevelConfiguration`,
with fair queuing so one runaway controller can't starve `leader-election` or
node heartbeats. Audit: confirm it isn't disabled (`--enable-priority-and-fairness=false`
is a finding), give a dedicated `PriorityLevelConfiguration` to high-value
controllers, and alert on `apiserver_flowcontrol_rejected_requests_total`. A
catch-all FlowSchema that lumps everything into one level re-creates the global-limit
DoS APF exists to prevent.

**Authentication**: prefer **OIDC** for human users (RBAC-design and SSO are
`sota-identity-access` territory — wire it there). Never distribute the cluster-admin
kubeconfig / client cert as the day-to-day human credential; client certs cannot be
revoked short of CA rotation. Service-to-API auth uses ServiceAccount tokens (`rules/02`).
**Every human session against the API is privileged access**, whatever role it maps to, so it goes through the IdP (OIDC, the
managed provider's IAM integration, or an authenticating proxy using impersonation) with
**phishing-resistant MFA enforced at the IdP**, and the kubeconfig carries an `exec`
credential plugin, not a pasted bearer. **Never hand a person a ServiceAccount token as a
login**: Kubernetes defines a ServiceAccount as a non-human identity for workloads and
automation; a token minted for "alice-admin" has no MFA, no IdP offboarding, and audit
logs name the SA, not the person. A kubeconfig `user.token`/`tokenFile` entry held by a
human is the finding. OWASP: Kubernetes Security cheat sheet.

**Cluster web UIs are human sessions too.** The upstream Kubernetes Dashboard repository
was archived in January 2026 (its README now points to Headlamp, under kubernetes-sigs), so
a deployed Dashboard is an unmaintained component: plan its removal under §7. Whatever UI
you keep, three rules make it safe to reach:
- **Per-user identity, never a shared UI identity.** The UI calls the API *as the person*:
  its own OIDC login (Headlamp supports one) or an authenticating proxy that sends the
  user's token on every request (Dashboard honours `Authorization: Bearer <token>` for this,
  and the header is lost if the UI is reached through the API-server proxy). RBAC and the
  audit log then see alice, not a ServiceAccount everyone borrows. The UI's own
  ServiceAccount holds nothing users can act through, and nobody logs in by pasting an SA token.
- **MFA at the front door.** The proxy or the IdP behind the UI login enforces
  phishing-resistant MFA, as for any other human API session above.
- **Only the proxy can reach it.** A NetworkPolicy admits ingress to the UI pods from the
  proxy's pods alone, so a compromised pod elsewhere in the cluster cannot call the UI
  directly and skip authentication (policy depth: `sota-network-security`).
OWASP: Kubernetes Security cheat sheet.

```yaml
# BAD — kube-apiserver manifest fragments that are Critical/High findings
- --anonymous-auth=true
- --authorization-mode=AlwaysAllow
- --insecure-port=8080            # removed in modern K8s; if present, you're ancient
- --token-auth-file=/etc/tokens   # static token files are unrevocable plaintext creds
```

## 3. Kubelet hardening

The kubelet is a root-capable agent on every node with its own API. Harden it explicitly
— defaults have historically been loose.

| Setting | Required value | Why |
|---|---|---|
| `anonymous.enabled` (`--anonymous-auth`) | `false` | An open kubelet API = run any pod, read any Secret mounted on the node, exec into containers. **Critical if anonymous.** |
| `authorization.mode` (`--authorization-mode`) | `Webhook` | `AlwaysAllow` lets any authenticated client drive the kubelet. |
| `readOnlyPort` (`--read-only-port`) | `0` | The read-only port (10255) exposes pod/node metadata unauthenticated. |
| `--rotate-certificates`, `serverTLSBootstrap` | `true` | Short-lived, rotated kubelet certs. |
| `protectKernelDefaults` | `true` | Kubelet refuses unsafe sysctls. |
| `streamingConnectionIdleTimeout` | non-zero | Reaps idle exec/attach streams. |
| `makeIPTablesUtilChains` | `true` | Expected networking baseline. |

Hunt: `curl -sk https://NODE:10250/pods` returning data without a token is a Critical
finding (anonymous kubelet). `curl http://NODE:10255/pods` returning data means the
read-only port is open.

## 4. etcd security — "Secrets are base64, not encrypted"

**The reality:** by default Kubernetes stores Secret objects in etcd as **base64-encoded
plaintext**. Anyone who reads etcd (etcd client access, an etcd backup file, a disk image,
a node with the data dir) reads every Secret in the cluster. Base64 is encoding, not
encryption.

**Encrypt at rest with a KMS v2 provider** (GA since Kubernetes v1.29; KMS v1 deprecated
v1.28, disabled-by-default v1.29 — do not build on v1). KMS v2 does envelope encryption: a
local DEK encrypts data, a remote KMS KEK wraps the DEK, and v2 derives single-use DEKs
from a rotated seed for performance.

```yaml
# EncryptionConfiguration — KMS v2 first, so Secrets get the strong provider
apiVersion: apiserver.config.k8s.io/v1
kind: EncryptionConfiguration
resources:
  - resources: ["secrets"]
    providers:
      - kms:
          apiVersion: v2
          name: cloud-kms
          endpoint: unix:///run/kmsplugin/socket.sock
      - identity: {}        # fallback for reads of not-yet-rewritten data; never first
```

```yaml
# BAD — identity first means everything is written in plaintext
providers:
  - identity: {}
  - aescbc: { keys: [...] }   # also: aescbc is weaker than aesgcm/KMS; local key on disk
```

- The **provider listed first encrypts** new writes. `identity` must never be first.
- After enabling/rotating, **rewrite all Secrets** so existing data is re-encrypted:
  `kubectl get secrets -A -o json | kubectl replace -f -`.
- On managed clusters, enable the provider's secrets-encryption feature (e.g. EKS KMS
  envelope encryption, GKE Application-layer Secrets Encryption, AKS KMS etcd encryption).
- **etcd transport**: peer and client TLS with cert auth (`--client-cert-auth=true`,
  `--peer-client-cert-auth=true`); etcd reachable only from control-plane nodes, never
  exposed to the pod network or internet.
- **Only the API server touches the Kubernetes keyspace.** With `--client-cert-auth=true`
  etcd accepts *any* client certificate its `--trusted-ca-file` signed, so that CA is used
  for etcd alone (kubeadm generates a separate `etcd-ca` for exactly this; a CIS Kubernetes
  Benchmark check asks for a unique etcd CA) — sign etcd clients with the cluster CA and
  every kubelet cert becomes an etcd login. A component that wants etcd for its own state
  (a CNI or policy engine in etcd-datastore mode, for instance) gets its **own etcd
  cluster**; if it must share, turn on etcd auth (`etcdctl auth enable` — until then every
  trusted cert has full access) and give it a user whose role covers only its prefix
  (`etcdctl role grant-permission <role> --prefix=true readwrite /<component>/`), never
  `/registry/` (the API server's default `--etcd-prefix`, where every Secret lives) and
  never a copy of the API server's `apiserver-etcd-client` certificate. etcd's `/metrics`
  and `/health` endpoints sit outside its RBAC, so they still need network restriction.
  OWASP: Kubernetes Security cheat sheet.

### etcd backup, defrag, restore — TESTED

- **Scheduled `etcdctl snapshot save`** (or managed backup), stored **off-cluster** in a
  separate trust domain, encrypted, immutable, not deletable by cluster credentials.
- A backup of an *encrypted* etcd needs the KMS KEK to restore — back up your key access /
  document the KEK recovery, or the snapshot is unrestorable.
- **Periodic defrag** (`etcdctl defrag`) — fragmented etcd causes `mvcc: database space
  exceeded` and a hard API-server outage. Alert on etcd DB size approaching `--quota-
  backend-bytes`.
- **Restore drills**: an untested backup is a hope. Drill restore-into-a-throwaway-cluster
  on a schedule; record RTO. Cross-link DR posture with `sota-cloud-infrastructure`
  rules/07.

## 5. Node hardening

- **Minimal, hardened OS**; CIS-bench the nodes; auto-patch or immutable-rebuild.
- **Write down the CIS target level.** CIS benchmarks split recommendations into Level 1
  (baseline, little operational cost) and Level 2 (defense in depth for high-security
  environments, may break things if applied blindly). Target the CIS Kubernetes Benchmark
  **Level 1 as the floor** plus the Level 2 controls your risk justifies, recorded as a
  list with reasons, and apply the host OS's own CIS benchmark to the node image. Run
  kube-bench with the profile matching your platform (it ships EKS, GKE, AKS, k3s, RKE2 and
  OpenShift variants besides the generic `cis-*` ones), not the generic one against a
  managed cluster. Standalone Docker hosts outside Kubernetes (build agents, legacy
  single-host services) get the CIS Docker Benchmark instead, e.g. Docker Bench for
  Security (container hardening depth: `sota-sandboxing` rules/03). OWASP: DSOMM; Docker
  Security cheat sheet.
- **No SSH to nodes as a routine workflow** — node access is break-glass, audited.
- Container runtime hardened (containerd with sane defaults); no Docker socket on nodes.
- Pod-level isolation (seccomp/AppArmor/securityContext, runtime class gVisor/Kata) is
  **`sota-sandboxing`** (rules/03) — enforce it via admission (`rules/03`), don't re-spec
  it here.
- Protect node metadata endpoints: block pod access to the cloud metadata service
  (169.254.169.254) unless via workload identity — see `sota-cloud-infrastructure`
  rules/02 and `sota-network-security`.

## 6. Immutable distros (e.g. Talos, including on ARM)

**Talos Linux** — API-driven, immutable, minimal Linux purpose-built for K8s:
- **No SSH, no shell, no package manager, no interactive login.** The entire node is
  managed via the gRPC `talosctl` API (mTLS-authenticated). This removes the single
  biggest node-attack surface: there is no interactive foothold to gain.
- **Machine config is the security boundary.** Treat `machineconfig` like a Secret: it
  holds the cluster CA and join material. Store it encrypted, deliver via a trusted
  channel, and scope `talosconfig` credentials (the client cert) tightly — it is
  root-equivalent on the node.
- **SecureBoot + TPM disk encryption.** Modern Talos (systemd-boot + Unified Kernel Image
  is the default for new UEFI installs since v1.10) supports SecureBoot; combine with
  **LUKS2 disk encryption keyed to the TPM** (`machine.systemDiskEncryption`) for measured
  boot and at-rest disk protection. On ARM, confirm board/firmware SecureBoot + TPM 2.0
  support before relying on it; where TPM is unavailable, use a `nodeID` or KMS key source
  and document the weaker guarantee.
- **KubePrism / API access**: restrict the Talos API and Kubernetes API endpoints to
  management networks; the Talos API at :50000 is as sensitive as the kube-apiserver.
- Apply config changes via versioned, reviewed `talosctl apply-config` from git — Talos
  config is GitOps-able; treat it like the rest of `rules/04`.

```yaml
# Talos machine config fragment — TPM-bound disk encryption (verify slot/keys per version)
machine:
  systemDiskEncryption:
    state:     { provider: luks2, keys: [{ tpm: {}, slot: 0 }] }
    ephemeral: { provider: luks2, keys: [{ tpm: {}, slot: 0 }] }
```

**k3s / k0s** (lightweight self-hosted):
- k3s ships SQLite by default for single-server; use **embedded etcd (HA)** or an external
  datastore for multi-server, and apply the same etcd encryption discipline (§4) — k3s
  supports `--secrets-encryption` to enable at-rest encryption.
- k3s bundles components; pin the version, track its CVE feed, and disable bundled add-ons
  you don't use (`--disable traefik,servicelb` etc.) to shrink surface.
- k0s separates controller/worker cleanly; harden the same API-server/kubelet flags (§2,
  §3) via its config. Both still need RBAC/admission/audit from the other rules files.

## 7. Version skew, EOL & CVE response

- **Supported window**: the project maintains the **latest three minor releases**, each
  with ~1 year of patch support. Run a supported minor; an EOL control plane gets no CVE
  fixes. (Verify the supported minors at kubernetes.io/releases.)
- **Version skew policy** (since 1.28): the **control plane may be up to 3 minor versions
  ahead of kubelets**; kube-apiserver instances within ≤1 minor of each other; kubectl
  within ±1 of the API server. Upgrade control plane first, then nodes — never the reverse.
- **Upgrade cadence**: minor releases ~3×/year. Plan a rolling upgrade every 1–2 minors;
  don't fall to EOL. On managed clusters, stay on a supported channel and don't defer past
  the provider's forced-upgrade date.
- **CVE response runbook**: subscribe to the `kubernetes-announce` list / CVE feed; for a
  control-plane RCE or auth-bypass, patch on the emergency track, not the quarterly one.
  Track CVEs for *every* control too: Argo CD (`rules/04`), Kyverno/Gatekeeper (`rules/03`),
  operators (`rules/05`), **ingress controllers and CSI drivers** (the official feed's 2026
  wave hit both — ingress-nginx config-injection/auth-bypass/DoS CVE-2026-24512/-24513/
  -24514/-1580/-3288/-4342; CSI SMB/NFS subDir path traversal CVE-2026-3864/-3865), and
  the distro (Talos/k3s/k0s).
- **ingress-nginx is EOL** (retired by SIG Network/SRC; maintenance ended March 2026, repo
  read-only). The 2026 CVE wave *was* patched in the final releases (>=1.13.9/1.14.5/1.15.1);
  the standing risk is that any CVE found after EOL gets **no** fix. A deployed ingress-nginx is a
  standing High finding: migrate to Gateway API or an actively maintained ingress
  controller (ingress/edge config depth is `sota-network-security`).

## Audit checklist

- [ ] API server: `--anonymous-auth=false`, `--authorization-mode` includes RBAC and not `AlwaysAllow`, `NodeRestriction` enabled, profiling off, audit configured? (`grep -E 'anonymous-auth|authorization-mode|NodeRestriction|profiling' /etc/kubernetes/manifests/kube-apiserver.yaml`; managed → check provider posture)
- [ ] API Priority & Fairness left enabled (no `--enable-priority-and-fairness=false`), high-value controllers on a dedicated `PriorityLevelConfiguration`, `apiserver_flowcontrol_rejected_requests_total` alerted?
- [ ] Human API access via IdP (OIDC / provider IAM / impersonating proxy) with phishing-resistant MFA, and no person logging in with a static bearer or ServiceAccount token? **High** if an SA token is a human's login. (`grep -rnE '^ +token(File)?: ' ~/.kube/ <distributed-kubeconfigs>` — each hit is a static bearer, expect `exec:` instead; `grep -rnE 'kubectl create token|kubernetes\.io/service-account-token' <runbooks> <onboarding> <manifests>` — each hit: who receives that token, a workload or a person?)
- [ ] Kubernetes Dashboard: not deployed unless required; if deployed, NOT exposed publicly (no LoadBalancer/Ingress to it), reached only via `kubectl proxy`/authenticating proxy, and its ServiceAccount is least-privilege (never `cluster-admin`) — a privileged, exposed Dashboard is a one-click takeover (historic Tesla cryptojacking). Talos does not ship it; keep it that way. **Medium** for any deployed Dashboard (upstream archived January 2026; `grep -rnE 'kubernetesui/dashboard|kubernetes-dashboard' <manifests> <helm-values> <argocd-apps>` — each hit is the archived UI); **High** if any cluster UI acts through a shared ServiceAccount instead of the user's own token, has no MFA in front, or has no NetworkPolicy limiting its ingress to the proxy (`kubectl get networkpolicy -n <ui-namespace> -o yaml`, expect a `podSelector` on the UI pods with `ingress.from` naming only the proxy).
- [ ] Kubelet: anonymous-auth off, authz `Webhook`, `read-only-port=0`? (`curl -sk https://NODE:10250/pods` should 401; `curl http://NODE:10255/pods` should refuse)
- [ ] etcd encrypted at rest with KMS v2, `identity` not first, all existing Secrets rewritten? (`kubectl get secret -A -o json | head` against an etcd dump; check `EncryptionConfiguration`)
- [ ] etcd reachable only from control plane, client/peer TLS cert-auth on? (`etcdctl` from a worker should fail)
- [ ] Kubernetes etcd keyspace reachable by the API server alone: dedicated etcd CA, no other component holding the API server's etcd client cert, any co-tenant component on its own etcd or on an auth-enabled user limited to its own prefix? **High** if a non-API-server component can read `/registry/`. (`grep -rnE 'apiserver-etcd-client' <manifests> <cni-and-addon-configs> | grep -v 'kube-apiserver'` — each hit is another component using the API server's etcd identity; `etcdctl auth status` on a shared etcd should report enabled)
- [ ] etcd backups scheduled, off-cluster, immutable, restore-DRILLED, KEK recoverable? (when was the last restore drill?)
- [ ] etcd defrag scheduled and DB-size alerting wired?
- [ ] Control-plane nodes tainted to run no workloads?
- [ ] Nodes: minimal/hardened OS, kube-bench passing (platform-matched profile), no routine SSH? CIS target recorded — Kubernetes Level 1 floor, chosen Level 2 controls listed, host-OS CIS benchmark on the node image, standalone Docker hosts audited with the CIS Docker Benchmark (e.g. Docker Bench for Security)? **Medium** if no target level is written down or a managed cluster is scored with the generic profile. Talos: SecureBoot + TPM/LUKS2 disk encryption, machineconfig/talosconfig stored as secrets and scoped? k3s/k0s: `--secrets-encryption` on, unused add-ons disabled?
- [ ] Running a SUPPORTED minor (not EOL)? Skew within policy (control plane ≥ nodes, ≤3 minors)? (`kubectl version`, `kubectl get nodes -o wide`)
- [ ] CVE-response runbook exists and covers control plane + every add-on/controller + ingress/CSI + distro?
- [ ] No EOL ingress-nginx still deployed (retired March 2026 — final releases patched the 2026 CVE wave, but any post-EOL CVE is unpatched — High; migration to Gateway API or a maintained controller done or dated)?
