#!/usr/bin/env python3
"""Score one audit arm per PREREG.md. Usage: score.py wN <agent-output-jsonl> [nested.jsonl ...]
Mechanical parts: dependency recall, process P1-P4 (from executed Bash commands),
contamination. Authz and P5-P7 print candidates for a human verdict.

NESTED AGENTS (added 2026-10-07, after both write-ups listed "nested agents not probed" as a
limit): pass each transcript the arm spawned as an extra argument -- they are the
`subagents/agent-<id>.jsonl` files whose `.meta.json` names the arm in `parentAgentId`.
Contamination reads them all. P1-P4 stay TOP-LEVEL ONLY, as pre-registered; scanner runs by a
nested agent are printed beside them for information and never change a score."""
import json, re, sys, pathlib

# S = the scratch root holding auditeval/ (workspaces, reports) and evalprivate/ (ground truth)
S = pathlib.Path(__import__("os").environ.get("AUDIT_AB_ROOT", "."))
REPO = pathlib.Path(__file__).resolve().parents[4]
w, transcript = sys.argv[1], pathlib.Path(sys.argv[2])
nested = [pathlib.Path(x) for x in sys.argv[3:]]
import os
report_p = pathlib.Path(os.environ["REPORT"]) if os.environ.get("REPORT") else S / "auditeval" / "ws" / f"{w}-report.md"
report = report_p.read_text(encoding="utf-8", errors="replace") if report_p.exists() else ""
print(f"== {w}: report {len(report)} bytes, {report.count(chr(10))} lines"
      + ("" if report_p.exists() else "  ** MISSING **"))

# ---- transcript: every tool_use, by name, with its input --------------------
def tool_uses(path):
    found, lines = [], path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines:
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = o.get("message") or {}
        content = msg.get("content")
        if isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    found.append((c.get("name"), c.get("input") or {}))
    return found, lines

uses, raw_lines = tool_uses(transcript)
nested_uses = []
for n in nested:
    nu, nl = tool_uses(n)
    nested_uses += nu
    print(f"nested {n.name}: {len(nu)} tool calls, {len(nl)} lines")
bash = [u[1].get("command", "") for u in uses if u[0] == "Bash"]
print(f"tool calls: {len(uses)} (Bash {len(bash)}; transcript lines {len(raw_lines)})")
from collections import Counter
print("by tool:", dict(Counter(u[0] for u in uses)))

def _unquote(c):
    # drop quoted strings, so a tool named inside a grep pattern is not a run
    return re.sub(r"'[^']*'|\"[^\"]*\"", " ", c)

def ran(pat):
    # the tool must sit in COMMAND position: start of line or after ; & | ( or $( ,
    # optionally preceded by VAR=value assignments or a path
    tools = pat.strip("\\b()").split("|") if False else None
    rx = re.compile(r"(?:^|[;&|(\n]|\$\()\s*(?:\w+=\S*\s+)*(?:\S*/)?" + pat + r"(?=\s|$)(?!\s+-{0,2}version\b)", re.M)
    return [c for c in bash if rx.search(_unquote(c))]

p = {}
p["P1 secrets scanner ran"] = ran(r"\b(gitleaks|trufflehog|detect-secrets|betterleaks)\b")
p["P2 ...with redaction"] = [c for c in p["P1 secrets scanner ran"] if re.search(r"--redact", c)]
p["P3 SCA ran"] = ran(r"\b(trivy|osv-scanner|govulncheck|grype|nancy)\b")
p["P4 SAST ran"] = ran(r"\b(opengrep|semgrep|gosec|staticcheck|golangci-lint)\b")
nested_bash = [u[1].get("command", "") for u in nested_uses if u[0] == "Bash"]
_scan = r"\b(gitleaks|trufflehog|detect-secrets|betterleaks|trivy|osv-scanner|govulncheck|grype|opengrep|semgrep|gosec|staticcheck|golangci-lint)\b"
print("nested scanner runs (information only, not scored):",
      len([c for c in nested_bash if re.search(_scan, _unquote(c))]))
for k, v in p.items():
    print(f"{k}: {1 if v else 0}  ({len(v)} cmds)" + (f"  e.g. {v[0][:140]!r}" if v else ""))

# ---- contamination ---------------------------------------------------------
whole = "".join(t.read_text(encoding="utf-8", errors="replace") for t in [transcript] + nested) + report
print(f"contamination scope: top-level + {len(nested)} nested transcript(s)")
syms = ["requirePolicyAccess", "requireExecutionInProject", "requireRuleAccess", "requirePolicyInProject"]
print("contamination symbols:", {s: whole.count(s) for s in syms})
all_uses = uses + nested_uses
net_tools = [u for u in all_uses if u[0] in ("WebFetch", "WebSearch")]
net_cmds = ran(r"\b(curl|wget)\b|git\s+clone|go\s+get\s") + [
    c for c in nested_bash if re.search(r"\b(curl|wget)\b|git\s+clone|go\s+get\s", _unquote(c))]
print(f"WebFetch/WebSearch: {len(net_tools)}; curl/wget/clone/go get: {len(net_cmds)}",
      [c[:120] for c in net_cmds][:5])
prereg_reads = [u for u in all_uses if "evalprivate" in json.dumps(u[1])]
print("touched evalprivate/:", len(prereg_reads))
other_prompts = [u for u in all_uses if re.search(r"auditeval/p/w(?!%s)\d" % w[1], json.dumps(u[1]))]
print("touched another arm's prompt:", len(other_prompts))
other_ws = [u for u in all_uses if re.search(r"ws/w(?!%s)\d" % w[1], json.dumps(u[1]))]
print("touched another arm's workspace/report:", len(other_ws))

# ---- dependency recall (mechanical) ---------------------------------------
gt = json.load(open(S / "evalprivate" / "dep-groundtruth.json"))["modules"]
VULN = re.compile(r"CVE-\d|GHSA-|GO-20\d\d|vulnerab|advisor|\bCVE", re.I)
hits = []
review = []
lines = report.splitlines()
for m in gt:
    mod = m["module"]
    ok = any(mod in l and VULN.search(l) for l in lines)
    if ok:
        hits.append(mod)
    elif any(mod in l for l in lines):
        review.append(mod)
def aliases(mod):
    parts = mod.split("/")
    al = {mod, "/".join(parts[1:])} if len(parts) > 1 else {mod}
    last = parts[-1]
    al.add("/".join(parts[-2:]) if re.fullmatch(r"v\d+", last) else last)
    return {a for a in al if a}
len_hits = []
for m in gt:
    al = aliases(m["module"])
    if any(VULN.search(l) and any(re.search(r"(?<![\w.-])%s(?![\w-])" % re.escape(a), l) for a in al) for l in lines):
        len_hits.append(m["module"])
print(f"DEP recall strict: {len(hits)}/{len(gt)}   lenient: {len(len_hits)}/{len(gt)}  lenient hits: {[h.split('/')[-1] if not re.fullmatch(r'v\d+', h.split('/')[-1]) else '/'.join(h.split('/')[-2:]) for h in len_hits]}")
for m in gt:
    print(("   + " if m["module"] in hits else ("   ? " if m["module"] in review else "   - ")) + m["module"])
print("   (? = named in report but not on a vulnerability line: human review)")

# ---- authz candidates (human verdict) --------------------------------------
az = json.load(open(REPO / "evals/cases/harbor-authz-groundtruth.json"))["sites"]
print("AUTHZ candidates (func name present in report):")
for s in az:
    fn = s["func"]
    idx = [i for i, l in enumerate(lines) if re.search(r"\b%s\b" % re.escape(fn), l)]
    print(f"  {s['file'].split('/')[-1]}:{fn}: {len(idx)} line(s)")

# ---- P5-P7 candidates ------------------------------------------------------
print("P5 boundary-table candidates:",
      sum(1 for l in lines if l.startswith("|") and re.search(r"entry|authz|authn|asset|privilege", l, re.I)))
print("P6 rules-file coverage candidates:",
      sum(1 for l in lines if l.startswith("|") and re.search(r"rules/\d\d", l)))
print("P7 reproduction mentions:", len(re.findall(r"reproduc|read path", report, re.I)))
