# 07 — XML: XXE, XSLT and Parser Hardening

Scope: every JDK and library XML parser, transformer and validator that can read
caller-influenced input. Split out of rules/04 (formerly section 3) on 2026-09-25; the section is
now §1. Maps to CWE-611 (XXE), CWE-91, CWE-776.

Core principle: **no JDK XML factory is safe by default; harden each one you create, in
one place.**

## 1. XML and XXE

- Disable DTDs and external entities on every parser
  (`DocumentBuilderFactory`, `SAXParserFactory`, `XMLInputFactory`,
  transformers):
  `setFeature("http://apache.org/xml/features/disallow-doctype-decl", true)`,
  disable `external-general-entities`/`external-parameter-entities`,
  `setXIncludeAware(false)` (OWASP XXE cheat sheet). The full per-parser settings are §2, the
  resolver that backs them §3. Same care for YAML (`SnakeYAML` `SafeConstructor`) and XML-based
  formats.
- **`setExpandEntityReferences(false)` is not an XXE control.** Its Javadoc is about whether
  entity reference nodes get expanded in the tree, not whether anything is fetched. Measured on
  Temurin 21.0.12 and 25.0.4 with it as the only setting, against a local HTTP listener: a
  general entity was not fetched, but an **external parameter entity** (the out-of-band XXE
  channel) and an **external DTD subset** were each fetched. Never count it as hardening.
- **The parsers people forget are also parsers.** `SchemaFactory`, `Validator` and
  `XPath.evaluate(expr, new InputSource(...))` each parse XML with their own defaults (an
  `XMLReader` from `getXMLReader()` needs the `SAXParserFactory` hardening above). Measured
  on Temurin 21.0.12 and 25.0.4 with an entity pointing at a local file:
  - `XPath.evaluate` over an `InputSource` returned the file's contents;
  - a `Validator` **echoed the file's contents in its validation error message**;
  - a `SchemaFactory` read an `xs:include` of a local `file:` URL.

  The fix differs from the `DocumentBuilderFactory` one. Set
  `XMLConstants.ACCESS_EXTERNAL_DTD` and `ACCESS_EXTERNAL_SCHEMA` to `""` on the
  `SchemaFactory` and on each `Validator`. With them set, both refused; the `Validator` said
  "'file' access is not allowed due to restriction set by the accessExternalDTD property".
  For XPath, parse with a hardened `DocumentBuilder` first and evaluate against the
  `Document`.
- **JDK 25 ships a stricter config file, and it is not a substitute.** The file is
  `$JAVA_HOME/conf/jaxp-strict.properties.template`, applied with
  `-Djava.xml.config.file=`. With it, the entity reads above failed on the catalog. The
  `SchemaFactory` `xs:include` of a local file **still succeeded** (Temurin 25.0.4). Keep the
  per-factory settings.
- **A stylesheet is code.** An XSLT from a caller can call Java through extension functions.
  Measured: on Temurin **21.0.12** a stylesheet calling
  `java.lang.System.getProperty` through the `xalan/java` namespace **ran by default**. On
  **25.0.4** it was refused, because that JDK's `conf/jaxp.properties` sets
  `jdk.xml.enableExtensionFunctions=false`. The exact JDK release where this default flipped
  was not verified. On either version, `FEATURE_SECURE_PROCESSING=true` refused it. Never
  compile a caller-supplied stylesheet. If you must, set that feature and the
  `ACCESS_EXTERNAL_STYLESHEET`/`ACCESS_EXTERNAL_DTD` properties to `""`, and treat any
  `enableExtensionFunctions=true` as a finding.

## 2. Per-parser hardening matrix (DOM, SAX, StAX, Validator, Transformer)

Settings are **optional** for an implementation: a parser may reject a feature it does not know,
and `DocumentBuilderFactory.setFeature` threw `ParserConfigurationException` for an unknown one
(measured, 25.0.4). **Fail closed**: let that exception abort startup, never catch and continue.
Create factories with `newDefaultInstance()` (`XMLInputFactory.newDefaultFactory()` for StAX;
present on every factory above plus `XPathFactory`, JDK 9+), so a classpath lookup cannot hand
you an implementation whose settings you did not test.

| Parser | Set on the object you parse with |
|---|---|
| DOM `DocumentBuilderFactory` | `disallow-doctype-decl` true; `FEATURE_SECURE_PROCESSING` true; `setAttribute(ACCESS_EXTERNAL_DTD, "")` and `ACCESS_EXTERNAL_SCHEMA`; `setXIncludeAware(false)`; `setValidating(false)` |
| SAX `SAXParserFactory` | the same features on the factory; the two `ACCESS_EXTERNAL_*` go through `SAXParser.setProperty`, since the SAX factory has no `setAttribute` |
| StAX `XMLInputFactory` | `setProperty(SUPPORT_DTD, false)`, or if a DTD must parse, `IS_SUPPORTING_EXTERNAL_ENTITIES` false; both default to **true** (read back on 25.0.4) |
| `SchemaFactory` / `Validator` | `setProperty(ACCESS_EXTERNAL_DTD, "")` and `ACCESS_EXTERNAL_SCHEMA` on the factory **and** each `Validator` (§1) |
| `TransformerFactory` | `FEATURE_SECURE_PROCESSING` true; `setAttribute` of `ACCESS_EXTERNAL_DTD` and `ACCESS_EXTERNAL_STYLESHEET` to `""` |

- **If a DTD must stay enabled**, turn off `external-general-entities`,
  `external-parameter-entities` and `nonvalidating/load-external-dtd` **together**. Any one
  left on is a fetch path. All measured on 21.0.12 and 25.0.4 against a local listener: an
  empty `ACCESS_EXTERNAL_DTD` refused both an external DTD and an external entity, and
  `SUPPORT_DTD=false` or `IS_SUPPORTING_EXTERNAL_ENTITIES=false` stopped the StAX fetch.
- **`setValidating(true)` undoes `load-external-dtd=false`**: with both set, the external DTD
  was fetched (measured).
- **`-Djdk.xml.dtd.support=deny`** (documented since JDK 22 for DOM, SAX, StAX, validation and
  transform) rejected any DOCTYPE on 25.0.4 in DOM and StAX. On 21.0.12 it was **silently
  ignored** and the fetch happened, so it is a JDK 22+ backstop, never the only control.
- **A resolver or `ACCESS_EXTERNAL_*` does not cap entity expansion.** Nested internal
  entities expanded to 1000 characters with a resolver installed and zero resolver calls
  (measured). The expansion limit is what stops a billion-laughs document. Measured with ten
  nested levels: 21.0.12 stopped at 64000 expansions by default and ran out of heap with
  `FEATURE_SECURE_PROCESSING` set to `false`; 25.0.4 stopped at 2500 either way. Never turn
  that feature off, and prefer `disallow-doctype-decl` or `dtd.support=deny`, which refuse it.
  OWASP: XML External Entity Prevention cheat sheet.

## 3. Deny-all resolvers and one secure factory

- **Install a resolver that refuses**, not one that returns nothing. The resolver is a method
  of the API itself, not an optional feature a parser may reject. Set an `EntityResolver` on
  **each** `DocumentBuilder` and `XMLReader` (the factories do not carry it), and
  `XMLInputFactory.RESOLVER` for StAX (which does pass it to its readers). Measured on
  21.0.12 and 25.0.4:
  - a resolver that throws: no fetch, parse fails;
  - one that **returns `null`** means "resolve it yourself", and the entity **was fetched**;
  - a StAX `XMLResolver` returning `""` **was fetched** as well;
  - `new InputSource(InputStream.nullInputStream())` (DOM/SAX) or
    `InputStream.nullInputStream()` (StAX) gave empty content with no fetch.
- **Allowlist only where references are legitimate** (SEI CERT IDS17-J): map each expected
  identifier to a local copy and refuse the rest. CERT's example returns an empty
  `InputSource` for unknown IDs, which failed with `MalformedURLException` (measured); a throw
  says what happened.
- **`SAXParser.parse(source, DefaultHandler)` replaces your resolver.** It installs the handler
  as the reader's `EntityResolver`, and `DefaultHandler.resolveEntity` returns `null`. Measured:
  deny resolver on `getXMLReader()`, then that overload, and the entity was fetched; calling
  `XMLReader.parse` directly refused. Use the reader, or override `resolveEntity` in the
  handler.
- **One secure-factory utility** builds every parser, transformer and validator with §2 and the
  resolver, and is the only place a factory is created. An audit then reduces to "does any code
  call a factory outside it". OWASP: XML External Entity Prevention cheat sheet.

## 4. Wrapper and binding libraries (dom4j, JDOM, JAXB, XDK)

A wrapper builds its own reader unless you hand it one. Pass the hardened `XMLReader` (from
`SAXParserFactory`, not `XMLReaderFactory`, which is `@Deprecated(since="9")`) or
`XMLStreamReader` in.

- **dom4j**: `new SAXReader()` fetched an external entity (2.2.0, measured). `setXMLReader`
  alone is not enough: `read()` installs the `SAXReader`'s own resolver on your reader, and
  when you set none on the `SAXReader` that is a default resolving any system ID (source).
  A deny resolver on the supplied reader was
  overwritten and the entity fetched; `SAXReader.setEntityResolver(deny)` refused it.
  `SAXReader.createDefault()` turns off the external-entity and load-external-dtd features and
  silently ignores a reader that rejects them, so do not rely on it alone.
- **JDOM**: `new SAXBuilder()` fetched (2.0.6.1, measured). Use
  `SAXBuilder(XMLReaderJDOMFactory)` returning your reader, or `setEntityResolver(deny)`.
- **JAXB** (`jakarta.xml.bind`): the `File`, `InputStream`, `Reader`, `URL` and `InputSource`
  overloads of `unmarshal` leave the parser to the implementation, whose defaults were not
  measured. On untrusted input use `unmarshal(XMLStreamReader)` from your hardened factory, or
  `unmarshal(Source)` with a `SAXSource` over your hardened reader.
- **Oracle XDK** (`oracle.xml.parser.v2`): Oracle's docs say `setSecureProcessing()` on the
  parser sets its entity-reference, DTD-object and expansion-depth attributes. Not measured.
  OWASP: XML External Entity Prevention cheat sheet.

## 5. Document-carried stylesheet and schema references; restricting your own imports

- **A document names its own stylesheet and schema, so whoever wrote the document does.** The
  `<?xml-stylesheet href=...?>` processing instruction, `xsi:schemaLocation` and
  `xsi:noNamespaceSchemaLocation` are input. Measured on Temurin 21.0.12 and 25.0.4 against a
  local listener:
  - `TransformerFactory.getAssociatedStylesheet` fetched nothing itself. The `Source` it returned
    had the PI's `href` as its system ID. Compiling that `Source` on a default factory fetched the
    remote stylesheet and ran it.
  - A `Validator` from the no-argument `SchemaFactory.newSchema()` fetched the schema named by
    `xsi:noNamespaceSchemaLocation`, and also the one named by `xsi:schemaLocation`. It refused once
    `ACCESS_EXTERNAL_SCHEMA` was `""` on both the factory and the validator. A `Schema` compiled
    from the application's own source ignored the hint and fetched nothing.

  Compile schemas from sources you ship, and never call `newSchema()` with no argument on caller
  documents. Treat an associated-stylesheet system ID as a key and check it against an allowlist
  of stylesheets you already hold, such as a map to precompiled `Templates`. Never pass the
  returned `Source` straight to `newTransformer`/`newTemplates`.
- **Your own `xsl:import`, `xsl:include`, `xs:include`/`xs:import` and `document()` references,
  in order of preference:**
  1. **A `CatalogResolver` in `strict` mode** (`javax.xml.catalog`, JDK 9+).
     `CatalogFeatures.Feature.RESOLVE` is documented as defaulting to `strict`, and
     `CatalogFeatures.defaults()` read `strict` on both JDKs. Build it with
     `CatalogManager.catalogResolver(features, catalogUri)`, then install it as the
     `TransformerFactory` `URIResolver` and the `SchemaFactory` `LSResourceResolver`. Measured:
     mapped references loaded from the local copy, and an unmapped `http:` reference threw with no
     fetch, for `xsl:import`, `xs:include` and a transform-time `document()`. The factory's resolver
     reached the transformer. With no resolver, the same `document()` call fetched.
  2. **A hand-written `URIResolver`/`LSResourceResolver` allowlist that throws for anything
     unlisted.** The same trap as §3 applies: the Javadoc of both says a `null` return asks the
     processor to resolve (open) the URI itself.
  3. **`ACCESS_EXTERNAL_*` alone.** It works per protocol only. With `ACCESS_EXTERNAL_STYLESHEET`
     set to `""`, the application's own local `file:` import was refused as well (measured). The
     usual response is to loosen it to `"file"` or `"all"`, which reopens every path under that
     scheme. Keep it as the backstop under 1 or 2, not the allowlist.

  OWASP: XML External Entity Prevention cheat sheet.

## Audit checklist

- [ ] **XXE — CRITICAL (verify DTDs disabled)** —
      `grep -rnE 'DocumentBuilderFactory|SAXParserFactory|XMLInputFactory|TransformerFactory|SAXReader' --include='*.java' --include='*.kt' .`
      ;
      `grep -rn 'disallow-doctype-decl\|SUPPORT_DTD\|setEntityResolver\|SafeConstructor' --include='*.java' --include='*.kt' . || echo "verify XXE hardening"`
      (`setExpandEntityReferences` is deliberately absent: it is not hardening, §1)
- [ ] **`setExpandEntityReferences(false)` counted as XXE hardening — HIGH when it is the only
      setting** (§1: a parameter entity and an external DTD were still fetched) —
      `grep -rnE 'setExpandEntityReferences\(' --include='*.java' --include='*.kt' .`
      (each hit's factory needs a real §2 control beside it)
- [ ] **Factory from a classpath lookup, validation on, or StAX DTD/external entities left on —
      HIGH** (§2) —
      `grep -rnE '(DocumentBuilderFactory|SAXParserFactory|TransformerFactory|SchemaFactory|XPathFactory)\.newInstance\(|XMLInputFactory\.new(Instance|Factory)\(|setValidating\([[:space:]]*true|(SUPPORT_DTD|IS_SUPPORTING_EXTERNAL_ENTITIES|supportDTD|isSupportingExternalEntities)"?,[[:space:]]*(true|Boolean\.TRUE)' --include='*.java' --include='*.kt' .`
      (a `newInstance` outside the one secure factory is the finding; also read each
      `setFeature`/`setAttribute` call site for a `catch` that logs and carries on)
- [ ] **Resolver that returns nothing, or one silently replaced — HIGH** (§3: `null` and a StAX
      `""` were both fetched) —
      `grep -rnE '(setEntityResolver|setXMLResolver|RESOLVER,)[^;]*->[[:space:]]*(null|""|new InputSource\(\))|\.parse\([^;,]*,[[:space:]]*(new [A-Za-z]*Handler\(|[A-Za-z_]*[hH]andler[[:space:]]*\))' --include='*.java' --include='*.kt' .`
      ; `grep -rnE -A6 '(InputSource|Object) resolveEntity\(' --include='*.java' --include='*.kt' . | grep -E 'return[[:space:]]+(null|"")'`
      (a two-argument `SAXParser.parse(src, handler)` discards the reader's resolver)
- [ ] **Wrapper or binding library building its own reader — HIGH on untrusted input** (§4:
      dom4j and JDOM defaults both fetched) —
      `grep -rnE 'new SAXReader\(|SAXReader\.createDefault\(|new SAXBuilder\(|XMLReaderFactory\.createXMLReader\(|\.unmarshal\([[:space:]]*[^)[:space:]]' --include='*.java' --include='*.kt' . | grep -vE 'unmarshal\([[:space:]]*(new SAXSource|[A-Za-z_.]*(streamReader|StreamReader|saxSource|SAXSource))'`
      (each `SAXReader` needs `setEntityResolver`; each `unmarshal` argument must be a hardened
      `XMLStreamReader` or `SAXSource`)
- [ ] **XXE in the parsers the grep above does not name — CRITICAL on reachable input** (§1;
      measured: `Validator` echoed a local file in its error, `SchemaFactory` read an
      `xs:include`, `XPath` over an `InputSource` returned the file) —
      `grep -rnE 'SchemaFactory|newValidator\(|getXMLReader\(|XMLReaderFactory|\.evaluate\([^;]*new InputSource' --include='*.java' --include='*.kt' .`
      ; then `grep -rnE 'ACCESS_EXTERNAL_(DTD|SCHEMA|STYLESHEET)' --include='*.java' --include='*.kt' .`
      (a `SchemaFactory`/`Validator` with no matching `setProperty(..., "")` is the finding;
      the JDK strict config template did NOT stop the `xs:include`)
- [ ] **Caller-supplied XSLT — CRITICAL** (§1: extension functions ran by default on JDK
      21.0.12) — `grep -rnE 'newTransformer\([^)]|newTemplates\(|enableExtensionFunctions' --include='*.java' --include='*.kt' --include='*.properties' .`
      (trace each stylesheet `Source` to a constant; `enableExtensionFunctions=true` is a
      finding on sight; `newTransformer()` with no argument is the identity transform and
      does not match)
- [ ] **Stylesheet or schema chosen by the document, or own imports with no resolver — HIGH,
      CRITICAL when the stylesheet is compiled** (§5: the PI's stylesheet was fetched and ran; a
      no-argument `newSchema()` fetched the `xsi:` location) —
      `grep -rnE 'getAssociatedStylesheet\(|\.newSchema\([[:space:]]*\)' --include='*.java' --include='*.kt' .`
      (trace each returned `Source` to an allowlist lookup) ;
      `grep -rlE 'TransformerFactory|SchemaFactory' --include='*.java' --include='*.kt' . | while IFS= read -r f; do grep -qE 'setURIResolver|setResourceResolver|catalogResolver\(' "$f" || echo "$f: factory with no resolver"; done`
      (fine if the §3 secure factory installs it elsewhere; an `ACCESS_EXTERNAL_STYLESHEET` or
      `ACCESS_EXTERNAL_SCHEMA` of `"all"` or `"file"` is the loosened backstop)
- [ ] **No XXE-specific SAST gate — HIGH** (the greps above are for a review; CI needs a rule set
      that fails the build). Find-Sec-Bugs (1.14.0) reports `XXE_DOCUMENT`, `XXE_SAXPARSER`,
      `XXE_XMLREADER`, `XXE_XMLSTREAMREADER`, `XXE_XPATH`, `XXE_SCHEMA_FACTORY`, `XXE_VALIDATOR`,
      `XXE_DTD_TRANSFORM_FACTORY` and `XXE_XSLT_TRANSFORM_FACTORY`. The Semgrep/Opengrep rule
      repositories carry `documentbuilderfactory-disallow-doctype-decl-missing`,
      `saxparserfactory-disallow-doctype-decl-missing`, `transformerfactory-dtds-not-disabled`
      (under `java/lang/security/audit/xxe/`) and `xmlinputfactory-possible-xxe` (`rules/06` §3) —
      `grep -rlE 'findsecbugs|java[./]lang[./]security[./]audit[./]xxe|xmlinputfactory-possible-xxe' --include='pom.xml' --include='*.gradle' --include='*.gradle.kts' --include='*.yml' --include='*.yaml' . || echo "FINDING: no XXE-capable SAST rule set configured"`
      ; a gate that cannot fail, or XXE patterns excluded:
      `grep -rnE 'pattern="[^"]*XXE_|failOnError>false|spotbugs\.failOnError=false|ignoreFailures[[:space:]]*=[[:space:]]*true' --include='*exclude*.xml' --include='pom.xml' --include='*.gradle' --include='*.gradle.kts' --include='*.properties' .`
      (an exclude filter under another file name needs a separate read)
