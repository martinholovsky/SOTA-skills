# 03 — Per-Component Threat Catalogs

Use these catalogs AFTER decomposition (`02`): for each component on the DFD,
walk its catalog and emit threat sentences (*actor → action → asset → impact*)
for every applicable item. In AUDIT mode, additionally record control
present/partial/absent with file:line evidence (`06`).

Catalogs are floors, not ceilings — they encode the threats that recur in
practice; boundary-specific reasoning (`01` §2) finds the rest. STRIDE/LINDDUN
letters annotate each item for classification.

## 1. Web frontend (browser-executed code)

- **XSS in all variants (T/I/E):** reflected, stored, DOM-based; framework
  escape hatches (`dangerouslySetInnerHTML`, `v-html`, `innerHTML`,
  `bypassSecurityTrust*`). Stored XSS is a time-shifted boundary crossing —
  attacker content executes later in victims' sessions.
- **CSP absent or neutered (defense-in-depth for XSS):** `unsafe-inline`,
  `unsafe-eval`, wildcard sources defeat the point. Audit the header, not the
  intent.
- **Token storage (I/S):** long-lived tokens in `localStorage` are exfiltrable
  by any XSS; prefer httpOnly+SameSite cookies or in-memory + refresh.
- **CSRF (S/T):** state-changing requests authenticated by cookies need
  SameSite + anti-CSRF token; JSON-only APIs still need it if cookies auth and
  content-type isn't enforced server-side.
- **Client-side authz as the ONLY authz (E):** hidden admin menu ≠ access
  control; every privileged decision re-checked server-side.
- **Secrets shipped in bundles (I):** API keys, internal URLs, feature-flag
  payloads — assume the bundle is public; grep build artifacts for entropy.
- **Supply chain (T):** npm dependencies execute in your security context;
  third-party `<script>` tags execute in your origin; subresource integrity
  for CDN assets; lockfile + provenance for packages.
- **Open redirects (S):** `?next=` params feeding `location` enable phishing
  and OAuth token theft; allowlist destinations.
- **postMessage / iframe (S/T/I):** missing origin checks on `message`
  listeners; embedding untrusted iframes without `sandbox`; clickjacking —
  `frame-ancestors`.
- **Sensitive data residue (I/L):** PII in URL params (logged everywhere),
  browser cache/history, analytics events, session-replay tools (LINDDUN: L,
  Dd).

## 2. API / backend service

- **Broken object-level authz / IDOR (E/I):** THE top API threat. Every
  handler touching a resource by ID must verify the caller's right to THAT
  object, not just a valid session. Audit: pick 5 by-ID endpoints, find the
  tenant/owner check.
- **Broken function-level authz (E):** admin routes guarded only by URL
  obscurity or frontend; middleware exclusion lists.
- **Mass assignment / over-binding (T/E):** request body bound straight to
  model (`role`, `is_admin`, `price` settable). Use explicit allowlists/DTOs.
- **Injection (T/I/E):** SQL (string-built queries), NoSQL (`$where`, operator
  injection), command (`exec` with user input), template (SSTI), LDAP, header/
  log injection (CRLF). Parameterize; treat logs as an injection sink.
- **SSRF (S/I/E):** any user-influenced URL fetched server-side (webhook test
  buttons, importers, PDF renderers, image proxies) reaches internal services
  and cloud metadata (§9). Allowlist scheme+host+port; block link-local; re-
  resolve after redirects (DNS rebinding).
- **Authn weaknesses (S):** JWT alg confusion / `none`, unvalidated `aud`/
  `iss`, no expiry check, symmetric key reuse across services; password reset
  token predictability; missing brute-force lockout/rate limit; session
  fixation.
- **Unsafe deserialization (T/E):** pickle/Java serialization/`yaml.load` on
  external data = RCE primitive. Treat serialized blobs as code.
- **Excessive data exposure (I):** returning full ORM objects and filtering
  client-side; verbose errors with stack traces/SQL; GraphQL introspection +
  unbounded query depth/aliases (also D).
- **Rate limiting & resource caps (D):** per-principal limits on authn
  endpoints, expensive queries, pagination (`?limit=10000000`), regex on user
  input (ReDoS), zip/XML expansion (bombs, XXE — also I).
- **Repudiation (R):** security-relevant actions (login, authz failure,
  privilege change, data export) logged with actor + object + outcome, to a
  store app credentials can't rewrite.
- **Internal trust (S/E):** "internal" services accepting unauthenticated
  calls — anyone with SSRF or a foothold is "internal".

## 3. Database / data tier

- **Shared superuser account (E):** every service connecting as one privileged
  user = no internal boundaries; per-service users, least privilege, no DDL at
  runtime.
- **Network exposure (S/I):** DB reachable beyond its app subnet; public IPs
  on managed DBs; no TLS on connections.
- **Encryption (I):** at-rest (and: who holds the key — disk encryption
  doesn't stop SQL-level theft); field-level for crown jewels (tokens, SSNs)
  so a SQLi/backup leak yields ciphertext.
- **Backups & replicas (I):** backups inherit none of prod's access controls
  by default — encrypted? access-logged? tested restore? Read replicas with
  weaker creds; snapshots shared cross-account.
- **Row-level isolation (E/I):** multi-tenant tables relying solely on app
  WHERE clauses; consider RLS as a second layer for high-value tenancy.
- **Audit & repudiation (R):** DDL/DCL and bulk-read logging; who watches
  `SELECT *` of the users table?
- **Retention & privacy (LINDDUN Dd/Nc):** retention enforced (TTL/jobs), data
  deletion actually deletes (incl. backups policy), purpose-bound copies (no
  prod PII in staging/analytics without masking).
- **ORM truths (T):** raw query escape hatches (`.raw(`, `text(`,
  `query_string`) carry injection risk audits often skip.

## 4. Message queue / event stream

A queue is a **time-shifted entry point**: consumers execute attacker-era data
in a later, often more privileged context.

- **Producer authn/authz (S):** can any internal workload publish to any
  topic? Shared broker creds = any compromised pod forges any event. Per-
  service credentials + topic ACLs.
- **Message integrity & schema (T):** consumers validate schema + business
  invariants (price ≥ 0, state transitions legal); never trust
  producer-supplied identity fields — derive actor from broker auth or signed
  envelope.
- **Confused-deputy consumers (E):** consumer acts at high privilege on
  low-trust data ("delete-user" event with attacker-chosen ID). Re-check
  authorization at consumption time, not just production time.
- **Poison messages & retries (D):** malformed message crash-looping a
  consumer stalls the partition; DLQ + max retries; idempotency keys (replay =
  duplicate side effects — payments!).
- **Disclosure (I):** queues persist PII/secrets in payloads; broker at-rest
  encryption, payload minimization (send IDs not blobs), DLQ contents are an
  unmonitored data store of your worst messages.
- **Ordering/race abuse (T):** logic depending on event order an attacker can
  influence (cancel-after-ship races, double-spend via concurrent consumers).
- **Repudiation (R):** event provenance — which principal produced this
  message, traceable end to end?

## 5. File storage / upload pipelines

- **Content-type laundering (T/E):** trust magic bytes + re-encode, never the
  client `Content-Type` or extension; SVG is XSS, HTML upload + same-origin
  serving = stored XSS; polyglot files.
- **Parser attack surface (E/D):** image/PDF/office parsers are RCE farms —
  sandbox/isolate parsing workers (separate service, no creds, egress-deny);
  decompression bombs; XML in office docs → XXE.
- **Path traversal (T/I):** user-influenced filenames/keys (`../`, absolute
  paths, unicode normalization); generate server-side names, map via DB.
- **Serving (I/E):** serve user content from a separate origin/domain (cookie
  isolation); signed URLs with short expiry; no public-listable buckets (§9);
  `Content-Disposition` + `X-Content-Type-Options: nosniff`.
- **Authorization (E/I):** signed-URL leakage via referer/logs; per-object
  authz on download endpoints (file IDOR is as common as API IDOR).
- **Malware relay (abstract asset):** your storage distributing malware to
  other users — scanning or risk-acceptance, stated either way.
- **Quota (D):** per-user size/count caps; multipart abandonment cleanup.

## 6. CI/CD & build pipeline

The pipeline holds deploy creds and shapes every artifact — it is usually the
highest-privilege, least-modeled component.

- **Poisoned pipeline execution (T/E):** PRs from forks executing privileged
  workflows; `pull_request_target` + checkout-of-PR-head; injectable
  expressions (`${{ github.event.issue.title }}` in `run:`); pipeline config
  editable by the same PR it gates.
- **Secrets exposure (I):** long-lived cloud keys in CI secrets vs. OIDC
  federation; secrets readable by all repo collaborators; secret-echo via
  `set -x`/debug logs; cache poisoning across trust levels (PR cache reused by
  main builds).
- **Dependency/supply chain (T):** lockfiles + integrity hashes enforced in
  CI; dependency confusion (internal package names registered publicly,
  registry order); install scripts execute at build privilege; typosquats;
  base-image provenance and pinning by digest.
- **Artifact integrity (T):** signed artifacts/provenance (SLSA-style) so prod
  runs what CI built; deploy step verifies signature; who can push to the
  registry directly, bypassing CI?
- **Runner trust (E):** self-hosted runners on shared infra = lateral
  movement; ephemeral runners; runner reach into prod networks.
- **Branch protection as a security control (T/R):** force-push/admin-bypass
  on release branches; required reviews on workflow files specifically; audit
  trail of who approved what.
- **Environment promotion (E):** can staging creds deploy to prod? Separate
  identities per environment.

## 7. Mobile clients

- **The app binary is public (I):** secrets/API keys in the app are
  extracted — assume so; per-user tokens only; server-side checks for
  everything (client is UI, never enforcement).
- **Local storage (I):** tokens/PII in Keychain/Keystore, not plist/
  shared-prefs/SQLite plaintext; OS backups capture app data — mark exclusions.
- **Transport (S/I):** TLS everywhere + pinning for high-value apps (with a
  rotation story); user-installed CA threat for sensitive verticals.
- **Deep links / app links (S/T):** unvalidated deep-link params hitting authn
  actions; link hijacking (claim verified app links); OAuth redirect via
  custom scheme is interceptable — use PKCE always.
- **IPC surface (E):** exported Android components (activities/receivers/
  providers) — audit the manifest; iOS URL schemes and extensions.
- **WebView (T/E):** JS bridges (`addJavascriptInterface`) exposing native
  functions to loaded content; loading remote content in privileged WebViews.
- **Reverse engineering & tamper (T):** root/jailbreak + repackaging for
  client-trusting apps (games, payments); attestation (Play Integrity/App
  Attest) as mitigation where the business case warrants.
- **Privacy (LINDDUN):** device identifiers enabling cross-app linking (L/I);
  analytics SDKs shipping PII (Dd/U); permissions minimal (U).

## 8. LLM agent / tool-use systems

Model the LLM as a **confused-deputy-prone process whose control plane and
data plane are the same channel**. Every token the model reads is potentially
instructions. Companion catalogs: OWASP LLM Top 10 and the OWASP Top 10 for
Agentic Applications 2026 (ASI01–ASI10: goal hijack, tool misuse, identity/
privilege abuse, agentic supply chain, unexpected code execution, memory
poisoning, inter-agent comms, cascading failures, human-trust exploitation,
rogue agents) — the items below cover them; use ASI numbering when reporting.

- **Direct prompt injection (S/T):** user input overriding system intent.
  System prompts are not a security boundary — assume full disclosure of the
  prompt (I) and design so that prompt knowledge gains nothing.
- **Indirect prompt injection (S/T/E) — the defining threat:** instructions
  embedded in retrieved web pages, RAG documents, emails, tickets, tool
  outputs, repo files. Any agent that (a) reads attacker-influenceable content
  AND (b) has tools with side effects is exploitable by default. Enumerate
  every content source on the DFD as a hostile entry point.
- **Excessive agency (E):** tool scope beyond the task (agent with `send_email`
  + `read_all_docs` = exfiltration machine). Least-privilege tools: per-task
  allowlists, read-only by default, scoped credentials per invocation, human
  confirmation gates on irreversible/external actions (payments, deletes,
  sends, code execution).
- **Exfiltration via outputs (I):** injected instructions encode secrets into
  markdown image URLs, links, or tool parameters. Mitigate: egress allowlists,
  render-time URL sanitization, no auto-fetch of model-emitted URLs.
- **Tool-call injection (T/E):** model-generated arguments flowing into
  SQL/shell/URLs — tool implementations must validate args exactly like an
  internet-facing API (the model is an untrusted caller).
- **Cross-tenant leakage in RAG (I/E):** retrieval must enforce the CALLER's
  ACLs at query time — embeddings stores rarely carry authz natively.
- **Multi-agent / MCP trust (S/T):** third-party tool servers and agent cards
  are org-boundary crossings; tool descriptions themselves can carry
  injections; pin/verify tool definitions.
- **Named MCP attack classes (T/S/E)** — enumerate per attached server; use
  these names in findings (OWASP MCP Top 10 MCP03:2025; MITRE ATLAS
  AML.T0104); mitigations detailed in sota-code-security rules/23 §1:
  - *Tool poisoning:* hidden instructions in tool descriptions/metadata →
    violates the instruction/data boundary → pin + human-review full
    definitions at install.
  - *Rug pull:* tool definition/behavior changes after approval → violates
    the approval's integrity over time → hash-pin definitions, re-approve on
    change.
  - *Tool shadowing:* one server's descriptions steer use of ANOTHER server's
    tools → violates inter-server isolation → separate sessions/agents for
    high-privilege tools.
  - *Line jumping:* injection at `tools/list`, before any call → bypasses
    invocation-time gates → treat listings as untrusted; review before
    connecting.
  - *Preference manipulation (MPMA):* manipulative descriptions bias tool
    selection toward attacker servers → violates selection integrity →
    allowlisted servers + description review.
- **Reasoning-model attacks (S/D):** CoT hijacking / H-CoT — untrusted text
  posing as the model's own reasoning steers safety/tool decisions (S);
  OverThink-class decoys in retrieved content force excessive reasoning
  tokens — cost/latency exhaustion (D). Cap reasoning budgets; keep untrusted
  content out of reasoning scaffolds (sota-code-security rules/23 §1).
- **Memory/state poisoning (T):** persisted conversation memory or scratchpads
  let an injection survive across sessions and users.
- **DoS / cost (D):** unbounded agent loops, token-expensive inputs, recursive
  tool calls — cap steps, tokens, spend per request.
- **Privacy (LINDDUN):** prompts/completions logged with PII (Dd); user data in
  fine-tuning/eval sets (Nc); provider data-retention terms (org boundary).
- **Mitigation pattern:** dual-LLM / plan-then-execute (planner sees untrusted
  content, executor with tools sees only structured plan), or taint-tracking:
  once untrusted content enters context, downgrade available tools for the
  rest of the session.

## 9. Cloud-specific threats (cross-cutting)

- **IAM misconfig (E):** wildcard actions/resources (`"Action":"*"`);
  privilege-escalation primitives (`iam:PassRole` + `*:Create*`,
  `iam:PutUserPolicy`, `sts:AssumeRole` trust policies open to broad
  principals); unused-but-live credentials; no permission boundaries on CI
  identities. Audit IaC, not the console.
- **Metadata service / credential theft (I/E):** SSRF → `169.254.169.254` →
  role creds (the canonical cloud kill chain). Enforce IMDSv2/hop-limit=1 (or
  GCP metadata header), block link-local egress from app containers, minimal
  instance roles.
- **Public buckets/storage (I):** bucket policy + ACL + account-level
  public-access-block all checked; "authenticated users" ≠ "my users"; listable
  buckets enumerate keys; same for public snapshots/AMIs/container registries.
- **Cross-account trust (S/E):** resource policies (S3, KMS, SNS, Lambda)
  granting external accounts; confused deputy without `ExternalId`/source-arn
  conditions.
- **Secrets sprawl (I):** secrets in env vars visible to whole task/pod, in
  IaC state files (state bucket protection!), in container layers, in Lambda
  env config readable by `lambda:GetFunction`.
- **Logging/detection (R):** control-plane audit logs (CloudTrail-class) on,
  immutable, alarmed for IAM changes and impossible-travel; flow logs at
  boundaries you claimed in the model.
- **Serverless/managed (E/D):** function resource policies (who can invoke),
  event-source injection (S3 key names, SNS payloads as untrusted input),
  concurrency limits as DoS containment.

## Audit checklist

- [ ] Every DFD component mapped to its catalog; each item dispositioned
      (present/partial/absent/N-A) — no silent skips.
- [ ] Frontend: XSS sinks audited, CSP effective, token storage justified,
      CSRF covered, no secrets in bundles.
- [ ] API: object-level authz verified on sampled by-ID endpoints; mass
      assignment, SSRF, deserialization, and rate limits checked with code
      evidence.
- [ ] Database: per-service least-priv users, encryption + key custody,
      backup/replica protections, retention enforcement.
- [ ] Queues: producer authn, schema validation at consumers, authz re-check
      at consumption, idempotency, DLQ handling.
- [ ] File pipeline: magic-byte validation, parser isolation, traversal-proof
      naming, separate serving origin, download authz.
- [ ] CI/CD: fork-PR privilege, OIDC over static keys, lockfile enforcement,
      artifact signing, workflow-file review protection, runner isolation.
- [ ] Mobile: no embedded shared secrets, Keychain/Keystore usage, PKCE,
      exported-component audit, WebView bridge audit.
- [ ] LLM/agent: every content source treated as hostile, tool least-
      privilege + confirmation gates, output URL handling, RAG ACL
      enforcement, step/spend caps.
- [ ] Cloud: IAM wildcards and escalation primitives, IMDSv2/metadata
      protection, public-access blocks, cross-account conditions, audit-log
      immutability.
