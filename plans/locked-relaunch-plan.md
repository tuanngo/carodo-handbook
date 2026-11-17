# Locked relaunch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When iOS relaunches Carodo in a locked iPhone (after its first unlock since a restart), the services start at once, so Auto Mode and Start Drive from a Shortcuts automation record the drive; the `launched` line says truly who launched it and whether the start waited.

**Architecture:** `AppLaunch` gates its start on "can the database file be read now" (`StoreReadability`) instead of `UIApplication.isProtectedDataAvailable` (false whenever the iPhone is locked). The `launched` line reads the app state when it is written, not in `CarodoApp.init`, and carries `waited=1 waitedS=…` from `LaunchContext` when the start had to wait.

**Tech Stack:** Swift 6, SwiftUI app lifecycle, UIKit (`UIApplication`), Foundation `FileHandle`, XCTest.

**Spec:** [`locked-relaunch.md`](locked-relaunch.md) (read it first: section 2 is the cause, section 5 the design).

`carodo-ios` at `c8fcea2` (after the 2026-11-17 refactor: `refactor(core): each file in the folder of what it is`, tests in folders mirroring `Carodo/`). Files this plan touches have not moved: `Carodo/App/AppLaunch.swift`, `Carodo/App/CarodoApp.swift`, `Carodo/App/DependencyContainer.swift`, `Carodo/Core/Diagnostics/LaunchContext.swift`, `Carodo/Core/Diagnostics/TrackingLog.swift`, `Carodo/Core/Diagnostics/DiagnosticsLogFormat.swift`, `Carodo/Core/Persistence/DatabaseManager.swift`.

## Global Constraints

- No schema, API, entitlement, background mode, file protection class, dependency or target change (spec section 4).
- No `!`, `try!`, `DispatchQueue`, `Task.detached`, `@unchecked Sendable`; no `@MainActor` written on app types (the target defaults to the main actor); every new main-actor class declares `nonisolated deinit {}`.
- A new log field is classified in `DiagnosticsLogFormat.sharedKeys` or `developerOnlyKeys`: `waited` shared, `waitedS` Developer only (P9: with the process's start it tells a minute).
- No coordinates, place names or identifiers in any new log line (P5).
- Work in a worktree: `git worktree add ../carodo-ios-locked-relaunch -b fix/locked-relaunch` from `main`, its own simulator (`SIM_ID` in that worktree's `.env`), never the owner's tree.
- Done = `task format`, `task lint`, `task warnings`, `task test` pass in the worktree; one commit for the outcome (code, tests, docs together), lowercase conventional, no AI attribution (P8); no push.

## Review Focus

1. **A fresh install launched for the first time** (no database file yet): must still start (fallback to `isProtectedDataAvailable`, which is true when the person opens it) — Task 1 test `testAMissingFileFallsBack`.
2. **The database file exists but cannot be read** (before the first unlock; on the simulator stood in for by a file with mode `000`): must wait, never open the database — Task 1 test `testAnUnreadableFileIsNotReadable`, Task 2 test `testAnUnreadableStoreWaitsForTheUnlockAndStartsOnce`.
3. **The notification and a screen appearing both fire after the unlock**: the services start once — kept by Task 2's existing assertions.
4. **An empty database file** (0 bytes, a crash during the very first open): readable means "the open succeeded", not "a byte came back" — Task 1 test `testAnEmptyFileIsReadable`.
5. **The `launched` line of a launch that waited** is written after the unlock, when the state may already be `active`: `waited=1` must say so, so `state=active` is not read as "the person opened it at once" — Task 3 test `testALaunchThatWaitedSaysSo`.

---

### Task 1: `StoreReadability` and one database location

**Files:**
- Create: `Carodo/Core/Persistence/StoreReadability.swift`
- Modify: `Carodo/Core/Persistence/DatabaseManager.swift` (add the default location), `Carodo/App/DependencyContainer.swift:266-271` (use it)
- Test: `CarodoTests/Core/Persistence/StoreReadabilityTests.swift`

**Interfaces:**
- Produces:
  - `DatabaseManager.defaultDirectory: URL` (`static`, `nonisolated`): `URL.applicationSupportDirectory.appending(path: "Carodo", directoryHint: .isDirectory)` — the same folder `DependencyContainer.live` opens today; `live` uses it instead of its own `FileManager.url(for:…)` chain (one source of the path).
  - `DatabaseManager.defaultFileURL: URL` = `defaultDirectory.appending(path: fileName)`.
  - `nonisolated enum StoreReadability { static func canRead(fileAt url: URL) -> Bool? }`: `nil` when no file exists at `url`; `true` when `FileHandle(forReadingFrom:)` opens it (then closed); `false` when the open throws. Reads no byte.

- [ ] **Step 1: Write the failing tests** in `StoreReadabilityTests` (temporary directory per test, removed in `tearDown`):
  - `testAReadableFileIsReadable`: write `Data([1, 2, 3])`, `XCTAssertEqual(StoreReadability.canRead(fileAt: url), true)`.
  - `testAnEmptyFileIsReadable`: write `Data()`, expect `true`.
  - `testAMissingFileIsUnknown`: no file, expect `nil`.
  - `testAnUnreadableFileIsNotReadable`: write a file, `FileManager.default.setAttributes([.posixPermissions: 0o000], …)`, expect `false`; restore `0o644` before removal.
  - `testTheDefaultFileIsTheOneTheAppOpens`: `XCTAssertEqual(DatabaseManager.defaultFileURL.lastPathComponent, "carodo.sqlite")` and `DatabaseManager.defaultDirectory.lastPathComponent == "Carodo"`, parent is `URL.applicationSupportDirectory`.
- [ ] **Step 2: Run** `xcodebuild test … -only-testing:CarodoTests/StoreReadabilityTests` (the worktree's `SIM_ID`). Expected: build fails, `StoreReadability` not found.
- [ ] **Step 3: Implement** `StoreReadability.canRead(fileAt:)` and the two `DatabaseManager` statics; switch `DependencyContainer.live` to `DatabaseManager.defaultDirectory` (`makeDatabase` already creates the folder). Doc comment on `StoreReadability`: why the file and not `isProtectedDataAvailable` (spec section 2, one paragraph).
- [ ] **Step 4: Run** the same tests. Expected: 5 pass.

### Task 2: `AppLaunch` waits only while the store cannot be read

**Files:**
- Modify: `Carodo/App/AppLaunch.swift`, `Carodo/App/CarodoApp.swift:28-34`
- Test: `CarodoTests/App/AppLaunchTests.swift`

**Interfaces:**
- Consumes: `StoreReadability.canRead(fileAt:)`, `DatabaseManager.defaultFileURL` (Task 1).
- Produces: `AppLaunch.init(canReadStore: @escaping () -> Bool, start: @escaping (_ deferred: Bool) -> DependencyContainer)` (the parameter `isProtectedDataAvailable` is renamed; behaviour of `begin()` / `startIfReady(deferred:)` unchanged otherwise). `CarodoApp` passes `canReadStore: { StoreReadability.canRead(fileAt: DatabaseManager.defaultFileURL) ?? UIApplication.shared.isProtectedDataAvailable }`.

- [ ] **Step 1: Update and add tests** in `AppLaunchTests`:
  - Rename the two existing tests' closure label to `canReadStore:`; rename `testALockedLaunchWaitsForTheUnlockAndStartsOnce` → `testAnUnreadableStoreWaitsForTheUnlockAndStartsOnce` (assertions unchanged).
  - New `testALockedIPhoneWithAReadableStoreStartsAtOnce`: `canReadStore: { true }` while the test never posts `protectedDataDidBecomeAvailableNotification`; after `begin()`, `XCTAssertNotNil(launch.container)` and `starts == [false]`. Comment: the 2026-11-17 drive; this is also what lets Start Drive from a Shortcuts automation find the container (`DriveStartActions.start` in `CarodoApp.init` returns `.needsApp` only while `container` is nil).
- [ ] **Step 2: Run** `-only-testing:CarodoTests/AppLaunchTests`. Expected: build fails on the `canReadStore:` label.
- [ ] **Step 3: Implement** the rename in `AppLaunch`; rewrite its doc comment (it waits only before the first unlock since a restart, read from the store itself; iOS's `isProtectedDataAvailable` is false whenever the iPhone is locked, spec section 2) and the `Logger` line ("store not readable: waiting for the first unlock"). Wire `canReadStore` in `CarodoApp.init`; update the comments there that say "before the first unlock" so they say "until the store can be read".
- [ ] **Step 4: Run** `AppLaunchTests`. Expected: 4 pass.

### Task 3: the `launched` line says who launched it and whether it waited

**Files:**
- Modify: `Carodo/Core/Diagnostics/LaunchContext.swift`, `Carodo/Core/Diagnostics/TrackingLog.swift:157-175` (the `LaunchState` doc comment), `Carodo/Core/Diagnostics/DiagnosticsLogFormat.swift` (keys), `Carodo/App/CarodoApp.swift` (`startServices`), `Carodo/App/DependencyContainer.swift:124-128` and `:847-858` (the line)
- Test: `CarodoTests/Core/Diagnostics/LaunchContextTests.swift`, `CarodoTests/Core/Diagnostics/TrackingLogFieldsTests.swift`, `CarodoTests/App/CarodoAppTests.swift`

**Interfaces:**
- Consumes: `AppLaunch`'s `deferred` flag (Task 2) passed into `startServices`.
- Produces:
  - `LaunchContext.waitedS: Int?` (new stored property, last in the memberwise init, default `nil`); `detail` appends ` waited=1 waitedS=<n>` after `lastMode` when non-nil.
  - `LaunchContext.make(_ origin:, previous:, lastMode:, startedAt: Date? = nil)`: `waitedS = startedAt.map { max(0, Int($0.timeIntervalSince(origin.at).rounded())) }`.
  - `DependencyContainer.launchStartedAt: Date?` (set by `startServices` to `.now` only when `deferred`), passed to `make` as `startedAt`.
  - `DependencyContainer.launchState: (() -> TrackingLogEntry.LaunchState)?` replaces the stored value; the `launched` line calls it when it is written.
  - `CarodoApp.launchState(_ state: UIApplication.State) -> TrackingLogEntry.LaunchState` (`static`): `.background` → `.background`, `.active` → `.active`, else `.inactive`. `startServices` sets `container.launchState = { launchState(UIApplication.shared.applicationState) }`; the read in `CarodoApp.init` is removed.
  - `DiagnosticsLogFormat`: `"waited"` in `sharedKeys`, `"waitedS"` in `developerOnlyKeys`.

- [ ] **Step 1: Write the failing tests**
  - `LaunchContextTests.testALaunchThatWaitedSaysSo`: `origin.at = launch`, `make(origin, previous: nil, lastMode: nil, startedAt: launch + 1_085)` → `detail == "build=1.0(1) waited=1 waitedS=1085"`.
  - `LaunchContextTests.testALaunchThatDidNotWaitSaysNothing`: `startedAt: nil` → `detail == "build=1.0(1)"`.
  - `TrackingLogFieldsTests`: the `.launched` sample's `LaunchContext` gains `waitedS: 1_085` (so both keys are classified or the test fails).
  - `CarodoAppTests.testTheLaunchStateIsReadAsUIKitReportsIt`: the three mappings above, `.inactive` included.
- [ ] **Step 2: Run** `-only-testing:CarodoTests/LaunchContextTests -only-testing:CarodoTests/TrackingLogFieldsTests -only-testing:CarodoTests/CarodoAppTests`. Expected: build fails (`startedAt`, `waitedS`, `launchState(_:)` missing).
- [ ] **Step 3: Implement** the interfaces above. `TrackingLogEntry.LaunchState`'s comment: read when the `launched` line is written (UIKit has finished launching), `background` when iOS launched Carodo; with `waited=1` the state is the one after the unlock.
- [ ] **Step 4: Run** the three classes. Expected: pass, and `TrackingLogFieldsTests` reports no unclassified key.

### Task 4: docs, full checks, commit

**Files:**
- Modify: `docs/architecture.md:42` ("Launch before the first unlock"), `docs/tracking.md` (Was Carodo running?: `state=` and when it is read, `waited`/`waitedS`; the 2026-11-09 silence possibly this fault), `docs/specs/auto-mode.md:51-55` (Start Drive from an automation starts in the background with Carodo swiped away and the iPhone locked; device check pending)
- Handbook (separate repo, separate commit): `plans/technical-debt.md` (new PV row: spec section 7's three device checks), `plans/locked-relaunch.md` Status line.

- [ ] **Step 1: Edit the three docs** as listed; each states the rule (the store's readability, after the first unlock) and its reason (the 2026-11-17 drive), never cites the handbook.
- [ ] **Step 2: Run** `task format && task lint`. Expected: lint clean.
- [ ] **Step 3: Run** `task warnings`. Expected: no warnings.
- [ ] **Step 4: Run** `task test`. Expected: all pass (count noted in the report; ~2,450 before this work).
- [ ] **Step 5: Self-review the diff** against `AGENTS.md` (Self-review list): no coordinates, `try?` only where ignorable, nothing left unused (`isProtectedDataAvailable` still used only in the fallback).
- [ ] **Step 6: Commit in the worktree**, own paths only:

```bash
git add Carodo/Core/Persistence/StoreReadability.swift Carodo/Core/Persistence/DatabaseManager.swift \
  Carodo/App/AppLaunch.swift Carodo/App/CarodoApp.swift Carodo/App/DependencyContainer.swift \
  Carodo/Core/Diagnostics/LaunchContext.swift Carodo/Core/Diagnostics/TrackingLog.swift \
  Carodo/Core/Diagnostics/DiagnosticsLogFormat.swift \
  CarodoTests/Core/Persistence/StoreReadabilityTests.swift CarodoTests/App/AppLaunchTests.swift \
  CarodoTests/App/CarodoAppTests.swift CarodoTests/Core/Diagnostics/LaunchContextTests.swift \
  CarodoTests/Core/Diagnostics/TrackingLogFieldsTests.swift \
  docs/architecture.md docs/tracking.md docs/specs/auto-mode.md
git diff --cached --stat
git commit -m "fix(launch): a relaunch in a locked iphone starts auto mode and start drive at once"
```

- [ ] **Step 7: Handbook commit**: the PV row and the spec's status, `docs(plans): locked relaunch …`.
- [ ] **Step 8: Report** and wait: merging `fix/locked-relaunch` into `main` and `task device` are the owner's call; the device check (spec section 7) is what proves the cause.
