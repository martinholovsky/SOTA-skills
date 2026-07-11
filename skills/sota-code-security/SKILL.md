---
name: sota-code-security
description: >-
  State-of-the-art secure coding and security auditing rules (2026 baseline).
  Use whenever BUILDING or modifying code that crosses a trust boundary —
  endpoints, handlers, auth/login/signup, sessions, JWT/OAuth, file uploads,
  payments, multi-tenant features, crypto/secrets handling, parsers, CLI/exec
  wrappers, LLM agents or tool-calling — AND whenever AUDITING code for
  security (security review, pentest-prep, vulnerability hunt, threat model,
  hardening, OWASP, CWE, injection, XSS, CSRF, SSRF, IDOR, deserialization,
  prompt injection, secrets leak, "is this code safe"). Trigger keywords:
  secure, security, vulnerability, exploit, harden, audit, authn, authz,
  authentication, authorization, crypto, TLS, sanitize, validate, injection,
  SQLi, XSS, CSRF, SSRF, IDOR, JWT, OAuth, PKCE, passkey, argon2, CSP, CORS,
  upload, rate limit, prompt injection, tool-call security, data ingestion,
  feed, parser, file upload, archive, zip bomb, decompression bomb, webhook,
  scraping, RAG corpus, deserialization, polyglot.
---

# SOTA Code Security

## Purpose

One skill, two modes. The `rules/` files define the 2026 secure-coding baseline
(OWASP Top 10 2025/API 2023/LLM + Agentic Top 10, CWE-mapped). In **BUILD** mode
you write
code that conforms to the rules by default. In **AUDIT** mode you hunt for
violations of the same rules and report them as severity-rated findings. The
rules are the single source of truth for both — anything a rules file forbids
is a finding; anything it mandates is the implementation default.

Threat-model framing for both modes: every input is hostile until validated at
a trust boundary; every output channel (response, error, log, model context) is
adversary-readable; every privileged operation needs an explicit, code-enforced
(never prompt-, comment-, or convention-enforced) authorization decision.

## BUILD mode — secure-by-default while writing code

1. **Identify trust boundaries first.** Before writing a handler/parser/job,
   name what crosses in (user input, third-party content, model output, file
   bytes) and what authority the code wields. Pick the relevant rules files
   from the index below and follow them as you write — not as a review pass.
2. **Defaults, not options.** Use the rules' default choices without being
   asked: parameterized queries, argv-exec, argon2id, AEAD via libsodium-class
   libraries, `__Host-` cookies, allowlist DTOs (`extra=forbid`), deny-by-default
   route policy, per-principal rate limits, timeouts on every outbound call.
3. **Structural over disciplinary.** Prefer designs where the insecure variant
   cannot be written: ownership predicates inside queries, RLS for tenancy,
   typed Secret wrappers with masked repr, central crypto/authz modules, logger
   redaction filters. If safety depends on every future dev remembering a rule,
   redesign.
4. **Never hand-roll** crypto, session machinery, password hashing, JWT/OAuth
   protocol steps, HTML sanitizers, or auth token schemes. Compose vetted
   libraries per rules/02 and rules/04.
5. **When requirements force a deviation** (e.g. shell-out unavoidable, CORS
   must reflect origins), implement the rules file's documented mitigation
   stack and leave a `SECURITY:` comment stating the residual risk.
6. **Finish with the file's audit checklist.** Before declaring code complete,
   run the relevant rules files' end-of-file checklists against your own diff;
   fix every "no".

## AUDIT mode — hunting vulnerabilities against these rules

Process:
1. **Map the attack surface**: entry points (routes, GraphQL resolvers, queue
   consumers, cron jobs, WS/gRPC, webhooks, file ingestion, LLM tool loops),
   secrets locations, authz enforcement points, outbound fetchers.
2. **Sweep by rules file**, prioritized: 03 (authz) and 01 (injection) find the
   most criticals; then 02, 05, 08, 04, 07, 06. For each file, grep-drive the
   hunt from its named sinks/APIs (e.g. `shell=True`, `dangerouslySetInnerHTML`,
   `verify=False`, `pickle.loads`, `merge(`, `Object.assign(.*req.body`,
   `permit!`, `algorithms=` absent near `jwt.`).
3. **Trace, don't pattern-match**: confirm untrusted data actually reaches the
   sink and no upstream boundary neutralizes it. Report the full source→sink
   path. A reachable sink with attacker data = finding; an unreachable one =
   note as hardening debt, Low.
4. **Check the negatives**: missing controls are findings too — absent rate
   limiting, absent CSRF tokens, absent tenant predicate, absent timeout,
   absent security headers. Use each rules file's audit checklist as the
   completeness gate; every "no" answer becomes a finding or an accepted risk.
5. **Verify, then report.** No speculative findings: state the concrete exploit
   scenario; if exploitability is uncertain, say what's unverified and rate
   conservatively.

### Severity conventions (CVSS-style impact mapping)

| Severity | CVSS band | Criteria | Examples |
|---|---|---|---|
| **Critical** | 9.0–10.0 | Unauthenticated (or trivially authenticated) remote compromise of confidentiality/integrity at scale: RCE, SQLi dumping the DB, auth bypass, cross-tenant read/write, secrets in public repo/client bundle | `pickle.loads(request.body)`; JWT `alg` not pinned; reflected-Origin CORS with credentials; tenant_id from request param |
| **High** | 7.0–8.9 | Single-user-scoped compromise or privileged-precondition full compromise: IDOR on sensitive objects, stored XSS, SSRF reaching metadata, authenticated command injection, session fixation, missing object-level authz | Ownership check missing on `GET /documents/{id}`; `dangerouslySetInnerHTML` on user bio; upload served executable from app origin |
| **Medium** | 4.0–6.9 | Meaningful weakening requiring chaining or limited impact: CSRF on non-critical state, ReDoS/resource exhaustion, missing rate limit on login, verbose errors leaking internals, weak-parameter argon2/bcrypt, missing security headers on sensitive pages, log injection | No lockout on login; stack traces in prod 500s; `SameSite` unset with no CSRF token but Origin checked |
| **Low** | 0.1–3.9 | Hardening gaps and defense-in-depth misses with no direct exploit: missing `__Host-` prefix, `Server` header exposure, report-only CSP, unmasked PII in internal logs, missing `Vary: Origin` | Cookie lacks prefix; HSTS missing includeSubDomains; EXIF not stripped |

Adjust one band up/down for context: data sensitivity (health/financial ↑),
internet-exposed vs internal-only (↓ one max — network position is not identity),
existing compensating control (↓), trivially scriptable at scale (↑).

### Finding format

```
[SEVERITY] <title>
File: <path>:<line>            (every claim anchored to file:line)
CWE: CWE-<id> (<name>)         (omit only if genuinely unmapped)
Source → Sink: <where attacker data enters> → <dangerous operation>
Exploit scenario: <concrete attacker story: who, sends what, gets what>
Fix: <specific change, referencing the rules/ section with the pattern>
```

Order the report Critical→Low; lead with a one-paragraph executive summary
(counts by severity, worst finding, systemic themes). Group repeated instances
of one weakness into a single finding listing all locations.

## Rules index

| File | Topics | Read this when... |
|---|---|---|
| [rules/01-input-injection.md](rules/01-input-injection.md) | SQLi/NoSQLi, command & argument injection, path traversal/Zip Slip, SSRF + DNS rebinding, XXE, SSTI, deserialization, prototype pollution, ReDoS, canonicalization, allowlist validation | ...any external data reaches a query, shell, path, URL fetcher, parser, template, regex, or object loader; writing input validation; auditing any handler |
| [rules/02-authentication.md](rules/02-authentication.md) | argon2id parameters, credential-stuffing defense, session lifecycle/fixation, JWT (alg pinning, claims, storage, refresh rotation), OAuth2/OIDC + PKCE, MFA/TOTP, account recovery, passkeys/WebAuthn | ...building or reviewing login, signup, sessions, tokens, SSO, password reset, MFA enrollment, or anything that proves identity |
| [rules/03-authorization.md](rules/03-authorization.md) | Deny-by-default enforcement, IDOR/BOLA, function-level authz, RBAC/ABAC/ReBAC, multi-tenant isolation (RLS), confused deputy, authz bypass patterns | ...any endpoint takes an object ID; multi-tenant features; role/permission systems; service-to-service trust; hunting access-control bugs (start here for audits) |
| [rules/04-cryptography.md](rules/04-cryptography.md) | Algorithm table (AEAD, X25519, Ed25519), nonce discipline, CSPRNG use, key management/rotation/KMS, TLS config & cert verification, constant-time comparison, tamper-evident logs/audit ledgers (keyed chains, anchoring, integrity vs completeness), secrets in code/CI | ...encrypting, signing, hashing, generating tokens, configuring TLS, storing secrets, building or auditing a "tamper-evident"/audit ledger, or you see any crypto primitive or `verify=False` in code |
| [rules/05-web-security.md](rules/05-web-security.md) | Context-aware XSS encoding, Trusted Types, nonce-based CSP, CSRF stack, CORS misconfig, clickjacking, header baseline, cookie attributes/prefixes, file upload pipeline | ...rendering user content, setting headers/cookies, configuring CORS, handling uploads, or auditing anything browser-facing |
| [rules/06-memory-resource-safety.md](rules/06-memory-resource-safety.md) | Integer overflow/truncation, bounds & banned C APIs, unsafe/FFI policy, untrusted size fields, decompression bombs, timeouts/rate limits/load shedding, TOCTOU & race-driven bypass | ...parsing binary formats, doing arithmetic on input-derived sizes/money, writing C/C++/unsafe Rust/FFI, or auditing DoS and concurrency surfaces |
| [rules/07-data-exposure.md](rules/07-data-exposure.md) | Leak-free error handling, oracle-free responses, logging redaction & log injection, security event logging, mass assignment, response over-exposure, debug surfaces in prod | ...designing errors/logging, binding request bodies to models, shaping API responses, or auditing what an attacker learns from outputs |
| [rules/08-llm-ai-security.md](rules/08-llm-ai-security.md) | Prompt injection (direct/indirect), lethal trifecta, dual-LLM/taint gating, tool-call authorization & human-in-the-loop, model output as untrusted data, RAG ACLs, model supply chain | ...building or auditing anything with an LLM: agents, tool calling, RAG, chat UIs rendering model output, MCP servers, prompt/completion logging |
| [rules/09-untrusted-data-ingestion.md](rules/09-untrusted-data-ingestion.md) | Hostile data feeds/content; ingest as a trust boundary, provenance/taint tagging; sandboxed parsers (image/archive/PDF/Office/XML/CSV/JSON, fuzzy-hash); zip-slip/zip-bomb/pixel-bomb/decompression caps; size/rate/timeout DoS controls, quarantine/DLQ; parse-don't-validate, MIME sniffing, polyglots, AV; feed integrity & broker pattern | ...ingesting attacker-authored external data — threat-intel/RSS feeds, scraped content, user uploads, third-party webhooks/APIs, RAG corpora, email, file imports — through parsers into storage/UI; auditing collectors, upload endpoints, or feed pipelines |

## Top-10 non-negotiables

Violations of these are findings regardless of context; in BUILD mode they are
never acceptable shortcuts:

1. **Every SQL/NoSQL value parameterized** — no string-built queries, raw-query
   escape hatches audited, identifiers allowlist-mapped. (CWE-89)
2. **No shell string execution** — argv arrays only, `--` separators, no
   `shell=True`/`exec(string)`. (CWE-78)
3. **No native deserialization of untrusted data** — no pickle /
   ObjectInputStream / unserialize / Marshal / yaml.load; data-only formats +
   schema. (CWE-502)
4. **Object-level authz on every ID the client supplies** — ownership/tenant
   predicate inside the query, deny by default, 404 for unauthorized. (CWE-639/862)
5. **Passwords only as argon2id (or scrypt/bcrypt) hashes** at current
   parameters; login/reset rate-limited with uniform errors. (CWE-916/307)
6. **JWT verification pins algorithms and checks `exp`/`iss`/`aud`**; OAuth is
   Authorization Code + PKCE with exact redirect URIs; tokens never in
   localStorage or URLs. (CWE-347)
7. **No hardcoded or client-shipped secrets, no disabled TLS verification** —
   CSPRNG for all tokens, constant-time comparison for all secret checks.
   (CWE-798/295/330/208)
8. **All user-influenced output encoded/sanitized for its sink** — HTML context
   encoding + allowlist sanitizer for rich text; applies equally to LLM output.
   (CWE-79)
9. **Outbound fetch of user-supplied URLs gets full SSRF defense** — scheme
   allowlist, post-resolution private-IP block, pinned connection, redirect
   re-validation. (CWE-918)
10. **LLM tool calls authorized in code against the human principal** —
    session-bound scoping, schema-validated arguments, human confirmation for
    irreversible actions; prompts are never the security boundary. (CWE-863)
