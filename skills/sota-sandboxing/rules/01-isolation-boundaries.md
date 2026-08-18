# 01 — Isolation Boundaries: Principles & Boundary Selection

Scope: how to choose the *right* isolation boundary for a given threat, before any
implementation detail. Read this first; every other rules file assumes the boundary
choice made here is correct.

---

## 1. Core principles

**R1.1 — Least privilege is the design input, not a hardening pass.**
Enumerate what the workload *needs* (files, syscalls, network destinations, CPU/memory,
wall-clock) before writing the sandbox config. Everything not enumerated is denied.
A sandbox derived from "remove what looks dangerous" (blocklist) always leaks; one
derived from "grant what is required" (allowlist) fails closed.
*Rationale:* attackers find the capability you forgot to remove; they cannot use one
you never granted.

**R1.2 — Defense in depth means independent layers, not redundant ones.**
Stack boundaries with *different failure modes*: e.g., seccomp (kernel attack-surface
reduction) + user namespace (root-in-container ≠ root-on-host) + network policy
(post-compromise egress containment). Two copies of the same control (two seccomp
profiles) is one layer. Assume each layer will be bypassed; ask "what does the attacker
hold after this layer falls?"

**R1.3 — A sandbox is only as strong as its widest interface.**
Count the attack surface in *reachable kernel/API surface*, not in marketing terms.
A container with `--privileged` is process isolation in a costume. A VM with a
host-mounted 9p/virtiofs share of `$HOME` is a fancy chroot. Audit the holes punched
through the boundary (mounts, sockets, device nodes, shared memory, environment),
not the boundary's brand name.

**R1.4 — Fail closed.**
Sandbox setup failure must abort the workload, not run it unsandboxed. Common bug:
`if seccomp_load() fails: log warning; continue`. Treat "sandbox unavailable" as
"execution forbidden."

**R1.5 — Sandboxes are not a substitute for input validation, and vice versa.**
Validation reduces probability of compromise; the sandbox bounds the *blast radius*
when validation fails. You need both. Any design doc saying "we don't need to sandbox
the parser because we validate input" (or the reverse) is a finding.

---

## 2. Boundary strength ranking

From strongest to weakest. Strength = cost for an attacker with arbitrary code
execution *inside* the boundary to reach the layer outside it.

| Rank | Boundary | Shared with attacker | Typical escape class | Escape rarity |
|---|---|---|---|---|
| 1 | **Separate hardware** (air-gapped or dedicated machine) | Nothing (or network only) | Physical / supply chain / network lateral | Extremely rare |
| 2 | **Full VM** (KVM/QEMU, Hyper-V, ESXi) | CPU, hypervisor, device emulation | Hypervisor/device-model bugs (e.g., QEMU device emulation CVEs), speculative side channels | Rare |
| 3 | **microVM** (Firecracker, Cloud Hypervisor; Kata Containers) | CPU, minimal VMM (~few virtio devices) | VMM bugs; far smaller device surface than QEMU | Rare |
| 4 | **User-space kernel** (gVisor/runsc) | Host kernel via ~50–70 filtered syscalls from the Sentry | Bugs in Sentry or in the narrow host syscall set | Uncommon |
| 5 | **Container** (runc + namespaces + cgroups + seccomp + LSM) | Entire host kernel | Kernel LPE (any of ~hundreds of reachable syscalls), misconfiguration (mounts, caps) | Common via misconfig; periodic via kernel CVE |
| 6 | **OS process sandbox** (seccomp + Landlock + rlimits + drop privs, no namespaces) | Host kernel, often host filesystem view | Kernel LPE; policy gaps | Same kernel exposure as 5, fewer layers |
| 7 | **Language runtime / in-process** (V8 isolate, WASM in-process, JVM SecurityManager-style, "restricted Python") | Entire process address space, all of the above | Runtime JIT/compiler bugs; any native-memory bug = full process compromise | V8/WASM: regular CVE cadence. Restricted-Python/JS "jails" without process isolation: trivially escaped — treat as no boundary |

**R2.1 — Never treat rank 7 alone as a security boundary for untrusted *code*.**
V8 isolates and WASM engines are good *components* of a sandbox, but production
deployments that bet on them (Cloudflare Workers, fastly) wrap them in process
isolation + seccomp + scheduling defenses. In-language sandboxes (`eval` with a
scrubbed scope, RestrictedPython, `vm2` — repeatedly escaped and now deprecated)
are not boundaries at all.

**R2.2 — Side channels degrade every shared-CPU boundary.**
For confidentiality between mutually distrusting tenants (secrets on both sides),
shared-kernel boundaries (5–7) are insufficient against a determined attacker;
prefer 1–3 plus disabled SMT or core scheduling for cross-tenant secrets.

---

## 3. Choosing the boundary for the threat

Classify the workload first. The three canonical threat shapes:

### A. Untrusted CODE (you intentionally execute attacker-supplied logic)
Examples: CI runners for public PRs, code-execution APIs, plugin systems, serverless
multi-tenant, **AI-generated code execution**.
- Assume arbitrary syscalls, infinite loops, fork bombs, kernel-exploit attempts.
- **Minimum bar: rank ≤ 4** (gVisor) for anything internet-facing or multi-tenant;
  **rank ≤ 3** (Firecracker/Kata) when tenants' data confidentiality matters.
- A plain runc container (rank 5) is acceptable only for *semi-trusted* code
  (your own employees' jobs) AND with the full hardening set from `02`/`03`.

### B. Untrusted INPUT (your trusted code parses attacker-controlled data)
Examples: image/PDF/video/archive/font parsing, file-format converters, AV scanners,
protocol decoders.
- Threat is memory-corruption → attacker pivots to "untrusted code" *inside your
  process*. Sandbox the *parser*, not the whole service.
- **Minimum bar: rank 5–6** — dedicated short-lived process with seccomp deny-by-default,
  no network, read-only view of only the input, write to a pipe/output fd. See `04`.
- Rank 7 (compile parser to WASM, e.g. RLBox-style) is a strong *additional* layer
  because it converts memory corruption into a trap, but pair it with process isolation.

### C. MULTI-TENANT (many customers on shared infrastructure, no attacker assumed yet)
- The boundary must hold even if one tenant is fully compromised (becomes case A).
- Shared-kernel containers between tenants = accepting that any single kernel LPE
  breaches all tenants. Acceptable only with a documented risk sign-off; default to
  microVM/VM-per-tenant or gVisor.
- Data-plane vs control-plane: tenant *code* needs A-level isolation; tenant *data*
  processed by your code needs B-level isolation per-tenant request where feasible.

### Decision table

| Workload | Floor | Preferred |
|---|---|---|
| Public code-execution / AI agent code | gVisor | Firecracker/Kata microVM, fresh per session |
| Internal CI (semi-trusted) | Hardened container | gVisor or ephemeral VM runners |
| Risky parser in a trusted service | seccomp'd subprocess | subprocess + Landlock + WASM-compiled parser |
| SaaS multi-tenant app code | gVisor / Kata | microVM per tenant |
| Browser-like rendering of untrusted content | dedicated process + seccomp | site-isolation-style process per origin |
| Cross-tenant secrets (KMS, signing) | dedicated VM | dedicated hardware / HSM |

**R3.1 — Ephemerality is a boundary multiplier.** A sandbox destroyed after one task
(fresh microVM per request, `--rm` container per job) turns persistence into a
non-goal for the attacker and erases foothold accumulation. Prefer
one-shot-per-unit-of-untrust over long-lived shared sandboxes. Never reuse a sandbox
across trust domains (two different users/tenants/sessions).

**R3.2 — Co-locate by trust, not by convenience.** Never schedule untrusted-code
workloads on nodes that also run control-plane, secrets, or build-signing workloads
(K8s: taints/tolerations + dedicated node pools; see `03`).

**R3.3 — The data the sandbox can see is part of the boundary decision.**
A perfectly escaped-proof sandbox that mounts the production database credentials is
a breach by design. Inventory secrets/mounts/tokens reachable *inside* the sandbox;
the correct amount for untrusted code is zero (broker pattern, `04`).

---

## 4. Reference stacks (known-good compositions)

Use these as starting points; each line is an independent layer per R1.2.

### Stack A — public code-execution service (untrusted code, multi-tenant)
```
Firecracker microVM per session (jailer: chroot+seccomp+cgroup around VMM)
 └─ minimal guest kernel, no modules, read-only rootfs + tmpfs workspace
 └─ no NIC, or vsock-only to a host-side broker/proxy
 └─ host: dedicated node pool, no secrets co-resident, VMM as non-root user
 └─ wall-clock kill + snapshot-restore pool for latency
```

### Stack B — multi-tenant K8s SaaS (tenant apps, semi-hostile)
```
gVisor (runsc, KVM platform) RuntimeClass per tenant namespace
 └─ PSA restricted + securityContext baseline (03 §3.2)
 └─ default-deny NetworkPolicy ingress+egress, FQDN egress via Cilium
 └─ per-tenant node pools for high-tier tenants; SMT off for shared pools
 └─ Falco/Tetragon on every node, alerts paged
```

### Stack C — risky parser inside a trusted service (untrusted input)
```
one-shot worker process per input (bwrap/minijail or self-applied)
 └─ empty netns, new pid/mount/ipc ns, pivot_root minimal tree
 └─ seccomp compute-only allowlist (no openat/socket/exec)
 └─ Landlock empty fs policy; input/output as inherited FDs only
 └─ cgroup: 256M mem, pids.max=16, 10s wall-clock kill; output size cap in parent
```

### Stack D — AI coding agent on a developer laptop
```
container (rootless podman / Docker userns-remap) per session
 └─ workspace bind-mount only; no $HOME, no dotfiles, no SSH agent
 └─ network: deny-by-default, proxy with FQDN allowlist for package mirrors
 └─ harness-side approval gate for writes outside workspace / pushes / spends
 └─ orchestrator + credentials outside the container (05 §6)
```

## 5. Verifying a boundary (boundaries are claims until tested)

**R5.1 — Ship an in-sandbox probe and run it in CI.** The probe *attempts* what the
policy denies and fails the build if anything succeeds:
- read canary secret paths (`/run/secrets`, `~/.aws/credentials`, env vars);
- `curl 169.254.169.254` and one non-allowlisted FQDN and one raw IP;
- denied syscalls (`unshare`, `mount`, `ptrace` of pid 1) expecting `EPERM`/kill;
- write to `/`, `/etc`, the host-visible mounts; exec a setuid binary;
- fork bomb / 2× memory.max allocation, expecting clean containment + kill.

**R5.1b — the probe needs an allow arm.** Every bullet above is a denial: the build
fails if something *succeeds*. A policy that denies everything passes all of them.
Add one arm that runs the **representative legitimate workload** to completion
inside the same policy — the real parser on a real input, the real job on a real
payload — and fail the build if *that* is refused, killed or truncated. Without it
the probe cannot tell a working sandbox from a sandbox nobody can use, and the
difference surfaces in production instead (`sota-code-security` rules/12 §1a).

**R5.2 — Test the failure mode, not just the policy:** kill the seccomp loader,
point at a kernel without Landlock, make the proxy unreachable — the workload must
*abort*, not proceed (R1.4). Chaos-test fail-closed annually at minimum.

**R5.3 — Inspect the running artifact, not the manifest.** Audits read
`/proc/<pid>/status` (CapEff, Seccomp, NoNewPrivs), `nsenter`-visible mounts, and
live NetworkPolicy/iptables state. Drift between spec and runtime is itself a
finding (Medium).

## 6. Anti-patterns (instant findings)

- **"Docker = secure"**: default Docker (root in container, broad seccomp allowlist,
  all default caps) is an operational tool, not a security boundary claim. (High)
- **chroot as a sandbox**: trivially escaped by root; not a security mechanism. (High)
- **Language-level jails as sole boundary** (`vm2`, RestrictedPython, `eval` scrubbing,
  regex-filtering "dangerous" code before exec). (Critical when running untrusted code)
- **Sandbox with prod credentials/cloud metadata reachable** (169.254.169.254 open,
  service-account token mounted). (Critical)
- **Shared long-lived sandbox across tenants/sessions.** (High)
- **Fail-open sandbox setup.** (High)
- **Boundary downgraded for performance without recorded risk acceptance.** (Medium)

---

## Audit checklist

- [ ] Workload classified (untrusted code / untrusted input / multi-tenant) and the
      chosen boundary meets the floor in the decision table.
- [ ] Privileges derived from an explicit needs-list; allowlist, not blocklist, at
      every layer (syscalls, files, network, capabilities).
- [ ] At least two *independent* layers between untrusted execution and the crown
      jewels; documented "what does the attacker hold if layer N falls?"
- [ ] All holes through the boundary inventoried: mounts, sockets, device nodes,
      shared memory, env vars, tokens, metadata endpoints.
- [ ] Sandbox setup fails closed (workload aborts if any layer can't be applied).
- [ ] Sandboxes are per-trust-domain and ephemeral; no reuse across users/tenants.
- [ ] No secrets, cloud credentials, or metadata service reachable from inside.
- [ ] Untrusted workloads scheduled away from control-plane/secrets workloads.
- [ ] No anti-pattern from §6 present; any boundary downgrade has a written,
      dated risk acceptance.
- [ ] In-sandbox denial probe exists and runs in CI; fail-closed behavior
      chaos-tested; runtime state matches the spec (CapEff/Seccomp/NoNewPrivs
      inspected, not assumed).
- [ ] The probe has an **allow arm** as well as its denial arms — the real
      workload completes inside the real policy, so a sandbox that denies
      everything cannot pass CI (R5.1b).
- [ ] Side-channel posture documented for cross-tenant confidentiality (SMT,
      core scheduling, memory dedup disabled where required).
