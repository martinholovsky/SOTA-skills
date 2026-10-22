#!/usr/bin/env python3
"""code-rules-hook.py — after the agent writes code, name the rules file for what that code DOES.
A Claude Code PostToolUse hook on Edit|Write|MultiEdit, ON by default since ROADMAP 73 (m): the plugin
registers it (hooks/hooks.json) and install.sh's routing setup offers it.

WHY. ROADMAP 73. Reading the right rules file changes what an agent builds: with the cited files
named in the prompt, rule tests rose 0.698 -> 0.868 (sota-agent-evals v7, 2026-10-11, SUPPORTED).
Every shipped way of getting there chose the file from the TASK and failed: a hook that lists a
skill's files and asks for a full read got whole files read (79 -> 472 lines per run) but the right
one in 11/20 runs, and outcomes did not move (v8, NULL); a BM25 match of the prompt against the
rules index found a cited file for 6/20 tasks. Prompts do not name their risk: "export the orders
as CSV" never says formula injection, "fetch the callback URL" never says SSRF. The CODE does —
`csv.writer`, an outbound fetch, `zipfile` — so this hook selects from what was just written.
MEASURED: v9 (2026-10-12) reached a cited rules file in 18/20 runs (v8 11/20, files named in the
prompt 20/20), so the choice of file works, but rule tests went 0.698 -> 0.717 (NULL). In 6 of the
8 runs that failed a rule test, the agent named the tested risk and left it out as a decision for
the user ("beyond your spec"). v10 (2026-10-12) added APPLY below, saying the named rules are part
of the task: rule tests 0.717 -> 0.906 (SUPPORTED, 6 cases up, 0 down), above the arm that named the
files in the prompt (0.868), with spec tests still 20/20. v11 replaced APPLY with a bare
"MANDATORY:" label: 0.698 (NULL), and every failing run handed the rule back. The content is the
lever, not the emphasis. Shipped by default 2026-10-12 (ROADMAP 73 (m)) at +68% cost per run over the
plain install; the trigger table is in-sample: its author had read the 20 cases v9-v13 ran on, though it was
not changed after v9's replay (PRE-REGISTRATION-v9.md). OUT OF SAMPLE: v14 (2026-10-13, cases-v5,
20 tasks sampled from OWASP ASVS and authored blind to this library) ran this hook plus the router's
table against neither: reach 8/20 -> 13/20, as an offline replay of this table predicted, but cited
rule tests 0.667 -> 0.667 (NULL). Four of the five runs that reached the file and failed named the
risk and handed it back, citing the precise spec as the request ruling it out.

WHAT IT SAYS (as `additionalContext`, read next to the tool result): for each trigger the written
text matches, in table order, the absolute path of the rules file and the section to check, with
one action — read each named file in full, then check the change against it — and then (APPLY,
ROADMAP 73 (j), measured in v10) that those rules are part of the task: build each with a
conservative default rather than handing it back, unless the request rules it out, and name each
default in one line of the final message. A file is named at
most once per session, and at most PER_EVENT new files per edit, so a long session is not flooded.
"Once" holds when two copies run on one edit (the plugin's and the installer's, which Claude Code
runs in parallel): each file is claimed with an exclusive create, and only the copy that wins
names it.
Test files are skipped: what matters is what the shipped code does.

The triggers are a table of regular expressions over the written text, and they are crude on
purpose: a false trigger costs one file read, a missed one costs the rule.

IT NEVER BLOCKS: any error prints one line to stderr and exits 0 with no output.
SOTA_CODE_RULES_HOOK=off (or 0 / false / no) disables it.

Registered by the plugin; install.sh --routing adds it to ~/.claude/settings.json. By hand
(user or project settings.json):
  "hooks": {
    "PostToolUse": [{"matcher": "Edit|Write|MultiEdit", "hooks": [{"type": "command",
                     "command": "python3 /ABS/PATH/scripts/code-rules-hook.py"}]}]
  }
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIMIT = 10_000
PER_EVENT = 2
CODE_EXT = {"py", "pyi", "go", "rs", "c", "h", "cc", "cpp", "cxx", "hpp", "java", "kt", "kts",
            "cs", "php", "rb", "swift", "js", "jsx", "mjs", "cjs", "ts", "tsx", "sh", "bash"}
TEST_PATH = re.compile(r"(^|/)(tests?|spec|__tests__)/|(^|/)test_[^/]*$|_test\.\w+$|\.(test|spec)\.\w+$")

# (what the code does, pattern, [(skill, rules file number, section to check)]). Order is priority:
# specific surfaces first, the generic ones (handlers, logging, retries) last. Each row was written
# from the skills' own rules indexes, not from any eval task.
TRIGGERS: list[tuple[str, str, list[tuple[str, str, str]]]] = [
    ("fetches a URL, which is an SSRF surface whenever any part of the destination comes from a caller",
     r"urlopen|requests\.(get|post|put|head|request)\(|httpx\.|aiohttp\.|\bhttp_?get\b|\bfetch\(|"
     r"urllib\.request|http\.client|HttpClient|http\.(Get|Post|NewRequest)\(",
     [("sota-code-security", "01", "§5 SSRF")]),
    ("writes CSV or spreadsheet output",
     r"\bcsv\b|text/csv|openpyxl|xlsxwriter|\bxlsx\b",
     [("sota-code-security", "01", "§11, CSV/formula injection")]),
    ("reads or extracts an archive",
     r"zipfile|tarfile|extractall|ZipFile|\.namelist\(|archive/zip|java\.util\.zip",
     [("sota-code-security", "01", "§4 path traversal and Zip Slip"),
      ("sota-code-security", "09", "untrusted data ingestion")]),
    ("accepts a file or image from outside",
     r"upload|content[_-]type|mimetype|\bPIL\b|Image\.open|imghdr|\.(png|jpe?g|gif|webp)\b",
     [("sota-code-security", "21", "§1 file upload handling"),
      ("sota-code-security", "09", "untrusted data ingestion")]),
    ("builds an email or a message header",
     r"EmailMessage|smtplib|email\.(message|mime|utils)|[\"'](Subject|Reply-To|To|From|Cc)[\"']|send_?mail",
     [("sota-code-security", "01", "§11, CRLF / header injection")]),
    ("runs a process",
     r"subprocess|os\.system|os\.popen|shell=True|exec\.Command|Runtime\.getRuntime",
     [("sota-code-security", "01", "§3 command injection")]),
    ("builds a database query",
     r"\.execute\(|\bSELECT\b|\bINSERT\s+INTO\b|\bUPDATE\s+\w+\s+SET\b",
     [("sota-code-security", "01", "§2 SQL injection")]),
    ("parses or builds XML",
     r"xml\.|etree|lxml|minidom|XMLParser|DocumentBuilder",
     [("sota-code-security", "01", "§6 XXE and XML")]),
    ("deserialises data",
     r"pickle|yaml\.load|marshal\.loads|ObjectInputStream|unserialize\(",
     [("sota-code-security", "01", "§8 unsafe deserialization")]),
    ("renders HTML or a template",
     r"render_template|jinja|Template\(|innerHTML|dangerouslySetInnerHTML|text/html|Markup\(",
     [("sota-code-security", "05", "XSS and web security")]),
    ("checks a password or handles a login",
     r"passw(or)?d|\blogin\b|authenticat|credential|sign_?in",
     [("sota-code-security", "02", "§1, credential stuffing, lockout and enumeration")]),
    ("issues or checks a session or token",
     r"session|\btokens?\b|cookie|remember_?me|\bjwt\b|bearer",
     [("sota-code-security", "17", "§2 session management"),
      ("sota-code-security", "02", "authentication")]),
    ("decides who may do what",
     r"principal|permission|\broles?\b|_roles?\b|\broles?_|is_admin|\bowner\b|tenant|authoriz|forbidden|\b403\b",
     [("sota-code-security", "03", "§1-§3 deny by default, IDOR, function-level authorization")]),
    ("sends or receives a webhook or callback",
     r"webhook|callback_?url|x-signature|signing_secret",
     [("sota-api-design", "06", "webhooks")]),
    ("returns a list that can grow",
     r"\blimit\b|\boffset\b|\bcursor\b|page_?size|next_page",
     [("sota-api-design", "01", "§4 pagination")]),
    ("moves money or must not run twice",
     r"idempot|payment|\bcharge\b|refund|\btransfer\b",
     [("sota-api-design", "01", "§6 idempotency keys")]),
    ("calls something that can fail or hang",
     r"\bretr(y|ies)\b|backoff|timeout|time\.sleep|circuit|max_attempts",
     [("sota-architecture", "04", "§1-§3 timeouts, retries, circuit breakers")]),
    ("logs, returns errors, or returns records about people",
     r"logger\.|logging\.|traceback|str\(e\)|repr\(e\)|\bemail\b|\bphone\b|password_hash",
     [("sota-code-security", "07", "§1, §2 and §4: errors, logs, response over-exposure")]),
    ("adds a request handler or endpoint, which needs abuse control keyed to the caller",
     r"def \w+\(self,\s*(principal|req|request)\b|@(app|router|bp)\.(get|post|put|delete|patch|route)\(|"
     r"\b(status_code|status)\s*[,=:]\s*(200|201|400|401|403|404|409|429)\b|return\s*\(?\s*(200|201|400|401|403|404|409|429)\s*,",
     [("sota-api-design", "07", "§2 rate limiting"),
      ("sota-code-security", "06", "§5 resource exhaustion")]),
]
COMPILED = [(what, re.compile(rx, re.I), refs) for what, rx, refs in TRIGGERS]


def skill_dir(name: str) -> Path | None:
    """The copy of the skill the session loads: the user config first, then a plugin root, then
    this checkout (the same order as skill-depth-hook.py)."""
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


def rules_file(skill: str, num: str) -> Path | None:
    d = skill_dir(skill)
    hits = sorted((d / "rules").glob(num + "-*.md")) if d else []
    return hits[0] if hits else None


def written_text(tool_input: dict) -> str:
    parts = [tool_input.get("content"), tool_input.get("new_string")]
    parts += [e.get("new_string") for e in tool_input.get("edits") or [] if isinstance(e, dict)]
    return "\n".join(p for p in parts if isinstance(p, str))


def state_dir(session_id: str) -> Path:
    """One marker file per rules file named in this session; its content is the path."""
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", session_id or "nosession")[:80]
    return Path(tempfile.gettempdir()) / "sota-code-rules-hook" / safe


def named_before(d: Path) -> set[str]:
    try:
        return {m.read_text(encoding="utf-8") for m in d.iterdir()}
    except OSError:
        return set()


def claim(d: Path, p: Path) -> bool:
    """True for exactly one caller per (session, file), even when two copies race."""
    d.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(d / hashlib.sha256(str(p).encode()).hexdigest()[:32],
                     os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(str(p))
    return True


def select(text: str, already: set[str]) -> list[tuple[str, Path, str]]:
    """(what the code does, rules file, sections) for up to PER_EVENT files not named before. A
    second trigger naming a file already picked adds its reason and section to that entry."""
    picked: dict[Path, tuple[list[str], list[str]]] = {}
    for what, rx, refs in COMPILED:
        if not rx.search(text):
            continue
        for skill, num, section in refs:
            p = rules_file(skill, num)
            if p is None or str(p) in already:
                continue
            if p in picked:
                if what not in picked[p][0]:
                    picked[p][0].append(what)
                picked[p][1].append(section)
            elif len(picked) < PER_EVENT:
                picked[p] = ([what], [section])
    return [("; ".join(w), p, "; ".join(s)) for p, (w, s) in picked.items()]


APPLY = ("These rules apply to this change: they are part of what was asked, not extras beyond the spec. "
         "Build what each one requires now, with a conservative default (a cap, a limit, an allow-list, a "
         "guard). Do not hand it back as a question or a note instead of building it, unless the user's "
         "request explicitly rules it out. In your final message, name each default you chose in one line, "
         "so the user can change it.")


def message(path: str, picks: list[tuple[str, Path, str]]) -> str:
    lines = ["SOTA: the code you just wrote in %s:" % path]
    for what, p, section in picks:
        lines.append("- %s. Its rules: %s (check %s)" % (what, p, section))
    lines.append("Read each file named above in full now — every line, with no offset, limit, head, "
                 "line range or grep, because a rule you did not read cannot be applied. Then check "
                 "this change against it, including the Audit checklist at its end, before you finish.")
    lines.append(APPLY)
    return "\n".join(lines)


def respond(event: dict) -> str:
    """The JSON to print for one PostToolUse event, or "" for nothing. Records what it named."""
    if event.get("tool_name") not in {"Edit", "Write", "MultiEdit"}:
        return ""
    ti = event.get("tool_input") or {}
    path = str(ti.get("file_path") or "")
    ext = path.rsplit(".", 1)[-1].lower() if "." in path.rsplit("/", 1)[-1] else ""
    if ext not in CODE_EXT or TEST_PATH.search(path):
        return ""
    sd = state_dir(str(event.get("session_id") or ""))
    picks = [x for x in select(written_text(ti), named_before(sd)) if claim(sd, x[1])]
    if not picks:
        return ""
    return json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                              "additionalContext": message(path, picks)[:LIMIT]}})


TABLE_HEADING = "## What your code does: the rules outside this skill"


def table() -> str:
    """The trigger table as Markdown for a language skill's SKILL.md, paths relative to that file.
    The same rows the hook fires on, so an index link and the hook name the same files."""
    out = [TABLE_HEADING, "",
           "When the code you write does one of these things, the rule for it lives in another skill. "
           "Read that file in full before you finish, and check your change against its Audit checklist.",
           "", "| When your code... | Read in full | Check |", "|---|---|---|"]
    for what, _, refs in TRIGGERS:
        for skill, num, section in refs:
            hits = sorted((ROOT / "skills" / skill / "rules").glob(num + "-*.md"))
            if hits:
                rel = "../%s/rules/%s" % (skill, hits[0].name)
                out.append("| %s | [%s rules/%s](%s) | %s |" % (what, skill, num, rel, section))
    return "\n".join(out) + "\n"


ROUTER = ROOT / "skills" / "sota" / "SKILL.md"
ROUTER_HEADING = "## What your code does: the rules file to read"


def router_table() -> str:
    """The same triggers as a section of the router (ROADMAP 73 (o)), one row per set of files, so
    an agent that never runs this hook (any host but Claude Code) still finds the file from the
    words of its task. v12: a cited file was reached in 5 of 7 tasks where the router linked it next
    to matching words, 1 of 13 where it did not. Generated; the self-test fails if the router's copy
    differs."""
    groups: dict[tuple, list[str]] = {}            # one row per set of files, in table order
    for what, _, refs in TRIGGERS:
        what = what.split(", which")[0]
        if len(refs) == 1:                         # one file: its section goes beside the words
            skill, num, section = refs[0]
            groups.setdefault(((skill, num, ""),), []).append("%s (%s)" % (what, section))
        else:
            groups.setdefault(tuple(refs), []).append(what)
    out = [ROUTER_HEADING, "",
           "When the code you are about to write does one of these things, read the file in full, then",
           "check your change against it and its Audit checklist before you finish. " + APPLY, "",
           "| When your code... | Read in full, then check |", "|---|---|"]
    for refs, whats in groups.items():
        cells = []
        for skill, num, section in refs:
            hits = sorted((ROOT / "skills" / skill / "rules").glob(num + "-*.md"))
            if hits:
                cells.append(("[`%s` rules/%s](../%s/rules/%s) %s" % (skill, num, skill, hits[0].name, section)).rstrip())
        out.append("| %s | %s |" % ("; ".join(whats), "; ".join(cells)))
    return "\n".join(out) + "\n"


def router_section(text: str) -> str:
    """The router's copy: from ROUTER_HEADING to the next level-2 heading."""
    i = text.find(ROUTER_HEADING)
    if i < 0:
        return ""
    j = text.find("\n## ", i + len(ROUTER_HEADING))
    return text[i:j + 1 if j >= 0 else len(text)].rstrip("\n") + "\n"


def main() -> int:
    if os.environ.get("SOTA_CODE_RULES_HOOK", "on").lower() in {"off", "0", "false", "no"}:
        return 0
    try:
        out = respond(json.load(sys.stdin))
    except Exception as e:                      # never block a tool result
        print("sota code-rules-hook: %s: %s — no hint this time" % (type(e).__name__, e),
              file=sys.stderr)
        return 0
    if out:
        print(out)
    return 0


def self_test() -> int:
    """Drives the script as Claude Code does (JSON on stdin) and checks its output."""
    fails: list[str] = []
    n = 0

    def check(label, cond):
        nonlocal n
        n += 1
        if not cond:
            fails.append(label)

    with tempfile.TemporaryDirectory() as t:
        env = {k: v for k, v in os.environ.items() if k != "SOTA_CODE_RULES_HOOK"}
        env.update({"TMPDIR": t, "HOME": t, "CLAUDE_CONFIG_DIR": str(Path(t) / "no-config")})   # resolve to THIS checkout

        def run(event, extra=None, raw=None):
            p = subprocess.run([sys.executable, str(Path(__file__).resolve())],
                               input=raw if raw is not None else json.dumps(event),
                               capture_output=True, text=True, env=dict(env, **(extra or {})), timeout=30)
            c = json.loads(p.stdout)["hookSpecificOutput"]["additionalContext"] if p.stdout.strip() else ""
            return p.returncode, c, p.stderr

        def ev(sid, path, text, tool="Write"):
            ti = {"file_path": path, "content": text} if tool == "Write" else {"file_path": path, "new_string": text}
            return {"tool_name": tool, "session_id": sid, "tool_input": ti}

        cs01 = str(ROOT / "skills" / "sota-code-security" / "rules")
        rc, c, _ = run(ev("s1", "/w/shop/export.py", "import csv\nw = csv.writer(f)\n"))
        check("csv: exit 0", rc == 0)
        check("csv: names code-security/01 by absolute path", (cs01 + "/01-") in c and "CSV/formula" in c)
        check("csv: one concrete action, a full read", "Read each file named above in full" in c
              and "Audit checklist" in c)
        check("csv: the rule is part of the task, with no hand-back exit", "they are part of what was asked" in c
              and "Do not hand it back" in c and "conservative default" in c)
        rc, c, _ = run(ev("s1", "/w/shop/export.py", "w.writerow(row)  # csv again\nimport csv\n", "Edit"))
        check("same file is not named twice in a session", c == "")
        rc, c, _ = run(ev("s2", "/w/shop/export.py", "import csv\n", "Edit"))
        check("another session names it again", "01-" in c)
        rc, c, _ = run(ev("s3", "/w/shop/a.py", "import zipfile\nz.extractall(d)\nr = requests.get(u)\n"))
        check("at most %d files per edit" % PER_EVENT, c.count("Its rules:") == PER_EVENT)
        check("table order: the fetch (row 1) before the archive (row 3)",
              c.find("SSRF") != -1 and c.find("SSRF") < c.find("Zip Slip"))
        check("a second section of a file already picked is merged, not dropped",
              c.count("01-input-injection") == 1 and "Zip Slip" in c and "09-untrusted" in c)
        rc, c, _ = run(ev("s4", "/w/shop/api.py", "    def search(self, q):\n        return 200, {}\n", "Edit"))
        check("handler: names the rate-limiting files", "07-security-operations" in c and "06-memory" in c)
        rc, c, _ = run({"tool_name": "MultiEdit", "session_id": "s5",
                        "tool_input": {"file_path": "/w/a.py", "edits": [{"old_string": "x", "new_string": "import tarfile"}]}})
        check("MultiEdit edits are read", "Zip Slip" in c)
        for label, e in (("test file is silent", ev("s6", "/w/tests/test_export.py", "import csv")),
                         ("test_ prefix is silent", ev("s6", "/w/test_export.py", "import csv")),
                         ("markdown is silent", ev("s6", "/w/README.md", "export as csv")),
                         ("no trigger is silent", ev("s6", "/w/a.py", "x = 1 + 2\n")),
                         ("other tool is silent", {"tool_name": "Bash", "tool_input": {"command": "csv"}})):
            rc, c, _ = run(e)
            check(label, rc == 0 and c == "")
        rc, c, _ = run(ev("s7", "/w/a.py", "import csv"), {"SOTA_CODE_RULES_HOOK": "off"})
        check("opt-out is silent", rc == 0 and c == "")
        # Two copies on one edit (plugin + installer, run in parallel) must not both name a file.
        # Checked on claim() itself: two parallel processes barely overlap, so a run-twice test
        # passed even with the exclusive create removed (watched 2026-10-12).
        d, f = Path(t) / "claim", ROOT / "x.md"
        check("claim: the first caller wins", claim(d, f) is True)
        check("claim: a second caller for the same file loses", claim(d, f) is False)
        check("claim: the marker records the path", named_before(d) == {str(f)})
        rc, c, err = run(None, raw="{not json")
        check("malformed input: exit 0, no output, says why", rc == 0 and c == "" and "code-rules-hook" in err)

    # Labelled trigger cases from three field reports of 2026-10-20 (ADOPTION-LOG). Checked on the
    # compiled table directly, because the once-per-session rule would hide a second fire.
    def fires(what, text):
        return any(w.startswith(what) and rx.search(text) for w, rx, _ in COMPILED)

    for text in ('@require_role("editor")', "if not current_user.roles: deny()",
                 "SELECT * FROM user_roles", 'if not has_role(u, "ops"): deny()', "role_required(x)"):
        check("authorization form fires (a missed one costs the rule): %s" % text,
              fires("decides who may do what", text))
    # KNOWN false triggers, kept firing ON PURPOSE until a labelled set exists to tighten against
    # (ADOPTION-LOG 2026-10-20 deferral). If one of these stops firing, resolve that deferral.
    for what, text in (("logs, returns errors", "git -c user.email=t@example.invalid commit"),
                       ("returns a list that can grow", 'p.add_argument("--limit", type=int)'),
                       ("decides who may do what", 'role = m.get("role")\nif role == "user": pass'),
                       # 2026-10-21 field report: an HTTP-status client, and a CLI's error message
                       ("decides who may do what", 'if r.status == 403:\n    raise RuntimeError(f"GET {url} refused")'),
                       ("checks a password or handles a login",
                        'print("error: not authenticated with the registry", file=sys.stderr)'),
                       # 2026-10-22 field report: an OS tracing session, no authentication in sight
                       ("issues or checks a session or token",
                        "/// Decodes Task Scheduler events read from a private ETW session.")):
        check("known false trigger still fires (see the deferral before changing): %s" % what,
              fires(what, text))

    # The real checkout: every file a trigger names exists, and every pattern compiles and fires on
    # at least one sample of its own (no dead row).
    missing = sorted({"%s/%s" % (s, n) for _, _, refs in TRIGGERS for s, n, _ in refs if rules_file(s, n) is None})
    check("every named rules file exists: %s" % missing, not missing)
    check("every trigger names at least one file", all(refs for _, _, refs in TRIGGERS))
    rows = [l for l in table().splitlines() if l.startswith("| ") and "](../" in l]
    check("--table: one row per (trigger, file) pair (%d)" % len(rows),
          len(rows) == sum(len(refs) for _, _, refs in TRIGGERS))
    check("the router's table is the generated one (python3 scripts/code-rules-hook.py --router-table)",
          router_section(ROUTER.read_text(encoding="utf-8")) == router_table())
    for f in fails:
        print("FAIL:", f)
    print("%s: %d/%d" % ("FAIL" if fails else "PASS", n - len(fails), n))
    return 1 if fails else 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--router-table"]:
        sys.stdout.write(router_table())
        sys.exit(0)
    if sys.argv[1:] == ["--table"]:
        sys.stdout.write(table())
        sys.exit(0)
    sys.exit(self_test() if sys.argv[1:] == ["--self-test"] else main())
