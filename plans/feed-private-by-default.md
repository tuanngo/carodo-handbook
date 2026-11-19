# Feed: private by default (quarter-hour times, a 7-day Feed that deletes itself, a sharing preview)

Status: **design approved by the owner, 2026-11-19** (with C1–C7; the shape is not location on the
label; the preview copy approved). Part 1 (decisions and contract) done 2026-11-19: carodo-ios `d0186ad`, carodo-app `a276e84`. Next: Part 2 (backend). Supersedes the "Hour rounding before sending" section of
[`privacy-policy-review.md`](privacy-policy-review.md) (owner, 2026-11-18): the rounding is now to
the quarter hour, and the server no longer keeps any exact Feed time.

## Why

The Feed is extra: signals of how people drive, not the product. Carodo is private by default, and
that is what we tell users and App Review. A pre-staging review of the backend (2026-11-19) found
that the Feed still leaks *when* a person drove, finer than the hour that ADR 0007 / P9 promise:

1. A drive leaves the Feed at exactly `ended_at` + 72 h (`apps/api/src/services/feed/read.ts`
   compares the exact end; `stats.ts` likewise). A reader who polls sees the moment it goes.
2. An item turns from "now" to "Nh" at exactly `ended_at` + 1 h
   (`services/shared/coarse-time.ts`, `NOW_AFTER_END_MS`).
3. A drive appears on the Feed the moment it is published, which is about when it ended. Anyone
   refreshing learns when "@tuan" arrived; over days, their routine (home, work).
4. The shape is promised deleted within 30 days (contract `DriveShape`, `carodo-ios/docs/privacy.md`,
   `specs/feed.md`), but nothing deletes it; drives taken off by Stop sharing stay forever.

Prior art the owner looked at: another drive app's global feed sends username, avatar, exact
`startedAt`/`endedAt` to the millisecond, a route path, and fuel station names with times. Carodo
deliberately does none of that.

## Goals

- Nothing another person sees tells a time finer than **15 minutes**, including the moment a drive
  appears or disappears. Labels stay coarse ("now", "2h", "3d").
- The backend **never stores** an exact Feed time. It receives and keeps quarter-hour times only.
- The driver sees their own drive on the Feed **at once**.
- The Feed covers **7 days** (168 h). A drive older than that is **deleted** from the backend, with
  its shape, its item and the reactions on it. No separate 30-day retention.
- Before sharing, the person **sees exactly the row others will see**.
- The privacy policy, `docs/privacy.md`, the App Store label and App Review notes tell the same
  story, saying *what* is kept and for how long, not *how* it is computed.

## Non-goals

- Live status, leaderboards, follows, profiles, badges on the Feed (still later phases, ADR 0007).
- Report and block (still deferred).
- Share links (`/v1/shares`): not built; unchanged here.
- Changing the shape algorithm (`DriveShapeMaker`): unchanged.

## Anti-goals (a failure even if it works)

- Any response, cache, appearance or disappearance that lets a reader place an end or start
  finer than a quarter hour.
- An exact Feed time at rest on the backend (D1, R2, logs, analytics).
- A preview that differs from what is actually sent (it must be built by the same code path).
- The author waiting for the quarter to see their own drive.

## Decisions (the owner's, 2026-11-19)

| # | Decision |
|---|---|
| D1 | Others see a drive from the **next quarter-hour boundary** after it ended (ended 10:37 → shown 10:45). All drives of a quarter appear together, in a random order inside it. |
| D2 | The **author sees it at once**, on their own Feed page, before the quarter. |
| D3 | The device sends times **rounded to the quarter hour**; the backend stores no exact Feed time. |
| D4 | The Feed window is **7 days**; a drive that leaves it is **deleted** (drive, shape, empty item, its reactions). |
| D5 | **Stop sharing** and **account deletion** delete the rows at once; nothing is kept to republish. Start sharing again publishes only drives that end from then on (no backfill, ADR 0008, as `FeedPublisher` does). |
| D6 | The **privacy policy (web)** is updated; it states what and how long, not the mechanism. |
| D7 | A **sharing preview** shows the person's row as others will see it, in **Share your drives?** (top, above the two radio cards) and in **Edit profile** (under Sharing). |
| D8 | P9 becomes: nothing another person sees carries a time finer than **15 minutes**; labels say hours or days. |

## Calls made by the agent (the owner may overturn while reading)

- **C1. Overlap check moves to the device.** ADR 0007 (Plausibility) asks the server to refuse a
  drive that overlaps another; with quarter-hour times it cannot check this precisely. App Attest
  already limits callers to the genuine app, which never records overlapping drives. ADR 0007's
  Plausibility line is amended; the range checks (≤ 24 h, distance, duration) stay on the server.
- **C2. The preview uses the person's latest car drive** (real shape, distance, duration, part of
  day), built on the device by the same mapper the outbox uses; with no car drive yet, a fixed
  sample drive, labelled as an example. Nothing is sent to build it.
- **C3. Precision of figures:** durations sent rounded to the minute, GPS distance to 100 m.
  Exact seconds plus the quarter would narrow the start; this keeps both ends at quarter level.
- **C4. Unpublish tombstones stay, but only inside the window.** Without one, a hide (`DELETE`,
  revision 5) arriving before a late publish (revision 4) would let the hidden drive back. The
  tombstone is deleted with the window like everything else, so nothing outlives 7 days.
- **C5. The age label** counts from when others first see the drive (its release quarter):
  "now" for the first hour, then "1h"–"23h", then "1d"–"6d". Every change of label falls on a
  quarter boundary.
- **C6. Server audit times** (`published_at`, `updated_at`, `unpublished_at` on `drives`,
  `created_at` on `feed_items`) stay exact server time (owner, 2026-11-19, after Part 1): when the
  server received a write, never in a response, never an order, never a reason to show or hide
  anything. Pruning and the Feed's order use the drive's `ended_at`. `reactions.created_at` stays
  exact: it is the reader's own data (their export), never shown to anyone else.
- **C7. The day cap** (50 visible drives a local day) stays.

## How it works

### What the device sends (contract `DriveInput`, `PUT /v1/feed/drives/{tripId}`)

Replaces `startedAt` / `endedAt` (exact) with:

- `endedAt`: RFC 3339 UTC, minutes in {00, 15, 30, 45}, seconds 0; the drive's end floored to
  the quarter hour.
- `elapsedDurationS`, `movingDurationS`: whole minutes in seconds (multiples of 60).
- `distanceM`: a multiple of 100.
- Unchanged: `revision`, `localDate`, `localStartHour`, `partOfDay`, `vehicle`, `weather`, `shape`.

The server refuses (400 `validation`) a time not on a quarter, a duration not a multiple of 60, a
distance not a multiple of 100: the rule is enforced, not hoped for. Ranges stay (422
`out_of_range`); `endedAt` more than 15 min ahead of the server is 422 `start_time_invalid`
(name kept for compatibility, or renamed `time_invalid`: builder's call, in the contract).
A drive whose `endedAt` is already outside the 7-day window is answered 204 and not stored.

### What the backend keeps (D1, pre-release: edit `0001_baseline.sql` in place)

- `drives`: `ended_at` (INTEGER Unix ms, on a quarter) keeps its name and replaces `started_at`,
  `drove_at`; `stopped_at` goes (D5 deletes instead). Audit times stay exact server time (C6).
- `feed_items`: `sort_hour` goes; `last_ended_at` (the newest visible drive's `ended_at`)
  keeps its name. Order: `last_ended_at DESC, id DESC` (the id is random).
- Indexes follow the queries (cost rules C1, C2, C5): the Feed page, the release check, the
  hourly deletion by `ended_at`, an account's drives.

### Who sees what, when

- **Others (and guests):** a drive is on the Feed once `ended_at + 15 min <= now` (its
  release) and while `ended_at >= now − 168 h`, both compared on quarter boundaries. An item is
  on the Feed while it has a released drive, ordered by its newest *released* drive's quarter: a
  drive not yet released never moves or hides its item (otherwise a publish at 10:37 would move or
  hide the day's item at that moment). So the order is computed from released drives at read time
  or on release, never at publish.
  The shared, cached page (ADR 0008 in carodo-app) is computed with `now` floored to the quarter,
  so a cache never straddles a release.
- **The author:** the member's overlay (`readerPage`) adds the reader's own drives that are not
  released yet, from one indexed read by account, and merges them into their own item for that
  day (or shows that item at the top when it is not on the shared page yet). `isAuthor` and
  `tripIds` as today.
- **Hiding stays as built** (`specs/feed.md`): long-press your own row → Hide from feed, "Shared to
  Feed · Hide" on the drive summary, "On the Feed" on Journey detail; Stop sharing removes all.
  New with this design: a drive hidden before its release quarter is never seen by anyone else.
  A hidden drive keeps only its tombstone (trip id, revision; no summary, no shape) until the
  window deletes it (C4).
- **Stats** (`/v1/feed/stats`): over released drives in the 7-day window; still only from 10
  distinct drivers; busiest hour from `localStartHour`. `windowHours` becomes 168.

### Deletion

- **Hourly job** (`prune.expired`, bounded, one batch): deletes drives (and tombstones) whose
  `ended_at` is older than 168 h plus one hour of margin, then items left with no drive;
  reactions go with their item (`ON DELETE CASCADE`).
- **Stop sharing:** deletes the account's drives and items in the same batch as the switch.
- **Account deletion:** deletes the Feed rows at once (not only `hidden_at`); the rest of the
  erase is as today.
- **Start sharing again:** no backfill (ADR 0008; `FeedPublisher` publishes only drives that end
  after sharing turned on). The app's Feed window (`FeedPublisher.feedWindow`, 72 h today) becomes
  7 days, so a drive caught up late is still sent within the window.

## Sharing preview (iOS)

- **Where:** at the top of **Share your drives?** (step 2 of joining) and in **Edit profile** under
  the Sharing switches (`specs/feed.md`, Joining and Profile).
- **What:** one Feed row, drawn by the Feed's own row view, from the person's latest car drive
  (C2), through the same mapper the outbox uses (`FeedPublication`, `DriveShapeMaker`), so the
  preview is what would be sent. It follows the choices live: Anonymous shows "Someone",
  @yourname shows the name; Show vehicle name off removes the car. Age shows "now".
- **Copy** (approved by the owner, 2026-11-19): "This is all others see. Never your route, places
  or exact times." / "Người khác chỉ thấy như thế này. Không bao giờ thấy lộ trình, địa điểm hay
  giờ chính xác."
- A mockup in `design/mockups/` before code (`AGENT_WORKFLOW.md`, Design).
- Light/Dark, largest Dynamic Type, VoiceOver reads the row as the Feed does.

## Privacy story (web, docs, Apple)

- **Privacy policy** (`carodo-app/apps/web/src/pages/privacy-content.ts`; another session has
  uncommitted edits there: add to them, never overwrite): the Feed paragraph says each shared drive
  shows for 7 days and is then deleted from our servers; we never store or show the exact time a
  drive started or ended; others see only a rough time ("just now", "2h ago"). No mention of
  quarters, ordering or shape rotation. Drop "we erase the rest within 30 days" for Feed data.
- **`carodo-ios/docs/privacy.md`, `specs/feed.md`, `sync.md`:** the new times, the 7-day window,
  deletion, the preview; remove "deletes shapes and vehicle names within 30 days".
- **carodo-app `docs/storage.md`, `docs/architecture.md`:** what `drives` now holds.
- **App Store privacy label:** unchanged types (User ID; Other User Content: drive summaries and
  reactions). The abstract shape is **not** declared as location: it cannot be placed on a map
  (owner, 2026-11-19; closes that item in `privacy-policy-review.md`).
- **App Review Notes** (handbook `plans/apple-questions.md` or the submission checklist): a sample
  `PUT /v1/feed/drives` body, the sentence "no coordinates or places; times rounded; deleted after
  7 days", and a screenshot of Share your drives? with the preview.

## Documents and code to change

1. **Decisions and contract** (owner approves the diff; P6):
   ADR 0007 (P9 wording, 7-day window, Plausibility, deletion), the P9 / invariant 9 text in the
   workspace `AGENTS.md`, `carodo-ios/AGENTS.md`, `carodo-app/AGENTS.md`;
   `carodo-ios/docs/api/carodo-api.yaml` → 0.29.0 (`DriveInput`, `Ago`, `CommunityStats.windowHours`,
   `/v1/feed` and `/v1/feed/drives` descriptions, `DriveShape` retention, account export's drives);
   `carodo-ios/docs/sync.md` (Publishing; the backend has no copy of the contract, it cites this
   one); carodo-app ADR 0007 (late is normal: tombstones within the window);
   `services/shared/coarse-time.ts` header.
2. **Backend:** baseline schema; `drives/input.ts` (new fields, strict rounding), `drives/publish.ts`
   (drop out-of-window, delete on Stop sharing), `feed/items.ts`, `feed/read.ts` (release, window,
   author overlay), `feed/stats.ts`, `coarse-time.ts` (quarter, labels per C5),
   `accounts/sharing.ts`, `accounts/lifecycle.ts`, `jobs/prune.ts`; tests on both sides of every
   boundary (release at :45 − 1 ms / :45, window at 168 h, label changes), cost tests (no full
   scan), and a test that no response or cached page carries a time off a quarter.
3. **iOS:** `FeedPublication` and `FeedAPI.DriveInput` (rounding), `FeedPublisher.feedWindow` (7 days),
   `LocalFeedServer` (the mock follows the new contract), the preview view and its two placements,
   strings (EN + VI).
4. **Web and docs:** privacy policy, `privacy.md`, `feed.md`, `sync.md`, backend `storage.md`;
   `privacy-policy-review.md` updated to point here.

Texts still describing today's behaviour after Part 1 (sweep, 2026-11-19), each changed by the part
that changes the behaviour:

- Part 2 (backend): carodo-app `docs/storage.md:17-18`, `docs/architecture.md:18,111`,
  `docs/cost.md:39,41` (examples on `drove_at` / `sort_hour`).
- Part 3 (iOS): `specs/feed.md:24,71-72,101,168-169,283,287-288,303` (72 h, the "72h" pill and its
  empty-state copy in EN and VI, 30-day shapes, "finer than the hour"); `data-model.md:222`
  ("72-hour backfill"); `operations/setup.md:167` (the mock publishes "the last 72 hours").
- Part 4 (docs): `privacy.md:107` ("finer than the hour").
- Unchanged: `specs/settings.md:115` and its `Settings.xcstrings` line are the tracking log, not the
  Feed.

The contract change is breaking and needs no compatibility path: nothing is released, the app and
backend move together, and local/staging D1 is reset (`task db:reset`).

Suggested order: 1 → 2 → 3 → 4, one commit per repo per finished outcome. Staging can be deployed
before or after; it holds no real user data.

## Acceptance

- No Feed or stats response, and no cached page, contains a time, or changes, at a moment finer
  than a quarter hour (tests freeze `now` at both sides of :x5 boundaries).
- A drive ended 10:37 is absent from a guest's Feed at 10:44:59.999 and present at 10:45; present
  on its author's Feed at 10:37 (once published).
- No D1 column on `drives` / `feed_items` holds a time off a quarter.
- A drive whose `ended_at` is 169 h old is gone from D1 after the hourly job; its item and
  reactions too. Stop sharing leaves no published drive for the account (a hidden drive's
  tombstone stays until its window passes).
- A publish with a time off a quarter, or durations/distances not rounded, is refused 400.
- The preview row equals the row the Feed later shows for that drive (same mapper; a unit test
  compares them), and follows Anonymous / @name / Show vehicle name live.
- Policy, `privacy.md`, label and App Review notes say the same thing.
- `task app:check`, `task ios:test`, `task ios:lint`, `task ios:warnings` pass; screenshots of
  the preview (Light/Dark/VI/largest type).

## Left to the builder

- Exact SQL and index shapes (within the cost rules), the cache key's quarter.
- Whether `start_time_invalid` is renamed (keep the code stable if the app already branches on it).
- How the author's unreleased drive merges into their item on the client vs the server, as long
  as `FeedItem` stays the contract's shape.
- The preview's layout details, after the mockup.

## Carried into Parts 2 and 3 (Part 1 review, 2026-11-19)

- `Ago` for the author's drive before release: "now"; `FeedItem.ago` counts from the newest drive
  the reader can see (Part 2).
- A drive under 100 m after rounding is not sent (Part 3); a `minimum`/`maximum` breach stays 422
  `out_of_range` as today (Part 2).
- The account export lists published drives only, never tombstones (Part 2, contract line).
- carodo-ios ADR 0007 "A Feed row": add the 100 m distance rounding; carodo-app P9 title
  "Coarse at rest" → "Coarse drive times at rest" (with Part 2's docs).
- `services/shared/coarse-time.ts` header (Part 2).
