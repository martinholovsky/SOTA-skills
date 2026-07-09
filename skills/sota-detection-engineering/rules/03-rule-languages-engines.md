# 03 — Rule Languages & Detection Engines

Pick the engine that matches the telemetry and the behavior, then write rules
that are specific, FP-resistant, and performant. Read this when choosing between
Sigma, YARA/YARA-X, Suricata, Falco, Tetragon, or SIEM-native query languages,
or when reviewing rule quality. Defensive framing throughout: these detect and
hunt; adversary emulation (rules/06) validates them.

## 1. Engine selection

| Engine | Domain | Use when |
|---|---|---|
| **Sigma** | log events (any source) | Portable, vendor-agnostic log detections you compile to your SIEM. The default for log-based detection. |
| **YARA-X** | files, memory, malware | Classifying/matching file or memory content (samples, dropped payloads, in-memory implants). |
| **Suricata** (or Snort/Zeek) | network packets/flows | IDS/IPS, protocol anomalies, C2 signatures, payload inspection on the wire. |
| **Falco** | eBPF/syscall runtime, K8s | Container/host runtime detection with a mature rules ecosystem; CNCF graduated. |
| **Tetragon** | eBPF runtime, K8s, in-kernel enforcement | Low-overhead runtime observability + in-kernel *enforcement* (kill/block); part of Cilium. |
| **SIEM-native** (KQL/SPL/EQL/ES\|QL/Lucene) | correlation in your platform | Multi-event correlation, joins, statistics, and sequence logic that portable formats can't express. |

Rule of thumb: write log detections in **Sigma** for portability; drop to
SIEM-native only when you need correlation/sequence/stats Sigma can't model.
Use runtime engines (Falco/Tetragon) for syscall/container behavior, network
engines for the wire, YARA for content.

## 2. Sigma (+ pySigma / sigma-cli)

Sigma is a YAML format describing log detections independent of any SIEM.
**pySigma** is the current conversion library (it replaced the legacy `sigmac`
toolchain); **sigma-cli** is the CLI front-end. Backends and processing
pipelines for each target query language live as separate plugins (see the
pySigma plugin directory) to keep the core vendor-neutral. Verify current
backend/pipeline support at sigmahq.io and github.com/SigmaHQ.

Workflow: write once in Sigma → `sigma convert` with the backend + a pipeline
that maps fields to your schema (OCSF/ECS, rules/02) → deploy the generated
query. CI-validate with `sigma check`.

**Bad** (brittle, over-broad, no context):

```yaml
title: PowerShell encoded command
detection:
  sel:
    Image|endswith: '\powershell.exe'
  condition: sel
# Fires on every PowerShell launch. Pure noise; no behavior, no ATT&CK mapping.
```

**Good** (behavioral, scoped, mapped, FP-aware):

```yaml
title: Suspicious Encoded PowerShell from Office Parent
id: 9b2e... (stable UUID)
status: stable
description: Office app spawning PowerShell with an encoded command — a common
  macro-to-payload handoff.
references:
  - https://attack.mitre.org/techniques/T1059/001/
tags:
  - attack.execution
  - attack.t1059.001
logsource:
  category: process_creation
  product: windows
detection:
  selection:
    Image|endswith: '\powershell.exe'
    ParentImage|endswith:
      - '\winword.exe'
      - '\excel.exe'
      - '\outlook.exe'
    CommandLine|contains|all:
      - '-enc'
  filter_admin:                       # allowlist known-benign automation
    User|startswith: 'SVC_'
  condition: selection and not filter_admin
falsepositives:
  - Signed admin tooling launched from Office add-ins (rare; allowlisted above)
level: high
```

Quality rules: stable `id`; ATT&CK `tags`; real `logsource`; tight `selection`;
explicit `filter_*` allowlists in the `condition`; honest `falsepositives` and
`level`. Avoid single-field broad matches and regexes that are easy to evade by
trivial casing/spacing — anchor on behavior + parent/child + context.

## 3. YARA / YARA-X

YARA matches patterns in files and memory. **YARA-X** is the Rust rewrite and
the current standard: it reached **1.0 stable (June 2025)** and ships frequent
releases; legacy YARA is in **maintenance mode** (bug fixes
only, no new features). New rules target YARA-X; validate with `yr check` and
scan with `yr scan`. (Source: virustotal.github.io/yara-x, VirusTotal blog.)

**Bad** (one rotated byte defeats it; trivial Pyramid-of-Pain tier):

```
rule Bad_Hash_Only {
  condition: hash.md5(0, filesize) == "44d88612fea8a8f36de82e1278abb02f"
}
```

**Good** (structural — costs the author real rework to evade):

```
rule Suspicious_Packed_PE_With_RWX {
  meta:
    author = "soc"
    attack = "T1027.002"          // software packing
    description = "PE with RWX section and high-entropy body — likely packed"
  strings:
    $mz = { 4D 5A }
  condition:
    $mz at 0 and
    pe.number_of_sections > 0 and
    for any s in pe.sections : (
      s.characteristics & pe.SECTION_MEM_EXECUTE and
      s.characteristics & pe.SECTION_MEM_WRITE and
      math.entropy(s.raw_data_offset, s.raw_data_size) > 7.2
    )
}
```

Prefer structural/behavioral conditions (PE structure, entropy, string
combinations) over single hashes or single fixed strings. Keep conditions
performant — anchor cheap checks (`$mz at 0`) before expensive ones (entropy);
gate module use so the scan short-circuits.

## 4. Suricata / Snort (network)

Signature-based network IDS/IPS. Detail belongs to **sota-network-security**
(IDS tuning, DNS exfil, flow analysis); from a detection-engineering view:

- Prefer protocol/behavioral logic (TLS JA4 fingerprints, HTTP anomalies,
  beaconing intervals, DNS query patterns) over raw payload byte-strings, which
  encryption defeats.
- Treat `rev`/`sid` and rule metadata like code; version-control your ruleset.
- IPS (inline block) needs the same FP discipline as auto-containment (rules/04)
  — a false drop is an outage.

## 5. Falco vs. Tetragon (eBPF runtime / K8s)

Both observe kernel-level behavior via eBPF; choose by need.

- **Falco** — CNCF *graduated*; mature rules language and large community
  ruleset; rich syscall + container + K8s-audit detection; primarily *detect/
  alert*. Current line is v0.x (verify at falco.io); v0.44 removed the legacy
  (non-CO-RE) eBPF probe and gVisor engine support — older kernels need the
  kernel-module driver or an older Falco.
- **Tetragon** — part of **Cilium**; very low-overhead eBPF observability with
  **in-kernel enforcement** (it can *kill* a process or block an action in the
  kernel, not just alert), driven by `TracingPolicy` CRDs. Production-ready on
  the v1.x line (verify the current release at the Cilium/Tetragon repo).

Use Falco when you want a broad detect-only ruleset fast. Use Tetragon when you
want fine-grained process/file/network observability with optional kernel
enforcement and tight Cilium/K8s integration. They coexist.

**Falco** (good — specific behavior + exclusions, not "any exec"):

```yaml
- rule: Shell Spawned in Container by Web Server
  desc: Interactive shell launched by a web-server process inside a container —
    classic RCE-to-shell.
  condition: >
    spawned_process and container and
    proc.name in (bash, sh, zsh) and
    proc.pname in (nginx, httpd, node, python)
  output: "Shell in container (pod=%k8s.pod.name proc=%proc.cmdline parent=%proc.pname)"
  priority: WARNING
  tags: [container, mitre_execution, T1059]
```

**Tetragon** `TracingPolicy` (observe + enforce — kill on sensitive file read):

```yaml
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: block-serviceaccount-token-read
spec:
  kprobes:
    - call: "security_file_open"
      syscall: false
      args:
        - index: 0
          type: "file"
      selectors:
        - matchArgs:
            - index: 0
              operator: "Equal"
              values:
                - "/var/run/secrets/kubernetes.io/serviceaccount/token"
          matchActions:
            - action: Sigkill      # in-kernel enforcement; omit for detect-only
```

Enforcement actions (`Sigkill`/`Override`) are powerful and dangerous — pilot in
detect-only, scope by pod/namespace selectors, and treat enabling kill like
enabling IPS block (rules/04 auto-containment guardrails). K8s-specific runtime
detection content is shared with **sota-kubernetes**.

## 6. SIEM-native query languages

Use when correlation, sequencing, joins, or statistics exceed Sigma's model:

- **EQL** (Event Query Language) — sequence/ordered-event logic
  (`sequence by host.id [process where ...] [network where ...]`): ideal for
  multi-step behaviors.
- **KQL** (Sentinel/Defender), **SPL** (Splunk), **ES|QL/Lucene** (Elastic) —
  stats, joins, lookups, baselining (`| stats count by user | where count > N`).
- Keep these in version control with the same review/test rigor as Sigma. Their
  power is also their FP risk: a sloppy `join` or unbounded time window produces
  noise and crushes the cluster.

## 7. Rule quality principles (all engines)

- **Specific over broad** — anchor on behavior + context (parent/child, user,
  path, sequence), never a single broad field. "powershell.exe ran" is not a
  detection.
- **FP-resistant** — bake allowlists into the rule with comments explaining each;
  document residual FPs in the ADS doc.
- **Performant** — cheap predicates first; bounded time windows; no
  catastrophic regexes; profile expensive correlations.
- **Evasion-aware** — assume the adversary reads your rules. Don't anchor on a
  trivially changed string (a flag spelling, a filename). Anchor on the behavior
  they can't avoid.
- **Mapped & owned** — ATT&CK tags, stable ID, owner, test fixtures.

## Audit checklist

- [ ] Is each detection written in the right engine for its telemetry (Sigma for
      logs, YARA-X for files, network engine for the wire, Falco/Tetragon for
      runtime, SIEM-native only for correlation)?
- [ ] Are Sigma rules converted via pySigma/sigma-cli with a schema pipeline and
      CI-validated (`sigma check`), or hand-written per SIEM and copy-pasted?
- [ ] Are new YARA rules targeting **YARA-X** (not legacy YARA), and structural/
      behavioral rather than single-hash?
- [ ] Grep the ruleset for hash-only / single-broad-field detections — how many
      are pure IOC matches dressed as detections?
- [ ] Do Falco/Tetragon policies anchor on specific behaviors with exclusions,
      or fire on "any exec / any connection"?
- [ ] If Tetragon enforcement (`Sigkill`/`Override`) is enabled, is it scoped by
      selector and piloted in detect-only, with the same guardrails as IPS?
- [ ] Do SIEM-native queries bound their time windows and avoid unbounded
      joins/regexes that cause noise or cluster load?
- [ ] Is every rule evasion-aware (anchored on unavoidable behavior, not a
      trivially mutated string)?
- [ ] Does each rule carry ATT&CK tags, a stable ID, an owner, and test
      fixtures?
