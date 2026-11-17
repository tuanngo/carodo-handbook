# App shell split — `MainTabView` and `AppState` (composition audit step 4)

**Status:** handoff written 2026-11-18; **not started**, waiting for the owner's go and D1–D3
below. Step 4 of [`../audits/2026-11-18-ios-app-composition-audit.md`](../audits/2026-11-18-ios-app-composition-audit.md)
(findings F3, F4; the audit's D3 approved "F3 after F1, F4 only if still wanted"). Steps 1–3 are
done (carodo-ios `16efbd7`, `c4ed342`, `d7ee4bc`, `4ecd269`, `e240d9e`).

Read first: the audit's F3 and F4, `carodo-ios/AGENTS.md` (UI, Git, Recipes: a screen state to
check on the simulator), `carodo-ios/docs/design-system.md#screen-layout`.

## Where it stands (carodo-ios at `e240d9e`, re-measure before starting)

| File | Lines | Roles today |
|---|---|---|
| `App/MainTabView.swift` | 802 | Tab bar and 4 tab stacks (`tab(_:)`, 791); 13 `@State` (5 view models, 4 paths, garage state, `DriveFlow`); `body` 156–408 (7 sheets or covers, 17 `onChange`/`task`); the floating stack and banners (`floatingStack` 432, `discardedBanner` 500); drive actions (409–610); the model factories (`journeyDetail` 611, `placeNearby` 652, `carAudioVehicleEditor` 747, `fuelEntry` 762, `expenseEntry` 768, `vehicleEditor` 781, `backupModel` 570, `makeGarageModel` 44); `destination(for:)` 657–746, one case per `AppRoute` |
| `App/MainTabView+Sheets.swift` | 122 | Already split out: the sheets |
| `App/AppState.swift` | 314 | Preferences (18 functions take `defaults: UserDefaults`); three request/handled pairs (`requestDriveStart`/`drivePendingStartHandled`, `requestFuelLog`/`fuelLogHandled`, `requestLiveDrive`/`liveDriveHandled`) beside `mapIntent`, which already is a one-shot value; the `…DidChange()` signals |

`destination(for:)` is used three ways: the tab stacks' `navigationDestination` (797), the garage
sheet's stack (290–291) and a `routeDestination` closure (321).

## Task brief

```text
Outcome:
  MainTabView keeps tabs, paths, sheets and the drive's top-level wiring; where each AppRoute
  leads (and the model it needs) and the floating controls are views of their own. Optionally
  (D2) AppState's preferences are their own type. Nothing a person sees changes.
User story:
  None: a maintenance change so the busiest shared file is readable and collides less.
Existing behaviour (files read):
  The table above; App/{MainTabView, MainTabView+Sheets, AppState, AppRoute, DriveFlow,
  GarageSheetState, CarLogSheets}.swift.
Owner decisions needed:
  D1–D3 below.
Spec (Ready?) and mockups:
  No spec change: navigation and layout stay as they are (docs/specs/* unchanged).
Acceptance criteria:
  - MainTabView.swift about 500 lines: moving destination(for:) with the 8 factories (~230
    lines) and the floating stack with its banner (~100) reaches it; re-measure and state the
    figure the moves reach before promising it (AGENT_WORKFLOW, a target the steps can reach).
  - Every AppRoute opens the same screen from every tab, the garage sheet and routeDestination.
  - A view model a screen owns lives as long as before (see Constraints, identity).
  - task lint, task warnings, task test pass; screenshots as below.
Non-goals:
  New navigation (a router, coordinators, a routing library), new routes, visual or copy
  changes, DriveFlow's logic, the container.
Relevant files/docs:
  App/*, Features/* views that MainTabView builds, Carodo/Previews/App/MainTabView+Previews.swift,
  CarodoTests/App/{AppRouteTests, DriveFlowTests, GarageSheetStateTests, MapIntentTests},
  docs/architecture.md (App folder line), carodo-ios/AGENTS.md Architecture tree.
Constraints:
  - Cross-feature navigation stays in App/ (AGENTS.md, Recipes: a feature): the new files live
    in App/, never in a feature.
  - Identity: today a destination's model is made when its route is drawn. Moving the factory
    into another struct must not make it run on every MainTabView body pass or keep a model
    that today is fresh per push. Keep the model's creation at the same point of the view tree
    (inside the destination view's own @State or the same closure), and check it by pushing a
    journey, going back, pushing again.
  - No AnyView added; the existing two stay or go, never multiply.
  - Resource safety: no new task, timer or animation; the floating stack keeps its exact
    modifiers (Reduce Motion, the bar height measures).
  - MainTabView.swift and *.xcstrings are shared with other sessions: stage your own hunks only.
  - Run tests with task test (it waits for the shared simulator; a raw xcodebuild test does not).
Validation commands/device checks:
  task format, task lint, task warnings, task test, task release-check (previews and samples
  stay Debug only). Screenshots on your own simulator (docs/operations/setup.md#screenshots-as-evidence),
  reached by taps with AXe on -carodo.sampleData YES: each tab, a journey detail from Journeys
  and from the Map, the garage sheet and a car's page, the Start panel, recording (a route the
  Simulator plays), the discarded banner and the saved toast; Light, Dark, xxxLarge, Vietnamese.
  Device: none required beyond PV-33 (behaviour unchanged).
Allowed scope:
  App/MainTabView*.swift, new App/ files (D1), App/AppState.swift and its callers for F4 (D2,
  D3), their previews and tests, docs/architecture.md, carodo-ios/AGENTS.md (the App tree).
Do not:
  Change a route, a sheet's presentation, a string, a layout value, DriveFlow, or the
  container; add a dependency; commit without the screenshots.
```

## Slices (each one commit, proven)

1. **Destinations.** `AppDestination` (a `View` taking the route and what it reads:
   `container`, `appState`, `drive`, the garage state's callbacks) with `destination(for:)`'s
   switch and the 8 factories. `MainTabView`'s three uses call it. Tests: `AppRouteTests` still
   pass; add one only if a route's mapping becomes testable without a view.
2. **Floating controls.** `floatingStack` and `discardedBanner` as `FloatingDriveControls`
   (in `App/`, it reads `DriveFlow` and `AppState`). Screenshots of the states it draws.
3. **(D2) Preferences.** `AppPreferences`: the UserDefaults-backed values and their writes, held
   by `AppState`; keys unchanged (iOS invariant 8: UserDefaults keys are data). Tests:
   `AppStateVehicleChoiceTests` and a round trip per preference group.
4. **(D3) One-shot requests.** The three pairs become one optional value consumed once, as
   `mapIntent` is. Tests: each request handled once, a second request while one is pending.

## Owner decisions (with a recommendation)

- **D1: the names** `AppDestination` and `FloatingDriveControls`, both in `App/`. Recommend yes.
- **D2: do slice 3 (preferences) now.** Recommend **later**: `AppState` reads well today, and
  every feature touches it; do it when `AppState` next grows.
- **D3: do slice 4 (requests) now.** Recommend yes, small and it removes three event-as-state
  pairs; it goes with slice 1 or 2, not alone.

## Left open after steps 1–3 (already recorded)

PV-33 in [`technical-debt.md`](technical-debt.md): the device checks of steps 2–3 (inputs at
`init`, `TripReconciliation`).
