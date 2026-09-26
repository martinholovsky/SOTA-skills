# 03 — Authorization & Access Control

Scope: object-level authorization (IDOR/BOLA), function-level access control,
RBAC/ABAC/ReBAC, deny-by-default, multi-tenant isolation, confused deputy.
Maps to OWASP A01:2025 (Broken Access Control — still the #1 web risk, and since
the 2025 release also home to SSRF), API1:2023 (BOLA), API5:2023 (BFLA),
CWE-862/863/639/284.

Core principle: **authentication says who you are; authorization must be checked
again for every object and every operation.** The most common real-world vuln class
is not injection — it is a handler that fetches by ID and forgets to ask "does
*this* user own *this* row?"

## 1. Deny by default (CWE-862)

- Every route/handler/RPC requires an explicit authorization decision; absence of
  a check = denied, enforced by middleware/framework, not by convention.
  An unannotated endpoint should fail closed or fail CI.
- Centralize policy in one enforcement layer (middleware, policy engine, service
  decorators). Scattered inline `if user.role == "admin"` checks drift and get
  missed on new endpoints.
- Apply to **all** entry points: REST, GraphQL resolvers (each field/resolver,
  not just the query root), WebSocket messages, gRPC methods, background-job
  enqueue endpoints, and "internal" admin routes (CWE-425 — forced browsing;
  hidden ≠ protected).
- **A failed check ends the request.** A denial that only *sets* a response — a redirect, a
  401/403 — without `return`/`exit` lets the handler run on into the protected code. Measured
  2026-09-25 on PHP 8.5 (php-cgi): `header("Location: /login")` sent the 302 and the file
  write on the next line still ran. Order matters too: authenticate, and run every check that
  does not need the body, before the body is parsed or acted on — not only for webhook
  signatures. OWASP: Code Review Guide v2.
- **Keep an authorization inventory and test it.** Write down, per resource, who may read and
  who may write each field, including rules that depend on the object's state or status (a
  draft's price is editable, a paid one's is not). Test it both ways: the presentation layer's
  gating (hidden buttons, disabled fields) must match the server rules, and a security test
  must fail when a new route, resolver or cache appears with no access classification. OWASP:
  ASVS 5.0 V8.1.2; Next.js Security cheat sheet; Secure Coding Practices QRG.
- Authorize HTTP methods independently: `GET /users/1` protected but
  `PATCH /users/1` open is a classic miss; so are method-override headers
  (`X-HTTP-Method-Override`).
- GraphQL needs resolver-level enforcement because one endpoint serves every
  shape — route-level middleware sees only `/graphql`:

```js
// GOOD: authz attached to the field, evaluated per resolution
salary: {
  type: GraphQLFloat,
  resolve: requireAuthz("employee:salary:read",        // permission, not role
    (emp, _, ctx) => ctx.authz.sameOrgAndHR(ctx.user, emp))(salaryResolver),
}
// also: depth/complexity limits and introspection gating -> rules/06 §5, rules/07 §4
```

```python
# GOOD pattern: framework-level default-deny
@app.before_request
def enforce():
    rule = ROUTE_POLICY.get(request.endpoint)   # no entry -> deny
    if rule is None or not rule.allows(current_user, request):
        abort(403)
```

## 2. Object-level authorization — IDOR/BOLA (CWE-639)

- Every fetch/update/delete by identifier must verify the caller's relationship
  to **that specific object** — ownership, tenant membership, or an explicit
  grant. Role checks alone don't cut it: "any authenticated user" + sequential
  IDs = full data dump.
- Encode the check in the query itself so it cannot be skipped:

```python
# BAD: fetch then (maybe) check
doc = Document.get(doc_id)
return doc                                # whose doc?

# GOOD: ownership is part of the lookup; absence = 404
doc = Document.get(id=doc_id, owner_id=current_user.id)  # or tenant_id=...
if doc is None: abort(404)                # don't leak existence with 403 vs 404
```

- Audit every place an ID arrives: path params, query strings, JSON bodies
  (including nested IDs like `{"comment": {"post_id": ...}}`), bulk endpoints,
  export/report jobs, file-download handlers, and ID arrays in batch operations
  (each element needs the check).
- Random IDs (UUIDv4) reduce enumerability but are **not** authorization
  (CWE-340 misuse). Treat guessable-vs-random as defense in depth only.
- Indirect references: where practical, scope all queries through the user's own
  collection (`current_user.documents.find(id)`) so there is no unscoped accessor
  to misuse.
- **Take no id at all where you can.** An object that belongs to the caller (their profile,
  cart, settings) is resolved from the authenticated principal on a `/me`-style route, so
  there is nothing to tamper with. Where ids must be exposed, a per-user or per-session
  indirect reference map (a short token the server maps to the real id for that user only) is
  an option. Encrypting or signing ids is not a substitute for the ownership check, and doing it
  safely is hard (key handling, malleability, reuse across users); keep the check either way.
  OWASP: Insecure Direct Object Reference Prevention, Authorization cheat sheets; Code Review
  Guide v2.

## 3. Function-level authorization — BFLA (CWE-863)

- Verify the caller may perform the *operation*, not just see the object: a user
  who can read an invoice must not be able to call `POST /invoices/{id}/refund`.
- Don't trust client-supplied role/privilege fields — role comes from the
  server-side session/token claims validated against the DB, never from a request
  body (`{"role": "admin"}` mass assignment, see rules/07) or a client-set header
  (`X-Admin: true`).
- **Privilege copied into a session goes stale.** A role, permission set or tenant list stored
  in the session (or a token claim) at login is a snapshot. Re-read it from the authoritative
  store for sensitive decisions, or re-validate on an interval short enough for your revocation
  needs; keep a per-user permission version so a role change forces re-authentication or a
  session refresh. When privilege drops, remove every higher-privilege flag and cached datum
  the session carries, not just the role field. Session-ID rotation on elevation is rules/17
  §2; IdP-pushed revocation is `sota-identity-access` rules/06 §5. OWASP: Code Review Guide v2,
  Go-SCP (access control).
- State-machine authorization: actions valid only in certain states (approve own
  expense report, re-trigger completed payment) need state checks server-side —
  workflow bypass is an authz bug. Enforce the full doctrine (OWASP Business Logic):
  validate the current state on every step and reject out-of-order transitions;
  **mark one-time operations consumed** so a captured request can't be replayed
  (payment capture, coupon redemption, password-reset token); expire abandoned
  partial-workflow state; and **never store the workflow position in a client-readable/
  writable field** — keep it server-side keyed to the session/resource. A rejected out-of-order
  step is also a **security event**: log it at high severity with the user and the step (the
  OWASP Logging Vocabulary names it `sequence_fail` at CRITICAL), because a legitimate UI rarely
  produces one and detection can key on it (rules/07 §2). OWASP: Logging Vocabulary cheat sheet.
- **Transaction authorization binds to the data it approved.** A step-up, OTP, signature or
  approval covers the exact values the user confirmed (amount, payee, account), stored
  server-side with it. Any change to those values after entry voids it and restarts the flow;
  the execute step re-compares the data being committed with the data authorized, inside the
  committing transaction, or the gap is a TOCTOU (CWE-367). Each authorization is single-use
  and short-lived. High-value flows can require a second, different approver per transaction,
  which is separate from separation of duties at role-grant time. OWASP: Transaction
  Authorization cheat sheet, ASVS 5.0 V2.3.5.
- **Payment results come from the gateway, never the browser.** The user's return from a
  hosted payment page carries parameters the user can edit. Fulfil only on a verified
  server-to-server notification (rules/02 §8) or a server-side status query, and only when the
  gateway's amount, currency and order id equal what you created; fulfil each payment once, so
  a replayed callback does nothing. OWASP: Third Party Payment Gateway Integration cheat sheet.

## 4. Model choice: RBAC / ABAC / ReBAC

- **RBAC**: roles → permission sets. Right default for small/medium apps. Rules:
  permissions checked, not role names (`can(user, "invoice:refund")`, not
  `role == "admin"`) so roles can evolve; no permission accumulation across role
  changes (recompute, don't append); admin roles audited and minimal.
- **ABAC**: policy over attributes (user dept, resource classification, time,
  device). Use when context matters; keep policies in one engine (OPA/Rego,
  Cedar, Casbin), versioned and tested like code:

```cedar
// Cedar: explicit, testable, deny-by-default (no permit -> deny)
permit (principal, action == Action::"invoice:read", resource)
  when { resource.tenant == principal.tenant &&
         (resource.owner == principal || principal.role == Role::"finance") };
forbid (principal, action, resource)
  when { resource.classification == "restricted" && !principal.cleared };
// forbid overrides permit — encode hard ceilings as forbids
```
- **ReBAC**: relationships as the model ("editor of doc", "member of org that
  owns folder") — Zanzibar-style (SpiceDB, OpenFGA, Ory Keto). Right answer for
  sharing/nesting/inheritance (Drive-like products). Beware: relationship-graph
  traversal depth and negative permissions need explicit design.
- Whatever the model: decisions must be **testable in isolation** — a policy test
  suite asserting allow/deny matrices per role/relationship is an audit
  requirement, not a nicety.

```python
# GOOD: permission check, single policy module, deny-matrix tested
def can(user, action: str, resource) -> bool: ...      # the ONLY decision API

@pytest.mark.parametrize("role,action,owns,expected", [
    ("viewer", "invoice:read",   True,  True),
    ("viewer", "invoice:refund", True,  False),
    ("admin",  "invoice:refund", False, True),
    ("member", "invoice:read",   False, False),   # not owner, same tenant -> deny
])
def test_policy_matrix(role, action, owns, expected): ...
```
- Privilege escalation paths to check explicitly: can a user grant themselves a
  role? Invite themselves to a higher-privileged group? Edit the policy store?
  Modify their own `tenant_id`/`org_id`? (CWE-269)
- **Permission data is itself protected.** ACLs, role assignments, group memberships and policy
  metadata tell an attacker who to target and what a stolen account can reach, so *reading* them
  needs an authorization decision too, not only changing them: a user sees their own grants,
  and listing another principal's grants is an admin permission. OWASP: Cornucopia (AZJ).

## 5. Multi-tenant isolation

- Every tenant-owned table carries `tenant_id`; **every query filters on it** —
  enforce structurally, not by developer discipline:
  - Postgres Row-Level Security with `SET LOCAL app.tenant_id` (or
    `set_config('app.tenant_id', …, true)`) inside each request's transaction —
    never a plain `SET`, which leaks to the next client under transaction pooling
    (`sota-databases` rules/04) — policies
    `USING (tenant_id = current_setting('app.tenant_id')::uuid)`; or
  - ORM global scopes/default filters applied from the authenticated context.
```sql
-- GOOD: Postgres RLS — isolation enforced even if app code forgets the filter
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents FORCE ROW LEVEL SECURITY;     -- applies to table owner too
CREATE POLICY tenant_isolation ON documents
  USING (tenant_id = current_setting('app.tenant_id')::uuid);
-- per request, from the AUTHENTICATED context, in the same transaction:
SET LOCAL app.tenant_id = '...';
-- and the app role must not be BYPASSRLS / superuser
```

- `tenant_id` derives from the **authenticated session/token only** — never from
  a request parameter, subdomain string, or header the client controls. A verified claim may
  *select* the tenant, but check an active membership (or service grant) at request time, so a
  user removed from the tenant is refused before their token expires.
- ORM tenant scopes are defence in depth, not the boundary. Measured 2026-09-25 on SQLAlchemy
  2.1.0 with a `do_orm_execute` hook adding `with_loader_criteria`: ORM SELECTs were scoped
  (and bulk UPDATE, only because the hook also handled UPDATE), while `session.execute(text(...))`
  and a Core `engine.connect()` query returned every tenant's rows. Keep the final boundary in
  the database (RLS with a non-bypass role, or per-tenant roles/schemas). OWASP: Multi Tenant
  Security cheat sheet.
- Cross-tenant leak surfaces beyond queries: caches keyed without tenant,
  search indexes, background jobs that loop over tenants with shared state,
  signed URLs without tenant scope, sequence-number leakage across tenants,
  uniqueness checks revealing other tenants' data ("email already exists").
- Test isolation explicitly: an automated test that authenticates as tenant A
  and replays tenant B's object IDs against every entity type.

## 6. Confused deputy (CWE-441) & service-to-service

- A privileged service acting on behalf of a less-privileged caller must carry
  and enforce the **caller's** authority, not its own: pass the user context
  (token exchange — OAuth2 RFC 8693, or signed internal context) downstream and
  re-check authorization at the data-owning service.
- "Internal" services trusting any in-network caller is the classic deputy setup:
  require service identity (mTLS/SPIFFE, signed service tokens) AND per-request
  user authorization. Network position is not identity (zero trust).
- **Do not pass the external access token inward.** The edge verifies it and issues an
  internal-only identity structure (a signed token in a format only internal services accept),
  and internal services require that and refuse external tokens, so a leaked user token opens
  nothing on an internal service exposed by mistake. The internal token never reaches browsers
  or devices, and its format is extensible so claims can be added later. OWASP: Microservices
  Security cheat sheet.
- CSRF and SSRF are confused-deputy instances: the browser and your server,
  respectively, wield ambient authority on an attacker's behalf — same mental
  model, fixes in rules/05 and rules/01.
- Capability URLs / signed URLs: scope them narrowly (object, verb, expiry),
  treat as bearer credentials (no logging, short TTL), and ensure the signer
  checks authorization *before* signing.
- Cloud IAM deputies: services assuming roles on user requests must use
  external-id / source-identity conditions so callers can't aim the service's
  credentials at arbitrary resources.

## 7. Admin & support tooling

- Internal/admin panels get **more** scrutiny, not less: they aggregate
  cross-tenant power. Require SSO + MFA + step-up, network restriction where
  feasible, and their own authz model (support tier ≠ engineering tier ≠
  finance tier) — one "is_staff" boolean is a finding in any non-trivial org.
- Impersonation ("login as user") features: explicit grant per use, time-boxed,
  banner-visible to the operator, **fully audit-logged** (who impersonated
  whom, when, what they did), and ideally consent- or ticket-gated. Sensitive
  user actions (password/email change, payouts) blocked during impersonation.
- Support and admin staff may *start* a user's password reset (the user receives the normal
  reset link), but never set, choose or see the new password; a "set password" field in an admin
  tool means staff know a credential they could later use as that user. OWASP: ASVS 5.0 V6.4.6.
- Every admin mutation needs an immutable audit trail (actor, target, before/
  after, reason) — both a compliance requirement and your insider-threat and
  incident-forensics control (pairs with rules/07 §2 security logging).
- Break-glass paths (emergency access) must alert loudly and expire; a
  permanent quiet backdoor "for ops" is indistinguishable from a compromise.

## 8. Background jobs, webhooks & non-interactive paths

- Jobs enqueued on behalf of a user carry the **principal**, and the worker
  re-authorizes at execution time against current grants (revocation between
  enqueue and run must take effect). Job args are untrusted-ish: validate like
  request input — queues get written to by more code paths over time.
- Scheduled/cron jobs that touch tenant data iterate with per-tenant scoping
  (RLS context set per tenant inside the loop) — a cross-tenant batch bug is a
  Critical with no request log to find it by.
- Inbound webhooks authenticate the **sender** (HMAC, rules/02 §8) and then
  still authorize the *claimed subject*: a valid Stripe signature on an event
  naming `customer_X` doesn't mean your handler should mutate `customer_Y`
  from a spoofable field — map external IDs to internal rows through owned
  associations.
- Internal/ops endpoints triggered by schedulers or service meshes: service
  identity required (mTLS), no "trusted because port 8081" assumptions.

## 9. Common bypass patterns to hunt in audits

- Authorization done in the controller but a second code path (GraphQL, legacy
  v1 API, mobile BFF, gRPC) hits the same model unchecked.
- Check on read, none on write (or vice versa); none on `HEAD`/`OPTIONS`-routed
  handlers.
- A deny branch that redirects or sets 401/403 and does not return: PHP `header('Location: …')`
  with no `exit`, Express `res.redirect()` with no `return`. The protected code runs anyway (§1).
- Authz before async work, none when the job executes (job args carry user IDs —
  re-verify at execution time; grants may have been revoked).
- Cache poisoning of authz decisions: decision cached on user ID but not object,
  or cached across tenants.
- Fail-open exception handling: policy-engine timeout / lookup error →
  `except: pass` → allow (CWE-636). Authorization errors must deny.
- Replay across environments: staging tokens accepted in prod (shared signing
  keys, missing `aud`/`iss` environment binding).

## Audit checklist

- [ ] Is there a single default-deny enforcement layer covering REST, GraphQL resolvers, WebSocket, gRPC, and admin routes?
- [ ] Does every object lookup by client-supplied ID include an ownership/tenant predicate in the query itself?
- [ ] Are nested IDs, batch arrays, exports, downloads, and background-job parameters object-level checked too?
- [ ] Are operation-level (function-level) checks distinct from visibility checks?
- [ ] Do roles/privileges come exclusively from server-side state — never request bodies or client headers?
- [ ] Can no user grant themselves elevated roles, group memberships, or modify their own tenant binding?
- [ ] Is tenant filtering enforced structurally (RLS or mandatory ORM scopes) with tenant_id sourced from the session only?
- [ ] Are caches, search indexes, signed URLs, and uniqueness errors tenant-scoped?
- [ ] Do internal services require both service identity (mTLS) and propagated end-user authorization?
- [ ] Do policy-engine failures and exceptions deny (fail closed)?
- [ ] Is there an automated cross-tenant / cross-user access test suite asserting the deny matrix?
- [ ] Are 404 (not 403) returned for objects the caller cannot see, consistently?
- [ ] Do admin tools have tiered roles, MFA/step-up, and immutable audit trails for every mutation?
- [ ] Is impersonation time-boxed, logged, visible, and blocked from sensitive account changes?
- [ ] Is RLS `FORCE`d with a non-bypass app role where Postgres tenancy is used?
- [ ] Do background workers re-authorize the carried principal at execution time, and do webhook handlers map external subjects to internally-owned rows?
- [ ] Are hard policy ceilings encoded as forbids/deny rules that override grants?
- [ ] **Denial halts (§1, §9)**: does every failed authentication or authorization check end the handler (`return`/`exit` after the redirect or 401/403), and do checks run before the body is processed? HIGH when code after the denial reads or changes data. Read each hit of `grep -rnE '(^|[;{)])[[:space:]]*res\.(redirect|sendStatus|status\(40[13]\))' --include='*.js' --include='*.ts' .` and of `grep -rnE "header\([[:space:]]*['\"]Location:" --include='*.php' . | grep -vE 'exit|die|return'`
- [ ] **Stale session privilege (§3)**: are roles or permissions cached in the session re-read or re-validated for sensitive actions, and flushed with their privileged data when privilege drops? MEDIUM, HIGH on admin paths; each hit of `grep -rnE "session(\[['\"]|\.get\(['\"]|\.)(role|roles|is_?[aA]dmin|permissions|privileges|scopes)" --include='*.py' --include='*.js' --include='*.ts' --include='*.php' --include='*.rb' .` is a decision on a snapshot
- [ ] **Transaction authorization (§3)**: is each step-up/OTP/approval bound to the exact transaction data, voided by any change, re-compared at execution, single-use, and is a second approver available for high-value flows? HIGH on money movement; design review, no reliable grep
- [ ] **Payment verification (§3)**: is fulfilment triggered only by a verified gateway callback or server-side status query that matches amount, currency and order id, once per payment? CRITICAL when a return-URL parameter decides; each hit of `grep -rnE "(request\.(args|GET|query_params)|req\.query|params|\\\$_(GET|REQUEST))(\.get\(|\[|\.)[\"']?(status|payment_status|paid|result|success|amount)" --include='*.py' --include='*.js' --include='*.ts' --include='*.php' --include='*.rb' .` needs its decision traced
- [ ] **Tenant membership and ORM scope (§5)**: is tenant membership checked at request time rather than trusted from a token claim, and does raw SQL/Core/bulk access still meet a database-level boundary? HIGH; each hit of `grep -rnE "(claims|token|jwt|payload)(\[['\"]|\.)tenant(_id|Id)?" --include='*.py' --include='*.js' --include='*.ts' --include='*.go' --include='*.java' .` needs a membership check beside it
- [ ] **Authorization inventory (§1)**: is there a written per-field read/write rule set (state-dependent rules included), a test that UI gating matches the server rules, and a test that fails on a new route, resolver or cache with no access classification? MEDIUM; each hit of `grep -rnE "(v-if|v-show|\*ngIf)=\"[^\"]*([Aa]dmin|[Rr]ole|can[A-Z])|\{[[:space:]]*(user\.)?(is[A-Z][A-Za-z]*[Aa]dmin|isAdmin|can[A-Z][A-Za-z]*|role[[:space:]]*===[^&]*)[[:space:]]*&&" --include='*.vue' --include='*.html' --include='*.tsx' --include='*.jsx' .` is a UI gate that needs a matching server rule
- [ ] **Caller-derived objects (§2)**: are the caller's own objects resolved from the principal (`/me`) rather than a client id, and is every encrypted or indirect id still ownership-checked? HIGH when a user id in the path is trusted; each hit of `grep -rnE "[\"'](/api)?/users?/(:[A-Za-z_]*[iI]d|\{[A-Za-z_]*[iI]d\}|<(int:)?[a-z_]*id>)/|(decrypt|unseal)[A-Za-z]*[Ii]d\(" --include='*.py' --include='*.js' --include='*.ts' --include='*.java' --include='*.go' .` needs its ownership check found
- [ ] **Sequence failures logged (§3)**: does each rejected out-of-order transition emit a high-severity security event (`sequence_fail`)? MEDIUM; `grep -rlE '(raise|throw new)[[:space:]]+(Invalid|Illegal|OutOf)[A-Za-z]*(Transition|Sequence|Step)' --include='*.py' --include='*.java' --include='*.kt' --include='*.js' --include='*.ts' --include='*.cs' . | xargs -r grep -LE 'sequence_fail|[Ss]ecurity_?[Ee]vent|security_?log'` lists files that reject a transition and never log one
- [ ] **Permission data reads (§4)**: does reading ACLs, role assignments and policy metadata need its own authorization? MEDIUM, HIGH when another principal's grants are listable; each hit of `grep -rnE "(\.get\(|@GetMapping\(|@Get\(|GET[[:space:]])[[:space:]]*[\"'][^\"']*/(roles|permissions|acls?|grants|policies)[\"'/]" --include='*.py' --include='*.js' --include='*.ts' --include='*.java' --include='*.go' . | grep -vE 'require|[Aa]uthori[sz]e|PreAuthorize|permission_required'` is an unguarded read
- [ ] **Internal identity token (§6)**: does the edge exchange the external token for an internal-only one that internal services require, never forwarding the user's token or exposing the internal one to clients? HIGH; each hit of `grep -rnE "Authorization[\"']?[[:space:]]*[:,=][[:space:]]*(req|request)\.(headers|META|header|get_header)" --include='*.py' --include='*.js' --include='*.ts' --include='*.go' --include='*.java' .` forwards the caller's token
- [ ] **Admin password reset (§7)**: can staff only trigger the user's own reset flow, never set, choose or view a password? HIGH; each hit of `grep -rnE "(set_?[Pp]assword|update_?[Pp]assword)\([^)]*(request|req|form|body|params)[.[]" --include='*.py' --include='*.js' --include='*.ts' --include='*.java' --include='*.php' --include='*.rb' .` in an admin or support handler is a finding
