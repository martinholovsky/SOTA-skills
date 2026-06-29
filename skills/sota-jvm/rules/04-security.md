# 04 — Security: deserialization, injection, XXE, JNDI, crypto

The JVM removes memory-corruption bugs, so the dominant RCE classes are
**unsafe deserialization, injection, and lookup/eval of untrusted data**, plus
crypto misuse. Treat every byte from network/file/DB/IPC as hostile.
Standards: [SEI CERT Oracle Java](https://wiki.sei.cmu.edu/confluence/display/java),
[OWASP Deserialization](https://cheatsheetseries.owasp.org/cheatsheets/Deserialization_Cheat_Sheet.html),
[OWASP Java](https://cheatsheetseries.owasp.org/).

## 1. Deserialization — the signature Java RCE

- **Never** call `ObjectInputStream.readObject()` on untrusted bytes. Gadget
  chains in common libraries turn deserialization into arbitrary code execution
  (the entire `ysoserial` family). This is CRITICAL on sight.
- Prefer data formats with no code-execution semantics: JSON/protobuf/Avro with
  an explicit schema, deserialized into known DTOs. Disable polymorphic type
  handling unless allowlisted (Jackson `enableDefaultTyping`/`@JsonTypeInfo`
  with untrusted input is the JSON equivalent of the gadget problem).
- If native serialization is unavoidable, install a strict **`ObjectInputFilter`**
  allowlist (JEP 290, `setObjectInputFilter` / `jdk.serialFilter`) limiting
  classes and graph size. Treat it as defense-in-depth, not a fix.

## 2. Injection (SQL, command, LDAP, expression)

- **SQL/JPQL/HQL**: parameterized `PreparedStatement` / bound JPA parameters
  only. String concatenation into a query is CRITICAL — no exceptions for
  "internal" values. `ORDER BY`/identifiers can't be bound: allowlist them.
- **OS command**: `ProcessBuilder` with an argument **list** and no shell; never
  `Runtime.exec("sh -c " + input)`. Validate/allowlist the program.
- **LDAP/JNDI**: never pass attacker-controlled names to `Context.lookup` —
  this is the Log4Shell (CVE-2021-44228) class. Disable remote-codebase loading;
  validate URLs against an allowlist; keep logging libs patched.
- **Expression/script eval**: SpEL, OGNL, MVEL, `ScriptEngine` (Nashorn/JS),
  Spring expression contexts, and template engines evaluating user input are
  RCE. Don't evaluate untrusted expressions; sandbox or remove the capability.

## 3. XML and XXE

- Disable DTDs and external entities on every parser
  (`DocumentBuilderFactory`, `SAXParserFactory`, `XMLInputFactory`,
  transformers):
  `setFeature("http://apache.org/xml/features/disallow-doctype-decl", true)`,
  disable `external-general-entities`/`external-parameter-entities`,
  `setXIncludeAware(false)`, `setExpandEntityReferences(false)` (OWASP XXE
  cheat sheet). Same care for YAML (`SnakeYAML` `SafeConstructor`) and XML-based
  formats.

## 4. Cryptography (the JCA)

- Use vetted algorithms via the JCA; **don't roll your own**.
  - Symmetric: AES-256 in an authenticated mode (**GCM**); never ECB, never
    unauthenticated CBC. Unique random nonce per message.
  - Randomness: **`SecureRandom`** for keys/tokens/IVs/salts — never
    `java.util.Random`/`Math.random`/`ThreadLocalRandom`. Don't seed
    `SecureRandom` with a fixed value.
  - Hashing: SHA-256+ for integrity; **password hashing** uses Argon2/bcrypt/
    PBKDF2 (a KDF), never plain SHA/MD5. MD5/SHA-1 for security is HIGH.
  - Constant-time comparison for MACs/tokens (`MessageDigest.isEqual`), never
    `String.equals`/`Arrays.equals` on secrets (timing leak).
- TLS: use the platform default protocols/cipher suites (TLS 1.2+/1.3); **never**
  install an all-trusting `TrustManager` or `HostnameVerifier` that returns
  true — disabling certificate validation is HIGH/CRITICAL. See
  `sota-code-security` rules/04 and `sota-network-security`.

## 5. Other boundaries

- **Path traversal**: canonicalize and verify the result stays under an allowed
  root (`Path.normalize()` + `startsWith`); reject `..`. Use `java.nio.file`.
- **SSRF / URL fetch**: validate/allowlist destinations; block internal/metadata
  ranges (see `sota-code-security`).
- **Secrets**: never hardcode; load from a secret manager/env; don't log them;
  prefer `char[]`/`byte[]` you can wipe over `String` for passwords (`rules`
  cross-ref `sota-secrets-management`).
- **Spring/framework**: keep dependencies patched (Spring4Shell, Log4Shell were
  dependency CVEs — `rules/06`); enable CSRF/auth correctly (`sota-code-security`).

## Audit checklist

```bash
# Deserialization — CRITICAL
grep -rnE 'readObject\(|ObjectInputStream|XMLDecoder' --include='*.java' .
grep -rnE 'enableDefaultTyping|@JsonTypeInfo|activateDefaultTyping' --include='*.java' .  # Jackson polymorphic

# Injection — CRITICAL/HIGH
grep -rnE '(createQuery|createNativeQuery|prepareStatement|executeQuery|executeUpdate)\([^?)]*\+' --include='*.java' .
grep -rnE 'Runtime\.getRuntime\(\)\.exec|new ProcessBuilder' --include='*.java' --include='*.kt' .
grep -rnE 'ctx\.lookup|InitialContext|new InitialDirContext' --include='*.java' .   # JNDI/Log4Shell-class
grep -rnE 'SpelExpressionParser|Ognl|ScriptEngineManager|getEngineByName' --include='*.java' .

# XXE — CRITICAL (verify DTDs disabled)
grep -rnE 'DocumentBuilderFactory|SAXParserFactory|XMLInputFactory|TransformerFactory|SAXReader' --include='*.java' .
grep -rn 'disallow-doctype-decl\|setExpandEntityReferences\|SafeConstructor' --include='*.java' . || echo "verify XXE hardening"

# Crypto misuse — HIGH
grep -rnE 'new Random\(|Math\.random|ThreadLocalRandom' --include='*.java' . | grep -iE 'key|token|iv|salt|nonce|secret'
grep -rnE '"(MD5|SHA-?1|DES|RC4)"|/ECB/|Cipher\.getInstance\("AES"\)' --include='*.java' --include='*.kt' .
grep -rnE 'TrustManager|HostnameVerifier|checkServerTrusted' --include='*.java' .   # all-trusting?
grep -rn 'Arrays.equals\|\.equals(' --include='*.java' . | grep -iE 'mac|hmac|token|signature|digest'

# Static security analysis
#   SpotBugs + Find-Sec-Bugs; OWASP dependency-check / OSV-Scanner (rules/06)
```
