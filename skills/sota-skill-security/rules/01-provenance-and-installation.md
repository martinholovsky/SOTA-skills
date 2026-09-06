# Provenance and installation — deciding what earns a place in the context

Everything here is the dependency-management playbook, applied to a dependency that
executes in the model instead of the interpreter. The difference that matters:
**a package must be called; a skill only has to be loaded.**

---

## 1. Provenance before content, and licence before both

Before reading what a skill *says*, establish what it *is*:

- **Who publishes it, at what identity.** A GitHub account, an org, a marketplace
  entry. Note that an org name is not an identity claim — anyone can create
  `acme-security-tools`.
- **The licence.** This is not bureaucracy: an unlicensed public repository grants
  you no right to copy its text. You may take the *idea class*; you may not vendor
  the prose. Notes-on-a-book repositories are frequently both unlicensed and
  derivative, and are the commonest trap.
- **The age and the pulse.** A skill last touched two years ago pinning a tool
  version that has since had a CVE is not neutral — it is confidently wrong
  (`rules/03` §2).

Read these from the API or the repository, **not from the page that recommended
it**. A recommendation is a claim about a skill, and this whole file is about not
accepting claims.

## 2. Pin it, and treat the description as the interface

**A skill installed from a branch re-installs itself on every pull.** Pin a commit
SHA or a tag. If the platform's install mechanism cannot pin, record the SHA you
reviewed somewhere you will diff against.

On update, **diff before adopting**, and weight the diff by where it lands:

| Changed | Why it matters |
|---|---|
| **the `description` / trigger text** | **highest.** On platforms where a skill auto-loads, the description is the *entire* classifier and the body is inert until it fires. A description change silently changes *when* the skill applies — the one change that alters behaviour without altering a single rule |
| a rule's prescription | ordinary content review |
| an added script or resource | re-run the closure review (§3) |
| the licence | re-run §1 |

**A skill that changed its own trigger is the shape to look for.** Broadening a
description is how a narrow skill starts loading everywhere; narrowing one is how a
skill you depend on silently stops applying.

## 3. Review the closure, not the entry point

The review unit is everything that reaches the model or the machine because you
installed this:

- the entry file **and every file it references** — a `SKILL.md` that says "see
  `rules/07`" has a body you have not read;
- **scripts** shipped alongside, including hooks and install scripts;
- **resources fetched at load or run time** — a skill that pulls a remote ruleset is
  a skill whose content is not what you reviewed;
- **transitively installed things**: an MCP server the skill tells you to add, a
  plugin it depends on.

The failure is not exotic. It is that you read a well-written `SKILL.md`, and the
part that mattered was in a file you did not open.

**If the closure cannot be enumerated, that is the finding.** A skill that fetches
guidance at runtime cannot be reviewed, only trusted.

## 4. Inventory what actually loads — not what is documented

Before auditing content, establish the set. Agents load instructions from more
places than people remember:

- global/user config (an always-on agent file);
- project files — `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.cursorrules` and their
  kin, **including symlinks between them**, where one file is three entry points;
- a skills or plugins directory, and anything symlinked into it;
- marketplace or plugin manifests;
- nested per-directory files, which may exist in a subtree you did not write.

**Enumerate by looking, not by asking the docs.** The gap between "what we install"
and "what loads" is exactly where an unreviewed file lives. For each entry record:
source, pinned version, date a human last read the diff, and whether it can execute
or fetch.

"Installed from a link someone posted in chat" is a finding, not a provenance.

## 5. The marketplace is a distribution channel, not a review

An entry appearing in a curated list means someone thought it was useful. It does
not mean anyone read it adversarially, and it does not mean the version you install
today is the version that was listed. Treat a listing as discovery and do §1–§3
anyway.

---

## Audit checklist

- [ ] **Inventory taken by looking** (§4) — every path an agent loads instructions
      from, including symlinks and per-directory files, with source and pinned
      version recorded? A set assembled from documentation rather than the
      filesystem is not an inventory.
- [ ] **Every installed skill pinned** to a SHA or tag, not tracking a branch (§2)?
      Anything tracking a branch re-installs on every pull and is a standing finding.
- [ ] **Update diffs read, weighted by surface** (§2) — and a change to a
      **description/trigger** treated as a behaviour change rather than a docs edit?
- [ ] **Closure reviewed, not just the entry point** (§3): referenced files, shipped
      scripts, fetched resources, transitively installed servers? Any skill whose
      closure cannot be enumerated flagged as unreviewable.
- [ ] **Licence established before any text was reused** (§1), and idea-vs-text
      distinguished for unlicensed sources?
- [ ] **Publisher identity and pulse recorded** (§1) — a stale skill pinning tool
      versions with known advisories treated as wrong, not neutral?
- [ ] No entry whose provenance is "someone recommended it" (§1, §5)?
