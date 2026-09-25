# 04 — Security: injection, deserialization, ASP.NET Core, crypto

The CLR is memory-safe, so the dominant .NET vulnerabilities are **injection,
unsafe deserialization, auth gaps, and crypto misuse**. Treat every byte from
network/file/DB/config as untrusted. Reference:
[OWASP .NET cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/DotNet_Security_Cheat_Sheet.html),
[ASP.NET Core security](https://learn.microsoft.com/en-us/aspnet/core/security/).

## 1. SQL injection

- **EF Core**: LINQ is parameterized and safe. `FromSql`, `ExecuteSql` and `SqlQuery` (and the older
  `FromSqlInterpolated`) wrap each interpolated value in a `DbParameter`. **`FromSqlRaw`,
  `ExecuteSqlRaw` and `SqlQueryRaw` with string concatenation/interpolation are CRITICAL**: they
  send the built string as SQL, and EF's "SQL Queries" page puts `SqlQueryRaw` in the same dynamic
  class as `FromSqlRaw`.
- **Dapper / ADO.NET**: always pass parameters (`new { id }` / `SqlParameter`), never concatenate
  input into the SQL text. Identifiers (table/column/ORDER BY) can't be parameters — allowlist them.

## 2. Deserialization

- **`BinaryFormatter` is removed in .NET 9+** (the API throws `PlatformNotSupportedException`); it
  was a notorious RCE vector. Never reintroduce it (or `NetDataContractSerializer`, `SoapFormatter`,
  `LosFormatter`, `ObjectStateFormatter`) — CRITICAL on sight.
- **Web Forms ViewState is `ObjectStateFormatter` output, so its key is the only thing between
  a client and that deserializer** (.NET Framework `System.Web`; ASP.NET Core has no ViewState).
  The class is `sota-code-security` rules/01 §8. Three findings. `EnableViewStateMac="false"` is
  intent to ship unsigned state: Microsoft's "Farewell, EnableViewStateMac!" post says 4.5.2+
  refuses it and that without the MAC an attacker may run code on the server. Remove it.
  A fixed `<machineKey validationKey=… decryptionKey=…>` in `web.config` is CRITICAL when the
  value came from a sample, a tutorial or another app, or sits in source control. Microsoft counted
  over 3,000 publicly disclosed keys used for ViewState code injection (Security blog, Feb 2025).
  The default, `AutoGenerate,IsolateApps`, is a random per-app key held in LSA. It is the safe
  choice for a single server and not a finding. A web farm needs one explicit key: generate it
  with a CSPRNG, keep it out of the repo (encrypt the `machineKey` section), and rotate it after any
  exposure. `ViewStateEncryptionMode="Never"` (the default is `Auto`) is MEDIUM information exposure:
  encryption hides the contents, but it is the MAC that stops tampering.
  OWASP: Code Review Guide v2.
- **"Removed" has an opt-back-in, and it re-arms every caller.** On .NET 9+ the
  unsupported `System.Runtime.Serialization.Formatters` NuGet package plus the
  `EnableUnsafeBinaryFormatterSerialization` switch (MSBuild property, or the
  `System.Runtime.Serialization.EnableUnsafeBinaryFormatterSerialization` AppContext switch)
  restore a working `BinaryFormatter` "including its vulnerabilities" (Microsoft's
  compatibility-package page). The type identity is unchanged, so a **dependency** that calls
  it starts working again with no edit of its own. Measured on the .NET 10 SDK: package alone →
  `NotSupportedException`, switch alone → `PlatformNotSupportedException`, both → a full
  round-trip. Either half in a project file is CRITICAL until justified.
- **`DataSet`/`DataTable` are a deserializer.** Microsoft: they are *"in general not safe
  when populated with untrusted input"* — `ReadXml`/`ReadXmlSchema`, a `DataSet` parameter on a
  SOAP/WCF endpoint, or `DeserializeObject<DataSet>` via Json.NET (a DoS vector). The built-in
  type allowlist (Microsoft ties removing it to CVE-2020-1147) is switched off wholesale by
  `Switch.System.Data.AllowArbitraryDataSetTypeInstantiation` and widened by the
  `System.Data.DataSetDefaultAllowedTypes` AppDomain key — both are findings on an input path.
  Bind untrusted data to a DTO instead. Legacy .NET Framework code: `JavaScriptSerializer` built
  with a `SimpleTypeResolver` is the same gadget class as `TypeNameHandling` (CA2321/CA2322).
- **JSON**: prefer `System.Text.Json` with known types. Newtonsoft `TypeNameHandling.Auto/All/Objects`
  (or `System.Text.Json` with an unrestricted polymorphic type resolver) on untrusted input enables
  gadget-style RCE — don't. Bind to explicit DTOs.
- **`System.Text.Json` defaults are lenient**: unknown members are ignored, a repeated property is
  accepted, nullability and required constructor parameters go unenforced. For untrusted JSON on
  .NET 10+ use the `JsonSerializerOptions.Strict` preset (`UnmappedMemberHandling.Disallow`,
  `AllowDuplicateProperties = false`, `RespectNullableAnnotations`, `RespectRequiredConstructorParameters`,
  case-sensitive; ".NET 10 libraries" what's-new), or set those properties on the options you own
  (`ConfigureHttpJsonOptions`/`AddJsonOptions`). Duplicate keys: `sota-code-security` rules/01 §11.
- **When Json.NET type names cannot be removed, the binder is the control.** Set
  `JsonSerializerSettings.SerializationBinder` to your own `ISerializationBinder`. Its
  `BindToType(assemblyName, typeName)` returns the type only on an exact match against a fixed
  set, and returns `null` or throws for anything else. Do not use `Contains`/`StartsWith`, which
  also admit generic wrappers and look-alike names. Without one, `DefaultSerializationBinder`
  loads whatever assembly and type the payload names (`Assembly.Load` then `GetType`, read in the
  Json.NET source). CA2327–CA2330 flag type handling without a binder, and CA2326 flags type
  handling at all (off by default). Three limits remain:
  - **An allowlist covers the whole graph, not the root.** An allowed type with a member typed
    `object` or a broad interface lets the payload choose that member's type. Every nested
    `$type` must also pass the binder. Types whose setters act on the machine are dangerous even
    when "harmless": `FileInfo.IsReadOnly`'s setter changes the file's attributes on disk (read in
    the runtime source).
  - **The type name must not come from storage the attacker can write.** `Type.GetType(row.TypeName)`
    fed to `new DataContractJsonSerializer(t)`, `DataContractSerializer` or `XmlSerializer` is the
    same flaw one hop removed. Map a stored discriminator to a `typeof(...)` from a fixed table.
  - **Gadget-bearing assemblies raise the stakes.** The published RCE chains use types like
    `ObjectDataProvider` and `ResourceDictionary` (WPF), `PSObject` (PowerShell,
    `System.Management.Automation`), `AssemblyInstaller`, `WorkflowDesigner`, `BindingSource` and
    `DataViewManager`. An internet-facing service that deserializes type-named data should not
    reference WPF, WinForms or the PowerShell SDK. Treat any reference as HIGH until the
    deserializer is fixed. Removing gadgets is defence in depth, not the fix.

  OWASP: Deserialization cheat sheet.
- **`XmlSerializer`/`DataContractSerializer`** with attacker-controlled types is risky; disable DTD
  processing on XML readers (XXE) — `XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit,
  XmlResolver = null }`. **A consumer is as safe as the reader it is given.** Measured on .NET 10:
  `XmlReader.Create` without settings refused a DOCTYPE, but `new XPathDocument(stream)` (or a
  `TextReader`), `XmlDocument.Load(stream)` and `new XmlTextReader(...)` parsed it, and the first
  two expanded internal entities up to the `MaxCharactersFromEntities` limit. External entities
  stayed unresolved until a reader was handed an `XmlUrlResolver`: then `XPathDocument` returned a
  local file's contents. So build `XPathDocument` and the input to `XslCompiledTransform.Transform`
  from `XmlReader.Create(source, hardenedSettings)`, and load stylesheets with the default
  `XsltSettings` (`document()` stayed prohibited, measured). *(OWASP: XXE Prevention cheat sheet.)*

## 3. Command / path / other injection

- **OS command**: avoid shelling out; if you must, use `ProcessStartInfo` with
  `ArgumentList` (no `UseShellExecute`, no concatenated `Arguments`/shell).
- **Path traversal**: combine with a known root and verify the resolved `Path.GetFullPath` stays
  under it (compare against the root **plus a trailing separator**, or `/srv/up` admits
  `/srv/upload-evil`); reject `..`. Don't pass user input straight to file APIs.
- **`Path.Combine` discards the root when a later argument is rooted.** Measured on .NET 10:
  `Path.Combine("/srv/uploads", "/etc/passwd")` returns `/etc/passwd`; `Path.Join` returns
  `/srv/uploads/etc/passwd`. `Join` removes that trap but does not resolve `..`, so the
  `GetFullPath` + prefix check above is still what makes either safe.
- **Archive extraction (Zip Slip)**: `ZipFile.ExtractToDirectory` enforces the boundary —
  it throws `IOException` when an entry would land outside the destination (read in
  `ZipFileExtensions.ZipArchiveEntry.Extract.cs`, measured on .NET 10). The hand-rolled loop
  `entry.ExtractToFile(Path.Combine(dest, entry.FullName))` has no such check: a
  `../escaped.txt` entry was written outside `dest`. Prefer the directory API; if you must
  loop, apply the §3 path check to every entry.
- **LDAP/XPath/regex (ReDoS)**: parameterize/escape. **Regex has no timeout by default**:
  the match timeout is `Regex.InfiniteMatchTimeout` unless the process sets the
  `REGEX_DEFAULT_MATCH_TIMEOUT` AppContext value (read in `Regex.Timeout.cs`). On untrusted
  input pass a `TimeSpan` (`new Regex(p, opts, timeout)`, `matchTimeoutMilliseconds:` on
  `[GeneratedRegex]`) or use `RegexOptions.NonBacktracking` (.NET 7+, linear time). A
  **pattern** from a user is worse than input: `Regex.Escape` it, and Microsoft states that
  timeouts are *not* a security boundary against malicious patterns (CA3012).
  - **Escaping has a gap.** `Regex.Escape` leaves `]`, `}` and `-` alone (measured on .NET 10),
    so escaped data is safe as a literal run but **not inside a `[...]` class**. Build classes from
    a fixed set.
  - **A validator must match the whole string.** `Regex.IsMatch` finds a match anywhere, so an
    unanchored allowlist accepts `abc;rm`. In .NET, `$` and `\Z` also match **before a final `\n`**:
    `^[a-z]+$` accepts `"abc\n"`. Anchor with `\A…\z`, and never add `RegexOptions.Multiline` to a
    validator, because that makes `^`/`$` line anchors. `[RegularExpression]` (DataAnnotations)
    already requires the match to span the whole value and defaults to a 2 s timeout.
  - **Bound the input twice.** Check `input.Length` against a cap before matching, and put explicit
    limits in the pattern (`{1,64}`, not `+`).
  - **The engine has a cost.** The default engine backtracks. Atomic groups `(?>…)` stop a local
    blow-up, but .NET has no possessive quantifiers (`a++` is a parse error). `NonBacktracking`
    throws `NotSupportedException` when a pattern uses lookaround, backreferences or atomic groups,
    and it rejects `RightToLeft`. When you need those, stay on the backtracking engine with a timeout.
    *(OWASP: Input Validation cheat sheet; OWASP Proactive Controls 2024 C3; ASVS 5.0 V1.2.9;
    OWASP Go-SCP, validation.)*
- **Dynamic code evaluation: input must never become code.** .NET has no `eval`, but these do the
  same job: Roslyn scripting (`CSharpScript.EvaluateAsync`/`RunAsync` from
  `Microsoft.CodeAnalysis.CSharp.Scripting`), `CSharpCompilation.Create` + `Assembly.Load` of the
  bytes, `System.Reflection.Emit`, templates compiled to C# at runtime, and **dynamic LINQ**
  (`System.Linq.Dynamic.Core`: a `.Where("…")` string or `DynamicExpressionParser`). It also covers
  reflection that takes a name from the request: `Type.GetType(input)`, `Activator.CreateInstance`
  on that type, and `GetMethod(input).Invoke`. Measured on .NET 10: `Type.GetType` turned
  a string into `System.Diagnostics.Process`, and `Activator` then built a `ProcessStartInfo`.
  Roslyn scripting with default `ScriptOptions` read `/etc/hostname`. **Removing references is
  not a sandbox.** With `WithReferences(empty).WithImports()`, a direct `Process.Start` failed
  to compile. The same script then went through `Type.GetType(...).GetMethod("Start").Invoke`
  and created a file on disk. The runtime has no in-process boundary to fall back on: .NET 6+
  has no CAS or extra AppDomains, and Microsoft says CAS *"is no longer treated as a security
  boundary"*. It points you to OS boundaries (process, container, user account) instead
  (`sota-sandboxing`). The safe shape is a `Dictionary<string, Func<…>>` dispatch table, or an
  allowlist that maps names to `typeof(...)`, so input picks from a fixed set and is never
  compiled. For user formulas, use an expression library with a fixed grammar and no member
  access. Dynamic LINQ before 1.6.0 exposed reflection and static members (CVE-2024-51417). On
  1.7.4, `"".GetType()` and `System.IO.File` were rejected (measured), but a caller-supplied
  predicate can still filter on any property, so allowlist the fields it may name. The same
  sink covers `Expression.Lambda(...).Compile()` over a tree built from input, and CodeDom;
  `CompileAssemblyFromSource` threw `PlatformNotSupportedException` on .NET 10 (measured), so
  it matters on .NET Framework. `[AllowPartiallyTrustedCallers]` has no effect outside .NET
  Framework (Microsoft API docs). Keep secrets out of `ISerializable.GetObjectData`: what it
  adds leaves with the payload. *(OWASP: Code Review Guide; Proactive Controls 2024 C3; ASVS 5.0 V1.3.)*
- **SSRF: an outbound request to a destination the caller picks.** The policy is
  `sota-code-security` rules/01 §5. This bullet covers how to apply it in .NET. Best: take a key
  or ID from the caller, look up the base `Uri` in your own allowlist, and build the request
  yourself. Passing a caller's URL to `HttpClient.GetAsync`, `new HttpRequestMessage` or
  `WebRequest.Create` is the finding. When the destination really must be open:
  - **Check the address that is actually dialled.** If you resolve with `Dns.GetHostAddressesAsync`
    and then call `GetAsync(url)`, the name is resolved twice, and DNS rebinding can pass the first
    lookup. Do the check in `SocketsHttpHandler.ConnectCallback` instead (with `IHttpClientFactory`,
    set it via `ConfigurePrimaryHttpMessageHandler`). Resolve `context.DnsEndPoint.Host`, test every
    address, then connect a `Socket` to the checked `IPAddress` and return a `NetworkStream`.
    Reject these ranges:
    - loopback (`IPAddress.IsLoopback`)
    - private: 10/8, 172.16/12, 192.168/16, and ULA fc00::/7 (`IsIPv6UniqueLocal`)
    - link-local: 169.254/16, which includes 169.254.169.254 and so also catches the cloud
      metadata hostnames that resolve to it, and `IsIPv6LinkLocal`
    - 0.0.0.0/8
    - multicast

    Before any IPv4 range test, convert IPv4-mapped IPv6 (`IsIPv4MappedToIPv6` → `MapToIPv4()`).
    `System.Net.IPNetwork.Parse("10.0.0.0/8").Contains(ip)` does the range test.
    Measured on .NET 10:
    - The callback runs for every new connection, including a redirect hop to another host.
    - **Behind a proxy, the callback only sees the proxy's endpoint.** A request to
      169.254.169.254 through a `WebProxy` logged only the proxy address. So set
      `UseProxy = false` on the guarded handler, or enforce the rule at the proxy.
  - **`IPAddress.TryParse` is not strict.** On .NET 10 it accepted `127.1`, `0x7f.0.0.1`,
    `0177.0.0.1` and `2130706433`, and parsed each of them as 127.0.0.1. Never compare the
    caller's host *text* against a blocklist. Parse it, then test the resulting `IPAddress`.
  - **Redirects are followed by default.** `SocketsHttpHandler` and `HttpClientHandler` both
    default to `AllowAutoRedirect = true` with `MaxAutomaticRedirections = 50` (measured). Either
    set it to `false` and re-validate each `Location` yourself, or rely on the connect-time check
    above, which sees every hop.
  - **Schemes.** `HttpClient` throws `NotSupportedException` for `file`, `ftp` and `gopher`
    (measured). The obsolete `WebRequest.Create` (SYSLIB0014) does not: it returned a
    `FileWebRequest` for `file://` and an `FtpWebRequest` for `ftp://`. Still require
    `uri.Scheme == Uri.UriSchemeHttps` on any `Uri` you did not build yourself. A GraphQL resolver
    that fetches a URL argument belongs to this same class.

  OWASP: SSRF Prevention, .NET Security and GraphQL cheat sheets.

## 4. ASP.NET Core authn/authz & web

- **AuthZ on every non-public endpoint, denied by default**: set `AuthorizationOptions.FallbackPolicy`
  to `new AuthorizationPolicyBuilder().RequireAuthenticatedUser().Build()`. It covers every endpoint
  with no authorization metadata, including ones added later, and `[AllowAnonymous]` marks the
  deliberate exceptions (ASP.NET Core "secure data" docs). Without it an endpoint is public unless
  someone remembered `[Authorize]`/`.RequireAuthorization()`. Missing auth is HIGH.
- **Antiforgery** for cookie-authenticated state-changing requests
  (`[ValidateAntiForgeryToken]` / the antiforgery middleware). **CORS** locked
  to specific origins — never `AllowAnyOrigin()` with credentials.
- **Passkeys**: ASP.NET Core Identity has built-in passkey (WebAuthn) support in .NET 10+ — prefer
  them for new interactive logins (depth: `sota-code-security`, `sota-identity-access`).
- Validate/bind model input (data annotations / explicit validation); don't
  over-post (use DTOs/`[Bind]` allowlists, not the EF entity directly). Set
  security headers/HSTS; don't leak stack traces in production responses.
- **Secrets**: never in source/`appsettings.json` committed to git — use user secrets (dev), env, or
  a vault (`sota-secrets-management`); don't log them. Two .NET-specific ways they reach a log
  anyway. A `record`'s compiler-generated `ToString` *"displays the names and values of public
  properties and fields"*: measured on the .NET 10 SDK image, `record Creds(string User, string
  Password)` printed `Creds { User = bob, Password = hunter2 }`. Override `PrintMembers` on any
  record that carries a credential. And EF Core's `EnableSensitiveDataLogging()` puts *"parameter
  values for commands being sent to the database"* and entity property values into logs and
  exception messages. Keep it out of every non-development configuration. Logger-level redaction is
  `sota-observability` rules/01 §4. A desktop or Windows client keeps local secrets in
  `ProtectedData.Protect(..., DataProtectionScope.CurrentUser)` (DPAPI) or the OS credential store,
  never a plain file or registry value. Windows-only: Linux threw `PlatformNotSupportedException`
  (measured). *(OWASP: .NET Security cheat sheet.)*
- **Runtime patch level is an audit surface** — framework CVEs such as CVE-2025-55315 (Kestrel
  request smuggling) and how to check them: `rules/06` §3.

## 5. Cryptography & transport

- **Randomness**: `System.Security.Cryptography.RandomNumberGenerator` (e.g.
  `RandomNumberGenerator.GetBytes`) for tokens/keys/IVs/salts — never `System.Random` (HIGH).
- **Symmetric**: AES-GCM (`AesGcm`) for authenticated encryption; never ECB,
  never unauthenticated CBC. **Hashing**: SHA-256+; passwords via a KDF
  (the one-shot `Rfc2898DeriveBytes.Pbkdf2(password, salt, iterations, HashAlgorithmName.SHA256, length)`,
  or Argon2/bcrypt via a library) — never plain MD5/SHA-1 (HIGH).
- **`new Rfc2898DeriveBytes(...)` is the legacy shape.** Every constructor is obsolete from
  .NET 10 (SYSLIB0060: use the static `Pbkdf2`), and the short overloads obsoleted in .NET 7
  (SYSLIB0041) default to **SHA-1 and 1,000 iterations** — measured on .NET 10:
  `new Rfc2898DeriveBytes("pw", salt)` reports `hash=SHA1 iterations=1000`. Name the hash and
  the iteration count explicitly; an inherited constructor call is a weak password store.
- Use ASP.NET Core **Data Protection** for at-rest tokens/cookies rather than hand-rolled crypto —
  and keep the package patched: `Microsoft.AspNetCore.DataProtection` 10.0.0–10.0.6 let attackers
  forge authentication cookies and decrypt protected payloads (CVE-2026-40372, fixed in **10.0.7**).
  Patching alone isn't enough after exposure: forged artifacts stay valid, so revoke the key ring
  (`RevokeAllKeys()`) and rotate tokens/API keys issued during the vulnerable window. Constant-time
  compare (`CryptographicOperations.FixedTimeEquals`) for MACs/tokens. **Several instances need one
  key ring.** Measured on .NET 10: a payload protected under one key directory failed on another
  ("not found in the key ring"), and under another `SetApplicationName` too, which breaks
  antiforgery tokens and auth cookies behind a load balancer. Configure `PersistKeysTo…` (shared
  store), `SetApplicationName` and `ProtectKeysWith…` (without it the key file held the key in
  clear, measured). The antiforgery cookie defaults to `SecurePolicy=None` (read from
  `AntiforgeryOptions`): set `Always`. *(OWASP: CSRF Prevention cheat sheet.)*
- **Post-quantum**: .NET 10 ships PQC in the BCL — `MLKem` (FIPS 203) plus
  `MLDsa`/`SlhDsa`/`CompositeMLDsa` (FIPS 204/205; still `[Experimental]`, SYSLIB5006), backed by
  OpenSSL 3.5+ or Windows CNG with PQC support. For new long-lived signatures/key exchange, plan
  migration on these built-ins rather than unvetted packages.
- **TLS**: never disable validation — `ServerCertificateCustomValidationCallback`
  returning `true` (or `HttpClientHandler` accepting all certs) is HIGH/CRITICAL. A pin is an
  extra check: return `false` unless `errors == SslPolicyErrors.None`, then compare `SHA256.HashData(
  cert.PublicKey.ExportSubjectPublicKeyInfo())` with a set of pins that includes a backup
  (a wrong pin failed the handshake, the right one passed; measured). *(OWASP: Pinning cheat sheet.)*
- **Don't hard-code the protocol version.** `SslProtocols.Tls`/`Tls11` are obsolete from
  .NET 7 (SYSLIB0039) — HIGH. Hard-coding even `Tls12`/`Tls13`, or assigning
  `ServicePointManager.SecurityProtocol`, freezes the app out of whatever the OS enables next
  (CA5398/CA5386) — LOW. Use `SslProtocols.None` to defer to the system default.

## 6. `unsafe` code and P/Invoke

C# is memory-safe until a project opts out. `unsafe` blocks, pointers and `fixed` need
`<AllowUnsafeBlocks>true</AllowUnsafeBlocks>` (default `false`), and so does source-generated
P/Invoke (`[LibraryImport]`, .NET 7+). `[DllImport]` and `Marshal.*` on raw pointers cross
the same boundary. **That one property in a `.csproj` is the signal**: without it a project
has no unsafe code to audit, and with it every `unsafe` block and native signature is audited
with the C rules (buffer lengths, lifetimes, `SetLastError`, string marshalling). The class
is `sota-code-security` rules/06 §3.

## 7. ASP.NET Core defaults that fail open

Each of these compiles, runs and passes a happy-path test. The class is owned elsewhere
(`sota-code-security` rules/05 for cookies, redirects, XSS and CSRF; rules/02 for JWT); this
section is the .NET spelling an auditor has to grep for.

- **Cookies carry no attributes unless you set them.** `Response.Cookies.Append(key, value)`
  emits `key=value; path=/` and nothing else (measured, .NET 10), and a new `CookieOptions` has
  `Secure = false`, `HttpOnly = false`, `SameSite = Unspecified` (read in `CookieOptions.cs`).
  Pass `new CookieOptions { Secure = true, HttpOnly = true, SameSite = SameSiteMode.Lax }` (or
  `Strict`). `CookieBuilder.SecurePolicy` defaults to `SameAsRequest`: behind a TLS-terminating
  proxy without forwarded headers the request looks like HTTP and `Secure` is dropped — use
  `CookieSecurePolicy.Always`.
- **Cookie scope: leave `Domain` unset, and a prefix is not enforced by the framework.** A new
  `CookieOptions` has `Path = "/"` and `Domain = null`, which makes a host-only cookie. Setting
  `Domain` (or `options.Cookie.Domain`) sends the cookie to that domain *and every subdomain* (MDN),
  so leave it null unless the cookie really must be shared. For a cookie the app sets itself, name
  it `__Host-…` with `Secure`, `Path=/` and no `Domain`. The browser then refuses to let a sibling
  subdomain set or overwrite it. ASP.NET Core does not check the prefix. On .NET 10 it emitted
  `__Host-b=v; domain=example.com; path=/; secure` and `__Host-c=v; path=/` with no error
  (measured). The browser then silently drops both cookies, so a broken prefix shows up as a missing
  cookie, not as an exception. The session/auth cookie is `sota-code-security` rules/17. *(OWASP:
  Session Management and Cookie Theft Mitigation cheat sheets; ASVS 5.0 V3.3.)*
- **Forwarded headers set `RemoteIpAddress`.** The middleware trusts `X-Forwarded-*` only from a
  peer in `KnownProxies`/`KnownIPNetworks` (default loopback; `KnownNetworks` is obsolete in .NET 10,
  ASPDEPR005); list your real proxies there. Findings: `.Clear()` of both with nothing re-added,
  `ForwardLimit = null` (default 1; the docs allow `null` only with known proxies set), or
  `ASPNETCORE_FORWARDEDHEADERS_ENABLED=true`, which Microsoft warns does not restrict which IPs
  forwarders are accepted from. Any client then picks its own IP, defeating IP rate limits,
  allowlists and the audit log. Forwarding `X-Forwarded-Host`? Set `AllowedHosts` (empty = all).
  Policy: `sota-network-security` rules/05 R6. *(ASP.NET Core proxy and load balancer docs.)*
- **Open redirect.** `Redirect(url)` / `Results.Redirect(url)` follow any absolute URL. For a
  `returnUrl` use `LocalRedirect` (throws on a non-local URL) or check `Url.IsLocalUrl` first
  (ASP.NET Core "Prevent open redirect attacks"). CA3007 is the analyzer's taint version.
- **Razor encodes; three constructs opt out.** `@value` is HTML-encoded; `Html.Raw(x)`
  (*"without HTML-encoding"*, `IHtmlHelper`), `new HtmlString(x)` and Blazor `(MarkupString)x`
  emit it verbatim. On user-influenced data each is stored XSS — sanitize with an allowlist
  sanitizer first, or don't.
- **A state-changing action without a verb attribute answers GET, and GET skips antiforgery.**
  An attribute-routed action with `[Route]` and no `[HttpPost]` accepts every method; minimal-API
  `app.Map(...)` likewise. The antiforgery filters treat GET, HEAD, OPTIONS and TRACE as safe
  (`SafeHttpMethods.IsSafe`). Measured on .NET 10 with `AutoValidateAntiforgeryToken` applied
  globally: a `[Route]`-only delete action returned **200 to a token-less GET** and 400 to a
  token-less POST, so the CSRF defence was bypassed by changing the verb. Put an explicit
  `[HttpPost]`/`[HttpDelete]` (or `MapPost`/`MapDelete`) on every mutation. CA5395 flags the
  missing attribute (with security rules enabled, `rules/06` §2) **only in a project where some
  controller carries `[ValidateAntiForgeryToken]`**: measured, the same code with the filter
  registered globally raised neither CA5395 nor CA5391 under `AnalysisModeSecurity=All`, and
  adding one attributed controller made both fire. Do not read the analyzer's silence as a pass.
- **JWT bearer validation is on by default — the finding is turning it off.**
  `TokenValidationParameters` defaults `ValidateIssuer`, `ValidateAudience`, `ValidateLifetime`,
  `RequireExpirationTime` and `RequireSignedTokens` to `true` (read in the IdentityModel
  source). Setting any to `false` (CA5404), an `AudienceValidator`/`LifetimeValidator` that
  always returns `true` (CA5405), or a custom `SignatureValidator` (it replaces signature
  checking) is HIGH unless the code says why. `ValidateIssuerSigningKey` defaults to `false`:
  it validates the *key* that verified the signature, which matters when a token can carry its
  own key (the source's example is X509Data) — set it `true` there.
- **The Development environment is a debug mode, and it only takes one variable.** The environment
  comes from `DOTNET_ENVIRONMENT` or `ASPNETCORE_ENVIRONMENT`. Under `WebApplication` the `DOTNET_`
  value wins. When neither is set the environment is `Production` (Microsoft docs, and measured: the
  SDK container image sets neither). In `Development`, `WebApplication` adds the developer exception
  page **without any `UseDeveloperExceptionPage()` call**. Measured on .NET 10: with the same
  binary, a throwing endpoint returned an empty 500 in Production. With
  `ASPNETCORE_ENVIRONMENT=Development` it returned the exception message, the stack trace and the
  source path and line. Anything gated on `IsDevelopment()` switches on as well: the `webapi`
  template's `MapOpenApi()`, `EnableSensitiveDataLogging` (§4) and seed or reset endpoints. So the
  finding is `Development` in a Dockerfile `ENV`, a compose or Kubernetes manifest, a `web.config`,
  or `<EnvironmentName>` in a publish profile. `launchSettings.json` is fine: Microsoft documents it
  as used only on the local machine and not deployed. `dotnet run` and `dotnet watch` are
  development launchers that apply its first profile, so a production container runs the published
  DLL (`dotnet app.dll`). Enforce it at startup: in a Release build, fail fast when
  `builder.Environment.IsDevelopment()` is true (an `#if !DEBUG` guard), and log `EnvironmentName`.
  *(OWASP: Error Handling cheat sheet; Secure Headers Project; ASVS 5.0 V13.4.)*

## 8. Legacy ASP.NET (`System.Web`) configuration

Audit the effective chain as one unit, since a child file can undo its parent: `machine.config`,
root `web.config`, IIS `applicationHost.config`, then each app and folder `web.config`. Read
`<compilation debug>`, `<trace>`, `<customErrors>` (default `RemoteOnly`; `Off` shows details to all),
`<httpCookies>`, `<sessionState>`, `maxRequestLength`, `<authentication>`, `<authorization>`,
`<identity impersonate>`, `<connectionStrings>` (encrypt it) and `system.webServer/security`. Lock
what children must not weaken with `<location allowOverride="false">` (default `true`), restrict
file ACLs, drop unused sections. Request validation backs up encoding and input validation, never
replaces them; turning it off is a finding: `validateRequest="false"` (`<pages>` or `@ Page`,
honoured only under `requestValidationMode="2.0"`), that downgrade itself, or `0.0` (off app-wide).
So is `enableEventValidation="false"`, which Microsoft strongly advises against. Each exception
names its page and reason. *(OWASP: Code Review Guide v2; .NET Security cheat sheet.)*

## Audit checklist

- [ ] **`unsafe` / P/Invoke — HIGH on input-derived lengths** (§6) —
      `grep -rnE 'AllowUnsafeBlocks' --include='*.csproj' --include='*.props' .` ;
      `grep -rnE '(^|[^[:alnum:]_])unsafe([^[:alnum:]_]|$)|(^|[^[:alnum:]_])fixed[[:space:]]*\(|\[(DllImport|LibraryImport)|Marshal\.(Copy|PtrToStructure|AllocHGlobal|ReadIntPtr)' --include='*.cs' .`
- [ ] **SQL injection — CRITICAL** —
      `grep -rnE 'FromSqlRaw|ExecuteSqlRaw|SqlQueryRaw' --include='*.cs' .` (each SQL argument must be a constant) ;
      `grep -rnE '(FromSqlRaw|ExecuteSqlRaw|SqlQueryRaw)(Async)?(<[^>]*>)?\([^)]*(\+|\$)|CommandText[[:space:]]*=[^;]*(\+|\$")|new SqlCommand\([^)]*(\+|\$")' --include='*.cs' .`
      ; `grep -rnE '\.(Query|Execute)[A-Za-z]*(<[^>]*>)?\([[:space:]]*(\$@?|@\$)?"[^"]*\{' --include='*.cs' .`
      (Dapper `Query*`/`Execute*` with interpolated SQL; a raw `"""` literal or SQL built earlier escapes all three)
- [ ] **Deserialization — CRITICAL** —
      `grep -rnE 'BinaryFormatter|NetDataContractSerializer|LosFormatter|SoapFormatter|ObjectStateFormatter' --include='*.cs' .` ; `grep -rnE 'TypeNameHandling\.(Auto|All|Objects|Arrays)' --include='*.cs' .`
- [ ] **XXE / command / path — HIGH/CRITICAL** —
      `grep -rnE 'DtdProcessing|XmlResolver|new XmlDocument|XmlReader|XmlTextReader|new XPathDocument\(|XslCompiledTransform' --include='*.cs' . | head` ; `grep -rnE 'Process\.Start|ProcessStartInfo|UseShellExecute' --include='*.cs' . | head`
- [ ] **Auth / CORS / antiforgery — HIGH** (§4) —
      `grep -rnE 'AllowAnyOrigin|AllowAnyHeader|AllowAnyMethod' --include='*.cs' .` ;
      `grep -rn 'FallbackPolicy' --include='*.cs' . || echo "no FallbackPolicy: an endpoint without [Authorize] is public"` ;
      `grep -rLE '\[Authorize|\[AllowAnonymous' --include='*Controller.cs' .` (no attribute at all) ;
      `grep -rnE '\.Map(Get|Post|Put|Delete|Patch|Methods|Group)?\(' --include='*.cs' . | grep -vE 'RequireAuthorization|AllowAnonymous'`
      (minimal APIs; a `.RequireAuthorization()` on a later line or the parent `MapGroup` is unseen) ;
      `grep -rnE 'PersistKeysTo|ProtectKeysWith' --include='*.cs' . || echo "key ring not shared or protected (§5) — MEDIUM with >1 instance"`
- [ ] **Crypto misuse — HIGH** —
      `grep -rnE '\bnew Random\(|System\.Random' --include='*.cs' . | grep -iE 'token|key|iv|salt|nonce|password|secret'` ; `grep -rnE 'MD5|SHA1|TripleDES|\bDES\b|CipherMode\.ECB' --include='*.cs' .` ;
      `grep -rnE 'ServerCertificateCustomValidationCallback|RemoteCertificateValidationCallback' --include='*.cs' . | head`
- [ ] **Secrets in config/source — HIGH** —
      `grep -rniE '"?(password|pwd|secret|apikey|api_key|connectionstrings?)"?[[:space:]]*[=:]' --include='appsettings*.json' --include='*.cs' .` (a `"ConnectionStrings":` hit: read the section for `Password=`/`Pwd=`)
- [ ] **Data Protection package patch level — HIGH** (§5) —
      `grep -rn 'Microsoft\.AspNetCore\.DataProtection' --include='*.csproj' --include='packages.lock.json' --include='Directory.Packages.props' .`
      (10.0.0–10.0.6 = CVE-2026-40372, need 10.0.7+; if exposed while vulnerable: key ring revoked
      and tokens rotated?). Runtime and Kestrel patch levels are in the `rules/06` checklist
- [ ] **Static security analysis: enable security CA rules + a SAST (rules/06)**
- [ ] **BinaryFormatter re-armed on .NET 9+ — CRITICAL until justified** (§2) — either half of
      the opt-back-in:
      `grep -rnE 'EnableUnsafeBinaryFormatterSerialization|System\.Runtime\.Serialization\.Formatters"' --include='*.csproj' --include='*.props' --include='*.json' --include='*.cs' .`
      (package reference, lock-file entry, MSBuild property or AppContext switch)
- [ ] **DataSet/DataTable as a deserializer — HIGH/CRITICAL on an input path** (§2) —
      `grep -rnE '\.ReadXml(Schema)?\(|AllowArbitraryDataSetTypeInstantiation|DataSetDefaultAllowedTypes|JavaScriptSerializer|SimpleTypeResolver|Deserialize(Object)?<Data(Set|Table)>' --include='*.cs' --include='*.json' --include='*.config' .`
      (trace each to its source: untrusted input = finding)
- [ ] **Path traversal and Zip Slip — HIGH** (§3) —
      `grep -rnE 'ExtractToFile\(|Combine\([^)]*\.FullName' --include='*.cs' .` (per-entry
      extraction: no boundary check) ; `grep -rnE 'Path\.Combine\(' --include='*.cs' .` (a rooted
      later argument discards the root: for each call fed by a request, is the result passed
      through `GetFullPath` and prefix-checked against root + separator?)
- [ ] **Regex without a timeout on untrusted input — MEDIUM (ReDoS)** (§3) —
      `grep -rnE 'new Regex\(|Regex\.(IsMatch|Match|Matches|Replace|Split)\(|\[GeneratedRegex\(' --include='*.cs' . | grep -vE 'TimeSpan|matchTimeout|NonBacktracking'` ; `grep -rn 'REGEX_DEFAULT_MATCH_TIMEOUT' .` (a hit sets a process-wide default and
      covers the rest); a pattern built from input without `Regex.Escape` is HIGH
- [ ] **Validation regex with a `$` anchor instead of `\z` — MEDIUM** (§3) —
      `grep -rnE '[^@(,[:space:]$]\$"' --include='*.cs' . | grep -v 'RegularExpression('`
      (a literal ending in `$` also accepts a trailing `\n`, so for a validator the fix is `\A…\z`;
      `[RegularExpression]` requires the match to span the whole value, so it is excluded). Also read
      every `IsMatch` used as an allowlist for a missing anchor or `RegexOptions.Multiline`
- [ ] **Password KDF on the legacy constructor — HIGH** (§5) —
      `grep -rnE 'new Rfc2898DeriveBytes\(|PasswordDeriveBytes' --include='*.cs' .` (short overloads = SHA-1 × 1,000; want the static `Rfc2898DeriveBytes.Pbkdf2` with explicit hash and iterations)
- [ ] **Hard-coded TLS protocol — HIGH for Tls/Tls11/Ssl3, LOW for Tls12/Tls13** (§5) —
      `grep -rnE 'SslProtocols\.(Ssl2|Ssl3|Tls|Tls11|Tls12|Tls13|Default)([^[:alnum:]]|$)|SecurityProtocolType\.|ServicePointManager\.SecurityProtocol' --include='*.cs' .` (want `SslProtocols.None`)
- [ ] **Cookies without attributes — MEDIUM (HIGH for a session cookie)** (§7) —
      `grep -rnE 'Cookies\.Append\([^,]+,[^,]+\)|(Secure|HttpOnly)[[:space:]]*=[[:space:]]*false|CookieSecurePolicy\.(None|SameAsRequest)|SameSiteMode\.None' --include='*.cs' .`
      (two-argument `Append` emits no Secure/HttpOnly/SameSite; a value containing a comma
      escapes the first pattern, so read every `Cookies.Append` on an auth path)
- [ ] **Open redirect — MEDIUM** (§7) —
      `grep -rnE '(^|[^[:alnum:]_])(Redirect|RedirectPermanent|RedirectPreserveMethod|RedirectPermanentPreserveMethod)\([[:space:]]*[^")[:space:]]' --include='*.cs' .` (non-literal target: want `LocalRedirect` or a preceding `Url.IsLocalUrl`)
- [ ] **Raw HTML output — HIGH on user data (stored XSS)** (§7) —
      `grep -rnE 'Html\.Raw\(|(new |\()(HtmlString|MarkupString)[()]' --include='*.cs' --include='*.cshtml' --include='*.razor' .`
- [ ] **Mutations reachable by GET, so antiforgery never runs — HIGH** (§7) —
      `grep -rnE '\.Map\("|IgnoreAntiforgeryToken' --include='*.cs' .` (any-verb minimal
      endpoints; opted-out antiforgery) ;
      `grep -rnE -A2 '^[[:space:]]*\[Route\(' --include='*.cs' . | grep -E '(IActionResult|ActionResult|Task<)'`
      (action-level `[Route]` with no verb attribute — confirm there is no `[HttpPost]` etc.;
      conventional-routed actions are invisible to grep: CA5395 finds them, but only where a
      controller carries `[ValidateAntiForgeryToken]` — a global filter keeps it silent)
- [ ] **Secrets reaching logs — HIGH** (§4) —
      `grep -rnE 'EnableSensitiveDataLogging\([[:space:]]*(true)?[[:space:]]*\)' --include='*.cs' .`
      (confirm each is behind an `IsDevelopment()` check) ;
      `grep -rniE '(log|logger)\.(log|logtrace|logdebug|loginformation|logwarning|logerror|logcritical)\([^;]*(passw|secret|token|api_?key|credential)' --include='*.cs' .`
      (read the arguments: a credential passed to the call is the finding, while message
      text that only *names* one, such as "password reset for {User}", also matches) ;
      `grep -rniE 'record[[:space:]]+(struct[[:space:]]+|class[[:space:]]+)?[a-z0-9_]+[[:space:]]*\([^)]*(passw|secret|token|api_?key|credential)' --include='*.cs' .`
      (a positional record holding a credential: its `ToString` prints it unless
      `PrintMembers` is overridden)
- [ ] **JWT validation switched off — HIGH** (§7) —
      `grep -rnE '(RequireExpirationTime|RequireSignedTokens|ValidateAudience|ValidateIssuer|ValidateLifetime)[[:space:]]*=[[:space:]]*false|(AudienceValidator|LifetimeValidator|IssuerValidator|SignatureValidator)[[:space:]]*=' --include='*.cs' .` (a custom validator delegate must be read: `=> true` is CA5405)
- [ ] **SSRF: outbound request to a caller-chosen URL — HIGH (CRITICAL where the cloud
      metadata endpoint 169.254.169.254 is reachable)** (§3) —
      `grep -rnE '\.(Get|GetString|GetStream|GetByteArray|GetFromJson|Post|PostAsJson|Put|PutAsJson|Patch|Delete)Async(<[^>]*>)?\([[:space:]]*([^"$)[:space:]]|\$"[^/])|new HttpRequestMessage\([^,]+,[[:space:]]*([^"$)[:space:]]|\$"[^/])|WebRequest\.Create\(' --include='*.cs' .`
      (a non-literal, non-relative destination; trace each one to its source, since a cache's
      `GetAsync(key)` also matches). For every hit fed by a request, check three things.
      `grep -rnE 'ConnectCallback|UseProxy|AllowAutoRedirect' --include='*.cs' .` has to show
      a connect-time address check. The handler must not route through a proxy. Redirects must be
      disabled or seen by that check. No hits means there is no DNS-rebinding defence.
- [ ] **Dynamic code evaluation from input — CRITICAL (runtime code generation, dynamic LINQ,
      reflection by name)** (§3) —
      `grep -rnE 'CSharpScript\.|CSharpCompilation\.Create|Assembly\.Load(From|File)?\([^"]|System\.Linq\.Dynamic\.Core|DynamicExpressionParser|Type\.GetType\([^")]|GetMethod\([^")]|CompileAssemblyFrom(Source|Dom|File)|Expression\.Lambda|GetObjectData\(' --include='*.cs' --include='*.csproj' .`
      (trace every hit to its source: a request-derived script, type or method name is the
      finding; a `System.Linq.Dynamic.Core` version below 1.6.0 is CVE-2024-51417; a
      reference-stripped `ScriptOptions` is not a mitigation; a `GetObjectData` hit: read each
      `AddValue` for a secret)
- [ ] **Cookie attribute scope: `Domain` set, or a `__Host-` cookie that breaks the prefix rules
      — MEDIUM** (§7) —
      `grep -rnE '(^|[^[:alnum:]_])Domain[[:space:]]*=[[:space:]]*[^=[:space:]]|"__Host-' --include='*.cs' . | grep -vE '(^|[^[:alnum:]_])Domain[[:space:]]*=[[:space:]]*null'`
      (confirm a `Domain` hit is a cookie and must really span subdomains; every `__Host-`
      cookie needs `Secure = true`, `Path = "/"` and no `Domain`, since ASP.NET Core emits it either way)
- [ ] **`ASPNETCORE_ENVIRONMENT=Development` or `UseDeveloperExceptionPage` in production — HIGH** (§7) —
      `grep -rnE 'UseDeveloperExceptionPage|(ASPNETCORE|DOTNET)_ENVIRONMENT[^=:]{0,12}[=:[:space:]][[:space:]]*"?Development|EnvironmentName[[:space:]]*=[[:space:]]*(Environments\.Development|"Development")|<EnvironmentName>Development' --include='*.cs' --include='*.json' --include='*.yml' --include='*.yaml' --include='Dockerfile*' --include='*.config' --include='*.pubxml' --include='*.csproj' . | grep -v 'launchSettings\.json'`
      (the explicit call must sit behind `IsDevelopment()`; a Kubernetes `name:`/`value:` pair
      spans two lines and escapes the pattern, so read the deployment manifests too)
- [ ] **ViewState MAC off, or a fixed or published `machineKey` — CRITICAL; encryption `Never` —
      MEDIUM** (§2) —
      `grep -rniE 'enableViewStateMac[[:space:]]*=[[:space:]]*"?false|viewStateEncryptionMode[[:space:]]*=[[:space:]]*"?never|(validationKey|decryptionKey)[[:space:]]*=[[:space:]]*"[0-9a-f]{16}' --include='*.config' --include='*.aspx' --include='*.ascx' --include='*.master' .`
      (a hex key in the repo is the finding whatever its origin; `AutoGenerate,IsolateApps` does
      not match and is fine; a `<machineKey>` split across lines needs a read)
- [ ] **Json.NET type handling without a strict binder, type names from storage, gadget
      assemblies — HIGH/CRITICAL** (§2) —
      `grep -rnE 'TypeNameHandling\.(Auto|All|Objects|Arrays)|SerializationBinder[[:space:]]*=|[Tt]ypeName\.(Contains|StartsWith|EndsWith)\(' --include='*.cs' .`
      (a file with type handling but no `SerializationBinder =` is CA2327; a binder matching by
      prefix or substring is a bypass) ;
      `grep -rnE 'new (DataContractJsonSerializer|DataContractSerializer|XmlSerializer)\([[:space:]]*(Type\.GetType\(|[a-z_][A-Za-z0-9_]*[[:space:]]*[,)])' --include='*.cs' .`
      (a runtime `Type`: trace where it came from; `typeof(...)` is fine) ;
      `grep -rnE 'ObjectDataProvider|ResourceDictionary|System\.Management\.Automation|Microsoft\.PowerShell\.SDK|AssemblyInstaller|WorkflowDesigner|BindingSource|DataViewManager|<UseWPF>true|<UseWindowsForms>true' --include='*.cs' --include='*.csproj' --include='*.xaml' .`
      (a finding only in a service that deserializes type-named input)
- [ ] **Untrusted JSON on lenient `System.Text.Json` defaults — MEDIUM** (§2) —
      `grep -rnE '(JsonSerializer\.Deserialize|ReadFromJson|GetFromJson)(Async)?(<[^>]*>)?\(' --include='*.cs' . | grep -vE 'Strict|AllowDuplicateProperties|UnmappedMemberHandling'` (named options instance: read how it was built)
- [ ] **Spoofable client IP via forwarded headers — HIGH where the IP gates access, limits or audit** (§7) —
      `grep -rnE '(KnownProxies|KnownIPNetworks|KnownNetworks)\.Clear\(\)|ForwardLimit[[:space:]]*=[[:space:]]*null|FORWARDEDHEADERS_ENABLED[^=:]{0,3}[=:[:space:]][[:space:]]*"?[Tt]rue' --include='*.cs' --include='*.json' --include='*.yml' --include='*.yaml' --include='Dockerfile*' --include='*.env' --include='.env*' .`
      (a `Clear()` needs the real proxy `Add`ed after it; read each `UseForwardedHeaders` setup for its proxy list and `AllowedHosts`)
- [ ] **Legacy `System.Web` validation off, debug or trace on, config not locked — HIGH** (§8) —
      `grep -rniE 'validateRequest[[:space:]]*=[[:space:]]*"?false|requestValidationMode[[:space:]]*=[[:space:]]*"?[0-3][.]|enableEventValidation[[:space:]]*=[[:space:]]*"?false|debug[[:space:]]*=[[:space:]]*"?true|<trace[^>]*enabled[[:space:]]*=[[:space:]]*"?true|customErrors[^>]*mode[[:space:]]*=[[:space:]]*"?off' --include='*.config' --include='*.aspx' --include='*.ascx' --include='*.master' .`
      (each needs a named page and reason) ; `grep -rniE 'allowOverride[[:space:]]*=[[:space:]]*"?false' --include='*.config' . || echo "nothing locked: a child web.config can weaken any setting"`
