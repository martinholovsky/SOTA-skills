#!/usr/bin/env python3
"""Authz location matcher. Usage: authz.py <report.md>
For each of the 16 ground-truth sites: credited-by-location if the report names the function
or cites a line inside the function's span (from the pristine v2.5.1 source). Prints the
report lines that located it, so the 'describes a missing ownership check' half is judged
by a human reading them."""
import json, re, sys, pathlib

# S = the scratch root holding auditeval/ (workspaces, reports) and evalprivate/ (ground truth)
S = pathlib.Path(__import__("os").environ.get("AUDIT_AB_ROOT", "."))
SRC = S / "auditeval" / "src-pristine"
GT = json.load(open(pathlib.Path(__file__).resolve().parents[4] / "evals/cases/harbor-authz-groundtruth.json"))["sites"]
report = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").splitlines()

def spans(path):
    lines = (SRC / path).read_text().splitlines()
    starts = [(i + 1, m.group(1)) for i, l in enumerate(lines)
              for m in [re.match(r"func (?:\([^)]*\)\s*)?(\w+)\(", l)] if m]
    out = {}
    for k, (ln, name) in enumerate(starts):
        end = starts[k + 1][0] - 1 if k + 1 < len(starts) else len(lines)
        out[name] = (ln, end)
    return out

# every "file.go:N" or "file.go:N,M,K" or "file.go:N/M" or "file.go:N-M" reference
REF = re.compile(r"([\w./-]*?(\w+\.go)):((?:\d+(?:\s*[-,/]\s*)?)+)")
found = 0
for s in GT:
    base = s["file"].split("/")[-1]
    lo, hi = spans(s["file"])[s["func"]]
    assert lo <= s["line_v251"] <= hi, (s, lo, hi)   # positive control on the span math
    why = []
    for n, l in enumerate(report, 1):
        if re.search(r"\b%s\b" % re.escape(s["func"]), l):
            why.append((n, "func"))
            continue
        # walk file refs and bare continuation refs (`:143`) in order; a bare ref
        # belongs to the most recently named .go file on the same line
        cur, hit = None, False
        for m in re.finditer(r"(\w+\.go):((?:\d+(?:\s*[-,/+]\s*)?)+)|(?<![\w.]):(\d+)", l):
            if m.group(1):
                cur = m.group(1); nums = [int(x) for x in re.findall(r"\d+", m.group(2))]
            else:
                nums = [int(m.group(3))]
            if cur == base and any(lo <= x <= hi for x in nums):
                hit = True
                break
        if hit:
            why.append((n, f"line in {lo}-{hi}"))
    ok = bool(why)
    found += ok
    print(f"{'+' if ok else '-'} {base}:{s['func']} [{lo}-{hi}]  " + ", ".join(f"L{n}({w})" for n, w in why[:4]))
print(f"AUTHZ located: {found}/{len(GT)}  (then read the cited lines for the ownership-check description)")
