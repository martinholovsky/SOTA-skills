#!/usr/bin/env python3
"""memory-guard-hook.py — a PreToolUse hook on Bash that asks before a command changes an agent's
memory folder.

WHY. A "move the memory into the repository and symlink it" step ran `mv` onto a path an earlier
session had already made a symlink, and the following `rm -r` deleted the only real copy of a
project's notes; it came back only from a backup (field-reported 2026-11-23,
`sota-docs-workflow` rules/06 §4). The warning was already written down. A rule that has to be
remembered loses to habit; a hook that asks does not.

WHAT IT GUARDS. Claude Code keeps auto memory in `<config>/projects/<key>/memory` (`<config>` is
$CLAUDE_CONFIG_DIR or ~/.claude), keyed by the path a session started in, and an
`autoMemoryDirectory` setting can name another folder. The guarded set is:
  - any `.claude/projects/<key>/memory` path written literally in the command;
  - the real folder behind every `<config>/projects/*/memory` (symlinks resolved, so a link from the
    key into a repository protects the repository folder too);
  - every folder an `autoMemoryDirectory` setting names: user settings, and the project settings of
    the hook's working directory.
A command is asked about when it runs rm, mv, rmdir, unlink or ln AND one of its words resolves to
a guarded folder or a path inside one (relative words resolve against the working directory).

WHAT IT DOES. It never blocks: it returns permissionDecision "ask", so the person decides. Input it
cannot parse also yields "ask", so a broken guard is loud. Any other internal error lets the
command run (exit 0, no output): a hook must never break the shell. Off with
SOTA_MEMORY_GUARD=off. `--self-test` runs the labelled cases.
"""
from __future__ import annotations

import glob
import json
import os
import re
import shlex
import sys

VERB = re.compile(r"(?:^|[\s;&|(`])(?:sudo\s+)?(?:command\s+)?(rm|mv|rmdir|unlink|ln)(?=\s)")
# A path assembled through a variable (`P=~/.claude/projects; rm -r "$P/-k/memory"`) cannot be
# resolved, so the two halves on one line count: asking about a few extra commands is the cheap side.
LITERAL = re.compile(r"\.claude/projects\b[^\n]*?memory|memory[^\n]*?\.claude/projects")

# A heredoc body is text unless a shell (or ssh) runs it: a Python heredoc that WRITES a note
# mentioning `ln -s … .claude-memory` must not ask (field report 2026-11-25: 4 of 8 asks of a guard
# were heredocs whose text named those commands). Same shape as action-rules-hook.py drop_bodies.
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1([^\n]*)\n(.*?)\n?[ \t]*\2[ \t]*(?=\n|$)", re.S)
SHELL_RUNNER = re.compile(r"(?:^|[\s;&|(])(?:sudo\s+)?(?:bash|sh|zsh|dash|ksh|ssh)\b[^\n]*$")


def drop_text_bodies(command: str) -> str:
    """The command with every heredoc body removed unless the opener line feeds it to a shell."""
    def repl(m: re.Match) -> str:
        opener = command[:m.start()].rsplit("\n", 1)[-1]
        return m.group(0) if SHELL_RUNNER.search(opener) else "<<HEREDOC" + m.group(3) + "\n"
    return HEREDOC.sub(repl, command)


REASON = (
    "This command changes an agent memory folder. Before approving, check that the session has: "
    "(1) mapped the source and destination with `ls -ld --` and `readlink --` (memory keys start with "
    "'-', so bare ls, readlink and rm read them as options), (2) found the ONE real folder with "
    "`realpath` and counted its files, (3) copied, compared with `diff -r` and counted before removing "
    "anything, and (4) not gated this step on `[ ... ] && [ ... ]` under set -e. "
    "Rule: sota-docs-workflow rules/06 §4; procedure: /sota-init data, step P3."
)


def config_dir() -> str:
    return os.path.expanduser(os.environ.get("CLAUDE_CONFIG_DIR") or "~/.claude")


def _setting_dirs(path: str) -> list[str]:
    try:
        with open(path, encoding="utf-8") as fh:
            v = json.load(fh).get("autoMemoryDirectory")
    except (OSError, ValueError, AttributeError):
        return []
    if isinstance(v, str) and (v.startswith("/") or v.startswith("~/")):
        return [os.path.expanduser(v)]
    return []   # the docs reject any other form, so it names no folder


def guarded_roots(cwd: str, home_config: str | None = None) -> set[str]:
    cfg = home_config or config_dir()
    roots: set[str] = set()
    for p in glob.glob(os.path.join(glob.escape(cfg), "projects", "*", "memory")):
        roots.add(os.path.realpath(p))
        roots.add(os.path.abspath(p))
    candidates = [os.path.join(cfg, "settings.json"), os.path.join(cfg, "settings.local.json")]
    if cwd:
        candidates += [os.path.join(cwd, ".claude", "settings.json"),
                       os.path.join(cwd, ".claude", "settings.local.json")]
    for c in candidates:
        for d in _setting_dirs(c):
            roots.add(os.path.realpath(d))
            roots.add(os.path.abspath(d))
    return {r.rstrip(os.sep) or os.sep for r in roots}


def _words(command: str) -> list[str]:
    try:
        lex = shlex.shlex(command, posix=True, punctuation_chars=";&|()<>")
        lex.whitespace_split = True
        return list(lex)
    except ValueError:          # unbalanced quotes: fall back to plain splitting
        return command.split()


def _inside(path: str, roots: set[str]) -> bool:
    return any(path == r or path.startswith(r + os.sep) for r in roots)


def decide(command: str, cwd: str, roots: set[str]) -> str | None:
    """'ask' when the command mutates (rm/mv/rmdir/unlink/ln) and names a memory folder."""
    command = drop_text_bodies(command)
    if not VERB.search(command):
        return None
    if LITERAL.search(command):
        return "ask"
    for w in _words(command):
        if not w or w.startswith("-") and not w.startswith("-/"):
            continue
        w = os.path.expanduser(w)
        p = w if os.path.isabs(w) else os.path.join(cwd or os.getcwd(), w)
        p = os.path.normpath(p)
        for cand in (p, os.path.realpath(p)):
            if _inside(cand, roots):
                return "ask"
    return None


def emit(decision: str, reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "permissionDecision": decision,
                                             "permissionDecisionReason": reason}}))


def self_test() -> int:
    import tempfile
    fails, n = [], 0
    with tempfile.TemporaryDirectory() as d:
        d = os.path.realpath(d)
        cfg = os.path.join(d, "cfg")
        repo = os.path.join(d, "repo")
        kept = os.path.join(repo, "notes-memory")
        other = os.path.join(d, "elsewhere")
        os.makedirs(os.path.join(cfg, "projects", "-a", "memory"))
        os.makedirs(os.path.join(cfg, "projects", "-b"))
        os.makedirs(kept)
        os.makedirs(os.path.join(repo, ".claude"))
        os.makedirs(other)
        os.symlink(kept, os.path.join(cfg, "projects", "-b", "memory"))   # key -> repo folder
        set_dir = os.path.join(d, "chosen")
        os.makedirs(set_dir)
        with open(os.path.join(repo, ".claude", "settings.local.json"), "w", encoding="utf-8") as fh:
            json.dump({"autoMemoryDirectory": set_dir}, fh)
        roots = guarded_roots(repo, cfg)
        mem_a = os.path.join(cfg, "projects", "-a", "memory")
        cases = [
            # (command, expected)
            (f'mv "{mem_a}" "{repo}/x" && ln -s "{repo}/x" "{mem_a}"', "ask"),   # the 2026-11-23 shape
            (f"rm -r -- {mem_a}/", "ask"),
            (f"rmdir -- {mem_a}/sota-guard-probe", "ask"),                       # /sota-init P3.6
            (f"sudo rm -rf {mem_a}", "ask"),
            (f"unlink {cfg}/projects/-b/memory", "ask"),
            ("rm notes-memory/MEMORY.md", "ask"),                                 # relative, via the link
            (f"rm -rf {set_dir}/old.md", "ask"),                                  # autoMemoryDirectory
            ('P=~/.claude/projects; rm -r "$P/-x/memory"', "ask"),               # literal form
            (f"ls -la -- {mem_a}/", None),
            (f"readlink -- {cfg}/projects/-b/memory", None),
            (f"cat {kept}/MEMORY.md", None),
            (f"rm -r {other}/build", None),                                       # verb, no memory
            ("git commit -m 'rm the memory leak'", None),                         # words only
            ("grep -rn armor src/", None),                                        # 'rm' inside a word
            (f"cp -R {kept} {other}/backup", None),                               # copy is allowed
            ("python3 - <<'PY'\nopen('N.md','a').write('ln -s ../.claude-memory ~/.claude/projects/-k/memory')\nPY", None),
            (f"cat >> notes.md <<'EOF'\nthen rm -r {mem_a}\nEOF", None),           # heredoc text only
            (f"bash <<'EOF'\nrm -r {mem_a}\nEOF", "ask"),                          # a shell runs it
            (f"ssh host <<'EOF'\nrm -rf ~/.claude/projects/-k/memory\nEOF", "ask"),
        ]
        for cmd, want in cases:
            n += 1
            got = decide(cmd, repo, roots)
            if got != want:
                fails.append(f"{cmd!r}: got {got}, want {want}")
        # fail closed on unparseable input
        n += 1
        out = _run_main_with(b"not json")
        if '"ask"' not in out:
            fails.append(f"unparseable input must ask, got {out!r}")
        # opt-out
        n += 1
        os.environ["SOTA_MEMORY_GUARD"] = "off"
        out = _run_main_with(json.dumps({"tool_input": {"command": f"rm -r {mem_a}"}}).encode())
        os.environ.pop("SOTA_MEMORY_GUARD")
        if out.strip():
            fails.append(f"SOTA_MEMORY_GUARD=off must print nothing, got {out!r}")
    for f in fails:
        print("SELF-TEST FAIL:", f, file=sys.stderr)
    print(f"memory-guard-hook self-test: {n - len(fails)}/{n} cases correct")
    return 1 if fails else 0


def _run_main_with(stdin_bytes: bytes) -> str:
    import io
    import contextlib
    buf = io.StringIO()
    old = sys.stdin
    sys.stdin = io.TextIOWrapper(io.BytesIO(stdin_bytes), encoding="utf-8")
    try:
        with contextlib.redirect_stdout(buf):
            main([])
    finally:
        sys.stdin = old
    return buf.getvalue()


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    if os.environ.get("SOTA_MEMORY_GUARD", "").lower() in ("off", "0", "false", "no"):
        return 0
    try:
        data = json.load(sys.stdin)
        command = data["tool_input"]["command"]
        if not isinstance(command, str):
            raise TypeError("command is not a string")
        cwd = data.get("cwd") if isinstance(data.get("cwd"), str) else os.getcwd()
    except Exception as e:  # fail closed: an unreadable payload must not pass silently
        emit("ask", f"memory-guard-hook could not parse its input ({type(e).__name__}); "
                    "confirm this command manually.")
        return 0
    if not VERB.search(command):   # most commands: no filesystem scan at all
        return 0
    try:
        if decide(command, cwd, guarded_roots(cwd)) == "ask":
            emit("ask", REASON)
    except Exception:  # never break the shell over a guard bug
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
