# Weather on a drive: facts kept, Apple's figures cached

Status: **approved, D1–D7 as recommended (owner, 2026-11-19); slice 1 done (carodo-ios `b19600e`; device check PV-39 open); D4's copy fell back to "Gặp mưa": "Mưa trên đường" overflowed a Feed row at xxxLarge.** Replaces the storage and
sync part of [`../drafts/weather.md`](../drafts/weather.md) (which stored and synced Apple's
figures). Follows carodo-ios ADR 0020 (outside lookups gated and ledgered) and the paid team
(`paid-team-attest-staging.md`).

**Owner decisions already made (2026-11-19):**
- Apple's weather figures (temperature, humidity, wind, …) are **never stored for good**: only in a
  cache kept for a limited time (WeatherKit terms, below).
- What Carodo **derives** from them (rain or not, a coarse sky, fog) **may be stored**.
- Weather is **not synced** to iCloud: WeatherKit answers past hours, so another device asks again.
- Two layers, as above.

## 1. Today (files read)

| What | Where | How it behaves |
|---|---|---|
| The one lookup | `Core/Weather/WeatherLookup.swift` (`WeatherKitLookup`) | Feed rain tag only: one `.hourly(hour, hour+1h)` request at the start rounded to 0.1° (`WeatherRounding`) and its start hour, through the `weatherKit` gate. Returns `Weather` (rain, clear, unknown); every error is `.unknown`. Non-throwing, so a caller cannot tell offline from no rain asked |
| Caller | `Core/Feed/FeedPublisher.swift:175` | Asks at publish time; nothing stored |
| Wiring | `App/DependencyContainer+Feed.swift:41` | `WeatherKitLookup` when `CARODO_WEATHERKIT`, else `NoWeatherLookup` |
| Gate | `Core/MapLookup/ProviderGate.swift`, `docs/architecture.md#outside-requests-one-gate-per-provider` | `weatherKit`: 10 a minute, 100 a day, 3 a minute reserved for screens |
| Ledger | `trip_enrichments` (`DatabaseManager` v1_initial), `Core/Domain/Journey/TripEnrichment.swift` | `EnrichmentKind`: `gap_route`, `poi_match`; backoff 5 min, 1 h, 6 h, 1 day, `failed` after 8. Derived, local, never synced, never in a backup |
| Scheduler | `Core/Recording/EnrichmentScheduler.swift` | Passes at launch, on a journal change, on return to the app; outside lookups only while on screen |
| Caches | `Core/Maintenance/LocalCache.swift` | `placeNames` (7 days), `pointsOfInterest` (7 days), `journeyMaps` (30 days) |
| Attribution | `Features/Feed/Views/WeatherAttribution.swift` | Apple Weather mark + legal link at the end of the Feed while a rain chip shows |
| Build flag | `Configs/Shared.xcconfig` `CARODO_WEATHERKIT_FLAG`; this Mac's `Local.xcconfig` empties it | The entitlement `com.apple.developer.weatherkit` is in `Carodo.entitlements` |
| Names taken | `Weather` (Feed API enum, `FeedAPI.swift:27`, a field sent), WeatherKit's `Weather`, `WeatherCondition`, `WeatherService` | New types must not reuse them |

### The terms (Apple Developer Program License Agreement, Attachment 8, read 2026-11-19)

- **1.6:** Apple Weather Data "may not be cached, pre-fetched, or stored … other than on a temporary
  and limited basis solely to improve the performance of the WeatherKit APIs", unless the
  documentation expressly permits it.
- **1.5:** no use "as part of any secondary or derived database".
- **1.2:** Value-Added Services or Products are allowed: data derived from Apple Weather Data and
  "transformed so that it is not possible … to ascertain or use Apple Weather Data in the form
  originally supplied".
- **3.2:** Apple may limit, suspend or revoke WeatherKit access on a breach.

This plan reads them as: Apple's figures only in a bounded cache; Carodo's own coarse facts may be
stored. An interpretation, not legal advice.

### What other apps do (read for comparison)

- **Driveline** (`~/code/oss/swift/Driveline`): `.current` at the first fix and at the finish while
  recording; a `BGProcessingTask` sweep fills missing start/end for 30 days with `.hourly(date±1h)`.
  Stores temperature, Apple's description and symbol for good in SwiftData, synced by CloudKit.
- **Pilgrim** (`~/code/oss/swift/pilgrim-ios`): `.current` during a walk, retried every 10 s; four
  columns on the walk, for good; a REST fallback with the WeatherKit private key in Info.plist.
- **CarStack** (its container in `drive-data/`): `Library/Caches/weather-data.db` is **WeatherKit's
  own cache** (the framework's schema, about 4 minutes' life for current weather, keyed by a
  ~110 m cell and locale); the app itself stores the figures with exact positions in
  `sessions.weather_json` / `weather_samples_json`, for good.

All three keep Apple's figures for good (against 1.6). WeatherKit's own cache lives minutes, too
short for a journal, so Carodo needs its own bounded cache.

## 2. Proposal

### What is asked

- **Points of a drive:** the start at its start hour, the end at its end hour, and one point per
  full hour of recorded time in between, at where the car was then (D5). Each point is a cell
  (`WeatherRounding`, 0.1°, about 11 km) and an hour.
- **One request per distinct `cell|hour`** (`.hourly(hour, hour+1h)`), as today. A 30-minute drive
  in one cell and hour costs 1; a 4-hour drive about 5; a return drive in the same cell and hour
  0 (cache). Past hours are answered back to 2021-08-01, so a drive saved offline gets its weather
  later and any device can ask again.
- Hour precision only: WeatherKit has no minute data for the past. Copy says "rain at the start",
  never "rain from 08:15".

### Layer 1: Apple's figures, cached for a limited time

- `LocalCache.weatherHours` (folder `WeatherHours`), key `cell|hour`, value a Carodo struct
  `WeatherHourReading` with the figures the detail page shows: condition, daylight, temperature,
  apparent temperature, humidity, wind speed and gust, precipitation kind, amount and chance,
  visibility. Erased with the local data, never in a backup or iCloud.
- Lives until the answer's `metadata.expirationDate`, capped at D3. Expired: the next screen that
  needs it asks again through the gate (screen priority).
- Offline with an expired entry: the figures are hidden (unknown is not zero); the stored facts
  still show.
- Like `PlaceNames`, its keys are cells: location history in Caches for a limited time, erased with
  the local data (`docs/privacy.md` names it).

### Layer 2: Carodo's facts, stored

A new derived table `trip_weather`, one row per trip, written by the pass when every point is
answered (D1):

| Column | Type | Meaning |
|---|---|---|
| `trip_id` | TEXT PK → `trips(id)` ON DELETE CASCADE | |
| `rules_version` | INTEGER NOT NULL | `TripWeatherFacts.rulesVersion`; a new version asks again (via the ledger) |
| `start_sky` | TEXT NOT NULL | `DriveSky` at the start: `clear`, `cloudy`, `rain`, `heavy_rain`, `storm`, `fog`, `snow` |
| `end_sky` | TEXT NOT NULL | the same at the end |
| `rain` | TEXT NOT NULL | `none`, `part` (some points), `all` |
| `heavy_rain` | INTEGER NOT NULL | 1 when a point is `heavy_rain` or `storm` |
| `low_visibility` | INTEGER NOT NULL | 1 when a point is fog or visibility under a threshold (Configuration) |
| `strong_wind` | INTEGER NOT NULL | 1 when a gust passes a threshold (Configuration) |

- No figure from Apple (no temperature, humidity or wind value), no coordinate, no cell, no hour
  (the trip has its times). Seven sky values from WeatherKit's ~35 conditions: transformed (1.2).
- `DataOwnership`: derived, owned by `trips`. Never synced, never in a backup or `.carodo` (another
  device derives it, `docs/architecture.md#derived-insights-and-enrichment`).
- Raw values stored: `DriveSky`, `rain` values never renamed (iOS invariant 8). WeatherKit's
  `WeatherCondition` raw values are never stored; the adapter maps them once.

### The pass

- `EnrichmentKind.weather = "weather"` in `trip_enrichments`, run by `EnrichmentScheduler` after
  `namePlaces`, background priority, newest drives first. `done` when the row is written; a failed
  point (`LookupFailure`) leaves the trip `retry` with the usual backoff; the points already
  answered stay in Layer 1 and cost nothing on the retry.
- `WeatherLookup` changes to throw `LookupFailure` and return a `WeatherHourReading`, so offline is
  never read as "no rain" (the "Unknown is not zero" rule).
- `TripWeatherFacts` (pure, `Core/Domain/Journey`): points of a drive from its packed track and
  times, and facts from the readings. Nonisolated, `@concurrent` entry for the track walk.

### Who reads what

| Reader | Reads |
|---|---|
| Journey detail: a weather line ("Rain at the start · 24 °C → 22 °C") | facts always; figures from Layer 1 when present (asked on open if expired) |
| Feed rain tag (`FeedPublisher`) | `trip_weather` (D4); no request of its own. Absent at publish time: asks the same service (one key, one request), else `unknown` |
| Later: Journeys filter "Rain", narrative "in heavy rain" (ADR 0012), badges | facts only |

Attribution (Apple Weather mark + legal link) wherever weather shows: `WeatherAttribution` moves to
`DesignSystem`, used by the Feed and Journey detail.

### Slices

1. **Facts without a screen:** `WeatherHourReading`, throwing `WeatherLookup`, `LocalCache.weatherHours`,
   `TripWeatherFacts`, `trip_weather` in `v1_initial`, `EnrichmentKind.weather`, the pass; the Feed
   reads facts. Device check: requests per drive on the pulled drives, and the real
   `expirationDate` of a past-hour answer (it sets D3).
2. **Journey detail weather line** with attribution; screenshots Light/Dark, xxxLarge, Vietnamese.
3. Later, each its own plan: Journeys filter, narrative, badges.

## 3. Acceptance criteria

- A drive saved offline gets its facts later, once; recording, figures and replay never wait.
- Requests: one per distinct cell and hour of a drive; reopening a drive inside the cache life makes
  none; a whole pass stays inside the gate (100 a day).
- `trip_weather` holds only the columns above; no Apple figure, coordinate or cell anywhere in the
  database, the tracking log or a backup (a test reads the schema and the backup format).
- Offline with no cache: the detail page shows the facts or nothing, never a 0 °C or "clear".
- Without WeatherKit (`CARODO_WEATHERKIT` empty, Personal Team) the pass records nothing and no
  screen shows weather.
- Tests on both sides of each threshold (`low_visibility`, `strong_wind`, the points of a drive at
  59/60/61 minutes) and the sky mapping for every `WeatherCondition` case.

## 4. Non-goals

Live weather while driving, forecasts, alerts, minute data, weather on the share card (its own
decision later), syncing weather, storing any Apple figure for good.

## 5. Files and docs (carodo-ios)

- Code: `Core/Weather/` (lookup, reading, cache use), `Core/Domain/Journey/TripWeatherFacts.swift`,
  `Core/Domain/Journey/TripEnrichment.swift`, `Core/Persistence/DatabaseManager.swift` +
  a GRDB store, `Core/Persistence/DataOwnership.swift`, `Core/Maintenance/LocalCache.swift`,
  `Core/Recording/EnrichmentScheduler.swift`, `Core/Feed/FeedPublisher.swift`,
  `App/DependencyContainer+*.swift`, `DesignSystem/` (attribution), Journey detail (slice 2),
  `Resources/Localization` (slice 2).
- Docs in the same change: `docs/data-model.md` (`trip_weather`, `weather` kind),
  `docs/architecture.md` (LocalCache table, enrichment passes, derived insights: the WeatherKit
  terms), `docs/privacy.md` (what is sent, cached, stored), `docs/specs/journey-detail.md`,
  `docs/specs/feed.md` (rain tag source), `docs/specs/drive-recording.md` (Deferred row), an ADR
  (D6).
- Handbook: `drafts/weather.md` status → superseded by this plan for storage; `plans/backlog.md`
  "Weather along the way".

## 6. Owner decisions

- **D1 The facts kept** (the table above). *Recommended as listed.*
- **D2 A temperature band** (`cold`, `mild`, `warm`, `hot`) among the facts, for the narrative and a
  filter. *Recommended: not in v1*; the exact temperature shows from the cache, and a band can be
  added by a rules version later.
- **D3 The cache's limit.** (a) `expirationDate` alone; (b) `expirationDate` capped at 7 days, as
  Apple's place names. *Recommended (b)*, set once slice 1 measures `expirationDate` on the device;
  if Apple's answer is shorter than a day, revisit before slice 2.
- **D4 When a Feed row shows the rain chip.** (a) It rained where the drive started, at its
  start hour (today); (b) it rained at any point of the drive (`rain != none`). *Recommended (b)*:
  a drive that set off dry and ran into rain is a rainy drive to the reader. Only a yes/no leaves
  the phone, as today (the API's `weather` field is unchanged). The chip's copy says "met rain",
  not "it was raining": `row.rain` "🌧 Rain" / "🌧 Mưa trên đường" (owner, 2026-11-19; was "🌧 Mưa", which reads
  like a forecast; "🌧 Gặp mưa" if the longer one crowds the row at xxxLarge, checked on the
  slice 1 screenshots), its translator comment "the drive met rain at some point (Apple Weather)".
- **D5 Points.** (a) start and end only; (b) start, end and each full hour. *Recommended (b)*:
  long trips are where the weather changes; the cost is one request an hour.
- **D6 An ADR** "WeatherKit: figures cached, facts kept" (carodo-ios 0021). *Recommended*: it binds
  every later weather feature.
- **D7 The cell** stays 0.1° (`WeatherRounding`) for every point. *Recommended*: weather is coarse at
  that scale and one rounding serves the Feed and the detail page.

Schema (`trip_weather`, `weather` kind), a cache and the Feed tag's meaning are contracts (P6):
nothing is built before these are approved.
