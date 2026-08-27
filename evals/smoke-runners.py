#!/usr/bin/env python3
"""Every eval runner must still be able to REACH its first network call.

WHY THIS EXISTS. `run-desc-routing.py` was dead from 2026-08-05 to 2026-08-27: an
ablation-assertion guard called `.splitlines()` on the list `catalogue()` returns and
raised `AttributeError` before the first API call. It went unnoticed for three weeks
because the last recorded run of that eval PREDATED the guard — a guard added by an
instrument audit to prevent a fake null instead made the instrument unrunnable
(`sota-code-security` rules/12: watch the guard run).

`--help` would NOT have caught it: the crash was inside `main()`, after argparse. So the
success signal here is "the runner got as far as trying to talk to the network".

HOW. `urllib.request.urlopen` is the single choke point every runner shares; it is patched
to raise, and each `main()` is run under an alarm. Outcomes:

  reached the network   -> healthy (the interesting case)
  SystemExit            -> a guard fired or it needs args; alive, so not a failure here
  alarm                 -> still doing local work after N seconds; alive
  any other exception   -> DEAD, and this script fails

This proves runners can START. It does not prove they produce correct numbers — that is
what the per-runner selftests and the negative-control harness are for.

Usage: python3 evals/smoke-runners.py [--timeout N]
Exit 1 if any runner is dead.
"""
import argparse, contextlib, glob, importlib.util, io, os, signal, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _Reached(Exception):
    pass


class _Alarm(Exception):
    pass


# Args for the runners that legitimately require them; a missing entry means "no args",
# which is fine — the runner will exit(2) with usage and that counts as alive.
ARGS = {
    "run-clean.py": ["--cases", "evals/cases/router.jsonl"],
    "run-competitors.py": ["--competitors-dir", os.path.join(ROOT, "no-such-dir")],
    "judge-live-build.py": ["--builds", os.path.join(ROOT, "no-such-dir")],
    "run-dead-path.py": ["--selftest"],
    "run-build-safe.py": ["--selftest"],
    "run-build-safe-arms-guided.py": ["/tmp/smoke-out", "smoke/model", "1000"],
    "run-build-safe-arms.py": ["u", "/tmp/smoke-out", "smoke/model", "1000"],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=20,
                    help="per-runner seconds before it counts as alive-but-busy")
    a = ap.parse_args()

    os.chdir(ROOT)
    sys.path.insert(0, os.path.join(ROOT, "evals"))
    urllib.request.urlopen = lambda *x, **k: (_ for _ in ()).throw(_Reached())
    signal.signal(signal.SIGALRM, lambda *x: (_ for _ in ()).throw(_Alarm()))

    files = sorted(glob.glob(os.path.join(ROOT, "evals/run-*.py"))
                   + glob.glob(os.path.join(ROOT, "evals/judge-*.py")))
    files = [f for f in files if os.path.basename(f) != os.path.basename(__file__)]
    # Fail closed on an empty scope: "0 checked, 0 dead, exit 0" is the signature of a
    # gate that verifies nothing (`sota-code-security` rules/11 §2.2).
    if not files:
        sys.exit(f"no eval runners found under {ROOT}/evals — refusing to report a pass.")

    dead, saved_argv = [], sys.argv
    print(f"Smoke test: can each eval runner reach its first network call? "
          f"({len(files)} runners, {a.timeout}s each)\n")
    for f in files:
        base = os.path.basename(f)
        spec = importlib.util.spec_from_file_location("smoke_" + base[:-3].replace("-", "_"), f)
        mod = importlib.util.module_from_spec(spec)
        signal.alarm(a.timeout)
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                spec.loader.exec_module(mod)
                sys.argv = [f] + ARGS.get(base, [])
                if hasattr(mod, "main"):
                    mod.main()
            verdict = "ok    (completed without needing the network)"
        except _Reached:
            verdict = "ok    (reached its first network call)"
        except _Alarm:
            verdict = f"ok    (alive; still working locally after {a.timeout}s)"
        except SystemExit:
            verdict = "ok    (guard fired or usage printed)"
        except BaseException as e:              # noqa: BLE001 — any other failure is the finding
            verdict = f"DEAD  {type(e).__name__}: {str(e).splitlines()[0][:70]}"
            dead.append(base)
        finally:
            signal.alarm(0)
            sys.argv = saved_argv
        print(f"  {base:32s} {verdict}")

    print(f"\n{len(files)} runners checked, {len(dead)} dead.")
    if dead:
        sys.exit("FAIL: dead runner(s): " + ", ".join(dead))
    print("PASS: every eval runner can start.")


if __name__ == "__main__":
    main()
