# 03 — Admission Control & Policy-as-Code

Scope: the gate between "a manifest was submitted" and "the object exists in etcd." Pod
Security Admission, the policy engines (Kyverno, Gatekeeper/OPA, ValidatingAdmission
Policy/MutatingAdmissionPolicy), the AUDIT→ENFORCE rollout discipline, image verification
at admission, and PolicyException hygiene. **Pod-level securityContext/seccomp field
internals are `sota-sandboxing` (rules/03);** this file owns *enforcing them at admission*.
Image *signing/provenance production* is `sota-devsecops` (rules/02); this file owns
*verifying signatures at admission*.

Admission runs after authn/authz, on the object: **validating** webhooks/policies accept
or reject; **mutating** ones modify (inject sidecars, set defaults). Admission is where
policy becomes enforcement — RBAC says *who*, admission says *what's allowed to exist*.

---

## 1. Pod Security Admission (PSA) — the built-in floor

PSA is the in-tree replacement for the removed PodSecurityPolicy (PSA stable since K8s
v1.25; PSP gone since 1.25). It enforces the three **Pod Security Standards** by namespace
**label**, in three **modes**:

- **Standards**: `privileged` (no restrictions), `baseline` (blocks known escalations:
  hostNetwork/PID/IPC, privileged, hostPath, most added caps), `restricted` (hardened:
  non-root, no privilege escalation, seccomp RuntimeDefault, drop ALL caps, etc.).
- **Modes**: `enforce` (reject), `audit` (allow + audit-log annotation), `warn` (allow +
  client warning). You can set all three independently and pin a `-version`.

```yaml
# GOOD — enforce restricted; audit/warn at the same level catch drift in subresources
apiVersion: v1
kind: Namespace
metadata:
  name: payments
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: latest   # or pin to your minor
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

**Enforce `restricted` on workload namespaces.** `baseline` is a transitional floor, not a
destination. **PSA's limits** (this is why you also need an engine, §2):
- PSA is **per-namespace and standard-only** — it cannot express "images must come from
  our registry," "no `:latest` tag," "every pod has resource limits," or "the SA isn't
  `default`." It only checks the built-in pod-security fields.
- It does **not mutate** — it won't add a missing `securityContext`, only reject.
- Privileged-namespace exemptions (kube-system, some operators) are broad. Don't let a
  workload land in an exempt/privileged namespace to dodge PSA.

The *meaning* of `runAsNonRoot`, `seccompProfile`, capability drops → `sota-sandboxing`.

## 2. Policy engines — choosing one

You need a general engine for everything PSA can't express. The 2026 options:

| Option | What it is | Use when |
|---|---|---|
| **ValidatingAdmissionPolicy (VAP)** | In-tree, CEL-based validating policies. GA since K8s **v1.30**. No external webhook/pod — runs in the API server. | The check is *validation only* and expressible in CEL. Lowest operational risk (no webhook to fail, no extra pod). Prefer for simple invariants. |
| **MutatingAdmissionPolicy (MAP)** | In-tree, CEL-based *mutating* policies. GA in K8s **v1.36** (beta 1.34, feature-gated). | Mutation you'd otherwise run a mutating webhook for, once you're on a GA-supporting version. Verify your cluster's version before relying on it. |
| **Kyverno** | K8s-native policy engine: CEL-based `policies.kyverno.io/v1` types (`ValidatingPolicy`, `ImageValidatingPolicy`, `MutatingPolicy`, `GeneratingPolicy`, `DeletingPolicy`; v1 API since 1.17, docs list it stable since 1.18). The legacy `kyverno.io/v1` `ClusterPolicy`/`Policy` (JMESPath) is deprecated (marked 1.17, officially deprecated in 1.19, the last line with full support); per the tracking issue kyverno#17214, 1.20 hard-errors on creating or changing a legacy policy (stored ones are still enforced; the Helm chart blocks the upgrade while legacy CRs exist) and full removal follows — verify at kyverno.io/docs/policy-types/overview. Verify the latest release at github.com/kyverno/kyverno/releases. Runs as an admission webhook + controllers. | You want readable, K8s-native policies, image verification, resource generation, and don't want to write Rego. Most teams' default. |
| **Gatekeeper (OPA)** | OPA/Rego policies via ConstraintTemplates + Constraints. Verify the latest release at github.com/open-policy-agent/gatekeeper/releases. Webhook + audit controller; can also generate VAPs. | You already use Rego/OPA org-wide, or need very expressive logic. Heavier; Rego learning curve. |

Guidance: **use VAP for what it cleanly covers** (it's the lowest-risk, in-tree option),
and one of **Kyverno / Gatekeeper** for the rest (image verification, mutation, generation,
cross-resource logic). Don't run all three doing overlapping things. Whatever you pick:
policies live in git, are GitOps-deployed (`rules/04`), and have **CI-tested deny cases**
(kyverno CLI `kyverno test`, gatekeeper-library tests, VAP unit tests) so an "improvement"
can't silently stop blocking.

**Policy objects are an escalation primitive — never delegate their creation to tenants.**
Policies execute inside the engine's privileged pod: CVE-2026-4789 (GHSA-rggm-jjmc-3394,
CVSS 8.5 per the GHSA; the CISA-ADP entry scores it 9.8; GHSA published 2026-04) let any
author of a Kyverno `NamespacedValidatingPolicy` use the CEL `http.Get()`/`http.Post()` library to make arbitrary HTTP requests *from the Kyverno
admission-controller pod* — reaching cloud metadata (169.254.169.254) and internal
services, bypassing RBAC (the GHSA lists 1.16.4 as patched). It was one of a 2026 wave of Kyverno
SSRF/apiCall/namespace-escape advisories that kept coming: CVE-2026-54523 (CVSS 9.6, fixed in
1.18.2), then five advisories published 2026-09-10 — among them GHSA-5qq8-67g6-4h2w
(cluster-admin via policy `apiCall` `urlPath`, CVSS 9.9) and GHSA-5cjf-wwfg-pj4c (an
`ImageValidatingPolicy` exception ignores its image scope, so it bypasses signature
verification) — whose only fixed version is **1.19.1**. The practical floor is therefore
**Kyverno >= 1.19.1** (as of 2026-09-26; re-check github.com/kyverno/kyverno/security/advisories
before citing it). So: treat create/update on (namespaced) policy CRDs like `bind`/`escalate`
(`rules/02` §2.2); put an egress NetworkPolicy on policy-engine pods (block the metadata
endpoint and all unneeded egress); and run a line that carries the fix for *every* published
advisory, not just CVE-2026-4789.

```yaml
# Kyverno ValidatingPolicy — require resource limits AND block :latest (PSA cannot do either)
apiVersion: policies.kyverno.io/v1
kind: ValidatingPolicy
metadata: { name: workload-baseline }
spec:
  validationActions: [Deny]                 # NOT [Audit] (see §3)
  autogen:                                  # also emit the rule for pod controllers
    podControllers: { controllers: [deployments, statefulsets, daemonsets, jobs, cronjobs] }
  matchConstraints:
    resourceRules:
      - { apiGroups: [""], apiVersions: [v1], operations: [CREATE, UPDATE], resources: [pods] }
  validations:
    - message: "containers must set cpu/memory limits"
      expression: >-
        object.spec.containers.all(c, has(c.resources) && has(c.resources.limits) &&
        'cpu' in c.resources.limits && 'memory' in c.resources.limits)
    - message: ":latest tag is not allowed; pin a digest"
      expression: >-
        object.spec.containers.all(c, !c.image.endsWith(':latest'))
```

(Checked 2026-09-26 against the v1.19.1 CRD schema and with `kyverno apply` on a compliant
Pod, a limit-less Pod, a `:latest` Pod and a Deployment: 1 pass, 3 fail as intended.)

## 3. The AUDIT→ENFORCE rollout discipline (and the trap)

New policies break workloads if you enforce blind. The discipline:
1. **Deploy in audit/warn** (Kyverno CEL policies and VAP bindings `validationActions:
   [Audit]` or `[Warn, Audit]`; legacy Kyverno per-rule `failureAction: Audit`; PSA
   `audit`+`warn`; Gatekeeper `enforcementAction: dryrun` or `warn`).
2. **Watch the audit signal** — collect every would-be violation, fix the workloads (or
   add a *scoped* exception, §5).
3. **Flip to enforce** once the violation rate is zero/known (`validationActions: [Deny]`,
   `failureAction: Enforce`, `enforcementAction: deny`). Then enforce stays on.

**The trap (a real, recurring audit finding):** policies left in **Audit/dryrun forever**.
Audit-only is not a control — it produces a dashboard nobody reads while violations sail
through. Treat "policy exists but never enforces" as **High**: the org believes it's
protected and isn't. For each Audit-mode policy, demand a flip-date and an owner, or
downgrade it to honest "we don't enforce this."

Hunt: `grep -rE '(validationFailureAction|failureAction):[[:space:]]*Audit|enforcementAction:[[:space:]]*(dryrun|warn)|validationActions:[[:space:]]*\[[^]D]*\]' policies/`
— legacy Kyverno (spec-level and per-rule), Gatekeeper `dryrun`/`warn`, and any flow-style
`validationActions` list without `Deny` (Kyverno CEL policies, VAP bindings; `[Deny, Audit]`
enforces and is not a hit). A block-style list escapes it, so also read
`grep -rnA2 'validationActions:[[:space:]]*$' policies/` (checked 2026-09-26 on BSD grep, GNU
grep and ugrep: 7/7 flow-style positives, 0/4 enforcing negatives). Then
`kubectl get ns -o json | jq -r '.items[] | select(.metadata.labels["pod-security.kubernetes.io/enforce"] == null) | .metadata.name'`
lists namespaces with no PSA `enforce` label.

## 4. Image verification at admission

Signing an image (cosign, `sota-devsecops` rules/02) does nothing unless **admission
verifies the signature and rejects unsigned/unattested images**. Use a Kyverno
`ImageValidatingPolicy` (the successor of the deprecated `ClusterPolicy` `verifyImages` rule)
or the sigstore **policy-controller**:

```yaml
# Kyverno ImageValidatingPolicy — Deny, keyless, exact identity, mutate tag→digest
apiVersion: policies.kyverno.io/v1
kind: ImageValidatingPolicy
metadata: { name: verify-signed-images }
spec:
  validationActions: [Deny]
  failurePolicy: Fail                     # a verification error rejects, never admits
  matchConstraints:
    resourceRules:
      - { apiGroups: [""], apiVersions: [v1], operations: [CREATE, UPDATE], resources: [pods] }
  matchImageReferences:
    - glob: "registry.example.com/*"
  validationConfigurations:
    mutateDigest: true                    # pin the verified digest into the spec
    verifyDigest: true
    required: true
  attestors:
    - name: ci
      cosign:
        keyless:
          identities:
            # exact match: `*` in `subject` is a literal character, not a wildcard;
            # for a pattern use `subjectRegExp`, anchored (^...$) — it is an unanchored search
            - issuer: "https://token.actions.githubusercontent.com"
              subject: "https://github.com/org/repo/.github/workflows/release.yml@refs/heads/main"
        ctlog: { url: "https://rekor.sigstore.dev" }
  validations:
    - expression: >-
        images.containers.map(image, verifyImageSignatures(image, [attestors.ci])).all(e, e > 0)
      message: "image must be signed by org/repo's release workflow"
```

(Checked 2026-09-26 with `kyverno apply` against a keyless-signed public test image: the exact
`subject` passed; the same policy with `@refs/heads/*` as `subject` rejected it, confirming the
literal match — cosign compares `subject` with `==` and `subjectRegExp` with an unanchored
`MatchString`. `kyverno apply` does not mutate, so feed it a digest-pinned image.)

Traps:
- **"Signing exists but admission only Audits it."** Same as §3 — unsigned images still
  run. High. Enforce, or it's theater.
- **Prereq ordering**: enforce *can block scheduling* if your build/sign path isn't
  complete for every in-use image (base images, third-party charts, kube-system). Inventory
  what's deployed, get everything signed/allowlisted, *then* enforce — or you'll wedge the
  cluster. Scope `imageReferences` to registries you control and allowlist the rest
  explicitly (with expiry) rather than disabling enforcement.
- Verify the exact **issuer + subject identity**, not just "a signature exists" — an
  attacker's valid signature from their own identity passes a check that doesn't pin who.
- Require **provenance attestations** (SLSA) too, not only signatures, for high-value
  workloads (`sota-devsecops` rules/02).
- **A valid signature does not mean an approved base.** A team can sign an image built
  on anything. Where the org keeps a blessed base set (`sota-devsecops` rules/04 §4.3),
  admission also checks the image's signed provenance: BuildKit's SLSA provenance lists
  every image the build pulled, by digest, in `buildDefinition.resolvedDependencies` as
  `pkg:docker/...` entries, so a Kyverno attestation check can require all of them to
  be approved digests. Guard the empty case, since `all()` (or legacy `AllIn`) over an empty
  list passes. The
  `org.opencontainers.image.base.name`/`.digest` annotations are typed by whoever runs the
  build, so they are no substitute. Admission sees only new pods, so also run a scheduled
  job that takes every running image digest (`kubectl get pods -A -o
  jsonpath='{..imageID}'`), fetches its provenance (`cosign verify-attestation --type
  slsaprovenance1 ...`) and flags any base outside the approved set, such as an image
  admitted before the policy existed or one whose base has since been withdrawn.
  OWASP: DSOMM; Kubernetes Security cheat sheet.

```yaml
# ImageValidatingPolicy spec additions (same attestor `ci` as above) — every image the
# build pulled is an approved base. extractPayload() returns the whole in-toto
# Statement, hence `.predicate.` ; the exists() guard is there because all() over an
# empty list is true.
  variables:
    - name: approvedBases                 # sha256 digests of the blessed base images
      expression: "['<approved-base-digest-1>', '<approved-base-digest-2>']"
  attestations:
    - name: slsa
      intoto: { type: "https://slsa.dev/provenance/v1" }
  validations:
    - expression: >-
        images.containers.map(image, verifyAttestationSignatures(image, attestations.slsa, [attestors.ci])).all(e, e > 0)
      message: "image has no SLSA provenance signed by the CI identity"
    - expression: >-
        images.containers.all(image, extractPayload(image, attestations.slsa).predicate.buildDefinition.resolvedDependencies.exists(d, d.uri.startsWith('pkg:docker/')))
      message: "provenance lists no base image"
    - expression: >-
        images.containers.all(image, extractPayload(image, attestations.slsa).predicate.buildDefinition.resolvedDependencies.filter(d, d.uri.startsWith('pkg:docker/')).all(d, d.digest.sha256 in variables.approvedBases))
      message: "image was built on a base outside the approved set"
```

(Checked 2026-09-26: a real keyless-attested image whose provenance lists only a git
dependency is rejected by the empty-list guard; the digest logic, run as a JSON-mode
`ValidatingPolicy` over mock Statements, passes an approved base and rejects an unapproved
one and an empty list.)

## 5. PolicyException / exemption discipline

Every engine has an escape hatch (Kyverno `PolicyException`, Gatekeeper Constraint
`excludedNamespaces`/`match`, VAP `matchConditions`, PSA namespace exemptions). Without
discipline these become permanent holes:
- **Scoped**: exact namespace + resource + rule, never cluster-wide "skip this policy."
- **Owned and time-bound**: an owner annotation and an expiry; CI/cron fails or alerts on
  expired exceptions.
- **PR-reviewed and inventoried**: exceptions live in git, are reviewed like code, and a
  query lists all live ones. An untracked, unexpiring exception is how "we enforce
  restricted" quietly becomes "except in these 30 namespaces."

## Audit checklist

- [ ] PSA `enforce: restricted` (or justified `baseline`) on every workload namespace, not just `warn`/`audit`? (`kubectl get ns -L pod-security.kubernetes.io/enforce`)
- [ ] No workloads parked in privileged/exempt namespaces (kube-system, operator ns) to dodge PSA?
- [ ] A policy engine covers what PSA can't (registry allowlist, no `:latest`, required limits, non-default SA, host-path/host-namespace bans)?
- [ ] Engine choice sane (VAP for simple validation; Kyverno/Gatekeeper for the rest; not three overlapping)? Version current/supported? Kyverno policies on the `policies.kyverno.io` CEL types, not legacy `kyverno.io/v1` `ClusterPolicy`/`Policy` (deprecated; 1.20 rejects new or changed ones — `grep -rnE '^apiVersion:[[:space:]]*kyverno\.io/' policies/`, each hit except a `GlobalContextEntry` is a legacy policy or exception to migrate)?
- [ ] Policy CRD writes (incl. Kyverno namespaced policies) never delegated to tenants; policy-engine pods behind an egress NetworkPolicy (metadata endpoint blocked); running line carries the fix for every published Kyverno advisory (>= 1.19.1 as of 2026-09-26)?
- [ ] All security policies in `Enforce`, not parked in `Audit`/`dryrun` indefinitely? (the §3 hunt — a bare `grep -rE 'Audit|dryrun'` misses Gatekeeper `warn` and a `[Warn]`-only binding) Each Audit-mode policy has a flip-date + owner?
- [ ] Image verification ENFORCED for controlled registries: exact signer issuer+subject, provenance required, tag→digest mutation, full image inventory covered before enforce? (not Audit-only)
- [ ] Where an approved base set exists: admission requires signed provenance whose `pkg:docker/` dependencies are all approved digests (empty list rejected), and a scheduled job re-checks every running image's base? **Medium** if base approval rests only on a signature or on the self-declared base annotation. (`grep -rnE 'org\.opencontainers\.image\.base\.(name|digest)' <policies>` — each hit is a policy trusting a build-typed label; `grep -rnE 'resolvedDependencies' <policies>` — no hit means provenance bases are never checked)
- [ ] Policies in git, GitOps-deployed, with CI-tested deny cases (`kyverno test` / gatekeeper tests / VAP units)?
- [ ] Exceptions scoped, owned, time-bound, PR-reviewed, inventoried, expiry-alerted? (`kubectl get policyexceptions.policies.kyverno.io -A` for the CEL types; `polex` is the short name of the legacy `kyverno.io` kind only; list Gatekeeper excludedNamespaces)
- [ ] Mutating policies/webhooks reviewed for what they inject (a hostile mutation adds a sidecar/hostPath) — see `rules/05`?
