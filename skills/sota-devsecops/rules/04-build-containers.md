# 04 — Build Integrity & Containers (hermetic builds, Dockerfiles, base images, registries)

Scope: the transformation from source to artifact. Goal: the build is a pure function of
committed inputs (hermetic, ideally reproducible), the artifact carries nothing it doesn't
need (minimal runtime), and the registry preserves integrity (digests, immutability).

## 4.1 Hermetic & reproducible builds

**Hermetic** (no undeclared inputs) is the security property; **reproducible** (bit-
identical output from same inputs) is the verification property. Pursue hermetic always,
reproducible where the payoff justifies it (SLSA verification, multi-party trust).

- All network fetches during build go through lockfile/hash-verified channels (rules/03
  §3.1) or a proxy with an allowlist. A build step that `curl`s an unpinned URL is an
  unreviewable input — every such fetch is a finding (High if it pipes to sh).

```dockerfile
# BAD — unpinned remote code execution as a build step
RUN curl -sSL https://install.example.com/tool.sh | sh

# GOOD — pinned download, verified
RUN curl -fsSLo /tmp/tool.tgz https://releases.example.com/tool-1.4.2-linux-amd64.tgz \
 && echo "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08  /tmp/tool.tgz" | sha256sum -c - \
 && tar -xzf /tmp/tool.tgz -C /usr/local/bin
```

- Pin the toolchain: compiler/SDK versions come from a pinned builder image or
  `.tool-versions`/`mise`/Nix — "whatever is on the runner" is an undeclared input.
- Build does not read the environment beyond declared args: no `ENV`-dependent branches,
  no time-dependent codegen. For reproducibility: set `SOURCE_DATE_EPOCH` (most
  toolchains and BuildKit honor it for timestamps), stable archive ordering
  (`tar --sort=name --mtime=...`), `-trimpath` for Go, deterministic zip for Java.
- Build and test in CI from a clean checkout only — artifacts built on laptops never get
  promoted (no provenance, no hermeticity, SLSA L0).
- Verify reproducibility where you claim it: a scheduled job rebuilds a recent release
  from the same SHA and diffs digests (`diffoscope` for the failure analysis). A
  reproducibility claim that is never re-derived is marketing; one independent rebuild
  per release window turns provenance from "trust the builder" into "check the builder".
- **Third-party binaries and tools arrive through a package manager or artifact repository**,
  where they are locked, scanned and logged (rules/03 §3.3). The hash-pinned download in the
  GOOD example is a documented exception with an owner, not the default path. **A binary
  committed to the repository is never acceptable**: it cannot be reviewed or rebuilt, and
  OpenSSF Scorecard's `Binary-Artifacts` check flags it.
- **Local, tarball and cache installs are verified too.** A package installed from a local
  path, a `.tgz`, a wheel file or a restored cache skips the registry's integrity path
  unless a recorded hash is checked. `pip install --require-hashes` refused a local wheel
  listed without a hash (measured, pip 26.1.2). A CI cache restore is matched on its key,
  which is a name you chose, not a hash of the content, so never restore dependencies from a
  cache without re-verifying them against the lockfile (rules/01 §1.6).
- **CI executes only the reviewed build definition.** No step runs code fetched or generated
  outside it: no `curl | sh`, no `eval "$(curl …)"`, no script whose URL comes from a
  variable. zizmor's `adhoc-packages` audit (v1.26.0+) flags `run:` steps that install
  packages outside a locked manifest. (OWASP: SCVS 1.2, 3.6, 4.1, 4.14)
- **Keep user-controllable build inputs to a small, typed allowlist.** SLSA provenance calls
  them `externalParameters` and asks build platforms to "minimize the size and complexity"
  of them, and verifiers to reject unexpected ones. On GitHub, prefer `workflow_dispatch`
  inputs of type `boolean`, `choice`, `number` or `environment`; an input of `type: string`
  (or with no type) that reaches a build command is free-text control over the build.
- **Build steps do not reconfigure name resolution or the network path.** No writes to
  `/etc/hosts` or `/etc/resolv.conf`, no `--add-host` (a `docker`/`podman`/`buildx build`
  flag; `add-hosts:` on the build-push action), no proxy variables (`HTTPS_PROXY`,
  `https_proxy`, `NO_PROXY`) set mid-job: each can silently send a hash-pinned fetch
  somewhere else, and only the hash check stands in the way. Put the proxy in the runner
  image, reviewed. (OWASP: Software Supply Chain Security cheat sheet; SCVS 3.8)
- Build tooling is a dependency too: pin BuildKit/buildx, syft/grype/cosign versions in
  CI (via pinned action SHAs or pinned tool downloads with checksums) — an unpinned
  `latest` scanner can silently change gate behavior, and a compromised tool download is
  arbitrary code in the build (this is rules/03 applied to the pipeline itself).

## 4.2 Multi-stage Dockerfiles

**Rule: build tools, source, and secrets never appear in the runtime image.** Multi-stage
is the mechanism; the final stage copies artifacts only.

```dockerfile
# GOOD
# syntax=docker/dockerfile:1.7
FROM golang:1.23.4-bookworm@sha256:<digest> AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN --mount=type=cache,target=/go/pkg/mod go mod download && go mod verify
COPY . .
RUN --mount=type=cache,target=/root/.cache/go-build \
    CGO_ENABLED=0 go build -trimpath -ldflags="-s -w -X main.commit=${GIT_SHA}" -o /out/app ./cmd/app

FROM gcr.io/distroless/static-debian13:nonroot@sha256:<digest>
COPY --from=build /out/app /app
USER nonroot:nonroot
ENTRYPOINT ["/app"]
```

```dockerfile
# BAD — single stage: toolchain + source + git history shipped to prod, runs as root
FROM golang:latest
COPY . .
RUN go build -o app . && chmod 777 app
CMD ./app
```

Hard rules:
- **`USER` non-root** in the final stage (numeric UID for k8s `runAsNonRoot` checks, or
  distroless `:nonroot`). Root-in-container is one kernel bug or hostPath mistake from
  root-on-node.
- **Secrets via BuildKit secret mounts only**: `RUN --mount=type=secret,id=netrc ...`.
  NEVER `ARG TOKEN` / `ENV TOKEN` / `COPY .npmrc` — build args land in image history
  (`docker history`), copied-then-deleted files persist in the layer. Any credential in an
  ARG/ENV/layer = High (Critical if the image is in a shared registry).
- **`.dockerignore`** excluding `.git`, `.env*`, secrets, local configs, `node_modules` —
  `COPY . .` without it ships your git history and whatever junk is on the build machine.
- Order for cache correctness: manifests + frozen install first, then source. Never let a
  cache mount cross trust boundaries (rules/01 §1.6).
- No `apt-get upgrade` at build (unreproducible drift) — get fixes by bumping the base
  digest instead. `apt-get install` with `--no-install-recommends` and version pins where
  the base supports it.
- `ENTRYPOINT` exec-form (`["/app"]`), `HEALTHCHECK` for non-k8s runtimes; no `sudo`, no
  setuid binaries you didn't ask for (distroless solves this class).
- **The image must contain what the code needs at runtime**, not just what the
  checkout has: data files, rulesets, models, migrations, and optional extras are
  dropped silently by package manifests and stage copies. "Works in a dev
  checkout, dead in the image" is a silent no-op, not a crash — the feature just
  returns empty. Smoke-test each control **against the built image**, and have
  the component assert its required artifacts at startup (`sota-code-security`
  rules/14 §2).

### 4.2.1 Interpreted-runtime variant (Node example; Python is isomorphic)

```dockerfile
# syntax=docker/dockerfile:1.7
FROM node:22.12.0-bookworm-slim@sha256:<digest> AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm \
    npm ci --ignore-scripts                  # scripts off by default (rules/03 §3.4)
COPY . .
RUN npm run build && npm prune --omit=dev

FROM gcr.io/distroless/nodejs22-debian13:nonroot@sha256:<digest>
WORKDIR /app
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY --from=build /app/package.json ./
USER nonroot
CMD ["dist/server.js"]
```

- **Copied files are not root's by accident.** `COPY` without `--chown` creates files owned by
  UID/GID 0 (Dockerfile reference). Leave application code root-owned **and read-only** to
  the runtime user (the process cannot rewrite its own code), and `--chown=<uid>` only the
  paths it must write. Never `chown -R`/`chmod 777` the whole tree to silence an error.
- **Do not make a package-manager launcher PID 1.** Measured 2026-09-25 (podman, node
  22.23.3, npm 10.9.9), stopping a container: with `CMD ["node", "server.js"]` the app's
  SIGTERM handler ran and it exited 0; with `npm start` the handler **never ran** (exit 1,
  npm reporting the child killed by SIGTERM); with shell-form `sh -c` the signal was
  ignored until the 10-second SIGKILL (exit 137). Exec the runtime directly, as above, or
  add a small init (`--init` in Docker and Podman). `yarn start` and `pnpm start` are the
  same shape. (OWASP: NodeJS Docker cheat sheet)

Python: builder installs into a venv (`pip install --require-hashes -r requirements.txt
--prefix /opt/venv` or `uv sync --locked`), final stage is
`distroless/python3`/Chainguard python copying `/opt/venv` — never ship pip, build
headers, or the resolver into the runtime image.

### 4.2.2 Image metadata for traceability

Stamp OCI annotations at build so every image self-identifies (consumed by rules/02 §2.8
and incident response):

```dockerfile
LABEL org.opencontainers.image.source="https://github.com/myorg/app" \
      org.opencontainers.image.revision="${GIT_SHA}" \
      org.opencontainers.image.created="${BUILD_DATE}"
```

(`image.source` also links GHCR images back to the repo for access control.) Pass via
build args from CI — but remember args used only in LABELs are fine; args carrying
secrets are not (§4.2).

## 4.3 Base image strategy

- **Digest-pin every `FROM`**: `FROM alpine:3.21@sha256:...` with Renovate updating the
  digest (it bumps both tag comment and digest — pin without rot). A bare tag means your
  base can change under you between builds, silently (Medium; High for release builds).
- Minimal runtime, in order of preference for compiled apps:
  `gcr.io/distroless/static` (nothing but certs/tzdata) > distroless/base (libc) >
  Chainguard/Wolfi images (near-zero-CVE, apk-based, frequent rebuilds; check license/SLA
  for the versioned ones) > alpine (small, musl caveats) > slim debian/ubuntu. Full
  distro images in prod = Medium (CVE noise + attack tooling: shells, package managers,
  curl all gift-wrapped for the attacker).
- Interpreted runtimes: use the distroless/Chainguard language images (python, node) or a
  tightly-trimmed slim base; the multi-stage pattern still applies (build deps, compilers,
  headers stay in the builder).
- **One blessed base set per org**, rebuilt/re-digested weekly via automation, with app
  teams consuming the internal mirror — not forty teams pulling forty bases from Docker
  Hub (also dodges Hub rate limits and gives you a choke point for emergency base
  patching).
- Debugging distroless: use ephemeral debug containers (`kubectl debug`) or `:debug`
  variants in non-prod — do NOT add a shell to the prod image "temporarily".
- **Images have a maximum age in production** (e.g. 30 days, first- and third-party alike).
  Rebuild when the base's packages change, not only on the weekly cron, and redeploy
  inside the limit. Never patch a running container (`kubectl exec … apt-get upgrade`):
  the fix is a rebuild plus redeploy, or the next restart silently reverts it. Measure age
  from the build record (provenance, SBOM store, push time), not the image config's
  `created` field — reproducible images pin it:
  `crane config gcr.io/distroless/static-debian13:nonroot` reports
  `1970-01-01T00:00:00Z` (measured 2026-09-26). (OWASP: DSOMM; Kubernetes Security cheat sheet)

### 4.3.1 Base image upgrade flow (make it boring)

The base image is your largest, most-shared dependency; treat it with rules/03 rigor:

1. Weekly scheduled job rebuilds/mirrors blessed bases, scans them, signs them
   (rules/02), publishes new digests to the internal registry.
2. Renovate opens digest-bump PRs across consuming repos (grouped, automerge-eligible
   when tests pass — a base digest bump with green tests is the safest PR class there is).
3. Emergency path (critical base CVE): the same flow, manually triggered, with an org
   dashboard of which services still run the old digest (query deployed digests against
   SBOM store, rules/03 §3.5).

Audit: ask "when a glibc CVE lands, what happens?" If the answer involves forty teams
editing Dockerfiles by hand, the strategy is missing (Medium).

## 4.4 Image scanning

- Scan in CI per build (`grype`/`trivy image` against the **built digest**, before push or
  between push and promotion) and on schedule against **deployed** digests (rules/03
  §3.6 — new CVEs hit old images).
- Gate on triaged policy, not raw severity walls; same VEX/ignore-with-expiry discipline
  as rules/03 §3.6. A scan step with `continue-on-error: true` or `exit-code: 0` is
  decorative (Medium, High if it's the only control).
- Scan the base image separately on its weekly rebuild — base CVEs are fixed by bumping
  the blessed base once, not by forty app teams triaging the same finding.
- Also run config scanning on the Dockerfile (hadolint; trivy misconfig/checkov catch
  root-user, ADD-vs-COPY, latest-tags) as a PR check.
- **Malware and binary composition analysis reach beyond libraries.** The malicious-package
  checks of rules/03 §3.4 see packages; extend them to container images, VM and golden
  images, and release binaries. **As supplier**, before release: inventory the built
  binaries (syft catalogs binaries, e.g. `go-module-binary-cataloger`), compare the result
  with the expected SBOM (an unexpected component is the finding), and secret-scan the
  unpacked artifact (`trivy rootfs --scanners secret <dir>`). **As consumer**, run the same
  on binaries you receive (vendor installers, agents, appliance images) before they enter
  the internal repository, plus a malware scan (ClamAV, or YARA rules from
  `sota-detection-engineering`). `trivy vm` is marked EXPERIMENTAL (trivy 0.72.0 help).
  (OWASP: DSOMM; Software Supply Chain Security cheat sheet)
- Don't conflate: secret scanning of image layers (trivy/ggshield can) is worth one
  scheduled pass over the registry — finds the `ENV TOKEN` mistakes of §4.2 historically.

## 4.5 Registry security & immutable tags

- **Immutable tags**: enable tag immutability where the registry supports it (ECR
  immutable tags, Artifactory, GAR via policy). A re-pushed `v1.2.3` is either an accident
  that breaks provenance or an attack that survives review. Mutable release tags = High.
- **Deploy by digest** (rules/06 §6.6, rules/07 §7.1): manifests reference
  `image@sha256:...`; tags are for humans. `:latest` in any deploy manifest = High; a
  mutable tag in prod manifests = Medium-High.
- AuthN/AuthZ: CI pushes via OIDC-federated, repo-scoped identity (no static registry
  passwords — rules/01 §1.2); runtime pulls via read-only pull identities per
  cluster/namespace; humans get no push rights to release repos (CI is the only writer —
  that's what makes provenance meaningful).
- Separate repos (or registries) for `dev` / `staging-verified` / `prod-promoted`;
  promotion copies a verified digest (rules/02 §2.5), never rebuilds. Prod pulls only
  from the prod registry — enforce via admission policy registry allowlist (rules/07).
- Retention: garbage-collect untagged/dev images on schedule, but **never** delete
  digests referenced by running workloads or release history; keep release artifacts +
  attestations for your audit horizon.
- Pull-through cache for upstream bases (mirrors §4.3 and rules/03 §3.3): availability,
  audit log, single patch point.

### 4.5.1 Reference CI build-push-attest sequence

```yaml
- name: Build and push by digest
  id: build
  uses: docker/build-push-action@<sha> # v6
  with:
    push: true
    tags: ghcr.io/myorg/app:${{ github.sha }}   # human-readable; digest is the identity
    provenance: false        # provenance via attest step below (single source of truth)
    sbom: false
- name: Scan exactly what was pushed
  run: grype "ghcr.io/myorg/app@${{ steps.build.outputs.digest }}" --fail-on high
- name: SBOM + attest + sign (rules/02, rules/03 §3.5)
  run: |
    syft "ghcr.io/myorg/app@${DIGEST}" -o cyclonedx-json > sbom.cdx.json
    cosign attest --yes --type cyclonedx --predicate sbom.cdx.json "ghcr.io/myorg/app@${DIGEST}"
    cosign sign --yes "ghcr.io/myorg/app@${DIGEST}"
```

The invariant: every post-build step operates on `@digest` captured from the push — never
re-resolve a tag mid-pipeline (a re-resolved tag is a TOCTOU window).

## 4.6 Build infrastructure separation

- Builders are not runtime: build clusters/runners have no access to prod data planes, no
  prod secrets, and prod has no reason to reach builders. The build system signs (id-token)
  and pushes — that's its entire prod-facing surface.
- Shared BuildKit/buildd daemons across trust levels are a cross-tenant risk (cache
  poisoning, socket = root): per-job ephemeral builders (rules/01 §1.6) or rootless
  BuildKit with isolated caches. Mounting `/var/run/docker.sock` into CI job containers
  is host-root-for-every-job (High).
- Cache keys must include the trust context: a release build restoring a cache produced
  by an untrusted PR build inherits whatever the PR poisoned (rules/01 §1.6).

### 4.6.1 The host under the pipeline

Self-hosted runners and CI servers are production-tier assets, hardened like one.

- The runner/agent process runs as a **non-root** OS account. The GitHub runner's
  `config.sh` refuses root unless `RUNNER_ALLOW_RUNASROOT` is set, so that variable in a
  provisioning file is a finding; in Kubernetes, no `runAsUser: 0` on runner pods.
- Runner and CI-server hosts and images are patched on a schedule, kept in a versioned
  inventory, and built to a CIS or STIG baseline.
- **No unused services** on build hosts and runner images: the runner agent and what builds
  need, nothing listening that a job could reach or abuse (no stray SSH, web or database
  daemons). Compare `ss -tlnp` on the host with the expected list.
- **Build steps never change the system CA trust store** (`update-ca-certificates`,
  `update-ca-trust`, files dropped into `/usr/local/share/ca-certificates` or
  `/etc/pki/ca-trust`) or the tool-level equivalents (`NODE_EXTRA_CA_CERTS`,
  `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, `git config http.sslCAInfo` or
  `http.sslVerify false`, `GIT_SSL_NO_VERIFY`). A CA added mid-build lets whoever holds its
  key read and rewrite every TLS fetch after it. An organisation CA belongs in the reviewed
  runner image.
- **Toolchain integrity is monitored.** Compilers, SDKs and VCS clients in the runner image
  are verified against the vendor's checksum or signature when installed, and a hash
  baseline of those binaries is re-checked on a schedule, so that a swapped `gcc` or `git`
  shows up.
- **The whole build stack has a cadence**: runner images, toolchains, CI plugins and
  scanners are updated, patched and re-approved on a fixed schedule with a recorded date,
  not only when something breaks. (OWASP: Software Supply Chain Security cheat sheet;
  SCVS 3.9, 3.15, 3.16)
- Nothing sensitive survives a job: no credentials, tokens or checkouts left on disk.
  Ephemeral runners (rules/01 §1.6) give you this by construction; a persistent host needs a
  workspace and credential wipe that is itself verified.
  (OWASP: CI/CD Security cheat sheet; GitHub Actions Security cheat sheet; Secrets Management cheat sheet)

## 4.7 Developer endpoints are build infrastructure

A laptop that holds signing keys, publish tokens or push rights to release branches is part
of the supply chain, and its IDE extensions run with the developer's full access.

- Allow only vetted IDEs and extensions. VS Code enforces this with the `extensions.allowed`
  setting (`AllowedExtensions` policy, since 1.96), by publisher, extension ID or pinned
  version; other IDEs need their own allowlist or a private marketplace.
- Keep an inventory of installed extensions and plugins
  (`code --list-extensions --show-versions`), so a malicious extension can be traced to
  the machines that have it.
- Machines holding signing or publish credentials run endpoint protection and are enrolled
  in device management; better still, those credentials live in CI (rules/02 §2.6).
  (OWASP: Software Supply Chain Security cheat sheet)

## Audit checklist

- [ ] No unpinned/unverified network fetches in builds (no `curl | sh`); toolchain versions pinned; builds run from clean CI checkouts only
- [ ] Multi-stage Dockerfiles; final stage minimal (distroless/Chainguard-class), non-root `USER`, exec-form ENTRYPOINT
- [ ] No secrets in ARG/ENV/COPY'd files/layers — BuildKit secret mounts only; `.dockerignore` excludes `.git` and env/secret files
- [ ] Every `FROM` digest-pinned with Renovate-managed updates; org-blessed base images rebuilt on schedule from an internal mirror
- [ ] Image scans per build on the built digest + scheduled scans of deployed digests; gates fail closed; ignores carry owner + expiry; hadolint/dockerfile misconfig checks on PRs
- [ ] Registry: immutable tags on; deploys reference digests (no `:latest`); CI is the sole writer to release repos via OIDC; promotion copies verified digests, never rebuilds
- [ ] Retention preserves released digests + attestations; pull-through cache for upstream bases
- [ ] Build infra isolated from runtime; no docker.sock mounts; ephemeral or rootless builders; caches scoped by trust boundary
- [ ] **Runner hosts hardened (§4.6.1), High:** `grep -rn -E 'RUNNER_ALLOW_RUNASROOT|runAsUser:[[:space:]]*0[[:space:]]*$' <runner provisioning: Dockerfiles, IaC, Helm values>` is empty; hosts/images on a patch schedule with a CIS/STIG baseline; no credentials left between jobs
- [ ] **Maximum image age enforced; no in-place patching (§4.3), Medium:** running digests (`kubectl get pods -A -o jsonpath='{..imageID}'`) checked against their build date from provenance/SBOM store, none past the limit; `grep -rn -E '(kubectl|docker|podman) exec[^|;]*(apt-get|apt|apk|yum|dnf|microdnf|pip|npm) +(install|upgrade|update|add)' <runbooks, scripts>` is empty
- [ ] **No remote code execution or committed binaries in the build (§4.1), High:** `grep -rn -E '(curl|wget)[^|;]*\|[[:space:]]*(sudo[[:space:]]+)?(ba|z)?sh([[:space:]]|$)|eval[[:space:]]+"?\$\((curl|wget)|(ba|z)?sh[[:space:]]+<\((curl|wget)' .github/workflows` is empty (extend the path list to Dockerfiles and scripts); `git ls-files | grep -E '\.(exe|dll|so|dylib|jar|war|bin)$'` hits are each justified; local, tarball and cache installs are hash-checked
- [ ] **Build inputs typed; no DNS or network rewrites in builds (§4.1), High:** `grep -rn -E '/etc/hosts|/etc/resolv\.conf|--add-host|add-hosts:|(HTTPS?|ALL|NO)_PROXY[[:space:]]*[=:]|(https?|all|no)_proxy[[:space:]]*[=:]' .github/workflows` is empty; `yq '.on.workflow_dispatch.inputs // {} | to_entries | .[] | select((.value.type // "string") == "string") | .key' .github/workflows/*.yml` lists only inputs that never reach a build command
- [ ] **No package-manager launcher as PID 1; app files not root-writable by the app (§4.2.1), Medium:** `grep -n -E '^(CMD|ENTRYPOINT)[[:space:]].*(npm|yarn|pnpm)[^A-Za-z]+(start|run)' Dockerfile*` is empty; no `chmod 777` or blanket `chown -R` of the app tree
- [ ] **Release binaries and received binaries analysed (§4.4), Medium:** the release workflow has a binary inventory, secret scan and (for received binaries) malware scan — `grep -rn -E 'clamscan|yara|trivy[[:space:]]+(rootfs|vm|fs)[^#]*secret|syft[[:space:]]+(scan[[:space:]]+)?(dir|file):' .github/workflows` is non-empty where release artifacts are built
- [ ] **Build hosts: no CA-store changes, minimal services, toolchain baseline, patch cadence (§4.6.1), High:** `grep -rn -E 'update-ca-certificates|update-ca-trust|/usr/local/share/ca-certificates|/etc/pki/ca-trust|NODE_EXTRA_CA_CERTS|SSL_CERT_FILE|REQUESTS_CA_BUNDLE|http\.sslVerify[[:space:]=]+"?false|http\.sslCAInfo|GIT_SSL_NO_VERIFY' .github/workflows Dockerfile* <runner-image-dir>` hits only the reviewed runner image; `ss -tlnp` on a runner host matches its expected listeners; toolchain hash baseline and last stack re-approval date recorded
- [ ] **IDE extensions allowlisted and inventoried (§4.7), Medium:** managed VS Code settings contain `"extensions.allowed"` (`grep -c '"extensions.allowed"' <managed settings.json>` is not `0`); an extension inventory exists for machines holding signing/publish credentials
