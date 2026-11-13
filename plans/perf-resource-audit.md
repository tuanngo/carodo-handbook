# Performance and resource audit — findings and fix plan (2026-11-06)

Status (2026-11-13): **1–3 fixed and confirmed on the iPhone; 4 fixed in code (`isOffScreen` in
`JourneyDetailView.isCovered`), its memory not re-measured; 9 built (`-carodo.sampleJournal N`);
5/11, 12 and TD-12 done (carodo-ios 53edd24, b39f20c); 13 measured on the iPhone (4.5× faster);
14 done (cc2b501); 6 done (6947f81, merged e147432)**; 7, 8, 10 and Replay's Speed overlays open
(Still pending, at the end).
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
- **Done 2026-11-13** (carodo-ios `6947f81`, branch `perf/speed-overlays`, not yet in `main`).
  Counted on 31 real drives (`SpeedOverlayCountReplayTests`, opt-in): median 42 overlays, city
  drives 7–77, a 98 km drive 115, the 337 km drive 259; 13 of 31 over 50. Now one
  `MKMultiPolyline` per band plus one for the stop-and-go dots: 2–4 on every drive. iPhone 12 Pro
  Max, 337 km drive in Speed, Activity Monitor median:

  | | Carodo CPU | backboardd CPU |
  |---|---|---|
  | Still, before → after | 0.1 % → 0.1 % | 5.5 % → 5.7 % |
  | Panned and pinched by hand 38 s, before → after | 41.1 % → 38.1 % | 31.4 % → 27.0 % |

  A modest gain: on `MKMapView` 259 overlays cost far less than ADR 0015's 708 SwiftUI ones;
  panning is mostly tiles. One hand run each, so within noise of the gesture. Same look (owner
  checked on the device). Open: Replay's Speed still adds one `ReplayLine` per band run (its
  driven line animates per piece); apply the same rule once the Replay session's work lands.

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

## Second pass — 2026-11-12 (after source audit M04)

Found while fixing M04 (carodo-ios c88007e). Measured with `PlaceVisitsPerformanceTests`
(opt-in: `TEST_RUNNER_CARODO_PERF=1 TEST_RUNNER_CARODO_PERF_DRIVES=10000`), `SampleJournal` on an
on-disk WAL database, Debug build on the simulator: absolute times are above a Release build on an
iPhone; compare before and after on the same setup. Real routes average 2.7 KB (owner's iPhone,
26 drives; 3 over a 4 KB page), about 3.7 times `SampleJournal`'s, so route-bound costs are higher
on real data. None is a crash risk at realistic sizes (10,000 drives is years of heavy use); each
is CPU, memory and battery spent on a screen opening, growing with the journal.

### 11. Medium — Garage and a vehicle's page still load every journey with its route (issue 5, open)

- `GarageViewModel.swift:94` and `VehicleDetailViewModel.swift:85` call `journeys()`: every
  completed trip, its route decoded, then filtered and totalled on the main actor. The heaviest
  read left on a screen people open often. Fix as issue 5 says: totals and weekly distance in SQL,
  a vehicle page's own drives only (`WHERE vehicle_id = ?`), paged.

### 12. Medium — Journey Detail reads the whole journal on every open

- `JourneyDetailViewModel.loadPointCards` calls `passportFacts()` to count the visits of its
  points' places: every driven trip, each open of any journey with points (~150 ms at 10,000
  drives, Debug). Fix: for each place the points stand in, `drives(endingNear:)` (the
  `trips_on_end` index) and `PlaceVisitLog.summaries` on those few drives only; same counts.

### 13. Low — `passportFacts()` is a whole-journal read, ~18 % slower in Debug since M04

- Callers: the Passport (expected), the Map's visit counts (cached per journal revision and
  places), `BadgeLedger` when no facts are handed in, and issue 12. After M04 it reads four REAL
  columns per row instead of slicing the route blob: 127 → 150 ms at 10,000 drives in Debug
  (`GROUP BY` instead of the correlated parent subquery measured no better). Expected to reverse
  on real routes, whose slice walks overflow pages; **measure on the iPhone** with a real-sized
  journal before changing anything. If it stays slower: read the end columns only where a caller
  needs them, or keep one result per journal revision for its several callers.

### 14. Low — navigation values that carry journeys — done 2026-11-13 (carodo-ios cc2b501)

- Pages keep the ids of drives the journal still holds (from the Passport's facts, no read) and
  link by `AppRoute.journeyID`. Checked on the simulator by taps: a reached tier opens its drive,
  a locked one has no chevron. A debug-opened milestone page pushes under itself (TD-23, DEBUG only).

- `AppRoute` values stay in the stack while their page is open. `PlaceVisitsPage` no longer holds
  journeys (M04). Still holding one decoded `Journey` per row: the Passport's visited places
  (`PassportViewModel.swift:273`, the latest drive of each listed place), `PassportStampsPage` and
  `MilestoneDetailPage` (a drive per reached tier). Bounded by places and badges, so a few MB at
  most today, but it grows with them and every navigation compares and hashes these values. Fix:
  rows link by `AppRoute.journeyID` (read when opened), the pages keep only what rows show.

**Done 2026-11-12** (carodo-ios 7260c5f split the repository files first, then 53edd24, b39f20c;
merged into `main` with caf0915). 10,000 `SampleJournal` drives, Debug, simulator, before → after:

| Read | Before | After |
|---|---|---|
| Garage opens (`GarageViewModel.load`) | 149 ms | 51 ms |
| A vehicle's page (6,925 drives) | 102 ms | 30 ms |
| `passportFacts()` (issue 13) | 156 ms | 39 ms |
| A place's visits page, Home (4,959 visits) | 86 ms | 28 ms |
| Journey Detail point cards' visits, Home + an ordinary place | 50 ms (whole journal) | 39 ms (~2 ms without Home) |
| 30 earlier drives for the comparison | 0.6 ms (routes) | 0.2 ms (one column) |

- 11: `drives()` / `drives(of:)` (on `trips_on_vehicle`) return `DriveFact`s; the vehicle page
  lists no drives, so no paging was needed (TD-10's trigger did not fire).
- 13: the cost was not the SQL (25 ms) but reading each row's 20 columns **by name** (GRDB
  searches the row per lookup); `driveFacts` now reads by position. Still to measure on the iPhone.
- The Garage's weeks skip drives older than the bars before the calendar work (36 → 5 ms).
- Measured by `GaragePerformanceTests` and `PlaceVisitsPerformanceTests` (opt-in).

**On the iPhone (2026-11-13):** iPhone 14 "VanSam" (iOS 27), USB, Debug build, the same two tests
at 10,000 `SampleJournal` drives; before = carodo-ios 7260c5f (split, not optimised), after =
b525900. Warm runs (cold within a few ms):

| Read | Before | After |
|---|---|---|
| Garage opens | 539 ms | 138 ms |
| A vehicle's page (6,925 drives) | 346 ms | 74 ms |
| `passportFacts()` (issue 13) | 496 ms | 109 ms |
| A place's visits page, Home (4,959 visits) | 281 ms | 85 ms |
| A place's visits page, an ordinary place | 13.3 ms | 6.1 ms |
| Journey Detail point cards' visits (Home + ordinary) | ~520 ms (passportFacts + summaries) | 131 ms |
| 30 earlier drives for the comparison | 1.7 ms | 0.3 ms |

The iPhone is three to four times slower than the simulator in Debug, and the gains hold there:
issue 13 is answered (no need to keep one result per revision). The phone then got the owner's
29-drive journal and its own 3 drives restored (`-carodo.debugRestoreBackup` with the container's
absolute path, found by a unit test printing `NSHomeDirectory()`).

**Order for a new session (as written before the work):** 11 → 12 (largest and most frequent) → measure 13 on the iPhone over
USB (`xctrace`, the method above) → 14. Each with a before/after row in `PlaceVisitsPerformanceTests`
or a sibling test, and no schema change.

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

## Next session — issue 6, then what is still open (written 2026-11-13)

### Brief

```text
Outcome: issue 6 answered by measurement, and fixed only if the count says so.
Existing behaviour (read before planning): carodo-ios Features/Journeys/Views/JourneyDetailMap.swift
  (the detail map is an MKMapView now; `speedOverlays: [MKPolyline]` built on the first switch to
  Speed, one per `RouteMapContent.Line`), Core/Journal/RouteMapContent.swift,
  Core/Domain/JourneyAnalysis.swift `segments(of:)`, ADR 0015, docs/design-system.md (Map rules).
  The issue's text above predates the move to MKMapView: no SwiftUI MapPolyline is left there.
Step 1, measure (no device needed): count the speed-band segments per drive in the real journals
  in drive-data/ (newest TuanNgo iPhone pull: 29 drives, 1,135 km; VanSam now holds the same plus
  its own 3). Report the distribution (median, max, the city drives) locally only (P5, Development
  data: no plots or coordinates committed).
Step 2, decide: over ~50 overlays on a real drive → one MKMultiPolyline per band (4 overlays),
  the speed share bars keeping exact values; else record "measured, not a problem" and close 6.
Acceptance: before/after overlay count and a frame check of Speed on VanSam (USB, xctrace Activity
  Monitor, Method above) on the drive with the most segments; task lint, warnings, test pass.
Owner decisions needed: none for the multipolyline (a rendering detail, same look); any
  change to how bands look (merging short runs) is the owner's.
```

### Still pending (do not lose)

| Item | Where it stands | Next step |
|---|---|---|
| Issue 6, speed overlays | Done 2026-11-13 (`6947f81`, merged `e147432`) | Replay's Speed: same rule after the Replay session lands |
| Issue 4, Detail map memory | Fixed in code (`isOffScreen`), memory not re-measured | Xcode memory graph after Detail → Map tab on an iPhone: count live `MKMapView` |
| Issue 7, recording panel | Open: the 1 s `TimelineView` in `RecordingPanels.swift` (~l.447) wraps the panel body | Scope it to the time rows; measure with issue 1's method |
| Issue 8, Place editor | Open: `onMapCameraChange(.continuous)` writes the model per frame | Careful: the same handler detects the camera leaving the fallback frame; split that from the model write |
| Issue 10, UI scroll test | `CarodoUITests` target approved 2026-11-06, not started | Scroll/hitch metrics on Journeys and Feed with `-carodo.sampleJournal 2000` |
| TD-23 | DEBUG-opened Passport page pushes links under itself | With TD-14 (debug arguments in one place) |
| Lessons inbox | 8 of ~10 entries ([`lessons-inbox.md`](lessons-inbox.md)) | Build L5 (`docs/solutions/`) at ~10 or before TestFlight |
| Branches | Deleted 2026-11-13 (`refactor/repo-split`, `perf/passport-routes`, `perf/speed-overlays`, all merged) | Done |
| VanSam iPhone | Restored 32 drives; `Documents/restore.carodo`, `restore29.carodo` left in the app container | Leave, or delete with the app; never copy them elsewhere (P5) |
| Other sessions, uncommitted in carodo-ios `main` | L2 hot-phone GPS (waits for its device drive), Replay W2, `LaunchMark` staged | Theirs: never stage them; work in a worktree |
