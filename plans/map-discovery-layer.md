# Map · Discovery layer ("Roads you've discovered")

Status: **committed** (carodo-ios `08a6216`, 2026-11-15); device checks in PV-24; colours chosen on the iPhone (TD-33 resolved, carodo-ios `b2fa3b5`: Plum on a muted map, New solid). Approved: every
recommendation, D1–D5. Slices 1–4 built in carodo-ios in one change (counting, atlas, screen, docs);
lint, a clean build with no warnings and the full suite (2,214 passed, 19 skipped) pass. The
palette below is in the code as the starting point; the owner picks colours and widths on the
device with real drives (owner, 2026-11-15: "choose the colours once it is on the map"), then it
is committed. Open: PV-24 in [technical-debt.md](technical-debt.md).
Mockup: [`design/mockups/source/map-discovery-layer.html`](../design/mockups/source/map-discovery-layer.html)
(synthetic town; today's Heatmap beside looks A and B, light and dark map).

## Frame

**Outcome.** A Map history layer, **Discovery**, that colours every road the person drove by when
they first discovered it and how familiar it is, in three classes, so a heavily driven area no longer
turns dark and the newest roads stand out. The Heatmap leaves the layer picker.

**Why.** The Heatmap's ramp darkens with every drive: on a light map 20+ drives are charcoal brown
and the person's commute dominates everything else (mockup, "Today").

**Acceptance criteria**

1. Layer picker: Routes · Discovery · Footprint. Discovery's legend has three rows:
   New roads (first driven in the last 30 days), Explored (first driven earlier), Familiar (driven
   often). English and Vietnamese.
2. One road reads in one class whatever the number of drives on it: nothing darkens with
   repetition. New draws on top, Familiar at the bottom and never wider than Explored.
3. Classification is derived on device from the stored display routes, passenger trips excluded
   (as the heat map today); nothing new is stored, nothing new leaves the device.
4. The 30-day window moves with the local day: a road crosses from New to Explored on the day it
   turns 31 days old, without a relaunch.
5. Budget as the Heatmap's today: nothing computed until Discovery is first shown; one drive added
   or removed costs O(k) for that drive; pan and zoom read only the cache. First Discovery view of
   2,000 synthetic drives within 20 % of today's first heat map (`HistoryAtlasPerformanceTests`,
   `CARODO_PERF=1`, Release, same simulator), then measured once on the owner's iPhone.

**Non-goals.** Map matching to a real road network; a stored `visited_cells` table; sharing or
Feed use of discovery data; a "new roads this month" statistic or badge (a later Passport idea);
changing Routes or Footprint.

## What the code does today (read 2026-11-15)

| Fact | Where |
|---|---|
| Heatmap is lazy: `heatIndex` is nil until the layer is first shown; while another layer shows, no heat is counted, kept or drawn. Hiding it costs nothing at runtime. | `Core/Atlas/HistoryAtlas.swift` (`heatLines(in:)`, `heatIndex`) |
| Counting: a 20 m grid (`HeatGrid`), each drive adds 1 to every cell in the 3 × 3 neighbourhood of a cell it crossed, once per drive; packed `UInt64` cell keys, flat count arrays, journeys indexed per 16 × 16 block; add/remove is incremental and reports only the journeys whose drawn runs change. This **is** the spatial index and the "road segment" store: a cell plus its neighbours is our road segment. | `Core/Domain/RouteHeat.swift` (`RouteHeatIndex`) |
| Drawing: each journey's route is split into runs where its level changes; runs shorter than 2 cells are absorbed; one `MKMultiPolyline` per level, quietest first (ADR 0015). | `RouteHeatIndex.runs(for:)`, `Features/Map/Views/AtlasOverlays.swift` |
| Viewport + zoom: one padded area asked once the camera settles; lines thinned per `AtlasDetail` (stored route close up, 12 m city, 35 m far, turns over 22° kept); answers cached by mode, viewport and revision (16 entries). A bounds scan over 2,000 drives is ~3 ms, so the docs record that the Map needs no R-tree. | `HistoryAtlas.layer(_:in:)`, `AtlasGrid.swift`, `docs/specs/navigation.md` (History at scale) |
| Inputs: `JourneyRoute` carries id, version, display route, `isPassenger`; **no date**. Read by `routes(skipping:)`, which decodes only changed routes. | `HistoryAtlas.swift`, `Core/Persistence/GRDBJourneyRepository.swift:235` |
| Layer choice persisted as the raw value in UserDefaults (`visualizationKey`); an unknown value falls back to Routes. | `Features/Map/ViewModels/MapAtlasViewModel.swift:236` |
| Colours: `DriveHeatPalette` (5-level light and dark ramps, widths 3 + 0.6·level); `CarodoColor.copper` is exactly #BD8053; `CarodoColor.stone` is #77736D (not the proposed stones). | `DesignSystem/DriveHeatPalette.swift`, `DesignSystem/CarodoColor.swift` |
| Measured (2026-11-07, Mac simulator, Release, 2,000 synthetic drives): first heat map ~290 ms after the index rewrite; one more commute ~1 ms. Never measured on an iPhone. | `docs/specs/navigation.md` |

## Answers to the owner's questions

**If the Heatmap is hidden, is it still loaded?** No. Its counts are built only the first time the
layer is shown, and nothing else reads them. Hidden, it is dead code, not a cost. Since the repo
rules say a removed feature takes what only it used, the recommendation is to **replace** it, not
hide it: Discovery reuses the counting (`RouteHeatIndex`); the 5-level `DriveHeatLevel`,
`DriveHeatPalette` and the "Drives" legend go. A saved choice of `heatmap` opens Discovery
(the raw value is data, AGENTS.md iOS invariant 8: it is mapped, never reused for something else).

**Precomputed data + viewport rendering + zoom-adaptive detail?** Yes, and it is already how the
Map works: derived once off the main actor (`HistoryAtlas` actor), kept, updated per journey;
pan and zoom ask one padded area once the camera settles and read thinned, cached lines. Nothing is
recomputed from GPS samples on a camera move (only display routes are ever read). Discovery plugs
into the same path as one more mode.

**Spatial index?** We have the one that fits: the cell hash (packed key → slot) for counts and the
16 × 16 block index for "which journeys pass here". An R-tree or quadtree is not needed for 2,000
drives (bounds scan ~3 ms); it is listed in `docs/architecture.md` as the tool only for thousands
of polygons. Reconsider only if a device measurement says otherwise.

**A `visited_cells` table, or `firstDiscoveredAt / lastTraversedAt / traversalCount` per road
segment?** Keep these **per cell, in memory, derived**, not in the database, for now:

- `traversalCount`: exists (distinct drives per cell neighbourhood).
- `firstDiscoveredAt`: new, the earliest start time among the drives covering the cell. The only
  field Discovery needs that we lack.
- `lastTraversedAt`: not needed by the three classes. Left out (no field without a reader); cheap
  to add the same way if a "fading roads" idea comes.

Why not a table now: it would be a schema change (P6) holding derived data that must be rebuilt
on every edit, trim, join, delete, restore and iCloud change, and must never sync (it is a function
of trips that already sync). The in-memory rebuild is ~0.3 s for 2,000 drives on the simulator.
**When a table would be right:** if the owner's iPhone takes more than ~0.5 s for the first
Discovery view (Release), a rebuildable cache table keyed by the rules version, local only, in its
own ADR. "Road segments" from a real road network would need map matching against OSM or a
service: a new dependency (P6) and, as a service, sending routes out (P5). The 20 m cell with its
neighbourhood stays our segment.

## Proposal

### Classification (pure, deterministic, `now` and calendar injected)

For a cell with `count` distinct drives and `firstSeen` (earliest drive start among them), against
`asOf` = start of the local day:

| Class | Rule | Precedence |
|---|---|---|
| New roads | `firstSeen ≥ asOf − 30 days` | first: a road discovered this month is New however often it was driven since (a new commute stays New for 30 days) |
| Familiar | not New, `count ≥ 6` | second |
| Explored | everything else | — |

Thresholds (30 days, 6 drives) live in a `Configuration`, are tested on both sides, and are
recorded as hypotheses in `docs/specs/navigation.md`. 6 is where the Heatmap's "6–10" begins.

Removal: `firstSeen` is a minimum, so removing a drive cannot just subtract. When the removed
drive was the minimum of a cell, recompute that cell from the drives the block index lists there
(O(k · drives in those blocks)); the other fields update as today.

Day change: classes depend on `asOf`, so the cache key gains it; on a new local day, runs are
placed again for drives whose cells cross the 30-day line (or all drives, if that measures under
50 ms; decide by measurement in slice 1).

### Rendering

Three `MKMultiPolyline`s, Familiar, then Explored, then New on top (ADR 0015: a handful of
overlays). Same thinning, viewport and casing rules as today (Charcoal casing on imagery, 55 % in
3D). Colours and widths: the owner picks from the mockup (decision D3 and D4).

| | Light map | Dark map, Satellite, Hybrid |
|---|---|---|
| New roads | Copper #BD8053 (= `CarodoColor.copper`) | Copper, or a lifted #D08A58 (mockup) |
| Explored | Warm Stone #B5A08C | Warm Stone #B5A08C |
| Familiar | Deep Stone #88786B | Deep Stone #88786B |

On a dark ground the darker Familiar already recedes; on a light map it stands out more, which is
why look B draws it thinner. A new `DiscoveryPalette` in `DesignSystem/` replaces
`DriveHeatPalette`; whether Warm and Deep Stone become named `CarodoColor`s is D4.

### Legibility on Apple's maps (measured 2026-11-15)

Contrast (WCAG ratio) of each line colour against the ground of real MapKit screenshots, a 3 km
city view on the iOS 27.2 simulator with the sample journal (synthetic), line pixels excluded;
median ground, and for imagery against the Charcoal casing the Map already draws there. 3:1 is the
usual floor for a line that carries meaning.

| Colour | Light | Dark | Hybrid / Satellite ground | On the Charcoal casing |
|---|---|---|---|---|
| Copper #BD8053 | 2.9 | 4.2 | 1.7 / 2.4 | 4.5 |
| Lifted copper #D08A58 | 2.5 | 4.9 | 2.0 / 2.8 | — |
| Deep copper #AC6230 (the heat ramp's level 2) | **4.1** | 3.0 | — | — |
| Warm Stone #B5A08C | **2.2** | 5.5 | 2.2 / 3.2 (1.0 on bright roofs) | 5.9 |
| Deep Stone #88786B | 3.8 | 3.3 | **1.3** / 1.9 | 3.5 |

Readings:

- **Dark map:** works as proposed; the darker Familiar recedes, as intended. New reads best in the
  lifted copper.
- **Light map:** Explored is faint (2.2) and close to Apple's beige land; Brand Copper for New is
  2.9 and only 1.3× Warm Stone's luminance, so New and Explored differ by hue alone. A darker
  Explored cannot fix both: at 3:1 it has Copper's luminance. Proposed: New in deep copper #AC6230
  on the light map (4.1, 1.8× Explored), Explored stays quiet, Familiar stays 2.5 pt.
- **Satellite and Hybrid:** the stones are the colours of concrete, roofs and dirt (Deep Stone 1.3
  on Hybrid); without the casing they vanish. The existing Charcoal casing is required for all
  three classes there, and the dark set is used.
- **Colour vision:** on the light map deep copper and Deep Stone have the same luminance (1.1×);
  width (4 / 3 / 2.5 pt) and New drawn on top carry the difference. Slice 3 checks a greyscale
  screenshot.
- **3D:** history lines draw at 55 % width, so Familiar becomes ~1.4 pt; slice 3 checks it and
  floors it if it disappears.

Proposed palette (`DiscoveryPalette`, light / dark-and-imagery):
New #AC6230 / #D08A58 · Explored #B5A08C / #B5A08C · Familiar #88786B / #88786B; widths 4 / 3 /
2.5 pt; Charcoal casing on imagery as today.

## Slices

1. **Counting (pure).** `RouteHeatIndex` keeps `firstSeen` per slot beside `counts` and takes each
   drive's start; `DiscoveryClass` + `Configuration`; runs split by class instead of heat level;
   removal recompute; `DriveHeatLevel` removed. Tests: 30-day edge (29 d 23 h / 30 d / 31 d,
   across a DST change), count 5 / 6, New beats Familiar, removing the earliest drive moves
   `firstSeen` to the next, passenger excluded, day change re-classifies. Perf test updated and run.
2. **Atlas + data.** `JourneyRoute.startedAt` (from `trips.started_at` in `routes(skipping:)`'s
   existing query; no schema change); `MapVisualizationMode.discovery`, `heatmap` mapped to it on
   read; `HistoryAtlas` mode, cache key with `asOf`.
3. **Screen.** Picker row (title, one-line detail, symbol), three-row legend, `DiscoveryPalette`,
   `AtlasOverlays`, strings EN + VI in `Map.xcstrings` (heat strings removed). Simulator screenshots:
   light, dark, Satellite, xxxLarge, Vietnamese.
4. **Docs, same change.** `docs/specs/navigation.md` (Layers, History at scale),
   `docs/architecture.md` (the "Route heat" algorithm row becomes "Route discovery"),
   `docs/design-system.md` (palette). Device check: first Discovery view time and idle CPU on the
   owner's iPhone with their journal.

Files: `Core/Domain/RouteHeat.swift`, `Core/Atlas/HistoryAtlas.swift`,
`Core/Persistence/GRDBJourneyRepository.swift` (routes query), `Features/Map/Views/{MapAtlasView,
MapLayersPicker, AtlasOverlays}.swift`, `Features/Map/ViewModels/{MapAtlasViewModel,
MapExperience}.swift`, `DesignSystem/DriveHeatPalette.swift` → `DiscoveryPalette.swift`,
`Resources/Localization/Map.xcstrings`, tests `RouteHeatIndexTests`/`RouteHeatTests`,
`HistoryAtlasTests`, `AtlasOverlaysTests`, `MapAtlasViewModelTests`, perf test.
No schema, API, permission, entitlement or dependency change.

## Assumed, not checked

- The first Discovery build costs about the same as the first heat map (one extra `Double` per
  slot and a `min`); slice 1 measures it.
- `trips.started_at` is in the same row `routes(skipping:)` already reads; reading it adds no
  decode cost worth measuring.
- How Deep Stone reads on Apple's real Standard map (the mockup's base map is drawn by hand):
  screenshots in slice 3 decide.

## Decisions for the owner

- **D1 · Heatmap:** replace it with Discovery (recommended: no runtime cost either way, but hidden
  code is code to keep), or keep it hidden behind Developer.
- **D2 · Familiar threshold:** 6 drives (recommended, matches the heat ramp), 5, or 10. Window for
  New: 30 days from the start of the local day (recommended).
- **D3 · Look:** A (Familiar = Explored width) or B (Familiar 2.5 pt, New cased) — recommended B.
- **D4 · Colours:** New = Copper on both grounds, or the lifted copper on dark; Warm/Deep Stone as
  new `CarodoColor` tokens (recommended, they are shared design values) or private to the palette.
- **D5 · Name and copy:** "Discovery" in the picker, detail "Roads you've discovered"; Vietnamese
  proposed: "Khám phá" / "Những cung đường bạn đã đi qua"; legend "Đường mới · Đã khám phá ·
  Quen thuộc".

## Owner changes after the build (2026-11-15)

- The New window is **14 days**, not 30: with 30, every drive the owner had recorded (all since
  30 Oct) was New, so Discovery looked like the Routes layer.
- New takes the **Routes layer's Copper (#BD8053) with a glow**, as the share card's Glow line:
  the Copper drawn twice under the line (3× and 2× its width, 14 % and 30 % opacity, three quarters
  of that on a light map). Stacked strokes, not a blur: MapKit redraws overlay tiles at every zoom.
  The legend's New swatch glows too. Discovery is now at most 5 overlays.
- On returning to the app on a new day the Map redraws once, so the window moves without a pan.
- Explored and Familiar are a **slightly cool grey** (light map #80848A / #4A4D52, dark map
  #B0B4BA / #80848C), not the warm stones: on the simulator the stones sank into Apple's warm map.
  A brown ramp (copper fading with age) was compared too and dropped: New lost its place among
  browns and a deep brown Familiar read as the Heatmap again. Copper is the one warm colour left.
- **Greys dropped on the owner's iPhone** (same day): zoomed out, a grey Explored line on a highway
  read as Apple's own grey highway. Explored and Familiar are now the **drained copper** ramp
  (light map #967864 / #695244, dark map #C8A88C / #967A64): Apple's maps draw nothing brown.
- On the iPhone, zoomed out, Explored still did not read: the colour search for Explored and
  Familiar moved to **TD-33**; the drained copper stays as a placeholder. The legend shows only
  the three names (New roads, Explored, Familiar), no description lines (owner, 2026-11-15).

