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
| A version of your own package published with no matching tag/CI run, or from an unusual identity or time | Stolen publish token — the worm pattern |
| Registry token used from an unexpected IP, or a new token created | Credential theft staging a publish |
| Unexpected dependency added in your own released package | Tampered release, even when the publish path looked normal |
| A CI secret value revealed or exported through the platform UI or API, where the platform allows it (GitLab can reveal a variable not created as "Masked and hidden") | A person reading a production secret outside any pipeline |
| Job output containing `U2FsdGVkX1` (base64 of openssl's `Salted__` header) or long base64 blobs, or a workflow change adding `base64 \| base64` or `openssl enc` | Encoding defeats value-match masking (rules/01 §1.10); double base64 and openssl-encrypted output are how a secret is printed past it |

Each detection needs an owner and a tested response path; a detection nobody drills is a
dashboard widget.

Keep a **pipeline and publisher-compromise playbook** with named roles and an escalation
path. It covers revoking every CI, registry and cloud token the pipeline held
(`npm token revoke`, `rules/01` §1.10); marking bad versions with `npm deprecate` (or the
registry's equivalent), and unpublishing where the registry's policy allows; and notifying
consumers through an advisory. (OWASP: GitHub Actions Security cheat sheet; NPM Security
cheat sheet)

### 7.3.2 Containment for a trusted dependency that turns malicious

Every control before runtime (rules/03, rules/15) can pass a dependency that was clean
yesterday and ships a payload today. Assume that will happen, and decide in advance what the
payload can reach. Four layers bound it, and each limits something different:

| Layer | What it limits |
|---|---|
| **Workload identity**: a per-service identity with short-lived, narrowly scoped credentials (`sota-identity-access`, `sota-secrets-management`) | What there is to steal: the workload's own expiring credentials, not a shared long-lived key |
| **Egress restriction**: default-deny egress with destination allowlists (`sota-network-security`) | Exfiltration and second-stage downloads: the payload cannot reach its command server or upload data |
| **Segmentation**: namespace or network default-deny between services | Lateral movement: the compromised service reaches only what it already calls |
| **Runtime detection**: process, file and network rules (`sota-detection-engineering`) | Time to notice: a shell spawned by an application process, a new outbound destination, reads of credential files |

Build jobs get the same treatment (rules/01 §1.6: ephemeral runners, egress control). The
audit question: pick one dependency of a production service and ask what it could reach if
it ran attacker code at startup. The answer should come from these four layers, not from
trust in the maintainer. (OWASP: Zero Trust Architecture cheat sheet)

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
  (`rules/09` §1 — that's not break-glass, that's no glass).

## 7.6 Closing the loop

Runtime signals feed back into the pipeline: admission denials reveal unsigned/legacy
images to migrate; drift corrections reveal process gaps; scanner findings on *deployed*
digests (rules/03 §3.6) drive rebuild-and-promote of patched bases (rules/04 §4.3);
incident retros add Opengrep rules (rules/05 §5.1) and admission policies. A DevSecOps
setup that only adds controls and never tunes them ends as the bypassed, resented variety.
Track: gate latency, exception/suppression counts and ages, time-to-remediate by severity,
rollback drill recency, restore test results. Those five trends are the honest health
dashboard of everything in this skill.

**Security defect metrics**, reported on a fixed schedule and reviewed for quick wins:

- open vulnerabilities by severity, split by layer (application or infrastructure) and by
  component;
- fix rate against SLA, per team or repository (rules/13 §13.3 sets the SLA);
- time from a patch being available to it running in production, measured from the
  advisory's fix date to the deploy event of rules/02 §2.8, not to the merge;
- recurrence by defect class: the same class coming back in the same codebase means a
  missing rule, test or guardrail rather than a missing fix.
  (OWASP: DSOMM; SAMM)

## 7.7 Cleanup on a shared runtime is a change, not housekeeping

`prune`, `fstrim` and their friends read as tidying and are treated as safe by default. They
are neither: they mutate state that other things hold open, and the damage surfaces later,
somewhere else, wearing a different failure's clothes.

Field-reported: `podman image prune -a` + `volume prune` + `fstrim` on a dev VM corrupted the
container runtime's overlay storage. Every `podman run` then failed with `input/output
error` **on a VM with 62 GB free inside** — and the runtime went on looking healthy, because
images still pulled and `podman ps` still reported running containers fine. Only something
needing a *new* container failed. Downstream, a test file went from 3 passed to 1 passed /
2 failed, and **a harness that cannot start is indistinguishable from a harness that ran and
found nothing** — the second reading being a conclusion about the target
(`sota-testing` rules/04 §4.8).

- **Treat prune/trim as a change requiring a restart and a post-change smoke test**, not as
  maintenance. Restart the runtime, then start one throwaway container and assert it
  produced output. "Still running" is not "still able to start".
- **Enumerate foreign-owned resources before pruning shared infrastructure.** A `container
  prune` removes *another project's* stopped database container, which moves its anonymous
  volume into the dangling set for the next `volume prune` to delete. The check that makes
  it safe is listing dangling volumes and confirming **none are named** — a named volume is
  one somebody chose to keep.
- **On a machine you share with other work, prune is a coordination problem.** The blast
  radius is every project on the host, and nothing in the command says so.
- **"Reclaimable" is the tool's definition of unused, not yours.** `podman system df` counts
  an image as reclaimable when no *container* references it (Docker's docs do not define
  the column at all), so every build-only
  image and pinned toolchain reads as garbage (`sota-shell-scripting` rules/09 §5a).
  Field-reported: 22 GB "reclaimable (93%)", where `image prune -a` would have deleted the
  toolchain images three CI gates build from, and the narrow `image prune` correctly freed
  0 bytes. **Prefer the narrow command, whose failure mode is freeing nothing.**
- **Pruning a cached image whose tag moves is a version bump, not a cleanup.** `podman build`
  pulls a base image only when it is missing (`--pull` defaults to `missing`), so the cache
  was the only thing holding a `FROM …:rawhide`/`:latest`/bare-major image still. Remove it
  and the next build compiles against whatever the tag points at today. In the field case,
  that was a toolchain whose LLVM version mismatch segfaulted the linker rather than
  reporting anything. Before removing a base image, check whether any Containerfile names it
  by a moving tag.
- The capacity side of the same coin — *check headroom before a command that writes at
  scale* — is `sota-shell-scripting` rules/08 §3.

## Audit checklist

- [ ] Admission enforces (not audits) image verification in prod: exact signer identity + issuer, provenance attestation required, registry allowlist, tag→digest mutation, `failurePolicy: Fail`, all Pod-paths covered; Kyverno policies on the CEL v1 types (ClusterPolicy deprecated since 1.17, removal planned v1.20)
- [ ] Baseline workload policies enforced: PSA restricted-equivalent, no `:latest`, non-root, resource limits, attribution labels
- [ ] Policies in git, GitOps-deployed, with CI-tested deny cases; exceptions are scoped, owned, time-bound, PR-reviewed, and inventoried
- [ ] CI/CD, deploy, admission, registry, and control-plane audit events stream to tamper-resistant storage with ≥1y retention; pipeline identities are alertable principals
- [ ] Deploy traceability: digest → source SHA → run → approver queryable in seconds; deploy markers in observability
- [ ] High-signal alerts wired: release-workflow modification, runner registration, policy change, unsigned-image attempt, break-glass use, push-protection bypass
- [ ] **Own-package publishes reconciled (§7.3.1), High:** `comm -13 <(git tag -l 'v*' | sed 's/^v//' | sort) <(npm view <pkg> versions --json | jq -r 'if type=="array" then .[] else . end' | sort)` prints nothing (any output is a version published without a release tag); a publisher-compromise playbook names owners and covers revoke, deprecate/unpublish, and consumer notice
- [ ] **Secret-exfiltration detections wired (§7.3.1), Medium:** `grep -rn -E 'base64[^|]*\|[[:space:]]*base64([[:space:]]|$)|openssl[[:space:]]+(enc|aes-[0-9]+|des)' .github/workflows` is empty or each hit is reviewed; job logs are searched for `U2FsdGVkX1`; UI reveal or export of CI variables alerts where the platform logs it
- [ ] **Containment layers exist for a malicious dependency (§7.3.2), High:** `kubectl get networkpolicy -A -o json | jq -r '.items[] | select(.spec.podSelector == {} and ((.spec.policyTypes // []) | index("Egress")) and ((.spec.egress // []) | length == 0)) | .metadata.namespace' | sort -u` lists every production namespace (default-deny egress); workloads use per-service identities; runtime detection covers process and outbound-connection anomalies
- [ ] **Security defect metrics reported (§7.6), Low:** open vulnerabilities by severity, layer and component; fix rate against SLA per team; patch-available-to-production time; recurrence by class, reviewed on a schedule
- [ ] Backup inventory covers state/registry/git/secrets/keys; restores tested on schedule against RPO/RTO; backups immutable, in a separate trust domain, not deletable by prod-compromising credentials
- [ ] Break-glass documented per gate, alarmed on use, time-bound, post-reviewed, reconciled to git; routine admin bypass absent
- [ ] Feedback loop metrics tracked: gate latency, exception age/count, remediation SLAs, rollback drill and restore test recency
- [ ] **Is prune/trim on a shared runtime treated as a change?** (§7.7) Restart plus a
      post-change smoke test that *starts* something, foreign-owned resources enumerated
      first, and dangling volumes confirmed unnamed before deletion.
- [ ] **Would a prune change what the next build compiles against?** (§7.7) Any
      `FROM` on a moving tag (`latest`, `rawhide`, `stable`, a bare major) is pinned only by
      the cache the prune deletes. And is the narrow command (`image prune`) used rather than
      `-a`, with "reclaimable" not read as "unused by us"?

