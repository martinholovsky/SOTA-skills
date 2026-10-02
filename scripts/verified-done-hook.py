#!/usr/bin/env python3
"""verified-done-hook.py — refuse "done" on a changed tree until a verification command has
passed on exactly that tree. A Claude Code hook (opt-in: it is NOT in hooks/hooks.json).

WHY. The library tells the model to "claim done only with evidence" (router principle 6), and
until now nothing could make it: the README said "no mechanism forces a model to run a skill"
and an analysis read that as "the library cannot enforce anything". The host can. Claude Code
runs this script on four hook events, and a Stop hook that returns {"decision": "block"} stops
the turn from ending (code.claude.com/docs/en/hooks, verified 2026-10-02). That moves one
non-negotiable from instruction to enforcement; the rest of the library stays advisory.

WHAT IT RECORDS (an evidence ledger under .git/, never in the worktree):
  SessionStart        the tree the session began on (the baseline)
  PostToolUse  Bash   a verification command that exited 0, and the tree it ran on
  PostToolUseFailure  the same command when it failed ("Exit code N" in `error`)
WHAT IT ENFORCES, at Stop:
  tree unchanged since the session began        -> allow (a question, a read, a review)
  latest verification on the CURRENT tree passed -> allow
  otherwise                                      -> block, saying which case it is
A "tree" is the id `git write-tree` gives the whole working tree (tracked + untracked, minus
ignored) through a throwaway index, so any edit after the passing run invalidates it.

WHAT COUNTS AS VERIFICATION: a command matching a test/gate runner (DEFAULT_VERIFY, or the
regexes in .sota/verify-commands, one per line) that is NOT piped, chained with `;`/`||`, or
backgrounded — `pytest | tail` reports tail's status (sota-shell-scripting rules/01 §3), so it
is recorded as IGNORED and named in the block reason. `cd x && pytest` counts.

IT NEVER TRAPS A SESSION: background tasks pending -> allow (the session is paused, not done);
after MAX_BLOCKS consecutive blocks on one tree -> allow with a visible systemMessage that the
turn ended UNVERIFIED (Claude Code overrides a block after 8 anyway); not a git repo, git
missing, or SOTA_VERIFIED_DONE=off -> allow. Every internal error allows and says so on
stderr: a broken gate must not brick the editor (fail-open, loudly — this is a guard, not a
security boundary; a determined model can still run a fake command matching the pattern).

Install (user or project settings.json):
  "hooks": {
    "SessionStart":       [{"hooks": [{"type": "command", "command": "python3 /ABS/PATH/scripts/verified-done-hook.py"}]}],
    "PostToolUse":        [{"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 /ABS/PATH/scripts/verified-done-hook.py"}]}],
    "PostToolUseFailure": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 /ABS/PATH/scripts/verified-done-hook.py"}]}],
    "Stop":               [{"hooks": [{"type": "command", "command": "python3 /ABS/PATH/scripts/verified-done-hook.py"}]}]
  }
Self-test: python3 scripts/verified-done-hook.py --self-test
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

MAX_BLOCKS = int(os.environ.get("SOTA_VERIFIED_DONE_MAX_BLOCKS", "3"))
DEFAULT_VERIFY = [
    r"(^|/)check-invariants\.sh\b", r"\bpre-commit run\b",
    r"\bpytest\b", r"\bpython3? -m (pytest|unittest)\b", r"\b(tox|nox)\b",
    r"\b(npm|pnpm|yarn|bun)( run)? test\b", r"\bvitest\b", r"\bjest\b",
    r"\bcargo (test|nextest)\b", r"\bgo test\b", r"\bdotnet test\b",
    r"\bmake (test|check)\b", r"\bjust test\b", r"\bctest\b",
    r"\bmvn\b.*\b(test|verify)\b", r"\bgradlew?\b.*\b(test|check)\b",
    r"\b(rspec|phpunit|pest)\b", r"\bbundle exec (rspec|rake)\b",
]
UNSAFE = re.compile(r"(?<![|])\|(?![|])|;|\|\||(?<![&])&(?![&])")  # pipe, ;, ||, background &


def git(cwd, *args, env=None):
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True,
                          env=env, timeout=60)


def tree_id(cwd):
    """The id of the whole working tree as git would commit it, via a throwaway index."""
    gd = git(cwd, "rev-parse", "--absolute-git-dir")
    if gd.returncode != 0:
        return None, None
    gitdir = gd.stdout.strip()
    tmp = tempfile.mkdtemp(prefix="sota-vd-")
    try:
        idx = os.path.join(tmp, "index")
        real = os.path.join(gitdir, "index")
        if os.path.exists(real):
            shutil.copyfile(real, idx)          # seeded copy: add -A only rehashes changes
        env = dict(os.environ, GIT_INDEX_FILE=idx)
        if git(cwd, "add", "-A", env=env).returncode != 0:
            return gitdir, None
        wt = git(cwd, "write-tree", env=env)
        return gitdir, (wt.stdout.strip() if wt.returncode == 0 else None)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def ledger_path(gitdir, session):
    key = hashlib.sha256((session or "no-session").encode()).hexdigest()[:16]
    d = os.path.join(gitdir, "sota-verified-done")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, key + ".json")


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, path)                       # atomic: a crashed write leaves the old ledger


def verify_patterns(cwd):
    extra = os.path.join(cwd, ".sota", "verify-commands")
    pats = list(DEFAULT_VERIFY)
    if os.path.exists(extra):
        with open(extra, encoding="utf-8") as f:
            pats += [l.strip() for l in f if l.strip() and not l.startswith("#")]
    return [re.compile(p) for p in pats]


def classify(cmd, cwd):
    """'verify' | 'ignored' (a verifier, but its exit status is not its own) | None."""
    if not any(p.search(cmd) for p in verify_patterns(cwd)):
        return None
    return "ignored" if UNSAFE.search(cmd) else "verify"


def emit(obj):
    if obj:
        sys.stdout.write(json.dumps(obj))


def handle(ev):
    if os.environ.get("SOTA_VERIFIED_DONE", "").lower() == "off":
        return None
    cwd = ev.get("cwd") or os.getcwd()
    name = ev.get("hook_event_name", "")
    gitdir, tree = tree_id(cwd)
    if not gitdir or not tree:
        return None                              # not a repo / git missing: nothing to judge
    path = ledger_path(gitdir, ev.get("session_id"))
    led = load(path)
    led.setdefault("baseline", tree)             # lazy baseline if SessionStart was missed

    if name == "SessionStart":
        led["baseline"] = tree
    elif name in ("PostToolUse", "PostToolUseFailure") and ev.get("tool_name") == "Bash":
        cmd = (ev.get("tool_input") or {}).get("command", "")
        kind = classify(cmd, cwd)
        if kind:
            ok = name == "PostToolUse"
            led["last"] = {"tree": tree, "ok": ok, "kind": kind, "cmd": cmd[:200]}
            if kind == "verify":
                led.setdefault("runs", []).append({"tree": tree, "ok": ok, "cmd": cmd[:200]})
                led["runs"] = led["runs"][-50:]
    elif name == "Stop":
        save(path, led)
        return stop_verdict(ev, led, tree, path)
    save(path, led)
    return None


def stop_verdict(ev, led, tree, path):
    if ev.get("background_tasks"):
        return None                              # paused waiting on work, not done
    if tree == led.get("baseline"):
        led["blocks"] = 0; save(path, led)
        return None
    runs = [r for r in led.get("runs", []) if r["tree"] == tree]
    if runs and runs[-1]["ok"]:
        led["blocks"] = 0; save(path, led)
        return None
    blocks = led.get("blocks", 0) + 1 if led.get("blocked_tree") == tree else 1
    led["blocks"], led["blocked_tree"] = blocks, tree
    save(path, led)
    if blocks > MAX_BLOCKS:
        return {"systemMessage": "verified-done: ending UNVERIFIED after %d blocks — the tree "
                "changed and no verification command passed on it." % MAX_BLOCKS}
    if runs:
        why = "the last verification on this tree FAILED (%s)" % runs[-1]["cmd"]
    elif led.get("last", {}).get("kind") == "ignored" and led["last"]["tree"] == tree:
        why = ("`%s` was not counted: it is piped, chained with ; or ||, or backgrounded, so its "
               "exit status is not the verifier's. Run it alone" % led["last"]["cmd"])
    elif led.get("runs"):
        why = "files changed after the last passing verification"
    else:
        why = "the tree changed this session and no verification command has run"
    return {"decision": "block",
            "reason": "verified-done: %s. Run the project's tests or gates on the current tree "
                      "(unpiped) and report the result, or say plainly that it is unverified and "
                      "why. (%d/%d)" % (why, blocks, MAX_BLOCKS)}


def main():
    if sys.argv[1:] == ["--self-test"]:
        return self_test()
    try:
        ev = json.loads(sys.stdin.read() or "{}")
        emit(handle(ev))
    except Exception as e:                       # fail open, loudly: never brick the session
        sys.stderr.write("verified-done-hook: internal error, allowing: %r\n" % (e,))
    return 0


def self_test():
    """Each case is a known-good or known-bad session; a gate that never blocks fails here."""
    tmp = tempfile.mkdtemp(prefix="sota-vd-test-")
    fails = 0
    try:
        sh = lambda *a: subprocess.run(a, cwd=tmp, capture_output=True, check=True)
        sh("git", "init", "-q"); sh("git", "config", "user.email", "t@t"); sh("git", "config", "user.name", "t")
        open(os.path.join(tmp, "a.txt"), "w").write("1\n")
        sh("git", "add", "-A"); sh("git", "commit", "-qm", "init")
        def ev(name, **kw):
            return dict({"hook_event_name": name, "cwd": tmp, "session_id": "self-test"}, **kw)
        def bash(cmd, ok=True):
            return ev("PostToolUse" if ok else "PostToolUseFailure", tool_name="Bash",
                      tool_input={"command": cmd})
        def edit(text):
            open(os.path.join(tmp, "a.txt"), "w").write(text)
        def check(label, got, want):
            nonlocal fails
            v = "block" if got and got.get("decision") == "block" else \
                ("unverified" if got and "systemMessage" in got else "allow")
            ok = v == want
            fails += not ok
            print("  [%s] %s: %s%s" % ("ok" if ok else "FAIL", label, v, "" if ok else " (want %s)" % want))
        handle(ev("SessionStart"))
        check("no change -> allow", handle(ev("Stop")), "allow")
        edit("2\n")
        check("changed, nothing run -> block", handle(ev("Stop")), "block")
        handle(bash("pytest -q | tail -3"))
        r = handle(ev("Stop"))
        check("piped verifier is not evidence -> block", r, "block")
        check("  ...and the reason names the pipe", {"decision": "block"} if r and "piped" in r["reason"] else None, "block")
        handle(bash("pytest -q", ok=False))
        check("failing verifier -> block", handle(ev("Stop")), "block")
        handle(bash("cd sub && pytest -q"))
        check("passing verifier on this tree -> allow", handle(ev("Stop")), "allow")
        edit("3\n")
        check("edit after the passing run -> block", handle(ev("Stop")), "block")
        handle(bash("ls -la"))
        check("non-verifier command is not evidence -> block", handle(ev("Stop")), "block")
        check("background task pending -> allow", handle(ev("Stop", background_tasks=[{"id": "x"}])), "allow")
        for _ in range(MAX_BLOCKS):
            handle(ev("Stop"))
        check("after MAX_BLOCKS -> ends with a visible UNVERIFIED message", handle(ev("Stop")), "unverified")
        os.environ["SOTA_VERIFIED_DONE"] = "off"
        check("SOTA_VERIFIED_DONE=off -> allow", handle(ev("Stop")), "allow")
        del os.environ["SOTA_VERIFIED_DONE"]
        nongit = tempfile.mkdtemp(prefix="sota-vd-nongit-")
        check("not a git repo -> allow", handle({"hook_event_name": "Stop", "cwd": nongit}), "allow")
        shutil.rmtree(nongit, ignore_errors=True)
        dirty = git(tmp, "status", "--porcelain").stdout
        check("ledger lives outside the worktree", None if "sota" not in dirty else {"decision": "block"}, "allow")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("SELF-TEST %s (%d failure(s))" % ("PASS" if not fails else "FAIL", fails))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
