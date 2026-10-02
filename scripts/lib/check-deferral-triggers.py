#!/usr/bin/env python3
"""Invariant 39: a branch that edits a file an ADOPTION-LOG deferral is waiting on must
touch that deferral's row.

THE INCIDENT. A deferral whose trigger is "the next rules/NN edit" fires silently: nothing
tells the editor the item exists. #481 and #482 each edited such files without doing the
deferred item, and the second was only noticed at the next session's close. Check 27 asserts
every deferral NAMES a trigger; nothing noticed when one FIRED.

WHAT COUNTS AS WAITING ON A FILE. Only deferrals whose trigger is an EDIT ("the next rules/03
edit", "rules/19 is next edited", "the next table-format maintenance edit"). The file is
resolved from the row itself: the first `sota-*` skill named, and every rules/NN attached to
it -- in the subject ("in `sota-copywriting` rules/04 §5") or in the trigger ("the next
rules/02, 05 or 06 edit"). Reading the subject is what covers topic-only triggers such as
"the next email-law edit", which name no path at all. Triggers on dates, drafts, field
reports or sweeps are out of scope: no diff can fire them.

WHAT SATISFIES IT. The row's current line appears among the ledger lines this branch added:
either the item was done (the row flips to RESOLVED and stops being a marker), or the row was
annotated ("trigger fired <date>: ..., still due"). A deferral added in the same branch is
added lines too, so it is acknowledged by construction.

WHAT IT CANNOT SEE, stated so the gap is not mistaken for coverage: an edit-trigger that
names no skill or no rules file ("the next DMARC/email-authentication edit" on a skill-level
row) is reported as UNRESOLVED and not enforced -- skip rather than guess.

Built corpus-first (the lesson of check 38's detector): --self-test runs a labelled set of
real ledger rows before the tree is judged, and a detector regression fails the check.

Usage:
  check-deferral-triggers.py --self-test
  check-deferral-triggers.py --list LEDGER            # path<TAB>ledger-line, one per resolved file
  check-deferral-triggers.py LEDGER BASE [HEAD]       # judge BASE...HEAD (HEAD: replay a past commit)
"""
import re
import subprocess
import sys

# Same marker regex as check 27, deliberately: the two checks must agree on what a deferral is.
MARKER = re.compile(r'(?:^|\|)\s*(?:-\s+)?\*\*DEFERRED\s+—')
SKILL = re.compile(r'`(sota(?:-[a-z]+)+|sota)`')
RULES = re.compile(r'rules/(\d{2})((?:\s*(?:,|or|and)\s*\d{2}\b)*)')
# "next ... edit" within one clause, or "is next edited". Dots are allowed inside the gap
# ("the next §3.7 edit" was missed by a first draft that excluded them); ";" ends a clause.
EDIT = re.compile(r'\bnext\b[^;]{0,80}?\bedit(?:ed)?\b', re.I)
TRIGGER_START = re.compile(r'revisit|trigger', re.I)


def marker_cell(line):
    return next((c for c in (line.split('|') if '|' in line else [line]) if 'DEFERRED' in c), line)


def split_row(cell):
    """(subject, trigger): the trigger starts at the first 'revisit'/'trigger' word."""
    m = TRIGGER_START.search(cell)
    if not m:
        return cell, ''
    trig = cell[m.start():]
    end = trig.find('**')                     # the bold marker closes the trigger clause
    return cell[:m.start()], (trig[:end] if end != -1 else trig)


def rules_numbers(text):
    out = []
    for m in RULES.finditer(text):
        out.append(m.group(1))
        out.extend(re.findall(r'\d{2}', m.group(2)))
    return out


def resolve(cell):
    """None if the trigger is not an edit; else (skill or None, sorted rules numbers)."""
    subject, trig = split_row(cell)
    if not EDIT.search(trig):
        return None
    nums = []
    sm = SKILL.search(subject)
    if sm:
        # only the subject segment attached to THIS skill, up to the next skill named: a row
        # citing other skills as the contrary source must not guard their files
        nxt = SKILL.search(subject, sm.end())
        nums += rules_numbers(subject[sm.end():nxt.start() if nxt else len(subject)])
    else:
        sm = SKILL.search(trig)
        if not sm:
            return (None, [])
    skill = sm.group(1)
    nums += rules_numbers(trig)
    return (skill, sorted(set(nums)))


# Labelled corpus: real rows from docs/ADOPTION-LOG.md (2026-09-30), trimmed to the part the
# detector reads. Expected value: None (not an edit trigger) or (skill, [rules numbers]).
CORPUS = [
    ("- **DEFERRED — Iceberg `rewrite_position_delete_files` / `rewrite_manifests` in "
     "`sota-data-engineering` rules/05's maintenance example; revisit trigger: the next "
     "table-format maintenance edit.**", ("sota-data-engineering", ["05"])),
    ("- **DEFERRED — invoker commands, `dialog closedby` and `contrast-color()` in "
     "`sota-frontend-design`; revisit trigger: the next rules/02, 05 or 06 edit, or the "
     "Interop 2026 results.**", ("sota-frontend-design", ["02", "05", "06"])),
    ("- **DEFERRED — `sota-performance` rules/01 says to always enable `net/http/pprof`, "
     "against `sota-observability` rules/05 and `sota-golang` rules/04; revisit trigger: the "
     "operator approves the one-line fix, or the next rules/01 edit.**", ("sota-performance", ["01"])),
    ("- **DEFERRED — the CAN-SPAM rule, in `sota-copywriting` rules/04 §5; revisit trigger: "
     "the next email-law edit.**", ("sota-copywriting", ["04"])),
    ("- **DEFERRED — lead-list probes for `sota-architecture` AUDIT step 3; revisit trigger: "
     "the next rules/07 edit, or a field report of a missed dual-write.**", ("sota-architecture", ["07"])),
    ("- **DEFERRED — native package-manager cooldowns in `sota-devsecops` rules/03; revisit "
     "trigger: the next §3.7 edit, or Renovate docs pointing at them.**", ("sota-devsecops", ["03"])),
    ("- **DEFERRED — verifying good bots by forward-confirmed rDNS; revisit trigger: "
     "draft-ietf-webbotauth reaches WG last call, or rules/19 is next edited.**", (None, [])),
    ("- **DEFERRED — DMARC `np=` and `t=` tags in `sota-network-security`; revisit trigger: "
     "the next DMARC/email-authentication edit.**", ("sota-network-security", [])),
    ("| 1b — router step 2 | **DEFERRED — revisit on a second independent session that "
     "invoked the router and opened no domain `SKILL.md`** | — |", None),
    ("- **DEFERRED — revisit trigger: the next time the competitor benchmark is re-run for "
     "any", None),
    ("- **DEFERRED — OWASP Top 10:2025 A10 is unmapped in `sota-code-security` rules/01, 07, "
     "09; revisit trigger: the next OWASP mapping pass, or the first audit finding that needs "
     "A10.**", None),
    ("- **DEFERRED — \"keep DOMPurify patched; avoid IN_PLACE mode\" in "
     "`sota-javascript-typescript` rules/09; revisit trigger: that skill's next sweep batch.**",
     None),
    ("- **DEFERRED — CAA `accounturi` in `sota-network-security`; revisit trigger: before the "
     "CA/Browser Forum Baseline Requirements date of 2027-03-15.**", None),
]


def self_test():
    bad = 0
    for row, want in CORPUS:
        got = resolve(marker_cell(row))
        if got != want:
            bad += 1
            print("SELF-TEST MISS: %r -> %r, expected %r" % (row[:70], got, want))
    print("SELF-TEST %d/%d" % (len(CORPUS) - bad, len(CORPUS)))
    return bad == 0


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True, check=True).stdout


def rules_files():
    return [p for p in git("ls-files", "skills/*/rules/*.md").split("\n") if p]


def mapping(ledger_lines):
    """[(lineno, line, [paths])] for resolved edit deferrals, plus unresolved [(lineno, why)]."""
    files = rules_files()
    resolved, unresolved = [], []
    for i, line in enumerate(ledger_lines, 1):
        if not MARKER.search(line):
            continue
        r = resolve(marker_cell(line))
        if r is None:
            continue
        skill, nums = r
        paths = []
        for n in nums:
            hit = [p for p in files if p.startswith("skills/%s/rules/%s-" % (skill, n))]
            if len(hit) == 1:
                paths.append(hit[0])
        if not paths:
            why = "names no skill" if skill is None else \
                  ("`%s` but no rules file" % skill if not nums else
                   "`%s` rules/%s matches no single file" % (skill, ",".join(nums)))
            unresolved.append((i, why))
        else:
            resolved.append((i, line, paths))
    return resolved, unresolved


def main(argv):
    if argv[1:] == ["--self-test"]:
        return 0 if self_test() else 1
    if len(argv) == 3 and argv[1] == "--list":
        lines = open(argv[2], encoding="utf-8").read().split("\n")
        for i, _, paths in mapping(lines)[0]:
            for p in paths:
                print("%s\t%d" % (p, i))
        return 0
    if len(argv) not in (3, 4):
        print(__doc__.split("Usage:")[1])
        return 2
    ledger, base = argv[1], argv[2]
    head = argv[3] if len(argv) == 4 else "HEAD"
    if head == "HEAD":
        lines = open(ledger, encoding="utf-8").read().split("\n")
    else:                                      # replaying a past commit: its own ledger
        lines = git("show", "%s:%s" % (head, ledger)).split("\n")
    resolved, unresolved = mapping(lines)
    # Read the diff from the SAME state the ledger was read from. For HEAD that is the
    # working tree against the merge base (`git diff <base>`), which includes staged and
    # unstaged edits: reading the ledger from the work tree but the diff from base...HEAD
    # blocked a commit whose staged ledger row acknowledged the very file it edited
    # (found 2026-10-02 by this check's first real use). In CI the tree is clean, so both
    # forms agree. A replayed past commit keeps base...<commit>.
    rng = [base] if head == "HEAD" else ["%s...%s" % (base, head)]
    changed = set(p for p in git("diff", "--name-only", *rng).split("\n") if p)
    added = set(l[1:] for l in git("diff", "--unified=0", *rng, "--", ledger).split("\n")
                if l.startswith("+") and not l.startswith("+++"))
    fired = acked = 0
    bad = []
    for i, line, paths in resolved:
        hit = [p for p in paths if p in changed]
        if not hit:
            continue
        fired += 1
        if line in added:
            acked += 1
        else:
            subject = split_row(marker_cell(line))[0]
            subject = re.sub(r'^\s*-?\s*\*\*DEFERRED\s+—\s*', '', subject).strip().rstrip(';')
            bad.append("%s is edited, and the deferral at %s:%d waits on it (%s) -- do the item "
                       "and flip the row to RESOLVED, or annotate the row: 'trigger fired <date>: "
                       "<PR> edited <file>, still due'" % (", ".join(hit), ledger, i, subject[:80]))
    for i, why in unresolved:
        print("UNRESOLVED %s:%d edit trigger %s -- not enforced" % (ledger, i, why))
    print("SCOPE %d" % len(resolved))
    for b in bad:
        print(b)
    if bad:
        return 1
    print("    ok (%d edit-triggered deferral(s) resolved to a file, %d unresolved; this branch "
          "fired %d, %d acknowledged in the ledger)" % (len(resolved), len(unresolved), fired, acked))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
