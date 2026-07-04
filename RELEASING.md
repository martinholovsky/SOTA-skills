# Releasing

How to cut a SOTA-skills release. Adding a skill is a **minor** bump (the
library only ever adds); fixes to existing content are a **patch**. Everything
lands through a PR — `main` is protected for everyone, including admins (see
[AGENTS.md](AGENTS.md)).

## 1. Version-bearing files (every release)

| File | What changes |
|---|---|
| `VERSION` | the new semver, single line |
| `.claude-plugin/plugin.json` | `"version"`; also the skill/domain counts in `"description"` if they changed |
| `CHANGELOG.md` | new `## [X.Y.Z] - YYYY-MM-DD` section at the top **and** a `[X.Y.Z]: …/releases/tag/vX.Y.Z` link ref at the bottom (top entry = current version — no `[Unreleased]` left behind); when the file nears the 500-line cap, move the oldest release sections **and their link refs** to `docs/CHANGELOG-archive.md` |

## 2. Count-bearing surfaces (when the skill count changes)

Recount from the tree — never adjust numbers by memory (invariant 6 fails CI
on drift among these surfaces, and invariant 5 on version drift):

```sh
ls -d skills/*/ | wc -l                          # N skills (incl. router)
find skills -name '*.md' | wc -l                 # M files
find skills -name '*.md' -exec cat {} + | wc -l  # ~L lines
```

Then update every surface that carries a count:

- **README**: badge `skills-N`, hero sentence "N skills (M files, ~Lk lines)",
  social-preview `alt` text, and a table row per new skill.
- **Router** (`skills/sota/SKILL.md`): body "A library of N domain skills"
  (N = total − 1), a routing-table row + library-map entry per new skill, and
  the domain list in the frontmatter description — which must stay
  **≤ 1024 characters** (invariant 4; it hit the cap at v1.8.0 and needed a
  trim).
- **`.claude-plugin/marketplace.json`**: counts in the plugin `description`.
- **`assets/social-preview.html`**: the "N skills" pill — the *only* count in
  the image by design (the tagline is deliberately count-free; the pill sat
  stale at "30 skills" for three releases before v1.8.0). Re-render the PNG:
  serve the directory over localhost (`python3 -m http.server`) and
  screenshot at exactly **1280×640** with a headless browser — `file://` is
  typically blocked. Commit both files.
- GitHub **Settings → Social preview** is a separate manual upload — updating
  `assets/social-preview.png` in the repo does **not** refresh it; re-upload
  the new PNG there.

## 3. Land the PR

```sh
./scripts/check-invariants.sh        # same checks as CI
git checkout -b <branch> && git commit && git push
# open the PR; both required checks green → squash-merge
```

## 4. Tag and publish (after the squash-merge)

```sh
git checkout main && git pull --ff-only
git tag -a vX.Y.Z -m vX.Y.Z && git push origin vX.Y.Z
# release notes = the [X.Y.Z] section of CHANGELOG.md
gh release create vX.Y.Z --title vX.Y.Z --notes-file <notes>
```

Plugin installs pick the release up because the `plugin.json` version bumped
(`/plugin update sota-skills@sota-skills`); symlinked clone installs update on
`git pull`, and `./scripts/install.sh --update` also links any brand-new
skills.

## Pre-tag checklist

- [ ] `./scripts/check-invariants.sh` passes
- [ ] `VERSION` == `plugin.json` version == the tag you're about to push
- [ ] CHANGELOG top entry is the new version, dated, with its link ref
- [ ] If the skill count changed: README badge/hero/alt, router body +
      description, marketplace.json, social-preview pill + regenerated PNG
      all show the recounted numbers
- [ ] New skills appear in the README table and the router's routing table +
      library map
- [ ] GitHub Settings social-preview re-upload done (or consciously deferred)
