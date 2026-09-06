# Authoring a skill others install, and auditing one for being wrong

`rules/01` and `rules/02` treat a skill as a supply-chain artifact. This treats it
as what it is once loaded: **a control**. Controls can be inert, wrong, or
confidently wrong, and a skill is unusually good at the third.

---

## 1. The description is the interface, and it is the whole classifier

On platforms that auto-load skills, **only the frontmatter description is read
until the skill fires.** The body — every rule you wrote — is inert until something
decides to load it. Three consequences that authors get wrong:

- **The description is not marketing, it is a trigger classifier.** It decides when
  your rules apply and when they silently do not. Write the conditions, the trigger
  vocabulary a real task would use, and the **negative boundary**: *"Not for X — use
  Y."* That one sentence is what stops a tempting sibling absorbing the task.
- **Numbered imperatives in the body are obeyed; subordinate clauses are not.** A
  requirement buried mid-sentence in a paragraph is a requirement that does not
  survive a long context. Put load-bearing rules where they read as instructions.
- **Caps are real and silent.** Where a platform caps the description length,
  exceeding it can make the loader skip the skill entirely — a skill that is
  installed, correct, and never loads. Check the cap; do not assume truncation.

**Changing a description is changing behaviour** (`rules/01` §2). Version it with
the same care as a rule.

## 2. A skill is a control — and the dangerous failure is confidence

Three failure modes, worst last:

1. **Inert** — never loads (bad trigger, over-cap description, unindexed file).
   Detectable: nothing changes when you delete it.
2. **Wrong** — states something false. Detectable by review against a primary source.
3. **Confidently wrong** — states something false, *specifically*, with a version
   number and a rationale. This is the one that ships, because specificity reads as
   authority and a reader who would have checked a vague claim does not check a
   precise one.

The third is why **freshness is a security property of a skill**, not a quality nicety:

- a pinned tool version that has since had an advisory;
- a "current best practice" that a standard has superseded;
- a command that changed its flags, so the guidance now produces a usage error
  *about the product under test* rather than a finding.

**Rules for the author:**

- **Cite a primary source, at a date, for anything version- or advisory-sensitive** —
  and prefer "latest stable, verify at «official source»" over a number that rots.
- **Version numbers mark semantic boundaries only**: "GA since", "fixed in", "removed
  in". Not "the current release is".
- **Reproduce before you assert.** A per-language table row written from recall is
  the single most reliable place to be confidently wrong; measure the row.
- **Where a recommended tool goes EOL, name the successor** and keep one line saying
  why, so an auditor can date the change.

## 3. State what you did not verify

A skill transfers confidence at scale: every session that loads it inherits the
author's certainty, including the parts the author never checked.

- **Mark unverified claims as unverified**, in the text, not in a commit message.
- **State the scope you tested.** *"Verified on Kubernetes + one orchestrator; the
  equivalent surface on other platforms is not checked"* is more useful than a
  confident generalisation, and it tells the next author exactly what to extend.
- **State what the rule does not cover.** A skill silent on its own limits is the
  one that reaches production unchallenged.
- **Do not launder a measurement.** If a number came from one sample at temperature
  zero, say so beside the number. A lift quoted without its sample size will be
  requoted without its sample size.

## 4. Authoring hygiene for a skill others install

- **No credentials, ever** — not in examples, not in fixtures. Where a secret-shaped
  example is genuinely needed, make it obviously synthetic and expect scanners to
  flag it.
- **No unexplained network calls**, and no install-time fetching of guidance
  (`rules/01` §3 makes such a skill unreviewable).
- **No shell unless shell is the point**, and then only the shell the purpose needs
  (`rules/02` §1).
- **Keep it generic.** Internal hostnames, project names and stack assumptions leak
  the author's employer into every consumer's context, and abbreviations leak just
  as effectively as full names.
- **Make the skill's own claims checkable.** Where a rule asserts a count, a cap or a
  file list, something should be able to verify it — the same standard the skill
  would impose on the code it audits.

## 5. Auditing someone else's skill set

Sample rather than read everything, and sample where being wrong is expensive:

1. **The security-relevant claims first.** A wrong crypto or authz prescription is
   the worst outcome and the cheapest to check against a standard.
2. **Anything with a version number** — the freshness pass of §2.
3. **Anything that tells the agent to disable, skip or bypass** a check.
4. **The descriptions**, as a set: do two overlap, and does anything say which wins
   (`rules/02` §3)?
5. **The unreached files.** A rules file no index points at is written, capped, and
   never loaded — inert by construction.

Report findings as `file:line | rule | severity | effort | fix`, and rate severity by
**what an operator would do differently if they believed it**.

---

## Audit checklist

- [ ] **Every skill's description written as a trigger classifier** (§1) — conditions,
      real task vocabulary, and a **negative boundary** where a tempting sibling
      exists — and checked against the platform's length cap, since exceeding it can
      make the skill silently never load?
- [ ] **Load-bearing rules written as imperatives**, not as subordinate clauses in
      prose (§1)?
- [ ] **Freshness treated as a security property** (§2): every version-, advisory- or
      command-sensitive claim carries a primary source and a date, version numbers mark
      only semantic boundaries, and EOL tools name their successor?
- [ ] **Per-language / per-tool table rows reproduced rather than recalled** (§2) —
      the highest-yield place for a confidently wrong claim?
- [ ] **Unverified claims marked unverified in the text**, and the tested scope stated
      rather than generalised (§3)?
- [ ] **Numbers carry their sample size** where the skill quotes a measurement (§3)?
- [ ] **No credentials, no unexplained network calls, no shell beyond the skill's
      purpose, no internal names or stack assumptions** (§4)?
- [ ] **Audit sample weighted to expensive-if-wrong claims** — security prescriptions,
      version-pinned facts, and anything instructing the agent to disable a check (§5)?
- [ ] **Unreached files identified** — any rules file no index points at is inert by
      construction (§5)?
