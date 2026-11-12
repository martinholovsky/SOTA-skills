#!/usr/bin/env python3
"""check-checklist-probes.py — run every `grep` probe in the skills' audit checklists and fail on
one that cannot run. A probe that exits 2 never searched anything, and most checklist probes end
in `2>/dev/null`, so a broken one prints nothing and reads as a clean codebase
(sota-shell-scripting rules/06 §2d: "a checklist line is a control").

WHY. Nothing ran these. check-claims.sh re-runs measured claims about tool behaviour, by design;
invariants 2, 22 and 37 check where a checklist sits and the shape of its `--include`, never
whether the command parses. The class recurs: an earlier pass found four probes that never ran
(PCRE `(?!…)` under `grep -E`), and on 2026-10-21 two more had been dead since 2026-09-23 — a
doubled backslash (`\\[`, `\\(`) inside a code span, which reaches grep as a literal backslash
plus an unbalanced bracket. They exited 2 on BSD grep, ugrep and GNU grep alike (ADOPTION-LOG
2026-10-21, the field report on this session).

WHAT IT DOES. Every code span after `## Audit checklist` in skills/*/rules/*.md that starts with
`grep ` is a probe. Each runs under bash in an empty temporary directory, with `<file>`-style
placeholders replaced by an empty file and `2>/dev/null` removed so the error is visible:
  rc 0 or 1                                  -> ran (a match, or none)
  rc 2 and stderr names a missing path       -> ran far enough to look for its target
  anything else                              -> BROKEN, printed with the file and the error
  rc 123 from `xargs` with no error but a missing path -> ran (see run_probe)
WHAT IT SKIPS, counted and printed (skip rather than guess):
  - a span whose last word is a flag, or that has no pattern argument (`grep -r`, prose)
  - a placeholder with a space in it (`<runner provisioning: Dockerfiles>`), which is prose
  - a pipeline stage that is not a read-only filter (see SAFE); the probes are documentation,
    and a documentation line is not executed unless it can only read
WHAT IT CANNOT CATCH: a probe that runs and answers the wrong question (an unquoted `src/**/`
that searches one level in bash, a regex that misses a case). Only a known-bad fixture per
probe catches those.

Run on the two OS runners of the executable-claims job: BSD grep and GNU grep reject different
regexes. Exit 0 = every probe ran; 1 = a broken probe; 2 = the scan itself failed (no files, no
probes). Self-test: python3 scripts/check-checklist-probes.py --self-test
"""
import os
import re
import shlex
import subprocess
import sys
import tempfile

SPAN = re.compile(r"(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.S)
PLACEHOLDER = re.compile(r"<[A-Za-z][\w.-]*>")
PROSE_PLACEHOLDER = re.compile(r"<[^<>]*\s[^<>]*>")
DEVNULL_ERR = re.compile(r"\s*2>\s*/dev/null")
LINE_BREAK = re.compile(r"[ \t]*\n[ \t]*")
MISSING = re.compile(r"No such file or directory|cannot open|can't open")
# each pipeline stage must start with one of these (read-only filters); `xargs` only before one
SAFE = {"grep", "egrep", "fgrep", "sort", "uniq", "wc", "head", "tail", "cut", "awk", "tr", "cat",
        "echo", "printf", "find"}
UNSAFE_TOKEN = re.compile(r"\brm\b|\bsed\s+-i|\s-delete\b|\s-exec\b|\s-fprint|\s-fls\b|\bmv\b|\bcurl\b|\bwget\b")


def _unquoted(span):
    """For each character of span, whether it sits outside quotes (and is not backslash-escaped)."""
    out, q, esc = [], None, False
    for ch in span:
        out.append(q is None and not esc)
        if esc:
            esc = False
        elif ch == "\\" and q != "'":
            esc = True
        elif q is None and ch in "'\"":
            q = ch
        elif q == ch:
            q = None
    return out


def prose_placeholder(span):
    """An UNQUOTED `<words with spaces>` operand: prose standing in for a path, so not runnable.
    A quoted one is pattern text: `static_cast<[a-z0-9_ ]+>`, `Record<string, *[^>]+>` and `<%==`
    inside a quoted regex were matched here and six real probes were skipped."""
    uq = _unquoted(span)
    return any(uq[m.start()] for m in PROSE_PLACEHOLDER.finditer(span))


def fill_placeholders(span):
    """Replace each UNQUOTED `<name>` (a file-operand placeholder) with `empty`. A quoted one is
    pattern text: `'<NoWarn>'`, `'List<Integer>'` and `"<all_urls>"` are what the probe searches
    for, and rewriting them made seven JVM and several .NET probes search for `empty` instead."""
    uq = _unquoted(span)
    return PLACEHOLDER.sub(lambda m: "empty" if uq[m.start()] else m.group(), span)


def probes_in(text):
    i = text.find("\n## Audit checklist")
    if i < 0:
        return []
    out = []
    for m in SPAN.finditer(text[i:]):
        # join a span that Markdown wrapped, but keep spaces inside a line: collapsing every run turned
        # the ruby probe `'^    json \('` (four spaces, a Gemfile.lock dependency) into `'^ json \('`
        span = LINE_BREAK.sub(" ", m.group(2)).strip()
        if span.startswith("grep "):
            out.append(span)
    return out


def _tokens(cmd):
    """Shell words and operators, quote-aware: `'a|b'` is one word, a bare `|` is a pipe."""
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    return list(lex)


def skip_reason(span):
    if prose_placeholder(span):
        return "prose placeholder"
    cmd = fill_placeholders(span)
    if UNSAFE_TOKEN.search(cmd):
        return "not read-only"
    try:
        toks = _tokens(cmd)
    except ValueError:
        return None  # unbalanced quotes: bash will report it, and that is a finding, not a skip
    if toks[-1].startswith("-"):
        return "ends in a flag"
    segments, cur = [], []
    for t in toks:
        if t in {"|", "||", "&&", ";", "&", "|&"}:
            segments.append(cur)
            cur = []
        else:
            cur.append(t)
    segments.append(cur)
    if not [w for w in segments[0][1:] if not w.startswith("-") and w not in {"<", ">", "2"}]:
        return "no pattern argument"
    for seg in segments:
        for i, t in enumerate(seg):
            if t in {">", ">>", "&>", ">|"} and (i + 1 >= len(seg) or seg[i + 1] != "/dev/null"):
                return "writes a file"
        if not seg:
            continue
        name = seg[0]
        if name == "xargs":
            name = next((w for w in seg[1:] if not w.startswith("-")), "")
        if name not in SAFE:
            return f"stage `{name}` not on the read-only list"
    return None


def run_probe(span, workdir, env):
    cmd = DEVNULL_ERR.sub("", fill_placeholders(span))
    r = subprocess.run(["bash", "-c", cmd], cwd=workdir, env=env, capture_output=True, text=True,
                       timeout=20, stdin=subprocess.DEVNULL, check=False)
    if r.returncode in (0, 1):
        return "ran", ""
    err = r.stderr.strip()
    if r.returncode == 2 and MISSING.search(err):
        return "missing path", ""
    # `xargs` exits 123 when an invocation exits 1-125, so 1 (no match) and 2 (an error) look the
    # same; grep prints to stderr on 2, and 2>/dev/null is stripped, so stderr decides. GNU xargs
    # runs the command once on empty input where BSD xargs does not, so this arm is GNU's.
    if r.returncode == 123 and all(MISSING.search(l) for l in err.splitlines()):
        return ("missing path", "") if err else ("ran", "")
    return "BROKEN", f"rc={r.returncode} {(err.splitlines() or [''])[-1][:160]}"


def scan(files):
    counts = {"ran": 0, "missing path": 0, "skipped": 0, "BROKEN": 0}
    broken, skipped = [], {}
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "empty"), "w").close()
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": d, "LC_ALL": "C"}
        for f in files:
            with open(f, encoding="utf-8") as fh:
                spans = probes_in(fh.read())
            for span in spans:
                why = skip_reason(span)
                if why:
                    counts["skipped"] += 1
                    skipped[why] = skipped.get(why, 0) + 1
                    continue
                verdict, detail = run_probe(span, d, env)
                counts[verdict] += 1
                if verdict == "BROKEN":
                    broken.append((f, span, detail))
    return counts, broken, skipped


def main(argv):
    if argv:
        files = argv
    else:
        r = subprocess.run(["git", "ls-files", "skills/*/rules/*.md"], capture_output=True,
                           text=True, check=False)
        files = r.stdout.split()
    if not files:
        print("FAIL: no rules files found (an empty scope verifies nothing)")
        return 2
    counts, broken, skipped = scan(files)
    total = counts["ran"] + counts["missing path"] + counts["BROKEN"]
    grep_v = subprocess.run(["bash", "-c", "grep --version 2>&1 | head -1"], capture_output=True,
                            text=True, check=False).stdout.strip()
    print(f"grep: {grep_v}")
    print(f"{len(files)} rules files · {total} probes run · {counts['ran']} ran · "
          f"{counts['missing path']} looked for a missing path · {counts['skipped']} skipped "
          f"({', '.join(f'{k}: {v}' for k, v in sorted(skipped.items()))}) · {counts['BROKEN']} BROKEN")
    if total == 0:
        print("FAIL: no probe ran (an empty scope verifies nothing)")
        return 2
    for f, span, detail in broken:
        print(f"BROKEN {f}: {span[:140]}\n       {detail}")
    if broken:
        print("A probe that exits 2 never searched anything; under 2>/dev/null it reads as clean. "
              "Inside a code span a backslash is literal: write \\[ not \\\\[. A probe containing a "
              "backtick needs a ``double-backtick`` span.")
        return 1
    print("ok")
    return 0


def self_test():
    good = ("x\n## Audit checklist\n- [ ] `grep -rnE 'a|b' src/` ok\n"
            "- [ ] `grep -nE 'x' <file>` placeholder\n"
            "- [ ] ``grep -rn 'a`b' src/`` a backtick inside a double span\n"
            "- [ ] `grep -r` a flag mention\n"
            "- [ ] `grep -rl x . | xargs grep -L y` xargs: BSD skips, GNU runs once and exits 123\n"
            "- [ ] `grep -rl x . | xargs rm` not read-only\n")
    bad = "x\n## Audit checklist\n- [ ] `grep -rnE 'export (\\\\[|\\\\{)' src/` doubled backslash\n"
    fails = 0
    with tempfile.TemporaryDirectory() as d:
        g, b = os.path.join(d, "good.md"), os.path.join(d, "bad.md")
        with open(g, "w", encoding="utf-8") as fh:
            fh.write(good)
        with open(b, "w", encoding="utf-8") as fh:
            fh.write(bad)
        c, br, sk = scan([g])
        if br or c["ran"] + c["missing path"] != 4 or c["skipped"] != 2:
            fails += 1
            print(f"FAIL good fixture: counts={c} broken={br} skipped={sk}")
        c, br, _ = scan([b])
        if c["BROKEN"] != 1:
            fails += 1
            print(f"FAIL bad fixture not caught: counts={c}")
        if main([b]) != 1:
            fails += 1
            print("FAIL main() did not exit 1 on the bad fixture")
        empty = os.path.join(d, "none.md")
        with open(empty, "w", encoding="utf-8") as fh:
            fh.write("no checklist here\n")
        if main([empty]) != 2:
            fails += 1
            print("FAIL main() did not fail closed on a scope with no probes")
    print("self-test:", "ok" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    sys.exit(main(sys.argv[1:]))
