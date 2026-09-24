#!/usr/bin/env python3
"""Concept x language matrix: which audit CONCEPTS each language skill actually probes.

WHY THIS EXISTS, and what it can see that page 5 of the skill map cannot. `gen-skill-map.py`
maps topic x language at FILE granularity, which is how ROADMAP 57 (a missing API/design
file) was found. It is structurally blind to a concept that is missing *inside* a file that
exists: on 2026-09-21 `sota-shell-scripting` rules/07 (PowerShell) carried the `$?`-is-
volatile rule with an audit probe while the bash half carried neither, and both skills
"have" their files, so no file-level matrix could ever have reported it.

THE HONEST LIMIT, stated before the output is read. This classifies by declared matchers
over item text. A matcher answers "does this wording appear", never "is this idea covered"
-- the same gap `sota/rules/01` warns about. So:

  * every run prints its DENOMINATOR: items classified / items total, per skill;
  * every unmatched item is LISTED, not silently dropped, because an item this file cannot
    classify is a hole in the vocabulary and the only way to find it is to print it;
  * a PRESENT cell is a claim too: `--explain CONCEPT LANG` prints the items behind it and
    the substring each matched, and `--explain all all` does it for every present cell. A
    cell lit by `slog` inside `syslog` hides an absence no candidate row can show;
  * a concept's absence from a language is a CANDIDATE, never a finding. Confirm by opening
    the file -- 2 of 8 candidate Python gaps died on reading during ROADMAP 59's first pass.
  * EVERY absence of a universal concept is listed, in one of two blocks: CANDIDATE GAPS
    (missing in 1-5 languages) and MOSTLY ABSENT (missing in 6-9). The second block exists
    because the first one alone hid `numeric precision & money` at 3/9 for a whole pass
    (ROADMAP 65): a threshold with no recorded rationale made the widest absences the
    invisible ones. A concept missing almost everywhere is either a class-wide gap or not
    universal after all -- triage decides which, and it cannot decide what it is not shown.

Presence, not counts. The two checklist body formats are not comparable by volume (a
checkbox bundles several commands; a fence counts per line -- see gen-skill-map.py's
audit_items docstring), but "does this skill probe concept X at all" is format-agnostic,
which is exactly why this asks presence.

`sota-shell-scripting` is reported as its OWN group, never as a tenth language column:
LANGUAGE-TIER.md is explicit that it is not a peer of the tier. Mixing the two spines would
manufacture gaps that are only a difference in kind.
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import extract_items as E  # noqa: E402

# --- the concept vocabulary -------------------------------------------------------
#
# (concept, universality, pattern). `universality`:
#   "universal"  -- every language in the tier should probe this; a blank cell is a
#                   candidate gap worth opening the file for.
#   "conditional"-- only applies where the language has the feature. A blank cell is
#                   expected for languages without it and is NOT a gap. The reason is
#                   recorded so a later reader does not "fix" a principled difference.
#
# Adding a concept? Put the pattern in the corpus's OWN vocabulary, not yours: read a
# neighbouring skill's headings first. A matcher written from memory reports a false
# absence, which is the failure this file is most likely to produce.
#
# ...and the second failure: a FALSE PRESENCE. A bare substring lights a cell from a word
# that is not the concept, and a present cell hides the absence it stands on -- no candidate
# row can ever show it. The fourth pass (2026-09-24) printed the substring behind every
# present cell (`--explain all all`) and tightened what it found: `slog` in `syslog`,
# `import` in `DllImport` and in `python3 -c "import json"`, `n+1` in `n=$((n+1))`, `clock`
# in "a wall-clock bound", `null` in `/dev/null`, `lock` in lockfile/blocking/`uv.lock`,
# `safety` in rust's `// SAFETY:` (vulnerability scanning, a PINNED concept, was 9/9 on that
# and on c/c++'s "safety-standard analysis"), `currency` in "concurrency", `lts` in
# "results"/"defaults", `validat` in "iterator invalidation", `sanitiz` in `-fsanitize`, `rsa` in "traversal", `erb` in "verbose", `sanitiz` in "sanitizer", `leak` in
# "leaked secrets", `provenance` in "size provenance", `measure` in "measured on". Hence
# the `\b`s, lookbehinds and narrowed phrases below. Adding a pattern? Run
# `--explain all all` before and after and read every substring your change adds.
CONCEPTS = [
    # --- language baseline / API surface
    ("error handling & propagation", "universal",
     r"error handl|wrap(ped|ping)? error|error type|swallow|empty catch|catch \(|"
     r"\brescue\b|on_error|error code|errors\.(is|as)|unwrap|expect\(|panic"),
    ("absence / null / in-band sentinel", "universal",
     r"in-band|sentinel|(?<!/dev/)null|\bnil\b|\bnone\b|optional|nullable|"
     r"(?<!head )(?<!tail )(?<![\w-])-1\b|magic (number|value)|truthiness"),
    ("public API surface & evolution", "universal",
     r"public (api|surface)|semver|breaking change|deprecat|__all__|\babi\b|"
     r"\bexport|visibility|private_constant|readonly|\bfinal\b|"
     # go states this in Go-native terms and was reported absent for it (triage
     # 2026-09-21: 02-design.md probes grab-bag packages, returned interfaces, fat
     # interfaces and package-level mutable state).
     r"fat interface|returned interface|grab[- ]bag|package-level|interface \{"),
    ("immutability / const discipline", "conditional:has a const or freeze mechanism",
     r"immutab|const\b|constexpr|readonly|frozen|freeze|final field|mutat|defensive copy"),
    ("typing / generics discipline", "conditional:gradual or explicit typing",
     r"type hint|typing|mypy|generic|any\b|unknown\b|strict(ness)?|nullable ref|rbs|sorbet"),

    # --- concurrency
    ("data race / shared mutable state", "universal",
     r"data race|race condition|shared mutab|thread[- ]safe|goroutine|gvl|ractor|"
     r"send\b.*sync|atomic|mutex|synchroniz|inside lock|lock\s*\(|lock\\s\*\\\(|session lock|"
     r"threading\.(r?lock|thread)|free[- ]threaded|nogil|check-then-act"),
    ("cancellation / timeouts", "universal",
     r"cancel|timeout|deadline|context\.|ctx\b|abortcontroller|cancellationtoken|"
     r"stop_token|jthread"),
    ("task / thread leaks", "universal",
     r"(task|thread|goroutine|coroutine|timer|unstructured) leak|leak detection|goleak|"
     r"clearinterval|orphan|detached task|fire[- ]and[- ]forget|unawaited|background task|"
     r"unjoined|thread\.new|async void|task\.run"),
    ("blocking the event loop / executor", "conditional:has an event loop or async runtime",
     r"event loop|blocking (call|io|the)|block_on|run_until|sync over async|\.result\(\)|"
     r"configureawait|deadlock|sync\(|scryptsync"),
    ("backpressure / unbounded queues", "universal",
     r"unbounded (queue|channel|fan-out|parallelism|concurren)|parallelism unbounded|"
     r"backpressure|bounded (queue|channel)|buffer size|queue depth|executors\.new|"
     r"linkedblockingqueue|sizedqueue|semaphore"),

    # --- memory / resources
    ("resource lifecycle (close/dispose/RAII)", "universal",
     r"raii|dispose|close\(|\bdefer |using \(|using var\b|await using|with open|"
     r"context manager|finaliz|file handle|connection (leak|pool)|`ensure`|ensure (block|clause)|"
     r"block form|impl drop|mem::forget|"
     r"session_write_close"),
    ("memory safety (bounds, UAF, overflow)", "conditional:manual memory management",
     r"use[- ]after[- ]free|buffer overflow|bounds|out of bounds|dangling pointer|"
     r"double free|integer overflow|sanitizer|asan|ubsan|valgrind|miri|allocunsafe"),

    # --- security
    ("SQL / query injection", "universal",
     r"sql inject|parameteriz|prepare|raw quer|sql built from|string interpolation in (a )?quer|"
     r"activerecord|sqlalchemy|dapper|pdo|whereraw|selectraw|db::raw|escape_string|"
     r"emulate_prepares|->query|execute\(|sqlx|diesel|knex|sequelize|query buil|"
     r"sql built as|sqlite3_exec|\(select\|insert"),
    ("command / subprocess injection", "universal",
     r"command inject|shell[= ]true|os/exec|subprocess|system\(|popen|`backtick|"
     r"process\.start|processbuilder|std::process|argument injection|child_process|"
     r"execsync|spawnsync|execfile|runtime\.getruntime|shell_exec|proc_open"),
    ("path traversal / file access", "universal",
     r"path traversal|\.\./|directory traversal|os\.root|filepath\.(join|clean)|"
     r"realpath|symlink|temp file|tmpfile|file permission|0600|umask|path\.join|"
     r"canonical|basename|lfi\b|include\(|require_once|mktemp|tempfile|"
     r"path\.combine|getfullpath|zip slip|zipentry|sendfile"),
    ("deserialization / unsafe parsing", "universal",
     r"deserializ|unserialize|pickle|marshal|yaml\.load|objectinputstream|binaryformatter|"
     r"gob\b|xxe|xml external|phar|serde|bincode|json\.loads|fromjson|readobject|xslt|"
     r"stylesheet|js-yaml|safeload|yaml loader"),
    ("output encoding / XSS / templating", "conditional:renders markup or templates",
     r"xss|(?<!exception-)escap(?!e hatch)|html_safe|htmlspecialchars|dangerouslysetinnerhtml|innerhtml|"
     r"autoescap|\berb\b|template inject|(?<![-f])sanitiz(e|ed|es|ing|ation)\b"),
    ("cryptography & randomness", "universal",
     r"crypto|cipher|\baes\b|\brsa\b|\bhash(ing)?\b|bcrypt|argon2|pbkdf2|md5|sha1\b|"
     r"csprng|secure random|\brand\b|nonce|\biv\b|constant[- ]time"),
    ("secrets handling", "universal",
     r"secret|credential|api key|password|token\b|\.env\b|hardcoded|vault|keyring"),
    ("input validation & untrusted data", "universal",
     r"(?<!in)validat|untrusted|maxbytesreader|disallowunknownfields|(?<![-f])sanitiz(e|ed|es|ing|ation)\b|allowlist|whitelist|bounds check|schema|"
     r"decompress|zip bomb|size limit|max size"),
    # Reclassified 2026-09-22 by triage. Router cross-cutting rule 18 puts transport/PKI
    # in `sota-network-security` rules/06 and TLS *client config* in `sota-code-security`
    # rules/04, library-wide. So a language skill with no TLS probe is DELEGATING, not
    # gapped -- rust, js/ts and c/c++ were being reported as gaps for obeying the router.
    ("TLS / transport verification", "conditional:transport/PKI is delegated library-wide (router rule 18)",
     r"\btls|\bssl|certificate|insecureskipverify|verify=false|hostname verif|"
     r"insecureignorehostkey|trust ?store|http://|rustls|openssl|danger_accept|"
     r"servercertificatevalidation|curlopt_ssl"),
    ("authn / authz checks", "universal",
     r"authoriz|authenticat|permission check|idor|access control|jwt|oauth|csrf|"
     r"session (fixation|cookie|id|hijack|regenerat|lock|token|storage|expir)|session_|"
     r"cookie|samesite|httponly|privilege drop|relinquish"),
    ("logging hygiene / PII in logs", "universal",
     r"log(ging|s)? (secret|pii|token|password)|redact|structured log|\bslog\b|"
     r"sensitive data in|stack trace (in|to) (the )?(response|user)|authorization`/`cookie|"
     # Third pass, 2026-09-24: php already probed secrets in stack traces via
     # `#[\SensitiveParameter]` (an artefact), and the probes closed that pass are titled
     # "Secrets reaching logs" / "Log injection".
     r"secrets reaching (logs|traces)|log injection|sensitiveparameter|"
     r"filter_parameters|enablesensitivedatalogging"),

    # --- supply chain / tooling
    ("dependency pinning & lockfiles", "universal",
     r"lockfile|lock file|go\.sum|cargo\.lock|package-lock|poetry\.lock|gemfile\.lock|"
     r"pinned|pin\b|checksum|integrity hash|packages\.lock\.json"),
    ("vulnerability scanning of dependencies", "universal",
     r"govulncheck|cargo audit|pip-audit|npm audit|bundler-audit|dependency-check|"
     r"\bosv|advisory|\bcve\b|dependabot|renovate|safety (check|scan)|audit --locked|"
     r"composer audit|nugetaudit|dotnet list package --vulnerable"),
    ("static analysis / linter configuration", "universal",
     r"clippy|golangci|ruff|mypy|eslint|rubocop|phpstan|psalm|clang-tidy|cppcheck|"
     r"spotbugs|analyzer|lint|detekt|ktlint|brakeman|bandit|gosec|semgrep"),
    ("build reproducibility & CI gates", "universal",
     r"\bci\b|github actions|workflow|pipeline|reproducib|build flag|hardening flag|"
     r"-d_fortify|relro|stack protector|csproj|gradle|maven|cmake"),
    ("supply-chain provenance & publishing", "universal",
     r"(?<!size )(?<!path )provenance(?! loss)|slsa|sigstore|cosign|sbom|registry|typosquat|"
     r"publish(?!ed (package|librar))(?! a second)(?!aot|trimmed)|gosumdb|gonosumdb|go mod verify|"
     r"(package|registry|vendor|org) namespace|namespace (squat|reserv|prefix)|"
     r"dependency confusion|crates\.io|npmjs|pypi|rubygems|nuget|checksum|verification-metadata|"
     r"cyclonedx"),

    # --- testing
    ("test suite health & determinism", "universal",
     r"flaky|determinis|test (suite|coverage)|coverage|assert|table[- ]driven|"
     r"(?<![\w-])-race\b|\bctest\b|nextest|pytest|vitest|junit|\brspec\b|minitest|xunit|phpunit"),
    ("property-based / fuzz testing", "conditional:a fuzzing or property library exists",
     r"fuzz|property[- ]based|quickcheck|proptest|hypothesis|afl|libfuzzer|go-fuzz"),

    # --- performance
    ("profiling before optimizing", "universal",
     r"profil|pprof|flamegraph|benchmark|\bbench\b|jmh|criterion|\bperf\b|measure(?!d on)"),
    ("allocation / GC pressure", "universal",
     r"alloc(?!unsafe)|unbounded cache|\bgc\b|garbage collect|heap|boxing|clone\(\)|copy on|string concat|"
     r"stringbuilder|interning|__slots__|fetchall"),
    ("N+1 and accidental quadratic", "universal",
     r"(?<![\w(])n\+1(?!\))|quadratic|nested loop|o\(n2\)|o\(n\^2\)|eager load|includes\(|"
     r"preload|select_related|"
     # Third pass, 2026-09-24: go's `rules/06` probe is titled "O(n²)" with a superscript,
     # which neither spelling above matches -- an artefact.
     r"o\(n²\)|uselazyloadingproxies"),

    # --- concepts added 2026-09-21 after the first run's UNCLASSIFIED list named them.
    # Every one came from reading items this file could not classify, which is the
    # vocabulary hole the --show-unmatched report exists to surface.
    ("suppressing a linter / type check", "universal",
     r"ts-ignore|ts-nocheck|ts-expect-error|nolint|noqa|rubocop:disable|"
     r"suppresswarnings|pragma warning disable|#!?\\\[allow|allow\(|phpstan-ignore|"
     r"psalm-suppress|nosonar|lint:ignore|type: ?ignore|baseline|waiver|"
     r"warning disable|deny\(warnings\)|suppress"),
    ("module boundaries & imports", "universal",
     r"(?<![\w\"'])import\b|circular depend|cyclic|module boundar|package (layout|structure)|"
     r"relative import|project reference|internal package|namespace layout|grab[- ]bag|"
     r"using namespace|pragma once|fvisibility|`pub` field|unreachable_pub|internalsvisibleto|"
     r"require_relative|load_path"),
    # ROADMAP 65, 2026-09-24: `toFixed` could never match (items are lowercased before
    # matching), and `rounding` lit js/ts from "surrounding". Neither changed a cell.
    ("numeric precision & money", "universal",
     r"float(ing)? (point|money)|decimal|(?<!sur)rounding|money|\bcurrency|bigint|bigdecimal|"
     r"tofixed|precision loss|integer division"),
    ("date, time & timezone", "universal",
     r"timezone|\btz\b|\butc\b|\bdst\b|daylight|monotonic|time\.now|datetime|leap second|"
     r"epoch|wall[- ]clock (interval|time|read|for)|(steady|system|high_resolution)_clock|"
     r"clock_gettime|clock_monotonic|systemtime|\binstant\b|stopwatch|localtime|"
     r"time\.time\(\)|date\.now|hrtime|microtime|hrtime\(|process\.clock"),
    ("encoding, unicode & text", "conditional:the skill handles text decoding explicitly",
     r"unicode|utf-8|encoding|decode|normaliz(e|ation)|locale|collation|byte order mark"),

    # --- cross-cutting operational
    ("exit status / error signalling of tools", "conditional:the skill drives external commands",
     r"exit (status|code)|\$\?|errorlevel|pipestatus|pipefail|nonzero|non-zero exit"),
    ("version floor / EOL awareness", "universal",
     r"\beol\b|end of life|minimum (version|supported)|msrv|version floor|"
     r"unsupported version|\blts\b|deprecated (runtime|version)|language version|"
     r"standard pinned|requires-python|engines\.node"),
    ("resource limits / DoS guards", "universal",
     r"rate limit|quota|\bdos\b|denial of service|redos|catastrophic backtrack|"
     r"max (depth|length|size|connections)|recursion (depth|limit)|maxbytesreader|"
     r"max_execution_time|request_terminate_timeout|memory_limit|"
     r"limitreader"),
]



# --- the universal floor -----------------------------------------------------------
# Concepts every language skill in the tier probes TODAY. Pinned, so that a new skill, a
# refactor or a checklist rewrite cannot quietly drop one: `--assert-universal` fails if
# any of these stops being 9/9. This is a RATCHET, not a description -- it is the half of
# ROADMAP 61 that a template alone cannot provide, because a template is only read once,
# when a skill is created, and says nothing about the next edit.
#
# Measured 2026-09-22. `suppressing a linter / type check` reached 9/9 that same day
# (ROADMAP 60), so it is pinned immediately: the gate's first job is to defend work that
# was just done, which is when a regression is cheapest to make and least likely noticed.
#
# Adding to this list is a claim that EVERY language should probe it -- check the triage
# ledger in docs/LANGUAGE-TIER.md first, because a concept can be absent for a principled
# reason (transport/PKI is delegated library-wide, router rule 18).
UNIVERSAL_FLOOR = [
    "error handling & propagation",
    "absence / null / in-band sentinel",
    "data race / shared mutable state",
    "cryptography & randomness",
    "secrets handling",
    "input validation & untrusted data",
    "dependency pinning & lockfiles",
    "vulnerability scanning of dependencies",
    "static analysis / linter configuration",
    "build reproducibility & CI gates",
    "test suite health & determinism",
    "suppressing a linter / type check",
    # Reached 9/9 on 2026-09-22 when ROADMAP 57 closed (js/ts, php, ruby written that
    # day; python and c/c++ the day before). Pinned immediately, for the same reason as
    # the line above: the cheapest moment to lose work is right after doing it.
    "public API surface & evolution",
    # Fourth pass, 2026-09-24: 9/9 after the false presences were removed and the real
    # absences they hid were closed, each cell's matched substring read by hand with
    # `--explain all all`. `typing / generics` is also 9/9 but is conditional, so it is not
    # a claim about every language and stays out.
    "logging hygiene / PII in logs",
    "date, time & timezone",
    "resource lifecycle (close/dispose/RAII)",
    "cancellation / timeouts",
    "SQL / query injection",
    "command / subprocess injection",
    "path traversal / file access",
    "authn / authz checks",
    "profiling before optimizing",
    "allocation / GC pressure",
    "version floor / EOL awareness",
    # ROADMAP 65, 2026-09-24: 3/9 -> 9/9. The six absences (rust, go, c/c++, .NET, php,
    # ruby) were all real; each now carries a BUILD bullet and a probe tested on bad and
    # good fixtures under ugrep and BSD grep, and every cell's matched substring was read
    # by hand with `--explain` (js/ts rests on its float-money probe, not on its three
    # "HIGH if money" severity notes).
    "numeric precision & money",
]

def classify(text):
    """Concepts this item matches. An item may match several -- a probe for
    `yaml.load` is both deserialization and untrusted input, and forcing a single
    bucket would hide one of them."""
    low = text.lower()
    # Probes are stored as escaped regex (`Process\.Start`), so a matcher written for the
    # plain spelling never sees them. Match the backslash-stripped text as well; the union
    # cannot drop a concept the raw text already matched. Found by the 2026-09-24 .NET pass.
    plain = low.replace("\\", "")
    return [c for c, _, pat in CONCEPTS if re.search(pat, low) or re.search(pat, plain)]


def explain_hits(text, pat):
    """(matched substring, ~60 chars of context) for every match in `text`, read the same
    two ways `classify` reads it. Deduplicated on position so a match both copies share is
    printed once."""
    low = text.lower()
    out, seen = [], set()
    for copy in (low, low.replace("\\", "")):
        for m in re.finditer(pat, copy):
            key = (m.group(0), copy[max(0, m.start() - 30):m.end() + 30])
            if key not in seen:
                seen.add(key)
                out.append(key)
    return out


def explain(concept, lang):
    """Print every item of `lang` that puts `concept` in its cell, and WHICH substring did.

    Why this exists: a PRESENT cell is a claim too. The 2026-09-24 third pass found six
    cells lit only by substring accident (`slog` inside `syslog`, `import` inside
    `DllImport`), each hiding a real absence the candidate list can never show, and every
    one was found by printing the matched substring exactly like this."""
    pats = {c: p for c, _, p in CONCEPTS}
    if concept == "all" and lang == "all":
        # The sweep form: one line per PRESENT cell with the distinct substrings that lit
        # it and how many items each came from. Read it for words that are not the concept
        # (`import` in `dllimport`); a cell resting on one such item is a false presence.
        for c, _, pat in CONCEPTS:
            for s in E.LANGS:
                subs, n = {}, 0
                for _f, _k, text in E.skill_items(s):
                    got = {sub for sub, _ctx in explain_hits(text, pat)}
                    n += bool(got)
                    for sub in got:
                        subs[sub] = subs.get(sub, 0) + 1
                if n:
                    print("%-40s %-6s items=%-3d %s" % (c[:40], E.label(s), n, ", ".join(
                        "%r x%d" % kv for kv in sorted(subs.items(), key=lambda kv: -kv[1]))))
        return 0
    skill = {E.label(s): s for s in E.LANGS + E.SHELL}.get(lang, lang)
    if concept not in pats or skill not in E.LANGS + E.SHELL:
        print("unknown concept or language. concepts: %s; languages: %s"
              % ("; ".join(pats), ", ".join(E.label(s) for s in E.LANGS + E.SHELL)))
        return 2
    items = E.skill_items(skill)
    n = 0
    for f, _k, text in items:
        hits = explain_hits(text, pats[concept])
        if hits:
            n += 1
            print("%s: %s" % (f, text[:110]))
            for sub, ctx in hits:
                print("    matched %r in: ...%s..." % (sub, ctx))
    print("%d of %d %s items match '%s'" % (n, len(items), E.label(skill), concept))
    return 0


def build(skills):
    present = {}     # concept -> set(skill)
    classified = {}  # skill -> (n_classified, n_total)
    unmatched = {}   # skill -> [text, ...]
    for s in skills:
        items = E.skill_items(s)
        hit = 0
        misses = []
        for _f, _k, text in items:
            cs = classify(text)
            if cs:
                hit += 1
                for c in cs:
                    present.setdefault(c, set()).add(s)
            else:
                misses.append(text)
        classified[s] = (hit, len(items))
        unmatched[s] = misses
    return present, classified, unmatched


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--show-unmatched", type=int, default=0, metavar="N",
                    help="print N unclassified items per skill (vocabulary holes)")
    ap.add_argument("--min-coverage", type=float, default=0.0, metavar="FRAC",
                    help="exit 1 if any skill classifies below this fraction")
    ap.add_argument("--assert-format", action="store_true",
                    help="exit 1 if any skill's rules-file Audit checklist is not tickable")
    ap.add_argument("--assert-universal", action="store_true",
                    help="exit 1 if any UNIVERSAL_FLOOR concept is not present in all 9")
    ap.add_argument("--explain", nargs=2, metavar=("CONCEPT", "LANG"),
                    help="print the items that light CONCEPT for LANG (label, e.g. .NET, "
                         "or skill name) and the substring each matched, then exit. "
                         "Use it on a PRESENT cell before believing it. `--explain all all` "
                         "prints every present cell's matched substrings (the sweep form)")
    args = ap.parse_args()
    if args.explain:
        return explain(*args.explain)

    present, classified, unmatched = build(E.LANGS)
    sh_present, sh_classified, sh_unmatched = build(E.SHELL)

    # --- the matrix
    width = max(len(c) for c, _, _ in CONCEPTS) + 2
    head = " " * width + "".join("%-8s" % E.label(l) for l in E.LANGS)
    print(head)
    print("-" * len(head))

    # Every absence of a universal concept lands in exactly one of two lists. Until
    # 2026-09-24 only 1-5 missing was listed and 6+ was silently dropped, with no rationale
    # recorded; that hid `numeric precision & money` (3/9) from every pass (ROADMAP 65). The
    # split is kept rather than merged because the two mean different things: a few blanks
    # are usually per-language gaps or vocabulary artefacts, while a concept missing almost
    # everywhere is either a class-wide gap or a concept mis-labelled `universal`. Operator
    # decision 2026-09-24: list every absence; triage decides which it is.
    candidates, mostly_absent = [], []
    for concept, universality, _ in CONCEPTS:
        have = present.get(concept, set())
        row = "".join(("%-8s" % ("  X" if l in have else "  .")) for l in E.LANGS)
        print("%-*s%s" % (width, concept, row))
        missing = [l for l in E.LANGS if l not in have]
        if universality != "universal" or not missing:
            continue
        (candidates if len(missing) <= 5 else mostly_absent).append(
            (concept, missing, len(have)))

    # --- denominators, always
    print("\nCLASSIFICATION DENOMINATOR (items matched / items read)")
    worst = 1.0
    for l in E.LANGS:
        hit, tot = classified[l]
        frac = hit / tot if tot else 0.0
        worst = min(worst, frac)
        print("  %-8s %4d / %-4d  %5.1f%%" % (E.label(l), hit, tot, 100 * frac))
    hit, tot = sh_classified["shell-scripting"]
    print("  %-8s %4d / %-4d  %5.1f%%   (reported separately: not a peer of the tier)"
          % ("shell", hit, tot, 100 * hit / tot if tot else 0))

    # --- shell as its own group
    print("\nSHELL (own spine -- concepts it probes)")
    probed = sorted(c for c, ss in sh_present.items() if "shell-scripting" in ss)
    print("  " + ("\n  ".join(probed) if probed else "(none)"))

    # --- candidates, never called findings
    print("\nCANDIDATE GAPS -- a universal concept absent from some languages.")
    print("NOT findings. Open the file before believing any row (2 of 8 such Python")
    print("candidates died on reading during ROADMAP 59's first pass).")
    if not candidates:
        print("  (none)")
    for concept, missing, have in sorted(candidates, key=lambda x: -x[2]):
        print("  %-42s present %d/9, absent: %s"
              % (concept, have, ", ".join(E.label(m) for m in missing)))

    print("\nMOSTLY ABSENT -- a universal concept missing in 6+ languages: either a real")
    print("class-wide gap or a concept that is not universal; triage decides.")
    if not mostly_absent:
        print("  (none)")
    for concept, missing, have in sorted(mostly_absent, key=lambda x: -x[2]):
        print("  %-42s present %d/9, absent: %s"
              % (concept, have, ", ".join(E.label(m) for m in missing)))

    if args.show_unmatched:
        print("\nUNCLASSIFIED ITEMS -- holes in THIS FILE's vocabulary, not in the skills.")
        for l in E.LANGS + E.SHELL:
            miss = unmatched.get(l) or sh_unmatched.get(l) or []
            if not miss:
                continue
            print("  [%s] %d unclassified; first %d:" % (E.label(l), len(miss),
                                                         min(args.show_unmatched, len(miss))))
            for t in miss[:args.show_unmatched]:
                print("      " + t[:150])

    if args.assert_format:
        # UNIFIED CHECKLIST FORMAT (2026-09-23). Three body formats were in use and invariant
        # 2 gates only the heading. Only the tickable form is ENUMERABLE, and AUDIT mode tells
        # the model to "verify your diff satisfies every item" -- unfollowable against a shell
        # block. Two mechanical readers had already given wrong answers because of it: a
        # `- [ ]` count returned 0 for seven of nine skills, and a concept pass reported
        # sota-golang as lacking API/design probes its 02-design.md plainly has.
        #
        # WIDENED 2026-09-23 from the nine language skills to EVERY skill, and per FILE. The
        # language-only scope left 14 fenced files in two domain skills ungated, and a file
        # whose checklist is plain `- ` bullets yields ZERO items -- which the old
        # `kinds and ...` test read as a pass. Three sota-architecture files sat there.
        wrong, files = [], 0
        dirs = E.all_rules_dirs()
        for d in dirs:
            for f in sorted(d.glob("*.md")):
                files += 1
                kinds = [k for k, _t in E.items_in_file(f)]
                if not kinds:
                    wrong.append("%s (no tickable items)" % f.relative_to(E.ROOT))
                elif set(kinds) != {"box"}:
                    wrong.append("%s (%s)" % (f.relative_to(E.ROOT),
                                              ", ".join(sorted(set(kinds)))))
        print("\nCHECKLIST FORMAT")
        if not files:
            print("  FAIL: 0 rules files read -- the gate verified nothing")
            return 1
        if wrong:
            print("  NOT TICKABLE (%d of %d rules files):" % (len(wrong), files))
            for w in wrong:
                print("    " + w)
            print("  Every '## Audit checklist' must use `- [ ]` bullets.")
            print("  scripts/lib/unify_checklist.py converts a fenced block; review its output.")
            return 1
        print("  ok (%d rules files across %d skills, all tickable)" % (files, len(dirs)))

    if args.assert_universal:
        broken = []
        for concept in UNIVERSAL_FLOOR:
            have = present.get(concept, set())
            missing = [E.label(l) for l in E.LANGS if l not in have]
            if missing:
                broken.append((concept, missing))
        print("\nUNIVERSAL FLOOR (%d pinned concepts)" % len(UNIVERSAL_FLOOR))
        if broken:
            for concept, missing in broken:
                print("  REGRESSED: %-42s now absent from: %s" % (concept, ", ".join(missing)))
            print("A concept every language probed has stopped being probed by one of them.")
            print("Either restore it, or -- if it is now delegated -- remove it from")
            print("UNIVERSAL_FLOOR and record why in docs/LANGUAGE-TIER.md's triage ledger.")
            return 1
        print("  ok (all %d still present in 9/9)" % len(UNIVERSAL_FLOOR))

    if args.min_coverage and worst < args.min_coverage:
        print("\nFAIL: lowest coverage %.1f%% is below the required %.1f%%"
              % (100 * worst, 100 * args.min_coverage))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
