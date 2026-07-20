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

- `cases/router.jsonl` (20) — routing: a plain prompt → the skills that must
  load. Tests the router's task→skill mapping.
- `cases/audit.jsonl` (13) — audit: a deliberately vulnerable snippet → the
  finding category an audit must flag. Tests that the security skills catch the
  obvious. `cases/audit-hard.jsonl` (14) is the harder set — multi-vuln + subtle
  (IDOR/SSRF/TOCTOU/ReDoS); it *still* saturates at 1.00 both arms (see below).
- `cases/repo-audit.jsonl` (8) + `cases/repo-audit/orderdesk/` — a 15-file
  FastAPI app with 8 defects that are **invisible in any single file** (an authz
  check one layer assumes another enforces, a taint that crosses modules, an
  invariant one file documents and another violates, an insecure default trusted
  elsewhere). Scored by `run-repo-audit.py`. Result: **+0.00** on sonnet-4.6 and
  opus-4.8 — when the whole repo fits in one context, a capable model reads
  across files and catches cross-file defects unaided
  ([`results/2026-07-13/REPO-AUDIT.md`](results/2026-07-13/REPO-AUDIT.md)). The
  real audit-lift frontier is a repo too large to hold at once (agentic,
  selective reading), logged there as the open follow-up.
- `cases/completeness.jsonl` (7) — a minimal "build X" task → a rubric of
  universal best practices a blind judge scores the generated code against. The
  breadth run adds `completeness-{go,iac,frontend,frontend-complex}.jsonl` (3 each)
  for the five-domain baseline analysis.
- `cases/freshness.jsonl` (32) — a current-2026 fact question → the token a
  correct answer must contain. Every fact is present in the library and was
  primary-source-verified.
- `cases/silent-failure.jsonl` (69) — a control that **looks enabled and does
  nothing** (inert scanner, fail-open policy, ruleset that loads zero rules,
  truncation before inspection, a test that passes against a no-op'd body …) →
  the mechanism by which it is inert. 41 positives + **8 negative controls** whose
  correct answer is "not silent" (the control fails loudly), so an arm that cries
  no-op at everything cannot score 1.00; **26 positives are tagged `novel`** —
  mechanisms `sota-code-security` rules/10 does *not* enumerate, which separates
  "teaches the lens" from "recites its own list". Two designs: `run-clean.py`
  (vocabulary given — classification) and `run-silent-open.py` (free-form, blind
  opus judge — discovery), both with an `--ablate` arm that removes rules/10.
  Result: **+0.00 — no measurable lift**, reproduced at n=49 and again at n=69.
  An earlier **+0.07 from a 15-case version did not replicate and is retracted**.
  The `novel` subgroup was grown 6 → 26 to test whether the enumerated catalogue
  *anchors* the model onto its own list: **it does not** (0.96 unguided vs 0.92
  with-library — one case, inside run spread), so that hypothesis is retired too
  ([`results/2026-07-20/SILENT-FAILURE.md`](results/2026-07-20/SILENT-FAILURE.md)).
  **Case-authoring note:** cases carry answer keys (`expect`, `reference`) and
  analysis metadata (`novel`); the runners whitelist only the input fields
  (`id`/`language`/`snippet`/`prompt`/`task`) into the prompt, so a new field
  cannot silently leak the answer — and `run-clean.py` aborts if a case is left
  with no content field at all, the guard added after that whitelist silently
  emptied the routing eval.
- `cases/finding-adjudication.jsonl` (30) — audit **precision**, the mirror of every
  other audit set here: a code snippet + a *claimed* finding → UPHELD or REFUTED.
  15 genuine claims and 15 plausible-but-wrong ones failing for six distinct reasons
  (upstream guard, unreachable code, inflated severity, misread mechanism, already
  mitigated, behaviour that is actually correct). Scored by `run-adjudication.py` on
  **specificity** (refute the false) and **sensitivity** (keep the real), with an
  ablation arm that strips `rules/01` §6. Result: **+0.00 — all three arms 1.00**,
  zero wrong answers in 90 adjudications per arm
  ([`results/2026-07-20/AUDIT-PROCESS.md`](results/2026-07-20/AUDIT-PROCESS.md)).
- `cases/desc-routing.jsonl` (10) — an adversarially-confusable task → the correct
  skill (`expect`) and the tempting wrong sibling (`distractor`). Scored by
  `run-desc-routing.py` as an A/B on the description cross-refs (result: +0.00).

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

## Clean isolated run (no session contamination)

`score.py` scores an agent you drive by hand *inside* a Claude Code session —
where the sota `CLAUDE.md` directive + skill registry are ambient, so the
"without-library" arm isn't truly library-free. **`run-clean.py`** removes that:
it makes **raw model-API calls** (OpenRouter; `OPENROUTER_API_KEY` from env or
`.env`, never committed) with the library content pasted into the with-arm only.

```sh
python3 evals/run-clean.py --cases evals/cases/freshness.jsonl --model anthropic/claude-sonnet-4.6
python3 evals/run-clean.py --cases evals/cases/router.jsonl
python3 evals/run-clean.py --cases evals/cases/audit-hard.jsonl
python3 evals/run-repo-audit.py          # cross-file audit (own fixture repo + harness)
python3 evals/run-competitors.py --competitors-dir DIR   # SOTA vs competing libraries
python3 evals/run-decay.py               # multi-turn skill-application decay (anchor/reminder/control)
python3 evals/run-desc-routing.py --samples 3 --temp 0.7   # description-catalogue routing A/B
python3 evals/run-clean.py --cases evals/cases/silent-failure.jsonl --ablate  # rules/10 ablation
python3 evals/run-silent-open.py --samples 5 --temp 1.0    # silent controls, open-ended + judged
python3 evals/run-adjudication.py --samples 3 --temp 0.7   # audit precision (false-positive resistance)
```

`--ablate` (on `run-clean.py`) drops `rules/10-silent-control-failure.md` from the
with-library arm, so a new rule file's contribution can be separated from the rest
of the skill. Generalize it by changing `ABLATE_FILE` when testing a different file.

**Competitor benchmark** (`run-competitors.py`, `cases/competitors.json`): SOTA
vs. the most popular competing guidance libraries on the 7 completeness tasks —
content-only, blind-judged. Result (2026-07-14): **SOTA-skills 0.99 vs
[affaan-m/ECC](https://github.com/affaan-m/ECC) ~230k★ 0.87,
[PatrickJS/awesome-cursorrules](https://github.com/PatrickJS/awesome-cursorrules) ~40k★ 0.83,
[alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) ~23k★ 0.81** (unguided
0.58) — SOTA wins/ties every case, loses none; competitors drop the same
cross-cutting concerns (rate limiting, transport, tests). Clone each competitor at
the pinned SHA into `DIR`
([`results/2026-07-13/COMPETITOR-BENCHMARK.md`](results/2026-07-13/COMPETITOR-BENCHMARK.md)).
A five-domain **breadth** run then reframes it: the lead tracks the *unguided
baseline*, not the domain — SOTA leads ~+10 where a base model ships incomplete code
(production backend in any language, complex/security-sensitive frontend) and ties
where it doesn't (simple UI, templated IaC)
([`results/2026-07-13/BREADTH.md`](results/2026-07-13/BREADTH.md)).

**Skill-application decay** (`run-decay.py`, `results/2026-07-13/DECAY.md`): the
*temporal* dimension — does a rule loaded early stop being applied as a session
grows? Arms: anchor / reminder (the `UserPromptSubmit`-hook analog) / control. First
run: **no decay at moderate scale** (guidance held over 30 unrelated turns; anchor
1.00, control 0.40) — bounds the problem but needs a bigger intervening context to
find the breaking point.

**Description-catalogue routing A/B** (`run-desc-routing.py`,
`cases/desc-routing.jsonl`, `results/2026-07-13/desc-routing-3sample.json`): measures
the skill **auto-loader** path (pick from the description catalogue), distinct from
the router table above. A/Bs the catalogue with vs without the negative cross-refs
("Not for X — use sota-Y") on 10 adversarially-confusable tasks. **Honest +0.00** —
the model never routed to the warned-against sibling in either arm, so the
description-selection path is already saturated for a frontier model (like audit); the
cross-refs are kept as zero-cost defensive clarity, no lift claimed.

**Live-agent BUILD validation** (`judge-live-build.py`) closes the completeness
eval's one simulation gap: `run-completeness.py` *pastes* the router's principle
5 + rules to stand in for what an agent loads. To confirm the real router-driven
flow behaves the same, drive an actual sub-agent over each `completeness` task
(handed only the bare "build X" prompt + the standing sota directive), collect
its files under `DIR/<case-id>/`, then:

```sh
python3 evals/judge-live-build.py --builds DIR   # same blind opus judge + rubrics
```

Result (2026-07-13, 7 live sub-agent builds): **0.99 mean, 6/7 perfect** —
matching the 0.99 paste-based simulation (0.987 vs 0.988) and far above the 0.60 unguided base, so the
simulation is a faithful proxy for the real router flow
([`results/2026-07-13/LIVE-BUILD.md`](results/2026-07-13/LIVE-BUILD.md)).

## Harness conventions (learned the hard way, 2026-07-20)

In one day, **four** changes to this harness silently did nothing while still
printing a plausible number:

| What broke | What it printed |
|---|---|
| A prompt-field whitelist that dropped `prompt` | The routing eval sent the model bare case ids — and a recall score |
| An ablation keyed on a section **number** | A renumber broke the match; the "ablated" arm would have been the full corpus |
| A scripted CHANGELOG edit whose anchor string didn't exist on that branch | "updated" — and the commit shipped without the entry |
| A wait condition matching a per-case `lift=` progress line | A still-running job reported complete, at 1 case of 7 |

These are the exact class `sota-code-security` rules/10 describes, in the tooling
that measures the library. So:

- **Guards abort, never warn.** `run-clean.py` refuses to run a case with no
  content field; `run-adjudication.py` refuses if its ablation target is missing;
  `run-completeness.py` refuses if the router's BUILD section no longer matches the
  hash its `BUILD_WORKFLOW` mirror was synced against. Three of the four failures
  above were caught by a guard like these.
- **Watch the guard fail before trusting it.** Every one of them was verified by
  deliberately breaking the input and confirming the abort.
- **Wait on a terminal artifact, not a log substring.** `--out` is written last;
  key completion checks on the file existing.
- **Assert a scripted edit landed.** Re-read the file; do not trust the script's
  own success message.
- **Pin what you mirror.** Anything hand-copied from the library into the harness
  (currently `BUILD_WORKFLOW`) carries a hash of its source and fails loudly on
  drift — the mirror rotted for four days and nothing noticed.

## Recorded runs

`results/<date>/` holds raw per-arm predictions (+ rationales / clean-run
outputs). Writeup: [`results/2026-07-10/BASELINE.md`](results/2026-07-10/BASELINE.md).
Headline (clean, by dimension): **completeness +0.39** (0.60→0.99 over 7 build
tasks — from a bare "build X" prompt the library embeds the tests/rate-limits/
logging/transport a base model skips; the thesis, and the part web-search likely can't
replace — predicted, not measured here), **freshness +0.50–0.53** (32-case set; base model
*confidently wrong*, but a web-search agent would likely recover most of it — predicted, not measured here), **routing
+0.09–0.14**, **audit +0.00** (even the 14 harder cases saturate). The lift is
only "small" if you measure the easy dimensions. Run:
`python3 evals/run-completeness.py`.

**Multi-sample confidence** (2026-07-13, `--samples 3 --temp 0.7`,
[`results/2026-07-13/MULTI-SAMPLE.md`](results/2026-07-13/MULTI-SAMPLE.md)): the
lifts hold and the **with-library arm is near-zero variance** — completeness
0.60→1.00 (+0.39, with-arm ±0.01 across-case sd, 6/7 cases perfectly steady),
routing 0.90→1.00 (+0.10, ±0.00), freshness 0.44→0.97 (+0.53, ±0.00). The
sampling wobble is all in the unguided arm; the library removes it.

The completeness number is load-bearing on *how* the library is applied — an
ablation: base model **0.60**; + rules pasted **~0.89** (first 4 tasks; the model
reads the guidance but silently drops peripheral concerns); + the **BUILD
self-audit** (check the diff against each Audit checklist, fill every gap)
**0.93** (7 tasks); + the router's short **universal non-negotiables** (operating
principle 5) **0.99** (7 tasks, 6/7 perfect — what a real agent loads). The
occasional slip is a **finite-constraint-budget** effect, **not** a coverage gap:
the guidance was in context with a checklist item, but a long dense context makes
a low-salience item fade — *adding* the "missing" rule made it worse; a short
salient reminder fixed it (see
[`docs/WHY-COMPLETENESS-RESIDUAL.md`](../docs/WHY-COMPLETENESS-RESIDUAL.md)).
Artifact: `results/2026-07-13/completeness-7case-p5.json`.

## Extending

Add a new case kind by giving each case an `id` and an `expect` list — `score.py`
is generic over the expected/predicted set comparison. Highest-value next set
(from the baseline): **harder audit cases** — multi-vuln snippets and subtler
authz/business-logic cases where a bare model misses what a skill-guided audit
catches. Also: contract tests the API skill should demand, migration-safety
cases for the DB skill.
