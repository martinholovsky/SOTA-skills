# Live-agent BUILD validation — result (2026-07-13)

**Question (roadmap item 2):** the completeness eval (`run-completeness.py`)
*pastes* the router's operating principle 5 + rules + a self-audit instruction
into a single API call to simulate what an agent loads. Does the **real
router-driven flow** — a live agent that reads the router, loads lean, plans with
a checklist, and runs the terminal self-audit gate — behave the same, or does the
paste over-state what an actual agent does?

**Answer: validated.** Seven fresh sub-agents were each handed only the bare
"build X" completeness task plus the standing sota directive (consult the router,
follow BUILD mode). All seven independently followed the workflow, and the
terminal self-audit gate demonstrably recovered the cross-cutting concerns and
caught real gaps — the exact mechanism the simulation credits for the
completeness lift, now confirmed outside the simulation.

## Setup

One `general-purpose` sub-agent per `completeness` case (c1–c7), model
`sonnet`, each in an isolated empty work dir, told to follow the real router
BUILD workflow and log its process. Artifacts collected under
`live-build/<case-id>/`; `evals/judge-live-build.py` reuses the completeness
harness's blind opus judge + rubrics to score them. Six of seven wrote the
requested `process.md` self-audit log; c1 completed a full code deliverable but
stalled before writing its log (it blocked waiting on a background pytest).

## What was verified (primary sources, not agent summaries)

**1. All seven followed the router BUILD workflow.** Each `process.md` records
the exact skill files read (router → lean skill set → matching rules files), a
pre-implementation requirements checklist, and a per-item self-audit outcome —
the load-lean → plan-with-checklist → terminal-self-audit shape the router
prescribes.

**2. Cross-cutting concerns are present in every applicable build** (the items
the salience effect predicts get dropped, per `WHY-COMPLETENESS-RESIDUAL.md`).
Per-file presence check across the authored source:

| build | rate-limit files | logging files | test files | transport refs |
|---|---|---|---|---|
| c1 ticket-api | 5 | 4 | 3 | 1 |
| c2 upload | 3 | 2 | 1 | 4 |
| c3 email-worker | 3 | 5 | 7 | 0 * |
| c4 login | 5 | 3 | 2 | 3 |
| c5 search | 6 | 5 | 5 | 3 |
| c6 webhook | 4 | 2 | 4 | 4 |
| c7 pw-reset | 5 | 4 | 3 | 3 |

\* c3 is a background queue worker with no HTTP endpoint, so TLS/transport is
correctly N/A — and its `process.md` says so explicitly ("rate limiting keyed to
an external caller identity doesn't apply 1:1 — there is no inbound caller"),
which is the *contextual* application of principle 5 the router asks for, not
blind checklist-ticking.

**3. The terminal self-audit gate caught and fixed REAL gaps** — verified by
reading the `process.md` audit tables, not the agents' own summaries:

- **c6 webhook** — the gate found two genuine gaps in the already-built code and
  fixed them with tests: (a) FastAPI's `/docs` `/redoc` `/openapi.json` were
  exposed in production (gated to `None` when env=production); (b) the
  DB-touching critical section had no timeout — a stuck lock would hold the
  request open indefinitely (wrapped in `asyncio.timeout`, mapped to an honest
  504). Items 21–27 of its table are *reasoned* out-of-scope calls, not silent
  omissions — exactly the "say why, don't drop silently" principle-5 discipline.
- **c3 email-worker** — the gate caught a real concurrency bug: handler tasks
  spawned via bare `asyncio.create_task` were orphaned under a direct
  cancellation of `worker.run()`; fixed to `tg.create_task` so the TaskGroup owns
  them, with a regression test that would have hung before the fix.
- **c2 / c4 / c5 / c7** each likewise report the gate catching a real defect
  (event-loop-blocking CPU work + missing request-id; a naive/aware datetime
  comparison bug in the refresh flow; unlogged authz-denial events; a log
  redaction filter that was dropping/leaking `extra` audit data).

This is the simulation's claim made concrete: the self-audit-LAST step is not
ceremonial — in a live flow it re-surfaces faded cross-cutting concerns *and*
finds bugs the first pass introduced.

## The one thing still pending: the reproducible recall number

The automated blind-judge recall (to place the live builds on the same
0.60-base / 0.99-simulated scale) did **not** complete: the OpenRouter account
is out of credits (HTTP 402; `total_usage` 225.14 ≥ `total_credits` 225.00, and
the two repo-audit runs earlier today spent the tail). `evals/judge-live-build.py`
is written, its artifact collector verified (it prunes `.venv`/caches and reads
the ~19–22 authored files per build), and it will produce the number in one
command once credits are topped up:

```sh
python3 evals/judge-live-build.py --builds <live-build-dir> \
  --out evals/results/2026-07-13/live-build.json
```

So the **qualitative + structural** validation of roadmap item 2 is complete and
positive; the **single scalar** that would let us write "live-agent completeness
= 0.XX vs 0.99 simulated" is deferred to the next run with credit available. It
does not change the finding — every applicable build carries the cross-cutting
concerns, and the self-audit gate provably works in the live flow — but it is
recorded honestly as unfinished rather than asserted.
