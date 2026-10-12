#!/usr/bin/env python3
"""Turn every skill/rules pointer in skills/**/*.md into a relative Markdown link, keeping the
visible text byte-identical. Only the (target) is added. Written for the sota-agent-evals v12
measurement (tools/linkify.py there, tree c127f728...) and used for the library-wide
conversion, ROADMAP 73 (n), 2026-10-12. Re-running it on a converted tree changes nothing.

  `sota-x` rules/06 §3   ->  [`sota-x` rules/06](../../sota-x/rules/06-topic.md) §3
  `rules/04` §1          ->  [`rules/04`](04-topic.md) §1            (own skill)
  `sota-x`               ->  [`sota-x`](../../sota-x/SKILL.md)
  `rules/01-x.md`        ->  [`rules/01-x.md`](rules/01-x.md)        (SKILL.md index)

Untouched: frontmatter, fenced code, existing links, inline code that is not exactly a pointer,
pointers that do not resolve to a file (counted). Usage: linkify-pointers.py ROOT [--check]

REVIEW WHAT IT GUESSES -- the conversion found 22 wrong targets this way, every one of them a
valid path (invariant 8 cannot see a link to the WRONG file, only to a missing one):
  - a bare `rules/NN` is given to the last skill named earlier in its paragraph, as a reader
    would take it; in checklists, tables and "rules/NN here" it means the file's OWN skill;
  - a skill name wrapped across a line (`sota-\n  sandboxing`) is not recognised as a name,
    so the rules/NN after it is attributed to the file's own skill;
  - an unresolved number is skipped and printed; most were a misattribution, not a dead file.
After a run, list every link whose target is a skill other than the one the visible text
names, and read each in context.
"""
import pathlib, re, sys, collections

root = pathlib.Path(sys.argv[1])
check = "--check" in sys.argv
skills_dir = root / "skills"
SKILLS = {p.name for p in skills_dir.iterdir() if (p / "SKILL.md").exists()}
RULES = {s: {f.name[:2]: f.name for f in (skills_dir / s / "rules").glob("*.md")}
         for s in SKILLS if (skills_dir / s / "rules").is_dir()}

NAME = r'sota(?:-[a-z0-9]+)*'
# one alternation; order matters (longest forms first)
POINTER = re.compile(
    r'(?P<span>`(?P<n0>' + NAME + r')/rules/(?P<d0>\d\d)(?:-[a-z0-9-]+\.md)?`)'
    r'|(?P<full>(?P<q1>`?)(?P<n1>' + NAME + r')(?P=q1)(?P<sep>\**\s+\**|/)(?P<q2>`?)rules/(?P<d1>\d\d)(?:-[a-z0-9-]+\.md)?(?P=q2))'
    r'|(?P<own>(?P<q3>`?)rules/(?P<d2>\d\d)(?:-[a-z0-9-]+\.md)?(?P=q3))'
    r'|(?P<name>(?P<q4>`?)(?P<n2>' + NAME + r')(?P=q4))')


def protected(text):
    mask = bytearray(len(text))
    def cover(a, b):
        for i in range(a, b):
            mask[i] = 1
    if text.startswith("---"):
        end = text.find("\n---", 3)
        cover(0, end + 4)
    for m in re.finditer(r'(?ms)^\s*(```|~~~).*?^\s*\1[^\n]*$', text):
        cover(m.start(), m.end())
    for m in re.finditer(r'\[[^\]]*\]\([^)\s]+\)', text):            # existing links, text may wrap
        cover(m.start(), m.end())
    # inline code spans; a span may wrap inside a paragraph, and a one-line regex then pairs
    # every later backtick wrongly and masks real pointers as code (3 were missed that way)
    for m in re.finditer(r'(?<!`)`((?:[^`\n]|\n(?![ \t]*\n))+)`(?!`)', text):
        c = " ".join(m.group(1).split())
        if not re.fullmatch(NAME + r'|rules/\d\d(?:-[a-z0-9-]+\.md)?|' + NAME + r'/rules/\d\d(?:-[a-z0-9-]+\.md)?', c):
            cover(m.start(), m.end())
    for m in re.finditer(r'https?://\S+|[\w.-]*/' + NAME + r'|' + NAME + r'[\w.]*/(?!rules/)', text):  # urls, paths
        cover(m.start(), m.end())
    return mask


def rel(src, skill, target):
    """Path from src's directory to skills/<skill>/<target>."""
    import os
    return os.path.relpath(skills_dir / skill / target, src.parent)


stats = collections.Counter()
changed = 0
for src in sorted(skills_dir.rglob("*.md")):
    me = src.relative_to(skills_dir).parts[0]
    text = src.read_text(encoding="utf-8")
    mask = protected(text)
    out, last = [], 0
    for m in POINTER.finditer(text):
        if any(mask[m.start():m.end()]):
            continue
        g = m.groupdict()
        if g["span"]:
            sk, num, kind = g["n0"], g["d0"], "name+file"
        elif g["full"]:
            sk, num, kind = g["n1"], g["d1"], "name+file"
        elif g["own"]:
            # a bare rules/NN belongs to the last skill named earlier in the same paragraph,
            # as a reader would take it ("sota-code-security (rules/01 SSRF, rules/05 CSP)")
            para = text[max(0, text.rfind("\n\n", 0, m.start())):m.start()]
            prior = [n for n in re.findall(NAME, para[-160:]) if n in SKILLS]
            sk, num, kind = (prior[-1] if prior and not re.search(r'[.;]\s', para[para.rfind(prior[-1]):]) else me), g["d2"], "own rules/NN"
        else:
            sk, num, kind = g["n2"], None, "name"
            if sk == me or sk not in SKILLS or (sk == "sota" and not g["q4"]):
                stats["skip: self/unknown name"] += 1
                continue
        if sk not in SKILLS:
            stats["skip: unknown skill"] += 1
            continue
        if num is not None:
            fn = RULES.get(sk, {}).get(num)
            if not fn:
                stats["skip: unresolved rules/%s in %s" % (num, sk)] += 1
                continue
            target = "rules/" + fn
        else:
            target = "SKILL.md"
        stats[kind] += 1
        out.append(text[last:m.start()])
        out.append("[%s](%s)" % (m.group(0), rel(src, sk, target)))
        last = m.end()
    new = "".join(out) + text[last:]
    if new != text:
        changed += 1
        if not check:
            src.write_text(new, encoding="utf-8")
for k, v in sorted(stats.items(), key=lambda kv: -kv[1]):
    print("%6d %s" % (v, k))
print("files changed: %d" % changed)
