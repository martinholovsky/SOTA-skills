# 07 — PowerShell (`pwsh`) — CI steps, deploy scripts, entrypoints

Scope: this skill's premise is that shell hides in CI blocks, entrypoints and Makefile
recipes (`rules/04`). On a Windows runner — and increasingly on Linux ones — that shell is
PowerShell, and **none of `set -euo pipefail`, `${PIPESTATUS[0]}` or ShellCheck exists
there**. The failure classes are the same; the mechanisms are not. Read this together with
`rules/01` §3 (the safety baseline it replaces) and `rules/06` (ad-hoc commands, where the
exit-status traps below bite hardest).

Two dialects, and they are different products: **PowerShell 7.x** (`pwsh`, cross-platform,
MIT-licensed, ships separately) and **Windows PowerShell 5.1** (`powershell.exe`, a Windows
OS component, frozen). Guidance below is for 7.x unless it says otherwise. Versions and
end-of-support dates are in §7 — check them before you pin.

## 1. There is no `set -euo pipefail`. Assemble the equivalent, and know what it misses

**Rule: a PowerShell script that matters opens with an explicit error posture, because the
defaults continue past errors.**

`$ErrorActionPreference` defaults to **`Continue`** — Microsoft's own table — and it
"[d]etermines how PowerShell responds to a non-terminating error, an error that doesn't stop
the cmdlet processing." So a failing cmdlet prints red text and the script carries on, which
is the `set -e`-less behaviour in `rules/01` §3 with a more convincing error message.

```powershell
#!/usr/bin/env pwsh
Set-StrictMode -Version Latest        # undeclared variables & bad property refs become errors
$ErrorActionPreference = 'Stop'       # cmdlet errors terminate  (default: Continue)
$PSNativeCommandUseErrorActionPreference = $true   # native non-zero exits too (default: $false)
```

- **`$ErrorActionPreference` is wider than `-ErrorAction`.** The preference variable "applies
  to **both** non-terminating and statement-terminating errors", while the `-ErrorAction`
  parameter "only affects non-terminating errors". Setting one per-call is not the same
  control as setting the posture.
- **The line that is actually missing is the third one.** `$PSNativeCommandUseErrorActionPreference`
  defaults to **`$false`**: when it is `$true`, "native commands with non-zero exit codes issue
  errors according to `$ErrorActionPreference`." Left at the default, `$ErrorActionPreference =
  'Stop'` does **nothing** for `git`, `docker`, `kubectl`, `terraform`, `msbuild` or any other
  executable — a failed `git push` mid-script is invisible and the script runs on. This is the
  single highest-yield defect in PowerShell CI, and it looks fixed because the second line is
  present. (PowerShell 7.4 added control over how `stderr` writes are handled; 7.2 stopped
  redirected native errors reaching `$Error`.)
- **Deliberate non-zero exits exist**: `robocopy` uses exit codes as information. Scope the
  opt-out to the call rather than the script, as Microsoft's own example does — a scriptblock
  setting `$PSNativeCommandUseErrorActionPreference = $false`, then checking `$LASTEXITCODE`
  explicitly.
- **`try/catch` only catches *terminating* errors.** A non-terminating error under `Continue`
  never enters `catch`. Either set the posture above or pass `-ErrorAction Stop` on the call
  you are guarding; a `catch` around unguarded cmdlets is decoration.
- Audit: a `.ps1` under `ci/`, `deploy/` or a container entrypoint with no
  `$ErrorActionPreference` line = **High**; one that sets it but not
  `$PSNativeCommandUseErrorActionPreference` while calling native tools = **High** (the
  control is present and inert — `sota-code-security` rules/10).

## 2. Three ways to read "did that work", and they disagree

**Rule: name which status you are reading, and never read a status through a wrapper that
does not propagate it.** This is `rules/06`'s table for bash, re-derived: the mechanism
differs, the false green is identical.

| you read | it means | the trap |
|---|---|---|
| `$?` | execution status of the **last command**: `True` if it succeeded | set by `Write-Error` **but not for the function that called it** |
| `$LASTEXITCODE` | "the exit code of the last **native program or PowerShell script**" | unset if no native command has run yet; a stale value otherwise |
| `throw` / `catch` | a terminating error | never fires for a non-terminating one, nor for a native non-zero exit at the default preference |

- **`$?` does not climb out of a function.** Microsoft's documented example: a function that
  calls `Write-Error` shows `$?` as `False` *inside* the function and **`True`** on the next
  line outside it. "The `Write-Error` cmdlet always sets `$?` to **False** immediately after
  it's executed, but won't set `$?` to **False** for a function calling it" — use
  `$PSCmdlet.WriteError()` when the caller must see it. A wrapper function that validates
  input and `Write-Error`s on bad input therefore reports success to its caller.
- **For executables the two agree by construction**: `$?` "is set to **True** when
  `$LASTEXITCODE` is 0, and set to **False** when `$LASTEXITCODE` is any other value." So for
  native tools, read `$LASTEXITCODE` — it carries the number, and `$?` throws it away.
- **`$LASTEXITCODE` is not reset by a cmdlet.** Only a native command or a script's `exit`
  moves it, so a check after a cmdlet-only stretch reads whatever the last executable left
  there — the stale-status shape of `rules/06` §1.
- **A pipeline has no `PIPESTATUS`.** PowerShell pipelines pass objects, not exit codes; there
  is nothing to index. If you need the producer's status, do not pipe it — capture output and
  check `$LASTEXITCODE` on its own line, the same conclusion `rules/01` §3 reaches for zsh.
- Audit: `if ($?)` after anything other than the immediately preceding native command =
  **Medium**; a wrapper function whose only failure signal is `Write-Error` = **High**.

## 3. `pwsh -File` and `pwsh -Command` end differently

**Rule: know which invocation form your CI uses, because they derive the process exit code by
different rules.** From `about_Automatic_Variables`:

- Called with **`-File`**, `$LASTEXITCODE` is `1` "if the script terminated due to an
  exception", the value of `exit` if used, or `0` on success.
- Called with **`-Command`**, it is `1` "if the script terminated due to an exception **or if
  the result of the last command set `$?` to `$false`**", and `0` "if the script completed
  successfully and the result of the last command set `$?` to `$true`".

So under `-Command` the **last statement decides the verdict**. A step that ends with a
`Write-Host` summary, a cleanup call, or a log tail reports success no matter what failed
three lines earlier — the masked-exit-code defect of `rules/06`, promoted to an entire CI
step. End such a script with an explicit `exit` you computed, never with a convenience call.

## 4. GitHub Actions: the built-in shell is safe, and opting out silently removes the safety

**Rule: use the bare `shell: pwsh` keyword, and treat any custom shell string as taking over
responsibility for fail-fast and exit propagation.**

For the built-in `pwsh` and `powershell` keywords, GitHub prepends `$ErrorActionPreference =
'stop'` to the script and appends `if ((Test-Path -LiteralPath variable:\LASTEXITCODE)) {
exit $LASTEXITCODE }`, so the step's status reflects the script's last exit code
([workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)).
That is a good default and it is **not inherited** by a custom shell:

```yaml
- shell: pwsh                 # GOOD: fail-fast prepended, exit code appended
  run: ./deploy.ps1
- shell: pwsh -File {0}       # BAD: both the prepend and the append are gone
  run: ./deploy.ps1
```

- **The prepend does not cover native commands.** It sets `$ErrorActionPreference`, not
  `$PSNativeCommandUseErrorActionPreference` (§1), so a failing `terraform` or `docker` in the
  middle of a step still does not stop it. The appended `exit $LASTEXITCODE` rescues only the
  case where the failing executable was the **last** one to run.
- **The append is conditional on the variable existing** (`Test-Path variable:\LASTEXITCODE`).
  A step that runs no native command never sets it, so the append is a no-op and the step's
  status comes from pwsh itself.
- `shell: powershell` is **Windows PowerShell 5.1**, a different product with a different
  engine; and on a self-hosted Windows runner without PowerShell Core installed, `pwsh` falls
  back to it. Pin the dialect you tested (§7).
- Audit: a custom `shell:` string wrapping PowerShell with no explicit `exit` = **High** —
  this is `sota-devsecops` rules/09's "the gate's own exit code" question, one layer down.

## 5. Injection: `Invoke-Expression` is `eval`, and string-built commands are the same defect

**Rule: never interpolate untrusted input into a command string.** `rules/03` §1 in
PowerShell's vocabulary — the sinks differ, the class does not.

```powershell
# BAD — every one of these is eval
Invoke-Expression "Get-Item $userPath"
& ([scriptblock]::Create($fromRequest))
$cmd = "git checkout $branch"; Invoke-Expression $cmd

# GOOD — arguments stay arguments
Get-Item -LiteralPath $userPath
git checkout -- $branch
$params = @{ Path = $userPath; Recurse = $true }; Get-ChildItem @params   # splatting
```

- **`-LiteralPath` over `-Path`** wherever the value is not yours: `-Path` interprets `*`,
  `?` and `[ ]` as wildcards, so a filename containing them silently selects other files, or
  nothing. The quiet-wrong-set shape of `rules/06`.
- **Splatting (`@params`) is the array-for-command-building rule** of `rules/05`: it keeps
  arguments as data instead of re-parsing a string.
- **Argument passing to native commands differs by platform**:
  `$PSNativeCommandArgumentPassing` defaults to `Windows` on Windows and `Standard`
  elsewhere, so the same script can pass arguments differently on a Windows runner and a
  Linux one. Test on the platform you deploy to.
- **Double quotes interpolate, single quotes do not** — `"$x"` and `"$($x.Prop)"` expand,
  `'$x'` is literal. A password or token in a double-quoted string headed for a command line
  is `rules/03` §2's argv-exposure defect.
- Audit: any `Invoke-Expression`/`iex` reachable from input = **Critical** if the input
  crosses a trust boundary; `-Path` with an externally supplied value = **Medium**.

## 6. Execution policy is not a security control

**Rule: never present `Set-ExecutionPolicy` as a defence, and never treat `-ExecutionPolicy
Bypass` in a pipeline as a finding on its own.** Microsoft is explicit: "The execution policy
isn't a security boundary, it's defense in depth. For example, users can easily bypass a
policy by typing the script contents at the command line when they can't run a script."

- **Enforcement is Windows-only.** On non-Windows "the default execution policy is
  **Unrestricted** and can't be changed"; `Get-ExecutionPolicy` returns `Unrestricted` but
  "the behavior really matches **Bypass**". A cross-platform script that reasons about policy
  is reasoning about nothing on two of its three platforms.
- The real controls are the ones this library already names: signing and provenance
  (`sota-devsecops` rules/03), least privilege for the account the script runs as
  (`sota-sandboxing`), and not fetching code at runtime (`rules/03` §5 on `curl|bash`, whose
  PowerShell form is `iwr ... | iex` and is the same defect).
- `Unblock-File` clears the mark-of-the-web; note that `curl.exe`, `Invoke-RestMethod` and
  `Invoke-WebRequest` do **not** set it, so a download through them is never marked in the
  first place.
- Audit: a remediation that says "set the execution policy to RemoteSigned" and stops =
  **Info, and wrong** — record what actually gates execution.

## 7. Versions, and the EOL date beside each one

Operating principle 1: a version with no end-of-support date beside it has not been looked
up. From Microsoft's support-lifecycle page (checked 2026-09-14 — re-check before pinning,
because two of these fall inside two months):

| release | released | end of support | note |
|---|---|---|---|
| PowerShell 7.6 (LTS) | 18-Mar-2026 | **14-Nov-2028** | current LTS; prefer for new work |
| PowerShell 7.5 | 23-Jan-2025 | **10-Nov-2026** | current Stable |
| PowerShell 7.4 (LTS) | 16-Nov-2023 | **10-Nov-2026** | previous LTS |
| Windows PowerShell 5.1 | Aug-2016 | tied to the **Windows** lifecycle | an OS component, not this product; no new features |

- **5.1 is not "old PowerShell", it is a different runtime** (.NET Framework, `Desktop`
  edition). Scripts that work under `pwsh` can fail under it, and `shell: powershell` in CI
  selects it. If you must support both, say so and test both.
- PowerShell 7.x support "follows the support lifecycle of .NET", so a PowerShell EOL is
  really the underlying .NET EOL — check both when a pin has to be justified.

## 8. Lint and format, because ShellCheck does not run here

**Rule: PowerShell gets its own analyser in CI, gating at the same severity as ShellCheck
does for bash (`rules/03` §7).** The analyser is
[PSScriptAnalyzer](https://github.com/PowerShell/PSScriptAnalyzer) (`Invoke-ScriptAnalyzer`),
with `Invoke-Formatter` as the `shfmt` analogue.

- Run it over the whole tree, fail the build on `Error` **and** `Warning` — the argument in
  `rules/03` §7 for not dismissing `style` applies unchanged: the low-severity rules are where
  the quoting and scoping defects are.
- Suppressions carry a reason and an owner, like every other ignore in this library
  (`sota-devsecops` rules/03 §3.6).
- **Watch the analyser fail once before trusting a green run** — `sota-code-security`
  rules/11 §7. A misconfigured `-Path` that matches no `.ps1` reports zero findings and
  exits 0, which is the empty-denominator signature this repo gates on.

## Audit checklist

- [ ] Does every `.ps1` that runs in CI, deploy or an entrypoint set `$ErrorActionPreference`
      explicitly rather than inheriting `Continue`?
- [ ] Where native commands are called, is `$PSNativeCommandUseErrorActionPreference` set to
      `$true` — or is each call's `$LASTEXITCODE` checked on its own line? (Default `$false`
      makes an `ErrorActionPreference = 'Stop'` script silently tolerate a failed `git`.)
- [ ] Is `Set-StrictMode -Version Latest` set, so a typo'd variable is an error and not `$null`?
- [ ] Does any `catch` guard a cmdlet that was never made terminating (no `-ErrorAction Stop`,
      no `Stop` preference)?
- [ ] Does a wrapper function signal failure only through `Write-Error`, which does not set
      `$?` for its caller?
- [ ] Is `$?` read anywhere other than immediately after the command it describes?
- [ ] Is `$LASTEXITCODE` read where no native command has necessarily run, so it is stale or
      unset?
- [ ] Under `pwsh -Command`, does the script end with a convenience call (logging, cleanup)
      whose `$?` becomes the process exit code?
- [ ] Does any GitHub Actions step use a **custom** `shell:` string for PowerShell, dropping
      the built-in prepend/append — and if so, does it exit explicitly?
- [ ] Any `Invoke-Expression`, `iex`, `[scriptblock]::Create()` or `iwr | iex` reachable from
      untrusted input?
- [ ] Is `-Path` used with externally supplied values where `-LiteralPath` is meant?
- [ ] Are command lines built by string concatenation rather than splatting?
- [ ] Is an execution policy cited anywhere as a security control?
- [ ] Is the target dialect stated (7.x vs Windows PowerShell 5.1), and is each pinned version
      recorded with its end-of-support date?
- [ ] Does CI run PSScriptAnalyzer over the whole tree, gate on Warning and above, and has the
      gate been watched producing a finding rather than only a clean run?
