#!/usr/bin/env python3
"""Generate the 5-domain breadth chart (light + dark SVG, + PNG if rsvg-convert).

Grouped horizontal bars: per domain (ordered by unguided baseline ascending), the
unguided baseline / best competitor / SOTA-skills completeness %. The story reads off
the picture: where the unguided bar is LOW, SOTA-skills (green) pulls clearly ahead;
where it is HIGH, all three converge. Numbers from the competitor-benchmark +
competitor-breadth-* result JSONs (2026-07-15/16). Regenerate:
  python3 assets/gen-breadth-chart.py
"""
import os, shutil, subprocess

# (domain, unguided, best-competitor, SOTA-skills) — ascending by baseline
ROWS = [
    ("Frontend — hard SSR / auth", 53, 83, 93),
    ("Python backend", 58, 87, 99),
    ("Go backend", 67, 87, 97),
    ("Frontend — simple forms", 77, 97, 97),
    ("IaC — K8s / Docker / Terraform", 87, 100, 100),
]
THEMES = {
    "light": dict(surface="#ffffff", border="#d0d7de", ink="#1f2328", muted="#656d76",
                  track="#eaeef2", sota="#2fa45f", comp="#57606a", base="#adb5bd"),
    "dark": dict(surface="#0d1117", border="#30363d", ink="#e6edf3", muted="#8b949e",
                 track="#21262d", sota="#3fb950", comp="#768390", base="#484f58"),
}
W, H = 760, 486
LABEL_X, BAR_X, BAR_MAX = 24, 232, 372
FIRST_TOP, GROUP_H, BAR_H, BAR_GAP = 108, 70, 13, 4
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"


def svg(theme):
    t = THEMES[theme]
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="{FONT}" '
         f'role="img" aria-label="Completeness by domain (unguided / best competitor / SOTA-skills): '
         f'hard frontend 53/83/93, Python backend 58/87/99, Go backend 67/87/97, simple frontend '
         f'77/97/97, IaC 87/100/100. SOTA-skills leads where the unguided baseline is low, ties where it is high.">',
         f'<rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" fill="{t["surface"]}" stroke="{t["border"]}"/>',
         f'<text x="{LABEL_X}" y="40" font-size="19" font-weight="700" fill="{t["ink"]}">'
         f'Where the library earns its keep</text>',
         f'<text x="{LABEL_X}" y="62" font-size="12" fill="{t["muted"]}">Completeness % by domain, ordered by '
         f'how complete an <tspan font-style="italic">unguided</tspan> model already is. SOTA-skills leads '
         f'where the model ships incomplete code; ties where it doesn’t.</text>']
    # legend
    leg = [("unguided model", t["base"]), ("best competitor", t["comp"]), ("SOTA-skills", t["sota"])]
    lx = LABEL_X
    for name, col in leg:
        o.append(f'<rect x="{lx}" y="80" width="12" height="12" rx="3" fill="{col}"/>')
        o.append(f'<text x="{lx+17}" y="90" font-size="11.5" fill="{t["ink"]}">{name}</text>')
        lx += 30 + len(name) * 6.9
    for i, (name, base, comp, sota) in enumerate(ROWS):
        gt = FIRST_TOP + i * GROUP_H
        o.append(f'<text x="{LABEL_X}" y="{gt + GROUP_H//2 + 2}" font-size="12" font-weight="600" '
                 f'fill="{t["ink"]}">{name}</text>')
        for j, (val, col) in enumerate([(base, t["base"]), (comp, t["comp"]), (sota, t["sota"])]):
            by = gt + 6 + j * (BAR_H + BAR_GAP)
            w = round(BAR_MAX * val / 100, 1)
            weight = "700" if j == 2 else "400"
            o.append(f'<rect x="{BAR_X}" y="{by}" width="{BAR_MAX}" height="{BAR_H}" rx="4" fill="{t["track"]}"/>')
            o.append(f'<rect x="{BAR_X}" y="{by}" width="{w}" height="{BAR_H}" rx="4" fill="{col}"/>')
            o.append(f'<text x="{BAR_X + w + 7}" y="{by + 10.5}" font-size="11.5" font-weight="{weight}" '
                     f'fill="{t["ink"]}">{val}%</text>')
    o.append(f'<text x="{LABEL_X}" y="{H-14}" font-size="10.5" fill="{t["muted"]}">Content-only, blind-judged; '
             f'best-competitor = the strongest of ECC / claude-skills / cursorrules per domain · '
             f'data: evals/results/2026-07-13/BREADTH.md</text>')
    o.append('</svg>')
    return "\n".join(o) + "\n"


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    rsvg = shutil.which("rsvg-convert")
    for mode in ("light", "dark"):
        p = os.path.join(here, f"breadth-{mode}.svg")
        open(p, "w", encoding="utf-8").write(svg(mode))
        print("wrote", p)
        if rsvg:
            png = os.path.join(here, f"breadth-{mode}.png")
            subprocess.run(["rsvg-convert", "-w", "1520", p, "-o", png], check=True)
            print("wrote", png)


if __name__ == "__main__":
    main()
