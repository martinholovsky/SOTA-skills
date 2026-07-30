#!/usr/bin/env bash
#
# selfcheck.sh — prove this fixture still has the four properties it exists to test.
#
# A fixture that quietly loses its planted behaviour measures nothing while still
# printing a score: exactly the failure class it is built to detect. So each
# property is re-derived here by mutation, in a scratch copy, against the real
# suite — never asserted from the file contents.
#
# Run: bash evals/cases/dead-path/selfcheck.sh      (exit 0 = fixture intact)
set -euo pipefail

SRC="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
fail=0

suite() {  # <dir> -> 0 if the suite passes
  (cd "$1" && python3 -m unittest discover -s tests -t . -q >/dev/null 2>&1)
}

fresh() {  # <name> -> path to a clean copy
  local d="$WORK/$1"
  rm -rf "$d"; mkdir -p "$d"
  cp -R "$SRC/ledger" "$SRC/tests" "$d/"
  find "$d" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
  printf '%s' "$d"
}

expect() {  # <label> <expected pass|fail> <dir>
  local label="$1" want="$2" dir="$3" got
  if suite "$dir"; then got=pass; else got=fail; fi
  if [ "$got" = "$want" ]; then
    printf '  ok   %-34s suite %s (as designed)\n' "$label" "$got"
  else
    printf '  FAIL %-34s suite %s, expected %s\n' "$label" "$got" "$want"
    fail=1
  fi
}

echo "dead-path fixture selfcheck"

# 0. Baseline: an unmutated copy must pass, or every result below is meaningless.
expect "baseline" pass "$(fresh base)"

# 1. csv_export LOOKS unused (no static import; named only as a config string)
#    but is resolved at runtime -> removing it must BREAK the suite.
d=$(fresh d1); rm "$d/ledger/exporters/csv_export.py"
expect "delete csv_export (looks unused)" fail "$d"

# 2. xml_export LOOKS used (statically imported, referenced in a branch) but the
#    branch cannot execute -> removing it AND its dead reference must keep green.
d=$(fresh d2); rm "$d/ledger/exporters/xml_export.py"
python3 - "$d" <<'PY'
import re, sys, pathlib
p = pathlib.Path(sys.argv[1], "ledger", "app.py")
s = p.read_text()
s = s.replace("from ledger.exporters import xml_export\n", "")
s = re.sub(r"\n    if entries and entries\[0\]\[.source.\] == Source\.LEGACY_BATCH:\n"
           r"        return xml_export\.render\(entries\)\n", "\n", s)
p.write_text(s)
PY
expect "delete xml_export + dead branch" pass "$d"

# 3. check_currency LOOKS untested (no test names it) but is exercised through
#    ingest -> no-op'ing it must BREAK the suite. The finding here is REFUTED.
d=$(fresh c1)
python3 - "$d" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1], "ledger", "controls.py")
s = p.read_text()
s = s.replace('    if code not in ("EUR", "GBP", "USD"):\n'
              '        raise RejectedEntry(f"unsupported currency: {code}")\n', "")
p.write_text(s)
PY
expect "no-op check_currency" fail "$d"

# 4. validate_amount LOOKS enforced (called on the ingest path) but its boolean
#    is discarded -> no-op'ing it must leave the suite green. Real finding.
d=$(fresh c2)
python3 - "$d" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1], "ledger", "controls.py")
s = p.read_text()
s = s.replace("    return isinstance(amount, int) and 0 < amount <= limit",
              "    return True")
p.write_text(s)
PY
expect "no-op validate_amount" pass "$d"

# 5. The mechanism behind 4, demonstrated rather than inferred: an amount far
#    over the configured limit must still post, because the boolean is ignored.
d=$(fresh c2b)
if (cd "$d" && python3 -c "
from ledger import app
e = app.ingest({'ref':'R-9','amount':10**9,'currency':'EUR'})
raise SystemExit(0 if e['amount'] == 10**9 else 1)
" >/dev/null 2>&1); then
  printf '  ok   %-34s over-limit entry posts (as designed)\n' "validate_amount is bypassable"
else
  printf '  FAIL %-34s over-limit entry did NOT post\n' "validate_amount is bypassable"
  fail=1
fi

echo
if [ "$fail" -ne 0 ]; then
  echo "FAIL: the fixture no longer has the properties it tests for."
  exit 1
fi
echo "PASS: fixture intact (6 properties re-derived by mutation)."
