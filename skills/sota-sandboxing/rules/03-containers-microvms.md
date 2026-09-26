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
# builder's Python minor MUST equal the runtime's (python3-debian13: 3.13 as of 2026-09-26,
# read `crane config` Entrypoint) — a mismatch fails at import: ModuleNotFoundError
FROM python:3.13-slim@sha256:<digest> AS build
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --target=/deps -r requirements.txt
COPY . .

FROM gcr.io/distroless/python3-debian13:nonroot@sha256:<digest>
COPY --from=build /deps /app/deps
COPY --from=build /app /app
ENV PYTHONPATH=/app/deps
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

**Read-only rootfs does not cover what you mount on top of it.** Every bind mount
or volume the workload only *reads* (input data, models, config) is mounted
read-only: `-v src:/in:ro` or `--mount type=bind,src=…,dst=/in,readonly`; Compose
`"./in:/in:ro"`; Kubernetes `volumeMounts[].readOnly: true`. A read-only mount is
not automatically read-only below it: Kubernetes documents that a read-write
filesystem mounted *under* a read-only volume stays writable unless
`recursiveReadOnly: Enabled` is set (GA in v1.33; needs kernel ≥ 5.12 and runtime
support, and fails the pod otherwise — `IfPossible` falls back silently). Docker
makes submounts of a read-only bind mount read-only best-effort on kernel ≥ 5.12
and leaves them writable below that; to fail instead of falling back, use
`--mount …,readonly,bind-recursive=readonly` (the option exists only on `--mount`).
OWASP: Docker Security cheat sheet.

**The limit list includes the accelerator and the wire.** CPU, memory, pids and
disk are not the whole budget:
- **GPU:** grant devices explicitly and by count or ID — Kubernetes
  `limits: { nvidia.com/gpu: 1 }` (GPUs go in `limits` only; the scheduler uses
  it as the request), Docker `--gpus device=<index|UUID>`, Compose `count: 1` or
  `device_ids`. `--gpus all`, Compose `count: all` **or an omitted count**, and
  `NVIDIA_VISIBLE_DEVICES=all` (the default baked into base CUDA images) all hand
  the workload every GPU on the host. Device memory is capped only by hardware
  partitioning (a MIG profile); time-slicing replicas bound how many workloads share
  a device, not how much memory each takes (R2.4).
- **Network bandwidth:** `docker run` has no network rate flag (its `*-bps` flags
  throttle block devices), so shape at the network layer: on Kubernetes, the CNI
  `bandwidth` plugin plus the `kubernetes.io/ingress-bandwidth` /
  `kubernetes.io/egress-bandwidth` pod annotations (documented as experimental);
  elsewhere a `tc` qdisc on the veth, or per-client rate limits at the egress
  proxy (`05` R4.1). One tenant saturating the uplink is a denial of service for
  every neighbour, and a bulk exfiltration channel.
OWASP: Secure AI Model Ops cheat sheet.

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
that holds when the runtime itself fails. Verify runc ≥ 1.2.8/1.3.3; ≥ 1.3.6/1.4.3
also closes CVE-2026-41579 (medium, CVSS 3.3: a malicious image's `/dev` symlink makes runc write
host symlinks; exploitable under podman/containerd, not Docker — GHSA-xjvp-4fhw-gc47).

**R1.5 — Supply chain is part of sandbox posture:** pin base images by digest, scan
(grype/trivy) in CI with a severity gate, sign and verify (cosign + policy
controller), generate SBOMs. An attacker who owns your base image is *inside* the
sandbox at boot.

**R1.6 — Published ports skip the host firewall; the default bridge is flat.**
With no host address, `-p 8080:80` (or Compose `"8080:80"`) publishes on every
host interface (`0.0.0.0` and `[::]`), and Docker's NAT rules steer that traffic
before it reaches the `INPUT` chain a UFW-style firewall filters — the port is
reachable from outside while `ufw status` says it is closed. So:
- Bind to loopback unless the port must be public: `-p 127.0.0.1:8080:80`,
  `"127.0.0.1:8080:80"`; the daemon's `"ip"` setting changes the default host
  address for the default bridge.
- Put host-level filtering for container traffic in the `DOCKER-USER` chain,
  which Docker evaluates before its own forwarding rules; rules appended to
  `FORWARD` never see those packets. After any Docker or firewall-manager
  upgrade, confirm from *another host* that only intended ports answer.
- Don't use the default bridge. Every container started without `--network`
  lands on it and can reach every other one (inter-container communication is on
  by default, `--icc`/`"icc"`). Create user-defined networks per trust group and
  attach only the containers that must talk; set `"icc": false` for anything left
  on the default bridge.
OWASP: Docker Security cheat sheet.

## 2. Sandboxed runtimes: gVisor, Kata, Firecracker

**R2.1 — gVisor (runsc):** user-space kernel (Sentry) intercepts the container's
syscalls; host kernel sees only the Sentry's narrow, seccomp-pinned syscall set.
- Use for: untrusted/multi-tenant containers needing container UX, fast startup,
  high density; CPU/memory overhead modest, **syscall- and I/O-heavy workloads pay
  the most** (platform choice: KVM on bare metal, `systrap` — the default since
  mid-2023 — inside VMs; `ptrace` is unsupported and slated for removal).
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
(virtio net/block/vsock/rng/pmem/mem + balloon; optional PCI *transport* for virtio
since 1.13 via `--enable-pci`; no device passthrough in its device API, no GPU —
as of 2026-09-26).
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
*weakens* the boundary (audit it). The GPU container stack is itself escape
surface: NVIDIA Container Toolkit hooks let a crafted image reach the host
(CVE-2024-0132, fixed in toolkit 1.16.2 / GPU Operator 24.6.2, not hit in CDI mode;
CVE-2025-23266, critical, fixed in toolkit 1.17.8 / GPU Operator 25.3.2 — NVIDIA
bulletins 5582, 5659), so hold those floors on any GPU node. **A GPU is shared state:** never schedule
mutually untrusted tenants onto one GPU through time-slicing — NVIDIA's own
GPU Operator docs state it gives no memory or fault isolation between replicas —
and allow co-tenancy only with hardware partitioning that isolates memory
(MIG-class); otherwise give each tenant whole devices. Clear accelerator memory
between jobs as you would scratch files: GPU on-chip "local" memory has leaked
between processes (LeftoverLocals, CVE-2023-4969 — AMD, Apple and Imagination GPUs
affected, Qualcomm unknown, NVIDIA and Intel not, per CERT/CC VU#446598), so reset
or scrub the device, or
destroy the VM, before the next tenant's job. Confidential GPU modes are
`sota-confidential-computing` rules/02. OWASP: AISVS 4.2.4; Secure AI Model Ops
cheat sheet. For agent workloads on K8s, the Kubernetes
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
      appArmorProfile: { type: RuntimeDefault }  # AppArmor nodes; or Localhost + localhostProfile
      # procMount: leave unset (= Default, masked /proc); never Unmasked
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

**AppArmor and `/proc` are part of the template, not node luck.** The
`appArmorProfile` field (stable since v1.31, replacing the beta annotation) takes
`RuntimeDefault`, `Localhost` (with `localhostProfile`) or `Unconfined`. Left
unset, the runtime default applies *only if the node has AppArmor enabled*; set
explicitly to `RuntimeDefault`, a pod is refused admission on a node without it —
so set it on AppArmor node pools to turn a silent gap into a scheduling error
(SELinux-based nodes use `seLinuxOptions` instead, `02`). `procMount` must stay
`Default`, which keeps `/proc` paths masked and read-only; `Unmasked` exposes them
(and `/sys/firmware`), Kubernetes only admits it with `hostUsers: false`, and PSS
**baseline** already forbids any value but `Default`, as it forbids
`Unconfined` AppArmor. OWASP: Docker Security and Kubernetes Security cheat
sheets.

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
  # IN-CLUSTER destination: select it by IDENTITY, never by its pod CIDR. Pod IPs are
  # recycled, so a CIDR silently re-points at whatever lands there next.
  - to: [{ namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: backend } },
           podSelector: { matchLabels: { app: approved-backend } } }]
    ports: [{ protocol: TCP, port: 443 }]
```
A cluster with no NetworkPolicies = flat network = any pod compromise reaches every
service. DNS egress should also be policy-constrained (DNS exfil channel); CNIs like
Cilium can enforce FQDN-level egress (`toFQDNs`) — prefer that for external allowlists.

**Why the in-cluster peer is a selector and not `ipBlock: { cidr: 10.0.5.0/24 }`, which
this example used until 2026-09-11.** `sota-network-security` requires every allow to
reference identity and **never a bare CIDR** (its non-negotiable 3, rules/02). Inside the
cluster that rule is satisfiable and a CIDR is strictly worse: pod IPs are ephemeral and
reused, so the policy grants whatever occupies the range later — the allowlist widens
without the manifest changing. **Outside the cluster it is not satisfiable**: vanilla
NetworkPolicy has no identity selector for an external destination, so `ipBlock` is the
only expressible form and is a **documented exception, not a default** — name the
destination and the reason in a comment, keep the prefix as tight as the peer actually
requires, and prefer a CNI that can express identity there (Cilium `toFQDNs`/`toEntities`)
over widening the CIDR. The exception is scoped in `sota-network-security` rules/03 §3.

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
syscalls, access to service-account token by unexpected binary, **opening a device
node** the workload was not granted a use for (host block devices, `/dev/mem`,
GPU/accelerator devices from a non-GPU image — the one step a GPU miner cannot
skip), and **any connection attempt to the cloud metadata endpoint** from a
workload that should not reach it — the attempt matters even when the network
blocks it. In Falco the stock versions are not in the default ruleset: `Contact
cloud metadata service from container` ships in the *incubating* rules, matches
only `169.254.169.254` (add `fd00:ec2::254` and your cloud's equivalents) and
exempts `kube-system` via `user_known_metadata_access`; `Privileged Container
Device Access` and `Container Accessing GPU Device` ship in the *sandbox* rules,
the GPU one `enabled: false` until you tune `user_known_gpu_workloads`. Load the
file, tune the exception macro, and enable the rule, or write your own.
OWASP: Secure AI Model Ops cheat sheet.

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
- [ ] Every IN-cluster egress peer selected by identity (`podSelector`/`namespaceSelector`),
      not by a pod CIDR — `grep -n 'ipBlock' policies/` and, for each hit, require either an
      out-of-cluster destination or a rewrite; a recycled pod IP re-points the allow silently
- [ ] Default-deny NetworkPolicy ingress+egress in every namespace; DNS and
      metadata-endpoint egress explicitly constrained; FQDN egress allowlists for
      external calls where CNI supports it.
- [ ] Secrets short-lived and file-mounted; no long-lived cloud keys in pods;
      metadata service unreachable or audience-bound.
- [ ] Runtime detection deployed on all nodes with the R4.1 minimum rule set,
      routed to on-call, and canary-tested within the last quarter.
- [ ] Rootless/userns-remapped engine on hosts where dev containers run; Docker
      API never on unauthenticated TCP; runc ≥ 1.2.8/1.3.3 (November 2025
      escape trio, R1.4), ≥ 1.3.6/1.4.3 under podman/containerd (CVE-2026-41579);
      GPU nodes run NVIDIA Container Toolkit ≥ 1.17.8 / GPU Operator ≥ 25.3.2 (R2.4).
- [ ] **High** — Published ports bound to loopback unless deliberately public,
      host filtering in `DOCKER-USER`, exposure checked from another host, and no
      service on the default bridge with `icc` on (R1.6):
      `grep -rnE -- '(-p|--publish)[ =]"?[0-9]+:[0-9]+|^[[:space:]]*-[[:space:]]*"?[0-9]+:[0-9]+' .`
      — each hit publishes on all interfaces; want `127.0.0.1:` or a documented
      reason.
- [ ] **High** — No GPU shared between mutually untrusted tenants by
      time-slicing; co-tenancy only with MIG-class partitioning; device memory
      reset or VM destroyed between tenants' jobs (R2.4):
      `grep -rnE 'timeSlicing:|nvidia\.com/gpu\.shared' .` on a multi-tenant
      cluster is a finding unless the sharing pods are one tenant.
- [ ] **Medium** — Mounts the workload only reads are read-only, and a read-only
      mount with filesystems below it is recursively read-only (R1.2):
      `grep -rnE -e '(-v|--volume)[ =][^ ]+:/[^ :]*(:[^ ]*)?([[:space:]]|$)' -e '^[[:space:]]*- +[^ :#]+:/[^ :]*(:[^ ]*)?[[:space:]]*$' . | grep -vE '[:,]ro([^[:alnum:]]|$)'`
      — each hit is a writable `-v` or Compose short-syntax mount; confirm the
      workload writes there. `--mount` and Kubernetes `volumeMounts` need a
      manual read for `readonly` / `readOnly: true`.
- [ ] **Medium** — GPUs granted by explicit count or ID, never "all", and
      network bandwidth shaped per workload where tenants share an uplink (R1.2):
      `grep -rnE -- '--gpus[ =]"?all|NVIDIA_VISIBLE_DEVICES[=:[:space:]]+"?all|^[[:space:]]*count:[[:space:]]*"?all' .`
      — each hit exposes every host GPU; a Compose GPU reservation with no
      `count` and no `device_ids` does too, and a base CUDA image defaults to all.
- [ ] **Medium** — Pod template sets `appArmorProfile` (on AppArmor nodes) and
      never unmasks `/proc` or runs unconfined (R3.2):
      `grep -rnE 'procMount:[[:space:]]*"?Unmasked|type:[[:space:]]*"?Unconfined|apparmor\.security\.beta\.kubernetes\.io/[^:]*:[[:space:]]*"?unconfined' .`
      — each hit is a finding (covers seccomp `Unconfined` too).
- [ ] **Medium** — Runtime sensor alerts on device-node opens and metadata-endpoint
      attempts (R4.1). For Falco, find configs that load only the default ruleset,
      and overrides that switch the stock rules off:
      `grep -rlE 'falco_rules\.yaml' . | xargs -r grep -LE 'falco-(incubating|sandbox)_rules'`
      and `grep -rnE -A2 -- '- rule: (Contact cloud metadata service from container|Contact EC2 Instance Metadata Service From Container|Privileged Container Device Access|Container Accessing GPU Device)' . | grep -E 'enabled:[[:space:]]*false'`
      — a hit on either is a finding unless custom rules cover both classes. Also read
      any `rules:` selection in `falco.yaml` (`- disable:` by `rule:` wildcard or `tag:`):
      it runs after every rules file and overrides their `enabled:`.
