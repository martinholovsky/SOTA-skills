# 04 — Lifecycle & Provisioning

Scope: the identity lifecycle — **Joiner-Mover-Leaver (JML)**, SCIM-driven
provisioning *and* deprovisioning, the orphaned-account problem, access reviews /
recertification, just-in-time (JIT) provisioning, and dormant-account detection.

This is the **most-failed area in IAM**, and the failure is almost always the same:
deprovisioning. Creating access is visible and self-correcting (people complain when they
can't log in); removing access is invisible and silent (no one complains that a departed
employee still has a token). Design deprovisioning *first*.

## 1. Source of truth and the JML model

- There is **one authoritative source of identity** (HRIS for employees, a partner
  directory for B2B, a service registry for machines). Every account maps to a record in
  it. Access lifecycle events are *driven by* changes there, not entered ad hoc in each
  app.
- **Joiner**: on hire, the source creates the identity; birthright access (baseline
  accounts/groups, minimal — rules/03) is provisioned automatically; everything beyond is
  requested + approved with an owner and expiry.
- **Mover**: on role/department change, access is **recomputed**, not accumulated —
  old-role access is *removed* as new-role access is granted. Movers are where access
  creep hides: a long-tenured employee who changed teams five times and kept every grant.
- **Leaver**: on termination, **all** access is revoked within a tight SLA — accounts
  disabled, sessions and tokens killed (rules/02 §6, rules/06 CAEP), API keys and
  workload credentials they own reassigned/rotated. Disable before delete (preserve audit
  trail), then delete/anonymize per retention policy (**sota-privacy-compliance**).
- **No self-issued identities on internal tools.** CI/CD systems, code hosts, wikis and
  admin consoles sign users in through the central IdP only. Disable self-registration,
  local accounts and shared accounts there, and restrict sign-in to email domains the
  organisation controls. Otherwise anyone who can reach the login page can mint a
  joiner that no source of truth knows about. OWASP: CI/CD Security cheat sheet.
- **Service accounts cannot log in interactively.** An account used by a backend,
  middleware, database or pipeline is refused at every front-end and interactive
  surface: the web UI, SSO, SSH, console logon (in AD, `Deny log on locally` / `Deny log
  on through Remote Desktop Services`, rules/07 §1). A stolen service credential then
  cannot become a human session. OWASP: Authentication cheat sheet.
- **Log every account creation and change with the access it grants.** Record who
  created or changed the account, which account, and the roles, groups and permissions
  it received, as structured events (OWASP Logging Vocabulary's `user_created` /
  `user_updated` carry the granted attributes). Reconciliation (§3) and reviews (§4) can
  then answer "who granted this, when" from the log rather than from memory. OWASP:
  Logging Vocabulary cheat sheet.

## 2. SCIM-driven provisioning AND deprovisioning

- Use **SCIM 2.0** (RFC 7643/7644, protocol in rules/01 §8) so the source of truth pushes
  create/update/deactivate to every connected app, rather than each app managing its own
  user list.
- **Deprovisioning is the half everyone forgets.** A SCIM `active=false` / DELETE on a
  leaver must:
  - terminate the account's ability to authenticate (not just hide it in the UI),
  - kill live sessions and revoke refresh tokens,
  - cascade to apps that don't speak SCIM (manual runbook with an SLA and a verification
    step).
- Apps that *cannot* be SCIM-provisioned (no connector) are the orphan factory: maintain
  an explicit list, and a manual deprovisioning checklist that is *verified*, not assumed.
- Verify deprovisioning end-to-end: a test that disables a test identity at the source and
  asserts it can no longer authenticate to each downstream app.

## 3. The orphaned-account problem (#1 IAM failure)

An **orphaned account** has no valid owner — the human left, the service was
decommissioned, the contract ended — but the account still authenticates. It is the
prime target for takeover because no one watches it.

- **Reconcile continuously**: periodically diff the IdP/app population against the source
  of truth. Every account with no matching active record is an orphan candidate → disable
  → investigate → delete.
- High-risk orphans: **privileged** accounts of departed admins, **service accounts**
  whose owning team dissolved, **external/B2B** accounts past contract end, **break-glass**
  accounts (rules/05) that linger between uses.
- Every account has a named **owner** (a person, not a team alias that no one reads). An
  ownerless account is itself a finding.
- **AI agents and assistants are identities, so inventory them.** For each one, record
  its identity (service account, OAuth client, workload identity), a human owner, its
  purpose, the permissions it holds and the systems it connects to (MCP servers, SaaS
  integrations, queues). Review the inventory on the access-review cadence (§4) and
  retire stale entries. Hunt for unregistered agents in IdP and audit-log data: OAuth
  grants to unknown clients, tokens used from agent frameworks, service accounts
  created outside the provisioning path. Reconcile them like any other orphan
  candidate. Agents are cheap to start and nobody notices when one outlives its project.
- **Decommissioning a non-human identity has a checklist, and ends in a check.** When an
  agent, service or integration is retired:
  1. mark it retired in the inventory;
  2. revoke its identity, certificates and issued tokens;
  3. disable its service accounts and OAuth clients;
  4. remove its role bindings and policies;
  5. clean up dependent registrations: broker and queue subscriptions, webhooks,
     stored sessions, caches, third-party SaaS integrations, and any credentials it
     created or was handed ("shadow" credentials);
  6. archive its audit logs for the retention period, not delete them with it;
  7. verify that no access remains: attempt authentication and look for activity after
     the retirement date.
  A decommission that stops at "switched it off" leaves the identity working. OWASP:
  DSOMM (Inventory of AI agents; Decommissioning of AI agents).

## 4. Access reviews / recertification

- Periodically, the owner/manager **recertifies** that each grant is still needed.
  Cadence by risk: privileged and SoD-sensitive access quarterly (or tighter); standard
  access semi-annually/annually. This is a SOC 2 / ISO 27001 control —
  **sota-privacy-compliance** for evidence. **Every account is in scope**, not just the
  privileged ones: standard users, service accounts, external/B2B identities and agents
  (§3) are reviewed at least yearly (the cadence OWASP DSOMM asks for all user
  privileges). A programme that reviews only admins misses the access creep of
  everyone else.
- Reviews must be **actionable and default-revoke**: "review by the deadline or access is
  removed," not a rubber-stamp where everything is approved in bulk. Track decisions as
  audit evidence (who certified what, when).
- Reviews surface: role explosion, access creep on movers, orphans, SoD violations,
  unused grants (granted but never exercised — candidates for removal).

## 5. Just-in-time (JIT) provisioning

- **JIT account provisioning** (federation): on first SSO login from a trusted upstream,
  create the local account from verified token claims rather than pre-provisioning
  everyone. Useful for large B2B/social populations. Risks: deterministic linking on a
  verified immutable id (rules/02 §8) and a **deprovisioning** story — a JIT-created
  account still needs a leaver path (it won't get a SCIM DELETE if the upstream doesn't
  send one). Pair JIT-in with reconciliation/dormancy cleanup.
- **JIT privilege elevation** (different thing): request elevated rights for a bounded
  window instead of holding them — covered in rules/05.

## 6. Dormant-account detection

- Run a job that flags accounts with **no successful authentication in N days** (e.g. 30
  for privileged, 90 for standard). Dormant accounts are disabled after a grace/notice
  window; dormant *privileged* accounts are escalated immediately.
- Dormancy detection requires reliable **last-login** telemetry — ensure the IdP emits
  auth events and they are retained (feeds **sota-detection-engineering** for anomaly and
  impossible-travel detection too).
- Distinguish dormant *humans* (likely a missed leaver) from dormant *service accounts*
  (likely a decommissioned workload whose credential is now a standing liability —
  rules/05).

```sql
-- Dormant human accounts (no login in 90d) that still authenticate
SELECT a.username, a.last_login_at, a.owner, a.is_privileged
FROM accounts a
WHERE a.enabled
  AND a.type = 'human'
  AND (a.last_login_at IS NULL OR a.last_login_at < now() - interval '90 days')
ORDER BY a.is_privileged DESC, a.last_login_at NULLS FIRST;
```

## Audit checklist

- [ ] Is there a single authoritative source of identity, and does every account map to a record in it?
- [ ] Is birthright access minimal and automatic, with all other access requested + approved + expiring?
- [ ] On role change (mover), is access **recomputed** rather than accumulated? Look for long-tenured users with grants from old roles.
- [ ] Is there a defined leaver SLA, and does termination revoke ALL access — disable account, kill sessions/refresh tokens, rotate owned credentials?
- [ ] Is deprovisioning SCIM-driven where possible, with an explicit verified manual runbook for non-SCIM apps?
- [ ] Does an end-to-end test confirm a disabled identity can no longer authenticate downstream?
- [ ] Is there continuous reconciliation against the source of truth to find orphaned accounts? (no record → disable → delete)
- [ ] Does every account — human, service, external, break-glass — have a named individual owner?
- [ ] Are there orphaned privileged or service accounts of departed staff / dissolved teams / ended contracts? (highest priority)
- [ ] Are access reviews/recertification run on a risk-based cadence, default-revoke, with decisions retained as audit evidence?
- [ ] Do JIT-provisioned (federated) accounts have a working leaver/dormancy path, with linking on a verified immutable id?
- [ ] Is there a dormant-account detection job (with reliable last-login telemetry) that disables stale accounts and escalates dormant privileged ones?
- [ ] **High** — Do CI/CD systems and internal tools sign in only through the central IdP, with self-registration and local accounts off and sign-in limited to organisation-controlled domains; are service accounts refused at every interactive surface; and is each account creation or change logged with the privileges granted? Self-registration switched on: `grep -rniE '(self_?registration|registration_?allowed|allow_?(self_?)?sign_?up|sign_?up_?enabled|enable_?sign_?up|allow_?registration)["'\'']?\]?[[:space:]]*[:=][[:space:]]*["'\'']?(true|on|yes|enabled)|disable_?registration["'\'']?[[:space:]]*[:=][[:space:]]*["'\'']?(false|off|no)' .`
- [ ] **Medium** — Do access reviews cover every account (standard, service, external, agent) at least yearly, not only privileged access?
- [ ] **High** — Is there an inventory of AI agents and assistants (identity, human owner, purpose, permissions, connected systems), reviewed periodically, with unregistered agents hunted in IdP and audit-log data, and does retiring an agent or non-human identity follow a written checklist that ends in a verified "no access remains"?
