# 04 — Security: injection, deserialization, ASP.NET Core, crypto

The CLR is memory-safe, so the dominant .NET vulnerabilities are **injection,
unsafe deserialization, auth gaps, and crypto misuse**. Treat every byte from
network/file/DB/config as untrusted. Reference:
[OWASP .NET cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/DotNet_Security_Cheat_Sheet.html),
[ASP.NET Core security](https://learn.microsoft.com/en-us/aspnet/core/security/).

## 1. SQL injection

- **EF Core**: LINQ is parameterized and safe. `FromSql`/`ExecuteSql` (the
  *interpolated* `FromSqlInterpolated`-style) parameterize interpolated values.
  **`FromSqlRaw`/`ExecuteSqlRaw` with string concatenation/interpolation is
  CRITICAL** — they don't parameterize a built string.
- **Dapper / ADO.NET**: always pass parameters (`new { id }` / `SqlParameter`),
  never concatenate input into the SQL text. Identifiers (table/column/ORDER BY)
  can't be parameters — allowlist them.

## 2. Deserialization

- **`BinaryFormatter` is removed in .NET 9+** (the API throws
  `PlatformNotSupportedException`); it was a notorious RCE vector. Never
  reintroduce it (or `NetDataContractSerializer`, `SoapFormatter`, `LosFormatter`,
  `ObjectStateFormatter`) — CRITICAL on sight.
- **JSON**: prefer `System.Text.Json` with known types. Newtonsoft
  `TypeNameHandling.Auto/All/Objects` (or `System.Text.Json` with an
  unrestricted polymorphic type resolver) on untrusted input enables gadget-style
  RCE — don't. Bind to explicit DTOs.
- **`XmlSerializer`/`DataContractSerializer`** with attacker-controlled types is
  risky; disable DTD processing on XML readers (XXE) — `XmlReaderSettings {
  DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null }`.

## 3. Command / path / other injection

- **OS command**: avoid shelling out; if you must, use `ProcessStartInfo` with
  `ArgumentList` (no `UseShellExecute`, no concatenated `Arguments`/shell).
- **Path traversal**: combine with a known root and verify the resolved
  `Path.GetFullPath` stays under it; reject `..`. Don't pass user input straight
  to file APIs.
- **LDAP/XPath/regex (ReDoS)**: parameterize/escape; bound regex with timeouts
  (`Regex` `matchTimeout`) on untrusted input.

## 4. ASP.NET Core authn/authz & web

- **AuthZ on every non-public endpoint**: `[Authorize]`/policies/role checks /
  endpoint authorization; default-deny. Missing auth is HIGH.
- **Antiforgery** for cookie-authenticated state-changing requests
  (`[ValidateAntiForgeryToken]` / the antiforgery middleware). **CORS** locked
  to specific origins — never `AllowAnyOrigin()` with credentials.
- Validate/bind model input (data annotations / explicit validation); don't
  over-post (use DTOs/`[Bind]` allowlists, not the EF entity directly). Set
  security headers/HSTS; don't leak stack traces in production responses.
- **Secrets**: never in source/`appsettings.json` committed to git — use user
  secrets (dev), env, or a vault (`sota-secrets-management`); don't log them.
- **Runtime patch level is an audit surface**: the memory-safe runtime's
  residual risk includes framework CVEs — e.g. CVE-2025-55315 (Kestrel HTTP
  request smuggling, fixed in 8.0.21/9.0.10/10.0 RC2) and CVE-2026-45591
  (SignalR/Blazor Server MessagePack nested-array DoS, fixed in
  8.0.28/9.0.17/10.0.9, June 2026). Self-contained/AOT-published apps embed
  the framework — they need a rebuild and redeploy, not just host patching.

## 5. Cryptography & transport

- **Randomness**: `System.Security.Cryptography.RandomNumberGenerator` (e.g.
  `RandomNumberGenerator.GetBytes`) for tokens/keys/IVs/salts — never
  `System.Random` (HIGH).
- **Symmetric**: AES-GCM (`AesGcm`) for authenticated encryption; never ECB,
  never unauthenticated CBC. **Hashing**: SHA-256+; passwords via a KDF
  (`Rfc2898DeriveBytes`/PBKDF2, or Argon2/bcrypt via a library) — never plain
  MD5/SHA-1 (HIGH).
- Use ASP.NET Core **Data Protection** for at-rest tokens/cookies rather than
  hand-rolled crypto — and keep the package patched:
  `Microsoft.AspNetCore.DataProtection` 10.0.0–10.0.6 let attackers forge
  authentication cookies and decrypt protected payloads (CVE-2026-40372,
  fixed in **10.0.7**). Patching alone isn't enough after exposure: forged
  artifacts stay valid, so revoke the key ring (`RevokeAllKeys()`) and rotate
  tokens/API keys issued during the vulnerable window. Constant-time compare
  (`CryptographicOperations.FixedTimeEquals`) for MACs/tokens.
- **TLS**: never disable validation — `ServerCertificateCustomValidationCallback`
  returning `true` (or `HttpClientHandler` accepting all certs) is HIGH/CRITICAL.

## Audit checklist

```bash
# SQL injection — CRITICAL
grep -rnE 'FromSqlRaw|ExecuteSqlRaw' --include='*.cs' . | head
grep -rnE '(FromSqlRaw|ExecuteSqlRaw|CommandText|new SqlCommand)\([^)]*(\+|\$")' --include='*.cs' .
grep -rnE '\.Query[^(]*\(\s*\$?"[^"]*\{' --include='*.cs' .       # Dapper string-interpolated SQL

# Deserialization — CRITICAL
grep -rnE 'BinaryFormatter|NetDataContractSerializer|LosFormatter|SoapFormatter|ObjectStateFormatter' --include='*.cs' .
grep -rnE 'TypeNameHandling\.(Auto|All|Objects|Arrays)' --include='*.cs' .

# XXE / command / path — HIGH/CRITICAL
grep -rnE 'DtdProcessing|XmlResolver|new XmlDocument|XmlReader' --include='*.cs' . | head
grep -rnE 'Process\.Start|ProcessStartInfo|UseShellExecute' --include='*.cs' . | head

# Auth / CORS / antiforgery — HIGH
grep -rnE 'AllowAnyOrigin|AllowAnyHeader|AllowAnyMethod' --include='*.cs' .
grep -rnLE '\[Authorize\]|RequireAuthorization|\[AllowAnonymous\]' --include='*Controller.cs' . | head  # endpoints w/o auth?

# Crypto misuse — HIGH
grep -rnE '\bnew Random\(|System\.Random' --include='*.cs' . | grep -iE 'token|key|iv|salt|nonce|password|secret'
grep -rnE 'MD5|SHA1|TripleDES|\bDES\b|CipherMode\.ECB' --include='*.cs' .
grep -rnE 'ServerCertificateCustomValidationCallback|RemoteCertificateValidationCallback' --include='*.cs' . | head

# Secrets in config/source — HIGH
grep -rniE '(password|pwd|secret|apikey|api_key|connectionstring)\s*[=:]' appsettings*.json --include='*.cs' . | head

# Vulnerable framework/package patch levels — HIGH
grep -rnE 'Microsoft\.AspNetCore\.DataProtection' --include='*.csproj' --include='packages.lock.json' .  # 10.0.0–10.0.6 = CVE-2026-40372 (need 10.0.7+); if exposed while vulnerable: key ring revoked + tokens rotated?
dotnet --list-runtimes  # ASP.NET Core < 8.0.21/9.0.10 (CVE-2025-55315) or < 8.0.28/9.0.17/10.0.9 (CVE-2026-45591)? Check container base-image tags; self-contained/AOT apps need rebuild

# Static security analysis: enable security CA rules + a SAST (rules/06)
```
