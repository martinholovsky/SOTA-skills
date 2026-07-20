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

FROM gcr.io/distroless/static-debian12:nonroot@sha256:<digest>
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
  rules/10 §2.11).

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

FROM gcr.io/distroless/nodejs22-debian12:nonroot@sha256:<digest>
WORKDIR /app
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/dist ./dist
COPY --from=build /app/package.json ./
USER nonroot
CMD ["dist/server.js"]
```

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

## Audit checklist

- [ ] No unpinned/unverified network fetches in builds (no `curl | sh`); toolchain versions pinned; builds run from clean CI checkouts only
- [ ] Multi-stage Dockerfiles; final stage minimal (distroless/Chainguard-class), non-root `USER`, exec-form ENTRYPOINT
- [ ] No secrets in ARG/ENV/COPY'd files/layers — BuildKit secret mounts only; `.dockerignore` excludes `.git` and env/secret files
- [ ] Every `FROM` digest-pinned with Renovate-managed updates; org-blessed base images rebuilt on schedule from an internal mirror
- [ ] Image scans per build on the built digest + scheduled scans of deployed digests; gates fail closed; ignores carry owner + expiry; hadolint/dockerfile misconfig checks on PRs
- [ ] Registry: immutable tags on; deploys reference digests (no `:latest`); CI is the sole writer to release repos via OIDC; promotion copies verified digests, never rebuilds
- [ ] Retention preserves released digests + attestations; pull-through cache for upstream bases
- [ ] Build infra isolated from runtime; no docker.sock mounts; ephemeral or rootless builders; caches scoped by trust boundary
