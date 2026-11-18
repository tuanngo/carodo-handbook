# GPS plausibility: live speed, jumps and speed spikes without a fixed speed cap (TD-65 + no cap)

Status: **Built** (approved 2026-11-18; carodo-ios `cbd7ff2`, committed at the owner's word before
the device drive, 2026-11-19). The owner took the three recommendations. Device drive pending.

## Result (2026-11-18)

- Slack chosen: `maxAccuracySlackM` 15 m, `jumpSpeedFactor` 1.5 kept, `maxAccelerationMps2` 5 kept.
  Compared on the 35 journeys against `main` (a worktree at `0179c7f`, the same probe): factor 1.2
  or 1.0 rejected real steps of an imported drive and cut one journey by 3.2 %; an uncapped slack
  let the 43 m-accuracy spike through.
- Built beyond the plan: an untrusted Doppler speed still **bounds** a step (speed + 2 × its
  accuracy), so a fix waits only with no Doppler speed at all; with the speed known at both ends
  of a step the gain is a dt² / 4, not ½ a dt² (a 6 s multipath step at a 2026-11-16 start gained
  90 m and +177 m on its drive otherwise).
- Distance: 853.14 → 853.07 km over 35 journeys (−0.01 %). Changed over 0.25 %: two journeys,
  each the named spikes (−40 m: a fix 20 m in 0.37 s; −30 m: the 686/687 s and 761 s spikes of
  `replay-creep-and-gps-spikes.md`). Moving time 16.799 → 16.800 h. Top speed unchanged on every
  journey (the one Doppler spike, 27 km/h, was under its drive's top).
- `ingest` cost (Debug, iPhone 17 Pro Max simulator, 67,307 fixes, two runs each): 1.64 / 1.65 µs
  a fix before, 1.62 / 1.53 µs after.
- Checks: `task lint`, `task warnings` (none), `task test` (2,586, 24 skipped, 0 failures), the
  opt-in drive-data replays pass.
- Device check still required: a drive start (when the speed appears after "–"), a pause and a
  background flush mid-start, and if possible a fast motorway.

## Plan as approved

## Outcome

A fix is judged by what the drive itself says (the receiver's Doppler speed, how fast a car can
change speed, the fixes around it), never by a fixed top speed. A car at 280 km/h on an Autobahn
records its whole distance; a car at 150 km/h on a Vietnamese expressway is never shown 200 km/h
from a bad fix; the live panel never shows 80–90 km/h while the car does 20. The same spike
detector serves the recorder (live), Replay and Driving dynamics.

## What the code does today (files read)

- `Carodo/Core/Recording/RouteRecorder.swift` `ingest`: rejects a fix whose step from the last
  accepted fix is faster than `maxPlausibleSpeedMps` = `LocationSample.implausibleSpeedMps` = **70 m/s
  (252 km/h)**, or longer than `isConsistentStep` allows: `reference × dt × 1.5 + ½ × 5 × dt² +
  max(accuracy of both)`, the reference the fastest of the two fixes' trusted Doppler speeds **and the
  last accepted step's position-derived speed** (`lastStepSpeedMps`). With no speed known the step is
  bounded by the 70 m/s cap only. Three rejections in a row break the segment (`maxConsecutiveJumps`).
- Same file, `currentSpeedMps` (the live panel): the fix's Doppler speed, or **the step's
  position-derived speed when the fix has none** (TD-65).
- Same file, top speed: every trusted Doppler speed (`LocationSample.trustedSpeed`, over 2 × its
  `speedAccuracy`, or any speed when the accuracy is unknown), **with no bound and no spike check**.
- Only accepted fixes are stored (`trip_points`, then `trip_tracks`); a rejected fix and its Doppler
  speed are gone.
- `Carodo/Core/Domain/Journey/TrackSpikes.swift`: offline, position spikes only (a fix the Doppler
  speed says the car could not reach, with a landing within 3 fixes); used by Replay only.
- `Carodo/Core/Domain/Journey/DrivingDynamics.swift`: offline, shadow only (logged, never stored or
  shown); weighted least-squares slope of Doppler speed over 3 s windows; car events at −0.30 g /
  +0.28 g (≈ 2.9 / 2.7 m/s²), at least 2 windows. No spike step before it.
- `LocationSample.implausibleSpeedMps` also bounds `PassportExploration` (and the Footprint's gap
  breaks, `docs/tracking.md` "Implausible speed"); `TripContinuation.maxSpeedMps` 41.7 m/s
  (150 km/h) bounds how far a car went during a relaunch gap.

## What the data says (`drive-data/`, 2026-11-18, temporary probe, deleted)

35 journeys, 67,307 fixes: 29 recorded by Carodo, 6 imported from Carstack (no `speedAccuracy` at
all: 34k fixes trust any speed). Stored fixes are the ones the recorder accepted then, so what it
rejected is not in the data.

| Question | Finding |
|---|---|
| Fastest Doppler speed | 113.5 km/h: nothing near the 252 km/h cap, so no real drive shows the Autobahn failure; it comes from the code |
| Real change of Doppler speed, 1 s apart | p50 0.13, p99 1.5, p99.9 **2.7**, max 7.5 m/s² |
| Above 6 m/s² | 4 steps: one Doppler **out-and-back** (3 → 27 → 0 km/h, +6.7 then −7.5 m/s², `speedAccuracy` 2.3–3.9 so trusted), one 1 → 24 km/h that stayed (Doppler settling or a hard start), one on an import, one the way back of the spike |
| Doppler out-and-back over 4 m/s² both ways | **1** in 67k fixes |
| Fixes without a Doppler speed | minute 0: 5.5 %, 1: 2.3 %, 2: 1.2 %, 3: 1.9 %, 4: 0 %, after: 0.3 %. Runs of 1–46 fixes; **6 of 29 drives** waited 2–56 s for their first Doppler speed |
| Position step beyond the Doppler distance (`step − v_max × dt`) | p99 2.8 m, p99.9 16.6 m, p99.99 36.7 m, max 139 m (dt 4 s at 23 km/h, first minute) |
| Steps a bound of `v × dt × k + ½ × 12 × dt² + slack` would reject (single-step estimate, not a replay) | slack 10 m: 43–53 (5–7 in the first 2 min); slack 15 m: 23–26; slack 20 m: 11 |
| Position speed > 2 × the nearby Doppler + 20 km/h | 115 steps, 29 of them in the first 2 minutes (e.g. 161 km/h at a Doppler of 24–28) |

What follows from it:

1. A **one-sided** acceleration bound (a physical `a_max` of 10–12 m/s²) does not catch the Doppler
   spike seen (6.7 m/s²). The signature of a spike is **out and back**: a change over a threshold one
   way, then the other way at the next fix. A car cannot reverse 4+ m/s² of acceleration inside a
   second; real driving stayed under 2.7 m/s² 99.9 % of the time.
2. Positions are where the jumps are, at the start above all. Doppler speed is the evidence.
3. The single-step numbers say what to compare, not what to ship: a rejected fix changes the next
   step, so the real distance change is measured by replaying the drives through the recorder.

## Proposal

### 1. Live speed is the receiver's own (TD-65)

`currentSpeedMps` = the fix's Doppler speed (0 while held at a stop); with none, **nil** (the panel
shows "—", as it does before the first fix). Never a speed from two positions. No delay, no change to
distance, `rulesVersion` unchanged by this part alone.

### 2. No fixed speed cap in the recorder: each step bounded by its own evidence

`isConsistentStep` becomes, with `v` the fastest **trusted Doppler speed** of the two fixes (never a
position-derived speed):

```
allowed = v × dt × jumpSpeedFactor + ½ × maxAccelerationMps2 × dt² + slack
```

- `lastStepSpeedMps` leaves the reference (one bad step no longer widens the next).
- `slack`: the accuracy term is bounded. Candidates compared on the drives:
  `max(accuracy)` (today), `min(max(accuracy), 15 m)`, a fixed 10 m / 15 m.
- `maxAccelerationMps2` stays a **physical** constant (5 today; 10–12 is a sports car); compared
  at 5 and 10.
- `maxPlausibleSpeedMps` (70 m/s) leaves the recorder. A step with evidence is bounded by it; a car
  at 280 km/h has a Doppler of 78 m/s and passes.

**A step with no evidence** (no trusted Doppler on either fix: the start, after a tunnel) is no longer
let through by the cap alone. It **waits for the next fix** (one fix late, about 1 s): the fixes are
consistent with each other when their position speeds change by no more than `maxAccelerationMps2`
(+ slack) between steps, the incremental form of `TrackSpikes`' landing test (`maxRun` 3). An
out-and-back fix is dropped; a consistent run is accepted; the first trusted Doppler speed settles it.
While a fix waits, the live speed is "—" (part 1) and its distance is added when it is accepted.

### 3. Doppler speed spikes (top speed, Driving dynamics)

`TrackSpikes` gains the speed test: a fix whose Doppler speed changes by more than
`speedSpikeMps2` (4 m/s², proposed: above every real value but the spike in the data's 99.9 %,
at 1.5 × the car event thresholds) one way and as much back at the next fix is a **speed spike**.
Its position may still be good: only its speed is ignored.

- **Top speed** counts a Doppler speed once the next fix shows it was not a spike (one fix late;
  the stored figure is unchanged when there is no spike).
- **Driving dynamics** leaves speed spikes out of its windows (they are unusable fixes there, as
  a poor `speedAccuracy` is).
- **Replay**: speed spikes are left out of the speed it shows, as position spikes are of its line.

### 4. One place for the physical bounds

`maxAccelerationMps2` and `speedSpikeMps2` live in one `Configuration` the recorder and
`TrackSpikes` share; a test holds that both stay above `DrivingDynamics`' car thresholds (a real
hard brake must never be taken for a spike).

### 5. The other users of the 70 m/s cap

| Reader | Today | Proposed |
|---|---|---|
| `PassportExploration` (simplified routes, no Doppler) | breaks a route faster than 70 m/s | keep a bound (no evidence on a simplified route), raised to **100 m/s (360 km/h)**: above any car on a road, below a teleport. Renamed so its role is data sanity, not driving |
| Footprint gap breaks | the same constant | the same 100 m/s |
| `TripContinuation.maxSpeedMps` 41.7 m/s over a gap of up to 10 min | 200 km/h on an Autobahn for 10 min = 33 km, over its 26 km | the higher of 41.7 m/s and the last trusted Doppler speed before the gap |

## Persistence and cost

- `RouteRecorder.ingest` stays O(1) a fix: at most 3 waiting fixes and two speed comparisons.
- `TripWriter` is unchanged: one transaction per 10 fixes or 15 s, off the main actor.
- A waiting fix is decided on **pause, finish and the background flush** before its batch is
  written, so no tail is lost by those; a kill by iOS loses at most the waiting fixes (≤ 3 s, less
  than the 10-fix batch it may already lose).
- Recovery replays the stored fixes through the same rules: the same decisions. The rules change
  distance, so `RouteRecorder.rulesVersion` 3 → 4 (`trip_enrichments` recompute as today).
- Measured: `ingest` time on the 35 journeys before and after (opt-in timing test), and
  `DrivingDynamics` usable windows (`windows=…/…`) before and after.

## Scope and files

| File | Change |
|---|---|
| `Carodo/Core/Recording/RouteRecorder.swift` | live speed Doppler only; the new step bound; waiting fixes; top speed one fix late; `rulesVersion` 4 |
| `Carodo/Core/Domain/Journey/TrackSpikes.swift` | the speed spike; an incremental form the recorder uses |
| `Carodo/Core/Domain/Journey/DrivingDynamics.swift` | speed spikes left out of windows; `version` 2 |
| `Carodo/Core/Tracking/LocationSample.swift` | the 70 m/s constant replaced by the sanity bound (100 m/s) for its two remaining readers |
| `Carodo/Core/Recording/TripContinuation.swift` | the gap's speed from the last Doppler speed |
| `Carodo/Core/Replay/ReplayTimeline.swift` | speed spikes out of the shown speed |
| `CarodoTests/…` (mirrors) | below |
| `docs/tracking.md` | the filter table (no cap, the step bound, waiting fixes, speed spikes, `rulesVersion` 4) |
| `docs/architecture.md` | Algorithms: `TrackSpikes` (both spikes, live and offline), `DrivingDynamics` row |
| `docs/specs/drive-recording.md` | live speed "—" without a Doppler speed |

Not touched: the schema, `TripWriter`, the API, what is shown on the detail page.

## Tests

- Recorder: 280 km/h straight synthetic drive (78 m/s Doppler, 1 Hz): every fix accepted, distance
  within 1 %; 150 km/h with one position fix 15 m out and back: dropped; one Doppler fix at 200 km/h
  among 150: top speed 150; a start with 10 fixes without Doppler, one 60 m out and back: dropped,
  live speed nil until the first Doppler speed; a consistent no-Doppler run: accepted; a tunnel
  (4+ jumps): new segment as today; waiting fixes decided on pause and finish.
- `TrackSpikes`: speed spike out and back (flagged), a hard brake at 4 m/s² that holds (kept), a
  start 0 → 5 m/s² that holds (kept).
- `DrivingDynamics`: a spike among steady speed makes no event and no window.
- Bounds: `speedSpikeMps2` and `maxAccelerationMps2` above the car thresholds.
- Real drives (opt-in, `task replay`): per journey, distance, moving time, top speed and rejections
  before vs after, for each slack candidate.

## Acceptance

- On every pulled journey, distance changes by under 1 % (or the difference is a named spike), top
  speed changes only where a speed spike is named, and the 3 → 27 → 0 km/h spike no longer sets
  anything.
- The 280 km/h synthetic drive keeps its full distance; today's recorder loses it (the test fails
  on `main` first).
- No live speed comes from positions.
- `ingest` within 10 % of today's time; `task lint`, `task warnings`, `task test` pass.
- Device check still required: a real drive start (the first minute's "—" and when the speed
  appears), and if possible a fast motorway drive.

## Non-goals

- Showing braking or acceleration events (a product decision, `driving-dynamics-shadow.md`).
- Storing rejected fixes (a schema change; the raw store keeps accepted fixes only).
- A per-vehicle top speed or any legal limit.

## Decisions for the owner

1. **Live speed "—" without a Doppler speed** (up to a minute at the start on 6 of 29 drives).
   Recommended: yes; a speed from positions is wrong as often as not there.
2. **One fix late for a fix with no evidence and for top speed** (about 1 s; ≤ 3 s lost on a kill).
   Recommended: yes.
3. **The sanity bound for routes without Doppler at 100 m/s (360 km/h).** Recommended: yes.
4. **The slack**: chosen from the replay's comparison and reported before it ships.
