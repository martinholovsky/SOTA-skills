# 06 — AUDIT Mode: Reconstructing a Threat Model from an Existing System

Goal: given a codebase (plus IaC, configs, pipelines), rebuild the threat
model the system IMPLIES, compare it with whatever the team INTENDED, and
report the gaps as severity-rated, evidence-backed findings. This is gap
analysis against catalogs — not pentesting (you prove absence of controls,
not presence of exploits) and not code review (you work at the
boundary/control level, not line-by-line).

## 1. Audit procedure (ordered; timebox each phase)

1. **Collect artifacts (30 min):** repo(s), lockfiles, IaC, CI configs,
   Dockerfiles/k8s manifests, any existing threat model/architecture docs,
   `.env.example`, OpenAPI/proto specs. Note what you were NOT given —
   un-auditable surface goes in the report as such, never silently skipped.
2. **Extract the system model** per `02` §B: entry-point sweep, store/asset
   inventory, actor/privilege table, inferred trust boundaries. Output the
   reconstructed mermaid DFD — this diagram is deliverable #1 even if you find
   nothing else; most teams have never seen their real attack surface drawn.
3. **Reconstruct intent:** read existing docs/ADRs/old models, auth middleware
   comments, IaC structure. Write down the implied assumptions ("services
   trust the gateway's headers", "bucket is private"). Each assumption becomes
   a test target.
4. **Run the catalogs (`03`)** against each component → control-presence
   matrix (§2 below). Prioritize components on paths to top-3 assets when
   time-boxed; record de-scoping explicitly.
5. **Test assumptions from step 3:** for each, find the code/config that makes
   it true. No evidence = broken assumption = finding (these are usually the
   Criticals: "gateway-only trust" with services bound to 0.0.0.0).
6. **Gap analysis (§3):** absent/partial controls → threat sentences → rate in
   deployment context (`04` §3) → findings (§6).
7. **Deliver (§7):** findings report + reconstructed model + remediation
   ordering. Hand the reconstructed model to the team as their new baseline
   (`05` §4) — the audit's lasting value.

## 2. Control-presence matrix

For every (component × applicable catalog item) record one of:

| State | Meaning | Evidence required |
|---|---|---|
| **Present** | Control implemented and reachable on all relevant paths | file:line of the control + how you confirmed coverage |
| **Partial** | Implemented but bypassable, inconsistent, or covering some paths | both: where it works and where it doesn't |
| **Absent** | No control found after a genuine search | the searches performed (so reviewers can re-run them) |
| **N/A** | Catalog item doesn't apply | one-line reason |
| **Unverifiable** | Outside provided artifacts | what artifact would settle it |

Rules:
- **Evidence or it didn't happen — in both directions.** "Present" without
  file:line is as worthless as "Absent" without the search trail. Audits get
  challenged; the matrix is your defense.
- **Partial is the most important state.** One authz-checked endpoint proves
  the team knows the pattern; the seventeen unchecked ones are the finding.
  Inconsistency also tells you remediation is adoption, not invention.
- **Sample honestly:** for repetitive surfaces (50 routes), sample ≥20% plus
  ALL routes touching top assets; state the sampling rule in the report.
- **Check the negative space:** middleware exclusion lists, `// TODO: auth`,
  `@SkipAuth`-style decorators, IaC `count = 0`/commented blocks, disabled
  tests with `security` in the name, `.allowlist` files. Disabled controls are
  stronger findings than never-built ones (someone decided).

Matrix excerpt (orders-api × API catalog, `03` §2):

| Catalog item | State | Evidence |
|---|---|---|
| Object-level authz | **Partial** | tenant check in invoice_repo.py:22, payments.py:31; ABSENT in order_repo.py:18 + 8 of 11 sampled by-id routes |
| Mass assignment | Present | DTO allowlists via schemas/*.py; no `**request.json` hits |
| SSRF controls | **Absent** | webhook "test" fetch at hooks.py:77, no allowlist; searches: `requests.get(`, `urlopen`, `httpx` |
| Rate limiting | **Unverifiable** | nginx config not provided; app-level none found |
| Deserialization | N/A | JSON only; no pickle/yaml.load hits |

## 3. Gap analysis — from absent control to ranked finding

For each Absent/Partial cell:

1. **Write the threat sentence** the missing control would have addressed
   (actor → action → asset → impact), using the actual actors and assets from
   the reconstructed model — never "an attacker could potentially".
2. **Walk the real path:** can the named actor actually reach the weakness
   from an entry point in THIS deployment? An unparameterized query fed only
   by a config constant is hygiene (Low), not injection (Critical).
   Reachability is what separates an audit from a scanner run.
3. **Classify the gap:**
   - **Missing primary control** — nothing stands between actor and asset
     (no authz check on a reachable endpoint). Rates on raw L×I.
   - **Missing defense-in-depth** — primary control exists; backstop absent
     (authz present, but no RLS / no audit log). Cap at one band below what
     primary-control failure would rate, and say which primary it backstops.
   - **Posture/hygiene** — weakens future changes rather than today's paths
     (shared DB superuser in a single-service system). Usually Low/Medium with
     a "rises to X when Y" note.
4. **Chain before rating.** Individually-Medium gaps that compose into a
   Critical path get ONE chained finding rated for the chain (SSRF [M] +
   IMDSv1 [M] + over-privileged role [M] = metadata-credential takeover [C]),
   with member gaps listed as remediation points. Report the chain, not three
   medium tickets nobody connects.

## 4. Severity calibration (audit-specific)

Apply `SKILL.md` conventions + `04` §3 anchors, with these audit rules:

- **Rate what IS, not what might be coded later.** Severity reflects current
  deployment context; include a "context sensitivity" note when one config
  change would jump the rating ("Medium today; Critical if this service is
  ever exposed publicly — see T-7").
- **Unverifiable ≠ Low.** A control you couldn't verify on a Critical path is
  reported as "Unverified, potential High" with the artifact request —
  downgrading for lack of access rewards opacity.
- **Broken stated assumptions inherit the severity of what relied on them.**
  If "internal network is trusted" underpins all service authn and is false,
  that single finding is Critical even though each individual service merely
  "lacks mTLS".
- **No severity inflation for volume.** Forty Low hygiene findings do not sum
  to a High; instead emit one thematic finding ("input validation is not
  systematic: 40 instances, list attached") so the remediation is a pattern
  fix, not whack-a-mole.

## 5. Tooling and timeboxing

Tools feed the audit; they are never the audit:

- **Use scanners as input, not output.** SAST/dep-scan/IaC-scan results are
  candidate Absent/Partial cells — each still needs the reachability walk
  (§3.2) before it becomes a finding. Forwarding scanner output as an audit
  is the canonical failure mode of this discipline.
- **Targeted code sweeps** (opengrep/grep) excel at the matrix's repetitive
  cells: authz-check presence per route, raw-SQL escape hatches, `verify=False`,
  skip-auth decorators, `dangerouslySetInnerHTML`. Save the rule set — it
  becomes the structural regression guard you recommend (`04` §5 VER-2).
- **Read IaC before code.** Network policy, IAM, and bucket policy answer
  reachability questions that would take hours to establish from app code.

Timebox tiers (state which tier the report represents):

| Tier | Budget | Scope |
|---|---|---|
| Rapid | 1 day | DFD + entry-point sweep + assumptions test + top-asset paths only; catalogs for the 2–3 highest-risk components |
| Standard | 3–5 days | Full matrix on all components on top-3 asset paths; sampled elsewhere |
| Deep | 2+ weeks | Full matrix everywhere + chain construction + process meta-audit |

A Rapid audit that says so is honest; a Rapid audit formatted like a Deep one
is malpractice — the un-examined surface must be listed (§1.1).

## 6. Finding format (binding)

Every finding uses the `SKILL.md` format. Worked example:

```
[HIGH] Cross-tenant order read via unscoped lookup (orders-api, STRIDE-E/I)
Location: services/orders/handlers/get_order.py:41; absent tenant filter in
          repositories/order_repo.py:18
Threat: Any authenticated customer can read any other tenant's orders
        (PII: names, addresses — asset A1) by iterating sequential order
        IDs on GET /orders/{id}, because the lookup filters by id only and
        IDs are sequential (migrations/0042_orders.sql:7).
Evidence: get_order.py:41 `order = repo.get(order_id)` — no tenant_id in
          query; confirmed pattern on 9 of 11 by-id endpoints sampled
          (exceptions: invoices, payments — both filter by tenant).
Recommendation: enforce tenant scoping in the repository layer (single
          choke point, pattern already exists in invoice_repo.py:22);
          switch new IDs to UUIDv7. Map to SR-104; add abuse-case test
          per 05 §3.
Residual risk if accepted: mass PII enumeration by any self-service
          signup; likely notifiable breach.
```

Rules:
- One finding = one decidable remediation. Split findings the team would
  assign to different owners; merge instances of one pattern (per §4).
- The Evidence line must let a skeptic reproduce your conclusion from the
  repo alone. Quote minimally; cite precisely.
- Recommendation names WHERE the control goes and reuses the team's existing
  good patterns when they exist (adoption beats invention, §2).
- Positive observations (Present controls on critical paths) get a short
  section — they calibrate trust in the audit and stop teams "fixing" what
  works.

## 7. Audit report structure

```
1. Scope & method: artifacts received/withheld, sampling rules, timebox,
   catalogs applied, un-audited surface.
2. Reconstructed system model: DFD + entry-point/asset/actor tables (02).
3. Findings: Critical → Low, chained findings first within band.
4. Thematic observations: systemic patterns (one per theme) + positives.
5. Control-presence matrix: appendix, full table with evidence.
6. Assumption test results: stated/implied assumptions, held or broken.
7. Proposed baseline: the model handed back for living maintenance (05 §4),
   pinned to the audited git SHA.
8. Remediation ordering: chains broken at cheapest link first; pattern
   fixes over instance fixes; quick wins (config-level Criticals) flagged.
```

Meta-findings — the audit also rates the team's PROCESS:
- No threat model existed → Medium process finding (plus the baseline you
  deliver remediates it).
- Model existed but drifted (trigger-matching changes since last revision,
  `05` §4) → finding, with the missed triggers listed.
- Expired risk acceptances, orphaned threats without dispositions, abuse-case
  tests deleted/skipped → findings per `04`/`05` checklists.

## Audit checklist (meta — quality bar for the audit itself)

- [ ] Artifact inventory recorded, including what was NOT provided; nothing
      silently skipped — unverifiable surface reported as such.
- [ ] Reconstructed DFD + entry-point sweep completed per 02 §B before any
      catalog work; sweep commands/searches reproducible.
- [ ] Implied assumptions written down and each tested against code/config;
      broken assumptions rated by what relied on them.
- [ ] Control-presence matrix complete for in-scope components; every cell
      Present/Partial/Absent/N-A/Unverifiable with evidence or search trail.
- [ ] Sampling rules stated; all top-asset paths examined, not sampled.
- [ ] Negative space checked: exclusion lists, skip-auth decorators, disabled
      tests, commented-out IaC.
- [ ] Reachability walked for every finding; hygiene vs. primary-control vs.
      defense-in-depth gaps distinguished and rated accordingly.
- [ ] Exploit chains assembled and rated as chains; no severity-by-volume.
- [ ] Every finding in the binding format with file:line evidence and a
      located, pattern-reusing recommendation.
- [ ] Positive controls acknowledged; process meta-findings (stale model,
      expired acceptances) included.
- [ ] Baseline model delivered, pinned to the audited SHA, ready for living
      maintenance per 05.
