# Heavy work off the main actor: one door per heavy function, a rule that sees the callers

Design, for the owner's approval. Written 2026-11-16 from TD-46 (`plans/technical-debt.md`), left
by the location runtime work ([`location-runtime.md`](location-runtime.md)). `carodo-ios` at
`8734883`. After approval this becomes a step-by-step implementation plan; no code before that
([`../AGENT_WORKFLOW.md`](../AGENT_WORKFLOW.md), Plan before code).

**Status (2026-11-16):** design approved by the owner. Next: the implementation plan.
**Built (2026-11-16):** [`main-actor-work-plan.md`](main-actor-work-plan.md), carodo-ios `7d56640`,
merged into `main` as `3a11d86`. The measurement of section 7 was not taken: PV-27.

## 1. Why

Carodo's app and widget default to the main actor (`docs/architecture.md#concurrency`). With
`NonisolatedNonsendingByDefault`, a `nonisolated async` function with no `@concurrent` runs on its
**caller's** actor: called from a view model, its work runs on the main thread, the one thread that
draws the screen and takes touches. F1 of the location audit was one such case (the Feed invite's
shape). Rule R4 (`ArchitectureTests`) was added to catch more, but it only sees a function whose
own line says `nonisolated`, so it misses every async member of a `nonisolated` type.

A read of all of them (2026-11-16, section 3) found **six places that run whole-drive or
whole-history work on the main thread**. None was seen by the owner as a hitch yet; each grows with
the length of a drive or the size of the journal, so it gets worse as the app is used, and is worst
on a restore or when iCloud brings many drives at once.

The fix is at the root: the heavy pure functions get one off-main entry each, every caller goes
through it, and a test checks the callers instead of the declarations.

## 2. Goals, non-goals, anti-goals

**Goals**

1. Each heavy pure function named in section 4 has one `@concurrent` async entry; no main-actor
   code calls its synchronous form.
2. The six places of section 3 use those entries.
3. A source-reading test fails when a heavy function's synchronous form is called anywhere but
   inside its own entry or another `@concurrent` function (R6, section 5). R4's wrong allow-list
   reason is corrected; R4 stays as it is otherwise.
4. Each changed caller keeps today's behaviour: the same result, saved the same way, in the same
   order; a result that arrives after its screen or request ended is dropped, never written to
   state that belongs to a newer request.
5. One before-and-after measurement on an iPhone (section 7), so the report can say what the
   person feels, not only that the isolation is right.

**Non-goals**

- Making any of these functions faster. The work is the same; it moves off the main thread.
- The ~280 other async members found (database reads, network calls, light `map`/`filter` on a
  page): read and classified, left as they are.
- `CloudSyncService`'s design, the outbox, the backend, schema, API, dependencies: none change.
- A general "no heavy work on the main actor" checker. R6 names a list; a new heavy function joins
  it by one line (section 5).

**Anti-goals** (a failure even if it works)

- A merge, split, trim, restore or sync whose saved result differs from today's.
- A screen that shows a stale result after the person moved on (the "answer after an `await`"
  rule of `carodo-ios/AGENTS.md`).
- A speed-up claimed without a number.

## 3. What the read found

Every `async` function inside a `nonisolated` type without `@concurrent`, under `Carodo/`
(script-assisted, then read one by one; the script is not kept).

| Kind | About | Left as is because |
|---|---|---|
| Only awaits the database or the network; the work is inside GRDB's closure, off the main thread | 253 | Nothing to move |
| Light work on a page (a `map`, a `filter`, one JSON page) | 25 | Small and bounded |
| Sample repositories (previews, sample-data mode) | 10 | Not in a real journal |
| **Whole-drive or whole-history work, on the caller's actor = main** | **6** | Section 4 |

The six, today (paths under `carodo-ios/Carodo/`):

| # | Where it runs | What runs on the main thread | When |
|---|---|---|---|
| H1 | `Core/Sync/CloudSyncService.swift`, `fetched` and `sent` (the class is main-actor; the `CKSyncEngineDelegate` methods hop onto it) | For each record: `CloudRecordCoding.incoming(from:)` reads and decodes a trip's track file; then for each trip to derive, `SummaryRefresh.derive` replays the recorder over every fix | iCloud brings drives from another device: a restore, a second iPhone, a reinstall |
| H2 | `Core/Recording/WaitJoining.swift`, `split` and `merge` → `rederive`, called from `JourneyDetailViewModel.split(at:)` and `merge(_:)` | `SummaryRefresh.derive` over the joined drive's every fix | Split or Merge Drives on a journey's page |
| H3 | `Core/Recording/JourneyTrim.swift`, `apply`, called from `JourneyTrimViewModel` and `JourneyDetailViewModel` | `SummaryRefresh.derive` over the kept part | Saving a trim |
| H4 | `Core/Recording/GapHealing.swift`, `run`, called from `DependencyContainer.healGaps()` | `SummaryRefresh.derive` for each trip whose gap was healed | After launch and after a drive, once per unchecked trip |
| H5 | `Core/Achievements/BadgeLedger.swift`, `reconcile`, called from `DependencyContainer.recordMilestones()` and `PassportViewModel.loadMilestones` | `AchievementEngine.crossings` over every drive in the journal, then `changes` against every stored unlock | After launch, after a drive, opening the Passport |
| H6 | `Core/Feed/FeedPublisher.swift`, `publish(_:)` (main-actor class) → `FeedPublication.body` | `DriveShapeMaker.shape` over the drive's every fix (privacy cut, projection, Douglas–Peucker) | A finished drive published to the Feed while sharing is on |

Also found: R4's allow-list says `CloudSyncService.handleEvent` and `nextRecordZoneChangeBatch`
are fine because "the work awaits the store". The delegate methods themselves only hop, so the
entry stays on the list, but the reason is wrong: the work after the hop is H1. The reason is
rewritten to say the hop is deliberate and the heavy work goes through R6's entries.

Already right, for comparison: `SummaryRefresh.run` and `GRDBBackupStore.restore` are
`@concurrent`; the location runtime made `latestCarDrive` and its shape `@concurrent` (F1).

## 4. Design

### 4.1 One off-main entry per heavy function

The heavy functions are pure and synchronous. Each gets an async twin that is the only way
main-actor code reaches it:

| Heavy function (synchronous, stays) | Entry (new) |
|---|---|
| `SummaryRefresh.derive(_:configuration:calendar:)` | `SummaryRefresh.deriving(_:configuration:calendar:) async -> Journey?`, `@concurrent` |
| `CloudRecordCoding.incoming(from:readTrack:)` | an `@concurrent` function that decodes a batch of records, returning the decoded ones and the failures to log |
| `AchievementEngine.crossings(of:catalogue:)` + `changes(computed:stored:)` | one `@concurrent` function returning the changes for `reconcile` to record |
| `DriveShapeMaker.shape(route:tripID:privacyZone:homeAndWork:configuration:)` | `DriveShapeMaker.shaping(…) async -> DriveShape?`, `@concurrent`; the F1 helper in `DependencyContainer` (`inviteShape`) is folded into it |

Names are the builder's call within the repo's naming rules; the rule is one entry per heavy
function, beside it in the same file. The synchronous forms stay for tests and for code already
off the main thread (`SummaryRefresh.run`, `GRDBBackupStore.restore`).

### 4.2 The six callers

- **H1:** `fetched` and `sent` call the batch decoder and `deriving`. The writes to the store and
  `onRemoteChange` stay in today's order. Records still arrive in any order (`docs/sync.md`); the
  existing two-database sync tests must pass unchanged.
- **H2, H3, H4:** `rederive`, `JourneyTrim.apply` and `GapHealing.run` await `deriving`. Their
  store writes keep their order.
- **H5:** `reconcile` awaits the off-main computation, then records on the store as today.
- **H6:** `FeedPublication.body` becomes async (or takes a shape already made) and awaits
  `shaping`; the publisher's revision and outbox logic stay as they are.

**Results after an `await`.** Each view model caller (`JourneyDetailViewModel`,
`JourneyTrimViewModel`, `PassportViewModel`) is read for what it does with the answer: if it
writes state after the `await`, it checks that its request is still the current one, as the repo's
rule asks. Where it already only returns a `Bool` for the view to reload, nothing changes.

### 4.3 What does not change

The heavy functions' bodies, every threshold, the recorder's rules version, every query, the sync
order, the Feed payload.

## 5. The rule

**R6** in `CarodoTests/ArchitectureTests.swift`, reading the sources like R1–R5:

- A list of heavy synchronous calls, each with the one entry allowed to call it:
  `SummaryRefresh.derive(` → `deriving`, `CloudRecordCoding.incoming(` → its batch entry,
  `AchievementEngine.crossings(` → the ledger's entry, `DriveShapeMaker.shape(` → `shaping`.
- The test fails when one of them is called under `Carodo/` outside its entry, unless the
  enclosing function is itself `@concurrent` (today: `SummaryRefresh.run`,
  `GRDBBackupStore.restore`).
- The test is written first against today's tree and must fail naming the six places of section
  3 (a guard that cannot fail guards nothing).
- Adding a heavy function later is one line in the list; `docs/architecture.md#concurrency` says
  when a function counts as heavy: it walks a whole drive's fixes or the whole journal.

R4 stays (it catches a different mistake); its allow-list reason for `CloudSyncService` is
corrected (section 3). TD-46's other point, that R1, R3 and R5 match text only, is left open in
the register.

## 6. Tests

- **R6**, failing first, then passing.
- **Same result:** for each entry, a test that it returns exactly what the synchronous form returns
  for a synthetic input (a recorded synthetic trip for `deriving`, a synthetic history for the
  ledger, a synthetic route for `shaping`, a synthetic record batch with one damaged record for the
  decoder).
- **Callers unchanged:** the existing tests of `WaitJoining`, `JourneyTrim`, `GapHealing`,
  `BadgeLedger`, `FeedPublisher` and the two-database sync tests pass with no edit.
- **Stale answer:** for each view model caller that writes state after the `await`, a test that a
  second request started before the first answer arrives keeps the second's result.
- `task replay` and `task showcase` equal to their baseline before the change.

## 7. Measurement

Before and after on the owner's iPhone, release build, on power, three runs each
(`carodo-ios/docs/operations/device-testing.md`, Measuring performance), with Instruments
(Time Profiler and Hangs):

- **Merge Drives** on the two longest real drives in the journal (H2): the main thread's longest
  blocked stretch and any hang reported.
- If time allows, **restore** a `.carodo` backup of the owner's journal on a test install (H1/H4/H5
  at once), the same figures.

Without these numbers the report says "the work is off the main thread", never "faster". The
measurement is done by the agent with the owner's iPhone connected, or left as a PV row if the
phone is not available.

## 8. Slices

One slice, one commit: the entries, the six callers, R6 and the docs together, since R6 cannot
pass with part of the callers moved. Committed when `task lint`, `task warnings`, `task test`,
`task replay` and `task showcase` pass; the measurement follows before or after the commit, and
its numbers go in the report and in `docs/architecture.md` only if taken.

## 9. Decisions

**The owner's:** none new. No schema, API, permission, dependency or module changes (P6).

**Made here, for the owner to check**

- The fix is at the heavy function (an entry each), not six separate `@concurrent` patches.
- The six places are fixed together in one commit.
- R4 stays beside R6.
- The measurement is one scenario (Merge Drives), the restore only if time allows.
- The ~280 light or harmless functions are left alone.

**Left to the builder:** the entries' exact names and the batch decoder's shape; whether
`FeedPublication.body` becomes async or takes a shape; how R6 finds the enclosing function (the
location runtime's scanner helpers in `SourceFiles` are the starting point).

## 10. Docs

- `carodo-ios/docs/architecture.md#concurrency`: what makes a function heavy, the rule "one
  `@concurrent` entry per heavy function, beside it", and R6.
- `carodo-ios/AGENTS.md`, Concurrency: one line pointing at that rule.
- The handbook: TD-46 updated (R4's blind spot is covered for heavy work by R6; the text-matching
  point stays open); this file's status.

## 11. Assumed, not checked

- The six are the only whole-drive or whole-history work reached from the main actor. The read
  covered `async` members of `nonisolated` types and the callers of `SummaryRefresh.derive`; a
  synchronous main-actor function calling a heavy function directly (no `async` at all) would not
  have shown up. R6 will find any such call when it is written first (section 5).
- `CloudRecordCoding.incoming` is heavy because it reads and decodes a track file; its cost per
  record is not measured.
- `AchievementEngine.crossings` grows with the journal; its cost on today's journal is not
  measured and may be small.
- No other session edits these files while this runs; checked before the first edit.
