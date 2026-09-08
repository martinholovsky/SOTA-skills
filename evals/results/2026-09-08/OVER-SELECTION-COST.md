# What over-selection actually costs — ROADMAP item 38

**Date:** 2026-09-08 · **Method:** `POST /v1/messages/count_tokens`, model
`claude-sonnet-5` · **Input:** the per-case `extra` sets in
[`../2026-09-06/routing-recall.json`](../2026-09-06/routing-recall.json) ·
**Samples:** n/a — this is arithmetic over an existing measured run, not a new eval ·
**Files counted:** 22 distinct `SKILL.md`

Item 38 asked one question with a pre-registered decision rule: *"If it is a few thousand
tokens per task, it is a router note, not a project."*

## Result

Routing recall reads 0.975 while precision reads 0.569 — the model loads roughly twice what
the router says to. Priced in tokens, counting each over-selected skill's `SKILL.md` (the
marginal load; `rules/*` are opened on demand, so this is the **floor**):

| case | gold skills | extra | gold tok | extra tok | overhead |
|---|---:|---:|---:|---:|---:|
| `k8s_cluster_audit` | 3 | 4 | 13,417 | 20,071 | 150% |
| `agent_subagent_delegation` | 2 | 4 | 7,900 | 18,261 | **231%** |
| `mcp_server_audit` | 3 | 4 | 14,511 | 18,313 | 126% |
| `untrusted_feed_ingest` | 2 | 4 | 11,001 | 15,665 | 142% |
| `evidence_shell_script` | 2 | 3 | 11,151 | 12,389 | 111% |
| `next_security_review` | 4 | 2 | 15,323 | 11,288 | 74% |
| `crypto_key_rotation` | 2 | 2 | 12,289 | 8,773 | 71% |
| `browser_verification` | 2 | 1 | 7,184 | 2,615 | 36% |
| `single_go_error_control` | 1 | 0 | 3,282 | 0 | **0%** |
| `single_ux_copy_control` | 1 | 0 | 2,615 | 0 | **0%** |

- **Mean 10,738 extra tokens per task**; median 11,838; max 20,071.
- Pooled: **98,673 gold vs 107,375 over-selected — +109%** on the `SKILL.md` load.

## The decision the item asked for

**It is not "a few thousand tokens".** At ~10.7k per task it is an order of magnitude above
the threshold item 38 registered, so by its own rule this is **not merely a router note**.

But the direction matters and the evidence already exists: a padded context measured
**−0.01** (ROADMAP 25) and **−0.03** (item 32). So over-selection is a **token, latency and
money** cost, **not** a measured quality cost. The honest framing is economic: every
multi-domain task pays roughly double the intended `SKILL.md` load, for no measured
degradation and no measured benefit.

**Both single-skill control cases over-select exactly zero.** The cost is concentrated in
multi-domain tasks — which is where the router is doing the most work and where a
tie-breaking rule would have the most to bite on.

## Limits, stated

- **This is a floor, not the bill.** It counts `SKILL.md` only. An over-selected skill whose
  `rules/*` also get opened costs multiples of this.
- It reuses one measured routing run (2026-09-06, 10 cases). It is arithmetic over that run,
  so it inherits its sample and its gold sets — including that some gold sets are `derived`
  rather than transcribed from the router.
- **No money figure**, deliberately: converting to currency needs current per-token pricing,
  which is exactly the kind of fast-moving fact this library refuses to hardcode. Multiply
  10.7k by your own rate.
