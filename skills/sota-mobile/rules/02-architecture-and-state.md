# 02 — Architecture & State

Mobile apps die from state bugs: stale screens, double-fired effects, races on rotation and backgrounding, and untestable god-objects. The cure is the same on every stack — unidirectional data flow, explicit state machines, injected dependencies, and enforced module boundaries. None of this is optional ceremony; each rule below pays for itself in a class of production bug it makes impossible.

## 1. Rules

### 2.1 Unidirectional data flow, exactly one pattern per codebase

State flows down, events flow up, and every piece of state has exactly one writer. Pick the platform-idiomatic flavor and apply it uniformly:

- **iOS/SwiftUI:** `@Observable` view models (MVVM) or TCA-style reducers. One `@MainActor` observable object per screen owning that screen's state.
- **Android/Compose:** ViewModel exposing a single `StateFlow<UiState>` (MVVM) or an MVI reducer. Collect with `collectAsStateWithLifecycle` — plain `collectAsState` keeps collecting while backgrounded.
- **React Native:** server state in TanStack Query (cache, refetch, invalidation), client state in Zustand/Redux Toolkit; components render state and dispatch events. Don't reimplement a server cache in Redux by hand.
- **Flutter:** BLoC or Riverpod; widgets are pure functions of state.

Two patterns in one codebase is worse than either alone: every screen transition crosses a paradigm boundary, and new code copies whichever pattern the author saw last. Auditors: mixed paradigms (half MVVM, half massive-view-controller; Redux and ad-hoc context state interleaved) is a MEDIUM finding with a migration-plan remediation, not a rewrite demand.

```kotlin
// BAD: three writers, no owner, untestable, races on config change
@Composable
fun CartScreen(repo: CartRepo) {
    var items by remember { mutableStateOf(listOf<Item>()) }
    LaunchedEffect(Unit) { items = repo.load() }              // writer 1
    Button(onClick = {
        repo.items.add(item)                                   // writer 2
        GlobalScope.launch { repo.sync() }                     // leaks past screen
    }) { Text("Add") }
}

// GOOD: single owner; events in, immutable state out
class CartViewModel(private val repo: CartRepo) : ViewModel() {
    private val _state = MutableStateFlow<CartState>(CartState.Loading)
    val state: StateFlow<CartState> = _state.asStateFlow()

    fun onEvent(e: CartEvent) = when (e) {
        is CartEvent.Add -> viewModelScope.launch {
            _state.update { it.withPendingItem(e.item) }
            repo.add(e.item)   // repo persists + queues sync (rules/03)
        }
        // ...
    }
}

@Composable
fun CartScreen(vm: CartViewModel) {
    val state by vm.state.collectAsStateWithLifecycle()
    CartContent(state = state, onEvent = vm::onEvent)  // stateless, previewable
}
```

```swift
// GOOD: same shape on iOS
@MainActor @Observable
final class CartViewModel {
    private(set) var state: CartState = .loading
    private let repo: CartRepository
    init(repo: CartRepository) { self.repo = repo }

    func send(_ event: CartEvent) { /* reduce + structured Task */ }
}
```

### 2.2 Model UI state as a closed type, not a pile of booleans

`isLoading + error + data` triplets allow 8 combinations, of which 5 are bugs ("loading spinner over an error banner over stale data"). Use sealed types / enums with associated data so illegal states don't compile:

```swift
// BAD
final class OrdersVM {
    var isLoading = false
    var error: Error?
    var orders: [Order] = []
    // loading == true && error != nil && !orders.isEmpty — what renders?
}

// GOOD: every case is a designed screen
enum OrdersState: Equatable {
    case loading
    case loaded(orders: [Order], refreshing: Bool, isStale: Bool)
    case empty
    case failed(message: String, retryable: Bool)
}
```

```kotlin
sealed interface OrdersState {
    data object Loading : OrdersState
    data class Loaded(val orders: List<Order>, val refreshing: Boolean, val isStale: Boolean) : OrdersState
    data object Empty : OrdersState
    data class Failed(val message: String, val retryable: Boolean) : OrdersState
}
```

Include offline/stale variants (`isStale`) — offline-first behavior ([rules/03](03-offline-background-push.md)) is unrepresentable without them, and "stale data shown while refreshing" is the single most common mobile screen state. Each sealed case doubles as a snapshot-test fixture (2.9).

### 2.3 State must survive process death and configuration change

The OS kills backgrounded apps routinely; Android additionally recreates activities on rotation, resize, and locale change. Triage every piece of state into one of three buckets:

1. **Ephemeral UI state** (scroll position, half-typed text, selected tab): `SavedStateHandle` / `rememberSaveable` (Android), `@SceneStorage` / state restoration (iOS). Losing a user's half-typed review to a phone call is a bug users *feel*.
2. **Durable data:** the local DB ([rules/03](03-offline-background-push.md)). Never "it's still in the singleton" — after process death it isn't, and the crash on unwrapping it lands in your top-5 crash signatures.
3. **In-flight work:** must be resumable or idempotent. A checkout that corrupts if the process dies mid-request is a HIGH finding; the outbox pattern ([rules/03](03-offline-background-push.md) §3.2) is the fix.

Make it testable in QA: Android — enable "Don't keep activities" and use `adb shell am kill` on the backgrounded app; iOS — Xcode's simulated termination, plus launch-into-deep-link and launch-from-notification paths (which are also cold starts with no warm state).

```kotlin
// BAD: survives rotation only by accident, dies with the process
object DraftHolder { var draft: String = "" }

// GOOD
class ComposeViewModel(private val saved: SavedStateHandle) : ViewModel() {
    var draft: String
        get() = saved["draft"] ?: ""
        set(v) { saved["draft"] = v }
}
```

### 2.4 Effects are owned by the state owner and tied to lifecycle

- Network calls, timers, and subscriptions launch from the state owner's scope — `viewModelScope`, or structured-concurrency `Task`s tied to the observable's lifetime — never from view/render code, and never on `GlobalScope` / detached tasks. Views re-render arbitrarily often; an effect in a view body fires arbitrarily often. A `GlobalScope` job outlives the screen and writes to dead state.
- **One-shot effects** (navigate, toast, haptic) are *consumed events*, not state: a `Channel`/`SharedFlow(replay=0)` on Android, an `AsyncStream` or explicit callback on iOS. Modeling "navigate to success screen" as a sticky `Bool` re-fires it on every rotation — the canonical double-navigation bug.
- Effects must be cancellable: leaving the screen cancels its in-flight loads (structured concurrency gives this for free if you don't detach).

```kotlin
// BAD: sticky event state — re-navigates on every config change
data class State(..., val navigateToSuccess: Boolean = false)

// GOOD: consumed exactly once
private val _effects = Channel<CartEffect>(Channel.BUFFERED)
val effects = _effects.receiveAsFlow()
// collector: LaunchedEffect(Unit) { vm.effects.collect { handle(it) } }
```

### 2.5 Dependency injection: constructor injection behind interfaces, one composition root

- Every view model takes its dependencies (repositories, clock, dispatchers) via constructor, typed as protocols/interfaces. No `Foo.shared` / `object` singletons reached from inside business logic — they make tests order-dependent, previews impossible, and parallel test execution flaky.
- One composition root at the edge: Hilt/Koin modules (Android), an `AppDependencies` container or swift-dependencies (iOS — the pattern matters, not the framework), a context/DI shell (RN). Product code never constructs its own infrastructure.
- **Inject the clock and the dispatchers/schedulers.** Time and threading are dependencies. Hardcoded `Date()` / `Dispatchers.IO` / `DispatchQueue.global()` is the root cause of most flaky mobile test suites.

```swift
// BAD
final class ProfileVM {
    func load() async {
        let user = try? await APIClient.shared.currentUser()   // unmockable
        self.greeting = user.map { greet($0, at: Date()) }     // untestable at midnight
    }
}

// GOOD
protocol UserFetching { func currentUser() async throws -> User }

@MainActor @Observable
final class ProfileVM {
    private let api: UserFetching
    private let now: () -> Date
    init(api: UserFetching, now: @escaping () -> Date = Date.init) {
        self.api = api; self.now = now
    }
}
```

```kotlin
// GOOD: dispatchers injected, swapped for a TestDispatcher in tests
class SyncRepo(
    private val api: Api,
    private val io: CoroutineDispatcher,   // = Dispatchers.IO in prod module
)
```

### 2.6 Modularize for build time and ownership, not aesthetics

Monolithic app modules hit a wall: every change triggers near-full rebuilds, merge conflicts concentrate, and layering is unenforceable. The structure that works:

- **Layers:** `:core:*` (network, database, design-system, analytics) ← `:feature:*` (one module per user-facing feature) ← `:app` (composition root + navigation wiring only, near-zero code).
- **Features never depend on features.** Cross-feature flows go through navigation contracts or shared core abstractions. The first feature-to-feature import is the first brick of the big ball of mud — make it a lint/CI error (Gradle dependency rules, SPM target graph, eslint-plugin-boundaries, Dart `import_lint`).
- Split api/impl where compile-time fan-out hurts: features depend on `:core:network:api` (interfaces), only `:app` sees `:core:network:impl` — changing the implementation then rebuilds one module.
- iOS: same shape with local SPM packages; keep the Xcode project a thin shell. RN/Flutter: package-per-feature with enforced import rules.
- **Thresholds:** under ~30k LOC a single module is fine — don't gold-plate. Beyond that, incremental build time and test isolation pay for the structure. Track clean and incremental build times in CI so the wall is visible before you hit it.

### 2.7 Navigation is declarative, centralized, and deep-link-addressable

- One navigation system per app: Compose Navigation with type-safe routes, SwiftUI `NavigationStack` driven by a route enum in a router/coordinator, React Navigation, GoRouter. Ad-hoc `present(_:)` / `startActivity()` calls scattered through views defeat deep linking, restoration, and testing.
- **Routes are data.** If a screen can't be expressed as a serializable route value, it can't be deep-linked, restored after process death, or opened from a push notification — and all three will be product requirements eventually.

```swift
enum Route: Hashable, Codable {
    case orders
    case order(id: String)
    case settings(SettingsSection)
}
// NavigationStack(path: $router.path) — the whole stack is a [Route], save/restore trivially
```

- Every route reachable from a notification or deep link must handle being the **first** screen: cold start, no back stack, possibly no valid session. Build the pipeline once, centrally: parse → validate (security: [rules/04](04-security.md) §4.6) → auth-gate → synthesize a sensible back stack (order detail gets an Orders parent, not an empty stack).
- Navigation logic (which route follows which event) lives in the state owner / coordinator, not in view code — it's business logic and needs tests.

### 2.8 Repository layer mediates all data access

Views and view models never touch the network client or the DB directly. One repository per domain aggregate decides: cache vs network, offline queueing ([rules/03](03-offline-background-push.md)), retry policy, and DTO → domain mapping.

- **DTOs do not leak above the repository.** Wire types change with the API; domain types change with the product. Coupling screens to wire types turns every backend rename into a 40-file diff — and old shipped binaries pin old wire assumptions ([rules/06](06-release-and-operations.md) §6.8), so the mapping layer is also where tolerance for unknown/missing fields lives.
- Repositories expose reactive reads (`Flow` / `AsyncSequence` / Query observables) backed by the DB, plus imperative commands. They are interfaces in `:core:*:api`, faked in view-model tests.

```kotlin
// BAD: VM knows about Retrofit DTOs and Room entities
class OrdersVM(private val api: OrdersApi, private val dao: OrdersDao)

// GOOD
interface OrdersRepository {
    fun orders(): Flow<List<Order>>          // observes local truth
    suspend fun refresh(): RefreshResult     // network → DB
    suspend fun cancel(id: OrderId): Result<Unit>  // queued mutation
}
```

### 2.9 Testing follows from the architecture

If 2.1–2.8 hold, testing is cheap. If testing is hard, the architecture is wrong — fix the architecture, don't write more heroic tests.

- **Unit (the bulk):** reducers/view models with fake repositories; sealed-state assertions; injected `TestDispatcher`/test clock. Milliseconds each, thousands run per commit.
- **Snapshot:** every design-system component, and key screens rendered once per sealed state case (2.2 fixtures), across dark mode, large font scale, and RTL.
- **UI/E2E:** a handful of critical flows only — login, the core loop, purchase. Expensive and flaky by nature; keep the pyramid shaped like a pyramid. Full strategy in [rules/06](06-release-and-operations.md) §6.9.

## Audit checklist

- [ ] (§1: 2.1) Single UDF pattern applied consistently; every screen's state has exactly one writer; no mixed paradigms without a written migration plan.
- [ ] (§1: 2.2) UI state modeled as sealed/closed types with stale/offline variants; no loading/error/data boolean piles.
- [ ] (§1: 2.3) State triaged for process death: saved-state handles for ephemeral UI, DB for durable data, idempotent/resumable in-flight work; QA exercises "Don't keep activities" / simulated termination / launch-from-notification.
- [ ] (§1: 2.4) No `GlobalScope`/detached effects; no network or side effects launched from view/render code; in-flight work cancelled on screen exit.
- [ ] (§1: 2.4) One-shot effects (navigation, toasts) delivered as consumed events, never sticky state.
- [ ] (§1: 2.5) Constructor injection throughout; no singleton reach-ins from business logic; clock and dispatchers injectable; one composition root.
- [ ] (§1: 2.6) Module graph: features don't import features (enforced by tooling, not convention); composition root only in `:app`; build times tracked in CI.
- [ ] (§1: 2.7) Navigation centralized, route-as-data; every push/deep-link target survives cold-start entry with synthesized back stack; navigation decisions unit-tested.
- [ ] (§1: 2.8) Repository layer present; DTOs don't leak past it; repositories exposed as fakeable interfaces with reactive reads.
- [ ] (§1: 2.9) Test pyramid intact: fast unit bulk on VMs/reducers, snapshot coverage of design system + state cases (incl. dark/RTL/font scale), ≤ ~10 E2E flows.
