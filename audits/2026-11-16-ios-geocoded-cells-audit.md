# `geocoded_cells` audit — 2026-11-16

`carodo-ios` at `77c412e`. Audit and plan only, read-only; **no code before the owner approves each
phase** (`AGENT_WORKFLOW.md`, Plan before code). It covers TD-2 row 1, TD-36, and the
`geocoded_cells` part of TD-6: the table must be settled before `v1_initial` is frozen.

This file keeps apart **Today** (what the code does, with its file), **Proposed**, and **Assumed**
(not checked). Sources read: `Core/Location/PlaceLookup.swift`, `Core/Formatting/PlaceName.swift`,
`Core/Formatting/PlaceArea.swift`, `Core/Recording/PlaceNaming.swift`,
`Core/Recording/ProvincesCrossedSource.swift`, `Core/Recording/PlaceDetectionRun.swift`,
`Core/Domain/ProvincesCrossed.swift`, `Core/Domain/FrequentPlaces.swift`, `Core/Domain/PassportAnalysis.swift`,
`Core/Narrative/JourneyFacts.swift`, `Core/Journal/ShareCard.swift`,
`Core/Persistence/{DatabaseManager, GRDBJourneyRepository, GRDBJourneyRepository+Places, +Edits, +Joins, GRDBPlaceRepository, GRDBCloudSyncStore, DataOwnership}.swift`,
`Core/Backup/BackupDocument.swift`, `Core/Sync/CloudRecordCoding.swift`,
`Features/Journeys/ViewModels/Detail/JourneyDetailViewModel.swift`,
`Features/Journeys/ViewModels/Visits/PlaceVisitsPage.swift`, `Features/Map/ViewModels/MapAtlasViewModel.swift`,
`App/DependencyContainer.swift`, `docs/data-model.md`, `docs/privacy.md`, `docs/specs/journey-detail.md`,
`docs/specs/feed.md`, ADR 0007, `docs/api/carodo-api.yaml`; handbook `plans/technical-debt.md`
(TD-2, TD-6, TD-26, TD-36), `plans/apple-maps-data-review.md`.

**Status (2026-11-16):** phase 1 is built and merged into `carodo-ios` `main` (`dd58a24`), after
a self-review that fixed three cases: a file sealed before the first unlock is kept, the Journeys
list re-reads titles only, and a place's page asks its one address now. The device checks are
still pending (TD-40). Phase 1b (Apple's points of interest and fuel stations) is built and merged
(`0fc5c50`, merge `ef650f0`; [`../plans/apple-poi-data-phase-1b.md`](../plans/apple-poi-data-phase-1b.md);
open: TD-42). Apple is asked only while the app is on screen (`408f6a3`, merge `b143467`; TD-43).
Phase 1 and 1b are done in code; they close when the device checks of TD-40, TD-42 and TD-43 pass. The Settings question was
settled as Developer only: Developer → Clear place names (`docs/specs/developer-mode.md`). Phase 2
has not started. What phase 1 leaves open is TD-40.

## Decisions taken (owner, 2026-11-16)

- **Two phases.** Phase 1 removes `geocoded_cells`. Apple is asked only when online, and its
  answers are held in a temporary cache. Phase 2 adds data the device keeps for good, built from
  OSM and handed out by the Carodo server.
- **The temporary cache lasts 7 days**, in two tiers (memory and disk; section 4).
- **Phase 1 hides the Passport's "provinces first reached"** until phase 2.
- **Phase 1's narrative names no province.**
- **Phase 1's Provinces Crossed is asked when the detail page opens.** It is held in the 7-day
  cache. Offline, the row is not shown.
- **Rejected:** a server that looks up OSM by coordinate (as some apps do for "coverage
  statistics"). It sends a drive's ends to the server (P5/P7), makes naming depend on the server,
  and Nominatim's public service allows 1 request a second and no app back-end use.
- **Phase 2 may relax P5/P7 only in the bounded way of section 6**, through an ADR, never ad hoc.

## The picture: three sources of place knowledge

| Source | Gives | Network | Kept |
|---|---|---|---|
| **The device's own data**: GPS, `start_cell`/`end_cell` (Carodo's grid keys), the person's Places | Distance, time, speed, replay, route, Places, frequent places | Never needed | For good |
| **Apple** (`CLGeocoder`, MapKit) | Ward and province names, street, POI, for display | Needed | **7 days at most** (ADPLA §2.5), never in the journal database |
| **OSM, as packs handed out by the Carodo server** (phase 2) | Province and ward boundaries, tunnels (`tunnel=yes`), toll booths (`barrier=toll_booth`) | Only to download a pack | For good on the device (ODbL) |

The rule across all three: the device matches its own route against data it holds. **A coordinate
or a route never goes to the server** (P5/P7), except under the bounded rule of section 6.

## 1. Today: every read and write of `geocoded_cells` and the columns keyed to it

### Schema

| Object | Where | What |
|---|---|---|
| `geocoded_cells` (`WITHOUT ROWID`) | `DatabaseManager.swift:375` | `cell` PK (`PlaceKey`, "10741,106733"), `ward`, `locality`, `district`, `province`, `street`, `poi`, `country`, `lookup_version`, `looked_up_at`. "Local cache, never synced" |
| `trips.start_cell`, `trips.end_cell` | `DatabaseManager.swift:278` | The `PlaceKey` of the trimmed track's first and last fix: **Carodo's own grid keys, not Apple data** |
| `trips.places_version` | same | `PlaceNaming.rulesVersion` the ends were keyed with |
| `trips.narrative` | same | Text written on the device; can name provinces from the cache (`JourneyFacts.Region`) |
| `DataOwnership` | `DataOwnership.swift:68,75` | `geocoded_cells` classed **Independent** |

### Writers (all through `PlaceLookup` → `AppleGeocoderPlaceLookup` → `CLGeocoder`)

| Writer | File / function | When | What it asks |
|---|---|---|---|
| Naming a drive's ends | `PlaceNaming.run` (`DependencyContainer.swift:1141`) | After a save, at launch, on return to the app; 20 trips a run | Start and end cells, skipping private places; then `setPlaceKeys` writes `start_cell`/`end_cell` |
| Provinces Crossed | `GeocodedProvinceSource.provinces(…, lookUp:)` (`ProvincesCrossedSource.swift`), from `findProvincesCrossed` (`DependencyContainer.swift:1155`) and the detail page | After naming; when the detail page opens | The few chain cells the bisection needs, within `maximumLookupsPerRun` |
| Naming a detected place | `PlaceDetection.run` (`PlaceDetectionRun.swift:65`) | After a save, budget 12 | The cell of a stop Apple named no POI for |
| `savePlace` | `GRDBJourneyRepository+Places.swift:148` | — | `INSERT OR REPLACE`, all 7 fields (all nil = Apple had nothing) |

These set `start_cell`/`end_cell` back to NULL: a trim (`+Edits.swift:211,337`), a re-derive
(`+Edits.swift:290`), a join or split (`+Joins.swift:155,201`), a track from iCloud
(`GRDBCloudSyncStore.swift:349`).

### Readers

| Reader | File | Fields | Feature, screen | Beside an Apple map? |
|---|---|---|---|---|
| `details(for:)` | `+Places.swift:14` | ward, locality, district, country, province (both ends) | **Titles**: Journeys list, Day view (`DayFeaturedJourney`), detail, join and split options; the **share card**'s `EndName` | List, Day: **no**. Detail: yes. Card: an image leaving the app |
| `driveFacts` | `GRDBJourneyRepository.swift:177` | ward, locality, district, country; end province | **Passport**: provinces first reached (`PassportAnalysis.provinceFirsts`), exploration (`PassportExploration:166`), visit origins (`PlaceVisitLog`) | **No** |
| `cachedPlaces(keys:)` | `ProvincesCrossedSource.swift:42` | province, country | **Provinces Crossed** on the detail page; the **narrative** (`JourneyFacts.Region`, stored in `trips.narrative`) | A text row on a page with a map |
| `cachedPlace(key:)` | `JourneyDetailViewModel.swift:382` | `PlaceName.area` (street + ward) | Stop and point **cards** on the detail map | Yes |
| `cachedPlaces(keys:)` | `MapAtlasViewModel.swift:367` | `PlaceName.area` | **Map** tab: place marker labels | Yes |
| `cachedPlace(key:)` | `PlaceVisitsPage.swift:39` | `area`, `address` (+ province) | A place's **visits page** | Its map is **assumed, not checked** |
| cells only | `GRDBPlaceRepository.swift:105` → `FrequentPlaces` | cell keys, no Apple field | Frequent-place suggestions | — (no Apple data) |
| — | `PlaceFields.poi` | **never read** | — | — |
| `DriveArea` | `PlaceName.swift` | province, country | **None**; only `DriveAreaTests` | — |

### Where it goes

| Destination | `geocoded_cells` | `start_cell`/`end_cell` | Derived |
|---|---|---|---|
| iCloud | No: the trip record is the encrypted `BackupTrip` payload (`CloudRecordCoding.swift:116`), which has no cell | No | `narrative`: no; titles are made when read, never stored |
| `.carodo` file | No (`BackupDocument.BackupTrip`) | No | No |
| Backend | No | No | Not today; a **share card image** may carry an end's ward or province (TD-26) |

Findings beside the main one:
- `DriveArea` is dead code, and row 5 of `apple-maps-data-review.md` is stale: `feed.md` and ADR
  0007 rule out any area on the Feed, and the API contract has none.
- `setPlaceKeys` (`+Places.swift:171`) sets `ck_pending` and raises `revision` when the cells
  change, though iCloud does not carry them: an upload with nothing new. Its purpose (perhaps the
  Feed's `revision`) is not confirmed; settled in phase 1, slice 1.3.

## 2. What each feature needs

| Feature | Field | Without a map? | Must last? | Phase 1 | Phase 2 |
|---|---|---|---|---|---|
| Journey title | VN: post-2025 ward/commune; elsewhere: town | Yes (list, Day) | Better, not required | From the 7-day cache; else the time of day | OSM, for good |
| Provinces Crossed | province + country along the route | Text row | Better | Asked when the detail opens, 7-day cache; offline hidden | OSM, for good, offline |
| Narrative | province | Detail | It is stored text | **Names no province** | Names it again (OSM) |
| Passport, provinces first reached | end province, whole history | Yes | **Yes** | **Hidden** | OSM, for good |
| Passport exploration, visit origins | ward | Yes | Better | 7-day cache, else left out | OSM |
| Share card ends | ward, or province in a private place | Image outside the app | At share time | Cache or asked when sharing; offline: no ends | OSM |
| Stop cards, Map markers, visits page | street + ward | No (with a map) | No | 7-day cache | Street stays Apple (7 days); ward from OSM |
| Detected place with no POI | ward (address) | As above | Its label | Resolved on display | OSM |
| Tunnels, toll booths | — | — | Yes | — | **New**: OSM packs, matched on the device |
| `poi`, `district` | — | — | No | Dropped | — |

## 3. Phase 1 — remove `geocoded_cells`, Apple only while online

**Outcome.** No Apple answer stays on the device more than 7 days, and none is in the journal
database. With the network, titles, Provinces Crossed and addresses look as they do today. Offline,
every screen still shows distance, time, speed, the route and the replay. A title falls back to the
time of day ("Morning drive"), which is a fact and never an error. The schema is ready for the
TD-6 freeze.

**Non-goals.** OSM, the server, tunnels and tolls (phase 2). Replacing `CLGeocoder`: the target is
iOS 18, `MKReverseGeocodingRequest` exists only from iOS 26, and it has no ward field (TD-36 stays
open).

### Slices

| # | Slice | Schema / contract | Tests |
|---|---|---|---|
| 1.1 | **`PlaceNameCache`**: two tiers (section 4) behind one type in `Core/Location`, wrapping `PlaceLookup`. Lookups are asked for what is on screen, deduplicated by cell, cancelled with their view, and held to a per-minute budget against Apple's throttle. The private-place rule is kept: such a cell is never asked. On iOS 26+, try `MKReverseGeocodingRequest` with the ward read as Driveline does (Reference apps); keep `CLGeocoder` on iOS 18–25 and wherever the ward does not come back | A cache file in `Library/Caches` (its own format version; not the journal database) | Expiry on both sides of 7 days; purge; in-flight dedupe; budget; a private cell is never asked; offline gives "unknown", never "no place"; a damaged cache file is dropped, never a crash |
| 1.2 | **Schema**: drop `geocoded_cells` from `v1_initial`; keep `start_cell`/`end_cell`/`places_version`; `DataOwnership` updated; migrator test; development reset (invariant 6) | **schema (P6)** | The migrator test; `DataOwnership` tests |
| 1.3 | **Writers**: `PlaceNaming` keys the cells only (no lookup); a drive just saved warms the cache for its two ends (one user action). `PlaceDetection` stops looking up addresses. Provinces Crossed asks from the detail page into the cache. Decide on `ck_pending` in `setPlaceKeys` | — | PlaceNaming without a lookup; Provinces Crossed with an empty and a warm cache |
| 1.4 | **Readers**: titles (list, Day, detail), Passport exploration and visit origins, share card ends, stop cards, Map markers and visits page read through `PlaceNameCache`. The SQL joins on `geocoded_cells` go. Passport "provinces first reached" is hidden. The narrative's region names no province | — | Title with a hit, a miss and offline; share card without ends; Passport with the section hidden; narrative strings |
| 1.5 | **Clean-up and docs**: delete `DriveArea` and `PlaceFields.poi`; update `data-model.md`, `privacy.md` (7 days, never synced), `specs/journeys.md` (titles), `specs/passport.md`, `specs/journey-detail.md` (Along the way), `specs/share.md`, `architecture.md` (the Provinces crossed row) | — | `LocalizationTests` for removed strings |

1.1–1.5 make one outcome, so they go in one commit (or a branch merged as one). They are listed
separately for review only. **Screens touched** (evidence: Light, Dark, xxxLarge, Vietnamese): the
Journeys list online and offline, the detail page, Passport, a share card without ends.

**Acceptance.**
- No table in the journal database holds an Apple field.
- A cache entry older than 7 days is never read and is deleted at the next launch or
  backgrounding.
- In airplane mode every screen loads with no error state, and titles show the time of day.
- `task lint`, `task warnings` and `task test` pass.

**Device check still required:** a real drive offline, then online, to see the titles fill in;
throttling while scrolling a long list.

## 4. The 7-day cache: two tiers, as common caches do

The pattern is the one widely used image caches ship with, and their defaults match the owner's
7 days. SDWebImage keeps a memory cache and a disk cache, with `maxDiskAge` defaulting to one week.
Kingfisher has a memory storage and a disk storage, with disk expiration defaulting to 7 days.
Apple's `URLCache` is also memory plus disk. Carodo applies it to place names:

| Tier | What | Lifetime | Why |
|---|---|---|---|
| **Memory** (`NSCache`-like, keyed by cell) | The parsed `PlaceFields` | The app session; evicted under memory pressure | Scrolling and going back cost nothing |
| **Disk** (`Library/Caches/PlaceNames/`, one small file) | cell, fields, `fetched_at` | **Hard 7 days from `fetched_at`**; then never read, and deleted at launch and on backgrounding | Titles survive a relaunch and a short offline spell |

Rules that differ from an image cache, because of ADPLA §2.5:
- **No stale-while-revalidate past 7 days.** An expired entry is treated as absent: the screen
  shows the fallback and asks again when online.
- **Purged for real.** The whole folder is deleted when its format version changes.
- **Never in the journal database, iCloud, a `.carodo` file or a log.** `Caches` is not in the
  device backup, and iOS may clear it, which is harmless.
- **Never asked in bulk.** Only for rows on screen, a drive just saved, an opened detail or a
  share. This follows Apple's guidance of one request per user action.

## 5. Phase 2 — OSM packs from the server, matched on the device

**Outcome.** Province and ward names, the Passport's provinces, Provinces Crossed, and the
**tunnels and toll booths a drive passed** are known for good, offline, with no Apple dependency.
The server hands out data and never sees a route.

**Gate (slice 2.0, no app code).** Build the packs from a Geofabrik / planet extract, then measure:
- the size;
- completeness against the official 3,321 communes and wards;
- agreement with Apple on the cells of the `drive-data/` drives (locally; nothing is sent out).

On OSM's state: the community thread (latest post 2026-01-18) says the provinces are updated. It
reported, at the time, about 1,476 boundaries still at the old `admin_level=6`, about a hundred
wards at `admin_level=8`, and over 1,800 commune relations lacking `wikidata`, and it makes no
claim of completeness. So the build selects by containment and the official name list, never by
`admin_level` alone. Gaps are fixed in OSM upstream, never copied from government maps (unclear
licence; it would taint the ODbL build).

| # | Slice | Repo | Schema / contract |
|---|---|---|---|
| 2.0 | Spike and measurements above; results written here | handbook + `carodo-app/tools/boundaries` | — |
| 2.1 | ADR "Place names and Map Data": OSM for what is kept, Apple 7 days, ODbL duties; and an ADR for section 6 if taken | ios | **P5/P7 amendment if section 6 is taken** |
| 2.2 | Build pipeline in a Worker or CI job: packs (VN boundaries, world admin-1, VN tunnels and toll booths) on R2 with a manifest and versions | app | **new service and contract (P6)** |
| 2.3 | `cell_areas` (cell, country, province_id, ward_id, dataset_version), plus where a drive passed a tunnel or a toll booth (`trip_features`, derived, local). An **additive migration** if `v1_initial` is frozen by then | ios | **schema (P6)** |
| 2.4 | `AreaLookup`: an offline point-in-polygon lookup with a grid index; tunnel and toll matching along the raw track. Titles, Passport (shown again), Provinces Crossed and the narrative read OSM first, then Apple's 7-day cache for what OSM lacks (outside VN: towns, streets) | ios | — |
| 2.5 | Attribution "© OpenStreetMap contributors" (About, Acknowledgements, the share web page), as pilgrim-ios does in its About (`Scenes/Settings/AboutView.swift`: a sentence on where the map comes from, then the credit linked to openstreetmap.org/copyright); ODbL notice; the published extract | ios + app | — |
| 2.6 | Records: close TD-2 row 1 and TD-36; rewrite `apple-maps-data-review.md` rows 1–5; narrow TD-26 | handbook | — |

**Size, estimated, to measure in 2.0:**
- Vietnam's wards and provinces: about 2–6 MB.
- World admin-1: about 5–15 MB.
- Vietnam's tunnels and toll booths: a few hundred KB.

**Bundled or downloaded:** the Vietnam packs ship in the app so naming works from the first launch
(P7). The server sends updates.

**ODbL (technical reading, not legal advice):**
- The packs are a derivative database used publicly, so they are offered under ODbL. This binds
  the data, not the code.
- Names on screen and on a card are a Produced Work: the attribution goes where people reasonably
  see it.
- Apple data is never mixed into the OSM-derived packs or tables (ADPLA §2.2 forbids a derived
  database; ODbL would make the mix share-alike).

## 6. Phase 2: relaxing P5/P7 in a bounded, legitimate way

Phase 2's default needs no relaxation. Vietnam is downloaded whole, and the world's admin-1 is
small enough to download whole. A relaxation is needed only if Carodo wants **finer data outside
Vietnam** (towns, wards and tolls worldwide are gigabytes) without sending everyone the world.

**Proposed rule (for an ADR, owner's approval):** the device may ask the server for **a coarse tile
of data, never for a lookup.**

| Constraint | What it prevents |
|---|---|
| The request names a **tile id of about 100 km or more** (a geohash of 3 characters, or a province), never a coordinate | The server learning a home or a route; a tile is about as coarse as IP geolocation already is |
| **Neighbours are fetched with it** (the 3×3 tiles around it) | One tile pointing at one town |
| **Away from the moment of a drive**: at launch or on Wi-Fi, batched, never when a drive ends | Timing tying a tile to a drive's end |
| **No account, no username, no device id** on the request. The pack is public static data on a CDN (R2), so App Attest is not needed for it | Linking tiles across requests to one person |
| The server and CDN logs **do not keep tile ids** with an IP; analytics count packs, not people | A log becoming a location history (P5) |
| Packs are **public and the same for everyone** | The server giving people different answers, or learning anything from the answer |

**Weighed and not proposed:**
- A server lookup by coordinate, even rounded to 1 km: one end of a drive is a home.
- A lookup through an Oblivious HTTP relay (Cloudflare Privacy Gateway): it hides the IP, but the
  server still reads every coordinate, and P7's App Attest key links the requests.
- Private Information Retrieval: correct, but far beyond a solo developer's budget.

**Assumed, not checked:** the tile size that keeps packs small enough (measure in 2.0); whether the
CDN can drop path and IP from its logs, or only shorten their retention.

## Reference apps read (`~/code/oss/swift`, 2026-11-16)

| App | What it does | Take | Leave |
|---|---|---|---|
| Driveline, `Services/GeocodingService.swift`, `Sweeps/PlaceNameSweepService.swift` | Uses `MKReverseGeocodingRequest` (iOS 26). Reads `subLocality`/`locality` through the deprecated `MKMapItem.placemark`, behind a private protocol (`LegacyMapItemPlacemark`) so the call site raises no warning. Then falls back to `addressRepresentations.cityWithContext`, `cityName`, `address.shortAddress` | On iOS 26+, `PlaceLookup` can use `MKReverseGeocodingRequest` and still read the ward. Check this in phase 1 (slice 1.1) on a Vietnamese address. It narrows TD-36 but does not close it: `placemark` is deprecated too | Its sweep stores the names in the drive for good (SwiftData): the ADPLA §2.5 issue this audit removes |
| pilgrim-ios, `Models/Data/CustomImageCache.swift` (the `Cache` pod, hyperoslo) | `HybridStorage` = `MemoryStorage` (15 min, 50 items) + `DiskStorage` in Caches (5 MB cap). The expiry is kept as the file's modification date, and `removeExpiredObjects` purges | The shape of `PlaceNameCache`: the two tiers, expiry kept with each entry, a purge pass, a size cap | The pod (P6: Carodo writes the small cache itself), and its `expiry: .never` on disk |
| OutRun | No geocoding, no cache | — | — |

## Owner decisions still open

| # | Decision | Recommendation |
|---|---|---|
| D2 | Bundle the Vietnam packs in the app, with server updates | **Yes** |
| D3 | Titles outside Vietnam in phase 2 | OSM admin-1 when the two ends differ; Apple's town from the 7-day cache; else the time of day |
| D5 | An OSM credit on the share card image itself | No; on the share web page and in About |
| D6 | Where the pack build lives | `carodo-app/tools/boundaries`, run by CI or a Worker cron |
| D7 | `ck_pending` set by `setPlaceKeys` | Decide in slice 1.3, after confirming what reads `revision` |
| D8 | Section 6 (coarse tiles) | Only when finer data outside Vietnam is wanted; an ADR first |

## Assumed, not checked

- Every size above is an order-of-magnitude estimate.
- OSM's completeness in November 2026 (the thread's figures date from 2025).
- Whether the visits page shows an Apple map.
- Whether `MKReverseGeocodingRequest`'s fields hold the street the cards use (`PlaceArea`). Partly checked 2026-11-16 (iOS 27 simulator): the ward is `addressRepresentations.cityName`, the street only inside `shortAddress`, no province field (TD-36).
- Apple's throttle on `CLGeocoder` (no published figure; ADPLA §2.7).
- ADPLA O1: that the agreement accepted in the developer account matches the public text (TD-2).

Sources: [OSM Community: Tổ chức lại các đơn vị hành chính tại Việt Nam](https://community.openstreetmap.org/t/t-ch-c-l-i-cac-d-n-v-hanh-chinh-t-i-vi-t-nam/132336),
[Wikipedia: 2025 Vietnamese administrative reform](https://en.wikipedia.org/wiki/2025_Vietnamese_administrative_reform),
SDWebImage `SDImageCacheConfig.maxDiskAge` and Kingfisher `DiskStorage.Config.expiration` (one-week
defaults, from their documentation).
