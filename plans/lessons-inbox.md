# Lessons inbox — waiting for `docs/solutions/` (study L5)

Status: collecting (owner, 2026-11-13). L5, one lesson per file in `carodo-ios/docs/solutions/`
for agents to grep before touching an area, is built once there are enough lessons to make it
worth the convention: **about ten entries here, or before the first TestFlight build, whichever
comes first** ([`drive-recorders-study.md`](../references/repos/drive-recorders-study.md) L5, §5).
Until then every lesson lands here, already in L5's shape, so moving it is mechanical.

A lesson belongs here when a bug cost a device round trip, survived a review, was fixed twice, or
a measurement overturned what everyone assumed. The binding rule it produced may already be in a
repo's docs (say where); the entry keeps the story an agent needs to recognise the situation.

Write in English, no real coordinates or traces (P5). Template:

```markdown
### <slug>
- applies_when: <the change an agent is about to make, in words it would grep for>
- area: <module or folder> · found: <date, commit> · severity: <high|medium|low>
- Context: what happened, with the numbers.
- Guidance: what to do instead.
- Why it matters: the cost of repeating it.
- Rule now in: <repo doc or test that enforces it, or "nowhere yet">
```

## Waiting to be moved (scattered today)

Lessons already paid for that L5 gathers, beside the entries below:

- "Five mistakes a source audit found here" — `carodo-ios/AGENTS.md`, Self-review.
- "Map rules — learned the hard way" — `carodo-ios/docs/design-system.md`.
- The iOS 26.0 isolated-deinit crash (carodo-ios `9db0594`) — `AGENTS.md`, Concurrency.
- `CLLocationUpdate.liveUpdates` suspended on a background wake — `drive-recorders-study.md` §1.
- Derived data selected by presence instead of version — study L4 (Pilgrim's lesson).

## Entries

### screen-reads-whole-journal
- applies_when: a screen, card or view model needs totals, counts, a comparison or "last used"
  over many drives; calling `journeyRepository.journeys()`
- area: Features/*/ViewModels, Core/Repositories · found: 2026-11-12, carodo-ios 53edd24, b39f20c ·
  severity: medium
- Context: the Garage and a vehicle's page read every trip with its decoded route to sum distance
  and time (149 ms and 102 ms at 10,000 drives, Debug, simulator); Journey Detail read the whole
  journal to count a few places' visits and 30 routes to compare one figure.
- Guidance: read light rows with only what is shown (`drives()`, `drives(of:)`, `summary(in:)`,
  `distances(before:limit:)`), on an index for one vehicle, place or end. A place's figures come
  from the drives ending near it.
- Why it matters: the cost grows with the journal and is paid on every open; real routes are
  about 3.7 times the synthetic ones, so the simulator understates it.
- Rule now in: carodo-ios `docs/architecture.md#complexity-budget`; `ArchitectureTests` fails on
  `.journeys()` in `Features/` (90666be).

### grdb-row-lookup-by-name
- applies_when: decoding `Row`s in a loop over many trips; a light read that is slower than
  expected; `row["column"]` in a `compactMap` over the journal
- area: Core/Persistence · found: 2026-11-12, carodo-ios 53edd24 · severity: medium
- Context: `passportFacts()` took 156 ms at 10,000 drives while its SQL alone took 25 ms. Each
  `row["name"]` searches the row's columns; 20 columns × 10,000 rows was five times the query.
  Reading by position from a cursor brought it to 39 ms, and the place visits page from 86 to 28.
- Guidance: over the whole journal, read columns by position (`Row.fetchCursor`, `row[0]`) with
  the SELECT beside it and a comment tying the two; measure the query alone before blaming SQL.
- Why it matters: "a light read without routes" was assumed fast and was slower than the
  heavy read it replaced, until measured part by part.
- Rule now in: carodo-ios `docs/architecture.md#complexity-budget`.

### calendar-before-date-filter
- applies_when: bucketing drives by week, month or day with `Calendar` over a long history
- area: Core/Domain (GarageAnalysis and kin) · found: 2026-11-12, carodo-ios 53edd24 · severity: low
- Context: the Garage's 12 weekly bars ran `dateComponents` and `dateInterval` on every drive of
  every vehicle: 36 ms at 10,000 drives. A `Date` comparison first (older than the bars by more
  than any zone's offset) brought it to 5 ms.
- Guidance: filter with a cheap comparison, then do calendar work on what is left; keep the
  margin wider than any time-zone offset so a drive's own local day still decides.
- Why it matters: calendar calls are among the most expensive per-item work in Swift.
- Rule now in: carodo-ios `docs/architecture.md#complexity-budget`.

### perf-claim-needs-same-setup-before
- applies_when: reporting a speed-up; writing "faster" in a commit or a plan
- area: CarodoTests/*PerformanceTests · found: 2026-11-12 · severity: low
- Context: the first "after" number for the Garage (198 ms) looked like a regression against
  `journeys()` alone (95 ms); only the old code run through the same test (149 ms) gave a true
  before. The old code was measured in a throwaway worktree at the previous commit.
- Guidance: one opt-in test, the same journal size and build, run on both commits; break a
  surprising number into its parts (SQL, decoding, analysis) before changing anything.
- Rule now in: carodo-ios `AGENTS.md` (Done means) and `docs/architecture.md`.

### split-large-files-in-a-worktree
- applies_when: moving or splitting a large shared file while other sessions run; a commit that
  would include `Carodo.xcodeproj/project.pbxproj` changed by someone else; `main` with a peer's
  staged files
- area: workflow, Git · found: 2026-11-12, carodo-ios 7260c5f..caf0915 · severity: medium
- Context: a parallel session had uncommitted edits and a regenerated `project.pbxproj`; splitting
  two 1,000+ line files in the shared tree would have mixed both into one commit. Done in a
  worktree on a branch, then main merged into the branch, the project regenerated and tested,
  and `main` fast-forwarded: the peer's files never moved. A merge commit in the shared tree was
  impossible anyway: Git refuses a merge while the index holds someone else's staged change.
- Guidance: a refactor that moves files goes in a worktree; bring it home by fast-forward; commit
  your own paths in a shared tree with a temporary index (`GIT_INDEX_FILE`), re-checking `HEAD`
  first; quote nothing through a shell variable holding several paths (zsh does not split it).
- Rule now in: carodo-ios `AGENTS.md` (Git) covers worktrees and staging; the fast-forward route
  is nowhere yet.

### temp-index-commit-misses-generated-project
- applies_when: committing new Swift files from a shared tree with `GIT_INDEX_FILE`; adding a file
  and staging only "your paths"
- area: workflow, Git, XcodeGen · found: 2026-11-13, carodo-ios 90666be → 2ab8b71 · severity: low
- Context: two new test files were committed by path through a temporary index; the regenerated
  `Carodo.xcodeproj/project.pbxproj` was left out, so `HEAD` listed files its project did not
  build, and the shared tree's regenerated project then blocked the next fast-forward.
- Guidance: a commit that adds or removes a source file includes the project regenerated from that
  same tree (`xcodegen generate` in a clean worktree at `HEAD` + your change), checked with
  `git diff` to name only your files.
- Rule now in: nowhere yet (`AGENTS.md` Git says the project is generated, not that it travels
  with an added file).

### debug-destination-outside-the-path
- applies_when: a DEBUG launch argument that opens a page; `.navigationDestination(item:)` or
  `isPresented:` on a screen whose links use `NavigationLink(value:)`
- area: Features (DEBUG), navigation · found: 2026-11-13, TD-23 · severity: low
- Context: `-carodo.debugOpenMilestones` showed its page with `.navigationDestination(item:)`; a
  value link on that page appended to the tab's typed path beneath it, so the drive opened under
  the milestone page. Taps through the app were correct; only the debug route looked broken.
- Guidance: a debug route pushes onto the same typed path a tap would (`AppRoute` on the tab's
  stack); judge a link opened from a debug page against the tapped route before calling it a bug.
- Rule now in: nowhere yet (TD-23, with TD-14).
