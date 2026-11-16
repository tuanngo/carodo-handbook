# Map lookups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every request to Apple Maps' services is created in `Core/MapLookup`, behind a protocol
with a fake, by the composition root, and two source-reading tests keep it so; TD-45's two location
adapters get a counting seam and the one-shot fix a tracking-log line.

**Architecture:** One new seam, `MapSnapshotting`, takes both `MKMapSnapshotter`s out of
`Core/Journal`; `JourneyMapSnapshotService.shared` becomes the container's `mapImages`; the
onboarding film asks the container's `GapRouter`. `CoreCurrentPosition` and `CoreMotionActivity`
take their system calls through small protocols, as `CompassHeading` does (`CompassControlling`).
Rules R7 and R8 join `ArchitectureTests`.

**Tech Stack:** Swift 6.2 (main actor by default, `@concurrent` to leave it), MapKit, Core
Location, Core Motion, XCTest, XcodeGen, `task` shortcuts.

**Spec:** [`map-lookups.md`](map-lookups.md) (approved 2026-11-17 with D1, D2, Q1). Read it first,
then `carodo-ios/AGENTS.md`. The pattern it follows: [`location-runtime.md`](location-runtime.md)
and [`location-runtime-plan.md`](location-runtime-plan.md).

**Status (2026-11-17):** approved by the owner and executed inline the same day.

**Done (2026-11-17):** on `refactor/map-lookups` in `../carodo-ios-map-lookups`: `1cc3247` (Tasks
1–6), `c8ae877` (Task 7, the `position` line), `b70e2b4` (the final review's fix: R8 also holds
`POINameCache(`, `MapDataCache(` and `MapKitPOISearch.pointsOfInterest(`); merged into `main` by the owner's choice in carodo-ios `853f28e` (2,445 tests green on the merged result), not pushed.
Checks: lint clean, no warnings, 2,445 unit tests (23 skipped); R7 and R8 each seen failing on a
planted violation; before/after screenshots identical but for the status-bar clock and a few
antialiased pixels. Rulings: Day screenshot skipped (same backdrop as Explore); `render`
`@concurrent` (keeps the Footprint's drawing off the main actor); Tasks 3 and 4 in one pass; two
`privacy.md` rows (onboarding directions, map tiles, both undocumented before). Deferred minors
from the final review: the share card's ground trusts `lines.first`; R8's own-file match by name;
`CoreMotionActivity.deliver` is a test seam, the Core Motion callback itself untested; the
Footprint's projected lines held whole before thinning; the `position` line's time read inside its
`Task`. Device check: PV-26 (the `position` line on a drive with a fill-up).

## Global Constraints

- Repo `carodo-ios`, base `3a11d86`. Work in a worktree:
  `git worktree add ../carodo-ios-map-lookups -b refactor/map-lookups`, then `xcodegen generate`
  there. Before editing a file named below, `git log -1 -- <file>`; a file changed since `3a11d86` is
  re-read, never overwritten.
- **No image changes** (anti-goal 1): every `MKMapSnapshotter.Options` value, both label shrinks
  (`JourneyMapSnapshotService` 1.8, `ShareCardRenderer` 1.5), the queue
  (`.global(qos: .userInitiated)`), the service's three-at-a-time limit, its cache version (`7`) and
  key stay as they are.
- **No lookup's inside changes:** caches, budgets, TTLs, `isActive`, `enrichJourneys`.
- No schema, API, permission, entitlement, background mode, dependency or target change (P6). The
  one new persisted value is the tracking log's `position` kind (Task 7), an added raw value.
- No coordinate, accuracy value or place name in a log line (P5).
- Protocols are not moved: `GapRouter` stays in `Core/Recording/GapHealing.swift`, `POISearching`
  and `NearbyStationFinding` in `Core/Domain`.
- Every new main-actor class declares `nonisolated deinit {}`. No `!`, `try!`, `Task.detached`,
  `DispatchQueue`, `@unchecked Sendable`.
- Commits: two, lowercase conventional, no AI attribution (P8): Task 6 and Task 7. Stage own paths
  only. Not pushed, not merged without the owner.

## Review Focus

1. **Offline or MapKit fails:** the Footprint and backdrops show no image and no stale one; the
   share card is made on its plain ground with the route in the same place. Pinned in Task 3.
2. **Erase while a map image is being made:** the image is never written back after the erase.
   The existing erase test stays and runs on the fake snapshotter (Task 3).
3. **A Footprint with an empty line or a one-point line among others:** lines are never joined and
   the count is kept through projection. Pinned in Task 3 (`MapSnapshot.project`).
4. **A second `follow` while following, or `follow` before Motion access:** no second start, the
   new handler wins, nothing starts without access. Pinned in Task 2.
5. **Log fuel with no permission, or no fix in time:** the line says `answer=none`, and no request
   starts without permission. Pinned in Tasks 1 and 7.

---

## File map

| File | Change | Task |
|---|---|---|
| `Carodo/Core/Location/CurrentPosition.swift` | `PositionControlling` protocol + `CLLocationManager` conformance | 1 |
| `Carodo/Core/Location/CoreCurrentPosition.swift` | takes `PositionControlling` and a `Request` closure; `onAnswer` hook | 1, 7 |
| `CarodoTests/CoreCurrentPositionTests.swift` | new | 1, 7 |
| `Carodo/Core/Motion/MotionActivity.swift` | `ActivityControlling` protocol + conformance; `CoreMotionActivity` takes it | 2 |
| `CarodoTests/CoreMotionActivityTests.swift` | new | 2 |
| `Carodo/Core/MapLookup/MapSnapshotting.swift` | new: request, snapshot, protocol, `NoMapSnapshot` | 3 |
| `Carodo/Core/MapLookup/AppleMapSnapshotter.swift` | new: the live adapter | 3 |
| `Carodo/Core/Journal/JourneyMapSnapshotService.swift` | takes `any MapSnapshotting`; `snapshot` and `.shared` go | 3, 4 |
| `Carodo/Core/Journal/ShareCardRenderer.swift` | `ground` takes `any MapSnapshotting` | 3 |
| `Carodo/Features/Journeys/ViewModels/Share/ShareCardModel.swift` | `makeGround` has no default | 3 |
| `CarodoTests/MapSnapshotTests.swift` | new | 3 |
| `CarodoTests/JourneyMapSnapshotServiceTests.swift`, `ShareCardModelTests.swift`, `ShareCardRendererTests.swift` | on the fake | 3 |
| `Carodo/App/DependencyContainer.swift` | `mapSnapshotter`, `mapImages`, the `\.mapImages` key, erase path, `onAnswer` wiring | 4, 7 |
| `Carodo/App/CarodoApp.swift:106` | `.environment(\.mapImages, …)` | 4 |
| `Carodo/DesignSystem/Components/JourneyMapBackdrop.swift`, `Carodo/Features/Passport/Views/PassportExplorationSection.swift` | read `\.mapImages` | 4 |
| `Carodo/Features/Journeys/Views/Detail/JourneyDetailView.swift` | builds `makeGround` from the container | 4 |
| `Carodo/Features/Onboarding/Map/JourneyMapLayer.swift`, `Views/OnboardingView.swift` | the demo road through `GapRouter` | 5 |
| `Carodo/Core/Recording/GapHealing.swift` | `GapRouter`'s doc comment only | 5 |
| `CarodoTests/ArchitectureTests.swift` | R7, R8, roots parameter | 6 |
| `Carodo/Core/Diagnostics/TrackingLog.swift`, `DiagnosticsLogFormat.swift` | `position` kind and entry, keys | 7 |
| `docs/architecture.md`, `AGENTS.md`, `docs/tracking.md`, `docs/privacy.md` (check) | Task 6, 7 | 6, 7 |

---

### Task 0: Worktree and the "before" screenshots

- [ ] **Step 1:** Create the worktree (Global Constraints), `xcodegen generate`, `task build`.
- [ ] **Step 2:** On a simulator of your own (UDID by `-destination id=`), with
  `-carodo.sampleData YES` and the DEBUG launch arguments in
  `docs/operations/setup.md#qa-launch-arguments-debug`, take Light and Dark screenshots of: the
  Passport's Footprint, Explore's latest drive (backdrop), a Day page with one drive (backdrop), a
  share card of a sample drive (Focus look), and the onboarding film's map (with the app's live
  container: a fresh install with no sample data, network on). Save them in the session's scratchpad
  as `before-<screen>-<light|dark>.png`. These are synthetic routes; never commit them.

### Task 1: `CoreCurrentPosition` behind a counting seam (TD-45)

**Files:** Modify `Carodo/Core/Location/CurrentPosition.swift`, `CoreCurrentPosition.swift`;
create `CarodoTests/CoreCurrentPositionTests.swift`.

**Interfaces:**
- Produces:
  ```swift
  /// The two reads `CoreCurrentPosition` makes of Core Location, so a test sets them.
  protocol PositionControlling: AnyObject {
      var authorizationStatus: CLAuthorizationStatus { get }
      var location: CLLocation? { get }
  }
  extension CLLocationManager: PositionControlling {}

  final class CoreCurrentPosition {
      typealias Request = @Sendable (_ maxAgeS: TimeInterval, _ maxAccuracyM: Double, _ timeout: Duration) async -> LocationSample?
      init(manager: any PositionControlling = CLLocationManager(), request: @escaping Request = CoreCurrentPosition.liveRequest)
      // today's static `request(maxAgeS:maxAccuracyM:timeout:)`, renamed `liveRequest`, same body
  }
  ```

- [ ] **Step 1: Write the failing tests** (`@MainActor`, a `FakePosition: PositionControlling`
  with settable `authorizationStatus` and `location`, a request closure that counts calls through an
  actor and returns a set fix). Fixes are synthetic (`TripFixtures`), maxAge 120 s, accuracy 100 m:
  - `testAFreshDriveFixAnswersWithNoRequest`: authorized, `driveFix` 10 s old at 5 m → that fix;
    requests == 0.
  - `testAFreshCachedFixAnswersWithNoRequest`: no drive fix, `location` 30 s old at 20 m → it;
    requests == 0.
  - `testStaleFixesMakeExactlyOneRequest`: drive fix 300 s old, cached 300 s old → the request's
    fix; requests == 1.
  - `testNoPermissionAnswersNilWithNoRequest`: `.denied`, fresh drive fix → nil; requests == 0.
  - `testTheDriveFixIsReadAtAskTime`: `driveFix` set after `init` reads the closure's current
    value (the root's wiring, `DependencyContainer.swift:339`).
- [ ] **Step 2:** `task test -- -only-testing:CarodoTests/CoreCurrentPositionTests` → fails to
  compile (`init(manager:request:)` missing).
- [ ] **Step 3:** Add `PositionControlling` beside `CurrentPositionProviding`; `CoreCurrentPosition`
  stores both and calls `request` on `.request`. `lastKnown` reads `manager.location`. Update the
  sensors table's current-position row in `docs/architecture.md` (its two Core Location reads behind
  `PositionControlling`).
- [ ] **Step 4:** The same command → PASS; `CurrentPositionTests` and `SensorLifecycleTests` still
  pass.

### Task 2: `CoreMotionActivity` behind a counting seam (TD-45)

**Files:** Modify `Carodo/Core/Motion/MotionActivity.swift`; create
`CarodoTests/CoreMotionActivityTests.swift`.

**Interfaces:**
- Produces:
  ```swift
  /// The calls `CoreMotionActivity` makes of Core Motion, so a test counts them.
  protocol ActivityControlling: AnyObject {
      func startActivityUpdates(to queue: OperationQueue, withHandler handler: @escaping CMMotionActivityHandler)
      func stopActivityUpdates()
      func queryActivityStarting(from start: Date, to end: Date, to queue: OperationQueue,
                                 withHandler handler: @escaping CMMotionActivityQueryHandler)
  }
  extension CMMotionActivityManager: ActivityControlling {}

  init(manager: any ActivityControlling = CMMotionActivityManager(),
       isAllowed: @escaping () -> Bool = { CMMotionActivityManager.isActivityAvailable()
                                           && CMMotionActivityManager.authorizationStatus() == .authorized })
  ```
  Both of today's guards read `isAllowed()`.

  The start handler maps the activity with `static func reading(_ activity: CMMotionActivity) ->
  RecentActivity.Reading` (today's mapping, shared with the query) and hands it to
  `func deliver(_ reading: RecentActivity.Reading)` (internal), which calls the current handler. A
  test never builds a `CMMotionActivity` (its default init has no start date): it calls `deliver`.

- [ ] **Step 1: Write the failing tests** (a `CountingActivity: ActivityControlling` keeping
  `starts`, `stops` and `queries`):
  - `testASecondFollowReplacesTheHandlerAndStartsNothing`: follow(a), follow(b) → starts == 1; a
    delivered reading reaches b only.
  - `testStopStopsOnceAndASecondStopDoesNothing`: follow, stop, stop → stops == 1.
  - `testNoFollowWithoutAccess`: `isAllowed` false → follow starts nothing; then true → follow
    starts once.
  - `testAQueryWithoutAccessAsksNothing`: `readings(from:to:)` with `isAllowed` false → nil; no
    query.
- [ ] **Step 2:** Run `-only-testing:CarodoTests/CoreMotionActivityTests` → compile failure.
- [ ] **Step 3:** Implement; the motion row of `docs/architecture.md`'s sensors table names
  `ActivityControlling`.
- [ ] **Step 4:** Run → PASS; `SensorLifecycleTests` still passes.

### Task 3: `MapSnapshotting` and both snapshot callers on it

**Files:** Create `Carodo/Core/MapLookup/MapSnapshotting.swift`, `AppleMapSnapshotter.swift`,
`CarodoTests/MapSnapshotTests.swift`; modify `JourneyMapSnapshotService.swift`,
`ShareCardRenderer.swift`, `ShareCardModel.swift` and the three test files in the file map.

**Interfaces:**
- Produces (in `MapSnapshotting.swift`, all `nonisolated`):
  ```swift
  struct MapSnapshotRequest: Sendable {
      enum Area: Sendable { case region(MKCoordinateRegion), mapRect(MKMapRect) }
      enum Look: Sendable { case muted, journey }
      let area: Area; let size: CGSize; let scale: CGFloat; let isDark: Bool; let look: Look
      let lines: [[CLLocationCoordinate2D]]
  }
  struct MapSnapshot: Sendable {
      let image: UIImage
      let lines: [[CGPoint]]   // in the snapshot's points (before any label shrink is undone)
      /// Every line projected, one for one, empty lines kept empty.
      static func project(_ lines: [[CLLocationCoordinate2D]], by point: (CLLocationCoordinate2D) -> CGPoint) -> [[CGPoint]]
  }
  protocol MapSnapshotting: Sendable {
      func snapshot(_ request: MapSnapshotRequest) async -> MapSnapshot?
  }
  struct NoMapSnapshot: MapSnapshotting   // always nil
  ```
  `AppleMapSnapshotter: MapSnapshotting` (a `nonisolated struct`): `.muted` is
  `MKStandardMapConfiguration(elevationStyle: .flat, emphasisStyle: .muted)` with
  `pointOfInterestFilter = .excludingAll`; `.journey` is `CarodoMapLook.standard(isDark:is3D: false)`;
  `traitCollection` from `isDark`; started on `.global(qos: .userInitiated)`; lines projected with
  `snapshot.point(for:)` inside the completion.
- `JourneyMapSnapshotService.init(directory: URL?, snapshotter: any MapSnapshotting)`; the `Render`
  typealias and closure go. Its private render builds the request (today's region, size × 1.8,
  scale ÷ 1.8, `.muted`, `request.lines`) and `draw(_:on:)` takes a `MapSnapshot` (divides points by
  1.8, as `screen` does today).
- `ShareCardRenderer.ground(for: Request, withMap: Bool, using snapshotter: any MapSnapshotting) async -> Ground`
  (`.mapRect(rect)`, size × 1.5, `ShareCard.scale` ÷ 1.5, `.journey`, `lines: [request.route]`).
- `ShareCardModel.init(…, makeGround: @escaping MakeGround, …)` with no default.

- [ ] **Step 1: Write the failing tests**
  - `MapSnapshotTests.testProjectKeepsEveryLineAndItsLength`: lines `[[a, b], [], [c]]` with
    `point = { CGPoint(x: $0.longitude, y: $0.latitude) }` → three lines of 2, 0 and 1 points, in
    order.
  - `MapSnapshotTests.testNoMapSnapshotAnswersNil`.
  - `ShareCardRendererTests.testOfflineGroundIsPlainWithTheRouteInPlace`: `ground(for:withMap: true,
    using: NoMapSnapshot())` → `image == nil` and `line` equals `ground(…withMap: false…)`'s.
  - `JourneyMapSnapshotServiceTests`: replace each `render` closure with a `GatedSnapshotter:
    MapSnapshotting` that does what the closure did (enter the gate, return
    `MapSnapshot(image: UIImage(), lines: request.lines.map { _ in [] })`). Assertions unchanged,
    including erase. Add `testNoSnapshotGivesNoImage` (with `NoMapSnapshot`, `image(for:)` → nil and
    nothing cached in memory).
  - `ShareCardModelTests`: its `makeGround` calls `ground(for:withMap: false, using: NoMapSnapshot())`.
- [ ] **Step 2:** Run the four test classes → compile failure.
- [ ] **Step 3:** Implement. Move R4's allow-list entry `"JourneyMapSnapshotService.swift: snapshot"`
  to the adapter's function if it is `nonisolated async` without `@concurrent`, with the same reason
  line; remove it otherwise.
- [ ] **Step 4:** Run → PASS; `task test` all green (callers of `.shared` still compile: `.shared`
  goes in Task 4, so give it `snapshotter: AppleMapSnapshotter()` for now).

### Task 4: One owner for the map images

**Files:** `DependencyContainer.swift`, `CarodoApp.swift`, `JourneyMapBackdrop.swift`,
`PassportExplorationSection.swift`, `JourneyDetailView.swift`, `JourneyMapSnapshotService.swift`.

**Interfaces:**
- Consumes: Task 3's `init(directory:snapshotter:)`, `AppleMapSnapshotter`, `ground(for:withMap:using:)`.
- Produces: on `DependencyContainer`, `let mapSnapshotter: any MapSnapshotting` and
  `let mapImages: JourneyMapSnapshotService`; `EnvironmentValues.mapImages:
  JourneyMapSnapshotService` with a hand-written key beside `DependencyContainerKey` (same reason:
  `@Entry` would build a service on every read), default
  `JourneyMapSnapshotService(directory: nil, snapshotter: NoMapSnapshot())`.

- [ ] **Step 1:** `DependencyContainer.init` takes `mapSnapshotter: any MapSnapshotting =
  AppleMapSnapshotter()` and `mapImageFolder: URL? = nil`, and builds `mapImages` from them. Only
  the app's live container (`DependencyContainer.swift` around line 312) passes
  `JourneyMapSnapshotService.defaultDirectory()`; sample, showcase, `unsaved` and preview
  containers keep `nil` (spec 4.3).
- [ ] **Step 2:** Lines 957 and 967 use `mapImages`. `static let shared` is deleted.
- [ ] **Step 3:** `CarodoApp.swift:106` adds `.environment(\.mapImages, container.mapImages)`.
  `JourneyMapBackdrop` and `PassportFootprintImage` read `@Environment(\.mapImages)`.
- [ ] **Step 4:** `JourneyDetailView` reads `@Environment(\.dependencyContainer)` and passes
  `makeGround: { [snapshotter = container.mapSnapshotter] in await ShareCardRenderer.ground(for: $0,
  withMap: $1, using: snapshotter) }`.
- [ ] **Step 5:** `task build`, then `task test` → green; `grep -rn "JourneyMapSnapshotService.shared" Carodo` → nothing.

### Task 5: The onboarding film's road through `GapRouter`

**Files:** `JourneyMapLayer.swift`, `OnboardingView.swift`, `GapHealing.swift` (comment).

- [ ] **Step 1:** `JourneyMapLayer` gains `let router: (any GapRouter)?`, handed to its
  `Coordinator`; `OnboardingView` passes `container.gapRouter`.
- [ ] **Step 2:** `loadRoute()` asks `router?.route(from: DemoRoute.start, to: DemoRoute.end)` (as
  `(latitude, longitude)` tuples; driving), builds `MKPolyline(coordinates:count:)` from the answer's
  coordinates and calls `install(_:)`. No router, a thrown error or nil: return, as today's
  `try?`/`guard` does (the film draws its own line). Capture `[weak self]`; the `Task` stays as it is.
- [ ] **Step 3:** `GapRouter`'s comment: "Apple's road between two points, behind a boundary
  (docs/privacy.md: only the two points go to Apple): a GPS gap, a lead-in, the onboarding film's
  demo road."
- [ ] **Step 4:** `task build`; `grep -rn "MKDirections(" Carodo` → only `Core/MapLookup/AppleMapsGapRouter.swift`.

### Task 6: Rules R7 and R8, docs, checks, screenshots, first commit

**Files:** `CarodoTests/ArchitectureTests.swift`, `docs/architecture.md`, `AGENTS.md`,
`docs/privacy.md` (check only).

- [ ] **Step 1: Write the rules** (exact needles from spec section 5):
  - `lines(containing:outside:)` gains `in roots: [String] = ["Carodo"]` and prefixes paths as
    today. R1 (`testOnlyCoreLocationCreatesLocationManagers`) and R2 pass
    `["Carodo", "CarodoShared", "CarodoWidgets"]`.
  - `testOnlyMapLookupAsksAppleMaps` (R7): the eleven request needles outside
    `Carodo/Core/MapLookup/`, the three roots, minus `let allowed: [String] = []` (comment: an
    entry is `"File.swift:line: needle"`'s file and needle with its reason, approved by the owner;
    spec section 5). Message: "ask Apple Maps from Core/MapLookup, behind a protocol with a fake".
  - `testOnlyTheCompositionRootCreatesALookup` (R8): the nine needles, outside
    `Carodo/App/DependencyContainer.swift`, each type's own file exempt as R3 does
    (`PlaceNameCache.swift`, `POINameLookup.swift` for `POINameCache.pointsOfInterest(`,
    `JourneyMapSnapshotService.swift`, …). Message: "DependencyContainer creates the lookup and
    hands it in".
- [ ] **Step 2:** Prove each rule bites: add `_ = CLGeocoder()` to a Feature file, run
  `-only-testing:CarodoTests/ArchitectureTests` → R7 fails naming it; revert. Same for
  `AppleMapsGapRouter()` in a ViewModel → R8 fails; revert.
- [ ] **Step 3: Docs.** `docs/architecture.md`: "Map lookups: one owner each" after the sensors
  section (spec section 6: the table of spec section 3 as it now stands, the "where, not a ban"
  paragraph, and the tripwire note); the tree's `MapLookup/` line ("the only folder that asks Apple
  Maps' services"). `AGENTS.md`: the `MapLookup/` line in the tree and the recipe "A request to Apple
  Maps" (folder, protocol and fake, the container, the cache's budget, active only; an exception is
  an allow-list entry the owner approves). `docs/privacy.md`: if it names where a snapshot or the
  demo road is asked, update the file name; what is sent does not change.
- [ ] **Step 4: Checks.** `task format`, `task lint`, `task warnings`, `task test` → all pass;
  write down the test count.
- [ ] **Step 5: After screenshots.** The same screens, simulator and arguments as Task 0 →
  `after-*.png`; compare each pair (pixel diff, e.g. `compare -metric AE` if ImageMagick is there,
  else side by side). Any difference is explained or fixed, never accepted silently. Onboarding
  with sample data now shows the drawn line (Q1, expected).
- [ ] **Step 6: Commit.** `git add` the files of Tasks 1–6 by path, `git diff --cached --stat`
  shows only them, then:
  `git commit -m "refactor(maplookup): apple maps asked from one folder, the map images owned by the container, two location seams held by tests"`.

### Task 7: The `position` tracking-log line (D2), second commit

**Files:** `TrackingLog.swift`, `DiagnosticsLogFormat.swift`, `CoreCurrentPosition.swift`,
`DependencyContainer.swift`, `docs/tracking.md`, `CarodoTests/CoreCurrentPositionTests.swift`,
`TrackingLogFieldsTests` (if it lists keys).

**Interfaces:**
- Produces:
  ```swift
  nonisolated enum CurrentPositionAnswer: String, Sendable { case drive, cached, request, none }
  // CoreCurrentPosition:
  var onAnswer: ((CurrentPositionAnswer, _ waitS: Int?) -> Void)?   // waitS only for request/none after a request
  // TrackingLogEntry.Kind: case position      (raw value "position", persisted: never renamed)
  static func position(at: Date, answer: CurrentPositionAnswer, waitS: Int?) -> TrackingLogEntry
  // detail: "answer=<raw>" plus " waitS=<n>" when present, whole seconds, rounded down
  ```
- [ ] **Step 1: Failing tests** in `CoreCurrentPositionTests`: each Task 1 case also asserts the one
  `onAnswer` call (`drive`/nil, `cached`/nil, `request`/0 with an instant fake, `none`/nil without
  permission); `testATimedOutRequestAnswersNone` (request returns nil → `none` with a `waitS`). A
  `TrackingLog` test: `.position(at:answer: .request, waitS: 3).detail == "answer=request waitS=3"`.
- [ ] **Step 2:** Run → fails.
- [ ] **Step 3:** Implement; `answer` and `waitS` go in `DiagnosticsLogFormat.sharedKeys` (a
  category and a duration inside one moment). The container wires
  `position.onAnswer = { [trackingLog] answer, wait in Task { await trackingLog.record(.position(at: .now, answer: answer, waitS: wait)) } }`.
  `docs/tracking.md`'s log format gets the line.
- [ ] **Step 4:** `task lint`, `task warnings`, `task test` → pass.
- [ ] **Step 5: Commit** these paths only:
  `git commit -m "feat(diagnostics): a position line says who answered a screen's current position"`.

### Task 8: Handbook and report

- [ ] **Step 1:** `carodo-handbook`: TD-45 closed for the seams, its device half added to PV-26
  (the `position` line read on a drive with a fill-up); TD-46's "only `Carodo/` is scanned" closed
  for R1, R2, R7; the backlog row moved to done; this plan's and the spec's status lines with the
  two hashes.
- [ ] **Step 2:** Report as `AGENTS.md` asks: files, commands and results (test count), the
  screenshot pairs' outcome, the device check still needed (the `position` line on a drive), no
  schema/API/permission/dependency change, the new persisted log kind.

## Decisions made in this plan (the spec left them to the builder)

- `JourneyMapSnapshotService` loses its `Render` closure; its tests use a fake `MapSnapshotting`.
- `\.mapImages` is a hand-written environment key in `DependencyContainer.swift`; its default has no
  folder and no snapshotter, so a preview never writes the cache or asks Apple.
- `CoreMotionActivity` takes an `isAllowed` closure for the two static Core Motion reads.
- R7 and R8 start with empty allow-lists.
- The `position` line is written for `current(…)` only; the Map marker's `lastKnown` read is not a
  request and logs nothing.

## Not in this plan

TD-46's text-matching limits; `MKReverseGeocodingRequest` (iOS 26); moving protocols; the live
maps; TD-43's device check.
