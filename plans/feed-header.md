# The Feed's header

Status: **Part 1 built 2026-11-14 (`864cb95`): the bar only.** The owner split the work: the bar
first, the body (subtitle, pulse line, decisions 3 and 4 below) after a review. Built: the road
symbol (`road.lanes`, the owner's pick over the proposed `person.2.fill` and a globe; it also stands
for GPS distance elsewhere, noted to the owner) and "Feed" in title 2 bold at the leading edge,
through one `TabTitleToolbarItem` shared with the Passport; the avatar at the trailing edge (as
decision 2: a guest keeps the person-symbol avatar). The tab icons stay as they are (owner): the
Passport tab `seal.fill` beside the stamp in its bar, the Feed tab `person.2.fill` beside the road.
**Part 2, the body: waiting for the owner's review.**
Mockup: [`design/mockups/passport/passport-feed-headers.png`](../design/mockups/passport/passport-feed-headers.png),
Round 2, frames F1 (member) and F2 (guest, quiet). Follows [`passport-tab-and-header.md`](passport-tab-and-header.md):
the Passport's bar as built is the grammar this plan copies.

## Outcome

The Feed opens like the Passport: its title in the bar, which stays put while the page scrolls
(the owner's correction on the Passport, 2026-11-14), then a short line that says what the page
is, then the community's pulse as one quiet line instead of a second large title. One commit.

## Owner decisions already taken (2026-11-14)

- The title stays **Feed** ("Bảng tin"), large and on the left, not centred.
- Subtitle "The journeys we share."
- The identity entry on the right: the avatar for a member, an entry to join for a guest.
- No Groups, Leaderboard or Routes tabs; no hero card while there is no real community content.
- Plain background, no artwork (the Feed shows how people drive, never where: ADR 0007).

## What the code does today (files read)

- `Features/Feed/Views/FeedView.swift`: a `ScrollView`; while loaded and the pulse is known,
  `FeedPulseHeader`, then the rows (`sheet`). The bar: inline title "Feed" drawn small and
  centred (`.navigationTitle` + `.inline`), `ProfileToolbarItem` at the **leading** edge.
  A failed first load shows no header (`feed.md`: no right number means no number).
- `Features/Feed/Views/FeedPulseHeader.swift`: two modes (`CommunityPulse`):
  - `.numbers` (10 drivers or more in 72 h): a Copper "72h" pill, "**142** drivers" at
    `.largeTitle` bold, then "9,840 km · 312 h · Busiest 7–8 AM" (`.subheadline`).
  - `.warmingUp`: "You're among the first drivers" (`.title3` bold, one line, scaled down before
    it wraps), "driving together around the world", then `RoadMarkings` (the warm-up dashes).
- `DesignSystem/Components/JourneyComponents.swift`: `ProfileToolbarItem` (leading; hides the
  bar's shared glass; `OwnAvatar` at 34 pt in a 44 pt target; VoiceOver "Join the Feed" for a
  guest, "Edit profile" for a member; a guest's avatar is a person symbol).
- `Features/Passport/Views/PassportView.swift` (as built, `a528517`): leading toolbar item = the
  stamp at 30 pt + "Passport" in `.title2` bold, shared background hidden, a header trait;
  trailing = the gear; inline display mode with a clear principal item so the system draws no
  centred title.
- Spec: `docs/specs/feed.md`, "Header" and "States".

## Proposal

**The bar** (pinned, system):
- Leading: the Feed's symbol (`person.2.fill`, the tab's own, in Copper at the stamp's size) and
  "Feed" in `.title2` bold, one header element for VoiceOver; shared background hidden. The same
  item shape as the Passport's, extracted into one `TabTitleToolbarItem(symbol:title:)` beside
  `ProfileToolbarItem` so the two pages cannot drift (logic found twice is merged).
- Trailing: the identity entry. Member: the avatar, as today. Guest: decision 2 below.
- No centred title.

**Under the bar** (scrolls with the page), a new `FeedHeader` replacing `FeedPulseHeader`'s top:
- "The journeys we share." / "Những hành trình ta cùng chia sẻ." (`.body`, secondary). Shown in
  every loaded state, also before the pulse is known; not on a failed first load (the error
  replaces the page, as today).
- The pulse, one line (`.subheadline`, secondary, `monospacedDigit`):
  - 10 drivers or more: the Copper "72h" pill, then "**142 drivers** · 9,840 km · 312 h ·
    Busiest 7–8 AM" (the count in primary semibold). Wraps between its parts at xxxLarge, never
    inside one.
  - Fewer than 10: "You're among the first drivers" as that one line (no pill, no number, as the
    spec requires), and the road-marking line under it as today; the "driving together around
    the world" subtitle goes (the new subtitle says what the page is).
- Rows, empty and failed states: unchanged.

Strings: `Feed.headerSubtitle` (new). `Feed.pulseFirstSubtitle` removed if nothing else uses it.

Docs: `docs/specs/feed.md` (Header; Item layout's "Then the header"), `docs/design-system.md`
(Screen layout: the Feed joins the Passport's exception: its title shows in the bar),
`docs/specs/navigation.md` (the avatar moves to the trailing edge).

## Decisions for the owner

| # | Decision | Recommendation |
|---|---|---|
| 1 | A symbol before "Feed", as the stamp before "Passport" | yes, `person.2.fill` in Copper: the two tab pages read alike |
| 2 | A guest's entry on the right | the person-symbol avatar as today (VoiceOver "Join the Feed"), not a "Join" text button: the invite row in the Feed already says Join in words, and a text button in the bar would be a second call to action |
| 3 | The large "142 drivers" | becomes part of the one pulse line (the mockup); the Feed's large type is the bar's title only |
| 4 | Vietnamese subtitle | "Những hành trình ta cùng chia sẻ." (native, not word for word; to confirm) |

## Acceptance

- The bar stays put while the Feed scrolls; its title and avatar match the Passport's placement.
- The subtitle and pulse line show in the loaded states; the failed first load shows the error
  alone; the empty state keeps the subtitle and pulse.
- Fewer than 10 drivers: no pill, no number, no 0.
- Light, Dark, xxxLarge, Vietnamese screenshots (sample Feed: numbers, warm-up, empty, failed,
  guest, member); `task lint`, `task warnings`, `task test` pass.

## Non-goals

Rows, reactions, the invite, the profile sheet, publishing. No contract or schema change.

## How to build it

Inline, one session, Opus: one screen, the Passport's bar to copy, no domain logic.
