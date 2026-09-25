# 23 — LLM Platform & Supply Chain: Models, Prompts, MCP Servers, Logging

Split out of rules/08 (formerly section 5) on 2026-09-25, when rules/08 neared the 500-line cap;
the section is now §1. rules/08 keeps its other section numbers, so §6 there is unchanged.

## 1. Platform & supply-chain notes

- Treat downloaded models/weights/adapters like executable dependencies:
  pinned versions, checksums, trusted registries; `pickle`-loaded checkpoints
  are arbitrary code execution (rules/01 §8) — use safetensors.
- System prompts, tool definitions, and guardrail configs are security-relevant
  code: version them, review changes, test with an adversarial suite
  (injection corpus + your own red-team cases) in CI; regression-test on every
  model/prompt upgrade since behavior shifts. **What the suite holds is part of the control:**
  - *Obfuscated variants* of every payload — Base64 and other encodings, scrambled-letter
    (typoglycemia) spellings, Best-of-N style case, spacing and phrasing mutations, forged
    reasoning lines (`Thought: ...`) — scored as a block rate over the whole corpus beside a
    false-refusal rate on benign inputs (rules/10 §5: a rate needs its denominator).
  - *Retrieval and memory boundaries*: cross-tenant queries return zero foreign chunks; a
    deleted or de-permissioned document is gone from retrieval, the vector store and the
    response cache; no cached answer crosses users or permission levels; altered source
    attribution fails verification.
  - *Release gate*: a change to tool policy, approval logic or credential scope with no new
    or changed test blocks the release, and a change that also weakens those tests gets a
    security reviewer.
  - *Evidence, kept per release*: the agent and model version, tool policy and retrieval
    config tested; the abuse cases run with expected and observed outcomes (approvals,
    denials, timeouts, circuit-breaker trips); any accepted residual risk and its
    compensating control.
  - *Freshness*: each newly published technique and each payload seen in an incident
    becomes a regression case.
  OWASP: AI Agent Security cheat sheet, LLM Prompt Injection Prevention cheat sheet, RAG
  Security cheat sheet.

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
  and apply rules/08 §2 executor-side authorization regardless of what the server claims.
  Remote MCP servers must require auth (the MCP spec's OAuth-based authorization,
  rev 2026-07-28: Client ID Metadata Documents over the now-deprecated Dynamic Client
  Registration, and clients MUST validate a present RFC 9207 `iss` response parameter against the recorded issuer) — unauthenticated internet-exposed MCP servers and
  trojaned MCP packages are recurring 2026 incident patterns (see NSA's CSI
  "Model Context Protocol (MCP): Security Design Considerations", May 2026).
  Agent config files the harness
  executes (hooks, settings, MCP server definitions checked into repos) are a
  code-execution surface: review them like CI config, never let the agent
  write them unapproved.
- **MCP server supply chain, past the pin** (the skill and plugin analogue is
  `sota-skill-security` rules/01):
  - *Install:* verify the server package's signature or checksum against the
    publisher's own source. Adding a local server takes an explicit consent
    prompt the user can cancel; a file in a cloned repo never adds one silently.
  - *Every call:* re-hash the tool's definition in a canonical JSON form (for
    example RFC 8785 JCS, so key order and whitespace neither hide nor fake a
    change) before each execution and compare it with the approved hash. A
    mismatch blocks the call and alerts; checking only at connect time misses a
    definition swapped between listing and calling.
  - *Names:* namespace tools per server (`server.tool`) and flag a tool whose
    name equals, or nearly equals, one exposed by another server.
  - *Scanning:* run an automated MCP scanner for poisoned descriptions and
    definition drift in CI and whenever a server updates.
  - *Advisories:* keep an inventory of approved AI components (models, MCP
    servers, plugins) and match it continuously against compromise advisories;
    a match quarantines the component (disable it, revoke its credentials)
    before triage, not after.
  OWASP: AISVS 10.1.1, AISVS 10.4.7, DSOMM, MCP Security cheat sheet, Secure
  Coding with AI cheat sheet.
- Named MCP/agent attack classes — use these names in findings (IDs: OWASP MCP
  Top 10 MCP03:2025 Tool Poisoning, which names no rug-pull or shadowing
  sub-techniques; MITRE ATLAS AML.T0115.002 Publish Poisoned AI Artifacts: AI Agent
  Tools and AML.T0110 AI Agent Tool Poisoning — AML.T0104 is gone since ATLAS 2026.07):
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
    (cost/latency DoS: OWASP LLM10:2025 Unbounded Consumption; ATLAS
    AML.T0034.001 Resource-Intensive Queries). Mitigate: never feed untrusted content as reasoning
    scaffold/thinking context, cap reasoning-token budgets per request,
    alert on token-consumption anomalies.
- Log prompts/completions for forensics, but apply rules/07 hygiene — context
  windows routinely contain PII and secrets; redact before storage, scope
  retention. **This rule is about your application logging its own calls. The
  developer's coding-agent transcript is a separate surface with a separate
  owner** — `~/.claude/projects/**/*.jsonl` and its equivalents hold whatever the
  harness loaded, including files it read on its own initiative:
  `sota-secrets-management` rules/04 §7.

## Audit checklist

- [ ] Are model artifacts checksum-pinned (safetensors, no pickle) and prompts/tool manifests version-controlled with adversarial regression tests?
- [ ] Are MCP tool definitions hash-pinned at approval with re-approval forced on any change (rug pull), and is the *full* description shown to the approver (tool poisoning)?
- [ ] Are high-privilege tools isolated from third-party servers in separate sessions/agents (tool shadowing), with tool listings treated as untrusted input before any invocation (line jumping)?
- [ ] Are MCP server packages signature/checksum-verified at install with a cancellable consent prompt, tool definitions re-hashed canonically before each call, tools namespaced per server with collisions flagged, an MCP scanner run, and the AI-component inventory matched against advisories (§1)? MEDIUM, HIGH for a server holding credentials. Probe for an unpinned server package: `grep -rnE '"args"[[:space:]]*:[[:space:]]*\[[[:space:]]*("-y",[[:space:]]*)?"(@[a-z0-9-]+/)?[a-z0-9_][a-z0-9._-]*(@latest)?"' .`
- [ ] **Does the adversarial suite cover obfuscated variants (scored with a false-refusal denominator), cross-tenant, stale-permission, cache and deletion cases, and does a tool-policy, approval or credential-scope change without tests block release, with evidence retained (§1)?** MEDIUM, HIGH for an agent holding write or payment tools. Injection test files with no obfuscated variant: `grep -rliE 'prompt.?injection|jailbreak|ignore (all )?previous instructions' --include='*test*' . | while IFS= read -r f; do grep -qiE 'base64|b64|typoglyc|best.of.n|thought:' "$f" || echo "$f"; done`
