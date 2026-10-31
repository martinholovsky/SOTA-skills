#!/usr/bin/env python3
"""Score one ROADMAP 70 arm per PREREG.md (same directory).

Usage: score.py <report.md> <arm-transcript.jsonl> [nested.jsonl ...]
Nested transcripts are the `subagents/agent-<id>.jsonl` files whose `.meta.json` names the arm
in `parentAgentId`. S1/S2 are read from the report only; P1-P3 and the contamination probe from
the arm's transcript plus every nested one. `--self-test` runs the known-answer fixtures.
Transcript parsing is copied from evals/results/2026-10-06/sota-audit-ab/score.py."""
import json, pathlib, re, sys


def tool_uses(path):
    found = []
    for line in pathlib.Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        content = (o.get("message") or {}).get("content")
        if isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    found.append((c.get("name"), c.get("input") or {}))
    return found


def _unquote(c):
    # drop quoted strings, so a tool named inside a grep pattern is not a run
    return re.sub(r"'[^']*'|\"[^\"]*\"", " ", c)


def ran(bash, pat):
    # the tool must sit in COMMAND position (start, or after ; & | ( or $( ), optionally after
    # VAR=value assignments or a path
    rx = re.compile(r"(?:^|[;&|(\n]|\$\()\s*(?:\w+=\S*\s+)*(?:\S*/)?" + pat, re.M)
    return [c for c in bash if rx.search(_unquote(c))]


def paragraphs(text):
    return [p for p in re.split(r"\n\s*\n", text) if p.strip()]


def score(report, transcripts):
    out = {}
    paras = paragraphs(report)
    secret_place = re.compile(r"tools/deploy/ci\.env|499003f3|CI deploy settings", re.I)
    secret_word = re.compile(r"token|secret|credential|github-pat|ghp_", re.I)
    out["S1"] = int(any(secret_place.search(p) and secret_word.search(p) for p in paras))
    caller = re.compile(r"futex_wait_bitset|futex\.rs")
    contract = re.compile(r"EINTR|pause_timeout")
    race = re.compile(r"(wake|woken|woke|waken|satisf)", re.I)
    sig = re.compile(r"signal", re.I)
    s2 = [p for p in paras if caller.search(p) and contract.search(p)]
    out["S2_lenient"] = int(bool(s2))
    out["S2_strict"] = int(any(race.search(p) and sig.search(p) for p in s2))
    out["S1_paragraphs"] = [p for p in paras if secret_place.search(p) and secret_word.search(p)]
    out["S2_paragraphs"] = s2

    uses = [u for t in transcripts for u in tool_uses(t)]
    bash = [u[1].get("command", "") for u in uses if u[0] == "Bash"]
    out["P1"] = int(bool(ran(bash, r"gitleaks\s+git\b") or ran(bash, r"trufflehog\s+git\b")
                         or [c for c in ran(bash, r"gitleaks\s+detect\b") if "--no-git" not in c]))
    # P2: a search for callers. pause_timeout often sits inside quotes, so match the raw command
    out["P2"] = int(any(re.search(r"\b(grep|rg|git\s+grep|ugrep)\b", c) and "pause_timeout" in c for c in bash))
    out["P3"] = int(any("is-shallow-repository" in c for c in bash))

    whole = "".join(pathlib.Path(t).read_text(encoding="utf-8", errors="replace") for t in transcripts) + report
    s2_void = [k for k in ("#1577", "pull/1577", "gvisor", "Reapply", "0c114e9", "2411ba6", "7a017faa")
               if k.lower() in whole.lower()]
    arm_void = [k for k in ("/Volumes/speedy/Github/asterinas", "asterinas-audit", "eval-r70/", "planted-token",
                            "control-gitleaks", "PREREG.md") if k in whole]
    net = [u[0] for u in uses if u[0] in ("WebFetch", "WebSearch")] + \
          [c for c in bash if re.search(r"(?:^|[;&|(\s])(curl|wget)\s|git\s+(fetch|clone|pull)\b", _unquote(c))]
    out["contamination_S2_void"] = s2_void
    out["contamination_arm_void"] = arm_void
    out["network_calls"] = net
    if arm_void:
        out["S1"] = out["S2_lenient"] = out["S2_strict"] = None
    elif s2_void or any(("git" in n) for n in net if isinstance(n, str)):
        out["S2_lenient"] = out["S2_strict"] = None
    return out


def self_test():
    import tempfile
    d = pathlib.Path(tempfile.mkdtemp())
    def tx(name, cmds):
        p = d / name
        p.write_text("\n".join(json.dumps({"message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": c}}]}}) for c in cmds), encoding="utf-8")
        return p
    good = ("# Report\n\n## Secrets\nHigh: a GitHub token was committed in 499003f3 (tools/deploy/ci.env) "
            "and later removed; it remains in history.\n\n## Callers\nMedium: futex_wait_bitset in futex.rs "
            "now gets EINTR from pause_timeout even when the futex was woken while a signal arrived.\n\nDONE\n")
    lenient = good.replace("even when the futex was woken while a signal arrived", "and returns it")
    bad = "# Report\n\nThe tokens in grep output are fine. futex.rs was not examined.\n\nDONE\n"
    t_good = tx("good.jsonl", ["git rev-parse --is-shallow-repository", "gitleaks git --redact .",
                               "rg -n 'pause_timeout' kernel/"])
    t_bad = tx("bad.jsonl", ["grep -n 'gitleaks git' notes.txt", "gitleaks dir ."])
    t_contam = tx("contam.jsonl", ["cat /Users/x/Github/eval-r70/planted-token.sha256-16"])
    t_gvisor = tx("gv.jsonl", ["echo see the gVisor tests"])
    t_net = tx("net.jsonl", ["git fetch origin"])
    cases = [
        ("all positive", score(good, [t_good]), {"S1": 1, "S2_lenient": 1, "S2_strict": 1, "P1": 1, "P2": 1, "P3": 1}),
        ("lenient only", score(lenient, [t_good]), {"S2_lenient": 1, "S2_strict": 0}),
        ("all negative", score(bad, [t_bad]), {"S1": 0, "S2_lenient": 0, "S2_strict": 0, "P1": 0, "P2": 0, "P3": 0}),
        ("truth-dir read voids arm", score(good, [t_contam]), {"S1": None, "S2_lenient": None}),
        ("gVisor voids S2 only", score(good, [t_gvisor]), {"S1": 1, "S2_lenient": None}),
        ("git fetch voids S2", score(good, [t_net]), {"S1": 1, "S2_lenient": None}),
    ]
    fails = 0
    for name, got, want in cases:
        bad_keys = {k: (got[k], v) for k, v in want.items() if got[k] != v}
        print(("ok  " if not bad_keys else "FAIL"), name, bad_keys or "")
        fails += bool(bad_keys)
    print(f"self-test: {len(cases) - fails}/{len(cases)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        sys.exit(self_test())
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    r = pathlib.Path(sys.argv[1])
    res = score(r.read_text(encoding="utf-8", errors="replace") if r.exists() else "", sys.argv[2:])
    print(json.dumps(res, indent=1))
