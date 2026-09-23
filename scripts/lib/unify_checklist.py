"""Convert a fenced-shell Audit checklist into the tickable `- [ ]` form.

WHY. Three checklist body formats were in use and invariant 2 gates only the heading. Only
the tickable form is ENUMERABLE, and AUDIT mode instructs the model to "verify your diff
satisfies every item" -- an instruction that cannot be followed against a shell block.

The evidence that this is not cosmetic: a `- [ ]`-only count returned **0 for seven of nine**
skills (recorded in gen-skill-map.py's audit_items docstring), and on 2026-09-22 a
concept-matrix pass mis-parsed fenced blocks and reported `sota-golang` as lacking API/design
probes that its 02-design.md plainly has. Two mechanical readers, two wrong answers, from the
format alone.

WHAT IT DOES, and what it deliberately does not. Inside the `## Audit checklist` section, a
```bash fence becomes bullets: each `#` comment plus the command lines under it is ONE item,
which is the same grouping `extract_items.py` uses. A fence that is not shell (a csproj
snippet, a config sample) is left ALONE -- it is illustrative, not a probe. Prose between
fences is preserved verbatim.

This is a mechanical first pass whose output is REVIEWED, never trusted: it cannot know that
two adjacent comments are really one idea, and it will not invent severity labels that the
source never had.
"""

import re


def _flush(label, cmds, trailing, out):
    """Emit one `- [ ]` bullet from a comment + its commands."""
    if not label and not cmds:
        return
    parts = []
    text = (label or "").strip().rstrip(":")
    if text:
        parts.append(text)
    rendered = []
    for c in cmds:
        c = c.strip()
        if not c:
            continue
        # a trailing `# note` on a command line is explanation, not part of the command
        m = re.match(r'^(.*?)\s{2,}#\s*(.+)$', c)
        if m and not m.group(1).rstrip().endswith("\\"):
            cmd, note = m.group(1).rstrip(), m.group(2).strip()
        else:
            cmd, note = c, ""
        # inline code span: use a longer fence when the command itself contains a backtick
        tick = "``" if "`" in cmd else "`"
        pad = " " if cmd.startswith("`") or cmd.endswith("`") else ""
        rendered.append("%s%s%s%s%s%s" % (tick, pad, cmd, pad, tick,
                                          (" (%s)" % note) if note else ""))
    body = "; ".join(rendered)
    if parts and body:
        line = "- [ ] **%s** — %s" % (parts[0], body)
    elif parts:
        line = "- [ ] **%s**%s" % (parts[0], ("  " + trailing) if trailing else "")
    else:
        line = "- [ ] %s" % body
    out.append(_wrap(line))


# Code spans first, prose second. Counting backticks for parity FAILED on a php probe whose
# command contains a literal backtick -- it is rendered as a ``double-backtick`` span, the
# parity went even mid-span, and the wrapper split the command across two lines. The command
# survived, but as two fragments. So tokenise: a span is atomic and is never broken.
_SPAN = re.compile(r'(``.+?``|`[^`]+`)', re.S)


def _wrap(line, width=96, indent="      "):
    """Wrap at a word boundary. An inline code span is ATOMIC and never split."""
    toks = []
    for part in _SPAN.split(line):
        if not part:
            continue
        if part.startswith("`"):
            toks.append(part)                    # atomic
        else:
            toks.extend(w for w in part.split(" ") if w != "")
    cur, lines = "", []
    for w in toks:
        if cur and len(cur) + 1 + len(w) > width:
            lines.append(cur)
            cur = indent + w
        else:
            cur = (cur + " " + w) if cur else w
    if cur:
        lines.append(cur)
    return "\n".join(lines)


def convert(text):
    """Return (new_text, n_items) -- or (text, 0) if there is nothing to convert."""
    m = re.search(r'(?ms)^(## Audit checklist.*?$)(.*)\Z', text)
    if not m:
        return text, 0
    # THE PREFIX IS EVERYTHING BEFORE THE HEADING, and dropping it truncated six files to
    # their checklists on 2026-09-23 before a single assertion caught it. The item count
    # still matched, so the only signal was the line count -- which is why the guard at the
    # end of this function compares the untouched half byte for byte.
    prefix, head, body = text[:m.start(1)], m.group(1), m.group(2)

    out, i, n = [], 0, 0
    lines = body.splitlines()
    while i < len(lines):
        ln = lines[i]
        fence = re.match(r'^\s*```(\w*)\s*$', ln)
        if not fence:
            out.append(ln)
            i += 1
            continue
        lang = fence.group(1)
        # collect the fence body
        j = i + 1
        block = []
        while j < len(lines) and not re.match(r'^\s*```\s*$', lines[j]):
            block.append(lines[j])
            j += 1
        if lang not in ("bash", "sh", "shell", ""):
            out.extend(lines[i:j + 1])          # not a probe block: leave it be
            i = j + 1
            continue
        # 1. JOIN SHELL LINE CONTINUATIONS. A command split over lines with a trailing `\\`
        #    is ONE command; emitting it as two produced a bullet containing `... || \\` and a
        #    naked `echo` beside it (c/c++ 01, 2026-09-23). 16 such lines across the tier.
        joined, acc = [], ""
        for b in block:
            if acc:
                acc = acc.rstrip()[:-1].rstrip() + " " + b.strip() if acc.rstrip().endswith("\\") else acc + " " + b.strip()
            else:
                acc = b
            if acc.rstrip().endswith("\\"):
                continue
            joined.append(acc); acc = ""
        if acc:
            joined.append(acc)
        block = joined

        label, cmds, in_note = None, [], False
        for b in block:
            s = b.strip()
            # 2. A COMMENT STARTING `^` IS A TRAILING NOTE on the item above, not a new label.
            #    Treated as a label it became the heading of the NEXT probe, attaching an
            #    explanation to a command it does not describe. 16 across the tier.
            # A `^` note runs until the next line that is not an indented continuation.
            # The corpus writes a new label as `# Label` (one space) and a continuation as
            # `#   more text` (two or more), so the indent is the discriminator. Without
            # this, only the note's FIRST line was absorbed and its second became the
            # heading of the next probe.
            if s.startswith("#") and (re.match(r'^#\s*\^', s) or (in_note and re.match(r'^#\s{2,}\S', s))):
                in_note = True
                note = s.lstrip("#").lstrip().lstrip("^").strip()
                if cmds or label:
                    label = ((label + " ") if label else "") + note
                elif out:
                    out[-1] = out[-1].rstrip() + " " + note
                continue
            if s.startswith("#"):
                in_note = False
            if not s:
                _flush(label, cmds, "", out); n += 1 if (label or cmds) else 0
                label, cmds = None, []
                continue
            if s.startswith("#"):
                if cmds:                         # a new comment starts a new item
                    _flush(label, cmds, "", out); n += 1
                    label, cmds = None, []
                label = (label + " " + s.lstrip("# ").strip()) if label else s.lstrip("# ").strip()
            else:
                cmds.append(b)
        if label or cmds:
            _flush(label, cmds, "", out); n += 1
        i = j + 1
    result = prefix + head + "\n".join(out)
    # SELF-CHECK: everything before `## Audit checklist` must be untouched. A converter that
    # rewrites the body of a rules file is a content bug, not a formatting one.
    if not result.startswith(prefix):
        raise AssertionError("converter altered the text before the checklist heading")
    if len(result.splitlines()) < len(prefix.splitlines()):
        raise AssertionError("output is shorter than the prefix alone -- truncation")
    return result, n
