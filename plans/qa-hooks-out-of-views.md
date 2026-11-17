# QA hooks out of the production views

**Status:** done, merged into carodo-ios `main` as one commit `e4b20ac` (owner, 2026-11-17; from `refactor/qa-hooks`: step A `b3fc2ea`, `16eb270`, step B `c252787`). Not pushed. Follows
[`debug-build-separation.md`](debug-build-separation.md); runs beside
[`dependency-container-split.md`](dependency-container-split.md) (separate worktrees, file boundary
below).

## Why (owner, 2026-11-17)

Reading a production view means reading through its QA hooks: `if LaunchFlag.x.isOn { … }` branches
that open a sheet, pick a tab, fake a state at launch. They do nothing in Release (`LaunchFlag+Release`
answers nothing), so this is about **readability and agents**, not about Release size: a view's
body and `.task` should read as the product, and an agent making a preview or a mockup should not
have to step around QA plumbing. `#if DEBUG` is allowed only inside a small function whose one job
is to say how the build behaves; never scattered through views (owner, 2026-11-17).

## Task brief

```text
Outcome:
  No production view or view model reads a QA launch flag in its body, its state or its flow.
  Each screen's QA hooks live in one Debug-only place beside the screen, attached with one line;
  Release compiles a no-op twin. `DebugLaunchArguments` becomes Debug only.

User story:
  As the owner (and as an agent writing a preview), I open JourneyDetailView or MainTabView and read
  the product, with the QA hooks one line away when I need them.

Existing behaviour (files read, as of carodo-ios 93c3df7):
  QA flag reads per production file (`LaunchFlag.` or `launchArguments`):
    JourneyDetailView 10, ReplayView 6, MainTabView 6 (+ DebugLaunchArguments, 19 fields, read by
    MainTabView and DriveFlow), AppState 6, JourneysView 5, VehicleDetailView 4, GarageView 4,
    PassportView 3, OnboardingView 3, MapAtlasView 3, ReplayExportView 3,
    JourneyDetailElevationSection 2, FuelEntrySheet 2, FeedProfileSheet 2, and 1 each in
    DriveDiagnosticsView, PlacesView, PassportViewModel, AtlasMapView, ShareCardView,
    JourneyDetailViewModel, ExpenseEntrySheet, JoinTheFeedSheet, FeedView, RecordingExpandedPanel,
    AutoModeSheet, Core/Diagnostics/NetworkPath.
  Already Debug only: ReplayExportBench+Debug, NarrativeLabView+Debug, Core/PreviewData.
  Pattern in use: `X+Debug.swift` beside `X+Release.swift`, same interface (project.yml excludes
  `*+Release.swift` from Debug and `*+Debug.swift` from Release); `NarrativeLabEntry`,
  `GeofencyImportSection` are the small examples.

Owner decisions needed (the plan proposes, the owner approves before code):
  1. The shape. Recommendation: one `ViewModifier` per screen, `<Screen>QA+Debug.swift` holding that
     screen's hooks (reading LaunchFlag, the state it needs passed in as bindings), and
     `<Screen>QA+Release.swift` returning `content` unchanged; the view's body gains one line
     (`.modifier(JourneyDetailQA(...))`). Alternative: everything that opens a screen state moves to
     MainTabView's QA extension. The plan picks per hook and says why.
  2. A hook that needs a view's private state (a sheet's isPresented, a selected tab): widen it to
     internal for the modifier, or pass a binding in. Recommendation: a binding, never widen.
  3. AppState's 6 reads and NetworkPath's 1 (Core, not a view): in scope or left as they are?

Spec (Ready?) and mockups: no behaviour change; none.

Acceptance criteria:
  - `grep -rln "LaunchFlag\." Carodo/Features Carodo/App` lists only `*+Debug.swift` files
    (and whatever the owner keeps, named in this plan).
  - `DebugLaunchArguments` is `+Debug`; Release has no symbol named `DebugLaunchArguments` or `*QA`
    other than the no-op twins.
  - Every flag in docs/operations/setup.md#qa-launch-arguments-debug still works in Debug: spot-check
    on the simulator a flag per converted screen (screenshots in the scratchpad).
  - `task lint`, `task warnings`, `task test`, `task release-check` pass.

Non-goals:
  Renaming any `-carodo.debug…` flag; changing what a flag does; DependencyContainer's own flag
  reads (they belong to dependency-container-split.md); Swift packages or new targets (P6).

Relevant files/docs:
  carodo-ios: Configuration/LaunchFlag*.swift, Features/Developer/DebugLaunchArguments.swift,
  App/MainTabView.swift, App/DriveFlow.swift, App/AppState.swift, the views above, project.yml
  (configs, read only), AGENTS.md ("A screen state to check on the simulator"),
  docs/operations/setup.md (QA launch arguments), docs/architecture.md (Previews/PreviewData row).

Constraints:
  project.yml changes need the owner's approval (P6); none should be needed. `#if DEBUG` never in a
  view or a view model. A Release twin holds no logic: same interface, answers nothing.

Validation commands/device checks:
  task generate && task lint && task warnings && task test && task release-check
  Simulator by UDID: -carodo.sampleData YES -carodo.hasCompletedOnboarding YES plus one flag per
  converted screen. No device check needed (no tracking or background change).

Allowed scope:
  carodo-ios Features/, App/ except DependencyContainer*.swift, Configuration/, the docs above.

Do not:
  Touch App/DependencyContainer*.swift (the other session's file); give LaunchFlag raw values; put a
  sample type on a production path; commit another session's change (stage own paths only).
```

## Audit (2026-11-17, carodo-ios 93c3df7, read only)

**What the code does today** (files read: every file below, `Configuration/LaunchFlag+Release.swift`,
`Features/Developer/DebugLaunchArguments.swift`, `project.yml` exclusions, `CarodoTests/Configuration/
LaunchFlagTests.swift`, `CarodoTests/Features/Developer/DebugLaunchArgumentsTests.swift`,
`CarodoTests/App/DriveFlowTests.swift`).

The brief's counts hold (`grep -e "LaunchFlag\." -e launchArguments`, Previews and PreviewData left
out). The hooks are of two kinds, which need two shapes:

- **Open once (≈50 reads):** after the screen loads, set a sheet, a cover, a tab, a path, a filter,
  a player position. All in a `.task` or a `did…Once` function, guarded by `@State did…` flags
  (MainTabView 3, JourneysView 4, FeedView 1, FeedProfileSheet 1, AtlasMapCoordinator 1).
- **Value override (12 sites):** the screen computes a value and QA replaces it:
  `MainTabView.isCarPlayConnected` (carPlay), `JourneyDetailView.initialFlow` (journeySheet, reveal;
  runs in `init` for `@State flow`), `JourneyDetailView.debugSelectedPoint` (selectPoint, a fallback
  inside `body`), `ReplayView.usesGlass` (replaySurface), `View.debugScrollAnchor()` (scrollBottom,
  6 call sites, defined in PassportView.swift), `MapAtlasView.launchCameraRect` (mapCamera),
  `MapAtlasView.runLaunchTour` (mapTour, a ~40-line Instruments routine), `PassportView`'s
  `LaunchDestination` (openMilestones), `JourneyDetailElevationSection` (elevationSelect, inside a
  computation), `JourneyDetailViewModel.loadProvinces` (provinces), `PassportViewModel.load`
  (passportFail), `NetworkPath.start` (offline, Core).

Constraints found that shape the plan:

- Some state a hook writes has a **private type**: `JourneyDetailView.DetailSheet`/`DetailCover`,
  `PassportView.LaunchDestination`. A binding to it cannot leave the file; a closure can.
- **`private(set)` blocks an extension in another file:** `AppState.isFeedMember`,
  `DriveFlow.savedToast` (that one already has `DriveFlow.showForQA`, which stays).
- **Timing:** today each hook runs after `await model.load()` in the same task. A modifier's own
  `.task` starts beside it, not after it, so the modifier needs a ready signal. ReplayViewModel and
  GarageViewModel have `state`; DriveFlow and JourneyDetailViewModel expose none found (not checked
  in full).
- `AppState.openDebugMapIntent(defaults:)` is called from `DependencyContainer.swift:485` (the other
  session's file): its name and signature must stay.
- `DebugLaunchArguments` is read only by MainTabView (and its test, which runs in Debug).
- **Finding:** `AppState.isFeedMember` is written only by `-carodo.feedMember` and read nowhere, so
  the flag shows nothing today (its comment promises the member's Feed). Not in this plan's scope
  (non-goal: changing what a flag does); see decision 5.

## Plan (proposed, waiting for the owner's approval)

### Shapes

- **M, a modifier per screen.** `<Screen>QA+Debug.swift` beside the view: `struct <Screen>QA:
  ViewModifier` reads the flags, keeps its own `did…` state, and acts through what it is given:
  a ready value (it runs `.task(id: ready)` once true), bindings for internal-typed state, closures
  for private-typed state (the view passes `openTrim`, `{ sheet = .merge(nil) }`), the observable
  model by reference. `<Screen>QA+Release.swift`: the same `init`, `body` returns `content`. The view
  gains one `.modifier(<Screen>QA(…))` call (a few lines for JourneyDetail and MainTab).
- **S, a seam on the same type.** For a value override: a static on `<Screen>QA`
  (`ReplayQA.usesGlass`, `JourneyDetailQA.selectedPoint(points)`), `false`/`nil` in Release. The
  view keeps one named token where the value is computed; no flag name, no parsing.
- **B, a bench pair.** A whole QA routine moves to its own pair, like `ReplayExportBench`:
  `MapAtlasView.runLaunchTour` → `MapLaunchTour+Debug/+Release`.

### Per screen

| Screen (reads) | Shape | Notes |
|---|---|---|
| MainTabView (8) + DebugLaunchArguments | M + S | `MainTabQA`: applyLaunchArgumentsOnce, pushMapJourneyIfAsked, switchTabLater, pushVehicleLater, simulateStop, the launch clock and the 3 `did…` states move out (~130 lines). Inputs: appState, drive, session, garage, journeyDayModel (references), `$mapPath`, `$passportPath`, `$opensLogForCar`, `$carAction`, the `startDrive` closure, ready = the garage task's run. `isCarPlayConnected` → S. `DebugLaunchArguments.swift` → `+Debug`, no twin (only `MainTabQA+Debug` reads it) |
| AppState (6) | pair | `AppState+LaunchFlags+Debug/+Release`: `applyLaunchFlags(defaults:)`, called once from `init`, and `openDebugMapIntent(defaults:)` (same signature). `isFeedMember`: decision 5 |
| JourneyDetailView (10) | M + S | Open-once hooks (trim, replay, share card, merge, context editor, routeDisplay, openVisits) → M with closures; `initialFlow`'s two reads and `debugSelectedPoint` → S |
| ReplayView (6) | M + S | seek, rate, line, editor, autoplay → M (ready: `model.state`); `usesGlass` → S |
| JourneysView (5) | M | the 4 `did…` states move with it; `wantsDebugJourney` (read in `body` at :188) → S |
| GarageView (4), VehicleDetailView (4) | M | bindings only |
| PassportView (3) | M + S | scope → M; `LaunchDestination` → S; `debugScrollAnchor()` → its own pair `ScrollAnchorQA+Debug/+Release` (6 call sites, unchanged) |
| OnboardingView (3) | M | `applyLaunchFlags` moves whole; it calls `model.debugJump` (stays, model API) |
| MapAtlasView (3) | B + S | tour → B; camera → S; follow → M |
| ReplayExportView (3), FuelEntrySheet (2), ExpenseEntrySheet, ShareCardView, AutoModeSheet, RecordingExpandedPanel, PlacesView, DriveDiagnosticsView, FeedView, JoinTheFeedSheet, FeedProfileSheet (2) | M | small, bindings or the model |
| JourneyDetailElevationSection (2) | M + S | open → M; select fraction → S |
| AtlasMapView (1) | S | `selectLaunchPlace` is a UIKit coordinator method, not a view: the prefix comes from `AtlasMapQA.placePrefix` |
| JourneyDetailViewModel (1), PassportViewModel (1) | S | `JourneyDetailQA.provinces`, `PassportQA.failsLoad`: the model asks the seam |
| NetworkPath (1, Core) | kept | one guarded line at the start of `start()`, like a build-behaviour function; decision 3 |

Result to expect: `LaunchFlag.` in Features/ and App/ only in `*+Debug.swift`; about 20 new
`*QA+Debug/+Release` pairs (~40 small files); ~12 seam tokens left in production code, each a named
`<Screen>QA.x`; no `#if DEBUG` added. No project.yml change (the `*+Debug`/`*+Release` rules
already cover the new files).

### Slices (one commit each when proven, or one commit for all: decision 6)

1. The pattern on the two heaviest: `MainTabQA` (+ `DebugLaunchArguments+Debug`) and
   `JourneyDetailQA`; simulator spot checks; owner looks at the shape before the rest.
2. Journeys, Replay, Map, Passport, Garage.
3. The small ones, AppState, the view models; docs (AGENTS.md "A screen state to check", setup.md
   QA section: where a screen's hooks live, `docs/architecture.md` Previews/PreviewData row).

### Tests

- `DebugLaunchArgumentsTests`, `LaunchFlagTests`, `DriveFlowTests` unchanged (they run in Debug).
- New source rule? Not proposed (source rules stay lean): the acceptance grep is checked by hand
  and in the report. Decision 7 if the owner wants it guarded.
- `task release-check` gains nothing; the `*QA` twins are the only `QA` symbols in Release.

### Validation

`task generate && task lint && task warnings && task test && task release-check`; on a simulator
of my own (by UDID): `-carodo.sampleData YES -carodo.hasCompletedOnboarding YES` plus one flag per
converted screen (debugOpenTrim, debugReplayAt, debugOpenGarage, debugTabAfter, debugOpenVehicle,
debugJourneyFilterSheet, debugPassportScope, debugMapCamera, debugOnboardingScene, debugFuelEntry,
debugFeedIdentitySheet, …), screenshots in the scratchpad. No device check (no tracking change).

### Assumed, not checked

- That every screen has a ready signal the modifier can watch; where none does (DriveFlow's
  vehicles, JourneyDetailViewModel), the view passes one it already has (e.g. the garage task's
  revision), or the product task keeps one awaited call into the modifier's static: decision 4.
- That moving a hook from "after load, same task" to "when ready, own task" changes no screen
  state on the simulator (a sheet opened a frame later is not a behaviour change).

### Owner decisions

1. **Shape:** M + S + B as above (recommended), over moving everything to MainTabView (it cannot
   reach a screen's private sheets).
2. **Private state:** bindings for internal types, closures for private types; nothing widened
   (recommended).
3. **AppState in scope** (it is in App/, the acceptance grep covers it) via the pair above;
   **NetworkPath kept** as it is (recommended).
4. **Timing:** each modifier watches a ready value; where none exists, one awaited call stays in
   the product task (recommended), rather than adding production state only for QA.
5. **`-carodo.feedMember`:** remove the flag, `AppState.isFeedMember`, its doc row (recommended:
   it shows nothing), or keep it as is for when the Feed reads it.
6. **Commits:** one per slice (recommended: slice 1 is reviewed before the rest), or one.
7. **A source rule** for "no `LaunchFlag.` outside `+Debug` in Features/App": not recommended now.

## Approved, with a cleanup (owner, 2026-11-17)

Decisions 1–7 approved as recommended. Added: the QA flags exist for testing; a flag that is not
needed is deleted rather than moved, and data states come from `.carodo` files made by tests
(restored with `-carodo.debugRestoreBackup`) rather than flags that fake data.

**What "needed" turns on:** an agent has no way to tap the simulator here (no AXe or idb
installed; `docs/operations/setup.md#screenshots-as-evidence` reaches every state by launch flags).
A flag that opens a sheet is how an agent produces the screenshots AGENTS.md asks for. So the
cleanup depends on one tooling choice (decision 8).

Inventory (126 flags; references counted across carodo-ios docs, the handbook and git history:
most appear only in setup.md, written once for the screenshots of the change that added them):

- **Keep, whatever decision 8 says (~47):**
  data and environment (sampleData, sampleJournal, showcaseJournal, showcaseNow, emptyJournal,
  readFailure, restoreBackup, samplePlaces, stopPlaceAnyStop, offline, onboarding, the 7 feed mock
  flags); what the simulator cannot do (carPlay, startDrive, expandRecording, autoFinish,
  pendingDrive, pendingSheet, shortDrive, connectedToast, savedToast); measurement (mapTour, follow,
  tabAfter, pushVehicleAfter, replayExport and its 4 options, the 3 narrativeLab flags); frame-exact
  states (replayAt, onboardingScene, onboardingTime); entry points (tab, openJourney, openReplay,
  openSettings, openDeveloper, openPassport, openGarage, openVehicle).
- **Delete now (data a `.carodo` gives, or dead):** feedMember (reads nowhere), provinces (a
  synthetic `.carodo` drive across provinces; assumption: the lookup names it on the simulator),
  keepDropped and needsLook only if the sample journal holds a dropped and a pending drive (to check).
- **Delete if agents can tap (decision 8 = AXe), ~70:** every flag that opens a sheet, a page, a
  filter or a selection one tap from an entry point: the Garage's 11, autoModePage, vehiclePicker,
  the Feed's 3, openPlaceEditor, diagnosticsShowLog, passportScope, openMilestones, scrollBottom,
  selectPlace, mapCamera, mapIntent, openTrim, openShareCard, openMerge, openContextEditor,
  routeDisplay, journeySheet, reveal, openVisits, selectPoint, openElevation, elevationSelect,
  shareCard, replayLine, replayRate, replayAutoplay, replayEditor and its 3, journeyFilter,
  journeyFilterSheet, startPanel, autoModeSheet, compactBar, mapJourney, logForCar, expense, day,
  dayExpanded, passportFail, and the Settings pages but openSettings/openDeveloper (openCrashes,
  openNarrativeLab, openDriveDiagnostics, openPlaces, openBackup, openICloud, openFAQ, openAbout,
  openRecording).
- **replaySurface** is a design comparison (glass against solid, docs/specs/replay.md): deleting
  the flag leaves the glass branch of ReplayView unused, so it goes too, or the flag stays until
  the owner picks (decision 9).

Each deletion takes its case, its doc row, its hook and any `did…` state with it; the hooks that
remain move as planned above (fewer, smaller `*QA` pairs).

**Decisions 8–9 (owner, 2026-11-17):** AXe for taps on the simulator (a developer tool, not in the
app); the ~70 sheet and page flags go once AXe is proven on 2–3 states. `replaySurface` goes with
the glass branch (solid stays).

**AXe proven (2026-11-17, AXe 2.0.4, iPhone 18 Pro simulator, iOS 27.2, Debug):** Garage → Add
vehicle (sheet), Journey Detail → More → Trim (menu, then a cover), Settings → scroll → FAQ (a
pushed page). What the docs must say: `axe tap --label X --wait-timeout N --udid $SIM`; a label
used twice is tapped by its point (`axe describe-ui` gives the frame); a row below the fold needs
`axe swipe` first; a sample-data journey (`-carodo.sampleData`) offers no Edit, Trim or Merge (no
trip store), so those need `-carodo.sampleJournal N` (written through the real store).
Work happens in the worktree `carodo-ios-qa-hooks` (branch `refactor/qa-hooks`). `mapIntent` stays
until the container split lands (its call is in `DependencyContainer.swift`), then goes in a
follow-up.

## Direction changed: no hook for testing in production (owner, 2026-11-17)

"We are cheating into production code only to handle testing; that is wrong against the
architecture we started from." The per-screen `*QA` modifiers and seams are dropped: production
code (views, view models, `AppState`, services) holds no launch-flag read and no method or state
only QA calls. A screen is reached by taps (AXe), data comes from what the composition root builds
(sample stores, a restored `.carodo`), and a state the simulator cannot produce becomes a fake
chosen at the composition root, as the sensors' fakes already are.

### Step A, done (carodo-ios `refactor/qa-hooks`)

- 92 flags gone (126 → 34) with their hooks, doc rows and QA-only state; QA-only APIs with them
  (`OnboardingModel.debugJump`/`frozenTime`, `ReplayExportModel.debugShow`,
  `JourneyRevealFlow.init(presentation:)`, `AppState.isFeedMember`); Replay's glass branch and
  `RoundToolButton.usesGlass`; `-carodo.debugMapTour` became `task map-tour` (AXe gestures).
- Flags are read only by the composition root (`DependencyContainer*`, `Core/PreviewData`), plus
  the step-B list below. Docs: setup.md (what a flag may do; reaching a screen with AXe),
  AGENTS.md recipe, onboarding, replay, design-system, device-testing.
- Checks at `16eb270`: lint, no warnings, 2496 tests 0 failures, release-check, Release strings
  `carodo.debug` 0. Simulator (AXe): Journeys → latest drive → Replay; Passport → My Garage;
  More → Trim (`-carodo.sampleJournal`); Settings → FAQ; kept flags: pending drive chip,
  connected-start banner, auto-finish stop.

### Step B, to plan before code (what still touches production)

| Hook | Where | Clean replacement to plan |
|---|---|---|
| startDrive, expandRecording, autoFinish, shortDrive, savedToast | `App/MainTabQA+Debug` (one `@State` and one awaited call in `MainTabView`), `DriveFlow.showForQA` | A scripted `LocationSource` fake chosen by the composition root (a drive, then a stop), started by tapping Start (AXe); or `xcrun simctl location` for a real recorded drive. Open question: the stop's minutes on a simulator clock |
| pendingDrive, pendingSheet | same | A motion fake (Auto Mode's detection) at the composition root |
| connectedToast, carPlay | same, `MainTabView.isCarPlayConnected` | A car-audio fake injected into `CarConnections` (created in `DependencyContainer.init` today) |
| offline | `Core/Diagnostics/NetworkPath.start` | The path's updates injected; the composition root gives "none" |
| replayExport (+4 options) | `ReplayView`'s task calls `ReplayExportBench` | An opt-in device test (`CarodoTests/Performance`) rendering a sample drive, or the Export screen driven by AXe |

### Step B, done (carodo-ios `c252787`, owner 2026-11-17: "use the showcase script to simulate")

- A drive's states are a showcase route played to Core Location (`showcase/sim_drive.py`), on the
  device database: start by one tap (AXe), auto-finish, Auto Mode. CarPlay and no network are
  fakes chosen by `DependencyContainer.live()` (`SampleHardware`, `Core/PreviewData`, Debug only),
  read by `CarConnections` (`readRoute`) and `NetworkPath` (injected updates). The export bench is
  the opt-in `ReplayExportPerformanceTests`. Flags 34 → 21, read only by the composition root and
  Debug-only files.
- No separate UI test target: XCUITest would need the same fakes (no motion, car audio or network
  switch on the Simulator) and a new target (P6). Revisit when regression runs are wanted.
- Checks at `c252787`: lint, no warnings, 2498 tests 0 failures (24 skipped: the opt-in ones),
  release-check, Release strings `carodo.debug` 0.
- Proven on the Simulator (iPhone 18 Pro, iOS 27.2, Debug), each on the real path:
  Prenn played after one tap → saved 10.8 km, 18 min, "Ended: by itself after stopping" (the route
  is 14.0 km: 3.2 km not kept, not investigated; the "Drive saved" toast was not caught on screen,
  its path is unit-tested); Auto Mode on, the same route without a tap → "I'm driving …" pending
  chip; `-carodo.debugCarPlay YES` on an empty garage → first car added and linked, "Recording
  with CarPlay · Started as Carodo opened in your car" with Undo; `-carodo.debugOffline YES` with
  the sample Feed → "You're offline".
- Next (owner): export a few short real drives as GPS showcase routes for this kind of check. Real
  tracks are development data: kept in `drive-data/`, never committed (handbook included) nor sent
  out without the owner's approval (AGENTS.md, Development data).

### Follow-up audit (2026-11-17, carodo-ios `1743fe2`)

A read of `main` after `e4b20ac` found three hooks left: `AppState.autoFinish` read
`carodo.autoFinish`, a key nothing wrote and Release honoured too (gone: auto-finish is on until
the Start panel's setting exists); `NarrativeLabView` read three flags and kept a static (the flags
are now read by `NarrativeLabEntry+Debug` and passed in as `NarrativeLabModel.AutoRun`; a run
starts each time the lab opens); `JourneysViewModel.listedJourneys`, left with no reader (gone).
Flags 21, read only by the composition root and Debug-only files. Kept as they are (composition
root, owner's call): `stopPlaceAnyStop` loosening the place resolver, and the Feed mock's seed
writing `FeedPublisher.sharingSinceKey`.
