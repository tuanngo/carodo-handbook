# Map layers: legibility and places

Status: Approved (2026-11-18). Steps 1–3 done on branch `feat/map-look` (carodo-ios, worktree
`carodo-ios-map-look`, not merged): the owner tuned the look on the iPhone and the values are the
defaults (`852012b`, 2026-11-19): Discovery always on Apple's dark muted map with a 1 pt casing
under Explored and Familiar; far out 0.6× and Explored 85 %; Footprint a 25 %/30 % Copper wash, no
line per square, a 1 pt deep Copper outline, squares one level finer zoomed out. The lab is gone.
Also done there: the Passport's explained explored area (`ac59a69`) and its Footprint image faded
beyond the drives as the share card's, Apple's logo kept whole (`0bb57a8`, `MapVeil`). Dropped: the
Discovery fog (the dark map does its work, so no cost gate), the Charcoal fog (Apple's labels
haloed on it), Familiar's lift (it drew Familiar within ΔE 7 of Explored). Step 4, the Places
toggle, done there too (`45ae8cf`, 2026-11-19; simulator only, size by visits not built). Next:
merge into main (conflict expected in `MapAtlasView.swift`). Owner decisions:
places become a toggle of their own (a, 2026-11-18); the place callout is decided in a later
session from mockups (b); no Footprint share card (c).

## Problem

On the Map tab, Discovery and Footprint read faint on Apple's muted map, while a trip's share card,
also muted, reads well. Places show only on Footprint.

## Today (audited 2026-11-18)

- `CarodoMapLook.standard(mutesLight:)`: Discovery and Footprint use MapKit's `.muted` emphasis
  in Light too. It is a washed-out map, flat in luminance.
- `DiscoveryPalette`: New Copper (189,128,83) 3.5 pt on its casing; Explored Plum (155,100,190)
  3 pt; Familiar (98,45,135) 2.5 pt; no casing under Explored or Familiar.
- `AtlasZoomThinning`: at 60 km wide and more, lines at 0.45× and Explored at 0.6 opacity
  (`farExploredOpacity`).
- `AtlasOverlays` Footprint: squares filled with Copper 18 % (22 % dark) with a 0.6 pt hairline
  per square, under a fog of Ivory 70 % / Charcoal 60 % (`MapTuning.footprintFog*`). The edge of
  the driven area is drawn only by the hairlines of its squares.
- `ShareCardRenderer` (the card that reads well): Apple's default emphasis (`look: .journey`),
  half its saturation taken away (`mapSaturation` 0.5), a veil of the card's ground at 78 % away
  from the route (`veilOpacity`), the map whole in an 80 pt band along it, the route 3.5 pt on a
  5.5 pt Ivory edge. The contrast comes from the focus (map whole where the drive is, ghosted
  elsewhere), not from the line's colour.
- A veil over Discovery (two blended polygons) was measured on the iPhone (2026-11-15) and doubled
  the GPU. A band cleared along each road needed a renderer of its own. Both were dropped. The
  Footprint fog (one `MKPolygon` with a hole per square, normal blend) is the cheapest overlay.
- Places: `AtlasPlaceView` (`AtlasPointMarkers.swift`) on Footprint only, detected places
  clustered (`clusteringIdentifier`), saved ones never grouped.

## Proposal

### 1. Measure before changing (Developer only)

- **Fixed scenes:** the sample journal (`-carodo.sampleData YES`) on the simulator, one camera per
  zoom (about 15 km, 60 km, the country), Light and Dark, each layer. The screenshots stay in the
  scratchpad.
- **Script (scratchpad, not committed):** samples a line's pixels against the ground beside it and
  reports:
  - the WCAG contrast ratio, target ≥ 3:1 (non-text graphics);
  - ΔE2000 between the Discovery classes, target ≥ 20;
  - the same after a deuteranopia simulation.

  Footprint: the luminance step between a driven square and the fog.
- **A tuning panel in Developer:** sliders for the `MapTuning` and palette values below, applied
  through the `mapTuning` environment the struct was built for. The owner tunes on the iPhone, and
  the chosen numbers are written back as defaults. Debug only, in the composition root's reach;
  no launch flag in a view.

### 2. Discovery: the card's focus, cheaply

- **The Footprint fog under Discovery too:** the same one polygon, with a hole per driven square.
  The map stays whole where the person has driven and is ghosted elsewhere, as on the card. It
  reuses the squares already derived per journey, at the cost measured for Footprint. The fog must
  also be measured on the iPhone under Discovery.
- **A base map variant to compare in the panel:** Apple's default emphasis under the fog (the
  card's ground) against `.muted` today. The fog quiets the map's colour away from the roads; near
  them, check that greens and blues do not fight Plum.
- **A thin Ivory casing (about 1 pt) under Explored and Familiar,** as New has. It separates them
  from Apple's roads and labels.
- **A floor on width:** never under 2 pt far out. Explored's far opacity goes to about 0.85
  (`farExploredOpacity`).

### 3. Footprint: an edge to the territory

- **The outline of the driven area:** one Copper line, 1.5–2 pt, along the outer edges of the
  squares. An edge is outer when it has no square beside it, so it is computed once per answer with
  the squares. It replaces the hairline on every square.
- **The fill** goes from 18 % up to about 28–30 %.
- **The outline's colour in the panel:** Copper or a deep Copper. The stone-grey fog was dropped
  after the baseline (it lowers the contrast; see Baseline).

### 4. Places: a toggle (owner, 2026-11-18)

- **Places in the Layers popover,** a switch apart from the layer, remembered (a new UserDefaults
  key, a name that is data), on by default.
- **On:**
  - Saved places (Home, Work, …) show on every layer, small.
  - Detected places show on Routes and Footprint (owner, 2026-11-18, D2). Discovery stays
    about roads.
- **Ranked by `displayPriority`:** saved places are `.required`; places visited often are
  `defaultHigh`; places visited once are `defaultLow`. MapKit hides the low ones as markers
  collide, alongside the clustering kept today.
- **Size (optional):** the marker in up to three steps of visits.
- A journey's stops and breaks stay on its own page (ADR 0015). On the Map they are its detected
  places.
- Off: no place markers on any layer.

## Baseline (2026-11-18, simulator, sample journal, iPhone 18 Pro, iOS 27.2)

**Method:**
- Three cameras: the opening frame (a country), two pinches in (about 60 km) and four pinches in
  (about 15 km). Light and Dark.
- Discovery: the WCAG contrast of each class's colour, at its opacity, against the median of the
  map's own pixels in that screenshot.
- Footprint: computed from that ground with the fog and fill opacities in the code.
- The tool and the screenshots are in the session scratchpad (synthetic data, nothing
  committed).

The muted ground reads light green-grey in Light (about 237,245,227) and dark teal in Dark (about
35,75,73), not neutral grey.

| Scene | New (Copper) | Explored | Explored far (α 0.6) | Familiar |
|---|---|---|---|---|
| Light | 2.9–3.1 : 1 | 3.7–3.9 : 1 | **2.1 : 1** | 8.2–8.7 : 1 |
| Dark | 2.9–3.1 : 1 | 4.1–4.3 : 1 | **2.4–2.5 : 1** | **2.2–2.3 : 1** |

| Footprint | square ↔ fog | square hairline ↔ square |
|---|---|---|
| Light (Ivory fog 70 %, fill 18 %) | **1.16 : 1** | 1.6 : 1 |
| Dark (Charcoal fog 60 %, fill 22 %) | 1.70 : 1 | 1.6 : 1 |

**Read:**
- Discovery is legible near. It fails far out, where Explored fades to 60 % on lines 0.45× wide,
  and in Dark, where the deep Plum of Familiar sinks into the dark map. At 0.85 far opacity
  Explored reaches 3.0 : 1 (Light) and 3.4 : 1 (Dark).
- **Footprint in Light is the real failure:** the driven squares and the fog differ by 1.16 : 1.
  A stone-grey fog makes it worse (about 1.0 : 1), so that variant is dropped. An outline of the
  driven area in a deep Copper (about 140,88,52) reaches 5.2 : 1 against the Ivory fog, and full
  Copper 2.9 : 1. The outline, not the fill or the fog, is the lever.

## Non-goals

- The place callout and a bottom place card: next session, decided from mockups.
- A Footprint or Passport share card.
- Any change to the trip share card.

## Files

`DesignSystem/DiscoveryPalette.swift`, `DesignSystem/MapTuning.swift`,
`DesignSystem/Map/CarodoMapLook.swift`, `Features/Map/Views/AtlasOverlays.swift`,
`Features/Map/Views/AtlasMapView.swift` (renderer, places by layer),
`Features/Map/Views/AtlasPointMarkers.swift` (priority), `Features/Map/Views/MapLayersPicker.swift`
(toggle), `Features/Map/ViewModels/MapAtlasViewModel.swift` (the setting, places for every
layer), the Developer panel, `Core/Atlas/HistoryAtlas.swift` (squares for Discovery, the
outline), `Resources/Localization/Map.xcstrings`. Docs: `docs/specs/navigation.md` (Map, layers,
places), `docs/design-system.md#route-line-colours`.

## Acceptance

- In every measured scene, every line reaches ≥ 3:1 against its ground, and the Discovery classes
  stay ≥ ΔE 20 apart. The numbers are given before and after.
- On the iPhone, a screen at rest stays under 1 % CPU. The overlay count rises by at most one
  polygon per layer. The GPU is compared before and after (Instruments) on the same scene.
- The places toggle works on every layer and is remembered. Off draws no marker.
- Tests: the outline's edges (an isolated square, a hole, two squares at a corner), the priority
  by visits, and the setting's default.
- Light and Dark, xxxLarge (the popover), Vietnamese screenshots.

## Decided

- D1 (owner, 2026-11-18): the fog under Discovery, **only if it passes a cost gate on the iPhone**.
  Built first behind the Developer panel, then measured on one scene against Discovery today:
  - **Gate:** the screen at rest stays under 1 % CPU, and the GPU while panning and zooming rises
    by no more than about 15 % (Instruments, the same scene and gesture).
  - **Fails:** dropped, and Discovery keeps the casing and the width floor only.
  - **Why it may pass:** the dropped veil cost twice the GPU because it was two blended polygons.
    The fog is one polygon in the normal blend, drawn into the tiles MapKit caches, and nothing is
    drawn per frame. It is capped at 1,500 holes, merged coarser when zoomed out. Discovery goes
    from 4 overlays to 5.
- D2 (owner, 2026-11-18): detected places on Routes too.
