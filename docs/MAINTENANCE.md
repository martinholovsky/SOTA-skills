# Maintenance — keeping the library accurate

The library's value is that its fast-moving claims (versions, CVEs, RFCs,
specs, GA states, tool status, standards) hold up against primary sources.
CI enforces *structure* (the 7 invariants in `scripts/check-invariants.sh` +
gitleaks + shellcheck) but **cannot** verify that a claim is *true* — that
needs web access and judgment. This file is the human/agent process that
covers the accuracy dimension CI can't, plus how efficacy is measured.

The 2026-07-10 audit ([AUDIT-2026-07-10.md](AUDIT-2026-07-10.md)) flagged the
absence of this runbook and eval scaffold as the top strategic gaps.

## 1. The freshness stamp

`LAST-VERIFIED` (repo root) holds the date of the last full-library
re-verification sweep. `scripts/check-freshness.sh` fails once that stamp is
older than the re-verify window (**6 months**; was 12 — content drifts far
faster). `.github/workflows/freshness.yml` runs it monthly (report-only, does
not block PRs). A red freshness report means: **due for a sweep** — run the
procedure below, then bump `LAST-VERIFIED`.

The window is 6 months, not shorter, on purpose: a too-short window is
perpetually red and trains everyone to ignore it (the same failure the
retired per-file-marker backlog had). 6 months catches real drift while
staying clearable.

## 2. The re-verification sweep (runbook)

Goal: re-verify every skill's rot-prone claims against primary sources and
fix what has drifted. Do it as a **rolling** pass (a few skills a month) or a
**batched** sweep before the window expires — either way, update
`LAST-VERIFIED` only after a full pass.

**Per skill:**

1. **Extract the rot-prone claims** — anything with a shelf life: version
   numbers and "latest/current" statements, CVE/advisory IDs and fix
   versions, RFC/ISO/NIST/OWASP/CIS/WCAG numbers and editions, "GA since /
   removed in / deprecated" statements, tool recommendations and their
   maintenance status.
2. **Verify each against a PRIMARY source** you fetch now — vendor release
   notes, the RFC editor, NIST/OWASP pages, GitHub Security Advisories, the
   project's own repo/docs. Not memory, not a blog restating it.
3. **Fix drift under the repo policies** (see
   [CONTRIBUTING.md](../CONTRIBUTING.md)): no rot-prone version pins ("latest
   stable, verify at source"; keep only semantic boundaries like "fixed in
   vX" / "GA since"); replace EOL/unmaintained tools with their maintained
   successor (project-recommended first, then a maintained CNCF/OSS fork),
   keeping a one-line EOL note for auditors.
4. **Adversarially re-verify** — a second pass (ideally a different agent)
   that re-fetches the source and re-reads the edit, defaulting to "wrong"
   until the evidence reproduces. This is where hallucinated citations get
   caught (e.g. the 2026-07 sweeps caught "BIMI = RFC 8910" and a stale
   DMARC RFC this way).

**At scale**, this is a natural multi-agent job: one research+fix agent per
skill in parallel, then an independent adversarial verify pass, then land the
fixes via PR. The 2026-07-08 sweep (65 fixes) and 2026-07-10 audit followed
exactly this shape, reproducible from the CHANGELOG entries.

**After a full pass:** set `LAST-VERIFIED` to today (`date +%F`), note the
sweep in the CHANGELOG, and open a PR. Do **not** add per-file markers — that
convention is retired.

## 3. Measuring efficacy (the eval harness)

Freshness keeps claims *true*; the eval harness (`evals/`) keeps the library
*effective* — does loading a skill actually change agent output for the
better? It is a manually-run prototype (an LLM eval can't run deterministically
in CI): golden-set cases with expected outcomes + a scoring script. See
[`evals/README.md`](../evals/README.md) for how to run it and read the score.
Run it before and after a large content change as a regression check, and
grow the golden sets as coverage warrants.

## 4. What is and isn't automated

| Dimension | Gate | Automated? |
|---|---|---|
| Structure (line cap, checklist-last, description cap, counts, router completeness) | `check-invariants.sh` (7 checks) | Yes — pre-commit + CI |
| Secrets | gitleaks (full history) | Yes — CI |
| Shell quality | shellcheck | Yes — CI |
| Claim **accuracy** | this runbook + `LAST-VERIFIED` | No — human/agent, monthly red-flag |
| **Efficacy** | `evals/` | No — manual prototype |

The bottom two are deliberately not in CI: verifying a claim against a live
primary source, or scoring an LLM's output, is non-deterministic and needs
network + judgment. Keeping them honest is a maintainer discipline, and this
file is the checklist for it.
