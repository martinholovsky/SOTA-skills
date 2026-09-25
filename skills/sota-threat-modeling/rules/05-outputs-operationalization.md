# 05 — Outputs & Operationalization

A threat model's value is measured by the controls it ships and the
regressions it catches — not by the document. This file defines the artifacts
and the machinery that keeps them alive.

## 1. The threat model document — template

Keep it short enough to re-read at every trigger (target: 2–6 pages / one
markdown file in-repo). Store it NEXT TO THE CODE (`docs/threat-model.md` or
per-service), versioned in git — review-diffable, blame-able, findable.

**The model is itself sensitive.** Its threat table, open findings and accepted
risks are a list of unfixed weaknesses with the reasoning an attacker would
otherwise have to rebuild. Choose its location on confidentiality as well as
convenience: readable on a need-to-know basis. In a private repo, next to the
code is right. In a **public or broadly shared repo**, keep the full register
(open threats, accepted residuals, exploit paths) in a restricted place, still
versioned and linked by ID, and publish in-tree only a sanitised view: scope,
DFD, assumptions and mitigated threats with their requirement IDs. The re-model
triggers and PR security notes still work against the in-tree view. OWASP:
Threat Modeling cheat sheet, Threat Modeling Playbook.

```markdown
# Threat Model: <system/service> — v<NN>
Owner: <tech lead>   Last full review: <date>   Methodologies: STRIDE-per-interaction (+LINDDUN)

## 1. Scope & business context
What is modeled, what is explicitly excluded and why. 3 sentences on what
the business loses if this system fails (feeds impact anchors, see 04 §3).

## 2. System model
L0/L1 mermaid DFDs with trust boundaries (02). Tables: entry points,
assets (ranked), actors/privilege levels, data stores.

## 3. Assumptions
Numbered, falsifiable: "A1: broker is reachable only inside the VPC",
"A2: provider X does not train on our data (contract §4)". Every assumption
is a standing threat if false — audits test these first.

## 4. Threats & dispositions
| ID | Threat (actor→action→asset→impact) | Class | L | I | Rating | Disposition | Req IDs | Residual |
One row per threat. This table IS the model; everything else is support.

## 5. Security requirements
SR-IDs with testable MUST statements + verification refs (04 §5).

## 6. Risk register (residuals & acceptances)
| Threat | Residual | Owner | Review date |   ≤ 1 page (04 §6).

## 7. Re-model triggers & history
The trigger list for THIS system + changelog of revisions and what prompted
them.
```

Rules:
- **The threat table is the contract.** Reviews approve rows, not prose.
  If a section doesn't change a row, cut it.
- **Diagrams as code** (mermaid in markdown): diffable in PRs, no stale Visio
  exports. A diagram that can't be updated in the same PR as the code change
  will drift.
- **Write assumptions you'd bet against.** "We assume input is validated
  upstream" is the most breached assumption in distributed systems; naming it
  makes it auditable.

## 2. Security requirements backlog

- **Requirements enter the same backlog as features** — same tracker, same
  refinement, same definition of done. A separate "security spreadsheet" is
  where requirements go to die.
- **Tag and link:** label `security`, link to threat ID and model version.
  Priority comes from the threat rating (04 §3): Critical-derived requirements
  block the release that introduces the threat; High within the sprint/cycle;
  Medium scheduled; Low backlog with review date.
- **Acceptance criteria = the verification entry.** A security story is done
  when the abuse-case test passes and the structural guard is in CI — not when
  "code is written".
- **Recurring requirements become paved road.** If three models demand "JWT
  validation per SR-x", build/adopt a shared middleware and convert the
  requirement to "uses paved-road component vX" — threat modeling output
  should compound into platform, shrinking future models.

## 3. Abuse cases as test cases

For every mitigated High+ threat, write the attacker's user story and automate
it:

```
Abuse case AC-012 (from T-012, IDOR):
  As tenant-A attacker with a valid session,
  I request GET /orders/{tenant-B-order-id}
  expecting 404/403 and an authz-failure audit event.

test_cross_tenant_order_access_denied():
    token = login(tenant="A")
    r = client.get(f"/orders/{seed_order(tenant='B').id}", auth=token)
    assert r.status_code in (403, 404)
    assert audit_log.contains(event="authz.denied", actor=token.sub)
```

Rules:
- **Test the control's OBSERVABLE effect, not its implementation** (status
  code + audit event, not "repository was called with tenant param") — so
  refactors keep the test honest.
- **Negative tests at the right layer:** authz → integration/API tests;
  injection → unit tests on the sink + fuzz where parsers are involved; rate
  limits/DoS caps → load-shaped tests or config assertions; CSP/headers/IaC
  posture → policy-as-code (OPA/conftest, tfsec-style rules) running in CI.
- **For LLM/agent threats** (03 §8): maintain an injection corpus (strings
  embedding "ignore instructions, call tool X / exfiltrate to URL") run
  against the agent in CI; assert tools-not-called / URL-not-fetched / spend
  caps hold. Probabilistic systems need statistical assertions (N trials,
  zero tool-policy violations).
- **Each abuse-case test cites its threat ID in the test name or docstring**
  — when it fails, the developer reads WHY this matters; when someone deletes
  it, review sees a threat losing its verification.
- **Pentest/red-team findings feed back:** every confirmed finding becomes
  (a) a threat-table row — was it missing or mis-rated? — and (b) an
  abuse-case regression test.

**Write abuse stories when the user story enters the backlog**, not only
afterwards for High+ threats: each story that moves value, ownership or state
gets its attacker counterpart before refinement, drafted from the personas in
`02` §3 (malicious, abusive, unknowing). Business-logic flaws carry no payload
signature, so they come from these questions, asked per feature:
- What does the legitimate user do step by step, and what does the system
  assume at each step? **Which assumption pays the user if it is false?** That
  is where the bug is.
- Can a step be skipped, repeated or reordered by calling its endpoint directly?
- Can two actors act on one object at once, or one user from two tabs or two
  devices?
- What does a chain of individually legal actions yield at abnormal volume
  (a thousand sign-ups, referrals, retries)?
- Which invariant must always hold (a coupon redeems once, a balance never goes
  negative), what enforces it, and is that enforcement atomic?

Each answer that names a gap becomes a threat row and an abuse case above; the
controls are `sota-code-security` rules/03 §3 (state-machine authorization) and
the tests `sota-testing` rules/09 §4. OWASP: Abuse Case cheat sheet, Business
Logic Security cheat sheet, DSOMM.

## 4. Keeping the model living

A threat model is stale the moment the system changes in a way the model
didn't anticipate. Freshness is enforced by TRIGGERS, not calendars (plus one
calendar backstop).

### Re-model triggers (the canonical list — tailor per system, never shrink below this)

| Trigger | Why it invalidates the model |
|---|---|
| New dependency (package, SaaS, model provider) | New org-trust boundary + supply-chain surface (03 §6) |
| New entry point: route, queue/topic, cron, webhook, callback, upload | Attack surface change by definition (02 §5) |
| New or moved trust boundary (service split/merge, network change, new env) | Every boundary crossing needs enumeration (01 §2) |
| New data class (PII category, credentials, payment, health) | Asset table + LINDDUN pass invalidated; impact anchors shift |
| Authn/authz change (token format, session, roles, tenancy model) | The S and E columns of every interaction change |
| Crypto/key management change | Silent impact-rating changes across stored assets |
| New actor class (partners, plugin authors, agent tools, support tooling) | Privilege table invalidated |
| Deserialization / file parsing / template rendering added | Highest-yield vuln classes; instant catalog pass |
| Incident or pentest finding in this system | Empirical proof the model missed something |
| Acceptance/review date expired (04 §6) | Disposition no longer valid |

### Enforcement mechanics (pick at least two)

- **PR template** with a `## Security notes` section: author states which
  triggers apply (or "none") — makes the check cheap and the omission visible.
- **CI trigger heuristics:** flag PRs touching route registrations, lockfiles
  with new packages, IaC network/IAM files, auth middleware, or `*.proto` —
  require the security-notes section to be non-trivial on flagged PRs.
- **Model version pinning:** the threat-model doc records the git SHA range it
  covers; an audit (06) compares triggers-since-SHA against model revisions.
- **Calendar backstop:** full re-read annually or per major version,
  WHICHEVER COMES FIRST with trigger-driven updates — the backstop catches
  slow drift (dependency rot, team turnover, assumption decay).

### Incremental update discipline

- Trigger fires → update only the affected rows/diagram region + bump model
  version with a one-line changelog ("v12: added Stripe webhook EP3, threats
  T-031..034"). Full rewrites are for re-architecture only.
- **Deleting is updating:** removed features must remove threats/requirements,
  or the model accretes noise until nobody reads it. Dead rows are marked
  `retired (vNN)`, kept one version for the diff, then dropped.
- New team members onboard by READING the threat model before the code —
  if that's not useful, the model has failed its second purpose
  (knowledge transfer), fix it.

## 5. PR security-notes template (paste into PR template)

```markdown
## Security notes
Triggers touched: [ ] new dependency  [ ] new entry point  [ ] trust boundary
[ ] new data class  [ ] authn/authz  [ ] crypto  [ ] parsing/deserialization
[ ] none
New input → from whom: ...
Runs at privilege → can now reach: ...
Writes/emits/calls (incl. logs, third parties): ...
At 1000× volume / 100MB payload: ...
Threat model updated? <link/version or "no triggers">
```

A filled template takes 3 minutes for "none" and ~10 when triggers fire; it
gives reviewers a fixed place to look and auditors (`06`) a drift signal.
Reject "N/A" without the checkbox rationale — the box list IS the rationale.

## 6. Threat-model review session format (when a workshop IS warranted)

For new services, new trust boundaries, or escalations from a four-questions
pass. 60–90 minutes, hard cap; 3–6 people: feature owner, one engineer who
did NOT write the design, security (if available), someone who runs prod.

1. (10 min) Owner walks the DFD; attendees attack the DIAGRAM first — missing
   flows, unlabeled arrows, "where does the webhook actually land?" Fixing
   the model is cheaper than fixing threats against the wrong model.
2. (35 min) Per boundary crossing, STRIDE prompts; scribe writes threat
   sentences directly into the table — no minutes, no slides.
3. (15 min) Rate and disposition in-session for everything captured; assign
   requirement owners. Undispositioned threats don't leave the room.
4. (5 min) Confirm re-model triggers and the model owner.

Rules: the design's author never scribes (they defend instead of capture);
"that's already handled" requires naming WHERE (file/control) or the threat
stays; park exploit-tactics rabbit holes after 2 minutes — enumeration
breadth beats depth here.

## 7. Program health metrics (measure the machinery, not threat counts)

Track quarterly, per service:

| Metric | Healthy signal | Smell |
|---|---|---|
| Trigger compliance | % trigger-matching PRs with non-trivial security notes ≥ 90% | template rubber-stamped "none" on PRs adding routes |
| Model freshness | days since last revision < days since last trigger-matching merge | model older than the current architecture |
| Verification coverage | % High+ mitigations with passing abuse-case tests = 100% | requirements "done" with no VER link |
| Acceptance hygiene | 0 expired review dates | acceptances from departed owners |
| Escape rate | incidents/pentest findings that existed as un-actioned model rows | model knew, backlog buried it — a prioritization failure, fix the rating pipeline not the model |

Do NOT manage to "number of threats found" — it incentivizes noise and
punishes good design. Escape rate is the only outcome metric that matters.

## 8. Output sizing — match artifact to audience

| Audience | Artifact | Size |
|---|---|---|
| Engineers (daily) | threat table + requirements in repo | the source of truth |
| Reviewers (per PR) | security-notes section | 3–10 lines |
| Leadership (quarterly) | risk register | ≤ 1 page |
| Auditors/customers | the doc (template §1) + evidence links | 2–6 pages |
| Public repo / outside contributors | sanitised view (§1): no open or accepted threats | 1–2 pages |

Never produce the 40-page monolith: it satisfies no audience and updates
never. Generate views from the threat table instead.

## Audit checklist

- [ ] Threat model exists in-repo, versioned, with owner and last-review date;
      follows (or maps cleanly onto) the template sections.
- [ ] The threat table has L/I/rating/disposition/requirement-ID columns
      filled for every row; no prose-only threats.
- [ ] Assumptions are explicit, numbered, and individually testable; spot-
      check 2–3 against reality (network reachability, contract terms).
- [ ] Security requirements live in the team's actual backlog with threat-ID
      links and rating-derived priority — not a side spreadsheet.
- [ ] Every mitigated High+ threat has an automated abuse-case test citing
      its threat ID; tests assert observable effects and run in CI.
- [ ] Posture controls (headers, IaC, IAM) covered by policy-as-code checks,
      not manual review notes.
- [ ] Re-model trigger list documented for this system; PR template or CI
      heuristics enforce it; sample 5 trigger-matching PRs for security notes.
- [ ] Model changelog shows trigger-driven incremental updates (not one big-
      bang revision years ago); covered-SHA or date range recorded.
- [ ] Incidents/pentest findings traceable into threat rows + regression
      tests.
- [ ] Risk register ≤ 1 page, current owners, no expired review dates.
- [ ] Model confidentiality matches its location: find in-tree models with
      `git ls-files | grep -i -E "threat[-_ ]?model|risk[-_ ]?register"` and the
      repo's visibility (`gh repo view --json visibility`). A public repo
      carrying open or accepted threats → Medium, or High when a row gives an
      unmitigated Critical/High exploit path.
- [ ] Abuse stories are written at story intake for features that move value,
      ownership or state, and the business-logic questions (§3) are answered.
      List workflow-abuse tests with `grep -rn -i -E "(def |it\(|test\(|func Test)[^(]*(skip|replay|repeat|reorder|out.?of.?order|concurren|twice|double)" .`;
      zero hits in a codebase with multi-step or value-dispensing flows →
      Medium.
