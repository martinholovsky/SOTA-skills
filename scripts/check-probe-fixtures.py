#!/usr/bin/env python3
"""check-probe-fixtures.py — prove each audit-checklist probe DETECTS what it claims (invariant 44).

WHY. Invariant 43 proves a checklist item cites the section it audits; check-checklist-probes.py
proves its `grep` probe runs. Neither proves the probe catches anything: "a probe that runs and
answers the wrong question (an unquoted `src/**/` that searches one level in bash, a regex that
misses a case)" — that script's own docstring — "only a known-bad fixture per probe catches".

WHAT IT DOES. Every probe that check-checklist-probes.py would run (same extraction, same skip
rules) gets an id: `<rules-file stem>#<sha1 of the normalised probe text, 10 hex>`. Its fixtures
live in scripts/probe-fixtures/<skill>/<rules-file stem>/<hash>/ as two directories:
  bad/   a minimal tree the probe must flag   -> stdout must be NON-empty
  good/  a near-miss the probe must not flag  -> stdout must be empty
An optional `.expect` file in either directory replaces that rule with an exact expected stdout
(for probes that always print, e.g. a count). The probe runs under bash with the case directory as
its working directory; `<placeholder>`s become the file `empty`, which a fixture may provide. Exit
status must be 0, 1 or (xargs) 123 — an rc 2 never searched anything and fails the fixture.

THE RATCHET. scripts/probe-fixture-baseline.json lists runnable probes that have no fixtures yet.
  F1  a runnable probe with no fixtures that is not in the baseline   (a new probe ships proven)
  F2  a fixture that fails: bad printed nothing, good printed something, or rc 2
  F3  a baseline entry that now has fixtures, or whose probe no longer exists  (--tighten)
  F4  a fixture directory whose probe no longer exists: the probe was edited, so re-prove it
  F5  the baseline grew against the merge base
Because the id hashes the probe text, editing a probe orphans its fixture (F4) and, if the new
text is unproven, raises F1 — an edited probe is re-proven, never grandfathered.

USAGE  python3 scripts/check-probe-fixtures.py            check (exit 1 on F1-F5)
       python3 scripts/check-probe-fixtures.py --structure  F1, F3-F5 only (invariant 44: fast)
       python3 scripts/check-probe-fixtures.py --tighten  rewrite the baseline to what is needed
       python3 scripts/check-probe-fixtures.py --list [SKILL]  print unproven probes with ids
       python3 scripts/check-probe-fixtures.py --self-test
"""
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join("scripts", "probe-fixtures")
BASELINE = os.path.join("scripts", "probe-fixture-baseline.json")
_spec = importlib.util.spec_from_file_location("ccp", os.path.join(ROOT, "scripts", "check-checklist-probes.py"))
ccp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ccp)


def git_files(pattern):
    r = subprocess.run(["git", "ls-files", pattern], capture_output=True, text=True, check=False)
    return sorted(f for f in r.stdout.split() if f)


def probe_id(rules_file, span):
    stem = os.path.splitext(os.path.basename(rules_file))[0]
    return "%s#%s" % (stem, hashlib.sha1(span.encode("utf-8")).hexdigest()[:10])


def runnable_probes(files):
    """{id: (rules_file, span)} for every probe check-checklist-probes.py would run."""
    out = {}
    for f in files:
        with open(f, encoding="utf-8") as fh:
            for span in ccp.probes_in(fh.read()):
                if ccp.skip_reason(span) is None:
                    out[probe_id(f, span)] = (f, span)
    return out


def fixture_dir(rules_file, pid):
    skill = rules_file.split("/")[1]
    stem, h = pid.split("#")
    return os.path.join(FIX, skill, stem, h)


HARNESS_FILES = (".expect", ".keep")  # the harness's own files: a `grep -r .` must never read them


def run_case(span, case_dir):
    cmd = ccp.DEVNULL_ERR.sub("", ccp.fill_placeholders(span))
    # A shell is the point: the probes ARE shell pipelines. Their text is repo-tracked and has
    # already passed ccp.skip_reason()'s read-only allowlist (no writes, no rm/curl/-exec), the
    # same trust model as check-checklist-probes.py. 20 s per case: a fixture is a few files.
    # The probe runs in a COPY of the case without the harness's files, with HOME set to that
    # copy's absolute path: run in place, `grep -r .` read `.expect` and a relative HOME broke `~`.
    with tempfile.TemporaryDirectory() as tmp:
        work = os.path.join(tmp, "case")
        try:
            shutil.copytree(case_dir, work, symlinks=True, ignore=shutil.ignore_patterns(*HARNESS_FILES))
        except OSError as e:
            return 127, "", "cannot copy the fixture: %s" % e
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": work, "LC_ALL": "C"}
        try:
            r = subprocess.run(["bash", "-c", cmd], cwd=work, env=env, capture_output=True, text=True,
                               timeout=20, stdin=subprocess.DEVNULL, check=False)
        except subprocess.TimeoutExpired:
            return 124, "", "timed out after 20 s"
    return r.returncode, r.stdout, r.stderr


def check_case(span, case_dir, want_output):
    rc, out, err = run_case(span, case_dir)
    if rc not in (0, 1, 123):
        return "rc %d: %s" % (rc, (err.strip().splitlines() or [""])[-1][:140])
    exp = os.path.join(case_dir, ".expect")
    if os.path.exists(exp):
        with open(exp, encoding="utf-8") as fh:
            want = fh.read().strip()
        # as a multiset of lines: `grep -r` walks directories in filesystem order, which differs
        # between the macOS and Linux runners (a two-file ruby fixture failed on GNU alone)
        if sorted(out.strip().splitlines()) == sorted(want.splitlines()):
            return None
        return "stdout %r, .expect %r" % (out.strip()[:80], want[:80])
    if want_output and not out.strip():
        return "the known-bad tree printed nothing: the probe misses what it claims to catch"
    if not want_output and out.strip():
        return "the known-good tree printed %r: the probe flags a near-miss" % out.strip().splitlines()[0][:100]
    return None


def fixture_ids():
    out = set()
    for root, dirs, _ in os.walk(FIX):
        if "bad" in dirs and "good" in dirs:
            rel = os.path.relpath(root, FIX).split(os.sep)
            if len(rel) == 3:
                out.add("%s#%s" % (rel[1], rel[2]))
    return out


def load_baseline(text=None):
    if text is None:
        if not os.path.exists(BASELINE):
            return None
        with open(BASELINE, encoding="utf-8") as fh:
            text = fh.read()
    return set(json.loads(text)["unproven"])


def state():
    probes = runnable_probes(git_files("skills/*/rules/*.md"))
    have = fixture_ids()
    return probes, have


def merge_base_baseline():
    mb = subprocess.run(["git", "merge-base", "HEAD", "origin/main"], capture_output=True, text=True)
    if mb.returncode != 0 or not mb.stdout.strip():
        return None
    old = subprocess.run(["git", "show", "%s:%s" % (mb.stdout.strip(), BASELINE)], capture_output=True, text=True)
    return load_baseline(old.stdout) if old.returncode == 0 else None


def check(run=True):
    probes, have = state()
    base = load_baseline()
    if base is None:
        print("FAIL: %s missing — the ratchet has nothing to compare against" % BASELINE)
        return 1
    bad = []
    for pid, (f, span) in sorted(probes.items()):
        if pid in have:
            if not run:
                continue
            d = fixture_dir(f, pid)
            for case, want in (("bad", True), ("good", False)):
                why = check_case(span, os.path.join(d, case), want)
                if why:
                    bad.append("F2 %s %s: %s — %s" % (pid, case, why, span[:90]))
        elif pid not in base:
            bad.append("F1 %s (%s): a probe with no fixtures — add %s/{bad,good}/ — %s"
                       % (pid, f, fixture_dir(f, pid), span[:90]))
    for pid in sorted(base):
        if pid in have or pid not in probes:
            bad.append("F3 stale baseline entry %s — run `python3 scripts/check-probe-fixtures.py --tighten`" % pid)
    for pid in sorted(have - set(probes)):
        bad.append("F4 %s: fixtures for a probe that no longer exists (edited?) — re-key or remove them" % pid)
    mb = merge_base_baseline()
    if mb is not None and len(base) > len(mb):
        bad.append("F5 the baseline grew against the merge base: %d > %d" % (len(base), len(mb)))
    proven = len([p for p in probes if p in have])
    print("SCOPE %d" % len(probes))
    for b in bad:
        print(b)
    if not probes:
        print("FAIL: no runnable probes (an empty scope verifies nothing)")
        return 1
    if bad:
        return 1
    print("    ok (%d runnable probes: %d with fixtures%s, %d baselined unproven; growth %s)"
          % (len(probes), proven, " (all pass)" if run else " (structure only; CI runs them)", len(base),
             "checked against the merge base" if mb is not None else "not checked"))
    return 0


def tighten():
    probes, have = state()
    base = load_baseline()
    if base is None:
        print("no baseline to tighten; refusing to create one silently")
        return 1
    new = sorted(p for p in base if p in probes and p not in have)
    with open(BASELINE, "w", encoding="utf-8") as fh:
        json.dump({"_note": "invariant 44 ratchet: runnable checklist probes with no fixtures. Entries may "
                            "only be REMOVED; regenerate with `python3 scripts/check-probe-fixtures.py --tighten`.",
                   "unproven": new}, fh, indent=1)
        fh.write("\n")
    print("baseline tightened: %d -> %d" % (len(base), len(new)))
    return 0


def list_unproven(skill=None):
    probes, have = state()
    for pid, (f, span) in sorted(probes.items()):
        if pid not in have and (skill is None or f.split("/")[1] == skill):
            print("%s\t%s\t%s" % (pid, fixture_dir(f, pid), span))
    return 0


def self_test():
    fails = 0
    with tempfile.TemporaryDirectory() as d:
        span = "grep -rn 'eval(' --include='*.py' ."
        b, g = os.path.join(d, "bad"), os.path.join(d, "good")
        os.makedirs(b); os.makedirs(g)
        with open(os.path.join(b, "a.py"), "w") as fh:
            fh.write("eval(x)\n")
        with open(os.path.join(g, "a.py"), "w") as fh:
            fh.write("evaluate(x)\n")
        if check_case(span, b, True) is not None:
            fails += 1; print("FAIL known-bad not flagged")
        if check_case(span, g, False) is not None:
            fails += 1; print("FAIL known-good flagged")
        if check_case(span, g, True) is None:
            fails += 1; print("FAIL a bad case that prints nothing passed")
        if check_case("grep -rnE '(' .", b, True) is None:
            fails += 1; print("FAIL an rc-2 probe passed")
        with open(os.path.join(g, ".expect"), "w") as fh:
            fh.write("0")
        if check_case("grep -rn 'eval(' . | wc -l | tr -d ' '", g, False) is not None:
            fails += 1; print("FAIL .expect exact match")
        # the harness's own .expect must be invisible to the probe: it holds the text `0`
        if check_case("grep -rl '0' . | wc -l | tr -d ' '", g, False) is not None:
            fails += 1; print("FAIL a probe read the harness's .expect file")
        os.remove(os.path.join(g, ".expect"))
        # a quoted <tag> is pattern text, an unquoted one is a file operand
        with open(os.path.join(b, "p.csproj"), "w") as fh:
            fh.write("<NoWarn>CS8602</NoWarn>\n")
        if check_case("grep -rn '<NoWarn>' --include='*.csproj' .", b, True) is not None:
            fails += 1; print("FAIL a quoted <tag> was rewritten to a placeholder")
        if ccp.fill_placeholders("grep -n 'x' <file>") != "grep -n 'x' empty":
            fails += 1; print("FAIL an unquoted <placeholder> was not filled")
        if ccp.fill_placeholders("grep -n \"\\\"<all_urls>\" <file>") != "grep -n \"\\\"<all_urls>\" empty":
            fails += 1; print("FAIL an escaped quote ended the quoted pattern early")
        # .expect is a multiset: directory traversal order differs between platforms
        with open(os.path.join(b, "z.py"), "w") as fh:
            fh.write("eval(y)\n")
        with open(os.path.join(b, ".expect"), "w") as fh:
            fh.write("./z.py\n./a.py\n")
        if check_case("grep -rl 'eval(' --include='*.py' .", b, True) is not None:
            fails += 1; print("FAIL .expect compared in traversal order")
        # `~` is the case copy: a relative HOME made `~/.npmrc` resolve to <case>/<case>/.npmrc
        os.remove(os.path.join(b, ".expect"))
        with open(os.path.join(b, ".npmrc"), "w") as fh:
            fh.write("_authToken=literal\n")
        if check_case("grep -n '_authToken=[^$]' ~/.npmrc", b, True) is not None:
            fails += 1; print("FAIL ~ did not resolve to the case directory")
    # a span keeps the spaces inside a line: Gemfile.lock indents a locked gem by exactly four
    if ccp.probes_in("x\n## Audit checklist\n- `grep -nE '^    json \\(' Gemfile.lock`\n") != ["grep -nE '^    json \\(' Gemfile.lock"]:
        fails += 1; print("FAIL probes_in() collapsed the spaces inside a probe")
    print("self-test:", "ok" if not fails else "FAILED %d" % fails)
    return 1 if fails else 0


if __name__ == "__main__":
    os.chdir(ROOT)
    a = sys.argv[1:]
    if "--self-test" in a:
        sys.exit(self_test())
    if "--tighten" in a:
        sys.exit(tighten())
    if "--list" in a:
        rest = [x for x in a if x != "--list"]
        sys.exit(list_unproven(rest[0] if rest else None))
    sys.exit(check(run="--structure" not in a))
