# 01 — Commands, Flags, Args & Configuration

Scope: subcommand grammar, POSIX/GNU flag conventions, args vs flags vs stdin,
defaults, dangerous operations, config precedence, env var naming, help text.

## 1. Command grammar

- Pick **one** subcommand ordering scheme and never mix:
  - `noun verb` (`tool repo clone`, `tool repo list`) — scales best when nouns
    multiply; group help by resource. Prefer this for tools with >1 resource type.
  - `verb noun` (`tool get pods`) — fine for query-centric tools; commit to it.
  - Bad: `tool repo clone` next to `tool list-users` next to `tool prune repos`.
    Three grammars = user must memorize every command individually.
- Single-purpose tools need **no subcommands** (`grep`, `jq`). Don't invent
  `tool run` as the only subcommand; make the tool do its thing directly.
- Names: lowercase, single word; verbs from the conventional set — `list, get,
  create, delete, update, add, remove, run, start, stop, status, init, config,
  login, logout, version, completion, help`. Don't coin `enumerate` when `list`
  exists; don't have both `delete` and `remove` meaning different things.
- Aliases are fine (`ls` → `list`, `rm` → `delete`) but help shows the canonical
  name and the alias resolves everywhere (completion, docs).
- Max depth: two levels of subcommand (`tool noun verb`). A third level
  (`tool a b c`) is a smell — usually the third word is really an argument.
- Reserve and implement: `tool help <cmd>` ≡ `tool <cmd> --help`,
  `tool version` ≡ `tool --version`, `tool completion <shell>`.
- **Suggest on typo** (Levenshtein over the command table), then exit nonzero:

  ```
  $ tool stauts
  error: unknown command "stauts"
  Did you mean "status"?
  Run 'tool --help' for usage.
  $ echo $?
  2
  ```

  Never auto-execute the guess — `tool prune` guessed from `tool prun` deleting
  data is unforgivable. (cobra: disable `SuggestionsMinimumDistance` auto-run is
  default-safe; clap: `suggestions` on by default; argparse: add a custom hook.)
  Agent-facing/machine modes may disable suggestions entirely (e.g. cobra's
  `DisableSuggestions`) — for an AI agent an unknown command should fail hard,
  not offer a guess it might adopt (rules/02 §9).

## 2. Flag syntax — POSIX/GNU, no improvisation

- **Every flag has a long form** (`--output`); short forms (`-o`) only for the
  handful used constantly. Long-only flags are self-documenting in scripts and
  CI configs — that's where flags get read by other humans.
- Support standard GNU behavior: bundling (`-abc` = `-a -b -c`), `--flag=value`
  and `--flag value`, `--` terminates flag parsing (everything after is
  positional — mandatory for tools that accept filenames, which can start with `-`):

  ```
  $ tool delete -- --weird-filename
  ```

- Repeatable flags for lists: `-v -v` for verbosity, `--tag a --tag b` for
  values. Prefer repetition over ad-hoc delimiters (`--tag a,b` may be offered
  *additionally*, but commas appear in real values).
- Never invent single-dash long flags (`-output`). Java-style `-Dkey=val` and
  Go's single-dash flags exist; don't propagate them in new tools.
- Flag names: kebab-case (`--dry-run`, not `--dryRun`/`--dry_run`); booleans
  are plain switches with a `--no-<flag>` negation when the default is true
  (`--color` / `--no-color`).
- **Same flag, same meaning, everywhere.** `-o` must not mean `--output` in one
  subcommand and `--organization` in another. Maintain a global flag registry;
  audit collisions in review.
- Standard names users already know — don't get creative:
  `-h/--help`, `--version`, `-q/--quiet`, `-v/--verbose`, `-o/--output`,
  `-f/--force`, `-n/--dry-run` (or `--dry-run` long-only), `--json`, `--yes`,
  `--no-color`, `--config`, `-C <dir>` (run as if in dir).
  Note the trap: `-v` is verbose in most tools but version in some — pick
  verbose, give version only `--version` (and `-V` if you must).

## 3. Args vs flags vs stdin

- Positional args only for the **primary object(s)** of the command, the thing
  you'd say in the sentence: `tool deploy <service>`, `rm file1 file2`.
- One type of positional is fine; two types (`tool copy <src> <dst>`) is the
  ceiling; three or more positionals of different meanings is a design bug —
  switch the extras to flags. Order-dependence is where users make mistakes.
- Everything optional, every modifier, every "how" → flag. Flags are
  self-documenting at the call site and reorderable.
- **No required flags on the common path.** If `--region` is required for every
  invocation, it's not a flag, it's missing config/default. Required flags are
  acceptable only on rare expert subcommands.
- stdin: accept `-` as a filename meaning stdin (GNU convention); read data
  from stdin when no file arg is given **and stdin is not a TTY**:

  ```
  $ cat payload.json | tool apply        # data via pipe
  $ tool apply -f payload.json           # same, explicit
  $ tool apply                            # TTY stdin: don't hang — print usage
  ```

  Never silently block reading a TTY stdin the user didn't intend to type into.
- Secrets: **never as argv** (`--password hunter2` is visible in `ps`, shell
  history, CI logs). Accept via file (`--password-file`), stdin
  (`--password-stdin`, the docker pattern), or interactive no-echo prompt.
  Env vars for secrets are a last resort — they leak into child processes and
  crash dumps; if supported, document the risk.

## 4. Defaults

- The zero-flag invocation must do the obviously useful, **safe** thing.
  Optimize for the 80% case; flags exist for the 20%.
- Defaults must be visible: show effective values in `--help`
  (`--timeout <secs>   request timeout (default: 30)`) and provide
  `tool config list`/`--show-config` to print the fully resolved configuration
  **with the source of each value** (flag/env/file/default) — this single
  feature kills most "works on my machine" config bugs.
- Default to the least destructive interpretation. `tool clean` defaulting to
  "delete everything matching" is wrong; default narrow, widen with flags.

## 5. Dangerous operations

- Destructive/irreversible commands (delete, overwrite, force-push, prune):
  - On a TTY: confirm interactively; for severe cases require typing the
    resource name (the GitHub repo-deletion pattern), not just `y`.
  - Non-TTY/script: **refuse with a clear error** naming the bypass flag —
    never hang on a prompt, never assume yes:

    ```
    $ tool env delete prod < /dev/null
    error: refusing to delete environment "prod" without confirmation
    hint: pass --force to delete without prompting
    $ echo $?
    1
    ```

  - `--force`/`-f` bypasses confirmation; `--yes`/`-y` answers benign prompts.
    Keep them distinct — `--yes` must not unlock destructive paths.
- Big blast radius needs friction proportional to damage: deleting one item =
  `y/N`; deleting a namespace = type its name; `--all` + `--force` together for
  "everything".
- Pair every dangerous op with `--dry-run` (rules/03 §2) and, where feasible, a
  grace mechanism (trash/soft-delete/`undo`, or print what to back up first).

## 6. Configuration precedence

- Exactly this chain, highest wins, documented in `--help`/docs verbatim:

  1. command-line flags
  2. environment variables
  3. project-level config (e.g. `./.toolrc`, `./tool.toml` — found by walking
     up from cwd, stopping at repo root or `$HOME`)
  4. user-level config (`$XDG_CONFIG_HOME/tool/config.toml`, see rules/03 §6)
  5. system-level config (`/etc/tool/…`) — only if genuinely needed
  6. built-in defaults

- Resolution must be **deterministic and explainable**. If two project files
  could apply, define the rule (nearest wins) and surface it in
  `--show-config`'s source column.
- Every config key gets a flag; most get an env var. Not every flag needs a
  config key (one-shot flags like `--dry-run` shouldn't be configurable —
  a config file silently forcing dry-run, or worse `force=true`, is a trap).
- One config format. TOML or YAML for human-edited config; JSON only if humans
  never touch it (no comments). Validate on load and report the file and key:
  `error: ~/.config/tool/config.toml: unknown key "tiemout" (did you mean "timeout"?)`.

## 7. Environment variables

- Namespace everything: `TOOL_*` (`TOOL_API_URL`, `TOOL_LOG_LEVEL`). Unprefixed
  names (`TIMEOUT`, `DEBUG_MODE`) collide with the user's environment and other
  tools. `TOOL_DEBUG=1` not `DEBUG=1` — though *reading* the conventional
  generics below is fine.
- Respect the conventional generics rather than reinventing them:
  `NO_COLOR`, `TERM`, `EDITOR`/`VISUAL`, `PAGER`, `HTTP_PROXY`/`HTTPS_PROXY`/
  `NO_PROXY`, `TMPDIR`, `XDG_*`. Also honor `CI` (set by virtually every CI
  system) as a signal to disable interactivity and fancy output.
- Env vars are for context that varies per environment (endpoints, proxies,
  CI), not for per-invocation behavior — that's what flags are for.
- Boolean env vars: treat set-and-non-empty as true, but accept `0`/`false` as
  false to match user expectations; document which convention you use.

## 8. Help text

- `-h` and `--help` work on the root and **every** subcommand, print to stdout,
  exit 0, and never trigger side effects (no config load failures, no network).
- Invoked with no args and no obvious default action: print concise help (or a
  short usage + hint) and exit **nonzero** — no-args is usually a mistake, and
  exit 0 would hide it from scripts. If the tool *has* a sensible default
  action, do that instead.
- Help structure, in order: one-line description; usage line
  (`tool <command> [flags] <arg>`); **examples first among the detail** — 2-3
  real, copy-pasteable invocations covering the common cases; then flags
  (short, long, value placeholder, description, default); then a docs URL.
- Usage-line notation: `<required>`, `[optional]`, `...` repeatable, `|`
  alternatives. Keep placeholders meaningful: `--output <format>` not
  `--output <value>`.
- Wrong usage gets a targeted error + the relevant usage line + exit code 2 —
  not the full help dump (which scrolls the actual error off-screen):

  ```
  $ tool deploy
  error: missing required argument <service>
  usage: tool deploy <service> [flags]
  Run 'tool deploy --help' for details.
  ```

- Keep `--help` accurate by construction: generate docs/man/completions from
  the same parser definitions (rules/04 §3).

## Audit checklist

- [ ] One subcommand grammar (noun-verb or verb-noun) used consistently; conventional verb names; ≤2 levels deep.
- [ ] Unknown command/flag → suggestion + nonzero exit; never auto-executes the guess.
- [ ] Every flag has a long form; kebab-case; `--flag=value` and `--` separator work; repeated flags accumulate.
- [ ] No short-flag meaning collisions across subcommands; standard names (`-h`, `-q`, `-v`, `-o`, `-f`, `--json`, `--yes`) mean the standard things.
- [ ] ≤2 positional arg types per command; everything else is a flag; no required flags on common-path commands.
- [ ] `-` accepted for stdin where files are accepted; no command silently blocks reading TTY stdin.
- [ ] No secret accepted via argv; file/stdin/no-echo-prompt paths exist.
- [ ] Destructive ops: TTY confirmation (typed name for severe), non-TTY refuses with `--force` hint, `--yes` ≠ `--force`.
- [ ] Config precedence is flags > env > project > user > system > defaults, deterministic, and documented; `--show-config` (or equivalent) prints resolved values with sources.
- [ ] Config parse errors name file + key and suggest near-misses; unknown keys are errors or loud warnings, not silence.
- [ ] All tool-specific env vars carry the `TOOL_` prefix; `NO_COLOR`, proxy vars, `EDITOR`, `PAGER`, `CI` respected.
- [ ] `-h/--help` on every subcommand: stdout, exit 0, no side effects, examples present, defaults shown.
- [ ] Usage errors print the specific error + short usage + exit 2, not the full help wall.
