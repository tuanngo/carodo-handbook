# The outputs of `connect()`: observe what is state, keep what is ordered

Status: **Approved D1–D4 (owner, 2026-11-18); built on carodo-ios branch `feat/connect-observations` (d473b1d), not merged: waiting for the device check PV-35.** Slice 2 of [min-ios-26.md](min-ios-26.md):
with the floor at iOS 26, `Observations` (Swift 6.2, the `Observation` module) is available. This plan says
which of the wiring in `App/DependencyContainer+Connect.swift` becomes "the receiver follows the source"
(OutRun's `observeRecording(of:)`), and which stays a closure on purpose.

## 1. What the two reference apps do (read 2026-11-18)

**OutRun** (`~/code/oss/swift/OutRun`, iOS 18, `swift-perception`'s `Perceptions`, the back-port of `Observations`):

- **The receiver owns its subscription.** `SyncManager.observeRecording(of:)` and `WorkoutLiveActivityService(core:)`
  start a loop over the source's state themselves; nothing outside assigns a callback into them.
- **The current value first, then the changes.** `observeRecording` reads `recorder.isCollectingData` at once
  before it iterates, so nothing waits for the first emission.
- **The task is kept and cancelled** (`recordingObservationTask?.cancel()` before a new one), the loop captures
  `[weak self]` and checks `Task.isCancelled`.
- **A buffer policy chosen per stream:** `.bufferingLatest(1)` for state where only the latest matters
  (recording on/off, preferences); `.unbounded` where every status in turn matters (`core.status`,
  `recorder.status`).
- **One derived value from several sources:** the Live Activity observes `contentState(recorder, preferences)`,
  one value built from both, and sleeps 1 s after each update instead of throttling by hand.

**Driveline** (`~/code/oss/swift/Driveline`, iOS 27, SwiftData, Combine):

- **The owner calls its followers directly, in order.** `DriveRecordingService.finishDrive()` stops location,
  stops the recorder, then calls the Live Activity, Spotlight and the classifier itself: no callback, no
  observer, where order matters.
- `@Observable` services are injected once at the app root and read by the views; derived values are computed
  where they are shown, with no relay object in between.
- Not for Carodo: Combine `.sink` (Carodo's rules forbid Combine), SwiftData, `swift-perception` (a package;
  iOS 26 has `Observations` itself).

**The lesson for Carodo:** observation for **state** someone follows; a direct call for **order**; and an event
(something that happened, not a value) is neither, it stays a call.

## 2. What `Observations` does, and its three traps

`Observations { expression }` is an `AsyncSequence` of the expression's value: the current one first, then a
new one after each change. On the recording path these matter:

1. **After, not during.** A change is delivered when the observing actor next suspends, never inside the call
   that made it. Anything that must happen *before* the next line of the caller (the tracking mode before the
   recording GPS starts) cannot be an observation.
2. **Coalesced.** Several changes in one transaction arrive as one value: a car audio route that drops and comes
   back within one turn of the main actor is seen as "connected" only, and the disconnect is lost. An **event**
   cannot be an observation.
3. **Only `@Observable` state.** The name caches (`MapDataCache`) are actors, not `@Observable`: their "names
   arrived" is an event from an actor, which `Observations` does not see.

`withObservationTracking { } onChange: { Task { observe() } }`, which Carodo writes by hand in three places, has
the same timing (after, coalesced): those three convert one for one, with nothing that behaves differently.

### Checked, not assumed (2026-11-18, Swift 6.4.2, the SDK's `Observation` interface and a run on macOS 27)

| Question | Answer | What the plan does with it |
|---|---|---|
| Available at our floor? | `@available(anyAppleOS 26.0)`; `Element: Sendable`; the closure is `@Sendable @isolated(any)` and inherits the caller's actor (main) | No availability check, no `@MainActor` written; values passed out are `Sendable` (`Bool`, small structs) |
| Does a change the closure does not read wake it? | **No**: 100 changes of an unread property, 0 emissions | A follower reads only what it decides on (`session.isActive`, never the fix count): a drive's fixes cost it nothing |
| Does an equal value emit again? | **Yes**: `isActive` true → true emitted twice | Each loop compares with the last value it acted on before doing anything |
| Two changes in one turn? | **Coalesced**: false then true in one turn → one `true` | Events stay calls (section 3) |
| Does `untilFinished` end when its source is freed? | **No**: with no further change the closure never runs again, the loop waits for ever | Each follower **keeps its task and cancels it** when it stops; never relies on the source going away |
| Does cancelling end the loop and free the follower? | **Yes**: the loop ends at once, the follower is freed (`[weak self]` in the loop, `[weak source]` in the closure) | The same two weak captures in every follower; the release test (section 6) proves it |

## 2b. Cost, layers and clean code: the rules every follower keeps

- **Nothing runs while nothing changes.** A follower is one suspended task for the app's life: no timer, no
  polling, no work per fix. Today's hand-written loops start a **new `Task` per change** to re-arm; a single
  `Observations` loop allocates none per change.
- **Launch does less, not more.** A follower reads its source once (the current value, OutRun's pattern) and
  waits; B replaces today's two tracking-mode updates at launch (`CarodoApp`, the first `onChange`) with one.
- **One decision per change.** Read the smallest state, compare with the last value, act only on a
  difference: no repeated `trackingMode.update`, no second `mode` line.
- **Layers.** A follower of app state lives in the composition root (`App/`); a sensor follows the drive in
  its own type in `Core/Motion`, `Core/Diagnostics` (as today); `Core` never names `AppState` (D passes plain
  closures built by the container); no View moves the tracking mode (B).
- **One way to follow.** After this slice `withObservationTracking` is gone from `Carodo/` and every follower
  has the same shape (stored task, two weak captures, compare, act); a rule test keeps it gone.

## 3. Audit: every closure `connect()` and `wireCallbacks` assign (code at `98d9185`)

| # | Wiring | Source → receiver | Kind | Proposal |
|---|---|---|---|---|
| 1 | `driveSession.onActiveChange` → `updateTrackingMode` | session → tracking mode | **Ordered**: the mode moves before the recording GPS starts (comment in `connect()`) | **Keep** |
| 2 | `location.onStatusChange` → `recordingConditions.locationDidChange` + `updateTrackingMode` | permission → prompt gate, tracking mode | The gate's part is an answer to a prompt it asked (event); the mode's part is state | Gate's part **keeps** the closure; the mode's part moves to **B** |
| 3 | `appState.isAlwaysGranted = { location.isAlways }` | permission → AppState (read) | An input, read on demand | **D** (given at init) |
| 4 | `driveSession.onUntoldChange` → `appState.rememberUntoldDrives` | session → UserDefaults | State, but **durable**: the ids must be written before iOS suspends a background relaunch, so the "Drive saved" toast survives a kill | **Keep** (a hop could lose them) |
| 5 | `driveSession.writer?.onSettled` → diagnostics, joins, `journalDidChange` | writer → several | Event (a drive id, once) | **Keep** |
| 6–7 | `placeNames.setOnChange`, `poiNames.setOnChange` → `placeNamesDidChange` | actor caches → AppState | Event from an actor (trap 3) | **Keep** |
| 8 | `cloudSync.onRemoteChange` → journal + garage revision | iCloud → AppState | Event (a batch arrived) | **Keep** |
| 9 | `carConnections.onCarAudioChange` → `session.carAudioChanged` + log | car audio → session | **Event with edges**: a disconnect seen alone starts the auto-finish hint (trap 2) | **Keep** |
| 10 | `carConnections.onGarageChange` → `garageDidChange` | car audio → AppState | Event (first car added) | **Keep** |
| 11 | `carConnections.onEvent` → tracking log | car audio → log | Event | **Keep** |
| 12 | `battery.onPowerChange` → `session.powerChanged` | battery → session's GPS rule | Today a callback fired by notifications; the rule reads `isCharging`, Low Power, thermal | **Keep** this slice (the session's GPS path; see section 7) |
| 13 | `driveSession.onDiagnostic` → tracking log | session → log | Event | **Keep** |
| 14 | `battery.start { session.isActive }` | session → battery level marks | State, followed by a hand-written `withObservationTracking` loop | **A** |
| 15 | `barometer.follow { session.isActive }` | session → barometer on/off | State, same hand-written loop | **A** |
| 16 | `driveActivity.isAppActive`, `.distanceUnit`, `.vehicle`, `.notice` | app → Live Activity (reads) | Inputs, assigned after creation with placeholder defaults (`{ false }`, `.km`) | **D** |
| 17 | `driveActivityActions.resume/keepGoing/finish` | Lock Screen intents → session | Commands | **Keep** (they are calls by nature) |
| 18 | `AutoModeCoordinator(settings: …)` closures | settings → Auto Mode (reads) | Inputs, given at init already | Unchanged |

Beside `connect()`, three places follow state by hand, and two drive the tracking mode from outside the
composition root:

- `DriveActivityController.observe()`, `Barometer.observe()`, `BatteryMonitor.follow()`: the recursive
  `withObservationTracking` pattern (re-armed in a `Task` after each change, never cancelled).
- `MainTabView` calls `container.updateTrackingMode` on a change of the permission and of the Auto Mode switch
  (`MainTabView.swift:335–346`), and `CarodoApp` once at launch. A **view** moves the tracking mode, against
  iOS invariant 2 ("tracking lives outside SwiftUI"); a permission change moves it twice (here and #2).

## 4. Proposal

### A. The three hand-written loops become `Observations` (no behaviour change)

`DriveActivityController`, `Barometer` and `BatteryMonitor` each keep one stored `Task` iterating
`Observations { … }`, read the current value first (OutRun), capture `[weak self]` and cancel the task when they
stop. The recursion, the re-arming `Task` per change and its leak path go. Same timing as today (section 2).

### B. The tracking mode follows its inputs in one place

`DependencyContainer.followTrackingMode(appState:)`, started from `connect()`: applies the mode once at once,
then one `Observations` over `(Auto Mode switch, Always, session active)` calls `trackingMode.update` only when
that triple differs from the last one it applied (section 2b). Then:

- `MainTabView` no longer calls `updateTrackingMode` (two calls); `CarodoApp`'s launch call goes (the follower
  applies at once); `location.onStatusChange` keeps only the gate's line.
- `onActiveChange` (#1) **stays**: the follower sees the same change a hop later and repeats an update with the
  same inputs, which `TrackingModeController.apply` already ignores (it acts only on a change; a test proves
  it writes no second `mode` line).
- The erase (`DependencyContainer+LocalData`) keeps its direct calls: it must stop Auto Mode *before* erasing.

### C. Nothing else becomes an observation

The events (#5–#11, #13), the durable write (#4) and the ordered call (#1) stay closures, each with a one-line
comment naming why (ordered, event, durable), so the next reader does not "fix" it into an observation.

### D. Inputs given at creation, not assigned after (recommended, decision D2)

`DriveActivityController` takes its four inputs (#16) in a small `Inputs` value at `init`, and `AppState`
its `isAlwaysGranted` (#3), instead of mutable closure properties with placeholder defaults: no window in which
a default answers, nothing assignable twice. This needs `live()` to receive `AppState` (CarodoApp already creates
it before the container). `Core` still never names `AppState`: the container builds the closures.

### Expected result

`connect()` loses the `driveActivity.*` assignments (D) and keeps the rest with their reason; about 105 → 90
lines (D removes about 10, B about 3 and adds 1). The real gains are not the count: the tracking mode no longer depends on a view being alive, a
permission change moves it once, three hand-written observation loops and their uncancelled tasks go.

## 5. Files

`App/DependencyContainer+Connect.swift`, `+Live.swift` (D), `App/CarodoApp.swift`, `App/MainTabView.swift`,
`App/AppState.swift` (D), `Core/LiveActivity/DriveActivityController.swift`, `Core/Motion/Barometer.swift`,
`Core/Diagnostics/BatteryMonitor.swift`; tests beside each; `docs/architecture.md` (a short "Following state"
rule: state is observed by the receiver, order is a direct call, an event is a call) and `docs/tracking.md` if
it names who moves the mode.

## 6. Tests and checks

- Each follower: change the `@Observable` source, await delivery, assert the effect; cancel, change again,
  assert nothing. A helper in `CarodoTests/Support` that awaits an observed change with a deadline (no sleeps
  in tests that can be avoided).
- B: Auto Mode switched on and off, Always given and taken, a drive starting: the mode moves once each;
  `onActiveChange` plus the follower write one `mode` line, not two; with no view alive (no `MainTabView`), a
  permission change still moves the mode.
- `DependencyContainerConnectTests`: the container and the state are still released (no task keeps them).
- `task lint`, `task warnings`, `task test`; a rule test that `withObservationTracking` appears nowhere in
  `Carodo/` and `updateTrackingMode` only in the composition root.
- **Device checks still required:** Auto Mode toggled with the app on screen → standby; Always taken away in
  Settings while Carodo is in the background → mode off; a background Auto Mode drive → its Live Activity on
  return; the barometer on and off with a drive (pressure in `trip_points`).

## 7. Non-goals

- Events to `AsyncStream`: each has one listener; a stream adds a task and a lifetime for nothing.
- `battery.onPowerChange` (#12) as an observation of the battery by the session: it would put an observation
  loop on the recording path for a change that is rare; worth it only if a second listener appears.
- The name caches as `@Observable` (they are actors by design).
- Adding `swift-perception` or any package.

## 8. Risks

- **A hop of delay** for the tracking mode after the Auto Mode switch or a permission change (milliseconds, the
  next main-actor turn). Today the view's `onChange` has the same hop.
- **Tests that await an observation** can be timing-sensitive: one helper with a deadline, used everywhere.
- **D touches the composition root's order** (`live()` before `connect()`): built and tested in its own step
  inside the slice.

## 9. Owner decisions

| # | Question | Proposal |
|---|---|---|
| D1 | Scope: A + B + C | **Yes.** A and B are the gains; C writes down why the rest stays |
| D2 | D (inputs at creation) in this slice? | **Yes**, last step of the slice: it removes the "assigned after creation" lines, which was the original complaint |
| D3 | `onUntoldChange` (#4) stays a synchronous write | **Yes**: durability before a background suspension beats one closure less |
| D4 | The permission gate keeps `onStatusChange` for its prompt answers | **Yes**: an answer to a prompt is an event |

## 10. Result (2026-11-18)

Built as planned, with what the build taught:

- **`Following.start`** (`Core/Concurrency/Following.swift`) is the one shape: read now, act, then a kept task over
  `Observations` that acts only on a different value. Four users: `Barometer`, `BatteryMonitor`,
  `DriveActivityController`, `followTrackingMode`.
- **A followed value needs a `nonisolated` conformance** under the default main-actor isolation (Swift 6.4):
  `Observations` requires `Sendable`, and a main-actor `Equatable` conformance is refused
  (`#IsolatedConformances`). `TrackingModeInputs`, `Frame`, `Showing` are `nonisolated`.
- **The Live Activity's `refresh` became a pure `frame()` and `show()`**: `Observations` follows a value, so the
  reads that used to wake it (including those in `scheduleWake`: the pending auto-finish and the warning time) all
  moved into `frame()`; with no activity and none that may start it still stops before the drive's figures.
- **The battery's first value only sets the state**: a drive already recording at launch writes no `start` line,
  as before.
- **The follower starts last in `connect()`**, after Auto Mode is built, where `CarodoApp`'s launch update used to run.
- `isAlwaysGranted` is gone: `requestAutoMode(_:alwaysGranted:)`, its one caller (`MapAtlasView`) passes the
  permission it already reads.
- Two rules (`ArchitectureTests`): no `withObservationTracking`; `updateTrackingMode` only in the composition root.

Checks after the last change: `task lint` passes; `task warnings` no warnings, no isolated deinits; `task test`
(iOS 27.2) 2,548 tests, 0 failures, 24 skipped. The new tests run 5 times in a row: every run that started passed
(two runs had the runner killed before connecting, the known start failure `task test` retries).

Left open: **PV-35** (device checks), then the merge into `main`.
