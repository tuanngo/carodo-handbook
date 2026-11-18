# Replay: the creep out of a stop, and GPS spikes (A + C)

Status: **Done 2026-11-18** (carodo-ios `8cb20b7`; the owner took the three recommendations). The owner watched it: the creeps natural; the 11:11 stop still jumped inside its compressed second (10–29 m a frame, by a frame-by-frame playback), fixed by a creep sharing up to 3/4 of the stop's second by its metres (5.1 m a frame at 15×, 8.5 m in the video), then accepted. Left open: TD-64, TD-65, KL-8.

## Outcome

In Replay and the Replay video, the wheel never jumps after a stop or on a single bad GPS fix: a car
that crept out of a stop is seen creeping, and a fix that went out and came back is not drawn. The
summary (distance, moving time, top speed) and the detail page's stops do not change.

## What was found (real drives, `drive-data/`, read-only)

The 11:09 drive on 2026-11-18 (`5EF778C7`, 3.1 km, stop-and-go) through today's `RouteRecorder` and
`ReplayTimeline` (a temporary opt-in probe, deleted): six steps of 20 m or more in one story second.

| Offset | Step | Cause |
|---|---|---|
| 380 s | 80 m in 0.02 story s | the end of the journal stop 107 s + 273 s: the car crept 80 m in three creeps inside it, held at the stop anchor |
| 492 s | 48 m | a hold released after a creep |
| 683 s | 104 m | a hold released at `stopRadiusM` (100 m): ~25 s of creeping at a Doppler speed under the trusted 2 m/s |
| 686–687 s | 29 m back, 46 m on | GPS: one fix at 43 m accuracy, out and back |
| 761 s | 30 m out, 15 m back | GPS: one fix at 22 m accuracy, 3 s after leaving a stop |

The long drives (07:08 `4FA149EA`, 16:20 `6CD04920`) show no hop at a stop's end: the car stood
still and left above 2 m/s, so the hold released within metres. Their remaining steps (21–39 m) are
GPS spikes on the move.

Across the 38 pulled drives, a position-derived speed of 60–160 km/h while the Doppler speed said
10–28 km/h occurs on 23 drives, on 12 of them within the first two minutes (the receiver warming
up). The
Doppler speed itself spiked once only (29 km/h among 5 km/h). Fixes without a speed are 5 % of
the first minute against 0.4 % after it.

## What the code does today

- `Core/Recording/RouteRecorder.swift`: a stop is confirmed after 10 s at ≤ 1 m/s; from then every
  route point sits at the stop anchor (`metrics.route` takes `held?.latitude`), until a trusted
  2 m/s or 100 m from the anchor (`StopRule`). The jump filter (`isConsistentStep`) allows
  `reference × dt × 1.5 + ½ × 5 × dt² + max(accuracy)`; the reference includes the last step's
  position-derived speed, so a spike widens the allowance for the fix after it, and the accuracy
  term lets a fix move as far as its own error. `currentSpeedMps` falls back to the step's
  position-derived speed when a fix has none.
- `Core/Recording/TripReplay.swift`: `Step.point` is the held route point; `Step.stored.sample` the raw fix.
- `Core/Replay/ReplayTimeline.swift` `make(samples:gaps:roads:…)`: one keyframe per step at
  `step.point`, `speedMps` 0 while held; the journal's stops (`JourneyAnalysis.stopIntervals` on the
  recorder's route) compressed in `finish`.
- `Core/Replay/ReplayRoute.swift`: the drawn line is the keyframes, simplified per run.
- The video uses the same timeline (`roads: .recorded`, `forVideo`), so both fixes reach it.
- `docs/specs/replay.md` (The timeline): "Gaps: no invented movement"; "Stops are the journal's";
  `docs/architecture.md` (Algorithms): the `ReplayTimeline` row's "Never" includes "a stop rule of
  Replay's own".

## Proposal

### A. The creep out of a held stop is shown (`ReplayTimeline.make`)

While the recorder holds a stop, Replay places the wheel by a **display anchor** of its own, from
the raw fixes (`step.stored.sample`). It holds while the raw fix stays within `creepRadiusM`
(proposed `max(10 m, 1.5 × accuracy)`). Once a fix leaves that radius, the wheel follows the raw
fixes until they are still again (a step under 1 m), and that fix becomes the display anchor.

- Movement is recorded movement, never invented (the spec's rule holds): the creep's fixes are real.
- **Distance:** the recorder adds a held stop's metres at its release (`away`). The keyframes of a
  creep carry that amount spread by path length, ending exactly at the recorder's figure at the
  release (as `appendRoad` spreads a healed road). The arrival still equals the journey's distance.
  This needs the release's figure, so the held run is buffered and written at the release: one
  pass, O(n).
- **Stops unchanged:** the spans are still the journal's (`stopIntervals` on the recorder's route).
  A creep inside a journal stop plays inside its compressed second, so 80 m glides there instead of
  teleporting. A creep under a minute plays at the rate.
- Parked drift: the radius is above the drift seen at 8 m accuracy (≤ 2 m a fix); a fix over 50 m
  accuracy never reaches the timeline (the recorder rejects it).

### C. Out-and-back GPS spikes are left out of what Replay draws (`TrackSpikes`, new, pure)

`Core/Domain/Journey/TrackSpikes.swift`: which fixes of a track are spikes, knowing the fixes after
them (offline, the whole track). From each kept fix `a`, up to `maxRun` (3) fixes ahead, find the
first fix `c` the car could have reached from `a`:
`d(a, c) ≤ v × Δt × 1.5 + slackM` (5 m; built without the `½ a Δt²` first proposed: over a four-second look-ahead it reached a fix 50 m off, and a `c` that skips a run must also reach the fix after it), where `v` is the highest Doppler speed among
`a…c` (a speed present, trusted or not). The fixes between `a` and `c` that it could not have
reached are spikes. With no such `c` within `maxRun`, nothing is dropped: the position really moved
(a tunnel, a restart), as the recorder's `maxConsecutiveJumps`.

- Unlike the recorder's filter, the bound has no accuracy term and no position-derived reference,
  the two openings the 686 s and 761 s fixes went through. A fast U-turn passes (its step is within
  its Doppler speed); the 686/687 and 761 s fixes do not.
- Never a stop's first or last fix, never across a segment break or a gap; a track with no speeds
  drops nothing.
- Replay: a spike's keyframe is left out. The next keyframe keeps the recorder's distance, so the
  figure runs on and the arrival is unchanged; the line and the camera never see the spike.
- C runs on the raw fixes before A, so A follows clean fixes.

### Reuse later (not in this plan)

`TrackSpikes` answers one question: is this fix an excursion its neighbours and its Doppler speed
contradict? The next readers, each its own decision:

1. **The start of a drive.** The 60–160 km/h position spikes in the first minutes are exactly what
   it finds. Where a person sees 80–90 km/h while the car does 20, the likely path is
   `RouteRecorder.currentSpeedMps` falling back to a position-derived speed for a fix without a
   Doppler speed (12 × more frequent in the first minute); the stored top speed is Doppler-only and
   already unaffected (35–50 km/h on those drives). Live, the test needs the fix after (1 s late):
   the recorder could show nothing rather than a position speed, and count distance one fix behind.
2. **A Doppler speed spike** (none in today's data beyond 29 km/h): the same out-and-back test on
   speed, `|Δv| > 5 m/s² × Δt` there and back, in the same type.
3. **The recorder's filter** (direction B): taking out the accuracy term or the position reference
   changes distance, so it bumps `RouteRecorder.rulesVersion` and is compared on drives first.

## Scope and files

| File | Change |
|---|---|
| `Carodo/Core/Domain/Journey/TrackSpikes.swift` | new: the detector and its `Configuration` |
| `Carodo/Core/Replay/ReplayTimeline.swift` | `make(samples:…)`: spikes left out, the display anchor and the creep's distance |
| `CarodoTests/Core/Domain/Journey/TrackSpikesTests.swift` | new |
| `CarodoTests/Core/Replay/ReplayTimelineTests.swift` | creep and spike cases |
| `CarodoTests/DriveData/ReplayStopAlignmentReplayTests.swift` | add: no step ≥ 20 m within one story second unless across a jump, on the pulled drives |
| `docs/specs/replay.md` | The timeline: the creep and the spikes |
| `docs/architecture.md` | Algorithms: a `TrackSpikes` row; the `ReplayTimeline` row's display anchor |

Not touched: `RouteRecorder`, `TripReplay`, `JourneyAnalysis`, the schema, the summary, the
detail page and the live map.

## Tests

- `TrackSpikes`: one fix out and back (dropped); two and three in a row (dropped); four (kept, it
  moved); a U-turn at 10 m/s (kept); a fast straight road at 30 m/s (kept); no speeds (nothing
  dropped); across a segment break (kept); a stop's boundary fix (kept).
- `ReplayTimeline`: a held stop with a 60 m creep then a release: no keyframe step over the creep's
  own steps; distance at the release and at arrival equal the recorder's; the stop span's start, end
  and label unchanged. Parked drift of 3 m around the anchor: the wheel still. A spike: its
  keyframe gone, arrival distance unchanged.
- Real drives: the alignment test still passes (same stops); the new hop check passes on all 38
  drives; the 11:09 drive's six hops are gone.

## Acceptance

- On the 11:09 drive, no keyframe step ≥ 20 m in under 2 story seconds; same on every pulled drive
  outside a jump or a gap.
- Distance at arrival, the stops (count, start, end, label) and the video's length unchanged on
  every pulled drive.
- `task lint`, `task warnings`, `task test` pass; `ReplayTimeline.make` stays O(n).

## Decisions for the owner

1. **Speed shown while creeping.** The creep's Doppler is ~1 m/s, under the trusted bar, so it
   would read "—". Recommended: the creep's own distance over its time (a fact from the fixes),
   only on its keyframes.
2. **The live map and the detail page** still draw the straight line from the anchor to the
   release (they read the recorder's route). Recommended: leave them for direction B.
3. **`creepRadiusM`** `max(10 m, 1.5 × accuracy)`: a hypothesis, to compare on the pulled drives
   before code is final.

## Assumed, not checked

- That the 660–685 s positions are right and the Doppler speed lagged (the course stayed frozen at
  97° while the positions went west). If the positions were wrong instead, A shows a creep that did
  not happen; C does not catch it (it is smooth, not out and back).
- The 80–90 km/h at the start was seen on the live screen; which screen is not confirmed.
