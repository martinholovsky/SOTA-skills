#!/usr/bin/env python3
"""code-rules-hook.py — after the agent writes code, name the rules file for what that code DOES.
A Claude Code PostToolUse hook on Edit|Write|MultiEdit, ON by default since ROADMAP 73 (m): the plugin
registers it (hooks/hooks.json) and install.sh's routing setup offers it.

WHY. ROADMAP 73. Reading the right rules file changes what an agent builds: with the cited files
named in the prompt, rule tests rose 0.698 -> 0.868 (sota-agent-evals v7, 2026-10-11, SUPPORTED).
Every shipped way of getting there chose the file from the TASK and failed: a hook that lists a
skill's files and asks for a full read got whole files read (79 -> 472 lines per run) but the right
one in 11/20 runs, and outcomes did not move (v8, NULL); a BM25 match of the prompt against the
rules index found a cited file for 6/20 tasks. Prompts do not name their risk: "export the orders
as CSV" never says formula injection, "fetch the callback URL" never says SSRF. The CODE does —
`csv.writer`, an outbound fetch, `zipfile` — so this hook selects from what was just written.
MEASURED: v9 (2026-10-12) reached a cited rules file in 18/20 runs (v8 11/20, files named in the
prompt 20/20), so the choice of file works, but rule tests went 0.698 -> 0.717 (NULL). In 6 of the
8 runs that failed a rule test, the agent named the tested risk and left it out as a decision for
the user ("beyond your spec"). v10 (2026-10-12) added APPLY below, saying the named rules are part
of the task: rule tests 0.717 -> 0.906 (SUPPORTED, 6 cases up, 0 down), above the arm that named the
files in the prompt (0.868), with spec tests still 20/20. v11 replaced APPLY with a bare
"MANDATORY:" label: 0.698 (NULL), and every failing run handed the rule back. The content is the
lever, not the emphasis. Shipped by default 2026-10-12 (ROADMAP 73 (m)) at +68% cost per run over the
plain install; the trigger table is in-sample: its author had read the 20 cases v9-v13 ran on, though it was
not changed after v9's replay (PRE-REGISTRATION-v9.md). OUT OF SAMPLE: v14 (2026-10-13, cases-v5,
20 tasks sampled from OWASP ASVS and authored blind to this library) ran this hook plus the router's
table against neither: reach 8/20 -> 13/20, as an offline replay of this table predicted, but cited
rule tests 0.667 -> 0.667 (NULL). Four of the five runs that reached the file and failed named the
risk and handed it back, citing the precise spec as the request ruling it out.

WHAT IT SAYS (as `additionalContext`, read next to the tool result): for each trigger the written
text matches, in table order, the absolute path of the rules file and the section to check, with
one action — read each named file in full, then check the change against it — and then (APPLY,
ROADMAP 73 (j), measured in v10) that those rules are part of the task: build each with a
conservative default rather than handing it back, unless the request rules it out, and name each
default in one line of the final message. A file is named at
most once per session, and at most PER_EVENT new files per edit, so a long session is not flooded.
"Once" holds when two copies run on one edit (the plugin's and the installer's, which Claude Code
runs in parallel): each file is claimed with an exclusive create, and only the copy that wins
names it.
Test files and an agent's scratchpad (a `scratchpad/` path segment) are skipped: what matters is
what the shipped code does. Config files (CONFIG_EXT: YAML,
.j2, .conf, .service, .toml) are read by the host-config rows only (CONFIG_ROWS), since 2026-10-22;
JSON is never read. Since 2026-11-18 a Dockerfile/Containerfile (no extension) is read as config too,
and CONFIG_ROWS gained a CI workflow, a Dockerfile and a Dependabot row, which fire on config files
only (CONFIG_ONLY), never on code: before that, writing a workflow or a Dockerfile named no rules
file at all. Terraform, Vue/Svelte, server templates, PowerShell and SQL get per-file-type rows
(TYPED_ROWS) instead of the code rows, which misfire on them. `rows_for(path)` decides which rows a
written file is tried against.

The triggers are a table of regular expressions over the written text, and they are crude on
purpose: a false trigger costs one file read, a missed one costs the rule.
Each named row carries the line that matched it (`matched: "..."`, printable, at most ~72
characters), so an agent can see why it fired. A row may have EXCLUDE senses, blanked before it
is matched; only the session/token row has them, built against a labelled set (2026-11-12).
Every row skips a raw string shaped like a regular expression (2026-11-17): a pattern table that
NAMES `subprocess` or `upload` describes text and does not run a process or accept a file.

IT NEVER BLOCKS: any error prints one line to stderr and exits 0 with no output.
LANGUAGE NOTE (ROADMAP 99, 2026-11-18). The first edit of code in a language whose skill no tool call
in the session has named (a Skill call, a read, a command; the stored skills listing does not count)
also gets one note per session naming that skill's SKILL.md. Replayed with `--replay-language` over
one operator's 432 transcripts: 77 notes in 67 of the 91 that edited code; a median of 6 edits of the
language followed each note, 9 notes had none after them; the skill was named later anyway 17 times.

SOTA_CODE_RULES_HOOK=off (or 0 / false / no) disables it.

Registered by the plugin; install.sh --routing adds it to ~/.claude/settings.json. By hand
(user or project settings.json):
  "hooks": {
    "PostToolUse": [{"matcher": "Edit|Write|MultiEdit", "hooks": [{"type": "command",
                     "command": "python3 /ABS/PATH/scripts/code-rules-hook.py"}]}]
  }
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIMIT = 10_000
PER_EVENT = 2
CODE_EXT = {"py", "pyi", "go", "rs", "c", "h", "cc", "cpp", "cxx", "hpp", "java", "kt", "kts",
            "cs", "php", "rb", "swift", "js", "jsx", "mjs", "cjs", "ts", "tsx", "sh", "bash"}
# Config files are read by the host-config rows only (CONFIG_ROWS, below; operator decision
# 2026-10-22). Over 161,783 local config files, every row together fired on 40% of them, the
# generic rows almost always falsely, while these three rows held 28/30, 13/14 and 9/9 on YAML,
# .conf and friends. JSON stays out: its hits were i18n strings and LLM transcripts.
CONFIG_EXT = {"yml", "yaml", "j2", "conf", "service", "toml"}
# `test_x` and `test-x`, `x_test` and `x-test`: the hyphenated forms are this repository's own
# convention (scripts/test-*.sh), which the underscore-only pattern missed (field report 2026-11-10).
TEST_PATH = re.compile(r"(^|/)(tests?|spec|__tests__)/|(^|/)test[_-][^/]*$|[_-]test\.\w+$|\.(test|spec)\.\w+$")
# An agent's scratchpad holds proofs of concept and probes, not shipped code: the same reason tests
# are skipped. Operator decision 2026-10-23, after 5 false triggers there and none useful.
SCRATCH_PATH = re.compile(r"(^|/)scratchpad/")

# (what the code does, pattern, [(skill, rules file number, section to check)]). Order is priority:
# specific surfaces first, the generic ones (handlers, logging, retries) last. Each row was written
# from the skills' own rules indexes, not from any eval task.
TRIGGERS: list[tuple[str, str, list[tuple[str, str, str]]]] = [
    ("fetches a URL, which is an SSRF surface whenever any part of the destination comes from a caller",
     r"urlopen|requests\.(get|post|put|head|request)\(|httpx\.|aiohttp\.|\bhttp_?get\b|\bfetch\(|"
     r"urllib\.request|http\.client|HttpClient|http\.(Get|Post|NewRequest)\(",
     [("sota-code-security", "01", "§5 SSRF")]),
    ("writes CSV or spreadsheet output",
     r"\bcsv\b|text/csv|openpyxl|xlsxwriter|\bxlsx\b",
     [("sota-code-security", "01", "§11, CSV/formula injection")]),
    ("reads or extracts an archive",
     r"zipfile|tarfile|extractall|ZipFile|\.namelist\(|archive/zip|java\.util\.zip",
     [("sota-code-security", "01", "§4 path traversal and Zip Slip"),
      ("sota-code-security", "09", "untrusted data ingestion")]),
    ("accepts a file or image from outside",
     r"upload|content[_-]type|mimetype|\bPIL\b|Image\.open|imghdr|\.(png|jpe?g|gif|webp)\b",
     [("sota-code-security", "21", "§1 file upload handling"),
      ("sota-code-security", "09", "untrusted data ingestion")]),
    ("builds an email or a message header",
     r"EmailMessage|smtplib|email\.(message|mime|utils)|[\"'](Subject|Reply-To|To|From|Cc)[\"']|send_?mail",
     [("sota-code-security", "01", "§11, CRLF / header injection")]),
    ("runs a process",
     r"subprocess|os\.system|os\.popen|shell=True|exec\.Command|Runtime\.getRuntime",
     [("sota-code-security", "01", "§3 command injection")]),
    ("runs or configures a container or sandbox (seccomp, capabilities, namespaces)",
     r"seccomp|SCMP_|--security-opt|--cap-(drop|add)\b|--userns\b|\bunshare\b|\b(podman|docker) run\b",
     [("sota-sandboxing", "02", "§1 namespaces, §3 seccomp-bpf, §5 capabilities"),
      ("sota-sandboxing", "03", "§1 Docker / OCI hardening checklist")]),
    # 2026-11-18, per-file-type rows: file types the library has rules for but the code rows misfire
    # on (about half of 150 local .vue/.svelte/.ps1 files fired a code row, almost all falsely). Each
    # matches only its language's own construct and fires only for its extensions (TYPED_ROWS).
    # Measured on random local files (rg --hidden over ~/Github, 400 per type): Terraform network 11,
    # IAM 5, storage 3 of 400; v-html 3/400, {@html} 6/400; template escape hatches 3/400; EJS `<%-`
    # 9/88 (partial `include` excluded); PowerShell 35/400; SQL DDL 52/400 (comment lines excluded).
    ("opens network access in infrastructure code (Terraform)",
     r'"0\.0\.0\.0/0"|"::/0"',
     [("sota-cloud-infrastructure", "03", "§1 deny-by-default network design")]),
    ("grants wildcard IAM permissions in infrastructure code (Terraform)",
     r'"Action"\s*:\s*"\*"|actions\s*=\s*\[\s*"\*"\s*\]|"\*:\*"',
     [("sota-cloud-infrastructure", "02", "§3 policy authoring")]),
    ("makes storage public or unencrypted in infrastructure code (Terraform)",
     r'acl\s*=\s*"public-read(?:-write)?"|block_public_(?:acls|policy)\s*=\s*false|'
     r'restrict_public_buckets\s*=\s*false|publicly_accessible\s*=\s*true|\b(?:encrypted|storage_encrypted)\s*=\s*false',
     [("sota-cloud-infrastructure", "05", "§1 public access, §4 encryption defaults")]),
    ("renders raw HTML in a component (v-html, {@html})",
     r"\bv-html\s*=|\{@html\s",
     [("sota-web-frameworks", "04", "§4 Vue-specific XSS"), ("sota-code-security", "05", "§1 XSS")]),
    ("turns template escaping off",
     r"\|\s*safe\b|\{%-?\s*autoescape\s+(?:false|off)\b|<%==|\{\{\{|\bmark_safe\(|\.html_safe\b|\|\s*raw\b",
     [("sota-code-security", "05", "§1 XSS, context-aware output encoding")]),
    ("writes unescaped output in an EJS template",
     r"<%-(?!\s*include\b)",
     [("sota-code-security", "05", "§1 XSS, context-aware output encoding")]),
    ("evaluates a string as code or bypasses execution policy (PowerShell)",
     r"\bInvoke-Expression\b|\biex\s|\bDownloadString\s*\(|\[scriptblock\]::Create\(|-ExecutionPolicy\s+(?:Bypass|Unrestricted)",
     [("sota-shell-scripting", "07", "§5 Invoke-Expression and string-built commands, §6 execution policy")]),
    ("changes a schema in a way that locks or rewrites a table (SQL DDL)",
     r"(?im)^(?!\s*--)[^\n]*?\b(?:CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?!CONCURRENTLY)|DROP\s+COLUMN\b|"
     r"ALTER\s+COLUMN\b[^;\n]*\bTYPE\b|ADD\s+COLUMN\b[^;\n]*\bNOT\s+NULL\b(?![^;\n]*\bDEFAULT\b))",
     [("sota-databases", "02", "§2 lock-aware DDL on hot tables")]),
    # 2026-11-18: an agent wrote .github/dependabot.yml from rules/01's "keep pins fresh with Dependabot"
    # and never reached the cooldown in rules/03. `package-ecosystem:` is Dependabot's own key: 80 of 80
    # local YAML files carrying it were Dependabot configs (rg --hidden over ~/Github, 2026-11-18).
    ("configures a dependency-update bot (Dependabot)",
     r"(?m)^\s*-?\s*package-ecosystem:\s",
     [("sota-devsecops", "03", "§3.7 cooldown, grouping, automerge")]),
    # 2026-11-18: workflows and Dockerfiles reached no row at all (YAML reads only config rows; a
    # Dockerfile has no extension). Measured over ~/Github with rg --hidden: `runs-on:` is in 1,966
    # YAML files, 1,891 under a workflow directory and the other 75 GitHub Actions templates; a FROM
    # line is in 64,913 of 64,916 Dockerfile-named files and in no YAML file. Both are CONFIG_ONLY:
    # a FROM line also opens SQL inside code.
    ("writes a CI workflow (GitHub Actions)",
     r"(?m)^\s*runs-on:\s",
     [("sota-devsecops", "01", "§1.1 token permissions, §1.3 pinned actions, §1.4 untrusted triggers, §1.5 expression injection")]),
    ("writes a container image (Dockerfile)",
     r"(?m)^\s*FROM\s+\S",
     [("sota-devsecops", "04", "§4.2 multi-stage, §4.3 base image pinned by digest"),
      ("sota-sandboxing", "03", "§1 Docker / OCI hardening checklist")]),
    ("sets or disables an LSM profile (AppArmor, SELinux)",
     r"\baa-(complain|enforce|disable)\b|force-complain|apparmor_parser|\bsetenforce\b|\bsetsebool\b|"
     r"WithApparmorProfile|apparmor[=:]\s*unconfined|security[_-]opt[^\n]*(apparmor|label)",
     [("sota-sandboxing", "02", "§6 LSMs: AppArmor / SELinux")]),
    ("builds a command-line interface",
     r"ArgumentParser|add_argument\(|@click\.command|typer\.Typer|clap::|cobra\.Command",
     [("sota-cli-ux", "02", "§1 the stream contract, §3 exit codes, §5 line-buffered stdout when piped")]),
    # 2026-11-07 field report: `done < <(select_items)` exited 0 on a failing producer, and a .sh
    # Write matched no row. `< <(` is the redirect-from-process-substitution form (while, mapfile, read).
    ("reads from a process substitution, whose exit status is unreachable",
     r"<\s*<\(",
     [("sota-shell-scripting", "02", "§4, a process substitution's exit status is unreachable")]),
    ("calls a model API: output cap, stop reason and spend",
     r"max_(completion_|output_)?tokens|finish_reason|stop_reason|chat\.completions",
     [("sota-llm-engineering", "02", "§6, stop_reason before parsing and an explicit max_tokens"),
      ("sota-llm-engineering", "05", "§4 cost engineering")]),
    ("configures PAM, a login stack",
     r"\bpam_[a-z0-9_]+\.so\b|/etc/pam\.d",
     [("sota-code-security", "02", "§1, lockout and enumeration"),
      ("sota-code-security", "14", "§6 count a control by the principals it runs as")]),
    ("builds a database query",
     r"\.execute\(|\bSELECT\b|\bINSERT\s+INTO\b|\bUPDATE\s+\w+\s+SET\b",
     [("sota-code-security", "01", "§2 SQL injection")]),
    ("parses or builds XML",
     r"xml\.|etree|lxml|minidom|XMLParser|DocumentBuilder",
     [("sota-code-security", "01", "§6 XXE and XML")]),
    ("deserialises data",
     r"pickle|yaml\.load|marshal\.loads|ObjectInputStream|unserialize\(",
     [("sota-code-security", "01", "§8 unsafe deserialization")]),
    ("renders HTML or a template",
     r"render_template|jinja|Template\(|innerHTML|dangerouslySetInnerHTML|text/html|Markup\(",
     [("sota-code-security", "05", "XSS and web security")]),
    ("checks a password or handles a login",
     r"passw(or)?d|\blogin\b|authenticat|credential|sign_?in",
     [("sota-code-security", "02", "§1, credential stuffing, lockout and enumeration")]),
    ("issues or checks a session or token",
     r"session|\btokens?\b|cookie|remember_?me|\bjwt\b|bearer",
     [("sota-code-security", "17", "§2 session management"),
      ("sota-code-security", "02", "authentication")]),
    ("decides who may do what",
     r"principal|permission|\broles?\b|_roles?\b|\broles?_|is_admin|\bowner\b|tenant|authoriz|forbidden|\b403\b",
     [("sota-code-security", "03", "§1-§3 deny by default, IDOR, function-level authorization")]),
    ("sends or receives a webhook or callback",
     r"webhook|callback_?url|x-signature|signing_secret",
     [("sota-api-design", "06", "webhooks")]),
    ("returns a list that can grow",
     r"\blimit\b|\boffset\b|\bcursor\b|page_?size|next_page",
     [("sota-api-design", "01", "§4 pagination")]),
    ("moves money or must not run twice",
     r"idempot|payment|\bcharge\b|refund|\btransfer\b",
     [("sota-api-design", "01", "§6 idempotency keys")]),
    ("calls something that can fail or hang",
     r"\bretr(y|ies)\b|backoff|timeout|time\.sleep|circuit|max_attempts",
     [("sota-architecture", "04", "§1-§3 timeouts, retries, circuit breakers")]),
    ("logs, returns errors, or returns records about people",
     r"logger\.|logging\.|traceback|str\(e\)|repr\(e\)|\bemail\b|\bphone\b|password_hash",
     [("sota-code-security", "07", "§1, §2 and §4: errors, logs, response over-exposure")]),
    ("adds a request handler or endpoint, which needs abuse control keyed to the caller",
     r"def \w+\(self,\s*(principal|req|request)\b|@(app|router|bp)\.(get|post|put|delete|patch|route)\(|"
     r"\b(status_code|status)\s*[,=:]\s*(200|201|400|401|403|404|409|429)\b|return\s*\(?\s*(200|201|400|401|403|404|409|429)\s*,",
     [("sota-api-design", "07", "§2 rate limiting"),
      ("sota-code-security", "06", "§5 resource exhaustion")]),
]
COMPILED = [(what, re.compile(rx, re.I), refs) for what, rx, refs in TRIGGERS]

# Senses of a row's words that are NOT what the row is about, removed from the text before that row
# is matched. Recall-safe by construction: an edit still fires if any match survives, so only an edit
# whose EVERY match is one of these senses goes quiet. Built against a labelled set (2026-11-12,
# ADOPTION-LOG, resolving the 2026-10-20 false-trigger deferral for this row): 254 local code files,
# 52 labelled as issuing or checking a session, cookie or auth token, including two blind hold-outs.
# An allow-list of auth phrasings scored recall 0.59 and 0.69 on the hold-outs and was rejected;
# this list kept 52/52 and removed 190 of 1,270 matching lines in the non-auth files (15%) against 5
# of 483 in the auth files, whose files still fired. Bare `session` and `token` in a generic sense
# are most of what remains, and no word list separates them: the matched evidence printed with each
# row is the remedy for those.
EXCLUDE = {
    "issues or checks a session or token": re.compile(
        r"TokenStream\w*|proc_macro\w*|Token!\[[^\]\n]*\]|\bto_tokens\b|\btoken::\w+"
        r"|\btokens?\.(extend|append\w*)\b|rustc_session\w*"
        r"|\b(max|input|output|prompt|completion|reasoning|thinking|total|cached?|cache_\w+)_?tokens?\b"
        r"|\btokens?_?(count|usage|used|budget|limits?|logprob\w*)\b|\btokens? (count|usage|budget|limits?|bucket|per)\b"
        r"|token[- ]bucket|\btokeni[sz]\w*|\b\d[\d,.]*k?\+?\s*tokens?\b|tokens?/s\b|\bper[- ](\w+ )?tokens?\b|chars?/token"
        r"|\b(special|control|sentinel|canary|inert|benign|unique)[ _-](\w+[ _-])?tokens?\b"
        r"|design[- ]system tokens?|\bDS tokens\b|tokens/[\w-]+\.css"
        r"|\bClientSession\b|requests\.Session\(\)|\bAsyncSession\b|\w*sessionmaker\b|\bget_session\(\)|\bdb\.session\b"
        r"|\bsession\.(add|commit|rollback|execute|query|flush|scalars?|begin|run)\(|\.session\(\)"
        r"|\bprocess[_ ]groups?\b|\bsession leader\b|AVAudioSession\w*|\baudio ?session\w*|\bsession[- ]bus\b"
        r"|\bstack[ _]?cookies?\w*|\bStackCookie\b"
        r"|\b(next|prior|previous|working|debugging|chat|LLM|agent|coding|training|interactive|knowledge[- ]sharing) sessions?\b"
        r"|\bSession(Start|End)\b"
        # a quota or scope, not session management: MAX_LOOPS_PER_SESSION, max_messages_per_session,
        # "per-session sliding window". 129 local lines read 2026-11-17, all quota or scope but one: "a
        # per-session token printed at startup", which the older `per[- ](\w+ )?tokens?` sense above
        # already blanked (a pre-existing miss, not this line's). Only the phrase is blanked, so a
        # session word beside it still fires ("the per-session cookie").
        r"|(?:\b|_)per[_ -]sessions?\b",
        re.I),
}


# A raw string that IS a regular expression describes text; it does not do what its words say. A
# detector's own pattern table (`r"subprocess|os\.system|..."`) fired "runs a process", and a
# Stop hook's word list fired "accepts a file". Of 60 sampled lines over 67,524 local Python files
# whose every match of a row sat inside a raw string, 60 were pattern source (2026-11-17). Only
# regex-shaped raw strings are blanked (an escape class, a group or an unspaced `a|b`), so a raw
# string holding SQL, including `a || b`, still fires.
RAW_STRING = re.compile(r"""(?<![A-Za-z0-9_])[rR][bB]?("[^"\n]*"|'[^'\n]*')""")
REGEX_SHAPED = re.compile(r"\\[bBdDsSwW.]|\(\?|\w\|\w")


def blank_regex_literals(text: str) -> str:
    return RAW_STRING.sub(lambda m: " " * len(m.group(0)) if REGEX_SHAPED.search(m.group(0))
                          else m.group(0), text)


def row_match(what: str, rx: re.Pattern, text: str) -> re.Match | None:
    """The row's first match in `text` after regex-shaped raw strings and its EXCLUDE senses are
    blanked, or None. Blanking keeps offsets, so the match indexes the original text."""
    text = blank_regex_literals(text)
    ex = EXCLUDE.get(what)
    return rx.search(ex.sub(lambda m: " " * len(m.group(0)), text) if ex else text)


def evidence(text: str, m: re.Match) -> str:
    """The matched word in its line, so the agent can see WHY a row fired: one printable,
    backtick-free line of at most about 72 characters."""
    start = text.rfind("\n", 0, m.start()) + 1
    end = text.find("\n", m.end())
    line = text[start:end if end != -1 else len(text)]
    col = m.start() - start
    if len(line) > 72:
        lo = max(0, col - 30)
        line = ("…" if lo else "") + line[lo:lo + 70] + ("…" if lo + 70 < len(line) else "")
    return re.sub(r"[\x00-\x1f\x7f-\x9f`]", " ", line).strip()

# Rows the hook fires on that --router-table does NOT render (operator decision 2026-10-22,
# ADOPTION-LOG). The router is at its 500-line cap, and its rows are the evidence base v12 measured
# reach from, so a new trigger starts here, in the hook only, and is promoted into the router once
# its reach is measured. Each entry is a row's `what`; --self-test fails on a name with no row.
HOOK_ONLY = {
    "runs or configures a container or sandbox (seccomp, capabilities, namespaces)",
    "sets or disables an LSM profile (AppArmor, SELinux)",
    "builds a command-line interface",
    "reads from a process substitution, whose exit status is unreachable",
    "configures PAM, a login stack",
    "calls a model API: output cap, stop reason and spend",
    "configures a dependency-update bot (Dependabot)",
    "writes a CI workflow (GitHub Actions)",
    "writes a container image (Dockerfile)",
    "opens network access in infrastructure code (Terraform)",
    "grants wildcard IAM permissions in infrastructure code (Terraform)",
    "makes storage public or unencrypted in infrastructure code (Terraform)",
    "renders raw HTML in a component (v-html, {@html})",
    "turns template escaping off",
    "writes unescaped output in an EJS template",
    "evaluates a string as code or bypasses execution policy (PowerShell)",
    "changes a schema in a way that locks or rewrites a table (SQL DDL)",
}
# The only rows that also read CONFIG_EXT files. Each name must be a trigger row (--self-test).
CONFIG_ROWS = {
    "configures a dependency-update bot (Dependabot)",
    "writes a CI workflow (GitHub Actions)",
    "writes a container image (Dockerfile)",
    "runs or configures a container or sandbox (seccomp, capabilities, namespaces)",
    "sets or disables an LSM profile (AppArmor, SELinux)",
    "configures PAM, a login stack",
}
# Rows that fire on config files only, never on code: their words also occur in code (SQL's FROM).
CONFIG_ONLY = {
    "configures a dependency-update bot (Dependabot)",
    "writes a CI workflow (GitHub Actions)",
    "writes a container image (Dockerfile)",
}
# Per-file-type rows: they fire only for these extensions, and these files get no ordinary code row.
_TEMPLATE = {"turns template escaping off"}
_TF = {"opens network access in infrastructure code (Terraform)",
       "grants wildcard IAM permissions in infrastructure code (Terraform)",
       "makes storage public or unencrypted in infrastructure code (Terraform)"}
_RAW = {"renders raw HTML in a component (v-html, {@html})"}
_PS = {"evaluates a string as code or bypasses execution policy (PowerShell)"}
TYPED_ROWS = {
    "tf": _TF, "vue": _RAW, "svelte": _RAW,
    "html": _TEMPLATE, "htm": _TEMPLATE, "jinja": _TEMPLATE, "jinja2": _TEMPLATE, "j2": _TEMPLATE,
    "erb": _TEMPLATE, "hbs": _TEMPLATE, "njk": _TEMPLATE,
    "ejs": {"writes unescaped output in an EJS template"},
    "ps1": _PS, "psm1": _PS,
    "sql": {"changes a schema in a way that locks or rewrites a table (SQL DDL)"},
}
CONFIG_ONLY |= set().union(*TYPED_ROWS.values())   # typed rows never fire on ordinary code
DOCKERFILE_NAME = re.compile(r"^(?:dockerfile|containerfile)(?:\..+)?$|\.(?:dockerfile|containerfile)$", re.I)


def rows_for(path: str) -> set[str] | None:
    """The trigger names to try for a written file: config rows for config files and Dockerfiles,
    every row but the config-only ones for code, and None to skip the file."""
    name = path.rsplit("/", 1)[-1]
    if DOCKERFILE_NAME.search(name):
        return set(CONFIG_ROWS)
    # The Dockerfile row reads Dockerfile-named files only: matched case-blind, its FROM line is
    # Python's `from __future__` in a `.py.j2` template (15 of 17 .j2 hits, measured 2026-11-18).
    config = set(CONFIG_ROWS) - {"writes a container image (Dockerfile)"}
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext in TYPED_ROWS:   # .j2 is a config file too: it keeps the config rows
        return set(TYPED_ROWS[ext]) | (config if ext in CONFIG_EXT else set())
    if ext in CODE_EXT:
        return {w for w, _, _ in TRIGGERS} - CONFIG_ONLY
    if ext in CONFIG_EXT:
        return config
    return None


def skill_dir(name: str) -> Path | None:
    """The copy of the skill the session loads: the user config first, then a plugin root, then
    this checkout (the same order as skill-depth-hook.py)."""
    cands = []
    if os.environ.get("CLAUDE_CONFIG_DIR"):
        cands.append(Path(os.environ["CLAUDE_CONFIG_DIR"]) / "skills")
    cands.append(Path.home() / ".claude" / "skills")
    if os.environ.get("CLAUDE_PLUGIN_ROOT"):
        cands.append(Path(os.environ["CLAUDE_PLUGIN_ROOT"]) / "skills")
    cands.append(ROOT / "skills")
    for c in cands:
        if (c / name / "SKILL.md").is_file():
            return c / name
    return None


def rules_file(skill: str, num: str) -> Path | None:
    d = skill_dir(skill)
    hits = sorted((d / "rules").glob(num + "-*.md")) if d else []
    return hits[0] if hits else None


def written_text(tool_input: dict) -> str:
    parts = [tool_input.get("content"), tool_input.get("new_string")]
    parts += [e.get("new_string") for e in tool_input.get("edits") or [] if isinstance(e, dict)]
    return "\n".join(p for p in parts if isinstance(p, str))


def state_dir(session_id: str) -> Path:
    """One marker file per rules file named in this session; its content is the path."""
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", session_id or "nosession")[:80]
    return Path(tempfile.gettempdir()) / "sota-code-rules-hook" / safe


def named_before(d: Path) -> set[str]:
    try:
        return {m.read_text(encoding="utf-8") for m in d.iterdir()}
    except OSError:
        return set()


def claim(d: Path, p: Path) -> bool:
    """True for exactly one caller per (session, file), even when two copies race."""
    d.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(d / hashlib.sha256(str(p).encode()).hexdigest()[:32],
                     os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(str(p))
    return True


def select(text: str, already: set[str], rows: set[str] | None = None) -> list[tuple[str, Path, str]]:
    """(what the code does, rules file, sections) for up to PER_EVENT files not named before. A
    second trigger naming a file already picked adds its reason and section to that entry.
    `rows`, when given, limits the triggers to those names (a config file's CONFIG_ROWS)."""
    picked: dict[Path, tuple[list[str], list[str]]] = {}
    for what, rx, refs in COMPILED:
        if rows is not None and what not in rows:
            continue
        m = row_match(what, rx, text)
        if not m:
            continue
        why = '%s (matched: "%s")' % (what, evidence(text, m))
        for skill, num, section in refs:
            p = rules_file(skill, num)
            if p is None or str(p) in already:
                continue
            if p in picked:
                if why not in picked[p][0]:
                    picked[p][0].append(why)
                picked[p][1].append(section)
            elif len(picked) < PER_EVENT:
                picked[p] = ([why], [section])
    return [("; ".join(w), p, "; ".join(s)) for p, (w, s) in picked.items()]


# ROADMAP 99 (2026-11-18): the language skill for code the session writes. The router's cross-cutting
# rule 1 says to load it; over one operator's 94 sessions (436 transcripts), 66 of 116 (session,
# language) pairs had no tool call naming the skill before the first edit (2026-11-18). So the first edit of a
# language whose skill no TOOL CALL has named gets one note per session, naming the skill's SKILL.md
# (its index), not its rules files: v14 measured whole rules-file reads as ~90% of a +38% cost.
LANG_SKILL = {"py": "sota-python", "pyi": "sota-python", "go": "sota-golang", "rs": "sota-rust",
              "c": "sota-c-cpp", "h": "sota-c-cpp", "cc": "sota-c-cpp", "cpp": "sota-c-cpp",
              "cxx": "sota-c-cpp", "hpp": "sota-c-cpp", "java": "sota-jvm", "kt": "sota-jvm",
              "kts": "sota-jvm", "cs": "sota-dotnet", "php": "sota-php", "rb": "sota-ruby",
              "swift": "sota-swift", "js": "sota-javascript-typescript", "jsx": "sota-javascript-typescript",
              "mjs": "sota-javascript-typescript", "cjs": "sota-javascript-typescript",
              "ts": "sota-javascript-typescript", "tsx": "sota-javascript-typescript",
              "sh": "sota-shell-scripting", "bash": "sota-shell-scripting"}


def lang_skill(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    return LANG_SKILL.get(name.rsplit(".", 1)[-1].lower(), "") if "." in name else ""


def skill_named(transcript: str, skill: str) -> bool:
    """True when a TOOL CALL in the transcript names the skill (a Skill call, a read, a command).
    Raw text is not enough: the transcript also stores the skills listing, which names every skill
    (measured 2026-11-18: `skill_listing` and `instructions` attachments)."""
    try:
        with open(transcript, encoding="utf-8", errors="replace") as f:
            for line in f:
                if skill not in line or '"tool_use"' not in line:
                    continue
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                c = (o.get("message") or {}).get("content") if isinstance(o, dict) else None
                for b in c if isinstance(c, list) else []:
                    if isinstance(b, dict) and b.get("type") == "tool_use" and skill in json.dumps(b.get("input")):
                        return True
    except (OSError, TypeError):
        return False
    return False


def language_note(path: str, skill: str) -> str:
    d = skill_dir(skill)
    if d is None:
        return ""
    return ("SOTA: this session writes %s code (%s), and no tool call in it has loaded the language "
            "skill yet. Its index is %s: its Top-10 non-negotiables and its rules index (which rules "
            "file to read for what this code does) apply to this and every later edit in the language. "
            "Read it before the next edit." % (skill.removeprefix("sota-"), path, d / "SKILL.md"))


APPLY = ("These rules apply to this change: they are part of what was asked, not extras beyond the spec. "
         "Build what each one requires now, with a conservative default (a cap, a limit, an allow-list, a "
         "guard). Do not hand it back as a question or a note instead of building it, unless the user's "
         "request explicitly rules it out. In your final message, name each default you chose in one line, "
         "so the user can change it.")


def message(path: str, picks: list[tuple[str, Path, str]]) -> str:
    lines = ["SOTA: the code you just wrote in %s:" % path]
    for what, p, section in picks:
        lines.append("- %s. Its rules: %s (check %s)" % (what, p, section))
    lines.append("Read each file named above in full now — every line, with no offset, limit, head, "
                 "line range or grep, because a rule you did not read cannot be applied. Then check "
                 "this change against it, including the Audit checklist at its end, before you finish.")
    lines.append(APPLY)
    return "\n".join(lines)


def respond(event: dict) -> str:
    """The JSON to print for one PostToolUse event, or "" for nothing. Records what it named."""
    if event.get("tool_name") not in {"Edit", "Write", "MultiEdit"}:
        return ""
    ti = event.get("tool_input") or {}
    path = str(ti.get("file_path") or "")
    rows = rows_for(path)
    if rows is None:
        return ""
    if TEST_PATH.search(path) or SCRATCH_PATH.search(path):
        return ""
    sd = state_dir(str(event.get("session_id") or ""))
    picks = [x for x in select(written_text(ti), named_before(sd), rows) if claim(sd, x[1])]
    lang = ""
    skill = lang_skill(path)
    # claimed once per session even when the skill is loaded, so the transcript is read at most once
    if skill and claim(sd, Path("lang:" + skill)) and not skill_named(str(event.get("transcript_path") or ""), skill):
        lang = language_note(path, skill)
    if not picks and not lang:
        return ""
    text = "\n\n".join(x for x in (message(path, picks) if picks else "", lang) if x)
    return json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                              "additionalContext": text[:LIMIT]}})


TABLE_HEADING = "## What your code does: the rules outside this skill"


def table() -> str:
    """The trigger table as Markdown for a language skill's SKILL.md, paths relative to that file.
    The same rows the hook fires on, so an index link and the hook name the same files."""
    out = [TABLE_HEADING, "",
           "When the code you write does one of these things, the rule for it lives in another skill. "
           "Read that file in full before you finish, and check your change against its Audit checklist.",
           "", "| When your code... | Read in full | Check |", "|---|---|---|"]
    for what, _, refs in TRIGGERS:
        for skill, num, section in refs:
            hits = sorted((ROOT / "skills" / skill / "rules").glob(num + "-*.md"))
            if hits:
                rel = "../%s/rules/%s" % (skill, hits[0].name)
                out.append("| %s | [%s rules/%s](%s) | %s |" % (what, skill, num, rel, section))
    return "\n".join(out) + "\n"


ROUTER = ROOT / "skills" / "sota" / "SKILL.md"
ROUTER_HEADING = "## What your code does: the rules file to read"


def router_table() -> str:
    """The same triggers as a section of the router (ROADMAP 73 (o)), one row per set of files, so
    an agent that never runs this hook (any host but Claude Code) still finds the file from the
    words of its task. v12: a cited file was reached in 5 of 7 tasks where the router linked it next
    to matching words, 1 of 13 where it did not. Generated; the self-test fails if the router's copy
    differs."""
    groups: dict[tuple, list[str]] = {}            # one row per set of files, in table order
    for what, _, refs in TRIGGERS:
        if what in HOOK_ONLY:
            continue
        what = what.split(", which")[0]
        if len(refs) == 1:                         # one file: its section goes beside the words
            skill, num, section = refs[0]
            groups.setdefault(((skill, num, ""),), []).append("%s (%s)" % (what, section))
        else:
            groups.setdefault(tuple(refs), []).append(what)
    out = [ROUTER_HEADING, "",
           "When the code you are about to write does one of these things, read the file in full, then",
           "check your change against it and its Audit checklist before you finish. " + APPLY, "",
           "| When your code... | Read in full, then check |", "|---|---|"]
    for refs, whats in groups.items():
        cells = []
        for skill, num, section in refs:
            hits = sorted((ROOT / "skills" / skill / "rules").glob(num + "-*.md"))
            if hits:
                cells.append(("[`%s` rules/%s](../%s/rules/%s) %s" % (skill, num, skill, hits[0].name, section)).rstrip())
        out.append("| %s | %s |" % ("; ".join(whats), "; ".join(cells)))
    return "\n".join(out) + "\n"


def router_section(text: str) -> str:
    """The router's copy: from ROUTER_HEADING to the next level-2 heading."""
    i = text.find(ROUTER_HEADING)
    if i < 0:
        return ""
    j = text.find("\n## ", i + len(ROUTER_HEADING))
    return text[i:j + 1 if j >= 0 else len(text)].rstrip("\n") + "\n"


def replay_language(root: str) -> int:
    """Where the language note would have fired in local transcripts, with this hook's own filters:
    per transcript, in time order, the first non-test, non-scratchpad edit of a language whose skill
    no earlier tool call named. Prints notes, the edits of that language after each note (what the
    note could still reach), and how often the skill was named later anyway."""
    files = with_edits = with_note = notes = zero_after = named_later = 0
    after: list[int] = []
    per: dict[str, int] = {}
    for dp, _dn, fn in os.walk(os.path.expanduser(root), followlinks=True):
        for f in fn:
            if not f.endswith(".jsonl"):
                continue
            calls: dict[str, tuple[str, str, dict]] = {}
            with open(os.path.join(dp, f), encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if '"tool_use"' not in line:
                        continue
                    try:
                        o = json.loads(line)
                    except ValueError:
                        continue
                    c = (o.get("message") or {}).get("content") if isinstance(o, dict) else None
                    for b in c if isinstance(c, list) else []:
                        if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id") not in calls:
                            calls[b["id"]] = (str(o.get("timestamp") or ""), str(b.get("name")), b.get("input") or {})
            seq = sorted(calls.values(), key=lambda x: x[0])
            if not seq:
                continue
            files += 1
            named: set[str] = set()
            noted: dict[str, int] = {}
            edited = False
            for i, (_ts, name, inp) in enumerate(seq):
                text = json.dumps(inp)
                named |= {sk for sk in set(LANG_SKILL.values()) if sk in text}
                if name not in {"Edit", "Write", "MultiEdit"}:
                    continue
                path = str(inp.get("file_path") or "")
                sk = lang_skill(path)
                if not sk or TEST_PATH.search(path) or SCRATCH_PATH.search(path):
                    continue
                edited = True
                if sk in noted or sk in named:
                    continue
                noted[sk] = i
            with_edits += edited
            with_note += bool(noted)
            for sk, i in noted.items():
                notes += 1
                per[sk] = per.get(sk, 0) + 1
                later = seq[i + 1:]
                n_after = sum(1 for _t, nm, inp in later if nm in {"Edit", "Write", "MultiEdit"}
                              and lang_skill(str(inp.get("file_path") or "")) == sk
                              and not TEST_PATH.search(str(inp.get("file_path") or "")))
                after.append(n_after)
                zero_after += n_after == 0
                named_later += any(sk in json.dumps(inp) for _t, _n, inp in later)
    after.sort()
    print("transcripts %d; with a code edit %d; with a note %d; notes %d" % (files, with_edits, with_note, notes))
    print("  by skill: " + ", ".join("%s %d" % kv for kv in sorted(per.items(), key=lambda kv: -kv[1])))
    if after:
        print("  edits of the language after the note: median %d; none after %d; skill named later anyway %d"
              % (after[len(after) // 2], zero_after, named_later))
    return 0 if files else 1


def main() -> int:
    if os.environ.get("SOTA_CODE_RULES_HOOK", "on").lower() in {"off", "0", "false", "no"}:
        return 0
    try:
        out = respond(json.load(sys.stdin))
    except Exception as e:                      # never block a tool result
        print("sota code-rules-hook: %s: %s — no hint this time" % (type(e).__name__, e),
              file=sys.stderr)
        return 0
    if out:
        print(out)
    return 0


def self_test() -> int:
    """Drives the script as Claude Code does (JSON on stdin) and checks its output."""
    fails: list[str] = []
    n = 0

    def check(label, cond):
        nonlocal n
        n += 1
        if not cond:
            fails.append(label)

    with tempfile.TemporaryDirectory() as t:
        env = {k: v for k, v in os.environ.items() if k != "SOTA_CODE_RULES_HOOK"}
        env.update({"TMPDIR": t, "HOME": t, "CLAUDE_CONFIG_DIR": str(Path(t) / "no-config")})   # resolve to THIS checkout

        def run(event, extra=None, raw=None):
            p = subprocess.run([sys.executable, str(Path(__file__).resolve())],
                               input=raw if raw is not None else json.dumps(event),
                               capture_output=True, text=True, env=dict(env, **(extra or {})), timeout=30)
            c = json.loads(p.stdout)["hookSpecificOutput"]["additionalContext"] if p.stdout.strip() else ""
            return p.returncode, c, p.stderr

        # A transcript in which the Python skill was loaded by a tool call: the rules-trigger checks
        # below use it, so the language note (ROADMAP 99) stays out of their way.
        loaded = Path(t) / "loaded.jsonl"
        loaded.write_text(json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": "x1", "name": "Skill", "input": {"skill": "sota-python"}}]}}) + "\n",
            encoding="utf-8")

        def ev(sid, path, text, tool="Write", transcript=None):
            ti = {"file_path": path, "content": text} if tool == "Write" else {"file_path": path, "new_string": text}
            return {"tool_name": tool, "session_id": sid, "tool_input": ti,
                    "transcript_path": str(transcript if transcript is not None else loaded)}

        cs01 = str(ROOT / "skills" / "sota-code-security" / "rules")
        rc, c, _ = run(ev("s1", "/w/shop/export.py", "import csv\nw = csv.writer(f)\n"))
        check("csv: exit 0", rc == 0)
        check("csv: names code-security/01 by absolute path", (cs01 + "/01-") in c and "CSV/formula" in c)
        check("csv: one concrete action, a full read", "Read each file named above in full" in c
              and "Audit checklist" in c)
        check("csv: the rule is part of the task, with no hand-back exit", "they are part of what was asked" in c
              and "Do not hand it back" in c and "conservative default" in c)
        rc, c, _ = run(ev("s1", "/w/shop/export.py", "w.writerow(row)  # csv again\nimport csv\n", "Edit"))
        check("same file is not named twice in a session", c == "")
        rc, c, _ = run(ev("s2", "/w/shop/export.py", "import csv\n", "Edit"))
        check("another session names it again", "01-" in c)
        rc, c, _ = run(ev("s3", "/w/shop/a.py", "import zipfile\nz.extractall(d)\nr = requests.get(u)\n"))
        check("at most %d files per edit" % PER_EVENT, c.count("Its rules:") == PER_EVENT)
        check("table order: the fetch (row 1) before the archive (row 3)",
              c.find("SSRF") != -1 and c.find("SSRF") < c.find("Zip Slip"))
        check("a second section of a file already picked is merged, not dropped",
              c.count("01-input-injection") == 1 and "Zip Slip" in c and "09-untrusted" in c)
        rc, c, _ = run(ev("s4", "/w/shop/api.py", "    def search(self, q):\n        return 200, {}\n", "Edit"))
        check("handler: names the rate-limiting files", "07-security-operations" in c and "06-memory" in c)
        rc, c, _ = run({"tool_name": "MultiEdit", "session_id": "s5",
                        "tool_input": {"file_path": "/w/a.py", "edits": [{"old_string": "x", "new_string": "import tarfile"}]}})
        check("MultiEdit edits are read", "Zip Slip" in c)
        for label, e in (("test file is silent", ev("s6", "/w/tests/test_export.py", "import csv")),
                         ("test_ prefix is silent", ev("s6", "/w/test_export.py", "import csv")),
                         # hyphenated names, this repository's own convention (scripts/test-*.sh);
                         # field-reported 2026-11-10: every test here was read as shipped code
                         # (own sessions: in s6 a first fire would hide the second, once per session)
                         ("test- prefix is silent", ev("s6a", "/w/scripts/test-export.sh", "import csv")),
                         ("-test suffix is silent", ev("s6b", "/w/scripts/export-test.sh", "import csv")),
                         ("scratchpad file is silent", ev("s6", "/tmp/claude-1/x/scratchpad/poc.py", "import csv")),
                         ("markdown is silent", ev("s6", "/w/README.md", "export as csv")),
                         ("no trigger is silent", ev("s6", "/w/a.py", "x = 1 + 2\n")),
                         ("other tool is silent", {"tool_name": "Bash", "tool_input": {"command": "csv"}})):
            rc, c, _ = run(e)
            check(label, rc == 0 and c == "")
        # Config files: only CONFIG_ROWS fire. A generic row's words in YAML stay silent; JSON is not read.
        rc, c, _ = run(ev("s8", "/w/roles/selinux/tasks/main.yml", "- name: relax\n  shell: setenforce 0\n"))
        check("config: a host-config row fires on YAML", "02-linux-os-hardening" in c and "§6 LSMs" in c)
        rc, c, _ = run(ev("s9", "/w/deploy/app.yaml", "role: admin\ntimeout: 30\nlogging: debug\npassword: x\n"))
        check("config: generic rows are silent on YAML", rc == 0 and c == "")
        rc, c, _ = run(ev("s10", "/w/i18n/th.json", '{"unshare": "x", "setenforce 0": "y"}'))
        check("config: JSON is not read", rc == 0 and c == "")
        rc, c, _ = run(ev("s12", "/w/app/scratchpad_utils.py", "import csv\n"))
        check("a shipped file NAMED like scratchpad still fires (segment, not substring)", "01-" in c)
        # The test-name filter must not swallow shipped files that merely contain "test".
        for i, path in enumerate(("/w/scripts/latest.sh", "/w/app/contest_x.py", "/w/app/testimony.py")):
            rc, c, _ = run(ev("s13-%d" % i, path, "import csv\n"))
            check("a shipped file containing 'test' still fires: %s" % path.rsplit("/", 1)[1], "01-" in c)
        # ROADMAP 99: the language note, once per session, only when no tool call loaded the skill
        listing = Path(t) / "listing.jsonl"
        listing.write_text(json.dumps({"type": "attachment", "attachment": {"type": "skill_listing",
                           "content": "sota-python: ... sota-rust: ..."}}) + "\n" + json.dumps(
            {"type": "assistant", "message": {"role": "assistant", "content": [
                {"type": "tool_use", "id": "y", "name": "Bash", "input": {"command": "ls"}}]}}) + "\n", encoding="utf-8")
        # joinpath, not `ROOT / "skills" / …`: check-plugin-dist.py reads that shape as a file the hook
        # loads at run time and requires it in its minimal known-good tree
        py_md = str(ROOT.joinpath("skills", "sota-python", "SKILL.md"))
        rc, c, _ = run(ev("L1", "/w/app/core.py", "x = 1\n", transcript=listing))
        check("language note: fires when only the skills listing names the skill", py_md in c and "rules index" in c)
        rc, c, _ = run(ev("L1", "/w/app/other.py", "y = 2\n", transcript=listing))
        check("language note: once per session", c == "")
        rc, c, _ = run(ev("L1", "/w/app/lib.rs", "fn f() {}\n", transcript=listing))
        check("language note: a second language gets its own note", "sota-rust" in c and "SKILL.md" in c)
        rc, c, _ = run(ev("L2", "/w/app/core.py", "x = 1\n"))
        check("language note: silent when a tool call loaded the skill", c == "")
        rc, c, _ = run(ev("L3", "/w/app/core.py", "x = 1\n", transcript=Path(t) / "missing.jsonl"))
        check("language note: an unreadable transcript still reminds", py_md in c)
        rc, c, _ = run(ev("L4", "/w/tests/test_core.py", "x = 1\n", transcript=listing))
        check("language note: a test file is silent", c == "")
        rc, c, _ = run(ev("L5", "/w/app/export.py", "import csv\nw = csv.writer(f)\n", transcript=listing))
        check("language note: combined with a rules note in one message", "01-" in c and py_md in c)
        rc, c, _ = run(ev("L6", "/w/README.md", "python code", transcript=listing))
        check("language note: markdown is silent", c == "")
        rc, c, _ = run(ev("s7", "/w/a.py", "import csv"), {"SOTA_CODE_RULES_HOOK": "off"})
        check("opt-out is silent", rc == 0 and c == "")
        # Two copies on one edit (plugin + installer, run in parallel) must not both name a file.
        # Checked on claim() itself: two parallel processes barely overlap, so a run-twice test
        # passed even with the exclusive create removed (watched 2026-10-12).
        d, f = Path(t) / "claim", ROOT / "x.md"
        check("claim: the first caller wins", claim(d, f) is True)
        check("claim: a second caller for the same file loses", claim(d, f) is False)
        check("claim: the marker records the path", named_before(d) == {str(f)})
        rc, c, err = run(None, raw="{not json")
        check("malformed input: exit 0, no output, says why", rc == 0 and c == "" and "code-rules-hook" in err)

    # Labelled trigger cases from three field reports of 2026-10-20 (ADOPTION-LOG). Checked on the
    # compiled table directly, because the once-per-session rule would hide a second fire.
    def fires(what, text):
        return any(w.startswith(what) and row_match(w, rx, text) for w, rx, _ in COMPILED)

    for text in ('@require_role("editor")', "if not current_user.roles: deny()",
                 "SELECT * FROM user_roles", 'if not has_role(u, "ops"): deny()', "role_required(x)"):
        check("authorization form fires (a missed one costs the rule): %s" % text,
              fires("decides who may do what", text))
    # 2026-11-17: a detector's regex table and a quota name are not the behaviour they mention ...
    for what, text in (("runs a process", 'ROW = r"subprocess|os\\.system|shell=True"'),
                       ("accepts a file or image from outside", 'CONTROL = re.compile(r"(?:zip|archive|upload|tls)")'),
                       ("issues or checks a session or token", 'MAX_PER_SESSION = int(os.environ.get("X", "3"))'),
                       ("issues or checks a session or token", "max_messages_per_session: int = 1000")):
        check("quiet: %s" % text, not fires(what, text))
    # 2026-11-18: a Dependabot config names the cooldown rule; a CI workflow does not
    check("Dependabot config fires the update-bot row",
          fires("configures a dependency-update bot", "version: 2\nupdates:\n  - package-ecosystem: pip\n"))
    check("a workflow does not fire the update-bot row",
          not fires("configures a dependency-update bot", "on: push\njobs:\n  t:\n    runs-on: ubuntu-latest\n"))
    # 2026-11-18: workflows and Dockerfiles route to config rows; code never fires config-only rows
    def picks_for(path, text):
        r = rows_for(path)
        return [] if r is None else [w for w, _, _ in COMPILED if w in r and row_match(w, _rx(w), text)]
    def _rx(w):
        return next(rx for x, rx, _ in COMPILED if x == w)
    wf = "on: push\npermissions: {}\njobs:\n  t:\n    runs-on: ubuntu-latest\n"
    df = "FROM python:3.14-slim\nRUN pip install x\nUSER 1000\n"
    sql = 'Q = """\nSELECT id\nFROM users\nWHERE id = ?\n"""\n'
    check("a workflow fires the CI-workflow row", "writes a CI workflow (GitHub Actions)" in picks_for(".github/workflows/ci.yml", wf))
    check("Dockerfile routes to config rows and fires", "writes a container image (Dockerfile)" in picks_for("Dockerfile", df))
    check("Dockerfile.prod and app.containerfile route too",
          rows_for("Dockerfile.prod") is not None and rows_for("app.containerfile") is not None)
    check("SQL's FROM in Python never fires the Dockerfile row",
          "writes a container image (Dockerfile)" not in picks_for("app/db.py", sql))
    check("a file with no extension that is not a Dockerfile is skipped", rows_for("Makefile") is None)
    # 2026-11-18 per-file-type rows: each fires on its construct, stays quiet on the near miss, and
    # never on ordinary code that happens to contain the same words.
    typed_cases = [
        ("main.tf", 'ingress {\n  cidr_blocks = ["0.0.0.0/0"]\n}', 'ingress {\n  cidr_blocks = ["10.0.0.0/8"]\n}',
         "opens network access in infrastructure code (Terraform)"),
        ("iam.tf", 'actions = ["*"]', 'actions = ["s3:GetObject"]',
         "grants wildcard IAM permissions in infrastructure code (Terraform)"),
        ("s3.tf", 'block_public_acls = false', 'block_public_acls = true',
         "makes storage public or unencrypted in infrastructure code (Terraform)"),
        ("Comment.vue", '<div v-html="body"></div>', '<div v-text="body"></div>',
         "renders raw HTML in a component (v-html, {@html})"),
        ("Note.svelte", '{@html note}', '{note}', "renders raw HTML in a component (v-html, {@html})"),
        ("page.html", '{{ bio|safe }}', '{{ bio }}', "turns template escaping off"),
        ("show.html.erb", '<%== user.bio %>', '<%- if admin? %>', "turns template escaping off"),
        ("bio.ejs", '<div><%- user.bio %></div>', "<%- include('header') %>",
         "writes unescaped output in an EJS template"),
        ("run.ps1", 'Invoke-Expression $cmd', 'Get-Content $path', 
         "evaluates a string as code or bypasses execution policy (PowerShell)"),
        ("0002_add.sql", 'CREATE INDEX users_email ON users (email);',
         'CREATE INDEX CONCURRENTLY users_email ON users (email);\n-- CREATE INDEX old ON t (x);',
         "changes a schema in a way that locks or rewrites a table (SQL DDL)"),
    ]
    for path, bad, good, row in typed_cases:
        check("typed row fires on %s" % path, row in picks_for(path, bad))
        check("typed row quiet on the near miss in %s" % path, row not in picks_for(path, good))
    check("a .py.j2 template's `from __future__` never fires the Dockerfile row",
          "writes a container image (Dockerfile)" not in picks_for("roles/x/templates/mod.py.j2", "from __future__ import annotations\n"))
    check("Dockerfile.j2 still fires the Dockerfile row",
          "writes a container image (Dockerfile)" in picks_for("templates/Dockerfile.j2", "FROM python:3.14-slim\n"))
    check("ordinary code never fires a typed row",
          not any(w in picks_for("app/models.py", 'Q = "CREATE INDEX i ON t (x)"  # v-html {@html x}')
                  for w in set().union(*TYPED_ROWS.values())))
    check("a typed file gets no ordinary code row",
          picks_for("Comment.vue", "setTimeout(() => refresh(), 1000) // Permission granted") == [])
    check("every typed row names a rules file that exists",
          all(rules_file(sk, n) is not None for w, _, refs in TRIGGERS
              if w in set().union(*TYPED_ROWS.values()) for sk, n, _ in refs))
    # ... and the same words still fire where they are code or a real session
    for what, text in (("builds a database query", 'q = r"SELECT name FROM users WHERE id = " + uid'),
                       ("builds a database query", 'q = r"SELECT a || b FROM t WHERE id = " + uid'),
                       ("runs a process", 'subprocess.run(["ls", r"C:\\tmp"])'),
                       ("issues or checks a session or token", "the per-session cookie is set HttpOnly"),
                       ("issues or checks a session or token", 'response.set_cookie("session", sid)')):
        check("still fires: %s" % text, fires(what, text))
    # KNOWN false triggers, kept firing ON PURPOSE until a labelled set exists to tighten against
    # (ADOPTION-LOG 2026-10-20 deferral). If one of these stops firing, resolve that deferral.
    for what, text in (("logs, returns errors", "git -c user.email=t@example.invalid commit"),
                       ("returns a list that can grow", 'p.add_argument("--limit", type=int)'),
                       ("decides who may do what", 'role = m.get("role")\nif role == "user": pass'),
                       # 2026-10-21 field report: an HTTP-status client, and a CLI's error message
                       ("decides who may do what", 'if r.status == 403:\n    raise RuntimeError(f"GET {url} refused")'),
                       ("checks a password or handles a login",
                        'print("error: not authenticated with the registry", file=sys.stderr)'),
                       # 2026-10-22 field report: an OS tracing session, no authentication in sight
                       ("issues or checks a session or token",
                        "/// Decodes Task Scheduler events read from a private ETW session."),
                       # 2026-10-22 EDR closure report: WQL text read from an event, parsed as data, not run
                       ("builds a database query",
                        '/// The WMI consumer\'s "Query" field holds WQL such as SELECT * FROM __InstanceCreationEvent.'),
                       # 2026-10-23 field report: a client sending its OWN key outbound, and a ZMQ session class
                       ("issues or checks a session or token", 'headers = {"Authorization": f"Bearer {api_key}"}'),
                       ("decides who may do what", 'headers = {"Authorization": f"Bearer {api_key}"}'),
                       ("issues or checks a session or token", "class ConsumerSession:\n    pass"),
                       ("decides who may do what", 'cfg = {"ec_role": "producer"}'),
                       # 2026-10-22 resume pass: a C++ extension in a set literal, matched case-blind as "Cc"
                       ("builds an email or a message header", 'CODE_EXT = {"c", "h", "cc", "cpp"}'),
                       # 2026-10-24 field report: a red-team corpus generator; the words are test data
                       ("checks a password or handles a login",
                        'INTENTS = ["write a phishing email asking for login credentials"]'),
                       ("issues or checks a session or token",
                        '"""Token Smuggling: split a blocked word across two tokens."""'),
                       # 2026-10-26 field report: a script that only READS a CSV export, and LLM token counts
                       ("writes CSV or spreadsheet output", "rows = list(csv.DictReader(open(p)))"),
                       ("issues or checks a session or token", 'print(f"in {n_in} / out {n_out} tokens")'),
                       # 2026-11-01 field reports: a lint name containing "circuit", and a probe of a
                       # hard-coded loopback URL inside a --network none container
                       ("calls something that can fail or hang", 'LINTS = ["clippy::short_circuit_statement"]'),
                       ("fetches a URL", 'r = urllib.request.urlopen("http://127.0.0.1:8080/readyz")'),
                       # 2026-11-10 field report: jq's select() in a shell script (re.I), and a status
                       # line that only reads session_id from its input
                       ("builds a database query", "jq -r '.items[] | select(.ok)' <in.json"),
                       ("issues or checks a session or token", 'key="$(printf %s "$session_id" | cksum)"')):
        check("known false trigger still fires (see the deferral before changing): %s" % what,
              fires(what, text))

    # 2026-11-12 session/token EXCLUDE (resolves the deferral for that row): text made only of the
    # excluded senses goes quiet; any auth sense beside them still fires (a miss costs the rule).
    sess = "issues or checks a session or token"
    for text in ("let ts = TokenStream::new();", "resp = client.create(max_tokens=256)",
                 "db.session.commit()", "let s = AVAudioSession.sharedInstance()",
                 "fn configure(stack_cookie: u64)", "async with aiohttp.ClientSession() as s:"):
        check("excluded sense alone does not fire the session row: %s" % text, not fires(sess, text))
    for text in ("resp = client.create(max_tokens=256)\nsession_start()",
                 "let ts = TokenStream::new();\nif token != expected { deny() }",
                 "db.session.commit()\n$_SESSION['uid'] = $id", "jwt.verify(token, key)",
                 "res.cookie('sid', sid, { httpOnly: true })"):
        check("an auth sense beside an excluded one still fires: %s" % text.split(chr(10))[-1], fires(sess, text))
    # 2026-11-11 (this hook on a transcript parser): a class named Session for a Claude Code session.
    # A known false trigger that must still fire: no word list separates it, the evidence line does.
    check("known false trigger still fires: transcript Session class",
          fires(sess, 'class Session:\n    """One Claude Code session, read from its transcript."""'))
    # The evidence line: what matched, in its line, printable and backtick-free.
    ev = [w for w, _, _ in select("x = 1\nreq.session['uid'] = u  # `x`\x1b[2J", set())]
    check("the message names what matched, in its line: %s" % ev,
          any('matched: "' in w and "req.session" in w for w in ev))
    check("the evidence carries no backtick or control character",
          all("`" not in w and "\x1b" not in w for w in ev))
    long = "y = " + "a" * 200 + " session_id " + "b" * 200
    ev2 = [w for w, _, _ in select(long, set())]
    check("long-line evidence is cut around the match", any("session_id" in w and len(w) < 200 for w in ev2))

    # The real checkout: every file a trigger names exists, and every pattern compiles and fires on
    # at least one sample of its own (no dead row).
    missing = sorted({"%s/%s" % (s, n) for _, _, refs in TRIGGERS for s, n, _ in refs if rules_file(s, n) is None})
    check("every named rules file exists: %s" % missing, not missing)
    check("every trigger names at least one file", all(refs for _, _, refs in TRIGGERS))
    rows = [l for l in table().splitlines() if l.startswith("| ") and "](../" in l]
    check("--table: one row per (trigger, file) pair (%d)" % len(rows),
          len(rows) == sum(len(refs) for _, _, refs in TRIGGERS))
    check("the router's table is the generated one (python3 scripts/code-rules-hook.py --router-table)",
          router_section(ROUTER.read_text(encoding="utf-8")) == router_table())
    names = {what for what, _, _ in TRIGGERS}
    check("every HOOK_ONLY name is a trigger row: %s" % sorted(HOOK_ONLY - names), HOOK_ONLY <= names)
    check("every CONFIG_ROWS name is a trigger row: %s" % sorted(CONFIG_ROWS - names), CONFIG_ROWS <= names)
    check("config and code extensions do not overlap", not (CONFIG_EXT & CODE_EXT))
    rt = router_table()
    check("no HOOK_ONLY row reaches the router table", not any(w.split(", which")[0] in rt for w in HOOK_ONLY))
    for what, sample in (("builds a command-line interface", 'p = argparse.ArgumentParser(prog="x")'),
                         ("builds a command-line interface", "#[derive(clap::Parser)]"),
                         ("reads from a process substitution", 'done < <(select_items "$1")'),
                         ("reads from a process substitution", "mapfile -t rows < <(git rev-list -3 HEAD)"),
                         ("runs or configures a container", 'cmd = ["podman", "run", "--cap-drop=ALL", img]'),
                         ("runs or configures a container", "ctx.add_rule(SCMP_ACT_ERRNO(38), clone3)"),
                         ("configures PAM", 'line = "auth required pam_faillock.so preauth"'),
                         ("sets or disables an LSM profile", 'oci.WithApparmorProfile(""),'),
                         ("sets or disables an LSM profile", "run(['aa-complain', profile])"),
                         ("calls a model API", "r = client.messages.create(model=m, max_tokens=64000)"),
                         ("calls a model API", 'if r.choices[0].finish_reason == "length": raise Truncated')):
        check("hook-only row still fires in the hook: %s" % sample, fires(what, sample))
    for f in fails:
        print("FAIL:", f)
    print("%s: %d/%d" % ("FAIL" if fails else "PASS", n - len(fails), n))
    return 1 if fails else 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--router-table"]:
        sys.stdout.write(router_table())
        sys.exit(0)
    if sys.argv[1:2] == ["--replay-language"]:
        sys.exit(replay_language(sys.argv[2] if len(sys.argv) > 2 else "~/.claude/projects"))
    if sys.argv[1:] == ["--table"]:
        sys.stdout.write(table())
        sys.exit(0)
    sys.exit(self_test() if sys.argv[1:] == ["--self-test"] else main())
