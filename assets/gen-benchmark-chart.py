#!/usr/bin/env python3
"""Generate the competitor-benchmark bar chart (light + dark SVGs) in assets/.

A single-measure magnitude chart: best-practice completeness (%) per library, with
SOTA-skills emphasized. Identity is carried by the text labels (each bar is named),
so color is not load-bearing — the brand green marks SOTA-skills, recessive grays
carry the rest. Numbers come from evals/results/2026-07-13/competitor-benchmark.json
(the 7-task, content-only, blind-judged means, rounded to whole %).

Regenerate: python3 assets/gen-benchmark-chart.py
"""
import os

ROWS = [
    ("SOTA-skills", 99, "sota"),
    ("affaan-m/ECC", 87, "comp"),
    ("PatrickJS/awesome-cursorrules", 83, "comp"),
    ("alirezarezvani/claude-skills", 81, "comp"),
    ("unguided model", 58, "base"),
]

THEMES = {
    "light": dict(surface="#ffffff", border="#d0d7de", ink="#1f2328", muted="#656d76",
                  track="#eaeef2", sota="#2fa45f", comp="#57606a", base="#8c959f"),
    "dark": dict(surface="#0d1117", border="#30363d", ink="#e6edf3", muted="#8b949e",
                 track="#21262d", sota="#3fb950", comp="#768390", base="#545d68"),
}

W, H = 720, 340
LABEL_X, BAR_X, BAR_MAX = 24, 250, 410
FIRST_TOP, ROW_H, BAR_H = 84, 46, 20
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"


def svg(theme_name):
    t = THEMES[theme_name]
    fill = {"sota": t["sota"], "comp": t["comp"], "base": t["base"]}
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="{FONT}" role="img" '
        f'aria-label="Best-practice completeness by library: SOTA-skills 99%, '
        f'affaan-m/ECC 87%, PatrickJS/awesome-cursorrules 83%, '
        f'alirezarezvani/claude-skills 81%, unguided model 58%.">',
        f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" '
        f'fill="{t["surface"]}" stroke="{t["border"]}"/>',
        f'<text x="{LABEL_X}" y="40" font-size="19" font-weight="700" '
        f'fill="{t["ink"]}">How complete is the generated code?</text>',
        f'<text x="{LABEL_X}" y="62" font-size="12" fill="{t["muted"]}">'
        f'% of a fixed best-practice rubric implemented — blind-judged, 7 build '
        f'tasks, content-only. Higher is better.</text>',
    ]
    for i, (name, pct, kind) in enumerate(ROWS):
        top = FIRST_TOP + i * ROW_H
        by = top + 13
        w = round(BAR_MAX * pct / 100, 1)
        weight = "700" if kind == "sota" else "400"
        out.append(f'<text x="{LABEL_X}" y="{by+15}" font-size="12.5" '
                   f'font-weight="{weight}" fill="{t["ink"]}">{name}</text>')
        out.append(f'<rect x="{BAR_X}" y="{by}" width="{BAR_MAX}" height="{BAR_H}" '
                   f'rx="4" fill="{t["track"]}"/>')
        out.append(f'<rect x="{BAR_X}" y="{by}" width="{w}" height="{BAR_H}" '
                   f'rx="4" fill="{fill[kind]}"/>')
        out.append(f'<text x="{BAR_X + w + 8}" y="{by+15}" font-size="13" '
                   f'font-weight="{weight}" fill="{t["ink"]}">{pct}%</text>')
    out.append(f'<text x="{LABEL_X}" y="323" font-size="10.5" fill="{t["muted"]}">'
               f'SOTA-skills wins or ties all 21 head-to-head cases (loses none) · '
               f'data: evals/results/RESULTS.md</text>')
    out.append('</svg>')
    return "\n".join(out) + "\n"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    for mode in ("light", "dark"):
        path = os.path.join(here, f"benchmark-{mode}.svg")
        open(path, "w", encoding="utf-8").write(svg(mode))
        print("wrote", path)


if __name__ == "__main__":
    main()
