# Contributing to SOTA-skills

Thanks for helping improve the library. SOTA-skills is a collection of Markdown
skills that an AI assistant reads to build and audit software using
state-of-the-art practices. There is no code to run — contributions are edits to
Markdown, held to a few hard invariants.

By contributing you agree your contribution is licensed under
[CC BY 4.0](LICENSE), the same as the rest of the library.

## Ground rules

1. **Keep it generic.** The library must apply to anyone. Do not hard-code one
   person's or company's stack, project names, or infrastructure. Name products
   only as neutral *examples* ("e.g. PostgreSQL"), never as an assumption about
   the reader ("you run PostgreSQL"). Personalization belongs in a local
   `profiles/<you>.md`, which is git-ignored and never committed.
2. **Verify every claim.** Fast-moving facts (versions, specs, advisories,
   regulations) must be checked against a **primary source** — a spec, vendor
   doc, CVE/CWE, or official release — and cited. Prefer "needs verification"
   over a confident guess. The library's value is that its claims hold up.
   Corollary — **no rot-prone version pins**: never write "the current release
   is X.Y"; say "latest stable, verify at the official source". Version
   numbers are for semantic boundaries only ("GA since", "fixed in", CVE fix
   versions, spec editions). Recommend maintained tools; when one goes EOL,
   point at its maintained successor and keep a one-line EOL note.
3. **Stay lean.** Every Markdown file is **≤ 500 lines** so skills load
   incrementally without blowing the context window. If a topic outgrows that,
   split it into another `rules/NN-topic.md`.

## Repository layout

```
skills/
  sota/                       # master router — routing + operating principles
  sota-<domain>/
    SKILL.md                  # when-to-use, BUILD/AUDIT workflows,
                              # top-10 non-negotiables, rules index
    rules/
      01-<topic>.md           # ≤500 lines, ends with "## Audit checklist"
      02-<topic>.md
profiles/
  example.md.template         # copy to profiles/<you>.md (git-ignored)
scripts/check-invariants.sh   # the invariants below, enforced
AGENTS.md                     # guidance for AI assistants working on the repo
                              # (CLAUDE.md and GEMINI.md are symlinks to it)
```

## Anatomy of a skill

**`SKILL.md`**

- YAML frontmatter with exactly two fields: `name` and `description`. If the
  description contains a colon, use a block scalar (`>` or `|`) so the YAML stays
  valid. Per the [Agent Skills spec][skills-spec], `name` is ≤ 64 chars
  (lowercase, digits, hyphens) and `description` is **≤ 1024 characters** — a
  loader skips any skill whose description exceeds the cap, so keep it tight
  (trim prose before trigger keywords). Enforced by invariant 4 below.
- A `description` that says *when* to use the skill (BUILD and AUDIT triggers)
  and a list of trigger keywords — Claude Code matches prompts against this.
- Body: a short "when to use", a **BUILD** workflow and an **AUDIT** workflow, a
  **top-10 non-negotiables** list, and a **rules index** table pointing at the
  `rules/` files.

**`rules/NN-topic.md`**

- Roughly 80–350 lines of concrete, current guidance with short examples
  (a target, not a floor — compact rules files are fine; the hard cap is 500).
- Ends with an **`## Audit checklist`** — yes/no questions, ideally with
  grep/lint patterns, so the rule can be used to hunt violations.
- Fast-moving claims must be verified against primary sources when written.
  Library-wide re-verification is tracked by the root **`LAST-VERIFIED`** file
  (YYYY-MM-DD of the last full-library sweep: per-skill research against
  primary sources, findings adversarially verified, fixes applied). Update it
  only after such a sweep — not on ordinary edits. A monthly CI job
  (`scripts/check-freshness.sh`) goes red when the stamp exceeds the
  re-verify window (**6 months**). Do not add per-file `<!-- last-verified -->`
  line-1 markers (retired convention; the script warns about strays). The
  step-by-step sweep runbook is [docs/MAINTENANCE.md](docs/MAINTENANCE.md).

**Findings format** (AUDIT mode, used throughout):

```
file:line | rule violated | severity | effort | fix
```

- Severity: **Critical** · **High** · **Medium** · **Low** · **Info**
- Effort: **trivial** · **small** · **medium** · **large**

Borderline severities should state the deciding assumption; unconfirmed findings
are marked "needs verification", never asserted.

## The invariants (enforced)

`scripts/check-invariants.sh` runs in pre-commit and CI and fails the build on:

1. any tracked `*.md` over **500 lines**;
2. any `skills/*/rules/*.md` that doesn't **end** with an
   **`## Audit checklist`** (it must be the file's last `## ` heading);
3. any **internal/private reference** leaking into tracked files (the private
   pattern list is intentionally not in the repo; PRs from forks run the
   generic checks and the maintainer's CI runs the full list);
4. any `skills/*/SKILL.md` `description` over **1024 characters** (the Agent
   Skills cap) or written as an unquoted inline scalar containing `: ` —
   invalid YAML that makes loaders skip the skill; use `description: >-`.
   (Check 4 needs `python3`, and is skipped with a warning if it is absent
   locally — CI always enforces it.)
5. **version drift**: `VERSION`, `plugin.json`, and the CHANGELOG top entry
   must agree; the newest `v*` tag must never be ahead of `VERSION`;
6. **count drift**: the exact-count surfaces (README badge/hero, router body,
   plugin/marketplace descriptions) must match a recount of the `skills/`
   tree — adding or removing a skills file means updating them in the same
   PR. The social-preview pill and README alt carry an **"N+" floor** instead
   (checked only against dropping below it), so the image needs no per-release
   re-render.
7. **router drift**: every domain skill must appear in the router's routing
   table AND its library map (both in `skills/sota/SKILL.md`) — adding a skill
   means updating both.

Secrets are scanned separately by **gitleaks** (config in `.gitleaks.toml`);
CI scans the full git history, the pre-commit hook scans each commit.

[skills-spec]: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

## Local setup

```sh
pipx install pre-commit     # or: brew install pre-commit
pre-commit install          # run the same checks on every commit
```

(`scripts/install.sh` also checks for the hook when run from a checkout and
offers to install it, or prints this tip if the `pre-commit` tool is missing.)

Run the invariant checks any time:

```sh
./scripts/check-invariants.sh
```

## Submitting a change

1. Fork and branch (`git checkout -b improve-sota-databases-indexing`).
2. Make the edit; keep diffs focused (one skill / one concern per PR).
3. Run `pre-commit run --all-files` (or at least `./scripts/check-invariants.sh`).
4. Open a PR describing **what** changed, **why**, and **how the claims were
   verified** (cite sources for any new version/spec/advisory claim).

### PR checklist

- [ ] Stays generic — no personal/company stack, project names, or "you run X".
- [ ] New fast-moving claims cite a primary source.
- [ ] Every touched `rules/*.md` still ends with `## Audit checklist`.
- [ ] All touched files are ≤ 500 lines.
- [ ] No secrets in examples (masked/placeholder only).
- [ ] `pre-commit` / `scripts/check-invariants.sh` passes.

## Adding a whole new skill

Same structure: a `skills/sota-<domain>/` folder with a `SKILL.md` (two-field
frontmatter, BUILD/AUDIT workflows, top-10, rules index) and `rules/NN-*.md`
files each ending in an audit checklist. Add the skill to the router
(`skills/sota/SKILL.md`) routing table and to the table in `README.md`. Open an
issue first if you want to discuss scope.

## Questions

Open an issue. For anything security-sensitive (bad security guidance, or a real
secret accidentally committed), follow [SECURITY.md](SECURITY.md) instead.
