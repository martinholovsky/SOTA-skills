# evals/ — efficacy regression harness (prototype)

Freshness (see [../docs/MAINTENANCE.md](../docs/MAINTENANCE.md)) keeps the
library's claims *true*. This harness asks a different question: does loading a
skill actually change agent output for the better? It turns "the skills work"
from an assertion into a number you can re-run.

**This is a prototype and is deliberately not in CI.** An LLM eval is
non-deterministic and needs an agent + network, so it can't be a blocking gate.
You run an agent over the cases yourself and score the result here. The value
is a repeatable baseline: run it before and after a large content change and
watch the score, and grow the golden sets as coverage warrants (2026-07-10
audit STRAT-HIGH-2).

## Cases

- `cases/router.jsonl` — routing: a plain prompt → the skills that must load.
  Tests the router's task→skill mapping.
- `cases/audit.jsonl` — audit: a deliberately vulnerable snippet → the finding
  category an audit must flag. Tests that the security skills catch the obvious.

Each line is one case with an `id` and an `expect` list (see `score.py` header
for the schema). Add cases freely; keep `expect` to unambiguous must-haves.

## How to run

1. **Baseline (no skills):** in a session with the SOTA skills NOT loaded, give
   the agent each case's `prompt` (routing) or ask it to audit each `snippet`
   (audit). Record what it did in a predictions JSON:

   ```json
   { "r01": ["sota-api-design", "sota-code-security"], "a01": ["sql-injection"] }
   ```
   (routing → skills it loaded; audit → finding categories it reported.)

2. **With skills:** repeat in a session with the SOTA skills loaded (via the
   plugin or `~/.claude/skills`). Record a second predictions JSON.

3. **Score both:**

   ```sh
   python3 evals/score.py evals/cases/router.jsonl predictions-with.json
   python3 evals/score.py evals/cases/audit.jsonl  predictions-with.json
   ```

   The script prints per-case recall (did it load/flag every expected item?)
   and precision (FYI), then the means. It exits non-zero if any case has a
   miss. Compare the *with-skills* score to the *baseline* — the delta is the
   library's measured lift.

## Interpreting

- **Recall is the load-bearing metric.** A miss (recall < 1.0) is a real gap:
  either the skill isn't being routed/applied, or its guidance doesn't cover the
  case. Investigate — it's exactly the kind of blind spot the harness exists to
  surface.
- **Precision is informational** for routing (loading an extra relevant skill
  isn't wrong); for audit, extras are usually fine too (more true findings).
- These golden sets are small and the `expect` sets are judgment calls, so
  treat the score as a *regression signal*, not an absolute grade. The point is
  the delta over time, not the third decimal place.

## Recorded runs

`results/<date>/` holds the raw per-arm predictions (+ rationales for the
logged run) so scores are re-scorable and comparable over time. Writeup:
[`results/2026-07-10/BASELINE.md`](results/2026-07-10/BASELINE.md) — two runs, a
replicated **~+0.10 routing recall lift** attributable to the router's
cross-cutting rules, a **control-validity analysis** (the "without-library" arm
is a routing-aware control, not truly library-free — so the number is a lower
bound), and the finding that the audit cases are too easy to discriminate yet
(both arms 13/13). A clean library-vs-nothing run needs an isolated environment
(no sota `CLAUDE.md`, no registered skills).

## Extending

Add a new case kind by giving each case an `id` and an `expect` list — `score.py`
is generic over the expected/predicted set comparison. Highest-value next set
(from the baseline): **harder audit cases** — multi-vuln snippets and subtler
authz/business-logic cases where a bare model misses what a skill-guided audit
catches. Also: contract tests the API skill should demand, migration-safety
cases for the DB skill.
