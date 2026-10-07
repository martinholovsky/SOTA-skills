#!/usr/bin/env python3
"""test-mcp-server.py — drive scripts/sota-mcp-server.py over real stdio and check every answer.

Each case sends JSON-RPC lines to a fresh server process and asserts on the parsed replies.
The hostile cases matter most: path traversal in every name-bearing argument, unknown names,
a malformed line, an oversized line and a notification (which must get NO reply). A case
that expects an error also asserts the error is the RIGHT one, so a server that rejects
everything cannot pass. Prints a denominator; exits 1 on any failure.
"""
import json
import subprocess
import sys
from pathlib import Path

SERVER = Path(__file__).resolve().parent / "sota-mcp-server.py"
INIT = {"jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                   "clientInfo": {"name": "test", "version": "0"}}}


def run(lines):
    """Send raw lines (dicts are JSON-encoded), return the list of parsed reply objects."""
    data = "".join((json.dumps(x) if isinstance(x, dict) else x) + "\n" for x in lines)
    p = subprocess.run([sys.executable, str(SERVER)], input=data, capture_output=True,
                       text=True, timeout=30)
    if p.returncode != 0:
        raise AssertionError("server exited %d: %s" % (p.returncode, p.stderr[-400:]))
    return [json.loads(l) for l in p.stdout.splitlines() if l.strip()]


def call(i, name, args):
    return {"jsonrpc": "2.0", "id": i, "method": "tools/call",
            "params": {"name": name, "arguments": args}}


passed, failed = 0, []


def check(label, cond, detail=""):
    global passed
    if cond:
        passed += 1
    else:
        failed.append("%s %s" % (label, detail))


# 1. lifecycle and version negotiation
r = run([INIT, {"jsonrpc": "2.0", "method": "notifications/initialized"},
         {"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 0}},
         {"jsonrpc": "2.0", "id": 1, "method": "ping"}])
check("initialize replies", len(r) == 2, "got %d replies (notifications must get none)" % len(r))
check("echoes a supported version", r[0]["result"]["protocolVersion"] == "2025-06-18")
check("declares tools/resources/prompts", set(r[0]["result"]["capabilities"]) == {"tools", "resources", "prompts"})
check("ping answers {}", r[1].get("result") == {})
r = run([{**INIT, "params": {**INIT["params"], "protocolVersion": "1999-01-01"}}])
check("unknown version -> newest supported", r[0]["result"]["protocolVersion"] == "2025-11-25")

# 1b. the MODERN era (2026-07-28): discover, per-request _meta, no handshake, version errors
def modern(i, method, params=None):
    p = dict(params or {})
    p["_meta"] = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
                  "io.modelcontextprotocol/clientCapabilities": {}}
    return {"jsonrpc": "2.0", "id": i, "method": method, "params": p}


bad = modern(4, "tools/list")
bad["params"]["_meta"]["io.modelcontextprotocol/protocolVersion"] = "1900-01-01"
r = run([modern(1, "server/discover"), modern(2, "tools/list"),
         modern(3, "tools/call", {"name": "get_skill", "arguments": {"name": "sota"}}), bad])
d = r[0]["result"]
check("discover lists modern + legacy versions",
      d["supportedVersions"][0] == "2026-07-28" and "2025-11-25" in d["supportedVersions"])
check("discover is a complete, cacheable result",
      d.get("resultType") == "complete" and d.get("ttlMs") == 0 and d.get("cacheScope") in ("public", "private"))
check("modern tools/list without initialize",
      len(r[1]["result"]["tools"]) == 3 and r[1]["result"].get("ttlMs") == 0
      and r[1]["result"].get("cacheScope") in ("public", "private"))
check("modern tools/call is complete and not cacheable",
      "# SOTA Engineering Skills" in r[2]["result"]["content"][0]["text"]
      and r[2]["result"].get("resultType") == "complete" and "ttlMs" not in r[2]["result"])
e = r[3].get("error", {})
check("unsupported modern version -> -32022 with supported list", e.get("code") == -32022
      and "2026-07-28" in e.get("data", {}).get("supported", [])
      and e.get("data", {}).get("requested") == "1900-01-01", str(e))
r = run([INIT, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}])
check("legacy results carry no modern-only fields",
      "resultType" not in r[1]["result"] and "ttlMs" not in r[1]["result"])

# 2. tools: the happy path
r = run([INIT, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
         call(2, "list_skills", {}), call(3, "get_skill", {"name": "sota"}),
         call(4, "get_rules_file", {"skill": "sota-swift", "file": "05"}),
         call(5, "get_rules_file", {"skill": "sota-swift", "file": "05-security.md"})])
names = {t["name"] for t in r[1]["result"]["tools"]}
check("three tools", names == {"list_skills", "get_skill", "get_rules_file"}, str(names))
lst = r[2]["result"]["content"][0]["text"]
check("list_skills names the router and a language skill", "sota —" in lst and "sota-swift —" in lst)
check("get_skill returns the router", "# SOTA Engineering Skills" in r[3]["result"]["content"][0]["text"])
check("rules by number", r[4]["result"]["content"][0]["text"].startswith("# 05"))
check("rules by full name", r[5]["result"]["content"][0]["text"] == r[4]["result"]["content"][0]["text"])

# 3. tools: hostile and wrong input — each must be a tool error, and the right one
hostile = [("get_skill", {"name": "../../etc/passwd"}), ("get_skill", {"name": "/etc/passwd"}),
           ("get_skill", {"name": "sota-nope"}), ("get_skill", {"name": 7}),
           ("get_rules_file", {"skill": "sota", "file": "../../../etc/passwd"}),
           ("get_rules_file", {"skill": "sota", "file": "01/../../SKILL.md"}),
           ("get_rules_file", {"skill": "sota", "file": "99"}),
           ("get_rules_file", {"skill": "../sota", "file": "01"}),
           ("no_such_tool", {})]
r = run([INIT] + [call(i + 1, n, a) for i, (n, a) in enumerate(hostile)])
for (n, a), rep in zip(hostile, r[1:]):
    res = rep.get("result", {})
    txt = res.get("content", [{}])[0].get("text", "")
    check("rejects %s %s" % (n, a), res.get("isError") is True and "root:" not in txt, txt[:80])

# 4. resources
r = run([INIT, {"jsonrpc": "2.0", "id": 1, "method": "resources/list"},
         {"jsonrpc": "2.0", "id": 2, "method": "resources/read",
          "params": {"uri": "sota://skills/sota-golang/rules/05-security.md"}},
         {"jsonrpc": "2.0", "id": 3, "method": "resources/read",
          "params": {"uri": "sota://skills/sota/../../etc/passwd"}},
         {"jsonrpc": "2.0", "id": 4, "method": "resources/read", "params": {"uri": "file:///etc/passwd"}},
         {"jsonrpc": "2.0", "id": 5, "method": "resources/read", "params": {"uri": 123}},
         {"jsonrpc": "2.0", "id": 6, "method": "ping"}])
uris = [x["uri"] for x in r[1]["result"]["resources"]]
check("resources cover every rules file", len(uris) > 300 and all(u.startswith("sota://skills/") for u in uris), str(len(uris)))
check("resource read", "# 05" in r[2]["result"]["contents"][0]["text"])
check("traversal uri rejected", r[3].get("error", {}).get("code") == -32002)
check("file:// uri rejected", r[4].get("error", {}).get("code") == -32002)
check("non-string uri is invalid params", r[5].get("error", {}).get("code") == -32602, str(r[5]))
check("server alive after a non-string uri", r[6].get("result") == {})

# 5. prompts
r = run([INIT, {"jsonrpc": "2.0", "id": 1, "method": "prompts/list"},
         {"jsonrpc": "2.0", "id": 2, "method": "prompts/get",
          "params": {"name": "sota-audit", "arguments": {"arguments": "STEER-TOKEN"}}},
         {"jsonrpc": "2.0", "id": 3, "method": "prompts/get", "params": {"name": "../sota-audit"}}])
pnames = {p["name"] for p in r[1]["result"]["prompts"]}
check("five command prompts", pnames == {"sota-audit", "sota-close", "sota-deep-audit", "sota-report", "sota-resume"}, str(pnames))
body = r[2]["result"]["messages"][0]["content"]["text"]
check("prompt body substitutes $ARGUMENTS", "STEER-TOKEN" in body and "$ARGUMENTS" not in body and not body.startswith("---"))
check("unknown prompt rejected", r[3].get("error", {}).get("code") == -32602)

# 6. framing robustness
r = run([INIT, "{not json", "x" * (1 << 20 + 1), {"jsonrpc": "2.0", "id": 9, "method": "bogus/method"},
         {"jsonrpc": "1.0", "id": 10, "method": "ping"}, {"jsonrpc": "2.0", "id": 11, "method": "ping"}])
codes = [x.get("error", {}).get("code") for x in r[1:]]
check("parse error, oversize, unknown method, bad jsonrpc", codes[:4] == [-32700, -32600, -32601, -32600], str(codes))
check("server still answers after bad input", r[-1].get("result") == {})

total = passed + len(failed)
print("test-mcp-server: %d/%d checks passed" % (passed, total))
for f in failed:
    print("  FAIL:", f)
sys.exit(1 if failed else 0)
