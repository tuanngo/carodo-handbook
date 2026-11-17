# Backend Feed V1 — align carodo-app with contract 0.28.1-draft

Status: **built 2026-11-15 (local, tested; uncommitted until the first deploy).** S0–S6 done in
carodo-app; contract descriptions moved to 0.28.2-draft (no shape changed). `task check`: api 173
tests, web 20 (25 after the landing, 2026-11-16), lint and typecheck clean. Left open: TD-47, TD-48, KL-6, KL-7, PV-28
(`technical-debt.md`). Supersedes the "Next, in order" list of [`backend.md`](backend.md).

**Owner decisions (2026-11-15):** delete endpoints outside V1 and every table no V1 code uses, keep
the columns of kept tables; constraints after linkto (amended the same day): foreign keys with
cascade from `accounts` for what an account owns, none on auxiliary tables, `CHECK` only on a
system job's status, other fixed sets as lowercase text; the profanity list as a seeded table like linkto's `slug_policies`; D2 "now" by
`coarse-time.ts` (contract follows); D3 a renamed name held 90 days; D4 order by hour then random id;
D5 schema as listed; docs synced after. OSM ([`geodata-osm.md`](geodata-osm.md)) waits until the
Feed is integrated.

**As built, beyond the plan below:** tables without code were dropped too (shares, backups,
backup_keys, web_sessions, reports, blocks, outbox_events, badge_definitions; they return with their
slices); `username_policies` + `apps/api/seeds/username-policies.sql` (applied by `task db:reset`,
the tests and every deploy, `task db:policies:<env>`); a local day holds at most 50 visible drives
(422 `out_of_range`, so a page reads its items' drives whole); `Vary: Authorization` on the Feed.
Bug found on the way: an unpublish at the drive's own revision did nothing (`>` instead of `>=`),
so hiding a drive without a local edit would not have hidden it; covered by
`publish.test.ts` ("hides at the drive's own revision"). Measured (C14, `cost.test.ts`, 500
accounts, 10,000 drives): a page 42 rows for its items + 80 drives + 52 counts + 48 for a member's
reactions; stats 82 + 165 for 82 drives in the window; a publish 6–8 rows read, 7–10 written.

**Goal:** the iOS app's `LocalFeedServer` (the device-only mock of the Feed backend) can be replaced
by the real `carodo-api` with no screen changing: every operation the app calls for community
access today answers as `carodo-ios/docs/api/carodo-api.yaml` 0.28.1-draft says.

**Owner decisions already made (2026-11-15):** code and schema outside Feed V1 are **deleted**,
not parked (pre-release, the schema is edited in place, history keeps the old code). Calls to
outside services (OSM first) go through our server; that track is
[`geodata-osm.md`](geodata-osm.md), not this plan.

## 1. Audit — what the code does today

Files read: `apps/api/migrations/0001_baseline.sql`; `src/routes/{accounts,auth,drives,feed,live}.ts`;
`src/services/drives/{input,publish}.ts`; `src/services/feed/{items,read}.ts`;
`src/services/accounts/{claim,usernames}.ts`; `src/services/shared/coarse-time.ts`; the file list of
`src/` and `test/`. On the iOS side: `docs/api/carodo-api.yaml` (0.28.1), `docs/sync.md` ("Local mock",
"Outbox"), ADR 0007, `Core/Networking/LocalFeedServer.swift`.

The backend was built against contract ~0.25. Against 0.28.1:

| Area | Backend today (file) | Contract 0.28.1 |
|---|---|---|
| Claim | `POST /v1/accounts` needs `feedOptIn`, `liveOptIn`, `displayName`, `regionCode` (`services/accounts/claim.ts`) | `username` + `deviceCheckToken` + optional `sharing`; sharing off by default |
| Username | pattern `[a-z0-9_.]{3,20}`, reserved list (`usernames.ts`); no profanity list, no edge rules | also no leading/trailing `.`/`_`, no `..`/`__`; reasons `reserved`, `profane`; suggestions |
| Profile | none | `GET`/`PUT /v1/me/profile` (`{id, username}`), 3 changes in 30 days (`username_change_limit`) |
| Availability | none | `GET /v1/usernames/{username}` (guest or member, rate-limited) |
| Sharing | `feed_opt_in`, `live_opt_in` columns, no endpoint | `GET`/`PUT /v1/me/sharing`: `sharing`, `displayAs`, `showVehicle`; off removes every drive, on lifts those marks |
| Publish | `PUT`/`DELETE /v1/drives/{tripId}` (`routes/drives.ts`); input with `tags`, `area`, `maxSpeedMps`, `ranked`, shape 2–24 integer points 0–1000 (`drives/input.ts`); 20 drives/hour cap | `/v1/feed/drives/{tripId}`; `DriveInput` with `endedAt`, `localStartHour`, `partOfDay`, `weather`, `vehicle` (make/model only), shape `{version: 1, points}` 8–64 points in 0–1; geographic key/value → 422 `geo_payload_rejected`; `sharing_off` 403 |
| Feed item | one person's drives in one **hour** (`drove_at`), id = HMAC(account, hour), carries `user` with account id (`feed/items.ts`) | one person's drives on one **local day**, random id stable for the item's life, no author id, `isAuthor`, `tripIds` (own only), `displayName` or null, `vehicle` or null, `reactions`, `myReaction` |
| Feed page | Discover/Following tabs, scope/region, `live`, `stats`, `topDrivers` (`feed/read.ts`) | one worldwide list over 72 h, `{items, nextCursor, hasMore}`; guest page shared (`public`, ~2 min), member page `private` with its own ETag |
| Stats | `drive_stats_hourly` table, never filled | `GET /v1/feed/stats`: drivers, distance, duration, busiest local hour over 72 h, only from 10 distinct drivers, else `warmup` |
| Reactions | none | `PUT`/`DELETE /v1/feed/items/{itemId}/reaction`, five fixed values, members only |
| Off-contract | `/v1/live` (`routes/live.ts`, `services/live/`), Following, regions (`accounts/region.ts`), `POST /v1/account/secret` (removed in 0.28.0), tables `live_status`, `follows`, `leaderboard_entries`, `badges`, `apple_links`, `drive_stats_hourly` | none of these |

Kept as they are: App Attest, guest token, session/refresh, `DELETE /v1/account` and the erase job,
jobs and pruning, edge cache (`lib/cache/edge-cache.ts`, ADR 0008), sealed cursors
(`feed/cursor.ts`), `coarse-time.ts`. Tables kept for later slices already in the contract:
`badge_definitions`, `shares`, `backups`, `backup_keys`, `web_sessions`, `reports`, `blocks`,
`outbox_events`, `pending_ops`, `job_*`.

Assumed, not checked: that `GET /v1/badges/catalogue` is not needed for V1 (the app ships a copy,
ADR 0013); that the 2026-11-07 audit findings APP-01..06 are fixed (the 2026-11-12 handbook audit
still lists backend items H03, M06–M09, L09–L12 as open; `backend.md` says the six are open). S0
re-checks both before deleting anything.

## 2. Proposal — slices

Each slice ends with `task check` green, its tests added, rows read/written measured (C14), and the
docs it touches updated in the same change.

**S0 — Delete what V1 does not have.** Routes `live.ts`, `POST /v1/account/secret`; services
`live/`, `accounts/region.ts`, Following in `feed/read.ts`, plausibility `ranked` and `tags`; their
tests. Schema: drop `live_status`, `follows`, `leaderboard_entries`, `badges`, `apple_links`,
`drive_stats_hourly`; from `accounts` drop `display_name`, `avatar_key`, `live_opt_in`,
`region_code`; from `drives` drop `vehicle_kind`, `ranked`, `tags`, `region_code`, `area_*`, and the
indexes they served. Prune and erase jobs lose their live/leaderboard parts. Reserved names lose
`leaderboard` and `live` only if the owner wants (recommend keeping them reserved).

**S1 — Account, username, profile, sharing.**
- `POST /v1/accounts` to the contract body; `sharing` optional, absent = off.
- One username rule in `usernames.ts`: the contract pattern, reserved list, a profanity list (EN +
  VI, the owner reviews it), reasons `invalid | taken | reserved | profane`, up to 3 suggestions.
- `GET /v1/usernames/{username}` (`RL_READ` per key; a held name answers `taken`).
- `GET`/`PUT /v1/me/profile`: rename in one batch with the change count; a new table
  `username_changes (account_id, changed_at)` read through `(account_id, changed_at)`.
- `GET`/`PUT /v1/me/sharing`: columns `sharing`, `display_as`, `show_vehicle` on `accounts`. Off:
  every visible drive gets `stopped_at`; on: `stopped_at` cleared, so the app's republish at the
  same revision applies. A drive the person hid keeps its own tombstone through both.

**S2 — Publish.** Move to `/v1/feed/drives/{tripId}`; `parseDriveInput` to the 0.28.1 `DriveInput`;
the geographic refusal (same key list as `LocalFeedServer.geographicKey`, at any depth; a shape
point outside 0–1) before any other check; `sharing_off` 403; `drives` gains `ended_at`,
`local_start_hour`, `weather`, `item_id`. Revision and tombstone rules unchanged. A publish also
creates or updates its item (S3) in the same `db.batch()`.

**S3 — Items and the Feed read.**
- New table `feed_items (id random UUID, account_id, local_date, sort_hour, last_ended_at,
  created_at)`, `UNIQUE (account_id, local_date)`. `sort_hour = publicHour(latest visible
  ended_at)`, NULL when the item has no visible drive; the item keeps its id (and its reactions)
  when a drive joins or leaves it.
- Page: keyset on `feed_items_on_feed (sort_hour DESC, id DESC) WHERE sort_hour IS NOT NULL`, within
  72 h; then the page's drives in one query by `item_id IN json_each(?)` and reaction counts the
  same way; one round trip with `db.batch()` where the statements allow it.
- Guest page: computed once per TTL bucket and shared (ADR 0008, `Cache-Control: public`, at most
  ~2 min old). The cached form keeps author ids for the member overlay and is never sent as is.
- Member page: the shared page plus the reader's own overlay (`isAuthor`, `tripIds`,
  `myReaction`), `Cache-Control: private`, ETag per reader.
- `ago` from `coarse-time.ts` (see decision D2).

**S4 — Community stats.** `GET /v1/feed/stats` computed from `drives` over 72 h through a partial
index on `ended_at`, cached for every reader (C9) with a 5-minute bucket; `visible` only from 10
distinct drivers, else `warmup` in steps of 0.1. Rows read = drives in the window; an hourly rollup
only once the measured rows say so.

**S5 — Reactions.** Table `reactions (item_id, account_id, reaction, created_at)`, primary key
`(item_id, account_id)`, index on `account_id` (erase). `PUT` replaces, `DELETE` is idempotent, 404
when the item is gone (no visible drive or older than 72 h), `RL_WRITE` per key, assertion required.

**S6 — Record.** `docs/architecture.md`, `docs/storage.md`, `docs/cost.md` (measured rows),
`docs/metrics.md`, ADR 0008 (what is cached now), `apps/api/README.md`; `backend.md` status and
next list; `technical-debt.md` for what is left.

## 3. Non-goals

Report, block-author, `/v1/me/blocks` (deferred until App Review asks; tables stay, the Feed does
not read `blocks` until then). Shares, backups, web pairing, badges catalogue. Staging deploy. Any
iOS change: `BackendService` replacing `LocalFeedTransport` / `LocalCommunityRepository` is the iOS
track (`ios-backend-integration.md`). OSM (`geodata-osm.md`).

## 4. Acceptance criteria

- Every operation listed in contract 0.28.1's description under "What the app calls for community
  access now" answers as the contract says, with a workers test per status code it lists.
- No route, table, column or test for Live, Following, region, leaderboard, Feed badges, Sign in
  with Apple or `/v1/account/secret` remains (`grep` proof in the report).
- The full-scan guard passes over every new query; rows read for a Feed page (guest and member),
  stats and a publish are measured at 500 accounts and 10,000 drives, as the current Feed was.
- A test per invariant at risk: no author id or exact time in any response (P9); a geographic body
  refused whole (P5); a late older revision changes nothing; sharing off then on republishes, a hid
  drive stays hidden; an item keeps its id and reactions when a drive joins it.
- `task check` green after the last change.

## 5. Decisions for the owner

- **D1 Profanity list:** a short EN + VI list in code, reviewed by you. Recommend: yes, ~100 words,
  matched on the name with `.`/`_`/digits removed.
- **D2 "now" rule:** the contract says "now" = started this hour, or published in the last hour and
  started within three; `LocalFeedServer` says "now" = ended within the hour; `coarse-time.ts` says
  started this hour or ended within the hour. Recommend: the backend follows the contract, and the
  mock is aligned on the iOS side (contract wins).
- **D3 A renamed username:** hold the old name 90 days like a deleted one (impersonation)?
  Recommend: yes; the contract and the mock do not say, so the contract description gains one line
  (your approval).
- **D4 Feed order inside an hour:** items ordered by `sort_hour`, then their random id, so no
  finer time leaks through order. Recommend: yes.
- **D5 Schema changes** (P6): the tables and columns in S0–S5. Approve as listed or ask for changes.
