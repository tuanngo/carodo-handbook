# Community access and Feed permissions — plan

Status: **approved 2026-11-12** (owner). S0 `3743f7b`, S1 `2f862a3`, S2 `23a4e00` committed; S3 done (`cfff8fd`, `f5d0c50`, `82985f8`); S4 deferred until App Review asks (owner); S5 backend next.
Source: the owner's draft "Community Access & Feed Permissions" (2026-11-12), the audit below and
the brainstorm of the same day (mockups: Settings option A, Join flow A without the Apple step).

## Why

Before the first App Store submission the Feed must meet Guideline 1.2 (user-generated content:
filter, report, block, contact, terms) and 5.1.1(v) (an account created in the app is deleted in
the app). Joining must stay one short step, and the claim screen is polished.

Feed posts are built by the backend from trip summaries. The only text a person types that others
see is the **username** and the **vehicle name** (make and model). That is the whole surface 1.2
applies to.

**No Sign in with Apple in V1 (owner, 2026-11-12).** Evaluated and dropped:

- No guideline requires it: 4.8 applies only when a third-party login (Google, Facebook) is
  offered; Carodo offers none.
- Bans already hold without it: DeviceCheck's per-device bit survives a reinstall, App Attest
  limits callers to the genuine app, and the server bans the account (ADR 0009). A ban on an Apple
  ID is easier to dodge (a new Apple ID is free) than a ban on the iPhone.
- Account deletion is required either way (claiming a username creates an account); Apple sign-in
  would only add token revocation, Apple's server notifications and a credential check at launch.
- Backup does not need it: the iCloud backup (ADR 0005) needs no Carodo account; the optional
  encrypted server backup (ADR 0011, not built) uses the same username account.
- Offline is unaffected either way (P1).

The cost accepted: someone who has iCloud Keychain off and reinstalls loses their username and
claims a new one; their drives stay on the iPhone. Recorded as debt (TD-21) for a recovery path later.

## Decisions (owner, 2026-11-12)

| ID | Decision |
|---|---|
| C1 | Local-first: recording, journal, replay, garage, passport, share card and export need no account |
| C2 | Guests read the Feed and see reactions and counts |
| C3 | **No Sign in with Apple in V1**, neither required nor optional: "Secure your profile" and the Apple link are removed |
| C4 | **Joining = claiming a username** (ADR 0008 kept): the account secret lives in iCloud Keychain |
| C5 | **Joining and sharing are separate.** A member can react without sharing drives ("Just react for now") |
| C6 | Sharing on publishes eligible car drives automatically (as today) |
| C7 | Anonymous ("Someone") / @username stays, chosen at the share step, not the claim step; default Someone |
| C8 | Show vehicle name is chosen at the share step and on the Profile page, not at claim |
| C9 | **No backfill** on Start sharing: only car drives that end after sharing turned on are published (today: the last 72 hours) |
| C10 | Five reactions, members only (unchanged) |
| C11 | Settings shows **one identity, the community profile** (mockup option A): the local driver name goes away; Passport shows @username, or "Driver" before joining |
| C12 | Join flow: **Claim → Share your drives?** (optional) |
| C13 | Vehicle name stays free text (no catalog); it is filtered instead |
| C14 | Account deletion in the app through `DELETE /v1/account` (already in the contract); never "email support to delete" |
| C15 | No public profile, follows or comments (unchanged, ADR 0007) |

Answers to the draft's open questions (from the code and ADRs today, kept):

- **D1 Feed off:** Stop sharing removes every published row (`/v1/me/sharing`, as built).
- **D2 Identity change:** display choice and vehicle visibility apply **when rows are read**, so a
  change reaches past rows too. Applying at post time would leave a username on old rows after
  switching to Someone.
- **D3 Scope:** car drives with an assigned vehicle that are not hidden (as built); no other quality gate in V1.
- **D4 Queued posts after Stop sharing:** the outbox drops them; the server refuses them anyway (`403 sharing_off`).
- **D5 Sign out:** there is none in V1; publishing is done by the device, the server never
  publishes on its own.

## Access matrix

| Feature | Guest | Member, sharing off | Member, sharing on |
|---|---|---|---|
| Record, journal, replay, garage, passport, share card, export | ✅ | ✅ | ✅ |
| Read Feed, see reactions | ✅ | ✅ | ✅ |
| React | → Join | ✅ | ✅ |
| Report a row | ✅ (hides it on this device) | ✅ | ✅ |
| Block a row's author | → Join | ✅ | ✅ |
| Hide my own row | — | — | ✅ |
| Automatic publishing | ❌ | ❌ | ✅ |
| Profile (username, show as, vehicle name, blocked, delete) | — | ✅ | ✅ |

A guest's Report is accepted (reviewers test as guests) and also hides that row on the device.
Block needs an account, because a block is stored against the reader's account.

## Audit — what exists today

- **Contract** `carodo-ios/docs/api/carodo-api.yaml` 0.27.0-draft: `/v1/accounts` claims a username
  with a guest token, takes `sharing` (claim and Start sharing are one request) and returns an
  `accountSecret` (iCloud Keychain); `/v1/auth/apple` recovers and `/v1/account/apple` links Apple
  ("Secure your profile"); `/v1/account/secret` rotates the secret (Sign out everywhere);
  `DELETE /v1/account` deletes; `/v1/feed/items/{id}/report` (reasons offensive_name, spam,
  impersonation, other; members only) and `/block-author` are defined, not built; `/v1/me/sharing`.
- **iOS:** `Features/Feed/Views/FeedIdentityView.swift` holds `JoinTheFeedSheet` (username +
  display choice + vehicle toggle + Start sharing in one sheet), `FeedSharingView` (the sharing
  page), `UsernameChangeView`, `UsernameEntry`; `FeedIdentityViewModel`, `FeedSharingActions`.
  `Core/Feed/FeedPublisher.swift`: `startSharing` and `catchUp` publish drives of the last 72 h
  (`backfillWindow`). `CommunityRepository` (`Core/Repositories/Repositories.swift:706`) has no
  report, block or delete call. `LocalCommunityRepository` + `Core/Networking/LocalFeedServer.swift`
  are the device-only mock. `Features/Authentication` (`LoginView`, `LoginViewModel`, `AuthService`,
  `AuthModels`) is an unused scaffold. `AppState.driverName` (UserDefaults) feeds Settings' top row
  (`SettingsView.accountSection`) and the Passport name (`PassportSections.displayName`).
- **Backend** `carodo-app`: scaffold only; `0001_baseline.sql` already has `reports` and `blocks`.
- **Docs:** ADR 0007 (Feed privacy; report and block required before the App Store), ADR 0008
  (join with a username; optional Apple link), ADR 0009 (App Attest, DeviceCheck bans),
  `docs/specs/feed.md`, `account.md` (deletion flow; mentions Apple token revocation and Secure
  your profile), `settings.md`. Debt: TD-8 (report/block, release blocker).

## Proposal

### 1. Identity (ADR 0008 amended)

- Joining is claiming a username; the server returns the account secret, kept as a synchronizable
  iCloud Keychain item, so a new iPhone with the same iCloud keeps the username (as decided).
- Removed: "Secure your profile", the Apple link and Apple recovery (`account.md`, ADR 0008, the
  contract). The unused `Features/Authentication` scaffold (`LoginView` and friends) is deleted.
- Bans: DeviceCheck bit + account ban + App Attest (ADR 0009, unchanged).
- `/v1/accounts` no longer requires `sharing`: claiming makes a member with sharing off; Start
  sharing is the separate `PUT /v1/me/sharing`.

### 2. Join flow

Opened from the Feed avatar, ☺︎ on a row, the invite, "Share to Feed?" on a drive summary and
Settings → Set up your profile.

1. **Claim:** left-aligned title in two tones ("Claim your name. / Make it yours."), two lines of
   description, the field with a fixed `@` prefix and the status icon **inside** the field
   (✓ green, ! when taken), one status line under it ("@tuanngo is free."), suggestion chips only
   when the name is taken or reserved, **Claim @name**, Not now. One line under the button: "By
   claiming you agree to the Terms of Use" (link). The field opens with a free suggestion.
2. **Share your drives?** (optional): two radio cards, **As Someone** (default) / **As @name**,
   Show vehicle name, **Start sharing** / **Just react for now**. Opened from a drive summary,
   Start sharing also publishes that drive (the person asked for it); nothing else from before.

Closing after step 1 leaves a member with sharing off. For a member with sharing off, every entry
that opened Join (invite row, "Share to Feed?") opens step 2 directly.

### 3. Settings and Passport (mockup option A)

- Settings' top row: guest → avatar placeholder + **Set up your profile** (opens Join); member →
  avatar + **@username**, subtitle "Profile · Feed sharing on/off" (opens Profile).
- The local driver name is removed (`AppState.driverName`, its key, its catalog strings, the
  Settings text field). Passport shows @username, or "Driver" before joining. Avatars use the
  username's initial, or a neutral placeholder.

### 4. Profile page (replaces `FeedSharingView`)

Reached from Settings' top row and the Feed avatar. A settings list:
Username (→ change page: same field with the icon inside, "You can change it 3 times in 30 days", Save) ·
**Feed:** Share my drives, Show as (Someone / @name), Show vehicle name, the line "Others see your
car, time and distance. Never your route or places." · Blocked drivers (count → Unblock all) ·
Delete account (owner 2026-11-12: support stays Settings → Send Feedback; the Terms of Use move to Settings → About).
Turning sharing off still asks "Stop sharing?" and removes every row.

**Delete account** (`account.md`, unchanged except the Apple step): offer Export → what is lost
(username, Feed rows, reactions, share links; drives on the iPhone and the iCloud backup stay) →
confirm → `DELETE /v1/account` → the secret is removed from iCloud Keychain and the app is a guest.
Without network it waits and says so; nothing reads as deleted before the server confirms.

### 5. Report and block (TD-8)

- **Entry, with no new mark on the row** (the owner wants the Feed no busier): the
  row's long-press menu (**Report**, and for members **Block this driver**; own rows keep **Hide
  from feed**), and a quiet **Report** link at the foot of the ☺︎ reaction picker, which every row
  already has, so App Review finds it without knowing to long-press.
- **Report sheet:** one short list of reasons: Offensive name · Offensive vehicle name · Spam ·
  Pretending to be someone · Something else (optional note, 500 characters). Sending hides the row
  on this device at once and says "Thanks. We'll review it within 24 hours."
- **Block:** a confirmation ("You won't see this driver's drives again. They won't know."), then
  every row of that author disappears for this reader. No identity is shown or stored on the
  device; **Unblock all** in Profile clears the list (the server keeps blocks by author, never sends them).
- **Server moderation (carodo-app):** a row reported by 3 different readers is hidden for everyone
  until reviewed; the owner reviews the queue within 24 hours (a small script or `wrangler d1` task
  to list, hide, rename a username, ban). Vehicle names and usernames pass the same VI + EN
  profanity filter at publish and at claim; a vehicle name that fails is dropped from the row, not
  refused (the drive still publishes).
- **Terms of Use and contact** (owner 2026-11-12: one Terms of Use page holds the community rules; no separate Community Guidelines page): one short page (zero tolerance for offensive names,
  impersonation, spam; how to report; contact address), served by carodo-web and linked from the
  Claim screen, Profile and the report sheet.

### 6. Contract changes (P6, owner approval) — 0.28.0-draft

- `POST /v1/accounts`: `sharing` optional (claim without sharing; default off).
- Remove `/v1/auth/apple`, `/v1/account/apple` and the `AppleCredential` schema; `DELETE /v1/account`
  loses its Apple sentence.
- `POST /v1/feed/items/{id}/report`: also accepts the guest token (rate limited per App Attest key);
  reason `offensive_vehicle` added.
- `GET /v1/me/blocks` → `{ count }`, `DELETE /v1/me/blocks` (unblock all).
- Remove `/v1/account/secret` (no Sign out everywhere in V1).
- No new entitlement, dependency or service.

## Slices (each one reviewable)

| # | Slice | Repo | Notes |
|---|---|---|---|
| S0 | Docs and contract: ADR 0008 amended (no Apple, join ≠ share), ADR 0007 note (no backfill), `feed.md`, `account.md`, `settings.md`, `passport.md`, contract 0.28.0; TD-21 recorded | carodo-ios, handbook | Owner approves the contract before S2 |
| S1 | Settings + Passport one identity: remove `driverName`, top row "Set up your profile" / @username, Passport name | carodo-ios | Local only |
| S2 | Join flow on the local mock: Claim screen polish, Share step; `FeedPublisher` without the 72 h backfill (`startSharing` and `catchUp` only for drives ending after sharing turned on); remove `Features/Authentication` | carodo-ios | done `23a4e00` |
| S3 | Profile replacing `FeedSharingView`. Owner 2026-11-12: Edit profile is a fitted, flat sheet (no cards) from Settings and the avatar; the username is edited in the sheet (Save @name); how others see you stays two radio cards (owner: clearer than a switch); the Settings Privacy → Feed sharing row is removed. Then Blocked drivers, Guidelines, Support, Delete account against the mock | carodo-ios | sheet `cfff8fd`, field `f5d0c50`; Delete account + Terms of Use in About `82985f8` (support stays Send Feedback); Blocked drivers moves to S4; S3 done |
| S4 | Report and block: row menu, report sheet, local hide, block + Unblock all; `CommunityRepository` `report`/`block`/`blocks`/`deleteAccount`; mock server stores them | carodo-ios | **Deferred** (owner, 2026-11-12): built only if App Review asks; designed and in the contract (TD-8) |
| S5 | Backend: accounts (claim with sharing off), rename, `DELETE /v1/account` with the 90-day name hold, vehicle-name and username profanity filter, the Terms of Use page; report/block routes, threshold auto-hide and the moderation script last (deferred in the app) | carodo-app | Its own plan in carodo-app; contract 0.28.1-draft (`3516b7c`) |

Each iOS slice: tests (view models, publisher no-backfill on both sides of the sharing moment,
report hides locally, block filters every row of an author, delete leaves the journal untouched),
strings EN + VI, screenshots Light, Dark, large Dynamic Type, Vietnamese.

Before submission, outside these slices: privacy policy URL and the App Privacy label (username,
identifiers), already listed in the release-readiness follow-ups.

## Handoff to carodo-app (2026-11-12)

The iOS side of S0–S3 is built on the local mock; S4 is deferred (owner: only if App Review asks).
The session that builds S5 starts from contract **0.28.1-draft** (carodo-ios `3516b7c`, its
version note lists what the app calls) and carodo-ios ADR 0007 and 0008. Found in carodo-web's
uncommitted pages (`apps/web/src/pages/`, another session's work), to fix there:

1. **One name for the terms.** The app links "Terms of Use" (Claim, Settings → About) to
   `carodo.app/terms`; the page is titled "Terms of Service". Rename the page (and the footer
   links) to Terms of Use.
2. **The community rules Guideline 1.2 needs.** The terms must say plainly that there is no
   tolerance for objectionable content or abusive users (offensive usernames or vehicle names,
   impersonation, harassment, spam), how to report (support@carodo.app), and that breaking them
   hides the content or suspends the account. Today only "harass, threaten, or abuse" appears
   under Acceptable use.
3. **Privacy page out of date.** It still mentions Sign in with Apple, an optional display name and
   live status; none exist (ADR 0008: a username only, no sign-in; no Live in Feed V1). It should
   also say what deletion does as built: rows and reactions gone at once, everything within 30
   days, the username held 90 days as a hash.

## Acceptance

- A guest records, replays, exports and reads the Feed with no prompt to join.
- Claiming a username asks for nothing else (no Apple, no email); closing after the claim leaves a
  member with sharing off who can react; nothing is published.
- Start sharing publishes no drive that ended before it (except the drive whose summary opened Join).
- Switching to Someone removes the username from the person's past rows.
- A guest can report a row; the row disappears on that device at once.
- A blocked author's rows never appear again for that reader; Unblock all brings them back.
- Settings never shows a name field; Passport shows @username or "Driver".
- Delete account works from the app alone, leaves every drive on the iPhone, and afterwards the
  Feed no longer shows the account.

## Non-goals

Sign in with Apple or any other sign-in, account recovery without iCloud Keychain (TD-21),
comments, follows, public profiles, a vehicle catalog, publishing older drives, an in-app
moderation dashboard.

## From the brainstorm (2026-11-12)

- **Report stays** (Guideline 1.2 names it; owner asked to keep the Feed clean); placed without a new mark on the row (section 5).
- **The terms line on the Claim screen stays**, one line: App Review asks user-generated-content
  apps for an agreement to terms with no tolerance for objectionable content.
- **Contact (owner):** support@carodo.app.
- **No public profile in V1** (ADR 0007 unchanged): a profile would gather one person's drives,
  times and car on one page, a pattern of their life; anonymous rows must stay unlinkable; it adds
  text to moderate. Kept in the roadmap as a later idea.

## Owner answers (2026-11-12)

1. **No Sign out and no Sign out everywhere in V1** (the secret syncs back through iCloud
   Keychain); `/v1/account/secret` removed.
2. **Auto-hide at 3 distinct reports.**
3. The terms line on Claim stays; no public profile in V1 (both confirmed).
