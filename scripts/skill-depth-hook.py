#!/usr/bin/env python3
"""skill-depth-hook.py — after a sota skill loads, name the rules files to open next. A Claude Code
PostToolUse hook on the `Skill` tool (opt-in: it is NOT in hooks/hooks.json until it is measured).

WHY. Loading a skill loads its SKILL.md, which is an index; every rule and Audit checklist lives in
`rules/*.md`, which the model must open itself. Measured in sota-agent-evals with the library and
the routing layer installed (sonnet-5.5, 20 cases each): the router was invoked 20/20, and a rules
file was opened 0/20 (v4, 2026-10-09). A "Next actions" block at the top of the router moved that
to 1/20 against 0/20 (v5, 2026-10-10, NULL) — and the three runs it did send on to a language skill
all stopped at that skill's SKILL.md. Text in an index does not carry the model to the next file.
This hook moves the instruction from the index to the moment after the load, with the paths.

WHAT IT SAYS (as `additionalContext`, which Claude reads next to the tool result):
  sota (the router)   it applies no rule; invoke the language skill for the file types found in
                      the session's cwd (an extension map below), plus the domain skills
  sota-<name>         its SKILL.md is an index and no rule from it is applied yet; the absolute
                      path of each rules file, to Read the ones the index matches to the work
  anything else       nothing
Plain stdout is not shown to Claude on PostToolUse; only the JSON field is
(code.claude.com/docs/en/hooks, read 2026-10-10). Each string is capped at 10,000 characters;
--self-test asserts every skill in this checkout fits.

IT NEVER BLOCKS: any error prints one line to stderr and exits 0 with no output.
SOTA_DEPTH_HOOK=off (or 0 / false / no) disables it.

Install (user or project settings.json):
  "hooks": {
    "PostToolUse": [{"matcher": "Skill", "hooks": [{"type": "command",
                     "command": "python3 /ABS/PATH/scripts/skill-depth-hook.py"}]}]
  }
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIMIT = 10_000
# File extension -> language skill. Every value must be a skill in this checkout (--self-test).
LANG = {
    "py": "sota-python", "pyi": "sota-python",
    "sh": "sota-shell-scripting", "bash": "sota-shell-scripting",
    "go": "sota-golang", "rs": "sota-rust",
    "c": "sota-c-cpp", "h": "sota-c-cpp", "cc": "sota-c-cpp", "cpp": "sota-c-cpp",
    "cxx": "sota-c-cpp", "hpp": "sota-c-cpp",
    "java": "sota-jvm", "kt": "sota-jvm", "kts": "sota-jvm",
    "cs": "sota-dotnet", "php": "sota-php", "rb": "sota-ruby", "swift": "sota-swift",
    "js": "sota-javascript-typescript", "jsx": "sota-javascript-typescript",
    "mjs": "sota-javascript-typescript", "cjs": "sota-javascript-typescript",
    "ts": "sota-javascript-typescript", "tsx": "sota-javascript-typescript",
}
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "target", "dist", "build"}
MAX_FILES = 5000


def skill_dir(name: str) -> Path | None:
    """The copy of the skill the session loaded: the user config first, then a plugin root, then
    this checkout."""
    cands = []
    if os.environ.get("CLAUDE_CONFIG_DIR"):
        cands.append(Path(os.environ["CLAUDE_CONFIG_DIR"]) / "skills")
    cands.append(Path.home() / ".claude" / "skills")
    if os.environ.get("CLAUDE_PLUGIN_ROOT"):
        cands.append(Path(os.environ["CLAUDE_PLUGIN_ROOT"]) / "skills")
    cands.append(ROOT / "skills")
    for c in cands:
        if (c / name / "SKILL.md").is_file():
            return c / name
    return None


def file_types(cwd: Path) -> dict[str, int]:
    """Language skill -> number of files of its types under cwd (dot dirs and vendored trees
    skipped, at most MAX_FILES files looked at)."""
    counts: dict[str, int] = {}
    seen = 0
    for base, dirs, files in os.walk(cwd):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS]
        for f in files:
            seen += 1
            if seen > MAX_FILES:
                return counts
            sk = LANG.get(f.rsplit(".", 1)[-1].lower()) if "." in f else None
            if sk:
                counts[sk] = counts.get(sk, 0) + 1
    return counts


def router_text(cwd: Path) -> str:
    found = file_types(cwd) if cwd.is_dir() else {}
    if found:
        langs = ", ".join("`%s` (%d file%s)" % (s, n, "" if n == 1 else "s")
                          for s, n in sorted(found.items(), key=lambda kv: -kv[1]))
        which = "this workspace holds files for " + langs
    else:
        which = "no source files were found in the working directory, so pick it from the task"
    return ("SOTA: the `sota` router is a map and applies no rule by itself. Next, before writing "
            "or reviewing code, invoke the language skill with the Skill tool — %s — plus the "
            "domain skills the router's table names for this task. Each skill's rules live in its "
            "rules/*.md files; their paths are given when the skill loads." % which)


def skill_text(name: str, d: Path) -> str:
    rules = sorted((d / "rules").glob("*.md"))
    if not rules:
        return ""
    head = ("SOTA: `%s` loaded its index (SKILL.md) only — no rule from it is applied yet. The "
            "rules are in the files below. Before writing or changing code, Read the ones whose "
            "topic matches the work (the index you just loaded says which); before finishing, "
            "check your diff against the Audit checklist at the end of each file you opened.\n"
            % name)
    return head + "\n".join(str(p) for p in rules)


def respond(event: dict) -> str:
    """The JSON to print for one PostToolUse event, or "" for nothing."""
    if event.get("tool_name") != "Skill":
        return ""
    name = str((event.get("tool_input") or {}).get("skill") or "").split(":")[-1].strip()
    if name == "sota":
        text = router_text(Path(event.get("cwd") or os.getcwd()))
    elif name.startswith("sota-"):
        d = skill_dir(name)
        text = skill_text(name, d) if d else ""
    else:
        return ""
    if not text:
        return ""
    return json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                              "additionalContext": text[:LIMIT]}})


def main() -> int:
    if os.environ.get("SOTA_DEPTH_HOOK", "on").lower() in {"off", "0", "false", "no"}:
        return 0
    try:
        out = respond(json.load(sys.stdin))
    except Exception as e:                      # never block a tool result
        print("sota skill-depth-hook: %s: %s — no hint this time" % (type(e).__name__, e),
              file=sys.stderr)
        return 0
    if out:
        print(out)
    return 0


def self_test() -> int:
    """Drives the script as Claude Code does (JSON on stdin) and checks its output."""
    fails: list[str] = []
    n = 0

    def run(event, env_extra=None, raw=None):
        env = {k: v for k, v in os.environ.items() if k != "SOTA_DEPTH_HOOK"}
        env.update(env_extra or {})
        p = subprocess.run([sys.executable, str(Path(__file__).resolve())], input=raw if raw is not None
                           else json.dumps(event), capture_output=True, text=True, env=env, timeout=30)
        return p.returncode, p.stdout, p.stderr

    def check(label, cond):
        nonlocal n
        n += 1
        if not cond:
            fails.append(label)

    def ctx(out):
        return json.loads(out)["hookSpecificOutput"]["additionalContext"] if out.strip() else ""

    with tempfile.TemporaryDirectory() as t:
        cfg = Path(t) / "cfg"
        sk = cfg / "skills" / "sota-python" / "rules"
        sk.mkdir(parents=True)
        (sk.parent / "SKILL.md").write_text("---\nname: sota-python\n---\n")
        for f in ("01-tooling.md", "04-async.md"):
            (sk / f).write_text("# x\n## Audit checklist\n")
        ws = Path(t) / "ws"
        (ws / "pkg").mkdir(parents=True)
        (ws / "pkg" / "a.py").write_text("")
        (ws / "pkg" / "b.py").write_text("")
        (ws / "run.sh").write_text("")
        (ws / ".git").mkdir()
        (ws / ".git" / "hook.rb").write_text("")          # a dot dir: must not count
        env = {"CLAUDE_CONFIG_DIR": str(cfg)}

        rc, out, _ = run({"tool_name": "Skill", "tool_input": {"skill": "sota-python"}}, env)
        c = ctx(out)
        check("skill: exit 0", rc == 0)
        check("skill: names the skill", "`sota-python`" in c)
        check("skill: absolute path of every rules file",
              str(sk / "01-tooling.md") in c and str(sk / "04-async.md") in c)
        check("skill: event name", out and json.loads(out)["hookSpecificOutput"]["hookEventName"] == "PostToolUse")

        rc, out, _ = run({"tool_name": "Skill", "tool_input": {"skill": "sota-skills:sota-python"}}, env)
        check("plugin-prefixed name resolves", str(sk / "04-async.md") in ctx(out))

        rc, out, _ = run({"tool_name": "Skill", "tool_input": {"skill": "sota"}, "cwd": str(ws)}, env)
        c = ctx(out)
        check("router: names the language skill found", "`sota-python` (2 files)" in c)
        check("router: second language", "`sota-shell-scripting` (1 file)" in c)
        check("router: dot dir skipped", "sota-ruby" not in c)

        rc, out, _ = run({"tool_name": "Skill", "tool_input": {"skill": "sota"}, "cwd": str(Path(t) / "nope")}, env)
        check("router: no workspace still answers", "pick it from the task" in ctx(out))

        for label, ev in (("non-sota skill is silent", {"tool_name": "Skill", "tool_input": {"skill": "pdf"}}),
                          ("other tool is silent", {"tool_name": "Bash", "tool_input": {"command": "ls"}}),
                          ("unknown sota skill is silent", {"tool_name": "Skill", "tool_input": {"skill": "sota-nope"}})):
            rc, out, _ = run(ev, env)
            check(label, rc == 0 and out == "")

        rc, out, _ = run({"tool_name": "Skill", "tool_input": {"skill": "sota-python"}},
                         dict(env, SOTA_DEPTH_HOOK="off"))
        check("opt-out is silent", rc == 0 and out == "")

        rc, out, err = run(None, env, raw="{not json")
        check("malformed input: exit 0, no output, says why", rc == 0 and out == "" and "skill-depth-hook" in err)

    # The real checkout: every value in LANG is a skill here, and every skill's hint fits the cap.
    names = {p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").is_file()}
    check("every LANG value is a skill in this checkout: %s" % sorted(set(LANG.values()) - names),
          set(LANG.values()) <= names)
    sized = 0
    for nm in sorted(names - {"sota"}):
        d = ROOT / "skills" / nm
        txt = skill_text(nm, d)
        if txt:
            sized += 1
            check("%s hint under %d chars (%d)" % (nm, LIMIT, len(txt)), len(txt) < LIMIT)
    check("sized every non-router skill (%d)" % sized, sized == len(names) - 1)

    for f in fails:
        print("FAIL:", f)
    print("%s: %d/%d" % ("FAIL" if fails else "PASS", n - len(fails), n))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(self_test() if sys.argv[1:] == ["--self-test"] else main())
