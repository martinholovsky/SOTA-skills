#!/usr/bin/env python3
"""zsh-equals-hook.py — refuse a Bash command whose unquoted `=word` zsh would rewrite or abort on.
A Claude Code PreToolUse hook on Bash, ON by default since 2026-10-21 (operator decision, ADOPTION-LOG):
the plugin registers it (hooks/hooks.json) and install.sh's routing setup offers it.

WHY. zsh's EQUALS option (on by default) expands an unquoted word starting with `=` to the path of
the command it names: `=ls` becomes `/bin/ls`, silently. A word that names no command aborts the
whole list at that point: `cat a; echo ===; grep x b` prints `a`, then `(eval):1: == not found`,
and the grep never runs. The part before the cut reads as a complete answer
(sota-shell-scripting rules/06 §1, the `EQUALS` row). The row did not stop the habit: a field report
(2026-10-21) records the row read at 07:30:02Z and broken at 07:31:02Z. A separator typed before
the next command is a reflex, and reading a rule does not change it, so this is the structural
control. MEASURED 2026-10-21 over one operator's local transcripts, 43,848 Bash calls in 1,836
files: 345 ended in `(eval):N: <word> not found`. The counts at the time of writing are in the
ADOPTION-LOG row; re-derive them rather than trusting this line.

WHAT IT FLAGS: a word that begins, unquoted, with `=` and is longer than `=` itself, outside
heredoc bodies, comments and arithmetic `(( ))`. Inside `[[ ]]` the operators `=`, `==` and `=~`
are exempt, because zsh parses them there. Bare `==` OUTSIDE `[[ ]]` is flagged: `[ a == a ]` aborts
with `= not found` (zsh 5.9, measured). The line-499 lint regex in rules/06 missed that shape.
A double-quoted `"$( … )"` is lexed as the command line it is. A cut inside `( )`, `$( )` or a
function body ends only that subshell or that call (measured), so it is flagged all the same: the
half that answers the question is still the half that never ran. NOT LEXED: backquotes inside
double quotes, and `case` patterns. A miss there costs what no hook costs today.

ONLY UNDER zsh: it acts when $SHELL's basename is `zsh`, which is the shell Claude Code runs Bash
commands in. Under bash `echo ===` is harmless and the hook allows everything.
SOTA_ZSH_EQUALS_HOOK=off (or 0 / false / no) disables it, and =on forces it regardless of $SHELL.

ON A HIT it exits 2 with the reason on stderr. Claude Code blocks the call and shows Claude that
text as the tool's error (code.claude.com/docs/en/hooks, "Exit code 2", verified 2026-10-21). It
never rewrites the command: a silent rewrite would hide the habit on every host without the hook.
Every internal error allows and says so on stderr (fail-open, loudly: a broken guard must not brick
the shell).

Install without the plugin (user or project settings.json; install.sh --routing writes this):
  "hooks": {
    "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 /ABS/PATH/scripts/zsh-equals-hook.py"}]}]
  }
Lint a snippet or a checklist (the rules/06 audit item): python3 scripts/zsh-equals-hook.py --check
FILE… — each file is lexed as one zsh command line; exit 1 on any hit, 2 on an unreadable file, and
it prints the bytes it read beside the verdict, so a zero is not a lint that read nothing.
Self-test: python3 scripts/zsh-equals-hook.py --self-test   (add --require-zsh to fail when zsh is
absent rather than skip the half that checks each case against the real shell)
"""
import json
import os
import sys

# shutil, subprocess and tempfile are imported inside self_test(): this runs before every Bash
# call, and moving them here took a call from 137 to 85 ms median (bare python3: 69; 2026-10-21).

OPERATORS = set(";&|()<>`\n")
COND_OPERATORS = {"=", "==", "=~"}


def _skip_quoted(s, i, quote, subs=None):
    """i is just past the opening quote; return the index just past the closing one. Inside
    double quotes a `$( … )` is a nested command line with quotes of its own: it is skipped as a
    unit (else its inner `"` ends the string early and the quoting desyncs) and, when `subs` is
    given, appended to it so the caller can lex it, since zsh expands `=word` in there too."""
    while i < len(s):
        c = s[i]
        if c == "\\" and quote != "'":
            i += 2
            continue
        if c == quote:
            return i + 1
        if quote == '"' and s.startswith("$(", i) and not s.startswith("$((", i):
            end = _skip_cmdsub(s, i + 2)
            if subs is not None:
                subs.append(s[i + 2:end - 1])
            i = end
            continue
        i += 1
    return i


def _skip_cmdsub(s, i):
    """i is just past `$(`; return the index just past the matching `)`."""
    depth = 1
    while i < len(s) and depth:
        c = s[i]
        if c in "'\"":
            i = _skip_quoted(s, i + 1, c)
            continue
        if c == "\\":
            i += 2
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        i += 1
    return i


def _skip_arith(s, i):
    """i is just past `((`; return the index just past the matching `))`."""
    depth = 2
    while i < len(s) and depth:
        if s[i] == "(":
            depth += 1
        elif s[i] == ")":
            depth -= 1
        i += 1
    return i


def _read_heredoc_word(s, i):
    """i is just past `<<`; return (delimiter, strip_tabs, index after the delimiter word)."""
    strip = i < len(s) and s[i] == "-"
    if strip:
        i += 1
    while i < len(s) and s[i] in " \t":
        i += 1
    word = []
    while i < len(s) and s[i] not in " \t" and s[i] not in OPERATORS:
        if s[i] in "'\"":
            end = _skip_quoted(s, i + 1, s[i])
            word.append(s[i + 1:end - 1])
            i = end
        elif s[i] == "\\":
            word.append(s[i + 1:i + 2])
            i += 2
        else:
            word.append(s[i])
            i += 1
    return "".join(word), strip, i


def equals_words(cmd):
    """Return the unquoted `=word`s zsh's EQUALS would expand, in order."""
    s, i, found = cmd, 0, []
    at_start, cond, heredocs = True, 0, []
    while i < len(s):
        c = s[i]
        if c == "\n":
            i += 1
            for delim, strip in heredocs:
                while i < len(s):
                    end = s.find("\n", i)
                    end = len(s) if end < 0 else end
                    line = s[i:end]
                    i = end + 1
                    if (line.lstrip("\t") if strip else line) == delim:
                        break
            heredocs, at_start = [], True
            continue
        if c in " \t":
            i, at_start = i + 1, True
            continue
        if s.startswith("<<", i) and not s.startswith("<<<", i):
            delim, strip, i = _read_heredoc_word(s, i + 2)
            heredocs.append((delim, strip))
            at_start = True
            continue
        if at_start and c == "#":
            end = s.find("\n", i)
            i = len(s) if end < 0 else end
            continue
        if s.startswith("$((", i) or (at_start and s.startswith("((", i)):
            i = _skip_arith(s, i + (3 if c == "$" else 2))
            at_start = False
            continue
        if c in OPERATORS:
            i, at_start = i + 1, True
            continue
        if at_start:
            end, subs = i, []
            while end < len(s) and s[end] not in " \t" and s[end] not in OPERATORS:
                end = _skip_quoted(s, end + 1, s[end], subs) if s[end] in "'\"" else end + 1
            word = s[i:end]
            for inner in subs:
                found.extend(equals_words(inner))
            if word == "[[":
                cond += 1
            elif word == "]]" and cond:
                cond -= 1
            elif word.startswith("=") and word != "=" and not (cond and word in COND_OPERATORS):
                found.append(word)
            i, at_start = end, False
            continue
        if c in "'\"":
            subs = []
            i = _skip_quoted(s, i + 1, c, subs)
            for inner in subs:
                found.extend(equals_words(inner))
        elif c == "\\":
            i += 2
        else:
            i += 1
    return found


def reason(words):
    shown = ", ".join(f"`{w}`" for w in words[:5])
    return (
        f"zsh EQUALS: unquoted {shown} begins with `=`. zsh rewrites `=cmd` to that command's path, "
        "and a word naming no command aborts the whole list right there: what ran before it "
        "prints, nothing after it runs. Quote it (`echo '==='`), separate with `echo ---`, and "
        "use `[[ a == b ]]` rather than `[ a == b ]`. Not run. "
        "(sota-shell-scripting rules/06 §1; this hook: scripts/zsh-equals-hook.py)"
    )


def active():
    mode = os.environ.get("SOTA_ZSH_EQUALS_HOOK", "").lower()
    if mode in {"off", "0", "false", "no"}:
        return False
    if mode in {"on", "1", "true", "yes"}:
        return True
    return os.path.basename(os.environ.get("SHELL", "")) == "zsh"


def main():
    try:
        if not active():
            return 0
        event = json.load(sys.stdin)
        if event.get("tool_name") != "Bash":
            return 0
        cmd = (event.get("tool_input") or {}).get("command")
        if not isinstance(cmd, str):
            return 0
        words = equals_words(cmd)
        if words:
            print(reason(words), file=sys.stderr)
            return 2
        return 0
    except Exception as e:  # noqa: BLE001 -- the hook's top-level boundary: fail open, loudly
        print(f"zsh-equals-hook: internal error, allowing: {e!r}", file=sys.stderr)
        return 0


# (command, expected flagged words). Every case with a zsh verdict is ALSO run in real zsh by the
# self-test, and the verdict must agree: True = zsh cut the list or rewrote the word.
CASES = [
    ("echo ===; echo AFTER", ["==="], True),
    ("echo =====; echo AFTER", ["====="], True),
    ("echo a | head -1; echo ===; echo AFTER", ["==="], True),
    ("[ a == a ] && echo AFTER", ["=="], True),
    ("echo a ==; echo AFTER", ["=="], True),
    ("echo ==x; echo AFTER", ["==x"], True),
    ("echo =nosuchcmdxyz; echo AFTER", ["=nosuchcmdxyz"], True),
    ("echo =ls", ["=ls"], True),                       # silent: prints /bin/ls
    ("(echo ===; echo AFTER)", ["==="], True),        # cuts the subshell only
    ("x=$(echo ===; echo AFTER); echo $x", ["==="], True),
    ("echo ---; echo AFTER", [], False),
    ("echo '==='; echo AFTER", [], False),
    ('echo "==="; echo AFTER', [], False),
    ("echo \\===; echo AFTER", [], False),
    ("[[ a == a ]] && echo AFTER", [], False),
    ("[[ a = a ]] && [[ ab =~ b ]] && echo AFTER", [], False),
    ("x=1; [[ $x == 1 ]] && echo AFTER", [], False),
    ("[ a = a ] && echo AFTER", [], False),
    ("a=b cmd=c; echo AFTER", [], False),
    ("awk -F= 'BEGIN{print \"AFTER\"}'", [], False),
    ("echo --opt=val; echo AFTER", [], False),
    ("echo =; echo AFTER", [], False),
    ("(( 1 ==1 )) && echo AFTER", [], False),
    ("echo $(( 1 ==1 )); echo AFTER", [], False),
    ("echo x # ===\necho AFTER", [], False),
    ("cat <<'E'\n===\nE\necho AFTER", [], False),
    ("cat <<E\n=== $HOME\nE\necho AFTER", [], False),
    ("cat <<-E\n\t===\n\tE\necho AFTER", [], False),
    ("python3 -c 'x = 1' ; echo AFTER", [], False),
    ('grep -n "_decompress =" /dev/null; echo AFTER', [], False),
    ("cat <<<'==='; echo AFTER", [], False),
    ('echo "$(echo ===; echo AFTER)"', ["==="], True),
    ('G(){ echo a; echo ====; echo AFTER; }; G', ["===="], True),
    ('echo "n=$(grep -c "^a = \\"b\\"$" /dev/null)" && echo "=== x" && echo AFTER', [], False),
    ("echo \"$(jq -n '\"\\(1)=\\(2)\"')\"; echo AFTER", [], False),
]


def self_test(require_zsh):
    import shutil
    import subprocess
    import tempfile

    fails = 0
    for cmd, want, _ in CASES:
        got = equals_words(cmd)
        if got != want:
            fails += 1
            print(f"FAIL lexer {cmd!r}: want {want} got {got}")
    print(f"lexer: {len(CASES) - fails}/{len(CASES)} cases")

    zsh = shutil.which("zsh")
    if zsh is None:
        if require_zsh:
            print("FAIL: zsh not found and --require-zsh given")
            return 1
        print("SKIP: zsh not found, so the cases were not checked against the real shell")
    else:
        bad = 0
        for cmd, _, cut in CASES:
            r = subprocess.run([zsh, "-fc", cmd], check=False, capture_output=True, text=True, timeout=10,
                               cwd="/", stdin=subprocess.DEVNULL)
            # True = zsh cut the list or rewrote a word: AFTER missing, or `=ls` became a path
            real = ("AFTER" not in r.stdout) if "AFTER" in cmd else ("/ls" in r.stdout)
            if real != cut:
                bad += 1
                print(f"FAIL zsh disagrees on {cmd!r}: expected cut={cut}, zsh cut={real} "
                      f"(stderr {r.stderr.strip()[:60]!r})")
        fails += bad
        print(f"zsh ({zsh}): {len(CASES) - bad}/{len(CASES)} verdicts agree")

    # the hook end to end: event in, exit code and stderr out
    def run(cmd, env_extra, tool="Bash"):
        env = {k: v for k, v in os.environ.items() if k != "SOTA_ZSH_EQUALS_HOOK"}
        env.update(env_extra)
        ev = json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool,
                         "tool_input": {"command": cmd}})
        r = subprocess.run([sys.executable, os.path.abspath(__file__)], input=ev,
                           check=False, capture_output=True, text=True, env=env, timeout=30)
        return r.returncode, r.stderr

    e2e = [
        ("deny under zsh", run("echo ===; ls", {"SHELL": "/bin/zsh"}), 2, "EQUALS"),
        ("allow clean under zsh", run("echo ---; ls", {"SHELL": "/bin/zsh"}), 0, ""),
        ("allow under bash", run("echo ===; ls", {"SHELL": "/bin/bash"}), 0, ""),
        ("forced on", run("echo ===", {"SHELL": "/bin/bash", "SOTA_ZSH_EQUALS_HOOK": "on"}), 2, "EQUALS"),
        ("opt-out", run("echo ===", {"SHELL": "/bin/zsh", "SOTA_ZSH_EQUALS_HOOK": "off"}), 0, ""),
        ("other tool", run("echo ===", {"SHELL": "/bin/zsh"}, tool="Read"), 0, ""),
    ]
    for name, (rc, err), want_rc, want_err in e2e:
        if rc != want_rc or want_err not in err:
            fails += 1
            print(f"FAIL e2e {name}: rc={rc} (want {want_rc}) stderr={err.strip()[:80]!r}")
    r = subprocess.run([sys.executable, os.path.abspath(__file__)], input="not json",
                       check=False, capture_output=True, text=True, timeout=30,
                       env={**os.environ, "SOTA_ZSH_EQUALS_HOOK": "on"})
    if r.returncode != 0 or "internal error" not in r.stderr:
        fails += 1
        print(f"FAIL e2e fail-open: rc={r.returncode} stderr={r.stderr.strip()[:80]!r}")
    with tempfile.TemporaryDirectory() as d:
        bad, good = os.path.join(d, "bad.sh"), os.path.join(d, "good.sh")
        with open(bad, "w", encoding="utf-8") as f:
            f.write("cat a\necho ===\ngrep x b\n")
        with open(good, "w", encoding="utf-8") as f:
            f.write("cat a\necho ---\n")
        me = [sys.executable, os.path.abspath(__file__), "--check"]
        for name, argv, want in [("check hit", [bad], 1), ("check clean", [good], 0),
                                 ("check unreadable", [os.path.join(d, "nope")], 2),
                                 ("check no files", [], 2)]:
            r = subprocess.run(me + argv, check=False, capture_output=True, text=True, timeout=30)
            if r.returncode != want:
                fails += 1
                print(f"FAIL {name}: rc={r.returncode} (want {want}) {r.stdout.strip()[:80]!r}")
    print(f"end to end: {len(e2e) + 5} checks")
    print("ok" if not fails else f"FAILED: {fails}")
    return 1 if fails else 0


def check(paths):
    if not paths:
        print("zsh-equals-hook --check: no files given", file=sys.stderr)
        return 2
    total, rc = 0, 0
    for path in paths:
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            print(f"{path}: unreadable: {e}", file=sys.stderr)
            return 2
        total += len(text.encode())
        for w in equals_words(text):
            print(f"{path}: unquoted {w}")
            rc = 1
    print(f"checked {len(paths)} file(s), {total} bytes: {'HITS' if rc else 'clean'}")
    return rc


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(check(sys.argv[sys.argv.index("--check") + 1:]))
    if "--self-test" in sys.argv:
        sys.exit(self_test("--require-zsh" in sys.argv))
    sys.exit(main())
