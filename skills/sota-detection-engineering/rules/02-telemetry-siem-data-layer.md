# 02 — Telemetry Coverage & the SIEM/Data Layer

**You can't detect what you don't collect.** Log-source coverage is the #1 gap
in every real detection program. A perfect Sigma rule against a log you never
ship detects nothing. Read this when deciding what telemetry to collect,
choosing a SIEM/data lake, normalizing schemas, sizing retention, or auditing
whether the data foundation can even support detection and IR.

Boundary: **sota-observability owns the telemetry *pipeline*** — how logs are
emitted, structured, shipped, and stored, plus retention plumbing and cost. This
rule owns it from the *security* angle: which sources are non-negotiable for
detection, what fidelity detections require, and how to size data for *IR and
hunting* (a different requirement than ops debugging).

## 1. Log-source coverage: the security floor

Before writing detections, inventory sources against your attack paths. The
non-negotiable categories:

| Source | Detects | Without it you are blind to |
|---|---|---|
| **Endpoint / EDR** | process exec, injection, credential dumping, persistence | most host TTPs; the largest single coverage source |
| **Cloud audit** (CloudTrail / GCP Audit / Azure Activity) | IAM abuse, persistence, exfil, resource hijack | cloud control-plane attacks (the modern breach path) |
| **K8s audit log** + admission | `exec`/`attach`, RBAC changes, secret reads, privileged pods | container/orchestrator attacks (see sota-kubernetes) |
| **Network / flow** (NetFlow, VPC flow, Zeek) | C2 beaconing, lateral movement, exfil volume | east-west movement, DNS exfil (see sota-network-security) |
| **Identity / auth** (IdP, MFA, directory) | impossible travel, MFA fatigue, token theft, new-device | account takeover (see sota-identity-access) |
| **Application** | business-logic abuse, app-layer attacks, agent/LLM abuse | abuse only your app can see (auth flows, prompt-injection) |
| **DNS** | DGA, exfil over DNS, C2 resolution | a huge fraction of malware behavior |

Map each to its **enabled** state, not its *available* state. CloudTrail data
events (S3/Lambda object-level) are off by default and are exactly where exfil
shows up. K8s audit logging requires an explicit policy file — many clusters ship
with it effectively disabled. The audit finding is "data event logging not
enabled," not "no S3 detection."

Coverage assessment, concretely: take your top 5 attack scenarios (from threat
modeling), and for each ATT&CK technique in the chain, name the log that would
witness it and confirm it is collected, parsed, and queryable. Gaps are findings
*before* any rule is written.

## 2. Detection data quality

Collection isn't enough; the data must be detection-grade:

- **Completeness** — are all instances of the source shipping? One unmonitored
  subnet, region, or cluster is the one the adversary uses. Track expected vs.
  actual senders and alert on a source going silent (a dead sensor is an
  outage you must page on — adversaries kill logging: T1685 Disable or Modify
  Tools, formerly T1562, under ATT&CK v19's Defense Impairment tactic TA0112).
- **Timeliness** — ingestion lag directly inflates MTTD. A log that lands an hour
  late detects an hour late.
- **Fidelity** — does the event carry the fields the detection needs? Command
  lines truncated, user fields empty, or process ancestry missing make whole
  technique classes undetectable. Verify the *fields*, not just the event count.
- **Integrity** — can the source be tampered with or disabled by the very
  activity you're detecting? Ship logs off-host immediately; an attacker who
  owns the box owns its local logs.

## 3. Normalization: OCSF and ECS

Detections written against raw, per-vendor formats don't port and break on
vendor changes. Normalize:

- **OCSF (Open Cybersecurity Schema Framework)** — vendor-agnostic event schema
  (categories, classes, attribute dictionary), Apache-2.0, backed by a broad
  industry coalition. Verify the current version at schema.ocsf.io /
  github.com/ocsf/ocsf-schema (the schema repo tracks version in `version.json`;
  as of mid-2026 it is on the 1.x line, ~1.8 stable with 1.9 in development).
  AWS Security Lake and a growing set of tools emit/ingest OCSF natively.
- **Elastic ECS (Elastic Common Schema)** — the field-naming standard across the
  Elastic ecosystem; many Sigma backends and detection content assume ECS field
  names. ECS and OCSF are converging/mapping efforts exist; pick the one your
  primary platform speaks and map the rest to it.

Write detections against the normalized schema, not the wire format. This is
what lets one Sigma rule cover sources from three vendors and survive a vendor's
log-format change.

## 4. SIEM / data-lake choice

There is no universal right answer; choose on data volume, query model, cost,
and team. Patterns:

- **Classic SIEM** (Splunk, Microsoft Sentinel, Elastic Security) — strong
  correlation, mature detection content, rich query languages (SPL/KQL/EQL+ES|QL).
  Cost scales with ingest; volume discipline is mandatory.
- **Open-source / self-hosted** (OpenSearch, the Elastic stack, Wazuh) — control
  and cost predictability; you own the operational burden.
- **Security data lake** (e.g. lake + query engine over object storage, often
  OCSF-normalized) — decouples cheap long-term storage from compute, enabling
  long retention for hunting/IR at far lower cost; queries are
  higher-latency/batch. Increasingly the pattern for big environments.
- **Log/observability platforms** (Loki, etc.) — fine for ops, often weak for
  correlation-heavy security detection; know the limits before betting detection
  on them.

A common modern split: hot tier (recent data, real-time detections) in a fast
SIEM; cold tier (long retention) in a cheap data lake for hunting and IR
lookback. Detections run hot; hunts and investigations reach into cold.

## 5. Retention sized for IR and hunting

Ops retention (days–weeks) is far too short for security. Drivers:

- **Dwell time.** Industry median dwell time is *weeks to months*. If you retain
  30 days and the adversary was in for 90, your incident investigation hits a
  wall — you cannot reconstruct initial access or scope. Retain security-relevant
  sources (auth, cloud audit, EDR, DNS, network metadata) long enough to
  out-last realistic dwell — commonly **12 months** for the highest-value
  sources, longer where compliance dictates.
- **Retro-hunting.** When a new IOC/TTP from threat intel lands, you hunt it
  *backwards* across history. No history → no retro-hunt.
- **Forensics & legal.** IR and potential litigation need defensible retention
  with integrity (see rules/06 chain of custody).

Tier to control cost: short hot retention for high-volume/low-value sources,
long cold retention for the security-critical ones. Coordinate the *plumbing*
with sota-observability; you own the *security minimums*.

## 6. Volume & cost discipline

Ingest-priced platforms turn "collect everything" into a budget crisis that ends
with someone disabling sources — re-opening blind spots. Discipline:

- **Filter at the edge,** not by dropping sources. Drop known-noise event types
  (verbose health checks, debug chatter) before ingest; keep the security-
  relevant fields.
- **Tier by value.** Route high-value/low-volume (auth, cloud audit) to the
  expensive hot SIEM; route high-volume/low-value (verbose proxy logs) to the
  cheap lake.
- **Never silently drop a security source to save money.** That's a Critical
  finding waiting to be an incident. If a source must be trimmed, sample
  transparently and document the blind spot in the affected detections' ADS
  blind-spots section.

## Audit checklist

- [ ] Is there a log-source inventory mapped to attack paths, with *enabled*
      (not merely *available*) status per source?
- [ ] For the top 5 attack scenarios, can you name and confirm the collected log
      for every technique in the chain?
- [ ] Are cloud data events (e.g. CloudTrail S3/Lambda object-level) and K8s
      audit logging explicitly *enabled*, not left at insecure defaults?
- [ ] Is there alerting when a log source goes silent (dead sensor / T1685
      logging tamper, formerly T1562)? Hunt: per source, compare current ingest
      rate to a 7-day baseline and flag drops >50%.
- [ ] Do events carry the fields detections need (full command lines, user,
      process ancestry), or are they truncated/empty?
- [ ] Are detections written against a normalized schema (OCSF/ECS), or against
      raw per-vendor formats that won't port?
- [ ] Is security retention sized to out-last realistic dwell time (≥12 months
      for high-value sources), not ops retention (days)?
- [ ] Is there a hot/cold tiering that keeps long-history retro-hunting
      affordable?
- [ ] Has any security source been dropped or sampled purely for cost without
      documenting the resulting blind spot?
- [ ] Are logs shipped off-host promptly so a compromised host can't erase its
      own evidence?
