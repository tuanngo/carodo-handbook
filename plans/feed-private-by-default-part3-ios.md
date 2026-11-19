# Feed private by default — Part 3: iOS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this
> plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

Status: **3a done and merged into carodo-ios main 2026-11-19 (`5772921`; branch commits d9b72e8, d8212ad, e79d8da, 08f381a, 73774d5, f1c5152).** Final review (fresh reviewer): 0 Critical, 2 Important fixed in 08f381a; code review (high): 9 findings fixed in 73774d5. Owner's open points settled as recommended in f1c5152: the author's own row offers no reaction until the quarter after its earliest drive's end; contract `Ago` counts the same for the author (a late drive is not "now"); `localDate`/`localStartHour` derived from the sent end less the sent minutes. Merged: 2691 tests pass, lint clean. Not yet seen on a simulator: the own row hiding ☺︎. The live round passed before 73774d5 (not re-run). 3b waits for the mockup. Approved by the owner, 2026-11-19 (decisions 1–3 as recommended: 3a now, 3b after the mockup; "7d" chip; "Example" sample).

**Goal:** the app sends what contract 0.29.0-draft asks (quarter-hour `endedAt`, whole minutes,
100 m), publishes within the 7-day window, its mock server behaves like the backend, the Feed's
copy says 7 days, and the person sees their row as others will before they share.

**Architecture:** one pure rounding step in `FeedPublication` (the only place a drive becomes a
`DriveInputBody`); one pure "as others see it" mapper, moved out of `LocalFeedServer`, used by the
mock server and by the sharing preview, so the preview is the mock's row by construction.

**Tech Stack:** Swift 6, SwiftUI, Swift Testing / XCTest (as each test file uses), XcodeGen.

**Spec:** [`feed-private-by-default.md`](feed-private-by-default.md); binding texts: carodo-ios ADR
0007, `docs/api/carodo-api.yaml` 0.29.0-draft (`DriveInput`, `Ago`), `docs/sync.md`; backend as
built in [Part 2](feed-private-by-default-part2-backend.md).

## What the code does today (read 2026-11-19)

- `Core/Domain/Feed/FeedPublication.swift`: builds `DriveInputBody` with exact `startedAt`,
  `endedAt`, `distanceM`, `movingDurationS`, `elapsedDurationS` (Double, unrounded). The real
  backend now refuses every such body (400): **publishing is broken until Task 1 lands.**
- `Core/Networking/FeedAPI.swift`: `DriveInputBody` still has `startedAt`.
- `Core/Feed/FeedPublisher.swift`: `feedWindow = 72 h` (catch-up never sends older drives).
- `Core/Networking/LocalFeedServer.swift` (mock, DEBUG and tests): `windowHours = 72`, shows a
  drive at once to everyone, `ago(started:ended:)` from the exact start, accepts 100 m–2000 km and
  30 s–24 h, builds `FeedItemBody` from stored bodies inline (lines ~290–325).
- Feed copy: `Feed.xcstrings` "No drives in the last 72 hours" (EN, VI), header comments, the stats
  chip shows `windowHours` + "h" (it would say "168h").
- Sharing UI: `JoinTheFeedSheet` (`ShareStep` uses `SharingSwitches`), `FeedProfileSheet`
  (`SharingSwitches` under Sharing); `FeedRow(row: FeedItemPresentation, item: FeedItem, …)`.
- Docs still describing 72 h / 30-day shapes / "finer than the hour": `docs/specs/feed.md`,
  `docs/data-model.md` (`feed_state` row), `docs/operations/setup.md` (the mock's "last 72 hours").
  Line numbers in the spec's sweep have moved; found again by `grep -n "72\|30 days\|finer than"`.

Assumed, not checked: `Journey.elapsedDurationS` and `movingDurationS` are seconds as Double;
`JSONEncoder.carodoAPI` writes dates as RFC 3339 without fractional seconds (checked in Task 1's
test, which decodes the encoded body).

## Global Constraints

- P9: the device keeps exact times; what leaves it about a drive is `endedAt` floored to the
  quarter hour (UTC, seconds 0), `elapsedDurationS` / `movingDurationS` rounded to the nearest
  minute (elapsed at least 60), `distanceM` rounded to the nearest 100 m. A drive under 100 m
  after rounding is not sent (spec, "Carried into Parts 2 and 3"). No start time is sent.
- `localDate`, `localStartHour`, `partOfDay` stay computed from the exact start in the drive's
  zone (they are a day and an hour, not a time).
- Feed window 7 days (`FeedPublisher.feedWindow = 7 × 24 h`), same as the backend's 168 h.
- Preview copy (owner, 2026-11-19): "This is all others see. Never your route, places or exact
  times." / "Người khác chỉ thấy như thế này. Không bao giờ thấy lộ trình, địa điểm hay giờ chính
  xác."
- A screen change needs a mockup in `design/mockups/` approved before code, and screenshots
  (Light/Dark, VI, largest Dynamic Type) before commit.
- Stage only own paths. The main checkout has another session's uncommitted edits in
  `docs/sync.md`, `docs/privacy.md`, `docs/operations/setup.md`: merging this branch must not
  overwrite them (rebase or merge after they commit; say so in the report).

## Decisions for the owner (each with a recommendation)

1. **Split:** Part 3a = Tasks 1–3 (sending, mock, copy and docs; no new screen) now; Part 3b =
   Task 4 (preview) after its mockup is approved. *Recommended*: 3a unblocks publishing against
   the real backend today; 3b waits only for the mockup.
2. **Stats chip text:** "7d" / "7 ngày" when `windowHours` is a whole number of days, else "Nh".
   *Recommended* over "168h".
3. **Preview drive when the person has no car drive yet** (spec C2): a fixed sample (14 min,
   13.7 km, morning, a generic shape) labelled "Example" / "Ví dụ". *Recommended* as the spec says.

## Review Focus

1. A drive ending at hh:59:59.9 local in a zone with a 30/45-minute offset (India, Nepal): the
   quarter is floored in UTC, never in local time.
2. Rounding that crosses a limit: 49 m → 0 (not sent), 99.9 km fine, 23 h 59 min 40 s → 86 400
   (allowed), over 24 h → still refused by the server; moving rounded never above elapsed rounded.
3. A drive ending exactly on a quarter stays on that quarter (no step back).
4. The preview with Anonymous / @name / Show vehicle off, and an empty garage (sample).
5. Catch-up after 5 days offline: drives within 7 days are sent, older ones are not.

---

### Task 1: Send only coarse figures (contract 0.29.0-draft)

**Files:**
- Modify: `Carodo/Core/Domain/Feed/FeedPublication.swift`, `Carodo/Core/Networking/FeedAPI.swift`
  (`DriveInputBody`: drop `startedAt`), `Carodo/Core/Feed/FeedPublisher.swift` (`feedWindow`)
- Test: `CarodoTests/Core/Domain/Feed/FeedPublicationTests.swift`,
  `CarodoTests/Core/Feed/FeedPublisherTests.swift`, `CarodoTests/Core/Networking/FeedAPITests.swift`

**Interfaces:**
- Produces: `FeedPublication.quarter(_ date: Date) -> Date` (floor to 15 min since 1970, UTC),
  `FeedPublication.minutes(_ seconds: Double, atLeast: Double = 0) -> Double`,
  `FeedPublication.hundredMeters(_ meters: Double) -> Double`; `body(...)` returns nil when the
  rounded distance is under 100. `DriveInputBody` without `startedAt`.

- [ ] **Step 1: Failing tests** in `FeedPublicationTests`:
  `endIsFlooredToTheQuarterInUTC` (10:37:12 → 10:30:00; 10:45:00 → 10:45:00; a journey in
  `Asia/Kolkata` ending 16:14:59 local, 10:44:59 UTC → 10:30 UTC), `figuresAreRounded`
  (1 234 m → 1 200, 1 250 → 1 300, 754.6 s → 780, elapsed 20 s → 60, moving 20 s → 0),
  `aDriveUnder100mIsNotSent` (49 m → nil), `bodyHasNoStart` (encoded JSON has no `startedAt`,
  `endedAt` ends in `:00Z` with minutes in {00,15,30,45}).
  `FeedPublisherTests`: `catchUpSendsDrivesWithinSevenDays` (6 days old sent, 8 days not).
- [ ] **Step 2: Run** `task test SIM_ID=<own simulator>`; Expected: the new tests fail (compile
  error on `startedAt` / wrong values).
- [ ] **Step 3: Implement** the three helpers and use them in `body(...)`; drop `startedAt`;
  `feedWindow = 7 * 24 * 3_600`. Fix callers the compiler names (LocalFeedServer is Task 2).
- [ ] **Step 4: Run** the suite; Expected: all pass.
- [ ] **Step 5: Commit** `feat(feed): send the drive's end on a quarter hour, whole minutes and 100 m`
  (with Task 2 if the mock does not compile without it: one commit then, ledgered).

### Task 2: The mock server behaves like the backend

**Files:**
- Create: `Carodo/Core/Domain/Feed/FeedRowAsOthersSee.swift` (pure)
- Modify: `Carodo/Core/Networking/LocalFeedServer.swift`, `Carodo/Core/Outbox/LocalFeedTransport.swift` if needed
- Test: `CarodoTests/Core/Networking/LocalFeedServerTests.swift`,
  `CarodoTests/Core/Domain/Feed/FeedRowAsOthersSeeTests.swift`

**Interfaces:**
- Produces: `FeedRowAsOthersSee.item(id: UUID, drives: [DriveInputBody], displayName: String?,
  showVehicle: Bool, now: Date) -> FeedItemBody?` (`isAuthor` false, no `tripIds`, no
  reactions); `FeedRowAsOthersSee.ago(endedAt: Date, now: Date) -> String`, the backend's
  `agoLabel` (release = end + 15 min; "now" until 1 h after it, then "1h"–"23h", "1d"–"6d").
- The mock: `windowHours = 168`; a stored drive's `visibleAt = max(endedAt, floor(received)) + 15
  min`; others' pages show it from then, its author at once; refuses (400 `validation`) a body off
  the rounding, as the backend does; 204 and not stored for `endedAt` older than 7 days.

- [ ] **Step 1: Failing tests:** `agoMatchesTheBackend` (same table as carodo-app
  `test/unit/shared/coarse-time.test.ts`), `othersSeeADriveFromItsQuarter` (ended 10:30, received
  10:38: absent at 10:44:59, present at 10:45), `theAuthorSeesItAtOnce`, `offQuarterIsRefused`,
  `olderThanSevenDaysIsNotStored`.
- [ ] **Step 2: Run**; Expected: fail.
- [ ] **Step 3: Implement** the mapper (moved from the mock's inline code, not copied) and the
  mock's rules; seeded sample drives on quarters, figures rounded.
- [ ] **Step 4: Run** the suite; Expected: pass.
- [ ] **Step 5: Commit** `feat(feed): the local server releases drives at the quarter and keeps 7 days`

### Task 3: Seven days in the copy and the docs

**Files:**
- Modify: `Carodo/Resources/Localization/Feed.xcstrings` (empty state, header comments, the stats
  chip per decision 2), the view that formats the chip (found by its string key),
  `docs/specs/feed.md`, `docs/data-model.md`, `docs/operations/setup.md`
- Test: the chip's formatter in `DisplayFormatTests` or the Feed view model's tests (where it lives)

- [ ] **Step 1: Failing test** `windowChipSaysDays` (168 → "7d", 72 → "3d", 30 → "30h").
- [ ] **Step 2–4:** run (fail), implement, run (pass); EN and VI strings: "No drives in the last 7
  days" / "Chưa có chuyến nào trong 7 ngày qua".
- [ ] **Step 5: Docs:** feed.md (7 days, deletion with the window, rounding sent, author sees at
  once, others from the quarter; drop "30 days" and "finer than the hour"), data-model.md (no
  72-hour backfill), setup.md (the mock keeps 7 days, releases at the quarter).
- [ ] **Step 6:** `task test`, `task lint`, `task warnings`; screenshot of the Feed's empty state
  and header (Light/Dark, VI).
- [ ] **Step 7: Commit** `feat(feed): seven days in the feed's copy` + `docs(feed): …`.

### Task 4 (Part 3b, after the mockup): Sharing preview

**Files:**
- Create: `design/mockups/feed/sharing-preview.png` (handbook), first, for the owner;
  `Carodo/Features/Feed/Views/SharingPreview.swift`,
  `Carodo/Features/Feed/ViewModels/SharingPreviewModel.swift`
- Modify: `JoinTheFeedSheet.swift` (`ShareStep`: above the two radio cards),
  `FeedProfileSheet.swift` (under Sharing), `Feed.xcstrings` (copy above, "Example")
- Test: `CarodoTests/Features/Feed/SharingPreviewModelTests.swift`

**Interfaces:**
- Consumes: `FeedPublication.body(...)` (Task 1), `FeedRowAsOthersSee.item(...)` (Task 2),
  `FeedItemPresentation`, `FeedRow` (reactions off, no join button).
- Produces: `SharingPreviewModel(latestCarDrive:…, displayAs:, username:, showVehicle:)` →
  `FeedItemPresentation`; follows the choices live.

- [ ] **Step 1:** mockup, owner approves.
- [ ] **Step 2: Failing tests:** `previewIsTheMocksRow` (the same drive through
  `FeedPublication.body` → `FeedRowAsOthersSee.item` equals what `LocalFeedServer` returns to a
  guest), `anonymousSaysSomeone`, `usernameShowsTheName`, `vehicleOffDropsTheCar`,
  `noCarDriveShowsTheExample`, `ageSaysNow`.
- [ ] **Step 3–4:** implement, run (pass).
- [ ] **Step 5:** screenshots Light/Dark, VI, largest Dynamic Type; VoiceOver label as the Feed's.
- [ ] **Step 6: Commit** `feat(feed): see your row as others will before you share`.

## Acceptance

- Every `DriveInputBody` the app encodes passes the backend's checks (Task 1 tests use the
  contract's rules; a run against local `task app:dev` publishes a real drive: 204, row on the Feed
  at the next quarter for a guest, at once for the author).
- No exact start or end of a drive in any body the app sends (test on the encoded JSON).
- The mock's ages and release match the backend's (same table as carodo-app's unit test).
- The preview equals the mock's guest row for the same drive (Task 4).
- `task ios:test`, `task ios:lint`, `task ios:warnings` pass; screenshots as listed.

## Non-goals

- Refreshing page 1 after one's own publish (carodo-handbook TD-75): only if testing shows it.
- Live status, report and block, share links.
- Part 4 (web privacy page, `privacy.md`, App Review notes).
