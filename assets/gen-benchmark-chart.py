#!/usr/bin/env python3
"""Generate the competitor-benchmark bar chart (light + dark) in assets/.

A single-measure magnitude chart: best-practice completeness (%) per library, with
SOTA-skills emphasized. Identity is carried by the text labels (each bar is named),
so color is not load-bearing — the brand green marks SOTA-skills, recessive grays
carry the rest. Numbers come from evals/results/2026-07-13/competitor-benchmark.json
(the 7-task, content-only, blind-judged means, rounded to whole %).

Emits both SVG (used on GitHub) and, if `rsvg-convert` is installed, a 2x PNG
(1440px wide — for LinkedIn/slides/anywhere SVG isn't supported).

Regenerate: python3 assets/gen-benchmark-chart.py
"""
import os
import shutil
import subprocess

# ONE baseline row, shown as a BAND, not two rows.
#
# An earlier version drew two "unguided model" bars (58% and 64%) because the
# competitor benchmark and the superpowers head-to-head are separate runs whose
# unguided arms differ -- temp-0 is not deterministic. It was accurate and it read
# as a bug: a reader's first reaction was "why two baselines with two numbers?".
# Confusion is a real cost, and explaining it in a footnote does not undo it.
#
# So the baseline is a single row spanning 58-64%, drawn as a solid bar to 58 with a
# lighter extension to 64. That is honest about the spread AND makes the point the
# two rows existed to make: obra/superpowers at 60% lands INSIDE the band, so it is
# not distinguishable from no guidance at all. Nothing is claimed that the runs
# cannot support, and there is only one baseline on the chart.
#
# Star counts are live-fetched context, not a metric: they say these are the POPULAR
# libraries. SOTA-skills deliberately carries none -- comparing our own star count
# here would be a different (and irrelevant) claim. Fetched 2026-09-10; stars rot,
# so the footer dates them.
ROWS = [
    ("SOTA-skills",                        99, "sota", ""),
    ("affaan-m/ECC",                       87, "comp", "255k"),
    ("PatrickJS/awesome-cursorrules",      83, "comp", "41k"),
    ("alirezarezvani/claude-skills",       81, "comp", "26k"),
    ("obra/superpowers",                   60, "comp", "284k"),
]
BASE_LO, BASE_HI = 58, 64          # unguided, across the two runs

THEMES = {
    "light": dict(surface="#ffffff", border="#d0d7de", ink="#1f2328", muted="#656d76",
                  track="#eaeef2", sota="#2fa45f", comp="#57606a", base="#8c959f"),
    "dark": dict(surface="#0d1117", border="#30363d", ink="#e6edf3", muted="#8b949e",
                 track="#21262d", sota="#3fb950", comp="#768390", base="#545d68"),
}

W, H = 760, 420
LABEL_X, BAR_X, BAR_MAX = 24, 300, 350
FIRST_TOP, ROW_H, BAR_H = 84, 46, 20
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"


def svg(theme_name):
    t = THEMES[theme_name]
    fill = {"sota": t["sota"], "comp": t["comp"], "base": t["base"]}
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="{FONT}" role="img" '
        f'aria-label="Best-practice completeness by library: SOTA-skills 99%, '
        f'affaan-m/ECC 87% (255k stars), PatrickJS/awesome-cursorrules 83% (41k stars), '
        f'alirezarezvani/claude-skills 81% (26k stars), obra/superpowers 60% (284k stars), '
        f'and an unguided model at 58 to 64 percent across the two runs. Superpowers falls '
        f'inside the unguided band, so it is not distinguishable from no guidance.">',
        f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" '
        f'fill="{t["surface"]}" stroke="{t["border"]}"/>',
        f'<text x="{LABEL_X}" y="40" font-size="19" font-weight="700" '
        f'fill="{t["ink"]}">How complete is the generated code?</text>',
        f'<text x="{LABEL_X}" y="62" font-size="12" fill="{t["muted"]}">'
        f'% of a fixed best-practice rubric implemented — blind-judged, 7 build '
        f'tasks, content-only. Higher is better.</text>',
    ]
    def row(i, name, stars, pct, kind, band_hi=None):
        top = FIRST_TOP + i * ROW_H
        by = top + 13
        w = round(BAR_MAX * pct / 100, 1)
        weight = "700" if kind == "sota" else "400"
        out.append(f'<text x="{LABEL_X}" y="{by+15}" font-size="12.5" '
                   f'font-weight="{weight}" fill="{t["ink"]}">{name}</text>')
        if stars:
            out.append(f'<text x="{BAR_X - 10}" y="{by+15}" font-size="11" '
                       f'text-anchor="end" fill="{t["muted"]}">{stars}\u2605</text>')
        out.append(f'<rect x="{BAR_X}" y="{by}" width="{BAR_MAX}" height="{BAR_H}" '
                   f'rx="4" fill="{t["track"]}"/>')
        if band_hi is not None:
            # the lighter extension: the same baseline measured in the other run
            wh = round(BAR_MAX * band_hi / 100, 1)
            out.append(f'<rect x="{BAR_X}" y="{by}" width="{wh}" height="{BAR_H}" '
                       f'rx="4" fill="{t["base"]}" opacity="0.62"/>')
        out.append(f'<rect x="{BAR_X}" y="{by}" width="{w}" height="{BAR_H}" '
                   f'rx="4" fill="{fill[kind]}"/>')
        label = f"{pct}%" if band_hi is None else f"{pct}\u2013{band_hi}%"
        x = BAR_X + (w if band_hi is None else round(BAR_MAX * band_hi / 100, 1)) + 8
        out.append(f'<text x="{x}" y="{by+15}" font-size="13" '
                   f'font-weight="{weight}" fill="{t["ink"]}">{label}</text>')

    for i, (name, pct, kind, stars) in enumerate(ROWS):
        row(i, name, stars, pct, kind)
    row(len(ROWS), "unguided model", "", BASE_LO, "base", BASE_HI)

    out.append(f'<text x="{LABEL_X}" y="{H-31}" font-size="10.5" fill="{t["muted"]}">'
               f'SOTA-skills wins or ties all 21 head-to-head cases (loses none) · '
               f'data: evals/results/RESULTS.md</text>')
    out.append(f'<text x="{LABEL_X}" y="{H-14}" font-size="10.5" fill="{t["muted"]}">'
               f'unguided band = the same arm measured in two runs (58% 2026-07-14, 64% 2026-09-08); '
               f'superpowers falls inside it \u00b7 stars fetched 2026-09-10</text>')
    out.append('</svg>')
    return "\n".join(out) + "\n"


PNG_WIDTH = 1440  # 2x the 720px viewBox — retina / social-share resolution


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    have_rsvg = shutil.which("rsvg-convert")
    for mode in ("light", "dark"):
        svg_path = os.path.join(here, f"benchmark-{mode}.svg")
        open(svg_path, "w", encoding="utf-8").write(svg(mode))
        print("wrote", svg_path)
        if have_rsvg:
            png_path = os.path.join(here, f"benchmark-{mode}.png")
            subprocess.run(["rsvg-convert", "-w", str(PNG_WIDTH), svg_path, "-o", png_path],
                           check=True)
            print("wrote", png_path)
    if not have_rsvg:
        print("note: rsvg-convert not found — SVGs written, PNGs skipped "
              "(install librsvg, or: rsvg-convert -w 1440 benchmark-light.svg -o benchmark-light.png)")


if __name__ == "__main__":
    main()
