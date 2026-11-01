# Security Policy

SOTA-skills ships **no executable code** — it is a library of Markdown that an AI
assistant reads. There is no runtime, network surface, or build artifact to
exploit. "Security" here means two things specific to a guidance library:

1. **Dangerous or incorrect security guidance** — a skill that recommends an
   insecure pattern, an outdated mitigation, a wrong severity, or advice that
   would lead someone to ship a vulnerability.
2. **A real credential accidentally committed** in an example (the security
   skills are full of *intentional* secret-shaped examples; a genuine one is the
   bug).

Both are taken seriously: bad advice in a widely-read security skill can cause
real-world harm downstream.

## Reporting

**Please do not open a public issue for either case above.** Instead, report
privately via GitHub Security Advisories:

➡️ <https://github.com/martinholovsky/SOTA-skills/security/advisories/new>

Include the file and line, what is wrong, and (for guidance issues) a primary
source — a spec, CVE/CWE, vendor advisory, or authoritative doc — so the fix can
be verified the same way the library asks every claim to be verified.

You can expect an acknowledgement within a few days. Confirmed issues are fixed
on `main`; a credential reported in history is rotated-first and purged.

## Scope

**In scope**

- Insecure, outdated, or incorrect security guidance in any skill or rules file.
- A real secret/credential committed anywhere in the repository or its history.
- A claimed mitigation that does not actually mitigate, or a misclassified
  severity that understates real risk.

**Out of scope**

- Vulnerabilities in third-party tools, libraries, or services that a skill
  merely *mentions* — report those to their respective maintainers.
- The behavior of any AI model that consumes these skills. The skills are
  advisory; how a model or harness acts on them is outside this repository.
- Theoretical issues with no path to harm in a read-only Markdown library.

## Disclosure

Coordinated disclosure is appreciated. Once a fix is on `main` (and any leaked
credential is rotated), the advisory can be published.
