# ROADMAP 48 — does routing survive a change of task shape?

**2026-09-12** · `evals/run-routing-shift.py --samples 3 --temp 0.7` ·
`claude-sonnet-4.6` · 4 cases × 2 arms × 3 samples · objective name-match, no judge ·
**pre-registered** in [PRE-REGISTRATION-ROUTING-SHIFT.md](PRE-REGISTRATION-ROUTING-SHIFT.md),
committed before any call · artifact `routing-shift.json`

## Result

| arm | correct |
|---|---|
| fresh (prompt alone) | 0.750 |
| shifted (after two turns of other work) | 0.500 |

**ROUTING-SHIFT = +0.250** — exactly the pre-registered threshold for "the effect
reproduces". **And the headline is the least interesting thing here**, because the per-case
data says two different things.

| case | fresh | shifted | what it means |
|---|---|---|---|
| s1 docs → shell verification | 1.00 | 1.00 | no shift |
| s2 docs → test-suite diagnosis | 1.00 | 1.00 | no shift |
| **s3 shell → CI/gate reproduction** | **0.00** | **0.00** | **fails from a cold start — not a shift at all** |
| **s4 build → evidence-script** | **1.00** | **0.00** | **the only genuine shift** |

## The delta is one case, and I said so in advance

With four cases, **one case is 0.25**. The registration fixed the threshold there precisely
because nothing finer is interpretable, so "+0.250" means *exactly one case moved* — s4,
where two turns about building a secure endpoint were enough to keep the model on
`sota-code-security` when the question had moved to whether an attestation script's
self-test proves anything. Real, reproduced 3/3 in both arms, and thin evidence on its own.

## The finding that outranks it: s3 is a trigger defect, and the item said there were none

ROADMAP 48's framing was explicit — *"neither is a trigger defect: the description matched,
the rule existed, and it simply was not loaded when the work changed shape."* **For s3 that
is false.** The prompt — *"the pre-commit hook passes locally but the same check fails in CI
on the identical commit; which one is telling the truth?"* — goes to `sota-shell-scripting`
**3/3 in the fresh arm**, with no prior context at all. Nothing was "treated as done for the
session": the classifier never pointed at the right skill in the first place.

The right skill is `sota-devsecops`, whose **rules/09 §5** is titled *"The scoped gate is not
the gate — reproduce the invocation, not an equivalent"* and is about exactly this
divergence. Checked against its `description`, which is the entire auto-load classifier:
**"pre-commit", "local" and "reproduce" appear nowhere in it.** "gate" and "CI" do, but they
are swamped by pipeline/supply-chain vocabulary, and the prompt's surface words — hook,
check, passes, locally — are shell words.

**This is the same miss that produced the 2026-09-12 retraction**, where a session doing
shell work never opened `sota-devsecops/rules/09` and filed a duplicate-rule proposal as a
result. It was recorded as a routing-treated-as-done failure. It is not. It reproduces from
a cold start, which makes it a **description** problem with a known fix and a regression pin.

## What this does not establish

1. **Four cases, one model, one day.** The +0.250 is one case and sits exactly on the
   threshold; it is a direction, not a magnitude.
2. **Two prior turns is a weak frame** next to the multi-hour sessions the observations came
   from. A small shift here does **not** clear the real behaviour — it bounds what two turns
   can do.
3. **It measures which skill the model *says* applies**, not what it loads. No Skill tool
   exists in an eval. Same proxy `run-desc-routing.py` publishes on, labelled rather than
   hidden.
4. **The fresh arm is 0.750, not ~0.90**, and the registered void condition asked for that to
   be read first: the range is real (s3 sits at the floor in both arms), so the delta is not
   a squeeze artefact — but the ceiling is lower here than on `desc-routing`'s own cases.
