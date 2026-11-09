# GPS engine: field test, open work, battery and performance

Status: engine built in code (2026-11-04); this plan is what to prove, tune and improve next.
The rules themselves live in `carodo-ios/docs/tracking.md` and the device procedure in
`carodo-ios/docs/operations/device-testing.md`; this file only lists what to do and in which order.

## Where it stands (2026-11-04)

- Recording: trusted speeds and the stop anchor (rules v3), departure and arrival (v4), the
  jump filter, gap healing, packed tracks, summary refresh, recovery.
- Auto Mode: standby (significant changes + 150 m parking geofence), a 120 s detection window,
  4 trusted fixes at 12 km/h, motion-based vehicle choice with "Bike rides too", auto-finish
  (5 min; 10 min on a bicycle; 90 s after car audio goes while stopped), Stop and wait.
- Per trip: `vehicle_source`, `car_audio`, motion seconds; vehicle class car / motorbike / bicycle.
- Tooling: `task pull-all`, `task replay` (every real drive against today's rules), `task events`,
  `task device-all` on three iPhones.

## 1. Field test (next 2–3 days, no engine code)

From 2026-11-07 every check names its moment (`carodo-ios/docs/operations/device-testing.md`,
"Checks by when they can be made"): **passenger** (read off the screen while recording; the driver
never touches the phone), **after parking**, or **logs** (`task pull-db`, `task events`). The lists
below predate this; most of their items are log checks.

Each day: `task pull-all`, `task replay`, `task events`, one line per finding in device-testing.md
Results. Before the first day: `task pull-all`, then `task device-all`, then re-add the vehicles
(the schema changed).

- [x] Auto Mode wakes from the parking geofence: `woke leftParking` → `driveStarted auto` in 3–4 s
      (2026-11-04, two iPhones). Missed metres at the start: to measure.
- [ ] A night indoors with Auto Mode on: no drive, battery flat.
- [x] Auto-finish after 5 min parked, end time at the stop (2026-11-04, both iPhones); bicycle still to do.
- [ ] Car audio lost while stopped: ends after 90 s (`autoFinished disconnected`).
- [ ] App killed mid-drive: next launch `launched recovered=1`, no sequence gap.
- [ ] Force-quit from the app switcher, then leave: does iOS still relaunch Carodo? (Traccar's
      SDK documents that a force-quit pauses tracking until the app is opened again.)
- [ ] CarPlay with one car in the garage: linked by itself, `car_audio = carplay`.
- [ ] Bicycle: the switch shows only with a bicycle; off → `detectionTimedOut cycling`; on → the
      bicycle; handlebar mount: does motion read cycling or unknown?
- [ ] Low Power Mode: wake and start latency.
- [ ] Battery per hour of recording (`battery` log lines; Developer → Battery), on battery and charging.

## 1a. Tomorrow's run for C: why the parking geofence wakes Carodo late (2026-11-05)

Before: `task pull-all`, then `task device-all` (the build with the geofence log and the lead-in;
the schema did not change). On every iPhone: Auto Mode on, location Always, Carodo **not**
force-quit from the app switcher, internet on (one iPhone may stay offline to compare).

1. Park, let the drive end by itself (or end it), and leave the phones still for 10 minutes or more.
2. Drive off without opening Carodo. Note the time you start moving and roughly where you are when
   the phone shows the location arrow.
3. Repeat once with a short stop (5–15 min, staying in the car) to check Stop and wait now joins.

After: `task pull-all`, `task events`, `task replay`. Read:

| Look at | Tells |
|---|---|
| `woke geofence left delayS=…` | delayS ≈ 0 with a `significantChange` in the same second: iOS noticed the exit late (a cell-based geofence); delayS large: iOS noticed early but woke Carodo late |
| `startGap=…m` (replay notes) | the metres missed before the first fix; then the lead-in that routed them |
| no `woke geofence` line at all | the geofence never fired; the wake came from the significant change only |
| `waitJoin joined` after the short stop | the 1,000 m rule for Auto Mode starts |

Then decide: late notice → keep the lead-in, perhaps a smaller radius or a second wake source
(`CLVisit` departures, decision D3); late delivery → try `CLLocationManager.startMonitoring(for:)`
(region monitoring that relaunches a terminated app) next to `CLMonitor`.

## 1b. Findings from two iPhones on one drive (2026-11-04)

The 16:39 Auto Mode drive (a jam, half of it stopped), carried together:

| | iPhone 17 Pro Max | iPhone 14 |
|---|---|---|
| Stored | 5.17 km | 5.62 km |
| Raw positions | 5.73 | 5.96 |
| Smoothed 8 m / 15 m | 5.37 / 5.22 | 5.43 / 5.24 |
| Accuracy p50 | 12.6 m | 14.2 m |
| Held by the stop anchor while the phone said > 1 m/s | 222 m | 97 m |

Same-second separation p50 4 m: the phones agree on the road; they disagree on noise. Candidates
(replay every drive with `task replay` before adopting either):

- F1 (over-count, the 14): measure distance on a lightly smoothed track (~5 m, as the display
  route is) instead of fix to fix, so jitter while moving stops adding up. Both phones would land
  within ~1–3 %.
- F2 (under-count in jams, the 17): crawling at 1–2.7 m/s stays held at the stop anchor until
  100 m; let a crawl that keeps one direction for ~10 s leave the stop.
- F3 (done, rules v5): departure and arrival clamped inside the drive; fixes recorded during the
  auto-finish grace still count toward distance when they leave the anchor; only drift so far.

## 1c. Checklist for 2026-11-06 (build of 2026-11-05 afternoon, all three iPhones, fresh databases)

Installed 2026-11-05 ~14:00 with `CONFIRM=erase` and no restore: the owner polishes the empty states
first. Each evening: `task pull-all`, `task events`, `task replay`; findings in device-testing.md.

Field (no code):

Labels (2026-11-07): **[passenger]** read off the screen or done on the phone while moving, so
only with a passenger; **[after parking]** on the phone once parked; **[logs]** from `task pull-db`
/ `task events` at the desk. Anything set up before leaving (Low Power Mode, a force-quit, Auto Mode)
is done parked.

- [ ] **[logs]** Leave Home with Carodo closed (not in the foreground), 2–3 times: `woke geofence left
      place|parking` before any `significantChange`, and how far out (the 05/11 loop was the first
      region exit to wake Carodo by itself).
- [ ] **[logs]** Add a Place, then leave it without reopening the app: `geofence left place` (the place is now
      watched at once).
- [ ] **[after parking]** + **[logs]** A car with CarPlay, one car in the garage: linked by itself, the drive sure (not pending),
      `car_audio = carplay`.
- [ ] **[passenger]** Start, CarPlay or a shortcut while parked: "Ready · Waiting to move", then Live once moving.
- [ ] **[logs]** Car audio lost while stopped: ends after 90 s (`autoFinished disconnected`).
- [ ] **[after parking]** + **[logs]** Parked minutes cut off (carodo-ios `fca3622`, `af84aa1`;
      `field-tests/2026-11-08-parked-minutes.md`): an end by itself after the grace, Finish after
      waiting parked, and a force-quit while parked opened 10+ min later each end at the stop, with
      no fix after `ended_at`.
- [ ] **[passenger]** + **[after parking]** A pending drive on a motorbike: no panel, the dashed chip; answer from the Journeys card
      (driver, passenger with each mode, Not me); a passenger route thin and grey on the Map.
- [ ] **[logs]** A night indoors with Auto Mode on: no drive, battery flat.
- [ ] **[passenger]** + **[logs]** App killed mid-drive: next launch `launched recovered=1`, no sequence gap.
- [ ] **[logs]** Force-quit from the app switcher, then leave: does iOS still relaunch Carodo?
- [ ] **[logs]** Battery per hour of recording (`battery … net=`), on battery and charging (05/11: 5 % in 44 min, unplugged).
- [ ] **[logs]** Low Power Mode: wake and start latency.
- [ ] **[after parking]** + **[logs]** Bicycle, if still wanted: the switch, `detectionTimedOut cycling`, handlebar mount readings.
- [ ] **[after parking]** + **[logs]** Every saved drive logs `ride …` and `motion walkAfterStopS=…`; answer each pending drive so
      the `ride` lines get labels.

Tuning, once the data is in:

- [ ] **[logs]** `walkAwayS` (built 2026-11-05 at 20 s): tune from 5–10 real stops of `walkAfterStopS`
      (so far: 9 s, and `none` on 05/11 16:22).
- [ ] **[logs]** D2: geofence radius (150 m) and detection window (120 s); 05/11 took 1:47 to confirm.
- [ ] **[logs]** B1 on battery (lower GPS during a long stop without Low Power Mode): measure before and after.
- [ ] **[logs]** How the person travelled: rules from the labelled `ride` lines (metro, bus, ride, own vehicle),
      at most ordering the answers (carodo-ios `docs/specs/vehicle-detection.md`).
- [ ] **[logs]** D3: `CLVisit` as a third wake source, decided from the geofence results above.

## 1d. Checks for the evening build of 2026-11-05 (TuanNgo iPhone, installed 19:35)

What changed (`gps-perf-audit.md`, second pass): the Map's live updates stay off in `.preparing`
(A1); the follow camera glides linearly over the fix interval (B3); `LiveLine.segments` kept
incrementally (B5); the tracking mode moves inside `session.start`/finish via
`DriveSessionManager.onActiveChange` (A2/A3); `TripWriter` logs `writeBacklog` (C2).

Already seen on the device (stationary, 19:37–19:42): `mode recording` / `mode standby` logged in
the same millisecond as `driveStarted` / the discard (the earlier build lagged 54 ms behind the
view's `onChange`). No `writeBacklog`.

Each evening `task pull-db` and read `tracking_events`; on a drive:

- [ ] **[passenger]** + **[logs]** Manual Start while Auto Mode is **detecting** (just after leaving Home, before it starts by
      itself): `mode recording` in the same millisecond as `driveStarted`, no second continuous GPS.
- [ ] **[logs]** Auto Mode start and auto-finish: `mode standby` at the finish, then the next drive wakes on
      `geofence left parking` from **this** drive's end (the parking spot is now set after the mode
      change, so it must be the route's end, not the last known location).
- [ ] **[passenger]** Start, then look at the Map before the first fix: the dot shows (last known spot) and moves
      once the first fix is accepted; while paused it still moves.
- [ ] **[passenger]** Map following for a whole drive: the camera rolls evenly, no stop-and-go each second; heading
      follow while stopped still turns with the compass.
- [ ] **[logs]** Battery per hour with the Map open and following, vs the 05/11 figure (5 % in 44 min).
- [ ] **[logs]** No `writeBacklog` on any drive (a line there means SQLite fell behind: report it).

Added the same evening (needs the next install, which erases: the schema lost its CHECKs):

- [ ] **[after parking]** + **[logs]** **Walk away** (`walkAwayS`, built): park, get out and walk off. The drive ends 20–40 s
      after the walk begins, at the stop (`autoFinished walkedAway`, `end_reason = walked_away`),
      instead of 5 min later. Compare with `motion walkAfterStop=…S` on the same drive. The 16:22
      drive logged `walkAfterStop=none` (Core Motion saw no walk in the 5 min): if that is common
      (phone left in the car, or iOS late to report walking), the grace still ends it.
- [ ] **[after parking]** Sitting in the parked car for a few minutes: no walk-away; the grace ends it as before.
- [ ] **[logs]** **Short walks at a stop** (05/11 16:22: a wait with a short walk that nothing recorded; that
      drive's `motion` said `automotiveS=556 walkingS=0`): read the new `motion timeline …` line
      of each drive. A `w`/`r` token after a stop's start shows Core Motion saw the walk (and how
      confident, how long until the next token); none means iOS never reported it. Note the stop
      and roughly how long you walked, to compare.
- [ ] **[after parking]** **Lead-in start**: an Auto Mode drive from Home lists its start before the first fix (the
      departure moves back by the lead-in's time) and its drive time is no shorter than its moving
      time. Drives from before the install are re-derived at launch (recorder version 6).
- [ ] **[after parking]** **Trim, parked tail**: an auto-finished drive's timeline ends in a flat grey stretch with a
      parking sign (the minutes after the arrival), not near-empty speed bars.

### The 16:22 Auto Mode drive (2026-11-05, `831A48E9`), read from the pulled database

- **The start "joined by itself" is the lead-in, as designed.** iOS woke Carodo at 16:22:04
  (`geofence left parking` and `left place`), the drive started 16:22:15, its first fix 230 m from
  the parked spot (`fromParkedM=230`). Gap healing routed the missing way out of Home with Apple
  Maps: `trip_gaps` `start_sequence = -1`, `healed`, 451 m (rule: 100–1,500 m straight from the last
  drive's end, tracking.md "Lead-in").
- **Open question from it:** the lead-in adds its moving time but not to the elapsed time (the
  start is unchanged), so this drive stores `moving_duration_s` 604 > `elapsed_duration_s` 556.
  Moving longer than elapsed reads wrong anywhere both show (and in an average over elapsed).
  Options: move `departed_at`/the shown start back by the lead-in's time, or leave the lead-in's
  time out of moving. A product call; not changed.
- **The end did not lose GPS.** The raw track is 857 fixes at 1 Hz from 16:22:12 to 16:36:28, no
  gap over 4 s, median accuracy 8 m (13–14 m after 16:34). The car stopped at 16:31:28 (the
  drive's end, `arrived_at`); the stop was confirmed 16:31:58 and auto-finish waited the grace to
  16:36:28 (`autoFinished stopped`, `walkAfterStop=none`). Those 5 min of parked fixes are kept
  (raw samples are never dropped) and the trim timeline spans them (`TrimTrack.endedAt` = last
  sample), so its last third is near-zero-speed bars that look like missing GPS.
  Ideas, not decided: draw the after-arrival tail of the timeline as "parked" (distinct, not
  speed bars), or start the end grip at `arrived_at` with the tail outside it; `walkAwayS`
  (decided, to build) would shorten such tails when the person walks away.
- Lowering the GPS at a stop is off on battery (`lowerWhileStoppedOnBattery = false`, B1), which
  is why the 5 parked minutes ran at full rate.

## 2. Open work (after the field test)

| # | Work | Needs |
|---|---|---|
| O1 | Trim a walk longer than 100 m at either end with Core Motion `walking` | a real drive with a long walk |
| O2 | Vehicle detection slice 2: the parked-spot rule and "Right vehicle?" after the drive | a person with 2+ vehicles |
| O3 | Developer mode: ~~Report a drive~~ (**done 2026-11-04**), rejected fixes live, GPX, re-derive, map overlay | — |
| O4 | The toast queue survives a relaunch ("Drive saved") | built 2026-11-05 (`UntoldDrives`, ids kept as a preference) |
| O5 | Replay screen: compressed departure, arrival and long stops | the replay screen |
| O6 | Bicycle thresholds and the 12 km/h start for slow city riding, tuned with `task replay` | real rides |
| O7 | Pending drives, the rest: "My other vehicle" (add a vehicle from the answer), the "Add your motorbike to the garage?" hint after 3 answers | — |
| O8 | "I'm a passenger" in the Start panel; turning a sure drive into a passenger trip from the detail | — |
| O9 | Journeys banner "N drives need a look", answering them one after another | — |
| O10 | CloudKit push skips pending trips (`confirm_by` set) | built 2026-11-05 (`GRDBCloudSyncStore.pendingChanges`) |

2026-11-05: iCloud sync (code; device check waits for the paid account) and O4 built.

Decisions for the owner before tuning Auto Mode:

- ~~D1: the parking spot as the drive's start place~~ **done 2026-11-04 as the lead-in**: Auto
  Mode's missed start (~500 m measured) and the way out after a joined wait are routed by Apple Maps
  from the previous drive's last fix (carodo-ios `docs/tracking.md`, Lead-in).
- C **decided 2026-11-05, built**: the 05/11 school run lost ~2 km (no exit while leaving home,
  `geofence left` only with a significant change 2 km out). The parking geofence moved to
  `CLLocationManager.startMonitoring(for:)`, every saved place got its own exit region (`leftPlace`),
  a significant change pads the circle by its accuracy up to the radius only (`ParkedCheck`, held
  ones logged), the lead-in may start at the place the drive is leaving, and battery lines carry
  `net=`. Device check: `woke geofence left place|parking` before `significantChange`, and how far
  out. **Seen 2026-11-05 (TuanNgo, 16.8 km loop):** the whole loop kept (first fix 18 m from Home);
  `geofence left parking` started the way back in 19 s, and `left place` + `left parking` woke
  Carodo with no significant change at all: the first region exits seen to wake it by themselves.
  Fixed from it: a saved place is watched at once (it waited for the app's next return), and pending
  drives stay out of the iCloud queue on every later write. Was: in all three Auto Mode starts so far `woke leftParking` came in
  the same second as `woke significantChange`: the parking geofence never woke Carodo by itself.
  Log `woke geofence left delayS=…` (built) tells whether iOS noticed the exit late or delivered it
  late; if late delivery, try region monitoring through `CLLocationManager.startMonitoring(for:)`.
  The privacy zone setting does not touch recording (checked 2026-11-04).
- D2: geofence radius (150 m) and detection window (120 s), from the field test numbers.
- D3: `CLVisit` departures as a third wake source, or dropped as redundant.

Outside the engine but on its data: `trips.revision` in the publish payload builder; `region_cell`
for Nearby (API contract, P5); the Feed by vehicle class (ADR 0007, API contract).

## 3. Battery and performance review

**Full audit (2026-11-05), for careful review:** [`gps-perf-audit.md`](gps-perf-audit.md) —
findings A–E with evidence, effort, and comments (dual GPS in `preparing`, MainActor /
Observation churn, Map camera thrash, writer backpressure, threshold scatter, priority order).

### Snapshot as of 2026-11-04 (proposals B1–B7)

What cost energy then, from the code (several rows below are now Done; the audit above checks
what remains):

- Recording: one `CLLocationManager`; accuracy/activity now follow `RecordingGPS` (B2/B3 Done),
  not always BestForNavigation. Still ~1 Hz while moving; `pausesLocationUpdatesAutomatically =
  false`.
- Detection: a second manager at Best (B4) for up to 120 s per wake.
- The Map: live line is thinned (`LiveLine`, B5 Done), and idle Map uses session fixes once
  `.preparing` or `.recording` (B6, audit A1). The follow camera glides over the fix interval
  (audit B3).
- Cheap already: significant changes + region monitoring in standby, writes batched (10 / 15 s),
  the 20 s auto-finish check, the barometer only while recording.
- Measured once: a 31 min motorbike drive used 5 % (60 → 55 %, Low Power Mode on at the start).

Proposals, best value first. Each one is measured before and after (Developer → Battery %/hour,
MetricKit's location time by accuracy, Instruments Energy Log on a device) and replayed
(`task replay`) so the distances do not move.

| # | Change | Why | Risk |
|---|---|---|---|
| B1 | **After the field test** (needs a measured baseline and a device check of the resume). **Low Power Mode part built 2026-11-04** (one rule, `RecordingGPS`: a stop held 60 s lowers to 100 m with a 50 m filter; any fix restores); on battery without Low Power Mode it stays off (`lowerWhileStoppedOnBattery`, later the `stopLowPowerGPS` flag) until measured. Device check: the app keeps running and the first fix on leaving comes soon. **Lower GPS while a stop lasts**: once the stop anchor has held 60 s, switch to `kCLLocationAccuracyHundredMeters` with a 50 m distance filter; back to full accuracy on a fix 50 m from the anchor or a trusted 2 m/s | Parked minutes (up to 5 or 10 before auto-finish, plus every long light and jam) cost as much as driving; Traccar's SDK pauses GPS after 60 s still and wakes on a 100 m region exit | a slower resume after the stop: the first metres come back as a straight line from the anchor, as today; the no-signal timeout (720 s) must stay longer than the grace |
| B2 | **Done 2026-11-04.** **BestForNavigation only while charging**, `kCLLocationAccuracyBest` on battery | Apple's own guidance; CarPlay and car chargers usually charge the phone | fewer fixes in tunnels or urban canyons on battery: check with `task replay` and gap counts |
| B3 | **Done 2026-11-04.** **`activityType` per class**: `.fitness` for a bicycle (no road snapping, paths and parks), `.automotiveNavigation` for car and motorbike | the activity type steers Core Location's own filtering | none known; a bicycle on a road should still read fine |
| B4 | **Done 2026-11-04.** **Detection at `kCLLocationAccuracyBest`** instead of BestForNavigation | the window needs trusted Doppler speeds, not navigation precision | a later confirm: measure with the start latency |
| B5 | **Done 2026-11-04.** **Live map line from a thinned route**: append to a simplified polyline (or redraw at most every few seconds) instead of the whole raw route on every fix | a 2 h drive is 7,200 points redrawn twice a second while the Map is visible | none to recording (display only) |
| B6 | **Done (2026-11-05).** **One location stream while recording**: Map uses session fixes in `.preparing` and `.recording`, not `liveUpdates` (audit A1; `.paused` keeps the Map's updates, the session's GPS is off). The detection→recording handoff (A2/A3) is synchronous / milliseconds — tidiness only | removes a second session | the dot when the session has no fix yet |
| B7 | **Check the route copy cost** in Instruments: `DriveMetrics.route` grows every fix inside a struct read by views | a copy-on-write per fix would be O(n²) over a long drive | only if Instruments shows it |
| B8 | **Done (2026-11-05, audit B3).** **Follow camera glides linearly over the fix interval** (0.2–1.2 s) instead of a 0.8 s ease per fix | MapKit thrash while following | feel of follow while driving |
| B9 | **Partial (2026-11-05).** `LiveLine.segments` cached (B5); marker heading already isolated (B4 withdrawn). **Open:** throttle Observation (B2), after Instruments, so the Map body is not rebuilt at GPS rate | CPU while Map + recording | must not blank the live line or marker |

Not proposed: `pausesLocationUpdatesAutomatically = true` (iOS pauses at a long light and resumes
late or not at all in the background; Stop and wait covers the long stops instead), a distance
filter while moving (fewer fixes make the jump filter and replays worse for little gain at 1 Hz).

## 4. What OwnTracks and Traccar Client teach

**OwnTracks (iOS)** has four modes: Quiet and Manual (no background monitoring), Significant (the
everyday mode, Apple's ≥ 500 m / ~5 min changes, "the most battery-efficient") and Move (continuous
GPS, publishing every `locatorDisplacement` 100 m or `locatorInterval` 300 s, "about as much
battery as a navigation app", recommended only while charging or moving fast). Region monitoring
runs apart from the modes.
→ Carodo already matches this split (standby on significant changes and a region, GPS only while
detecting or recording). The lesson is the charging advice (B2) and naming the cost honestly in
the Auto Mode sheet.

**Traccar Client SDK (iOS)**: moving and stationary states; stop detection from Core Motion,
combining live updates with a historical query at start so a phone already still is classified
right; after `stopTimeoutSeconds` (60) still it pauses GPS and watches a `stationaryRadiusMeters`
(100 m) region whose exit resumes tracking; significant changes and region exits relaunch a
terminated app; a stationary heartbeat (off by default, needs background fetch); positions kept
when any of distance (75 m), time (300 s) or heading changes; accuracy MEDIUM (100 m) by default;
a SQLite FIFO upload queue with backoff from 5 s to 5 min; a force-quit pauses tracking until the
app is opened, and so does a reboot.
→ For Carodo: B1 is Traccar's stationary pause adapted to a drive journal (Carodo keeps 1 Hz while
moving, since replay and the jump filter need it); the historical motion query at start matches
what Auto Mode does (`recentActivity(minutes: 2)`); the force-quit and reboot limits are worth
telling the person in the Auto Mode sheet once proven on a device; the upload queue is Carodo's
outbox already. Traccar's server-side trip rules were compared in `tracking.md`.

Sources: owntracks.org/booklet/features/location, traccar.org/client-configuration,
traccar.org/traccar-client-sdk (read 2026-11-04).
