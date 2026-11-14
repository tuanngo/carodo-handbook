# Journeys — Filter / Refine

Status: **Built 2026-11-15.** Approved by the owner with every recommendation (2026-11-14).
Slice 1 carodo-ios `10cd23d` (Vehicle and Distance), slice 2 `fa68304` (the period in the sheet).
Built differently from the plan: the sheet opens about three quarters high, not at the medium
height (three groups did not fit, and the chosen period sat under the button); the Vehicle group
needs two vehicles in the garage, archived ones included, not two active ones; `ChipFlow` moved
from the share card's panel to the design system for the sheet and the tokens. Found on the way:
Explore hid every other journey when the journal held one driven drive and passenger trips (the
history waited for two *driving* drives); it now follows the listed journeys (`showsHistory`,
tested). After the owner's review (2026-11-15) carodo-ios `a5587ee`: the chips and tokens take the
share editor's Aa chip size, the Show button sits on its own ground, and the sheet measures itself
to open exactly as tall as its chips need.

### Open, for the owner's review

1. **Device checks (PV-23):** the sheet and tokens at xxxLarge on an iPhone SE-class width; the
   self-sizing sheet on a real device (the first open, rotating text size while it is up); a
   rare-vehicle filter timed on the real history (no index on vehicle or distance); VoiceOver on
   the chips, tokens and the button's "2 on".
2. **Copy to approve:** "Filter / Lọc chuyến", "GPS distance / Quãng đường GPS", "Any / Mọi
   quãng", "Period / Thời gian", "All time / Mọi lúc" (was "All / Tất cả"), "This year / Năm nay",
   "Show 4 drives / Xem 4 chuyến", "No drives match / Không có chuyến nào khớp", "No drives match
   these filters. / Không có chuyến nào khớp với bộ lọc.", "Clear filters / Bỏ lọc", VoiceOver
   "Remove filter: … / Bỏ lọc: …", "2 on / Đang lọc theo 2 mục".
3. **Taste:** the filter button is primary ink at rest while **+** beside it is Copper (the app
   tint); the mockup draws both dark. Keep, or make both the same ink.
4. **Not built, by plan:** Places / Regions groups; tags (Night, Long) as chips; a chip for drives
   with no car; Search.
Mockup: [`design/mockups/passport/passport-feed-headers.png`](../design/mockups/passport/passport-feed-headers.png),
Round 3, frames J1 (at rest), J2 (the filter sheet), J3 (filtered, with tokens).
Follows [`passport-tab-and-header.md`](passport-tab-and-header.md), which freed the bar's leading slot.

## Outcome

Journeys has one place to narrow the journal: a `slider.horizontal.3` button at the leading edge of
the bar opens a sheet with Vehicle and Distance (and, if decision 1 is approved, the period). While
a filter is on, the button turns Copper with a dot, each active filter is a token under the bar
that one tap removes, a totals line states what the filter holds, and Explore lists only the drives
that match. Places / Regions can join the sheet later without reworking it.

## Owner decisions already taken (2026-11-14)

- The button is `slider.horizontal.3` at the bar's leading edge (empty since the Passport stamp
  became a tab, `34433d2`).
- Vehicle and Distance first; Places / Regions may follow.

## Audit — what the code does today

Files read: `docs/specs/journeys.md`, `docs/design-system.md` (Native header controls),
`Features/Journeys/Views/Explore/JourneysView.swift`, `Features/Journeys/ViewModels/Explore/JourneysViewModel.swift`,
`DesignSystem/Components/JourneyCards.swift` (`JourneyPeriodMenu`, `JourneyMonthHeader`),
`Core/Domain/JourneyAnalysis.swift` (`JourneyPeriod`), `Core/Repositories/JourneyRepository.swift`,
`Core/Persistence/GRDBJourneyRepository.swift`, `Core/Journal/JourneyStatisticsService.swift`,
`Core/Persistence/DatabaseManager.swift` (indexes), `Core/Domain/Vehicle.swift` (`active`,
`namedOnRow`), `Features/Journeys/ViewModels/Day/JourneyDayViewModel.swift` (vehicle use only).

1. **The bar.** `JourneysView.toolbar` has the Explore / Day picker (`.principal`) and **+**
   (`.topBarTrailing`, only when a car can be logged for). The leading slot is empty.
2. **The only filter is the period.** `JourneyPeriod` (`all`, `week`, `month`) lives in
   `JourneysViewModel.period` (not saved: every launch opens on All). `JourneyPeriodMenu` sits at the
   trailing edge of the *first month header* (`JourneyListRowView`, `isFirst`), or beside "No other
   drives in this period." when only the latest drive is left. It is used nowhere else.
3. **What the period narrows.** `listInterval` feeds three reads: the pages
   (`journeyRepository.journeys(in:before:limit:)`, and the second read that finishes the last day),
   the month headers' distance (`loadMonthTotals` → `summary(in: month ∩ period)`), and `summary`
   (the filtered totals). `summary` is **read by no view today** (only `JourneysViewModelTests`):
   Explore shows no totals line for a period.
4. **What it does not narrow.** The latest drive (`statistics.latestJourney()`, the journal's newest
   sure drive) and `overview` (all time, used only by `isFirstDrive` and to decide whether a history
   exists). `rebuildList` always drops the latest drive from the rows and drops a day heading left
   with only it.
5. **Reloads and staleness.** The view's `.task(id:)` keys on `mode`, `requestID` (= `period.rawValue`)
   and `journalRevision`; `load()` takes a new `generation` and every await checks it, so a slow
   answer for an old period never replaces the new one. A filter must join `requestID` the same way.
6. **Queries.** GRDB pages are `SELECT * FROM trips WHERE <journal> [AND started_at range]
   [AND started_at < cursor] ORDER BY started_at DESC LIMIT ?` on the partial index
   `trips_on_journal (started_at)`. A private `condition:` parameter exists for SQL written in the
   store (never from input). `summary(in:)` is one aggregate counting only sure, driven drives
   (`driving`: `confirm_by IS NULL AND rider = 'driver'`). `trips_on_vehicle (vehicle_id)` exists;
   there is no index on `distance_m`, and none is needed (below).
7. **Day.** `JourneyDayViewModel` reads one day (`journeys(in: day)`), the month heatmap
   (`activity(in:)`) and the day's totals; it has no filter and its figures are "what happened on
   this day".
8. **Vehicles.** The garage includes archived vehicles (`archivedAt`, ADR 0014); `[Vehicle].active`
   filters them out; a row names its car only when more than one vehicle is active (`namedOnRow`).
   A journey's `vehicleID` may be nil (a pending drive with no guess, older data).
9. **Distance bands in use elsewhere.** Day's heatmap colours a *day* by its GPS distance: none,
   under 10 km, 10–<50, 50–<100, 100+. The derived tag "long drive" is 100 km or more. Neither is a
   drive filter.
10. **Spec.** `journeys.md` "Not built → Search" already imagines "tokens filter by vehicle and by
    tag (Night, Long) beside the period filter". This plan builds the tokens without the search
    field; Search stays Not built.
11. **Names.** No `JourneyFilter`, `DistanceBand` or other `*Filter` type exists in `Carodo/`
    (`SpeedBand` is speed, unrelated).

**Mockup vs spec (the spec wins):** J1–J3 still show the "Where have I been?" heading (removed,
`a844e28`) and journeys in cards (Explore rows are unboxed); the mockup's periods are "All time /
This month / This year / 2025", the code's "All / This week / This month".

## Proposal

### Behaviour

- **Button** (Explore only, see decision 3): `slider.horizontal.3` in `.topBarLeading`, secondary
  ink at rest; Copper with a small Copper dot while any filter is on (J3). VoiceOver: "Filter",
  value "Off" / "2 on". A light tap opens the sheet.
- **Sheet** (J2): medium detent, drag indicator, the app's background. "Filter" with **Reset** (only
  when something is chosen). Groups as single-choice chips, one choice per group, the chosen one in
  a light Copper tint with a Copper outline (the same language as Day's selected day):
  - **Vehicle:** All, then the garage's vehicles, active first then archived (history keeps them;
    decision 4). Hidden when the garage has at most one vehicle, as a row's car is.
  - **GPS distance** (labelled as GPS distance, P2): Any, then the bands of decision 2.
  - **Period** (only if decision 1 is approved): All time, This week, This month, This year, then
    past years.
  - The button at the bottom says how many drives the list will show and closes the sheet:
    "Show 4 drives" / "Hiện 4 chuyến"; "No drives match" (disabled) at zero. The count is read
    live as chips change (one `COUNT(*)`, see Data), with the same generation guard as the pages.
  - Changing a chip applies on **Show**, not at once (the list behind the sheet does not reload on
    every tap); dismissing by drag keeps the previous filter.
- **Tokens** (J3), under the bar, above the list: one capsule per active filter ("Mazda CX-5 ×",
  "Over 50 km ×"), Copper ink on a light Copper tint; a tap removes it. They wrap to a second line
  at large text, never cut. VoiceOver: a button "Remove filter: Mazda CX-5".
- **Totals line** under the tokens: "4 drives · 412 km" (`Common.countDrives` + GPS distance),
  counting what every total counts (sure, driven drives), the same rule as a day header.
- **Latest drive:** hidden while a filter is on (decision 3); the list is then exactly the filter's
  drives, newest first, the latest one included as an ordinary row.
- **Empty:** a filter that matches nothing shows one centred line, "No drives match these
  filters." with "Reset filters" under it (no zero totals). It replaces "No other drives in this
  period." if decision 1 moves the period.
- **State:** the filter lasts the session (tab switches, a drive's detail and back), never saved; a
  fresh launch opens unfiltered, as the period does today. Pull to refresh keeps it. A vehicle
  deleted while chosen drops its token.

### Data (no schema change, no contract change)

- `Core/Domain/JourneyFilter.swift`: `nonisolated struct JourneyFilter: Equatable, Sendable` with
  `interval: DateInterval?`, `vehicleID: UUID?`, `distance: DistanceBand?` (half-open meters range,
  SI at rest), `isEmpty`, and a stable `requestID` string for the view's task id. `DistanceBand`
  owns its edges and its label (formatted at the boundary through `DisplayFormat`).
  Places / Regions later add fields here.
- `JourneyRepository`: the interval methods gain a filter form —
  `journeys(matching:before:limit:)`, `summary(matching:)`, `count(matching:)`; the existing
  `journeys(in:…)` and `summary(in:)` stay as one-line wrappers (`JourneyFilter(interval:)`), so
  Day, the Passport, Places and the statistics service do not change. In-memory defaults filter
  in Swift (`JourneyFilter.matches(_ journey:)`, the one predicate the tests check against SQL).
- GRDB: `vehicle_id = ?`, `distance_m >= ? AND distance_m < ?` appended with arguments (never
  interpolated). Ordering still walks `trips_on_journal`; the extra conditions are checked per row.
  Risk named: a rare filter (an archived car with three drives) pages by walking the whole journal
  index — a few thousand rows of one table, no route decoded; acceptable at this scale, and a
  candidate to measure on the iPhone with the owner's history, not a reason for a new index.
- `JourneyStatisticsService.summary(matching:)` beside `summary(in:)`.
- `JourneysViewModel`: `filter` replaces `period` (or holds it, decision 1); `listInterval`
  becomes the filter; the page read, the finish-the-day read and the month totals all take it;
  `rebuildList` keeps the latest drive in the rows when the feature is hidden; `requestID` is the
  filter's; `hasFilter`, `tokens`, `removeToken(_:)`, `reset()`, and `matchCount(for:) async` for the
  sheet.

### Files

| File | Change |
|---|---|
| `Core/Domain/JourneyFilter.swift` (new) | `JourneyFilter`, `DistanceBand` |
| `Core/Domain/JourneyAnalysis.swift` | `JourneyPeriod` gains `year` (and past years) if decision 1 |
| `Core/Repositories/JourneyRepository.swift` | filter methods + in-memory defaults; interval wrappers |
| `Core/Persistence/GRDBJourneyRepository.swift` | filter SQL on the page, summary and count reads |
| `Core/Journal/JourneyStatisticsService.swift` | `summary(matching:)` |
| `Features/Journeys/ViewModels/Explore/JourneysViewModel.swift` | filter state, tokens, latest-drive rule, count |
| `Features/Journeys/Views/Explore/JourneysView.swift` | leading button, sheet, tokens, totals line, empty state; drops the period menu (decision 1) |
| `Features/Journeys/Views/Explore/JourneyFilterSheet.swift` (new) | the sheet |
| `DesignSystem/Components/JourneyCards.swift` | `JourneyPeriodMenu` removed if decision 1 (no other user) |
| `Resources/Localization/Journeys.xcstrings` | new strings, English and Vietnamese |
| `docs/specs/journeys.md` | Header, Explore (history, latest drive), Filter section, Search note, Data |
| `docs/design-system.md` | Native header controls: the filter button replaces "the period menu belongs to the content" |
| `docs/operations/setup.md` | a DEBUG launch argument opening Explore filtered, for screenshots |

### Tests

- `JourneyFilterTests`: band edges on both sides (9 999 m / 10 000 m, 49 999 m / 50 000 m), miles
  edges if decision 2 keeps unit-specific bands, `isEmpty`, `requestID` stable.
- `GRDBJourneyRepositoryTests` (in-memory database): pages, summary and count with vehicle, band and
  interval together; a passenger and a pending drive listed but not in the summary; the
  finish-the-day read keeps the filter; SQL agrees with `JourneyFilter.matches` on the same rows.
- `JourneysViewModelTests`: a filter reloads and drops an older answer (generation); the latest
  drive is hidden and listed as a row while filtered, back as the feature on reset; month totals
  follow the filter; token removal; empty state with no zero totals; the period still narrows
  (regression), and the latest drive's "First drive" label never claims from a filtered read.
- `LocalizationTests` cover the new strings.

## Decisions for the owner

1. **Move the period into the sheet?** **Recommended: yes.** One place states every filter; the
   period becomes a token like the others, so "This month" is always visible without scrolling to
   the first month (today it scrolls away with it). The month header goes back to being a header.
   Periods: All time, This week, This month, This year, then each past year with drives (from the
   journal's first drive: one `MIN(started_at)` row; none appear until the journal spans a second
   year). Cost: the period is one tap further (sheet, chip, Show) instead of a menu.
   Alternative: keep the menu where it is and leave the sheet to Vehicle / Distance — two places
   to filter, and the menu's Copper name and the button's dot would both say "filtered".
2. **Distance: three fixed bands?** **Recommended: yes, the mockup's three, as half-open ranges:**
   Under 10 km · 10–50 km · Over 50 km (`< 10 000 m`, `10 000–< 50 000 m`, `≥ 50 000 m`), so every
   drive falls in exactly one band. In miles: Under 5 mi · 5–30 mi · Over 30 mi (round edges in
   the person's unit, converted to meters for the query, never "Under 6.2 mi"). Reasons: three
   short chips fit one line at default text, cover the commute / errand / trip shapes of the
   owner's real journal, and need no slider (a range slider is fiddly in a sheet and invites
   precision nobody needs here). Not chosen: Day's heatmap bands (they describe a *day*, and five
   chips crowd the row); a free range slider; "Over 100 km" (the Long tag) — can join as a fourth
   chip later if the owner looks for road trips.
3. **Explore, Day, or both; and the latest drive?** **Recommended: Explore only, and the latest
   drive hides while any filter is on.** Day answers "what happened on this day": its totals, its
   strip marks and its calendar heat would stop meaning the day if a car were filtered out, and a
   filtered day would often be empty. So the button and the tokens show in Explore only (the leading
   slot is empty in Day; the picker stays centred), and the filter is kept for when the person comes
   back to Explore. The latest drive hides because a filter promises "only these drives": a Honda
   drive featured above a Mazda filter would contradict it; the totals line takes its place, and
   the latest drive, if it matches, is the first row. With decision 1, "This week" hides it too —
   consistent, and harmless (the latest drive is almost always this week's first row).
4. **Vehicle list** (smaller): **recommended:** the garage's vehicles, active first, then archived;
   the group hidden with one vehicle. Drives with no car have no chip in slice 1.

## Slices

1. **Filter: Vehicle and Distance** — domain, queries, view model, button, sheet, tokens, totals
   line, latest-drive rule, empty state, spec. The period menu stays as it is. One commit.
2. **Period in the sheet** (if decision 1) — `JourneyPeriod.year` and past years, the period group
   and token, `JourneyPeriodMenu` removed, spec and design-system updated. One commit.

Each is proven by `task lint`, `task warnings`, `task test`, and simulator screenshots (Light and
Dark, xxxLarge, Vietnamese) of J1, J2, J3 and the empty state, with `-carodo.sampleData YES`
(no real route in a screenshot that leaves the scratchpad).

## Acceptance criteria

- The button opens the sheet in Explore; it is not shown in Day.
- Choosing Mazda CX-5 and Over 50 km lists only those drives, newest first, with their day and
  month headings, the month distance counting only them, and "N drives · X km" equal to the sum of
  the listed sure, driven drives.
- The sheet's count equals the number of rows the list then shows.
- Each token removes its filter in one tap; Reset clears all; the latest drive comes back unfiltered.
- A drive exactly at 10 km lands in 10–50 km; at 50 km in Over 50 km.
- Paging and the finish-the-day read keep the filter (a filtered list never shows a non-matching
  drive after scrolling).
- Changing the filter quickly never shows an older filter's results.
- xxxLarge: chips and tokens wrap, nothing cut; VoiceOver reads the button's state and each token as
  a removable filter. English and Vietnamese.
- No schema, API, permission or dependency change.

## Non-goals

Search (the text field), Places / Regions, tags (Night, Long), multi-select within a group,
saving the filter across launches, a filter on Day or the Map, the Passport's own period chips.

## Assumed, not checked

- That the owner's journal (pulled database) holds few enough drives that the unindexed vehicle /
  band conditions stay well under a frame; to measure on the iPhone in slice 1, not claimed.
- That `.topBarLeading` and the principal picker coexist at xxxLarge on the smallest supported
  iPhone without the picker shrinking further than today (it already flexes for **+**).

## Device checks still required

Sheet and tokens at xxxLarge on an iPhone SE-class width; scroll and filter on the owner's real
history (timing of a rare-vehicle filter); VoiceOver on the sheet's chips.
