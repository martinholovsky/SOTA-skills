# Using the library from other agents — where each one looks

`scripts/install.sh` is native to Claude Code, which reads `~/.claude/skills`. Most other
agents **do not document that directory**, so a default install may be invisible to them. A
field report (2026-09-29) found this on a Copilot CLI machine: the skills were installed,
`verify-setup.sh` passed, and Copilot saw none of them.

Every path below comes from the vendor's own documentation, **fetched 2026-09-29**, with
the URL and a verbatim quote kept in the intake entry (`docs/ADOPTION-LOG.md`, 2026-09-29).
These paths move. Re-check the linked page before relying on a row.

## The table

| agent | personal skills | global instructions | documents `~/.claude/skills`? |
|---|---|---|---|
| **Claude Code** | `~/.claude/skills` | `~/.claude/CLAUDE.md` | yes (native) |
| **GitHub Copilot CLI** | `~/.copilot/skills`, `~/.agents/skills` | `~/.copilot/copilot-instructions.md` (`COPILOT_HOME` replaces `~/.copilot`) | **no** — `.claude/skills` is project-level only |
| **Copilot in VS Code** | `~/.copilot/skills`, `~/.claude/skills`, `~/.agents/skills` | `~/.copilot/copilot-instructions.md` (Agent Host); `~/.claude/CLAUDE.md` (Local agent, `chat.useClaudeMdFile`) | yes |
| **OpenAI Codex CLI** | `$HOME/.agents/skills` (admin: `/etc/codex/skills`) | `~/.codex/AGENTS.override.md`, else `~/.codex/AGENTS.md` (`CODEX_HOME`) | **no** (not mentioned — undocumented, not tested) |
| **Cursor** | `~/.agents/skills`, `~/.cursor/skills`, plus `~/.claude/skills` and `~/.codex/skills` for compatibility | *User Rules* in Customize → Rules — a settings screen, **no documented file** | yes |
| **Gemini CLI** | `~/.gemini/skills`, `~/.agents/skills` | `~/.gemini/GEMINI.md` | **no** (not mentioned — undocumented, not tested) |

Project-level equivalents: `.agents/skills` is read by all five non-Claude agents. Copilot
(CLI and VS Code) and Cursor also read `.claude/skills`, so `install.sh --project DIR` already
reaches them. Codex and Gemini do not.

Sources: [Copilot CLI skills](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills) ·
[Copilot CLI instructions](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions) ·
[VS Code skills](https://code.visualstudio.com/docs/agent-customization/agent-skills) ·
[VS Code instructions](https://code.visualstudio.com/docs/agent-customization/custom-instructions) ·
[Codex skills](https://learn.chatgpt.com/docs/build-skills) ·
[Codex AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md) ·
[Cursor skills](https://cursor.com/docs/skills) · [Cursor rules](https://cursor.com/docs/rules) ·
[Gemini CLI skills](https://geminicli.com/docs/cli/skills/) ·
[Gemini CLI GEMINI.md](https://geminicli.com/docs/cli/gemini-md/) ·
[agentskills.io client guide](https://agentskills.io/client-implementation/adding-skills-support.md).
Gemini CLI's own page says it *"was replaced by Antigravity CLI on June 18th, 2026"* for unpaid
and Google One users. Antigravity's skill paths were **not** researched here.

## What the installer does with it

- **Skills: `~/.agents/skills`, and only that.** It is the one personal path that all five
  non-Claude agents document. `~/.copilot/skills` is deliberately *not* also written: VS
  Code reads `~/.copilot`, `~/.claude` **and** `~/.agents`, so a third copy of each skill
  would add nothing.
  - `--target all` links into both `~/.claude/skills` and `~/.agents/skills`.
  - `--target agents` links into `~/.agents/skills` alone.
  - `--target claude` keeps the old behaviour.
  - With no `--target`, the installer links Claude only. If it finds `~/.copilot`, `~/.codex`
    or `~/.gemini` (the agents that do not document `~/.claude/skills`), it **offers** the fan-out
    on an interactive run, or accepts it under `--yes`. A non-interactive run prints a
    one-line hint instead.
- **Directive: every agent that is installed.** With `--routing`, the managed routing block
  also goes into `copilot-instructions.md`, `~/.codex/AGENTS.md` and `~/.gemini/GEMINI.md`,
  but only for an agent whose home directory exists.
  - It follows the same contract as `CLAUDE.md`: a `.bak` before the first change, the block
    **appended** to your own content (never replacing it), and refreshed in place between the
    markers on later runs.
  - Cursor has no file to write, so the installer tells you to paste the block into User
    Rules.
  - It warns if a directive names the `sota` skill while `~/.agents/skills` is empty, because
    such an instruction cannot be followed.
- **No hook.** The `UserPromptSubmit` re-injection is Claude Code's. For other agents the
  directive is the only always-on layer.
- **Check it:** `scripts/verify-setup.sh` reports three rows:
  - **1e** — skills are live links, not copies.
  - **1f** — each detected agent reaches `~/.agents/skills`, compared against the checkout's
    count.
  - **2b** — each detected agent's global file carries the directive.

  All three report PARTIAL, never FAIL. Another agent being installed is not evidence that
  you want the library in it.

## Windows: a copy that looks like a link

Git Bash and MSYS2 do **not** fail `ln -s` when Windows refuses a symlink. They copy and
exit 0: MSYS2's default is `winsymlinks:deepcopy`
([msys2.org/docs/symlinks](https://www.msys2.org/docs/symlinks/)), and Git for Windows
says *"the ln -s command in Git Bash does not create symbolic links. Instead, it creates
copies"* ([gitforwindows.org/symbolic-links](https://gitforwindows.org/symbolic-links)). Without Developer Mode or Administrator rights, the default
install was therefore a **snapshot that `git pull` never reaches**, and nothing said so.

The installer now does three things:
- It sets `MSYS=winsymlinks:nativestrict`. MSYS2 documents this as enabling native
  symlinks; whether it does so in **Git Bash** is not stated by Git for Windows and is
  **not verified**.
- It probes once, asserting `-L` on the result rather than trusting the exit status.
- When no link results, it copies **on purpose** with a warning to re-run after every pull.

`verify-setup.sh` check 1e catches an install copied earlier.

**Unverified:** this path was tested on macOS with an `ln` shim that copies and exits 0, as
deepcopy does. It has **not** been run on a real Windows machine.

## Not verified — do not rely on these

- **Symlinked skill folders.** Only Codex documents following them (*"Codex supports
  symlinked skill folders and follows the symlink target"*). The Copilot, VS Code, Cursor
  and Gemini pages never mention symlinks, which is an absence, not a guarantee.
- **Duplicate skill names.** An agent that reads both `~/.claude/skills` and
  `~/.agents/skills` (VS Code, Cursor) sees each skill twice under `--target all`. Only
  Gemini documents a precedence rule (*"the `.agents/skills/` alias takes precedence"*); for
  the others the behaviour is undocumented.
- **`COPILOT_HOME` and skills.** The Copilot CLI page says the variable moves *both
  user-level instruction locations*. It does not say whether the skills directory moves
  with it.
- **Windows home.** No vendor page gives a `%USERPROFILE%` form of these paths; `~` is
  assumed to mean the user's home folder there.
