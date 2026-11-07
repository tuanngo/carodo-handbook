# Badge ledger, sync and vehicle archive (draft for review, 2026-11-05)

Status: **Approved 2026-11-05** (with the three assumptions confirmed). The binding text now
lives in carodo-ios ADR 0013 and 0014, `docs/data-model.md`, `docs/sync.md` ("Badges"),
`docs/api/carodo-api.yaml` 0.24, `docs/specs/garage.md`, `docs/specs/feed.md`, and carodo-app
`0001_baseline.sql`; where this draft disagrees, those win. Changes made on approval:
- `instanceRef` is a **random `public_ref`** created at the first publish and replaced when the
  account changes, not a hash of the vehicle id (a hash would link two accounts of one person).
- The **publication revision protocol** (`sync.md`): a new action writes
  `max(publication_revision, server_revision) + 1`; equal revisions go to `private`; equal
  `published` states keep the lower `public_ref`; a device whose `public_ref` lost a merge hides
  the old one.
- Unlocks stay immutable in normal use; **repair** (after restore or import) may move an unlock
  to an earlier crossing, never a later one; **Erase all data** removes the ledger and the zone.
- Hiding a badge hides its Feed item; publishing it again restores the same item
  (`posted_threshold`, `posted_at` kept).

Three layers, one role each:

| Layer | Holds | Built in |
|---|---|---|
| Device (GRDB), authoritative | the unlock ledger (immutable facts) and each badge instance's state (seen, publication) | slice 3 |
| The person's iCloud (CloudKit private DB) | a private replica of both, with the journal | slice 3 |
| Carodo backend | only what the person chose to publish: a showcase, never the ledger | slice 4 |

Scope stays ADR 0013: **Road Miles** and **Faithful Car** only. No points, levels, streak, night,
frequency or speed achievements. Cartographer, Trailblazer, Road Warrior and Full Circle are
future candidates, each needing its own product and safety review; nothing here implements them.

---

## 1. Identity: stable ids, never positions

- **Badge id** — stable, never reused: `road_miles`, `faithful_car`.
- **Tier id** — stable within its badge, never renamed, never reused: `km_100`, `km_500`,
  `km_1000` … A tier's threshold never changes under the same id; a different threshold is a new
  tier id and the old one is retired. Order on screen comes from the threshold, never from the
  id or a position, so inserting a tier later changes no stored meaning.
- **Scope** — what one badge instance is about, declared by the definition:
  - `lifetime` → instance key `""` (Road Miles)
  - `vehicle` → instance key = the vehicle's UUID (Faithful Car)
  - `period` → reserved in the schema (e.g. `2026-11`), **no rule uses it**; the app ignores a
    definition with a scope it does not know.
- **Badge instance** = (badge id, instance key). **Unlock** = (badge id, instance key, tier id).
- **Threshold snapshot** — every unlock stores the metric and threshold it crossed, so it keeps
  its meaning if the catalogue later retires that tier. A tier's label is formatted from the
  snapshot ("1,000 km"), so a retired tier still reads correctly without catalogue names.

## 2. Local schema (P6, edits `v1_initial` pre-release)

Two tables: history that never changes, and state that does (owner point 3: visibility is an
explicit field, never inferred from a timestamp).

```sql
-- Immutable facts: a tier crossed, once, forever (ADR 0013: a tier never goes down).
CREATE TABLE badge_unlocks (
  badge_id      TEXT NOT NULL,
  instance_key  TEXT NOT NULL DEFAULT '',      -- '' lifetime; the vehicle UUID for a per-car badge
  tier_id       TEXT NOT NULL,
  metric        TEXT NOT NULL,                 -- snapshot: 'total_distance_m' | 'vehicle_distance_m'
  threshold     REAL NOT NULL,                 -- snapshot, in the metric's SI unit (metres)
  earned_at     REAL NOT NULL,                 -- the crossing drive's end (UTC epoch), not when computed
  trip_id       TEXT REFERENCES trips (id) ON DELETE SET NULL,  -- the drive that crossed it
  created_at    REAL NOT NULL,                 -- when this device recorded it (local audit only)
  needs_push    INTEGER NOT NULL DEFAULT 0,
  ck_system_fields BLOB,
  deleted_at    REAL,                          -- tombstone, only for an erase (section 4)
  PRIMARY KEY (badge_id, instance_key, tier_id)
) WITHOUT ROWID;
CREATE INDEX badge_unlocks_on_trip ON badge_unlocks (trip_id) WHERE trip_id IS NOT NULL;  -- Journey Detail stamp

-- Mutable, one row per badge instance: what the person has seen and chosen to show.
CREATE TABLE badge_states (
  badge_id      TEXT NOT NULL,
  instance_key  TEXT NOT NULL DEFAULT '',
  seen_threshold REAL NOT NULL DEFAULT 0,      -- the highest unlocked threshold the person has seen
  visibility    TEXT NOT NULL DEFAULT 'private' CHECK (visibility IN ('private', 'published')),
  published_tier_id TEXT,                      -- the tier shown while published (the person's choice)
  publication_revision INTEGER NOT NULL DEFAULT 0,  -- bumped by every publish or unpublish
  publication_changed_at REAL,
  server_revision INTEGER NOT NULL DEFAULT 0,  -- the highest revision the backend acknowledged
  updated_at    REAL NOT NULL,
  needs_push    INTEGER NOT NULL DEFAULT 0,
  ck_system_fields BLOB,
  deleted_at    REAL,
  PRIMARY KEY (badge_id, instance_key)
) WITHOUT ROWID;
```

- No foreign key from `instance_key` to `vehicles`: vehicles are archived, never deleted in the
  normal flow (section 6), and a restore can bring unlocks before their vehicle row.
- `trip_id` is local-only meaning: it never leaves the device except to the person's iCloud.
- The engine only **inserts** unlocks; nothing updates an unlock except the foreign key nulling
  `trip_id` when its drive is purged.

**Engine rule (pure, `AchievementEngine`):** walk the counted drives in start order (completed,
not trashed, the person driving); the running sum per instance crosses each threshold at one
drive; that drive and its end time become `trip_id` and `earned_at`. Insert every crossed tier
that has no unlock row. Never delete when a sum falls (drives deleted). Deterministic: two
devices with the same journal compute the same rows.

## 3. iCloud (CloudKit private DB)

- Two record types: `BadgeUnlock` (record name `unlock.<badge>.<instance>.<tier>`) and
  `BadgeState` (`state.<badge>.<instance>`); payload JSON in `encryptedValues`, like `Place` and
  `Trip`. Deterministic record names mean two devices that earn the same tier write the same
  record, and the conflict rules below settle it.
- The `.carodo` file backup carries both arrays (`BackupBadgeUnlock`, `BackupBadgeState`; older
  files without them restore with none and the engine re-derives what the journal still proves).

## 4. Merge rules, per field

| Data | Rule | Why |
|---|---|---|
| Unlock: existence | **union** — a row on any device exists everywhere | a fact never un-happens |
| Unlock: `earned_at`, `trip_id` | the **earliest** `earned_at` wins, with its `trip_id`; equal times keep the non-null `trip_id` | both devices usually computed the same values; the earliest is the true moment |
| Unlock: `metric`, `threshold` | first writer wins (equal by construction: the tier id fixes them) | immutable |
| State: `seen_threshold` | **max** | once seen anywhere, it is not new anywhere |
| State: `visibility`, `published_tier_id`, `publication_changed_at` | the **higher `publication_revision`** wins; on equal revisions **`private` wins** | a revoke is never lost to a concurrent publish |
| State: `server_revision` | max | acknowledgement only moves forward |
| New revision | `max(local revision, highest seen) + 1` | a device that missed changes still writes above them |

**Erasure and privacy deletion** (not unions):
- **No per-badge delete in V2.** The person can unpublish (hide from others) but not erase one
  fact from their private history; it would be re-derived from the journal at once anyway.
- **Erase all data** (Settings, existing flow) deletes the local tables and the CloudKit zone. The
  existing rule (`sync.md`: a deleted zone turns backup off on every device) stops another
  device from resurrecting rows by union.
- **Account deletion** clears everything published on the server (existing cascade); local
  `badge_states` go back to `private` with a higher revision, with no outbox message (the
  account is gone).
- **Purged drive:** its unlocks stay, `trip_id` becomes NULL; the Journey Detail stamp
  disappears with the drive. A drive in Recently Deleted keeps its `trip_id`.

## 5. Publishing (slice 4) — outbox, idempotent, ordered

- **Explicit only:** earning never publishes. "Share to Feed" on a stamp publishes that instance
  at a tier the person picks (its highest by default); "Hide" unpublishes. Needs "Share my
  drives"; turning the Feed off unpublishes every published instance.
- **Same transaction:** changing `badge_states` (new revision) and enqueueing its message commit
  together (`OutboxStore.enqueue(_:now:in:)`).
- **Operations:** `publishBadge(badge, instanceRef, body)` and `unpublishBadge(badge,
  instanceRef, revision)`; key `badge:<badge>:<instanceRef>`, so a newer one replaces a waiting
  older one (publish then hide while offline sends only the hide).
- **Ordering on the server:** every message carries `publication_revision`. The server applies a
  publish only when its revision is **higher** than the stored one, and a hide when it is
  **higher or equal**; so a stale publish (offline retry, another device, out-of-order delivery)
  can never show a revoked badge again. A revision another device already used makes the hide
  win, matching the local rule.
- **Results:** the existing classification; a 404 on a hide is delivered. A delivered message
  raises `server_revision`.
- **Archiving a vehicle never unpublishes** its Faithful Car (owner decision 2026-11-05); its
  public label (kind, make, model) stays as it was sent.

## 6. Vehicle archive (owner decision 2026-11-05)

Archive replaces Delete in the Garage. The vehicle row, its id, its drives and its Faithful Car
history stay; archive and restore never touch related data.

- **Schema:** `vehicles.archived_at REAL NULL` (P6, `v1_initial`), synced in the vehicle payload
  and the `.carodo` backup (`archivedAt`, optional: older payloads read as active). Last write wins
  on `updatedAt`, as every vehicle field.
- **Repository:** `vehicles()` keeps returning every non-deleted vehicle (history needs them);
  a new `activeVehicles()` (or a filter) serves selection. `archive(id)` / `restore(id)` set or
  clear `archived_at` and `needs_push`.
- **Audit of today's reads** (`vehicles()` callers):

| Caller | Gets |
|---|---|
| Garage carousel, counts, empty state, Passport Garage row ("2 cars") | active only; archived under a compact **Past Vehicles** list with Restore |
| New-drive assignment, default/last-used vehicle, Auto Mode (`AutoModeCoordinator`), car audio detection (`CarConnections`) | active only; an archived car's audio link stays stored but is ignored, and works again on restore |
| Journey Detail and Journeys labels, narration (`JourneyNarration`), Passport totals and Faithful Car | all, archived included (a past drive keeps its car) |
| Journey Detail vehicle picker | active, plus the drive's own car when archived (shown as such) |
| `BackupService` | all, with `archivedAt` |

- **Removed from the standard flow:** the editor's Delete. `delete(_:)` stays in the repository
  for a future, separate data-management workflow (its own privacy and retention rules), not
  reachable from Garage.
- Expenses and maintenance do not exist yet in the code; when they come they follow the vehicle
  row and are untouched by archive.
- Lasting decision → a short ADR in `carodo-ios/docs/decisions/` ("Vehicles are archived, not
  deleted") plus `specs/garage.md`.

## 7. Catalogue (bundled in slice 3; served in slice 4)

```json
{
  "version": 2,
  "badges": [
    {
      "id": "road_miles",
      "metric": "total_distance_m",
      "scope": "lifetime",
      "visibility": "feed",
      "tiers": [
        { "id": "km_100", "threshold": 100000 },
        { "id": "km_500", "threshold": 500000 }
      ],
      "names": { "en": "Road Miles", "vi": "…" },
      "art": "road_miles"
    }
  ]
}
```

- No `points`, no `levels`. `scope` is `lifetime | vehicle | period`; `period` (with a `period`
  field `month | year`) is reserved and unused. `retiredAt` on a definition or a tier keeps it
  for display of earned unlocks and stops new ones.
- The app accepts only metrics in its own whitelist (today `total_distance_m`,
  `vehicle_distance_m`) and never the excluded kinds of ADR 0013, so a served catalogue can tune
  thresholds and names but never widen the scope.
- Slice 3: the bundled file only (`Resources/BadgeCatalogue.json`, names in the String Catalog
  instead if the copy rules prefer); slice 4 adds `GET /v1/badges/catalogue` with ETag, newer
  version wins.

## 8. Contract changes (P6; edit `carodo-api.yaml` + `sync.md` first, backend copy follows)

- **`BadgeCatalogue`** as in section 7 (drop `levels`, tier `points`; add `scope`, tier `id`,
  `retiredAt`; metric examples only the two whitelisted).
- **Publish:** `PUT /v1/me/badges/{badgeId}/{instanceRef}` (App Attest assertion), body
  `BadgePublication`:
  ```yaml
  required: [tierId, threshold, revision, earnedLocalDate]
  tierId: string           # stable tier id
  threshold: number        # snapshot, metres
  revision: integer >= 1   # publication_revision
  earnedLocalDate: date    # the day, in the drive's zone; never a time
  vehicle: VehicleLabel    # vehicle scope only: kind, make, model
  ```
  `instanceRef` is `lifetime`, or for a vehicle an opaque, deterministic key:
  `base64url(SHA-256("carodo.badge|" + badgeId + "|" + vehicleUUID))[0..22]`. Same on every
  device and after a restore (the vehicle UUID is kept), and the server never learns a vehicle
  UUID, a trip id or a time finer than the day.
- **Hide:** `DELETE /v1/me/badges/{badgeId}/{instanceRef}?revision=` → 204; 404 when unknown.
- **Public reads:** a Feed badge item carries `{ badgeId, tierId, threshold, vehicle?, ago }`;
  never `instanceRef`, a trip id, a route or an exact time. Profile showcase (chosen badges) is a
  separate later change.
- **`BadgeEarned`** is replaced by `BadgePublication` (input) and `FeedBadge` (output); its stale
  description (long drives, new roads) goes.

**D1 (`0001_baseline.sql`, pre-release in place):**

```sql
CREATE TABLE badges (
  account_id    TEXT NOT NULL REFERENCES accounts (id) ON DELETE CASCADE,
  badge_id      TEXT NOT NULL,
  instance_ref  TEXT NOT NULL,                  -- 'lifetime' or an opaque hash; never a device id
  tier_id       TEXT NOT NULL,
  threshold     REAL NOT NULL,
  vehicle_kind  TEXT, vehicle_make TEXT, vehicle_model TEXT,
  earned_local_date TEXT NOT NULL,              -- a day, never a time
  revision      INTEGER NOT NULL,
  posted_threshold REAL,                        -- the highest tier already posted as a Feed item
  posted_at     INTEGER,                        -- server arrival of that post (Feed order, coarse in reads)
  hidden_at     INTEGER,                        -- set by a hide or account deactivation
  updated_at    INTEGER NOT NULL,
  PRIMARY KEY (account_id, badge_id, instance_ref)
) WITHOUT ROWID;
CREATE INDEX badges_on_feed ON badges (posted_at DESC) WHERE hidden_at IS NULL AND posted_at IS NOT NULL;
```

- A Feed item is posted when an instance is first published or published at a higher threshold
  than `posted_threshold`; publishing again after a hide at a tier already posted shows it on the
  profile but posts nothing new (no spam by toggling).
- `badge_definitions` keeps its shape; its JSON follows section 7. Badges never count toward the
  leaderboard (unchanged).

## 9. Reconciliation

| Item | Today | Change |
|---|---|---|
| ADR 0013 (pre-release: changed in place, status line notes the revision) | "one row per tier with badge id, vehicle id, tier" | stable tier ids, threshold snapshot, two tables, merge rules, archived vehicles keep badges, instance refs |
| New ADR 0014 | — | vehicles are archived, not deleted |
| `data-model.md` | `earned_badges` | `badge_unlocks`, `badge_states`, `vehicles.archived_at` |
| `sync.md` | earned badges "re-derivable", not synced | two record types, merge rules, outbox operations |
| `carodo-api.yaml` 0.23 → 0.24 | points/levels, PUT by badge only, no hide | section 8 |
| `carodo-app` `0001_baseline.sql` | PK (account, badge), integer tier | section 8; `lifecycle.ts` hide on deactivation unchanged |
| `specs/feed.md` | Long Hauler example, long drives / new roads | Road Miles / Faithful Car only |
| `specs/garage.md` | "Delete is at the bottom of the edit form" | Archive, Past Vehicles, Restore |

## Questions left for the owner

1. **Seen on all devices** (max merge): a stamp seen on the iPhone is not "new" on the iPad.
   Assumed yes.
2. **Republish after hide posts nothing new** at an already-posted tier. Assumed yes.
3. **`earned_at` = the crossing drive's end**, so a journal imported or restored later shows the
   real moment, not the import day. Assumed yes.
