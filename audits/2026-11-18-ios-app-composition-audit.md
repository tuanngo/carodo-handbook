# App composition audit — 2026-11-18

`carodo-ios` at `42e434a`. Audit only, read-only; **no code before the owner approves each finding**
(`AGENT_WORKFLOW.md`, Plan before code). The question (owner, 2026-11-17): are `Carodo/App` and
`DependencyContainer` more complex and longer than they need to be, and what do the reference apps
do that we can learn from?

This file keeps apart **Today** (what the code does, with its file), **Proposed**, and **Assumed**
(not checked).

Sources read: `App/{DependencyContainer, +Live, +Connect, +Recovery, +Maintenance, +Diagnostics,
+Feed, +LocalData, +Caches}.swift`, `App/{CarodoApp, MainTabView, AppState, DriveFlow}.swift`,
`Core/PreviewData/DependencyContainer+Samples.swift`, `CarodoTests/Rules/ArchitectureTests.swift`
(composition-root rules), `carodo-ios/docs/architecture.md` (Sensors, Map lookups),
`plans/enrichment-scheduler.md`. Reference apps in `~/code/oss/swift` (section 3).

**Status (2026-11-18):** D1–D4 approved as recommended (owner). Step 1 done as enrichment-scheduler
slice 2 (carodo-ios `16efbd7`). Step 2 done (carodo-ios `c4ed342`, see below). Step 3 done:
`DriveDiagnostics` (`d7ee4bc`), `JournalUpkeep` (`4ecd269`), `TripReconciliation` (`e240d9e`).
Step 4 (F3, F4) not started: its handoff is [`../plans/app-shell-split.md`](../plans/app-shell-split.md).

Step 3 as built: `LaunchReconciliation` is named `TripReconciliation`, since it also runs after each
saved drive and on return to the app. The launch's facts (cause, origin, waited) are the argument of
`startAtLaunch(_:)`, called by `CarodoApp.startServices` before any other caller can reach the
container, instead of three container `var`s set after `live()`. `+Recovery`, `+Maintenance` and
`+Diagnostics` are gone; the container's stored `var`s went from 21 to 5 (`feedBackend`,
`feedPublisher`, `autoMode`, `cloudSync`, `journalSeed`) plus two `lazy` services (`diagnostics`,
`driveActivity`, both reading what `connect` builds).

Step 2 as built, against F2's proposal: `DriveSessionManager.Inputs` (six readers), the battery's
network and the tracking mode's place regions are given in `init`; `CarodoApp.wireCallbacks`
moved into `+Connect` (`wireCallbacks(appState:)`, called by `connect`). Three differences, each
because the value needs `AppState`, which `live()` does not take: `autoMode` stays a `var` built in
`connect`; `DriveActivityController`'s four readers stay in `connect` (two read `AppState`, the
four are kept together); `Inputs` fields stay optional with a nil default, so tests set only what
they read (a missing reader in the container is caught by review, not the compiler).

## 1. Summary

The direction is right and stricter than every reference app: one composition root, protocols at
the boundaries with a fake beside each, sensors and lookups created only there (enforced by
`ArchitectureTests`), no singletons, no DI library, sample data impossible in Release. Keep all of
it (section 4).

What is too much is **what the container does besides composing**. It carries use-case logic and
its state, and it wires its services in a second phase through closures assigned after `init`, in
two places. `MainTabView` and `AppState` each hold several roles. App is 3,691 lines in 26 files;
the size itself is not the problem, the roles are.

| # | Finding | Severity | Confidence |
|---|---|---|---|
| F1 | The container holds use-case logic and its mutable state | Medium | Confirmed |
| F2 | Services are completed after `init` by 23 closure assignments, in two places | Medium | Confirmed |
| F3 | `MainTabView` is tab bar, navigation, floating controls and model factory at once | Low | Confirmed |
| F4 | `AppState` mixes preferences, one-shot requests and change signals | Low | Confirmed |
| I1 | One launch state the root view switches on | Idea | — |

## 2. Findings

### F1. The container holds use-case logic and its mutable state

**Today.** `DependencyContainer.swift` declares 41 stored `let`s and 21 `var`s. The extensions are
not wiring but work:

- `+Recovery` (156 lines): launch reconciliation (`reconcileAtLaunch`, `recoverUnfinishedTrips`),
  Stop and wait (`joinWait`), held pieces (`settleHeldTrips`), with `launchReconciliation`,
  `launchCause`, `launchOrigin`, `launchWaited` as container state.
- `+Maintenance` (165 lines): the enrichment pass (`enrichJourneys`, `healGaps`, `namePlaces`,
  `matchPoints`, `narrateJourneys`, `findProvincesCrossed`), milestones, new roads, with
  `isEnriching`, `narrationSkips`, `newRoadsTask`, `newRoadsRequested` as container state.
- `+Diagnostics` (140 lines): motion and driving-dynamics analysis after a drive for the tracking
  log (`logMotion`, `logDrivingDynamics`, `logRide`), and the trip report.

So the container is the composition root and also three services without a type of their own.
Each can be tested only by building a whole container (12 test files do: `AppLaunchTests`,
`DriveFlowTests`, `BackgroundFlushTests`, `LocalDataEraseTests`, …).

**Proposed.** Each becomes a `final class` in `Core/`, beside the runs it calls, its state moved
with it, its dependencies through `init`, created once in `live()` and held as a `let`:

| New type | Folder | Takes from the container |
|---|---|---|
| `LaunchReconciliation` (recovery, Stop and wait, held pieces) | `Core/Recording` | `+Recovery`, the four launch vars |
| `EnrichmentScheduler` (already planned, `plans/enrichment-scheduler.md` 2.4) | `Core/Recording` | the pass in `+Maintenance`, `isEnriching`, `narrationSkips` |
| `JournalUpkeep` (milestones, new roads, provinces) | `Core/Maintenance` | the rest of `+Maintenance`, the new-road vars |
| `DriveDiagnostics` (after-drive log lines, trip report) | `Core/Diagnostics` | `+Diagnostics` |

The container keeps only construction and the few lifecycle calls (`flushForBackground`,
`eraseLocalData`, which already go through `LocalDataWork`). Callers (`CarodoApp.launch`,
`DriveFlow`, `MainTabView`) call the owning type: `container.enrichment.run(…)`, not a wrapper
left on the container.

**Touches.** The four extensions, `DependencyContainer.swift`, `CarodoApp.swift`, `DriveFlow.swift`,
`MainTabView.swift`, `DependencyContainer+Samples.swift`, the tests above (they construct the new
type on fakes instead of a whole container where they test only it),
`docs/architecture.md` (the file-per-concern list in Sensors).

### F2. Services are completed after `init` by 23 closure assignments, in two places

**Today.** After construction, `connect(appState:)` (`+Connect`, 125 lines) assigns 23 closure or
dependency properties on 8 objects: `driveSession` 9 (`motionReadings`, `motionFollow`,
`pressureNow`, `currentCarAudio`, `power`, `vehicleClassOf`, `onActiveChange`, `onDiagnostic`,
`onUntoldChange`), `driveActivity` 4, `driveActivityActions` 3, `carConnections` 3, `battery` 2,
`trackingMode` 1, `cloudSync` 1. `CarodoApp.wireCallbacks` assigns three more
(`appState.isAlwaysGranted`, `locationPermissionManager.onStatusChange`,
`driveSession.writer?.onSettled`). `AutoModeCoordinator` is built there too, so `autoMode` is a
`var` that is nil until `connect` runs.

Why it costs: a missing assignment still compiles and reads as "no value" (`nil`, no pressure,
no car audio); a test or preview that never calls `connect` runs a session with different inputs
from the app; the order matters (`driveActivity.start()` after its four closures) and is held only
by the order of lines. The wiring lives in two files with two different reasons to be there.

**Proposed.** Split by direction.

- **Inputs** (what the session reads: motion, pressure, car audio, power, vehicle class) are known
  when the services are built. Group them in one value, `DriveSessionManager.Inputs`, passed to
  `init`; previews and tests pass `.none` explicitly. Same for `DriveActivityController` (its four
  readers). Nothing to forget, and a missing one fails to compile.
- **Outputs** (what reacts to the session: tracking mode, `AppState`, the log) stay closures, since
  iOS 18 has no `Observations` sequence, but are assigned in **one** place, one function per
  service, after `AppState` exists. `CarodoApp.wireCallbacks` moves into it.
- `AutoModeCoordinator` is built in `live()` with the settings readers taking `AppState`, so
  `autoMode` becomes a `let`.

**Assumed, not checked.** That every input is available in `live()` without `AppState` (the
vehicle readers come from `carConnections`, which exists by then). `AppState.distanceUnit` and
`isAutomaticTrackingEnabled` are outputs' concerns or are read through a closure given `AppState`;
to confirm per closure before slicing.

### F3. `MainTabView` is tab bar, navigation, floating controls and model factory at once

**Today.** 792 lines: 13 `@State` (5 view models, 4 navigation paths, garage state, drive flow),
a 253-line `body` with 7 sheets or covers and 17 `onChange`/`task`, `destination(for:)` (90 lines,
one case per `AppRoute`), and 7 model factories (`journeyDetail` 40 lines, `backupModel`,
`vehicleEditor`, `fuelEntry`, `expenseEntry`, `placeNearby`, `makeGarageModel`). The floating
stack and banners are another ~100 lines (432–530).

**Proposed.** `AppDestinations` (in `App/`): `AppRoute` → its view and the model it needs, the
factories with it (~180 lines out). The floating stack and the discarded banner as their own view
(~100 lines out). `MainTabView` keeps tabs, paths and sheets: about 500 lines, which is what these
two moves reach (`AGENT_WORKFLOW.md`, a target the steps can reach). The navigation rule stays:
cross-feature navigation is wired in `App/`.

### F4. `AppState` mixes preferences, one-shot requests and change signals

**Today.** 314 lines: 18 functions take `defaults: UserDefaults` (preferences: units, currency,
appearance, Auto Mode, last vehicle, untold drives, onboarding…); three request/handled pairs carry
events as state (`requestDriveStart`/`drivePendingStartHandled`, `requestFuelLog`/`fuelLogHandled`,
`requestLiveDrive`/`liveDriveHandled`), while `mapIntent` already shows the one-value form; and the
`…DidChange()` signals the screens reload on.

**Proposed.** `AppPreferences` (the UserDefaults-backed values and their writes) held by
`AppState`; the three pairs become one optional request value consumed once, as `mapIntent` is.
The change signals stay. Low priority: readable today, and every feature touches `AppState`.

### I1. One launch state the root view switches on

Today the launch is spread over `AppLaunch` (container nil before the first unlock),
`isStorageUnavailable`, `launchReconciliation` and `CarodoApp.launch`. OutRun's root switches on
one `initializing / needsSetup / initialized / failed` status. Worth considering only after F1
(`LaunchReconciliation` would own the state); not proposed now.

## 3. What the reference apps do

Read 2026-11-18 in `~/code/oss/swift`. Licences: Driveline MIT; OutRun and Pilgrim GPL-3.0 (ideas
only); MilkyWay, TrailMate no licence (ideas only); FreePace MIT. Nothing is copied.

| App | Composition | Take | Refuse |
|---|---|---|---|
| **Driveline** | `AppBootstrap.boot()` (one function, 150 lines) returns `AppEnvironment`: 8 `let`s, no state, no logic. Every service gets its dependencies in `init` (`DriveRecordingService`, 11 parameters). Background enrichment is three **sweep services** (`PlaceNameSweepService`, `WeatherSweepService`, `CategoryPredictionSweepService`): each an `actor` of ~60 lines with its own single-flight flag and task identifier; the root only lists them, sweeps on foreground, schedules on background | Use cases as their own small types owning their state (F1); dependencies in `init` (F2); the root as a list, not the logic | `configure()` after `init`; defaults that build real services; Combine; `@unchecked Sendable`; SwiftData |
| **OutRun** | An `OutRunCore` facade with an explicit `status` the root view switches on. The recorder is built with its services in `init`; sync **observes** the recorder (`observeRecording(of:)`) instead of the recorder calling out. Navigation: a 15-line `RoutingScope` decides sheet or full screen per route; `MainScene` 236 lines | Outputs observed by their consumer (F2); one launch status (I1); routes decided apart from the tab view (F3) | The `TFRouting` library (a dependency, and GPL) |
| **Pilgrim** | About 20 singletons (`WayStore.shared` 25 uses, `AudioSessionCoordinator.shared` 23, …) | — | Singletons: our container is the better form |
| **MilkyWay** | FactoryKit DI library, coordinators per flow | — | A DI library and coordinator layers: more than Carodo needs |
| **FreePace, TrailMate** | No container: services as `@State` in the `App`; FreePace builds a view model inside `body`, TrailMate `try!` | — | Both |

## 4. What stays

- One `DependencyContainer`, injected once through its hand-written `EnvironmentKey` (TD-53).
- `Stores`: the caller always chooses the data source; sample data never a default.
- The composition-root rules in `ArchitectureTests` (sensors, lookups, `LocalCache`). The new
  types of F1 create no sensor or lookup: they receive them, so the rules need no change.
- Fakes beside each protocol; no DI library, no singletons, no coordinators.

## 5. Order, and the enrichment scheduler

1. **Enrichment** (F1 row 2) is `plans/enrichment-scheduler.md` slice 2, being built by another
   session. Its shape is aligned in that plan's section 2.5 (added 2026-11-18), so it lands as the
   first F1 type and nothing here redoes it.
2. **F2 inputs**: `DriveSessionManager.Inputs`, `DriveActivityController` readers, `autoMode` as
   `let`; outputs in one function. After slice 2 is committed (both touch `+Connect` and
   `DependencyContainer.swift`).
3. **F1 rest**: `LaunchReconciliation`, `JournalUpkeep`, `DriveDiagnostics`, one commit each.
4. **F3**, then **F4** if still wanted.

Each step is one commit with behaviour unchanged: `task lint`, `task warnings`, `task test` pass;
no screen changes, so no screenshots; recovery after termination stays a device check (PV list).

**Acceptance.** `DependencyContainer.swift` holds no use-case `var` (the 21 `var`s drop to the
lazily built or late-published ones: `feedBackend`, `feedPublisher`, `cloudSync`, `journalSeed`,
`lifecycleLogging`, counted again after step 2); `+Recovery`, `+Maintenance`, `+Diagnostics` are
gone; no service property is assigned outside its `init` except the outputs' one function;
`MainTabView` about 500 lines; `docs/architecture.md` lists the container's files as they are.

## 6. Owner decisions (with a recommendation)

- **D1: F1 as four types in `Core/`** (table in F1). Recommend yes.
- **D2: F2 split into inputs at `init` and outputs in one place.** Recommend yes; it removes the
  "forgot a closure" failure without a new pattern.
- **D3: F3 now, F4 later.** Recommend F3 after F1; F4 only if `AppState` grows.
- **D4: wait for scheduler slice 2 before step 2.** Recommend yes: the same files.
