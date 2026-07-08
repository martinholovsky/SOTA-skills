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
| **Kyverno** | YAML-native policy engine (validate/mutate/generate/verifyImages/cleanup). Current line ~v1.18 (verify). Runs as an admission webhook + controllers. | You want readable, K8s-native policies, image verification, resource generation, and don't want to write Rego. Most teams' default. |
| **Gatekeeper (OPA)** | OPA/Rego policies via ConstraintTemplates + Constraints. Current line ~v3.22 (verify). Webhook + audit controller; can also generate VAPs. | You already use Rego/OPA org-wide, or need very expressive logic. Heavier; Rego learning curve. |

Guidance: **use VAP for what it cleanly covers** (it's the lowest-risk, in-tree option),
and one of **Kyverno / Gatekeeper** for the rest (image verification, mutation, generation,
cross-resource logic). Don't run all three doing overlapping things. Whatever you pick:
policies live in git, are GitOps-deployed (`rules/04`), and have **CI-tested deny cases**
(kyverno CLI `kyverno test`, gatekeeper-library tests, VAP unit tests) so an "improvement"
can't silently stop blocking.

**Policy objects are an escalation primitive — never delegate their creation to tenants.**
Policies execute inside the engine's privileged pod: CVE-2026-4789 (CVSS 9.8, disclosed
2026-03) let any author of a Kyverno `NamespacedValidatingPolicy` use the CEL
`http.Get()`/`http.Post()` library to make arbitrary HTTP requests *from the Kyverno
admission-controller pod* — reaching cloud metadata (169.254.169.254) and internal
services, bypassing RBAC; it was one of a 2026 wave of Kyverno SSRF/apiCall advisories.
So: treat create/update on (namespaced) policy CRDs like `bind`/`escalate` (`rules/02`
§2.5); put an egress NetworkPolicy on policy-engine pods (block the metadata endpoint and
all unneeded egress); and confirm the running line includes the CVE-2026-4789 fix (merged
2026-04; patched releases per the project's security advisories).

```yaml
# Kyverno — require resource limits AND block :latest (PSA cannot do either)
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata: { name: workload-baseline }
spec:
  validationFailureAction: Enforce          # NOT Audit (see §3)
  background: true
  rules:
    - name: require-limits
      match: { any: [{ resources: { kinds: ["Pod"] } }] }
      validate:
        message: "containers must set cpu/memory limits"
        pattern:
          spec: { containers: [{ resources: { limits: { memory: "?*", cpu: "?*" } } }] }
    - name: disallow-latest
      match: { any: [{ resources: { kinds: ["Pod"] } }] }
      validate:
        message: ":latest tag is not allowed; pin a digest"
        pattern:
          spec: { containers: [{ image: "!*:latest" }] }
```

## 3. The AUDIT→ENFORCE rollout discipline (and the trap)

New policies break workloads if you enforce blind. The discipline:
1. **Deploy in audit/warn** (`validationFailureAction: Audit` / PSA `audit`+`warn`,
   Gatekeeper `enforcementAction: dryrun`).
2. **Watch the audit signal** — collect every would-be violation, fix the workloads (or
   add a *scoped* exception, §5).
3. **Flip to enforce** once the violation rate is zero/known. Then enforce stays on.

**The trap (a real, recurring audit finding):** policies left in **Audit/dryrun forever**.
Audit-only is not a control — it produces a dashboard nobody reads while violations sail
through. Treat "policy exists but never enforces" as **High**: the org believes it's
protected and isn't. For each Audit-mode policy, demand a flip-date and an owner, or
downgrade it to honest "we don't enforce this."

Hunt: `grep -rE 'validationFailureAction:\s*Audit|enforcementAction:\s*dryrun' policies/`
and `kubectl get ns -o json | jq '.items[].metadata.labels | select(.["pod-security.
kubernetes.io/enforce"]==null)'` (namespaces with warn/audit but no enforce).

## 4. Image verification at admission

Signing an image (cosign, `sota-devsecops` rules/02) does nothing unless **admission
verifies the signature and rejects unsigned/unattested images**. Use Kyverno `verifyImages`
or the sigstore **policy-controller**:

```yaml
# Kyverno verifyImages — Enforce, keyless, exact identity, mutate tag→digest
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata: { name: verify-signed-images }
spec:
  validationFailureAction: Enforce
  rules:
    - name: verify
      match: { any: [{ resources: { kinds: ["Pod"] } }] }
      verifyImages:
        - imageReferences: ["registry.example.com/*"]
          mutateDigest: true            # pin the verified digest into the spec
          required: true
          attestors:
            - entries:
                - keyless:
                    issuer: "https://token.actions.githubusercontent.com"
                    subject: "https://github.com/org/repo/.github/workflows/release.yml@refs/heads/main"
```

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
- [ ] Engine choice sane (VAP for simple validation; Kyverno/Gatekeeper for the rest; not three overlapping)? Version current/supported?
- [ ] Policy CRD writes (incl. Kyverno namespaced policies) never delegated to tenants; policy-engine pods behind an egress NetworkPolicy (metadata endpoint blocked); running line includes the CVE-2026-4789 fix?
- [ ] All security policies in `Enforce`, not parked in `Audit`/`dryrun` indefinitely? (`grep -rE 'Audit|dryrun' policies/`) Each Audit-mode policy has a flip-date + owner?
- [ ] Image verification ENFORCED for controlled registries: exact signer issuer+subject, provenance required, tag→digest mutation, full image inventory covered before enforce? (not Audit-only)
- [ ] Policies in git, GitOps-deployed, with CI-tested deny cases (`kyverno test` / gatekeeper tests / VAP units)?
- [ ] Exceptions scoped, owned, time-bound, PR-reviewed, inventoried, expiry-alerted? (`kubectl get polex -A`; list Gatekeeper excludedNamespaces)
- [ ] Mutating policies/webhooks reviewed for what they inject (a hostile mutation adds a sidecar/hostPath) — see `rules/05`?
