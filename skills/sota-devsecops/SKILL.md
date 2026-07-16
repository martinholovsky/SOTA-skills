---
name: sota-devsecops
description: >-
  State-of-the-art DevSecOps and software supply chain security (2026). Applies when building or auditing CI/CD pipelines, GitHub Actions workflows, supply chain controls, SBOM generation, SAST/secret-scanning gates, dependency management, container builds, container/artifact registries, IaC (Terraform), GitOps, and deployment strategy. Trigger keywords: CI/CD, pipeline, GitHub Actions, supply chain, SBOM, SAST, dependency, container build, container registry, registry security, Zot, Harbor, ECR, GAR, ACR, GHCR, immutable tags, pull-through cache, IaC, Terraform, deployment, provenance, SLSA, cosign, dependabot, renovate. Use for BOTH setting up new pipelines and auditing existing ones. Not for application code vulnerabilities (use sota-code-security) or in-cluster runtime hardening (use sota-kubernetes).
---

# SOTA DevSecOps & Supply Chain Security

## Purpose

This skill encodes the 2026 state of the art for securing the path from source code to
running workload: pipeline hardening, dependency and artifact supply chain, build integrity,
analysis gates, IaC/deployment security, and runtime policy enforcement. It is defensive:
every rule exists to prevent a real, named class of compromise (token theft, workflow
injection, dependency confusion, tag mutation, state leakage, bypassable gates).

Two operating modes. Pick one explicitly at the start of the task.

## BUILD mode

Use when creating or extending pipelines, Dockerfiles, Terraform, GitOps configs, or
dependency tooling.

1. Identify which stages of the source-to-production path the task touches (source → CI →
   build → artifact → deploy → runtime) and read the matching rules files from the index
   below BEFORE writing config.
2. Default to the most restrictive option that works: read-only tokens, OIDC over stored
   keys, SHA pins, digest pins, frozen lockfile installs, non-root distroless runtime.
   Loosen only with a written reason in a comment.
3. Every gate you add must be a **required** check that fails closed. A scanner whose job
   is `continue-on-error: true` is documentation, not a control.
4. Ship the verification path with the signing path: if you generate provenance/signatures/
   SBOMs, also wire the consumer (admission policy, `gh attestation verify`, cosign verify
   in CD). Unverified attestations are dead weight.
5. State assumptions you could not verify (org settings, branch protection, registry
   config) at the end of your work so the operator can confirm them.

## AUDIT mode

Use when reviewing existing pipelines, workflows, Dockerfiles, IaC, or dependency posture.

Process: enumerate workflows/build files/IaC; for each, walk the relevant Audit checklist
at the end of every rules file; report findings in the format below; do not report style
nits as security findings.

### Severity conventions

| Severity | Meaning | Examples |
|---|---|---|
| **Critical** | Remote compromise of pipeline, secrets, or artifacts is achievable now by an external party | `pull_request_target` checking out PR head with secrets; script injection from PR title into `run:`; long-lived cloud admin keys in repo secrets used by fork-triggered workflow; unauthenticated registry push |
| **High** | Compromise achievable by a contributor, or a single upstream event away | Actions pinned to mutable tags; no branch protection on default branch; CI token with `write-all`; no lockfile / unfrozen installs; Terraform applies from un-reviewed plans with admin creds |
| **Medium** | Weakens defense in depth or detection | Missing SBOM/provenance; scanners non-blocking; no drift detection; mutable image tags in deploy manifests; no secret-scanning push protection |
| **Low** | Hygiene, hardening headroom | Missing `.dockerignore`; unpinned dev-only tooling; verbose CI logs; missing CODEOWNERS on workflows |

Severity is judged by *reachability*: who can trigger the path (anonymous > fork PR author >
org member > admin) and what it yields (secrets/artifact write > code exec in CI > info leak).

### Finding format

```
[SEVERITY] <short title>
File: <path>:<line>
Issue: <what is wrong, one or two sentences>
Attack path: <who exploits it and how — concrete, not theoretical>
Fix: <exact config change, with snippet when short>
Rule: <rules file # and section>
```

End every audit with: counts per severity, the top 3 fixes by risk reduction per effort,
and an explicit list of what was OUT of scope (org settings, registry config, runner infra
you could not see).

## Rules index

| File | Read this when... |
|---|---|
| [rules/01-pipeline-security.md](rules/01-pipeline-security.md) | Writing or auditing CI workflows: GITHUB_TOKEN permissions, OIDC to cloud, SHA-pinning actions, `pull_request_target` / fork PR handling, script injection, self-hosted runners, branch/environment protection, signed commits, workflow-file ownership |
| [rules/02-provenance-signing.md](rules/02-provenance-signing.md) | Artifact integrity: SLSA levels, build provenance, in-toto attestations, Sigstore/cosign keyless signing, GitHub artifact attestations, npm/PyPI trusted publishing, release and tag integrity, verification at deploy time |
| [rules/03-dependencies.md](rules/03-dependencies.md) | Anything touching package manifests or lockfiles: frozen installs, dependency review gates, dependency confusion and registry scoping, typosquatting and malicious-package indicators, SBOM (CycloneDX/SPDX), vuln scanning with osv-scanner/grype, VEX and triage discipline, Renovate/Dependabot strategy, vendoring |
| [rules/04-build-containers.md](rules/04-build-containers.md) | Dockerfiles and build systems: hermetic/reproducible builds, multi-stage builds, build secrets, base image strategy (distroless/Chainguard, digest pinning), image scanning, registry security, immutable tags |
| [rules/05-analysis-gates.md](rules/05-analysis-gates.md) | CI quality/security gates: SAST (Semgrep/CodeQL), secret scanning and push protection, IaC scanning (checkov/trivy/tfsec), DAST, license compliance, making gates non-bypassable (required checks, no continue-on-error), flaky-test discipline |
| [rules/06-iac-deployment.md](rules/06-iac-deployment.md) | Terraform and delivery: state security, plan/apply separation with review, saved-plan apply, drift detection, GitOps (Flux/Argo) security model, progressive delivery (canary/blue-green/flags), rollback readiness, build-once-promote-many environment parity |
| [rules/07-runtime-ops.md](rules/07-runtime-ops.md) | Runtime enforcement and operations: admission control for signed images (Kyverno/policy-controller), policy as code (OPA/Kyverno) with tests, Pod Security, incident-ready CI/CD audit logging, deployment traceability, backup/restore testing, break-glass |
| [rules/08-registry-security.md](rules/08-registry-security.md) | Securing the container/artifact registry as infrastructure: the registry as a tier-0 supply-chain trust anchor; no anonymous push/pull and least-privilege robot/CI accounts (Zot accessControl, Harbor robots, cloud IAM); immutable tags and digest pinning to defeat tag mutation; OCI referrers for signature/SBOM/scan storage; scan-on-push and continuous re-scan; pull-through cache and image-layer dependency confusion; retention/GC that won't break running deploys; registry HA/backup; network hardening (no anonymous internet exposure, no hostNetwork, TLS) |

When a task spans stages (most do), read every matching file. For a full pipeline audit,
read all eight.

## Top 10 non-negotiables

Violations of these are at minimum **High** in AUDIT mode and must never be introduced in
BUILD mode:

1. **Top-level `permissions:` block in every workflow**, starting from `contents: read`
   (or `{}`), elevating per job only. Never rely on org/repo default token permissions.
2. **No long-lived cloud credentials in CI secrets.** Use OIDC federation with
   `sub`-claim conditions scoped to repo + ref/environment.
3. **Pin third-party actions (and base images) by full commit SHA / digest**, with a
   version comment, updated by Renovate/Dependabot. Tags are mutable attack surface.
4. **Never combine untrusted PR code with secrets or write tokens.** `pull_request_target`
   (or `workflow_run`) must not check out or execute PR head content; treat fork artifacts
   as hostile input.
5. **No untrusted expression interpolation in `run:` scripts.** PR titles, branch names,
   issue bodies, commit messages go through `env:` indirection, quoted.
6. **Lockfiles committed; CI installs are frozen** (`npm ci`, `--frozen-lockfile`,
   `--require-hashes`, `--locked`). A build that resolves versions at build time is not
   reproducible and not reviewable.
7. **Security gates are required status checks that fail closed.** No
   `continue-on-error`, no `|| true`, no unprotected default branch, no "admins bypass".
8. **Build once, promote the same digest through environments.** Deploy manifests
   reference image digests (or signed, verified tags), never `:latest`.
9. **Terraform state is secret material**: remote encrypted backend, least-privilege
   access, plan on PR with read-only creds, apply only a reviewed saved plan via a
   protected environment.
10. **Production admission requires verified provenance**: signed images (cosign/Kyverno
    verifyImages or equivalent), non-root, pinned digests — enforce, don't just audit.

If the user asks for something that violates a non-negotiable, implement the secure
alternative and explain the delta; only comply after they acknowledge the risk explicitly.
