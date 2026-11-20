#!/usr/bin/env python3
"""action-rules-hook.py — a PreToolUse hook on Bash that keys on the ACTION a command takes.

Two field reports (2026-11-18, ADOPTION-LOG; ROADMAP 98) found the same miss: a step taken
through Bash reached no owning rules file. A release signed commits with an OpenPGP card and
never opened `sota-cli-ux` rules/03 §9 (one `Bad PIN`, two timeouts), and a CI redesign edited
pipeline templates through `python3 - <<EOF` scripts with `sota-devsecops` invoked and its
rules/09, 13 and 16 never opened. The code-rules hook sees Edit/Write only, and a description
or a router row only helps when routing fires; this fires on the command itself.

Five classes, each acted on at most once per session (src_edit once per rules file and language):

  sign      a command that signs or unlocks with a person's key (`git commit -S`, `git tag -s`,
            a commit or annotated tag when `commit.gpgSign`/`tag.gpgSign` is set, `gpg --sign`,
            `ssh-keygen -Y sign`, `cosign sign --sk`, `ykman`, `fido2-token`, ...). REFUSED once,
            because each failed or timed-out attempt can spend one of the person's PIN tries and
            a note shown after the command would arrive too late: Claude Code places a
            PreToolUse `additionalContext` next to the tool RESULT (hooks reference, read
            2026-11-18). Issued again, the same command runs.
  registry  a push, copy or retag of an image (`docker push`, `crane tag`, `skopeo copy`, ...).
  ci_edit   a write to a CI definition or a container build file from the shell, including a
            script in a heredoc that opens one for writing, or a heredoc that writes a CI object
            (`kind: Workflow`, `WorkflowTemplate`, a Tekton `PipelineRun`).
  scan      an image or filesystem vulnerability scan (`trivy image`, `grype`).
  src_edit  a write to a source file from the shell (`cat > x.go <<EOF`, `tee`, `sed -i`, a heredoc
            script that opens a quoted source path for writing). The code-rules hook keys on
            Edit/Write, so a source file written through Bash reached no rules file: a field report
            (2026-11-20, ADOPTION-LOG) counted 126 Bash writes of Go files against 20 Edit/Write in
            one session, and a fail-open defect in one of the 126. The command text (heredoc body
            included) goes to the code-rules hook's own `respond()` as a Write event, so the same
            triggers, language note and once-per-session state apply as for an Edit.

The last four add context and never block.

The command is parsed into segments and argv, not grepped: a commit message, a grep pattern or
`git log -S` (a pickaxe search) is not a signing step. Replay over one operator's transcripts
(2026-11-18: 39,464 Bash calls, 94 sessions): `sign` fired on 13 calls in 2 sessions, all real,
including all 7 `git commit -S` calls of the incident; `ci_edit` caught all 11 edits of the
incident's pipeline templates and fires in 36 of 94 sessions, at most once each; `scan` in 5;
`registry` in none. Re-run it with `--replay` (default root ~/.claude/projects).
src_edit, replayed 2026-11-20 over 472 transcripts (43,405 Bash calls): it matches 4,070 calls in 77
sessions, but the note shown is the code-rules hook's, which skips tests and the scratchpad and names
each rules file once per session: 352 notes in 73 sessions, 2 to 6 in most, 18 at most. Of 30 sampled
notes, at least 21 named a file the command writes; 4 named a file a script only read (`importlib`,
`read_text`, a glob in a listing), and 5 named a scratchpad path first, their note coming from
another path in the same command. On the field report's own defect the note names the language
skill and four `sota-code-security` files, not `sota-golang` rules/01: that session had already
read the SKILL.md, so it is not shown to have prevented that one.

Off with SOTA_ACTION_RULES_HOOK=off. Any internal error lets the command run (exit 0, no output):
a hook must never break the shell. `--self-test` runs the labelled cases.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys

# subprocess, tempfile and hashlib are imported where they are used: together they cost about
# 37 ms of the hook's start-up, measured 2026-11-18, and most commands match no class at all.
LIB = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def rf(skill: str, name: str) -> str:
    return os.path.join(LIB, "skills", skill, "rules", name)


NOTES = {
    "sign": (
        "sota action-rules: this command signs or unlocks with a person's key, and each failed or "
        "timed-out attempt can spend one of their PIN tries. It was not run; this happens once per "
        "session, and the same command runs if it is issued again. What decides it first: whether "
        "the project asks for this signature at all (its policy, and `git config --get "
        "commit.gpgSign` / `tag.gpgSign`): a signature it does not require is a prompt the task "
        "does not need. The retry counter reads without spending an attempt (`gpg --card-status`, "
        "`fido2-token -I <device>`). The person hears every prompt in order (PIN, then touch) and "
        "how many signing steps the task has, before the first one, and a touch step starts after "
        "they say ready. Owning rules: %s §9; %s §2.7."
        % (rf("sota-cli-ux", "03-behavior-lifecycle.md"), rf("sota-devsecops", "02-provenance-signing.md"))
    ),
    "registry": (
        "sota action-rules: this command pushes, copies or retags an image. Owning rules: %s §3 "
        "(build to a candidate that is unique per build, promote the same digest after the last "
        "gate) and %s §8.3 (a tag is mutable, a consumer pins the digest)."
        % (rf("sota-devsecops", "09-gates-that-hold.md"), rf("sota-devsecops", "08-registry-security.md"))
    ),
    "ci_edit": (
        "sota action-rules: this command writes a CI pipeline definition or a container build file "
        "from the shell, which the code-rules hook (Edit/Write) does not see. Owning rules: %s "
        "(workflow hardening), %s §3 (gates and promotion), %s §16.2a (a cache outage must not fail "
        "the build), %s (Dockerfiles)."
        % (rf("sota-devsecops", "01-pipeline-security.md"), rf("sota-devsecops", "09-gates-that-hold.md"),
           rf("sota-devsecops", "16-fast-ci-without-blind-spots.md"), rf("sota-devsecops", "04-build-containers.md"))
    ),
    "scan": (
        "sota action-rules: this command runs a vulnerability scan. A scanner's fixed version for an "
        "OS package is the distribution's fixed build; whether the base image's package channel "
        "carries it, for each architecture, is a separate check before a rebuild is promised. "
        "Owning rules: %s §13.6." % rf("sota-devsecops", "13-vulnerability-remediation.md")
    ),
}

CLASSES = ("sign", "registry", "ci_edit", "scan", "src_edit")

# ---------------------------------------------------------------- parsing

HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1[^\n]*\n.*?\n[ \t]*\2[ \t]*(?=\n|$)", re.S)
ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
WRAPPERS = {"sudo", "env", "command", "exec", "time", "nice", "nohup", "xargs", "!"}


def segments(cmd: str) -> list[str]:
    """Split on ; && || | & newlines and subshell brackets outside quotes, heredoc bodies removed."""
    cmd = HEREDOC.sub("<<HEREDOC\n", cmd)
    out: list[str] = []
    buf: list[str] = []
    quote = None
    i = 0
    while i < len(cmd):
        c = cmd[i]
        if quote:
            buf.append(c)
            if c == quote:
                quote = None
            elif c == "\\" and quote == '"' and i + 1 < len(cmd):
                buf.append(cmd[i + 1])
                i += 1
        elif c in "'\"":
            quote = c
            buf.append(c)
        elif c == "\\" and i + 1 < len(cmd):
            buf.append(cmd[i:i + 2])
            i += 1
        elif c in ";|&\n(){}":
            out.append("".join(buf))
            buf = []
        else:
            buf.append(c)
        i += 1
    out.append("".join(buf))
    return [s.strip() for s in out if s.strip()]


def argv_of(seg: str) -> list[str]:
    try:
        words = shlex.split(seg, comments=True)
    except ValueError:
        return []
    while words and (ASSIGN.match(words[0]) or words[0] in WRAPPERS or words[0] == "timeout"):
        skip = 2 if words[0] == "timeout" and len(words) > 1 else 1
        words = words[skip:]
        while words and words[0].startswith("-") and len(words) > 1:  # a wrapper's own flags
            words = words[1:]
    if words:
        words[0] = words[0].rsplit("/", 1)[-1]
    return words


def git_sub(argv: list[str]) -> tuple[str, list[str], str | None]:
    """(subcommand, its args, the -C directory if any)."""
    i, cdir = 1, None
    while i < len(argv):
        a = argv[i]
        if a == "-C" and i + 1 < len(argv):
            cdir = argv[i + 1]
            i += 2
            continue
        if a in ("-c", "--git-dir", "--work-tree", "--namespace"):
            i += 2
            continue
        if a.startswith("-"):
            i += 1
            continue
        return a, argv[i + 1:], cdir
    return "", [], cdir


def git_config_true(key: str, cwd: str | None) -> bool:
    import subprocess
    try:
        r = subprocess.run(["git", "config", "--get", "--type=bool", key], cwd=cwd or None,
                           capture_output=True, text=True, timeout=2, check=False)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.stdout.strip() == "true"


def short_flags(args: list[str]) -> set[str]:
    out: set[str] = set()
    for a in args:
        if a.startswith("-") and not a.startswith("--") and len(a) > 1:
            out.update(a[1:])
    return out


def is_sign(argv: list[str], cwd: str | None, config=git_config_true) -> bool:
    if not argv:
        return False
    tool, args = argv[0], argv[1:]
    if set(args) & {"--help", "-h"}:
        return False
    if tool == "git":
        sub, rest, cdir = git_sub(argv)
        flags = [r for r in rest if r.startswith("-")]
        where = os.path.join(cwd or ".", os.path.expanduser(cdir)) if cdir else cwd
        if sub in ("commit", "merge", "rebase", "cherry-pick", "revert", "am", "pull"):
            if any(f.startswith("-S") or f.startswith("--gpg-sign") for f in flags):
                return True
            if "--no-gpg-sign" in flags or sub != "commit":
                return False
            return config("commit.gpgSign", where)
        if sub == "tag":
            if any(f in ("-s", "--sign", "-u") or f.startswith("--local-user") for f in flags):
                return True
            if "--no-sign" in flags or set(flags) & {"-d", "--delete", "-l", "--list", "-v", "--verify"}:
                return False
            annotated = any(f in ("-a", "--annotate", "-m", "-F") or f.startswith(("--message", "--file")) for f in flags)
            return annotated and config("tag.gpgSign", where)
        if sub == "push":
            return any(f.startswith("--signed") for f in flags)
        return False
    if tool in ("gpg", "gpg2"):
        longs = {a.split("=")[0] for a in args if a.startswith("--")}
        if longs & {"--sign", "--clearsign", "--clear-sign", "--detach-sign", "--card-edit", "--edit-card",
                    "--sign-key", "--quick-sign-key", "--lsign-key", "--change-pin"}:
            return True
        return bool(short_flags(args) & {"s", "b"})
    if tool == "ssh-keygen":
        return "-Y" in args and "sign" in args
    if tool == "cosign":
        return bool(args) and args[0] in ("sign", "sign-blob", "attest", "attest-blob") and (
            "--sk" in args or any("pkcs11:" in a for a in args))
    if tool == "ykman":
        return bool(args) and not set(args) & {"info", "list", "--version"}
    if tool in ("yubico-piv-tool", "pkcs11-tool"):
        return any(a in ("--login", "-l", "--verify-pin") for a in args) or (
            tool == "yubico-piv-tool" and any(a.startswith("-a") and a not in ("-astatus", "-aversion") for a in args))
    if tool == "fido2-token":
        return bool(args) and not set(args) & {"-I", "-L"}
    if tool == "age-plugin-yubikey":
        return bool(set(args) & {"--generate", "-g"})
    return False


def is_registry(argv: list[str]) -> bool:
    if not argv or set(argv) & {"--help", "-h", "help"}:
        return False
    tool, args = argv[0], argv[1:]
    sub = next((a for a in args if not a.startswith("-")), "")
    if tool in ("docker", "podman", "nerdctl", "buildah"):
        if sub == "push" or args[:2] in (["image", "push"], ["manifest", "push"]):
            return True
        return sub in ("build", "buildx") and ("--push" in args or any("type=registry" in a for a in args))
    if tool == "crane":
        return sub in ("push", "copy", "cp", "tag", "mutate", "append", "rebase", "delete")
    if tool == "skopeo":
        return sub in ("copy", "delete", "sync")
    if tool == "oras":
        return sub in ("push", "cp", "copy", "tag", "attach")
    if tool == "regctl":
        return args[:2] in (["image", "copy"], ["image", "mod"], ["image", "delete"]) or sub == "tag"
    if tool == "cosign":
        return sub == "copy"
    if tool in ("executor", "kaniko"):
        return any(a.startswith("--destination") for a in args)
    return False


CI_NAME = (r"\.github/workflows/[^/\s'\"]+\.ya?ml|\.gitlab-ci\.ya?ml|Jenkinsfile|\.circleci/config\.ya?ml"
           r"|azure-pipelines\.ya?ml|bitbucket-pipelines\.ya?ml|\.buildkite/[^\s'\"]+\.ya?ml|\.tekton/[^\s'\"]+\.ya?ml"
           r"|[^/\s'\"]*(?:workflow|pipeline)[^/\s'\"]*\.ya?ml|(?:Docker|Container)file(?:\.[\w.-]+)?")
CI_PATH = re.compile(r"(?:^|/)(?:%s)$" % CI_NAME)
# the CI path as a whole quoted string, the way a script names a file it opens, not a word in prose
CI_PATH_QUOTED = re.compile(r"(['\"])[^'\"\s]*?(?:%s)\1" % CI_NAME)
SCRIPT_WRITE = re.compile(r"open\([^)]*['\"][wa]\+?['\"]|\.write_text\(|\bwrite\(")
CI_KIND = re.compile(r"^\s*kind:\s*(?:Workflow|WorkflowTemplate|ClusterWorkflowTemplate|CronWorkflow"
                     r"|Pipeline|PipelineRun|TaskRun)\s*$", re.M)
WRITE_TO_FILE = re.compile(r"(?:cat|tee)\b[^\n|;&]*<<|>\s*['\"]?[^\s'\"&|;]+\.ya?ml")
REDIRECT = re.compile(r">>?\s*(['\"]?)([^\s'\"&|;]+)\1")


def ci_edit_in_text(cmd: str) -> bool:
    """A script (usually a heredoc body) that opens a CI file for writing, or writes a CI object."""
    if CI_PATH_QUOTED.search(cmd) and SCRIPT_WRITE.search(cmd):
        return True
    return bool(CI_KIND.search(cmd) and WRITE_TO_FILE.search(cmd))


def is_ci_edit(argv: list[str], seg: str) -> bool:
    if not argv:
        return False
    tool, args = argv[0], argv[1:]
    for m in REDIRECT.finditer(seg):
        if CI_PATH.search(m.group(2)):
            return True
    if not any(CI_PATH.search(a) for a in args):
        return False
    if tool == "sed":
        return any(a.startswith("-i") or a.startswith("--in-place") for a in args)
    if tool == "perl":
        return any(a.startswith("-") and not a.startswith("--") and "i" in a[1:] for a in args)
    if tool in ("tee", "truncate"):
        return True
    if tool in ("cp", "mv", "install", "ln"):
        return bool(args) and bool(CI_PATH.search(args[-1]))
    if tool == "kubectl":
        return bool(args) and args[0] in ("apply", "create", "replace")
    if tool == "argo":
        return bool(args) and (args[0] == "submit" or args[:2] in (
            ["template", "create"], ["template", "update"], ["cron", "create"]))
    return False


SRC_EXT = r"pyi?|go|rs|c|h|cc|cpp|cxx|hpp|java|kts?|cs|php|rb|swift|jsx?|mjs|cjs|tsx?|sh|bash"
SRC_PATH = re.compile(r"(?:^|/)[^/\s'\"]+\.(?:%s)$" % SRC_EXT)
SRC_PATH_QUOTED = re.compile(r"(['\"])([^'\"\s]+\.(?:%s))\1" % SRC_EXT)


ASSIGN_VALUE = re.compile(r"(?:^|[\s;&(])([A-Za-z_][A-Za-z0-9_]*)=['\"]?([^'\"\s;&|)]+)")
VAR_PREFIX = re.compile(r"^\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")


def src_paths(cmd: str) -> list[str]:
    """Source files this command writes: a redirect, tee, sed -i / perl -pi, cp/mv/install to one,
    or a script (usually a heredoc) that names a quoted source path and writes a file."""
    out: list[str] = []
    if SCRIPT_WRITE.search(cmd):
        out += [m.group(2) for m in SRC_PATH_QUOTED.finditer(cmd)]
    for seg in segments(cmd):
        for m in REDIRECT.finditer(seg):
            if SRC_PATH.search(m.group(2)):
                out.append(m.group(2))
        argv = argv_of(seg)
        if not argv:
            continue
        tool, args = argv[0], argv[1:]
        files = [a for a in args if SRC_PATH.search(a)]
        if not files:
            continue
        if tool == "sed" and any(a.startswith("-i") or a.startswith("--in-place") for a in args):
            out += files
        elif tool == "perl" and any(a.startswith("-") and not a.startswith("--") and "i" in a[1:] for a in args):
            out += files
        elif tool == "tee":
            out += files
        elif tool in ("cp", "mv", "install") and SRC_PATH.search(args[-1]):
            out.append(args[-1])
    # a path named through a variable assigned in the same command (`S=/…/scratchpad; cat > $S/x.py`)
    # resolves to its value, so the code-rules hook's scratchpad and test exemptions can see it
    env = dict(ASSIGN_VALUE.findall(cmd))
    out = [VAR_PREFIX.sub(lambda m: env.get(m.group(1) or m.group(2), m.group(0)), x) for x in out]
    seen: set[str] = set()
    return [x for x in out if not (x in seen or seen.add(x))]


def code_rules_note(paths: list[str], cmd: str, event: dict) -> str:
    """The code-rules hook's own note for these paths, as if each had been written with Write."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "sota_code_rules_hook", os.path.join(os.path.dirname(os.path.realpath(__file__)), "code-rules-hook.py"))
    if spec is None or spec.loader is None:
        return ""
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    notes = []
    for path in paths:
        out = mod.respond({"tool_name": "Write", "tool_input": {"file_path": path, "content": cmd},
                           "session_id": event.get("session_id"), "transcript_path": event.get("transcript_path")})
        if out:
            notes.append(json.loads(out)["hookSpecificOutput"]["additionalContext"])
    if not notes:
        return ""
    return ("sota action-rules: this command writes source from the shell, which the code-rules hook "
            "(Edit/Write) does not see; its note follows.\n" + "\n\n".join(notes))


def is_scan(argv: list[str]) -> bool:
    if not argv or set(argv) & {"--help", "-h", "--version"}:
        return False
    tool, args = argv[0], argv[1:]
    if tool == "trivy":
        return bool(args) and args[0] in ("image", "i", "fs", "rootfs", "sbom")
    return tool == "grype" and bool(args)


def classify(cmd: str, cwd: str | None = None, config=git_config_true) -> set[str]:
    found: set[str] = set()
    if ci_edit_in_text(cmd):
        found.add("ci_edit")
    if src_paths(cmd):
        found.add("src_edit")
    here = cwd
    for seg in segments(cmd):
        argv = argv_of(seg)
        if argv[:1] == ["cd"] and len(argv) > 1:
            here = os.path.join(here or ".", os.path.expanduser(argv[1]))
            continue
        if is_sign(argv, here, config):
            found.add("sign")
        if is_registry(argv):
            found.add("registry")
        if is_ci_edit(argv, seg):
            found.add("ci_edit")
        if is_scan(argv):
            found.add("scan")
    return found

# ---------------------------------------------------------------- once per session


def state_dir(session_id: str) -> str:
    import tempfile
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", session_id or "nosession")[:80]
    return os.path.join(tempfile.gettempdir(), "sota-action-rules-hook", safe)


def claim(d: str, cls: str) -> bool:
    """True for exactly one caller per (session, class), even when two copies of the hook race."""
    import hashlib
    os.makedirs(d, mode=0o700, exist_ok=True)
    try:
        fd = os.open(os.path.join(d, hashlib.sha256(cls.encode()).hexdigest()[:32]),
                     os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return False
    os.close(fd)
    return True


def decide(event: dict, sd: str | None = None, config=git_config_true) -> dict | None:
    if event.get("tool_name") != "Bash":
        return None
    cmd = (event.get("tool_input") or {}).get("command")
    if not isinstance(cmd, str) or not cmd.strip():
        return None
    classes = classify(cmd, event.get("cwd"), config)
    if not classes:
        return None
    if sd is None:
        sd = state_dir(str(event.get("session_id") or ""))
    if "sign" in classes and claim(sd, "sign"):
        return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                       "permissionDecisionReason": NOTES["sign"]}}
    notes = [NOTES[c] for c in ("registry", "ci_edit", "scan") if c in classes and claim(sd, c)]
    if "src_edit" in classes:
        cr = code_rules_note(src_paths(cmd), cmd, event)  # code-rules' own state: once per rules file
        if cr:
            notes.append(cr)
    if not notes:
        return None
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": "\n".join(notes)}}


def main() -> int:
    if os.environ.get("SOTA_ACTION_RULES_HOOK", "").lower() in ("off", "0", "false", "no"):
        return 0
    try:
        event = json.load(sys.stdin)
        out = decide(event)
    except Exception:  # noqa: BLE001 — a hook must never break the shell it guards
        return 0
    if out:
        sys.stdout.write(json.dumps(out))
    return 0

# ---------------------------------------------------------------- replay and self-test


def replay(root: str) -> int:
    """Count, per class, the Bash calls and sessions this hook would act on in local transcripts."""
    calls = {c: 0 for c in CLASSES}
    sessions: dict[str, set[str]] = {c: set() for c in CLASSES}
    total, files = 0, 0
    for dp, _dn, fn in os.walk(os.path.expanduser(root), followlinks=True):
        for f in fn:
            if not f.endswith(".jsonl"):
                continue
            files += 1
            seen: set[str] = set()
            with open(os.path.join(dp, f), encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    try:
                        o = json.loads(line)
                    except ValueError:
                        continue
                    content = (o.get("message") or {}).get("content")
                    if not isinstance(content, list):
                        continue
                    for b in content:
                        if not (isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Bash"):
                            continue
                        if b.get("id") in seen:
                            continue
                        seen.add(b.get("id"))
                        cmd = (b.get("input") or {}).get("command")
                        if not isinstance(cmd, str):
                            continue
                        total += 1
                        for c in classify(cmd, None, lambda *_: False):
                            calls[c] += 1
                            sessions[c].add(str(o.get("sessionId")))
    print("transcripts %d, Bash calls %d (git signing config not read: explicit flags only)" % (files, total))
    for c in CLASSES:
        print("  %-9s %5d calls in %3d sessions" % (c, calls[c], len(sessions[c])))
    return 0 if files else 1


CASES = [
    # (command, config true for, expected classes)
    ('git commit -q -S -m "docs: release"', (), {"sign"}),
    ('git add a && git commit -S -F - <<\'EOF\'\nmsg\nEOF', (), {"sign"}),
    ("git -C repo commit --gpg-sign=ABCD -m x", (), {"sign"}),
    ("git rebase --force-rebase --gpg-sign main", (), {"sign"}),
    ("git tag -s v1.0.0 -m v1.0.0", (), {"sign"}),
    ("git commit -m x", ("commit.gpgSign",), {"sign"}),
    ("git tag -a v1 -m v1", ("tag.gpgSign",), {"sign"}),
    ("echo test | gpg --local-user ABCD --clearsign", (), {"sign"}),
    ("gpg -bsa file.tar.gz", (), {"sign"}),
    ("ssh-keygen -Y sign -f key -n file x", (), {"sign"}),
    ("ykman piv keys generate 9c pub.pem", (), {"sign"}),
    ("git log -S needle --oneline", ("commit.gpgSign",), set()),
    ("git commit -m 'mention git commit -S here'", (), set()),
    ("git commit --no-gpg-sign -m x", ("commit.gpgSign",), set()),
    ("git tag -l", ("tag.gpgSign",), set()),
    ("git tag v1", ("tag.gpgSign",), set()),
    ("grep -rn 'git commit -S' docs/", (), set()),
    ("cat > RELEASING.md <<'EOF'\nSign the release:\ngit tag -s v1.0.0\nEOF", (), set()),
    ("gpg --card-status", (), set()),
    ("gpg --verify sig.asc", (), set()),
    ("fido2-token -I /dev/hidraw0", (), set()),
    ("ykman info", (), set()),
    ("docker push registry.example/app:candidate-123", (), {"registry"}),
    ("crane tag registry.example/app@sha256:ab release", (), {"registry"}),
    ("skopeo copy --help | grep creds", (), set()),
    ("docker tag a b", (), set()),
    ("sed -i '' 's/x/y/' .github/workflows/ci.yml", (), {"ci_edit"}),
    ("cat > Dockerfile <<'EOF'\nFROM scratch\nEOF", (), {"ci_edit"}),
    ("python3 - <<'EOF'\np='kustomize/workflows/build/workflow-template.yaml'; s=open(p).read()\n"
     "open(p,'w').write(s.replace('a','b'))\nEOF", (), {"ci_edit"}),
    ("cat > /tmp/run.yaml <<'EOF'\napiVersion: argoproj.io/v1alpha1\nkind: Workflow\nEOF\n"
     "kubectl create -f /tmp/run.yaml", (), {"ci_edit"}),
    ("python3 - <<'EOF'\np='docs/notes.md'; s=open(p).read()\ns=s.replace('x','the Containerfile')\n"
     "open(p,'w').write(s)\nEOF", (), set()),
    ("grep -n runs-on .github/workflows/ci.yml", (), set()),
    ("actionlint .github/workflows/ci.yml", (), set()),
    ("trivy image --scanners vuln app:1", (), {"scan"}),
    ("trivy --version", (), set()),
    # src_edit (2026-11-20 field report): a source file written through Bash
    ("cat > internal/intel/fetch.go <<'EOF'\npackage intel\nEOF", (), {"src_edit"}),
    ("cat >> cmd/api/main.go <<'EOF'\nfunc x() {}\nEOF", (), {"src_edit"}),
    ("printf 'x' | tee src/app.ts", (), {"src_edit"}),
    ("sed -i '' 's/a/b/' pkg/store/user.go", (), {"src_edit"}),
    ("python3 - <<'EOF'\np='internal/worker/tasks/report_sources.go'\ns=open(p).read()\nopen(p,'w').write(s)\nEOF", (), {"src_edit"}),
    ("grep -rn 'io.ReadAll' --include='*.go' .", (), set()),
    ("cat internal/intel/fetch.go | head", (), set()),
    ("git commit -m 'fix internal/intel/fetch.go'", (), set()),
    ("go test ./internal/... > test-output.txt", (), set()),
]


def self_test() -> int:
    import tempfile
    from pathlib import Path
    fails = 0
    for cmd, cfg, want in CASES:
        got = classify(cmd, None, lambda k, _w, cfg=cfg: k in cfg)
        if got != want:
            fails += 1
            print("FAIL classify(%r) = %s, want %s" % (cmd[:70], sorted(got), sorted(want)))
    with tempfile.TemporaryDirectory() as d:
        sd = os.path.join(d, "s")
        ev = {"tool_name": "Bash", "tool_input": {"command": "git commit -S -m x"}, "session_id": "t"}
        first, second = decide(ev, sd), decide(ev, sd)
        if not (first and first["hookSpecificOutput"].get("permissionDecision") == "deny"):
            fails += 1
            print("FAIL the first signing command of a session was not refused")
        if second is not None:
            fails += 1
            print("FAIL a repeated signing command was refused again")
        ev2 = {"tool_name": "Bash", "tool_input": {"command": "docker push r/a:1 && trivy image r/a:1"}, "session_id": "t"}
        out = decide(ev2, sd)
        ctx = (out or {}).get("hookSpecificOutput", {}).get("additionalContext", "")
        if "permissionDecision" in (out or {}).get("hookSpecificOutput", {}) or "§3" not in ctx or "§13.6" not in ctx:
            fails += 1
            print("FAIL a registry + scan command did not get both notes as context, without a decision")
        if decide(ev2, sd) is not None:
            fails += 1
            print("FAIL a context note was repeated in the same session")
        if decide({"tool_name": "Edit", "tool_input": {"command": "git commit -S"}}, sd) is not None:
            fails += 1
            print("FAIL a non-Bash tool was acted on")
    with tempfile.TemporaryDirectory() as d:
        import uuid
        ev3 = {"tool_name": "Bash", "session_id": "t-" + uuid.uuid4().hex, "transcript_path": "",
               "tool_input": {"command": "cat > internal/intel/fetch.go <<'EOF'\npackage intel\n"
                              "func get(c *http.Client, u string) { resp, _ := c.Get(u); "
                              "body, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20)); _ = body }\nEOF"}}
        ctx = ((decide(ev3, os.path.join(d, "s")) or {}).get("hookSpecificOutput") or {}).get("additionalContext", "")
        if "code-rules hook" not in ctx or "rules/" not in ctx:
            fails += 1
            print("FAIL a Go file written by a heredoc did not get the code-rules note: %r" % ctx[:160])
    # the extension list must match the code-rules hook's language map, or a language falls through
    import importlib.util
    spec = importlib.util.spec_from_file_location("crh", os.path.join(os.path.dirname(os.path.realpath(__file__)), "code-rules-hook.py"))
    crh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(crh)
    exts = {e for e in crh.LANG_SKILL}
    covered = {e for e in exts if SRC_PATH.search("a." + e)}
    if covered != exts:
        fails += 1
        print("FAIL src_edit misses code-rules languages: %s" % sorted(exts - covered))
    for cls, text in NOTES.items():
        for path in re.findall(r"(/\S+?\.md)", text):
            if not Path(path).is_file():
                fails += 1
                print("FAIL the %s note names a missing file: %s" % (cls, path))
    print("self-test: %s (%d classify cases)" % ("ok" if not fails else "FAILED %d" % fails, len(CASES)))
    return 1 if fails else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv[1:]:
        sys.exit(self_test())
    if "--replay" in sys.argv[1:]:
        rest = [a for a in sys.argv[1:] if a != "--replay"]
        sys.exit(replay(rest[0] if rest else "~/.claude/projects"))
    sys.exit(main())
