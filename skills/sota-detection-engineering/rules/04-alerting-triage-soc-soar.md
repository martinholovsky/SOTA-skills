# 04 — Alerting, Triage, SOC & SOAR

A detection that fires is useless until a human (or trusted automation) acts on
it correctly and quickly. The SOC is where detections become outcomes — and
where most programs fail, by drowning analysts in noise until they stop looking.
Read this when designing alert flow, fighting alert fatigue, tuning, assigning
severity, enriching/correlating, writing runbooks, building SOAR automation, or
auditing SOC effectiveness.

Boundary: **sota-observability rules/04 owns the alerting *plumbing*** (routing,
paging, dedup transport, on-call rotation, SLO burn-rate alerts for ops). This
rule owns the *security* content riding that plumbing: which security signals
page, how they're triaged, and how the SOC stays sane.

## 1. Alert fatigue is the dominant failure

The single most common reason a SOC misses a real attack: the true positive was
one of 9,000 alerts that day and nobody looked. Treat signal-to-noise as the
program's primary health metric.

- **A chronically ignored alert is a Critical defect**, not a backlog item. If
  analysts mute, auto-close, or skip a detection, it is providing negative value
  (consuming attention, creating false confidence). Fix or retire it.
- **Precision over recall at the alert tier.** A detection at 5% true-positive
  rate trains analysts to ignore it — including the one time it's real. Move
  low-precision logic to *hunting* (rules/05) or add corroboration; don't page
  on it.
- **Measure it.** Alerts/analyst/shift, % auto-closed, % actioned, time-to-
  triage. Rising volume with flat true positives means the SOC is getting worse,
  not busier.

## 2. Tuning & suppression — always with expiry

Tuning is continuous, not a launch task.

- **Tune by adding context, not by deleting detections.** Scope tighter, add
  allowlists for known-benign (with comments), require corroboration. Preserve
  the detection's intent.
- **Suppressions MUST expire.** A permanent suppression is a silent blind spot
  that outlives the reason it was created. Every suppression carries an owner,
  a reason, and an expiry date; on expiry it's re-reviewed, not auto-renewed.

```yaml
# suppression with mandatory expiry — never "forever"
suppression:
  detection_id: 9b2e-...
  reason: "Backup job svc_backup triggers T1003 LSASS-read FP; ticket SEC-412"
  scope: { host: bkp-01, user: svc_backup }
  owner: alice
  expires: 2026-09-01        # re-review, do not auto-extend
```

Audit smell: suppressions with no `expires`, or a suppression list longer than
the detection list. Both mean the SOC is silencing rather than tuning.

## 3. Severity & priority

Assign severity honestly and consistently; inflation is as harmful as noise.

- Base severity on **impact × confidence × asset criticality**, not on how scary
  the technique sounds. A high-confidence detection on a crown-jewel system
  outranks a low-confidence detection on a sandbox.
- Reserve the top severity (page-a-human-now) for signals that are both
  high-confidence and high-impact. If everything is Critical, nothing is.
- Enrich severity dynamically: the same detection on a production identity-provider
  host is higher priority than on a test VM. Asset/identity context (below)
  drives this.

## 4. Enrichment

Every alert should arrive *pre-investigated* so triage is seconds, not a
research project. Auto-attach:

- **Asset context** — what is this host/account/resource, who owns it, how
  critical, is it internet-facing.
- **Identity context** — user role, privilege level, recent auth behavior,
  whether the account is service vs. human (feeds sota-identity-access
  anomaly detections).
- **Threat-intel context** — is this IP/domain/hash known-bad, and from which
  actor (rules/05 TI). TI is enrichment, not the detection.
- **Related signals** — other alerts on the same entity in the window.

Enrichment is what lets an analyst (or SOAR) decide in one screen. Unenriched
alerts force per-alert manual lookups — a hidden multiplier on triage time.

## 5. Deduplication & correlation

Raw detections produce many events per real incident. Collapse them:

- **Deduplicate** identical/near-identical alerts into one case with a count.
- **Correlate** related signals on the same entity/time window into a single
  incident (the "alert storm = one breach" pattern). EQL sequences or SIEM
  correlation rules (rules/03 §6) build these.
- **Aggregate to risk** where supported: many low-confidence signals on one
  entity crossing a risk threshold becomes one high-confidence alert (risk-based
  alerting) — turns noise into signal instead of suppressing it.
- **Correlate identity across layers.** Map the human user, the service or
  workload identity (service account, SPIFFE ID, cloud role) and the device to
  one entity so an IdP sign-in, the API calls it led to and the pod that made
  them land in one case. Feed two supply-chain signals in as runtime detection
  inputs, not only as build-time gates: an image that fails signature
  verification or whose digest does not match its signed manifest (an admission
  denial or policy report), and a vulnerability finding marked *reachable* on a
  workload that is running. Either one raises the risk of every other alert on
  that workload. OWASP: Zero Trust Architecture cheat sheet.

The analyst should see *incidents*, not a firehose of atomic events.

## 6. Runbooks — every alert, no exceptions

**No actionable alert reaches a human without a runbook.** The runbook answers:
what does this detection mean, what's the blast radius, how do I confirm TP vs.
FP, what are the first containment steps, who/when to escalate. Link it from the
alert payload.

- Wire the *delivery/linking* via sota-observability rules/04 (alerting +
  runbook plumbing); you own the *security content* of the runbook.
- A runbook that's never been executed is a draft. Validate runbooks during
  tabletops and after real incidents (rules/06).
- Audit: pick 5 firing detections; how many have a linked runbook with concrete
  triage and containment steps vs. an empty wiki stub?

## 7. SOAR & automation — with guardrails

Automate the repetitive, gate the dangerous.

- **Safe to automate:** enrichment (lookups, geo, TI, asset/identity), dedup/
  correlation, ticket creation, evidence collection, notifying the user "was
  this you?".
- **Auto-containment needs guardrails.** Isolating a host, disabling an account,
  revoking a token, or killing a process (Tetragon `Sigkill`, rules/03) can
  cause an outage if the trigger was a false positive. Guardrails:
  - High confidence only (corroborated/risk-threshold detections, not single
    noisy signals).
  - **Blast-radius limits** — never auto-isolate a production database primary or
    disable a break-glass/admin account; allowlist the untouchables.
  - **Reversibility & audit** — every automated action is logged, attributable,
    and reversible; prefer "quarantine" over "destroy."
  - **Human-in-the-loop for high-impact** — propose-and-approve, not auto-execute,
    above a blast-radius threshold.
- **Revoke device trust on confirmed compromise.** When a device is confirmed
  compromised, the containment set includes revoking its device certificate or
  marking its posture non-compliant, so conditional access denies it everywhere
  at once, not only on the account that alerted. It runs under the guardrails
  above (confirmed, reversible, logged). OWASP: Zero Trust Architecture cheat
  sheet.
- Automation that can take down production is itself an attack surface and an
  availability risk — threat-model it (sota-threat-modeling) and least-privilege
  its credentials (sota-secrets-management).

## 8. Case management & the FP lifecycle

- **One case per incident**, accumulating all correlated alerts, enrichment,
  analyst notes, and actions — the evidentiary spine for IR (rules/06) and the
  post-incident review.
- **Disposition every alert** (TP / FP / benign-true / duplicate). Undispositioned
  alerts mean you can't measure precision or know what to tune.
- **The FP feedback loop is mandatory:** an FP disposition feeds back to tuning
  (§2) — add the allowlist, file the suppression-with-expiry. FPs that are closed
  but never fed back guarantee the same FP tomorrow.

## 9. SOC metrics

- **Time-to-triage / time-to-disposition** — speed of the human tier.
- **Alert precision** per detection — drives tune-or-retire decisions.
- **Auto-close rate** — high rate = the detection shouldn't page.
- **Coverage of runbooks** — % of paging detections with a validated runbook.
- **Automation rate** — % of toil automated (without crossing into unsafe
  auto-containment).
- **Security-signal rates** — auth success/failure ratio and policy-violation
  counts (authz denials, guardrail blocks) per app, trended beside MTTD/MTTR; a
  step change is an attack or a broken control (detections: rules/02 §7).

Avoid the vanity trap: "alerts handled" rewards noise. Reward incidents resolved
correctly and fast.

## Audit checklist

- [ ] What's the alert volume per analyst per shift, and the % auto-closed/
      ignored? Is any detection chronically muted (a Critical defect)?
- [ ] Are low-precision detections paging humans, or moved to hunting/
      corroboration?
- [ ] Do all suppressions have an owner, reason, and **expiry**? Hunt the
      suppression config for entries lacking an `expires`/`ttl` field.
- [ ] Is severity based on impact × confidence × asset criticality, or inflated
      so everything is Critical?
- [ ] Do alerts arrive enriched (asset/identity/TI/related signals), or must
      analysts do manual lookups per alert?
- [ ] Are alerts deduplicated and correlated into incidents, or does the analyst
      face a firehose of atomic events?
- [ ] Pick 5 paging detections: how many have a linked, concrete, executed-at-
      least-once runbook?
- [ ] Does any auto-containment exist? If so: confidence gate, blast-radius
      allowlist of untouchables, reversibility, audit logging, and human-in-loop
      above a threshold?
- [ ] **Cross-layer identity and device trust (§5, §7) — Medium:** are user,
      workload and device identities joined into one entity, do image-signature
      failures and reachable-vulnerability findings feed runtime risk, and does
      the SOAR containment set include revoking device trust? Zero files from
      `grep -rliE 'revoke.{0,30}device|device.{0,30}(cert|trust|posture)' soar/ playbooks/`
      (point it at the SOAR playbook directory) means device revocation is
      missing.
- [ ] Is every alert dispositioned, and do FP dispositions feed back into tuning
      (suppression-with-expiry / allowlist)?
- [ ] Are SOC metrics outcome-based (precision, time-to-disposition, runbook
      coverage) or vanity-based (alerts handled, events processed)?
