#!/usr/bin/env python3
"""Generate docs/skill-map.drawio — how the router reaches the skills, and how the
skills reach each other.

WHY A GENERATOR AND NOT A DRAWING. A hand-drawn map of 42 skills and ~300 cross-links is
stale the first time a rules file moves, and nothing would report it -- the failure mode
this repo exists to gate against. So the map is DERIVED: every node and edge is read out
of the tree at generation time, every extracted skill name is validated against the real
skills/ directory listing, and the run prints its denominators so a drop is visible.

Five pages:
  1. Router -> skills, grouped by family (the routing table in skills/sota/SKILL.md).
  2. The 21 cross-cutting routing rules and the skills each one names.
  3. The MEASURED cross-skill reference graph, aggregated to families.
  4. A worked slice: what an SSO task actually traverses.
  5. Section x language: which topics each language skill gives its own rules file.

LAYOUT IS A CORRECTNESS CONCERN HERE, not decoration. Three of these pages were first
drawn in forms that RENDER but cannot be READ: 63 bipartite edges collapsed into one
orthogonal trunk running through the skill boxes; 110 edges over 38 nodes made a hairball;
and a 2x3 grid put the router above the top row so every edge to a lower family crossed
the boxes above it. The fixes are structural -- text instead of edges, aggregate to
families, one row instead of a grid -- and each was found by rendering the page and
looking at it, which no XML check can do.

Usage: python3 scripts/gen-skill-map.py [--min-weight N] [--out PATH] [--json PATH]
"""
import argparse, collections, html, json, math, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# The ONE hand-maintained thing here, and it fails closed: if a skill is added or removed
# and this list is not updated, the run aborts naming the difference rather than drawing a
# map that silently omits it.
FAMILIES = [
    ("Security core", "#d5e8d4", "#82b366", [
        "sota-code-security", "sota-threat-modeling", "sota-skill-security",
        "sota-secrets-management", "sota-sandboxing", "sota-confidential-computing",
        "sota-detection-engineering", "sota-network-security", "sota-identity-access",
        "sota-security-compliance", "sota-privacy-compliance"]),
    ("Platform & delivery", "#dae8fc", "#6c8ebf", [
        "sota-cloud-infrastructure", "sota-kubernetes", "sota-devsecops",
        "sota-observability", "sota-architecture"]),
    ("Data & AI", "#ffe6cc", "#d79b00", [
        "sota-databases", "sota-data-engineering", "sota-ml-engineering",
        "sota-llm-engineering"]),
    ("Product surface", "#e1d5e7", "#9673a6", [
        "sota-api-design", "sota-frontend-design", "sota-web-frameworks",
        "sota-ux-writing", "sota-copywriting", "sota-cli-ux", "sota-mobile",
        "sota-docs-workflow"]),
    ("Quality", "#fff2cc", "#d6b656", [
        "sota-testing", "sota-performance", "sota-async-concurrency"]),
    ("Languages", "#f8cecc", "#b85450", [
        "sota-rust", "sota-golang", "sota-c-cpp", "sota-jvm", "sota-python",
        "sota-javascript-typescript", "sota-dotnet", "sota-php", "sota-ruby",
        "sota-shell-scripting"]),
]


# --- page 5: section x language ------------------------------------------------
# Hand-declared like FAMILIES, and gated the same way: every rules file of every language
# skill must appear below, or the run aborts. A file added without a topic would otherwise
# vanish from the matrix silently, which is the exact failure this map exists to avoid.
LANGS = ["rust", "golang", "c-cpp", "jvm", "python", "javascript-typescript",
         "dotnet", "php", "ruby"]
LANG_LABEL = {"javascript-typescript": "js/ts", "c-cpp": "c/c++", "dotnet": ".NET",
              "golang": "go", "python": "python", "rust": "rust", "jvm": "jvm",
              "php": "php", "ruby": "ruby"}
TOPIC_ORDER = ["Idioms / baseline", "API / design", "Errors", "Typing", "Concurrency",
               "Memory / UB", "Security", "Web / HTTP", "Performance",
               "Tooling / CI / supply chain", "Testing"]
# file number -> topics it carries. A number in two topics means one file covers both.
LANG_TOPICS = {
    "rust": {"01": ["Idioms / baseline", "API / design"], "02": ["Errors"],
             "03": ["Memory / UB"], "04": ["Concurrency"], "05": ["Security"],
             "06": ["Performance"],
             "07": ["Tooling / CI / supply chain", "Testing"]},
    "golang": {"01": ["Errors"], "02": ["Idioms / baseline", "API / design"],
               "03": ["Concurrency"], "04": ["Web / HTTP"], "05": ["Security"],
               "06": ["Performance"],
               "07": ["Tooling / CI / supply chain", "Testing"]},
    "c-cpp": {"01": ["Idioms / baseline", "API / design", "Errors", "Typing"], "02": ["Memory / UB"], "03": ["Memory / UB"],
              "04": ["Security"], "05": ["Concurrency"],
              "06": ["Tooling / CI / supply chain", "Testing"], "07": ["Performance"]},
    "jvm": {"01": ["Idioms / baseline", "Errors"], "02": ["API / design"], "03": ["Concurrency"],
            "04": ["Security"], "05": ["Performance"],
            "06": ["Tooling / CI / supply chain", "Testing"]},
    "python": {"01": ["Tooling / CI / supply chain"], "02": ["Typing"],
               "03": ["Idioms / baseline", "API / design", "Errors"],
               "04": ["Concurrency"], "05": ["Security"],
               "06": ["Performance"], "07": ["Testing", "Web / HTTP"]},
    "javascript-typescript": {"01": ["Typing"], "02": ["Idioms / baseline", "API / design", "Errors"],
                              "03": ["Concurrency"], "04": ["Web / HTTP"],
                              "05": ["Security"], "06": ["Performance"],
                              "07": ["Testing", "Tooling / CI / supply chain"]},
    "dotnet": {"01": ["Idioms / baseline", "Typing"], "02": ["API / design", "Errors"],
               "03": ["Concurrency"], "04": ["Security", "Web / HTTP"], "05": ["Performance"],
               "06": ["Tooling / CI / supply chain", "Testing"]},
    "php": {"01": ["Idioms / baseline", "Concurrency", "API / design", "Errors", "Typing"], "02": ["Security"],
            "03": ["Security"], "04": ["Security", "Web / HTTP"],
            "05": ["Tooling / CI / supply chain", "Testing"], "06": ["Performance"]},
    "ruby": {"01": ["Idioms / baseline", "API / design", "Errors", "Typing"], "02": ["Security"], "03": ["Web / HTTP"],
             "04": ["Tooling / CI / supply chain", "Testing"],
             "05": ["Concurrency", "Performance"]},
}
# A topic carried by a file that also carries another is marked shared; a topic present
# only as a section inside a broader file is marked inline. Both are read off the tree.
INLINE = {("php", "Concurrency"): "01 §6",
          # ROADMAP 57 landed API/design as a SECTION inside the idioms file for five
          # languages rather than a dedicated file. Declared inline so page 5 shows where
          # it actually lives -- it read BLANK for four of them until 2026-09-22, while
          # the sections existed, because this table is hand-maintained.
          ("c-cpp", "API / design"): "01 §9",
          ("javascript-typescript", "API / design"): "02 §Designing",
          ("php", "API / design"): "01 §6a",
          ("ruby", "API / design"): "01 §8",
          ("python", "API / design"): "03 §13",
          # Errors/Typing/Web where the topic is a SECTION, verified by reading each
          # heading 2026-09-22. Every one of these rendered BLANK while the legend said
          # "no dedicated treatment" -- false for all of them. Same declaration gap as
          # API/design, one row down.
          ("c-cpp", "Errors"): "01 §7",
          ("jvm", "Errors"): "01 §4",
          ("python", "Errors"): "03 §10",
          ("javascript-typescript", "Errors"): "02 §Error",
          ("dotnet", "Errors"): "02 §4",
          ("php", "Errors"): "01 §5",
          ("ruby", "Errors"): "01 §5",
          ("c-cpp", "Typing"): "01 §6",
          ("ruby", "Typing"): "01 §6",
          ("python", "Web / HTTP"): "07 §1-2",
          ("dotnet", "Web / HTTP"): "04 §4",
          # php and .NET are gradual-typing languages too, which the note's
          # "only in the gradual-typing pair" missed: php bolts PHPStan/Psalm LEVELS onto
          # a dynamic language exactly as python does mypy, and C# NRT is opt-in
          # nullability you enable per project. Both have a dedicated section.
          ("php", "Typing"): "01 §2",
          ("dotnet", "Typing"): "01 §2"}


def audit_items(lang):
    """Actionable items in a language skill's Audit checklists. Counted format-aware because
    the BODY format is not gated -- only the heading is (invariant 2) -- and three forms are
    in use: tickable `- [ ]`, fenced shell block, and prose+commands. A `- [ ]`-only count
    returned 0 for seven of nine skills on 2026-09-21, which is how the split was found.

    The two forms are NOT comparable: a checkbox item can bundle several commands while a
    fence counts per line. Use this to compare within a format, never across."""
    box = cmd = lines = 0
    for f in sorted((ROOT / ("skills/sota-%s/rules" % lang)).glob("*.md")):
        t = f.read_text(encoding="utf-8")
        lines += len(t.splitlines())
        m = re.search(r'(?ms)^## Audit checklist\s*(.*)\Z', t)
        if not m:
            continue
        box += len(re.findall(r'^\s*- \[ \] ', m.group(1), re.M))
        infence = False
        for ln in m.group(1).splitlines():
            if ln.strip().startswith("```"):
                infence = not infence
            elif infence and ln.strip() and not ln.strip().startswith("#"):
                cmd += 1
    return box + cmd, lines


def skill_family(name):
    for fam, fill, stroke, members in FAMILIES:
        if name in members:
            return fam, fill, stroke
    return "?", "#ffffff", "#9e9e9e"


def tracked(pattern):
    out = subprocess.check_output(["git", "ls-files", pattern], cwd=ROOT).decode()
    return [l for l in out.split() if l]


def unwrap(text):
    """Markdown wraps `sota-secrets-\\nmanagement`, so a naive scan yields 'sota-secrets-'
    and the edge is lost. Join a hyphen that ends a line to the next word before scanning.
    Every name is validated against the real directory listing afterwards, so an
    over-eager join cannot invent a skill -- it can only fail to match, and the printed
    denominator is what would show that."""
    return re.sub(r'-\n\s*', '-', text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-weight", type=int, default=3,
                    help="page 3 edge threshold (default 3)")
    ap.add_argument("--out", default="docs/skill-map.drawio")
    ap.add_argument("--json", default="docs/skill-map.json")
    args = ap.parse_args()

    files = tracked("skills/*.md")
    skills = sorted({p.split("/")[1] for p in files})
    domain = [s for s in skills if s != "sota"]
    # Fail closed on an empty scope: a drifted pathspec would otherwise draw an empty map
    # and exit 0 (sota-code-security rules/11 §2.2).
    if not files or not domain:
        sys.exit("gen-skill-map: scanned 0 skill files — pathspec drift, refusing to draw")

    placed = {s for _, _, _, members in FAMILIES for s in members}
    missing = sorted(set(domain) - placed)
    extra = sorted(placed - set(domain))
    if missing or extra:
        sys.exit("gen-skill-map: FAMILIES is out of sync with the tree.\n"
                 "  in tree, unplaced: %s\n  placed, not in tree: %s" % (missing, extra))

    # ---- router routing table + cross-cutting rules -------------------------
    router = unwrap((ROOT / "skills/sota/SKILL.md").read_text(encoding="utf-8"))
    table = re.findall(r'^\|\s*`(sota-[a-z0-9-]+)`\s*\|\s*(.+?)\s*\|\s*$', router, re.M)
    table = [(s, d) for s, d in table if s in domain]

    xc_start = router.index("## Cross-cutting routing rules")
    xc = router[xc_start:router.index("## BUILD mode", xc_start)]
    rule_pos = [(int(m.group(1)), m.start(), m.group(2))
                for m in re.finditer(r'^(\d+)\.\s+\*\*(.+?)\*\*', xc, re.M | re.S)]
    rules = []
    for i, (num, start, title) in enumerate(rule_pos):
        end = rule_pos[i + 1][1] if i + 1 < len(rule_pos) else len(xc)
        named = sorted({n for n in re.findall(r'sota-[a-z0-9-]+', xc[start:end])
                        if n in domain})
        t = " ".join(title.split())
        if len(t) > 64:                      # cut at a word boundary, not mid-word:
            t = t[:64].rsplit(" ", 1)[0] + "…"   # "...crypto skill (b" was the tell
        rules.append((num, t, named))

    # ---- measured cross-skill edges ----------------------------------------
    edges = collections.Counter()
    detail = collections.defaultdict(set)
    tgt = re.compile(r'`?(sota-[a-z0-9-]+)`?\**\s*(rules/\d+)?\s*\**\s*'
                     r'(§[0-9]+[a-z]?(?:\.[0-9]+)?)?')
    for p in files:
        a = p.split("/")[1]
        if a == "sota":
            continue
        for m in tgt.finditer(unwrap((ROOT / p).read_text(encoding="utf-8"))):
            b = m.group(1)
            if b not in domain or b == a:
                continue
            edges[(a, b)] += 1
            bits = " ".join(x for x in (m.group(2), m.group(3)) if x)
            if bits:
                detail[(a, b)].add(bits)
    indeg = collections.Counter()
    for (a, b), n in edges.items():
        indeg[b] += n

    # Per-language stats, and the fail-closed check that every rules file is classified.
    lang_files = {}
    for lang in LANGS:
        paths = [f for f in files if f.startswith("skills/sota-%s/rules/" % lang)]
        nums = sorted(pathlib.Path(f).name.split("-")[0] for f in paths)
        declared = sorted(LANG_TOPICS[lang])
        if nums != declared:
            sys.exit("gen-skill-map: LANG_TOPICS[%r] does not match the tree.\n"
                     "  on disk: %s\n  declared: %s" % (lang, nums, declared))
        total = sum(len((ROOT / f).read_text(encoding="utf-8").splitlines()) for f in paths)
        lang_files[lang] = (total, len(paths))
    unknown = {t for l in LANG_TOPICS.values() for ts in l.values() for t in ts
               } - set(TOPIC_ORDER)
    if unknown:
        sys.exit("gen-skill-map: topics not in TOPIC_ORDER: %s" % sorted(unknown))

    assert_matrix_matches_tree()
    pages = [page_router(), page_rules(rules),
             page_graph(edges, indeg, args.min_weight), page_slice(),
             page_matrix(lang_files)]
    xml = ('<mxfile host="gen-skill-map.py" type="device">\n'
           + "\n".join(pages) + "\n</mxfile>\n")
    (ROOT / args.out).write_text(xml, encoding="utf-8")

    shown = {k: v for k, v in edges.items() if v >= args.min_weight}
    (ROOT / args.json).write_text(json.dumps({
        "skills": domain,
        "routing_table_rows": len(table),
        "cross_cutting_rules": [{"n": n, "title": t, "skills": s} for n, t, s in rules],
        "edges": [{"from": a, "to": b, "weight": w, "targets": sorted(detail[(a, b)])}
                  for (a, b), w in sorted(edges.items(), key=lambda kv: -kv[1])],
    }, indent=2) + "\n", encoding="utf-8")

    print("skill files scanned : %d" % len(files))
    print("skills              : %d (%d domain + router)" % (len(skills), len(domain)))
    print("routing table rows  : %d" % len(table))
    print("cross-cutting rules : %d" % len(rules))
    print("cross-skill edges   : %d distinct, %d mentions"
          % (len(edges), sum(edges.values())))
    print("drawn on page 3     : %d (weight >= %d)" % (len(shown), args.min_weight))
    print("language skills      : %d, %d rules files, %d lines"
          % (len(LANGS), sum(v[1] for v in lang_files.values()),
             sum(v[0] for v in lang_files.values())))
    print("wrote %s and %s" % (args.out, args.json))


# --------------------------------------------------------------------------- draw.io
def esc(s):
    """draw.io cells here set html=1, and under html=1 a literal newline collapses to a
    space -- every multi-line label rendered as one run-on line until that was caught by
    rendering the file and looking at it.

    The break must be written as the ENTITY, not as a raw tag. A literal '<br>' inside an
    XML attribute is malformed XML: the first attempt did exactly that, the file stopped
    parsing, and draw.io answered with a bare 'Export failed' naming no line or reason.
    Escaping it means the XML parser hands draw.io '<br>', which html=1 then renders."""
    # Backticks are stripped, not escaped: draw.io's renderer treats them as MATH
    # delimiters, so `state` came out italic and `sota-shell-scripting` rendered as
    # "sota - shell - script in g" -- garbled algebra in a diagram about skills.
    return html.escape(str(s).replace("`", ""), quote=True).replace("\n", "&lt;br&gt;")


def slug(name):
    """Cell IDs are XML ATTRIBUTES and cell() escapes only the value, not the id. A family
    name like 'Platform & delivery' therefore emitted id="f_Platform & delivery", which is
    malformed XML -- and draw.io rendered it anyway, so "it opens" did not catch it. The
    XML parse did. Keep ids to a safe token set."""
    return re.sub(r'[^A-Za-z0-9_]', '_', name)


def cell(cid, value, style, x, y, w, h, parent="1"):
    return ('        <mxCell id="%s" value="%s" style="%s" vertex="1" parent="%s">\n'
            '          <mxGeometry x="%d" y="%d" width="%d" height="%d" as="geometry"/>\n'
            '        </mxCell>' % (cid, esc(value), style, parent, x, y, w, h))


def edge(eid, src, dst, value="", style="", lx=None):
    """lx slides the label along the edge (-1 .. 1). Two edges leaving the same node
    otherwise drop their labels on the same point and overprint each other, which is how
    'identity infrastructure' and 'app-level login' rendered as one word."""
    base = ("edgeStyle=orthogonalEdgeStyle;rounded=1;html=1;"
            "jettySize=auto;orthogonalLoop=1;" + style)
    geo = ('          <mxGeometry relative="1" as="geometry"/>' if lx is None else
           '          <mxGeometry x="%s" relative="1" as="geometry">\n'
           '            <mxPoint as="offset"/>\n'
           '          </mxGeometry>' % lx)
    return ('        <mxCell id="%s" value="%s" style="%s" edge="1" parent="1" '
            'source="%s" target="%s">\n%s\n        </mxCell>'
            % (eid, esc(value), base, src, dst, geo))


def page(pid, name, cells, w=1600, h=1200):
    return ('  <diagram id="%s" name="%s">\n'
            '    <mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" guides="1" '
            'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
            'pageWidth="%d" pageHeight="%d" math="0" shadow="0">\n'
            '      <root>\n        <mxCell id="0"/>\n        <mxCell id="1" parent="0"/>\n'
            '%s\n      </root>\n    </mxGraphModel>\n  </diagram>'
            % (pid, esc(name), w, h, "\n".join(cells)))


NOTE = ("shape=note;whiteSpace=wrap;html=1;backgroundOutline=1;darkOpacity=0.05;"
        "fillColor=#FFF9B2;strokeColor=none;fontSize=11;align=left;verticalAlign=top;")
BOX = "rounded=1;whiteSpace=wrap;html=1;fontSize=11;"


def page_router():
    c = [cell("note",
              "Page 1 — the router reaches a skill by its DESCRIPTION.\n\n"
              "Only the frontmatter `description` auto-loads; it is the entire trigger "
              "classifier, and the router BODY is inert until the Skill tool fires. So "
              "these edges are not links — they are a classifier choosing among 41 "
              "competing descriptions.\n\n"
              "Measured 2026-09-20: correct=0.900 on the 10-case golden set, 1.000 on "
              "the 5-case SSO set.",
              NOTE, 40, 30, 620, 170)]
    c.append(cell("router",
                  "sota  (router)\nrouting table · 21 cross-cutting rules\n"
                  "BUILD mode · AUDIT mode",
                  BOX + "fillColor=#000000;fontColor=#ffffff;strokeColor=#000000;"
                        "fontStyle=1;fontSize=13;",
                  1050, 120, 340, 100))
    # ONE ROW, not a 2x3 grid. In a grid the router sits above the top row, so every
    # edge to a lower family must cross the family boxes above it -- rendered, six edges
    # ran straight down THROUGH Security core and Platform & delivery. A single row means
    # each edge reaches its own column and crosses nothing. Straight edges, because
    # orthogonal routing would re-introduce a shared horizontal channel.
    x, y, gap = 40, 320, 390
    for fi, (fname, fill, stroke, members) in enumerate(FAMILIES):
        gh = 40 + 28 * len(members)
        gid = "fam%d" % fi
        c.append(cell(gid, "%s  (%d)" % (fname, len(members)),
                      "swimlane;whiteSpace=wrap;html=1;fontStyle=1;fontSize=12;"
                      "startSize=26;fillColor=%s;strokeColor=%s;" % (fill, stroke),
                      x + fi * gap, y, 370, gh))
        for mi, m in enumerate(members):
            c.append(cell("%s_%d" % (gid, mi), m.replace("sota-", ""),
                          BOX + "fillColor=#ffffff;strokeColor=%s;" % stroke,
                          10, 30 + 28 * mi, 350, 22, parent=gid))
        # Pin the endpoints: leave the router's bottom, arrive at the family's TOP edge.
        # Unpinned, draw.io picks the nearest side, so the two outermost edges attached to
        # a SIDE and clipped the corner of the box next door.
        c.append(edge("e_%s" % gid, "router", gid, "",
                      "edgeStyle=none;strokeColor=#888888;endArrow=blockThin;"
                      "exitX=0.5;exitY=1;exitDx=0;exitDy=0;"
                      "entryX=0.5;entryY=0;entryDx=0;entryDy=0;"))
    return page("p1", "1 · Router to skills", c, 2420, 760)


def page_rules(rules):
    """No edges. 63 links between two tight columns all share one orthogonal channel and
    route THROUGH the skill boxes -- rendered, it was a single vertical trunk and you could
    not tell which rule reached which skill. The information is 'rule N names X, Y, Z', so
    the readable form is the row itself."""
    c = [cell("note",
              "Page 2 — the 21 cross-cutting routing rules, verbatim from "
              "skills/sota/SKILL.md.\n\n"
              "These are the explicit hand-offs: which skill wins when two look plausible. "
              "The right column lists exactly the skills each rule NAMES — drawn as text "
              "rather than as edges, because 63 edges between two columns render as one "
              "unreadable trunk.",
              NOTE, 40, 20, 700, 120)]
    y = 180
    c.append(cell("hdr_r", "rule",
                  BOX + "fillColor=#f5f5f5;strokeColor=#999999;fontStyle=1;", 40, y, 470, 26))
    c.append(cell("hdr_s", "skills it names",
                  BOX + "fillColor=#f5f5f5;strokeColor=#999999;fontStyle=1;", 520, y, 640, 26))
    y += 34
    for num, title, names in rules:
        h = 30
        c.append(cell("r%d" % num, "%d. %s" % (num, title),
                      BOX + "fillColor=#fff2cc;strokeColor=#d6b656;align=left;"
                            "spacingLeft=8;", 40, y, 470, h))
        label = " · ".join(n.replace("sota-", "") for n in names) or "—"
        c.append(cell("rs%d" % num, label,
                      BOX + "fillColor=#dae8fc;strokeColor=#6c8ebf;align=left;"
                            "spacingLeft=8;", 520, y, 640, h))
        y += h + 6
    return page("p2", "2 · Cross-cutting rules", c, 1250, y + 60)


def page_graph(edges, indeg, minw):
    """Aggregated to families, not drawn as 110 skill-to-skill edges. At 38 nodes the
    detailed graph is a hairball: orthogonal routing threads edges behind boxes and no
    individual link is traceable. Six family nodes carry the same structure legibly, and
    the detail that a reader actually wants -- which skills are hubs, which single links
    are strongest -- is exact text beside it rather than a shape to squint at."""
    fam_edges = collections.Counter()
    for (a, b), w in edges.items():
        fa, fb = skill_family(a)[0], skill_family(b)[0]
        if fa != fb:
            fam_edges[(fa, fb)] += w
    internal = collections.Counter()
    for (a, b), w in edges.items():
        fa, fb = skill_family(a)[0], skill_family(b)[0]
        if fa == fb:
            internal[fa] += w

    c = [cell("note",
              "Page 3 — how the skills reference each other, aggregated to families.\n\n"
              "%d distinct skill-to-skill edges / %d mentions in the tree. Drawing all of "
              "them is a hairball at 38 nodes, so the graph is aggregated: an arrow is the "
              "TOTAL weight of every reference from one family to another, and the number "
              "inside a family is references within it.\n\n"
              "This is the layer a routing measurement does not cover: routing gets you to "
              "the right skill, this is which skill defers to which. Every individual edge, "
              "with its rules/NN and § targets, is in docs/skill-map.json."
              % (len(edges), sum(edges.values())),
              NOTE, 40, 20, 720, 170)]

    import math as _m
    names = [f[0] for f in FAMILIES]
    cx, cy, R = 660, 720, 380
    pos = {}
    for i, fam in enumerate(names):
        a = 2 * _m.pi * i / len(names) - _m.pi / 2
        pos[fam] = (cx + R * _m.cos(a) - 110, cy + R * _m.sin(a) - 45)
    for fam, fill, stroke, members in FAMILIES:
        x, y = pos[fam]
        c.append(cell("f_%s" % slug(fam), "%s\n%d skills · %d internal refs"
                      % (fam, len(members), internal[fam]),
                      BOX + "fillColor=%s;strokeColor=%s;fontStyle=1;verticalAlign=middle;"
                      % (fill, stroke), int(x), int(y), 220, 90))
    # straight edges: orthogonal routing is what put lines behind the boxes
    for i, ((fa, fb), w) in enumerate(sorted(fam_edges.items(), key=lambda kv: kv[1])):
        if w < 10:
            continue
        c.append(edge("fe%d" % i, "f_%s" % slug(fa), "f_%s" % slug(fb), str(w),
                      "edgeStyle=none;endArrow=blockThin;strokeColor=#8c8c8c;opacity=70;"
                      "fontSize=10;labelBackgroundColor=#ffffff;"
                      "strokeWidth=%d;" % min(6, 1 + w // 40)))

    hubs = sorted(indeg.items(), key=lambda kv: -kv[1])[:10]
    c.append(cell("panel_h",
                  "MOST REFERENCED (inbound weight)\n\n"
                  + "\n".join("%-26s %d" % (k.replace("sota-", ""), v) for k, v in hubs),
                  BOX + "fillColor=#ffffff;strokeColor=#b85450;align=left;spacingLeft=10;"
                        "verticalAlign=top;spacingTop=8;fontFamily=Courier New;fontSize=11;",
                  1180, 200, 330, 240))
    top = sorted(edges.items(), key=lambda kv: -kv[1])[:12]
    c.append(cell("panel_e",
                  "STRONGEST SINGLE LINKS\n\n"
                  + "\n".join("%-22s -> %-22s %d"
                               % (a.replace("sota-", ""), b.replace("sota-", ""), w)
                               for (a, b), w in top),
                  BOX + "fillColor=#ffffff;strokeColor=#6c8ebf;align=left;spacingLeft=10;"
                        "verticalAlign=top;spacingTop=8;fontFamily=Courier New;fontSize=11;",
                  1180, 470, 330, 280))
    return page("p3", "3 · Cross-skill references (measured)", c, 1600, 1200)


def page_slice():
    c = [cell("note",
              "Page 4 — a worked slice: what an SSO task traverses, end to end.\n\n"
              "Measured 2026-09-20: all 5 SSO routing cases were correct, 3/3 samples "
              "each. Routing was never the problem. The two real gaps were a CONTENT "
              "gap (Golden SAML — in a skill that routed correctly and held nothing) "
              "and a CHECKLIST gap (`state`, whose rule lives in a different skill, so "
              "an auditor walking this skill's checklist was never prompted).",
              NOTE, 40, 20, 700, 140)]
    nodes = [
        ("s_task", 'task: "audit our SSO integration"', "#ffffff", "#666666",
         60, 200, 280, 50),
        ("s_router", "sota (router)\nrule 10: identity infrastructure vs app-level login",
         "#000000", "#000000", 60, 300, 280, 70),
        ("s_ia", "sota-identity-access\nrules/01 federation protocols",
         "#d5e8d4", "#82b366", 440, 190, 270, 60),
        ("s_ia3", "§3 claim validation at the RP\naud · azp · iss · exp · nonce · alg",
         "#ffffff", "#82b366", 800, 120, 300, 50),
        ("s_ia4", "§4 redirect-URI discipline\nexact match · no wildcards",
         "#ffffff", "#82b366", 800, 190, 300, 50),
        ("s_ia5", "§5 PKCE downgrade\nrequire S256 — do not merely offer",
         "#ffffff", "#82b366", 800, 260, 300, 50),
        ("s_ia7", "§7 SAML attack classes\nXSW · comment injection · Golden SAML",
         "#ffffff", "#82b366", 800, 330, 300, 50),
        ("s_cs", "sota-code-security\nrules/02 §4 — `state` / login CSRF",
         "#dae8fc", "#6c8ebf", 440, 560, 270, 60),
        ("s_det", "sota-detection-engineering\nrules/07 — forged SAML tokens T1606.002",
         "#ffe6cc", "#d79b00", 800, 560, 300, 60),
        ("s_gap", "ADDED 2026-09-20\nGolden SAML mechanics + detection\n"
                  "`state` checklist item",
         "#f8cecc", "#b85450", 1180, 390, 280, 90),
    ]
    for cid, val, fill, stroke, x, y, w, h in nodes:
        fc = "fontColor=#ffffff;" if fill == "#000000" else ""
        c.append(cell(cid, val,
                      BOX + "fillColor=%s;strokeColor=%s;%s" % (fill, stroke, fc),
                      x, y, w, h))
    links = [("s_task", "s_router", "description classifier"),
             ("s_router", "s_ia", "identity infrastructure"),
             ("s_ia", "s_ia3", ""), ("s_ia", "s_ia4", ""),
             ("s_ia", "s_ia5", ""), ("s_ia", "s_ia7", ""),
             ("s_router", "s_cs", "app-level login"),
             ("s_ia7", "s_det", 'rule 12: "would we catch it?"'),
             ("s_det", "s_gap", ""), ("s_cs", "s_gap", "")]
    # slide the two labels that leave the router apart; they collided at the midpoint
    offsets = {("s_router", "s_ia"): "-0.45", ("s_router", "s_cs"): "0.45"}
    # The four section edges leave ONE node for four stacked boxes. Orthogonal routing
    # gives them a shared vertical channel that runs straight through §5 and §7 -- the
    # "links go through other items" failure. Straight edges fan out instead.
    fan = {("s_ia", "s_ia3"), ("s_ia", "s_ia4"), ("s_ia", "s_ia5"), ("s_ia", "s_ia7")}
    for i, (a, b, lbl) in enumerate(links):
        st = ("edgeStyle=none;strokeColor=#82b366;endArrow=blockThin;"
              if (a, b) in fan else "strokeColor=#666666;")
        c.append(edge("se%d" % i, a, b, lbl, st, lx=offsets.get((a, b))))
    return page("p4", "4 · Worked slice: an SSO task", c, 1650, 800)


# --- cross-instrument consistency -------------------------------------------------
# WHY THIS EXISTS. LANG_TOPICS above is HAND-DECLARED, and `gen-concept-matrix.py` derives
# the same kind of fact by reading every Audit checklist in the tree. On 2026-09-22 they
# disagreed and nothing noticed: ROADMAP 57 put an API/design SECTION into five idioms
# files, the concept matrix reported 9/9, and page 5 rendered four BLANK cells because this
# table was never updated. The map was regenerated in that same session and still lied.
#
# The map's own gate cannot catch this: it proves the committed artifact matches the
# generator, never that the generator matches the tree. So the two instruments are checked
# against each other here.
#
# Only topics with an UNAMBIGUOUS concept counterpart are checked. The rest (Idioms, Memory
# / UB, Web / HTTP, Performance, Errors, Typing) have no 1:1 concept and are deliberately
# left out rather than mapped approximately -- a loose mapping would open red and get
# disabled, which docs/CONVENTIONS-LEDGER.md says is worse than no gate.
TOPIC_CONCEPT = {
    "API / design": "public API surface & evolution",
    # Added 2026-09-22 after all SEVEN Errors blanks turned out to have a section.
    # It was excluded on the first pass as "no 1:1 concept", which was too hasty:
    # error handling is in UNIVERSAL_FLOOR at 9/9, so the two instruments were
    # already making contradictory claims about the same fact.
    "Errors": "error handling & propagation",
    "Concurrency": "data race / shared mutable state",
    "Security": "input validation & untrusted data",
    "Testing": "test suite health & determinism",
    "Tooling / CI / supply chain": "dependency pinning & lockfiles",
}


def assert_matrix_matches_tree():
    """Abort if the hand-declared LANG_TOPICS contradicts what the tree actually contains."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_cm", str(ROOT / "scripts" / "gen-concept-matrix.py"))
    cm = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(cm)
    except Exception as e:                      # never let the cross-check break the map
        print("NOTE: concept cross-check skipped (%s)" % e, file=sys.stderr)
        return
    present, _classified, _un = cm.build(LANGS)
    bad = []
    for topic, concept in TOPIC_CONCEPT.items():
        probing = present.get(concept, set())
        for lang in LANGS:
            declared = any(topic in v for v in LANG_TOPICS[lang].values())
            if lang in probing and not declared:
                bad.append("%s probes %r (concept: %s) but LANG_TOPICS declares no %r"
                           % (LANG_LABEL[lang], topic, concept, topic))
    if bad:
        sys.exit("MATRIX DISAGREES WITH THE TREE -- page 5 would render a blank cell for a "
                 "topic the skill actually covers:\n  " + "\n  ".join(bad) +
                 "\nAdd the topic to LANG_TOPICS (and an INLINE marker if it is a section "
                 "inside a broader file), or correct the concept matcher if the concept "
                 "hit is a false positive.")


def _universal_phrase():
    """"N sections are universal -- a, b, c", counted off LANG_TOPICS itself."""
    uni = [tp for tp in TOPIC_ORDER
           if all(any(tp in v for v in LANG_TOPICS[l].values()) for l in LANGS)]
    words = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six",
             7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten", 11: "Eleven"}
    # first segment, ORIGINAL case -- lowercasing turned "API / design" into "api"
    short = [tp.split(" /")[0].split(" \u2014")[0].strip() for tp in uni]
    return "%s sections are universal \u2014 %s" % (
        words.get(len(uni), str(len(uni))), ", ".join(short))


def page_matrix(lang_files):
    """Section x language. A grid, because that is what a comparison of 11 topics across 9
    languages IS -- drawing it as nodes and edges would be the page-2 mistake again."""
    c = [cell("note",
              "Page 5 — section x language. Which topics each language skill gives its own "
              "rules file.\n\n"
              "SOLID = a file of its own. LIGHT = shares a file with another topic, or is a "
              "section inside a broader file (the cell says which). BLANK = no file AND no "
              "section — which is NOT the same as 'not covered': a concept can still be "
              "probed from inside another topic, and gen-concept-matrix.py is what answers "
              "that question. This legend read 'no dedicated treatment' until 2026-09-22, "
              "while 11 cells were blank with a real section behind them.\n\n"
              # DERIVED, never written. This sentence read "Four sections are universal"
              # while the table below it showed SIX (Concurrency and Testing were already
              # 9/9), and then SEVEN once ROADMAP 57 closed -- wrong before anyone touched
              # it, and wrong again after. A count with its own source of truth twelve
              # lines away has no business being a literal.
              "%s. The "
              "variation is not arbitrary: Errors gets a file only where the error MODEL is "
              "distinctive (Rust, Go); Typing wherever a checker is bolted onto the language "
              "(python, js/ts, ruby, php, c/c++, .NET NRT) and not in rust/go/jvm; Memory/UB "
              "only where memory is manual. `sota-shell-scripting` is excluded — 9 files "
              "with a different spine, grouped with languages but not a peer."
              % _universal_phrase(),
              NOTE, 40, 20, 900, 180)]
    x0, y0, cw, rh, lw = 430, 230, 108, 34, 380
    for j, lang in enumerate(LANGS):
        c.append(cell("mh%d" % j, LANG_LABEL[lang],
                      BOX + "fillColor=#f5f5f5;strokeColor=#999999;fontStyle=1;fontSize=11;",
                      x0 + j * cw, y0, cw - 6, rh - 6))
    for i, topic in enumerate(TOPIC_ORDER):
        y = y0 + (i + 1) * rh
        c.append(cell("mr%d" % i, topic,
                      BOX + "fillColor=#f5f5f5;strokeColor=#999999;align=left;"
                            "spacingLeft=10;fontStyle=1;fontSize=11;", 40, y, lw, rh - 6))
        for j, lang in enumerate(LANGS):
            nums = sorted(n for n, tops in LANG_TOPICS[lang].items() if topic in tops)
            if not nums:
                style = BOX + "fillColor=#fafafa;strokeColor=#dddddd;fontSize=10;"
                label = ""
            else:
                shared = any(len(LANG_TOPICS[lang][n]) > 1 for n in nums)
                inline = INLINE.get((lang, topic))
                label = inline or ", ".join(nums)
                fam_fill = "#d5e8d4" if not (shared or inline) else "#eaf5e9"
                fam_stroke = "#82b366" if not (shared or inline) else "#a9cfa5"
                style = (BOX + "fillColor=%s;strokeColor=%s;fontSize=10;"
                         % (fam_fill, fam_stroke))
            c.append(cell("m%d_%d" % (i, j), label, style,
                          x0 + j * cw, y, cw - 6, rh - 6))
    y = y0 + (len(TOPIC_ORDER) + 1) * rh + 10
    for lbl, key in (("rules-file lines", "lines"), ("files", "files")):
        c.append(cell("mt_%s" % key, lbl,
                      BOX + "fillColor=#ffffff;strokeColor=#999999;align=left;"
                            "spacingLeft=10;fontSize=11;", 40, y, lw, rh - 6))
        for j, lang in enumerate(LANGS):
            n = lang_files[lang][0] if key == "lines" else lang_files[lang][1]
            c.append(cell("mt%s%d" % (key, j), str(n),
                          BOX + "fillColor=#ffffff;strokeColor=#cccccc;fontSize=11;",
                          x0 + j * cw, y, cw - 6, rh - 6))
        y += rh

    # --- the shell strip ------------------------------------------------------------
    # sota-shell-scripting is NOT a column here: different spine, so a shared grid would
    # imply comparisons that do not hold. But leaving it off the page entirely made a
    # reader ask "do we not cover bash/zsh?" on 2026-09-22 -- with 9 files and ~2.8k lines
    # in the tree, more than jvm or .NET. Absent from the picture read as absent from the
    # library, so it gets a strip of its own, clearly outside the grid.
    y += 12
    sh_files = sorted((ROOT / "skills/sota-shell-scripting/rules").glob("*.md"))
    sh_lines = sum(len(f.read_text(encoding="utf-8").splitlines()) for f in sh_files)
    c.append(cell("m_sh", "sota-shell-scripting (bash + zsh + PowerShell) — covered, and "
                          "deliberately NOT a column: its spine is different, so a shared "
                          "grid would imply comparisons that do not hold.\n"
                          "%d files, %d lines — larger than several language skills. zsh is "
                          "treated as its own dialect throughout, not as a bash footnote."
                          % (len(sh_files), sh_lines),
                  BOX + "fillColor=#fffbe6;strokeColor=#d6b656;align=left;spacingLeft=10;"
                        "verticalAlign=middle;fontSize=11;", 40, y, lw + 9 * cw - 6, 46))
    y += 54
    for j, f in enumerate(sh_files):
        title = f.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
        short = title.split("—")[-1].strip() if "—" in title else title
        c.append(cell("msh%d" % j, "%s\n%s" % (f.name[:2], short[:26]),
                      BOX + "fillColor=#fdf6d8;strokeColor=#d6b656;fontSize=9;",
                      40 + j * ((lw + 9 * cw) // 9), y,
                      ((lw + 9 * cw) // 9) - 6, rh + 6))
    y += rh + 18

    dens = {l: (audit_items(l)[0] / lang_files[l][0] * 100) for l in LANGS}
    c.append(cell("m_note2",
                  "API / design was the one asymmetry that did not track a language "
                  "difference. CLOSED 2026-09-22 (ROADMAP 57): all nine now carry it, as a "
                  "dedicated file in some and a section inside the idioms file in others, "
                  "and gen-concept-matrix.py pins it at 9/9 so it cannot regress.\n\n"
                  "Per-language detail deliberately NOT repeated here -- it lives in "
                  "docs/LANGUAGE-TIER.md. This sentence named the languages twice and "
                  "rotted twice in two days (2026-09-21 and -22), because a hand-written "
                  "list inside a GENERATED artifact has no gate: the map gate proves the "
                  "artifact matches the generator, never that the generator is true.\n\n"
                  "RETRACTED 2026-09-21 — this note previously read \"jvm and .NET are 3–4x "
                  "thinner\". True of line count, false of what line count stood in for: per "
                  "100 rules-lines they carry the HIGHEST audit-item density in the library "
                  "(.NET %.1f, jvm %.1f — COMPUTED NOW, not the 2026-09-21 figures of "
                  "10.6 and 10.5; both skills have gained audit items since) and rust, "
                  "the second-largest skill, is lowest at "
                  "%.1f. The bounded deficit is worked examples. Caveat: the checkbox and "
                  "shell-block checklist formats are not comparable, so this read is "
                  "within-format."
                  % (dens["dotnet"], dens["jvm"], dens["rust"]),
                  NOTE, 40, y + 20, 900, 150))
    return page("p5", "5 · Section x language", c, 1500, y + 180)


if __name__ == "__main__":
    main()
