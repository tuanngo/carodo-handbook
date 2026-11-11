# Feed V1 · Part 4 — publishing, against a local mock of the backend · Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** With sharing on, the owner's own car drives are published exactly as the app will
publish them to the real backend (contract 0.27.0-draft bodies, through the outbox), and the Feed
reads them back from a **local mock server** that answers with the contract's JSON. The backend
replaces the mock later behind the same transport and repository, with no screen changing.

**Architecture:**
- `Core/Networking/FeedAPI.swift`: Codable DTOs mirroring the contract (`DriveInput`,
  `DriveShape`, `FeedItem`, `FeedDrive`, `CommunityStats`, `Sharing`, feed page).
- `trips.feed_state` + `trips.feed_published_at` in `v1_initial` (P6, approved with the design).
- `FeedPublication` (pure): a journey, its car and the person's private places → a `DriveInput`.
- `LocalFeedServer` (actor, DEBUG + Release-safe, device-only): what the backend will do —
  accounts/sharing, publish/unpublish with revision and tombstones, geographic-payload refusal,
  day grouping, coarse ages, display choices at read time, stats with k ≥ 10 and `warmup` — kept
  in a JSON file in Application Support. Answers are contract JSON.
- `LocalFeedTransport: OutboxTransport` hands outbox messages to the server; `OutboxRelay` gets
  wired (it is built but nothing drains it today).
- `FeedPublisher` (service in the composition root): publish after a car drive is saved, the
  72-hour backfill on Start sharing, hide, unpublish on delete.
- `LocalCommunityRepository: CommunityRepository` decodes the server's JSON into today's domain
  types (Part 5 widens them). `-carodo.sampleData YES` keeps `SampleCommunityRepository`.

**Tech Stack:** Swift 6, GRDB, XCTest. No new dependency, no network.

**Spec:** `carodo-handbook/plans/feed-v1-design.md`; `carodo-ios/docs/specs/feed.md`;
`docs/api/carodo-api.yaml` 0.27.0-draft; `docs/sync.md` (Publishing, Outbox).

## Global Constraints

- The mock lives on the device only: nothing leaves it, no URL, no port. It stores only what the
  real server would (summaries and shapes, never a route or a coordinate) and is deleted with the app.
- The device sends exactly the contract body; the mock refuses what the server will refuse
  (geographic keys at any depth, a shape point out of 0–1, out-of-range figures).
- Only car drives with an assigned vehicle are published (`VehicleClass.car`); nothing on the
  tracking path waits on publishing (P1); the outbox is written in the same transaction as the
  state change.
- P9: the mock returns ages in hours ("2h"), never an instant; `busiestHour` is a local hour.
- Pre-release schema edit in `v1_initial`; the DEBUG reset erases the dev database on the
  owner's device at the next run (journeys return from a `.carodo` backup).
- Part 5 builds the Join sheet and the sharing page; until then DEBUG `-carodo.feedSharing YES`
  turns sharing on for the claimed username (or a DEBUG one).
- `task lint`, `task warnings`, `task test` pass; device check: a real car drive appears as "You".

## Review Focus

1. **A drive published before sharing was on**, or a two-wheeler, or a drive with no vehicle,
   must never reach the server. Tests in Task 3 and Task 5.
2. **Hide wins over a late publish** (outbox retry after a hide): revision + tombstone in the
   mock; test `testAHideIsNotUndoneByALatePublish`.
3. **Stop then Start sharing** republishes what was not hidden (the reviewer's C1): test
   `testStartingAgainRepublishesWhatWasNotHidden`.
4. **Time zones:** a drive recorded in another zone groups under its own local day and part of
   day. Test with `Journey.timeZone` set to UTC+9 while the test runs in UTC+7.
5. **A damaged mock file** (truncated JSON) must not crash the app: the server starts empty and
   says so in the log; test `testADamagedStoreStartsEmpty`.

---

### Task 1: Contract DTOs

**Files:** Create `Carodo/Core/Networking/FeedAPI.swift`; Test `CarodoTests/FeedAPITests.swift`.

**Interfaces — Produces** (all `nonisolated struct …: Codable, Hashable, Sendable`, field names as the contract):
`DriveInputBody { revision, startedAt, endedAt, localDate: String, localStartHour, partOfDay: PartOfDay, distanceM, movingDurationS, elapsedDurationS, vehicle: VehicleLabelBody, weather: Weather, shape: DriveShapeBody? }`,
`VehicleLabelBody { make: String?, model: String? }`, `enum Weather: String { rain, clear, unknown }`,
`DriveShapeBody { version: Int, points: [[Double]] }`, `SharingBody { sharing, displayAs: DisplayAs, showVehicle }` (`enum DisplayAs: String { anonymous, username }`),
`FeedDriveBody { durationS, distanceM, ago: String, partOfDay, weather: String?, shape: DriveShapeBody? }`,
`FeedItemBody { id: UUID, isAuthor, displayName: String?, vehicle: VehicleLabelBody?, drives, totalDurationS, totalDistanceM, ago, reactions: [String: Int], myReaction: String? }`,
`FeedPageBody { items, nextCursor: String?, hasMore }`, `CommunityStatsBody { windowHours, visible, drivers: Int?, distanceM: Double?, durationS: Double?, busiestHour: Int?, warmup: Double? }`.
Dates encode as RFC 3339 UTC (`JSONEncoder.carodoAPI` / `JSONDecoder.carodoAPI`, one place).

- [ ] **Step 1: Tests** — `testADriveInputEncodesTheContractsKeysOnly` (encoded keys == the contract's list; no `lat`, `lon`, `route`), `testDatesAreRFC3339UTC`, `testAFeedPageFromTheContractExampleDecodes` (a hand-written JSON page in the test).
- [ ] **Step 2:** run → fails (types missing). **Step 3:** implement. **Step 4:** run → pass.

### Task 2: The trip's feed state

**Files:** Modify `Carodo/Core/Persistence/DatabaseManager.swift` (`trips`: `feed_state TEXT NOT NULL DEFAULT 'none'`, `feed_published_at REAL`), `Carodo/Core/Domain/Journey.swift` (`var feedState: FeedState = .none`), the trip row mapping in `GRDBJourneyRepository`, `docs/data-model.md` (move the columns from Planned to the `trips` table).
Create `Carodo/Core/Persistence/FeedStateStore.swift`. Test `CarodoTests/FeedStateStoreTests.swift`.

**Interfaces — Produces:** `nonisolated enum FeedState: String { none, published, hidden }`;
`struct FeedStateStore { init(database: DatabaseWriter); func setState(_: FeedState, trip: UUID, enqueue: OutboxOperation?, now: Date) async throws` (one transaction: column + outbox row);
`func markAcknowledged(trip: UUID, at: Date) async throws`; `func publishable(since: Date) async throws -> [UUID]` (completed, not deleted, `feed_state != 'hidden'`, ended at or after `since`).
`feedHidden` iCloud sync: map `feed_state == hidden` into the trip record (`CloudRecordCoding`), a hide wins on merge.

- [ ] **Step 1: Tests** — migrator on an in-memory `DatabaseQueue` creates both columns; `setState` writes the column and the outbox row together (a throwing enqueue leaves the column unchanged); `publishable(since:)` leaves out hidden, deleted and older trips; the CloudKit mapping round-trips `feedHidden` and a merge of hidden vs published keeps hidden.
- [ ] **Steps 2–4:** red, implement, green.

### Task 3: `FeedPublication`

**Files:** Create `Carodo/Core/Domain/FeedPublication.swift`; Test `CarodoTests/FeedPublicationTests.swift`.

**Interfaces — Consumes:** `DriveShapeMaker.shape(...)`, `PrivacyZone`, `PartOfDay`, Task 1 DTOs.
**Produces:** `static func body(for journey: Journey, vehicle: Vehicle?, route: [CLLocationCoordinate2D], privacyZone: PrivacyZone, homeAndWork: [CLLocationCoordinate2D], weather: Weather = .unknown) -> DriveInputBody?` — nil unless `vehicle?.vehicleClass == .car`; local date, start hour and part of day in `journey.timeZone` (else the device zone); `revision` from the journey; vehicle make/model always sent.

- [ ] **Step 1: Tests** — `testOnlyCarDrivesArePublished` (motorbike, bicycle, nil → nil); `testTheLocalDayAndHourAreTheDrivesOwn` (UTC+9 zone); `testTheBodyCarriesNoCoordinate` (encode and scan for the route's latitude digits); `testTheShapeIsTheMakersForThisTrip`.
- [ ] **Steps 2–4:** red, implement, green.

### Task 4: `LocalFeedServer`

**Files:** Create `Carodo/Core/Networking/LocalFeedServer.swift`; Test `CarodoTests/LocalFeedServerTests.swift`.

**Interfaces — Produces:** `actor LocalFeedServer { init(fileURL: URL?, now: @Sendable () -> Date, calendar: Calendar)`
`func claim(username: String, sharing: SharingBody) -> Result<Void, ServerError>`; `func sharing() -> SharingBody?`; `func setSharing(_: SharingBody)`;
`func put(tripID: UUID, body: Data) -> Int` (HTTP status) ; `func delete(tripID: UUID, revision: Int) -> Int`;
`func feed(cursor: String?, limit: Int) -> Data` (a `FeedPageBody`); `func stats() -> Data` (a `CommunityStatsBody`);
`func addSyntheticDrivers(_ count: Int)` (DEBUG: other drivers' drives from `SampleData`, for the ≥ 10 view) }`.
Rules: the contract's. Items = drives grouped by (author, `localDate`), newest first, 72 h window on `endedAt`, ids random per group and stable for its life; ages from `endedAt` to `now` in whole hours; `displayName` and `vehicle` from the author's sharing at read time; the reader is the only account, so its items are `isAuthor`; stats: distinct authors in 72 h, < 10 → `visible: false`, numbers null, `warmup = floor(drivers) / 10`; `busiestHour` = most common `localStartHour`.

- [ ] **Step 1: Tests** — `testAPublishedDriveComesBackAsTheReadersRow`, `testDrivesOfOneLocalDayAreOneItem`, `testAgesAreWholeHours`, `testAnOlderRevisionChangesNothing`, `testAHideIsNotUndoneByALatePublish`, `testStoppingRemovesEveryRow`, `testStartingAgainRepublishesWhatWasNotHidden`, `testShowVehicleOffNamesNoCar`, `testAGeographicKeyIsRefused` (422), `testUnderTenDriversNoNumberIsShown`, `testTenDriversShowTheNumbers` (with `addSyntheticDrivers(9)`), `testTheStoreSurvivesARestart` (file round-trip), `testADamagedStoreStartsEmpty`.
- [ ] **Steps 2–4:** red, implement, green.

### Task 5: Publisher, transport, outbox wiring

**Files:** Create `Carodo/Core/Outbox/LocalFeedTransport.swift`, `Carodo/Core/Feed/FeedPublisher.swift`; Modify `Carodo/Core/Outbox/OutboxOperation.swift` (comments and key `feed:<tripID>` for the new paths), `Carodo/App/DependencyContainer.swift` (server, store, relay, publisher), `Carodo/App/MainTabView.swift` (after a car drive is saved: `publisher.driveSaved(id)`; on scene active: `relay.drain`), journey delete path (enqueue unpublish). Test `CarodoTests/FeedPublisherTests.swift`.

**Interfaces — Produces:** `final class FeedPublisher { func driveSaved(_ id: UUID) async; func startSharing(now: Date) async /* backfill 72 h */; func stopSharing() async; func hide(_ id: UUID) async; func journeyDeleted(_ id: UUID, revision: Int) async }` — each writes state + outbox in one transaction, then asks the relay to drain.

- [ ] **Step 1: Tests** (in-memory DB, real `OutboxStore` and `OutboxRelay`, `LocalFeedServer` without a file): `testACarDriveSavedWhileSharingIsPublished`, `testNothingIsPublishedWhileSharingIsOff`, `testStartSharingPublishesTheLast72HoursNotHidden`, `testHideRemovesTheRowAndKeepsItHidden`, `testDeletingAJourneyRemovesItsRow`.
- [ ] **Steps 2–4:** red, implement, green.

### Task 6: Repository, composition, docs, device check, commit

**Files:** Create `Carodo/Core/Repositories/LocalCommunityRepository.swift` (decodes the server's JSON → `FeedPage`, `FeedIdentity`; claim through the server); Modify `DependencyContainer` (non-sample builds use it; `-carodo.sampleData YES` keeps the sample), `docs/sync.md` (a "Local mock" paragraph), `docs/operations/setup.md` (`-carodo.feedSharing YES`, `-carodo.feedSyntheticDrivers N`), `docs/specs/feed.md` (Today). Test `CarodoTests/LocalCommunityRepositoryTests.swift` (decoding, cursor, a bad cursor → `.badCursor`).

- [ ] **Step 1:** tests red → implement → green.
- [ ] **Step 2:** `task format`, `task lint`, `task warnings`, `task test`.
- [ ] **Step 3:** simulator: claim a username (DEBUG), `-carodo.feedSharing YES`, run a sample drive through `-carodo.sampleJournal` is in-memory only — instead record a short simulated drive with a car: it appears as the reader's row; screenshot.
- [ ] **Step 4:** device check for the owner (listed in the report): after the dev database reset, restore the `.carodo`, turn sharing on, drive: the drive shows as "You" with its shape.
- [ ] **Step 5:** stage this plan's paths; commit `feat(feed): publish car drives through the outbox to a local feed server`.
