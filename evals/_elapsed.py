"""Wall-time reporting and a local duration baseline for the eval runners.

Every runner used to finish without saying how long it took, so "this got 30x
faster" -- or 30x slower -- was visible only to a human diffing two logs. The
invariant script has printed its duration alongside its denominators since
2026-07-30 (`sota-code-security` rules/11 SS2.1: a step that reports "nothing
found" far faster than its claimed work allows did not do the work). The runners
did not.

Printing alone was not enough. SS2.1's tell is a COMPARISON -- "far faster than
its claimed work allows" needs something to compare against -- so each run is
appended to a local ledger and the next run of the same runner prints the delta.
The regression becomes visible in the log you are already reading.

DURATION WITHOUT A DENOMINATOR IS THE SAME DEFECT IN TIME FORM. "12s" says
nothing; "12s over 7 cases" does. Runners call note_work(n, unit) once they know
their corpus size, and a run recorded without one is printed as `no denominator`
rather than being quietly compared as bare seconds.

THE LEDGER IS DELIBERATELY GIT-IGNORED, and that is correctness, not a
compromise: a duration is only comparable on the same machine and network.
Committing one would invite exactly the cross-machine comparison it cannot
support, and would dirty the tree on every local run.

PRINTED, NEVER GATED, and to **stderr**. Two deliberate choices:

- No threshold fails a build. These runners call a remote API whose latency is
  not ours; a duration gate would be flaky, and a flaky gate gets disabled, which
  is how a control becomes inert. A large swing is flagged in the text, and a
  human decides.
- stderr, so a runner whose stdout is piped into a report or parsed by another
  tool is not silently given an extra line to choke on.

Registered via atexit so the line still prints when a runner ends through
`sys.exit(...)` -- which several of them do on an empty corpus, and which is
exactly the fast-exit case worth timing.

FAILS OPEN ON EVERY PATH. A missing, unreadable, or corrupt ledger must never
break a run: this module reports, it never decides.

A RUN THAT DID NOT DO THE WORK IS NOT A BASELINE. Every invocation appends --
deliberately, since a fast exit on an empty corpus is exactly the case worth timing
-- so this ledger carries `--selftest` runs, usage errors and aborted runs beside
real measurements. They were indistinguishable until 2026-09-02, when a replay of
the live ledger showed **46 of 60 rows were sub-10s aborts (77%)** and **3 of the 14
real runs had been compared against one**: `run-completeness` printed
`previous 0.1s -- 6340.0x slower <-- CHECK THIS` on its first genuine measurement,
and the next real run would have read `previous 0.0s (no usable ratio)` against an
abort logged 92 seconds after a good 3651.8s run. The diagnostic this module exists
to implement was inert for its most-run runner.

The cause was not that aborts are recorded; it is that `_previous()` could not tell
them apart. `run-build-safe.py` calls `note_work(len(cases))` BEFORE its `--selftest`
branch, so the runner's own scorer test recorded `n=7 cases` in the same shape as a
measurement. So: mark at the point of collection, filter on read, and say what was
excluded -- `sota-observability` rules/05 SS8a and
`sota-code-security` rules/11 SS2.7, both written from this defect. `note_complete()` is that mark; a row without it is `partial` and is read, counted and
reported, but never returned as a baseline.

This module is NOT a measuring instrument: nothing scores it and no published
number depends on it.
"""

import atexit
import os
import sys
import time

# Ratio at which a change is worth a human's attention. Not a threshold that
# fails anything -- SS2.1 is about the 30x speedup that means the work stopped
# happening, and 5x is comfortably outside ordinary API-latency noise.
NOTABLE_RATIO = 5.0

LEDGER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "durations.tsv")

# Ledger row status, column 6. A 5-column row predates the marker (2026-09-02) and
# is treated as `partial`: we cannot know whether it did its work, and guessing from
# its duration is the naming-convention filter that caused this defect.
OK, PARTIAL = "ok", "partial"

_work = {"n": None, "unit": "items", "complete": False}

# Partial rows passed over while looking for a baseline, so the printed line can state
# its own exclusion filter instead of leaving the reader to wonder.
_skipped = {"n": 0}


def note_complete():
    """Mark this run as having finished its work; call it after main() returns.

    A runner that exits early -- `--selftest`, a usage error, a guard, an empty
    corpus, an exception -- never reaches this, and is recorded as `partial`.
    """
    _work["complete"] = True


def note_work(n, unit="cases"):
    """Declare the denominator for this run: how many items it processed."""
    try:
        _work["n"] = int(n)
        _work["unit"] = str(unit)
    except Exception:
        pass


def _previous(label):
    """Most recent COMPLETED prior row for this label, or None. Never raises.

    Partial rows are counted into `_skipped` and passed over. Comparing against one
    is worse than having no baseline: it manufactures a 6340x alarm, or silently
    disarms the check with `no usable ratio`.
    """
    _skipped["n"] = 0
    try:
        with open(LEDGER, encoding="utf-8") as fh:
            rows = [r.rstrip("\n").split("\t") for r in fh if r.strip()]
    except Exception:
        return None
    for row in reversed(rows):
        if len(row) < 5 or row[1] != label:
            continue
        if len(row) < 6 or row[5] != OK:
            _skipped["n"] += 1
            continue
        try:
            return {"elapsed": float(row[2]),
                    "n": int(row[3]) if row[3] != "-" else None,
                    "unit": row[4]}
        except Exception:
            continue
    return None


def _append(label, elapsed):
    try:
        os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
        stamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
        n = _work["n"] if _work["n"] is not None else "-"
        status = OK if _work["complete"] else PARTIAL
        with open(LEDGER, "a", encoding="utf-8") as fh:
            fh.write(f"{stamp}\t{label}\t{elapsed:.1f}\t{n}\t{_work['unit']}\t{status}\n")
    except Exception:
        pass


def _compare(prev, elapsed):
    """Human-readable delta against the previous run, or why there isn't one."""
    # A run that did not do the work is not comparable to one that did: comparing them
    # produces a 23x "CHECK THIS" alarm about an abort, which is noise in the exact
    # place SS2.1's real signal is meant to appear. Say so and stop.
    if not _work["complete"]:
        return "partial run — not compared, and not a baseline for the next run"
    if prev is None:
        if _skipped["n"]:
            return (f"no completed baseline yet — {_skipped['n']} partial run(s) "
                    f"excluded; this run becomes it")
        return "no baseline yet — this run becomes it"
    now_n, prev_n = _work["n"], prev["n"]
    if now_n and prev_n and now_n != prev_n:
        # Different corpus sizes: compare per item, and say so.
        a, b = elapsed / now_n, prev["elapsed"] / prev_n
        basis = f"per {_work['unit'][:-1] if _work['unit'].endswith('s') else _work['unit']}"
    else:
        a, b = elapsed, prev["elapsed"]
        basis = "total"
    if a <= 0 or b <= 0:
        return f"previous {prev['elapsed']:.1f}s (no usable ratio)"
    ratio, faster = (b / a, True) if a < b else (a / b, False)
    word = "faster" if faster else "slower"
    line = f"previous {prev['elapsed']:.1f}s — {ratio:.1f}x {word} ({basis})"
    if ratio >= NOTABLE_RATIO:
        line += "  <-- CHECK THIS: a large swing usually means the work changed, not the speed"
    if now_n is None or prev_n is None:
        line += "  [no denominator — bare seconds, weak evidence]"
    if _skipped["n"]:
        line += f"  [{_skipped['n']} partial run(s) skipped to find it]"
    return line


def report_on_exit(label):
    """Print '[label elapsed 12.3s ...]' to stderr when the process exits."""
    started = time.time()
    prev = _previous(label)

    def _emit():
        elapsed = time.time() - started
        n = _work["n"]
        size = f" over {n} {_work['unit']}" if n is not None else ""
        mark = "" if _work["complete"] else " PARTIAL —"
        try:
            print(f"[{label}{mark} elapsed {elapsed:.1f}s{size} | "
                  f"{_compare(prev, elapsed)}]", file=sys.stderr)
        except Exception:
            pass
        _append(label, elapsed)

    atexit.register(_emit)
