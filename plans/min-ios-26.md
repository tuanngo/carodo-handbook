# Minimum iOS 26.0: audit and plan

Status: **Approved D1–D5 (owner, 2026-11-18). Slice 1 built and checked on the iOS 27.2 simulator (section 7); not yet run on an iOS 26.0 runtime (none installed). Slice 2 not started.** The owner's call (2026-11-18): raise the floor of all
of Carodo from iOS 18.0 to **iOS 26.0**, so the Map and place names leave `CLGeocoder`, the iOS 18 branches go, and
the services' outputs can be observed (`Observations`, iOS 26) instead of assigned closures. Provinces after
`CLGeocoder`: **(a) read from Apple's `cityWithContext`** until OSM phase 2 (owner, 2026-11-18). This plan replaces
ADR 0018's "a floor of iOS 26 was set aside" (pre-release: ADR 0018 is edited in place, `docs/decisions/README.md`).

Two slices, two commits. Slice 1 (the floor, the clean-up, the geocoder) is detailed here; slice 2 (the outputs of
`connect()`) is outlined, and gets its own short plan with the closure-by-closure list before any code.

## 1. Audit (what the code does today)

| Area | Today (file) | Impact at iOS 26 |
|---|---|---|
| Targets | `project.yml`: `options.deploymentTarget.iOS: "18.0"`, `IPHONEOS_DEPLOYMENT_TARGET: "18.0"`; app, widget and tests inherit | 2 lines, `xcodegen generate` |
| `FoundationModels` | `project.yml:152`: weak-linked, "iOS 18–25 still launch" | Linked normally. The model's own availability (`SystemLanguageModel.availability`: device not eligible, Apple Intelligence off) is still checked: an iPhone 11–15 runs iOS 26 without the model |
| `#available(iOS 26.0, *)` / `@available(iOS 26.0, *)` | 22 uses: `DesignSystem/PlatformCompatibility.swift` (7), `Core/Narrative/JourneyNarrator.swift` (3), `NarrativeEvaluation+Debug.swift` (1), `Core/Recognition/VehicleNameModel.swift` (5), `App/StartDriveIntent.swift` (2), `CarodoTests/Core/Backup/BackupTests.swift` (an `XCTSkip`) | All removed; the iOS 18 branch beside each goes with it |
| `PlatformCompatibility.swift` | The one file where Views meet APIs newer than iOS 18 (ADR 0018): `LiquidGlass.isAvailable`, `carodoGlass`, `CarodoGlassContainer`, `carodoBottomBar`, `carodoSoftTopScrollEdge`, `carodoHidesSharedBackground`, `MKMapItem.carodo(at:)`. Call sites: `FloatingNavigation` (4), `JourneyComponents` (2), `AppleMapsGapRouter` (2), `MainTabView+Sheets`, `JourneyDetailView`, `JourneyStorySheet`, `PassportView` | Each wrapper becomes one native call. Proposed: the file is deleted, the call sites call the API (decision D1) |
| Fallback-only code at call sites | Whatever a View adds only when `LiquidGlass.isAvailable` is false (a ring, a shadow); `carodoFloatingSurface(translucent: true)` reached from `carodoGlass` | Removed; `carodoFloatingSurface` kept only if a caller other than the fallback remains |
| `StartDriveIntent` | iOS 26: `supportedModes` + `continueInForeground`; before: `needsToContinueInForegroundError` (deprecated at 26) | One path: the iOS 26 one |
| `CLGeocoder` (TD-36) | `Core/MapLookup/PlaceLookup.swift`, `AppleGeocoderPlaceLookup`: `CLPlacemark` → `PlaceFields` (6 parts). Deprecated at 26, so it warns once the target is 26 and `task warnings` fails | Replaced by `MKReverseGeocodingRequest` in the same commit (section 2) |
| `MKMapItem.placemark` (TD-39) | `MapKitPOISearch.swift:45` (`item.placemark.coordinate`); `PlatformCompatibility.swift:104` (`MKPlacemark` fallback). TD-39 also names `MapKitStationFinder` | `item.location.coordinate`; the fallback goes. To confirm at build: the warning list at target 26 is the list fixed |
| iOS 27 deprecations (TD-39) | `ReplayMovieWriter` (async input receivers), `LanguageModelSession.GenerationError` | Not warned at a target of 26: out of scope, stay in TD-39 |
| Place-name cache | `Core/MapLookup/PlaceNameCache.swift`: `PlaceFields` per cell, a week at most, file `names-v2.json` (`fileVersion = 2`); every lookup goes through it, and only it calls `PlaceLookup` | Unchanged path; `fileVersion` 2 → 3 (section 2.3) |
| Rules | `CarodoTests/Rules/SwiftSourceTests.swift` (9 mentions) and `ArchitectureTests.swift` (1) name `CLGeocoder` / `CLPlacemark` | Reworded for `MKReverseGeocodingRequest` (the rule's intent: one owner of geocoding, R7/R8) |
| `task deprecations` | `Taskfile.yml:319`: builds with the target raised to the SDK because the iOS 18 target hid iOS 26–27 deprecations | Kept (it still finds iOS 27 ones); its text says iOS 26 |
| iOS 18.0 colour bridge | `CarodoSurface.swift:18`, `design-system.md:62`, `VehicleArtworkTests.swift:144`: on iOS 18.0 `UIColor(Color)` keeps only the Light value | **Not checked** whether iOS 26 still does it. Checked in the build on 26.0; removed only if it is fixed there |
| TD-19 (isolated deinit crash) | Crashes on iOS 18.6 **and 26.0** | The `nonisolated deinit` rule stays; the 18.6 check before TestFlight becomes a 26.0 check |
| Docs | carodo-ios `AGENTS.md:15` (Stack), ADR 0018, ADR 0012 (lines 27, 36), `decisions/README.md:52`, `operations/setup.md:5`, `design-system.md:432` (compatibility file), `architecture.md:435–444` (TD-19 runtimes), `data-model.md` (place-names table: Apple's names, section 2.2); workspace `AGENTS.md:46` | Reworded. `POINameLookup.swift`'s "`MKMapItemRequest`, iOS 18" is a fact about the API: kept |
| Simulators | Runtimes installed: 26.x and 27.2 (`docs/operations/setup.md`) | Every supported version is now checkable on a simulator: ADR 0018's "iOS 18 only on a device" gap closes |

Not checked yet (assumptions): that no other API Carodo calls is deprecated at 26 (the build at target 26 lists them;
anything beyond the table above stops the work and comes back as a question); that the 26.0 runtime is still installed.

## 2. The geocoder: `MKReverseGeocodingRequest`

### 2.1 What Apple returns (checked 2026-11-18, macOS 27, `vi_VN`, public landmarks only)

| Place | `cityName` | `cityWithContext(.full)` | `regionName` / `region` | `name` | `address.fullAddress` | Old `CLPlacemark` |
|---|---|---|---|---|---|---|
| Bến Thành market | P. Bến Thành | P. Bến Thành, Thành Phố Hồ Chí Minh, Việt Nam | Việt Nam / VN | Chợ Bến Thành | Chợ Bến Thành, Phan Chu Trinh, P. Bến Thành, Thành Phố Hồ Chí Minh, Việt Nam | locality P. Bến Thành, admin Thành Phố Hồ Chí Minh, thoroughfare Phan Chu Trinh |
| Nha Trang cathedral | P. Nha Trang | P. Nha Trang, Khánh Hòa, Việt Nam | Việt Nam / VN | Nhà thờ Chánh Tòa Nha Trang | Nhà thờ …, P. Nha Trang, Khánh Hòa, Việt Nam | admin Khánh Hòa, thoroughfare nil |
| Phan Rang | P. Phan Rang | P. Phan Rang, Khánh Hòa, Việt Nam | Việt Nam / VN | 15 Lê Hồng Phong | 15 Lê Hồng Phong, P. Phan Rang, Khánh Hòa, Việt Nam | thoroughfare Lê Hồng Phong |
| Apple Park | Cupertino | Cupertino, CA Hiệp Chủng Quốc Hoa Kỳ | … / US | Apple Park | Apple Park, 1 Apple Park Way, Cupertino, CA  95014, … | admin CA, subAdmin Santa Clara County, thoroughfare Apple Park Way |
| Ubud | Gianyar | Gianyar, Tỉnh Bali, Indonesia | Indonesia / ID | Jalan Raya Ubud | Jalan Raya Ubud, Gianyar, Tỉnh Bali, Indonesia | subLocality Ubud, admin Tỉnh Bali, thoroughfare Jalan Raya Ubud |

`pointOfInterestCategory` is nil on every result, so a point of interest cannot be told from an address by a field.

### 2.2 Mapping to `PlaceFields` (the domain type and its readers do not change)

| Part | From | Notes |
|---|---|---|
| `locality` | `cityName` | Same value as before in every row above: titles in Vietnam do not change |
| `countryCode` | `addressRepresentations.region?.identifier` | Same as `isoCountryCode` |
| `province` | `cityWithContext(.full)` with the leading `cityName` and the trailing `regionName` removed, separators trimmed | "Thành Phố Hồ Chí Minh", "Khánh Hòa", "CA", "Tỉnh Bali". Empty → nil. `ProvinceName.display` already shortens "Thành Phố …" and "Tỉnh …" |
| `street` | `address.fullAddress` cut before `cityName`. Two or more parts before it: the last is the street (house number dropped). One part: the street only when it starts with a house number (dropped), else nil | Bến Thành → Phan Chu Trinh; Phan Rang → Lê Hồng Phong; Apple Park → Apple Park Way; Nha Trang → nil (a point of interest, as before); **Ubud → nil (was Jalan Raya Ubud)**: a street named alone, without a number, is lost |
| `subLocality`, `district` | — | No such parts any more: always nil. In Vietnam both were empty or equal to `locality`, so titles do not move; abroad a title can read the town ("Gianyar") where it read the neighbourhood ("Ubud") |

The parsing is a pure function on strings (`PlaceFields.init(cityName:cityWithContext:regionName:region:fullAddress:)`
or a static on the adapter: D3), unit-tested with the five rows above as fixtures (public landmarks: no drive
data), plus empty and missing inputs, a city that also appears inside the street, and a `cityWithContext` without the
region. The adapter keeps the vi_VN-then-current-locale order, the `ProviderGate` call per request and a request per
lookup (`MKReverseGeocodingRequest` is single-use). "No result" (`MKError.placemarkNotFound`) stays nil; any other
error stays a `LookupFailure` through the gate, as today.

### 2.3 The cache

Every name is still read from `PlaceNameCache`, and only the cache calls the lookup: nothing above it changes. The
entries already on a device came from `CLGeocoder` (`district`, `subLocality` filled, a slightly different street), so
`fileVersion` 2 → 3: the old file is dropped, and each cell is asked once more when it is next on screen (at most a week
of entries; the journal stores only cells, so no title is lost, it is re-derived). `POINameCache` is untouched.

`PlaceNameCache.swift` and `MapDataCache.swift` carry another session's uncommitted changes today; slice 1 touches
only the `fileVersion` line there and adds to the file, never overwrites it (`AGENT_WORKFLOW.md`, Working in
parallel), or waits for that session's commit.

## 3. Slice 1: the floor (one commit)

1. `project.yml`: both targets 26.0; `FoundationModels` linked normally, its comment gone. `xcodegen generate`.
2. ADR 0018 rewritten in place: "Carodo runs on iOS 26 and later"; the reason (Liquid Glass and MapKit's geocoding
   without branches, `Observations`, every supported version on a simulator), the cost (iPhone XS, XS Max and XR,
   which iOS 26 does not run on; nobody runs Carodo yet), no compatibility file until a floor below the newest SDK
   needs one again. File renamed `0018-ios-26-minimum.md`; `decisions/README.md` row; ADR 0012's iOS 18–25 lines.
3. `PlatformCompatibility.swift` deleted; its call sites call `glassEffect`, `GlassEffectContainer`, `safeAreaBar`,
   `scrollEdgeEffectStyle`, `sharedBackgroundVisibility`, `MKMapItem(location:address:)` (D1). Fallback-only code at
   the call sites goes with it.
4. Narrative and Recognition: the `@available` and the `#available` gone; the model's availability check kept.
   `StartDriveIntent`: one path. `BackupTests`: no skip.
5. `AppleGeocoderPlaceLookup` → `MKReverseGeocodingRequest` (section 2), renamed for what it now uses (D3);
   `PlaceFields` doc comments name the new sources; `PlaceNameCache.fileVersion = 3`;
   `MapKitPOISearch` (and `MapKitStationFinder` if it warns) off `placemark`.
6. The rules in `SwiftSourceTests` / `ArchitectureTests` name the new request type.
7. Clean-up in the same commit: every comment that says "iOS 18", "before iOS 26", "the fallback" removed or
   reworded; the iOS 18.0 colour-bridge note only if 26.0 no longer needs it; nothing left unused (a fallback
   modifier, a catalog string, a doc row); TD-36 closed, TD-39 narrowed to the iOS 27 items, TD-19's check moved
   to 26.0 (`plans/technical-debt.md`).
8. Docs: section 1's Docs row; `data-model.md#place-names` table gets the new sources and the lost parts.

**Acceptance criteria**

- `grep -rn "#available\|@available(iOS" Carodo CarodoWidgets CarodoShared CarodoTests` finds nothing (the
  `@available(*, unavailable)` initialisers stay); no `CLGeocoder`, `CLPlacemark`, `MKPlacemark` or `.placemark`
  left; no "iOS 18" left in the sources or docs except facts about an API's own version.
- `task format`, `task lint`, `task warnings` (0 warnings at target 26), `task test` pass, on the 27.2 simulator and
  once on 26.0 (TD-19's runtime).
- The geocoder parser tests pass on the five fixtures; Journey Detail on the simulator shows the same start/end
  titles, provinces and stop areas for the showcase journal (`-carodo.showcaseJournal`) as before, place names
  asked again after the cache bump.
- Screenshots of the screens whose glass code moved (floating bar, a sheet, Journey Detail, Passport) on 26.0 and
  27.2, Light and Dark: unchanged on screen.

**Device checks still required:** a real drive's titles and Provinces Crossed on an iPhone (PV-26's route if
convenient). Nothing on the tracking path changes.

## 4. Slice 2 (outline only): the outputs of `connect()`

`connect()` (`App/DependencyContainer+Connect.swift`) assigns 17 closures after building the services. Before any code,
a short plan lists each one in one of three kinds:

| Kind | Examples | Proposal |
|---|---|---|
| Ordered: must run in the same call, before what follows | `driveSession.onActiveChange` (the tracking mode moves before the recording GPS starts), `carConnections.onCarAudioChange` → `driveSession`, `battery.onPowerChange` | **Stay closures.** `Observations` delivers after the change, coalesced, at a later suspension point: the order would break on the recording path |
| State the app shows | `onUntoldChange`, `cloudSync.onRemoteChange`, `onGarageChange`, the name caches' `setOnChange` | The service exposes `@Observable` state; `AppState` follows it (`Observations`), as OutRun's `observeRecording(of:)` |
| Events, not state | `driveSession.onDiagnostic`, `carConnections.onEvent` | `Observations` sees the latest state and would drop events between two looks: stay closures, or an `AsyncStream` (D4) |
| Inputs the service asks for | `driveActivity.isAppActive`, `.distanceUnit`, `.vehicle`, `.notice`, the Auto Mode settings | Not outputs: unchanged |

Expected size: `connect()` shrinks by about a third, not to a handful of lines. Its test is that a change on another
device or in the background still reaches the screen (`AppState`) without the closure.

## 5. Risks

- **Street on stop cards and a place's page** comes from text, not a field: a street named alone without a house
  number (Ubud) is lost; a format Apple changes could drop more. Tested on fixtures, re-checked on a real drive.
- **Province** comes from text too (accepted, owner 2026-11-18) until OSM phase 2.
- **Abroad, the title can read a coarser place** (the town, not the neighbourhood): `subLocality` is gone.
- **iPhone XS, XS Max, XR** cannot run Carodo. Nobody runs it today.
- TD-19 is not closed: 26.0 still crashes on an isolated deinit; the rule stays.

## 6. Owner decisions

| # | Question | Proposal |
|---|---|---|
| D1 | Keep the `carodo…` wrappers as Carodo's own names, or call the native APIs? | **Native APIs, file deleted.** A wrapper with one call inside hides the API a reader knows. A future floor below the SDK brings the file back for what needs it |
| D2 | Street: parse it from `fullAddress` (section 2.2), or show the ward only on stop cards? | **Parse.** It is right in four of five fixtures and the miss shows the ward alone, as today when Apple has no street |
| D3 | Name of the adapter | `AppleMapsPlaceLookup` (it is MapKit now, not "the geocoder"); the parser beside it in `Core/MapLookup` |
| D4 | Slice 2's events | Stay closures (one listener each); an `AsyncStream` only if a second listener appears |
| D5 | Order | Slice 1 now; slice 2's list after slice 1 is committed |

## 7. Slice 1: result (2026-11-18)

Built in the worktree `carodo-ios-ios26` (branch `feat/ios-26`) as planned, with these differences found on the way:

- **`PlaceFields` lost `subLocality` and `district`**: no source fills them now, so they and `PlaceName`'s
  fallbacks went (nothing left unused); their tests use `locality`.
- **Off the coast Apple gives the country as the city** (`cityName` "Việt Nam", context "Vịnh Chân Mây, Việt Nam"):
  read as no place; a city-state ("Singapore, Singapore") keeps its city. A test for each.
- **`ForegroundContinuableIntent` is deprecated at 26**: `StartDriveIntent` keeps `supportedModes` only.
- **`task warnings`' isolated-deinit check would have gone blind at a target of 26**: it matched only the
  back-deployed `swift_task_deinitOnExecutorMainActorBackDeploy`; at 26 the call is `swift_task_deinitOnExecutor`
  (seen in the binary: only Xcode's `ResourceBundleClass`). The pattern now matches both.
- `FoundationModels` is linked by `import` alone (the `project.yml` entry went); `JourneyNarrators` and
  `VehicleNameModels` went with their `#available`, the call sites build Apple's model directly.
- `SwiftSourceTests` keep `CLGeocoder` as text in their reader fixtures (strings, not an API use), and
  `ArchitectureTests` keeps it in R7's list of request types.

Checks after the last change: `task lint` passes; `task warnings`: no warnings, no isolated deinits;
`task test` (iPhone 18 Pro, iOS 27.2): 2,541 tests, 0 failures, 24 skipped (opt-in). The geocoder was compared
with `CLGeocoder` on nine public places (section 2.1, plus Hải Vân, Lăng Cô, Chân Mây, Prenn): the ward and
province match everywhere on land. In the app (showcase drives) titles read "P. Hải Vân → X. Chân Mây - Lăng Cô",
"X. Đồng Văn → X. Mèo Vạc"; screenshots (Journeys, Journey Detail Dark, Passport Light at xxxLarge) show the glass
bar, toolbar and scroll edges as before.

Left open: **TD-62** (names sometimes missing after a cold launch, on `main` too); the iOS 26.0 runtime run
(TD-19); a real drive's titles, stops and provinces on an iPhone.
