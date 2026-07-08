# 07 — Runtime Enforcement & Operations (admission, policy as code, logging, recovery)

Scope: the controls that make the rest of this skill *enforced* rather than aspirational —
the cluster refuses unverified artifacts, policy lives in git with tests, every action is
attributable, and recovery is proven, not presumed.

## 7.1 Admission control: only verified images run

The pipeline's signatures and attestations (rules/02) mean nothing if the cluster runs
whatever it's handed. Admission is where supply chain security becomes mandatory.

```yaml
# Kyverno ImageValidatingPolicy (CEL, v1 — GA since 1.17) — require cosign keyless
# signature + provenance from the release workflow, prod namespaces
apiVersion: policies.kyverno.io/v1
kind: ImageValidatingPolicy
metadata: { name: verify-image-signature }
spec:
  validationActions: [Deny]                          # not Audit — see rollout
  webhookConfiguration: { failurePolicy: Fail }
  validationConfigurations: { mutateDigest: true }   # rewrite tag → verified digest
  matchConstraints:
    namespaceSelector: { matchLabels: { env: prod } }
    resourceRules:
      - apiGroups: [""]
        apiVersions: [v1]
        resources: [pods]
        operations: [CREATE, UPDATE]
  matchImageReferences:
    - glob: "ghcr.io/myorg/*"
  attestors:
    - name: release
      cosign:
        keyless:
          identities:
            - subject: "https://github.com/myorg/*/.github/workflows/release.yml@refs/heads/main"
              issuer: "https://token.actions.githubusercontent.com"
        ctlog: { url: "https://rekor.sigstore.dev" }
  attestations:
    - name: provenance
      intoto: { type: https://slsa.dev/provenance/v1 }  # require provenance, not just a signature
  validations:
    - expression: >-
        images.containers.map(i, verifyImageSignatures(i, [attestors.release])).all(e, e > 0)
      message: image not signed by the release workflow
    - expression: >-
        images.containers.map(i, verifyAttestationSignatures(i,
        attestations.provenance, [attestors.release])).all(e, e > 0)
      message: missing or unverified provenance attestation
```

Legacy: the `kyverno.io/v1` ClusterPolicy `verifyImages` pattern still works but is
deprecated since Kyverno 1.17 (Feb 2026; critical fixes only from 1.18, removal planned
for v1.20, Oct 2026) — write new policies against the CEL v1 types and migrate existing
ones via the project's ClusterPolicy→CEL migration guide, pinning the same subject/issuer.

Rules:
- **Registry allowlist first**: a policy verifying `ghcr.io/myorg/*` but admitting
  `docker.io/anything` unverified is a bypass with extra YAML. Pair signature
  verification with "images only from these registries" (and rules/04 §4.5 prod-registry
  promotion).
- Verify **identity, not existence**: exact issuer + subject (workflow), as in rules/02
  §2.3 — `subject: "*"` verifies that *someone* used Sigstore.
- Require the **provenance/SBOM attestations**, not just a signature, once rules/02 is in
  place; optionally add freshness conditions (scan attestation < N days).
- `failurePolicy: Fail` on the webhook for prod admission — `Ignore` means "enforce
  unless the enforcer is down", which is the first thing an attacker or an outage takes
  out. Accept the availability tradeoff consciously (HA the controller; exempt
  kube-system to avoid bricking the cluster).
- Cover all Pod-producing paths (Kyverno/policy-controller handle Pod via workload
  controllers; verify your policy matches Deployments/CronJobs creation too, or relies on
  Pod-level matching that can't be skipped).
- **Rollout pattern**: `Audit` → triage violations to zero → flip to enforce (`Deny` for
  the CEL policy types). Shipping
  straight to Enforce breaks workloads and gets the policy deleted; staying in Audit
  forever is the Medium finding "decorative admission".
- Alternatives: Sigstore `policy-controller` (`ClusterImagePolicy`) if you want
  verification-only; OPA Gatekeeper + external-data cosign provider works but is more
  moving parts. Cloud-native equivalents (Binary Authorization on GKE) are fine — same
  identity-pinning rules.

## 7.2 Policy as code (OPA / Kyverno) — beyond image verification

The baseline policy set every cluster should enforce (mirrors rules/04 hardening):

- Pod Security Admission `restricted` (or equivalent policies): no privileged, no
  hostPath/hostNetwork/hostPID, `runAsNonRoot`, no privilege escalation, seccomp
  RuntimeDefault, capabilities dropped.
- Org invariants: digests not tags (`:latest` denied), resource limits present, required
  labels (owner, app) for attribution, no `default` ServiceAccount with API access,
  ingress/Service restrictions per tier.
- Beyond the cluster: same policy-as-code approach for IaC (conftest/OPA in the plan
  gate, rules/05 §5.3) and for CI config — one policy language strategy, many enforcement
  points.

```yaml
# Pod Security Admission — enforce restricted in prod, warn ahead of enforcement elsewhere
apiVersion: v1
kind: Namespace
metadata:
  name: prod-payments
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: "v1.36"   # pin to your cluster's minor — 'latest' changes under you
    pod-security.kubernetes.io/warn: restricted
    pod-security.kubernetes.io/audit: restricted
```

PSA gives the hardened-pod baseline for free; Kyverno/Gatekeeper add what PSA can't
express (image rules, label requirements, org invariants). Use both — replacing PSA with
hand-rolled policies usually re-implements it worse.

Engineering discipline (policies are production code):
- **Policies live in git**, deployed via GitOps (rules/06 §6.4) — never `kubectl apply`'d
  by hand; the policy repo is protected like prod because it *is* the prod rulebook.
- **Policies have tests**: `kyverno test` fixtures / OPA `opa test` + conftest unit tests
  with good/bad manifests, run as a required CI check on the policy repo. An untested
  policy change can no-op your entire admission layer in one merge (test the *deny* cases
  especially).
- **Exceptions are first-class, scoped, and time-bound**: Kyverno `PolicyException` (or
  documented exclusion lists) naming the workload, the policy, a reason, an owner, and an
  expiry — reviewed via PR like any code. A namespace-wide permanent exemption is policy
  deletion in disguise (High). Inventory exceptions on a schedule (rules/05 §5.1
  suppression discipline applies).
- Version and stage policy rollouts (audit→enforce per policy, per environment) and
  monitor webhook latency/error budgets — a flapping webhook gets `failurePolicy: Ignore`d
  by a tired SRE at 3am unless you've engineered it properly.

```yaml
# kyverno-test.yaml — the deny case is the one that matters
apiVersion: cli.kyverno.io/v1alpha1
kind: Test
metadata: { name: image-policy-tests }
policies: [verify-image-signature.yaml]
resources: [fixtures/signed-pod.yaml, fixtures/unsigned-pod.yaml, fixtures/dockerhub-pod.yaml]
results:
  - policy: verify-image-signature
    rule: require-signed-images
    resources: [signed-pod]
    result: pass
  - policy: verify-image-signature
    rule: require-signed-images
    resources: [unsigned-pod, dockerhub-pod]
    result: fail            # if this fixture ever "passes", the gate is open — CI must catch it
```

(Fixture above uses the legacy ClusterPolicy schema; the Kyverno CLI also tests the CEL
v1 policy types — carry the same deny-case fixtures over when migrating.)

OPA equivalent: `opa test policies/ -v` with `deny` rule unit tests, plus
`conftest test --policy policies/ fixtures/` in the same required check.

## 7.3 Incident-ready logging & deployment traceability

Design logging for the worst day: "we think the pipeline was compromised three weeks ago —
what did it touch?"

Must-capture, retained beyond the incident-discovery horizon (≥ 1 year for pipeline audit
trails is a common floor; match your compliance regime):

- **CI/CD audit events**: workflow runs (who/what/when/SHA), secret access, environment
  approvals, workflow-file changes, runner registrations, org Actions-policy changes
  (GitHub audit log streaming to your SIEM — the in-product retention is short).
- **Deploy events**: digest, source SHA, pipeline run URL, approver, environment — the
  rules/02 §2.8 traceability triple, emitted to your observability stack as deploy
  markers (also makes "what changed?" the first incident query it should be).
- **Admission decisions**: policy denials *and* exception uses; an attempted unsigned
  image in prod is a page, not a log line.
- **Registry events**: pushes (which identity wrote which digest), deletions, auth
  failures.
- **Cluster/cloud control plane**: kube-audit (at least metadata level on writes,
  request-level on secrets access), CloudTrail/equivalent — with the TF apply roles and
  GitOps controller identities as named, alertable principals: those identities acting
  outside their pipelines is a high-fidelity compromise signal.

Properties: logs ship to storage the producing system cannot alter or delete
(write-once/object-lock or a separate logging account) — an attacker with CI compromise
must not be able to erase the CI audit trail (same logic as Rekor's transparency log).
Alert on the high-signal few: workflow modifications on release workflows, new runner
registration, admission-policy changes, break-glass use (§7.5), bypass events (rules/05
§5.2). Don't ship 400 unactioned detections; ship ten that page.

### 7.3.1 High-signal detections for the delivery chain

| Signal | Why it pages |
|---|---|
| Modification of release/deploy workflow files or org Actions policy | Gate tampering — precedes artifact injection |
| New self-hosted runner registered / runner label change | Attacker-controlled build capacity |
| `id-token`-bearing job in an unexpected workflow/ref | OIDC role-assumption staging |
| TF apply role or GitOps controller identity used outside its pipeline source | Stolen pipeline identity in interactive use |
| Registry push to a release repo by a non-CI identity | Bypasses the only-CI-writes invariant (rules/04 §4.5) |
| Admission policy changed / PolicyException created | Enforcement-layer tampering |
| Unsigned-image admission attempt in prod | Either an attack or a broken pipeline — both urgent |
| Secret-scanning push-protection bypass approved | Human judged a secret OK — verify |
| Break-glass credential checkout | By definition exceptional |

Each detection needs an owner and a tested response path; a detection nobody drills is a
dashboard widget.

## 7.4 Backup & restore testing

A backup that has never been restored is a hypothesis. Scope is wider than the database:

- **Inventory what reconstruction needs**: databases AND object stores, Terraform state
  (rules/06 §6.1 — losing state orphans the infra), container registry (released digests
  + attestations, rules/04 §4.5), git (the GitOps repo is prod), secret manager contents,
  CA/KMS key material (without the KMS key, encrypted backups are noise — key DR is its
  own plan), CI configuration.
- **Define RPO/RTO per system, then test against them**: scheduled automated
  restore-verification (restore to an isolated environment, run integrity checks, report)
  — quarterly minimum for tier-0, plus a periodic full game-day that exercises the
  *people* and the runbook, not just the cron job.
- Backups are an attack target (ransomware's first stop): separate account/project,
  separate credentials that prod identities cannot reach, immutability/object-lock on the
  backup store, and **deletion requires a second identity** (no single principal can
  destroy prod *and* its backups — check this explicitly; it's commonly violated by an
  admin role that spans both). Backup access is also data access: encrypt, restrict
  reads, log them.
- Restore *security* posture too: a restored environment must come back inside the same
  controls (admission policies, secrets re-pointed, old credentials not resurrected from
  the backup).
- Audit severity: no restore testing = High masquerading as "we have backups"; backups
  deletable by prod-compromising credentials = High.

### 7.4.1 Recovery scope matrix (verify each cell has an owner and a tested procedure)

| Asset | Backup mechanism | Restore tested? | Deletable by prod creds? |
|---|---|---|---|
| Databases | PITR + snapshots, cross-account copy | scheduled auto-verify | must be NO |
| TF state | bucket versioning + replication | drill: restore N-1 state, plan must be clean | must be NO |
| Git (incl. GitOps repo) | mirror to second provider/account | drill: rebuild from mirror | must be NO |
| Registry (released digests + attestations) | replication / immutable storage | pull + verify signatures from replica | must be NO |
| Secret manager | provider backup or sealed export | restore to isolated vault, count entries | must be NO |
| KMS/CA keys | multi-region keys, documented key DR | tabletop minimum | N/A — focus on availability |

The right-hand column is the ransomware question; answer it with actual IAM policy
review, not assumption.

## 7.5 Break-glass — the audited escape hatch

Every gate in this skill needs exactly one legitimate bypass, or the first sev-1 will
create an unaudited one permanently:

- A documented break-glass identity/path per system (cluster-admin cred in a sealed vault
  slot, ruleset bypass role, registry direct-push identity) that is: normally unused,
  **alerted on use** (page, not log), time-bound, and followed by a mandatory post-use
  review that re-rotates the credential and reconciles whatever was changed back into git
  (drift handling, rules/06 §6.3).
- Break-glass use is an *input to process fixes*: frequent use means a gate is
  mis-designed — fix the gate, don't normalize the bypass.
- Audit both failure modes: no break-glass defined (gates will be dismantled under
  pressure) and break-glass that is just "the admins bypass protection routinely"
  (rules/05 §5.6 — that's not break-glass, that's no glass).

## 7.6 Closing the loop

Runtime signals feed back into the pipeline: admission denials reveal unsigned/legacy
images to migrate; drift corrections reveal process gaps; scanner findings on *deployed*
digests (rules/03 §3.6) drive rebuild-and-promote of patched bases (rules/04 §4.3);
incident retros add Semgrep rules (rules/05 §5.1) and admission policies. A DevSecOps
setup that only adds controls and never tunes them ends as the bypassed, resented variety.
Track: gate latency, exception/suppression counts and ages, time-to-remediate by severity,
rollback drill recency, restore test results. Those five trends are the honest health
dashboard of everything in this skill.

## Audit checklist

- [ ] Admission enforces (not audits) image verification in prod: exact signer identity + issuer, provenance attestation required, registry allowlist, tag→digest mutation, `failurePolicy: Fail`, all Pod-paths covered; Kyverno policies on the CEL v1 types (ClusterPolicy deprecated since 1.17, removal planned v1.20)
- [ ] Baseline workload policies enforced: PSA restricted-equivalent, no `:latest`, non-root, resource limits, attribution labels
- [ ] Policies in git, GitOps-deployed, with CI-tested deny cases; exceptions are scoped, owned, time-bound, PR-reviewed, and inventoried
- [ ] CI/CD, deploy, admission, registry, and control-plane audit events stream to tamper-resistant storage with ≥1y retention; pipeline identities are alertable principals
- [ ] Deploy traceability: digest → source SHA → run → approver queryable in seconds; deploy markers in observability
- [ ] High-signal alerts wired: release-workflow modification, runner registration, policy change, unsigned-image attempt, break-glass use, push-protection bypass
- [ ] Backup inventory covers state/registry/git/secrets/keys; restores tested on schedule against RPO/RTO; backups immutable, in a separate trust domain, not deletable by prod-compromising credentials
- [ ] Break-glass documented per gate, alarmed on use, time-bound, post-reviewed, reconciled to git; routine admin bypass absent
- [ ] Feedback loop metrics tracked: gate latency, exception age/count, remediation SLAs, rollback drill and restore test recency
