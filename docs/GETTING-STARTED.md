# New here? Start with this guide

This page is for you if you have never used SOTA-skills, or if you are new to AI coding
assistants. It explains three things in plain language: **what the library is**, **what it
does for you**, and **how to start using it**. Every other doc assumes you already know these,
so read this one first.

It takes about ten minutes to read. You need no prior knowledge of "skills", "routers" or
"hooks". Each term is explained the first time it appears.

## What SOTA-skills is

You probably already use an AI coding assistant such as Claude Code, Codex or Gemini CLI. It
writes code that works, but it tends to leave things out. It might skip the tests, the rate
limit, the input validation, the structured logging or the TLS settings, and it rarely
mentions what it skipped. The longer a session runs, the more of your earlier instructions it
forgets.

SOTA-skills is a library of **engineering rules written for your assistant to read**. "SOTA"
means *state of the art*: the current best practice for each area of software engineering,
checked against primary sources such as official docs, standards and security advisories.

The rules are grouped into **skills**. A skill is a folder of Markdown files that covers one
area of engineering, for example:

| Skill | What it covers |
|---|---|
| `sota-code-security` | Injection, login and permissions, cryptography, secure web defaults |
| `sota-testing` | What to test, how to write tests that catch real bugs, keeping a suite healthy |
| `sota-databases` | Schemas, safe migrations, indexes, transactions |
| `sota-python`, `sota-golang`, `sota-rust`, … | Rules specific to one programming language |

There are 40+ skills in all. The full table is in the
[README → Skills](../README.md#skills) section.

There is no program to run, no account and no telemetry. The library is plain text that your
assistant reads at the moment it needs it.

## Why you would want it

**1. Your assistant stops dropping the boring but important parts.** In this project's own
measurements, with a plain "build X" prompt the share of best practices that made it into the
code rose from about 59% without the library to about 98% with it. The numbers and their
method are in [Measured results](../evals/results/RESULTS.md).

**2. It works for building *and* for reviewing.** Every skill has two modes:

- **BUILD**: your assistant follows the rules while it writes code, then checks its own work
  against a checklist before showing it to you.
- **AUDIT**: your assistant reviews existing code against the same rules. It reports each
  problem with its location, how serious it is, how hard it is to fix, and the fix itself.

**3. Only the rules you need are loaded.** Your assistant can only hold so much text at
once (its *context*). Loading the whole library would push out your own code and
instructions. Instead, a **router** skill called `sota` reads your request, decides which
areas it touches, and loads only those rule files. A request to add a login page loads the
security and web rules. It does not load the Kubernetes rules.

**4. The rules stay in force during long sessions.** On Claude Code the library installs a
small **hook**: a script that runs on every message you send and reminds the assistant to
route through the library. Your assistant therefore keeps applying the rules on turn 80, not
only on turn 1.

**5. It does not make things up about versions.** Facts that change quickly, such as release
versions and security advisories, are written so the assistant re-checks them at the source
instead of trusting a stale number.

## How to start

### Step 1: Install it

Pick **one** of these two ways.

**Option A: the plugin (simplest, Claude Code only).** In Claude Code, type:

```text
/plugin marketplace add martinholovsky/SOTA-skills
/plugin install sota-skills@sota-skills
```

**Option B: clone and install (works with more assistants, and lets you read the files).**
In a terminal:

```sh
git clone https://github.com/martinholovsky/SOTA-skills
cd SOTA-skills
./scripts/install.sh
```

The installer links the skills into `~/.claude/skills/` so they apply in every project you
open. It also asks whether to set up **always-on routing**, which makes the library apply to
every request however you phrase it. Answer **yes** unless you have a reason not to. The
installer backs up any file before it changes it.

If you use Codex, Copilot, Cursor, Gemini CLI or Antigravity, run
`./scripts/install.sh --target all` instead. Note that these assistants do not get the
per-message reminder hook, which only exists on Claude Code. See
[MULTI-AGENT.md](MULTI-AGENT.md) for the details.

### Step 2: Ask for something in plain language

You do not need to name a skill. Open any project and describe what you want, as you
normally would:

```text
Add a password-reset flow to this app.
```

```text
Design a small REST API for a to-do list, with tests.
```

The router works out which skills apply, and your assistant follows them. To check that it
happened, look for your assistant mentioning a `sota-…` skill, or ask it which skills it
used.

### Step 3: Try an audit

Audits are often where a new user sees the most value. In a project you already have, ask:

```text
Audit this repo. Give me severity, effort and a fix for every finding.
```

You can also type the ready-made command `/sota-audit`. It asks you to agree the scope first,
then works through the checklists one item at a time.

### Step 4 (optional): Tell it your preferred stack

If you always use, say, PostgreSQL and FastAPI, write that down once in a **profile** so you
do not have to repeat it:

```sh
cp profiles/example.md.template profiles/<you>.md   # then edit it
mkdir -p ~/.claude/profiles
ln -sfn "$(pwd)/profiles/<you>.md" ~/.claude/profiles/<you>.md
```

Your profile stays on your machine. Git ignores it, so it is never committed. The library
then uses your choices as defaults when it builds, and flags code that departs from them
when it audits.

## The six slash commands

Slash commands are shortcuts you type into Claude Code. The library ships six. You do not
need any of them to get value from the library, but they help as your sessions get longer:

| Type this | When | What happens |
|---|---|---|
| `/sota-resume` | Starting a session | Finds the open work in the project (TODOs, checklists, trackers) and offers to do it |
| `/sota-auto` | Nobody will be around to answer, e.g. overnight | Works through the open items without asking, holds back anything it cannot undo (merges, releases, spending without a `budget=$N`), and ends with a report of every decision it made for you |
| `/sota-audit` | Finishing a piece of work | Reviews the code against the library's checklists |
| `/sota-close` | Ending a session | Corrects anything that turned out wrong, records what is unfinished, and updates the docs |
| `/sota-report` | Ending a session | Writes a report, kept out of git, on where the library's guidance helped or fell short |
| `/sota-deep-audit` | Big moments: a release, inheriting a codebase | A thorough, multi-agent review. It costs much more to run, so it is not for routine use |

All six accept extra words, for example `/sota-close focus on the login changes`.

## Common questions

**Do I have to say "SOTA" or name a skill?** No. With always-on routing turned on, plain
requests are enough. Name a skill only if you want to force one, for example "check this
against `sota-databases`".

**Will it slow my assistant down or fill its memory?** Only a small amount. Only the rule
files that match your task are loaded, and each file is kept under 500 lines for this reason.

**Does it send my code anywhere?** No. The library is text files on your machine and never
contacts any server. Your assistant itself works as it always does.

**Does it guarantee my code is secure?** No. It makes your assistant much more consistent
about applying good practice, but it is guidance, not a guarantee. To have the rules enforced
on every commit, whoever writes it, see
[README → Enforcing the gates](../README.md#enforcing-the-gates).

**How do I update it?** Plugin: `/plugin update sota-skills@sota-skills`. Clone: run
`scripts/update.sh` in your checkout. Details are in
[README → Updating](../README.md#updating).

**I found a rule that is wrong or missing.** Please say so. Reports from real use are how the
library improves. See [README → Found a gap?](../README.md#found-a-gap-tell-us--its-the-only-signal-we-get).

## Where to go next

| If you want to… | Read |
|---|---|
| See every install option | [README → Installation](../README.md#installation) |
| See more example requests | [README → Using it](../README.md#using-it) |
| Understand how a request is routed to skills | [README → How it works](../README.md#how-it-works) |
| See the evidence that it works | [Why it works](WHY-IT-WORKS.md) and [Measured results](../evals/results/RESULTS.md) |
| Find any other topic | [Docs index](INDEX.md) |
