"""Wall-time reporting for the eval runners.

Every runner used to finish without saying how long it took, so "this got 30x
faster" — or 30x slower — was visible only to a human diffing two logs. The
invariant script has printed its duration alongside its denominators since
2026-07-30 (`sota-code-security` rules/11 SS2.1: a step that reports "nothing
found" far faster than its claimed work allows did not do the work). The runners
did not.

PRINTED, NEVER GATED, and to **stderr**. Two deliberate choices:

- No threshold. These runners call a remote API whose latency is not ours; a
  duration gate would be flaky, and a flaky gate gets disabled, which is how a
  control becomes inert.
- stderr, so a runner whose stdout is piped into a report or parsed by another
  tool is not silently given an extra line to choke on.

Registered via atexit so the line still prints when a runner ends through
`sys.exit(...)` -- which several of them do on an empty corpus, and which is
exactly the fast-exit case worth timing.

This module is NOT a measuring instrument: nothing scores it and no published
number depends on it. It reports; it never decides.
"""

import atexit
import sys
import time


def report_on_exit(label):
    """Print '[label elapsed 12.3s]' to stderr when the process exits."""
    started = time.time()

    def _emit():
        print(f"[{label} elapsed {time.time() - started:.1f}s]", file=sys.stderr)

    atexit.register(_emit)
