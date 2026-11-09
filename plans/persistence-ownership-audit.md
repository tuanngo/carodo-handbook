# Persistence Foundation — foreign keys and application-managed ownership

Status: **Step B built 2026-11-09, uncommitted, waiting for the owner's review.** Approved: keep
F1–F3 and F6, drop F4–F5, `DataOwnership` with owned / derived / owned record / referencing /
independent; `visited_cells` kept (TD-7). No device reset.
Scope: `v1_initial` FKs, the GPS recording lifecycle, every journey deletion path, an ownership
registry, integrity tests. Not OBD (ADR 0019 stays as decided).

Owner's rule (2026-11-07): relationships are checked in the app; a reference that iCloud may
bring before its target is a plain id (no FK), joined at read time and cleaned up explicitly.

## 1. FK inventory (`DatabaseManager.v1_initial`)

| # | Column | Target | On delete | Synced / restored? | Can it arrive before its target? | Proposal |
|---|---|---|---|---|---|---|
| F1 | `trip_points.trip_id` | `trips` | CASCADE | never (local, live drive only) | **No**: written only by `TripWriter`, one serial stream, `begin` before any `append` | **Keep** |
| F2 | `trip_tracks.trip_id` | `trips` | CASCADE | iCloud (`CKAsset` of the `Trip` record), `.carodo` (inside `BackupTrip`) | **No**: always inserted in the same transaction as its trip, after it (`close`→`pack`, `insertTrip`, `applyTrip`) | **Keep** |
| F3 | `trip_gaps.trip_id` | `trips` | CASCADE | never (derived, local) | No: `saveGaps` writes for a trip it read | **Keep** |
| F4 | `vehicle_links.vehicle_id` | `vehicles` | CASCADE | not yet; `docs/sync.md` plans "all fields", `ck_*` columns exist | **Yes, once links sync** (a `VehicleLink` record before its `Vehicle` fails the insert) | **Drop**, plain id + explicit cleanup |
| F5 | `badge_unlocks.trip_id` | `trips` | SET NULL | `.carodo` today, iCloud planned (ADR 0013) | **Yes**: an unlock before its drive; today the insert writes `(SELECT id FROM trips WHERE id = ?)`, so the link is **dropped for good** (the case the owner's rule was made for). Restore hides it only by inserting trips first | **Drop**, keep the id as it came |
| F6 | `visited_cells.first_trip_id` | `trips` | SET NULL | never | n/a: **no code writes `visited_cells`** (reserved; only erase-all touches it) | **Keep as is** (local); the reserved table itself is a separate question (R6) |

No FK today, by design (keep): `trips.vehicle_id`, `trips.parent_id`, `vehicle_logs.vehicle_id`
/ `trip_id` / `declined_trip_id`, `fuel_logs` (same), `badge_states`, `places`.

Why keep F1–F3: they are **ownership inside one aggregate** (a trip and its fixes, packed track,
routed gaps), never cross a sync boundary on their own, and are always written after their parent
in the same writer or transaction. The FK there costs nothing in ordering, and gives two
guarantees no app code would give as cheaply: no fix can exist without its trip, and every hard
delete of a trip (ten paths, §3) takes its data with it.

Why drop F4–F5: they are references **between records that sync separately**. With an FK the
insert fails or (F5) the link is nulled, losing it. The pattern already used by `vehicle_logs`
applies: keep the id, join at read, clean up where the owner is hard-deleted.

## 2. GPS recording lifecycle (verified in code)

| Step | Where | Writes | Order / atomicity |
|---|---|---|---|
| Start | `DriveSessionManager` → `TripWriter.begin` → `beginTrip` | `INSERT trips (status 'recording')` | First operation of the trip's serial stream |
| Fixes | `TripWriter.record` → batch (10 fixes or 15 s) → `append` | `INSERT trip_points` per fix, one transaction per batch | Same stream, after `begin`: **trips row before trip_points rows — correct** |
| Pause / resume | `segment` bumped; same trip, same stream | rows | — |
| Failed write | `TripWriter.failed` keeps replayable ops (`begin`, `append`, vehicle ops) in `unwritten`; `retryComplete` replays them in order, then completes | — | A failed `begin` makes the appends fail too (F1); they wait in memory for the retry. The causes of a failed `begin` (database unavailable) fail an `append` anyway, so the FK adds no loss |
| Termination | rows stay; `trips.status = 'recording'` | — | Every committed batch is on disk; at most one batch (≤10 fixes / 15 s) lost |
| Launch recovery | `TripRecovery.run`: `unfinishedTrips()` reads rows; resume (`reopen`, same trip, rows continue) or `complete` / `hold` / `discardTrip` | — | `discardTrip` only when `TripReplay` finds no usable fix even keeping short |
| Finish / drop / hold | `close` in one transaction: `pack` (rows + any earlier packed track → `trip_tracks`, fixes after `ended_at` left out, `trip_points` deleted), then the summary `UPDATE` | `INSERT OR REPLACE trip_tracks`, `DELETE trip_points`, `UPDATE trips` | Atomic: a crash leaves either rows or the track, never neither |
| Trash / restore | `trash` / `restore`: `trashed_at` only | `UPDATE trips` | GPS untouched |
| Delete for good | `erase(_:journeys:)` (§3) | | |

No change proposed to this flow, the algorithms or the canonical metrics.

## 3. Every journey deletion path

| Path | Kind | Owned data (points, track, gaps) | Parts (`parent_id`) | References kept |
|---|---|---|---|---|
| `discardTrip` (recording, recovery) | hard | CASCADE | `freeParts` | badge SET NULL |
| `purgeDropped` | hard | CASCADE | `freeParts` | " |
| `discardHeld` | hard | CASCADE | `freeParts` | " |
| `deletePending` / `purgePending` | hard | CASCADE | parts deleted with it | " |
| `erase` (Delete for good, Recently Deleted purge), never in iCloud | hard | CASCADE | parts first, deleted | " |
| `erase`, in iCloud | **tombstone** | **explicit** `DELETE` from a hand list `["trip_points","trip_tracks","trip_gaps"]` (the row stays: CASCADE never fires) | parts tombstoned | route, places, narrative, name, note cleared |
| `GRDBCloudSyncStore.markDeleted` (iCloud confirmed) | hard (tombstones) | CASCADE (already gone) | — | badge SET NULL |
| `applyDeletions` (another device deleted) | hard | CASCADE | `freeParts` | `trips.vehicle_id` nulled for a deleted vehicle |
| `resetCloudMarkers` | hard (tombstones) | CASCADE | — | |
| `GRDBLocalDataStore.erase` (Erase data) | hard, all | hand list of 16 tables, children first | — | |
| Restore / import (`GRDBBackupStore.restore`) | **never replaces**: a trip already here is skipped | — | parents inserted before parts | vehicle id kept only if restored |

Vehicle hard deletes (`markDeleted`, `applyDeletions`, `resetCloudMarkers`, erase-all) take its
`vehicle_links` by CASCADE today; its logs and fill-ups are tombstoned by the local delete and
reach their own record deletes.

## 4. Risks

| # | Risk | Severity | Fix |
|---|---|---|---|
| R1 | F5: a badge unlock restored or synced before its drive loses `trip_id` for good (insert writes the subquery). Restore is safe only because trips go first | High once badges sync; latent today | Drop F5; write the id as it came; reads already find the drive by id (a missing drive reads as none) |
| R2 | F4: a synced `VehicleLink` before its `Vehicle` fails the insert | Latent (links not synced yet) | Drop F4; `links()` already joins `vehicles`; explicit cleanup on vehicle hard delete |
| R3 | Tombstone path keeps its own list of trip-owned tables; a new per-trip table forgotten there keeps data of a deleted drive (P5) | Medium | Ownership registry (§5), used by `erase` |
| R4 | Erase-all keeps its own list of every table; a new table forgotten survives Erase data | Medium | Registry + a schema test: every table is classified |
| R5 | Without F4, vehicle hard deletes must delete links themselves (four paths) | Introduced by R2's fix | One `VehicleOwnership.hardDelete` used by the four paths |
| R6 | `visited_cells` is a reserved table nothing writes | Low (unused schema) | Out of scope; owner's call: keep reserved or remove pre-release |
| R7 | Plain-id references (`vehicle_logs.trip_id`, `badge_unlocks.trip_id` after R1) dangle after a hard delete | By design | Documented: read through a join; never shown as a fact |

## 5. Ownership registry (proposal)

One file, `Core/Persistence/DataOwnership.swift`, nonisolated, no new abstraction beyond lists and
two helpers:

```swift
nonisolated enum DataOwnership {
    /// Rows that are part of a trip (FK CASCADE): gone with a hard delete, deleted explicitly
    /// when the trip is tombstoned.
    static let tripOwned = ["trip_points", "trip_tracks", "trip_gaps"]
    /// Rows that name a trip but outlive it (plain id, read through a join).
    static let tripReferencing = ["vehicle_logs", "fuel_logs", "badge_unlocks", "visited_cells"]
    /// Rows that are part of a vehicle, deleted with its hard delete (no FK after F4).
    static let vehicleOwned = ["vehicle_links"]
    /// Every table Erase data empties, children first.
    static let eraseOrder = [...]   // today's list, unchanged in content

    static func deleteTripOwned(_ tripID: String, in db: Database) throws
    static func deleteVehicleOwned(_ vehicleID: String, in db: Database) throws
}
```

Used by: `GRDBJourneyRepository.erase` (tombstone), the four vehicle hard-delete paths,
`GRDBLocalDataStore.erase`. Hard trip deletes keep relying on CASCADE (F1–F3), and the registry
says so.

Guard tests (`DataOwnershipTests`), reading the real schema:

- every table in `sqlite_master` (minus `grdb_migrations`) is in `eraseOrder`;
- every table with a `trip_id` column is in exactly one of `tripOwned` / `tripReferencing`, and
  every `tripOwned` table has an FK CASCADE to `trips`;
- every table with a `vehicle_id` column is classified (owned / referencing);
- `PRAGMA foreign_key_list` of every table matches the inventory above (F1–F3, F6): a new FK is a
  decision, not an accident.

## 6. Minimal change (Step B, after approval)

Schema (edit of `v1_initial`; a reset with `CONFIRM=erase` and a `.carodo` import, dev policy):

1. `vehicle_links.vehicle_id`: drop `.references("vehicles", onDelete: .cascade)`; add an index on
   `vehicle_id`? Not needed: the unique `(vehicle_id, role)` index serves both reads and deletes.
2. `badge_unlocks.trip_id`: drop `.references("trips", onDelete: .setNull)`; the index stays.

Code:

3. `GRDBBadgeRepository.record`: write `unlock.tripID` as given (insert and move-earlier), not the
   subquery. Readers of the stamp already query by trip id.
4. `DataOwnership` (§5); `erase` uses `deleteTripOwned`; `markDeleted`, `applyDeletions`,
   `resetCloudMarkers` call `deleteVehicleOwned` before deleting vehicles; erase-all uses
   `eraseOrder`.
5. Docs: `docs/data-model.md` (FK list, ownership section), `docs/sync.md` (links and unlocks
   kept as they came), `AGENTS.md` one line (new tables are classified in `DataOwnership`).

Tests (in-memory, synthetic data):

- **GPS not lost:** begin → batches → no close → `unfinishedTrips` returns every appended fix in
  order; recovery `complete` packs them all (`point_count` = fixes up to the end); a failed
  `append` replayed by `retryComplete` lands in place; resume (`reopen`) continues sequences and
  the pack merges rows with an earlier packed track.
- **No orphan after every hard-delete path** (each in §3, and erase-all): no `trip_points` /
  `trip_tracks` / `trip_gaps` row without its trip, no `vehicle_links` row without its vehicle,
  `PRAGMA foreign_key_check` clean.
- **Tombstone policy:** delete for good of a synced journey keeps the tombstone and its parts'
  tombstones, removes owned data, keeps `vehicle_logs.trip_id` and the badge unlock's `trip_id`
  (reads as none), clears route/places/narrative/name/note.
- **Order independence:** a badge unlock inserted (restore, sync merge) before its trip keeps its
  `trip_id` and the stamp shows once the trip arrives; a vehicle link before its vehicle is hidden,
  then returned; restore with trips listed after badges gives the same database as before.
- **Links unaffected:** the role tests from ADR 0019 and `CarConnectionsTests` unchanged; deleting
  a vehicle by each hard path removes its links of every role.

Not changed: `trip_points`/`trip_tracks`/`trip_gaps` FKs, the recording flow, `TrackCodec`, any
metric, `.carodo` format, CloudKit records.
