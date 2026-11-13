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
| **W3** Video spike (done 2026-11-13: the MapKit view drawn per frame) | A one-day answer, written here, to: how frames of the replay reach a video file | A 10 s 9:16 clip of a synthetic drive plays in Photos, with its frame rate and render time measured on the iPhone |
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

### W2 Reveal result (2026-11-13, carodo-ios b525900)

Audit on the drives in `drive-data/`: no mountain road (the three highway drives have no tight bend,
the 338 km trip four); the bends are in town drives of 2 to 14 km (U-turns, blocks, roundabouts at
20 to 40 km/h), where Follow turned at 45° a second or faster for 15 to 30 % of the time on screen.
So the drafts' Hairpin Reveal and Junction Reveal became one behaviour, the Reveal, tuned in town
(owner, 2026-11-13).

Built: pitch 40°, distance × 1.8, heading eased slowly (at most 25° a second) toward the road's
overall direction. The trigger changed from the approved plan: chord / path under 0.60 cut hard
turning by half only, because a jog right then left reads straight; it is now the corners ahead
summed (`CameraScript.turning`: 30 m steps, a corner is 15° or more; enter at 150°, leave at 60°,
hold and cooldown 2 s on screen), read over 0.75 × the camera's distance. Measured, Follow alone →
with the Reveal: seconds turning hard 280 → 83 at 15×, 143 → 45 at 60×; swings 56 → 4 and 52 → 15;
up 18 % and 30 % of the time on screen. The owner accepted it from simulator recordings of a town drive.

Open: hairpins on a real mountain drive (none in the data); 15 swings left at 60× on very short
town drives; Terrain Reveal after W3 (it depends on what 3D terrain MapKit has in Vietnam).

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

### W3 result on the simulator (2026-11-13; the iPhone run is still open)

A throwaway test (not committed) rendered a made-up 10 s drive at 30 fps, 1080 × 1920, with the
product's camera (`ReplayCameraRig`), three ways, into `AVAssetWriter` (H.264). iPhone 18 Pro
simulator, tiles cached:

| Route | Per frame | 10 s clip takes | Result |
|---|---|---|---|
| (c) the map view drawn per frame (`drawHierarchy(in:afterScreenUpdates: true)` on an `MKMapView` in its own window, the camera set for each frame) | about 40 ms (56 ms with one refresh of waiting) | 17 s | Works, against the expectation above: 3D buildings, the line under them, the annotation, Apple's logo and Legal link all in the frame. Frame-exact, no system prompt, and it is the view Replay already draws |
| (c) the same, waiting for `mapViewDidFinishRenderingMap(fullyRendered: true)` before each frame | 1.4 s | 7 min | Unusable: with a moving camera the callback did not come within 1.5 s for 267 of 300 frames |
| (b) `MKMapSnapshotter` with an `MKMapCamera` per frame | 210 ms | 63 s | Works, 3D buildings and the logo; but the route and wheel are drawn on top of the image (over the buildings), and it is a second renderer to keep looking like Replay |
| (a) `ReplayKit` capture | not run | real time | Not available on the simulator; a system prompt each session |

Answer so far: **(c), the map view drawn per frame**, off screen, paced by the renderer rather than
the clock (each frame is the rig's pose at `frame / fps`). (a) stays the fallback if (c) fails on
the iPhone. Still to prove, on the iPhone: that `drawHierarchy` returns the map there (MapKit draws
with Metal), the time per frame, memory and heat over a 60 s clip, and tiles: a frame is drawn
whether or not its tiles have arrived, so a first silent pass along the camera's path (or a short
wait per frame) must load them. Nothing was added to the app: no framework, no Info.plist key.

### W3: Carodo Studio and a second engine (2026-11-13)

For the iPhone run the spike became a small app outside the repos, `~/code/carodo/carodo-studio`
(bundle id `app.carodo.studio`, owner approved; it holds no drive data and never touches Carodo's
database). It renders the same made-up 10 s drive in four places (Ho Chi Minh City, Da Lat, San
Francisco, Zermatt) three ways and writes its measurements beside the clips;
`./run-device.sh "iPhone name"` builds, installs, renders and pulls them back. The writer follows
ImmersiveMap's `VideoExportAssetWriter` (pool buffers, fixed step, back-pressure, BT.709, HEVC).

The third way is ImmersiveMap (`~/code/oss/swift/ImmersiveMap`, MIT, a Swift + Metal map engine,
linked as a local package; owner asked for a short spike before the W4 renderer is chosen): its
own offscreen export, which waits for each frame's tiles, on OpenStreetMap data from a hosted
planet PMTiles archive, with open terrain relief.

Simulator, 300 frames of 1080 × 1920 (iPhone 18 Pro simulator; not the iPhone):

| Route | Per frame | 10 s clip takes | Seen in the frames |
|---|---|---|---|
| MapKit view (with a silent first pass for tiles) | 80 to 130 ms | 32 to 46 s | Apple's map: many buildings and places, logo and Legal in frame; terrain flat at this camera, in Zermatt too |
| MapKit snapshotter (10 fps) | 170 to 190 ms | about 55 s at 30 fps | as above, route over the buildings |
| ImmersiveMap | 130 to 145 ms | 39 to 43 s | OpenStreetMap: fewer buildings in Vietnam; relief and hillshade in Zermatt; no credit in the frame (must be added); the spike's camera mapping (zoom, bearing) is still off |

The iPhone run is below. Open for
ImmersiveMap: who hosts the planet archive in production (the default is the maintainer's), its
detail outside Europe, a moving wheel in the export, the camera mapping, and the dependency itself
(P6, ADR 0015 names MKMapView). Both engines cover the world: MapKit by Apple, ImmersiveMap by
OpenStreetMap.

### W3 result on the iPhone (2026-11-13, iPhone 12 Pro Max, iOS 27.2)

Carodo Studio rendered the made-up 10 s drive (300 frames, 1080 × 1920) in the four places, one
after another, about nine minutes in all. `drawHierarchy` returns the map on the iPhone: no flat
frame in the 20 sampled per clip, in any place.

| Route | Per frame | 10 s clip takes | Peak memory | Seen in the frames |
|---|---|---|---|---|
| MapKit view | 37 to 38 ms (p95 40 to 43, max 76) in every place | 17.6 to 17.7 s, of which 6.4 s is the silent first pass for tiles | 423 to 763 MB (San Francisco the highest) | Apple's map: 3D buildings, places, the line under the buildings, the wheel, logo and Legal in frame |
| MapKit snapshotter | 172 to 212 ms; 452 ms in San Francisco | 52 to 64 s at 30 fps (measured at 10 fps); 136 s in San Francisco | 418 to 820 MB | as above, the line over the buildings |
| ImmersiveMap | 40 to 148 ms (Da Lat the least, San Francisco the most) | 12 to 45 s | 519 to 1,066 MB | OpenStreetMap: few buildings and no places in Vietnam; relief and hillshade in Zermatt, where MapKit's ground is flat; no wheel, no credit; the spike's camera still looks from farther and another bearing |

Heat: `nominal` at the start, `fair` after the first clip, `serious` after about two minutes of
rendering without a pause, and it stayed there. The MapKit view's time per frame did not change
at `serious`.

**Answer to W3: the MapKit view drawn per frame** (route (c)). It is the fastest and the steadiest
on the weakest iPhone, it is the view Replay already draws, and it adds no dependency. The
snapshotter is dropped. ImmersiveMap stays a later option for terrain only (its relief is the one
thing MapKit did not show), not the W4 renderer: its open points are those listed above.

Open for W4: a 60 s clip (memory, heat, and the render time against "under a minute": at 37 ms a
frame, 60 s at 30 fps is about 67 s plus the first pass, so the frame rate, the 16 ms settle or
the first pass must give); memory near 500 MB on a 6 GB iPhone, 763 MB in a dense city; what the
export does when the iPhone is already `serious`; TD-2 before a video leaves the device.

`run-device.sh` must be run from Terminal: an agent's shell is a background session and cannot use
the signing key (`errSecInternalComponent`). Launching the app and pulling the results work from
either. The clips are in `carodo-studio/results/`.

**Owner, 2026-11-13: agreed.** W4 renders with the MapKit view; ImmersiveMap is looked at again
only if a Terrain Reveal wants real relief.

### W4 plan (approved by the owner, 2026-11-13)

**Reference (owner, 2026-11-13): another drive app's export screen.** What it does: a 9:16 preview
card (map above; distance, a speed dial and the clock below; the drive's name, date and the app's
address at the foot); toggles for theme, text and the car; a range bar over the speed profile with
two handles to pick a part of the drive; an Export sheet with Length 15 / 30 / 60 s, each showing
the rate it means (60 s of a 312 km drive is about 248 ×), or a Speed (1 × to 60 ×) showing the
length it means; 1080 × 1920 at 60 fps. Worth taking: length first with the rate shown, the range
bar on the speed profile (Carodo's scrubber already draws one), the preview being the video's own
frame. Not taken: its video is one fast rate, not an edit; it shows exact times and the start with
place names around it (P5, P9).

**Audit of what exists.**

- `ReplayCameraRig`, `ReplayTimeline`, `CameraScript`, `ReplayRoute` are pure and already take
  `dt`: a renderer steps them at `1 / fps` with no screen. Stops already play in about 1 s.
- The map's dressing (overlays, casing, the wheel, the ends) lives inside `ReplayMapView`'s
  coordinator (569 lines); the renderer needs the same dressing on its own off-screen `MKMapView`,
  so that part is extracted and used by both, not copied.
- `PrivacyZone` exists and trims a route for the Feed (`FeedPublication`); the share card, the
  share sheet for a drive and the part-of-day line are specified in `share.md` but not built.
- Carodo Studio's `MovieWriter` (HEVC, pool buffers, back-pressure) and the map-view render loop
  are the spike's code to bring over. Of its 37 ms a frame, 16 ms is a fixed wait before each draw.

**Slices** (each: plan detail, build, device check, one commit).

| Slice | Outcome | Done when |
|---|---|---|
| **W4a** Renderer | `ReplayVideoRenderer` in the app: an off-screen `MKMapView` with Replay's dressing, the rig stepped at a fixed `dt`, a first pass for tiles, `AVAssetWriter`, progress and cancel. The whole drive at one rate fitted to the length asked. Reached from a DEBUG launch argument only | A real drive from `drive-data/` exports to a 30 s and a 60 s clip on the iPhone 12 Pro Max; per frame, total time, memory and heat written here; the wait before each draw reduced or justified by a count of frames with missing tiles |
| **W4b** The frame | What the video shows beside the map: distance so far, the speed dial, the drive's line (day and part of day, vehicle), the CARODO mark; Apple's logo and Legal link left visible. The privacy zone applied: trimmed route, time from 0, opening and closing frames on the trimmed route only | Owner approves frames in Light and Dark, English and Vietnamese; a test asserts no fix inside the zone reaches the renderer |
| **W4c** Export screen | From Replay's header: a preview of the frame, Length 15 / 30 / 60 s with the rate shown, Export with progress and cancel, then the system share sheet (Save Video, Messages, …) | Exported and saved to Photos on the iPhone from a real drive; the screen in Light, Dark, large Dynamic Type, Vietnamese; the app backgrounded mid-export fails cleanly |
| **W4d** Recap edit | The length is spent unevenly: the opening, the Reveals, the arrival and the highlights near Replay's rate, the long straight parts compressed harder; a pure `RecapScript` made before rendering | Tests on both sides of each rule; the owner prefers it to the one-rate clip of the same drive |
| **W4e** A part of the drive | The reference's range bar: two handles on the speed profile choose the part exported | After W4c, if the owner wants it |

**Decisions (owner, 2026-11-13: all six agreed as proposed; the CARODO mark is added in W4b, drawn over the map's frame).**

1. **One rate first, the edit after (W4d)?** `replay.md` says the recap is an edit, not a faster
   rate. Proposed: ship the fitted single rate first (the reference does only this, and stops are
   already compressed), then judge the edit against it.
2. **Frame rate.** 30 fps proposed. At 60 fps the render takes twice as long: a 60 s clip is 3,600
   frames, over two minutes on the iPhone 12 Pro Max at today's 37 ms.
3. **Time in a shared video (P9).** Proposed: the day and part of day, and time elapsed from 0;
   no clock. The reference shows the exact clock.
4. **Start and end (P5).** Proposed: the privacy zone setting applies as on the Feed shape (300 m
   by default), and can be turned off for one export.
5. **TD-2 gate.** Until Apple's terms on map imagery in an exported video are read, export stays
   behind the DEBUG argument (W4a, W4b) and the Developer screen (W4c); nothing in a release build.
6. **Contracts (P6), approved 2026-11-13, restated:** `AVFoundation` in the app;
   `NSPhotoLibraryAddUsageDescription` in `project.yml` with W4c. No schema, API or package change.

### W4a result (2026-11-13, carodo-ios 00fe310)

Built: `ReplayVideoStage` (Replay's own `ReplayMapCoordinator` and map at 360 × 640 points, no
second dressing), `ReplayVideoRenderer` (first pass for tiles, then one frame per `1 / fps` of the
video's clock through `ReplayPlayer.renderFrame`), `ReplayMovieWriter`, and
`ReplayTimeline.rate(forPlaybackS:)`. Reached by `-carodo.debugReplayExport 30` only; the report
and the clip land in the app's `Documents/replay-export/`.

iPhone 17 Pro Max, iOS 27.2, a real town drive, 30 s asked (31 s, 930 frames, rate 37.6 ×):

| Wait before each frame | Per frame (mean / p95 / max) | Whole export | First pass | Memory | Frames drawn while MapKit loaded | Seen |
|---|---|---|---|---|---|---|
| 16 ms (default) | 63 / 83 / 87 ms | 61.6 s | 3.0 s, no stop timed out | 487 MB | 6 | Complete: 3D buildings, street names, the driven line whole, the wheel, logo and Legal |
| 4 ms | 51 / 67 / 72 ms | 49.9 s | 2.8 s | 497 MB | 14 | not inspected |
| 0 ms | 41 / 63 / 70 ms | 40.9 s | 2.8 s | 493 MB | 0 | Wrong: the driven line broken behind the wheel, street names missing |

So the wait is kept: without it MapKit has not laid out the labels or redrawn the line when the
frame is taken. Heat: `nominal` to `fair` in the first clip.

**Where a frame's time went (iPhone 17 Pro Max, the same 31 s clip, carodo-ios 587a94a).**
The report now splits a frame into setting the camera, the wait, drawing and the encoder.

| Run | Per frame | Wait (asked → real) | Draw | Encoder | Export | Frames repeated (of 930) |
|---|---|---|---|---|---|---|
| As first built | 60.5 ms | 16 → 19.7 ms | 40.1 ms | 0.3 ms | 59.1 s | 26 |
| The app's windows hidden | 46.4 ms | 16 → 21.5 ms | 24.3 ms | 0.3 ms | 46.1 s | 25 |
| … and no wheel / flat ground / line grown at 10 Hz | 46 to 48 ms | | 24 to 26 ms | | | |
| … and the wait 9 ms (one refresh at 120 Hz) | 35.5 ms | 9 → 11.3 ms | 23.5 ms | 0.3 ms | 35.9 s | 31 |
| … and the wait 4 ms | 32 to 33 ms | 4 → 5.2 or 8.0 ms | 25 ms | 0.3 ms | 32 to 34 s | 134 when 5.2 ms was waited, 25 when 8.0 |
| … 9 ms, drawn without the screen's updates | 25.0 ms | 9 → 14.3 ms | 10.3 ms | 0.2 ms | 26.1 s | 326, and 338 jumps |
| … 17 ms, drawn without the screen's updates | 33.3 ms | 17 → 21.6 ms | 11.3 ms | 0.2 ms | 33.9 s | 46 |

"Frames repeated" counts pairs of consecutive frames that are nearly the same; about 25 are the
drive's own standstills and the hold at the arrival.

Kept: the app's own windows hidden while a debug export renders (Replay's screen and map under
the stage cost 16 ms a frame; W4c's Export screen must take them down); the wait is one refresh
of the screen, rounded up (9 ms at 120 Hz, 17 ms at 60 Hz); the map is always drawn after the
screen's updates. Rejected: a shorter wait and drawing without the screen's updates (both repeat
and skip frames); the wheel, the elevation and the line's growth cost nothing measurable. The
encoder is not the cost on a device (it was most of a frame on the simulator).

Result: 63 → 35 ms a frame; a clip renders in about 1.15 times its length on the iPhone 17 Pro
Max. The 24 ms of drawing is `drawHierarchy` itself and did not move.

Open:

- **"Under a minute for a 60 s clip" is not met** on the fastest iPhone (about 70 s), and a
  60 Hz iPhone waits 17 ms a frame, not 9: about 1.3 to 1.5 times the clip's length expected on
  the iPhone 12 Pro Max, not measured. The owner decides: accept it, 24 fps, or a 30 s default.
- **The iPhone 12 Pro Max** has not run it: time per frame, memory and heat there, a 60 s clip.
- **Very high rates.** On the simulator the 312 km drive asked for in 10 s (about 3,000 ×) drew
  an empty grid: tiles cannot follow. 60 s of it is about 250 to 300 ×, not tried on a device:
  `-carodo.debugOpenJourney` reaches only the first 20 journeys and the long drives on the
  owner's iPhone are older.
- **A saved place's marker** (Home) shows at the drive's end in the frame: with the privacy zone
  in W4b, a shared video shows no place mark.
- A test that waits on real time (`AtlasMapViewTests.testATapReleasesTheHoldAfterTheGrace`)
  failed once in four full runs; it is not part of this work.

Not in W4: highlights chips (R.2C), a 1:1 size, music, a 3D car model, web replay, the share card
image (its own slice in `share.md`; W4b's frame should be designed so the card can reuse it).

### Brief for the next session

```text
Outcome: W4a of the wow track (the renderer in the app), after the owner answers the six decisions.
Existing behaviour (files read): carodo-ios Core/Replay/{ReplayCameraRig,ReplayTimeline,CameraScript,
  ReplayRoute}.swift, Features/Journeys/Views/ReplayMapView.swift, ViewModels/ReplayPlayer.swift,
  Core/Domain/PrivacyZone.swift, docs/specs/{replay,share}.md; carodo-studio Studio/{Renderers,
  MapKitStage,MovieWriter}.swift.
Acceptance: per slice table above.
Non-goals: see "Not in W4".
Constraints: the rig and timeline unchanged; the map's dressing extracted from ReplayMapView, never
  copied; no coordinates in logs; no schema or API change.
Validation: task lint, task warnings, task test; device: iPhone 12 Pro Max, a 30 s and a 60 s clip
  of a real drive (the owner runs the signed build from Terminal).
Do not: rewrite FollowCamera or the player; put export in a release build before TD-2.
```
