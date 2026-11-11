# Feed V1 · Part 1 — docs and contract 0.27.0-draft · Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `carodo-ios/docs` states Feed V1 exactly as designed, and `docs/api/carodo-api.yaml`
0.27.0-draft is the contract the paused backend will build against.

**Architecture:** Docs only, no Swift. Rewrite in place (pre-release: ADRs and contract are edited,
not superseded). The contract keeps every working mechanism (revision + tombstone publishing, the
sealed cursor, ETag, RFC 9457 problems, guest read tokens) and drops or reshapes what V1 does not have.

**Tech Stack:** Markdown, OpenAPI 3.1 YAML. Checks with the system `ruby` (no package added).

**Spec:** `carodo-handbook/plans/feed-v1-design.md` (approved 2026-11-11). Read it first; this
plan only decides what that document leaves to the contract and the doc layout.

## Global Constraints

- Every document in English; Vietnamese only as app copy beside its English (AGENTS.md, Language).
- `carodo-ios/docs` never links to `carodo-handbook/` (AGENTS.md, Docs).
- P5/P9: nothing another person sees carries a position, place or a time finer than the hour.
- P6: the contract diff is shown to the owner and approved **before** it is committed.
- P8: no AI attribution in commits.
- Stage only the paths this plan touches; never `git add -A`.
- Contract version string: `0.27.0-draft`.

## Review Focus

1. **A dangling `$ref`** after removing schemas (`LiveDriver`, `TopDriver`, `LeaderboardEntry`,
   `PublicProfile`, `FollowedDriver`, `FeedBadge`, `BadgePublication`, `BadgeCatalogue`,
   `DriveArea`, `Region`, `Scope`, `ServedScope`, `UserId`): the backend's generator fails. Task 4
   Step 2 checks every `$ref` resolves.
2. **A doc still describing a deleted thing** (Live, leaderboard, Following, Profiles, badges on the
   Feed, Nearby/region, `feedOptIn`, `liveOptIn`, "Show username"): a builder follows the stale
   line. Task 6 greps for them.
3. **A field that leaks time or place** slipping into a response schema (`startedAt`, `endedAt`, a
   minute, a zone, a province). Task 4 Step 3 greps response schemas.
4. **Anonymous linkability:** an anonymous row's `id` must be random per row, never derived from
   the account or trip, and the response never carries an author id (design: block through the
   post). Task 4 Step 3 asserts `authorId`/`userId` do not appear in `FeedItem`.
5. **Guest writes:** reactions, publish, sharing, report and block must require `bearerAuth`
   (members only, owner 2026-11-11); only `GET /v1/feed`, `GET /v1/feed/stats` and the username
   check accept a guest token. Task 4 Step 3 checks each path's `security`.

---

### Task 1: ADR 0007 and ADR 0008 state V1

**Files:**
- Modify: `carodo-ios/docs/decisions/0007-privacy-first-feed.md` (whole Decision section)
- Modify: `carodo-ios/docs/decisions/0008-join-with-a-username.md`

- [ ] **Step 1: Rewrite ADR 0007's Decision for V1.** Keep Status `Accepted`, add
  `Amended 2026-11-11 (Feed V1)`. It states, each as one bullet:
  - tabs unchanged (Map · Journeys · Feed); on the Feed the avatar opens your Feed sharing page
    (not a Profile);
  - V1 is one worldwide Feed of car drives from the last 72 hours; no tabs, filters, Following,
    Profiles, Live, leaderboard, area/region, badges on the Feed;
  - a row is one person's drives on their local day; anonymous by default ("Someone"), the
    username only if the person chose it; a row's id is random; no author id in any response;
  - never a route, map, place, start/end or a time finer than the hour ("2h ago", part of day);
  - the shape rule: device-made from the trimmed route (`max(privacy zone, 300 m)`, Home/Work
    rule), none under 2 km, 48–64 points in the unit box, aligned to its own long axis, seeded
    tilt ±15° and mirror; drawn without a start/end marker;
  - five fixed reactions (🔥 ☕ 🌙 🌧 🎉), no likes, no counts of who; members only;
  - community stats need 10 distinct drivers; below that no number is shown;
  - nothing ranks or rewards speed.
  Reason: keep the existing reason, add "reactions say how a drive felt, likes reward
  performance". Consequence: report and block through the post are required before the App Store;
  the removed features are later phases (named, not specified).
- [ ] **Step 2: Amend ADR 0008.** Joining = claim a username **and** choose how you appear
  (Someone / username) and whether the car is named, then **Start sharing**; nothing is published
  before it. Remove "an optional photo" and the display-name default. Keep the Keychain account,
  sessions, Sign in with Apple recovery, deletion. Add: Stop sharing removes the posts and keeps
  the username; username rules (format, no leading/trailing `.`/`_`, no `..`/`__`, reserved words,
  server profanity list VI+EN, 3 changes per 30 days).
- [ ] **Step 3: Check** `grep -nE "Discover|Following|leaderboard|Live|Nearby|region|badge|photo" docs/decisions/0007-privacy-first-feed.md docs/decisions/0008-join-with-a-username.md`
  Expected: only lines naming them as later phases.

### Task 2: `docs/specs/feed.md` rewritten for V1

**Files:**
- Modify: `carodo-ios/docs/specs/feed.md` (whole file)

- [ ] **Step 1: Rewrite with the sections** `Purpose`, `Today`, `Behaviour` (Header · Your drive ·
  Invite · Rows · Reactions · Route shape · States · Joining · Feed sharing page · End of a drive ·
  Hiding), `Data and privacy`, `Acceptance`. Content comes from the design's Decisions, in spec
  voice. Copy appears as English with its Vietnamese beside it where the design fixes it
  ("You're among the first drivers"; "driving together around the world" / "cùng lái trên khắp
  thế giới"; "Join the Feed"; "Start sharing"; "Show vehicle name"; "Your morning drive could be
  here"; "No drives in the last 72 hours"; "Couldn't load the Feed").
- [ ] **Step 2: `Today`** says: built = M1 read-only Global feed on `SampleCommunityRepository`;
  not built = everything else in this spec; the deferred UI is to be deleted.
- [ ] **Step 3: Delete** the `Vehicle classes` section (cars only now, one line under Rows) and the
  `Header control` subsection.
- [ ] **Step 4: Acceptance** lists one checkable line per behaviour (e.g. "below 10 drivers the
  header shows no number, no 72h pill, no Worldwide label").
- [ ] **Step 5: Check** `grep -nE "Discover|Following|leaderboard|Live|Nearby|Profile|badge" docs/specs/feed.md` → no line except a later-phase note.

### Task 3: Settings, account, data model, design system

**Files:**
- Modify: `carodo-ios/docs/specs/settings.md:17-19,47-48`
- Modify: `carodo-ios/docs/specs/account.md`
- Modify: `carodo-ios/docs/data-model.md` (the `trips` publishing columns, line ~466)
- Modify: `carodo-ios/docs/design-system.md` (new subsections)

- [ ] **Step 1: settings.md** — item 1 becomes the driver card with no heading; the Feed identity
  row is removed; Privacy gains **Feed sharing** (state Off / Someone / username; opens the
  sharing page or the Join sheet); drop "Show my area on the Feed".
- [ ] **Step 2: account.md** — no photo; Stop sharing vs deleting the account; username rules
  (same as ADR 0008).
- [ ] **Step 3: data-model.md** — replace `publish_to_feed` / `published_at` with
  `trips.feed_state TEXT NOT NULL DEFAULT 'none'` (`none` · `published` · `hidden`) and
  `trips.feed_published_at REAL NULL` (when the backend acknowledged). `hidden` survives Stop
  sharing, rejoining and the 72 h backfill; deleting a journey sends an unpublish. Mark it
  "schema change approved with the Feed V1 design (P6); lands in `v1_initial` in part 4".
- [ ] **Step 4: design-system.md** — add `RadioCard` (selected: pale copper fill, thin copper
  border, filled radio; unselected: surface, no border; `isSelected` trait) and **Feed shape**
  (Catmull-Rom curve, taper, fade both ends, ribbon masked off the text side with a haloed core,
  Stone for others via a semantic colour, Copper for you, no markers).
- [ ] **Step 5: Check** `grep -n "publish_to_feed\|published_at" docs/*.md docs/specs/*.md` → none
  outside a "replaced by" note.

### Task 4: Contract 0.27.0-draft

**Files:**
- Modify: `carodo-ios/docs/api/carodo-api.yaml`

**Interfaces (what parts 2–5 build against):**
- `GET /v1/feed?cursor=` (guest or member) → `{ items: FeedItem[], nextCursor, hasMore }`; ETag/304 kept.
- `GET /v1/feed/stats` (guest or member) → `CommunityStats`.
- `GET|PUT /v1/me/sharing` (member) ↔ `Sharing { sharing: bool, displayAs: anonymous|username, showVehicle: bool }`.
- `PUT /v1/feed/drives/{tripId}` (member) body `DriveInput` → 204; `DELETE …?revision=` → 204.
- `PUT|DELETE /v1/feed/items/{itemId}/reaction` (member) body `{ reaction: Reaction }`.
- `POST /v1/feed/items/{itemId}/report`, `POST /v1/feed/items/{itemId}/block-author` (member; defined, built later).

- [ ] **Step 1: Edit the YAML.**
  - `info.version: 0.27.0-draft`; description gains one line: Feed V1, worldwide, 72 h.
  - **Remove paths:** `/v1/leaderboard`, `/v1/users/{userId}`, `/v1/users/{userId}/feed`,
    `/v1/follows/{userId}`, `/v1/following`, `/v1/live`, `/v1/reports`, `/v1/blocks/{userId}`,
    `/v1/badges/catalogue`, `/v1/me/badges/{badgeId}/{publicRef}`, `/v1/drives/{tripId}`.
  - **Remove schemas** no path uses any more (Review Focus 1 list) and the `Scope`/`Region`
    parameters.
  - **`/v1/me/profile`:** `ProfileInput` keeps `username` only (no `displayName`, `avatarUrl`,
    `feedOptIn`, `liveOptIn`, `regionCode`).
  - **Add `/v1/me/sharing`** (`Sharing` above). `PUT` with `sharing: false` removes every post
    (the server keeps tombstones as today). `displayAs`/`showVehicle` apply at read.
  - **Add `/v1/feed/drives/{tripId}`:** move the old `/v1/drives/{tripId}` PUT/DELETE here with its
    revision + tombstone text; drop leaderboard wording and `hour_full`; 403 `sharing_off`;
    422 `start_time_invalid`, `geo_payload_rejected`, `not_a_car`.
  - **`DriveInput`:** keep `revision`, `startedAt`, `localDate`, `distanceM`, `movingDurationS`,
    `elapsedDurationS`, `vehicle`, `partOfDay`; add `localStartHour` (integer 0–23, the busiest-hour
    statistic only, never returned), `endedAt` (date-time, server-only for "Nh ago", never
    returned), `weather` (enum `rain`, `clear`, `unknown`); remove `tags` (V1 has no tag but weather),
    `maxSpeedMps` and `area`.
  - **`DriveShape`:** `{ version: 1, points: [[x,y], …] }` or null; numbers 0–1, `minItems` 8,
    `maxItems` 64; description = the design's shape rule.
  - **`FeedDrive`:** `durationS`, `distanceM`, `ago`, `partOfDay`, `weather` (only `rain` is ever
    sent back; absent otherwise), `shape`.
  - **`FeedItem`:** one person's drives on their local day: `id` (random per item), `isAuthor`
    (bool), `displayName` (string or null = "Someone"), `vehicle` (or null when hidden),
    `drives` (newest first, the client shows the 3 longest), `totalDurationS`, `totalDistanceM`,
    `ago`, `reactions: { [Reaction]: integer }` (only those > 0), `myReaction` (Reaction or null).
  - **`Reaction`:** enum `fire`, `coffee`, `moon`, `rain`, `party` (🔥 ☕ 🌙 🌧 🎉).
  - **`CommunityStats`:** `windowHours: 72`, `visible` (bool); when visible `drivers`,
    `distanceM`, `durationS`, `busiestHour` (0–23, authors' local hour); when not, all four `null`
    and `warmup` (0–1, multiples of 0.1); never a number from fewer than 10 drivers.
  - **`/v1/feed`:** drop `tab`, `scope`, `region`, `live`, `stats`, `topDrivers`; 72 h window;
    blocked authors excluded for a member.
  - **Username:** `Username` pattern becomes
    `^(?![._])(?!.*[._]$)(?!.*(\.\.|__))[a-z0-9_.]{3,20}$`; `/v1/usernames/{username}` reasons add
    `profane`; `PUT /v1/me/profile` 429 `username_change_limit` (3 per 30 days).
  - Errors stay `Problem` (RFC 9457) with `code`.
- [ ] **Step 2: Every `$ref` resolves and the file parses.**

  Run:
  ```sh
  ruby -ryaml -e 'd=YAML.load_file("docs/api/carodo-api.yaml"); refs=File.read("docs/api/carodo-api.yaml").scan(/\$ref: "#\/([^"]+)"/).flatten.uniq; bad=refs.reject{|r| r.split("/").reduce(d){|n,k| n.is_a?(Hash) ? n[k] : nil}}; puts(bad.empty? ? "ok #{refs.size} refs" : bad)'
  ```
  Expected: `ok N refs`.
- [ ] **Step 3: Privacy and auth greps.**
  - `ruby -ryaml -e 'd=YAML.load_file("docs/api/carodo-api.yaml"); s=d["components"]["schemas"]; puts (%w[FeedItem FeedDrive CommunityStats].map{|k| s[k].to_s}.join =~ /startedAt|endedAt|authorId|userId|region|minute/) ? "LEAK" : "clean"'` → `clean`
  - `ruby -ryaml -e 'd=YAML.load_file("docs/api/carodo-api.yaml"); d["paths"].each{|p,v| v.each{|m,o| next unless o.is_a?(Hash) && o["summary"]; g=(o["security"]||d["security"]).to_s.include?("guestToken"); puts "#{m.upcase} #{p}" if g}}'`
    → exactly `GET /v1/feed`, `GET /v1/feed/stats`, `GET /v1/usernames/{username}`, plus the
    auth/account paths that already allowed it (unchanged).
- [ ] **Step 4: Show the owner** `git diff --stat docs/api/carodo-api.yaml` and a one-screen summary
  of added/removed paths. **Wait for approval (P6) before Task 7.**

### Task 5: `docs/sync.md` follows the contract

**Files:**
- Modify: `carodo-ios/docs/sync.md` (table rows 13–34, sections from line ~194 and 218–262)

- [ ] **Step 1:** Remove the Live status row and the badge publication protocol paragraphs
  (`publishBadge`/`unpublishBadge`, `public_ref` for the Feed); keep badge *state* sync to iCloud.
- [ ] **Step 2:** "Publishing to the Carodo backend" becomes: while sharing is on, each completed
  car drive whose `feed_state` is not `hidden` is sent with `PUT /v1/feed/drives/{tripId}` through
  the outbox (key `feed:<tripId>`); revision rules unchanged; on Start sharing the car drives that
  ended in the last 72 h are enqueued; hide/delete enqueue `DELETE …?revision=`; weather is
  decided on the device; no region. Update the direct-vs-outbox table to the new paths.
- [ ] **Step 3: Check** `grep -nE "feedOptIn|liveOptIn|regionCode|/v1/live|/v1/drives/|publishBadge" docs/sync.md` → none.

### Task 6: Leftovers across docs

**Files:**
- Modify: any file the grep below finds in `carodo-ios/docs/` and `carodo-ios/AGENTS.md` (P5 line on
  the Feed: "at most a province the person opts into" → removed), workspace `AGENTS.md` (same line).

- [ ] **Step 1: Find** `grep -rnE "Live|leaderboard|Following|Nearby|province the person opts|feedOptIn|liveOptIn|Show username|Profiles?\b" docs AGENTS.md ../AGENTS.md | grep -v "^docs/api/"`
- [ ] **Step 2:** Fix each hit to V1 or to "a later phase", or leave it when it is about something
  else (a car's "live" panel, iCloud "following" a record). Name the kept ones in the report.
- [ ] **Step 3:** `carodo-app/AGENTS.md` carries the same P5 line, but another session has
  uncommitted work there: do not edit it; name it in the report for the owner.
- [ ] **Step 4: Handbook:** add a "Feed, later" block to `carodo-handbook/product/roadmap.md`
  listing what V1 removed (Live, leaderboard, Following, Profiles, milestones/badges on the Feed,
  challenge, top cars, area/region, two-wheelers, filters) and mark TD-8 in
  `plans/technical-debt.md` as a release blocker (report + block through the post).

### Task 7: Commit (after the owner approved the contract)

- [ ] **Step 1:** `cd carodo-ios && git add docs/decisions/0007-privacy-first-feed.md docs/decisions/0008-join-with-a-username.md docs/specs/feed.md docs/specs/settings.md docs/specs/account.md docs/data-model.md docs/design-system.md docs/api/carodo-api.yaml docs/sync.md AGENTS.md` plus any file Task 6 changed; `git diff --cached --stat` lists only those.
- [ ] **Step 2:** `git commit -m "docs(feed): feed v1 spec, adrs and contract 0.27.0-draft"` (body: the
  decisions in three lines; no AI trailer).
- [ ] **Step 3:** Workspace `AGENTS.md` (not a repo) is saved, not committed. Handbook:
  `git add product/roadmap.md plans/technical-debt.md && git commit -m "docs(roadmap): feed features after v1, report and block before release"`.
