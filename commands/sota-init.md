---
description: Set up a repository the way the library expects — inventory what already exists, agree a plan, then add only what is missing (licence, .gitignore and secret scanning, gates, the agent file with this project's own facts, where project data lives), never overwriting a file, and finish with one commit that `git revert` undoes. Run it once, in a new repo or one the library has not been applied to.
---

Set this repository up the way the library expects, adding only what is missing.

This is the day-zero sequence the router offers in one line ("Day zero" in the `sota` skill),
run as one agreed pass. It **adds**; it never overwrites, deletes or rewrites a file that
exists. Everything it writes goes into one commit, so `git revert <sha>` undoes the files.
Hooks it installs outside git are listed at the end with their uninstall command.

## 0. Load the rules this pass applies

Invoke the `sota-docs-workflow` skill **now** and read `sota-docs-workflow` rules/01 §8 (the
documentation baseline), `sota-docs-workflow` rules/01 §10 (day zero) and its `rules/06` (where
project data lives). Invoke the
`sota-shell-scripting` skill and read its `rules/06` (ad-hoc commands) before the first search:
step 1 reports absences, and a search that silently matched nothing reads exactly like "not
present". The parentheses below point into those files; they are not substitutes for them.

`<library>` below is the SOTA-skills checkout: two levels above `readlink ~/.claude/skills/sota`
for a symlink install, or the plugin's root under `~/.claude/plugins` (the directory that holds
`scripts/init-gates.sh`).

**Is this repository yours to set up?** On an upstream you do not own, stop after step 1 and ask:
files added there ride on every branch and PR. Personal scaffolding then goes in
`.git/info/exclude`, never the tracked `.gitignore`.

## 1. Inventory — read only, with a control

Print one row per item: present or missing, and the path or command that showed it. Run a
positive control in the same command as each absence search: a file you know exists.

| Item | How to look |
|---|---|
| Git history | `git rev-list --count HEAD` (a few commits = day zero; a long history means the repo may have decided against some items: ask rather than add) |
| Licence | `LICENSE*`, `COPYING*`, `COPYRIGHT*`, never the bare name |
| `.gitignore` | present, and whether it ignores `.env` and the language's build output |
| Secret scanning | a hook manager (`.pre-commit-config.yaml`, `lefthook.yml`, `.husky/`) or a CI job running gitleaks, trufflehog or similar |
| Gates | lint, format, type check, tests, dependency audit: in a hook config or CI |
| Agent file | `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md`, and what each actually contains |
| Where project data lives | a section with that title in the agent file (`sota-docs-workflow` rules/06 §2) |
| README, CHANGELOG | present at the root |
| Manifests | `pyproject.toml`, `package.json`, `Cargo.toml`, `go.mod`, `pom.xml`/`build.gradle*`, `*.csproj`, `composer.json`, `Gemfile`, `Package.swift` |

From the manifests, read the project's own facts: name, description, test runner, package
manager, the commands that build and test it. **Run each command you intend to write down**
(`--help` at least) and record what it printed. A command copied into the agent file unrun
becomes a fact the next session trusts.

## 2. Plan — and ask what is the user's to decide

Show the plan as a table: each step below as **create**, **skip (exists: <path>)** or **ask**.
Then ask, in one message, only what you cannot decide:

- **The licence.** Never choose one. Offer the common choices for the project's kind, and fetch
  the chosen text from its canonical source (choosealicense.com or the SPDX list), never from
  memory. If the user wants none yet, record that it is deliberately unlicensed.
- **Solo or shared?** A shared or CI-checked repository needs its gates **in the repository**,
  and its contributing docs must say how to install the tooling (`sota-docs-workflow` rules/01
  §10). An ambient install of this library on your machine is not a control on anyone else's
  commit.
- **Where kept data lives**, if the project produces any: the repository-local default, or a
  place the project or organisation already uses (`sota-docs-workflow` rules/06 §2).
- **CI**, if there is none: offer a workflow skeleton. Write it only on a yes.

Do not start step 3 until the user agrees to the plan. A decline is decided: do not ask again
in the same session.

## 3. Add what is missing, in this order

Each step checks `ls -ld -- <path>` first and **skips a path that exists**, even an empty one or
a symlink. It never edits an existing file, with one exception: appending a missing section to
the agent file, shown to the user first.

1. **`.gitignore`**, before anything else can be committed: the language's standard entries
   plus `.env`, `*.local.*` and the project's class-3 folders. If one exists, list the missing
   entries and ask before appending.
2. **Secret scanning and gates**: `<library>/scripts/init-gates.sh --dry-run`, show its output,
   then run it without `--dry-run`. It installs both the pre-commit and pre-push hooks. Install
   the tools it names as missing only with the user's agreement.
3. **Licence**: the text the user chose, as `LICENSE` at the root.
4. **Agent file**: `<library>/scripts/gen-agents-md.sh` writes the library's managed block.
   Add `--siblings` for a `CLAUDE.md` pointer. In a shared repository, pass a `--skills-dir`
   every contributor resolves, or say in the file that the library is a personal install. Then
   add a short **project section outside the managed markers**, holding only what an agent
   would get wrong without it (`sota-docs-workflow` rules/01 §7): the commands step 1 ran, the
   deviations from the language's defaults, the paths nothing may touch.
5. **"Where project data lives"**: the section from `sota-docs-workflow` rules/06 §2, with the
   places agreed in step 2. Its first line says when it applies. For an existing project with
   data already scattered, stop at declaring the places: the audit and any moves are a separate
   task (rules/06 §3 and §4), run when the user asks for it.
6. **README and CHANGELOG**, only if missing: a README with what the project is, a quickstart
   whose commands step 1 ran, and its honest status; a CHANGELOG with an `Unreleased` section.
7. **Nothing else by default.** `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, an ADR
   log and runbooks are created when their trigger fires (`sota-docs-workflow` rules/01 §8). Name
   any trigger that has already fired (public repository, outside contributors, a security
   surface, a decision being made) and offer that file alone.
8. **CI**, only on the yes from step 2: invoke the `sota-devsecops` skill and read its
   `rules/01` (pipeline security) first: actions pinned to a commit SHA, least-privilege
   `permissions:`, no secrets in pull-request workflows from forks.

## 4. Verify, then commit once

- Run `<library>/scripts/verify-setup.sh` in the repository. It is read-only. Report each FAIL
  and each UNVERIFIED row; an UNVERIFIED row is not a pass.
- Run the gates once (`pre-commit run --all-files`). Formatters may change files: show the diff
  and ask before keeping it.
- Read `git status --porcelain` by eye. Stage **by path**, only the files this pass created,
  never with `git add -A` (`sota-docs-workflow` rules/04 §1).
- Propose one commit, `chore: initialise repository (sota-init)`, and make it on the user's yes.
  Push only when asked.

## 5. Report

One table: each item as created, skipped (with the existing path) or declined, and how to
undo it.

- Files: `git revert <sha>` of the one commit.
- Hooks: `pre-commit uninstall --hook-type pre-commit --hook-type pre-push`.
- Anything installed on the machine (tools, the library itself): named, with the command that
  installed it.

The agent hooks (the zsh command check, the code-rules and action-rules notes, the per-prompt
reminder) are not part of this pass: they belong to the machine or account, not the repository.
If `verify-setup.sh` reported any of them unregistered (its checks 2c–2f), name
`<library>/scripts/install.sh --routing` as the one step that registers them.

Say plainly what was not done: declined items, triggers you named and did not act on, commands
you could not run.
