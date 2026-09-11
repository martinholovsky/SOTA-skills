#!/usr/bin/env bash
#
# plugin-budget-check.sh — tell a PLUGIN user when their skill descriptions are not
# reaching the model.
#
# WHY THIS EXISTS. Claude Code reserves a per-turn character budget for the skill
# listing: `(contextTokens x 4) x skillListingBudgetFraction`, fraction defaulting to
# 0.01 — 8,000 characters on a 200k-context model, shared across EVERY installed skill.
# Over budget it does not shorten descriptions; it ranks entries by recent usage and
# renders the losers as a bare `- name` with no description at all. A skill with no
# description cannot be auto-selected on what it does, and a never-used skill ranks
# zero and goes first.
#
# The engine DOES notice. Measured 2026-09-11 by forcing the condition with
# SLASH_COMMAND_TOOL_CHAR_BUDGET and reading the log it wrote:
#
#   [WARN] Skill listing over budget: 65 skills, 47324 chars > 8000 budget
#          — descriptions will be truncated.
#
# That line goes to ~/.claude/debug/*.txt and NOWHERE ELSE. It never reaches the user,
# which is why this library ran ~20 of its 42 skills as bare names for an entire session
# with nobody noticing. A control that reports correctly into a sink nobody reads is the
# `reported but never read` class, and the fix is to put it where someone will read it.
#
# WHY A HOOK AND NOT A SETTING. A plugin cannot do this declaratively. Verified against
# the shipped 2.1.268 binary: the settings precedence is
# ["userSettings","projectSettings","localSettings","flagSettings","policySettings"] —
# there is no plugin scope — and a plugin contributes skills, hooks, agents, commands and
# MCP servers only. A SessionStart hook is the single lever a plugin has.
#
# WHY IT DOES NOT JUST FIX IT. Writing skillListingBudgetFraction into the user's GLOBAL
# settings unasked is precisely what this library tells auditors to flag. It reports, with
# the numbers and the exact command, and lets the user decide — the same `offer, never
# perform` rule install.sh follows.
#
# Always exits 0: a session must never fail because a notice could not be printed.
set -uo pipefail

CLAUDE_HOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
settings="$CLAUDE_HOME/settings.json"
data="${CLAUDE_PLUGIN_DATA:-$HOME/.claude/sota-skills-data}"

# Sum `- name: description` the way the listing counts it. awk only: no jq, no python3 —
# this runs on every session start on machines we do not control.
measure() {
  # shellcheck disable=SC2016  # this is an awk program, not a shell expansion
  find -L "$@" -maxdepth 4 -name SKILL.md 2>/dev/null | tr '\n' '\0' | xargs -0 awk '
    FNR == 1 {
      if (seen) total += len + nlen + 6
      seen = 1; len = 0; fm = 0; ind = 0
      n = FILENAME; sub(/\/SKILL\.md$/, "", n); sub(/.*\//, "", n); nlen = length(n)
    }
    /^---[[:space:]]*$/ { fm = !fm; next }
    fm && /^description:/ { ind = 1; sub(/^description:[[:space:]]*/, ""); gsub(/^[[:space:]]+|[[:space:]]+$/, ""); len += length($0); next }
    fm && ind && /^[[:space:]]/ { gsub(/^[[:space:]]+|[[:space:]]+$/, ""); len += length($0) + 1; next }
    fm { ind = 0 }
    END { total += len + nlen + 6; print total + 0 }
  ' 2>/dev/null
}

dirs=""
for d in "$CLAUDE_HOME/skills" "$CLAUDE_HOME/plugins"; do
  [ -d "$d" ] && dirs="$dirs $d"
done
[ -n "$dirs" ] || exit 0
# shellcheck disable=SC2086  # word splitting is intended: a list of directories
visible="$(measure $dirs)"
[ -n "${visible:-}" ] && [ "$visible" -gt 0 ] 2>/dev/null || exit 0

# +25% for the bundled skills no script can enumerate — they are compiled into the binary,
# not on disk. Validated 2026-09-11 against the engine's own count: 38,507 visible here
# estimated 48,134 against a true 47,324, i.e. +1.7% and on the conservative side.
need="$(awk -v v="$visible" 'BEGIN { printf "%d", v * 1.25 }')"

frac="$(sed -n 's/.*"skillListingBudgetFraction"[[:space:]]*:[[:space:]]*\([0-9.]*\).*/\1/p' \
        "$settings" 2>/dev/null | head -1)"
# Absent or unparseable means the engine uses its default, so assuming it is correct,
# not pessimistic: this warns exactly when the shipped default is in force.
[ -n "${frac:-}" ] || frac="0.01"

# Size against a 200k context: the documented fallback, the common case, and the only
# one a hook can assume. A fraction that fits there fits a larger window too.
budget="$(awk -v f="$frac" 'BEGIN { printf "%d", 200000 * 4 * f }')"
[ "$need" -gt "$budget" ] 2>/dev/null || exit 0

# Speak once per (need, frac) pair: silent again once it is fixed, and it speaks again if
# the corpus grows. Nagging every session is how a real warning gets tuned out.
mkdir -p "$data" 2>/dev/null || true
marker="$data/.budget-notice-$need-$frac"
[ -e "$marker" ] && exit 0
: > "$marker" 2>/dev/null || true

want="$(awk -v n="$need" 'BEGIN { f = (n / 800000 * 100); f = int(f) + (f > int(f)); f = f / 100
                                  if (f < 0.02) f = 0.02; if (f > 0.10) f = 0.10; printf "%.2f", f }')"
cat <<MSG
[sota-skills — relay this to the user now, briefly, then continue with their request.]
Your installed skill descriptions do not fit Claude Code's per-turn skill-listing budget, so
some skills are being listed as a bare name with NO description. Those cannot be auto-selected
on what they do — the model can only reach them if something names them explicitly.

  descriptions found   ~${need} characters (incl. an allowance for built-in skills)
  listing budget       ${budget} characters at a 200k context (skillListingBudgetFraction=${frac})

Claude Code logs this to ~/.claude/debug/ and shows it nowhere, which is why it goes unnoticed.

Offer to fix it by setting the fraction in ~/.claude/settings.json (it reserves that share of
every context window for the listing, so it is the user's call):

  skillListingBudgetFraction: ${want}

Ask before changing their settings. They can also run /skills to disable skills they do not use.
MSG
exit 0
