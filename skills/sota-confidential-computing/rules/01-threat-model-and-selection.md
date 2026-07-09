# 01 — Threat Model & Selection: When Confidential Computing Is the Answer

Scope: the decision layer of confidential computing (CC) — what a hardware TEE
actually defends against, what it never will, and how to decide whether a workload
needs one at all. Read this before any implementation file. This file does NOT own
TEE hardware specifics (rules/02), attestation protocol and verification (rules/03),
confidential Kubernetes (rules/04), or cryptographic PETs like FHE/MPC (rules/05).
Protecting the *host from the workload* is sota-sandboxing rules/01; key custody and
HSM/KMS design is sota-secrets-management rules/02; application-layer vulnerabilities
remain sota-code-security regardless of what hardware the app runs on.

---

## 1. Definition discipline

**R1.1 — Use the Confidential Computing Consortium definition, verbatim.**
Confidential computing is *the protection of data in use by performing computation in
a hardware-based, attested Trusted Execution Environment*. All three properties are
load-bearing: **hardware-based** (isolation enforced below the host OS/hypervisor),
**attested** (a remote party can cryptographically verify what is running and where
before trusting it), **TEE** (confidentiality *and* integrity for code and data in
use). The CCC amended the definition at the end of 2022 specifically to make
attestation explicit — a TEE you cannot attest is a trust claim you cannot check.

**R1.2 — Memory encryption alone is NOT confidential computing.**
- Intel **TME / TME-MK**: transparent full-memory encryption with SoC-held keys,
  enabled in firmware, invisible to software. No attestation, no per-workload trust
  boundary, no integrity protection. It mitigates cold-boot/bus-probing of DRAM and
  nothing else — a malicious hypervisor reads guest memory through the CPU exactly
  as before.
- **AMD SEV without SNP** (plain SEV, SEV-ES): encrypts guest memory but provides no
  memory *integrity* — a malicious hypervisor can remap and replay pages — and on
  clouds typically offers only boot-time launch attestation rather than
  guest-requestable runtime evidence. AMD SEV-SNP exists precisely to add the
  integrity and on-demand attestation-report guarantees that make "the hypervisor is
  my adversary" a defensible claim.

Rule: when the threat model includes the host/hypervisor, the floor is the
SEV-SNP/TDX class (or an equivalent attested, integrity-protected TEE). A design doc
that says "memory is encrypted, therefore confidential" is a finding (High).

**R1.3 — Attestation is what turns encrypted memory into a trust decision.**
Encryption without attestation protects data from an adversary who *isn't asked for
permission*; it does nothing against an operator who simply launches your workload
in a fake or downgraded environment. The trust chain is: hardware root of trust →
signed evidence about platform + workload measurement → verifier appraisal →
relying party decision (roles per the RATS architecture, RFC 9334). Every guarantee
in this file is conditional on that chain being *verified before secrets flow* —
mechanics in rules/03.

**R1.4 — Platform reality check (verify at use time).** AMD SEV-SNP and Intel TDX
confidential VMs are generally available on major clouds (per the Azure and Google
Cloud confidential-VM documentation; region, machine-series, and GPU support vary —
verify current availability in the provider docs). Arm CCA (Realms/RME) silicon and
software stacks are maturing, but broad public-cloud instance availability still
lags the x86 offerings (needs verification at time of use). Process-level enclaves
and GPU TEEs are rules/02 territory.

---

## 2. What CC protects against — and what it never will

In-scope vs out-of-scope below follows the CCC's own threat-vector scoping
(*A Technical Analysis of Confidential Computing*); treat deviations from it in a
vendor pitch as marketing.

### 2.1 Adversaries a properly attested TEE removes

| Adversary | How CC blocks it |
|---|---|
| **Infrastructure operator / cloud insider** | Memory encrypted with SoC-held keys; admin tooling, host debuggers, memory dumps see ciphertext |
| **Hypervisor / host OS compromise** | Hardware denies host reads/writes of TEE memory; SNP/TDX-class integrity blocks remap/replay tampering |
| **Co-tenants** (escalating through the host) | Same boundary — a tenant who owns the hypervisor still sits outside the TEE |
| **Basic physical memory attacks** | Cold boot, DRAM bus probing/interposers, DMA from devices outside the TEE hit ciphertext |
| **Impersonation of the environment** | Attestation lets the relying party refuse to release data/keys to a non-genuine or downgraded platform |

### 2.2 Threats CC explicitly does NOT address

| Non-covered threat | Why | Who owns it |
|---|---|---|
| **Bugs in the workload itself** | Attestation proves *which* code runs, not that it is *good* code; an SQLi or RCE inside the TEE executes with the TEE's trust | sota-code-security |
| **Malicious/backdoored code you attest** | Measurement of a trojan is a perfectly valid measurement; garbage in, attested garbage out | supply-chain controls, sota-devsecops |
| **Side channels** | Out of CCC scope: mitigations are split across CPU vendor, firmware, OS, and *your code* (constant-time crypto, no secret-dependent memory access). TEEs have a real history of demonstrated microarchitectural and ciphertext side-channel attacks — budget for "bounded honesty", not perfection | vendor patches + rules/02 + workload discipline |
| **Sophisticated physical attacks** | Long-term/invasive hardware access (decapping, microprobing) is out of scope | facility security, threat acceptance |
| **The TEE vendor** | The CPU vendor's silicon, microcode, and signing keys are *in* your TCB — CC moves trust from the cloud operator to the chip maker, it does not eliminate trust | vendor selection, rules/02 |
| **Availability** | The host can refuse to schedule, pause, or destroy the TEE at will; CC guarantees confidentiality/integrity, never uptime | sota-architecture resilience patterns |

**R2.1 — Name the residual TCB in the design doc.** Every CC design must state what
remains trusted: CPU vendor hardware + firmware, the attestation verification
service, the guest firmware/kernel image you measure, and every line of workload
code. "Zero trust infrastructure" with an unstated multi-million-line guest image
in the TCB is a finding (Medium).

**R2.2 — XSS in a TEE is still XSS.** Any claim that CC "secures the application"
is a category error. CC changes *who can spy on a correct program*; it does not make
an incorrect program correct. Findings that an app-layer control was skipped
"because we run confidential" are High.

---

## 3. The inverse-of-sandboxing framing

**R3.1 — State the direction of protection explicitly.**

| | Sandboxing (sota-sandboxing) | Confidential computing (this skill) |
|---|---|---|
| Protects | the **host/platform** | the **workload and its data** |
| From | the **workload** (untrusted code/input) | the **host** (operator, hypervisor, co-tenants, physical access) |
| Trust stance | workload untrusted, infrastructure trusted | workload trusted (attested), infrastructure untrusted |
| Failure of interest | escape *out* | inspection/tampering *in* |

**R3.2 — The two compose; neither substitutes for the other.** A confidential VM
running an AI agent still needs a sandbox *inside* the TEE for the code the agent
executes (boundary choice per sota-sandboxing rules/01); a perfectly sandboxed
workload on hostile infrastructure still leaks everything to the operator. When a
system both executes untrusted code and processes data the infrastructure must not
see, apply both skills to the same system and document each boundary's direction.
A review that finds a TEE used *as* the sandbox for untrusted code — with nothing
protecting the TEE contents from that code — is a finding (High).

---

## 4. The escalation ladder — pick the lowest rung that satisfies the threat model

Each rung *adds* one guarantee over the previous, at a real cost. Escalating a rung
without naming the adversary the previous rung leaves unaddressed is
architecture-by-vibes.

| Rung | Mechanism | Added guarantee | Cost / operational burden |
|---|---|---|---|
| 0 | **TLS in transit + encryption at rest** | data protected outside running systems | baseline; effectively free — always required, never sufficient against a live host adversary |
| 1 | **HSM/KMS key custody** (sota-secrets-management rules/02) | *keys* never exposed to app hosts; crypto operations isolated and audited | per-op latency/cost; key ceremony and quorum ops; protects keys, NOT the plaintext data your app decrypts into RAM |
| 2 | **Confidential VM** (SEV-SNP/TDX class) | whole-VM memory confidentiality+integrity vs host, remote attestation; lift-and-shift, no code change | small perf overhead; attestation pipeline to build and operate (rules/03); guest image is in the TCB; feature gaps vs normal VMs (e.g. live-migration/backup limits per provider docs) |
| 3 | **Process-level enclave** (SGX-class, or library-OS on CVM tech) | TCB shrinks from "guest OS + app" to "app (+ runtime)"; host *OS* also untrusted | code partitioning or library-OS constraints; smaller ecosystem; higher dev effort; side-channel discipline falls more heavily on your code (rules/02) |
| 4 | **Cryptographic PETs** (FHE, MPC, ZKP — rules/05) | no hardware trust at all; math replaces the chip vendor in the TCB | orders-of-magnitude compute overhead, narrow operation sets, specialist skills; today viable for targeted sub-computations, not general workloads |

**R4.1 — Justify the rung by adversary, in writing.** The design doc must contain a
sentence of the form: "Rung N−1 fails against ⟨adversary⟩ because ⟨mechanism gap⟩;
rung N closes it by ⟨guarantee⟩." If nobody can write that sentence, stay at the
lower rung. (Findings: unjustified rung — Medium; unjustified rung with waived
compensating controls — High.)

**R4.2 — Rungs stack, they don't replace.** A confidential VM still terminates TLS,
still fetches keys from a KMS — ideally gated on attestation ("secure key release"),
which is the canonical rung-1+rung-2 composition (rules/03).

---

## 5. Drivers that legitimately demand CC

1. **Regulated multi-party data collaboration** — parties compute over pooled data
   none of them may show the others or the infrastructure host (fraud consortia,
   clinical studies). Attestation gives every party the same verifiable claim about
   the code that touches their data.
2. **IP-sensitive models/weights on rented infrastructure** — model weights or
   proprietary algorithms deployed to a cloud, partner site, or customer premises
   where the operator must not be able to exfiltrate them.
3. **Sovereignty / jurisdictional requirements** — demonstrating that a foreign or
   third-party operator is *technically* unable to read data in use, not merely
   contractually forbidden.
4. **Untrusted edge hardware** — devices in physically accessible or third-party
   locations (retail, telco, industrial) where DRAM extraction and host tampering
   are realistic.
5. **Compliance-scope reduction arguments** — "the cloud operator is outside our
   compliance/audit scope because it cannot access data in use." This can be a real
   driver, but its force is decided by *your assessor*, not by the vendor's
   whitepaper. Rule: obtain the auditor's/regulator's written position on how CC
   affects scope *before* architecting around the assumption; an unvalidated
   scope-reduction assumption driving the design is a finding (High).

Counter-driver: if the honest answer to "who is the adversary?" is only "external
attackers and our own bugs," CC adds cost without adding a defense — rungs 0–1 plus
sota-code-security already cover that adversary.

---

## 6. Anti-patterns (instant findings)

- **Checkbox CC — attestation never verified.** Confidential VMs deployed, no
  verifier, no appraisal policy, secrets provisioned to any VM that asks. This is
  paying for encrypted RAM while trusting the operator exactly as before. (Critical)
- **Attest-nothing "confidential" deployments.** Marketing "confidential" on plain
  memory encryption (TME-only hosts, SEV without SNP) or on TEEs whose evidence is
  never consumed by any relying party. (High)
- **Secrets delivered before/independent of attestation.** Keys baked into the
  image, injected by the (untrusted!) host at boot, or released on network identity
  alone — the TEE protects data from the host while the key arrived *through* the
  host. Key release must be attestation-gated (rules/03). (Critical)
- **CC as an app-security substitute.** Skipping input validation, authz, or patching
  "because it runs in a TEE" (see R2.2). (High)
- **Double-paying for isolation nobody threat-modeled.** Enclave-in-CVM-in-dedicated-
  host stacks with no written adversary model per layer; or CC applied to a workload
  whose data the operator legitimately processes elsewhere in plaintext anyway
  (the confidentiality claim is void, the bill is not). (Medium)
- **Ignoring the availability gap.** SLA/DR designs that assume the TEE also protects
  uptime; the host can kill it at will (§2.2). (Medium)
- **Sandboxing/CC direction confusion.** Untrusted code run *inside* the TEE with the
  TEE's secrets, on the theory that "it's isolated" (see R3.2). (High)

---

## 7. Decision table: adversary → minimum mechanism

| Adversary you must defeat | Minimum mechanism (lowest sufficient rung) |
|---|---|
| Network eavesdropper | TLS (rung 0) — sota-network-security |
| Stolen disk / decommissioned hardware | Encryption at rest (rung 0) |
| App-host compromise stealing *keys* | HSM/KMS custody, keys non-exportable (rung 1) |
| Cloud operator / insider reading data **in use** | Confidential VM, attested, SNP/TDX class (rung 2) |
| Malicious **hypervisor** (read *and* tamper) | Rung 2 with memory integrity — SNP/TDX class, not plain SEV |
| Compromised **guest OS** also untrusted | Process-level enclave / minimized-TCB design (rung 3) |
| Physical DRAM attack on edge hardware (cold boot/DMA) | Rung 2 hardware, plus measured boot; sophisticated invasive attacks remain out of scope |
| Co-tenant on shared infrastructure | Rung 2 for host-mediated attacks; side channels additionally need scheduling/SMT posture (sota-sandboxing rules/01, rules/02 here) |
| **TEE vendor itself** / no hardware trust acceptable | Cryptographic PETs (rung 4, rules/05) — or split trust across vendors/parties |
| Your own buggy or malicious workload | No rung helps — sota-code-security, sota-sandboxing, supply-chain controls |

---

## Audit checklist

- [ ] Does every "confidential computing" claim rest on a hardware-based, **attested**
      TEE (CCC definition) — not on memory encryption alone (TME-only, SEV without
      SNP)? Grep design docs for `TME`, `SEV` without `SNP`, "memory encryption"
      used as a synonym for confidential.
- [ ] Is attestation evidence actually **verified by a relying party before secrets
      or data flow** (RFC 9334 roles assigned), rather than merely available?
      (Depth: rules/03.)
- [ ] Does the design doc name the adversary per R4.1 and justify the chosen rung as
      the lowest sufficient one — with each layer of any stacked isolation mapped to
      a threat?
- [ ] Is the residual TCB written down (CPU vendor, firmware, guest image, verifier,
      workload code) and is someone accountable for patching each element?
- [ ] Are out-of-scope threats explicitly handled elsewhere: workload vulnerabilities
      (sota-code-security), side channels (vendor patches + workload discipline),
      availability/DoS (resilience design), sophisticated physical attacks (accepted
      or mitigated)?
- [ ] Where the system also runs untrusted code or parses untrusted input, is there a
      sandbox boundary *inside or alongside* the TEE with its direction of protection
      documented (sota-sandboxing rules/01)?
- [ ] Are keys released only against successful attestation (no keys in images, no
      host-injected secrets)? Grep deployment code for cloud-init/user-data secret
      injection into "confidential" VMs.
- [ ] If compliance-scope reduction is a driver, is there a written assessor/regulator
      position confirming the treatment — not just vendor collateral?
- [ ] Have platform capability claims (SNP/TDX instance availability, GPU TEE support,
      Arm CCA status, provider feature limits like live migration/backup) been
      re-verified against current provider documentation rather than copied from
      older docs?
- [ ] Is there any workload paying for CC whose threat model no one can state
      (anti-pattern §6) — or any workload whose stated threat model demands CC but
      runs without it?
