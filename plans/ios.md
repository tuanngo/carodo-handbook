# iOS plan

The one place for the iOS plan and its status. The cross-track phases are in
[`../product/roadmap.md`](../product/roadmap.md); what the code does right now
is in [`architecture.md`](../../carodo-ios/docs/architecture.md#what-is-wired-today). Update the status here in the
same change that moves a slice forward.

Status: `Done` · `Done in code` (device check pending) · `In progress` · `Next` · `Later`.

## Phase 1 — UI first (on sample data)

| Slice | Content | Proven on | Status |
|---|---|---|---|
| **A** | Dark surfaces, floating bar and Start Drive states, Map home, Journeys with summary, Feed and leaderboard, Profile/Garage sheet, Start panel shell, onboarding | Simulator | Done |

Still open in phase 1: responsive check on every iPhone size and the largest Dynamic Type sizes;
the `Theme` clean-up (`carodo-ios/docs/design-system.md`, Known gaps).

## Phase 2 — GPS engine

Exit criteria: [`device-testing.md`](../../carodo-ios/docs/operations/device-testing.md#exit-criteria-for-the-gps-engine-roadmap-phase-2).

| Slice | Content | Proven on | Status |
|---|---|---|---|
| **B** | `DriveSessionManager` + tests; Start, compact and expanded panels on real foreground GPS (When In Use); undo, hold-to-finish, short-drive rule | Simulator + iPhone | Done in code; iPhone drive pending |
| **C** | Schema additions (`vehicles`, `trips.vehicle_id`, sync columns, recovery state: `data-model.md`); GRDB `JourneyRepository` / `VehicleRepository` replacing the sample ones; batched sample writes while recording; Journey Summary after persist; recovery of an unfinished trip at launch; installation identity created at first launch | iPhone | Done in code (iPhone drive pending): schema, `GRDBVehicleRepository` + Garage, `GRDBJourneyRepository`, batched sample writes (`TripWriter`), launch recovery (`TripRecovery`, proven on the Simulator by terminating mid-drive), onboarding's first car in `vehicles`, installation id at first launch. Journey Summary opens after the write is confirmed (Retry on failure) |
| **D** | Always permission UX; background recording; Auto Mode wake strategy (parking geofence, significant changes, motion check; `tracking.md`); Auto Mode wired (`DrivingDetectionEngine` → `DriveSessionManager.start(trigger: .auto)`) with stop hysteresis and stop grace; `carodo://trip/start` deep link and the CarPlay Shortcuts automation | iPhone + car | Later |

Before D: `UIBackgroundModes: location` reviewed against invariant 7 (2026-11-02): permission UX,
persistence and launch recovery exist, so background recording is on, and only while a drive records.

Slice D progress (in code, device check pending):
- **D1 done:** Auto Mode explainer before the Always prompt (Settings toggle and Start panel go
  through it; Auto Mode is remembered and turns itself off if Always is taken away); a
  `CLBackgroundActivitySession` keeps a recording drive going in the background.
- **D2 done:** `carodo://trip/start` (from any launch state) and the Start Drive App Intent for
  Shortcuts and automations, both idempotent, last-used vehicle.
- **Reliability first** (owner's order, 2026-11-02, after reading OwnTracks iOS, MIT):
  1. **Tracking status: done.** `TrackingHealth` and the tracking log, Settings → Tracking status.
  2. **Background flush and recovery: done in code** (device check pending). Waiting samples are
     written on leaving the foreground inside `BackgroundWork` (ends once, on finish or expiry);
     a batch is also written when 15 s old; recovery skips the live trip (a launch-time race found
     on the Simulator: a drive started by a link before recovery was discarded as short). Proven on
     the Simulator: drive, background, terminate, relaunch, every sequence recovered.
  3. **Standby vs recording modes: done in code** (device check pending). `TrackingModeController`
     + `CoreLocationServices`; proven on the Simulator in the background (wake by significant
     change, 120 s detection window, back to standby, no re-wake). Found on the way: CLMonitor names
     must be alphanumeric (crash); the permission status arrives after launch (now a callback);
     a `liveUpdates` session started in the background is suspended (detection uses standard
     updates); significant changes inside the parking circle re-woke the app (now ignored).
     D3 must start the recording session from the background with standard updates too.
  4. **Outbox before network: done in code.** Table `outbox` (renamed from `backend_outbox`;
     Transactional Outbox: `OutboxOperation`, `OutboxStore`, `OutboxRelay`, `OutboxTransport`).
     Only publish, unpublish and revoke go through it; creating a share link, claiming a username
     and account deletion stay direct. Tests: classification, coalescing, same-transaction commit,
     surviving termination (file database reopened), retry with backoff, rejected drop, no double
     send. Found on the way: actor reentrancy let two drains send twice (now one drain at a time),
     and strict FIFO let one stuck message block all (messages are independent now). Wiring
     (enqueue on publish/delete, real transport, drain triggers) comes with `BackendService`.
- **D3: done in code** (device drives pending). `StopDetector` (stop 3 km/h for 30 s, resume
  12 km/h, grace 5 min ending at the stop, 12 min no-signal), auto-finish for every drive (default
  on; Start panel setting still to build), `AutoModeCoordinator` (detection → session from the
  background, seeded with the confirming fixes → auto-finish → standby), motion "on foot" closes a
  detection early, recording source moved to standard `CLLocationManager` updates. Simulator, app
  in the background throughout: wake → auto start → 150 fixes → no-signal finish → standby.
  The shorter grace after a CarPlay/Bluetooth disconnect is done in code (2026-11-03, 90 s while
  stopped, `auto-mode.md`). Left for later: trimming parked GPS jitter from the distance, the auto-finish toggle in the Start panel, the parking spot as start
  place (owner decision).

## Next session: first run

The brief for onboarding → first drive (mockups, then code) is [`first-run.md`](first-run.md).

| Slice (2026-11-03) | Status |
|---|---|
| Mockups: Day 0 (rev. 3), Day 1, Auto Mode sheet | Done (`design/mockups/`) |
| Your first car: name, Car / Motorbike tiles, colour; the wheel steps aside for the keyboard; units to Settings (Automatic) | Done in code |
| Vehicle looks in the schema (`body_style`, `color`, `fuel_type`), `VehicleArt`, the compact `VehicleCard` | Done in code |
| Map: standing Auto Mode button, the status line, "No drives yet"; the Map never asks for location | Done in code |
| Start panel: vehicle card with Change / Add, readiness, mode, one-tap hint; No vehicle as a choice | Done in code |
| Auto Mode sheet, car-audio links (`vehicle_links`), linked vehicle on every start, 90 s grace on disconnect, Shortcuts steps (iOS 26) and one-tap "Carodo CarPlay" (iOS 27), localised Start Drive intent | Done in code, device checks pending |
| First drive saved: "First drive" mark; the detail reads well before place names (template sentence, part-of-day title) | Done in code |
| Garage carousel (cards, 12-week bars, odometer as entered) and the Looks form with fuel | Done in code |
| Elevation card and sheet (3 m noise level, barometer), per-fix accuracies and pressure (`TrackCodec` v2), tuning logs | Done in code |
| Motorbike device test (2026-11-04 morning), then tune the stop thresholds from its data | Next |
| Recording polish: start source and end reason on every drive, the stop countdown, the Map while recording, after an automatic end, dropped short drives ([`recording-polish.md`](recording-polish.md)) | Next (owner decisions first) |
| GPS engine: field test on three iPhones, open work, battery and performance proposals (B1–B7), lessons from OwnTracks and Traccar ([`gps-engine.md`](gps-engine.md)) | Field test first (2026-11-04) |
| Vietnamese copy review (owner) | Next |

## Phase 3 — Journal and 2D replay

| Item | Spec | Status |
|---|---|---|
| Journeys and journey detail on real data; delete and edit | `carodo-ios/docs/specs/journeys.md` | Later |
| 2D replay (speed-coloured route, timeline scrub, overlay) | `carodo-ios/docs/specs/replay.md` | Later |
| Route simplification with per-point `t` and `speedMps` (ready for sync) | `carodo-ios/docs/sync.md` | Later |
| Developer mode: live GPS, full log, export database (AirDrop) and GPX, re-derive, map overlay, read-only thresholds; DEBUG and TestFlight only | `carodo-ios/docs/specs/developer-mode.md` | Slice 1 done in code 2026-11-03 (entry, Live, Battery + MetricKit, log, export, thresholds); rejected fixes, GPX, re-derive, overlay, QA switches next |
| Stop and wait: join drives split by a wait in the car (≤ 20 min, same spot and vehicle, no walking), non-destructive on `merged_into_trip_id`; tests both sides; device check with a real wait | `carodo-ios/docs/tracking.md` (Stop and wait) | Done in code 2026-11-03, Split here included (timeline stop row and replay compression still to do; device check pending) |
| Places 1: `places` (the geocoding cache renamed `geocoded_cells`) in `v1_initial` and its repository; the pure frequent-place detector (thresholds, role guess, neighbours, dismissals) with tests | `carodo-ios/docs/specs/places.md` | Done in code (2026-11-03) |
| Places 2: Places screen (list, add from a pin or a drive end, edit on a map); suggestion card; titles and commute grouping from places | `carodo-ios/docs/specs/places.md` | Later |
| Places 3: private regions hidden anywhere along a shared route, with the fixed offset; "Route hidden: private place" (lands with the share card, phase 4) | `carodo-ios/docs/specs/places.md` | Later |

## Phase 4 — Share, sync and Feed live

| Item | Spec | Status |
|---|---|---|
| Share card (offline, privacy trim) | `carodo-ios/docs/specs/share.md` | Later |
| Username claim (Join the Feed), account secret in iCloud Keychain, App Attest; Secure your profile (Apple) | `carodo-ios/docs/specs/account.md` | Later |
| `CloudSyncService`: iCloud backup and sync of vehicles and trips (`CKSyncEngine`) | `carodo-ios/docs/sync.md` | Later |
| `BackendService` + outbox: publish, share upload, account; tested with a fake HTTP client | `carodo-ios/docs/sync.md` | Later |
| Share link create / revoke | `carodo-ios/docs/specs/share.md` | Later |
| Feed, leaderboard and live status on real data; publishing opt-in; report/block | `carodo-ios/docs/specs/feed.md` | Later |
| Profile and Follow (first slice on sample data: your own and other drivers' Profiles, Follow, leaderboard rows open a Profile); still to do: Report / Block, paging, blocked states, Join the Feed for a guest | `carodo-ios/docs/specs/profile.md` | Done in code (sample) |
| Leaderboard: Week · Month · Year with ‹ › (asked by `start`, the reader's own Monday / 1st), Distance and (month, year) Active days, podium for the top three, ▲▼ against the period before, your pinned row with the gap to the next rank | `carodo-ios/docs/specs/feed.md` | Done in code (sample) |
| **Badges 1 — art first.** Sketch the whole stamp set before any code: the round stamp (A) and the visa stamp (B) for every badge of the first catalogue, each at tier 1, a middle tier and the top tier (rings, tier numeral, ink density, copper foil), light and dark, at 20 pt, card size and full size; then a SceneKit prototype of the 3D stamp: a rubber die built from a heightfield of the same drawing (mirrored), on a handle, turned with a finger, pressed down to ink an impression on a page with a haptic thump; Reduce Motion rests. Proven at 60 fps on the oldest supported iPhone. Sketches in `design/passport-stamp/`, the chosen art into `design/brand/source/` | [`../drafts/achievements.md`](../drafts/achievements.md), carodo-ios ADR 0013 | Next |
| **Badges 2 — earned on the device.** The metrics as pure functions with tests on both sides of every threshold; the bundled catalogue; `earned_badges` in `v1_initial` (schema approval, P6); the Passport's stamp page (inked impressions, next ones in pencil with progress); the celebration after the drive (the stamp coming down), never while recording; the Passport dot | [`../drafts/achievements.md`](../drafts/achievements.md) | Later |
| **Badges 3 — on the Feed.** The served catalogue (`GET /v1/badges/catalogue`, ETag, newer wins, unknown metrics ignored); publishing a Feed-visible badge (`PUT /v1/me/badges/{badgeId}`) through the outbox; badge items on the Feed and the Profile as flat impressions; points and the level | [`../drafts/achievements.md`](../drafts/achievements.md), carodo-ios `docs/specs/feed.md` | Later |
| Privacy copy and App Store privacy label | [`privacy.md`](../../carodo-ios/docs/privacy.md) | Later |

## Release tooling (before the first TestFlight build)

| Item | Notes | Status |
|---|---|---|
| Version and build number | `MARKETING_VERSION` stays in `project.yml`; the build number is derived (e.g. `git rev-list --count HEAD`), never kept in a per-machine file, so two machines never upload the same number | Later |
| `task archive` + `task testflight` | `xcodebuild archive` and `-exportArchive` with `ExportOptions.plist`, upload with an App Store Connect API key: key ID and issuer ID in `.env`, the `.p8` outside the repo (`~/.appstoreconnect/private_keys/`; `*.p8` is gitignored) | Later |
| Privacy Report from the archive | Organizer → **Generate Privacy Report** on the archive: the app's `PrivacyInfo.xcprivacy` and GRDB's both listed, and they match the App Store privacy label (`carodo-ios/docs/privacy.md`, Before release). An undeclared required-reason API fails the upload (ITMS-91053) | Later |
| `task screenshots` | Capture App Store screenshots straight from a 6.9" simulator (`xcrun simctl io <SIM_ID> screenshot`) with sample data and the QA launch arguments, at the required size: no resizing or padding | Later |

Considered from an iOS template and not taken: generating icon sizes (one 1024 icon is enough; ours
come from the brand source) and resizing screenshots with white padding.

## Release scope (decide before the first TestFlight build)

Found by a pre-release review on 2026-11-07. Each is a risk at App Review (incomplete or
misleading features, App Review Guidelines 2.1 and 2.3), not a crash.

| Item | Today | Options | Status |
|---|---|---|---|
| **Feed in v1** (owner's product decision) | Release builds show sample data: `DependencyContainer.live()` never passes a community repository, so the default `SampleCommunityRepository` is used; Join the Feed only says it is not open yet | (a) hide the Feed tab, Profile and leaderboard in Release until the backend is wired (DEBUG and QA keep them); (b) finish identity and publishing ([`ios-backend-integration.md`](ios-backend-integration.md)) before the first release. Never ship sample people as if real | Open: owner decides |
| **Widget status** | `CarodoStatusWidget` always says "Ready to drive": it reads neither the Location permission nor the recording state, and its timeline is `.never` | (a) a real state: the app writes a small status (permission, recording, Auto Mode) where the extension can read it and calls `WidgetCenter.reloadTimelines` when it changes; an App Group is an entitlement (P6) and the widget spec follows; (b) narrow the widget to a Start Drive shortcut that claims no state; (c) leave it out of v1 | Open |

## Phase 5 — Next

3D flyover replay, then video export (map technology choice as an ADR first:
`carodo-handbook/references/repos/ios.md`).

## Unscheduled

Candidates with no slice yet, mostly from the CarStack study: [`backlog.md`](backlog.md).

- Live Activity for a recording drive (`CarodoWidgets` has only the bundle).
- Export and delete-all (required before public release, `privacy.md`).
- Tracking-quality diagnostics screen for development builds.
