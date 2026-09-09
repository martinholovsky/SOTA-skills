#!/usr/bin/env bash
#
# Negative controls — proof our own gates can still FAIL.
#
# Two subjects: scripts/check-invariants.sh (part A) and scripts/verify-setup.sh
# (part B). One script, one CI job, one bar.
#
# WHY THIS EXISTS. check-invariants.sh prints "ok" fifteen times on a clean tree.
# So does a check whose pathspec drifted, whose predicate stopped matching, or
# that was quietly disabled. Those states are typographically identical, and this
# repo's own library calls that an inert control: `sota-code-security` rules/12 §1
# mutation-probes every control. `sota-code-security` rules/15 §2.2 requires that an
# instrument carry a known-bad it must reject and a known-good it must pass.
# `sota-devsecops` rules/09 §1, which
# says outright that no mainstream framework requires evidence a gate CAN fail.
# We required that of everyone else and did not do it here. This closes that.
#
# WHAT IT DOES. For each mutation below: apply a known-bad to a disposable copy of
# the tree, run the gate, and require BOTH
#   (a) a non-zero exit, and
#   (b) the EXPECTED check to be the one that complained.
# (b) is not pedantry. A harness that accepts any non-zero exit reports "18/18
# controls caught" while every run dies before the thing under test (rules/15
# §2.1, "the instrument that cannot fail"). A mutation caught for the wrong reason
# is a FALSE PASS and is reported as one.
#
# POSITIVE CONTROL FIRST. The unmutated copy must exit 0. If it does not, the
# harness is measuring nothing and aborts rather than reporting results — a
# known-bad that "fails" in a tree that already fails proves nothing.
#
# ASSERT THE MUTATION TOOK. The copy is a git worktree at HEAD, so it would carry
# the COMMITTED gate, not the one being edited. The working-tree gate is copied in
# and byte-compared, because "the code you changed may not be the code that ran"
# is the trap rules/15 §2.2 names explicitly.
#
# Scope: invariants 1, 2, 6, 10 and 15 — the five with a cheap, unambiguous
# known-bad. The others are diff-, history- or release-shaped and need a fixture
# with real commits; they are NOT covered, and this script says so rather than
# implying whole-gate coverage.
#
# Portable to macOS bash 3.2 (no associative arrays).
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
REPO=$(pwd)
GATE=scripts/check-invariants.sh
[ -f "$GATE" ] || { echo "FAIL: $GATE not found"; exit 1; }

WT=$(mktemp -d)/wt
# REPORTED, NEVER GATED. This runs on EXIT, so a non-zero here would overwrite the
# harness's real exit code — and the whole point of this script is that a non-zero for
# any reason other than the intended check is a FALSE PASS. Same stance as
# `evals/_elapsed.py`: it reports, it never decides. Also `docs/CONVENTIONS-LEDGER.md` —
# a flaky gate gets disabled and leaves you worse off than no gate.
#
# The `|| true` here used to swallow the failure while `rm -rf` deleted the directory
# anyway, which orphans the worktree REGISTRATION: `git worktree list` then shows a
# `prunable` entry forever, and success and failure of this cleanup were
# indistinguishable — `sota-code-security` rules/10 §2.4, in the one script whose job is
# proving that failures surface. Found 2026-09-03 with two orphans already registered
# (concurrent runs against one repo are the likely trigger). `git gc` does prune them,
# but only at `gc.worktreePruneExpire`, which defaults to 3 months — that grace is why
# this went unnoticed, not why it was fine.
cleanup() {
  git worktree remove --force "$WT" >/dev/null 2>&1 \
    || echo "  warn: could not remove worktree $WT — pruning its registration" >&2
  rm -rf "$(dirname "$WT")"
  git worktree prune                 # the rm above orphans the registration otherwise
}
trap cleanup EXIT

echo "Negative controls for $GATE"
echo "  disposable worktree: $WT"
git worktree add --detach "$WT" HEAD >/dev/null 2>&1 || {
  echo "FAIL: could not create a worktree (need a clean git repo)"; exit 1; }

# The worktree is at HEAD; test the gate we HAVE, not the gate we shipped.
cp "$REPO/$GATE" "$WT/$GATE"
cmp -s "$REPO/$GATE" "$WT/$GATE" || { echo "FAIL: gate copy did not take"; exit 1; }

# One gate run per probe: capture output AND status together. Running it twice
# doubles a ~10s check and invites the two runs to disagree.
GATE_OUT=""
GATE_RC=0
run_gate() {
  GATE_RC=0
  GATE_OUT=$( cd "$WT" && bash "./$GATE" 2>&1 ) || GATE_RC=$?
}

# --- positive control -----------------------------------------------------
printf '  [positive control] clean copy must PASS ... '
run_gate
if [ "$GATE_RC" -eq 0 ]; then
  echo "ok"
else
  echo "FAIL"
  echo
  echo "The unmutated copy does not pass. Every result below would be meaningless,"
  echo "so nothing was run. Fix the tree (or the gate) first:"
  printf '%s\n' "$GATE_OUT" | tail -20
  exit 1
fi

# --- mutations ------------------------------------------------------------
# Each entry: id | human name | mutate fn | expected substring in the gate output.
tested=0
caught=0
failed=0

# `git checkout -- .` + `git clean -fd` is NOT enough: git clean leaves files that
# have been `git add`-ed, so probe 10's staged file leaked into probe 15, which
# then failed on check 6 (file count 299) instead of check 15. The (b) assertion
# reported that as a FALSE PASS on the first run of this harness — which is the
# whole reason (b) is there. `git reset --hard` clears the index too; it also
# reverts the gate we deliberately copied in, so the copy is redone and re-verified.
restore() {
  # No `|| true`: a failed reset leaks the previous mutation into the next probe,
  # which would then measure the wrong thing (found 2026-08-16).
  ( cd "$WT" && git reset -q --hard HEAD && git clean -fdq ) >/dev/null 2>&1 \
    || { echo "FATAL: could not restore the probe worktree — later probes would be"; \
         echo "       contaminated by the previous mutation."; exit 1; }
  cp "$REPO/$GATE" "$WT/$GATE"
  cmp -s "$REPO/$GATE" "$WT/$GATE" || { echo "FAIL: gate copy did not survive restore"; exit 1; }
}

probe() {  # <id> <name> <expected substring>   — mutation already applied
  local id="$1" name="$2" want="$3"
  tested=$((tested + 1))
  # ASSERT THE MUTATION TOOK (added 2026-08-16). Every mutation below is a hardcoded
  # literal — a count, a phrase, a path. When one goes stale the edit is a silent
  # no-op, the gate correctly passes, and this harness then reports "NOT CAUGHT:
  # INERT", accusing a healthy gate. A stale probe must fail as a PROBE, loudly.
  if git -C "$WT" diff --quiet && [ -z "$(git -C "$WT" status --porcelain)" ]; then
    echo "  [$id] $name — PROBE BROKEN: the mutation changed nothing (stale literal?)."
    echo "        This is a defect in the probe, not evidence about the gate."
    failed=$((failed + 1))
    restore
    return
  fi
  run_gate
  if [ "$GATE_RC" -eq 0 ]; then
    echo "  [$id] $name — NOT CAUGHT: the gate still passed. This check is INERT."
    failed=$((failed + 1))
  # NO PIPE. This was `printf ... | grep -qF -- "$want"`, and on 2026-09-06 it
  # reported probe 4 as a FALSE PASS while its own diagnostic line below printed the
  # expected string out of the SAME variable -- a self-contradiction that can only come
  # from the pipeline, not the content. It reproduced only on the CI runner (ubuntu,
  # bash 5, GNU grep); 29/29 passed on macOS bash 3.2 in the same commit, and a 400 KB
  # synthetic case would not reproduce it locally, so the precise signal is NOT
  # established. `grep -q` exits the moment it matches, which is the shape
  # check-invariants.sh's own header warns about ("never grep -m 1/head on a pipe in
  # here") and the likeliest cause under `pipefail`.
  #
  # The fix does not depend on knowing which: a bash glob match has no pipe, no
  # subprocess and no grep dialect, so the comparison can no longer fail for any reason
  # other than the content. AN INSTRUMENT THAT CAN ACCUSE A HEALTHY GATE IS WORSE THAN
  # NO INSTRUMENT -- this harness exists to find exactly that, in everything but itself.
  elif case "$GATE_OUT" in (*"$want"*) true ;; (*) false ;; esac; then
    echo "  [$id] $name — caught"
    caught=$((caught + 1))
  else
    echo "  [$id] $name — FALSE PASS: gate failed, but not for this reason."
    echo "        expected to see: $want"
    printf '%s\n' "$GATE_OUT" | grep -E '^ +[A-Z]' | head -3 | sed 's/^ */        got: /'
    failed=$((failed + 1))
  fi
  restore
}

# 1 — line budget: a rules file over the 500-line cap.
target="skills/sota-code-security/rules/12-verifying-the-verifier.md"
( cd "$WT" && awk 'BEGIN{for(i=0;i<600;i++) print "padding line to breach the cap"}' >> "$target" )
probe 1 "line budget (rules file over 500 lines)" "OVER 500"

# 2 — every rules file ends with an Audit checklist.
( cd "$WT" && perl -0pi -e 's/^## Audit checklist$/## Not A Checklist/m' "$target" )
probe 2 "audit checklist missing from a rules file" "MISSING/NOT-LAST '## Audit checklist'"

# 6 — count-bearing surfaces match the tree.
# The mutation is count-AGNOSTIC: it matches whatever numbers the README currently
# carries and rewrites only the file count. A hardcoded literal here went stale twice
# (298 -> 300 when rules/13 and rules/14 landed, 2026-08-20; 300 -> 301 when
# sota/rules/02 landed, 2026-08-26), each time costing a red CI run that said PROBE
# BROKEN. That assertion did its job both times — it never accused the healthy gate —
# but the staleness added no signal invariant 6 doesn't already give, since a changed
# count fails invariant 6 first. The regex still asserts it landed, so a change to the
# hero SENTENCE (not its numbers) is still reported as a broken probe.
( cd "$WT" && perl -0pi -e 's/\*\*(\d+) skills \(\d+ files/**$1 skills (999 files/' README.md )
probe 6 "README file count drifted from the tree" "README hero file count"

# 10 — a rules file its own SKILL.md never indexes.
( cd "$WT" && cp "$target" "skills/sota-code-security/rules/99-unindexed-probe.md" \
    && git add -A >/dev/null 2>&1 )
probe 10 "rules file not referenced by its own SKILL.md" "not referenced in"

# 15 — the library map omits a rules file that exists. The map moved out of the router
# into sota/rules/04 (2026-09-02); this probe moved with it, which is the point of a
# probe asserting its own mutation landed rather than trusting a hardcoded literal.
( cd "$WT" && perl -0pi -e 's/10 silent control failure, 11 dead-path diagnostics, /10 silent control failure, /' skills/sota/rules/04-library-map.md )
probe 15 "library map omits an existing rules file" "map missing:"

# 16 — README documents a hook install.sh does not write (the 2026-08-05 defect).
( cd "$WT" && perl -0pi -e 's/\(3\) ROUTE BEFORE YOU ACT/(3) route whenever/' README.md )
probe 16 "README's documented hook drifted from HOOK_CMD" "README documents a hook install.sh does not write."

# --- Added 2026-08-16 -------------------------------------------------------
# These five invariants were previously unprobed AND (3, 4, 7) not even declared
# uncovered. All five are single-file edits, so the old rationale ("diff-, history-
# or release-shaped") never applied to them. Probe 3 deliberately uses a GENERIC
# phrase: the worktree is `git worktree add HEAD`, so the untracked .denylist.local
# is absent and only the built-in patterns are active locally.

# 3 — an internal-name leak (generic phrase, always in DENY).
# Build the phrase at runtime: writing it literally here would make THIS file trip
# check 3 (it did, on the first attempt — the gate caught its own probe).
deny_word=user
( cd "$WT" && printf '\nNote: the %s runs a private cluster.\n' "$deny_word" >> README.md )
probe 3 "internal-name leak in a tracked file" "Internal reference(s) found"

# 4 — a SKILL.md description pushed over the 1024-char cap.
( cd "$WT" && perl -0pi -e 's/(\nname: sota-golang\ndescription: )/$1PADDING. /' skills/sota-golang/SKILL.md   && perl -0pi -e 's/(\ndescription: PADDING\. )/$1 . ("filler text to breach the description cap. " x 25)/e' skills/sota-golang/SKILL.md )
probe 4 "SKILL.md description over the 1024-char cap" "OVER 1024"

# 7 — a skill missing from the router's routing table.
( cd "$WT" && perl -ni -e 'print unless /^\| `sota-golang` \|/' skills/sota/SKILL.md )
probe 7 "skill missing from the router routing table" "routing table missing:"

# 8 — a relative link to a *.md target that does not resolve.
( cd "$WT" && printf '\nSee [the missing page](docs/NO-SUCH-FILE-HERE.md).\n' >> README.md )
probe 8 "internal markdown link does not resolve" "BROKEN LINK"

# 13 — a scoreboard row with an empty Samples cell.
( cd "$WT" && perl -pi -e 's/\| 2 runs × 3, temp 0\.7 \|/|  |/ if /\*\*Completeness\*\* \(7 build tasks\)/' evals/results/RESULTS.md )
probe 13 "scoreboard row with no sample size" "NO SAMPLE SIZE:"

# 17 — a document that describes the checks, disagreeing with them. This is the
# shape that shipped twice: AGENTS.md kept its old count while the script grew.
# The mutation is DERIVED (decrement whatever count is there) rather than hardcoded.
# Every other probe pins a literal on purpose — but this one's literal is the
# invariant count, so it goes stale on every single check added: it did so twice on
# 2026-08-20 alone, and each time the landed-assertion caught it as PROBE BROKEN
# rather than as a defect. Deriving removes the recurring cost; the landed assertion
# still fires if the substitution matches nothing. The expected substring is likewise
# trimmed to the part that does not move.
( cd "$WT" && perl -pi -e 's/runs \*\*(\d+) checks\*\*/"runs **" . ($1 - 1) . " checks**"/e' AGENTS.md )
probe 17 "a doc's invariant count disagrees with the script" "but check-invariants.sh has"

# 18 — a `§` reference left dangling by a renumbered section. This is the split
# hazard the check was built for: rename one heading and every citation of it
# across every skill still reads as a valid pointer. The mutation targets a
# section cited from ANOTHER skill on purpose — a same-file rename would be
# caught by eye, a cross-skill one never is.
( cd "$WT" && perl -pi -e 's/^## 1b\. Where the probe lives/## 1z. Where the probe lives/' \
     skills/sota-code-security/rules/12-verifying-the-verifier.md )
probe 18 "a section reference dangles after a renumber" "resolves nowhere"

# 19 — silencing the coverage check by EXEMPTING a check instead of probing it.
# That is the one-line move invariant 19's pin exists to stop, so it is the half
# worth probing: the other half (a check with no known-bad at all) demonstrated
# itself on introduction, when 19 flagged 19.
( cd "$WT" && perl -pi -e 's/^(\s*echo "\s+)12(\s+— mtime-based)/${1}12, 18${2}/' \
     scripts/check-negative-controls.sh )
probe 19 "a check is exempted rather than probed" "GREW by"

# 20 — §AUDIT drifting away from the rules files that hold its procedure. The pin is
# the forcing function to re-read sota/rules/01 §5; mutate the section and the pin must
# be the thing that complains. Mutating a HEADING would also trip invariant 18, so the
# edit is inside a pass's prose where only the hash can see it.
( cd "$WT" && perl -pi -e 's/^1\. \*\*Recon\.\*\* Inventory/1. **Recon.** Enumerate/' \
     skills/sota/SKILL.md )
probe 20 "router §AUDIT changed without the pin being re-read" "AUDIT DRIFT"

# 21 — a CHANGELOG version that shipped and never got a tag. Inserted BELOW the top
# entry on purpose: the top one is legitimately untagged on a release PR, so a probe
# that mutated it would prove nothing. The worktree shares the repo's .git, so
# `git tag -l` sees the real tags there and the check does not skip.
# Insert before the SECOND '## [' — i.e. BELOW the top entry. A first draft inserted before
# the FIRST one, which made 9.9.9 the top entry; invariant 5 then complained about the top
# entry instead, and the harness correctly reported FALSE PASS rather than crediting the catch.
( cd "$WT" && perl -0pi -e 's/(\n## \[[0-9])/++$n==2 ? "\n## [9.9.9] - 2026-01-01\n\nA version that shipped without a tag.\n$1" : $1/ge' CHANGELOG.md )
probe 21 "a CHANGELOG version was never tagged" "NO TAG for CHANGELOG version"


# 22 — a checklist bullet stranded inside a code fence. The real defect (PR #226,
# found 2026-09-05) put two of them in THIS file's §2.2 example output, where they
# rendered as gate output for three weeks. The mutation reproduces that exactly:
# one bullet inserted into the fenced sample, flush-left, where a diff reader's eye
# reads it as another line of the example.
( cd "$WT" && perl -pi -e "s{^(\[2/10\] Every skills/\*/rules/\*\.md ends with an .## Audit checklist.\n)}{\$1- [ ] a checklist bullet nobody will read\n}" \
     skills/sota-code-security/rules/11-dead-path-diagnostics.md )
probe 22 "checklist bullet stranded inside a code fence" "CHECKLIST BULLET INSIDE A CODE FENCE"

# 23 — a CHANGELOG version heading whose link ref was never added. This is the real
# defect verbatim: 1.31.2, 1.32.0, 1.32.1 and 1.32.2 all shipped this way and were
# found by hand at the v1.32.3 cut. Targets a version BELOW the top entry and touches
# only the reference block, so no heading moves and invariants 5, 9 and 21 stay quiet —
# the (b) assertion would report a FALSE PASS otherwise.
( cd "$WT" && perl -0pi -e 's/^\[1\.32\.0\]: .*\n//m' CHANGELOG.md )
probe 23 "a CHANGELOG version heading has no link ref" "NO LINK REF for CHANGELOG version"

# 24 — AGENTS.md over its own 200-line target. The real defect twice over: 201 on
# 2026-09-05 and 202 on 2026-09-06, each time from adding an invariant's table row,
# each time caught only by a hand-run `awk`. Appends to a file no other check reads
# for length, so nothing else can complain first.
( cd "$WT" && printf 'padding to breach the always-loaded cap\n' >> AGENTS.md )
probe 24 "AGENTS.md over its own 200-line target" "it must stay UNDER 200"

# 24b — the cap's PREMISE, not its arithmetic (rules/10 §1's proxy question). The
# 200 only matters because CLAUDE.md/GEMINI.md symlink here and the file therefore
# loads every session. Replace the symlink with a copy and the cap still passes while
# guarding something nobody loads. Uses python3 for the unlink+copy so the mutation is
# a single, assertable step.
( cd "$WT" && python3 -c "import os,shutil; os.remove('CLAUDE.md'); shutil.copy('AGENTS.md','CLAUDE.md')" \
    && git add CLAUDE.md >/dev/null 2>&1 )
probe 24b "CLAUDE.md is a copy, not a symlink to AGENTS.md" "not a symlink (120000)"

# 25 — a newly added eval flag that never reaches evals/README.md. This is
# --no-gate-arm's own defect, replayed: it shipped in v1.33.0 documented in the root
# README and in --help, and not in the harness's front door.
( cd "$WT" && perl -pi -e 's/^(    ap\.add_argument\("--out", default=None\))/    ap.add_argument("--brand-new-undocumented", action="store_true")\n$1/' evals/run-completeness.py )
probe 25 "a new eval flag is undocumented in evals/README.md" "undocumented eval flags rose to"

# 25b — ROADMAP 41's half: a whole new RUNNER that never reaches evals/README.md.
# The flag probe above cannot catch this and that is the point: the runner it replays
# (run-routing-recall.py) shipped six flags whose names were already in the file from
# other runners, so the undocumented count did not move by one. Named `.py` under
# evals/ because that is the scan's own denominator; the string is chosen so no
# substring of it appears in the README.
( cd "$WT" && printf '#!/usr/bin/env python3\n"""probe."""\n' > evals/run-zzz-probe-unnamed.py )
probe 25b "a whole new eval runner is not named in evals/README.md" "are not named in evals/README.md"
rm -f "$WT/evals/run-zzz-probe-unnamed.py"

# 26 — the drift that actually happened, three times in one session: the priorities
# table left pointing at an item its own ledger had closed. Mutate the TABLE, not the
# ledger, so the probe exercises the arm that failed in the field rather than the
# easiest one to break (an off-by-one in the header would also fire, on a different
# arm). Uses the highest ledger number + 1, which is guaranteed absent from the open
# list and from every row, so the probe cannot accidentally name a real open item.
( cd "$WT" && python3 - <<'MUT'
import re, pathlib
p = pathlib.Path("docs/ROADMAP.md"); t = p.read_text()
nums = [int(x) for x in re.findall(r'(?m)^\|\s*(\d+)\s*\|', t)]
ghost = max(nums) + 1
t = re.sub(r'(?m)^(\| \*\*1\*\* \| )\*\*', r'\g<1>**Item %d — ' % ghost, t, count=1)
p.write_text(t)
MUT
git add docs/ROADMAP.md >/dev/null 2>&1 )
probe 26 "priorities table cites an item that is not open" "priorities table points at item"

# 27 — a deferral marker with no revisit condition. Mutates the whole CELL, not a
# prefix of it: a first attempt replaced only the opening words, the rest of the cell
# still carried "revisit", and the probe reported a catch that never happened. Asserts
# the cell actually changed before running, per rules/11 §2.5.
( cd "$WT" && python3 - <<'MUT'
import re, pathlib
p = pathlib.Path("docs/ADOPTION-LOG.md"); lines = p.read_text().splitlines()
i = next(i for i, l in enumerate(lines)
         if re.search(r'(?:^|\|)\s*(?:-\s+)?\*\*DEFERRED\s+—', l) and '|' in l)
cells = lines[i].split('|')
j = next(j for j, c in enumerate(cells) if 'DEFERRED' in c)
assert 'revisit' in cells[j] or 'once' in cells[j], "fixture drift: cell had no trigger to remove"
cells[j] = " **DEFERRED — parked** "
lines[i] = '|'.join(cells)
p.write_text("\n".join(lines) + "\n")
MUT
git add docs/ADOPTION-LOG.md >/dev/null 2>&1 )
probe 27 "a deferral with no revisit trigger" "names no revisit trigger"

# 28 — an eval case set that never says how its cases were chosen. This is
# prompt-independence.jsonl's own defect replayed: the rule lived in the results doc
# and not in the case file, in the set backing the +0.509 headline.
( cd "$WT" && perl -pi -e 's/SELECTION RULE/how it was built/ if $. < 40' evals/cases/desc-routing-regressions.jsonl \
    && git add evals/cases/desc-routing-regressions.jsonl >/dev/null 2>&1 )
probe 28 "an eval case set declares no SELECTION RULE" "no 'SELECTION RULE' comment"

# --- probes for a DIFF-BASED check --------------------------------------------
# Checks 11, 14 and 29 read `git diff <merge-base>...HEAD`, so a mutation in the
# working tree is invisible to them: they see a clean HEAD and correctly report "not
# a release commit". 11 and 14 sat unprobed for that reason, declared as "needs state
# a worktree lacks" — and that reason was WRONG, which is why writing 29's probe had
# to close them too. A worktree does not lack a merge base; it lacks a COMMIT, and
# this harness can make one, on a detached HEAD that nothing references and `cleanup`
# throws away with the worktree. EXPECTED_UNPROBED drops 11 and 14 in the same change
# (invariant 19 fails on a pin that still exempts a check now probed).
#
# It needs its own probe function for two reasons, and neither is a relaxation:
#   - `probe`'s mutation-took assertion is `git status --porcelain` non-empty, which a
#     committed mutation clears. This asserts HEAD MOVED and that the commit touched
#     files — strictly more than a dirty tree.
#   - `restore`'s `git reset --hard HEAD` would preserve the probe commit, leaking it
#     into every later probe. This resets to the ORIGINAL sha, captured before any.
WT_ORIG=$(git -C "$WT" rev-parse HEAD)
wt_commit() {  # <message> — commit whatever the caller staged/changed
  ( cd "$WT" && git add -A >/dev/null 2>&1 \
      && git -c user.email=probe@invalid -c user.name="negative control" \
             commit -q -m "$1" ) \
    || { echo "FATAL: probe commit failed — the diff-based probes below would be inert."; exit 1; }
}
probe_committed() {  # <id> <name> <expected substring>  — commit already made
  local id="$1" name="$2" want="$3"
  tested=$((tested + 1))
  local head; head=$(git -C "$WT" rev-parse HEAD)
  if [ "$head" = "$WT_ORIG" ] || [ -z "$(git -C "$WT" diff --name-only "$WT_ORIG" "$head")" ]; then
    echo "  [$id] $name — PROBE BROKEN: no commit landed on top of the worktree HEAD."
    echo "        This is a defect in the probe, not evidence about the gate."
    failed=$((failed + 1))
  else
    run_gate
    if [ "$GATE_RC" -eq 0 ]; then
      echo "  [$id] $name — NOT CAUGHT: the gate still passed. This check is INERT."
      failed=$((failed + 1))
    elif case "$GATE_OUT" in (*"$want"*) true ;; (*) false ;; esac; then
      echo "  [$id] $name — caught"
      caught=$((caught + 1))
    else
      echo "  [$id] $name — FALSE PASS: gate failed, but not for this reason."
      echo "        expected to see: $want"
      printf '%s\n' "$GATE_OUT" | grep -E '^ +[A-Z]' | head -3 | sed 's/^ */        got: /'
      failed=$((failed + 1))
    fi
  fi
  ( cd "$WT" && git reset -q --hard "$WT_ORIG" && git clean -fdq ) >/dev/null 2>&1 \
    || { echo "FATAL: could not rewind the probe worktree to $WT_ORIG."; exit 1; }
  cp "$REPO/$GATE" "$WT/$GATE"
  cmp -s "$REPO/$GATE" "$WT/$GATE" || { echo "FAIL: gate copy did not survive rewind"; exit 1; }
}

# 29 — a release that edits a skill description and declares no routing check. This
# is v1.35.0's own defect replayed: sota-skill-security shipped a description carrying
# "instruction file" twice, took r1_token_count's traffic from sota-llm-engineering
# 3/3 → 0/3, and was live for a day with invariants 4, 7 and 15 all green.
#
# Bumping VERSION also trips the other release-time checks (5 on the manifests, 14 on
# the front door, 21/23 on the CHANGELOG). That is collateral, not a false pass: the
# assertion is check 29's own sentence, which appears only if check 29 fired. A probe
# whose mutation trips one gate and is asserted against another is the FALSE PASS this
# harness refuses, and this is not that.
( cd "$WT" && perl -pi -e 's/^(description: )/$1Probe rewrite of the routing surface. / if $. < 10' \
      skills/sota-golang/SKILL.md \
    && printf '99.0.0\n' > VERSION )
wt_commit "probe: a release that rewrites a skill description"
probe_committed 29 "a release changes a description and declares no routing check" \
  "declares no routing check"

# 29b — the escape hatch has to be TRUE, not merely present. Same release, this time
# WITH a **Routing checked:** line that resolves to a file which exists and has
# nothing to do with routing. Invariant 11's escapes are declarations-that-must-hold;
# so is this one, and a declaration nobody resolves is a checkbox.
( cd "$WT" && perl -pi -e 's/^(description: )/$1Probe rewrite of the routing surface. / if $. < 10' \
      skills/sota-golang/SKILL.md \
    && printf '99.0.0\n' > VERSION \
    && perl -0777 -pi -e 's/^## \[/## [99.0.0] - 2099-01-01\n\n**Routing checked:** README.md\n\n## [/ if $. == 0' \
      CHANGELOG.md )
wt_commit "probe: a release declaring a routing check that resolves nowhere"
probe_committed 29b "a routing declaration that resolves to an unrelated file" \
  "never mentions desc-routing-regressions"

# 11 — LAST-VERIFIED moved by an ordinary edit. The stamp records a FULL
# re-verification of the library against primary sources; the 2026-07-08 sweep touched
# 100 skill files. Both escapes must be absent for this to fire: the diff is one file,
# not sweep-shaped, and the CHANGELOG says nothing about the stamp.
( cd "$WT" && printf '2099-12-31\n' > LAST-VERIFIED )
wt_commit "probe: move the freshness stamp with no sweep behind it"
probe_committed 11 "LAST-VERIFIED moved without a sweep" \
  "LAST-VERIFIED changed, but this diff touches only"

# 14 — a release that declares no front-door terms. Its own defect replayed: at the
# v1.19.7 cut, five capabilities had shipped across three releases with zero mentions
# anywhere a reader looks.
( cd "$WT" && printf '99.0.0\n' > VERSION )
wt_commit "probe: a release with no front-door declaration"
probe_committed 14 "a release declares no front-door check" \
  "declares no front-door check"

# =============================================================================
# Part B — negative controls for scripts/verify-setup.sh
# =============================================================================
# Same bar, different subject. verify-setup.sh reports whether a MACHINE + REPO
# are really set up, so its known-bad is a fixture, not a file edit: a fake
# CLAUDE_CONFIG_DIR (the script reads that env var, so HOME is never touched), a
# throwaway git repo, and a stub `gh` on PATH so check 10's run history is ours
# to decide.
#
# The inversion matters. Part A mutates a GOOD tree and expects a failure. Here
# the fixture starts good — every check passing — and each probe REMOVES one
# thing, then requires that specific check to report FAIL. A probe that fails
# some *other* check is a FALSE PASS, exactly as in part A: removing a gate
# config cascades into checks 8 and 9, so "something went red" proves nothing.

echo
echo "Negative controls for scripts/verify-setup.sh"
VS=$(mktemp -d)
cleanup_vs() { rm -rf "${VS:?}"; }
trap 'cleanup; cleanup_vs' EXIT   # part A's worktree AND this fixture

build_fixture() {  # a machine+repo where every check passes
  rm -rf "${VS:?}/home" "${VS:?}/repo" "${VS:?}/bin"
  mkdir -p "$VS/home/skills" "$VS/home/profiles" "$VS/bin" "$VS/repo/.github/workflows"
  # library reach: the router plus a couple of domain skills
  mkdir -p "$VS/home/skills/sota" "$VS/home/skills/sota-testing" "$VS/home/skills/sota-golang"
  # …and the SOURCE side, which is what makes the installed count a denominator
  # rather than a lone number (verify-setup check 1). verify-setup resolves the
  # library from ITS OWN path, not the cwd, so the fixture has to carry a copy of
  # the script for that resolution to land inside the fixture. Copy, then assert
  # the copy is identical — a stale fixture copy would test yesterday's script.
  mkdir -p "$VS/repo/skills/sota" "$VS/repo/skills/sota-testing" "$VS/repo/skills/sota-golang"
  mkdir -p "$VS/repo/scripts"
  cp "$REPO/scripts/verify-setup.sh" "$VS/repo/scripts/verify-setup.sh"
  cmp -s "$REPO/scripts/verify-setup.sh" "$VS/repo/scripts/verify-setup.sh" \
    || { echo "fixture copy of verify-setup.sh differs from the original — aborting"; exit 1; }
  # always-on routing: both layers
  printf 'routing: consult the sota router.\n' > "$VS/home/CLAUDE.md"
  printf '{"hooks":{"UserPromptSubmit":[{"hooks":[{"command":"echo sota"}]}]}}\n' > "$VS/home/settings.json"
  printf 'stack\n' > "$VS/home/profiles/example.md"
  # repo context
  cd "$VS/repo"
  git init -q . && git config user.email t@e && git config user.name t
  printf 'MIT\n' > LICENSE; printf '*.log\n' > .gitignore
  printf '# readme\n' > README.md; printf '# agents\n' > AGENTS.md
  printf 'repos:\n  - repo: gitleaks/gitleaks\n' > .pre-commit-config.yaml
  printf 'name: CI\non: [push]\njobs: {a: {runs-on: ubuntu-latest, steps: []}}\n' > .github/workflows/ci.yml
  printf '#!/bin/sh\nexit 0\n' > .git/hooks/pre-commit; chmod +x .git/hooks/pre-commit
  git remote add origin https://example.invalid/x.git
  # stub gh: authenticated, and every sampled run concluded "success"
  cat > "$VS/bin/gh" <<'GH'
#!/bin/sh
case "$1 $2" in
  "auth status") exit 0 ;;
  "run list")    i=0; while [ $i -lt 60 ]; do echo success; i=$((i+1)); done; exit 0 ;;
esac
exit 0
GH
  chmod +x "$VS/bin/gh"
  cd "$REPO"
}

run_vs() {  # sets VS_OUT / VS_RC
  VS_RC=0
  # Run the fixture's copy, so the script's self-relative library lookup resolves
  # inside the fixture rather than against this repo (which would make every probe
  # compare the fixture's 3 skills against the real tree's 42).
  VS_OUT=$( cd "$VS/repo" && CLAUDE_CONFIG_DIR="$VS/home" PATH="$VS/bin:$PATH" \
            bash "$VS/repo/scripts/verify-setup.sh" 2>&1 ) || VS_RC=$?
}

build_fixture
printf '  [positive control] fully-configured fixture must PASS ... '
run_vs
if [ "$VS_RC" -eq 0 ] && ! printf '%s\n' "$VS_OUT" | grep -q '^FAIL'; then
  echo "ok"
else
  echo "FAIL"
  echo "  The known-good fixture does not pass, so every probe below would be"
  echo "  meaningless. Nothing was run."
  printf '%s\n' "$VS_OUT" | grep -E '^(FAIL|PARTIAL)' | sed 's/^/    /'
  exit 1
fi

vs_out_has_fail() {  # a FAIL line that ALSO contains $1 — same line, no pipe (see part A)
  local needle="$1" line
  while IFS= read -r line; do
    case "$line" in (FAIL*"$needle"*) return 0 ;; esac
  done <<VSEOF
$VS_OUT
VSEOF
  return 1
}

vs_probe() {  # <name> <expected check label>  — fixture already broken by caller
  local name="$1" want="$2"
  tested=$((tested + 1))
  run_vs
  if [ "$VS_RC" -eq 0 ]; then
    echo "  [vs] $name — NOT CAUGHT: verify-setup still exited 0. This check is INERT."
    failed=$((failed + 1))
  # Same de-piping as part A, but this assertion is ANCHORED -- the want must appear on
  # a FAIL line, not merely somewhere after one. A flat glob over the whole buffer would
  # have accepted a match on a different line, which loosens the probe rather than fixing
  # it; iterating lines keeps `grep "^FAIL.*want"` semantics exactly, with no pipe.
  elif vs_out_has_fail "$want"; then
    echo "  [vs] $name — caught"
    caught=$((caught + 1))
  else
    echo "  [vs] $name — FALSE PASS: it failed, but not on '${want}'."
    printf '%s\n' "$VS_OUT" | grep '^FAIL' | head -2 | sed 's/^/        got: /'
    failed=$((failed + 1))
  fi
  build_fixture
}

vs_out_has_partial() {  # a PARTIAL line that ALSO contains $1 — same line, no pipe
  local want="$1" line
  while IFS= read -r line; do
    case "$line" in PARTIAL*) case "$line" in *"$want"*) return 0 ;; esac ;; esac
  done <<VSEOF
$VS_OUT
VSEOF
  return 1
}

vs_probe_partial() {  # <name> <expected check label> — for branches that report
  # PARTIAL rather than FAIL. verify-setup exits on n_fail alone, so a PARTIAL run
  # exits 0 and vs_probe (which demands non-zero) would read it as INERT. Assert the
  # row instead of the exit code — and still refuse a catch for the wrong reason.
  local name="$1" want="$2"
  tested=$((tested + 1))
  run_vs
  if vs_out_has_partial "$want"; then
    echo "  [vs] $name — caught (PARTIAL)"
    caught=$((caught + 1))
  else
    echo "  [vs] $name — NOT CAUGHT: no PARTIAL row for '${want}'. This branch is INERT."
    printf '%s\n' "$VS_OUT" | grep -E '^(FAIL|PARTIAL)' | head -2 | sed 's/^/        got: /'
    failed=$((failed + 1))
  fi
  build_fixture
}

rm -rf "$VS/home/skills";                       vs_probe "no skills installed"            "1. sota skills reachable"
# A `git pull` updates every existing symlink and can create none, so a newly added
# skill stays uninstalled while the count still looks plausible. Observed on a real
# machine at 41 of 42.
rm -rf "$VS/home/skills/sota-golang";           vs_probe_partial "installed count below the source count" "1. sota skills reachable"
rm -f "$VS/home/settings.json" "$VS/home/CLAUDE.md"; vs_probe "no routing directive or hook"  "2. always-on routing"
ln -sf /nonexistent/x.md "$VS/home/profiles/dangling.md"; vs_probe "dangling profile symlink" "3. stack profile"
rm -f "$VS/repo/AGENTS.md";                     vs_probe "no agent file"                  "4. agent file present"
rm -f "$VS/repo/LICENSE";                       vs_probe "no licence"                     "6a. licence"
rm -f "$VS/repo/.gitignore";                    vs_probe "no .gitignore"                  "6b. .gitignore"
rm -rf "$VS/repo/.pre-commit-config.yaml" "$VS/repo/.github"; vs_probe "no gate mechanism" "7. gate mechanisms found"
printf 'repos:\n  - repo: some/other-linter\n' > "$VS/repo/.pre-commit-config.yaml"
rm -rf "$VS/repo/.github";                      vs_probe "gates without secret scanning"  "8. secret scanning configured"
rm -f "$VS/repo/.git/hooks/pre-commit";         vs_probe "hook manager configured, not installed" "9. hooks installed"
# A stage declared in the config installs NO hook (pre-commit 4.6.0, verified
# 2026-08-19). Check 9 still passes here — the pre-commit hook file is present —
# which is exactly why 9a exists and why this probe names 9a, not 9.
printf 'repos:\n  - repo: gitleaks/gitleaks\n    hooks:\n      - id: gitleaks\n        stages: [pre-push]\n' \
  > "$VS/repo/.pre-commit-config.yaml"
vs_probe "stage declared in config, its hook never installed" "9a. declared stages installed"
cat > "$VS/bin/gh" <<'GH'
#!/bin/sh
case "$1 $2" in
  "auth status") exit 0 ;;
  "run list")    i=0; while [ $i -lt 60 ]; do echo skipped; i=$((i+1)); done; exit 0 ;;
esac
exit 0
GH
chmod +x "$VS/bin/gh";                          vs_probe "CI history is all-skipped"      "10a. CI has executed"

# --- result ---------------------------------------------------------------
echo
if [ "$tested" -eq 0 ]; then
  echo "FAIL: 0 mutations tested — an empty negative-control run proves nothing."
  exit 1
fi
if [ "$failed" -ne 0 ]; then
  printf 'FAIL: %d of %d mutations were not caught by the check they target.\n' "$failed" "$tested"
  exit 1
fi
printf 'PASS: %d/%d mutations caught by the intended check.\n' "$caught" "$tested"
echo "      check-invariants.sh COVERED: 1, 2, 3, 4, 6, 7, 8, 10, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29 (26 of 29)."
echo "      NOT COVERED, and why — every remaining one needs state a worktree lacks:"
echo "        5, 9        — a version/CHANGELOG-shaped fixture (VERSION vs tag vs top entry)."
echo "        12          — mtime-based: needs a rendered asset older than its source."
echo "      verify-setup.sh: checks 1, 2, 3, 4, 6a, 6b, 7, 8, 9, 9a, 10a. Checks 5"
echo "      and 11 are judgement (N/A by design) and 10b/12 need a different fixture."
