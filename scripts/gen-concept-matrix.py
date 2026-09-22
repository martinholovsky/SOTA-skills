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
  * a concept's absence from a language is a CANDIDATE, never a finding. Confirm by opening
    the file -- 2 of 8 candidate Python gaps died on reading during ROADMAP 59's first pass.

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
CONCEPTS = [
    # --- language baseline / API surface
    ("error handling & propagation", "universal",
     r"error handl|wrap(ped|ping)? error|error type|swallow|empty catch|catch \(|"
     r"rescue|on_error|error code|errors\.(is|as)|unwrap|expect\(|panic"),
    ("absence / null / in-band sentinel", "universal",
     r"in-band|sentinel|null|nil |none\b|optional|nullable|-1|magic (number|value)"),
    ("public API surface & evolution", "universal",
     r"public (api|surface)|semver|breaking change|deprecat|__all__|abi|"
     r"export|visibility|private_constant|readonly|final\b"),
    ("immutability / const discipline", "conditional:has a const or freeze mechanism",
     r"immutab|const\b|constexpr|readonly|frozen|freeze|final field|mutat|defensive copy"),
    ("typing / generics discipline", "conditional:gradual or explicit typing",
     r"type hint|typing|mypy|generic|any\b|unknown\b|strict(ness)?|nullable ref|rbs|sorbet"),

    # --- concurrency
    ("data race / shared mutable state", "universal",
     r"data race|race condition|shared mutab|thread[- ]safe|goroutine|gvl|ractor|"
     r"send\b.*sync|atomic|lock|mutex|synchroniz"),
    ("cancellation / timeouts", "universal",
     r"cancel|timeout|deadline|context\.|ctx\b|abortcontroller|cancellationtoken"),
    ("task / thread leaks", "universal",
     r"leak|orphan|detached task|fire[- ]and[- ]forget|unawaited|background task|"
     r"goroutine leak|dangling"),
    ("blocking the event loop / executor", "conditional:has an event loop or async runtime",
     r"event loop|blocking (call|io|the)|block_on|run_until|sync over async|\.result\(\)|"
     r"configureawait|deadlock"),
    ("backpressure / unbounded queues", "universal",
     r"unbounded|backpressure|bounded (queue|channel)|buffer size|queue depth"),

    # --- memory / resources
    ("resource lifecycle (close/dispose/RAII)", "universal",
     r"raii|dispose|close\(|defer |using |with open|context manager|finaliz|"
     r"file handle|connection (leak|pool)|ensure\b"),
    ("memory safety (bounds, UAF, overflow)", "conditional:manual memory management",
     r"use[- ]after[- ]free|buffer overflow|bounds|out of bounds|dangling pointer|"
     r"double free|integer overflow|sanitizer|asan|ubsan|valgrind|miri"),

    # --- security
    ("SQL / query injection", "universal",
     r"sql inject|parameteriz|prepare|raw quer|sql built from|string interpolation in (a )?quer|"
     r"activerecord|sqlalchemy|dapper|pdo|whereraw|selectraw|db::raw|escape_string|"
     r"emulate_prepares|->query|execute\(|sqlx|diesel|knex|sequelize|query buil"),
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
     r"gob\b|xxe|xml external|phar|serde|bincode|json\.loads|fromjson|readobject"),
    ("output encoding / XSS / templating", "conditional:renders markup or templates",
     r"xss|escap|html_safe|htmlspecialchars|dangerouslysetinnerhtml|innerhtml|"
     r"autoescap|erb|template inject|sanitiz"),
    ("cryptography & randomness", "universal",
     r"crypto|cipher|aes|rsa|hash(ing)?|bcrypt|argon2|pbkdf2|md5|sha1\b|"
     r"csprng|secure random|rand\b|nonce|iv\b|constant[- ]time"),
    ("secrets handling", "universal",
     r"secret|credential|api key|password|token\b|\.env|hardcoded|vault|keyring"),
    ("input validation & untrusted data", "universal",
     r"validat|untrusted|sanitiz|allowlist|whitelist|bounds check|schema|"
     r"decompress|zip bomb|size limit|max size"),
    # Reclassified 2026-09-22 by triage. Router cross-cutting rule 18 puts transport/PKI
    # in `sota-network-security` rules/06 and TLS *client config* in `sota-code-security`
    # rules/04, library-wide. So a language skill with no TLS probe is DELEGATING, not
    # gapped -- rust, js/ts and c/c++ were being reported as gaps for obeying the router.
    ("TLS / transport verification", "conditional:transport/PKI is delegated library-wide (router rule 18)",
     r"tls|ssl|certificate|insecureskipverify|verify=false|hostname verif|"
     r"insecureignorehostkey|trust ?store|http://|rustls|openssl|danger_accept|"
     r"servercertificatevalidation|curlopt_ssl"),
    ("authn / authz checks", "universal",
     r"authoriz|authenticat|permission check|idor|access control|jwt|oauth|session|csrf|"
     r"cookie|samesite|httponly"),
    ("logging hygiene / PII in logs", "universal",
     r"log(ging|s)? (secret|pii|token|password)|redact|structured log|slog|"
     r"sensitive data in|stack trace (in|to) (the )?(response|user)"),

    # --- supply chain / tooling
    ("dependency pinning & lockfiles", "universal",
     r"lockfile|lock file|go\.sum|cargo\.lock|package-lock|poetry\.lock|gemfile\.lock|"
     r"pinned|pin\b|checksum|integrity hash|packages\.lock\.json"),
    ("vulnerability scanning of dependencies", "universal",
     r"govulncheck|cargo audit|pip-audit|npm audit|bundler-audit|dependency-check|"
     r"osv|advisory|cve|dependabot|renovate|safety\b"),
    ("static analysis / linter configuration", "universal",
     r"clippy|golangci|ruff|mypy|eslint|rubocop|phpstan|psalm|clang-tidy|cppcheck|"
     r"spotbugs|analyzer|lint|detekt|ktlint|brakeman|bandit|gosec|semgrep"),
    ("build reproducibility & CI gates", "universal",
     r"ci\b|github actions|workflow|pipeline|reproducib|build flag|hardening flag|"
     r"-d_fortify|relro|stack protector|csproj|gradle|maven|cmake"),
    ("supply-chain provenance & publishing", "universal",
     r"provenance|slsa|sigstore|cosign|sbom|publish|registry|namespace|typosquat|"
     r"dependency confusion|crates\.io|npmjs|pypi|rubygems|nuget"),

    # --- testing
    ("test suite health & determinism", "universal",
     r"flaky|determinis|test (suite|coverage)|coverage|assert|table[- ]driven|"
     r"-race\b|nextest|pytest|vitest|junit|rspec|minitest|xunit|phpunit"),
    ("property-based / fuzz testing", "conditional:a fuzzing or property library exists",
     r"fuzz|property[- ]based|quickcheck|proptest|hypothesis|afl|libfuzzer|go-fuzz"),

    # --- performance
    ("profiling before optimizing", "universal",
     r"profil|pprof|flamegraph|benchmark|bench\b|jmh|criterion|perf\b|measure"),
    ("allocation / GC pressure", "universal",
     r"alloc|gc\b|garbage collect|heap|boxing|clone\(\)|copy on|string concat|"
     r"stringbuilder|interning"),
    ("N+1 and accidental quadratic", "universal",
     r"n\+1|quadratic|nested loop|o\(n2\)|o\(n\^2\)|eager load|includes\(|preload|select_related"),

    # --- concepts added 2026-09-21 after the first run's UNCLASSIFIED list named them.
    # Every one came from reading items this file could not classify, which is the
    # vocabulary hole the --show-unmatched report exists to surface.
    ("suppressing a linter / type check", "universal",
     r"ts-ignore|ts-nocheck|ts-expect-error|nolint|noqa|rubocop:disable|"
     r"suppresswarnings|pragma warning disable|#!?\\\[allow|allow\(|phpstan-ignore|"
     r"psalm-suppress|nosonar|lint:ignore|type: ?ignore|baseline|waiver|"
     r"warning disable|deny\(warnings\)|suppress"),
    ("module boundaries & imports", "universal",
     r"import|circular depend|cyclic|module boundar|package (layout|structure)|"
     r"relative import|project reference|internal package|namespace layout|grab[- ]bag"),
    ("numeric precision & money", "universal",
     r"float(ing)? (point|money)|decimal|rounding|money|currency|bigint|bigdecimal|"
     r"toFixed|precision loss|integer division"),
    ("date, time & timezone", "universal",
     r"timezone|tz\b|utc|dst\b|daylight|clock|monotonic|time\.now|datetime|"
     r"leap second|epoch|duration"),
    ("encoding, unicode & text", "conditional:the skill handles text decoding explicitly",
     r"unicode|utf-8|encoding|decode|normaliz(e|ation)|locale|collation|byte order mark"),

    # --- cross-cutting operational
    ("exit status / error signalling of tools", "conditional:the skill drives external commands",
     r"exit (status|code)|\$\?|errorlevel|pipestatus|pipefail|nonzero|non-zero exit"),
    ("version floor / EOL awareness", "universal",
     r"eol\b|end of life|minimum (version|supported)|msrv|version floor|"
     r"unsupported version|lts\b|deprecated (runtime|version)"),
    ("resource limits / DoS guards", "universal",
     r"rate limit|quota|dos\b|denial of service|redos|catastrophic backtrack|"
     r"max (depth|length|size|connections)|recursion (depth|limit)"),
]


def classify(text):
    """Concepts this item matches. An item may match several -- a probe for
    `yaml.load` is both deserialization and untrusted input, and forcing a single
    bucket would hide one of them."""
    low = text.lower()
    return [c for c, _, pat in CONCEPTS if re.search(pat, low)]


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
    args = ap.parse_args()

    present, classified, unmatched = build(E.LANGS)
    sh_present, sh_classified, sh_unmatched = build(E.SHELL)

    # --- the matrix
    width = max(len(c) for c, _, _ in CONCEPTS) + 2
    head = " " * width + "".join("%-8s" % E.label(l) for l in E.LANGS)
    print(head)
    print("-" * len(head))

    candidates = []
    for concept, universality, _ in CONCEPTS:
        have = present.get(concept, set())
        row = "".join(("%-8s" % ("  X" if l in have else "  .")) for l in E.LANGS)
        print("%-*s%s" % (width, concept, row))
        missing = [l for l in E.LANGS if l not in have]
        if universality == "universal" and 0 < len(missing) <= 5:
            candidates.append((concept, missing, len(have)))

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

    if args.min_coverage and worst < args.min_coverage:
        print("\nFAIL: lowest coverage %.1f%% is below the required %.1f%%"
              % (100 * worst, 100 * args.min_coverage))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
