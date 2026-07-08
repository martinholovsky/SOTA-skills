# 02 — Output, Exit Codes & Interaction

Scope: stdout/stderr contract, machine-readable output, TTY detection, color,
exit codes, streaming, progress, prompts, verbosity levels, error messages.

## 1. The stream contract

- **stdout = the product. stderr = the process.** Primary output — the data the
  command exists to produce — goes to stdout. Logs, progress, spinners,
  warnings, prompts, errors, "Done in 3.2s" — all stderr.
- The test: `tool cmd | next-tool` must feed `next-tool` only data;
  `tool cmd > out.json` must still show the human progress and errors on the
  terminal (because they're on stderr).

  ```
  # Bad — log line corrupts the JSON consumer:
  $ tool export | jq .
  parse error: Invalid literal at line 1: "Connecting to api.example.com..."

  # Good:
  $ tool export 2>err.log | jq .name   # data flows; chatter captured separately
  ```

- Success on a pure mutation may print a one-line confirmation to **stderr**
  (it's status, not output) — or print the created resource's ID to stdout,
  because that's data scripts will capture. Decide per command; be consistent.
- Never write log lines and data interleaved on stdout "because the user sees
  one terminal". They see one terminal; their pipes don't.

## 2. Machine-readable output

- **Every command that lists or reads data gets `--json`.** Output format is
  API: the moment someone greps your human table, you're locked into its
  whitespace forever. `--json` gives them a stable contract instead.
  - JSON mode: pure JSON on stdout, nothing else; one document, or **NDJSON
    (one object per line) for streams/lists** so consumers can process
    incrementally and `head`/`grep` keep working.
  - Field names are versioned API surface: additive changes only; renames go
    through deprecation (rules/03 §7).
  - Errors in JSON mode are JSON too (on stderr or as a final object — pick one
    and document it), with `code`/`message` fields, plus the nonzero exit.
- Human table mode: no table borders/box-drawing — they're noise and break
  `awk`/`grep`. Columns separated by whitespace, one record per line, header
  row suppressible (`--no-header`) or absent when piped. A `--plain` flag that
  strips alignment/truncation keeps line-oriented tools viable without JSON.
- `-o/--output <format>` (`json|yaml|table|...`) scales better than flag
  proliferation if you'll ever support more than two formats; `--json` can
  remain as sugar.
- A `--format`/`--template` (Go-template/jsonpath-style) option is a power
  feature, not a substitute for `--json`.

## 3. Exit codes are API

- `0` = success, **only** success. Partial failure is not success: `tool sync`
  that failed 3 of 10 items must not exit 0 just because it printed warnings.
  CI reads `$?`, not your prose.
- Differentiate at minimum:
  - `0` success
  - `1` operational failure (the thing failed)
  - `2` usage error (bad flags/args — matches widespread Unix convention)
  - further codes for failure classes scripts must distinguish
    (e.g. `3` = check found violations, like `grep`'s "no match" `1` vs error `2`)
- `130` after SIGINT (128+signal, the shell convention) — most runtimes do this
  if you re-raise the signal after cleanup rather than `exit(1)` (rules/03 §3).
- Document every code in `--help`/man. Undocumented codes are unusable;
  scripts will treat all nonzero alike and lose the distinction you built.
- Never `exit(0)` from a generic top-level error handler. Audit: search for
  exception/panic handlers that print and fall through to a normal return.
- `--help`/`--version` exit 0; unknown flag exits 2.

## 4. TTY detection, color & terminal respect

- Detect per stream: `isatty(stdout)` gates color/animation **on stdout**,
  `isatty(stderr)` gates spinners/progress **on stderr**, `isatty(stdin)` gates
  prompts. A pipe on stdout must not kill the progress bar on a TTY stderr.
- Color policy, in precedence order:
  1. `--color`/`--no-color` flag (or `--color=always|never|auto`)
  2. `NO_COLOR` env var **set and non-empty** → no color (per no-color.org;
     empty string does *not* disable). `CLICOLOR_FORCE`/`FORCE_COLOR` non-empty
     → force color (de facto conventions; support if low-cost)
  3. auto: color only if the stream is a TTY and `TERM` is set and ≠ `dumb`
- `--color=always` must exist — users pipe through `less -R` and CI renderers
  that handle ANSI. Auto-detection alone strands them.
- Color conveys redundant emphasis, never sole meaning (colorblind users,
  `NO_COLOR` users): "error:" prefix in red, not red-means-error alone.
- Pager: output known to be long (help dumps, logs) may auto-page on a TTY via
  `$PAGER` (default `less -FRX` behavior: quit if one screen). Always
  bypassable; never page when piped.
- Handle `SIGPIPE`/`EPIPE` gracefully: `tool list | head -3` must not print a
  panic/traceback after `head` exits. Exit silently (conventionally 141).
- Don't query or assume terminal width when not a TTY; when a TTY, wrap/truncate
  to width but never truncate in `--plain`/`--json` modes.

## 5. Streaming & progress

- **Stream results as they're produced**; don't buffer the full result set and
  dump at the end. The user gets feedback, pipes get data early, and `head`
  terminates work early. Line-buffer stdout when piped (block buffering can
  hold output for minutes on slow producers).
- Anything that can exceed ~2s shows progress on stderr (TTY only):
  spinner for indeterminate, progress bar with units (`12/87 files, 3.1 MB/s`)
  when total is known, step log (`[2/5] Building image…`) for phases.
- Progress must include enough to act on: current item name (so a hang is
  diagnosable), rate, ETA when honest.
- When not a TTY: replace animation with occasional plain log lines on stderr
  (e.g. one line per phase) — CI logs full of `\r` spinner frames or a
  thousand progress-bar redraws are a classic audit finding.
- First feedback within ~100ms of invocation (even just validating args or a
  "Resolving dependencies…" line) — silence reads as a hang.

## 6. Prompts

- Prompt **only** when stdin is a TTY. stdin closed or piped ⇒ take the
  documented default or fail fast naming the flag that supplies the answer.
  A CLI that hangs in CI awaiting input that will never come is a Critical
  finding.
- **Never require a prompt**: every interactively-gathered value has a
  flag/env/config path. `--yes`/`-y` accepts benign confirmation defaults;
  `--no-input` forces "fail instead of prompting" for strict CI.
- Prompts go to stderr (stdout may be redirected); read from `/dev/tty` only if
  you must prompt despite redirected stdin — and prefer not to.
- Confirmation default is the safe answer: `Continue? [y/N]` — Enter aborts.
- Password input: no echo, and verify the no-echo path actually engages when
  stdin is a TTY; never read passwords from argv (rules/01 §3).
- Interactive convenience must never be the only path: a fancy selector
  (fuzzy-pick a target) is sugar over `tool deploy <target>`, not a replacement.

## 7. Error messages

- Anatomy of an actionable error — **what failed, why, how to fix**:

  ```
  # Bad:
  $ tool deploy api
  Error: operation failed

  # Good:
  $ tool deploy api
  error: cannot read config file ./tool.toml
  cause: line 14: unknown key "tiemout" (did you mean "timeout"?)
  hint: edit ./tool.toml or regenerate with 'tool config init'
  ```

  Include the concrete noun: full path, URL, resource name, offending value.
  "Permission denied" without *which file* sends the user to strace.
- The fix line is the highest-value text in your tool. If the remedy is a
  command, print the command, copy-pasteable.
- **No stack traces at users by default.** Catch at the top level, print the
  human message, exit nonzero. Full traceback behind `--debug`/`TOOL_DEBUG=1`,
  plus a one-liner telling users to use it / where to report bugs. Audit:
  any user-reachable input that produces a raw traceback is at least Medium.
- Errors to stderr, prefixed (`error:`/`warning:`), lowercase-after-prefix,
  no exclamation marks, no blame ("you provided an invalid…" → "invalid…").
- Expected-failure paths (not found, no match, already exists) are concise
  one-liners with distinct exit codes — not walls of context meant for bugs.

## 8. Verbosity levels

- Three dials, independent of data output:
  - `-q/--quiet`: suppress non-error stderr chatter; errors still print; exit
    codes unchanged. (`-qq`/`--silent` to also suppress errors is optional —
    scripts that only want `$?`.)
  - default: progress + key status lines on stderr.
  - `-v/--verbose`, repeatable (`-vv`, `-vvv`): more diagnostic detail on
    stderr — what's being read, requests made, timing.
  - `--debug`: everything + internals (stack traces, wire dumps) — for bug
    reports. May alias `-vvv`.
- Verbosity changes **stderr only**. `-v` must never add fields or lines to
  stdout data, and `-q` must never remove data from stdout — otherwise scripts
  change behavior based on log level.
- Log-style stderr lines in verbose modes carry level prefixes
  (`debug:`/`info:`) so users can grep; honor `TOOL_LOG=debug`-style env
  config if the tool embeds a logger.
- Redact secrets in every verbosity, including `--debug` wire dumps
  (`Authorization: Bearer ***`). Verbose modes leaking tokens into CI logs is
  a Critical finding.

## 9. AI agents as a third user

- **Agents are now a consumer class of their own** alongside the human at a
  TTY and the script in CI — a stricter script: everything above (pure
  `--json`, structured errors, distinct exit codes, never prompt on non-TTY)
  applies, plus the constraints below. A well-designed CLI is a peer agent
  interface to an MCP server, not a lesser one.
- Once agents drive the tool, the surface is **frozen, additive-only**: agents
  act on stale knowledge of your flags for months, so never remove or
  repurpose — only add (rules/03 §7, with less slack).
- **Output costs context window.** Offer `--fields` (or equivalent) to select
  top-level JSON fields; keep default JSON lean; paginate large lists.
- Put the remediation in-band: JSON-mode errors carry `code`/`message` plus a
  machine-actionable `remediation` (the exact command to run) — an agent can
  act on that, not on prose (§7's fix line, machine-readable).
- Mutations: replace the interactive confirmation with a **confirmation
  envelope** — the first call returns the concrete plan, a distinct exit
  code, and the exact re-invocation (e.g. with `--confirm`); executing
  requires that second call. Never gate a mutation on a TTY prompt an agent
  cannot answer.
- **Validate inputs locally before any network call**: agents hallucinate
  plausible-looking values (wrong-format IDs, invisible control characters);
  a precise client-side error beats a round-trip and a vague 404.
- Consider suppressing did-you-mean suggestions in machine modes: for an
  agent, an unknown command should be a hard, unambiguous failure, not a
  guess it may adopt (rules/01 §1's never-auto-execute rule still holds).

## Audit checklist

- [ ] Data on stdout only; logs/progress/prompts/errors on stderr; verified by `tool cmd >out 2>err` inspection.
- [ ] `tool list | jq .` works: no ANSI, no banner, no log lines in the stream.
- [ ] `--json` (or `-o json`) on every list/read command; NDJSON for streams; JSON-mode errors are machine-readable; fields treated as versioned API.
- [ ] Human tables: no borders; `--plain`/`--no-header` or auto-plain when piped.
- [ ] Exit codes: 0 only on full success; usage errors = 2; distinct documented codes for failure classes; partial failure ≠ 0; no `exit 0` in catch-all handlers.
- [ ] SIGINT exits 130; `tool list | head` causes no EPIPE traceback.
- [ ] Color: auto by TTY; `NO_COLOR` (non-empty) and `TERM=dumb` disable; `--color=always|never|auto` supported; color never sole carrier of meaning.
- [ ] Output streams incrementally; stdout line-buffered when piped; no end-of-run dumps for long operations.
- [ ] >2s operations show progress on stderr (TTY); non-TTY gets sparse plain lines, no `\r` animation spam in CI logs.
- [ ] First output within ~100ms; no silent multi-second startup.
- [ ] No prompt when stdin is not a TTY: `tool cmd </dev/null` never hangs; `--yes`/`--no-input` paths exist; prompts on stderr; safe default answer.
- [ ] Errors name the failing path/value, state the cause, and give a copy-pasteable fix; stack traces only under `--debug`; errors prefixed and on stderr.
- [ ] `-q` and `-v`/`-vv` exist; verbosity alters stderr only; stdout data identical at every level.
- [ ] No secret/token appears at any verbosity level, including `--debug`.
- [ ] Agent-facing surface: JSON output field-selectable (`--fields` or equivalent); JSON-mode errors include a machine-actionable remediation; mutations offer a non-interactive confirm protocol (plan + explicit `--confirm` re-invocation), not a TTY-only prompt.
- [ ] Inputs validated locally (format/charset) before network calls; in machine modes unknown commands/flags fail hard rather than fuzzy-matching.
