# Vehicle telemetry (OBD-II) — schema readiness

Status: **Step B in progress (2026-11-09).** Owner decisions below; built: `vehicle_links`
typed associations (§2b) in `v1_initial`, ADR 0019, docs. Uncommitted, waiting for review.

Principle: **GPS is the primary spatial evidence. OBD-II is optional vehicle telemetry. Journey
owns the timeline, not a single sensor source.**

## 1. Current persistence architecture (audited 2026-11-09)

- **One GRDB/SQLite file**, `DatabasePool` in WAL, `synchronous = NORMAL`, FKs on
  (`DatabaseManager`). One migration, `v1_initial`, edited in place pre-release; DEBUG builds set
  `eraseDatabaseOnSchemaChange`, so **any edit of `v1_initial` erases the iPhone's database**.
  `task device` guards it: it compares the phone's `sqlite_master` with this build's
  (`SchemaDumpTests`) **for exact equality** and refuses to install without `CONFIRM=erase`; the
  drives come back only through a `.carodo` (`task backup-db` + AirDrop).
- **Journey identity:** `trips.id` (UUID made on device), `parent_id` for joined parts, `status`
  (`recording` / `completed` / `dropped` / `held`), `trashed_at`, tombstone `deleted_at`. No FKs
  on `vehicle_id` / `parent_id` (owner, 2026-11-07: sync order).
- **GPS storage:** live fixes are `trip_points` rows (WITHOUT ROWID, PK `(trip_id, sequence)`, FK
  CASCADE); on completion `TrackCodec` packs them into `trip_tracks` (ADR 0004). Measured on the
  owner's pulled database: 19 drives, 50 744 fixes, 442 KB → **8.7 bytes a fix**.
  `trip_points.source` (default `core_location`) is never written by code and **not in
  `TrackCodec`**, so it is lost on packing: it is not a provenance field.
- **Derived metrics:** `trips.distance_m`, durations, speeds, `departed_at`/`arrived_at` are
  derived from the GPS track by `RouteRecorder`; `recorder_version` is their provenance and
  `SummaryRefresh` re-derives older ones. `route`, `trip_gaps`, places, narrative are derived and
  rebuildable. GPS distance ≠ odometer (P2).
- **Vehicle identity and odometer:** `vehicles.id` UUID, archived not deleted (ADR 0014);
  odometer only in `vehicle_logs.odometer_m` / `fuel_logs.odometer_m`, entered by the person
  (ADR 0016/0017). `vehicle_links` = car audio (CarPlay / Bluetooth), **one live link per vehicle**
  (unique index), port name private.
- **`.carodo`:** header `CARODOBK` · file version byte (1) · flags · zlib(JSON) [AES-GCM].
  `BackupDocument.formatVersion` 1; optional fields added without a bump; `JSONDecoder` ignores
  unknown keys (`BackupTests.testFieldsALaterBuildAddsAreIgnored`). A newer file version is
  refused cleanly (`Failure.newerVersion`). The whole document is one JSON in memory, tracks as
  base64.
- **Sync:** iCloud record types `Vehicle`, `VehicleLog`, `FuelLog`, `Place`, `Trip`; payload =
  the backup shapes (`CloudPayload` v1, unknown fields ignored); a trip's packed track is a
  `CKAsset`. Backend gets only published/shared summaries; optional encrypted backup (ADR 0011)
  carries summary + packed track.
- **Hard-coded per-trip table lists** in three places: `GRDBLocalDataStore.erase` (all tables),
  `GRDBJourneyRepository.erase(_:journeys:)` (tombstoned trip: `trip_points`, `trip_tracks`,
  `trip_gaps`, deleted explicitly because the row stays, so CASCADE never fires), and CASCADE for
  trips never synced.

### Couplings that would cost a large change later

| # | Coupling | Risk | Proposal |
|---|---|---|---|
| C1 | **Schema change = erase.** Pre-release the only way to change the schema wipes real test drives on every iPhone. | Every telemetry/schema step costs the testers' drives, or is postponed. The brief forbids it. | **Freeze `v1_initial` now; every change from here is a registered, additive migration** (`v2_…`). |
| C2 | `task device` compares schemas for equality. | The first additive migration is reported as "ERASES the drives". | Ask the build's migrator instead: `hasSchemaChanges` on a copy of the phone's DB (erase only if true). |
| C3 | Per-trip data deleted by hand-kept table lists. | A new per-trip table forgotten in the tombstone path keeps data of a deleted drive (privacy). | One list (`TripOwnedData`) used by both erase paths; a test that every table with a `trip_id` is in it. |
| C4 | `trip_points.source` is undefined and **not kept by `TrackCodec`**: lost when the drive packs. | Read as a generic sensor switch (OBD rows "with `source = obd`"), or trusted as provenance it cannot give. | Define it as the **spatial location source** (§2a); OBD never enters `trip_points`. Codec provenance designed for a later version, not built now. |
| C5 | `vehicle_links` is one car-audio link per vehicle (index, repository writes, `CarConnections`), while `VehicleLink.swift` and `auto-mode.md` say an OBD adapter plugs in there. | Adding a kind as-is: linking audio deletes the adapter link, `link(for:)` may return the adapter. | **Option A (§2b):** typed vehicle-device associations with a `role`; every audio path scoped to `role = 'car_audio'`. |
| C6 | `.carodo` is one in-memory JSON. | A year of telemetry (~70–150 MB, §6) base64-inflated in one JSON can get the app killed. | No change now: the file-version byte already negotiates; telemetry ships with file version 2 (sectioned) or stays out of `.carodo` (§5). |

Not couplings (checked, keep): trip identity and lifecycle; trip figures as GPS-derived with
`recorder_version`; odometer only as the person's readings; `trip_tracks` per drive; one database
file. The `trips` table already owns the timeline (`started_at`/`ended_at`/status) separately from
the GPS track, so no refactor of `trips` is needed.

## 2a. `trip_points.source` — the spatial location source (owner, 2026-11-09)

**Definition:** where the position of this fix came from. Values (TEXT, `LocationSourceKind`, the
list grows): `core_location` (today, the default), later `external_gnss` (a GNSS receiver over
BLE), `imported` (a GPX/track import), others that give a position. It never names a sensor that
gives no position: OBD-II, Core Motion and the barometer are not location sources (the barometer's
`pressure_kpa` stays a field of the fix it was read with).

Audit:

- Nothing writes it (`TripWriter` relies on the default) and nothing reads it; `TripSample` has no
  source; `TrackCodec` v2 has no field for it. So today it says "core_location" while live and
  disappears at completion.
- That is truthful for every existing drive: Core Location has been the only source. A v2 track
  therefore decodes as `core_location`, by definition and without a backfill.

Future codec (designed, **not built in this phase**):

- `TrackCodec` v3 adds a **source dictionary** after the count (varint n, then n short strings,
  index 0 = `core_location`) and uses the free **flags bit 7** = "source changes at this fix",
  followed by a varint index. A drive from one source costs a few bytes in total; a drive that
  switches (external GNSS drops out, the phone takes over) costs ~2 bytes per switch.
- **Write the lowest version that holds the data:** a track whose every fix is `core_location`
  stays v2, so older builds (and iCloud / `.carodo` readers on them) keep reading it; only a track
  with another source is written v3, and an older build reports it `unsupportedVersion` (exists)
  instead of misreading it.
- `TripSample` gains `source` in that change; `RouteRecorder` filters may treat sources
  differently (accuracy semantics differ for an external receiver).
- A trip whose fixes all come from an import may also carry it at the trip level (provenance of
  the whole drive, `start_trigger = imported`); decided with the import feature.

Change now: the column comment and `docs/data-model.md` row ("spatial location source; OBD-II
never"), and the ADR. No schema or codec change.

## 2b. `vehicle_links` — typed vehicle-device associations (Option A)

### Audit

- **Columns:** `id`, `vehicle_id` (FK CASCADE), `kind` (`carplay` / `bluetooth_audio`), `port_uid`,
  `name` (the port's name, private), `created_at`, `ck_*`, `deleted_at`.
- **Indexes:** `vehicle_links_on_vehicle` UNIQUE(`vehicle_id`) and `vehicle_links_on_port`
  UNIQUE(`port_uid`), both WHERE `deleted_at IS NULL`.
- **Writes (`GRDBVehicleRepository`):** `link(_:to:)` tombstones every live link `WHERE vehicle_id
  = ? OR port_uid = ?`, then inserts; `unlink(vehicleID:)` tombstones **every** link of the
  vehicle; deleting a vehicle tombstones its links. Archiving keeps them (ADR 0014).
- **Reads:** `links()` returns every live link with a known kind (unknown kinds skipped:
  forward-compatible). `CarConnections` matches the current audio route by `portUID` only
  (`linkedVehicle(for:)`), shows `link(for: vehicleID)` = **the first** link of the vehicle, and
  `unlink` reads that link's kind for the log and the auto-finish hint (`onCarAudioChange`).
- **Automatic behaviour, all audio-only:** CarPlay links itself with one car; CarPlay with an
  empty garage adds the first car; "Not a car" (`carodo.notCarAudio`, UserDefaults) and
  `firstCarAddedFrom` hold port UIDs. Car-audio disconnect is a hint, never the end (P4).
- **Spec (`docs/specs/auto-mode.md`):** each vehicle has one audio link, each audio device belongs to
  one vehicle, a new device for a vehicle replaces its old link.
- **Lifecycle:** created while connected (iOS lists no paired devices), replaced, tombstoned with
  the vehicle, kept while archived. Local today: not in iCloud (`docs/sync.md`: "Not synced yet:
  vehicle links") nor in `.carodo`, though the `ck_*` columns exist.
- **Identifier semantics:** `port_uid` is `AVAudioSessionPortDescription.uid`, opaque, issued by
  iOS's audio system. An OBD BLE adapter's identifier would be `CBPeripheral.identifier`: opaque,
  issued by Core Bluetooth, **scoped to this iPhone** (another iPhone sees another UUID).

### Domain fit

The association is the same fact for both: **"when this device is present, the phone is in this
vehicle"**. Same lifecycle: created by the person (or by a sure automatic rule), a device belongs
to one vehicle at a time, moved by re-linking, tombstoned with the vehicle, kept while archived.
An adapter is plugged into one car exactly as a car's CarPlay belongs to it.

What differs is **not** the association:

- Car audio is observed passively (route change); an adapter is connected actively (Core
  Bluetooth central, the `bluetooth-central` background mode: P6 later). That is the connection
  and its sessions (`telemetry_sessions`), not the link.
- Adapter facts (protocol, firmware, supported PIDs, VIN read) change per connection: they belong
  to the session's `metadata`, not to the link.
- Audio-only rules (first car from CarPlay, only-car linking, "Not a car") stay in
  `CarConnections`, keyed on the audio role.

So A does not force two lifecycles into one abstraction: the link stays a small association;
connection lifecycles live elsewhere for both.

### A vs B

| | A. Typed associations in `vehicle_links` | B. `vehicle_links` audio + `vehicle_adapters` |
|---|---|---|
| Domain | One concept, "device identifies vehicle", one place to answer "which devices does this car have" (Garage, delete, archive, sync) | Two tables for the same fact; delete/archive/sync written twice |
| Code change | Scope 3 writes + 1 read to the audio role; new role gets its own repository calls | None in audio code |
| Regression risk | Real but contained: an unscoped query would touch the adapter link. Covered by tests | None |
| Audio-specific fields | `port_uid` → generic `device_uid`; `name` already generic (device's own name); `kind` already a device kind | n/a |
| Sync later | One record type `VehicleLink` | Two |

**Recommendation: A**, because the semantics are the same and the cost is a role filter. B would
only be right if adapters needed per-link state of their own, which the audit places in sessions.

### Schema under A

```text
vehicle_links
  id, vehicle_id                       -- unchanged
  role        TEXT NOT NULL DEFAULT 'car_audio'   -- VehicleLinkRole: car_audio | obd_adapter (new)
  kind        TEXT NOT NULL            -- transport within the role: carplay | bluetooth_audio | obd_ble | obd_wifi
  device_uid  TEXT NOT NULL            -- renamed from port_uid; opaque id issued by the OS framework of `kind`
  name        TEXT NOT NULL            -- the device's own name; private, never logged (P5)
  created_at, ck_pending, ck_metadata, deleted_at   -- unchanged

vehicle_links_on_vehicle  UNIQUE (vehicle_id, role)  WHERE deleted_at IS NULL
vehicle_links_on_device   UNIQUE (role, device_uid)  WHERE deleted_at IS NULL
```

- `role` is a column, not derived from `kind`, so the unique indexes never list kinds (a new audio
  transport needs no index rebuild) and `kind` stays checked by the app.
- **Cardinality:** one live link per (vehicle, role): a car keeps its audio link **and** an
  adapter; car audio stays one per vehicle as the spec says; an adapter belongs to one vehicle.
  Several adapters for one car: not supported (no use case); relaxing it is an index change only.
- `device_uid` is scoped by its framework: an `obd_ble` uid matches only on the iPhone that paired
  it. When links sync, an adapter link from another iPhone is kept but never matches here; the
  ingestion may later confirm a car by the VIN it reads (never stored in clear: P5).

### Code changes that make A safe (with the slice that lands the schema)

- `VehicleLink` gains `role`; `VehicleLinkKind` cases carry their role; `CarAudioPort` stays audio.
- `link(_ port: CarAudioPort, to:)`: tombstone `WHERE role = 'car_audio' AND (vehicle_id = ? OR
  device_uid = ?)`. `unlink(vehicleID:)` → `unlink(vehicleID:role:)`. Vehicle delete keeps
  tombstoning all roles (correct for both).
- `links()` keeps returning every role; `CarConnections` keeps only `role == .carAudio` when it
  loads, so `linkedVehicle(for:)`, `link(for:)`, first-car and only-car rules never see an adapter.
- Tests: an adapter link survives linking, relinking and unlinking car audio; a car-audio port and
  an adapter with the same uid string do not collide; `CarConnections` ignores adapter links;
  deleting a vehicle tombstones both; existing `CarConnections` tests unchanged.

### Migration under A

Rows existing today all become `role = 'car_audio'` by the column default; kinds and uids are
kept as they are. In a registered migration: `ADD COLUMN role … DEFAULT 'car_audio'`, `RENAME
COLUMN port_uid TO device_uid` (SQLite 3.25+, iOS 18 ships 3.43), drop the two old indexes,
create the two new ones. Each existing vehicle has at most one live link and each port one, so
the new unique indexes cannot fail on existing data. Or, while `v1_initial` is still edited in
place, the same in `v1_initial` with the erase cut-over: that choice waits on decision C1.

## 2. Proposed schema (migration `v2_vehicle_telemetry`)

Storage choice: **chunked, packed per channel, written as the session goes** — not one row per
reading, and not `trip_points`-style rows packed at the end.

| Option | Bytes / reading | 1 h at 10 readings/s | Writes | Verdict |
|---|---|---|---|---|
| Row per reading (`session, at, channel, value`) + index | ~60–80 | ~2.5 MB (≈100× the GPS track) | one insert per reading | rejected |
| Typed wide row per tick (rpm, speed, …) | ~40 | ~1.4 MB, NULL-heavy; a new PID = new column | per tick | rejected |
| Rows while live, packed at end (as GPS) | rows then ~2–3 | ~2.5 MB live, ~100 KB after | per reading + one pack | works, but doubles writes and needs the pack on the end path |
| **Chunks: ~30 s of one channel per blob** | ~2–3 + ~60 per chunk | **~100–150 KB** | **one transaction per flush (all channels)** | **chosen** |

Why chunks: telemetry is optional, so losing the last ≤30 s in a crash is acceptable (GPS is not:
it keeps rows). It removes the pack step from the drive's end path, keeps write amplification
low, and a range read by `(session, channel, time)` decodes only the chunks needed.

```text
telemetry_sessions            -- one connection of one adapter during one trip
  id                TEXT PK   -- UUID on device
  trip_id           TEXT NOT NULL   -- no FK (owner 2026-11-07; may sync before its trip); cleaned in TripOwnedData
  vehicle_id        TEXT            -- no FK; NULL = not known
  source_kind       TEXT NOT NULL   -- 'obd2' (TelemetrySourceKind; the list grows)
  link_id           TEXT            -- the vehicle_links row (role obd_adapter) it connected through; no FK; NULL = not linked
  protocol          TEXT            -- e.g. 'iso15765_11bit_500k'; NULL = unknown
  status            TEXT NOT NULL   -- recording | completed | interrupted
  started_at        REAL NOT NULL
  ended_at          REAL
  end_reason        TEXT            -- disconnected | trip_ended | failed …
  metadata          TEXT            -- JSON: supported channels, adapter firmware; never location
  codec_version     INTEGER NOT NULL   -- the chunk codec this session's chunks use
  created_at, updated_at REAL NOT NULL
  index telemetry_sessions_on_trip (trip_id, started_at)
  index telemetry_sessions_on_recording (started_at) WHERE status = 'recording'

telemetry_chunks              -- rowid table: the blob is large (as trip_tracks)
  id                INTEGER PK
  session_id        TEXT NOT NULL REFERENCES telemetry_sessions ON DELETE CASCADE
                                    -- strict ownership: a chunk always travels with its session
  channel           TEXT NOT NULL   -- stable key carrying its unit: 'engine_speed_rpm',
                                    -- 'vehicle_speed_mps', 'coolant_temperature_c', 'fuel_rate_lph' …
  sequence          INTEGER NOT NULL
  first_at, last_at REAL NOT NULL
  sample_count      INTEGER NOT NULL
  data              BLOB NOT NULL   -- time deltas (ms) + value deltas (per-channel scale) + quality flags, zlib
  unique index telemetry_chunks_on_channel (session_id, channel, sequence)
  index telemetry_chunks_on_time (session_id, channel, first_at)
```

- **Measurement type, value, unit:** `channel` names the quantity and its unit (naming rule:
  unit in the name, SI at rest; °C and percent are the exceptions OBD reports, named in the key).
  The channel catalog (scale, range, PID mapping) is code, versioned with `codec_version`.
- **Quality:** a per-reading flag bit (invalid / no data / estimated), not a column.
- **Timestamps:** device clock at receipt (injected clock); GPS fixes use `CLLocation.timestamp`.
  Alignment rules (adapter latency) are decided with the ingestion, not stored now.
- **Nothing is written by v2.** No codec, no writer, no reader in this step. No rows for old
  journeys.
- **Not synced yet:** no `ck_*` columns. When telemetry syncs it becomes its own record type
  (`TelemetrySession`, chunks as a `CKAsset`) and gains `ck_pending`/`ck_metadata`/`deleted_at`
  additively, per `docs/sync.md`.
- **Not in v2, on purpose (additive later, no lock-in):** VIN (identifies a car like a plate: P5), telemetry-derived summary columns (fuel used, idle
  time: once channels are known), a `source` on `vehicle_logs` for an OBD odometer reading (most
  cars don't expose it).

## 3. Existing fields

- **Keep unchanged:** all of `trips` (figures stay GPS-derived; canonical distance unchanged),
  `trip_points` (spatial fixes only), `trip_tracks`, `TrackCodec` v2, `vehicles`, `vehicle_logs`,
  `fuel_logs`, `recorder_version` semantics.
- **Refactor:** `vehicle_links` to typed associations (§2b); C3 `TripOwnedData` list.
- **Define:** `trip_points.source` as the spatial location source (§2a).
- **Rules added to docs:** telemetry never writes a `trips` figure, never fills `trip_points`,
  never writes `odometer_m`; an OBD-derived figure is shown as its own value with its source.

## 4. Migration plan

1. `v1_initial` frozen: byte-for-byte as on the phones today; a comment says so.
2. Register `v2_vehicle_telemetry`: two `CREATE TABLE` + four `CREATE INDEX`. Nothing touches an
   existing table. GRDB runs it in one transaction; `eraseDatabaseOnSchemaChange` erases only if
   an applied migration's schema changed, which it does not.
3. `task device` / `device-all` (C2): the schema check becomes "would this build erase this
   database?": a test (env-gated like `SchemaDumpTests`) opens the copied DB and answers with
   `migrator.hasSchemaChanges`; "migrates" installs, "erases" still needs `CONFIRM=erase`.
4. iOS invariant 6 and `docs/data-model.md`: "pre-release, schema changes are additive
   registered migrations; `v1_initial` is never edited again". (The first-release rule, additive
   only, simply starts now.)

Tests (`DatabaseMigrationTests`):

- **Upgrade with data:** migrate an in-memory DB `upTo: "v1_initial"`, insert synthetic data of
  every kind (completed trips with packed tracks, a `recording` trip with `trip_points`, joined
  parts, trashed and tombstoned trips, vehicles, links, logs, fuel, places, badges, outbox,
  `tracking_events`, `cloudkit_state`); run the full migrator; assert every pre-existing table's
  rows are identical (per-table checksum), `hasSchemaChanges` was false, telemetry tables empty,
  `PRAGMA foreign_key_check` clean, `trips` figures unchanged, a recording trip still recovers.
- **Fresh install** = upgrade: the schema from scratch equals the schema after upgrading.
- **Idempotent:** a second migrate is a no-op.
- **Ownership:** deleting / tombstoning a trip removes its telemetry sessions and chunks; erase-all
  empties them; every table with `trip_id` is in `TripOwnedData`.
- **Index plans:** `SchemaIndexTests` gets the two telemetry queries (by trip; by
  session+channel+time).
- **Real data, local only:** an env-gated test runs the migrator on a **copy** of each
  `drive-data/*.sqlite` and compares row checksums before/after (never committed, nothing printed
  but counts). Then one `task device` install on the owner's iPhone, check the journal intact.

## 5. `.carodo` compatibility

No change to the reader/writer now: there is no telemetry to write, and the format already has
both negotiation levels. Future contract (recorded in the ADR):

- **Small additions** (session list, summaries): optional JSON fields, `formatVersion` unchanged;
  older builds ignore them (tested today). An older build that restores and re-exports drops them:
  accepted and stated.
- **Large data** (chunks): file version 2, a sectioned container (a manifest plus sections read one
  at a time, the GPS part first), because a JSON in memory does not scale to telemetry. Older builds
  refuse it with "made by a newer Carodo" (exists). A v2 build still reads v1.
- **Unknown sections** are skipped; **missing telemetry** is normal (a journey with none); a
  damaged telemetry section never fails the GPS restore; telemetry decoding gets bounds like
  `TrackCodec.maxUnpackedBytes`.
- Including telemetry in an export may be a choice (size).

## 6. Performance and reliability

- **Volume:** an ELM327-class BLE adapter answers ~10–20 PIDs/s in total. At 10 readings/s:
  ~36 000/h → ~100–150 KB/h packed. Two hours a day ≈ 70–110 MB/year, **3–5× the GPS track**
  (8.7 B/fix ≈ 31 KB/h). Rows would be ~1.8 GB/year.
- **Writes:** one transaction per ~30 s flush, all channels, a few KB. GPS batches keep their
  cadence; WAL has one writer, and the flush is short and never inside a `TripWriter`
  transaction.
- **Isolation:** the ingestion is a separate service with its own in-memory buffer (bounded), its
  own writer calls and its own errors; a telemetry failure is logged (no values tied to place) and
  ends the session, never touches recording. GPS never waits for, reads or depends on telemetry.
  The tracking path does not import telemetry code.
- **Background:** BLE in the background needs `bluetooth-central` (a P6 entitlement decision for
  the adapter step), not now.
- **Memory:** readers decode chunk ranges, never a whole session at once.
- **Retention:** later setting ("keep raw telemetry N months, keep its summary"); chunks deleted
  per session, journey untouched. Deferred.
- **Alternative considered:** a second SQLite file for telemetry (separate writer lock, failure
  isolation). Rejected for now: it breaks atomic ownership with trips and invariant 1 ("no second
  local store"); revisit only if a device measurement shows write contention.

## 7. Now vs later

| Now (Step B) | Later, additive, no lock-in |
|---|---|
| Freeze `v1_initial`; registered migrations (C1) | Chunk codec and channel catalog |
| `task device` check by `hasSchemaChanges` (C2) | Adapter table, BLE, polling, `bluetooth-central` |
| `v2_vehicle_telemetry` (2 tables, 4 indexes) | iCloud record type, `ck_*` columns |
| `TripOwnedData` + tests (C3) | `.carodo` file version 2 / telemetry sections |
| `trip_points.source` defined as spatial source (C4) | `TrackCodec` v3 source dictionary, `TripSample.source` |
| `vehicle_links` role + `device_uid` + scoped audio paths (C5) | `obd_adapter` links written (with pairing) |
| | Derived telemetry summaries, VIN, OBD odometer provenance |
| Migration + compatibility tests; real-data local check | Retention setting |

## 8. ADR and docs

- **ADR 0019** "Vehicle telemetry is an optional source beside GPS": sessions per trip, chunked
  storage, never a GPS figure or the odometer, isolation from recording, `.carodo` contract,
  `trip_points.source` as the spatial location source (codec v3 rule), `vehicle_links` as typed
  vehicle-device associations (one live link per vehicle and role). `docs/specs/auto-mode.md`
  (links section) follows.
- **ADR 0003 or `docs/data-model.md`** (wherever the migration rule lives): registered additive
  migrations from now.
- `docs/data-model.md` (tables, indexes, migration section), `docs/architecture.md` (telemetry
  beside the drive pipeline), `docs/specs/backup.md` + `docs/sync.md` (future contract, short),
  `docs/operations/device-testing.md` (the new install check), `docs/decisions/README.md` index.
- `carodo-ios/AGENTS.md`: iOS invariant 6 rewritten; one new iOS invariant: "Telemetry is a
  separate source: never on the tracking path, never in `trip_points`/`trip_tracks`, never a trip
  figure or an odometer reading." Workspace `AGENTS.md` mirrors the migration rule line.

## Decisions (owner, 2026-11-09)

1. **`v1_initial` stays edited in place** until TestFlight preparation, where freezing and
   versioned migrations are reassessed. A controlled reset is accepted; a database holding real
   test journeys is never erased without a backup and an explicit confirmation (`task device`
   `CONFIRM=erase`). C1/C2 deferred to that review.
2. **Telemetry schema deferred.** No `telemetry_sessions`/`telemetry_chunks`; §2 is the logical
   design, kept in ADR 0019. Tables, chunk codec, retention, sync decided with real ingestion,
   tried in DEBUG first.
3. **`vehicle_links`: Option A**, built as §2b. One adapter per vehicle is the first policy.
4. **`telemetry_sessions.trip_id` nullable:** journey-linked or standalone (diagnostics, periodic
   check, adapter test). No fake journey; standalone sessions own their cleanup and retention and
   are never deleted with a journey nor attached to one by timestamps alone.
5. **`trip_points.source`:** the spatial location source (§2a); codec v3 designed, not built.

The sections above still describe the deferred telemetry tables with `trip_id NOT NULL`; decision 4
replaces that when the ingestion slice designs them.
