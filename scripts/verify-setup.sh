#!/usr/bin/env bash
#
# verify-setup.sh — the DETERMINISTIC half of docs/VERIFY-SETUP.md.
#
# init-gates.sh and gen-agents-md.sh SET THINGS UP. This reports whether the
# result is real. "Configured" and "working" render identically: a
# .pre-commit-config.yaml with no installed hook is a file, not a control; a CI
# workflow whose every run is "skipped" is a gate on paper.
#
# STRICTLY READ-ONLY. It creates, modifies and deletes nothing — run it on a repo
# you do not trust yet. Every check reports what it OBSERVED; anything it could
# not actually run is UNVERIFIED with the reason, never a pass.
#
# WHAT STAYS IN THE PROMPT (docs/VERIFY-SETUP.md), because a script cannot do it:
#   - check 4's content judgement: does the agent file carry real build/test
#     commands, deviations and traps, or does it restate generic best practice?
#   - check 5b: are the agent file's factual CLAIMS still true? (Commands
#     existing is checkable; "pinned to 3.11" still being accurate is not.)
#   - check 11: the routing dry-run.
# This script does the rest — existence, resolution, installation state, and run
# history — which it does better than a prompt, and identically every time.
#
# Exit code: 1 if any check FAILed, else 0. UNVERIFIED does NOT fail the run —
# it means nobody watched the thing work, which is unknown, not broken. Do not
# read a 0 as "the setup is good" when the report carries UNVERIFIED rows.
#
# Portable to macOS bash 3.2 (no associative arrays, no mapfile).
set -euo pipefail

RUN_SAMPLE=60
while [ $# -gt 0 ]; do
  case "$1" in
    --runs) RUN_SAMPLE="${2:?--runs needs a number}"; shift 2 ;;
    -h|--help)
      echo "usage: verify-setup.sh [--runs N]   # N = CI runs to sample for check 10 (default 60)"
      exit 0 ;;
    *) echo "unknown argument: $1 (try --help)" >&2; exit 2 ;;
  esac
done
case "$RUN_SAMPLE" in
  ''|*[!0-9]*) echo "--runs must be a positive integer, got: $RUN_SAMPLE" >&2; exit 2 ;;
esac

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$REPO_ROOT"

CLAUDE_HOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"

n_pass=0; n_fail=0; n_partial=0; n_unver=0; n_na=0

row() {  # <status> <check> <evidence>
  case "$1" in
    PASS)       n_pass=$((n_pass + 1)) ;;
    FAIL)       n_fail=$((n_fail + 1)) ;;
    PARTIAL)    n_partial=$((n_partial + 1)) ;;
    UNVERIFIED) n_unver=$((n_unver + 1)) ;;
    N/A)        n_na=$((n_na + 1)) ;;
  esac
  printf '%-11s %-34s %s\n' "$1" "$2" "$3"
}

section() { printf '\n== %s\n' "$1"; }

echo "SOTA setup verification (read-only) — $REPO_ROOT"

# --- A. Is the library reaching this directory? ---------------------------
section "A. Library reach"

# Probe every install path, not one: personal, project, and plugin.
skill_dirs=""
for d in "$CLAUDE_HOME/skills" ".claude/skills" "$CLAUDE_HOME/plugins"; do
  [ -d "$d" ] && skill_dirs="$skill_dirs $d"
done
n_sota=0
router_seen=0
for d in $skill_dirs; do
  # -L: a symlinked skill dir is the recommended install, so follow links.
  while IFS= read -r s; do
    [ -n "$s" ] || continue
    n_sota=$((n_sota + 1))
    case "$(basename "$s")" in sota) router_seen=1 ;; esac
  done <<EOF
$(find -L "$d" -maxdepth 3 -type d -name 'sota' -o -maxdepth 3 -type d -name 'sota-*' 2>/dev/null || true)
EOF
done
if [ -z "$skill_dirs" ]; then
  row "FAIL" "1. sota skills reachable" "no skills dir found (looked in $CLAUDE_HOME/skills, .claude/skills, $CLAUDE_HOME/plugins)"
elif [ "$n_sota" -eq 0 ]; then
  row "FAIL" "1. sota skills reachable" "skills dir(s) exist but contain no sota* skill:$skill_dirs"
elif [ "$router_seen" -eq 0 ]; then
  row "PARTIAL" "1. sota skills reachable" "$n_sota sota* skills, but the 'sota' ROUTER is not among them — routing is what loads the rest"
else
  row "PASS" "1. sota skills reachable" "$n_sota sota* skills incl. the router, in:$skill_dirs"
fi

# Always-on routing is THREE layers; report which of them are actually present.
directive=0; hook=0
[ -f "$CLAUDE_HOME/CLAUDE.md" ] && grep -qi 'sota' "$CLAUDE_HOME/CLAUDE.md" 2>/dev/null && directive=1
if [ -f "$CLAUDE_HOME/settings.json" ]; then
  # Substring test, not a JSON parse: the hook may be a shell one-liner, a script
  # path, or a wrapper, and any of those is a working injection.
  if tr -d '\n' < "$CLAUDE_HOME/settings.json" | grep -qi 'UserPromptSubmit' \
     && grep -qi 'sota' "$CLAUDE_HOME/settings.json"; then
    hook=1
  fi
fi
if [ "$directive" -eq 1 ] && [ "$hook" -eq 1 ]; then
  row "PASS" "2. always-on routing" "CLAUDE.md directive + UserPromptSubmit hook mentioning sota"
elif [ "$directive" -eq 1 ]; then
  row "PARTIAL" "2. always-on routing" "CLAUDE.md directive only — routing depends on the model reading it, not on per-prompt injection"
elif [ "$hook" -eq 1 ]; then
  row "PARTIAL" "2. always-on routing" "UserPromptSubmit hook only — no global directive in $CLAUDE_HOME/CLAUDE.md"
else
  row "FAIL" "2. always-on routing" "neither a sota directive in CLAUDE.md nor a UserPromptSubmit hook — routing depends on how each prompt is phrased"
fi

# Profile: report the FILENAME only. Its contents are the user's stack.
prof_found=0; prof_dangling=""
for p in "$CLAUDE_HOME"/profiles/*.md; do
  [ -e "$p" ] || [ -L "$p" ] || continue
  if [ -e "$p" ]; then prof_found=$((prof_found + 1)); else prof_dangling="$prof_dangling $(basename "$p")"; fi
done
if [ -n "$prof_dangling" ]; then
  row "FAIL" "3. stack profile" "dangling symlink(s):$prof_dangling"
elif [ "$prof_found" -gt 0 ]; then
  row "PASS" "3. stack profile" "$prof_found profile(s) resolve in $CLAUDE_HOME/profiles (names not read)"
else
  row "N/A" "3. stack profile" "none present — optional; the skills' own defaults apply"
fi

# --- B. Is this repo's own context in place? ------------------------------
section "B. Repo context"

agent_file=""
for f in AGENTS.md CLAUDE.md GEMINI.md; do
  [ -e "$f" ] && { agent_file="$f"; break; }
done
if [ -z "$agent_file" ]; then
  row "FAIL" "4. agent file present" "no AGENTS.md / CLAUDE.md / GEMINI.md"
else
  link_note=""
  for f in AGENTS.md CLAUDE.md GEMINI.md; do
    if [ -L "$f" ]; then
      if [ -e "$f" ]; then link_note="$link_note $f->$(readlink "$f")"
      else row "FAIL" "4. agent file present" "$f is a DANGLING symlink"; link_note=" DANGLING"; fi
    fi
  done
  case "$link_note" in
    *DANGLING*) : ;;
    *) row "PASS" "4. agent file present" "$agent_file$link_note — CONTENT not judged here, see docs/VERIFY-SETUP.md checks 4-5" ;;
  esac
fi

# 5a: the commands an agent file names should exist. Only the presence of a task
# runner is mechanical; whether a NAMED command resolves is check 5a in the
# prompt, and whether its CLAIMS are true is 5b, which no script can do.
row "N/A" "5. agent file is TRUE" "judgement check — run the prompt in docs/VERIFY-SETUP.md (5a commands resolve, 5b claims still accurate)"

# Capabilities, not one implementation's filename.
# First match wins; a glob loop, not `ls` — this repo's own rules/01 says never
# parse ls, and A && B || C (SC2015) prints BOTH rows if the first `row` ever fails.
lic=""
for c in LICENSE* COPYING* COPYRIGHT*; do [ -e "$c" ] && { lic="$c"; break; }; done
if [ -n "$lic" ]; then
  row "PASS" "6a. licence" "$lic"
else
  row "FAIL" "6a. licence" "no LICENSE*/COPYING*/COPYRIGHT* — nobody may legally reuse this"
fi
if [ -f .gitignore ]; then
  row "PASS" "6b. .gitignore" "present"
else
  row "FAIL" "6b. .gitignore" "absent"
fi
rdm=""
for c in README*; do [ -e "$c" ] && { rdm="$c"; break; }; done
if [ -n "$rdm" ]; then
  row "PASS" "6c. README" "$rdm"
else
  row "FAIL" "6c. README" "absent"
fi

# --- C. Are the gates real, or just configured? ---------------------------
section "C. Gates"

gates=""
[ -f .pre-commit-config.yaml ] && gates="$gates pre-commit"
[ -d .husky ] && gates="$gates husky"
{ [ -f lefthook.yml ] || [ -f lefthook.yaml ] || [ -f .lefthook.yml ]; } && gates="$gates lefthook"
n_wf=0
if [ -d .github/workflows ]; then
  n_wf=$(find .github/workflows -maxdepth 1 -name '*.yml' -o -maxdepth 1 -name '*.yaml' 2>/dev/null | wc -l | tr -d ' ')
  [ "$n_wf" -gt 0 ] && gates="$gates ci(${n_wf}-workflow)"
fi
if [ -n "$gates" ]; then
  row "PASS" "7. gate mechanisms found" "${gates# }"
else
  row "FAIL" "7. gate mechanisms found" "no pre-commit / husky / lefthook / CI workflows — nothing gates this repo"
fi

# Secret scanning: search the gate configs, do not infer from a filename.
# Plain grep, NOT `git grep`: git grep reads only TRACKED files, and the primary
# use case for this script is a repo you just scaffolded, whose configs are still
# untracked. Measured 2026-08-02 — an untracked .pre-commit-config.yaml
# configuring gitleaks was reported as "no secret scanning", a false FAIL on
# exactly the repo the check exists for.
scan_paths=""
for p in .pre-commit-config.yaml .github .husky lefthook.yml lefthook.yaml .lefthook.yml; do
  [ -e "$p" ] && scan_paths="$scan_paths $p"
done
scan_hits=""
if [ -n "$scan_paths" ]; then
  for pat in gitleaks trufflehog detect-secrets ggshield gitguardian; do
    # shellcheck disable=SC2086  # word splitting is how the path list is passed
    if grep -r -l -i -- "$pat" $scan_paths >/dev/null 2>&1; then
      scan_hits="$scan_hits $pat"
    fi
  done
fi
if [ -n "$scan_hits" ]; then
  row "PASS" "8. secret scanning configured" "${scan_hits# } referenced in a gate config"
else
  row "FAIL" "8. secret scanning configured" "no gitleaks/trufflehog/detect-secrets/ggshield in any gate config"
fi

# INSTALLED vs merely configured — three distinct states, not two.
hookspath=$(git config --get core.hooksPath 2>/dev/null || true)
hookdir="${hookspath:-.git/hooks}"
installed=0
if [ -d "$hookdir" ]; then
  installed=$(find "$hookdir" -maxdepth 1 -type f ! -name '*.sample' 2>/dev/null | wc -l | tr -d ' ')
fi
if [ "$installed" -gt 0 ]; then
  row "PASS" "9. hooks installed" "$installed non-sample hook(s) in $hookdir"
elif [ -n "$gates" ] && echo "$gates" | grep -q 'pre-commit\|husky\|lefthook'; then
  row "FAIL" "9. hooks installed" "a hook manager is CONFIGURED but $hookdir holds no non-sample hook — that is a file, not a control (run its install step)"
else
  row "N/A" "9. hooks installed" "no local hook manager configured"
fi

# Has each workflow ever EXECUTED, and ever REJECTED anything?
if [ "$n_wf" -eq 0 ]; then
  row "N/A" "10. CI run history" "no workflows to have a history"
elif ! command -v gh >/dev/null 2>&1; then
  row "UNVERIFIED" "10. CI run history" "gh not installed — cannot read real run conclusions; a green badge is not evidence"
elif ! gh auth status >/dev/null 2>&1; then
  row "UNVERIFIED" "10. CI run history" "gh not authenticated — run 'gh auth login'"
else
  # gh's own jq (-q), not a hand-rolled grep over the JSON: a miscounting parser
  # is the failure this repo keeps finding in its own instruments.
  runs=$(gh run list --limit "$RUN_SAMPLE" --json conclusion -q '.[].conclusion' 2>/dev/null || true)
  if [ -z "$runs" ]; then
    row "UNVERIFIED" "10. CI run history" "gh returned no runs (none yet, or no access); sample size 0"
  else
    n_runs=$(printf '%s\n' "$runs" | grep -c . || true)
    n_exec=$(printf '%s\n' "$runs" | grep -cE '^(success|failure)$' || true)
    n_rej=$(printf '%s\n' "$runs" | grep -c '^failure$' || true)
    if [ "$n_exec" -eq 0 ]; then
      row "FAIL" "10a. CI has executed" "$n_runs run(s) sampled, NONE concluded success/failure — an all-skipped history is a control on paper (rules/10 §2.13)"
    else
      row "PASS" "10a. CI has executed" "$n_exec of $n_runs sampled run(s) actually concluded"
    fi
    if [ "$n_rej" -gt 0 ]; then
      row "PASS" "10b. CI has rejected" "$n_rej failure(s) in $n_runs sampled — observed doing its job"
    else
      # No hardcoded sample here. This script runs against ANY repo, and a number
      # measured on one is both wrong for the reader and rot-prone: the note used
      # to read "this repo: 0 failures in 60, 1 in 200" and was false three days
      # later once CI volume pushed that failure out of the window (rules/10 §2.10
      # — a literal in reporting output instead of a derived value).
      row "UNVERIFIED" "10b. CI has rejected" "no failures in $n_runs sampled run(s) — that is not 'never'. Widen with --runs N"
    fi
  fi
fi

# --- E. Can the findings be acted on? -------------------------------------
section "E. Actionability"

if git rev-parse --git-dir >/dev/null 2>&1; then
  origin=$(git remote get-url origin 2>/dev/null || true)
  if [ -n "$origin" ]; then
    row "PASS" "12. remote" "origin: $origin (fork-vs-upstream: check push access before promising a fix)"
  else
    row "PARTIAL" "12. remote" "a git repo with no 'origin' — fixes cannot be pushed anywhere"
  fi
else
  row "N/A" "12. remote" "not a git repository"
fi

# --- Result ---------------------------------------------------------------
printf '\n%s\n' "PASS $n_pass · FAIL $n_fail · PARTIAL $n_partial · UNVERIFIED $n_unver · N/A $n_na"
if [ "$n_unver" -gt 0 ]; then
  echo "UNVERIFIED is not a soft PASS: nobody watched those work. Treat them as unknown."
fi
cat <<'EOF'
Not covered here (a script cannot): whether the agent file's content is
meaningful, and whether its factual claims are still true. Run the prompt in
docs/VERIFY-SETUP.md for those, plus the one check nothing read-only can do —
whether the secret gate actually REJECTS a commit.
EOF
[ "$n_fail" -eq 0 ]
