# 02 — TEE Technologies: Landscape & Selection

Scope: the map of trusted-execution technologies — what each one actually guarantees,
what it does not, and how to choose between them for a given workload shape and threat
model. Threat-model taxonomy and the decision to use confidential computing at all is
rules/01; remote-attestation verification and TCB recovery depth is rules/03; running
TEEs on Kubernetes is rules/04; cryptographic alternatives (FHE/MPC/PETs) are rules/05.
General isolation-boundary ranking and Wasm-as-a-sandbox are sota-sandboxing rules/01;
this file owns only the *confidentiality-against-the-operator* layer that sandboxes do
not provide.

---

## 1. VM-level TEEs — confidential VMs (the current mainstream)

Lift-and-shift confidentiality: the whole guest VM is the TEE. The hypervisor and host
operator are outside the trust boundary. This is the default choice in 2026 — all three
major clouds ship confidential-VM offerings on this model (verify current SKU/region
support at each provider's docs).

### 1.1 AMD SEV-SNP — and why the ladder below it is insufficient

AMD shipped three generations under the "SEV" name. They are **not** interchangeable,
and the name alone in a design doc is a red flag:

| Generation | Adds | Missing | Verdict |
|---|---|---|---|
| **SEV** | Per-VM memory encryption (AES, key in the AMD-SP) | Register-state protection, memory *integrity*, runtime attestation | Insufficient: malicious hypervisor reads VMEXIT register state, replays/remaps ciphertext |
| **SEV-ES** | Encrypted CPU register state on VMEXIT | Memory integrity, runtime attestation | Insufficient: ciphertext block moves/replay and page remapping still possible |
| **SEV-SNP** | Memory **integrity** (Reverse Map Table: anti-replay, anti-remap, anti-alias — "a VM always sees the data it last wrote"), interrupt-injection protections, **remote attestation** — any relying party can request a signed report at any time | Ciphertext side channels remain (§6) | The floor for confidential computing on AMD |

Per AMD's SEV-SNP whitepaper and SNP-attestation guide: SEV/SEV-ES attestation was
*launch-time only* (guest-owner-only); SEV-SNP replaced it with runtime remote
attestation carrying measurement, guest policy, chip ID, and TCB version — the input
rules/03 depends on.

**R1.1 — "SEV" without "-SNP" is a finding (High).** Plain SEV and SEV-ES provide
encryption without integrity or runtime attestation; published attacks (unencrypted
VM state, ciphertext remapping) defeat their operator-exclusion claim. Require SEV-SNP
(introduced with 3rd Gen AMD EPYC) and verify the platform actually enables it —
`dmesg | grep -i sev` in the guest must show `SEV-SNP`, not just `SEV`.

**R1.2 — Encryption ≠ integrity ≠ attestation; a CC claim needs all three.** Apply
this test to every technology in this file: (a) is guest memory confidential against
the host? (b) can the host tamper/replay/remap without detection? (c) can a remote
party cryptographically verify what is running? A "confidential" offering missing any
leg is a hardened VM, not a TEE.

### 1.2 Intel TDX — teach the layering, not the acronym

TDX is built **on top of** a memory-encryption substrate that is *not itself*
confidential computing. Per Intel's TDX whitepaper and the Intel architecture
memory-protections documentation:

| Layer | What it is | What it is NOT |
|---|---|---|
| **TME** | Total Memory Encryption: one transparent key for all of DRAM | No per-tenant separation; protects against cold-boot/physical DRAM reads only |
| **TME-MK** (a.k.a. MKTME) | Multi-key TME: per-KeyID AES-XTS keys, assignable per VM/domain | No isolation from the hypervisor (VMM assigns keys and can map pages), no integrity, no attestation |
| **TDX** | Trust Domains: SEAM-mode TDX module + VMX, private KeyIDs reserved from the TME-MK pool, memory-integrity protection (MAC), CPU-state isolation from the VMM, remote attestation (via SGX-based quoting infrastructure) | Not available on parts that only ship TME/TME-MK |

**R1.3 — "The platform has memory encryption" is not a CC claim (finding: High if
marketed as one).** TME/TME-MK alone leaves the hypervisor fully in the TCB. Only a
TD (TDX guest) with verified attestation excludes the operator. The same logic marks
plain SEV (R1.1) and any "encrypted RAM" marketing on other platforms.

**R1.4 — TDX availability is a platform property — verify, don't assume.** TDX
shipped in Xeon Scalable parts and is GA as confidential-VM offerings at major clouds
(e.g. Azure DC/ECesv6-class on 5th Gen Xeon; GCP C3). Verify the current SKU, region,
and TDX-module version at the provider's docs at design time (latest stable).

### 1.3 ARM CCA — real architecture, trailing hardware

Arm CCA introduces *Realms* via the Realm Management Extension (RME), an optional
Armv9-A architectural feature: realm VMs isolated from the Normal-world hypervisor,
with attestation, managed by the (open-source, TF-A) RMM firmware. Linux kernel guest
support is upstream (see the kernel's arm64 Arm CCA documentation).

**R1.5 — Treat ARM CCA as "verify availability before you architect on it."** As of
mid-2026 there is no generally available CCA cloud instance; development targets Arm
Fixed Virtual Platforms (simulators), and the first announced CCA-capable cloud
silicon (e.g. Azure's Cobalt 200, announced November 2025) is in provider-internal
production with customer availability "planned" — verify current status at the
provider before committing. Designs targeting Arm today should plan the attestation
abstraction (rules/03) so CCA can slot in, not assume it exists.

---

## 2. Process-level enclaves — Intel SGX

The enclave is a protected region *inside* an untrusted process; the OS, hypervisor,
and everything else on the machine is outside the TCB. Smallest attack surface of any
option here — and the highest engineering cost.

**R2.1 — Know SGX's split status before recommending it.** Per Intel's own support
documentation: SGX is deprecated/removed on client Core CPUs (11th/12th Gen onward)
but explicitly continues on Xeon server parts, with no announced deprecation plans.
SGX is a server technology now. Historic EPC (Enclave Page Cache) limits of ~128–256MB
with brutal paging penalties are largely lifted on modern Xeon (e.g. Intel documents
up to 64GB EPC on Xeon D-1700/2700-class parts; verify per SKU), with ECDSA/DCAP
attestation replacing the retired EPID service.

**R2.2 — Unmodified apps go in via a LibOS; verify the LibOS is alive.**
- **Gramine** (formerly Graphene; a Linux Foundation project): the most established
  LibOS for unmodified Linux applications in SGX, but mainline activity has stalled —
  last release v1.9 (June 2025), and no commits or merged PRs on the main branch for
  over a year as of mid-2026. Apply the liveness check below before adopting.
- **Occlum**: maintained but noticeably less active (v0.31.0, March 2025; sparse
  commits since) — re-verify project health before adopting.
- Anything else: check the repository yourself (last release, last non-bot commit,
  open-issue triage) before betting a security boundary on it. A dead LibOS is
  unpatched TCB (finding: High).

**R2.3 — When process-level beats VM-level.** Choose SGX over a confidential VM when:
- the secret is small and the code touching it is small (keys, signing, matching
  logic): the TCB is your enclave code + LibOS, not an entire guest kernel + distro;
- you need *finer granularity than a VM* — enclave per key, per tenant, per function;
- the host itself is semi-trusted and you only need to carve out the crown jewels.

Costs you accept: porting/manifest work (even with a LibOS: syscall gaps, fork/exec
limits), EPC sizing per SKU, and the richest side-channel attack literature of any
TEE (§6) — SGX's fine-grained OS-adversary model is exactly what single-stepping
attacks exploit. A whole-app-in-enclave design usually indicates the wrong tool:
that is a confidential VM with extra steps and a bigger porting bill.

---

## 3. AWS Nitro Enclaves — a different trust model (state it honestly)

Nitro Enclaves are hardened, highly constrained VMs carved out of an EC2 parent
instance. Per AWS's own documentation: isolation of enclave vCPUs and memory is
provided by the **Nitro Hypervisor** ("the same Nitro Hypervisor technology that
provides CPU and memory isolation for EC2 instances"); the enclave has **no persistent
storage, no interactive access, no external networking** — only a local vsock to the
parent; attestation is provided by the **Nitro Security Module (NSM)**, producing
CBOR/COSE attestation documents signed by the AWS Nitro PKI, with first-class KMS
integration (key policies conditioned on enclave measurements).

**R3.1 — Do not describe Nitro Enclaves as SEV/TDX-class operator exclusion (finding:
High in any design doc that does).** There is no hardware memory encryption excluding
the infrastructure operator: the Nitro hypervisor — AWS's software/firmware — *is* the
isolation and attestation root of trust, so **AWS remains in the TCB**. AWS's security
claim is design/operational ("no mechanism for operator access"), independently
assessed in NCC Group's public 2023 Nitro System review — a strong claim, but a
different *kind* of claim than "the CPU vendor's silicon excludes the cloud operator."
If the threat model is "protect data from the cloud provider itself," Nitro Enclaves
do not address it; SEV-SNP/TDX instances do (with verified attestation, rules/03).

**R3.2 — Where Nitro Enclaves excel:** removing *your own* operators, the parent
instance's root user, and co-resident software from the TCB of a small critical
workload (key custody, PII tokenization) — with a mature attestation-to-KMS release
flow and no porting to a new ISA. Note the model is processor-agnostic (Intel, AMD,
Graviton parents). For "protect from everyone except AWS," they are often the
lowest-friction option on AWS; combine with SEV-SNP-enabled parent instances where
supported if you also want memory encryption in the stack.

---

## 4. Confidential accelerators — GPU TEEs for AI workloads

CPU-only TEEs are useless for the dominant confidential-AI use case (model weights
and prompts on GPUs) unless the accelerator extends the boundary.

**R4.1 — NVIDIA confidential computing exists on Hopper (H100) and Blackwell
datacenter GPUs — and only there (verify SKU support for anything else).** Per
NVIDIA's Hopper confidential-computing whitepaper and product documentation:
- H100 (first confidential GPU): CC mode pairs the GPU with a CPU TEE (SEV-SNP or TDX
  confidential VM); CPU↔GPU PCIe transfers go through encrypted bounce buffers
  (AES-GCM-256 in the DMA engine); on-package HBM is inside the boundary; the GPU
  produces its own **attestation** (verified via NVIDIA's attestation services/tools —
  verify current verifier tooling at NVIDIA's docs), which must be checked *in
  addition to* the CPU TEE's report (rules/03).
- Blackwell: first TEE-I/O-capable GPU; adds inline protection over NVLink and
  near-parity performance in CC mode per NVIDIA's published materials.

**R4.2 — A "confidential AI" design must name the full boundary (finding: High if
the GPU is hand-waved).** Required in the design doc: CPU TEE technology, GPU CC mode
on/off, who verifies the GPU attestation, and whether multi-GPU interconnect traffic
(NVLink) is protected on the deployed generation. "The VM is confidential" while
weights sit in an unattested GPU across an unencrypted bus is confidential theater.

---

## 5. Wasm and TEEs

Wasm runtimes as portable sandboxes — protecting the *host from the workload* — are
sota-sandboxing rules/01 territory, and Wasm alone provides zero confidentiality
against the operator. The inverted combination (Wasm module *inside* a TEE for
portability across enclave technologies) was pioneered by **Enarx**.

**R5.1 — Do not recommend Enarx as a maintained dependency (finding: Medium if a
design relies on it).** Verified against the project repository (mid-2026): last
release v0.7.1 (January 2023); subsequent commit activity is essentially automated
dependency bumps. Treat it as dormant — an important design reference, not a
supported platform. The pattern survives elsewhere (Wasm runtimes running inside
confidential VMs/containers); if a current project claims this space, apply the R2.2
liveness check before adopting.

---

## 6. Side channels and physical attacks — the honest framing

TEEs raise attacker cost; they do not make co-resident adversaries disappear. Vendors
respond to microarchitectural breaks with microcode/firmware fixes surfaced as TCB
version bumps — which is why attestation policy must track TCB levels and why TCB
recovery is a first-class operational flow (rules/03).

Attack classes to carry in every TEE threat model:

| Class | Example (verified literature) | Affects | Posture |
|---|---|---|---|
| Transient execution / speculative | Spectre-class lineage; vendor advisories per microcode cycle | All | Patched via TCB recovery; attestation must reject stale TCBs (rules/03) |
| Ciphertext side channels | CipherLeaks (USENIX Security '21) and generalized follow-up (IEEE S&P '22): deterministic XEX/XTS encryption means repeated plaintext at a fixed address yields identical ciphertext a malicious hypervisor can monitor (e.g. VMSA register state) — broke constant-time OpenSSL RSA/ECDSA; AMD bulletin AMD-SB-3021 | SEV-SNP | Software mitigations (register masking, ciphertext-hiding guidance per AMD); constant-time code alone is NOT sufficient — document residual risk |
| Interrupt / single-stepping | SGX-Step framework: attacker-controlled timer interrupts step an enclave one instruction at a time; Intel's AEX-Notify ISA mitigation (USENIX Security '23); interrupt-*counting* variants against AEX-Notify published since (2025) — the arms race is live | SGX primarily; analogues studied on VM TEEs | Assume a privileged host can observe execution granularity; avoid secret-dependent control flow, verify AEX-Notify enabled |
| SMT co-residency | Sibling-thread contention leaks | All shared-CPU | Cloud CVMs: provider-controlled (document what the provider states); own hardware: disable SMT or core-schedule per tenant, same rule as sota-sandboxing rules/01 R2.2 |
| Physical (bus interposition, chip attacks) | DRAM interposers, voltage glitching literature | All | Memory encryption raises cost substantially; a determined physical attacker with lab time is outside most cloud threat models — say so explicitly rather than claiming immunity |

**R6.1 — Side-channel posture is documented, never assumed away (finding: Medium for
absence, High for a false "TEEs stop side channels" claim).** Every CC design doc
carries a short section: which classes apply, which are mitigated by current TCB,
which are accepted residual risk, and the trigger for re-evaluation (vendor advisory
→ TCB bump → attestation policy update, rules/03).

**R6.2 — Secrets-handling code inside a TEE still follows constant-time discipline
*plus* TEE-specific guidance.** On SEV-SNP, constant-time is provably insufficient
against ciphertext side channels without the vendor-recommended mitigations; on SGX,
secret-dependent branches are readable via single-stepping. The TEE is the container,
not the crypto review.

---

## 7. Selection table

Workload shape × threat model → technology. Everything here is "(latest stable,
verify current platform support)" — SKUs, regions, and TCB baselines move.

| Workload shape | Threat: exclude cloud/infra operator | Threat: exclude co-tenant + own ops only |
|---|---|---|
| Lift-and-shift VM / whole container stack | SEV-SNP or TDX confidential VM (verify SNP not plain SEV, R1.1; verify TD not just TME-MK, R1.3) | Ordinary hardened VM + sota-sandboxing controls may suffice — do not pay the CC tax without the threat (rules/01) |
| Containers on Kubernetes | Confidential VMs as nodes, or CoCo-style pod-level CVMs — rules/04 | Standard K8s isolation (sota-kubernetes, sota-sandboxing) |
| Small critical function (key custody, signing, tokenization) | SGX enclave (Gramine for unmodified code) on Xeon, or per-function confidential VM | AWS-only: Nitro Enclaves (R3.1 trust model accepted and written down) |
| GPU inference / training on sensitive models or data | SEV-SNP/TDX CVM **plus** GPU CC mode on Hopper/Blackwell-class parts, both attestations verified (R4.2) | GPU CC mode still valuable against co-resident software; document what is and isn't in the boundary |
| Arm-based deployment | ARM CCA when actually available on your target platform (R1.5) — until then, no operator-exclusion story on Arm cloud silicon; re-scope or change ISA | Standard Arm virtualization + sandboxing |
| Portable across TEE vendors | Design to the attestation abstraction (rules/03) and a VM-shaped workload; avoid enclave-ABI lock-in | n/a |

**R7.1 — The technology choice is an output of rules/01, not of vendor preference.**
An audit asks, in order: (1) what operator/tenant is being excluded? (2) does the
chosen technology's trust model actually exclude them (R1.2, R3.1)? (3) is the
attestation of that technology verified by a relying party (rules/03)? A "yes" on
(1) with a mismatch on (2) is the defining Critical finding of this domain — e.g.
"protect from the cloud provider" implemented on Nitro Enclaves, plain SEV, or
TME-MK-only silicon.

---

## Audit checklist

- [ ] Every "SEV" reference specifies SEV-**SNP**; no design relies on plain SEV or
      SEV-ES for operator exclusion (grep design docs and IaC for `sev` without
      `snp`; check guest `dmesg` for `SEV-SNP`).
- [ ] No claim treats memory encryption alone (TME, TME-MK, "encrypted RAM") as
      confidential computing; TDX/TD attestation present where Intel is the platform.
- [ ] Any ARM CCA dependency carries a dated availability verification for the
      actual target platform, not an assumption.
- [ ] SGX designs: target is Xeon (not client CPUs); EPC sizing checked against the
      actual SKU; the LibOS's maintenance status verified within the last quarter
      (last release + non-bot commits).
- [ ] Nitro Enclaves designs state explicitly that the Nitro hypervisor/AWS is in the
      TCB, and the documented threat model does not require excluding the cloud
      operator (grep for "Nitro" near "memory encryption" — that pairing is usually
      the R3.1 misclaim).
- [ ] Confidential-AI designs name the GPU generation, CC mode status, interconnect
      protection, and GPU attestation verifier — not just the CPU TEE.
- [ ] No dependency on dormant Wasm-TEE projects (Enarx-class) without a documented
      fork/maintenance plan; project liveness checked, not assumed.
- [ ] A side-channel posture section exists: applicable classes (ciphertext,
      single-stepping, transient execution, SMT), current mitigations, accepted
      residual risk, and the advisory→TCB-bump→policy-update trigger.
- [ ] Secrets code inside TEEs reviewed for TEE-specific leakage (ciphertext side
      channels on SEV-SNP; secret-dependent control flow on SGX), not just generic
      constant-time rules.
- [ ] The technology matches the rules/01 threat model: the excluded party is
      actually outside the chosen technology's TCB, and its attestation is verified
      per rules/03.
