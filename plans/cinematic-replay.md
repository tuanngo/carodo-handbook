# Cinematic Journey Replay (V2.3R)

Agreed with the owner on 2026-11-08: Replay comes before Journey Enrichment. Three phases, each
landing in `carodo-ios/docs/specs/replay.md` when built; this file keeps the order, the slices, the
state and what is still open. Map technology is already decided: `MKMapView` (carodo-ios ADR 0015,
"Cinematic 3D Route Replay will draw on MKMapView too").

| Phase | Scope | State |
|---|---|---|
| **R.1** Cinematic Route Replay | Full-screen replay from Journey Detail: the recorded route, the Carodo wheel moving on recorded time, one Follow camera in 3D pitch, the speed-profile timeline, play / pause / seek / rate, live distance and speed | R.1a timeline done 2026-11-08; R.1b next |
| **R.2** Camera & Terrain | The Cinematic Director: Follow, Reveal and Highlight shots scheduled on the timeline before playback; opening, descent and closing beats; speed-led height; realistic elevation, satellite / hybrid; speed-coloured driven line | Draft in `replay.md` (R.2) |
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
