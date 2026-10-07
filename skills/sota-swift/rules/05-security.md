# 05 — Security: the language-level surface

Swift-specific spellings of the classes `sota-code-security` owns. Every API default quoted here
was read from the library's source or docs on 2026-10-07; re-check before relying on one.

## 1. Input validation and untrusted data

- Validate at the boundary into typed values (a `struct` with a failable or throwing init), then
  pass the typed value inward — not raw `String`s re-checked three layers down.
- **Decoding has no size cap**: swift-foundation's `JSONDecoder` caps nesting depth (512) but not
  input size. Bound the body before decoding — Vapor's `defaultMaxBodySize` is `"16kb"` and can be
  raised per route; raise it deliberately, never to unlimited (rules/06).
- **Regex**: Swift's `Regex` engine backtracks (SE-0351: *"the regex engine backtracks by
  default"*); there is no linear-time guarantee, so ReDoS is possible on input. Validate with
  `wholeMatch(of:)` (anchored), not `firstMatch`; never compile `try Regex(userString)`; escape
  untrusted text with `NSRegularExpression.escapedPattern(for:)`; bound backtracking with
  `Local { }` (atomic) or possessive quantifiers; cap input length first.

## 2. Deserialization and unsafe parsing

- `NSKeyedUnarchiver`: use `unarchivedObject(ofClass:from:)` (secure coding). The deprecated
  `unarchiveObject(with:)` and `NSUnarchiver` instantiate arbitrary classes from the archive —
  Apple describes NSSecureCoding as *"robust against object substitution attacks"*. Never set
  `requiresSecureCoding = false` on untrusted data.
- `XMLParser.shouldResolveExternalEntities` defaults to `false` (Apple: setting it `true` *"may
  cause other I/O operations, either network-based or disk-based"*) — XXE. Keep it `false`.
  Needs verification: whether swift-corelibs-foundation's `XMLParser` on Linux expands *internal*
  entities regardless (entity-expansion DoS); cap XML input size either way.
- `PropertyListDecoder`/`PropertyListSerialization` on untrusted data: decode into concrete
  `Codable` types, never into `NSObject` graphs.

## 3. Cryptography and randomness

- Use **CryptoKit**, or **swift-crypto** off Apple platforms (it *"re-exports the API of
  CryptoKit"* on Apple platforms and uses BoringSSL elsewhere). `Insecure.MD5`/`Insecure.SHA1`:
  *"For new services, avoid these algorithms."* No `CC_MD5`/`CC_SHA1` from CommonCrypto.
- Randomness for keys, tokens and nonces: `SymmetricKey(size:)`, `SystemRandomNumberGenerator`
  (the default for `.random(in:)`). Never `arc4random`, `srand`/`rand`, `drand48` for secrets.
- Compare MACs with `HMAC.isValidAuthenticationCode` (constant time); never `==` on a MAC, token
  or digest. Primitive choice and protocol → `sota-code-security` rules/04.

## 4. Secrets handling and logging

- No secrets in source or `Package.swift`; read them from the environment or a secret store at
  startup (`sota-secrets-management`). Vapor's docs: *"Dotenv files with sensitive information
  such as passwords should not be committed"* — ignore `.env*` in git.
- **swift-log has no built-in redaction**: its metadata attributes (SLG-0004) are, in its own
  words, *"classifications, not enforcement"*. Never pass tokens, passwords, `Authorization`
  headers or PII as message text or metadata; log identifiers, not values.
- Apple's `os.Logger` redacts dynamic strings by default; `privacy: .public` on a secret undoes
  that and is a finding.
- Query-string tokens end up in access and error logs (Vapor's error middleware logs the request
  URL): send credentials in headers.

## 5. Injection: SQL, commands, dynamic code

- **SQL**: SQLKit interpolation binds with `\(bind:)`; `\(unsafeRaw:)` — whose own doc says
  *"This interpolation is inherently unsafe. It provides no protection whatsoever against SQL
  injection attacks"* — and the deprecated `\(raw:)` concatenate. In PostgresNIO, plain `\(value)`
  in a `PostgresQuery` binds; `\(unescaped:)` and `PostgresQuery(unsafeSQL:)` do not. Fluent's
  raw-SQL paths are the same rule.
- **Commands**: `Process` with `executableURL` and an `arguments` array (`launchPath` is legacy);
  never `/bin/sh -c` with interpolated input. swift-subprocess (1.0 with Swift 6.4) — prefer an
  absolute `.path(...)` executable over a PATH lookup by name.
- **A failed child does not throw.** `Process.run()` throws only when the launch fails; after
  `waitUntilExit()` check `terminationReason == .exit` **and** `terminationStatus == 0` — on
  `.uncaughtSignal` the status holds the signal number (swift-corelibs-foundation
  `Process.swift`). swift-subprocess says it directly: *"A non-zero exit code is a normal
  result, not a thrown error"* — test `terminationStatus.isSuccess`.
- **Dynamic code evaluation**: Swift has no `eval`, but these evaluate strings: JavaScriptCore
  `JSContext.evaluateScript`, `NSExpression(format:)`, `NSPredicate(format:)` built by string
  interpolation (use `%@` arguments or `evaluate(with:substitutionVariables:)`), `dlopen`/`dlsym`
  and `NSClassFromString` fed by input.

## 6. Files and paths

- Canonicalise and contain: swift-system's `FilePath.lexicallyResolving(_:)` *"returns `nil` if
  the result would "escape" from `self`"*, but *"does not consult the file system to resolve
  symlinks"* — so also resolve symlinks (`resolvingSymlinksInPath`/`realpath`) and re-check the
  prefix. `URL.standardized` alone is not a containment check; `appendingPathComponent(input)`
  with `../` in the input walks out of the base.

## 7. Outbound HTTP: SSRF and TLS verification

- **AsyncHTTPClient follows up to 5 redirects by default**: set `.disallow` or a deliberate
  `.follow(max:allowCycles:)`, and re-validate the target of each hop. Its configuration has no
  connect-time address filter (needs verification: only `dnsOverride` was found), so resolve and
  check the destination against private, loopback and metadata ranges yourself before dialling
  user-supplied URLs (`sota-code-security` rules/01).
- **TLS verification stays on**: never `certificateVerification: .none` or
  `.noHostnameVerification` in NIOSSL. NIOSSL's `makeClientConfiguration()` defaults to
  `minimumTLSVersion: .tlsv1` — set `.tlsv12` explicitly. A `URLSession` delegate that answers
  `serverTrust` challenges with `.useCredential` without evaluating the trust disables
  verification. Transport policy → `sota-network-security` rules/06.

## Audit checklist

- [ ] Input validation: untrusted input becomes typed values at the boundary; request bodies are size-capped before decoding (no unlimited `maxSize`).
- [ ] Regex escaping, anchoring & engine: input is validated with the anchored `wholeMatch` (not `firstMatch`); no user-supplied pattern is compiled (grep `try +Regex\(`); interpolated text goes through `escapedPattern(for:)`; input length is capped because the engine backtracks and is not linear-time.
- [ ] Deserialization: no `unarchiveObject(with:`, `NSUnarchiver` or `requiresSecureCoding = false` on untrusted data; `shouldResolveExternalEntities` never `true`; XML input size-capped.
- [ ] Cryptography & randomness: CryptoKit/swift-crypto only; no `Insecure.MD5`/`Insecure.SHA1`/`CC_MD5` for security; secrets from `SymmetricKey`/`SystemRandomNumberGenerator`, never `arc4random`/`srand`/`drand48`; MACs and tokens compared with `isValidAuthenticationCode`, never `==`.
- [ ] Secrets handling: no credentials in source, `Package.swift` or committed `.env` files; `.env*` git-ignored.
- [ ] Logging hygiene: no logging secrets, tokens, passwords, `Authorization` headers or PII in messages or metadata (swift-log does not redact) (grep `logger\.\w+\(.*(token|password|secret|apiKey|authorization)`); no `privacy: .public` on secrets; credentials never in query strings.
- [ ] SQL injection: no `\(unsafeRaw:`, `\(raw:`, `\(unescaped:` or `unsafeSQL:` (grep) reachable by input — no raw query built by string interpolation; queries are parameterized with `\(bind:)`/plain `PostgresQuery` interpolation.
- [ ] Command / subprocess injection: `Process`/swift-subprocess use an argv array with an absolute executable; no `"/bin/sh"` + `"-c"` with interpolation (grep `"/bin/(ba)?sh"`).
- [ ] Child exit status read (MEDIUM, HIGH when the output is trusted): `grep -rlE 'Process\(\)|import Subprocess' --include='*.swift' . | while IFS= read -r f; do grep -qE 'terminationStatus|isSuccess' "$f" || echo "$f"; done` — and every `terminationStatus` check also tests `terminationReason`.
- [ ] Dynamic code evaluation: no `evaluateScript`, `NSExpression(format:`, interpolated `NSPredicate(format:`, `dlopen` or `NSClassFromString` fed by input.
- [ ] Path traversal: file paths built from input are resolved (`lexicallyResolving` + symlink resolution) and contained under the base directory.
- [ ] SSRF / outbound requests: user-supplied URLs are validated against private/loopback/metadata addresses before connecting; AsyncHTTPClient redirect policy is explicit.
- [ ] TLS verification: no `certificateVerification: .none`/`.noHostnameVerification`; NIOSSL clients set `minimumTLSVersion: .tlsv12`; no `URLSession` trust override that skips evaluation (grep `serverTrust`).
