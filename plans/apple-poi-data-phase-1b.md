# Apple points of interest kept by Carodo — phase 1b: audit, plan and brief

Status: **built and merged** (2026-11-16), carodo-ios `0fc5c50`, merged in `ef650f0`. Owner's decisions: D1–D5 as recommended (D2: B now, and send C
anyway). What it leaves open: TD-42. This follows phase 1
of [`../audits/2026-11-16-ios-geocoded-cells-audit.md`](../audits/2026-11-16-ios-geocoded-cells-audit.md)
(carodo-ios `dd58a24`: Apple's addresses kept a week at most, outside the database) and covers rows 6
and 7 of [`apple-maps-data-review.md`](apple-maps-data-review.md) (TD-2). It must land before
`v1_initial` is frozen (TD-6): it changes `places` and `fuel_logs`.

This file keeps apart **Today** (with files), **Proposed**, and **Assumed**. Read at carodo-ios
`1470fd2`: `Core/Domain/Place.swift`, `Core/Formatting/PlaceLabel.swift`, `Core/Domain/PlaceDetection.swift`,
`Core/Recording/PlaceDetectionRun.swift`, `Core/Location/MapKitPOISearch.swift`,
`Core/Location/MapKitStationFinder.swift`, `Features/Journeys/ViewModels/Visits/PlaceNearbyModel.swift`,
`Features/Garage/ViewModels/FuelEntryModel.swift`, `Features/Garage/Views/FuelHistorySheet.swift`,
`Core/Formatting/ExpenseLabel.swift`, `Core/Backup/{BackupDocument,GeofencyImport}.swift`,
`Core/Persistence/{DatabaseManager,GRDBPlaceRepository,GRDBVehicleRepository}.swift`,
`Features/Places/ViewModels/PlaceEditorModel.swift`, `docs/operations/cloudkit.md`.

## 1. Today: what Carodo keeps from Apple's points of interest

| Data | Written by | Columns | Kept | Shown | With an Apple map? |
|---|---|---|---|---|---|
| A **detected place's point of interest** (name, category, identifier) | `PlaceDetection.place(for:poi:)` from `StopPlaceResolver`, after a drive (`MKLocalPointsOfInterestRequest`, `MapKitPOISearch`) | `places.name`, `poi_category`, `poi_id` | SQLite + iCloud (the `Place` payload) + `.carodo` (`BackupPlace`), **for good** | `Place.label` everywhere: Map callouts, journey point cards, the visits page, the Passport's Visited places, titles (a saved place) | Map and cards yes; **Passport list and titles no** |
| A **POI picked in Find Nearby** on a detected place's page | `PlaceNearbyModel` (lines 77–79) | the same three | the same, **for good** | the same | the same |
| A **fuel station** picked in the fill-up sheet | `FuelEntryModel` from `MapKitStationFinder` | `fuel_logs.station_name`; `latitude`/`longitude` = **the station's coordinates from Apple** (only when here and now) | SQLite + iCloud + `.carodo`, **for good** | Fuel history, the vehicle's expense lines (`ExpenseLabel`) | **No** |
| The **Find Nearby list** itself | `PlaceNearbyModel` | — | memory only | the visits page | yes (fine today) |
| A **Geofency import** (DEBUG, test data) | `GeofencyImport` | `name`, `poi_category`, `poi_id` from the person's own export file | SQLite + iCloud | as detected places | as above |

What is not Apple's and stays: a place's centre and radius (the person's own GPS stop, or what they
drew), its role, the private switch, a name the person typed, a station name the person typed.

The station finder keeps no identifier (`MapKitStationFinder` builds `name|lat|lon` as its id).

## 2. Which terms are in play (from `apple-maps-data-review.md`)

- **§2.5 (no caching or storing beyond temporary):** the name and category are Map Data. Stored for
  good, they are the same problem as `geocoded_cells`.
- **Identifiers:** WWDC25 session 204 says place identifiers "remain valid over time" and "can be
  persisted and shared". This is the one piece of Apple data that has a written basis for keeping it
  (open question 2 of the review: whether a WWDC session counts as MapKit Documentation). Since
  iOS 18, `MKMapItemRequest(mapItemIdentifier:)` turns an identifier back into a map item, with its
  name and category. iOS 18 is the deployment target.
- **§2.4 (shown with its map):** a POI name in the Passport list or a fuel history line has no map.
- **Open question 3:** a name *the person picks* (Find Nearby, the station list). Is it Map Data or
  the person's input? The terms make no exception for it.

**On Geofency's export holding addresses** (owner, 2026-11-16): it shows that Geofency keeps
addresses. It does not show what Apple allows Carodo. Geofency may have them from another provider,
under its own agreement, or typed by the person, and its compliance is its own. Carodo's import
reads no address today (`GeofencyImport.Entry`: name, category, place id, circle). A file the
person brings from another app is the person's data: Carodo did not obtain it through the Apple Maps
Service. That reading is an assumption (D4).

## 3. Options

| | A. Keep as today | B. Identifier only, names resolved for a week (**recommended**) | C. Ask Apple in writing |
|---|---|---|---|
| What is stored | name, category, id for good | `poi_id` for good; a name only when **the person typed or confirmed it in an editor**; station: its identifier, and the person's own fix as the position | as A, if Apple says yes |
| Apple's name and category | kept | `MKMapItemRequest` by identifier when shown, kept 7 days in the same two-tier cache as phase 1 | kept |
| Offline more than a week | everything shows | a detected place reads "Detected place" with a generic symbol; a picked station shows the fill-up without a station name | everything shows |
| Terms risk | §2.5 and §2.4, as `geocoded_cells` was | the identifier rests on WWDC25; the confirmed name rests on question 3 (D1) | none once answered |
| Schema | none | `places`: drop `poi_category` (it comes with the lookup); `name` = the person's own. `fuel_logs`: add `station_poi_id`; `station_name` = typed or confirmed; `latitude`/`longitude` = the device's fix at a here-and-now fill-up | none |
| Cost | none | one slice of work, plus the cache made generic | a wait of unknown length; can run alongside B |

## 4. Recommendation: B, built on phase 1's cache

- **Reuse, don't copy.** Extract the core of `PlaceNameCache` into one generic two-tier cache: the
  memory plus `Library/Caches` file, the 7-day expiry, purges, the per-minute budget, the pause
  after a failure, the queue cap, sealed-file handling and the change callback. Then two keyed uses
  sit on it: cells → `PlaceFields` (today's `PlaceNameCache`) and POI identifiers → name and
  category (new, `MKMapItemRequest`). Each keeps its own file and budget, since CLGeocoder and
  MapKit throttle separately. One `AppState` revision for both (`placeNamesRevision`).
- **What is written changes; screens do not.**
  - Detection writes only `poi_id`.
  - Find Nearby writes only `poi_id`. Its list shows names from the in-memory search, as today.
  - The station picker writes `station_poi_id` and the person's own fix.
  - `Place.label` and the expense lines read the cache through the repositories, as titles do since
    phase 1.
- **The person's confirmation is theirs** (D1). Saving a detected place as the person's own place
  (the editor), or typing a station's name, stores the name shown in the field at Save. That name is
  pre-filled from the resolved one and the person can edit it, so the stored value is the one they
  entered. A bare pick in a list stores the identifier only.
- **Identity never depends on a name.** The Passport's Visited places count by place id already
  (`VisitedPlace` key `place:<uuid>`), so a name unknown offline hides a label, never a visit:
  phase 1's "unknown is not zero" problem does not recur.

## 5. Slices (for the new session)

| # | Slice | Schema / contract | Tests |
|---|---|---|---|
| 1b.1 | Extract the generic two-tier cache from `PlaceNameCache`; `PlaceNameCache` becomes its cell use. No behaviour change | — | The existing 15 cache tests pass unchanged; the generic core keeps them |
| 1b.2 | `POINameLookup` over `MKMapItemRequest(mapItemIdentifier:)` behind a protocol, and its cache use. An identifier Apple no longer knows is cached as "none" for the week, never an error loop | — | A fake lookup: hit, miss, none, offline pause, budget |
| 1b.3 | **Schema in `v1_initial`**: `places.poi_category` dropped, `name` documented as the person's own; `fuel_logs.station_poi_id` added, `latitude`/`longitude` = the device's fix. `Place`, `FuelLog`, `BackupPlace`, `BackupFuelLog` (the `.carodo` and iCloud payload) follow. `MapKitStationFinder` returns `mapItemID`. Detection, Find Nearby and the station picker write identifiers only | **schema + `.carodo` format (P6)**; the iCloud payload is one encrypted blob (`CloudRecordCoding.payloadKey`), so no CloudKit field changes (to confirm) | Migrator test; backup round trip; each writer stores no Apple name |
| 1b.4 | Readers: `Place.label` callers (Map callouts, journey point cards, the visits page, Visited places), the fuel history and `ExpenseLabel` resolve through the cache and refresh on the revision. Unknown shows the generic label, never an empty row | — | Label with a hit, a miss and offline; Passport counts unchanged when names are unknown |
| 1b.5 | Docs: `data-model.md` (places, fuel_logs, the cache), `privacy.md` (MapKit rows), `specs/places.md`, `specs/garage.md`, ADR 0017 (fill-ups) updated in place (pre-release); handbook: TD-2 rows 6–7, `apple-maps-data-review.md` rows 1, 6, 7 | — | `LocalizationTests` for any new string |

1b.1–1b.5 are one outcome, so one commit, as phase 1 was.

**Acceptance**
- No table holds an Apple name or category.
- `poi_id` and `station_poi_id` are the only Apple data stored for good.
- With the network, every label reads as it does today.
- In airplane mode after the cache is cleared (Developer → Clear place names, extended to both
  caches), no screen errors: detected places read their generic label, fill-ups their figures.
- `task lint`, `task warnings` and `task test` pass.
- Screenshots: Places and the Map callout, the visits page, the fuel history (Light, Dark,
  xxxLarge, Vietnamese).

**Device checks:** a fill-up at a real station (its identifier stored, the name resolved); a long
Visited places list scrolled online (MapKit throttling).

## 6. Owner decisions

| # | Decision | Recommendation |
|---|---|---|
| D1 | A name the person **confirms in an editor** (saving a detected place, a station name in the field) is kept as theirs; a bare pick in a list keeps the identifier only | **Yes**: it is what the person entered. A name never confirmed stays Apple's (7 days) |
| D2 | Option B, or keep A while asking Apple (C) | **B now**, and send C anyway: an answer would only let names come back |
| D3 | A fill-up's position: the device's fix at a here-and-now fill-up (the person's GPS), or none | **The device's fix**: it is the person's own location, private like the journal |
| D4 | A Geofency import's names (DEBUG test data from the person's own file) | Kept as the person's names: the person brought them. DEBUG only, never a feature |
| D5 | Clear place names in Developer also clears the POI cache | **Yes**, one button for both |

## 7. Brief for the new session

```text
Outcome: Carodo keeps no Apple point-of-interest name or category for good; only identifiers
  (places.poi_id, fuel_logs.station_poi_id) and what the person typed or confirmed. Names and
  categories are resolved by identifier (MKMapItemRequest) and kept 7 days in the phase 1 cache.
User story: my places and fill-ups read as today with the network; offline for a week they still
  load, with generic labels where Apple's names were.
Existing behaviour (files read): carodo-handbook/plans/apple-poi-data-phase-1b.md §1.
Owner decisions needed: D1–D5 in §6 (answers given in the session's first message).
Spec (Ready?) and mockups: no new screen; specs/places.md and specs/garage.md change with it.
Acceptance criteria: §5, Acceptance.
Non-goals: OSM (phase 2); Find Nearby's list itself (memory only already); the Map's own labels.
Relevant files/docs: §1's list; Core/Location/PlaceNameCache.swift; docs/data-model.md
  (Place names); carodo-handbook/audits/2026-11-16-ios-geocoded-cells-audit.md.
Constraints: P5, P6 (schema and .carodo format approved in this plan), invariant 6 (edit
  v1_initial), reuse the phase 1 cache (extract, never copy), one commit.
Validation commands/device checks: task lint, task warnings, task test; screenshots; §5 Device checks.
Allowed scope: slices 1b.1–1b.5.
Do not: keep any Apple name in SQLite, iCloud or a .carodo file; add a package; touch OSM work.
```

Prompt for the new session (paste as is, after the owner's answers to D1–D5):

> Implement phase 1b from carodo-handbook/plans/apple-poi-data-phase-1b.md (brief in §7). Owner's
> decisions: D1 …, D2 …, D3 …, D4 …, D5 …. Read the plan and carodo-ios AGENTS.md first; work in a
> worktree; one commit; report as AGENT_WORKFLOW.md says and wait for my review before merging.

## Assumed, not checked

- That `MKMapItemRequest` by identifier returns the name and category for a Vietnamese POI and
  works on iOS 18.0 (to try in 1b.2 on the simulator).
- That an identifier returned in 2026 still resolves later (WWDC25 says so).
- That the iCloud `Place` and `FuelLog` records carry the payload only, so no CloudKit field changes
  (`CloudRecordCoding.payloadKey`; to confirm in 1b.3).
- Geofency's `placeID` is Apple's identifier (the import's comment says so).
