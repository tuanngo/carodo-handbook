# New roads per drive (`new_road_m`)

Status: **approved** (owner, 2026-11-15: D1–D6 as recommended; table name `trip_new_roads`).
Slice 1 next. Discussed with the owner on 2026-11-15: compute from the trips, not from a stored cell
table like carstack's; the owner's concern is performance, answered in "Performance" below.

## Frame

**Outcome.** Every completed drive knows how many metres of road it drove **for the first time**,
counted on the same 20 m grid as the Map's Discovery layer. Journey Detail can say "2.4 km of new
road", and the Passport can sum new road for All time, This year and This month with one indexed
query (`trips` joined to a small side table by primary key), with no route loaded.

**User story.** As a driver I want to see how much of a drive was new road, and how much new road I
discovered this month or this year, so exploring feels like progress.

**Why now.** `visited_cells` is a reserved table nothing writes, on a grid no feature uses, and it
holds the one foreign key outside a trip's own rows (TD-7). The backlog reserves a per-drive new-road
figure. The Discovery layer (carodo-ios `08a6216`) already computes, in memory, when each road was
first driven: the figure is that, per drive.

## What the code does today (read 2026-11-15)

| Fact | Where |
|---|---|
| `visited_cells(cell_x, cell_y, first_trip_id → trips SET NULL, first_at)`, WITHOUT ROWID, 1/400° (~280 m) grid. **Nothing writes it**; only Erase data and tests touch it | `Carodo/Core/Persistence/DatabaseManager.swift:432`, index `visited_cells_on_first_trip` (:563), `DataOwnership.swift:57,69,75`, `docs/data-model.md` (`visited_cells`, Indexes, Ownership), `docs/specs/backup.md:132`, tests `DataOwnershipTests`, `LocalDataEraseTests`, `GRDBVehicleRepositoryTests` |
| Three grids for one idea: `visited_cells` 1/400°; `FootprintGrid` zoom-17 tiles (~300 m, Map Footprint and the Passport's explored km²); `HeatGrid` 20 m with a 3 × 3 neighbourhood (Discovery layer) | `HistoryAtlas.swift:77`, `RouteHeat.swift:428` |
| `RouteHeatIndex` keeps per cell the count of distinct drives and `firstDriven` (earliest start among the drives covering it); `add`/`remove` are incremental and return the journeys whose classes changed; passenger drives are excluded | `Carodo/Core/Domain/RouteHeat.swift` |
| `HistoryAtlas` (actor, off the main actor) holds every journey's display route for the Map, loaded through `routes(skipping:)` (journal trips with a route and `confirm_by IS NULL`: pending drives are left out). The heat index is built lazily, the first time Discovery shows, then kept and updated per journey; above 50 changes (or a quarter of the journal) it is dropped and rebuilt | `Core/Atlas/HistoryAtlas.swift:157,171,217–260,328`, `GRDBJourneyRepository.swift:241` |
| Measured (Mac simulator, Release, 2,000 synthetic drives): first Discovery index ~290 ms; one more commute ~1 ms. **Never measured on an iPhone** | `docs/specs/navigation.md` (History at scale) |
| The Passport's exploration card has one period control: All time · This year · This month; a drive belongs to the period it started in | `docs/specs/passport.md` §2 |
| No `new_road`/`roads_version` name exists in code or docs; `RoadDiscovery` (the Map's three classes) is taken | grep 2026-11-15 |
| Reference: carstack (`drive-data/carstack-SQLite/pull-20261112-210950`) stores `visited_cells(cx, cy)` on 1/400° with no owner or time (2,064 cells for 10 drives) and `sessions.new_route_m`, computed once at completion against that set | read locally; not committed, not cited from carodo-ios |

**Why not carstack's way.** Cells with no owner cannot be taken back when a drive is deleted or
trimmed; a drive restored after a newer one counts in the wrong order; ~280 m counts new *area*,
not new *road* (a parallel street 200 m away reads as driven), and differs from the Map's Discovery.
Storing 20 m cells instead would be ~50 rows a km of road, hundreds of thousands of rows that copy
what `trips.route` already holds and must be rebuilt on every edit, restore and iCloud change.
Kept from carstack: **the figure lives on the trip and statistics are a SUM.**

## Proposal

### Data (`v1_initial` edited in place, pre-release)

| Change | Detail |
|---|---|
| Drop `visited_cells` | Table, index `visited_cells_on_first_trip`, its `DataOwnership` reference and lists, the doc rows, the test lines. Resolves TD-7 (the FK goes with the table) |
| New table `trip_new_roads`, WITHOUT ROWID | `trip_id` TEXT PK → `trips(id)` ON DELETE CASCADE (a trip's own derived row, like `trip_gaps`: classified **derived** in `DataOwnership`); `new_road_m` REAL NOT NULL: metres of this drive's display route on 20 m cells no earlier drive covered (the Discovery rule: a cell is new to the drive whose start is its `firstDriven`), a stretch the drive passes twice counted once; `rules_version` INTEGER NOT NULL (`NewRoads.rulesVersion`, bumped when the grid, the neighbourhood or the rule changes). **No row = not counted** (yet, or never: passenger, pending, a joined part; the journey's first part carries it). Derived: never synced, never backed up |

**Why a side table and not two columns on `trips` (owner's question, 2026-11-15: the BLOB lesson).**
SQLite rewrites a whole row on UPDATE. Measured (Mac, sqlite3, WAL, 2,000 rows with a 40 KB route
blob, as a long drive's display route): an UPDATE that keeps the row's size (an integer 0 → 1)
writes ~4 KB a row, 8.2 MB for 2,000; one that changes the size (NULL → a REAL) rewrites the
**blob with it**, 82 MB for 2,000; the same writes on a small WITHOUT ROWID table: 0.12 MB.
Counting writes `new_road_m` (NULL → value), and invalidation writes many rows at once, so on
`trips` they would rewrite the routes again and again. The side table never touches `trips`: its
blobs, `updated_at`, `revision` and iCloud stay as they are. Reads join by primary key.
Real sizes, read locally from two pulled databases of the owner's iPhone (2026-11-10 and
2026-11-13, 22 and 30 drives): display routes average **~2.5–2.9 KB**, largest 20 KB. Most rows fit
one 4 KB page, so the 40 KB case above is the long-drive worst case, not the usual one: a
size-changing UPDATE today costs about one page a row, a few rows of overflow for the longest.

**One side table for places, points and roads too? (owner, 2026-11-15) Not now (D6).**
`places_version` and `points_version` are written once per drive, beside `start_cell`/`end_cell`
on `trips` that change with them; with real route sizes a re-run over 2,000 drives writes about
one page a row (~8 MB, well under a second), and moving them means rewriting four working
pipelines (naming, place detection, gap healing, the narrative) and their work queues for a gain
not measured. New roads differ: their invalidation deletes many rows at once, after any edit of an
older drive, and "no row = not counted" keeps unknown apart from zero. Revisit with a measurement:
if a rules bump over the owner's journal on the iPhone takes over ~1 s or the WAL grows past
~50 MB, the other bookkeeping moves into the same table (renamed `trip_enrichment`, one row per
trip, typed columns; never a key-value table). Recorded as a technical-debt row when this ships.

No new index: the Passport's sum walks `trips_on_journal` (`started_at`, completed, live) and looks
each trip up in `trip_new_roads` by its primary key. Measured on the same file: a SUM over 1,000
of 2,000 trips, 1.7 ms.

**Sum property.** Each cell has exactly one first drive, so the drives' `new_road_m` split the road
the person ever drove: `SUM` over All time ≈ the length of distinct road driven, over a month = the
road first driven that month, never counted twice.

### Invalidation (persistent, so a kill never leaves a stale figure)

A drive's figure depends on every drive that started before it. Every write that adds, removes or
changes the route of a counted drive, or changes whether it counts, runs in the same transaction:

```sql
DELETE FROM trip_new_roads
WHERE trip_id IN (SELECT id FROM trips WHERE started_at >= :startedAt)
```

(small rows only; `trips` is read, never written)

Writes covered: complete (only the new drive, nothing after it in the usual case), delete for good,
trash and restore from Recently Deleted, trim, join and split, rider change (driver ↔ passenger),
a pending drive confirmed (`confirm_by` → NULL), a summary re-derived (`SummaryRefresh`), a trip
saved from iCloud or a `.carodo` restore (the earliest `started_at` of the batch). One statement
over a table in the thousands.

### Computation (one worker, off the main actor)

- Lives with `HistoryAtlas`, which already holds every route and the heat index: one index serves
  Discovery and new roads. A pure `RouteHeatIndex.newRoadM(for:)` gives one drive's figure from the
  index (unit-tested on its own).
- Runs in the after-drive work (beside `points_version`, the narrative), never on the recording or
  finish path, never before the finish banner, and **not while a drive records** (risk prevented:
  CPU and heat during a drive, beside GPS).
- Asks for the counted drives with no row or `rules_version < current`, counts those drives from the index (built if not yet: the one
  expensive step, once per app session), writes in batches of ~200 rows per transaction and only
  rows whose value changed; cancellable, resumes at the next run.
- The usual case, the newest drive: the index is updated with it (~1 ms) and one row is written.

### Reads (never compute)

- `JourneyRepository`: the drive's `newRoadM` with its summary; `newRoadM(from:to:)` = the SUM above.
- A figure not counted yet (no row, or an old version) is **hidden, never 0 km**; while any drive
  of a period waits, the Passport hides that period's sum rather than show a short one (AGENTS.md, Unknown is
  not zero). Metres at rest, km/mi only in the View.

### Performance budget (opt-in test, `CARODO_PERF=1`, Release, 2,000 synthetic drives)

| Measure | Target |
|---|---|
| Count every drive from scratch (index built + all rows written) | < 1 s on the owner's iPhone; recorded on the Mac simulator too |
| One new drive (index already built) | < 10 ms |
| Passport sum for a period | < 5 ms |
| Main-thread hangs during either | none |
| Memory of the kept index | measured; if large, release it after counting while Discovery is not shown |

Fallback, only if the iPhone misses the first target: a local, rebuildable cell cache table keyed
by `roads_version`, in its own ADR. Not built now.

## Slices

1. **Schema.** Drop `visited_cells`; add `trip_new_roads`; invalidation in every listed write path
   (one helper in the repository, called from each). Tests: migrator on an in-memory
   `DatabaseQueue`; each write path deletes the rows of itself and later drives, never of earlier
   ones, and leaves `trips` unwritten; deleting a trip cascades its row; `DataOwnership` and Erase
   tests updated. Docs: `data-model.md` (the new table, the dropped one, Indexes, Ownership),
   `backup.md`. TD-7 resolved. Devices reinstall with `CONFIRM=erase`.
2. **Counting.** `RouteHeatIndex.newRoadM(for:)` + the worker. Tests: a drive on new ground counts
   its length; the same road again counts 0; a road 10 m beside an old one counts 0, 60 m beside
   counts; a drive passing its own new road twice counts it once; passenger and pending get no row;
   deleting the first drive moves its new road to the next drive over the same road; the sum over
   drives equals the distinct road; out-of-order arrival (newer first, older later) ends with the
   same figures as in order. Perf test with the budget above. Docs: `docs/specs/navigation.md`
   (Discovery: the shared index), `docs/architecture.md` (algorithms: new roads reuse
   `RouteHeatIndex`).
3. **Showing it** (after D3): Journey Detail line and the Passport figure for the chosen period,
   copy in English and Vietnamese, screenshots Light/Dark, xxxLarge, Vietnamese. Docs:
   `docs/specs/journeys.md`, `docs/specs/passport.md`.

Each slice is one commit in carodo-ios once lint, warnings and tests pass; slice 3 waits for the
owner's look on screen.

## Owner decisions

| # | Question | Recommendation |
|---|---|---|
| D1 | Drop `visited_cells` (not rename) | **Drop.** "Visited" clashes with the Passport's *visited* (where a drive ended) vs *passed through*; the grid fits nothing; a cache, if ever needed, is `footprint_cells` or a roads cache with its own ADR |
| D2 | Where and what names | **A side table `trip_new_roads(trip_id, new_road_m, rules_version)`**, not columns on `trips` (measured: a size-changing UPDATE on `trips` rewrites the route blob); `new_road_m`, not carstack's `new_route_m` ("route" is a drive's display route here; the Map says "New roads") |
| D3 | Where it shows | Journey Detail: one line in the summary when ≥ 100 m ("2.4 km of new road"); Passport: beside the explored area, following the period control. Copy and placement checked on the iPhone |
| D4 | A new-area figure (~300 m squares, km²) per drive | **Not now** (no reader; the Passport's explored area already exists); same pass and version if it comes |
| D6 | Move `places_version`, `points_version` (and other bookkeeping) into the same side table | **Not now.** Real routes average ~2.5 KB, so their rewrite costs about one page a row; moving them reworks four pipelines for an unmeasured gain. Trigger to revisit: a rules bump over the owner's journal > ~1 s on the iPhone or WAL > ~50 MB; then one `trip_enrichment` table with typed columns |
| D5 | Send it to the backend (Feed) | **Not in V1.** It reveals no place, but it changes when older drives are restored (a re-publish), the backlog keeps it on device, and a `DriveInput.newRoadM` field is a contract change (P6) |

## Non-goals

A stored cell table; map matching to real road segments (new dependency or service, P6/P5);
"% of a city driven" (needs boundaries, no data source); badges on new road (a later Passport idea);
any change to how Discovery classifies or draws.

## Assumptions not checked yet

- A joined journey reaches `HistoryAtlas` as one route under its first part's id (the figure is
  stored there): check `routes(skipping:)` and the parts read before slice 2.
- Every write path listed above goes through `GRDBJourneyRepository` (or the iCloud and restore
  stores) where the invalidation can run in the same transaction: list them in slice 1.
- iPhone timing is unknown until measured (the simulator's 290 ms is the only number).

## Validation

`task lint`, `task warnings`, `task test`; `CARODO_PERF=1` perf test in Release on the simulator
and once on the owner's iPhone (device check, `docs/operations/device-testing.md`, Measuring
performance). Real drives in `drive-data/` may be used locally to compare figures with the Map's
New roads; nothing from them is committed.
