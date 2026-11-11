#!/usr/bin/env python3
"""session-load-audit.py — what a Claude Code session actually loaded from this library, read from
its transcript: skills invoked, rules files read or searched (and by which tool), whether each
file's Audit checklist was read and re-read after the last edit, and which of its runnable probes
were executed.

  python3 scripts/session-load-audit.py TRANSCRIPT.jsonl [MORE.jsonl ...]  # one session (+ subagents)
  python3 scripts/session-load-audit.py --cwd /path/to/project            # newest session for that dir
  python3 scripts/session-load-audit.py --cwd DIR --diff BASE [--repo R]  # + probes over the built code
  python3 scripts/session-load-audit.py --diff BASE --show-hits           # PRIVATE: where each new hit is
  python3 scripts/session-load-audit.py --json ...                        # machine-readable
  python3 scripts/session-load-audit.py --self-test

WHY. /sota-report check E asks "was it loaded?" with the transcript as evidence, in both
directions, and the intake cannot see the session (docs/FIELD-REPORT-PROMPT.md). Done by hand it
went wrong twice: a "never opened" file had been read 22 hours later to write the report, and an
appendix was retyped. This makes the answer a re-runnable artifact.

WHAT IT CAN AND CANNOT SAY. The transcript half proves PROCESS: a file was read, its checklist
lines were inside the range read, a probe ran as published. A re-read is not compliance. The
--diff half looks at the ARTIFACT: every runnable checklist probe over the files changed since
BASE, hits counted on added lines only, joined with the transcript into loaded x new-hit. A hit is
a lead (first real run: 4 of 9 sampled were real), no hit is not compliance (only the items with a
runnable probe can hit; the count is printed), and the per-item "was it followed" is the bounded
verdict walk /sota-report check E2 asks for.

THREE INSTRUMENT TRAPS IT HANDLES (each would otherwise lie):
  1. A tool call is written more than once (subagent and resumed-session copies; measured
     2026-10-22 over 1,840 transcripts, ~2x). Everything is keyed by unique tool_use id.
  2. Library files are often read with `cat`/`sed`/`grep` through Bash, not the Read tool. Counting
     only Skill/Read calls reports a loaded file as unloaded. Bash commands are parsed too; a
     mention it cannot resolve (a path built from a variable) is COUNTED, never dropped.
  3. Checklist line positions come from THIS checkout, which may differ from the text the session
     loaded. The library commit is printed so the reader can tell.

ENVIRONMENT. --cwd looks under $CLAUDE_CONFIG_DIR/projects (default ~/.claude/projects).

PRIVACY (default, deliberate). Output carries library-relative paths, tool names, tool_use ids,
timestamps, counts and the EXTENSIONS of edited non-library files. Never command text, project
paths, file contents or the transcript's directory. It is meant to be pasted into a field report.

Exit: 0 report written, 2 usage error or unreadable transcript.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / file)
    if spec is None or spec.loader is None:
        raise SystemExit(f"session-load-audit: cannot load scripts/{file}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


ccp = _load("ccp", "check-checklist-probes.py")          # probe extraction, same as the gates
cpf = _load("cpf", "check-probe-fixtures.py")            # probe ids, same as the fixture tree

LIB_PATH = re.compile(r"skills/sota[\w-]*(?:/[\w.*-]+)*/?")
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
READERS = {"cat", "sed", "head", "tail", "less", "more", "bat", "nl", "awk", "view"}
SEARCHERS = {"grep", "rg", "ugrep", "egrep", "fgrep", "ag", "ack", "git"}
SEGMENT_OPS = {"|", "||", "&&", ";", "&", "|&", "\n"}
# The router's language rule (cross-cutting rule 1), as an extension heuristic only.
EXT_SKILL = {
    ".py": "sota-python", ".go": "sota-golang", ".rs": "sota-rust", ".java": "sota-jvm",
    ".kt": "sota-jvm", ".kts": "sota-jvm", ".cs": "sota-dotnet", ".php": "sota-php",
    ".rb": "sota-ruby", ".swift": "sota-swift", ".c": "sota-c-cpp", ".h": "sota-c-cpp",
    ".cc": "sota-c-cpp", ".cpp": "sota-c-cpp", ".hpp": "sota-c-cpp", ".js": "sota-javascript-typescript",
    ".mjs": "sota-javascript-typescript", ".cjs": "sota-javascript-typescript",
    ".ts": "sota-javascript-typescript", ".tsx": "sota-javascript-typescript",
    ".jsx": "sota-javascript-typescript", ".sh": "sota-shell-scripting", ".bash": "sota-shell-scripting",
    ".ps1": "sota-shell-scripting",
}


@dataclass(slots=True)
class Call:
    """One unique tool_use, validated at the boundary: only the fields this script reads."""
    id: str
    name: str
    ts: str
    turn: int
    file_path: str = ""
    offset: int | None = None
    limit: int | None = None
    command: str = ""
    skill: str = ""
    is_error: bool | None = None


@dataclass(frozen=True, slots=True)
class Access:
    call_id: str
    ts: str
    turn: int
    tool: str          # Skill | Read | Bash:<verb> | Edit
    kind: str          # invoke | read | search | count | edit | other
    lines: tuple[int, int] | None = None   # 1-based inclusive range read, None = unknown
    whole: bool = False


@dataclass(slots=True)
class Session:
    calls: list[Call] = field(default_factory=list)
    prompts: int = 0
    raw_tool_use_blocks: int = 0
    files: list[str] = field(default_factory=list)
    sha256: list[str] = field(default_factory=list)


# ------------------------------------------------------------------ parsing

def _is_prompt(entry: dict) -> bool:
    if entry.get("type") != "user" or entry.get("isMeta"):
        return False
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return bool(content.strip())
    if isinstance(content, list):
        kinds = {c.get("type") for c in content if isinstance(c, dict)}
        return "text" in kinds and "tool_result" not in kinds
    return False


def _int(v) -> int | None:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def parse(paths: Sequence[Path]) -> Session:
    s = Session()
    seen: dict[str, Call] = {}
    errors: dict[str, bool] = {}
    prompt_ts: set[str] = set()
    pending: list[tuple[str, dict]] = []
    for p in paths:
        data = p.read_bytes()
        s.files.append(p.name)
        s.sha256.append(hashlib.sha256(data).hexdigest()[:16])
        # Lenient on purpose (code-security rules/01 §1 asks for strict decoding of untrusted input):
        # a transcript is local, harness-written JSONL, and one bad byte must cost one record, not
        # the whole audit. A replaced character cannot create a library path that was not there.
        for raw in data.decode("utf-8", "replace").splitlines():
            try:
                e = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(e, dict):
                continue
            ts = e.get("timestamp") if isinstance(e.get("timestamp"), str) else ""
            if _is_prompt(e) and ts:
                prompt_ts.add(ts)
            content = (e.get("message") or {}).get("content") if isinstance(e.get("message"), dict) else None
            if not isinstance(content, list):
                continue
            for c in content:
                if not isinstance(c, dict):
                    continue
                if c.get("type") == "tool_use" and isinstance(c.get("id"), str):
                    s.raw_tool_use_blocks += 1
                    pending.append((ts, c))
                elif c.get("type") == "tool_result" and isinstance(c.get("tool_use_id"), str):
                    if isinstance(c.get("is_error"), bool):
                        errors[c["tool_use_id"]] = c["is_error"]
    prompts = sorted(prompt_ts)
    s.prompts = len(prompts)
    for ts, c in pending:
        cid, inp = c["id"], c.get("input") if isinstance(c.get("input"), dict) else {}
        prev = seen.get(cid)
        if prev is not None:
            if ts and (not prev.ts or ts < prev.ts):   # a re-stamped copy: keep the earliest
                prev.ts = ts
            continue
        seen[cid] = Call(
            id=cid, name=str(c.get("name") or ""), ts=ts, turn=0,
            file_path=str(inp.get("file_path") or inp.get("notebook_path") or ""),
            offset=_int(inp.get("offset")), limit=_int(inp.get("limit")),
            command=str(inp.get("command") or ""), skill=str(inp.get("skill") or ""))
    for call in seen.values():
        call.turn = sum(1 for t in prompts if t <= call.ts) if call.ts else 0
        call.is_error = errors.get(call.id)
    s.calls = sorted(seen.values(), key=lambda c: (c.ts, c.id))
    return s


# ------------------------------------------------------------------ classification

def lib_rel(token: str) -> str | None:
    m = LIB_PATH.search(token)
    return m.group(0).rstrip("/") if m else None


def _segments(cmd: str) -> list[tuple[list[str], str]]:
    """Each simple command with the operator that follows it ('|' means its output is filtered)."""
    lex = shlex.shlex(cmd.replace("\n", " ; "), posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    try:
        toks = list(lex)
    except ValueError:
        toks = cmd.split()
    segs: list[tuple[list[str], str]] = []
    cur: list[str] = []
    for t in toks:
        if t in SEGMENT_OPS:
            if cur:
                segs.append((cur, t))
            cur = []
        else:
            cur.append(t)
    if cur:
        segs.append((cur, ""))
    return segs


def _downstream(seg: Sequence[str], rng: tuple[int, int] | None, whole: bool, nlines: int
                ) -> tuple[str, tuple[int, int] | None, bool]:
    """A reader piped into another command: `| head -n N` bounds it, `| grep` makes it a search,
    anything else makes the range unknown. `cat f | head -400` is NOT a whole-file read."""
    verb = _verb(seg)
    if verb in {"head", "tail"} and rng is not None:
        sub, _ = _range(verb, seg, rng[1] - rng[0] + 1)
        if sub is None:
            return "read", None, False
        lo = rng[0] + sub[0] - 1
        hi = rng[0] + sub[1] - 1
        return "read", (lo, hi), lo <= 1 and hi >= nlines
    if verb in SEARCHERS:
        return "search", None, False
    return "read", None, False


def _verb(seg: Sequence[str]) -> str:
    words = [w for w in seg if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", w)]
    while words and words[0] in {"command", "env", "sudo", "time", "nice", "xargs", "do", "then",
                                 "else", "elif", "if", "while", "until", "!", "(", "{", "$("}:
        words = words[1:]
    return os.path.basename(words[0]) if words else ""


def _range(verb: str, seg: Sequence[str], nlines: int) -> tuple[tuple[int, int] | None, bool]:
    """Line range a reader printed, as far as it can be known statically."""
    text = " ".join(seg)
    if verb in {"cat", "less", "more", "bat", "nl", "view"}:
        return (1, nlines), True
    if verb == "sed" and not re.search(r"\s-i", text):
        m = re.search(r"(\d+)\s*,\s*(\d+)\s*p", text)
        if m:
            return (int(m.group(1)), int(m.group(2))), False
        m = re.search(r"(\d+)\s*,\s*\$\s*p", text)
        if m:
            return (int(m.group(1)), nlines), False
        return None, False
    if verb == "head":
        m = re.search(r"-n\s*(\d+)|-(\d+)\b", text)
        n = int(next(g for g in m.groups() if g)) if m else 10
        return (1, min(n, nlines)), n >= nlines
    if verb == "tail":
        m = re.search(r"-n\s*\+(\d+)|\+(\d+)\b", text)
        if m:
            start = int(next(g for g in m.groups() if g))
            return (start, nlines), start <= 1
        m = re.search(r"-n\s*(\d+)|-(\d+)\b", text)
        n = int(next(g for g in m.groups() if g)) if m else 10
        return (max(1, nlines - n + 1), nlines), n >= nlines
    return None, False


def _nlines(rel: str, lib: Path) -> int:
    try:
        return (lib / rel).read_text(encoding="utf-8").count("\n")
    except OSError:
        return 0


def accesses(s: Session, lib: Path) -> tuple[dict[str, list[Access]], dict[str, int], list[Call], list[Call]]:
    by_file: dict[str, list[Access]] = {}
    other: dict[str, int] = {"unresolved library mentions": 0, "directory or glob searches": 0,
                             "non-library skills invoked": 0}
    edits: list[Call] = []
    bash: list[Call] = []
    for c in s.calls:
        if c.name == "Skill":
            name = c.skill.split(":", 1)[-1]
            if name.startswith("sota"):
                by_file.setdefault(f"skills/{name}/SKILL.md", []).append(
                    Access(c.id, c.ts, c.turn, "Skill", "invoke"))
            else:
                other["non-library skills invoked"] += 1
        elif c.name in {"Read", "Grep", "Glob"} or c.name in EDIT_TOOLS:
            rel = lib_rel(c.file_path)
            if c.name in EDIT_TOOLS:
                edits.append(c)
            if not rel or not rel.endswith(".md"):
                continue
            if c.name in EDIT_TOOLS:
                by_file.setdefault(rel, []).append(Access(c.id, c.ts, c.turn, c.name, "edit"))
            elif c.name == "Read":
                n = _nlines(rel, lib)
                start = c.offset or 1
                end = min(n, start + (c.limit or 2000) - 1) if n else start + (c.limit or 2000) - 1
                by_file.setdefault(rel, []).append(
                    Access(c.id, c.ts, c.turn, "Read", "read", (start, end), start <= 1 and end >= n > 0))
        elif c.name == "Bash":
            bash.append(c)
            if "skills/" not in c.command:
                continue
            segs = _segments(c.command)
            for i, (seg, op) in enumerate(segs):
                verb = _verb(seg)
                for tok in seg:
                    if "skills/" not in tok:
                        continue
                    rel = lib_rel(tok)
                    if not rel:
                        other["unresolved library mentions"] += 1
                        continue
                    if not rel.endswith(".md") or "*" in rel:
                        other["directory or glob searches"] += 1
                        continue
                    if not (lib / rel).is_file():
                        other["unresolved library mentions"] += 1
                        continue
                    inplace = verb in {"sed", "perl"} and re.search(r"\s-p?i\b|\s-i", " ".join(seg))
                    if inplace:
                        kind, rng, whole = "edit", None, False
                    elif verb in READERS:
                        kind = "read"
                        n = _nlines(rel, lib)
                        rng, whole = _range(verb, seg, n)
                        if op in {"|", "|&"} and i + 1 < len(segs):
                            kind, rng, whole = _downstream(segs[i + 1][0], rng, whole, n)
                    elif verb in SEARCHERS:
                        kind, rng, whole = "search", None, False
                    elif verb == "wc":
                        kind, rng, whole = "count", None, False
                    else:
                        kind, rng, whole = "other", None, False
                    by_file.setdefault(rel, []).append(
                        Access(c.id, c.ts, c.turn, f"Bash:{verb or '?'}", kind, rng, whole))
    return by_file, other, edits, bash


def checklist_start(rel: str, lib: Path) -> int | None:
    try:
        for i, line in enumerate((lib / rel).read_text(encoding="utf-8").split("\n"), 1):
            if line.startswith("## Audit checklist"):
                return i
    except OSError:
        return None
    return None


def covers_checklist(a: Access, start: int | None) -> str:
    if start is None or a.kind != "read":
        return "no"
    if a.whole:
        return "yes"
    if a.lines is None:
        return "unknown"
    lo, hi = a.lines
    if lo <= start <= hi:
        return "yes"
    if hi > start:            # began inside the checklist: part of it was read
        return "partial"
    return "no"


_SCOPE = re.compile(r"\s\.(?=\s*(?:\||;|&&|$))")


def _probe_body(span: str) -> str:
    """The probe as published, minus its `.` search scope (often replaced by a directory),
    whitespace removed. Matching only the PATTERN over-counts: measured on a real transcript,
    `'math/rand'` matched a survey `rg` of the library that never ran the probe."""
    return re.sub(r"\s+", "", _SCOPE.sub(" ", span))


def probe_runs(rel: str, lib: Path, bash: Sequence[Call]) -> list[tuple[str, list[str]]]:
    try:
        text = (lib / rel).read_text(encoding="utf-8")
    except OSError:
        return []
    out = []
    squashed = [(c.id, re.sub(r"\s+", "", c.command)) for c in bash]
    for span in ccp.probes_in(text):
        if ccp.skip_reason(span) is not None:
            continue
        body = _probe_body(span)
        ran = [cid for cid, cmd in squashed if body and body in cmd]
        out.append((cpf.probe_id(rel, span), ran))
    return out


# ------------------------------------------------------------------ diff mode: probes over the built code

MAX_FILES, MAX_BYTES_EACH = 500, 1_000_000
_HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")
_HIT = re.compile(r"^(?:\./)?(.+?):(\d+):")
_INCLUDE = re.compile(r"--include=(?:'([^']+)'|\"([^\"]+)\"|(\S+))")


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)


def diff_scope(repo: Path, base: str) -> tuple[dict[str, set[int]], str]:
    """{path: added line numbers} for the working tree against BASE, untracked files whole.
    The base is resolved and GUARDED first: an empty comparand silently answers 'clean'."""
    r = _git(repo, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}")
    if r.returncode != 0 or not r.stdout.strip():
        why = _git(repo, "rev-parse", "--verify", f"{base}^{{commit}}").stderr.strip()
        return {}, f"base {base!r} does not resolve to a commit in {repo}: {why or 'no output'}"
    sha = r.stdout.strip()
    d = _git(repo, "diff", "-U0", "--no-color", "--no-ext-diff", sha, "--")
    if d.returncode != 0:
        return {}, f"git diff failed: {d.stderr.strip()}"
    added: dict[str, set[int]] = {}
    cur = None
    for line in d.stdout.split("\n"):
        if line.startswith("+++ "):
            cur = line[6:] if line.startswith("+++ b/") else None
        elif cur and (m := _HUNK.match(line)):
            start, count = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
            if count:
                added.setdefault(cur, set()).update(range(start, start + count))
    u = _git(repo, "ls-files", "--others", "--exclude-standard", "-z")
    for path in filter(None, u.stdout.split("\0")):
        try:
            n = (repo / path).read_bytes().count(b"\n") + 1
        except OSError:
            continue
        added[path] = set(range(1, n + 1))
    return added, ""


def _stage(repo: Path, added: dict[str, set[int]], into: Path) -> tuple[list[str], int]:
    """Copy each changed REGULAR file (no symlink followed) under a size cap. Returns staged, skipped."""
    staged, skipped = [], 0
    for rel in sorted(added):
        src = repo / rel
        if src.is_symlink() or not src.is_file() or src.stat().st_size > MAX_BYTES_EACH:
            skipped += 1
            continue
        dst = into / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(src.read_bytes())
        staged.append(rel)
    return staged, skipped


def _applies(span: str, names: Sequence[str]) -> bool:
    globs = [next(g for g in m.groups() if g) for m in _INCLUDE.finditer(span)]
    return not globs or any(fnmatch.fnmatch(os.path.basename(n), g) for n in names for g in globs)


def probe_coverage(lib: Path) -> tuple[int, int]:
    """(checklist items, items carrying >= 1 runnable probe), counted live: the bound on what a
    mechanical pass can say. Measured 2026-11-11: 1,296 of 4,304."""
    items = runnable = 0
    for p in (lib / "skills").glob("*/rules/*.md"):
        t = p.read_text(encoding="utf-8")
        i = t.find("\n## Audit checklist")
        if i < 0:
            continue
        for it in re.split(r"\n(?=- \[ \])", t[i:])[1:]:
            items += 1
            runnable += any(ccp.skip_reason(s) is None for s in ccp.probes_in("\n## Audit checklist\n" + it))
    return items, runnable


def diff_probes(repo: Path, base: str, lib: Path) -> tuple[dict, str]:
    added, err = diff_scope(repo, base)
    if err:
        return {}, err
    if len(added) > MAX_FILES:
        return {}, f"{len(added)} changed files exceeds {MAX_FILES}: pass a nearer --diff base"
    out = {"base": base, "changed_files": len(added), "added_lines": sum(map(len, added.values())),
           "staged_files": 0, "skipped_files": 0, "probes_total": 0, "probes_not_applicable": 0,
           "probes_missing_path": 0, "probes_run": 0, "probes_broken": [], "hits": []}
    out["checklist_items"], out["checklist_items_with_probe"] = probe_coverage(lib)
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "diff"
        stage.mkdir()
        staged, out["skipped_files"] = _stage(repo, added, stage)
        out["staged_files"] = len(staged)
        if not staged:
            return out, ""
        for rel in sorted(str(p.relative_to(lib)) for p in (lib / "skills").glob("*/rules/*.md")):
            text = (lib / rel).read_text(encoding="utf-8")
            for span in ccp.probes_in(text):
                if ccp.skip_reason(span) is not None:
                    continue
                out["probes_total"] += 1
                if not _applies(span, staged):
                    out["probes_not_applicable"] += 1
                    continue
                rc, stdout, stderr = cpf.run_case(span, str(stage))
                pid = cpf.probe_id(rel, span)
                errs = [ln for ln in stderr.splitlines() if ln.strip()]
                only_missing = rc in (2, 123) and errs and all(ccp.MISSING.search(ln) for ln in errs)
                if only_missing and not stdout.strip():
                    # the probe names a path (a workflow dir, package.json) this diff does not touch
                    out["probes_missing_path"] += 1
                    continue
                out["probes_run"] += 1
                if rc not in (0, 1, 123) and not only_missing:
                    out["probes_broken"].append(pid)
                    continue
                new, pre, unattributed, where = 0, 0, 0, []
                for line in stdout.splitlines():
                    m = _HIT.match(line)
                    if not m:
                        unattributed += bool(line.strip())
                    elif int(m.group(2)) in added.get(m.group(1), set()):
                        new += 1
                        where.append(f"{m.group(1)}:{m.group(2)}")
                    else:
                        pre += 1
                if new or pre or unattributed:
                    out["hits"].append({"probe": pid, "rules_file": rel, "new": new, "pre_existing": pre,
                                        "unattributed": unattributed, "where": where})
    return out, ""


# ------------------------------------------------------------------ report

def library_commit(lib: Path) -> str:
    r = subprocess.run(["git", "-C", str(lib), "rev-parse", "--short", "HEAD"],
                       capture_output=True, text=True, check=False)
    return r.stdout.strip() or "unknown (not a git checkout)"


def build(s: Session, lib: Path) -> dict:
    by_file, other, edits, bash = accesses(s, lib)
    last_edit = max((c.ts for c in edits if c.ts), default="")
    files = []
    for rel in sorted(by_file):
        acc = by_file[rel]
        start = checklist_start(rel, lib) if "/rules/" in rel else None
        cov = [(a, covers_checklist(a, start)) for a in acc]
        read_cl = [a for a, v in cov if v in {"yes", "partial"}]
        unknown = [a for a, v in cov if v == "unknown"]
        probes = probe_runs(rel, lib, bash) if "/rules/" in rel else []
        files.append({
            "file": rel,
            "first": min(a.ts for a in acc), "first_turn": min(a.turn for a in acc),
            "accesses": [{"id": a.call_id, "ts": a.ts, "turn": a.turn, "tool": a.tool, "kind": a.kind,
                          "lines": list(a.lines) if a.lines else None, "checklist": v} for a, v in cov],
            "kinds": sorted({a.kind for a in acc}),
            "checklist_read": "n/a" if start is None else ("yes" if read_cl else ("unknown" if unknown else "no")),
            "checklist_reread_after_last_edit": ("n/a" if start is None or not last_edit else
                                                 ("yes" if any(a.ts > last_edit for a in read_cl) else
                                                  ("unknown" if any(a.ts > last_edit for a in unknown) else "no"))),
            "probes_total": len(probes),
            "probes_run": [{"probe": pid, "ids": ids} for pid, ids in probes if ids],
        })
    loaded = {f["file"].split("/")[1] for f in files if set(f["kinds"]) & {"invoke", "read", "search"}}
    exts: dict[str, int] = {}
    for c in edits:
        if lib_rel(c.file_path):
            continue
        name = os.path.basename(c.file_path)
        ext = os.path.splitext(name)[1].lower() or ("Dockerfile" if name.startswith("Dockerfile") else "(none)")
        exts[ext] = exts.get(ext, 0) + 1
    expected = sorted({EXT_SKILL[e] for e in exts if e in EXT_SKILL})
    return {
        "transcripts": [{"file": f, "sha256_16": h} for f, h in zip(s.files, s.sha256)],
        "library_commit": library_commit(lib),
        "tool_use_blocks": s.raw_tool_use_blocks, "unique_tool_use_ids": len(s.calls),
        "user_prompts": s.prompts,
        "first_ts": s.calls[0].ts if s.calls else "", "last_ts": s.calls[-1].ts if s.calls else "",
        "last_edit_ts": last_edit,
        "bash_commands": len(bash),
        "bash_after_last_edit": sum(1 for c in bash if last_edit and c.ts > last_edit),
        "edited_non_library_extensions": exts,
        "router_invoked": any(f["file"] == "skills/sota/SKILL.md" and "invoke" in f["kinds"] for f in files),
        "skills_touched": sorted(loaded),
        "expected_language_skills_missing": [k for k in expected if k not in loaded],
        "other": other,
        "files": files,
    }


_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def _safe(v) -> str:
    """Transcript-derived text is escaped before it reaches a terminal (CWE-150)."""
    return _CTRL.sub(lambda m: "\\x%02x" % ord(m.group(0)), str(v))


def _sanitize(o):
    if isinstance(o, dict):
        return {_safe(k): _sanitize(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_sanitize(v) for v in o]
    return _safe(o) if isinstance(o, str) else o


def markdown(r: dict) -> str:
    r = _sanitize(r)
    L = ["## Session load audit (scripts/session-load-audit.py, output verbatim)", ""]
    L.append(f"- Transcripts: " + ", ".join(f"`{t['file']}` sha256:{t['sha256_16']}" for t in r["transcripts"]))
    L.append(f"- Library measured at: `{r['library_commit']}` (checklist positions are from this commit)")
    L.append(f"- Tool calls: {r['unique_tool_use_ids']} unique ids ({r['tool_use_blocks']} blocks); "
             f"{r['user_prompts']} user prompts; {r['first_ts']} → {r['last_ts']}")
    L.append(f"- Last edit: {r['last_edit_ts'] or 'none'}; Bash commands: {r['bash_commands']}, "
             f"{r['bash_after_last_edit']} after the last edit")
    L.append(f"- Router invoked: {'yes' if r['router_invoked'] else 'NO'}; skills touched: "
             + (", ".join(r["skills_touched"]) or "none"))
    exts = ", ".join(f"{k}×{v}" for k, v in sorted(r["edited_non_library_extensions"].items())) or "none"
    L.append(f"- Non-library files edited, by extension: {exts}")
    miss = r["expected_language_skills_missing"]
    L.append("- Language skill expected from those extensions but not touched (heuristic): "
             + (", ".join(miss) if miss else "none"))
    L.append("- Not resolved: " + "; ".join(f"{k}: {v}" for k, v in r["other"].items()))
    L += ["", "| Library file | First (turn) | How | Checklist read | Re-read after last edit | Probes run |",
          "|---|---|---|---|---|---|"]
    for f in r["files"]:
        how = ", ".join(sorted({a["tool"] for a in f["accesses"]}))
        probes = f"{len(f['probes_run'])}/{f['probes_total']}" if f["probes_total"] else "-"
        L.append(f"| `{f['file']}` | {f['first']} ({f['first_turn']}) | {how} | {f['checklist_read']} "
                 f"| {f['checklist_reread_after_last_edit']} | {probes} |")
    L += ["", "Probes run (id → tool_use ids):"]
    any_run = False
    for f in r["files"]:
        for p in f["probes_run"]:
            any_run = True
            L.append(f"- `{p['probe']}` → " + ", ".join(p["ids"]))
    if not any_run:
        L.append("- none")
    L += ["", "Proves process only (read, checklist in range, probe pattern executed), never that a rule "
              "was applied. `unknown` = a reader whose range cannot be known statically (awk, a computed sed)."]
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ discovery + main

def config_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def newest_for_cwd(cwd: str) -> list[Path]:
    """The newest main transcript whose entries record this working directory, plus its subagents."""
    want = os.path.realpath(cwd)
    best: tuple[float, Path] | None = None
    for p in (config_dir() / "projects").glob("*/*.jsonl"):
        try:
            with p.open(encoding="utf-8", errors="replace") as fh:
                for _, raw in zip(range(200), fh):
                    if '"cwd"' not in raw:
                        continue
                    e = json.loads(raw)
                    if isinstance(e, dict) and isinstance(e.get("cwd"), str):
                        if os.path.realpath(e["cwd"]) == want:
                            m = p.stat().st_mtime
                            if best is None or m > best[0]:
                                best = (m, p)
                        break
        except (OSError, json.JSONDecodeError):
            continue
    if best is None:
        return []
    main = best[1]
    subs = sorted((main.parent / main.stem).glob("**/*.jsonl")) if (main.parent / main.stem).is_dir() else []
    return [main, *subs]


def loaded_rules(r: dict | None) -> set[str] | None:
    if r is None:
        return None
    return {f["file"] for f in r["files"] if "/rules/" in f["file"]
            and set(f["kinds"]) & {"read", "search", "invoke"}}


def join(r: dict | None, d: dict) -> dict:
    """The 2x2 per rules file: loaded (transcript) x new probe hits (built code), and the bounded
    verdict-walk set /sota-report asks for: every loaded rules file plus every file with a new hit."""
    loaded = loaded_rules(r)
    hit_files = sorted({h["rules_file"] for h in d["hits"] if h["new"]})
    rows = []
    for rel in hit_files:
        state = "unknown (no transcript)" if loaded is None else (
            "loaded + new hit: rule shape, if the walk confirms it" if rel in loaded
            else "not loaded + new hit: routing gap, if the walk confirms it")
        rows.append({"rules_file": rel, "quadrant": state,
                     "new_hits": sum(h["new"] for h in d["hits"] if h["rules_file"] == rel)})
    for rel in sorted(loaded or ()):
        if rel not in hit_files:
            rows.append({"rules_file": rel, "quadrant": "loaded, no new mechanical hit", "new_hits": 0})
    walk = sorted((loaded or set()) | set(hit_files))
    return {"quadrants": rows, "verdict_walk": walk}


def diff_markdown(d: dict, j: dict, show_hits: bool) -> str:
    d, j = _sanitize(d), _sanitize(j)
    L = ["", f"## Diff probe audit (working tree vs `{d['base']}`)", "",
         f"- Changed files: {d['changed_files']} ({d['added_lines']} added lines); staged "
         f"{d['staged_files']}, skipped {d['skipped_files']} (symlink, non-regular or > {MAX_BYTES_EACH} bytes)",
         f"- Probes: {d['probes_run']} run of {d['probes_total']} runnable "
         f"({d['probes_not_applicable']} not applicable: their --include matches no changed file; "
         f"{d['probes_missing_path']} name a path the diff does not contain); "
         f"broken: {len(d['probes_broken'])}" + (" — " + ", ".join(d["probes_broken"]) if d["probes_broken"] else ""),
         "", "| Probe | Rules file | New (added lines) | Pre-existing | Unattributed |", "|---|---|---|---|---|"]
    shown = [h for h in d["hits"] if h["new"] or h["pre_existing"]]
    for h in shown:
        L.append(f"| `{h['probe']}` | `{h['rules_file']}` | {h['new']} | {h['pre_existing']} | {h['unattributed']} |")
    if not shown:
        L.append("| none | | | | |")
    only_file = len(d["hits"]) - len(shown)
    L.append(f"\n{only_file} more probe(s) printed only file-level or absence output (`grep -l`, "
             f"`|| echo 'no …'`): written for a whole repository, not attributable to added lines; in --json.")
    if show_hits:
        L += ["", "New hits (PRIVATE, local use only; never paste into a report):"]
        L += [f"- `{h['probe']}` {w}" for h in d["hits"] for w in h["where"]]
    L += ["", "| Rules file | Loaded x new hit |", "|---|---|"]
    L += [f"| `{q['rules_file']}` | {q['quadrant']} |" for q in j["quadrants"]] or ["| none | |"]
    L += ["", "Verdict walk (met / not met / not applicable with reason / not checked, per checklist item):"]
    L += [f"- `{w}`" for w in j["verdict_walk"]] or ["- none"]
    L += ["", f"A hit is a lead, not a verdict: read it. No hit is not compliance: "
              f"{d['checklist_items_with_probe']} of {d['checklist_items']} checklist items carry a runnable "
              f"probe, and each probe is proven on one fixture, not on all code."]
    return "\n".join(L) + "\n"


def _fail(msg: str, as_json: bool) -> int:
    if as_json:
        print(json.dumps({"code": "usage", "message": msg}), file=sys.stderr)
    else:
        print(f"error: {msg}", file=sys.stderr)
    return 2


def main(argv: Sequence[str]) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog="exit codes: 0 report written, 2 usage error, unreadable or empty transcript")
    ap.add_argument("transcripts", nargs="*", type=Path)
    ap.add_argument("--cwd", help="audit the newest session recorded for this working directory")
    ap.add_argument("--library", type=Path, default=ROOT, help="library checkout (default: this one)")
    ap.add_argument("--diff", metavar="BASE", help="also run every applicable probe over the working "
                    "tree's changes since BASE, counting hits on added lines only")
    ap.add_argument("--repo", type=Path, default=Path.cwd(), help="repository for --diff (default: cwd)")
    ap.add_argument("--show-hits", action="store_true", help="print new hits as path:line (PRIVATE; "
                    "for checking a hit locally, never for a report)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    lib = a.library.resolve()
    d = j = None
    if a.diff:
        top = _git(a.repo, "rev-parse", "--show-toplevel")
        if top.returncode != 0:
            return _fail(f"--repo {a.repo} is not inside a git repository: {top.stderr.strip()}", a.json)
        d, err = diff_probes(Path(top.stdout.strip()), a.diff, lib)
        if err:
            return _fail(err, a.json)
        if not a.transcripts and not a.cwd:
            j = join(None, d)
            if not a.show_hits:
                for h in d["hits"]:
                    h.pop("where")
            out = json.dumps(_sanitize({"diff": d, "join": j}), indent=2) + "\n" if a.json else diff_markdown(d, j, a.show_hits)
            return _write(out)
    paths = list(a.transcripts)
    if a.cwd:
        found = newest_for_cwd(a.cwd)
        if not found:
            return _fail(f"no transcript under {config_dir() / 'projects'} records cwd {a.cwd}; "
                         f"pass the .jsonl path instead", a.json)
        paths += found
    if not paths:
        return _fail("no transcript given; pass TRANSCRIPT.jsonl or --cwd DIR", a.json)
    for p in paths:
        if not p.is_file():
            return _fail(f"not a file: {p}", a.json)
    try:
        s = parse(paths)
    except OSError as e:
        return _fail(f"cannot read transcript: {e}", a.json)
    if not s.calls:
        return _fail(f"0 tool calls in {len(paths)} transcript(s): not a session transcript, or the "
                     f"format changed; refusing to report an empty audit", a.json)
    r = build(s, lib)
    if d is not None:
        j = join(r, d)
        if not a.show_hits:
            for h in d["hits"]:
                h.pop("where")
        if a.json:
            return _write(json.dumps(_sanitize({**r, "diff": d, "join": j}), indent=2) + "\n")
        return _write(markdown(r) + diff_markdown(d, j, a.show_hits))
    return _write(json.dumps(_sanitize(r), indent=2) + "\n" if a.json else markdown(r))


def _write(text: str) -> int:
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except BrokenPipeError:
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 141
    return 0


# ------------------------------------------------------------------ self-test

def self_test() -> int:
    """Known-good and known-bad cases over a synthetic transcript against THIS checkout's text."""
    rules = "skills/sota-golang/rules/05-security.md"
    other = "skills/sota-code-security/rules/04-cryptography.md"
    text = (ROOT / rules).read_text(encoding="utf-8")
    probes = [p for p in ccp.probes_in(text) if ccp.skip_reason(p) is None]
    start = checklist_start(other, ROOT)
    if not probes or start is None:
        print("FAIL self-test: fixture premise gone (no runnable probe in golang 05, or no checklist in 04)")
        return 1
    probe = probes[0]

    def tu(cid, name, inp):
        return {"type": "tool_use", "id": cid, "name": name, "input": inp}

    def asst(ts, *blocks):
        return {"type": "assistant", "timestamp": ts, "message": {"role": "assistant", "content": list(blocks)}}

    def result(ts, cid, err=False):
        return {"type": "user", "timestamp": ts, "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": cid, "content": "x", "is_error": err}]}}

    secret_path = "/private/acme-corp/app/main.go"
    secret_cmd = "grep -rn acme-internal-token /private/acme-corp"
    edit_entry = asst("2026-01-01T00:00:04Z", tu("t_edit", "Edit", {"file_path": secret_path, "old_string": "a", "new_string": "b"}))
    skill_entry = asst("2026-01-01T00:00:01Z", tu("t_skill", "Skill", {"skill": "sota-skills:sota"}))
    lines = [
        {"type": "user", "timestamp": "2026-01-01T00:00:00Z", "message": {"role": "user", "content": "build it"}},
        asst("2026-01-01T00:00:01Z", tu("t_skill", "Skill", {"skill": "sota-skills:sota"})),
        asst("2026-01-01T00:00:01Z", tu("t_skill", "Skill", {"skill": "sota-skills:sota"})),   # duplicate
        asst("2026-01-01T00:00:02Z", tu("t_read04", "Read", {"file_path": f"/x/{other}", "offset": 1, "limit": max(1, start - 5)})),
        asst("2026-01-01T00:00:03Z", tu("t_cat", "Bash", {"command": f"cd /private/acme-corp && cat /x/{rules}  # acme-internal"})),
        asst("2026-01-01T00:00:03Z", tu("t_pipe", "Bash", {"command": f"cat {other} | head -n {max(1, start - 5)}"})),
        edit_entry,
        asst("2026-01-01T00:00:05Z", tu("t_probe", "Bash", {"command": "cd /proj && " + probe})),
        result("2026-01-01T00:00:06Z", "t_probe", err=True),
        asst("2026-01-01T00:00:07Z", tu("t_secret", "Bash", {"command": secret_cmd})),
        asst("2026-01-01T00:00:07Z", tu("t_survey", "Bash", {"command": "rg -n " + " ".join(
            "'" + q + "'" for q in re.findall(r"'([^']+)'", probe)) + " skills"})),   # pattern only
        asst("2026-01-01T00:00:08Z", tu("t_var", "Bash", {"command": 'f="$d"/skills/x; sed -n 1,5p "$f"'})),
        {"type": "user", "timestamp": "2026-01-01T00:00:09Z", "message": {"role": "user", "content": "thanks"}},
        asst("2026-01-01T00:00:10Z", tu("t_tail", "Bash", {"command": f"tail -n 80 {other}"})),
    ]
    fails: list[str] = []
    ran = [0]

    def check(cond, msg):
        ran[0] += 1
        if not cond:
            fails.append(msg)

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "s.jsonl"
        p.write_text("\n".join(json.dumps(x) for x in lines) + "\nnot json\n", encoding="utf-8")
        s = parse([p])
        r = build(s, ROOT)
        md = markdown(r)
        f = {x["file"]: x for x in r["files"]}
        check(r["unique_tool_use_ids"] == 10 and r["tool_use_blocks"] == 11, f"dedupe: {r['unique_tool_use_ids']}/{r['tool_use_blocks']}")
        check(not any("t_survey" in pr["ids"] for pr in f.get(rules, {}).get("probes_run", [])),
              "a command carrying only the probe's pattern is not a run of the probe")
        check(r["router_invoked"], "plugin-prefixed Skill call not seen as the router")
        check(r["user_prompts"] == 2, f"prompts {r['user_prompts']} != 2 (tool_result rows are not prompts)")
        check(f.get(rules, {}).get("checklist_read") == "yes", "a whole-file cat of golang 05 covers its checklist")
        check(f.get(other, {}).get("checklist_read") == "yes", "tail -n 80 of 04 must cover its checklist")
        acc04 = f.get(other, {}).get("accesses", [])
        check(any(a["tool"] == "Read" and a["checklist"] == "no" for a in acc04), "Read stopping short of the checklist must say no")
        check(any(a["id"] == "t_pipe" and a["checklist"] == "no" for a in acc04),
              "cat FILE | head -n N stopping short is not a whole-file read")
        check(f.get(other, {}).get("checklist_reread_after_last_edit") == "yes", "tail after the edit is a re-read after the last edit")
        check(f.get(rules, {}).get("checklist_reread_after_last_edit") == "no", "golang 05 read only before the edit")
        check(any(pr["ids"] == ["t_probe"] for pr in f.get(rules, {}).get("probes_run", [])), "executed probe not matched")
        check(r["expected_language_skills_missing"] == [], "golang was read, .go edit expects nothing missing")
        check(r["edited_non_library_extensions"] == {".go": 1}, f"extensions {r['edited_non_library_extensions']}")
        check(r["other"]["unresolved library mentions"] >= 1, "a variable-built path must be counted, not dropped")
        check(r["bash_after_last_edit"] == 5, f"bash after last edit {r['bash_after_last_edit']} != 5")
        for leak in ("acme", "/private", "/proj", "build it", secret_cmd):
            check(leak not in md and leak not in json.dumps(r), f"privacy: {leak!r} leaked into the output")
        # known-bad: the language heuristic must fire when the language skill was never touched
        p2 = Path(d) / "s2.jsonl"
        p2.write_text("\n".join(json.dumps(x) for x in (lines[0], skill_entry, edit_entry)) + "\n", encoding="utf-8")
        r2 = build(parse([p2]), ROOT)
        check(r2["expected_language_skills_missing"] == ["sota-golang"], f"missing-skill heuristic: {r2['expected_language_skills_missing']}")
        check(r2["files"][0]["checklist_read"] == "n/a", "SKILL.md has no checklist")
        # known-bad: an empty transcript must refuse, not print an empty audit
        p3 = Path(d) / "empty.jsonl"
        p3.write_text('{"type":"user"}\n', encoding="utf-8")
        check(main([str(p3)]) == 2, "an audit with 0 tool calls must exit 2")
        # control characters from a transcript are escaped before printing (CWE-150)
        p4 = Path(d) / "ctrl.jsonl"
        # the timestamp is printed in the table, so an ESC there would reach the terminal
        p4.write_text(json.dumps(asst("2026-01-01T00:00:01Z\x1b[2J", tu("t_ctrl", "Skill", {"skill": "sota"}))) + "\n",
                      encoding="utf-8")
        md4 = markdown(build(parse([p4]), ROOT))
        check("\x1b" not in md4, "an ESC from a transcript id reached the output")
    # ---- diff mode, in a throwaway repo: one pre-existing hit, two new ones (modified + untracked)
    crypto = "skills/sota-golang/rules/05-security.md"
    seed_probe = [s for s in ccp.probes_in((ROOT / crypto).read_text(encoding="utf-8"))
                  if ccp.skip_reason(s) is None and s == "grep -rn 'math/rand' --include='*.go' ."]
    check(len(seed_probe) == 1, "fixture premise: the math/rand probe in golang rules/05")
    if seed_probe:
        pid = cpf.probe_id(crypto, seed_probe[0])
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "r"
            (repo / "app").mkdir(parents=True)
            g = ["git", "-C", str(repo), "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
                 "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
            subprocess.run(g + ["init", "-q"], check=True)
            (repo / "app/old.go").write_text("package app\nimport \"math/rand\"\n", encoding="utf-8")
            subprocess.run(g + ["add", "-A"], check=True)
            subprocess.run(g + ["commit", "-q", "-m", "base"], check=True)
            (repo / "app/old.go").write_text("package app\nimport \"math/rand\"\nvar _ = \"math/rand\"\n", encoding="utf-8")
            (repo / "app/new.go").write_text("package app\nimport \"math/rand\"\n", encoding="utf-8")
            (repo / "app/link.go").symlink_to("/etc/hosts")
            dp, err = diff_probes(repo, "HEAD", ROOT)
            check(not err, f"diff mode errored: {err}")
            h = next((x for x in dp.get("hits", []) if x["probe"] == pid), None)
            check(h is not None and h["new"] == 2 and h["pre_existing"] == 1,
                  f"math/rand probe: want new=2 pre=1, got {h and (h['new'], h['pre_existing'])}")
            check(dp.get("skipped_files", 0) >= 1, "an untracked symlink must be skipped, not followed")
            check(dp.get("probes_not_applicable", 0) > 0, "a --include='*.py' probe applies to no .go change")
            check(not dp.get("probes_broken"), f"probes broke on the staged tree: {dp.get('probes_broken')}")
            check(dp.get("probes_missing_path", 0) > 0,
                  "a probe naming a path the diff lacks (a workflow dir) is counted as such, not as run")
            _, bad = diff_probes(repo, "no-such-ref", ROOT)
            check("does not resolve" in bad, "an unresolvable base must be refused, never read as clean")
            j_none = join(None, dp)
            check(any(q["quadrant"].startswith("unknown") for q in j_none["quadrants"]), "no transcript -> unknown")
            fake = {"files": [{"file": crypto, "kinds": ["read"]}]}
            j_in = join(fake, dp)
            check(any(q["rules_file"] == crypto and q["quadrant"].startswith("loaded + new hit")
                      for q in j_in["quadrants"]), "loaded + new hit -> rule shape")
            check(crypto in j_in["verdict_walk"], "a loaded file is in the verdict walk")
            j_out = join({"files": []}, dp)
            check(any(q["rules_file"] == crypto and "routing gap" in q["quadrant"] for q in j_out["quadrants"]),
                  "not loaded + new hit -> routing gap")
            for x in dp["hits"]:
                x.pop("where", None)
            md5 = diff_markdown(dp, j_in, False)
            check("app/" not in md5 and "old.go" not in md5, "privacy: a hit path leaked without --show-hits")
    if fails:
        print(f"FAIL self-test: {len(fails)} of {ran[0]} checks\n  " + "\n  ".join(fails))
        return 1
    print(f"ok self-test: {ran[0]} checks over synthetic transcripts (dedupe, Bash readers and pipes, "
          "checklist range, re-read ordering, probe match, language heuristic, privacy, control chars, "
          "empty refusal)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
