# Map lookups: held like the sensors, with rules a test holds

Design, for the owner's approval. Written 2026-11-17 from the backlog row "Map lookups held like
the sensors" ([`backlog.md`](backlog.md)), section 10 of [`location-runtime.md`](location-runtime.md),
and TD-45 ([`technical-debt.md`](technical-debt.md)). `carodo-ios` at `3a11d86`. After approval this
becomes a step-by-step implementation plan; no code before that
([`../AGENT_WORKFLOW.md`](../AGENT_WORKFLOW.md), Plan before code).

**Status (2026-11-17):** draft reviewed against the code's use cases (section 10); the owner
answered D1, D2 and Q1 the same day (section 9), and approved the design (2026-11-17). Next: the
implementation plan, [`map-lookups-plan.md`](map-lookups-plan.md).
**Built (2026-11-17):** carodo-ios `1cc3247`, `c8ae877`, `b70e2b4` on `refactor/map-lookups`,
merged into `main` in `853f28e`; the device half of TD-45 is PV-26.

## 1. Why

The location runtime put every sensor in one folder, under an owner, behind a protocol with a fake,
and made `ArchitectureTests` (R1–R6) fail on a stray one. Apple Maps' network lookups were left out:
"not sensors, they get their own row when that family is done" (location-runtime.md, section 6).

They cost something different from a sensor: not battery, but **Apple's quota and the person's
privacy**. Each request sends a coordinate to Apple, MapKit throttles per app across all its
requests (`MKError.loadingThrottled`), and Apple's geocoding guidance is one request a minute for a
moving user and none while the app is in the background (TD-43). A request made where nobody looks
spends the same quota every screen's names depend on.

Today (section 3) most of them already have a protocol and are created by the composition root,
but three places ask Apple directly, outside any rule:

- the onboarding film asks `MKDirections` from inside a Feature view
  (`Features/Onboarding/Map/JourneyMapLayer.swift`);
- two map-image makers each build an `MKMapSnapshotter` in `Core/Journal`
  (`JourneyMapSnapshotService`, `ShareCardRenderer`), one of them a process-wide `.shared` that
  views reach for directly.

Nothing stops a fourth. This work makes the layout and two tested rules do the watching, and
closes TD-45, the two location adapters left without a counting seam.

## 2. Goals, non-goals, anti-goals

**Goals**

1. `Core/MapLookup` is the only folder that creates a request to Apple Maps' services: geocoding,
   search, points of interest, directions, map item by identifier, map snapshots.
2. Each lookup has a protocol and a fake, and its live adapter is created only by
   `DependencyContainer`. The two lookup caches (`PlaceNameCache`, `POINameCache`) too: a second
   cache is a second budget, and two budgets would double the requests a minute.
3. One table in `carodo-ios/docs/architecture.md` says, for each lookup: its protocol and fake, its
   owner, who asks it, what bounds it (cache, budget, timeout), and whether it may run in the
   background (never).
4. Two rules in `ArchitectureTests` (R7, R8, section 5) fail on a request or an adapter made
   anywhere else.
5. TD-45: `CoreCurrentPosition` and `CoreMotionActivity` get a counting seam like
   `CompassControlling`, with unit tests of their switch and their start/stop.
6. The location and lookup rules scan `CarodoShared/` and `CarodoWidgets/` too (the "only
   `Carodo/` is scanned" part of TD-46; both are clean today).

**Non-goals**

- The inside of a lookup: its caching, budget, TTL, retry and active-only rule stay as they are
  (`MapDataCache`, `PlaceNameCache`, `POINameCache`, `enrichJourneys`).
- Moving the protocols. `GapRouter` (in `Core/Recording`), `POISearching` and
  `NearbyStationFinding` (in `Core/Domain`) stay beside the pure logic that uses them; the rule is
  about who creates, not where a protocol sits.
- `CLGeocoder` → `MKReverseGeocodingRequest` (needs iOS 26; `PlaceLookup.swift` says when).
- The live `Map` and `MKMapView` on screens: drawing tiles is the map's own business, not a request
  Carodo makes (design-system.md, Map rules).
- The rest of TD-46 (text matching in R1, R3, R5, R6): the new rules match text the same way and
  say so.
- Schema, API, permissions, entitlements, background modes, dependencies, targets: none change.

**Anti-goals** (a failure even if it works)

- A map image, a share card or the onboarding film looks different after this work.
- A lookup made in the background that was not made before, or more requests a minute than before.
- Screens slower to show their map image (the snapshot keeps its queue and its three-at-a-time
  limit).
- A rule so broad it fails on a type or an options value that sends nothing
  (`MKDirections.Request`, `MKMapSnapshotter.Options`, `MKPointOfInterestFilter`).

## 3. Today

Every place in `Carodo/` that creates a request to Apple Maps (grep at `3a11d86`; `CarodoShared/`
and `CarodoWidgets/` have none):

| Request | Created in | Behind | Created by | Fake | In the background |
|---|---|---|---|---|---|
| `CLGeocoder` (reverse) | `Core/MapLookup/PlaceLookup.swift` (`AppleGeocoderPlaceLookup`) | `PlaceLookup`, asked only through `PlaceNameCache` | `DependencyContainer` (app, showcase) | `ScriptedPlaceLookup` and two more (tests) | Never: `MapDataCache` asks nothing while not active (TD-43, built) |
| `MKMapItemRequest` (name by id) | `Core/MapLookup/POINameLookup.swift` (`MapKitPOINameLookup`) | `POINameLookup`, through `POINameCache` | `DependencyContainer` (app, showcase) | `ScriptedPOINameLookup` (tests) | Never: same cache rule |
| `MKLocalSearch` (points of interest) | `Core/MapLookup/MapKitPOISearch.swift` | `POISearching` (place detection, a place's Nearby) | `DependencyContainer.journeyPointServices` | `SamplePOISearch`, test fakes | Never: `enrichJourneys` matches points only while active |
| `MKLocalSearch` (stations) | `MapKitPOISearch.pointsOfInterest`, called by `MapKitStationFinder` | `NearbyStationFinding` | `DependencyContainer` | `SampleStationFinder` | No: the fill-up sheet on screen |
| `MKDirections` (gaps, lead-ins) | `Core/MapLookup/AppleMapsGapRouter.swift` | `GapRouter` | `DependencyContainer` | `FakeRouter` (tests); nil in sample containers | Never: `enrichJourneys` routes only while active |
| `MKDirections` (onboarding's demo road) | **`Features/Onboarding/Map/JourneyMapLayer.swift`**, in the view's coordinator | nothing | the view | none; offline it draws its own line | No: onboarding on screen |
| `MKMapSnapshotter` (Footprint, backdrops) | **`Core/Journal/JourneyMapSnapshotService.swift`** (`snapshot`) | a `Render` closure in its `init` | **`static let shared`**, reached by `JourneyMapBackdrop`, `PassportExplorationSection` and the container's erase | a `Render` stand-in (tests) | No: rows on screen |
| `MKMapSnapshotter` (share card) | **`Core/Journal/ShareCardRenderer.swift`** (`ground`) | nothing; `ShareCardModel` takes a `makeGround` closure whose default calls it | `JourneyDetailView` (default closure) | a `makeGround` stand-in (tests) | No: the share editor on screen |

So the shape is mostly there: what is missing is the onboarding request, the two snapshotters,
the `.shared` service, and a test that keeps it that way.

TD-45, as it stands: `CoreCurrentPosition.current` reads `CLLocationManager.authorizationStatus`
and `location` directly and starts `CLLocationUpdate.liveUpdates()` in a static function;
`CoreMotionActivity.follow` and `stopFollowing` call `CMMotionActivityManager` directly. The pure
order (`CurrentPositionChoice.pick`) and the session's use are tested; the adapters are not.

## 4. Design

### 4.1 The family

`Core/MapLookup` keeps its eight files and gains one: `AppleMapSnapshotter.swift`. Its header in
`docs/architecture.md`'s tree becomes "the only folder that asks Apple Maps' services".

### 4.2 Map snapshots behind one protocol

A protocol and its live adapter, in `Core/MapLookup`:

```swift
nonisolated struct MapSnapshotRequest: Sendable {
    enum Area: Sendable { case region(MKCoordinateRegion), mapRect(MKMapRect) }
    enum Look: Sendable { case muted, journey }   // muted: flat, no POI (the Footprint, backdrops);
                                                   // journey: CarodoMapLook.standard(isDark:is3D: false)
    let area: Area
    let size: CGSize          // already enlarged by the caller's label shrink
    let scale: CGFloat
    let isDark: Bool
    let look: Look
    let lines: [[CLLocationCoordinate2D]]   // projected into the image, in the snapshot's points
}

nonisolated struct MapSnapshot: Sendable {
    let image: UIImage
    let lines: [[CGPoint]]
}

nonisolated protocol MapSnapshotting: Sendable {
    /// The map, or nil when MapKit gives none (offline with nothing cached).
    func snapshot(_ request: MapSnapshotRequest) async -> MapSnapshot?
}
```

- `AppleMapSnapshotter` builds the `MKMapSnapshotter.Options` from the request, starts it on the
  same `.global(qos: .userInitiated)` queue as today, and projects `lines` with the snapshot's own
  `point(for:)` inside the completion: `MKMapSnapshotter.Snapshot` never leaves the adapter (it is
  not `Sendable`). Its R4 allow-list entry moves with it (from `JourneyMapSnapshotService.swift:
  snapshot`).
- `JourneyMapSnapshotService` keeps everything it owns today (memory and disk cache, in-flight
  sharing, three at a time, prune, erase) and draws its lines from `MapSnapshot.lines`; its `init`
  takes `any MapSnapshotting` in place of today's `Render` closure.
- `ShareCardRenderer.ground(for:withMap:)` takes `any MapSnapshotting` and builds its `Ground` from
  the answer; the plain ground when nil, as today.
- The label shrink (1.8 for the service, 1.5 for the card) and every option value stay where they
  are decided today, so the images are pixel-for-pixel the same (anti-goal 1). The Footprint's
  lines are projected in the completion instead of while drawing: the same `point(for:)` calls,
  moved; the 1.5-point thinning stays in `draw`.
- `JourneyMapSnapshotService`'s tests build it today with a `Render` closure that returns an image
  (cache, in-flight sharing, erase). They take a fake `MapSnapshotting` returning a blank image
  instead; what they prove does not change.
- Fake: `NoMapSnapshot` (always nil: the offline path every caller already handles), beside the
  protocol; tests keep their stand-ins.

### 4.3 One owner for the map images

`JourneyMapSnapshotService.shared` goes. `DependencyContainer` creates one service with the live
snapshotter and the default cache folder (`mapImages`), and the root puts it in the environment;
`JourneyMapBackdrop` and `PassportExplorationSection` read it there, and the erase path uses the
container's. The share editor's `makeGround` closure is built from the container's snapshotter
where `JourneyDetailView` opens it (the view reads `\.dependencyContainer`, as `OnboardingView`
does; it reads only `AppState` today).

The builder's call, with a sound default: an environment value of its own (`\.mapImages`) rather
than `DesignSystem` reading the whole container. A container made for a preview or a test gets a
service with no disk folder, so only the app's one service ever writes the cache folder.

### 4.4 The onboarding film's demo road

`JourneyMapLayer.loadRoute()` asks the container's `GapRouter` (Apple's directions between two
points, by car) in place of building its own `MKDirections`, and turns the answer's coordinates into
its `MKPolyline`. `OnboardingView` already reads the container and hands the router in. With no
router (a sample container), or no answer, the film draws its own line, as it does offline today.

This reuses `GapRouter` for a second caller of the same capability; no type is renamed. Its doc
comment widens from "a GPS gap or a lead-in" to "Apple's road between two points" (section 9, made
here).

### 4.5 In the background

No change in behaviour. The table (goal 3) states for each lookup what keeps it in the foreground:
the caches' `isActive`, `enrichJourneys`' `appIsActive`, or being asked only from a screen. TD-43's
device check stays pending as it is.

### 4.6 TD-45: two counting seams

Same pattern as `CompassControlling` (`Core/Location/HeadingSource.swift`): a small protocol over
the exact system calls the adapter makes, the system manager conforming by an empty extension, the
adapter taking it in `init` with the system manager as default.

- **`CoreCurrentPosition`**: a protocol for `authorizationStatus` and `location`, and the one-shot
  request injected as a closure (`(maxAgeS, maxAccuracyM, timeout) async -> LocationSample?`), its
  default today's `liveUpdates` function. Tests on a counting fake: a fresh drive fix answers with
  no request; a stale drive fix and no cached fix make exactly one request; no permission answers
  nil with no request; a cached fix that is fresh and accurate enough answers with no request; the
  root's `driveFix` wiring reads the session's last fix.
- **`CoreMotionActivity`**: a protocol for `startActivityUpdates(to:withHandler:)`,
  `stopActivityUpdates()` and `queryActivityStarting(from:to:to:withHandler:)`, plus the two
  availability and authorization reads as injected values. Tests: a second `follow` replaces the
  handler and starts nothing; `stopFollowing` stops once, a second stop does nothing; a reading
  reaches only the current handler; no follow without access.

### 4.7 A tracking-log line for the one-shot fix (TD-45, second half)

TD-45 also notes that "no second GPS request beside a fill-up" cannot be read from a drive. A
`position` line when a screen asks for the current position: who answered (`drive`, `cached`,
`request`, `none`) and, for a request, how long it took in whole seconds. No coordinate, no
accuracy value. Both fields are classified shared in `DiagnosticsLogFormat` (a category and a
duration inside one moment). Owner's decision D2.

## 5. The rules, each a test

In `CarodoTests/ArchitectureTests.swift`, with the same helper as R1–R3.

| # | Rule | The test fails when |
|---|---|---|
| R7 | Only `Core/MapLookup` asks Apple Maps' services | `CLGeocoder(`, `MKLocalSearch(`, `MKLocalSearchCompleter(`, `MKLocalPointsOfInterestRequest(`, `MKDirections(`, `MKMapItemRequest(`, `MKMapSnapshotter(`, `MKLookAroundSceneRequest(`, `MKLookAroundSnapshotter(`, `MKReverseGeocodingRequest(` or `MKGeocodingRequest(` appears outside `Carodo/Core/MapLookup/`. A request type is listed even when unused today, so the first use lands in the folder. `MKDirections.Request(` and `MKMapSnapshotter.Options(` do not match: they send nothing |
| R8 | Only the composition root creates a lookup or a lookup cache | `AppleGeocoderPlaceLookup(`, `MapKitPOINameLookup(`, `MapKitPOISearch(`, `MapKitStationFinder(`, `AppleMapsGapRouter(`, `AppleMapSnapshotter(`, `PlaceNameCache(`, `POINameCache.pointsOfInterest(` or `JourneyMapSnapshotService(` appears outside `Carodo/App/DependencyContainer.swift` and the type's own file |

**A rule on where, not a ban** (owner, 2026-11-17). Any Apple Maps service may be used. The usual
way is a new adapter in `Core/MapLookup` (protocol, fake, created by the container), which passes
both rules with no exception. A request that truly must be made elsewhere is an entry in the
rule's allow-list with its reason on the line, as R4's are; the change that adds it presents the
reason in its report, and the owner approves it.

R1, R2, R7 (and the source helper) scan `Carodo/`, `CarodoShared/` and `CarodoWidgets/` (goal 6).
Both new rules match text: a request built through a typealias or a factory slips past them, as
R1 and R3 already say (TD-46).

## 6. Docs

In the same change as the code (`carodo-ios/AGENTS.md`, Recipes):

- `docs/architecture.md`: a section "Map lookups: one owner each" after "Sensors: one owner each",
  with the table of section 3 as it will stand (protocol, fake, owner, asked by, bounded by, in
  the background). The sensors table's current-position and motion rows name their new seams. The
  folder tree's `MapLookup/` line.
- `carodo-ios/AGENTS.md`: the Architecture tree line for `MapLookup/`, and one recipe, "A request to
  Apple Maps", naming the folder, the protocol-and-fake pair, the composition root, the cache's
  budget and the active-only rule.
- `docs/privacy.md`, if it names where a snapshot or the onboarding road is asked (to check; no
  change in what is sent).
- `docs/tracking.md`'s log format, if D2 is taken.
- The handbook: TD-45 closed (or narrowed to what a device shows), TD-46's "only `Carodo/` is
  scanned" closed, the backlog row moved to done.

## 7. Slices and how each is proven

**One slice, one commit** (`refactor(maplookup): …`): it is small, and every part is the same
outcome. If D2 is taken, the log line is its own commit (it changes what a drive records in the
log).

1. **Unit tests**: R7 and R8 fail before the change and pass after; the TD-45 seam tests (4.6);
   `JourneyMapSnapshotService`, `ShareCardRenderer` and `ShareCardModel` tests pass on a fake
   snapshotter.
2. **Checks**: `task lint`, `task warnings`, `task test`.
3. **Simulator, before and after** (anti-goal 1): screenshots on the same simulator and data
   (`-carodo.sampleData YES`) of the Passport's Footprint, a Journeys row backdrop, a share card
   (Light and Dark), and the onboarding film's map. The same images, or the difference explained.
4. No device check is needed for the lookups (nothing on the tracking path changes). TD-45's
   seams are proven by unit tests; the `position` line (D2) is read on the next device drive with
   a fill-up, added to PV-26.

Committed when 1–3 pass.

## 8. Order inside the slice

1. TD-45 seams and their tests (no behaviour change, independent).
2. `MapSnapshotting`, `AppleMapSnapshotter`, both callers on it.
3. `mapImages` owned by the container; `.shared` removed.
4. Onboarding on `GapRouter`.
5. R7, R8, the wider scan; docs.

## 9. Decisions

**The owner's**

| # | Decision | Answer (2026-11-17) |
|---|---|---|
| D1 | Map snapshots count as a map lookup (they ask Apple's servers for tiles at a region) and move under the rule | **Yes** (owner): `MapSnapshotting`, `AppleMapSnapshotter`, `.shared` removed |
| D2 | A `position` tracking-log line (4.7) | **Yes, its own commit** (owner); read on the next device drive with a fill-up (PV-26) |
| Q1 | With no `GapRouter` (sample, showcase, DEBUG and storage-failure containers) the onboarding film draws its own line instead of Apple's road | **Accepted** (owner): no extra router in the container; the app's own container keeps Apple's road |
| D3 | One commit for the slice, D2's line apart | Recommended; follows from D2 |

**Made here, for the owner to check**

- Protocols stay where their consumers are; only creation is ruled.
- Onboarding reuses `GapRouter`; no rename.
- `\.mapImages` as its own environment value, not the container in `DesignSystem`.
- The two caches are in R8 (a second cache is a second budget).
- Request types unused today (`MKLocalSearchCompleter`, Look Around, iOS 26 geocoding) are listed in
  R7 anyway.
- No ADR: the rule extends `docs/architecture.md`'s, it changes no decision.

## 10. Review against the code's use cases

Done after writing (2026-11-17), by walking each caller of section 3 through the design.

| Use case | Path today | Under this design | Found |
|---|---|---|---|
| A drive's ends named (journal, detail) | `GRDBJourneyRepository` → `PlaceNameCache` → `AppleGeocoderPlaceLookup` | Unchanged; R8 holds the one cache | Showcase's DEBUG container makes its own pair, inside `DependencyContainer.swift`: allowed |
| A place's name by Apple id (places, fill-ups) | repositories → `POINameCache` → `MapKitPOINameLookup` | Unchanged | — |
| Place detection, a place's Nearby | `enrichJourneys` / `PlaceNearbyModel` → `journeyPointServices.search` | Unchanged | `journeyPointServices` makes a `MapKitPOISearch()` per read, inside the container: allowed (stateless) |
| Log fuel: stations | `MapKitStationFinder` → `CoreCurrentPosition` + `MapKitPOISearch.pointsOfInterest` (static) | Unchanged; the static call stays inside the folder | TD-45's seam covers its fix; D2's line makes it readable on a drive |
| Gap and lead-in healing | `enrichJourneys` → `AppleMapsGapRouter`, only while active | Unchanged | — |
| Onboarding's demo road | the view's own `MKDirections` | the container's `GapRouter` | `gapRouter` is nil in the sample, DEBUG and storage-failure containers: the film draws its own line there (Q1: accepted) |
| Passport Footprint, Explore/Day backdrop | `.shared` → `MKMapSnapshotter` | `\.mapImages` → `AppleMapSnapshotter` | Sample and showcase runs write the app's cache folder today; under 4.3 only the app's container does (builder's call kept) |
| Share card | `ShareCardModel` default `makeGround` → `ShareCardRenderer.ground` | closure from the container's snapshotter | `JourneyDetailView` needs the container from the environment |
| Erase local data | `DependencyContainer` → `.shared.eraseLocalCache()` | its own `mapImages` | — |
| Replay, the live maps (Atlas, detail, replay) | `MKMapView` on screen | Untouched (non-goal) | No snapshotter or request in the replay export |

## 11. Assumed, not checked

- `JourneyMapSnapshotService.draw` uses the snapshot only for its image and `point(for:)`, so
  projected lines are enough (read, not run).
- `UIImage` is `Sendable` on iOS 18 (it is marked so since iOS 17's SDK).
- `OnboardingView`'s container is the app's live one at first launch, so the film keeps Apple's
  road there.
- Nothing in `CarodoShared/` or `CarodoWidgets/` would trip R1, R2 or R7 once scanned (grep says
  none today).
