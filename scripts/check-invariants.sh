#!/usr/bin/env bash
#
# Enforce SOTA-skills repository invariants. Run by pre-commit and CI.
# Exits non-zero (and prints offenders) if any invariant is violated.
#
# Invariants:
#   1. Every tracked *.md is <= 500 lines  (skills load incrementally).
#   2. Every skills/*/rules/*.md ends with an "## Audit checklist".
#   3. No internal/private references leak in (the library stays generic).
#
# Portable to macOS bash 3.2 (no mapfile/associative arrays).
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

MAX_LINES=500
fail=0
note() { printf '    %s\n' "$1"; }

# --- 1. Line budget -------------------------------------------------------
echo "[1/3] Markdown files <= ${MAX_LINES} lines"
over=0
while IFS= read -r f; do
  n=$(wc -l < "$f")
  if [ "$n" -gt "$MAX_LINES" ]; then
    note "OVER ${MAX_LINES} (${n} lines): $f"
    over=1
  fi
done < <(git ls-files '*.md')
if [ "$over" -eq 0 ]; then echo "    ok"; else fail=1; fi

# --- 2. Audit checklist in every rules file -------------------------------
echo "[2/3] Every skills/*/rules/*.md has an '## Audit checklist'"
missing=0
while IFS= read -r f; do
  if ! grep -qE '^## Audit checklist' "$f"; then
    note "MISSING '## Audit checklist': $f"
    missing=1
  fi
done < <(git ls-files 'skills/*/rules/*.md')
if [ "$missing" -eq 0 ]; then echo "    ok"; else fail=1; fi

# --- 3. No internal/private references -------------------------------------
# Keep the library generic and shareable. This guards against re-introducing
# the personal stack/project names that were scrubbed before going public.
echo "[3/3] No internal-name leaks"
DENY='Probably\.Group|dn-platform|dn-go-api|dn-fe|ContextIPS|AethelGard|Vuln-AID|JARVIS|\bMemex\b|the user runs|the user operates'
# This script necessarily contains the patterns above, so exclude it from its
# own scan (it is small and reviewed; everything else is checked).
hits=$(git ls-files -z -- ':(exclude)scripts/check-invariants.sh' \
       | xargs -0 grep -InE "$DENY" 2>/dev/null || true)
if [ -n "$hits" ]; then
  note "Internal reference(s) found — keep the library generic:"
  printf '%s\n' "$hits" | sed 's/^/      /'
  fail=1
else
  echo "    ok"
fi

# --- Result ---------------------------------------------------------------
echo
if [ "$fail" -ne 0 ]; then
  echo "FAIL: repository invariants violated (see above)."
  exit 1
fi
echo "PASS: all repository invariants satisfied."
