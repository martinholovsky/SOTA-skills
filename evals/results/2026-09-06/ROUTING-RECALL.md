# Routing recall and precision over a gold set — and the reframing it refutes

**2026-09-06** · `run-routing-recall.py` · `anthropic/claude-sonnet-4.6`, 10 cases,
1 sample, temp 0 · artifact `routing-recall.json`

## Why this was built

Two external assessments (2026-09-06) said the library was missing skills — MCP security,
agent engineering, browser verification. Checking the tree showed the content exists:
MCP tool poisoning / rug pulls / shadowing / MCP03:2025 live in `sota-code-security`
rules/08, `sota-sandboxing` rules/05 **and** `sota-threat-modeling` rules/03.

So I proposed a reframing: **not missing, but unreachable** — knowledge fragmented across
skills that routing cannot assemble. The second assessment agreed and built on it,
proposing `Effective Coverage = Content Coverage × Routing Recall`.

**That reframing is not supported by measurement.**

## Result

| | recall | precision |
|---|---|---|
| **All 10 cases** | **0.975** | **0.569** |
| Gold set transcribed from the router's own composition rules (n=5) | 0.95 | **0.45** |
| Gold set derived — the three contested "missing skill" shapes (n=3) | **1.00** | 0.48 |
| Single-skill controls (n=2) | 1.00 | **1.00** |

**Under-selected: 1 of 10 cases. Over-selected: 8 of 10.**

The three shapes both assessments called missing skills route at **recall 1.00**:

```
mcp_server_audit           recall=1.00   (code-security + sandboxing + threat-modeling)
agent_subagent_delegation  recall=1.00   (llm-engineering + sandboxing)
browser_verification       recall=1.00   (testing + frontend-design)
```

The knowledge is not unreachable. It is found, every time, and then buried in company.

## What is actually wrong

**Over-selection.** Against gold sets *transcribed from the router's own prose*, precision
is **0.45** — the model loads roughly twice what the router says to load. The single-skill
controls score 1.00/1.00, so this is not a model that always picks many things: it is
selective when the task is narrow and expansive when the task sounds broad.

Most-frequent over-selections: `sota-threat-modeling` (5 cases), `sota-identity-access`
(3), `sota-code-security` (3).

## Caveats, stated before anyone quotes the number

- **n=10, one sample, temp 0.** This repo's own measured noise floor is ±0.03 at n=1, and
  temp 0 is not deterministic here. Recall 0.975 vs 1.0 is inside noise; precision 0.569
  vs 1.0 is not.
- **Precision is only as good as the gold set.** The commonest "extra" is
  `sota-threat-modeling`, and the router's rule 2 says security tasks *do* usually need it.
  On the five router-sourced cases the gold set is transcribed rather than judged, which is
  why that subgroup is the one to quote; on the derived cases my judgement is in play and
  the true precision is likely higher than 0.48.
- **The prompt asks for "no more and no fewer".** Over-selection here is against an
  explicit instruction, which makes it a stronger finding — and also means it does not
  directly predict what an auto-loader does with no such instruction.
- **Cost, not quality.** ROADMAP 25 added 400 lines of competing guidance to a
  with-library arm and measured **−0.01**. So the demonstrated cost of loading too much is
  tokens, latency and money — *not*, on current evidence, answer quality. An optimisation
  framed as `argmax Q − λC` would be optimising a term this repo has already measured near
  zero on the Q axis.

## What this changes

1. **Do not build `sota-mcp-security`, `sota-agent-engineering`, or a browser-verification
   skill on reachability grounds.** The reachability premise is refuted for all three. If
   they are ever built it must be for a different, stated reason.
2. **`Effective Coverage = Content × Routing Recall` is the right decomposition and the
   wrong diagnosis here** — the second factor is ~0.98. The interesting term is precision,
   which that formulation omits.
3. **The open question is whether over-selection costs anything.** Recall is solved;
   quality-under-padding measured −0.01; so the live question is token/latency cost and
   conflict rate. Conflict needs a judge and has a real seed incident (a liveness-probe
   rule against a no-`await` async rule, which is why the router carries a
   conflict-resolution clause).

## The methodological note

This is the third time in one session that a structural intuition dissolved on
measurement — after item 12's file-count trigger and the router's 500-line cap. In this
case the intuition was **mine**, proposed to correct someone else's, and adopted by them
before either of us had a number. The instrument took under an hour to build and cost ten
API calls.
