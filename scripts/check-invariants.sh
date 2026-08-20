#!/usr/bin/env bash
#
# Enforce SOTA-skills repository invariants. Run by pre-commit and CI.
# Exits non-zero (and prints offenders) if any invariant is violated.
#
# Invariants:
#   1. Every tracked SKILL file (skills/*/*.md, skills/*/rules/*.md) is <= 500
#      lines, so skills load incrementally. ONLY INSTRUCTION FILES ARE CAPPED:
#      a file is capped iff an agent loads it as instructions. Everything else
#      (README, CHANGELOG, docs/, evals/, scripts) is deliberately uncapped.
#   2. Every skills/*/rules/*.md ends with an "## Audit checklist".
#   3. No internal/private references leak in (the library stays generic).
#   4. Every skills/*/SKILL.md description is <= 1024 characters (Agent Skills
#      spec: loaders skip a skill whose description exceeds the cap) and is
#      not YAML-invalid (unquoted ': ' inline — strict loaders reject it).
#   5. Version lockstep: VERSION == plugin.json "version"; CHANGELOG's top
#      entry is [Unreleased] or [VERSION]; the newest v* tag is never ahead
#      of VERSION (VERSION may lead during a release PR).
#   6. Count-bearing surfaces match the tree: README badge/hero/social-alt,
#      the router's "N domain skills", plugin.json + marketplace.json
#      descriptions, and the social-preview pill.
#   7. Router completeness: every skill appears in the router's routing table
#      AND its library map (skills/sota/SKILL.md), and every map entry names a
#      real skill (catches the map-drift the 2026-07-10 audit found).
#   8. Internal links resolve: every relative Markdown link to a *.md target
#      (in any tracked *.md) points at a file that exists — catches doc/README/
#      INDEX/CHANGELOG link rot when a file is moved or renamed. Scope is *.md
#      targets only: non-.md relative links overlap prose/code fragments that
#      match the [text](x) shape (e.g. type annotations) and false-positive.
#      (Idea adopted from the training-knowledge-vault vault-doctor, 2026-07-24;
#      see docs/ADOPTION-LOG.md.)
#   9. CHANGELOG has at most one "## [Unreleased]" heading, it is the topmost
#      entry, and the archives have none. Check 5 only compares the TOP entry
#      to VERSION, so a second [Unreleased] lower down passed CI silently — on
#      2026-07-28 two feature PRs each added one above [1.19.3] and main
#      carried both until the release cut noticed by hand.
#  10. Every skills/*/rules/*.md is referenced by its own SKILL.md. The model
#      reads only the rules files the SKILL.md index points at, so an unindexed
#      rules file is never loaded — written, capped, checklist-ed, unreachable.
#      Skill-level twin of check 7 (a skill missing from the router).
#  11. LAST-VERIFIED only moves alongside a sweep. The stamp records the last
#      FULL re-verification pass, not the newest verified fact, so bumping it on
#      an ordinary edit asserts a sweep that never happened. Escapes: a
#      sweep-shaped diff (>= 20 skill files; the real 2026-07-08 sweep touched
#      100), or naming LAST-VERIFIED in the CHANGELOG, which is how a rolling
#      pass declares completion. DIFF-based — skips with a note if there is no
#      merge base, like checks 4 and 8 skip without python3.
#  12. Every assets/*.png is no older than the assets/*.html it renders. The PNGs
#      are committed build outputs and nothing regenerates them, so an un-rendered
#      HTML fix is invisible: the README embeds the image, never the source. PR
#      #173 fixed a stale line-cap claim in how-it-works.html and left the PNG at
#      its 2026-07-09 render, so main served the old claim all day while the diff
#      read as done. HISTORY-based (commit times, not mtimes — a fresh clone
#      stamps every file identically); escape is "[no-render]" in the HTML's own
#      commit subject.
#  13. Every scoreboard row in evals/results/RESULTS.md declares its sample size.
#      A lift from one run is typographically identical to a lift from ten, and
#      this repo has been burned twice: a +0.07 retracted when the set grew 15 ->
#      49, and a +0.40 corrected to +0.39 by a second run. A REGRESSION GUARD like
#      check 10 — all 10 rows pass today. Shape-driven (finds the table by its
#      "Samples" header), so a renamed or dropped column fails closed instead of
#      passing over zero rows.
#  14. A release declares its front-door terms, and they resolve. Invariant 6 fails
#      on a wrong NUMBER in the README; nothing failed on a CAPABILITY that never
#      got a sentence anywhere a reader looks -- five shipped across v1.17.0-v1.19.7
#      with zero README hits. Discovery ("what counts as a capability") is judgement
#      and cannot be gated; DECLARATION can, so a release must carry
#      "**Front door checked:** a · b" in its CHANGELOG section, and every term must
#      resolve in README.md or docs/INDEX.md AND appear in that release's own entry.
#      DIFF-based, release commits only — silent on an ordinary PR.
#  15. The router's library map lists every rules FILE, both directions. Check 7
#      proves each SKILL appears in the map; check 10 proves each rules file is
#      indexed by its OWN SKILL.md. Neither looks at the map's CONTENTS, so
#      sota-code-security/rules/11 sat unlisted in skills/sota/SKILL.md for two
#      releases (v1.19.8 → v1.21.0) with every check green. Compares the NN numbers
#      the map enumerates per skill against skills/<skill>/rules/NN-*.md, and
#      reports BOTH a file missing from the map and a map entry naming a file that
#      does not exist. Needs python3 (map entries wrap across lines); skipped with
#      a note if absent, like checks 4 and 8.
#  16. The hook README documents == the hook install.sh writes. install.sh WRITES
#      the UserPromptSubmit hook and README DOCUMENTS it; nothing kept them equal.
#      On 2026-08-05 three texts existed at once — the README block (two revisions
#      behind), HOOK_CMD, and what was in a real settings.json — and the README's
#      is the one a reader copies by hand, so the stale one is the one that
#      spreads. Parses the fenced JSON rather than regexing the string, so
#      reformatting the block is not a false positive. Needs python3; skipped with
#      a note if absent, like checks 4, 8 and 15.
#
# ADDING A CHECK? Three things this file learned the hard way — all from real
# incidents recorded in the checks below:
#   - WATCH IT FAIL FIRST. Break the input deliberately, confirm the abort, restore.
#     Invariant 9's first cut printed its heading and nothing else: a `grep -m 1` on
#     a PIPE SIGPIPE'd the upstream printf, and `pipefail` + `set -e` killed the
#     script mid-check. It looked like it passed. Never `grep -m 1`/`head` on a pipe
#     in here.
#   - PRINT YOUR DENOMINATOR, and fail on an empty scope — use scope(). Checks 2 and
#     10 printed "ok" over ZERO files until 2026-07-30, and check 6's tree recount
#     did not catch it.
#   - SKIP, DON'T GUESS. If a prerequisite is missing (python3, a merge base), say so
#     and skip. A check that assumes it passed is worse than one that isn't there.
#
# Portable to macOS bash 3.2 (no mapfile/associative arrays). Checks 4 and 8 need
# python3 (Unicode char counting; link parsing); they are skipped with a warning
# if python3 is absent locally (CI runs on a runner that always has it).
# Check 5's tag comparison is skipped with a note when no v* tags are visible
# (e.g. a shallow CI checkout without tags).
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

# Wall time for the whole run, reported at the end next to the denominators.
# rules/11 §2.1: a gate that reports "nothing wrong" far faster than its claimed
# work allows did not do the work — but that tell is unavailable unless someone
# records the duration. Printed, never gated: a duration threshold in CI is flaky
# under runner variance, and a flaky gate gets disabled, which is how a control
# becomes inert. Whole seconds only ($SECONDS), because sub-second timing is not
# portable to the macOS bash 3.2 this script still supports.
START_SECONDS=$SECONDS

MAX_LINES=500
MAX_DESC=1024
fail=0
# --- --self-test: every check must have a known-bad, or a declared exemption ---
# `sota-code-security` rules/12 §1b: a negative control belongs INSIDE the tool, so
# "every check can go red" is a property of the suite rather than of whoever last
# edited it. Until 2026-08-20 this repo did not practise its own rule — the probes
# lived only in check-negative-controls.sh, and remembering to add one was a
# sentence in AGENTS.md. Invariant 18 was added without a probe in the same commit,
# which is the failure mode exactly.
#
# The structural half runs in a second and is the part that cannot be forgotten:
# a check that is neither probed nor declared-exempt fails. Both sets are derived
# from check-negative-controls.sh itself — the `probe N` calls and the numbers in
# its own "NOT COVERED" block — so there is no second list to drift. The probe
# COUNT stays ungated on purpose (a static count of call sites under-reads).
# Then it hands off to the harness, which actually watches each check fail.
if [ "${1:-}" = "--self-test" ]; then
  harness="$(dirname "$0")/check-negative-controls.sh"
  [ -r "$harness" ] || { echo "FAIL: cannot read $harness"; exit 1; }
  python3 - "$0" "$harness" <<'SELFPY' || exit 1
import re, sys, pathlib
inv, neg = (pathlib.Path(a).read_text(encoding="utf-8") for a in sys.argv[1:3])

marks = re.findall(r'echo "\[(\d+)/(\d+)\]', inv)
totals = {int(n) for _, n in marks}
if len(totals) != 1:
    print("FAIL: check markers disagree on the total: %s" % sorted(totals)); sys.exit(1)
N = totals.pop()
checks = set(range(1, N + 1))

probed = {int(m) for m in re.findall(r'^probe (\d+) ', neg, re.M)}

# the exemptions, read from the harness's own NOT COVERED block — the same text
# invariant 17 already gates the documentation against
tail = neg.split("NOT COVERED", 1)
declared = set()
if len(tail) == 2:
    for line in tail[1].splitlines():
        m = re.match(r'\s*echo "\s+((?:\d+,\s*)*\d+)\s+—', line)
        if m:
            declared |= {int(x) for x in re.findall(r'\d+', m.group(1))}

missing = sorted(checks - probed - declared)
both    = sorted(probed & declared)
strays  = sorted((probed | declared) - checks)
bad = 0
for n in missing:
    bad = 1
    print("FAIL: check %d has no known-bad in check-negative-controls.sh and is not "
          "declared unprobeable — add a probe, or say why it cannot have one" % n)
for n in both:
    bad = 1
    print("FAIL: check %d is both probed and declared unprobeable" % n)
for n in strays:
    bad = 1
    print("FAIL: %d is probed or declared but is not a check in this script" % n)
if bad: sys.exit(1)
print("    ok (%d checks: %d probed, %d declared unprobeable, 0 unaccounted)"
      % (N, len(probed), len(declared)))
SELFPY
  echo "[self-test] structural: every check accounted for"
  echo "[self-test] handing off to the harness — it watches each one actually fail"
  exec "$harness"
fi

note() { printf '    %s\n' "$1"; }

# Every file-list-driven check reports HOW MANY items it examined, and fails on
# an empty scope. "0 checked, 0 failed, exit 0" is the signature of a gate whose
# pathspec drifted — the gate reads as green while verifying nothing. Found here
# by mutation on 2026-07-30: renaming the rules/ pathspec made checks 2 and 10
# print "ok" over zero files, and check 6's tree recount did NOT catch it because
# the SKILL.md count was unchanged. See sota-code-security rules/11 §2.
# Returns 1 on an empty scope so callers can set fail=1.
scope() {  # <count> <noun> — returns 1 on an empty scope; prints nothing on success
  if [ "$1" -eq 0 ]; then
    note "SCOPE EMPTY: examined 0 $2 — pathspec drift? a gate that checks nothing passes silently"
    return 1
  fi
  return 0
}

# --- 1. Line budget -------------------------------------------------------
# ONLY INSTRUCTION FILES ARE CAPPED. A file is capped iff an agent loads it as
# instructions -- skills/*/SKILL.md and skills/*/rules/*.md, nothing else. The cap
# is load-bearing only there: a rules/SKILL file over ~500 lines defeats
# incremental loading (the whole point is that the model reads the rules matching
# the task, not a wall of text). Everything else in this repo -- README,
# CHANGELOG, docs/, evals/, AGENTS.md, these scripts -- is prose or code read by
# people, deliberately uncapped since 2026-07-15; navigability there comes from a
# table of contents and docs/INDEX.md, not a line ceiling.
echo "[1/18] Skill Markdown (skills/**) <= ${MAX_LINES} lines"
over=0
seen1=0
while IFS= read -r f; do
  [ -f "$f" ] || { note "SKIPPED (tracked but missing from worktree): $f"; continue; }
  seen1=$((seen1 + 1))
  # awk NR, not `wc -l`: counts a final line without trailing newline too.
  n=$(awk 'END{print NR}' "$f")
  if [ "$n" -gt "$MAX_LINES" ]; then
    note "OVER ${MAX_LINES} (${n} lines): $f"
    over=1
  fi
done < <(git ls-files 'skills/*/*.md' 'skills/*/rules/*.md')
scope "$seen1" "skill files" || over=1
if [ "$over" -eq 0 ]; then echo "    ok ($seen1 skill files)"; else fail=1; fi

# --- 2. Audit checklist ends every rules file ------------------------------
echo "[2/18] Every skills/*/rules/*.md ends with an '## Audit checklist'"
missing=0
seen2=0
while IFS= read -r f; do
  [ -f "$f" ] || { note "SKIPPED (tracked but missing from worktree): $f"; continue; }
  seen2=$((seen2 + 1))
  # The checklist must be the file's LAST '## ' heading (docs say "ends
  # with"). Track code-fence state so a '## Audit checklist' INSIDE a fence
  # doesn't satisfy the check (the 2026-07-01 fix missed this; 2026-07-10
  # audit reproduced the bypass). A trailing suffix is still allowed — four
  # files use '## Audit checklist (meta — …)' legitimately.
  last_h2=$(awk '/^(```|~~~)/{fence=!fence} !fence && /^## /{h=$0} END{print h}' "$f")
  case "$last_h2" in
    '## Audit checklist'*) ;;
    *) note "MISSING/NOT-LAST '## Audit checklist': $f"; missing=1 ;;
  esac
done < <(git ls-files 'skills/*/rules/*.md')
scope "$seen2" "rules files" || missing=1
if [ "$missing" -eq 0 ]; then echo "    ok ($seen2 rules files)"; else fail=1; fi

# --- 3. No internal/private references -------------------------------------
# Keep the library generic and shareable. Two pattern sets:
#   - generic reader-assumption phrases, tracked right here;
#   - a PRIVATE denylist of pre-publication internal names, deliberately NOT
#     tracked: a tracked list would disclose the very names it suppresses.
#     (The pre-July-2026 list remains in public git history — accepted risk,
#     decided 2026-07-01; see docs/AUDIT-2026-07-01.md finding S1.)
# Private patterns load from $SOTA_DENYLIST (CI: repository secret) or
# .denylist.local (git-ignored, one ERE per line, '#' comments). When neither
# exists (e.g. an external fork's PR), only the generic phrases are checked —
# the maintainer's pre-commit hook and this repo's CI carry the full list.
echo "[3/18] No internal-name leaks"
DENY='the user runs|the user operates'
if [ -n "${SOTA_DENYLIST:-}" ]; then
  DENY="$DENY|$SOTA_DENYLIST"
elif [ -f .denylist.local ]; then
  extra=$(grep -vE '^[[:space:]]*(#|$)' .denylist.local | paste -sd'|' - || true)
  if [ -n "$extra" ]; then
    DENY="$DENY|$extra"
  else
    # An all-comment or unreadable .denylist.local silently degraded this check to the
    # two generic phrases, with output byte-identical to a full scan (found 2026-08-16).
    note "(private denylist present but empty/unparseable — generic checks only)"
  fi
else
  note "(private denylist unavailable — generic checks only)"
fi
# Case-insensitive so casing variants can't slip past; errors are fatal, not
# swallowed (a scan that can't read a file must not pass). This script holds
# the generic phrase patterns, so it is excluded from its own scan.
set +e
hits=$(git grep -iInE "$DENY" -- ':(exclude)scripts/check-invariants.sh')
rc=$?
name_hits=$(git ls-files | grep -iE "$DENY")
nrc=$?
set -e
if [ "$rc" -gt 1 ] || [ "$nrc" -gt 1 ]; then
  note "ERROR: denylist scan failed (grep exit content=$rc names=$nrc)"
  fail=1
elif [ -n "$hits" ] || [ -n "$name_hits" ]; then
  note "Internal reference(s) found — keep the library generic:"
  { printf '%s\n' "$hits"; printf '%s\n' "$name_hits" | sed 's/$/ (file name)/'; } \
    | sed '/^ *(file name)$/d; s/^/      /'
  fail=1
else
  echo "    ok"
fi

# --- 4. Skill description length <= 1024 chars ----------------------------
# The Agent Skills spec caps `description` at 1024 characters; loaders (Claude
# Code, Codex, ...) skip any skill that exceeds it. Count Unicode characters
# (descriptions use em-dashes: 1 char, 3 bytes) via python3, parsing both
# folded block scalars (`>-`) and plain single-line descriptions.
echo "[4/18] Every skills/*/SKILL.md description <= ${MAX_DESC} characters"
if command -v python3 >/dev/null 2>&1; then
  if desc_out=$(python3 - "$MAX_DESC" <<'PY'
import sys, glob, re
cap = int(sys.argv[1])
bad = 0
def get_desc(text):
    """Return (description, yaml_error_or_None)."""
    m = re.match(r'---\n(.*?)\n---', text, re.S)
    if not m:
        return None, None
    lines = m.group(1).split('\n')
    for i, ln in enumerate(lines):
        if ln.startswith('description:'):
            rest = ln[len('description:'):].strip()
            if rest[:1] in ('>', '|'):           # block scalar
                buf = []
                for cont in lines[i + 1:]:
                    if cont.strip() and not cont[:1].isspace():
                        break                    # next top-level key ends it
                    buf.append(cont.strip())
                return ' '.join(x for x in buf if x), None
            # Plain (unquoted) inline scalar: ': ' inside it, or a trailing
            # ':', is invalid YAML — strict loaders reject the frontmatter
            # and silently skip the skill. Quoted scalars are fine.
            err = None
            if rest[:1] not in ('"', "'") and (': ' in rest or rest.endswith(':')):
                err = "unquoted ':' in inline description (invalid YAML — use 'description: >-')"
            return rest.strip('\'"'), err        # plain / quoted single line
    return None, None
def get_name(text):
    m = re.match(r'---\n(.*?)\n---', text, re.S)
    if not m:
        return None
    n = re.search(r'^name:\s*(.+)$', m.group(1), re.M)
    return n.group(1).strip().strip('\'"') if n else None

# Anthropic's Agent Skills reference states two constraints the agentskills.io
# spec page does not: `name` and `description` "Cannot contain XML tags", and
# `name` "Cannot contain reserved words: anthropic, claude". Found 2026-08-02 by
# re-verifying an ABSENCE claim ("there is no size cap") against a SECOND
# independent source, exactly as skills/sota/rules/01 sections 5 and 7 require --
# and the second source is the only one that carries these. sota-dotnet's
# description held `Span<T>/Memory<T>`, which is a well-formed XML start tag.
XML_TAG = re.compile(r'<[A-Za-z/][^>]*>')
RESERVED = ('anthropic', 'claude')
files4 = sorted(glob.glob('skills/*/SKILL.md'))
print("SCOPE %d" % len(files4))
for f in files4:
    d, err = get_desc(open(f, encoding='utf-8').read())
    if not d:
        print(f"MISSING/EMPTY description: {f}"); bad = 1; continue
    if err:
        print(f"{err}: {f}"); bad = 1
    if len(d) > cap:
        print(f"OVER {cap} ({len(d)} chars): {f}"); bad = 1
    hits = XML_TAG.findall(d)
    if hits:
        print(f"XML TAG in description {hits[:3]} (spec: descriptions cannot contain XML tags): {f}")
        bad = 1
    n = get_name(open(f, encoding='utf-8').read())
    if n:
        if XML_TAG.search(n):
            print(f"XML TAG in name: {f}"); bad = 1
        for w in RESERVED:
            if w in n.lower():
                print(f"RESERVED WORD '{w}' in name '{n}': {f}"); bad = 1
sys.exit(1 if bad else 0)
PY
  ); then
    # Denominator, per this file's own rule at the top: a drifted glob that
    # examines 0 files used to print "ok" and exit 0 here (found 2026-08-16).
    n4=$(printf '%s\n' "$desc_out" | sed -n 's/^SCOPE //p')
    if scope "${n4:-0}" "SKILL.md descriptions"; then
      echo "    ok (${n4} descriptions)"
    else
      fail=1
    fi
  else
    printf '%s\n' "$desc_out" | grep -v '^SCOPE ' | sed 's/^/    /'
    fail=1
  fi
else
  note "SKIPPED: python3 not found (CI enforces this check)"
fi

# --- 5. Version lockstep ----------------------------------------------------
# One version, four places: VERSION, plugin.json, the CHANGELOG's top entry,
# and (after the release lands) the newest v* tag. Drift here shipped a main
# briefly claiming 1.8.0 with 1.9.0 content (2026-07-03) — hence a hard check.
echo "[5/18] Version lockstep (VERSION == plugin.json == CHANGELOG top; tag not ahead)"
v5=0
ver=$(tr -d '[:space:]' < VERSION)
# Strict X.Y.Z: rejects interior malformations (1..2, 1.2, 1.2.3.4) the old
# character-class guard missed (2026-07-10 audit).
if ! printf '%s' "$ver" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$'; then
  note "VERSION is not a plain X.Y.Z semver: '$ver'"; v5=1
fi
pj=$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' .claude-plugin/plugin.json | head -n 1)
[ "$pj" = "$ver" ] || { note "plugin.json version '$pj' != VERSION '$ver'"; v5=1; }
top=$(grep -m 1 -E '^## \[' CHANGELOG.md | sed 's/^## \[\([^]]*\)\].*/\1/')
case "$top" in
  Unreleased|"$ver") ;;
  *) note "CHANGELOG top entry is [$top] — expected [Unreleased] or [$ver]"; v5=1 ;;
esac
# Newest v* tag by semver sort. VERSION may lead the tag (open release PR);
# a tag ahead of VERSION means VERSION was never bumped — fail.
tag=$(git tag --list 'v[0-9]*' | sed 's/^v//' | sort -t. -k1,1n -k2,2n -k3,3n | tail -n 1)
if [ -z "$tag" ]; then
  note "(no v* tags visible — tag check skipped; needs a full-depth checkout)"
else
  newest=$(printf '%s\n%s\n' "$tag" "$ver" | sort -t. -k1,1n -k2,2n -k3,3n | tail -n 1)
  if [ "$tag" != "$ver" ] && [ "$newest" = "$tag" ]; then
    note "newest tag v$tag is AHEAD of VERSION $ver — bump VERSION + plugin.json"
    v5=1
  fi
fi
if [ "$v5" -eq 0 ]; then echo "    ok"; else fail=1; fi

# --- 6. Count-bearing surfaces match the tree --------------------------------
# The drift class the 2026-07-01 audit kept finding: skill/file/line counts
# rot on surfaces nobody recounts (the social preview said "30 skills" for
# three releases). Recount from the tree and compare every tracked surface;
# RELEASING.md lists the same surfaces for manual release edits.
echo "[6/18] Count-bearing surfaces match the tree"
v6=0
ck() { # ck <found> <expected> <surface>
  [ "$1" = "$2" ] || { note "$3: says '${1:-<not found>}', tree says '$2'"; v6=1; }
}
ck_floor() { # ck_floor <found-floor> <actual> <surface> — "N+" surfaces (the
  # social-preview image and its alt say "40+" so the PNG needn't be
  # re-rendered/re-uploaded every release): pass while actual >= floor.
  case "$1" in
    ''|*[!0-9]*) note "$3: no 'N+' floor found (expected e.g. '40+')"; v6=1; return ;;
  esac
  [ "$2" -ge "$1" ] || { note "$3: floor '$1+' is ahead of tree count '$2'"; v6=1; }
}
n_skills=$(git ls-files 'skills/*/SKILL.md' | wc -l | tr -d ' ')
n_files=$(git ls-files 'skills/' | grep -c '\.md$' || true)
n_lines=$(git ls-files 'skills/' | grep '\.md$' | tr '\n' '\0' | xargs -0 cat | awk 'END{print NR}')
n_klines=$(awk -v l="$n_lines" 'BEGIN{printf "%d", (l + 500) / 1000}')
n_domains=$((n_skills - 1))   # every skill except the router

ck "$(sed -n 's/.*badge\/skills-\([0-9]*\)-.*/\1/p' README.md | head -n 1)" \
   "$n_skills" "README badge"
hero=$(grep -m 1 -E '[0-9]+ skills \([0-9]+ files, ~[0-9]+k lines\)' README.md || true)
ck "$(printf '%s' "$hero" | grep -oE '[0-9]+ skills \(' | grep -oE '[0-9]+' || true)" \
   "$n_skills" "README hero skill count"
ck "$(printf '%s' "$hero" | grep -oE '\([0-9]+ files' | grep -oE '[0-9]+' || true)" \
   "$n_files" "README hero file count"
ck "$(printf '%s' "$hero" | grep -oE '~[0-9]+k lines' | grep -oE '[0-9]+' || true)" \
   "$n_klines" "README hero ~k-lines"
ck_floor "$(sed -n 's/.*alt="SOTA Engineering Skills — \([0-9]*\)+ .*/\1/p' README.md | head -n 1)" \
   "$n_skills" "README social-preview alt (N+)"
ck "$(sed -n 's/^A library of \([0-9]*\) domain skills.*/\1/p' skills/sota/SKILL.md | head -n 1)" \
   "$n_domains" "router body (skills/sota/SKILL.md)"
for j in .claude-plugin/plugin.json .claude-plugin/marketplace.json; do
  ck "$(sed -n 's/.*(\([0-9]*\) skills).*/\1/p' "$j" | head -n 1)" "$n_skills" "$j skill count"
  ck "$(sed -n 's/.*across \([0-9]*\) domains.*/\1/p' "$j" | head -n 1)" "$n_domains" "$j domain count"
done
ck_floor "$(sed -n 's/.*>\([0-9]*\)+ skills<.*/\1/p' assets/social-preview.html | head -n 1)" \
   "$n_skills" "social-preview.html pill (N+)"
if [ "$v6" -eq 0 ]; then echo "    ok"; else fail=1; fi

# --- 7. Router completeness -----------------------------------------------
# Every domain skill must appear in the router's routing table (as a
# `sota-name` table row) AND its library map (as **sota-name/rules**); every
# library-map entry must name a real skill dir. Catches the drift the
# 2026-07-10 audit found: sota-confidential-computing was added to the table
# but missing from the map for a full release.
echo "[7/18] Router lists every skill (routing table + library map)"
v7=0
seen7=0
router=skills/sota/SKILL.md
bt='`'
for d in skills/sota-*/; do
  name=$(basename "$d")
  seen7=$((seen7 + 1))
  grep -qE "^\| ${bt}${name}${bt} " "$router" || { note "routing table missing: $name"; v7=1; }
  grep -qF "**${name}/rules**" "$router" || { note "library map missing: $name"; v7=1; }
done
while IFS= read -r name; do
  [ -d "skills/$name" ] || { note "library map names a non-existent skill: $name"; v7=1; }
done < <(grep -oE '\*\*sota-[a-z-]+/rules\*\*' "$router" | sed 's/\*\*//g; s#/rules##')
scope "$seen7" "domain skills" || v7=1
if [ "$v7" -eq 0 ]; then echo "    ok ($seen7 domain skills)"; else fail=1; fi

# --- 8. Internal Markdown links resolve -----------------------------------
# Every relative Markdown link whose target is a *.md file must resolve to a
# file that exists, in ANY tracked *.md (skills, README, docs, CHANGELOG,
# evals). Catches the link rot a rename/move leaves behind — the class the
# 2026-07-24 dry run found already live in evals/results (../../docs vs the
# real ../../../docs). Scoped to *.md targets on purpose: broadening to every
# relative link flags prose/code fragments that match the [text](x) shape
# (type annotations like `(x: T)`, `(std|default)`) — a false-positive source
# with no rot-catching upside. Fenced AND inline code are stripped so link-shaped
# examples (in ``` fences or `backticks`) are not scanned. Idea from vault-doctor
# (training-knowledge-vault); see docs/ADOPTION-LOG.md.
echo "[8/18] Internal Markdown links resolve (*.md targets)"
if command -v python3 >/dev/null 2>&1; then
  if link_out=$(python3 - <<'PY'
import os, re, sys
files = [l for l in os.popen("git ls-files '*.md'").read().splitlines() if l.strip()]
print("SCOPE %d" % len(files))
LINK = re.compile(r'(?<!\!)\[[^\]]*\]\(([^)]+)\)')   # [text](target); (?<!!) skips images
bad = 0
for f in files:
    try:
        text = open(f, encoding='utf-8').read()
    except OSError:
        continue
    # drop fenced AND inline code so link-shaped *examples* (e.g. this file's own
    # `[text](file.md)`) are not mistaken for real links
    text = re.sub(r'```.*?```', '', text, flags=re.S)
    text = re.sub(r'~~~.*?~~~', '', text, flags=re.S)
    text = re.sub(r'`[^`\n]*`', '', text)
    for m in LINK.finditer(text):
        raw = m.group(1).strip()
        if raw.startswith(('http://', 'https://', 'mailto:', 'tel:', '#', '<')):
            continue                                   # external / anchor-only / autolink
        tgt = raw.split('#', 1)[0].split('?', 1)[0].strip()
        if not tgt.endswith('.md'):
            continue                                   # *.md targets only (see comment)
        target = os.path.normpath(os.path.join(os.path.dirname(f), tgt))
        if not os.path.exists(target):
            print(f"BROKEN LINK  {f}: ({raw})")
            bad = 1
sys.exit(1 if bad else 0)
PY
  ); then
    # Denominator (added 2026-08-16): an empty pathspec used to print "ok", exit 0.
    n8=$(printf '%s\n' "$link_out" | sed -n 's/^SCOPE //p')
    if scope "${n8:-0}" "markdown files"; then
      echo "    ok (${n8} markdown files)"
    else
      fail=1
    fi
  else
    printf '%s\n' "$link_out" | grep -v '^SCOPE ' | sed 's/^/    /'
    fail=1
  fi
else
  note "SKIPPED: python3 not found (CI enforces this check)"
fi

# --- 9. One [Unreleased] section, at the top ---------------------------------
# Check 5 reads only the FIRST '## [' heading, so a duplicate [Unreleased]
# further down is invisible to it. Two feature PRs each opened one above the
# previous release (2026-07-28) and both sat on main until a human noticed
# during the release cut. Fence-aware, like check 2: a CHANGELOG entry may
# legitimately quote '## [Unreleased]' inside a code fence.
echo "[9/18] CHANGELOG has at most one [Unreleased], and it is the top entry"
v9=0
changelogs="CHANGELOG.md $(git ls-files 'docs/CHANGELOG-archive*.md' | tr '\n' ' ')"
for cl in $changelogs; do
  [ -f "$cl" ] || continue
  # strip fenced blocks so quoted headings inside ``` are not counted
  body=$(awk '/^(```|~~~)/ { fence = !fence; next } !fence' "$cl")
  n=$(printf '%s\n' "$body" | grep -cE '^## \[Unreleased\]' || true)
  case "$cl" in
    CHANGELOG.md)
      if [ "$n" -gt 1 ]; then
        note "CHANGELOG.md has $n '## [Unreleased]' headings — merge them into one"
        v9=1
      elif [ "$n" -eq 1 ]; then
        # No `grep -m 1` / `head` here: they close the pipe early, the upstream
        # printf dies of SIGPIPE, and `set -o pipefail` + `set -e` then kill the
        # script mid-check — it printed the heading and nothing else. (Check 5's
        # `grep -m 1` is safe only because it reads a FILE, not a pipe.)
        first=$(printf '%s\n' "$body" | grep -E '^## \[' | sed -n '1s/^## \[\([^]]*\)\].*/\1/p')
        if [ "$first" != "Unreleased" ]; then
          note "CHANGELOG.md has an [Unreleased] section below [$first] — it must be the top entry"
          v9=1
        fi
      fi
      ;;
    *)
      if [ "$n" -gt 0 ]; then
        note "$cl has an '## [Unreleased]' heading — archives hold released versions only"
        v9=1
      fi
      ;;
  esac
done
if [ "$v9" -eq 0 ]; then echo "    ok"; else fail=1; fi

# --- 10. Every rules file is indexed by its own SKILL.md ---------------------
# The library's loading model is: SKILL.md loads first, and the model reads only
# the rules files its index points at. So a rules file that no SKILL.md mentions
# is written, reviewed, capped, checklist-ed — and never loaded. It is the
# skill-level twin of the problem invariant 7 solved one level up (a skill
# missing from the router) and of the front-door gap RELEASING.md §2b covers
# (a capability with no README mention): the artifact exists, nothing errors,
# and it is unreachable. Same class as `sota-devsecops` rules/03 §3.9, applied
# to ourselves. All 255 rules files passed when this landed, so it is a
# regression gate, not a repair; it was watched to fail on an injected file
# and on a renamed reference before being trusted.
echo "[10/18] Every skills/*/rules/*.md is referenced by its own SKILL.md"
v10=0
seen10=0
while IFS= read -r rf; do
  seen10=$((seen10 + 1))
  skill_dir=$(dirname "$(dirname "$rf")")
  sk="$skill_dir/SKILL.md"
  base=$(basename "$rf")
  if [ ! -f "$sk" ]; then
    note "$rf: no SKILL.md in $skill_dir"
    v10=1
  elif ! grep -qF "$base" "$sk"; then
    note "$rf: not referenced in $sk — the model never loads it (add it to the rules index)"
    v10=1
  fi
done < <(git ls-files 'skills/*/rules/*.md')
scope "$seen10" "rules files indexed" || v10=1
if [ "$v10" -eq 0 ]; then echo "    ok ($seen10 rules files indexed)"; else fail=1; fi

# --- 11. LAST-VERIFIED only moves alongside a sweep -------------------------
# The stamp is the date of the last FULL re-verification pass, not a recency
# marker for the newest verified fact — so a rules section may carry today's
# verification dates while the stamp is months old, by design. Bumping it on an
# ordinary edit asserts a sweep that never happened, planting a false green in
# the one control whose job is detecting stale claims.
#
# That rule was already written in AGENTS.md, docs/MAINTENANCE.md and
# check-freshness.sh's own header — and two separate sessions still proposed
# bumping it wrongly and caught themselves only on verification. A convention
# documented three times and still nearly broken twice is exactly
# `sota-code-security` rules/10 §2.12: a natural-language instruction standing in
# for an enforced control. So it becomes a gate.
#
# Two legitimate escapes, because docs/MAINTENANCE.md allows a BATCHED or a
# ROLLING pass:
#   (a) the diff is sweep-shaped — the 2026-07-08 sweep touched 100 skill files
#       (31 skills, 65 findings), so the floor sits far below a real one;
#   (b) the CHANGELOG diff names LAST-VERIFIED — which the runbook already
#       requires ("note the sweep in the CHANGELOG"), and which is how a rolling
#       pass declares its completion.
# This is the first DIFF-based invariant; every other check reads the whole tree.
# With no merge base it skips with a note rather than guessing, like checks 4/8.
SWEEP_MIN_SKILL_FILES=20
echo "[11/18] LAST-VERIFIED moves only with a sweep (batched diff, or declared in CHANGELOG)"
v11=0
base=""
for ref in origin/main main; do
  if git rev-parse --verify -q "$ref" >/dev/null 2>&1; then
    base=$(git merge-base HEAD "$ref" 2>/dev/null || true)
    [ -n "$base" ] && break
  fi
done
if [ -z "$base" ] || [ "$base" = "$(git rev-parse HEAD)" ]; then
  note "SKIPPED (no merge base to diff against, or nothing ahead of it)"
  echo "    ok (skipped)"
else
  changed=$(git diff --name-only "$base"...HEAD)
  # Compare the parsed DATE, not the file. Keying on the file meant a comment-only
  # edit demanded an escape — and the first such change (2026-07-31, moving the rule
  # into the file) satisfied it reflexively by naming LAST-VERIFIED in the CHANGELOG
  # even though the stamp never moved. A gate that fires on non-events trains people
  # to wave it through, which is how it becomes decorative (rules/12 §2).
  stamp_now=$(grep -v '^[[:space:]]*#' LAST-VERIFIED 2>/dev/null | tr -d '[:space:]' || true)
  stamp_was=$(git show "$base":LAST-VERIFIED 2>/dev/null | grep -v '^[[:space:]]*#' | tr -d '[:space:]' || true)
  if printf '%s\n' "$changed" | grep -qx 'LAST-VERIFIED' && [ "$stamp_now" != "$stamp_was" ]; then
    n_skill=$(printf '%s\n' "$changed" | grep -c '^skills/.*\.md$' || true)
    declared=0
    git diff "$base"...HEAD -- CHANGELOG.md | grep -q '^+.*LAST-VERIFIED' && declared=1
    if [ "$n_skill" -ge "$SWEEP_MIN_SKILL_FILES" ]; then
      echo "    ok (LAST-VERIFIED moved with $n_skill skill files — sweep-shaped)"
    elif [ "$declared" -eq 1 ]; then
      echo "    ok (LAST-VERIFIED moved and declared in the CHANGELOG)"
    else
      note "LAST-VERIFIED changed, but this diff touches only $n_skill skill file(s)"
      note "and the CHANGELOG does not mention LAST-VERIFIED. The stamp records a"
      note "FULL re-verification pass (the 2026-07-08 sweep touched 100 skill files)."
      note "If this really completes a rolling pass, say so in the CHANGELOG entry;"
      note "otherwise revert the stamp — an ordinary edit must not move it."
      v11=1
    fi
  elif printf '%s\n' "$changed" | grep -qx 'LAST-VERIFIED'; then
    echo "    ok (LAST-VERIFIED touched but the stamp is unchanged: $stamp_now)"
  else
    echo "    ok (LAST-VERIFIED unchanged)"
  fi
fi
if [ "$v11" -ne 0 ]; then fail=1; fi

# --- 12. Rendered assets are current --------------------------------------
# assets/*.png are committed BUILD OUTPUTS of the assets/*.html beside them, and
# nothing regenerates them. The README embeds the PNG and never the source — so an
# HTML edit that is not re-rendered is invisible to every reader, while the diff,
# the commit message and the CHANGELOG all report the surface fixed.
#
# Not hypothetical: PR #173 (2026-08-01) changed how-it-works.html from "every file
# < 500 lines" to "each < 500 lines" — the entire point of that PR — and left
# how-it-works.png at its #55 render from 2026-07-09. main served the stale claim
# for the rest of the day on the one surface anybody actually looks at.
#
# Passes all three docs/CONVENTIONS-LEDGER.md filters: it has already failed; it
# fails SILENTLY (nobody reads the HTML, and the PNG looks fine — it just says the
# old thing); and it is mechanically checkable from git log alone.
#
# COMMIT times, not mtimes: a fresh clone stamps every file with the checkout time,
# so an mtime comparison would pass on any CI runner — green while examining
# nothing (rules/11 §2.2). Equal timestamps PASS: rendering in the same commit as
# the edit is the wanted behaviour, not a violation.
#
# Escape: "[no-render]" in the HTML's own last commit subject, for an edit that
# cannot change the output. Deliberately a DECLARATION and not a heuristic —
# invariant 11 learned that a gate firing on non-events gets waved through until it
# is decorative, and nothing short of rendering both can tell a cosmetic HTML edit
# from a load-bearing one.
#
# HISTORY-based, like check 11's diff: with no commit history for a pair it skips
# with a note rather than guessing, because a shallow clone must not read as a pass.
echo "[12/18] Rendered assets: each assets/*.png is no older than its *.html"
v12=0
seen12=0
checked12=0
while IFS= read -r html; do
  seen12=$((seen12 + 1))
  png="${html%.html}.png"
  html_ct=$(git log -1 --format=%ct -- "$html" 2>/dev/null || true)
  if [ -z "$html_ct" ]; then
    note "SKIPPED (no commit history for $html — shallow clone?)"
    continue
  fi
  if ! git ls-files --error-unmatch "$png" >/dev/null 2>&1; then
    note "NEVER RENDERED: $html has no committed $png"
    note "  Render it and commit both (CONTRIBUTING.md -> Rendered assets)."
    v12=1
    continue
  fi
  png_ct=$(git log -1 --format=%ct -- "$png" 2>/dev/null || true)
  if [ -z "$png_ct" ]; then
    note "SKIPPED (no commit history for $png — shallow clone?)"
    continue
  fi
  checked12=$((checked12 + 1))
  if [ "$html_ct" -gt "$png_ct" ]; then
    # Captured into a variable, NOT piped into grep -q: an early-exiting grep on a
    # pipe SIGPIPEs the upstream git and pipefail turns a MATCH into a failure —
    # the exact shape that made invariant 9's first cut look like it passed.
    subject=$(git log -1 --format=%s -- "$html" 2>/dev/null || true)
    case "$subject" in
      *"[no-render]"*)
        note "ok, declared [no-render]: $html"
        continue
        ;;
    esac
    note "STALE RENDER: $png is older than $html"
    # Full timestamp, not %cs: a same-day miss printed the SAME date on both lines
    # while asserting one was older, which reads as a broken check rather than a
    # real finding — and a check nobody believes is one they turn off.
    note "  $html last changed $(git log -1 --format=%ci -- "$html")"
    note "  $png last changed $(git log -1 --format=%ci -- "$png")"
    note "  The README embeds the PNG, not the source. Re-render and commit both"
    note "  (CONTRIBUTING.md -> Rendered assets), or put [no-render] in the commit"
    note "  subject when the edit cannot change the output."
    v12=1
  fi
done < <(git ls-files 'assets/*.html')
scope "$seen12" "rendered asset sources" || v12=1
if [ "$v12" -eq 0 ]; then
  if [ "$checked12" -eq 0 ] && [ "$seen12" -gt 0 ]; then
    echo "    ok (skipped — no usable commit history)"
  else
    echo "    ok ($checked12 asset pairs)"
  fi
fi
if [ "$v12" -ne 0 ]; then fail=1; fi

# --- 13. Every scoreboard row declares its sample size ---------------------
# The last actionable candidate in docs/CONVENTIONS-LEDGER.md. A lift from one run
# is typographically identical to a lift from ten, and this repo has been burned by
# exactly that twice: a +0.07 on inert-control detection did not survive growing the
# set from 15 to 49 cases and was RETRACTED, and a +0.40 published from one synced
# run became +0.39 on the two-run mean. Neither number looked uncertain on the page.
#
# Like invariant 10, this is a REGRESSION GUARD with no incident of its own: all 10
# rows populate the column today. It prevents the next row from being added without
# one, which is the cheap moment to catch it — the expensive moment is after the
# number has been quoted somewhere.
#
# Shape-driven, not position-driven: it finds any table whose header has a "Samples"
# column and checks that column in every data row beneath it. So it also fails when
# the column is RENAMED or dropped (0 tables -> SCOPE EMPTY), which is the drift a
# hardcoded column index would sail straight past.
echo "[13/18] Every scoreboard row declares its sample size"
v13=0
BOARD="evals/results/RESULTS.md"
if [ ! -f "$BOARD" ]; then
  note "SKIPPED (no $BOARD in this checkout)"
  echo "    ok (skipped)"
else
  s13=$(awk -F'|' '
    /^\|/ {
      if (!intable) {
        for (i = 1; i <= NF; i++) {
          g = $i; gsub(/^[ \t]+|[ \t]+$/, "", g)
          if (g == "Samples") { col = i; intable = 1; tables++; next }
        }
        next
      }
      if ($0 ~ /^\|[ :|-]*$/) next          # the |---|---| separator row
      rows++
      cell = $col;  gsub(/^[ \t]+|[ \t]+$/, "", cell)
      label = $2;   gsub(/^[ \t]+|[ \t]+$/, "", label)
      if (cell == "") printf "EMPTY\t%d\t%s\n", NR, label
      next
    }
    { intable = 0 }                          # a non-table line ends the table
    END { printf "TABLES\t%d\nROWS\t%d\n", tables, rows }
  ' "$BOARD")
  n_tables=$(printf '%s\n' "$s13" | awk -F'\t' '$1=="TABLES"{print $2}')
  n_rows=$(printf '%s\n' "$s13" | awk -F'\t' '$1=="ROWS"{print $2}')
  # Process substitution, NOT a pipe: a `| while` runs the loop in a subshell and
  # every v13=1 set inside it is discarded when the subshell exits — a gate that
  # finds offenders, prints them, and still exits 0.
  while IFS="$(printf '\t')" read -r kind line label; do
    [ "$kind" = "EMPTY" ] || continue
    note "NO SAMPLE SIZE: $BOARD:$line — \"$label\""
    v13=1
  done < <(printf '%s\n' "$s13")
  if [ "$v13" -ne 0 ]; then
    note "  A number without its n reads exactly like a number with one. State the"
    note "  sample size in the row (\"3×, temp 0.7\", \"1×\") — see evals/README.md."
  fi
  scope "${n_tables:-0}" "scoreboard tables with a Samples column" || v13=1
  scope "${n_rows:-0}" "scoreboard rows" || v13=1
  if [ "$v13" -eq 0 ]; then echo "    ok ($n_rows scoreboard rows)"; fi
fi
if [ "$v13" -ne 0 ]; then fail=1; fi

# --- 14. A release declares its front-door terms, and they resolve ---------
# Invariant 6 fails on a wrong NUMBER in the README. Nothing failed on a
# capability that never got a sentence anywhere a reader looks: at the v1.19.7 cut,
# `adversarial`, `refut`, `decision ledger`, `inert`, `no-op` and `ADOPTION-LOG` all
# returned ZERO hits in README.md — five capabilities shipped across three releases
# with no front-door mention. RELEASING.md section 2b has prescribed the grep since,
# and it has caught something at THREE consecutive cuts, which is the argument for a
# gate rather than evidence the habit sticks.
#
# DISCOVERY IS NOT MECHANIZABLE -- "what counts as a capability" is judgement, which
# is why this candidate sat blocked in docs/CONVENTIONS-LEDGER.md. DECLARATION IS.
# So this gates the verification, not the discovery, exactly as invariant 11 gates
# LAST-VERIFIED with escapes that are declarations which must be TRUE.
#
# Only fires on a RELEASE commit (VERSION changed against the merge base), so it adds
# nothing to an ordinary PR. On a release it requires, in the new version's CHANGELOG
# section, a line of the form:
#
#     **Front door checked:** term one · term two · term three
#
# and then verifies every term BOTH ways: it must appear in README.md or
# docs/INDEX.md (the front door is real), AND in that release's own CHANGELOG section
# (you cannot pass by declaring a filler word that was never part of the release).
# A missing line on a release commit fails closed.
echo "[14/18] A release declares its front-door terms, and they resolve"
v14=0
base14=""
for ref in origin/main main; do
  if git rev-parse --verify -q "$ref" >/dev/null 2>&1; then
    base14=$(git merge-base HEAD "$ref" 2>/dev/null || true)
    [ -n "$base14" ] && break
  fi
done
if [ -z "$base14" ] || [ "$base14" = "$(git rev-parse HEAD)" ]; then
  note "SKIPPED (no merge base to diff against, or nothing ahead of it)"
  echo "    ok (skipped)"
elif ! git diff --name-only "$base14"...HEAD | grep -qx 'VERSION'; then
  echo "    ok (not a release commit — VERSION unchanged)"
else
  # The release section is the one matching VERSION -- NOT the topmost '## ['
  # heading. Keying on the top heading read [Unreleased] instead when one still sat
  # above the new entry, and reported "no declaration" for a release that had one.
  # Found by watching case C fail for the wrong reason.
  ver=$(tr -d '[:space:]' < VERSION)
  sec=$(awk -v v="## [$ver]" 'index($0,v)==1{f=1;print;next} f&&/^## \[/{exit} f{print}' CHANGELOG.md)
  if [ -z "$sec" ]; then
    note "VERSION is $ver but CHANGELOG.md has no '## [$ver]' section to check"
    v14=1
    sec=""
  fi
  # ANCHORED to line start. Unanchored, this also matched the format example quoted
  # inside invariant 14's own CHANGELOG entry ("`**Front door checked:** term · term`
  # to its CHANGELOG section..."), and the two matches concatenated into garbage terms.
  # Found on this gate's FIRST real release, which is the point of shipping it early.
  # A declaration is its own line: unindented, unbackticked.
  decl=$(printf '%s\n' "$sec" | grep -i '^\*\*Front door checked:\*\*' || true)
  if [ -z "$decl" ]; then
    note "VERSION changed but this release declares no front-door check."
    note "  Add to the new CHANGELOG section (RELEASING.md section 2b):"
    note "    **Front door checked:** <term> · <term>"
    note "  Each term must appear in README.md or docs/INDEX.md, and in this section."
    v14=1
  else
    # shellcheck disable=SC2016  # single-quoted sed scripts, not expansions
    terms=$(printf '%s\n' "$decl" | sed 's/.*\*\*[Ff]ront door checked:\*\*//' \
      | tr '·,;' '\n' | sed 's/^[[:space:]]*//; s/[[:space:]]*$//; s/^[`*]*//; s/[`*.]*$//' \
      | grep -v '^$' || true)
    n_terms=0
    while IFS= read -r t; do
      [ -n "$t" ] || continue
      n_terms=$((n_terms + 1))
      if ! grep -qiF -- "$t" README.md docs/INDEX.md 2>/dev/null; then
        note "NO FRONT DOOR: \"$t\" appears in neither README.md nor docs/INDEX.md"
        v14=1
      fi
      # Guard against declaring a word that was never part of this release.
      if ! printf '%s\n' "$sec" | grep -v '\*\*[Ff]ront door checked:\*\*' | grep -qiF -- "$t"; then
        note "NOT IN THIS RELEASE: \"$t\" is declared but absent from the release's own entry"
        v14=1
      fi
    done <<EOF
$terms
EOF
    scope "$n_terms" "declared front-door terms" || v14=1
    if [ "$v14" -eq 0 ]; then echo "    ok ($n_terms terms declared, all resolve)"; fi
  fi
fi
if [ "$v14" -ne 0 ]; then fail=1; fi

# --- 15. Router library map lists every rules FILE ------------------------
# Check 7 proves every SKILL is in the map. Check 10 proves every rules file is
# indexed by its OWN SKILL.md. Neither reads the map's CONTENTS — which is how
# sota-code-security/rules/11 stayed unlisted in the router for two releases
# (v1.19.8 → v1.21.0) with all fourteen checks green. Both directions matter: a
# file absent from the map is invisible to a router-driven load, and a map entry
# for a file that no longer exists sends the model after nothing.
echo "[15/18] Router library map lists every rules file (both directions)"
v15=0
if command -v python3 >/dev/null 2>&1; then
  map_out=$(python3 - <<'MAPPY'
import os, re, glob, sys
router = "skills/sota/SKILL.md"
try:
    lines = open(router, encoding="utf-8").read().splitlines()
except OSError as e:
    print("ERROR: cannot read %s: %s" % (router, e))
    print("SCOPE 0")
    sys.exit(1)

# A map entry is "- **<skill>/rules**: 01 title, 02 title, ..." and wraps onto
# indented continuation lines until the next list item or an unindented line.
entries, name = {}, None
for line in lines:
    m = re.match(r'^- \*\*(sota-[a-z-]+)/rules\*\*:(.*)$', line)
    if m:
        name = m.group(1)
        entries[name] = m.group(2)
        continue
    if name is not None:
        if line.startswith("- ") or (line.strip() and not line.startswith("  ")):
            name = None
        else:
            entries[name] += " " + line

# Anchor each number to a list position (entry start, or after a comma) so a
# title containing digits cannot read as a rules number: "02 NIST 800-53/800-171"
# must yield 02 and never 80, 53 or 17.
NUM = re.compile(r'(?:^|[:,])\s*(\d{2})\s')
dirs = sorted(glob.glob("skills/sota-*/rules"))
bad = 0
for d in dirs:
    skill = d.split("/")[1]
    files = set()
    for f in glob.glob(d + "/*.md"):
        b = os.path.basename(f)
        if re.match(r'^\d{2}-', b):
            files.add(b[:2])
    listed = set(NUM.findall(entries.get(skill, "")))
    for n in sorted(files - listed):
        print("map missing: %s/rules/%s-*.md exists but the router does not list it" % (skill, n))
        bad += 1
    for n in sorted(listed - files):
        print("map stale: router lists %s/rules %s but no such file exists" % (skill, n))
        bad += 1
print("SCOPE %d" % len(dirs))
sys.exit(1 if bad else 0)
MAPPY
  ) || v15=1
  n15=$(printf '%s\n' "$map_out" | sed -n 's/^SCOPE //p')
  while IFS= read -r l; do
    case "$l" in SCOPE\ *|'') ;; *) note "$l" ;; esac
  done <<EOF
$map_out
EOF
  scope "${n15:-0}" "skills with a rules/ dir" || v15=1
  if [ "$v15" -eq 0 ]; then echo "    ok (${n15:-0} skills, map matches the tree)"; fi
else
  note "SKIPPED (python3 not found; CI always has it)"
  echo "    ok (skipped)"
fi
if [ "$v15" -ne 0 ]; then fail=1; fi

# --- 16. The documented hook matches the installed hook -------------------
# install.sh WRITES the UserPromptSubmit hook; README DOCUMENTS it. Nothing kept
# them equal, and on 2026-08-05 three different texts existed at once: the
# README's block (two revisions behind), install.sh's HOOK_CMD, and what was
# actually in a user's settings.json. The README's is the one a reader copies by
# hand, so a stale block is the version that spreads. Silent by construction —
# nothing executes the README.
echo "[16/18] README's documented hook == install.sh's HOOK_CMD"
v16=0
if command -v python3 >/dev/null 2>&1; then
  hook_out=$(python3 - <<'HOOKPY'
import re, json, sys

FENCE = chr(96) * 3
try:
    readme = open("README.md", encoding="utf-8").read()
    lines = open("scripts/install.sh", encoding="utf-8").read().splitlines()
except OSError as e:
    print("ERROR: %s" % e); print("SCOPE 0"); sys.exit(1)

# The shipped value: the one HOOK_CMD assignment in install.sh.
PREFIX = 'readonly HOOK_CMD="'
sh = [l for l in lines if l.startswith(PREFIX)]
if len(sh) != 1:
    print("expected exactly 1 HOOK_CMD assignment in scripts/install.sh, found %d" % len(sh))
    print("SCOPE 0"); sys.exit(1)
shipped = sh[0][len(PREFIX):-1]

# The documented value: parse the fenced JSON rather than regexing the string, so
# a reformat of the block is not a false positive.
blocks = [b for b in re.findall(FENCE + r'json\n(.*?)' + FENCE, readme, re.S)
          if "UserPromptSubmit" in b]
documented = []
for b in blocks:
    try:
        d = json.loads(b)
    except json.JSONDecodeError as e:
        print("README JSON block does not parse: %s" % e)
        print("SCOPE 0"); sys.exit(1)
    for grp in d.get("hooks", {}).get("UserPromptSubmit", []):
        for h in grp.get("hooks", []):
            if "command" in h:
                documented.append(h["command"])

if not documented:
    print("no UserPromptSubmit command found in any README json block — "
          "the documented hook vanished, or the block stopped being valid JSON")
    print("SCOPE 0"); sys.exit(1)

bad = 0
for d in documented:
    if d != shipped:
        bad += 1
        print("README documents a hook install.sh does not write.")
        print("  README    (%d chars): %s" % (len(d), d[:90]))
        print("  HOOK_CMD  (%d chars): %s" % (len(shipped), shipped[:90]))
        for i, (x, y) in enumerate(zip(d, shipped)):
            if x != y:
                print("  first difference at char %d: %r vs %r" % (i, d[i:i+40], shipped[i:i+40]))
                break
        else:
            print("  one is a prefix of the other (length differs)")
print("SCOPE %d" % len(documented))
sys.exit(1 if bad else 0)
HOOKPY
  ) || v16=1
  n16=$(printf '%s\n' "$hook_out" | sed -n 's/^SCOPE //p')
  while IFS= read -r l; do
    case "$l" in SCOPE\ *|'') ;; *) note "$l" ;; esac
  done <<EOF
$hook_out
EOF
  scope "${n16:-0}" "documented hook commands" || v16=1
  if [ "$v16" -eq 0 ]; then echo "    ok (${n16:-0} documented hook, matches HOOK_CMD)"; fi
else
  note "SKIPPED (python3 not found; CI always has it)"
  echo "    ok (skipped)"
fi
if [ "$v16" -ne 0 ]; then fail=1; fi

# [17] The documents that DESCRIBE the checks drift from the checks themselves.
# Twice in one week: CONTRIBUTING.md listed part A's negative-control coverage as
# five invariants when the harness printed eleven, and CONVENTIONS-LEDGER.md headed
# its enforced section "(14) — invariants 1–14" while 15 and 16 were already gated
# and described in its own table below. Nothing read those documents, so a doc that
# under-describes the gates is indistinguishable from a correct one — the same
# class every other check here is about, aimed at our own prose.
#
# Two traps this had to be built around, both real in the current tree:
#   - "invariant 15 checks the router's library map" is a number followed by the
#     word "checks" and is NOT a count. Excluded by look-behind.
#   - a correction note that QUOTES the old wording ("(14) — invariants 1–14") is
#     history, not a claim. Counts inside double quotes are ignored, which is the
#     same supersede-don't-edit rule the CHANGELOG follows.
echo "[17/18] Docs describing the invariants agree with the scripts"
v17=0
if command -v python3 >/dev/null 2>&1; then
  doc_out=$(python3 - <<'DOCPY'
import re, sys, pathlib

DOCS = ["AGENTS.md", "CONTRIBUTING.md",
        "docs/CONVENTIONS-LEDGER.md", "docs/MAINTENANCE.md"]

def norm(s):
    s = s.replace("*", "").replace("`", "")
    return re.sub(r'"[^"\n]*"', '""', s)      # quotations are history, not claims

def flat(s):
    # Collapse wrapping: these lists are prose and wrap at ~80 cols, so a
    # substring test against the raw text fails on where the line happened to
    # break. Cost me one false positive before it was written down.
    return re.sub(r'\s+', ' ', norm(s))

try:
    inv = pathlib.Path("scripts/check-invariants.sh").read_text(encoding="utf-8")
    neg = pathlib.Path("scripts/check-negative-controls.sh").read_text(encoding="utf-8")
except OSError as e:
    print("ERROR: %s" % e); print("SCOPE 0"); sys.exit(1)

# --- the authority: the numbering the script actually prints -----------------
marks = re.findall(r'echo "\[(\d+)/(\d+)\]', inv)
if not marks:
    print("no [k/N] check markers found in check-invariants.sh")
    print("SCOPE 0"); sys.exit(1)
totals = {int(n) for _, n in marks}
if len(totals) != 1:
    print("check markers disagree on the total: %s" % sorted(totals))
    print("SCOPE 0"); sys.exit(1)
N = totals.pop()
ks = [int(k) for k, _ in marks]
if sorted(ks) != list(range(1, N + 1)):
    print("check numbers are not exactly 1..%d: %s" % (N, sorted(ks)))
    print("SCOPE 0"); sys.exit(1)

bad = 0
claims = 0

# --- every stated count must be N -------------------------------------------
COUNT_PATS = [
    # \b before the digits, or "Invariant 10 checks" matches the trailing "0"
    # and reports a phantom "0 checks" — it did, before the boundary was added.
    re.compile(r'(?<!invariant )(?<!Invariant )\b(\d+)\s+(?:checks|invariants)\b'),
    re.compile(r'invariants\s+1\s*[–-]\s*(\d+)'),
    re.compile(r'Enforced\s*\((\d+)\)'),
]
for f in DOCS:
    try:
        text = pathlib.Path(f).read_text(encoding="utf-8")
    except OSError as e:
        print("cannot read %s: %s" % (f, e)); bad += 1; continue
    for ln, line in enumerate(norm(text).splitlines(), 1):
        for pat in COUNT_PATS:
            for m in pat.finditer(line):
                claims += 1
                if int(m.group(1)) != N:
                    bad += 1
                    print("%s:%d says %r but check-invariants.sh has %d checks"
                          % (f, ln, m.group(0).strip(), N))

# --- the per-invariant descriptions must enumerate all N ---------------------
# The stated count and the actual list can drift apart: update "runs 18 checks"
# and forget the table row, and every count claim still agrees. AGENTS.md carries
# one table row per invariant; CONTRIBUTING.md carries one numbered item.
ENUMS = [("AGENTS.md", re.compile(r'^\| (\d+) \| ', re.M), "invariant table rows"),
         ("CONTRIBUTING.md", re.compile(r'^(\d+)\. ', re.M), "numbered invariant items")]
for f, pat, label in ENUMS:
    try:
        raw = pathlib.Path(f).read_text(encoding="utf-8")
    except OSError as e:
        print("cannot read %s: %s" % (f, e)); bad += 1; continue
    nums = sorted({int(x) for x in pat.findall(raw)})
    claims += 1
    if nums != list(range(1, N + 1)):
        bad += 1
        missing = [i for i in range(1, N + 1) if i not in nums]
        print("%s's %s are %s, not 1..%d%s"
              % (f, label, nums if len(nums) < 25 else "%d entries" % len(nums), N,
                 " (missing %s)" % missing if missing else ""))

# --- the two coverage lists the harness prints must appear verbatim ----------
def harness_list(prefix):
    m = re.search(re.escape(prefix) + r'\s*([0-9a-z, ]+?)\s*(?:\(|\.)', neg)
    return m.group(1).strip() if m else None

covered = harness_list("check-invariants.sh COVERED:")
vs_list = harness_list("verify-setup.sh: checks")
m = re.search(r'COVERED:[^(]*\((\d+ of \d+)\)', neg)
ratio = m.group(1) if m else None
if not covered or not vs_list or not ratio:
    print("could not extract the coverage lists from check-negative-controls.sh")
    print("SCOPE 0"); sys.exit(1)

for f in ("AGENTS.md", "CONTRIBUTING.md"):
    try:
        text = flat(pathlib.Path(f).read_text(encoding="utf-8"))
    except OSError as e:
        print("cannot read %s: %s" % (f, e)); bad += 1; continue
    for label, want in (("part A invariant list", covered),
                        ("part A ratio", ratio),
                        ("part B check list", vs_list)):
        claims += 1
        if want not in text:
            bad += 1
            print("%s does not restate the harness's %s (%r)" % (f, label, want))

print("SCOPE %d" % claims)
sys.exit(1 if bad else 0)
DOCPY
  ) || v17=1
  n17=$(printf '%s\n' "$doc_out" | sed -n 's/^SCOPE //p')
  while IFS= read -r l; do
    case "$l" in SCOPE\ *|'') ;; *) note "$l" ;; esac
  done <<EOF
$doc_out
EOF
  scope "${n17:-0}" "documented count/coverage claims" || v17=1
  if [ "$v17" -eq 0 ]; then echo "    ok (${n17:-0} claims checked against the scripts)"; fi
else
  note "SKIPPED (python3 not found; CI always has it)"
  echo "    ok (skipped)"
fi
if [ "$v17" -ne 0 ]; then fail=1; fi

# --- 18. Section cross-references resolve ----------------------------------
# Invariant 8 resolves `[text](file.md)` links. It cannot see a `§` reference,
# because a `§` reference is PROSE, not a link — and the library carries ~1,300
# of them across skills/. They break silently: renumber a section, or split a
# rules file, and every citation of it still reads as a valid pointer while
# leading nowhere. Added 2026-08-20 immediately BEFORE splitting rules/10 and
# rules/11 for exactly that reason, and it found six live defects on its very
# first run over the unmodified tree (two dangling sections, four cross-skill
# refs that resolved to the wrong skill's rules/NN).
#
# Two conventions it had to learn the hard way, both found by reading the
# findings instead of trusting the count (`sota-code-security` rules/12 §2.2):
#   - a heading may number itself `## 3.` OR `## §3 ` — missing the second form
#     read one whole file as unnumbered and hid 102 valid references;
#   - `§N.M` means a `### N.M` heading in SOME files and "item M of the ordered
#     list in §N" in others. Both are legitimate; a checker that knows only the
#     first flags nine correct references. That is rules/12 §2.1's "generalised
#     from one sample", committed by this check's own first draft.
# It is deliberately FAIL-OPEN on ambiguity — a bare `rules/NN` is tried against
# every skill named on the line and against the containing skill, and any hit
# passes. A gate that flags correct prose gets disabled, which leaves you worse
# off than no gate (docs/CONVENTIONS-LEDGER.md).
echo "[18/18] Section references (§N) resolve to a real section"
v18=0
if command -v python3 >/dev/null 2>&1; then
  ref_out=$(python3 scripts/lib/check-section-refs.py 2>&1) || v18=1
  while IFS= read -r l; do
    case "$l" in SCOPE\ *|'') ;; *) note "$l" ;; esac
  done <<EOF
$ref_out
EOF
  n18=$(printf '%s\n' "$ref_out" | sed -n 's/^SCOPE //p')
  scope "${n18:-0}" "section references" || v18=1
  if [ "$v18" -eq 0 ]; then echo "    ok (${n18:-0} section references resolved)"; fi
else
  note "SKIPPED (python3 not found; CI always has it)"
  echo "    ok (skipped)"
fi
if [ "$v18" -ne 0 ]; then fail=1; fi

# --- Result ---------------------------------------------------------------
echo
if [ "$fail" -ne 0 ]; then
  echo "FAIL: repository invariants violated (see above)."
  exit 1
fi
printf 'PASS: all repository invariants satisfied (18 checks over %s skill files / %s rules files, %ss).\n' \
  "${seen1:-?}" "${seen2:-?}" "$((SECONDS - START_SECONDS))"
