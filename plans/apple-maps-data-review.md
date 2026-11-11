# TD-2 — Apple Maps data kept or shown by Carodo: review record

Status: **recorded, not fixed** (2026-11-09). Scheduled by the owner: review before the first TestFlight build, together
with the Privacy Report. The remedy is **not** part of V2.3.3. This file separates three things: what was checked, what
still needs interpretation, and the Carodo data flows affected. It is a technical record, not a legal opinion.

## 1. What was checked

**Apple Developer Program License Agreement, Attachment 6 (Apple Maps Service).** Read on developer.apple.com on
2026-11-09. The footer says Schedule 1 was updated on 2026-10-29. The binding version is the one accepted in the developer
account, so it must be checked again there.

| Clause | Quoted (shortened) |
|---|---|
| §1.2 definition | "Map Data" means any content, data or information provided through the Apple Maps Service including … imagery, terrain data, latitude and longitude coordinates, transit data, points of interest and traffic data. |
| §1.2 | You will use the Apple Maps Service and Map Data only as necessary for providing services and functionality for Your Application. |
| §2.1 | No "remove, obscure or alter" of Apple Maps' copyright, trademarks, logos, legal notices or links. |
| §2.2 | No bulk download, no "extract, scrape or reutilize"; no use of Map Data "as part of any secondary or derived database". |
| §2.3 | No "copy, modify, translate, create a derivative work of, publish or publicly display the Map Data" unless expressly permitted. |
| §2.4 | Map Data shown on a map only on an Apple map. No "surface Map Data … without displaying the corresponding Apple map (e.g., if You surface an address result …, You must display the corresponding map with the address result)". |
| §2.5 | "Unless otherwise expressly permitted in writing by Apple, Map Data may not be cached, pre-fetched, or stored … other than on a temporary and limited basis solely as necessary (a) for Your use of the Apple Maps Service as permitted herein or in the MapKit … Documentation, and/or (b) to improve the performance … after which, in all cases, You must delete any such Map Data." |
| §2.7 | Apple may limit the number of MapKit transactions or revoke access; no figure is published. |
| §4 | An example reason to revoke: "obscures or removes the Apple Maps logo or embedded links when displaying a map". |

**WWDC25 session 204, "Go further with MapKit"** (transcript): place identifiers "remain valid over time"; "Identifiers
can be persisted and shared"; "Place identifiers are still the best choice when you want to persist a reference to a
specific place". The same session: "we're deprecating CLGeocoder".

**iOS 27.2 SDK (Xcode 27.2, headers):** `MKMapItem.identifier` and `MKMapItemIdentifier` exist since iOS 18.0.
`MKMapItem.Identifier` is `RawRepresentable` (a string) and `Codable`. `MKMapItemRequest(mapItemIdentifier:)` exists since
iOS 18.0. `MKPointsOfInterestRequestMaxRadius` exists since iOS 14.

## 2. What still needs interpretation

1. Whether a `CLGeocoder` (Core Location) result is "Map Data provided through the Apple Maps Service". The terms name no
   API. The two APIs share one backend (DTS said so on the forums), so the safe reading is yes.
2. Whether "Identifiers can be persisted" in a WWDC session counts as "MapKit Documentation" or "permitted in writing"
   under §2.5.
3. Whether the name and coordinates of a POI that **the person picks and saves themselves** (a fill-up's station name)
   are Map Data or data the person entered. The terms have no exception for this.
4. What "temporary and limited" means: whether a cache kept until the system clears it (Caches) counts as temporary; a
   permanent cache in SQLite almost certainly does not.
5. Whether a ward or province name drawn from an address, or an ISO 3166-2 code, is still Map Data.
6. Whether §2.4 applies to address text in a list or a title when the same screen has no map.

Ways out: ask Apple in writing (Developer Technical Support or Apple Developer's legal contact), or redesign so nothing
depends on the interpretation (section 4).

## 3. The Carodo data flows affected (source audit 2026-11-09)

| # | Data | Apple source | Where it is kept, for how long | Where it shows | Clauses concerned |
|---|---|---|---|---|---|
| 1 | `geocoded_cells`: ward, district, province, street, POI, country per ~110 m cell | `CLGeocoder` | SQLite on the device, **permanent**, not synced | The source of rows 2–5 | §2.5, §2.2 (a derived database?) |
| 2 | Journey titles ("P. Tân Mỹ → …") | from 1 | Derived when read; `trips.start_cell`/`end_cell` are the keys | Journeys list, detail (with a map), widget? | §2.4 when there is no map |
| 3 | `trips.narrative`: a summary sentence holding place names | from 1, through the on-device model | SQLite, permanent; not synced | Journey detail | §2.5 (a derived form), §2.3 |
| 4 | Provinces Crossed, Passport (provinces driven through) | from 1 | Derived; the provinces sit in the cache | Detail, Passport (possibly with no map) | §2.4, question 5 |
| 5 | The area on the Feed (`DriveArea`, ISO 3166-2, opt-in) | from 1 | Sent to the backend on publish (in the contract, not wired yet) | Seen by others, no map | §2.4, question 5, §1.2 |
| 6 | `fuel_logs.station_name` + coordinates (ADR 0017) | `MKLocalPointsOfInterestRequest` | SQLite + iCloud (`FuelLog`, encrypted), permanent | Fill-up list, vehicle detail | §2.5, question 3 |
| 7 | `places.poi_category` (and the name, if taken from a suggestion) | MapKit | SQLite + iCloud (`Place`) | Places, Passport | §2.5 (minor) |
| 8 | `trip_gaps.route`, lead-in: the road Apple draws across lost GPS | `MKDirections` | SQLite, permanent; goes into the display route (KL-3), which syncs to iCloud and **to the backend when shared** (the trimmed route) | Detail map, share page (not built) | §2.5, §2.2, §2.4 (what map does the web page draw?) |
| 9 | Map snapshot images for the list and the Passport | `MKMapSnapshotter` | `Caches/JourneyMaps/*.png`, the system may clear it | Journeys list, Passport | §2.5 (imagery; arguably temporary and for performance, §2.5(b)) |
| 10 | Share card / link preview image | a snapshot or drawn by Carodo | Shared outside; the preview is uploaded to the backend (spec, not built) | Messaging apps, web | §2.3 "publicly display", §2.1 the logo on the image |
| 11 | A Journey Point on the Map: address, Nearby POI, Find nearby | `CLGeocoder`, `MKLocalPointsOfInterestRequest`, `MKLocalSearch` | In memory only: the address and Find nearby per focus, the Nearby POI per app session; only **reads** row 1 | A preview with a map | Designed to fit §2.4, §2.5(b) |

## 4. Remedies to decide at the review (not now)

- Row 1: move from a permanent cache to a bounded one (for example deleted after N days), or store a reduced result Carodo
  produces itself (a province name as Carodo's own label) if that is confirmed to be allowed. Review Provinces Crossed and
  the titles at the same time.
- Rows 6 and 7: store the place identifier (iOS 18+), with the name being what the person confirms or edits; or ask
  Apple.
- Row 8: a route Apple drew never reaches the backend (the share page uses only recorded GPS points), unless it is shown
  to be allowed.
- Row 10: keep the logo and legal notice on every image with an Apple map background; the preview image draws the route
  only on a non-Apple background.
- An ADR recording the policy: "Map Data in Carodo".

Related: [journey-points.md](journey-points.md), `carodo-ios/docs/privacy.md`, carodo-ios ADR 0017.
