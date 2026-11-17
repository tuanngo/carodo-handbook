# Debug and Release, kept apart

**Status:** in progress. Previews, sample data and the QA launch flags are out of Release (done,
2026-11-17). Left: the build behaviours still under `#if DEBUG`, Developer's fog and Geofency tools,
and a review of `DependencyContainer+Samples+Debug/Release`. Handoff for the next session below.

## Goal (owner, 2026-11-17)

A Release build (TestFlight, the App Store) holds no preview, no sample data and no QA hook; a Debug
build keeps them all for local work (previews, mockups, the simulator with `-carodo.*` flags). Code
reads its production flow without `#if DEBUG`: the build system picks what each configuration
compiles, not conditionals in the code.

## What is done (carodo-ios, `main`, not pushed)

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

## Handoff: the next session

```text
Outcome:
  No `#if DEBUG` left in carodo-ios outside the +Debug/+Release pairs, and DependencyContainer's
  sample containers reviewed and settled.

Existing behaviour (files read):
  `#if DEBUG` remains in (as of 53b1d18):
  - Build behaviour:
    Carodo/Configuration/Configuration.swift:18, :38   environment and backend URL
    Carodo/Core/Networking/BackendService.swift:30     App Attest: software key in Debug
    Carodo/Core/Persistence/DatabaseManager.swift:50   erase the database on a schema change
    Carodo/Core/Diagnostics/TrackingLog.swift:574      the log profile at launch
    Carodo/Core/Diagnostics/DeveloperAccess.swift:32   Developer access
  - Developer tools:
    Carodo/DesignSystem/MapTuning.swift:59             fog keys (`MapTuning.DebugKey`)
    Carodo/Features/Developer/Views/DeveloperView.swift:20, :54, :64   fog sliders, Geofency import
    Carodo/Features/Map/Views/MapAtlasView.swift:62, :363              the map reads the fog sliders
  DependencyContainer+Samples (Carodo/App):
    +Debug: sampleContainer(defaults:) for -carodo.sampleData / sampleJournal / showcaseJournal,
    samplePOISearch(defaults:) for -carodo.debugSamplePlaces, and the sample and showcase journals.
    +Release: both return nil.

Owner decisions needed:
  1. Build behaviour: one `BuildFlavor` pair (`BuildFlavor+Debug/+Release`, `isDebug` constant) the
     five call sites read, or a pair per concern? Recommendation: a pair per concern where the Debug
     side carries code (App Attest's software key, the schema reset), a constant where it is a value
     (the log profile, Developer access); the backend URL stays with xcconfig/Info.plist.
  2. Footprint fog sliders: delete them (MapTuning's comment says they go once the values are
     chosen) or move them to a +Debug file? Geofency import: keep as a +Debug Developer section?
  3. DependencyContainer+Samples (review points below): keep in Carodo/App, or move the Debug half
     into Core/PreviewData beside SampleContainer.swift?

Review points for DependencyContainer+Samples:
  - It widened `unsaved(_:isStorageUnavailable:)`, `inMemory()`, `journalSeed` and
    `fixedFeedActions` from private to internal so the extension can reach them. Check nothing else
    starts using them; `journalSeed` and `fixedFeedActions` are QA-only state on a production type.
  - `sampleJournal(count:)` reuses `unsaved`, the production fallback for a database that cannot be
    opened: one path, two purposes. Keep it, or give the sample journal its own builder.
  - `Core/PreviewData/SampleContainer.swift` (`Stores.sample`, `SampleCommunityRepository.qa`,
    `FeedSharingActions.sample`) and `DependencyContainer+Samples+Debug.swift` do the same job for
    previews and for QA launches: one file may be enough (PreviewData is already Debug-only, so the
    Debug half needs no `+Debug` name there; the Release stub would stay in Carodo/App).
  - `ArchitectureTests` (one-lookup-owner rules, lines ~173 and ~198) now exempt the prefix
    `Carodo/App/DependencyContainer`, so both Samples files may create Apple Maps lookups (the
    showcase journal names places). Moving the file means moving that exemption.
  - `inMemory()` ends in `preconditionFailure` when the schema cannot be created in memory (a
    broken build, which the migrator tests catch); the owner accepted no sample fallback.

Acceptance criteria:
  - `grep -rn "#if DEBUG" Carodo CarodoShared CarodoWidgets` prints nothing (or only what the owner
    keeps, named in this plan).
  - Debug behaves as today: schema reset, software App Attest key, developer log profile, the local
    backend URL; Release as today.
  - `task lint`, `task warnings`, `task test`, `task release-check` pass; `strings` on the Release
    binary finds no `carodo.debug` and no fog key.

Non-goals:
  Renaming the `-carodo.debug…` flags (docs and habits use them); Swift packages or new targets for
  the Debug code (P6, and the folder exclusion already does it).

Relevant files/docs:
  carodo-ios: project.yml (Debug/Release EXCLUDED_SOURCE_FILE_NAMES), Taskfile.yml (release-check),
  Carodo/Configuration/LaunchFlag*.swift, Carodo/App/DependencyContainer*.swift,
  Carodo/Core/PreviewData/SampleContainer.swift, AGENTS.md ("A preview or a mockup", "A screen state
  to check on the simulator"), docs/operations/setup.md#qa-launch-arguments-debug,
  docs/architecture.md (the Previews/PreviewData row).

Constraints:
  project.yml changes need the owner's approval (P6). Before the first TestFlight build the schema
  reset must stay Debug-only (invariant 6). App Attest: Release never gets the software key (P7).

Validation commands/device checks:
  task generate && task lint && task warnings && task test && task release-check
  Simulator (by UDID): -carodo.sampleData YES -carodo.hasCompletedOnboarding YES plus a flag per
  converted hook. A Debug install on the iPhone after the build-behaviour change: the schema reset
  still asks CONFIRM=erase (`task device`), App Attest still attests with the software key.

Do not:
  Bring `#if DEBUG` back into a view or a view model; give LaunchFlag raw values; put a sample type
  in a production path (the Release build fails, by design).
```

## Seen on the way, not fixed

- The first launch after `simctl install` (straight after `task test` on the same simulator) showed
  Onboarding although `-carodo.hasCompletedOnboarding YES` was passed; a second launch was right.
  Seen with the Garage pilot too, so not caused by `LaunchFlag`. Not investigated.
- TD-53 (sample data built at every launch): Release can no longer build sample data at all (no
  `Sample*` symbol in the binary since `b41df51`). Close it after one live-launch trace confirms
  `SampleJourneyRepository.init` is gone in Debug too.
