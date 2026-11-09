# V2.3.0 Journey Enrichment & Driving Dynamics: architecture and data-readiness audit

Status: audit only, 2026-11-08. No code changed. Waiting for the owner's decisions (F) before any slice.

Method: read the recording, persistence, analysis and Replay sources (references below), and
measured the real telemetry in the pulled device databases (`drive-data/`, 3 iPhones, 17 completed
drives, 17,856 fixes, about 5.2 hours of driving). Only aggregate figures were printed; no
coordinate left the databases. The scripts are throwaway (session scratchpad), not committed.

---

## A. Current architecture (as built)

### A.1 Lifecycle

| Stage | Owner (file) | What happens |
|---|---|---|
| Acquisition | `Core/Recording/LocationSource.swift` (`CoreLocationSource`) | Standard `CLLocationManager` updates, `distanceFilter = none`, `pausesLocationUpdatesAutomatically = false`, background updates on only while a drive records. Accuracy and activity type come from one pure rule, `RecordingGPS.settings` (`Core/Recording/RecordingGPS.swift`): `best` on battery, `bestForNavigation` while charging, `hundredMeters` + 50 m filter after a 60 s stop **only** in Low Power Mode (or with `lowerWhileStoppedOnBattery`, off in production). Bicycle uses `.fitness`. |
| Detection (Auto Mode) | `Core/Location/CoreLocationServices.swift` (second manager for detection GPS), `Core/Tracking/DrivingDetectionEngine`, `AutoModeCoordinator` | Region exit / significant change wakes; detection fixes confirm; the session starts with a seed of detection fixes and a later lead-in (`GapHealing`). |
| Sample mapping | `LocationSample(location:)` | Kept from `CLLocation`: timestamp, lat/lon, altitude, speed, course, horizontal/vertical/speed/course accuracy; barometric pressure is added by the session. **Not kept:** `ellipsoidalAltitude`, `floor`, `sourceInformation` (simulated / accessory-produced). |
| Filtering + metrics | `Core/Recording/RouteRecorder.swift` (pure, `rulesVersion = 1`) | Rejects: accuracy ≤ 0 or > 50 m, older than 10 s, non-increasing time, implausible (> 70 m/s) or inconsistent steps (kinematic bound). After 3 jumps the segment breaks. A stop anchor holds position while stopped (≤ 1 m/s for 10 s; leaves at a trusted 2 m/s or 100 m). Top speed only from trusted Doppler speed (`speed > 2 × speedAccuracy`). |
| Live session | `Core/Recording/DriveSessionManager.swift` | One state for every start (manual, Auto Mode, Shortcut). `ingest` feeds `StopDetector` (auto-finish) and the recorder; **only accepted fixes** are written. Pause increments `segment`; recovery (`resume(_:)`) replays stored samples and treats the time away as a gap in the same segment. |
| Persistence while live | `TripWriter` → `trip_points` (WITHOUT ROWID, `(trip_id, sequence)`) | Batches of 10 fixes or 15 s; flushed on pause, background and when GPS is lowered. Every field above, as REAL columns. |
| Completion | `GRDBJourneyRepository.pack` → `trip_tracks` (`TrackCodec` v2, ADR 0004) | Lossless at stored precision (1 ms, 1e-7°, 1 cm, 1 cm/s, 0.01°, 1 Pa), ~7 B/fix. **Fixes after the drive's end (the parked minutes before auto-finish) are deleted** together with gaps reaching them. |
| Derived, stored | `trips` row (figures, `departed_at`/`arrived_at`, `motion_*_s` totals, `recorder_version`, `places_looked_up_at`, `gaps_checked_at`, narrative + version), `trips.route` (Douglas–Peucker 8 m display route, `RouteCoding`), `trip_gaps` (Apple Maps-routed gaps, `rules_version`), `geocoded_cells` (`lookup_version`) | Re-derived at launch when `RouteRecorder.rulesVersion` changes (`SummaryRefresh`). |
| Derived, on demand | `TripReplay.metrics` → `JourneyDetailAnalysis` (`@concurrent`), `SlowMoving`, `JourneyAnalysis.stops/stopBands/speedShares/elevation`, `TrimTrack` | Journey Detail replays the **raw track** through the same recorder every visit (O(n)), never the display route. |
| Replay | `Core/Replay/ReplayTimeline.swift`, `ReplayRoute.swift` (R.1, partly uncommitted work of another session) | Keyframes from `TripReplay.metrics(onStep:)`; stops > 1 min and jumps compressed; reserved slot for R.3 highlights; spec says enrichment becomes a highlight source "read when the timeline is built, never while playing". |
| Edits | Trim (`trim_start_at/end_at`, non-destructive), merge / Stop and wait (`parent_id`, each part its own segment), split | Raw track of every part kept; reads cut to the trim. |
| Sync | `docs/sync.md` | The packed track travels to iCloud as an asset; **derived data never travels**: each device re-derives. A journey from another device can exist with only its display route until the track arrives. |

### A.2 The four layers, kept apart today

1. **Raw telemetry** (accepted fixes): `trip_points` → `trip_tracks`. Complete for accepted fixes, lossless.
2. **Filtered telemetry**: not stored; reproduced deterministically by replaying layer 1 through `RouteRecorder` (positions held at the stop anchor, speed 0 while held, healed gaps inserted).
3. **Display geometry**: `trips.route` (8 m DP), plus the Map's coarser levels; never used for figures when a track exists.
4. **Derived metrics**: the `trips` figures (versioned by `recorder_version`) and on-demand analyses.

This separation is already right. **No duplicate storage is needed** for any feature below: every
candidate algorithm reads layer 1 (or layer 2 by replay) at O(n), the same cost Journey Detail
already pays.

### A.3 Measured telemetry (17 drives, 3 iPhones, 2026-11-06…08)

| Measure | Value | Meaning |
|---|---|---|
| Fix interval | 98.8 % ≤ 1.1 s; p50 1.00 s; p99 1.94 s | Steady 1 Hz, including background recording. |
| Gaps > 5 s inside a segment | 0–28 per drive; > 30 s: one in 17 drives | Tunnels / urban canyons; a few drives are patchy. |
| Horizontal accuracy | median 8–14 m | Fine for stops and POI radius, not for lane-level geometry. |
| Speed present | 88–100 % of fixes | Some fixes come without Doppler speed. |
| Speed accuracy | p10 0.72, p50 1.41, p90 3.63, p99 4.07 m/s | Single-step Δv noise is about the size of a hard-braking threshold. |
| Course accuracy (moving > 3 m/s) | per-drive median 11–27°; only 25 % of moving fixes under 10° | Too coarse for cornering. |
| Barometer | 94–100 % of fixes | Already used for elevation. |
| \|a\| from consecutive Doppler speeds | p50 0.23, p99 1.71, max 5.38 m/s² | 18 one-step spikes > 3 m/s², **none lasting two steps**; the spikes' speed accuracy median is 2.97 m/s: noise. |
| a over a 3 s window | braking max 2.29 m/s² (0.23 g); acceleration max 2.73 m/s² | **Zero** events at the architecture doc's −0.30 g hypothesis in 5.2 h. |
| Lateral v·dψ/dt (v > 5 m/s) | p99 2.13, max 8.6 m/s²; with course accuracy < 10°: max 7.3 | Physically implausible peaks: course noise, not cornering. |

What the zero means is **not yet known**: either these drives had no harsh events (plausible) or
Core Location's filtered speed lags and flattens a real peak. Only labelled drives can tell.

---

## B. Data-readiness matrix

Historical compatibility applies to every row: every journey since the clean database
(2026-11-07) has a v2 track with all accuracies, so it can be (re)analysed. A journey synced from
another device before its track arrives has only the display route: it shows no enrichment until
the track lands. A trimmed journey is analysed inside its trim; a joined journey part by part.

| Feature | Available | Missing | Limits | Feasibility |
|---|---|---|---|---|
| Temporary stops (15 s – 5 min) | 1 Hz speed, stop anchor, `JourneyAnalysis.stopDurations` (gap-aware), `StopBands` | A stop's interval and position as values (today only durations/counts) | Cannot tell a light from a queue (the code says so) | **Ready** |
| Longer stationary periods in a journey | The above + joined waits (`parent_id`, no walking during the wait) | — | A wait > 5 min **with** walking becomes two journeys (by design) | **Ready** |
| GPS loss vs stationary | Gap thresholds (`maximumObservedGapS` 30 s), positions and speeds at both edges, `GapHealing` | Whether GPS was **lowered** during the gap (Low Power Mode) is only in the tracking log, not on the trip; rejected fixes are counted, not kept | A gap whose two edges sit within the stop radius at speed 0 is "probably stationary"; otherwise unknown | **Partial** |
| Parking vs traffic congestion | `SlowMoving` (crawl ≥ 60 s and ≥ 100 m), stop durations | Per-stop Core Motion evidence (walking during the stop) | Parking mid-drive with walking is cut out by design (the drive ends) | **Partial** |
| Rest stop | Duration only | Walking evidence, POI | Real rest stops (walk to a café or toilet, > 5 min) **end the drive**: they live between journeys, not inside one | **Partial**, mostly **Blocked inside a journey** |
| Fuel stop | Stop interval + position, `MapKitStationFinder`'s POI query pattern, `fuel_logs` with `trip_id` + coordinates (ground truth) | POI lookup around a past stop, its cache | Attendant-pumped fuel (common in VN) stays within the 5 min grace or is joined; dense streets put many POIs within 50 m | **Partial** |
| EV charging stop | As fuel, `vehicles.fuel_type` | — | A charge lasts longer than the grace and the person usually walks: almost always a **journey boundary** (end of one, start of the next) | **Blocked inside a journey**; **Partial** as journey-end context |
| POI context | MapKit POI request already used (ADR 0017), `geocoded_cells` cache with `poi` field and `lookup_version`, `Place.contains` for private places | Lookup around stops, a store for results, terms review | Throttling (`MKError.loadingThrottled`), offline, ambiguity | **Partial** |
| Weather | Start/end time zone, times and positions; derived-and-versioned table pattern | WeatherKit capability, paid account, service code | Historical hourly data exists in WeatherKit (verify the range and terms before building); attribution is required on every surface showing it | **Blocked** (account/entitlement), architecture **ready** |
| Strong acceleration | 1 Hz Doppler speed + speed accuracy | Calibration on labelled drives | 1 s differencing is noise; 3 s windows look sane but are uncalibrated; a filtered speed may flatten peaks | **Partial** (shadow only) |
| Hard braking | Same | Same + controlled test | Same; no event above −0.23 g seen in 5.2 h | **Partial** (shadow only) |
| Speed fluctuation / stop-and-go | `SlowMoving`, stop bands, speed shares, smoothed windows | — | Descriptive, not judgemental | **Ready** |
| Aggressive cornering | Course + course accuracy | Yaw rate (gyroscope) | Course noise produces 7–9 m/s² phantom lateral accelerations | **Blocked** with GPS only |
| Smoothness indicator | Windowed acceleration, jerk | Calibration, a product meaning | Any score invites "safety score" reading | **Partial**, not recommended yet |

---

## C. Technical risks (highest first)

1. **Wrong driving events (High).** One-step differencing yields false "hard braking" every ~17
   minutes of driving in this data; lateral estimates from course are wrong by a factor of 3–4.
   Only a windowed derivative with speed-accuracy gating, a minimum duration and hysteresis, run
   as a shadow metric against labelled drives, is safe to try. Nothing should reach the screen
   before precision is measured.
2. **Attributing driving to the wrong person or vehicle (High).** `trips.rider` can be passenger;
   a car, a motorbike and a bicycle behave differently; the phone owner may not be driving. Driving
   insights must be gated on `rider == driver`, a known vehicle class, and they must describe the
   drive, never the person. No score, no collision or accident claim (out of scope by brief).
3. **Evidence that expires (Medium).** Core Motion keeps activity history for about 7 days, on the
   recording device only. Walking during a stop (the strongest "left the vehicle" signal) is read
   today only for walk-away and Stop and wait, never stored per stop. If Smart Stops wants it, it
   must be read and stored soon after the drive is saved; after 7 days, or on a second device, it
   is gone.
4. **Telemetry deliberately not kept (Low–Medium, by design).** Rejected fixes (> 50 m, stale,
   jumps) are counted, not stored; the parked minutes after an automatic end are deleted at pack;
   GPS mode changes are logged, not stored on the trip; `sourceInformation` is dropped. None
   blocks the features above; the GPS mode change is the only one Smart Stops would miss (gap vs
   lowered stop). Recommendation: keep as is (no duplicate data) until a slice shows the need.
5. **Four stop definitions (Medium, exists today).** `RouteRecorder` (≤ 1 m/s for 10 s, leave
   2 m/s or 100 m), `StopDetector` (0.83 m/s for 30 s, resume 3.33 m/s or 100 m), the route-based
   `JourneyAnalysis.stopDurations` (≥ 60 s, gap-aware), and `TrimTrack.stops` (raw speed ≤ 1 m/s,
   ≥ 60 s, **not gap-aware**, a copy of the same idea on different input). The Trim sheet's stops
   can already differ from the route timeline's; Smart Stops on top would make a third reading.
   The first two have different jobs (live hold vs auto-finish) and should stay; the last two
   should be one function.
6. **Recording performance (Medium if violated, Low as planned).** Nothing below needs per-fix
   work while recording. Every enrichment runs after save, off the main actor, like place lookup
   and gap healing. The risk is someone hooking analysis into `ingest` or the writer's completion
   transaction; the rule must be written down.
7. **Privacy and third-party data (Medium).** A POI or weather request sends a coordinate to Apple.
   It must follow the geocoding rules in `docs/privacy.md`: never a point inside a private place,
   only stop positions (not the route), nothing logged. Storing a POI's name and category, and
   letting it travel in the backup, needs a check of MapKit's terms (place identifiers that can be
   re-resolved exist on newer iOS; verify the API level against the iOS 17 target).
8. **External lookups versus "derived data never travels" (Medium).** Re-deriving stops and
   dynamics on each device is cheap. Re-fetching POI and weather on each device costs quota and
   can disagree between devices. The person's confirmations are source data and must sync.
9. **AI narration (Medium).** ADR 0012 and `JourneyFacts` keep stops, fuel and weather out of
   the summary. Any enriched fact may enter only when confirmed by the person or measured
   (duration of a stop), with a new `JourneyFacts.version` and an ADR update.

---

## D. Minimal refactor proposal

### Must prepare now (before the first V2.3 feature; no schema, no UI)

1. **One stop segmentation.** Extend `JourneyAnalysis.stopDurations` into intervals with their
   anchor and evidence (start, end, anchor position, gap inside or at its edge, fix count);
   `stops`, `stopBands` and `TrimTrack.stops` read it. Behaviour change: the Trim sheet's stops
   become gap-aware like the route timeline (docs: `specs/journey-editing.md` if it describes them).
   Tests on both sides of 60 s and 30 s gaps.
2. **A track-quality measure, on demand.** A pure value from the raw track: fix continuity
   (share of 1 Hz intervals, longest gap), share of fixes with trusted speed, speed accuracy
   percentiles, course accuracy share. It is the *telemetry measurement confidence* every insight
   checks; computed with the analysis, never stored. Name to be checked against the codebase
   (`GPSSignal`, `TrackingHealth` exist and mean other things).
3. **Write the persistence rule down** (in `docs/architecture.md`, one paragraph): enrichment
   computed from the track is derived and recomputed (versioned, never synced); results of an
   external lookup are a local cache with `rules_version`/status (like `trip_gaps`,
   `geocoded_cells`); the person's confirmation is source data in an existing synced entity where
   one fits (a confirmed fuel stop is a `fuel_logs` row with `trip_id`). Plus: nothing in
   enrichment runs on the recording path.

### Can defer (until the slice that needs it)

- An enrichment table. Stops and dynamics need none (on demand, O(n)). The first table comes with
  the first external lookup or the first expiring evidence (walking during a stop): `trip_id`,
  kind, interval, rules version, status (pending / done / unavailable / failed-retry), compact
  payload, looked-up time. A P6 schema decision at that time.
- Per-stop Core Motion evidence, read at save (within the 7-day window).
- Storing GPS mode changes on the trip (only if gap vs lowered stop proves to matter).
- Core Motion device motion (gyroscope for cornering, a handling gate). Only after GPS-only
  braking/acceleration is measured; costs battery for the whole drive and needs orientation-free
  features (yaw-rate magnitude, not raw axes). P6.
- WeatherKit (paid account, capability: P6).

### Should avoid

- A generic `JourneyEvent` protocol, registry or enrichment service layer before two concrete
  kinds share real code. Stops, dynamics, POI and weather have different lifecycles.
- Storing smoothed speeds, accelerations or a second track. Re-derive from layer 1.
- Changing `RouteRecorder` filtering for dynamics: it would bump `rulesVersion` and change
  distances. Dynamics read the raw samples with their own gating.
- Per-route-point POI or weather queries; lookups inside private places.
- Cornering events from GPS course.
- A driving or safety score; any accident or collision wording.
- Unconfirmed enrichment in the AI summary.

---

## E. Proposed V2.3 sequence

| Step | What | Depends on | Acceptance | Tests |
|---|---|---|---|---|
| 2.3.0 | D "must prepare" 1–3 | — | Route timeline, stop bands and Trim agree on every stored drive; quality values for the 17 local drives look sane; docs updated | Unit: stop intervals both sides of thresholds, gaps, joined parts, trim; quality on synthetic tracks |
| 2.3.1 | Driving dynamics **shadow**: windowed longitudinal events (speed-accuracy gated, ≥ 2–3 s dwell, hysteresis, merge within a window, none across a gap or a held stop), event confidence; computed after save, logged as counts + `conf=` in the tracking log (no coordinates). No UI | 2.3.0 | Zero events on the noise fixtures; on device, labelled drives (normal city, highway, a **controlled** braking and acceleration run on a closed, safe area with a reference) give measured precision/recall | Deterministic fixtures: noise spikes, real ramps, gaps, missing speed, bicycle/motorbike classes, passenger |
| 2.3.2 | Smart Stops v1 (no network): each stop with its duration class and context: joined wait, at a saved place (`Place.contains`), a fill-up logged at that time, gap-ambiguous | 2.3.0 | Every stop's label explains its evidence; "unknown" is a result | Unit per rule; `fuel_logs` as ground truth on device |
| 2.3.3 | Walking-during-stop evidence (read at save, stored) | 2.3.2, schema approval | Present for drives within 7 days; absent, never guessed, afterwards | Pure classification tests; Motion denied path |
| 2.3.4 | POI candidates for stops ≥ a threshold: one request per stop, cached, status machine, private places skipped; the person confirms (fuel → a prefilled fill-up) | 2.3.2, terms check, schema approval | Offline drive shows stops without POI and fills later; no repeated request; no request for a private place | Fake search service; throttling and offline; ranking by distance and category |
| 2.3.5 | Weather (when the account allows): start and end, plus hourly checkpoints on long drives; snapshot with provenance and attribution | Account + capability (P6) | Missing weather hides; attribution on every surface | Fake service; checkpoint selection |
| 2.3.6 | Presentation: Detail (a "Stops and places" reading of the existing route timeline; a quiet driving line only once 2.3.1 is validated), Replay R.3 highlights, summary inputs | Each feature validated | Per product decisions in F | Screenshots (Light/Dark, large type, Vietnamese) |

Presentation guidance (no UI now): stops belong in the existing **Route timeline** (section 3),
not a new section; driving dynamics, if shown, as one descriptive line under **Driving Pace**
("smooth, steady pace"), never a list of "harsh events" by default; weather as a quiet chip near
the identity line; Replay markers read from the same values when the timeline is built.

---

## F. Open questions for the owner

1. **Dynamics: shown or only measured?** Is the goal a visible insight ("smooth drive", "3 firm
   brakes"), or a developer shadow metric until data proves it? Which tone is acceptable?
2. **Which drives get dynamics?** Cars only, or motorbikes too (common in Vietnam, where a phone in
   a pocket moves on its own)? Passenger journeys excluded?
3. **Stops between journeys.** Rest, food and charging stops usually end the drive (walking). Should
   Smart Stops cover the time *between* journeys of one outing, or only stops inside a journey?
4. **Confirmation.** May a confirmed fuel stop create a fill-up log (prefilled station and time),
   or should a confirmation be its own record?
5. **Core Motion device motion.** Acceptable to consider later for cornering and as a handling gate,
   at a battery cost during every drive?
6. **WeatherKit.** When the paid account comes: start/end only or along the way? May weather appear
   on a share card (it hints at place and time)?
7. **POI retention.** May a POI's name and category be stored with the journey and travel in the
   person's iCloud and `.carodo` backup, or only a category?
8. **Validation run.** Who drives the controlled braking/acceleration runs, where, and with what
   reference (a second phone, an OBD reader, a dash speed log)?

---

Source references: `Carodo/Core/Recording/{LocationSource,RecordingGPS,RouteRecorder,DriveSessionManager,TripWriter,TrackCodec,TripReplay,JourneyTrim,GapHealing}.swift`,
`Carodo/Core/Tracking/{StopDetector,WaitJoin,DriveConfidence,LocationSample}.swift`,
`Carodo/Core/Persistence/{DatabaseManager,GRDBJourneyRepository}.swift`,
`Carodo/Core/Domain/{JourneyDetails,JourneyDetailAnalysis,SlowMoving,Journey}.swift`,
`Carodo/Core/Location/{CoreLocationServices,MapKitStationFinder,PlaceLookup}.swift`,
`Carodo/Core/Motion/MotionActivity.swift`, `Carodo/Core/Narrative/JourneyFacts.swift`,
`Carodo/Core/Replay/ReplayTimeline.swift`; docs `tracking.md`, `architecture.md#algorithms--one-per-problem`,
`sync.md`, `privacy.md`, `specs/journey-detail.md`, `specs/replay.md`, ADR 0004, 0012.

---

## G. Owner decisions (2026-11-08)

V2.3.0 Foundation shipped in carodo-ios `fda2612` (one stop segmentation, `TrackQuality`, the
enrichment rules in `docs/architecture.md`).

| # | Question | Decision |
|---|---|---|
| 1 | Show harsh braking / acceleration? | Later, yes; for now **shadow mode only** (measured and logged, nothing on screen). |
| 2 | Cars or motorbikes? | Both, each with its own thresholds. Evaluated only when the person drove: the journey is sure and `rider == driver` (the rule `JourneyMerge` uses). Bicycles are not evaluated. |
| 3 | Smart Stops between journeys? | Yes, in two tiers: **Journey Stops** inside a journey (V2.3.2, verifiable GPS) and **Between-Journey Context** later. |
| 4 | Fuel stop confirmation | Opens a prefilled fill-up form; the person saves it. Never a log created by itself. |
| 5 | Core Motion | May be researched later; no continuous gyroscope. |
| 6 | Weather | Start and end for a short journey, checkpoints along a long one. Share card later. Still blocked on the paid account (WeatherKit). |
| 7 | POI in iCloud | Only what the person confirms syncs; suggested POIs stay a local cache until MapKit's terms are checked. |
| 8 | Who tests harsh braking | Simulated data first (proves the code), then a controlled real run with OBD or a reference instrument (proves the measurement: whether Core Location's speed flattens a real peak). |

### Between-Journey Context (tier 2): how it should be built

- **Never merges by itself**, never claims an activity (food, fuel, charging): a break between two
  journeys of one trip is a suggestion, not a fact. Statistics, mileage, milestones and history
  stay per journey.
- **No new data model.** The pairing exists: `JourneyMerge` lists only neighbours in the journal,
  same vehicle, both sure and both driven or both ridden. Tier 2 reuses that rule to find a break,
  with a shorter window than Merge's 6 h (proposal: about 2 h, to decide), and its only action is
  the existing, reversible Merge (Split here undoes it).
- Example: HCMC → Da Lat as Journey A (85 km), a 25-minute stop with a walk (fuel, coffee),
  Journey B (215 km). Stop and wait does not join them (walking, over 20 min); tier 2 shows the
  break between A and B and offers Merge.
- A Road Trip collection or multi-leg journey stays a later product decision; nothing is built for
  it now.

### Still to decide before V2.3.1

- The tier-2 window (2 h proposed).
- Motorbike thresholds: start from the car hypotheses (−0.30 g / +0.28 g) or measure first in
  shadow mode with no threshold shown? Proposal: log the windowed distribution per vehicle class
  first, set thresholds from data.
