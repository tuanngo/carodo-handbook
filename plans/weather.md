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

## 7. Slice 2 plan: the weather line on Journey detail

Status: **approved (owner, 2026-11-19): S1, S2, S4, S5, S6 as recommended; S3 approved with the
owner's wording below; S7 (sun and UV facts) approved.** Starts after PV-39 (the device check of slice 1).

### Today (files read)

| What | Where | How it behaves |
|---|---|---|
| The story's order | `Features/Journeys/Views/Detail/JourneyDetailView.swift` `story` | Identity, `JourneySummarySection` (tags, distance, time, speed), the trimmed line, the route timeline (the preview ends there), Journey Context, the Feed switch, Along the way, Driving Pace, elevation, milestones, drive logs, memories |
| Loading | `JourneyDetailViewModel.load()` | Reads the journey, the track, places; secondary reads (provinces, commute, merge candidates) fall back to hiding their section; the provinces are cached with the analysis (`JourneyDetailCache`) |
| Weather service | `Core/Recording/TripWeather.swift` | `facts(forJourney:)`: the stored facts, else looked up now and stored. Nothing reads one drive's figures from the cache yet |
| Attribution | `Features/Feed/Views/WeatherAttribution.swift` | Apple's mark (from `WeatherService.attribution`, light or dark) and "Other data sources"; Feed strings (`Feed.weatherMark`, `Feed.weatherSources`) |
| Units | `AppState.distanceUnit` (km or mi) | No temperature setting; `Measurement<UnitTemperature>` follows the region (°C in Vietnam, °F in the US) |
| Spec | `docs/specs/journey-detail.md#the-story-top-to-bottom` | No weather today; "Summary" says weather is never in the written summary (ADR 0012 keeps that) |

### Proposal

- **One quiet line under the figures** (after `JourneySummarySection`, before the trimmed line),
  an SF Symbol of the sky and one sentence, then the temperature when the cache has it:
  `🌧 Rain at the start, dry by the end · 31° → 28°`. No card: a fact of the drive, like the trimmed line.
  Hidden when the drive has no facts (not looked up, offline, a Personal Team build).
- **The sentence, from the stored facts only** (`JourneyWeatherLine`, pure, tested; S3 as the owner
  wrote it, 2026-11-19). A memory of the drive, never a forecast: no "soon", "expected", "seems".

  | Facts | English | Vietnamese |
  |---|---|---|
  | rain `all` | Rain all the way | Mưa suốt đường |
  | rain `part`, start rainy, end not | Rain at the start, dry by the end | Mưa lúc đi, tạnh lúc tới |
  | rain `part`, start not, end rainy | No rain at the start, rain by the end | Không mưa lúc đi, mưa lúc tới |
  | rain `part`, both ends dry | Rain on the way | Gặp mưa trên đường |
  | rain `none`, clear | Clear | Trời quang |
  | rain `none`, cloudy | Cloudy | Nhiều mây |
  | rain `none`, cloudy then clear | Clouds cleared | Mây tan, trời quang |
  | rain `none`, clear then cloudy | Clear, then cloudy | Trời quang, rồi nhiều mây |
  | rain `none`, fog at an end | Fog | Sương mù |
  | rain `none`, snow at an end | Snow | Tuyết |

  **Heavy rain in the sentence, only where the facts place it.** `start_sky` and `end_sky` say
  whether an end was `heavy_rain` or `storm`; `heavy_rain` with neither end heavy means a point in
  between (the points are the start, the hours, the end):
  - heavy at the start, end dry → "Heavy rain at the start, dry by the end" / "Mưa to lúc đi, tạnh lúc tới";
  - heavy at the end, start dry → "No rain at the start, heavy rain by the end" / "Không mưa lúc đi, mưa to lúc tới";
  - heavy between, both ends dry → "Heavy rain on the way" / "Mưa to giữa đường";
  - rain `all` with a heavy point → "Rain all the way · heavy at times" / "Mưa suốt đường · có lúc mưa to";
  - any other heavy case (rain at both ends, heavy at one) → the rain sentence and "· heavy rain" /
    "· mưa to".

  **One extra at most**, the first that applies and is not already said: heavy rain → low visibility
  ("· poor visibility" / "· tầm nhìn kém") → strong wind ("· strong wind" / "· gió mạnh"). "Sương
  mù · tầm nhìn kém" is allowed (fog and visibility are two facts).

  **Sun (owner, 2026-11-19, S7):** slice 2 starts by adding three facts to `trip_weather`
  (`v1_initial`, rules version 2, cache file v2 with the UV index): `start_daylight`,
  `end_daylight` (Apple's `isDaylight` at those hours) and `strong_sun` (a daylight point with UV
  index 8 or more, WHO "very high"). "Sunny" / "Nắng" is said only for a clear sky in daylight with
  UV 3 or more at that end ("Nắng lúc đi, mưa lúc tới"; a clear night stays "Trời quang"); "No
  rain" is never written as "sunny". `strong_sun` is the last extra: "· harsh sun" / "· nắng gắt".
  Extras in order: heavy rain → poor visibility → strong wind → harsh sun. The start's UV ≥ 3 needs
  its own fact: `start_daylight` is stored as "daylight with UV 3 or more" (`start_sunlit`,
  `end_sunlit`), so the stored columns are `start_sunlit`, `end_sunlit`, `strong_sun`. Tests on both
  sides of UV 2/3 and 7/8, day and night. No daylight column of its own (owner, 2026-11-19): a night drive is the
  drive's local hour (`PartOfDay`), never the weather; a sun-based night, if ever wanted, is computed
  on the device from the drive's time and place.

  The line wraps at xxxLarge, never cut. The sentence is never stored: facts only, worded on screen.
- **Temperature from the cache only:** the start's and the end's readings (`WeatherHourCache`), one
  value when they round to the same degree, formatted by `Measurement` for the region (S2). An
  expired entry is asked again on open, at screen priority (the gate keeps 3 a minute for screens),
  at most two requests; offline or refused, the temperature hides and the sentence stays.
- **A drive the pass has not reached** is looked up on open (`TripWeather.facts`), as the Feed
  does; the line appears when the answer comes (`.task`, its result checked against the journey
  still shown).
- **Attribution:** Apple Weather's mark and "Other data sources" at the end of the story while the
  line shows (S4). `WeatherAttribution` moves to `DesignSystem/` (it is used by two features), its
  strings to `Common`.
- **Model:** `JourneyDetailViewModel` gets `weather: JourneyWeatherLine?`, loaded after the track
  (the points come from the track it already read); `DependencyContainer` hands it `tripWeather`.
  `TripWeather` gains `endReadings(of fixes:)`: the start's and end's readings from the cache,
  asked when missing. Not cached with the analysis: facts change when the pass answers.
- **The Simulator** cannot sign WeatherKit: a DEBUG launch flag `-carodo.debugWeather rain|clear`
  makes the composition root build a fixed `SampleWeatherLookup` (`Core/PreviewData`), so the line
  can be reached by taps for screenshots (S5). No hook in a view or a model.

### Acceptance criteria

- A drive with facts shows the line under its figures in the preview state of the sheet; one
  without shows nothing and leaves no gap.
- The temperature shows only from a fresh cache entry or an answer now; offline with an expired
  entry the sentence shows alone; never "0°".
- Opening a drive with fresh cache entries sends no request; an expired one at most two.
- The attribution shows at the end of the story whenever the line shows, light and dark.
- VoiceOver reads the line as one sentence ("Weather: rain all the way, 31 to 28 degrees").
- xxxLarge: the line wraps, never cut; Vietnamese checked at xxxLarge.
- Tests: every row of the sentence table, the extras, one temperature vs two, the hidden cases;
  `endReadings` asking only what is missing.

### Non-goals

The weather on the route timeline's start and end, the Map, share cards, the narrative, a Journeys
filter "Rain", badges; a temperature unit setting.

### Files and docs

`Features/Journeys/ViewModels/Detail/` (`JourneyWeatherLine`, the view model),
`Features/Journeys/Views/Detail/` (the line), `DesignSystem/` (attribution moved),
`Core/Recording/TripWeather.swift`, `Core/PreviewData/` and `App/DependencyContainer*` (S5),
`Resources/Localization/Journeys.xcstrings` and `Common.xcstrings`;
`docs/specs/journey-detail.md` (the story's order, the line), `docs/specs/feed.md` (attribution's
home), `docs/operations/setup.md` (the launch flag), `docs/privacy.md` (a screen may ask).

### Owner decisions

- **S1 Where the line goes:** (a) under the figures, in the preview; (b) its own small card after
  Along the way. *Recommended (a)*: it is a fact of the drive, read at a glance like the distance.
- **S2 Temperature unit:** (a) the region's (°C in Vietnam, °F in the US); (b) follow km/mi.
  *Recommended (a)*: what the phone shows in its own Weather app.
- **S3 The sentences:** approved with the owner's wording (2026-11-19), as in the table above.
- **S4 Attribution at the end of the story** (as the Feed) rather than beside the line.
  *Recommended*: one quiet mark, not a logo in the summary.
- **S5 The DEBUG launch flag** for the Simulator. *Recommended*: the only way to show the line
  without WeatherKit on the Simulator, and it follows the QA rule (the composition root chooses).
- **S6 Ask on open** for a drive with no facts or an expired temperature. *Recommended*: at most a
  few requests at screen priority; without it an old drive shows nothing until a pass reaches it.
