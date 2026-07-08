# 01 — Detection Engineering as a Discipline

Detection engineering is the practice of treating security detections as
engineered, maintained software artifacts with a lifecycle, tests, owners, and
metrics — not a pile of rules someone wrote once. Read this when standing up the
discipline, writing detection specs, mapping coverage, or auditing whether a
team *practices* detection engineering or merely accumulates rules.

## 1. The detection lifecycle

Detections are living things. Run them through a loop, not a one-shot:

```
hypothesis → build → test → deploy → tune → retire
     ▲                                          │
     └──────────── coverage gaps ───────────────┘
```

- **Hypothesis.** A falsifiable statement about adversary behavior in *your*
  environment: "An adversary with a stolen OAuth token will register a new MFA
  device (T1556.006) to persist." Name the technique, the actor capability, and
  the telemetry that witnesses it. No hypothesis → no detection.
- **Build.** Express the logic in the right engine (rules/03), scoped tightly,
  with allowlist context for known-benign.
- **Test.** Validate it fires on the real technique (adversary emulation,
  rules/06) and stays quiet on a benign baseline. Capture both as regression
  fixtures.
- **Deploy.** Ship through CI to the SIEM/engine, with a runbook and an owner.
- **Tune.** Watch FP/TP rates for a burn-in window; adjust scope, add
  corroboration, set suppressions with expiry.
- **Retire.** Delete detections that no longer map to a live threat, fire on
  decommissioned systems, or have lost the team's trust. Stale detections are
  liabilities: they generate noise and create false coverage confidence.

Audit smell: a rule repo where the newest commit is a year old and nobody can
say which detections are trusted. That's accumulation, not engineering.

## 2. Detection-as-Code (DaC)

Apply software engineering rigor to detections. Non-negotiable practices:

- **Version control.** Every detection in git. History tells you who changed
  what scope and why. Diffs are reviewable.
- **Peer review.** Detections merge via PR with a second reviewer who checks the
  ADS doc, the FP analysis, and the test. A detection one person understands is
  a bus-factor risk.
- **CI testing.** On every PR: lint/syntax-validate the rule (e.g. `sigma check`
  via sigma-cli, `yr check` for YARA-X, `falco --validate`), run it against a
  known-malicious sample (must alert) and a benign corpus (must not), and gate
  the merge on both.
- **Automated deployment.** A pipeline compiles/converts and pushes detections
  to the engine — no hand-editing rules in the SIEM console. The console is a
  read path; git is the write path.
- **Metadata as schema.** Enforce required fields (id, ATT&CK technique, owner,
  severity, data source, FP notes, test reference) via a CI schema check.

Good detection PR contents:

```
detections/identity/new_mfa_device_after_suspicious_login.yml   # the rule
tests/identity/new_mfa_device_after_suspicious_login_pos.json   # must fire
tests/identity/new_mfa_device_after_suspicious_login_neg.json   # must not
docs/ads/new_mfa_device_after_suspicious_login.md               # ADS spec
```

## 3. The ADS framework (Palantir)

The **Alerting and Detection Strategy** framework is the canonical detection
spec. Write it *before* the rule; it forces the thinking that low-FP detections
require. Sections:

- **Goal** — what malicious/anomalous behavior this detects, in plain language.
- **Categorization** — ATT&CK tactic/technique IDs (and ATLAS for AI systems).
- **Strategy abstract** — how it works at a high level: what data, what logic,
  what triggers.
- **Technical context** — the detail an analyst needs: log fields, data source
  quirks, environment specifics.
- **Blind spots & assumptions** — how an adversary defeats this, what it assumes
  is true. This is the section that separates engineers from rule-copiers.
- **False positives** — known benign triggers and how triage distinguishes them.
- **Validation** — exactly how to prove it works (the emulation test).
- **Priority** — severity and why.

(Source: github.com/palantir/alerting-detection-strategy-framework.) If a
detection has no ADS doc, in AUDIT mode that's a Medium finding: no blind-spot
analysis means no one knows how it fails.

## 4. The Pyramid of Pain

David Bianco's model ranks indicators by how much pain detecting them inflicts
on the adversary. Detect high, supplement low:

```
            ▲ TTPs ................. tough! (rewrite their playbook)
            │ Tools ................ challenging
            │ Network/Host Artifacts annoying
            │ Domain Names ......... simple
            │ IP Addresses ......... easy
            ▼ Hash Values ......... trivial (one rebuild defeats it)
```

- **Hashes/IPs/domains (IOCs):** trivially rotated. Useful for *enrichment* and
  *retro-hunting*, worthless as a primary strategy. A detection portfolio that
  is mostly hash/IP feeds is brittle by design.
- **TTPs:** behaviors the adversary must perform to achieve their goal
  (e.g. dumping LSASS, creating an IAM admin key, `kubectl exec` into a prod
  pod). Detecting these forces the adversary to change *how they operate* —
  expensive. Aim your engineering budget here.

Rule of thumb: for every IOC feed you subscribe to, ask "what TTP detection
would catch the *behavior* this IOC is a symptom of?" Build that instead.

## 5. Coverage mapping: MITRE ATT&CK + Navigator

- **ATT&CK** is the shared taxonomy of adversary tactics and techniques.
  Verify the current version at attack.mitre.org/resources/versions/ — as of
  mid-2026 the current Enterprise release is **v19** (April 2026), which split
  the former Defense Evasion tactic into **Stealth (TA0005)** and **Defense
  Impairment (TA0112)**. Pin to a version in your tooling; ATT&CK changes
  technique IDs and structure between releases, and a coverage map built on an
  old version silently misrepresents gaps.
- **Map every detection to technique IDs** in its metadata. This is what makes
  coverage measurable.
- **Use ATT&CK's structured detection objects.** v18 (Oct 2025) retired the
  free-text Detections/Data Sources in favor of machine-readable **Detection
  Strategies (DETxxxx)** and **Analytics (ANxxxx)** objects, extended to Mobile
  in v19. Map detection metadata to DET/AN IDs where applicable, and mine the
  Analytics as hypothesis fuel and a coverage cross-check.
- **ATT&CK Navigator** renders coverage as a heatmap layer (JSON). Generate it
  from your detection metadata automatically — a hand-maintained layer rots
  instantly. Color by confidence (validated vs. unvalidated vs. none), not mere
  existence; a rule that's never fired is not coverage.
- **Threat-informed prioritization.** Don't chase 100% of the matrix. Prioritize
  techniques used by adversaries who actually target your sector (threat intel,
  rules/05) and the techniques that the *other SOTA skills* tell you matter for
  your stack: cloud/K8s/identity attack paths. MITRE CTID's **INFORM** maturity
  model (updated Jan 2026) and the Center for Threat-Informed Defense's
  resources (ctid.mitre.org) give a structured way to measure and grow.

Coverage anti-pattern: optimizing for matrix cells colored green rather than for
detecting the techniques in your top threat scenarios. A green Navigator with
no validated detections of your crown-jewel attack path is a vanity metric.

## 6. Maturity & metrics

Measure the program, not activity. Useful metrics:

- **Coverage** — % of in-scope ATT&CK techniques with at least one *validated*
  detection. Distinguish "have a rule" from "proved it fires."
- **Precision (1 − FP rate)** — of alerts from a detection, how many were true.
  Low precision = noise = the detection is a defect regardless of recall.
- **MTTD (mean time to detect)** — from adversary action to alert. Measure it
  with emulation, not by waiting for real incidents.
- **MTTR / time-to-triage** — how fast an alert reaches disposition.
- **Detection-as-code health** — % of detections with tests, ADS docs, owners;
  age distribution; retirement rate.

Beware vanity metrics: total rule count, alert volume, "events processed." None
correlate with catching adversaries; high alert volume usually means the
opposite.

Maturity progression (rough): ad-hoc rules → version-controlled detections →
ATT&CK-mapped + tested → CI/CD detection-as-code with regression → continuous
validation (purple teaming, BAS) feeding the hypothesis backlog.

## 7. Concurrent siblings & owned boundaries

- **sota-observability** owns the telemetry pipeline. Detection logic consumes
  its output. Reference rules/01 (structured logging) for the schema you query
  and rules/04 (alerting/SLO) for the *plumbing* that routes your security
  alerts — you own the security *content*, not the pipe.
- **sota-threat-modeling** rules/03 (threat catalogs, STRIDE/ATT&CK/ATLAS)
  enumerates threats at design time; turn each high-priority threat into a
  detection hypothesis here.
- **sota-kubernetes** (K8s audit-log detections, admission events),
  **sota-network-security** (network IDS, DNS-exfil, flow logs), and
  **sota-identity-access** (auth anomaly, impossible-travel, MFA-fatigue) own
  the domain-specific detections; this skill owns the *discipline* that produces
  and validates them.
- **sota-code-security** rules/08 (LLM/AI security) defines the prompt-injection
  / excessive-agency threats; detecting them at runtime (and ATLAS coverage) is
  yours.

## Audit checklist

- [ ] Are detections in version control, with PR review and CI tests, or edited
      directly in the SIEM console?
- [ ] Does each detection carry required metadata (ATT&CK ID, owner, severity,
      data source, FP notes, test ref)? Enforced in CI?
- [ ] Is there an ADS (or equivalent) doc per detection, including a blind-spots
      / assumptions section?
- [ ] Pick 5 detections: how many are validated against the real technique vs.
      "written and hoped"? (`grep -L "validation" docs/ads/` to find specs with
      no validation section.)
- [ ] Is the portfolio TTP-weighted, or dominated by hash/IP/domain IOC feeds?
      (Count rules whose only condition is an IOC match.)
- [ ] Is ATT&CK pinned to a known version, and is the Navigator coverage layer
      generated from metadata (not hand-maintained)?
- [ ] Does coverage prioritization follow threat intel for the org's sector, or
      chase matrix completeness?
- [ ] Are coverage, precision, and MTTD measured? Or only vanity metrics (rule
      count, alert volume)?
- [ ] Is there a retirement process? When did a detection last get deleted?
- [ ] Hunt query for stale detections: in the rule repo, list detections whose
      last meaningful edit predates the last ATT&CK version bump and that target
      systems still in the asset inventory.
