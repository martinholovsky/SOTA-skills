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

## 3. Function-level authorization — BFLA (CWE-863)

- Verify the caller may perform the *operation*, not just see the object: a user
  who can read an invoice must not be able to call `POST /invoices/{id}/refund`.
- Don't trust client-supplied role/privilege fields — role comes from the
  server-side session/token claims validated against the DB, never from a request
  body (`{"role": "admin"}` mass assignment, see rules/07) or a client-set header
  (`X-Admin: true`).
- State-machine authorization: actions valid only in certain states (approve own
  expense report, re-trigger completed payment) need state checks server-side —
  workflow bypass is an authz bug. Enforce the full doctrine (OWASP Business Logic):
  validate the current state on every step and reject out-of-order transitions;
  **mark one-time operations consumed** so a captured request can't be replayed
  (payment capture, coupon redemption, password-reset token); expire abandoned
  partial-workflow state; and **never store the workflow position in a client-readable/
  writable field** — keep it server-side keyed to the session/resource.

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

## 5. Multi-tenant isolation

- Every tenant-owned table carries `tenant_id`; **every query filters on it** —
  enforce structurally, not by developer discipline:
  - Postgres Row-Level Security with `SET app.tenant_id` per request, policies
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
  a request parameter, subdomain string, or header the client controls.
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
