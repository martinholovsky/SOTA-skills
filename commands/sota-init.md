---
description: Set up a repository the way the library expects — inventory what already exists, agree a plan, then add only what is missing (licence, .gitignore and secret scanning, gates, the agent file with this project's own facts, where project data lives), never overwriting a file, and finish with one commit that `git revert` undoes. Safe to re-run in any repository, new or already set up: it adds only what is missing. `/sota-init data` runs only phase 2, the audit and fix of where an existing project's data lives.
---

Set this repository up the way the library expects, adding only what is missing.

This is the day-zero sequence the router offers in one line ("Day zero" in the `sota` skill),
run as one agreed pass. It **adds**; it never overwrites, deletes or rewrites a file that
exists. Everything it writes goes into one commit, so `git revert <sha>` undoes the files.
Hooks it installs outside git are listed at the end with their uninstall command.

**Re-running is safe.** In a repository already set up, the inventory finds each item and the
plan marks it **skip (exists)**; only what is missing is added. The library's own blocks in
an existing agent file and gate config are refreshed only when the user agrees: both
`gen-agents-md.sh` and `init-gates.sh` rewrite only between their markers, and a second run
leaves the file byte-identical and the user's own text and hooks intact (measured 2026-11-25). If
nothing is missing, say so and make no commit.

**Phase 2**, the audit and fix of where an existing project's data lives, is separate and runs
only on request: offered at the end of phase 1, or alone as **`/sota-init data`** (then skip
straight to Phase 2 below). It works under a different contract: it may move and delete data that
git does not hold, each step asked for, and **`git revert` does not undo those moves**.

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
   entries and ask before appending. Add a floor of **operating-system metadata** too, because
   contributors' machines are unknown: `.DS_Store` and `._*` (macOS), `Thumbs.db` and
   `desktop.ini` (Windows), `.directory` and `.Trash-*` (Linux). Do not paste GitHub's whole
   `Global/*.gitignore` templates: the Windows one ignores `*.msi`, `*.cab` and `*.lnk`, and
   the Linux one `*~` and `nohup.out`, so a project shipping an installer stops tracking it.
   Patterns about one person's own tools belong in their `core.excludesFile` (default
   `~/.config/git/ignore`, per `man gitignore`), not here.
2. **Secret scanning and gates**: `<library>/scripts/init-gates.sh --dry-run`, show its output,
   then run it without `--dry-run`. Where a gate config exists, run it only if the user agreed to
   refresh the library's block in the plan. It installs both the pre-commit and pre-push hooks. Install
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
   data already scattered, stop at declaring the places: the audit and any moves are Phase 2,
   offered in the report and run only on a yes.
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

The agent hooks (the zsh command check, the code-rules and action-rules notes, the memory guard,
the per-prompt reminder) are not part of this pass: they belong to the machine or account, not the
repository. If `verify-setup.sh` reported any of them unregistered (its checks 2c–2g), name
`<library>/scripts/install.sh --routing` as the one step that registers them.

Say plainly what was not done: declined items, triggers you named and did not act on, commands
you could not run. If the project already holds data outside git (ignored folders, scratch output
that docs cite, an agent memory store), offer Phase 2 in one line.

---

# Phase 2 — Where project data lives: audit and fix (`/sota-init data`)

Goal: a reboot or routine cleanup loses nothing, and a move to another machine loses only a short,
documented list of machine-bound items. `sota-docs-workflow` rules/06 is the rule (the five
classes, the checks, the Audit checklist); this phase is the order to run them in. Run alone, it
skips step 0, so **invoke the `sota-docs-workflow` skill and read its rules/06, and invoke the
`sota-shell-scripting` skill and read its rules/06, before the first command**: every check here is an absence
claim, and a search that matched nothing reads like a clean repository. Print a count beside
every result and a positive control beside every zero.

**The contract.** Inventory and checks are read only. A move or delete happens one step per
command, each asked for, and only after the map in P3. Ask before deleting anything not clearly
class 3 or 4, touching another project's memory or containers, moving data between volumes, any
security decision (where keys live, what a scanner may skip), and pushing. If the machine is busy
with another project's work, ask before running the suite.

## P0. Discover the environment, and record each answer for the section

- **Path spellings.** Can the project be reached by more than one path (a symlinked parent, a bind
  mount, a mapped drive)? Compare identity, never contents: `[ A -ef B ]`, or `realpath` both. A
  `diff -r` of a folder against itself reports "identical", and an agent that keys memory by path
  sees one project as two.
- **Backup.** What backs the project folder up, and does it skip ignored or cache paths? Ask, then
  check per path with the backup tool's own query where it has one. "It is backed up" is usually
  a belief.
- **Temp lifetimes.** Which temp folders this OS clears and when, and where the agent's scratchpad
  is. Class 4 is defined by what disappears.
- **Agent memory.** Where this agent keeps persistent memory, whether it is keyed by path, and
  whether a setting can name the folder. Read the agent's own documentation; for Claude Code see
  rules/06 §4.
- **Container objects** this project created (compose labels, the volume names in the compose
  file). Other projects may share the runtime: list before touching anything.
- **Interpreters.** Can a system update replace the interpreter a gate uses, taking its installed
  packages with it? Prefer gates on the standard library or a pinned project-local environment.

## P1. Inventory (rules/06 §3)

1. Ignored paths: `git status --ignored=matching --short` (the default form hides folders holding
   only empty directories), `du -sh` each, and a class for each one. Flag any you cannot classify.
2. Ephemeral and home-directory paths in tracked text of every type and in commit messages
   (`git log --all --format=%B`), with a control needle in the same command. Read every hit; it is
   a finding when it says where something is kept.
3. Commands that delete: `clean` targets, cleanup scripts, CI steps, every tracked `rm -rf`, each
   read against the table, and any log pruner checked for cited names.
4. Evidence that exists only in class 4: for every number a tracked doc states, find the run's
   output. Copy it into the repository, compare byte for byte, cite it by name, and **decide its
   class before the copy is done**: class 1, committed, when it is small and holds nothing secret
   or private; class 2, ignored, only when it is too large, private or generated, and then P0's
   backup must cover it. Inside the repository folder but ignored is no safer than outside it.
5. Result files that record an input path: each still exists, or its recorded checksum matches a
   version in history (`git show <c>:<file> | shasum -a 256`) or the generator rebuilds it. Write
   the recovery command beside the result.
6. "Reproducible from …" claims: the copies they name exist, or the claim gets a dated correction.
7. Earlier scratchpads for this project: compare by content and by what produced each file, not by
   name. A run against a mock is disposable; the only copy of a real run is not.
8. Container objects: each is class 3 (with its rebuild command) or class 5 (archived, checksum
   beside it). Never another project's.
9. Secrets: where keys live, whether a token sits in a class-3 folder, and what references it.

## P2. No gate depends on class 3

Run the full suite once with the class-3 items absent (moved out of the tree, or in a fresh
clone). A gate that fails only then depends on class 3: fix the test so it creates or fakes what
it needs, and prove the fix by reverting it once and watching the gate fail. Put the items back and
list them. Also find out whether a gate's input set or the secret scanner covers ignored paths,
because then class-2 and agent files change gate results.

## P3. Agent memory (rules/06 §4)

1. **Map before you touch.** For every path key the agent may use: `ls -ld --`, `readlink --` and
   `realpath --` (keys often start with `-`). Find the ONE real folder and count its files. None,
   or two that differ: stop and ask. "Every key" means every key whose name contains the
   project's, found with the `find` in rules/06 §4, not only the keys the known spellings give: a
   session started in a subfolder or a scratchpad gets its own. A non-empty extra is compared
   with the real store and asked about; an empty one goes on the user's yes with `rmdir --`
   (folder, then key), which refuses anything not empty.
2. **Mechanism, in this order:** a setting that names the folder (Claude Code:
   `autoMemoryDirectory` in `.claude/settings.local.json`, kept out of git through
   `.git/info/exclude` in a repository you do not own); then symlinks from every path key, which
   stay as the fallback wherever the setting may not be honoured.
3. **Path form.** Absolute or `~/`: pick the one with fewer machine-bound dependencies and write
   the reason down. If the project is reached through a symlinked parent, the `~/` form also needs
   that link on a new machine.
4. **If the store must move:** copy into a new folder whose name you checked does not exist, even
   as a link; `diff -r` and count; point the setting or links at it; list it through every key and
   spelling; delete the old folder only on the user's yes, and only after `realpath` shows it is
   not the new one.
5. **Prove it with a differential**, as rules/06 §4 describes: a scratch folder with a canary,
   from every path spelling, headless and interactive, checking the filesystem rather than the
   session's report. The control arm (no setting) is where you see which keys the current version
   actually uses; record them in the report. Remove the scratch folder afterwards.
6. **A guard.** If a hook that asks before `rm`, `mv`, `rmdir`, `unlink` or `ln` on the memory
   folder is installed, prove it is wired: run `rmdir -- <memory-folder>/sota-guard-probe` (a
   folder that does not exist, so nothing is lost if no guard asks), see it ask, and answer no. If
   none is installed, say so in the report and name the library's (`<library>/scripts/install.sh
   --routing` offers it): the incident behind rules/06 §4 happened with the warning already
   written down.

## P4. Paths the project's own tools write into results

Where the project's tools record file paths in results, record them relative to the repository and
print a NOTE (never refuse) when an input or output lies outside it or under a temp folder.
Self-test both cases and mutation-probe the helper.

## P5. Write it down, then prove it holds

- Rewrite the "Where project data lives" section with what was measured: P0's answers, one row per
  class with this project's places, a rebuild command per class-3 entry, the machine-bound list
  with recreate steps, and the move and delete rules (rules/06 §4). Its first line stays the
  trigger. Add a CHANGELOG entry, and fix every current-state doc the change made false.
- Every number this phase writes into the section, the CHANGELOG or a doc comes from a file in
  this session's scratchpad. Before the commit, copy each such working file into the class P1.4
  decides, compare byte for byte, and cite it by name.
- Run the suite and commit, staged by path: the section, and every file this phase placed in
  class 1. List the class-2 files separately with the backup that covers each. Ask before pushing.
- Report, each with its output: the section exists and starts with the trigger; every memory key
  and spelling resolves to the one folder and the agent states that folder; the guard asked (or
  that none is installed); the suite passes with class 3 absent. Every number comes from command
  output with its denominator, and anything not measured says "unverified".
