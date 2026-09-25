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

## 4a. Temporary files: the name is not the file

`tempfile.mktemp()` returns a *name* and creates nothing. **Deprecated since Python 2.3**,
and the stdlib says why: *"By the time you get around to doing anything with the file name it
returns, someone else may have beaten you to the punch."* That is a TOCTOU window in a
world-writable directory — the attacker wins it by creating a symlink at that path first.

- **Use `mkstemp()` / `NamedTemporaryFile()`.** The docs guarantee the file is *"readable and
  writable only by the creating user ID"*, not executable by anyone, and that *"there are no
  race conditions in the file's creation"* given a working `os.O_EXCL`.
- **A hardcoded `/tmp/...` path is the same bug without the API call**, and it is the more
  common one — predictable, world-writable, and often written before anything checks it.
  Honour `TMPDIR` by letting `tempfile` choose.
- **Widening permissions after the fact undoes the guarantee.** `os.chmod(path, 0o777)` on a
  secrets file, or a service `umask(0)`, hands the file to every local account.

```python
# BAD — name now, file later; and the mode is set after content is written
path = tempfile.mktemp(suffix=".key")
open(path, "w").write(secret); os.chmod(path, 0o644)

# GOOD — created atomically, owner-only from the first byte
fd, path = tempfile.mkstemp(suffix=".key")
with os.fdopen(fd, "w") as fh:
    fh.write(secret)
```

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

## 6a. Cryptography: this skill does not own it

§6 covers *randomness*. Algorithm and protocol choice — AEAD selection, nonce discipline,
key derivation, constant-time comparison, crypto agility, post-quantum migration — is
**`sota-code-security` rules/04**, deliberately, because those decisions are identical across
languages and drift badly when restated per runtime. Load it before designing anything
cryptographic; this section is only the Python-specific part.

- **Use PyCA `cryptography`** for general-purpose work; it is the library the ecosystem
  standardises on. `pycryptodome` exists as an API-compatible successor to the long-dead
  `pycrypto` import path — if you find `from Crypto...` in a codebase, establish which of the
  two is actually installed before changing anything, because the import name is the same.
- **`hashlib` is not a password API.** `md5`/`sha1` for *security* purposes are flagged
  (bandit B303/B324); for a non-security digest pass `usedforsecurity=False` so the intent is
  in the code rather than in a reviewer's head. Password hashing wants argon2/bcrypt/scrypt,
  not a bare hash — the choice itself is `sota-code-security` rules/04.
- **`crypt` was removed in 3.13** (PEP 594, rules/01 §7a). Code still importing it is both
  broken on a modern floor and using weak, platform-dependent hashing.

## 6b. Remote host trust: verify, or you are trusting DNS

- **`paramiko`'s default is safe** — `SSHClient` uses `RejectPolicy`, which raises on an
  unknown host key. The defect is opting *out*:
  `set_missing_host_key_policy(AutoAddPolicy())` stores and saves any key it is offered, so
  the first connection — the one an attacker most wants to intercept — is unauthenticated.
  `WarningPolicy` is the same hole with a log line. Load known-hosts
  (`client.load_system_host_keys()`) and keep the default.
- **`telnetlib` was removed in 3.13** and was plaintext credentials before that.
- TLS verification lives in §7; the same principle applies to both: an unverified peer is an
  unauthenticated peer, whatever the transport.

## 7. XML & SSRF quickies

- Untrusted XML: use `defusedxml`; stdlib `etree` is OK against entity *expansion* on modern
  versions but external entity and DTD handling across libs (lxml!) still needs hardening:
  `lxml.etree.XMLParser(resolve_entities=False, no_network=True)`.
- SSRF (policy: `sota-code-security` rules/01 §5; this is the Python idiom):
  - **Take a key, not a URL.** Accept a host name or record id, look it up in your own
    allowlist and build the URL yourself; a caller-supplied URL relayed to a client is the bug.
  - **Check the address you dial, at connect time.** Validating the hostname and then letting
    the client resolve it again leaves a DNS-rebinding window. With httpcore, pass
    `httpcore.ConnectionPool(network_backend=...)` a `httpcore.SyncBackend` subclass whose
    `connect_tcp()` runs `socket.getaddrinfo`, rejects the request if *any* returned address is
    bad, and dials the vetted IP; TLS still verifies the original hostname, because httpcore
    takes `server_hostname` from the origin. `httpx.HTTPTransport` (0.28) exposes no backend
    parameter, so with httpx pin instead: resolve and vet, request `https://<ip>/…` with a
    `Host` header and `extensions={"sni_hostname": host}` via `client.build_request` +
    `client.send`. Both measured against httpx 0.28.1 / httpcore 1.0.9.
  - **What "bad" means**: unwrap `ip.ipv4_mapped` first, then reject `not ip.is_global` (covers
    loopback, RFC 1918, ULA `fc00::/7`, link-local incl. `169.254.169.254`, `0.0.0.0/8`,
    `100.64/10`) **and** `ip.is_multicast`, which the check misses: `224.0.0.1` reads
    `is_global == True`. Also refuse metadata host names (`metadata.google.internal`) before
    resolving.
  - **Parse literals with `ipaddress.ip_address`**, which rejects `0177.0.0.1`, `0x7f.0.0.1`,
    `2130706433` and `127.1`; `socket.inet_aton` accepts every one of them as `127.0.0.1`.
  - **Redirects**: httpx defaults to `follow_redirects=False`; requests defaults to
    `allow_redirects=True` on `get`/`Session.request`. Turn it off and re-run the full check on
    each `Location` yourself, capping hops (`max_redirects` only limits the count).
  - **Schemes**: httpx raises `UnsupportedProtocol` for anything but http(s), but
    `urllib.request.urlopen` reads `file://` — allowlist `https` before a URL reaches it.
  OWASP: SSRF Prevention, .NET Security and GraphQL cheat sheets.

## 7a. `assert` is not a control — `-O` deletes it

`python3 -O` and `PYTHONOPTIMIZE=1` strip `assert` statements entirely. Verified:
a function whose `assert x > 0` raised under a normal run printed `passed` under
both. So any validation, authorization, or bounds check written as an `assert`
**does not exist** in an optimized deployment, and the source still reads correct.

- Validation and security checks are `if not ok: raise ...`, never `assert`.
- Keep `assert` for impossible internal states you want loud in development.
- Audit: `grep -rn "assert " --include="*.py"` over request handlers, validators
  and permission code, then check whether the runtime is invoked with `-O` /
  `PYTHONOPTIMIZE` (Dockerfile `CMD`, entrypoint, `uv run` flags).
- Note the sibling trap: lenient numeric parsing. `int(" 12 \n")` is `12` and
  `float("1_0")` is `10.0` — a corrupt field yields a plausible number rather
  than an error. Full class: `sota-code-security` rules/13 §3.

## 8. Input-adjacent denial of service & injection oddities

- **ReDoS:** user input through a regex with nested/ambiguous quantifiers
  (`(a+)+`, `(.*)*`, `(\w+\s?)*`) can run exponentially. Audit every `re.*` whose pattern
  *or* subject is user-controlled; prefer anchored, linear patterns; set a length cap on the
  subject before matching; for hostile-input parsing consider the `regex` module's timeout
  or the RE2 bindings (`google-re2`, which binds Google's C++ RE2).
- **A regex used as a control (validation, allowlist, routing, redaction)** — four checks,
  each measured on CPython 3.14.6:
  - *Escaping.* Anything from outside that becomes part of a pattern goes through
    `re.escape()` first (`regex.escape()` / `re2.escape()` for those engines). An f-string
    like `re.compile(f"^{user_prefix}")` lets the caller inject `.*` or a quantifier bomb.
  - *Anchoring.* Validate with `re.fullmatch()` / `Pattern.fullmatch()` (3.4+). `re.match()`
    anchors only at the start, so `re.match(r"[a-z]+", "abc;rm")` succeeds; `$` also matches
    just before a trailing `\n`, so `re.match(r"^[a-z]+$", "abc\n")` succeeds while
    `re.fullmatch(r"[a-z]+", "abc\n")` is `None`. Hand-anchored patterns end in `\Z` (spelled
    `\z` from 3.14), and never carry `re.MULTILINE`, which turns `^`/`$` into line anchors.
  - *Bounds.* Give every repeat an upper limit (`[a-z0-9_]{3,32}`, not `+`) and reject by
    `len()` before the regex runs.
  - *Engine.* Stdlib `re` backtracks and has no timeout argument. For patterns you write,
    atomic groups `(?>...)` and possessive quantifiers `*+ ++ ?+` (3.11+) forbid
    backtracking into what they matched (`(?:a++)+b` on 24 `a`s: 0.1 ms vs 0.6 s for `(a+)+b`). For patterns or subjects you do not control, use a linear-time engine
    (`google-re2`, imported as `re2`, which rejects backreferences and lookaround at compile
    time) or the third-party `regex` module's `timeout=` keyword, which raises `TimeoutError`.
    Needing a backreference or lookaround is the price of leaving the linear engine: keep
    that pattern on a bounded, length-capped subject.
  OWASP: Input Validation cheat sheet; OWASP Proactive Controls 2024 C3; ASVS 5.0 V1.2.9;
  OWASP Go-SCP (regular expressions, validation).
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

## 8a. Debug consoles and error pages in production

Django's `DEBUG=False` is already a settings rule (rules/07 §2). This is the mechanism, and
it generalises past Django.

- **Werkzeug's interactive debugger executes arbitrary Python** in any traceback frame when
  `evalex` is on — which is what Flask's `debug=True` turns on. Its own documentation is
  unusually blunt: *"The debugger must never be used on production machines. We cannot stress
  this enough."* It is PIN-protected by default, and the same docs say the PIN is *"not meant
  to entirely secure the debugger"* — treat it as friction, not a control.
- **"Production means anything that is not development, and anything that is publicly
  accessible"** — including a staging box with a public DNS name.
- **The non-executing half still leaks.** A debug error page prints settings, environment and
  often connection strings; an unauthenticated `/metrics` or a profiler endpoint does the same
  more quietly. The control is that debug state is read from the environment and defaults to
  *off*, never a literal in source that someone must remember to flip.

Dependency and supply-chain hygiene and static-analysis gates (formerly sections 9 and 10)
moved to [rules/08](08-supply-chain.md) §1–§2 on 2026-09-25.

## 11. `ctypes`, `cffi` and C extensions — Python without its safety

`ctypes` and `cffi` read and write arbitrary process memory from pure Python. The standard
library's own warning is that incorrect use "can corrupt data and objects, reveal sensitive
information, cause crashes, or otherwise compromise the running process". A wrong `argtypes`,
a buffer sized from input, or a pointer kept after its owner is freed is a C bug with no C
file to review. Confine these calls to one module, declare `argtypes`/`restype` on every
foreign function, and validate lengths before they cross. The class is `sota-code-security` rules/06 §3.

## Audit checklist

- [ ] **`ctypes` / `cffi` — HIGH where a size or pointer comes from input** (§11) —
      `grep -rnE '^[[:space:]]*(import|from)[[:space:]]+(ctypes|cffi)|ctypes\.(CDLL|cdll|string_at|memmove|cast|create_string_buffer)' --include='*.py' .`
      (each foreign function declares `argtypes`/`restype`; lengths validated before the call)
- [ ] **Code execution / deserialization [CRITICAL on untrusted data]** —
      `grep -rn "pickle.loads\|pickle.load\|read_pickle\|joblib.load\|marshal.loads\|dill" --include="*.py" src/`
      ; `grep -rn "torch.load" --include="*.py" src/ | grep -v "weights_only=True"` ;
      `grep -rn "yaml.load(" --include="*.py" src/ | grep -v "SafeLoader\|safe_load"` ;
      `grep -rn "\beval(\|\bexec(" --include="*.py" src/ | grep -v "literal_eval\|model.eval()"`
      ; `grep -rn "\.format(.*request\|f\".*{.*request" --include="*.py" src/ | head`
      (format-string gadgets)
- [ ] **Subprocess [HIGH]** — `grep -rn "shell=True" --include="*.py" src/` ;
      `grep -rn "os.system\|os.popen" --include="*.py" src/`
- [ ] **SQL [CRITICAL]** —
      `grep -rn 'execute(f"\|execute(".*%s" *%\|execute(.*+ ' --include="*.py" src/` ;
      `grep -rn "\.raw(\|\.extra(\|RawSQL" --include="*.py" src/` (Django edges);
      `grep -rn 'text(f"' --include="*.py" src/` (SQLAlchemy text+f-string)
- [ ] **Path traversal & archives [HIGH]** —
      `grep -rn "extractall\|extract(" --include="*.py" src/ | grep -v 'filter='` ;
      `grep -rn "request.*filename\|\.filename" --include="*.py" src/` (then check containment);
      `grep -rn "is_relative_to\|realpath" --include="*.py" src/` (mitigations present?)
- [ ] **Randomness & secrets [HIGH]** —
      `grep -rn "random\.\(choice\|choices\|randint\|random\)" --include="*.py" src/ # security context?`
      ; `grep -rn "== .*token\|token.* ==" --include="*.py" src/ | head` (timing-unsafe
      compare); `grep -rn "verify=False\|_create_unverified" --include="*.py" src/` ;
      `grep -rnE "(api_key|secret|password|token) *= *['\"][A-Za-z0-9_\-]{12,}" --include="*.py" .`
      (hardcoded); `grep -rn "md5(\|sha1(" --include="*.py" src/ | grep -v usedforsecurity`
- [ ] **XML / SSRF** —
      `grep -rn "lxml.etree\|xml.etree\|xml.dom\|xml.sax" --include="*.py" src/` (defused?
      entities off?); `grep -rn "get(url\|get(request\.\|urlopen(" --include="*.py" src/ | head`
      (user-controlled URL fetch?)
- [ ] **--- SSRF: outbound request to a caller-influenced host (§7) --- [HIGH; CRITICAL where
      the metadata endpoint 169.254.169.254 is reachable]** —
      `grep -rnE '(requests|httpx)\.(get|post|put|patch|delete|head|options|request|stream)\(|urlopen\(|(allow|follow)_redirects[[:space:]]*=[[:space:]]*True' --include='*.py' src/`
      (module-level helpers have no connect-time hook, and redirects-on re-opens every
      check; for each hit, and each `requests.Session`, find where the dialled IP is vetted
      after DNS resolution — a hostname check before the call is not it)
- [ ] **ReDoS / DoS surfaces** —
      `grep -rnE "re\.(match|search|fullmatch|findall|sub)\(" --include="*.py" src/ | head -30`
      (user-controlled subject?);
      `grep -rnE "\((\.\*|\\\\w\+|\[\^?[^]]*\]\+)\)[\*\+]" --include="*.py" src/` (nested
      quantifiers); `grep -rn "zlib.decompress\|Image.open" --include="*.py" src/` (size budgets
      present?); `grep -rn "set_int_max_str_digits" --include="*.py" src/` ;
      `grep -rn "webbrowser.open" --include="*.py" src/` (user-influenced URL? [HIGH]
      CVE-2026-4519/4786)
- [ ] **--- Regex as a control: escaping, anchoring, engine (§8) --- [HIGH where the regex
      gates validation or authorization; MEDIUM elsewhere]** —
      `grep -rnE 're\.(match|compile|search|fullmatch|sub|findall)\([[:space:]]*(r?f|fr)["'"'"']|\.match\(|re\.(M|MULTILINE)([^A-Za-z_]|$)' --include='*.py' src/`
      (an f-string pattern with no `re.escape()` is injection; a `re.match` used to validate
      needs `re.fullmatch` or a `\Z`; a MULTILINE validator accepts any one good line)
- [ ] **--- Temp files and permissions (§4a) ---** — `grep -rn "mktemp(" --include="*.py" src/`
      (TOCTOU [HIGH]); `grep -rnE '"/tmp/|'"'"'/tmp/' --include="*.py" src/` (predictable path
      [MEDIUM]); `grep -rnE 'chmod\(.*0o(6|7)[0-7][0-7]|umask\(0\)' --include="*.py" src/`
      (widened perms [HIGH if secrets])
- [ ] **--- Crypto (§6a) — choice itself is sota-code-security rules/04 ---** —
      `grep -rnE '\bmd5\(|\bsha1\(' --include="*.py" src/ | grep -v usedforsecurity` ([MEDIUM]);
      `grep -rn "from Crypto" --include="*.py" src/` (pycrypto vs pycryptodome [MEDIUM])
- [ ] **--- Remote host trust (§6b) ---** —
      `grep -rnE 'AutoAddPolicy|WarningPolicy' --include="*.py" src/` (host key not verified
      [HIGH])
- [ ] **--- Debug consoles (§8a) ---** —
      `grep -rnE 'debug\s*=\s*True|DEBUG\s*=\s*True' --include="*.py" src/` (literal, not env
      [HIGH in prod path])
- [ ] **--- Template autoescape (§1) --- [HIGH where user data renders into HTML]** —
      `grep -rnE 'Environment\(|Template\(' --include='*.py' src/` (read each for `autoescape=`:
      measured with Jinja2 3.1.6, `Environment().autoescape` is `False` and `{{ x }}` rendered
      `<script>` verbatim, while `select_autoescape()` escaped it) ;
      `grep -rnE 'autoescape[[:space:]]*=[[:space:]]*False|Markup\(|mark_safe\(|\|[[:space:]]*safe' --include='*.py' --include='*.html' --include='*.j2' .`
      (each explicit opt-out needs a reason)
- [ ] **--- `assert` as a control (§7a) --- [HIGH where it guards authorization or
      validation]** —
      `grep -rnE '^[[:space:]]*assert[[:space:]]' --include='*.py' src/` (outside tests every
      hit is a check that `-O` deletes; read the handlers, validators and permission code) ;
      `grep -rnE 'python[0-9.]*("?,)?[[:space:]]+"?-OO?([[:space:]",]|$)|PYTHONOPTIMIZE' --include='Dockerfile*' --include='*.sh' --include='*.y*ml' --include='*.toml' .`
      (the deployment that runs optimized)