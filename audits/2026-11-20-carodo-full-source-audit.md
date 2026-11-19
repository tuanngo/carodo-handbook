# 2026-11-20 full source audit (carodo-ios + carodo-app)

Read-only audit of the whole workspace, asked by the owner on 2026-11-19: vulnerabilities, optimisation,
clean code, duplication and UI inconsistency. Seven auditors ran in parallel, one slice each; their reports
are kept whole in the appendices (A1–A7). carodo-ios at `5772921` (plus another session's uncommitted
config/entitlement changes, read but not judged); carodo-app at its `main`. Items already tracked in
`plans/technical-debt.md`, `plans/backend-source-audit.md` and the earlier audits were left out and are
only cited by id. Nothing was edited, built on a device or run on a simulator: every finding is from
reading the code ("Confirmed" = the code path is certain; "Plausible" = depends on data or OS behaviour
not checked). The only High (TRK-1) was re-checked by hand against `DriveSessionManager.resume()`.

State: **group 1 fixed** in carodo-ios `5aae671` (owner approved 2026-11-20): TRK-1, TRK-2, TRK-10,
XC-11, UIA-1, UIB-1 (avatar routing; the Join sheet's load failure still shows the claim step's own
error), DOM-1, DOM-2 (no test: `storyShares` is private), XC-1 (photo tile only; the other date sites
listed under XC-1 are open), DOM-9 (`coordinate`), UIA-6, DAT-8. Left on purpose: TRK-8 (clearing
`vehicleID` in `reset()` changes what idle panels read, no bug today), XC-10 (`VehicleIdentityPresentation`
is a documented reservation in `docs/design-system.md`; `LocalCache.maximumAgeS` is the hook DOM-8's fix
needs). Device check pending: TRK-1 (pause > 5 min at a stop, Resume, drive on / stay parked).
**Group 2 fixed** in carodo-ios `8f4fef9` (owner approved 2026-11-20): UIA-2 (Explore reloads in place,
the loaded pages read again; only a new filter shows the spinner; a failed reload still shows the
failure), UIB-2 (`CarodoSurface.onError`, `.carodoDestructive`; screenshots Light, Dark, Vietnamese
xxxLarge), XC-8 for what moves (PlaceEditorView camera, the heading cone, the claim button, the share
chips' tick, OdometerSheet on `rollingDigits`). Left: the XC-8 sites that only fade or change colour
(RootView, JourneyDayView, MapStatusViews), which Reduce Motion allows.
Group 3 (decisions before code, with recommendations): [`plans/audit-2026-11-20-group-3.md`](../plans/audit-2026-11-20-group-3.md).
Everything else is open, waiting for the owner's pick.

## Summary

| Slice | Appendix | High | Medium | Low |
|---|---|---|---|---|
| Tracking and recording | A1 (TRK) | 1 | 3 | 6 |
| Data, sync, backup, networking | A2 (DAT) | 0 | 4 | 5 |
| Domain, algorithms, lookups | A3 (DOM) | 0 | 0 | 11 |
| UI: App shell, Journeys, Map, Drive | A4 (UIA) | 0 | 2 | 6 |
| UI: Feed, Passport, Garage, Places, Settings, Backup, widgets | A5 (UIB) | 0 | 4 | 12 |
| Cross-cutting: design system, duplication, dead code, rules, tests | A6 (XC) | 0 | 4 | 10 |
| Backend carodo-app | A7 (API) | 0 | 3 | 9 |
| **Total** | | **1** | **20** | **59** |

No Critical. No IDOR, SQL injection, App Attest gap, banned construct (`try!`, `as!`, `DispatchQueue`,
`Task.detached`, Combine, `print`, `@unchecked Sendable`) or unused localization key was found.
The Feed's P5/P9 rules hold on the iOS side; widget code is extension-safe.

## Suggested order

**1. Fix first: drives or data can be lost**

| Id | What | Where |
|---|---|---|
| TRK-1 (High) | Resume after a pause can end the drive at once, at the stop before the pause: `pause()`/`resume()` never reset `StopDetector` | `Core/Recording/DriveSessionManager.swift:573`, `Core/Tracking/StopDetector.swift:204` |
| TRK-2 | One leftover trip that fails to save stops launch recovery for every later trip, at every launch | `Core/Recording/TripReconciliation.swift` |
| TRK-4 | The "short drive" test differs between live, recovery and resume: a real short drive can be deleted | A1 |
| DAT-1 | An iCloud batch that fails to apply is lost for good (change token already moved on) | `Core/Sync/CloudSyncService.swift:338` |
| DAT-2 | A record an older build skipped is never fetched again after an update | A2 |
| DAT-3 | One undecodable incoming track aborts the batch's deletes; the asset is stored with no size check | A2 |
| DAT-4 | Deletes made while signed out of iCloud are dropped on sign-in (privacy: a deleted drive survives) | A2 |
| UIA-1 | A failed garage read forgets the remembered vehicle and saves that | `App/DriveFlow.swift` |

**2. Privacy and security**

| Id | What |
|---|---|
| API-1 | An edit to a visible drive reaches the Feed within 30 s instead of the next quarter hour (P9) |
| API-2 | One attested key can claim unlimited usernames (only a per-location rate limit) |
| API-3 | Hourly prune deletes ≤1,000 rows/table; sessions and unauthenticated challenges can outgrow it |
| UIB-1 | Offline member taps the Feed avatar and gets "Claim your name" (`try?` folds failure into "not a member") |
| DOM-1 | Shared-log allowlist includes `car=`, same hash as developer-only `port` (no leak today) |
| DAT-5, API-5, API-10 | Crafted track can trap on join; any member can plant a tombstone for a known trip id; web has no security headers / SRI |

**3. Performance (main actor, whole-history work)**: TRK-3 (finish and recovery walk the whole drive on the
main actor, outside R6), UIB-4 and UIB-5 (Passport reloads every route per scope change; Passport and Garage
sums on the main actor), UIA-4 (Journey Detail reloads on every reappear), DOM-4/5/6/11, DAT-7.

**4. UI consistency**: XC-3 (cards hand-drawn in ~30 places, two fills, three hairlines), XC-5 (24 chevrons in
six styles), XC-9 (~1,040 raw spacing numbers vs 102 token uses), XC-6 (opacity-faded text), XC-7 (52 pt
odometer ignores Dynamic Type), XC-8 (8 animations ignore Reduce Motion), UIB-2 (Delete account 2.6:1
contrast in Dark), UIB-7, UIB-13–15, UIA-2 (Explore blanks to a spinner on every journal change), UIA-7, XC-2.
Best taken as one design-system pass (a `CarodoCard` and a chevron component) rather than file by file.

**5. Clean code and duplication** (pick up when a file is touched): TRK-7–10, DOM-9/10, UIA-5/6, UIB-6/11/12/16,
XC-10–14, API-11/12, DAT-8. **Correctness, small**: XC-1 (photo time in phone's zone, P3), XC-13, UIB-3,
UIB-8–10, UIA-3, UIA-8, DOM-2/3/7/8, DAT-6/9, TRK-5/6. **Tests to add**: XC-4 (JournalUpkeep,
BackendFeedTransport/Sharing, FeedAnswers) and the tests each fix above names.

**Contract and docs**: API-4 (P9 does not list account deletion / Stop sharing as exceptions), API-6–9
(profile 400, claim 429 vs 403, suggestions, no backend copy of the contract). These need the owner's call (P6).

## Coverage limits

Not read in full: `GapHealing`, `EnrichmentScheduler`, `RecordingGPS`, `DetectionWindow` internals (A1); most of
the Replay camera and recap code, `DrivingDynamics`, `TrackSpikes`, `StopPosition`, privacy-zone redaction,
`TripReport`, `MetricKitStore`, `ShareCardRenderer` (A3). No device or simulator check was made; every
performance item is unmeasured.


---

# Appendix A1

## Audit 01: tracking and recording path (read-only, 2026-11-20)

Scope: `Carodo/Core/{Recording,Tracking,Location,Motion,LiveActivity,Connections,Permissions,Concurrency}`,
`App/DriveFlow.swift`, `App/DependencyContainer+Live.swift`, `+Connect.swift`, `+LocalData.swift` (flush/erase part),
`Core/Recording/TripReconciliation.swift` (the former `+Recovery`, moved in `e240d9e`). Paths below are relative to `carodo-ios/`.
Already tracked and not repeated: TD-44, TD-45, TD-50, TD-55, TD-56, TD-64/65/66, TD-68, PV-8/30/32/37/42; the
2026-11-19 Auto Mode battery audit F2/F4 (detection GPS Best for the whole window) is still open as written there.

Summary: High 1 · Medium 3 · Low 6.

---

### TRK-1 · High · bug · Confirmed (by reading; no test covers it)

**Resume after a pause can end the drive at once, at the stop from before the pause.**

- `Carodo/Core/Recording/DriveSessionManager.swift:573-582` (`resume()`) and `:480-489` (a paused trip taken back at launch)
- `Carodo/Core/Tracking/StopDetector.swift:204-221` (`verdict`), `:85-88` (`init` sets `lastUsableFixAt` only once)
- `Carodo/Core/Recording/DriveSessionManager.swift:896-909` (the 20 s check keeps running through the pause)

What is wrong: `pause()` and `resume()` never tell the `StopDetector` that a pause happened. During the pause its state
does not change: `stoppedSince`, `slowSince` and `lastUsableFixAt` stay as they were before the pause.
`checkAutoFinish` only checks `state`, so as soon as `resume()` sets `.recording` the next check (the 20 s tick,
or the first fix through `ingest` → `checkAutoFinish`) sees a stop or a silence as long as the whole pause:
- Paused while stopped (the usual case: people pause at a stop), and the pause longer than `stopGraceS` (300 s, 600 s
  for a bicycle): the first fix after Resume reads `.still` because the car hasn't moved off yet. `stoppedSince`
  stays, `now - graceFrom >= stopGraceS`, and the verdict is `.finish(endedAt: stoppedSince, reason: .stopped)`.
- Paused while moving, pause > 720 s: if the 20 s tick fires before the first accepted fix arrives (GPS cold start after
  a long pause, indoors or in a garage), `now - lastUsableFixAt >= completionTimeoutS` and the verdict is `.noSignal`
  with `endedAt` = the last fix before the pause.

Failure scenario: an Auto Mode drive (auto-finish on). The person pauses at a café for 20 min, taps Resume
(in the app or on the Lock Screen) while still parked, and the drive is saved at once, ended at the café. What
follows is either a new Auto Mode drive (if a wake catches it) or nothing at all. A launch-resumed paused trip
(`resume(_ trip:)` always turns auto-finish on) behaves the same way. `testWithoutAutoFinishOrWhilePausedNothingEndsByItself`
(`CarodoTests/Core/Tracking/AutoModeTests.swift:426`) checks only the paused state, not what happens after Resume.

Fix: add `StopDetector.resumed(at:)`, which clears the stop and slow run and sets `lastUsableFixAt = at`
(or sets `keptGoingAt` and `lastUsableFixAt`). Call it from both resume paths. Add tests for a pause longer than
the grace and longer than the no-signal timeout, each followed by a still fix and by no fix.

---

### TRK-2 · Medium · bug (recovery hole) · Confirmed

**One unfinished trip that fails to save stops recovery for every trip after it, at every launch, and loses the
outcome of the trips already handled.**

- `Carodo/Core/Recording/TripRecovery.swift:55-89` (`try await store.complete/hold/discardTrip` inside the loop)
- `Carodo/Core/Recording/TripReconciliation.swift:74-85` (`result = try await TripRecovery.run(...)`; `catch` keeps `Result()`)

What is wrong: `run` throws out of its loop on the first failed write. The caller then keeps an empty `Result`.
The trips completed before the failure are committed but are not logged (`recoverTrip`), get no Stop and wait
(`joinWait` loops over `result.completed`), and give no `noteInterrupted`. A trip already taken back by `resume`
also loses its `resumed` step. The trips after the failing one stay `recording`. If the failure repeats (one
damaged trip, for example a constraint failure on `complete`), the same thing happens at every launch: those trips
never reach the journal, and the `launched` line reports 0 recovered.

Fix: catch per trip inside `run` and record a `failed` step, then continue with the next trip, so the result
stays complete. The caller then always gets the partial result.

---

### TRK-3 · Medium · performance · Confirmed (isolation from `project.yml`: `SWIFT_DEFAULT_ACTOR_ISOLATION: MainActor`, approachable concurrency)

**Whole-drive work on the main actor at the finish and at launch recovery.**

- `Carodo/Core/Recording/DriveSessionManager.swift:649-657`: `JourneyAnalysis.stopBands(of: recorder.metrics.route)`
  and `Journey.make` → `RouteSimplifier.simplify(metrics.route)` (`TripReplay.swift:159-180`), run synchronously in `end()`.
- `Carodo/Core/Recording/TripRecovery.swift:46` (`static func run` is `nonisolated async` without `@concurrent`, so
  it runs on the caller's actor, the main actor in `TripReconciliation`): `TripReplay.recover` replays every stored fix
  through `RouteRecorder` twice (once for `metrics`, once more with `keepingShort`), then `stoppedSince` replays them a
  third time through `StopDetector`, then simplifies.
- `DriveSessionManager.resume(_:)` (`:464-477`) replays the whole stored trip on the main actor (this one is needed,
  but it adds to the same launch).

What is wrong: `docs/architecture.md` (Algorithms table) names "simplifying on the main actor" as a mistake, and R6
covers whole-drive walks. These calls escape R6 because neither `RouteSimplifier.simplify` nor `TripReplay.recover`
is on its heavy list (KL-5: the list is kept by hand).

Failure scenario: a 3 h drive at 1 Hz is about 10,800 fixes. The hold-to-finish gesture and the Live Activity's
Finish block the main thread for Douglas–Peucker plus the band pass. A launch in the background after iOS ended the
app mid-drive replays the drive three times on the main thread before the first screen or the GPS restart.

Fix: give `TripRecovery.run` (or `TripReplay.recover`) a `@concurrent` entry and add it to R6. In `end()`, either
build the `Journey` with the simplified route off the main actor (the writer already completes asynchronously)
or simplify incrementally. Run `recover(keepingShort:)` once and decide short or long from its metrics.

---

### TRK-4 · Medium · bug (data loss on edge) · Confirmed

**Recovery and resume judge "short" with different rules from the live session.** This is a duplicated rule
that has drifted apart.

- Live: `DriveSessionManager.swift:319-324` (`isShortDrive`: class rules via `configuration.rules(for: vehicleClass)`, plus `missedStartM`)
- Recovery: `TripReplay.swift:121-125` (car thresholds `configuration.shortDriveDistanceM/shortDriveMovingS` always, no missed start)
- Resume: `DriveSessionManager.resume(_:)` (`:442-502`) restores neither `missedStartM` nor `fastFixes` (both are reset by `reset()`, `:1028`, `:1032`)

Failure scenarios:
- A 350 m / 80 s bicycle ride (kept live: the bicycle rule is 200 m / 60 s) whose app is ended mid-ride: recovery
  treats it as short with the car rule, so it is held. `HeldFragment.verdict` then needs 5 fixes at ≥ 25 km/h or 60 s
  automotive, which a bicycle rarely gives, so the ride is deleted.
- An Auto Mode drive that counted only because of its missed start (`missedStartM`, the 2026-11-08 case in the
  comment), resumed after a termination: once resumed, `isShortDrive` is true. With `fastFixes` reset to 0 and the
  short end reason `.stopped`, a drive under 150 m and 90 s moving is deleted instead of being dropped for "Keep it".

Fix: one function decides "short" (`ClassRules` plus missed start) and both paths call it. `UnfinishedTrip` needs
the class (from the vehicle) and the drive's `fromParkedM` (or a recount at resume). In `resume`, recount
`fastFixes` from the replayed fixes.

---

### TRK-5 · Low · bug (race across await) · Confirmed

**Untold-drive ids can be wiped after the await.** `App/DriveFlow.swift:262-273`: the guard checks
`session.untoldAutoFinishes.isEmpty` before `await journeyRepository.journeys(...)`. After the await,
`appState.rememberUntoldDrives([])` clears the persisted list. If an auto-finish lands during the read (Live
Activity Finish, or the 20 s check), `onUntoldChange` has just persisted its id, and this line wipes it. If the app
is then ended before `tellAutoFinishes` runs, the "Drive saved" toast for that drive is lost. Fix: remove only the
ids that were read (`ids`) and keep any others.

### TRK-6 · Low · battery · Confirmed

**The barometer runs through a pause.** `App/DependencyContainer+Connect.swift:56`:
`barometer.follow { driveSession?.isActive }`, and `isActive` includes `.paused` (`DriveSessionManager.swift:20-24`).
A pause can last up to 8 h (`pausedMaxS`), and during it `CMAltimeter` delivers to the main actor about once a second
and updates an `@Observable`. `Barometer.swift:5-7` says "Runs only while recording". Fix: follow
`state == .recording || .preparing` (the GPS's own condition, `applyGPS`).

### TRK-7 · Low · clean-code (unbounded growth, missing log line) · Confirmed

**`prependedByTrip` is emptied only through `DriveDiagnostics.logMotion` → `logRide` → `autoStart(trip.id)`**
(`Core/Tracking/AutoModeCoordinator.swift:245`, `:292-294`; `Core/Diagnostics/DriveDiagnostics.swift:~94-101`).
`logMotion` returns before `logRide` when `motion.readings` is nil (no Motion access) or when the trip is no longer
stored (discarded, short, Not me). So every such Auto Mode start leaves an entry for the life of the process, and
without Motion access the `leadIn` and `ride` lines are never written. Fix: call `logRide` whatever Motion answers,
and take the entry on every settled id (discard included).

### TRK-8 · Low · clean-code · Confirmed

**`reset()` leaves `vehicleID` and `trigger` set** (`DriveSessionManager.swift:1001-1036`), but clears
`vehicleSource`, `rider` and the rest. While idle, `vehicleClass` (`:199`) still answers for the last drive's
vehicle. Nothing wrong reads it today (the readers are guarded by `isActive`), but `DriveFlow.handle` reads
`session.trigger` after `finish` (`App/DriveFlow.swift:187`) and depends on this. Fix: hand the trigger over in
`FinishOutcome` or in the journey (`journey.start` already holds it), and clear both in `reset()`.

### TRK-9 · Low · duplication · Confirmed

- `TripContinuation.Ended(...)` is built twice with the same nine arguments in `DriveSessionManager.end`
  (`:674-676` and `:706-708`). Extract `private func interruptedEnd(...)`.
- The path length of a `[LocationSample]` is computed three times:
  `Core/Recording/TripReconciliation.swift:189`, `Core/Tracking/DetectionWindow.swift:194`,
  `Core/Domain/Journey/StopPosition.swift:117`. One `Geo.pathLength(_:)` would replace them.

### TRK-10 · Low · clean-code · Confirmed

**`TripWriter.discard()` keeps the trip in `failedTrips`** (`Core/Recording/TripWriter.swift:207-213`;
`unwritten` is cleared, `failedTrips` is not). After any failed write to a trip that is later discarded (undo,
Not me, short), `settled(id)` (`:245-247`) never clears `lastError`, so diagnostics keep showing a stale save error
for a trip that no longer exists, and the set grows. Fix: `failedTrips.remove(tripID)` in `discard()`.

---

### Checked and fine

- `TripWriter`: one ordered consumer, unbounded stream with backlog logging, failed writes replayed before
  an end, `confirmSaved` before "saved" is shown. `begin` and `reopen` clearing `pending` cannot drop fixes,
  because every end path flushes or discards first.
- `RouteRecorder`: validation before any consumer (stop detector, writer and live line all sit behind `acceptNext`);
  waiting fixes are settled before a pause, the finish and the background flush (`flushForBackground`).
- `DriveSessionManager` tasks: `likelyAnswerTask` and `autoFinishTask` use `[weak self]`, are cancelled in `reset`/`end`,
  and check `tripID`/`stoppedSince` after the await (`checkWalkAway`, `readLikelyAnswer`).
- No `Date()` inside the engines: `StopDetector`, `DrivingDetectionEngine`, `RouteRecorder`, `TrackingModeController`
  and `AutoModeCoordinator` take `now`. The wall clock is read only in the adapters (`CoreLocationServices`, Core Motion).
- `AutoModeCoordinator`: the Core Motion answers (`activityQuery`, `stillQuery`) are cancelled with the window and
  checked against `windowStats.openedAt`. `TrackingModeController.holdTask`/`timeoutTask`/`placesTask` are cancelled and re-checked.
- `CoreLocationSource`/`CoreLocationServices`: background updates only while a drive or detection runs, the hold is
  released in `endDrive`, region reports are filtered to the standby manager, and no coordinate reaches a log
  (only distances, accuracies and hashed port ids).
- `CarConnections`: P4 holds (a disconnect only shortens the grace); port names are never logged (`logID` hash).
- `DriveActivityController`/`SystemDriveActivityHost`: one wake task, cancelled on every end; updates are queued in order.
- `PermissionGate`, `PermissionPlan`, `Following`: no leaks; `Following`'s task is kept and cancelled by each owner.
- `flushForBackground`, the erase gate (`beginLocalDataErase`), `TripContinuation`, `ShortAutoDrive`, `ConnectedStart`.

Not covered in depth: `GapHealing`, `EnrichmentScheduler`, `RecordingGPS`, `DetectionWindow` internals, `MotionActivity` querying.

---

# Appendix A2

## Audit 02: data and the outside world (persistence, sync, backup, outbox, networking, identity)

carodo-ios at `5772921` (working tree has another session's uncommitted changes to entitlements, xcconfigs, project.yml and sync docs; they were read, not judged as finished work). Read-only audit.

Scope read: `Core/Persistence` (DatabaseManager schema, GRDBCloudSyncStore, GRDBBackupStore, +Backup, +Recording track paths, +Joins, DataOwnership, TrackCodec, RouteCoding, BoundedInflate, FeedStateStore, SQL interpolation sites), `Core/Sync` (CloudSyncService, CloudRecordCoding), `Core/Backup` (BackupFile, BackupFileAccess, BackupService, BackupDocument header, ZipEntry+Debug), `Core/Outbox` (all), `Core/Networking` (APIClient, BackendService, FeedAPI, BackendFeedTransport, claim path), `Core/Identity` (all but the debug key body), `Core/Maintenance` (LocalDataFiles, LocalCache), `App/DependencyContainer+LocalData`, `+Feed`/`+Connect` (spot), `Carodo.entitlements`, `project.yml` (ATS). Tracked items checked against `technical-debt.md` and the 2026-11-12 source audit (TD-20: M01, M10, L16 etc. are fixed and not re-reported).

### Findings

#### DAT-1 — A fetched iCloud batch that fails to apply is lost for good on this device
- Severity: Medium · Category: bug (data integrity) · Confidence: Confirmed (code path); the engine behaviour is CKSyncEngine's documented model
- Refs: `Carodo/Core/Sync/CloudSyncService.swift:338-384` (`handle`), `:352-353`, `:430-444` (`applyFetched`), `Carodo/Core/Persistence/GRDBCloudSyncStore.swift:197-247`
- What: `.fetchedRecordZoneChanges` runs `applyFetched`; any throw (a write failing: disk full, the database unreadable during a background push before first unlock, an I/O error) is caught at `:380`, logged as "Handling an iCloud event failed" and status goes `.failed`. CKSyncEngine has already advanced its server change token for that batch and delivers a `.stateUpdate` that `handle` persists (`:344-345`). Nothing records which records were not applied, and nothing makes the engine fetch them again.
- Failure: device B is offline/locked while device A renames a drive and deletes another; a silent push wakes B, the apply transaction fails, the token moves on. B never receives the rename or the delete until that record changes again or the engine state is reset (erase, account change). `status` flips back to `.upToDate` at the next clean round, so the person is never told.
- Fix: on an apply failure, do not persist the state from that round (keep the last saved serialization, or save `nil` to force a full refetch), or keep the failed record names in a table and fetch them with `CKFetchRecordsOperation` on the next start.

#### DAT-2 — A record skipped by an older build is never fetched again after the app updates
- Severity: Medium · Category: bug (data integrity) · Confidence: Confirmed
- Refs: `Carodo/Core/Sync/CloudRecordCoding.swift:126-127`, `Carodo/Core/Sync/CloudSyncService.swift:431-436`, `:472-477`; docs `docs/sync.md:63-66`
- What: a record with `CloudPayload.version` above `currentVersion` is "left in iCloud as it is" (logged and skipped). The fetch token still moves past it (as DAT-1). When this device later installs the build that can read version 2, nothing re-fetches the skipped records: CKSyncEngine only delivers records changed after the token.
- Failure: iPhone on 1.0 and iPad on 1.1 (payload v2). Every drive the iPad records while the iPhone is on 1.0 is skipped there; after the iPhone updates to 1.1 those drives never appear on it (and are not in its `.carodo` backups) unless edited again on the iPad. Silent data divergence across the owner's devices.
- Fix: keep the skipped record names (or simply a flag "skipped for version N") in `cloudkit_state`; when `CloudPayload.currentVersion` rises above the stored one, fetch them (or reset `engine_state` to refetch the zone whole). Document it in `docs/sync.md`.

#### DAT-3 — One undecodable incoming track aborts the batch's deletions and is stored unvalidated
- Severity: Medium · Category: bug / security (foreign bytes) · Confidence: Confirmed
- Refs: `Carodo/Core/Sync/CloudRecordCoding.swift:131` (`Data(contentsOf:)` of the asset, unbounded), `Carodo/Core/Persistence/GRDBCloudSyncStore.swift:235-242`, `:335-340` (track inserted as received, `codec_version`/`point_count` from the payload), `Carodo/Core/Sync/CloudSyncService.swift:437-443`, `Carodo/Core/Persistence/GRDBJourneyRepository+Recording.swift:222-228` (`TrackCodec.decode` throws)
- What: `store.apply` commits the trip with its raw asset bytes; only afterwards does the derive loop call `trips.storedTrip(id:)`, which decodes the track and throws `TrackCodec.DecodeError` on a damaged one. The throw leaves `applyFetched` before `store.applyDeletions(deleted)` and before `onRemoteChange?()`. With DAT-1, the deletions of that fetch are then lost for good. The bad track also stays in `trip_tracks` with `recorder_version = 0`, so every later derive of that drive (launch, Journey Detail) throws again. The asset file is read whole with `Data(contentsOf:)` before any size check (the codec bounds only the inflated size), against the "foreign bytes get bounds" rule.
- Failure: a truncated asset (an interrupted upload from another device, a damaged file) makes this device keep drives deleted on the other device in the same batch, and leaves a drive that never opens.
- Fix: validate the track (`TrackCodec.decode`, a size cap from `point_count`) in `CloudRecordCoding.decoding` and treat a bad one as a failed record; apply deletions before the derive loop and make the loop per-trip `do/catch` (log, keep `recorder_version 0`).

#### DAT-4 — Signing back in to iCloud drops deletes made while signed out
- Severity: Medium · Category: privacy / bug · Confidence: Plausible (depends on CKSyncEngine delivering `.signIn` for the same account after `.signOut`, which is its documented behaviour)
- Refs: `Carodo/Core/Sync/CloudSyncService.swift:386-405`, `Carodo/Core/Persistence/GRDBCloudSyncStore.swift:408-421`; `docs/sync.md:103-106`
- What: `.signIn` calls `resetCloudMarkers()`, which hard-deletes every tombstone (`deleted_at IS NOT NULL`) before re-marking rows. Repositories tombstone deletes while signed out (the engine is stopped, so they stay pending). When the same account comes back, those deletes are never sent: the records stay in the zone.
- Failure: the person signs out of iCloud, deletes a drive (a private route) and signs back in. The drive stays in iCloud and on their other devices, and comes back on a new iPhone or after Erase data plus iCloud restore. A delete the person made does not happen (P5: location history the person chose to remove persists).
- Fix: on `.signIn` keep tombstones (clear only `ck_metadata` and set `ck_pending`); drop them only on `.switchAccounts` and on a zone deletion, where the zone no longer holds the records. Add a test and a line in `docs/sync.md`.

#### DAT-5 — A crafted track can trap the app when parts are joined
- Severity: Low · Category: security (foreign bytes, trapping arithmetic) · Confidence: Confirmed (needs crafted bytes in a `.carodo` or the person's own iCloud)
- Refs: `Carodo/Core/Persistence/TrackCodec.swift:126-158` (sequence/segment decoded as any `Int64` via `&+`), `Carodo/Core/Persistence/GRDBJourneyRepository+Joins.swift:39-41` (`$0.sequence + offset`, `$0.segment + offset`)
- What: the codec accepts any `Int64` sequence/segment; `joinedTrack` adds `index * 1_000_000` with trapping `+`. A sequence near `Int.max` in a second part crashes the app on every read of that drive (journal derive at launch included, so possibly a launch loop).
- Fix: in `TrackCodec.decode`, reject a sequence or segment outside `0..<TripSample.partOffset` (or `Int32` range) as `.corrupt`; add the case to its damaged-input tests.

#### DAT-6 — A failed Keychain read reads as "no account"
- Severity: Low · Category: bug ("unknown is not zero") · Confidence: Plausible
- Refs: `Carodo/Core/Identity/AccountSecrets.swift:35-38`, `Carodo/Core/Networking/APIClient.swift:93`, `:112-117`; `Carodo/Core/Identity/AppAttestKey.swift:91-96`
- What: `KeychainAccountSecrets.text` folds a Keychain error (e.g. `errSecInteractionNotAllowed`) into `nil`, so `hasAccount()` says guest. A claim made then overwrites the stored secret (`KeychainItem.write` updates first), losing the old account and its username for good. `DeviceAttestKey.load` does the same (`try? item.read()`), so a failed read generates and saves a new App Attest key over the old id, and every token bound to the old key fails afterwards.
- Fix: make the reads `throws` and let callers tell "absent" from "failed" (show the Feed as unavailable, never offer a claim, never mint a new key on a read error).

#### DAT-7 — The iCloud pending query scans five tables on every relevant write
- Severity: Low · Category: performance · Confidence: Plausible (no measurement)
- Refs: `Carodo/Core/Persistence/GRDBCloudSyncStore.swift:36-61`; schema `Carodo/Core/Persistence/DatabaseManager.swift` (no index on `ck_pending`)
- What: the `ValueObservation` behind `pendingChangeUpdates` re-runs a `UNION ALL` of full scans of `vehicles`, `vehicle_logs`, `fuel_logs`, `places` and `trips` after each write touching their `ck_pending`/`deleted_at`/`status`/`confirm_by` columns. Cheap today; it grows with the journal on every edit, rename and sync batch (the route blob stays off it thanks to the column order).
- Fix: partial indexes `ON <table>(id) WHERE ck_pending = 1` (schema change, P6/invariant 6: `v1_initial`).

#### DAT-8 — Stale schema comment claims an `ON DELETE SET NULL` that does not exist
- Severity: Low · Category: clean-code · Confidence: Confirmed
- Refs: `Carodo/Core/Persistence/DatabaseManager.swift` (comment above `trips_on_parent`: "the `ON DELETE SET NULL` from a deleted trip"); `trips.parent_id` has no foreign key (column defined bare; `docs/sync.md` "no foreign key on `trips.vehicle_id` or `parent_id`"), parts are freed by `GRDBJourneyRepository.freeParts`
- Fix: say the index serves `freeParts` and the parts' reads.

#### DAT-9 — A sent batch whose bookkeeping fails is not handed back to the engine
- Severity: Low · Category: bug · Confidence: Confirmed (code path), rare trigger
- Refs: `Carodo/Core/Sync/CloudSyncService.swift:446-461`, `Carodo/Core/Persistence/GRDBCloudSyncStore.swift:142-169`
- What: iCloud saved the records and the engine dropped their pending changes. If `CloudPayload.decode` of one saved record or `store.markSent` throws, no row clears `ck_pending` and no change is re-added; the observation (`removeDuplicates`) does not fire because the pending id set did not change. The rows wait until the next `start()` (next launch or foreground restart), and their old `ck_metadata` makes that send a conflict round-trip.
- Fix: on a failure in `sent`, re-add `.saveRecord` for every saved record (cheap: `outgoing` answers nil once nothing is left).

### Already tracked (not re-reported)
- Backup resource bounds (M10, fixed: `BackupFile.Limits`, `BoundedInflate`, `BackupFileAccess.read` cap); iCloud retry (M01, fixed); cloud payload version gate (L16, fixed; DAT-2 is the consequence it left).
- KL-4 (`.carodo` without vehicle links), TD-6 (dev schema reset), TD-34 (bookkeeping on `trips` rewrites the route blob), TD-21 (no recovery without iCloud Keychain), PV-38 (iCloud sync device checks).

### Checked and fine
- SQL: every interpolated fragment is a constant table/column name or `databaseQuestionMarks`; `journeys(condition:)` is documented as never from input. No injection.
- CloudKit privacy: the payload goes only in `encryptedValues` (`CloudRecordCoding.swift:116`), the track as a `CKAsset` (encrypted), record names are UUIDs; logs carry only `CKError` codes (`describe`).
- `BackupFile`: size checked before load, iterations capped before PBKDF2, header authenticated as AES-GCM AAD, inflate bounded, version gates for file and document; temp backups written with `.completeFileProtection`.
- `TrackCodec`: header count bounded against the body before `reserveCapacity`, inflate bounded by count × max point bytes, varint shift capped at 64; `RouteCoding.decode` rejects partial blobs.
- `ZipEntry+Debug`: Debug only; declared size checked against the cap before allocating.
- Outbox: enqueue joins the caller's transaction and coalesces per resource; a replaced message's late `remove`/`postpone` hits a missing id (no-op); a hide's unpublish carries the bumped revision and `publish` re-checks revision and hidden state in the write transaction.
- P9: `FeedPublication.body` sends only the quarter-floored end, whole minutes, 100 m, a start hour derived from the sent figures; `feed_published_at` stays on device.
- App Attest: signed requests serialized with assertions made at send time; single-flight guest/access token fetches; the software key is `#if DEBUG` only, Release falls back to `UnavailableAttestKey`; no device or installation id on any request; Keychain items `AfterFirstUnlock(ThisDeviceOnly)`, the secret synchronizable as designed.
- ATS: only `NSAllowsLocalNetworking`; Release uses https (`Configuration.apiBaseURL`).
- DataOwnership: every trip/vehicle reference in the schema is classified; remote vehicle deletion runs `ownersDeleting` and clears trip links; trip-owned tables cascade.
- Local erase: sync paused and drained before the erase; only temporary copies and caches go before the database (rebuildable files, not files tied to surviving rows).
- `markSent` compares `updated_at` at the payload's millisecond precision and a trip's `revision`, so edits made during a send go again.
- Conflict apply: a tombstone or newer pending local change keeps the row and takes the server's system fields; links to records not here yet are kept; a part's join or trim re-derives the affected drives.

---

# Appendix A3

## Audit 03 — Domain, algorithms, lookups (carodo-ios, read-only)

Slice: `Carodo/Core/{Domain, Journal, Narrative, Atlas, Replay, MapLookup, Weather, Recognition, Achievements, Formatting, Diagnostics, Photos}`, against `docs/architecture.md` (Algorithms, Complexity budget, Concurrency, Map lookups). Tracked items (TD-n, KL-n, prior audit M16 etc.) are not repeated. Nothing above Low was confirmed in this slice; the code is in good shape. The slice was not read in full: see "Coverage limits" at the end.

### Findings

#### DOM-1 — Low — privacy — the shared log allows `car=`, which holds the same port hash as the developer-only `port`
- Refs: `Core/Diagnostics/DiagnosticsLogFormat.swift:71` (`"car", "carState", "outputs", "how"` in `sharedKeys`), `:79` (`port` developer only), `Core/Diagnostics/TrackingLog.swift:504-506` (`car=\(port.logID)`), `Core/Connections/CarConnections.swift:326` (`logID` = kind + 3 bytes of SHA-256 of the port uid).
- What is wrong: `port=carplay#3fa2c1` is classified developer-only because it is a stable identifier of the car's audio device (P5). The `route` line writes the same `logID` under the key `car`, and `car` is on the shared allowlist. Today the line never reaches the shared log only because `TrackingLog.swift:155` makes every carAudio event except connected/disconnected `.debug`, and shared mode drops debug lines. The key allowlist itself does not hold this field back. The comment at `:70` ("the info lines: connected, disconnected") does not match the keys listed.
- Failure scenario: someone moves `route` to `.info` (for example, to diagnose CarPlay links from a tester's shared log). Then a per-car stable identifier ships in the shared text, and `TrackingLogFieldsTests` stays green: its sample only has `car=none`.
- Fix: move `car` (and `carState`, `outputs`, `how`, which only debug lines carry) to `developerOnlyKeys`. Add a sample `route … car=carplay#…` line to `TrackingLogFieldsTests`.
- Confidence: Confirmed (misclassification); no leak today.

#### DOM-2 — Low — bug — `ReplayTimeline.storyShares` can return NaN
- Refs: `Core/Replay/ReplayTimeline.swift:522-532`.
- What is wrong: when `stillS <= 0`, `movingShare = 1`, and the result still evaluates `(1 - movingShare) * dts[index] / stillS` for each non-moving link. A non-moving link with `dt == 0` (`meters < creepStillStepM * max(0, 1)`) gives `0 * 0 / 0 = NaN`. If every non-moving link in the stop span has `dt == 0`, `stillS` is 0, and the guard only falls back to time shares when `movedM < creepMinM`.
- Failure scenario: a stop span with ≥ 20 m of creep, where every non-moving link has zero recorded duration (two fixes with the same timestamp, or a link left after spike removal with equal times). A NaN story value then poisons `keyframes[].story`. The binary searches in `moment`/`advance` misbehave, and the scrubber and video length (`storyDurationS`) become NaN.
- Fix: return `0` for non-moving links when `stillS <= 0` (`stillS > 0 ? … : 0`). Add a test with a zero-dt link inside a creeping stop.
- Confidence: Plausible. The arithmetic is confirmed; whether the recorder ever stores equal-timestamp fixes inside a stop was not checked.

#### DOM-3 — Low — bug — `ProviderGate.send` throws raw, unclassified errors to callers that join an in-flight request
- Refs: `Core/MapLookup/ProviderGate.swift:106-108` vs `:116-126`.
- What is wrong: the first caller gets a `LookupFailure` (classified, and the cooldown recorded). A second caller with the same key awaits `running.value` and gets the raw `MKError` / `URLError` / `CLError`. The protocol docs promise `LookupFailure` (`PlaceLookup.swift:8`, `WeatherLookup.swift:12`).
- Failure scenario: two adapters ask the same key at once, for example `AppleMapsPlaceLookup` from `MapDataCache.lookUp` (Provinces) and from a different cache instance or a test path. The joiner's `catch LookupFailure.overBudget`, or a `switch` on the failure, does not match, so an offline failure can be treated as a generic failure. The impact is small today because `MapDataCache.ask` already dedupes per key.
- Fix: wrap the joiner's await in the same `do/catch` and map it with `LookupFailure(error)`, passing `CancellationError` through.
- Confidence: Confirmed (code path); impact Low.

#### DOM-4 — Low — performance — Passport streaks run the calendar on every drive of the history, several times
- Refs: `Core/Domain/Passport/PassportAnalysis.swift:129` (`longestStreakRun`: `startOfDay` for every start), `:174` (`drivingDays`: `startOfDay` for every drive again), `:195` (`currentStreak`: `startOfDay` for every start, although only the last days matter).
- What is wrong: this goes against the budget row "Calendar work over many drives: a `Date` comparison first, the calendar only on what is left". `highlights` maps the whole history through `startOfDay` twice, and `rhythm` → `currentStreak` does it a third time just to count back from today.
- Failure scenario: at 2,000+ drives, each Passport load runs about 6,000 `Calendar.startOfDay` calls on whatever actor calls this (a few ms; more on older phones). It also grows with the history for a figure that needs only recent days.
- Fix: build the sorted day set once and pass it to both `longestStreakRun` and `drivingDays`. In `currentStreak`, first keep only the starts after `today - (count of days) …`, or walk the sorted days from the end.
- Confidence: Confirmed (pattern). The cost was not measured.

#### DOM-5 — Low — performance — `FuelEconomy.average` filters every drive once per full fill
- Refs: `Core/Domain/Vehicle/FuelLog.swift:197-201`.
- What is wrong: inside the loop over fills, `drives.lazy.filter { vehicleID … startedAt in [start, fill) }` scans the vehicle's whole drive list for each full fill: O(fills × drives). The budget row "Lookups inside a loop" names this pattern.
- Failure scenario: three years of weekly fills (about 150) and 2,000 drives is about 300k comparisons per Garage render of that vehicle. That is fine today, but it grows quadratically.
- Fix: sort the vehicle's drives by `startedAt` once and walk them with a pointer alongside the fills (prefix sums of `distanceM`).
- Confidence: Confirmed (complexity); no measured stall.

#### DOM-6 — Low — performance — `MapDataCache.store` sorts the whole cache on every insert once it is full
- Refs: `Core/MapLookup/MapDataCache.swift:383-388`.
- What is wrong: once `entries.count > maximumEntries` (5,000), every new answer sorts all entries by `fetchedAt` to drop one. A drain or `remember` (search results) of k answers costs k × O(n log n) on the actor.
- Failure scenario: a person with a full cache scrolls the journal. Each of 100 queued names sorts 5,000 entries (about 0.5M comparisons in total per drain), and other cache reads wait on the actor meanwhile.
- Fix: evict in a batch down to about 90 % of the cap, so the sort runs once per many inserts. Alternatively, evict expired entries first (`purgeExpired`), which usually frees enough.
- Confidence: Confirmed (complexity); small absolute cost.

#### DOM-7 — Low — clean-code / bug — a cancelled map-image request does not give up its queue place
- Refs: `Core/Journal/JourneyMapSnapshotService.swift:150-152` (the doc comment says "One still queued gives its turn up at once"), `:182-195` (`acquire` uses a plain `withCheckedContinuation`, not cancellation-aware), `:170-171`.
- What is wrong: `leave` cancels the flight's task, but if that task is parked in `acquire`, it stays in `waiting` until a running render releases. It then takes the slot, sees `Task.isCancelled`, and releases. It does not "give its turn up at once". With a fast scroll, dozens of cancelled flights stay queued, each costing a resume and release, and the comment overstates the behaviour.
- Failure scenario: a fast scroll through Journeys queues 30 rows and leaves. A newly visible row's render waits behind the cancelled continuations as they drain one by one through each freed slot. That is a short delay, not a wrong image.
- Fix: make `acquire` cancellation-aware (`withTaskCancellationHandler` that removes and resumes its continuation), or correct the comment.
- Confidence: Plausible (behaviour read from code; the delay was not measured).

#### DOM-8 — Low — privacy / clean-code — cached map images are pruned only at launch, and the clock is `Date()`
- Refs: `Core/Journal/JourneyMapSnapshotService.swift:89` (prune only in `init`), `:162-168` (`make` reads a file with no age check), `:332` (`Date()` rather than an injected clock).
- What is wrong: a PNG of Apple map tiles past `LocalCache.journeyMapsMaximumAgeS` is still read and shown while the process stays alive. An app kept alive for days by Auto Mode relaunches never re-runs `prune`. The age limit is the Map Data "temporary, limited basis" safeguard (the broader terms question is TD-2/TD-41). The age rule also cannot be tested deterministically.
- Fix: check the file's creation date against `maxAge` in `make` before using it, or prune on foreground as `MapDataCache.purgeExpired` does. Inject `now`.
- Confidence: Plausible (how long a real process lives was not checked).

#### DOM-9 — Low — duplication / clean-code — `DisplayFormat.coordinate` is an unused copy of `position`, and `clock` lost its doc comment
- Refs: `Core/Formatting/DisplayFormat.swift:30-38` (`coordinate`, no caller in app or tests), `:104-113` (`position`, the same output; the doc comment of `clock` at `:104-105` is fused onto `position`), `:115` (`clock` has no doc comment).
- What is wrong: two functions produce byte-identical text. One is dead, and the comments are misattached: `position` reads "A drive's clock time as the driver lived it".
- Fix: delete `coordinate`, and move lines 104-105 back above `clock`.
- Confidence: Confirmed.

#### DOM-10 — Low — duplication — route bounds are computed three times, none across the 180th meridian
- Refs: `Core/Journal/RouteFraming.swift:48-70` (`rect(forLines:)` hand-rolled min/max), `RouteFraming.bounds(of:)` (same over `RoutePoint`), `Core/Atlas/AtlasGrid.swift:26-38` (`AtlasRect.init(_ coordinates:)`).
- What is wrong: the same "bounds in map points" loop appears three times. None uses `LocalProjection.longitudeDelta`, the architecture's rule for this, so a route across 180° gets bounds the width of the world. A share-card or snapshot frame then shows the whole world, and the Atlas entry intersects every viewport.
- Fix: one `AtlasRect(lines:)` / `MKMapRect` helper that unwraps x the short way (as `FootprintGrid.cells` already does), used by all three.
- Confidence: Confirmed (duplication); the antimeridian effect is Plausible, since no such drive exists.

#### DOM-11 — Low — performance — `Money.fractionDigits` builds a `NumberFormatter` per call
- Refs: `Core/Formatting/Money.swift:13-18`, called by `decimal`, `minor`, and both `format` functions (each row in Garage logs and totals).
- What is wrong: `NumberFormatter` construction is expensive (ICU setup). It runs once or twice per amount shown, on the main actor during list rendering.
- Fix: a small static `[String: Int]` cache, or `Locale.Currency`/ISO 4217 table lookup.
- Confidence: Confirmed (pattern); the cost was not measured.

### Checked and fine
- `Geo` / `LocalProjection`: haversine is clamped (`min(1, sqrt(h))`). Longitude delta and interpolation take the short way, and `metersPerDegreeLongitude` has a floor.
- Prior M16 (heat across 180°) is fixed: `HeatGrid.steps`, `distanceM` and `interpolate` all use `LocalProjection.longitudeDelta`/`interpolatedLongitude`.
- `RouteHeatIndex` add/remove/recompute: stamps prevent double counting, the minimum is recomputed through block membership, and `intersects` is a binary search. It matches the algorithm table.
- `FootprintGrid.cells`: wraps dx across 180°, and `AtlasGrid.tile` wraps x into range, so the `UInt64(tile.x)` key can never trap.
- `HistoryAtlas`: incremental update, a revision guard on snapshots, and a bounded layer cache (16).
- `ProviderGate.waitS`: the per-minute window index math is correct (the `freeing`-th oldest must expire), and the screen reserve is applied for background work.
- `MapDataCache`: failures are never cached (only `store` after a successful `ask`). The file size is bounded before reading, a damaged file is deleted, a locked-file read keeps `isLoaded=false` and never overwrites, there is no double drain across awaits, and cooldown and rest back off exponentially.
- `PlaceNameCache` / `POINameLookup` / `AppleMapsPlaceLookup`: private cells are refused before asking, and "nothing there" (nil) is kept apart from failure (throws).
- `ProvinceBisection`: explicit stack, cached anchors, a `maximumLookupsPerRun` budget enforced in `ProvincesCrossedSource`, and gaps mark the result incomplete.
- `WeatherPoint` / `WeatherRounding`: the hour is floored in UTC, only an about-11 km cell leaves the device, and the WeatherKit gate has a per-day cap.
- `DiagnosticsLogFormat`: fail-closed allowlist, hour-only times in shared mode (P9), and the debug level is filtered out of shared output.
- `DisplayFormat.clockEnds` / `dayAndPartOfDay`: use the recorded zone (P3). Durations are clamped at 0.
- `JourneyDetails` speed shares and elevation: totals are guarded (`total > 0`, `points.count >= 2`), and smoothing uses running sums (O(n)).
- `DriveShapeMaker.fitted` and `RouteGlyphMaker.scale`: guard on a zero or non-finite side; the log is used only above `nearDistanceM`.
- `JourneyFacts.comparison`: guards `median > 0`.
- `JourneyStatisticsService.latestJourney`: pages until a sure drive is found (L15 resolved).
- `BadgeLedger`, `PhotoSaver` (add-only permission, off the main actor), `VehicleRecognitionService` (no network, model answers checked against the name): fine.
- No `Date()` in domain logic other than DOM-8. No `try!`, `as!`, `DispatchQueue`, `Task.detached` or `.repeatForever` in the slice.

### Coverage limits
These were read only partly or by pattern search: `ReplayTimeline` (beyond its division sites), `RecapScript`, `CameraDirector`/`CameraScript`, `FollowCamera`, `DrivingDynamics`, `TrackSpikes`, `StopPosition`, `PrivacyZone`/`PrivateRegionRedaction`, `NarrativeEvaluation+Debug`, `TrackingLog` (beyond the car-audio part), `TripReport`, `MetricKitStore`, and `ShareCardRenderer`.

---

# Appendix A4

## Audit 04: App shell, Journeys, Map, Drive (UI slice)

carodo-ios at `5772921`, read-only, 2026-11-20. Slice: `Carodo/App` (MainTabView, RootView,
FloatingDriveControls, AppDestination, AppState, DeepLink, DriveFlow, CarLogSheets, JourneyByIDView),
`Features/Journeys`, `Features/Map`, `Features/Drive`.

Already tracked, so not reported again: TD-50 (recording panels' 1 s `TimelineView`), TD-70 (callouts),
TD-29 (figure and unit wrap), U5 / design-system Known gaps (about 450 literal paddings and radii, so
literal `padding(14)` and `cornerRadius: 18/20` in this slice are not listed one by one), C6 / step 7
(view models built in `destination(for:)`, measured and accepted), the AnyView factories and
`MapAtlasView` root `@State` ("Considered and not planned"), A4 (the collapsed panel under the
expanded sheet).

### Findings

#### UIA-1 — Medium — bug
**A failed garage read makes the app forget the person's chosen vehicle, and stores that.**
`Carodo/App/DriveFlow.swift:71`, `:81`, `:83-86`.
`reloadVehicles()` reads `(try? await vehicleRepository.vehicles()) ?? []`, so a failed read gives an empty
garage. Line 81 then runs `appState.forgetVehicle()` because the remembered vehicle is "gone". That writes
`lastVehicleID = nil` and `vehicleChoice = false` to UserDefaults. Line 86 also sets `hasReadGarage = true`, so
`tapStartButton` sees `vehicles.isEmpty` as an empty garage and decides it is ready.
**Scenario:** the database read fails once, for example during a relaunch with I/O pressure or a
store that cannot be read yet. The next one-tap start records with no vehicle, and every later start
asks for the vehicle again, although the car still exists. This is the "Unknown is not zero" rule in AGENTS.md:
an absent answer and a failed one are folded into one `nil`.
**Fix:** use `do/catch`. On failure, keep the earlier `vehicles` and leave `forgetVehicle`, `selectedVehicleID`
and `hasReadGarage` as they are. Forget only after a read that succeeded. `DriveStarts.startFromShortcut:56`
does not forget, so it is the pattern to follow.
**Confidence:** Confirmed (code path). Whether a read fails in the field is Plausible.

#### UIA-2 — Medium — bug (UX)
**Every journal change wipes Explore to a spinner and sends the list back to its top.**
`Features/Journeys/Views/Explore/JourneysView.swift:173-178`, `:186-188`;
`ViewModels/Explore/JourneysViewModel.swift:88-93`, `:349-363`.
The `.task` id includes `appState.journalRevision`. `prepare(revision:)` clears `loadedRequest`, so
`loadIfNeeded()` runs a full `load()`. That sets `state = .loading` and `journeys = []`, and
`listSections` replaces the whole list with a `ProgressView`. Only the first page comes back.
Day does not do this: `JourneyDayViewModel` keeps the shown day through `state.beginReload()`.
**Scenarios:**
- Long-press Delete on a row deep in the history: the list blanks, then reopens at the top.
- On return to the foreground, `DriveFlow.returnedToForeground` (`App/DriveFlow.swift:294`, `:302`) calls
  `journalDidChange()` when enrichment fills a name or a held trip settles. A person reading Explore
  sees it flash to a spinner and lose their place, with no action of their own.
- Pull-to-refresh (`refresh()` → `load()`) shows the system spinner and the in-list spinner together.
**Fix:** reload in place like Day. Keep `journeys` and `state` until the new first page arrives, then swap
it in. Only a filter change should clear the list.
**Confidence:** Confirmed in code. The foreground case is Plausible: it needs enrichment to report a change.

#### UIA-3 — Low/Medium — bug
**"Log for your car" gets every active vehicle, bicycles included, not the loggable ones.**
`Carodo/App/CarLogSheets.swift:59` and `:72`.
`open()` reads fill-ups and logs for `drive.loggableVehicles`, which has no bicycles (`DriveFlow.swift:90-92`).
It then builds `LogForCar(vehicles: drive.vehicles, …)`, which is every active vehicle.
`VehicleActionsSheet` documents its input as "Active vehicles with fuel or an odometer"
(`Features/Garage/Views/VehicleActionsSheet.swift:19`). With no remembered vehicle, it preselects `vehicles.first`.
**Scenario:** a garage with a car and a bicycle. The sheet offers the bicycle as a choice, and
may open on it, with fuel and odometer actions it cannot take. The bicycle also has no logs read, so
it shows no log line.
**Fix:** pass `vehicles` (the local `loggableVehicles`) instead of `drive.vehicles`.
**Confidence:** Confirmed (code). I did not check on screen how the sheet draws a bicycle.

#### UIA-4 — Low — performance
**Journey Detail runs its whole `load()` again on every reappearance, and twice after a Trim.**
`Features/Journeys/Views/Detail/JourneyDetailView.swift:197-199`, `:133-137`;
`ViewModels/Detail/JourneyDetailViewModel.swift:469-477`, `:637-724`.
`.task { await model.load() }` has no "already loaded" guard. Each of these re-runs it:
- back from a pushed visits page;
- a tab switch back;
- closing Replay, or any full-screen cover.

Each run reads details, places, vehicles, drive logs, milestones, joined parts, merge candidates, history
distances and the narrative, then `loadWeather()`. The cached analysis is the only part it skips.
After Trim, the cover's dismissal re-runs `.task` and the trim callback also calls `reloadJourney()` → `load()`.
The two loads overlap, and nothing (no generation token) protects them. The older load stores a cache entry
under its own captured `journey`, so the cache can miss. It is not a wrong display.
**Fix:** keep a loaded flag or revision and re-run only on `journalRevision`/trim. Give `load()` a generation
token like `JourneysViewModel`.
**Confidence:** Confirmed (code). The cost was not measured.

#### UIA-5 — Low — duplication
**Explore's and Day's view models repeat the same row accessors.**
`ViewModels/Explore/JourneysViewModel.swift:253-255, 280-305, 320-331` and
`ViewModels/Day/JourneyDayViewModel.swift:166-227`.
These are in both, with the same bodies: `mapIdentity(_:)`, `title(for:)`, `titleAwaitsPlaces(for:)`,
`startMark(for:)`, `rowVehicle(for:)`, `vehicle(for:)`, `milestone(for:unit:)` and `glyph(for:)`. Each reads its
own `details`/`glyphs`/`vehicles`/`milestones` dictionaries.
**Fix:** one small value type, for example `JournalRowFacts` holding details, glyphs, vehicles and
milestones, with these accessors. Both models own one and the rows read through it.
**Confidence:** Confirmed.

#### UIA-6 — Low — clean-code
**Dead method: `JourneysViewModel.detailModel(for:)`.**
`ViewModels/Explore/JourneysViewModel.swift:338-343`. Nothing calls it in `Carodo/` or `CarodoTests/`. Journey Detail's model
comes from `AppDestination.Models.journeyDetail`. Its doc comment ("with the same repositories as the
list") also suggests a second way to build the page that does not exist.
**Fix:** remove it.
**Confidence:** Confirmed (grep).

#### UIA-7 — Low — duplication / ui-consistency
**Charcoal ground written as a literal RGB in two renderers.**
`Features/Journeys/Views/Replay/ReplayVideoOverlay.swift:53` and `Core/Journal/ShareCardRenderer.swift:349`
both use `UIColor(red: 30/255, green: 29/255, blue: 27/255)`. That is a darker Charcoal than `CarodoColor.charcoal`
(36·35·33) and is not a design-system token. The video and the share card agree only by copy.
**Fix:** make it a named token in `CarodoColor` (a dark ground for rendered media) and use it in both.
**Confidence:** Confirmed.

#### UIA-8 — Low — bug
**The short-drive banner's timer is not keyed to the notice.**
`Carodo/App/FloatingDriveControls.swift:125-128`.
`.task { sleep 2.5 s; drive.shortDriveNotice = nil }` runs once per appearance of the `Label`. A second
notice that arrives while the first is on screen keeps the same view and the same task, so it is cleared
when the first notice's 2.5 s run out. If the person leaves the screen (the task is cancelled), the
`try?` sleep returns at once and clears the notice early. That second part is harmless.
**Fix:** `.task(id: shortDriveNotice)` and `do { try await … } catch { return }`, as `KeptToast` does
(`JourneysView.swift:516-520`).
**Confidence:** Plausible. Two short drives ending within 2.5 s is rare.

### Checked and fine

- **Deep links:** `carodo://trip/start` is idempotent. `DeepLink` → `OutsideRequest.startDrive` waits for
  `hasReadGarage`, and `DriveFlow.start` → `container.startDrive` returns `.alreadyRecording` while a
  drive records. `openLiveDrive` re-checks the request after its `await`. Unknown links are ignored.
- **Display links:** `ReplayPlayer`, `JourneyMapCoordinator` and `AtlasMapView` use `DisplayLinkTarget.link(owner:)`.
  Replay stops its link when paused, at the end and in `onDisappear`. There is no `.repeatForever`,
  `Task.detached`, `DispatchQueue`, `try!`, `as!`, `@unchecked`, `isAccessibilitySize` or large title in the slice.
- **Maps taken down:** the Map tab (`MapAtlasView` `takeDown`/`comeBack`) and Journey Detail
  (`isOffScreen`) take their maps down when off screen.
- **Stale answers:** these are guarded by generation or call counters with cancellation checks:
  `JourneysViewModel.load/loadMore/refresh*`, `JourneyDayViewModel.loadDay/loadMonths/refreshDetails`,
  `MapAtlasViewModel.showPlaces` (`placesCall`, a cancelled read not treated as failed) and
  `placeRenamed`. Explore's prefetch is owned by the model.
- **LoadState:** Explore and Day show `LoadFailedView` with Retry on failure, and "empty" only once loaded.
  Secondary reads fall back to hiding, not to "0".
- **`JourneyByIDView`:** says "unavailable", never an empty drive.
- **Strings:** no hard-coded user-facing string literals in the slice. `Text(verbatim:)` is used only for "·"
  and the "×" rate.
- **Copper:** used as small marks only (filter dot, day marks, location marker, 3 pt bars). Never a large fill.
- **Long-lived services:** `DriveFlow` Tasks capture `[weak self]` or only values, and the class has
  `nonisolated deinit`.
- **Garage sheet:** it opens after its model loads and re-checks `isGaragePresented` after the `await`.
- **`CarLogSheets`:** cancels the earlier read when a new one starts.

---

# Appendix A5

## Audit 05: other features and widgets (Feed, Passport, Garage, Places, Settings, Backup, Help, Developer, Onboarding, CarodoWidgets, CarodoShared)

This is a read-only audit of carodo-ios `main` at `5772921` plus the working tree. Nothing was edited.
Known items I left out: TD-11, TD-35, TD-49, TD-52, TD-71, U5 (spacing and radii are fixed only when a file is touched), A5, L14.

### Medium

#### UIB-1: An offline member who taps the Feed avatar gets "Claim your name"
- Severity: Medium. Category: bug.
- Refs: `Carodo/Features/Feed/ViewModels/FeedViewModel.swift:90-91`, `Carodo/Features/Feed/Views/FeedView.swift:105`, `Carodo/Features/Feed/Views/JoinTheFeedSheet.swift:18-25`, `Carodo/Features/Feed/ViewModels/FeedIdentityViewModel.swift:193-194`.
- What is wrong: `loadStanding()` reads `try? await repository.identity()`, so a failed read makes `isMember` false. The avatar then opens `.join` instead of `.profile`. In the Join sheet, `load()` fails the same way and sets `.failed`, and `.failed` falls to the `default:` branch, which is `ClaimStep`. This is the "unknown is not zero" mistake.
- Scenario: A member opens the Feed offline, or while the server is down, and taps their avatar. They see "Claim your name" and a username field, not Edit profile. Settings uses `appState.feedProfile` and gets this right, so the two entry points disagree.
- Fix: Decide join or profile from `appState.feedProfile`, as Settings does, or keep membership unknown when the read fails and disable the avatar. Give `JoinTheFeedSheet` a real failed state with Retry instead of `ClaimStep`.
- Confidence: Confirmed.

#### UIB-2: Delete account button has white text on the Dark error colour (about 2.6:1)
- Severity: Medium. Category: accessibility.
- Refs: `Carodo/Features/Feed/Views/FeedProfileSheet.swift:230-241`.
- What is wrong: The confirm button draws `.foregroundStyle(.white)` in `.headline` on a `CarodoSurface.error` capsule. Dark `error` is 255·118·110, and white on it is about 2.6:1. AA needs 4.5:1 for 17 pt semibold. `docs/design-system.md#contrast` says every text colour passes. The capsule is also drawn by hand next to `.carodoPrimary`, so the sheet's CTA style lives in a second place.
- Scenario: In Dark appearance, "Delete account" reads poorly on its most consequential button.
- Fix: Use Charcoal text on the Dark error fill (a token, for example `CarodoSurface.onError`), or a darker destructive fill in Dark. Consider a `.carodoDestructive` button style next to `CarodoPrimaryButtonStyle`.
- Confidence: Confirmed (ratio computed from the documented token).

#### UIB-3: A cancelled Passport load can briefly show the failed state
- Severity: Medium. Category: bug.
- Refs: `Carodo/Features/Passport/Views/PassportView.swift:84-93`, `Carodo/Features/Passport/ViewModels/PassportViewModel.swift:234-251`, `:270-308`.
- What is wrong: `load()` and `loadExploration()` run from `.task(id:)`, which cancels the previous run when the id changes. Their `catch` does not tell `CancellationError` apart and has no generation check. A cancelled `load()` sets `state = .failed`, which hides every section and shows the header's Retry. A cancelled `loadExploration()` with the same scope sets `exploration = .failed` and `signature = nil`. A cancelled run that does not throw can still apply older facts after the newer run, because nothing checks a request id. `loadRhythm` has no guard either.
- Scenario: Saving a drive and its derived writes bump `journalRevision` twice in quick succession. The Passport flashes "couldn't load" and the footprint fails, then reappears. Rarely, it can end on the older facts.
- Fix: Add a request counter, as `loadMilestones` already has. In `catch`, return on `CancellationError` or `Task.isCancelled` before writing `.failed`.
- Confidence: Plausible. GRDB async reads throw on cancellation; I did not reproduce it.

#### UIB-4: Every Passport scope change reads and redraws the whole history for the unchanged header
- Severity: Medium. Category: performance.
- Refs: `Carodo/Features/Passport/ViewModels/PassportViewModel.swift:280-286`.
- What is wrong: For any scope other than All time, `loadExploration` calls `drivenRoutes(in: nil)`, which loads every route's points. It then runs `geometry` and `signature` again to rebuild the header artwork, which does not depend on scope. It also re-reads the private places each time.
- Scenario: Switching to This month on a long journal decodes every route and recomputes redacted segments, cells and the fingerprint. This is CPU and battery spent on a picture that did not change.
- Fix: Cache the all-time signature keyed by `factsRevision` plus the private circles' fingerprint, and only recompute it when that key changes.
- Confidence: Confirmed by reading. The cost is unmeasured.

### Low

#### UIB-5: Whole-journal analyses run on the main actor, several times per load
- Severity: Low. Category: performance.
- Refs: `Carodo/Features/Passport/ViewModels/PassportViewModel.swift:58-65,128-130,225-230,236-246`, `Carodo/Features/Garage/ViewModels/GarageViewModel.swift:89-108`.
- What is wrong: The `didSet` observers on `facts`, `vehicles` and `unlocks` each run `derive()` or `deriveMilestones()`. One `load()` therefore runs `PassportAnalysis.highlights` and `vehicleTotals` twice, and `AchievementEngine.progress` three times, all on the main actor over every drive. Garage's `load` runs `vehicleTotals`, `gpsSinceReading` per vehicle and `weeklyDistanceM` per vehicle over all drives on the main actor too. This is O(vehicles × drives). AGENTS.md (Concurrency, R6) asks for whole-journal work to go through a `@concurrent` entry. These functions are not on R6's list.
- Fix: Derive once after both reads, in one `@concurrent` function that returns a value bundle. Add the heavy functions to R6 if a measurement shows a cost.
- Confidence: Plausible. The cost depends on journal size.

#### UIB-6: `VehicleDetailViewModel` declares its own `LoadState`
- Severity: Low. Category: clean-code.
- Refs: `Carodo/Features/Garage/ViewModels/VehicleDetailViewModel.swift:7-13`, `Carodo/Core/Domain/LoadState.swift:5`.
- What is wrong: A nested `enum LoadState` adds `.missing` and shadows the shared type. TD-10 was closed as "one LoadState", and the conventions say "never reuse an existing name for a new concept". The nested type also loses `beginReload()`, so line 76 does the same thing by hand.
- Fix: Keep `Core` `LoadState` and add a separate `isMissing` flag, or rename the type `VehicleDetailState`.
- Confidence: Confirmed.

#### UIB-7: Edit profile's failed state uses `ContentUnavailableView`, not `LoadFailedView`
- Severity: Low. Category: ui-consistency.
- Refs: `Carodo/Features/Feed/Views/FeedProfileSheet.swift:39-50`, `docs/design-system.md` (Components, `LoadFailedView`).
- What is wrong: The design system says every failed primary read uses `LoadFailedView` and names only two exceptions: the Feed's quiet state and the Passport card. The profile sheet hand-draws a third look. TD-35 tracks only its "blames the connection" wording.
- Fix: Use `LoadFailedView(title: .Feed.identityFailed, retry: reload)`, or list the sheet as an exception in the doc.
- Confidence: Confirmed.

#### UIB-8: Places editor can open at 0°, 0° (Null Island)
- Severity: Low. Category: bug.
- Refs: `Carodo/Features/Places/ViewModels/PlacesViewModel.swift:100-109`.
- What is wrong: `startCentre` is nil when there is no drive and no place. The editor is then built at `latitude: 0, longitude: 0`. When location is not allowed, `followsPerson` is false, so nothing moves the map.
- Scenario: Someone who denied location and has not driven yet taps Add Home. The map opens in the Gulf of Guinea, and Save without panning stores a place there.
- Fix: Fall back to the device region's centre (`Locale.region`) or the whole-country map, and disable Save until the map has been moved.
- Confidence: Confirmed by reading.

#### UIB-9: Places reads a whole journey to get one coordinate
- Severity: Low. Category: performance.
- Refs: `Carodo/Features/Places/ViewModels/PlacesViewModel.swift:101`.
- What is wrong: `journeys(before: nil, limit: 1).first?.route.last` decodes the latest drive's full route on every load, including after each Undo, only to use its last point.
- Fix: Use a light end-point read (the store already has endpoint and fact reads), or `drives().first`'s end.
- Confidence: Confirmed.

#### UIB-10: Backup restores can overlap
- Severity: Low. Category: bug.
- Refs: `Carodo/Features/Backup/ViewModels/BackupViewModel.swift:175-197`, `Carodo/App/MainTabView.swift:263-264`.
- What is wrong: `open(_:)` has no `isBusy` guard. An incoming file opens a second `BackupView` with a new model, so a restore can start while Settings → Backup is still making or restoring a backup. Nothing serializes the two restores.
- Scenario: A restore of file A is running and an AirDrop of file B arrives. Both run against the store.
- Fix: Guard `open` on `isBusy`, and serialize restores in one place: the container's data-work gate, which erase already uses.
- Confidence: Plausible.

#### UIB-11: The profile sheet's model is built on every parent redraw, in two copies of the same switch
- Severity: Low. Category: duplication / performance.
- Refs: `Carodo/Features/Feed/Views/FeedView.swift:125-132`, `Carodo/Features/Settings/Views/SettingsView.swift:142-151`.
- What is wrong: Both views create `FeedIdentityViewModel(...)` inside the sheet's `@ViewBuilder`. `FeedProfileSheet.init` then calls `renameModel`, creating a second model. This happens on every body pass of the presenter, and `@State` throws the new models away. The Join/Edit switch is the same in both files.
- Fix: Add one `FeedIdentitySheet(kind:repository:actions:)` view that owns its models in `@State`, and use it from both places.
- Confidence: Confirmed.

#### UIB-12: Price per litre or kWh is formatted twice, and the unit is hard-coded
- Severity: Low. Category: duplication / localization.
- Refs: `Carodo/Features/Garage/Views/FuelEntrySheet.swift:419`, `Carodo/Features/Garage/Views/FuelHistorySheet.swift:124`.
- What is wrong: Both files build `"\(Money.format(minorPerUnit:))/\(electric ? "kWh" : "L")"` as a verbatim string. The unit and its order are not in the String Catalog.
- Fix: Add a `DisplayFormat.unitPrice(minor:currency:energy:)` backed by a catalog entry such as `Garage.fuelUnitPrice` with a named placeholder.
- Confidence: Confirmed.

#### UIB-13: iCloud status uses system colours and a separate secondary style
- Severity: Low. Category: ui-consistency / accessibility.
- Refs: `Carodo/Features/Settings/Views/ICloudView.swift:195` (`.syncing: .blue`), `:158,:163`, `Carodo/Features/Backup/Views/BackupView.swift:142,151,162,164` (`.foregroundStyle(.secondary)`).
- What is wrong: `docs/design-system.md#contrast` says "A status is never the system's colour: always the token" and "a caption that steps back uses `textSecondary`". These screens use `.blue` for a status and `.secondary` for captions, which does not follow Increase Contrast tuning. Settings row tiles in system colours are allowed by the doc and are not part of this finding.
- Fix: Use `CarodoSurface.accent` or a status token for syncing, and `CarodoSurface.textSecondary` for these captions.
- Confidence: Confirmed.

#### UIB-14: iCloud status words and duplicated titles
- Severity: Low. Category: duplication.
- Refs: `Carodo/Features/Settings/Views/ICloudView.swift:177-181,201-212,244-255`.
- What is wrong: `ICloudHeader.title` and `ICloudStatusLabel.title` are near-identical switches. The header says "Synced just now" for anything under 60 s. The Settings row shows the raw relative date, for example "10 seconds ago", for the same state.
- Fix: Add one `CloudSyncStatus.title` and one "synced" formatter, and use them in both views.
- Confidence: Confirmed.

#### UIB-15: Garage empty state's Add button is not the primary CTA style
- Severity: Low. Category: ui-consistency.
- Refs: `Carodo/Features/Garage/Views/GarageView.swift:52-58`.
- What is wrong: The button uses `.borderedProminent` with `.tint(CarodoSurface.accent)`. The design system lists "Add vehicle" as a `.carodoPrimary` CTA, which is Copper with Charcoal text.
- Fix: Use `.buttonStyle(.carodoPrimary)`.
- Confidence: Confirmed.

#### UIB-16: Small leftovers
- Severity: Low. Category: clean-code.
- Refs and fixes:
  - `Carodo/Features/Feed/ViewModels/FeedItemPresentation.swift:50-62`: a bare `do { }` block with no `catch` and no `try`. Remove the scope.
  - `Carodo/Features/Feed/ViewModels/FeedViewModel.swift:249-252`: the prefetch task's `self?.prefetchTask = nil` can clear a newer task started after a refresh. Clear it only if it is still the same task.
  - `docs/design-system.md:596` names a component `FeedItemRow` that does not exist; the row is `FeedRow`. Fix the doc.
  - Outside my slice, noted in passing: `Carodo/Core/Formatting/DisplayFormat.swift:104-107`. The `clock` doc comment sits above `position()`.
- Confidence: Confirmed.

### Checked and fine

- **Feed privacy (P5, P9, ADR 0007):**
  - Rows show only part of day, a server-coarse `Ago` (hours or more, or "now"), duration, distance, tags, rain and an abstract shape. No place, route or exact time.
  - The invite row shows only the person's own drive.
  - The live-status clocks are the system's own.
  - The reader's own rows withhold reactions until the quarter after the drive (`heldOwnRows`).
  - No screen requires an account.
- **Feed load logic:** generation guards on the first page, page loads and reactions. Auto-retry backoff runs on the page's task. The offline and unavailable wording is split.
- **Widgets and CarodoShared:**
  - No `UIApplication.shared` or other app-only API.
  - The Live Activity carries no place, coordinate or vehicle name.
  - The clocks are `Text(timerInterval:)`, so nothing updates from the app.
  - The intents are not discoverable and act only through `DriveActivityActions`.
- **No forbidden patterns in the slice:** no `.repeatForever`, `DispatchQueue`, `Task.detached`, `try!`, `as!`, `@unchecked Sendable`, `isAccessibilitySize` or `Date()`. No large titles: every screen is inline, and the Passport and Feed use `TabTitleToolbarItem` as documented.
- **TimelineViews:**
  - Onboarding: `.animation(paused: isStill)`.
  - iCloud: 30 s, on screen only.
  - Developer: 1 s, Debug-only page.
- **Other screens:**
  - Garage list, vehicle detail and Places use `LoadFailedView`.
  - Vehicle detail hides Fuel when its read fails instead of saying "no fill-ups".
  - The Backup restore and decode path is `@concurrent`.
  - Help search is small and in-memory.

---

# Appendix A6

## Cross-cutting audit: design system, duplication, dead code, rules, tests, size

carodo-ios at `5772921` (main), with uncommitted changes in the working tree (config, entitlements, docs). Read-only.
Scope: the whole of `Carodo/`, `CarodoWidgets/`, `CarodoShared/` and `CarodoTests/`. I left out anything already
tracked in `carodo-handbook/plans/technical-debt.md` or in the 2026-11-12 audit. That audit's L02 (unused
`MetricTile`, `JourneyRow`, `StampRing`, `CarodoFilterMenu`, `LoginView`) and L08 (19 unused keys) are now fixed:
none of those names or keys remain. The "Known gaps" section of design-system.md already admits that spacing is
mostly written in place, so XC-9 only gives numbers.

Method: I grepped the source tree with `grep -rEn --include=*.swift`, leaving out `Carodo/Previews` and
`Core/PreviewData` where it matters. Three throwaway scripts (kept in the session scratchpad, not committed) did the rest:

- `keys.py` maps every catalog key to its generated symbol (`.Table.camelKey`), and also looks for the raw key
  and for dynamic prefixes.
- `dups.py` and `dups2.py` hash function bodies, first as written and then with identifiers renamed.
- A word-frequency pass finds declared members that are referenced only once.

---

### Medium

#### XC-1 — A drive photo's time is shown in the phone's zone, not the drive's (P3)
- **Severity** Medium · **Category** rule-violation · **Confidence** High
- **Where:** `Carodo/Features/Journeys/Views/Detail/JourneyDetailContextSections.swift:195`
  `Text(memory.at.formatted(date: .omitted, time: .shortened))`
- **What is wrong:** P3 and `docs/data-model.md#time` say a drive is shown in the zone it was recorded in.
  `DisplayFormat.clock(_:timeZone:)` (`Core/Formatting/DisplayFormat.swift:115`) is the one helper that does this.
  The photo tile beside the drive's own clock range uses the device zone instead.
- **Why it matters:** Open a drive recorded abroad, or across a DST change. The departure reads 08:12 in the
  drive's zone, while the photos taken on that drive read 14:12.
- **Fix:** `DisplayFormat.clock(memory.at, timeZone: journey.timeZone)`. Pass the zone into the memories section.
- **Related, lower risk:** these sites format drive-related dates with `Date.formatted` in the device zone and
  without the drive's zone:
  - `GarageView.swift:375` (last drive)
  - `PassportExplorationSection.swift:346,370` (last visit)
  - `PassportStampRow.swift:73-75`
  - `JourneyDayView.swift:192`

  A date is less sensitive than a time, but it can still be off by a day near midnight. Decide per site, and
  route through `DisplayFormat.day(_:timeZone:)` where the date is a drive's.

#### XC-2 — The Replay video's colours copy the share card's renderer instead of reusing it
- **Severity** Medium · **Category** duplication · **Confidence** High
- **Where:**
  - `Carodo/Features/Journeys/Views/Replay/ReplayVideoOverlay.swift:48-53` builds its ground as `UIColor(red: 30/255, green: 29/255, blue: 27/255)`, and its ink, `quiet` (alpha 0.72/0.68) and accent itself.
  - `Carodo/Core/Journal/ShareCardRenderer.swift:348-362` has the same values in `paper(isDark:)`, `ink`, `quiet(isDark:)` and `accent`. Its comment says the video uses the same ground.
- **What is wrong:** The "signature" palette is written down twice. The near-black ground (30,29,27) is in neither
  `CarodoColor` nor `CarodoSurface`.
- **Why it matters:** The video and the share card are meant to look like one brand (the overlay says "the same
  as a share card's"). Changing one renderer will quietly fork them.
- **Fix:** Make `ShareCardRenderer.ink/quiet/accent` non-private, or better, move them into a small
  `SignaturePalette(isDark:)` in `Core/Journal` or `DesignSystem`. Use it from both renderers, and give the
  ground a `CarodoColor` name.
- **Same kind of copy:** `Carodo/DesignSystem/Brand3D/Wheel3D.swift:42` has Copper written in as
  `UIColor(red: 189/255, …)`. Use `UIColor(CarodoColor.copper)`.

#### XC-3 — Cards are drawn by hand in about 30 places, in two surfaces, with three hairline strengths
- **Severity** Medium · **Category** ui-consistency · **Confidence** High
- **Where:**
  - `.carodoCard()` (`DesignSystem/CarodoSurface.swift:102`) fills `CarodoSurface.elevated` with a hairline at 60 %. It has 47 uses.
  - 31 sites fill `CarodoSurface.card` by hand instead (see the list below).
  - 13 sites under `Features/` stroke `CarodoSurface.stroke` themselves, at 100 % (9), 60 % (3) or 70 % (1), at 0.5 or 2 pt. For example `JourneyDetailContextSections.swift` (3), `FuelEntrySheet.swift` (2), `JourneyDetailSummarySections.swift`, `JourneyDayCalendar.swift`, `VehicleActionsSheet.swift`, `ArchiveVehicleSheet.swift`, `CarAudioRows.swift`.
  - 13 sites draw `CarodoSurface.elevated|card, in: RoundedRectangle(...)` by hand.

  The 31 hand-filled `.card` sites (count per file):

  | File | Sites |
  |---|---|
  | `LogEntryParts` | 2 |
  | `FuelEntrySheet` | 2 |
  | `UsernameEntry` | 2 |
  | `FeedRow` | 2 |
  | `PlaceEditorPanel` | 1 |
  | `MilestoneDetailView` | 1 |
  | `ShareFieldsPanel` | 1 |
  | `JourneyMergeSheet` | 1 |
  | `JourneyDetailView` | 1 |
  | `VehicleEditorView` | 1 |
  | `OdometerSheet` | 1 |
  | `NumberKeypad` | 1 |
  | others | about 15 |

- **What is wrong:** design-system.md says "a card's radius `.carodoCard()`" and "hairline borders 0.5 pt at
  60 % opacity on cards". In practice there are two card fills (`elevated` and `card`) and three hairline
  strengths. The radius values in use are spread out:

  | Radius (pt) | Uses |
  |---|---|
  | 14 | 25 |
  | 18 | 20 |
  | 20 | 10 |
  | 12 | 10 |
  | 16 | 8 |
  | 8 | 7 |
  | 24 | 6 |
  | others | 9 |

  The doc says "radii in use are 14–24", but 8 and 12 pt are also in use.
- **Why it matters:** Cards look slightly different from screen to screen in Light and Dark mode, and the
  60 % rule is not true in practice.
- **Fix:** Decide with the owner whether `card` is a second card level. If it is, add
  `.carodoCard(level: .raised)` or `.carodoInsetCard()`. Then move each hand-built card into the modifier when its
  file is next touched, and refresh the radius sentence in the doc. Do not do a mass rewrite, per the doc's own
  policy.

#### XC-4 — Small test gaps on non-UI logic that matters
- **Severity** Medium · **Category** test-coverage · **Confidence** Medium
- None of the types below has a test file, and no test names them (checked by type name across `CarodoTests`):
  - **`JournalUpkeep`** (`Core/Maintenance/JournalUpkeep.swift`, 78 lines). It holds badge and new-road upkeep after every journal change: one count at a time, "a change came while counting → count once more", and the "no work while driving" gate (`isDriving`). These are state transitions with a battery cost. Test them with a fake `JourneyRepository` and `BadgeRepository`.
  - **`BackendFeedTransport` / `BackendFeedSharing`** (`Core/Outbox/BackendFeedTransport.swift`). The mapping from nil status to retry, the acknowledge-on-delivered step, and `revokeShare → .delivered` are exercised only by `BackendLiveTests`, which is opt-in. A fake `APIClient` test would cover them, as AGENTS.md asks ("test with a fake HTTP client").
  - **`FeedAnswers`** (`Core/Networking/FeedAnswers.swift`). It holds the privacy rule "below the threshold only the warm-up, never a number" and the clamp on `warmup`. Only `LocalCommunityRepositoryTests` covers it, indirectly. `BackendCommunityRepository` has no test.
  - **`TripRecord` / `TripPointRecord`** (`Core/Persistence/TripRecord.swift`, 162 lines). These are the GRDB row mappings on the recording path. Repository tests probably round-trip them, but nothing names them. Confirm that a store test covers every column, including the nullable ones.
- **Checked, no action needed:**
  - `EnrichmentBackoff` is covered through `EnrichmentSchedulerTests:208`.
  - `StopRule` is covered through `RouteRecorderTests` and `StopDetector` tests.
  - Recovery (`TripRecoveryTests`, `TripReconciliationTests`), backup decoding (`BackupTests`, `ZipEntryTests`, `BackupFilesTests`) and sync (`CloudSyncServiceTests`, `CloudRecordCodingTests`) all have dedicated tests.

---

### Low

#### XC-5 — A disclosure chevron is drawn by hand 24 times in six styles
- **Severity** Low · **Category** ui-consistency / duplication · **Confidence** High
- **Where:** `Image(systemName: "chevron.right")` appears in 24 production files. Examples:
  - `PlaceVisitRow.swift:25`
  - `SettingsView.swift:131`
  - `PlacesView.swift:208`
  - `PassportExplorationSection.swift:218,298`
  - `MilestoneDetailView.swift:270`
  - `VehicleDetailView.swift:182`
  - `VehicleEditorView.swift:264`
  - `FuelSection.swift:83`
  - `OdometerSection.swift:70`
  - `JourneyContextSection.swift:124`

  The styles in use:
  - Fonts: `.footnote.weight(.semibold)` (15), `.caption2.weight(.bold)` (4), and `.footnote.medium`, `.caption.semibold`, `.caption2.semibold` once each.
  - Colours: `textSecondary` (14), `textSecondary.opacity(0.7)` (2), `.opacity(0.6)` (1), `.tertiary` (1), `accent` (1).
- **Why it matters:** List rows disagree from screen to screen. The faded variants (XC-6) also go against the
  contrast rule.
- **Fix:** Add a `DisclosureChevron()` view in `DesignSystem/Components` (footnote semibold, `textSecondary`,
  hidden from accessibility) and adopt it file by file.

#### XC-6 — Text and icons faded with opacity, against the contrast rule
- **Severity** Low · **Category** ui-consistency · **Confidence** High
- **The rule:** design-system.md, Contrast: "Text is never faded with opacity below these… uses
  `textSecondary` as it is".
- **Where:**
  - **Text:**
    - `RecordingExpandedPanel.swift:420`: `textPrimary.opacity(0.8)`.
    - The placeholder "0" at `textSecondary.opacity(0.5)` in `OdometerSheet.swift:76`, `FuelEntrySheet.swift:379` and `ExpenseEntrySheet.swift:132`. The same pattern appears three times.
  - **Icons:**
    - `VehicleDetailView.swift:184`, `VehicleEditorView.swift:266`, `PlacesView.swift:210`, `MilestoneDetailView.swift:282`, `RecordingRequirementsView.swift:118`, at 0.6–0.8.
    - `JourneyDetailContextSections.swift:195`: a caption at `.opacity(0.8)` on media.
  - **Decorative fills, which are acceptable:** 37 `textSecondary/textPrimary.opacity(...)` sites in total, most of them fills and dashes.
- **Why it matters:** Text faded this way falls below 4.5:1 on Ivory, and it ignores Increase Contrast.
- **Fix:** Use `textSecondary` as it is. For the placeholder "0", either accept `textSecondary` as the placeholder
  colour or record an exception in the doc. Put the placeholder in one helper inside `LogEntryText` or
  `NumberKeypad`.

#### XC-7 — A fixed-size 52 pt figure ignores Dynamic Type
- **Severity** Low · **Category** ui-consistency · **Confidence** High
- **Where:** `Carodo/Features/Garage/Views/OdometerSheet.swift:74`: `.font(.system(size: 52, weight: .semibold, design: .rounded))`.
- **What is wrong:** design-system.md, Typography, allows fixed point sizes only for SF Symbols in fixed controls.
  `PassportHeader.swift:18` shows the pattern to follow: `@ScaledMetric(relativeTo: .largeTitle)`.
- **Other fixed sizes checked:**
  - These 21 are symbols inside fixed-size marks and buttons: `StopMapMarkers`, `PlaceStyle`, `MapControlButton`, `MilestoneDetailView:246`, `JourneyMapPinContent:28` and others.
  - The two in `RecordingExpandedPanel` are already `@ScaledMetric`.
- **Fix:** Use `@ScaledMetric(relativeTo: .largeTitle) var readingSize = 52`, and check the sheet at xxxLarge.
  `.minimumScaleFactor` may be needed for long readings.

#### XC-8 — Animations that skip Reduce Motion
- **Severity** Low · **Category** ui-consistency · **Confidence** Medium
- **The rule:** design-system.md:518 says "any new animation that moves layout" turns off under Reduce Motion
  (`Animation.carodo(_:reduceMotion:)`).
- **Where:** these files animate with a raw curve and never read `accessibilityReduceMotion`:

  | Site | What it animates |
  |---|---|
  | `RootView.swift:22` | onboarding → app, 0.45 s |
  | `PlaceEditorView.swift:84` | `withAnimation(.easeInOut(0.25))` on the map camera; design-system.md:190 says the camera moves without easing under Reduce Motion |
  | `JourneyDayView.swift:88` | |
  | `FeedProfileSheet.swift:154` | |
  | `ShareFieldsPanel.swift:142` | |
  | `AtlasLocationMarkers.swift:72` | cone rotation |
  | `MapStatusViews.swift:25` | |
  | `OdometerSheet.swift:78` | digits; `.rollingDigits` exists for this |

  Some of these only change opacity or colour, which is fine. PlaceEditorView, RootView and AtlasLocationMarkers move things.
- **Fix:** Wrap the movement cases in `.carodo(_, reduceMotion:)`. Use `.rollingDigits` in OdometerSheet.

#### XC-9 — The spacing and radius tokens are rarely used, and the doc's numbers are stale
- **Severity** Low · **Category** ui-consistency · **Confidence** High
- **Counts:**
  - 463 raw `.padding(n)` / `.padding(.edge, n)` and 578 raw `spacing: n` across the app, against 102 `CarodoSpacing.` uses.
  - Off-grid values are common: 14 (43), 10 (32), 6 (31), 5 (8), 9 (6).
  - Worst files (raw spacing numbers): `PlaceCard.swift` (37), `FuelEntrySheet.swift` (29), `MilestoneDetailView.swift` (24), `ReplayView.swift` (23), `JourneyDetailSummarySections.swift` (23), `GarageView.swift` (23), `FeedRow.swift` (22).
- **Doc drift:**
  - design-system.md:452 lists `CarodoSpacing (2, 4, 8, 12, 16, 24, 32, 48)`, but `CarodoSpacing.swift` stops at `xl = 32`. There is no 48.
  - "Known gaps" says "about 450 numbers", but the real count is about 1,040.
  - design-system.md:596 names `FeedItemRow`, but the type is `FeedRow` (`Features/Feed/Views/FeedRow.swift:6`).
- **Fix:** Fix the doc (add `xxl = 48` or drop it from the doc, update the count, rename FeedItemRow), and keep the
  policy of converting only touched files. A `CarodoRadius` token, or more `.carodoCard(cornerRadius:)`, would
  cover the radii spread in XC-3.

#### XC-10 — Dead and speculative code in production
- **Severity** Low · **Category** dead-code · **Confidence** High
- **Used only by tests** (no production reference; a word-frequency pass, then grep):
  - `PrivacyZone.hidingEnds(of:)` (`Core/Domain/Places/PrivacyZone.swift:23`). Production calls `PrivacyZone.cutting` directly (`ShareCardModel.swift:97,105`). `PrivacyZoneTests` exercises only the wrapper. Move the tests to `cutting`, then delete the wrapper.
  - `LocalCache.maximumAgeS` (`Core/Maintenance/LocalCache.swift:30`). No reference anywhere, tests included. The per-case constants it switches over are used directly.
  - `ShareCardRenderer.veilMask(around:size:)` (`:160`), `HistoryAtlas.currentStatistics()` (`:289`), `BadgeState.forgettingAccount(at:)` (`Achievements.swift:342`), `CarConnections.unlinkedPort` (`:238`), `RouteRecorder.waitingCount` (`:266`), `DrivingDynamics…validWindowShare` (`:159`), `GRDBCloudSyncStore.pendingChanges()` (`:31`). Each is a test-only accessor. They are acceptable if they exist as test seams; otherwise remove them, or mark them clearly.
- **Never used:** `VehicleIdentityPresentation` (`DesignSystem/Components/VehicleIdentity.swift:6`) has cases `.photoHero` and `.replay3D` and an unused `presentation:` parameter, and every case draws the emblem. This goes against "nothing left unused". Delete it until the photo or 3D work starts.
- **Documented, not wired:** `FrequentPlaceDetector` (`Core/Domain/Places/FrequentPlaces.swift`, 174 lines). Only its tests call it. `docs/specs/places.md:22` says "Nothing calls the detector yet". This is listed for awareness only; it is intentional.

#### XC-11 — `TripWriter` has the only `deinit` that is not `nonisolated`
- **Severity** Low · **Category** rule-violation · **Confidence** Medium
- **Where:** `Carodo/Core/Recording/TripWriter.swift:117` `deinit { continuation.finish() }`. `TripWriter` is a
  main-actor class (`final class`, default isolation).
- **The rule:** AGENTS.md (Concurrency) and architecture.md:443 say "Every main-actor class declares
  `nonisolated deinit {}` (or makes its deinit `nonisolated`)". Every other class in the tree complies.
- **Runtime risk:** this depends on whether the compiler makes the deinit isolated. If it did, `task warnings`
  (the otool `deinitOnExecutor` scan) would fail, and I did not run a build to check. The body touches only a
  Sendable `let` (the `AsyncStream.Continuation`), so marking it `nonisolated deinit` is safe and matches the
  rule. It sits on the recording path.

#### XC-12 — Small logic duplicates
- **Severity** Low · **Category** duplication · **Confidence** High
- **"Today / Yesterday / else date":** written twice, in `Features/Garage/Views/GarageView.swift:370-375`
  (`lastUsedLine`) and `Features/Garage/Views/LogEntryParts.swift:7-13` (`LogEntryText.time`). Extract one
  `DisplayFormat.relativeDay(_:now:calendar:)` that takes the per-case strings, or a closure.
- **The vehicle picker's `check`/`checkmark` view:** identical in `Features/Drive/Views/VehiclePickerSheet.swift:111`
  and `Features/Journeys/Views/Editing/JourneyVehiclePickerSheet.swift:187`. Both sheets build the same
  `VehicleCard` row, divider and add-row in a card. A shared `VehicleChoiceList` in DesignSystem (`VehicleCard` is
  already there) would remove both copies.
- **The fuel and expense models:** `FuelEntryModel.save()` (`:220`) and `ExpenseEntryModel.save()` (`:71`) are the
  same 10 lines. So are `FuelEntrySheet.save` (`:430`) and `ExpenseEntrySheet.save` (`:217`). They are small, but
  `LogEntryParts.swift` already exists for exactly this kind of sharing.
- **Infinite-scroll prefetch:** `FeedViewModel.itemAppeared` (`:247`) and `JourneysViewModel.journeyAppeared`
  (`:484`) are the same body. This is borderline, and acceptable at two copies.
- **Map control buttons:** `MapAtlasView.swift:661-676` (layers button) and `MapStatusViews.swift:6-27`
  (`MapAutoModeButton`) each rebuild the 44 pt symbol button that `MapControlButton` provides, with the same
  17 pt semibold symbol. Either extend `MapControlButton` with a "prominent/tile" style and a busy state, or
  record why they differ.

#### XC-13 — Answers after an `await` in View-level `Task {}` that is not kept
- **Severity** Low · **Category** clean-code (AGENTS self-review "An answer after an await belongs to its request") · **Confidence** Medium
- **Counts:** 123 `Task {` in `Features/*/Views` and `App`. Most are button actions whose result only sets an
  error flag, which is fine. Two write navigation state after an `await` with no cancel and no request check:
  - `JourneyDetailView.swift:482`: `onOpenVisits` → `Task { if let page = await model.visitsPage(forPoint: id) { visitsPage = page } }`. If a person taps two points quickly, the slower answer can open the wrong page.
  - `JourneyDetailView.swift:730-735`: share. `sheet = .shareCard(...)` is set after two awaits (`privateCircles`, `shareRoute`), so the sheet can open after the person has left the page or opened something else.
- **Fix:** Keep the task in `@State`, cancel it on a new request or on disappear, and check `Task.isCancelled` or
  the request id before assigning. The other UI auditor may report the same lines; this is the tree-wide pattern.

#### XC-14 — Files over 600 lines
- **Severity** Low · **Category** clean-code · **Confidence** High

  | Lines | File | Possible split |
  |---|---|---|
  | 1039 | `Core/Recording/DriveSessionManager.swift` | One class. Its tracking state is deliberate ("the one session state"). Extensions by concern (`+Stops`, `+Finish`, `+Inputs`) would follow the `DependencyContainer+…` pattern. |
  | 1007 | `Core/Replay/ReplayTimeline.swift` | Already three `extension ReplayTimeline` blocks (`:131`, `:558`, `:707`). Move each to `ReplayTimeline+<Concern>.swift`. |
  | 966 | `Features/Map/Views/AtlasMapView.swift` | 8 types: `AtlasMapState`, `AtlasOverlaySync`, configuration and command structs, and a 575-line `AtlasMapCoordinator` (`:204`). Move the coordinator to `AtlasMapCoordinator.swift`, as `JourneyMapCoordinator` already is. |
  | 933 | `Features/Journeys/Views/Detail/JourneyDetailView.swift` | Its sections are already partly split out (`JourneyDetail*Sections.swift`). The 680-line extension (`:253`) holds actions and sheets. |
  | 922 | `Features/Map/Views/MapAtlasView.swift` | One View of about 860 lines: controls column, layers popover, status, sheets. Split out `MapControlsColumn` and the sheets. |
  | 808 | `Features/Journeys/ViewModels/Detail/JourneyDetailViewModel.swift` | |
  | 697 | `Core/Diagnostics/TrackingLog.swift` | |
  | 655 | `DesignSystem/Brand/CarodoMarkGeometry.swift` | Geometry data. Fine. |
  | 652 | `Features/Journeys/Views/Detail/JourneyMapCoordinator.swift` | |
  | 651 | `Features/Map/ViewModels/MapAtlasViewModel.swift` | |
  | 612 | `Core/Persistence/GRDBVehicleRepository.swift` | |
  | 606 | `Core/Persistence/DatabaseManager.swift` | `v1_initial`. Fine. |

  Test files: `AutoModeTests.swift` (1082), `ReplayTimelineTests.swift` (780), `AtlasMapViewTests.swift` (733),
  `DriveSessionPersistenceTests.swift` (632).
- **Highest value:** `AtlasMapView` (move out the coordinator) and `MapAtlasView` (one huge body). Map is the
  screen that "has not been reviewed yet" per design-system.md, Known gaps.

---

### Checked and fine

- **Banned constructs in production:** none of `try!`, `as!`, force unwraps (pattern scan), `DispatchQueue`, `Task.detached`, `@unchecked Sendable`, `ObservableObject`, `@Published`, `import Combine`, `print(`, `NSLog(` or `fatalError(`.
  - The 4 `preconditionFailure` calls are programmer-error guards: hard-coded URLs and the container injection.
  - Tests have 2 `try!`, 1 `DispatchQueue` and 16 `print`. Test-only, not a rule there.
- **`@MainActor`:** 97 uses, all on closure types that cross nonisolated boundaries, plus `AppIntent.perform`. None is on a view, view model or service type.
- **`nonisolated deinit`:** present on every class in the tree except `TripWriter` (XC-11).
- **`Date()` / `.now` in `Core/Tracking`:** none. The engines take `now` injected. Wall-clock reads are only in adapters (`Core/Location`, `Core/Motion`) and in log timestamps in Recording.
- **Forbidden UI patterns:** no `.repeatForever`, no `isAccessibilitySize`, no `.navigationBarTitleDisplayMode(.large)`, no system `.orange`, `.green` or `.red` used as a status, and no `Color(red:)` outside the palette files. The exceptions are XC-2, Brand3D's SceneKit lights and `UIColor` lights.
- **Localization:** every key in all 14 app catalogs and the widget catalog maps to a generated symbol or a raw/dynamic reference: 0 unused keys out of about 1,450.
  - No hard-coded `Button("…")`, `Label("…")`, `navigationTitle("…")`, `accessibilityLabel("…")` or `String(localized: "…")` outside Developer.
  - The 4 `Text("…")` sites are interpolations of already-localized or verbatim parts (`JourneyCards.swift:149,158,179`, `JourneyDayCalendar.swift:55`).
- **Dead design-system types:** none. Every type in `DesignSystem` and `CarodoShared` has a production reference, either directly or through its style or modifier shorthand (`.carodoPrimary`, `.inline`, `.feedShape`, `.collapsesFloatingBar`). The only exception is `VehicleIdentityPresentation` (XC-10).
- **Geo:** one haversine and one Earth radius (`Core/Domain/Geo.swift`). `CLLocation.distance(from:)` appears only in the Core Location adapter.
- **Formatters:** no `DateFormatter`, `NumberFormatter` or `MeasurementFormatter` outside `Core/Formatting`, except `Core/Backup/BackupFile.swift:130`, a file-name timestamp, which is acceptable.
- **Shared building blocks:** share sheets go through `ActivitySheet` or `ShareLink`. Empty and failed states use `ContentUnavailableView`, `LoadFailedView` and `JourneyEmptyState`, with no parallel copies.
- **Extension safety:** `CarodoShared/` and `CarodoWidgets/` contain no `UIApplication`, no raw colours or fonts and no literal `Text`.
- **Exact duplicates:** the function-body hash found only XC-12 (`save`, `mostDriven`/`mostDrivenTitle` in Passport). The last is a 5-line copy between `PassportRecordTitles.swift:4` and `PassportHighlightsSection.swift:269`; make one call the other.

---

# Appendix A7

## Backend audit: carodo-app (read-only, 2026-11-20)

Scope: `apps/api/src` (routes, http, services, lib, jobs, rpc), `apps/api/migrations/0001_baseline.sql`,
`apps/api/wrangler.jsonc` (rate limits, environments), `apps/web/src`. Compared with
`carodo-ios/docs/api/carodo-api.yaml` (the backend keeps no copy in `docs/api/`, see API-9).
These were already tracked and are not reported again: APP-01…06 (backend-source-audit.md), TD-73
(an out-of-window revision), TD-74 (an empty item left after a refused publish), TD-75 (the own item
missing on page 2), TD-76 (Stop sharing and `hidden_at`), KL-6, KL-7, TD-48 (contract YAML), and the
DeviceCheck TODO (`docs/architecture.md`). Paths are relative to `carodo-app/`. I ran no commands
other than reads.

---

### API-1 · Medium · privacy (P9)
**A drive edit changes the Feed at the moment it arrives, not at a quarter hour.**
- `apps/api/src/services/drives/publish.ts:78`: when a drive is already visible, a new revision
  keeps the old `visible_at` (the `CASE`). It still overwrites `ended_at`, `local_date`, `item_id`
  and the figures.
- `apps/api/src/services/drives/publish.ts:108` and `apps/api/src/services/feed/items.ts:44`:
  `refreshAfterPublish` runs in the same batch and sets `feed_items.last_ended_at` from the
  drive's new `ended_at`. The check `visible_at <= quarter` passes because `visible_at` is the old
  one.
- `apps/api/src/routes/feed.ts:19`: the shared first page is rebuilt every 30 s inside a quarter.
  `DRIVES_SQL` (`services/feed/read.ts`) shows the new figures and age straight away.

**Scenario:** a drive is visible since 10:15 (it ended at 10:00). The device sends revision 2 with
`endedAt` 11:30 at 11:31, for example after a resume or merge, or a late Auto Mode end that extends
the trip. Within 30 s, every reader sees the item move to the top with "now" and the longer
duration. A new `localDate` also counts: a brand-new item appears, since `refreshAfterPublish` also
refreshes `local_date = ?2`. The arrival moment is exactly what `visibleAt()`
(`services/shared/coarse-time.ts`) is designed to hide: "that moment minus a known delay would tell
the end to the minute". It also contradicts the doc comment in `items.ts` ("never when one is
published").

**Fix:** keep the old `visible_at` only when the revision does not move `ended_at` later or change
`local_date`. Otherwise give it `visibleAt(new endedAt, now)`. Or keep showing the old figures until
the next quarter.

**Confidence:** Confirmed for the server mechanism. Whether the app sends a later `endedAt` for an
already-published trip is Plausible (merge, resume).

### API-2 · Medium · security (abuse)
**One attested device can claim any number of accounts and usernames.**
- `apps/api/src/routes/accounts.ts:25`: the only cap is `RL_CLAIM` at 5 a minute per key
  (wrangler.jsonc). It is counted per Cloudflare location and is eventually consistent, as
  `http/rate-limit.ts` itself says. That allows about 7,200 claims a day per key.
- `apps/api/src/services/accounts/claim.ts:60`: `deviceCheckToken` is accepted unread (the tracked
  TODO).
- `http/rate-limit.ts` says "An exact count (claims per key and per device, ADR 0009) lives in D1
  with the rule that needs it". No such count exists: `claimAccount` never counts the accounts
  whose sessions use `app_key_id`.
- The contract's `403 claim limit reached` is never returned (see API-7).

**Scenario:** one real iPhone, or any software key on staging where `APP_ATTEST_DEBUG=1`, scripts
claims and squats thousands of usernames. Each held name then blocks reuse for 90 days on deletion.

**Fix:** before the insert, add an exact per-key cap in the claim's own statement:
`WHERE (SELECT count(*) FROM sessions WHERE app_key_id = ? …) < N`, or a `claims` counter row. This
needs an index on `sessions (app_key_id)`, a schema change (P6). It is independent of DeviceCheck.

**Confidence:** Confirmed.

### API-3 · Medium · performance / bug
**Pruning `sessions` and `auth_challenges` is capped at 1,000 rows an hour, below what they can grow
by.**
- `apps/api/src/services/jobs/prune.ts:12`, `:30` and `:34`: at most 24,000 deletions a day per
  table.
- `apps/api/src/services/auth/sessions.ts` (`refreshSession`): every refresh inserts a new
  `sessions` row and keeps the rotated one until its `expires_at`, 90 days after creation.
- `apps/api/src/services/auth/challenges.ts:24`: every unauthenticated
  `POST /v1/auth/challenge` writes a row. Its only limit is `RL_AUTH` per IP and location, 30 a
  minute.

**Scenario:** 15-minute access tokens give an active user many refreshes a day. Each makes a row
that lives 90 days. Around 1,000 daily users at about 25 refreshes a day already outpace the prune,
so the table and its index grow without bound. Separately, a botnet or IPv6 rotation can write
challenge rows faster than 1,000 an hour, and D1 bills every write.

**Fix:**
- Prune a rotated row soon after rotation, for example `revoked_at <= now - 30 d`, using a partial
  index. The reuse window can be shorter than 90 days.
- Raise or loop the per-table batch within the run's budget (C10 allows a bounded loop across runs,
  not per run).
- Consider HMAC-stateless challenges, which need no row.

**Confidence:** Plausible. The volume depends on how often the app refreshes.

### API-4 · Low · privacy (P9)
**Changes to the Feed and stats outside the hide exception land mid-quarter.**
- `apps/api/src/services/accounts/sharing.ts` (Stop sharing) and
  `apps/api/src/services/accounts/lifecycle.ts` (delete) remove drives and items at once.
- The first page (30 s buckets) and stats (5 min buckets, `routes/feed.ts`) are recomputed within
  the quarter.
- `CommunityStats.drivers` and `warmup` (`services/feed/stats.ts`) therefore drop at a minute-level
  moment.

P9's exceptions name only "a person hiding their own drive". Deleting an account or stopping
sharing is arguably the same intent, but it is not written down.

**Fix:** add these two acts to the P9 exception list in AGENTS.md and ADR 0007, or nothing in code.

**Confidence:** Confirmed (a docs gap).

### API-5 · Low · security
**`POST /v1/feed/drives/{tripId}` and `DELETE` let any member plant a tombstone for any trip id they
can guess.**
- `apps/api/src/services/drives/publish.ts`, `unpublishDrive`: the insert runs without a prior row
  and gives the caller ownership.
- The owner's later PUT then gets `404` until the tombstone is pruned (7 days).

Trip ids are device UUIDv4 values and appear only in the author's own `tripIds`, so exploitation
needs a leaked id. Each tombstone is also a row written per request, capped only by `RL_WRITE`.

**Fix:** a tombstone created without a prior row could be owned by nobody: match on `trip_id` only
when the first PUT arrives from the same account. Or accept this as known.

**Confidence:** Confirmed mechanism, low likelihood.

### API-6 · Low · contract
**`PUT /v1/me/profile` returns 400 `username_invalid` for an invalid name.**
- `apps/api/src/services/accounts/usernames.ts:56`.
- The contract for this operation lists 409, 422 and 429, with no 400. `POST /v1/accounts` does
  document 400.

**Fix:** list 400 `username_invalid` on `PUT /v1/me/profile`, or say what the 422 is for. It is
currently never returned.

**Confidence:** Confirmed.

### API-7 · Low · contract
**`POST /v1/accounts` limit codes do not match the contract.**
- The contract says `403 Device banned or claim limit reached` and lists no 429.
- The server answers 429 `rate_limited` from `RL_CLAIM` and `RL_AUTH` (`routes/accounts.ts:21`
  and `:25`), and never 403.

The app may branch on 403 to show "limit reached".

**Fix:** add 429 to the contract, or map the claim limit to 403 once API-2 exists.

**Confidence:** Confirmed.

### API-8 · Low · contract
**Username suggestions are offered only for `taken` names.**
- The contract says "a taken or reserved name may carry suggestions".
- `apps/api/src/routes/accounts.ts:53` suggests only for `taken`.

**Fix:** reword the contract ("a taken name"), or suggest for `reserved` too, unless reserved
because it contains "carodo".

**Confidence:** Confirmed.

### API-9 · Low · contract / docs
**The backend has no contract copy.**
- AGENTS.md (root, recipes) says "then the backend's copy and both implementations". There is no
  `carodo-app/docs/api/carodo-api.yaml`, and `find` shows none in the repo.

**Fix:** state that the iOS file is the only copy, or add the copy and a check that keeps them
equal.

**Confidence:** Confirmed.

### API-10 · Low · security (web hardening)
**`carodo-web` sends no security headers.**
- No CSP, `X-Content-Type-Options`, `frame-ancestors`/`X-Frame-Options`, `Referrer-Policy` or HSTS
  (`apps/web/src/app.tsx`; nothing matches in `apps/web/src`).
- The production analytics script loads from `https://t.linkto.so/t.js` without SRI
  (`apps/web/src/layout.tsx:96`).

There is no user content today, so XSS risk is low. Share pages (planned) will render user-supplied
vehicle labels.

**Fix:** use Hono `secureHeaders()` with a CSP allowing self, the inline hashes and t.linkto.so,
before share pages ship.

**Confidence:** Confirmed.

### API-11 · Low · duplication
**Hex encoding is written twice.**
- `apps/api/src/services/auth/sessions.ts:30` (`hashSecret`).
- `apps/api/src/services/accounts/usernames.ts:122` (`usernameHoldHash`).

**Fix:** add a `toHex(bytes)` beside `toBase64Url` in `lib/encoding/bytes.ts`.

**Confidence:** Confirmed.

### API-12 · Low · duplication
**Reaction counts are folded with the same loop twice.**
- `apps/api/src/services/feed/read.ts:114` (`sharedPage`).
- `apps/api/src/services/feed/read.ts:164` (`readerPage`).

**Fix:** extract `countsByItem(rows)`.

**Confidence:** Confirmed.

---

### Checked and fine
- **Tokens.** HMAC tokens with labels derived per kind (HKDF) and constant-time `subtle.verify`.
  Expiry is parsed after verification, length is capped, and a guest token cannot pass as an access
  token.
- **Account secret login.** A missing account and a wrong secret take the same work (hash first,
  `bytesEqual`). The session insert is guarded by the current `secret_hash`. Refresh rotation and
  revocation run in one batch (APP-01 holds). A refresh token presented by another key revokes the
  family.
- **App Attest attestation.** Chain to the pinned root, with validity and signature algorithms. The
  nonce is bound to the consumed single-use challenge (consumed before verification). The key id is
  the hash of the public key. rpIdHash, counter 0, AAGUID versus the allowed environments,
  credential id, and the validation category are all checked. `carodo-debug` is impossible in
  production whatever the var says. Refusal reasons are constant categories (APP-03 holds).
- **Assertions.** They sign method, path with query, and the body hash. The counter is checked
  before the conditional `counter < ?` update, so racing replays fail. The token and the assertion
  must name the same key.
- **Authorization and IDOR.** Every write is scoped by `caller.accountId` from the session:
  publish (`ON CONFLICT … WHERE drives.account_id = excluded.account_id`), unpublish, reactions
  (keyed on reader and item), profile, sharing and delete. `tripIds` only reach the author. No
  author id is in any response, and item ids are random.
- **SQL.** Everything is bound. The only interpolations are constants (`VISIBLE`, `ITEMS`, the
  `RELEASE_BATCH`, `prune` table names from a fixed list, the `SessionGuard` SQL from code). Id
  lists travel through `json_each`.
- **Input bounds.**
  - Bodies are streamed with a cap (APP-02 holds).
  - Base64 and string lengths are capped before decoding.
  - Drive input: rounding, ranges, labels (no control or bidi characters), shape points 8–64 in
    the unit box, recursive depth-limited geo-key rejection.
  - The CBOR decoder has a depth limit, length checks before allocation, no indefinite lengths and
    safe integers. The DER reader checks lengths against the input, with at most 4 length bytes.
  - The cursor is AES-GCM sealed with a length cap and is not forgeable. A Feed cache key only
    takes a cursor that opened.
- **Feed P9 basics.** `ended_at` is required on a quarter. `visible_at` is fixed at receipt to a
  later quarter. Ages are computed from `clock.quarter` on the shared page. Order is the quarter,
  then a random id. The cache key carries the quarter. Exact audit columns never appear in a
  response. The release job resumes from its cursor after a missed run.
- **Caching.** A guest page is `public` and a member's is `private` with `Vary: Authorization`. The
  shared cache never holds reader-specific data (the overlay is added after it). `caches.default`
  keys are under `/__cache/…`, reached only from the Worker.
- **Privacy in logs and analytics.** No account id, token, coordinate or IP. The rate-limit key uses
  `cf-connecting-ip` only as the limiter key. The metrics write the route pattern, not the URL.
  Erase and job details are counts only.
- **Account deletion.** It is one batch, guarded against a concurrent deletion. Erasure runs R2
  first, then a cascading row delete, with backoff. Username holds are HMAC-keyed.
- **Rename.** The limit and the hold are checked inside the UPDATE, and the follow-up statements
  are gated by `changes() = 1`.
- **Workers hygiene.** No floating promises: `waitUntil` is used for cache puts and scheduled work.
  Module-level maps are caches only (derived keys, in-flight computations). Indexes exist for every
  query read, and the FK child columns are indexed.
- **WebRpc** exposes only `ping`. Web pages render static copy through JSX escaping, and the inline
  JSON escapes `<`.
