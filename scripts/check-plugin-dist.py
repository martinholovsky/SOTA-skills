#!/usr/bin/env python3
"""check-plugin-dist.py — refuse a plugin tree the Claude plugin directory would block or hold.

  python3 scripts/check-plugin-dist.py DIST        # check a tree built by build-plugin-dist.sh
  python3 scripts/check-plugin-dist.py --selftest  # every check must catch its own known-bad

WHY. The directory tracks the generated plugin-dist branch (RELEASING.md §4b) and serves each
new commit on it to everyone who has the plugin. So the tree is checked before it is pushed,
against the rules the directory states (claude.com/docs/plugins/pre-submission-checklist,
fetched 2026-11-01) and the icon rule that `claude plugin validate` prints (Claude Code
2.1.316, ICON_MISSING): Python, not shell, because it parses JSON and PNG headers and runs
eighteen checks (sota-shell-scripting, "should this be shell at all?").

EVERY CHECK PRINTS ITS DENOMINATOR (`ok [files] 373 files (limit 512)`), so a check that
read nothing cannot pass silently: a check whose population is empty fails. Two are behavioural
POSITIVE CONTROLS, run in a scratch config dir: the routing hook must print the standing-rules
text on stdout with an empty stderr (an error message that merely mentions "sota" must not
pass), and every scripts/ path that the first-run notice and the update reminder tell a user
to run must exist in the tree.

--selftest builds a good tree from this checkout's own hook scripts, requires it to pass every
check, then applies one known-bad per check and requires that check, and only that check, to
fail: a catch for the wrong reason is a false pass.

Exit: 0 clean, 1 a check failed, 2 usage or an unreadable tree.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

MAX_ENTRIES = 9999          # "fewer than 10,000 files and folders" -> validation stops
MAX_FILES = 512             # more -> held for a reviewer
MAX_TEXT_BYTES = 256 * 1024  # a non-image, non-font file over 256 KiB -> held
MAX_ANY_BYTES = 5 * 1024 * 1024  # any file over 5 MiB -> validation stops
README_MIN_WORDS = 40       # outside code blocks
ICON_PATH = ".claude-plugin/icon.png"
ICON_MIN, ICON_MAX = 512, 2048
ICON_MAX_BYTES = 2 * 1000 * 1000  # "under 2 MB"; read as decimal, the stricter reading
ROUTING_PREFIX = "sota standing rules"
PNG_SIG = b"\x89PNG\r\n\x1a\n"
IMAGE_MAGIC = {  # "complete PNG, JPEG, GIF, and WebP images" are accepted binaries
    "png": (PNG_SIG,),
    "jpeg": (b"\xff\xd8\xff",),
    "gif": (b"GIF87a", b"GIF89a"),
}
FONT_EXT = {".woff", ".woff2", ".ttf", ".otf"}
JUNK = {".DS_Store", "Thumbs.db", "desktop.ini"}
PKG_CONFIG = {".npmrc", "bunfig.toml", "uv.toml", "package.json", "package-lock.json",
              "npm-shrinkwrap.json", "bun.lock", "bun.lockb", ".yarnrc", ".yarnrc.yml",
              "pip.conf", "poetry.toml"}
WIN_DEVICE = re.compile(r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?$", re.I)
HOOK_CMD = re.compile(r'^"\$\{CLAUDE_PLUGIN_ROOT\}/([A-Za-z0-9_./-]+)"$')
SCRIPT_REF = re.compile(r"\bscripts/[A-Za-z0-9_.-]+\.(?:sh|py)\b")
# A hook script's own path references: `"$here/x.sh"`, `${root}/scripts/install.sh`, and Python
# `ROOT / "skills" / "sota"`. Literal parts only; a reference built from a variable is not read.
# Python is read only for `ROOT / "skills" / …`, where the hook keeps its run-time data: the first
# draft read every `ROOT / "…"` and flagged a path inside code-rules-hook.py's own self-test.
SHELL_REF = re.compile(r"\$\{?(?:here|root|repo|REPO|SCRIPT_DIR|CLAUDE_PLUGIN_ROOT)\}?/([A-Za-z0-9_.-][A-Za-z0-9_./-]*)")
PY_REF = re.compile(r'\bROOT\s*/\s*"skills"(?:\s*/\s*"[A-Za-z0-9_.-]+")*')


class Report:
    def __init__(self, quiet: bool = False) -> None:
        self.failed: list[str] = []
        self.quiet = quiet

    def ok(self, name: str, msg: str) -> None:
        if not self.quiet:
            print(f"ok   [{name}] {msg}")

    def fail(self, name: str, msg: str) -> None:
        if name not in self.failed:
            self.failed.append(name)
        if not self.quiet:
            print(f"FAIL [{name}] {msg}")


def walk(root: Path) -> tuple[list[Path], list[Path], list[Path]]:
    """Files, directories and symlinks under root, never following a link."""
    files, dirs, links = [], [], []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for n in dirnames + filenames:
            p = Path(dirpath, n)
            if p.is_symlink():
                links.append(p)
            elif p.is_dir():
                dirs.append(p)
            else:
                files.append(p)
    return files, dirs, links


def image_kind(head: bytes) -> str | None:
    for kind, sigs in IMAGE_MAGIC.items():
        if any(head.startswith(s) for s in sigs):
            return kind
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


def is_text(data: bytes) -> bool:
    if b"\x00" in data:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def is_emoji(ch: str) -> bool:
    cp = ord(ch)
    return cp >= 0x1F000 or 0x2600 <= cp <= 0x27BF or cp == 0xFE0F


def hidden_codepoints(text: str) -> list[str]:
    """Code points that hide text from a reviewer (sota-code-security rules/09 §4, Trojan Source):
    bidi controls, tag characters, a BOM, ZWSP and ZWNJ. A ZERO WIDTH JOINER between two emoji is
    an ordinary emoji sequence (Unicode TS #51) and is allowed; anywhere else it is flagged."""
    hits = []
    for i, ch in enumerate(text):
        cp = ord(ch)
        if (0x202A <= cp <= 0x202E or 0x2066 <= cp <= 0x2069 or 0xE0000 <= cp <= 0xE007F
                or cp in (0xFEFF, 0x200B, 0x200C)):
            hits.append(f"U+{cp:04X}")
        elif cp == 0x200D and not (0 < i < len(text) - 1 and is_emoji(text[i - 1]) and is_emoji(text[i + 1])):
            hits.append("U+200D")
    return hits


def readme_words(text: str) -> int:
    words, fenced = 0, False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if not fenced:
            words += len(re.findall(r"[A-Za-z0-9][\w'’-]*", re.sub(r"`[^`]*`", " ", line)))
    return words


def png_size(path: Path) -> tuple[int, int] | None:
    """Width and height from the IHDR chunk: a header-only read, never a decode."""
    with path.open("rb") as f:
        head = f.read(24)
    if len(head) < 24 or head[:8] != PNG_SIG or head[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", head[16:24])


def run_hook(dist: Path, script: str, data: Path, cfg: Path, extra: dict[str, str]) -> subprocess.CompletedProcess:
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(cfg.parent),
        "CLAUDE_PLUGIN_ROOT": str(dist),
        "CLAUDE_PLUGIN_DATA": str(data),
        "CLAUDE_CONFIG_DIR": str(cfg),
        "CLAUDE_PROJECT_DIR": str(cfg.parent / "proj"),
        **extra,
    }
    return subprocess.run(["bash", str(dist / script)], env=env, cwd=str(cfg.parent),
                          stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=60)


def check(dist: Path, rep: Report) -> None:
    files, dirs, links = walk(dist)
    rel = sorted(p.relative_to(dist).as_posix() for p in files)

    # manifest: plugin.json parses, and its version is the tree's VERSION
    try:
        man = json.loads((dist / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))
        ver = (dist / "VERSION").read_text(encoding="utf-8").strip()
        name = man.get("name", "")
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?", name):
            rep.fail("manifest", f"plugin.json name {name!r} is not lowercase letters, digits and hyphens")
        elif man.get("version") != ver:
            rep.fail("manifest", f"plugin.json version {man.get('version')!r} != VERSION {ver!r}")
        elif not re.fullmatch(r"\d+\.\d+\.\d+", ver):
            rep.fail("manifest", f"VERSION {ver!r} is not X.Y.Z")
        else:
            rep.ok("manifest", f"{name} {ver}, plugin.json == VERSION")
    except (OSError, ValueError) as e:
        rep.fail("manifest", f"plugin.json or VERSION unreadable: {e}")

    # provenance: the tree says which commit it was built from
    try:
        src = (dist / "SOURCE_COMMIT").read_text(encoding="utf-8").strip()
        if re.fullmatch(r"[0-9a-f]{40}", src):
            rep.ok("provenance", f"SOURCE_COMMIT {src[:12]}")
        else:
            rep.fail("provenance", f"SOURCE_COMMIT is not a full commit id: {src[:60]!r}")
    except OSError:
        rep.fail("provenance", "SOURCE_COMMIT missing")

    # entries / files: the counts the directory limits
    entries = len(files) + len(dirs) + len(links)
    if entries > MAX_ENTRIES:
        rep.fail("entries", f"{entries} files and folders (validation stops at 10,000)")
    else:
        rep.ok("entries", f"{entries} files and folders (limit {MAX_ENTRIES})")
    if not files:
        rep.fail("files", "0 files: the tree is empty")
    elif len(files) > MAX_FILES:
        rep.fail("files", f"{len(files)} files (more than {MAX_FILES} is held for a reviewer)")
    else:
        rep.ok("files", f"{len(files)} files (limit {MAX_FILES})")

    # symlinks: blocked where the plugin loads them; none ship at all
    if links:
        rep.fail("symlinks", f"{len(links)} symlink(s): " + ", ".join(p.relative_to(dist).as_posix() for p in links[:3]))
    else:
        rep.ok("symlinks", f"0 symlinks among {entries} entries")

    # sizes and binaries: one read per file
    big, huge, binary, kinds = [], [], [], {"text": 0, "image": 0, "font": 0}
    for p in files:
        size = p.stat().st_size
        r = p.relative_to(dist).as_posix()
        if size > MAX_ANY_BYTES:
            huge.append(f"{r} ({size} B)")
        with p.open("rb") as f:
            head = f.read(16)
        kind = image_kind(head)
        if p.suffix.lower() in FONT_EXT:
            kinds["font"] += 1
            continue
        if kind:
            kinds["image"] += 1
            if kind == "webp" and r == ICON_PATH:
                pass  # the icon check reports this one
            continue
        if size > MAX_TEXT_BYTES:
            big.append(f"{r} ({size} B)")
        if size <= MAX_ANY_BYTES and not is_text(p.read_bytes()):
            binary.append(r)
        else:
            kinds["text"] += 1
    if huge or big:
        rep.fail("sizes", "over the limit: " + ", ".join((huge + big)[:5]))
    else:
        rep.ok("sizes", f"{len(files)} files: none over 5 MiB, no non-image over 256 KiB")
    if binary:
        rep.fail("binaries", f"{len(binary)} file(s) neither text, image nor font: " + ", ".join(binary[:5]))
    else:
        rep.ok("binaries", f"{kinds['text']} text, {kinds['image']} image, {kinds['font']} font")

    # codepoints: every shipped file is loaded by every installer, so a hidden character is High
    hid = []
    for p in files:
        if p.suffix.lower() in FONT_EXT or image_kind(p.open("rb").read(16)):
            continue
        h = hidden_codepoints(p.read_text(encoding="utf-8", errors="replace"))
        if h:
            hid.append(f"{p.relative_to(dist).as_posix()} ({', '.join(sorted(set(h)))})")
    if hid:
        rep.fail("codepoints", f"{len(hid)} file(s) carry hidden code points: " + "; ".join(hid[:5]))
    else:
        rep.ok("codepoints", f"{kinds['text']} text files: no bidi, tag, BOM or stray zero-width characters")

    # junk: OS files the directory blocks
    all_names = [p.name for p in files + dirs + links]
    junk = [n for n in all_names if n in JUNK or n == "__MACOSX"]
    if junk:
        rep.fail("junk", "OS files the directory blocks: " + ", ".join(sorted(set(junk))))
    else:
        rep.ok("junk", f"0 of {len(all_names)} names are .DS_Store, Thumbs.db, desktop.ini or __MACOSX")

    # names: valid on both Windows and macOS, no case-only twins
    bad, seen = [], {}
    for p in files + dirs + links:
        r = p.relative_to(dist).as_posix()
        n = p.name
        if ":" in n or n.endswith((".", " ")) or WIN_DEVICE.match(n) or any(c in n for c in '<>"|?*\\'):
            bad.append(r)
        low = r.lower()
        if low in seen and seen[low] != r:
            bad.append(f"{seen[low]} ~ {r}")
        seen[low] = r
    if bad:
        rep.fail("names", "names invalid on Windows or macOS: " + ", ".join(bad[:5]))
    else:
        rep.ok("names", f"{len(seen)} paths valid on Windows and macOS, no case-only twins")

    # pkgcfg: a package-manager config or lockfile is held or blocked
    pk = [r for r in rel if Path(r).name in PKG_CONFIG]
    if pk:
        rep.fail("pkgcfg", "package-manager files: " + ", ".join(pk))
    else:
        rep.ok("pkgcfg", f"0 of {len(rel)} files are package-manager config or lockfiles")

    # readme: at least 40 words outside code blocks
    rd = dist / "README.md"
    if not rd.is_file():
        rep.fail("readme", "README.md missing")
    else:
        w = readme_words(rd.read_text(encoding="utf-8", errors="replace"))
        if w < README_MIN_WORDS:
            rep.fail("readme", f"README.md has {w} words outside code blocks (need {README_MIN_WORDS})")
        else:
            rep.ok("readme", f"README.md has {w} words outside code blocks (need {README_MIN_WORDS})")

    # license: a LICENSE file, and the manifest names it
    lic = [r for r in rel if "/" not in r and r.upper().startswith(("LICENSE", "COPYING"))]
    if not lic:
        rep.fail("license", "no LICENSE file at the tree root")
    else:
        rep.ok("license", "license file(s): " + ", ".join(lic))

    # hooks: every command is "${CLAUDE_PLUGIN_ROOT}/<file>" naming an executable that ships
    try:
        hj = json.loads((dist / "hooks/hooks.json").read_text(encoding="utf-8"))
        cmds = [h.get("command", "") for groups in hj.get("hooks", {}).values()
                for g in groups for h in g.get("hooks", [])]
        if not cmds:
            rep.fail("hooks", "hooks.json declares 0 commands")
        else:
            probs = []
            for c in cmds:
                m = HOOK_CMD.match(c)
                if not m:
                    probs.append(f"{c!r} is not a quoted ${{CLAUDE_PLUGIN_ROOT}}/<file> path")
                    continue
                t = dist / m.group(1)
                if t.is_symlink() or not t.is_file():
                    probs.append(f"{m.group(1)} does not ship")
                elif not os.access(t, os.X_OK):
                    probs.append(f"{m.group(1)} is not executable")
            if probs:
                rep.fail("hooks", "; ".join(probs))
            else:
                rep.ok("hooks", f"{len(cmds)} of {len(cmds)} hook commands name an executable that ships")
    except (OSError, ValueError, AttributeError) as e:
        rep.fail("hooks", f"hooks/hooks.json unreadable: {e}")

    # helpers: every file a shipped hook script loads by path ships too. A hook that cannot find
    # its helper fails OPEN by design (plugin-budget-check.sh: `[ -x "$lister" ] || exit 0`), so
    # an allowlist that drops one leaves a hook that silently does nothing while every other
    # check stays green. A reference resolves against the script's own dir or the tree root,
    # because `$here` means either, depending on the script.
    try:
        hc = [HOOK_CMD.match(c) for c in cmds] if "cmds" in locals() else []
        targets = sorted({m.group(1) for m in hc if m})
        refs: list[tuple[str, str]] = []
        for tgt in targets + ["scripts/skill-listing-sources.sh"]:
            tp = dist / tgt
            if not tp.is_file():
                continue
            for line in tp.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.lstrip().startswith("#"):
                    continue
                for m in SHELL_REF.finditer(line):
                    refs.append((tgt, m.group(1)))
                for m in PY_REF.finditer(line):
                    refs.append((tgt, "/".join(re.findall(r'"([^"]+)"', m.group(0)))))
        miss = sorted({f"{t} -> {r}" for t, r in refs
                       if not ((dist / Path(t).parent / r).exists() or (dist / r).exists())})
        if not refs:
            rep.fail("helpers", "found 0 path references in the hook scripts, so nothing was checked")
        elif miss:
            rep.fail("helpers", "a hook loads a file that does not ship: " + ", ".join(miss[:5]))
        else:
            rep.ok("helpers", f"{len(set(refs))} path reference(s) in {len(targets)} hook scripts, all shipped")
    except OSError as e:
        rep.fail("helpers", f"could not read a hook script: {e}")

    # icon: the listing icon is taken once, at the first portal save, and cannot change later
    ic = dist / ICON_PATH
    if not ic.is_file() or ic.is_symlink():
        rep.fail("icon", f"{ICON_PATH} missing")
    else:
        size = ic.stat().st_size
        wh = png_size(ic)
        if size >= ICON_MAX_BYTES:
            rep.fail("icon", f"{ICON_PATH} is {size} bytes (must be under 2 MB)")
        elif wh is None:
            rep.fail("icon", f"{ICON_PATH} is not a PNG (no PNG signature and IHDR)")
        elif wh[0] != wh[1]:
            rep.fail("icon", f"{ICON_PATH} is {wh[0]}x{wh[1]}, not square")
        elif not ICON_MIN <= wh[0] <= ICON_MAX:
            rep.fail("icon", f"{ICON_PATH} is {wh[0]}x{wh[1]} (need {ICON_MIN} to {ICON_MAX} px a side)")
        else:
            rep.ok("icon", f"{ICON_PATH} PNG {wh[0]}x{wh[1]}, {size} bytes")

    # routing + hook-refs: run the hooks themselves, in a scratch config dir
    with tempfile.TemporaryDirectory() as t:
        tp = Path(t)
        cfg = tp / "cfg"
        cfg.mkdir()
        (tp / "proj").mkdir()
        try:
            r = run_hook(dist, "scripts/plugin-routing-hook.sh", tp / "data", cfg, {})
            if r.returncode == 0 and r.stdout.startswith(ROUTING_PREFIX) and not r.stderr:
                rep.ok("routing", f"plugin-routing-hook.sh printed {len(r.stdout)} chars beginning {ROUTING_PREFIX!r}, stderr empty")
            else:
                rep.fail("routing", f"plugin-routing-hook.sh rc={r.returncode}, stdout {r.stdout[:60]!r}, stderr {r.stderr.strip()[:120]!r}")
        except (OSError, subprocess.SubprocessError) as e:
            rep.fail("routing", f"plugin-routing-hook.sh did not run: {e}")

        told: list[str] = []
        try:
            n = run_hook(dist, "scripts/plugin-notice.sh", tp / "data", cfg, {})
            data = tp / "data"
            data.mkdir(exist_ok=True)
            stamp = data / ".update-reminder-last"
            stamp.touch()
            os.utime(stamp, (0, 0))  # 1970: due on any interval
            u = run_hook(dist, "scripts/update-reminder.sh", data, cfg, {"SOTA_UPDATE_REMINDER_DAYS": "1"})
            outs = {"plugin-notice.sh": n.stdout, "update-reminder.sh": u.stdout}
            silent = [k for k, v in outs.items() if not v.strip()]
            for v in outs.values():
                told += SCRIPT_REF.findall(v)
            missing = sorted({s for s in told if not (dist / s).is_file()})
            if silent:
                rep.fail("hook-refs", "printed nothing, so nothing was checked: " + ", ".join(silent))
            elif missing:
                rep.fail("hook-refs", "a hook tells the user to run a script that does not ship: " + ", ".join(missing))
            else:
                rep.ok("hook-refs", f"{len(set(told))} script path(s) named by the notice and the reminder, all shipped")
        except (OSError, subprocess.SubprocessError) as e:
            rep.fail("hook-refs", f"a hook did not run: {e}")


# ---------------------------------------------------------------- selftest

def make_png(path: Path, w: int, h: int) -> None:
    def chunk(t: bytes, d: bytes) -> bytes:
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + b"\x00" * w for _ in range(h))  # greyscale, one byte a pixel
    path.write_bytes(PNG_SIG + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


SHIP_SCRIPTS = ["plugin-budget-check.sh", "plugin-notice.sh", "update-reminder.sh",
                "plugin-routing-hook.sh", "code-rules-hook.py", "zsh-equals-hook.py",
                "skill-listing-sources.sh", "install.sh", "statusline.sh", "init-gates.sh",
                "gen-agents-md.sh"]


def good_tree(repo: Path, d: Path) -> None:
    (d / ".claude-plugin").mkdir(parents=True)
    (d / ".claude-plugin/plugin.json").write_text(json.dumps(
        {"name": "fixture-plugin", "version": "1.2.3", "description": "fixture", "license": "MIT"}))
    make_png(d / ICON_PATH, 512, 512)
    (d / "VERSION").write_text("1.2.3\n")
    (d / "LICENSE").write_text("MIT fixture licence text\n")
    (d / "SOURCE_COMMIT").write_text("0" * 40 + "\n")
    (d / "README.md").write_text(("This fixture plugin exists only so that the checker can be shown a "
                                  "tree that passes every check before each known-bad is applied to "
                                  "a fresh copy of it, one at a time, so that a catch for the wrong "
                                  "reason is visible as a second failing check rather than a pass.\n"))
    (d / "skills/x").mkdir(parents=True)
    # an emoji ZWJ sequence is legitimate text and must pass [codepoints]
    (d / "skills/x/SKILL.md").write_text("---\nname: x\ndescription: fixture skill\n---\n"
                                         "`'\U0001F468\u200d\U0001F469\u200d\U0001F467'.length === 8`\n",
                                         encoding="utf-8")
    # the paths code-rules-hook.py reads at run time (the [helpers] check resolves them)
    for sk in ("sota", "sota-code-security/rules"):
        (d / "skills" / sk).mkdir(parents=True, exist_ok=True)
    (d / "skills/sota/SKILL.md").write_text("---\nname: sota\ndescription: fixture router\n---\nbody\n")
    (d / "skills/sota-code-security/rules/01-x.md").write_text("# fixture\n")
    (d / "hooks").mkdir()
    shutil.copy2(repo / "hooks/hooks.json", d / "hooks/hooks.json")
    (d / "scripts").mkdir()
    for s in SHIP_SCRIPTS:
        shutil.copy2(repo / "scripts" / s, d / "scripts" / s)


def m_files(d: Path) -> None:
    (d / "many").mkdir()
    for i in range(MAX_FILES + 1):
        (d / "many" / f"f{i}.md").write_text("x\n")


def m_install_line(d: Path) -> None:
    p = d / "scripts/install.sh"
    s = p.read_text(encoding="utf-8")
    p.write_text(s.replace("readonly HOOK_CMD=", "readonly HOOK_CMD_RENAMED=", 1), encoding="utf-8")


def m_hook_target(d: Path) -> None:
    p = d / "hooks/hooks.json"
    p.write_text(p.read_text().replace("plugin-notice.sh", "plugin-notice-gone.sh", 1))


MUTATIONS = [
    ("manifest", "VERSION disagrees with plugin.json", lambda d: (d / "VERSION").write_text("9.9.9\n")),
    ("provenance", "SOURCE_COMMIT missing", lambda d: (d / "SOURCE_COMMIT").unlink()),
    ("files", f"{MAX_FILES + 1} extra files", m_files),
    ("sizes", "a 300 KiB text file", lambda d: (d / "big.md").write_text("x" * 300 * 1024)),
    ("symlinks", "a symlink", lambda d: (d / "link.md").symlink_to("README.md")),
    ("binaries", "a zip file", lambda d: (d / "a.zip").write_bytes(b"PK\x03\x04\x00\x00" + bytes(range(256)))),
    ("codepoints", "a right-to-left override hidden in a skill file",
     lambda d: (d / "skills/x/SKILL.md").write_text("---\nname: x\ndescription: ok\n---\nrun \u202eexample\n", encoding="utf-8")),
    ("codepoints", "a zero-width joiner between two letters, outside any emoji sequence",
     lambda d: (d / "skills/x/SKILL.md").write_text("---\nname: x\ndescription: ok\n---\nad\u200dmin\n", encoding="utf-8")),
    ("junk", "a .DS_Store", lambda d: (d / ".DS_Store").write_text("x\n")),
    ("names", "a colon in a file name", lambda d: (d / "a:b.md").write_text("x\n")),
    ("pkgcfg", "an .npmrc", lambda d: (d / ".npmrc").write_text("registry=https://example.invalid/\n")),
    ("readme", "a 9-word README with words in a fence",
     lambda d: (d / "README.md").write_text("Too short to list. Nine words is not forty.\n```\n" + "word " * 60 + "\n```\n")),
    ("license", "no LICENSE file", lambda d: (d / "LICENSE").unlink()),
    ("hooks", "a hook command naming a file that does not ship", m_hook_target),
    ("helpers", "plugin-budget-check.sh's lister does not ship, so the hook would go silent",
     lambda d: (d / "scripts/skill-listing-sources.sh").unlink()),
    ("icon", "icon missing", lambda d: (d / ICON_PATH).unlink()),
    ("icon", "icon not square (600x512)", lambda d: make_png(d / ICON_PATH, 600, 512)),
    ("icon", "icon too small (256x256)", lambda d: make_png(d / ICON_PATH, 256, 256)),
    ("icon", "icon is a JPEG named .png",
     lambda d: (d / ICON_PATH).write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 64)),
    ("routing", "HOOK_CMD unreadable, so the hook prints only an error on stderr", m_install_line),
    ("hook-refs", "the notice names scripts/init-gates.sh and it does not ship",
     lambda d: (d / "scripts/init-gates.sh").unlink()),
]


def selftest() -> int:
    repo = Path(__file__).resolve().parent.parent
    bad = 0
    with tempfile.TemporaryDirectory() as t:
        base = Path(t) / "good"
        good_tree(repo, base)
        rep = Report(quiet=True)
        check(base, rep)
        if rep.failed:
            print(f"FAIL selftest: the known-good tree fails {rep.failed}; nothing below would mean anything")
            check(base, Report())
            return 1
        print(f"ok   selftest: the known-good tree passes all checks")
        for i, (want, what, mutate) in enumerate(MUTATIONS):
            d = Path(t) / f"bad{i}"
            shutil.copytree(base, d, symlinks=True)
            mutate(d)
            rep = Report(quiet=True)
            check(d, rep)
            if rep.failed == [want]:
                print(f"ok   selftest: {what} -> [{want}] fails, and nothing else")
            else:
                bad += 1
                print(f"FAIL selftest: {what} -> expected only [{want}] to fail, got {rep.failed or 'nothing'}")
    n = len(MUTATIONS)
    print(f"{'PASS' if not bad else 'FAIL'}: {n - bad}/{n} known-bads caught by their own check")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] in {"-h", "--help"}:
        print(__doc__)
        return 0 if len(argv) == 2 else 2
    if argv[1] == "--selftest":
        return selftest()
    dist = Path(argv[1])
    if not dist.is_dir():
        print(f"check-plugin-dist: {dist} is not a directory", file=sys.stderr)
        return 2
    rep = Report()
    check(dist.resolve(), rep)
    if rep.failed:
        print(f"FAIL: {len(rep.failed)} check(s) failed: {', '.join(rep.failed)}")
        return 1
    print("PASS: every check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
