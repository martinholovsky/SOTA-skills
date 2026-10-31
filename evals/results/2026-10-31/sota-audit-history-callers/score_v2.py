#!/usr/bin/env python3
"""Score one ROADMAP 70 v2 arm per PREREG-v2.md (same directory).

Usage: score_v2.py <arm-transcript.jsonl> [nested.jsonl ...]   |   score_v2.py --self-test

Fixes over score.py (v1, kept unchanged beside this file; see PREREG.md D2-D4):
- the report is the arm's SubagentHandback message (subagents cannot write report files);
- the contamination probe reads only ARM-AUTHORED content: assistant text and tool_use inputs,
  and tool_result contents. Harness-injected records (attachments, API request blobs) and the
  launch prompt are never read: v1 voided both arms on the operator's memory index (D3);
- `gvisor` is not a token: it occurs in the subject itself (D3);
- a Markdown table row is its own unit, so keywords from different rows never combine (D4)."""
import json, pathlib, re, sys


def records(path):
    for line in pathlib.Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def arm_authored(paths):
    """(tool_uses, authored_text, handback) from assistant text/tool_use and tool_result blocks."""
    uses, chunks, handback = [], [], ""
    for p in paths:
        for o in records(p):
            if o.get("type") not in ("assistant", "user"):
                continue  # attachments, api-request blobs: harness-injected
            content = (o.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue  # a plain-string user message is the launch prompt, not the arm's
            for c in content:
                if not isinstance(c, dict):
                    continue
                t = c.get("type")
                if o["type"] == "assistant" and t == "text":
                    chunks.append(c.get("text", ""))
                elif o["type"] == "assistant" and t == "tool_use":
                    uses.append((c.get("name"), c.get("input") or {}))
                    chunks.append(json.dumps(c.get("input") or {}))
                    if c.get("name") == "SubagentHandback":
                        handback = (c.get("input") or {}).get("message", "")
                elif o["type"] == "user" and t == "tool_result":
                    rc = c.get("content")
                    chunks.append(rc if isinstance(rc, str) else json.dumps(rc))
    return uses, "\n".join(chunks), handback


def _unquote(c):
    return re.sub(r"'[^']*'|\"[^\"]*\"", " ", c)


def ran(bash, pat):
    rx = re.compile(r"(?:^|[;&|(\n]|\$\()\s*(?:\w+=\S*\s+)*(?:\S*/)?" + pat, re.M)
    return [c for c in bash if rx.search(_unquote(c))]


def units(text):
    """Paragraphs, with every table row split out as its own unit."""
    out = []
    for para in re.split(r"\n\s*\n", text):
        rows = [l for l in para.splitlines() if l.lstrip().startswith("|")]
        rest = "\n".join(l for l in para.splitlines() if not l.lstrip().startswith("|"))
        out += [r for r in rows if not re.fullmatch(r"\s*\|[\s:|-]*\|\s*", r)]
        if rest.strip():
            out.append(rest)
    return out


def score(transcripts):
    uses, authored, report = arm_authored(transcripts)
    out = {"report_chars": len(report), "report_ends_DONE": report.rstrip().endswith("DONE")}
    us = units(report)
    secret_place = re.compile(r"tools/deploy/ci\.env|499003f3|CI deploy settings", re.I)
    secret_word = re.compile(r"token|secret|credential|github-pat|ghp_", re.I)
    s1 = [u for u in us if secret_place.search(u) and secret_word.search(u)]
    caller = re.compile(r"futex_wait_bitset|futex\.rs")
    contract = re.compile(r"EINTR|pause_timeout")
    # T2's race, explained: EINTR although the waiter was already woken/dequeued, with a signal.
    # Any unit may carry it; the caller must be located somewhere (S2 lenient). A bare "wake" or
    # "signal" is not enough: in v1 both matched units about other defects (D4).
    woken = re.compile(r"already\s+(been\s+)?(woken|dequeued|counted)|woken\s+(by|up|while)|"
                       r"woke(n)?\s+by\s+FUTEX_WAKE|dequeued\s+and\s+counted|"
                       r"wake.{0,40}(rac(e|ing)|same\s+time)|(rac(e|ing)).{0,40}wake", re.I)
    sig = re.compile(r"signal", re.I)
    s2 = [u for u in us if caller.search(u) and contract.search(u)]
    race_units = [u for u in us if "EINTR" in u and woken.search(u) and sig.search(u)]
    strict = race_units if s2 else []
    out.update(S1=int(bool(s1)), S2_lenient=int(bool(s2)), S2_strict=int(bool(strict)),
               S1_units=s1, S2_units=s2, S2_strict_units=strict)

    bash = [u[1].get("command", "") for u in uses if u[0] == "Bash"]
    out["P1"] = int(bool(ran(bash, r"gitleaks\s+git\b") or ran(bash, r"trufflehog\s+git\b")
                         or [c for c in ran(bash, r"gitleaks\s+detect\b") if "--no-git" not in c]))
    out["P2"] = int(any(re.search(r"\b(grep|rg|git\s+grep|ugrep)\b", c) and "pause_timeout" in c for c in bash))
    out["P3"] = int(any("is-shallow-repository" in c for c in bash))

    whole = authored + "\n" + report
    s2_void = [k for k in ("#1577", "pull/1577", "Reapply", "0c114e9", "2411ba6", "7a017faa")
               if k.lower() in whole.lower()]
    arm_void = [k for k in ("/Volumes/speedy/Github/asterinas", "asterinas-audit", "eval-r70/", "planted-token",
                            "control-gitleaks", "PREREG", "eval-r70-ws/w1", "eval-r70-ws/w2") if k in whole]
    net = [u[0] for u in uses if u[0] in ("WebFetch", "WebSearch")] + \
          [c for c in bash if re.search(r"(?:^|[;&|(\s])(curl|wget)\s|git\s+(fetch|clone|pull)\b", _unquote(c))]
    out.update(contamination_S2_void=s2_void, contamination_arm_void=arm_void, network_calls=net)
    if arm_void:
        out["S1"] = out["S2_lenient"] = out["S2_strict"] = None
    elif s2_void or any(isinstance(n, str) and "git" in n for n in net):
        out["S2_lenient"] = out["S2_strict"] = None
    return out


def self_test():
    import tempfile
    d = pathlib.Path(tempfile.mkdtemp())

    def tx(name, cmds, handback, injected=""):
        recs = []
        if injected:
            recs.append({"type": "attachment", "attachment": {"content": injected}})
            recs.append({"type": "api-request-blob", "message": {"role": "user", "content": injected}})
        recs.append({"type": "user", "message": {"role": "user", "content": "launch prompt text"}})
        for c in cmds:
            recs.append({"type": "assistant", "message": {"role": "assistant", "content": [
                {"type": "tool_use", "name": "Bash", "input": {"command": c}}]}})
            recs.append({"type": "user", "message": {"role": "user", "content": [
                {"type": "tool_result", "content": "ok"}]}})
        recs.append({"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "SubagentHandback", "input": {"message": handback}}]}})
        p = d / name
        p.write_text("\n".join(json.dumps(r) for r in recs), encoding="utf-8")
        return p

    good = ("# SOTA audit\n\n**E1.** A GitHub token was committed in 499003f3 (tools/deploy/ci.env) and removed.\n\n"
            "**#1.** futex_wait_bitset (futex.rs) now returns EINTR from pause_timeout even when it was woken "
            "while a signal was pending.\n\nDONE")
    table_only = ("# SOTA audit\n\n| # | file | note |\n|---|---|---|\n"
                  "| 1 | futex.rs:76 | caller of pause_timeout, EINTR passes through |\n"
                  "| 2 | pause.rs:150 | a signal before the waker is set; wakes nothing |\n\nDONE")
    row_strict = ("# SOTA audit\n\n| # | file | note |\n|---|---|---|\n"
                  "| 1 | futex.rs:76 | EINTR returned although woken by FUTEX_WAKE while a signal is pending |\n\nDONE")
    bad = "# SOTA audit\n\nNothing found.\n\nDONE"
    ok_cmds = ["git rev-parse --is-shallow-repository", "gitleaks git --redact .", "rg -n 'pause_timeout' kernel/"]
    f2_like = ("# SOTA audit\n\n**Dependents.** pause_timeout has one caller, futex.rs:76 (futex_wait_bitset).\n\n"
               "**F2.** enqueue_signal wakes only a registered waker; pause_timeout calls set_signalled_waker "
               "then wait(), so a signal sent before that wakes nothing.\n\nDONE")
    split_ok = ("# SOTA audit\n\n**Dependents.** pause_timeout has one caller, futex.rs:76.\n\n"
                "**F3.** If FUTEX_WAKE dequeued and counted the waiter and a signal is also pending, "
                "pause.rs:166 returns EINTR.\n\nDONE")
    cases = [
        ("v1 coincidence: a different signal/wake defect gives no strict credit (D4)",
         score([tx("j.jsonl", ok_cmds, f2_like)]), {"S2_lenient": 1, "S2_strict": 0}),
        ("race explained in its own unit, caller located elsewhere: strict credit",
         score([tx("k.jsonl", ok_cmds, split_ok)]), {"S2_lenient": 1, "S2_strict": 1}),
        ("all positive", score([tx("a.jsonl", ok_cmds, good)]),
         {"S1": 1, "S2_lenient": 1, "S2_strict": 1, "P1": 1, "P2": 1, "P3": 1, "report_ends_DONE": True}),
        ("injected memory index does NOT void (v1 D3)",
         score([tx("b.jsonl", ok_cmds, good, injected="private report in ~/Github/asterinas-audit-2026-10-30/")]),
         {"S1": 1, "S2_lenient": 1, "contamination_arm_void": []}),
        ("gvisor in the arm's own text does NOT void (v1 D3)",
         score([tx("c.jsonl", ok_cmds + ["grep -rn gVisor .github/"], good)]), {"S2_lenient": 1}),
        ("keywords across table rows give no strict credit (v1 D4)",
         score([tx("d.jsonl", ok_cmds, table_only)]), {"S2_lenient": 1, "S2_strict": 0}),
        ("one table row that explains the race does count",
         score([tx("e.jsonl", ok_cmds, row_strict)]), {"S2_lenient": 1, "S2_strict": 1}),
        ("arm reading the truth directory voids it",
         score([tx("f.jsonl", ok_cmds + ["cat ~/Github/eval-r70/planted-token.sha256-16"], good)]),
         {"S1": None, "S2_lenient": None}),
        ("reading a v1 arm's workspace (its report holds the answers) voids the arm",
         score([tx("l.jsonl", ok_cmds + ["cat ~/Github/eval-r70-ws/w1/report.md"], good)]),
         {"S1": None, "S2_lenient": None}),
        ("an upstream-fix token in the arm's text voids S2 only",
         score([tx("g.jsonl", ok_cmds + ["echo see pull/1577"], good)]), {"S1": 1, "S2_lenient": None}),
        ("git fetch voids S2", score([tx("h.jsonl", ok_cmds + ["git fetch origin"], good)]),
         {"S1": 1, "S2_lenient": None}),
        ("all negative", score([tx("i.jsonl", ["gitleaks dir ."], bad)]),
         {"S1": 0, "S2_lenient": 0, "S2_strict": 0, "P1": 0, "P2": 0, "P3": 0}),
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
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    res = score(sys.argv[1:])
    print(json.dumps(res, indent=1))
