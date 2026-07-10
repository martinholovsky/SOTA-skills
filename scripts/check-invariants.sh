#!/usr/bin/env bash
#
# Enforce SOTA-skills repository invariants. Run by pre-commit and CI.
# Exits non-zero (and prints offenders) if any invariant is violated.
#
# Invariants:
#   1. Every tracked *.md is <= 500 lines  (skills load incrementally).
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
#
# Portable to macOS bash 3.2 (no mapfile/associative arrays). Check 4 needs
# python3 for correct Unicode character counting; it is skipped with a warning
# if python3 is absent locally (CI runs on a runner that always has it).
# Check 5's tag comparison is skipped with a note when no v* tags are visible
# (e.g. a shallow CI checkout without tags).
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

MAX_LINES=500
MAX_DESC=1024
fail=0
note() { printf '    %s\n' "$1"; }

# --- 1. Line budget -------------------------------------------------------
echo "[1/7] Markdown files <= ${MAX_LINES} lines"
over=0
while IFS= read -r f; do
  [ -f "$f" ] || { note "SKIPPED (tracked but missing from worktree): $f"; continue; }
  # awk NR, not `wc -l`: counts a final line without trailing newline too.
  n=$(awk 'END{print NR}' "$f")
  if [ "$n" -gt "$MAX_LINES" ]; then
    note "OVER ${MAX_LINES} (${n} lines): $f"
    over=1
  fi
done < <(git ls-files '*.md')
if [ "$over" -eq 0 ]; then echo "    ok"; else fail=1; fi

# --- 2. Audit checklist ends every rules file ------------------------------
echo "[2/7] Every skills/*/rules/*.md ends with an '## Audit checklist'"
missing=0
while IFS= read -r f; do
  [ -f "$f" ] || { note "SKIPPED (tracked but missing from worktree): $f"; continue; }
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
if [ "$missing" -eq 0 ]; then echo "    ok"; else fail=1; fi

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
echo "[3/7] No internal-name leaks"
DENY='the user runs|the user operates'
if [ -n "${SOTA_DENYLIST:-}" ]; then
  DENY="$DENY|$SOTA_DENYLIST"
elif [ -f .denylist.local ]; then
  extra=$(grep -vE '^[[:space:]]*(#|$)' .denylist.local | paste -sd'|' - || true)
  [ -n "$extra" ] && DENY="$DENY|$extra"
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
echo "[4/7] Every skills/*/SKILL.md description <= ${MAX_DESC} characters"
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
for f in sorted(glob.glob('skills/*/SKILL.md')):
    d, err = get_desc(open(f, encoding='utf-8').read())
    if not d:
        print(f"MISSING/EMPTY description: {f}"); bad = 1; continue
    if err:
        print(f"{err}: {f}"); bad = 1
    if len(d) > cap:
        print(f"OVER {cap} ({len(d)} chars): {f}"); bad = 1
sys.exit(1 if bad else 0)
PY
  ); then
    echo "    ok"
  else
    printf '%s\n' "$desc_out" | sed 's/^/    /'
    fail=1
  fi
else
  note "SKIPPED: python3 not found (CI enforces this check)"
fi

# --- 5. Version lockstep ----------------------------------------------------
# One version, four places: VERSION, plugin.json, the CHANGELOG's top entry,
# and (after the release lands) the newest v* tag. Drift here shipped a main
# briefly claiming 1.8.0 with 1.9.0 content (2026-07-03) — hence a hard check.
echo "[5/7] Version lockstep (VERSION == plugin.json == CHANGELOG top; tag not ahead)"
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
echo "[6/7] Count-bearing surfaces match the tree"
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
echo "[7/7] Router lists every skill (routing table + library map)"
v7=0
router=skills/sota/SKILL.md
bt='`'
for d in skills/sota-*/; do
  name=$(basename "$d")
  grep -qE "^\| ${bt}${name}${bt} " "$router" || { note "routing table missing: $name"; v7=1; }
  grep -qF "**${name}/rules**" "$router" || { note "library map missing: $name"; v7=1; }
done
while IFS= read -r name; do
  [ -d "skills/$name" ] || { note "library map names a non-existent skill: $name"; v7=1; }
done < <(grep -oE '\*\*sota-[a-z-]+/rules\*\*' "$router" | sed 's/\*\*//g; s#/rules##')
if [ "$v7" -eq 0 ]; then echo "    ok"; else fail=1; fi

# --- Result ---------------------------------------------------------------
echo
if [ "$fail" -ne 0 ]; then
  echo "FAIL: repository invariants violated (see above)."
  exit 1
fi
echo "PASS: all repository invariants satisfied."
