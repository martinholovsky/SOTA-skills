# 03 — Consent & User Rights Engineering

User rights (access, export, rectification, deletion, objection, consent
withdrawal) are product features with APIs, SLAs, state machines, and tests. Most
regimes give you ~30–45 days to fulfill them (GDPR: one month, extensible;
CCPA/CPRA: 45 days) — verify the active SLA for your regimes (rules/04). The
hard part is never the endpoint; it is propagation through every copy of the data
(which is why rules/01 §5's derivative graph must exist first).

## 1. Consent is a state machine, not a boolean

**Rule:** Model consent as an append-only, versioned record per (subject, purpose),
with explicit states and transitions. Never a `marketing_ok boolean` column —
that loses when, to what text, how granular, and whether it was withdrawal or
absence.

```sql
-- GOOD: append-only consent ledger; current state = latest event per (subject, purpose)
CREATE TABLE consent_events (
  id             uuid PRIMARY KEY,
  subject_id     uuid NOT NULL,
  purpose        text NOT NULL,          -- 'marketing_email', 'analytics', 'ml_training'
  action         text NOT NULL CHECK (action IN ('granted','withdrawn','expired','superseded')),
  policy_version text NOT NULL,          -- exact notice text version shown
  mechanism      text NOT NULL,          -- 'signup_checkbox','preference_center','cmp_banner','api'
  occurred_at    timestamptz NOT NULL,
  evidence       jsonb                   -- UI context, locale, IP-derived region (minimized)
);
-- BAD: ALTER TABLE users ADD COLUMN gdpr_ok boolean DEFAULT true;  -- default-on consent is not consent
```

**Required properties:**
- **Granular:** one purpose per consent; no bundling ("agree to terms + marketing
  + analytics" in one checkbox fails GDPR validity and several state laws).
- **Versioned:** record the policy/notice version. When the notice materially
  changes, prior consents are `superseded` and re-prompt is required for the new
  scope — never silently widened.
- **Revocable as easily as granted:** withdrawal path ≤ effort of grant path
  (one click from any marketing email; preference center, not a support ticket).
- **Checked at point of use:** the email sender, the analytics loader, the ML
  training-set builder each query current consent state at execution time — not
  at enrollment time. Stale snapshots of consent are a classic audit finding.
  **For profiling and personalization, the check is an authorization gate, not
  a model input:** it runs before the feature fetch and before the model call,
  and a refused request never reaches either. A `consent` column in the feature
  vector lets the model learn around it, and the personal data was already
  fetched. Where an identifier-free step (contextual scoring of page content)
  runs without profiling consent, consent attaches where its output is joined
  to a user or device identifier — gate that identifier write and the model
  call as two separate checks, since either can happen without the other.
  OWASP: AI-Powered Advertising Systems Security cheat sheet.
- **Propagated to processors:** withdrawal triggers suppression downstream
  (marketing platform suppression list, ad-platform audience removal, CMP signal
  to tags). Track propagation lag; minutes-to-hours, not "next quarterly sync."
  Withdrawal also invalidates what was *derived* under the consent (§5 item 9).
- **Auditable:** for any (subject, purpose, time) you can answer "what was the
  consent state and how do we know" — this is your defense artifact.

```python
# GOOD: point-of-use check — the campaign sender asks the consent service NOW
def send_campaign(campaign, recipients):
    allowed = consent.filter_granted(recipients, purpose="marketing_email")
    suppressed = consent.suppression_list("marketing_email")   # tombstoned/deleted users
    for user in allowed - suppressed:
        ...

# BAD: the campaign audience was exported to a CSV three weeks ago, when
# consent was checked once. 214 users withdrew since. The CSV doesn't know.
```

**Don't use consent as the lawful basis for everything.** Necessary-for-service
processing (auth, billing, fraud) typically rests on contract/legitimate-interest
bases (rules/04 §1); flooding users with consent prompts for essential processing
trains them to click yes and makes real consent meaningless. Map basis per purpose
in the catalog; reserve consent for genuinely optional processing.

## 2. Cookie & tracker governance

**Rule:** No non-essential tag, SDK, or cookie executes before consent for its
category, in jurisdictions requiring opt-in (EU/UK ePrivacy). Technical
enforcement, not banner theater:

- Tag manager / CMP integration gates script injection by consent category;
  verify by loading the site fresh in an EU context and diffing network requests
  pre/post consent. Trackers firing pre-consent = HIGH finding.
- Server-side tagging doesn't exempt you — consent state must gate server-side
  forwarding too.
- Maintain a tracker inventory (it's part of rules/01 §4's processor map): each
  tag → category, vendor, consent purpose, data sent.
- **Honor Global Privacy Control:** CCPA/CPRA regulations require treating GPC as
  a valid opt-out of sale/share; wire the header/JS signal into the same consent
  state machine as the banner. GPC (`Sec-GPC: 1`) is one of several opt-out
  signals to read at feature-fetch time, not only at page load: an IAB Tech Lab
  GPP string (OpenRTB 2.6 carries it in `regs.gpp` / `regs.gpp_sid`); iOS App
  Tracking Transparency (without authorization the advertising identifier reads
  as all zeros from iOS 14.5); and the Android advertising ID, which reads as
  zeros once the user deletes it — Google Play policy forbids linking a reset
  or deleted ID to data derived from the previous one without explicit consent,
  so a zeroed or changed ID is an opt-out event, not a new user. OWASP:
  AI-Powered Advertising Systems Security cheat sheet.
- Dark-pattern check: reject UIs where "Accept all" is one click and "Reject" is
  three; EU regulators have fined exactly this asymmetry.

## 3. DSAR — access & export engineering

**Rule:** Build one export pipeline that walks the data inventory (rules/01), not
N hand-written queries that drift from the schema.

**Identity verification first.** A DSAR is an attack vector: an attacker who can
"export" someone else's data has industrialized doxxing. Verify to the assurance
level of the data: session re-auth for logged-in users; for email-only requests,
verify control of the account identifier (signed link + step-up where data is
sensitive). Never return data to an unverified third-party request; agent
requests (CCPA authorized agents) need documented verification flow. Log the
verification evidence with the request.

**Completeness = inventory-driven.** The export job iterates the catalog's
per-entity field list across SoR + derivatives that hold unique data (support
tickets, billing, comms logs). A hand-rolled export that misses tables added since
it was written is a silent compliance failure — test it: create a fixture user
touching every PII table, export, assert coverage against the catalog (CI test).

**Machine-readable:** JSON/CSV with documented schema (GDPR Art. 20 portability
requires "structured, commonly used, machine-readable"). PDF-only = finding.

**Exclude others' data:** exports must not leak other subjects (e.g., a thread
includes the counterparty's messages — redact/scope). Also exclude your secrets:
internal fraud scores or moderation notes may be exemptable depending on regime —
flag for counsel, don't decide ad hoc in the export code.

**Operational:** ticket every request with a deadline clock; deliver via
authenticated channel (in-app download with expiring link — not an email
attachment); record fulfillment proof.

## 4. Deletion architecture — hard, soft, crypto-shred

**Rule:** Choose the mechanism per datastore deliberately; combinations are normal.

| Mechanism | What it is | Use when | Watch out |
|---|---|---|---|
| **Hard delete** | Row/object physically removed | Primary stores, object storage | FK cascades; ensure replicas/indexes follow; DB may retain in WAL/vacuum lag (acceptable, bounded) |
| **Soft delete → purge** | Flag now, hard-delete via scheduled purge after grace period | Need short undo/fraud window | Soft delete WITHOUT a running purge job is retention-forever wearing a costume — always pair flag with purge automation and monitoring |
| **Crypto-shredding** | Per-subject (or per-tenant) encryption key; destroy the key, all ciphertext becomes noise | Immutable/append-only stores (event logs, Kafka with long retention), backups, archives where physical deletion is impractical | Key management is the whole game (sota-secrets-management); every copy must actually be encrypted under that key — one plaintext side-channel defeats it; key destruction must be provable and itself logged |
| **Anonymization in place** | Strip/overwrite identifying fields, keep skeleton row | Referential integrity or aggregate stats require the row (orders for accounting) | Must pass rules/02 §3's bar — overwriting name with 'DELETED' while keeping address and device ID is not anonymization |

**Legal holds and retention duties override deletion** (tax records, fraud
evidence, litigation hold): model as explicit, reviewable exemptions per data
category in the deletion engine — not as "we keep everything just in case."

## 5. Deletion propagation — the graph is the architecture

**Rule:** Deletion executes against the system of record and propagates along the
recorded derivative graph (rules/01 §5) to ALL of:

1. **Primary DB + replicas** (replication handles it; verify lag-bounded).
2. **Caches** — Redis/memcached keys, CDN-cached responses keyed to the user:
   explicit invalidation or TTL ≤ your propagation SLA.
3. **Search indexes** — delete-by-query/doc-id; verify index rebuild jobs don't
   resurrect from a stale source snapshot.
4. **Analytics/warehouse** — delete or null user rows in warehouse + downstream
   marts; modern lakehouse formats (Iceberg/Delta) support targeted deletes;
   schedule compaction so deleted data physically leaves storage.
5. **Logs** — bounded retention (e.g., 30–90 d) usually suffices instead of
   per-user log scrubbing — acceptable and defensible IF retention is short,
   enforced, and documented; long-retention logs containing PII make per-user
   deletion intractable (that's the finding: fix the logs, per sota-observability).
6. **Backups** — industry-standard approach: backups expire on schedule; deleted
   data dies with the backup cycle; document the max window (e.g., "fully purged
   within retention period + cycle = 35 days") AND ensure restore procedure
   re-applies deletions (replay tombstones after restore) so restoring a backup
   doesn't resurrect deleted users. Crypto-shredding makes backups immediate
   instead.
7. **Third-party processors** — call their deletion APIs (most major processors
   have them) or ticket per DPA; record confirmation.
8. **ML training data & derived models** — remove from training sets and feature
   stores; for models already trained, document the position (retrain cadence
   within which the data washes out; vector-store entries deleted immediately).
   An ML pipeline with no answer here is a HIGH finding as of 2026.
9. **Derived materializations on consent withdrawal** — the same fan-out runs
   for a withdrawn purpose, not only for erasure: audience segments, lookalike
   and propensity scores, cached embeddings, LLM KV/prefix caches and warm
   adapter pools built from the subject's data are invalidated, and caches of
   derived artefacts carry the consent version in their key so a withdrawal
   misses rather than hits. Prove it with a regression test: grant, serve,
   withdraw, replay the same request, and assert no derived artefact is read
   and no profiling model is invoked. OWASP: AI-Powered Advertising Systems
   Security cheat sheet.

```yaml
# GOOD: deletion fan-out is declared, not hardcoded — generated from the
# catalog's derivative graph (rules/01 §5); adding a store without a deletion
# handler fails CI
deletion_targets:
  - system: users-db          # SoR — executes first
    mechanism: hard_delete
  - system: redis-sessions
    mechanism: key_pattern_invalidate   # sess:{user_id}:*
  - system: opensearch-users
    mechanism: delete_by_id
  - system: warehouse.events
    mechanism: iceberg_delete           # + weekly compaction verified
  - system: mailchimp
    mechanism: vendor_api_delete        # confirmation stored
  - system: kafka.audit-topic
    mechanism: crypto_shred             # per-user key in KMS
  - system: feature-store
    mechanism: row_delete + retrain_window: 30d
each_emits: completion_record(system, request_id, count, ts, job_version)
```

**Tombstones:** keep a minimal deletion record (subject ID hash, request ID,
timestamp, scope) so you can (a) prove deletion happened, (b) suppress
re-ingestion (CDC replays, partner re-syncs, backup restores re-inserting the
user), (c) honor "don't recontact" without holding the contact data. The
tombstone itself is minimized — never store the deleted data in it.

**Proof of deletion:** the deletion job emits a signed/immutable completion
record per target system (system, object count, timestamp, job version). This is
your DSAR response artifact and your audit evidence. "We ran a script" is not
proof.

```text
GOOD: DELETE /me → request row (state machine: received → verified → executing →
completed) → fan-out workers per target system from the catalog → per-system
completion records → tombstone → user notified. End-to-end test in CI creates a
full-footprint fixture user, deletes, then asserts zero residue via catalog scan.

BAD: UPDATE users SET deleted = true. Email remains in: warehouse, Algolia,
Mailchimp, Redis sessions, S3 exports, and the model fine-tuned last month.
The DSAR response claimed completion 40 days ago.
```

## 6. Retention enforced by automation, not policy docs

**Rule:** Every datastore/table/bucket/topic holding personal data has a retention
period in the catalog AND a running enforcement mechanism. Policy that no machine
executes is fiction; auditors and regulators increasingly ask to see the mechanism.

Mechanisms by store (set at creation time — IaC templates should require them):
- **Relational:** time-based partitioning + automated partition drop (cheap,
  instant, vacuum-free) > row-level DELETE jobs (verify they actually run and
  keep up).
- **Object storage:** lifecycle rules (transition → expire) on every bucket;
  bucket without lifecycle rule and without documented "indefinite + why" = finding.
- **Streams:** topic retention.ms / compaction; long-retention topics with PII
  prefer crypto-shred keys.
- **Search/cache:** index ILM policies / TTLs.
- **Warehouse:** retention-partitioned raw layer; aggregate-then-drop pattern
  (rules/02 §4 ladder).
- **Backups/logs:** retention policies per rules above.

**Monitor enforcement:** a scheduled check that samples each store for
oldest-record age vs. cataloged retention and alerts on violation. Retention jobs
fail silently for months otherwise — the audit query "show me the oldest PII row"
should never surprise you.

**Pick periods by purpose, not comfort:** retention derives from the purpose's
lifetime (account-life + grace; legal minimums for tax/AML; days-to-weeks for raw
telemetry). "Indefinite" requires a written justification per category and an
owner's signature; default answer is a number.

```hcl
# GOOD: retention is a required, validated attribute in the storage module —
# you literally cannot create a PII bucket without choosing a number
module "bucket" {
  source              = "modules/s3-classified"
  name                = "support-attachments"
  data_classification = "pii"            # required tag, policy-checked (rules/05 §4)
  retention_days      = 730              # creates the lifecycle rule
  # omit retention_days on a pii bucket -> terraform validation error
}

# BAD: aws_s3_bucket with no lifecycle block, created in 2021 by a script,
# 14 TB of exports, classification unknown, owner left in 2023.
```

## 7. Rectification & objection — the forgotten rights

- **Rectification (GDPR Art. 16; correction under state laws):** user-editable
  fields are self-serve; non-editable ones (KYC'd identity) get a support flow.
  The fix executes at the SoR and propagates along the same derivative graph as
  deletion — a corrected email that still bounces from the marketing platform's
  stale copy is a failed rectification.
- **Objection / opt-out of specific processing (Art. 21; state-law profiling
  opt-outs):** implement as a per-purpose processing block in the consent state
  machine (`action: 'objected'`), honored at point of use exactly like
  withdrawal. Objection to direct marketing is absolute — no balancing test,
  suppress immediately.
- **Automated-decision review (Art. 22; state profiling rules):** where fully
  automated decisions have significant effects (credit, hiring, pricing), build
  the human-review path and decision-input logging now — it is also an EU AI Act
  high-risk overlap (rules/04 §5).

## Audit checklist

- [ ] Consent stored as versioned, append-only, per-purpose records with policy version and mechanism; no boolean consent columns; no default-on consent
- [ ] Consent checked at point of use (read the sender/tracker/training-job code), withdrawal ≤ grant effort, propagation to processors automated and lag-monitored
- [ ] Profiling consent is checked before the feature fetch and model call, never passed as a model feature; the identifier join and the model call are gated separately (§1). HIGH where a non-consented request reaches the model. Probe for consent in a feature vector: `grep -rnE "(features|feature_vector|model_input)[^#]*[\"'](has_|is_)?consent[a-z_]*[\"']" .`
- [ ] No non-essential trackers fire pre-consent (verify with fresh-session network diff); GPC honored where CCPA/CPRA applies; GPP, ATT status and Android ad-ID deletion/reset also read at feature-fetch time (§2) — MEDIUM
- [ ] Consent withdrawal invalidates derived segments, scores, embeddings and model caches; a withdraw-and-replay regression test exists (§5 item 9). HIGH if derived artefacts survive withdrawal. Probe for memoized derived artefacts keyed without consent: `grep -rnE -A1 '@(functools\.)?(lru_cache|cache)' . | grep -E 'def [a-z_]*(segment|lookalike|embed|audience)'`
- [ ] DSAR export is inventory-driven with CI completeness test; identity verification precedes disclosure and is logged; output machine-readable; other subjects' data excluded
- [ ] Deletion request flow exists as a state machine with deadline tracking; end-to-end deletion test (fixture user → delete → catalog residue scan) in CI
- [ ] Soft deletes paired with running, monitored purge jobs
- [ ] Propagation covers caches, search, warehouse, logs (or bounded log retention), third-party processors, ML datasets; backup window documented; restore replays tombstones
- [ ] Crypto-shredding used (or justified absent) for immutable/long-retention stores; key destruction provable
- [ ] Tombstones prevent re-ingestion and contain no deleted data; per-system proof-of-deletion records produced
- [ ] Every PII store has cataloged retention + running enforcement (partition drops, lifecycle rules, TTLs) + oldest-record monitoring; "indefinite" only with signed justification
- [ ] Legal holds modeled as explicit exemptions, not blanket non-deletion
- [ ] Rectification propagates along the derivative graph (test: correct a fixture user's email, verify downstream copies)
- [ ] Objection/profiling opt-outs implemented per purpose; direct-marketing objection suppresses unconditionally
- [ ] Storage modules require retention + classification parameters at creation (IaC-level enforcement)
