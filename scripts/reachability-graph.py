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
For the skills that DECLARE their routing it checks the declaration instead (C4, the stage-3 pilot):
a manifest in MANIFEST_DIR names, per rules file, the task tags that should route a builder there;
every tag's keywords must appear in that file's own routing prose (its index row and the BUILD lines
that reference it), every declared `via` hop (05 -> 09 when the parser is security-critical) must be
a real edge in this graph, and every labelled case must reach the files it names. A BUILD trigger
that is removed from the prose, or a pointer that is deleted, then fails a named case.

`--sync` checks the other half, BUILD rule <-> AUDIT probe, at section level (invariant 43). A
numbered section (`## N.`, `## Na.`, `## §N`, and since 2026-10-25 dotted `## N.M`) is a BUILD rule; a checklist item citing `(§N)` in the
same file is its probe. Measured 2026-10-24: 1,246 of 1,770 numbered sections had no citing item and
3,124 of 4,146 items cited no section, so the check is a RATCHET over a committed baseline
(SYNC_BASELINE): S1 every numbered section is cited by its own checklist, marked `*(advisory)*` or
`*(audited in ...)*` within its first lines, or listed in the baseline; S2 per file, checklist items
citing no section never exceed the baseline count; S3 a rules file with no numbered sections is in
the baseline (new files number their sections), and S2 skips such a file since it has nothing
to cite; S4 every baseline entry is still needed (a fixed one
must leave, so the debt only shrinks); S5 the baseline does not grow against the merge base, except
by CONVERSION: a file unnumbered at the merge base that is now numbered moves its debt from file level
to section level through --sync-convert (probes 43e and 43f hold both sides of that exemption).

Usage:
  reachability-graph.py --check            run C1-C3; exit 1 on any violation
  reachability-graph.py --sync             run S1-S5; exit 1 on any violation
  reachability-graph.py --sync-tighten     rewrite the baseline, REMOVING stale entries only
  reachability-graph.py --sync-convert     move newly numbered, formerly unnumbered files to section-level debt
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


# --- C4: declared routing (stage-3 pilot) --------------------------------------------------------
MANIFEST_DIR = "scripts/skill-manifests"


def routing_prose(sm_text, rules_file):
    """The prose that routes a builder to one rules file: its own rules-index row (the row whose FIRST
    cell links it -- another row may mention it, as rust's 05 row mentions 08's move) and every BUILD
    line that references it by link, `rules/NN` or "Load NN"."""
    b, n = os.path.basename(rules_file), os.path.basename(rules_file)[:2]
    idx = section(sm_text, r"Rules? index")
    row = next((l for l in idx.splitlines() if re.match(r"^\|\s*\[`?rules/%s" % re.escape(b[:2]), l)
                and b in l.split("|")[1]), "")
    build = [l for l in section(sm_text, "BUILD").splitlines()
             if b in l or re.search(r"rules/%s\b|[Ll]oad %s\b" % (n, n), l)]
    return "\n".join([row] + build)


def manifest_check(edges):
    bad, cases_run, manifests = [], 0, 0
    if not os.path.isdir(MANIFEST_DIR):
        return bad, 0, 0
    for mf in sorted(os.listdir(MANIFEST_DIR)):
        if not mf.endswith(".json"):
            continue
        manifests += 1
        m = json.load(open(os.path.join(MANIFEST_DIR, mf), encoding="utf-8"))
        sk = m["skill"]
        sm = "skills/%s/SKILL.md" % sk
        text = strip_code(open(sm, encoding="utf-8").read())
        have = {os.path.basename(f)[:2]: f for f in git_files("skills/%s/rules/*.md" % sk)}
        decl = m["files"]
        for n in sorted(set(have) - set(decl)):
            bad.append("C4 %s: rules/%s has no declared route" % (mf, n))
        for n in sorted(set(decl) - set(have)):
            bad.append("C4 %s: declares rules/%s, which does not exist" % (mf, n))
        for n, spec in sorted(decl.items()):
            if n not in have:
                continue
            if not spec.get("build"):
                bad.append("C4 %s: rules/%s declares no BUILD tag" % (mf, n))
            prose = routing_prose(text, have[n]).lower()
            for tag in spec.get("build", []):
                kws = m["tags"].get(tag)
                if kws is None:
                    bad.append("C4 %s: rules/%s uses undefined tag %r" % (mf, n, tag))
                elif not any(k.lower() in prose for k in kws):
                    bad.append("C4 %s: rules/%s is declared for %r, but none of %s appears in its index row or "
                               "the BUILD lines that reference it" % (mf, n, tag, kws))
        for v in m.get("via", []):
            src, dst = have.get(v["from"]), have.get(v["to"])
            if not (src and dst and (src, "same-skill", dst) in edges):
                bad.append("C4 %s: declared hop rules/%s -> rules/%s (when %s) has no link in the graph"
                           % (mf, v["from"], v["to"], v["when"]))
        aud_all = COVERAGE in section(text, "AUDIT")
        for c in m.get("cases", []):
            cases_run += 1
            tags = set(c["tags"])
            if c["mode"] == "audit":
                got = set(have) if aud_all else set()
            else:
                got = {n for n, spec in decl.items() if tags & set(spec.get("build", []))}
                grew = True
                while grew:
                    grew = False
                    for v in m.get("via", []):
                        src, dst = have.get(v["from"]), have.get(v["to"])
                        if (v["from"] in got and v["to"] not in got and set(v["when"]) <= tags
                                and src and dst and (src, "same-skill", dst) in edges):
                            got.add(v["to"]); grew = True
            miss = sorted(set(c["must_load"]) - got)
            if miss:
                bad.append("C4 %s: case %r (%s) does not reach rules/%s" % (mf, c["task"], c["mode"], ", rules/".join(miss)))
    return bad, manifests, cases_run


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
    # C4 -- declared routing, for the skills that have a manifest
    c4, n_manifests, n_cases = manifest_check(set(edges))
    bad += c4
    domain = sum(1 for sm in skill_mds if sm.split("/")[1] not in (ROUTER,) and sm.split("/")[1] in by_skill)
    print("SCOPE %d" % len(rules))
    for b in bad:
        print(b)
    if bad:
        return 1
    print("    ok (%d rules files, %d edges, 0 index-only; AUDIT coverage: %d by the coverage line, %d by naming "
          "every file, of %d domain skills; every numeric reference resolves; %d declared manifests, %d labelled cases)"
          % (len(rules), len(edges), c2_line, c2_enum, domain, n_manifests, n_cases))
    return 0


# --- invariant 43: section <-> probe sync, as a ratchet ------------------------------------------
SYNC_BASELINE = "scripts/section-sync-baseline.json"
# Dotted ids count (`## 6.1`, `## 3.4a`): until 2026-10-25 only `## N.` / `## Na` did, so every rules file
# of sota-devsecops and sota-testing, numbered `## N.M`, read as UNNUMBERED and sat outside the ratchet.
SECTION = re.compile(r"^## (?:§\s?)?(\d+[a-z]?(?:\.\d+[a-z]?)*)\.?\s+(.*)$", re.M)
MARKER = re.compile(r"\*\((?:advisory|audited in)\b", re.I)


def local_cites(text):
    """Section numbers a checklist cites in its OWN file: `§N` not preceded (same line, 60 chars) by
    another file's reference, so `[rules/03](...) §2` and `sota-x` rules/NN §M do not count."""
    out = set()
    for line in text.splitlines():
        for m in re.finditer(r"§\s?(\d+[a-z]?(?:\.\d+[a-z]?)*)", line):
            if re.search(r"rules/\d|sota-[a-z]|SKILL\.md|\]\(", line[max(0, m.start() - 60):m.start()]):
                continue
            parts = m.group(1).split(".")  # `§6.3.2` cites 6, 6.3 and 6.3.2: a top-level `## 6.` is cited
            for k in range(1, len(parts) + 1):  # by `§6.3` exactly as before, and a dotted `## 6.3` by itself
                out.add(".".join(parts[:k]))
    return out


def sync_state():
    """(uncited sections as 'file :: heading', {file: uncited item count}, [files with no sections])."""
    unc, items, unnumbered = [], {}, []
    for f in git_files("skills/*/rules/*.md"):
        s = open(f, encoding="utf-8").read()
        i = s.find("\n## Audit checklist")
        body, chk = (s[:i], s[i:]) if i >= 0 else (s, "")
        secs = list(SECTION.finditer(body))
        if not secs:
            unnumbered.append(f)
        cited = local_cites(chk)
        for k, m in enumerate(secs):
            end = secs[k + 1].start() if k + 1 < len(secs) else len(body)
            head = "\n".join(body[m.end():end].strip().splitlines()[:3])
            if m.group(1) in cited or MARKER.search(m.group(0) + "\n" + head):
                continue
            unc.append("%s :: %s" % (f, m.group(0)[3:].strip()))
        n = sum(1 for it in re.findall(r"^- \[ \].*?(?=^- \[ \]|\Z)", chk, re.M | re.S) if not local_cites(it))
        if n:
            items[f] = n
    return sorted(unc), items, sorted(unnumbered)


def load_baseline(text=None):
    if text is None:
        if not os.path.exists(SYNC_BASELINE):
            return None
        text = open(SYNC_BASELINE, encoding="utf-8").read()
    b = json.loads(text)
    return set(b["uncited_sections"]), dict(b["uncited_items"]), set(b["unnumbered_files"])


def write_baseline(unc, items, unnumbered):
    with open(SYNC_BASELINE, "w", encoding="utf-8") as fh:
        json.dump({"_note": "invariant 43 ratchet: entries may only be REMOVED. Regenerate with "
                            "`python3 scripts/reachability-graph.py --sync-tighten`, which never adds one.",
                   "uncited_sections": sorted(unc), "uncited_items": dict(sorted(items.items())),
                   "unnumbered_files": sorted(unnumbered)}, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def merge_base_rev():
    mb = subprocess.run(["git", "merge-base", "HEAD", "origin/main"], capture_output=True, text=True)
    return mb.stdout.strip() if mb.returncode == 0 and mb.stdout.strip() else None


def merge_base_baseline(rev):
    """The baseline as it was at the merge base, or None when there is none."""
    if rev is None:
        return None
    old = subprocess.run(["git", "show", "%s:%s" % (rev, SYNC_BASELINE)], capture_output=True, text=True)
    return load_baseline(old.stdout) if old.returncode == 0 else None


def new_files_since(rev):
    """Rules files that did not exist at the merge base (a split or a new file)."""
    if rev is None:
        return set()
    old = subprocess.run(["git", "ls-tree", "-r", "--name-only", rev, "skills/"], capture_output=True, text=True)
    return set(git_files("skills/*/rules/*.md")) - set(old.stdout.split())


def heading(entry):
    return entry.split(" :: ", 1)[1]


def sync_check():
    unc, items, unnumbered = sync_state()
    base = load_baseline()
    if base is None:
        print("FAIL: %s missing -- the ratchet has nothing to compare against" % SYNC_BASELINE)
        return 1
    b_unc, b_items, b_unnum = base
    rev = merge_base_rev()
    fresh = new_files_since(rev)
    b_heads, now_heads = {heading(e) for e in b_unc}, {heading(e) for e in unc}
    bad, moved = [], 0
    for e in unc:
        if e in b_unc:
            continue
        if heading(e) in b_heads:  # the same section moved or copied: debt relocated, not added
            moved += 1
            continue
        bad.append("S1 %s: a numbered section no checklist item cites (§N) -- cite it, or mark it "
                   "*(advisory)* / *(audited in ...)* under its heading" % e)
    total_now, total_base = sum(items.values()), sum(b_items.values())
    for f, n in items.items():
        if n <= b_items.get(f, 0):
            continue
        if f in unnumbered:  # no `## N.` to cite: S3 tracks the file itself until it is numbered
            continue
        if f in fresh and total_now <= total_base:  # a split: items moved into a new file
            moved += 1
            continue
        bad.append("S2 %s: %d checklist items cite no section (baseline %d) -- a new item cites the "
                   "section it checks, as (§N)" % (f, n, b_items.get(f, 0)))
    for f in unnumbered:
        if f not in b_unnum:
            bad.append("S3 %s: a rules file with no numbered sections -- number them (## 1. ...) so "
                       "checklist items can cite them" % f)
    stale = [e for e in sorted(b_unc - set(unc)) if heading(e) not in now_heads] \
        + ["%s (items: baseline %d, now %d)" % (f, n, items.get(f, 0))
           for f, n in b_items.items() if items.get(f, 0) < n] + sorted(b_unnum - set(unnumbered))
    relocated = [e for e in sorted(b_unc - set(unc)) if heading(e) in now_heads]
    for e in stale + ["%s (moved; re-key it)" % e for e in relocated]:
        bad.append("S4 stale baseline entry, now fixed: %s -- run `python3 scripts/reachability-graph.py "
                   "--sync-tighten` and commit the smaller baseline" % e)
    mb = merge_base_baseline(rev)
    if mb is not None:
        m_unc, m_items, m_unnum = mb
        m_heads = {heading(e) for e in m_unc}
        # CONVERTED debt is not growth (2026-10-25): a file the merge base listed as UNNUMBERED that is now
        # numbered moves its debt from file level to section level, and its uncited sections enter the
        # baseline through --sync-convert. Exempt only files unnumbered AT THE MERGE BASE, so the exemption
        # cannot be granted by editing the branch's own baseline; a bogus entry for such a file is stale (S4).
        conv = [e for e in b_unc if e.split(" :: ", 1)[0] in m_unnum]
        grew = sorted(b_heads - m_heads - {heading(e) for e in conv})
        if len(b_unc) - len(conv) > len(m_unc):
            grew.append("uncited sections %d > %d" % (len(b_unc) - len(conv), len(m_unc)))
        if total_base > sum(m_items.values()):
            grew.append("uncited items %d > %d" % (total_base, sum(m_items.values())))
        grew += sorted(set(b_unnum) - set(m_unnum) - fresh)
        for e in grew:
            bad.append("S5 the baseline GREW against the merge base: %s -- the debt may only shrink" % e)
    print("SCOPE %d" % len(git_files("skills/*/rules/*.md")))
    for b in bad:
        print(b)
    if bad:
        return 1
    print("    ok (%d numbered sections uncited and %d uncited checklist items, all baselined%s; %d files "
          "unnumbered; growth %s)" % (len(unc), total_now, ", %d relocated" % moved if moved else "", len(unnumbered),
                                      "checked against the merge base" if mb is not None else
                                      "not checked: no baseline at the merge base (new here, or no origin/main)"))
    return 0


def sync_tighten():
    """Shrink the baseline to what is still needed, re-keying relocated debt; never adds new debt."""
    unc, items, unnumbered = sync_state()
    base = load_baseline()
    if base is None:
        print("no baseline to tighten; refusing to create one silently")
        return 1
    b_unc, b_items, b_unnum = base
    b_heads = {heading(e) for e in b_unc}
    fresh = new_files_since(merge_base_rev())
    new_unc = [e for e in unc if e in b_unc or heading(e) in b_heads]
    new_items = {f: min(n, b_items[f]) for f, n in items.items() if f in b_items}
    budget = sum(b_items.values()) - sum(new_items.values())
    for f, n in sorted(items.items()):
        if f not in b_items and f in fresh and n <= budget:  # items moved into a split-off file
            new_items[f] = n
            budget -= n
    new_unnum = [f for f in unnumbered if f in b_unnum]
    write_baseline(new_unc, new_items, new_unnum)
    print("baseline tightened: sections %d -> %d, items %d -> %d, unnumbered %d -> %d (no new debt added)"
          % (len(b_unc), len(new_unc), sum(b_items.values()), sum(new_items.values()), len(b_unnum), len(new_unnum)))
    return 0


def sync_convert():
    """Move files the baseline lists as UNNUMBERED, and that now have numbered sections, from file-level
    to section-level debt: their uncited sections and items enter the baseline, the file leaves the
    unnumbered list. Touches no other entry; S5 accepts it only for files unnumbered at the merge base."""
    unc, items, unnumbered = sync_state()
    base = load_baseline()
    if base is None:
        print("no baseline to convert into; refusing to create one silently")
        return 1
    b_unc, b_items, b_unnum = base
    done = sorted(f for f in b_unnum if f not in unnumbered)
    add = [e for e in unc if e.split(" :: ", 1)[0] in done and e not in b_unc]
    new_items = dict(b_items)
    for f in done:
        if f in items:
            new_items[f] = items[f]
        else:
            new_items.pop(f, None)
    write_baseline(sorted(set(b_unc) | set(add)), new_items, sorted(b_unnum - set(done)))
    print("converted %d file(s) from unnumbered to section-level debt: %d uncited section(s) added; "
          "unnumbered %d -> %d" % (len(done), len(add), len(b_unnum), len(b_unnum) - len(done)))
    return 0


def main(argv):
    if argv[1:2] == ["--sync-convert"]:
        return sync_convert()
    if argv[1:2] == ["--check"]:
        return check()
    if argv[1:2] == ["--sync"]:
        return sync_check()
    if argv[1:2] == ["--sync-tighten"]:
        return sync_tighten()
    if argv[1:2] == ["--sync-init"]:  # one-time: write the first baseline (refuses if one exists)
        if load_baseline() is not None:
            print("baseline exists; use --sync-tighten"); return 1
        write_baseline(*sync_state()); print("baseline written"); return 0
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
