# 08 — The Web Layer: Actuator, Request Binding, Authorization Rules, Filters

Split out of rules/04 (formerly section 6) on 2026-09-25, when rules/04 neared the 500-line cap;
the section is now §1. rules/04 keeps its other section numbers.

## 1. The web layer — actuator, request binding, authorization rules, filters

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
  Executable-JAR deployments were not affected. Outside Spring the same shape is Apache
  Commons `BeanUtils.populate(bean, request.getParameterMap())`: property binding from
  request names with no allowlist at all.
- **Authorization rules are first-match.** `authorizeHttpRequests` evaluates its pairs "in
  the order listed, applying only the first match". So a broad `permitAll()` placed above a
  narrow rule silently wins. End with `.anyRequest().denyAll()`, or `.authenticated()` as a
  stated choice. The docs call default deny "a healthy security practice since it turns the
  set of rules into an allow list". Prefer `permitAll()` to `web.ignoring()`: an ignored path
  skips the whole filter chain, security headers included. Since Spring Security 6,
  authorization runs on **every dispatch** (FORWARD, ERROR and INCLUDE as well as REQUEST), so
  an error page or forward target needs its own rule rather than inheriting its caller's.
- **Descriptors, annotations and code all declare roles, and they must agree.** On Jakarta EE
  (and Spring on a servlet container) access rules live in three places. The first is
  deployment descriptors: `web.xml` `security-constraint`, `security-role`,
  `security-role-ref` and `run-as`, `ejb-jar.xml`, and vendor files such as `weblogic.xml`,
  whose `security-role-assignment` maps roles to principals or marks them
  `externally-defined`. The second is annotations: `@ServletSecurity`, plus `@RolesAllowed`,
  `@PermitAll`, `@DenyAll`, `@RunAs` and `@DeclareRoles` from `jakarta.annotation.security`.
  The third is code that calls `isUserInRole`. The Servlet spec makes the descriptor win: a
  `security-constraint` whose `url-pattern` exactly matches an annotated servlet's pattern
  makes `@ServletSecurity` "have no effect" there. With `metadata-complete="true"` the
  container ignores the annotations entirely. So an annotation can read as protection that
  the descriptor has silently replaced. For `isUserInRole("X")` the spec says a
  `security-role-ref` should link `X` to an application role. When there is none, the
  container tests membership in a role literally named `X`, so a name declared nowhere in the
  application resolves only through realm or vendor mapping that the reviewer cannot see.
  `run-as`/`@RunAs` raises the identity of everything the component calls, and each one needs
  a written reason. (Servlet spec facts read from the Jakarta Servlet specification source on
  2026-09-25.) OWASP: Code Review Guide v2.
- **Filter ordering.** A servlet `Filter` that reads identity, logs the principal or enforces
  tenancy must run **after** the security filter chain has authenticated the request. If it
  is registered earlier, it sees an anonymous request, or trusts a header the chain would
  have rejected. Check the order **on the running application**, not from `@Order`
  annotations. Both the default order and the property that sets it have moved between Spring
  Boot majors: Boot 4's `SecurityProperties` on main no longer carries a filter order.
- **CSRF: disabled, or bypassed by a GET.** Spring Security's docs say CSRF protection "is
  enabled" by default "for unsafe HTTP methods". `csrf().disable()`,
  `csrf(AbstractHttpConfigurer::disable)` or `csrf { disable() }` on a cookie-session app is
  HIGH. An API authenticated only by a header token, with no cookie for a forged request to
  ride, is the usual exception, and the reason belongs in a comment. The quieter hole is a state-changing handler reachable by GET.
  `CsrfFilter`'s default matcher skips `GET`, `HEAD`, `TRACE` and `OPTIONS` (read from its
  source), and a method-level `@RequestMapping` with no `method` maps every verb
  (`RequestMethod[] method() default {}`). So such a handler is reachable by a cross-site
  GET with no token check. Use `@PostMapping` and friends for anything that writes. It is
  the same class as the HEAD-to-GET confusion in `sota-ruby` rules/03.
- **View names are routing.** A controller return value of `"redirect:" + param` or
  `"forward:" + param`, or `new ModelAndView(param)`, lets the caller choose the target.
  Those prefixes are `UrlBasedViewResolver.REDIRECT_URL_PREFIX`/`FORWARD_URL_PREFIX`.
  `response.sendRedirect(param)` and `request.getRequestDispatcher(param)` are the servlet
  spellings. A **forward reaches what a browser cannot**: the Servlet spec says the
  contents of `WEB-INF` "may be exposed using the `RequestDispatcher` calls". Allowlist
  targets; the open-redirect rule is `sota-code-security` rules/01 §11. **A redirect does not end
  the handler.** `sendRedirect`, `forward` and a `Location` header are plain calls: the servlet
  Javadoc only says the response "should be considered to be committed". The code after them
  runs, so `return` or throw on the next line, above all after a failed auth check. OWASP: Code
  Review Guide v2.
- **CORS with credentials: `allowedOriginPatterns("*")` reflects any origin.** Spring
  refuses `allowedOrigins("*")` together with `allowCredentials(true)`, throwing
  `IllegalArgumentException` from `validateAllowCredentials`. But `checkOrigin` returns the
  request's own `Origin` for a pattern of `*` without calling that validation. So
  `allowedOriginPatterns("*")` plus credentials is reflect-any-origin-with-cookies (both
  read from `CorsConfiguration` source). The class is `sota-code-security` rules/05.
- **Session IDs in URLs.** Tomcat's `ApplicationContext` source says "URL re-writing is
  always enabled by default" and adds `COOKIE` beside it, so `encodeURL`/
  `encodeRedirectURL` can put `;jsessionid=` into links, logs and `Referer` headers. Set
  the tracking mode to cookie only: `server.servlet.session.tracking-modes=cookie` in
  Spring Boot, or `<tracking-mode>COOKIE</tracking-mode>` in `web.xml`. **A cookie the app sets
  itself starts bare**: `new jakarta.servlet.http.Cookie(...)` and Spring's `ResponseCookie.from`
  builder both default secure/HttpOnly to false with no SameSite, Path or Domain (servlet-api
  6.1.0, spring-web 7.0.9 source). Set each: `.secure(true).httpOnly(true).sameSite("Lax")`, or
  `setAttribute("SameSite", "Lax")` (Servlet 6.0+); Tomcat 11 adds none unless its `CookieProcessor`
  sets `sameSiteCookies`. Prefer a `__Host-` name (`Secure`, `Path=/`, no `Domain`). Its session
  cookie is `HttpOnly` (`StandardContext.useHttpOnly = true`). Policy: `sota-code-security` rules/05.
- **The servlet container's own configuration** (Tomcat `server.xml` as the example; Jetty and
  Undertow have equivalents). Defaults below are from the Tomcat 11.0 configuration reference,
  read 2026-09-25; check the reference for your major version. The `<Server>` shutdown port
  listens on localhost unless `address` says otherwise, and accepts a plain-text command
  string. Set `port="-1"` when a service wrapper (jsvc, Commons Daemon) stops Tomcat, and
  otherwise keep it on loopback with a non-default command. On `<Host>`, `autoDeploy`,
  `deployOnStartup` and `deployXML` all **default to `true`**. The docs advise security-conscious
  sites to set `deployXML="false"` so a WAR's own `META-INF/context.xml` cannot reconfigure the
  container. A production host that deploys from a pipeline wants all three off, so an absent
  attribute is the finding. On `<Context>`, `crossContext`, `privileged` (container servlets
  such as the manager) and `<Resources allowLinking>` all default to `false`. Each `true`
  needs a reason, and `allowLinking` must never be `true` on a case-insensitive filesystem,
  where the docs warn it exposes JSP source. On `<Connector>`, `maxPostSize` (default 2 MiB,
  form and multipart parameters only, so it is not a body-size limit) and
  `maxParameterCount` (default 1000) are the parsing limits, and a negative value means no
  limit. TLS and protocol choice are `sota-network-security`. **Version disclosure**: Tomcat
  sends no `Server` header unless the app or the connector's `server` attribute sets one, but
  `ErrorReportValve` `showServerInfo` defaults to `true` and prints the version on error
  pages. OWASP: Code Review Guide v2.

## Audit checklist

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
      disallow-list is weaker than an allow-list) ;
      `grep -rnE 'BeanUtils\.populate\(' --include='*.java' --include='*.kt' .`
      (the non-Spring spelling: every request parameter name becomes a setter call)
- [ ] **Authorization rules — HIGH** —
      `grep -rnE 'authorizeHttpRequests|requestMatchers|anyRequest|permitAll|ignoring\(' --include='*.java' --include='*.kt' .`
      (read each chain top-down: first match wins; the chain must end in `anyRequest()`;
      `web.ignoring()` on a non-static path is a finding)
- [ ] **Descriptor, annotation and code roles disagree — HIGH** (§1) —
      `grep -rnE 'metadata-complete="true"|<externally-defined|<run-as>|<run-as-role-assignment>|@RunAs\(' --include='*.xml' --include='*.java' --include='*.kt' .`
      (annotations ignored, roles defined outside the app, or elevated identity: each needs a
      reason) ;
      `grep -rhoE 'isUserInRole\("[^"]+"\)' --include='*.java' --include='*.kt' . | sed -E 's/.*\("([^"]+)"\)/\1/' | sort -u | while IFS= read -r role; do grep -rqE "<role-name>[[:space:]]*${role}[[:space:]]*</role-name>|DeclareRoles\([^)]*\"${role}\"" --include='*.xml' --include='*.java' --include='*.kt' . || echo "undeclared role: ${role}"; done`
      (a role named in code but declared nowhere in the app; then compare each
      `security-constraint` URL pattern with the `@ServletSecurity`/`@RolesAllowed` on the same
      target)
- [ ] **Filter order — MEDIUM, HIGH if the filter enforces tenancy or reads identity** —
      `grep -rnE 'implements (jakarta|javax)\.servlet\.Filter|extends OncePerRequestFilter|FilterRegistrationBean|@Order' --include='*.java' --include='*.kt' .`
      (confirm on the running app that each identity-reading filter runs after the security
      chain; an annotation is not evidence of the effective order)
- [ ] **CSRF disabled, or a write reachable by GET — HIGH on a cookie-session app** (§1) —
      `grep -rnE 'csrf\(\)\.disable\(|csrf\([[:space:]]*AbstractHttpConfigurer::disable|csrf\([^)]*->[^)]*\.disable\(|csrf[[:space:]]*\{[[:space:]]*disable\(' --include='*.java' --include='*.kt' .`
      (needs a written reason naming the non-cookie credential) ;
      `grep -rnE '^[[:space:]]+@RequestMapping' --include='*.java' --include='*.kt' . | grep -v 'method'`
      (an indented, method-level mapping with no `method` answers GET, which `CsrfFilter`
      never checks; read the handler: does it write?)
- [ ] **View names and dispatch targets from request data — HIGH** (§1) —
      `grep -rnE '"(redirect|forward):"[[:space:]]*\+|new ModelAndView\([[:space:]]*[^")[:space:]]|sendRedirect\(|getRequestDispatcher\(' --include='*.java' --include='*.kt' .`
      (each target must be a constant or an allowlist entry; a `forward:`/dispatcher target
      from input can read `WEB-INF`)
- [ ] **Code still running after a redirect or forward — HIGH after an auth check** (§1) —
      `grep -rnE -A1 'sendRedirect\(|\.forward\(|setHeader\("Location"' --include='*.java' --include='*.kt' . | grep -E '^[^:]+-[0-9]+-' | grep -vE '^[^:]+-[0-9]+-[[:space:]]*(return|throw|\}|$)'`
      (prints the statement after each call; a status set after `Location` is expected)
- [ ] **CORS: wildcard origin pattern with credentials — HIGH** (§1) —
      `grep -rnE 'allowedOriginPatterns\([^)]*"\*"|addAllowedOriginPattern\("\*"\)|originPatterns[[:space:]]*=[[:space:]]*"\*"|allowCredentials[[:space:]]*(\(|=)[[:space:]]*"?true' --include='*.java' --include='*.kt' .`
      (a `*` pattern and `allowCredentials` true on the same mapping reflect every origin;
      Spring's own `*` + credentials guard does not cover patterns)
- [ ] **Session IDs in URLs; app-set cookies without Secure/HttpOnly/SameSite — MEDIUM** (§1) —
      `grep -rnE 'new (jakarta\.servlet\.http\.|javax\.servlet\.http\.)?Cookie\(|encodeURL\(|encodeRedirectURL\(|tracking-modes|trackingModes|setSessionTrackingModes|<tracking-mode>' --include='*.java' --include='*.kt' --include='*.properties' --include='*.y*ml' --include='web.xml' .`
      (no cookie-only tracking-mode setting means Tomcat's default still includes `URL`) ;
      `grep -rlE 'new (jakarta\.servlet\.http\.|javax\.servlet\.http\.)?Cookie\(|ResponseCookie\.from\(' --include='*.java' --include='*.kt' . | while IFS= read -r f; do grep -qi 'samesite' "$f" || echo "$f"; done`
      (files creating a cookie that never set SameSite; at every creation site also confirm `setSecure(true)`/`setHttpOnly(true)` or `.secure(true).httpOnly(true)`)
- [ ] **Servlet container configuration — HIGH for deployment, linking and limits, MEDIUM for
      disclosure** (§1) —
      `grep -rnE '<Server[^>]*[[:space:]]port="[0-9]|autoDeploy="true"|deployOnStartup="true"|deployXML="true"|crossContext="true"|privileged="true"|allowLinking="true"|max(PostSize|ParameterCount)="-|showServerInfo="true"|[[:space:]]server="[^"]*[0-9]' --include='*.xml' .`
      (an enabled shutdown port must be on loopback with a non-default command) ;
      `grep -rL 'autoDeploy="false"' --include='server.xml' .`
      (lists each `server.xml` that leaves `autoDeploy` at its `true` default)
