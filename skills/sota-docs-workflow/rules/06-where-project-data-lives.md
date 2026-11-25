# 06 — Where project data lives: declare the places, then check that nothing points elsewhere

Scope: everything a project produces or depends on that version control does not hold. That means
run outputs, evidence, large results, caches, scratch files, keys, archives, and an agent's memory.
Left undeclared, each session invents its own place. Then a reboot, a new machine or a cleanup
loses the one copy that a document still cites.

**This file defines classes and checks, not locations.** Where each class lives is the
project's decision, or the organisation's. It can be an ignored folder in the repository, an
artifact store, an object-storage bucket, a shared volume or a data platform. A company may
forbid local copies of some data altogether: classification and retention decide that
([`sota-privacy-compliance` rules/01](../../sota-privacy-compliance/rules/01-data-inventory-classification.md) §2,
[rules/03](../../sota-privacy-compliance/rules/03-consent-and-user-rights.md) §6). An
organisation-wide default belongs in the stack profile (`~/.claude/profiles/*.md`, router
principle 4), and a project's own declaration overrides it. **Where neither exists, do not invent
a layout silently.** Ask, or use the repository-local default in §2, say once that you did, and
record it.

## 1. Five classes, defined by what may happen to them

| Class | What it holds | May it be deleted? | Rule that holds wherever it lives |
|---|---|---|---|
| **1 Tracked** | code, docs, test data, small reference results | only by a commit | anything a doc, commit, handoff or result **cites** is here, or in class 2 under a name that keeps it, or its exact regenerate command is written beside the citation |
| **2 Kept, not committed** | outputs too large, private or generated to commit that must survive: evidence, run outputs with payloads, large results, failure logs a doc cites, a fuzzer's crash reproducers, the agent memory you keep | never without the owner | it is backed up per the owner's policy, or the declaration says it is not; **no cleanup command deletes it wholesale**, because one folder often holds cited and uncited files side by side |
| **3 Rebuildable** | derived and disposable: virtual environments, caches, build output, generated files, dev-database volumes | freely | each has a rebuild command; **no test or gate depends on it**; no long-lived secret sits in it |
| **4 Ephemeral** | session scratch: `/tmp`, `$TMPDIR`, an agent's scratchpad | expected to vanish (on reboot, or when the session ends) | **never cited** in a doc, commit or result; anything worth keeping is copied to class 1 or 2 before the session ends |
| **5 External by design** | data that lives elsewhere on purpose: image archives (with a checksum beside each), keys in a secret manager, VM disks, a dataset on a platform | per its owner | named by path or URI in the declaration |

Two placements are easy to get wrong. **A fuzzer's crash reproducer is class 2, not 3**: re-running
the fuzzer does not reliably find the same input, so the file is the only copy of a finding until it
becomes a regression test (field-reported 2026-11-25: an `artifacts/` folder declared rebuildable).
**Citing a class-2 file by its name is allowed** when the name is stable and the folder is never
wiped wholesale (field-reported 2026-11-25: a run summary that existed only in a scratchpad was
copied into `evidence/`, compared byte for byte, and cited by name). **Moving a file into the
repository does not keep it; its class does.** Commit it (class 1) when it is small and holds
nothing secret or private. Ignore it (class 2) only when it is too large, private or generated,
and then the declared backup must cover that path, because an ignored file inside the repository
is lost with the working tree like any other.

Add a **machine-bound** list: what does not travel with the project to a new machine. Examples
are agent configuration and hooks, credentials, CLI logins, container-runtime registration, and
path symlinks. Give the steps to recreate each one. Secrets in classes 2–5 follow
[`sota-secrets-management`](../../sota-secrets-management/SKILL.md); the class only says where a
reference to the secret lives.

## 2. Declare it where agents and people will read it

Put a section titled **"Where project data lives"** in the file every session loads (`AGENTS.md`,
or the project's `CLAUDE.md`). Its **first line states when it applies**, so a session follows it
without being told: *"Before creating, moving or deleting project data or agent memory, place it by
this table and follow the move/delete rules below."* Then give one row per class with the
project's actual places, the machine-bound list, and the rebuild command for each class-3 entry.

The repository-local default, for when nothing else is declared: class 2 in an ignored folder named
for its contents (`evidence/`, `runs/`, `results/`), class 3 in ignored tool folders (`.venv/`,
`.cache/`), class 4 left where the tool puts it. Excluding a folder from git is a choice too.
Personal working files belong in `.git/info/exclude`, not the tracked `.gitignore`, when the
repository is not yours.

## 3. Audit: things that point at places nobody keeps

Each check below is location-agnostic. It holds whatever the declaration says.

- **Ephemeral paths in tracked text of every type**, not just code: `/tmp`, `/private/var`,
  `/var/folders`, `$TMPDIR`, a scratchpad, a home directory. Search JSON, YAML, TOML, shell and
  Markdown as well, and commit messages, with a control needle you know is present in the same
  command. Read every hit: it is a finding when it says **where something is kept** (a doc, a
  result or a commit message pointing at the only copy). Code that creates its own temp directory
  is not one, and neither is quoted output that merely contains such a path, such as a kernel
  message from a VM.
- **Commands that delete.** `clean` targets, cleanup scripts, CI steps and every `rm -rf` in tracked
  files, each checked against the declaration. Declaring a class does not change the command
  (field-reported 2026-11-25: two days after a folder was declared class 2, `make clean` still ran
  `rm -rf` on it, cited logs included). A pruner that caps a log archive skips the names a doc cites
  (field-reported 2026-11-23: a cap of N per gate had deleted 7 of the 21 logs tracked docs cited).
- **Evidence that exists only in class 4.** For each number or result a tracked doc states, find
  the run's output. A copy found only in a scratchpad or temp folder moves to class 2 now: copy it,
  compare it byte for byte, and cite it by name. A ledger that refuses failed runs is the usual
  cause (field-reported 2026-11-25).
- **Ignored folders `git status --ignored` does not show.** A folder holding only empty directories
  is hidden from the default listing; `git status --ignored=matching` lists it (measured
  2026-11-25, git 2.55.0). A fuzzer's `artifacts/` stays empty until the day it finds a crash.
- **"Reproducible from …" claims.** A doc saying a result can be rebuilt from scratch or temp copies
  is an absence-of-loss claim: check that the copies exist. Correct the claim with a dated note if
  they do not.
- **Result files that record an input path.** Each recorded file still exists, or its recorded
  checksum matches a version in history (`git show <commit>:<file> | shasum -a 256`) and the
  regenerate command sits beside the result.
- **A gate that passes only because a class-3 file happens to exist.** Move the file aside, re-run
  the gate, and watch it fail. Fix the test so it creates or fakes what it needs, then prove the fix
  by reverting it once ([`sota-testing` rules/06](../../sota-testing/rules/06-property-fuzzing-mutation.md)
  §6.3). Field-reported 2026-11-23: an adapter self-test passed only because a git-ignored token
  file was present on the developer's machine.
- **What the gates hash or scan.** If a gate's input set or a secret scanner covers ignored paths,
  class-2 and agent files can change its result. Know which way yours goes before writing there.
- **Rebuild commands that rebuild.** Run one class-3 rebuild in a clean checkout.
- **Facts about the repository held only in an agent's memory**: [`sota` rules/01](../../sota/rules/01-audit-methodology.md) §4a.

## 4. Moving or deleting kept data and agent memory

Kept data is often reached through symlinks that earlier sessions made. An agent's memory store is
keyed by path, so one repository reached by two path spellings (through a symlinked parent) gets
two keys, and often a link from one to the other. Field-reported 2026-11-23: a "move the memory
into the repository and symlink it" step ran `mv` onto a path that was already a symlink, and the
following `rm -r` deleted the only real copy of a project's notes. It came back only from a backup.

- **Map before you touch.** Run `ls -ld --` and `readlink --` on the source **and** the destination,
  and `realpath` to find the one real folder. Count its files. Names that start with `-` (agent
  memory keys often do) need `--` or a `./` prefix
  ([`sota-shell-scripting` rules/02](../../sota-shell-scripting/rules/02-robustness-correctness.md)).
- **Copy, compare, count, list through every path that should see it, and only then remove.** Run one
  destructive step per command. Gate it with `if …; then …; else echo STOP; exit 1; fi`, never a
  bare `[ … ] && [ … ]` under `set -e`
  ([`sota-shell-scripting` rules/01](../../sota-shell-scripting/rules/01-safety-baseline.md) §2).
- **`mv`, `ln -s` and `rm -r link/` act on the target of a symlink to a directory**, on BSD and GNU
  alike: [`sota-shell-scripting` rules/08](../../sota-shell-scripting/rules/08-ad-hoc-side-effects.md) §3c.
- **Claude Code can point the store at a folder you choose.** `autoMemoryDirectory` in the project's
  `.claude/settings.local.json` (excluded from git) names the memory folder.
  - *Measured:* 2026-11-24 with Claude Code 2.1.331, headless: the session reported that path and
    wrote its memory there, none under the per-path key. Field-reported 2026-11-25 with 2.1.332, as
    a differential (no setting; a scratch folder seeded with a canary; the real folder): the canary
    loaded and a new memory was written only to the scratch folder, from both path spellings of one
    repository, headless and interactive. An interactive session started before the setting existed
    named the per-key **symlink** path, so the harness does not resolve the link when it prints it.
  - *From the docs, not run* (code.claude.com/docs/en/memory, fetched 2026-11-25): the value "must be
    an absolute path or start with `~/`"; it needs v2.1.234 or later; a project-level value is
    honoured "under the same workspace trust rule as hooks"; and while
    `permissions.blockReadsOutsideWorkingDirectories` is on, a repository-chosen folder is neither
    loaded nor written.
  - *Not measured:* other agents' equivalents.
  - **Keep the per-spelling links as a fallback** where they exist: the setting is not honoured in an
    untrusted folder, under that read block, or before v2.1.234, and then the links are what point
    the store at the one folder. The folder is class 2 like any other kept data.
  - **Prove it with a differential, not one reading.** When links and setting point at the same
    folder, every reading agrees whichever mechanism chose it. Point the setting at an empty scratch
    folder seeded with a canary line, start a session from every path spelling, and check the
    filesystem: the canary is quoted, a new memory lands only there, and the real store is
    unchanged. Then point it back.
- **A guard on the store beats a note about it.** A pre-command hook that asks before any
  `rm`/`mv`/`ln` naming the memory folder is the structural form of this section, for the same
  reason the reminder-style rule failed. The library ships one for Claude Code
  (`scripts/memory-guard-hook.py`, offered by `install.sh --routing`, registered by the plugin):
  it guards the per-path keys, the real folders behind them and any `autoMemoryDirectory` folder.

## Audit checklist

- [ ] **The project declares where its data lives** (§1, §2): the agent file carries a "Where project
      data lives" section whose first line says when it applies, with one row per class, a
      machine-bound list, and a rebuild command for every class-3 entry. Or the stack profile
      declares it organisation-wide. Without either, the finding is the missing declaration, not a
      layout you prefer.
- [ ] **No tracked doc, result or commit message cites an ephemeral path** (§3): search every file
      type for `/tmp/`, `/private/var/`, `/var/folders/`, `$TMPDIR` and scratchpad paths, for
      example `git grep -n -I -E '/tmp/|/private/var/|/var/folders/|scratchpad'`, with a control
      needle you know is present, and read each hit.
- [ ] **No gate depends on a class-3 file** (§3): moving the file aside makes the gate fail, and
      the test was fixed to fake it (with the fix itself watched failing once).
- [ ] **Recorded input paths resolve** (§3): every path a result file records exists, or its
      checksum matches a version in history and the regenerate command is beside the result.
- [ ] **No command deletes class-2 data wholesale** (§1, §3): every `clean` target, cleanup
      script, CI step and tracked `rm -rf` was read against the declaration, and any log pruner
      skips the files a doc cites.
- [ ] **No cited result exists only in class 4** (§3): each number a tracked doc states has its
      run output in class 1 or 2, copied, compared byte for byte and cited by name.
- [ ] **The ignored-path inventory used `git status --ignored=matching`** (§3), so folders
      holding only empty directories were classified too, and fuzzer crash reproducers are
      class 2 (§1).
- [ ] **A memory-folder setting was proven by a differential** (§4): a scratch folder with a
      canary, from every path spelling, with the real store unchanged; the per-spelling links
      kept as the fallback where they exist.
- [ ] **Moves and deletes of kept data were mapped first** (§4): source and destination were
      checked with `ls -ld --` and `readlink --`, the data was copied, compared and counted before
      anything was removed, and no `rm -r` named a symlink with a trailing slash.
