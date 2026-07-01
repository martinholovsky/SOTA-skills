# Rules 04 — Agents & Tool Use

An agent is a loop where the model decides what happens next. That autonomy is
the value and the entire risk surface: cost, latency, and failure modes all
become open-ended unless you bound them in the harness. The harness — not the
prompt — owns budgets, stopping, authorization, and observability.

Security split: tool-call authorization, prompt-injection-resistant design,
and the lethal trifecta are sota-code-security rules/08; executing agent code
in isolation is sota-sandboxing rules/05. This file owns build quality.

## 1. Workflow first, agent when earned

**Deterministic orchestration first.** If you can draw the flowchart, write
the flowchart — code-orchestrated steps with LLM calls at the nodes
(classify → route → extract → render). Workflows are cheaper, faster,
debuggable, and evaluable per-step. The escalation ladder (each step only
when the eval shows the previous failing):

1. Single call → 2. structured output → 3. workflow (chain/router/
   parallel-fan-out in code) → 4. single agent with tools → 5. multi-agent.

Gate for tiers 4–5 — all four must hold, otherwise stay at 3:

- **Complexity:** the path genuinely can't be enumerated in advance.
- **Value:** the outcome justifies 10–100× the tokens of a workflow.
- **Viability:** current models demonstrably handle this task class (eval).
- **Cost of error:** failures are detectable and recoverable (tests, review,
  rollback) — or gated by a human (§6).

Audit heuristic: an "agent" whose traces show the same 3 tools in the same
order every run is a workflow paying agent overhead — refactor (Medium).

## 2. Tool design

Tools are the API you publish to a very literal consumer. Most agent failures
are tool-design failures, not model failures.

```json
// GOOD
{
  "name": "search_orders",
  "description": "Search the customer's own orders by status and date range. Call this when the user asks about order status, history, or delivery dates. Returns at most `limit` orders, newest first. Returns an empty list when nothing matches — that means the customer has no such orders; do not retry with the same arguments.",
  "input_schema": {
    "type": "object",
    "properties": {
      "status": {"type": "string", "enum": ["pending", "shipped", "delivered", "cancelled"]},
      "placed_after": {"type": "string", "format": "date", "description": "ISO date, e.g. 2026-01-31"},
      "limit": {"type": "integer", "description": "1-20, default 5"}
    },
    "required": ["status"],
    "additionalProperties": false
  }
}

// BAD
{ "name": "query", "description": "Run a query",
  "input_schema": {"type": "object", "properties": {"q": {"type": "string"}}} }
```

- **Descriptions say *when* to call, not just what it does.** Current frontier
  models reach for tools conservatively; trigger conditions in the
  description ("call this when…") measurably lift correct-call rate
  (verified provider guidance, 2026). Also state what the output means and
  what NOT to do (no-retry conditions, limits).
- **Narrow scope:** `search_orders(customer_scoped)` over `run_sql(string)`.
  Broad tools (bash, SQL, generic HTTP) give leverage but make gating,
  auditing, and parallelizing impossible — promote an action to a dedicated
  tool when you need to gate it (§6), validate it, render it, or mark it
  parallel-safe. Server-side scoping (tenant from session, not from model
  args) is the security half — sota-code-security rules/08.
- **Strict schemas:** enums, formats, `additionalProperties: false`, examples
  in descriptions; use provider strict/validated tool modes where available.
  Validate arguments in code anyway — schema conformance ≠ semantic validity.
- **Idempotency for anything retried:** loops re-execute on transient
  failure. Mutating tools take an idempotency key (derive from tool-call ID)
  or are safe to re-run; a non-idempotent `send_email`/`charge_card` inside
  a retrying loop is a Critical finding.
- **Errors a model can act on:** return structured, instructive failures —
  `"date must be ISO format (2026-01-31), got '1/31/26'"` not `"Error 422"`
  or a stack trace. Distinguish retryable / fix-your-args / give-up in the
  payload. Empty results return an explicit "no results, don't retry same
  args" message, not `[]` alone.
- **Bound tool output size.** A tool returning 200KB of JSON floods the
  context (rules/02 §2): paginate, summarize, or write-to-file-and-reference.
  Token-cap every tool result in the harness.
- **Few, distinct tools.** Overlapping tools ("search_docs" vs "find_docs")
  cause dithering. Prefer one well-described tool per capability; for large
  tool libraries use provider tool-search/dynamic-loading rather than 80
  schemas in every prompt (cache-aware: append, don't swap — rules/02 §5).

## 3. The loop: stopping conditions and budgets

Every agent loop has, in the harness, ALL of:

```python
class AgentBudget:
    max_iterations: int          # e.g. 15 — hard stop on tool-call rounds
    max_total_tokens: int        # input+output across the whole run
    max_cost_usd: float          # computed from per-model price table
    wall_clock_timeout_s: int    # end-to-end deadline
    max_consecutive_errors: int  # e.g. 3 — same tool failing → abort
    max_repeat_calls: int        # identical (tool, args) → loop detection
```

- **On budget exhaustion, fail loudly and usefully:** persist the partial
  trace, summarize state ("ran out of budget after X; completed A, B;
  remaining C"), surface to user/queue. Silent truncation that presents a
  partial result as complete is a High finding.
- **Loop detection:** identical tool+args repeated, or no state change across
  N iterations → inject a "you are repeating yourself; change approach or
  report blockage" turn once, then abort.
- **Tell the model its budget** where the provider supports it (task-budget
  style parameters) or via prompt ("you have ~N tool calls; prioritize") —
  models wrap up gracefully when they can see the countdown; the harness
  limit stays authoritative.
- **Check `stop_reason` every turn** and handle each value explicitly:
  tool-use → execute; end-of-turn → done; max-tokens → truncated (raise cap
  or split, don't parse the stump); refusal → its own path; provider
  pause/continue signals → resume per provider docs. An unhandled
  `stop_reason` is an infinite-loop or data-corruption bug waiting.
- Long runs on current frontier models can legitimately take minutes per
  request — plan streaming/async/progress UX rather than raising HTTP
  timeouts forever (rules/05 §3).

## 4. Human-in-the-loop gates

Consequential actions get code-enforced approval gates — the model proposes,
the harness pauses, a human (or policy engine) approves:

- **Always gate:** irreversible/destructive ops (delete, send-external,
  deploy), money movement, anything touching production data or third
  parties on the user's behalf.
- **Gate shape:** the loop *suspends* on a pending approval (durable state,
  resumable), renders the exact proposed action + args to the approver, and
  resumes with approve/deny + reason fed back to the model (deny reason lets
  it adjust). Provider permission policies / "always ask" tool modes
  implement this server-side where available.
- **Approval is per-action, not per-session.** A blanket "yes to everything
  for an hour" is not a gate. Batch *similar* low-risk actions for one
  review where volume demands it.
- Authorization (can this principal do this at all) is enforced in code
  regardless of approval UX — sota-code-security rules/08; the prompt is never the boundary.

## 5. Context management across turns

Long-running agents die of context bloat: old tool results dominate the
window, costs grow quadratically with history, and quality drops.

- **Within a session:** prune stale tool results (context editing) and/or
  summarize-compact earlier history once past a threshold. Prefer
  provider-native compaction where offered (server-side summarization blocks
  you must echo back — verified Anthropic beta, 2026); else implement
  compaction yourself: summarize all but the last N turns, keep the system
  prompt + task statement + open commitments verbatim. Compaction is lossy —
  eval it (does the agent still complete tasks post-compaction?).
- **Across sessions: memory.** File/store-based memory the agent reads and
  writes (notes, learned preferences, prior decisions). Treat memory as a
  product surface: schema/format guidance in the prompt, size limits,
  expiry/decay, user-visible and erasable where it holds user data
  (rules/06 §5), and protected from poisoning via untrusted content
  (sota-code-security rules/08). Current frontier models measurably improve with an explicit
  memory file + instructions on when to consult/update it — but only if you
  tell them when.
- **Don't resend what you can reference:** large artifacts go to files/object
  storage with a read tool, not pasted into every turn.
- Cache-aware: history is append-only with a stable prefix (rules/02 §5);
  compaction events are natural cache-rebuild points — don't also swap tools
  or models there.

## 6. MCP integration

MCP (Model Context Protocol) is the de-facto open standard for tool/context
servers. **Verified June 2026:** current spec revision **2025-11-25**; the
next revision is at release-candidate stage dated **2026-07-28** and includes
breaking changes (stateless protocol core, Extensions framework, Tasks for
long-running work, MCP Apps, OAuth-aligned authorization hardening, formal
deprecation policy). Engineering consequences:

- **Pin the protocol revision** you build against (2025-11-25 today); track
  the 2026-07-28 RC and plan migration — don't hand-roll protocol handling;
  use maintained official SDKs that absorb revision churn.
- **Treat third-party MCP servers as untrusted dependencies:** version-pin,
  review tool descriptions before exposing them to your model (description
  text is prompt input — injection surface, sota-code-security rules/08), and apply your own
  allowlist/gating layer over their tools rather than mounting everything.
- **Your own tools don't have to be MCP.** In-process tool definitions are
  simpler, faster, and easier to test; MCP earns its overhead when you need
  cross-app reuse, third-party integration, or a marketplace of servers.
- The same tool-design rules (§2) apply verbatim to MCP tool definitions —
  most public MCP servers ship vague descriptions and unbounded outputs;
  wrap or fix them before production.
- Credentials for MCP servers belong in a secrets/vault layer, never in
  prompts or agent-visible config (sota-secrets-management). Request the
  **narrowest scope per server** (`mail.readonly`, not `mail.full`) and prefer
  short-lived tokens over long-lived PATs.
- **When you *operate* an MCP server (DN self-hosts them), harden the server,
  not just the client** (OWASP MCP Security): bind local HTTP/SSE transports to
  `127.0.0.1`, not `0.0.0.0`; **validate the `Origin`/`Host` header on every
  request** to block DNS-rebinding from a browser tab; use non-guessable session
  IDs bound to user context (`<user_id>:<session_id>`), never a bare sequence;
  put remote servers behind TLS with verified server identity and auth. An
  unauthenticated MCP server on `0.0.0.0` is an open tool-execution endpoint.

## 7. Multi-agent: patterns and their real costs

Multi-agent is tier 5 for a reason. Costs that proposals systematically
ignore: token multiplication (each agent re-carries context — orchestrator+
subagent systems commonly burn ~10–15× a single chat's tokens), inter-agent
information loss (agents communicate by lossy summary), debugging across N
interleaved traces, and eval complexity (judge trajectories and handoffs,
not just final output).

Patterns that earn their cost:

- **Orchestrator → parallel subagents** for *independent* subtasks (read 30
  files, research 5 competitors): subagents fan out with clean, scoped
  contexts, return summaries; orchestrator keeps the main thread. This is
  the dominant legitimate pattern — it's about context isolation and
  parallelism, not role-play.
- **Generator → critic/verifier** with a *fresh-context* verifier: separate
  context genuinely de-anchors review (a self-critiquing single agent
  doesn't). Cap revision rounds.
- **Cheap-model subagents under an expensive orchestrator** for mechanical
  legwork (rules/05 §1 routing applies per-agent).

Anti-patterns (findings): role-play committees ("PM-agent talks to
Dev-agent") replicating org charts instead of isolating contexts; depth>1
delegation trees nobody can trace; agents sharing no state but expected to
agree; multi-agent where one good prompt + workflow scores the same on the
eval. Subagent results are inputs to the orchestrator — validate them like
tool output; budgets (§3) apply **per-agent and per-tree** (a parent's
budget bounds the sum of its children).

## Audit checklist

- [ ] Escalation ladder respected: no agent where a workflow's eval scores
      match; no multi-agent without measured single-agent failure; the four
      §1 gates documented for every agent in the system.
- [ ] Every tool: when-to-call description, strict schema
      (`additionalProperties: false`, enums), bounded output size,
      structured actionable errors, explicit empty-result semantics.
- [ ] Mutating tools idempotent or idempotency-keyed; no non-idempotent
      side effects inside a retrying loop.
- [ ] Harness enforces ALL budget dimensions (iterations, tokens, cost,
      wall-clock, consecutive-error, repeat-call) with loud, state-
      preserving failure — grep every loop for its bound.
- [ ] `stop_reason` exhaustively handled; truncated output never parsed as
      complete.
- [ ] Consequential actions behind per-action human/policy gates that
      suspend durably and feed deny-reasons back; authorization additionally
      code-enforced (sota-code-security rules/08).
- [ ] Context management present for long sessions: pruning/compaction with
      eval coverage, memory with limits/expiry/erasability, artifacts by
      reference not by paste.
- [ ] MCP: protocol revision pinned (2025-11-25 era; 2026-07-28 RC migration
      tracked), official SDKs used, third-party servers version-pinned with
      reviewed descriptions and an own gating layer; MCP credentials in a
      vault.
- [ ] Multi-agent: pattern is context-isolation/parallelism or fresh-context
      verification — not role-play; token multiplication estimated and
      accepted; per-tree budgets; subagent output validated; traces
      reconstructable per agent.
