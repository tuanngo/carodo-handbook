# Feed private by default — Part 2: backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

Status: **done 2026-11-19**: carodo-app 7367a39, 2d674e1 (code), 0f643d9, 6b65a99 (docs); carodo-ios 22e3d9b, fc6579c, 61d8eb8. Names approved by the owner the same day: API
`endedAt`, columns `drives.ended_at` and `feed_items.last_ended_at` (no name tells how a time is
made coarse); no `started_at` (Live gets its own ADR).

**Goal:** carodo-app implements contract 0.29.0-draft: quarter-hour drive times only, others see a
drive from its release quarter, its author at once, a 7-day Feed that deletes itself, and Stop
sharing / account deletion that delete.

**Architecture:** `drives` keeps only `ended_at` (the device's end, already on a quarter) and no
start; `feed_items.last_ended_at` is the `ended_at` of an item's newest visible drive, set at
publish. Others' pages read released items through `feed_items_on_feed` and merge in the few items
touched in the last quarter (their released key computed from their drives), so a publish never
moves or hides an item between quarter hours, with no new cron. The member overlay adds the reader's
own unreleased drives. The hourly `prune.expired` deletes what left the window.

**Tech Stack:** TypeScript, Hono, Cloudflare Workers, D1, Vitest in workerd
(`@cloudflare/vitest-plugin`), Biome.

**Spec:** [`feed-private-by-default.md`](feed-private-by-default.md); binding texts committed in
Part 1: carodo-ios `d0186ad` (ADR 0007, contract 0.29.0-draft, `sync.md`), carodo-app `a276e84`
(P9, ADR 0007).

## Global Constraints

- Owner, 2026-11-19 (after Part 1): **server audit columns stay exact** (`published_at`,
  `updated_at`, `unpublished_at` on `drives`; `created_at` on `feed_items`): they are when the server
  received a write, never sent to anyone. **Item ids stay random** (`crypto.randomUUID()`), never
  UUIDv7. **Columns marked "unused in Feed V1" stay** in the schema.
- No exact device time of a drive at rest: `started_at` and `drove_at` go; `ended_at` and
  `feed_items.last_ended_at` stay and hold only quarter times. `stopped_at` goes (Stop sharing
  deletes). Names never say how a time is coarsened (owner, 2026-11-19).
- Quarter = 15 min = `QUARTER_MS`; window = 168 h; release = `ended_at + 15 min`. Every
  boundary a reader can observe (release, window, age label, cache bucket) falls on a quarter of
  server time: compute from `floorTo(now, QUARTER_MS)`, never from `now` itself.
- Public order: `(key quarter DESC, item id DESC)`; the id is random. Never an audit column, never
  a UUIDv7.
- Pre-release: edit `apps/api/migrations/0001_baseline.sql` in place; `task db:reset`.
- Cost rules: every query through an index (the `workers` setup fails a full scan), no `await` in a
  loop, one `db.batch()` per write path; state rows read in the report (C14).
- Other sessions' uncommitted files in carodo-app: `apps/api/wrangler.jsonc`,
  `apps/web/src/pages/privacy-content.ts`, `docs/architecture.md`, `docs/operations/deploy.md`,
  `package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`. Do not touch them except
  `docs/architecture.md` (Task 8: add to it, commit only own hunks via `git apply --cached`).
  `task typecheck` fails until that session runs `task types`; the gate here is `task lint` +
  `pnpm --dir apps/api run test` (state this in the report).
- Commits: lowercase conventional, no AI attribution (P8); one commit per task; on `main` as the
  owner does; never push.

## Review Focus

1. **An item moves or vanishes for others at a publish moment** (a second drive of the day
   published at 10:37 while the 09:00 drive shows): Task 4 tests the guest page before and after
   that publish within one quarter is identical.
2. **The author's view leaks to others through the shared cache:** the overlay must never enter
   the cached page; Task 4 tests a guest page after the author's own read in the same quarter.
3. **A late PUT resurrects a hidden drive after Stop sharing and Start sharing:** tombstones
   survive Stop sharing; Task 3 tests hide → stop → start → late lower-revision PUT → still hidden.
4. **Boundary off by one at release and window** (`<=` vs `<`): Task 2 unit tests and Task 4
   workers tests freeze `now` at `release − 1 ms` / `release` and window edge ± 1 ms.
5. **Prune reads a whole table or leaves orphan items/reactions:** Task 6 tests that a drive 169 h
   old, its item and reactions are gone, a 167 h one stays, and the setup's full-scan check passes.

---

### Task 0: contract names

**Files:**
- Modify: `carodo-ios/docs/api/carodo-api.yaml`, `carodo-ios/docs/sync.md` (own hunks),
  `carodo-ios/docs/decisions/0007-privacy-first-feed.md`, `carodo-app/docs/decisions/0007-event-time-comes-from-the-device-late-is-normal.md`,
  the spec.

- [ ] **Step 1:** rename `endedQuarter` to `endedAt` everywhere; the field's description says
  "the end of the drive, on a quarter hour (:00, :15, :30, :45 UTC, zero seconds)"; texts keep the
  rule, column names follow the approved names.
- [ ] **Step 2:** YAML parses (`ruby -ryaml -e 'YAML.load_file(...)'`); `grep -rn endedQuarter` → none.
  Commit carodo-ios `docs(api): name the drive end endedAt` and carodo-app
  `docs: name the drive end ended_at`.

### Task 1: schema

**Files:**
- Modify: `apps/api/migrations/0001_baseline.sql` (`drives`, `feed_items`, their indexes)
- Modify: `apps/api/test/workers/db/schema.test.ts`, `apps/api/test/support/feed.ts`,
  `apps/api/test/workers/feed/cost.test.ts` (seeding only)

**Interfaces:**
- Produces: `drives.ended_at INTEGER NOT NULL`; `feed_items.last_ended_at INTEGER` (NULL: no
  visible drive); indexes `drives_on_ended_at (ended_at)` (prune, stats),
  `drives_on_item_id`, `drives_on_account_id (account_id, local_date)` (kept),
  `feed_items_on_feed (last_ended_at DESC, id DESC) WHERE last_ended_at IS NOT NULL`,
  `feed_items_on_local_date (local_date)` (prune). Dropped: columns `started_at`, `drove_at`,
  `stopped_at`, `feed_items.sort_hour`; index `drives_on_unpublished_at`. `drives.ended_at` and
  `feed_items.last_ended_at` keep their names, now quarter times.
- Test helper: `seedDay(accountId, localDate, endedAts: number[]): Promise<string>` (item's
  `last_ended_at` = max).

- [ ] **Step 1:** In `schema.test.ts` add `it("keeps no exact time of a drive")`: `PRAGMA table_info(drives)`
  names include `ended_at`, `published_at`, `updated_at`, `unpublished_at`, `hidden_at` and none
  of `started_at`, `drove_at`, `stopped_at`; `feed_items` has `last_ended_at`, not `sort_hour`;
  index `feed_items_on_feed` is on `last_ended_at`.
- [ ] **Step 2:** `pnpm --dir apps/api exec vitest run test/workers/db/schema.test.ts` → FAIL on
  `started_at` present.
- [ ] **Step 3:** Edit the baseline: the columns and indexes above; comments say `ended_at` is
  the device's end floored to 15 min (the only time of a drive), audit columns are server time,
  never in a response (owner, 2026-11-19); `hidden_at` is moderation only now.
- [ ] **Step 4:** Update `seedDay` and the cost test's bulk insert to the new columns (they will be
  exercised in Tasks 4–6). Run the schema test → PASS. `task db:reset` → succeeds.
- [ ] **Step 5:** No commit yet: the suite stays red until Task 5 (the code still reads the old
  columns). Tasks 1–5 land as one commit at the end of Task 5, so every commit on `main` passes.

### Task 2: coarse time

**Files:**
- Modify: `apps/api/src/services/shared/coarse-time.ts`, `apps/api/src/lib/time/units.ts`
- Test: `apps/api/test/unit/shared/coarse-time.test.ts`

**Interfaces:**
- Produces in `lib/time/units.ts`: `QUARTER_MS = 15 * MINUTE_MS`.
- Produces in `coarse-time.ts` (replaces `publicHour` and the old `agoBucket`):
  - `isQuarter(at: number): boolean`
  - `interface FeedClock { quarter: number; releasedUpTo: number; windowStart: number }` and
    `feedClock(now: number): FeedClock` — `quarter = floorTo(now, QUARTER_MS)`,
    `releasedUpTo = quarter − QUARTER_MS` (a drive is released iff `ended_at <= releasedUpTo`),
    `windowStart = quarter − 168 h` (in the window iff `ended_at >= windowStart`).
  - `FEED_WINDOW_MS = 168 * HOUR_MS`.
  - `agoLabel(endedAt: number, now: number): string` — from the release
    (`endedAt + QUARTER_MS`): before it or under 1 h `"now"`, then `"1h"`–`"23h"`, `"1d"`–`"6d"`
    (contract `Ago`, pattern `^(now|[1-9]h|1[0-9]h|2[0-3]h|[1-6]d)$`; clamp at `"6d"`).

- [ ] **Step 1: tests** — `feedClock` at `10:44:59.999` → `releasedUpTo` 10:15 (a drive ended 10:37,
  quarter 10:30, not released); at `10:45:00.000` → `releasedUpTo` 10:30 (released). `windowStart`
  at 10:45 = 10:45 − 168 h. `agoLabel(q10:30, 10:45)` = "now", at `11:44:59.999` "now", at `11:45` "1h",
  at `q + 15 min + 24 h` "1d", at 7 days "6d", before release "now". Every label matches the
  contract pattern. `isQuarter` true at :00/:15/:30/:45 with 0 s and 0 ms, false at :37 and :45:00.001.
- [ ] **Step 2:** run `pnpm --dir apps/api exec vitest run test/unit/shared/coarse-time.test.ts` → FAIL.
- [ ] **Step 3:** implement; header comment: the quarter is the finest time anyone else may see or
  observe (P9), audit columns are server time and never leave.
- [ ] **Step 4:** run → PASS (unit project only; no commit, see Task 1 Step 5).

### Task 3: publishing (input, publish, unpublish, sharing, deletion)

**Files:**
- Modify: `apps/api/src/services/drives/input.ts`, `apps/api/src/services/drives/publish.ts`,
  `apps/api/src/services/feed/items.ts` (refresh only), `apps/api/src/services/accounts/sharing.ts`,
  `apps/api/src/services/accounts/lifecycle.ts`
- Test: `apps/api/test/unit/drives/input.test.ts`, `apps/api/test/workers/drives/publish.test.ts`,
  `apps/api/test/workers/accounts/lifecycle.test.ts`, `apps/api/test/support/drives.ts`

**Interfaces:**
- Consumes: `isQuarter`, `feedClock`, `QUARTER_MS` (Task 2).
- Produces: `DriveFields` with `endedAt: number` (quarter ms; no `startedAt`, `droveAt`);
  `checkTime(endedAt: number, localDate: string, now: number): Result<null>`;
  `refreshItems` sets `last_ended_at = max(ended_at)` of visible drives
  (`VISIBLE = "d.hidden_at IS NULL AND d.unpublished_at IS NULL"`).
- Test helper `driveInput({ endedAgoMs, durationMin, revision, distanceM }, overrides)` sends
  contract 0.29.0 bodies: `endedAt` floored, durations multiples of 60, distance multiple of 100.

- [ ] **Step 1: unit tests (input)** — accepts a 0.29.0 body and returns `endedAt` as ms;
  refuses 400 `validation`: `endedAt` at :37, at :45:01, a `startedAt` key is ignored (not
  required), `elapsedDurationS` 61, `movingDurationS` 30, `distanceM` 12_050; refuses 422
  `start_time_invalid`: `endedAt` 15 min + 1 quarter ahead (ahead by exactly 15 min passes);
  the UTC date of `endedAt` minus `localDate` of −3 and +3 days (−2 and +2 pass); 422
  `out_of_range` for a rounded value outside the range (`distanceM` 0 and 2_000_100,
  `elapsedDurationS` 0 and 86_460; 60 and 86_400 pass). Rounding is checked before ranges. The
  geographic check still runs first.
- [ ] **Step 2: workers tests (publish)** — rewrite the file's cases to the new rules:
  - publishes into its day's item; `ended_at` stored as sent; `published_at` and `updated_at`
    are server time (≈ `Date.now()`), exact;
  - a drive with `endedAt` older than `windowStart` answers 204 and writes no row (no
    `drives`, no `feed_items` row);
  - no `feed_items` row is created when the publish is refused (sharing off, another account's trip,
    day full);
  - revision rules unchanged; `published_at` kept on a higher revision;
  - **Stop sharing** deletes the account's published drives and all its items (reactions with
    them); a hidden drive's tombstone survives; hide → stop → start → PUT at a lower or equal
    revision → 204 and still not visible (Review Focus 3); a republish after Start sharing is a new
    insert;
  - **unpublish** clears the summary (zeros, `vehicle_*`, `shape`, `weather` NULL, `item_id` NULL),
    keeps `trip_id`, `revision`, `ended_at`; without a row it inserts a tombstone with
    `ended_at = feedClock(now).quarter`; the item is refreshed;
  - replace "keeps a tombstone 30 days, then prunes it" (moves to Task 6).
  - `lifecycle.test.ts`: after `DELETE /v1/account`, no `drives` or `feed_items` row of the
    account exists (was `hidden_at`).
- [ ] **Step 3:** run `pnpm --dir apps/api exec vitest run test/unit/drives test/workers/drives test/workers/accounts/lifecycle.test.ts` → FAIL.
- [ ] **Step 4: implement**
  - `input.ts`: parse `endedAt` (instant, `isQuarter`), rounding checks (400), `checkTime` as
    above (drop the year rule: the window rule replaces it), ranges unchanged except
    `elapsedDurationS` 60–86_400.
  - `publish.ts`: out of window → `ok(null)` before any write; item insert becomes
    `INSERT … SELECT … WHERE (SELECT feed_opt_in FROM accounts WHERE id = ?2 AND deleted_at IS NULL) = 1 ON CONFLICT DO NOTHING`;
    upsert drops the `stopped_at` branch; columns follow Task 1. Unpublish as Step 2.
  - `sharing.ts`: sharing off → `DELETE FROM drives WHERE account_id = ? AND unpublished_at IS NULL`
    then `DELETE FROM feed_items WHERE account_id = ?` in the same batch (both through
    `drives_on_account_id` / the `(account_id, local_date)` unique index).
  - `lifecycle.ts`: replace the `hidden_at` update and `refreshItemsOf` with
    `DELETE FROM drives WHERE account_id = ?` and `DELETE FROM feed_items WHERE account_id = ?`.
  - `items.ts`: `refreshItems` / `refreshAfterPublish` / `refreshItemOfTrip` on `last_ended_at`;
    `refreshItemsOf` is no longer needed (delete it if unused).
- [ ] **Step 5:** run → PASS (no commit yet).

### Task 4: reading the Feed (release, merge, author overlay, cache)

**Files:**
- Modify: `apps/api/src/services/feed/read.ts`, `apps/api/src/services/feed/items.ts`,
  `apps/api/src/services/feed/cursor.ts`, `apps/api/src/routes/feed.ts`
- Test: `apps/api/test/unit/feed/items.test.ts`, `apps/api/test/unit/feed/cursor.test.ts`,
  `apps/api/test/workers/feed/feed.test.ts`

**Interfaces:**
- Consumes: `feedClock`, `agoLabel` (Task 2); schema (Task 1).
- Produces:
  - `FeedPosition { key: number; itemId: string }` (was `sortHour`); `FIRST_POSITION.key = MAX_SAFE_INTEGER`.
  - `sharedPage(env, position, clock: FeedClock, now: number): Promise<SharedPage>`;
    `readerPage(env, shared, readerId, clock, now, first: boolean): Promise<FeedPage>`.
  - `DriveRow` loses `drove_at` (`ended_at` is now a quarter); `feedItem(row, drives, reactions, now)`
    uses `agoLabel(drive.ended_at, now)`; the item's `ago` is its newest drive in `drives`.
- Algorithm of `sharedPage` (the one part the tests alone do not pin):
  1. `RELEASED_SQL`: items with `last_ended_at IS NOT NULL AND last_ended_at BETWEEN windowStart AND releasedUpTo AND (last_ended_at, id) < (key, itemId)`, joined to accounts as today, `ORDER BY last_ended_at DESC, id DESC LIMIT 21` (`feed_items_on_feed`).
  2. `RECENT_SQL`: items with `last_ended_at > releasedUpTo` (joined to accounts as in 1) (same index, a range: only items whose
     newest drive is not released yet, i.e. touched this or the last quarter), all of them.
  3. One batch: their drives (`drives_on_item_id`, visible, `ended_at BETWEEN windowStart AND releasedUpTo`)
     and reaction counts, for the union of ids.
  4. A recent item's key = max `ended_at` of its released drives; none → dropped. Keep recent
     items whose `(key, id) < position`; merge with (1) by `(key DESC, id DESC)`; take 20; `hasMore`
     when more than 20 remained; cursor = last taken `(key, id)`.
  5. Every drive in an item is released (step 3's filter), so an item shows only released drives.
- `readerPage`: for a member, `OWN_PENDING_SQL` — the reader's visible drives with
  `ended_at > releasedUpTo` and `local_date >= ` the window's first day (`drives_on_account_id`),
  with their items. Merge each into the reader's item on the page if present; on the first page,
  the reader's items holding a pending drive and absent from the page go first (the app pins your
  latest row); on later pages, those item ids are left out. Pending drives' `ago` is "now".
  Reactions on them: none (the item is not on the Feed for others).
- Route: the cache key adds `q=<clock.quarter>`; `compute` gets the clock; the overlay never enters
  the cached body.
- `reactions.ts`: `react` requires an item with a released drive in the window:
  `EXISTS (SELECT 1 FROM drives d WHERE d.item_id = ?1 AND VISIBLE AND d.ended_at BETWEEN ?5 AND ?6)`.

- [ ] **Step 1: unit tests** — `cursor.test.ts` round-trips `{ key, itemId }`; `items.test.ts`:
  ages from `ended_at` ("now" until release + 1 h), no exact time in the JSON (every number
  that is a time is absent: assert keys of each drive are exactly `durationS, distanceM, ago,
  partOfDay` plus optional `weather`, `shape`).
- [ ] **Step 2: workers tests** (`feed.test.ts`; a boundary is tested by calling `sharedPage` /
  `readerPage` with an explicit clock and `now`, or by `vi.setSystemTime` if it reaches the route
  in workerd: builder's call, ledgered):
  - a drive ended 10:37 (quarter 10:30) is absent from a guest's page at 10:44:59.999 and present
    at 10:45 with ago "now"; present on its author's first page at 10:40 with ago "now" and
    `isAuthor`;
  - **Review Focus 1:** author has a released 09:00 drive; guest page at 10:40 before and after the
    author publishes a 10:37 drive is identical (same items, order, drives);
  - **Review Focus 2:** after the author reads at 10:40, a guest read at 10:40 does not contain the
    10:37 drive;
  - window: a drive with `ended_at` = windowStart is shown, one quarter older is not;
  - order: newest released quarter first; inside one quarter, by item id; pages by key without
    repeating an item (rewrite the existing paging test);
  - reacting to an item with only an unreleased drive answers 404;
  - keep: choices at read time, own item marking, ETag, Vary, 401, racing reads.
- [ ] **Step 3:** run `pnpm --dir apps/api exec vitest run test/unit/feed test/workers/feed/feed.test.ts` → FAIL.
- [ ] **Step 4:** implement as specified.
- [ ] **Step 5:** run → PASS (and no full scan from the setup check). No commit yet.

### Task 5: community numbers

**Files:**
- Modify: `apps/api/src/services/feed/stats.ts`, `apps/api/src/routes/feed.ts` (cache key `q`)
- Test: `apps/api/test/workers/feed/feed.test.ts` (stats block)

**Interfaces:**
- Produces: `communityStats(env, clock: FeedClock): Promise<CommunityStats>` with `windowHours: 168`;
  `TOTALS_SQL` / `BUSIEST_SQL` bound `(windowStart, releasedUpTo)` over `drives_on_ended_at`
  with `VISIBLE`.

- [ ] **Step 1:** tests: `windowHours` 168; an unreleased drive is not counted (10 drivers of whom
  one is unreleased → `visible` false, warmup 0.9); a drive one quarter older than the window is not
  counted. Run → FAIL.
- [ ] **Step 2:** implement; run → PASS.
- [ ] **Step 3:** `task lint` and `pnpm --dir apps/api run test` → all pass. Commit Tasks 1–5
  together: `feat(feed): quarter-hour drive times, release at the next quarter, 7-day window`.

### Task 6: the Feed deletes itself

**Files:**
- Modify: `apps/api/src/services/jobs/prune.ts`
- Test: `apps/api/test/workers/jobs/scheduled.test.ts`, `apps/api/test/workers/drives/publish.test.ts` (moved tombstone test)

**Interfaces:**
- Produces: prune targets `drives` by `ended_at` with `keepMs = FEED_WINDOW_MS + HOUR_MS`
  (drives and tombstones), then `feed_items` by `local_date` older than the date of
  `now − FEED_WINDOW_MS − 3 days` (a local day is within two days of its drives' ends); items
  cascade their reactions. `PruneTarget` gains `kind: "instant" | "date"` (or a separate statement:
  builder's call) since `local_date` is TEXT.

- [ ] **Step 1:** tests: a drive (and a tombstone) with `ended_at` 169 h ago is deleted, 167 h
  stays; an item whose `local_date` is 11 days ago is deleted with its reactions, one 8 days ago
  stays; prune reads no full table (setup check). Run → FAIL.
- [ ] **Step 2:** implement in the same single `db.batch()`; drives before items. Run → PASS.
  Commit `feat(jobs): delete feed drives and items once they leave the 7-day window`.

### Task 7: cost at size

**Files:**
- Modify: `apps/api/test/workers/feed/cost.test.ts`

- [ ] **Step 1:** rewrite the three cases on the new queries: a page reads ≤ `3 × 21 + 2` rows for
  released items plus the recent items' rows; drives ≤ `ITEMS × (2 × MAX_DRIVES_PER_DAY + 1)`;
  stats read ≤ `2 × window drives + 2`; publish writes a few rows; prune deletes in one batch.
  Seed a year of drives at quarter times.
- [ ] **Step 2:** `pnpm --dir apps/api exec vitest run test/workers/feed/cost.test.ts` → PASS; copy
  the logged rows-read figures into the report (C14). Commit `test(feed): rows read at size on quarter-hour drives`.

### Task 8: texts follow the owner's audit decision, and the carried minors

**Files:**
- Modify: `carodo-app/AGENTS.md` (P9), `carodo-app/docs/decisions/0007-event-time-comes-from-the-device-late-is-normal.md`,
  `carodo-app/docs/storage.md:17-18`, `carodo-app/docs/architecture.md:18,111` (own hunks only),
  `carodo-app/docs/cost.md:39,41`, `carodo-ios/docs/decisions/0007-privacy-first-feed.md` ("A Feed
  row": 100 m), `carodo-ios/docs/api/carodo-api.yaml` (`Ago`: "now" for the author's drive before
  release; `FeedItem.ago` from the newest drive the reader sees), the spec's C6.

- [ ] **Step 1:** P9 title "Coarse drive times at rest"; body: the backend never receives or keeps
  an exact time of a drive; it keeps exact server times of what it received (audit columns such as
  `published_at`, `updated_at`, `unpublished_at`) and of its protocol, never in a response, a log
  tied to an account, or a public order. ADR 0007 (carodo-app): drop "not kept on a drive" and the
  `unpublished_at` quarter exception; say audit columns are exact server time, never public, never
  an order (owner, 2026-11-19). Spec C6 says the same.
- [ ] **Step 2:** storage/architecture/cost texts describe `ended_at`, `last_ended_at`, the
  7-day deletion; contract lines as listed; YAML parses (`ruby -ryaml …` → ok).
- [ ] **Step 3:** `task lint` and `pnpm --dir apps/api run test` → all pass. Commit carodo-app
  `docs: feed times as built (quarter hours, exact audit columns)` and carodo-ios
  `docs(feed): ages before release and distance rounding`.

### Task 9: visibility fixed at receipt, released by a quarter-hour job (after the final review)

Owner, 2026-11-19, after the final review found that a drive published after its quarter appeared
at the moment of publishing (its end readable to the minute from Auto Mode's detection delay):

- `drives.visible_at` (name approved): `max(ended_at + 15 min, floor(received, 15 min) + 15 min)`,
  set at publish; a new revision of a drive others already see keeps it. Index `drives_on_visible_at`.
- `feed_items.last_ended_at` counts only drives with `visible_at <= ` the current quarter. A new
  job `feed.release` on its own cron `*/15 * * * *` refreshes the items whose drives became visible
  since its cursor (`job_states.cursor`), bounded and idempotent; the hourly jobs stay on `17 * * * *`.
- `RECENT_SQL` and the merge at read go: a page is ~21 items through `feed_items_on_feed`.
- Hiding stays immediate (owner): an unpublish refreshes its item at once.
- Review minor 1: `prune.expired` also deletes items whose `last_ended_at` left the window.
- `apps/api/wrangler.jsonc` is committed whole (owner: the paid team's APP_ID is in use).
- Test: a drive ended 10:37 and published 10:47 is not on another reader's page before 11:00.
