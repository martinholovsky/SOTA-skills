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
| **1 Tracked** | code, docs, test data, small reference results | only by a commit | anything a doc, commit, handoff or result **cites** is here, or its exact regenerate command is written beside the citation |
| **2 Kept, not committed** | outputs too large, private or generated to commit that must survive: evidence, run outputs with payloads, large results, the agent memory you keep | never without the owner | it is backed up per the owner's policy, or the declaration says it is not |
| **3 Rebuildable** | derived and disposable: virtual environments, caches, build output | freely | each has a rebuild command; **no test or gate depends on it**; no long-lived secret sits in it |
| **4 Ephemeral** | session scratch: `/tmp`, `$TMPDIR`, an agent's scratchpad | expected to vanish (on reboot, or when the session ends) | **never cited** in a doc, commit or result; anything worth keeping is copied to class 1 or 2 before the session ends |
| **5 External by design** | data that lives elsewhere on purpose: image archives (with a checksum beside each), keys in a secret manager, a dataset on a platform | per its owner | named by path or URI in the declaration |

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
  Markdown as well, with a control needle you know is present in the same command. A hit in a doc,
  a result file or a commit message is a finding. A hit in code that creates its own temp
  directory is not.
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
- **A guard on the store beats a note about it.** A pre-command hook that asks before any
  `rm`/`mv`/`ln` naming the memory folder is the structural form of this section, for the same
  reason the reminder-style rule failed.

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
- [ ] **Moves and deletes of kept data were mapped first** (§4): source and destination were
      checked with `ls -ld --` and `readlink --`, the data was copied, compared and counted before
      anything was removed, and no `rm -r` named a symlink with a trailing slash.
