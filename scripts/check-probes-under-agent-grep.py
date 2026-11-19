#!/usr/bin/env python3
"""check-probes-under-agent-grep.py — does a checklist probe give the same verdict when `grep` is an
agent's shell function rather than the grep binary? A release-time check, run locally (ROADMAP 95).

WHY. In an agent's shell, `grep` can be a function: Claude Code's shell snapshot defines one that
runs ugrep with `-G --ignore-files --hidden -I` and a list of excluded directories. CI runs every
probe against its fixtures with the real grep (check-probe-fixtures.py), so a probe that an agent
pastes into its own shell can answer differently with nothing to show it. Measured 2026-11-13 over
3,828 fixture cases: the real grep passed all of them; under the function 12 probes gave a wrong
verdict (3 known-bad trees printed nothing, 9 known-good trees printed a "missing gate" line). Each
fix is one word (`command grep`). Prefixing all ~2,000 probes was rejected as a context cost every
reader pays; this check finds the few instead (operator decision 2026-11-19, ROADMAP 95 option b).
CI cannot run it: the function calls the agent's own binary.

WHAT IT DOES. For every runnable probe with fixtures, each case (bad/, good/) runs three ways, in a
fresh copy of the case with LC_ALL=C and HOME set to the copy, judged by check-probe-fixtures.py's
own rule (.expect as a set of lines, else bad/ must print and good/ must not):
  binary     bash -c PROBE                                   what CI runs
  wrap-bash  bash: the snapshot's grep function, then PROBE  isolates the grep program
  wrap-zsh   zsh -f: source the snapshot, then PROBE         the agent's shell as a whole
A FLIP is a case the binary arm passes and a wrapped arm does not. An .expect case that matches once
a leading `./` is removed from each line is counted apart (ugrep prints `src/x`, grep `./src/x`). A case the binary arm fails is
the fixture gate's finding, counted here but not a flip.

USAGE
  check-probes-under-agent-grep.py [--snapshot FILE] [--jobs N] [RULES_FILE ...]
  check-probes-under-agent-grep.py --self-test
The snapshot defaults to the newest ${CLAUDE_CONFIG_DIR:-~/.claude}/shell-snapshots/*.sh that
defines `function grep {`. Sourcing it runs it: pass only your own snapshot.
Exit 0 = no flip; 1 = a flip (fix that probe: `command grep`, or a pattern both read alike);
2 = nothing was compared (no snapshot with a grep function, no probes, or the self-test's control
failed) — not a pass.
"""
import glob
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("cpf", os.path.join(ROOT, "scripts", "check-probe-fixtures.py"))
cpf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cpf)

GREP_FUNC = re.compile(r"^function grep \{.*?^\}\n", re.S | re.M)
ARMS = ("binary", "wrap-bash", "wrap-zsh")


def find_snapshot():
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    for f in sorted(glob.glob(os.path.join(base, "shell-snapshots", "*.sh")), key=os.path.getmtime,
                    reverse=True):
        try:
            with open(f, encoding="utf-8") as fh:
                if GREP_FUNC.search(fh.read()):
                    return f
        except OSError:
            continue
    return None


def load_func(snapshot):
    with open(snapshot, encoding="utf-8") as fh:
        m = GREP_FUNC.search(fh.read())
    return m.group(0).replace("function grep {", "grep() {", 1) if m else None


def run(arm, cmd, case_dir, snapshot, func_bash):
    with tempfile.TemporaryDirectory() as tmp:
        work = os.path.join(tmp, "case")
        shutil.copytree(case_dir, work, symlinks=True, ignore=shutil.ignore_patterns(*cpf.HARNESS_FILES))
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": work, "LC_ALL": "C"}
        if arm == "binary":
            argv = ["bash", "-c", cmd]
        elif arm == "wrap-bash":
            argv = ["bash", "-c", func_bash + "\n" + cmd]
        else:
            argv = ["zsh", "-f", "-c", "source " + shlex_quote(snapshot) + " >/dev/null 2>&1\n" + cmd]
        try:
            # the probes ARE shell: repo-tracked text that passed ccp.skip_reason()'s read-only allowlist,
            # the fixture gate's own trust model; the snapshot is the operator's own file
            r = subprocess.run(argv, cwd=work, env=env, capture_output=True, text=True, timeout=60,  # noqa: S603
                               stdin=subprocess.DEVNULL, check=False)
        except subprocess.TimeoutExpired:
            return 124, ""
    return r.returncode, r.stdout


def shlex_quote(s):
    return "'" + s.replace("'", "'\\''") + "'"


def verdict(rc, out, case_dir, want_output):
    if rc not in (0, 1, 123):
        return "rc%d" % rc
    exp = os.path.join(case_dir, ".expect")
    if os.path.exists(exp):
        with open(exp, encoding="utf-8") as fh:
            want = fh.read().strip()
        got, exp_lines = sorted(out.strip().splitlines()), sorted(want.splitlines())
        if got == exp_lines:
            return "ok"
        # ugrep prints `src/x` where grep prints `./src/x`: the same hits, read the same by an
        # auditor. Counted apart, never as a flip (2026-11-19: 80 of 80 .expect "flips" were this).
        strip = lambda ls: sorted(l[2:] if l.startswith("./") else l for l in ls)
        return "ok-prefix" if strip(got) == strip(exp_lines) else "expect-mismatch"
    if want_output and not out.strip():
        return "bad-silent"
    if not want_output and out.strip():
        return "good-flagged"
    return "ok"


def compare(files, snapshot, jobs, arms):
    func_bash = load_func(snapshot)
    probes = cpf.runnable_probes(files)
    work = []
    for pid, (rf, span) in sorted(probes.items()):
        d = cpf.fixture_dir(rf, pid)
        for case, want in (("bad", True), ("good", False)):
            cd = os.path.join(d, case)
            if os.path.isdir(cd):
                work.append((pid, rf, span, case, cd, want))

    def one(j):
        pid, rf, span, case, cd, want = j
        cmd = cpf.ccp.strip_devnull_err(cpf.ccp.fill_placeholders(span))  # the gate's own, quote-aware
        row = {"id": pid, "file": rf, "case": case, "probe": span}
        for arm in arms:
            rc, out = run(arm, cmd, cd, snapshot, func_bash)
            row[arm] = verdict(rc, out, cd, want)
        return row

    with ThreadPoolExecutor(max_workers=jobs) as ex:
        return list(ex.map(one, work)), len(probes)


def report(rows, nprobes, arms):
    print("%d probes · %d fixture cases · arms: %s" % (nprobes, len(rows), ", ".join(arms)))
    for arm in arms:
        print("  %-9s ok %d of %d" % (arm, sum(r[arm] in ("ok", "ok-prefix") for r in rows), len(rows)))
    binfail = [r for r in rows if r["binary"] != "ok"]
    flips = [r for r in rows if r["binary"] == "ok"
             and any(r[a] not in ("ok", "ok-prefix") for a in arms if a != "binary")]
    prefix = [r for r in rows if r["binary"] == "ok" and r not in flips
              and any(r[a] == "ok-prefix" for a in arms if a != "binary")]
    if prefix:
        print("  %d case(s) differ only by a leading ./ on the printed path (not a flip)" % len(prefix))
    if binfail:
        print("  %d case(s) fail with the real grep too: check-probe-fixtures.py's finding, not a flip"
              % len(binfail))
    print("FLIPS: %d case(s) in %d probe(s)" % (len(flips), len({r["id"] for r in flips})))
    for r in flips:
        arms_bad = ", ".join("%s=%s" % (a, r[a]) for a in arms if a != "binary" and r[a] != "ok")
        print("  FLIP %s %s/ [%s]: %s" % (r["file"], r["case"], arms_bad, r["probe"][:120]))
    if flips:
        print("Fix: prefix that probe's grep stages with `command` (the wrapper's ugrep reads some "
              "patterns and directories differently), or use a pattern both read alike.")
    return flips


def self_test():
    """A wrapper that discards all output must flip every bad/ case; one that calls the real grep
    must flip nothing. Over one rules file's probes, so it runs in seconds."""
    files = cpf.git_files("skills/sota-shell-scripting/rules/*.md")
    probes = cpf.runnable_probes(files)
    if not probes:
        print("self-test: FAILED (no probes found to test with)")
        return 2
    fails = 0
    with tempfile.TemporaryDirectory() as d:
        silent, passthru = os.path.join(d, "silent.sh"), os.path.join(d, "pass.sh")
        with open(silent, "w", encoding="utf-8") as fh:
            fh.write("function grep {\n  :\n}\n")
        with open(passthru, "w", encoding="utf-8") as fh:
            fh.write("function grep {\n  command grep \"$@\"\n}\n")
        arms = ("binary", "wrap-bash")
        rows, _ = compare(files, silent, 8, arms)
        bad = [r for r in rows if r["case"] == "bad" and r["binary"] == "ok"]
        if not bad or any(r["wrap-bash"] == "ok" for r in bad if r["probe"].startswith("grep")):
            fails += 1
            print("FAIL a silencing wrapper did not flip the bad/ cases (%d bad cases)" % len(bad))
        rows, _ = compare(files, passthru, 8, arms)
        flipped = [r for r in rows if r["binary"] == "ok" and r["wrap-bash"] != "ok"]
        if flipped:
            fails += 1
            print("FAIL a pass-through wrapper flipped %d case(s): %s" % (len(flipped), flipped[0]["probe"][:80]))
        if find_snapshot_in(d) != os.path.join(d, "shell-snapshots", "x.sh"):
            fails += 1
            print("FAIL snapshot discovery did not find the newest file defining grep")
    print("self-test:", "ok" if not fails else "FAILED %d" % fails)
    return 1 if fails else 0


def find_snapshot_in(base):
    os.makedirs(os.path.join(base, "shell-snapshots"), exist_ok=True)
    with open(os.path.join(base, "shell-snapshots", "y.sh"), "w", encoding="utf-8") as fh:
        fh.write("alias ll='ls -l'\n")
    with open(os.path.join(base, "shell-snapshots", "x.sh"), "w", encoding="utf-8") as fh:
        fh.write("function grep {\n  :\n}\n")
    os.utime(os.path.join(base, "shell-snapshots", "y.sh"), (2e9, 2e9))  # newer, but no grep
    old = os.environ.get("CLAUDE_CONFIG_DIR")
    os.environ["CLAUDE_CONFIG_DIR"] = base
    try:
        return find_snapshot()
    finally:
        if old is None:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        else:
            os.environ["CLAUDE_CONFIG_DIR"] = old


def main(argv):
    if "-h" in argv or "--help" in argv:
        print(__doc__)
        return 0
    if "--self-test" in argv:
        return self_test()
    snapshot, jobs, files, out_json = None, 8, [], None
    it = iter(argv)
    for a in it:
        if a == "--snapshot":
            snapshot = next(it, None)
        elif a == "--jobs":
            jobs = int(next(it, "8"))
        elif a == "--json":
            out_json = next(it, None)
        elif a.startswith("-"):
            print("unknown option %s" % a)
            return 2
        else:
            files.append(a)
    snapshot = snapshot or find_snapshot()
    if not snapshot or not load_func(snapshot):
        print("SKIPPED: no shell snapshot defining `function grep {` (looked in "
              "${CLAUDE_CONFIG_DIR:-~/.claude}/shell-snapshots/); nothing was compared — not a pass")
        return 2
    arms = ARMS if shutil.which("zsh") else ARMS[:2]
    if len(arms) < 3:
        print("note: zsh not found, the wrap-zsh arm is skipped")
    files = files or cpf.git_files("skills/*/rules/*.md")
    rows, nprobes = compare(files, snapshot, jobs, arms)
    if not rows:
        print("FAIL: no fixture case ran (an empty scope verifies nothing)")
        return 2
    print("snapshot: %s" % snapshot)
    flips = report(rows, nprobes, arms)
    if out_json:
        with open(out_json, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, indent=0)
    return 1 if flips else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
