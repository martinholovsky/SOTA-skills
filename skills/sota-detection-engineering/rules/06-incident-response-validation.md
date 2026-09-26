# 06 — Incident Response & Detection Validation

Detection without response is an alarm nobody answers; response without
validated detections is improvisation under fire. This rule covers both ends:
the IR lifecycle that turns an alert into a contained, learned-from incident,
and the adversary-emulation discipline that proves your detections actually fire
*before* a real adversary tests them for you. Read this when building IR
capability, writing playbooks, handling an incident, or setting up continuous
detection validation. Also the **AUDIT-mode entry point** alongside rules/04.

## 1. The IR lifecycle

The classic model is **PICERL** (Preparation, Identification, Containment,
Eradication, Recovery, Lessons learned). Since April 2025 the authoritative
reference is **NIST SP 800-61 Revision 3**, which reframes incident
response around the **CSF 2.0** functions — Govern, Identify, Protect, Detect,
Respond, Recover — emphasizing IR as continuous risk management woven into the
six functions rather than a standalone linear sequence (verify at
csrc.nist.gov). PICERL remains a fine operational mnemonic; map it onto the
CSF-aligned model:

- **Preparation / Govern+Identify+Protect** — the work done *before*: plan,
  roles, authority-to-contain, contacts, tooling, logging (rules/02), playbooks,
  tabletops. Most incidents are won or lost here.
- **Identification / Detect** — your detections, hunts, and deception (rules/03,
  /05) surface it; triage (rules/04) confirms scope and severity.
- **Containment / Respond** — stop the spread: isolate, disable, block, revoke.
  Short-term (stop bleeding) then long-term (sustainable lockdown).
- **Eradication / Respond** — remove the foothold: kill persistence, rotate
  compromised creds (sota-secrets-management), patch the entry vector.
- **Recovery / Recover** — restore to known-good, monitor for re-entry, validate
  the threat is gone before declaring done.
- **Lessons learned / Recover→Govern** — blameless PIR (§5) that feeds new
  detections and closes the loop back to Preparation.

## 2. Playbooks & severity classification

- **Playbooks per incident type** (account compromise, ransomware, cloud-key
  abuse, data exfil, K8s/container compromise, LLM/agent abuse) — concrete,
  step-by-step, with decision points and named roles. Distinct from a *runbook*
  (rules/04, per-alert triage); a playbook governs the whole incident.
  - **LLM/agent abuse** needs steps a generic playbook lacks. Preserve the action
    and guardrail logs first (sota-sandboxing rules/05 R4.4; rules/02 §7), then:
    disable the abused tool or connector at the broker, halt every instance of
    the agent (sota-sandboxing rules/05 R4.3, the fleet halt), rotate every
    credential the agent could reach, purge or quarantine persistent memory
    entries written during the suspect window (a poisoned memory re-injects in
    every later session — sota-code-security rules/08 §1), and roll the system
    prompt, model and guardrail configuration back to the last known-good
    version. Restoring the agent is a reviewed step, not a timeout.
    OWASP: AISVS 12.1.2; LLMSVS 8.1; DSOMM.
  - **RAG poisoning** adds four steps. Quarantine the poisoned source documents
    and delete their embeddings from every index and replica. Invalidate the
    response cache and any retrieval or semantic cache that may hold answers
    built from them. Join the retrieval logs (which chunk IDs were served to
    whom — sota-llm-engineering rules/05) against the poisoned chunk IDs to list
    the users and sessions that received tainted answers, and decide whether to
    notify them. Re-index from a verified clean source rather than deleting
    in place and hoping nothing was missed. OWASP: RAG Security cheat sheet.
- **Legacy systems get an explicit rank.** List the critical legacy systems in
  the playbooks by name and priority, with the business continuity plan's
  recovery target for each: they usually cannot be patched or rebuilt quickly,
  so containment (isolate the enclave) and recovery order must be decided in
  advance. Their compensating monitoring is rules/02 §1. OWASP: Legacy
  Application Management cheat sheet.
- **Severity classification** drives the response tier (who's paged, how fast,
  whether leadership/legal/comms engage). Define levels by business impact +
  scope + data sensitivity, agreed in advance — not argued during the incident.
- **Declare incidents decisively.** Hesitation to call an incident is a common,
  costly failure. Err toward declaring; downgrading is cheap, lost early hours
  are not.

## 3. Forensic readiness, evidence & chain of custody

You cannot collect in the moment what you didn't prepare to collect.

- **Forensic readiness** — sufficient, integrity-protected, long-retained
  telemetry (rules/02) and the ability to snapshot volatile state (memory, disk,
  container/pod, cloud resource) before it's destroyed. Cloud/container
  ephemerality is the trap: a terminated pod or scaled-down instance takes its
  evidence with it — snapshot/preserve *before* containment kills it.
- **Evidence handling & chain of custody** — for anything that may support legal
  action or attribution: record who collected what, when, from where, and every
  subsequent handoff; hash evidence on collection and verify integrity; store
  read-only with access logging. A broken chain of custody can void the evidence
  entirely.
- **Order of volatility** — capture the most ephemeral first (memory, network
  state) before the durable (disk, logs).

## 4. Containment/eradication/recovery discipline

- **Contain before you eradicate, eradicate before you recover** — but preserve
  evidence first (§3). Pulling the plug destroys memory forensics; isolate
  (network-quarantine) instead where you need the box live.
- **Scope before you eradicate.** Eradicating one host while the adversary holds
  three others just tips them off. Use the incident's correlated entities
  (rules/04) and a hunt (rules/05) to size blast radius first.
- **Rotate all potentially exposed credentials** during eradication (assume the
  adversary took everything reachable) — coordinate with sota-secrets-management.
- **Recovery requires monitoring for re-entry** — heightened detection on the
  affected entities for a defined window; adversaries commonly return.

## 5. Blameless post-incident review (PIR)

- **Blameless** — focus on systemic/process gaps, not individual fault. Blame
  suppresses the honest disclosure that makes the review useful, and the next
  incident will be hidden longer.
- **Outputs that feed the loop:** for each "we didn't detect this early enough,"
  a new detection hypothesis (rules/01); for each "the runbook was wrong," a
  runbook fix (rules/04); for each "we couldn't get the evidence," a forensic-
  readiness gap (§3). A PIR that produces no detection/process changes was
  theater.
- **Track timeline metrics** (time to detect, contain, eradicate, recover) to
  measure whether the program is improving incident over incident.

## 6. Tabletop exercises

- Walk through realistic scenarios with the actual responders before a real
  incident. Tabletops find the broken phone tree, the missing authority-to-
  contain, the playbook nobody can locate — cheaply.
- Exercise the *decisions* (who can isolate prod? who calls legal? when do we
  notify?) and the *contacts* (are they current?). Run them regularly; rotate
  scenarios to match your top threats (threat modeling) and recent intel
  (rules/05).

## 7. Detection validation via adversary emulation (for defense)

**Validation is mandatory and defensive.** You run attacker techniques against
*your own* environment to prove your detections fire and your response works —
this is purple teaming and regression testing, not offense. A detection that's
never been triggered by the real technique is unproven.

Tools (verify current status at each project):

- **Atomic Red Team** (Red Canary) — a large library of small, ATT&CK-mapped
  "atomic" tests (~1,000+ tests across 200+ techniques). Run one atomic, confirm
  the mapped detection fires. The unit-test of detections; ideal for CI
  regression (rules/01 §2). github.com/redcanaryco/atomic-red-team.
- **MITRE Caldera** (now an Apache project, apache/caldera) — automated,
  campaign-style adversary emulation: chains techniques into an end-to-end
  operation to test detection *across the kill chain*, not just per-atomic.
- **Stratus Red Team** (DataDog) — cloud-native emulation (AWS/Azure/GCP/K8s);
  emulates cloud control-plane TTPs to validate cloud-audit detections (rules/02).
  github.com/DataDog/stratus-red-team. Pairs with the cloud/K8s/identity attacks
  the sibling skills prevent.
- **Breach-and-attack-simulation (BAS)** — continuous, automated emulation
  platforms for ongoing coverage assurance.

### Purple teaming & regression

- **Purple teaming** — red (emulate) and blue (detect/respond) work *together* in
  real time: run a technique, watch whether it's detected, tune on the spot,
  re-run. The fastest way to turn coverage gaps into detections.
- **Detection regression testing** — wire atomic tests into CI so a change that
  silently breaks a detection (a renamed field, a pipeline change, rules/02)
  fails the build, not the next incident. This is the test half of detection-as-
  code (rules/01 §2).
- **Continuous coverage assessment** — schedule emulation against the ATT&CK
  techniques in your threat model and update the Navigator layer (rules/01 §5)
  with *validated* (not merely *existing*) coverage. The honest coverage map is
  the one backed by a passing emulation.

### AI-system validation

For LLM/agent systems, validate detection of the threats in **MITRE ATLAS**
(the AI-system counterpart to ATT&CK; its tactic and technique counts change
between releases — take the matrix from atlas.mitre.org, not from a remembered count) and sota-code-security rules/08: emulate
prompt-injection, tool/agent abuse, and model-exfil attempts against your own
agents and confirm runtime detections fire.

## Audit checklist

- [ ] Is there a written IR plan mapped to a maintained standard (e.g., NIST SP
      800-61r3 / CSF 2.0; check csrc.nist.gov for a newer revision), with roles, severity tiers, and authority-to-contain defined
      *before* an incident?
- [ ] Are there incident-type playbooks (account compromise, ransomware, cloud-
      key abuse, data exfil, container, LLM/agent abuse) — concrete and current?
- [ ] **LLM/agent playbook (§2) — High where an agent ships:** does it disable
      the tool, halt the fleet, rotate reachable credentials, purge memory and
      roll back the prompt/model/guardrail version? Zero files from
      `grep -rliE 'purge.{0,30}memory|roll.?back.{0,30}prompt' playbooks/`
      (point it at wherever playbooks live) means those steps are missing.
- [ ] **RAG poisoning (§2) — High where RAG ships:** does the playbook quarantine
      documents and embeddings, invalidate caches, trace recipients through
      retrieval logs and re-index from a clean source? Zero files from
      `grep -rliE 'embedding|re-?index|retrieval.?log' playbooks/` means there
      is no RAG step at all.
- [ ] **Legacy ranking (§2) — Medium (manual):** are critical legacy systems
      named and ranked in the playbooks, tied to BCP recovery targets?
- [ ] Is forensic readiness real: can you snapshot a pod/instance/memory *before*
      containment destroys it, especially for ephemeral cloud/container workloads?
- [ ] Is there a chain-of-custody process (collector, time, hashing, read-only
      storage, access logging) for evidence that may be used legally?
- [ ] Does containment preserve evidence and scope blast radius before
      eradication, and rotate all exposed credentials?
- [ ] Are post-incident reviews blameless, and do they *produce* new detections/
      runbook fixes/forensic-gap closures (not just a doc)?
- [ ] Are tabletop exercises run regularly with the real responders, exercising
      decisions and verifying contacts are current?
- [ ] Are detections **validated against the real technique** via Atomic Red
      Team / Caldera / Stratus before they're trusted? Pick 5 — how many have a
      passing emulation test?
- [ ] Is detection regression testing wired into CI so a broken detection fails
      the build?
- [ ] Is coverage continuously assessed via emulation/purple-teaming, and does
      the Navigator reflect *validated* coverage?
- [ ] For LLM/agent systems, are ATLAS-class threats (prompt injection, agent
      abuse) emulated against your own agents to validate runtime detection?
