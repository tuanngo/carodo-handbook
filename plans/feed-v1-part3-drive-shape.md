# Feed V1 · Part 3 — the drive shape maker · Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A pure, tested function turns a car drive's route into the contract's `DriveShape`
(0.27.0-draft): trimmed, Home/Work-cut, 48–64 points in the unit box, on its own long axis with a
seeded tilt. No UI, no publishing (Parts 4–5).

**Architecture:** `DriveShape` moves to the contract's form (doubles in 0–1, 8–64 points).
`DriveShapeMaker` (pure enum, `Core/Domain`) runs trim → Home/Work cut → length check → local
metres → principal axis → seeded tilt and mirror → unit box → simplification. Douglas–Peucker is
reused from `RouteSimplifier` by extracting its planar core.

**Tech Stack:** Swift 6, XCTest. No new dependency.

**Spec:** `carodo-handbook/plans/feed-v1-design.md` (Route shape); `carodo-ios/docs/specs/feed.md`
(Route shape); contract `DriveShape`.

## Global Constraints

- Pure and `nonisolated`; no `Date()`, no Core Location services (only `CLLocationCoordinate2D` values).
- Test routes are synthetic (P5): generated lines, arcs and grids, never a real trace.
- Values from the design: trim `max(privacyZone.meters, 300)` along the route; Home/Work radius
  300 m; none under 2,000 m left; 48–64 points (fewer only when the trimmed route has fewer, never
  under 8); tilt within ±15°; mirror 50 %; both seeded by the trip id; unit box keeps aspect ratio.
- `task lint`, `task warnings`, `task test` pass; commit only this plan's paths.

## Review Focus

1. **A start at Home with the route looping back near it:** the Home/Work cut stops at the first
   point outside 300 m, then a later return inside the radius is kept — expected, the design cuts
   ends only. Test `testHomeCutStopsAtTheFirstPointOutsideTheRadius`.
2. **Degenerate routes:** all points equal, two points, a perfectly straight line (zero
   perpendicular spread) must not divide by zero: straight line gives a flat shape at y ≈ 0.5,
   identical points give nil. Tests in Task 2.
3. **Aspect ratio:** a straight drive must not be stretched to fill the height. Test asserts the
   y-extent of a straight line stays under 0.27 (the tilt's rise).
4. **Seed stability across runs:** the seed must come from the UUID bytes, never `hashValue`
   (randomised per process). Test compares against a stored expected first point.
5. **Damaged shapes from the network:** `DriveShape(points:)` refuses NaN, infinities, out-of-box
   values and counts outside 8–64. Tests in Task 1.

---

### Task 1: `DriveShape` in the contract's form

**Files:**
- Modify: `Carodo/Core/Domain/DriveShape.swift`
- Modify: `Carodo/DesignSystem/Components/RouteViews.swift` (`RouteShape(shape:)` scaling 0–1 instead of 0–1000), `Carodo/Core/PreviewData/SampleData.swift` (`sampleShape`: 0–1 doubles, 24–40 points)
- Test: `CarodoTests/DriveShapeTests.swift`, `CarodoTests/RouteShapeTests.swift` (scale)

**Interfaces:**
- Produces: `struct DriveShape { static let pointRange = 8...64; let points: [SIMD2<Double>]; init?(points: [SIMD2<Double>]) }` — every coordinate finite and in `0...1`.

- [ ] **Step 1: Tests** — `testEightToSixtyFourPointsMakeAShape` (7 → nil, 8 and 64 → shape, 65 → nil), `testEveryCoordinateStaysInTheUnitBox` (−0.01, 1.01 → nil), `testNonFiniteValuesAreRefused` (`.nan`, `.infinity` → nil).
- [ ] **Step 2:** Run `-only-testing:CarodoTests/DriveShapeTests` → fails to compile (Int points).
- [ ] **Step 3:** Change the type; fix `RouteShape`, `sampleShape`, `RouteShapeTests`.
- [ ] **Step 4:** Run `DriveShapeTests`, `RouteShapeTests`, `FeedItemPresentationTests`, `SampleDataTests` → pass.

### Task 2: `DriveShapeMaker`

**Files:**
- Modify: `Carodo/Core/Domain/RouteSimplifier.swift` (extract `static func keptIndices(planar: [SIMD2<Double>], tolerance: Double) -> [Int]`; `kept` calls it)
- Create: `Carodo/Core/Domain/DriveShapeMaker.swift`
- Test: `CarodoTests/DriveShapeMakerTests.swift`

**Interfaces:**
- Consumes: `DriveShape(points:)` (Task 1), `PrivacyZone`, `LocalProjection`, `SeededGenerator`.
- Produces:
  ```swift
  nonisolated enum DriveShapeMaker {
      struct Configuration: Sendable { var minimumTrimM = 300.0; var homeWorkRadiusM = 300.0
          var minimumLengthM = 2_000.0; var points = 48...64; var maxTiltDegrees = 15.0 }
      static func shape(route: [CLLocationCoordinate2D], tripID: UUID, privacyZone: PrivacyZone,
                        homeAndWork: [CLLocationCoordinate2D], configuration: Configuration = .init()) -> DriveShape?
      static func trimmed(_ route: [CLLocationCoordinate2D], privacyZone: PrivacyZone,
                          homeAndWork: [CLLocationCoordinate2D], configuration: Configuration = .init()) -> [CLLocationCoordinate2D]
  }
  ```

- [ ] **Step 1: Tests** (synthetic routes built in the test file: a 10 km east–west line at 10.8° N with a point every 25 m; a 10 km north–south line; a winding 12 km sine road; a 2.4 km line):
  - `testTrimsThreeHundredMetresAlongTheRouteAtEachEnd` — zone `.off` and `.m300`: trimmed length = full − 600 m ± 25 m.
  - `testALargerPrivacyZoneTrimsMore` — `.km1`: full − 2,000 m ± 25 m.
  - `testHomeCutStopsAtTheFirstPointOutsideTheRadius` — Home 100 m from the start: the first kept point is > 300 m from Home and the trim is at least 300 m.
  - `testUnderTwoKilometresLeftHasNoShape` — the 2.4 km line → nil.
  - `testALongRouteGivesFortyEightToSixtyFourPointsInTheUnitBox` — winding road: count in 48...64, all in 0...1.
  - `testAStraightDriveLiesNearlyFlat` — north–south line: x-extent ≥ 0.9, y-extent ≤ 0.27 (a ±15° tilt of a unit line rises at most sin 15° ≈ 0.26).
  - `testTheSameTripAlwaysGivesTheSameShape` — two calls, equal; a stored expected first point for one fixed UUID (guards against `hashValue`).
  - `testTwoTripsOfOneRouteDiffer` — two UUIDs → different points.
  - `testTheCompassHeadingDoesNotChangeTheShape` — the east–west and north–south lines with the same trip id → equal shapes (± 1e-6).
  - `testIdenticalPointsGiveNoShape` — 400 copies of one coordinate → nil.
- [ ] **Step 2:** Run `-only-testing:CarodoTests/DriveShapeMakerTests` → fails (type missing).
- [ ] **Step 3: Implement.** Order and the parts the tests do not pin:
  - trim: walk cumulative metres from each end (`Geo` distance) and cut at the first point past `max(zone, minimumTrimM)`; then, per end, while that end's point is within `homeWorkRadiusM` of any Home/Work centre, drop it.
  - length check on the trimmed route (sum of segment metres) `< minimumLengthM` → nil; fewer than 8 points → nil.
  - project to metres with `LocalProjection` (origin = first point); centroid; principal axis angle `0.5 * atan2(2·sxy, sxx − syy)`; rotate by −angle.
  - seed: `UInt64` from the UUID's 16 bytes (first 8 XOR last 8) into `SeededGenerator`; mirror x if `next() & 1 == 1`; tilt `(Double(next()) / Double(UInt64.max) * 2 − 1) * maxTiltDegrees`.
  - fit into the unit box: scale = 1 / max(width, height), centre the shorter side.
  - simplify: binary search the tolerance (0 … 0.5, 24 iterations) with `RouteSimplifier.keptIndices(planar:)` for the largest kept count ≤ 64 that is ≥ 48; when the route has fewer than 48 points keep them all.
  - `DriveShape(points:)`, clamping each coordinate to 0...1 against rounding.
- [ ] **Step 4:** Run the tests → pass; then `-only-testing:CarodoTests/RouteSimplifierTests` → still pass.
- [ ] **Step 5:** `docs/architecture.md` Algorithms table: a row "A drive's Feed shape" naming `DriveShapeMaker` and the rejected alternatives (k·90° turns; every k-th point; north-up).

### Task 3: Checks and commit

- [ ] **Step 1:** `task format`, `task lint`, `task warnings`, `task test` → clean, 0 warnings, all pass.
- [ ] **Step 2:** Stage this plan's paths; commit `feat(feed): drive shapes made on the device for the feed` (no AI trailer).
