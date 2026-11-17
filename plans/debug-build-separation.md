# Debug and Release, kept apart

**Status:** done and committed (2026-11-17: carodo-ios `53b1d18`, `8d6541d`, `93c3df7`). Previews,
sample data, the QA launch flags and the Debug-only tools are out of Release.

## Goal (owner, 2026-11-17)

A Release build (TestFlight, the App Store) holds no preview, no sample data and no QA hook; a Debug
build keeps them all for local work (previews, mockups, the simulator with `-carodo.*` flags). Code
reads its production flow without `#if DEBUG`: the build system picks what each configuration
compiles, not conditionals in the code.

**Clarified (owner, 2026-11-17):** `#if DEBUG` is fine in production code when it sits inside one
small function whose only job is to say how this build behaves; what must not happen is `#if DEBUG`
scattered through views and flows, or sample and preview code reaching Release.

## What is done (carodo-ios, `main`)

| Commit | Outcome |
|---|---|
| `536e144` | The app never falls back on sample data: `DependencyContainer.init` takes a required `Stores` (journeys, vehicles, places, badges, community, tracking log); previews and tests pass `Stores.sample(...)`. A database that cannot be opened shows an empty journal, the backend's Feed and Apple's stations and places. `SeededGenerator` became `Core/Domain/SplitMix64` (the Feed's drive shape uses it) |
| `b41df51` | Every `#Preview` moved to `Carodo/Previews/<Feature>/<View>+Previews.swift`. `project.yml` excludes `Carodo/Previews` and `Core/PreviewData` from Release. No default container in the environment (`preconditionFailure`): `CarodoApp` injects one, a preview calls `.previewContainer()`. `task release-check` builds Release and reads the binary's symbols |
| `868ab8e` | The Live Activity's previews moved to `CarodoWidgets/Previews`, excluded from the widget's Release build |
| `aa88198` | `LaunchFlag` (Garage first): `Configuration/LaunchFlag.swift` names each QA flag; `LaunchFlag+Debug.swift` reads it, `LaunchFlag+Release.swift` reads none. `project.yml`: Debug excludes `*+Release.swift`, Release excludes `*+Debug.swift` |
| `53b1d18` | Every screen's QA hooks moved to `LaunchFlag` (120 cases). A flag's name comes from its case (`fuelEntry` is `-carodo.debugFuelEntry`, nine older ones have no `debug`), so Release holds none of the names; `LaunchFlagTests` fails on a flag missing from `docs/operations/setup.md`. Debug-only tools became `+Debug.swift` files: `DependencyContainer+Samples`, `ReplayExportBench` (was `ReplayExportDebug`), the narrative lab (`NarrativeLabEntry` is its door) |

Measured: Release `__TEXT` 14.64 MB → 14.46 MB (−180 KB); `#if DEBUG` from ~85 blocks in 45 files to
12 in 7; Release strings `carodo.debug…` 234 → 0. `task lint`, `task warnings`, `task test` (2497),
`task release-check` pass at `53b1d18`.

## How it works (read before changing it)

- **Three Debug-only places:** `Carodo/Previews/`, `Carodo/Core/PreviewData/`,
  `CarodoWidgets/Previews/` (excluded from Release in `project.yml`), plus any file named
  `*+Debug.swift`. A file the app calls in both builds is a pair, `X+Debug.swift` and
  `X+Release.swift`, with the same interface; the Release one answers "nothing" (nil, false, no-op,
  `EmptyView`).
- **`EXCLUDED_SOURCE_FILE_NAMES` gotcha:** `Folder/*` matches only the folder's own files; a
  subfolder needs `Folder/*/*` (and a bare folder name matched nothing). `Previews` is one level deep
  on purpose.
- **`#Preview` bodies are type-checked in Release** (measured: excluding the sample files broke 25
  views' previews). That is why previews live in their own excluded folder, not in the view's file.
- **`LaunchFlag`** is `nonisolated` (read off the main actor) and `CaseIterable`; it has no raw
  values on purpose (raw values kept every flag name in the Release binary). `.isOn`, `.text`,
  `.number`, `.digits`; `isOn(in:)`, `text(in:)`, `number(in:)` read another `UserDefaults` suite
  (tests, `AppState(defaults:)`).
- **Proof:** `task release-check` (Release compiles without the Debug-only files; no `Sample*`,
  `InMemory*`, `Showcase*`, `PreviewRegistry` symbol in the app or the widget). Strings:
  `strings build/release/Build/Products/Release-iphonesimulator/Carodo.app/Carodo | grep carodo.debug`
  prints nothing.
- **Launch flags are per run, not per build:** Xcode's scheme (Arguments Passed On Launch),
  `xcrun simctl launch <UDID> app.carodo.ios -carodo.sampleData YES …`, `devicectl … process launch`.
  A value fixed per build goes through xcconfig (`Configs/Local.xcconfig`) into Info.plist.

## Decisions and the last step (owner, 2026-11-17)

1. **Build behaviour keeps `#if DEBUG`**, each already one small function: `Configuration.current`,
   `apiBaseURL`, `BackendService.attestKey()`, `DatabaseManager.migrator`, `TrackingLogProfile.atLaunch`,
   `DeveloperAccess.currentBuild()`. No `BuildFlavor` pair.
2. **Footprint fog sliders deleted**: the owner chose 70 % (Light) and 60 % (Dark); `MapTuning.DebugKey`,
   the `@AppStorage` overrides in `MapAtlasView` and the five catalog strings went with them.
   **Geofency import** stays, Debug only: `GeofencyImportSection+Debug/+Release`, and
   `GeofencyImport`, `ZipEntry`, `GeofencyImportModel` renamed `+Debug` (their only reader).
3. **Samples in one place:** `Core/PreviewData/DependencyContainer+Samples.swift` holds `Stores.sample`,
   `SampleCommunityRepository.qa`, `FeedSharingActions.sample` and the QA containers
   (`sampleContainer`, sample and showcase journals). `SampleContainer.swift` and the App/ pair are
   gone; `live()` reads it in one `#if DEBUG` line, and `poiSearch(defaults:)` (private) picks
   `SamplePOISearch` the same way. `fixedFeedActions` is an init parameter (`let`). `journalSeed`
   stays a settable `var`: the showcase's seed task holds the container it seeds, so it is set
   after creation. `unsaved()` stays shared with the sample journal. `ArchitectureTests` names both
   files as the composition root (`compositionRoot`).

Result: `#if DEBUG` in 6 build-behaviour functions and 2 in `DependencyContainer` (`live()`,
`poiSearch`), none in a view. `task lint`, `task warnings`, `task test` (2497, 0 failures),
`task release-check` pass. Release strings: no `carodo.debug` flag; `footprintFogLight/Dark` remain as
`MapTuning`'s production property names. Simulator: `-carodo.sampleData YES -carodo.debugOpenDeveloper YES`
opens Developer without the fog section; the Geofency section (below the fold) was not seen.

## Seen on the way, not fixed

- The first launch after `simctl install` (straight after `task test` on the same simulator) showed
  Onboarding although `-carodo.hasCompletedOnboarding YES` was passed; a second launch was right.
  Seen with the Garage pilot too, so not caused by `LaunchFlag`. Not investigated.
- TD-53 (sample data built at every launch): closed 2026-11-17, confirmed in Debug under lldb
  (technical-debt.md).
- The `carodo-debug` software attestation is Debug only since carodo-ios `93c3df7`
  (`SoftwareAttestKey+Debug.swift`). `DebugLaunchArguments` stays compiled in Release (inert: it reads
  `LaunchFlag`): `MainTabView` and `DriveFlow` read 30+ of its fields in both builds, so a Release twin
  would copy them all. It goes with the next step, the QA hooks out of the production views
  (31 files read `LaunchFlag`; `JourneyDetailView` 10, `ReplayView` 6, `AppState` 6).
