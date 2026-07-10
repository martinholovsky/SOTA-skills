# 01 — Control Plane, etcd & Node/Distro Hardening

Scope: the cluster's brain — HA control plane, API server and kubelet hardening, etcd
encryption/backup/restore, node and immutable-distro hardening (Talos, k3s/k0s), version
skew and CVE response. Frame against the **CIS Kubernetes Benchmark** (v1.12.0 at writing,
matched to your minor version) and the **NSA/CISA Kubernetes Hardening Guidance** (v1.2,
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
  fixes. (Verify current numbers at kubernetes.io/releases — at writing latest is the 1.36
  line; 1.34/1.35/1.36 supported.)
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
- [ ] Kubernetes Dashboard: not deployed unless required; if deployed, NOT exposed publicly (no LoadBalancer/Ingress to it), reached only via `kubectl proxy`/authenticating proxy, and its ServiceAccount is least-privilege (never `cluster-admin`) — a privileged, exposed Dashboard is a one-click takeover (historic Tesla cryptojacking). Talos does not ship it; keep it that way.
- [ ] Kubelet: anonymous-auth off, authz `Webhook`, `read-only-port=0`? (`curl -sk https://NODE:10250/pods` should 401; `curl http://NODE:10255/pods` should refuse)
- [ ] etcd encrypted at rest with KMS v2, `identity` not first, all existing Secrets rewritten? (`kubectl get secret -A -o json | head` against an etcd dump; check `EncryptionConfiguration`)
- [ ] etcd reachable only from control plane, client/peer TLS cert-auth on? (`etcdctl` from a worker should fail)
- [ ] etcd backups scheduled, off-cluster, immutable, restore-DRILLED, KEK recoverable? (when was the last restore drill?)
- [ ] etcd defrag scheduled and DB-size alerting wired?
- [ ] Control-plane nodes tainted to run no workloads?
- [ ] Nodes: minimal/hardened OS, kube-bench passing, no routine SSH? Talos: SecureBoot + TPM/LUKS2 disk encryption, machineconfig/talosconfig stored as secrets and scoped? k3s/k0s: `--secrets-encryption` on, unused add-ons disabled?
- [ ] Running a SUPPORTED minor (not EOL)? Skew within policy (control plane ≥ nodes, ≤3 minors)? (`kubectl version`, `kubectl get nodes -o wide`)
- [ ] CVE-response runbook exists and covers control plane + every add-on/controller + ingress/CSI + distro?
- [ ] No EOL ingress-nginx still deployed (retired March 2026 — final releases patched the 2026 CVE wave, but any post-EOL CVE is unpatched — High; migration to Gateway API or a maintained controller done or dated)?
