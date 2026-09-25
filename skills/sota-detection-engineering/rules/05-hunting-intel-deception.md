# 05 — Threat Hunting, Intelligence & Deception

Detections catch what you anticipated. Hunting finds what you didn't; threat
intel tells you what to look for and contextualizes what you find; deception
manufactures the highest-fidelity signals you'll ever own. Read this when
running hunts, building/operating a threat-intel capability or TIP, consuming
STIX/TAXII feeds, or deploying honeypots/honeytokens/canaries. (Especially
load-bearing if you operate a threat-intel platform or a deception zone.)

## 1. Hypothesis-driven hunting & the hunt loop

Hunting is the proactive, human-led search for adversary activity that evaded
existing detections. It is **hypothesis-driven** — not "go look at the data," but
"I believe X is happening; here's how I'd prove it."

The hunt loop:

```
1. Hypothesis      "An adversary who phished a dev is using their cloud creds
                    to enumerate IAM (T1087) from a new ASN."
2. Scope data      Which logs witness it? (cloud audit + identity, rules/02)
3. Hunt            Query/baseline/stack-count to find anomalies; pivot.
4. Findings        TP → incident (rules/06). FP/benign → understand baseline.
5. Operationalize  Turn a repeatable hunt into a *detection* (rules/01). A hunt
                    you run twice should become a rule.
```

The fifth step is what makes hunting compound: every successful hunt either
finds an intrusion or produces a new detection (and a tuned baseline). A hunt
program that never spawns detections is just expensive log-staring.

Where hypotheses come from: threat intel (a new actor TTP, §3), ATT&CK coverage
gaps (rules/01 — hunt the cells you can't yet detect), crown-jewel attack paths
(threat modeling), and anomalies analysts notice.

## 2. Structured analytic techniques & IOC vs IOA/TTP hunting

- Use **structured analytic techniques** to fight bias: state assumptions
  explicitly, consider alternative explanations (could this be benign admin
  activity?), seek disconfirming evidence. The brittle failure of hunting is
  confirmation bias — finding the "attack" you went looking for.
- **IOC hunting** (find this hash/IP/domain) is fast, retrospective, and brittle
  — best for *retro-hunting* a fresh intel indicator across history (rules/02
  retention). **IOA/TTP hunting** (find this *behavior*) is durable and is what
  catches novel and evasive actors. Weight your hunt program toward behavior, per
  the Pyramid of Pain (rules/01 §4).
- Useful behavioral techniques: **stack counting** (frequency-of-occurrence —
  rare parent/child pairs, rare process paths), baselining (deviation from an
  entity's own history), and **least-frequency analysis** (the one host doing
  the thing no other host does).

## 3. Threat intelligence: lifecycle, TIP, standards

Threat intel is a process, not a feed subscription. The lifecycle: **direction →
collection → processing → analysis → dissemination → feedback.** Without
direction (what decisions does this intel serve?) and feedback (did it help?),
a TIP becomes an expensive IOC landfill.

- **Tiers of intel:** strategic (who targets our sector, their objectives),
  operational (campaigns, TTPs), tactical (IOCs/atomic indicators). Tactical
  IOCs are the lowest-value, fastest-decaying tier — treat them as enrichment
  and retro-hunt fuel, not as your detection strategy (Pyramid of Pain again).
- **TIP (Threat Intelligence Platform):** ingests, deduplicates, scores, ages-out,
  and disseminates intel; the engine that turns feeds into *operationalized*
  detections and enrichment. Aging-out matters: a 2-year-old IP IOC is mostly
  noise. Score by confidence and source, and expire indicators.
- **Intel-driven detection:** the highest-value output is converting an actor's
  *TTP* (not their IOCs) into a durable detection (rules/03). When intel says
  "actor uses technique T1234," the deliverable is a tested detection, not an
  IOC import.

### STIX 2.1 / TAXII 2.1

- **STIX 2.1** — the OASIS standard data model for cyber threat intelligence
  (objects: indicators, attack-patterns, threat-actors, relationships, etc.).
- **TAXII 2.1** — the OASIS standard transport (collections + channels) for
  exchanging STIX over HTTPS.
- Both have been **approved OASIS Standards since 2021** (verify at
  oasis-open.org / docs.oasis-open.org/cti). Build the TIP to speak STIX 2.1 over
  TAXII 2.1 so it interoperates with ISACs, vendors, and sharing communities
  rather than locking into a proprietary feed format.

### Framing models

- **Diamond Model** (adversary–capability–infrastructure–victim) — pivot across
  the four vertices to expand from one indicator to a campaign.
- **Cyber Kill Chain / ATT&CK** — situate observed activity in the intrusion
  lifecycle to anticipate the next step and find earlier-stage evidence.

## 4. Deception: the highest-fidelity detection you own

Legitimate users have no reason to touch a decoy. So a triggered deception
asset has a **near-zero false-positive rate** — the inverse of every log-based
detection, where FPs are the dominant cost. Deception is force-multiplying
signal: cheap to deploy, expensive for the adversary to avoid (they can't tell
the decoy from the real thing).

- **Honeytokens / canary credentials** — fake AWS keys, API tokens, DB
  connection strings, service-account creds planted where an adversary who's
  inside will find them (config files, CI variables, a "secrets" doc, a
  honeypot's environment). *Any* use = compromise, full stop. Coordinate planting
  and alerting with **sota-secrets-management rules/04 (honeytokens)** — that
  skill owns the credential mechanics; you own detecting and responding to use.
- **Canary tokens** — tripwires beyond credentials: a watched URL, a tracked
  document, a DNS canary, a unique S3 object. Fired = someone is somewhere they
  shouldn't be.
- **Honeypots / deception zone** — decoy services/hosts (and, in K8s, decoy
  pods/secrets) that look real. Interaction = malicious by definition. The
  goal is to seed it across the paths attackers
  *must* traverse (lateral movement targets, credential stores, "admin" panels)
  so movement trips a wire early.
- **Placement is everything.** A honeytoken nobody encounters never fires; one in
  the adversary's natural path (the file they'll grep, the creds they'll spray)
  fires on first contact. Place decoys along real attack paths, not in a corner.
  Placements that pay off in applications:
  - **Honey user rows** in the app's own user store, with credentials nobody
    was ever given. The login path checks for them: an attempt against one means
    the user table leaked, so page IR and move the app into a secure state
    (forced re-verification, tightened throttling — rules/02 §7
    population-wide spikes).
  - **A bait path listed as `Disallow` in robots.txt** and linked nowhere else.
    Well-behaved crawlers skip it and robots.txt is not access control
    (RFC 9309 says so), so a request to it marks a crawler that read the file
    and ignored it, or a person mining it for targets.
  - **Watermarked canary records** in public listings: a unique fake entry per
    listing or per consumer, so when the data shows up elsewhere the record
    says which scraper or account took it.
  - **Honeytokens for AI agents** in the agent's workspace, memory and config
    paths (a fake key in a dotfile, a canary URL in a memory entry). The agent's
    task never needs them, so use means it was steered by injected instructions.
    The response is agent-specific: contain the agent and revoke its credentials
    (sota-sandboxing rules/05 R4.5), then run the rules/06 §2 LLM playbook.
  OWASP: Bot Management and Anti-Automation cheat sheet; Code Review Guide v2;
  DSOMM.
- **Detection wiring.** Every deception asset must alert with maximum severity
  and rich context (who/where/how) and route straight to IR — these are
  presumed-true-positive (rules/04 routes; rules/06 responds). Guard against the
  adversary detecting the decoy (timing, fingerprintable artifacts) where you
  can, but even crude deception yields high-value signal.

## Audit checklist

- [ ] Is hunting hypothesis-driven (stated, falsifiable hypotheses) or
      unstructured log-staring?
- [ ] Does every successful/repeatable hunt get operationalized into a detection
      (rules/01)? Or do findings evaporate after the hunt?
- [ ] Is the hunt program behavior/TTP-weighted, or mostly IOC sweeps?
- [ ] Are structured analytic techniques used to counter confirmation bias
      (alternative hypotheses, disconfirming evidence)?
- [ ] Does the threat-intel program have *direction* and *feedback*, or is the
      TIP an IOC landfill?
- [ ] Are indicators scored by confidence/source and **aged out**, or kept
      forever (decayed IOCs = noise)?
- [ ] Is intel converted into *TTP detections*, or only imported as IOC matches?
- [ ] Does the TIP speak **STIX 2.1 / TAXII 2.1** for interoperability with
      sharing communities?
- [ ] Are honeytokens/canaries/honeypots deployed along *real attack paths*
      (credential stores, lateral-movement targets), not in unused corners?
- [ ] Does every deception asset alert at max severity with context and route
      straight to IR? Hunt: enumerate planted canaries vs. those wired to an
      alert — any unwired decoy is a wasted tripwire.
- [ ] Are honeytoken mechanics coordinated with sota-secrets-management rules/04?
- [ ] **Application placements (§4) — Medium:** are there honey user rows
      checked at login, a robots.txt bait path, canary records in public
      listings, and honeytokens in agent workspaces, each wired to a response?
      Zero files from
      `grep -rliE 'honey.?(user|account|row)|canary.?record|bait.?path|robots\.txt' detections/`
      means no application placement is wired to an alert.
