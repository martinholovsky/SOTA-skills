#!/usr/bin/env python3
"""check-version-pins.py — find claims about what is CURRENT that carry a version number.

POLICY (operator decision 2026-09-25, CONTRIBUTING "No rot-prone version pins"): a statement of
what is current or latest must not carry a number ("the current release is 3.x", "Java 25 is the
current LTS", "iOS 26 current"). It is stale the day the next release ships and nothing reports
it. Versions stay only as SEMANTIC BOUNDARIES — feature availability ("since Go 1.24"), fix floors
("fixed in 1.81.0"), removals ("removed in .NET 9"), API eras ("React 19 Server Components") — and
a claim carrying an ISO date ("verified 2026-07-09", "as of 2026-06") is dated provenance, not a pin.

WHY IT IS BUILT THIS WAY. The first version was a list of regexes patched after every miss (bold
markers, wrapped lines, runs of whitespace, exemptions) — four fix-and-rerun rounds in one hour.
This one is built the other way round:
  1. a LABELLED CORPUS (positives in every shape seen in the tree, negatives that share the
     vocabulary) is the specification, and `--self-test` fails if any label is misclassified;
  2. text is NORMALISED ONCE — fenced code dropped, emphasis/code/links stripped, wrapped lines
     joined into paragraphs, whitespace collapsed, then split into clauses — so formatting can
     never hide a match again;
  3. each clause is CLASSIFIED by independent cues, not by one pattern per phrasing:
       pin  =  currency cue  AND  a version token not governed by a boundary cue
               AND no ISO date in the clause
     plus two cue-only pins: a year "baseline" label, and "at the time of writing" + a version.
Invariant 37's lesson applies too: the self-test is the positive control, and it runs before
every scan, so a regression in the detector fails the gate instead of reading as a clean tree.

Usage:  check-version-pins.py --self-test
        check-version-pins.py FILE...     (prints "path:line: clause"; exit 1 if any pin)
"""
import re
import sys

# ---------------------------------------------------------------- normalisation
FENCE = re.compile(r'^\s*(```|~~~)')
LINK = re.compile(r'\[([^\]]*)\]\([^)]*\)')
EMPH = re.compile(r'(\*\*|__|\*|`)')
BLOCK_START = re.compile(r'^\s*([-*+]\s|\d+[.)]\s|#{1,6}\s|\||>\s?|- \[[ x]\])')


def paragraphs(text):
    """Yield (first_line_number, joined_text). Fenced code is skipped (a pin inside a config
    example is data, not a claim). A list item, heading or table row starts a new unit."""
    unit, start, in_fence = [], None, False
    for i, raw in enumerate(text.split('\n'), 1):
        if FENCE.match(raw):
            in_fence = not in_fence
            if unit:
                yield start, ' '.join(unit)
                unit, start = [], None
            continue
        if in_fence:
            continue
        if not raw.strip() or BLOCK_START.match(raw) or raw.lstrip().startswith('|'):
            if unit:
                yield start, ' '.join(unit)
            unit, start = [], None
            if not raw.strip():
                continue
        if start is None:
            start = i
        unit.append(raw.strip())
    if unit:
        yield start, ' '.join(unit)


def normalise(s):
    s = LINK.sub(r'\1', s)
    s = re.sub(r'https?://\S+', ' ', s)                 # a version inside a URL is not a claim
    s = re.sub(r'^\s*#{1,6}\s+[\d.]+\s', ' ', s)          # heading section numbers ("## 8.8 …")
    s = EMPH.sub('', s)
    s = re.sub(r'<!--.*?-->', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


# unit split: sentences only. Splitting at ';', a dash or a table bar separated a claim from its
# version ("spec v1.0.0 — still the current version"; "| 7.5 | … | current Stable |").
CLAUSE = re.compile(r'(?<=[.!?])\s+(?=[A-Z(`])')

# ---------------------------------------------------------------- cues
PRODUCT = (r'(?:Go|Java|JDK|Kotlin|\.NET|C#|PHP|Ruby|Python|Node(?:\.js)?|TypeScript|Rust|'
           r'Swift|Xcode|iOS|iPadOS|macOS|Android|Chromium|Chrome|Safari|Firefox|Kubernetes|K8s|'
           r'PostgreSQL|Postgres|bash|zsh|PowerShell|Kafka|Delta Lake|Spring Boot|Rails|Django|'
           r'React|Vue|Nuxt|Next\.js|OpenSSL|Argo CD|Kyverno|Gatekeeper|Harbor|Airflow|DuckDB|Debezium)')
# a version: v-prefixed, dotted, or N.x — never a section/criterion number, never a quantity
VERSION = re.compile(
    r'(?<![\w.§/-])(?<!§ )(?<!\bsections )(?<!\bsection )(?<!\bWCAG )(?<!\bSC )(?<!\bASVS )'
    r'(v\d+(?:\.\d+)*(?:\.x)?\+?|\d+\.(?:\d+|x)(?:\.(?:\d+|x))*\+?)'
    r'(?![\w%]|\s?(?:ms|s|GB|MB|KB|TB|x|×|%|px|em|rem|days?|hours?|min)\b)')
PRODUCT_NUM = re.compile(r'\b' + PRODUCT + r'\s?(\d{1,3})(?![\w.])')
GLUED = re.compile(r'\b(?:net|netcoreapp|netstandard|py|node|jdk)(\d+(?:\.\d+)*)\b', re.I)
EDITION = re.compile(r'\bedition\s*=?\s*"?(20\d\d)\b', re.I)
REVISION = re.compile(r'\bRev(?:ision)?\.?\s?(\d+(?:\.\d+)*)\b')   # spec revisions: "Revision 3", "Rev 5"

REL = (r'(?:releases?|versions?|line|stable|LTS|major|minor|edition|spec(?:ification)?|standard|'
       r'baseline|revision|generation|train|SDK|toolchain|JDKs?|verdict|authoritative)')
CURRENCY = re.compile(
    r'\b(?:current(?:ly)?|latest|newest)\s+(?:[\w.-]+\s+){0,3}?' + REL + r'\b'   # "current stable line"
    r'|\b(?:is|are)\s+(?:now\s+|still\s+)?(?:the\s+)?(?:current|latest)\b'       # "4.x is current"
    r'|\d(?:\.[\dx]+)*\+?\s+(?:is\s+)?current\b'                                  # "iOS 26 current", "5.x current"
    r'|\bcurrent(?:ly)?\s+(?:on|at)\b'                                            # "currently on 2.x"
    r'|\bcurrent\s+v?\d+\.[\dx]'                                                  # "current v2.15.x"
    r'|\bas\s+of\s+(?:(?:mid|early|late)[- ]?)?20\d\d(?![-\d])'                   # vague date
    r'|\bat\s+(?:the\s+time\s+of\s+)?writing\b'
    r'|\bon\s+the\s+\S+\s+line\b|\brelease\s+train\b|\bproduction-ready\s+on\b',
    re.I)
CURRENCY_FALSE = re.compile(
    r'\bBest\s+Current\s+Practice\b|\bthen-current\b|\bcurrent-thread\b|:latest\b|\blatest\s+tag\b'
    r'|\bBaseline\s+Requirements\b|\ban?\s+(?:newest|latest)\b', re.I)
BASELINE_LABEL = re.compile(
    r'(?:^|[(\s])Baseline(?:\s+(?:assumptions|language\s+version))?\s*(?::|as\s+of)'
    r'|\bBaseline\s+' + PRODUCT + r'\s*\d'
    r'|\b(?:(?:mid|early|late)[- ]?)?20\d\d\s+baseline\b')
BOUNDARY_BEFORE = re.compile(
    r'(?:\bsince|\bfixed\s+in|\badded\s+in|\bintroduced\s+in|\bremoved\s+in|\bdeprecated\s+in|'
    r'\bfrom|\buntil|\bbefore|\bprior\s+to|\bafter|\bthrough|\bup\s+to|\bat|\bat\s+least|'
    r'\bminimum|\bfloor|\brequires?|\bneeds?|\bbelow|\babove|\bolder\s+than|\bnewer\s+than|'
    r'\breached|\bbecame|\bfirst\s+support\w*|\bin|≥|>=|<=|<|>|\^)\s*(?:[\w.#-]+\s+){0,2}$', re.I)
BOUNDARY_AFTER = re.compile(
    r'^\+?\s*(?:[\w.-]+\s+)?(?:added|removed|introduced|deprecated|fixed|shipped|dropped|'
    r'made|changed|renamed|flipped|released|first\s+support\w*|or\s+later|or\s+newer|and\s+later|and\s+up|onwards?)\b', re.I)
SUBCLAUSE = re.compile(r',\s+(?:but|and|while|which|whereas|although|though)\b')  # not ';' (see CLAUSE)
# Provenance dates a claim. It exempts only the version/cue pair it sits beside (or a whole
# unit when it opens it, "Verified (2026-07-09): ..."), because one dated observation must not
# shield an undated pin later in the sentence. A bare ISO date is provenance unless an EVENT word
# introduces it: "v1.33 reached EOL ~2026-06" dates the EOL, not the claim beside it.
PROVENANCE = re.compile(
    r'\bas\s+of\s+20\d\d-\d\d(?:-\d\d)?\b|\b(?:measured|verified|re-?checked|fetched)\b'
    r'|\bas\s+of\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+(?:\d{1,2},?\s+)?20\d\d', re.I)
ISO_DATE = re.compile(r'\b20\d\d-\d\d(?:-\d\d)?\b')
EVENT_BEFORE_DATE = re.compile(
    r'(?:\bEOL|\bend[- ]of[- ](?:life|support)|\breleased|\breached|\bshipped|\buntil|\bsince|'
    r'\bfrom|\bbefore|\bafter|\bby|\bdeadline|\bscheduled|\bdue|\bplanned|\bends?|\bexpires?|'
    r'\bretire[sd]?|\bGA|\bbecomes?)\b[^.;]{0,20}$', re.I)


def provenance_spans(c):
    spans = [(m.start(), m.end()) for m in PROVENANCE.finditer(c)]
    spans += [(m.start(), m.end()) for m in ISO_DATE.finditer(c)
              if not EVENT_BEFORE_DATE.search(c[max(0, m.start() - 30):m.start()])]
    return spans


def versions(clause):
    out = [(m.start(1), m.end(1)) for m in VERSION.finditer(clause)]
    out += [(m.start(1), m.end(1)) for m in PRODUCT_NUM.finditer(clause)]
    out += [(m.start(1), m.end(1)) for m in GLUED.finditer(clause)]
    out += [(m.start(1), m.end(1)) for m in EDITION.finditer(clause)]
    out += [(m.start(1), m.end(1)) for m in REVISION.finditer(clause)]
    return out


def governed(clause, start, end, cues=()):
    """A version is a boundary when a boundary cue sits right before or right after it, or it
    carries a '+' (\"13+\" = 13 or later). A boundary word that is part of a currency cue does
    not count: in "currently at 8.30" the "at" is the claim about now, not a floor."""
    if clause[end - 1:end] == '+' or clause[end:end + 1] == '+':
        # "13+" is a floor — unless a currency cue follows at once ("1.0+ as of mid-2026")
        if not re.match(r'\+?\s*(?:as\s+of|is\s+current|current)\b', clause[end:end + 20], re.I):
            return True
    lo = max(0, start - 40)
    b = BOUNDARY_BEFORE.search(clause[lo:start])
    if b and any(m.start() <= lo + b.start() < m.end() for m in cues):
        b = None
    return bool(b or BOUNDARY_AFTER.search(clause[end:end + 40]))


def is_pin(clause):
    c = normalise(clause)
    prov = provenance_spans(c)
    if any(s < 30 for s, _ in prov):          # "Verified (2026-07-09): ..." dates the whole unit
        return False
    c = CURRENCY_FALSE.sub(' ', c)
    if BASELINE_LABEL.search(c):
        return bool(versions(c)) or bool(re.search(r'20\d\d\s+baseline', c, re.I))
    cues = list(CURRENCY.finditer(c))
    if not cues:
        return False
    vs = versions(c)
    if any(governed(c, s, e, cues) for s, e in vs):
        # "needs >=1.26.5 on the 1.26 line": a per-line floor, not a claim about now
        cues = [m for m in cues if not re.match(r'on\s+the\s', m.group(0), re.I)]
    # The version must sit near the cue AND in the same sub-clause: "(D)TLS 1.3 (…), but as of
    # mid-2026 no standard is published" puts a protocol name 50 chars from a vague date.
    NEAR = 60
    def linked(s, m):
        lo, hi = min(s, m.start()), max(s, m.end())
        return hi - lo <= NEAR + (m.end() - m.start()) and not SUBCLAUSE.search(c[lo:hi])
    def dated(s, m):                          # a provenance marker beside this pair dates it
        lo, hi = min(s, m.start()), max(s, m.end())
        return any(ps < hi + 40 and pe > lo - 40 for ps, pe in prov)
    return any(not governed(c, s, e, cues) and any(linked(s, m) and not dated(s, m) for m in cues)
               for s, e in vs)


def scan(path):
    text = open(path, encoding='utf-8').read()
    hits = []
    for line, para in paragraphs(text):
        for clause in units(para):
            if is_pin(clause):
                hits.append((line, clause.strip()))
                break
    return hits


def units(para):
    """Sentences; a table row becomes each cell paired with its first cell, so a label cell
    (\"current Stable\") keeps its version (\"PowerShell 7.5\") and a long cell is not merged
    with its neighbours."""
    if para.lstrip().startswith('|'):
        cells = [normalise(c) for c in para.strip().strip('|').split('|')]
        cells = [c for c in cells if c and not set(c) <= set('-: ')]
        if not cells:
            return []
        out = []
        for cell in cells[1:] or cells[:1]:
            for sent in CLAUSE.split(cell):
                out.append(cells[0] + ' ' + sent)
        return out
    return CLAUSE.split(normalise(para))


# ---------------------------------------------------------------- labelled corpus
# Every positive shape seen in the tree on 2026-09-25, plus the pins the sweep reports named
# that the first detector missed; every negative is a real sentence (or a near-miss built from
# one) that shares the vocabulary. Add a line here BEFORE changing a pattern.
PINS = [
    "State-of-the-art C and C++ engineering rules (2026 baseline) that Claude applies",
    "Baseline Java 25 LTS (virtual threads final since 21; structured concurrency still preview), Kotlin 2.x.",
    "New projects: target the latest LTS (Java 25 at the time of writing; verify at the Oracle roadmap)",
    "target the latest LTS TFM (`net10.0` at the time of writing; verify at the .NET support policy page)",
    "Verify the current version at attack.mitre.org — as of\n  mid-2026 the current Enterprise release is **v19** (April 2026)",
    "as of mid-2026 it is on the 1.x line, ~1.8 stable with 1.9 in development",
    "Current line is v0.x (verify at falco.io)",
    "(Kafka 4.x is current — ZooKeeper is gone, KRaft-only)",
    "**Delta Lake 4.x** is current (variant type, collations)",
    "Current stable line is **3.x** (verify the current release when you pin)",
    "Current line ~v1.18 (verify).",
    "Current edition as of mid-2026; new code starts here (`edition = \"2024\"`)",
    "SSDF version referenced is the current final (v1.1 / SP 800-218)",
    "Current as of mid-2026: ShellCheck v0.11.0 (Aug 2025), shfmt v3.13.x",
    "CVSS v4.0 (the current spec, 2023) replaced temporal metrics",
    "| iOS | iOS 26 current (26.5.x); iOS 27 announced at WWDC |",
    "Bash-focused (bash 5.x current; macOS ships bash 3.2 and defaults to zsh)",
    "now a Linux Foundation project with an active 2.x release train",
    "Production-ready on the v1.x line (Tetragon)",
    "the current release is 2.7.0",
    "Tokio remains 1.x (1.52 as of mid-2026)",
    "**Zot** (user's choice; current line **v2.1.x**, e.g. v2.1.14 Jan 2026)",
    "The rules/ files define the mid-2026 baseline for engineering LLM-powered software",
    "Modern Python (2026 baseline): uv for everything",
    "PER-CS 2.x current",
    "Vitest (v4 current)",
    "OWASP CRS current line 4.x (4.25 is the first CRS-4 LTS)",
    # added after the first library-wide run (2026-09-25): real lines it missed
    "Conventional Commits (conventionalcommits.org, spec v1.0.0 — still the current version as of 2026)",
    "| PowerShell 7.5 | 23-Jan-2025 | 10-Nov-2026 | current Stable |",
    "Baseline: .NET 10 LTS (released Nov 2025, supported to Nov 2028) and C# 14",
    "Baseline: Next.js 16.x (App Router).",
    "Baseline as of mid-2026: a recent stable Rust toolchain, edition 2024",
    "(Verify current numbers at kubernetes.io/releases — at writing latest is the 1.36 line; 1.34/1.35/1.36 supported.)",
    "Current Argo CD line is ~3.4.x (verify).",
    "Harbor (current v2.15.x, Mar 2026): projects + robot accounts + RBAC",
    "Log-based CDC (Debezium-class, 3.x current) is the default",
    "DuckDB (1.5.x as of mid-2026) or Polars on one machine outperforms a Spark cluster",
    "MASVS v2.1 current (adds MASVS-PRIVACY)",
    "dbt note: the Fusion engine is in preview and dbt Core 2.0, built on the Fusion foundation, is in alpha as of mid-2026.",
    "DuckLake (1.0+ as of mid-2026) is viable for DuckDB-centric small platforms",
    "The current authoritative reference is NIST SP 800-61 Revision 3 (finalized April 2025), which replaced the four-phase model.",
    # a fix agent's probe, 2026-09-26: "at" is both the currency cue and a boundary word
    "gitleaks is currently at v8.30.1 (the latest release).",
    "The scanner is currently at 8.30.1.",
    # a research agent, 2026-09-26: an EVENT date (EOL) is not provenance for the pin beside it
    "(Current upstream: v1.36, supported window v1.34–v1.36 as of mid-2026 — the latest three minors; v1.33 reached EOL ~2026-06; verify your managed-provider version offerings at design time.)",
    # 2026-09-26: a bare date shielded these (an until/EOL date, or a dated observation beside an undated pin)
    'React ≥ 19.x, Next ≥ 15.x (16.x current), Vue ≥ 3.5, Nuxt ≥ 4.x (Nuxt 3 security-only until 2026-07-31).',
    'ES2024+ available, React 19.2-era with Server Components and React Compiler 1.0 where relevant, latest stable Vitest + flat-config ESLint (v9/v10).',
    'Frame against the CIS Kubernetes Benchmark (CIS listed v2.0.1 as latest on 2026-09-25; use the edition matched to your minor version) and the NSA/CISA Kubernetes Hardening Guidance (v1.2, Aug 2022 — still the current edition; verify before citing).',
]
NOT_PINS = [
    "latest stable (verify at go.dev/doc/devel/release)",
    "Target the latest LTS (verify at the Oracle Java SE support roadmap).",
    "os.Root is available since Go 1.24.",
    "MSRV ≥ 1.81.0 for anything that may run on Windows (CVE-2024-43402 fixed in 1.81.0).",
    "BinaryFormatter was removed in .NET 9.",
    "React 19 Server Components run on the server.",
    "GA since 1.27; experiment-only in 1.26.",
    "Verified (2026-07-09): OWASP CRS current line 4.x (4.25 is the first CRS-4 LTS)",
    "The matrix below was verified current as of 2026-06; tools rename, fork, and die.",
    "Kubernetes 1.34 was fetched as latest on 2026-09-25; use the edition matched to your minor version",
    "Concurrent duplicate while first is in flight: 409 (or block).",
    "A 200ms synchronous task means every concurrent request waits 200ms.",
    "floor and current — a ^8.2 constraint tested only on 8.5 misses breaks",
    "Reinforces the keep-the-toolchain-current rule in rules/08 §1.",
    "noncurrent_version_expiration { noncurrent_days = 90 }",
    "Pin the current patch from go.dev/doc/devel/release.",
    "The current directory is searched when no path is given.",
    "Check the current state with kubectl get pods.",
    "the latest point release of your branch fixes it (verify at php.net/releases)",
    "JUnit 6 requires Java 17+.",
    "a 1.5x speedup on the current workload",
    "Upgrade to 2.3.6 or later.",
    "Swift 6 language mode enforces data-race safety.",
    "Node 26 becomes LTS on 2026-10-28.",
    "requires kernel 6.3 or newer and runc 1.2+",
    "Supported until 2027: PHP 8.4 security fixes (php.net, dated table).",
    "View transitions are Baseline 2024 (widely available).",
    "argon2id baseline parameters: memory at least 64 MiB, t=3, p=4 (OWASP Password Storage cheat sheet).",
    "Pin with a tilde range such as tokio = \"~1.51\" to stay on an LTS line.",
    # real lines the first library-wide run wrongly flagged (2026-09-25)
    "They conflict with the baseline above: GCC 16.2 refused -mindirect-branch=thunk beside -fcf-protection=full",
    "§3.7 keeps dependencies current.",
    "Keep workflow SAST current, or its new detections never run; zizmor adds audits in minor releases.",
    "Deploy by digest (rules/06 §6.6, rules/07 §7.1): manifests reference image@sha256; tags are for humans. :latest is never a pin.",
    "Harbor v2.15 added tag-deletion options in GC (verified-current).",
    "Patched in the then-current 3.2.x/3.3.x patch releases; upgrade.",
    "The textbook ReDoS no longer reproduces on current JDKs: measured on Temurin 21.0.12 and 25.0.4.",
    "Measured with tsc 6.0.3 and 7.0.2: this baseline without its types line failed on process.",
    "Pin the image version to production's version. postgres:latest in tests + Postgres 14 in prod = testing a different engine.",
    "Any FROM on a moving tag (latest, rawhide, stable, a bare major) is pinned only by the cache.",
    "Public CAs may not issue for unqualified names (CA/B Baseline Requirements sections 4.2.2 and 7.1.2.7.12).",
    "Split out of rules/01 at v1.37.0, which keeps the safety baseline.",
    "Re-baseline only through review, never auto-accept (rules/02 §2.8 applies).",
    "Always compare to a baseline: a trivial predictor (majority class, last value, simple heuristic) and the current production model.",
    "YARA-X is the Rust rewrite and the current standard: it reached 1.0 stable (June 2025).",
    "Measured on tokio 1.53.1 and a current-thread runtime: a task stored tenant-A in a thread_local!.",
    "autocomplete tokens per WCAG 1.3.5 (required at AA for user-data fields).",
    "Status (verified July 2026): NIST Cybersecurity Framework 2.0 (CSWP 29) was published 26 Feb 2024.",
    "The OAuth 2.0 Security Best Current Practice, RFC 9700, requires PKCE.",
    "sota-code-security rules/11 §2.2: the same gate's green today does not cover the scope it had.",
    "## 8.8 Product notes (brief — verify current at use)",
    "go version (os.Root containment needs >=1.26.5 on the 1.26 line — CVE-2026-39822 symlink escape)",
    "use a golangci-lint release whose notes list your Go minor (v2.9.0 first supported 1.26, v2.13.0 first supports 1.27)",
    "Compare the running php -v with the newest release of its branch (https://www.php.net/releases/?json&version=8.4 returns it).",
    "Current verdict mechanics: MEETS_STRONG_INTEGRITY requires hardware-backed signals and a recent security patch (on Android 13+, patched within a year).",
    "iOS: built with the currently required SDK (iOS 26 SDK as of Apr 28, 2026).",
    "The IETF has chartered the SEAT working group to standardize attestation in (D)TLS 1.3 (successor to the individual draft line), but as of mid-2026 no standard is published.",
    "| rules/04-security.md | Java deserialization (Jackson 2 and 3 spellings); the Security Manager is gone (removed in JDK 24) and on current JDKs ReDoS no longer reproduces. |",
    "use a golangci-lint release whose notes list your Go minor (v2.9.0 first supported 1.26, v2.13.0 first supports 1.27; take the latest stable and check its release notes)",
    # 2026-09-26: dated observations and release events; a generic "a newest release"
    'Frame against the CIS Kubernetes Benchmark (CIS listed v2.0.1 as latest on 2026-09-25; use the edition matched to your minor version).',
    'Baseline language line: Ruby 3.4+; Ruby 4.0 was released 2025-12-25 and is in normal maintenance (latest stable — verify at the branches page).',
    '4.0 released 2025-12-25; for the latest stable release, verify at the branches page',
    '| PowerShell 7.6 (LTS) | 18-Mar-2026 | **14-Nov-2028** | LTS, newest at the 2026-09-14 check; prefer the newest supported LTS for new work |',
    'A newest release can be a tombstone: bincode 3.0.0 is one compile_error! line, and RUSTSEC-2025-0141 (2025-12-16, informational: unmaintained) records that its development has stopped for good.',
]


def self_test():
    bad = [('missed pin', s) for s in PINS if not any(is_pin(c) for c in units(s))]
    bad += [('false pin', s) for s in NOT_PINS if any(is_pin(c) for c in units(s))]
    for kind, s in bad:
        print("SELF-TEST %s: %s" % (kind, s[:100]))
    print("SELF-TEST %d/%d pins, %d/%d non-pins correct"
          % (len(PINS) - sum(k == 'missed pin' for k, _ in bad), len(PINS),
             len(NOT_PINS) - sum(k == 'false pin' for k, _ in bad), len(NOT_PINS)))
    return 1 if bad else 0


if __name__ == '__main__':
    if sys.argv[1:] == ['--self-test']:
        sys.exit(self_test())
    rc = 0
    for f in sys.argv[1:]:
        for line, clause in scan(f):
            rc = 1
            print("%s:%d: %s" % (f, line, clause[:160]))
    sys.exit(rc)
