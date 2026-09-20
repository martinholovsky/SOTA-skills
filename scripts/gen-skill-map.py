#!/usr/bin/env python3
"""Generate docs/skill-map.drawio — how the router reaches the skills, and how the
skills reach each other.

WHY A GENERATOR AND NOT A DRAWING. A hand-drawn map of 42 skills and ~300 cross-links is
stale the first time a rules file moves, and nothing would report it -- the failure mode
this repo exists to gate against. So the map is DERIVED: every node and edge is read out
of the tree at generation time, every extracted skill name is validated against the real
skills/ directory listing, and the run prints its denominators so a drop is visible.

Four pages:
  1. Router -> skills, grouped by family (the routing table in skills/sota/SKILL.md).
  2. The 21 cross-cutting routing rules, as a bipartite rule -> skill map.
  3. The MEASURED cross-skill reference graph, thresholded (default: weight >= 3).
  4. A worked slice: what an SSO task actually traverses.

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
        rules.append((num, " ".join(title.split())[:58], named))

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

    pages = [page_router(), page_rules(rules),
             page_graph(edges, indeg, args.min_weight), page_slice()]
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
    return html.escape(str(s), quote=True).replace("\n", "&lt;br&gt;")


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
              NOTE, 40, 30, 520, 150)]
    c.append(cell("router",
                  "sota  (router)\nrouting table · 21 cross-cutting rules\n"
                  "BUILD mode · AUDIT mode",
                  BOX + "fillColor=#000000;fontColor=#ffffff;strokeColor=#000000;"
                        "fontStyle=1;fontSize=13;",
                  700, 60, 320, 90))
    # Two columns. The row advances by the TALLER of its two groups, not by whichever was
    # drawn last: Security core has 11 members and its right-hand neighbour has 5, so
    # advancing by the last one overlapped the next row on top of it. Caught by rendering
    # the page and looking at it, which is the only check that sees a collision.
    x, y, row_max = 40, 230, 0
    for fi, (fname, fill, stroke, members) in enumerate(FAMILIES):
        gh = 40 + 28 * len(members)
        row_max = max(row_max, gh)
        gid = "fam%d" % fi
        c.append(cell(gid, "%s  (%d)" % (fname, len(members)),
                      "swimlane;whiteSpace=wrap;html=1;fontStyle=1;fontSize=12;"
                      "startSize=26;fillColor=%s;strokeColor=%s;" % (fill, stroke),
                      x, y, 380, gh))
        for mi, m in enumerate(members):
            c.append(cell("%s_%d" % (gid, mi), m.replace("sota-", ""),
                          BOX + "fillColor=#ffffff;strokeColor=%s;" % stroke,
                          10, 30 + 28 * mi, 360, 22, parent=gid))
        c.append(edge("e_%s" % gid, "router", gid, "", "strokeColor=#666666;"))
        if fi % 2 == 0:
            x = 480
        else:
            x, y, row_max = 40, y + row_max + 40, 0
    return page("p1", "1 · Router to skills", c, 1700, 1700)


def page_rules(rules):
    c = [cell("note",
              "Page 2 — the 21 cross-cutting routing rules, verbatim from "
              "skills/sota/SKILL.md.\n\n"
              "These are the explicit hand-offs: which skill wins when two look "
              "plausible (rule 9 splits infra four ways; rule 10 separates identity "
              "infrastructure from app-level login; rule 18 fans cryptography out "
              "because there is deliberately no crypto skill).\n\n"
              "An edge is drawn only where the rule NAMES the skill.",
              NOTE, 40, 20, 600, 150)]
    targets = sorted({s for _, _, names in rules for s in names})
    for i, t in enumerate(targets):
        c.append(cell("t_%s" % t, t.replace("sota-", ""),
                      BOX + "fillColor=#dae8fc;strokeColor=#6c8ebf;",
                      1120, 200 + 40 * i, 250, 26))
    for i, (num, title, names) in enumerate(rules):
        rid = "r%d" % num
        c.append(cell(rid, "%d. %s" % (num, title),
                      BOX + "fillColor=#fff2cc;strokeColor=#d6b656;align=left;"
                            "spacingLeft=8;",
                      60, 200 + 40 * i, 450, 30))
        for t in names:
            c.append(edge("e_%s_%s" % (rid, t), rid, "t_%s" % t, "",
                          "strokeColor=#b3b3b3;opacity=55;endArrow=blockThin;"))
    return page("p2", "2 · Cross-cutting rules", c, 1550, 1150)


def page_graph(edges, indeg, minw):
    shown = {k: v for k, v in edges.items() if v >= minw}
    nodes = sorted({n for k in shown for n in k})
    c = [cell("note",
              "Page 3 — the MEASURED cross-skill reference graph: every place one "
              "skill's files name another skill.\n\n"
              "%d distinct edges / %d mentions in the tree; %d drawn here at "
              "weight >= %d. Ring is inbound weight — the centre is what everything "
              "else defers to. Edge thickness is weight.\n\n"
              "This is the layer a routing measurement does NOT cover: reaching the "
              "right skill is page 1, but whether the rule you need is in THIS file or "
              "one it defers to is here. Full data, including rules/NN and § targets, "
              "in docs/skill-map.json."
              % (len(edges), sum(edges.values()), len(shown), minw),
              NOTE, 30, 20, 660, 170)]
    ranked = sorted(nodes, key=lambda n: -indeg[n])
    hub, inner, outer = ranked[:1], ranked[1:9], ranked[9:]
    cx, cy = 850, 780
    pos = {}
    for n in hub:
        pos[n] = (cx - 90, cy - 20)
    for i, n in enumerate(inner):
        a = 2 * math.pi * i / max(1, len(inner))
        pos[n] = (cx + 300 * math.cos(a) - 90, cy + 240 * math.sin(a) - 20)
    for i, n in enumerate(outer):
        a = 2 * math.pi * i / max(1, len(outer))
        pos[n] = (cx + 640 * math.cos(a) - 90, cy + 540 * math.sin(a) - 20)
    for n in nodes:
        x, y = pos[n]
        top = n in hub
        c.append(cell("g_%s" % n, "%s\n%d inbound" % (n.replace("sota-", ""), indeg[n]),
                      BOX + ("fillColor=#f8cecc;strokeColor=#b85450;fontStyle=1;"
                             if top else "fillColor=#ffffff;strokeColor=#9e9e9e;"),
                      int(x), int(y), 180, 40))
    for i, ((a, b), w) in enumerate(sorted(shown.items(), key=lambda kv: kv[1])):
        c.append(edge("ge%d" % i, "g_%s" % a, "g_%s" % b, "",
                      "strokeColor=#9e9e9e;opacity=45;endArrow=blockThin;"
                      "strokeWidth=%d;" % min(5, 1 + w // 6)))
    return page("p3", "3 · Cross-skill references (measured)", c, 1800, 1600)


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
    for i, (a, b, lbl) in enumerate(links):
        c.append(edge("se%d" % i, a, b, lbl, "strokeColor=#666666;",
                      lx=offsets.get((a, b))))
    return page("p4", "4 · Worked slice: an SSO task", c, 1650, 800)


if __name__ == "__main__":
    main()
