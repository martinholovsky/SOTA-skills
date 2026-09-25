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
- **Trust only the system CA store in release.** A `<trust-anchors>` block containing `<certificates src="user" />` outside `<debug-overrides>` makes any CA the device owner (or malware, or an MDM profile) installed a valid issuer for your API — HIGH. `debug-overrides` is ignored when `android:debuggable` is false, so that is the only safe home for a proxy CA. The platform default for apps with **`targetSdkVersion` 23 or lower** already includes user CAs, so a stale target SDK re-opens this without any config line. On iOS, weakening hides in per-domain keys under `NSExceptionDomains` as well as the global switch: `NSExceptionAllowsInsecureHTTPLoads = YES`, `NSExceptionMinimumTLSVersion` below the `TLSv1.2` default, `NSExceptionRequiresForwardSecrecy = NO` (which also drops the key-length check). Each is a finding that needs a written justification, the same as `NSAllowsArbitraryLoads`. OWASP: MASTG-TEST-0285, MASTG-TEST-0286, MASTG-TEST-0342.
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
- **Act on the app half of the verdict, not only the device half.** A genuine, patched phone can run a repackaged copy of your app. On Play Integrity, first check that `requestDetails` matches the request, then require `appIntegrity.appRecognitionVerdict == PLAY_RECOGNIZED` and compare `packageName` and `certificateSha256Digest` to your own values. `UNRECOGNIZED_VERSION` means the certificate or package name is not the one Play distributes: treat it as a modified binary. Use `accountDetails.appLicensingVerdict` (`LICENSED` = the user got the app from Play) only where sideloading itself should matter. On App Attest, the server confirms that the RP ID hash equals SHA-256 of your App ID (team prefix + bundle ID), that the counter is 0 at attestation, and that the `aaguid` matches the production environment. A server that reads only `deviceIntegrity` and ignores these fields has accepted any re-signed APK.
- On-device checks add cost but no certainty. Comparing the running signing certificate (`PackageManager.GET_SIGNING_CERTIFICATES`, API 28+) or a checksum of your own code against a baked-in value costs an attacker a patch and a re-sign. Because the check lives in the binary it guards, it is a deterrent layered under the server verdict (4.8), never a substitute for it. OWASP: MASTG-TEST-0050, MASVS-RESILIENCE-2, OWASP Cornucopia CMQ, RS4, RSQ.
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
- **Settings that must stay at their safe values:**
  - *Safe Browsing* is on by default on devices that support it. Opting out through `setSafeBrowsingEnabled(false)` or the `android.webkit.WebView.EnableSafeBrowsing` manifest meta-data needs a written reason.
  - *File-origin flags*: `setAllowFileAccessFromFileURLs` and `setAllowUniversalAccessFromFileURLs` (both deprecated in API 30 as insecure) stay `false`. Turning them on lets script in a `file://` page read other local files, including WebView cookies and app-private data. Serve bundled content through `androidx.webkit.WebViewAssetLoader` over https instead of `file://`. `setAllowFileAccess` defaults to `true` for apps targeting API 29 and below, so set it to `false` explicitly.
  - *iOS file scope*: `loadFileURL(_:allowingReadAccessTo:)` grants read access to the whole second argument. Pass the file itself, or the narrowest directory it needs, never the app's Documents or home directory.
  - *Debugging*: `WebView.setWebContentsDebuggingEnabled(true)` lets anyone with adb inspect and modify every WebView in the app. Since WebView 113 it switches on by itself when the app is `android:debuggable`, so a debuggable release (4.9) is also an inspectable one. `WKWebView.isInspectable` (iOS 16.4+, default `false`) stays off in release. Gate both on a debug build flag.
  - *`UIWebView`* is deprecated since iOS 12, and Apple stopped accepting new apps that use it in April 2020 and updates in December 2020. Any reference to it, including one inside a third-party SDK, is a finding. OWASP: MASTG-TEST-0227, MASTG-TEST-0331, MASTG-TEST-0333, MASTG-TEST-0335, MASTG-TEST-0336, MASTG-TEST-0399, OWASP Cornucopia PCJ.
- Don't build login inside WebViews (4.4); don't share the app's session cookies with arbitrary web content; clear WebView cookies/storage on logout; keep the WebView component updated (Android System WebView updates via Play — minSdk policy affects which engine versions you see).

### 4.8 Root/jailbreak detection: honest deterrence only

Hand-rolled detection (su binary checks, jailbreak file paths, hook-framework scans) is bypassed by commodity tooling (Magisk DenyList, Shamiko, Frida hide scripts) precisely for the attackers who matter, while false-positiving on harmless power users. Honest posture:

- Prefer **server-verified attestation** (4.5) over client-side checks; decide consequences server-side where they can't be patched out.
- Degrade rather than block where possible (hide cached credentials, require fresh auth, disable offline vaults) unless regulation mandates hard blocks — and if it does, document that the block is best-effort.
- In design docs and audits, never let root/JB detection be listed as a *control*. An app whose data protection depends on jailbreak detection has no data protection — the protection is Keychain/Keystore hardware semantics (4.1) and server enforcement.

### 4.9 Reverse-engineering posture: obfuscation is a speed bump, design like the binary is open source

- Android: **R8** on for release (shrinking + obfuscation) — its real value is size and noise; keep and archive `mapping.txt` per release (also needed for crash symbolication, rules/06). Commercial protectors (DexGuard, iXGuard) buy *time*, justified mainly for finance/DRM threat models; budget for the build-pipeline and crash-debugging tax they impose.
- iOS: strip symbols in release; compiled Swift resists casual reading; no `#if DEBUG` backdoors, staging endpoints, or test bypasses compiled into release builds (audit: grep release artifacts, not source).
- **A release build is not debuggable, and you check the artifact to prove it.** On Android, `android:debuggable="true"` (in Gradle, `isDebuggable = true` on a build type) lets a debugger attach, and it also switches on WebView debugging (4.7) and honours the `<debug-overrides>` trust anchors (4.3). On iOS the equivalent is the `get-task-allow` entitlement (`com.apple.security.get-task-allow` on macOS). Apple's notarization guidance says the macOS form gets around security checks so a debugger can work, that in a shipping app it can let an attacker inject code at runtime, and that Xcode's standard export removes it. Source config can be right while the shipped build is wrong: a custom signing or re-signing step, or a build type copied from `debug`. So the check runs on the built APK and the exported IPA (rules/06 §6.9 RC ritual). OWASP: MASTG-TEST-0039, MASTG-TEST-0082, MASTG-TEST-0226, MASTG-TEST-0261.
- **Premium features are server-entitled, never client-flag-gated.** A client-side `isPremium` boolean is flipped once in a patched APK and redistributed forever; the server checking entitlement per request is unpatchable.
- Logs are an exfiltration channel: release builds log no PII/tokens (Timber tree swap; `os_log` with `%{private}` specifiers; proguard rules don't accidentally keep debug log calls). Crash breadcrumbs follow the same rule.

### 4.10 Privacy is a security surface and a store-enforcement surface

- Collect the minimum (MASVS-PRIVACY). Every collected data type must appear accurately in the iOS privacy manifest → Privacy Nutrition Label and the Android **Data safety form**. Mismatches between declared and observed behavior (proxy the app and compare) are both an audit finding and a store-enforcement risk.
- Third-party SDKs inherit your permissions and your users' trust: maintain an SDK inventory with each SDK's data collection; on iOS, commonly-used SDKs must ship their own **privacy manifest and signature** — prefer SDKs that do.
- iOS ATT: prompt only if you actually track across apps/sites; IDFA reads without consent return zeros and invite rejection. Gate analytics/ads SDK initialization behind consent where GDPR/CCPA applies — initializing then asking is the pattern regulators fine.
- Don't request permissions you can avoid (photo *picker* instead of library permission; coarse instead of fine location) — each permission is attack surface, review friction, and user trust spent.

## Device data and the inter-app surface

### 4.11 Where non-secret app data lives: app-private vs shared storage, file protection classes, App Group containers

Secrets follow 4.1. This rule covers everything else sensitive: PII caches, downloaded documents, exports, message databases.

- **Android: app-private storage only.** Use `getFilesDir()`/`getCacheDir()`, Room, or DataStore. Shared storage (`MediaStore`, the Storage Access Framework, `Environment.getExternalStoragePublicDirectory`) is readable by other apps by design. For apps targeting API 29 or lower, scoped storage is not enforced, so any app with `READ_EXTERNAL_STORAGE` can read *everything* on external storage, including `getExternalFilesDir()`, and one with `WRITE_EXTERNAL_STORAGE` can plant files there that your app later loads. Never request `MANAGE_EXTERNAL_STORAGE` (all-files access) unless you are building a file manager. If sensitive data must go outside the sandbox, encrypt it under a Keystore key first.
- **No world-readable modes.** `MODE_WORLD_READABLE`/`MODE_WORLD_WRITEABLE` throw `SecurityException` from Android 7.0 on. Code that still passes them is either dead or falling back to something worse, such as a `chmod` or a copy to shared storage. Share through a `FileProvider` with a per-URI grant (4.14).
- **iOS: set a Data Protection class; don't inherit it.** When you set nothing, iOS applies `completeUntilFirstUserAuthentication`, which leaves the file readable whenever the device is locked after the first unlock since boot. Write sensitive files with `.completeFileProtection` (`Data.WritingOptions`) or set `FileProtectionType.complete`, or make it the app-wide default with the `com.apple.developer.default-data-protection` entitlement (`NSFileProtectionComplete`). Drop a class only for files that background work must touch while the device is locked, and write down which ones and why (rules/03 §3.6). `FileProtectionType.none`/`.noFileProtection` on user data is a finding.
- **Shared containers are shared.** Treat data in an App Group container (`containerURL(forSecurityApplicationGroupIdentifier:)`, a suite-named `UserDefaults`) or in a keychain item under a shared access group (`keychain-access-groups`, `kSecAttrAccessGroup`) as readable and writable by *every* app and extension in that group. That includes the share extension or widget with the weakest code. If an app has any keychain access group, items it adds without a `kSecAttrAccessGroup` go into the first group in its list, not into an app-only one. Set the group explicitly on every `SecItemAdd`. Put in a group only what every member needs, and validate what you read back (4.12). OWASP: MASTG-TEST-0056, MASTG-TEST-0200, MASTG-TEST-0201, MASTG-TEST-0202, MASTG-TEST-0299, MASTG-TEST-0303, MASTG-TEST-0388, OWASP Mobile Application Security cheat sheet.

### 4.12 Data read back from the device or downloaded is untrusted: integrity and safe parsing

On a rooted or jailbroken device, or after a restore from a backup the user edited, anything the app persisted can come back changed. That covers prefs and `UserDefaults`, plists, files, SQLite/Room/Core Data rows, serialized objects, and cached downloaded config or content. An app that trusts what it wrote yesterday has a client-side authorization flaw.

- **Security-relevant values are not stored client-side as authority.** Entitlements, roles, PIN-attempt counters, lockout timers and feature unlocks live on the server (4.9). When a value must be cached offline, store it with a MAC under a non-exportable key (an Android Keystore HMAC key; CryptoKit `HMAC` with a key held in the Keychain) or as a server-signed blob. Verify the MAC before acting on the value, and treat a failed check as "absent", not as "trusted default". The encoding, expiry and verify-then-parse rules are the generic signed-blob rules in `sota-code-security` rules/04 §7.
- **Validate on read, not only on write.** Type-check and bound every field loaded from local storage or a downloaded file, just as you would a network response. Parse with a schema-checked decoder, never a polymorphic deserializer that reads type names out of the data. Reject records that fail, rather than crashing or partly applying them.
- **Downloaded config and content** (remote config, feature-flag payloads, rule sets, HTML/JS bundles, ML models) are checked for integrity before first use and again on each load from cache: a signature or a pinned hash from the server, over TLS (4.3). A cache directory another process can write to (4.11) turns a verified download into an unverified one. OWASP: MASTG-TEST-0002, MASTG-TEST-0047, MASTG-TEST-0079, MASTG-TEST-0090, MASTG-TEST-0338, MASTG-TEST-0387, OWASP Cornucopia NS9, RSJ.

### 4.13 Sensitive data in the UI: masking, clipboard, screenshots

Screen-level leakage (app-switcher snapshots, `FLAG_SECURE`, keyboard learning) is in 4.1. The clipboard is the other exit.

- **Secret fields can't be copied.** Password, OTP, card-number and recovery-phrase fields turn off copy and cut: `isSecureTextEntry`, or override `canPerformAction(_:withSender:)` on iOS; on Android, a password `inputType` or a `customSelectionActionModeCallback` that removes copy. When the product needs a "copy" button (a generated password, an account number), treat it as a deliberate, narrow export.
- **iOS: local-only and expiring.** Write with `UIPasteboard.general.setItems(_:options:)` and pass `.localOnly: true`, which keeps the item off other devices via Handoff/Universal Clipboard, plus a short `.expirationDate`. Do not assign to `UIPasteboard.general.string`, which sets neither option. For copy/paste that never needs to leave your own apps, use a named pasteboard (`UIPasteboard(name:create:)`), which only apps with your team ID can see and which lasts until the app quits, instead of the general one.
- **Android: flag it and clear it.** Before `setPrimaryClip`, set `ClipDescription.EXTRA_IS_SENSITIVE` (API 33+) in the clip's extras. This is a rendering hint that hides the content in the system's copy preview; it does *not* stop another app from reading the clip. So also clear the clip when it has served its purpose, with `clearPrimaryClip()` (API 28+). On devices before Android 10, background apps can read the clipboard, so a long-lived sensitive clip is exposed there.
- Cross-platform clipboard helpers take only the content, with no place to pass these options: Flutter's `Clipboard.setData(ClipboardData(text:))` and the React Native community `Clipboard.setString`. Use a platform channel or native module for sensitive values. OWASP: MASTG-TEST-0073, MASTG-TEST-0276, MASTG-TEST-0277, MASTG-TEST-0278, MASTG-TEST-0279, MASTG-TEST-0280, OWASP Cornucopia NS3.

### 4.14 Inter-app surface beyond links: IPC components, overlays, extensions

4.6 covers inbound links and component export. These are the other paths another app on the device can use.

- **Overlays (tapjacking).** On screens where a tap confirms something (payment, permission grant, login, destructive action), set `android:filterTouchesWhenObscured="true"` (or `setFilterTouchesWhenObscured(true)`). This drops touches that arrive while another window covers the view. From API 31, also call `window.setHideOverlayWindows(true)`, which requires the `HIDE_OVERLAY_WINDOWS` permission. Android 12+ blocks touches through fully occluding untrusted overlays by default, but not partial occlusion. For that, reject events carrying `MotionEvent.FLAG_WINDOW_IS_PARTIALLY_OBSCURED` (API 29+) on the most sensitive controls.
- **Task hijacking (StrandHogg).** A malicious app can set its `taskAffinity` to your package name and slide its activity into your task. Give sensitive activities `android:taskAffinity=""`, don't set `allowTaskReparenting="true"`, and review every `singleTask`/`singleInstance` activity. Google's guidance is that configuration only partly mitigates the first variant, and the full fix is the OS patch in Android 11 (API 30) and later. So a `minSdk` below 30 is an accepted residual risk that the threat model must name, not something a manifest line closes.
- **Implicit intents and broadcasts carry no secrets.** Any app can declare a matching filter and receive an implicit intent. Tokens, PII, mutable `PendingIntent`s and `Binder`s travel only in explicit intents (`setPackage`/`setComponent`). Broadcasts carrying anything sensitive are sent with a receiver permission, `sendBroadcast(intent, permission)`, where the permission is custom and `android:protectionLevel="signature"`, or restricted with `setPackage`. A custom permission is registered when its defining app is installed, so define it in the app that installs first, or in every app that uses it. Receivers registered at runtime state `RECEIVER_NOT_EXPORTED` unless other apps must reach them.
- **What comes back is input.** Activity results, picker and share-sheet URIs, and data from `ContentResolver` are attacker-choosable. A `content://` or `file://` URI returned by a hostile "gallery" can point into your own private files. Open it, then canonicalize and check the resulting file descriptor before use, and never copy it to a path built from a provider-supplied display name (path traversal).
- **ContentProviders and FileProviders.** A provider is `android:exported="false"` unless another app must query it. That is the default only for `targetSdkVersion` 17+, so write it anyway. If a provider is exported, give it `readPermission`/`writePermission` at signature level. Build queries with `?` placeholders and `selectionArgs`, never by concatenating `selection`, `sortOrder` or projection strings. `SQLiteQueryBuilder` with `setStrict(true)`, `setStrictColumns(true)` and a projection map rejects unknown columns. Don't let several providers with different permissions share one database file: injection in one reads the others' tables. For `FileProvider`, no `<root-path>`, no `path="."` or `path="/"`, and no `<external-path>` for anything sensitive. Share one narrow directory and grant `FLAG_GRANT_READ_URI_PERMISSION` for the single URI. **Runtime test:** from outside the app, run `adb shell content query --uri content://<authority>/<path>` against each exported authority, including a `--where` value containing a quote. The shell user's permissions are not a third-party app's, so a denial here is not proof. OWASP: MASTG-TEST-0007, MASTG-TEST-0035, MASTG-TEST-0340, MASTG-TEST-0355, MASTG-TEST-0356, MASTG-TEST-0357, MASTG-TEST-0374, MASTG-TEST-0375, MASVS-PLATFORM-3, OWASP Cornucopia AA5, PC5, PC6, PC7, PC8.

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
- [ ] **HIGH** (4.3) Release trust config accepts only system CAs, and ATS carries no per-domain weakening without a written justification: no `src="user"` outside `<debug-overrides>`, no `targetSdkVersion` at 23 or below, no `NSExceptionAllowsInsecureHTTPLoads`/`NSExceptionRequiresForwardSecrecy`=NO/`NSExceptionMinimumTLSVersion` below TLSv1.2. Probe (a `src="user"` hit inside `<debug-overrides>` is acceptable only if the release build is non-debuggable; an `NSExceptionMinimumTLSVersion` of `TLSv1.3` is a tightening): `grep -rnE 'src="user"|cleartextTrafficPermitted="true"|NSAllowsArbitraryLoads|NSException(AllowsInsecureHTTPLoads|MinimumTLSVersion|RequiresForwardSecrecy)|targetSdk(Version)? *=? *\(? *(1?[0-9]|2[0-3]) *\)? *$' --include='*.xml' --include='*.plist' --include='*.gradle' --include='*.kts' .`
- [ ] **HIGH** (4.5) The server acts on `appIntegrity.appRecognitionVerdict` (`PLAY_RECOGNIZED`, expected `packageName` + `certificateSha256Digest`) after checking `requestDetails`; App Attest validation checks RP ID hash, counter and `aaguid`. Probe (lists server files that read the device verdict and never the app verdict): `grep -rlE 'deviceRecognitionVerdict' . | while IFS= read -r f; do grep -qE 'appRecognitionVerdict' "$f" || echo "$f: device verdict read, app verdict never checked"; done`
- [ ] **HIGH** (4.7) WebView settings: Safe Browsing not disabled; file-URL cross-origin flags off; `setAllowFileAccess(false)` explicit where targetSdk ≤ 29; `loadFileURL` read access scoped to the file or its own directory; web-contents debugging and `isInspectable` gated on a debug build; no `UIWebView` in app or SDK code. Probe: `grep -rnE '(setAllow(Universal|File)AccessFromFileURLs\(|allow(Universal|File)AccessFromFileURLs *= *)true|(setSafeBrowsingEnabled\(|safeBrowsingEnabled *= *)false|WebView\.EnableSafeBrowsing|setWebContentsDebuggingEnabled\(true\)|isInspectable *= *true|UIWebView|allowingReadAccessTo: *(URL\(fileURLWithPath: *NSHomeDirectory|FileManager\.default\.urls|[A-Za-z.]*(documentDirectory|documentsDirectory|homeDirectory))' --include='*.kt' --include='*.java' --include='*.xml' --include='*.swift' --include='*.m' --include='*.h' .`
- [ ] **HIGH** (4.9) Release is not debuggable, checked on the artifact: `apkanalyzer manifest debuggable <release>.apk` prints `false`, and `codesign -d --entitlements - --xml Payload/<App>.app | grep -c 'get-task-allow</key><true/>'` prints `0` for the exported IPA. Source probe: `grep -rnE 'android:debuggable="true"|isDebuggable *= *true|debuggable +true|get-task-allow' --include='*.xml' --include='*.gradle' --include='*.kts' --include='*.entitlements' --include='*.plist' --include='*.pbxproj' .`
- [ ] **HIGH** (4.11) Sensitive non-secret data stays in app-private storage with no world-readable modes; iOS sensitive files carry `complete` protection; App Group containers and shared keychain groups hold only what every member needs, with `kSecAttrAccessGroup` set explicitly. Probe (App Group and access-group hits are review items, not findings on their own): `grep -rnE 'MODE_WORLD_(READABLE|WRITEABLE)|getExternalStoragePublicDirectory|getExternalStorageDirectory|getExternal(Files|Cache)Dirs?\(|MANAGE_EXTERNAL_STORAGE|requestLegacyExternalStorage="true"|FileProtectionType\.none|noFileProtection|NSFileProtectionNone|forSecurityApplicationGroupIdentifier|UserDefaults\(suiteName|kSecAttrAccessGroup' --include='*.kt' --include='*.java' --include='*.xml' --include='*.swift' --include='*.m' --include='*.plist' --include='*.entitlements' .`
- [ ] **HIGH** (4.12) No entitlement, role, lockout counter or unlock flag is trusted from prefs/`UserDefaults`/files without a MAC or server signature; locally read and downloaded data is schema-validated on load. Probe (key-name heuristic, so it misses renamed keys; read each hit): `grep -rniE '(getBoolean|getInt|getLong|getString|bool\(forKey:|integer\(forKey:|string\(forKey:|object\(forKey:) *\(? *"[a-z_]*(premium|admin|role|entitle|unlock|licen|attempt|lockout|pro_?user|paid|subscri)' --include='*.kt' --include='*.java' --include='*.swift' --include='*.m' --include='*.dart' --include='*.ts' --include='*.tsx' .`
- [ ] **MEDIUM** (4.13) Secret fields block copy; iOS writes to the general pasteboard use `setItems(_:options:)` with `.localOnly` and `.expirationDate`; Android sensitive clips set `EXTRA_IS_SENSITIVE` and are cleared after use. Probe (the second half lists Android files that call `setPrimaryClip` and never set the flag): `grep -rnE '(UIPasteboard\.general|\[UIPasteboard generalPasteboard\])\.(string|strings|url|urls|image|images|color|colors|items) *=|Clipboard\.set(Data|String)\(' --include='*.swift' --include='*.m' --include='*.dart' --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' . ; grep -rlE 'setPrimaryClip' --include='*.kt' --include='*.java' . | while IFS= read -r f; do grep -qE 'EXTRA_IS_SENSITIVE|extra\.IS_SENSITIVE' "$f" || echo "$f: setPrimaryClip without IS_SENSITIVE"; done`
- [ ] **MEDIUM** (4.14) Sensitive confirmation screens filter obscured touches (`filterTouchesWhenObscured`, `setHideOverlayWindows` on API 31+); no `allowTaskReparenting`, sensitive activities use `taskAffinity=""`, each `singleTask`/`singleInstance` reviewed, and a `minSdk` below 30 is recorded as residual StrandHogg risk. Probe (prints a line if no overlay defence exists anywhere): `grep -rnE 'allowTaskReparenting="true"|taskAffinity="[^"]+"|launchMode="single(Task|Instance)"' --include='*.xml' . ; grep -rqE 'filterTouchesWhenObscured|setFilterTouchesWhenObscured|setHideOverlayWindows|FLAG_WINDOW_IS_(PARTIALLY_)?OBSCURED' --include='*.xml' --include='*.kt' --include='*.java' . || echo 'no overlay defence anywhere in the app'`
- [ ] **HIGH** (4.14) No sensitive extras in implicit intents; sensitive broadcasts carry a signature-level receiver permission or `setPackage`; runtime receivers are `RECEIVER_NOT_EXPORTED` unless other apps must reach them; returned URIs and results are validated. Probe: `grep -rniE 'send(Ordered)?Broadcast\([^,)]*\)|sendStickyBroadcast|putExtra\( *"[a-z_]*(token|password|passwd|secret|session|otp|pin)|RECEIVER_EXPORTED' --include='*.kt' --include='*.java' .`
- [ ] **HIGH** (4.14) Providers unexported or signature-permission protected; selection built with `?` + `selectionArgs`, never concatenation; FileProvider paths narrow (no `<root-path>`, broad `path`, or sensitive `<external-path>`), grants per URI; each exported authority queried with `adb shell content query` from outside the app. Probe: `grep -rnE '<(root|external)-path|path="(\.|/)?"|(rawQuery|execSQL|appendWhere|query)\([^;]*" *\+ *[A-Za-z_]|(rawQuery|execSQL|appendWhere)\("[^"]*\$' --include='*.xml' --include='*.kt' --include='*.java' .`
- [ ] Findings mapped to MASVS v2.1 groups; every group either has findings or an explicit "examined, clean."
