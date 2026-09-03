# Pre-registration — does offloading the library map cost routing accuracy?

Written and committed **before any agent ran**. PR #308.

## The change under test

`skills/sota/SKILL.md` 499 → 398 lines: the 108-line **library map** moved to
`skills/sota/rules/04-library-map.md`. Measured token effect (already known,
`count_tokens`, `claude-sonnet-5`): router **16,997 → 13,415**, −21.1% per load.
The open question is whether routing accuracy pays for that.

## Instrument, and a correction

**`run-clean.py --cases evals/cases/router.jsonl`.** It pastes
`skills/sota/SKILL.md` as the with-library treatment (`run-clean.py:186-187`), so it
can see this change.

**PR #308 originally named `run-desc-routing.py`. That was wrong and would have
measured nothing.** That runner builds its catalogue from each skill's frontmatter
`description` (`parse_desc`, `catalogue`) and never reads the router body — the arm
could not have seen the treatment, so its +0.00 would have been structural, not a
result. Its own docstring says as much: it measures the description catalogue "as
opposed to the router table that `run-clean.py --cases router.jsonl` measures".

## Design

- 27 router cases, two arms per run: **with-library** (router pasted) and
  **no-library** (skill names only).
- Two runs of the *same* command, differing only in which router is on disk:
  **BEFORE** = `main` (map inline, 499 lines) · **AFTER** = PR #308 (map offloaded, 398).
- `--samples 3 --temp 0.7`. Not temp 0: measured on this repo, temp 0 is **not**
  deterministic and the n=1 noise floor is ≈±0.03.
- Metric: mean recall on the with-library arm.

## Built-in negative control

The **no-library arm never reads the router**, so it is identical work in both runs.
Whatever it moves by between BEFORE and AFTER is this measurement's own noise, and no
treatment effect smaller than that is reportable.

## Prediction

**No meaningful change in with-library recall** — |Δ| at or below the no-library arm's
own drift between the two runs. Reasoning: the 2026-08-26 sweep found routing recall
flat at 2.6× router length, and the map is a lookup table, not routing logic — the
routing table and the 21 cross-cutting rules both stay in the router.

## What would falsify it

With-library recall **drops** in AFTER by more than the no-library arm's drift over the
same pair of runs. That would mean the map was carrying routing signal, and the
offload should be reverted or the map's pointer strengthened.

**A drop is the outcome that blocks the merge.** A rise is not a win to claim from n=3;
it would be noise absent a much larger sample.
