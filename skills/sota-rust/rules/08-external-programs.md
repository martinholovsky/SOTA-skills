# 08 — Running External Programs (`std::process::Command`)

Split out of rules/05 (formerly section 9) on 2026-09-25, when rules/05 reached the 500-line
cap; the section is now §1.

## 1. Running external programs — `std::process::Command`

`Command` takes a program plus an argument vector and **there is no shell**: the
docs are explicit that "shell syntax like quotes, escaped characters, word
splitting, glob patterns, variable substitution, etc. have no effect". That makes
the classic injection hard to write by accident and moves the risk somewhere else.
Behaviour below was **measured on rustc 1.97.1 / tokio 1.53, macOS** unless a doc
is quoted; re-check the platform-specific items on your target.

**R9.1 — Arguments are never split, by either API.** `.arg("-l -a")` passes the
single argument `-l -a` (measured), and `.args([..])` merely iterates — neither
splits on whitespace. The Rust mistake is therefore the *inverse* of the shell
one: a string assembled as though it were a command line arrives as one nonsense
argument, and `Command::new("ls -l")` looks for a program literally named `ls -l`.
That failure is loud and harmless. The dangerous spelling is the one that puts a
shell back:

```rust
// BAD — a shell, and therefore injection, is back
Command::new("sh").arg("-c").arg(format!("convert {path} out.png"))
// GOOD — absolute program, argv, end-of-options, no shell
Command::new("/usr/bin/convert").arg("--").arg(&path).arg("out.png")
```

**R9.2 — Argument injection survives argv.** A value beginning with `-` becomes a
flag. Pin your own flags first, then `--`, then validated operands; prefer a
library binding to a CLI wrapper for attacker-influenced parameters.
`sota-sandboxing` rules/04 §5 lists the exec-capable argument gadgets
(`find -exec`, `tar --checkpoint-action`, `ssh -o ProxyCommand`, …) to check for.

**R9.3 — Windows `.bat`/`.cmd` is a documented exception (CVE-2024-24576, CVE-2024-43402).**
`cmd.exe` and batch files decode their command line non-standardly, so argv-safety
does not hold there: before **Rust 1.77.2**, passing untrusted arguments to a batch
file could run arbitrary shell commands. That fix was bypassable — Windows strips
trailing whitespace and periods from a path, so a name like `x.bat. .` still ran as
a batch file without the mitigation (CVE-2024-43402, fixed in **Rust 1.81.0**;
blog.rust-lang.org, 2024-09-04). The fix did not make escaping safe — the
standard library now **returns an `InvalidInput` error when it cannot safely escape
an argument**, and the current `Command` docs still carry the warning that for
`cmd.exe` "a malicious argument can potentially run arbitrary shell commands". So:
MSRV **≥ 1.81.0** for anything that may run on Windows (1.77.2 is the bypassable
first fix), propagate that
`InvalidInput` rather than unwrapping it, and treat `CommandExt::raw_arg` as
trusted-input-only.

**R9.4 — Dropping a `Child` neither kills nor reaps it.** "There is no
implementation of `Drop` for child processes, so if you do not ensure the `Child`
has exited then it will continue to run, even after the `Child` handle to the child
process has gone out of scope" — measured: still alive 600 ms after the handle was
dropped. The same docs warn that a terminated-but-unwaited process "is still around
as a *zombie*" and that too many "may exhaust global resources (for example process
IDs)". So an error path that returns early while holding a `Child` leaks a *running
process*, not just a handle — and `?` makes that the easy path to write. Own the
child on every exit route, including the error and cancellation ones.

**R9.5 — `std` has no timeout, and a tokio timeout does not kill the child.**
Neither `wait()` nor `wait_with_output()` takes a deadline, and `wait_with_output()`
waits for **EOF on the pipes**, which a grandchild that inherited them can hold open
indefinitely. Measured, and this is where Rust differs from Go (whose `Wait` blocks
past context cancellation unless `cmd.WaitDelay` is set):
`tokio::time::timeout(2s, child.wait_with_output())` **does** fire at 2.0 s under
exactly that pipe-holding grandchild, so Rust needs no `WaitDelay` equivalent.
But firing only cancels *your future* — the child and its grandchild keep running.
Pair the deadline with `.kill_on_drop(true)` (measured: the child is gone 600 ms
after the handle drops) or kill and `wait()` explicitly. In sync code the
long-standing option is the `wait-timeout` crate — mature rather than active (last
release 2025-02, still 0.2.x, ~50M recent downloads), so check its upstream health
before adopting it (`sota-devsecops` rules/10 §5); otherwise use a supervisor
thread you actually join. Never abandon a thread parked in `wait()`. Killing the
direct child does not signal its *group*: for that, spawn it into its own group
with `process_group(0)` (Unix, stable since **1.64**) and signal the group.

**R9.6 — Output is buffered without a cap.** `output()`/`wait_with_output()`
collect the child's stdout into a `Vec<u8>` with no limit — measured, 5 MB of
`/dev/zero` buffered without complaint, and a hostile child can make that
unbounded. For anything attacker-influenced, take `Stdio::piped()` and read with an
explicit `.take(MAX)`, or send output to a file or `Stdio::null()`.

**R9.7 — Environment and program resolution both have sharp edges.** The child
inherits the parent's environment by default. `env_clear()` gives it **zero**
variables (measured) — but a *bare* program name still resolves, because with
`PATH` removed `execvp` falls back to an OS-defined default (the docs say typically
`/bin:/usr/bin`, "not the parent's `PATH`"): measured, bare `uname` still ran while
a binary present only in the process's working directory did **not**, so that
fallback did not include `.` here. Do not rely on either half — **pass an absolute
path**. Relative program paths are worse: the docs call the interpretation relative
to the parent's cwd versus `current_dir` "platform specific and unstable" and
recommend `canonicalize`; measured on macOS, `Command::new("./p").current_dir(d)`
ran `d/p`. Use `uid`/`gid` to drop privilege where relevant (both trigger
`setgroups(0, NULL)` unless groups are set explicitly, dropping supplementary
groups). `CommandExt::pre_exec` is `unsafe` for a real reason — the closure runs
after `fork` in the child, where "normal operations like `malloc`, accessing
environment variables through `std::env` or acquiring a mutex are not guaranteed to
work"; keep it async-signal-safe or use a purpose-built crate.

**R9.8 — Code evaluation from input runs a program without a `Command`.** Rust has no
`eval`, so dynamic code evaluation arrives through a crate: an embedded interpreter fed a
caller's text (`mlua` `lua.load(src).exec()`, `rhai::Engine::eval`/`run`, an embedded JS
engine), a plugin loaded from a caller-influenced path (`libloading::Library::new` is an
`unsafe fn` because loading "executes initialisation routines"), or a registry that
resolves a type or function name taken from input. Read in mlua 0.12.1, rhai 1.26.1,
libloading 0.9.0 and measured on rustc 1.97.1:
- **mlua's "safe" is memory safety, not a sandbox.** `Lua::new()` loads the *safe subset*
  and `os.execute` and `io.open` were both present (measured, `lua54`). Untrusted text
  gets `Lua::new_with(StdLib::TABLE | StdLib::STRING | StdLib::MATH, LuaOptions::default())`
  — measured: no `os`, no `io`.
- **rhai sets no resource limits.** `Engine::new()` reports `max_operations`,
  `max_string_size` and `max_array_size` as 0, meaning unlimited, so `loop {}` pins a
  thread. Set `set_max_operations` (measured: 100,000 stopped `loop {}` with "Too many
  operations"), `set_max_call_levels`, `set_max_expr_depths` and the size limits.
- **Prefer no evaluation**: a `match` or `HashMap<&str, fn(..)>` dispatch table over an
  allowlist of names, or a parser you own for a fixed grammar (no loops, no host calls).
- **An in-process interpreter is not a security boundary**: an engine bug, or a host
  function you registered, reaches the whole process. Hostile code goes to a separate
  process or Wasm sandbox (`sota-sandboxing` rules/01, rank 7 is treated as no boundary).
OWASP: Code Review Guide; Proactive Controls 2024 C3; ASVS 5.0 V1.3.

For the isolation the child itself needs — seccomp/Landlock, fd-only interfaces,
memory budgets — see `sota-sandboxing` rules/04 §5 and rules/02 R7.2a.

## Audit checklist

- [ ] Subprocess: `rg 'Command::new\("(sh|bash|cmd|powershell)"' -t rust` and
      `rg '\.arg\("-c"\)' -t rust` — a shell with any interpolated value = Critical.
      `rg 'Command::new\(' -t rust` for non-absolute program names on
      attacker-reachable paths = Medium (R9.1, R9.7).
- [ ] Every spawned `Child` is killed **and** waited on every exit path, including
      `?` early-returns and cancellation — `rg 'spawn\(\)' -t rust` and read the
      error paths; a dropped `Child` keeps running and then becomes a zombie
      (R9.4). Deployed code targeting Windows declares MSRV **≥ 1.81.0** (R9.3;
      1.77.2 fixed CVE-2024-24576 but not its bypass CVE-2024-43402).
- [ ] Every subprocess wait has a deadline **and** a kill: a bare
      `wait()`/`wait_with_output()` = High on any attacker-influenced child, and a
      `tokio::time::timeout` without `.kill_on_drop(true)` (or an explicit kill)
      leaves the child running when it fires (R9.5).
- [ ] **Dynamic code evaluation from input (R9.8) — Critical if the text is
      caller-influenced, else Medium** —
      `rg -n -t rust 'Lua::(new|new_with|unsafe_new)\(|rhai::|Engine::new(_raw)?\(|\.eval(_with_scope|_expression)?(::<[^>]*>)?\(|Library::new\(' .`
      — each hit: where the text or path comes from, which stdlib/limits are set, and why
      a dispatch table would not do. An in-process engine counts as no sandbox.
