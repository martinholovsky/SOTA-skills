# SOTA Engineering Skills

Skills that make Claude build and audit software to state-of-the-art practice, with every
claim checked against a primary source. Forty-two domain and language skills (security,
architecture, APIs, databases, cloud, Kubernetes, web frameworks, observability, testing, LLM
engineering, Rust, Go, C/C++, Java and Kotlin, Python, TypeScript, .NET, PHP, Ruby, Swift and
more) sit behind one router skill, `sota`, and each works in two modes: BUILD applies the rules
while writing code, and AUDIT reviews existing code and reports findings as
`file:line | rule | severity | effort | fix`.

Source, measurements and the full documentation:
<https://github.com/martinholovsky/SOTA-skills>. This tree is generated from that repository
for the Claude plugin directory; `SOURCE_COMMIT` names the commit it was built from.

## What runs where

Per Anthropic's plugin support table (claude.com/docs/plugins/platform-support, read
2026-11-01):

| Component | claude.ai chat | Cowork | Claude Code |
|---|---|---|---|
| Skills (`skills/`) | loads | loads | loads |
| Slash commands (`commands/`) | loads each as a skill, applied when it fits | loads | loads |
| Hooks (`hooks/hooks.json`) | **ignored** | loads | loads |

**In chat you get the skills and none of the hooks.** That matters, because the per-prompt
routing reminder below is the measured reason the skills get used at all: across 166 agent runs
with every skill installed and no routing reminder, the model invoked a SOTA skill zero times
(sota-agent-evals v3, 2026-10-08). In chat, name the skill or say "use the sota skills" in your
message. A plugin installed on your claude.ai account also appears in Claude Code as a synced
plugin, where the hooks do run.

## Hooks: everything that runs on your machine

Six hooks, all on by default in Cowork and Claude Code. **None makes a network request**: no
`curl`, no fetch, no `git fetch`/`pull`, no socket; every `git` call is local. Each
fails open (an error is one line on stderr, and the hook exits 0) except where stated.

| Event | Script | What it reads | What it writes | Output | Turn it off |
|---|---|---|---|---|---|
| SessionStart | `scripts/plugin-budget-check.sh` | `~/.claude/settings.json` (`skillListingBudgetFraction`) and the installed skills' descriptions, via `scripts/skill-listing-sources.sh` | a marker file in the plugin data dir | one notice when skill descriptions overflow Claude Code's listing budget, or the library is installed twice; otherwise nothing | remove the plugin |
| SessionStart | `scripts/plugin-notice.sh` | nothing | a marker in the plugin data dir, so it speaks once | a one-time first-run notice | it runs once |
| SessionStart | `scripts/update-reminder.sh` | this tree's `VERSION`; `.sota-install` stamps left by a copied install of the same library; for a git-checkout install, that checkout's branch and settings | a timestamp in the plugin data dir | at most one short notice every 14 days saying an update *may* exist (it never checks), plus a notice if a copied install of the library is older than its checkout | `SOTA_UPDATE_REMINDER_DAYS=0` |
| UserPromptSubmit | `scripts/plugin-routing-hook.sh` | your user and project `settings.json`, to stay silent if the same reminder is already installed; `scripts/install.sh`, read as text for the reminder's wording | nothing | the "sota standing rules" reminder (validate claims, keep docs current, route to the skills) added to every prompt | `SOTA_ROUTING_HOOK=off` |
| PostToolUse (Edit, Write, MultiEdit) | `scripts/code-rules-hook.py` (needs `python3`) | the text Claude just wrote | per-session claim files in your temp dir, so each rules file is named once | names the rules file for what that code does (an outbound fetch, a CSV writer, an archive, a handler) | `SOTA_CODE_RULES_HOOK=off` |
| PreToolUse (Bash) | `scripts/zsh-equals-hook.py` (needs `python3`) | the Bash command Claude is about to run | nothing | **can block the command** (exit 2, with the reason) when zsh would silently rewrite or cut it, such as an unquoted `===` separator; acts only when the agent's shell is zsh | `SOTA_ZSH_EQUALS_HOOK=off` |

The plugin data dir is `$CLAUDE_PLUGIN_DATA`, which Claude Code sets. Set the variables in
`settings.json` under `"env"` or in your shell.

## Also in this tree

- `scripts/statusline.sh`, `scripts/init-gates.sh`, `scripts/gen-agents-md.sh`: optional
  extras the first-run notice offers (a status line showing which skills ran, pre-commit gates
  for a repository, an `AGENTS.md` for other agents). Nothing runs them unless you do.
- `scripts/install.sh` ships only because the routing hook reads its reminder text from it. It
  is the installer for a git checkout and is not meant to be run from this tree; it names
  scripts that are not here.

## Licence and security

Skills and documentation: CC BY 4.0 (`LICENSE`). Code (every `*.sh` and `*.py` file and `hooks/hooks.json`): Apache-2.0 (`LICENSE-APACHE`).
Report bad or dangerous guidance as described in `SECURITY.md`; anything security-sensitive goes
to a private advisory, not a public issue.
