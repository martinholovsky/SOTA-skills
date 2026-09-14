# PowerShell routing — the claimed gap did not reproduce, and the real one is narrower

**Date:** 2026-09-14 · **Runner:** [`evals/run-desc-routing.py`](../../run-desc-routing.py)
· **Model:** `anthropic/claude-sonnet-4.6` · 3 samples, temp 0.7, objective name-match
scoring · **Arms:** pre-change tree (`origin/main`, **0 of 42 descriptions naming
PowerShell**) vs this branch.

This is a **probe set, not a measurement set**. Its cases were selected by outcome and must
never be averaged into the published A/B number (`sota-llm-engineering` rules/01 §8).

## Why it was run

An external audit claimed PowerShell had "no explicit description match". Grepping confirmed
the *string* was absent from every description — and that was taken as a routing gap. It is
not the same claim, and the difference is the whole finding here.

## Result

| case | phrasing carries | before | after |
|---|---|---|---|
| `r4_powershell_windows_ci` | "PowerShell **script**", "$ErrorActionPreference", CI | **1.00** | 1.00 |
| `h1_no_script_word` | ".ps1", "deploy step", terraform/docker — no "script"/"shell" | **1.00** | 1.00 |
| `h2_pwsh_only` | "**pwsh** automation", "**injection** risk", "release runner" | **0.00** | **1.00** |

`h2` before: `sota-code-security` on 3 of 3 samples. After: `sota-shell-scripting` on 3 of 3.
Both ablation arms (with and without the negative cross-reference) agree in both directions,
so the movement is carried by the **keywords**, not the cross-ref sentence.

## What this refutes, including something of ours

**The audit's claim, as stated, does not reproduce.** A Windows CI PowerShell task routed
correctly *before* any change, from "shell scripting … CI scripts … entrypoint script" alone.
The absent string was not an absent capability.

**And the first version of this work repeated the same error.** The `r4_powershell_windows_ci`
regression case was written from the grep, added to a set whose SELECTION RULE says "each case
exists because a specific mis-route actually happened" — and it pins **nothing**: 1.00 in both
arms. It was replaced by `h2`, which is an observed mis-route. This is
[`measure-before-you-agree`](../../../docs/ADOPTION-LOG.md) in its exact documented shape:
*grep answers "does this string appear", never "is this idea covered"*.

## What survives

The **routing** gap is real but narrow, and neither the audit nor our own first pass had
located it: it appears when a task names PowerShell **without** shell/script vocabulary
**and** carries a competing signal — here, "injection", which is squarely `sota-code-security`
territory. Two of three phrasings never needed the fix.

The **content** gap was never in question and is what justified the work: 0 files taught
PowerShell, so `rules/07` is new capability regardless of how tasks route to it.

## Limits

Three phrasings, one model, n=3 each, temp 0.7. Enough to refute an absence claim (one
observed mis-route does that) and **not** enough to size the effect. No lift is claimed and
none of these numbers belong on the scoreboard.
