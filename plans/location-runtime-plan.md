# Location runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every sensor (GPS, compass, motion) is created in one folder, behind a protocol with a
fake, owned by the composition root, and five source-reading tests keep it so; the audit's findings
F1–F4 are fixed on the way.

**Architecture:** Files move with no type renamed (slice A, no behaviour change), then two small
seams are added, `HeadingSource` and `CurrentPositionProviding`, and the on/off handling is
tightened (slice B). Several `CLLocationManager`s stay, one job each. Rules live in
`ArchitectureTests`, behaviour tests run on fakes.

**Tech Stack:** Swift 6.2 (main actor by default, `@concurrent` to leave it), Core Location, Core
Motion, XCTest, XcodeGen, `task` shortcuts.

**Spec:** [`location-runtime.md`](location-runtime.md) (approved 2026-11-16 with D1–D3). Read it
first, then `carodo-ios/AGENTS.md`. The audit behind it:
[`../audits/2026-11-16-ios-location-runtime-audit.md`](../audits/2026-11-16-ios-location-runtime-audit.md).

**Status (2026-11-16):** plan approved by the owner; handed to an agent. **Changed by the
owner the same day:** slice B is committed once its unit tests and the simulator before/after
(Task 8, Step 3) pass; the drive on the iPhone follows as a pending validation (a PV row), not as
a gate. This replaces every line below that says slice B waits for the field review.

**Done (2026-11-16):** both slices built and committed on `refactor/location-runtime` in
`../carodo-ios-location-runtime`: slice A `567a787`, slice B `9ccaa95`; not merged, not pushed, not
installed on an iPhone. Checks: lint clean, no warnings, 2,417 unit tests, `task replay` and
`task showcase` identical to the baselines, the simulator's before and after within 0.3 %. The drive
on the iPhone is PV-26 ([`../field-tests/2026-11-16-location-runtime.md`](../field-tests/2026-11-16-location-runtime.md));
what is left open: TD-44, TD-45 ([`technical-debt.md`](technical-debt.md)).

## Global Constraints

- Repo `carodo-ios`, base `b143467`. Work in a worktree:
  `git worktree add ../carodo-ios-location-runtime -b refactor/location-runtime`, then
  `xcodegen generate` there. Before the first move: `git status` and `git log -3` on every file
  named in Task 1; a file changed since `b143467` is re-read, never overwritten.
- **No Swift type is renamed.** No threshold, filter or detection rule changes. No schema, API,
  permission, entitlement, background mode or dependency changes (P6). Standard location updates
  stay for recording and detection.
- Never hand-edit `Carodo.xcodeproj`; after moving files run `xcodegen generate`.
- Swift rules of `AGENTS.md`: no `!`, `try!`, `as!`, `DispatchQueue`, `Task.detached`,
  `@unchecked Sendable`; every main-actor class declares `nonisolated deinit {}`; a stored closure
  or `Task` in a service captures `[weak self]`.
- No coordinate, place name or plate in a log, a test fixture or a committed file (P5). Fixtures
  are synthetic.
- `CarodoTests/` stays flat: one file per subject at the top level.
- Checks, from the worktree, after the last edit of each task: `task format`, `task lint`,
  `task warnings`, `task test`. Report the run after the last change.
- Commits: lowercase conventional, **no AI attribution of any kind** (P8). Stage by path only.
  **Slice A is committed when its checks pass. Slice B is never committed by the agent**: it waits
  for the owner's field review (spec, section 8).
- Docs in English; they change in the same commit as the behaviour.
- A finding that needs a contract, a schema or another feature's files stops the work and goes to
  the owner.

## Review Focus

1. **iOS relaunches the app in the background (region exit) with no view drawn.** The standby
   services and the session must still be created at launch, in today's order. Pinned in Task 1,
   Step 6.
2. **The fill-up sheet opens with location denied, Approximate, or a fix worse than 100 m.** The
   station list is nil or waits for a better fix; it never shows stations around a wrong place.
   Pinned in Task 5, Step 1.
3. **A paused drive's last fix is old.** "Where the phone is now" must not answer with it. Pinned
   in Task 5, Step 1.
4. **The Map is left and re-entered, or heading follow toggled twice, within one turn of the main
   actor.** The compass keeps turning the map. Pinned in Task 4, Step 1.
5. **Sample-data mode and previews never touch Core Location.** A `DependencyContainer()` built
   with defaults holds fakes for the new seams. Pinned in Task 5, Step 1.

---

## File map

```
Carodo/Core/Location/            (sensors only)
  LocationSource.swift             moved from Core/Recording; keeps the protocol, BackgroundHold and its init
  CoreLocationSource.swift         split out: the class + `LocationSample.init(location:)`
  ManualLocationSource.swift       split out: the fake
  LocationServicesControlling.swift  the protocol, cut from Core/Tracking/TrackingModeController.swift
  CoreLocationServices.swift       stays
  InertLocationServices.swift      stays
  HeadingSource.swift              new (Task 4): protocol, `NoHeading`, `CompassControlling`
  CompassHeading.swift             stays, changed in Task 4
  CurrentPosition.swift            new (Task 5): protocol, `CurrentPositionChoice`, `NoCurrentPosition`
  CoreCurrentPosition.swift        new (Task 5)
  LocationPermissionManager.swift  stays, loses `lastKnownCoordinate` in Task 5
Carodo/Core/MapLookup/           (new folder; files moved unchanged from Core/Location)
  AppleMapsGapRouter, MapDataCache, MapKitPOISearch, MapKitStationFinder, PlaceLookup,
  PlaceNameCache, POINameLookup, JourneyPointServices
Carodo/Core/Tracking/TravelHeading.swift   moved from Core/Location (a pure rule)
CarodoTests/
  ArchitectureTests.swift          R1–R5 added
  CompassHeadingTests.swift        new
  CurrentPositionTests.swift       new
  FeedInviteDriveTests.swift       new
  SensorLifecycleTests.swift       new (Task 7)
```

---

## Slice A: gather, no behaviour change

### Task 1: Move the files

**Files:** as the file map, moves and one split only. Modify `Core/Tracking/TrackingModeController.swift`
(the protocol leaves it).

**Interfaces:** Produces the folder layout later tasks name. Every type keeps its name and members.

- [ ] **Step 1: Baselines, before anything moves.** In the worktree run `task test`, `task replay`
  and `task showcase`; save the three outputs in the scratchpad as `baseline-test.txt`,
  `baseline-replay.txt`, `baseline-showcase.txt`. Expected: all pass. If `task replay` has no
  database, note it and go on with `task showcase` alone.
- [ ] **Step 2: Move with `git mv`** so history follows: the eight lookup files to
  `Carodo/Core/MapLookup/`, `TravelHeading.swift` to `Carodo/Core/Tracking/`,
  `Core/Recording/LocationSource.swift` to `Core/Location/`.
- [ ] **Step 3: Split `LocationSource.swift`** by cutting text, changing none: `CoreLocationSource`
  and the `LocationSample.init(location:)` extension into `CoreLocationSource.swift`;
  `ManualLocationSource` into `ManualLocationSource.swift`; the protocol, `BackgroundHold` and its
  `init(_ diagnostic:)` stay.
- [ ] **Step 4: Cut `protocol LocationServicesControlling`** with its doc comment out of
  `TrackingModeController.swift` into `Core/Location/LocationServicesControlling.swift`.
- [ ] **Step 5: `xcodegen generate`, then `task build`.** Expected: builds; `git diff --stat` shows
  renames and the two splits only (no line of logic added or removed: check with
  `git diff -M --stat` that moved files read 100 % similar, and the split parts sum to the old file).
- [ ] **Step 6: `task test`, `task replay`, `task showcase`.** Expected: the same counts and the
  same lines as the three baselines (`diff` each). `AppLaunchTests` passing covers Review Focus 1;
  also confirm by reading that `DependencyContainer`'s live factory still creates
  `CoreLocationServices` and calls `logRestoredRegions()` before the container, as at `b143467`.

No commit yet: slice A is one commit (Task 3).

### Task 2: F1, the isolation rule (R4), the motion rule (R2), one bearing

**Files:**
- Modify: `Carodo/App/DependencyContainer.swift` (`latestCarDrive`, about line 370)
- Modify: `Carodo/Features/Onboarding/Map/JourneyMapLayer.swift` (`DemoRoute.bearing`, about line 271)
- Test: `CarodoTests/ArchitectureTests.swift`, `CarodoTests/FeedInviteDriveTests.swift` (new)

**Interfaces:**
- Produces: `DependencyContainer.inviteShape(route: [CLLocationCoordinate2D], tripID: UUID) async -> DriveShape?`,
  `@concurrent private nonisolated static`.

- [ ] **Step 1: Write R4, failing.** In `ArchitectureTests`:
  `testWorkInANonisolatedAsyncFunctionIsConcurrent`. It reads every `.swift` under `Carodo/`,
  finds each declaration line matching `nonisolated` … `func` … `async` whose own line and the
  line before hold no `@concurrent`, and asserts the found list (`File.swift: funcName`) equals
  this allow-list, each entry with its reason in a comment:
  `JourneyMapSnapshotService.swift: snapshot` (MapKit draws on the queue it is given),
  `CloudSyncService.swift: handleEvent` and `CloudSyncService.swift: nextRecordZoneChangeBatch`
  (`CKSyncEngine` delegate; the work awaits the store). Protocol requirements (a `func` line
  inside a `protocol` body, no `{`) are skipped.
- [ ] **Step 2: Run it.** `xcodebuild test … -only-testing:CarodoTests/ArchitectureTests`.
  Expected: FAIL, naming `DependencyContainer.swift: latestCarDrive`. If it names others, each is
  read: work on the caller's actor is fixed here the same way; a pure `await` chain joins the
  allow-list with its reason; anything unclear goes in the report.
- [ ] **Step 3: Write `FeedInviteDriveTests.testTheInviteIsTheNewestCarDriveWithItsShape`.** Build
  `DependencyContainer(journeyRepository:vehicleRepository:)` on the sample repositories (as
  `CarodoAppTests` does), call `latestCarDrive()`, and assert against the same sample journey read
  directly: `distanceM`, `durationS`, `car`, and `shape == DriveShapeMaker.shape(route:tripID:
  privacyZone: .default, homeAndWork: [])` for that journey's points. A second test: a journal with
  no car drive gives nil. Run: PASS on today's code (it pins behaviour before the change).
- [ ] **Step 4: Fix F1.** Add `inviteShape` (signature above; its body is today's
  `DriveShapeMaker.shape` call with `.default` and `[]`) and `await` it from `latestCarDrive`.
  `latestCarDrive` itself gets `@concurrent`: it only awaits repositories and builds a value. Add
  the comment the audit asked for at the `?? journey.route` fallback: the shape is a picture, not
  a figure, so the simplified route is a sound fallback.
- [ ] **Step 5: Write R2.** `testOnlyCoreMotionCreatesMotionManagers`: no line under `Carodo/`
  outside `Carodo/Core/Motion/` contains `CMAltimeter(`, `CMMotionActivityManager(`,
  `CMMotionManager(` or `CMPedometer(`. Expected: PASS at once; prove it can fail by adding
  `_ = CMAltimeter()` to a file in `Core/Recording`, seeing it fail, removing it.
- [ ] **Step 6: `DemoRoute.bearing`** becomes one call to
  `Geo.bearing(latitude:longitude:toLatitude:toLongitude:)`.
- [ ] **Step 7: Run** `ArchitectureTests` and `FeedInviteDriveTests`. Expected: PASS.

### Task 3: Slice A's docs, checks and commit

**Files:** `docs/architecture.md`, `docs/tracking.md`, `AGENTS.md` (carodo-ios).

- [ ] **Step 1: `docs/architecture.md`.** A new section "Sensors: one owner each": the rule (one
  folder creates, the composition root owns, a protocol and a fake each, held by
  `ArchitectureTests`) and a table with one row per sensor: recording GPS, the background hold,
  standby (significant changes, parking circle, place regions), detection GPS, permission, compass,
  altimeter, motion activity. Columns: type and file, owner, turned on by, turned off by, runs in
  the background. The audit's section 5 is the source; every cell is checked against the code. Rows
  slice B changes (compass, current position) are written as they are today. Update the folder tree
  and any path naming a moved file.
- [ ] **Step 2: `docs/tracking.md`.** Headings and paths that name moved files; "Core Location
  notes" links to the new section.
- [ ] **Step 3: `AGENTS.md`.** The Architecture tree (`Location/` = sensors, `MapLookup/`), and a
  recipe "A sensor or a system manager": create it in `Core/Location` or `Core/Motion` behind a
  protocol with a fake, own it in `DependencyContainer`, add its row to the docs table.
- [ ] **Step 4: Checks.** `task format`, `task lint`, `task warnings`, `task test`. Expected: lint
  clean, no warning, tests pass with the baseline's count plus the new ones.
- [ ] **Step 5: The Feed's invite on the simulator** (DEBUG launch arguments,
  `docs/operations/setup.md#qa-launch-arguments-debug`: sample data, the Feed tab): a screenshot in
  Light, kept in the scratchpad. It shows the invite with its shape as before.
- [ ] **Step 6: Commit slice A.** `git add` each path; `git diff --cached --stat` lists only this
  work's files.

```bash
git commit -m "refactor(location): sensors in one folder, map lookups in their own, isolation rule held by a test"
```

---

## Slice B: behaviour (uncommitted until the owner's field review)

Before Task 4: build slice A's commit on the simulator and record the **before** drive of Task 8,
Step 2. It is the baseline the after-run is compared with.

### Task 4: The compass (F2)

**Files:**
- Create: `Carodo/Core/Location/HeadingSource.swift`
- Modify: `Carodo/Core/Location/CompassHeading.swift`, `Carodo/App/DependencyContainer.swift`,
  `Carodo/App/MainTabView.swift` (about line 171), `Carodo/Features/Map/Views/MapAtlasView.swift`
  (line 43 and its init), `Carodo/Features/Map/Views/AtlasLocationMarkers.swift` (the preview)
- Test: `CarodoTests/CompassHeadingTests.swift`

**Interfaces:**
- Produces:
  - `protocol HeadingSource: AnyObject { func headings() -> AsyncStream<CLLocationDirection> }`
  - `final class NoHeading: HeadingSource` (a stream that finishes at once)
  - `protocol CompassControlling: AnyObject { func startUpdatingHeading(); func stopUpdatingHeading() }`,
    `extension CLLocationManager: CompassControlling {}`
  - `CompassHeading.init(compass: any CompassControlling = CLLocationManager())`,
    `private(set) var isRunning: Bool`, `func receive(_ degrees: CLLocationDirection)` (the
    delegate callback forwards to it)
  - `DependencyContainer.headingSource: any HeadingSource` (default `NoHeading()`, live
    `CompassHeading()`); `MapAtlasView(…, compass: any HeadingSource)`.

- [ ] **Step 1: Write the failing tests** on a counting fake `CompassControlling` (`starts`,
  `stops`):
  - `testANewStreamSurvivesTheOldOnesStop`: take a stream, end it (cancel the task consuming it),
    take a second stream **before yielding**, then let the main actor run
    (`await Task.yield()` until the old stream's stop has had its turn). Assert `isRunning`, and
    that `receive(90)` reaches the second stream. (Review Focus 4.)
  - `testASecondStreamEndsTheFirst`: two `headings()` in a row; the first stream finishes; the
    compass was started once and not stopped.
  - `testTheLastStreamEndingStopsTheCompass`: after the only stream ends and the main actor runs,
    `isRunning == false` and `starts == stops`.
  - `testAHeadingWithNoStreamIsDropped`: `receive(10)` with no stream does nothing.
- [ ] **Step 2: Run.** `-only-testing:CarodoTests/CompassHeadingTests`. Expected: build error (no
  `init(compass:)`); with the seam added first and nothing else, the first test FAILS.
- [ ] **Step 3: Implement.** Each `headings()` call takes the next token (an `Int`), finishes the
  previous continuation, starts the compass if not running. A stream's termination hops to the
  main actor and stops the compass and clears the continuation **only if its token is still the
  current one**. `headingFilter = 4` and the accuracy guard stay; the delegate is set only when the
  injected compass is a `CLLocationManager`.
- [ ] **Step 4: Wire.** The container owns it; `MainTabView` passes `container.headingSource`;
  `MapAtlasView`'s `@State private var compass = CompassHeading()` goes; the preview passes
  `NoHeading()`. `.task(id: followMode == .heading)` is unchanged.
- [ ] **Step 5: Run** the four tests and `task build`. Expected: PASS.

### Task 5: One "where the phone is now" (F4), and rules R1 and R3

**Files:**
- Create: `Carodo/Core/Location/CurrentPosition.swift`, `Carodo/Core/Location/CoreCurrentPosition.swift`
- Modify: `Carodo/Core/MapLookup/MapKitStationFinder.swift`, `Carodo/Core/Location/LocationPermissionManager.swift`
  (remove `lastKnownCoordinate`), `Carodo/Features/Map/Views/MapAtlasView.swift` (about line 647),
  `Carodo/App/DependencyContainer.swift`, `Carodo/App/MainTabView.swift`, the Map preview
- Test: `CarodoTests/CurrentPositionTests.swift`, `CarodoTests/ArchitectureTests.swift`

**Interfaces:**
- Produces:
  - `protocol CurrentPositionProviding: AnyObject, Sendable { var lastKnown: LocationSample? { get }; func current(maxAgeS: TimeInterval, maxAccuracyM: Double, timeout: Duration) async -> LocationSample? }`
  - `nonisolated enum CurrentPositionChoice: Equatable { case use(LocationSample), request, unavailable }`
    with `static func pick(isAuthorized: Bool, driveFix: LocationSample?, cached: LocationSample?, now: Date, maxAgeS: TimeInterval, maxAccuracyM: Double) -> CurrentPositionChoice`
  - `final class NoCurrentPosition: CurrentPositionProviding` (nil for both)
  - `final class CoreCurrentPosition: NSObject, CurrentPositionProviding` with
    `var driveFix: (() -> LocationSample?)?`
  - `MapKitStationFinder(position: any CurrentPositionProviding)`;
    `DependencyContainer.currentPosition: any CurrentPositionProviding` (default
    `NoCurrentPosition()`); `MapAtlasView(…, position: any CurrentPositionProviding)`.

- [ ] **Step 1: Write the failing tests.** Synthetic samples around a fixed `now`.
  `CurrentPositionChoice.pick` with `maxAgeS: 120`, `maxAccuracyM: 100`:
  - not authorized, any fixes → `.unavailable`;
  - a drive fix 5 s old, 10 m → `.use(driveFix)`, even with a cached fix present;
  - a drive fix 121 s old (a paused drive), a cached fix 30 s old, 20 m → `.use(cached)`
    (Review Focus 3); the same drive fix at 119 s → `.use(driveFix)`;
  - a drive fix 5 s old but 101 m, no cached → `.request`; at 100 m → `.use` (Review Focus 2);
  - a fix with negative accuracy (iOS's "invalid") is never used;
  - no fix at all, authorized → `.request`.
  And `testTheDefaultContainerTouchesNoSensor`: `DependencyContainer()` holds a `NoHeading` and a
  `NoCurrentPosition` (Review Focus 5).
- [ ] **Step 2: Write R1 and R3, failing.** In `ArchitectureTests`:
  - `testOnlyCoreLocationCreatesLocationManagers` (R1): no line under `Carodo/` outside
    `Carodo/Core/Location/` contains `CLLocationManager(`, `CLBackgroundActivitySession(`,
    `CLLocationUpdate.` or `CLMonitor(`. Comment lines (`//`) are skipped.
  - `testOnlyTheCompositionRootCreatesASensor` (R3): `CoreLocationSource(`,
    `CoreLocationServices(`, `CompassHeading(`, `CoreCurrentPosition(`, `CoreMotionActivity(`,
    `Barometer(` appear under `Carodo/` only in `App/DependencyContainer.swift` (and each type's
    own file). The two permission managers are not on the list (spec, section 6).
  Run. Expected: R1 FAILS naming `MapKitStationFinder.swift` (twice: the manager and
  `liveUpdates`); R3 passes if Task 4 is done. A guard that cannot fail guards nothing: this
  failing run is recorded in the report.
- [ ] **Step 3: Implement `pick`**, then `CoreCurrentPosition`: its own `CLLocationManager`;
  `lastKnown` is the manager's `location` as a `LocationSample` (no age check, as the Map's marker
  reads today); `current` calls `pick` with `driveFix?()` and the cached fix, and on `.request`
  runs **today's loop from `MapKitStationFinder.currentLocation()` moved here unchanged**: the
  first `CLLocationUpdate.liveUpdates()` fix within `maxAccuracyM`, raced against `timeout` in a
  task group, the loser cancelled. It never asks for permission. A doc comment says: foreground
  only (a sheet, a marker), never on the tracking path.
- [ ] **Step 4: `MapKitStationFinder`** takes `position`, calls
  `current(maxAgeS: 120, maxAccuracyM: 100, timeout: fixTimeout)` and loses `currentLocation()` and
  its manager. Distances use a `CLLocation` built from the sample. `radiusM`, `limit` and
  `fixTimeout` (8 s) stay.
- [ ] **Step 5: Wire.** The live factory creates one `CoreCurrentPosition`, passes it to
  `MapKitStationFinder(position:)` and the container, and after the container exists sets
  `driveFix = { [weak session] in session?.lastFix }`. `MapAtlasView` reads `position.lastKnown`
  where it read `location.lastKnownCoordinate`; `LocationPermissionManager.lastKnownCoordinate` is
  deleted.
- [ ] **Step 6: Run** `CurrentPositionTests`, `ArchitectureTests`, `FuelLogTests`. Expected: PASS.

### Task 6: One projection (F3 for `GapHealing`) and rule R5

**Files:**
- Modify: `Carodo/Core/Recording/GapHealing.swift` (`closest`, about line 234)
- Test: `CarodoTests/ArchitectureTests.swift`; `CarodoTests/GapHealingTests.swift` unchanged

- [ ] **Step 1: Write R5, failing.** `testOneFlatProjection`: no line under `Carodo/` outside
  `Core/Domain/Geo.swift` and `Core/PreviewData/` contains a metres-per-degree literal (`111_` or
  `110_574`). Expected: FAIL naming `GapHealing.swift`. Any other hit is read: a projection is
  switched to `LocalProjection`; anything that is not one is reported, not silenced.
- [ ] **Step 2: Rewrite `closest`** on a `LocalProjection` whose origin is the fix: `a` and `b`
  through `xy(latitude:longitude:)`, the fix at the origin, the clamped fraction as the dot product
  it is today, the distance from the same points. Signature and return type unchanged.
- [ ] **Step 3: Run** `GapHealingTests` and `ArchitectureTests`. Expected: PASS with no test
  edited. If a `GapHealingTests` accuracy fails, stop: the 0.1 % move was expected to sit inside
  every accuracy, and a failure is a finding for the owner, not a tolerance to widen.
- [ ] **Step 4: `task replay` and `task showcase`**, `diff` against Task 1's baselines. Expected:
  identical, or a lead-in distance differing by at most about 0.1 %; every differing line is
  listed in the report with both values.

### Task 7: On/off tightening (spec 5.4)

**Files:** `Carodo/Core/Motion/MotionActivity.swift`, `Carodo/Core/Location/LocationSource.swift`
(comments), `Carodo/Core/Location/CoreLocationServices.swift`, possibly
`Carodo/Core/Recording/DriveSessionManager.swift`. Test: `CarodoTests/SensorLifecycleTests.swift`.

Each row of the spec's table is first confirmed by reading its callers; the outcome below is the
decision when the reading agrees. One that reads differently is reported, not forced.

- [ ] **Step 1: Write `SensorLifecycleTests`** on `DriveSessionManager` with `ManualLocationSource`
  and a counting `MotionActivityFollowing` fake (the one in `RecordingGPSTests`, moved to a shared
  test helper if it is private):
  - `testEveryWayADriveEndsStopsTheGPSAndReleasesTheHold`: for each way a drive ends that the
    session exposes (finish by hand, discard, auto-finish, an end at recovery; found by reading the
    callers of `source.stopUpdates()` and `source.endDrive()`, lines 612, 925, 941 at `b143467`):
    afterwards `isRunning == false` and `endDriveCount == 1`.
  - `testAPauseStopsTheGPSAndKeepsTheHold`: after pause, `isRunning == false`, `endDriveCount == 0`;
    after resume, running again with one more start.
  - `testMotionFollowingIsBalanced`: through lower GPS at a stop → raise → lower → end, the fake's
    `follow` and `stopFollowing` alternate, never two `follow`s in a row, and it is stopped at the
    end.
  Run. Expected: PASS if the session is already tight. **A failure is a real bug found**: fix it
  in `DriveSessionManager` inside this task, and give its root cause in the report.
- [ ] **Step 2: `CoreMotionActivity.follow`.** Store the handler in a property the update closure
  reads through `[weak self]`; a second `follow` while following replaces the handler and starts
  nothing; `stopFollowing` clears it. The protocol's comment says so.
- [ ] **Step 3: `LocationSource`'s comments** state the contract the tests now hold: a second
  `startUpdates` replaces the handler; `stopUpdates` is safe to repeat; `endDrive` after
  `stopUpdates` ends a drive, a pause calls `stopUpdates` alone.
- [ ] **Step 4: `CoreLocationServices.didFailWithError`** logs which manager failed ("Detection GPS
  failed" when `manager === detector`, else "Standby location failed"); no coordinate, no error
  text with a position. `anchorWhenLocated` stays set after a failed request (the next delivery
  still places the circle: the documented fallback); a comment says so.
- [ ] **Step 5: Read, no code expected.** (a) `Barometer`: it re-applies when the recording state
  changes, not when Motion access changes mid-drive; write that as its row's note in the docs
  table. (b) A location permission revoked mid-drive: confirm by reading
  `LocationPermissionManager.onStatusChange`'s wiring that the tracking log records it; if it does
  not, stop and ask (a new log line is a field to classify).
- [ ] **Step 6: Run** `SensorLifecycleTests`, `RecordingGPSTests`, `DriveSessionManagerTests`,
  `CoreLocationServicesTests`, `TrackingModeTests`. Expected: PASS.

### Task 8: Docs, simulator before and after, field-test script, report

**Files:** `carodo-ios/docs/architecture.md`, `docs/tracking.md`, `docs/specs/` where a station
list or the Map's marker is described; in the handbook `field-tests/YYYY-MM-DD-location-runtime.md`,
`plans/technical-debt.md`, `plans/backlog.md`, this plan's and the spec's status lines, the audit's
status line.

- [ ] **Step 1: Docs.** The sensors table gets its slice B rows: compass (owner: the container;
  on: the Map's heading follow; off: its stream ending, token-guarded) and current position (on: a
  foreground request with no fresh fix; off: its answer or its timeout). The fuel spec says the
  station list uses the recording drive's fix when one is open. The parking circle's own
  "current location" is named as a different question, kept.
- [ ] **Step 2: Full checks.** `task format`, `task lint`, `task warnings`, `task test`,
  `task replay`, `task showcase`. Expected: clean; the replays as Task 6 found them.
- [ ] **Step 3: Simulator, before and after.** A simulator of this session's own, by UDID
  (`SIM_ID` in `.env`). The **before** run is on slice A's commit (taken before Task 4), the
  **after** run on the finished tree, both the same way:
  `xcrun simctl openurl "$SIM_ID" carodo://trip/start`, then from the handbook
  `python3 showcase/sim_drive.py prenn --udid "$SIM_ID"`, until the drive ends by itself. During
  the after run also: Map → heading follow on, switch tab and back, follow off and on (the map
  keeps turning); open "Log fuel" while recording (stations listed).
  Compare from each run's database and tracking log (`task drives DB=…`, `task events DB=…`):
  points, distance and durations equal within the simulator's own run-to-run noise (state the
  numbers); start, hold, stop and end events once each, in the same order; in the after run, no
  second location start around the fuel sheet. A difference is explained, never tuned away.
  A simulated route proves plumbing only.
- [ ] **Step 4: Screenshots** of the screens touched (the Map in heading follow, the fill-up
  sheet's station list): Light and Dark, xxxLarge, Vietnamese; kept in the scratchpad.
- [ ] **Step 5: Write the field-test script** from `field-tests/_template.md` (phone first, at most
  about ten steps, each with its moment; no place names): parked: build installed, Auto Mode on;
  a manual drive with a pause and a Resume from the Lock Screen; a fill-up logged at a stop
  mid-drive; heading follow at a stop, tab switched and back; an Auto Mode start from parked;
  after parking: both drives in Journeys. **Logs** steps name the evidence to read after
  `task ios:pull-db`: `hold=` lines, one start and one end per drive, no location start beside the
  fuel entry's time, the detection window's events.
- [ ] **Step 6: Record what is open.** In `plans/technical-debt.md`: a PV row "Location runtime on
  an iPhone" (what the simulator showed, what only the drive shows); rows for anything left from
  Task 7. In `plans/backlog.md`: the spec's section 10 (map lookups with TD-43, the `UserDefaults`
  and power-state audit, I1, I2, `CarodoTests` in folders). Status lines updated.
- [ ] **Step 7: Report, no commit.** The completion report of `AGENT_WORKFLOW.md`, ending
  "slice B: waiting for the owner's review": behaviour changed (compass handover, station list on
  the drive's fix, lead-in distances by up to about 0.1 %, the log text of a location failure),
  test evidence from Step 2, the simulator's figures, bugs found in Task 7 with root causes, the
  field-test file to drive. After the owner accepts the field review, slice B is one commit:

```bash
git commit -m "fix(location): one source for the current position, a compass that survives its handover, sensor rules held by tests"
```

  and the branch is merged into `main` by the owner's word.

---

## Decisions made in this plan (the spec left them to the builder)

- The one-shot fix keeps `CLLocationUpdate.liveUpdates()`, moved unchanged into
  `CoreCurrentPosition`: the least behaviour change; it runs in the foreground only, where
  `liveUpdates` is not suspended.
- The order "drive's fix, cached fix, request" is a pure function (`CurrentPositionChoice.pick`)
  with `now` injected, so it is tested without Core Location.
- The compass's seam is the two calls it makes (`CompassControlling`), not a wrapper of
  `CLLocationManager`.
- `TravelHeading` moves to `Core/Tracking`.
- The Map's first marker keeps reading the cached fix with no age check.
- `latestCarDrive` is not given the lighter read (the audit's option b): it would be a new
  repository query.
- `Barometer` gets a documented note, no code.

## Not in this plan

A before/after Instruments measurement of F1 (the fix is claimed as isolation, not as a speed-up);
the inside of `Core/MapLookup`; any threshold; `CarodoTests` in folders.
