# Driving Passport V2

Status: Ready (2026-11-05; decisions applied the same day). Phase: 3 (slices 1–3), 4 (slice 4, with the Feed). Decisions:
carodo-ios ADR 0007 (privacy-first Feed), ADR 0013 (badges earned on the device). Visual idea:
`design/mockups/garage/passport-garage-overview.png`; this draft wins where they differ.

Each slice moves its part into `carodo-ios/docs/specs/passport.md` (and `garage.md`, `places.md`
where it touches them) in the change that ships it. When the last slice ships, this file goes.

## Purpose

The driver's own page, as a personal story rather than a second dashboard: what they drive
(**owned**: My Garage), where they have been (**explored**: Footprint and Places), and what they
have done (**recognised**: Highlights and Milestones). Private by default, offline, no account.

## Today (audit, 2026-11-05)

Code wins where this differs from `docs/specs/passport.md`.

- **Navigation is right:** Journeys' round stamp pushes `PassportView` (`AppRoute.passport`); the
  gear pushes Settings; Garage opens as a sheet at two thirds, as in the mockup (changed
  2026-11-05; it was a pushed `AppRoute.garage`), and each vehicle `AppRoute.vehicle(id)` inside it
  at full height.
- **Sections now:** Driver card (stamp, name, "Driving since", all-time distance · drives ·
  driving time), Month card (month totals with arrows), Driving calendar (month grid), Places
  visited (start/end place names by count), Garage (each vehicle with totals), Highlights (longest
  drive, longest streak, most-driven car, night drives). Empty journal: the booklet empty state and
  Garage.
- **Logic:** `PassportAnalysis` (pure: months, day distances, grid, streak, places, highlights)
  and `PassportViewModel`. The model loads **every** journey into memory
  (`journeyRepository.journeys()`), which does not scale (case E).
- **Repeats:** the Month card and the calendar repeat Journeys → Activity (month totals, heatmap
  calendar, `JourneyStatisticsService.month`).
- **Data that exists:** display routes per trip (`trips.route_simplified`) and the Map's
  `HistoryAtlas` (viewport, level of detail, Footprint squares on `AtlasGrid`); snapshot drawing
  (`JourneyMapSnapshotService`, `MKMapSnapshotter`); `trip_gaps` (`straight` = no plausible
  road); reverse geocoding of each trip's **first and last** point only (`geocoded_cells`:
  ward, locality, district, province, country); saved places (`places`) matched to each drive's
  ends when read (`SavedPlaceMark`); the night tag (`PartOfDay`, 21:00–04:00 local); the
  driving-day aggregate (`JourneyActivityDay`).
- **Missing capabilities** (reported, not to be faked):
  - Names of areas a route **passes through**: only the ends are geocoded. Explored Areas can
    count squares (`AtlasGrid`), not name them, until route geocoding exists (it would send more
    points to Apple: a privacy decision).
  - **Visits** as such: a drive's end is a visit candidate; a stop inside a drive is not recorded
    as a place.
  - An **achievement store**: `earned_badges` (ADR 0013) is not in the schema; nothing records
    which drive crossed a threshold.

## Behaviour

### Order, top to bottom

1. Driver Identity · 2. Your Footprint · 3. Places Visited · 4. Highlights & Milestones ·
5. Driving Rhythm · 6. My Garage.

(The mockup puts Rhythm before Milestones and has no Places row; this order is decided.)

General rules:
- **One set of totals.** All-time distance, drives and driving time appear once, in the Identity.
  No month card. Section captions describe the section, never repeat a figure shown above.
- **No card inside a card.** Each section is one surface (`carodoCard`) or none; a section with
  nothing true to say shrinks to one line, never an empty frame.
- **Loading and failure are not empty.** A section whose data is loading shows its frame with a
  quiet placeholder; a failed read shows a retry line in that section only. Garage reads vehicles
  on its own and shows even if journeys fail.
- A journey anywhere opens the shared journey detail. The floating bar stays hidden in the
  Passport space (as today).

### 1. Driver Identity (`PassportIdentityHeader`, `PassportLifetimeSummary`)

- The existing Passport stamp (never a generic avatar), the display name, "Driving since <month
  of the first drive>" (hidden with no drive), and a **Private** chip (lock + "Private"): the page
  is the person's only. @username under the name once they joined the Feed (ADR 0008).
- Lifetime summary three across: GPS distance, drives, driving time (moving time, as everywhere;
  `JourneySummary` from `JourneyStatisticsService.allTime`), zeros with no drive.
- Look: a subtle editorial band in brand tokens (Charcoal → Copper wash in Dark, Ivory → Copper
  in Light) behind the stamp. **No illustrated landscape or road** (the mockup's art reads as a
  route that is not the person's). Text keeps 4.5:1 on the band in both modes.

### Exploration group: Footprint, Explored area, Places — slice 2 (decisions 2026-11-05)

**Two definitions, never mixed.** *Passed through* is geometry: the Footprint routes and the
explored area say where drives went. *Visited* is a destination: only where a drive the person
drove **ended**. A route crossing 20 squares visited nothing; no POI is ever put on a square or a
route. This keeps the Passport ready to become a real exploration map later (stops, arrivals)
without inventing visits now.

**One scope for the group** (`PassportScope`): **All time** (default) · **This month** (the
current local calendar month, half-open, never rolling 30 days). One menu in the group's header
changes the map, the explored area, Places Visited and "new this month" together. The Identity's
lifetime totals never follow it. The choice lasts while the Passport is on screen and resets to All
time when it is opened again; no other month (that is Journeys → Activity).

#### Geometry rules (`PassportGeometry`, pure)

Applied in this order to each driven drive's display route in scope (pending and passenger drives
left out, as everywhere in the Passport):
1. **Split at impossible jumps:** two display points whose implied speed is above 70 m/s
   (252 km/h), or whose time does not move forward, start a new segment (a GPS jump is not a
   road). *Not* split by the recorder's gap rule (30 s and 300 m): the display route is simplified,
   so a long straight road is two points minutes apart, and the stored gaps (`trip_gaps`) point at
   raw samples, not display points. A GPS gap (a tunnel) is drawn as the Map and the thumbnails
   draw it. Known limit until gaps are kept against display points.
2. **Private regions redacted** (default on, no setting in V2): every live, non-dismissed private
   place (`is_private`: Home, Work, School, Family by default, and private areas) hides a circle of
   its radius around its **hidden centre** (the centre moved by its fixed `hide_offset`, as shares
   will use: the real centre is never the cut's centre). Points inside are dropped and the route is
   split there; pieces are never rejoined. Stored samples and routes are never changed.
3. **Segments of one point are dropped.**
Two drives are never joined; there are no start or end markers.

#### Your Footprint (`PassportFootprintPreview`)

- A static map image of the redacted segments in Copper, about 16:10, in the group's card.
- **Framing:** fits every redacted segment in scope with padding; distant drives are never dropped
  to improve the composition (a far trip widens the frame; the Map is where to zoom). A single
  short drive gets a minimum span (about 2 km).
- **Rendering:** `MKMapSnapshotter` off the main actor, reusing `JourneyMapSnapshotService`'s
  drawing; cached in memory and on disk by **(scope, route-data revision, privacy revision,
  appearance, size, scale)**. While a new image renders, the previous one stays with a subtle
  progress mark, and an image of the other scope is never shown as this one (it is dimmed with the
  mark until the right one is ready).
- **Tap → Map tab, Routes layer,** through a `MapIntent` (layer, scope, privacy: redacted): the
  Map shows the same scope, redacted, camera fitted to it, with a dismissible chip ("From your
  Passport · This month · Private areas hidden"). Closing the chip or leaving returns the Map to the
  person's own layer and view; the intent never writes the Map's saved preference.
- **VoiceOver** (verified data only, no coordinate, no private place): "Map of your drives, all
  time: 72 drives, around TP. Hồ Chí Minh" (the most frequent end province in the cache; left out
  when unknown). Hint: "Opens the Map".
- **States** (contextual, never a blank map, never a fictional route):
  | Situation | Shows |
  |---|---|
  | No drive ever | "Your footprint starts with your first drive" (no map) |
  | This month, no drive | "No journeys this month." |
  | Drives, no usable GPS route | "No route to show: these drives have no GPS route." |
  | Drives, everything inside private areas | "No route preview: your drives stay inside private areas." |
  | Loading | the card's frame with a quiet placeholder (or the previous image, as above) |
  | Failed | "Couldn't draw your footprint" with Retry, in the card only |

#### Explored area

- **km²** of the unique `FootprintGrid` base squares (zoom 17, about 300 m) the **redacted**
  segments in scope cross: the Map's own cell rule (`FootprintGrid.cells`), the area of each square
  at its latitude, summed once per square (no bounding box). Rounded for display ("38 km²", one
  decimal under 10). Hidden when it cannot be computed; never estimated. Square count only in
  Developer mode.
- Info (i) and VoiceOver: "Estimated area covered by map grid cells your recorded journeys have
  crossed." Never "visited".
- **Tap → Map tab, Footprint layer,** same `MapIntent` (scope, redacted).

#### Places Visited (`PassportVisitedPlaces`)

- **A visit** = a completed drive the person drove whose **last point** (the display route's
  last point, read without decoding the route) is the destination. Starts are not visits.
- **Which place,** most reliable first:
  1. **A saved place containing the end** (`PlaceMatch`: the smallest live, non-dismissed one).
     If the person saved it from an Apple Maps point of interest (`poi_category` set), its name is
     a *verified POI*.
  2. **The end cell's area name** from the geocode cache (`PlaceName.short`: neighbourhood or ward,
     else locality, else district), labelled as an area, never as a venue.
  3. No reliable name: the visit is left out of the list (counted nowhere), never "Unnamed place"
     chips. The cell's nearby POI (`geocoded_cells.poi`) is **not** used: a POI near a parking spot
     is no evidence of a visit.
- **Never listed:** private places (Home, Work and the like by default, and private areas), in the
  preview and in All places alike. A saved place with no drive ending in it is not listed.
- **Order:** most recent visit first; routine saved places (Home, Work, School) after the others.
- **Header:** "14 places" (the places listed in scope) and, when any, "3 new this month": places
  whose first visit in the whole journal falls in the current month (from the complete on-device
  history; shown in both scopes).
- **Chip:** symbol (saved place: its role or POI symbol; area: a map pin), name, "4 visits ·
  Nov 3". VoiceOver says "area" for an area name ("Tân Thuận, area, 4 visits, last on 3 November").
- **Tap → the most recent drive that ended there** (`AppRoute.journey`, a real journey id from the
  same visit set; never a drive that only passed nearby). Back returns to the Passport.
- **All places:** a pushed list with the same rows and rules when there are more than 8; each row
  opens the same drive.
- **Empty in scope:** "No places this month" / "No named places yet: places appear once your
  drives are named." Never "no data".

#### Conflicts and gaps found (audit 2026-11-05)

1. **No share-card redaction exists to reuse:** sharing is not built (`docs/specs/share.md`,
   Today); only the Privacy zone setting and the places' hidden-circle offsets exist. Slice 2 adds
   the pure `PrivateRegionRedaction` in `Core/Domain`, written for the share card to reuse (its
   start/end trim stays the share's own rule).
2. **The Map tab has no time scope and no redacted mode:** it shows all history, unredacted, and
   its layer is a saved preference (`carodo.mapVisualization`). Smallest extension: a transient
   `MapIntent` on `AppState` (layer, scope, privacy) that the Map applies without saving, a scope
   filter in its route read, redaction of its routes and squares while the intent holds, and the
   chip to leave it.
3. **Gaps cannot be found on display routes:** the display route is simplified (a straight road
   is two points minutes apart) and `trip_gaps` is keyed by raw sample sequences. Splitting by the
   30 s / 300 m rule on display points cut every straight road (seen on the first build); the
   Passport splits only at impossible jumps. Marking real gaps needs their times stored with the
   route (a later change).
4. **Trips store no end coordinate:** the last point is read from the display route's last 40
   bytes in SQL (`substr` on `route_simplified`), so no route is decoded for visits.
5. **Verified POI needs evidence:** the only reliable POI is a saved place made from a POI; the
   cell POI is set aside, so in practice most visits are area names until arrivals or stops are
   recorded as places.

#### Stages

- **2a, data and rules** (built 2026-11-05): `PassportScope`, `PassportGeometry` (gap split, redaction),
  `PrivateRegionRedaction`, explored area, visits and place resolution, ordering, journey link,
  "new this month"; repository reads (end point in SQL, driven routes in scope); tests.
- **2b, Passport UI** (built 2026-11-05; `docs/specs/passport.md`): the group card, snapshot with cache and states, Places row and All places,
  VoiceOver.
- **2c, Map intent** (built 2026-11-05; `docs/specs/navigation.md`, Opened from the Passport): `MapIntent`, scope and redaction on the Map, the chip, camera fit; tests.

### 4. Highlights & Milestones (`PassportHighlightStamp`) — slice 3

One row (horizontal) of stamps, highlights first, then milestones; "All" pushes the full page
(milestones in progress and locked, records). Copper ink on Ivory, stamp shapes from the Passport
marks (ADR 0013), no medals, no gold or silver.

- **Highlights** (personal records and memories; they can change, they carry no badge):
  First drive (date, distance), Longest drive (by GPS distance), Longest streak (days),
  Most-driven car, **First drive in a new province** (when the end cell's `province` is known and
  differs from every earlier drive's; never a district guessed from a ward).
- **Milestones** (ADR 0013 as revised 2026-11-05: cumulative distance only; tiers never go
  down): **Road Miles** (100 · 500 · 1,000 · 5,000 · 10,000 · 25,000 · 50,000 km) and **Faithful
  Car** (per vehicle: 1,000 · 5,000 · 10,000 · 50,000 km). Nothing else unlocks in V2.
- **Neutral statistics** on the All page, with no target, progress bar, lock or cheer: night
  drives (a start 21:00–04:00 local, `PartOfDay`), active driving days, longest streak.
- **States:** unlocked (inked, the date and the drive that crossed it), in progress (pencil
  outline with real progress, "640 / 1,000 km"), locked (outline, no progress when there is none).
- **Zero journeys:** a single locked **First drive** stamp with "Your first drive starts your
  passport"; no grid of zeros.
- **Journey Detail** shows a small "Milestone unlocked" stamp on the drive that crossed it (needs
  the drive recorded on the earned row; see Data).
- **Never** (ADR 0013): speed of any kind, time of day, driving frequency (drive counts, driving
  days), consecutive days, long-drive goals, rankings; no points, XP or levels.

### 5. Driving Rhythm (`PassportDrivingRhythm`) — slice 3

A strip, a fraction of Activity's height:
- **This week** (the user's first weekday): seven day chips with the Activity heatmap steps
  (`ActivityHeatPalette`, the same `JourneyActivityDay` aggregate; no new query logic), today
  marked, future days faint.
- Two figures at the trailing edge: **Days driven this month** and **Current streak** (labelled
  as current; the longest streak is a highlight, not repeated here). Both are plain facts: no
  flame, no "keep it going", no target, no celebration when a streak grows or breaks.
- No month picker (the mockup's "Nov 2026 ⌄" is dropped: browsing months is Activity's job), no
  per-day list. Tapping the strip does nothing in slice 3; a link to Activity waits for supported
  cross-tab navigation.

### 6. My Garage (`PassportGaragePreview`) — slice 1

- Always visible, with or without drives, loading or failed journeys.
- **With vehicles:** one row: "My Garage", "2 cars · 1 motorbike" (titled by what is in it),
  the primary (or last-used) vehicle's art (`VehicleArt`, the soft 3D look) and its name with two
  lifetime figures (GPS distance, drives); the row pushes `AppRoute.garage` (carousel, vehicle
  page unchanged).
- **No vehicle:** "Add your car" opening the existing add-vehicle flow.
- No odometer, fuel, maintenance or expenses here: they belong to Garage and the vehicle page.

### Empty and data states

| Case | Shows |
|---|---|
| A. No vehicle, no drive | Identity (zeros, no "since"), Footprint line, locked First drive stamp, Add your car |
| B. Vehicles, no drive | as A, with the Garage row and the real vehicle |
| C. Drives, no route | Identity totals, Footprint "No routes to draw yet", Places only from named ends, highlights and milestones that hold, Rhythm, Garage |
| D. Drives and routes | every section |
| E. Many drives | the same, read by aggregates: no full journey load, one cached Footprint image, 8 place chips, one stamp row |

Places Visited, Rhythm and Highlights hide (not an empty card) when they have nothing true:
Places with no named visit, Rhythm with no drive.

## Achievements: one model, three presentations — slice 3 (Feed in slice 4)

- **One engine,** `AchievementEngine` in `Core/Domain`: pure, deterministic, no SwiftUI, fed
  with drive facts (id, start, local day, GPS distance, vehicle, part of day, counts as driving)
  and place evidence; tested on both sides of every threshold. Feed and Passport never compute
  achievements themselves.
- **Two outputs:**
  - `PersonalRecord` (highlights): kind, value, the drive; recomputed from the journal, may move
    to a new drive.
  - `MilestoneProgress` (threshold achievements, ADR 0013 badges: cumulative distance only):
    definition id, metric value, tier reached, next threshold; an **earned tier** is stored with
    the date and the drive that crossed it, and never goes down.
  - Neutral statistics (night drives, driving days, streaks) come from the same facts but are
    never thresholds.
- **Three presentations:** Passport Milestones (all, with progress, private), Highlights (records,
  never badges), Feed badges (slice 4: only eligible unlocked tiers the person chooses).
- **Private by default.** Unlocking never posts, shares or reveals a route or a place. Future
  controls: share one achievement, show chosen badges on the public profile, revoke.
- Visibility per metric (ADR 0013): distance totals and a car's milestones may reach the Feed,
  only when the person shares them; time of day, places and anything a routine can be read from
  stay in the Passport.

## Data and privacy

- **Reads:** journey summaries, display routes (via `HistoryAtlas`), trip gaps, the geocoded end
  cells, saved places, vehicles. Aggregates and pure functions; nothing in a View.
- **New storage (P6, approved 2026-11-05):** `badge_unlocks` (immutable, with the drive that
  crossed each tier, `trip_id` ON DELETE SET NULL) and `badge_states` (seen, publication);
  `badge-ledger.md`. Footprint images are a disposable cache (Caches directory), never
  synced, never a source of truth.
- **No new network:** no geocoding on render; route geocoding (for named explored areas) is not
  part of V2.
- **Private:** the Passport is never synced as a page, never on the backend, never in the Feed.
- **Future Passport Snapshot (slice 4):** a share made from the Passport may carry only aggregate
  distance, aggregate drive count, city- or province-level summaries the person approves one by
  one, and selected milestones. Never raw coordinates, routes or the Footprint image, saved or
  private places, exact times or anything that reads as a routine (days of week, times of day).
  Exact at rest, coarse to others (P9).

## Slices

1. **Layout, Garage preview, empty states** (existing data; **built 2026-11-05**, in
   `docs/specs/passport.md`; the aggregate reads moved to 1b): new order; Identity with Private
   chip and band; Month card and calendar removed (they repeat Activity); existing Places and
   Highlights kept as they are until slices 2–3 replace them; Garage row; cases A–C; journeys
   read by aggregates instead of a full load.
1b. **Aggregate reads** (**built 2026-11-05**: `passportFacts()`, 53 ms on 5,000 drives against 292 ms; no rollup needed): the Passport stops loading every journey (`journeys()` decodes each
   route): repository reads for lifetime facts (first drive, longest drive, night count, streak
   days, per-vehicle totals, end-place counts) without routes. A 5,000-drive journal opens fast.
2. **Footprint + Places Visited:** route aggregation (split at straight gaps, passenger out),
   cached snapshot, visit rules, explored squares, All places when over 8.
3. **Highlights + Milestones + Rhythm** (**built 2026-11-05**, in `docs/specs/passport.md`; not yet: the moment animation, the 3D stamp, the ledger's iCloud records): `AchievementEngine`, the badge ledger (approved 2026-11-05),
   stamps and the All page, Journey Detail "Milestone unlocked", the Rhythm strip.
4. **Passport Snapshot and Feed badges** (later): once the data and the privacy boundary are
   stable; with the Feed's publishing.

## Decided (2026-11-05)

1. **7-day streak:** not an achievement, badge, unlock or reward; the streak is a neutral figure in
   Rhythm (current) and on the All page (longest).
2. **Night Owl:** removed (ADR 0013); night drives are a neutral count.
3. **Points and levels:** out of V2, with no infrastructure kept for them (ADR 0013).
4. **Driving days:** a statistic only, no tiers.
5. **Explored area:** km², from the Footprint grid's real square areas; hidden when unavailable.
6. **Footprint scope:** All time (default) · This month (current calendar month), kept while the
   Passport is on screen; no month navigation.
7. **Principle:** the Passport celebrates driving history without rewarding more, longer, later,
   faster or competitive driving. Badges in V2: Road Miles and Faithful Car only (ADR 0013).

## To decide before implementation

Nothing blocking. The badge ledger (`badge_unlocks`, `badge_states`), its merge rules, the
contract 0.24 badge endpoints and the vehicle archive were approved on 2026-11-05
([`badge-ledger.md`](badge-ledger.md); carodo-ios ADR 0013, 0014). Slice 4 builds the
publishing on that contract.

## Acceptance

- The stamp on Journeys still pushes the Passport; the gear still opens Settings; Back returns to
  the same place.
- Lifetime totals appear once and equal Journeys' all-time overview.
- A vehicle shows with zero drives; Garage and vehicle pages open as today.
- Footprint draws only stored routes: two drives never joined, a straight gap never drawn,
  passenger drives absent; the frame fits the routes; with no route, the compact line.
- A saved place with no drive ending in it never appears in Places Visited; visit counts equal
  the drives ending there; no name appears that the cache does not hold.
- Every highlight and milestone value traces to drives; a deleted drive leaves an earned tier;
  zero drives shows one locked stamp. Only Road Miles and Faithful Car ever unlock; night drives,
  driving days and streaks never show a target, progress or lock.
- Footprint opens on All time; This month changes the map and the explored area together and is
  the current calendar month; leaving and reopening the Passport returns to All time.
- Rhythm uses the Activity aggregate and is a strip, not a calendar.
- No speed figure, record or badge anywhere on the page.
- Offline, no account; Light and Dark; Dynamic Type to accessibility sizes (rows stack, the stamp
  row becomes a list); VoiceOver reads each figure with its name and each stamp's state and
  progress; Reduce Motion respected.
- Many drives (a synthetic 5,000-drive journal): the Passport opens without a full journey load,
  and the Footprint image renders once per revision.
