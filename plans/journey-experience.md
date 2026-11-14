# Journey Experience — audit and plan

Status: **Design contract approved** (owner, 2026-11-14): D12–D31 decided, mockup V9
(`design/mockups/journeys/journey-experience-v2.png`, source `design/mockups/source/journey-experience.html`,
synthetic routes only); D22 (a share card "Line" style) left for the share-card plan. No code changed. Next: the
02a plan. Concept:
[`../drafts/journey-experience.md`](../drafts/journey-experience.md). Milestone 01 of four
(Audit & design contract); 02–04 are planned below and start only after approval.

## Outcome

Explore and Day read as a travel journal instead of a data table: lists draw each drive's real
shape (Route Glyph) instead of near-identical map thumbnails, ordinary journeys are open rows
instead of cards, and one shared set of primitives keeps the two screens one family. Discovery
enrichment comes later as its own capability.

## Existing behaviour (files read)

carodo-ios at `055e6b3`; another session has uncommitted edits in `JourneyDayViewModel.swift`,
`JourneyCards.swift`, `JourneyHeroCard.swift` and `StatColumn.swift` (Dynamic Type step 2b): the
build slices must start after that lands.

| Area | What the code does today | Files |
|---|---|---|
| Explore | One scroll: overview stats card (all time) → `JourneyHeroCard` (180 pt real map) → month header with period menu → day headers → one `JourneyCompactCard` per journey, **each a card** (`carodoCard`, 18 pt corners) with a 56 pt `JourneyMapThumbnail`. Paged 20 at a time in a `LazyVStack` | `Features/Journeys/Views/JourneysView.swift`, `ViewModels/JourneysViewModel.swift`, `DesignSystem/Components/JourneyCards.swift` |
| Day | Calendar strip / month grid → `JourneyStatsBlock` totals card → one journey: `JourneyHeroCard` Day style (150 pt map); several: `JourneyDayRow`s (62 pt thumbnail) **inside one card** | `Views/JourneyDayView.swift`, `JourneyDayCalendar.swift`, `JourneyActivityCalendar.swift`, `ViewModels/JourneyDayViewModel.swift` |
| Thumbnails | `MKMapSnapshotter` per journey, size and appearance, three at a time, memory + Caches, keyed by journey and route (cache `version = 6`); while loading, the route is drawn as a faint `RouteShape` on a plain tile | `Core/Journal/JourneyMapSnapshotService.swift`, `RouteFraming.swift`, `JourneyCards.swift` (`JourneyMapThumbnail`) |
| Route shape in SwiftUI | `RouteShape(route:)` fits lon/−lat into the rect keeping aspect; no latitude correction, no minimum span (a 60 m drive fills the box), no parts, no end marks; re-projects on every layout | `DesignSystem/Components/RouteViews.swift` |
| Display route | `trips.route`: Douglas–Peucker at 8 m on completion, 40 bytes a point; read with each journal row | `Core/Domain/RouteSimplifier.swift`, `docs/data-model.md` (`trips`) |
| Place meaning | `SavedPlaceMark.ends(of:in:)` gives a drive's start and end place (label, symbol, role); the start mark already leads row titles; `DisplayFormat.journeyTitle` names "Home → Work" | `Core/Domain/JourneyDetails.swift`, `Core/Formatting/PlaceName.swift` |
| Parts | `PassportExploration.gapFreeParts` splits a display route at impossible jumps (the Footprint's rule); recorder gaps live in `trip_gaps` against raw samples | `Core/Domain/PassportExploration.swift` |
| Discovery sources that exist | milestones per drive (`badge_unlocks.trip_id`, shown on Detail by `JourneyMilestoneSection`); first visit to a place (`PassportExploration.VisitedPlaces.newThisMonth`); provinces along a route (`ProvinceBisection`, Detail only, budgeted Apple lookups over `geocoded_cells`); route heat (`RouteHeat`); routines (`Commute`); on-device narration (`Core/Narrative`) | as named |
| Discovery sources missing | stored "new territory" (`visited_cells` is reserved, unused, and on a different grid than the Footprint's `AtlasGrid`); notable roads, bridges, tunnels (no data source at all); a per-journey discovery store and its version | `docs/data-model.md` (`visited_cells`) |

**Name clashes found** (AGENTS.md: a new concept never takes an existing name):

- *Signature* is the Copper route style on every map (`JourneyRouteDisplay.signature`,
  design-system "Route line colours"). "Route Signature" for the list mark would make two
  Signatures → **Route Glyph** proposed (D15).
- `JourneyStorySheet` is Journey Detail's sheet; "story" also names the detail's page sections.
  "Journey Story" for multi-drive grouping collides → a new word needed (D16).
- `JourneyPresentationState` / `JourneyPresentation.swift` is the detail sheet's state;
  "JourneyPresentationModel" would read as part of it → **`JourneyRowModel`** proposed.
- `DriveShape` is the Feed's privacy shape (no north, ends cut, ADR 0007). The glyph must stay a
  separate type: it keeps north and its ends, and must never reach the Feed.

**Docs disagree:** `journeys.md` says `JourneyCompactCard` is used by "the Journeys list, the
Activity day and the Passport"; the code uses it only in `JourneysView`. Code wins; the spec is
corrected in slice 02b.

## Assumed, not checked

- That drawing a glyph from the in-memory display route is cheap enough per row with no cache
  beyond memory (measured in 02a before deciding).
- That removing per-row snapshots lowers memory and Caches use in Explore (to measure, same test).
- That Apple's geocoder answers are enough for "new province" / "first time in" discoveries; road,
  bridge and tunnel names are not available from what Carodo already calls.

## Owner decisions (each with a recommendation)

The owner's D1–D14 are taken as proposed, with these readings against the code:

| ID | Question | Recommendation |
|---|---|---|
| D1–D7, D9–D11, D14 | as proposed | accept |
| D8 | infinite scroll, all journeys | already true (pages of 20); keep |
| D12 | keep the Latest drive hero with its map | accept; **Day with one drive** drops its 150 pt map hero for the same timeline row as a busy day (D5, "no map in every row"); a one-drive day is not special |
| D13 | no speed, elevation, weather in Explore/Day | accept; the Latest drive hero's climb is removed too (it is Explore) |
| D15 | name of the list mark | **Route Glyph** (Signature is taken) |
| D16 | name of the multi-drive grouping | decide at milestone 04; "Story" is taken by the detail sheet. Candidates: *Trip*, *Chapter*, *Road trip* |
| D17 | Explore's all-time overview card (337 km · 6 drives · 9 h) | **move into the month header line or remove**; a figure card leading a journal is the dashboard feel the concept rejects. Passport keeps lifetime totals |
| D18 | Day's totals card | keep the three figures but **without a card**: a quiet line under the strip ("3 drives · 84 km · 2 h 10") |
| D19 | Place Glyph in 02 or later | **Revised by the owner (2026-11-14): no place symbol in a list glyph** (too small); the title keeps the place's symbol. Slice 02d is dropped |
| D20 | Contextual Map for Latest drive keeps `MKMapSnapshotter` | yes, now faded under the featured block (D28); the snapshot service stays for the hero, share card and Passport; only list rows stop using it |
| D21 | Do the Feed shape and the share card take the Route Glyph concept? | **One visual family, three separate concepts** (mockup, last board). The glyph is for the person's own screens only (north up, real ends, place symbols). The Feed keeps `DriveShape` unchanged (ADR 0007: no north, ends cut, no marks): merging would put real ends back into what others see. The share card keeps its map. Shared code only: one *route fitting* step (cos-latitude projection, minimum span, padding, parts) for the glyph and the card's offline plain ground; `RouteCurve` stays the soft curve of Feed and card; the glyph's ring and dot are the small sizes of `RouteEndMarker`. Anything that leaves the device takes the privacy trim and never a Place Glyph symbol |
| D23 | Explore layout | **Open editorial timeline** (owner, 2026-11-14, mockup V3): no card per journey or per day and no rule beside the day (owner, 2026-11-14: one thing too many); rows read time first ("07:21 · 5.2 km · 17 min") with a 56 pt glyph on a faint well; the month line "November 2026 · 412 km"; a discovery is an accent in the flow (one line under its row, or a typographic block for a multi-drive journey whose art is its own drives) |
| D24 | Latest drive | **Sentence case "Latest drive"**, no map (the map lives in Journey Detail): a **featured block** (`JourneyFeature`: kicker, title, figures, the route drawn large at the trailing edge). One component for Latest drive, a one-drive Day and "A journey worth remembering" (owner, 2026-11-14) |
| D25 | Day rows | **Two cases** (owner, 2026-11-14, mockup V4). *One drive:* the featured block (D24) with its time range as kicker. *Several:* the compact timeline (dot and hairline rail at the edge, time range in Copper, title, distance · driving time) over **one frame drawing every route of the day together** on their real geography, from the first row to the last, fading before the text. Open: whether tapping a row highlights its route in the frame |
| D27 | Route art style | **One drawing everywhere on the person's own screens: the Feed's** (a curve through the points, a faint ribbon under a thin core, a halo in the ground colour), on the **real geometry**, north up, **with a start ring and an end dot** (the Feed's style, never the Feed's shape: D21 stands). Large art (featured block, Day frame) also fades toward the text and never crosses a line of it. Explore rows draw it at 56 pt inside the faint well, no fade (mockup V5, option B, recommended over the crisp polyline A and the Feed's bleeding layout C). One drawing module serves all sizes; the Feed's stroke helpers become that shared code |
| D26 | The sketch's large title "Explore — Where have I been?" and mountain illustrations | **Left out**: AGENTS.md forbids large and decorative titles, and an illustration is not recorded data. Back only by a change to the design rules |
| D28 | A map under the featured block | **Yes, faded** (owner, 2026-11-14, mockup V6): the muted snapshot `JourneyMapSnapshotService` already draws, at about half strength, fading out toward the text and the edges (a radial mask), the route on top placed by the snapshot's own projection so line and roads agree. One component, so Latest drive, a one-drive Day and "A journey worth remembering" all get it. Offline or no tiles: the same block without the map (never a placeholder). Rows and the Day frame stay mapless. Check before shipping: Apple's attribution rules for a snapshot shown faded (TD-2) |
| D29 | Explore row design | **2 + 3 combined** (owner, 2026-11-14, mockup V8): a leading time column (secondary ink), the title with its place symbol, driving time under it (and a milestone on that line), the route bare and sized by distance (log scale: 1 km at 40 % of the box, 100 km or more full), and the GPS distance always as the trailing figure; no chevron (the whole row is the button); the recording-source symbol only on the detail (changes `journeys.md`); the day header adds the day's kilometres; rows 12 pt apart. At xxxLarge the title wraps, route and km keep the first line's trailing edge |
| D30 | The row's route has no frame | **Unboxed** (owner, 2026-11-14, mockup V9): no tile and no fixed square; the route keeps its own proportions, is sized by distance, sits just before the kilometres, may spill above and below its row into the space between rows (rows 14 pt apart, no hairlines), and fades toward the title with the Feed's mask. A day header counts every drive of the day, the latest one included, so its figures match Day |
| D31 | Large text | **Supported, not designed for** (owner, 2026-11-14: most people are under 50): every screen still works up to xxxLarge with no figure cut (AGENTS.md), but layouts are tuned at the default size and xxxLarge gets no bespoke design |
| D22 | A share card style with no map ("Line": the trimmed route on paper) | Optional, later (share-card plan): it also avoids Apple's map terms for images used outside the app (TD-2). Not part of this plan |

## Plan

### 01 — Audit & design contract (this document) ✔

Plus, before 02 starts: a mockup of Explore and Day with real glyphs, drawn from synthetic routes,
reviewed by the owner. **Drawn 2026-11-14** (`design/mockups/journeys/journey-experience-v2.png`):
Explore Light, Dark and xxxLarge; Day busy, one drive, empty and Dark; the glyph's edge cases at 44
and 56 pt; the route family (D21). The glyph there is computed by the 02a rule in JavaScript, so the
board doubles as a reference for the Swift tests. Feedback on it changes the board, not code.

### 02 — Journey visual foundation (no enrichment, no schema change)

Four slices, each run, screenshotted and committed on its own.

- **02a Route Glyph primitive.** A pure geometry step in `Core/Journal` (beside `RouteFraming`):
  display route → parts (`gapFreeParts`) → equirectangular projection with cos(latitude) →
  minimum span (≈ 300 m) → fit with fixed padding → simplify to a point budget for the size →
  loop detection (end within ~50 m of start). A SwiftUI `RouteGlyph` view in `DesignSystem`
  strokes it (Copper, round caps) with start dot and end mark. Kept in memory keyed by
  (journey id, journey revision, size bucket, style). Unit tests: empty, one point, under 50 m,
  very short, straight line, loop, a jump splitting parts, high latitude aspect, antimeridian not
  supported (stated). An opt-in perf test: 2,000 synthetic journeys' glyphs, before/after numbers.
  `RouteShape` stays for the Feed shape and share card; the snapshot placeholder may adopt the
  glyph geometry (one projection rule, not two).
- **02b Explore open list.** `JourneyRowModel` built in `JourneysViewModel` from the journal read;
  shared primitives `JourneyTitle`, `JourneyMetrics`, `JourneyTimeRange`; `ExploreJourneyRow`
  (glyph 44 pt, title, distance · duration, start time, status marks) with no card, hairline or
  spacing separators; month and day headers kept; overview per D17; hero spacing/typography pass,
  climb removed (D13). `JourneyCompactCard` removed if nothing else uses it.
- **02c Day open timeline.** `DayJourneyRow` on the same model: start–end time leading, a thin
  vertical rule linking rows (no inferred events between them), glyph, title, distance ·
  duration; no wrapping card; one-drive day uses the same row (D12); totals as a line (D18);
  empty state kept.
- ~~02d Place Glyph~~: dropped (D19 revised).

Each slice updates `docs/specs/journeys.md` and, for 02a, `docs/design-system.md` (a "Route Glyph"
section beside "Route line colours" and "Feed shape"), in the same commit.

### 03 — Discovery engine (needs P6 approval: schema)

Start with the sources that already exist and are verified; one discovery kind per slice.

- A per-journey discovery result with a rules version (`discovery_version` on `trips`, local
  bookkeeping like `points_version`, never synced) and a small table of highlights keyed by
  (trip id, kind, subject) so a re-run never duplicates. Schema: `v1_initial` edited in place
  (pre-release), owner approval first.
- Kinds in order: **milestone** (from `badge_unlocks`, no new data), **first visit to a saved or
  detected place**, **first time in a province** (from `geocoded_cells`, extending the existing
  bisection budget to new drives only), **new ground** (needs `visited_cells` on the Footprint's
  grid; decide the grid first).
- Backfill newest first in batches, resumable; deferred on expensive/constrained networks
  (`NWPath.isExpensive`/`isConstrained`); no placeholder in Explore.
- Notable roads, bridges, tunnels: **not planned** until a data source is chosen (a new cloud
  service or dataset is a P6 decision).

### 04 — Journey storytelling (future)

Multi-drive grouping (D16), highlights ranking and deduplication, Explore integration; only when
03's data has proven reliable on real history.

## Acceptance (milestone 02)

- Explore: no card around ordinary journeys; no map image in any row; Latest drive keeps its map.
- Day: no card around the journeys; a one-drive day uses the timeline row.
- The glyph matches the route on Journey Detail for the drives in `drive-data/` (checked locally,
  screenshots kept in the scratchpad only), including the shortest, a loop and one with a GPS jump.
- Explore with 2,000 synthetic journeys scrolls with no hitch on the iPhone (opt-in test, Release,
  numbers before and after).
- `task lint`, `task warnings`, `task test` pass; screenshots Light, Dark, xxxLarge, Vietnamese for
  Explore and Day with none, one and several drives.

## Non-goals

Search, Feed, Journey Detail layout, the Map tab, any network call in 02, any schema change before
03, AI narration in lists.

## Risks

- Removing thumbnails removes context some drives need (two different drives with the same shape,
  e.g. Home → Work and back, look alike mirrored). The title (with its place symbol) carries that; to check
  in the screenshot review.
- A glyph of a real route is location data on screen: fine on the person's own screens; it must
  never be reused for the Feed, a share link or a notification without the privacy trim.
- Parallel edits in `JourneyCards.swift`, `JourneyDayViewModel.swift`: 02 waits for them.
