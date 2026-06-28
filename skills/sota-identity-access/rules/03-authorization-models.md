# 03 — Authorization Models & Design

Scope: the *model* that decides who may do what — RBAC vs ABAC vs ReBAC, role modeling
and role explosion, the **group→role mapping discipline**, least privilege and
segregation of duties (SoD), policy-as-code engines (OPA/Rego, AWS Cedar, OpenFGA,
SpiceDB), policy testing, and birthright vs requested access.

This file owns the **model and the engine**. It does NOT own app-level object-level
enforcement bugs (IDOR/BOLA in one handler) — that is **sota-code-security** rules/03.
The division: code-security asks "did this handler check ownership of this row?"; this
file asks "is the permission model correct, least-privilege, tested, and free of role
explosion and SoD violations?".

## 1. Choosing the model

| Model | Decides on | Use when | Engines |
|---|---|---|---|
| **RBAC** | Roles → permission sets | Small/medium apps; access maps cleanly to job functions; manageable number of roles | Native IdP roles, Casbin |
| **ABAC** | Attributes of subject/resource/action/environment (dept, classification, time, device, risk) | Context matters; dynamic conditions; cross-cutting rules | OPA/Rego, Cedar |
| **ReBAC** | Relationships in a graph ("editor of doc", "member of org that owns folder") | Sharing, nesting, inheritance, per-object grants (Drive/GitHub-like) | OpenFGA, SpiceDB, Ory Keto |

These compose: Cedar and Zanzibar-style engines support RBAC + ABAC + relationships. Pick
the *simplest* model that expresses your access rules; reach for ReBAC only when
per-object relationships and inheritance are real requirements, because the relationship
graph adds operational complexity (traversal depth, consistency, negative permissions).

## 2. RBAC: role modeling and role explosion

- **Check permissions, not role names.** Authorize on `can(user, "invoice:refund")`, not
  `role == "admin"`, so roles can evolve without code changes. Map roles → permissions in
  one place.
- **Role explosion** is the classic RBAC failure: combinatorial roles
  (`finance-eu-readonly-q3`) multiply until no one understands them. Defenses: keep roles
  aligned to *job functions*, factor cross-cutting context into ABAC attributes instead
  of new roles, and prune unused roles in access reviews (rules/04).
- **No permission accumulation across role changes.** When a user moves roles, *recompute*
  their effective permissions — do not append the new role and leave the old (the "access
  creep" of movers, rules/04).
- **Birthright vs requested.** Birthright access (everyone gets baseline accounts/groups
  on joining) is automatic and minimal; everything beyond is *requested* and *approved*,
  with an owner and an expiry. A privileged role granted as birthright is a finding.

## 3. The group→role mapping discipline (default-deny)

The most common silent over/under-grant lives in the IdP-group → app-role mapping:

- **Map explicitly and default-deny.** A user whose groups match *no* mapping must get
  *no* role — never a silent "default" role. The dangerous real-world bug: an IdP is
  wired so **every authenticated OIDC user is assigned a low/default app role regardless
  of their group membership**, because the app falls back to a default when no group claim
  maps. That simultaneously *over*-grants (outsiders/unmapped users get standing access)
  and *masks* the intended model. The fix is fail-closed: no matching group → no role →
  access denied.
- In Kanidm terms: scopes are granted via `oauth2 update-scope-map <client> <group>
  <scopes>` and claims via `update-claim-map`. A user in no mapped group ends up with no
  granted scopes — which is correct, *provided the RP treats "no scopes" as no access*
  rather than defaulting them in. Verify both sides.
- Re-map upstream/external group claims through your own model (rules/02 §8); never let an
  upstream IdP's arbitrary group assertion directly grant a privileged local role.

```rego
# GOOD (Rego): default deny; role derives only from an explicit group mapping
package authz
import rego.v1
default allow := false
role := r if { some g in input.user.groups; r := group_role[g] }   # undefined if no match
allow if { some p in role_permissions[role]; p == input.action }
# BAD: a fallback that silently grants everyone a baseline role
role := group_role[g] if { some g in input.user.groups }
role := "viewer"  # <-- default low role for ANY authenticated user regardless of group
```

## 4. Least privilege & segregation of duties

- **Least privilege**: each role/grant carries the minimum actions on the minimum
  resources. No role grants estate-wide `*`/admin "to be safe." Scope by resource,
  environment, and tenant.
- **Segregation of duties (SoD)**: define conflicting permission pairs that one identity
  must not hold together (create-vendor + approve-payment; request-access +
  approve-access; deploy-to-prod + approve-prod-deploy). Enforce SoD at grant time (block
  the assignment) and detect violations in access reviews. SoD violations are a Medium-to-
  High finding depending on the blast radius.
- **Just-in-time elevation** rather than standing privilege (rules/05): a user requests a
  permission for a bounded window instead of holding it permanently.
- **Log authorization decisions** (OWASP Authorization): the decision point emits a
  structured event — `who`, `action`, `resource`, `decision`, `policy/rule id` — for at
  least every *deny* and every privileged *allow*. Denies are a primary detection signal
  (enumeration, broken-object-level-auth probing); without them an authz bypass is
  invisible. Feed them to sota-detection-engineering; never log the token/credential.

## 5. Policy-as-code engines

Author authorization as versioned, tested code — not as clicks in an admin UI:

- **OPA / Rego** (CNCF Graduated): general policy engine; Rego is declarative and
  non-Turing-complete. Good for ABAC and centralized decision points; deploy as a sidecar
  or library; ship a bundle.
- **AWS Cedar** (open-sourced 2023; powers Amazon Verified Permissions): purpose-built
  authorization language, deny-by-default, `forbid` overrides `permit` (encode hard
  ceilings as `forbid`), designed for analysis/formal reasoning.
- **OpenFGA** (CNCF Incubating, late 2025) and **SpiceDB** (AuthZed): Zanzibar-style
  ReBAC. You declare a relationship schema and store tuples; the engine answers
  `check(user, relation, object)` and traverses inherited relationships. The model is the
  2019 Google Zanzibar paper. **Ory Keto** is another Zanzibar-style option.
- Whatever the engine: a single decision API the app calls, policy in version control,
  reviewed and deployed like code, with the policy store itself protected (editing the
  policy is a privileged action — rules/05).

```cedar
// Cedar: deny-by-default; forbid is a hard ceiling that overrides any permit
permit (principal, action == Action::"invoice:read", resource)
  when { resource.tenant == principal.tenant &&
         (resource.owner == principal || principal in Role::"finance") };
forbid (principal, action, resource)
  when { resource.classification == "restricted" && !principal.cleared };
```

```fga
# OpenFGA: relationships; "viewer of a folder" inherits to documents in it
model
  schema 1.1
type document
  relations
    define parent: [folder]
    define viewer: [user] or viewer from parent
    define editor: [user]
```

## 6. Policy testing (an audit requirement, not a nicety)

- Maintain an **allow/deny matrix** test suite: for each role/relationship × action ×
  resource-context, assert the expected decision, including the negatives (viewer cannot
  refund; cross-tenant denied; unmapped group → denied; SoD pair rejected).
- Run policy tests in CI and gate merges. A change to a role definition or Rego/Cedar/FGA
  model without a corresponding test change is suspect.
- Test the **fail-closed** behavior: engine timeout / lookup error must **deny**, never
  fall through to allow.

```python
@pytest.mark.parametrize("groups,action,expected", [
    (["finance"],  "invoice:refund", True),
    (["finance"],  "invoice:delete", False),   # finance can't delete
    (["support"],  "invoice:refund", False),
    ([],           "invoice:read",   False),   # no mapped group -> DENY (no default role)
])
def test_authz_matrix(groups, action, expected):
    assert decide(user(groups=groups), action) is expected
```

## Audit checklist

- [ ] Is the authorization model chosen deliberately (RBAC/ABAC/ReBAC) and the simplest that expresses the rules?
- [ ] Does the app authorize on permissions/relationships, not hardcoded role-name string checks?
- [ ] Is there role explosion (combinatorial, unused, or context-encoding roles) that should be ABAC attributes?
- [ ] On role/group change, are effective permissions recomputed (no accumulation/creep)?
- [ ] Is birthright access minimal, with all privileged access requested + approved + expiring?
- [ ] Is the group→role mapping explicit and **default-deny** — does an unmapped user get NO role rather than a silent default? (hunt for `default.*role`, `|| "viewer"`, fallback role assignment)
- [ ] Are upstream/external group claims re-mapped through the local model, never trusted to grant privileged roles directly?
- [ ] Does any role grant estate-wide `*`/admin without justification? (grep policy for `"*"`, `Action::"*"`, `allow.*true` without conditions)
- [ ] Are segregation-of-duties conflicting pairs defined and enforced at grant time?
- [ ] Is policy authored as versioned code (OPA/Cedar/OpenFGA/SpiceDB) with a single decision API, not clicked into a UI?
- [ ] Is the policy store itself a protected/privileged resource?
- [ ] Is there an allow/deny matrix test suite (including negatives and the unmapped-group case) gating CI?
- [ ] Does the engine fail **closed** (deny) on timeout/error?
