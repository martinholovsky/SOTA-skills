---
name: sota-code-security
description: >-
  State-of-the-art secure coding and security auditing rules (2026 baseline).
  Use whenever BUILDING or modifying code that crosses a trust boundary —
  endpoints, handlers, auth/login/signup, sessions, JWT/OAuth, file uploads,
  payments, multi-tenant features, crypto/secrets handling, parsers, CLI/exec
  wrappers, LLM agents or tool-calling — AND whenever AUDITING code for
  security (security review, pentest-prep, vulnerability hunt, threat model,
  hardening, OWASP, CWE, secrets leak, "is this code safe"). Trigger keywords:
  secure, security, vulnerability, exploit, harden, audit, authn, authz,
  authentication, authorization, crypto, TLS, sanitize, validate, injection,
  SQLi, XSS, CSRF, SSRF, IDOR, JWT, OAuth, PKCE, passkey, argon2, CSP, CORS,
  upload, rate limit, prompt injection, tool-call security, data ingestion,
  feed, parser, file upload, archive, zip bomb, decompression bomb, webhook,
  scraping, RAG corpus, deserialization, polyglot, silent failure, fail-open,
  no-op control, vacuous test, business logic.
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
6. **Every control must be falsifiable.** For each control you add, ask: *if
   this were silently a no-op, would anything observable differ?* If nothing
   would — no log, no metric, no failing test — the control is not finished.
   Assert on real loaded artifacts (not `exists()`), fail closed *and* loudly,
   never truncate what you are about to inspect or parse, and make degradation
   a distinct, metered state. rules/10 is the full catalog.
7. **Finish with the file's audit checklist.** Before declaring code complete,
   run the relevant rules files' end-of-file checklists against your own diff;
   fix every "no".

## AUDIT mode — hunting vulnerabilities against these rules

Process:
1. **Map the attack surface**: entry points (routes, GraphQL resolvers, queue
   consumers, cron jobs, WS/gRPC, webhooks, file ingestion, LLM tool loops),
   secrets locations, authz enforcement points, outbound fetchers.
2. **Sweep by rules file**, prioritized: 03 (authz) and 01 (injection) find the
   most criticals; then 02, 05, 08, 04, 07, 06, and 10 (silent no-ops) as a
   pass over whatever the others confirmed exists. For each file, grep-drive the
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
5. **Check the inert**: a control that is *present* but does nothing is invisible
   to steps 2–4, because the code is not wrong — it is a no-op. Run rules/10 as
   its own pass over every control the sweep confirmed exists: swallowed
   exceptions, weak existence checks, truncation into an inspector or out of a
   generator, degradation that never logs, and tests that pass against a
   no-op'd body. Sweep with rules/11 to decide where to look, then close with
   **rules/12** on the tools that produced your findings — an unvalidated
   instrument has produced none.
6. **Verify, then report.** No speculative findings: state the concrete exploit
   scenario; if exploitability is uncertain, say what's unverified and rate
   conservatively. Absence claims ("no instances of X") need a wider search and
   a second method than presence claims do.

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
| [rules/10-silent-control-failure.md](rules/10-silent-control-failure.md) | Controls that look enabled and do nothing: the falsification question, weak existence checks, optional-dependency degradation, empty/placeholder rulesets, swallowed enforcement exceptions, overloaded flags, early-return and truncation bypasses (into an inspector *or* out of a generator), silently-ignored config keys, doc/code default drift, **unearned claims in output — the numbers *and* the verification words** (`verified`/`reachable`/`tainted`, severity from a constant), shipped-artifact gaps, prompt/instruction standing in for an enforced control (attention leakage), a gate whose trigger never fires (a skipped job reports *Success*), **a control parked in audit/warn/dry-run/report-only mode**; the degraded-control helper; absence-claim evidence (the mutation probe itself moved to rules/12) | ...you are about to trust that a control is working — any audit pass over controls that *exist*, any build where a safeguard's failure would be invisible, any "it's enabled" claim from a banner, config, or green test |
| [rules/11-dead-path-diagnostics.md](rules/11-dead-path-diagnostics.md) | Finding the above at codebase scale: duration-not-result, printing every gate's denominator (`0 checked, 0 failed, exit 0`), cross-scale delta, telemetry silence, **the provenance of an analysis's rows — a sink that tests and production both write is two populations, and the contaminated aggregate carries the larger n**, proving a fix executed; scale-dependent silence (unbounded traversal, size-gated paths fixtures never cross, budgets that truncate coverage silently); stale-artifact no-ops (a cache/tag key narrower than the behaviour); format assumptions from one sample + lenient parsers returning plausible-but-wrong values; **contract drift by interaction — the producer/consumer seam no schema declares**; **location-dependent silence — a filter matching the ambient environment (absolute path, hostname) so a collection is correct on one machine and empty on another**; asserts stripped by `-O`/`NDEBUG`/missing `-ea`; ACTIVE/LATENT/REFUTED evidence labels; running every CI/hook/runbook script before reading any of them; **the four-state watcher model (**DONE / NOT-DONE / GONE / UNKNOWN** — `GONE` is terminal and knowable, and is the row people delete while fixing the other bug), metamorphic liveness oracles for a tool whose correct output you cannot state** (the test oracle problem); closes by handing the tools that produced the findings to rules/12 | ...sweeping a whole system for stages that report success while doing nothing, deciding where to apply rules/10, or validating that a pipeline's "0 findings" means it ran |
| [rules/12-verifying-the-verifier.md](rules/12-verifying-the-verifier.md) | Proving it, and distrusting whatever did the proving: the **mutation probe** for a security control (no-op the body, watch what fails) with its two traps; **where the probe lives** — a `--self-test` mode of the tool over a harness beside it, so "every check can go red" is a property of the suite, not of whoever last edited it; **your instrument is a control** — scorers, gates, benchmarks and thresholds need a known-bad reference at the floor and a known-good at the ceiling in CI, a negative control, abort-don't-warn, sample-before-counting, validation on inputs that *can* fail; **evidence the subject supplies about itself** (the EvoMap 84%-vacuous result); disclosing an instrument changed after results; **the guard that is an instance of what it guards** — a predicate the defect satisfies (`"auth=" in line` passes on `auth=None`), a guard nested in another gate's success branch, a denominator counting only survivors, **per-target kill verification at 100%**, vacuous satisfaction; the cross-discipline lineage (proof test, positive control, BITE, poka-yoke) | ...after rules/10 and rules/11 have produced findings, before any of them is reported or any number is quoted; whenever you add a gate, scorer or coverage assertion and need to know whether it can fail at all |
| [rules/13-context-dependent-silence.md](rules/13-context-dependent-silence.md) | The five classes rules/10 does not cover, split out of rules/11 §3 — each one **correct under the condition you tested and silently wrong under the one you shipped into**: scale-dependent silence (a size-gated path no fixture crosses), the stale-artifact no-op (a cache key narrower than the behaviour), a format assumption generalised from one sample, contract drift at a seam neither side declared — **including the seam whose producer is a model, where the defaulted read `.get(k, default)` turns a key-name disagreement into a plausible constant and only a runtime unconsumed-key diff can close it** — and location-dependent silence (correct here, empty there) | ...a diagnostic from rules/11 §2 fired — a suspicious duration, a denominator that will not move, telemetry that went quiet — and you need the class behind it; also before trusting any result measured in one environment, at one scale, against one sample |
| [rules/14-control-not-in-force.md](rules/14-control-not-in-force.md) | The other half of rules/10: not a control that runs and does nothing, but one that is **not there** — unearned claims in reporting output (the numbers *and* the verification words), shipped-artifact gaps, a natural-language instruction standing in for an enforced control, a control that never executes (a skipped job reports *Success*), and one parked in audit/warn/dry-run/report-only mode | ...you have read the control's body and it looks right; these are found by asking what **ships**, what **fires**, and what the output is **entitled to say** — never by reading the control itself |

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
