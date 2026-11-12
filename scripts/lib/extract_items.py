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

HISTORICAL NOTE: three body formats were once in use (tickable, fenced shell, and a third
misread as prose+command). Since 2026-09-23 every skill's checklist is tickable, and
`gen-concept-matrix.py --assert-format` fails any rules file that is not, including one
that yields ZERO items. Plain `- ` bullets read as zero items here, so the gate needs that
second arm. The fence branch below is kept so the gate can still NAME a regression.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# The language skills, plus shell as a SEPARATE population. LANGUAGE-TIER.md is
# explicit that sota-shell-scripting is not a peer of the tier (different spine), so it
# is carried here as its own group rather than another column -- mixing them would
# manufacture "gaps" that are just a different spine.
#
# LANGS is READ from scripts/gen-skill-map.py, never restated here. Until 2026-11-12 this file
# kept its own copy while invariant 36 checks only gen-skill-map.py's, so a language added to
# that list and the router passed invariant 36 while gen-concept-matrix.py (which reads THIS
# module) never held it to UNIVERSAL_FLOOR: adding "zig" to gen-skill-map.py on a disposable
# copy left --assert-universal at ten columns, exit 0. One source makes the gap impossible.
def _registered_langs():
    import ast
    src = (ROOT / "scripts" / "gen-skill-map.py").read_text(encoding="utf-8")
    # Exactly one top-level assignment: a later `LANGS += [...]` or a second `LANGS =` (even in a
    # docstring) was silently ignored or read instead -- shown on a disposable copy, 2026-11-12.
    if len(re.findall(r'^LANGS\s*(\+?=)', src, re.M)) != 1:
        raise SystemExit("extract_items: scripts/gen-skill-map.py must assign LANGS exactly once, "
                         "as one list literal")
    m = re.search(r'^LANGS\s*=\s*(\[[^\]]*\])', src, re.M)
    if not m:
        raise SystemExit("extract_items: LANGS not found in scripts/gen-skill-map.py")
    langs = ast.literal_eval(m.group(1))
    if not langs or not all(isinstance(x, str) for x in langs):
        raise SystemExit("extract_items: LANGS in scripts/gen-skill-map.py is empty or malformed")
    return langs


LANGS = _registered_langs()
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


def all_rules_dirs():
    """Every `skills/*/rules` directory -- the router's own included."""
    return sorted(d for d in (ROOT / "skills").glob("*/rules") if d.is_dir())


def all_items(skills):
    """{skill: [(file, kind, text), ...]}"""
    return {s: skill_items(s) for s in skills}
