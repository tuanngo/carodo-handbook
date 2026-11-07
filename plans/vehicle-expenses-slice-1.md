# Vehicle expenses, slice 1 (Log and link) Implementation Plan

**Status (2026-11-07):** Done. In `carodo-ios` main as `f55e0a4` (slice 1) and `c60dd0a` (Settings → Currency, added by the owner while reviewing), merged in `d3d2594`. Device checks still open (Task 6).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Log a car wash, a service or a toll from "Log for your car" with just an amount, link it (and fill-ups) to the drive being recorded, and show what was paid during a drive on its detail page, with suggestions to confirm or decline.

**Architecture:** No new table: the three expenses are `vehicle_logs` rows (`expense`/`wash`, `expense`/`toll`, `service`/`general`). Two nullable columns, `trip_id` and `declined_trip_id`, go on `vehicle_logs` and `fuel_logs` (no foreign key). A link names a `trips` row; it is read through `parent_id`, so merges and splits need no code, and a link to a trip that is gone, trashed or not on this device reads as unlinked. iCloud and `.carodo` carry the two fields inside the existing payload structs (`BackupVehicleLog`, `BackupFuelLog`), so no CloudKit schema change.

**Tech Stack:** SwiftUI, GRDB, XCTest, String Catalogs. iOS 17+, Swift 6.

**Spec:** `carodo-handbook/drafts/vehicle-expenses.md` (approved by the owner 2026-11-07). Read it first; this plan wins where it is more precise (see "Changes to the draft" below).

## Global Constraints

- carodo-ios `AGENTS.md` applies in full: no `!`/`try!`/`as!`, no `DispatchQueue`/`Task.detached`/`@unchecked Sendable`, `nonisolated` domain and stores, `@Observable` view models, no `@MainActor` annotations.
- Money: `amount` INTEGER in the currency's minor unit + `currency` ISO 4217 (`Money` in `Core/Formatting/Money.swift`); never summed across currencies; no total on a drive.
- No SQL foreign key and no `CHECK` on the new columns (owner rule); relationships are checked when read.
- Pre-release schema: edit `v1_initial` in `DatabaseManager`, never a new migration (iOS invariant 6).
- No GPS stored for wash, service or toll (owner, 2026-11-07).
- Every user-facing string in `Resources/Localization/` (Garage or Journeys table), English and Vietnamese, with a translator comment; Views use generated symbols (`Text(.Garage.…)`).
- Reuse before adding: no copied keypad, amount or time-line logic between the fuel sheet and the new sheet (Task 3 extracts it).
- Commits: the slice is one outcome. Do not commit per task. It shows on screen, so it waits for the owner's review of the screenshots (AGENTS.md, Git); then one commit `feat(garage): log a wash, a service or a toll and link it to the drive`, staged by path only.

## Changes to the draft (record them in it in Task 6)

- **Vehicle changed:** nothing moves. An entry keeps the vehicle it was logged for and stays linked to the drive (simpler; the person chose the car in the sheet).
- **Discard, purge, held fragments:** nothing is cleared. A link to a trip that no longer exists, or is trashed, reads as unlinked, so the entry can be suggested again for another drive. Trip ids are UUIDs never reused, so a dangling id is harmless.
- **Ready:** the session's `preparing` state already has its `trips` row; it links like `recording`.
- **Suggestions** need the drive to have a vehicle, and only list `service`/`expense` rows and fill-ups (never a bare odometer reading). The window is the drive itself plus **30 minutes** after it ends.
- **One drive per entry (owner, 2026-11-07).** An unlinked entry is suggested on one drive only, the nearest: the drive of its vehicle whose span holds its time, else the one that ended last before it (within 30 minutes). "Not this drive" there leaves it an expense of the vehicle, suggested nowhere; so one `declined_trip_id` is enough.

## Review Focus

1. A fill-up logged during a drive that is then discarded as too short: the fill stays in Fuel history, and is suggested (not shown as linked) on a later drive that covers its time. Pinned in Task 2 (`testALinkToAMissingTripReadsAsUnlinked`).
2. A drive moved to Recently Deleted: its entries are not shown as linked anywhere; restored, they come back linked. Pinned in Task 2 (`testATrashedDriveHidesItsLinks`).
3. Two drives merged: an entry linked to the later part shows on the merged drive. Pinned in Task 2 (`testALinkToAJoinedPartShowsOnTheJourney`).
4. Two drives close together (A ends 10:00, B runs 10:10–10:20, a wash at 10:15): it is suggested on B only, never on both; declined on B, it is suggested nowhere. Pinned in Task 2 (`testAnEntryIsSuggestedOnTheNearestDriveOnly`, `testADeclinedEntryIsSuggestedNowhere`).
5. The time moved, in the sheet, to before the recording started: no automatic link. Pinned in Task 3 (`testATimeBeforeTheDriveStartedIsNotLinked`).

---

### Task 1: Schema, domain fields and their round trips

**Files:**
- Modify: `Carodo/Core/Persistence/DatabaseManager.swift` (the `vehicle_logs` and `fuel_logs` blocks in `v1_initial`)
- Modify: `Carodo/Core/Domain/VehicleLog.swift`, `Carodo/Core/Domain/FuelLog.swift`
- Modify: `Carodo/Core/Persistence/GRDBVehicleRepository.swift` (`VehicleLogRecord`, `FuelLogRecord`, new `saveLog`)
- Modify: `Carodo/Core/Repositories/Repositories.swift` (`VehicleRepository`, its default extension, `SampleVehicleRepository`)
- Modify: `Carodo/Core/Backup/BackupDocument.swift` (`BackupVehicleLog`, `BackupFuelLog`)
- Modify: `docs/data-model.md` (`vehicle_logs`, `fuel_logs`, Indexes), `docs/specs/backup.md` (the log fields), `docs/sync.md` only if it lists payload fields
- Test: `CarodoTests/GRDBVehicleRepositoryTests.swift`, `CarodoTests/BackupTests.swift`, `CarodoTests/CloudRecordCodingTests.swift`

**Interfaces:**
- Produces: `VehicleLogEntry.tripID: UUID?`, `VehicleLogEntry.declinedTripID: UUID?` and the same two on `FuelLogEntry` (init parameters defaulting to nil, after `note`); `VehicleRepository.saveLog(_ entry: VehicleLogEntry) async throws` (adds or replaces by id; throws `VehicleLogError.invalid` when `!entry.isValid`; sets `ck_pending = 1`, keeps `created_at` of an existing row); `BackupVehicleLog.tripId`, `.declinedTripId`, and the same on `BackupFuelLog` (optional `UUID`, so older files and older payloads decode).

- [ ] **Step 1: Write the failing tests**

In `GRDBVehicleRepositoryTests`:
```swift
func testMigratorCreatesTheDriveLinkColumns() throws {
    let database = try DatabaseManager.makeInMemory()
    try database.read { db in
        for table in ["vehicle_logs", "fuel_logs"] {
            let columns = try db.columns(in: table).map(\.name)
            XCTAssertTrue(columns.contains("trip_id"), table)
            XCTAssertTrue(columns.contains("declined_trip_id"), table)
            XCTAssertTrue(try db.foreignKeys(on: table).isEmpty, "no foreign key (owner rule)")
        }
        let indexes = try db.indexes(on: "vehicle_logs").map(\.name) + db.indexes(on: "fuel_logs").map(\.name)
        XCTAssertTrue(indexes.contains("vehicle_logs_on_trip"))
        XCTAssertTrue(indexes.contains("fuel_logs_on_trip"))
    }
}

func testSaveLogKeepsTheDriveLinks() async throws {
    // repository over makeInMemory(), `car` saved; a wash with tripID and declinedTripID
    // saveLog → logs(for: car.id).first has the same tripID, declinedTripID, kind .expense, category "wash", amount 80_000, "VND"
    // saveLog again with tripID nil (same id) → one row, tripID nil
}

func testSaveFuelKeepsTheDriveLinks() async throws { /* same for saveFuel / fuelLogs */ }
```
In `BackupTests`: `BackupVehicleLog(entry).entry` and `BackupFuelLog(fill).entry` keep both ids; a JSON payload without the two keys decodes with both nil.
In `CloudRecordCodingTests`: an outgoing vehicle log with a `tripID` decodes back with it.
In `GRDBCloudSyncStoreTests` (AGENTS.md: records arrive in any order): an incoming vehicle log whose `tripID` names a trip this database does not have yet is stored with the link kept; once the trip arrives, `driveLogs(for:)` reads it as linked (Task 2 adds that assertion).

- [ ] **Step 2: Run them and see them fail**

Run: `xcodebuild test -project Carodo.xcodeproj -scheme Carodo -destination "platform=iOS Simulator,id=$SIM_ID" -quiet -only-testing:CarodoTests/GRDBVehicleRepositoryTests -only-testing:CarodoTests/BackupTests -only-testing:CarodoTests/CloudRecordCodingTests`
Expected: compile errors (`tripID` unknown, `saveLog` unknown).

- [ ] **Step 3: Implement**

- `v1_initial`: in both tables, after `note`, `t.column("trip_id", .text)` and `t.column("declined_trip_id", .text)` with a comment: the drive it was paid on (read through `parent_id`; a missing or trashed trip reads as unlinked) and the drive it was declined for; no foreign key. Indexes `vehicle_logs_on_trip` / `fuel_logs_on_trip` on `["trip_id"]`, condition `Column("trip_id") != nil && Column("deleted_at") == nil`.
- Records: coding keys `tripID = "trip_id"`, `declinedTripID = "declined_trip_id"`, mapped both ways like `vehicleID`.
- `saveLog` mirrors `saveFuel` (same transaction shape, same `updated_at`/`ck_pending` handling).
- Default extension: `saveLog` no-op. `SampleVehicleRepository`: `store.record(entry)` replacing by id.
- Backup structs: the two optional fields, filled in `init(_:)` and passed through in `entry`.
- `docs/data-model.md`: the two rows in both tables' column lists ("the drive it was paid on…", "the drive it was declined for; never suggested there again") and the two indexes in the Indexes table ("the entries of a drive").

- [ ] **Step 4: Run them and see them pass**

Same command. Expected: all pass.

---

### Task 2: A drive's logs, linked and suggested

**Files:**
- Create: `Carodo/Core/Domain/DriveLog.swift`
- Modify: `Carodo/Core/Persistence/GRDBVehicleRepository.swift`, `Carodo/Core/Repositories/Repositories.swift`
- Test: `CarodoTests/DriveLogTests.swift` (new), `CarodoTests/GRDBVehicleRepositoryTests.swift`

**Interfaces:**
- Consumes: Task 1 fields.
- Produces (all `nonisolated`, `Sendable`):
```swift
enum ExpenseCategory: String, CaseIterable, Sendable {   // order = tile order
    case wash, toll, service
    var kind: VehicleLogKind      // wash, toll → .expense; service → .service
    var category: String          // "wash", "toll", "general"
    init?(_ entry: VehicleLogEntry)   // the reverse; nil for any other kind/category
}
struct DriveLogItem: Identifiable, Hashable, Sendable {
    enum Source: Hashable, Sendable { case log(VehicleLogEntry), fuel(FuelLogEntry) }
    let source: Source
    var id: UUID; var at: Date; var amount: Int?; var currency: String?   // read from source
}
struct DriveLogs: Equatable, Sendable {
    var linked: [DriveLogItem]; var suggested: [DriveLogItem]   // each oldest first
    static let empty: DriveLogs
    static let suggestionWindowS: TimeInterval = 1_800
}
// VehicleRepository
func driveLogs(for journey: Journey) async throws -> DriveLogs
func link(_ item: DriveLogItem, to journeyID: UUID) async throws      // trip_id = journeyID
func unlink(_ item: DriveLogItem, from journeyID: UUID) async throws  // trip_id = NULL, declined_trip_id = journeyID
```
Default extension: `driveLogs` returns `.empty`, `link`/`unlink` no-op. `SampleVehicleRepository` implements all three over its store with the same rules (sample journeys have no parts and none are trashed).

**Rules for `driveLogs` (GRDB; "live trip" = `deleted_at IS NULL AND trashed_at IS NULL`):**
- *linked*: rows of both tables, `deleted_at IS NULL`, joined to `vehicles` like `logs(for:)`, whose `trip_id` is a live trip that is the journey or one of its parts (`id = :j OR parent_id = :j`).
- *suggested*: only when `journey.vehicleID` is set: rows of that vehicle, `deleted_at IS NULL`, `vehicle_logs.kind IN ('service','expense')` (all fill-ups), `occurred_at` in `[journey.startedAt, journey.endedAt + suggestionWindowS]`, `declined_trip_id IS NULL`, `trip_id` NULL or not a live trip, **and this journey is the entry's nearest drive**: among live, completed, top-level (`parent_id IS NULL`) trips of the same vehicle, the one whose `[started_at, ended_at]` holds `occurred_at`, else the one with the latest `ended_at <= occurred_at` within `suggestionWindowS`. A pure helper `DriveLogs.nearest(to date: Date, among spans: [DriveSpan], windowS: TimeInterval = suggestionWindowS) -> UUID?` (`struct DriveSpan: Sendable { let id: UUID; let startedAt: Date; let endedAt: Date }` in `DriveLog.swift`) decides it (tested in `DriveLogTests`); the store reads the few candidate spans around the entry's time and calls it.
- `link`/`unlink` update one row of the item's table, set `updated_at` and `ck_pending = 1`.

- [ ] **Step 1: Write the failing tests**

`DriveLogTests`: `nearest` picks the span holding the time (a time on a boundary belongs to the span it ends or starts: holding wins), else the latest ended within the window, else nil (31 minutes after); `ExpenseCategory` round-trips through a `VehicleLogEntry` for all three; an `odometer` row and an `expense`/`parking` row give nil; `DriveLogItem` reads `at`/`amount`/`currency` from both sources.

`GRDBVehicleRepositoryTests` (a journal with a completed trip from 10:00 to 11:00 for `car`, written with the helpers the file or `GRDBJourneyRepositoryTests` already use):
```swift
func testAnEntryLinkedToTheDriveIsLinked()                 // trip_id = trip → linked [wash], suggested []
func testAnEntryInTheWindowIsSuggested()                    // 11:25 → suggested; 11:31 → nothing; 09:59 → nothing
func testAnotherVehiclesEntryIsNeverSuggested()
func testAReadingAloneIsNeverSuggested()                    // kind .odometer at 10:30 → nothing
func testAnEntryIsSuggestedOnTheNearestDriveOnly()         // A 09:00–10:00, B 10:10–10:20, wash 10:15 → suggested on B, not on A; wash 10:05 → on A
func testADeclinedEntryIsSuggestedNowhere()                 // unlink(wash, from: B) → suggested on neither A nor B, still in logs(for:)
func testLinkThenUnlinkMovesTheEntry()                      // link → linked; unlink → neither list on that drive
func testALinkToAMissingTripReadsAsUnlinked()               // trip_id = UUID() with no row → suggested on the drive covering it
func testATrashedDriveHidesItsLinks()                       // trash(id:) → driveLogs of another drive covering the time suggests it; restore → linked again on the first
func testALinkToAJoinedPartShowsOnTheJourney()              // part with parent_id = trip; entry linked to the part → linked on trip
func testADriveWithNoVehicleHasNoSuggestions()
```

- [ ] **Step 2: Run them and see them fail**

Run: `… -only-testing:CarodoTests/DriveLogTests -only-testing:CarodoTests/GRDBVehicleRepositoryTests`
Expected: compile errors.

- [ ] **Step 3: Implement** `DriveLog.swift` and the three repository methods with the rules above. Two queries per list (one per table), merged and sorted by `at` in Swift.

- [ ] **Step 4: Run them and see them pass.**

---

### Task 3: The amount entry, shared, and the expense model

**Files:**
- Create: `Carodo/Core/Formatting/NumberEntry.swift`
- Create: `Carodo/Features/Garage/ViewModels/ExpenseEntryModel.swift`
- Modify: `Carodo/Features/Garage/ViewModels/FuelEntryModel.swift` (uses `NumberEntry` for both fields; takes `recording`)
- Modify: `Carodo/Core/Domain/DriveLog.swift` (adds `RecordingDrive`)
- Test: `CarodoTests/NumberEntryTests.swift`, `CarodoTests/ExpenseEntryModelTests.swift`, `CarodoTests/DriveLogTests.swift`; existing fuel model tests (find them: `grep -rl FuelEntryModel CarodoTests`) must still pass unchanged.

**Interfaces:**
```swift
nonisolated struct NumberEntry: Equatable, Sendable {
    init(integerDigits: Int, fractionDigits: Int)
    private(set) var text: String
    var allowsDecimal: Bool                 // fractionDigits > 0
    mutating func type(_ digit: Int)        // "0" + 5 → "5"; stops at the limits
    mutating func typeDecimal()             // "" → "0."; once; only when allowsDecimal
    mutating func deleteLast()
    mutating func set(_ text: String)       // a quick amount
}
nonisolated struct RecordingDrive: Equatable, Sendable {
    let tripID: UUID; let vehicleID: Vehicle.ID?; let startedAt: Date
    func tripID(forVehicle id: Vehicle.ID, at date: Date) -> UUID?   // same vehicle and date >= startedAt
}
@Observable final class ExpenseEntryModel {
    init(vehicle: Vehicle, category: ExpenseCategory, repository: any VehicleRepository,
         recording: RecordingDrive?, currency: String = Money.defaultCurrency(), now: @escaping () -> Date = Date.init)
    let vehicle: Vehicle; let category: ExpenseCategory; let currency: String
    var occurredAt: Date; var note: String; var failed: Bool
    private(set) var amount: NumberEntry      // integerDigits 12, fractionDigits Money.fractionDigits(currency)
    func typeDigit(_ digit: Int); func typeDecimal(); func deleteLast(); func useQuickAmount(_ minor: Int)
    var amountMinor: Int?                      // Money.minor(from:currency:), > 0
    var quickAmounts: [Int]                    // Money.quickAmounts(typed:currency:)
    var canSave: Bool                          // amountMinor != nil && !isSaving
    var entry: VehicleLogEntry?                // kind/category from `category`, time zone current, note trimmed (empty → nil), tripID from recording
    func save() async -> Bool                  // repository.saveLog; false + failed on error
}
```
`FuelEntryModel.init` gains `recording: RecordingDrive? = nil`; its `entry` sets `tripID` the same way. Its public API (`typeDigit`, `typeDecimal`, `deleteLast`, `text(for:)`, `allowsDecimal`, `quickAmounts`, `useQuickAmount`) stays, now delegating to two `NumberEntry` values (quantity: 3 and 2 digits; amount: 12 and `Money.fractionDigits(currency)`). No minimum amount for expenses (`Money.minimumFill` stays fuel-only).

- [ ] **Step 1: Write the failing tests**

`NumberEntryTests`: `type` replaces a lone "0"; integer limit (3 digits: "123" + 4 → "123"); fraction limit (2: "1.23" + 4 unchanged); `typeDecimal` on "" gives "0.", twice gives one point, disallowed when `fractionDigits == 0`; `deleteLast` on "" stays "".
`DriveLogTests`:
```swift
func testTheSameVehicleDuringTheDriveIsLinked()      // at == startedAt and later → tripID
func testATimeBeforeTheDriveStartedIsNotLinked()     // startedAt - 1 → nil
func testAnotherVehicleIsNotLinked()
```
`ExpenseEntryModelTests` (with `SampleVehicleRepository(vehicles: [car], logs: [], fuel: [])`, fixed `now`):
- typing "8", "0", "0", "0", "0" in VND → `amountMinor == 80_000`, `canSave`; nothing typed → `!canSave`;
- `entry` for `.service` has kind `.service`, category `"general"`; note "  " → nil;
- with `RecordingDrive(tripID: t, vehicleID: car.id, startedAt: now - 600)` → `entry?.tripID == t`; with `occurredAt = now - 3600` → nil;
- `save()` → `logs(for: car.id)` contains it.

- [ ] **Step 2: Run them and see them fail.**
- [ ] **Step 3: Implement**, then move `FuelEntryModel` onto `NumberEntry`.
- [ ] **Step 4: Run these tests and every existing fuel test; all pass.**

---

### Task 4: The three tiles and the expense sheet

**Files:**
- Create: `Carodo/Features/Garage/Views/ExpenseEntrySheet.swift`
- Create: `Carodo/Features/Garage/Views/LogEntryParts.swift` (extracted from `FuelEntrySheet`: `LogEntryTime.line(_ date: Date, now: Date = .now, calendar: Calendar = .current) -> String` — today's `FuelEntrySheet.when` —, `LogSheetCloseButton`, `QuickAmountChips(amounts: [Int], currency: String, pick: (Int) -> Void)`); `FuelEntrySheet` uses them, and its own copies go
- Modify: `Carodo/Features/Garage/Views/VehicleActionsSheet.swift`, `Carodo/App/MainTabView.swift`
- Modify: `Carodo/Resources/Localization/Garage.xcstrings`
- Modify: `docs/specs/garage.md` ("Log for your car", a new "Expense sheet" entry), `docs/operations/setup.md` (QA launch arguments)
- Test: `CarodoTests/LocalizationTests` (runs as is), any test calling `FuelEntrySheet.when` moves to `LogEntryTime.line`

**Interfaces:**
- Consumes: `ExpenseCategory`, `ExpenseEntryModel`, `RecordingDrive`, `FuelEntryModel(recording:)`.
- Produces: `VehicleActionsSheet.Action.expense(Vehicle, ExpenseCategory)` (id `"expense-\(category.rawValue)-\(vehicle.id)"`); `VehicleActionsSheet.init(…, logs: [Vehicle.ID: [VehicleLogEntry]] = [:], …)` where a vehicle missing from the map could not be read.

**Behaviour:**
- Tiles, after Log fuel and Update odometer, for every vehicle the sheet offers: Car wash, Tolls, Service (`ExpenseCategory.allCases` order). Detail line: the latest entry of that category, "Yesterday · 45.000 ₫" (relative named date · `Money.format(minor:currency:)`, the amount part left out when it has none), "Not logged yet" when there is none, nothing when the logs could not be read. Symbols are the builder's (suggested: `bubbles.and.sparkles`, `road.lanes`, `wrench.and.screwdriver`).
- `MainTabView.openLogForCar` also reads `vehicleRepository.logs(for:)` per vehicle (`try?`, missing on failure, like `lastFills`). `carAction` gains `.expense(let vehicle, let category): ExpenseEntrySheet(model: expenseEntry(vehicle, category))`.
- `MainTabView` computes `recordingDrive: RecordingDrive?` from `container.driveSession`: only when `state.isActive` and both `tripID` and `startedAt` are set (no `Date()`). It is passed to `fuelEntry` (both call sites) and `expenseEntry`.
- `ExpenseEntrySheet` has the fuel sheet's entry page shape: header (emblem, "Car wash · Daily", the time line `LogEntryTime.line` with a chevron, close button), the amount in large digits with the currency, `QuickAmountChips`, `NumberKeypad` (decimal key only when `amount.allowsDecimal`), **Save** (copper, disabled until `canSave`). The time line slides to a second page, **Time & note**: the `DatePicker` (`...Date.now`) and a one-line note `TextField`, then **Done**. Haptics as the fuel sheet (light on page change, success on save). Save failure: an alert like `fuelSaveFailed`.
- DEBUG: `-carodo.debugExpense wash|toll|service` opens that sheet for the first loggable vehicle (next to `carodo.debugLogForCar` in `MainTabView`); `-carodo.debugExpenseAmount 8` types digits, like `debugFuelAmount`. Both added to `docs/operations/setup.md#qa-launch-arguments-debug`.
- Copy (English / Vietnamese, the builder may refine per `docs/copy-and-localization.md`): Car wash / Rửa xe; Tolls / Phí cầu đường; Service / Bảo dưỡng; Not logged yet / Chưa ghi lần nào; Time & note / Thời gian & ghi chú; Note / Ghi chú; Couldn't save. Try again. / Chưa lưu được. Thử lại nhé.

- [ ] **Step 1: Extract `LogEntryParts` and move `FuelEntrySheet` onto it; build and run the fuel tests (no behaviour change).**
Run: `task build` then `task test`. Expected: build clean, all tests pass.
- [ ] **Step 2: Add the tiles, the action, the sheet, the strings and the debug arguments.**
- [ ] **Step 3: `task test` (LocalizationTests included) passes; `task lint` passes.**
- [ ] **Step 4: Screenshots** on the simulator (by UDID): `-carodo.sampleData YES -carodo.debugLogForCar YES` and `-carodo.debugExpense toll -carodo.debugExpenseAmount 45`, each in Light, Dark, a large Dynamic Type size (`-UIPreferredContentSizeCategoryName UICTContentSizeCategoryAccessibilityL`) and Vietnamese (`-AppleLanguages "(vi)"`). Save them in the scratchpad for the owner.

---

### Task 5: "During this drive" on the detail page

**Files:**
- Modify: `Carodo/Core/Domain/JourneyDetails.swift` (remove `FuelEvent` and `fuelEvents`: the phase-1 placeholder this replaces)
- Modify: `Carodo/Features/Journeys/ViewModels/JourneyDetailViewModel.swift`
- Modify: `Carodo/Features/Journeys/Views/JourneyDetailContextSections.swift` (replace `JourneyFuelEvents` with `JourneyDriveLogsSection`), `JourneyDetailView.swift:528-532`, `JourneyDetailSummarySections.swift` (timeline entries from `driveLogs.linked`)
- Modify: `Carodo/Core/PreviewData/SampleData.swift` (sample fill-ups/expenses linked to the long sample journeys instead of `fuelEvents`), `CarodoTests/SampleDataTests.swift:122`
- Modify: `Carodo/Resources/Localization/Journeys.xcstrings` (remove strings only the old section used; add the new ones)
- Modify: `docs/specs/journey-detail.md`
- Test: `CarodoTests/JourneyDetailViewModelTests.swift` (existing file, or create it if absent)

**Interfaces:**
- Consumes: `VehicleRepository.driveLogs(for:)`, `link(_:to:)`, `unlink(_:from:)`, `DriveLogItem`, `ExpenseCategory`.
- Produces: `JourneyDetailViewModel.driveLogs: DriveLogs` (private(set)); `func addToDrive(_ item: DriveLogItem) async`; `func removeFromDrive(_ item: DriveLogItem) async` (both call the repository, then read `driveLogs` again; a failure leaves the lists as they were); `var canLinkLogs: Bool` (= `canEdit`).

**Behaviour:**
- `load()` reads `driveLogs` as secondary data: `(try? await vehicleRepository.driveLogs(for: journey)) ?? .empty` (a failure hides the section, never "nothing paid").
- The section shows when `linked` or (`canLinkLogs` and `suggested`) is not empty, in the place `JourneyFuelEvents` held. Title "During this drive" / "Trong chuyến này". A row: symbol (fuel pump or bolt for a fill-up, the category's for an expense), title (category name; for a fill-up "38.5 L" / "Charge" with the station under it when there is one), the amount (`Money.format`), the time (`DisplayFormat.clock(at, timeZone: journey.timeZone)`). **No total, no cost per km.**
- A suggested row (only when `canLinkLogs`) is visibly distinct (secondary text, a dashed or lighter outline: the builder's) with **Add to this drive** / **Thêm vào chuyến** and **Not this drive** / **Không phải chuyến này**. A linked row has a context menu and an accessibility action **Remove from this drive** / **Gỡ khỏi chuyến này**.
- The timeline shows each linked item at its time, with its symbol (generalise its `.fuel` kind to carry a symbol).

- [ ] **Step 1: Write the failing tests** (`SampleVehicleRepository` with a wash linked to the journey and a toll suggested; `JourneyDetailViewModel` built with `edits`/`joins` as existing tests do so `canEdit` is true):
```swift
func testLoadReadsTheDrivesLogs()            // linked [wash], suggested [toll]
func testAddToDriveMovesTheSuggestion()      // addToDrive(toll) → linked [wash, toll] by time, suggested []
func testRemoveFromDriveDeclinesIt()         // removeFromDrive(wash) → linked [], suggested [] for this drive
func testAFailedReadHidesTheSection()        // a repository whose driveLogs throws → driveLogs == .empty
```
- [ ] **Step 2: Run and see them fail.**
- [ ] **Step 3: Implement**; remove `FuelEvent`, `fuelEvents`, `JourneyFuelEvents` and the strings only they used (`grep` each key before removing).
- [ ] **Step 4: `task test` passes.**
- [ ] **Step 5: Screenshots**: `-carodo.sampleData YES -carodo.debugOpenJourney <a long sample journey>` showing linked and suggested rows, in the four variants of Task 4.

---

### Task 6: Docs, the draft, and the whole check

**Files:**
- Modify: `carodo-handbook/drafts/vehicle-expenses.md` (slice 1 marked built; the "Changes to the draft" above written into its Decided section; what moved to `docs/` cut down to a pointer)
- Modify: `carodo-handbook/plans/vehicle-expenses-slice-1.md` (this file: status)

- [ ] **Step 1:** `task format`, then `task lint` → no findings.
- [ ] **Step 2:** `task warnings` → "no warnings" (fix or name any, files you did not touch too).
- [ ] **Step 3:** `task test` → all pass; give the count.
- [ ] **Step 4: Self-review** against carodo-ios `AGENTS.md` ("Self-review before handing back"): no coordinates stored for the three kinds, no `try?` on the save path, nothing left of `FuelEvent`, no duplicated keypad/amount logic.
- [ ] **Step 5: Report** to the owner (AGENTS.md, Report) with the screenshots; say "waiting for the owner's review". **Schema change:** `trip_id`, `declined_trip_id` on `vehicle_logs` and `fuel_logs` (approved 2026-11-07). **Device warning:** a DEBUG install erases a phone database whose `v1_initial` changed (`SchemaDumpTests`, `task device`), so `task ios:pull-db` before installing on the iPhone. **Device checks still required:** a fill-up and a toll logged while a real drive records are linked; Auto Mode pending drive.
- [ ] **Step 6: After the owner accepts:** stage by path only (`git add <each file>`, `git add -p` for `MainTabView.swift` and the `.xcstrings`), check `git diff --cached --stat`, commit `feat(garage): log a wash, a service or a toll and link it to the drive`. The handbook files commit in `carodo-handbook` separately (`docs: plan and draft for vehicle expenses`).
