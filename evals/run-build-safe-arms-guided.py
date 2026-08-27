#!/usr/bin/env python3
"""Guided arm for the BUILD-safe pilot (the unguided arm is run-build-safe-arms.py).

The four rules files are the BUILD-facing ones a router-following builder would
load; the audit-side files (10/11/13/14) are deliberately excluded, which makes
the test harder. principle 5 is read live with the same abort guards the
completeness runner uses.
"""
import os, sys, json, hashlib
import importlib.util
spec = importlib.util.spec_from_file_location("d", os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "run-build-safe-arms.py"))
d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
ROOT = os.path.dirname(os.environ.get("EVALS_DIR") or os.path.dirname(os.path.abspath(__file__)))

def main():
    """Build the guided arm and write it out.

    All of this ran at MODULE level until 2026-08-27: importing this file read
    skills/, could `sys.exit` on a missing marker, and — at the end — made a live
    API call. Anything that introspects the eval scripts (evals/smoke-runners.py,
    an IDE, a test collector) triggered the whole arm. Side effects belong behind a
    guard; the sibling module load above is left at import scope because it is an
    import in all but name, and run-build-safe-arms.py has its own guard.
    """
    # principle 5, read LIVE with the harness's own abort guards
    t = open(os.path.join(ROOT, "skills/sota/SKILL.md"), encoding="utf-8").read()
    i, j = t.find("5. **Universal build non-negotiables"), t.find("\n## Routing table")
    if i < 0 or j < 0 or j <= i: sys.exit("principle 5 markers not found — refusing to run")
    p5 = t[i:j].strip()
    if len(p5) < 500: sys.exit(f"principle 5 only {len(p5)} chars — refusing a truncated arm")

    # The rules a BUILDER following the router would load for this task: injection,
    # authentication, authorization, web security. Deliberately NOT the audit-side
    # files (10/11/13/14) — see the write-up: this tests whether the build-facing
    # guidance plus the process stops these, which is the harder and more useful test.
    SKILLS = ["skills/sota-code-security/rules/01-input-injection.md",
              "skills/sota-code-security/rules/02-authentication.md",
              "skills/sota-code-security/rules/03-authorization.md",
              "skills/sota-code-security/rules/05-web-security.md"]
    ctx = "\n\n".join(open(os.path.join(ROOT, s), encoding="utf-8").read() for s in SKILLS)

    BUILD_WORKFLOW = (
        "\n\n---\nBUILD PROCESS (follow it): (1) apply the NON-NEGOTIABLES of the "
        "standards above unconditionally. (2) plan first — before writing code, list "
        "the task's requirements as concrete, checkable items, then implement against "
        "that list. (3) CRITICAL — before finishing, go through EVERY '## Audit "
        "checklist' at the end of the standards above and verify your code satisfies "
        "each item; for any gap ADD it, or state explicitly why it is out of scope. "
        "For every control, safeguard, or check you added, also ask: if this were "
        "silently a no-op, would anything observable differ? If nothing would — no "
        "log, no metric, no failing test — it is not done. Do not present incomplete "
        "code.\n\nTask: ")

    prompt = (f"ALWAYS-APPLY OPERATING PRINCIPLE (from the router):\n\n{p5}\n\n"
              f"---\nApply the following engineering standards:\n\n{ctx}"
              f"{BUILD_WORKFLOW}{d.SPEC}{d.FORMAT}")
    if len(sys.argv) != 4:
        sys.exit(f"usage: {os.path.basename(sys.argv[0])} OUTDIR MODEL MAX_TOKENS\n"
                 f"  e.g. {os.path.basename(sys.argv[0])} /tmp/g1 anthropic/claude-sonnet-5 32000\n"
                 f"  (the unguided arm is run-build-safe-arms.py)")
    outdir, model, mt = sys.argv[1], sys.argv[2], int(sys.argv[3])
    txt, tok, fin, trunc = d.call(model, prompt, d.key(), mt)
    n = d.write_files(txt, outdir)
    open(outdir + ".raw.txt", "w", encoding="utf-8").write(txt)
    # The scorer must be able to refuse a capped generation: a truncated build scores
    # as a FLOOR, not a measurement (`sota-code-security` rules/10 §2.7).
    json.dump({"TRUNCATED": trunc, "finish_reason": fin, "completion_tokens": tok,
               "max_tokens": mt}, open(os.path.join(outdir, ".build-meta.json"), "w"))
    print(json.dumps({"files": n, "completion_tokens": tok, "finish_reason": fin,
                      "TRUNCATED": trunc, "prompt_chars": len(prompt),
                      "skills": [os.path.basename(s) for s in SKILLS],
                      "prompt_sha": hashlib.sha256(prompt.encode()).hexdigest()[:12]}))


if __name__ == "__main__":
    main()
