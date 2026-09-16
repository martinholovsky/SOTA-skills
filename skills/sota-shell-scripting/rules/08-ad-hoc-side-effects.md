# 08 — Ad-hoc commands: when the check itself does damage

Scope: the sibling of `rules/06`. That file is about a verification command returning the
**wrong answer**; this one is about a verification command with **side effects** — it
destroys what it was inspecting, or exhausts a resource nobody budgets. Split out of
`rules/06` at v1.42.2 when that file reached its 500-line cap; §3 and §4 keep their
numbers so every existing citation still names the right section. `rules/06` §2's
discipline — state the traversal, print the denominator, control the sweep — is assumed.

**The unifying property:** "I am only checking something" bounds nothing. A read-only
*intent* is not a read-only *command*, and the blast radius of a probe is whatever the
probe actually invokes.

## 3. An ad-hoc command can destroy the thing it was checking

The failure modes above are about *wrong answers*. A verification command can also do
**damage**, and nothing about "I am only checking something" bounds its blast radius.
Field-reported: a command whose entire purpose was to check a claim copied a 40 GB build
directory into a container on a host already at 99% full, which corrupted the container
runtime's storage and cost ~64 GB of images. The check was never run.

Before an ad-hoc command that **writes at scale** — a container copy or build, an image
export, a bulk archive, a recursive `cp`/`rsync`, anything with `--output` on a big tree:

- **Look at headroom first** (`df -h` on the target filesystem, and on the runtime's own
  storage, which is often a different one). A verification step is not exempt from capacity
  planning; it is just unbudgeted.
- **Prefer read-only**: mount the source `:ro`, and send output **outside the source tree**
  to a path you chose. A check that cannot write to its subject cannot corrupt it.
- **Bound it before running it** — `du -sh` the thing you are about to copy. "It is only the
  repo" is a guess about size, and the number is one command away.
- **Build output is the trap, and it is never in your mental model of the repo.** `target/`,
  `node_modules/`, `.venv/`, `vendor/`, `build/` and `dist/` reach tens of gigabytes and are
  exactly what a naive recursive copy takes. Exclude them, or better, do not copy: point the
  tool's output elsewhere (`CARGO_TARGET_DIR=/build`, `--target-dir`, `-o`) and leave the
  source read-only.
- **A full disk is not a clean failure.** On a VM-backed container runtime the guest's disk is
  a sparse file on the host's, so exhausting the host surfaces *inside* the VM as I/O errors
  and can corrupt the filesystem and image store — minutes later, in an unrelated command,
  long after the one that caused it.
- Cleanup on a shared runtime is not housekeeping: see `sota-devsecops` rules/07 §7.7.

## 4. The loop you left running exhausts the process table — and takes cleanup with it

§3 is about a command that writes too much. This is the same idea aimed at a resource
nobody budgets: **processes**. It is the more dangerous of the two, because running out
of disk still lets you run `rm`, and running out of processes does not let you run
anything at all.

**The shape.** A wait loop, backgrounded, with no bound on its iterations:

```bash
# WRONG — nothing here ever stops, and each tick spawns
while ! pgrep -f "run-eval.py" >/dev/null; do sleep 60; done &
```

Every iteration forks (`pgrep`, `grep`, `ps`, the subshells in a `$(…)`), and a
backgrounded loop outlives the command that started it — often the whole session. `rules/06` §1's
`pgrep -f` self-match is what makes it never stop: the loop's own argv contains the
pattern, so it matches itself forever. `rules/06` §1 frames that cost as *a burned timeout*. The
larger cost is that it never stops **spawning**.

**How big it gets, measured — and read the attribution note.** At failure on the machine
below, `ps -A | wc -l` read **11,463** against a `kern.maxprocperuid` of **11,136**: the
per-user table was full, with **≈10,700 `/bin/sh`** in it.

**Correction (2026-09-10): those figures are the *signature*, not evidence for this
section's cause.** When this section was first written the numbers were attributed to
backgrounded wait loops, which had indeed been running that hour — but parentage had not
been checked, and the section said so. It was checked afterwards, and the `/bin/sh`
processes belonged to a **self-recursive `PATH` shim** (`rules/03` §3a); deleting one file
took the count to **691**. The tell was in the evidence all along: a `zsh` wait loop spawns
`zsh`, `sleep` and `pgrep` — never **10,700 `/bin/sh`**.

**Two unrelated causes produce this identical signature** — an unbounded backgrounded loop
(this section) and a wrapper that shadows a command it calls (`rules/03` §3a) — and **only a
parentage check distinguishes them**: `ps -axo pid=,ppid=,command=`, grouped by ppid.
Sequential PIDs with one child each is a recursion; many children under one parent is a pool
or a loop. Fixing the wrong one leaves the machine exactly as exposed, so **do not pick
between them from whichever you happen to have been doing that hour.**

The mechanism and the remedies below are unchanged and independently sound: an unbounded
backgrounded wait *is* a real way to fill the process table, whether or not it was this
incident's cause.

**Recognise the signature, because it is not the one you expect:**

- It does **not** degrade gradually. It hits a ceiling and *every* tool fails at once.
- The error is `fork failed: resource temporarily unavailable`, and it appears in the
  agent's shell and the operator's interactive shell **simultaneously** — which reads
  like the machine broke, not like a script did something.
- **The cleanup tools are inside the blast radius.** `ps -o ppid`, `killall`, `pkill`,
  even `echo` in a fresh shell, all need to fork. So does the diagnosis: you cannot
  learn which process leaked because listing parents requires a process.
- `kill` being a **shell builtin does not rescue you** if each command runs in a newly
  spawned shell — that spawn is the thing failing, before any builtin executes.
- What is left is a GUI process manager (already running, kills internally) or a
  reboot. Plan for that before you background anything.

**So:**

- **Do not poll work that something else already reports.** Where a harness, CI or job
  runner notifies on completion, waiting for that notification costs nothing; a polling
  loop costs a process per tick and buys the same answer later.
- **Never background an unbounded wait.** Before writing any repeating loop, ask what
  makes it *stop* — and if the answer is a `pgrep` on a pattern the loop's own argv
  contains, the answer is **nothing** (`rules/06` §1).
- **Bound the iterations, not just the sleep**: `for i in $(seq 1 60)`, never a bare
  `while true` / `until`. A loop that gives up is a loop that cannot leak forever.
- **Keep it in the foreground** so it dies with the command that started it, and **watch
  an artifact rather than a process** — `until grep -q DONE run.log` forks less and
  cannot match itself.
- **Check headroom for the resource you are about to spend**, exactly as §3 asks for
  `df -h`: `ps -A | wc -l` against `sysctl -n kern.maxprocperuid` (macOS) or `ulimit -u`.
  A loop that ticks every 60s for a day is 1,440 spawns *if each one exits* — and a
  leaked-process count that climbs while you watch it is the cheapest early warning
  there is, because at the ceiling you can no longer run the command that would tell you.

Blast radius is not only disk (§3). It is whatever finite resource the command consumes
without anyone counting — and the process table is the one whose exhaustion disables the
tools you would use to recover.

## Audit checklist

- [ ] **Ad-hoc commands that write at scale** (§3): headroom checked (`df -h` on the target
      *and* the runtime's own filesystem), source mounted read-only, output outside the source
      tree, size bounded with `du -sh` before the copy, and build output (`target/`,
      `node_modules/`, `.venv/`, `vendor/`) excluded or redirected rather than copied.
- [ ] **Backgrounded wait loops** (§4): does any `&`-ed loop lack a bound on its
      iterations, and does anything make it stop other than a `pgrep` that matches the
      loop's own argv? Grep for the shape — `grep -nE '(while|until).*(true|pgrep|ps ).*&\s*$'`
      — and for polling of work a harness already reports. Headroom for the resource
      being spent is checked (`ps -A | wc -l` vs `ulimit -u`), not just `df -h`. If the
      table is already full, **establish parentage before assigning blame** — a
      self-recursive wrapper (`rules/03` §3a) produces the same signature, and only
      `ps -axo pid=,ppid=,command=` tells the two apart.
