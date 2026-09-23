# 04 — Security: deserialization, injection, XXE, JNDI, crypto, the web layer

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
- **Framework surfaces deserialize too** — gadget entry points are shifting from
  direct `readObject` to message converters and persisted state. Spring JMS
  `MappingJackson2MessageConverter` instantiated attacker-chosen classes from
  message type headers (CVE-2026-41855; fix adds `setTrustedPackages(...)`), and
  Spring Statemachine's Kryo persistence lacked a class allowlist
  (CVE-2026-41862). Require an explicit type allowlist on any converter or
  persistence layer that resolves classes from data.

## 2. Injection (SQL, command, LDAP, expression)

- **SQL/JPQL/HQL**: parameterized `PreparedStatement` / bound JPA parameters
  only. String concatenation into a query is CRITICAL — no exceptions for
  "internal" values. `ORDER BY`/identifiers can't be bound: allowlist them.
- **OS command**: `ProcessBuilder` with an argument **list** and no shell; never
  `Runtime.exec("sh -c " + input)`. Validate/allowlist the program.
  **`Runtime.getRuntime().exec(String)` tokenizes its argument on whitespace** — it is
  the `shell:true` of Java, and one tainted value carrying a space becomes two
  arguments. The JDK agrees: the three `String`-taking overloads are
  `@Deprecated(since="18", forRemoval=false)`; the `String[]` ones are not (read off
  `Runtime.class` on Temurin 25.0.3, 2026-08-20). Any surviving `exec(String)` call is
  a finding on the deprecation alone — grep below.
  **Deadlines**: `waitFor(t, unit)` returns `false` on timeout and fires on schedule
  (2003 ms on a 2 s budget, measured) — but it kills **nothing**, and `destroy()` reaps
  only the direct child, orphaning any grandchild holding the inherited pipe. Java is
  the one mainstream runtime with a portable fix: `p.descendants().forEach(
  ProcessHandle::destroyForcibly)` before `p.destroyForcibly()` (Java 9+, verified to
  kill the grandchild). Cross-language comparison: `sota-sandboxing` rules/04 R5.3a.
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
  dependency CVEs — `rules/06`); the web layer itself is §6 below.
- **`assert` is not a control**: assertions are **disabled by default** at
  runtime — Oracle's own guide says so, and adds that once disabled they are
  "essentially equivalent to empty statements in semantics and performance".
  Production JVMs are rarely started with `-ea`, so a validation or bounds check
  written as `assert` is a no-op in the deployment while reading correct in
  source. Use an explicit `if` + throw (or `Objects.requireNonNull`,
  `Preconditions`-style checks that survive). Class:
  `sota-code-security` rules/11 §4.

## 6. The web layer — actuator, request binding, authorization rules, filters

HTTP semantics (status codes, idempotency, rate limits, CORS) belong to `sota-api-design`, and
web-security classes (CSRF, XSS, headers) to `sota-code-security` rules/05. This section covers
the JVM mechanisms those attacks come in through. Spring is the example because it is the most
widely deployed JVM web stack. Ask the same questions of Jakarta EE, Micronaut, Quarkus or Ktor.
All Spring facts below were checked against Spring's own docs, advisories and source on
2026-09-23. **Re-verify them for the major version in front of you.**

- **Actuator exposure.** By default Spring Boot exposes only `health` over HTTP. Treat every
  widening of `management.endpoints.web.exposure.include` as a finding until you have shown the
  endpoint sits behind authentication or a firewall, which is the docs' own condition for
  setting it. A value of `*` on an internet-facing port is HIGH. **`heapdump` is the worst
  one.** It returns process memory. The `show-values` sanitization (default `never`) covers
  `/env`, `/configprops` and `/quartz`, not a heap dump, which holds every secret the process
  has loaded. Prefer `management.server.port` on an internal-only interface.
- **Typed request bodies.** §1 states the rule. The web layer is where it fires, because a
  `@RequestBody` is JSON the caller wrote. `@JsonTypeInfo(use = Id.CLASS)` or `Id.MINIMAL_CLASS`
  on a type reachable from a request lets the caller name the class to instantiate. Use
  `Id.NAME` with registered subtypes. `enableDefaultTyping` was deprecated in jackson-databind
  2.10 in favour of `activateDefaultTyping(PolymorphicTypeValidator)` (databind #2195). A
  validator that allows `Object` or a broad package prefix is the same hole under a new name.
- **Data binding (mass assignment).** Spring's reference docs say: *"for security reasons it is
  recommended either to use an object tailored specifically for web binding, or to apply
  constructor binding only. If property binding must still be used, then allowedFields
  patterns should be set."* Binding a persistence entity straight from a request lets the
  caller set `role`, `ownerId` or `id`. A record used as the binding target gets constructor
  binding by construction. **Spring4Shell (CVE-2022-22965) was this class** reaching the class
  loader through property binding. It affected Spring Framework 5.3.0–5.3.17 and 5.2.19 and
  earlier, and was fixed in 5.3.18 and 5.2.20. It required JDK 9+, Tomcat and WAR packaging.
  Executable-JAR deployments were not affected.
- **Authorization rules are first-match.** `authorizeHttpRequests` evaluates its pairs "in
  the order listed, applying only the first match". So a broad `permitAll()` placed above a
  narrow rule silently wins. End with `.anyRequest().denyAll()`, or `.authenticated()` as a
  stated choice. The docs call default deny "a healthy security practice since it turns the
  set of rules into an allow list". Prefer `permitAll()` to `web.ignoring()`: an ignored path
  skips the whole filter chain, security headers included. Since Spring Security 6,
  authorization runs on **every dispatch** (FORWARD, ERROR and INCLUDE as well as REQUEST), so
  an error page or forward target needs its own rule rather than inheriting its caller's.
- **Filter ordering.** A servlet `Filter` that reads identity, logs the principal or enforces
  tenancy must run **after** the security filter chain has authenticated the request. If it
  is registered earlier, it sees an anonymous request, or trusts a header the chain would
  have rejected. Check the order **on the running application**, not from `@Order`
  annotations. Both the default order and the property that sets it have moved between Spring
  Boot majors: Boot 4's `SecurityProperties` on main no longer carries a filter order.

## Audit checklist

- [ ] **Deserialization — CRITICAL** —
      `grep -rnE 'readObject\(|ObjectInputStream|XMLDecoder' --include='*.java' .` ;
      `grep -rnE 'enableDefaultTyping|@JsonTypeInfo|activateDefaultTyping' --include='*.java' .`
      (Jackson polymorphic);
      `grep -rnE 'MappingJackson2MessageConverter|JacksonJsonMessageConverter|new Kryo\(' --include='*.java' --include='*.kt' .`
      (framework deser — verify type allowlist)
- [ ] **Injection — CRITICAL/HIGH** —
      `grep -rnE '(createQuery|createNativeQuery|prepareStatement|executeQuery|executeUpdate)\([^?)]*\+' --include='*.java' .`
      ;
      `grep -rnE 'Runtime\.getRuntime\(\)\.exec|new ProcessBuilder' --include='*.java' --include='*.kt' .`
- [ ] **The String-taking exec overloads TOKENIZE on whitespace and are @Deprecated(since=18): a
      hit here is a finding on the deprecation alone, before any taint analysis.** —
      `grep -rnE 'Runtime\.getRuntime\(\)\.exec\(\s*"' --include='*.java' --include='*.kt' .`
- [ ] **waitFor(t,unit) reaps nothing: a destroy() with no descendants() sweep orphans
      grandchildren** —
      `grep -rn 'waitFor(' --include='*.java' --include='*.kt' . | grep -v 'descendants'` ;
      `grep -rnE 'ctx\.lookup|InitialContext|new InitialDirContext' --include='*.java' .`
      (JNDI/Log4Shell-class);
      `grep -rnE 'SpelExpressionParser|Ognl|ScriptEngineManager|getEngineByName' --include='*.java' .`
- [ ] **Path traversal / zip slip — HIGH (the rule is stated at 5 above; this is its probe)
      Found 2026-09-22: the BUILD half existed ("canonicalize and verify the result stays under
      an allowed root") with no audit probe anywhere in the skill -- the dominant gap shape. a
      path built from request data and never normalize()d. Then confirm the check is
      startsWith(root) AFTER normalize/toRealPath -- normalizing without comparing is a no-op.
      ZIP SLIP: an archive entry name is attacker-controlled and may contain ../ ; the extracted
      path must be resolved against the target dir and re-checked with startsWith.** —
      `grep -rnE 'new File\(|Paths\.get\(|Path\.of\(' --include='*.java' --include='*.kt' . | grep -vE 'normalize|toRealPath'`
      ;
      `grep -rnE 'getName\(\)|getEntry\(|ZipEntry|TarArchiveEntry' --include='*.java' --include='*.kt' .`
- [ ] **XXE — CRITICAL (verify DTDs disabled)** —
      `grep -rnE 'DocumentBuilderFactory|SAXParserFactory|XMLInputFactory|TransformerFactory|SAXReader' --include='*.java' .`
      ;
      `grep -rn 'disallow-doctype-decl\|setExpandEntityReferences\|SafeConstructor' --include='*.java' . || echo "verify XXE hardening"`
- [ ] **Actuator exposure — HIGH if internet-facing** —
      `grep -rnE 'management\.endpoints\.web\.exposure\.include|management\.server\.port|show-values' --include='*.properties' .`
      ; `grep -rnE '^[[:space:]]*(exposure|include|show-values):|heapdump' --include='*.yml' --include='*.yaml' .`
      (YAML nests the key, so the dotted pattern alone misses `include: "*"`, the commonest
      form. Anything beyond `health` needs auth or a firewall; `heapdump` exposed is HIGH on
      sight)
- [ ] **Request-body polymorphism — CRITICAL on a type reachable from `@RequestBody`** —
      `grep -rnE 'JsonTypeInfo\.Id\.(CLASS|MINIMAL_CLASS)|use *= *(JsonTypeInfo\.)?Id\.(CLASS|MINIMAL_CLASS)|activateDefaultTyping|enableDefaultTyping' --include='*.java' --include='*.kt' .`
      (then read the `PolymorphicTypeValidator`: allowing `Object` or a broad prefix is the
      same finding)
- [ ] **Mass assignment — HIGH** — list binding targets and confirm none is an entity:
      `grep -rnE '@(ModelAttribute|RequestBody)' --include='*.java' --include='*.kt' .` ;
      `grep -rnE 'setAllowedFields|setDisallowedFields|@InitBinder' --include='*.java' --include='*.kt' .`
      (property binding with no `setAllowedFields` on an entity is the finding; a
      disallow-list is weaker than an allow-list)
- [ ] **Authorization rules — HIGH** —
      `grep -rnE 'authorizeHttpRequests|requestMatchers|anyRequest|permitAll|ignoring\(' --include='*.java' --include='*.kt' .`
      (read each chain top-down: first match wins; the chain must end in `anyRequest()`;
      `web.ignoring()` on a non-static path is a finding)
- [ ] **Filter order — MEDIUM, HIGH if the filter enforces tenancy or reads identity** —
      `grep -rnE 'implements (jakarta|javax)\.servlet\.Filter|extends OncePerRequestFilter|FilterRegistrationBean|@Order' --include='*.java' --include='*.kt' .`
      (confirm on the running app that each identity-reading filter runs after the security
      chain; an annotation is not evidence of the effective order)
- [ ] **Crypto misuse — HIGH** —
      `grep -rnE 'new Random\(|Math\.random|ThreadLocalRandom' --include='*.java' . | grep -iE 'key|token|iv|salt|nonce|secret'`
      ;
      `grep -rnE '"(MD5|SHA-?1|DES|RC4)"|/ECB/|Cipher\.getInstance\("AES"\)' --include='*.java' --include='*.kt' .`
      ; `grep -rnE 'TrustManager|HostnameVerifier|checkServerTrusted' --include='*.java' .`
      (all-trusting?);
      `grep -rn 'Arrays.equals\|\.equals(' --include='*.java' . | grep -iE 'mac|hmac|token|signature|digest'`
- [ ] **Static security analysis SpotBugs + Find-Sec-Bugs; OWASP dependency-check / OSV-Scanner
      (rules/06)**