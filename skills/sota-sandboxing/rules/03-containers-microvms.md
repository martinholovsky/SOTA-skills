# 03 — Containers, microVMs & Kubernetes Hardening

Scope: Docker/OCI hardening, when to reach for gVisor/Kata/Firecracker, and
Kubernetes pod/network/runtime security. Assumes `01` boundary choice and `02`
kernel primitives.

---

## 1. Docker / OCI hardening checklist

**R1.1 — Non-root `USER`, numeric, created in the image.** Root-in-container is one
misconfig (or one kernel bug) away from root-on-host.

```dockerfile
# BAD — runs as root, fat base, secrets in layer, latest tag
FROM ubuntu:latest
COPY . /app
RUN apt-get update && apt-get install -y python3 curl wget vim
ENV API_KEY=sk-live-abc123
CMD ["python3", "/app/server.py"]
```

```dockerfile
# GOOD — multi-stage, distroless, pinned by digest, non-root numeric UID
FROM python:3.12-slim@sha256:<digest> AS build
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
COPY . .

FROM gcr.io/distroless/python3-debian12:nonroot@sha256:<digest>
COPY --from=build /install /usr/local
COPY --from=build /app /app
USER 65532:65532
ENTRYPOINT ["python3", "/app/server.py"]
```
Numeric UID matters: K8s `runAsNonRoot` can't verify a string user. Distroless /
Chainguard / scratch images remove the shell, package manager, and most CVE surface —
no shell also kills the easiest post-exploitation step.

**R1.2 — Run flags for anything touching untrusted data:**

```bash
docker run --rm \
  --user 65532:65532 \
  --read-only --tmpfs /tmp:rw,nosuid,nodev,noexec,size=64m \
  --cap-drop=ALL \
  --security-opt no-new-privileges \
  --security-opt seccomp=profile.json \      # custom allowlist; never "unconfined"
  --pids-limit 128 --memory 512m --memory-swap 512m --cpus 0.5 \
  --network none \                            # or a scoped egress network
  image:tag@sha256:<digest>
```

**R1.3 — Absolute prohibitions (each is a Critical/High finding):**
- `--privileged` — disables namespaces' security value, all caps, all devices.
- Mounting `/var/run/docker.sock` (or containerd/CRI socket) — full host control;
  socket-in-container == root-on-host regardless of everything else. If a workload
  "needs Docker," use a remote builder, Kaniko/BuildKit rootless, or a dedicated
  isolated DinD VM — never the host socket.
- `--cap-add=SYS_ADMIN | SYS_PTRACE | BPF | NET_ADMIN(host netns)`,
  `--device` host disks, `--pid=host`, `--net=host`, `--ipc=host`, `--userns=host`
  (when userns remap is on), `--security-opt seccomp=unconfined|apparmor=unconfined`,
  writable `/sys` or `/proc` mounts, host path mounts of `/`, `/etc`, `/root`, `$HOME`.

The same baseline in Compose form (so dev/staging don't silently drop it):

```yaml
services:
  app:
    image: app@sha256:<digest>
    user: "65532:65532"
    read_only: true
    tmpfs: ["/tmp:size=64m,mode=1777,noexec,nosuid,nodev"]
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true", "seccomp=./profile.json"]
    pids_limit: 128
    mem_limit: 512m
    cpus: 0.5
    networks: [backend-only]
    restart: on-failure:3        # crash-loop limiter; a looping exploit attempt
                                 # should not retry forever
```

**R1.4 — Engine-level:** enable user-namespace remap (`"userns-remap"` / rootless
Docker or podman rootless) so container-root maps to an unprivileged host UID;
keep `"no-new-privileges": true` and a default seccomp/AppArmor profile in
`daemon.json`; live-restore on; never expose the Docker API on TCP without mTLS.
The November 2025 runc escape trio (CVE-2025-31133 masked-path symlink race,
CVE-2025-52565 `/dev/console` bind-mount race, CVE-2025-52881 procfs write
redirect; fixed in runc 1.2.8/1.3.3/1.4.0-rc.3) is the concrete proof: user
namespaces block the most serious aspects of all three — userns is the layer
that holds when the runtime itself fails. Verify runc ≥ 1.2.8/1.3.3.

**R1.5 — Supply chain is part of sandbox posture:** pin base images by digest, scan
(grype/trivy) in CI with a severity gate, sign and verify (cosign + policy
controller), generate SBOMs. An attacker who owns your base image is *inside* the
sandbox at boot.

## 2. Sandboxed runtimes: gVisor, Kata, Firecracker

**R2.1 — gVisor (runsc):** user-space kernel (Sentry) intercepts the container's
syscalls; host kernel sees only the Sentry's narrow, seccomp-pinned syscall set.
- Use for: untrusted/multi-tenant containers needing container UX, fast startup,
  high density; CPU/memory overhead modest, **syscall- and I/O-heavy workloads pay
  the most** (mitigated by platforms: KVM platform > ptrace/systrap for perf).
- Not full kernel compatibility — test the workload; failures should push you to
  Kata, not back to runc.
- Drop-in: `runtimeClassName: gvisor` in K8s, `--runtime=runsc` in Docker.

**R2.2 — Kata Containers:** each pod/container in a lightweight VM (QEMU,
Cloud Hypervisor, or Firecracker VMM) with its own guest kernel; OCI/K8s-native.
- Use for: hardware-virtualization isolation with unmodified container images and
  near-full kernel compat; multi-tenant K8s where gVisor compat falls short.
- Cost: needs VT-x/AMD-V (bare metal or nested virt), ~100ms+ startup, per-pod
  memory overhead; host-mounted volumes traverse virtiofs (audit what you share).

**R2.3 — Firecracker:** minimal VMM (microVM), ~125ms boot, <5MiB overhead, jailer-
wrapped (chroot + seccomp + cgroups around the VMM itself), tiny device model
(virtio net/block/vsock only — no PCI passthrough, no GPU).
- Use for: function/job-grade untrusted code execution at scale (Lambda/Fargate
  model), AI-codegen execution sandboxes, anything wanting VM isolation with
  per-request ephemerality. Pair with a snapshot/pool strategy for cold-start.
- You bring the integration (no OCI runtime by itself; use Kata-FC,
  firecracker-containerd, or direct API).

**R2.4 — Selection rule:** runc+hardening for trusted code; gVisor when you need
defense-in-depth at container economics; Kata/Firecracker when tenants are mutually
hostile or code is fully untrusted; Firecracker specifically when you control the
stack and want minimal VMM surface + ephemerality. Re-state: GPU or exotic
device passthrough generally forces Kata(+VFIO) or full VM — and passthrough
*weakens* the boundary (audit it). For agent workloads on K8s, the Kubernetes
**Agent Sandbox** project (SIG Apps, launched KubeCon NA 2025) wraps this choice
in a declarative per-sandbox API with gVisor as default and Kata as the
stronger option — prefer it over hand-rolled per-agent pod plumbing.

## 3. Kubernetes pod security

**R3.1 — Pod Security Standards: enforce `restricted` by namespace label.**
PSP is removed; use Pod Security Admission or a policy engine (Kyverno/Gatekeeper)
for anything finer-grained.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: untrusted-jobs
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/audit: restricted
```

**R3.2 — The securityContext that should be your template default:**

```yaml
spec:
  automountServiceAccountToken: false      # default-on token is a top finding
  hostUsers: false                         # user namespaces — GA in v1.36
  runtimeClassName: gvisor                 # for untrusted workloads
  securityContext:
    runAsNonRoot: true
    runAsUser: 65532
    runAsGroup: 65532
    fsGroup: 65532
    seccompProfile: { type: RuntimeDefault }   # or Localhost + custom profile
  containers:
  - name: app
    image: app@sha256:<digest>
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities: { drop: ["ALL"] }
    resources:
      requests: { cpu: 100m, memory: 128Mi }
      limits:   { cpu: 500m, memory: 512Mi }   # memory limit mandatory
    volumeMounts:
    - { name: tmp, mountPath: /tmp }
  volumes:
  - { name: tmp, emptyDir: { sizeLimit: 64Mi, medium: Memory } }
```
`hostUsers: false` (user namespaces, GA in Kubernetes v1.36) maps container-root
to an unprivileged host UID and namespaces its capabilities — it blocks the R1.4
runc escape class. Needs kernel ≥ 6.3 with idmap-mount support on the pod's
filesystems, runc ≥ 1.2 / crun ≥ 1.9, containerd 2.0+ / CRI-O; require it for
untrusted workloads wherever nodes support it.

**R3.3 — Service account & API surface:** `automountServiceAccountToken: false`
unless the pod calls the API; per-workload service accounts with minimal RBAC (no
`cluster-admin`, no wildcard verbs, beware `pods/exec`, `secrets get/list`,
`create pods` — each is an escalation path). Block cloud metadata
(169.254.169.254) from pods via NetworkPolicy/iptables unless using bound,
audience-scoped identities (IRSA/Workload Identity).

**R3.4 — NetworkPolicy: default-deny both directions, then allowlist.**

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: default-deny, namespace: untrusted-jobs }
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: allow-dns-and-api, namespace: untrusted-jobs }
spec:
  podSelector: { matchLabels: { app: job-runner } }
  policyTypes: [Egress]
  egress:
  - to: [{ namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: kube-system } } }]
    ports: [{ protocol: UDP, port: 53 }, { protocol: TCP, port: 53 }]
  - to: [{ ipBlock: { cidr: 10.0.5.0/24 } }]   # only the approved backend
    ports: [{ protocol: TCP, port: 443 }]
```
A cluster with no NetworkPolicies = flat network = any pod compromise reaches every
service. DNS egress should also be policy-constrained (DNS exfil channel); CNIs like
Cilium can enforce FQDN-level egress (`toFQDNs`) — prefer that for external allowlists.

**R3.5 — Node & scheduling isolation:** untrusted workloads on dedicated node pools
(taints/tolerations + nodeSelector); no hostPath volumes (writable hostPath ≈ node
takeover; even read-only leaks); etcd encrypted at rest; kubelet authn/authz on
(`--anonymous-auth=false`, webhook authz); admission policy rejects R1.3-class specs
cluster-wide (Kyverno `disallow-privileged-containers`, `disallow-host-path`, etc.).

**R3.6 — Secrets:** prefer short-lived, externally-issued credentials (Secrets Store
CSI, Vault agent, cloud workload identity) over long-lived K8s Secrets; mount as
files not env vars (env leaks via `/proc/<pid>/environ`, crash dumps, child
processes); never bake into images.

## 4. Runtime detection (the layer after prevention)

**R4.1 — Run a runtime sensor on sandbox nodes** (Falco, Tetragon, or commercial
eBPF EDR). Prevention bounds the blast radius; detection tells you the boundary was
*tested*. Minimum alert set: exec into container (`kubectl exec`/runtime exec),
shell spawned in shell-less image, write below `/etc`/`/usr`, outbound connection
not matching policy, `setns`/nsenter usage, kernel module load, ptrace, mount
syscalls, access to service-account token by unexpected binary.

**R4.2 — Alerts must page someone.** A Falco rule nobody routes is documentation.
Wire to the SIEM/on-call; test with a benign canary (e.g., spawn `sh` in a
distroless pod in staging and confirm the page).

**R4.3 — Forensics readiness:** container logs shipped off-node; `--rm`/ephemerality
is good for security but plan checkpointing/image capture for incident response
(`kubectl debug` node profile, runtime checkpoint APIs).

---

## Audit checklist

- [ ] Images: non-root numeric `USER`, distroless/minimal base, pinned by digest,
      scanned + signed; no secrets in layers/env; multi-stage builds.
- [ ] No container runs `--privileged`, with the Docker/CRI socket, host
      namespaces (`pid/net/ipc/userns`), writable `/sys`-`/proc`, raw devices, or
      sensitive hostPath — verified by admission policy, not convention.
- [ ] Every container: cap-drop ALL (justified add-backs only),
      no-new-privileges/allowPrivilegeEscalation=false, read-only rootfs +
      size-capped tmpfs, seccomp RuntimeDefault-or-stricter (never unconfined),
      memory/CPU/pids limits.
- [ ] Untrusted/multi-tenant workloads run under gVisor or Kata/Firecracker
      (RuntimeClass), on tainted dedicated node pools; `hostUsers: false` set
      where nodes support user namespaces (GA in v1.36).
- [ ] PSA `restricted` enforced (+ audit/warn) on all non-system namespaces;
      exceptions enumerated with owners.
- [ ] `automountServiceAccountToken: false` by default; RBAC reviewed for
      escalation verbs (`pods/exec`, secrets, create pods, escalate/bind/impersonate).
- [ ] Default-deny NetworkPolicy ingress+egress in every namespace; DNS and
      metadata-endpoint egress explicitly constrained; FQDN egress allowlists for
      external calls where CNI supports it.
- [ ] Secrets short-lived and file-mounted; no long-lived cloud keys in pods;
      metadata service unreachable or audience-bound.
- [ ] Runtime detection deployed on all nodes with the R4.1 minimum rule set,
      routed to on-call, and canary-tested within the last quarter.
- [ ] Rootless/userns-remapped engine on hosts where dev containers run; Docker
      API never on unauthenticated TCP; runc ≥ 1.2.8/1.3.3 (November 2025
      escape trio, R1.4).
