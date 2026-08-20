# 03 — Behavior & Lifecycle

Scope: startup latency, idempotency, dry-run, signal handling, crash-only
design, network/offline behavior, self-update, telemetry, XDG directories,
shell completions, versioning the CLI surface.

## 1. Startup performance

- `tool --help` and `tool --version` must feel instant — target well under
  100ms perceived. These run constantly (humans exploring, completions, CI
  sanity checks); a 1.5s help is a tax on every interaction.
- Common killers, in audit order:
  - importing/initializing the world before parsing args (Python tools that
    `import` heavy deps at module top — defer imports into the subcommand
    that needs them; compiled langs largely immune)
  - network calls on startup: update checks, telemetry, auth validation —
    none may block `--help`/`--version`; do them lazily, async, or in the
    subcommands that need them
  - loading/validating full config for commands that don't use it
- Measure honestly: `time tool --help` cold and warm; on the JVM/Node, measure
  on the runtime your users have, not a warmed daemon.
- Shell completion functions invoke the binary; slow startup makes every TAB
  lag the user's shell (§8).

## 2. Idempotency & dry-run

- Make commands **re-runnable**: running the same command twice converges to
  the same state, second run a cheap no-op or explicit "already done" —
  not an error, not a duplicate.
  - `tool init` on an initialized dir: report "already initialized", exit 0
    (offer `--force` to reset).
  - `create` where the resource exists with the same spec: succeed (or
    `already exists` + distinct exit code if callers must distinguish — pick
    one, document it). Desired-state semantics (`apply`) beat imperative
    `create` for anything users automate.
- **`--dry-run` on every mutating command.** Requirements:
  - exercises the *real* code path (plan, validate, resolve) and skips only the
    write — a dry-run that takes a separate code branch lies;
  - prints the concrete plan: which files/resources, created/changed/deleted;
  - exits 0 if the run would proceed, nonzero if it would fail validation —
    making `--dry-run` a usable CI preflight;
  - performs **zero** writes, including logs-on-server side effects.
- Operations on many items: report per-item outcome and end with a summary
  (`8 updated, 1 skipped, 1 failed`); overall exit nonzero if any failed
  (rules/02 §3); support resume rather than redo (§4).

## 2a. `--self-test` for tools whose output is a verdict

A linter, a health checker, a scanner, a policy gate, a `doctor` command — anything
whose output is a **verdict** rather than an artifact — is an instrument, and an
instrument that cannot fail returns a plausible verdict on whatever it is handed
(`sota-code-security` rules/12 §2). From the outside a user cannot tell: *"0
problems found"* and *"0 checks ran"* print the same, and the second is the ordinary
result of a bad path, an empty glob, an over-narrow filter, or a missing toolchain.

- **Ship a `--self-test`** (or `doctor --self-test`) that injects each check's
  declared known-bad and asserts *that named check* reports it. Exit nonzero when a
  check has no known-bad, when a mutation is not caught, **or when a probe fails for
  an unrelated reason** — a non-zero exit from the wrong cause is a false pass, not
  a catch (rules/12 §1b).
- **Print the denominator on every ordinary run**, not only under `--self-test`:
  `checked 128 files, 3 problems`. A count of zero problems is only meaningful
  beside a count of what was examined, and users read the summary line, not the
  config.
- **Skips are output, not silence.** A check that could not run (missing toolchain,
  no network, unsupported platform) prints `skipped: <reason>` and is counted
  separately from `passed`. Folding skips into passes is how a tool reports green on
  a machine where it did almost nothing.
- **Keep `--self-test` offline and side-effect-free.** It is what a user runs when
  they already suspect the tool, so it must not need the network, must not write to
  the paths it checks, and must work on an installed copy — not just in the source
  tree (`--dry-run`'s "exercise the real path" rule, §2, applies to it too).

## 3. Signals: Ctrl-C is sacred

- First SIGINT: stop accepting new work, cancel in-flight operations, run
  bounded cleanup (seconds, not minutes), restore terminal state, exit.
  Second SIGINT: exit immediately, skipping cleanup — the user has spoken.

  ```
  ^C
  interrupted — rolling back partial upload (ctrl-c again to force quit)
  ```

- Exit status after SIGINT: re-raise the signal after cleanup
  (`signal(SIGINT, SIG_DFL); raise(SIGINT)`) so the shell sees death-by-signal
  (status 130) — `exit(1)` makes shell job control and script `trap`s misread
  what happened.
- **Always restore the terminal**: raw mode off, cursor visible, colors reset,
  alternate screen exited. A TUI/prompt that leaves the shell invisible-cursor
  or no-echo on Ctrl-C is a High finding. Use defer/finally/atexit paths that
  run on signal, and test it: hit Ctrl-C inside every prompt and progress bar.
- SIGINT must work **during network operations**: set cancellation on the
  request context (Go contexts, Python signal→cancel, Rust select on ctrl_c).
  A blocking socket read that ignores Ctrl-C for 60s reads as a hang.
- Handle SIGTERM like SIGINT-without-prompt (CI and orchestrators send it);
  SIGHUP at minimum doesn't corrupt state.
- Never trap SIGINT just to print "use 'exit' to quit" for batch commands —
  interactive REPLs may, batch operations may not.

## 4. Crash-only, resumable design

- Assume every run can die at any instruction (OOM-kill, power, `kill -9` —
  no cleanup handler runs). Design so the *next* run recovers, instead of
  relying on graceful shutdown:
  - **Write-then-rename**: never truncate-and-rewrite config/state/output in
    place; write `file.tmp` (same filesystem), fsync, atomic `rename(2)`.
    Audit any `open(path, "w")` on files the tool also reads.
  - Long multi-step operations journal progress (state file/manifest) so
    `tool sync` after an interrupt resumes — or at minimum re-runs safely
    (§2). Partial downloads: `.partial` suffix + resume or restart cleanly.
  - Locks: prefer OS-released mechanisms (`flock`) over PID/lock files; if a
    lock file is unavoidable, store PID + start time and detect staleness —
    "delete .tool.lock and retry" instructions mean the design failed.
  - On detected leftover state: say what was found, what you did:
    `note: resuming interrupted sync from step 3/7 (state: .tool/journal)`.

## 5. Network behavior, offline & self-update

- Timeouts on every network call — connect and overall — surfaced as a config
  default + `--timeout` flag. No infinite-hang defaults.
- Retries with capped exponential backoff + jitter for idempotent requests
  only; say what's happening after the first failure
  (`warn: retrying (2/3) after timeout: GET https://api…`).
- **Fail fast and clearly offline**: a DNS failure should produce
  `error: cannot reach api.example.com (DNS lookup failed) — check your network or set TOOL_API_URL`
  in ~seconds, not a 5-minute silent retry storm. Commands that *can* work
  offline (cached data, local ops) must not perform gratuitous network calls.
- Update checks: never block startup; cache the result
  (`$XDG_CACHE_HOME/tool/`); notify at most once per interval on stderr, TTY
  only, suppressible (`TOOL_NO_UPDATE_CHECK=1`) and disabled when `CI` is set.
- **Self-update (`tool self update`) is opt-in only — never automatic.**
  Auto-updating a CLI changes behavior under scripts between runs; teams pin
  versions for a reason (rules/04 §4). Self-update must verify
  signature/checksum before replacing the binary, use atomic rename, and
  respect non-writable install locations (brew/apt-managed binaries must
  refuse and point at the package manager).

## 6. Telemetry & files on disk

- Telemetry: **opt-in, or at minimum loudly disclosed on first run with a
  one-command opt-out** (`tool telemetry off` / `TOOL_TELEMETRY=0`); honor the
  `DO_NOT_TRACK` convention; document exactly what is collected; never collect
  argv (it contains paths/names/secrets), file contents, or anything
  identifying without consent. Telemetry must never block or fail a command,
  never run when disabled, and respect `CI`. Undisclosed phoning-home is a
  Critical audit finding.
- **XDG base directories — no `$HOME` litter.** Per the freedesktop spec:

  | Content | Env var | Default |
  |---|---|---|
  | config | `$XDG_CONFIG_HOME/tool/` | `~/.config/tool/` |
  | data (user-created, durable) | `$XDG_DATA_HOME/tool/` | `~/.local/share/tool/` |
  | state (history, logs, last-run) | `$XDG_STATE_HOME/tool/` | `~/.local/state/tool/` |
  | cache (safe to delete anytime) | `$XDG_CACHE_HOME/tool/` | `~/.cache/tool/` |
  | sockets/runtime | `$XDG_RUNTIME_DIR/tool/` | (unset ⇒ fall back to tmp + warn) |

  Respect the env vars when set (absolute paths only). New tools: don't create
  `~/.tool/`. Existing tools migrating: read old location if present, write
  new, say so once. On macOS, honoring XDG is the developer-tool norm even
  though `~/Library/...` is the platform convention — pick one, document it;
  on Windows use `%APPDATA%`/`%LOCALAPPDATA%`.
- Cache must be safe to `rm -rf` at any time — that's its contract. Don't put
  the only copy of anything in cache. Secrets/tokens: own file with `0600`
  perms (verify at write *and* read; warn on loose perms), or the OS keychain.

## 7. The CLI surface is a semver'd API

- The compatibility surface scripts depend on: command names, flag names and
  meanings, defaults, exit codes, env vars, config keys, JSON field names,
  and stdout format in `--json`/`--plain` modes. Changing any of these is a
  breaking change ⇒ major version.
- **Deprecate, don't remove**: keep the old flag working as an alias; print a
  one-line stderr warning naming the replacement and the removal version
  (`warning: --out is deprecated, use --output (removal in v3)`); keep it for
  ≥1 minor cycle, realistically ≥6 months; only then remove — with a clear
  error pointing at the replacement, not "unknown flag".
- Worse than removal is silent **meaning change**: same flag, different
  behavior. Never. If semantics must change, new flag name.
- Human-readable default output may evolve freely **only if** `--json`/
  `--plain` exist as the stable contract — ship them early precisely to buy
  this freedom (rules/02 §2).
- `tool --version` prints `tool X.Y.Z` (+ commit/date as extra tokens or via
  `--version --json`); parseable, no network, instant.

## 8. Shell completions

- Generate completions for **bash, zsh, fish** (PowerShell where relevant)
  from the same parser definition as `--help` — hand-maintained completion
  scripts drift. clap (`clap_complete`), cobra (built-in `completion`
  subcommand), Python (`argcomplete`/click/typer) all support this; use it.
- Convention: `tool completion <shell>` prints the script to stdout; docs show
  the one-liner per shell; packages (brew/deb) install them into the standard
  directories so users get them for free.
- Complete values, not just flag names: subcommands, enum flag values
  (`--output <TAB>` → `json yaml table`), and — where cheap — dynamic resource
  names. Dynamic completion calls back into the binary: it must be fast (§1)
  and **never block on the network or prompt**; degrade to nothing on failure.

## Audit checklist

- [ ] `time tool --help` ≪ 500ms; no network I/O on `--help`/`--version` (verify: airplane-mode or strace/dtruss spot-check).
- [ ] Re-running `init`/`create`/`apply` twice converges; second run no-ops or reports "already" without failing.
- [ ] Every mutating command has `--dry-run`; it runs the real plan path, prints concrete changes, writes nothing, and fails (nonzero) on what would fail.
- [ ] Verdict-producing tools (lint/scan/check/`doctor`) ship a `--self-test` that injects each check's known-bad and asserts the **named** check caught it; every run prints what it examined, and skips are reported with a reason, never folded into passes.
- [ ] Batch operations: per-item results + summary; nonzero exit on partial failure; resumable rather than restart-from-zero.
- [ ] First Ctrl-C: prompt cleanup + quick exit, status 130 (signal re-raised); second Ctrl-C: immediate; terminal state (echo, cursor, raw mode) restored — tested inside prompts and progress bars.
- [ ] Ctrl-C interrupts in-flight network calls promptly; SIGTERM handled like non-interactive SIGINT.
- [ ] State/config writes are write-tmp-fsync-rename; no truncate-in-place; interrupted runs leave resumable or ignorable state, with a note on next run.
- [ ] Locks self-clean (flock or staleness detection); no "delete the lock file" support folklore.
- [ ] All network calls have connect + overall timeouts and `--timeout`; retries are bounded, jittered, idempotent-only, and announced; offline failure is fast and names the unreachable host.
- [ ] Update check (if any): async, cached, stderr, TTY-only, off under `CI`, killable by env var; self-update opt-in, signature-verified, refuses package-manager-owned installs.
- [ ] Telemetry opt-in or disclosed-on-first-run with documented scope and one-command opt-out; honors `DO_NOT_TRACK`; never collects argv/contents; no hidden network calls (verify with a proxy/strace if suspicious).
- [ ] No new top-level `~/.tool*` litter: config/data/state/cache in XDG locations, env vars respected; cache survives `rm -rf` (tool regenerates); token files 0600 and checked.
- [ ] Flags/exit codes/JSON fields never removed or repurposed without deprecation warnings naming the replacement; deprecated aliases still function for a full cycle.
- [ ] `tool completion bash|zsh|fish` works and is generated from the parser source; dynamic completion is fast, offline-safe, and silent on failure.
