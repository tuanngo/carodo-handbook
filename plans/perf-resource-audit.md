# Performance and resource audit — findings and fix plan (2026-11-06)

Status: **issues 1–3 fixed and confirmed on the iPhone (2026-11-06); 4 inconclusive (memory graph next)**; 5–10 open.
Also recorded: the owner's route-colour decision in `carodo-ios/docs/design-system.md` (Route line
colours) and `docs/specs/navigation.md`.

Fixed (uncommitted; 862 tests pass on the simulator, lint clean; the new test is
`MapAtlasViewModelTests.testAStoppedDriveDoesNotMoveTheFollowingCamera`):
1. `MapAtlasView.follow(_:after:)` drops a drive fix that changes nothing on screen.
2. Feed `LiveRow`: a still dot (the pulse measured 4 % + 13 %, below). Re-measured 07:35: guest Feed, member Feed and the Leaderboard over the Feed all 0.0 % median (backboardd 1.9–3.3 %): fixed.
3. `BrandWheelDirector.isStill` (`OnboardingModel`): the stage poses once and stops rendering, and
   both onboarding display links poll at 30 Hz while still.
4. `JourneyDetailView`: its map is taken down on `onDisappear` (another tab or a pushed page).
Docs: design-system.md (map take-down, Brand 3D), navigation.md (drive fixes), feed.md (Live dot).

Re-measured on the iPhone (2026-11-06 06:52, same method, build with the four fixes):

| Screen | Before (Carodo / backboardd) | After | Verdict |
|---|---|---|---|
| Recording, Map tab, phone still | 24.5 % / 63.4 % | **0.3 % / 1.6 %** | fixed |
| Onboarding, a resting step | 10.6 % / 16.5 %, 417 MB | **0.6 % / 1.7 %**, 332 MB | fixed |
| Feed, guest | 18.8 % / 42.7 % | 4.3 % / 12.8 % | better, still over 1 % |
| Leaderboard over the Feed | 19.3 % / 49.7 % | 3.8 % / 12.9 % | better, still over 1 %: the Feed under it still costs as much as on screen |
| Detail → Map tab, memory at the end | 355 MB | 347 MB | inconclusive (below) |
| Map idle (check) | 0.1 %, 246 MB | 0.1 %, 257 MB | unchanged |

- **Feed:** the symbol pulse costs ~4 % in the app and ~13 % in the render server, and the same
  with the leaderboard pushed over it, so either `onDisappear` does not reach the rows under a
  push or the remaining cost is not the dot. Next: a static dot (the "Live" label already says it)
  and measure; if the 4 % stays, profile the Feed with a symbolicated build.
- **Detail map memory:** controls — Journeys list → Map ends at 293 MB; Detail → Feed stays at
  156 MB (Detail alone 157 MB). Memory is flat and CPU 0 %, so the map no longer renders, but its
  memory is not given back: either the view is still alive or MapKit keeps its tiles cached.
  Next: Xcode's memory graph after Detail → another tab, counting `MKMapView` instances.

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (recommended)
> or superpowers:executing-plans. One task per issue; each task ends with the same device
> measurement that found it (Method, below), before and after in the completion report.

References: `carodo-ios/docs/design-system.md` (Map tuning, Route line colours, Map rules — learned
the hard way, Map markers), carodo-ios ADR 0015.

## Method

- iPhone 17 Pro Max "TuanNgo iPhone" (iOS 27.2), **USB** (over Wi-Fi `xctrace` drops the device
  after ~1.4 s), Auto-Lock off. Build installed 2026-11-06 ~00:21 (Map on `MKMapView`); the vehicle
  colour work after it was not built.
- `xctrace record --template 'Activity Monitor' --all-processes` (attaching by pid or name fails on
  this device), 1 sample/s, first 5 s dropped, `Carodo` and `backboardd` (the render server: what
  the app's animation and map frames cost outside its own process). Screen opened with the DEBUG
  launch arguments of `docs/operations/setup.md`, `-carodo.hasCompletedOnboarding YES`, the sample
  journal (`-carodo.sampleData YES`, ~72 drives) except Trim (device database).
- Time Profiler traces recorded but not symbolicated (a Debug build has no dSYM: DWARF sits in
  `Carodo.debug.dylib`); causes below come from A/B runs plus the code. Scripts:
  `measure.sh` / `parse.py` (kept in the session scratchpad; to be added as `task perf` if wanted,
  see task 10).
- Threshold (owner): a still screen with median CPU > 1 % or memory growing is a problem; while
  recording, the per-second clock must not rebuild the parent screen.

## Measurements

| Screen (launch arguments) | Carodo CPU median / max | backboardd median | Memory start → end | Verdict |
|---|---|---|---|---|
| Map, idle (`debugTab map`) | 0.1 % / 6 % | 2.3 % | 300 → 246 MB | OK |
| Journeys, List | 0 % / 3 % | 2.2 % | 48 → 46 MB | OK |
| Journeys, Activity | 0 % / 3 % | 2.1 % | 44 → 42 MB | OK |
| Journeys, List, **scrolled by hand for 40 s** | 26.6 % / 36.7 % | 54.7 % | 56 → 55 MB (peaks 86) | OK: flat memory, thumbnails cached; hitches not measured (task 10) |
| Journey Detail, short (`debugOpenJourney 0`) | 0 % / 0.1 % | 2.1 % | 165 → 157 MB | OK |
| Journey Detail, 142-min drive (`debugOpenJourney 4`) | 0 % / 4.5 % | 2.2 % | 169 → 157 MB | OK with sample speeds (see issue 6) |
| Journey Detail, then the Map tab (`debugTabAfter map:8`) | 0.1 % / 51 % at the switch | 2.5 % | 172 → 355 MB | **+~110 MB** over Map idle (issue 4) |
| Trim (device database) | 0 % / 0.2 % | 2.2 % | 245 → 229 MB | OK |
| **Feed, guest** | **18.8 % / 22.6 %** | **42.7 %** | 42 → 40 MB | **issue 2** |
| Feed, member (`feedMember YES`) | 4.0 % / 4.3 % | 13.7 % | 42 → 39 MB | issue 2 |
| **Leaderboard pushed over the Feed** | **19.3 % / 20.5 %** | 49.7 % | 51 → 49 MB | issue 2 (the Feed under it still animates) |
| Passport | 0 % / 0.2 % | 2.1 % | 60 → 58 MB | OK |
| Garage | 0 % / 3.4 % | 1.9 % | 62 → 60 MB | OK at 72 drives (issue 5 at 2,000) |
| **Recording, Map tab, phone still** (`debugStartDrive YES`) | **24.5 % / 29.2 %** | **63.4 %** | 267 → 265 MB | **issue 1** (low for the first 11 s, before the first fix) |
| Recording, expanded panel | 5.7 % / 11.3 % | 9.4 % | 301 → 299 MB | issue 1 + issue 7 |
| Recording, Journeys tab | 0.5 % / 4.6 % | 2.2 % | 50 → 47 MB | OK: the per-second clock does not rebuild the parent |
| **Onboarding, a resting step** (`debugOnboardingScene 5`) | **10.6 % / 12.8 %** | 16.5 % | 424 → 417 MB | **issue 3** |
| Onboarding, a film (`debugOnboardingScene 1`) | 11.3 % / 15.9 % | 17.5 % | 433 → 417 MB | expected while playing |

No screen's memory grew over its run.

## Issues, most severe first

### 1. High — a recording map redraws every frame while the car stands still

- **Evidence:** Map tab while recording, phone on a desk: Carodo 24.5 %, backboardd 63.4 %, steady
  from the first fix (the first 11 s, "Finding GPS", sat at 0–3 %). Journeys tab while recording:
  0.5 %. A red light, a queue or a wait with the app open costs this much battery.
- **Cause:** `Features/Map/Views/MapAtlasView.swift:523` — every accepted drive fix calls
  `applyFollowCamera(.linear(glide))` (line 526), a linear glide lasting the time to the next fix,
  so the camera is always animating. The idle path (`show(_:)`, line 532) drops a fix that changes
  nothing on screen (`MapFix.changes(from:)`); the drive path does not.
- **Fix:** in `follow(_:after:)`, skip the camera command (keep placing the marker and the line)
  when `MapFix(fix…).changes(from: shownFix)` is false, and record `shownFix`. Moving fixes still
  glide, so driving looks the same. Unit-test the decision (a still fix sends no camera command, a
  moved one does) on a pure helper, not the view.
- **Done when:** recording on the Map tab, phone still, Carodo median ≤ 1 % after the first fix;
  a device drive still rolls smoothly (device check).

### 2. High — the Feed's "Live" dot animates forever, even when covered

- **Evidence:** guest Feed 18.8 % + backboardd 42.7 %; member Feed (fewer live rows) 4 %; with the
  leaderboard pushed over the Feed, still 19.3 %. The leaderboard has no animation of its own.
- **Cause:** `Features/Feed/Views/FeedView.swift:296` — `LiveRow` starts
  `.easeInOut(duration: 0.9).repeatForever()` on its opacity in `onAppear` and never stops; SwiftUI
  evaluates it every display frame (120 Hz) per row, and a pushed or other-tab view keeps it alive.
  It also ignores Reduce Motion.
- **Fix:** drop the SwiftUI repeat. Prefer a symbol with a system effect the render server runs
  (e.g. `Image(systemName: "circle.fill").symbolEffect(.pulse, options: .repeating, isActive:)` —
  `LiveStatusLabel`'s `.variableColor` costs ~0 % in-app, see "Recording, Journeys tab"), active only
  while the row is on screen (`onAppear`/`onDisappear` or `onScrollVisibilityChange`) and not under
  Reduce Motion; or a static dot. Owner picks the look.
- **Done when:** guest Feed and Leaderboard-over-Feed median ≤ 1 %.

### 3. Medium — onboarding renders 3D and the map every frame, also on resting steps

- **Evidence:** a resting step (Location permission) 10.6 %, the same as a playing film; ~420 MB.
- **Cause:** `DesignSystem/Brand3D/BrandWheelStage.swift:36` `rendersContinuously = true` and its
  `CADisplayLink` (line 169) run for the stage's whole life; `Features/Onboarding/Map/JourneyMapLayer.swift:59`
  adds a second `CADisplayLink`. `OnboardingView` pauses its `TimelineView`s when `isStill`
  (line 121) but not these two. While a name is typed the stage is at opacity 0 and still renders.
- **Fix:** give `BrandWheelDirector` a "still" signal (the model already knows: `isStill`); pause
  both display links (`isPaused = true`) and set `rendersContinuously = false` while still, then
  resume. Keep the two-key ignition (warm before the first frame). Verify on device that resuming
  shows no first-frame hitch (scenekit-product-stages skill).
- **Done when:** a resting step ≤ 1 %; films unchanged.

### 4. Medium — Journey Detail's map stays alive when another tab is shown

- **Evidence:** Detail open, then the Map tab: 355–375 MB against 246–262 MB for the Map alone
  (~110 MB, the size of the Detail map: Detail 157–169 MB vs the Journeys list 46 MB).
- **Cause:** `Features/Journeys/Views/JourneyDetailView.swift:61` — `isCovered` is
  `trimming != nil || isMapExpanded`; it misses "my tab is not selected" (design-system.md: "a map
  nobody sees is taken down … the Map tab's while another tab or page does").
- **Fix:** add the selected tab to `isCovered` (as the Map tab does: `appState.selectedTab`, or a
  `@Environment` value set per tab in `MainTabView`), so every map in a tab not shown is taken down.
  The same rule then covers a Detail page pushed on the Map or Feed tab.
- **Done when:** Detail → Map tab ends within ~20 MB of Map idle.

### 5. Medium — Garage and a vehicle's page load the whole journal with routes

- **Evidence:** code only (72 drives measure 0 %; the cost grows with the journal).
- **Cause:** `Features/Garage/ViewModels/GarageViewModel.swift:52` and
  `VehicleDetailViewModel.swift:53` call `journeyRepository.journeys()`: every completed trip with
  its decoded `route_simplified`, then filter, total and bucket by week on the main actor; the
  vehicle page keeps only its own drives.
- **Fix:** a repository read for what is drawn: per-vehicle totals and weekly distance in SQL (as
  `summary(in:)` and `passportFacts()` already do: no route), and for a vehicle page its drives
  only (`WHERE vehicle_id = ?`), paged like Journeys. No schema change.
- **Done when:** with 2,000 drives (task 9) opening the Garage stays under ~50 ms on the main
  actor and its memory near today's.

### 6. Medium (risk, not seen) — Journey Detail draws one `MapPolyline` per speed-band change

- **Evidence:** code; sample drives have smooth speeds, so it measured 0 %. A city drive whose
  speed crosses 30 or 60 km/h many times yields hundreds of segments.
- **Cause:** `DesignSystem/Components/RouteViews.swift:101` — one SwiftUI `MapPolyline` per
  `RouteMapContent.Line`, from `JourneyAnalysis.segments` (`Core/Domain/JourneyAnalysis.swift:90`),
  no bound; ADR 0015: 708 SwiftUI overlays held 100–170 % CPU.
- **Fix, measure first:** pull a real city drive (`task ios:pull-db`) and count its segments; if
  over ~50, either merge runs shorter than a minimum length/time into their neighbour's band (a
  display rule; the speed share bars keep exact values), or draw the detail map on `MKMapView`
  with one `MKMultiPolyline` per band (4 overlays), reusing `AtlasOverlays`. The latter is an ADR
  0015 amendment (owner).

### 7. Low — the expanded recording panel rebuilds its whole scroll view every second

- **Cause:** `Features/Drive/Views/RecordingPanels.swift:205` — the 1 s `TimelineView` wraps the
  `ScrollView`, including `ElevationChart` (Swift Charts). The compact panel (line 15) is scoped
  correctly.
- **Fix:** move the `TimelineView` into the header and the time-dependent rows only. Measure
  together with issue 1 (the panel's 5.7 % is mostly the map behind it).

### 8. Low — Place editor rebuilds its form every frame while the map is dragged

- **Cause:** `Features/Places/Views/PlaceEditorView.swift:133` —
  `onMapCameraChange(frequency: .continuous)` writes the model's latitude and longitude per frame.
- **Fix:** `.onEnd` for the model (the pin is the fixed centre overlay, so nothing needs the
  continuous value). Not measured (no launch argument opens the editor; add one).

### Not issues (checked)

- `UserAnnotation` only in the Place editor, where locating yourself is the point.
- `CompassHeading` stops with its task; the barometer runs only while recording.
- `BrandMarkEntranceView` (Journeys empty state) removes its SceneKit stage after 2.65 s. The
  Garage has no 3D wheel.
- `ListeningMark` (`CarAudioRows.swift:177`, `TimelineView(.animation)`) runs only while the Auto
  Mode sheet listens; not measured.
- GRDB reads run off the main actor; Passport reads no raw samples (`passportFacts`,
  `drivenRoutes`) and builds its geometry `@concurrent`; thumbnails are cached (memory 150 + disk),
  limited in flight, and cancelled when a row scrolls away.
- Route colours follow the new design-system rule: one drive in `CarodoSurface.accent` (Trim,
  snapshots, onboarding), Journey Detail by speed, the Map tab's Routes layer in
  `DriveHeatPalette.color(.few, …)` on light and dark.

## Tasks to add capability

### 9. A 2,000-drive journal (DEBUG) — proposal, needs owner approval

There is no way to load a large journal today: the sample journal is ~72 drives and lives in
`SampleRepository`, so it skips the GRDB paths that matter at scale.

- `-carodo.sampleJournal 2000`: at launch, an **in-memory** GRDB database (never the device file)
  filled with deterministic synthetic drives (`SampleData`'s generator, seeded; routes around a
  fixed synthetic origin, no real traces) through the real `TripStore` write path, then the live
  repositories on it. DEBUG only; documented in `docs/operations/setup.md`.
- Then re-measure Journeys (List, Activity, scrolling), Passport, Garage, the Map (routes, heatmap,
  footprint) and Detail at 2,000.

### 10. Scroll and hitch measurement as a UI test — proposal

- A `CarodoUITests` target (P6: a new target, owner approval) with `XCTOSSignpostMetric.scrollDecelerationMetric`
  and `XCTMemoryMetric` over Journeys List, Activity and the Feed, run on the iPhone with the
  2,000-drive journal; baseline stored in the scheme.
- Optionally `task perf SCREEN=…`: the launch + Activity Monitor + summary script used for this
  audit, so any agent can redo a row of the table.

## Order

1 → 2 → 3 → 4 (each small, each measured on the device) → 9 → 5 and 6 (they need the large or a
real journal) → 7, 8 → 10.
