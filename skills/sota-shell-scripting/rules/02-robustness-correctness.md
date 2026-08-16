# 02 — Robustness & Correctness

Interfaces, failure handling, portability, concurrency, idempotency.

## 1. Argument parsing

Every script ≥ one option gets structured parsing; every script gets `--help`; distributed
tools get `--version`.

- `getopts` (builtin, POSIX) for short options only — simple, portable, handles clustering
  (`-abc`). It does **not** do long options. Do not use external `getopt` unless you can
  guarantee GNU getopt (`getopt -T`; BSD/macOS getopt is broken for quoting).
- Manual `while/case` for long options — the SOTA default for nontrivial scripts:

```bash
usage() {
  cat <<EOF
Usage: ${0##*/} [-v] [--region REGION] TARGET
Deploy TARGET to the given region.

  -v, --verbose     verbose output
      --region R    target region (default: ${DEFAULT_REGION})
  -h, --help        show this help
EOF
}

verbose=0 region=$DEFAULT_REGION target=""
while (( $# > 0 )); do
  case $1 in
    -v|--verbose) verbose=1 ;;
    --region)     [[ ${2:-} ]] || die "--region requires a value"; region=$2; shift ;;
    --region=*)   region=${1#*=} ;;
    -h|--help)    usage; exit 0 ;;
    --)           shift; break ;;
    -*)           die "unknown option: $1 (see --help)" ;;
    *)            break ;;
  esac
  shift
done
(( $# == 1 )) || { usage >&2; exit 64; }   # EX_USAGE
target=$1
```

Rules: unknown option is an error, never silently ignored; `--` stops option parsing;
options taking values handle both `--opt val` and `--opt=val` or document which;
`usage` goes to stdout on `--help` (exit 0), stderr on misuse (exit 64).

## 2. Input validation

Validate before acting, fail with a message naming the bad value:

```bash
[[ $region =~ ^[a-z]{2}-[a-z]+-[0-9]$ ]] || die "invalid region: '$region'"
[[ -d $src ]] || die "source directory not found: $src"
[[ $count =~ ^[0-9]+$ ]] || die "count must be a non-negative integer, got: '$count'"
```

- Validate *types* of things shell is bad at (numbers, enums, paths) with `[[ =~ ]]` or
  case patterns; reject rather than sanitize.
- Required environment variables: check up front, all at once, not at first use:

```bash
: "${DEPLOY_TOKEN:?DEPLOY_TOKEN must be set}"   # -u-style with custom message
```

## 3. Errors to stderr, exit codes, die()

```bash
err() { printf '%s: %s\n' "${0##*/}" "$*" >&2; }
die() { err "$@"; exit 1; }
```

- Every diagnostic to stderr (`>&2`) — stdout is for *output* that callers pipe. A script
  that prints errors to stdout corrupts downstream consumers.
- Messages carry context: what was attempted, on what object, what the underlying error
  was. `die "failed to upload $artifact to $bucket: $curl_err"` not `die "error"`.
- Exit codes: 0 success only; 1 generic failure; 2 reserved-ish (bash builtin misuse);
  64–78 BSD sysexits if you want granularity (64 usage, 69 unavailable, 77 permission);
  126/127 (not executable / not found) and 128+N (signal) are shell-reserved — don't
  emit them yourself. Document non-trivial codes in `--help`.
- Never `exit` from inside a function where the caller might want to continue — `return`
  a status and let the top level decide; `exit` in sourced files kills the caller's shell.

## 4. Pipelines: pipefail awareness and PIPESTATUS

- `set -o pipefail` makes the pipeline status the rightmost nonzero status. Two follow-ups:
  - **zsh spells it differently and indexes from 1**: `${pipestatus[1]}` is the first
    stage (`${PIPESTATUS[0]}` in bash). `cmd | tail -1; echo $?` reports `tail`'s status
    in both shells — when the exit code is the thing under test, drop the pipe.
  - To know *which* element failed: `"${PIPESTATUS[@]}"` (bash; copy it immediately — any
    next command overwrites it):

```bash
dump_db | gzip > "$out"
status=("${PIPESTATUS[@]}")
(( status[0] == 0 )) || die "dump failed (${status[0]})"
(( status[1] == 0 )) || die "gzip failed (${status[1]})"
```

  - Expected-failure producers break under pipefail: `grep` exits 1 on no match
    (`grep pattern file | wc -l` "fails" on zero matches); a consumer like `head` closing
    early makes the producer die of SIGPIPE (141). Handle deliberately:

```bash
matches=$(grep -c pattern file || true)       # no-match is not an error here
yes | head -n 3                               # SIGPIPE on `yes` → status 141; guard:
out=$(produce | head -n 3) || (( $? == 141 ))  # accept SIGPIPE only
```

- Prefer process substitution over pipes into `while read` — the pipe runs the loop in a
  subshell, so variable updates vanish (SC2031):

```bash
# BAD — count is always 0 after the loop
cmd | while read -r line; do (( ++count )); done
# GOOD
while IFS= read -r line; do (( ++count )); done < <(cmd)
```

## 5. Portability: bash vs POSIX sh

Decide per script and enforce with the shebang + `shellcheck -s sh`.

- POSIX sh required: busybox/alpine and dash-based containers without bash, initramfs,
  `system()`-invoked snippets, packaging hooks. Then: no arrays (use `set -- args...`
  to reuse positional params), `[ ]` not `[[ ]]`, no `pipefail` (run each stage to a temp
  file or use a fifo/status-file trick), `. file` not `source`, no `${var//}`, no
  `<<<`/`<( )`, `printf` always (dash `echo` interprets escapes).
- bash-targeted: use bash properly (arrays, `[[ ]]`, `mapfile`) — half-POSIX bash is the
  worst of both. But remember macOS = bash 3.2: no associative arrays, no `mapfile`, no
  `${var,,}`, no `inherit_errexit`. If macOS devs run the script, either stay 3.2-clean
  or version-check (rules/01 §1). CI containers: confirm bash exists
  (`docker run image which bash`) before writing `#!/usr/bin/env bash` entrypoints —
  alpine base images have only busybox ash unless bash is installed.

## 6. Command existence and invocation

- `command -v tool >/dev/null 2>&1 || die "tool is required"` — never `which` (SC2230:
  external, non-portable output and exit codes).
- Check all dependencies up front in one place:

```bash
for cmd in jq curl flock; do
  command -v "$cmd" >/dev/null 2>&1 || die "missing required command: $cmd"
done
```

- Don't hardcode tool paths except in privileged scripts with a sanitized PATH (rules/03).

### A missing tool is a decision, not automatically a failure

`|| die` above is right for a tool the script cannot be correct without. It is wrong
for everything else, and the difference matters most in **gates and checks**, where
"the tool isn't installed" must never be reported as "the check passed".

Classify each dependency once, and make the behaviour match:

| The tool is… | Do | Never |
|---|---|---|
| **required for correctness** (the script's whole job) | `die` with the install command for this platform | proceed with a degraded result |
| **required for one check** inside a larger run | run the rest, **SKIP that check with a named note** — `SKIPPED: python3 not found (CI enforces this check)` — and make the skip visible in the summary | print `ok`, or count the skip as a pass |
| **optional / an enhancement** | proceed, note the reduced capability once | fail the run |
| **missing on an interactive run** | **stop and ask the human to install it**, naming the exact command, then continue or exit on their answer | silently install it, or `sudo` anything unasked |

```bash
need() {  # need <cmd> <what it is for> <install hint>
  command -v "$1" >/dev/null 2>&1 && return 0
  if [ -t 0 ] && [ -t 1 ]; then          # a human is present: ask, do not guess
    printf 'Missing %s (needed for %s). Install with: %s\n' "$1" "$2" "$3" >&2
    printf 'Install it now and press Enter to continue, or Ctrl-C to abort: ' >&2
    read -r _
    command -v "$1" >/dev/null 2>&1 && return 0
  fi
  return 1
}

need shellcheck "shell linting" "brew install shellcheck" \
  || note "SKIPPED: shellcheck not found — shell lint did not run"
```

Two rules that make this safe rather than sloppy:

- **A skipped check is not a passed check.** Print the skip on the same line the check
  would have used, count skips separately, and never let the summary read clean when a
  check did not execute (`sota-code-security` rules/10 §2.13 — a control that never runs).
  This repo does exactly that: four invariants print `SKIPPED: python3 not found` and CI,
  where python3 always exists, enforces them for real.
- **Never auto-install.** Installing software is a change to the user's machine; on a
  non-interactive run there is no one to consent, so degrade or fail loudly instead.
  Ask, print the command, and let the human run it — a script that quietly installs a
  package manager's worth of dependencies is a supply-chain event, not a convenience.

## 7. Network calls: timeouts and bounded retries

A network call without a timeout is a hang waiting to happen; without retry discipline it
is flaky CI.

```bash
# GOOD — fail on HTTP errors, bound total time, retry transient failures with backoff
curl --fail --silent --show-error --location \
     --connect-timeout 5 --max-time 60 \
     --retry 3 --retry-delay 2 --retry-all-errors \
     -o "$tmpfile" -- "$url" || die "download failed: $url"
```

- `--fail` (or `--fail-with-body` when you need the error payload): otherwise curl exits 0
  on HTTP 500 and you process an error page as data.
- `--max-time` always; `--retry-all-errors` only for idempotent GETs — never blind-retry
  POSTs that aren't idempotent.
- Non-curl commands: wrap with `timeout 60 cmd ...` (coreutils). Generic retry wrapper:

```bash
retry() { # retry N CMD...
  local -i n=$1 i; shift
  for (( i = 1; i <= n; i++ )); do
    "$@" && return 0
    (( i < n )) && { err "attempt $i/$n failed: $*; retrying"; sleep $(( i * 2 )); }
  done
  return 1
}
```

## 8. Concurrency: flock, background jobs, wait

- Concurrent invocation (cron + manual run, parallel CI jobs) corrupts state. Mutual
  exclusion via `flock` on Linux:

```bash
exec 9>"/var/lock/${0##*/}.lock"
flock -n 9 || die "another instance is running"
# lock held for the life of fd 9 (process lifetime); released automatically on exit/crash
```

  Never the `[ -f pidfile ]` dance — it races and leaks stale locks. macOS lacks `flock(1)`;
  use `mkdir`-as-lock (atomic) with trap cleanup if portable locking is needed.
- Background jobs: every `&` is owned — record the PID, `wait` on it, check its status.

```bash
# GOOD — bounded parallelism with per-job status (bash ≥4.3 wait -n; 5.1 adds -p)
pids=()
for host in "${hosts[@]}"; do
  deploy_one "$host" & pids+=($!)
done
fail=0
for pid in "${pids[@]}"; do
  wait "$pid" || { fail=1; err "job $pid failed"; }
done
(( fail == 0 )) || die "one or more deploys failed"
```

- Plain `wait` with no args returns 0 regardless of children's failures (pre-5.x semantics
  vary) — always wait per-PID when status matters. Never leave an unmanaged `&` (orphaned
  work continues after the script "succeeds" or dies).
- For real parallel fan-out with output grouping, prefer `xargs -P` or GNU parallel over
  hand-rolled job pools.

## 9. Idempotency and atomic writes

Scripts get re-run: after partial failure, by retries, by impatient operators. Design for it.

- Check-before-create, tolerate already-done:

```bash
mkdir -p -- "$dir"                       # not mkdir (fails if exists)
[[ -L $link ]] || ln -s -- "$target" "$link"
grep -qxF "$line" "$file" || printf '%s\n' "$line" >> "$file"
```

- **Atomic writes via mv**: never write a config/output file in place — a crash mid-write
  leaves a torn file that consumers read.

```bash
tmp=$(mktemp -- "${out}.XXXXXX")         # same directory → same filesystem → mv is atomic rename
generate > "$tmp"
chmod 0644 -- "$tmp"                     # mktemp creates 0600; fix perms before publishing
mv -f -- "$tmp" "$out"
```

- Downloads: download to temp, verify (checksum, `--fail` already ensured non-error body),
  then `mv` into place. Never let a consumer see a half-downloaded artifact.
- Deletions/migrations: make them no-ops on second run (`rm -f`, guarded `ALTER`s via the
  real tool, not shell).

## 10. Filenames are hostile input

Filenames may contain spaces, newlines, leading `-`, glob chars, non-UTF-8 bytes.

```bash
# BAD — splits on whitespace, breaks on newlines, -dashfile becomes an option
for f in $(find . -name '*.log'); do rm $f; done

# GOOD — NUL-delimited end to end
find . -name '*.log' -print0 | xargs -0 rm -f --
# or no pipe at all:
find . -name '*.log' -exec rm -f -- {} +
# or into an array (bash ≥4.4):
mapfile -d '' logs < <(find . -name '*.log' -print0)
```

- `--` before any operand that comes from a variable/glob, for every command that supports
  it (`rm`, `cp`, `mv`, `grep`, `git checkout`, ...). For commands without `--`, prefix
  relative paths: `rm "./$f"`.
- `while IFS= read -r -d '' f` to consume `-print0` streams in-loop.
- Never embed filenames in command strings passed to `ssh`/`bash -c` without proper
  quoting — use `printf '%q'` (bash) or pass as positional args to a remote script.

## Audit checklist

- [ ] **Missing-tool behaviour classified**: does every `command -v` failure `die`,
      skip-with-a-named-note, or ask an interactive human — and does the summary ever
      read clean while a check did not execute? Probe:
      `PATH=/usr/bin:/bin <script>` with a dependency removed, and confirm the run
      reports a SKIP rather than an `ok`. No script may auto-install a dependency.
- [ ] No `--help`: `grep -rLn -- '--help\|-h)' --include='*.sh'` → MEDIUM for any operator-facing script.
- [ ] Unknown options silently ignored: `case` parse loops missing a `-*)` error arm.
- [ ] SC2230 — `grep -rn 'which ' --include='*.sh'` → replace with `command -v`.
- [ ] Errors to stdout: `grep -rn 'echo.*[Ee]rror\|echo.*[Ff]ail' --include='*.sh'` lacking `>&2`.
- [ ] `exit 0` at end of failure paths; functions calling `exit` where `return` is right.
- [ ] Bare curl/wget: `grep -rn 'curl ' --include='*.sh' | grep -v -- '--max-time\|--fail'`
      → MEDIUM (no timeout) / HIGH if output is piped to a shell or parsed as data.
- [ ] Retries on non-idempotent operations (`--retry` + POST) → HIGH.
- [ ] SC2031/SC2030 — `| while read` subshell variable loss.
- [ ] Pipeline status ignored where producer matters and no `pipefail`/PIPESTATUS check.
- [ ] Lock discipline: cron-invoked or deploy scripts without `flock`/lock dir → MEDIUM;
      pidfile-based locks → MEDIUM (racy).
- [ ] Unmanaged `&`: `grep -rn ' &$' --include='*.sh'` without matching `wait` on PID.
- [ ] In-place writes of consumed files: `grep -rn '> */etc/\|> *.*\.conf' --include='*.sh'`
      without mktemp+mv → HIGH for configs read by daemons.
- [ ] `for .* in \$(find\|in \$(ls` and `xargs` without `-0` paired with `-print0` → HIGH
      in destructive contexts (SC2044, SC2011).
- [ ] Missing `--` before variable operands of `rm/mv/cp/chown/chmod/git`.
- [ ] Bashisms in `#!/bin/sh` files destined for alpine/busybox images (cross-check
      Dockerfiles for base image).
