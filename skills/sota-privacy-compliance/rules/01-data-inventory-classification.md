# 01 — Data Inventory & Classification

You cannot protect, minimize, export, or delete what you have not mapped. Every
other rule in this skill assumes an inventory exists. In AUDIT mode, building the
inventory IS step one — most findings fall out of the gap between what the org
thinks it stores and what it actually stores.

## 1. The data inventory is a living artifact, generated from code

**Rule:** Maintain a machine-readable data inventory (catalog of personal-data
fields with classification, purpose, owner, retention, and flow targets) that is
derived from schemas and code, validated in CI, and versioned in git. A spreadsheet
updated annually before the audit is not an inventory; it is a memorial to last
year's architecture.

**Rationale:** GDPR Art. 30 requires records of processing activities (RoPA); SOC 2
and ISO 27001 (A.5.9, A.5.12 in the 2022 control set) require asset inventories and
classification. But the engineering reason is stronger: every DSAR, deletion
request, breach-scope assessment, and residency question starts with "where is this
person's data?" — and you need the answer in minutes, not weeks.

**Implementation pattern — annotate at the schema, derive the map:**

```sql
-- GOOD: classification and purpose live with the column (PostgreSQL COMMENT,
-- harvested by a CI job into the catalog)
CREATE TABLE customers (
  id            uuid PRIMARY KEY,
  email         text NOT NULL,  -- @pii:contact @purpose:account,transactional-email @retention:account-life+30d
  full_name     text,           -- @pii:identity @purpose:account @retention:account-life+30d
  date_of_birth date,           -- @pii:identity @purpose:age-verification @retention:account-life
  health_notes  text            -- @pii:special-category @purpose:?? <- FAILS CI: special-category needs explicit purpose + lawful basis ref
);
```

```yaml
# GOOD: equivalent for typed schemas — protobuf/avro/JSON-schema custom options
# message Customer {
#   string email = 1 [(privacy.class) = PII_CONTACT,
#                     (privacy.purpose) = "account,transactional_email",
#                     (privacy.retention) = "account_life_plus_30d"];
# }
```

```text
BAD: a Confluence page titled "Data Map v3 FINAL (2)" last edited 14 months ago,
listing tables that were renamed two migrations back and missing the Kafka topics,
the Mixpanel events, and the support-ticket attachments entirely.
```

**CI enforcement:** a check that (a) every new column/field in a migration or
schema diff carries a classification annotation, (b) `special-category` and
`financial` tiers also carry purpose + retention, (c) the generated catalog diff is
attached to the PR. New unannotated field = failing build. This converts the
inventory from a documentation chore into a property of the codebase.

## 2. Classification tiers — pick few, define sharply, bind controls to tiers

**Rule:** Use a small fixed tier set; every tier maps to mandatory minimum controls.
A classification scheme without attached controls is taxonomy theater.

| Tier | Definition | Examples | Minimum controls |
|---|---|---|---|
| `public` | Intended for publication | Docs, marketing pages | Integrity only |
| `internal` | Business data, no personal data | Configs, non-PII metrics | Access control, standard retention |
| `confidential` | Business-sensitive, no personal data | Contracts, source code, pricing | Need-to-know access, encryption at rest |
| `pii` | Relates to an identified/identifiable person | Name, email, IP, device ID, user ID, location, behavioral events | Everything above + purpose binding, retention limit, DSAR/deletion coverage, processor mapping |
| `pii:special-category` | GDPR Art. 9 / sensitive under US state laws | Health, biometrics for ID, race/ethnicity, religion, sexual orientation, precise geolocation (CPRA), genetic data, children's data | Everything above + explicit lawful basis/consent record, strictest access (break-glass audited), DPIA, encryption with dedicated keys |
| `financial/regulated` | Payment card data (PCI), bank details, regulated sector data | PAN, CVV, account numbers, PHI under HIPAA | Tier controls of the governing standard (PCI DSS scoping — rules/04; HIPAA safeguards — rules/04) |

**Sharp edges to encode in the definitions:**
- **Identifiers are PII.** IP addresses, cookie IDs, device fingerprints, internal
  user UUIDs — anything linkable to a person is personal data under GDPR and most
  state laws. Classifying `user_id` as `internal` is the single most common
  inventory error.
- **Derived data inherits the tier.** An ML embedding of a support ticket, a
  propensity score, a session replay — derived from PII = PII.
- **Aggregates can drop tier only after a documented anonymization review**
  (rules/02 §4) — not by assertion.
- **Inference creates special-category data.** Purchase history that reveals health
  conditions or religion is special-category by inference; regulators have treated
  it as such.

## 3. PII discovery — schemas are the start, not the whole hunt

**Rule:** When building the inventory (or auditing), sweep every place data comes
to rest, not just the primary database. Personal data accumulates in six shadow
locations that schemas don't show:

1. **Logs** — request/response bodies, exception messages with user objects, debug
   logging of auth tokens and emails. Grep patterns: log statements interpolating
   `user`, `email`, `req.body`, `params`, `headers`; structured-logging fields
   without an allowlist. (Redaction mechanics: sota-observability.)
2. **Object storage** — uploads, exports, report dumps, CSVs from "one-off"
   scripts. Audit bucket-by-bucket: what writes here, does it contain PII, is
   there a lifecycle rule, who can read it? Use cloud-native scanners (e.g., DLP
   services that sample objects) for backfill discovery; use path/prefix
   conventions + IaC review for prevention.
3. **Backups & snapshots** — full copies of everything above, often with longer
   retention than the source and weaker access control. Inventory must record
   backup retention per datastore (deletion implications: rules/03 §5).
4. **Analytics & event pipelines** — every `track()` call is a collection event.
   Audit the event schema registry (if none exists: HIGH finding); look for
   free-text properties, URLs with query params (tokens, emails in
   `?email=`), and identify-calls shipping whole user objects to third parties.
5. **Search indexes & caches** — Elasticsearch/OpenSearch documents, Redis session
   blobs, CDN-cached API responses. Re-indexed and re-cached copies outlive
   source-row deletion unless explicitly propagated.
6. **ML training data & feature stores** — training snapshots, fine-tuned model
   artifacts, vector stores of user content. Record dataset lineage: which
   training sets contain which user cohorts, so deletion/consent changes can be
   honored (rules/03 §5).

**Audit greps that pay for themselves** (adapt per stack):

```bash
# Email/phone/SSN-shaped literals & column names in schemas and code
rg -i '(ssn|social_security|date_of_birth|dob|passport|tax_id|national_id)' --type sql
rg -i '(email|phone|address|geo|lat.?lon|ip_addr)' migrations/ schemas/
# PII flowing into logs
rg 'log(ger)?\.(info|warn|error|debug)\(.*\b(user|email|req\.body|password|token)' src/
# Analytics calls with raw payloads
rg '(track|identify|capture)\(.*\b(email|name|phone)' src/
# Query params carrying identity — rg honours .gitignore even for a path you name,
# so a gitignored logs/*.log is skipped silently; -uu searches it, -z reads rotated .gz
rg '[?&](email|token|user_id|ssn)=' src/
rg -uuz '[?&](email|token|user_id|ssn)=' logs/
```

Automated scanners (regex + ML classifiers over column names, sampled values, and
object stores) are good for breadth; they miss context (an `id` column that is a
person) and produce false positives (a `name` column for products). Always pair
scanner output with schema-owner review.

## 4. Data flow mapping — processors, subprocessors, and egress

**Rule:** For every PII category, the inventory records every external destination:
processor name, what data, what purpose, what region, DPA status, and the code path
or integration that sends it. Generate the candidate list from code and config, then
reconcile with contracts:

- Dependency manifests + SDK initializations (Stripe, Segment, Sentry, Intercom,
  OpenAI, ...): each analytics/error/support/AI SDK is a processor.
- Egress audit: outbound HTTP destinations from production (service-mesh or
  NAT/proxy logs) vs. the approved processor list. Unknown destination receiving
  request bodies = investigate immediately.
- Webhooks, ETL jobs, reverse-ETL, data-share agreements (Snowflake shares, S3
  cross-account replication).

```yaml
# GOOD: flow record (one per processor, in the versioned catalog)
processor: sentry
data: [pii:contact(email), pii:identity(username), ip_address]   # via error events
purpose: error monitoring
region: us            # check against residency requirements (rules/04 §7)
dpa: signed-2025-03   # link to contract record
code_paths: [src/instrument.ts]
controls: [beforeSend PII scrubber — tested in test/sentry_scrub.test.ts]
```

A processor in production without a DPA and inventory entry is a HIGH finding
(CRITICAL if special-category data flows to it). Subprocessors of your processors
matter too: your vendor's subprocessor list is part of your transfer analysis
(rules/04 §1) and your customers' subprocessor disclosures.

**Internal flows count as flows.** Map cross-boundary internal movement as well:
service A's PII landing in team B's warehouse, the data-science sandbox with a
prod replica, the staging environment seeded from production. Each is an access
expansion that the inventory must show. Production data in staging/dev is a
standing HIGH finding — seed non-prod from synthetic or irreversibly masked data
(masking mechanics: sota-databases), and treat any "temporary" prod copy as
having a TTL and an owner.

## 4b. Ownership — every data category has a name attached

**Rule:** Each PII category and each datastore has a designated owner (a team,
with an individual steward) recorded in the catalog. Owners answer DSAR-scoping
questions, approve purpose changes, sign retention justifications, and receive
the violation alerts from retention monitoring (rules/03 §6). Unowned data is
unmaintained data: when the team that built the feature dissolved, its tables
became the audit findings of two years later. CI can enforce this too — a catalog
entry whose `owner` no longer matches an active team in the org chart goes stale
loudly, not silently.

## 5. System-of-record designation — one writer, everyone else derives

**Rule:** For every personal-data entity (user profile, consent state, contact
info), designate exactly one system of record (SoR). All other copies are
declared derivatives with a recorded sync mechanism and staleness bound. Deletion,
rectification, and export execute against the SoR and propagate outward along the
recorded derivative edges.

**Rationale:** When three services each hold an editable copy of the user's email,
rectification (GDPR Art. 16) is unimplementable and exports self-contradict. The
deletion graph (rules/03 §5) is exactly the derivative graph — if it isn't
recorded, deletion is guesswork.

```text
GOOD: users-service = SoR for profile. CRM, analytics, search index are listed
derivatives fed by CDC stream; deletion tombstone flows the same path; max
staleness 5 min, monitored.

BAD: email stored in users DB, billing DB, and marketing platform; support staff
edit the CRM copy directly; nobody syncs back. Rectification request updates one
of three copies. Export returns the stale two.
```

## 6. Backfill strategy for the unmapped legacy estate

When auditing (or inheriting) a system with no inventory, sequence the build —
don't attempt a perfect map before extracting value:

1. **Schema sweep first** (hours): dump all schemas, flag candidate PII columns
   by name patterns + sampled values; classify with owners in a working session.
   This catches 70% and produces the catalog skeleton.
2. **Egress second** (days): SDK/dependency scan + outbound traffic review →
   processor map (§4). Third-party flows carry the highest regulatory risk per
   unit effort.
3. **Shadow locations third** (weeks): logs, buckets, analytics, backups (§3),
   prioritized by access breadth — a world-readable bucket outranks a locked
   backup vault.
4. **Wire the CI gate immediately** (§1) — even before backfill completes — so
   the unmapped estate stops growing while you drain it.
5. **Unstructured/SaaS sprawl last**, and accept sampling: ticket systems, CRMs,
   spreadsheets, chat exports. Inventory the *systems* and their retention/access
   even where field-level mapping is impractical; field-level fidelity there is
   rarely worth the cost.

Record confidence levels per entry (`verified-by-code` / `declared-by-owner` /
`scanner-detected`) so consumers of the map (DSAR jobs, breach scoping) know
what's load-bearing.

## Audit checklist

- [ ] Machine-readable data inventory exists, is versioned, and was updated within the current quarter (or is CI-generated)
- [ ] Every schema field holding personal data carries classification + purpose + retention annotations; CI rejects unannotated additions
- [ ] Classification tiers have documented, bound minimum controls; spot-check 5 `pii` fields for control compliance
- [ ] Internal identifiers (user IDs, device IDs, IPs) are classified as PII, not `internal`
- [ ] Special-category data is explicitly tiered with lawful-basis reference and DPIA link
- [ ] Logs, object storage, backups, analytics events, search indexes, caches, and ML datasets are covered by the inventory (sample each)
- [ ] Analytics event schema registry exists; no free-text/whole-object payloads to third parties
- [ ] Processor list is reconciled against actual production egress and SDK usage; every processor has a DPA reference and region
- [ ] Each personal-data entity has a designated system of record; derivative copies and sync paths are recorded
- [ ] Backup retention per datastore is recorded and consistent with deletion obligations
- [ ] Every data category and datastore has a current owner; staleness is detected (owner no longer exists → alert)
- [ ] No production personal data in staging/dev/sandbox environments (or masked irreversibly); "temporary" copies have TTL + owner
- [ ] Catalog entries carry confidence levels; load-bearing consumers (DSAR, breach scoping) rely only on verified entries
- [ ] RoPA (where GDPR applies) is derivable from the inventory, not maintained as a separate divergent document
