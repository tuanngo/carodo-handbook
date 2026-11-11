# Feed V1 · Part 5 — the Feed screen, joining and sharing · Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** The Feed screen, the Join the Feed sheet, the Feed sharing page and the entry points look
and behave as `feed-v1-design.md` decided, on the local feed server from Part 4.

**Architecture:** Domain first (items carry `isAuthor`, reactions, the community pulse), then the
shape background view, then the screen, then joining/sharing and the entry points. UI is a matter
of taste: it is left uncommitted for the owner's review (AGENTS.md, Git), with screenshots.

**Spec:** `carodo-handbook/plans/feed-v1-design.md` (Feed screen, Joining, Feed sharing page,
Settings, End of a car drive); `carodo-ios/docs/specs/feed.md`; mockups in `.superpowers/brainstorm/`.

## Global Constraints

- Copy in the String Catalogs, English and Vietnamese, comments on every key; the owner reviews it.
- Light, Dark, a large Dynamic Type size and Vietnamese screenshots before handing over.
- No time finer than the hour on screen; no number below 10 drivers; Copper only for "You".
- Reactions: members only; a guest's ☺︎ opens Join the Feed.
- `task lint`, `task warnings`, `task test` pass.

## Review Focus

1. Below 10 drivers the header shows no number, no pill (test on the view model's pulse).
2. A failed first load shows no header (no stats from a failed read).
3. The invite row never shows without a car drive, nor while sharing, nor within 7 days of Not now.
4. A guest tapping ☺︎ never sends a reaction.
5. Start sharing with a new username claims it first; a taken name keeps the sheet open with the reason.

---

### Task 1: Domain — pulse, author, reactions

**Files:** `Core/Domain/Community.swift` (`Reaction` enum fire/coffee/moon/rain/party with emoji;
`FeedItem.isAuthor`, `reactions: [Reaction: Int]`, `myReaction: Reaction?`;
`enum CommunityPulse { case numbers(drivers:distanceM:durationS:busiestHour:), warmingUp(Double) }`;
`FeedPage.pulse: CommunityPulse?` replacing `stats`), `Core/Repositories/Repositories.swift`
(`CommunityRepository`: `func react(_ reaction: Reaction?, item: UUID) async throws`,
`func sharing() async throws -> SharingBody?`), `LocalFeedServer` (reactions per item for the
reader: `react(itemID:reaction:)`, counts in `FeedItemBody.reactions`), `LocalCommunityRepository`,
`SampleCommunityRepository`, `FakeCommunityRepository`, `FeedViewModel` (pulse, `react`).
Tests: `LocalFeedServerTests` (`testAReactionCountsOncePerReader`, `testReactingAgainRemovesIt`),
`LocalCommunityRepositoryTests` (pulse below and above 10), `FeedViewModelTests` (react updates
the item optimistically and rolls back on failure).

### Task 2: The shape background

**Files:** Create `DesignSystem/Components/FeedShapeBackground.swift`; replace `DriveShapeThumbnail`'s
use on Feed rows. Catmull-Rom through the points sampled densely; per segment width 1.3→3.0 pt
(core) and opacity faded over the first and last 22 %; under it a halo in the row's background
(4→7 pt) and a ribbon (6→11 pt at 12 %) masked by a horizontal gradient (clear at 25 %, full at
60 % of the width). Colour Stone (`CarodoSurface.textSecondary`) or Copper (`CarodoSurface.accent`)
for the reader's own. Drawn with `Canvas`, static. Test: `FeedShapeBackgroundTests` — the sampled
curve passes through every input point; the fade is 0 at both ends and 1 in the middle.

### Task 3: The Feed screen

**Files:** `Features/Feed/Views/FeedView.swift` (split: `FeedPulseHeader.swift`, `FeedRow.swift`,
`FeedReactions.swift`, `FeedInvite.swift`), `FeedViewModel`, `FeedItemPresentation`, catalogs.
- Header: numbers mode (72h pill, "N drivers", "km · h · Busiest 7–8 AM"); warm-up mode (one line
  "You're among the first drivers", "driving together around the world", road dashes of fixed
  length across the width, filled to `warmup` rounded to whole dashes); none on failure.
- The reader's newest row pinned under the header on a pale Copper tint, named "You".
- Invite (not sharing, a car drive in the journal, not snoozed): "Your <part of day> drive could
  be here", its figures, "Join the Feed" · "Not now" (snooze 7 days, UserDefaults).
- Rows: one per item; a multi-drive item lists its 3 longest ("2.2 km · 8 min · 8h ago") then
  "+N more" (expands); totals as chips; the shape as the row's background; reactions (received
  with counts, ☺︎ opens the picker; a guest's opens Join); own row long-press → Hide from feed.
- Empty: header kept, faint dashed line, "No drives in the last 72 hours" + line. Failed: no header.

### Task 4: Join, sharing page, entry points

**Files:** Create `Features/Feed/Views/JoinTheFeedSheet.swift` (replaces `JoinFeedSheet` and the
claim part of `FeedIdentityView`), `Features/Feed/Views/FeedSharingView.swift`,
`DesignSystem/Components/RadioCard.swift`; modify `FeedIdentityViewModel` →
`FeedSharingModel` (claim, choices, start/stop through `FeedPublisher`), `SettingsView`
(driver card without heading; Privacy → Feed sharing row with its value), `AppRoute.feedIdentity`
→ `.feedSharing`, `JourneySummarySheet` ("Share to Feed?" / "Shared to Feed · Hide" for car
drives), journey detail (switch "On the Feed" for car drives). Tests: `FeedSharingModelTests`
(claim then start; taken name keeps the reason; stop keeps the username), `RadioCard` accessibility
trait in a view test if feasible.

### Task 5: Evidence and hand-over

- [ ] `task format`, `task lint`, `task warnings`, `task test`.
- [ ] Screenshots on a separate simulator: numbers / warm-up / empty / failed / invite / Join sheet /
  sharing page, Light + Dark + AX-L + Vietnamese.
- [ ] Leave uncommitted, report "waiting for the owner's review".
