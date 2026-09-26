# 06 — Incident & Breach Readiness

A personal-data breach is an incident response problem with a regulatory clock
attached. The clocks are short (hours, not weeks), start at "awareness," and
assume capabilities — scope determination, affected-user enumeration, regulator
contact paths, communication drafts — that cannot be built mid-incident. Build
them now; exercise them on a schedule. Whether a specific incident is legally
reportable is a counsel/DPO decision — your job is to make that decision
possible within the clock, with facts.

## 1. Breach classification — the triage questions

**Rule:** Encode breach triage as a decision flow your IR process runs in the
first hours, producing a written record even when the answer is "not reportable."

1. **Is personal data involved?** Check the data inventory (rules/01) for the
   affected systems — this is why the inventory must answer "what data lives
   here" in minutes. No personal data → security incident path only (still
   recorded; DORA/NIS2 may still apply to significant operational incidents).
2. **What kind of breach?** Confidentiality (disclosure/access), integrity
   (unauthorized alteration), availability (loss/destruction — yes, ransomware
   encrypting personal data without exfiltration is still a personal-data breach
   under GDPR).
3. **Whose data, which regimes?** Subjects' locations + data categories →
   rules/04 triage → which clocks start (see §2).
4. **Scope:** which subjects, which fields, what period? Enumerate from logs and
   the affected store — this drives risk assessment and individual notification.
   "We can't tell who was affected" defaults to "everyone in the store" — strong
   incentive for the access logging in §3.
5. **Risk to individuals:** identity-theft potential (SSNs, financials),
   special-category exposure, credential reuse, physical safety. Mitigating
   factors that genuinely matter: data encrypted with uncompromised keys
   (this is why encryption + key custody, sota-secrets-management, can render a
   stolen disk a non-notifiable event under several regimes), tokenized values
   without vault access, provable non-access.
6. **Processor or controller?** If you're a processor, your duty is typically
   notifying the controller without undue delay (GDPR Art. 33(2)) and per
   contract — check your DPAs' notice clauses (often 24–72h contractual).

## 2. Notification clocks per regime (verify before relying — rules/04 caveats apply)

| Regime | Notify whom | Clock (as of June 2026) |
|---|---|---|
| GDPR (current law) | Supervisory authority | **72h** from awareness unless unlikely to result in risk; document even if not notified (Art. 33(5)) |
| GDPR | Individuals | Without undue delay if high risk (Art. 34) |
| GDPR — pending Digital Omnibus (NOT in force) | Authority | Proposed 96h + high-risk threshold + single EU entry point — track adoption, build to 72h today |
| HIPAA | HHS + individuals (+ media) | Individuals ≤ **60 days** from discovery; media when >500 residents of one State/jurisdiction (45 CFR 164.406); HHS contemporaneously for ≥500 individuals, else annual log ≤ 60 days after year end (164.408) |
| US state breach laws (all 50 states, separate from privacy acts) | State AGs + residents | Varies: "most expedient time" to fixed 30/45/60-day windows per state — maintain a per-state matrix via counsel |
| NIS2 (in-scope entities) | National CSIRT/authority | Early warning **24h**, notification **72h**, final report ≤ 1 month |
| DORA (EU financial) | Competent authority | Initial ≤ **4h from classifying as major** (≤ 24h from awareness), intermediate 72h, final ≤ 1 month |
| PCI DSS / card brands | Acquirer/brands | Per contract — "immediately"/24h customary; PFI investigation likely |
| Contracts (B2B DPAs) | Your customers (you as processor) | Whatever you signed — inventory these clauses; they're often your shortest clock |

**Engineering consequence:** the IR runbook embeds the clock table, regulator
submission URLs/forms, and DPA notice clauses, and the incident tracker computes
deadlines from the awareness timestamp automatically. Discovering the reporting
portal during the incident is a self-inflicted wound.

```yaml
# GOOD: clocks as config in the IR tooling — opening a privacy-class incident
# instantiates deadline tasks with owners
incident_class: personal_data_breach
awareness_at: "{{ trigger.detected_at }}"
deadlines:
  - { at: +4h,  task: "Triage complete: data categories, regimes, prelim scope", owner: ir-lead }
  - { at: +24h, task: "Counsel/DPO reportability decision recorded",            owner: dpo }
  - { at: +48h, task: "Draft regulator notification from template",             owner: dpo }
  - { at: +72h, task: "GDPR Art.33 submitted OR documented decision not to",    owner: dpo, hard: true }
  - { at: +72h, task: "Customer DPA notices sent per contract matrix",          owner: account-mgmt }
escalation: page exec sponsor at T-12h for any hard deadline not in_progress
```

```text
BAD: "Legal will tell us when to notify." Legal learns of the incident on day 4,
because the engineering bridge never paged them — the 72h clock started at the
on-call engineer's first Slack message acknowledging unusual access ("awareness"
is when the organization could reasonably know, not when the lawyer reads email).
```

## 3. Forensics-friendly logging without privacy violations

**Rule:** You need logs good enough to scope a breach (who accessed what, when,
from where) without the logs themselves becoming a PII lake (rules/01 §3 shadow
copy #1). Resolve the tension deliberately:

- **Log access events about data, not the data:** `actor, action, object type,
  object ID, purpose claim, timestamp, origin` — never field values.
  `read user=8f3a fields=[email,address] by=support-agent-12 case=4411` scopes a
  breach precisely and contains no PII payload beyond pseudonymous IDs.
- **Data-access audit logs on high-tier stores** (DB audit logging, object-store
  access logs, admin-console logs) are the difference between "3 records
  accessed" and "assume all 4M" — enable them on every `pii:special-category`
  and `financial` store; they are also a HIPAA/PCI/SOC 2 requirement.
- **Integrity & retention:** audit logs write-once (object lock / append-only
  sink), clock-synced, retained longer than app logs (1 year+ common; PCI:
  12 months, 3 months immediately available) — a *deliberate* exception in the
  retention catalog, with the legal-obligation justification recorded.
- **Pseudonymize in the pipeline:** user identifiers in security telemetry as
  stable internal IDs, never emails; redaction at the edge per sota-observability.
  Resolution ID→identity happens at investigation time, access-controlled and
  itself logged.
- **Logging is a consumer of consent too.** A log line or telemetry event that
  carries personal data is collection, so it checks the same state every
  other consumer checks (rules/03 §1): withdrawn or expired consent, a
  do-not-track or GPC opt-out, and data that may not lawfully be collected in
  the user's jurisdiction. Otherwise the log pipeline becomes the side channel
  that keeps collecting after the user said stop. Security-necessary events
  (authentication, access to data) can rest on another lawful basis; record
  that basis per event class rather than exempting logging wholesale.
  OWASP: Logging cheat sheet.
- **Don't log yourself into a breach:** secrets, session tokens, auth headers,
  and request bodies in logs both violate minimization and turn log access into
  account takeover. Treat log stores at the classification tier of the most
  sensitive thing they contain — which is the argument for keeping that tier low.

```json
// GOOD: data-access audit event — scopes a breach, leaks nothing
{ "ts": "2026-06-12T09:14:03Z", "actor": "svc:support-portal/agent:a8c1",
  "action": "read", "object": "customer/7f3e22", "fields": ["email","address"],
  "purpose": "support_ticket:4411", "origin": "10.4.2.17", "decision": "allow" }

// BAD: app log that IS the breach when the log store is popped:
// "INFO fetched user {email: 'ana@example.com', dob: '1991-02-14',
//  card_last4: '4242', session: 'eyJhbGciOi...'}"
```

## 4. Communication readiness — templates before you need them

**Rule:** Pre-draft and counsel-review skeletons for (stored with the runbook,
parameterized, in version control):

1. **Regulator notification** (per primary regime): nature of breach, categories
   and approximate counts of subjects/records, DPO contact, likely consequences,
   measures taken/proposed. GDPR explicitly allows **phased notification** when
   you don't have everything at 72h — notify with what you have, supplement;
   never blow the deadline waiting for perfect information.
2. **Individual notification:** plain language; what happened, what data, what
   you've done, what they should do (password reset, credit monitoring where
   appropriate), contact channel. No minimizing weasel-words — regulators read
   these, and "we take your privacy seriously" without facts reads as evasion.
3. **Customer/DPA notification** (processor role): facts, scope, your IR status,
   their data specifically — enterprise customers will ask for affected-record
   lists; the scoping capability in §1.4 feeds this.
4. **Status page / press holding statement.**

Decision rights matrix (who may declare a breach, who approves external comms —
counsel always in the loop) lives with the templates. Exercise the whole path in
tabletops at least annually: a scenario, real clocks, drafting from templates,
mock regulator submission. Record the exercise — it is itself audit evidence
(rules/05 §3.6).

## 4b. Preservation vs. privacy during the investigation

Forensics wants to copy everything; privacy law still applies during an
incident. Reconcile explicitly in the IR runbook:

- **Preserve narrowly:** snapshot the affected systems and relevant log windows
  under legal hold (an explicit, scoped exemption per rules/03 §4 — not "pause
  all deletion globally"). Scheduled retention jobs continue everywhere else;
  blanket deletion freezes that linger for months are themselves findings.
- **Forensic copies are classified data:** images and exports containing
  personal data inherit the highest tier present — encrypted, access-limited to
  the IR team, inventoried (yes, in the rules/01 catalog, marked
  `legal_hold:IR-2026-014`), and destroyed on case closure with a recorded
  disposition. The forensic S3 bucket that outlives the incident by three years
  is a recurring real-world breach amplifier.
- **External responders are processors:** the DFIR firm gets a DPA/appropriate
  contract before receiving data, appears in the processor map, and returns or
  destroys data at engagement end.
- **Investigation access is itself logged** (§3's audit events) — regulators ask
  who accessed subject data during the response.

## 5. Post-incident data subject & data obligations

**Rule:** Closing the incident is not closing the obligations:

- **Individual follow-through:** credit-monitoring offers honored, support
  channel staffed beyond the announcement week, DSAR spike absorbed (breach
  announcements reliably trigger access/deletion waves — your rules/03 pipeline
  takes the load).
- **Compromised-data hygiene:** force credential resets, rotate tokens/keys that
  touched the breach path (sota-secrets-management), invalidate exposed session
  artifacts; if exfiltrated data included consent or contact records, ensure
  suppression lists still hold.
- **Breach register:** every personal-data incident — including non-reportable
  ones — recorded with facts, risk assessment, decision and rationale
  (GDPR Art. 33(5) requires documenting non-notified breaches; auditors ask for
  the register).
- **Corrective-action loop:** findings become tracked engineering work with
  owners and dates; the regulator's follow-up (and your next audit) will check.
  If the breach revealed inventory gaps ("we didn't know that bucket had PII"),
  the remediation includes the rules/01 discovery fix, not just the patched
  vulnerability.
- **Re-verify deletion/retention posture:** breaches disproportionately expose
  data that should already have been deleted (rules/03 §6). "Why did we still
  have 2019 records?" is the question every post-mortem must ask — over-retention
  converts directly into breach scope and fine multipliers.

## Audit checklist

- [ ] Breach triage decision flow documented; first-hours questions (§1) answerable — test: pick a datastore, demand "what personal data, whose, which regimes" in under 30 minutes
- [ ] Clock table with regulator submission paths and DPA notice clauses embedded in IR runbook; incident tracker auto-computes deadlines from awareness time
- [ ] Processor-role obligations mapped: every customer DPA's breach-notice clause inventoried with its clock
- [ ] Data-access audit logging enabled on all special-category/financial/regulated stores; write-once, clock-synced, retention ≥ regime minimum and cataloged as a justified exception
- [ ] Security telemetry pseudonymized; no secrets/tokens/bodies in logs (sample); log stores classified and access-controlled accordingly
- [ ] Analytics/telemetry emitters that carry personal data consult current consent, opt-out (incl. GPC) and jurisdiction state before emitting; security-log event classes have a recorded lawful basis (§3) — MEDIUM. Probe for direct emitter calls to review for a consent guard: `grep -rnE "(analytics|telemetry|posthog|mixpanel|segment)\.(identify|track|capture)\(" .`
- [ ] Affected-subject enumeration capability demonstrated (query from access logs + store snapshot), not asserted
- [ ] Encryption/tokenization state per store recorded so "data was protected" claims are provable in a notification decision
- [ ] Communication templates (regulator, individual, customer, public) exist, counsel-reviewed, version-controlled; decision-rights matrix current
- [ ] Tabletop exercised within 12 months with real clocks and template drafting; record retained
- [ ] Breach register includes non-reportable incidents with documented rationale
- [ ] Legal-hold mechanism is scoped per case, not a global deletion freeze; forensic copies inventoried, access-controlled, destroyed at closure with disposition record
- [ ] External DFIR/forensics vendors covered by DPA and present in the processor map before any data flows
- [ ] Post-incident loop verified on last incident: corrective actions tracked to closure, credential rotation done, retention question asked in the post-mortem
