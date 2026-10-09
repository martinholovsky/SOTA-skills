#!/usr/bin/env bash
#
# plugin-routing-hook.sh — the plugin's UserPromptSubmit routing reminder, ON by default.
#
# WHY THIS EXISTS. Skills alone are not used. Measured 2026-10-08 in sota-agent-evals: across
# 166 agent-loop runs with all skills installed but no routing layer, the model invoked a
# SOTA skill ZERO times — including the router, whose description was visible. A fresh
# install's listing budget also drops descriptions alphabetically from `sota-observability`
# onward (name-only: sota-python, sota-testing, ...). The installer's per-prompt routing hook
# is what makes Claude reach for the router; a plugin user had no such hook, while the
# first-run notice told them the skills "route automatically". Claude Code merges plugin hooks
# with user and project hooks (code.claude.com/docs/en/hooks), so the plugin can ship it.
#
# THE TEXT HAS ONE SOURCE: install.sh's HOOK_CMD, read at run time. invariant 16 already pins
# that text to the README; copying it here would be a second copy nobody gates.
#
# NO DOUBLE INJECTION: if a user or project settings file already carries the installer's
# hook (its marker, HOOK_SIG, is the literal "sota-* skills"), this prints nothing.
#
# OPT OUT: set SOTA_ROUTING_HOOK=off (or 0 / false), e.g. in settings.json "env".
#
# Output on stdout becomes context for the prompt (UserPromptSubmit). Errors go to stderr and
# the hook exits 0: a broken reminder must never block a prompt.
set -euo pipefail

case "${SOTA_ROUTING_HOOK:-on}" in
  off | OFF | 0 | false | FALSE | no) exit 0 ;;
esac

root="${CLAUDE_PLUGIN_ROOT:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}"
cfg="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
proj="${CLAUDE_PROJECT_DIR:-$PWD}"

for s in "$cfg/settings.json" "$cfg/settings.local.json" \
         "$proj/.claude/settings.json" "$proj/.claude/settings.local.json"; do
  [ -f "$s" ] || continue
  if grep -q 'UserPromptSubmit' "$s" 2>/dev/null && grep -qF 'sota-* skills' "$s" 2>/dev/null; then
    exit 0   # the installer's hook is already injecting the same text
  fi
done

line="$(grep -m1 '^readonly HOOK_CMD="echo '"'" "$root/scripts/install.sh" 2>/dev/null || true)"
text="${line#readonly HOOK_CMD=\"echo \'}"
text="${text%\'\"}"
if [ -z "$line" ] || [ -z "$text" ] || [ "$text" = "$line" ]; then
  echo "sota-skills: plugin-routing-hook could not read HOOK_CMD from $root/scripts/install.sh — no routing reminder this prompt" >&2
  exit 0
fi
printf '%s\n' "$text"
