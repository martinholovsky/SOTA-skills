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
- **Every exit from a security decision that is not an explicit allow is a deny**, in any
  language: the `default` of a `switch`/`match` over roles or states, the trailing `else`,
  an early `return` taken on an unexpected value, and the decision variable's initial
  value. Handle runtime *errors* as well as exceptions: in Java, `catch (Exception e)` does
  not catch an `Error` such as `AssertionError`, and a `return true` inside `finally`
  discards whatever was thrown and allows (both measured on JDK 25). A panic recovered by
  middleware must end the request as a denial, not continue it. OWASP: Code Review Guide v2.

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
  - secrets wrapped in types whose `toString`/`repr` is masked and whose value is reachable
    only through one explicitly named accessor (Pydantic `SecretStr.get_secret_value()`,
    Rust `secrecy`'s `expose_secret()`), so every read of the secret is greppable
    (in-memory handling: `sota-secrets-management` rules/02 §7). OWASP: Code Review Guide v2.
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
- **Payment integrations keep a full trail**: log every initiation, redirect to the gateway
  and callback with timestamp and source IP, and retain the raw callback request (headers
  and body, as received) so a dispute or forensic review can re-verify it later. Retain it
  under the same access and retention rules as other payment records. OWASP: Third Party
  Payment Gateway Integration cheat sheet.
- **What goes into one log line**:
  - an attack signal names the detection rule and the parameter, not the raw payload
    (the Logging Vocabulary's `malicious_sqli` carries a `ruleid` and a parameter name); a
    stored payload is an injection into every log viewer and SIEM query that renders it;
  - every user-supplied string field gets a length cap at the logger, in every language,
    not only in a JVM layout pattern, so one request cannot flood or truncate the record;
  - sessions are correlated by a keyed or salted hash of the session ID, never the ID;
  - file paths, internal host names and IPs are sensitive: they belong in the restricted
    server-side sink, not in anything a user, a vendor or a client log can see;
  - stack traces stay server-side, in a sink with restricted access (§1 two channels).
  OWASP: Logging, Logging Vocabulary, Session Management and Java Security cheat sheets;
  Go-SCP (logging).
- **Security logging runs on a trusted server-side component.** A browser, mobile app or
  partner system can suppress, forge or replay the events it sends, so it is never the
  only record of a security event. Treat log events arriving from clients or other trust
  zones as untrusted input: validate their format and size, count and alert on
  rejections, and authenticate their source where the event feeds a decision. Ship logs
  only to sinks named in a maintained log inventory; an undeclared sink (a debug
  forwarder, a vendor SDK) is unreviewed exposure. OWASP: Logging cheat sheet, Secure
  Coding Practices QRG, ASVS 5.0 V16.2.3.
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
- **Crypto, transport and protocol failures are security events, not connectivity
  noise.** Every encrypt, decrypt or signature-verification failure
  (`crypt_decrypt_fail`, `crypt_encrypt_fail`; the user still gets the uniform error of
  rules/04 §2); an outbound TLS handshake or certificate-verification failure, which can be
  an interception attempt (rules/04 §5); a KMS, HSM or crypto-library error; and a request
  using an HTTP method the route does not serve (`TRACE`, `PUT` on a read-only resource)
  once it is past the framework's `405`. Keep each separate from generic
  `network_error`, so a burst from one peer or principal can alert.
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

### 2.2 In-application detection with graded response

Detection points that only log wait for a human. An application can also respond on its
own, which is the model OWASP's AppSensor project describes; keep it small and predictable.

- **Place a few detection points in each layer**: presentation (tampered hidden or option
  fields, §2.1), business logic (sequence violations such as `sequence_fail`, impossible
  velocity) and data access (queries outside a user's normal scope, bulk reads). Name
  each one, as §2.1 names events.
- **Accumulate, then act.** Keep a risk score per user or session (and per source) that
  each detection raises and time lowers. Thresholds are configurable per detection point,
  per group of points and overall; a single anomaly moves the score, it does not trigger
  the strongest response.
- **Give every threshold a predefined, graded response**: raise log verbosity for that
  principal, add delay, disable one function, require step-up authentication, force
  logout (kill the session), lock the account, warn the user. Reuse existing localized
  controls, such as login lockout, as response actions rather than building parallel ones.
- Responses that reach other systems (fraud-engine settings, an IP-range block at the
  edge, a SOC ticket) are listed and owned, because a false positive there spreads.
- Say in the terms of service that suspicious activity may slow, restrict or suspend an
  account, so the reaction is disclosed. OWASP: Code Review Guide v2, Cornucopia,
  WSTG-BUSL-07.

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
- **Comments and leftovers in what the browser receives.** The build strips comments from
  shipped HTML, JS and CSS (the minifier's comment removal on, license banners kept
  deliberately), and an audit reads the delivered pages, not the source: `<meta>` tags,
  the body of `3xx` redirect responses (often a full page rendered before the redirect),
  and shipped JS bundles, looking for hidden endpoints, credentials, internal host names
  and TODO notes. OWASP: WSTG-INFO-05, Go-SCP (data protection), Secure Coding Practices
  QRG.
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
- When a full sensitive value must reach the client (an account number, a tax ID, a
  recovery code), the UI masks it by default and shows it only on an explicit user action,
  with the reveal logged for high-sensitivity fields. Mobile specifics:
  `sota-mobile` rules/04 §4.13. OWASP: ASVS 5.0 V14.2.6.
- Process-and-discard applies in memory too: once processing ends, wipe or re-encrypt the
  plaintext buffers of sensitive data, not only key material (best-effort in GC runtimes;
  `sota-secrets-management` rules/02 §7). OWASP: ASVS 5.0 V11.7.2.
- **SMS is a public channel.** It is unencrypted end to end and a SIM swap redirects it, so
  it may carry low-value notifications and one-time codes (with the limits of rules/02 §5 and §7), never
  account data, balances, health or personal details, or a link that works without login.
  OWASP: Mobile Application Security cheat sheet.
- **Encryption in the wrong place does not reduce exposure.** Encrypting in browser code
  protects nothing from the user holding the key and the code; encrypting an ID in a URL
  parameter is not access control (authorize the object, rules/03). A payload that crosses
  an intermediary which terminates TLS (a CDN, an API gateway, a message broker) needs
  message-level encryption if that intermediary is not trusted with it. Data published to a
  public content-addressed store (IPFS, Arweave) cannot be access-controlled or deleted, so
  it is encrypted before publishing or not published. Browser crypto such as Web Crypto
  remains right for end-to-end designs where the user is the party meant to hold the key.
  OWASP: AJAX Security and Cryptographic Storage cheat sheets, Cornucopia CR4, SCSVS S9.4.A1.
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
- **Log files never live under a web-served path.** A log written below the document root
  or a static directory is downloadable by anyone who guesses its name, and it holds
  exactly the data §2 keeps from users. If logs must be viewable over HTTP, serve them
  behind authentication as `text/plain` with `X-Content-Type-Options: nosniff`, never
  rendered as HTML (a logged payload would run). OWASP: Logging cheat sheet, Code Review
  Guide v2.
- **Ship only what runs.** Production images and packages exclude default and sample files,
  README, CHANGELOG and other documentation, examples, tests and unused modules; they
  reveal versions and paths and sometimes work as endpoints. Enforce it with a content check
  on the built artifact in CI (list the image or package files and fail on a denylist), not
  only a `.dockerignore` (`sota-devsecops` rules/04 §4.2). OWASP: WSTG-CONF-02, Go-SCP (data
  protection), Secure Coding Practices QRG.
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
- [ ] **Does every non-allow exit of a security decision deny (§1)** — `default`, trailing
      `else`, `finally`, recovered panics, and Java `Error`s that `catch (Exception)` misses?
      HIGH: `grep -rnE '(finally|default|else)[^a-zA-Z]*[:{>-][^}]*return[[:space:]]+(true|True|ALLOW|Allow|PERMIT)|default[[:space:]]*->[[:space:]]*(true|ALLOW|PERMIT)' .`
- [ ] **Are log lines free of raw payloads, raw session IDs and unbounded user strings, with
      stack traces, paths and host names only in the restricted sink (§2)?** MEDIUM:
      `grep -rnE '(log|logger|logging)\.[a-z]+\(.*(session_?id|session\.getId\(\)|sessionid|request\.body|req\.body|raw_?payload)' . | grep -viE 'hash|hmac|sha256'` — and confirm a length cap in the logger configuration.
- [ ] **Does security logging run server-side, with client- or partner-supplied log events
      validated as untrusted input and every sink in a log inventory (§2)?** MEDIUM. Client
      log intake routes to read: `grep -rnE '["'"'"'][^"'"'"']*/(client-?logs?|logs?|logging|telemetry)(/[a-z]*)?["'"'"']' .`
- [ ] **Do payment integrations log initiation, redirect and callback, and retain the raw
      callback (§2)?** MEDIUM. Callback handlers with no raw retention or audit in sight:
      `grep -rliE '(payment|gateway|checkout|stripe|adyen|paypal)[a-z_/-]*(callback|webhook|notify|ipn)' . | while IFS= read -r f; do grep -qiE 'raw_?(body|payload|callback|request)|get_data\(|getRawBody|rawBody|audit' "$f" || echo "$f"; done`
- [ ] **Do encrypt/decrypt/verify failures, outbound TLS or certificate failures, KMS/HSM
      errors and unexpected HTTP methods each emit a named security event (§2.1)?** MEDIUM.
      Files that catch such a failure and name no event:
      `grep -rlE 'InvalidTag|AEADBadTagException|BadPaddingException|CryptographicException|SSLHandshakeException|CertificateError|SSLCertVerificationError|ERR_TLS_CERT|message authentication failed' . | while IFS= read -r f; do grep -qiE 'crypt_(de|en)crypt_fail|security_?(event|log)|tls_fail|audit' "$f" || echo "$f"; done`
- [ ] **Is there in-application detection with graded, predefined responses and configurable
      thresholds (§2.2)?** LOW as a weakness when absent (MEDIUM for high-value or regulated
      flows): `grep -rqiE 'appsensor|detection_?point|risk_?score|threat_?score|response_?action' . || echo 'no in-app detection/response module: record as a weakness'` — then list every response that reaches another system.
- [ ] **Do shipped HTML, JS, meta tags and redirect bodies carry no revealing comments or
      notes (§4)?** LOW (HIGH when a credential or hidden endpoint is found). Over the built
      output, not the source: `grep -rniE '<!--.*(todo|fixme|password|secret|api[_-]?key|internal|/admin|debug)|(//|/\*).*(todo|fixme|password|secret|api[_-]?key|internal)' .`
- [ ] **Are full sensitive values masked in the UI until revealed, in-memory plaintext wiped
      after use, and nothing sensitive sent by SMS (§5)?** MEDIUM:
      `grep -rnE '\{[^}]*\.(ssn|iban|account_?number|card_?number|pan|tax_?id|national_?id)[^}]*\}' . | grep -viE 'mask|redact|last4|reveal'` ; `grep -rniE '(sms|messages\.create|sendSms|send_sms|publish\(.*PhoneNumber).*(balance|account_?number|iban|ssn|diagnos|password|date_of_birth|dob)' .`
- [ ] **Is encryption placed where it protects (§5)** — no client-side "encryption" or
      encrypted URL IDs standing in for access control, message-level encryption across
      untrusted TLS-terminating hops, nothing unencrypted on public content-addressed
      storage? MEDIUM (HIGH for personal data on IPFS/Arweave). Sites to read:
      `grep -rnE 'CryptoJS\.(AES|DES|TripleDES|Rabbit)\.(en|de)crypt|crypto\.subtle\.(en|de)crypt|ipfs\.(add|addAll)\(|arweave\.createTransaction\(|pinFileToIPFS' .`
- [ ] **Are log files outside every web-served path (§6)?** HIGH when one is reachable:
      `grep -rnE '(access_log|error_log|fileName|filename|FileHandler\(|path)[^#]*(/var/www|/htdocs|/wwwroot|/public/|/static/|webapps/|(^|[^a-z])static/|(^|[^a-z])public/)[^[:space:]"'"'"']*\.log' .`
- [ ] **Does CI check the built artifact's contents for docs, samples, examples, tests and
      unused modules (§6)?** LOW. Over the unpacked image or package root:
      `find . -type f \( -iname 'README*' -o -iname 'CHANGELOG*' -o -iname '*.md' -o -iname '*.sample*' -o -iname '*.example*' -o -path '*/examples/*' -o -path '*/samples/*' -o -path '*/docs/*' -o -path '*/doc/*' -o -path '*/test/*' -o -path '*/tests/*' \)`
      — a licence notice kept on purpose is fine.
