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
  SystemExit            -> a guard fired or it needs args; alive, so not a failure here.
                           THE MESSAGE IS PRINTED: a guard that fires always and one that
                           fires for want of args are the same exception, and rendering
                           both as a bare "ok" hid a dead runner for six days.
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

    # Every runner must ALSO put its side effects behind `if __name__ == "__main__"`.
    # The smoke check below cannot catch a module-level script: importing one runs the
    # whole thing, which looks exactly like "reached its first network call" — that is
    # how run-router-length.py passed while executing its sweep on import. Two runners
    # were found like this (2026-08-27), so it is asserted rather than remembered.
    import ast
    unguarded = []
    for f in files:
        tree = ast.parse(open(f, encoding="utf-8").read())
        if not any(isinstance(n, ast.If) and ast.unparse(n.test).startswith("__name__ ==")
                   for n in tree.body):
            unguarded.append(os.path.basename(f))
    if unguarded:
        sys.exit("FAIL: no `if __name__ == \"__main__\"` guard, so importing these runs "
                 "them: " + ", ".join(unguarded))
    print(f"  guard check: all {len(files)} runners keep side effects behind __main__\n")

    # And every .env read must be existence-checked. This defect is INVISIBLE locally — a
    # maintainer's tree has a .env, so the failing branch is only reachable on a machine
    # without one — and it shipped twice (run-router-length.py, run-build-safe-arms.py),
    # both caught by CI rather than by any local run. A static check costs nothing and does
    # not depend on the runner being reached.
    unguarded_env = []
    for f in files:
        tree = ast.parse(open(f, encoding="utf-8").read())
        for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
            src = ast.unparse(fn)
            # Match on the FUNCTION, not the open() call: these build the path first
            # (`p = os.path.join(..., ".env")`) and then call `open(p)`, so a check that
            # looked for ".env" inside the open() call matched nothing and passed the
            # broken tree as happily as the healthy one — caught by watching it fail.
            reads = ".env" in src and any(
                isinstance(c, ast.Call) and getattr(c.func, "id", "") == "open"
                for c in ast.walk(fn))
            if reads and "os.path.exists" not in src and "os.path.isfile" not in src:
                unguarded_env.append(f"{os.path.basename(f)}:{fn.name}()")
    if unguarded_env:
        sys.exit("FAIL: .env opened with no existence check (raises on any machine without "
                 "one, e.g. every CI runner): " + ", ".join(sorted(set(unguarded_env))))
    print("  env check:   every .env read is existence-checked\n")

    # And every runner that RECORDS a duration must also MARK the run complete. Without
    # the mark, `--selftest` runs, usage errors and aborts land in results/durations.tsv
    # in the same shape as measurements — 46 of 60 rows were aborts when this was
    # measured (2026-09-02), and 3 of 14 real runs had been compared against one. The
    # marker is `note_complete()` after `main()` returns; a runner that registers
    # `report_on_exit` without it silently re-opens the shared sink, which disarms the
    # §2.1 comparison this ledger exists for (`sota-code-security` rules/11 §2.7,
    # `sota-observability` rules/05 §8a).
    unmarked = []
    for f in files:
        tree = ast.parse(open(f, encoding="utf-8").read())
        for blk in [n for n in tree.body if isinstance(n, ast.If)
                    and ast.unparse(n.test).startswith("__name__ ==")]:
            names = [getattr(c.func, "id", "") for c in ast.walk(blk) if isinstance(c, ast.Call)]
            if "report_on_exit" in names and "note_complete" not in names:
                unmarked.append(os.path.basename(f))
    if unmarked:
        sys.exit("FAIL: records a duration but never calls note_complete(), so an aborted "
                 "run is indistinguishable from a measurement in results/durations.tsv: "
                 + ", ".join(sorted(set(unmarked))))
    marked = sum(1 for f in files if "report_on_exit" in open(f, encoding="utf-8").read())
    print(f"  ledger check: all {marked} duration-recording runners mark completion\n")

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
        except SystemExit as e:
            # PRINT THE MESSAGE. A guard that fires because the runner needs args and one
            # that fires on EVERY run are both SystemExit, and this line used to render
            # them identically as "ok". run-adjudication.py was dead from 2026-08-29 to
            # 2026-09-04 behind exactly that "ok" — its ablation target had moved to
            # another file. This harness still cannot FAIL on it (a usage exit is
            # legitimate), so the least it can do is show what the guard said.
            msg = str(e).splitlines()[0][:60] if str(e).strip() else "usage/args"
            verdict = f"ok    (exited: {msg})"
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
