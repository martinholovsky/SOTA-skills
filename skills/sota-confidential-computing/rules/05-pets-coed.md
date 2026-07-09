# 05 — PETs & Computing on Encrypted Data (FHE, MPC, ZKP, PSI)

Scope: cryptographic privacy-enhancing technologies that compute on encrypted or
secret-shared data with **no hardware trust anchor** — FHE, MPC/threshold schemes,
ZKPs, and the PSI/OPRF primitives behind the deployments that actually shipped.
Umbrella term: **COED** (computing on encrypted data). This file owns the
choose/deploy/audit rules for these tools and the honest cost model. It does NOT
own: TEE selection and the isolation ladder (rules/01–02), attestation (rules/03),
confidential K8s (rules/04), differential privacy and data-minimization
(sota-privacy-compliance rules/02), federated learning / DP-SGD
(sota-ml-engineering rules/07), or classical crypto — AEAD, TLS, key management
(sota-code-security rules/04 + sota-secrets-management rules/01).

---

## 1. Positioning: trust math instead of silicon — and pay for it

**R5.1 — Know what you are buying.** A TEE (rules/02) removes the host operator
from the TCB but keeps the silicon vendor, the microcode, and the attestation PKI
in it. COED removes *all* of them: confidentiality rests only on a hardness
assumption (typically lattice problems for FHE, standard assumptions for
MPC/ZKP). The price is orders of magnitude: FHE runs roughly **1,000×–1,000,000×
slower than plaintext** depending on workload — DARPA's DPRIVE program, which
funded FHE hardware accelerators, used the ~million-times figure as its baseline.
MPC pays in network rounds and bandwidth instead of CPU; ZKP pays at proving time.

**R5.2 — Decision-first triage: most "we need FHE" asks are not FHE problems.**
Before any COED design, force the requirement through this ladder:

| The actual requirement | Correct tool |
|---|---|
| "Cloud/host operator must not see the data" | TEE (rules/01 ladder) — same guarantee vs. that adversary, ~native speed |
| "Analytics output must not identify individuals" | Differential privacy / aggregation → sota-privacy-compliance rules/02 |
| "We must not hold this data at all" | Data minimization / pseudonymization → sota-privacy-compliance rules/02 |
| "Server must answer a query without learning the query" | PIR / PSI / OPRF (§5) — the one COED shape that ships at scale |
| "Two orgs must compute jointly, neither may see the other's inputs, and neither will accept a TEE vendor in the TCB" | MPC (§3) |
| "Prove a property of hidden data to a verifier" | ZKP (§4) |
| "Untrusted server computes an arbitrary function on data it may never see, no hardware trust allowed" | FHE (§2) — the narrow residual case |

A design doc that reaches for FHE without recording why a TEE or DP fails the
threat model is a **Medium** finding; if it also promises general-purpose
throughput, **High**.

**R5.3 — Real deployments illustrate the triage.** Signal's private contact
discovery runs in SGX enclaves — Signal's engineering blog explicitly lists
PSI-class approaches among the options that didn't work at their scale. When a
privacy-maximalist product picks the TEE, treat that as calibration for your own
cost-benefit, not as an anomaly.

---

## 2. FHE — fully homomorphic encryption

### 2.1 Scheme families: pick by workload shape, not by fashion

| Family | Computes | Use for | Notes |
|---|---|---|---|
| **BGV / BFV** | Exact modular-integer arithmetic (SIMD-batched) | Counting, exact aggregates, PIR lookups, database-style workloads | Apple's stack uses BFV (post-quantum 128-bit parameter sets) |
| **CKKS** | *Approximate* fixed-point/real arithmetic | ML inference, statistics, signal processing where small error is acceptable | Approximation error is a security surface — see R5.7 |
| **TFHE / CGGI (FHEW-family)** | Boolean gates and programmable lookup tables, fast bootstrapping per gate | Comparisons, branching, non-polynomial functions, small-integer logic | Complements the arithmetic families; scheme-switching combines them |

Choosing CKKS for exact money arithmetic or BFV for a comparison-heavy circuit
is a design error (Medium): the workaround circuits eat the performance budget.

### 2.2 Standardization status (verify at time of use — this moves)

- **ISO/IEC 28033** (JTC 1/SC 27) is standardizing exactly these families:
  Part 1 general, Part 2 BGV/BFV, Part 3 CKKS, Part 4 lookup-table (TFHE-style)
  evaluation, Part 5 scheme switching. As of mid-2026, Parts 1–4 are at **DIS**
  stage (Part 2 DIS voting closed April 2026) and Part 5 is a Working Draft —
  i.e., **not yet published**; publication was expected around end of 2026.
  Verify current stage at iso.org before citing it as "standardized".
- **ISO/IEC 18033-6:2019** already covers *partially* homomorphic mechanisms
  (ElGamal/Paillier-style) — sufficient for additive-only aggregation designs.
- **NIST** has no FHE competition; the **PEC (Privacy-Enhancing Cryptography)
  project** tracks FHE/MPC/ZKP/PSI and runs workshops (MPTS 2026 included a
  threshold-FHE session). Track csrc.nist.gov/projects/pec for status.
- The community **Homomorphic Encryption Security Standard**
  (HomomorphicEncryption.org) publishes the lattice-parameter tables that
  mainstream libraries encode as named security levels.

### 2.3 Libraries

Use an actively maintained, audited library (latest stable; verify maintenance
and open security issues before adopting): e.g. **OpenFHE** (C++; BGV, BFV,
CKKS, FHEW/TFHE variants, threshold FHE, proxy re-encryption) or **TFHE-rs**
(Rust; TFHE with programmable bootstrapping). Check the license before
committing: some FHE libraries ship under restricted licenses — TFHE-rs is
BSD-3-Clause-Clear and its maintainer states commercial use requires a separate
patent license — a procurement/legal gate, not just an engineering one.
Microsoft **SEAL** and Apple **swift-homomorphic-encryption** are the vendors'
own production libraries (§2.4). Writing your own scheme implementation is a
**Critical** finding outside a research context.

### 2.4 Honest performance reality

Production FHE successes are **narrow, private-lookup/PSI-shaped features**,
not general compute:

- **Apple Live Caller ID Lookup** (iOS 18): the phone sends a BFV-encrypted
  query; the server answers a spam/identity lookup via PIR without learning the
  number (open-sourced as swift-homomorphic-encryption).
- **Microsoft Edge Password Monitor**: SEAL-based HE plus an OPRF checks saved
  credentials against a breach corpus without revealing them to the server.

Common shape: tiny client-side ciphertexts, a server-side keyword/PIR lookup, a
tiny response — no deep multiplicative circuits, no encrypted training. Budget
rule: prototype with your real data sizes and measure ciphertext expansion
(often 10–1000×) and latency before committing; "we'll optimize later" is not a
plan at 4–6 orders of magnitude.

### 2.5 FHE security notes (audit anchors)

**R5.5 — Parameters ARE the security level.** Ring dimension, modulus chain,
and noise parameters jointly determine both correctness and the lattice security
level. Use the library's named standard parameter sets (128-bit+); any
hand-rolled parameter selection without a lattice-estimator analysis signed off
by a cryptographer is a **Critical** finding. Grep for custom
`ring_dim`/`poly_modulus_degree`/modulus values that differ from library presets.

**R5.6 — FHE gives confidentiality, not integrity.** Ciphertexts are malleable
*by design*; a malicious server can compute the wrong function or garbage and
the client cannot tell. If result correctness matters (payments, model outputs
acted on automatically), FHE alone is insufficient: add a verifiability layer —
ZKP over the evaluation, redundant evaluation across independent parties, or
run the evaluator inside an attested TEE (rules/02–03). An FHE design that
silently assumes an honest-but-curious server must state that assumption in the
threat model; omitting it is a **High** finding.

**R5.7 — CKKS decryption-sharing leakage (IND-CPA-D).** Li–Micciancio
(Eurocrypt 2021) showed that sharing CKKS *decrypted* results with anyone who
can also see ciphertexts leaks the noise and enables key recovery — the
IND-CPA-D model. Countermeasure is noise flooding with **worst-case** noise
estimates; Guo et al. (USENIX Security 2024) broke non-worst-case flooding with
practical key-recovery attacks. Rule: if any party other than the secret-key
holder ever observes CKKS decryptions (including "just approximate statistics"),
you need the library's IND-CPA-D-hardened decryption mode (OpenFHE documents
one) — absent that, **High**.

---

## 3. MPC and threshold cryptography

**R5.8 — Two protocol families, different cost profiles.** Conceptually:
*secret-sharing* protocols (Shamir/SPDZ-style) split every value across parties
and pay per multiplication in communication rounds — good for arithmetic on big
data among few well-connected parties; *garbled-circuit* protocols (Yao-style)
have constant rounds — good for high-latency links and boolean logic. Libraries
implement the choice; you choose the deployment topology and the trust model.

**R5.9 — The security model must be stated, not implied.**
- **Semi-honest** (honest-but-curious): parties follow the protocol but try to
  learn from transcripts. Cheap; adequate only when parties are contractually
  bound and misbehavior would be detectable/attributable out-of-band.
- **Malicious**: parties may deviate arbitrarily. Substantially more expensive;
  required when a compromised party is in the threat model.
Any MPC deployment doc that does not name its model is a **High** finding;
claiming "cryptographically private" while running semi-honest against
untrusted counterparties is **Critical**.

**R5.10 — Collusion assumptions are the whole game.** An n-of-m threshold means
security evaporates the moment `n` parties collude or are compromised by the
same actor. Parties must be *genuinely* independent: different operators,
different clouds/jurisdictions, different admin credentials. Three "parties"
that are three pods in one Kubernetes cluster under one ops team is one party
with extra steps (**Critical**). Document who operates each party and why they
won't collude; revisit at every org change.

**R5.11 — What actually deploys.** Threshold signing/custody (splitting a
signing key so no single host ever holds it — standard in digital-asset custody
and increasingly for CA/root keys), PSI (§5), and federated/private analytics
(e.g. Google's open-sourced Private Join and Compute for joint aggregate
statistics). **NIST IR 8214C — "NIST First Call for Multi-Party Threshold
Schemes" — was published in final form in January 2026**; it collects reference
material across threshold signing, PKE, key generation, threshold-FHE, and
ZKPoK (submission previews run through 2026). Track it for which
constructions gain reference status before standardizing internally.

---

## 4. ZKP — zero-knowledge proofs

**R5.12 — What ZKP adds.** Verifiable computation and credentials *without
revealing the witness*: prove "this result came from running program P on data I
won't show you", "I am over 18 / hold a valid credential", "this batch of
transactions is valid". ZKP proves integrity of a hidden computation — the
complement of FHE (confidential computation with no integrity, R5.6).

**R5.13 — SNARK vs STARK, conceptually.** SNARKs: tiny proofs and cheap
verification; older systems (Groth16-style) need a **per-circuit trusted
setup**, newer universal-setup systems need one ceremony total; pairing-based
constructions are *not* post-quantum. STARKs: no trusted setup (transparent),
hash-based and thus plausibly post-quantum, but larger proofs and costlier
verification. Choose on: who verifies (on-chain gas vs. a server), whether a
setup ceremony is operationally acceptable, and PQ posture requirements.

**R5.14 — Circuits are security-critical code; soundness bugs are silent
catastrophes.** A circuit that under-constrains one variable lets a prover
"prove" false statements — with no crash, no log line. Canonical case: the
BCTV14 proving-system flaw behind Zcash's original Sprout pool (discovered
March 2018, disclosed February 2019) would have allowed **undetectable
counterfeiting**. Treat circuits like consensus code:
- independent audit before production (**High** if missing);
- adversarial tests: attempt to prove *false* statements, not just verify true
  ones — a test suite with only honest-path tests is a **Medium** finding;
- formal/static circuit analyzers where the toolchain has them;
- use standard proof systems via maintained libraries and DSLs (latest stable;
  the ecosystem — Circom, Noir, halo2, gnark, arkworks-class tooling — moves
  fast, verify maintenance). Hand-rolled proof systems: **Critical**.

**R5.15 — Trusted-setup ceremonies are production infrastructure.** If your
system needs one: multi-party ceremony where one honest participant suffices,
transcript published, toxic waste destruction documented. Reusing another
project's setup requires verifying the circuit/parameters actually match.
An unceremonied or undocumented setup is **High**.

---

## 5. PSI / OPRF — the workhorses that actually ship

**R5.16 — Recognize the PSI/OPRF shape and use it before reaching for FHE/MPC
generality.** "Does my item appear in your set, without either side revealing
their set" covers most deployed COED: password-breach checking (Google's
Password Checkup blinds hashed credentials with an elliptic-curve OPRF —
secp224r1 exponent blinding — so Google never sees the credential and the
client never sees the corpus; Edge Password Monitor combines an OPRF with HE),
private compliance/deny-list lookups, ad-conversion measurement
(Private Join and Compute). These protocols are mature, fast enough for
production, and far simpler to audit than general FHE/MPC.

**R5.17 — PSI still leaks by design: size and intersection.** Standard PSI
reveals set sizes and which elements matched (to at least one party). If the
*cardinality* or the *match events* are themselves sensitive, you need PSI
variants (PSI-CA, PSI with associated data, unbalanced PSI) — pick the variant
against a written leakage budget, and rate-limit queries: an online PSI oracle
queried adaptively enumerates the other side's set element by element
(**High** if unthrottled).

---

## 6. Selection table and hybrids

| Goal | Reach for | Trust residue | Cost |
|---|---|---|---|
| Hide data from the compute host | **TEE** (rules/01–02) | Silicon vendor + attestation PKI | ~native |
| Same, but hardware vendors excluded from TCB | **FHE** | Lattice hardness + library correctness | 10³–10⁶× |
| Joint compute, no party sees others' inputs | **MPC** | Non-collusion of ≥ threshold parties | Network-bound, 10–1000× |
| Prove a claim without revealing the witness | **ZKP** | Circuit soundness (+ setup ceremony if SNARK) | Prover-side heavy |
| Membership lookup without revealing query/set | **PSI/OPRF** | Protocol assumptions + leakage budget | Near-production speed |
| Publishable aggregate outputs | **DP** → sota-privacy-compliance rules/02 | Epsilon budget honesty | ~native |

Hybrids worth knowing (each layer keeps its own threat model, per the
independent-layers principle in sota-sandboxing rules/01):
- **TEE + MPC**: parties each run in attested enclaves; MPC covers "we distrust
  each other", TEE covers "we distrust each host" at near-native speed.
- **FHE + ZKP**: FHE for input confidentiality, ZKP that the server evaluated
  the agreed function — patches R5.6's integrity hole.
- **TEE as FHE integrity anchor**: run the FHE evaluator inside an attested
  enclave; cheaper than ZK-verified FHE, reintroduces silicon trust for
  *integrity only* (confidentiality still rests on the math).
- **MPC/threshold for key custody of everything else**: threshold-protect the
  TEE sealing keys or the FHE secret key so no single admin can decrypt.

---

## 7. Anti-patterns (instant findings)

- Hand-rolled FHE parameters or a homemade scheme/proof system. (**Critical**)
- MPC "parties" operated by one organization/cluster/admin domain. (**Critical**)
- CKKS decryptions shared beyond the key holder without IND-CPA-D-hardened
  noise flooding. (**High**)
- FHE result trusted for integrity with no ZKP/TEE/redundancy and no recorded
  honest-server assumption. (**High**)
- MPC deployment with unstated adversary model, or semi-honest sold as
  "malicious-secure". (**High** / **Critical**)
- ZK circuit in production without independent audit or false-statement tests. (**High**)
- Unthrottled online PSI endpoint (adaptive set enumeration). (**High**)
- FHE chosen where the threat model is satisfied by a TEE or DP; no comparison
  recorded. (**Medium**)
- Citing ISO/IEC 28033 as a published standard without checking its current
  stage. (**Low**)

---

## Audit checklist

- [ ] Requirement triaged through §1 R5.2: is there a written rationale for why
      a TEE (rules/01) or DP (sota-privacy-compliance rules/02) does not satisfy
      the threat model before any FHE/MPC build?
- [ ] FHE scheme family matches workload shape (BGV/BFV exact, CKKS approximate,
      TFHE boolean/lookup) — no exact-arithmetic-on-CKKS or comparison-heavy BFV?
- [ ] All FHE parameters come from library standard/named parameter sets at
      ≥128-bit? (grep for custom `poly_modulus_degree`, `ring_dim`, modulus
      chains diverging from presets)
- [ ] Library actively maintained, latest stable, license/patent terms cleared
      (e.g. BSD-3-Clause-Clear commercial restrictions)?
- [ ] If CKKS decryptions are ever shared: IND-CPA-D-hardened decryption
      (worst-case noise flooding) enabled?
- [ ] Result-integrity story explicit: ZKP/TEE/redundant evaluation, or a
      documented honest-but-curious server assumption?
- [ ] Measured (not estimated) latency and ciphertext expansion on production
      data sizes before commitment?
- [ ] MPC: adversary model (semi-honest vs malicious) stated in the design doc
      and matched to counterparty trust?
- [ ] MPC: party operators enumerated with genuinely independent admin domains;
      collusion analysis dated and revisited on org changes?
- [ ] ZKP: standard proof system via a maintained library — no hand-rolled
      crypto? Circuit independently audited? Test suite attempts to prove FALSE
      statements?
- [ ] SNARK trusted setup: multi-party ceremony documented, transcript
      published, parameters verified to match the circuit in use?
- [ ] PSI: leakage budget written (set sizes, match events); online endpoints
      rate-limited against adaptive enumeration?
- [ ] Standards claims current: ISO/IEC 28033 stage, NIST PEC / IR 8214C
      threshold-call status re-verified, not copied from stale docs?
- [ ] DP, consent, and minimization questions routed to sota-privacy-compliance;
      DP-SGD/federated learning to sota-ml-engineering rules/07; classical
      crypto to sota-code-security rules/04?
