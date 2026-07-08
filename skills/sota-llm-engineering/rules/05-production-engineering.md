# Rules 05 — Production Engineering

The model is a remote dependency with variable latency, hard rate limits,
per-token billing, scheduled deprecations, and behavior that changes between
versions. Engineer around it like you would any unreliable, expensive,
versioned upstream — plus tracing rich enough to debug nondeterminism.

## 1. Model selection & routing

**Select per task on your eval (rules/01), not per vibe or leaderboard.**
Providers ship capability tiers with ~5–25× price spreads between frontier
and small models (illustrative, verified July 2026: Anthropic frontier tier
$10/$50 per MTok, Opus tier $5/$25, Sonnet tier $2–3/$10–15 introductory→
standard, Haiku 4.5 $1/$5; OpenAI and Google tier similarly — re-verify
prices before encoding them). Tokenizers also change between model
generations — the same text can tokenize to ~30% more tokens on a newer
model (per Anthropic's pricing page for its 2026 generation) — so cost
estimates built from a price table must re-baseline token counts per model,
not just prices. The pattern, stable across providers: **frontier tier**
for hard reasoning/agentic work, **mid tier** for most production volume,
**small/fast tier** for classification, routing, extraction, and judges.

- **Right-size empirically:** run the eval suite on the candidate tier below
  your current one; if scores hold, take the savings. Most production
  traffic is over-modeled.
- **Routing:** route by *route/feature* first (each endpoint pins its
  eval-justified model in config); dynamic per-request difficulty routing
  (cheap classifier → escalate hard cases) only when volume justifies its
  own eval + maintenance.
- **Pin model IDs; keep them in config, never inline.** One model registry
  per codebase mapping `task → {model, params, prompt_version}`. Aliases
  that auto-track "latest" are for dev only (§7).
- **Provider abstraction caution:** a thin internal gateway (one module that
  owns auth, retries, tracing, budgets) is mandatory; a *lowest-common-
  denominator* abstraction layer that hides provider-native capabilities
  (prompt caching, structured outputs, server-side tools, batch) is a trap —
  you pay the abstraction tax and lose the features that dominate cost and
  quality. Abstract the operational envelope, not the request semantics.
  Heavy frameworks earn inclusion only if you'd accept them as a normal
  dependency: pin versions, read the code you ship.
- **Fallback chains:** for each route, a configured fallback (usually same
  provider's adjacent tier, or a second provider if you're dual-homed) used
  on outage/overload — switched by the gateway, recorded in traces, and
  *eval-tested in advance* so degraded ≠ broken. Cross-provider fallback
  requires prompt/param compatibility testing per provider — don't assume.

## 2. Rate limits, retries, and errors

Verified error semantics (Anthropic, June 2026; OpenAI/Gemini analogous):
`429 rate_limit_error` (RPM/TPM/TPD exceeded — read `retry-after` and
`x-ratelimit-*` headers), `500 api_error`, `529 overloaded_error` (capacity —
retryable), `400` family (NOT retryable — fix the request), `401/403`
(credentials/permissions — page, don't retry).

- **Retry policy:** exponential backoff with full jitter, honoring
  `retry-after` when present; retry 429/500/529 and transport timeouts;
  never retry 4xx (except 408/429); cap attempts (3–5) and total elapsed
  time. Official SDKs do this out of the box (e.g. `max_retries` defaults) —
  prefer SDK retry config over hand-rolled loops; hand-rolled string-matching
  on error messages instead of typed exception classes is a Medium finding.
- **Idempotency:** any retried call that triggers side effects (via tools or
  downstream writes) needs idempotency keys (rules/04 §2).
- **Client-side throttling:** track your TPM/RPM budget and queue/shed
  *before* the provider 429s you; spread batch-ish traffic; per-tenant
  fairness limits so one tenant can't starve the org's quota.
- **Streaming requests need stream-aware timeouts** (time-to-first-token and
  inter-chunk idle timeouts), not one giant request timeout. Long
  non-streaming generations will hit HTTP timeouts — stream anything that
  can exceed ~1 minute.

## 3. Latency engineering

Order of leverage:

1. **Stream by default** for user-facing text — perceived latency is
   time-to-first-token; stream tool-use/agent progress too (status events),
   not just final text.
2. **Prompt caching** (rules/02 §5) — cached prefixes cut both cost and
   TTFT substantially on repeated-prefix traffic; verify hit rates in
   telemetry. Pre-warm caches before traffic bursts where the provider
   supports it.
3. **Parallelize independent calls** — fan out subtasks/retrieval/judges
   concurrently; an orchestrator awaiting sequential calls that share no
   data dependency is free latency.
4. **Right-size the model** — small-tier models are several× faster; route
   latency-critical paths accordingly (§1).
5. **Bound the output** — output tokens dominate generation time; tight
   `max_tokens` + concise-output instructions on latency-sensitive routes.
6. **Speculative/hedged calls** — for strict SLOs, race the same request on
   a faster tier or fire a duplicate after a p95 delay and take the first
   finisher; costs double tokens on the hedged fraction — budget it
   explicitly and only on routes that justify it.
7. Semantic/response caching (serve cached answers to near-duplicate
   queries) helps FAQ-shaped traffic; mind staleness + per-user data leaks
   in the cache key.

## 4. Cost engineering

Cost is a feature requirement with a number, not a postmortem surprise.

- **Budget per feature:** target cost/request and cost/day per route, wired
  into the eval gate (rules/01 §5) and alerting (§5). Estimate as
  `(input_tokens × in_price + output_tokens × out_price)` from the registry's
  price table — and re-verify prices on provider pages when they matter.
- **The big four levers**, in typical order of payoff:
  1. **Prompt caching** — ~90% off cached input on repeated prefixes;
  2. **Batch APIs** — 50% off for async workloads (verified: Anthropic
     Message Batches −50%, ≤24h turnaround; OpenAI Batch comparable). Any
     offline/nightly/bulk job paying real-time prices is a finding (Low–
     Medium by volume);
  3. **Model right-sizing** (§1);
  4. **Context diet** — token budgets per category (rules/02 §2), bounded
     tool outputs (rules/04 §2), compaction (rules/04 §5), few-shot pruning.
- **Per-unit attribution:** tag every call's cost to feature/tenant/user.
  "The AI bill doubled" must decompose in one query to *which route, which
  tenant, which prompt version*.
- Watch the multipliers: thinking/reasoning tokens bill as output; agent
  loops multiply everything (rules/04 §3 budgets are the cap); retries and
  repair loops compound — trace them.

## 5. Observability

If you can't replay it, you can't debug it. **Trace every call** through the
gateway — no direct provider SDK calls scattered in handlers.

Minimum span fields per LLM call:

```
trace_id / parent_span (ties multi-step pipelines + agent loops together)
model_id (exact version), provider, params (temp/effort/max_tokens)
prompt_version, template_id, feature/route, tenant/user (pseudonymous)
rendered prompt + completion (redacted per rules/06 §5; sampled if volume forces)
input_tokens, output_tokens, cache_read/write_tokens, reasoning_tokens
latency: TTFT + total; stop_reason; error class; retry count; fallback used
cost_usd (computed); tool calls with args/results (size-capped)
eval link: run_id when the trace is sampled into eval sets (rules/01 §7)
```

Use OTel GenAI semantic conventions / an LLM-observability platform
(LangSmith/Braintrust/Arize-class or self-hosted) rather than inventing a
schema — but any structured store beats none.

**Dashboards + alerts** per route: p50/p95 TTFT & total latency, error and
429 rates, cost/day vs budget, cache hit rate, token percentiles,
refusal/truncation rates, online eval scores & user-feedback rates
(rules/01 §4). Alert on: cost anomaly (>2× daily baseline), 429/5xx spikes,
cache hit-rate collapse, eval-score drops, spike in `stop_reason=max_tokens`
(silent truncation in prod).

Logging prompts/completions is logging user data: redaction, retention, and
access control per rules/06 §5 and sota-privacy-compliance.

## 6. Graceful degradation

Decide per route, in advance, what happens when the model is slow, down,
overloaded, refusing, or over budget:

- **Degrade in steps:** primary model → fallback model (§1) → cached/
  semantic-cache answer → non-LLM fallback (rule-based, search results,
  template) → honest unavailability ("AI assist is unavailable; here's the
  manual path"). Never an infinite spinner; never a fabricated answer to
  mask an outage.
- **Circuit breakers** around each provider: trip on error-rate/latency
  thresholds, route to the degradation path, half-open probe to recover —
  protects your latency budget and stops retry storms during provider
  incidents.
- **Refusals are a normal outcome** (current frontier models return explicit
  refusal stop-reasons): handle as a product path (rephrase, route to a
  fallback model where appropriate, or surface honestly) — not as a 500.
- **Load shedding:** under quota pressure, shed by priority (background
  jobs → batch queue; interactive traffic first) rather than uniformly
  failing.

## 7. Versioning & rollout

Everything that changes behavior is a versioned artifact: model ID, prompt,
params, retrieval config, tool schemas, judge prompts. A change to any of
them follows the same pipeline:

1. **Offline evals pass** (rules/01 §5) against the candidate.
2. **Shadow** (where feasible): run candidate alongside production on
   sampled live traffic, compare offline — zero user exposure; pairwise
   judge old-vs-new (rules/01 §2).
3. **Canary/A-B:** small % of traffic, watch online metrics + sampled
   judges; expand on green.
4. **Rollback is config:** previous model+prompt version stays deployable
   instantly; traces carry versions so incidents attribute cleanly.

- **Pinning vs auto-upgrade:** production pins exact model versions. Silent
  auto-upgrade (floating "latest" aliases) ships an uncontrolled behavior
  change — Critical on consequential routes without a regression gate.
  Providers deprecate models on schedules (months, not years): track
  deprecation announcements, run evals against the successor *early*, and
  migrate deliberately — a forced same-week migration is the failure mode
  pinning must not become. Budget one eval-gated model migration per route
  per ~6 months.
- Model migrations are also **prompt** migrations: newer frontier models
  follow instructions more literally — over-aggressive legacy scaffolding
  ("CRITICAL: ALWAYS…") over-triggers; re-tune per provider migration guides
  and your evals (rules/02 §7). Caches are per-model: expect a cold-cache
  cost/latency blip at cutover.

## Audit checklist

- [ ] Each route's model chosen by eval evidence; tier-below test performed;
      models/params/prompts in a config registry, none inline; price/limit
      claims in code or docs re-verified, not folklore; token counts
      re-baselined when the model (and its tokenizer) generation changes.
- [ ] Single gateway module owns all provider calls (auth, retries, tracing,
      budgets); no scattered direct SDK calls; abstraction does not mask
      provider-native caching/structured-output/batch features.
- [ ] Retries: jittered exponential backoff, `retry-after` honored, 4xx not
      retried, attempt+elapsed caps, typed error classes; client-side
      throttling and per-tenant fairness before provider 429s.
- [ ] Streaming on user-facing and long-running generations; TTFT and idle
      timeouts; no >1-minute non-streaming calls.
- [ ] Latency levers applied in order (stream, cache, parallelize,
      right-size, bound output) before exotic ones; hedged calls budgeted.
- [ ] Cost: per-route budget + alerting; caching hit-rate verified; offline
      workloads on batch API (−50%); cost attribution to
      feature/tenant/prompt-version queryable.
- [ ] Every call traced with the §5 minimum fields; agent steps share a
      trace; dashboards + the §5 alert set exist; prompt/completion logs
      redacted and retention-controlled.
- [ ] Per-route degradation ladder defined and tested (fallback model →
      cache → non-LLM → honest unavailability); circuit breakers on
      providers; refusals handled as product paths.
- [ ] Rollouts: eval gate → shadow/canary → expand; instant config rollback;
      no floating "latest" in production; deprecation calendar tracked with
      early successor evals; migration includes prompt re-tuning.
