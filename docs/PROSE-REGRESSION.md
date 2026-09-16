# Did this rule change make the guidance worse?

Every gate in this repo answers a *structural* question — is the file under the cap, does the
§-reference resolve, does the count match the list. **None of them reads what a rule says.**
An external audit on 2026-09-15 found 19 wrong statements in v1.42.1, and all 33 invariants
were green on every one. That is not a gap the invariants can close: "is this claim correct"
is semantic, and a fuzzy gate gets disabled ([CONVENTIONS-LEDGER](CONVENTIONS-LEDGER.md)).

What *can* be measured is whether the text you changed still makes a model do the right thing
— **compared against the same library before your change**. That is
[`evals/run-prompt-independence.py`](../evals/run-prompt-independence.py), and this note is
about when to reach for it. The mechanics live in [evals/README.md](../evals/README.md); the
harness conventions there are not repeated here.

## What it compares

Three arms, and the middle one is the point:

| arm | what it loads |
|---|---|
| `bare` | the task alone — a free negative control on the whole measurement |
| `pre` | your rules files **as of the ablation ref** (default `main`), read with `git show <ref>:<path>` — the real prior text, never a hand-mirror that can drift |
| `post` | the same files in your working tree |

`pre` vs `post` isolates *your edit*. Each case is rendered at three pressure levels —
supportive / neutral / **competing** — because a rule that only survives a neutral prompt is
absent exactly when it is needed.

## It is per-change by design — this is the part people miss

The treated cases are **one per rules file the originating branch changed**. They are not a
standing regression net over the library. If your branch edits files that no case loads, every
case is byte-identical between `pre` and `post`, and the runner **exits `FAIL`** rather than
printing a number:

```
FAIL: no case's rules files differ between main and the working tree
```

That is deliberate — an ablation that did not take is a duplicate arm wearing a different
label. **Seeing that message means you forgot to add a case, not that your change is safe.**

So using it means **adding a treated case that names your file**: an `id`, the `rules_files`
it loads, a `task` that exercises the rule *without naming it*, the three `pressure` strings,
and a fixed `rubric` the judge scores criterion by criterion. Leaking the rule into the task
is what made an earlier attempt saturate.

Keep the existing control cases. Their files are unchanged by construction, so their
`pre→post` delta is this run's **noise floor, measured inside the run** rather than assumed.

## When a prose change warrants a run

**Run it when the change alters what the model is told to *do*:**

- an imperative changes, or gains or loses an exception — *"never hold a lock across an
  await"* becoming *"never hold a **blocking** lock…"* changes the advice on real code;
- a severity or threshold moves (a `HIGH` becoming a `MEDIUM`, a cap, a floor, a percentage);
- a new non-negotiable or audit-checklist item lands;
- the router's BUILD/AUDIT workflow or an operating principle is edited;
- a rule is **narrowed** — scoping is the shape most likely to silently stop firing.

**Do not run it for:**

- typos, link fixes, adding a citation or a date to an existing claim;
- a split that moves text unchanged — `pre` and `post` render the same bytes, so the run
  measures nothing, and the guard above will say so;
- CHANGELOG, ADOPTION-LOG, README, or any file a model never loads as instructions;
- a correction that makes a *false* statement true. Verify that against the primary source
  instead. A model's behaviour is not evidence about what an upstream doc says.

That last exclusion is the common case in practice, and it is why this is a judgement call
rather than a gate.

## Cost, so the decision is informed

At defaults — 6 cases × 3 levels × 3 arms — one run is **54 build calls and 54 judge calls**.
Raising the sample count multiplies it. Narrow the arm list to drop the ablation and keep only
the total effect, or narrow the levels to the competing one, which discriminates most.

**Run the self-test first, every time.** It puts a deliberately compliant and a deliberately
non-compliant reference through the judge and requires them to separate 1.00 from 0.00. If
they do not, no number from the run means anything — and that check costs two calls instead of
a hundred.

## Reading the result

- **Controls `pre→post` ≈ 0.** That is your noise floor for this run. If a control moves, the
  run is noisy and a treated delta of the same size is not a finding.
- **Treated `pre→post` at or below the noise floor** — your edit did not measurably change
  behaviour on that case. That is a *real* outcome worth writing down, not a failure of the
  instrument.
- **Treated `pre→post` clearly negative** — the change made the guidance worse under pressure.
  Say so in the PR, with the number.
- **One sample is not a measurement.** A single run at temperature 0 is an indication; quote
  `n` beside any number you publish, which invariant 13 enforces on the scoreboard.

## What this does not do

It measures **the cases you wrote**, on the model you named, on the day you ran it. It is not
a general regression net over the whole library, and no instrument here is. Its value is that
it compares against *the real previous text* rather than against a memory of it — which is
precisely the failure mode that let 19 wrong statements ship under 33 green gates.
