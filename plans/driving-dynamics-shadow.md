# V2.3.1 — Driving Dynamics Shadow Mode: implementation plan

Status: **built**, carodo-ios `7ffb515` (the analysis) and `539ca4d` (the log line after a save). Planned
2026-11-08; what is still open is PV-3 in `technical-debt.md`.
Foundation: V2.3.0 (`fda2612`: `JourneyAnalysis.stopIntervals`, `TrackQuality`, `Percentiles`, the
"Derived insights and enrichment" rules in `docs/architecture.md`). The owner's decisions: section G of
`journey-v2.3-enrichment-audit.md`.

## 0. Scope

**In:** one pure analysis, run **once after a trip is saved**, that measures acceleration and
deceleration along the direction of travel from the GPS Doppler speed and writes **one line** to the
tracking log (Developer mode). The `task replay` tool computes the same analysis on databases pulled
from the iPhone, to study the distributions.

**Out:** UI, a safety score, any conclusion about driving behaviour, cornering, Core Motion, storing
results in the database, schema, sync, changes to `RouteRecorder`/recording/distance, Between-Journey
Smart Stops.

## 1. Algorithm and how GPS uncertainty is handled

### 1.1 Input

The accepted fixes of **the trip just saved** (`StoredTrip.samples`, the raw track), not the replayed
route: the route holds speed at 0 while the car stands at a stop, which distorts the derivative.
Dynamics reads the raw data and **does not filter positions again** (no logic shared with
`RouteRecorder`, whose filter has already decided which fixes are kept).

### 1.2 Speed slope per window: weighted linear regression

The audit showed that the speed difference between two consecutive fixes (1 s) is noise: 18 false
"hard brakes", none lasting more than one step. Instead, for each fix `i` take a **centred window,
W = 3 s wide** (a hypothesis, tunable) and estimate the slope `a` of `v(t)` by **weighted least
squares** with `wₖ = 1/σₖ²`, where `σₖ = speedAccuracy` of the fix:

- `a = Σw(t−t̄)(v−v̄) / Σw(t−t̄)²`, error `σₐ = √(1 / Σw(t−t̄)²)`.
- Equivalent to a first-order Savitzky–Golay derivative (the algorithm `docs/architecture.md` already
  lists as "Reference"), with an accuracy weight added: a fix with poor speed pulls the result less.
- Computed with **two pointers and running sums** (Σw, Σwt, Σwv, Σwt², Σwtv): O(n) for the whole trip,
  no intermediate array.

**An honest caveat:** Apple does not define Core Location's `speedAccuracy` as 1σ, and errors of
consecutive fixes are correlated (the internal Kalman filter). So `σₐ` is a **relative index** for
ranking and filtering, not a true statistical confidence interval. The real-world test (section 7.3)
will calibrate it.

### 1.3 A window is valid only when

- every fix in the window has the same `segment` (it never crosses a pause or the boundary of a joined
  part);
- every interval between two fixes is ≤ `TrackQuality.Configuration.regularIntervalS` (1.5 s):
  **reuse** V2.3.0's definition of a regular cadence, no second threshold. A GPS gap means no window;
- at least 3 fixes, all with speed ≥ 0 and a known speed accuracy;
- the speed accuracy of each fix is ≤ `maxSpeedAccuracyMps` (hypothesis 2.5 m/s, about the p75 of the
  audit data);
- the highest speed in the window is ≥ `minimumSpeedMps` (hypothesis 3 m/s ≈ 11 km/h): drops the noise
  while standing still, but keeps the braking phase down to a full stop (the start of the window is
  still moving).

### 1.4 Events (cars only, research thresholds)

A **Schmitt trigger** on the slopes of consecutive valid windows:

| | Enter | Leave | Minimum duration | Merge |
|---|---|---|---|---|
| Deceleration | `a ≤ −2.94 m/s²` (−0.30 g) | `a > −1.47` (half) | ≥ 2 consecutive window centres (~1 s) | two events less than 2 s apart are one |
| Acceleration | `a ≥ +2.75 m/s²` (+0.28 g) | `a < +1.37` | as above | as above |

An event ends as soon as it meets an invalid window (a GPS gap, a new segment): **an event never
bridges lost GPS**.

Two levels, both for the log only:
- **candidate**: the point estimate crosses the threshold;
- **confident**: the bound nearest the threshold still crosses it, `a + k·σₐ ≤ −2.94` (braking) or
  `a − k·σₐ ≥ +2.75` (acceleration), with `k = 1` as a hypothesis.

With the audit data (3 s, largest deceleration 2.29 m/s²), **0 candidates** are expected on ordinary
trips. That is the expected result, not a bug.

## 2. Cars and motorbikes

| | Car (`car`) | Motorbike (`motorbike`) | Bicycle, no vehicle assigned |
|---|---|---|---|
| Distribution analysis | Yes | Yes | No (log `skipped`) |
| Event thresholds | −0.30 g / +0.28 g, **research thresholds** | **None** (`nil`): distribution only | — |
| Window, window filter | Defaults of 1.3 | Same values at first, its own configuration to tune later | — |

- The vehicle class comes from `Vehicle.vehicleClass` of the trip's vehicle (already there). No vehicle
  assigned means no guess: skip.
- It measures GPS speed, not the phone's sensors, so a phone in a pocket or mounted on a motorbike makes
  no difference.
- The per-class configuration is a `Configuration` value with `byClass`, in `TrackingRules` (the one
  place for tunable thresholds), not a separate protocol or class.

## 3. Quality gating and confidence

Three separate layers:

1. **The journey qualifies** (a yes/no gate, not a score): the trip is sure (`!isPending`),
   `rider == .driver`, the vehicle class is `car` or `motorbike`. This is exactly the "sure + driven"
   condition `JourneyMerge` uses; if it is already a readable function, reuse it; if it lives inside
   `JourneyMerge.refusal`, extract a predicate on `Journey` that both read (no copy).
2. **Confidence of the measurement** (journey): from the trip's `TrackQuality`. Dynamics' own gate
   (hypotheses):
   - `regularIntervalShare ≥ 0.9`;
   - `trustedMovingSpeedShare ≥ 0.7`;
   - `speedAccuracy.p50 ≤ 2.0 m/s`.

   Failing it logs `skipped reason=quality(cadence|trusted|speedAcc)`. On the 18 audit trips, about 4
   would be dropped for `trusted < 0.7`. Plus a `measure conf=0.00…1.00` score computed with the existing
   **`DriveConfidence.ramp/score`** (no new formula).
3. **Confidence of each event**: `DriveConfidence.score` over its features: the margin past the
   threshold divided by `σₐ`, the number of consecutive windows, the fix coverage in the window, the mean
   speed accuracy. Logged as `conf=` like every other engine decision.

No score describes the driver; the log speaks only about the measurement.

## 4. Collecting distributions without storing more data

- **Nothing new is stored in the database.** Each trip writes **one tracking-log line**. The log is
  already capped (`GRDBTrackingLog` deletes old lines) and carries no coordinates and no event times
  (P5, P9):
  ```
  dynamics v1 class=car windows=1180 measure conf=0.82 brake p50=0.2 p99=1.2 max=2.3 accel p99=1.3 max=2.7 candidates=0/0 confident=0/0
  dynamics v1 skipped reason=passenger|pending|bicycle|noVehicle|quality(trusted)
  ```
- Percentiles use V2.3.0's `Percentiles` (nearest rank); no second helper.
- The full distribution (a histogram in 0.25 m/s² bins, grouped by vehicle class) is **built only in
  `task replay`**, recomputed from the raw tracks already there. It is stored nowhere, only printed while
  the tool runs.
- Every result can be recomputed from the raw track. Changing the algorithm means running `task replay`
  again, never a migration.

## 5. Running in shadow without touching recording or UI

- **When:** in `writer.onSettled` (`CarodoApp.swift`), right after `logMotion(forTrip:)`. That is where
  the after-save log lines already sit (`motion`, `ride`), after the trip is written and its transaction
  closed. It never touches `LocationSource → RouteRecorder → TripWriter`.
- **How:** `DependencyContainer.logDrivingDynamics(forTrip:)` reads the trip (`storedTrip`), the journey
  (rider, pending, vehicle) and the vehicle (class), then calls the pure analysis `@concurrent` (off the
  main actor) and writes the log. It has `guard !isErasingLocalData` and counts `activeDataWork` like
  `logMotion`. A failed read writes nothing (never "0 events" in place of "unknown").
- **A trip still pending when saved** (Auto Mode, not confirmed yet): log `skipped reason=pending`. The
  minimal option: **no** hook on a later confirmation; `task replay` computes these trips with their
  final state when the database is pulled. Logging at confirmation too would need a second hook: I
  propose leaving it for later.
- **No UI**, no screen changes. The Developer view only adds a group showing the `dynamics` configuration
  beside `StopDetector` (read from `TrackingRules`), like the existing groups.

## 6. Versioning, performance, battery

- `DrivingDynamics.version = 1`, printed in every log line. The version goes up whenever any rule changes
  (window, gate, threshold). The version history is a table in `docs/tracking.md`. Nothing is stored, so
  old trips never need recomputing on the device.
- **Performance:** O(n), two pointers; an hour of driving ≈ 3,600 fixes, computed in a few milliseconds,
  off the main actor, once per trip. The largest cost is one read and decompression of the track (about
  25 KB for an hour of driving).
- **Battery:** no new sensor, no network, nothing added while recording. The impact is not measurable
  next to recording.

## 7. Testing and validation

### 7.1 Unit tests on synthetic data (`DrivingDynamicsTests`)

Deterministic synthetic data, noise from a pseudo-random generator with a fixed seed in the test. No
real tracks.

- Steady 15 m/s plus ±σ noise: 0 candidates; slope p50 ≈ 0.
- A braking ramp of −3.5 m/s² for 3 s: 1 braking event of the right duration; at −2.5 m/s²: 0 (both
  sides of the enter threshold).
- Hysteresis: oscillating around the threshold gives 1 event; two ramps 1.5 s apart merge into one,
  3 s apart are two.
- A one-fix spike (as in the audit): 0 events.
- A GPS gap or a segment boundary in the middle of a ramp: no window across it, no event bridging it.
- A fix with no speed, or a speed accuracy above the threshold: the window is dropped.
- Weighting: an off-speed fix with poor accuracy pulls the slope less than one with good accuracy.
- Motorbike: a strong ramp still gives 0 events (no threshold) but appears in the distribution.
- Bicycle, passenger, pending, no vehicle: `skipped` with the right reason.
- Quality gate: both sides of 0.9 / 0.7 / 2.0.
- Simulated Core Location lag (a ramp through an exponential filter): measure how much the peak is
  flattened, recorded in the test as a **known property**, not a threshold.
- `DriveConfidenceTests`: the two new confidence functions, both sides of each step.
- Tracking log: the `dynamics` line has no coordinates and no event times.
- O(n): 100,000 fixes run under a generous time limit (guards against an accidental O(n²)).

### 7.2 Regression on real data (`task replay`)

- Added columns: vehicle class, qualifies or the skip reason, window count, braking and acceleration
  p99/max, candidate/confident. A histogram grouped by vehicle class is printed after the table.
- Expected on the pulled trips: 0 candidates for cars, distributions close to the audit. Every candidate
  that appears is looked at with a trip report (no coordinates).

### 7.3 A controlled real-world test (after the code is done)

- **Only in a closed area, with permission, with no other vehicles; never on a public road.** An
  experienced driver, low speeds.
- **Reference:** an OBD-II reader logging vehicle speed at ≥ 5 Hz, or a 10 Hz GNSS. Time aligned with a
  shared mark (start the Carodo trip and mark the reference app at the same moment).
- **Car:** from 40 km/h, 5 times at each level: light braking (~0.15 g), medium (~0.3 g), hard
  (~0.5 g); acceleration likewise, within the car's limits.
- **Motorbike:** light and medium braking only, with protective gear.
- **Measure:** Carodo's peak slope against the reference peak (flattening factor, lag); recall and
  precision of candidate/confident per level; whether `k` and `σₐ` can be calibrated.
- Results are recorded in this plan. Only then are official thresholds or any display discussed.

### 7.4 Shadow on ordinary trips

2–4 weeks of daily driving on 3 iPhones, cars and motorbikes; `task pull-db` then `task replay`. Use the
per-class distributions to propose motorbike thresholds.

**V2.3.1 counts as done when:** code and tests pass (`task lint`, `task warnings`, `task test`), the
replay runs, the docs are updated. The log line on a real iPhone after a trip is a **device check still
required**. V2.3.1 has no precision criterion: that is a condition for a later decision to display.

## 8. Files changed

| File | Change | Reason |
|---|---|---|
| `Carodo/Core/Domain/DrivingDynamics.swift` (new) | Pure analysis: windows, weighted slope, distribution, events, skip reasons, `version` | One responsibility, deterministic, testable |
| `Carodo/Core/Tracking/TrackingRules.swift` | Add the `dynamics` configuration (per vehicle class) | Tunable thresholds in one place |
| `Carodo/Core/Tracking/DriveConfidence.swift` | Two functions: measurement confidence, event confidence | Reuses `ramp/score`, no new formula |
| `Carodo/Core/Domain/Journey.swift` (maybe) and `Carodo/Core/Domain/JourneyMerge.swift` | Extract the "sure + driven" predicate if it sits inside `JourneyMerge` | No copy of Merge's rule |
| `Carodo/Core/Diagnostics/TrackingLog.swift` | Kind `.dynamics` and the function building its line | A log without coordinates |
| `Carodo/App/DependencyContainer.swift` | `logDrivingDynamics(forTrip:)` | Next to `logMotion`/`logRide` |
| `Carodo/App/CarodoApp.swift` | One call in `onSettled` after `logMotion` | Runs once after the save |
| `Carodo/Features/Developer/Views/DeveloperView.swift` | A group showing the `dynamics` configuration | See the thresholds in use |
| `CarodoTests/DrivingDynamicsTests.swift` (new), `DriveConfidenceTests`, `DiagnosticsLogTests`, `TrackingRulesTests` | Tests of 7.1 | |
| `CarodoTests/DriveDataReplayTests.swift` | Dynamics columns and the per-class histogram | Research tool, 7.2 |
| `docs/tracking.md` | A "Driving dynamics (shadow)" section: thresholds, gates, version | Thresholds are hypotheses, with a table like the other sections |
| `docs/architecture.md` | Move the "Harsh braking…" row from Reference to the built table (shadow, weighted regression); cornering stays in Reference, noted as blocked with GPS | One algorithm per problem |
| `docs/operations/device-testing.md` | The controlled test procedure (7.3) | Another session has uncommitted changes there: stage only this work's hunks |

**Unchanged:** schema, sync, `RouteRecorder`, `StopDetector`, `TripReplay`, `RideProfile`, the user's
UI, permissions, dependencies.

## 9. Duplication: reused or deliberately kept apart

- **Reused:** `TrackQuality` (the quality gate and the definition of a regular cadence); `Percentiles`;
  `DriveConfidence.ramp/score`; `LocationSample.trustedSpeed` (where needed); Merge's "sure + driven"
  condition; `Vehicle.vehicleClass`; the `storedTrip` read.
- **Deliberately kept apart:** `RideProfile.accelRms` (the RMS of 1 s speed differences, used to
  **guess the vehicle class** in the `ride` log). It answers a different question and is being logged;
  changing it would change figures in use. The docs note that the two numbers cannot be compared
  directly. `SlowMoving` (a 30 s moving average to find traffic jams) is a different problem too.
- **Risk of the algorithms drifting:** if Replay or Journey Detail later wants to show "hard braking",
  it must read `DrivingDynamics`' result, never compute it again.

## 10. Risks

- `speedAccuracy` is not 1σ and errors are correlated → `σₐ` is only a relative index, to be calibrated
  in 7.3.
- Core Location's filter may flatten braking peaks → GPS alone may never be enough to see hard braking.
  Shadow Mode answers this with no risk to the user.
- `rider = driver` is a default, not a confirmation → some unmarked passenger trips will get in.
  Acceptable while it only logs.
- A trip pending when saved has no log line on the device (only in the replay).

## 11. For the owner to confirm at approval

1. Accept the minimal option for pending trips (replay only), with no hook at confirmation yet?
2. 3 s is the main window; `task replay` also compares 2 s and 5 s to choose. Agreed?
