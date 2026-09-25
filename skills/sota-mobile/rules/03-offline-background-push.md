# 03 — Offline-First, Background Work & Push

Mobile networks fail constantly — elevators, subways, captive portals, congested stadium cells — and the OS suspends or kills your process whenever it likes. Apps that treat connectivity and foreground execution as defaults exhibit the classic failure modes: infinite spinners, lost user input, duplicate writes, and "works until you background it." This file covers the three disciplines that prevent them.

## Offline-first

### 3.1 Declare the offline posture; if offline-first, the local DB is the source of truth

Two valid postures exist:

- **Online-only with designed failure UX** — acceptable when stale data is dangerous (live trading, dispatch). Every screen still needs a designed offline state: a clear banner and disabled actions, not a spinner that never resolves.
- **Offline-first** — the default for content, messaging, productivity, and field-work apps.

For offline-first, one structural rule generates everything else: **the UI reads only from the local database, and the network writes into the database.**

- DB options: Room/SQLDelight (Android/KMP), GRDB/SwiftData/Core Data (iOS), SQLite/WatermelonDB/op-sqlite (RN), Drift (Flutter).
- Screens observe the DB reactively (Room `Flow`, GRDB `ValueObservation`, Drift watches). The UI never renders a network response directly.
- This kills the cache-coherence problem dead: one copy of truth on device, and every screen observing it updates together. No "list shows the old title after editing on the detail screen."

```kotlin
// BAD: screen state = network response; other screens show stale copies;
// offline = spinner forever
class OrdersVM(private val api: OrdersApi) : ViewModel() {
    suspend fun load() { _state.value = Loaded(api.getOrders()) }
}

// GOOD: DB is truth; network refreshes DB; all observers update together
class OrdersRepository(private val api: OrdersApi, private val dao: OrdersDao) {
    fun orders(): Flow<List<Order>> =
        dao.observeOrders().map { it.map(OrderEntity::toDomain) }   // UI reads this

    suspend fun refresh(): RefreshResult = try {
        val page = api.getOrders(since = dao.syncCursor())
        dao.transaction {
            dao.upsertAll(page.orders.map(::toEntity))
            dao.saveSyncCursor(page.nextCursor)
        }
        RefreshResult.Ok
    } catch (e: IOException) { RefreshResult.Offline }              // data still renders
}
```

```swift
// GOOD (iOS/GRDB): observation drives the screen; refresh is a side concern
func observeOrders() -> AsyncValueObservation<[Order]> {
    ValueObservation.tracking { db in try Order.fetchAll(db) }.values(in: dbQueue)
}
```

### 3.2 Queue mutations in a persistent outbox; make every mutation idempotent

Writes made offline — or on links that die mid-request, which is the same thing — go into an **outbox table**, not fire-and-forget coroutines:

- Each queued mutation carries a **client-generated idempotency key** (UUIDv4/v7), sent as a header or field; the server deduplicates on it. Without this, retries create duplicate orders, posts, and payments. Any retrying write path without idempotency keys is a HIGH audit finding.
- The queue drains via the platform scheduler (3.6/3.7) with exponential backoff and jitter, preserving **per-aggregate ordering** (two edits to the same record must not reorder; edits to different records may parallelize).
- Outbox rows survive process death (they're DB rows in the same transaction as the optimistic local write — atomicity matters: local change and its queued upload commit together or not at all).
- **Poison-message policy:** after N terminal failures (4xx that isn't auth/409), stop retrying, surface to the user, and report to telemetry. An outbox that retries a permanently rejected mutation forever burns battery and hides data loss.

```sql
CREATE TABLE outbox (
  id TEXT PRIMARY KEY,            -- idempotency key, sent to server
  aggregate_id TEXT NOT NULL,     -- ordering scope
  op TEXT NOT NULL,               -- 'order.cancel', payload JSON below
  payload TEXT NOT NULL,
  base_version INTEGER,           -- for conflict detection (3.4)
  attempts INTEGER DEFAULT 0,
  created_at INTEGER NOT NULL
);
```

### 3.3 Optimistic UI with visible pending state and visible rollback

- Apply the mutation locally immediately — write to the DB with `pending` status in the same transaction as the outbox row — and let the observing UI update instantly.
- Render pending state subtly once it's older than a few seconds (dimmed row, clock glyph). Users on bad networks deserve to know what hasn't landed yet.
- On terminal failure: roll back the local change **and tell the user** ("Couldn't post your comment — tap to retry"). Silently reverting an edit is data loss from the user's perspective and erodes trust in every future optimistic update.

### 3.4 Choose a conflict-resolution strategy per entity, explicitly

"Last write wins" is a decision, not a default you fall into. The escalation ladder, cheapest first:

1. **LWW with server timestamps** — fine for single-writer data (the user's own settings from their own devices, mostly).
2. **Field-level merge** — server merges non-overlapping field updates, rejects overlapping ones back to the client.
3. **Version preconditions** — the client sends `base_version` it edited against; server returns 409 + current state on mismatch; client merges or asks the user. The right default for shared business records.
4. **CRDTs / dedicated sync engines** — for genuinely collaborative data (shared documents, multi-user checklists). Prefer an existing engine or CRDT library over hand-rolling; hand-rolled sync protocols are multi-year bug farms with corruption-shaped failure modes.

Write the chosen strategy per entity in the repo (a table in the sync design doc). Auditors: offline-writable entity with no stated strategy = MEDIUM; concurrently-edited data under blind LWW = HIGH (it silently destroys user input).

### 3.5 Sync protocol hygiene

- **Delta sync** with a server-issued cursor (`since` token), never repeated full downloads. The server must handle "cursor too old/invalid" with an explicit full-resync signal, and the client must implement it — the untested resync path is where year-old installs break.
- Tombstones: deletions must sync as explicit records, or deleted items resurrect from stale caches.
- Detect connectivity by **attempting the request**, not by trusting reachability APIs — captive portals report "connected" while blackholing traffic. Reachability/`ConnectivityManager` signals are for *deferring* retries, never for *gating* attempts.
- Sync work is: off the main thread, batched, compressed, cancellable, and resumable mid-batch (commit progress per page, not at the end).
- Instrument it: sync success rate, drain latency, queue depth, and conflict rate are product health metrics, not nice-to-haves.

## Background work

### 3.6 iOS: background execution is a budgeted privilege, not a capability

- Use `BGTaskScheduler`: `BGAppRefreshTask` for short periodic refresh, `BGProcessingTask` for longer maintenance (with `requiresNetworkConnectivity`/`requiresExternalPower` set honestly). The OS schedules based on user habits and battery — treat scheduling as a **hint**. Anything that *must* happen also happens on next foreground.
- Every task registers an **expiration handler**, checkpoints progress, and calls `setTaskCompleted(success:)`. Tasks that run to the buzzer get throttled in future scheduling.
- Large uploads/downloads use **background `URLSession`** — transfers continue after process death and relaunch the app on completion. Keeping a process alive to babysit a transfer is the wrong tool and will be killed.
- Dedicated background modes (location, audio, VoIP/PushKit) only when the product genuinely *is* that feature — App Review rejects mode abuse, and PushKit VoIP pushes that don't present calls get the app killed.
- **Background work runs while the phone is locked, so it must not fetch or render sensitive data then.** Files with `complete` protection (rules/04 §4.11) are unreadable while `UIApplication.shared.isProtectedDataAvailable` is `false`. Check it at the start of a task, close protected files on `applicationProtectedDataWillBecomeUnavailable`, and defer sensitive work to the next unlock rather than downgrading the file's protection class so a refresh can read it. On Android, a Keystore key built with `setUnlockedDeviceRequired(true)` (API 28+) refuses to decrypt while `KeyguardManager.isDeviceLocked()` is true, which is the same boundary. A widget, notification or snapshot produced by that background run is readable on the lock screen. OWASP: MASTG-TEST-0315, OWASP Mobile Application Security cheat sheet.
- **Silent pushes (`content-available: 1`) are throttled and best-effort:** budgeted to roughly a few per hour, dropped under battery pressure, and never delivered to force-quit apps. An architecture that *requires* silent push delivery is broken by design. Use them only as a "sync sooner" accelerant layered over pull-based sync that works without them.

```swift
BGTaskScheduler.shared.register(forTaskWithIdentifier: "com.app.outbox", using: nil) { task in
    let work = Task { await syncEngine.drainOutbox(checkpointing: true) }
    task.expirationHandler = { work.cancel() }          // mandatory
    Task { task.setTaskCompleted(success: await work.value) }
}
```

### 3.7 Android: WorkManager for deferrable work; respect Doze, don't fight it

- **WorkManager** is the default for all deferrable-guaranteed work (sync, outbox drain, uploads): constraints (`NETWORK_CONNECTED`, charging), exponential backoff, **unique work names** (`enqueueUniqueWork` — without them, every trigger enqueues a duplicate chain), and persistence across reboots.

```kotlin
val drain = OneTimeWorkRequestBuilder<OutboxWorker>()
    .setConstraints(Constraints(requiredNetworkType = NetworkType.CONNECTED))
    .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30, TimeUnit.SECONDS)
    .build()
WorkManager.getInstance(ctx)
    .enqueueUniqueWork("outbox-drain", ExistingWorkPolicy.KEEP, drain)
```

- **Doze and App Standby Buckets** will batch and defer your work — that's the contract. Do not fight them with `setExactAndAllowWhileIdle` alarms or wakelocks for routine sync. Exact alarms are permission-gated and policy-reviewed; they're for user-facing scheduled moments (an actual alarm, a medication reminder), nothing else.
- **Foreground services** only for user-initiated, user-visible ongoing work (playback, navigation, active workout) with the correct `foregroundServiceType` declared — Play policy enforces declared types and rejects misuse. "Foreground service to keep sync alive" is both a policy violation and a battery-review magnet.
- `BroadcastReceiver.onReceive` does nothing but delegate to WorkManager — slow receivers ANR (rules/05).
- FCM **high-priority** messages punch through Doze, but repeated delivery without a user-visible result causes the platform to deprioritize your app's messages. Reserve high priority for genuinely time-critical user-facing events (incoming call, ride arriving); everything else is normal priority.

### 3.8 Every background job is idempotent, checkpointed, and time-indifferent

The universal contract both platforms converge on: background time can end mid-instruction. Therefore every job is written to be resumable from a checkpoint, idempotent on re-run (3.2 keys), and indifferent to running now versus in three hours. If the product genuinely demands real-time guarantees, that is a foreground feature or a server-side feature — not a background hack, because there is no reliable background on modern mobile OSes.

## Push notifications

### 3.9 Token lifecycle is server-side state with hygiene

- Fetch the APNs/FCM token on every launch and on the rotation callbacks (`didRegisterForRemoteNotificationsWithDeviceToken`, `onNewToken`) — tokens rotate on reinstall, restore-from-backup, and OS updates. Upload on change, keyed to **device + account**, with app version and environment (sandbox/prod APNs mixups are a classic "push works in dev only" bug).
- Process feedback: delete tokens on APNs 410/`Unregistered` and FCM `UNREGISTERED` responses. A token table that only grows means paying to push to ghosts and corrupting delivery metrics.
- **On logout, disassociate the token from the account server-side immediately.** Pushing user A's message previews to a device now logged in as user B is a CRITICAL privacy finding — and it happens by default if logout only clears local state.
- Server side: use token-based APNs auth (p8 key), batch sends, and respect collapse IDs to replace stale notifications instead of stacking them.

### 3.10 Push is a doorbell, not a delivery truck

Push delivery is at-most-once, unordered, size-limited (~4 KB), and transits third-party infrastructure. Therefore:

- The payload carries **identifiers and a collapse key, not data of record**. The app fetches truth from the API/DB on tap or in the background handler. State synced via push payloads diverges the first time a push is dropped — and pushes are dropped daily.
- Minimize sensitive content in payloads (it appears on lock screens and in transit metadata). When the product needs rich-but-private notifications, use the iOS **Notification Service Extension** / FCM data-message handler to fetch or decrypt content on-device before display.
- Never put auth tokens or signed URLs with broad scope in payloads (rules/04 §4.4).
- **The same applies to notifications the app builds itself.** A locally posted "Transfer of 2,400 to J. Smith" is on the lock screen for anyone holding the phone. On Android, sensitive notifications use `VISIBILITY_PRIVATE` with a redacted `setPublicVersion(...)` ("New transaction"), or `VISIBILITY_SECRET`. Under `VISIBILITY_PRIVATE` the icon and content *title* still show on a secure lock screen, so the title carries no sensitive data either. Never set `VISIBILITY_PUBLIC` on a notification or channel that carries account data. On iOS, the user's Show Previews setting decides whether the body appears when locked. Keep sensitive values out of the title and subtitle, supply a `hiddenPreviewsBodyPlaceholder`, and don't use `.hiddenPreviewsShowTitle`/`.hiddenPreviewsShowSubtitle` on categories whose title is sensitive. In either case the user can override your choice, so text that must not be seen on a locked device must not be in the notification at all. OWASP: MASTG-TEST-0315, OWASP Mobile Application Security cheat sheet.

### 3.11 Rich, actionable, and well-channeled notifications

- iOS: Notification Service Extension for attachments/decryption — it gets ~30 seconds and a tight memory cap, so it must degrade to plain text gracefully, never crash (a crashing NSE silently drops your notification content). Categories + actions for inline reply/approve; communication-style notifications and interruption levels used honestly (`time-sensitive` for genuinely time-sensitive things, or users revoke it).
- Android: **channels are mandatory UX architecture** — one channel per user-meaningful category ("Order updates", "Promotions"), with honest default importance, so users can mute marketing without muting the product. One channel for everything earns app-level mutes and uninstalls.
- Every notification deep-links to the **exact content** (route-as-data, rules/02 §2.7) through the validated deep-link pipeline (rules/04 §4.6) — landing on the home screen after tapping "Your order shipped" is a quality bug users notice.
- Localize and collapse: use collapse IDs / `setGroup` so ten events become one stacked notification, not ten rows.

### 3.12 Ask for notification permission in context, never at first launch

Android 13+ requires the runtime `POST_NOTIFICATIONS` permission; iOS always has. Both give you effectively **one** clean shot at the system prompt:

- Sequence: the user takes an action whose value depends on notifications ("notify me when it ships") → show your own pre-prompt explaining the concrete value → only then fire the system prompt. Acceptance rates double or better versus prompt-at-launch.
- On denial: degrade gracefully, surface a settings deep link *from the relevant feature*, and don't nag on a timer.
- iOS **provisional authorization** (quiet delivery to Notification Center without any prompt) is a legitimate warm-up: deliver value first, ask for full alerts later.
- A system permission prompt on first launch, before the user has seen any value, is an automatic MEDIUM finding: it maximizes the denial rate and permanently burns the only shot.

## Audit checklist

- [ ] Offline posture documented; online-only screens have designed failure states (no infinite spinners).
- [ ] Offline-first: UI reads exclusively from the local DB via reactive observation; network writes into the DB; no screen renders a network response directly.
- [ ] Mutations persisted in an outbox, committed atomically with the optimistic local write; client idempotency keys sent and deduplicated server-side; per-aggregate ordering preserved; poison-message policy exists.
- [ ] Optimistic updates show pending state and roll back visibly with a retry affordance on terminal failure.
- [ ] Conflict strategy written down per offline-writable entity; concurrent-edit data is not blind LWW; 409/merge path implemented and tested.
- [ ] Delta sync with cursor + tombstones + tested full-resync path; connectivity probed by attempting requests, not reachability flags; sync metrics instrumented.
- [ ] iOS: BGTaskScheduler with expiration handlers and completion calls; background URLSession for large transfers; background modes match the product; nothing *depends* on silent push delivery.
- [ ] Android: WorkManager with constraints/backoff/unique names; no exact alarms or wakelocks for routine sync; foreground services only user-visible with declared types; receivers delegate immediately; FCM high priority reserved for time-critical user-facing events.
- [ ] Every background job idempotent, checkpointed, and correct whether it runs now or hours late.
- [ ] Push tokens uploaded on rotation, keyed to device+account, deleted on feedback, disassociated on logout (verified — this is the privacy-critical one).
- [ ] Push payloads carry IDs/collapse keys, not data of record or secrets; rich content fetched/decrypted on-device; NSE degrades gracefully.
- [ ] **MEDIUM** (3.10, 3.6) Locally built notifications with sensitive content use `VISIBILITY_PRIVATE` + redacted `setPublicVersion` or `VISIBILITY_SECRET`, with nothing sensitive in the title; iOS categories with sensitive titles don't opt into `hiddenPreviewsShowTitle`/`Subtitle`; background refresh checks protected-data availability and defers sensitive work while locked. Probe (the second half lists files that schedule background tasks and never check protected-data availability): `grep -rnE 'VISIBILITY_PUBLIC|hiddenPreviewsShow(Title|Subtitle)' --include='*.kt' --include='*.java' --include='*.swift' --include='*.m' . ; grep -rlE 'BGAppRefreshTask|BGProcessingTask|BGTaskScheduler' --include='*.swift' --include='*.m' . | while IFS= read -r f; do grep -qE 'isProtectedDataAvailable|protectedDataWillBecomeUnavailable|ProtectedDataWillBecomeUnavailable' "$f" || echo "$f: background task never checks protected-data availability"; done`
- [ ] Android channels map to user-meaningful categories; notifications deep-link to exact content via the validated route pipeline; collapse/grouping used.
- [ ] Notification permission requested in context with a pre-prompt; provisional auth considered on iOS; denial path designed; never prompted at first launch.
