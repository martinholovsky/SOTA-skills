"""Extract every Audit-checklist item from the language tier, as TEXT.

WHY THIS IS SEPARATE FROM gen-skill-map.py's audit_items(). That function returns a
COUNT, and its own docstring warns the two body formats are not comparable -- a checkbox
item can bundle several commands while a fence counts per line. This module answers a
different question: *which concepts are present*, which is format-agnostic, so the
incomparability that blocks counting does not apply to presence.

It also reads what the counter deliberately skips: inside a fenced shell block the
`# comment` lines carry the semantics ("# Owning raw pointers -- MEDIUM") while the
command lines carry the probe. A concept sweep that ignored comments would miss the
meaning of every fence-format skill -- python, jvm, .NET, c/c++, php.

THREE BODY FORMATS, all in use and none gated (invariant 2 gates only the heading):
  tickable      `- [ ]` ...                      rust, js/ts
  fenced shell  ```bash ... ```                  python, jvm, .NET, c/c++, php
  prose+command mixed bullets and fences         golang, ruby
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# The nine language skills, plus shell as a SEPARATE population. LANGUAGE-TIER.md is
# explicit that sota-shell-scripting is not a peer of the tier (different spine), so it
# is carried here as its own group rather than a tenth column -- mixing them would
# manufacture "gaps" that are just a different spine.
LANGS = ["rust", "golang", "c-cpp", "jvm", "python", "javascript-typescript",
         "dotnet", "php", "ruby"]
SHELL = ["shell-scripting"]

LABEL = {"javascript-typescript": "js/ts", "c-cpp": "c/c++", "dotnet": ".NET",
         "golang": "go", "shell-scripting": "shell"}


def label(skill):
    return LABEL.get(skill, skill)


def _checklist_body(text):
    """The text after the LAST '## Audit checklist' heading, or None."""
    m = re.search(r'(?ms)^## Audit checklist.*?$\s*(.*)\Z', text)
    return m.group(1) if m else None


def items_in_file(path):
    """Yield (kind, text) for every actionable item in this file's Audit checklist.

    kind is 'box' (a `- [ ]` bullet with its continuation lines), 'cmd' (a command line
    inside a fence) or 'note' (a `#` comment inside a fence -- the semantic half).
    """
    text = path.read_text(encoding="utf-8")
    body = _checklist_body(text)
    if body is None:
        return

    lines = body.splitlines()
    infence = False
    box = None
    fence_item = None

    for ln in lines:
        stripped = ln.strip()

        if stripped.startswith("```"):
            infence = not infence
            if box:
                yield "box", " ".join(box)
                box = None
            if fence_item:
                yield "cmd", " ".join(fence_item)
                fence_item = None
            continue

        if infence:
            if box:
                yield "box", " ".join(box)
                box = None
            if not stripped:
                continue
            # A `#` comment plus the commands under it is ONE item: the comment carries
            # the semantics ("# Owning raw pointers -- MEDIUM") and the commands carry the
            # probe. Classifying a bare `grep -rnE 'func New\w*...'` on its own is what
            # made this file report go as lacking API-design probes on its first run,
            # while go's 02-design.md plainly has them under Go-specific wording.
            if stripped.startswith("#"):
                if fence_item:
                    yield "cmd", " ".join(fence_item)
                fence_item = [stripped.lstrip("# ").strip()]
            elif fence_item:
                fence_item.append(stripped)
            else:
                # a command with no comment above it: still an item, on its own
                yield "cmd", stripped
            continue

        if fence_item:
            yield "cmd", " ".join(fence_item)
            fence_item = None

        # outside a fence: checkbox bullets, with continuation lines folded in
        m = re.match(r'^\s*- \[ \]\s*(.*)$', ln)
        if m:
            if box:
                yield "box", " ".join(box)
            box = [m.group(1).strip()]
        elif box is not None and stripped:
            box.append(stripped)
        elif box:
            yield "box", " ".join(box)
            box = None

    if box:
        yield "box", " ".join(box)
    if fence_item:
        yield "cmd", " ".join(fence_item)


def skill_items(skill):
    """All items for one skill, as (file, kind, text) tuples."""
    out = []
    rules = ROOT / ("skills/sota-%s/rules" % skill)
    for f in sorted(rules.glob("*.md")):
        for kind, text in items_in_file(f):
            out.append((f.name, kind, text))
    return out


def all_items(skills):
    """{skill: [(file, kind, text), ...]}"""
    return {s: skill_items(s) for s in skills}
