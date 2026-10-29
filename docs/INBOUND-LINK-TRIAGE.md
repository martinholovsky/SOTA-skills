# Inbound-link triage, 2026-10-29 (ROADMAP 88)

Page 8 of [skill-map.drawio](skill-map.drawio) and `rules_inbound` in
[skill-map.json](skill-map.json) list the domain rules files that no other skill reaches, and
the files exactly one other skill reaches. This records a verdict for each file on both lists, so
the next pass reads the verdict instead of redoing it.

**Population.** The lists came from `scripts/gen-skill-map.py`'s own `no_cross_skill` and
`one_cross_skill`, on the branch after #656: **55** files no other skill reaches (9 of them
reached only by their own `SKILL.md` index) and **109** reached by exactly one, so **164** in
total. The router counts as "another skill" in the generator, and it does here.

**Verdicts.**

- **KEEP-INTERNAL:** the topic belongs to its own skill, so no sibling's task needs it.
- **KEEP-ENOUGH:** the one existing link comes from the sibling that needs it.
- **LINK:** a sibling's rules file discusses the task and had no path to the file. For each
  LINK, both the source line and the target section were read before the link went in.

**How deep each verdict goes.**

- The 164 files were split across four read-only agents, by skill family.
- **Every file was opened**, for its title and section headings. Body sections were read where
  a sibling looked like a candidate.
- The search for siblings that might need a file used targeted `git grep`s, listed in each
  family's notes. **It was not one exhaustive per-topic search for each file.**
- A KEEP verdict therefore means: *no plain need found by headings and the named searches*. It
  does not mean *proven unneeded*.
- The first pass judged the "exactly one" list from file names alone. Those verdicts were not
  accepted; each agent was sent back to open its files.

**Result:** 8 LINK, 156 KEEP. After the links, the generator reads 50 files that no other skill
reaches (7 reached only by their own index) and 111 that exactly one reaches. Five files left the
first list; three on the second gained a second link.

## The eight links added

| target file | linked from | why |
|---|---|---|
| `sota-jvm` rules/07 §2 (per-parser XML hardening) | `sota-code-security` rules/01 §6 (XXE) | §6 names Java parsers and shows one factory; the per-parser matrix lives only in jvm/07 |
| `sota-data-engineering` rules/06 §4 (deletion in immutable stores) | `sota-privacy-compliance` rules/03, erasure step 4 | the erasure step mentioned compaction but not snapshot expiry, which keeps the bytes |
| `sota-threat-modeling` rules/04 §2 (CVSS in context) | `sota-devsecops` rules/13 (CVSS-only SLA is a finding) | the rule rejected CVSS-only ranking with no path to the method |
| `sota-docs-workflow` rules/02 §6 and §7 (changelogs, migration guides) | `sota-api-design` rules/02 §10 | api-design's changelog section had no link to the docs side |
| `sota-mobile` rules/07 §1 (isolation for UI code) | `sota-swift` rules/03 (default isolation) | mobile/07 linked swift/03; nothing linked back |
| `sota-identity-access` rules/03 §5 (policy-as-code engines) | `sota-code-security` rules/03 (ABAC) | the source names OPA, Cedar and Casbin and stops; §5 compares them and their pitfalls |
| `sota-cloud-infrastructure` rules/02 §2 (platform-issued workload identity) | `sota-identity-access` rules/05 (workload identity federation) | identity-access had no link to cloud-infrastructure at all |
| `sota-observability` rules/04 §3 (burn-rate alerts) | `sota-architecture` rules/06 (SLOs with burn-rate alerts) | architecture/06 made burn-rate alerts a launch requirement with no link to the how-to |

## KEEP verdicts, by family

**Security** (9 with no other skill, 15 with one; 1 LINK above):

- *No other skill, KEEP-INTERNAL:*
  - code-security/19 (anti-automation: api-design has no bot or abuse text to hang a link on);
  - confidential-computing/03 and /05;
  - detection-engineering/03;
  - network-security/01;
  - security-compliance/01;
  - security-compliance/03 (devsecops rules/09 already quotes SSDF from the primary document);
  - skill-security/03.
- *One other skill, KEEP-ENOUGH:*
  - confidential-computing/01, /02 and /04 (`sota-kubernetes` never mentions confidential computing);
  - detection-engineering/01, /05 and /07;
  - identity-access/02 and /07;
  - network-security/02 (cloud-infrastructure rules/03 holds its own deny-by-default rules and links network-security /05 and /06);
  - privacy-compliance/05;
  - security-compliance/05;
  - threat-modeling/01, /02 and /03.
- *Searches:*
  - api-design for CAPTCHA, bot, multi-account, signup abuse and scraping;
  - devsecops for SSDF and CVSS;
  - kubernetes for confidential, CoCo and Kata;
  - kubernetes and cloud-infrastructure for microsegmentation, east-west and flat network;
  - code-security rules/03 lines 140–149.

**Infrastructure and data** (11 with no other skill, 30 with one; 3 LINK above):

- *No other skill, KEEP-INTERNAL:*
  - architecture/07;
  - cloud-infrastructure/01;
  - data-engineering/01 and /05;
  - ml-engineering/01, /03, /04, /05 and /06;
  - observability/06.
- *One other skill, KEEP-ENOUGH:*
  - architecture/03, /05, /06 and /08;
  - cloud-infrastructure/04, /05, /06 and /07;
  - data-engineering/02, /03 and /04;
  - databases/02, /05 and /08;
  - devsecops/08, /12, /13 and /15;
  - kubernetes/02, /04, /05, /06 and /07;
  - llm-engineering/03, /06 and /07;
  - ml-engineering/02;
  - observability/03.
- *Searches:*
  - cloud-infrastructure links in identity-access (0);
  - `sota-databases` in cloud-infrastructure/05 (1);
  - llm-engineering links in databases (0);
  - "error budget" and "burn rate" outside observability (5 files).
- *Least-searched verdicts:* databases/02, devsecops/13 and kubernetes/04.

**Product and documentation** (17 with no other skill, 15 with one; 2 LINK above):

- *No other skill, KEEP-INTERNAL:*
  - copywriting/01, /02 and /03;
  - docs-workflow/04;
  - frontend-design/06 and /07;
  - mobile/01, /02, /05 and /06;
  - web-frameworks/01, /04, /05 and /06;
  - web-frameworks/07 (a link from code-security is possible; no plain source sentence found).
- *One other skill, KEEP-ENOUGH:*
  - api-design/04;
  - cli-ux/01, /03 and /04;
  - docs-workflow/01 and /05;
  - frontend-design/01, /02, /03 and /04;
  - mobile/03;
  - ux-writing/01, /02, /03 and /04.
- *Searches:* targeted at api-design ↔ docs-workflow, swift ↔ mobile, and code-security / JS-TS ↔ web-frameworks.

**Cross-cutting and languages** (18 with no other skill, 49 with one; 1 LINK above):

- *No other skill, KEEP-INTERNAL:*
  - async-concurrency/03 and /05;
  - c-cpp/01;
  - dotnet/02 and /04;
  - golang/01;
  - jvm/02;
  - performance/02, /03 and /04;
  - php/03 (code-security already reaches php /01, /02 and /04);
  - python/01;
  - rust/02 and /03;
  - swift/02, /05 and /06.
- *One other skill, KEEP-ENOUGH:*
  - async-concurrency/01, /02, /04 and /06;
  - c-cpp/02, /03, /05 and /07;
  - dotnet/01, /03 and /05;
  - golang/02, /04 and /08;
  - javascript-typescript/01, /03, /05, /06, /08 and /09;
  - jvm/01, /04, /05, /06 and /08;
  - php/02, /04 and /05;
  - python/02, /03, /07 and /08;
  - ruby/01, /02 and /03;
  - rust/01, /04, /05, /06 and /08;
  - shell-scripting/04, /07 and /09;
  - swift/01, /07 and /09;
  - testing/03, /05 and /08.
- *Notes:*
  - A language file reached from its matching cross-cutting skill is the expected shape. Three cross-cutting skills declare a `per_language` file per language (invariant 42 C6).
  - ruby/03 §4 was checked as a candidate from code-security rules/17 and kept: that passage gives per-stack examples, not a per-language index.
  - This family's "exactly one" verdicts rest on headings, without a per-topic search.

## Re-running it

Regenerate the map (`python3 scripts/gen-skill-map.py`) and diff its two lists against the
files named here. Triage only the files that are new to a list, or whose citing skill changed.
