#!/usr/bin/env bash
#
# Does `git grep -P` (PCRE) find EXACTLY what `git grep -E` (POSIX ERE) finds for the
# private-name denylist? Written 2026-09-23 to decide whether invariant 3 may switch
# engines: -P measured 20x faster locally (0.17s vs 3.6s), but the CI patterns live in a
# secret nobody can read back, and an ERE construct that means something else in PCRE
# would silently reopen the leak the gate exists to close.
#
# WHY HISTORY. On the current tree both engines match nothing, and two empty sets agree
# about nothing. The accepted-risk history (names scrubbed from the tree, still in old
# commits) is a corpus of REAL positives, so parity is tested where it can actually fail.
#
# NEVER PRINTS A MATCH. CI logs are public. Only counts and a digest of the match set
# (revision:path:line, no text) are printed.
#
# Exit: 0 parity (non-vacuous) · 1 mismatch or engine failure · 2 vacuous (no positives).
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1
# The generic phrases are READ from the gate, not restated: a copy here would drift, and
# spelling them out would trip the very check this tests (only the gate is exempt from it).
DENY=$(sed -n "s/^DENY='\(.*\)'\$/\1/p" scripts/check-invariants.sh | head -1)
[ -n "$DENY" ] || { echo "FAIL: could not read the generic DENY phrases from scripts/check-invariants.sh"; exit 1; }
if [ -n "${SOTA_DENYLIST:-}" ]; then
  DENY="$DENY|$SOTA_DENYLIST"; src="SOTA_DENYLIST"
elif [ -f .denylist.local ]; then
  DENY="$DENY|$(grep -vE '^[[:space:]]*(#|$)' .denylist.local | paste -sd'|' -)"; src=".denylist.local"
else
  echo "FAIL: no private denylist available (neither SOTA_DENYLIST nor .denylist.local)"; exit 1
fi
revs=$(git rev-list --all | wc -l | tr -d ' ')
echo "source: $src · alternatives: $(printf '%s' "$DENY" | tr '|' '\n' | grep -c .) · revisions: $revs"
[ "$revs" -gt 1 ] || { echo "FAIL: shallow history ($revs revision) — this test needs fetch-depth: 0"; exit 1; }

run() {  # <engine flag> <out file> -> sorted "rev:path:line" set in <out>, git's exit code in $RC
  # PIPESTATUS must be read HERE: after the function returns it holds only the call's own
  # status (measured: 0 in bash 5 and 3.2 for a pipeline whose first stage exited 2), which
  # would report every engine failure as "no matches".
  # shellcheck disable=SC2046
  git grep -iIn "$1" -e "$DENY" $(git rev-list --all) -- ':(exclude)scripts/check-invariants.sh' \
    ':(exclude)scripts/denylist-engine-parity.sh' 2>"$TMPE" | cut -d: -f1-3 | LC_ALL=C sort -u > "$2"
  RC=${PIPESTATUS[0]}
}
TMPE=$(mktemp); trap 'rm -f "$TMPE" "$TE" "$TP"' EXIT
TE=$(mktemp); TP=$(mktemp)
run -E "$TE"; rcE=$RC
run -P "$TP"; rcP=$RC; errP=$(cat "$TMPE")
nE=$(wc -l < "$TE" | tr -d ' '); nP=$(wc -l < "$TP" | tr -d ' ')
hE=$(shasum -a 256 < "$TE" 2>/dev/null || sha256sum < "$TE"); hP=$(shasum -a 256 < "$TP" 2>/dev/null || sha256sum < "$TP")
echo "ERE : rc=$rcE  matches=$nE  digest=${hE:0:16}"
echo "PCRE: rc=$rcP  matches=$nP  digest=${hP:0:16}"
# git grep: 0 = matched, 1 = no match, anything else = the engine or the pattern failed.
if [ "$rcE" -gt 1 ] || [ "$rcP" -gt 1 ]; then
  echo "FAIL: an engine errored (ERE rc=$rcE, PCRE rc=$rcP)."
  # stderr is NOT echoed: git quotes the -e pattern in its error, and the pattern is the
  # secret. The exit codes are the whole diagnosis a public log may carry.
  [ -n "$errP" ] && echo "  (PCRE wrote $(printf '%s' "$errP" | wc -l | tr -d ' ') stderr line(s); not printed — they quote the pattern)"
  exit 1
fi
if [ "$nE" -eq 0 ]; then
  echo "VACUOUS: ERE matched nothing across $revs revisions — parity of two empty sets proves nothing."
  exit 2
fi
if [ "$hE" = "$hP" ]; then
  echo "PARITY: identical match sets ($nE revision:path:line hits across $revs revisions)."
  exit 0
fi
echo "MISMATCH: ERE-only $(LC_ALL=C comm -23 "$TE" "$TP" | wc -l | tr -d ' '), PCRE-only $(LC_ALL=C comm -13 "$TE" "$TP" | wc -l | tr -d ' ') — do NOT switch engines."
exit 1
