# Cinematic Journey Replay (V2.3R)

Agreed with the owner on 2026-11-08: Replay comes before Journey Enrichment. Three phases, each
landing in `carodo-ios/docs/specs/replay.md` when built; this file keeps the order, the slices, the
state and what is still open. Map technology is already decided: `MKMapView` (carodo-ios ADR 0015,
"Cinematic 3D Route Replay will draw on MKMapView too").

| Phase | Scope | State |
|---|---|---|
| **R.1** Cinematic Route Replay | Full-screen replay from Journey Detail: the recorded route, the Carodo wheel moving on recorded time, one Follow camera in 3D pitch, the speed-profile timeline, play / pause / seek / rate, live distance and speed | R.1a done (2fdd363); R.1b+c done 2026-11-08 (carodo-ios c5e263f); R.1d built 2026-11-08, owner's review; R.1e (device) next |
| **R.2A** Camera Foundation Polish | Opening (high over the start, down into Follow) and Cruise (dynamic distance on straights), on a pure `CameraDirector` with hysteresis, hold and cooldown in screen time | Done 2026-11-08 (carodo-ios 743ea84, Opening + Cruise) |
| **R.2B** Contextual Camera | Rest, Hairpin Reveal, Terrain Reveal, Junction Reveal: one at a time, each only once its trigger is proven trustworthy on device drives | Draft (`replay.md`, R.2) |
| **R.2C** Journey Highlights | Camera moments on verified facts (provinces crossed, Smart Stops, milestones); with R.3 and Journey Enrichment | Later |
| **R.2 options** | Driven line Copper or by speed (menu); Standard or Satellite map (menu) | Decided 2026-11-08, after R.2A |
| **R.3** Replay Highlights & Sharing | Highlights from facts the device already has, the reserved header slot, a 30–60 s Cinematic Recap (an edit, not a faster rate), 9:16 video export, the privacy trim on everything shared | Draft in `replay.md` (R.3); video rendering needs a spike |
| **V2.3** Journey Enrichment | Smart Stops, POI, Fuel / Charging, Weather | After R.3. Once built, its stops and places become highlight sources; Replay never queries them while playing |

## Principles across the three phases

- **One timeline model.** `ReplayTimeline` is built once, off the main actor, before the first
  frame: positions, cumulative distance, speed, compressed stops, gaps. Camera, metrics, highlights,
  the recap and the video all read it. Nothing is queried (POI, terrain, geocoding) while playing.
- **Recorded time is the truth.** The playhead is a recorded instant; a rate multiplies recorded
  time inside moving spans; a compressed stop plays in a fixed ~1 s whatever the rate. The clock
  shown is always the real local time of the drive.
- **No invented movement.** The wheel moves only between two trusted fixes of one segment, or along
  a road gap healing stored (drawn lighter, "estimated"). Across a straight gap or a pause it does
  not glide: the line is dashed and the wheel jumps after a short "GPS lost" hold.
- **The map is one persistent `MKMapView`.** Overlays are added once; per frame only the wheel
  annotation and the camera move, from the player's frame callback, never through SwiftUI state.
  SwiftUI sees metrics at ~5 Hz.
- **Reuse before adding:** `JourneyRepository.detailTrack` (trim applied), `TripReplay.analysisRoute`
  (so the end distance equals the detail page's), `RouteRevealPath` / the reveal's `strokeEnd`
  technique for the driven line, `AtlasLocationMarkers` (the wheel), `RouteEndMarker` /
  `PlaceMapMarker`, `AtlasOverlays` casing and `MapTuning`, `JourneyMapFraming`, `SpeedBand`,
  `DisplayFormat`, the journey title from `JourneyPresentation`.

## Architecture (R.1)

```
JourneyDetailView ── Replay control ──▶ .fullScreenCover
ReplayView (SwiftUI)
 ├── ReplayHeader           back · title capsule (title / local date) · Overview · Follow · [highlight slot, empty in R.1]
 ├── ReplayMapView          UIViewRepresentable; Coordinator owns the MKMapView, the route overlays,
 │    └── MKMapView          the wheel annotation and applies FollowCamera output each frame
 └── ReplayControlPanel
      ├── ReplayScrubber    speed-profile bars + handle + local clock (start / now / end)
      └── Play / Pause (Copper) · rate pill · distance so far · SpeedDial (moved to DesignSystem)

Features/Replay/ViewModels
  ReplayViewModel   @Observable: loads the track, builds the timeline (@concurrent), title, LoadState
  ReplayPlayer      @Observable final class: CADisplayLink, playhead, rate, play/pause/seek/restart;
                    per frame → map coordinator (closure); metrics published at ~5 Hz; stops and
                    releases the display link on dismiss
Core/Replay (pure, nonisolated, unit tested)
  ReplayTimeline    spans (moving / stop compressed / healed gap / straight gap / pause),
                    playback time ↔ recorded time, position(at:), distance(at:), speed(at:),
                    speedProfile(bins:)
  FollowCamera      smoothed heading (max turn rate, dead band), look-ahead so the wheel sits below
                    centre, distance / pitch; no update under a threshold of change
```

`Core/Replay` is a folder, not a module or target. No schema, API, permission or dependency change in
R.1.

## R.1 slices (one commit each once proven)

| Slice | Outcome | Proof |
|---|---|---|
| **R.1a** Timeline | `ReplayTimeline` from a `JourneyDetailTrack` (or the display route when no raw track): departure → arrival window, stops > 60 s compressed to ~1 s, pauses and straight gaps as jumps, healed gaps along their road, cumulative distance from the analysis route, trusted speed or nil, speed profile | Unit tests: both sides of the 60 s stop rule, a gap, a pause, a missing speed, a joined drive, the end distance equal to the journey's, 1 Hz × 3 h built under a budget |
| **R.1b** Screen shell | Replay control on Journey Detail; full-screen `ReplayView` over a persistent `MKMapView`: route (faint), ends, wheel at departure, header, panel with a scrubber that seeks (no playback yet) | Simulator screenshots Light / Dark / large Dynamic Type / Vietnamese |
| **R.1c** Playback | `ReplayPlayer`: play / pause / rate / seek / restart at the end; wheel moves; driven part drawn by `strokeEnd`; metrics at ~5 Hz, no rolling through values on seek | Unit tests on the player's clock (injected time); Instruments: no overlay re-adds while playing |
| **R.1d** Follow camera | 3D pitch Follow; manual pan / rotate / zoom suspends it and shows Follow; Reduce Motion keeps the whole route and hides Follow | `FollowCamera` tests (turn-rate cap, dead band, look-ahead); screen recording |
| **R.1e** Device pass | Short urban, long (2 h+), curvy, gappy, missing-speed and dense drives from `task ios:pull-db`; oldest supported iPhone; memory back to baseline after dismiss | Device check; numbers recorded here |

## Decided (owner, 2026-11-08)

- **Rates:** 5× / 15× / 30× / 60× / 120× (long drives were too slow at 15×), opening at the
  slowest that plays the drive in about 3 minutes. The fitted 30–60 s length is the R.3 Cinematic
  Recap (an edit), not a rate.
- **Surface:** solid, adaptive (`carodoFloatingSurface`, Ivory in Light, Charcoal in Dark), not the
  Live surface's always-Charcoal: Replay is reached from Journey Detail and is not the live drive.
  Glass behind `-carodo.debugReplaySurface glass`, compared on the iPhone before any change.
- **Entry:** the round play button at the bottom left of the detail map, above the sheet (where the
  Journey Reveal's button was). The speed legend moves to its right in Speed display.
- **Layout from the reference (2026-11-08):** header row = back · title capsule (title over date) ·
  Overview · Follow (Share in R.3); panel = speed-profile scrubber with a playhead and clock time,
  then Play (Copper) · rate pill · distance · compact speed dial. The live sheet's private
  `SpeedDial` moves to `DesignSystem/Components` for both (R.1b).

## R.1a result (2026-11-08)

Built: `Core/Replay/ReplayTimeline.swift`, and `TripReplay.metrics(onStep:)` so the timeline walks
the drive with the summary's own recorder (distance at arrival = the journey's, stops held where the
summary held them). 16 tests in `ReplayTimelineTests` (both sides of the 1-minute stop, straight
gap, healed gap, lead-in, pause, unknown speed, rates, default rate, scrubber bars, display-route
fallback, a 3-hour drive). Simulator, Debug: a 3-hour drive builds and plays every frame of a 120×
playback (~6,000 reads) in 20 ms in total. Not measured on the iPhone yet (R.1e).

## R.1b + R.1c result (2026-11-08, carodo-ios c5e263f)

Built together so the screen could be judged playing: the play button on the detail map, the
full-screen `ReplayView` (header, speed-profile scrubber, play / pause, rate pill, distance, compact
`SpeedDial`), `ReplayPlayer` (display link, ~5 Hz to SwiftUI), `ReplayRoute` (runs cut at jumps,
simplified at 8 m, each fix placed along its run for `strokeEnd`) and `ReplayMapView`. Moved to the
design system to share them: `SpeedDial` (from the live sheet, with a compact size) and
`DriveLocationMarker` / `MarkerHeading` (from the Map tab). The detail map is taken down while Replay
covers it. 1341 tests pass; lint and warnings clean. Still whole-route only: Follow and 3D in R.1d.

## R.1d result (2026-11-08)

`FollowCamera` (pure, 11 tests): 60° pitch, look-ahead 10 % of the distance (0.22 put the wheel on
the panel's edge), heading eased (0.8 s) with a 3° dead band and a 90°/s cap, distance from the
speed on screen (4 s of travel, 600 m–15 km, eased 1.5 s), a 1 s per-frame blend into Follow, a
snap on seek. Course falls back to the stretch's bearing (`ReplayTimeline.travelBearing`).
Header: Overview and Follow; the first Play follows; a finger frees the camera. Realistic
elevation on. Open: 3D buildings cannot be hidden on the standard configuration and sometimes
stand in front of the way ahead; tile loading at 120× on a highway needs the iPhone.
Owner review (2026-11-08): the route vanished while playing (strokeEnd pushed every frame; now at
most 10 Hz, proven by 12 consecutive frames), open at 15×, look through bends (pure pursuit 0.8 s
ahead), and an arrival beat (camera ahead to the finish, rising, then back to the whole route).

## R.2 — how the Director joins what exists (2026-11-08)

Extend, never rewrite. Per frame, unchanged: player → coordinator `show(frame)` → `FollowCamera.pose`
→ the one `setCamera`. Added between them:

```
ReplayViewModel.prepare (off main): ReplayTimeline · ReplayRoute · CameraScript (new)
  CameraScript: for each keyframe, how straight the road is over the next 250 m … 32 km (chord /
  path, two pointers, O(n) per window); nil across a jump or past the end. Later: grade, bend density.
coordinator.show(frame):
  facts  = script.straightness(at: keyframe, seeing: follow.distanceM × 2.5)      O(log n)
  intent = director.intent(facts, arrivalNear, dt)   CameraDirector (pure): phase, hysteresis,
                                                     hold, cooldown, eased strength; a seek resets
  pose   = follow.pose(…, intent)                    distance × intent.distanceScale; Opening lift
  setCamera(pose)                                    still the only writer of MKMapView.camera
```

Checked against what exists, no conflict found: pure pursuit still picks the heading (the Director
never touches it); Cruise multiplies the speed-led distance inside its bounds; the Arrival stays in
`FollowCamera` and turns Cruise off in its last seconds; per-frame cost grows by two binary searches.

## Performance rules for R.1b–R.1d (from the Map, the live drive and Journey Detail)

Each comes from a measured problem (`carodo-ios/docs/design-system.md`, Map rules — learned the hard
way; `docs/architecture.md`, Complexity budget):

1. **One `MKMapView` for the screen's life.** Overlays added once when the timeline is ready: the
   faint whole route and the driven line. The driven line grows by `strokeEnd` on its renderer, as
   the Journey Reveal does; never removed and re-added per frame.
2. **The frame loop bypasses SwiftUI.** `ReplayPlayer`'s `CADisplayLink` calls the map coordinator
   directly (wheel coordinate, camera, `strokeEnd`); SwiftUI observes only play state, rate and the
   ~5 Hz metrics, so `body` never runs per frame.
3. **The camera is set, not animated, per frame** (`mapView.camera = …` inside the tick). A
   `UIView.animate` per frame stacks animations and, without `.allowUserInteraction`, blocked every
   touch on the live map (2026-11-06). Animated flights only for one-off moves (Overview, the
   descent), with `.allowUserInteraction`.
4. **Nothing changes, nothing is drawn.** Paused, or a compressed stop with the wheel still: the
   tick skips the camera and annotation when the change is under a threshold (the `MapFix.changes`
   idea); the display link pauses while paused.
5. **Frame rate asked for, not assumed:** `preferredFrameRateRange` 30–60 fps (not 120 Hz
   ProMotion) until the iPhone shows the difference is worth the battery.
6. **Taken down when not seen:** backgrounding pauses playback and the display link; dismissing
   invalidates the display link (it retains its target) and releases the map.
7. **Hosted SwiftUI marker:** the wheel in an `MKAnnotationView` with `safeAreaRegions = []`
   (the 95 pt offset bug); `layoutMargins` set in full, camera moves after the first layout.
8. **Measure on the iPhone over USB** (`xctrace`, Time Profiler + Core Animation FPS), never only
   the simulator; compare the solid and glass panels there (`-carodo.debugReplaySurface glass`).

## Device checks (R.1, open)

- Smooth 60 fps follow on the oldest supported iPhone with a 2-hour drive.
- Memory and the display link released on dismiss (Instruments, Allocations).
- What 3D looks like in Vietnam: realistic elevation and 3D buildings are city-dependent; the
  pitched flat map must still read well.

## Wow track (owner, 2026-11-12)

The owner moved Replay ahead of the TestFlight gates for motivation and to have a short intro video
to show ([master-plan.md](master-plan.md), steps 1–4). Each step is a slice: plan, owner approval,
build, device check, one commit. The behaviours and the Director's rules stay those of
`carodo-ios/docs/specs/replay.md` (R.2, R.3); this section keeps the order and the open questions.

| Step | Outcome | Done when |
|---|---|---|
| **W1** TD-1 stop alignment | Replay's compressed stops and the journal's `JourneyAnalysis.stopIntervals` answer "a finished stop on the timeline" with one rule | A replay test on the owner's drives shows the same stops as the detail page's route timeline |
| **W2** R.2B one behaviour per slice | Rest first (the most frequent, the cheapest trigger), then Hairpin Reveal, then Terrain Reveal where MapKit has 3D terrain; Junction Reveal last or never | Each: thresholds on both sides tested, `docs/tracking.md`-style table in `replay.md`, a screen recording of a real drive at 15× and 60× approved by the owner |
| **W3** Video spike | A one-day answer, written here, to: how frames of the replay reach a video file | A 10 s 9:16 clip of a synthetic drive plays in Photos, with its frame rate and render time measured on the iPhone |
| **W4** Recap + export | The 30–60 s Cinematic Recap (an edit: highlights near real rate, the rest compressed) and a 9:16 export from it, through the share sheet | Exported on the iPhone from a real drive, privacy trim on, attribution visible, under a minute to render |

### W1 result (2026-11-12, carodo-ios 969ba51)

Audit, measured on the 29 journeys in `drive-data/` (34 stops of a minute or more): both sides found
the same 34 stops, but Replay's began about 10 s later (the recorder's stop confirmation) and ended
one fix earlier (median difference 11 s), so 6 of 34 labels differed: four by rounding, one joined
wait (the journal's 1,298 s stop played as two stops of 174 s around a "No GPS"), one stop left
without GPS (71 s in the journal, 177 s in Replay). The thresholds differed too (`>= 60 s` and
`> 60 s`).

Built: `ReplayTimeline` finds no stop of its own; it compresses the stops
`JourneyAnalysis.stopIntervals` returns (raw track and display route alike). A stop left without GPS
ends at the journal's estimate, on a keyframe added there; a jump inside a stop is part of the stop
(owner, 2026-11-12: a joined wait is one "Stopped 22 min"); the threshold is the journal's. Kept
apart, as the playing moment's state: a held fix reads speed 0, stops under a minute play as they
were, gaps outside a stop. `ReplayStopAlignmentReplayTests` asserts, on the drives in `drive-data/`,
the same count, start, end and label: 34 of 34.

Open: nothing on a device beyond the R.1 checks. For W2, Rest should trigger on these stop spans,
not on the held state. `drive-data/carodo-20261111-sim-after-p2.sqlite` does not open read-only
(SQLite error 14) and stops every drive-data replay test at the loader; the run above used a copy
of the folder without it.

### W2 Rest result (2026-11-12, carodo-ios ba17a06, c6d92e5)

Audit, the screen's camera simulated at 60 fps through the 34 stops of the drives in `drive-data/`
(each stop is 1.00 s on screen): Follow turned a median of 24° at 15× and 34° at 60× (p90 about
80°, over 45° at 13 of 34 stops) and at 60× came in to 0.65 of its distance (median), then backed out.

Built: Rest holds the heading and distance through a stop span (the journal's stop after W1); no
stand-back (owner); Cruise waits as it is. It also holds under the Arrival, unlike the first plan:
three or four last stops before a finish still turned up to 61° there, and the Arrival moves the
centre, pitch and distance, not the heading. The pose is composed by `ReplayCameraRig` (pure,
`Core/Replay`), out of the map coordinator: a drive-data test runs the screen's code (0° turned,
distance kept, at 15× and 60×), and W3/W4 can render the same camera without a screen. Owner
accepted it from simulator recordings of a real drive at 15× and 60×.

For recordings: `-carodo.debugRestoreBackup <path>` and `-carodo.debugReplayRate N` (carodo-ios
`docs/operations/setup.md`); `-carodo.debugOpenJourney` needs Journeys on Explore
(`-journeys.displayMode explore`). Open: the device pass with the R.1 checks.

### W3 — what the spike must decide

- **Capture route.** (a) `ReplayKit` in-app capture (`RPScreenRecorder.startCapture`) of the recap
  playing full screen into `AVAssetWriter`: real time, what the map really draws (3D buildings,
  terrain), but a system prompt each session and the export takes as long as the recap. (b)
  `MKMapSnapshotter` with an `MKMapCamera` per frame, the route and wheel drawn on each image:
  offline and frame-exact, but slow per frame and its 3D fidelity unproven. (c) Drawing the map
  view's layer per frame: likely blank or slow with MapKit's Metal rendering; try only to rule out.
  Expected answer: (a), unless the prompt or the real-time wait is unacceptable to the owner.
  **Evidence for (b), 2026-11-13:** ImmersiveMap's shipped tour export works exactly that way:
  a fixed time step per frame, each frame held until its tiles are loaded, `AVAssetWriter`
  ([`drive-recorders-study.md`](../references/repos/drive-recorders-study.md) §6). Carodo's rig
  already takes `dt` as an input, so a fixed `dt = 1/fps` drives it without a screen. Try (b) first
  for render time and 3D fidelity; keep (a) as the fallback if snapshots lose the 3D look.
- **Contracts (P6, owner approval before code):** `ReplayKit`/`AVFoundation` are Apple frameworks
  but new to the app; saving to Photos needs `NSPhotoLibraryAddUsageDescription` (the share sheet's
  "Save Video" likely needs it too: verify).
- **Terms:** map imagery inside a shared video must keep Apple's attribution and legal label in
  frame; read MapKit's terms on exported imagery with TD-2 before a video leaves the device.
- **Privacy (P5, P9):** the video uses the privacy-trimmed route with `t` re-based; no start or end
  place, no clock finer than the share card's part of day unless it is only for the owner's eyes.

### Brief for the next session

```text
Outcome: W1 then W2 (Rest) of the wow track; W3 spike only after W2's first commit.
Existing behaviour (files read): carodo-ios Core/Replay/{ReplayTimeline,CameraDirector,CameraScript,
  FollowCamera,ReplayRoute}.swift, Features/Journeys/Views/ReplayMapView.swift, docs/specs/replay.md.
Owner decisions needed: W2 order confirmed; W3 capture route and the Photos permission (P6).
Acceptance: per step table above.
Non-goals: a 3D car model, web replay, highlights from Journey Enrichment (R.2C), new map styles.
Constraints: one MKMapView, Director pure and prepared off the main actor, per-frame cost O(log n),
  the performance rules above; nothing queried while playing; no schema or API change.
Validation: task lint, task warnings, task test; device: a real drive replayed at 15× and 60×,
  Time Profiler + FPS over USB.
Do not: rewrite FollowCamera or the player; touch MainTabView beyond wiring.
```
