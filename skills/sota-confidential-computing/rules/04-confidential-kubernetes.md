# 04 — Confidential Kubernetes: Nodes, Pods & Confidential Containers

Scope: running confidential workloads on Kubernetes — the confidential-node vs
confidential-pod layers, the Confidential Containers (CoCo) stack (Kata TEE pods,
Trustee/KBS, agent policy, peer pods), and what changes operationally (secrets,
debugging, storage, image supply chain). This file owns only the *confidential*
layer. Control-plane/etcd/RBAC/admission/GitOps hardening is sota-kubernetes;
pod `securityContext`, seccomp and sandbox-boundary selection is sota-sandboxing
rules/01–03; TEE hardware depth is rules/02; attestation protocol depth is
rules/03; workload/threat selection is rules/01.

---

## 1. Two layers, two threat models

Kubernetes offers two distinct confidential layers. Naming them precisely is the
first audit question, because they protect against *different* adversaries.

| | Confidential **nodes** | Confidential **pods** (CoCo) |
|---|---|---|
| What it is | Whole worker node runs inside a confidential VM (SEV-SNP/TDX guest) | Each pod runs in its own TEE microVM (Kata) with a guest-side agent |
| Protects against | Cloud/infrastructure operator reading node memory; hypervisor-level snooping | All of the left column, **plus** the node OS, kubelet, node root, and the cluster admin |
| Does NOT protect against | K8s control plane, cluster admin, node root, kubelet, anything with `pods/exec` or hostPath — they are all *inside* the TEE | The pod's own code and its dependencies; side channels; availability (host can always kill the pod) |
| Trust boundary | Cloud provider excluded; cluster operator fully trusted | Cloud provider AND cluster operator excluded from the TCB |
| Attestation subject | The node VM (boot chain, firmware) | The pod's guest image, kata-agent config, agent policy, workload identity |
| Deployment friction | Near zero — a node-pool flag; workloads unchanged | Significant — RuntimeClass, guest image pull, KBS infrastructure, policy authoring, degraded debugging |

**R4.1 — Match the layer to the adversary from rules/01.** If the threat model
excludes only the *cloud provider* (data-in-use compliance, untrusted
infrastructure), confidential nodes suffice and cost almost nothing to adopt. If
it excludes the *cluster operator or platform team* (multi-party computation,
SaaS processing customer secrets, regulated data your own admins must not see),
only confidential pods deliver that — a confidential node changes nothing about
what `kubectl exec`, kubelet, or a node-root attacker can read. Selling
confidential nodes as protection from the cluster admin is a **Critical**
finding (false security claim).

**R4.2 — Confidential nodes do not attest your workload.** Node attestation
proves the *node VM* booted expected firmware/images; it says nothing about
which pods run there or what they do. Workload-bound attestation (rules/03)
requires pod-level TEEs where the evidence covers the guest image and policy.

**R4.3 — Layers compose.** CoCo pods on confidential-VM *hosts* is not
redundant: node-level encryption covers the non-CoCo system pods and kubelet
state, pod-level TEEs cover the sensitive workloads. But compose deliberately —
each layer adds attestation surface and failure modes.

---

## 2. Confidential nodes (managed offerings)

Verified against vendor docs as of this file's last-verified date; **re-verify
GA status at the provider's documentation before committing to a design.**

- **GKE Confidential GKE Nodes** — GA. Original GA on AMD SEV; AMD SEV-SNP and
  Intel TDX support is GA since GKE 1.32.2 on Standard clusters (Autopilot
  followed later, 1.35.2+), per Google's "Encrypt workload data in-use with
  Confidential GKE Nodes" docs. Enable per cluster or per node pool; machine
  series constrain which technology you get (e.g. N2D for SEV-SNP, C3 for TDX).
- **AKS confidential VM node pools** — GA on AMD SEV-SNP confidential VM sizes
  (DCasv5/ECasv5 families), per Microsoft's "Confidential VM node pools support
  on AKS" docs. Node pools of CVMs join a standard AKS cluster; guest
  attestation of the node is available.
- Other clouds/regions expose confidential-VM instance types that managed or
  self-managed node groups can use — treat "does the managed control plane
  support it" and "does the instance type exist in my region" as two separate
  verifications.

**R4.4 — Enable attestation-gated scheduling where the platform offers it, or
document that node attestation is unverified.** A confidential node whose
attestation nobody checks provides encryption-in-use but no *evidence*; that
downgrade must be a recorded decision, not an accident. (Medium)

**R4.5 — Confidential nodes change ~nothing else.** K8s Secrets, CSI volumes,
observability, `kubectl exec` all work unchanged — because the control plane is
still fully trusted. That convenience is precisely the limitation.

---

## 3. Confidential pods: the CoCo stack

**Confidential Containers (CoCo)** is a CNCF project (Sandbox maturity at the
time of writing — verify current level at cncf.io/projects before citing it in
a design review) that encapsulates each Kubernetes pod in its own TEE:

```
untrusted host (node)                      TEE guest (per pod)
┌─────────────────────────┐   ttRPC   ┌────────────────────────────┐
│ kubelet → containerd    │──────────▶│ kata-agent  ── OPA policy  │
│  └ kata shim (runtime)  │  (policy- │  ├ image-rs: pull, verify  │
│ CSI / CNI plugins       │  filtered)│  │  signatures, decrypt    │
│ sees: ciphertext pages, │           │  ├ confidential-data-hub   │
│ encrypted images, API   │           │  └ attestation-agent ──────┼──▶ Trustee
│ calls it may not issue  │           │        (evidence)          │    (KBS+AS)
└─────────────────────────┘           └────────────────────────────┘
```

Components (all under github.com/confidential-containers and the Kata
Containers project, which lives under the OpenInfra Foundation):

- **Kata Containers TEE runtime** — the pod runs in a microVM whose memory the
  host cannot read (SEV-SNP/TDX guest; see rules/02). A `RuntimeClass` (e.g.
  `kata-qemu-snp`, `kata-qemu-tdx`, platform-specific names) selects it per pod.
- **Guest image pull** — images are pulled and unpacked *inside the guest* by
  `image-rs`; a host-side snapshotter diverts the pull so the node never holds
  plaintext layers. This is load-bearing: host-side pull would hand the
  operator every byte of the image. Consequences: no node-level layer cache
  (pull cost per pod), and pod memory/disk must be sized for image contents.
- **Attestation-agent + Trustee** — the guest collects TEE evidence and sends
  it to **Trustee** (CoCo's trust-side components): the **Attestation Service
  (AS)** appraises evidence against reference values and policy; the **Key
  Broker Service (KBS)** is the relying party that releases secrets —
  image-decryption keys, sealed-secret unwrap keys, workload credentials —
  *only after* appraisal passes (the RCAR "background check" flow). This is
  the attest-then-release pattern of rules/03 applied to Kubernetes.
- **Confidential Data Hub (CDH)** — in-guest broker exposing sealed-secret
  unsealing and key-release APIs to the workload.
- **Peer pods / cloud-api-adaptor** — where you cannot run a TEE VM *on* the
  node (clouds without SEV-SNP/TDX bare-metal or child-VM support), the
  cloud-api-adaptor creates the pod VM as a sibling confidential VM via the
  cloud API instead of nesting it. Same CoCo control flow, different VM
  placement; network path and per-pod cost differ materially — verify current
  provider support in the cloud-api-adaptor repo.

**R4.6 — Nested virtualization is generally unavailable for SEV-SNP/TDX guests;
plan for bare metal or peer pods.** Classic nesting requires the host VMM to
read guest state, which is exactly what these TEEs prevent. On-prem CoCo means
Kata on bare-metal SEV-SNP/TDX hosts; in clouds it means either bare-metal
instances, a provider-specific child-VM mechanism (e.g. the SEV-SNP child VMs
of Azure's DCas_cc_v5-class sizes — though the AKS preview built on them is
retired, §6), or peer pods. A design that assumes
"CoCo on ordinary cloud VMs" is a **High** finding (it will not attest, or not
run).

### Agent policy: containing the untrusted host's API

The host talks to the pod only through the kata-agent's ttRPC API — so that API
*is* the attack surface the cluster admin retains. The **Kata agent policy**
mechanism (documented in the Kata Containers repo, "How to use the Kata Agent
Policy") closes it:

- A Rego policy document is attached to the pod; the kata-agent evaluates
  **every incoming API request** against it with an in-guest OPA engine and
  rejects anything not allowed ("blocked by policy").
- Locked-down policies deny `ExecProcess`, `ReadStream`/`WriteStream` (logs,
  stdio) and restrict container creation to the exact images, commands, mounts
  and env vars expected — so the host cannot inject a shell, exec a debug
  process, or read output.
- The policy digest is bound into the attestation evidence (e.g. on AKS the
  SHA-256 of the generated policy is the workload measurement used for secure
  key release; generic CoCo binds it via the init-data mechanism — verify the
  binding path for your platform). Trustee policy can then refuse keys to any
  pod running a weakened policy.

**R4.7 — A CoCo pod without a restrictive agent policy is not confidential from
the cluster admin.** Default-open agent APIs let the host exec into the guest —
the entire point of the layer evaporates. Generate the policy from the pod
manifest (e.g. `az confcom katapolicygen`-style tooling or CoCo's policy
tooling), pin image references by digest inside it, and verify the KBS refuses
release when the policy digest differs. Missing/permissive policy on a pod
claimed confidential: **Critical**.

---

## 4. What changes operationally

### Secrets

**R4.8 — Secrets come from the KBS after attestation, never from plain K8s
Secrets.** A K8s `Secret` lives in etcd, is readable by the control plane and
anyone with RBAC `get secrets`, and is delivered by the kubelet — three parties
your threat model just excluded. Patterns that work:

- Fetch at startup from the KBS (via CDH/attestation-agent) — the key exists
  only in TEE memory.
- **CoCo sealed secrets** — ciphertext stored as an ordinary K8s Secret,
  unsealed *inside the guest* via a KBS-released key; the control plane carries
  only ciphertext.

BAD: `envFrom: secretRef` on a confidential pod (control plane and host see
plaintext; on AKS, env vars from Secrets are additionally frozen into the
policy at deploy time). GOOD: sealed secret or in-guest KBS fetch. Plaintext K8s
Secret feeding a confidential pod's sensitive data: **High**.

### Observability and debugging

**R4.9 — Plan for deliberately degraded debugging before the first incident.**
With a locked-down agent policy there is no `kubectl exec`, no `kubectl logs`,
no ephemeral debug containers — by design. Required up front:

- A **debug variant** of the workload (policy allowing exec/logs) that the KBS
  distinguishes: debug-policy pods must receive *non-production* keys or none.
- A **break-glass procedure**: who may deploy the debug policy, where (never
  against production data), and how it is logged. Break-glass process depth is
  sota-identity-access.
- **In-guest telemetry egress**: the workload ships its own logs/metrics/traces
  to a collector over TLS, with the pipeline treating them as sensitive
  (rules/01 data-egress decisions; pipeline design is sota-observability).
  Anything the host can read (termination logs, stdio) is not available or not
  trustworthy.

No documented break-glass/debug plan for a production CoCo estate: **Medium**;
production KBS releasing prod keys to debug-policy pods: **Critical**.

### Storage

**R4.10 — Any volume mounted by the host is visible to the host.** CSI-provided
block/file volumes, hostPath, and even Secret/ConfigMap volumes traverse the
untrusted node. Rules:

- Sensitive data at rest → encrypt **in-guest** (e.g. dm-crypt/LUKS or
  application-layer encryption inside the pod) with keys released by the KBS
  after attestation. Cloud-managed disk encryption does NOT help here — its
  keys are held by the very infrastructure you distrust.
- Guest-internal ephemeral storage is memory-backed in typical CoCo
  configurations: heavy writes (including chatty logging to the container fs)
  consume pod memory and can OOM the pod — size limits accordingly (documented
  behavior on AKS CoCo).
- ConfigMap/Secret volume content and env vars may be pinned in the agent
  policy at deploy time; treat post-deploy mutation as unsupported.

---

## 5. Image supply chain interplay

**R4.11 — Move image trust decisions inside the guest.** CoCo supports
**encrypted container images** (decryption key released by the KBS only after
attestation — the registry and the node see only ciphertext) and **signature
verification inside the guest** (image-rs validates signatures against policy
before unpacking). Signing, provenance and registry hygiene are sota-devsecops;
this file adds: for a confidential workload, verification must happen *in the
TEE*, because a host-side check is a claim by the party you distrust.

**R4.12 — Admission control still applies; it just cannot see inside the TEE.**
Kyverno/Gatekeeper/ValidatingAdmissionPolicy (sota-kubernetes) still validate
the pod *spec* — RuntimeClass, annotations, image references, namespace policy
— and should enforce "pods in this namespace must use the confidential
RuntimeClass and carry a policy annotation". What admission cannot verify is
what executes inside the guest; that assurance comes from attestation + agent
policy + KBS policy. Do not let an admission-passed manifest be read as "the
workload is attested" — those are different verifiers with different evidence.

---

## 6. Choosing a deployment shape

| Requirement | Shape | Status caveat |
|---|---|---|
| Hide node memory from cloud operator, trust cluster admins | Confidential node pools (GKE Confidential GKE Nodes, AKS CVM node pools) | GA on both (verify region/machine-series support) |
| Pod-level TEE, managed, on Azure | AKS Confidential Containers (Kata + SEV-SNP child VMs) is **retired** — the preview never reached GA; Microsoft announced a March 2026 sunset with the runtime class removed. Confidential Containers on ACI (serverless, SEV-SNP, policy + secure key release) is the remaining managed option | Do not build on the retired AKS preview; verify current Azure offerings |
| Pod-level TEE on GKE | Not a managed GKE feature at time of writing (GKE's managed offering is node-level); self-managed CoCo on confidential/bare-metal nodes | Verify current GKE offerings |
| Pod-level TEE, self-managed / on-prem | CoCo operator + Kata on bare-metal SEV-SNP/TDX hosts, self-hosted Trustee | You own reference values, KBS HA, guest-image lifecycle |
| Pod-level TEE on a cloud without nesting/bare metal | CoCo peer pods (cloud-api-adaptor) on the provider's confidential VMs | Verify provider support matrix in the cloud-api-adaptor repo |
| Entire cluster (incl. control plane) shielded from the infrastructure provider | Confidential-cluster distributions that run every node in attested CVMs (e.g. Constellation, described in the Kubernetes blog "Confidential Kubernetes") | Cluster admin is still trusted — this is the node layer, cluster-wide |

**R4.13 — Preview features do not carry production confidentiality claims.**
If the platform labels the confidential feature preview/beta, the design doc
must say so and name the fallback. Compliance evidence built on a preview
feature without recorded risk acceptance: **High**.

---

## 7. Honest limitations (state these in every design doc)

- **Availability is never protected.** The host schedules, throttles, pauses,
  and kills TEE pods at will; it controls the network and the clock visible to
  the guest. Confidential computing protects confidentiality and integrity of
  memory — a malicious host can always DoS you. Any design that assumes the
  TEE guarantees liveness or timely execution is wrong (High).
- **Side channels are out of scope of the hardware guarantee.** Architectural
  side channels, controlled-channel/single-stepping attacks, and
  ciphertext-side-channel classes against SEV-SNP have published research;
  mitigations are firmware/kernel-version-dependent (rules/02). Cross-tenant
  co-residency of a TEE with attacker-controlled workloads remains a risk to
  document, not to dismiss.
- **The TCB moved, it didn't vanish.** You now trust the CPU vendor, its
  firmware/microcode supply chain, the guest kernel + kata-agent + image
  stack, your policy tooling, and Trustee. Track guest-image and CoCo-stack
  CVEs like any other base image (sota-devsecops).
- **Maturity.** CoCo is a CNCF Sandbox project at time of writing; managed
  pod-level Kubernetes offerings have been preview-labeled or retired (AKS's
  preview sunset in March 2026 without reaching GA); APIs (init-data, policy formats)
  are still evolving. Pin versions, read release notes at
  confidentialcontainers.org, and re-verify this file's status claims —
  they are the fastest-moving facts in this skill.
- **Performance/limits.** Pod startup is slower (VM boot + in-guest pull);
  memory overhead per pod is VM-sized; some K8s features (exec/logs, resource
  requests semantics, termination logs, protocol support) are restricted —
  check the platform's documented limitations list before porting a workload.

---

## Audit checklist

- [ ] Does the design state which adversary each confidential layer excludes —
      and is "protects from cluster admin" claimed only for pod-level TEEs,
      never for confidential nodes? (grep design docs for `confidential node`
      near `cluster admin`)
- [ ] Is the GA/preview status of every managed confidential feature verified
      against current vendor docs and recorded, with preview use risk-accepted?
- [ ] Do confidential pods declare a TEE RuntimeClass, and does admission
      policy enforce it for the sensitive namespaces? (`grep -r
      runtimeClassName` manifests; check Kyverno/VAP rules)
- [ ] Is a restrictive Kata agent policy attached to every confidential pod,
      generated from the manifest, denying exec/log APIs, with its digest bound
      into attestation and checked by KBS policy?
- [ ] Do secrets reach confidential pods only via attest-then-release (KBS
      fetch or sealed secrets) — no plaintext K8s Secret feeds sensitive data?
      (`grep -r "secretKeyRef\|envFrom" manifests` for confidential workloads)
- [ ] Are images for confidential pods pulled inside the guest, signature-
      verified in-guest, and (where confidentiality requires) encrypted with
      KBS-held keys?
- [ ] Is host-visible storage treated as untrusted — in-guest encryption with
      attestation-released keys for any sensitive persistent volume, and no
      hostPath into confidential pods? (`grep -r hostPath` manifests)
- [ ] Does a written debug/break-glass plan exist — debug-policy pods, KBS
      refusing production keys to them, logged approval path?
- [ ] Is in-guest telemetry egress in place (the team is not depending on
      `kubectl logs`/termination logs for a locked-down pod)?
- [ ] Are Trustee (KBS/AS) availability, reference-value updates, and policy
      change control owned and documented (rules/03 for appraisal depth)?
- [ ] Does the design doc contain the limitations block — no availability
      guarantee, side-channel posture, moved-not-removed TCB, maturity
      caveats?
- [ ] Are bare-metal/child-VM/peer-pod placement constraints verified for the
      target environment (no silent assumption that TEE VMs nest on ordinary
      cloud instances)?
