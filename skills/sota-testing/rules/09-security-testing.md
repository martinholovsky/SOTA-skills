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
- **A security property you delegate to a dependency is still yours to test.** Where
  a library does the sanitising, the token verification or the parser limit, write a
  test that pins the behaviour you rely on: this payload comes out inert, that
  token with the wrong key or algorithm is refused, this input over the cap is
  rejected. Upstream tests what upstream promised, which may not be what you
  depend on, and without your own test a version bump that changes the behaviour
  goes through CI green. OWASP: DSOMM.

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
| Config/Deploy (CONF) | headers, HTTP methods, admin surfaces, TLS config, default files and sample apps left installed | devsecops, network-security |
| Info Gathering (INFO) | no secrets/debug/version leak in responses, metafiles, errors; stack fingerprinted and versions checked against CVEs; external recon (below) | code-security 07 |
| WebSocket (CLNT/APIT) | foreign Origin refused at the handshake, auth at upgrade and for the connection's lifetime, message validation, size and rate limits | api-design 05 §2 |

WSTG is the *coverage* lens; don't transcribe all of it into unit tests — automate
what's stable as regression tests (§3–4), and run the exploratory/recon parts
(INFO, much of CONF) as DAST or periodic manual review (§5).

**Fingerprint the stack the way an attacker would, then look up the versions.**
Removing the `Server` and `X-Powered-By` headers (`sota-code-security` rules/05)
hides one signal of several. Collect the others against the deployed staging stack:
version-bearing headers, default error pages (send a malformed request line or an
unknown HTTP version), framework cookies and HTML markers, default files and
directories, and how the server orders and phrases its responses. Map every version
you can pin down to its known CVEs. A version you find this way that is behind the
patched release is a finding, whether or not the banner shows it. The defaults leak
unless changed: nginx `server_tokens` defaults to `on`, Apache `ServerTokens` to
`Full`, and the shipped `php.ini-production` sets `expose_php = On`.

**External recon is part of INFO, and it runs outside your own servers.** Search the
public places an attacker would: search engines and their cached copies, web
archives, paste sites, public code hosts and third-party services such as CI logs,
issue trackers and shared diagrams. Look for internal hostnames, configuration
files, stack traces, credentials and design documents, plus dev, test and staging
sites that were never meant to be public. Credentials found this way go straight to
the leak runbook (`sota-secrets-management` rules/04 §3); the rest are findings
against whoever published them. OWASP: WSTG-INFO-01, WSTG-INFO-02, WSTG-INFO-08
(WSTG-INFO-09 was merged into it).

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
  Assert structural safety (parameterized), not output-string matching. For **XSS**
  add a case per output context (element body, attribute, JS string, URL) plus one
  multi-context polyglot, a single payload built to close whichever of those
  contexts it lands in, so one parameter gets checked everywhere it is echoed. For
  parameters that reach a **directory**, add the LDAP filter metacharacters `*`,
  `(`, `)`, `\` and NUL, and assert that the filter the server builds still
  matches exactly one entry (`sota-code-security` rules/01 §11). Point the DAST
  injection scan at those parameters too, not only the SQL-backed ones. OWASP:
  Injection Prevention and XSS Filter Evasion cheat sheets.
- **Mass assignment** — over-post protected fields and assert they're ignored:
  `PATCH /profile {"is_admin":true,"balance":99999}` ⇒ unchanged.
- **Rate limiting / anti-automation** — the (N+1)th request in the window → 429;
  verify the limit is **per account/object**, not just per IP (aliases/batches
  bypass per-request limits — api-design 03/07). **Message-size limits get a test of
  their own:** send a body one byte over the configured cap and assert it is
  refused (HTTP 413; gRPC `RESOURCE_EXHAUSTED`) without the server reading the whole
  thing into memory. Send one request just under the cap too, as the allow case. The
  cap can be switched off entirely: nginx `client_max_body_size 0`, gRPC core
  `grpc.max_receive_message_length` of `-1` (grpc-go's server default is 4 MiB).
  OWASP: gRPC Security cheat sheet.
- **WebSocket** — the handshake and the open connection are tested separately. A
  handshake with a foreign `Origin` is refused; send one explicitly, because some
  helpers accept a request with no `Origin` at all (Spring's
  `WebUtils.isValidOrigin`). A missing, invalid or expired token cannot connect.
  An open socket is closed when its session expires or the user logs out. Messages
  are validated like any request body, and oversize frames and message floods hit a
  limit (api-design 05 §2). OWASP: WebSocket Security cheat sheet.
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

**Make the suite cheap to run, and watch its denial counts.** Give the authz tests
their own marker or script (`pytest -m authz`, an `authz-tests` package script) so a
developer can run just those, quickly, before pushing. In CI, have the integration
run report its 401 and 403 counts and compare them with the last green run on the
base branch. A jump means a functional change is colliding with a control, even when
every functional assertion still passes. It gets a human look, and it is not
auto-accepted into a new baseline. OWASP: Authorization Regression Testing cheat
sheet.

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

## 5a. Manual assessment and penetration testing

The §5 ceiling is why a manual assessment exists. Treat it as a process with rules,
not an event.

- **When.** Before a major release, whenever a new trust boundary appears (a new
  public API, a new tenant model, a new identity provider), and on a fixed cadence
  between those. Fix the known common classes first (the regression set in §3 and
  the scanners in §5), then commission the test, so the tester's time goes on what
  automation cannot find.
- **Scope.** Write it down, including the client side: the behaviour of third-party
  JavaScript your pages load (tags, widgets, analytics) is in scope, since it runs
  with your user's privileges. Give the tester the OpenAPI spec, a developer guide,
  or source access where you can. A white-box test covers more of the surface than a
  black-box one.
- **Independence.** The tester did not build the system (§1). Review the findings
  before release, and fix or formally accept each one with a date.
- **Close the loop in both directions.** Hotspots from code review and the risk ranking
  (`rules/01` §1.4) set the white-box tester's targets. Each pentest finding becomes a
  §3 regression test and sends a reviewer back into the code around it, because
  the same mistake is rarely made once. A finding in session management, for
  example, means the next change there needs explicit security tests.

**The manual REST technique.** A REST service's attack surface does not show in its
UI. Route real client traffic through an intercepting proxy that records **full
requests** (headers and bodies, not just URLs). Then read those requests for inputs
nobody documented: unusual headers, URL segments that vary a lot or follow a pattern
(dates, numbers, ids), an extensionless last segment where the stack normally uses
extensions, and JSON or XML nested inside parameter values. To tell a path segment
from a parameter, send a value that must be invalid. A plain 404 from the web server
suggests a real path. An application-level error suggests a parameter worth
fuzzing. Fuzz with the authentication emulated, and aim at the edges of each
parameter's valid range. OWASP: REST Assessment cheat sheet, SAMM (Verification,
Security Testing), Code Review Guide v2, DotNet Security and Third Party JavaScript
Management cheat sheets.

## 6. Placement, determinism, CI

- Security regression tests are **integration-tier** (real auth/DB/routing) and run
  on every PR — they must be deterministic and fast, like any other test
  (`rules/02`): seed users/tenants/roles via builders (`rules/03`), no shared
  mutable state, no real clock for token-expiry tests (inject it).
- DAST/fuzz/deep-scans run **out-of-band** (staging-on-merge, scheduled), never
  blocking the PR on their latency — but their *baselines* are reviewed in PRs so a
  growing ignore-list doesn't become silent mute-culture.
- **A security stress run belongs out-of-band too.** Against a pre-production
  environment sized like production: request floods, connection exhaustion,
  algorithmic-complexity inputs (regex, deep nesting, hash collisions) and oversize
  messages, unauthenticated actions first. Assert that every limit holds and that
  the service degrades (sheds load, answers 429 or 503) rather than falling over.
  The §3 unit checks prove a limit exists. This run proves it holds under load.
  OWASP: SAMM (Verification, Requirements-driven Testing).
- **Leave production-grade logging on during fuzz, pentest and load runs.** Without
  it a finding cannot be investigated, and the run cannot show whether your
  detections fired. The logging path is itself under test: CR/LF and control
  characters in logged fields (`sota-code-security` rules/07 §2), side effects of
  logging, and the sink failing (unreachable, disk full, no write permission). A
  request must neither hang nor fail because logging did, and a lost security event
  must be counted and alerted, never silently dropped (`sota-observability` rules/01
  §6a). OWASP: Logging cheat sheet, Code Review Guide v2.
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
- [ ] **Security behaviour delegated to a dependency pinned by your own test** (§1)?
      List the calls to find them:
      `grep -rnE '(DOMPurify\.sanitize|sanitizeHtml|bleach\.clean|nh3\.clean|Jsoup\.clean|jwtVerify|jwt\.(decode|verify))\(' src`
      A hit with no test of the property you rely on → Medium (High on a token check).
- [ ] **Stack fingerprinted and versions mapped to CVEs** (§2), from headers, error
      pages, default files and behaviour, not only from the banner? Version-bearing
      headers on the deployed stack:
      `curl -sI https://staging.example.test | grep -iE '^(server|x-powered-by|x-aspnet-version|x-aspnetmvc-version):.*[0-9]'`
      Any hit → Low, and a detected version behind its patched release → High.
- [ ] **External recon run** (§2): search engines, caches and archives, paste
      sites, public code hosts and third-party services checked for internal
      hostnames, configs, stack traces and design documents? Never done → Medium; a
      live credential found → Critical.
- [ ] Hostile-input corpus has **XSS cases per output context plus a polyglot**, and
      **LDAP filter metacharacters** on directory-backed parameters (§3)? Missing on
      a surface that echoes input or queries a directory → Medium.
- [ ] **Message-size limits tested one byte over and one byte under the cap** (§3),
      and never switched off? Probe:
      `grep -rnE "client_max_body_size[[:space:]]+0;|max_receive_message_length['\"][[:space:]]*,[[:space:]]*-1[^0-9]|MaxRecvMsgSize\(math\.MaxInt" .`
      Any hit on an untrusted-facing listener → High.
- [ ] **WebSocket set** (§2, §3): foreign-Origin handshake refused, missing or expired
      token refused, socket closed on logout or expiry, message limits enforced?
      Origin allow-all in code:
      `grep -rnE 'CheckOrigin:[[:space:]]*func\([^)]*\)[[:space:]]*bool[[:space:]]*\{[[:space:]]*return true|setAllowedOrigin(s|Patterns)\("\*"\)' .`
      plus the gofmt multi-line form (body's first line is `return true`; an allowlist
      whose `return true` sits inside an `if` does not match):
      `grep -rnA1 -E 'CheckOrigin:[[:space:]]*func\([^)]*\)[[:space:]]*bool[[:space:]]*\{[[:space:]]*$' . | grep -E -- '-[0-9]+-[[:space:]]*return[[:space:]]+true[[:space:]]*$'`
      Any hit on a cookie-authenticated socket → High; no WebSocket tests → Medium.
- [ ] **Authz tests runnable on their own** (a marker or script), and CI reports 401
      and 403 counts against the base branch (§3a)? No volume signal → Low.
- [ ] **Penetration-testing process defined** (§5a): triggers (major release, new
      trust boundary, cadence), written scope that includes third-party JavaScript,
      an independent tester, findings turned into §3 regression tests? No manual
      assessment ever on an internet-facing system → High.
- [ ] REST assessment used full-request capture and path-versus-parameter probing
      (§5a), not only a URL crawl? Crawl-only → Medium.
- [ ] **Out-of-band security stress run** against pre-production (§6), asserting
      limits hold and the service degrades rather than fails? None → Medium.
- [ ] **Logging on during fuzz, pentest and load runs, and the logging path tested**
      (§6)? Look for logging switched off in those runs' configs:
      `grep -rniE 'logging\.disable\((logging\.)?(CRITICAL|ERROR|WARNING|INFO)?\)|LOG_LEVEL"?[[:space:]]*[=:][[:space:]]*"?(off|none|silent)|--log-level[= ](off|none|silent)' .`
      A hit in a security-run config → Medium; no sink-failure test → Medium.
