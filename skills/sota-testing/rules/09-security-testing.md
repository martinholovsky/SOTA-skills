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
