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
| `CHANGELOG.md` | new `## [X.Y.Z] - YYYY-MM-DD` section at the top **and** a `[X.Y.Z]: …/releases/tag/vX.Y.Z` link ref at the bottom (top entry = current version — no `[Unreleased]` left behind). CHANGELOG is **no longer line-capped** (the 500-line invariant is skill-files-only since 2026-07-15), so archiving old releases is now **optional hygiene** for navigability, not forced: when the root gets long, you *may* move the oldest sections **and their link refs** into the newest `docs/CHANGELOG-archive*.md` (headings and `[X.Y.Z]:` refs must stay in the same file) |

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
  and a table row per new skill. The social-preview `alt` text says **"N+"**
  (a floor, e.g. "40+") — leave it alone unless the tree count falls below
  the floor or you deliberately raise it.
- **Router** (`skills/sota/SKILL.md`): body "A library of N domain skills"
  (N = total − 1), a routing-table row + library-map entry per new skill, and
  the domain list in the frontmatter description — which must stay
  **≤ 1024 characters** (invariant 4; it hit the cap at v1.8.0 and needed a
  trim).
- **`.claude-plugin/marketplace.json`**: counts in the plugin `description`.
- **`assets/social-preview.html`**: the pill reads **"N+ skills"** (a floor —
  "40+" since 2026-07-09) so the image does NOT need re-rendering or
  re-uploading on every skill addition; invariant 6 only fails if the tree
  count drops below the floor. When you *do* raise the floor: re-render the
  PNG by serving the directory over localhost (`python3 -m http.server`) and
  screenshotting at exactly **1280×640** with a headless browser (`file://`
  is typically blocked), commit both files, and re-upload the PNG at GitHub
  **Settings → Social preview** (the repo file does not refresh it).

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
- [ ] If the skill count changed: README badge/hero, router body +
      description, plugin/marketplace.json show the recounted numbers
      (the social-preview pill + README alt are "N+" floors — touch them
      only when deliberately raising the floor, which also means
      re-rendering the PNG)
- [ ] New skills appear in the README table and the router's routing table +
      library map
- [ ] GitHub Settings social-preview re-upload — only if the PNG changed
