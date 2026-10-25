# 21 — File Upload Handling (CWE-434)

Split out of [rules/05](05-web-security.md) (formerly section 10) on 2026-09-25, when [rules/05](05-web-security.md) reached the 500-line cap;
the section is now §1. Serving what was uploaded — `nosniff`, a separate origin, CSP on the
user-content origin — stays in [rules/05](05-web-security.md) §6 and [rules/20](20-browser-response-hardening.md).

## 1. File upload handling (CWE-434)

- Validate by **content**, not trust: check magic bytes/parse the file with a
  real decoder; the client `Content-Type` and filename extension are
  attacker-controlled.
- Allowlist extensions (parse, then compare against a set; no home-grown regex)
  AND served content types. Reject double extensions (`shell.php.jpg`), leading,
  repeated or trailing dots, leading hyphens, leading/trailing spaces, NUL
  tricks; **generate the stored filename yourself** (UUID), keep the original
  only as metadata (also kills path traversal, [rules/01](01-input-injection.md) §4).
- Store outside the web root, or in object storage with no execute semantics.
  Never in a directory where the app server executes code (the classic
  webshell: upload `x.php` into `/uploads` served by PHP). Harden the store:
  its own volume mounted `noexec,nosuid,nodev`, files written without execute
  bits (`0640`/`0440`). `noexec` blocks only direct execution of binaries — an
  interpreter mapped to the directory still runs scripts — so also disable
  per-directory config overrides: Apache `AllowOverride None` with
  `AllowOverrideList None` (`.htaccess` is then never read); IIS keeps
  `system.webServer/handlers` locked for the upload path (`<location path=…
  overrideMode="Deny">`, handlers `accessPolicy="Read"`) so an uploaded
  `web.config` cannot re-enable execution. OWASP: File Upload cheat sheet;
  Go-SCP.
- Serve with: `Content-Type` you determined, `X-Content-Type-Options: nosniff`,
  `Content-Disposition: attachment` for anything not explicitly displayable,
  and ideally from a **separate origin/sandbox domain** (usercontent.example) so
  HTML/SVG payloads can't script against your app origin. SVG is XSS-capable —
  sanitize or serve as attachment. Set the download name yourself: a validated
  name as `filename*=UTF-8''…` (RFC 6266) plus an ASCII `filename`, never raw
  input — same for email attachments. OWASP: ASVS 5.0 V5.4.1, V5.4.2.
- Limits: max size (enforced streaming, before buffering whole body), max
  files/request, rate limits; image processing in a sandboxed/least-privilege
  worker (decoder CVEs: ImageTragick lineage) with decompression-bomb caps
  (pixel-count limit before decode). Upload endpoints are authenticated,
  authorized, rate-limited and under a per-user total quota; each feature documents
  types, packed/unpacked max size and the fate of a flagged file; log each
  completion (uploader, stored name, detected type; [rules/07](07-data-exposure.md) §2.1).
- Scan where threat model warrants (AV/CDR for shared-file features, definitions
  current; never public multi-scanners — submitting discloses the file); refuse
  archives the feature doesn't need; strip metadata (EXIF GPS) from re-served
  images (privacy, [rules/07](07-data-exposure.md)). OWASP: File Upload cheat sheet; ASVS 5.0 V5.1.1.

## Audit checklist

- [ ] Are uploads content-validated (magic bytes or a real decoder; an extension allowlist that rejects double extensions, leading/repeated/trailing dots, leading hyphens, spaces and NUL), renamed server-side, stored non-executable outside the web root (ideally separate origin), size-capped pre-buffer with a per-request file count, rate limit and per-user quota on an authenticated, authorized endpoint, and served with nosniff + attachment disposition and a server-set `filename*=UTF-8''…` download name (§1)?
- [ ] Are SVGs sanitized or never served inline from the app origin (§1)?
- [ ] **Per-directory execution overrides — HIGH on upload paths**: `grep -rnEi -- "AllowOverride[[:space:]]+(All|FileInfo|Options)|overrideMode=['\"]Allow|accessPolicy=['\"][^'\"]*(Script|Execute)" .`; upload volume mounted `noexec,nosuid,nodev`, files written `0640`/`0440` (§1)?
- [ ] **Upload processing and retention (§1) — MEDIUM, HIGH when public uploads reach an unsandboxed image decoder**: are images decoded in a sandboxed least-privilege worker with a pixel-count cap before decode, EXIF/GPS stripped from re-served images (upload a GPS-tagged JPEG, download it, and `exiftool -gps:all` prints nothing), archives refused where the feature needs none, shared files AV/CDR-scanned with current definitions, and each completion logged with uploader, stored name and detected type? Each hit of `grep -rniE "virustotal\.com/(api|vtapi)|api\.metadefender\.com|hybrid-analysis\.com/api" .` that submits user files to a public multi-scanner is a finding.
