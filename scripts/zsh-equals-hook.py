#!/usr/bin/env python3
r"""zsh-equals-hook.py — refuse a Bash command whose unquoted `=word` zsh would rewrite or abort on,
or whose `set -- $scalar` zsh would not split, and (2026-10-27) four more bash habits zsh breaks:
a variable named `path`/`status`, a spaced literal expanded unquoted as arguments, `PIPESTATUS`/
`BASH_REMATCH`, and a `git grep` regex escape the platform reads as a plain letter.
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

ALSO FLAGS (2026-10-25): `set -- $p` or `set -- ${p}` on a scalar, at the start of a simple
command (after `do`, `then`, `{` and the like). zsh does not word-split an unquoted scalar, so it
sets ONE positional parameter and `$2` is empty: a field report (2026-10-24) has `set -- $p; ssh
-p "$2"` end in `Bad port ''`. Exempt: `$@`, `$*`, `$argv`, `${=p}`, `${(s: :)p}`, `$(cmd)`,
quoted `"$p"`, and a name assigned as an array in the same command (`a=(x y)`). MEASURED over
66,195 local agent Bash calls: 13 matched, all intended splits; every zsh session whose outcome is
visible failed downstream (one argument), so the false-refusal count found there is 0.

ALSO FLAGS (2026-10-27, ROADMAP 85). MEASURED before shipping over 39,715 unique local agent Bash
calls (tool_use ids deduplicated, heredoc bodies and quoted text not lexed), each hit read against
its joined result; the ADOPTION-LOG 2026-10-27 rows carry the method and the examples.
  - `path` or `status` assigned: `for path in`, `read … path`, `local/export/typeset path`,
    `path=…`, `status=$?`. `path` is tied to $PATH (every later command `command not found`),
    `status` is read-only. Exempt: `path=(… $path)`, the zsh idiom. 2 hits, 2 real (rules/06 §1).
  - a name assigned a quoted literal holding a space earlier in the same command, then expanded
    unquoted as an argument or a `for … in` list (`C="--a x"; cmd $C`): zsh passes ONE word.
    Deliberately narrow (`cmd $file` is usually right): not `echo`/`print`/`[`/`test`/declarations,
    not `${=C}`, `"$C"`, or a name reassigned or assigned an array. 9 hits, 9 real (rules/06 §1).
  - `$PIPESTATUS`, `${PIPESTATUS[n]}`, `$BASH_REMATCH`, `${BASH_REMATCH[n]}`, unquoted or in double
    quotes: unset in zsh, so empty. Exempt: single quotes (`bash -c '…'`), `\$`, a `:-` fallback
    (`${pipestatus[1]:-$PIPESTATUS}`), and BASH_REMATCH after `setopt bash_rematch`. 8 hits, 8 real
    (the fallback exemption was added on that corpus, after 1 false refusal).
  - `git grep` with `\b \B \< \> \s \S \w \W \d \D` in an -E pattern on macOS, and `\d`/`\D` under -E
    or the default BRE elsewhere (rules/06 §2f). Measured 2026-10-27: macOS git 2.55.0 reads every
    one of them under -E as the plain letter (`a\b` matches `ab`) and honours them under BRE; Debian
    git 2.47.3 (glibc) honours all but `\d`/`\D`, under both. So the check reads sys.platform. 72
    hits; re-run in their repos as -E against -P, 25 had silently dropped matches, 21 gave the same
    count at today's HEAD, 23 could not be re-run, and 3 were deliberate reproductions of this trap.
  The git grep failure is not zsh's: bash on macOS has it too, but the hook acts only under zsh.

ONLY UNDER zsh: it works out the shell Claude Code runs Bash commands in the way Claude Code does
(CLAUDE_CODE_SHELL, then $SHELL, then the first zsh or bash on PATH; see agent_shell) and acts only
when that is zsh. Under bash `echo ===` is harmless and the hook allows everything.
To reproduce one of these traps on purpose, run it inside `zsh -fc '…'`: quoted text is not lexed.
SOTA_ZSH_EQUALS_HOOK=off (or 0 / false / no) disables it, and =on forces it whatever the shell.

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
import re
import sys

# shutil, subprocess and tempfile are imported inside self_test(): this runs before every Bash
# call, and moving them here took a call from 137 to 85 ms median (bare python3: 69; 2026-10-21).

OPERATORS = set(";&|()<>`\n")
COND_OPERATORS = {"=", "==", "=~"}
# `set -- $p` in zsh: an unquoted scalar is NOT word-split (no SH_WORD_SPLIT), so it sets ONE
# positional parameter. `$@`, `$*`, `$argv`, `${=p}`, `${(s: :)p}` and `$(cmd)` do not match.
SCALAR_REF = re.compile(r"\$(?:([A-Za-z_][A-Za-z0-9_]*)|\{([A-Za-z_][A-Za-z0-9_]*)\})")
ARRAY_ASSIGN = re.compile(r"(?:^|[\s;&|(])(?:typeset -a |local -a |declare -a )?([A-Za-z_][A-Za-z0-9_]*)=\(")
RESERVED = {"do", "then", "else", "elif", "{", "!", "time", "if", "while", "until"}
ASSIGN = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)\+?=(.*)", re.DOTALL)
# zsh special parameters a bash habit clobbers: `path` is tied to $PATH, `status` is read-only.
SPECIAL_NAMES = {"path", "status"}
DECLARE = {"local", "typeset", "declare", "export", "readonly", "integer", "float", "private"}
# `read` options that take the NEXT word as a value rather than a variable name
READ_VALUE_OPTS = set("dupitnNk")
# bash-only variables that zsh leaves unset: `${pipestatus[1]}` and `$match` are the zsh names
BASH_VARS = re.compile(r"\$\{?(PIPESTATUS|BASH_REMATCH)(?![A-Za-z0-9_])")
# The escapes `git grep` patterns silently fail on, measured 2026-10-27 over a file holding
# `foo 53 bar`: on macOS (git 2.55.0, system regex) every one of these matches nothing under -E and
# matches under the default BRE; on Debian (git 2.47.3, glibc) only `\d`/`\D` fail, under -E and BRE.
GREP_ESCAPES_DARWIN_ERE = set("bB<>sSwWdD")
GREP_ESCAPES_ANY = set("dD")


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
    return _lex(cmd)["equals"]


def split_words(cmd):
    """Return each unquoted `$name` in `set -- $name` that zsh will NOT word-split, in order."""
    return _lex(cmd)["split"]


def _dequote(w):
    """The value of one shell word after quote removal (no expansion): `'\\b'` -> `\\b`."""
    out, i, n = [], 0, len(w)
    while i < n:
        c = w[i]
        if c == "\\":
            out.append(w[i + 1:i + 2])
            i += 2
        elif c == "'":
            j = w.find("'", i + 1)
            j = n if j < 0 else j
            out.append(w[i + 1:j])
            i = j + 1
        elif c == '"':
            i += 1
            while i < n and w[i] != '"':
                if w[i] == "\\" and i + 1 < n and w[i + 1] in '$`"\\\n':
                    out.append(w[i + 1])
                    i += 2
                else:
                    out.append(w[i])
                    i += 1
            i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _bash_vars(word):
    """`$PIPESTATUS` / `${BASH_REMATCH…}` references zsh would expand in this raw word: unquoted or
    inside double quotes, not escaped, not in single quotes (a `$( )` inside "" is lexed on its own)."""
    out, i, dq = [], 0, False
    while i < len(word):
        c = word[i]
        if c == "\\":
            i += 2
            continue
        if c == "'" and not dq:
            j = word.find("'", i + 1)
            i = len(word) if j < 0 else j + 1
            continue
        if c == '"':
            dq, i = not dq, i + 1
            continue
        if c == "$" and word.startswith("$(", i) and not word.startswith("$((", i):
            i = _skip_cmdsub(word, i + 2)
            continue
        if c == "$":
            m = BASH_VARS.match(word, i)
            # `${pipestatus[1]:-$PIPESTATUS}` names the bash form only as a fallback: exempt
            if m and not word.endswith((":-", ":="), 0, i):
                end = word.find("}", i) + 1 if m.group(0).startswith("${") else m.end()
                out.append(word[i:end or m.end()])
        i += 1
    return out


def _bad_escapes(pattern, ptype, darwin):
    """The backslash escapes in a `git grep` pattern that match nothing for this pattern type here."""
    bad, i = [], 0
    while i < len(pattern) - 1:
        if pattern[i] == "\\":
            e = pattern[i + 1]
            if (ptype == "E" and darwin and e in GREP_ESCAPES_DARWIN_ERE) or \
                    (ptype in "EG" and not darwin and e in GREP_ESCAPES_ANY):
                bad.append("\\" + e)
            i += 2
            continue
        i += 1
    return bad


def _git_grep(dw, darwin):
    """dw: the dequoted words of one simple command. Return [(pattern, [escapes])] for a `git grep`
    whose pattern carries an escape the regex type cannot match on this platform."""
    if not dw or dw[0] != "git":
        return []
    i = 1
    while i < len(dw) and dw[i].startswith("-"):
        i += 2 if dw[i] in {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env"} else 1
    if i >= len(dw) or dw[i] != "grep":
        return []
    ptype, pats, explicit, j = "G", [], False, i + 1
    types = {"--extended-regexp": "E", "--basic-regexp": "G", "--perl-regexp": "P", "--fixed-strings": "F"}
    long_value = {"--max-depth", "--threads", "--context", "--after-context", "--before-context",
                  "--max-count", "--file", "--regexp"}
    while j < len(dw):
        a = dw[j]
        if a == "--":
            break
        if a.startswith("--"):
            name, eq, val = a.partition("=")
            ptype = types.get(name, ptype)
            if name in long_value and not eq:
                val = dw[j + 1] if j + 1 < len(dw) else ""
                j += 1
            if name == "--regexp":
                pats.append(val)
                explicit = True
        elif a.startswith("-") and len(a) > 1:
            k = 1
            while k < len(a):
                ch = a[k]
                if ch in "EGPF":
                    ptype = ch
                elif ch in "ABCmef":
                    val = a[k + 1:]
                    if not val:
                        val = dw[j + 1] if j + 1 < len(dw) else ""
                        j += 1
                    if ch == "e":
                        pats.append(val)
                        explicit = True
                    break
                k += 1
        elif not explicit and not pats:
            pats.append(a)
        j += 1
    out = []
    for p in pats:
        bad = _bad_escapes(p, ptype, darwin)
        if bad:
            out.append((p, bad))
    return out


def _special_names(w):
    """The `path`/`status` a simple command assigns: `for path in`, `read … path`, `local path=`,
    `status=$?`. A zsh array edit of `path` itself (`path=(… $path)`) is the zsh idiom and exempt."""
    out, k = [], 0
    while k < len(w):
        m = ASSIGN.fullmatch(w[k])
        if not m:
            break
        if m.group(1) in SPECIAL_NAMES and not (m.group(2).startswith("(") and m.group(1) == "path"):
            out.append(w[k])
        k += 1
    if k >= len(w):
        return out
    head, rest = w[k], w[k + 1:]
    if head in {"for", "select"}:
        for x in rest:
            if x in {"in", "("} or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", x):
                break
            if x in SPECIAL_NAMES:
                out.append(f"{head} {x}")
    elif head == "read":
        skip = False
        for x in rest:
            if skip:
                skip = False
            elif x.startswith("-"):
                skip = x[-1] in READ_VALUE_OPTS
            elif x.split("?", 1)[0] in SPECIAL_NAMES:
                out.append(f"read {x}")
    elif head in DECLARE:
        for x in rest:
            name = x.split("=", 1)[0].rstrip("+")
            if name in SPECIAL_NAMES and not (name == "path" and x[len(name):].lstrip("+=").startswith("(")):
                out.append(f"{head} {x}")
    return out


def _analyze(words, st, hits):
    """Run the per-simple-command checks over one command's raw words."""
    while words and words[0] in RESERVED:
        words = words[1:]
    hits["split"].extend(_set_split(words, st["arrays"]))
    if not words:
        return
    dw = [_dequote(x) for x in words]
    hits["special"].extend(_special_names(words))
    k = 0
    assigns = []
    while k < len(words) and ASSIGN.fullmatch(words[k]):
        m = ASSIGN.fullmatch(words[k])
        assigns.append((m.group(1), m.group(2)))
        k += 1
    if k < len(words):
        head = dw[k]
        if head == "for" and "in" in dw[k:]:
            args = words[k + dw[k:].index("in") + 1:]
        elif head in {"echo", "print", "[", "test", "[[", "set", "export", "local", "typeset",
                      "declare", "readonly", "unset"}:
            args = []
        else:
            args = words[k + 1:]
        for x in args:
            m = SCALAR_REF.fullmatch(x)
            name = m and (m.group(1) or m.group(2))
            if name and name in st["spaced"] and name not in st["arrays"]:
                hits["argv"].append((head, x))
        for pat, bad in _git_grep(dw[k:], st["darwin"]):
            hits["gitgrep"].append((pat, bad))
    for name, val in assigns:
        q = val[:1]
        if q in "'\"" and len(val) > 1 and val.endswith(q) and " " in val and \
                not (q == '"' and ("$" in val or "`" in val)):
            st["spaced"].add(name)
        else:
            st["spaced"].discard(name)


def _set_split(words, arrays):
    """The scalar `$name` arguments of a `set -- …` simple command (leading reserved words skipped)."""
    while words and words[0] in RESERVED:
        words = words[1:]
    if words[:2] != ["set", "--"]:
        return []
    out = []
    for w in words[2:]:
        m = SCALAR_REF.fullmatch(w)
        if m and (m.group(1) or m.group(2)) not in arrays | {"argv"}:
            out.append(w)
    return out


CHECKS = ("equals", "split", "special", "argv", "bashvar", "gitgrep")


def _lex(cmd, darwin=None):
    """Lex one zsh command line; return {check: [hits]} for every check in CHECKS."""
    if darwin is None:
        darwin = sys.platform == "darwin"
    hits = {k: [] for k in CHECKS}
    found = hits["equals"]
    s, i = cmd, 0
    at_start, cond, heredocs = True, 0, []
    words = []
    st = {"arrays": set(ARRAY_ASSIGN.findall(cmd)), "spaced": set(), "darwin": darwin}
    rematch_on = re.search(r"setopt\s[^;\n]*bash_?rematch", cmd, re.IGNORECASE) is not None

    def sub(inner):
        h = _lex(inner, darwin)
        for k in CHECKS:
            hits[k].extend(h[k])

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
            _analyze(words, st, hits)
            words = []
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
            _analyze(words, st, hits)
            words = []
            continue
        if at_start:
            end, subs = i, []
            while end < len(s) and s[end] not in " \t" and s[end] not in OPERATORS:
                end = _skip_quoted(s, end + 1, s[end], subs) if s[end] in "'\"" else end + 1
            word = s[i:end]
            # `name=(…)`: the `(` is an operator to this lexer, so mark the assignment as an array one
            words.append(word + "(" if word.endswith("=") and s.startswith("(", end) else word)
            hits["bashvar"].extend(v for v in _bash_vars(word)
                                   if not (rematch_on and "BASH_REMATCH" in v))
            for inner in subs:
                sub(inner)
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
                sub(inner)
        elif c == "\\":
            i += 2
        else:
            i += 1
    _analyze(words, st, hits)
    return hits


def reason(words):
    shown = ", ".join(f"`{w}`" for w in words[:5])
    return (
        f"zsh EQUALS: unquoted {shown} begins with `=`. zsh rewrites `=cmd` to that command's path, "
        "and a word naming no command aborts the whole list right there: what ran before it "
        "prints, nothing after it runs. Quote it (`echo '==='`), separate with `echo ---`, and "
        "use `[[ a == b ]]` rather than `[ a == b ]`. Not run. "
        "(sota-shell-scripting rules/06 §1; this hook: scripts/zsh-equals-hook.py)"
    )


def split_reason(words):
    shown = ", ".join(f"`set -- {w}`" for w in words[:5])
    return (
        f"zsh word splitting: {shown} sets ONE positional parameter in zsh, which does not split an "
        "unquoted scalar the way bash does, so `$2` is empty (measured: `Bad port ''`). Split it "
        "explicitly: `set -- ${=p}` (zsh), or `read -r a b <<<\"$p\"` (both shells). If the name is "
        "an array, write `set -- \"${p[@]}\"`. Not run. "
        "(sota-shell-scripting rules/01 §3; this hook: scripts/zsh-equals-hook.py)"
    )


def special_reason(hits):
    shown = ", ".join(f"`{w}`" for w in hits[:5])
    return (
        f"zsh special parameter: {shown}. In zsh `path` is the array tied to $PATH, so assigning it "
        "empties the command search path and every later command fails `command not found`; "
        "`status` is read-only, so `status=$?` aborts the list. Rename it (`p`, `f`, `rc`). Not run. "
        "(sota-shell-scripting rules/06 §1, the `path`/`status` row; this hook: scripts/zsh-equals-hook.py)"
    )


def argv_reason(hits):
    shown = ", ".join(f"`{cmd} {w}`" for cmd, w in hits[:5])
    return (
        f"zsh word splitting: {shown} passes the variable as ONE argument in zsh, which does not "
        "split an unquoted scalar, and this command assigned it a value with a space. bash would "
        "split it; zsh hands the callee one word, which it rejects or silently misreads (measured: an option list reported back as one `unrecognized arguments:` string). "
        "Write `${=T}` (zsh), or use an array: `T=(a b); cmd \"${T[@]}\"`. Not run. "
        "(sota-shell-scripting rules/06 §1, the unquoted `$var` row; this hook: scripts/zsh-equals-hook.py)"
    )


def bashvar_reason(hits):
    shown = ", ".join(f"`{w}`" for w in hits[:5])
    return (
        f"bash-only variable in zsh: {shown}. zsh leaves `PIPESTATUS` unset (its form is "
        "`${pipestatus[1]}`, 1-based) and `BASH_REMATCH` unset unless `setopt BASH_REMATCH` "
        "(captures are in `${match[1]}`), so it prints empty, and two empties compare equal. Use the "
        "zsh form, or run the snippet under `bash -c '…'`. Not run. "
        "(sota-shell-scripting rules/06 §1, the pipeline-status and BASH_REMATCH rows; "
        "this hook: scripts/zsh-equals-hook.py)"
    )


def gitgrep_reason(hits):
    shown = ", ".join(f"`{p}` ({' '.join(sorted(set(b)))})" for p, b in hits[:5])
    return (
        f"git grep escape: {shown}. On macOS git uses the system regex, which under -E reads `\\b`, "
        "`\\<`, `\\s`, `\\w`, `\\d` as plain letters (measured git 2.55.0: `a\\b` matches `ab`), and "
        "`\\d` matches nothing under -E or the default BRE on glibc either. The result is a zero, or "
        "fewer lines, that reads as a clean answer. Write `[[:space:]]`, `[[:alnum:]_]`, "
        "`[[:digit:]]`, drop the boundary and filter afterwards, or use -P. Not run. "
        "(sota-shell-scripting rules/06 §2f; this hook: scripts/zsh-equals-hook.py)"
    )


REASONS = {"equals": reason, "split": split_reason, "special": special_reason, "argv": argv_reason,
           "bashvar": bashvar_reason, "gitgrep": gitgrep_reason}


def active():
    mode = os.environ.get("SOTA_ZSH_EQUALS_HOOK", "").lower()
    if mode in {"off", "0", "false", "no"}:
        return False
    if mode in {"on", "1", "true", "yes"}:
        return True
    return agent_shell() == "zsh"


def agent_shell():
    """The shell Claude Code runs Bash commands in, in its own order: a working bash/zsh path in
    CLAUDE_CODE_SHELL, else $SHELL when it is bash or zsh, else the first zsh then bash on PATH
    (the CLAUDE_CODE_SHELL entry in code.claude.com/docs/en/env-vars, and the binary's own strings:
    "is not a valid bash/zsh path, falling back to detection", 2.1.306). Reading $SHELL alone
    refused `echo ===` for a user whose login shell is zsh and whose agent runs bash."""
    for var in ("CLAUDE_CODE_SHELL", "SHELL"):
        path = os.environ.get(var, "")
        name = os.path.basename(path)
        if name in {"bash", "zsh"} and (var == "SHELL" or os.access(path, os.X_OK)):
            return name
    for name in ("zsh", "bash"):
        for d in os.environ.get("PATH", "").split(os.pathsep):
            if d and os.access(os.path.join(d, name), os.X_OK):
                return name
    return ""


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
        h = _lex(cmd)
        msg = [REASONS[k](h[k]) for k in CHECKS if h[k]]
        if msg:
            print("\n".join(msg), file=sys.stderr)
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


# (command, expected flagged `set --` words, $# in real zsh). Each command is run in zsh by the
# self-test and must print N=<that count>: 1 for a flagged scalar is the defect the hook names.
SPLIT_CASES = [
    ('p="a b"; set -- $p; echo N=$#', ["$p"], 1),
    ('p="a b"; set -- ${p}; echo N=$#', ["${p}"], 1),
    ('for x in "a b"; do set -- $x; echo N=$#; done', ["$x"], 1),
    ('p="a b"; if true; then set -- $p; fi; echo N=$#', ["$p"], 1),
    ('p="a b"; echo "$(set -- $p; echo N=$#)"', ["$p"], 1),
    ('p="a b"; set -- ${=p}; echo N=$#', [], 2),
    ('p="a b"; set -- ${(s: :)p}; echo N=$#', [], 2),
    ('p="a b"; set -- "$p"; echo N=$#', [], 1),
    ('a=(p q); set -- $a; echo N=$#', [], 2),
    ('set -- $(echo a b); echo N=$#', [], 2),
    ('set -- a b; set -- $@; echo N=$#', [], 2),
    ('set -- a b; set -- $argv; echo N=$#', [], 2),
    ("p='a b'; echo set -- $p; echo N=$#", [], 0),
    ('p="a b"\n# set -- $p\necho N=$#', [], 0),
]


# (check, command, expected hits, a stdout line real zsh must print; "!LINE" = must NOT print it).
# Every command is run in `zsh -f`: a flagged case shows the defect, an exempt one shows it works.
N = "n(){ echo N=$#; }; "
TRAP_CASES = [
    ("special", "for path in a b; do :; done; ls / >/dev/null && echo AFTER", ["for path"], "!AFTER"),
    ("special", 'read -r x path <<<"1 2"; ls / >/dev/null && echo AFTER', ["read path"], "!AFTER"),
    ("special", "f(){ local path=/x; ls / >/dev/null && echo AFTER; }; f", ["local path=/x"], "!AFTER"),
    ("special", "status=$?; echo AFTER", ["status=$?"], "!AFTER"),
    ("special", "for status in a; do :; done; echo AFTER", ["for status"], "!AFTER"),
    ("special", "path=(/usr/bin /bin $path); ls / >/dev/null && echo AFTER", [], "AFTER"),
    ("special", "p=x; for f in a; do :; done; read -r q <<<1; ls / >/dev/null && echo AFTER", [], "AFTER"),
    ("special", "echo $status $path >/dev/null; ls / >/dev/null && echo AFTER", [], "AFTER"),
    ("special", "cat <<'E' >/dev/null\nfor path in x\nE\nls / >/dev/null && echo AFTER", [], "AFTER"),
    ("special", "bash -c 'for path in a; do :; done; ls / >/dev/null' && echo AFTER", [], "AFTER"),
    ("argv", N + 'T="a b"; n $T', [("n", "$T")], "N=1"),
    ("argv", N + "T='-x -y'; n ${T}", [("n", "${T}")], "N=1"),
    ("argv", 'T="a b"; c=0; for x in $T; do c=$((c+1)); done; echo N=$c', [("for", "$T")], "N=1"),
    ("argv", N + 'T="a b"; n ${=T}', [], "N=2"),
    ("argv", N + 'T="a b"; n "$T"', [], "N=1"),
    ("argv", N + "T=(a b); n $T", [], "N=2"),
    ("argv", N + 'T="a b"; T=x; n $T', [], "N=1"),
    ("argv", 'T="a b"; echo $T', [], "a b"),
    ("bashvar", 'false | true; echo "p=${PIPESTATUS[0]}"', ["${PIPESTATUS[0]}"], "p="),
    ("bashvar", "false | true; echo p=$PIPESTATUS", ["$PIPESTATUS"], "p="),
    ("bashvar", '[[ ab =~ (a)(b) ]] && echo "m=${BASH_REMATCH[1]}"', ["${BASH_REMATCH[1]}"], "m="),
    ("bashvar", 'false | true; echo "p=${pipestatus[1]}"', [], "p=1"),
    ("bashvar", 'false | true; echo "p=${pipestatus[1]:-$PIPESTATUS}"', [], "p=1"),
    ("bashvar", "bash -c 'false | true; echo p=${PIPESTATUS[0]}'", [], "p=1"),
    ("bashvar", 'echo "p=\\${PIPESTATUS[0]}"', [], "p=${PIPESTATUS[0]}"),
    ("bashvar", "setopt bash_rematch; [[ ab =~ (a)(b) ]] && echo \"m=${BASH_REMATCH[2]}\"", [], "m=a"),
]

# (command, hits on macOS, hits elsewhere). Run in zsh inside a scratch repo whose one file holds
# `foo 53 bar`; each pattern matches it when its escapes work, so a hit on THIS platform must come
# back empty from real git and an exempt case must print `f.txt:1`.
GITGREP_CASES = [
    ("git grep -cE '\\bfoo'", [("\\bfoo", ["\\b"])], []),
    ("git grep -cE 'foo\\s53'", [("foo\\s53", ["\\s"])], []),
    ("git grep -cE '\\<foo'", [("\\<foo", ["\\<"])], []),
    ("git grep -c -e 'fo\\w' -E", [("fo\\w", ["\\w"])], []),
    ('git grep -cE "\\\\bfoo"', [("\\bfoo", ["\\b"])], []),
    ("git -C . grep -c -E '5\\d'", [("5\\d", ["\\d"])], [("5\\d", ["\\d"])]),
    ("git grep -c '5\\d'", [], [("5\\d", ["\\d"])]),
    ("git grep -c '\\bfoo'", [], []),
    ("git grep -cP '\\bfoo'", [], []),
    ("git grep -cE '[[:space:]]53'", [], []),
    ("echo git grep -cE '\\bfoo' >/dev/null; git grep -c foo", [], []),
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
    sfails = 0
    for cmd, want, _ in SPLIT_CASES:
        got = split_words(cmd)
        if got != want or equals_words(cmd):
            sfails += 1
            print(f"FAIL split lexer {cmd!r}: want {want} got {got}")
    fails += sfails
    print(f"split lexer: {len(SPLIT_CASES) - sfails}/{len(SPLIT_CASES)} cases")
    # each trap case flags only its own check, and no older case trips a newer check
    tfails, others = 0, [(c, None, "equals") for c, _, _ in CASES] + [(c, None, "split") for c, _, _ in SPLIT_CASES]
    for check, cmd, want, _ in TRAP_CASES:
        got = _lex(cmd)
        stray = [k for k in CHECKS if k != check and got[k]]
        if got[check] != want or stray:
            tfails += 1
            print(f"FAIL {check} lexer {cmd!r}: want {want} got {got[check]} stray {stray}")
    for cmd, mac, other in GITGREP_CASES:
        for darwin, want in ((True, mac), (False, other)):
            got = _lex(cmd, darwin)
            stray = [k for k in CHECKS if k != "gitgrep" and got[k]]
            if got["gitgrep"] != want or stray:
                tfails += 1
                print(f"FAIL gitgrep lexer (darwin={darwin}) {cmd!r}: want {want} got {got['gitgrep']} stray {stray}")
    for cmd, _, own in others:
        got = _lex(cmd)
        stray = [k for k in CHECKS if k != own and got[k]]
        if stray:
            tfails += 1
            print(f"FAIL {own} case trips {stray}: {cmd!r}")
    fails += tfails
    ntrap = len(TRAP_CASES) + 2 * len(GITGREP_CASES) + len(others)
    print(f"trap lexer: {ntrap - tfails}/{ntrap} cases (path/status, argv, bash vars, git grep, cross-talk)")

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
        bad = 0
        for cmd, _, n in SPLIT_CASES:
            r = subprocess.run([zsh, "-fc", cmd], check=False, capture_output=True, text=True, timeout=10,
                               cwd="/", stdin=subprocess.DEVNULL)
            if f"N={n}" not in r.stdout.split():
                bad += 1
                print(f"FAIL zsh disagrees on {cmd!r}: expected N={n}, got {r.stdout.strip()!r}")
        fails += bad
        print(f"zsh ({zsh}): {len(SPLIT_CASES) - bad}/{len(SPLIT_CASES)} split counts agree")
        bad = 0
        for check, cmd, _, line in TRAP_CASES:
            r = subprocess.run([zsh, "-fc", cmd], check=False, capture_output=True, text=True, timeout=10,
                               cwd="/", stdin=subprocess.DEVNULL)
            lines = r.stdout.splitlines()
            ok = (line[1:] not in lines) if line.startswith("!") else (line in lines)
            if not ok:
                bad += 1
                print(f"FAIL zsh disagrees on {check} {cmd!r}: expected line {line!r}, got {r.stdout.strip()[:60]!r}")
        fails += bad
        print(f"zsh ({zsh}): {len(TRAP_CASES) - bad}/{len(TRAP_CASES)} trap verdicts agree")
        git = shutil.which("git")
        if git is None:
            print("SKIP: git not found, so the git grep cases were not checked against real git")
        else:
            bad = 0
            darwin = sys.platform == "darwin"
            with tempfile.TemporaryDirectory() as d:
                for argv in (["init", "-q", d], ["-C", d, "add", "f.txt"]):
                    if argv[0] == "-C":
                        with open(os.path.join(d, "f.txt"), "w", encoding="utf-8") as f:
                            f.write("foo 53 bar\n")
                    subprocess.run([git, *argv], check=True, capture_output=True, timeout=30)
                for cmd, mac, other in GITGREP_CASES:
                    flagged = bool(mac if darwin else other)
                    r = subprocess.run([zsh, "-fc", cmd], check=False, capture_output=True, text=True,
                                       timeout=10, cwd=d, stdin=subprocess.DEVNULL)
                    matched = "f.txt:1" in r.stdout.split()
                    if matched == flagged:
                        bad += 1
                        print(f"FAIL git disagrees on {cmd!r}: hook flags={flagged}, git matched={matched} "
                              f"(stderr {r.stderr.strip()[:60]!r})")
            fails += bad
            print(f"git ({sys.platform}): {len(GITGREP_CASES) - bad}/{len(GITGREP_CASES)} git grep verdicts agree")

    # the hook end to end: event in, exit code and stderr out
    real_bash = shutil.which("bash") or "/bin/bash"
    def run(cmd, env_extra, tool="Bash"):
        env = {k: v for k, v in os.environ.items()
               if k not in {"SOTA_ZSH_EQUALS_HOOK", "CLAUDE_CODE_SHELL"}}
        env.update(env_extra)
        ev = json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool,
                         "tool_input": {"command": cmd}})
        r = subprocess.run([sys.executable, os.path.abspath(__file__)], input=ev,
                           check=False, capture_output=True, text=True, env=env, timeout=30)
        return r.returncode, r.stderr

    e2e = [
        ("deny under zsh", run("echo ===; ls", {"SHELL": "/bin/zsh"}), 2, "EQUALS"),
        ("allow clean under zsh", run("echo ---; ls", {"SHELL": "/bin/zsh"}), 0, ""),
        ("deny set -- $p under zsh", run('p="h 22"; set -- $p; ssh -p "$2" "$1"', {"SHELL": "/bin/zsh"}), 2, "word splitting"),
        ("allow set -- $p under bash", run('p="h 22"; set -- $p', {"SHELL": "/bin/bash"}), 0, ""),
        ("allow set -- ${=p} under zsh", run('p="h 22"; set -- ${=p}', {"SHELL": "/bin/zsh"}), 0, ""),
        ("allow under bash", run("echo ===; ls", {"SHELL": "/bin/bash"}), 0, ""),
        ("agent shell bash, login zsh", run("echo ===", {"SHELL": "/bin/zsh", "CLAUDE_CODE_SHELL": real_bash}), 0, ""),
        ("agent shell zsh, login bash", run("echo ===", {"SHELL": "/bin/bash", "CLAUDE_CODE_SHELL": zsh or real_bash}), 2 if zsh else 0, "EQUALS" if zsh else ""),
        ("invalid override falls back to $SHELL", run("echo ===", {"SHELL": "/bin/zsh", "CLAUDE_CODE_SHELL": "/nonexistent/bash"}), 2, "EQUALS"),
        ("forced on", run("echo ===", {"SHELL": "/bin/bash", "SOTA_ZSH_EQUALS_HOOK": "on"}), 2, "EQUALS"),
        ("opt-out", run("echo ===", {"SHELL": "/bin/zsh", "SOTA_ZSH_EQUALS_HOOK": "off"}), 0, ""),
        ("other tool", run("echo ===", {"SHELL": "/bin/zsh"}, tool="Read"), 0, ""),
        ("deny path under zsh", run("for path in a; do ls; done", {"SHELL": "/bin/zsh"}), 2, "special parameter"),
        ("deny joined argv under zsh", run('C="--a x"; cmd $C', {"SHELL": "/bin/zsh"}), 2, "ONE argument"),
        ("deny PIPESTATUS under zsh", run('a | b; echo "${PIPESTATUS[0]}"', {"SHELL": "/bin/zsh"}), 2, "bash-only"),
        ("deny git grep -E \\d under zsh", run("git grep -E 'x\\d'", {"SHELL": "/bin/zsh"}), 2, "rules/06 §2f"),
        ("allow PIPESTATUS under bash", run('a | b; echo "${PIPESTATUS[0]}"', {"SHELL": "/bin/bash"}), 0, ""),
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
        split = os.path.join(d, "split.sh")
        with open(split, "w", encoding="utf-8") as f:
            f.write('p="h 22"\nset -- $p\n')
        traps = {}
        for name, text in (("path", "for path in a b; do :; done\nls\n"), ("status", "status=$?\n"),
                           ("argv", 'C="--a x"\ncmd $C\n'), ("pipestatus", 'a | b\necho "${PIPESTATUS[0]}"\n'),
                           ("gitgrep", "git grep -nE 'a\\d'\n")):
            traps[name] = os.path.join(d, name + ".sh")
            with open(traps[name], "w", encoding="utf-8") as f:
                f.write(text)
        me = [sys.executable, os.path.abspath(__file__), "--check"]
        for name, argv, want in [("check hit", [bad], 1), ("check clean", [good], 0),
                                 ("check split hit", [split], 1),
                                 *[(f"check {k} hit", [v], 1) for k, v in traps.items()],
                                 ("check unreadable", [os.path.join(d, "nope")], 2),
                                 ("check no files", [], 2)]:
            r = subprocess.run(me + argv, check=False, capture_output=True, text=True, timeout=30)
            if r.returncode != want:
                fails += 1
                print(f"FAIL {name}: rc={r.returncode} (want {want}) {r.stdout.strip()[:80]!r}")
    print(f"end to end: {len(e2e) + 6 + len(traps)} checks")
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
        h = _lex(text)
        for w in h["equals"]:
            print(f"{path}: unquoted {w}")
        for w in h["split"]:
            print(f"{path}: set -- {w} (zsh does not word-split it)")
        for w in h["special"]:
            print(f"{path}: {w} (a zsh special parameter: path is $PATH, status is read-only)")
        for cmd, w in h["argv"]:
            print(f"{path}: {cmd} {w} (zsh passes one word)")
        for w in h["bashvar"]:
            print(f"{path}: {w} (unset in zsh)")
        for pat, bad in h["gitgrep"]:
            print(f"{path}: git grep '{pat}' ({' '.join(sorted(set(bad)))} not honoured here)")
        if any(h.values()):
            rc = 1
    print(f"checked {len(paths)} file(s), {total} bytes: {'HITS' if rc else 'clean'}")
    return rc


if __name__ == "__main__":
    if "--check" in sys.argv:
        sys.exit(check(sys.argv[sys.argv.index("--check") + 1:]))
    if "--self-test" in sys.argv:
        sys.exit(self_test("--require-zsh" in sys.argv))
    sys.exit(main())
