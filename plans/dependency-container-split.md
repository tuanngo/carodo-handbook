# DependencyContainer split

**Status:** done 2026-11-17 (carodo-ios `25469ef`, merged into main). Option A approved; open: TD-55 (gate as a type), PV-32 (recovery on a device). Runs beside
[`qa-hooks-out-of-views.md`](qa-hooks-out-of-views.md) (separate worktrees, file boundary below).

## Why (owner, 2026-11-17)

`Carodo/App/DependencyContainer.swift` is ~1,200 lines: the composition root, launch wiring, the
Feed's wiring, launch recovery, background maintenance passes, diagnostics logging and data erase in
one file. Every feature edits it, so it is hard to read and the file several sessions collide on
(AGENTS.md names it as a shared file). The goal is a file per concern, each readable on its own,
with no behaviour change.

## Task brief

```text
Outcome:
  DependencyContainer split by concern into files an agent can read on their own; same behaviour,
  same public surface, no new type unless the plan shows one is earned.

User story:
  As the owner (and as an agent adding a feature), I open the file for the concern I am changing
  (the Feed's wiring, launch recovery, a maintenance pass) and the composition stays in one place.

Existing behaviour (files read, as of carodo-ios 93c3df7):
  DependencyContainer.swift: stored properties and `Stores` (to ~160), `init` (~160–230),
  `live()` (~235, the composition; `#if DEBUG` sample container line), feed wiring
  (`feedMockURL`, `connectFeed`, `fixedFeedActions`, `feedActions`, ~340–440),
  `poiSearch(defaults:)` (`#if DEBUG`), `unsaved`, `inMemory`, `connect(appState:)` (~478–625, launch
  wiring incl. QA restore-backup and the journal seed), tracking mode, map data lookups,
  `flushForBackground`, `logAppLifecycle`, `reconcileAtLaunch` + `recoverUnfinishedTrips` (~693–784),
  an extension (~784–1160: joinWait, settleHeldTrips, tripReportFile, eraseLocalData, logMotion,
  logDrivingDynamics, logRide, recordMilestones, countNewRoads, enrichJourneys, matchPoints,
  healGaps, narrateJourneys, namePlaces), another extension (~1160), EnvironmentValues (~1189).
  Its 7 QA flag reads (feed mock backend, restore backup, …) are in scope here.
  Core/PreviewData/DependencyContainer+Samples.swift: the sample containers (Debug only).
  ArchitectureTests: `compositionRoot` exempts the prefix `Carodo/App/DependencyContainer`
  (any new `DependencyContainer+X.swift` in App/ is covered) and the Samples file.

Owner decisions needed (the plan proposes, the owner approves before code):
  1. The cut. Recommendation, extensions in App/ (no new types first):
     DependencyContainer.swift (properties, Stores, init, environment key),
     +Live.swift (live(), unsaved, inMemory, poiSearch), +Feed.swift (feed wiring),
     +Launch.swift (connect, reconcileAtLaunch, recovery, settleHeldTrips, joinWait),
     +Maintenance.swift (enrich, matchPoints, healGaps, narrate, namePlaces, milestones, new roads),
     +Diagnostics.swift (logMotion, logDrivingDynamics, logRide, tripReportFile, logAppLifecycle),
     +Data.swift (eraseLocalData, flushForBackground). The plan checks it against the code and
     the complexity budget (docs/architecture.md#complexity-budget).
  2. Private members an extension in another file needs: `private` → `fileprivate` does not cross
     files, so they become internal. Name each one widened in the plan; prefer moving the member
     with its only user.
  3. The 7 QA flag reads: gather into one `+QA+Debug.swift` with a Release twin, or keep each in its
     small `#if DEBUG` function (the rule since 2026-11-17)? Recommendation: the latter unless a
     flag sits in the middle of a flow.

Spec (Ready?) and mockups: no behaviour change; none.

Acceptance criteria:
  - No file of DependencyContainer over ~350 lines; each file's header says its concern.
  - No behaviour change: same tests pass unchanged (only moves; a test edited is named and justified).
  - Widened access listed in the report; nothing else starts using it.
  - docs/architecture.md (the App/ row and wherever DependencyContainer's parts are named) updated.
  - `task lint`, `task warnings`, `task test`, `task release-check` pass.

Non-goals:
  New abstractions, protocols or a DI framework; changing what is composed; the QA hooks in views
  (qa-hooks-out-of-views.md); Swift packages or new targets (P6).

Relevant files/docs:
  carodo-ios: App/DependencyContainer.swift, Core/PreviewData/DependencyContainer+Samples.swift,
  CarodoTests/Rules/ArchitectureTests.swift (compositionRoot), docs/architecture.md, AGENTS.md
  (Git: shared files).

Constraints:
  Moves only, in one commit per finished outcome; `nonisolated deinit {}` stays; Swift 6 main-actor
  defaults unchanged. Another session may edit DependencyContainer.swift: work in a worktree
  (`git worktree add ../carodo-ios-container-split -b refactor/container-split`), merge when done.

Validation commands/device checks:
  task generate && task lint && task warnings && task test && task release-check
  Simulator: a normal launch and -carodo.sampleData YES reach the Map. Device check: a Debug install
  launches and recovers an unfinished drive as before (launch recovery moved files).

Allowed scope:
  carodo-ios App/DependencyContainer*.swift, ArchitectureTests if a prefix changes, the docs above.

Do not:
  Touch the views' QA hooks (the other session's files); change behaviour while moving; commit
  another session's change (stage own paths only).
```

## Plan (approved by the owner 2026-11-17: the cut, option A, the QA functions)

Worktree `../carodo-ios-container-split`, branch `refactor/container-split`, from carodo-ios 93c3df7.

### Audit (what the code does today)

Read: `Carodo/App/DependencyContainer.swift` (1,215 lines, whole), `Core/PreviewData/DependencyContainer+Samples.swift`
(150), `App/DriveStarts.swift` (77, already an `extension DependencyContainer`), `CarodoTests/Rules/ArchitectureTests.swift`
and `Support/SourceTree.excluding` (a plain `hasPrefix`, so `Carodo/App/DependencyContainer+X.swift` is covered),
`project.yml` (`*+Debug.swift` / `*+Release.swift` excludes), `docs/architecture.md`, `docs/operations/setup.md` (line 109).

- **Swift constraint that shapes the cut:** stored properties cannot live in an extension, and `private` reaches only
  the same file. So every stored property stays in `DependencyContainer.swift`, and each `private` member that an
  extension in another file uses must become internal. There is no "these files only" access level in Swift.
- **Sizes today (approx.):** properties + `Stores` 158, `init` 71, `live()` 111, Feed wiring 95, `poiSearch`/`unsaved`/
  `inMemory` 36, `connect` 146, tracking mode + map data + flush 36, lifecycle 28, reconcile + recovery 90, joinWait +
  settleHeld 64, trip report 21, backup + erase + gate 52, motion/dynamics/ride logs 90, milestones + new roads 49,
  enrich/match/heal/narrate/name/provinces 110, `Logger.persistence` + environment keys 38.
- **QA reads: 8 `LaunchFlag` reads at 5 sites** (the brief said 7): `journeyPointServices` (2), `live()` feed mock (1),
  `connectFeed` mock seeding (3), `poiSearch(defaults:)` (1, inside its `#if DEBUG`), `connect` restore backup (1);
  plus `sampleContainer` in `live()`'s `#if DEBUG` and the `journalSeed` wait in `connect`. Release answers nothing.
- **Misplaced doc comments** (found while reading): the flush comment sits on `resumeMapDataLookups` (~633), the
  `enrichJourneys` comment on `joinWait` (~785) and on `badgeLedger` (~1015), the ride comment on
  `logDrivingDynamics` (~958). Moving re-attaches each to its member; no wording change.
- **Docs disagree with the brief:** `docs/architecture.md` has no `App/` row; the App/ line is in `AGENTS.md`
  (Architecture tree, and Git's shared-file list names `DependencyContainer.swift`).
- **The data-work gate** (`isErasingLocalData`, `activeDataWork`, `dataWorkWaiters`, `dataWorkFinished()`) is used by
  13 members that would land in 6 files: it is the main reason for the widened list below.

### Proposed cut (extensions in `Carodo/App/`, no new type)

| File | Holds | ~Lines |
|---|---|---|
| `DependencyContainer.swift` | class: every stored property (incl. `fixedFeedActions`, `launchReconciliation`, `lifecycleLogging`, moved up), `journeyPointServices`, `provinceSource`, `Stores`, `init`, `deinit`; `Logger.persistence`; environment keys | 285 |
| `+Live.swift` | `live()`, `feedMockURL` (its only user), `poiSearch(defaults:)`, `unsaved`, `inMemory` | 160 |
| `+Feed.swift` | `feedActions`, `latestCarDrive`, `weatherLookup`, `connectFeed`, the mock seeding | 100 |
| `+Connect.swift` | `connect(appState:)` (services, Live Activity, Auto Mode), `updateTrackingMode`, the restore-backup and journal-seed hooks | 175 |
| `+Recovery.swift` | `reconcileAtLaunch`, `recoverUnfinishedTrips`, `joinWait`, `settleHeldTrips` | 160 |
| `+Maintenance.swift` | `resumeMapDataLookups`, `purgeExpiredMapData`, `badgeLedger`, `recordMilestones`, `countNewRoads`, `enrichJourneys`, `matchPoints`, `healGaps`, `narrateJourneys`, `namePlaces`, `findProvincesCrossed` | 175 |
| `+Diagnostics.swift` | `logAppLifecycle`, `tripReportFile`, `logMotion`, `logDrivingDynamics`, `dynamicsEntry`, `logRide` | 135 |
| `+LocalData.swift` | `flushForBackground`, `backupService`, `canEraseLocalData`, `eraseLocalData`, `dataWorkFinished` | 80 |

Differs from the brief's cut: `+Launch` is split into `+Connect` (wiring, ~175) and `+Recovery` (reconciliation, ~160):
together they were ~330, at the 350 limit, and they are different readers (the device check names recovery alone).
`+Data` is named `+LocalData` (it is the local data's lifetime: flush, backup, erase). Each file opens with a doc
comment naming its concern. `DriveStarts.swift` stays as it is (outside the allowed scope).

### Access widened (`private` → internal, or `private(set)` → internal setter)

20 members, each with a doc line "internal for the container's own extensions": the gate `isErasingLocalData`,
`activeDataWork`, `dataWorkWaiters`, `dataWorkFinished()`; maintenance state `isEnriching`, `narrationSkips`,
`newRoadsTask`, `newRoadsRequested`, `newRoadCounter`; sensors `motionActivity`, `motionFollow`; `launchReconciliation`,
`lifecycleLogging`; `localDataStore`, `backupStore`; setters of `cloudSync`, `feedBackend` (set in `live()`),
`autoMode` (`connect`), `feedPublisher` (`connectFeed`); and `connectFeed(appState:)` (called from `connect`).
Stay private, moved with their only user: `feedMockURL`, `poiSearch(defaults:)`, `weatherLookup`, `dynamicsEntry`,
`logRide`, `recoverUnfinishedTrips`, `findProvincesCrossed` (fileprivate → private), instance `poiSearch`.
The report shows `grep` proving none of the 20 is used outside `Carodo/App/DependencyContainer*`.

### Owner decisions

1. **The cut:** the table above (8 files). Recommendation: approve it.
2. **Widened access:** (A) the 20 members above, moves only. (B) one small type for the gate (`LocalDataWork`:
   is-erasing, a count, waiters; begin, end, drain), which keeps the gate's 4 members private and makes erase's
   contract readable, at the cost of 13 call sites rewritten (not moves). Recommendation: **A now**; B recorded as a
   technical-debt candidate, decided apart because it touches erase.
3. **QA reads:** no `+QA+Debug` file. The one-line reads stay where they are (`live()`, `journeyPointServices`,
   `poiSearch(defaults:)` with its existing `#if DEBUG`). The three blocks in the middle of a flow become small
   functions in their concern's file, called from the same spot: `restoreDebugBackup(appState:)` and
   `awaitJournalSeed(appState:)` in `+Connect`, `seedFeedMock(server:publisher:)` in `+Feed`. Recommendation: approve.

### Docs

`AGENTS.md`: the App/ line in Architecture (DependencyContainer split by concern, `+Live`, `+Feed`, …) and the Git
shared-file list (`DependencyContainer*.swift`). `docs/architecture.md`: one line after "The composition root owns"
naming the files. `docs/operations/setup.md` line 109 stays true (`DependencyContainer.live()`). Member-level
references (`DependencyContainer.flushForBackground`, `.enrichJourneys`, …) stay valid: names do not change.

### Tests and validation

No test changes expected (every member keeps its name and signature). `task generate && task lint && task warnings &&
task test && task release-check`; `wc -l Carodo/App/DependencyContainer*.swift` (each ≤ ~350). Simulator by UDID: a
normal launch and `-carodo.sampleData YES` reach the Map. **Device check still required:** a Debug install launches
and recovers an unfinished drive. One commit: `refactor(app): dependency container split by concern`.
