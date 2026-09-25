# 08 — Registry Security (the registry as a supply-chain trust anchor)

Scope: the container/artifact **registry itself** as infrastructure. rules/04 covers how the
image is built and pushed; rules/02 covers signing and provenance; this file covers the box
that holds them — who can write to it, who can read from it, what it guarantees about the
bytes it serves, and what happens when it is internet-exposed with auth turned off.

The registry is **tier-0**: every image the cluster runs flows through it. An
anonymously-writable registry is cluster-wide RCE — an attacker re-pushes a trusted tag, the
next rollout pulls it, and you are running their code with your service account. Admission-time
*enforcement* of what may be pulled (signature verify, registry allowlist, digest pinning) lives
in the **sota-kubernetes** skill; network exposure controls reference **sota-network-security**;
running the registry workload itself hardened references **sota-sandboxing**. This file is the
registry's own posture.

## 8.1 The trust-anchor model — why this is tier-0

- The registry sits on the critical path of every deploy. Compromise it and you do not need to
  compromise CI, source, or the cluster: you change what the cluster *pulls*. This is the same
  authority as repo-write or CI-secret theft, often with worse detection (no PR, no audit trail).
- Three things must hold for the registry to be a trust anchor, not a liability:
  1. **Only trusted writers can push** (no anonymous, no shared creds, CI-scoped identities).
  2. **What a consumer pulls is immutable and verifiable** (immutable tags, digest pinning,
     signatures that get *verified* — rules/02 produces them, sota-kubernetes enforces them).
  3. **The registry is available and recoverable** (tier-0 dependency; if it is down, you cannot
     deploy or scale, and if it is lost, you cannot reconstruct without source rebuilds).
- Audit framing: a registry that fails (1) is **Critical** (anonymous/shared push = artifact
  injection). Failing (2) is **High** (tag mutation, no verification). Failing (3) is **Medium**
  (availability/recovery), **High** if it is also the only copy of release artifacts.

## 8.2 AuthN/AuthZ — no anonymous write, least-privilege everything

**Rule: no anonymous push, ever. Usually no anonymous pull either.** Anonymous pull is
defensible only for a deliberate public-mirror registry on an isolated network path — never on
the same instance that holds private images.

The real finding (Zot, self-hosted): the registry ran with **anonymous push+pull on a
`hostNetwork` port** because the auth/accessControl mount was left **commented out**. That is
Critical: any pod on the node network (and anything that can reach the host port) can push a
`:prod` tag. The commented-mount pattern is the hunt — config that *looks* secured in the repo
but is disabled at deploy.

```json
// BAD — Zot with no auth, anonymous everything (the finding)
{
  "http": { "address": "0.0.0.0", "port": 5000 }
  // "accessControl": { ... }   <-- mount commented out; defaults to anonymous read+write
}
```

```json
// GOOD — Zot: authenticated, anonymous denied, per-repo least privilege
{
  "http": {
    "address": "127.0.0.1", "port": 5000,
    "tls": { "cert": "/etc/zot/tls/cert.pem", "key": "/etc/zot/tls/key.pem" },
    "auth": { "openid": { "providers": { "oidc": {
      "issuer": "https://idp.internal", "clientid": "zot", "scopes": ["openid","email"] } } } },
    "accessControl": {
      "repositories": {
        "team-a/**": {
          "anonymousPolicy": [],                         // no anonymous access
          "defaultPolicy": ["read"],                     // authed users: pull
          "policies": [
            { "users": ["ci-team-a"], "actions": ["read","create","update"] }  // CI may push
          ]
        }
      },
      "adminPolicy": { "users": ["registry-admin"], "actions": ["read","create","update","delete"] }
    }
  }
}
```

- **htpasswd is the floor, not the target.** Static basic-auth credentials get shared, copied
  into CI as one blob, and never rotated. Prefer **OIDC / bearer-token** auth, and **mTLS** where
  clients are machines you control. Zot v2 supports OIDC (incl. dex/GitHub/Google/GitLab), LDAP,
  bearer-token, and mTLS with identity extraction from the peer cert (verified, v2.1.x). Harbor
  authenticates humans via OIDC/LDAP and machines via **robot accounts**.
- **Separate push and pull identities.** Runtime nodes get a **pull-only** credential scoped to
  the namespaces they run; CI gets a **push** credential scoped per-repo. A single read-write
  cred shared by both means a leaked node kubelet secret can rewrite prod images.
- **Robot/CI accounts are per-repo and expiring.** Harbor robot accounts carry scoped actions +
  expiration; Zot policies scope `actions` per repo pattern to a CI user. Never grant a CI
  identity `delete` or admin. Map this to OIDC-federated CI where the registry trusts the CI
  provider's tokens (no stored registry password — cross-ref rules/01 / rules/02 for the OIDC
  publish pattern).
- **Humans do not push to release repos.** CI is the only writer to anything promoted; that is
  what makes provenance meaningful (rules/02). Human push to a `dev/**` sandbox is fine.

## 8.3 Image integrity & immutability — defeating tag mutation

The attack: a tag like `app:prod` or `app:v1.2.3` is a *pointer*. If the registry lets it be
re-pushed, an attacker (or a careless human) repoints it to a different manifest and every
subsequent pull gets new bytes. Signed-by-CI provenance is worthless if the consumer trusts the
mutable pointer instead of the digest.

- **Enable tag immutability** where the registry supports it:
  - **Harbor**: tag immutability rules — an immutable tag cannot be deleted, re-pushed,
    re-tagged, or overwritten by replication (verified, goharbor.io). Scope rules to release tag
    patterns.
  - **ECR**: per-repository `imageTagMutability: IMMUTABLE` — a second push of an existing tag is
    rejected (verified, AWS docs).
  - **GAR**: immutable-tags setting is GA for Docker repositories — locks the digest a tag points
    to (verified, Google docs).
  - **ACR**: there is **no registry-wide immutable-tag toggle**; immutability is achieved by
    *locking* an image/repo (`az acr repository update --write-enabled false`) per artifact —
    treat ACR tag-immutability as a manual/automated lock step, not a built-in policy (verify
    current; Microsoft has had this as an open feature request).
  - **Zot**: enforce immutability at the consumer (digest pinning) + retention/policy; Zot does
    not ship a Harbor-style immutable-tag rule engine — do not assume one.
- **Consumers pin by digest.** Deploy manifests reference `image@sha256:...`, not tags (this is
  the build-once-promote-many invariant from rules/04 §4.5 and is *enforced* at admission by
  sota-kubernetes). A digest is content-addressed: it cannot be mutated under you. Tags are for
  humans; digests are the identity.
- **Signature + attestation storage and verification.** rules/02 produces cosign signatures and
  in-toto attestations; the registry **stores** them. Modern registries use the **OCI 1.1
  Referrers API** (`subject` + `artifactType`) to associate signatures/SBOMs/scan results with an
  image by digest — verified GA-track: OCI image+distribution v1.1 released; ECR, Quay, JFrog,
  GAR-class registries support the Referrers API; cosign/oras query it. Confirm your registry
  serves `/v2/<name>/referrers/<digest>` (older registries fall back to the tag-schema workaround
  — verify, because a registry that silently drops referrers loses your attestations). The
  *verify-and-enforce* step (admission requires a valid signature by your release identity) is in
  sota-kubernetes; the registry's job is to durably keep the referrer artifacts next to the image.
- **Content-trust legacy**: Harbor's old Notary/DCT path is superseded by **cosign**-based
  signing; treat new Notary v1/DCT setups as deprecated and standardize on cosign (rules/02).

## 8.4 Vulnerability management at the registry

The registry is the natural place to scan *what you actually store* and to re-scan against new
advisories without rebuilding. This complements (does not replace) CI scan-on-build (rules/04
§4.4) and the dependency posture in rules/03/05.

- **Scan-on-push, block-on-critical.** Configure the registry (or an attached scanner) to scan
  every pushed manifest and quarantine/fail images over policy:
  - **Harbor**: built-in Trivy scanning + a **"Prevent vulnerable images from running"** project
    policy (block pull above a severity) — this is the registry refusing to *serve* a failing
    image, a control admission cannot give you for non-cluster pullers.
  - **ECR**: enhanced scanning via **Amazon Inspector** — scan-on-push **and continuous re-scan**
    as new CVEs publish, covering OS + language packages and distroless/Chainguard/scratch bases
    (verified, AWS). Basic scanning is Clair-based.
  - **GAR**: Artifact Analysis on-push + continuous scanning across OS and language ecosystems
    (verified, Google). **ACR**: Microsoft Defender for Cloud scans at the **manifest** level on
    push/import/recent-pull (verified) — note untagged manifests still alert.
  - **Zot**: integrates Trivy for scan results surfaced in the API/UI; for hard *block-on-pull*,
    pair with admission enforcement (sota-kubernetes) since Zot is OCI-native and minimal.
- **Continuous re-scan is the point.** An image clean at push is not clean forever — a CVE
  disclosed next week applies to images already stored. Registry-side continuous scanning catches
  the "old image, new advisory" gap that build-time scanning structurally cannot. Reference the
  scheduled deployed-digest scan in rules/04 §4.4 / rules/03 — the registry continuous scan and
  the cluster deployed-digest scan are complementary (registry = what you store, cluster = what
  you run).
- **Store SBOM + scan attestations** next to the image (OCI referrers, §8.3) so the scan result
  and bill of materials travel with the artifact and feed admission policy ("scanned within N
  days" — rules/02 §2.4).
- **Quarantine, do not silently serve.** A failing image should be unpullable for prod (Harbor
  prevent-vulnerable policy, or a `quarantine/**` repo that admission rejects) — not merely
  flagged in a dashboard nobody reads. A scan with no enforcement is Medium decorative control.

## 8.5 Supply-chain pull hygiene

What the registry *pulls from upstream* is as much an attack surface as what it serves.

- **Pull-through cache / proxy for upstream images.** Front Docker Hub / public registries with a
  caching proxy (Zot **sync** in on-demand/mirror mode; Harbor proxy-cache projects; ECR
  pull-through cache; ACR artifact cache; GAR remote repos — all verified-current). Wins:
  - defeats Docker Hub rate limits (a real outage cause when forty nodes pull directly);
  - one audited choke point and one place to patch/scan upstream images;
  - availability: upstream outage does not stop your deploys.
- **Dependency confusion at the image layer.** Internal namespaces must not be shadowable by
  public ones. If you pull `mycorp/base` and a proxy can resolve that from Docker Hub's
  `mycorp/base`, an attacker who registers the public name owns your base image. Pin internal
  images to **your** registry by full path + digest; never let a proxy silently fall through to
  public for internal-looking names. (Same class as package dependency-confusion in rules/03 §3.2,
  applied to images.)
- **Allowed-registries policy.** Workloads pull only from your registry / blessed mirrors. This
  is **enforced at admission** by **sota-kubernetes** (registry allowlist) — reference it; do not
  duplicate the policy here. The registry-side half is: make your registry the only one that has
  what prod needs, so the allowlist is enforceable without breaking deploys.
- **Verify what the proxy serves against the authoritative upstream.** A pull-through cache
  is a man-in-the-middle you operate: poisoned or compromised, it hands tampered bytes to
  every consumer. Keep verification end to end, against values that did **not** come from
  the proxy: lockfile hashes (rules/03 §3.1), image signatures and digests (rules/02 §2.3),
  and for Go the checksum database, which the module reference describes as "a Transparent
  Log (or 'Merkle Tree') of go.sum line hashes" (so never `GOSUMDB=off` behind a proxy).
  A scheduled job re-fetches a sample of cached artifacts from upstream and compares
  digests. (OWASP: SCVS 4.2)
- **Purge a version named in a malicious-package advisory.** The cache's immutability, the
  feature that survives an unpublish, also keeps a malicious version alive after the
  registry removes it. When a `MAL-` advisory (OSV, fed by the OpenSSF malicious-packages
  feed) names a version: delete it from the proxy cache, block it at the proxy so no
  resolve can fetch it again, and use the proxy's fetch log to find who already pulled it
  (rules/07 §7.3.1). (OWASP: DSOMM)
- **Mirroring / air-gap.** For air-gapped or sovereignty-constrained environments, mirror the
  full dependency closure (bases, sidecars, operators) into your registry and cut external pull
  paths entirely — the allowlist then has nowhere else to go.

## 8.6 Retention, GC & availability — without breaking running deploys

- **Tag retention + garbage collection.** Expire dev/PR images on a schedule; GC unreferenced
  blobs to reclaim storage. Harbor v2.15 added tag-deletion options in GC (verified-current).
- **Never GC a digest a running workload references.** Deploys pin digests (§8.3); a retention
  rule that deletes by tag-age can orphan a digest that prod still runs, and the next node that
  cold-pulls it gets `manifest unknown` → `ImagePullBackOff`. Retention must exclude:
  digests referenced by live deployments (query deployed digests — rules/02 §2.8 / rules/04 §4.3),
  release artifacts within your audit horizon, and their attestations/SBOMs.
- **Run GC against a consistent view.** GC + concurrent push race on some registries — run GC in
  the registry's supported maintenance mode (Harbor handles locking; Zot GC has documented
  settings) rather than ad-hoc blob deletion.
- **HA + backup — it is tier-0.** The registry must survive node loss (HA replicas, replicated or
  object-store backend) and be **restorable** (backup the metadata DB *and* blob store together;
  test the restore). A registry that is the single copy of your release artifacts with no tested
  restore is a High availability/recovery finding. Harbor replication (to another Harbor, Docker
  Hub, ECR/GAR/ACR, any OCI registry — verified) and Zot sync give you a warm second copy.

## 8.7 Network & deployment hardening of the registry

- **Never anonymous + internet-exposed.** This is a continuously-scanned exposure class:
  registries on `0.0.0.0:5000` with auth off are found and abused at internet scale. Bind to
  loopback/cluster-internal, put authn in front, and restrict reachability — network policy /
  segmentation lives in **sota-network-security**; reference it. Internet-exposed + anonymous =
  Critical.
- **No `hostNetwork` unless genuinely required.** The finding ran the registry on a `hostNetwork`
  port, which both exposed it broadly and bypassed namespace network policy. Run it as a normal
  pod with a `ClusterIP`/internal Service; placement and pod hardening are **sota-kubernetes**;
  workload isolation (drop caps, read-only rootfs, non-root) is **sota-sandboxing**.
- **TLS always.** Even internal: registry creds and bearer tokens cross the wire on every push;
  plaintext registry traffic is credential interception. Terminate TLS at the registry or a
  trusted mesh sidecar; do not rely on `--insecure-registry` in clients (it disables verification
  fleet-wide and normalizes MITM).
- **Treat the registry config as security-critical material.** The commented-out accessControl
  mount is the canonical failure. Render config from a reviewed source (GitOps), validate it on
  deploy (fail startup if `accessControl`/`auth` is absent in a non-public registry), and alert if
  the running config permits anonymous write.

## 8.8 Product notes (brief — verify current at use)

- **Zot** (latest stable — verify at github.com/project-zot/zot/releases): OCI-native, minimal,
  no DB. `accessControl` with `repositories`/`anonymousPolicy`/`defaultPolicy`/`policies`/
  `adminPolicy`; OIDC/LDAP/bearer/mTLS auth; workload-identity OIDC for secretless CI; **sync**
  for pull-through/mirror (incl. ECR upstream). It does **not** ship Harbor-style immutable-tag
  rules or block-on-pull scanning gates — get those from digest pinning + admission
  (sota-kubernetes). Verified against zotregistry.dev.
- **Harbor** (current **v2.15.x**, Mar 2026): projects + robot accounts + RBAC; **tag
  immutability rules**; built-in **Trivy** scan + prevent-vulnerable-from-running policy;
  **replication** to any OCI registry; cosign signing (Notary/DCT legacy). Heavier (Postgres,
  Redis, multiple services) — its HA/backup story is real work. Verified against goharbor.io.
- **Cloud registries** — IAM-scoped (no separate registry passwords), each with immutable tags +
  scan-on-push:
  - **ECR**: `IMMUTABLE` tags; Inspector enhanced scanning (on-push + continuous); managed image
    signing; pull-through cache. IAM/repo policies for access.
  - **GAR**: immutable-tags GA; Artifact Analysis scanning; IAM-scoped; remote/virtual repos.
  - **ACR**: image-lock for immutability (no registry-wide toggle — verify); Defender for Cloud
    scanning (manifest-level); artifact cache; RBAC/AAD.
  - **GHCR / Docker Hub**: GHCR ties access to the source repo (`image.source` label, rules/04
    §4.2.2) and supports OIDC-published provenance; Docker Hub's main risk is rate limits + the
    blast radius of being everyone's default upstream — front it with a pull-through cache (§8.5).

## Audit checklist

Hunt patterns in brackets.

- [ ] **No anonymous push**, and no anonymous pull on any instance holding private images
  [grep config for `anonymousPolicy` non-empty / missing auth; commented-out `accessControl`/auth
  mount; `0.0.0.0` bind with no `auth` block]
- [ ] Auth is OIDC/token/mTLS, not bare htpasswd; CI/robot accounts are **per-repo, expiring,
  non-admin**; push and pull identities are separate [shared read-write cred used by nodes and CI]
- [ ] Humans cannot push to release/promoted repos; CI is the sole writer there
- [ ] **Immutable tags** enabled where supported (Harbor rules / ECR `IMMUTABLE` / GAR setting /
  ACR lock); release tags are not re-pushable [try re-pushing an existing release tag in staging]
- [ ] Consumers **pin digests**, not tags (enforced at admission by sota-kubernetes)
  [`:latest` or bare mutable tags in deploy manifests]
- [ ] Signatures/SBOM/scan **attestations stored** with the image via OCI referrers, and a named
  verifier exists (rules/02 + sota-kubernetes) [signing present, zero verification]
- [ ] **Scan-on-push + continuous re-scan**; failing images quarantined/unpullable for prod, not
  just dashboarded [scanner enabled but no block/quarantine policy]
- [ ] Upstream pulls go through a **pull-through cache**; internal image names cannot fall through
  to public (image-layer dependency confusion); allowed-registries enforced (sota-kubernetes)
  [direct `docker.io/...` pulls in manifests; proxy fall-through for internal namespaces]
- [ ] **Proxy contents verified; malicious versions purged (§8.5), High:** clients verify hashes/signatures from sources other than the proxy (no `GOSUMDB=off`); for each cached package version, `curl -s -d '{"package":{"name":"<pkg>","ecosystem":"npm"},"version":"<ver>"}' https://api.osv.dev/v1/query | jq -r '.vulns[]?.id | select(startswith("MAL-"))'` prints nothing, and any hit is deleted and blocked at the proxy
- [ ] Retention/GC **excludes digests referenced by running workloads** + release artifacts +
  their attestations [tag-age GC with no live-digest exclusion → ImagePullBackOff risk]
- [ ] Registry is **HA + backed up + restore-tested**; treated as tier-0 [single copy of release
  artifacts, no tested restore]
- [ ] **Not internet-exposed while anonymous**; **TLS** on; no `--insecure-registry`; no
  `hostNetwork` unless required; reachability restricted (sota-network-security) and workload
  hardened (sota-sandboxing) [public IP + port 5000 + no auth; `hostNetwork: true`]
- [ ] Registry config rendered from reviewed source; startup **fails closed** if auth/accessControl
  is absent on a non-public registry [config drift between repo and running instance]
