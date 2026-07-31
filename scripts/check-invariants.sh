#!/usr/bin/env bash
#
# Enforce SOTA-skills repository invariants. Run by pre-commit and CI.
# Exits non-zero (and prints offenders) if any invariant is violated.
#
# Invariants:
#   1. Every tracked SKILL file (skills/*/*.md, skills/*/rules/*.md) is <= 500
#      lines, so skills load incrementally. Non-skill Markdown (README,
#      CHANGELOG, docs/) is deliberately uncapped — see the check itself.
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
# The cap is load-bearing ONLY for skill files: a rules/SKILL file over ~500
# lines defeats incremental loading (the whole point is that the model reads the
# rules that match the task, not a wall of text). Non-skill Markdown (README,
# CHANGELOG, docs/) is human/agent-facing prose, not loaded as a skill, so it is
# intentionally uncapped (decided 2026-07-15) — navigability there comes from a
# table of contents and docs/INDEX.md, not a line ceiling.
echo "[1/11] Skill Markdown (skills/**) <= ${MAX_LINES} lines"
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
echo "[2/11] Every skills/*/rules/*.md ends with an '## Audit checklist'"
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
echo "[3/11] No internal-name leaks"
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
echo "[4/11] Every skills/*/SKILL.md description <= ${MAX_DESC} characters"
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
echo "[5/11] Version lockstep (VERSION == plugin.json == CHANGELOG top; tag not ahead)"
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
echo "[6/11] Count-bearing surfaces match the tree"
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
echo "[7/11] Router lists every skill (routing table + library map)"
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
echo "[8/11] Internal Markdown links resolve (*.md targets)"
if command -v python3 >/dev/null 2>&1; then
  if link_out=$(python3 - <<'PY'
import os, re, sys
files = [l for l in os.popen("git ls-files '*.md'").read().splitlines() if l.strip()]
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
    echo "    ok"
  else
    printf '%s\n' "$link_out" | sed 's/^/    /'
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
echo "[9/11] CHANGELOG has at most one [Unreleased], and it is the top entry"
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
echo "[10/11] Every skills/*/rules/*.md is referenced by its own SKILL.md"
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
echo "[11/11] LAST-VERIFIED moves only with a sweep (batched diff, or declared in CHANGELOG)"
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
  if printf '%s\n' "$changed" | grep -qx 'LAST-VERIFIED'; then
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
  else
    echo "    ok (LAST-VERIFIED unchanged)"
  fi
fi
if [ "$v11" -ne 0 ]; then fail=1; fi

# --- Result ---------------------------------------------------------------
echo
if [ "$fail" -ne 0 ]; then
  echo "FAIL: repository invariants violated (see above)."
  exit 1
fi
printf 'PASS: all repository invariants satisfied (11 checks over %s skill files / %s rules files, %ss).\n' \
  "${seen1:-?}" "${seen2:-?}" "$((SECONDS - START_SECONDS))"
