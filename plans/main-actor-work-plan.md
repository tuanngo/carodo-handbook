# Heavy work off the main actor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The four heavy pure functions get one `@concurrent` entry each, the six places that run
them on the main thread go through those entries, and a new rule (R6) fails on any direct call.

**Architecture:** Each heavy synchronous function keeps its body and gains an async twin beside it,
marked `@concurrent`, which is the only caller allowed outside other `@concurrent` code. Callers
`await` the twin and keep their store writes in today's order. `ArchitectureTests` gets R6, read
from the sources like R1–R5.

**Tech Stack:** Swift 6.2 (main actor by default, `NonisolatedNonsendingByDefault`), GRDB,
CloudKit (`CKSyncEngine`), XCTest, Instruments (`xctrace`), `task` shortcuts.

**Spec:** [`main-actor-work.md`](main-actor-work.md) (approved 2026-11-16). Read it first, then
`carodo-ios/AGENTS.md` (Concurrency, Self-review: "An answer after an `await` belongs to its
request"), then `carodo-ios/docs/architecture.md#concurrency`.

**Status (2026-11-17):** Tasks 1–6 built and merged (carodo-ios `7d56640`, `main` at `3a11d86`;
2,427 tests pass there). Task 7, the measurement on an iPhone, is not done: PV-27 in
`technical-debt.md`. Found on the way: `PassportViewModel` could show an older milestones read
that answered last; a request counter now drops it (`PassportViewModelTests`).

## Global Constraints

- Repo `carodo-ios`, base `8734883`. Work in a worktree:
  `git worktree add ../carodo-ios-main-actor -b fix/main-actor-work`; copy the gitignored `.env`
  from the main checkout; `xcodegen generate`. Before editing a file: `git log -1` on it; a file
  changed since `8734883` is re-read, never overwritten.
- No change to the heavy functions' bodies, any threshold, `RouteRecorder.rulesVersion`, any query,
  schema, API, the Feed payload, a dependency (P6). No Swift type renamed.
- Swift rules of `AGENTS.md`: no `!`, `try!`, `as!`, `DispatchQueue`, `Task.detached`,
  `@unchecked Sendable` (adding a `Sendable` conformance to a type that is not one is the same
  mistake); `@concurrent` on a `nonisolated` function, never a detached task.
- Synthetic test data only; no coordinate in a log or a fixture (P5).
- `CarodoTests/` stays flat; a test goes in its subject's existing file (list below).
- Checks from the worktree, after the last edit: `task format`, `task lint`, `task warnings`,
  `task test`, `task replay`, `task showcase`. Report that run, never an earlier one.
- **One commit** for Tasks 1–6 (the spec, section 8), made by the agent when the checks pass;
  lowercase conventional message, **no AI attribution of any kind** (P8: no `Co-Authored-By`, no
  footer). Stage by path. Never push or merge.
- Run every check in the foreground (timeout up to 600000 ms); never wait on a background run with
  a monitor (a session stalled that way on 2026-11-16).
- Simulators by UDID (`SIM_ID` in the worktree's `.env`); the owner's iPhone only for Task 7.
- A step that needs a contract, a schema, another feature's files, or that changes a saved result
  stops and goes to the owner.

## Review Focus

1. **A drive split or merged, then the page left before the answer arrives.** The journal reloads
   with the result; no state of the left page is written. Pinned in Task 3, Step 1.
2. **The Passport opened twice quickly (tab switch and back).** One set of milestones, not the
   older read's. Pinned in Task 4, Step 1.
3. **iCloud brings a batch with one damaged record and one record from a newer build.** The other
   records apply, the damaged one is logged and skipped, the newer one is kept as today. Pinned in
   Task 5, Step 1.
4. **A trim saved twice quickly.** The second trim's figures are what the page shows. Pinned in
   Task 3, Step 1.
5. **A drive hidden while its Feed body is being built.** The stale body is dropped by the
   revision check as today. Pinned in Task 4, Step 1.

---

## File map

| File | Change |
|---|---|
| `Carodo/Core/Recording/SummaryRefresh.swift` | + `deriving` |
| `Carodo/Core/Domain/Achievements.swift` | + `AchievementEngine.changes(of:catalogue:stored:)` async entry |
| `Carodo/Core/Domain/DriveShapeMaker.swift` | + `shaping` |
| `Carodo/Core/Sync/CloudRecordCoding.swift` | + `decoding(_:)` batch entry |
| `Carodo/Core/Recording/WaitJoining.swift`, `JourneyTrim.swift`, `GapHealing.swift` | await `deriving` |
| `Carodo/Core/Achievements/BadgeLedger.swift` | await the engine's entry |
| `Carodo/Core/Domain/FeedPublication.swift`, `Carodo/Core/Feed/FeedPublisher.swift` | the shape awaited |
| `Carodo/Core/Sync/CloudSyncService.swift` | batch decode and `deriving` |
| `Carodo/App/DependencyContainer.swift` | `inviteShape` folded into `shaping` |
| View models: `JourneyDetailViewModel`, `JourneyTrimViewModel`, `PassportViewModel` | read; changed only where a stale answer can land |
| `CarodoTests/ArchitectureTests.swift` | + R6; R4's reason fixed |
| Tests: `SummaryRefreshTests`, `BadgeLedgerTests`, `DriveShapeMakerTests`, `CloudRecordCodingTests`, `WaitJoinTests`, `JourneyTrimTests`, `GapHealingTests`, `FeedPublisherTests`, `CloudSyncServiceTests`, `JourneyDetailViewModelTests`, `PassportViewModelTests` | new cases in the existing files |
| `docs/architecture.md`, `AGENTS.md` (carodo-ios) | Concurrency |

---

### Task 1: R6, written first and failing

**Files:** `CarodoTests/ArchitectureTests.swift`, `CarodoTests/SourceFiles.swift` (a helper only if needed).

**Interfaces:**
- Produces: `testHeavyWorkIsReachedOnlyThroughItsConcurrentEntry`, and the list it reads:

```swift
/// Heavy synchronous call → the one entry allowed to make it (docs/architecture.md#concurrency).
private let heavy: [(call: String, entry: String)] = [
    ("SummaryRefresh.derive(", "deriving"),
    ("CloudRecordCoding.incoming(from: ", "decoding"),
    ("AchievementEngine.crossings(", "changes(of"),
    ("DriveShapeMaker.shape(", "shaping"),
]
```

- [ ] **Step 1: Baselines.** In the worktree: `task test`, `task replay`, `task showcase`, saved in
  the session's scratchpad as `baseline-{test,replay,showcase}.txt`. Expected: pass.
- [ ] **Step 2: Write the test.** For each non-comment line under `Carodo/` containing a `call`:
  find the enclosing `func` (walk back to the nearest line declaring one at a lower brace depth).
  It passes when that function's name is the call's `entry`, or the function or the line above it
  carries `@concurrent`. Every other hit is collected as `File.swift:line funcName` and the test
  asserts the collection is empty, with the message "call the @concurrent entry beside it".
- [ ] **Step 3: Run.** `xcodebuild test … -only-testing:CarodoTests/ArchitectureTests`. Expected:
  FAIL listing at least: `CloudSyncService.swift` (`fetched`, `sent`: derive and incoming),
  `WaitJoining.swift` (`rederive`), `JourneyTrim.swift` (`apply`), `GapHealing.swift` (`run`),
  `BadgeLedger.swift` (`reconcile`), `FeedPublication.swift` (`body`), `DependencyContainer.swift`
  (`inviteShape`, an `@concurrent` function: it must **not** be listed; if it is, the enclosing
  function search is wrong). Save the output for the report. Any hit not named here is read: a
  heavy call on the main actor joins this plan's scope and the report; anything else is reported.
   R6 matches the qualified call text only: an unqualified `derive(` inside `SummaryRefresh`
  itself is not seen (today only `run`, which is `@concurrent`). Say so in the test's comment.
- [ ] **Step 4: Fix R4's reason.** In `testWorkInANonisolatedAsyncFunctionIsConcurrent`, the
  allow-list comment for `CloudSyncService.swift: handleEvent` and `nextRecordZoneChangeBatch`
  becomes: the delegate methods only hop onto the service; its heavy work goes through R6's entries.

No commit: the tree commits once, after Task 6.

### Task 2: The four entries

**Files:** `SummaryRefresh.swift`, `Achievements.swift`, `DriveShapeMaker.swift`,
`CloudRecordCoding.swift` and their test files.

**Interfaces:**
- Produces:
  - `@concurrent static func deriving(_ trip: StoredTrip, configuration: RouteRecorder.Configuration = .init(), calendar: Calendar = .current) async -> Journey?` on `SummaryRefresh`
  - `@concurrent static func changes(of drives: [CountedDrive], catalogue: BadgeCatalogue, stored: [BadgeUnlock]) async -> (insert: [BadgeUnlock], moveEarlier: [BadgeUnlock])` on `AchievementEngine` (crossings, then `changes(computed:stored:)`)
  - `@concurrent static func shaping(route: [CLLocationCoordinate2D], tripID: UUID, privacyZone: PrivacyZone, homeAndWork: [CLLocationCoordinate2D], configuration: Configuration = .init()) async -> DriveShape?` on `DriveShapeMaker`
  - `@concurrent static func decoding(_ records: [CKRecord]) async -> (decoded: [IncomingRecord], failed: [(recordName: String, error: any Error)])` on `CloudRecordCoding` (a different name from `incoming(from:)` on purpose: R6 matches the call text, so the batch call must not contain `incoming(from: `)
  Each is a one-line call of its synchronous form (two for `changes(of:)`), placed directly under it with a doc comment naming R6.

- [ ] **Step 1: Write the failing tests**, one per entry in its subject's file, each asserting the
  entry equals the synchronous form on the same synthetic input:
  - `SummaryRefreshTests.testDerivingEqualsDerive`: a synthetic `StoredTrip` of 600 fixes with one
    gap → `await deriving(trip) == derive(trip)`; a trip of one fix → both nil.
  - `BadgeLedgerTests.testTheEngineEntryEqualsCrossingsThenChanges`: a synthetic history crossing
    two thresholds and one stored unlock → equal `insert` and `moveEarlier`.
  - `DriveShapeMakerTests.testShapingEqualsShape`: a synthetic route → equal; a route too short →
    both nil.
  - `CloudRecordCodingTests.testTheBatchDecodesEachAndReportsTheDamaged`: three records, one with
    no payload → two decoded equal to the one-by-one decode, one failure named by its record name.
- [ ] **Step 2: Run** those four. Expected: FAIL (the entries do not exist).
- [ ] **Step 3: Implement** the four entries. **If `CKRecord` is not `Sendable` in this SDK** (the
  compiler says so when it crosses into the `@concurrent` function): do not add a conformance;
  keep decoding on the caller, drop the batch entry and its R6 row, and say so in the report (H1's
  derive still moves off; the decode is the smaller part).
- [ ] **Step 4: Run** the four. Expected: PASS.

### Task 3: Re-deriving callers (H2, H3, H4)

**Files:** `WaitJoining.swift`, `JourneyTrim.swift`, `GapHealing.swift`; read
`JourneyDetailViewModel.swift` (`split(at:)`, `merge(_:)`, the trim call near line 447) and
`JourneyTrimViewModel.swift` (`save`, near line 237). Tests: `WaitJoinTests`, `JourneyTrimTests`,
`GapHealingTests`, `JourneyDetailViewModelTests`.

**Interfaces:** Consumes `SummaryRefresh.deriving`.

- [ ] **Step 1: Write the failing tests.**
  - `JourneyDetailViewModelTests.testASplitAnsweredAfterThePageLeftWritesNothing` (Review Focus 1)
    and `JourneyTrimTests` or the trim view model's test file:
    `testASecondTrimSavedBeforeTheFirstAnswersShowsTheSecond` (Review Focus 4). Read each caller
    first: if it only returns a `Bool` and the view reloads the journal, the test asserts that
    (the return value and the store's state after both), and no view model code changes.
  - The existing `WaitJoinTests`, `JourneyTrimTests`, `GapHealingTests` are the regression: they
    must pass with no edit.
- [ ] **Step 2: Run** the new tests. Expected: PASS if the callers are already safe (then say so),
  FAIL where a stale answer lands (fix it in Step 3 by checking the request is still current
  after the `await`, the repo's rule).
- [ ] **Step 3: Implement.** `rederive`, `JourneyTrim.apply` and `GapHealing.run` call
  `await SummaryRefresh.deriving(…)` where they called `derive`; arguments unchanged.
- [ ] **Step 4: Run** `WaitJoinTests`, `JourneyTrimTests`, `GapHealingTests`,
  `JourneyDetailViewModelTests`. Expected: PASS.

### Task 4: The ledger and the Feed shape (H5, H6), and F1's helper

**Files:** `BadgeLedger.swift`, `FeedPublication.swift`, `FeedPublisher.swift`,
`DependencyContainer.swift` (`inviteShape`, about line 401); read `PassportViewModel.swift`
(`loadMilestones`, about line 166). Tests: `BadgeLedgerTests`, `PassportViewModelTests`,
`FeedPublisherTests`, `FeedInviteDriveTests`.

**Interfaces:** Consumes `AchievementEngine.changes(of:catalogue:stored:)`, `DriveShapeMaker.shaping`.
Produces: `FeedPublication.body(…) async -> DriveInputBody?` (same parameters, now async).

- [ ] **Step 1: Write the failing tests.**
  - `PassportViewModelTests.testTwoLoadsKeepTheNewestMilestones` (Review Focus 2): two loads where
    the first's ledger answer arrives last; `newMilestones` is the second's.
  - `FeedPublisherTests.testADriveHiddenWhileItsBodyIsBuiltIsNotStored` (Review Focus 5): hide
    the drive (raise its revision) between the read and the store; nothing is stored, as today.
  - Existing `BadgeLedgerTests`, `FeedPublisherTests`, `FeedInviteDriveTests` pass unedited.
- [ ] **Step 2: Run.** Expected: as Task 3, Step 2.
- [ ] **Step 3: Implement.** `reconcile` awaits `changes(of: Self.countedDrives(read),
  catalogue:, stored: try await badges.unlocks())`; the rest of `reconcile` is unchanged.
  `FeedPublication.body` becomes `async` and awaits `shaping`; `FeedPublisher.publish` awaits it.
  `DependencyContainer.inviteShape` is deleted and `latestCarDrive` awaits `shaping` with
  `.default` and `[]`. A stale `newMilestones` write, if Step 2 found one, is guarded as in Task 3.
- [ ] **Step 4: Run** the four test classes. Expected: PASS.

### Task 5: iCloud (H1)

**Files:** `CloudSyncService.swift` (`fetched` about line 411, `sent` about line 431). Tests:
`CloudSyncServiceTests`, `GRDBCloudSyncStoreTests` (the two-database sync tests).

**Interfaces:** Consumes `CloudRecordCoding.decoding(_:)` (if Task 2 kept it) and
`SummaryRefresh.deriving`.

- [ ] **Step 1: Write the failing test** `CloudSyncServiceTests.testABatchWithADamagedAndANewerRecordAppliesTheRest`
  (Review Focus 3), at the level the existing tests drive `fetched` (read them first): three good
  records, one with no payload, one `unsupportedVersion`; the three apply, the damaged one is
  logged as today, the newer one is kept and not applied. If no existing test reaches `fetched`
  without CloudKit, write it against the decode-then-apply step the existing tests already use and
  say so in the report.
- [ ] **Step 2: Run.** Expected: PASS today (behaviour pinned before the change).
- [ ] **Step 3: Implement.** `fetched`: one `await CloudRecordCoding.decoding(records)`,
  each failure logged exactly as the loop logs it today; then `store.apply` and, per derived id,
  `await SummaryRefresh.deriving(trip)` and `saveDerived`, in today's order. `sent`: the
  `serverRecordChanged` branch's derive becomes `deriving`; its single-record decode may stay
  synchronous (one record; R6 then needs `sent` to call the batch entry with one record instead,
  which is the simpler way to keep R6 exact).
- [ ] **Step 4: Run** `CloudSyncServiceTests`, `GRDBCloudSyncStoreTests`, `CloudRecordCodingTests`.
  Expected: PASS with no existing test edited.

### Task 6: R6 green, docs, checks, commit

**Files:** `CarodoTests/ArchitectureTests.swift`, `docs/architecture.md`, `AGENTS.md` (carodo-ios).

- [ ] **Step 1: Run R6.** Expected: PASS. If it lists anything, fix it the same way or stop and ask.
- [ ] **Step 2: `docs/architecture.md#concurrency`.** Replace the R4 paragraph's last sentences
  with: a function is **heavy** when it walks a whole drive's fixes or the whole journal; each
  heavy function has one `@concurrent` entry beside it; R6 fails on a direct call outside that
  entry or other `@concurrent` code; R4 still catches a `nonisolated async` function declared
  without `@concurrent`; the four heavy functions named. Keep the "tripwire, not a proof" sentence
  for R1, R3, R5.
- [ ] **Step 3: `AGENTS.md`**, Conventions → Concurrency: one sentence: "A function that walks a
  whole drive's fixes or the whole journal is called through its `@concurrent` entry
  (`docs/architecture.md#concurrency`, R6)."
- [ ] **Step 4: Full checks.** `task format`, `task lint`, `task warnings`, `task test`,
  `task replay`, `task showcase`. Expected: clean; replay and showcase output identical to the
  baselines (`diff`); the test count is the baseline's plus the new tests.
- [ ] **Step 5: Commit.** `git add` each path; `git diff --cached --stat` lists only this work.

```bash
git commit -m "fix(concurrency): heavy work through one @concurrent entry each, held by a test"
```

### Task 7: Measure on the iPhone, then record

**Files:** handbook only: `plans/technical-debt.md` (TD-46, and a PV row if not measured), this
plan's and the spec's status lines, `docs/architecture.md` (only numbers that were taken, in a
follow-up commit on the same branch).

- [ ] **Step 1: Is the owner's iPhone connected?** `task devices` lists "TuanNgo iPhone" as
  physical and connected. If not: skip to Step 4 and add a PV row "Main-actor work measured on an
  iPhone" naming the scenario below.
- [ ] **Step 2: Before.** Install a **release** build of `8734883` on the iPhone (`task device` at
  that commit from a separate worktree or with `CONFIGURATION=Release` if the Taskfile supports it;
  read `task --list` first; a schema change prompt means stop). On power. In the app, open the
  longest drive whose neighbour may merge, run
  `xcrun xctrace record --template 'Time Profiler' --device "$DEVICE" --attach Carodo --time-limit 30s --output <scratchpad>/before-N.trace`
  while doing Merge Drives, then Undo/split back. Three runs. Read each trace's longest main-thread
  stretch and any Hang (`xcrun xctrace export --input … --toc`, then the hangs table).
- [ ] **Step 3: After.** The same with the branch's commit, the same drive, three runs.
- [ ] **Step 4: Record.** In the report: before and after, three runs each (longest main-thread
  block in ms, hangs counted), device model, build, power. TD-46 updated: heavy work held by R6;
  the text-matching point left open. Status lines: built, measured or PV. If the numbers were
  taken, a short line in `docs/architecture.md#concurrency` and a second commit
  `docs(concurrency): main-thread block before and after on an iphone`.
- [ ] **Step 5: Report.** `AGENT_WORKFLOW.md`'s completion report: behaviour changed ("none a
  person sees, except the screen stays responsive during these operations"; or what Steps 2–3
  showed), R6's first failing output, the baselines' diff, the commit hash(es), anything Task 2's
  `CKRecord` check changed, everything left open.

---

## Decisions made in this plan

- The entries are named `deriving`, `shaping`, `changes(of:catalogue:stored:)` and
  `decoding(_:)`, beside their synchronous forms.
- The badge entry combines `crossings` and `changes`: both walk the history, one hop is enough.
- `FeedPublication.body` becomes `async` rather than taking a prepared shape: one caller, and the
  shape stays private to the body.
- F1's `inviteShape` is folded into `shaping`, so there is one entry for the shape.
- If `CKRecord` is not `Sendable`, the batch decode is dropped rather than worked around.
- The measurement is Merge Drives only; restore is not measured in this plan.

## Not in this plan

Faster heavy functions; the ~280 light or harmless async functions; R1, R3, R5's text matching
(TD-46's other half); the map-lookups work and TD-45 (next in the queue).
