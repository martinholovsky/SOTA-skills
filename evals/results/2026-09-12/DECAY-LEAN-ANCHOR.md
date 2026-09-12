# ROADMAP 49 — decay against an anchor the filler can actually dilute

**2026-09-12** · `run-decay.py --lean-anchor --depths 0,12,30` · `c6_webhook` ·
build `claude-sonnet-4.6`, blind judge `claude-opus-4.8`, 10-item rubric ·
**pre-registered** in [PRE-REGISTRATION-DECAY-LEAN-ANCHOR.md](PRE-REGISTRATION-DECAY-LEAN-ANCHOR.md),
committed before any call · artifacts `decay-lean-anchor.json`, `decay-lean-k0-rerun.json`

## Results

| arm | K=0 | K=12 | K=30 |
|---|---|---|---|
| control (no guidance) | 0.50 / 0.40 | 0.40 | 0.40 |
| **anchor** (principle 5 at turn 1) | **0.00 / 0.00** ⚠ | **0.80** | **0.80** |
| reminder (anchor + a reminder on the probe) | 0.80 / 1.00 | 0.80 | — |

*Two values at K=0 are the original run and an independent re-run.*

**The registered headline could not be computed.** `DECAY = anchor@K0 − anchor@K30` requires
a K=0 build, and the anchor arm does not produce one.

## What did come out, and it is worth more than the headline was

**1. No decay where the arm builds.** anchor@K12 = anchor@K30 = **0.80**, with the filler
finally able to dilute (**4.12:1**, against 0.15:1 in the 2026-07-14 run that could not have
detected decay at any depth). Between twelve and thirty turns of unrelated conversation,
nothing was lost.

**2. The lean anchor works.** 0.80 against a 0.40 control — a **+0.40** gap on principle 5
alone, 3,155 characters. The pre-registered void condition (a floor effect, gap < 0.20) did
**not** trigger, so the null in (1) is a real null and not an artefact of having no headroom.

**3. The finding nobody registered: the anchor fails at K=0, reproducibly.**

| | artifact length | recall |
|---|---|---|
| anchor @ K=0 (run 1 / run 2) | **1,204 / 1,171 chars** | 0.00 / 0.00 |
| anchor @ K=12 / K=30 | 16,905 / 22,599 | 0.80 / 0.80 |
| reminder @ K=0 (run 1 / run 2) | 23,835 / 28,597 | 0.80 / 1.00 |

At K=0 the anchor arm returns roughly **1.2k characters** — not a low-quality build, **not a
build at all** against a rubric whose satisfied arms run 17–29k. Two independent runs agree.
The reminder arm, whose *only* difference is one reminder line appended to the same probe
after the same anchor, returns ~25k and scores 0.80–1.00. **REMINDER RECOVERY at K=0 =
+1.00.**

So in the one condition where the guidance is the immediately preceding turn, it is the
condition where the task is least likely to be executed — and depth *helps*.

**The mechanism is NOT established.** The plausible reading is that with the guidance
adjacent, the model answers *it* conversationally rather than performing the task, and the
filler turns push it far enough away that the probe reads as a standalone request. That is a
hypothesis. `run-decay.py` stores only `artifact_len`, never the artifact, so the 1.2k
response cannot be read — an instrument gap this run exposed and did not fix.

## Why this matters beyond the item

The reminder arm is the eval analogue of the shipped **re-injection hook**. This is the first
measurement in which that mechanism does something large: **+1.00 at K=0**, turning a
non-answer into a complete one. It is one case, one model, n=1 per cell — but it points at
the surface ROADMAP 48 chose on separate evidence, which is worth noting rather than
over-claiming.

## CORRECTION (2026-09-12, same day): finding 3 was wrong, and the truth is better

`run-decay.py` now retains artifacts instead of only their length (the instrument gap this
run exposed). The K=0 anchor cell was re-run a **third** time — 0.00 again, `artifact_len`
1,138 — and the response is now readable. **It is not a non-answer. It is a clarifying
question**, quoted in full at the top:

> *Before I build, one clarifying question that affects security scope:* **is rate limiting /
> abuse control handled at a gateway in front of this service, or does it need to live in
> this endpoint?** … *I'll build the full treatment either way (this is network-reachable,
> touches money, and processes untrusted caller data) — I just need to know whether to
> include an in-process rate limiter or document the gateway assumption.*

It then **lists every other decision correctly** — TLS enforced with HSTS, HMAC-SHA256
signature verification, idempotency keyed on the provider event ID, structured logging with
no secrets or PII, tests — and stops, waiting for the answer.

**That is the library working, not failing.** Operating principle 2 says stop and ask on
security-relevant decisions; principle 9 says ask in one line when it is genuinely ambiguous;
principle 5 says if a non-negotiable is handled elsewhere, *say so rather than silently
omitting it*. A money-touching, network-reachable endpoint taking untrusted caller input is
the exact case those rules describe. **The guidance made the model pause, correctly, and the
rubric scored the pause as ten missing requirements.**

The other two arms confirm it rather than contradicting it:

| arm | what it did | recall |
|---|---|---|
| control (no guidance) | built immediately — nothing told it to pause | 0.40 |
| **anchor** | **asked one question, stated every other decision** | **0.00** |
| reminder | the reminder says *"review your code **before finishing**"*, which presupposes finishing — so it built and **documented the gateway assumption inline** | 0.90 |

Both anchor and reminder are correct library behaviour. The rubric can only see one of them.

### So the real findings are

1. **No decay** — anchor@K12 = anchor@K30 = 0.80, unchanged.
2. **The K=0 result is a measurement artefact, not a behaviour.** `run-decay.py` scores the
   *presence of implementation* and cannot distinguish **"correctly paused to ask"** from
   **"omitted the requirement"**. Any completeness-style rubric has this hole; this one was
   caught only because a cell scored an implausible 0.00 three times and the artifact was
   finally retained.
3. **What was published here hours earlier — that guidance adjacent to a task suppresses the
   task — was wrong**, and is retracted above rather than edited away. The hypothesis was
   plausible, it was labelled unverified at the time, and it survived exactly as long as it
   took to read the evidence the runner had been discarding.

## What this does not establish

1. **n=1 per cell, one case, one model, one day.** The K=0 effect is reproduced; nothing
   else is.
2. **The registered DECAY metric is unmeasured**, not zero. Only the K12→K30 span was
   measurable, and it is flat.
3. **The K=0 mechanism is a hypothesis**, blocked on the runner not retaining artifacts.
4. The filler is trivia. Semantically-close distractors would plausibly behave differently.
