# V2.3.3 — Journey Points, Nearby POI, Footprints

Status (2026-11-10): **Slices 1, 2 and 3 are built; device checks PV-12 and PV-13 are open; Footprints is next.**
This is V2.3.3's only plan. The behaviour built is in carodo-ios `docs/` (the source of truth); this plan records only
the scope, the owner's decisions and what is still waiting.

## 1. Product

**Carodo remembers the roads we drove and the places we stopped. Apple Maps helps name the places nearby.**

- **Journey:** GPS, route, trip; it has a Start, an End, Stops and Breaks.
- **Map:** explore one Journey Point. Shows the GPS position Carodo recorded or inferred; Apple Maps adds the address and
  a Nearby POI when it can.
- **Footprints:** a map of the history of the roads driven and the places stopped at, on the existing Footprints layer,
  with no new Map Mode.

## 2. Terms

Canonical definitions: carodo-ios `docs/specs/domain.md` (Vocabulary). Use only: **Journey**, **Journey Point** (Start /
End / Stop / Break), **GPS Position**, **Nearby POI**, **Footprints**, **Saved Place**.

- A Nearby POI is a place Apple Maps found near the GPS Position: "Near / Gần", never "At / Tại". It is not a check-in,
  not a place visited, and never becomes a Saved Place.
- Saved Place keeps its current meaning (saved by the person; privacy, Auto Mode).
- The `geocoded_cells.poi` column (the reverse geocode's `areasOfInterest`) is not a Nearby POI and not a place visited.

## 3. Slices

| Slice | Content | Status |
|---|---|---|
| 1 | Stop and Break open on the Map tab: focus, GPS marker, position circle (`StopPosition`), native preview, Find nearby places, apart from the Live Map | Done: `3aa3e25` (the fullScreenCover version), `e027155` (Map tab) |
| 2 | Automatic Nearby POI for Stops and Breaks | Done: `f66dcfa`. Waiting for PV-13 |
| 3 | Start and End open on the Map | Done: `193d6ca`. Waiting for the device (PV-12) |

### Slice 2 (built)

Canonical spec: carodo-ios `docs/specs/journey-detail.md`, Where a stop was (preview, Nearby POI, Find nearby);
`docs/specs/navigation.md`, Journey points on the Map (focus, marker, camera); `docs/privacy.md` (what a request sends to
Apple); ADR 0015.

Decisions in short (owner, 2026-11-09): opening a Journey Point on the Map is the request; privacy is checked first (fail
closed), then **one** request is sent; `StopPlaceResolver` names **at most one** POI when all five conditions hold (enough
position evidence, not a public station or car park, duplicate names merged, close enough, not ambiguous). No score, no
ranking, no Confirm/Change/Remove. Cached in RAM per Journey Point for the app session; no persistent cache, no schema, no
sync, no `.carodo`. Find nearby places stays as secondary exploration.

Why the five conditions stay: a replay against real Apple Maps on 24 dev stops: loosening them named 9/24, 3 of them wrong
(a grocery, an office at a red light). The current thresholds: 0/24, each for a sound reason (14 imported stops with sparse
fixes, 10 Carodo stops of 1–3 min in busy streets with 2–4 places within 6–20 m). **Not yet proven effective**: there is
no stop ≥ 5 min recorded by Carodo yet (PV-13).

### Slice 3 (Start/End, built)

How (2026-11-10): Start/End are `JourneyPoint`s (`.start`, `.end`) on the timeline; the Map places them on the first/last
fix of the trimmed track (`JourneyPointTrack`), and the address is read from that fix's cell (the same as
`start_cell`/`end_cell`). The Start is estimated when a `TripGap.outsideStart` lead-in reaches the first kept fix: its
position is the route's first point, with no circle, no coordinates, no Nearby POI, and an "Estimated" line. Marker: the
route flag, or the Saved Place's `PlaceMapMarker`. The address Apple returns is kept in `StopPlaceMemory` (RAM). Inside a
private Saved Place the preview shows no coordinates (Stops too).

The original decisions (owner, 2026-11-09):

- Start and End are Journey Points like Stop and Break: the same `JourneyPoint`, the same path to the Map.
- **A Start with recorded GPS:** look up a Nearby POI through the same privacy and quality gates.
- **An estimated Start** (the Auto Mode lead-in drawn from the parking spot to the first fix, `missedStartM`): still
  viewable on the Map, **no** automatic POI lookup; the UI says plainly that the position is estimated. `JourneyPoint`
  carries the position's source (recorded / estimated).
- **End:** one fix (the last kept fix), with the Break's gate: accuracy ≤ 20 m, searched within 25 m.
- GPS that does not qualify for a POI lookup never takes away viewing the position on the Map.
- The address comes from `trips.start_cell` / `end_cell` (`geocoded_cells`, already there when the journey is saved); no
  new reverse geocode.
- Follows the trimmed journey (like the detail page). A private Saved Place: no address, no lookup, nothing sent.
- A small optimisation along with it: keep the reverse-geocoded address in `StopPlaceMemory` (RAM, like the Nearby POI),
  because today reopening the same stop in a session geocodes again. No schema, no new framework.

## 4. Footprints (after V2.3.3)

Put past Starts, Ends, Stops and Breaks on Footprints: clustered when zoomed out, single markers when zoomed in; tapping a
marker shows the time, the position and the journey; a Nearby POI only when the person opens that point. The source is
Carodo's journeys/GPS/Smart Stops, not Apple Maps. The meaning of explored area is unchanged. Follows the History at scale
principle (navigation.md).

Known (audit 2026-11-09): stops are not stored; recomputing them from the raw track takes about 4.5 ms per 1,000 fixes
(Debug, simulator); 2,000 trips are estimated at about 1.5 s optimised, once, off the main actor. Enough to build once and
keep in memory per journey revision, only for the journeys crossing the visible region; propose a derived table (P6) only
if a measurement on an iPhone shows it is slow. Journey Points have no lasting identity yet (TD-5). Not measured yet: the
Map's CPU with many annotations.

## 4b. Places from journey points (approved 2026-11-11; P1 built)

Goal (owner, 2026-11-11): like Geofency, Carodo builds the person's places by itself from where they drove, names each
one once, and can later say how many times a place was visited and list those visits. For the owner personally, this
replaces Geofency over time.

### Decisions approved (owner, 2026-11-11)

- **One `places` table, one `Place` type.** Settings places and detected places are the same thing; they differ by
  `source` (`added`, `suggested`, new `detected`) and `role`. Settings → Places lists only what the person keeps
  (`added`, accepted `suggested`); `detected` places show on the maps only. Keeping or giving a role to a detected place
  turns the same row into a Saved Place. A journey point belongs to the smallest live place containing it (the rule
  `SavedPlaceMark` already uses).
- **Automatic, with one Apple request per new place.** A new place is created from a qualifying journey point that no
  place contains yet, and Apple Maps is asked **once**, at creation (not per visit, not per tap). The result is kept on
  the place. This reverses two 2026-11-09 decisions (ADR 0015: "no Nearby POI becomes a saved place" and "past journey
  points never from Apple Maps"): the ADR is amended in the same change as the code.
- **Names:** the person's name → the POI name (only when `StopPlaceResolver`'s five gates pass, unchanged) → the street →
  the ward. A place without a POI keeps `name` NULL; its address is read from `geocoded_cells` at display time (the cell
  of its centre, as `start_cell` does), so it follows the app's language. `geocoded_cells` stays the address cache only:
  its ~110 m cell is too coarse for a POI (Geofency's median place radius is 12 m).
- **New columns (P6, approved):** `places.poi_id` (the POI's identifier, `MKMapItem.identifier` inside the adapter only;
  paired with the existing `poi_category`), and `source = detected`. No provider column (one source of POIs).

### Also approved (owner, 2026-11-11)

- **`places.poi_checked_at`** (REAL, NULL = not asked yet): needed to tell "not asked" from "asked, no POI" so an offline
  creation is retried and a failed answer is never read as "no POI" (Unknown is not zero). One more column (P6).
- **Which points create a place:** a recorded Start, an End, a Stop; not an estimated Start (no position to name); a Break
  only links to an existing place, never creates one (too short to be a place). The radius: the point's position circle,
  at least 25 m, at most 100 m.
- **Visits are derived, not stored:** a visit = a journey point inside the place; the count and list are read from the
  journal (no visits table, no foreign key; moving a place recounts). A stored index only if an iPhone measurement with
  2,000 drives shows it is slow (Footprints rule, §4).
- **Inside a private Saved Place:** no detected place and no request (fail closed); the point belongs to the private place.

### What it does not do (so it is not a full Geofency yet)

Carodo only knows the points of its drives. A place reached on foot, by taxi, or a drive Carodo did not record is not a
visit. Seeing those needs iOS visit monitoring (`CLMonitor`/visits) outside drives: a new background behaviour (P6) and a
battery question, a separate decision later. Optional, personal: import the owner's Geofency export (1,360 places, 1,047
with an Apple place id) as `detected` places in a DEBUG/Developer action; its 37,653 visits are not journey points and
are not imported. Approved (owner, 2026-11-11): as test data only, from a Developer action (P7).

### Slices (each one commit, each proven before the next)

| # | Slice | Schema |
|---|---|---|
| P1 | `PlaceSource.detected`, `poi_id`, `poi_checked_at` in `v1_initial`; Settings lists only kept places; sync and `.carodo` carry the columns; tests. **Done** (2026-11-11) | yes (approved above) |
| P2 | On journey save (after `PlaceNaming`, off the tracking path, never awaited by it): link each point to a place or create a `detected` one; ask Apple once (gates), retry later when offline | no |
| P3 | Journey Detail map: Stop and Break markers beside Start/End; a tap shows a popup (name or street, category symbol, address, time, duration, "Visited N times") | no |
| P4 | A place's visits: count, first and last, the list of journeys; open from the popup and from Settings → Places | no |
| P5 | History: create places for past journeys with a per-run budget under Apple's rate limit (a limit that names its risk) | no |
| P6 | Footprints: places as markers (category symbol, else neutral), clustered far out, visible area only | no |
| P7 | Developer: import a Geofency export (GeoJSON) as `detected` places, for test data only; skips a place already there | no |

Before TestFlight: TD-2 (Apple Maps data kept on the device) must cover stored POI names and ids.

## 5. Audit (2026-11-09)

**`geocoded_cells`:** schema and meaning unchanged.
- Journey Detail: the Start/End names = `start_cell` / `end_cell` JOIN `geocoded_cells`, written by `PlaceNaming` after
  the journey is saved. The page makes no request for stops.
- Other consumers: Provinces Crossed (reads; writes the cells its bisection asks for), Passport (reads).
- Map (focus on one point): reads the cache first, read only; when missing, calls `CLGeocoder` directly, does not write
  back and keeps nothing in RAM → a repeated request when reopening the same stop (fixed in Slice 3, §3).
- `poi`: stored, no screen reads it yet.

**Map performance: no change needed.** Routes, Heatmap and Footprints already load by the visible region (with a margin,
by tile), only once the camera stops, with detail by zoom, older requests cancelled, a cache by revision and incremental
updates; the whole display route is kept in memory (~8 MB for 2,000 trips, measured). Focus on one point: no history
drawn, a late answer is dropped (`addressRequest`), the Nearby POI cache avoids repeated requests from re-renders, the
Live Map is separate. The principle is recorded in navigation.md (History at scale).

## 6. Still waiting

- **PV-12:** Journey Points on the Map on a real iPhone. **PV-13:** Nearby POI on stops ≥ 5 min recorded by Carodo.
- **TD-2:** Apple Maps data kept on the device ([apple-maps-data-review.md](apple-maps-data-review.md)), before TestFlight.
- **TD-3, TD-4, TD-5:** two POI queries; imported drives without a provenance; Journey Points without a lasting identity.
- **Walking Evidence (V2.3.4):** Core Motion keeps only ~7 days on the recording device; decide on early collection before
  the first TestFlight build.
