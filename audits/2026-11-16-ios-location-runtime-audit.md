# Location, background and complexity audit — 2026-11-16

`carodo-ios` at `ef650f0`. Audit only, read-only; **no code before the owner approves each finding**
(`AGENT_WORKFLOW.md`, Plan before code). The question: are Core Location, Core Motion and the
background paths created, run and stopped as well as they can be, is anything split up or
duplicated, and is there O(n) work where the budget forbids it
(`carodo-ios/docs/architecture.md#complexity-budget`)? Three open-source drive and activity
recorders were read for comparison (section 3).

This file keeps apart **Today** (what the code does, with its file), **Proposed**, and **Assumed**
(not checked). Each finding lists every place it touches, so its impact can be judged before a fix
is chosen.

Sources read: `Core/Recording/{LocationSource, DriveSessionManager, RouteRecorder, TripWriter,
RecordingGPS, GapHealing}.swift`, `Core/Location/{CoreLocationServices, LocationPermissionManager,
CompassHeading, MapKitStationFinder}.swift`, `Core/Motion/{MotionActivity, Barometer,
MotionPermissionManager}.swift`, `Core/Tracking/TrackingModeController.swift`,
`Core/LiveActivity/DriveActivityController.swift`, `Core/Journal/JourneyMapSnapshotService.swift`,
`Core/Domain/{Geo, PrivateRegionRedaction, PlaceDetection, FrequentPlaces}.swift`,
`App/{BackgroundWork, DependencyContainer, MainTabView, CarodoApp, RootView}.swift`,
`Features/Map/{Views/MapAtlasView, ViewModels/MapAtlasViewModel}.swift`,
`Features/Passport/ViewModels/PassportViewModel.swift`, `Features/Feed/{Views/FeedView,
ViewModels/FeedViewModel}.swift`, `Features/Onboarding/Map/JourneyMapLayer.swift`,
`Core/Persistence/GRDBJourneyRepository.swift`, `project.yml`.

**Status (2026-11-16):** written, waiting for the owner's review. Nothing is fixed yet.

## 1. Summary

The location layer is sound. Each `CLLocationManager` has one job and runs only while that job
does; background location is on only while a drive records or Auto Mode detects; the per-fix
recording path is O(1) amortised; history-wide work runs off the main actor. The deliberate
difference from the reference apps (standard updates, not `CLLocationUpdate.liveUpdates`) is right
for Carodo and must stay (section 3).

| # | Finding | Severity | Confidence |
|---|---|---|---|
| F1 | The Feed invite builds a drive's shape on the main actor | Medium | Confirmed (isolation checked with the project's compiler flags) |
| F2 | `CompassHeading` can stop the compass of a newer stream | Low | Plausible (a race; not seen on the iPhone) |
| F3 | Two pieces of geometry copied instead of reused | Low | Confirmed |
| F4 | Three ways to get "where the phone is now" | Low | Confirmed |
| I1 | Ask for temporary full accuracy when location is Approximate | Idea (product, P6) | — |
| I2 | Absolute altitude from the barometer | Idea (feature, schema) | — |

## 2. Findings

### F1. The Feed invite builds a drive's shape on the main actor

**Today.** `DependencyContainer.latestCarDrive()` (`App/DependencyContainer.swift:359`) is
`nonisolated func … async` with no `@concurrent`. With `SWIFT_APPROACHABLE_CONCURRENCY: YES`
(`project.yml:23`, which turns on `NonisolatedNonsendingByDefault`) such a function runs on its
caller's actor. Its caller is `FeedViewModel.loadStanding()` (main actor) through the closure
`latestCarDrive: { [container] in await container.latestCarDrive() }` (`App/MainTabView.swift:192`).
Checked 2026-11-16 with a scratch program built with the project's flags (`-default-isolation
MainActor`, `NonisolatedNonsendingByDefault`): the plain `nonisolated async` call ran on the main
thread, the `@concurrent` one did not.

What it does there, on the main actor:

1. `journeyRepository.journeys(before: nil, limit: 30)`: `SELECT * FROM trips …`, so 30 full rows
   with their routes decoded (`GRDBJourneyRepository.swift:83`). The SQL itself runs on GRDB's
   queue; the decoding of `TripRecord` into `Journey` happens inside the read too. Off the main actor.
2. `journeyRepository.points(for:)` for the newest car drive: every accepted fix of that drive
   (about 10,000 for three hours). The read is off the main actor; the array lands on it.
3. `DriveShapeMaker.shape(route:…)` over those points: privacy cut, projection, principal axis,
   Douglas–Peucker. **On the main actor.** O(n log n) for one drive, O(n²) in Douglas–Peucker's
   worst case.

**Where it runs.** `FeedView` calls `loadStanding()` three times (`FeedView.swift:81, 103, 119`):
when the Feed appears, on pull to refresh, and after the join or profile sheet closes. Only when the
person is not sharing and has not snoozed the invite.

**Impact.** A hitch when opening the Feed after a long drive, on the frame the tab appears. Not
measured: the size of the hitch on the iPhone is an assumption until it is.

Also noted: `(try? await journeyRepository.points(for: journey)) ?? journey.route` folds a failed
read into the simplified route. The shape is a picture, not a figure, so the fallback is
acceptable under "Unknown is not zero"; say so in a comment when touching it.

**Proposed.**

- (a) Mark the pure part `@concurrent`: a `@concurrent nonisolated static func shape(…)` in
  `DependencyContainer` (or on `DriveShapeMaker` itself) called from `latestCarDrive`. One line of
  behaviour, no API change. Recommended.
- (b) Also read less: a light query for "the newest driver-rider car drive" (`drives()` already
  returns `DriveFact` rows without routes) and then `points(for:)` for that one drive only. Saves
  decoding 29 routes the invite never uses. Optional; a repository method is a small new query.
- Search the rest of the app for the same mistake: a `nonisolated … async` function with no
  `@concurrent` that does work, not only `await`s. Today the only other ones are
  `JourneyMapSnapshotService.snapshot` (fine: MapKit draws on the global queue it is given) and
  `CloudSyncService.handleEvent` / `nextRecordZoneChangeBatch` (fine: `CKSyncEngine` delegate, the
  work awaits the store). A test or a `task warnings` check could flag new ones; worth discussing.

**Tests.** A unit test that `latestCarDrive` returns the same invite as before for a synthetic
journal (no behaviour change). The hitch itself: before and after on the iPhone with Instruments
(Time Profiler on opening the Feed after a three-hour drive), per the complexity budget's rule that a
speed-up is claimed with numbers.

**Risk.** Low. The function already crosses an `await`; moving the shape off the main actor changes
no order of events.

### F2. `CompassHeading` can stop the compass of a newer stream

**Today.** `Core/Location/CompassHeading.swift`. `headings()` stores one `continuation`, starts
`startUpdatingHeading()`, and on termination schedules `Task { @MainActor in
self?.manager.stopUpdatingHeading() }`. The stop runs later, not at termination. If a new
`headings()` call starts updates before that `Task` runs, the old stream's stop turns off the new
stream's compass. The `continuation` field is also overwritten, so a second live stream would steal
the first one's headings.

**Where it runs.** One caller: `MapAtlasView` (`Features/Map/Views/MapAtlasView.swift:248`),
`.task(id: followMode == .heading)`. The task restarts when the follow mode toggles or the Map view
reappears (tab switch). The race needs a stop and a start within one main-actor turn, so it is
rare.

**Impact.** In heading follow, the map stops turning with the phone until the mode is toggled.
Display only; nothing recorded. Not seen on the iPhone.

**Proposed.** The shape `pilgrim-ios` uses for its `HeadingProvider` (section 3, idea only): a
`running` state, `start()` and `stop()` called directly. Concretely: give each stream a token; the
termination handler stops updates only when its token is still the current one, and clears
`continuation` only then. Keep the `AsyncStream` interface so `MapAtlasView` does not change.

**Tests.** A unit test behind a small protocol for the heading source (start/stop counts): start a
stream, end it, start another before the stop runs; the second keeps receiving. Today
`CompassHeading` takes no injected manager, so the test needs that seam (a protocol at a real
boundary, as the Swift rules allow).

**Risk.** Low; one file, one caller.

### F3. Two pieces of geometry copied instead of reused

**Today.**

- `DemoRoute.bearing(from:to:)` in `Features/Onboarding/Map/JourneyMapLayer.swift:271` is the same
  formula as `Geo.bearing(latitude:longitude:toLatitude:toLongitude:)` (`Core/Domain/Geo.swift:42`).
  One caller: `JourneyMapLayer.swift:126` (onboarding's demo drive heading).
- `GapHealing.closest(on:_:to:)` (`Core/Recording/GapHealing.swift:234`) projects to flat metres by
  hand with its own constant (`111_195`), while `LocalProjection` uses `111_320` and already has
  `xy(latitude:longitude:)` and `squaredDistance(from:toSegment:_:)`. Callers: `GapHealing.part`
  (lines 194–195), which serves `recordedPath(from:to:routes:)`, the lead-in from a road driven
  before (Auto Mode's missed start).

Other hand-written projections found, left alone: `SampleData` and `SampleJournal` (preview data,
synthetic routes), `PrivateRegionRedaction.swift:72` (the inverse, metres to degrees, already on
`LocalProjection.metersPerDegree`; `LocalProjection` has no inverse to reuse).

**Impact.** No visible bug today. A change to one copy misses the other (the 180th-meridian fix of
2026-11-16 had to be made in `GapHealing` by hand, carodo-ios `300805d`). Switching `GapHealing` to
`LocalProjection` moves its distances by about 0.1 % (the two constants), well inside the lead-in
thresholds (100 m to 1.5 km); its tests pass within their accuracies today.

**Proposed.** `DemoRoute.bearing` calls `Geo.bearing`; `GapHealing.closest` uses a
`LocalProjection` at the fix and `squaredDistance(from:toSegment:)` (which returns the clamped
fraction's distance; the fraction itself is still needed, so either extend `LocalProjection` with a
`closestFraction` or keep the dot product on its `xy` points).

**Tests.** The existing `GapHealingTests` (lead-in, round trip, 180th meridian) unchanged; the
onboarding demo heading has no test and needs none for a one-line reuse.

**Risk.** Low.

### F4. Three ways to get "where the phone is now"

**Today.**

| Where | How | Used by |
|---|---|---|
| `CoreLocationServices.setParkingSpotAtCurrentLocation` (`CoreLocationServices.swift:124`) | The fresher of its two managers' `location`, under 120 s, else `requestLocation()` | Auto Mode's parking circle |
| `MapKitStationFinder.currentLocation()` (`MapKitStationFinder.swift:39`) | A new `CLLocationManager`'s `location` under 120 s and 100 m, else the first `liveUpdates` fix within a timeout | The fill-up sheet's station list (`FuelEntryModel`) |
| `LocationPermissionManager.lastKnownCoordinate` (`LocationPermissionManager.swift:21`) | `manager.location?.coordinate`, no age check | The Map's marker before MapKit's first fix (`MapAtlasView.swift:647`) |

Each is correct for its use. But during a drive the session already holds a fresh accepted fix
(`DriveSessionManager.lastFix`), and logging fuel during a drive (the Live Activity's "Log fuel")
starts a second GPS request through `MapKitStationFinder`.

**Impact.** A few seconds of a second GPS request while one is already running: negligible battery,
a slower station list. No correctness issue.

**Proposed.** Not now. When the fill-up sheet is next changed: `NearbyStationFinding` takes an
optional fix from its caller (the recording drive's `lastFix` when one is open), and only looks one
up when none is given. Recorded in `plans/technical-debt.md` if the owner agrees.

**Risk.** Low; touches the fill-up flow merged with phase 1b today (`ef650f0`).

## 3. What the reference apps do

Read 2026-11-16 in `~/code/oss/swift` (`references/repos/ios.md`). Driveline is MIT; OutRun and
pilgrim-ios are GPL-3.0: **ideas only, no code copied**.

| | Driveline | OutRun | pilgrim-ios | Carodo |
|---|---|---|---|---|
| GPS API | `CLLocationUpdate.liveUpdates` | Standard updates | Standard updates | Standard updates |
| Background hold | `CLBackgroundActivitySession` | Background updates only while recording | Always on from the walk's start | `CLBackgroundActivitySession` while a drive is open (pause included), background updates only while it records |
| Managers | One | One, modes idle / recording | One per component (location, heading) | One per job (recording, standby, detection, permission, compass) |
| GPS while the app is open, not recording | No | Yes (idle mode, 25 m filter) | Yes while preparing a walk | No (MapKit's own user location) |
| Power tiers | No | No | Battery, heat, meditation | Battery, charging, stopped, hot, Low Power (`RecordingGPS`) |
| Persistence while recording | SwiftData | One write per fix on a background actor | The whole walk as JSON every 10–30 s (O(n) each, O(n²) a walk) | Batched rows in `trip_points`, written off the main actor; recovered at launch |
| Starts in the background | No (manual or Shortcuts) | No | No | Yes (Auto Mode after a region exit or significant change) |

What this means for Carodo:

- **Keep standard updates.** Driveline's `liveUpdates` works because its drives start in the
  foreground. Carodo's Auto Mode starts after iOS wakes it in the background, where a `liveUpdates`
  session was suspended within seconds (recorded in `CoreLocationServices.swift` and
  `LocationSource.swift`). Driveline's `streamProvider` / `sessionProvider` seams already exist here
  as `LocationSource` (with `ManualLocationSource`), `LocationServicesControlling`,
  `MotionActivityQuerying` and `BackgroundTaskSystem`.
- **Patterns to avoid, seen there:** a full-route checkpoint on a timer (pilgrim, O(n²) a walk); a
  lookup over all altitude samples on every fix (`altitudeData.last(where:)`, pilgrim); publishing
  the whole route array on each fix (pilgrim); a GPS kept on whenever the app is open (OutRun).
  Carodo's budget already forbids each.
- **Ideas worth keeping:** pilgrim's `HeadingProvider` shape for F2; I1 and I2 below.

## 4. Ideas (not findings)

### I1. Ask for temporary full accuracy when location is Approximate

**Today.** With Precise Location off, Carodo warns (`TrackingHealth` `approximateLocation`,
`MapStatus.preciseLocationOff`) and records what it gets. pilgrim-ios asks
`requestTemporaryFullAccuracyAuthorization(withPurposeKey:)` when a walk starts.

**Proposed.** At a drive's start with reduced accuracy, ask once for full accuracy for this session.
Needs a new Info.plist key (`NSLocationTemporaryUsageDescriptionDictionary`) with English and
Vietnamese text: an entitlement-level contract (P6), the owner's decision. A product change with
its own spec line in `docs/specs/` and `docs/privacy.md`.

### I2. Absolute altitude from the barometer

**Today.** `Barometer` records relative pressure (`trip_points.pressure_kpa`) for the elevation
chart. OutRun uses `CMAltimeter.startAbsoluteAltitudeUpdates` where available (iPhone 12 and later)
and relative altitude elsewhere.

**Proposed.** Not now. If the elevation chart needs better absolute heights, compare absolute
altitude with GPS altitude on real drives first; storing it is a schema change (TD-6 window).

## 5. Checked and fine

| Area | What was checked | Where |
|---|---|---|
| Recording GPS | Started with the drive, background updates turned off when it stops, `pausesLocationUpdatesAutomatically` false, accuracy and activity set per `RecordingGPS` | `Core/Recording/LocationSource.swift` |
| Background hold | One `CLBackgroundActivitySession` per open drive, its diagnostics task cancelled with it | `LocationSource.swift` (`holdBackground`, `endDrive`) |
| Standby | Significant changes, the parking circle and place regions on one manager; detection GPS on a second so its settings never touch the first; created at launch so a background relaunch reaches it | `Core/Location/CoreLocationServices.swift` |
| Map tab | MapKit's own user location, no extra GPS; the session's fixes while recording; the compass only in heading follow | `MapAtlasView.swift`, `AtlasMapView.swift` |
| Motion and barometer | Activity updates only while the GPS is lowered at a stop; the altimeter only while recording | `Core/Motion/` |
| Periodic work | The 20 s auto-finish check, the detection timeout and the Live Activity wake: `[weak self]`, cancelled with their owner | `DriveSessionManager.swift:834`, `TrackingModeController.swift:177`, `DriveActivityController.swift:153` |
| Background flush | Finite background time ended exactly once, on finish or expiry | `App/BackgroundWork.swift` |
| Per-fix path | Filter, append to the route, the live line and the writer's batch: O(1) amortised | `RouteRecorder.ingest`, `DriveSessionManager.ingest`, `TripWriter.record` |
| History-wide work | Off the main actor with `@concurrent`: the Map's redaction, place visit summaries, the Passport's geometry and glyph, the Journeys glyphs | `MapAtlasViewModel.swift:428, 532`, `PassportViewModel.swift:318, 338`, `JourneysViewModel.swift:465` |
| Loops inside loops | Only over small sets: route points × private circles, a drive's candidates × places, scored cells × places (once per run) | `PrivateRegionRedaction.redact`, `PlaceDetection.newPlaces`, `FrequentPlaces` |
| Map thumbnails | MapKit snapshots and their route drawing on a global queue | `JourneyMapSnapshotService.swift:225` |

## 6. Not covered

- O(n) work inside each View's `body` or a `Shape`'s `path`: relied on the budget and
  `ArchitectureTests`, not read view by view.
- iCloud sync (`CloudSyncService`) and the backend outbox.
- Anything measured on the iPhone: every impact above is from reading the code.

## 7. Plan, for approval

1. **F1** (one commit): `@concurrent` on the shape work, optionally the light read (b); before and
   after on the iPhone.
2. **F2 + F3** (one commit): the compass stream's token and its test; `Geo.bearing` and
   `LocalProjection` reused.
3. **F4, I1, I2**: rows in `plans/technical-debt.md` (or the backlog for I1 and I2) if the owner
   agrees; no code.
