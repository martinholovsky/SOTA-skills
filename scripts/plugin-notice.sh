#!/usr/bin/env bash
#
# plugin-notice.sh — one-time first-run notice for sota-skills PLUGIN users.
#
# Run by the plugin's SessionStart hook (hooks/hooks.json). Plugins are sandboxed
# and deliberately cannot set up the imperative extras (a global CLAUDE.md
# directive, the status line, per-project generators), so this points users at
# them — once. The notice goes to stdout, which Claude Code adds to context; it
# asks the model to relay the options to the user on the first turn.
#
# Guarded by a marker in the plugin's persistent data dir so it shows only once.
# Clone users get the same information from install.sh, so in practice this only
# fires for plugin installs.
#
set -euo pipefail

data="${CLAUDE_PLUGIN_DATA:-${HOME}/.claude/sota-skills-data}"
marker="${data}/.extras-notice-shown"
[ -e "$marker" ] && exit 0
mkdir -p "$data" 2>/dev/null || true
: > "$marker" 2>/dev/null || true

cat <<'MSG'
[sota-skills plugin — first-run notice. Relay this to the user once, briefly, then continue with their request.]
The SOTA engineering skills are installed and route automatically. A few extras are NOT enabled by the plugin (by design — a plugin can't change your global config or status line). Offer to set up any the user wants:
  - Always-on routing reminder (a UserPromptSubmit hook) — applies the skills without trigger words.
  - Status line showing which skills were used this session.
  - Pre-commit gates for the current repo (scripts/init-gates.sh).
  - AGENTS.md so Codex/Copilot/Gemini/Cursor use the skills too (scripts/gen-agents-md.sh).
The scripts ship with the plugin. Steps: https://github.com/martinholovsky/SOTA-skills#optional-extras-for-plugin-users
MSG
