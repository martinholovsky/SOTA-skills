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

_work = {"n": None, "unit": "items"}


def note_work(n, unit="cases"):
    """Declare the denominator for this run: how many items it processed."""
    try:
        _work["n"] = int(n)
        _work["unit"] = str(unit)
    except Exception:
        pass


def _previous(label):
    """Most recent prior row for this label, or None. Never raises."""
    try:
        with open(LEDGER, encoding="utf-8") as fh:
            rows = [r.rstrip("\n").split("\t") for r in fh if r.strip()]
    except Exception:
        return None
    for row in reversed(rows):
        if len(row) >= 5 and row[1] == label:
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
        with open(LEDGER, "a", encoding="utf-8") as fh:
            fh.write(f"{stamp}\t{label}\t{elapsed:.1f}\t{n}\t{_work['unit']}\n")
    except Exception:
        pass


def _compare(prev, elapsed):
    """Human-readable delta against the previous run, or why there isn't one."""
    if prev is None:
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
    return line


def report_on_exit(label):
    """Print '[label elapsed 12.3s ...]' to stderr when the process exits."""
    started = time.time()
    prev = _previous(label)

    def _emit():
        elapsed = time.time() - started
        n = _work["n"]
        size = f" over {n} {_work['unit']}" if n is not None else ""
        try:
            print(f"[{label} elapsed {elapsed:.1f}s{size} | {_compare(prev, elapsed)}]",
                  file=sys.stderr)
        except Exception:
            pass
        _append(label, elapsed)

    atexit.register(_emit)
