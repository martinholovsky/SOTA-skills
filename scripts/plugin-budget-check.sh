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

# WHAT is measured comes from skill-listing-sources.sh, shared with verify-setup.sh and
# install.sh. This script used to walk `$CLAUDE_HOME/skills` and `$CLAUDE_HOME/plugins`
# itself, with `find -maxdepth 4` — which reaches no plugin skill at all (the shallowest
# sits at depth 5), and counted every synced account set rather than the signed-in one.
# Field-reported 2026-09-29: it printed ~66.7k for a listing whose on-disk half was ~88k,
# because the sota-skills plugin installed beside a clone doubled the library unseen.
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
lister="$here/skill-listing-sources.sh"
[ -x "$lister" ] || exit 0
# The hook's stdin JSON carries the session's `model` (optional per the hooks docs —
# omitted after /clear, for one). Hand it to the lister, which uses a `[1m]` suffix as
# proof of a 1M window. Read stdin only when it is not a terminal: run by hand, `cat`
# would wait forever.
session_model=""
if [ ! -t 0 ]; then
  session_model="$(sed -n 's/.*"model"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' 2>/dev/null | head -1)"
fi
summary="$(SOTA_SESSION_MODEL="$session_model" "$lister" 2>/dev/null)"
val() { printf '%s\n' "$summary" | sed -n "s/^$1=//p" | head -1; }
visible="$(val total)"
dup="$(val duplicate_library)"
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

# Size against the window this machine actually runs, when anything knows it (the lister
# reads, in order: the window our status line last observed, CLAUDE_CODE_DISABLE_1M_CONTEXT,
# a `[1m]` model). Until 2026-09-29 this assumed 200K unconditionally, so a 1M-context
# user — whose budget is five times larger — was told their skills were being truncated
# when nothing was. Unknown still means 200K: the smaller window, so it errs to warning.
window="$(val window)"; case "$window" in ''|*[!0-9]*) window=200000 ;; esac
wsrc="$(val window_source)"; [ -n "$wsrc" ] || wsrc=unknown
budget="$(awk -v f="$frac" -v w="$window" 'BEGIN { printf "%d", w * 4 * f }')"
case "$wsrc" in
  observed) wnote="your context window, as the status line last saw it" ;;
  disabled) wnote="CLAUDE_CODE_DISABLE_1M_CONTEXT=1 caps every model at 200K" ;;
  model)    wnote="your model ($(val window_model)) runs the 1M window" ;;
  *)        wnote="window UNKNOWN, so the smaller 200K is assumed — on a 1M-context model the budget is 5x this and this notice does not apply" ;;
esac
over=0; [ "$need" -gt "$budget" ] 2>/dev/null && over=1
# Silent only when it fits AND the library is installed once. A duplicate is worth saying
# even when it fits: it spends the budget twice and is fixed by removing a copy, not by
# raising a setting — the opposite remedy to the one below.
[ "$over" -eq 1 ] || [ -n "$dup" ] || exit 0

# Speak once per (need, frac) pair: silent again once it is fixed, and it speaks again if
# the corpus grows. Nagging every session is how a real warning gets tuned out.
mkdir -p "$data" 2>/dev/null || true
marker="$data/.budget-notice-$need-$frac-${dup:-once}"
[ -e "$marker" ] && exit 0
: > "$marker" 2>/dev/null || true

if [ -n "$dup" ]; then
  cat <<MSG
[sota-skills — relay this to the user now, briefly, then continue with their request.]
SOTA-skills is installed TWICE: as the '$dup' plugin and as a personal copy in
$CLAUDE_HOME/skills. Every skill is listed twice, so the library costs double its share of
the skill-listing budget, and two versions can disagree about the same rule.

Offer to keep one: '/plugin uninstall $dup@<marketplace>' keeps the clone (live on git pull);
or remove the ~/.claude/skills/sota* links to keep the plugin (updates with the plugin).
MSG
  [ "$over" -eq 1 ] || exit 0
  echo
fi

want="$(awk -v n="$need" -v w="$window" 'BEGIN { f = (n / (w * 4) * 100); f = int(f) + (f > int(f)); f = f / 100
                                  if (f < 0.02) f = 0.02; if (f > 0.10) f = 0.10; printf "%.2f", f }')"
cat <<MSG
[sota-skills — relay this to the user now, briefly, then continue with their request.]
Your installed skill descriptions do not fit Claude Code's per-turn skill-listing budget, so
some skills are being listed as a bare name with NO description. Those cannot be auto-selected
on what they do — the model can only reach them if something names them explicitly.

  descriptions found   ~${need} characters (incl. an allowance for built-in skills)
  listing budget       ${budget} characters at a ${window}-token context (skillListingBudgetFraction=${frac})
                       (${wnote})

Claude Code logs this to ~/.claude/debug/ and shows it nowhere, which is why it goes unnoticed.

Offer to fix it by setting the fraction in ~/.claude/settings.json (it reserves that share of
every context window for the listing, so it is the user's call):

  skillListingBudgetFraction: ${want}

Ask before changing their settings. They can also run /skills to disable skills they do not use.
MSG
exit 0
