# 02 — Linux OS-Level Primitives: namespaces, cgroups, seccomp, Landlock, LSMs, capabilities

Scope: the kernel mechanisms every Linux sandbox is built from. Applies whether you
assemble them by hand (`clone3`/`unshare`, minijail, bubblewrap, nsjail, systemd) or
consume them via a container runtime (then also read `03`).

---

## 1. Namespaces

**R1.1 — Unshare every namespace you don't need to share.** A sandboxed process gets
new `mount`, `pid`, `net`, `ipc`, `uts`, `cgroup`, and (where possible) `user`
namespaces. Each shared namespace is reachable attack surface: shared `net` = host
loopback services; shared `pid` = signal/ptrace targets + `/proc/<pid>` of host
processes; shared `ipc` = SysV shm/semaphore tampering.

**R1.2 — User namespaces: two distinct rules.**
- *Rootless sandboxing* (good): map sandbox-root to an unprivileged host UID
  (`unshare -r`, podman rootless, bubblewrap). "root" inside has no host privilege;
  a container breakout lands as `nobody`-equivalent.
- *Unprivileged userns as kernel attack surface* (risk): unprivileged userns creation
  exposes normally-root-only kernel paths (netfilter, etc.) to any local user — a
  recurring LPE vector. On hosts that run untrusted code, restrict creation to
  sandboxing helpers: `kernel.unprivileged_userns_clone=0` (Debian),
  `user.max_user_namespaces` quota, or AppArmor `userns` restriction (Ubuntu 24.04+).
  Decide deliberately; don't leave the distro default unexamined.

**R1.3 — PID namespace needs a real init.** PID 1 inside must reap zombies and forward
signals (`tini`, `catatonit`, or `--init`). Combine with new `proc` mount
(`mount -t proc`) — never bind the host's `/proc` into a PID-namespaced sandbox
(leaks host process info and `/proc/sys` write paths).

**R1.4 — Mount namespace hygiene.** Build the sandbox filesystem from nothing:
pivot_root (not chroot) into a minimal tree; mount with `nosuid,nodev,noexec` wherever
possible; mark propagation `MS_PRIVATE`/`MS_SLAVE` so sandbox mounts can't propagate to
the host. Mask `/proc/kcore`, `/proc/sys`, `/sys/firmware`, `/proc/sysrq-trigger`.

**R1.5 — Network namespace default: empty.** A new netns has only loopback (down).
That *is* the network policy for most parsers and codegen sandboxes. Add connectivity
only via an explicit veth/slirp/proxy with an egress allowlist (see `05` §3).

## 2. cgroups v2

**R2.1 — Every sandbox gets a resource budget.** Unbounded sandboxes convert "escape
attempt failed" into "host DoS succeeded." Set, at minimum:

```
# cgroup v2 controllers for an untrusted job
memory.max=512M  memory.swap.max=0      # hard cap, no swap escape hatch
pids.max=128                            # fork-bomb stopper
cpu.max="50000 100000"                  # 0.5 CPU
io.max="259:0 rbps=10485760 wbps=10485760"
```

systemd-run equivalent (preferred over hand-rolled cgroup writes):
`systemd-run --scope -p MemoryMax=512M -p MemorySwapMax=0 -p TasksMax=128 -p CPUQuota=50% cmd`

**R2.2 — `memory.max` + `memory.oom.group=1`** so the OOM kill takes the whole sandbox
atomically, not one random victim thread that leaves a half-alive job.

**R2.3 — `pids.max` is non-negotiable** for any sandbox that can `fork`/`clone`.

**R2.4 — cgroup v1 is legacy**; on mixed hosts verify which hierarchy actually
enforces the limits you set. Don't mount the host cgroupfs writable inside a sandbox
(release_agent-style escapes; mount it read-only or not at all).

## 3. seccomp-bpf

**R3.1 — Deny-by-default (`SCMP_ACT_ERRNO` default action), explicit allowlist.**
Docker's default profile is a *blocklist-shaped allowlist* of ~350 syscalls tuned for
compatibility, not least privilege. For a real sandbox, profile the workload
(`strace -cf`, or `perf trace`) and allow only what it uses — typically 40–80 syscalls.

```json
{
  "defaultAction": "SCMP_ACT_ERRNO",
  "defaultErrnoRet": 1,
  "architectures": ["SCMP_ARCH_X86_64", "SCMP_ARCH_AARCH64"],
  "syscalls": [
    { "names": ["read","write","close","fstat","lseek","mmap","mprotect",
                "munmap","brk","rt_sigaction","rt_sigreturn","futex",
                "exit","exit_group","clock_gettime","getrandom"],
      "action": "SCMP_ACT_ALLOW" },
    { "names": ["openat"], "action": "SCMP_ACT_ALLOW",
      "comment": "constrain paths with Landlock; seccomp can't see strings" },
    { "names": ["clone"], "action": "SCMP_ACT_ALLOW",
      "args": [{ "index": 0, "op": "SCMP_CMP_MASKED_EQ",
                 "value": 2114060288, "valueTwo": 0,
                 "comment": "deny CLONE_NEW* flags" }] }
  ]
}
```

**R3.2 — Syscalls that must never appear in an untrusted-workload allowlist** unless
specifically justified: `ptrace`, `process_vm_readv/writev`, `bpf`, `perf_event_open`,
`mount`/`move_mount`/`fsmount`, `umount2`, `pivot_root`, `chroot` (post-setup),
`init_module`/`finit_module`, `kexec_load`, `open_by_handle_at`, `userfaultfd`,
`keyctl`/`add_key`, `setns`, `unshare` (post-setup), `io_uring_setup` (large,
fast-moving attack surface — deny for untrusted code), `quotactl`, `reboot`,
`settimeofday`/`clock_settime`, `acct`, `personality`.

**R3.3 — Seccomp filters argument *values*, never dereferenced pointers.** It cannot
check the path passed to `openat` — pair seccomp (syscall surface) with Landlock or
mount namespaces (file scope). Designs that claim path filtering in seccomp are bugs.

**R3.4 — Mechanics that matter:**
- Set `no_new_privs` before loading the filter (mandatory for unprivileged seccomp;
  also blocks setuid re-escalation).
- Cover **all architectures** the kernel can execute (x86-64 *and* x32/i386 entry on
  amd64 hosts — attackers switch ABI to dodge filters); either list every arch or kill
  foreign-arch syscalls with `SCMP_ACT_KILL_PROCESS`.
- Prefer `SCMP_ACT_ERRNO` for compat probing noise, `SCMP_ACT_KILL_PROCESS` for the
  hard-deny set in R3.2.
- `seccomp_unotify` (user-space supervisor) is for *emulation/brokering*, not security
  decisions on pointer args (TOCTOU on memory reads unless using `SECCOMP_IOCTL_NOTIF_ADDFD`
  and pidfd-based reads carefully).

## 4. Landlock

**R4.1 — Use Landlock for unprivileged filesystem (and 6.7+ network-port) scoping.**
It is stackable, needs no root, and complements seccomp: seccomp limits *which*
syscalls, Landlock limits *which objects*. ABI v4 (kernel 6.7) adds TCP bind/connect
port control; ABI v6 adds IPC scoping (`LANDLOCK_SCOPE_SIGNAL`,
`LANDLOCK_SCOPE_ABSTRACT_UNIX_SOCKET`) — close these channels for untrusted code;
ABI v7 (kernel 6.15+) emits `LANDLOCK_ACCESS` denial records via the audit
subsystem — wire them into detection; ABI v8 (kernel 7.0) adds
`LANDLOCK_RESTRICT_SELF_TSYNC` to apply a ruleset across all threads of the
process; mainline docs add ABI v9 (pathname-UNIX-socket scoping,
`LANDLOCK_ACCESS_FS_RESOLVE_UNIX`) and v10 (UDP bind/connect-send scoping + quiet
rule logging) — check the landlock(7) VERSIONS table for the kernels shipping them.

```c
// allow read-only on /usr, read-write only on the job dir; everything else denied
struct landlock_ruleset_attr attr = {
  .handled_access_fs = LANDLOCK_ACCESS_FS_EXECUTE | LANDLOCK_ACCESS_FS_READ_FILE |
                       LANDLOCK_ACCESS_FS_READ_DIR | LANDLOCK_ACCESS_FS_WRITE_FILE |
                       LANDLOCK_ACCESS_FS_MAKE_REG | LANDLOCK_ACCESS_FS_REMOVE_FILE,
  .handled_access_net = LANDLOCK_ACCESS_NET_CONNECT_TCP | LANDLOCK_ACCESS_NET_BIND_TCP,
};
```
Then add rules per path FD and `landlock_restrict_self()` after `prctl(PR_SET_NO_NEW_PRIVS,1)`.
Check ABI version at runtime and **fail closed** if the kernel lacks the features you need.

**R4.2 — Handled-access completeness:** any access type *not* in `handled_access_fs`
is implicitly allowed — a classic Landlock misconfiguration. Handle every access
right the ABI supports, then grant back selectively.

## 5. Capabilities

**R5.1 — Drop ALL, add back the minimum.** Root with all caps split across ~40 bits;
several are root-equivalent on their own: `CAP_SYS_ADMIN` (catch-all; mounts, etc.),
`CAP_SYS_PTRACE` (read any process memory), `CAP_SYS_MODULE`, `CAP_DAC_OVERRIDE`/
`CAP_DAC_READ_SEARCH`, `CAP_SETUID`/`CAP_SETGID`, `CAP_SYS_RAWIO`, `CAP_BPF`+`CAP_PERFMON`,
`CAP_NET_ADMIN` (in host netns), `CAP_SYS_BOOT`, `CAP_MKNOD`, `CAP_SYS_CHROOT` (escape
helper). Typical legitimate add-back for a service: `CAP_NET_BIND_SERVICE` — and even
that is obsolete if you bind ≥1024 or use systemd socket activation /
`net.ipv4.ip_unprivileged_port_start=0`.

**R5.2 — Clear the *bounding* set, not just effective/permitted**, so execve'd
children can't reacquire. Also scrub ambient capabilities.

**R5.3 — `no_new_privs` everywhere** (`prctl(PR_SET_NO_NEW_PRIVS,1)`,
`NoNewPrivileges=yes`, `securityContext.allowPrivilegeEscalation: false`): neutralizes
setuid/setgid/file-caps binaries inside the sandbox. There is almost no valid reason
for a sandboxed workload to lack it; absence is a finding.

## 6. LSMs: AppArmor / SELinux

**R6.1 — Run one MAC LSM in enforcing mode on sandbox hosts.** It's the layer that
holds when DAC and namespaces are misconfigured. SELinux (RHEL-family: containers get
`container_t` with per-instance MCS categories — sVirt — giving inter-container and
container↔host file isolation for free) or AppArmor (Debian/Ubuntu:
`docker-default`-style profile denying `/proc` and `/sys` writes, mount, ptrace peers).

**R6.2 — Never `setenforce 0` / `unconfined` to "fix" a denial.** Diagnose with
`ausearch -m AVC` / `journalctl` + `audit2allow -w`, then write a *narrow* rule.
`label=unconfined`, `apparmor=unconfined`, `:Z`-mounting whole host paths, or a
permissive-everything custom profile are findings, not fixes.

**R6.3 — LSM is your mount-scope backstop**, not your primary policy. Primary scoping
comes from mount namespaces/Landlock; LSM catches what they miss (e.g., leaked FDs,
`/proc/$pid/root` traversals).

## 7. Filesystem & misc hardening

**R7.1 — Read-only root, explicit writable tmpfs.** Rootfs mounted `ro`; writable
space is `tmpfs` with `size=`, `nosuid,nodev,noexec`, at known mountpoints (`/tmp`,
job dir). W^X at the filesystem level: nothing both writable and executable unless
the workload is a JIT (then confine the JIT dir alone).

**R7.2 — rlimits still matter inside cgroups:** `RLIMIT_NOFILE` (fd exhaustion),
`RLIMIT_CORE=0` (no core dumps of sensitive memory), `RLIMIT_FSIZE` (output bombs),
`RLIMIT_NPROC` as belt-and-braces with `pids.max`, CPU time via `RLIMIT_CPU` for
single-process jobs (cgroup `cpu.max` throttles but never terminates — you also need
a wall-clock kill, see `05` §4).

**R7.3 — Scrub inherited state across the boundary:** close all FDs except the
designed ones (`close_range(3, ~0U, 0)` or `O_CLOEXEC` discipline), reset signal
handlers/mask, empty environment then set an explicit one, `umask 077`, detach
controlling TTY (TIOCSTI/ioctl injection — use a pty pair or `TIOCSTI`-blocking
seccomp if a TTY is required).

**R7.4 — systemd as a sandbox assembler** for services: `DynamicUser=yes`,
`ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`, `PrivateDevices=yes`,
`PrivateNetwork=yes` (when no net needed), `RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6`,
`RestrictNamespaces=yes`, `LockPersonality=yes`, `MemoryDenyWriteExecute=yes`,
`SystemCallFilter=@system-service` minus `@privileged @resources @mount`,
`CapabilityBoundingSet=`, `NoNewPrivileges=yes`, `UMask=0077`. Verify with
`systemd-analyze security <unit>` — target "OK"/low exposure score; >8.0 on a
network-facing service is a finding.

## 8. Host kernel attack-surface sysctls (sandbox hosts)

**R8.1 — Baseline for any host running untrusted workloads:**

```bash
kernel.unprivileged_bpf_disabled=1      # eBPF LPEs; pair w/ JIT hardening below
net.core.bpf_jit_harden=2
kernel.yama.ptrace_scope=2              # admin-only ptrace (3 = none, if tolerable)
kernel.dmesg_restrict=1
kernel.kptr_restrict=2                  # no kernel pointers in /proc
kernel.perf_event_paranoid=3            # perf is an LPE+side-channel surface
kernel.sysrq=0
kernel.kexec_load_disabled=1
fs.protected_symlinks=1  fs.protected_hardlinks=1
fs.protected_regular=2   fs.protected_fifos=2
fs.suid_dumpable=0
vm.unprivileged_userfaultfd=0           # userfaultfd = exploit primitive
user.max_user_namespaces=<quota or 0>   # per R1.2 decision
```

**R8.2 — Module surface:** `modules_disabled=1` after boot where feasible, or at
minimum a module blocklist for ancient parsers the kernel auto-loads on demand
(dccp, sctp, rds, tipc, ax25 …) — `install <mod> /bin/false` in modprobe.d.
Lockdown mode (`lockdown=confidentiality`) where the platform supports it.

**R8.3 — These are host-wide layers, not per-sandbox substitutes.** They reduce the
kernel-LPE surface that rank-5/6 sandboxes (per `01`) expose by construction; they
do not change the boundary class.

---

## Audit checklist

- [ ] All seven namespace types unshared unless a documented need to share; host
      `/proc` never bind-mounted into PID-namespaced sandboxes.
- [ ] Userns posture decided explicitly: rootless mapping used for sandboxes AND
      unprivileged userns creation restricted on untrusted-code hosts.
- [ ] cgroup v2 budget present: `memory.max` + `swap.max=0`, `pids.max`, `cpu.max`,
      `memory.oom.group=1`; host cgroupfs not writable from inside.
- [ ] seccomp: deny-by-default allowlist (not the Docker default for high-risk
      workloads); all ABIs covered; R3.2 hard-deny set absent from allowlist;
      filter loaded after `no_new_privs`, before untrusted code.
- [ ] No design relies on seccomp filtering pointer arguments (paths).
- [ ] Landlock (or mount-ns scoping) restricts file access to enumerated paths;
      every `handled_access_fs` bit handled; fails closed on old kernels.
- [ ] Capabilities: bounding set cleared, ambient scrubbed, add-backs individually
      justified; no `CAP_SYS_ADMIN`/`CAP_SYS_PTRACE`/`CAP_BPF` for untrusted work.
- [ ] `no_new_privs` set on every sandboxed process.
- [ ] One LSM enforcing on hosts; no unconfined/permissive carve-outs without
      written justification.
- [ ] Read-only rootfs; writable mounts are size-capped tmpfs `nosuid,nodev,noexec`.
- [ ] FDs, env, signals, TTY scrubbed at the boundary; `RLIMIT_CORE=0`; wall-clock
      kill exists in addition to CPU quota.
- [ ] systemd services: `systemd-analyze security` exposure reviewed; the R7.4 set
      applied or deviations justified.
- [ ] Sandbox hosts apply the R8.1 sysctl baseline (esp. unprivileged BPF,
      userfaultfd, ptrace_scope, perf_event_paranoid) and restrict on-demand
      module autoloading; deviations documented.
