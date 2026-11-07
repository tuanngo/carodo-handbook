# Atlas on MKMapView + MKMultiPolyline — implementation plan (2026-11-05)

Status: **draft for owner review** — no code changed yet.

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (recommended)
> or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** the Map tab draws its whole history layer in a handful of overlays (heatmap: 5, one per
level; routes: 2; footprint: 1), so no line cap is needed and every line keeps all its points and
corners, while the screen keeps every behaviour it has today.

**Architecture:** only the map surface of `MapAtlasView` changes. Its SwiftUI `Map { … }` becomes
`AtlasMapView`, a `UIViewRepresentable` around `MKMapView` with a `Coordinator` (delegate,
renderers, camera). Everything around the map (chips, controls, legend, status line, sheets, tasks,
`HistoryAtlas`, the view model) stays SwiftUI and unchanged. The representable takes a value
snapshot (`AtlasMapState`) and a camera command; the coordinator diffs overlays **by group token**,
so a camera move or a GPS fix never touches the history overlays.

**Tech stack:** MapKit (UIKit: `MKMapView`, `MKMultiPolyline`, `MKMultiPolygon`, `MKCircle`,
`MKMapCamera`, `MKStandardMapConfiguration` …), SwiftUI `UIViewRepresentable`,
`UIHostingConfiguration` for the location marker. No new dependency or target.

**Evidence this rests on** (`carodo-ios/docs/specs/navigation.md`, History at scale): the SwiftUI
`Map` turns every `MapPolyline` into its own overlay. On an iPhone, 708 heat lines kept the CPU at
100–170 %; 450 is today's compromise, and anything under ~150 breaks the heatmap into dots. The
simulator's memory runs away past ~200 lines. The limit is overlays, not points.

## Global constraints

- iOS 17+, Swift 6, default MainActor isolation; `nonisolated` for pure builders; no
  `@unchecked Sendable`, no `DispatchQueue`, no `Task.detached`.
- No new package, target, entitlement or Info.plist key (P6 untouched).
- Map markers only from the design system (`RouteEndMarker`, `PlaceMapMarker`, the location
  markers moved, not redrawn); map motion and line values only from `MapTuning`.
- Copy: none added (the markers are decorative; VoiceOver labels unchanged).
- Location history stays private: no coordinates in logs, including the new perf logging.
- `task lint` passes; tests added per task; `docs/` updated in the same change.

## What exists today (survey of `MapAtlasView.swift`, 875 lines)

| # | Behaviour | Where today | Kept by |
|---|---|---|---|
| 1 | History layer: routes (drives copper, rides thin grey under), heatmap (5 levels, busier on top), footprint squares; a Passport focus draws its redacted lines | `map` content `switch model.layer` | Task 1, 2 |
| 2 | GPS accuracy circle under the route | `MapCircle` | Task 1, 2 |
| 3 | Live drive: one polyline per `LiveLine` segment, ivory casing 10 pt + copper 6 pt | `ForEach(segments)` | Task 1, 2 |
| 4 | Location marker: `UserLocationMarker` (cone in heading follow) or `DriveLocationMarker` (branded, travel tip) by `MapRenderingPolicy` | `UserAnnotation` | Task 4 |
| 5 | Map style: Standard (muted in Dark) / Hybrid / Imagery, POIs excluded, flat or realistic elevation (2D/3D) | `mapStyle` | Task 3 |
| 6 | No system controls (`mapControls {}`); bottom inset for the floating bar (`safeAreaPadding`) | | Task 3 |
| 7 | Camera: free; follow north-up / close / heading at a kept distance; a drive's fixes glide linearly over the fix interval; Map's own fixes ease 0.8 s; 2D/3D tilts in place; fit history (rect, or a pitched camera in 3D); focus saves and restores the camera | `position` writes | Task 3, 5 |
| 8 | A pan by the person drops follow to free | `position.positionedByUser` | Task 3, 5 |
| 9 | Heading of the map feeds the marker cone continuously; on settle: `lastCamera` and the history viewport (tilt-aware) | `onMapCameraChange` ×2 | Task 3, 5 |
| 10 | Off screen: the map is taken down; back: base map first, layer drawn in after a pause | `isOnScreen`, `reveal()` | Task 5 |

Not in the code today: **tapping a route to select it.** The plan does not add it; if wanted, it is
a separate feature (an MKMultiPolyline cannot say which drive was tapped without a hit-test index).

## Decisions for the owner

1. **Heat dedupe goes away.** With one overlay per level drawn quietest first, a quiet drive's line
   under a busy road is covered by the busy one: drawing each road once no longer buys anything and
   is what opened gaps. `HeatDeduplication`, the 450 cap and the grid coarsening are deleted; the
   heatmap draws every run with all its points (`absorbingShortRuns` stays, it only joins runs).
   Task 7 measures vertex cost; if a far view of 2,000 drives costs too much, the fallback is the
   direction-aware dedupe at a sub-point cell, still without a cap.
2. **One ADR** (`carodo-ios/docs/decisions/0015-the-map-tab-draws-on-mkmapview.md`): the Map tab's
   map is `MKMapView` because the SwiftUI `Map` has no multi-polyline; every other map (journey
   detail, Trim, places, onboarding) stays SwiftUI `Map`.
3. **Reveal becomes a fade.** With a few overlays there is nothing to draw in steps: coming back,
   the base map shows at once and the history overlays fade in (renderer alpha 0 → 1 over
   `MapTuning.atlasRevealFadeS` = 0.25 s, after `atlasRevealDelayS` = 0.12 s). `atlasRevealSteps` and
   `atlasRevealStepS` are removed.

## Files

| File | Change | Responsibility |
|---|---|---|
| `Carodo/Features/Map/Views/AtlasOverlays.swift` | create | Pure: layer + live line + accuracy → grouped overlays with their style and a group token |
| `Carodo/Features/Map/Views/AtlasMapView.swift` | create | `UIViewRepresentable` + `Coordinator`: configuration, overlay sync, renderers, camera commands, events |
| `Carodo/Features/Map/Views/AtlasLocationMarkers.swift` | create | `UserLocationMarker`, `DriveLocationMarker`, `MarkerHeading`, `HeadingCone`, `TravelTip` moved out of `MapAtlasView` (unchanged), plus the `MKAnnotationView` that hosts them |
| `Carodo/Features/Map/Views/MapAtlasView.swift` | modify | `map` → `AtlasMapView`; `position` → `AtlasCameraCommand`; events wired; reveal simplified; `mapScope` removed |
| `Carodo/Features/Map/ViewModels/MapAtlasViewModel.swift` | modify | `layerToken: Int`, bumped whenever `layer` is assigned |
| `Carodo/Core/Domain/RouteHeat.swift`, `Carodo/Core/Atlas/HistoryAtlas.swift` | modify (Task 6) | delete `HeatDeduplication` and the cap/coarsening |
| `Carodo/DesignSystem/MapTuning.swift` | modify | reveal values (decision 3) |
| `CarodoTests/AtlasOverlaysTests.swift`, `CarodoTests/AtlasMapViewTests.swift` | create | |
| docs: `specs/navigation.md`, `design-system.md` (Map tuning), `architecture.md` (Map row), ADR 0015 | modify/create | |

## Review focus

1. **A GPS fix or a camera move re-adds history overlays** → flicker and CPU. Pinned by
   `testACameraOnlyUpdateTouchesNoOverlay` and `testAFixReplacesOnlyTheLiveAndAccuracyOverlays` (Task 2).
2. **A pan while following is not detected** (MKMapView has no `positionedByUser`) → the camera
   fights the finger. Pinned by `testAGestureRegionChangeReportsAUserMove` (Task 3) + device check.
3. **Light/Dark or style switch leaves old colours** (renderers are cached per overlay). Pinned by
   `testAColourSchemeChangeRebuildsTheHistoryGroup` (Task 2): `onDarkMap` is part of the history token.
4. **The marker stops turning** (annotation views are reused; the heading must stay observed).
   Pinned by keeping `MarkerHeading` `@Observable` and hosting via `UIHostingConfiguration`
   (Task 4) + simulator check with `-carodo.debugStartDrive YES`.
5. **Going off screen while a camera animation runs** leaves a dead map retained by an animation
   block. Pinned by `testDismantleClearsTheDelegate` (Task 3): `dismantleUIView` sets
   `delegate = nil` and removes overlays.

---

### Task 1: Grouped overlays (pure)

**Files:** create `Carodo/Features/Map/Views/AtlasOverlays.swift`, `CarodoTests/AtlasOverlaysTests.swift`

**Interfaces — produces:**

```swift
enum AtlasOverlayGroup: Hashable { case history, live, accuracy }

/// One MKOverlay and how to draw it (the renderer reads this; nothing else styles a line).
struct AtlasOverlayStyle: Equatable {
    var stroke: UIColor; var fill: UIColor?; var lineWidth: CGFloat
    var lineCap: CGLineCap = .round; var lineJoin: CGLineJoin = .round
}

final class StyledMultiPolyline: MKMultiPolyline { let style: AtlasOverlayStyle }   // init(_ polylines:, style:)
final class StyledMultiPolygon: MKMultiPolygon { let style: AtlasOverlayStyle }
final class StyledCircle: MKCircle { var style: AtlasOverlayStyle }                 // via convenience init

enum AtlasOverlays {
    /// Quietest heat level first, so busier levels draw on top; rides before drives.
    static func history(_ layer: AtlasLayer?, onDarkMap: Bool) -> [MKOverlay]
    static func live(_ segments: [[CLLocationCoordinate2D]]) -> [MKOverlay]   // casing, then copper
    static func accuracy(center: CLLocationCoordinate2D?, radiusM: CLLocationAccuracy?) -> [MKOverlay]
}
```

Values copied from today's `map`: heat stroke `DriveHeatPalette.color(level, onDarkMap:)`, width
`DriveHeatPalette.lineWidth(level)`; drives `DriveHeatPalette.color(.once, …)` width
`lineWidth(.once)`; rides `CarodoSurface.textSecondary` 0.7 opacity, half width; footprint fill
`CarodoColor.copper` 0.22 (dark) / 0.18, stroke copper 0.55, 0.6 pt; live casing ivory 10, copper 6;
accuracy fill `accent` 0.12, stroke `accent` 0.35, 1 pt. Empty groups produce no overlay.

- [ ] **Step 1: failing tests**
  - `testAHeatmapIsFiveOverlaysAtMost`: 3,000 `AtlasHeatLine`s over all 5 levels → 5 overlays,
    each `StyledMultiPolyline`, levels ascending (`lineWidth` strictly increasing), polyline counts
    summing to 3,000, and every input coordinate present (no point dropped).
  - `testRoutesAreTwoOverlaysRidesFirst`: 2,000 drives + 50 rides → 2 overlays, first is the rides'.
  - `testRoutesWithoutRidesAreOneOverlay`.
  - `testFootprintIsOneMultiPolygon`: 1,500 tiles → 1 `StyledMultiPolygon` of 1,500 polygons.
  - `testNoLayerIsNoOverlay` (nil and empty layers).
  - `testALiveDriveIsCasingThenCopper`: 3 segments → 2 overlays, widths 10 then 6.
  - `testNoAccuracyWithoutARadius`.
- [ ] **Step 2:** run `xcodebuild test … -only-testing:CarodoTests/AtlasOverlaysTests` → fails (no type).
- [ ] **Step 3:** implement. A single-segment group is still an `MKMultiPolyline` (one renderer path).
- [ ] **Step 4:** tests pass; `task lint`.

### Task 2: Overlay sync by group token

**Files:** create `AtlasMapView.swift` (sync part only), `CarodoTests/AtlasMapViewTests.swift`

**Interfaces — consumes** Task 1. **Produces:**

```swift
struct AtlasMapState: Equatable {
    var historyToken: Int            // MapAtlasViewModel.layerToken, combined with onDarkMap and revealed
    var history: AtlasLayer?         // compared by token only (not Equatable-heavy)
    var onDarkMap: Bool
    var liveToken: Int               // session.liveLine revision (count of points is enough)
    var liveSegments: [[CLLocationCoordinate2D]]
    var accuracy: (center: CLLocationCoordinate2D, radiusM: Double)?   // wrapped Equatable
    var marker: AtlasMarker?         // Task 4
    var configuration: AtlasMapConfiguration   // Task 3
    var bottomInset: CGFloat
}

/// Applies the overlays that changed, by group; never touches a group whose token is the same.
final class AtlasOverlaySync {
    init(mapView: MKMapView)
    func apply(_ state: AtlasMapState)
    private(set) var tokens: [AtlasOverlayGroup: Int]
}
```

Order on the map (bottom to top): history, accuracy, live; groups are inserted with
`insertOverlay(_:below:)` against the first overlay of the group above so a replaced group keeps
its level.

- [ ] **Step 1: failing tests** (a real `MKMapView` in the hosted test, no window needed):
  - `testACameraOnlyUpdateTouchesNoOverlay`: apply a state, record `mapView.overlays` identities
    (`ObjectIdentifier`), apply the same state with only `bottomInset`/camera-irrelevant fields
    changed → identical array.
  - `testAFixReplacesOnlyTheLiveAndAccuracyOverlays`: change `liveToken` + accuracy → history
    overlay identities unchanged, live/accuracy identities new.
  - `testANewLayerReplacesOnlyTheHistory`.
  - `testAColourSchemeChangeRebuildsTheHistoryGroup`: same layer token, `onDarkMap` flipped → new
    history overlays with the dark colours.
  - `testGroupsKeepTheirOrder`: after replacing history, it is still below accuracy and live.
- [ ] **Step 2:** run → fails. **Step 3:** implement. **Step 4:** pass; lint.

### Task 3: The map view: configuration, renderers, camera, events

**Files:** `AtlasMapView.swift` (representable + coordinator), tests in `AtlasMapViewTests.swift`

**Interfaces — produces:**

```swift
struct AtlasMapConfiguration: Equatable { var style: MapAtlasViewModel.Style; var is3D: Bool; var isDark: Bool }
extension AtlasMapConfiguration { func make() -> MKMapConfiguration }   // pure mapping

/// A camera move the view asks for; applied once per id.
struct AtlasCameraCommand: Equatable {
    enum Target: Equatable { case camera(MapCamera), rect(MKMapRect) }
    enum Motion: Equatable { case none, ease(Double), linear(Double) }
    let id: Int; let target: Target; let motion: Motion
}

struct AtlasMapView: UIViewRepresentable {
    var state: AtlasMapState
    var command: AtlasCameraCommand?
    var onHeading: (CLLocationDirection) -> Void            // continuous (marker cone)
    var onSettle: (MapCamera, MKMapRect) -> Void            // regionDidChange
    var onUserMove: () -> Void                              // a gesture moved the map
}
```

Configuration mapping (copied from `mapStyle`): `.standard` →
`MKStandardMapConfiguration(elevationStyle: is3D ? .realistic : .flat, emphasisStyle: isDark ? .muted : .default)`;
`.imagery` → `MKHybridMapConfiguration(elevationStyle:)`; `.satellite` →
`MKImageryMapConfiguration(elevationStyle:)`; every one `pointOfInterestFilter = .excludingAll`.
`showsCompass = false`, `showsScale = false`, `showsUserLocation = false` (the marker is ours),
`isPitchEnabled = true`. `bottomInset` → `mapView.layoutMargins.bottom` and the edge padding of a
`.rect` command (what `safeAreaPadding(.bottom, barClearance)` did).

Camera: `.camera` → `MKMapCamera(lookingAtCenter:fromDistance:pitch:heading:)`; `.ease(d)` →
`UIView.animate(withDuration: d, delay: 0, options: [.curveEaseInOut, .beginFromCurrentState])`
setting `mapView.camera`; `.linear(d)` same with `.curveLinear` (a drive's glide); `.rect` →
`setVisibleMapRect(_:edgePadding:animated:)`. A command is applied once (coordinator keeps the last
id), so a re-render never replays it.

Events: `mapViewDidChangeVisibleRegion` → `onHeading(camera.heading)`; `regionDidChangeAnimated`
→ `onSettle(MapCamera(mapView.camera), mapView.visibleMapRect)`; `regionWillChangeAnimated` →
`onUserMove()` when any gesture recognizer of the map's view tree is `.began`/`.changed` (the
standard MKMapView idiom for "changed by the user").

- [ ] **Step 1: failing tests**
  - `testEachStyleMapsToItsConfiguration` (3 styles × 2D/3D × light/dark: class, elevation, emphasis, POI filter).
  - `testACommandIsAppliedOnce`: same command id twice → camera set once (count via a test hook
    `applied: Int` on the coordinator).
  - `testAGestureRegionChangeReportsAUserMove` / `testAProgrammaticChangeDoesNot` (inject the
    "is gesture active" check as a closure the test sets).
  - `testDismantleClearsTheDelegate`.
- [ ] **Step 2:** run → fails. **Step 3:** implement. **Step 4:** pass; lint.

### Task 4: The location marker as an annotation view

**Files:** create `AtlasLocationMarkers.swift` (move `MarkerHeading`, `UserLocationMarker`,
`DriveLocationMarker`, `HeadingCone`, `TravelTip` verbatim from `MapAtlasView.swift`, `private` →
internal); add to `AtlasMapView.swift`:

```swift
enum AtlasMarker: Equatable { case user, drive }          // from MapRenderingPolicy.showsBrandedMarker
final class AtlasMarkerAnnotation: NSObject, MKAnnotation { @objc dynamic var coordinate: CLLocationCoordinate2D }
final class AtlasMarkerView: MKAnnotationView   // contentConfiguration = UIHostingConfiguration { marker(heading) }
```

`AtlasMapState` gains `markerCoordinate: CLLocationCoordinate2D?` and `marker: AtlasMarker?`; the
`MarkerHeading` instance is passed once to the coordinator (it is `@Observable`, so the hosted
SwiftUI view turns without the annotation being rebuilt). A new coordinate moves the one annotation
inside the same animation as the camera command (so marker and camera glide together, as today);
the annotation is never removed and re-added for a fix. `zPriority = .max`, `collisionMode = .none`,
`displayPriority = .required`.

- [ ] **Step 1: failing test** `testAFixMovesTheOneAnnotation`: two states with different
  coordinates → `mapView.annotations.count == 1` and the same object, coordinate updated;
  `testTheMarkerKindFollowsThePolicy`.
- [ ] **Step 2–4:** fail → implement → pass; lint.

### Task 5: Switch MapAtlasView to AtlasMapView

**Files:** modify `MapAtlasView.swift`, `MapAtlasViewModel.swift` (`layerToken`), `MapTuning.swift`
(decision 3), `CarodoTests/MapAtlasViewModelTests.swift`.

- `@State position: MapCameraPosition` → `@State cameraCommand: AtlasCameraCommand?` and a counter;
  every `withAnimation(x) { position = … }` becomes `move(to:motion:)` with the same target and
  duration (follow ease 0.6/0.8/0.5, drive glide `.linear(glide)`, fit `.ease(0.7)`, focus restore
  `.ease(0.6)`, 2D/3D `.ease(0.5)`). Reduce Motion → `.none` where `withAnimation` had `nil` today.
- `onChange(position.positionedByUser)` → `onUserMove: { followMode = .free }`.
- The two `onMapCameraChange` bodies move verbatim into `onHeading` / `onSettle`
  (`MapCamera` and `AtlasRect(rect)` as today).
- Remove `mapScope`, `.mapScope`, `.mapStyle`, `.mapControls`, `revealed`, `revealGeneration`,
  `reveal()`, `layerCount`; `isOnScreen` stays (the representable is not in the tree off screen);
  coming back sets `historyVisible = false`, waits `atlasRevealDelayS`, then true → the coordinator
  fades the history renderers' alpha in over `atlasRevealFadeS`.
- `MapAtlasViewModel.layer`'s setter bumps `layerToken` (test: `testEveryNewLayerHasANewToken`).
- [ ] **Step 1:** view-model test fails → **Step 2:** implement the view model change → pass.
- [ ] **Step 3:** switch the view; build; all tests pass; lint.
- [ ] **Step 4: simulator checklist** (`-carodo.sampleData YES`), each against today's build:
  routes / heatmap / footprint / focus (`-carodo.debugMapIntent routes`); Standard / Hybrid /
  Satellite in Light and Dark; 2D↔3D; follow north-up → close → heading → pan drops to free;
  `-carodo.debugStartDrive YES` live line + branded marker + glide; tab away and back (fade);
  Journeys detail → back. Screenshots attached to the report.

### Task 6: Remove the cap and the dedupe

**Files:** `RouteHeat.swift` (delete `HeatDeduplication`, keep `absorbingShortRuns`),
`HistoryAtlas.swift` (heatLines returns every visible run, routes returns every line; delete
`drawable`), tests: delete the 5 `HeatDeduplication` tests and
`testAManyDriveViewStaysWithinWhatTheMapCanDraw`; add
`testTheHeatmapKeepsEveryRunAndEveryPoint` (4 drives with a 90° turn → every coordinate of every
run returned, the turn vertex present).
- [ ] fail → implement → full suite passes → lint.

### Task 7: Measure, then document

- [ ] Simulator: sample journal, heatmap/routes/footprint, 30 s `footprint` sampling → memory flat.
- [ ] iPhone (Activity Monitor via `xctrace`, `-carodo.sampleData YES`, then the owner's journal):
  heatmap / routes / footprint idle 30 s → CPU idle between gestures; compare with today's numbers
  in `docs/specs/navigation.md` (3,320 lines: 40–97 %; 450: 0–70 %).
- [ ] `HistoryAtlasPerformanceTests` (opt-in) for 2,000 drives: if a far heat view's total points
  make the first draw stall (> 100 ms on the main actor in Time Profiler), bring back the
  direction-aware dedupe at a sub-point cell, no cap (decision 1 fallback).
- [ ] Docs: `navigation.md` (History at scale: overlays per layer, no cap, the numbers),
  `design-system.md` (Map tuning: reveal fade), `architecture.md` (Map row), ADR 0015.

## Out of scope

Tapping a route to open its journey; moving any other map off SwiftUI `Map`; the 20–40 % CPU the
Map tab shows even with few lines (Time Profiler first; separate finding in `navigation.md`).

## Self-review

- Coverage: owner goals 1 (heat 5 overlays, no cap, all points) → Tasks 1, 6; 2 (routes and
  footprint few overlays) → Task 1; 3 (every behaviour, no re-add on camera/GPS) → table above,
  Tasks 2–5, Review focus 1. Route selection does not exist today: stated, not invented.
- Names: `AtlasOverlays`, `AtlasOverlayGroup`, `AtlasOverlayStyle`, `AtlasOverlaySync`,
  `AtlasMapState`, `AtlasMapConfiguration`, `AtlasCameraCommand`, `AtlasMapView`, `AtlasMarker`,
  `AtlasMarkerAnnotation`, `AtlasMarkerView`, `layerToken` — used consistently across tasks.
- Proportion: interfaces and tests only; bodies are left to the implementer except the style
  values and the configuration mapping, which are copied from today's code.
