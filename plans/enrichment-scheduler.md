# Enrichment scheduler — one owner for outside lookups, per-provider failures, budgets in requests

Status: **approved, D1–D6 as recommended (owner, 2026-11-17); slices 1 and 2 done (carodo-ios `42e434a`, `16efbd7`; slice 3’s ADR 0020 and docs went with slice 2).** Follows carodo-ios
`42f93fb` (place names show as they arrive) and `ce1029a` (`LocalCache`, the caches' registry).
Becomes carodo-ios ADR 0020 once approved.

**Owner decisions already made (2026-11-17):** a failure of one provider never stops the others
(rate limit, 5xx, timeout, a temporary geocoder error prove nothing about the device); only clear
loss of connection stops a pass. `next_attempt_at` moves only for work chosen or tried in that
pass. Budgets count real requests, not trips. A response several trips share is asked once. The
app is not to call Weather, OSM, places and toll services all at once on every launch. Earlier
(2026-11-15, `geodata-osm.md`): OSM and every non-Apple provider are reached through the Carodo
backend, never from the phone directly.

**The architecture (owner, 2026-11-17).** Two kinds of caller, one gate per provider, under the
adapters:

```
EnrichmentScheduler (passes) ─┐
Screens (repositories, caches)─┼─▶ existing adapters ─▶ ProviderGate ─▶ Apple / WeatherKit / backend
FeedPublisher (weather)      ─┘
results back to the caller: the scheduler → GRDB (ledger, trip_gaps, places);
the name caches → LocalCache
```

## 1. Today (files read)

| What | Where | How it behaves |
|---|---|---|
| The pass | `App/DependencyContainer+Maintenance.swift` `enrichJourneys()` | Runs at launch (`CarodoApp.launch`), after a saved drive (`DriveFlow` 216), on every return to the foreground (`DriveFlow` 300, `MainTabView` 569). One at a time. In order: `healGaps` (if active), `namePlaces`, `matchPoints` (if active), `narrateJourneys` |
| Gap healing | `Core/Recording/GapHealing.swift` `run` | `limit: 10` **trips**, newest first. A trip may route several gaps and lead-ins, two requests each on two wheels. Any error: `retryLater = true`, the whole pass stops, the trip stays unchecked (`trips.gaps_checked_at IS NULL`) and is tried again on the next foreground |
| Point matching | `Core/Recording/PlaceDetectionRun.swift` | `limit: 20` trips, `budget: 12` **requests** per run (already counted per request). Error: stops, journey unmatched (`trips.points_version` below the rules) |
| Place naming | `PlaceNaming.run` (local cell keys, `trips.places_version`), then `PlaceNameCache.request` and `findProvincesCrossed` | Names asked through `MapDataCache`: 20 a minute, a 60 s pause after a failure **of that cache only**, nothing while not active |
| POI names | `POINameCache` (`MapDataCache`) | Its own 20 a minute, its own pause. Shares MapKit's per-app throttle with point matching, stations and directions, but nothing counts them together |
| Weather | `Core/Weather/WeatherLookup.swift`, called by `FeedPublisher` (line 175) at publish | One request per published drive; any error is `.unknown` and published as such, never retried |
| Errors | `PlaceLookupError.retryLater / .notAllowed` (`Core/MapLookup/PlaceLookup.swift`) | One bucket: offline, throttled, server error and bad answer are the same `retryLater` |
| Connectivity | `Core/Diagnostics/NetworkPath.swift` | `NWPathMonitor` kind (wifi, cellular, none…), used by the tracking log and the Feed |
| Background | `appIsActive` gates in `enrichJourneys` and `MapDataCache.isActive` | Nothing outside is asked while the app is not active. Keep |

**Problems.**
1. Every foreground re-runs gap healing and point matching for the same failed trips: no backoff,
   no memory of the attempt.
2. One failure stops a whole kind; a throttled MapKit search stops gap routing too only by
   accident of order, and an offline geocoder does not stop MapKit. Neither is a rule.
3. Budgets differ in unit (trips for gaps, requests for POIs) and in scope (per run, per minute,
   per cache); MapKit's shared quota is counted in three places.
4. `retryLater` hides why: a 429 and an empty answer cannot be handled differently.
5. Outside the place-name ring "none" and "failed" are not stored apart per job.

## 2. Proposal

### 2.1 Error classification — `LookupFailure`

One typed error every outside adapter throws (Apple's and `BackendService`'s), replacing
`PlaceLookupError.retryLater` (`.notAllowed` stays: a policy refusal, never sent).

| Failure | Raised for | Scope | Effect |
|---|---|---|---|
| `.offline` | `URLError.notConnectedToInternet`, `.networkConnectionLost`, `.dataNotAllowed`, `.internationalRoamingOff` | the pass | stop every network call of this pass; the job tried gets its backoff, nothing else moves |
| `.connection` | `URLError.cannotFindHost`, `.cannotConnectToHost`, `.dnsLookupFailed`, `.secureConnectionFailed` | the provider, the pass if confirmed | the provider pauses; the pass stops only with evidence of a general loss: a second provider fails with `.connection`/`.offline` in the same pass, or `NetworkPath.kind == .none` (read after the failure, never as a preflight) |
| `.throttled(retryAfter:)` | HTTP 429, `MKError.loadingThrottled` | the provider | the provider cools down (`Retry-After`, else 60 s doubling to 15 min) |
| `.server` | HTTP 5xx, `URLError.timedOut`, `MKError.serverFailure` | the provider | the job backs off; 3 in a row pause the provider for the pass |
| `.invalidResponse` | undecodable body, an unexpected status | the provider | logged by provider and kind (no coordinates), the job backs off; never read as offline |
| *success, none* | `CLError.geocodeFoundNoResult`, `MKError.placemarkNotFound`/`.directionsNotFound`, an empty result | — | stored as `none`; not asked again until its rules version changes |

Apple's frameworks do not say which of offline, throttled or a server fault a `CLError.network`
was: it is `.server` for that provider only (never `.offline`). `NetworkPath` then decides whether
it was the device. **Assumption to check on an iPhone**: the `CLError`/`MKError` codes in
airplane mode and when throttled (a Live test beside `MapKitPOINameLookupLiveTests`).

### 2.2 Provider gate — budgets in requests (the most important part, owner 2026-11-17)

**Every outside request goes through its provider's gate**: a pass's jobs and every on-demand
request alike (a screen's place and POI names, Provinces Crossed on an opened drive, the fill-up
sheet's stations, a place's Find Nearby, weather at publish, a backend geodata call). The unit is
one request actually sent, never a trip: a trip with 3 gaps to route reserves 3 MapKit requests; a
lead-in on two wheels reserves 2 (driving and walking); geocoding outside Vietnam reserves 2
(Vietnamese, then the person's language); two trips needing the same lookup key send 1.

```swift
nonisolated enum Provider: String, CaseIterable, Sendable {
    case appleGeocoder
    case appleMapKit
    case weatherKit
    case carodoBackend
}
```

The raw value appears in the ledger's `last_failure` context and in the log, so it is a name that
is data (iOS invariant 8): never renamed.

`ProviderGate` (an actor in `Core/MapLookup`, one instance per `Provider`, created only by
`DependencyContainer`; `ArchitectureTests` fails on a gate created elsewhere, as for lookups):

- `reserve(_ units: Int) throws(LookupFailure)`: takes the units from the minute's, the pass's
  and the day's budget, or refuses (`.throttled` with the wait) while cooling down or spent. An
  adapter reserves before each call it makes, so the count is what was sent.
- **Single flight by key.** `request(key:units:_:)` runs the call once for a key: a second caller
  with the same key while it runs (the scheduler and a screen, two trips) awaits the same answer
  and spends nothing. Keys: a cell (geocoder), a POI identifier or a rounded search centre and
  radius (MapKit), the rounded gap ends and mode (directions), the ~11 km cell and hour
  (weather), the tile (backend).
- **Failures.** `record(_ failure: LookupFailure)` sets the provider's cooldown (2.1); the
  scheduler reads `.offline`/confirmed `.connection` to stop its pass.
- A screen's request over budget gets `.throttled` and shows what it shows when unknown; it
  never waits in the gate (the caches queue it as they do now).

**Not through a gate**: map tiles drawn by `Map` and `MKMapSnapshotter` (rendering, not a
service request; assumption to confirm in Apple's MapKit usage terms), and the Feed and account
calls, which keep `APIClient`'s own retry and are not enrichment.

The budgets:

| Provider | Covers | Per minute | Per pass | Per day |
|---|---|---|---|---|
| `apple.geocoder` | `CLGeocoder` (`PlaceNameCache`, provinces) | 20 | — | — |
| `apple.mapkit` | `MKLocalSearch`, `MKMapItemRequest`, `MKDirections` (POI names, matching, stations, gap routing) | 30 | 20 | — |
| `weatherkit` | `WeatherService` | 10 | 10 | 100 |
| `carodo.backend` | geodata (OSM, tolls) later; the Feed keeps its own client | 30 | — | — |

The numbers are hypotheses to tune, like `docs/tracking.md`'s (D2). `MapDataCache`'s own
`reserveLookup` and its 60 s pause move into the gate, so a screen's lookups and a pass's share
one count and one cooldown. Cooldowns live in memory: a relaunch starts with none, and the jobs'
`next_attempt_at` (2.3) keeps a relaunch from asking again at once.

**Shared responses inside a pass.** Beyond single flight, a pass keeps the answers it got by key
until it ends: a later job with the same key (two trips starting at the same cell, the same
weather hour) reads it and spends nothing.

### 2.3 Ledger — `trip_enrichments`

Local and derived (`DataOwnership`: derived, deleted with its trip; never synced, never in a
`.carodo`; no coordinates):

```
trip_enrichments(
  trip_id TEXT NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,              -- gap_route | poi_match | (later) weather | geodata
  rules_version INTEGER NOT NULL,
  status TEXT NOT NULL,            -- done | none | retry | failed
  attempts INTEGER NOT NULL DEFAULT 0,
  next_attempt_at REAL,            -- UTC epoch; NULL unless status = retry
  last_failure TEXT,               -- offline | connection | throttled | server | invalid_response
  updated_at REAL NOT NULL,
  PRIMARY KEY (trip_id, kind)) WITHOUT ROWID
```

- **Due** = no row, or `rules_version` below the kind's, or `status = 'retry' AND
  next_attempt_at <= now`. `done`/`none` at the current version are never due; `failed` waits
  for a new rules version or Developer → Retry enrichment.
- **Backoff** for a tried job: 5 min, 1 h, 6 h, 1 day, 1 day…; after 8 attempts `failed` (D4).
  A `.throttled` job's next attempt is no earlier than the provider's cooldown.
- **Only what was tried moves.** A pass stopped by `.offline` writes the job it was on; the trips
  it never reached keep their rows as they were.
- **Replaces** the external half of today's markers (D1): `trips.points_version` and
  `trips.gaps_checked_at` go; `trip_gaps.rules_version` stays (it versions the gaps themselves).
  Local derivations keep their columns (`places_version`, `narrative_version`,
  `trip_new_roads.rules_version`): they never fail for a network reason.

### 2.4 `EnrichmentScheduler`

Replaces `enrichJourneys()`; owned by `DependencyContainer`; tested on fakes with an injected
clock.

- **Triggers.** A drive saved (always); launch and foreground only if the last pass ended over
  15 minutes ago (D3) **or** a drive was saved since. Never while not active (kept rule).
- **A pass.** Local steps first (`PlaceNaming`, narratives: no network); then the due jobs,
  newest trips first, kind by kind (`gap_route`, then `poi_match`; later `geodata`). Each job
  reserves its requests on its provider's gate: a provider out of budget or cooling down skips
  its jobs (untouched, not "tried"); the other providers go on.
- **Lazy by default.** Weather and toll/geodata are asked when an action or a screen needs them
  (publish, an opened Journey Detail), through the same gate and ledger, never as a sweep over
  history. The screen-driven caches (`PlaceNameCache`, `POINameCache`) keep their queues and use
  the gate.
- **Log.** One line per pass (`docs/tracking.md#one-line-per-moment`): per kind tried / done /
  none / retry, per provider failures by class, requests spent. No coordinates, no trip ids in
  the shared log.

### 2.5 Shape of the scheduler (added 2026-11-18, from the app composition audit)

Added after D1–D6 were approved; it changes no decision, only where the code lives. Read
[`../audits/2026-11-18-ios-app-composition-audit.md`](../audits/2026-11-18-ios-app-composition-audit.md)
F1 and F2 before slice 2. Approved with the audit's D1–D4 (owner, 2026-11-18): slice 2 follows it.

- **Its own type, not container code.** `EnrichmentScheduler` is a `final class` in
  `Core/Recording` that owns the pass and its state: the single-flight flag (today the container's
  `isEnriching`), the narration skips (`narrationSkips`), the cooldown clock of D3. Nothing about
  the pass stays on `DependencyContainer`.
- **Everything through `init`.** The journal, place and trip stores, the gates, the narrator, the
  gap router and point services, `appIsActive`, the clock and the tracking log are `init`
  parameters. No property assigned after construction, no `configure()`. Built once in
  `DependencyContainer.live()` (and in `+Samples` / `unsaved` with fakes), held as
  `let enrichment: EnrichmentScheduler`.
- **The steps are called directly** (`GapHealing.run`, `PlaceDetection.run`, `PlaceNaming.run`,
  `JourneyNarration.run`): no step protocol, there is one caller (AGENTS.md, protocols only at real
  boundaries).
- **`+Maintenance` loses the pass, with no wrapper left:** `enrichJourneys`, `healGaps`,
  `namePlaces`, `matchPoints`, `narrateJourneys` go; callers (`CarodoApp.launch`, `DriveFlow`,
  `MainTabView`) call `container.enrichment.run(trigger:)` with the trigger of 2.4.
  `findProvincesCrossed`, milestones and new roads stay in `+Maintenance` for now: the audit's
  later step moves them.
- **Tests build the scheduler alone** on fakes and an injected clock, not a whole container.
- Leave `+Connect` and `CarodoApp.wireCallbacks` as they are: the audit's F2 step reshapes them
  after this slice is committed.

## 3. Scope, non-goals

In: 2.1–2.4 for gap routing, point matching, the two name caches and weather at publish (gate
only, D6). Out: SQLite for the Apple caches (step 3, with weather storage); geodata/toll
providers themselves (`geodata-osm.md`; they plug in as a `kind` and the `carodo.backend` gate);
`BGProcessingTask`; any change to what is sent (privacy rules unchanged).

## 4. Owner decisions (with a recommendation)

- **D1 — the ledger replaces `points_version` and `gaps_checked_at`.** Recommend yes: one
  source for "was this asked", no two markers that drift. Schema change in `v1_initial`
  (pre-release; reinstall).
- **D2 — the budgets in 2.2**, MapKit as one shared provider. Recommend yes, tuned with device
  runs.
- **D3 — 15-minute foreground cooldown**, a new drive bypasses it. Recommend yes.
- **D4 — backoff 5 m / 1 h / 6 h / 1 d, `failed` after 8 attempts**, Developer → Retry
  enrichment resets `failed`. Recommend yes.
- **D5 — evidence for stopping a pass on `.connection`**: a second provider's connection failure
  or `NetworkPath == .none`. Recommend yes.
- **D6 — weather**: through the gate now (budget, classification); its ledger row and any stored
  value wait for step 3 and a read of WeatherKit's storage terms. Recommend yes.

## 5. Slices (each one commit, proven)

1. **`LookupFailure` + `ProviderGate`**, no schema: adapters classify; `MapDataCache`, point
   matching, gap healing, stations, Find Nearby, provinces and weather reserve on the gate; gap
   healing's limit becomes requests. Tests: the table in 2.1 row by row on fakes; a 429 cools one
   provider while another answers; a trip with 3 gaps spends 3; two trips with one key spend 1
   (single flight and the pass's answers); two-call geocoding reserves 2; an on-demand screen
   lookup and a pass share one MapKit count. Enforced by structure, not a source rule: each Apple
   or backend adapter takes its `ProviderGate` in `init` and calls the framework only inside
   `gate.request`, so no adapter exists without its gate; `ArchitectureTests` only adds
   `ProviderGate` to the lookups the composition root alone creates.
2. **Ledger + scheduler**: `trip_enrichments` in `v1_initial`, `DataOwnership`, the scheduler
   replacing `enrichJourneys`; `points_version`/`gaps_checked_at` removed. Tests: due selection;
   only tried jobs move on `.offline`; backoff steps and `failed`; cooldown and the new-drive
   bypass; a shared key asked once for two trips; erase and trip delete take the rows.
3. **Docs**: ADR 0020; `docs/architecture.md` (Derived insights and enrichment, Map lookups table
   gains the gate), `docs/data-model.md` (the table), `docs/tracking.md` (the pass line),
   `docs/privacy.md` unchanged in substance.

## 6. Acceptance

- Launching twice within 15 minutes with nothing new asks no outside service.
- Offline (airplane mode) foreground: at most one request per provider is attempted, then
  nothing until backoff; trips not reached keep their rows.
- A 429 from one provider never delays another's jobs.
- Budgets in the log are requests, and no provider exceeds its per-minute figure in a test that
  runs a pass with 50 due trips.
- `task lint`, `task warnings`, `task test` pass; device check still required for 2.1's
  assumption and the airplane-mode run.

## 7. Files

`Core/MapLookup/{PlaceLookup,POINameLookup,MapKitPOISearch,MapKitStationFinder,AppleMapsGapRouter,MapDataCache}.swift`,
new `Core/MapLookup/ProviderGate.swift`, `Core/MapLookup/LookupFailure.swift`,
`Core/Weather/WeatherLookup.swift`, `Core/Recording/{GapHealing,PlaceDetectionRun}.swift`,
new `Core/Recording/EnrichmentScheduler.swift` (beside the runs it schedules),
`Core/Persistence/{DatabaseManager,GRDBJourneyRepository+Derived,GRDBJourneyRepository+Places}.swift`,
`DataOwnership`, `App/DependencyContainer+Maintenance.swift`, `App/DriveFlow.swift`,
`App/MainTabView.swift`, `App/CarodoApp.swift`, the matching tests and docs.
