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
#      spec: loaders skip a skill whose description exceeds the cap).
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
  n=$(wc -l < "$f")
  if [ "$n" -gt "$MAX_LINES" ]; then
    note "OVER ${MAX_LINES} (${n} lines): $f"
    over=1
  fi
done < <(git ls-files '*.md')
if [ "$over" -eq 0 ]; then echo "    ok"; else fail=1; fi

# --- 2. Audit checklist in every rules file -------------------------------
echo "[2/4] Every skills/*/rules/*.md has an '## Audit checklist'"
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
echo "[3/4] No internal-name leaks"
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
    m = re.match(r'---\n(.*?)\n---', text, re.S)
    if not m:
        return None
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
                return ' '.join(x for x in buf if x)
            return rest.strip('\'"')             # plain / quoted single line
    return None
for f in sorted(glob.glob('skills/*/SKILL.md')):
    d = get_desc(open(f, encoding='utf-8').read())
    if not d:
        print(f"MISSING/EMPTY description: {f}"); bad = 1; continue
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
