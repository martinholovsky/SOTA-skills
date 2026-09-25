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
  `setXIncludeAware(false)`, `setExpandEntityReferences(false)` (OWASP XXE
  cheat sheet). Same care for YAML (`SnakeYAML` `SafeConstructor`) and XML-based
  formats.
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

## Audit checklist

- [ ] **XXE — CRITICAL (verify DTDs disabled)** —
      `grep -rnE 'DocumentBuilderFactory|SAXParserFactory|XMLInputFactory|TransformerFactory|SAXReader' --include='*.java' .`
      ;
      `grep -rn 'disallow-doctype-decl\|setExpandEntityReferences\|SafeConstructor' --include='*.java' . || echo "verify XXE hardening"`
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
