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

**Legacy systems** (unsupported OS, mainframe, OT, an appliance with no agent) are
where this inventory most often reads "not collected", and they are the systems
least able to protect themselves, so they need *more* monitoring, not less. Write
a parser or converter that turns their non-standard logs into the normalized
schema (§3). Where no log can be shipped, run a scheduled script on or beside the
host that checks current IOCs (hashes, accounts, listening ports, scheduled jobs)
and reports the result to the SIEM, and alert when that report stops arriving.
Make up for thin host logs at the network edge: put the legacy systems in their
own enclave and alert on flow anomalies at its boundary — volume surges, a first
connection to or from a host that has never talked to it, new ports. IR
priority for these systems is rules/06 §2. OWASP: Legacy Application Management
cheat sheet; Zero Trust Architecture cheat sheet.

## 2. Detection data quality

Collection isn't enough; the data must be detection-grade:

- **Completeness** — are all instances of the source shipping? One unmonitored
  subnet, region, or cluster is the one the adversary uses. Track expected vs.
  actual senders and alert on a source going silent (a dead sensor is an
  outage you must page on — adversaries kill logging: T1685 Disable or Modify
  Tools, formerly T1562, under ATT&CK v19's Defense Impairment tactic TA0112).
  Silence says *that* a sensor stopped; it does not say *who* stopped it. Collect
  the attributed event for every stop, disable, uninstall, reconfigure and
  re-enable of an EDR, AV, integrity or logging agent, carrying actor, host and
  time, and join it to the silent-source alert: silence with a matching
  change-ticketed actor is maintenance, silence with no event or an unexpected
  actor is tampering. Examples of such events: Windows Security 1102 (audit log
  cleared) and 4719 (audit policy changed), both with the subject account; Sysmon
  4 (service state changed) and 16 (configuration changed); Defender 5001
  (real-time protection disabled) and 5007 (configuration changed); a Linux
  `CONFIG_CHANGE` audit record such as `op=set audit_enabled=0`, which carries the
  session's `auid`. Not every such event names the actor — the documented 5001
  message does not — so attribute those by joining to the process-creation or
  service-control event that preceded them on the same host. A *re-enable* is
  worth an alert too: an attacker who turns protection back on after acting is
  cleaning up. OWASP: Logging Vocabulary cheat sheet.
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
  github.com/ocsf/ocsf-schema (the schema repo tracks version in `version.json`).
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

## 7. Application & behavioural detections

Some attacks are visible only to the application: every endpoint, cloud and
network log looks normal because the attacker is using the product as designed.
§1 lists application logs as a floor source; this section is the detection
content that has to run on them. Each rule still follows rules/01 (ADS, test,
owner) and rules/04 (runbook, severity).

### Application-login attacks

The fan-out logic from rules/07 *Password spraying — T1110.003* is not AD-specific.
It applies unchanged to any web, API or mobile login endpoint, and there the app
or IdP log is often the only witness.

- **Spraying (T1110.003):** one source failing against many *distinct* accounts
  in a window, each below the lockout threshold. Count distinct accounts per
  source (Sigma `value_count` correlation, KQL `dcount()`), not events per
  account — a per-account count only catches vertical brute force. To catch one
  password tried across many accounts from rotating IPs, the app may log a
  *keyed* hash of the attempted password (key held outside the log store, short
  retention, never the plaintext) and group on it.
- **Credential stuffing (T1110.004):** many accounts, about one attempt each,
  spread across many sources. Group by ASN, client fingerprint and failure reason;
  a jump in "unknown user" failures is the tell.
- **Failure-rate spikes:** alert when one account's or one source's failure rate
  climbs well above its own baseline, and when the app-wide success/failure ratio
  shifts. The *success* that follows a burst of failures is the event to page on.
- **Impossible travel:** two successful sign-ins to one account from places no
  one could travel between in the elapsed time. Rate it **Critical** as a
  takeover signal, after excluding known VPN and corporate egress ranges; take the
  IP from the connection, not a client header (sota-identity-access rules/06 §2).
  Enrich with what the second session did (MFA change, export, payout edit).
- **Session-ID guessing and harvesting:** have the app log every request that
  presents a session ID it does not recognise (unknown, malformed, long expired)
  with the source and a truncated hash of the ID, never the ID itself. Count
  *distinct* invalid IDs per source; many from one source is someone guessing or
  replaying harvested tokens. Session design is sota-code-security rules/17 §2.
- **Per role and privilege group:** also count failures grouped by the target's
  role (admins, finance, support). A campaign aimed at twenty administrators stays
  under every per-user and per-IP threshold and still stands out in its group.
- **Population-wide spikes:** track the risky-login and failure rate across
  *all* users. When the whole population moves at once, treat it as a possible
  leak of your own credential store, not as background noise: require
  out-of-band re-verification (step-up, email or device confirmation) for
  every account that logs in during the window, open an incident to test whether
  the credential database leaked, and check the honey user rows (rules/05 §4).
- Prevention (throttling, lockout, MFA) is sota-code-security rules/02. This is
  the detective half, and it must fire even when the throttle works: a blocked
  spray still means someone is attacking.

OWASP: Go-SCP; Logging Vocabulary cheat sheet; Secure Coding Practices QRG; Zero
Trust Architecture cheat sheet; Code Review Guide v2; Session Management cheat
sheet.

### Reconnaissance: force-browsing and unknown methods

Before exploiting anything, an attacker maps what exists (ATT&CK T1595.003
Active Scanning: Wordlist Scanning). Real clients rarely ask for things that do
not exist, so the misses are the signal.

- **404 bursts:** count *distinct* not-found paths per source and per
  authenticated user in a window. A wordlist scan produces hundreds; a broken
  link produces one path many times. Allowlist your own scanners and known
  crawlers by identity, not by user agent.
- **Unknown methods and fields:** gRPC `UNIMPLEMENTED` (which gRPC also returns
  for an unsupported compression, so group by method name), HTTP 405 on routes
  the client never uses, and GraphQL validation errors for fields that are not in
  the schema (graphql-js reports them as `Cannot query field "x" on type "Y".`).
  A client generated from your schema does not produce these; one from an
  authenticated principal is a strong signal.
- **Resource-exhaustion patterns as probing:** bursts of `RESOURCE_EXHAUSTED`,
  429s or query-cost rejections concentrated on one identity are someone
  measuring your limits or enumerating through them.
- For gRPC, sota-api-design rules/04 lists `DEADLINE_EXCEEDED` and `UNAVAILABLE`
  as the key *ops* alerts and adds per-client security metrics. Ship those
  per-client `UNAUTHENTICATED`, `PERMISSION_DENIED`, `UNIMPLEMENTED` and
  `RESOURCE_EXHAUSTED` counts to the SIEM, so the rules above run under a security
  owner rather than on an ops dashboard.

OWASP: Logging Vocabulary cheat sheet; gRPC Security cheat sheet.

### Baseline-relative abuse anomalies

SLO burn alerts watch for users being hurt; abuse often leaves latency and
success rates *better*. Run a second set of alerts on business and security
metrics, each compared with its own seasonal baseline (the same hour of the same
weekday) and firing past a stated deviation, e.g. several standard deviations:

- login success and failure rates, and the ratio between them (above);
- funnel ratios — signup to verification to purchase: a signup surge with no
  purchases is fake-account creation, purchases with no browsing is card testing;
- 4xx counts *per route*, since a total hides one endpoint under attack;
- database read and write volume per principal (data-access analytics below)
  and serverless invocation counts per function, where a jump is abuse or a
  cost attack.

**Failed deployments and restart loops.** sota-observability rules/04 §4 routes
single-instance failures the platform self-healed to a ticket rather than a page,
and that stays right for ops. Still send them to the security queue as a signal:
a container that keeps crashing (kube-state-metrics
`kube_pod_container_status_restarts_total`, waiting reason `CrashLoopBackOff`)
can be an exploit attempt failing against the process, and a deployment failing
for no code reason can be a tampered pipeline or image. A self-healed restart
does not page anyone, but someone in security still looks at it.

OWASP: Bot Management and Anti-Automation cheat sheet; Secure Cloud Architecture
cheat sheet.

### LLM / agent runtime detections

Prevention is sota-code-security rules/08; action logging and containment are
sota-sandboxing rules/05 R4.4/R4.5. This is the detection content over those logs.

- **Jailbreak campaigns and system-prompt extraction** (ATLAS AML.T0054 LLM
  Jailbreak, AML.T0056 Extract LLM System Prompt). One refused prompt is noise.
  Page on patterns: the same or near-duplicate adversarial prompt across many
  sessions or accounts, or an output containing a canary string planted in the
  system prompt (confirmed extraction, honeytoken-grade fidelity — rules/05).
  Guardrail verdicts are events to aggregate, not the detection itself.
- **Conversation anomalies:** probing (rapid rewordings of a refused request),
  excessive retries or regenerations, and guardrail-blocked turns per user or
  session far above that user's and the population's baseline.
- **Per-agent behaviour profile:** write down, for each agent, the tools it
  calls, the data volume it reads and returns, its action rate and its target
  systems. Alert when it deviates past a stated threshold (a new tool, a new
  target, a volume multiple), and name the response for each alert — normally a
  step of the graduated containment in sota-sandboxing rules/05 R4.5. A profile
  with no threshold and no response is documentation, not detection. Include
  the classic insider signals: many files read in a short window, a repository
  or dataset the agent has never touched, activity outside its scheduled hours.
  This only works if each agent acts under its own identity (sota-sandboxing
  rules/05 R3.2); an agent borrowing a human's or a shared service account's
  credentials cannot be profiled or told apart from them.
- **Guardrail and moderation decisions are telemetry.** Emit one structured
  event per verdict: guardrail name, category or rule ID, verdict
  (allow/block/redact/escalate), model and prompt version, and the user, session
  and agent identity. Where the prompt is sensitive, log the rule ID and a hash
  of the input, not the text (sota-code-security rules/23 §1). Alert on *drift*
  in the rates per verdict and per reason, per user and population-wide: a
  refusal category that jumps is a campaign; approvals that rise after a prompt,
  model or guardrail change may mean a control stopped working. Per-user token
  and request volume against that user's baseline belongs in the same feed.
- **Model-provider APIs as a covert channel** (ATLAS AML.T0096 AI Service API,
  AML.T0108 AI Agent; ATT&CK T1102 Web Service, T1567 Exfiltration Over Web
  Service). Inventory which workloads legitimately call model-provider
  endpoints; alert on any other host or process calling them, on credentials not
  issued to that workload, and on payloads that do not fit the feature (large
  encoded blobs, steady beacon-like timing).

OWASP: AISVS 12.1.2, 12.2.2, 12.2.3, 12.2.6; LLMSVS 8.1; DSOMM; LLM Prompt
Injection Prevention cheat sheet; Logging Vocabulary cheat sheet. Incident
response for these detections: rules/06 §2.

### Data-access analytics: exfiltration, insider misuse, database anomalies

A valid account reading data it is allowed to read (T1078, T1213 Data from
Information Repositories) looks normal everywhere except in *how much* and
*which* records.

- **Per-identity volume baseline:** for each user, service account and API key,
  baseline records or bytes read per window; alert on large multiples and on a
  first-ever read of a dataset.
- **Access without business need:** authorised staff and admins opening
  sensitive records outside their assignment (a support agent with no matching
  ticket, an admin browsing high-profile accounts). Join the access log to the
  assignment or ticket source; the unmatched read is the alert. This needs the
  app to log *reads* of sensitive records, not only writes.
- **Database security anomalies:** bulk exports and dumps, query-rate spikes from
  one principal, and commands an application account should never send — MongoDB
  server-side JavaScript (`$where`, `$function`, `$accumulator`, and `mapReduce`,
  which MongoDB has deprecated), user and role grants, other admin commands. From
  an app principal, one occurrence is a high-fidelity alert.
- **Keep it apart from performance monitoring.** A slow-query dashboard is tuned
  to ignore exactly the fast, well-indexed bulk read an exfiltrating account
  makes. Route these to the SIEM under a security owner; the audit-log plumbing
  (e.g. pgaudit) is sota-databases rules/06.

OWASP: Code Review Guide v2; NoSQL Security cheat sheet; Zero Trust Architecture
cheat sheet.

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
- [ ] **App-login attacks (§7) — High:** do application/IdP login logs feed a
      distinct-accounts-per-source spray rule, per-account and per-source
      failure-rate alerts, and impossible travel rated Critical? Zero files from
      `grep -rliE 'type: *value_count|dcount\(' detections/` or from
      `grep -rliE 'impossible.?travel|geo.?velocity' detections/` means the fan-out
      or travel rule is missing; then confirm the hits cover app logins, not only AD.
- [ ] **LLM/agent runtime (§7) — High where an LLM feature or agent ships:** are
      there rules for jailbreak campaigns, system-prompt extraction, per-agent
      deviation with a named response, and unexpected callers of model-provider
      APIs? Zero files from
      `grep -rliE 'AML\.T0(054|056|096|108)|jailbreak|system.?prompt' detections/`
      means none exist.
- [ ] **Data access (§7) — High:** is there a per-identity read-volume baseline, a
      no-business-need rule for sensitive records, and a rule on admin or
      server-side-JS commands from app principals, owned by security rather than
      a performance dashboard? For MongoDB, zero files from
      `grep -rliE '\$where|\$function|\$accumulator|mapReduce|grantRolesToUser|createUser' detections/`
      means the dangerous-command rule is missing.
- [ ] **Legacy systems (§1) — Medium (manual):** is every legacy host either
      parsed into the SIEM or covered by a scheduled central IOC check with a
      stopped-reporting alert, and is its enclave boundary watched for flow
      anomalies?
- [ ] **Agent tamper attribution (§2) — High:** is every stop, disable or
      re-enable of an EDR, AV, integrity or logging agent collected with its
      actor and joined to the silent-source alert? Zero files from
      `grep -rliE 'EventID:[[:space:]]*(1102|4719|5001|5007)([^0-9]|$)|audit_enabled=0|CONFIG_CHANGE' detections/`
      means no rule watches the tamper events (Sysmon 4/16 need a
      Sysmon-channel check by hand).
- [ ] **Session guessing and population spikes (§7) — High:** is there a rule on
      distinct invalid session IDs per source, failures per role or privilege
      group, and a population-wide spike that triggers out-of-band
      re-verification? Zero files from
      `grep -rliE 'invalid.?session|unknown.?session|session.?(not.?found|expired)' detections/`
      means the session-guessing rule is missing.
- [ ] **Reconnaissance (§7) — Medium:** do rules count distinct 404 paths per
      source and user, and alert on gRPC `UNIMPLEMENTED`, GraphQL unknown-field
      errors and `RESOURCE_EXHAUSTED` bursts per identity? Zero files from
      `grep -rliE 'UNIMPLEMENTED|Cannot query field|status(_code)?[^0-9]{0,6}404' detections/`
      means none exist.
- [ ] **Baseline anomalies (§7) — Medium:** are funnel ratios, 4xx per route and
      per-function invocation counts alerted against a seasonal baseline, and do
      restart loops and failed deploys reach a security queue? Zero files from
      `grep -rliE 'restarts_total|CrashLoopBackOff' detections/` means restart
      loops never reach security.
- [ ] **Guardrail telemetry (§7) — High where an LLM feature ships:** is every
      guardrail or moderation verdict logged with its rule ID (not the sensitive
      prompt), and is drift in verdict and reason rates alerted? Zero files from
      `grep -rliE 'guardrail|moderation|refusal|safety.?filter' detections/`
      means no rule reads those verdicts.
