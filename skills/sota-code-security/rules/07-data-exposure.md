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
```

## Audit checklist

- [ ] Does a global boundary handler convert all unhandled errors to generic client messages with correlation IDs, full detail server-side only?
- [ ] Are stack traces, paths, SQL, versions, and framework debug pages unreachable in prod responses?
- [ ] Are existence/secret oracles avoided (uniform messages, codes, and timing for auth and object-access failures)?
- [ ] Is there a logger-level redaction filter for credentials/tokens/PII, plus masked-`repr` secret types?
- [ ] Are user-controlled values sanitized for CR/LF before logging, and format strings never built from input?
- [ ] Are security events (logins, denials, role changes, admin actions) logged with actor/action/target to an append-only store with alerting?
- [ ] Are query strings free of secrets and PII?
- [ ] Does every write endpoint bind through an explicit allowlist DTO (`extra="forbid"`) — no direct body-to-model assignment?
- [ ] Are privileged fields (role, verified, tenant_id, price) unwritable via any public schema?
- [ ] Do responses use explicit output DTOs (no raw entity serialization), with field-level authz on GraphQL?
- [ ] Are client-controlled field/include/expand/sort params allowlist-resolved?
- [ ] Are debug endpoints, playgrounds, actuators, source maps, `.git`/`.env`, and magic test bypasses absent from prod, and staging data masked or staging prod-hardened?
- [ ] Are error trackers, session replay, analytics, warehouses, caches, and backups covered by the same scrubbing/retention/access rules as the primary DB?
- [ ] Do deletion flows reach secondary stores, and do exports carry full authz, audit, and short-TTL signed links?
- [ ] Is data classified at the schema level with retention enforced by automated deletion jobs?
