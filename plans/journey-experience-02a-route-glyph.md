# Journey Experience 02a — the Route Glyph (geometry and drawing)

Status: **Approved** (owner, 2026-11-14: D32, D33). **02a·0 done** (carodo-ios `b98d636`; PV-22, TD-30); next: 02a. Parent: [`journey-experience.md`](journey-experience.md)
(design contract D12–D31, mockup V9). No code before approval.

## Outcome

One way to turn a drive's display route into a drawing without a map, and one way to draw it, used
by every route the person sees of their own drives off the map: the Explore row (D29, D30), the
featured block (D24), the Day frame of several drives (D25). 02a builds the foundation only and
**changes no screen**: 02b (Explore) and 02c (Day) adopt it. It is proven by tests and a gallery of
images, so it can be committed by itself.

## Where it sits after the refactors (carodo-ios `195fda6`, `b3d486e`, `e99f1f4`)

The refactors are finished and on `main`; 02a follows their rules rather than reshaping anything:

- **One view or type per file** (`b3d486e`). New code gets one file per type. Two files 02a touches
  still hold several types, and are split *as they are touched*, in the same commit, with moves only:
  `DesignSystem/Components/RouteViews.swift` (`SpeedBand` extension, `RouteShape`, `RouteCurve`,
  `RouteThumbnail`) and `FeedShapeBackground.swift` (`FeedShapeCurve`, `FeedShapeBackground`, the
  `feedShape` modifier, `FeedTextClearance`). `JourneyCards.swift` (8 types) is left for 02b, which
  removes two of them anyway.
- **One folder per part of Journeys** (`195fda6`): 02a adds nothing under `Features/Journeys`. In
  02b/02c the row model shared by Explore and Day sits at the root of `ViewModels/`, beside
  `JourneyPresentation.swift` (the refactor's rule for what all parts share); Explore-only views in
  `Views/Explore`, Day-only in `Views/Day`, and what both draw (the row parts, the featured block)
  in `DesignSystem/Components`.
- **One home per kind of token** (`e99f1f4`): spacing from `CarodoSpacing`, colours from
  `CarodoColor`/`CarodoSurface`, motion from `CarodoMotion`; no number written in place in new code.

## Existing behaviour (files read)

| What | Today | File |
|---|---|---|
| Display route | `trips.route`, Douglas–Peucker 8 m, read with every journal row (`Journey.route`) | `Core/Domain/RouteSimplifier.swift` |
| Parts | `PassportExploration.gapFreeParts(_:)`: a display route broken at impossible jumps (implied speed above `LocationSample.implausibleSpeedMps`, or time not moving forward) | `Core/Domain/PassportExploration.swift` |
| Budgeted simplify | `DriveShapeMaker.simplify(_:to:)` (private): Douglas–Peucker with the tolerance searched to keep a point budget, filling a straight line back to the lower bound | `Core/Domain/DriveShapeMaker.swift` |
| Planar simplify | `RouteSimplifier.keptIndices(planar:tolerance:)` | `RouteSimplifier.swift` |
| Curve through points | **twice**: `RouteCurve.path(through:)` (a Catmull-Rom `CGPath`; the share card, `RouteShape(smoothed:)`) and `FeedShapeCurve.sampled(_:in:steps:)` (the same Catmull-Rom, sampled, fitted by the shorter side; the Feed) | `RouteViews.swift`, `FeedShapeBackground.swift` |
| The Feed's drawing | `FeedShapeBackground`: a faint ribbon (masked toward the trailing edge) under a halo in the row's colour and a thin core; width growing toward the end, fading at both ends; `feedShape(_:…)` clears the shape around every laid-out line of text (`Text.LayoutKey`) | `FeedShapeBackground.swift` |
| Route ends | `RouteEnd` / `RouteEndMarker`: Ivory disc (start), Charcoal disc (end), a flag only from 18 pt; "draw route ends only through this type" | `DesignSystem/Components/RouteEndMarker.swift` |
| List route today | `JourneyMapThumbnail` (snapshot, `RouteShape` while loading); the Passport's longest drive draws `RouteShape` | `JourneyCards.swift`, `Passport/Views/PassportHighlightsSection.swift` |
| Dead code | `RouteThumbnail` is used nowhere | `RouteViews.swift` |

## 02a·0 — Route ends, one mark everywhere (before the glyph; D32)

A screen change, so its own commit with screenshots (Light, Dark, imagery; the owner reviews first):
`RouteEnd` draws ring / dot / loop at any size (no flag, no shadow, the halo in the line's casing
colour), `RouteEndMarker` uses it at 16 pt; callers keep calling them: Journey Detail map and pins,
Trim, the onboarding film (`JourneyMapLayer`, 24 → 16 pt), `JourneyMapSnapshotService` (12 pt),
`ShareCardRenderer` (14 pt); `JourneyPointCard` symbols `circle` / `circle.fill`; a loop (ends
within the glyph's loop radius) draws one mark on maps too. Docs: design-system "Route ends" and
"Map markers — one source". Tests: the marks' geometry (sizes, loop rule) where pure; the rest is
screenshots. Device check: the marks at a glance on a real map outdoors.

## Proposal

### 1. Geometry (pure, `nonisolated`, Core)

- **`RouteGlyph`** (`Core/Journal/RouteGlyph.swift`): a value, `Sendable`, `Hashable`.
  `parts: [[SIMD2<Double>]]` in a unit box scaled by its **longer** side and centred on the shorter
  (the convention `DriveShape` already uses, so the one curve fits both); `aspect` (width ÷ height
  of the drawing, for the unboxed layout, D30); `start`, `end` (or one point when `isLoop`);
  `isLoop`; `span` in metres (for the size by distance). Empty glyph = no drawable route.
- **`RouteGlyphMaker`** (`Core/Journal/RouteGlyphMaker.swift`), its `Configuration` holding every
  number:
  1. parts: `PassportExploration.gapFreeParts` (reused, not copied); a part of one point is dropped;
  2. projection: local metres around the route's mean latitude (x east × cos φ, y south), north up;
  3. minimum span: the bounds grown to at least **300 m** about their centre, so a car-park shuffle
     is a small mark, never a shape filling the box;
  4. simplify for the size: Douglas–Peucker to a **point budget** per part (default 12…48 for a
     row, 24…96 for large art), by the budgeted search extracted from `DriveShapeMaker` into
     `RouteSimplifier` (one algorithm, two callers; the Feed's output must not move: its tests stay
     green unchanged);
  5. loop: start and end within **max(50 m, 4 % of the span)** → `isLoop`;
  6. fit into the unit box.
  - `glyph(for route: [RoutePoint]) -> RouteGlyph` and `glyph(for routes: [[RoutePoint]]) ->
    [RouteGlyph]` **in one shared frame** (the Day frame, D25: home, school and back meet where
    they really meet); the same steps, the bounds taken over all routes.
  - `scale(forDistance m: Double) -> Double`: the size by distance (D29), log scale, 1 km → 0.40,
    100 km and more → 1.0, clamped. `distance` is the GPS distance (`distance_m`), never the span.
  - Antimeridian: not supported (a route crossing ±180° draws across the box); stated in the doc
    comment and a test, as `AtlasRect` does for the Map.
- No clock, no location services, no I/O: tests feed it synthetic `RoutePoint`s.

### 2. Drawing (DesignSystem)

- **One curve.** `RouteCurve` (own file) becomes the single Catmull-Rom: `path(through:)` (kept for
  the share card) and `sampled(_:in:steps:)` moved from `FeedShapeCurve`, which keeps only the
  Feed's fade and draw-in progress (`fade`, `drawnSegments`) and calls it. `FeedShapeCurveTests`
  keep passing; the sampling tests move to `RouteCurveTests`.
- **One clearance.** `FeedTextClearance` becomes `TextClearance` (own file) with a generic
  `clearedAroundText()` mask; `feedShape(_:…)` uses it unchanged, and the Explore row (02b) gets the
  same rule: a route never crosses a line of text at full strength.
- **`RouteGlyphView`** (`DesignSystem/Components/RouteGlyphView.swift`): a `Canvas` drawing a
  `[RouteGlyph]` the Feed's way on the real shape: a faint ribbon, a halo in the ground colour, a
  thin Copper core, then the ends. Parameters are values, no boolean flags: `ink` and `ground`
  colours; a `RouteGlyphView.Style` (`.row`: 44 pt class, no fade; `.art`: large, fading toward the
  leading edge with the Feed's gradient mask); `tones` for several glyphs (the Day frame);
  `scale` (from distance) applied as inset. Still: nothing animates (resource rules).
- **Ends** through `RouteEnd` (after 02a·0: ring, dot, loop) at 6 pt in a row and 9 pt in large
  art: one source for route ends, as the design system requires (D32).
- **No cache beyond the view model's** (a safeguard names its risk): making a glyph is a few
  hundred operations on a route already in memory; it is made once per journey and revision when a
  page of rows is built (02b), off the main actor (`@concurrent`), and dropped with the page. A file
  cache would guard against nothing measured; the opt-in perf test (below) decides, and a cache is
  added only if it fails its budget.

### 3. Clean-up in the same change

- Remove `RouteThumbnail` (unused).
- `RouteShape` stays (the Passport's longest drive, the snapshot placeholder until 02b removes it).

## Tests

- `RouteGlyphMakerTests` (both sides of every threshold): empty and one-point routes → empty glyph;
  under 300 m → drawn at the minimum span, centred; just above 300 m → fills the box; aspect kept
  (a north–south road is tall, an east–west one wide) and cos φ applied (a square at 60° N stays
  square); a GPS jump → two parts, never joined; loop at 49 m / 51 m (and the 4 % side); point
  budget met for a 10,000-point route and a 3-point one; straight line keeps its two ends; shared
  frame: two routes meeting at a point meet in the glyphs; scale at 0.5 km, 1 km, 10 km, 100 km,
  500 km; antimeridian stated.
- `RouteSimplifierTests`: the budgeted search (moved), on planar points.
- `DriveShapeMakerTests`, `DriveShapeTests`, `FeedShapeCurveTests`: unchanged and green (regression:
  the Feed's shape must not move).
- `RouteCurveTests`: the sampling tests moved from `FeedShapeCurveTests` + `path(through:)` passes
  through every point.
- **Gallery (opt-in, not in `task test`)**: `RouteGlyphGalleryTests` renders the mockup's twelve
  edge cases and the Day frame with `ImageRenderer`, Light and Dark, to the scratchpad, for the
  owner to compare with the board. A second opt-in pass draws the glyphs of the pulled drives in
  `drive-data/` (read-only, `DriveDataReplayTests` style): images stay in the scratchpad, never
  committed (Development data).
- **Perf (opt-in)**: 2,000 synthetic journeys' glyphs made, Release, on the iPhone; budget
  ≤ 0.5 ms a glyph median; before/after numbers in the report.

## Docs (same commit)

- `docs/design-system.md`: a **Route glyph** section beside "Route line colours" and "Feed shape":
  what it is, where it is used, the Feed's drawing on the real shape, ends through `RouteEnd`, never
  on anything that leaves the device; "Feed shape" says its curve and clearance are shared code.
- `docs/architecture.md`, Algorithms: a row "A drive drawn without a map" naming `RouteGlyphMaker`
  (parts, cos φ projection, 300 m minimum span, budgeted Douglas–Peucker, loop rule, shared frame).
- No spec change: no screen changes in 02a.

## Acceptance

- `task lint`, `task warnings`, `task test` pass after the last change; Feed tests unchanged.
- The gallery matches the board's edge cases (the owner looks at the images).
- No screen changes; no schema, API, permission, entitlement or dependency change.

## Owner decisions

| ID | Question | Recommendation |
|---|---|---|
| D32 ✔ | Route ends everywhere | **Approved (owner, 2026-11-14; board `design/mockups/journeys/route-ends.png`): retire the flags on every surface.** The start is a **ring** (casing-coloured fill, Copper rim), the end a **dot** (Copper, haloed in the casing colour), a loop the ring with the dot inside; no shadow; sizes 6 pt (list glyph), 9 (large art), 12 (snapshots; 14 on the share card), 16 (maps). Shape tells start from end (Differentiate Without Color). Still one source: `RouteEnd` draws the new marks and `RouteEndMarker` shows them in SwiftUI maps, so every caller changes with it; the journey point card's `flag.fill` / `flag.checkered` become `circle` / `circle.fill`. A saved place at an end keeps `PlaceMapMarker`. Done as its own slice, **02a·0**, before the glyph |
| D33 ✔ | Merge the two Catmull-Rom curves (`RouteCurve`, `FeedShapeCurve`) in 02a | **Yes**: the reuse rule ("logic found twice is merged in the same change"); the Feed's tests guard against any visible change |

## Non-goals

Any screen (02b, 02c); the featured block's faded map (02b); the Day frame's highlight on tap
(D25, open); discovery (03); the share card's "Line" style (D22).

## Risks

- Moving the Feed's curve could move the Feed's drawing by a pixel: guarded by its tests and a
  before/after screenshot of the Feed (Light, Dark).
- `gapFreeParts` reads the display route, where a recorder gap routed straight looks like a road:
  such a gap is drawn joined, as the Footprint draws it. Acceptable for a glyph; stated in the doc.
- The 300 m minimum span and the loop radius are hypotheses, tuned with the gallery of real drives.

## Slices after 02a (for orientation, each its own plan)

- **02b Explore**: `JourneyRowModel` (ViewModels root), `ExploreJourneyRow` (time column, title,
  driving time, unboxed glyph, km), `JourneyFeature` (featured block with faded snapshot), day
  headers counting every drive; removes `JourneyMapThumbnail`, `JourneyCompactCard`, the overview
  card and `JourneyHeroCard`; splits what is left of `JourneyCards.swift`; `journeys.md` updated.
- **02c Day**: one drive → `JourneyFeature`; several → the compact timeline over the day frame;
  `journeys.md` updated.
