# 09 — Security Testing

Functional tests prove the app does what it should; **security tests prove it
*won't* do what it shouldn't** under a hostile actor. That negative space is its
own discipline — a green functional suite says nothing about IDOR, injection, or
broken authz. This file owns security testing as a first-class test type: what to
test, how to write the regression tests, and where automated scanners fit.

**Boundaries.** The *vulnerability* knowledge lives in `sota-code-security`
(injection, authz, web), `sota-identity-access`, and `sota-api-design`; the
*threat enumeration* lives in `sota-threat-modeling`; the *pipeline scanners*
(SAST/DAST/dependency gates) live in `sota-devsecops rules/05`. This file is how a
**test author** turns all of that into executable, repeatable tests that fail when
a control regresses. Language-specific runner mechanics live in the language
skills.

## 1. Security testing is non-optional on security-critical paths

- Treat security tests as **mandatory coverage**, not a Q4 nice-to-have, on every
  path that touches authn/authz, crypto, input parsing, money/quota, tenancy, or
  untrusted data. Aim higher there than the general line — a sensible bar is a
  **≥90% coverage floor on security-critical code** vs the suite's normal target,
  with the gap treated as a finding.
- Every confirmed vulnerability (yours or a CVE in a dep you patch) gets a
  **failing regression test first**, then the fix — the same discipline as any bug
  (`rules/02`). It's the only proof the fix works and the only guard against
  silent reintroduction.
- Security tests are **negative tests**: the assertion is that the attack is
  *refused* (403/404/422, rejected, no state change), not that the happy path
  works. A suite with only positive cases is blind to every control bypass.
- **…and every enforcement control still needs one allow case.** Negative-only is
  the right emphasis and the wrong totality: a cap, quota, filter, allowlist or
  policy that refuses *everything* passes every negative test you can write. Pair
  each enforcement control's refusal test with one assertion that a representative
  legitimate request completes **through** that same control — not around it, and
  not against the bare environment (`sota-code-security` rules/12 §1a).
- **The author of a control is not the only author of its tests.** Tests for
  authn, authz, input validation and crypto are written, or at least reviewed,
  by someone other than whoever wrote the code: a second engineer, or a separate
  agent session given the requirement and not the implementation. An author who
  writes both tends to test what they built, holes included, and the suite goes
  green. **A coding agent is never the sole author of both the security code and its
  tests.** Treat such a change as unreviewed until a second party has read the tests
  against the requirement (`sota-llm-engineering` rules/04 §3a, *the judge is not
  the builder*; `sota-docs-workflow` rules/03 §7). OWASP: Secure Coding with AI
  cheat sheet.

## 2. WSTG as the verification map

The OWASP **Web Security Testing Guide** (WSTG) is the canonical category map for
"did we test the security of this surface". Use its categories as a checklist;
test the ones your surface exposes. Each maps to where the vuln rules live:

| WSTG category | Test that… | Vuln rules |
|---|---|---|
| Identity (IDNT) | registration/enumeration don't leak which accounts exist; roles assigned least-privilege | identity-access 01/04 |
| Authentication (ATHN) | lockout/throttle, no creds over GET, no default creds, MFA can't be skipped, reset-token single-use | code-security 02 |
| Authorization (ATHZ) | IDOR/BOLA, vertical/horizontal escalation, path traversal, OAuth weaknesses | code-security 03 |
| Session (SESS) | fixation, regeneration on privilege change, logout invalidates server-side, cookie flags | code-security 02 |
| Input Validation (INPV) | SQL/NoSQL/OS/LDAP injection, XSS, SSRF, deserialization, XXE | code-security 01 |
| Error Handling (ERRH) | errors don't leak stack/SQL/paths; failure is closed | code-security 07 |
| Cryptography (CRYP) | TLS floor, no weak ciphers, secrets not in responses, padding/oracle | code-security 04 |
| Business Logic (BUSL) | workflow order, value re-derivation, replay, abuse cases | §4 below |
| Client-side (CLNT) | DOM-XSS, postMessage origin, CORS, clickjacking, redirect | code-security 05 |
| API (APIT) | the above, per endpoint + method; mass assignment; rate limits | api-design 07 |
| Config/Deploy (CONF) | headers, HTTP methods, admin surfaces, TLS config | devsecops, network-security |
| Info Gathering (INFO) | no secrets/debug/version leak in responses, metafiles, errors | code-security 07 |

WSTG is the *coverage* lens; don't transcribe all of it into unit tests — automate
what's stable as regression tests (§3–4), and run the exploratory/recon parts
(INFO, much of CONF) as DAST or periodic manual review (§5).

## 3. The security-regression set (write these as code)

These are deterministic, fast, and belong in the integration layer (`rules/04`) —
real auth, real DB, real routing. Patterns:

- **Object-level authz / IDOR / BOLA** — the highest-yield test. For every
  resource fetched by an id, assert a foreign principal is refused:
  ```
  # tenant A's token, tenant B's resource id  →  404 (not 403; don't confirm existence)
  GET /orders/{B_order_id}  Authorization: A_token   ⇒  404, body has no B data
  ```
  Cover **nested, batch, export, and `include`/`expand` IDs** too — the bypass is
  usually the second-order id, not the path id.
- **Function-level authz / BFLA** — a lower-privileged principal calling a
  privileged operation is refused: `POST /admin/*`, `DELETE`, state transitions.
  Re-check **per method**, not just per path.
- **Authentication** — expired/invalid/none token → 401; lockout/throttle after N
  failures; reset/verify tokens are single-use and expire; no privilege from a
  client-set field (`{"role":"admin"}`, `X-Admin: true`).
- **Injection** — a per-engine hostile-input corpus run against each parameter,
  asserting no injection effect: SQL/NoSQL operators, OS metacharacters, path
  `../`, template `${}`, and the parser bombs (`rules/06` fuzzing finds the rest).
  Assert structural safety (parameterized), not output-string matching.
- **Mass assignment** — over-post protected fields and assert they're ignored:
  `PATCH /profile {"is_admin":true,"balance":99999}` ⇒ unchanged.
- **Rate limiting / anti-automation** — the (N+1)th request in the window → 429;
  verify the limit is **per account/object**, not just per IP (aliases/batches
  bypass per-request limits — api-design 03/07).
- **SSRF** — user-supplied URLs/webhooks can't reach loopback/RFC1918/link-local/
  multicast/CGNAT/metadata; redirects re-validated (code-security 01 §5).
- **Tenant isolation** — the cross-tenant test is mandatory and runs for *every*
  multi-tenant endpoint, ideally generated from the route table so new routes
  inherit it (the gap is always the one route nobody added a test for).
  **Run it the way production connects, or it proves nothing.** Use the application's
  DB role: PostgreSQL skips every policy for superusers and `BYPASSRLS` roles, and
  for the table owner unless the table has `FORCE ROW LEVEL SECURITY`. A suite run as
  the migration role therefore stays green with no isolation in place. Use the same
  connection path and pooler mode too. PgBouncer lists session-level `SET` as
  unsupported under transaction pooling, so a tenant context set that way breaks
  only behind that pooler. For **every RLS table, test each operation** (read,
  insert, update, delete) with a cross-tenant deny **and** a same-tenant allow.
  Policies can be scoped to single commands, so a correct read policy says nothing
  about the write one. A table with RLS on and no matching policy returns and
  changes nothing, so a deny-only suite passes on a table that serves nobody.
  Intentional cross-tenant paths (share links, delegated access, support/admin
  impersonation, reporting jobs) get their own tests. Each must reach exactly the
  object it grants and nothing next to it: no neighbouring id, sibling row or other
  operation (`sota-databases` rules/01 § Multi-tenancy and rules/06 § Row-Level
  Security; `sota-code-security` rules/03 §7). OWASP: Multi Tenant Security cheat sheet.
- **Shared caches across identities** — for every cache more than one principal
  reads through (CDN or reverse proxy, the framework's page/data cache, memoized
  server functions, an in-process LRU), **warm it as A, then request the same thing
  as B** (another user, another tenant, anonymous) and assert none of A's data comes
  back. Compare against a B-only baseline rather than checking one field. Then change
  A's role or tenant membership and repeat: the answer computed under the old
  grants must be gone. Run it against the deployed cache configuration, because a
  harness that switches caching off tests nothing here (build rules:
  `sota-web-frameworks` rules/03, `sota-performance` rules/05 §9). OWASP: Nextjs
  Security cheat sheet.

## 3a. Operating the authorization suite: matrix, contract negatives, wiring guard

Hand-picked authz tests cover the routes someone remembered. Three patterns close
that gap.

**The matrix is data; the tests are generated from it.** Keep one tech-neutral file
(YAML/CSV/JSON) with a row per role × method × path: the expected status and the
payload to send. `anonymous` is one of the roles. The integration suite reads it and
has every role call every endpoint. It fails on a wrong allow, a wrong deny, **or any
status the row did not predict** (a 500 on a deny path is not a pass), and the
failure message names role, method and path. Reconcile the file against the router's
own route listing in both directions: a route with no rows is untested, and a row for
a deleted route hides that gap.

```yaml
# authz-matrix.yaml: one row per (role, method, path)
- {role: anonymous, method: GET,    path: /orders/{own},   expect: 401}
- {role: viewer,    method: GET,    path: /orders/{own},   expect: 200}
- {role: viewer,    method: DELETE, path: /orders/{own},   expect: 403}
- {role: viewer,    method: GET,    path: /orders/{other}, expect: 404}
- {role: admin,     method: DELETE, path: /orders/{own},   expect: 204}
```

This is the HTTP layer. The decision-function matrix (`sota-code-security` rules/03
§4, `sota-identity-access` rules/03 §6) tests the policy on its own. You need both,
because a correct policy that no route calls still passes the unit matrix.

**Negatives from the OpenAPI contract.** The spec already declares which operations
need credentials (`security` + `securitySchemes`), so generate the no-credential and
bad-credential cases from it. Schemathesis's `ignored_auth` check (read in 4.28.0)
does this. When an operation that declares security answers 2xx, it resends the
request with no credentials and then with invalid ones, and fails unless the answer
is 401 or 403. The check is on by default. Any of these turns it off: a `--checks`
list that omits it, `--exclude-checks ignored_auth`, or `[checks.ignored_auth]
enabled = false` in `schemathesis.toml`. It does not try an expired token or one
missing a scope, so generate those rows yourself from the scopes each operation's
security requirement names. In OpenAPI 3.1.1, an operation-level `security: []`
removes auth and an empty `{}` entry makes it optional. Every such operation belongs
in the matrix as deliberately anonymous.

**Guard the wiring, not only the decisions.** A refactor can unregister, reorder or
route around the central enforcer: a sub-app mounted before the middleware, a new
router without the hook, a gateway policy detached. When that happens, new routes
come up open while every existing row still passes. Test the wiring itself:

```python
# Flask 3.1 shown; every framework exposes its route listing
def test_every_route_has_a_policy():
    app = create_app()
    missing = [r.endpoint for r in app.url_map.iter_rules()
               if r.endpoint != "static" and r.endpoint not in ROUTE_POLICY]
    assert not missing, f"routes with no policy row: {missing}"

def test_unannotated_route_is_denied():
    app = create_app()                                     # fresh app per test
    app.add_url_rule("/__probe", "probe", lambda: "open")  # no policy entry
    assert app.test_client().get("/__probe").status_code == 403
```

Each test catches a different break, so keep both. Checked against Flask 3.1.3: the
first fails when a route has no policy entry and stays green with the
`before_request` enforcer removed; the second fails when the enforcer is removed and
stays green on a new, unlisted route. Where a gateway enforces the OpenAPI
security definitions, send one request **through the deployed gateway** with no
credentials to a secured operation and expect 401/403. A gateway in pass-through or
report-only mode passes every test that calls the service directly
(`sota-code-security` rules/03 §1, rules/14 §5). OWASP: Authorization Regression
Testing and Authorization Testing Automation cheat sheets.

## 4. Business-logic & abuse-case testing

Scanners cannot find business-logic flaws — they need human-authored cases.

- Derive abuse cases from threat models: each high-priority threat becomes a test
  (`sota-threat-modeling rules/05 §3`). `T-012 IDOR → AC-012 → an executable
  test`. **Test the control's observable effect, not its implementation**, so the
  test survives refactors.
- The business-logic set: **workflow order** (skip/replay a step → rejected),
  **server-side value re-derivation** (submit `price:0`/`total:0` → recomputed),
  **one-time-operation replay** (re-submit a captured coupon/payment → consumed),
  **quantity/limit abuse** (negative, zero, overflow, fractional), and
  **time-of-check/time-of-use** races on balances/quotas (concurrent requests →
  no double-spend).
- Run a representative abuse-case set in CI; the long tail is exploratory
  (manual/pentest, §5).

## 5. Where automated tooling fits — and its ceiling

Layer the automation; none of it replaces the regression tests above.

- **SAST / secret-scanning** — in the PR gate (`devsecops rules/05`); catches
  injection sinks, hardcoded secrets. High false-positive; triage, don't auto-block
  on noise.
- **Dependency / SCA** — known-CVE deps, reachability-triaged (`devsecops rules/03`).
- **DAST** — authenticated baseline scan on a staging deploy, OpenAPI-fed
  (`devsecops rules/05 §5.4`); finds header/config/real-injection issues the unit
  layer can't. Treat findings as **leads**, confirm exploitability before filing.
- **Fuzzing** — parsers of untrusted bytes get a fuzz target in scheduled CI
  (`rules/06`); the canonical way to find the injection/overflow/DoS long tail.
- **The ceiling:** tools find *known patterns*. IDOR, broken authz, business-logic,
  and multi-step abuse are found by **human-authored tests and pentest** — which is
  exactly why §3–4 are code you own, not a scanner you outsource to.

## 6. Placement, determinism, CI

- Security regression tests are **integration-tier** (real auth/DB/routing) and run
  on every PR — they must be deterministic and fast, like any other test
  (`rules/02`): seed users/tenants/roles via builders (`rules/03`), no shared
  mutable state, no real clock for token-expiry tests (inject it).
- DAST/fuzz/deep-scans run **out-of-band** (staging-on-merge, scheduled), never
  blocking the PR on their latency — but their *baselines* are reviewed in PRs so a
  growing ignore-list doesn't become silent mute-culture.
- A merged security test with no assertion, or one that passes against the
  vulnerable code, is **Critical** (it manufactures false safety on the exact paths
  that matter most).

## Audit checklist

- [ ] **Every positive control in the suite asserts on the field that carries the
      detection**, not an aggregate over the whole result object
      (`sota-code-security` rules/16 §2.16) — a result type that mixes derived inputs
      with findings stays non-empty while detection is zero.

- [ ] Do security-critical paths (authn/authz, crypto, input parsing, money/quota,
      tenancy, untrusted data) have negative security tests, at a higher coverage
      bar (~90%) than the suite norm? Gaps treated as findings?
- [ ] Is there a **cross-tenant / IDOR** test for every resource fetched by id
      (incl. nested/batch/export/`include` ids), asserting 404 for a foreign
      principal — ideally generated from the route table?
- [ ] Function-level authz tested per method (privileged op from low-priv principal
      → refused), not just per path?
- [ ] Mass-assignment over-post tests on every write endpoint with protected fields?
- [ ] Rate-limit/anti-automation tests assert **per-account/object**, not per-IP?
- [ ] Injection: per-parameter hostile-input cases + a fuzz target for each
      untrusted-bytes parser (`rules/06`)?
- [ ] SSRF tests on every user-supplied-URL/webhook surface (blocked ranges +
      redirect re-validation)?
- [ ] Business-logic/abuse cases derived from the threat model
      (`sota-threat-modeling`), testing observable effect not implementation:
      workflow order, value re-derivation, one-time replay, TOCTOU races?
- [ ] Every fixed vuln/CVE has a regression test that fails on the vulnerable code?
- [ ] SAST + SCA in the PR gate; authenticated DAST baseline + fuzzing out-of-band;
      DAST/SAST baselines reviewed in PRs (no silent ignore-list growth)?
- [ ] Security tests deterministic (injected clock for expiry, seeded principals,
      no shared state) and able to fail (verified against the vulnerable version)?
- [ ] WSTG categories relevant to the surface walked as a coverage check — any
      exposed category with zero tests is a gap?
- [ ] Each enforcement control (cap, quota, rate limit, filter, allowlist, policy)
      has an **allow case** beside its refusal cases, so a control that blocks
      legitimate traffic cannot pass the suite (`sota-code-security` rules/12 §1a)?
- [ ] **Authz suite generated from a role × method × path matrix** (§3a), with
      `anonymous` as a role, failing on unexpected statuses, reconciled against the
      router's route listing both ways? Hand-picked authz tests only → High. Is
      Schemathesis's `ignored_auth` switched off? Probe:
      `grep -rnE '^\[checks\.ignored_auth\]|exclude-checks[ =][^ ]*ignored_auth' .`
      Any hit that disables it → High. Also read every `--checks` list, because one
      that omits it disables it too.
- [ ] **Enforcer wiring guarded** (§3a): a test enumerates the registered routes
      against the policy table, **and** a test calls an unannotated route and expects a
      deny. If a gateway enforces the OpenAPI security definitions, is it exercised
      with an unauthenticated request through the deployed gateway? None → High.
- [ ] **Tenant-isolation tests use the production DB role, connection path and pooler
      mode** (§3), and cover each operation on every RLS table with both a cross-tenant
      deny and a same-tenant allow, plus the sharing/admin paths? Probe for tests
      running as a role that bypasses RLS:
      `grep -rnE 'postgres(ql)?://postgres[:@]|user=postgres( |$)|(^|[^O])BYPASSRLS' --exclude-dir=.git --exclude-dir=node_modules .`
      (whole repo: test DSNs also live in `compose.yaml`, `compose.*.yml`, SQL seeds and CI
      files, and an unmatched `docker-compose*.yml` glob aborts the command in zsh). Any hit
      the test suite uses → High (the suite is green without isolation).
- [ ] **Cross-identity cache test** (§3) for every shared cache layer: warm as A,
      read as B, then repeat after A's role or tenant changes, against the deployed
      cache configuration? Missing on a cache that stores personalized responses → High.
- [ ] **Security tests independent of the code's author** (§1): on authn/authz/
      input-validation/crypto changes, did someone other than the author (human or a
      separate agent session) write or review the tests? A coding agent as sole author
      of both → Medium; as sole author of both on an authz or crypto change → High.
