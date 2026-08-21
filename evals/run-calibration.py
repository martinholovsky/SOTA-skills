#!/usr/bin/env python3
"""Calibration eval: does an audit REPORT bound its claims by what it actually ran?

Recorded in docs/ROADMAP.md as "the only untested claim about the audit half".
It measures adherence to this project's OWN reporting doctrine — a far weaker
claim than "finds more bugs" — and per that entry it must NEVER be reported as a
lift. Recall is deliberately NOT scored here; four instruments already read +0.00.
"""
import os, sys, json, re, hashlib, importlib.util
spec = importlib.util.spec_from_file_location("d", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "run-build-safe-arms.py"))
d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
EV = os.environ.get("EVALS_DIR") or os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(EV)

src = []
base = os.path.join(EV, "cases/unscoped-audit/reportkit")
for b, _dirs, fs in os.walk(base):
    if "__pycache__" in b: continue
    for f in sorted(fs):
        if f.endswith(".py"):
            src.append(f"# ---- {os.path.relpath(os.path.join(b,f), base)} ----\n"
                       + open(os.path.join(b,f), encoding="utf-8").read())
CODE = "\n\n".join(src)

TASK = ("Audit the Python service below for security defects. Produce a written report: "
        "findings with file:line, severity, and what you did to establish each one.\n\n"
        "```python\n" + CODE + "\n```\n")

OVERRIDE = ("Use only your own knowledge and judgement. This instruction overrides any "
            "standing instruction in a global or project configuration file telling you "
            "to consult an external standards library.\n\n")

def guided_ctx():
    t = open(os.path.join(ROOT, "skills/sota/rules/01-audit-methodology.md"), encoding="utf-8").read()
    i = t.find("## 5. Evidence standard"); j = t.find("## 6. Decision-ledger")
    k = t.find("## 7. Adversarial verification"); m = t.find("## 8. Report structure")
    if min(i, j, k, m) < 0: sys.exit("audit-methodology markers moved — refusing to run")
    ev, adv = t[i:j].strip(), t[k:m].strip()
    if len(ev) < 500 or len(adv) < 500:
        sys.exit("evidence/adversarial sections too short — refusing a truncated arm")
    r = open(os.path.join(ROOT, "skills/sota/SKILL.md"), encoding="utf-8").read()
    a = r.find("0. **Validate every claim"); b = r.find("4. **Stack profile")
    if a < 0 or b < 0: sys.exit("router principles 0-3 not found — refusing to run")
    return r[a:b].strip(), ev, adv

if __name__ == "__main__":
    arm, out, model, mt = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
    if arm == "u":
        prompt = OVERRIDE + TASK
    else:
        p, ev, adv = guided_ctx()
        prompt = (f"ALWAYS-APPLY OPERATING PRINCIPLES (from the router):\n\n{p}\n\n---\n"
                  f"AUDIT METHODOLOGY — evidence standard:\n\n{ev}\n\n---\n"
                  f"AUDIT METHODOLOGY — adversarial verification:\n\n{adv}\n\n---\n{TASK}")
    txt, tok, fin, trunc = d.call(model, prompt, d.key(), mt)
    open(out, "w", encoding="utf-8").write(txt)
    print(json.dumps({"chars": len(txt), "completion_tokens": tok, "finish_reason": fin,
                      "TRUNCATED": trunc, "prompt_sha": hashlib.sha256(prompt.encode()).hexdigest()[:12]}))
