#!/usr/bin/env python3
"""Build the rules-file reference graph of the library and check that every rules file is reachable.

An agent reaches a rules file only through a path: the router, a skill's SKILL.md (its BUILD steps,
its AUDIT steps, its rules index), or a link from another rules file. The 2026-10-24 library-wide
review (docs/ADOPTION-LOG.md) found that these paths rot silently: a sweep that lists "01-06" never
reaches the 07 added later; an AUDIT step that loads "the rules files matching what exists" skips the
file whose probe checks for something ABSENT; a split leaves a BUILD step pointing at the old file.
None of that breaks a link, so invariants 8 and 18 (links and section cites resolve) stay green.

This script makes the graph explicit and checks three exact properties (invariant 42):

  C1  every rules file has at least one inbound reference other than its own SKILL.md rules-index
      row (a BUILD or AUDIT step, another rules file, another skill, or the router);
  C2  every domain skill's AUDIT section either names every one of its rules files, or carries the
      canonical coverage line (COVERAGE below), which forbids skipping a file because the thing it
      checks for is absent;
  C3  every same-skill numeric reference (`rules/NN`, `NN-name.md`, "Load NN", "skip NN") resolves
      to a rules file that exists.

What it cannot check is whether a trigger fires for the RIGHT task: that is semantic (ROADMAP 16).

Usage:
  reachability-graph.py --check            run C1-C3; exit 1 on any violation
  reachability-graph.py --json             print the graph (nodes, edges with their source kind)
  reachability-graph.py --explain PATH     print every inbound edge of one rules file
"""
import json
import os
import re
import subprocess
import sys

COVERAGE = ("**Coverage:** every `rules/` file's Audit checklist applies in AUDIT mode. Mark one "
            "*not applicable* only with its reason in the report — never skip a file because the "
            "thing it checks for is absent, since that absence may be the finding.")

ROUTER = "sota"


def git_files(pattern):
    out = subprocess.run(["git", "ls-files", pattern], capture_output=True, text=True, check=True).stdout
    return sorted(f for f in out.split("\n") if f)


def section(text, head):
    """Body of the first `## <head>...` section, or ''. Headings are matched case-insensitively."""
    m = re.search(r"^## " + head + r"[^\n]*\n(.*?)(?=^## |\Z)", text, re.M | re.S | re.I)
    return m.group(1) if m else ""


def strip_code(text):
    """Drop fenced code blocks: a path inside a code sample is not a reference an agent follows."""
    return re.sub(r"^```.*?^```", "", text, flags=re.M | re.S)


def link_targets(text, src_dir):
    """Resolved repo paths of every Markdown link target in text."""
    out = set()
    for tgt in re.findall(r"\]\(([^)\s#]+\.md)(?:#[^)]*)?\)", text):
        out.add(os.path.normpath(os.path.join(src_dir, tgt)))
    return out


CROSS = re.compile(r"`(sota(?:-[a-z0-9-]+)?)`\]?(?:\([^)]*\))?\s+\[?`?(?:\*\*)?\[?`?rules/(\d{2})"
                   r"|\b(sota(?:-[a-z0-9-]+)?)/rules/(\d{2})")


def same_skill_numbers(text, is_skill_md):
    """Two-digit rules numbers a same-skill text points at, by prose rather than by link.

    Cross-skill spans (`sota-x` rules/NN) and link targets are removed first, so another skill's
    rules/06 is never read as this skill's. "read NN" is not a verb form: it matched "read 10
    docstrings" (measured 2026-10-24), so only "load NN" and "skip NN" count.
    """
    text = CROSS.sub(" ", re.sub(r"\[[^\]]*\]\([^)]*\)", " ", text))  # links: resolved by target
    nums = set(re.findall(r"(?<![\w/.-])rules/(\d{2})\b", text))
    nums |= set(re.findall(r"(?<![\w/.-])(\d{2})-[a-z0-9-]+\.md", text))
    if is_skill_md:
        nums |= set(re.findall(r"\b(?:[Ll]oad|[Ss]kip)\s+(\d{2})\b", text))
    return nums


def cross_skill_refs(text):
    """(skill, NN) pairs a text names in another skill: `sota-x` rules/NN, sota-x/rules/NN."""
    return {(a or c, b or d) for a, b, c, d in CROSS.findall(text)}


def build():
    rules = git_files("skills/*/rules/*.md")
    skill_mds = git_files("skills/*/SKILL.md")
    if not rules or not skill_mds:
        print("FAIL: 0 rules files or 0 SKILL.md enumerated -- the graph would verify nothing")
        sys.exit(1)
    by_skill = {}
    for f in rules:
        sk = f.split("/")[1]
        by_skill.setdefault(sk, {})[os.path.basename(f)[:2]] = f
    edges = []  # (source, source_kind, target)

    def add(src, kind, tgt):
        if tgt in rules and tgt != src:
            edges.append((src, kind, tgt))

    unresolved = []
    for sm in skill_mds:
        sk = sm.split("/")[1]
        text = strip_code(open(sm, encoding="utf-8").read())
        parts = {"build": section(text, "BUILD"), "audit": section(text, "AUDIT"),
                 "index": section(text, r"Rules? index")}
        rest = text
        for body in parts.values():
            rest = rest.replace(body, "") if body else rest
        parts["skill-other"] = rest
        for kind, body in parts.items():
            src_kind = ("router-" + kind) if sk == ROUTER else kind
            for tgt in link_targets(body, os.path.dirname(sm)):
                add(sm, src_kind, tgt)
            for n in same_skill_numbers(body, True):
                tgt = by_skill.get(sk, {}).get(n)
                if tgt:
                    add(sm, src_kind, tgt)
                elif kind in ("build", "audit"):
                    unresolved.append("%s (%s) names %s rules %s, which does not exist" % (sm, kind, sk, n))
            for osk, n in cross_skill_refs(body):
                if osk != sk and n in by_skill.get(osk, {}):
                    add(sm, "router" if sk == ROUTER else "other-skill", by_skill[osk][n])
    for f in rules:
        sk = f.split("/")[1]
        text = strip_code(open(f, encoding="utf-8").read())
        for tgt in link_targets(text, os.path.dirname(f)):
            add(f, "same-skill" if tgt.split("/")[1] == sk else "other-skill", tgt)
        for n in same_skill_numbers(text, False):
            if n in by_skill.get(sk, {}):
                add(f, "same-skill", by_skill[sk][n])
        for osk, n in cross_skill_refs(text):
            if osk != sk and n in by_skill.get(osk, {}):
                add(f, "other-skill", by_skill[osk][n])
    return rules, skill_mds, by_skill, sorted(set(edges)), unresolved


def check():
    rules, skill_mds, by_skill, edges, unresolved = build()
    inbound = {f: [] for f in rules}
    for src, kind, tgt in edges:
        inbound[tgt].append((src, kind))
    bad = []
    # C1 -- a path other than the file's own index row
    index_only = []
    for f in rules:
        own_sm = "skills/%s/SKILL.md" % f.split("/")[1]
        others = [(s, k) for s, k in inbound[f] if not (s == own_sm and k in ("index", "router-index"))]
        if not others:
            index_only.append(f)
    for f in index_only:
        bad.append("C1 %s: no inbound reference except its own rules-index row" % f)
    # C2 -- AUDIT coverage
    c2_line = c2_enum = 0
    for sm in skill_mds:
        sk = sm.split("/")[1]
        if sk == ROUTER or sk not in by_skill:
            continue
        aud = section(open(sm, encoding="utf-8").read(), "AUDIT")
        if not aud:
            bad.append("C2 %s: no AUDIT section found" % sm)
            continue
        if COVERAGE in aud:
            c2_line += 1
            continue
        named = {t for s, k, t in edges if s == sm and k == "audit"}
        missing = sorted(set(by_skill[sk].values()) - named)
        if missing:
            bad.append("C2 %s: AUDIT names %d of %d rules files and lacks the coverage line; missing: %s"
                       % (sm, len(by_skill[sk]) - len(missing), len(by_skill[sk]),
                          ", ".join(os.path.basename(m)[:2] for m in missing)))
        else:
            c2_enum += 1
    # C3 -- numeric references resolve
    bad += ["C3 " + u for u in unresolved]
    domain = sum(1 for sm in skill_mds if sm.split("/")[1] not in (ROUTER,) and sm.split("/")[1] in by_skill)
    print("SCOPE %d" % len(rules))
    for b in bad:
        print(b)
    if bad:
        return 1
    print("    ok (%d rules files, %d edges, 0 index-only; AUDIT coverage: %d by the coverage line, %d by naming "
          "every file, of %d domain skills; every numeric reference resolves)"
          % (len(rules), len(edges), c2_line, c2_enum, domain))
    return 0


def main(argv):
    if argv[1:2] == ["--check"]:
        return check()
    if argv[1:2] == ["--json"]:
        rules, _, _, edges, unresolved = build()
        json.dump({"nodes": rules, "edges": [dict(source=s, kind=k, target=t) for s, k, t in edges],
                   "unresolved": unresolved}, sys.stdout, indent=1)
        print()
        return 0
    if argv[1:2] == ["--explain"] and len(argv) == 3:
        _, _, _, edges, _ = build()
        hits = [(s, k) for s, k, t in edges if t == argv[2]]
        for s, k in hits:
            print("%-12s %s" % (k, s))
        print("%d inbound edge(s) to %s" % (len(hits), argv[2]))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
