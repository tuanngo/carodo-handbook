# Feed V1 · Part 2 — delete the deferred Feed UI · Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Live, Following, the leaderboard, Profiles and the Nearby scope leave the iOS app with
their strings, tests and docs; the M1 Global feed and the Feed identity keep working unchanged.

**Architecture:** Pure removal, outside in: screens and routes first, then the repository
methods and domain types only they used, then strings, tests and docs. Nothing is replaced here;
Part 5 rebuilds the Feed screen on contract 0.27.

**Tech Stack:** Swift 6, SwiftUI, XCTest, String Catalogs, XcodeGen.

**Spec:** `carodo-handbook/plans/feed-v1-design.md` (Delete, Phase 2) and
`carodo-ios/docs/specs/feed.md` (Today: "Built, to be deleted").

## Global Constraints

- Delete, don't hide: no `#if`, no flag, no commented-out code left (AGENTS.md self-review).
- A removed feature takes what only it used: a type, a property, a catalog string, a doc row,
  a QA launch argument.
- Keep, untouched in behaviour: `FeedView`'s Global list (paging, refresh, states, stats strip
  without the trophy), `FeedIdentityView` / `JoinFeedSheet`, `FeedItemRow`, `DriveShapeThumbnail`,
  `DriverAvatar`, `StampRing`, `AppState.isFeedMember` (the guest card still reads it until Part 5).
- Another session edits Places files in this tree: stage only this plan's paths; the String
  Catalogs and `MainTabView.swift` are shared, stage them by hunk if they carry foreign changes.
- `task lint`, `task warnings`, `task test` pass before the commit; screenshots of the Feed tab
  (Light, Dark, large Dynamic Type, Vietnamese) prove nothing visible changed for a guest.
- P8: no AI attribution.

## Review Focus

1. **A string key still used** after its feature is gone, or a **key left without a user**:
   the catalog keeps dead copy, or the build breaks on a removed generated symbol. Task 3 Step 2
   greps every removed key's symbol.
2. **The Feed's first page shape:** `FeedPage` loses `live`; the sample repository and the fake
   must still answer pages with the same items, stats and cursors (`FeedViewModelTests` unchanged).
3. **Deep links and routes:** `AppRoute` loses `.profile`; `AppRouteTests` and any persisted
   navigation must not decode an old value. Task 1 runs `AppRouteTests`.
4. **The avatar on the Feed** must still open the Feed identity for everyone (it opened your
   Profile only behind the flag). Screenshot in Task 4.
5. **Unused code after removal** (`PublicDriver.id` used only for links, `SampleData.driverID(at:)`,
   `DebugLaunchArguments.profile`): `task warnings` does not flag unused internals, so Task 2 Step 3
   greps each.

---

### Task 1: Screens and routes

**Files:**
- Delete: `Carodo/Features/Feed/Views/LeaderboardView.swift`, `Carodo/Features/Profile/` (both files), `Carodo/Features/Feed/FeedFeatures.swift`
- Modify: `Carodo/Features/Feed/Views/FeedView.swift` (Live rows, `FollowingStrip`, the Discover · Following picker, the trophy, the leaderboard sheet and its QA hook, profile links), `Carodo/Features/Feed/ViewModels/FeedViewModel.swift` (`tab`, `live`, `following`, `LeaderboardViewModel`), `Carodo/DesignSystem/Components/JourneyComponents.swift:170-180` (`ProfileToolbarItem` always opens the identity), `Carodo/App/AppRoute.swift` (`.profile`), `Carodo/App/MainTabView.swift` (`.profile` destination, `-carodo.debugOpenProfile`), `Carodo/Features/Developer/DebugLaunchArguments.swift` (`profile`)
- Delete tests: `CarodoTests/LeaderboardViewModelTests.swift`, `CarodoTests/ProfileViewModelTests.swift`
- Modify tests: `CarodoTests/AppRouteTests.swift` (drop `.profile` cases)

- [ ] **Step 1:** Make the edits. `FeedView` keeps one list: stats strip (`opensLeaderboard` removed), guest card, items, paging footer. `StatsStrip` loses its trophy branch.
- [ ] **Step 2:** `xcodegen generate` then `task build`. Expected: build succeeds (errors only in Core/Repositories if Task 2 types are still referenced — none expected here).
- [ ] **Step 3:** `task test` filtered: `xcodebuild test … -only-testing:CarodoTests/AppRouteTests -only-testing:CarodoTests/FeedViewModelTests`. Expected: pass.

### Task 2: Repository and domain

**Files:**
- Modify: `Carodo/Core/Repositories/Repositories.swift:694-720` (`CommunityRepository`: drop `following()`, `leaderboard(…)`, `profile(_:)`, `setFollowing(_:driver:)`; `feed(scope:cursor:)` → `feed(cursor:)`) and `SampleCommunityRepository`
- Modify: `Carodo/Core/Domain/Community.swift` (delete `FeedScope`, `LiveDriver`, `FeedTab`, `FollowedDriver`, `FollowingFeed`, `LeaderboardPeriod`, `LeaderboardMetric`, `LeaderboardEntry`, `LeaderboardBoard`, `ProfileSubject`, `PublicProfile`; `FeedPage.live` removed; `CommunityStats` loses its scope if it has one)
- Modify: `Carodo/Core/PreviewData/SampleData.swift` (sample live drivers, following, boards, profiles, `driverID(at:)`)
- Modify tests: `CarodoTests/FakeCommunityRepository.swift`, `CarodoTests/SampleDataTests.swift`, `CarodoTests/FeedViewModelTests.swift` (only call sites of `feed(scope:)`)

**Interfaces:**
- Produces: `func feed(cursor: FeedCursor?) async throws -> FeedPage`; `FeedPage(stats:items:nextCursor:hasMore:)`.

- [ ] **Step 1:** Make the edits.
- [ ] **Step 2:** `task build` then `task test`. Expected: all pass; test count drops only by the two deleted files.
- [ ] **Step 3:** `grep -rnE "FeedScope|LiveDriver|FeedTab|Following|Leaderboard|ProfileSubject|PublicProfile|driverID\(at|debugOpenProfile|debugOpenLeaderboard|debugFeedDeferred|deferredUI" Carodo CarodoTests` → no hit. `PublicDriver.id`: keep only if a remaining reader uses it; else remove.

### Task 3: Strings

**Files:**
- Modify: `Carodo/Resources/Localization/Feed.xcstrings`, `Common.xcstrings` (keys only the removed screens used: `feed.tab*`, `feed.live*`, `feed.following*`, `feed.leaderboard*`, `feed.trophy*`, `profile.*`, `common.scope*`, `common.profileLabel` if unused, …)

- [ ] **Step 1:** For each key in both catalogs, derive its generated symbol (`.Feed.liveBadge` for `feed.live.badge`, …) and list keys whose symbol has no use left in `Carodo/`. Remove those keys (JSON edit, keep the file's format).
- [ ] **Step 2:** `task build` and `task test` (`LocalizationTests` included). Expected: pass; then re-run the Step 1 scan → zero unused keys in the two catalogs (pre-existing unused keys outside these features are named in the report, not removed).

### Task 4: Docs, checks, evidence, commit

**Files:**
- Delete: `docs/specs/profile.md`
- Modify: `docs/specs/feed.md` (Today: the deferred UI is deleted), `docs/specs/README.md` (drop the profile row), `docs/operations/setup.md` (drop `-carodo.debugFeedDeferred`, `-carodo.debugOpenLeaderboard`, `-carodo.debugOpenProfile`; `-carodo.feedMember` describes the guest card only), `docs/design-system.md` (Discover / Following picker line, Leaderboard layout note, `ProfileToolbarItem` row), `docs/architecture.md:34`, `AGENTS.md` (Features list without Profile)

- [ ] **Step 1:** Edit the docs.
- [ ] **Step 2:** `task format`, `task lint`, `task warnings`, `task test`. Expected: lint clean, 0 warnings, all tests pass.
- [ ] **Step 3:** Screenshots on the simulator (by UDID): Feed tab as a guest with `-carodo.sampleData YES`, Light, Dark, `-UIPreferredContentSizeCategoryName UICTContentSizeCategoryAccessibilityL`, `-AppleLanguages "(vi)"`; the avatar opens the Feed identity.
- [ ] **Step 4:** Stage this plan's paths only, `git diff --cached --stat`, commit `refactor(feed): remove live, following, leaderboard and profiles deferred after v1`.
