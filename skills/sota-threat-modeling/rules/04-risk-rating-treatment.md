# 04 — Risk Rating & Treatment

Rating exists to ORDER work and justify dispositions — not to produce
precise-looking numbers. Prefer a coarse, calibrated, contextual scale applied
consistently over a fine-grained scale applied inconsistently.

## 1. DREAD — know it, and know why not to trust it

DREAD scores Damage, Reproducibility, Exploitability, Affected users,
Discoverability (1–10 each, averaged). Pitfalls — each one disqualifying for
serious use:

1. **Unanchored scales.** "Damage = 7" means different things to different
   raters; scores drift by who's in the room. (Microsoft itself dropped DREAD
   for this.)
2. **Averaging hides extremes.** Damage 10 / everything-else 2 averages to a
   "low" — but a hard-to-find RCE is still an RCE. Worst-dimension logic
   beats means.
3. **Discoverability rewards obscurity.** Rating threats lower because
   "nobody will find it" institutionalizes security-by-obscurity; attackers
   read code, run scanners, and get lucky. If you keep D, score it 10 always —
   at which point drop it.
4. **Double counting.** Reproducibility, Exploitability, Discoverability are
   three blurry views of likelihood; one inflated dimension skews the total.

If an org mandates DREAD: anchor every level with written exemplars, replace
the mean with max-of(Damage, weakest-link likelihood), and fix D=10. At that
point you have rebuilt likelihood × impact — use that directly (§3).

## 2. CVSS — what it's for and how to use it without lying

CVSS scores **vulnerability severity characteristics**, not your risk. Base
score assumes a "reasonable worst case" deployment that is not yours.

Rules:
- **Use CVSS for vulnerabilities (CVEs, pentest findings), not design-stage
  threats.** Threats from a model lack the concrete exploit parameters CVSS
  vectors encode; scoring hypotheticals produces false precision.
- **Never rank by base score alone.** Adjust with environmental/threat
  metrics — or informally: Is the vulnerable path reachable here? Authn in
  front? Exploit public? Asset behind it valuable? A 9.8 in a dev-only,
  network-isolated tool can be Medium; a 6.5 authz bypass on the payment API
  is Critical.
- **Record the vector string, not just the number** (e.g.
  `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`) so reviewers can audit the
  assumptions — the vector is the rating; the number is a summary.
- **Note the version prefix.** CVSS v4.0 (published 2023) replaced
  temporal metrics with threat metrics (CVSS-B/BT/BTE nomenclature); v3.1 and
  v4.0 scores coexist in feeds — the prefix says which rules produced the
  number, so never compare scores across versions.
- **CVSS ≠ exploitation probability.** For "will this actually be exploited",
  consult exploit-prediction signals (EPSS-class scores, KEV-style
  known-exploited lists) and your own exposure; severity and likelihood are
  separate axes.

## 3. Likelihood × impact — the default rating method

Use a 3×3 (or at most 4×4) matrix with ANCHORED level definitions. Anchors are
the whole method; publish them with the model.

**Likelihood anchors** (calibrate to your exposure):

| Level | Anchor |
|---|---|
| High | Exploitable by an unauthenticated or any-customer actor with public techniques/tools; or attack is automated/commodity (credential stuffing, scanner-findable) |
| Medium | Needs a valid account, a specific misconfig, social engineering, or chaining two weaknesses; technique documented but targeted |
| Low | Needs insider access, physical access, significant novel research, or multiple independent failures |

**Impact anchors** (write per system, in business terms — PASTA-lite preamble
from `01` §4 feeds this):

| Level | Anchor (example for a payments SaaS) |
|---|---|
| High | Any-customer data breach; money movement; RCE in prod; full account takeover class |
| Medium | Single-account compromise; partial data exposure; sustained outage of a paid feature |
| Low | Cosmetic, single-user self-inflicted, info of negligible value |

**Availability (DoS) impact takes two inputs: how much is lost, and how much the
service matters.** How much is lost uses CVSS v4's Availability Impact (§2): *total*, an
attacker able to "fully deny access to resources", sustained or persistent; or *partial*,
where "Performance is reduced or there are interruptions in resource availability". How
much it matters uses CVSS v4's Availability Requirement: loss "is likely to have a
catastrophic", "a serious", or "only a limited adverse effect" on the organization or the
people it serves. Record that requirement per service beside its §8 tier, because §8
tiers modeling *depth*: an internal, Low-tier job can still be one whose loss is serious.

| Service's availability requirement | Total loss | Partial loss |
|---|---|---|
| Catastrophic (safety-relevant; the revenue path, e.g. checkout) | High | Medium |
| Serious (a paid feature; a job with a hard downstream deadline) | Medium | Low |
| Limited (internal batch the next run makes up) | Low | Low |

The cells are this library's judgment, not CVSS output. *Serious × total* is the
existing Medium anchor ("sustained outage of a paid feature"). A partial loss sits one
band lower because CVSS defines its Low value by the absence of a "direct, serious
consequence". With no requirement recorded, state both readings and ask, per the
router's floor ([`sota` rules/03](../../sota/rules/03-audit-findings.md) §1 rule 1);
CVSS scoring an undefined requirement as High is a scoring default, not a rating.

**Matrix → priority:**

| | Impact Low | Impact Med | Impact High |
|---|---|---|---|
| **Likelihood High** | Medium | High | Critical |
| **Likelihood Med** | Low | Medium | High |
| **Likelihood Low** | Low | Low | Medium* |

\* Escalate Low×High to High when the impact is catastrophic-irreversible
(safety, signing-key theft) — fat tails don't average.

Rules:
- **Rate the threat AS MITIGATED TODAY,** then optionally note inherent (un-
  mitigated) risk. Ranking inherent risk floods the top band uselessly.
- **Likelihood follows the easiest path** to the impact, not the path you
  enumerated first. Attack trees (`01` §5) find the cheapest branch.
- **Don't multiply made-up numbers.** 1–5 scales multiplied give 1–25
  pseudo-precision; band labels resist abuse better. For real quantification
  use a FAIR-style analysis with ranges — only worth it for top-5 enterprise
  risks.
- **Calibrate across raters:** score 5 threats independently, compare, refine
  anchors where raters diverged. Re-calibrate when the team changes.

Severity-label conventions for audit findings are defined in `SKILL.md` and
elaborated in `06` — same axes, evidence-backed.

## 4. Treatment: accept / mitigate / transfer / avoid

Every threat gets exactly one disposition, recorded with the threat. "Noted"
or an unassigned ticket is not a disposition.

| Treatment | Use when | Required record |
|---|---|---|
| **Mitigate** | Control is cheaper than expected loss; default for High+ | Requirement ID(s) + owner + verification test (§5) |
| **Accept** | Residual risk below appetite; cost of control exceeds it | Named individual owner (a person with authority over the asset, not "the team"), rationale, expiry/review date. Un-expiring acceptances are how risk registers rot. |
| **Transfer** | Liability shiftable: insurance, payment processor, managed service | Contract/SLA reference + the residual you keep (reputation never transfers; breach-response duties rarely do) |
| **Avoid** | Feature/design not worth its risk | Design change record — e.g., don't store PANs at all (use a token vault), drop the "fetch any URL" feature, remove the agent's write-tools |

Rules:
- **Avoid is underused.** Always ask "can we not have this data/feature/
  privilege?" before designing a mitigation — deleted attack surface needs no
  patching. Data minimization is risk avoidance (and LINDDUN Dd treatment).
- **Mitigations can change likelihood OR impact — say which.** Rate limiting
  cuts likelihood; encryption + tokenization cut impact; segmentation cuts
  blast radius. Prefer one impact-cutting control plus one likelihood-cutting
  control on Critical paths (defense in depth, but bounded — two layers,
  justified, not five vague ones).
- **Acceptance escalates with severity:** Low — tech lead; Medium —
  eng manager; High — director/CISO; Critical — not acceptable without
  executive sign-off and a dated remediation plan.
- **Every mitigation has two names and a due date.** The *accountable* owner
  answers for the risk and can accept it; the *responsible* implementer does
  the work. One name for both hides who decides when the work slips. Track
  status per action (open, in progress, done, verified), not per threat.
- **Decide in advance what a missed due date does.** It never silently
  rolls over. It triggers, in order: escalation to the next acceptance level
  above, a re-rating (exposure may have grown while the fix waited), and
  either a new committed date or a time-boxed formal acceptance under the
  Accept row's rules. A mitigation past its date with none of these is an
  undisposed threat. OWASP: Threat Modeling Playbook.

## 5. Mapping mitigations to requirements and tests

A mitigation that is not a requirement will not be built; a requirement that
is not a test will not survive refactoring.

**Chain:** threat → requirement → implementation → verification. Keep IDs
linked end to end:

```
T-012  (High) Authenticated customer reads other tenants' orders via
       GET /orders/{id} (IDOR; STRIDE-E/I)
SR-104 Every order access MUST verify order.tenant_id == caller.tenant_id
       at the data-access layer (not per-handler).
IMPL   OrderRepository.get() takes tenant from auth context; handlers
       cannot pass tenant explicitly. (PR #482)
VER-1  Integration test: tenant-A token + tenant-B order id → 404.   [abuse case]
VER-2  Static check: CI greps for OrderRepository bypass / raw order
       queries outside the repository module.                        [regression guard]
```

Rules:
- **Write requirements as testable MUSTs** with a location ("at the
  data-access layer"), not aspirations ("handle authz properly"). One
  requirement may cover many threats; never the reverse without splitting.
- **Every mitigated High+ threat gets a VER entry** — an abuse-case test
  (negative test from the attacker's perspective, see `05` §3) and, where
  possible, a structural guard (lint rule, policy-as-code, dependency rule)
  that fails CI on regression.
- **Requirements live in the backlog with normal tracking** (see `05` §2) —
  a threat model PDF with embedded TODOs is a graveyard.

## 6. Residual risk documentation

After treatment, what risk remains — because controls are partial, accepted,
or transferred-with-remainder? Document per threat, one line:

```
T-012 residual: tenant check enforced in repository layer; raw-SQL
escape hatches remain in /reports module (compensated by VER-2 grep,
reviewed quarterly). Residual rating: Low. Owner: j.doe. Review: 2026-09.
```

Rules:
- **Residual rating uses the same L×I matrix** — re-rate after controls, don't
  hand-wave "lower".
- **Aggregate residuals roll up to a risk register** (one table: threat ID,
  residual rating, owner, review date) — this is the artifact leadership
  actually reads; keep it under a page.
- **An expired review date flips the acceptance to a finding** in audits
  (`06`). Build the expiry sweep into the living-model cadence (`05` §4).

## 7. Rating anti-patterns (rejected on sight in review)

- **Severity haggling by remediation cost.** "Let's call it Medium because the
  fix is hard" — cost belongs in the treatment decision (maybe you accept or
  phase it), never in the rating. Once cost leaks into severity, the register
  stops describing reality.
- **Best-case likelihood.** Rating "Low because our WAF probably blocks it" —
  rate against the easiest path WITH evidence of the control; "probably" means
  the control is Partial and the rating stands.
- **Impact capped at the component.** "Only the worker is compromised" —
  impact follows the privilege-reach map (`02` §8), not the initially-popped
  box. A worker with DB write is a database compromise.
- **Stale ratings after architecture change.** L×I was assigned when the
  service was internal; it's public now. Re-rating is part of every re-model
  trigger (`05` §4), not a separate ceremony.
- **One number for a threat class.** "XSS: High" — each instance rates on its
  own context (what the page can reach, who views it). Classes get thematic
  findings (`06` §4); instances get ratings.
- **Risk-appetite fog.** Accept/mitigate thresholds undefined, so every
  dispute is relitigated. Write the appetite line once ("we mitigate all
  High+, accept Medium with director sign-off, batch Lows quarterly") and
  point at it.
- **Ignoring marginal capability.** Rating a bug by what it *does* rather than
  what it *adds* to **the attacker**: an administrator "exploiting" a flaw to
  download a file the UI already lets them download gains nothing. Impact is
  access the attacker did not already hold — which includes reaching another
  tenant, the host from a guest, or production from a build step. It also includes
  **lost conditions on a held capability**: the same download *without* the audit
  log, approval step, step-up MFA, rate limit or expiry it normally carries is new
  capability (STRIDE's Repudiation). And the attacker is not always the privileged
  user: CSRF or stored XSS against an admin-only endpoint, or prompt injection
  steering an admin's agent, gives a non-admin the admin's reach.
- **Attacker position read off the transport.** "It's an HTTP API, so remote" —
  for *likelihood*, the position is the least-privileged place from which the
  vulnerable code is **reachable**, traced back through any proxy, queue or job
  runner. Bind address alone does not decide it: every container in a Kubernetes
  pod shares localhost, a browser on the host can reach loopback through DNS
  rebinding or CSRF, and other local users can reach it too. This is a risk
  position, not the CVSS Attack Vector: CVSS v3.1's User Guide scores data received
  over a network and passed to a separate vulnerable component as AV:Local. Record
  both, and say which one a rating uses (§2).
- **Probability theater.** "0.3 likelihood × $2.4M = $720k expected loss"
  built on gut numbers. Either do the FAIR-style estimation with calibrated
  ranges and document the basis, or keep honest bands.

## Worked micro-example — rating in context

Same vulnerability, two ratings, both correct:

- *Unauthenticated SSRF in PDF renderer; renderer pod has IMDSv2 enforced,
  egress-deny netpol, no cloud role.* Likelihood High, Impact Low (reaches
  nothing) → **Medium**, mitigate via URL allowlist; accept residual Low.
- *Same SSRF; pod runs with node's instance role, flat VPC.* Likelihood High,
  Impact High (metadata creds → account) → **Critical**: fix the egress/IMDS
  posture (impact cut) AND the SSRF (likelihood cut); nothing acceptable here.

The CVE/base score would be identical for both. Context is the rating.

## 8. Application and module risk tiers — how deep to model and review

Effort follows risk, and that decision is made once per system, not per
meeting. **Tier every application** in one cross-application inventory, rated
on data criticality (credentials, payment, health, bulk personal data),
exposure (internet-facing, partner-facing, internal only), regulatory scope,
safety impact, and pivot value (a legacy host that can reach newer systems
counts). The tier sets the depth:

| Tier | Typical profile | Threat model | Verification target |
|---|---|---|---|
| Low | internal, no sensitive data, no pivot | four-questions pass on change (`01`) | ASVS L1 |
| Medium | authenticated users, personal data, or partner exposure | STRIDE per interaction, L0+L1 DFD, re-model triggers | ASVS L2 |
| High | internet-facing with credentials/money/health, regulated, safety, or a pivot into High systems | full decomposition down to process/IPC boundaries, attack trees for top assets, independent review | ASVS L3 for the relevant chapters |

The ASVS level column follows ASVS 5.0's own framing: L2 is what most
applications should aim for, and L3 is for applications that must show the
highest assurance. Re-tier on the triggers in `05` §4, and date each entry. An
application missing from the inventory has no tier, which in practice means no
modeling.

**Tier modules inside a codebase the same way** by exposure, value and
regulatory weight, weighed against what extra review costs. Auth, session,
crypto, payment, tenant-isolation and audit-logging paths are the usual high
tier. The tier sets review intensity: a second reviewer or a named security
reviewer, and a fresh look at the relevant threat rows on every change. The
routing mechanism is CODEOWNERS with required code-owner review
([`sota-docs-workflow` rules/03](../../sota-docs-workflow/rules/03-code-review-pr-workflow.md) §3). This section decides *which* paths deserve
it. OWASP: SAMM, DSOMM, Threat Modeling Playbook, Legacy Application
Management cheat sheet, Code Review Guide v2.

## Audit checklist

- [ ] **Marginal capability and attacker position** (§7): does each rating count only what
      the attacker gains — including lost audit, approval or MFA conditions and
      victim-mediated reach — and is the position where the code is actually reachable
      from, recorded beside (not instead of) the CVSS Attack Vector?
- [ ] A single, anchored rating scheme is defined and used consistently;
      anchors written down, not folklore; a matrix of at most 4×4 bands,
      no multiplied 1–5 scores, anchors calibrated by raters scoring
      threats independently (§3).
- [ ] No raw DREAD means or unadjusted CVSS base scores used as priority;
      where DREAD is mandated, levels anchored with written exemplars,
      max-of replacing the mean, and Discoverability fixed at 10 (§1);
      CVSS vectors and their version prefix recorded where CVSS is used;
      no CVSS on design-stage threats, no cross-version score comparison,
      and exploitation likelihood taken from EPSS/KEV-class signals, not
      the CVSS number (§2).
- [ ] Threats rated as-mitigated (§3), with likelihood reflecting the easiest
      path; Low×catastrophic escalated, not averaged away.
- [ ] Each DoS/availability threat rated on both inputs (§3): total vs partial loss, and
      the service's recorded availability requirement. One rated from "it goes down"
      alone, or with no requirement and no stated assumption → Medium (the rating is unreproducible).
- [ ] Every threat has exactly one disposition: mitigate/accept/transfer/
      avoid; no "noted"/orphaned threats; a transfer cites its contract/SLA
      and the residual kept, and each mitigation says whether it cuts
      likelihood or impact (§4).
- [ ] Acceptances have a named individual owner (§4), rationale, and unexpired
      review date; acceptance authority matches severity.
- [ ] "Avoid" considered (§4) (data/feature/privilege removal) before expensive
      mitigations — evidence in at least one disposition.
- [ ] Threat→requirement→test ID chain intact for all High+ mitigations;
      abuse-case tests exist and run in CI; requirements are testable MUSTs
      naming where they hold, with a structural CI guard where possible
      (§5).
- [ ] Residual risks re-rated on the same scale and rolled into a ≤1-page
      register with owners and review dates (§6).
- [ ] Expired acceptances/reviews flagged as findings (§6).
- [ ] Each mitigation names an accountable owner and a responsible (§4)
      implementer with a due date and per-action status. A past-due action with
      no escalation, re-rating or time-boxed acceptance → Medium (High when
      the threat is High+).
- [ ] A cross-application inventory tiers every system and names its
      modeling depth and ASVS target (§8). A High-tier system with only a
      four-questions pass, or no tier at all → High.
- [ ] High-tier modules (auth, crypto, payment, tenancy) (§8) have heightened
      review. Probe: `cat .github/CODEOWNERS CODEOWNERS docs/CODEOWNERS 2>/dev/null | grep -v '^#' | grep -c -i -E 'auth|session|crypto|payment|billing|tenant'`;
      0 in a codebase that has such modules → Medium. The `2>/dev/null` also
      prints 0 when NO CODEOWNERS file exists — run `ls -1 .github/CODEOWNERS CODEOWNERS docs/CODEOWNERS`
      and name which case the finding is (no file vs no high-tier path).
