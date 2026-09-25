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
- **Jackson 3 changes the spellings, not the rule.** Packages and Maven groups move from
  `com.fasterxml.jackson` to `tools.jackson`, except `com.fasterxml.jackson.annotation`, which
  stays. So `@JsonTypeInfo` keeps its import. `enableDefaultTyping` is gone, because 3.0 drops
  everything deprecated as of 2.20. Default typing is now switched on only on the builder, with
  `JsonMapper.builder().activateDefaultTyping(ptv, …)` or `activateDefaultTypingAsProperty`, and
  a `PolymorphicTypeValidator` is required. `LaissezFaireSubTypeValidator` is no longer public.
  Annotation-driven typing defaults to `DefaultBaseTypeLimitingValidator`. It refuses base types
  such as `Object`, `Serializable` and `Comparable`, but it checks nothing below a narrower
  base. `builder().polymorphicTypeValidator(...)` replaces it, so read what that call installs.
  Spring Boot 4 / Framework 7 default to Jackson 3. The web-layer view is `rules/08` §1
  ([Jackson 3 migration guide](https://github.com/FasterXML/jackson/blob/main/jackson3/MIGRATING_TO_JACKSON_3.md),
  [Spring: Jackson 3 support](https://spring.io/blog/2025/10/07/introducing-jackson-3-support-in-spring)).
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
- **Third-party object mappers are safe only above a version and under a setting.** Each
  boundary below was read from the project's advisory, docs or jar on 2026-09-25; re-check it
  at the advisory before relying on it. **fastjson 1.x** (`com.alibaba:fastjson`, repository
  now archived): safe mode exists from 1.2.68 and switches autoType off completely
  (`ParserConfig.getGlobalInstance().setSafeMode(true)` or `fastjson.parser.safeMode=true`).
  The autoType bypass CVE-2022-25845 covers 1.2.25 to 1.2.82 (GHSA-pv7h-hx5h-mgfj). So
  require 1.2.83 or later with safe mode on and no `setAutoTypeSupport(true)`, or move to
  fastjson2 with autotype left off. **XStream**: XStream's security page says the default
  became an allowlist in 1.4.18, and before that it was a denylist, which the page calls a
  failed approach. DoS fixes kept landing after that, so run the latest release.
  `addPermission(AnyTypePermission.ANY)` or a broad wildcard undoes the allowlist.
  **YamlBeans**: CVE-2023-24621 lists 1.15 and earlier with no patched version. The 1.17 jar
  on Maven Central adds `SafeYamlConfig` (class tags and anchors off), but a plain `YamlConfig`
  still defaults `classTags` to `true` (1.17 source), so untrusted YAML goes through
  `SafeYamlConfig` only. **Castor XML**: its last Maven Central release is 1.4.1 (2016) and
  its last commit is from 2017, so no fix is coming. Keep untrusted input away from it.
  OWASP: Deserialization cheat sheet.
- **The class side of native serialization.** Mark a field that must never cross the wire
  `private transient`. Measured on Temurin 25.0.4: a `transient` password was absent from the
  stream and read back as `null`. Some domain classes are `Serializable` only because a
  framework demands it and must never be rebuilt from bytes. Give each one
  `private final void readObject(ObjectInputStream in) throws IOException { throw new
  InvalidObjectException("not deserializable"); }`, which threw on the same JDK. The review
  surface is wider than `readObject()`. It also covers `readUnshared()`, class-side
  `readObject`, `readObjectNoData` and `readResolve`, `Externalizable.readExternal`, XStream
  `fromXML`, and every `Serializable` class on the classpath, because a gadget is a class, not
  a call. Legacy code you cannot change can use a `-javaagent` that hardens
  `ObjectInputStream` with a gadget denylist, but only as a last resort behind
  `jdk.serialFilter`: a denylist misses the next gadget. OWASP: Deserialization cheat sheet.

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
  **LDAP filters are a second sink** (CWE-90; the class is `sota-code-security` rules/01 §11).
  Never concatenate into a filter string. Use the JNDI overload that takes arguments,
  `ctx.search(base, "(uid={0})", new Object[]{user}, controls)`: the Javadoc says each
  `{i}` is substituted "with any characters having special significance within filters
  (such as '*') having been escaped according to the rules of RFC 2254".
  **`SearchControls.setReturningObjFlag(true)` asks the provider to rebuild Java objects
  from directory entries** (`javaSerializedData`, `javaReferenceAddress`,
  `javaRemoteLocation`). That is deserialization of whatever an attacker wrote into the
  directory. The JDK gates it with `com.sun.jndi.ldap.object.trustSerialData`. Its
  documented default was "allowed" in the `java.naming` module docs at jdk-17-ga and
  jdk-19-ga, and "not allowed" from jdk-20-ga on (read from the `module-info.java` at
  each tag). So a `trustSerialData=true` anywhere is a finding. On a JDK whose `java.naming`
  docs still say "allowed", the absence of `=false` is one too. Update releases of older
  lines were not checked, so read the docs of the exact build.
  **A DN is a separate context with its own escaping.** The `{0}` overload of `search`
  substitutes its arguments into the filter only. The `name` argument, like any DN passed to
  `bind`, `lookup`, `modifyAttributes` or used as a bind principal, is taken as written. So
  escape each value placed in a DN with `javax.naming.ldap.Rdn.escapeValue` (RFC 2253, per its
  Javadoc), or build the name as `new LdapName(List.of(new Rdn("ou", "people"), new Rdn("uid",
  user)))`. ESAPI's `Encoder.encodeForDN` does the same job. Measured on Temurin 25.0.4:
  `"uid=" + "bob,ou=admins" + ",ou=people"` parsed as three RDNs, while the `Rdn` form stayed
  at two, and `escapeValue("bob,ou=admins+cn=x")` returned `bob\,ou\=admins\+cn\=x`. Filter
  escaping does not make a value safe in a DN. The two rule sets are in `sota-code-security`
  rules/01 §11. OWASP: LDAP Injection Prevention cheat sheet.
- **XPath injection** (CWE-643): an expression built by concatenation is the SQL-injection
  shape. Bind values with `XPath.setXPathVariableResolver` and reference them as `$name`.
  Measured on Temurin 25.0.4: `count(//user[name='" + in + "'])` with
  `in = "nobody' or '1'='1"` matched **2 of 2** users, and the `$name` form with the same
  value matched **0**.
- **Expression/script eval**: SpEL, OGNL, MVEL, `ScriptEngine` (Nashorn/JS),
  Jakarta EL (`ELProcessor`, `ExpressionFactory.createValueExpression`), Groovy
  (`GroovyShell`, `Eval.me`), Spring expression contexts, and template engines
  (FreeMarker, Velocity, Pebble) compiling a template *string* from user input are
  RCE. So is reflection named by input: `Class.forName(in)` loaded `java.lang.Runtime` (Temurin
  25.0.4). Dispatch via a fixed `Map<String, Handler>`/`enum` or a grammar you parse. A bare
  `parseExpression(in).getValue()` builds a `StandardEvaluationContext`; Spring's Javadoc says even
  `SimpleEvaluationContext` "must not be considered safe" for untrusted expressions. **No in-process
  sandbox is a boundary** (`System.setSecurityManager` threw `UnsupportedOperationException` on
  25.0.4): use a separate process or drop it. OWASP: Code Review Guide, Proactive Controls C3.
- **Regex from input, and the shapes `java.util.regex` still cannot survive** (CWE-1333;
  class: `sota-code-security` rules/01 §10). A pattern compiled from request data
  (`Pattern.compile(userInput)`, `s.matches(userInput)`) hands the caller the regex engine.
  Use `Pattern.quote` when the input is meant literally. **The textbook ReDoS no longer
  reproduces on current JDKs**: measured on Temurin 21.0.12 and 25.0.4, `(a+)+$`,
  `(a|aa)+$` and `^([a-z]+)*$` all finished in 0–9 ms on inputs of up to 24 `a`s plus `!`. **Bounded
  repetition and backreferences still blow up**, measured on 25.0.4 with `a`×N plus `!`:
  `^(a{1,2}){1,60}$` took 113 ms at N=28, 1.3 s at 36 and **9.1 s at 40**, and `(\1?a)+b`
  took 3.7 s at 40. So a clean result for the classic shape proves nothing about the
  others. For patterns from untrusted sources use RE2/J (`com.google.re2j`), whose README
  describes linear-time matching that omits backreferences. Otherwise cap the input
  length before matching.
- **A regex used as a gate (validation, allowlist, routing, redaction): escaping, anchoring,
  bounds, engine.** Measured on Temurin 21.0.12 and 25.0.4 unless noted.
  **Escaping**: `Pattern.quote(s)` (Kotlin `Regex.escape(s)`, which calls it) for data inside a
  pattern, or `Pattern.LITERAL` / `Regex.fromLiteral`; the *replacement* argument of
  `replaceAll`/`replaceFirst`/`Regex.replace` is its own mini-language, so a user value there
  goes through `Matcher.quoteReplacement` (`Regex.escapeReplacement`): an unescaped `$1` threw
  `IndexOutOfBoundsException: No group 1`. **Anchoring**: whole-input match is
  `String.matches`, `Pattern.matches`, `Matcher.matches()`, Kotlin `Regex.matches`/`matchEntire`.
  `find()`, Kotlin `containsMatchIn`/`find(...) != null` search anywhere, and `lookingAt()`
  anchors only the start: `[a-z]+` via `find()` accepted `<x>abc`. The trap for a `^…$` pattern
  run through `find()`: `$` also matches before a final line terminator, so `^[a-z]+$`
  accepted `"abc\n"` (and `^a$` accepted `"a\r\n"` and `"a\u2028"`) while `^[a-z]+\z`
  and `matches()` rejected it; with `MULTILINE`/`(?m)` it accepted `"abc\n<x>"`.
  Validate with `matches()`, or anchor with `\A`…`\z`. RE2/J 1.8 differs: its
  `^[a-z]+$` via `find()` rejected `"abc\n"`, so a port between the engines changes what a
  check admits. **Bounds**: cap length before matching and
  give every repetition an upper limit (`[a-z0-9]{1,64}`, not `+`). **Engine**:
  `java.util.regex` backtracks and has no match-timeout API (`javap` on `Pattern`/`Matcher`
  lists none). Mitigations: RE2/J for untrusted patterns; possessive quantifiers and atomic
  groups where semantics allow (`^(?>a{1,2}){1,60}$` took 0 ms where the plain form took
  1.3–1.4 s at 36 `a`s + `!`, and still matched 40 `a`s); or a deadline, by wrapping the input in
  a `CharSequence` whose `charAt` throws past a deadline (it aborted the 40-`a` case above at
  199 ms). RE2/J 1.8 rejects lookaround, backreferences, `a++` and `(?>…)`, so moving a pattern
  to `java.util.regex` to get them re-imports backtracking: cap input first. Sources, by
  name: OWASP Input Validation cheat sheet; OWASP Proactive Controls 2024 C3; ASVS 5.0
  V1.2.9; OWASP Go-SCP (validation, regular expressions).

XML and XXE (formerly section 3) moved to [rules/07](07-xml.md) §1 on 2026-09-25.

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
  - **The transformation string is where these rules are broken, so read every one.**
    Findings include:
    - `"…/CBC/…"` with no MAC over the ciphertext (padding oracle);
    - `DESede`/`TripleDES`, `Blowfish`, `RC2`, `RC4`/`ARCFOUR`;
    - `"RSA/…/NoPadding"` (textbook RSA; use OAEP);
    - `javax.crypto.NullCipher`, which is the identity transformation;
    - an IV or GCM nonce from a constant, from a string's bytes, or from `new byte[16]`.
      It must come from `SecureRandom` per message.

    For key sizes, `sota-code-security` rules/04 §1 already schedules RSA-2048 (112-bit)
    for deprecation after 2030. So a `KeyPairGenerator.initialize(1024)` is below a floor
    that is itself on its way out.
  - **Newer JDKs have JCA names for post-quantum and key derivation. Use them, not
    hand-rolled code.** The policy (which algorithm, hybrid or not, when) is
    `sota-code-security` rules/04 §1; these are only the JVM spellings.
    - ML-KEM (JEP 496, since JDK 24) is `KeyPairGenerator.getInstance("ML-KEM")` with
      `KEM.getInstance("ML-KEM")`. The parameter sets are `ML-KEM-512`/`-768`/`-1024`.
    - ML-DSA (JEP 497, since JDK 24) is `Signature.getInstance("ML-DSA")`. The parameter
      sets are `ML-DSA-44`/`-65`/`-87`.
    - HKDF (JEP 510, final in JDK 25) is `KDF.getInstance("HKDF-SHA256")` with
      `HKDFParameterSpec.ofExtract()…thenExpand(info, len)`. It replaces an extract/expand
      built by hand on `Mac` and a copied `HkdfUtil`. HKDF still does not take a password
      (the password-hashing line above).
    - Hybrid TLS 1.3 key exchange (JEP 527, JDK 27) puts `X25519MLKEM768` first in the
      default named groups, with no code change. **Pinning the groups turns it off.** A
      `jdk.tls.namedGroups` property or a `SSLParameters.setNamedGroups(...)` list written
      before JDK 27 does not contain it. `SecP256r1MLKEM768` and `SecP384r1MLKEM1024` exist
      but are off by default
      ([JEP 496](https://openjdk.org/jeps/496), [JEP 497](https://openjdk.org/jeps/497),
      [JEP 510](https://openjdk.org/jeps/510), [JEP 527](https://openjdk.org/jeps/527)).
  - **Hex-encode digests with `java.util.HexFormat`** (since 17), never a loop over
    `Integer.toHexString(b & 0xff)`. That drops each leading zero, so distinct inputs
    collide. Measured: bytes `{0x01,0x23}` and `{0x12,0x03}` both encode to `"123"`;
    `HexFormat` gives `0123` and `1203`.
- TLS: use the platform default protocols/cipher suites (TLS 1.2+/1.3); **never**
  install an all-trusting `TrustManager` or `HostnameVerifier` that returns
  true — disabling certificate validation is HIGH/CRITICAL. See
  `sota-code-security` rules/04 and `sota-network-security`.
  **Mail clients verify the hostname only if told to in the old API.**
  `mail.smtp.ssl.checkserveridentity` is documented "Defaults to false" in the legacy
  JavaMail (`com.sun.mail`) SMTP provider docs. Angus Mail's compatibility notes say the
  check "is enabled by default" from Angus Mail 1.1.0. Apache Commons Email only sets it to
  `true` when `setSSLCheckServerIdentity(true)` is called, so on the old provider it stays
  off. **SSH host keys are the same control** — the rule is stated once in
  `sota-code-security` rules/04 §5. The JVM spellings are JSch
  `setConfig("StrictHostKeyChecking", "no")` and MINA SSHD `AcceptAllServerKeyVerifier`.

## 5. Other boundaries

- **Path traversal**: canonicalize and verify the result stays under an allowed
  root (`Path.normalize()` + `startsWith`); reject `..`. Use `java.nio.file`.
- **SSRF / URL fetch**: validate/allowlist destinations; block internal/metadata
  ranges (see `sota-code-security`). **`java.net.URL` is also a file reader.** Measured on
  Temurin 25.0.4: `URI.create("file:///tmp/secret.txt").toURL().openStream()` returned the
  file. `java.net.http.HttpRequest.newBuilder(URI.create("file:///…"))` threw
  `IllegalArgumentException: invalid URI scheme file`. So a fetcher built on
  `URL.openConnection`/`openStream` needs an explicit `http`/`https` scheme allowlist, and
  the JDK `HttpClient` gives you that refusal for free.
- **SSRF in the JVM clients: check the address the socket dials, and every hop.** The
  policy is `sota-code-security` rules/01 §5. Take a host key or ID and build the URL from
  your allowlist. When the caller has to name the destination, the check belongs in a
  connect-time hook, because checking a string first and fetching after lets DNS rebinding
  through. All of the following was measured on Temurin 25.0.4 in 2026-09:
  - **OkHttp** (4.12.0 and 5.5.0): the `Dns` hook is skipped for IP-literal hosts.
    `RouteSelector` calls `InetAddress.getByName` directly when `canParseAsIpAddress()` is
    true. A `Dns` filter blocked `internal.test`, but `http://127.0.0.2/` and a redirect to
    it both came back 200. Put the check in `.socketFactory(...)` instead: return a `Socket`
    whose `connect(SocketAddress, int)` rejects a bad address. OkHttp creates the raw socket
    there and layers TLS over it, and that caught literals, hostnames and redirect hops.
    `followRedirects` and `followSslRedirects` both default to `true`. Only `http`/`https`
    URLs parse at all.
  - **Apache HttpClient 5** (5.5): `PoolingHttpClientConnectionManagerBuilder
    .setDnsResolver(...)` got called for hostnames, for IP literals and for each redirect
    hop, so a throwing `DnsResolver` works as the hook. `RequestConfig.DEFAULT` has
    redirects enabled. Use `HttpClientBuilder.disableRedirectHandling()` or
    `setRedirectsEnabled(false)`.
  - **JDK `java.net.http.HttpClient`**: redirects default to `Redirect.NEVER`. It has no
    per-client resolver or socket hook, and `Host` is a restricted header, so you cannot pin
    a checked IP and keep the name. For a caller-chosen destination, send it through an
    enforcing egress proxy (`.proxy(ProxySelector)`) or use a client above. With `NORMAL`
    or `ALWAYS`, hops are followed with no callback. Keep `NEVER` and re-validate each
    `Location` yourself.
  - **What the hook rejects, and where `InetAddress` falls short**: loopback, private,
    link-local, `0.0.0.0/8`, multicast and ULA. That covers `169.254.169.254`, the
    `fd00:ec2::254` IPv6 metadata address, and any metadata hostname, because the hook
    sees the resolved address rather than the name. `isSiteLocalAddress()` returned **false** for `fd00::/8`, so test
    `(b[0] & 0xfe) == 0xfc` yourself. `isAnyLocalAddress()` is true only for
    `0.0.0.0`/`::`, not for `0.1.2.3`, so test `b[0] == 0`. `::ffff:a.b.c.d` came back as
    an `Inet4Address`, so the IPv4 tests cover it. The IPv4-compatible `::127.0.0.1` stayed
    `Inet6Address` with `isLoopbackAddress()` false, so reject that form.
  - **Java's literal parser is lenient and differs from other parsers.** `InetAddress
    .getByName` and `ofLiteral` (present on 25, absent on 21) parse `2130706433` and
    `127.1` as `127.0.0.1`, and `0177.0.0.1` as **decimal** `177.0.0.1`. They reject hex.
    Checking a string with Java and then passing it to a proxy or `curl` that reads octal
    fails open. Accept an IPv4 literal only when `ofLiteral(s).getHostAddress().equals(s)`
    (IPv6 prints uncompressed, so that test does not work for IPv6), and let the socket
    check have the final say anyway.
  OWASP: SSRF Prevention, .NET Security and GraphQL cheat sheets.
- **Upload filenames are request data.** Servlet `Part.getSubmittedFileName()` and Spring
  `MultipartFile.getOriginalFilename()` return what the client sent. Spring's own Javadoc
  warns the name "could also contain characters such as '..'" and recommends generating
  your own. Never build a storage path from it; the upload pipeline is `sota-code-security`
  rules/05.
- **Secrets**: never hardcode; load from a secret manager/env; don't log them;
  prefer `char[]`/`byte[]` you can wipe over `String` for passwords (`rules`
  cross-ref `sota-secrets-management`). **A record logs its secrets for you**: the implicit
  `toString` holds *"the names of components of the record, and string representations of
  component values"* (`java.lang.Record`). Measured on Temurin 25, a `record Creds(String
  user, String password)` printed `Creds[user=bob, password=hunter2]`, so `log.info("{}",
  creds)` leaks it. Override `toString` on any record or Kotlin `data class` that carries a
  credential. Redaction at the logger is `sota-observability` rules/01 §4.
- **Spring/framework**: keep dependencies patched (Spring4Shell, Log4Shell were
  dependency CVEs — `rules/06`); the web layer itself is in `rules/08`.
- **`assert` is not a control**: assertions are **disabled by default** at
  runtime — Oracle's own guide says so, and adds that once disabled they are
  "essentially equivalent to empty statements in semantics and performance".
  Production JVMs are rarely started with `-ea`, so a validation or bounds check
  written as `assert` is a no-op in the deployment while reading correct in
  source. Use an explicit `if` + throw (or `Objects.requireNonNull`,
  `Preconditions`-style checks that survive). Class:
  `sota-code-security` rules/11 §4.

The web layer (formerly section 6) moved to [rules/08](08-web-layer.md) §1 on 2026-09-25.

## 7. Native and off-heap memory — JNI, FFM, `Unsafe`

The JVM is memory-safe until code leaves it. JNI (`native` methods, Kotlin `external`, loaded
with `System.loadLibrary`), the FFM API (`java.lang.foreign`, final in JDK 22, JEP 454) and
`sun.misc.Unsafe` all reach raw memory, where a wrong length is a buffer overflow and a crash
takes down the whole JVM. FFM's restricted methods only **warn** unless
`--enable-native-access` names the calling module, so set it to the named modules and never
`ALL-UNNAMED` by habit. `Unsafe`'s memory-access methods are deprecated for removal
(JDK 23, JEP 471), so migrate to `VarHandle` or FFM. Audit every crossing with the C rules;
the class is `sota-code-security` rules/06 §3.

**JDK 24 brought JNI under the same gate, but only as a warning.** JEP 472 makes loading and
linking a JNI library a restricted operation, and `--illegal-native-access` defaults to `warn`.
`deny` throws `IllegalCallerException` instead. Grant access per module with
`--enable-native-access=M1,M2`. `ALL-UNNAMED` (the only value the `Enable-Native-Access`
JAR-manifest attribute takes) grants the whole class path. JEP 498 does the same for `Unsafe`
memory access. `--sun-misc-unsafe-memory-access` defaults to `warn` on JDK 24, and `deny`
throws `UnsupportedOperationException`. A warning printed once to stderr gets read by nobody.
On JDK 24+, run CI and production with `--illegal-native-access=deny` and
`--sun-misc-unsafe-memory-access=deny`. Then a new dependency that reaches native code or
`Unsafe` fails the build instead of printing that warning. Where you do need an exception, grant
only the named module. **JEP 483's AOT cache refuses any `--illegal-native-access` value**, so
with a cache run this gate in a cache-free CI job instead (`rules/05` §2).

## Audit checklist

- [ ] **Native and off-heap memory — HIGH on untrusted lengths** (§7) —
      `grep -rnE '(^|[^[:alnum:]_])native[[:space:]][^;]*\(|(^|[^[:alnum:]_])external fun[[:space:]]|System\.load(Library)?\(|sun\.misc\.Unsafe|java\.lang\.foreign|(enable|illegal)-native-access|Enable-Native-Access|sun-misc-unsafe-memory-access' --include='*.java' --include='*.kt' --include='*.gradle*' --include='pom.xml' --include='MANIFEST.MF' --include='jvm.config' --include='Dockerfile*' --include='*.sh' .`
      (each hit is audited as C; `ALL-UNNAMED` needs a written reason; a `=warn`/`=allow`
      value, or a JDK 24+ launch with no `=deny` for both flags, is MEDIUM) ;
      `grep -rlE 'illegal-native-access=deny' --include='*.gradle*' --include='pom.xml' --include='jvm.config' --include='Dockerfile*' --include='*.sh' --include='*.y*ml' . || echo "no --illegal-native-access=deny anywhere"`
      (repeat with `sun-misc-unsafe-memory-access=deny`)
- [ ] **Deserialization — CRITICAL** —
      `grep -rnE 'readObject\(|ObjectInputStream|XMLDecoder' --include='*.java' --include='*.kt' .` ;
      `grep -rnE 'enableDefaultTyping|@JsonTypeInfo|activateDefaultTyping|polymorphicTypeValidator\(|LaissezFaireSubTypeValidator' --include='*.java' --include='*.kt' .`
      (Jackson polymorphic, 2.x and 3.x spellings; `activateDefaultTyping` also matches
      `…AsProperty`);
      `grep -rnE 'MappingJackson2MessageConverter|JacksonJsonMessageConverter|new Kryo\(' --include='*.java' --include='*.kt' .`
      (framework deser — verify type allowlist)
- [ ] **Object mappers in an unsafe mode — CRITICAL on untrusted input** (§1) —
      `grep -rnE 'setAutoTypeSupport\([[:space:]]*true|setSafeMode\([[:space:]]*false|safeMode[[:space:]]*=[[:space:]]*false|AnyTypePermission\.ANY|new YamlConfig\(|org\.exolab\.castor' --include='*.java' --include='*.kt' --include='*.properties' .`
      (then read the fastjson, XStream and YamlBeans versions in the lockfile against the
      §1 floors; safe mode must be switched on, since its absence does not match)
- [ ] **Native-serialization review surface and class-side hardening — HIGH** (§1) —
      `grep -rnE 'readUnshared\(|readObjectNoData\(|readResolve\(|readExternal\(|\.fromXML\(|(implements|:)[^{;]*(Serializable|Externalizable)' --include='*.java' --include='*.kt' .`
      (each `Serializable` hit: credential fields `transient`, and a class never meant to be
      read back has a `readObject` that throws; each read call: trace its bytes)
- [ ] **Injection — CRITICAL/HIGH** —
      `grep -rnE '(createQuery|createNativeQuery|prepareStatement|executeQuery|executeUpdate)\([^?)]*\+' --include='*.java' --include='*.kt' .`
      ;
      `grep -rnE '\.(query|queryForObject|queryForList|queryForMap|queryForRowSet|update|batchUpdate|execute|executeLargeUpdate|addBatch)\([[:space:]]*"[^"]*"[[:space:]]*\+' --include='*.java' --include='*.kt' .`
      (Spring `JdbcTemplate`, plain `Statement` and similar clients: the line above never
      names them; the `?`-placeholder form does not match)
      ;
      `grep -rnE '(createQuery|createNativeQuery|prepareStatement|executeQuery|executeUpdate|query|queryForObject|queryForList|queryForMap|queryForRowSet|update|batchUpdate|execute|executeLargeUpdate|addBatch)\([[:space:]]*"("")?([^"]*[^"\\])?\$[{a-zA-Z]' --include='*.kt' .`
      (Kotlin builds the same injection with a string template, `"... WHERE id = $id"` or
      `${x}`, and neither line above sees it. The `("")?` covers a `"""` raw string that opens
      on the call line. An escaped `\$` and a `$1` placeholder do not match; a raw string that
      continues onto later lines needs a read)
      ;
      `grep -rnE 'Runtime\.getRuntime\(\)\.exec|new ProcessBuilder' --include='*.java' --include='*.kt' .`
- [ ] **The String-taking exec overloads TOKENIZE on whitespace and are @Deprecated(since=18): a
      hit here is a finding on the deprecation alone, before any taint analysis.** —
      `grep -rnE 'Runtime\.getRuntime\(\)\.exec\(\s*"' --include='*.java' --include='*.kt' .`
- [ ] **waitFor(t,unit) reaps nothing: a destroy() with no descendants() sweep orphans
      grandchildren** —
      `grep -rn 'waitFor(' --include='*.java' --include='*.kt' . | grep -v 'descendants'` ;
      `grep -rnE 'ctx\.lookup|InitialContext|new InitialDirContext' --include='*.java' --include='*.kt' .`
      (JNDI/Log4Shell-class);
      `grep -rnE 'SpelExpressionParser|Ognl|ScriptEngineManager|getEngineByName' --include='*.java' --include='*.kt' .`
- [ ] **The eval sinks the line above does not name — CRITICAL on input** (§2) —
      `grep -rnE 'ELProcessor|createValueExpression|createMethodExpression|GroovyShell|Eval\.me\(|Velocity\.evaluate|VelocityEngine|freemarker\.template\.Template|PebbleEngine' --include='*.java' --include='*.kt' .`
      (a template or expression built from a request string is the finding; a template
      loaded by name from the classpath is not)
- [ ] **Dynamic code evaluation by name: reflection, SpEL parsed from a variable or a `StandardEvaluationContext` — CRITICAL on input** (§2) — `grep -rnE '(Class\.forName|\.getMethod|\.getDeclaredMethod|parseExpression)\([[:space:]]*[^"[:space:])]|StandardEvaluationContext' --include='*.java' --include='*.kt' .` (a literal first argument does not match; trace each hit to a request value)
- [ ] **LDAP filter injection and directory-borne deserialization — HIGH/CRITICAL** (§2) —
      `grep -rnE '\.search\([^;]*"[[:space:]]*\+' --include='*.java' --include='*.kt' .`
      (concatenated filter; use the `{0}` + `Object[]` overload) ;
      `grep -rnE '\.search\([^;]*"([^"]*[^"\\])?\$[{a-zA-Z]' --include='*.kt' .`
      (the same filter built with a Kotlin string template) ;
      `grep -rnE 'setReturningObjFlag\([[:space:]]*true|trustSerialData.{0,6}true' --include='*.java' --include='*.kt' --include='*.properties' --include='*.sh' --include='*.y*ml' --include='Dockerfile*' .`
      (objects rebuilt from LDAP entries; where the JDK's documented default is "allowed",
      as at jdk-17-ga and jdk-19-ga, an unset `trustSerialData` also allows it)
- [ ] **LDAP DN built from a raw value — HIGH** (§2) —
      `grep -rnE '(uid|cn|ou|dc|mail|sAMAccountName)=([^"]*"[[:space:]]*\+|[^"]*\$)' --include='*.java' --include='*.kt' . | grep -vE 'escapeValue|encodeForDN'`
      (a DN concatenated or templated from a variable; the `{0}` filter overload does not
      protect the base DN. Use `Rdn.escapeValue` or `LdapName`/`Rdn`)
- [ ] **XPath injection — HIGH** (§2) —
      `grep -rnE '\.(evaluate|compile)\([^;]*"[[:space:]]*\+' --include='*.java' --include='*.kt' .` ;
      `grep -rnE '\.(evaluate|compile)\("([^"]*[^"\\])?\$[{a-zA-Z]' --include='*.kt' .`
      (Kotlin string templates; an escaped `\$name` XPath variable does not match. The Java
      line also lists `Pattern.compile` concatenation, which the next item wants anyway)
- [ ] **ReDoS: regex from input, and the shapes that still backtrack — MEDIUM, HIGH on a
      request path** (§2: measured 9.1 s at 41 chars on JDK 25) —
      `grep -rnE 'Pattern\.(compile|matches)\([[:space:]]*[^")[:space:]]|\.(matches|replaceAll|replaceFirst)\([[:space:]]*[^")[:space:]]' --include='*.java' --include='*.kt' .`
      (pattern argument is not a literal: trace it to a constant or `Pattern.quote`) ;
      `grep -rnE '(compile|matches|replaceAll|replaceFirst|split)\("[^"]*(\}\)[*+{]|\\\\[1-9])' --include='*.java' --include='*.kt' .`
      (a bounded group under another quantifier, or a backreference: time it on 40 chars
      before calling it safe; `(a+)+` itself is NOT the test on current JDKs)
- [ ] **Regex anchoring on a validation gate: `find()`/`containsMatchIn` or a `$` that admits a
      trailing newline — HIGH on an allowlist, MEDIUM otherwise** (§2) —
      `grep -rnE '\.(find|lookingAt)\(\)|containsMatchIn\(|\.find\([^)]*\)[[:space:]]*[!=]=[[:space:]]*null|MULTILINE|\(\?[a-z]*m[a-z]*\)' --include='*.java' --include='*.kt' .`
      (a hit that decides accept/reject is the finding: use `matches()`/`matchEntire` or
      `\A`…`\z`; user data in a replacement string needs `Matcher.quoteReplacement`)
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
- [ ] **Client-supplied upload filenames — HIGH if they reach a path** (§5) —
      `grep -rnE 'getSubmittedFileName\(|getOriginalFilename\(' --include='*.java' --include='*.kt' .`
      (each hit must feed a display field or be discarded, never `resolve()`/`new File`)
- [ ] **`java.net.URL` reads `file:` — HIGH when the URL is request data** (§5, measured) —
      `grep -rnE 'new URL\(|\.toURL\(\)|\.openConnection\(|\.openStream\(' --include='*.java' --include='*.kt' .`
      (confirm an `http`/`https` scheme allowlist before the open, plus the SSRF controls;
      the JDK `HttpClient` refuses `file:` by itself)
- [ ] **SSRF: outbound client follows redirects, or has no connect-time internal address
      check — HIGH when the destination is request data** (§5, measured) —
      `grep -rnE 'Redirect\.(NORMAL|ALWAYS)|OkHttpClient\(\)|HttpClients\.(createDefault|createSystem)\(|followRedirects\(true\)|setRedirectsEnabled\(true\)|\.dns\(' --include='*.java' --include='*.kt' .`
      (each hit is a client that follows hops on its own, or runs with no hook. An OkHttp
      `.dns(` filter used as the guard is itself the finding, because IP literals skip it.
      For each client that reaches a caller-chosen host, confirm a `socketFactory` or
      `DnsResolver` guard exists, or an enforcing egress proxy)
- [ ] **Crypto misuse — HIGH** —
      `grep -rnE '(^|[^[:alnum:]_.])Random\(|Math\.random|ThreadLocalRandom|Random\.(Default|next)' --include='*.java' --include='*.kt' . | grep -iE 'key|token|iv|salt|nonce|secret'`
      (Java `new Random(`, Kotlin `Random()` and `kotlin.random.Random.nextX`; `SecureRandom(` does not match)
      ;
      `grep -rnE '"(MD5|SHA-?1|DES|RC4)"|/ECB/|Cipher\.getInstance\("AES"\)' --include='*.java' --include='*.kt' .`
      ; `grep -rnE 'TrustManager|HostnameVerifier|checkServerTrusted' --include='*.java' --include='*.kt' .`
      (all-trusting?);
      `grep -rnE 'Arrays\.equals|\.equals\(|contentEquals\(|[^=!]==[^=]' --include='*.java' --include='*.kt' . | grep -iE 'mac|hmac|token|signature|digest'`
      (Kotlin compares with `==` and `contentEquals`; use `MessageDigest.isEqual`)
- [ ] **Transformation strings, IVs and key sizes the line above misses — HIGH** (§4) —
      `grep -rnE '"(DESede|TripleDES|Blowfish|RC2|RC4|ARCFOUR)(/[^"]*)?"|"[A-Za-z0-9]+/CBC/[^"]*"|"RSA/[^"]*/NoPadding"|NullCipher' --include='*.java' --include='*.kt' .`
      (CBC is a finding unless a MAC covers the ciphertext; `AES/GCM/NoPadding` and OAEP do
      not match) ;
      `grep -rnE 'new (IvParameterSpec|GCMParameterSpec)\([^;]*(new byte\[|getBytes\()|static final byte\[\][[:space:]]*[A-Z_]*(IV|NONCE)|\.initialize\((512|768|1024|1536)[,)]' --include='*.java' --include='*.kt' .`
      (zero, string-derived or constant IV/nonce; RSA under 2048) ;
      `grep -rnE 'Integer\.toHexString\(' --include='*.java' --include='*.kt' .`
      (over digest bytes it drops leading zeros and collides; use `HexFormat`)
- [ ] **Hand-rolled HKDF, and TLS groups pinned without the hybrid — MEDIUM** (§4) —
      `grep -rliE 'hkdf' --include='*.java' --include='*.kt' . | while IFS= read -r f; do grep -qE 'KDF\.getInstance\(' "$f" || echo "$f"; done`
      (a file that names HKDF and never calls the JDK 25+ `KDF` API: a hand-built
      extract/expand or a third-party one; below JDK 25 a vetted library is the fix) ;
      `grep -rnE 'jdk\.tls\.namedGroups|setNamedGroups\(' --include='*.java' --include='*.kt' --include='*.properties' --include='*.security' --include='Dockerfile*' --include='*.sh' --include='jvm.config' . | grep -v 'MLKEM'`
      (a pinned list with no ML-KEM hybrid switches JDK 27's default off; a list split over
      several lines also prints, so read it)
- [ ] **Mail hostname check and SSH host keys — HIGH** (§4; host keys are
      `sota-code-security` rules/04 §5) —
      `grep -rnE 'ssl\.checkserveridentity|setSSLCheckServerIdentity\(false\)|import (javax\.mail|com\.sun\.mail)\.' --include='*.java' --include='*.kt' --include='*.properties' .`
      (on the legacy `com.sun.mail` provider an absent `checkserveridentity=true` is the
      finding) ;
      `grep -rnE 'StrictHostKeyChecking["'"'"']?[=, ]*["'"'"']?(no|off)|AcceptAllServerKeyVerifier' --include='*.java' --include='*.kt' --include='*.properties' .`
- [ ] **Secrets reaching logs — HIGH** (§5) —
      `grep -rniE '(log|logger)\.(trace|debug|info|warn|error)\([^;]*(passw|secret|token|api_?key|credential)' --include='*.java' --include='*.kt' .`
      (read the arguments: a credential passed to the call is the finding, while message
      text that only *names* one, such as "password reset for {}", also matches) ;
      `grep -rniE '(record|data class)[[:space:]]+[a-z0-9_]+[[:space:]]*(<[^>]*>)?[[:space:]]*\([^)]*(passw|secret|token|api_?key|credential)' --include='*.java' --include='*.kt' .`
      (a record or data class holding a credential: the generated `toString` prints it
      unless overridden)
- [ ] **Static security analysis SpotBugs + Find-Sec-Bugs; OWASP dependency-check / OSV-Scanner
      (rules/06)**