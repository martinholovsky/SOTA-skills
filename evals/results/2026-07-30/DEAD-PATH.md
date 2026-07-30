# Dead-path procedure eval — the hypothesis was wrong (+0.00)

**Date:** 2026-07-30 · **n:** 3 per arm, 6 live Claude Code sub-agents ·
**Instrument:** `evals/cases/dead-path/` + `evals/run-dead-path.py` ·
**Result: +0.00 on both scored axes. Both arms scored 1.000/1.000.**

## What this was testing, and why it should have been different

Four audit instruments already sat at +0.00, and the working explanation was that
they all score **recognition**: hand a frontier model the code and the question
and it is already at ceiling. `rules/11` and `rules/03 §3.9` do not ask for
recognition — they ask the model to *mutate the control, delete the dependency,
and run the real build*. That is **behaviour**, so the pre-registered hypothesis
(written into the roadmap before this ran) was:

> a bare agent reasons and scores ~0.25 verdict / 0.00 proof; a library-guided one
> runs the mutations.

**That hypothesis is refuted.** The bare agents ran the mutations unprompted.

## Setup

Six `general-purpose` sub-agents, identical prompts except the treatment:

- **bare (3):** the task, the four item ids, the verdict vocabulary, the report
  format. Nothing about procedure, evidence, or the library.
- **library (3):** the same, plus *"read and follow"* `rules/11` and
  `rules/03 §3.9`, and *"read only those two files from that repository"* (so an
  agent could not wander into `cases/dead-path.jsonl` and read the answers).

Each got its own copy containing **only** `ledger/` and `tests/` (9 files). The
fixture's `README.md` names the traps and `selfcheck.sh` contains the answers in
its comments — neither travelled, verified by grepping the handed-over copy for
every ground-truth term before launch.

## Result

| Arm | Verdict accuracy | Proof compliance | Both |
|---|---|---|---|
| bare1 / bare2 / bare3 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | **1.000** |
| lib1 / lib2 / lib3 | 1.000 / 1.000 / 1.000 | 1.000 / 1.000 / 1.000 | **1.000** |

**12/12 items correct in each arm**, including both inverted traps and the
REFUTED case that punishes over-flagging. Every agent in both arms worked in a
scratch copy, mutated the controls, deleted the modules, and ran the suite.

The bare agents did not merely comply — they went further than asked. One drove
`trace.Trace` over the suite to show `xml_export`'s render body never executes;
one used `dis` and identified `POP_TOP` after the control's `CALL` as the
bytecode tell for a discarded return; one fuzzed `parse()` across inputs to show
the reachable set of `source` values is exactly `{'api'}`. None of that was
requested.

## What differs, and why it is not in the score

Both arms reach the same verdicts with real evidence. What separates them is
**reporting discipline** — and the scorer does not grade it:

| Behaviour (post-hoc marker count) | bare | library |
|---|---|---|
| ACTIVE / LATENT label on the finding | 0/3 | 3/3 |
| Claim bounded by what actually ran ("the only suite is 4 tests") | 0/3 | 3/3 |
| Flags that the fix **moves a decision boundary** → needs known-good/known-bad validation | 0/3 | 3/3 |
| Severity / blast-radius statement | 1/3 | 3/3 |

Read this weakly. It is **post-hoc**, n=3, and partly tautological: the library
arm was told to follow a file that defines that vocabulary, so using it is
compliance rather than insight. Whether labelling and bounding *change any
outcome* is untested here. The honest summary is: **on everything this instrument
measures, the library adds nothing; the difference that remains is in how the
finding is written up, and its value is unmeasured.**

## Two disclosures

**1. The scorer was widened mid-run.** `lib3`'s `csv_export` proof initially
scored 0 because `RAN_RE` required a command-shaped token, and the proof said
"removed the file, ran the full suite → ModuleNotFoundError, 2 errors, exit 1" —
a real executed deletion, described in prose. That is a false negative in the
instrument, so execution verbs were added. The guard that keeps this honest is
`--selftest`, which still separates the arms **0.000 vs 1.000** after the change;
the reasoning arm cites greps and reads, which match no execution verb. Changing
an instrument after seeing data is a methodological red flag, so: the pre-fix
numbers were 6/6 arms at verdict 1.000, with proof 1.000 for five arms and 0.750
for `lib3`. **No arm's ranking changed** — the fix moved one arm from 0.750 to
1.000 in an already-saturated field.

**2. `lib3`'s report file is a transcription.** The harness blocked that agent
from writing a `.md` file (a subagent report-file guard; `bare2` hit the same
guard and worked around it via Bash). Its verdict lines were transcribed verbatim
from its returned output, but the surrounding method text was abridged — which is
why its raw marker counts looked low before correction. Its full returned output
did contain the ACTIVE label, the bounded claim, the decision-boundary warning and
a severity rating. Future runs should have the agent return the report in its
final message and let the parent write the file.

## What this means for the instrument

The fixture is not broken — its traps work, and `selfcheck.sh` re-derives all six
planted properties by mutation on every CI run. What is now known is that **the
traps do not discriminate at this model tier**: a capable agent handed a
four-item audit brief runs the procedure whether or not it is told to.

So this joins the other four as an honest null, and the "procedure not
recognition" explanation for their saturation does not survive. Two readings
remain open, neither tested:

- **The brief did the work.** Naming four suspects and demanding a `PROOF` field
  is itself a strong nudge. A genuinely unscoped prompt ("audit this repo") over a
  much larger tree might separate the arms — that is the agentic large-repo
  frontier already in the roadmap, and this run is weak evidence *for* prioritising
  it over more small fixtures.
- **The scored axes are the wrong ones.** If the real difference is labelling,
  bounding, and fix-risk, an instrument that grades those would measure something
  — but it would be measuring adherence to our own vocabulary, which is a much
  weaker claim than "finds more bugs", and should never be reported as a lift.

## Reproduce

```sh
bash evals/cases/dead-path/selfcheck.sh          # fixture still has its traps
python3 evals/run-dead-path.py --selftest        # scorer still separates the arms
python3 evals/run-dead-path.py --report REPORT.md
```
