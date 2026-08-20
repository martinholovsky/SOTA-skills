#!/usr/bin/env python3
"""Invariant 18 — every `§N` reference in skills/ resolves to a real section.

Prints one line per finding and a final `SCOPE <n>` line with the number of
references it actually resolved. Exits non-zero on any finding.

Why this exists: invariant 8 resolves Markdown links; a `§` reference is prose,
so nothing checked ~1,300 of them. See the header comment in check-invariants.sh.
"""
import collections, glob, re, subprocess, sys

# `## 3.`, `## §3 `, `## 8a.`, `### 2.2a` and `### 1b.1`. The letter suffix binds to
# EACH component, not just the last: an earlier `(\d+(?:\.\d+)*[a-z]?)` read `### 1b.1`
# as heading `1b`, which silently re-satisfied a `§1b` reference after `## 1b.` was
# renamed — and made negative-control probe 18 report INERT (caught 2026-08-20 by the
# harness, not by review).
HEADING  = re.compile(r'^#{2,4}\s+§?(\d+[a-z]?(?:\.\d+[a-z]?)*)[.\s]')
FENCE    = re.compile(r'^\s*```')
# External standards cite with `§` too (45 CFR §164.312, PCI DSS §6.4.3) and are
# never internal sections. Keyword-gated rather than shape-gated: §6.4.3 is
# shaped exactly like an internal reference.
EXTERNAL = re.compile(r'(CFR|PCI|DSS|ASVS|NIST|HIPAA|GDPR|\bISO\b|\bIEC\b|62443'
                      r'|800-\d|USC|Art\.)[^\n]{0,40}$')
SEC      = re.compile(r'§(\d+[a-z]?(?:\.\d+[a-z]?){0,2})\b')   # §3, §8a, §2.2a, §1b.1
RULES    = re.compile(r'`?rules/(\d{2})[a-z0-9-]*`?|(?<![\w/])`(\d{2})`')
SKILL    = re.compile(r'\b(sota(?:-[a-z]+)*)\b')
ITEM     = re.compile(r'^\s{0,3}(\d+)\.\s')            # a top-level ordered-list item


def index(path):
    """(heading ids, {section: ordered-list item numbers}) — `§N.M` can mean either."""
    heads, items, cur, fenced = set(), collections.defaultdict(set), None, False
    with open(path, encoding='utf-8') as fh:
        for line in fh:
            if FENCE.match(line):
                fenced = not fenced
                continue
            if fenced:
                continue
            m = HEADING.match(line)
            if m:
                heads.add(m.group(1))
                cur = m.group(1)
                continue
            it = ITEM.match(line)
            if it and cur:
                items[cur].add(it.group(1))
    return heads, items


def main():
    files = subprocess.run(['git', 'ls-files', 'skills/*/*.md', 'skills/*/rules/*.md'],
                           capture_output=True, text=True, check=True).stdout.split()
    if not files:
        print('no skill files found — pathspec drift?')
        print('SCOPE 0')
        return 1

    idx = {f: index(f) for f in files}

    def rules_file(skill, nn):
        hits = glob.glob(f'skills/{skill}/rules/{nn}-*.md')
        return hits[0] if len(hits) == 1 else None

    def resolves(target, sec):
        heads, items = idx[target]
        if sec in heads:
            return True
        if '.' in sec:                                  # §N.M -> item M of section N
            head, _, item = sec.rpartition('.')
            if head in heads and item in items.get(head, ()):
                return True
        return False

    findings, resolved = [], 0
    for f in files:
        own = f.split('/')[1]
        lines = open(f, encoding='utf-8').read().split('\n')
        fenced = False
        for i, line in enumerate(lines, 1):
            if FENCE.match(line):
                fenced = not fenced
                continue
            if fenced:
                continue
            # a reference may wrap across a line break; carry the previous tail
            prev = lines[i - 2][-80:] if i >= 2 else ''
            joined, off = prev + ' ' + line, len(prev) + 1
            skills_here = [m.group(1) for m in SKILL.finditer(joined)] + [own]
            rules_here = [(m.start(), m.end(), m.group(1) or m.group(2), m.group(1) is None)
                          for m in RULES.finditer(joined)]
            for m in SEC.finditer(joined):
                if m.end() <= off:            # matched wholly inside the carried tail
                    continue
                if EXTERNAL.search(joined[:m.start()]):
                    continue
                sec, cands, dangling = m.group(1), {f}, set()
                for (start, end, nn, shorthand) in rules_here:
                    # `NN` (backticked bare number) is genuinely ambiguous with a
                    # literal value — `16` as a configured depth read as "rules/16"
                    # and produced a false positive on correct prose. The explicit
                    # `rules/NN` form keeps a wide window; the shorthand must sit
                    # immediately before the §, which is the only way it is ever
                    # actually written (`(\`02\` §8)`).
                    near = ((0 <= m.start() - end <= (2 if shorthand else 120))
                            or (0 <= start - m.end() <= 40 and not shorthand))
                    if near:
                        hit = False
                        for sk in skills_here:
                            target = rules_file(sk, nn)
                            if target:
                                cands.add(target)
                                hit = True
                        # An explicit `rules/NN` that exists under NO skill named on
                        # the line and not under the containing skill is unambiguously
                        # broken — flag it even though section resolution is fail-open.
                        if not hit:
                            dangling.add(nn)
                if dangling:
                    findings.append(
                        '%s:%d: rules/%s cited beside §%s does not exist in %s '
                        'or any skill named on that line' %
                        (f, i, '/'.join(sorted(dangling)), sec, own))
                    continue
                if any(resolves(c, sec) for c in cands):
                    resolved += 1
                elif all(not idx[c][0] for c in cands):
                    pass                      # target numbers no sections at all
                else:
                    findings.append(
                        '%s:%d: §%s resolves nowhere (tried: %s) — name the skill '
                        'explicitly, or the section moved/was renumbered'
                        % (f, i, sec, ', '.join(sorted(c.split('/')[-1] for c in cands))))

    for line in findings:
        print(line)
    print('SCOPE %d' % resolved)
    return 1 if findings else 0


if __name__ == '__main__':
    sys.exit(main())
