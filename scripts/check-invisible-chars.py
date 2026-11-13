#!/usr/bin/env python3
"""Reject invisible and bidirectional code points in tracked text files.

`sota-devsecops` rules/05 section 5.6 and `sota-code-security` rules/09 section 4 tell every
reader to gate these in source, docs and agent-generated code. This repository did not run that
gate on itself until a field report (2026-11-10) found an agent had written a literal
RIGHT-TO-LEFT OVERRIDE into a test fixture, twice in one session, with nothing to catch it.

Scope: every file `git ls-files` lists, minus binaries (a NUL in the first 8 KiB). A hit prints
`path:line:col U+XXXX` and never the character itself. Deliberate occurrences are allow-listed
by path below; an allow-listed file that no longer holds one fails too, so the list cannot go
stale silently. An empty scope fails closed.

    python3 scripts/check-invisible-chars.py              # the tracked tree
    python3 scripts/check-invisible-chars.py --self-test  # known-bads, near-misses, controls

This file is ASCII on purpose: code points are written as chr() numbers, never as escapes.
"""
import os
import subprocess
import sys
import tempfile

# Zero-width (U+200B-200D), bidi embeddings/overrides (U+202A-202E) and isolates
# (U+2066-2069), the BOM / zero-width no-break space (U+FEFF), and tag characters
# (U+E0000-E007F), the ranges rules/09 section 4 names.
RANGES = ((0x200B, 0x200D), (0x202A, 0x202E), (0x2066, 0x2069), (0xFEFF, 0xFEFF), (0xE0000, 0xE007F))

# Deliberate occurrences: path -> why. Each must still contain at least one hit.
ALLOW = {
    "scripts/probe-fixtures/sota-javascript-typescript/05-security/1e6140bbdd/bad/src/access.ts":
        "a known-bad fixture: a zero-width space inside a role comparison",
    "skills/sota-javascript-typescript/rules/02-language-idioms.md":
        "the str.length example counts a zero-width joiner sequence",
    "scripts/probe-fixtures/sota-code-security/09-untrusted-data-ingestion/d4a6ea96ee/bad/role.go":
        "a known-bad fixture: a zero-width space alone, the case an agent's ugrep wrapper missed",
}


def flagged(c):
    o = ord(c)
    return any(lo <= o <= hi for lo, hi in RANGES)


def scan_text(text):
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        for col, c in enumerate(line, 1):
            if flagged(c):
                hits.append((n, col, ord(c)))
    return hits


def tracked(root):
    out = subprocess.run(["git", "-C", root, "ls-files", "-z"], capture_output=True, check=True).stdout
    return [p for p in out.decode("utf-8", "surrogateescape").split("\0") if p]


def check(root, allow):
    files = tracked(root)
    scanned = 0
    bad = []
    seen_allowed = set()
    for rel in files:
        path = os.path.join(root, rel)
        if os.path.islink(path) or not os.path.isfile(path):
            continue  # a symlink's target is scanned as its own tracked path
        with open(path, "rb") as f:
            data = f.read()
        if b"\0" in data[:8192]:
            continue
        scanned += 1
        hits = scan_text(data.decode("utf-8", "replace"))
        if not hits:
            continue
        if rel in allow:
            seen_allowed.add(rel)
            continue
        bad.extend("%s:%d:%d U+%04X" % (rel, n, col, o) for n, col, o in hits)
    stale = sorted(set(allow) - seen_allowed)
    return scanned, bad, stale


def main(root, allow=ALLOW):
    scanned, bad, stale = check(root, allow)
    if scanned == 0:
        print("FAIL: 0 text files scanned; the scope is empty, so this check verified nothing")
        return 1
    for line in bad:
        print("FAIL: invisible or bidi code point: " + line)
    for rel in stale:
        print("FAIL: allow-listed but holds no flagged code point (or is gone): " + rel)
    if bad or stale:
        print("Write such characters as escapes built at run time (chr(0x202E), printf with octal),"
              " never literally; sota-devsecops rules/05 section 5.6.")
        return 1
    print("ok (%d tracked text files, %d allow-listed)" % (scanned, len(allow)))
    return 0


def self_test():
    results = []

    def expect(label, cond):
        results.append(cond)
        print(("  ok   " if cond else "  FAIL ") + label)

    def repo(files, binary=None):
        d = tempfile.mkdtemp()
        subprocess.run(["git", "init", "-q", d], check=True)
        for rel, text in files.items():
            os.makedirs(os.path.dirname(os.path.join(d, rel)) or d, exist_ok=True)
            with open(os.path.join(d, rel), "w", encoding="utf-8") as f:
                f.write(text)
        for rel, data in (binary or {}).items():
            with open(os.path.join(d, rel), "wb") as f:
                f.write(data)
        subprocess.run(["git", "-C", d, "add", "-A"], check=True)
        return d

    # Each range's endpoints are caught, in code and in prose.
    for lo, hi in RANGES:
        for cp in sorted({lo, hi}):
            d = repo({"a.sh": "x='ok'\ny='a" + chr(cp) + "b'\n"})
            n, bad, _ = check(d, {})
            expect("U+%04X caught" % cp, n == 1 and bad == ["a.sh:2:5 U+%04X" % cp])
    # The field case: a literal RLO beside an escaped \u0007 (written here without a backslash-u).
    d = repo({"t/test-x.sh": "p=\"pwned" + chr(92) + "u0007" + chr(0x202E) + "X\"\n"})
    n, bad, _ = check(d, {})
    expect("field case caught in a hyphenated test file", bad == ["t/test-x.sh:1:15 U+202E"])
    # Near-misses that must pass: the escape spelled out, neighbouring code points, ordinary Unicode.
    clean = {
        "esc.sh": "printf '" + chr(92) + "342" + chr(92) + "200" + chr(92) + "256'\n",
        "py.py": "RLO = chr(0x202E)\nZW = '" + chr(92) + "u200b'\n",
        "near.md": "".join(chr(c) for c in (0x200A, 0x200E, 0x2029, 0x2065, 0x206A, 0xFEFE, 0xFF01)) + "\n",
        "text.md": "caf" + chr(0xE9) + " " + chr(0x2014) + " " + chr(0x4E2D) + " " + chr(0x1F600) + "\n",
    }
    n, bad, _ = check(repo(clean), {})
    expect("escapes, neighbours and ordinary Unicode pass (4 files)", n == 4 and bad == [])
    # A binary file is skipped, not decoded into false hits.
    d = repo({"a.txt": "fine\n"}, binary={"img.bin": b"\0PNG" + chr(0x202E).encode("utf-8")})
    n, bad, _ = check(d, {})
    expect("binary skipped", n == 1 and bad == [])
    # The allow-list exempts a path, and a stale entry is reported.
    d = repo({"fx/bad.ts": "role === 'user" + chr(0x200B) + "'\n", "ok.md": "x\n"})
    n, bad, stale = check(d, {"fx/bad.ts": "fixture"})
    expect("allow-listed path exempt", bad == [] and stale == [])
    n, bad, stale = check(d, {"fx/bad.ts": "fixture", "gone.md": "removed"})
    expect("stale allow-list entry reported", stale == ["gone.md"])
    d = repo({"fx/bad.ts": "clean now\n"})
    n, bad, stale = check(d, {"fx/bad.ts": "fixture"})
    expect("allow-listed file that lost its character reported", stale == ["fx/bad.ts"])
    # An empty scope fails closed through main().
    d = tempfile.mkdtemp()
    subprocess.run(["git", "init", "-q", d], check=True)
    # an empty allow-list, so the exit can only come from the empty scope, not a stale entry
    expect("empty scope fails closed (main() exits 1)", main(d, {}) == 1)
    passed = sum(results)
    print("%s: %d/%d" % ("PASS" if all(results) else "FAIL", passed, len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        sys.exit(self_test())
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()
    sys.exit(main(top))
