# iOS source audit — 2026-11-07

`carodo-ios`, audited at `5d87ccf` (read-only, weighted toward recording, concurrency, persistence,
backup/sync and data/error states). All seven findings were confirmed against the code and fixed
the same day, one commit each, each with a regression test that failed on the old code first.

Commit links resolve once `carodo-ios` `main` is pushed (it was 7 commits ahead when this was
written). Device checks still outstanding are listed at the end.

| Case | What went wrong | Priority | Fix |
|---|---|---|---|
| [IOS-01](#ios-01--a-stale-gps-fix-ended-a-healthy-drive) | A stale GPS fix ended a healthy drive | P1 | [`c330b53`](https://github.com/tuanngo/carodo-ios/commit/c330b5367d8c23205222443175ad5b1c35e08641) |
| [IOS-02](#ios-02--a-damaged-track-crashed-the-app) | A damaged packed track crashed the app | P2 (was P1) | [`6bb4b46`](https://github.com/tuanngo/carodo-ios/commit/6bb4b46b7688daa95a8fcd91f56059daaae9d4dc) |
| [IOS-03](#ios-03--a-late-motion-answer-closed-the-next-window) | A late Motion answer closed the next detection window | P3 (was P2) | [`80fc2bc`](https://github.com/tuanngo/carodo-ios/commit/80fc2bcc20c8078fff9006befe95da9d362579d4) |
| [IOS-04](#ios-04--a-failed-read-became-wrong-cached-figures) | A failed track read became wrong, cached figures | P2 | [`561efe3`](https://github.com/tuanngo/carodo-ios/commit/561efe3567ed4ab1074ec9ebb21c2561a8907aab) |
| [IOS-05](#ios-05--a-remote-trim-left-the-drive-stale) | A trim from another device left the drive stale | P2 | [`c35a4e5`](https://github.com/tuanngo/carodo-ios/commit/c35a4e572da47128f7b7f6a8dac657c490398215) |
| [IOS-06](#ios-06--sync-lost-a-trips-vehicle-and-parent) | Sync lost a trip's vehicle and parent for good | P2 | [`d264e95`](https://github.com/tuanngo/carodo-ios/commit/d264e9508f019aa4bb12a330aa00d1aac540b75a) |
| [IOS-07](#ios-07--passport-said-no-drives-when-it-could-not-read-them) | Passport said "No drives yet" when it could not read them | P3 (was P2) | [`354dfaf`](https://github.com/tuanngo/carodo-ios/commit/354dfafaf8156bdd1f0a764e97e0a7df1060d8eb) |

## Patterns to avoid

The seven cases come down to five habits. They are binding as self-review checks in
`carodo-ios/AGENTS.md` (Conventions, Self-review;
[`eb6417d`](https://github.com/tuanngo/carodo-ios/commit/eb6417d)); this section keeps the reasons.

1. **Validate before you mutate.** Every consumer of an input sees it only after the one gate that
   decides whether it is valid, not before (IOS-01). Order matters: a second consumer placed above
   the gate silently accepts what the gate rejects.
2. **Untrusted bytes get bounds, never conversions that trap.** Anything from a file, iCloud or the
   network is checked against what the payload can actually hold before it sizes an allocation;
   `Int(x)` on a foreign `UInt64` and unbounded decompression are crashes waiting (IOS-02).
3. **An answer after an `await` belongs to the request that asked.** A task whose result writes
   shared state is kept, cancelled when its owner ends, and checked after the `await` (IOS-03).
   Main-actor isolation does not stop interleaving across a suspension.
4. **Unknown is not zero, and a fallback is not a fact.** A failed or pending read hides what it
   would have shown; it never shows a value computed from a substitute ("0 drives", speed bands
   from a simplified route), and it is never cached as a success (IOS-04, IOS-07). `try?` that folds
   "absent" and "failed" into one `nil` is the usual cause; tell them apart.
5. **Remote changes follow the same path as local ones.** An edit arriving from another device
   must trigger exactly what the same edit made locally triggers (derivation, cache resets), and
   records may arrive in any order, so a reference to something not here yet is kept, not dropped
   (IOS-05, IOS-06). Test sync with two in-memory databases and out-of-order batches.

## IOS-01 · A stale GPS fix ended a healthy drive

- **What happened:** `DriveSessionManager` passed every fix to `StopDetector` before
  `RouteRecorder` checked its age. An accurate fix 12 minutes old (iOS can hand back a cached one)
  moved `lastUsableFixAt` back, and the next auto-finish check ended the drive as `noSignal` at that
  old time. A late fast fix could also clear a confirmed stop.
- **Why it slipped:** the recorder's freshness gate looked like the gate for everything; the stop
  detector sat above it and had none of its own.
- **Fix:** the session feeds the detector only fixes `RouteRecorder.Configuration.isTimely`
  accepts (one shared check), and the detector ignores a fix no newer than the last it took, which
  also covers the recovery replay path.
- **Guarded by:** `DriveSessionManagerTests` `testAnOldCachedFixNeverEndsAHealthyDrive`,
  `testALateFastFixKeepsTheStop`, `testAFixFromTheFutureNeverHoldsOffTheNoSignalEnd`;
  `StopDetectorTests` `testALateFixNeverSetsTheNoSignalClockBack`, `testAnOutOfOrderFastFixKeepsTheStop`,
  `testTheFirstFixAtTheDrivesStartCounts`.
- **Avoid:** pattern 1. When a pipeline has several consumers of one sample, put the shared
  validity check first and name it once.

## IOS-02 · A damaged track crashed the app

- **What happened:** `TrackCodec.decode` converted the header's `UInt64` count with `Int(count)`
  and reserved that much memory before checking the body; the zlib body unpacked without limit. A
  damaged `.carodo` file or iCloud record trapped (`Not enough bits to represent the passed value`,
  reproduced) instead of failing.
- **Why it slipped:** the decoder was written for tracks this app encoded; restore and iCloud made
  it read foreign bytes.
- **Fix:** the count must fit what the unpacked body can hold (7 bytes a point at least); unpacking
  streams and stops past the count's worst case or 64 MiB (`TrackCodec.maxUnpackedBytes`). A restore
  with a damaged track rolls back whole.
- **Guarded by:** `TrackCodecTests` `testACountNoIntCanHoldIsCorrupt`,
  `testACountTheBodyCannotHoldIsCorrupt`, `testATruncatedBodyIsCorrupt`,
  `testABodyThatUnpacksFarPastItsCountIsCorrupt`, `testADayAtOneHertzStillDecodes`;
  `GRDBBackupStoreTests` `testADamagedTrackFailsTheRestoreAndWritesNothing`.
- **Avoid:** pattern 2. Every decoder of stored or received bytes gets a "damaged input" test.

## IOS-03 · A late Motion answer closed the next window

- **What happened:** `AutoModeCoordinator.detectionStarted` asked Core Motion in an untracked
  `Task`. If window A timed out and window B opened before A's answer came back, A's "on foot"
  closed B and A's activity replaced B's (vehicle choice reads it).
- **Why it slipped:** main-actor code reads as sequential; the `await` in the middle is where
  another window can open.
- **Fix:** the task is kept, cancelled when its window ends or a new one opens, and its answer is
  dropped when cancelled (Core Motion itself does not stop).
- **Guarded by:** `AutoModeCoordinatorTests` `testALateMotionAnswerNeverClosesTheNextWindow`
  (a Motion fake that holds answers until the test releases them).
- **Avoid:** pattern 3. A fire-and-forget `Task { }` that writes state is a review flag.

## IOS-04 · A failed read became wrong, cached figures

- **What happened:** when Journey Detail could not read the raw track, it analysed the simplified
  display route instead and stored the result in `JourneyDetailCache`. A drive at 11 m/s read
  "100 % slow" with its stop uncounted, and reopening showed it again.
- **Why it slipped:** `try?` turned "no raw track exists" (sample data, where the route is right)
  and "the read failed" into the same `nil`.
- **Fix:** a read error leaves the raw-only sections out (speed bands, stops, elevation, what a trim
  left out), keeps the simplified route on the map, caches nothing, and the next open reads again.
- **Guarded by:** `JourneyTrimTests` `testATrackThatCannotBeReadLeavesTheAnalysisOutAndIsReadAgain`.
- **Avoid:** pattern 4. Never cache a fallback as if it were the real result.

## IOS-05 · A remote trim left the drive stale

- **What happened:** applying a trip fetched from iCloud updated its trim and parent but asked for
  no derivation when its track was already here, so the receiving phone kept the untrimmed
  distance (4.3 km in the test), speeds, route and end places. Joins and splits had the same gap.
- **Why it slipped:** the local trim, join and split each derive in their own flow; the sync path
  only knew "a new track arrived".
- **Fix:** a changed trim, or a part that arrives, joins or leaves, returns the affected drives for
  derivation; their end places and written summary are cleared and `recorder_version` set to 0 so a
  launch finishes the derive if the app ended first. Deriving is not an edit: nothing echoes back.
- **Guarded by:** `GRDBCloudSyncStoreTests` `testATrimMadeOnAnotherIPhoneDerivesTheDriveAgain`,
  `testAJoinMadeOnAnotherIPhoneDerivesTheDriveAgain` (split shares the join path; no test of its own).
- **Avoid:** pattern 5. Each local edit that derives something needs its remote twin and a
  two-database test.

## IOS-06 · Sync lost a trip's vehicle and parent

- **What happened:** a fetched trip whose vehicle or parent drive was not on the device yet had
  that link set to `nil` (the foreign keys forbade a dangling ID); when the record came in a later
  batch nothing reconnected it. An edit arriving before its vehicle also cleared a correct
  assignment, and a part arriving before its drive showed as a drive of its own.
- **Why it slipped:** ordering was sorted only within one batch, and the database constraint made
  "not here yet" look like "deleted".
- **Fix (owner decision: validate in the app, not the database):** `trips.vehicle_id` and
  `parent_id` have no foreign key (`v1_initial` edited; reinstall the app). Links are kept as they
  arrive; only a vehicle tombstoned here is let go. What the foreign key did on delete is now
  explicit: `applyDeletions` and deletes of never-synced trips clear the links
  (`GRDBJourneyRepository.freeParts`). Per-trip data (points, track, gaps) keeps its cascade.
- **Guarded by:** `GRDBCloudSyncStoreTests` `testATripThatArrivesBeforeItsVehicleKeepsIt`,
  `testAPartThatArrivesBeforeItsDriveJoinsItWhenItComes`,
  `testAPartThatArrivesAfterItsDriveDerivesTheDriveAgain`, `testDeletionsFromAnotherIPhoneLetGoOfTheirLinks`.
- **Avoid:** pattern 5. A new link between synced records is a plain ID column: check it where it
  is written, clear it where the other side is deleted, and never drop it because the target has
  not arrived.

## IOS-07 · Passport said "No drives" when it could not read them

- **What happened:** My Garage derived each car's totals from the journal facts, which start empty;
  while the journal loaded or after it failed, a car with drives read "No drives yet". The old test
  even asserted "every vehicle, with zero drives" on failure.
- **Why it slipped:** the garage was rightly kept visible on failure, and its numbers came along.
- **Fix:** `PassportViewModel.garageTotalsKnown` (journal loaded) gates the figures; the vehicle
  still shows. `-carodo.debugPassportFail YES` opens the failure state for screenshots.
- **Guarded by:** `PassportViewModelTests` `testTheGarageTotalsShowOnlyOnceTheJournalIsRead`,
  `testTheGarageShowsWhenTheJournalFails`, `testAnEmptyJournalKeepsTheGarage`.
- **Avoid:** pattern 4. When part of a screen stays up on failure, decide field by field what is
  still a fact.

## Still to check on a device

- IOS-01: a real Auto Mode drive with the app suspended for a while (cached fixes on resume).
- IOS-05 and IOS-06: two iPhones on one iCloud account, once CloudKit has been reviewed and
  deployed (`carodo-ios/docs/operations/cloudkit.md`).
- After IOS-06, reinstall the app on the simulator and the iPhone (schema edited in place).
