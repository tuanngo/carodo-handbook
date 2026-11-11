# Feed V1 — design

Status: **design, brainstormed with the owner 2026-11-11; builder check done; waiting for the owner's approval.** No code
changed. Replaces the plan in `feed-v2.md` (its audit and diff table stay the reference for what
exists today). Mockups: `.superpowers/brainstorm/9623-1794391688/content/` (throwaway HTML, not
committed). "My call" marks a choice the agent made that the owner did not decide; everything else
was decided by the owner in the brainstorm.

## Intent

The Feed answers two feelings at a glance: **where does my drive sit among everyone's, and how many
people are driving right now.** It is a quiet, worldwide pulse of people driving — how they drive
(car, part of day, distance, time), never where (ADR 0007). Nobody appears on it without asking to:
it is global, so joining is an explicit choice, and how you appear is chosen at the same moment.

The owner's `feed_spec_v2.md` asked for much more (tabs, milestones, challenges, top cars, two-wheelers,
4 parts of day). V1 is deliberately smaller; what was cut is listed under Non-goals and Phase 2.

## Goals

- A global Feed of car drives from the last 72 hours, one row per person per day.
- A header that gives the community's pulse (drivers, km, hours, busiest hour) and pins your own drive.
- Opt-in through one sheet: claim a username, pick how you appear (Someone / username), pick whether
  your car is named. Nothing is published before **Start sharing**.
- Your own posts are always yours to hide, one by one or all at once.
- Five fixed reactions instead of likes.
- The API contract for all of it (the backend is paused and only receives the contract).

## Non-goals (V1)

Tabs and filters (All / Milestones, Discover / Following), Friends and Following, Profiles, Live,
the leaderboard, milestones and badges on the Feed, the challenge card and Top cars, sections
(Today / Yesterday), two-wheelers and bicycles, Area / Nearby / province, comments, product
analytics events. Report and block are **deferred but required before the App Store** (below).

## Anti-goals (a failure even if it works)

- Anything that lets someone find where a person lives, works or drove: a recognisable route, a map,
  a place, an exact time. P5 and P9 bind every line below.
- Anything that rewards driving fast (ADR 0007): no likes, no ranking by speed, no speed figure.
- Appearing on the Feed without having pressed Start sharing.
- A number shown from too few drivers to be anonymous.

## Constraints

- Invariants P5, P6, P7, P9 and the iOS invariants. Contract, schema and the WeatherKit entitlement
  are P6 items: each listed here is approved only when this design is approved.
- Pre-release: contract (0.26.0-draft → 0.27.0-draft) and schema (`v1_initial`) are edited in place;
  no user or data exists anywhere, so nothing migrates.
- Backend paused: this work ships the contract and the iOS app against `SampleCommunityRepository`
  shaped like the new contract. The real `BackendService` path is wired when the backend exists.
- WeatherKit needs a paid team; on a Personal Team the capability is absent and the app sends
  `weather: unknown` (no rain tag), never fails.
- App Store Guideline 1.2: user-generated content needs filtering, report, block and a contact
  before release (TD-8).

## Decisions

### Joining (opt-in) — ADR 0008 amended

- Reading the Feed needs nothing. Appearing on it needs a claimed username **and** pressing Start
  sharing. "Share anonymously" without a username is not offered.
- **Join the Feed sheet** (`FittedSheet`, content height, swipe down to dismiss), top to bottom:
  - title "Join the Feed", subtitle "Your route and places always stay private";
  - username field with a live check ("✓ Available" / the reason it is not);
  - "How should others see you?" — two radio cards: **Someone** (default) and the typed username.
    Selected card: pale copper fill, thin copper border, filled radio; unselected: plain surface, no
    border. A new DesignSystem component (`RadioCard` or similar; SwiftUI has no built-in), with the
    `isSelected` accessibility trait;
  - toggle **Show vehicle name** (default on; off = the car is not mentioned at all, not even "a car");
  - button **Start sharing**: claims the username, saves the choices, publishes.
- Opened from: the invite row on the Feed, the "Share to Feed?" row on the drive summary, the avatar
  when not sharing, and the Settings row.
- Username validation at claim (Guideline 1.2 starts here, not at report time): `[a-z0-9_.]{3,20}`,
  no leading/trailing `.` or `_`, no `..` / `__`, reserved words, a Vietnamese + English profanity
  list kept on the server; at most 3 changes in 30 days (from v2, my call to keep).
- On Start sharing, car drives that ended within the last 72 hours are published too, so the invite's
  "Your morning drive could be here" comes true at once (my call).

### Feed sharing page (after joining)

- Reached from the top-left avatar on the Feed and from Settings. Holds: how others see you
  (Someone / username, the same radio cards), Show vehicle name, the username (change), and
  **Stop sharing**, which removes every post of yours from the Feed and stops publishing. It keeps
  the username; releasing it is deleting the account (`account.md`), unchanged (my call).
- Display name and vehicle visibility apply **at read time** on the server, so changing them changes
  past posts too (my call, as v2).

### Settings — the "Account & Feed" section goes

There is no sign-in (ADR 0008), and the account a username creates is invisible plumbing, so the
heading "Account & Feed" / "Tài khoản & Bảng tin" misleads. The account machinery itself stays as
ADR 0008 has it (Keychain secret, per-device sessions, optional Sign in with Apple recovery, delete
and export in `account.md`); only the heading goes. The optional photo is not in V1 (the locked
sheet has none; the stamp avatar stays).
- The driver card (avatar, local name, "Stored on this iPhone") stays first, with no section heading.
- The **Feed identity** row is replaced by **Feed sharing**, showing its state (Off / Someone /
  the username) and opening the sharing page (or the Join sheet when off). It moves into the Privacy
  section, beside the privacy zone that trims Feed shapes (my call for the placement).
- The old footer goes; the Privacy footer already says what the Feed shows.

### Feed screen

Top bar: avatar (left), "Feed" (title), nothing on the right (no sharing chip).

**Header ("community pulse"):**
- At or above the threshold (10 distinct drivers in the window, server-side k-anonymity):
  pill **72h**, a large "**142 drivers**", then "**9,840 km · 312 h · Busiest 7–8 AM**"
  (the copy keeps the voice of "driven … around the world"). The busiest hour is in the **authors'
  local hours** (people's 7–8 AM wherever they are), so the device also sends its local start hour
  (an hour, P9-coarse) (my call).
- Below the threshold: no pill, no label, no number. One line "**You're among the first drivers**"
  (single line; scales down before it wraps), subtitle "**driving together around the world**"
  ("cùng lái trên khắp thế giới"), then a **road-marking progress line**: dashes of a fixed length
  spread evenly across the width (the count follows the width, not the threshold), the filled part
  copper, rounded to whole dashes. It never states the threshold or a count. It does reveal the
  approximate count to someone who reasons about the fill; the owner accepted that.
- The pill returns only together with the numbers.

**Your drive:** when you share and have a post in the window, your latest day-row is pinned under
the header, tinted copper, named **You**.

**Invite row** (not sharing, at least one car drive in the journal): under the header,
"Your morning drive could be here", the latest car drive's figures and its faint shape, links
**Join the Feed** and **Not now** (snoozes the row for 7 days). Never shown with no car drive.

**Rows:** one per person per author's local day.
- Name: "Someone" or the username; time only as "2h ago" (hour-coarse, P9).
- One drive: "Completed a morning drive in a **Kia EV2**" (or "…a morning drive" with the vehicle
  hidden); chips duration and distance.
- Several drives: "Completed 7 drives in a **Kia EV2**", the 3 longest listed ("2.2 km · 8 min ·
  8h ago"), "+4 more" (tap expands), then the day's total chips.
- Parts of day: the existing **7** (not v2's 4).
- **Route shape as background:** large, faint, bleeding off the right edge of the row, no toggle.
  A multi-drive row shows its longest drive's shape. No shape → no background.
- **Reactions:** 🔥 ☕ 🌙 🌧 🎉, no likes (ADR 0007 amended). A row shows only reactions it has
  received, with counts, plus an always-visible ☺︎ button that opens the five-reaction picker.
  One reaction per viewer per post, tapping another replaces it, tapping it again removes it (my
  call). Who reacted is never shown. Only people who have joined can react (owner): for anyone
  else ☺︎ opens the Join sheet, and guest tokens stay read-only.
- **Rain tag** 🌧 on a drive that started in rain (WeatherKit, below).
- Own row: long-press → **Hide from feed**.

**States:**
- Loading: the existing skeleton.
- Empty (no drives in 72 h): the header stays; below it a faint dashed line, "No drives in the last
  72 hours", "New drives show here as people finish them". No button.
- Failed: no header (no right numbers → no numbers), "Couldn't load the Feed", a line that your own
  drives are safe on this iPhone, **Try again**.
- Offline with a cached page: out of scope for V1 (my call); the failed state applies.

### End of a car drive (`JourneySummarySheet`)

- Not sharing: a row "Share to Feed?" opening the Join sheet.
- Sharing: "Shared to Feed · Hide" (Hide removes that post).
- Non-car drives: nothing.
- Journey detail of a car drive: a toggle for whether that drive is on the Feed.

### What the device sends (publish)

Per car drive, through the outbox (P1: never on the tracking path): `tripId`; the author's local day
(for grouping); `partOfDay` (7 values) and the local start hour (for "Busiest"); started/ended instants in UTC (server-only; it returns only
"Nh ago"); distance (m) and duration (s); vehicle make/model (always sent, hidden at read when the
toggle is off); `weather` (`rain` / `clear` / `unknown`); `routeShape` or `null`. Nothing else:
no coordinate, place, province or speed. Only drives with an assigned vehicle of
`VehicleClass.car` are ever published; a drive with no vehicle is not a car drive (gates publishing,
backfill, the invite row and the summary row) (my call).

**The trip's feed state** (`v1_initial`, replacing `publish_to_feed` / `published_at`, P6): one value
— not shared / published / hidden by you — plus the publish time. A drive you hid stays hidden
through Stop sharing, joining again and the 72 h backfill. Deleting a journey on the phone deletes
its post (my call).

### Route shape (owner: more points than today; the numbers are my call, tune on device)

- Trim the first and last `max(privacy zone, 300 m)` along the route; if the start or end is within
  300 m of a saved Home or Work place, trim until the route leaves that radius (v2 FEED-SHAPE-03).
  Home/Work never leave the device.
- No shape if what remains is under 2 km (v2 said 1 km).
- Simplify (Douglas–Peucker on the normalized polyline, reusing the repo's simplifier) to **48–64
  points**: enough to fill the large background, still too coarse to lay on a street map.
- Normalize into the unit box keeping aspect ratio, then rotate by **any angle** and maybe mirror,
  seeded by `tripId` (the same drive always gives the same shape). Not v2's k·90°, which lines a
  route up with a street grid.
- Drawn with `Path`/`Canvas` only, never MapKit (v2 FEED-SHAPE-07). Tests: v2 FEED-SHAPE-08.

### Weather (P6: WeatherKit capability)

One WeatherKit request per car drive, at its start rounded to ~0.1° (~11 km), never the route;
keep only rain / clear / unknown. No capability or no answer → `unknown`.

### Report and block (deferred, before the App Store)

Not built in V1 (the published data is thin). The contract defines them now so nothing changes
later: report and block **through the post** (`POST /v1/feed/posts/{id}/report`,
`/block-author`); no author id ever appears in a response (an anonymous author stays unlinkable).
Tracked as TD-8 and a release blocker.

### Delete (Phase 2)

Leaderboard (`LeaderboardView`), Live, Following / Discover, Profiles, `FeedFeatures.deferredUI`
and everything only they use: code, catalog strings, spec sections, contract endpoints
(`/v1/leaderboard`, `/v1/users/*`, `/v1/follows`, `/v1/live`, `/v1/me/badges`, `/v1/reports`,
`/v1/blocks/{userId}`). Recorded as Phase 2 in the roadmap so the ideas are not lost.

## Contract 0.27.0-draft (outline)

Errors stay RFC 9457 problem+json, with v2's codes in `code`. A clean replacement, not side by
side: `POST /v1/feed/posts` replaces `PUT /v1/drives/{tripId}`, `/v1/me/sharing` replaces
`feedOptIn` and `region` on `/v1/me/profile`; accounts and auth endpoints stay (my call).
- `GET/PUT /v1/me/sharing` — `sharing` on/off, `displayAs` (`anonymous` / `username`),
  `showVehicle`; turning off removes the posts.
- `POST /v1/feed/posts` — upsert by `tripId` (fields above); `DELETE /v1/feed/posts/{tripId}` — hide.
  Server validates per v2 FEED-VAL-03/04 (rejects anything geographic).
- `GET /v1/feed?cursor&limit` — day groups (author local day), 72 h, opaque cursor, `isAuthor`,
  `displayName` resolved at read, reactions with counts and the viewer's own.
- `GET /v1/feed/stats?window=72h` — `visible`, and when visible drivers / km / hours / busiest hour;
  when not, every number `null` and a coarse `warmup` fraction (0–1, step 0.1) for the progress line.
- `PUT/DELETE /v1/feed/posts/{id}/reaction` — one of the five.
- `POST /v1/feed/posts/{id}/report`, `POST /v1/feed/posts/{id}/block-author` — defined, built later.
- Username claim and check (existing, with the validation above).
- Retention: posts leave the Feed after 72 h; shapes and vehicle names are deleted within 30 days
  (v2 FEED-RET-02).

## Docs that change with it

`carodo-ios/docs/specs/feed.md` (rewritten in English from this design), `settings.md`, `account.md`;
ADR 0007 rewritten in place to state V1 as it stands (reactions instead of no likes, one row per
person per local day, shape at 48–64 points and any angle, no live/region/badges/leaderboard; those
move to the roadmap's Phase 2) and ADR 0008 (joining = username + Start sharing + display
choice) amended in place; `docs/api/carodo-api.yaml` + `docs/sync.md`; `docs/data-model.md` for the
trip's feed state; `docs/design-system.md` for the radio card; the roadmap's Phase 2.

## Proposed order

1. Docs + contract 0.27.0-draft (owner approves the contract, P6).
2. iOS A: route-shape anonymizer and the publish summary builder (pure, tested; no UI).
3. iOS B: sharing settings, the trip's feed state (`v1_initial` column, P6), outbox publishing, 72 h
   backfill on joining, hide; sample repository shaped like the new contract.
4. iOS C: Feed screen (header both modes, invite, rows, reactions, states), Join sheet + radio card,
   sharing page, Settings, summary row, journey detail toggle.
5. iOS D: delete the deferred UI (can go first; independent).
6. WeatherKit tag (needs the capability; degrades to unknown).

## Left to the builder

Exact copy and its Vietnamese (catalog, owner review), dash length and spacing, skeleton details,
the expand animation, the outbox retry policy, which parts of v2's test plan map to which test file.
