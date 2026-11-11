# V2.3.2 — Smart Stops V1: implementation plan

Status: **built**, carodo-ios `365ceaa` (2026-11-09), after one review pass (fixed: the Merge sheet picking the wrong neighbouring trip, the marker as VoiceOver reads it, the times of a break). Still open: `technical-debt.md` (TD-1, KL-1, PV-1, PV-2). The final decisions are in **section 11**; where anything differs from section 11, section 11 wins.
Foundation: V2.3.0 `fda2612` (`JourneyAnalysis.stopIntervals`, `RouteStop`, `TrackQuality`), the
"silent stop" fix `2760b84` (another session, same function), and the decisions in section G of
`journey-v2.3-enrichment-audit.md`.

## 0. Principle: data leads, no activity labels

Every line about a stop belongs to exactly **one of three levels**, and its wording shows which:

| Level | Source | Example (EN / VI) |
|---|---|---|
| **Measured** | GPS: time, duration, a position inside a Saved Place's circle, the wait between two joined parts | "Stopped 4 min" / "Dừng 4 phút"; "At Home" / "Tại Nhà"; "Waited 12 min" / "Chờ 12 phút" |
| **Unconfirmed context** | An outside source (POI). **Not in V1** (no MapKit call) | (later) "Near a fuel station" / "Gần trạm xăng" |
| **Confirmed by the person** | A fill-up or an expense the person logged | "Fill-up logged" / "Đã ghi đổ xăng" |

**Never** a Coffee/Fuel/Rest/Charging Stop label inferred from a duration. A 4-minute stop is only
"Stopped 4 min". This is also a clean input for the Journey Narrator later: it may say only what is
measured or confirmed (ADR 0012 unchanged; V1 does not touch the Narrator).

## 1. Existing source to reuse

| Need | Already there | File |
|---|---|---|
| Stop segmentation (interval, start position, fix count, longest GPS gap, whether the end is estimated, silent stop) | `JourneyAnalysis.stopIntervals`, `RouteStop`, `minimumStopS` (60 s), `maximumObservedGapS` (30 s) | `Core/Domain/JourneyDetails.swift` |
| The replayed route every analysis reads | `TripReplay.metrics`, `JourneyDetailAnalysisBuilder` (`@concurrent`) | `Core/Recording/TripReplay.swift`, `Core/Domain/JourneyDetailAnalysis.swift` |
| A point inside a Saved Place | `PlaceMatch.place(atLatitude:longitude:in:)`, `Place.contains`, `SavedPlaceMark` | `Core/Domain/Place.swift`, `JourneyDetails.swift` |
| Fill-ups and expenses linked to the trip | `DriveLogs.linked: [DriveLogItem]` (time `at`; a fill-up has the station's coordinates when logged on the spot) | `Core/Domain/DriveLog.swift`, already loaded in `JourneyDetailViewModel` |
| Joined / merged waits | `JoinedPart` (`stoppedAt`, `waitS`), `joinedParts(of:)`, already loaded for the Split menu | `Core/Repositories/Repositories.swift` |
| Two neighbouring journeys | `mergeNeighbours(of:)`, `JourneyMerge.Pair`, `JourneyMerge.refusal`, `maxGapS` 6 h | `Core/Domain/JourneyMerge.swift`, already loaded for the Merge sheet |
| "Started where the previous trip ended" | `WaitJoin.Configuration.joinMaxDistanceM` (150 m), `joinMaxDistanceAutoStartM` (1,000 m) | `Core/Tracking/WaitJoin.swift` |
| GPS quality | `TrackQuality` | `Core/Domain/TrackQuality.swift` |

**How the screens use stop intervals today (audit):**
- **Journey Detail / Route timeline**: only one summary line, `StopSummary` ("2 stops · 4 min"), under the end. No single stops.
- **Trim**: `TrimTrack.stops` = `stopIntervals(≥ 60 s)`, for the "After a stop" chip and the snap marks.
- **Stop bands** (tracking log): `stopIntervals(≥ 15 s)`.
- **Replay**: does **not** use `stopIntervals`. `ReplayTimeline` compresses by the recorder's "held" state (> 60 s). This is where the two logics part (noted since V2.3.0). V1 does **not** change Replay; section 10 asks whether a later version unifies them.
- **Recording and auto-finish** (`RouteRecorder`, `StopDetector`): untouched.

## 2. The stop classification model

Classified **by evidence**, not by activity. One pure value, not stored:

```swift
/// One stop on a journey with what is known about it (docs/specs/journey-detail.md, Stops).
nonisolated struct JourneyStop: Identifiable, Equatable, Sendable {
    let stop: RouteStop                 // measured: interval, position, evidence (unchanged)
    let length: Length                  // measured: from StopBands' limits (1–5 min, ≥ 5 min)
    let wait: Wait?                     // measured: the wait between two joined or merged parts
    let place: SavedPlaceMark?          // measured: its position inside one of the person's places
    let logged: [DriveLogItem]          // confirmed: what the person logged at that stop
    let timing: Timing                  // measurement quality: .observed or .approximate (GPS gap)
}
```

- `Length`: reuses `StopBands`' limits (`mediumS` 60 s, `longS` 300 s); no second threshold.
- `Wait`: when the stop's interval holds the boundary between two parts (`JoinedPart.stoppedAt`).
- `Timing.approximate` when `endIsEstimated`, or when the stop holds a GPS gap that is **not** a silent stop (the car may have moved). A silent stop (the position unchanged) stays `observed`.
- **No** `activity`, `category` or `guess` field.

`JourneyStops.make(stops:places:logs:parts:)` is a pure function that only joins data (`Core/Domain/JourneyStops.swift`). It is not a new detector: it only reads `[RouteStop]`.

## 3. Evidence and confidence rules

| Evidence | Rule (hypothesis, tunable) | Level |
|---|---|---|
| Duration | `RouteStop.durationS`; with `≈` when `timing == .approximate` | Measured |
| Representative position | The run's first fix (always an accepted fix, ≤ 50 m). Used only against Saved Places; **no reverse geocoding** in V1 (section 10) | Measured |
| Saved Place | `PlaceMatch.place` at that position. Geometry only (inside the circle); it says nothing about what was done there | Measured |
| Joined/merged wait | A part boundary inside the stop | Measured |
| Logged fill-up/expense | An item in `driveLogs.linked` whose `at` falls in `[start − 5 min, end + 5 min]`, **or** a fill-up whose station coordinates are within 150 m of the stop's position. An item attaches to **at most one** stop (the nearest in time); an item that matches no stop still shows as today | Confirmed |
| GPS quality | Not a score: it only decides `observed`/`approximate` | — |

There is no "confidence" score for an activity, because no activity is inferred. Confidence here is
**the confidence of the time measurement** (`timing`), kept separate.

## 4. GPS gaps, trim, merge and split

- **GPS gaps:** already handled in `stopIntervals` (an estimated end after a gap > 30 s, silent stops).
  `JourneyStops` only reads it back as `timing`.
- **Trim:** the analysis runs on the trimmed track (as today). A stop cut in two by a trim becomes
  "waiting before leaving" or "parked" and is no longer a stop (a V2.3.0 test pins this). A logged item
  outside the kept part attaches to no stop.
- **Merge / Stop and wait:** the track holds every part, one segment each. The wait between two parts
  becomes a stop with a `wait`. Its position is where the car waited, not the first fix of the later part
  (V2.3.0 has the test).
- **Split:** only a new read after the split; there is no state to clean, since nothing is stored.
- **Replay:** unchanged.

## 5. Between-Journey Stops: conditions

A pure function `JourneyBreak.between(pair:earlierEnd:laterStart:)` in `Core/Domain/JourneyBreak.swift`.
It **calls** `JourneyMerge.refusal` and does not copy Merge's rules:

1. `JourneyMerge.refusal(pair) == nil`: neighbours, both sure, the same role (driver/passenger),
   compatible vehicles, a time gap from 0 to 6 h. **Merge's 6 h is unchanged.**
2. Both `rider == .driver`.
3. **The same vehicle**: both have a vehicle and it is the same one (stricter than Merge, which accepts
   one side without a vehicle; section 10).
4. `pair.gapS ≤ 2 h` (`JourneyBreak.maximumBreakS`, the owner's decision).
5. **Continuity of position**: the earlier trip's end and the later trip's start are within
   `WaitJoin.joinMaxDistanceM` (150 m), or within `joinMaxDistanceAutoStartM` (1,000 m) when Auto Mode
   started the later trip. **Reuses** exactly Stop and wait's two values (the same meaning: "started again
   where the previous trip stopped"). The start and end come from the display route (which always keeps
   both ends), not the raw track.
6. **Data quality**: a trip with no start or end point (an empty route) gets no suggestion.

The result is a measured fact: "25 min break before this drive". The **only** action: open the existing
Merge sheet. No automatic Merge, no Multi-leg model.

## 6. Performance and caching

- `stopIntervals` already runs in `JourneyDetailAnalysisBuilder` (off the main actor). V1 has the
  analysis keep `[RouteStop]` (≥ 60 s) instead of only `StopSummary`, and `StopSummary` is computed from
  that same list (no second segmentation).
- `JourneyStops.make`: O(stops × (logs + places + parts)). At most 20 places, and only a few logs and
  parts per trip, so it is negligible.
- `JourneyBreak`: reuses the neighbours the Merge sheet already loaded, **no extra query**.
- **No cache, no schema, nothing stored.** Everything is recomputed when the page opens, like the other
  analyses. If `JourneyDetailCache` holds the analysis, `[RouteStop]` goes with it.

## 7. Testing

**Unit tests** (`JourneyStopsTests`, `JourneyBreakTests`; synthetic data):
- Length: both sides of 60 s and 300 s.
- Saved Place: inside and outside the circle; a private Saved Place still matches (the person's own data).
- Logged items: both sides of ±5 min; station coordinates on both sides of 150 m; an item near two stops
  attaches to one; an unmatched item stays on the timeline.
- `timing`: a silent stop is `observed`; a tunnel-like gap is `approximate`; `endIsEstimated`.
- Joined and merged waits; a trim cutting through a stop; a trip with no stops.
- Between: each condition of `JourneyMerge.refusal` still blocks (pending, a different role, a different
  vehicle, > 6 h); both sides of 2 h; the same vehicle; both sides of 150 m and 1,000 m; an empty route;
  a passenger.
- No wording names an activity (a string test over the catalog).

**Regression:**
- Every stop test of V2.3.0 and of `2760b84` keeps its result.
- Read the 312 km trip in `drive-data/carodo/*.carodo` (a backup file, unencrypted) through `BackupFile`
  in the replay tool, printing figures only: 8 stops, 89 min expected (as in commit `2760b84`); print
  each stop's `JourneyStop` (duration, whether it has a Saved Place, whether it has an item, `timing`)
  and the Between pairs if any.
- Real data **never** enters the repo (P5).

**Screenshots** (once there is UI): Light/Dark, large Dynamic Type, Vietnamese; a trip with no stops, a
trip with 8 stops, one with a Saved Place, one with a fill-up, one with a joined wait, one with a break
between two trips.

## 8. Files expected to change

| File | Change |
|---|---|
| `Core/Domain/JourneyStops.swift` (new) | `JourneyStop`, `JourneyStops.make` (pure) |
| `Core/Domain/JourneyBreak.swift` (new) | The Between conditions, calling `JourneyMerge.refusal` |
| `Core/Domain/JourneyDetailAnalysis.swift` | Keeps `[RouteStop]`; `StopSummary` computed from it |
| `Features/Journeys/ViewModels/JourneyDetailViewModel.swift` | Joins stops with places, logs, parts; the break from the loaded neighbours. **Other sessions often edit this file**: stage only this work's hunks |
| `Features/Journeys/Views/JourneyDetailSummarySections.swift` | Route timeline: one line per stop (time, duration, measured or confirmed context); a break line between two trips with "Merge" |
| `Resources/Localization/Journeys.xcstrings` | EN/VI wording per section 0 |
| `CarodoTests/JourneyStopsTests.swift`, `JourneyBreakTests.swift` (new), `DriveDataReplayTests.swift` (reads `.carodo`) | Tests |
| `docs/specs/journey-detail.md` | Route timeline section: stops, the three evidence levels, breaks |
| `docs/architecture.md` | Algorithm table: "Stops on the way" gains the evidence join; Between-Journey |

**Unchanged:** schema, sync, `RouteRecorder`, `StopDetector`, `JourneyMerge`, `WaitJoin`, Replay,
Narrator, Trim (still reads `stopIntervals`), MapKit/WeatherKit.

## 9. Acceptance criteria

1. Every stop ≥ 60 s on the Route timeline has a time and a duration; the figures match `StopSummary`,
   Trim and the stop bands (one segmentation).
2. No line names an activity the person has not logged.
3. A stop at a Saved Place shows the place's name; a fill-up logged within a stop's interval shows
   "Fill-up logged" on that stop, never listed a second time.
4. An uncertain duration (lost GPS) carries `≈`.
5. Two trips meeting section 5 show "N min break" on both detail pages, with the Merge action (the
   existing sheet). Otherwise nothing shows.
6. The 312 km trip: 8 stops, 89 min, each readable.
7. `task lint`, `task warnings`, `task test` pass; screenshots as in section 7. No change to schema,
   sync, recording, Replay, Narrator.

## 10. For the owner to approve

1. **Which lines appear on the Route timeline:** every stop ≥ 1 min (a city trip could have 8–10
   lines), or stops ≥ 5 min as their own lines and short stops grouped as "and 6 short stops · 9 min"?
   Proposal: **group** (keeps the editorial layout tight).
2. **Matching items to stops:** are ±5 min and 150 m reasonable?
3. **An area name for a stop that is not a Saved Place** ("Stopped 12 min · P. Tân Mỹ") needs a reverse
   geocode per stop (sends coordinates to Apple, extends the table in `docs/privacy.md`). Proposal:
   **not in V1**.
4. **Between-Journey, same vehicle:** require both to have a vehicle and the same one (proposal), or
   follow Merge (accept one side without a vehicle)?
5. **Continuity of position:** reuse Stop and wait's 150 m / 1,000 m (proposal), or loosen it for road
   trips (for example parking at another lot across a rest stop)?
6. **Where breaks show:** only on the two trips' detail pages (proposal), or in the Journeys list too
   (later)?
7. **Replay:** keep its own compression logic (V1), or plan for Replay to read `stopIntervals` in a later
   version so there are no longer two definitions?
8. **The replay tool reading `.carodo`:** agree to add it (dev only, figures only)?

## 11. Decisions made (owner, 2026-11-09)

### 11.1 Three evidence levels (section 0 unchanged)

Measured / Unconfirmed suggestion (only once POI Discovery exists) / Confirmed by the person. A logged
item is a **confirmed fact**; **attaching** it to a particular stop is Carodo's inference, made only when
the evidence is enough (11.3). Never a Coffee/Fuel/Charging/Rest Stop label.

### 11.2 Presentation on the Route timeline

- Its own line for a stop **≥ 5 min** (`StopBands.longS`), for a stop with an attached logged item, and
  for the wait between two joined parts. Each stop is exactly **one line**: an attached item sits in the
  stop's line, never repeated as a line of its own.
- Stops from 1 to under 5 min: grouped into one sentence "N short stops · X" **only when there are 2 or
  more**. The grouped sentence has no position and is not a stop.
- 5 min is only a **presentation** rule: `stopIntervals`, `StopBands`, Trim stay as they are.
- Wording: "Stopped 12 min", "At Home · 8 min", "Waited between two legs · 25 min", and "about" for an
  estimated duration. No accuracy, confidence or version shown. No empty placeholder.

### 11.3 Attaching logged items to stops (replaces the "Fill-up/expense" row of section 3)

Only items **already linked to the journey** count (`driveLogs.linked`, links the person made). For
each item:
1. The item's **time** must fall within the stop, widened by 60 s (the person types times rounded to
   the minute).
2. A fill-up with **station coordinates** (logged on the spot) must also be ≤ 150 m from the stop's
   position. When both are there, both must hold.
3. Time only (an expense, a fill-up without coordinates): attach when it is something that happens while
   standing still (a fill-up, an expense) **and there is exactly one candidate stop**.
4. Two candidates or more, or none: **no attachment**. The item still shows as today.
No new fill-up, expense or Saved Place is created.

### 11.4 No new network

No reverse geocoding, no MapKit Nearby, no new request. Only offline data and what Journey Detail has
already loaded.

### 11.5 Between-Journey

- `JourneyMerge.refusal == nil` (called, not copied), both are the driver, **the same known vehicle**
  (no suggestion when one side has no vehicle), a break ≤ 2 h. Manual Merge keeps its 6 h.
- Continuity of position: **150 m when the person started the later trip, 1,000 m when Auto Mode
  started it**. Exactly Stop and wait's meaning, sharing one function with Stop and wait (extracted from
  `WaitJoin.verdict`, not copied). Not loosened for road trips.
- The start and end are fixes actually recorded: the display route's lead-in (before `startedAt`) is
  left out. A missing point means no suggestion.
- Shown only in Journey Detail. The only action opens the existing Merge sheet.

### 11.6 Technical debt: Replay Stop Alignment

Replay compresses stops by the recorder's "held" state (plus "silent stop" since `29f39f7`) and does not
read `stopIntervals`. Needs an audit: what is the same concern (a finished stop on the timeline) is
shared; what differs (the instant motion state during playback) stays apart. Not fixed in V2.3.2 (Replay
belongs to another session).

### 11.7 Developer replay reads `.carodo`

Dev only, read only, aggregate figures only, no coordinates. Baseline for the 312 km trip: 8 stops /
89 min. A result that differs from the baseline is explained, never fixed by tuning the algorithm to
the number.

## 12. Next phase: Journey Points (V2.3.3)

Built along the owner's final direction: [journey-points.md](journey-points.md).
