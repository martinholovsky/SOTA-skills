#!/usr/bin/env python3
"""sota-mcp-server.py — serve the SOTA skills library over MCP (stdio), read-only.

WHY. Every agent that loads Agent Skills (SKILL.md folders) reaches this library without this
file. It exists for the hosts that do not: an agent with MCP but no skills loader can call
`list_skills`, read the descriptions, and fetch the skill and rules files it chooses.

WHAT IT DOES NOT DO, on purpose (operator decision 2026-10-07, ADOPTION-LOG):
  - It does not route. `list_skills` returns the catalogue; the host's MODEL picks. Routing on
    meaning measured 0.88-0.975 recall across four models; a keyword router here would replace
    that with something weaker (a PowerShell task routed correctly with no description naming
    PowerShell, 2026-09-14).
  - It writes nothing, executes nothing and opens no network connection. Every servable file is
    enumerated at startup from skills/ and commands/ into an index, and every request is a
    dictionary lookup by name — no path is ever built from request input, so traversal has no
    surface.

PROTOCOL. JSON-RPC 2.0, one message per line on stdin/stdout (the MCP stdio transport); logs go
to stderr only. Dual-era: modern (2026-07-28 — server/discover, per-request _meta, no
handshake) and legacy (initialize, 2024-11-05 .. 2025-11-25). Implemented: server/discover,
initialize, ping, tools/list, tools/call, resources/list, resources/read, prompts/list,
prompts/get. Standard library only — no dependency to pin.

Usage:   python3 scripts/sota-mcp-server.py            (an MCP host starts it)
         python3 scripts/sota-mcp-server.py --check    (print what it serves, exit)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER_NAME = "sota-skills"
# DUAL-ERA (spec 2026-07-28, basic/versioning): a MODERN client sends no initialize; every
# request carries its version in params._meta and is served statelessly; servers MUST answer
# server/discover and reject an unsupported version with error -32022. A LEGACY client opens
# with initialize; a version not listed there gets the newest legacy one (2025-11-25
# lifecycle: "SHOULD be the latest version supported by the server").
MODERN_VERSIONS = ["2026-07-28"]
SUPPORTED_VERSIONS = ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]  # legacy, newest first
META_VERSION = "io.modelcontextprotocol/protocolVersion"
CACHEABLE = {"server/discover", "tools/list", "resources/list", "resources/read", "prompts/list"}
MAX_LINE = 1 << 20          # 1 MiB per request line: no legitimate request comes near it
MAX_FILE = 512 * 1024       # skill files are <= 500 lines; anything larger is not ours

NAME_RE = re.compile(r"^sota(-[a-z0-9]+)*$")
RULES_RE = re.compile(r"^(\d{2})(-[a-z0-9-]+)?(\.md)?$")


def log(msg):
    print("[sota-mcp] %s" % msg, file=sys.stderr, flush=True)


def version():
    try:
        return (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"


def frontmatter(text):
    """(fields, body). Handles `description: >-` folded blocks as well as one-line values."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    head, body = text[4:end], text[end + 4:].lstrip("\n")
    fields, key = {}, None
    for line in head.split("\n"):
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key = m.group(1)
            val = m.group(2)
            fields[key] = "" if val in (">-", ">", "|", "|-") else val
        elif key and line.startswith(" "):
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields, body


def build_index():
    skills, prompts = {}, {}
    for d in sorted((ROOT / "skills").iterdir()):
        sk = d / "SKILL.md"
        if not (d.is_dir() and NAME_RE.match(d.name) and sk.is_file()):
            continue
        fields, _ = frontmatter(sk.read_text(encoding="utf-8"))
        rules = {}
        rd = d / "rules"
        if rd.is_dir():
            for f in sorted(rd.glob("*.md")):
                m = RULES_RE.match(f.name)
                if m and f.is_file():
                    rules[f.name] = f
        skills[d.name] = {"path": sk, "description": fields.get("description", ""), "rules": rules}
    cd = ROOT / "commands"
    if cd.is_dir():
        for f in sorted(cd.glob("*.md")):
            if NAME_RE.match(f.stem):
                fields, _ = frontmatter(f.read_text(encoding="utf-8"))
                prompts[f.stem] = {"path": f, "description": fields.get("description", "")}
    if "sota" not in skills:
        raise SystemExit("no skills/sota/SKILL.md under %s — not a SOTA-skills checkout" % ROOT)
    return skills, prompts


def read(path):
    if path.stat().st_size > MAX_FILE:
        raise ValueError("file exceeds the size cap")
    return path.read_text(encoding="utf-8")


class ToolError(Exception):
    pass


INSTRUCTIONS = ("Engineering skills for building and auditing software. Call list_skills, "
                "choose by description, then get_skill and get_rules_file. Read-only.")


def resolve_rules(skill, name):
    """`07`, `07-performance` or `07-performance.md` → the indexed file. Lookup only."""
    m = RULES_RE.match(name or "")
    if not m:
        raise ToolError("file must look like '07' or '07-name.md'")
    rules = skill["rules"]
    exact = name if name.endswith(".md") else name + ".md"
    if exact in rules:
        return rules[exact]
    hits = [f for n, f in rules.items() if n.startswith(m.group(1) + "-")]
    if len(hits) == 1:
        return hits[0]
    raise ToolError("no such rules file; available: %s" % ", ".join(sorted(rules)))


TOOLS = [
    {"name": "list_skills",
     "description": "List every SOTA skill with its description. Start here: read the "
                    "descriptions, pick the skills that match the task (always consider "
                    "'sota', the router), then call get_skill for each.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "get_skill",
     "description": "Return a skill's SKILL.md: its workflow, top-10 rules and an index of "
                    "its rules files with when to read each.",
     "inputSchema": {"type": "object", "required": ["name"], "additionalProperties": False,
                     "properties": {"name": {"type": "string", "description": "e.g. sota-golang"}}}},
    {"name": "get_rules_file",
     "description": "Return one rules file of a skill, chosen from that skill's rules index.",
     "inputSchema": {"type": "object", "required": ["skill", "file"], "additionalProperties": False,
                     "properties": {"skill": {"type": "string", "description": "e.g. sota-golang"},
                                    "file": {"type": "string",
                                             "description": "e.g. 05, 05-security or 05-security.md"}}}},
]


class Server:
    def __init__(self):
        self.skills, self.prompts = build_index()

    # --- tools -------------------------------------------------------------------------
    def skill(self, name):
        if not isinstance(name, str) or name not in self.skills:
            raise ToolError("unknown skill %r; call list_skills" % (name,))
        return self.skills[name]

    def call_tool(self, name, args):
        if not isinstance(args, dict):
            raise ToolError("arguments must be an object")
        if name == "list_skills":
            lines = ["%s — %s" % (n, s["description"]) for n, s in self.skills.items()]
            return ("%d skills. Pick by description; the router 'sota' explains how they "
                    "combine.\n\n%s" % (len(lines), "\n\n".join(lines)))
        if name == "get_skill":
            return read(self.skill(args.get("name"))["path"])
        if name == "get_rules_file":
            return read(resolve_rules(self.skill(args.get("skill")), args.get("file")))
        raise ToolError("unknown tool %r" % (name,))

    # --- resources ---------------------------------------------------------------------
    def resources(self):
        out = []
        for n, s in self.skills.items():
            out.append({"uri": "sota://skills/%s/SKILL.md" % n, "name": "%s/SKILL.md" % n,
                        "description": s["description"][:300], "mimeType": "text/markdown"})
            for f in s["rules"]:
                out.append({"uri": "sota://skills/%s/rules/%s" % (n, f), "name": "%s/rules/%s" % (n, f),
                            "mimeType": "text/markdown"})
        return out

    def read_resource(self, uri):
        m = re.match(r"^sota://skills/([a-z0-9-]+)/(SKILL\.md|rules/([0-9a-z-]+\.md))$", uri or "")
        if not m or m.group(1) not in self.skills:
            raise ToolError("unknown resource %r" % (uri,))
        s = self.skills[m.group(1)]
        path = s["path"] if m.group(3) is None else s["rules"].get(m.group(3))
        if path is None:
            raise ToolError("unknown resource %r" % (uri,))
        return read(path)

    # --- prompts -----------------------------------------------------------------------
    def get_prompt(self, name, args):
        if name not in self.prompts:
            raise ToolError("unknown prompt %r" % (name,))
        _, body = frontmatter(read(self.prompts[name]["path"]))
        steer = ""
        if isinstance(args, dict) and isinstance(args.get("arguments"), str):
            steer = args["arguments"]
        return body.replace("$ARGUMENTS", steer)

    # --- dispatch ----------------------------------------------------------------------
    def handle(self, msg):
        method, params = msg.get("method"), msg.get("params") or {}
        if not isinstance(params, dict):
            raise RpcError(-32602, "params must be an object")
        meta = params.get("_meta") if isinstance(params.get("_meta"), dict) else {}
        if META_VERSION in meta:  # a modern request: served statelessly, per its own version
            asked = meta[META_VERSION]
            if asked not in MODERN_VERSIONS:
                raise RpcError(-32022, "Unsupported protocol version",
                               {"supported": MODERN_VERSIONS + SUPPORTED_VERSIONS, "requested": asked})
            result = self.dispatch(method, params)
            if isinstance(result, dict):
                result = dict(result, resultType="complete")
                if method in CACHEABLE:
                    # CacheableResult REQUIRES both fields (schema 2026-07-28). The library is
                    # the same for every caller, so the scope is public. Found missing by a
                    # real client (Claude Code rejected every list result), not by the tests.
                    result.setdefault("ttlMs", 0)
                    result.setdefault("cacheScope", "public")
            return result
        if method == "server/discover":  # a dual-era client's probe may arrive without _meta
            return dict(self.dispatch(method, params), resultType="complete", ttlMs=0,
                        cacheScope="public")
        return self.dispatch(method, params)

    def dispatch(self, method, params):
        if method == "server/discover":
            return {"supportedVersions": MODERN_VERSIONS + SUPPORTED_VERSIONS,
                    "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                    "instructions": INSTRUCTIONS,
                    "_meta": {"io.modelcontextprotocol/serverInfo":
                              {"name": SERVER_NAME, "version": version()}}}
        if method == "initialize":
            asked = params.get("protocolVersion")
            ver = asked if asked in SUPPORTED_VERSIONS else SUPPORTED_VERSIONS[0]
            return {"protocolVersion": ver,
                    "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                    "serverInfo": {"name": SERVER_NAME, "version": version()},
                    "instructions": INSTRUCTIONS}
        if method == "ping":
            return {}
        if method.startswith("notifications/"):
            return None  # initialized, cancelled, ...: nothing to do and nothing to say
        if method == "tools/list":
            return {"tools": TOOLS}
        if method == "tools/call":
            try:
                text = self.call_tool(params.get("name"), params.get("arguments") or {})
                return {"content": [{"type": "text", "text": text}], "isError": False}
            except (ToolError, ValueError, OSError) as e:
                return {"content": [{"type": "text", "text": str(e)}], "isError": True}
        if method == "resources/list":
            return {"resources": self.resources()}
        if method == "resources/read":
            try:
                uri = params.get("uri")
                if not isinstance(uri, str):
                    raise RpcError(-32602, "uri must be a string")
                return {"contents": [{"uri": uri, "mimeType": "text/markdown",
                                      "text": self.read_resource(uri)}]}
            except (ToolError, ValueError, OSError) as e:
                raise RpcError(-32002, str(e))
        if method == "prompts/list":
            return {"prompts": [{"name": n, "description": p["description"],
                                 "arguments": [{"name": "arguments", "required": False,
                                                "description": "free-text steering, as typed "
                                                               "after the slash command"}]}
                                for n, p in self.prompts.items()]}
        if method == "prompts/get":
            try:
                text = self.get_prompt(params.get("name"), params.get("arguments"))
            except (ToolError, ValueError, OSError) as e:
                raise RpcError(-32602, str(e))
            return {"description": self.prompts[params["name"]]["description"],
                    "messages": [{"role": "user", "content": {"type": "text", "text": text}}]}
        raise RpcError(-32601, "method not found: %s" % (method,))


class RpcError(Exception):
    def __init__(self, code, message, data=None):
        super().__init__(message)
        self.code, self.message, self.data = code, message, data


def reply(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def serve(server, stream):
    for raw in stream:
        if len(raw) > MAX_LINE:
            reply({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "request too large"}})
            continue
        line = raw.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            reply({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}})
            continue
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0" or not isinstance(msg.get("method"), str):
            if isinstance(msg, dict) and "id" in msg and "method" not in msg:
                continue  # a response to something we never sent; ignore
            reply({"jsonrpc": "2.0", "id": msg.get("id") if isinstance(msg, dict) else None,
                   "error": {"code": -32600, "message": "invalid request"}})
            continue
        is_request = "id" in msg
        try:
            result = server.handle(msg)
            if is_request:
                reply({"jsonrpc": "2.0", "id": msg["id"], "result": result})
        except RpcError as e:
            if is_request:
                err = {"code": e.code, "message": e.message}
                if e.data is not None:
                    err["data"] = e.data
                reply({"jsonrpc": "2.0", "id": msg["id"], "error": err})
        # Defence in depth: every input the tests can construct is validated before it gets
        # here, so this branch has no known trigger (mutation-tested 2026-10-07: removing it
        # changes no test result). It stays so an unforeseen input degrades to an error reply
        # rather than killing the host's server process.
        except Exception as e:  # noqa: BLE001 — the server must answer, never crash the host
            log("internal error on %s: %r" % (msg.get("method"), e))
            if is_request:
                reply({"jsonrpc": "2.0", "id": msg["id"],
                       "error": {"code": -32603, "message": "internal error"}})


def main():
    server = Server()
    if "--check" in sys.argv[1:]:
        n_rules = sum(len(s["rules"]) for s in server.skills.values())
        print("sota-mcp-server %s: %d skills, %d rules files, %d prompts, protocols %s"
              % (version(), len(server.skills), n_rules, len(server.prompts),
                 ", ".join(MODERN_VERSIONS + SUPPORTED_VERSIONS)))
        return 0
    log("serving %d skills from %s" % (len(server.skills), ROOT))
    serve(server, sys.stdin)
    return 0


if __name__ == "__main__":
    sys.exit(main())
