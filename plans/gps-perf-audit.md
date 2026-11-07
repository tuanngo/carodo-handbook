# GPS / Always / Map — performance audit (2026-11-05)

Status: **owner review done 2026-11-05**. Fixed in code: A1, B3, B5, A2/A3, C2, D3–D5, **D6
removed** (no single state machine; lifecycle in `carodo-ios/docs/tracking.md`). Device check still
required for A1/B3/B5. Source of truth for thresholds remains `carodo-ios/docs/tracking.md`; this
file is findings + commentary for prioritising work.

Related: [`gps-engine.md`](gps-engine.md) §3 (battery proposals B1–B7 from 2026-11-04). Several of
those are done in code; this audit checks what still costs CPU, memory and battery **after** B1–B6.

Scope audited (code read + cross-check):

- `Carodo/Core/Location/` — `CoreLocationServices`, `LiveLocation`, `CompassHeading`, permission
- `Carodo/Core/Recording/` — `DriveSessionManager`, `LocationSource`, `RouteRecorder`, `LiveLine`,
  `TripWriter`, `RecordingGPS`
- `Carodo/Core/Tracking/` — modes, Auto Mode, stop detector, rules
- `Carodo/Core/Atlas/` + `Features/Map/` — live overlays, history, heat, camera follow
- Wiring: `DependencyContainer`, `MainTabView`

Not audited here: Instruments on a physical iPhone (Energy / Time Profiler), widget, CloudKit while
idle. Those remain “device check still required”.

---

## Verdict (one paragraph)

The hot path is already thoughtful in places that matter for a drive journal: standby without
continuous GPS, recording GPS adaptive accuracy (`RecordingGPS`), sample DB batching, a thinned
live map line (`LiveLine`), and history layers suppressed while a drive is live. The remaining
cost is less “bad Swift micro-opts” and more **architecture on the MainActor + Observation**:
every accepted fix can invalidate Map + panels, re-animate the follow camera, and briefly run
**two** location pipelines around session start / `preparing`. Fix those first; haversine SIMD
will not move the needle.

---

## What is already good

| Area | Why it is fine |
|---|---|
| Tracking modes | `.recording` clears detection GPS and standby services (`TrackingModePolicy.services`) |
| Sample persistence | `TripWriter` batches (default 10 / 15 s), write off main via `@concurrent` |
| Live route display | `LiveLine` keeps O(thinned) points (~250 m span / DP), not every raw fix |
| History while driving | `MapRenderingPolicy` + `layerRequest == nil` unless idle — no heat/footprint per GPS tick |
| Recording GPS rule | One pure table (`RecordingGPS.settings`): stop → 100 m + 50 m filter; charging → navigation; else Best |
| No `Task {}` per fix on recording ingest | Delegate → sync `ingest` (avoids task storms) |
| Auto-finish / mode tasks | Cancelled on reset / leave detecting |

---

## Findings

Effort: **S** small PR · **M** a focused slice · **L** multi-day / architecture.
Impact is about Always + Map + long drives, not microbenchmarks.

### A. Dual / overlapping location pipelines (battery)

#### A1. Map `liveUpdates` + recording GPS overlap in `.preparing`

| | |
|---|---|
| **Impact** | Battery / CPU — two continuous location sessions until the first accepted fix |
| **Effort** | S |
| **Confidence** | High |
| **Evidence** | `MapAtlasView.isRecordingFixes` is `session?.state == .recording` only. `.task(id: LiveSource…)` starts `LiveLocation.follow` / `CLLocationUpdate.liveUpdates()` when `!isRecordingFixes`. `DriveSessionManager.start` goes to `.preparing` and immediately `beginUpdates()` → `CoreLocationSource.startUpdatingLocation()`. |

**Comment.** The intent in the Map comments is right (“only when nothing records”), but the gate
uses `.recording`, so the whole `preparing` window still runs both. Fix: gate on
`state == .preparing || state == .recording` — **not** `isActive`: `isActive` includes `.paused`,
where `pause()` stops the recording source, so the dot would freeze for the whole pause.
Trade-off: in `.preparing` the marker moves only on the first **accepted** fix; until then it
stays at the last live / last known coordinate. Small, high leverage.

#### A2. Detection GPS + recording GPS handoff at Auto Mode start

| | |
|---|---|
| **Impact** | ~~Battery~~ **Negligible** (second pass) — overlap is microseconds |
| **Effort** | S |
| **Confidence** | High that it is not a battery cost |
| **Evidence** | `AutoModeCoordinator.startDrive` calls `session.start` (starts `CoreLocationSource`) then `refreshMode()`. Detection uses a separate manager (`CoreLocationServices.detector`). Recording mode clears services only after `TrackingModeController.update`. |

**Comment.** Two managers are intentional (comments in `CoreLocationServices`: background detection
vs significant-change manager must not share settings).

**Second pass:** there is no “mode refresh tick”. `startDrive` calls `session.start` and then
`refreshMode()` in the same call stack; `TrackingModeController.update` → `apply()` →
`stopDetectionGPS()` is synchronous. Both managers run for a few instructions of one main-actor
turn. Swapping the order is tidiness only — not a group 1 item.

#### A3. Manual start while detecting: teardown is async via SwiftUI

| | |
|---|---|
| **Impact** | ~~Battery~~ **Low** (second pass) — milliseconds, foreground only |
| **Effort** | S |
| **Confidence** | High |
| **Evidence** | `MainTabView` starts the session; detection teardown is `.onChange(of: session.isActive)` → `updateTrackingMode`, not synchronous inside `start`. Auto Mode path does call `refreshMode()` immediately. |

**Comment.** Mode ownership should not depend on a view observing `isActive`. Prefer the
composition root / session start notifying the mode controller, so manual and Auto share one
handoff.

**Second pass:** every manual start is in the foreground (the Start Drive intent has
`openAppWhenRun = true`), so `onChange` runs on the next SwiftUI update — a window of
milliseconds, not seconds. The architecture point stands; the battery claim does not.

#### A4. Inventory of location clients (by design, cost adds up when concurrent)

| Client | Role |
|---|---|
| `LocationPermissionManager.manager` | Auth only (idle) |
| `CoreLocationServices.manager` | Significant changes + regions |
| `CoreLocationServices.detector` | Detection continuous GPS |
| `CoreLocationSource.manager` | Recording continuous GPS |
| `CompassHeading.manager` | Heading when follow = heading |
| `LiveLocation` / `CLLocationUpdate.liveUpdates()` | Map marker when not recording |

**Comment.** Do not merge everything into one `CLLocationManager` without a strong reason — iOS
settings on one manager fight each other (seen already: detection vs significant change). The
policy to enforce is: **at most one continuous GPS owner at a time**, plus idle geofences /
significant changes.

---

### B. Main-actor + Observation churn (CPU / UI)

#### B1. Entire ingest / filter / UI publish path is MainActor

| | |
|---|---|
| **Impact** | CPU — ~1 Hz (or bursts) compete with UI for the whole drive |
| **Effort** | L |
| **Confidence** | High |
| **Evidence** | App default actor isolation is MainActor (`project.yml`). `LocationSource` handler is `@MainActor`. `DriveSessionManager.ingest` runs `StopDetector`, `RouteRecorder`, `liveLine`, `writer?.record`, `applyGPS`, `checkAutoFinish` on that actor. Detection samples are MainActor too. |

**Comment.** Correct for a simple single-owner model; wrong if MapKit + SwiftUI are heavy on the
same actor. A pragmatic middle path (not a full actor rewrite): keep ingest on main for now, but
**stop publishing Observation-tracked fields every fix** (see B2–B4). Moving filter off main is
L and must keep cancellation / session lifecycle correct — do after the cheap wins.

#### B2. `@Observable` session mutates per accepted fix → Map + panels invalidate

| | |
|---|---|
| **Impact** | CPU — Map content builder + recording chrome at GPS rate |
| **Effort** | M |
| **Confidence** | High |
| **Evidence** | `DriveSessionManager` is `@Observable`. Each accept sets `lastFix`, mutates `liveLine`, mutates recorder/metrics. `MapAtlasView` reads `session?.lastFix`, `liveLine.segments`, mode/phase. `RecordingPanels` reads `session.metrics.*`. |

**Comment.** Observation is doing its job — that is the problem on a 1 Hz stream. Options: (1)
throttle UI publish (e.g. lastFix for camera at most ~2–3 Hz; metrics on a 1 s timer already used
in places); (2) split a non-`@Observable` recording core from a thin UI façade that samples it;
(3) map-only: drive camera/`liveLine` through local `@State` updated on a throttle, not by observing
the whole session.

#### B3. Follow camera re-animated on every fix (and compass tick)

| | |
|---|---|
| **Impact** | CPU / GPU / battery while Map is following |
| **Effort** | S |
| **Confidence** | High |
| **Evidence** | `onChange(of: session?.lastFix)` → `show` → `applyFollowCamera(duration: 0.8)` with `withAnimation(.easeInOut)`. Compass stream can call it again at 0.3 s. Spec notes the view drives the camera itself (`docs/specs/navigation.md`). |

**Second pass:** at ~1 Hz a 0.8 s animation mostly finishes before the next fix, so “overlap” is
rare; the real defect is **ease-in-out per fix**, which makes the camera stop and start every
second. The compass re-animates only while `course == nil` (stopped / slow) and the heading filter
is 4°, so it does not fight the fix-driven camera while driving. CPU win is unproven without
Instruments; the feel win is clear.

**Comment.** Overlapping 0.8 s animations at ~1 Hz is thrash, not smooth follow. Prefer: update
`position` without a long ease, or only animate when heading/mode changes; while driving, set
camera directly (or very short duration). This is the best S-size CPU win on the Map.

#### B4. ~~Continuous camera heading → `@Observable` marker → full Map body~~ — withdrawn

| | |
|---|---|
| **Impact** | CPU during pan / tilt / follow |
| **Effort** | M |
| **Confidence** | High |
| **Evidence** | `.onMapCameraChange(frequency: .continuous)` writes `markerHeading.map` when heading moves > 0.5°. `MarkerHeading` is `@Observable` in `@State`, so `MapAtlasView.body` re-runs — including history or live polylines, not only the annotation. |

**Comment.** Marker heading should not invalidate the whole `Map { … }` content. Isolate the
annotation (child view that owns heading) or write heading without triggering parent Observation
of the route layers.

**Second pass — wrong, withdrawn.** Observation tracks only properties *read during* a body. The
`MapAtlasView` body passes the `markerHeading` reference down and reads none of its properties;
`.map` is written from the camera-change closure. Only `DriveLocationMarker` /
`UserLocationMarker` read `heading.facing`, `.map`, `.travelAngle`, so only the marker
re-renders. The isolation the comment asks for is already there.

#### B5. `LiveLine.segments` allocates on every body read; dual `MapPolyline` per segment

| | |
|---|---|
| **Impact** | Alloc / CPU while live route shown |
| **Effort** | S–M |
| **Confidence** | High |
| **Evidence** | `LiveLine.segments` maps runs to new `[CLLocationCoordinate2D]` arrays every access. Map draws ivory casing + copper stroke per segment. Comment in Map says thinning avoids redrawing every fix — thinning helps vertex count, not Observation invalidation or allocation-on-read. |

**Comment.** Cache `segments` as a stored property updated only when `append` / `breakSegment`
actually changes kept geometry (tip-only updates can patch the last coordinate). Dual stroke is a
design choice; keep it if the look matters, but avoid rebuilding both arrays when only the tip
moved.

#### B6. Barometer callbacks on `.main` for the whole recording

| | |
|---|---|
| **Impact** | CPU light — extra main-queue callbacks; pressure only stamped on accept |
| **Effort** | S |
| **Confidence** | Medium–High |
| **Evidence** | `CMAltimeter.startRelativeAltitudeUpdates(to: .main)`. Started whenever `driveSession.isActive`. |

**Comment.** Prefer a background queue and only hop to main when storing the latest kPa, or keep
the value in a non-observed box that ingest reads. Low priority vs A1 / B3.

---

### C. Memory during long drives and large journals

#### C1. Full raw route in RAM for the live session

| | |
|---|---|
| **Impact** | Memory — hours × ~1 Hz `RoutePoint`s until finish |
| **Effort** | M |
| **Confidence** | High |
| **Evidence** | `DriveMetrics.route.append` every accept; finish runs `JourneyAnalysis.stopBands` and `RouteSimplifier` over it on the session actor. |

**Comment.** Intentional for summary/finish and matches ADR “exact samples kept”. Not a bug. If
multi-hour drives matter, spill or recompute stop bands from packed track / DB at finish (`@concurrent`)
instead of holding the full array for UI. UI should never need the full raw route — only `LiveLine`
+ scalar metrics.

#### C2. `TripWriter` `AsyncStream` unbounded (no backpressure)

| | |
|---|---|
| **Impact** | Memory if SQLite lags (background, contention) |
| **Effort** | M |
| **Confidence** | High |
| **Evidence** | `AsyncStream.makeStream(of: Operation.self)` with default buffering; `yield` never awaits. Consumer is a long-lived `Task`. Batching of samples is good; the **queue of batches** is not bounded. |

**Comment.** Production path is usually fine. Log (without coordinates) when the queue depth is
high, and if needed coalesce pending `.append` batches.

**Second pass:** do **not** bound with `.bufferingOldest(N)` / `.bufferingNewest(N)` — a full
buffer drops operations, i.e. accepted samples, which breaks iOS invariant 4 (“every accepted fix
is kept”) and could drop a `.complete`. Growth is the lesser evil; measure depth first.

#### C3. `HistoryAtlas` holds all journal display coordinates for the process lifetime

| | |
|---|---|
| **Impact** | Memory at scale (docs cite ~500k points / ~8 MB for 2k synthetic drives) |
| **Effort** | L |
| **Confidence** | High |
| **Evidence** | `HistoryAtlas.entries[*].near`; viewport culls **drawing**, not the store. |

**Comment.** Acceptable for early journals; plan eviction / region paging before multi-year use.
Not a GPS-engine bug — Map atlas capacity.

#### C4. Heatmap duplicates route coordinates again

| | |
|---|---|
| **Impact** | First-show CPU (~2.2 s documented for 2k drives); ~~memory doubling~~ |
| **Effort** | M |
| **Confidence** | High for CPU; memory claim withdrawn |
| **Evidence** | `RouteHeatIndex.add` keeps `route` in `Stored`; `HistoryAtlas` passes `entry.near` / `route.coordinates`. |

**Comment.** ~~Share storage with atlas entries~~ **Second pass:** the stored route is the same
array value as `Entry.near`; Swift arrays are copy-on-write and nothing mutates it, so the buffer
is shared, not doubled. Heat's own memory is `cells` / `counts` / `crossing`. Only the first-show
CPU remains.

#### C5. Full `routes()` decode on every journal reload after a drive

| | |
|---|---|
| **Impact** | CPU / peak memory when Map returns to idle |
| **Effort** | M |
| **Confidence** | High |
| **Evidence** | Idle + `journalRevision` reloads decode every `route_simplified` into full `RoutePoint`s then takes `.coordinate`. Atlas `replace` is incremental by version, but the load path pays full decode. |

**Comment.** Decode only changed journeys, or a coordinate-only blob for the atlas. Deferred
correctly during recording — pain hits at finish. **Second pass:** the decode runs inside
`database.read` (off the main actor), so it is peak memory + background CPU, not a UI hitch.

---

### D. Redundant work / organization (not always runtime cost)

#### D1. Two stop/accuracy pipelines per fix while auto-finish is on

| | |
|---|---|
| **Impact** | CPU small; cognitive cost large |
| **Effort** | M |
| **Confidence** | High |
| **Evidence** | Every ingest: `stopDetector?.ingest` then `recorder.ingest`. Both reject on accuracy; separate hysteresis (`StopDetector.Configuration` vs `RouteRecorder.Configuration`). Documented as different roles in `tracking.md`. |

**Comment.** Keep two roles if product needs them (auto-finish vs distance/stop-anchor), but share
the accuracy gate and one “stopped?” signal so thresholds cannot drift silently. Not the first
perf fix.

#### D2. `applyGPS()` on every fix

| | |
|---|---|
| **Impact** | Usually tiny; battery if conditions thrash and `configure` flips accuracy |
| **Effort** | S |
| **Confidence** | High |
| **Evidence** | Public `ingest` always calls `applyGPS()` when active; `guard wanted != gps` skips configure. Docs say “on every fix”. |

**Comment.** Cheap today. Optional: only recompute when power / vehicle / stoppedSince edge changes.
Low priority.

#### D3. Docs say every threshold lives in `TrackingRules` — several do not

| Outside `TrackingRules` | Where |
|---|---|
| `WakeQuieting.Configuration` | `TrackingMode.swift` |
| `GPSSignal` windows (15 s / 10 m / 30 m) | `RouteRecorder` / session signal |
| `LiveLine.maxSpanM` / tolerance | `LiveLine.swift` (tolerance ties to `RouteSimplifier`) |
| Auto-finish poll 20 s | `DriveSessionManager` |
| `GapHealing` gap/detour constants | `GapHealing.swift` (only `LeadIn` is on rules) |

**Comment.** Docs and Developer → Thresholds become a lie when knobs live elsewhere. Either move
them into `TrackingRules` or amend `tracking.md` to list the exceptions explicitly. Tuning risk >
runtime risk.

#### D4. Duplicated `70 m/s` implausible cap

| | |
|---|---|
| **Evidence** | `RouteRecorder.Configuration.maxPlausibleSpeedMps` and `PassportGeometry.implausibleSpeedMps` (in `PassportExploration.swift`) |

**Comment.** Same literal, two types — will diverge. One shared constant (or rules field).

#### D5. Parking radius from `TrackingRules.production`, not the container’s `rules`

| | |
|---|---|
| **Evidence** | `CoreLocationServices(parkingRadiusM: TrackingRules.production.autoMode.parkingRadiusM)` while the session gets `rules.session` from the container. |

**Comment.** Test / override rules desync geofence vs session. Wire from the same `rules` instance.
**Second pass:** the live factory never passes `rules`, so both are `.production` today — a latent
trap, not a live desync. Low.

#### D6. `TrackingStateMachine` pure + tested but not wired — **removed 2026-11-05**

| | |
|---|---|
| **Evidence** | Was documented as unwired; live path was already `AutoModeCoordinator` + `StopDetector` + `DriveSessionManager`. |

**Decision.** Do not wire and do not merge into one enum: iOS services (`TrackingMode`) ≠ trip
session ≠ auto-finish. Deleted the type, its tests, and `AppState.trackingState`. Lifecycle is
documented in `carodo-ios/docs/tracking.md` (Lifecycle — three owners).

---

### E. Map atlas extras (when idle / after drives)

| ID | Finding | Impact | Effort |
|---|---|---|---|
| E1 | Initial `layerRequest` can use full journal `shownBounds` before camera settles → one global history request then a second | First-paint hitch | S |
| E2 | Footprint `tile.corners` rebuilt every SwiftUI pass (up to 1,500 tiles × 4 points) | CPU when footprint on | S |
| E3 | LOD re-simplifies already DP-simplified routes (8 m → 30 / 150 m) and caches copies | CPU + retained arrays | M |

**Comment.** Not on the live GPS tick path (history off while recording). Worth a Map polish slice
after A/B.

---

## Priority for the owner (suggested)

Best leverage first — measure battery %/hour and Instruments before/after where noted.

| Order | IDs | Why |
|---|---|---|
| 1 | **A1, B3** | The one real dual-GPS window (`preparing`) + stop-and-go follow camera. |
| 2 | **B5, B2** | Cache `LiveLine.segments`; then measure whether per-fix Map body is still hot. |
| 3 | **C2 (depth log, no drop), C1 (finish off main)** | Writer visibility; don’t spike main at end of long drives. |
| 4 | **A2, A3, D3, D5, D4** (D6 removed) | Mode ownership in one place; single source of truth for thresholds. |
| 5 | **C3, C4, C5, E\*** | Scale the Map journal; not urgent until the journal is large. |
| 6 | **B1 (full off-main ingest)** | Only if 1–2 still leave the main thread hot in Instruments. |

Not proposed (same as gps-engine.md §3): `pausesLocationUpdatesAutomatically = true`; a distance
filter while moving (hurts jump filter / replay for little gain at 1 Hz).

---

## Review — second pass (2026-11-05)

Each finding re-checked against the code.

| ID | Verdict | Note |
|---|---|---|
| A1 | **Confirmed**, fix amended | Gate `.preparing \|\| .recording`, not `isActive` (pause stops the source) |
| A2 | **Overstated** | Synchronous handoff in one call stack; microseconds |
| A3 | **Overstated** | Foreground only; milliseconds. Architecture point stands |
| A4 | Confirmed | — |
| B1 | Confirmed | — |
| B2 | Confirmed | Body reads `liveLine.segments`, `state`, `isPending`, `onChange(lastFix)` |
| B3 | Confirmed, reframed | Ease-in-out stop-and-go per fix; compass only when `course == nil` |
| B4 | **Wrong — withdrawn** | Parent body reads no `markerHeading` property |
| B5 | Confirmed | `segments` rebuilt on every read |
| B6 | Confirmed | Low |
| C1 | Confirmed | `stopBands` + `Journey.make` on main at finish |
| C2 | Confirmed, fix amended | Never drop: invariant 4 |
| C3 | Confirmed | — |
| C4 | **Memory claim wrong** | CoW shares `Entry.near`; first-show CPU stands |
| C5 | Confirmed, softened | Decode is off main |
| D1–D3 | Confirmed | `GapHealing` has `static let` constants outside rules |
| D6 | **Removed** | Owner: do not wire; delete + document three-owner lifecycle |
| D4 | Confirmed | File is `PassportExploration.swift` |
| D5 | Latent | Both `.production` today |
| E1–E3 | Plausible / confirmed | E2 cheap in practice: body rarely re-runs when idle |

---

## Swift / concurrency notes (for review)

- Target is Swift 6 + default MainActor — hot path being MainActor is **consistent**, not accidental.
- Prefer structured cancellation (already mostly good) over more `Task {}` on the fix path.
- Unbounded `AsyncStream` on `TripWriter` is the main concurrency footgun for memory under load —
  but bounding it by dropping is worse (invariant 4).
- `@preconcurrency CLLocationManagerDelegate` is fine; do not “fix” by adding `@unchecked Sendable`.
- Barometer / battery Observation re-arm via `Task { @MainActor in … }` is OK at session edges, not
  per fix.

---

## Device checks still required

After any fix in group 1–2:

- [ ] Always + Auto Mode: wake → detect → record — confirm logs show no overlapping continuous GPS
      (one `startUpdatingLocation` owner).
- [ ] Manual start during detecting: same.
- [ ] Map follow during a 30+ min drive: Energy Log / battery %/hour vs build before.
- [ ] Preparing → first fix: Map marker still updates (A1 must not blank the dot).
- [ ] Background recording with lowered GPS at a stop (B1): app stays alive; first fix on leave OK.

---

## Changelog

| Date | Note |
|---|---|
| 2026-11-05 | Initial audit (code review; no Instruments). |
| 2026-11-05 | Second pass: B4 withdrawn, C4 memory claim withdrawn, A2/A3 downgraded, A1 and C2 fixes amended, priorities reordered. |
| 2026-11-05 | A1 (gate `.preparing \|\| .recording`), B3 (linear glide over the fix interval, 0.2–1.2 s), B5 (`LiveLine.segments` kept incrementally) implemented; tests in `LiveLineTests`, `MapExperienceTests`. |
| 2026-11-05 | A2/A3: `DriveSessionManager.onActiveChange` (fired from `state`'s `didSet`, before `beginUpdates`) moves the tracking mode in the composition root; `MainTabView` no longer does. C2: `TripWriter.queuedCount`, a `writeBacklog` log entry at 30 queued operations (once until half drained), nothing dropped. D3: `tracking.md` lists the thresholds outside `TrackingRules`. D4: `LocationSample.implausibleSpeedMps`. D5: one `rules` instance in `DependencyContainer.live`. |
| 2026-11-05 | D6: removed `TrackingStateMachine` + tests + `AppState.trackingState`; lifecycle section in `tracking.md`; comments on mode / session / Auto Mode coordinator. |
