# Two pre-registered runs stopped mid-flight: `HTTP 402 Payment Required`

> **Both runs were resumed and both items are now CLOSED** (noted 2026-09-11). ROADMAP 39
> completed 2026-09-09 ([CONFLICT-RATE.md](CONFLICT-RATE.md), `conflict-rate.json`) and
> ROADMAP 43 completed 2026-09-10 ([GATE-ABSORPTION-N3.md](GATE-ABSORPTION-N3.md),
> `completeness-gate-absorption-n3.json`) — both artifacts sit in this directory. The
> incident record below is left exactly as written; only this line and the closing one were
> added, because the file's own last sentence said the two items *stay open* and that
> sentence outlived the runs by two days.

**2026-09-09.** The OpenRouter account ran out of credit part-way through both long runs.
Neither produced its registered number, and **neither partial is a result**. This file
exists so the gap is recorded rather than discovered later as a missing artifact.

## What happened

| run | item | progress when it stopped | artifact |
|---|---|---|---|
| `run-conflict-rate.py --samples 3 --temp 0.0` | ROADMAP 39 | **10 of 17 pairs**, then aborted | [conflict-rate-ABORTED.log](conflict-rate-ABORTED.log) |
| `run-completeness.py --pad-rules 400 --no-gate-arm --samples 3 --temp 0.7` | ROADMAP 43 | **2 of 7 cases** (8 of 28 arm-cells), then stopped by hand once the 402 was known | [gate-absorption-n3-ABORTED.log](gate-absorption-n3-ABORTED.log) |

Both runners write their JSON artifact only at the end, so **no `--out` file exists for
either**. The logs above are the whole record.

## The guards behaved correctly, and that is the only claim made here

`run-conflict-rate.py` aborted with:

```
judge call failed after 4 tries: <HTTPError 402: 'Payment Required'>
A run that silently skipped a pair would under-report the conflict rate, so this
aborts rather than continuing.
```

That is the guard doing exactly its job. A run that swallowed the failure would have
divided by 17 while measuring 10 and printed a **lower** conflict rate with no sign that
anything was missing — the under-count with no signal that it is one, which is the shape
`sota-code-security` rules/11 §2.2a describes. The same is true of the completeness
runner's `call()`, which raises rather than returning an empty artifact.

**The judge calibration passed before the abort** — planted contradiction → 1 conflict,
benign pair → 0 — so the instrument was working; it ran out of money, not out of validity.

## Why the partial conflict numbers are NOT reported as a rate

10 of 17 pairs, 4 of them with a judge-reported conflict, is **not** 4/10. The
pre-registration fixed the denominator at 17 pairs and required a **hand-verified** rate
alongside the judge-reported one, and no hand verification has been done. Quoting 0.40
from this log would be:

- a rate over a denominator chosen by when the money ran out, and
- the judge-reported number, which the registration says is not the quotable one.

The completed rows are in the log for whoever re-runs it, and the seven pairs that never
ran are named there by their absence.
~~**`ROADMAP 39` and `ROADMAP 43` both stay OPEN.**~~ — true when written; **both
closed** on the re-runs above (39 on 2026-09-09, 43 on 2026-09-10).

## To resume

Top up the account, then re-run each from scratch — not from the log, which carries no
resumable state:

```sh
python3 evals/run-conflict-rate.py --samples 3 --temp 0.0 \
    --out evals/results/<date>/conflict-rate.json

python3 evals/run-completeness.py --pad-rules 400 --no-gate-arm --samples 3 --temp 0.7 \
    --out evals/results/<date>/completeness-gate-absorption-n3.json
```

Both pre-registrations stand unchanged and were committed before any call:
[conflict rate](PRE-REGISTRATION-CONFLICT-RATE.md) ·
[GATE-ABSORPTION n≥3](PRE-REGISTRATION-GATE-ABSORPTION-N3.md). Re-running does not need a
new registration — nothing about either design was changed in response to seeing a
partial, and the thresholds are the ones already written down.
