# Pre-registration — ROADMAP 39: conflict rate between simultaneously-loaded skills

**Written 2026-09-09, BEFORE any judged pair.** The runner
(`evals/run-conflict-rate.py`), its `--selftest`, its four abort guards and its judge
calibration were built and **watched to fail** first; no real pair has been scored.

## Why this one, and why a judge

Four failure modes of a skill library have been named in this repo; this is the only one
with a **real incident** behind it. Two rules contradicted each other in a live build — a
liveness-probe rule against a no-`await` `async def` rule — and that incident is the
reason the router carries a conflict-resolution clause at all. Nothing has ever measured
how often it happens. `run-routing-recall.py` said so in its own docstring and left it as
v2, because a contradiction is not detectable by set comparison: it needs something that
reads both texts.

## Design

- **Which skills are loaded together** comes from `routing-recall.jsonl`'s gold sets — the
  router's own stated compositions. **No routing call**, so a routing error cannot
  contaminate a conflict number.
- **Pairwise.** A contradiction is between two texts, so each case expands into every
  unordered pair of its gold skills: **17 pairs** from 8 multi-skill cases. The two
  single-skill cases contribute no pairs and are excluded — printed, not dropped quietly.
- **Corpus:** each skill's `SKILL.md` plus **every** `rules/*.md`, labelled by path so any
  quoted conflict can be checked against the file afterwards.
- Judge `anthropic/claude-sonnet-5`, **3 samples** per pair, temp 0.0. A pair counts as
  conflicted if **any** sample reports at least one conflict.

## This measures a CEILING, and the write-up must say so

BUILD step 2 says *load lean*: a real session opens a skill's `SKILL.md` and only the
rules files matching the work. Handing the judge every rules file of both skills
**maximises** the chance a contradiction exists somewhere in what was "loaded". So:

- a **low** number is strong — the lived rate is lower still;
- a **high** number is not yet a claim about practice, only about what is available to
  collide.

Narrowing to lean loading is a separate experiment (v3) and is not rescued into this one.

## Predictions, with numbers

**H1 — conflicts are rare.** Judge-reported rate ≤ **0.15** of pairs, and the
**hand-verified** rate ≤ **0.10**. This is the honest prior: the library has one recorded
incident in fourteen months of use.

**H2 — conflicts are common at the ceiling.** Judge-reported rate ≥ **0.40**. Then "load
lean" stops being only a context-budget argument and becomes a correctness one, and the
router's conflict-resolution clause is carrying more weight than its one-incident
provenance suggests.

**Between 0.15 and 0.40** is reported as-is with its sample size, and settles nothing on
its own.

### Two numbers, and only one of them is quotable

The judge's rate is **unverified**. Every reported conflict is read against the two files
by hand (router principle 7 and AUDIT step 7: re-reading your own finding re-runs the
reasoning that produced it). The write-up reports **both** — judge-reported and verified —
and the **verified** number is the one that may be quoted. A judge-asserted contradiction
that does not survive reading the two quotes is a false positive, and the smoke run
already produced one candidate of that shape (`sota-cli-ux` + `sota-ux-writing`,
2 conflicts at n=1 on a trivial task), so the false-positive rate is expected to be
non-trivial.

### The falsification condition

H1 is refuted if the verified rate exceeds 0.10. It will not be rescued by re-reading the
judge's output more charitably, dropping a pair whose conflict is "not really about the
task", or switching to lean loading after seeing the number — that last one is a
different experiment and needs its own registration.

## What could make this measure nothing

- **A judge that never says yes.** The single most likely failure, and the one that would
  produce exactly the number this project would like. Guarded: two synthetic control
  pairs run in the same batch with the same model, prompt and temperature — one with a
  planted head-on contradiction (must report ≥ 1) and one benign (must report 0). If they
  do not separate the run is **VOID and prints no rate**. Both branches were watched:
  the VOID path was triggered by neutering the planted control, and the live calibration
  separated 1 / 0.
- **A parse failure read as zero.** `parse_conflicts` returns `None`, never `[]`, and the
  runner aborts on it. `--selftest` asserts exactly that, because a broken judge and a
  clean library would otherwise be the same number.
- **Silent truncation.** The largest pair is ~397k characters. `--max-chars` aborts rather
  than let a provider truncate a corpus past the contradiction it was meant to contain.
  Watched to fail.
- **The gold sets are small and stated.** 17 pairs is 17 pairs; this is a rate with a
  denominator in the sentence, which is the whole reason for pre-registering it — a
  conflict rate is exactly the number that would be quoted without its sample size.
- **"Contradiction" is a judgement.** The prompt excludes mere difference of emphasis and
  excludes a narrower rule overriding a general default *when it says it is narrower* —
  which is the router's own conflict-resolution shape. A judge that ignores that
  instruction inflates the number, and hand-verification is what catches it.
- **One model, one day.** Dated to `sonnet-5`.

## Cost and status

17 pairs × 3 samples = **51 judge calls** plus 2 calibration calls, over ~4.4M characters
of corpus. Live spend on the operator's account, authorised 2026-09-09.
