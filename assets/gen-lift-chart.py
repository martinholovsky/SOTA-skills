#!/usr/bin/env python3
"""Generate the with-vs-without lift chart (light + dark) in assets/.

The front-door answer to "does the library actually change the output, and is that
still true?" — every headline dimension, both arms, on TWO model generations, so the
reader sees the lift AND whether it survived model progress. That second axis is the
point: a lift is a gap between a model and a standard, and the model side moves.

Three outcome shapes are visible directly in the bars:
  * completeness   — flat across a generation (a SALIENCE gap; models don't close it)
  * freshness      — shrinking (a RENEWABLE knowledge gap; the cutoff advances into a
                     fixed question set, so a fixed set under-reads its own claim)
  * defects avoided— collapsed to zero (a CLOSABLE knowledge gap; the model learned it)
  * routing        — flat, and notably not saturated

Numbers come from evals/results/RESULTS.md (which cites the per-run write-ups):
sonnet-4.6 rows from 2026-07-12/13 and 2026-08-21; sonnet-5 rows from
2026-08-21/COMPLETENESS-SONNET-5.md, 2026-08-21/BUILD-SAFE.md §1c and
2026-08-25/ITEM-20-FRESHNESS-ROUTING.md.

Bars and deltas are computed from UNROUNDED means; the printed scores are rounded to
2dp, so one row (routing on sonnet-5: 0.867 -> 0.994) shows a delta that does not equal
the difference of its two rounded labels. That is the rounding, not an error.

Emits both SVG (used on GitHub) and, if `rsvg-convert` is installed, a 2x PNG.

Regenerate: python3 assets/gen-lift-chart.py
"""
import os
import shutil
import subprocess

# (dimension, note, [(model, without, with)]) — unrounded means.
GROUPS = [
    ("Completeness", "durable — a salience gap, and models do not close it", [
        ("claude-sonnet-4.6", 0.59, 0.98),
        ("claude-sonnet-5", 0.62, 1.00),
    ]),
    ("Freshness", "erodes — the cutoff advances into a fixed question set", [
        ("claude-sonnet-4.6", 0.44, 0.97),
        ("claude-sonnet-5", 0.688, 0.990),
    ]),
    ("Routing", "holds — unchanged within the set's one-case resolution", [
        ("claude-sonnet-4.6", 0.90, 1.00),
        ("claude-sonnet-5", 0.867, 0.994),
    ]),
    ("Defects avoided", "EXPIRED — the newer model no longer writes them unaided", [
        ("claude-sonnet-4.6", 0.81, 1.00),
        ("claude-sonnet-5", 1.00, 1.00),
    ]),
]

THEMES = {
    "light": dict(surface="#ffffff", border="#d0d7de", ink="#1f2328", muted="#656d76",
                  track="#eaeef2", base="#8c959f", lift="#2fa45f", dead="#bcc4cc"),
    "dark": dict(surface="#0d1117", border="#30363d", ink="#e6edf3", muted="#8b949e",
                 track="#21262d", base="#545d68", lift="#3fb950", dead="#3d444d"),
}

W, H = 820, 500
LABEL_X, BAR_X, BAR_MAX = 24, 236, 330
FIRST_TOP, GROUP_H, ROW_H, BAR_H = 96, 100, 30, 17
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"


def svg(theme_name):
    t = THEMES[theme_name]
    alt = ("Measured lift with the library vs without, on two model generations. "
           + "; ".join(
               f"{dim}: " + ", ".join(
                   f"{m} {wo:.2f} to {wi:.2f}, lift {wi-wo:+.2f}" for m, wo, wi in rows)
               for dim, _, rows in GROUPS)
           + ". Completeness and routing hold across the generation, freshness erodes, "
             "defect-avoidance expires.")
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'font-family="{FONT}" role="img" aria-label="{alt}">',
        f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" '
        f'fill="{t["surface"]}" stroke="{t["border"]}"/>',
        f'<text x="{LABEL_X}" y="40" font-size="19" font-weight="700" '
        f'fill="{t["ink"]}">Does the library change the output — and is that still true?</text>',
        f'<text x="{LABEL_X}" y="62" font-size="12" fill="{t["muted"]}">'
        f'Grey = the model alone. Green = what loading the library adds. '
        f'Each dimension measured on two model generations.</text>',
        # legend
        f'<rect x="{LABEL_X}" y="72" width="22" height="9" rx="2" fill="{t["base"]}"/>',
        f'<text x="{LABEL_X+28}" y="80" font-size="10.5" fill="{t["muted"]}">unguided</text>',
        f'<rect x="{LABEL_X+92}" y="72" width="22" height="9" rx="2" fill="{t["lift"]}"/>',
        f'<text x="{LABEL_X+120}" y="80" font-size="10.5" fill="{t["muted"]}">with SOTA-skills</text>',
    ]
    for gi, (dim, note, rows) in enumerate(GROUPS):
        gtop = FIRST_TOP + gi * GROUP_H
        out.append(f'<text x="{LABEL_X}" y="{gtop}" font-size="13.5" font-weight="700" '
                   f'fill="{t["ink"]}">{dim}</text>')
        out.append(f'<text x="{LABEL_X + 9.2 * len(dim) + 10}" y="{gtop}" font-size="11" '
                   f'fill="{t["muted"]}">{note}</text>')
        for ri, (model, wo, wi) in enumerate(rows):
            by = gtop + 12 + ri * ROW_H
            w_base = round(BAR_MAX * wo, 1)
            w_lift = round(BAR_MAX * (wi - wo), 1)
            lift = wi - wo
            newest = ri == len(rows) - 1
            out.append(f'<text x="{LABEL_X + 8}" y="{by + 13}" font-size="11.5" '
                       f'font-weight="{"600" if newest else "400"}" '
                       f'fill="{t["ink"] if newest else t["muted"]}">{model}</text>')
            out.append(f'<rect x="{BAR_X}" y="{by}" width="{BAR_MAX}" height="{BAR_H}" '
                       f'rx="3" fill="{t["track"]}"/>')
            out.append(f'<rect x="{BAR_X}" y="{by}" width="{w_base}" height="{BAR_H}" '
                       f'rx="3" fill="{t["base"]}"/>')
            if w_lift > 0.5:
                out.append(f'<rect x="{BAR_X + w_base}" y="{by}" width="{w_lift}" '
                           f'height="{BAR_H}" rx="3" fill="{t["lift"]}"/>')
            tx = BAR_X + BAR_MAX + 10
            out.append(f'<text x="{tx}" y="{by + 13}" font-size="11.5" '
                       f'fill="{t["muted"]}">{wo:.2f} → {wi:.2f}</text>')
            colour = t["dead"] if abs(lift) < 0.005 else t["lift"]
            out.append(f'<text x="{tx + 84}" y="{by + 13}" font-size="12.5" '
                       f'font-weight="700" fill="{colour}">{lift:+.2f}</text>')
    out.append(f'<text x="{LABEL_X}" y="{H - 16}" font-size="10.5" fill="{t["muted"]}">'
               f'Bars and deltas from unrounded means; labels rounded to 2dp · '
               f'every number dated to the model it was measured on · '
               f'data and method: evals/results/RESULTS.md</text>')
    out.append('</svg>')
    return "\n".join(out) + "\n"


PNG_WIDTH = 1640  # 2x the 820px viewBox — retina / social-share resolution


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    have_rsvg = shutil.which("rsvg-convert")
    for mode in ("light", "dark"):
        svg_path = os.path.join(here, f"lift-{mode}.svg")
        open(svg_path, "w", encoding="utf-8").write(svg(mode))
        print("wrote", svg_path)
        if have_rsvg:
            png_path = os.path.join(here, f"lift-{mode}.png")
            subprocess.run(["rsvg-convert", "-w", str(PNG_WIDTH), svg_path, "-o", png_path],
                           check=True)
            print("wrote", png_path)
    if not have_rsvg:
        print("note: rsvg-convert not found — SVGs written, PNGs skipped "
              "(install librsvg, or: rsvg-convert -w 1640 lift-light.svg -o lift-light.png)")


if __name__ == "__main__":
    main()
