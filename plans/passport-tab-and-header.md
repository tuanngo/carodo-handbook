# Passport as a tab, and its editorial header

Status: **Built 2026-11-14.** Slice 1 `34433d2` (the Passport tab; the floating bar keeps the
default text size, owner-approved exception), slice 2 `f4e4b4d` (the header). Approved by the owner
with every recommendation below; the workspace `AGENTS.md` edit allowed. Built differently from the
plan: the artwork is a still `Canvas` (drawn when its lines, size or appearance change) rather than
an image rendered off the main actor; only the geometry is computed off it. Before the first drive
the header shows the title alone (decision 5's line would repeat the first-drive note below it).
Open: device checks below; the artwork's framing on the owner's real history.
Mockup: [`design/mockups/passport/passport-feed-headers.png`](../design/mockups/passport/passport-feed-headers.png)
(source `design/mockups/source/passport-feed-headers.html`), Round 3, first frame (P2).

## Outcome

1. **Slice 1 — the Passport is a tab.** The floating bar reads Map · Journeys · Passport · Feed,
   plus Start Drive. The round stamp leaves Journeys.
2. **Slice 2 — the Passport opens on an editorial header.** "Your Passport", "Every road since
   March 2026.", the all-time GPS distance as the hero figure, drives and driving time in one
   line, all directly on the background; the person's own routes drawn once, faintly, behind it.

Two commits, in this order: slice 2's header has no Back only because of slice 1.

Follow-ups, each with its own plan, not part of this one: the Feed's header (title "Feed", "The
journeys we share.", avatar or Join on the right) and Journeys' Filter (`slider.horizontal.3`:
Vehicle, Distance; later Places / Regions).

## Owner decisions already taken (2026-11-14, in conversation)

- The Passport becomes a tab; order Map · Journeys · Passport · Feed. The Feed keeps its name.
- The page draws its own large title; the system bar draws none.
- No @username, no Private chip, no stamp in the header: the Passport is the private side by nature.
- "Since" is the subtitle (mockup P2). The hero figure is the distance; no card, no icons, no rules.
- The artwork is the person's own routes, drawn once as a still image, in the hero only.

These overturn written rules, changed in place in the same commits (pre-release, so no superseding ADR):

| Rule today | Where | Becomes |
|---|---|---|
| Tabs are Map · Journeys · Feed; the Passport "stays on Journeys only; no tab or screen for it elsewhere" | ADR 0007 line 5–6; `docs/specs/navigation.md` | four tabs; the Passport is a tab |
| The Passport is a focused space; the bar steps aside | `navigation.md`, `passport.md` Navigation | the bar shows on the Passport's own page; pages pushed from it (Settings, a journey, milestones) still hide it |
| "No large titles"; "no other screen gets a heading or a drawn background without a decision" | `docs/design-system.md#screen-layout` | a second named exception: the Passport's header (title, subtitle, route artwork), owner 2026-11-14 |
| "No visible title (decided 2026-11-05: the Identity card's stamp says Driving Passport)" | `passport.md` Navigation | the large title in the page |

## What the code does today (files read)

- `DesignSystem/Components/FloatingNavigation.swift`: `RootTab` (`map`, `journeys`, `feed`; raw
  values used only by the DEBUG `-carodo.debugTab` arguments, never stored), `FloatingNavigationBar`
  lays the tabs out with `ForEach(RootTab.allCases)`, each `maxWidth: .infinity`, label `caption2`
  on one line with `minimumScaleFactor(0.8)`; `marks: [RootTab: LocalizedStringResource]` draws the
  Copper dot and gives VoiceOver its value.
- `App/MainTabView.swift` (868 lines): one `NavigationStack` and one `[AppRoute]` path per tab
  (`mapPath`, `journeysPath`, `feedPath`); `switch appState.selectedTab` over the three paths in
  `isBarHidden`, `applyLaunchArgumentsOnce`, `openRecordingRequirements`, `openSavedToast`;
  `destination(for:)` builds a **new `PassportViewModel` on every push** of `.passport`;
  `openDriveFromPassport` pops to Journeys before opening the Start panel because the bar is hidden
  on the Passport; `marks` carries only Journeys' "needs a look".
- `App/AppRoute.swift`: `.passport` is a route with `hidesFloatingBar == true`.
- `DesignSystem/Components/JourneyComponents.swift`: `PassportToolbarItem` (the stamp on Journeys,
  with the unseen-milestone dot from `appState.hasUnseenMilestone`), used only by `JourneysView`.
  `PassportStampIcon` is used only by it (and a preview).
- `Features/Passport/Views/PassportView.swift`: a `ScrollView` of a `VStack`; first
  `PassportIdentityHeader` (stamp, name from `appState.feedProfile`, "Driving since", Private chip,
  then `PassportLifetimeSummary`: three `StatColumn`s with dividers; loading = redacted
  placeholder, failed = line + Retry); the title hidden by a clear principal toolbar item; the gear
  pushes `AppRoute.settings`.
- `Features/Passport/ViewModels/PassportViewModel.swift`: `allTime`, `drivingSince`, `state`;
  `loadExploration()` **already reads routes** for the Footprint
  (`journeyRepository.drivenRoutes(in:)` → `PassportGeometry.segments(of:hiding:)`, gap-free and
  with private places removed, off the main actor, with a `fingerprint`). So "the Passport reads no
  route" in `passport.md` is already out of date (docs disagree; the code wins).
- `Core/Journal/RouteGlyphMaker.swift`: `glyphs(for:)` frames several drives in one frame, north
  up, thinned to at most 48 points a part; `RouteGlyphView` draws them.
- `Features/Developer/DebugLaunchArguments.swift`: `routes` is `[.passport] + pages`;
  `-carodo.debugOpenPassport` pushes it on the selected tab.
- Tests: `AppRouteTests` (asserts `.passport` hides the bar), `DebugLaunchArgumentsTests`
  (asserts `[.passport, .settings, .developer]`).
- Working tree: `docs/operations/setup.md` has another session's uncommitted change; this work
  adds its rows with the temp-index recipe (AGENTS.md, Git), never `git add` on the whole file.

Assumed, not checked: that a hidden-tab-bar `TabView` builds the Passport's stack only when the
tab is first selected, and fires `onAppear` each time it is selected (the milestone dot is
cleared by `PassportStampRow`'s `onAppear`; if the tab were built early the dot would clear
unseen: checked in slice 1, step 4); that `caption2` labels for four tabs fit
at xxxLarge in Vietnamese (see slice 1, step 5: measured, with a fallback).

## Slice 1 — the Passport is a tab

Steps:

1. `RootTab`: add `passport` between `journeys` and `feed`; title `Common.tabPassport`
   ("Passport" / "Hộ chiếu"); symbol `seal.fill` (the system's stamp shape; the same family as
   the `seal` on the milestones card). `allCases` order is the bar's order.
2. `MainTabView`: a `passportPath` and a fourth `tab(path:)` holding `PassportView`; the
   `PassportViewModel` is created **once** in `init` as `@State`, like `journeysModel` (a tab root
   lives as long as the shell; a model per push would reload on every return). Every
   `switch appState.selectedTab` gains the case. To stop four copies of the same switch, one
   private helper `withCurrentPath(_ body: (inout [AppRoute]) -> Void)` replaces them (logic found
   four times, merged in the same change).
3. `AppRoute`: remove `.passport` (nothing pushes it any more) from the enum, `hidesFloatingBar`
   and `destination(for:)`. Settings, milestones, visited places and journeys pushed from the
   Passport keep `hidesFloatingBar == true`, so the focused pages behave as today.
4. Journeys: remove `PassportToolbarItem` from `JourneysView`, and delete the type and
   `PassportStampIcon` with the strings only they used (`Common.passportHint`; `Common.passportLabel`
   if nothing else reads it). The leading slot stays **empty** until the Filter plan: no dead button.
   The unseen-milestone dot moves to the bar: `marks[.passport] = .Passport.milestoneNew` while
   `appState.hasUnseenMilestone`.
5. The bar with four tabs: check 390 pt and 375 pt widths, xxxLarge, Vietnamese. If a label would
   be cut or scaled below its neighbours, the tabs fall back to icons only for **all four**
   (`ViewThatFits` between the labelled and the icon-only row; the icon-only row is the compact
   bar's existing look). Never a "…".
6. The Passport as a tab root: `collapsesFloatingBar()` on its scroll view, as Journeys and the
   Feed; `openDriveFromPassport` loses its tab switch (the bar and the Start panel are on screen
   there now): it becomes the same call as the Start button; `PassportFirstDriveNote`'s comment is
   corrected. The Back button is gone by construction; the gear stays top trailing.
7. DEBUG arguments: `-carodo.debugTab passport` works through the raw value;
   `-carodo.debugOpenPassport YES` now selects the Passport tab; `routes` drops its leading
   `.passport` and its pages are pushed on `passportPath`. `docs/operations/setup.md` rows updated.
8. Docs in the same commit: ADR 0007, `specs/navigation.md` (tabs, focused pages, "Where the
   statistics live" item 3), `specs/passport.md` (Navigation), `specs/journeys.md` (Header: the stamp),
   `design-system.md` (Components: the `RootTab` row and the Passport marks row),
   `carodo-ios/AGENTS.md` (Architecture: the MainTabView line). `specs/share.md` and ADR 0013
   also say "round stamp", but mean the share card's and the badges' stamps: untouched. The workspace
   `AGENTS.md` ("Tabs: Map · Journeys · Feed") is outside both repos: the owner's edit, or said yes to here.

Tests: `AppRouteTests` (the Passport's pushed pages still hide the bar; `.passport` gone),
`DebugLaunchArgumentsTests` (new routes; the tab selected), a `RootTab` test fixing the order
and that every tab has a title and a symbol; `LocalizationTests` covers the new string.

Acceptance:
- Four tabs in the stated order; each keeps its own navigation state when left and returned to.
- The Passport tab shows the bar and Start Drive; Settings and a journey pushed from it hide them;
  a recording drive keeps its compact panel in both.
- The milestone dot shows on the Passport tab, stays while another tab is in front, and clears
  when the Passport's milestones card is shown; VoiceOver reads "Passport, new milestone".
- Journeys has no stamp; nothing else on Journeys moved.
- No label cut or shrunk at xxxLarge in Vietnamese on a 375 pt wide screen.
- `task lint`, `task warnings`, `task test` pass; screenshots: the bar on each tab (Light, Dark,
  xxxLarge, Vietnamese), the Passport tab with a pushed Settings.

## Slice 2 — the editorial header

A new `PassportHeader` replaces `PassportIdentityHeader` and `PassportLifetimeSummary` (both
deleted, with `PassportPrivateChip` and the strings only they used: `Passport.private`,
`privateHint`, `drivingSince`, `allTime`; `StatColumn` and `Common.drivingTime` stay, others use them).

Layout (leading-aligned, 20 pt side padding, on `CarodoSurface.background`, no card):

| Line | Content | Type |
|---|---|---|
| Title | "Your Passport" / "Hộ chiếu của bạn" | `.largeTitle` bold, a header for VoiceOver |
| Subtitle | "Every road since March 2026." / "Mọi cung đường từ tháng 3, 2026." (month and year from `drivingSince`, the locale's format) | `.body`, secondary |
| Hero | the all-time GPS distance, value and unit (`DisplayFormat.distance`) | value rounded bold at a `@ScaledMetric(relativeTo: .largeTitle)` 64 pt; unit `.title2` secondary; one line, `minimumScaleFactor` only as the last guard |
| Label | "all-time GPS" (the existing `Passport.allTimeGps`: P2, never just "distance") | `.subheadline`, secondary |
| Line | "30 drives · 15h 38m driving" | `.title3` semibold, units secondary; `ViewThatFits`: one line, else the two facts on two lines, never broken inside a figure |

States (the rules of today's header, kept):
- **Loading:** the figures redacted, hidden from VoiceOver; the subtitle without its date.
- **Failed:** the existing line and Retry in place of the figures; never zeros.
- **No drives:** title and a subtitle without a date ("Your first drive starts the story." /
  Vietnamese to write natively); no figures, no artwork; `PassportFirstDriveNote` below as today.
- VoiceOver: the title, then the figures as one element ("830 kilometres, all-time GPS, 30 drives,
  15 hours 38 minutes driving"); the artwork hidden.

The bar: unchanged mechanics (system bar, hidden title kept for VoiceOver and the app switcher,
the gear, the soft top scroll edge). The header scrolls with the page; no inline title appears
after it (my call: the selected tab already names the screen, and it avoids scroll tracking).

The artwork (`PassportRouteArtwork`, in `Features/Passport/Views`):
- **Source:** the all-time redacted lines the view model already knows how to make
  (`drivenRoutes(in: nil)` → `PassportGeometry.segments(of:hiding:)`), kept as
  `PassportViewModel.signature` beside `exploration`. While the Footprint's scope is All time (the
  default) the two are one read: the result is shared, not read twice. Private places are removed
  exactly as on the Footprint; if places cannot be read, no artwork.
- **Drawing:** framed, projected and thinned by `RouteGlyphMaker`, the one type that already puts
  several drives in one frame (24–48 points a part, points under 0.2 % of the frame dropped, so
  a short drive in a wide frame costs a handful of points). `glyphs(for:)` takes `RoutePoint`s
  and splits them itself; the redacted lines are already split, so it gains an entry point that
  takes the parts and shares the rest (no copy of the projection or the thinning). Stroked 1.5 pt in `CarodoSurface.accent` at
  about 40 % (50 % in Dark), aspect-fit to the hero's trailing two thirds, under a mask that
  fades it out toward the text and before the header's bottom edge.
- **Once:** rendered to an image off the main actor (`@concurrent`), keyed by the geometry
  fingerprint, the size and the colour scheme; redrawn only when one of them changes. No map
  tiles, no MapKit, no network, nothing that renders while the page rests.
- **Too little to draw:** no lines, or a drawing under 300 m across (the glyph's own floor):
  plain background.
- **Framing is the open risk:** one long trip can shrink the home area to a knot. First build
  frames everything; it is judged on the real `drive-data/` journals on the simulator (local
  only, no screenshot of a real route committed). If it reads badly, the fallback is framing the
  area holding most of the distance; that would be a named algorithm in
  `docs/architecture.md#algorithms--one-per-problem` and comes back to the owner first.
- Cost: no second read while the Footprint is on All time; one more `drivenRoutes` read when the
  person picks another scope. No performance claim is made: `passport.md` quotes a 5,000-drive
  measurement, but no such test was found in `CarodoTests`, so the artwork's time on a long
  journal is a candidate to measure (opt-in test, `docs/architecture.md#complexity-budget`), and
  the image is made off the main actor so the page never waits for it.

Docs in the same commit: `specs/passport.md` (Driver Identity → the header; "reads no route"
corrected to what the Footprint and the artwork read), `design-system.md` (Screen layout: the
exception; Route line colours: the artwork's row), `copy-and-localization.md` if the glossary
lists the removed lines.

Tests: `PassportViewModel` (the signature is the all-time lines whatever the scope; shared with
the Footprint at All time; empty when places fail to read; private places removed), the artwork's
geometry (empty, one point, under the floor, several drives in one frame), a subtitle test (with
and without a first drive, both languages through `LocalizationTests`).

Acceptance:
- The header matches mockup P2 in Light and Dark; nothing in it is a card, an icon or a rule.
- xxxLarge, Vietnamese: no figure cut or broken; the line stacks.
- Loading, failed and no-drives states as above; never a zero that reads as a fact.
- The artwork never reaches the Footprint card, never shows a route through a private place, and
  the page at rest stays under 1 % CPU (device check).
- `task lint`, `task warnings`, `task test` pass; screenshots of the four states × Light, Dark,
  xxxLarge, Vietnamese (synthetic sample data only).

## Non-goals

- The Feed's header and Journeys' Filter (follow-up plans).
- The cards below the header (Footprint, milestones, rhythm, garage): untouched.
- No schema, API, permission, entitlement, dependency or target change. No new stored string
  (`RootTab` raw values are DEBUG arguments only).

## Decisions for the owner

| # | Decision | Recommendation |
|---|---|---|
| 1 | The Passport tab's icon | `seal.fill`, judged on the screenshots; the drawn stamp can replace it later |
| 2 | Four labels do not fit at xxxLarge in Vietnamese | all four tabs fall back to icons only |
| 3 | The leading slot on Journeys until Filter ships | empty |
| 4 | An inline "Passport" title in the bar after the header scrolls away | no |
| 5 | No-drives subtitle | "Your first drive starts the story." |
| 6 | The workspace `AGENTS.md` line naming three tabs | the owner edits it, or allows this work to |

## Device checks still required after both slices

- The bar's four tabs and the Start Drive button on a real iPhone (glass on iOS 26, the surface on iOS 18).
- The Passport at rest under 1 % CPU with the artwork; the artwork on the owner's real history.

## How to build it

- **Inline, in one session, not parallel agents.** Slice 1 is a navigation change through
  `MainTabView`, one of the files several sessions share; AGENT_WORKFLOW names navigation as work
  for one integration owner. Slice 2 depends on slice 1 and is small.
- **Model.** Slice 1 is mechanical once this plan is approved (a new enum case and the places the
  compiler then points at): Opus is enough. Slice 2's layout is also within Opus; the artwork's
  framing judged on real data is the one part worth the stronger model, or the owner's eye on
  the simulator.
