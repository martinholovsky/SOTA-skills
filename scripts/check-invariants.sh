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
#
# Portable to macOS bash 3.2 (no mapfile/associative arrays). Check 4 needs
# python3 for correct Unicode character counting; it is skipped with a warning
# if python3 is absent locally (CI runs on a runner that always has it).
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

MAX_LINES=500
MAX_DESC=1024
fail=0
note() { printf '    %s\n' "$1"; }

# --- 1. Line budget -------------------------------------------------------
echo "[1/4] Markdown files <= ${MAX_LINES} lines"
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
echo "[2/4] Every skills/*/rules/*.md ends with an '## Audit checklist'"
missing=0
while IFS= read -r f; do
  [ -f "$f" ] || { note "SKIPPED (tracked but missing from worktree): $f"; continue; }
  # The checklist must be the file's LAST '## ' heading (docs say "ends
  # with") — a mention inside a code fence or mid-file no longer satisfies.
  last_h2=$(grep -E '^## ' "$f" | tail -n 1 || true)
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
echo "[3/4] No internal-name leaks"
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
echo "[4/4] Every skills/*/SKILL.md description <= ${MAX_DESC} characters"
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

# --- Result ---------------------------------------------------------------
echo
if [ "$fail" -ne 0 ]; then
  echo "FAIL: repository invariants violated (see above)."
  exit 1
fi
echo "PASS: all repository invariants satisfied."
