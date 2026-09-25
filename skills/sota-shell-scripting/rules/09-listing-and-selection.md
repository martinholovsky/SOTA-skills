# 09 — Listing and selection: the tool answered a different question

Scope: the commands that *enumerate* rather than search — a lister, a selector, a
"which one is latest". `rules/06` §2 is a searcher that traverses less than you think;
these are tools that return less than you think, or all of a population one step to the
left of the one you asked about. Both exit `0` with an empty stderr, which is why they
reach a report as measurements. Split out of `rules/06` (· v1.43.1) when that file
reached its 500-line cap, **keeping their section numbers** so existing citations resolve
— the same move `rules/08` made before it.

## 5. The listing tool answered your question about *one page*

`rules/06` §2 is a searcher that traverses less than you think. This is a lister that returns
than you think — and it is worse, because the shortfall is **policy, not a bug**: the tool
did exactly what it was asked, exited `0`, and wrote nothing to stderr.

Measured 2026-09-10 against a repository with 330 merged pull requests:

```text
gh pr list --state merged --json number | wc -l        →   30    ← no flag: a DEFAULT cap
gh pr list --state merged --limit 20 ...               →   20    ← the cap you typed
gh pr list --state merged --limit 1000 ...             →  330    ← the population
exit status 0, stderr empty, in all three
```

The no-flag answer is off by an order of magnitude. Nothing in the output distinguishes
"there are 30" from "here are the first 30 of 330", and `wc -l` turns either into a number
that looks like a measurement. The same default sits under `gh issue list`, `gh run list`,
`aws ... --max-items`, `kubectl get --chunk-size`, `docker ps -n`, and every REST `GET`
that pages at 30 or 100 — **a client library that iterates pages for you is the exception,
not the rule, and `curl` never does.**

Two distinct ways to get this wrong, and the second is the one that repeats:

- **The cap you never set.** You reach for a lister to *look* at recent items, the default
  page is the right size for looking, and later the same command gets used to *count*.
- **The cap you set yourself, for a different question.** `--limit 20` was correct when the
  question was "show me the recent ones". It silently became the answer when the question
  changed to "how many are there" — the flag is still in the scrollback, and the number it
  produced looks like a finding. Read the flags in your own command before quoting its
  output as a total.

**A count and a sample need different commands.** When the number is the deliverable, ask
the API for the number rather than for the rows, or make the tool prove it reached the end:

```bash
# GOOD — the server counts; no page size can shorten a total
gh api -X GET search/issues --raw-field q='repo:OWNER/REPO is:pr is:merged' -q .total_count

# GOOD — page until short, and say so; --paginate exists precisely for this.
# NOTE the predicate: `state=closed` is merged AND closed-unmerged. Filter, don't assume.
gh api --paginate '/repos/OWNER/REPO/pulls?state=closed&per_page=100' \
  -q '.[] | select(.merged_at != null) | .number' | wc -l

# CONTROL — a cap you can see: if the count equals the limit exactly, assume truncation
n=$(gh pr list --state merged --limit 100 --json number -q '.[].number' | wc -l)
[ "$n" -eq 100 ] && echo "AT THE CAP — this is a page, not a total" >&2
```

**Then check the two methods against each other — and read the disagreement.** Writing
this section, the server count said **330** and the paginated read said **339**. The
pagination was right; the *predicate* was wrong — `state=closed` includes the 9 PRs that
were closed without merging, so the fixed command had quietly started answering a different
question than the one it replaced. A second method exists to have a **different failure
mode** (`sota-code-security` rules/11 §7), and the whole return on that is the moment the
two numbers differ. Had they agreed, nothing would have been learned; had I run only the
fixed one, `339` would have shipped as the merged total. Reconcile the gap to a named cause
(`330 + 9 unmerged = 339`) before reporting either number — an unexplained delta between two
methods is a finding, not a rounding difference.

That last line generalises past `gh`: **a result whose size equals a round number you or the
tool chose is a page until proven otherwise.** 30, 50, 100, 1000. It costs one comparison
and it is the only signal the tool gives you, because it does not give one.

The reporting rule follows `rules/06` §2's: **say which bound produced the number.** "330 merged PRs
(`--limit 1000`, no truncation — the run returned fewer rows than the cap)" is a
measurement. "330 PRs" is a claim whose evidence has been thrown away, and "30" was too.

## 5a. The selector picked a different member than the question named

§5 returned **less** of the right population. This returns **all** of a neighbouring one —
harder to see: nothing truncated, nothing silent, no rule broken. The selector was reasonable
and answered a question one step to the left of the one asked. Three in one session:

| the question | the selector typed | what it actually returns |
|---|---|---|
| "the kernel this release ships" | `sort -V \| tail -1` over the repo | the newest available — here a **backports** kernel, 6.12 for a 6.1 release |
| "how much disk will this free" | `du -sh target` / the tool's own summary | apparent size / logical bytes deleted — **not** blocks returned to the filesystem |
| "how much is reclaimable" | `podman system df` | images not backing a *running* container, with shared layers double-counted down the ancestry chain |

`sort -V | tail -1` is the obvious way to get "the latest" and it is simply not "the
default". Each of the three is the correct answer to a question nobody asked.

- **Name the population member before writing the selector.** *Newest, largest, first,
  default, reclaimable, installed* are six members and at most one is your question.
- **The tell is a value that cannot belong to the thing you asked about.** The Debian probe
  returned a `CONFIG_LSM` string containing `ipe` — IPE merged in **Linux 6.12** (verified:
  `security/ipe/ipe.c` present at tag `v6.12`, absent at `v6.11`), so it cannot appear in a
  6.1 config. The row was refuted by its own output before it was written. Read one full
  record from any selection before building an argument on the aggregate.
- **Three numbers that disagree are three questions, not a discrepancy to average.** None of
  `du`, the tool's report and `df` is wrong; ask which the decision needs. General form:
  `sota-observability` rules/05 §7a.

## 5b. A filter that drops the file you named

A recursive grep given `--include='*.rb'` and the file `config.ru` never reads `config.ru`. `--include` filters
**every** file grep would read, including the ones named on the command line, so a named file
that does not match the glob is skipped: exit `1`, empty output, the same bytes as "not
found". Measured 2026-09-25 on BSD grep (macOS), ugrep, and GNU grep 3.11: all three skip it.
ripgrep does not: `rg -g '*.rb' PAT config.ru` still searches `config.ru`, because rg always
reads paths you name. So a probe that works under `rg` can break when it is rewritten for grep.

It hides in audit probes because the pair reads as belt and braces: a sweep filter plus the
one file you care about. Three shipped probes in this library had the shape. A Sinatra CSRF
check reported HIGH on every app, because it could never see the line it was looking for. A
session-cookie check always came back clean. A .NET secrets check never opened
`appsettings.json`.

```sh
grep -rn 'Rack::Protection' --include='*.rb' config.ru              # BAD  — config.ru skipped
grep -rn 'Rack::Protection' config.ru                               # GOOD — a named file needs no filter
grep -rn 'Rack::Protection' --include='*.rb' --include='config.ru' . # GOOD — the filter admits it
```

- **A named file needs no filter, and a filter needs `.` or a directory.** Mixing the two is
  the bug. If you need both, add an `--include` that matches the named file's basename.
- **Test the probe on a fixture where it must hit.** A probe that cannot fire exits the same
  way as a clean codebase does. `rules/06` §2's positive control is what catches it.
- **A brace glob inside `--include` has the same effect.** grep does not expand braces, so
  a quoted `--include='*.{py,js}'` matches no file on BSD grep, ugrep or GNU grep. Unquoted,
  bash expands it and zsh aborts with "no matches found" (`rules/06` §1). Write one
  `--include` per extension. Two shipped probes had this shape (measured 2026-09-25).
- **Invariant 37** fails the build on both shapes in any skill file.

## Audit checklist

- [ ] **A search filter next to a named file** (§5b): does any `grep` command combine
      `--include` with an explicitly named file the glob does not match? The named file
      is skipped and the command exits 1 exactly as for "no match". Run the probe on a
      fixture that must hit before trusting a clean result.

- [ ] **Does the selector name the population member the question does?** (§5a) — *newest*
      is not *default* (`sort -V | tail -1` returns a backports kernel), *apparent size* is
      not *blocks freed*, *not backing a running container* is not *reclaimable*. Nothing is
      truncated and the exit status is 0, so the only tell is a value that cannot belong to
      the subject; read one full record before trusting the aggregate.
- [ ] **Counts taken from a listing tool** (§5): does the command carry a `--limit`/
      `per_page`/`--max-items`, or rely on the tool's **default** page (30 for `gh`, 100 for
      most REST)? A total must come from a server-side count (`total_count`) or a paginated
      read (`gh api --paginate`), never from the first page. Treat a result whose size equals
      the cap exactly as truncated, and quote the bound alongside the number. Where a second
      method was run, is the delta between the two reconciled to a named cause — or was the
      un-truncated command also given a **different predicate** (`state=closed` vs merged)?
