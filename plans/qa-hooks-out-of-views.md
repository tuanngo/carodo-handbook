# QA hooks out of the production views

**Status:** not started (brief written 2026-11-17). Follows
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
