# DependencyContainer split

**Status:** not started (brief written 2026-11-17). Runs beside
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
