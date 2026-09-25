# 07 — Output, Errors, Logging & Data Exposure

Scope: error handling without leaks, logging hygiene, mass assignment, verbose
APIs and over-exposure, debug surfaces. Maps to OWASP A06/A02/A09:2025 (A09 is
"Security Logging and Alerting Failures" since the 2025 release),
CWE-209/532/915/213/489/200.

Core principle: **exposure is a one-way door.** Injection bugs get patched;
a leaked stack trace, token-in-log, or over-fetched PII payload is already in
attacker hands, third-party log pipelines, and backups. Design every output —
responses, errors, logs, metrics — as if it will be read by an adversary,
because logs and error trackers routinely are.

## 1. Error handling without leaks (CWE-209/550)

- Two error channels, never mixed:
  - **To the client**: generic message + stable error code + correlation ID.
  - **To logs/telemetry**: full exception, stack, context — keyed by the same
    correlation ID so support can join them.
- Never to the client: stack traces, exception class names, SQL fragments,
  file paths, internal hostnames/IPs, dependency versions, framework debug
  pages (`DEBUG=True`, Whoops, dev error overlays in prod — CWE-489 adjacent).
- Catch at the boundary: a global exception handler that converts *all*
  unhandled errors to the generic shape; per-route handlers may add precision
  only from an allowlist of safe messages.
- Don't leak via **differences** either: distinct messages, status codes, or
  response times for "user not found" vs "wrong password", "object missing" vs
  "forbidden" (use 404 for both, rules/03), padding vs MAC failure (rules/04) —
  all observable oracles (CWE-203/204).
- Fail closed: error paths must not skip authz/validation (`except Exception:
  return data_anyway`), must release resources, and must not leave partial
  state (use transactions).

```python
# BAD: three different responses = free enumeration + targeting data
if not user:            return {"error": "No account with that email"}, 404
if user.locked:         return {"error": "Account locked"}, 423
if not check(pw, user): return {"error": "Wrong password"}, 401

# GOOD: one response shape; detail goes to the security log, not the attacker
ok = user is not None and not user.locked and verify(pw, user)   # verify() runs
return ({"error": "invalid_credentials"}, 401) if not ok else issue_session(user)
# note: run the hash verification even when user is None (dummy hash) — timing
```

```python
# GOOD: boundary handler
@app.errorhandler(Exception)
def handle(e):
    cid = new_correlation_id()
    log.exception("unhandled", extra={"cid": cid})        # full detail, server-side
    return jsonify(error="internal_error", cid=cid), 500  # generic, client-side
```

## 2. Logging hygiene (CWE-532)

- **Never log**: passwords (including failed attempts — typo'd passwords are
  near-passwords), session IDs, JWTs/API keys/refresh tokens, full card
  numbers/CVV, private keys, OTPs, password-reset links, `Authorization`/
  `Cookie` headers, full request bodies of auth endpoints.
- PII (emails, names, addresses, government IDs, precise geo, health data):
  log only with purpose; prefer pseudonymous user IDs; mask
  (`j***@example.com`) or tokenize when the value is needed for support.
  Retention limits and deletion-on-request must reach logs and backups
  (GDPR/CCPA exposure is a security finding too).
- Enforce structurally, not by memory:
  - structured logging (JSON) with a **redaction filter** keyed on field names
    (`password`, `token`, `secret`, `authorization`, `ssn`, ...) and
    value-shape detectors (JWT regex, PAN Luhn check) at the logger level;
  - deny-by-default serialization for log objects (log explicit fields, never
    `log.info(f"{request.__dict__}")` / whole-object dumps);
  - secrets wrapped in types whose `toString`/`repr` is masked.
- **Log injection (CWE-117)**: strip/escape CR/LF and control chars from
  user-controlled values before logging (forged entries, log-parser exploits —
  and never let user input reach a log4j-style lookup/format string: log
  *arguments*, not concatenated format strings; CWE-134).
```python
# GOOD: redaction enforced at the logger, not at 500 call sites
SECRET_KEYS = re.compile(r"(?i)(pass(word)?|token|secret|authorization|api[_-]?key|cookie|ssn)")
JWT_SHAPE   = re.compile(r"eyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]+")

class Redact(logging.Filter):
    def filter(self, record):
        if isinstance(record.args, dict):
            record.args = {k: "[REDACTED]" if SECRET_KEYS.search(k) else v
                           for k, v in record.args.items()}
        record.msg = JWT_SHAPE.sub("[JWT]", str(record.msg))
        record.msg = record.msg.replace("\r", "\\r").replace("\n", "\\n")  # CWE-117
        return True

class Secret(str):
    def __repr__(self): return "Secret('****')"
    __str__ = __repr__          # f-string/log interpolation can't leak it
```

- Do log (security observability, OWASP A09): authn successes/failures, authz
  denials, validation rejections, privilege/role changes, MFA/recovery events,
  admin actions — with actor, action, target, result, source IP, timestamp;
  ship to an append-only store with alerting on anomalies.
- URLs end up in logs everywhere (proxies, CDNs, browser history): never carry
  secrets/PII in query strings (CWE-598).

### 2.1 Security events and in-app detection points

A security log is only searchable and alertable if every service names the same event
the same way. Adopt a shared vocabulary — the OWASP Logging Vocabulary's
`category_event[:args]` names are a ready one — rather than free-text messages, and
give each event a fixed severity so alerting keys on the name, not on a regex.

- **Authentication**: success; success *after* prior failures, with the retry count
  (`authn_login_successafterfail`); each failure; the failure threshold reached, with
  the limit (`authn_login_fail_max`); account lock, with a reason code
  (`authn_login_lock`); password change and **failed password change, at high
  severity** (the vocabulary rates `authn_password_change_fail` CRITICAL); token
  created, revoked and reused.
- **Session**: created, renewed, expired (with the reason: idle or absolute),
  logout, and use after expiry (`session_*`). A session cookie or JWT that fails its
  integrity check, a token that is expired, revoked or unknown, and a JWT failing
  validation for a suspicious reason (`alg` mismatch, unknown `kid`, bad signature)
  are each a separate event, never a silent 401. Log token **identifiers** — `jti`,
  `iat`, `azp` (the client it was issued to), `act` (the delegating actor, RFC 8693)
  and a hash of the session ID — never the token or session ID itself (§2).
- **Authorization**: every denial (`authz_fail`) and privilege change. At high
  assurance, log **every** authorization decision, allow included, and every read of
  sensitive data (`sensitive_read`) — who, which record, when — without the data.
- **Tampering: input the real client cannot produce is an attack signal, not a
  validation error.** A value outside a closed option set (select, radio, enum), a
  changed hidden or state field, a field the handler does not expect, transaction data
  altered after the user confirmed it, a deserialized type outside the allowlist
  (rules/01 §8), an output-validation failure. Emit a distinct event naming the
  field (`input_validation_discrete_fail`, `malicious_extraneous`) at a higher severity
  than routine rejections, which stay `input_validation_fail`. Mixing the two buries
  the probe among typos.
- **Business-logic and integrity detection points**: signups per IP, device or
  payment instrument; spikes in promo, referral or credit redemption; a multi-step flow
  finished faster than a person could; an order marked paid with no matching gateway
  confirmation, or a burst of gateway callbacks for one order; repeated cross-tenant
  denials from one principal; repeated deserialization failures from one principal.
  Each is a counter with a threshold and an owner, tagged with a distinct security
  severity once confirmed malicious so it reaches the SOC queue rather than the ops
  one (`sota-detection-engineering` owns the rules and triage).
- OWASP: Logging Vocabulary, Logging, Session Management and JSON Web Token cheat
  sheets; Input Validation, Transaction Authorization, Business Logic Security, Multi
  Tenant Security and Third Party Payment Gateway Integration cheat sheets; Proactive
  Controls 2024 C3/C9; ASVS 5.0 V16.3.2; Code Review Guide v2; Go-SCP (logging);
  Secure Coding Practices QRG.

## 3. Mass assignment / over-binding (CWE-915)

- Binding request bodies directly to ORM/domain models lets clients set fields
  you never exposed: `{"role":"admin"}`, `{"email_verified":true}`,
  `{"tenant_id":...}`, `{"price":0}`.
- Fix structurally: **explicit per-endpoint DTOs/schemas** (input models with
  only the writable fields), then map allowed fields to the entity. Allowlist,
  never blocklist:

```python
# BAD
user.update(**request.json)                       # CWE-915
# GOOD
class UpdateProfile(BaseModel):                    # pydantic: unknown keys rejected
    model_config = ConfigDict(extra="forbid")
    display_name: str
    bio: str
user.apply(UpdateProfile(**request.json))
```

- Framework audit points: Rails `permit!`/broad `permit` lists, Spring
  `@ModelAttribute` on entities (use `@JsonIgnore`/DTOs), Django `ModelForm`
  with `fields = "__all__"`, JS `Object.assign(user, req.body)` /
  `User.update(req.body)`, GraphQL input types mirroring DB models.
- Separate create/update/admin schemas — "writable at signup" ≠ "writable
  forever" (e.g. `email` writable at create, verified-flow-only later).
- **Re-derive security-sensitive values server-side; never accept them from the
  client** (OWASP Business Logic). Prices, subtotals, taxes, totals, balances,
  discounts, quotas, role/tier — take only identifiers + quantities and recompute
  from your own store/price book. `{"price": 0}` and `{"items": 5, "total": 0}` are
  the canonical e-commerce logic exploits; the same applies to credit/quota balances
  in any multi-tenant or metered system.
- Same bug, query side: client-controlled `fields`/`include`/`expand`/`sort`
  params must resolve through allowlists, or they become column-level IDORs
  and join-amplification DoS.

## 4. Verbose APIs & over-exposure (CWE-213/200)

- **Filter at the source, shape at the edge**: never fetch-everything and rely
  on the client to ignore fields. Response DTOs are allowlists of what leaves
  the service; serializing ORM entities directly leaks every added-later column
  (password hashes, internal flags, soft-deleted rows).
```python
# BAD: whatever columns exist (now or after next migration) go over the wire
return jsonify(user.__dict__)             # or UserSchema(model=User, fields="__all__")

# GOOD: output is an explicit allowlist, versioned with the API contract
class PublicUser(BaseModel):
    id: UUID
    display_name: str
    avatar_url: HttpUrl | None
return PublicUser.model_validate(user)    # adding a DB column changes nothing here
```

- Excessive data exposure patterns to hunt: list endpoints returning full
  objects where the UI shows two fields; `/users/{id}` returning email/phone to
  any authenticated user; embedded related objects (`order.user.passwordHash`);
  "admin" fields toggled by serializer flags that default open.
- GraphQL: every **field** is an endpoint — apply field-level authz; disable
  introspection in prod (or gate it); suggestion/typo hints off; cost-limit
  queries (rules/06 §5).
- Enumeration surfaces: incrementing IDs + list endpoints, uniqueness errors
  ("email taken"), timing differences, sitemap/export endpoints — rate-limit
  and design responses to avoid existence oracles where it matters.
- Metadata leaks: EXIF/GPS in re-served images, document author/revision
  history in served Office/PDF files, `.git`/`.env`/backup files reachable
  under the web root, source maps exposing server code paths in prod,
  verbose `OPTIONS`/`TRACE`.
- **Static web tier: list nothing, serve an allowlist.** Directory listing stays off
  unless a listing is the product: nginx `autoindex`, Tomcat's `listings` and IIS
  `directoryBrowse` default off, and Apache lists wherever `Options` includes
  `Indexes` (which `All` does). Go's `http.FileServer` lists any directory without an
  `index.html` — serve from a directory that has one everywhere, or wrap the
  filesystem. Serve only allowlisted extensions from the static root, so `.inc`,
  `.config`, `.bak`, `.old`, `.swp`, `~`, `.sql`, archives and source files are refused
  rather than sent as text. Sweep the deployed web root and public buckets for backup,
  old and unreferenced files, and test every deny rule with variants (case changes,
  percent-encoding, trailing slash or dot, path parameters) rather than trusting it.
  OWASP: ASVS 5.0 V13.4.3/V13.4.7, WSTG-CONF-03, WSTG-CONF-04, Go-SCP (system
  configuration).
- API versions: deprecated v1 endpoints with weaker checks stay exploitable —
  decommission, don't just de-document (shadow APIs; keep an inventory).

## 5. Data minimization, retention & secondary stores

- Classify data at the schema level (public / internal / confidential /
  regulated) and let classification drive handling: regulated fields get
  field-level encryption (rules/04 §4.1), masked logging, restricted
  serializers, and named retention periods enforced by deletion jobs — not
  policy documents.
- Don't collect what you can't protect: every stored sensitive field is
  permanent liability; derive (age bracket, not DOB), truncate (last-4),
  or process-and-discard where the product allows.
- Secondary stores inherit exposure but escape controls — audit them
  explicitly: analytics events, data warehouses/ETL, search indexes, caches,
  queue payloads (often logged by brokers), crash/error trackers (Sentry-class
  tools capture local variables — configure scrubbing), session-replay tools
  (capture keystrokes — block on auth/payment fields), backups (encrypted,
  access-controlled, retention-bounded, restore-tested).
- Deletion must be real: "deleted_at" soft-delete still serves data to any
  query missing the filter and to every secondary store; account-deletion
  flows must fan out to logs, backups schedule, search, analytics, and vendors.
- Exports/reports are mass-exposure events: same authz as the underlying data
  (rules/03), watermark/audit who exported what, rate-limit, and expire
  download links (signed, short-TTL — rules/04 §7).

## 6. Debug & non-prod surfaces (CWE-489)

- Production must have: debug modes off (framework debug pages, GraphQL
  playgrounds, Swagger UIs gated or auth'd), actuator/metrics/health endpoints
  restricted (`/actuator/env`, `/debug/pprof`, `/metrics` leak secrets/topology),
  profilers and REPL endpoints absent.
- Test/seed accounts, magic bypass headers (`X-Debug-User`), and feature-flag
  backdoors must never ship — grep for them in audits.
- **Enumerate the real route table, not the one you wrote.** Frameworks generate
  routes: Rails `resources :photos` creates seven actions unless limited with
  `only:`/`except:`; Spring Data REST exports every public repository interface by
  default (`RepositoryDetectionStrategies.DEFAULT`); admin panels, blueprints and
  scaffolding add more. Dump the router's own listing (`bin/rails routes` or the
  framework's equivalent), diff it against the routes the product needs, and remove
  the rest. For legacy apps, shrink
  the feature set the same way and switch off high-risk admin functions nobody uses.
  OWASP: Legacy Application Management and Nodejs Security cheat sheets.
- Non-prod environments holding prod data inherit prod's threat model: either
  mask/synthesize data or secure staging like prod (staging breaches are real
  breaches).

## 7. Audit grep starters

```text
printStackTrace|traceback.format_exc|err.Error\(\) flowing into responses
DEBUG\s*=\s*True | app.debug | NODE_ENV !== 'production' branches serving errors
log.*(password|token|secret|authorization|cookie|ssn|card)   console.log\(req\b
logger?\.\w+\(.*\+.*(req|input|user)   (format-string / log-injection shape)
\*\*request\.(json|form|POST)|Object.assign\(.*req.body|update\(req.body|permit!
fields\s*=\s*["']__all__["']           to_json without :only / serializer w/o fields
jsonify\(.*__dict__|model_to_dict\(    GraphQL introspection enabled in prod config
X-Debug|X-Test-User|bypass|backdoor|magic in auth middleware
/actuator|/debug/pprof|/metrics routes without auth   sourceMap: true in prod build
autoindex on | Options ... Indexes/All | directoryBrowse enabled="true" | http.FileServer(   (§4)
resources :x without only:/except: | spring-boot-starter-data-rest | @RepositoryRestResource  (§6)
401/UNAUTHORIZED handlers with no named authn_/session_/authz_ event                      (§2.1)
```

## Audit checklist

- [ ] Does a global boundary handler convert all unhandled errors to generic client messages with correlation IDs, full detail server-side only?
- [ ] Are stack traces, paths, SQL, versions, and framework debug pages unreachable in prod responses?
- [ ] Are existence/secret oracles avoided (uniform messages, codes, and timing for auth and object-access failures)?
- [ ] Is there a logger-level redaction filter for credentials/tokens/PII, plus masked-`repr` secret types?
- [ ] Are user-controlled values sanitized for CR/LF before logging, and format strings never built from input?
- [ ] Are security events (logins, denials, role changes, admin actions) logged with actor/action/target to an append-only store with alerting?
- [ ] **Does every authentication, session and authorization outcome emit a named event
      from one vocabulary (§2.1)** — success-after-failures with a count, threshold with the
      limit, lock with a reason, failed password change at high severity, session
      create/renew/expire/logout/use-after-expiry, tampered cookie or JWT, token `jti`
      rather than the token? MEDIUM (HIGH when failures are not logged at all). Files that
      reject a request as unauthenticated but name no event:
      `grep -rlE '401|UNAUTHORIZED|Unauthorized|BadCredentials|AuthenticationFailed' . | while IFS= read -r f; do grep -qE 'authn_|authz_|session_|security_event|audit' "$f" || echo "$f"; done`
- [ ] **Is input the real client cannot send logged as tampering, distinct from routine
      validation (§2.1)?** MEDIUM. Files validating a closed set with no tampering event:
      `grep -rliE 'choices|allowed_values|oneOf|Enum\(|in_array\(|isin\(' . | while IFS= read -r f; do grep -qiE 'discrete_fail|malicious_|tamper' "$f" || echo "$f"; done`
- [ ] **Do business-logic detection points exist (§2.1)** — signup, promo and referral
      velocity, inhumanly fast flows, cross-tenant denials, deserialization failures per
      principal — and **is "paid" set only from a verified gateway confirmation?** HIGH for
      the latter. Files that mark an order paid with no verification in sight:
      `grep -rliE '(status|state)[^a-z]{1,6}(paid|captured)' . | while IFS= read -r f; do grep -qiE 'verify|signature|retriev|construct_event|gateway' "$f" || echo "$f"; done`
- [ ] **Is directory listing off and the static root an extension allowlist, with no
      backup or stray files deployed (§4)?** MEDIUM (HIGH when a listed or leftover file
      holds source or credentials):
      `grep -rnE 'autoindex[[:space:]]+on|Options([[:space:]]+[+]?[A-Za-z]+)*[[:space:]]+[+]?(Indexes|All)|directoryBrowse[[:space:]]+enabled="true"|http\.FileServer\(' .`
      ; `grep -rn -A1 'listings</param-name>' . | grep -i 'true'` (Tomcat); and over the
      deployed web root:
      `find . -type f \( -name '*.bak' -o -name '*.old' -o -name '*.orig' -o -name '*.swp' -o -name '*~' -o -name '*.inc' -o -name '*.sql' -o -name '*.zip' -o -name '*.tar.gz' \)`
      — a Go `http.FileServer` hit is fine only when every served directory has an index.
- [ ] **Has the generated route table been dumped and trimmed to what the product uses
      (§6)?** MEDIUM:
      `grep -rnE '^[[:space:]]*resources?[[:space:]]+:[a-z_]+|spring-boot-starter-data-rest|@RepositoryRestResource' . | grep -vE 'only:|except:|exported[[:space:]]*=[[:space:]]*false'`
- [ ] Are query strings free of secrets and PII?
- [ ] Does every write endpoint bind through an explicit allowlist DTO (`extra="forbid"`) — no direct body-to-model assignment?
- [ ] Are privileged fields (role, verified, tenant_id, price) unwritable via any public schema?
- [ ] Do responses use explicit output DTOs (no raw entity serialization), with field-level authz on GraphQL?
- [ ] Are client-controlled field/include/expand/sort params allowlist-resolved?
- [ ] Are debug endpoints, playgrounds, actuators, source maps, `.git`/`.env`, and magic test bypasses absent from prod, and staging data masked or staging prod-hardened?
- [ ] Are error trackers, session replay, analytics, warehouses, caches, and backups covered by the same scrubbing/retention/access rules as the primary DB?
- [ ] Do deletion flows reach secondary stores, and do exports carry full authz, audit, and short-TTL signed links?
- [ ] Is data classified at the schema level with retention enforced by automated deletion jobs?
