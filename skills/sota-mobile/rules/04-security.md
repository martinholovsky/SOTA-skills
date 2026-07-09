# 04 — Mobile Security

Threat model first: the attacker **owns the device**. They can decompile your binary (jadx, Hopper), hook your functions at runtime (Frida, objection), proxy and strip your TLS, and read any file your app writes. Two consequences drive every rule here:

1. Client-side mechanisms raise attacker *cost* — they are deterrents. Only the server *enforces*.
2. Anything in the binary — strings, endpoints, keys, feature flags — is public the day you ship.

Anchor audits to **OWASP MASVS v2.1** (control groups: MASVS-STORAGE, -CRYPTO, -AUTH, -NETWORK, -PLATFORM, -CODE, -RESILIENCE, -PRIVACY) with the **MASTG v2** (v2.0.0 stable since June 2026; modular tests with stable `MASTG-TEST-*` IDs — cite the IDs in findings) for concrete test procedures. An audit should be able to state, per group, what was examined.

## Storage & secrets

### 4.1 Secrets go in Keychain/Keystore — nothing else, ever

- **iOS:** Keychain Services. Default to the most restrictive accessibility that works — `kSecAttrAccessibleWhenUnlockedThisDeviceOnly` for tokens; never `kSecAttrAccessibleAlways`-class. `ThisDeviceOnly` variants keep items out of backups and off other devices.
- **Android:** key material in **Android Keystore** (request StrongBox where available); secrets-at-rest encrypted with a Keystore-held key via a maintained wrapper (e.g., Tink). Note Jetpack's `EncryptedSharedPreferences`/`security-crypto` was deprecated — verify the currently recommended wrapper before adopting one; the architecture (Keystore key + AEAD over the value) is what matters.
- `UserDefaults`, `SharedPreferences`, plists, unencrypted SQLite/Room/Core Data, and `Documents/` are **plaintext to a rooted/jailbroken device and frequently included in backups**. Tokens, session cookies, API secrets, or PII caches in any of them = CRITICAL.

```kotlin
// BAD — plaintext on disk, readable by root, may land in cloud backups
prefs.edit().putString("refresh_token", token).apply()

// GOOD — AEAD over the value, key non-exportable in hardware
val aead: Aead = keystoreBackedAead("token_key")          // Tink AndroidKeystore integration
prefs.edit().putString("refresh_token",
    aead.encrypt(token.toByteArray(), "rt".toByteArray()).b64()).apply()
```

```swift
// GOOD — Keychain with tight accessibility
var query: [String: Any] = [
    kSecClass as String: kSecClassGenericPassword,
    kSecAttrService as String: "auth.refreshToken",
    kSecValueData as String: tokenData,
    kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
]
SecItemAdd(query as CFDictionary, nil)
```

- **Hardcoded secrets are public.** `strings`-level extraction defeats them; "obfuscated" keys delay extraction by hours. Anything truly secret stays server-side. Client "API keys" (Maps, analytics) are identifiers, not secrets — restrict them server-side (bundle ID / SHA-256 signing-cert restrictions, quotas, per-key scopes).
- Scope backups away from secret stores: Android `dataExtractionRules` excluding the encrypted prefs/DB files; iOS `URLResourceValues.isExcludedFromBackup` for sensitive caches.
- Screen-level leakage: redact sensitive screens in the app switcher (iOS: overlay on `sceneWillResignActive`); Android `FLAG_SECURE` on screens showing credentials/financial data (applied selectively — it also blocks the user's own screenshots); mark sensitive fields to suppress keyboard learning (`textContentType`/`importantForAutofill`, `isSecureTextEntry`).

### 4.2 Biometric auth gates a key, not a boolean

`if (biometricSuccess) { showVault() }` is defeated by hooking one return value with Frida. The correct design makes biometrics **cryptographically load-bearing**: the secret is encrypted under a hardware key that the secure element will only operate *after* user authentication. No hook can conjure the plaintext.

```kotlin
// BAD — a boolean a hook flips
biometricPrompt.authenticate(...)  // onSuccess: { unlockVault() }

// GOOD — key usable only after biometric auth; decryption fails without it
val spec = KeyGenParameterSpec.Builder("vault", PURPOSE_ENCRYPT or PURPOSE_DECRYPT)
    .setBlockModes(BLOCK_MODE_GCM).setEncryptionPaddings(ENCRYPTION_PADDING_NONE)
    .setUserAuthenticationRequired(true)
    .setUserAuthenticationParameters(0, AUTH_BIOMETRIC_STRONG)  // per-use, strong class only
    .setInvalidatedByBiometricEnrollment(true)                  // new finger ≠ your finger
    .build()
// Pass the Cipher in a CryptoObject through BiometricPrompt; decrypt with the returned cipher.
```

```swift
// GOOD — Keychain item gated by current biometric set
let acl = SecAccessControlCreateWithFlags(nil,
    kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly,
    .biometryCurrentSet, nil)   // re-enrollment invalidates the item
```

- `biometryCurrentSet` / `setInvalidatedByBiometricEnrollment(true)` are mandatory: without them, an attacker with the passcode adds their own fingerprint and unlocks everything.
- Android: require `BIOMETRIC_STRONG` for key release; Class 2 (weak) biometrics must not gate cryptography.
- Biometrics are **local user verification only** — never proof of identity to a server. Server auth remains tokens; biometrics merely authorize use of the locally stored token/key. "We send `biometric: true` to the API" is a CRITICAL design finding.

## Network

### 4.3 TLS everywhere; pin only with an exit strategy

- No cleartext, no exceptions baked in to "make staging work": iOS ATS stays fully on (any `NSAllowsArbitraryLoads` in a release build is HIGH); Android Network Security Config with `cleartextTrafficPermitted="false"`.
- **Certificate pinning** defends users on hostile networks against rogue/compromised CAs. It also bricks your app's networking if keys rotate and the pins don't — and you can't roll back binaries. If you pin:
  - Pin **SPKI hashes**, not certificates; pin your CA/intermediate or include **at least one backup pin** for an offline-held key.
  - Use platform mechanisms: Android Network Security Config `<pin-set expiration="...">` (expiration = graceful failure to unpinned TLS rather than permanent brickage); iOS `NSPinnedDomains` in Info.plist or a URLSession challenge delegate.
  - Ship a **remote kill switch** for pinning enforcement (rules/06 §6.4) and an update path before any planned rotation.
  - Without a backup pin and a rotation runbook, pinning is a self-inflicted outage scheduled for cert-renewal day — for most apps that's worse than not pinning.
- Accept what pinning is not: it does not protect your API from the device's owner — Frida unpinning scripts are commodity. That problem is attestation (4.5) plus server-side controls.

### 4.4 Token handling

- OAuth2/OIDC with **short-lived access tokens (minutes-hours) + rotating refresh tokens**, refresh token stored per 4.1. Server implements refresh-token rotation with reuse detection (a replayed old refresh token kills the family).
- Third-party/IdP auth flows run in the **system browser** — `ASWebAuthenticationSession` (iOS) / Custom Tabs (Android) — **with PKCE**. Never an embedded WebView: it's phishable (no URL bar), cookie-isolated, and rejected by major IdPs.
- **No tokens in URLs.** Not in deep links (history, referrers, other apps' interception), not in push payloads, not in query strings of GETs that hit logs/CDNs, not in analytics events, not in crash breadcrumbs. Magic-link pattern: the link carries a one-time short-lived code, exchanged server-side for tokens.
- Logout is a checklist, not a navigation event: revoke server-side → wipe Keychain/Keystore entries → clear WebView cookies/storage → disassociate push token (rules/03 §3.9) → clear in-memory caches. Audit by logging out and inspecting what survives.
- Clock skew: never validate token expiry against device time alone (users set clocks wrong); honor server 401s as truth.

### 4.5 App attestation for endpoints worth abusing

For endpoints attractive at scale — auth, signup, promotions, scraping-prone content APIs — add hardware-backed attestation, verified **server-side**:

- **iOS: App Attest** (+ DeviceCheck bits for per-device state). **Android: Play Integrity API** — SafetyNet Attestation is fully shut down (since January 2025); any code still calling it is dead code at best.
- Play Integrity verdict policy is a *decision table*, not a boolean. Current verdict mechanics: `MEETS_STRONG_INTEGRITY` requires hardware-backed signals and a recent security patch (on Android 13+, patched within ~12 months). Hard-requiring strong integrity locks out a long tail of real users on old-but-honest devices. Typical policy: deny on failed basic/device integrity; step-up (challenge, friction) when strong integrity is absent; log everything for tuning. Use the Integrity API's remediation dialogs where user-fixable.
- Bind attestation to requests (challenge nonces, not bare verdict caching) or attackers replay verdicts.
- Attestation raises bot cost substantially; it is still not absolute (device farms with genuine hardware exist). Keep server-side rate limiting, anomaly detection, and abuse economics as the real control.

## Platform attack surface

### 4.6 Deep links and universal links: untrusted input from hostile neighbors

Any app on the device can fire intents/URLs at yours. Rules:

- Prefer **verified links**: iOS Universal Links (apple-app-site-association) and Android App Links (`assetlinks.json` + `android:autoVerify="true"`). Custom URI schemes (`myapp://`) are claimable by any installed app — never use them for auth callbacks or sensitive flows. (Exception: OAuth-with-PKCE makes scheme interception unprofitable, but https callbacks remain preferable.)
- **One central router** (rules/02 §2.7) validates every inbound link: allowlist host+path patterns, type-check and bound every parameter, then **re-authenticate and re-authorize before showing protected content**. A deep link is a navigation *request*, not an authorization *grant* — `app.example/account/42` shows account 42 only if the current session owns it. Skipping authz because "the screen is deep inside the app" is the classic IDOR-by-deep-link.
- Never feed deep-link parameters into: WebView URLs (open redirect → token/session theft), file paths (traversal), SQL, or `Intent` forwarding.

```kotlin
// BAD: trusts the URL wholesale, loads attacker-controlled page in an authed WebView
fun handle(uri: Uri) { webView.loadUrl(uri.getQueryParameter("next")!!) }

// GOOD: allowlist route parsing, typed params, authz at the destination
sealed interface DeepLink {
    data class Order(val id: OrderId) : DeepLink
    data object Inbox : DeepLink
}
fun parse(uri: Uri): DeepLink? = when {
    uri.host != "app.example.com" -> null
    uri.pathSegments.firstOrNull() == "orders" ->
        uri.pathSegments.getOrNull(1)?.let { OrderId.parse(it) }?.let(DeepLink::Order)
    else -> null   // unknown = dropped, logged
}
```

- Android component hygiene: `android:exported="false"` unless deliberately public; validate callers of exported components; explicit intents internally; no forwarding of received intents (intent-redirection vulnerability class); `PendingIntent.FLAG_IMMUTABLE` unless mutation is specifically required.

### 4.7 WebView hardening

Every WebView is a full browser engine you ship, configured by you:

- **Default-deny:** JavaScript off unless the content needs it; `allowFileAccess=false`, `allowContentAccess=false`; never load `file://` or untrusted content with file access on; block geolocation/permissions prompts unless required.
- **Constrain navigation:** `shouldOverrideUrlLoading` / `WKNavigationDelegate` allowlists your origins; external links go to the system browser/Custom Tabs, which has the URL bar and sandbox your WebView lacks.
- **JS bridges are RPC endpoints exposed to whatever page loads.** `addJavascriptInterface` / `WKScriptMessageHandler` rules: attach only when loading your own origins; check the message's source origin per call; expose narrow, typed methods — never generic `eval`, `openUrl`, `getAuthToken` bridges. The canonical CRITICAL chain is: deep-link parameter → WebView URL → hostile page → token-returning JS bridge. Two rules above each independently break that chain; implement both.
- Don't build login inside WebViews (4.4); don't share the app's session cookies with arbitrary web content; clear WebView cookies/storage on logout; keep the WebView component updated (Android System WebView updates via Play — minSdk policy affects which engine versions you see).

### 4.8 Root/jailbreak detection: honest deterrence only

Hand-rolled detection (su binary checks, jailbreak file paths, hook-framework scans) is bypassed by commodity tooling (Magisk DenyList, Shamiko, Frida hide scripts) precisely for the attackers who matter, while false-positiving on harmless power users. Honest posture:

- Prefer **server-verified attestation** (4.5) over client-side checks; decide consequences server-side where they can't be patched out.
- Degrade rather than block where possible (hide cached credentials, require fresh auth, disable offline vaults) unless regulation mandates hard blocks — and if it does, document that the block is best-effort.
- In design docs and audits, never let root/JB detection be listed as a *control*. An app whose data protection depends on jailbreak detection has no data protection — the protection is Keychain/Keystore hardware semantics (4.1) and server enforcement.

### 4.9 Reverse-engineering posture: obfuscation is a speed bump, design like the binary is open source

- Android: **R8** on for release (shrinking + obfuscation) — its real value is size and noise; keep and archive `mapping.txt` per release (also needed for crash symbolication, rules/06). Commercial protectors (DexGuard, iXGuard) buy *time*, justified mainly for finance/DRM threat models; budget for the build-pipeline and crash-debugging tax they impose.
- iOS: strip symbols in release; compiled Swift resists casual reading; no `#if DEBUG` backdoors, staging endpoints, or test bypasses compiled into release builds (audit: grep release artifacts, not source).
- **Premium features are server-entitled, never client-flag-gated.** A client-side `isPremium` boolean is flipped once in a patched APK and redistributed forever; the server checking entitlement per request is unpatchable.
- Logs are an exfiltration channel: release builds log no PII/tokens (Timber tree swap; `os_log` with `%{private}` specifiers; proguard rules don't accidentally keep debug log calls). Crash breadcrumbs follow the same rule.

### 4.10 Privacy is a security surface and a store-enforcement surface

- Collect the minimum (MASVS-PRIVACY). Every collected data type must appear accurately in the iOS privacy manifest → Privacy Nutrition Label and the Android **Data safety form**. Mismatches between declared and observed behavior (proxy the app and compare) are both an audit finding and a store-enforcement risk.
- Third-party SDKs inherit your permissions and your users' trust: maintain an SDK inventory with each SDK's data collection; on iOS, commonly-used SDKs must ship their own **privacy manifest and signature** — prefer SDKs that do.
- iOS ATT: prompt only if you actually track across apps/sites; IDFA reads without consent return zeros and invite rejection. Gate analytics/ads SDK initialization behind consent where GDPR/CCPA applies — initializing then asking is the pattern regulators fine.
- Don't request permissions you can avoid (photo *picker* instead of library permission; coarse instead of fine location) — each permission is attack surface, review friction, and user trust spent.

## Audit checklist

- [ ] Grep + decompile spot-check: no secrets/tokens/PII in UserDefaults, SharedPreferences, plists, unencrypted DBs, hardcoded strings, or release logs.
- [ ] Keychain items use `WhenUnlockedThisDeviceOnly`-class accessibility; Android secrets AEAD-encrypted under Keystore keys; StrongBox/Secure Enclave requested where available.
- [ ] Backup rules exclude secret stores; app-switcher snapshots redacted on sensitive screens; `FLAG_SECURE` where warranted; sensitive fields opted out of keyboard learning/autofill.
- [ ] Biometrics release hardware-bound keys (`setUserAuthenticationRequired` + STRONG class / `biometryCurrentSet`); enrollment changes invalidate; no boolean-gated auth; nothing sends "biometric ok" to a server as identity.
- [ ] ATS fully on / cleartext off in release config; if pinned: SPKI pins + backup pin + expiry + remote disable + rotation runbook.
- [ ] OAuth via system browser + PKCE; refresh rotation with reuse detection; no tokens in deep links, pushes, query strings, logs, analytics, or breadcrumbs; logout verified to wipe Keychain/Keystore, WebView state, push association.
- [ ] High-value endpoints verify App Attest / Play Integrity server-side with nonce binding and a written per-verdict policy; no SafetyNet remnants; rate limiting exists independently.
- [ ] Deep links: verified app/universal links for sensitive flows; central allowlist router; typed params; authz re-checked at destination; params never reach WebView URLs, paths, SQL, or forwarded intents.
- [ ] Android: `exported=false` default; explicit internal intents; immutable PendingIntents; exported components validate callers.
- [ ] WebViews: JS/file access default-off; navigation origin-allowlisted; bridges narrow, typed, origin-checked; no auth flows inside WebViews; WebView state cleared on logout.
- [ ] Root/JB posture documented as deterrent; consequences decided server-side; no design doc lists client detection as a control.
- [ ] R8/symbol stripping on; mapping files archived; no debug backdoors in release artifacts; premium features server-entitled.
- [ ] Privacy manifest + Data safety form match observed network behavior; SDK inventory current; ATT/consent gates precede SDK initialization; permissions minimized (picker over library, coarse over fine).
- [ ] Findings mapped to MASVS v2.1 groups; every group either has findings or an explicit "examined, clean."
