# 03 — Remote Attestation: Verify Before You Trust

Scope: the attestation architecture (RATS roles, evidence flow, verification policy),
the attest-then-release pattern, verifier selection, measurement/reference-value
management, attested channels, and re-attestation. This file does NOT own: choosing
the TEE technology that produces the evidence (rules/02), threat-model fit (rules/01),
wiring attestation into Kubernetes pod lifecycles (rules/04), the secret store the
released keys live in (sota-secrets-management rules/02), or build-time provenance
(sota-devsecops rules/02). Remote attestation is the mechanism that makes a TEE
trustworthy to anyone outside it; a TEE without verified attestation is encrypted
memory plus a pinky promise.

---

## 1. The RATS architecture (RFC 9334) — the map for every vendor diagram

Every attestation product, however branded, decomposes into the RFC 9334 roles.
Classify a vendor's boxes into these roles first; gaps and conflations become
findings.

| Role | Does what | Trust consequence if compromised |
|---|---|---|
| **Attester** | Produces Evidence about itself (the TEE + its attestation agent) | Assumed hostile until verified — that is the point |
| **Verifier** | Appraises Evidence against Endorsements, Reference Values, and appraisal policy; emits Attestation Results | Total: a lying Verifier can vouch for anything |
| **Relying Party** | Consumes Attestation Results to make an authorization decision (release a key, admit a node, open a channel) | Total for the resources it gates |
| **Endorser** | Vouches for the Attester's capabilities — in practice the silicon vendor's certificate infrastructure (e.g. Intel PCS, AMD KDS) | Forged endorsements = fake hardware passes |
| **Reference Value Provider** | Supplies known-good values (measurements, minimum TCB versions) the Verifier compares Evidence against | Attacker-supplied "known-good" = attacker code passes |

Conceptual messages — keep these four distinct in designs and reviews:

- **Evidence** — claims the Attester signs about itself (measurements, TCB versions,
  policy flags). Raw, platform-specific, verified by nobody yet.
- **Endorsements** — the manufacturer's signed statements that this signing key
  belongs to genuine hardware (the certificate chain to the silicon vendor root).
- **Reference Values** — what the measurements *should* be.
- **Attestation Results** — the Verifier's verdict, signed by the Verifier, in a
  Verifier-neutral format (increasingly an Entity Attestation Token, RFC 9711 —
  a JWT/CWT with attestation claims).

**Two topologies (RFC 9334):**

- **Passport model** — Attester sends Evidence to the Verifier, gets an Attestation
  Result back, presents that result to Relying Parties. Scales to many Relying
  Parties; the result is a bearer-ish credential, so its validity window and
  audience matter.
- **Background-check model** — Attester hands Evidence to the Relying Party, which
  forwards it to a Verifier and acts on the returned result. The Relying Party
  never appraises Evidence itself; freshness is naturally per-transaction.

**Mapping real products onto the roles** (verify current scope at each vendor's docs):

| Product | RATS role(s) |
|---|---|
| Guest attestation agent / TEE quoting infrastructure | Attester |
| Intel Trust Authority (SaaS; attests SGX, TDX, TPM/vTPM, NVIDIA GPU workloads; formerly Project Amber) | Hosted Verifier issuing signed tokens — passport model |
| Microsoft Azure Attestation (attests SGX, VBS enclaves, TPMs; used for SEV-SNP/TDX confidential-VM guest attestation) | Hosted Verifier with customer-configurable appraisal policy |
| Confidential Containers **Trustee**: Attestation Service (AS) | Self-hosted Verifier |
| Trustee: Key Broker Service (KBS) | Relying Party + secret-release gate (background-check: KBS forwards Evidence to the AS) |
| Trustee: Reference Value Provider Service (RVPS) | Reference Value Provider |
| Veraison (open-source verifier components; started at Arm, now a Confidential Computing Consortium project) | Verifier building blocks |
| Intel PCS / AMD KDS (VCEK ← ASK ← ARK chain) | Endorser |
| Your KMS/secret store releasing keys on a valid result | Relying Party |

**R1.1 — Never let the Attester's host pick the Verifier or the Reference Values.**
The untrusted host operator must not control appraisal inputs. Verifier identity and
policy are pinned by the *workload owner* (baked into the workload or its config,
which is itself measured).

**R1.2 — Attestation Results are credentials: check signature, audience, expiry,
and replay window** like any token (token-validation depth: sota-code-security).

---

## 2. Attest-then-release — the only pattern that counts

The purpose of attestation is to gate something. The canonical enforcement point is
**key release**: the workload's data keys, API credentials, or disk-encryption keys
exist only in a broker (KBS, cloud KMS with attestation-conditioned release policy,
HSM-backed service) and are released ONLY after Evidence verifies against policy.
Storage/rotation of those secrets is sota-secrets-management rules/01–02; this rule
owns the *condition* on release.

```
BAD  (dashboard attestation):
  TEE boots → agent posts attestation to a monitoring endpoint → green tile
  on a dashboard → workload reads its secrets from a mounted file anyway.
  The attestation gates NOTHING. Disable the TEE and the system still works.

GOOD (attest-then-release):
  TEE boots with no secrets → agent obtains Evidence (nonce from broker bound
  into report data) → Verifier appraises → broker checks the Attestation
  Result against release policy → decrypts/releases the workload key into the
  attested channel → workload can now serve. No valid attestation = no key
  = workload provably cannot operate on protected data.
```

**R2.1 — Design test: turn attestation off; if the workload still functions with
production data, attestation gates nothing.** Finding severity: Critical. This is
the single most common confidential-computing deployment failure.

**R2.2 — Release keys *into* the attested identity, not near it.** Encrypt the
released secret to a public key that appears in the Evidence's report data (§3), or
deliver it over an attested channel (§6). Releasing a plaintext key over ordinary
TLS to "the pod that attested a moment ago" lets the host operator race or proxy
the release.

**R2.3 — Everything downstream of release is inside the trust boundary.** If the
released key is then written to a host-visible volume or env var, the TEE bought
nothing. Key handling inside the workload: sota-secrets-management rules/03.

**R2.4 — Fail closed.** Verifier unreachable / policy mismatch / TCB stale ⇒ no
key, workload does not start degraded. Availability mitigations are §4 (verifier
HA), never "skip attestation on timeout" (Critical).

---

## 3. What Evidence must contain — and the hard verification rules

Conceptually, every platform's Evidence carries four things (byte layouts differ —
SGX/TDX quotes, SEV-SNP attestation reports, Arm CCA realm tokens, TPM quotes):

1. **Measurement(s)** of what launched: enclave code identity (e.g. SGX MRENCLAVE /
   signer MRSIGNER) or, for VM-shaped TEEs, launch measurement of firmware +
   kernel/initrd/cmdline, extended at runtime via measurement registers/event logs.
2. **Platform TCB identity**: CPU/firmware security version numbers (SVNs),
   microcode level, platform provisioning identity.
3. **Policy/attribute flags**: debug mode, SMT allowance, migration allowance.
4. **Report data**: a caller-supplied field (64 bytes on SGX/TDX/SEV-SNP) the TEE
   signs verbatim — the hook for nonces and key binding.

Hard rules for any Verifier policy (hosted or self-written):

**R3.1 — Reject debug-mode TEEs in production. Always.** Debug attributes
(SGX ATTRIBUTES.DEBUG, TDX TD debug attribute, SEV-SNP guest policy DEBUG bit)
permit the host to inspect or single-step the TEE — Evidence signs the flag
precisely so you can refuse it. A policy that ignores the debug flag is Critical;
a dev-cluster exception must be a *different* policy on a *different* key set.

**R3.2 — Bind freshness into report data.** The Relying Party/Verifier issues an
unpredictable nonce; the Attester puts it (or a hash of nonce ‖ ephemeral public
key) in report data. Verifier checks the echo. Without this, yesterday's Evidence
from a since-compromised or since-deleted TEE replays forever. RFC 9334 allows
nonces, epoch IDs, or trusted timestamps — pick one deliberately; "none" is High.

**R3.3 — Verify the FULL certificate chain to the silicon vendor's root** (e.g.
SEV-SNP: VCEK → ASK → ARK, roots fetched from AMD KDS; SGX/TDX: PCK chain to the
Intel root via PCS), including revocation data. Pin the vendor root out-of-band —
never trust a root delivered alongside the Evidence by the host. Chain checked
only to an intermediate supplied by the platform under test: Critical.

**R3.4 — TCB status is a policy decision, not a boolean.** Intel-style appraisal
yields graded statuses (`UpToDate`, `SWHardeningNeeded`, `ConfigurationNeeded`,
`OutOfDate`, `Revoked`, and combinations); AMD binds the VCEK to the reported TCB
version. Policy must enumerate what each grade means for *this* workload:

| TCB status class | Default posture |
|---|---|
| Up to date | Release |
| Hardening/configuration needed | Release + alert + tracked remediation deadline |
| Out of date | Deny for new secrets; time-boxed grace for running fleet during TCB recovery (§5) |
| Revoked | Deny, revoke previously released keys, page (security incident) |

Silently accepting `OutOfDate`/`Revoked` because "the demo broke": Critical.

**R3.5 — Verify measurements against expected values, not against "signature
valid".** A genuine TEE running attacker code produces perfectly signed Evidence.
Signature validity authenticates the *platform*; reference values authenticate the
*workload*. Policies that stop at "quote verifies" are High.

---

## 4. Choosing a Verifier: hosted vs self-hosted

| Dimension | Hosted service (e.g. Intel Trust Authority, Azure Attestation) | Self-hosted (e.g. Trustee AS, Veraison-based) |
|---|---|---|
| Endorsement plumbing (vendor cert caching, TCB info) | Managed for you | You operate collateral caching/refresh |
| Trust | Verifier operator can vouch falsely — you trust the vendor/cloud with the verdict | Verdict stays in your trust domain; you must trust your own code + ops |
| Cloud-operator independence | Attesting a cloud TEE via the *same* cloud's verifier weakens the "protect from the cloud operator" story — acceptable only if that's not your threat (rules/01) | Independent of the infrastructure operator |
| Policy expressiveness | Vendor's policy language, per-tenant policies | Arbitrary; you own correctness of appraisal logic |
| Availability coupling | Attestation (and thus key release, boot, scale-up) depends on an external endpoint — model outage = cannot start workloads | You own HA; run the verifier redundantly, *outside* the fleet it attests |
| Air-gapped / sovereignty | Usually excluded | The only option; plan offline endorsement/reference-value sync |
| Audit | Verify what evidence the service actually checked (some publish audit/"faithful verification" artifacts) | Full transcript available |

**R4.1 — Whoever runs the Verifier can impersonate every attested workload's
trustworthiness.** Choose it with the same care as a root CA; log every verdict.

**R4.2 — Never run the Verifier/KBS on infrastructure the attestation is supposed
to distrust** (e.g. Trustee KBS as an ordinary pod on the same untrusted cluster
whose nodes it attests — the host operator can substitute its results). Run it in
a separately trusted domain, or itself inside an independently attested TEE. (High)

**R4.3 — Verifier availability is a tier-0 dependency.** Fresh nodes cannot join
and restarts cannot fetch keys during a verifier outage. HA-deploy it, monitor it,
and rehearse outage: the correct behavior is "cannot start new", never "start
unverified".

---

## 5. Measurements, reference values, and TCB recovery

**R5.1 — Two valid strategies for reference values; pick per workload:**
- **Golden-value pinning**: exact expected measurement(s), rotated on every
  release. Strongest; operationally heavy — every kernel/initrd/enclave rebuild
  is a reference-value update, and a missed update is an outage (key release
  fails closed).
- **Policy-based verification**: appraise structured claims (signer identity +
  minimum SVN + attribute constraints) instead of one hash — e.g. "signed by our
  release key, version ≥ N, debug off". Survives rebuilds; only as strong as the
  signing discipline behind it.

**R5.2 — Reference values must come from the build system, not from a "known-good"
deployment.** Measuring a running instance and pinning that hash launders whatever
was running into policy. Reproducible builds (sota-devsecops rules/02, rules/04)
let CI compute the expected measurement from source and publish it, signed, to the
Reference Value Provider (Trustee's RVPS; CoRIM is the emerging IETF interchange
format for reference values — still an Internet-Draft, verify status at the IETF
datatracker before standardizing on it).

**R5.3 — Build attestation and runtime attestation are complementary; you need
BOTH.** SLSA provenance proves how an artifact was *built* (sota-devsecops
rules/02); remote attestation proves what is *running now* on trustworthy
hardware. Provenance without RA can't see what the host actually launched; RA
without provenance verifies a measurement nobody can trace to reviewed source.
The reference-value pipeline is the join point.

**R5.4 — Plan TCB recovery before the first security event forces it.** Vendor
microcode/firmware updates raise SVNs and change TCB grades; platform-side updates
can change launch measurements. On a TCB recovery event, un-updated machines drop
to `OutOfDate` (or worse). Have, in advance: (a) a rehearsed fleet update +
re-attestation path; (b) reference-value/policy rotation with dual-validity
windows so old+new coexist during rollout; (c) an explicit, time-boxed,
risk-signed grace policy for degraded grades (R3.4); (d) monitoring for grace
expiry. Discovering this process during an embargoed CVE weekend is the
predictable failure mode. No documented TCB-recovery plan: High.

---

## 6. Attested channels (RA-TLS)

Attestation must be cryptographically bound to the channel that subsequently
carries secrets, or a machine-in-the-middle can splice a verified TEE's identity
onto its own connection.

**R6.1 — Bind the channel key into the Evidence.** Pattern: the TEE generates an
ephemeral TLS keypair *inside* the enclave/TD, puts the public key's hash in
report data, and presents Evidence with (or embedded in) its certificate; the peer
verifies Evidence and that the TLS key matches report data. Attestation and
channel are now the same identity. Trustee's KBS protocol (RCAR) achieves the same
binding at the application layer: the response key is attested, and secrets are
encrypted to it.

**R6.2 — Attestation over one channel + secrets over another = splice risk.**
Any design where the verified key and the delivery channel key are unrelated is
High.

**R6.3 — Standardization is in progress — say so in your design docs.** The IETF
has chartered the SEAT (Secure Evidence and Attestation Transport) working group
to standardize attestation in (D)TLS 1.3 (successor to the individual
draft-fossati-tls-attestation line), but as of mid-2026 no standard is published —
treat every RA-TLS implementation as a project-specific profile (TEE SDKs and confidential-container/K8s stacks ship
their own; verify each project's current mechanism at its docs). Interop between
two vendors' "RA-TLS" is not implied. Plain-TLS trust anchors and PKI hygiene:
sota-network-security.

---

## 7. Freshness, revocation, and monitoring

**R7.1 — Attestation is point-in-time.** It proves state at Evidence-generation;
it does not detect later runtime compromise *inside* the TEE. Re-attest on:
restart (always), key rotation / lease renewal (make releases leased, not
perpetual — align with sota-secrets-management rules/01 dynamic-secret TTLs),
policy or reference-value change, TCB recovery events, and a fixed schedule.
"Attested once at deploy, trusted for the pod's lifetime (weeks)" is Medium-High
depending on data sensitivity.

**R7.2 — Wire attestation verdicts into detection** (sota-detection-engineering
rules/01, rules/04). Alert on: any appraisal failure in prod (someone or something
launched a non-conforming image — treat as a security signal, not an ops blip),
debug-flagged Evidence, TCB-grade downgrades, Evidence from unknown platforms,
verifier policy changes, and grace-window expiry. Log full appraisal transcripts
(evidence hash, policy version, verdict, TCB grade) for forensics.

**R7.3 — Revocation must propagate to already-released secrets.** When a
measurement is retired (vuln in the image) or a platform is revoked, rotating
the reference values only stops *future* releases; previously released keys must
be rotated/revoked too. This is why leases (R7.1) beat one-shot release.

---

## Audit checklist

The first four questions catch the failure that voids everything else: attestation
that gates nothing.

- [ ] Does anything actually *consume* the Attestation Result? Trace one secret
      end-to-end: named broker/KMS releases it only on a valid, fresh result
      (grep for the release policy; a dashboard/metrics sink is not a consumer).
- [ ] Kill test documented: with attestation disabled or the verifier down, does
      the workload provably fail to obtain production secrets (fail closed)?
- [ ] Are secrets absent from the image, host env, and mounted volumes before
      attestation succeeds? (grep manifests for env/volume-injected prod secrets
      alongside "attestation" — coexistence is the tell.)
- [ ] Is the released secret bound to the attested identity (encrypted to a key in
      report data, or delivered over an RA-bound channel), not sent over ordinary
      TLS to whoever asked?
- [ ] Every deployment box mapped to a RATS role (Attester / Verifier / Relying
      Party / Endorser / RVP), with topology (passport vs background-check) named
      and result-token audience/expiry/replay handling stated?
- [ ] Does verification policy explicitly reject debug-mode Evidence in prod?
      (grep policy for the platform's debug attribute; absence of any debug check
      is the finding.)
- [ ] Fresh nonce or channel-key hash bound into report data and checked by the
      Verifier (grep for report_data / REPORT_DATA / runtime-data handling)?
- [ ] Certificate chain verified to a pinned silicon-vendor root with revocation,
      roots obtained out-of-band from the vendor (not from the attested host)?
- [ ] TCB status handled as graded policy (each grade → release/alert/deny with
      deadlines), never a silent boolean accept?
- [ ] Measurements compared to reference values sourced from the build pipeline
      (reproducible builds / signed by CI), not fingerprinted from a running
      instance; SLSA provenance and runtime attestation both present and joined?
- [ ] Verifier trust and placement justified: not operated by the party being
      distrusted, HA-deployed, every verdict logged?
- [ ] Written TCB-recovery runbook: fleet re-attestation path, dual-validity
      reference-value rotation, time-boxed signed grace windows, expiry alerts?
- [ ] Re-attestation triggers defined (restart, lease renewal, policy change,
      schedule) and secret releases leased rather than perpetual?
- [ ] Attestation failures, debug-flag sightings, and TCB downgrades alert into
      the SOC as security signals, with appraisal transcripts retained?
