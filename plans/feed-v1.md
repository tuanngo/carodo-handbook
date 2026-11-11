# Feed V1 — M1 implementation plan (read-only Feed + Feed identity, mock-backed)

Status: **built 2026-11-10** on carodo-ios branch `feat/feed-v1` (worktree `../carodo-ios-feed-v1`, cut
from `72f50ea`): commit `ae871a5` (Tasks 1–6, the Global feed on the paged mock) and `4873dc1` (Tasks 7–8,
the Feed identity). Full suite, `task lint` and `task warnings` green; screenshots Light/Dark/VI/AX
reviewed by the agent, the owner's copy review pending; merged into `main` and pushed (polish since: `29c4ad3`, `e4eea4e`). What it left open:
`technical-debt.md` TD-8, TD-9, TD-10. Decisions come from the M0 proposal reviewed the same day;
what M0 decided for the publishing phase but M1 does not apply is in section 9.

**Goal:** the Feed tab reads a paged Global Feed from a contract-shaped mock, shows anonymous
("Someone") and named items with a drive shape drawn as a SwiftUI `Path`, and a Feed identity
screen lets the person claim a username; everything behind `CommunityRepository`, replaceable by
`BackendService` later (handbook `plans/ios-backend-integration.md`).

**Architecture:** domain types follow `docs/api/carodo-api.yaml` 0.26.0-draft (`Ago`, `DriveShape`,
nullable `FeedItem.user`); `CommunityRepository.feed(scope:cursor:)` pages with an opaque cursor;
`FeedViewModel` copies the `JourneysViewModel` paging pattern; a `FeedItemPresentation` value is
the only thing the row renders; deferred features (Live, Following, Leaderboard, Profile) stay
compiled behind `FeedFeatures.deferredUI`, reachable only with a DEBUG launch argument.

**Spec:** `carodo-ios/docs/specs/feed.md`, `navigation.md`, `settings.md`, ADR 0007, 0008, 0009;
contract `carodo-ios/docs/api/carodo-api.yaml`.

## Global constraints

- iOS 18+, Swift 6 approachable concurrency: no `@MainActor` on views/view models; `nonisolated`
  on domain values, formatting, repository protocols and `Shape`s (`carodo-ios/AGENTS.md`).
- Every user-facing line in a String Catalog (EN + VI, translator comment); no `Text("literal")`.
- No coordinates, routes, places or exact times in Feed models or fixtures (P5, P9). Shapes in
  sample data are synthetic integer arrays, never derived from a real drive.
- No change to `AppState.swift`, the recording pipeline, the schema or the outbox in M1.
- Stage only this work's paths; `git add -p` for `MainTabView.swift` (another session edits it).
- Commit messages: lowercase conventional, no AI attribution (P8).
- Owner reviews the Vietnamese copy and the screenshots before each commit lands (UI copy is
  product). Decided copy: anonymous name **"Someone" / "Ai đó"**; the headline is a sentence
  "Completed a morning drive" / "Đã hoàn thành chuyến buổi sáng" (owner, 2026-11-10; `feed.md`'s
  "no sentence" rule is replaced in the same change).

## Review focus

1. Refresh while a page is loading: the stale page must not be appended to the new list.
2. A page with zero items and `hasMore == true`: the view model stops after one try, no loop.
3. A pasted username with Vietnamese diacritics or spaces is refused with a reason and never
   sent to the availability check.
4. A shape whose points coincide or are collinear draws without dividing by zero.
5. An item with no drives and no milestone (damaged data) is dropped, never rendered as "0 drives".

## Contract delta applied by M1 (0.25.0 → 0.26.0-draft, owner-approved 2026-11-10)

- `FeedItem.user`: `oneOf [PublicUser, null]`; null = anonymous; never a stable or derivable owner id.
- `FeedItem.id`: opaque, random per item, never derived from the account id.
- `FeedDrive`: `ago` and `partOfDay` become required.

---

### Task 1: Domain types from the contract

**Files:** modify `Carodo/Core/Domain/Community.swift`; create `Carodo/Core/Domain/DriveShape.swift`,
`Carodo/Core/Domain/Username.swift`; modify `Carodo/Core/Formatting/DisplayFormat.swift`,
`Carodo/Resources/Localization/Common.xcstrings`; tests `CarodoTests/AgoTests.swift`,
`CarodoTests/DriveShapeTests.swift`, `CarodoTests/UsernameTests.swift`, update `SampleDataTests`.

**Produces:**
- `nonisolated enum Ago: Hashable, Sendable { case now, hours(Int), days(Int), weeks(Int), months(Int), years(Int) }`
  with `init?(rawValue: String)` and `var rawValue: String` (pattern `^(now|[1-9][0-9]?(h|d|w|mo|y))$`).
- `nonisolated struct DriveShape: Hashable, Sendable { let points: [SIMD2<Int>]; init?(points:) }`
  (2…24 points, each 0…1000).
- `nonisolated struct Username: Hashable, Sendable { let value: String; init?(_ text: String) }`
  (lowercased, `^[a-z0-9_.]{3,20}$`) and `enum UsernameProblem { tooShort, tooLong, invalidCharacter }`
  via `static func problem(in text: String) -> UsernameProblem?`.
- `PublicDriver` gains `let username: String`; `FeedItem.driver` becomes `PublicDriver?`;
  `FeedDrive` gains `partOfDay: PartOfDay`, `shape: DriveShape?`; `ageS` fields become `ago: Ago`.
- `FeedCursor { let token: String }`, `FeedPage { live, stats: CommunityStats?, items, nextCursor: FeedCursor?, hasMore }`
  replaces `CommunityFeed`.
- `FeedIdentity { let username: Username? }`, `UsernameAvailability { available, taken(suggestions: [Username]), reserved, invalid }`.
- `DisplayFormat.ago(_:) -> String` (keys `Common.age.now/hours/days/weeks/months/years`; `age.minutes` removed),
  `DisplayFormat.title(partOfDay:)` that `title(startedAt:)` calls.

Tests: `AgoTests` (accepts now, 1h, 23h, 6d, 4w, 11mo, 1y; rejects 15m, 0h, h, 100h, empty),
`DriveShapeTests` (2 and 24 accepted, 1 and 25 rejected, -1 and 1001 rejected),
`UsernameTests` ("ab" tooShort, "abc" ok, 20 chars ok, 21 tooLong, "Minh" → "minh",
"mi nh" / "minh!" / "mính" invalidCharacter).

### Task 2: Paged repository and the contract-shaped mock

**Files:** modify `Carodo/Core/Repositories/Repositories.swift`, `Carodo/Core/PreviewData/SampleData.swift`;
test `CarodoTests/SampleCommunityRepositoryTests.swift`.

**Produces:** `CommunityRepository.feed(scope:cursor:) -> FeedPage`, `identity() -> FeedIdentity?`,
`usernameAvailability(_:) -> UsernameAvailability`, `claimUsername(_:) -> FeedIdentity`;
`stats(scope:)` removed (first page carries stats). `SampleCommunityRepository` becomes a
`final class` with `Behaviour { pageSize = 10, latency: Duration? = nil, failure: FailurePlan = .never }`,
`enum FailurePlan { never, firstPage, page(Int), everyOther }`, identity kept in memory only.
`SampleData.feedItems(now:)` (~28 grouped items, anonymous and named, synthetic shapes, rising `ago`)
and `SampleData.feedPage(items:cursor:pageSize:)` (cursor token `s:<index>`).

Tests: first page has stats and live, later pages do not; `hasMore` false only on the last page;
a returned cursor is always accepted; `.firstPage` throws once; `.page(2)` throws only there;
`claimUsername` then `identity()` returns the username; a sample name is `.taken`.

### Task 3: FeedViewModel paging and states

**Files:** modify `Carodo/Features/Feed/ViewModels/FeedViewModel.swift`; create
`CarodoTests/FeedViewModelTests.swift`, `CarodoTests/FakeCommunityRepository.swift` (shared fake,
replaces the private fakes in `ProfileViewModelTests`).

**Produces:** `state`, `items`, `stats`, `hasMore`, `isLoadingMore`, `pageFailed`, `refreshFailed`,
`prefetchItemID`, `itemAppeared(_:)`, `loadMore()`, `retryPage()`, `refresh()`, generation counter.

Tests: first page → `.loaded` with stats; `loadMore` appends and stops at `hasMore == false`;
`prefetchItemID` is the `prefetchDistance`th item from the end; page 2 failure keeps items and
sets `pageFailed`; `retryPage` recovers; refresh failure with items keeps them and sets
`refreshFailed`; a stale answer (refresh during loadMore) is dropped; an empty page with
`hasMore == true` stops.

### Task 4: FeedItemPresentation

**Files:** create `Carodo/Features/Feed/ViewModels/FeedItemPresentation.swift`; modify
`Carodo/Resources/Localization/Feed.xcstrings`; test `CarodoTests/FeedItemPresentationTests.swift`.

**Produces:** `nonisolated struct FeedItemPresentation` with `init?(item: FeedItem, unit: DistanceUnit)`
(nil when no drives and no milestone), `name`, `isAnonymous`, `headline: LocalizedStringResource`
("Completed a morning drive" per part of day; "Completed 3 drives" for a group), `dataLine`,
`ago`, `tags` (night hidden under a night headline), `shape` (longest drive's), `accessibilityLabel`.

### Task 5: Shape rendering

**Files:** modify `Carodo/DesignSystem/Components/RouteViews.swift`; test `CarodoTests/RouteShapeTests.swift`.

**Produces:** `RouteShape.init(shape: DriveShape)` (one fit for projected points),
`DriveShapeThumbnail` (static, 56 pt, copper, round joins, `accessibilityHidden`).

Tests: bounding rect inside the rect, aspect preserved (1000×500 → ~100×50), coincident points
do not crash.

### Task 6: FeedView V1, gate, launch arguments, docs, commit 1

**Files:** create `Carodo/Features/Feed/FeedFeatures.swift`; modify `FeedView.swift`,
`ProfileView.swift`, `LeaderboardView.swift` (compile only), `JourneyComponents.swift`
(`DriverAvatar.isAnonymous`), `docs/specs/feed.md`, `docs/operations/setup.md`,
`docs/architecture.md`, `docs/api/carodo-api.yaml`, `docs/copy-and-localization.md`, ADR 0007.

Launch arguments: `-carodo.debugFeedFailure first|page:N`, `-carodo.debugFeedEmpty YES`,
`-carodo.debugFeedDeferred YES`. States: loading, loaded, empty, failed + Retry, loading more,
page failed + Retry, refresh failed banner, end of feed. Screenshots Light/Dark, AX size, Vietnamese.

Commit: `feat(feed): global feed v1 on paged mock with anonymous items and drive shapes`.

### Task 7: FeedIdentityViewModel

**Files:** create `Carodo/Features/Feed/ViewModels/FeedIdentityViewModel.swift`; test
`CarodoTests/FeedIdentityViewModelTests.swift`.

**Produces:** `Phase { loading, guest, checking, available, unavailable(UsernameAvailability), claiming, claimed(FeedIdentity), failed }`,
`draft` (lowercased as typed), `problem`, `checkAvailability()`, `claim()`.

Tests: loads guest; "ab" → tooShort without a repository call; "minh" → checking → available;
taken → unavailable with suggestions; claim → claimed; claim failure → failed, draft kept;
a stale availability answer is dropped when the draft changed.

### Task 8: FeedIdentityView, route, Settings row, avatar, banner, docs, commit 2

**Files:** create `Carodo/Features/Feed/Views/FeedIdentityView.swift`; modify `AppRoute.swift`
(`.feedIdentity`, hides the bar), `MainTabView.swift` (destination), `JourneyComponents.swift`
(`OwnAvatarButton` → route), `FeedView.swift` (`GuestBanner` link), `SettingsView.swift`
("Account & Feed" + row), `Settings.xcstrings`, `Feed.xcstrings`; `docs/specs/navigation.md`,
`settings.md`, `profile.md`; `AppRouteTests`.

Commit: `feat(feed): feed identity screen with username claim, reached from the feed avatar and settings`.

## 9. Decided at M0, applied with publishing (not in M1)

`ProfileInput.username` nullable; `showUsername` / `showVehicle` server-side flags (default false);
`POST /v1/accounts` without a username (anonymous account, secret in iCloud Keychain); ADR 0008
and ADR 0007 "Opt-in" paragraph; `sync.md` Local columns (`publish_to_feed`, `published_at`,
`published_revision`, `shape_seed`), `FeedPublisher` reconciler after `onSettled`; shape builder
(distance trim, redaction longest piece, ≤24 points, stable seed). Deferred without effect on the
Feed UI: ETag/304 and offline cache, `hour_full`, region/area, badges, headline variety and long
form, Catmull-Rom smoothing, Report/Block (gate before public release).
