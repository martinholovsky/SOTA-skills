# ROADMAP 39 — conflict rate between simultaneously-loaded skills

**Run 2026-09-09** · `evals/run-conflict-rate.py --samples 3 --temp 0.0` ·
judge `anthropic/claude-sonnet-5` · 17 pairs from 8 multi-skill gold cases ·
1,496,659 characters of corpus · artifact `conflict-rate.json` ·
**pre-registered** in [PRE-REGISTRATION-CONFLICT-RATE.md](PRE-REGISTRATION-CONFLICT-RATE.md),
committed before any call

This is the first measurement of the **one failure mode of the four with a real incident
behind it**: two rules in this library contradicted each other in a live build (a
liveness-probe rule against a no-`await` `async def` rule), which is why the router carries
a conflict-resolution clause at all.

## The judge was a control before it was an instrument

Two synthetic pairs ran in the same batch, same model, same prompt, same temperature:

```
planted contradiction -> 1 conflict(s)   (needs >= 1)
benign pair           -> 0 conflict(s)   (needs == 0)
ok — separated.
```

Registered as VOID-if-they-don't-separate, because a judge that answers "no conflicts" to
everything produces exactly the number this project would most like to see. It separated
on this run and on the aborted one before it.

## Two numbers, and only the second is quotable

| | value |
|---|---|
| **Judge-reported** rate (any sample reports ≥ 1 conflict) | **6 / 17 = 0.353** |
| Raw conflicts reported | 11 |
| — quotes **fabricated** (the sentence is not in the file the judge named) | **3** |
| — survived quote-verification | 8, collapsing to **5 distinct claims** (one repeats across three samples) |
| — survived the **hand read** | **3 distinct claims**, on **3 pairs** |
| **Verified** rate | **3 / 17 = 0.176** |

`run-conflict-rate.py --verify` does the mechanical half — a quoted sentence absent from
the file it is attributed to is a fabrication and dies with no judgement needed. **3 of 11
reported conflicts failed that check**, which is the single most important number here for
anyone tempted to read a judge's output directly.

## Verdict against the registered thresholds

**H1 (conflicts are rare) is REFUTED.** It required judge-reported ≤ 0.15 **and** verified
≤ 0.10. The verified rate is **0.176**.

**H2 (common at the ceiling) is not met** — it required ≥ 0.40 and the judge-reported rate
is 0.353. So the judge number lands in the registered "report as-is, settles nothing on its
own" band, while the *verified* number refutes the honest prior. Both are reported; neither
is rounded toward the other.

**This is a CEILING, as registered.** The judge saw every `rules/*.md` of both skills. A
real session loads lean — `SKILL.md` plus the rules files matching the work — so the lived
rate is smaller. A low number here would have been strong; **0.176 is not low**, and it is
not yet a claim about practice.

## The three that survived

### 1. CONFIRMED — `sota-network-security` + `sota-sandboxing`: bare CIDR vs identity

`sota-network-security` **SKILL.md non-negotiable 3**: *"Every allow is explicit, justified
in a comment, and references identity (workload identity, label selector, SG/service
account) — **never a bare CIDR** or `world` entity."*

`sota-sandboxing` **rules/03** ships a reference egress NetworkPolicy whose allow is
exactly that:

```yaml
  - to: [{ ipBlock: { cidr: 10.0.5.0/24 } }]   # only the approved backend
```

Implementing the sandboxing example produces a policy the network-security non-negotiable
forbids, and **neither file states an exception**. The strongest of the three: it is a
top-10 non-negotiable on one side and a copyable code block on the other, and a K8s cluster
audit loads both skills by the router's own stated composition.

Worth noting for whoever fixes it: vanilla NetworkPolicy has **no** identity selector for a
destination outside the cluster, so `ipBlock` is the only expressible form there. That
makes network-security's rule too broad as written *or* the sandboxing example wrong about
an in-cluster backend — which is exactly the router's "the fix is an explicit exception in
whichever rule was too broad".

### 2. CONFIRMED — severity rubrics have no stated precedence

`sota-sandboxing` and `sota-threat-modeling` each ship their own Critical/High/Medium/Low
table, and so do `sota-kubernetes` and `sota-network-security`. The router carries a
cross-domain severity model in `sota/rules/03` §1.

The demonstrable defect is **not** that any two tables disagree on a specific finding — it
is that the router says the canonical finding **format** *"supersedes any per-skill
variant"* (`skills/sota/SKILL.md` line 24) and says **nothing equivalent for severity**.
One collision class was resolved explicitly; its sibling was left open. That asymmetry is
in the text and needs no judgement to see.

### 3. CONFIRMED (mild) — `sota-frontend-design` + `sota-web-frameworks`: prop spreading

`sota-frontend-design` rules/03: *"**Spread the rest**: forward `...rest` to the underlying
DOM node"* — unconditional. `sota-web-frameworks` rules/02: *"never spread
attacker-influenced objects onto DOM elements."*

The narrower security rule wins in its domain and **says** it is narrower
("attacker-influenced"), which is the router's resolution working. But the component rule
states no exception, so followed literally on a component whose props carry user input it
produces the injection the other forbids. A one-clause fix.

## The two that were refuted, and why the judge got them

Both refutations have the same cause and it is a **limitation of this design**: the judge
sees a *pair of skills* and **not the router** — which is precisely where conflict
resolution lives.

- **Finding-output schema** (twice: sandboxing+threat-modeling, frontend-design+web-frameworks).
  Both skills do mandate different templates. The router resolves it in its second
  paragraph. Refuted.
- **Severity of a missing default-deny NetworkPolicy** (kubernetes Medium vs
  network-security High). The kubernetes row carries its own scope marker —
  *"(requirement-level; depth → network-security)"* — and the network-security **High** row
  is a different predicate: a default-deny that *exists and is inert*, not one that is
  absent. Its **Medium** row covers the partial case. The judge matched surface wording.
  Refuted — and note the prompt explicitly excluded "a narrower rule that says it is
  narrower", so this is the judge disobeying an instruction, not an ambiguous case.

## What this does not establish

- **Ceiling, not lived rate.** Lean loading is the follow-up and needs its own registration.
- **The judge cannot see the router**, so it over-reports by construction on exactly the
  classes the router was written to resolve. Handing it the router is a design change, not
  a fix to this run.
- **17 pairs, one model, one day**, `sonnet-5`. A rate with its denominator in the sentence.
- **The hand read is mine**, by the same agent that ran the measurement. The three
  confirmations rest on quoted text that `--verify` proved exists, and #1 and #2 are
  checkable without judgement; #3 is a judgement call about how literally a rule is read.
- **Nothing is fixed here.** Repairing the three would change what this measured, so they
  are recorded and left for a follow-up.
