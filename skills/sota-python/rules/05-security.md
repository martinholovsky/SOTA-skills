# 05 — Security

Trust-boundary thinking: anything from the network, files, env, DB content, or LLM output is
attacker-controlled until validated. The items below are the Python-specific exploit classes;
each has a grep signature — hunt them all in audits.

## 1. Deserialization & code execution bans

**`pickle` on untrusted data = remote code execution.** `pickle.loads` executes arbitrary
callables during load. Same family: `shelve`, `marshal`, `dill`, `joblib.load`, pandas
`read_pickle`, torch `torch.load` without `weights_only=True`.

```python
# Bad — RCE if attacker controls the bytes (cache poisoning, uploaded model, queue message)
obj = pickle.loads(blob)

# Good — data interchange uses data formats
obj = msgspec.json.decode(blob, type=Job)     # or json + pydantic validation
```

- Pickle is acceptable ONLY for same-trust-domain, integrity-protected data (e.g., local
  multiprocessing, HMAC-signed cache where the key never leaves the service). Document why.
- **`yaml.load` without SafeLoader = code execution.** Always `yaml.safe_load(f)` /
  `yaml.load(f, Loader=yaml.SafeLoader)`.
- **`eval`/`exec` on any string containing external input — banned.** "Sandboxing" with
  `{"__builtins__": {}}` is bypassable; don't review it, reject it. Need expressions? Use
  `ast.literal_eval` (data literals only), a real expression library (simpleeval has caveats
  too), or define a DSL with explicit dispatch.
- Templates: Jinja2 with autoescape on for HTML (`select_autoescape`); never render
  user-controlled **template strings** (SSTI → RCE), only user data into fixed templates.
  Same logic for `str.format` on user-supplied format strings (`"{0.__class__}"` walks objects).

## 2. Subprocess: argv lists, never shell=True

```python
# Bad — shell injection: filename = "x; rm -rf /"
subprocess.run(f"convert {filename} out.png", shell=True)

# Good — argv vector, no shell, timeout, checked
subprocess.run(
    ["convert", "--", filename, "out.png"],
    check=True, capture_output=True, timeout=30,
)
```

- `shell=True` with ANY variable in the string is a HIGH finding. Constant-string
  `shell=True` is still a smell (PATH games, IFS) — rewrite as a list.
- `--` before user-controlled positional args so `-rf`-style values can't become flags
  (argument injection — applies to git, curl, tar, find especially).
- Validate or allowlist executables; never let the user pick the binary. Set `timeout=`,
  handle `CalledProcessError`. `os.system` is banned outright.

## 3. SQL: parameters, never interpolation

```python
# Bad — injection, all variants: f-string, %, +, .format
cur.execute(f"SELECT * FROM users WHERE email = '{email}'")

# Good — driver parameters
cur.execute("SELECT * FROM users WHERE email = %s", (email,))

# Good — SQLAlchemy 2.0 style
stmt = select(User).where(User.email == email)
rows = session.execute(stmt).scalars().all()
# Raw SQL when needed — still bound params:
session.execute(text("SELECT * FROM users WHERE email = :email"), {"email": email})
```

- Identifiers (table/column names) can't be parameterized — allowlist them against a fixed
  set, never interpolate user input.
- `LIKE` patterns: escape `%` and `_` in user input before binding.
- Django ORM is parameterized by default; the dangerous edges are `.raw()`, `.extra()`,
  and `RawSQL` — audit every occurrence.

## 4. Path traversal

`Path` arithmetic does not sandbox: `base / "../../etc/passwd"` escapes, and absolute
user paths replace the base entirely (`Path("/srv") / "/etc/passwd"` → `/etc/passwd`).

```python
def safe_join(base: Path, user_path: str) -> Path:
    candidate = (base / user_path).resolve()
    if not candidate.is_relative_to(base.resolve()):   # 3.9+
        raise ValueError("path escapes base directory")
    return candidate
```

- Apply to every filename from uploads, URLs, archive members, config. Also reject `\0`
  and, for uploads, generate server-side names (uuid) instead of trusting client filenames.
- Symlinks: `resolve()` follows them — decide whether links inside `base` pointing out are
  acceptable (usually not for upload dirs: check `os.path.realpath` containment after write,
  or `O_NOFOLLOW`).

## 5. Archive extraction (zip/tar slip)

Malicious archives contain members named `../../home/user/.bashrc`, absolute paths, links,
or device nodes — and zip bombs (small file → TB of output).

```python
# Bad
tarfile.open(path).extractall(dest)

# Good — 3.12+: filter validates members (rejects traversal, abs paths, devices, bad links)
with tarfile.open(path) as tf:
    tf.extractall(dest, filter="data")
```

- `filter="data"` is mandatory on tar extraction (it became the default in 3.14; be explicit
  anyway). Pre-3.12: validate each member's resolved destination with the §4 containment check.
- The filter itself has had bypasses — CVE-2025-4517: symlink chains pushing the resolved
  path past PATH_MAX escaped the destination even with `filter="data"` (fixed in 3.12.11,
  3.13.4, 3.14+). Keep the interpreter patched and keep the §4 containment check as defense
  in depth; never treat the filter as the sole control for hostile archives.
- `zipfile.extractall` strips leading `/` and dots but still follow up with size limits:
  cap total uncompressed size and member count before extracting (read `ZipInfo.file_size`,
  enforce a budget) — `extractall` has no bomb protection.

## 6. Randomness & secrets

```python
# Bad — Mersenne Twister is predictable from outputs
token = "".join(random.choices(string.ascii_letters, k=32))

# Good
token = secrets.token_urlsafe(32)
code  = f"{secrets.randbelow(1_000_000):06d}"
```

- `random` for simulations only; anything security-relevant (tokens, password resets, session
  ids, OTPs, salts) uses `secrets` or `os.urandom`.
- Compare secrets with `secrets.compare_digest` / `hmac.compare_digest`, never `==` (timing).
- Passwords: argon2 (`argon2-cffi`) or bcrypt — never raw sha256/md5, never homemade salting.
- Secrets come from env/secret manager, not source. `.env` is gitignored; values never appear
  in `repr`/logs (dataclass `field(repr=False)`, pydantic `SecretStr`).
- TLS: never ship `verify=False` (requests/httpx) or `ssl._create_unverified_context`;
  pin an internal CA bundle instead.
- `hashlib.md5/sha1` only for non-security checksums — and mark it:
  `hashlib.md5(data, usedforsecurity=False)`.

## 7. XML & SSRF quickies

- Untrusted XML: use `defusedxml`; stdlib `etree` is OK against entity *expansion* on modern
  versions but external entity and DTD handling across libs (lxml!) still needs hardening:
  `lxml.etree.XMLParser(resolve_entities=False, no_network=True)`.
- SSRF: any user-supplied URL fetched server-side must be validated — scheme allowlist
  (`https` only), resolve and reject private/link-local/metadata ranges (169.254.169.254),
  disable redirects or re-validate per hop. httpx: set `follow_redirects=False` and handle
  explicitly.

## 8. Input-adjacent denial of service & injection oddities

- **ReDoS:** user input through a regex with nested/ambiguous quantifiers
  (`(a+)+`, `(.*)*`, `(\w+\s?)*`) can run exponentially. Audit every `re.*` whose pattern
  *or* subject is user-controlled; prefer anchored, linear patterns; set a length cap on the
  subject before matching; for hostile-input parsing consider the `regex` module's timeout
  or Rust-backed RE2 bindings.
- **Decompression bombs** beyond archives: `zlib.decompress`, image loading
  (`PIL.Image` — set `Image.MAX_IMAGE_PIXELS`, it defaults to a warning), XML entity
  expansion (§7). Enforce decoded-size budgets, not just encoded-size limits.
- **Log injection:** user strings logged verbatim can forge log lines (`\n` + fake record)
  or smuggle ANSI escapes into terminals. Strip/escape control characters at the logging
  formatter for user-supplied fields; one more reason for structured logging
  (fields are quoted) — see rules/03 §11.
- **`int()`/numeric parsing:** Python ints are unbounded — `int(user_str)` of a 10MB digit
  string allocates happily; 3.11+ caps str→int at 4300 digits by default
  (`sys.set_int_max_str_digits`) — don't raise that limit on request paths. Cap input length
  before parsing.
- **`webbrowser.open()` command injection:** crafted URLs (e.g. containing `%action`)
  passed to `webbrowser.open()` reach the shell with certain browser types —
  CVE-2026-4519 and its incomplete-fix follow-up CVE-2026-4786 (2026). Never pass
  user-influenced URLs; validate scheme/host first, and keep the interpreter patched.
- **Header/CRLF injection:** never place raw user input into HTTP headers, email headers
  (`email.message` does folding — still validate), or redis/SMTP protocol lines; reject
  `\r`/`\n` in any value destined for a protocol line.

## 9. Dependency & supply-chain hygiene

- **Audit continuously:** `uv run pip-audit` or `osv-scanner --lockfile uv.lock` in CI on a
  schedule, not just on PRs (new CVEs land against old lockfiles).
- **Hash-pinned, locked installs everywhere:** `uv.lock` records hashes; CI/containers use
  `uv sync --locked`. Exporting for pip: `uv export --format requirements-txt` includes
  `--hash` entries — keep them.
- **Typosquatting:** verify package names on first add (`requests` not `request`, `pillow`
  not `PIL` on PyPI, `python-dateutil` not `dateutil`). New transitive deps in a lockfile
  diff deserve a glance — lockfile diffs are security-relevant code review.
- **No `pip install` from URLs/git in prod paths** without commit pinning
  (`package @ git+https://...@<full-sha>`).
- **Publish via PyPI Trusted Publishing (OIDC), not long-lived API tokens.** The GhostAction
  campaign (Sept 2025) exfiltrated thousands of CI secrets including PyPI tokens via
  injected GitHub Actions workflows; PyPI invalidated the stolen tokens and recommends
  Trusted Publishers (short-lived, repo-scoped). With `pypa/gh-action-pypi-publish` ≥v1.11
  under a Trusted Publisher, PEP 740 attestations (build provenance) are generated by
  default — don't disable them. Pin third-party Actions by commit SHA, not tag.
- Don't run `setup.py`-era installs of unvetted sdists in CI with secrets in env — build
  scripts execute arbitrary code; prefer wheels, isolate builders.
- Each project in its own venv (uv default); never share one env across trust levels, never
  install into the interpreter that runs your OS tooling.
- Containers: multi-stage build, `uv sync --locked --no-dev`, run as non-root, no compiler
  toolchain in the final image.

## 10. Static analysis gates

- Ruff `S` ruleset (bandit port) in the standard select (rules/01) — covers most greps below
  natively: S301 pickle, S602 shell=True, S608 SQL strings, S324 weak hashes...
- `bandit -r src/ -ll` as a CI job if you want bandit's full set, plus `semgrep --config
  p/python` for taint-style findings.
- Suppressions (`# noqa: S...`, `# nosec`) require a justification comment; bare `# nosec`
  is itself a finding.

## Audit checklist

```bash
# One-shot scanners
uvx ruff check --select S --statistics .
uvx bandit -r src/ -ll -q
uv run pip-audit 2>/dev/null || uvx pip-audit
osv-scanner --lockfile uv.lock 2>/dev/null

# Code execution / deserialization [CRITICAL on untrusted data]
grep -rn "pickle.loads\|pickle.load\|read_pickle\|joblib.load\|marshal.loads\|dill" --include="*.py" src/
grep -rn "torch.load" --include="*.py" src/ | grep -v "weights_only=True"
grep -rn "yaml.load(" --include="*.py" src/ | grep -v "SafeLoader\|safe_load"
grep -rn "\beval(\|\bexec(" --include="*.py" src/ | grep -v "literal_eval\|model.eval()"
grep -rn "\.format(.*request\|f\".*{.*request" --include="*.py" src/ | head   # format-string gadgets

# Subprocess [HIGH]
grep -rn "shell=True" --include="*.py" src/
grep -rn "os.system\|os.popen" --include="*.py" src/

# SQL [CRITICAL]
grep -rn 'execute(f"\|execute(".*%s" *%\|execute(.*+ ' --include="*.py" src/
grep -rn "\.raw(\|\.extra(\|RawSQL" --include="*.py" src/                     # Django edges
grep -rn 'text(f"' --include="*.py" src/                                      # SQLAlchemy text+f-string

# Path traversal & archives [HIGH]
grep -rn "extractall\|extract(" --include="*.py" src/ | grep -v 'filter='
grep -rn "request.*filename\|\.filename" --include="*.py" src/                # then check containment
grep -rn "is_relative_to\|realpath" --include="*.py" src/                     # mitigations present?

# Randomness & secrets [HIGH]
grep -rn "random\.\(choice\|choices\|randint\|random\)" --include="*.py" src/ # security context?
grep -rn "== .*token\|token.* ==" --include="*.py" src/ | head                # timing-unsafe compare
grep -rn "verify=False\|_create_unverified" --include="*.py" src/
grep -rnE "(api_key|secret|password|token) *= *['\"][A-Za-z0-9_\-]{12,}" --include="*.py" .  # hardcoded
grep -rn "md5(\|sha1(" --include="*.py" src/ | grep -v usedforsecurity

# XML / SSRF
grep -rn "lxml.etree\|xml.etree\|xml.dom\|xml.sax" --include="*.py" src/      # defused? entities off?
grep -rn "get(url\|get(request\.\|urlopen(" --include="*.py" src/ | head      # user-controlled URL fetch?

# ReDoS / DoS surfaces
grep -rnE "re\.(match|search|fullmatch|findall|sub)\(" --include="*.py" src/ | head -30   # user-controlled subject?
grep -rnE "\((\.\*|\\\\w\+|\[\^?[^]]*\]\+)\)[\*\+]" --include="*.py" src/                 # nested quantifiers
grep -rn "zlib.decompress\|Image.open" --include="*.py" src/                              # size budgets present?
grep -rn "set_int_max_str_digits" --include="*.py" src/
grep -rn "webbrowser.open" --include="*.py" src/                               # user-influenced URL? [HIGH] CVE-2026-4519/4786

# Supply chain
grep -rn "git+http" pyproject.toml uv.lock 2>/dev/null | grep -v "@[0-9a-f]\{40\}"
grep -rn "nosec\|noqa: S" --include="*.py" src/                               # justified suppressions?
```
