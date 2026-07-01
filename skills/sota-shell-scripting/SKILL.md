---
name: sota-shell-scripting
description: >-
  State-of-the-art shell scripting (bash-focused, defensive) for writing and auditing shell scripts, CI scripts, init/deploy scripts, container entrypoints, and Makefile recipes. Use when the task involves creating, modifying, reviewing, or hardening any shell code — trigger keywords: bash, shell script, sh, zsh, shellcheck, shfmt, CI script, Makefile shell, entrypoint script, set -euo pipefail, dotfiles, install script, cron job, wrapper script.
---

# SOTA Shell Scripting

Purpose: produce shell scripts that survive contact with reality — unusual filenames, missing
commands, partial failures, hostile input, signals, and concurrent invocation — and audit
existing scripts for the defect classes that cause most production shell incidents:
unquoted expansions, silent error swallowing, injection, secret leakage, and temp-file races.

Bash-focused (bash 5.x current; macOS ships bash 3.2 and defaults to zsh — see portability
rules). POSIX `sh` only when the target demands it (busybox/dash containers, init systems).

## First decision: should this be shell at all?

**Do NOT use shell when any of these hold.** Recommend Python/Go (or the project's primary
language) instead, and say so explicitly in BUILD and AUDIT output:

- Script exceeds ~100 lines of actual logic (not counting boilerplate/usage text).
- Needs real data structures (nested maps, JSON manipulation beyond a `jq` one-liner, sets).
- Needs granular error handling (retry *this* step, distinguish error kinds, partial rollback).
- Does arithmetic beyond integers, date math, or float comparison.
- Parses structured formats (JSON/YAML/XML) with string surgery instead of `jq`/`yq`.
- Needs portable concurrency beyond "run N jobs and `wait`".
- Is security-critical input handling (auth, parsing untrusted network data).

Shell is the right tool for: gluing processes together, CI steps, container entrypoints,
small install/deploy wrappers, environment setup — anything that is mostly *invoking other
programs* rather than computing.

## BUILD mode

When writing or modifying shell scripts:

1. **Pick the dialect deliberately.** `#!/usr/bin/env bash` unless the target is a minimal
   container/init context that only guarantees POSIX `sh`. Never `#!/bin/sh` with bashisms.
2. **Start every bash script from the safety preamble** (rules/01): `set -euo pipefail`,
   trap-based cleanup, `IFS` discipline — and know where `set -e` does NOT fire.
3. **Quote every expansion.** `"$var"`, `"$@"`, `"$(cmd)"`. Build commands with arrays,
   never with string concatenation.
4. **Errors are loud and routed to stderr** with script name + context; exit codes are
   meaningful and documented in `--help`.
5. **Make it idempotent and interrupt-safe**: `mktemp` + `trap` cleanup, atomic writes via
   `mv`, check-before-create, `flock` if concurrent runs are possible.
6. **Run `shellcheck` (treat all findings as blockers, suppress only with a justifying
   comment) and `shfmt -d` before declaring done.** If they are unavailable locally, state
   that and flag CI must run them.
7. Provide `--help` always; `--version` for distributed tools; `set -x` behind a
   `DEBUG`/`TRACE` env guard, never unconditionally (secret leakage).

## AUDIT mode

When reviewing existing shell scripts, hunt the defect classes in rules/ files bottom-up
(each rules file ends with an audit checklist of grep patterns and ShellCheck codes).
Run `shellcheck -S style` on every script if available; correlate findings with context —
ShellCheck flags symptoms, you judge exploitability and blast radius.

Severity conventions:

| Severity | Meaning | Examples |
|---|---|---|
| CRITICAL | Exploitable or data-destroying now | `eval` on untrusted input; unquoted var in `rm -rf`; secrets in argv/`set -x`; curl\|bash of unpinned URL in prod |
| HIGH | Will corrupt/fail on realistic input or failure | unquoted expansions in destructive paths; missing `set -e`/error checks around critical steps; predictable temp files; non-atomic config writes; missing `exec` in entrypoint (signals lost) |
| MEDIUM | Latent bug or fragility | parsing `ls`; `which` instead of `command -v`; missing `pipefail`; no `--` separators; no timeouts on network calls; `echo` for variable data |
| LOW | Style/maintainability with safety implications | missing `local`; `[ ]` where `[[ ]]` intended; missing `readonly`; inconsistent error messages |

Finding format:

```
[SEVERITY] file:line — short title (SCxxxx if applicable)
  Evidence: the offending line(s), verbatim
  Impact: what input/condition triggers it and what breaks
  Fix: concrete replacement code
  Effort: trivial | small | medium | large
```

## Rules index

| File | Covers |
|---|---|
| [rules/01-safety-baseline.md](rules/01-safety-baseline.md) | Shebang discipline, `set -euo pipefail` and its real limitations, quoting & word-splitting bug catalog, arrays, IFS, traps & mktemp cleanup, `[[ ]]`, printf, local/readonly, globbing pitfalls, never parse ls |
| [rules/02-robustness-correctness.md](rules/02-robustness-correctness.md) | Argument parsing (getopts/while-case, --help/--version), input validation, POSIX vs bash portability, stderr/exit-code discipline, PIPESTATUS, command -v, network timeouts & retries, flock & background jobs, idempotency & atomic writes, safe filename handling |
| [rules/03-security.md](rules/03-security.md) | eval/injection, secrets discipline (argv/env/set -x), PATH hygiene, sudo discipline, curl\|bash both directions, temp-file races, umask, ShellCheck+shfmt in CI |
| [rules/04-ci-and-operational.md](rules/04-ci-and-operational.md) | GitHub Actions shell pitfalls (`${{ }}` injection, multiline run, quoting in YAML), container entrypoints (exec, PID 1, privilege drop), Makefile shell gotchas, long-running script logging |

## Top 10 non-negotiables

1. `#!/usr/bin/env bash` + `set -euo pipefail` on every bash script — and explicit error
   handling where `-e` is known not to fire (conditions, `&&`/`||`, command substitution
   in assignments-with-modifiers, process substitution).
2. Quote **every** expansion: `"$var"`, `"$@"`, `"${arr[@]}"`, `"$(cmd)"`. SC2086 is a
   bug, not style.
3. Build argument lists with arrays; pass them as `"${args[@]}"`. Never accumulate a
   command in a string and `eval`/word-split it.
4. `trap cleanup EXIT` with an idempotent cleanup function; temp paths only via `mktemp`.
5. Never `eval`, `bash -c`, or `sh -c` with interpolated untrusted data; use `--` before
   positional file/user arguments to every command that supports it.
6. No secrets in argv, in environment dumps, or under `set -x`; `set +x` around sensitive
   sections; read secrets from files or fds.
7. Errors to stderr with context (`script: failed to X: $detail`); meaningful exit codes;
   never `exit 0` on failure paths.
8. Network calls get `--fail`, `--max-time`/timeouts, and bounded retries — never bare
   `curl url | ...`.
9. Handle arbitrary filenames: `find -print0 | xargs -0` / `-exec ... +`, `while IFS= read -r`,
   never iterate `$(ls)` or unquoted globs from variables.
10. ShellCheck (clean, or annotated suppressions) + shfmt enforced in CI; a shell script
    without CI linting is unreviewed code.

## Cross-references

- CI pipeline hardening, `${{ }}` injection, action pinning → `sota-devsecops`
- Secret storage/rotation → `sota-secrets-management`
- Container image/runtime hardening → `sota-sandboxing`, `sota-cloud-infrastructure`
- When the "don't use shell" rule fires → `sota-python` / `sota-golang`
