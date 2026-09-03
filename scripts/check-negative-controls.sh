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
# (mutation-probe every control), §2.2 (an instrument needs a known-bad it must
# reject and a known-good it must pass), and `sota-devsecops` rules/05 §5.6, which
# says outright that no mainstream framework requires evidence a gate CAN fail.
# We required that of everyone else and did not do it here. This closes that.
#
# WHAT IT DOES. For each mutation below: apply a known-bad to a disposable copy of
# the tree, run the gate, and require BOTH
#   (a) a non-zero exit, and
#   (b) the EXPECTED check to be the one that complained.
# (b) is not pedantry. A harness that accepts any non-zero exit reports "18/18
# controls caught" while every run dies before the thing under test (rules/12
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
# is the trap rules/12 §2.2 names explicitly.
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
cleanup() { git worktree remove --force "$WT" >/dev/null 2>&1 || true; rm -rf "$(dirname "$WT")"; }
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
  elif printf '%s\n' "$GATE_OUT" | grep -qF -- "$want"; then
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
  VS_OUT=$( cd "$VS/repo" && CLAUDE_CONFIG_DIR="$VS/home" PATH="$VS/bin:$PATH" \
            bash "$REPO/scripts/verify-setup.sh" 2>&1 ) || VS_RC=$?
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

vs_probe() {  # <name> <expected check label>  — fixture already broken by caller
  local name="$1" want="$2"
  tested=$((tested + 1))
  run_vs
  if [ "$VS_RC" -eq 0 ]; then
    echo "  [vs] $name — NOT CAUGHT: verify-setup still exited 0. This check is INERT."
    failed=$((failed + 1))
  elif printf '%s\n' "$VS_OUT" | grep -q "^FAIL.*${want}"; then
    echo "  [vs] $name — caught"
    caught=$((caught + 1))
  else
    echo "  [vs] $name — FALSE PASS: it failed, but not on '${want}'."
    printf '%s\n' "$VS_OUT" | grep '^FAIL' | head -2 | sed 's/^/        got: /'
    failed=$((failed + 1))
  fi
  build_fixture
}

rm -rf "$VS/home/skills";                       vs_probe "no skills installed"            "1. sota skills reachable"
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
echo "      check-invariants.sh COVERED: 1, 2, 3, 4, 6, 7, 8, 10, 13, 15, 16, 17, 18, 19, 20 (15 of 20)."
echo "      NOT COVERED, and why — every remaining one needs state a worktree lacks:"
echo "        5, 9        — a version/CHANGELOG-shaped fixture (VERSION vs tag vs top entry)."
echo "        11, 14      — diff-based: they compare against a merge base."
echo "        12          — mtime-based: needs a rendered asset older than its source."
echo "      verify-setup.sh: checks 1, 2, 3, 4, 6a, 6b, 7, 8, 9, 9a, 10a. Checks 5"
echo "      and 11 are judgement (N/A by design) and 10b/12 need a different fixture."
