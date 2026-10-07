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
| **Antigravity 2.0 app / IDE** *(fetched 2026-10-06)* | `~/.gemini/config/skills` (legacy `~/.gemini/antigravity/skills`) — **not** `~/.agents/skills` | `~/.gemini/GEMINI.md`, `~/.gemini/AGENTS.md`, `~/.gemini/config/{AGENTS,GEMINI}.md`, `~/.gemini/config/rules/*.md` | **no** |
| **Antigravity CLI** *(fetched 2026-10-06)* | `~/.gemini/antigravity-cli/skills` — **not** `~/.agents/skills` | `~/.gemini/GEMINI.md`, `~/.gemini/AGENTS.md`, `~/.gemini/config/rules/*.md`, `~/.gemini/antigravity-cli/rules/*.md` | **no** |

Project-level equivalents: `.agents/skills` is read by all six non-Claude agents (Antigravity:
*"Antigravity defaults to .agents/skills"*; its workspace rules are `AGENTS.md`/`GEMINI.md` and
`.agents/rules/*.md`). Copilot
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
[agentskills.io client guide](https://agentskills.io/client-implementation/adding-skills-support.md) ·
[Antigravity skills](https://antigravity.google/docs/skills) ·
[Antigravity rules](https://antigravity.google/docs/rules).
Gemini CLI's own page says it *"was replaced by Antigravity CLI on June 18th, 2026"* for unpaid
and Google One users, which makes Antigravity the more likely Google agent on a new machine.
Gemini CLI reads `AGENTS.md` only when configured to (`context.fileName`); `GEMINI.md` is its
default (gemini-cli `docs/cli/gemini-md.md`, fetched 2026-10-06).

## What the installer does with it

- **Skills: `~/.agents/skills`, plus Antigravity's own directories.** `~/.agents/skills` is
  the personal path Copilot, Codex, Cursor and Gemini CLI all document; Antigravity reads its
  own (`~/.gemini/config/skills`, `~/.gemini/antigravity-cli/skills`) and is linked there only
  when its home exists (`~/.gemini/config` or `~/.gemini/antigravity` for the app/IDE,
  `~/.gemini/antigravity-cli` for the CLI). A `--project` install needs nothing extra:
  Antigravity's workspace path is `.agents/skills`. `~/.copilot/skills` is deliberately *not* also written: VS
  Code reads `~/.copilot`, `~/.claude` **and** `~/.agents`, so a third copy of each skill
  would add nothing.
  - `--target all` links into `~/.claude/skills`, `~/.agents/skills` and each detected
    Antigravity skills directory.
  - `--target agents` links into `~/.agents/skills` alone.
  - `--target claude` keeps the old behaviour.
  - With no `--target`, the installer links Claude only. If it finds `~/.copilot`, `~/.codex`
    or `~/.gemini` (the agents that do not document `~/.claude/skills`, Antigravity among them), it **offers** the fan-out
    on an interactive run, or accepts it under `--yes`. A non-interactive run prints a
    one-line hint instead.
- **Directive: every agent that is installed.** With `--routing`, the managed routing block
  also goes into `copilot-instructions.md`, `~/.codex/AGENTS.md` and `~/.gemini/GEMINI.md`
  (read by both Gemini CLI and Antigravity), but only for an agent whose home directory exists.
  - The block ends with the router's **absolute path**: an agent that cannot load a skill by
    name is told which file to read. Agents with a skills loader ignore the line.
  - It follows the same contract as `CLAUDE.md`: a `.bak` before the first change, the block
    **appended** to your own content (never replacing it), and refreshed in place between the
    markers on later runs.
  - Cursor has no file to write, so the installer tells you to paste the block into User
    Rules.
  - It warns if a directive names the `sota` skill while `~/.agents/skills` — or a detected
    Antigravity skills directory — is empty, because such an instruction cannot be followed.
- **No hook.** The `UserPromptSubmit` re-injection is Claude Code's. For other agents the
  directive is the only always-on layer.
- **Check it:** `scripts/verify-setup.sh` reports three rows:
  - **1e** — skills are live links, not copies.
  - **1f** — each detected agent reaches `~/.agents/skills`, compared against the checkout's
    count, and each detected Antigravity surface finds the router under its own path.
  - **2b** — each detected agent's global file carries the directive.

  All three report PARTIAL, never FAIL. Another agent being installed is not evidence that
  you want the library in it.

## The optional MCP server

`scripts/sota-mcp-server.py` serves the library **read-only** over MCP (stdio, standard library
only): `list_skills` returns every skill's description so the agent's own model chooses,
`get_skill` and `get_rules_file` return the files, the files are also MCP resources, and the five
commands are MCP prompts. It does not route, write, execute anything or open a connection, and
every request is a lookup in an index built at startup, so no path is ever built from request
input. Dual-era: it answers the 2026-07-28 protocol (`server/discover`, per-request `_meta`) and
the older `initialize` handshake.

Every agent below already loads the skills directly, so this is a second path, **offered, never
imposed**: `install.sh --mcp` registers it for each detected agent (backup first, existing
entries kept), an interactive install or `--update` offers it, and `verify-setup.sh` check **1h**
reports which agents have it, with the enable command where they do not. Formats, from vendor
docs fetched 2026-10-07:

| agent | file | entry under `mcpServers` (Codex: a TOML table) |
|---|---|---|
| Copilot CLI (and VS Code's portable file) | `~/.copilot/mcp-config.json` (`$COPILOT_HOME`) | `{"type":"local","command":"python3","args":[…],"tools":["*"]}` — `tools` is required |
| Codex | `~/.codex/config.toml` (`$CODEX_HOME`) | `[mcp_servers.sota-skills]` `command`/`args`, inside managed markers |
| Gemini CLI | `~/.gemini/settings.json` | `{"command":"python3","args":[…]}` |
| Antigravity | `~/.gemini/config/mcp_config.json` | `{"command":"python3","args":[…]}` |
| Cursor | `~/.cursor/mcp.json` | `{"type":"stdio","command":"python3","args":[…]}` |

Claude Code is not offered it: it reads the skills natively. Tested: a stdio test suite
(`scripts/test-mcp-server.py`, in CI, mutation-checked) and a real client — Claude Code connected
in the modern era and fetched a rules file; that run is also what found a missing required field
(`cacheScope`) the suite had not asserted. Not run against the other five clients.

The installer never edits a Codex `config.toml` it cannot edit safely. It leaves the file
unchanged, with a warning, when the start marker has no end marker: stripping that block would
run to the end of the file and delete every table after it. It also leaves the file unchanged
when a `[mcp_servers.sota-skills]` table already exists outside the markers, for example from
`codex mcp add`, because a second copy would be a duplicate table that TOML forbids. The server
path is TOML-escaped. The test suite counts one reply per request and pins its total, so a
server that silently drops a request fails it (2026-10-07 audit).

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

**A copy now says which release it is.** Every copied skills directory gets a `.sota-install`
stamp (version, commit, source checkout). Before this, nothing could tell a stale copy from a
current one: the update reminder read the *checkout's* `VERSION`, so after a `git pull` it
reported the new release while the copy still served the old guidance. Now:
- the session-start reminder (`scripts/update-reminder.sh`, installed with always-on routing)
  compares each stamp with the checkout and, while they differ, names the copy, both versions and
  the re-install command — on every session, not on a timer, and with no network request;
- check 1e adds the same comparison (`STALE: … a copy of X, checkout is Y`);
- switching back to links removes the stamp.

A deliberate `--copy` is a pin, so the installer does not offer the reminder hook for it; the
forced copy on a machine without symlinks keeps the offer.

**Not done: directory junctions.** Git for Windows documents that *"Directory junctions can be
created by non-administrator users by default"*, which would make the copy unnecessary. How a
junction behaves under Git Bash (`-L`, `readlink`, this installer's pruning) cannot be checked
without a Windows machine, so it stays with the existing Windows deferral in
`docs/ADOPTION-LOG.md`.

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
- **The 2.0 app's MCP file.** Antigravity's docs give `~/.gemini/config/mcp_config.json` for the IDE and
  the CLI; the 2.0 app's tab describes only its Settings UI.
- **Antigravity detection.** A `~/.gemini/config` directory is taken to mean the Antigravity
  2.0 app or IDE is installed. Its docs name that path; whether anything else creates it is not
  known. Whether Antigravity follows **symlinked** skill folders is not documented.
- **Windows home.** No vendor page gives a `%USERPROFILE%` form of these paths; `~` is
  assumed to mean the user's home folder there.
