# Journeys · Day V1 — a daily driving journal

Status: **Built** (carodo-ios `066de55`, 2026-11-12): Phases 1–5 done; approved by the owner on 2026-11-11 (D1–D13, Q1–Q7 as recommended, refinements R1–R3). Later owner calls: driving time on rows and totals alike, "Today"/"Yesterday" in the day label, VoiceOver lines short and native. Open: device checks (haptics, midnight, zone change, VoiceOver), TD-16..18.
Phase 1 approved to build; Phase 2 waits for the owner's review of Phase 1. No commit before review.
Audit: this session, 2026-11-11 (files read are listed under Existing behaviour).

## Outcome

The Journeys tab's `List | Activity` becomes `Explore | Day`. Explore is today's List, unchanged
here (its polish is planned separately). Day answers one question, **what happened on this day?**:
a week strip that expands into the month calendar, the day's driving totals, and the day's journeys
shown according to how many there are. Journey Detail stays the one place that answers **what
happened during this journey?**

User story: "I open Day and see today. I swipe back a week, see which days I drove, tap Saturday
and see the one long trip I made, or the four errands; one tap takes me to the drive."

## Owner decisions (2026-11-11)

| # | Decision |
|---|---|
| D1 | Oldest journey first, morning to evening. |
| D2 | Day totals use moving time ("Driving time"), as Explore and the Passport; a journey's own row keeps its elapsed duration. |
| D3 | Pending and passenger journeys are listed with their existing marks, and left out of the totals and the calendar's activity marks (as Activity today). |
| D4 | Day opens on today, even with no drives, with a quiet shortcut to the most recent day with drives. |
| D5 | No between-drive gaps in V1: no inferred places, nothing that duplicates Smart Stops. |
| D6 | Days stay in the device's current calendar for V1. The conflicting docs are resolved, and days in the recorded zone are written down as deferred. |
| D7 | Week-based horizontal paging, in the calendar's first weekday and locale. |
| D8 | The heatmap lives on as the expandable month calendar. |
| D9 | Two calendar states in one screen: a compact week strip (default) and an inline month overview, opened by tapping the month/year header. No modal `MonthYearPicker` as the main navigation. |
| D10 | The content adapts: one journey (a prominent summary), several (compact entries), none (an empty note in context). |
| D11 | Day never duplicates Journey Detail: no route exploration, replay, Smart Stops, start/end discovery or analysis, and no raw track read for Day. |
| D12 | Both modes open the existing Journey Detail through `AppRoute.journey`. Coming back keeps the date, the calendar state and the scroll, and reloads only when the journal changed. |
| D13 | No backend, schema, recording or sync change. |

## Existing behaviour (files read)

- `Features/Journeys/Views/JourneysView.swift`: one `ScrollView` for both modes, sections chosen by
  `model.mode`, `.id(model.mode)` gives each mode its own scroll position; toolbar = Passport stamp,
  the segmented picker (a menu at accessibility sizes), **+** Log for your car.
- `Features/Journeys/ViewModels/JourneysViewModel.swift` (512 lines): owns both modes. List: pages,
  hero, overview, period filter, dropped drives. Activity: `activityMonth`, `selectedDay`,
  `activityDays`, `leadingDays`, `weekdaySymbols`, `picksDayOnLoad`/`chosenDay`, `journalCount`,
  `ActivityEmptyContext`. `JourneyDisplayMode { list, activity }` saved under
  `journeys.displayMode`. `calendar` is `Calendar.current` captured once at init.
- `Features/Journeys/Views/JourneyActivityCalendar.swift`: `JourneyMonthNavigation` (‹ month ⌄ ›
  plus the `MonthYearPicker` popover), `JourneyActivityCalendar` (7-column heatmap, today dot,
  selected outline, future days disabled, legend, Differentiate Without Color counts, a vertical
  list at accessibility sizes), `JourneyActivityDayHeader`, `JourneyActivityEmptyNote`.
- `Core/Journal/JourneyStatisticsService.swift`: `month(_:calendar:)` → `JourneyActivityMonth`
  (every day of the month, leading blanks, month totals) from `JourneyRepository.activity(in:calendar:)`;
  `summary(in:)`, `allTime()`, `latestJourney()` (newest non-pending, passenger included).
- `Core/Persistence/GRDBJourneyRepository.swift`: `activity(in:calendar:)` reads `started_at`,
  `distance_m`, `moving_duration_s` of sure, driven, completed trips in a range and groups them by
  `calendar.startOfDay` in Swift; `journeys(in:before:limit:)` (newest first, all journal trips incl.
  pending and passenger, joined parts folded in); `details(for:[Journey])` (titles, saved-place
  marks, purpose, one query). All on the partial `trips_on_journal(started_at)` index.
- `DesignSystem/Components/JourneyCards.swift`: `JourneyStatsBlock` (distance, drives, driving time
  = moving), `JourneyDayHeader`, `JourneyMapThumbnail` (snapshot, never a live map), `JourneyCompactCard`.
  `DesignSystem/Components/ActivityHeatPalette.swift`; `JourneyActivityDay.level` (five bands).
- `Features/Journeys/Views/JourneyHeroCard.swift`: 180 pt map + "● LATEST DRIVE" line, title,
  metrics, car, end place.
- Stops and points (`JourneyStops`, `JourneyPoint`, `JourneyBreak`, `PlaceDetection`,
  `JourneyAnalysis.stopIntervals`) all need one journey's raw track (`detailTrack`); nothing about
  stops is stored on `trips`. Out of Day V1 (D11).
- `Core/PreviewData/SampleJournal.swift` (`-carodo.sampleJournal N`): the newest drive is a long
  out-and-back on a highway (≈ 150 km+), weekdays are commutes and errands, some weekends are
  out-of-town days: every Day scenario exists in synthetic data.
- Docs: `docs/specs/journeys.md` (Activity, Days: device calendar, recorded zone "decided, not
  built"); `docs/data-model.md#time` says a drive's *day* reads in its recorded zone: **conflicts
  with the code and journeys.md** (code wins; fixed in Phase 1).

## Scope

In: the Explore / Day picker and the preference migration; `JourneyDayViewModel`; the week strip;
the inline month calendar; day totals; one / several / no journeys; the shortcut to the latest day
with drives; navigation and state restoration; calendar, zone, midnight and DST handling;
Activity code and copy removed; docs.

Non-goals: Explore polish; gaps or activities between drives; stops, places or memories on Day; a
day map of several routes; recorded-zone days; search; any schema, API, recording or sync change.

## Design

### Screen, top to bottom (one scroll)

1. **Calendar header**: the month and year ("November **2026**", year in Copper, as today) with a
   chevron that turns as the calendar expands; **Today** at the trailing edge only when the selected
   day is not today (a text button in Copper, never a fill).
2. **Calendar**, one of two states:
   - **Compact (default):** seven cells of the selected day's week, starting on
     `calendar.firstWeekday`; swipe pages a whole week. A cell = short weekday (Stone,
     `textSecondary`), the date number (Ivory/Charcoal ink, `textPrimary`), and under it a small
     Copper mark when the day has qualifying drives: its opacity or size follows
     `JourneyActivityDay.level` with the `ActivityHeatPalette` steps, so a 300 km day reads stronger
     than a 2 km one without a full heat fill. A day without drives keeps its number and no mark.
     Selected: a solid Copper cell with Charcoal content (R3). Today: the number in semibold Copper when not selected. Future days: a faint number,
     not selectable, no mark. The week ahead of the current one cannot be paged to.
   - **Expanded:** the existing month heatmap inline under the header (weekdays row, heat cells,
     legend), with ‹ › between months (no month after the current one). Tapping a day selects it
     and collapses back to that day's week. The header's month follows the paging and the
     expansion. The chevron, a tap on the header, or selecting a day collapses it.
   - The expand/collapse animates the height with `.carodo(...)` (Reduce Motion: a cross-fade).
   - **Visible week, selected day and header (R2):** three separate pieces of state.
     - `selectedDay` changes only by a tap on a day (strip or month), Today, or the latest-day
       shortcut. Swiping weeks or months **never** changes it; the selected day may be off screen.
     - `visibleWeek` (the start of the week the strip shows) follows the swipes; selecting a day
       makes it that day's week.
     - The **header month** is the month being browsed. In compact: the selected day's month
       when the selected day is in the visible week; otherwise the month holding most of the
       visible week's days (4 of 7). So 28 Oct – 3 Nov 2026 reads "October 2026", and "November
       2026" once 2 Nov is selected; 28 Dec 2026 – 3 Jan 2027 reads "December 2026", "January
       2027" with 1 Jan selected. In expanded: the month the grid shows.
     - **Expanding** opens the header month, not necessarily the selected day's month. ‹ › there
       change only the shown month, never the selection.
     - **Collapsing** by selecting a day shows that day's week. Collapsing without a selection
       (the header or the chevron) keeps the visible week when it touches the shown month;
       otherwise it shows the week holding the shown month's 1st.
     - **Today** selects today and shows its week (compact) or month (expanded).
     - Coming back from Journey Detail restores all three as they were.
3. **Day heading + totals**: "Today · 11 Nov" (`JourneyDayHeader`), then `JourneyStatsBlock` with
   the day's sure, driven totals (distance, drives, driving time = moving time, D2). When the day
   has only pending or passenger journeys, the block shows zeros only after a successful read and
   the journeys below explain themselves with their marks (D3; see Decision Q3).
4. **Content**, chosen from the loaded day:
   - **One journey** (R1): `JourneyHeroCard` in a compact **Day variant**, never Explore's full
     180 pt hero (Explore's hero is unchanged). The route preview about 120 pt (or the compact
     "No route to show" panel), then the time range "08:12 – 15:40" (start–end in the drive's own
     zone, "+1" when it ends after midnight) with the recording source's symbol, the title, and one
     line of distance · duration; the car and the end place only when known; the existing Needs a
     look / Passenger marks. No "Latest drive" label, no climb (Q7), and no figure the totals block
     above already states for the day beyond the journey's own distance and duration. One journey
     may be a 300 km road trip or a 4 km commute: the variant is the same. Taps open Journey Detail.
   - **Several journeys**: `JourneyCompactCard` per journey, oldest first (D1); its line already
     carries distance · duration · start time, source symbol and marks. No connectors, no gaps (D5).
   - **None**: a short note (below).
5. Pull to refresh reloads the day and drops the month cache, as today.

### Empty notes (never while loading, never after a failure)

| Case | English | Notes |
|---|---|---|
| Today, no drives, journal has drives | "No drives yet today." + "Last drive: Sun, 9 Nov ›" | the link selects that day |
| Past day, no drives | "No drives recorded." (+ the same link when an earlier day has drives? Q4) | |
| Empty journal | "Your driving story starts here." / "Your driving days will light up as you record journeys." | kept from Activity |
| Failed read | error + Retry | as today |

Vietnamese is written as native copy for the same intent (copy-and-localization.md), reviewed by
the owner.

### State and architecture

- **`JourneyDayViewModel`** (new, `Features/Journeys/ViewModels/`), `@Observable`, injected
  `journeyRepository`, `vehicleRepository`, `now: () -> Date`, `calendar: () -> Calendar` (read
  fresh, see Calendar changes). Owns: `selectedDay`, `isExpanded`, `shownWeek` (start of the week
  on screen), `shownMonth` (expanded), `monthCache: [Date: JourneyActivityMonth]`, the day's
  `journeys`, `details`, `summary`, `latestDrivingDay`, `state`. Generation checks on every load (an
  answer after an `await` belongs to its request).
- **`DayCalendar`** (new, pure, `nonisolated`, `Core/Journal/`): week start for a day, the seven
  days of a week, the months a week touches, the next/previous week, whether a day is selectable,
  and the indicator level for a day from the cached months. All with an injected `Calendar` and
  `now`; no `Date()`, no 86 400 s arithmetic.
- **`JourneysViewModel`** becomes Explore's model: the Activity members leave it
  (`activityMonth`, `selectedDay`, `activityDays`, `leadingDays`, `weekdaySymbols`,
  `picksDayOnLoad`, `chosenDay`, `journalCount`, `ActivityEmptyContext`, the activity branch of
  `load()`, `listInterval`'s day branch). It is not renamed (churn across tests and callers for no
  behaviour).
- **`JourneyDisplayMode { explore, day }`** with the saved value migrated on read: `list` →
  `explore`, `activity` → `day`, written back once. The picker and its menu fallback stay as
  they are; only labels and tags change. The mode stays owned by `JourneysViewModel` (it is the
  tab's state) and saved as today.
- **Ownership:** `MainTabView` creates `JourneyDayViewModel` beside `journeysModel` (one small
  hunk) and passes both to `JourneysView`; models live for the session, so going to Journey Detail
  and back keeps the date, the calendar state and the data. The scroll keeps its place because the
  Day scroll view stays in the navigation stack (`.id(mode)` changes only with the mode).
- **Loading:**
  - Day: `journeys(in: dayInterval, before: nil, limit: Int.max)` (a day is small; the list query
    is newest first, Day reverses it), then `details(for:)` and `vehicles()`; totals from
    `statistics.summary(in: dayInterval)`, the same aggregate as everywhere (no Swift-side sum that
    could drift from Explore).
  - Indicators: `statistics.month(_:calendar:)` per month, cached by month start; a week across two
    months loads both. Paging to a week whose months are not cached loads them; the strip shows the
    numbers at once and the marks when they arrive (never a false "no drives" mark: a day whose
    month is not loaded shows no mark and is not announced as empty to VoiceOver).
  - Latest day with drives (D4): see Decision Q1.
  - Reload only when `AppState.journalRevision` changed, the day changed, or pull to refresh;
    the month cache is dropped on a revision change.
- **Calendar changes:** the model reads the calendar through a function returning
  `Calendar.autoupdatingCurrent` in the app (a fixed calendar in tests). On
  `NSCalendarDayChanged`, `NSSystemTimeZoneDidChange`, `NSCurrentLocaleDidChange` and on return to
  the foreground: rebuild the week and caches; if the selection was today (not chosen by the
  person), it moves to the new today; a chosen day stays.
- **DST:** days come from `calendar.dateInterval(of: .day, for:)` (23 h or 25 h days included);
  weeks from `dateInterval(of: .weekOfYear, …)` and `date(byAdding: .day/.weekOfYear)`.
- **Performance:** a week page reads at most two cached month aggregates; a day reads one indexed
  range plus one details query; route images come from `JourneyMapSnapshotService` (no live map).
  No raw tracks (D11). Nothing here scans the history; the latest-day lookup is one `LIMIT 1` row.
  No performance claim is made without a measurement; the 2000-drive sample journal is the check
  (`-carodo.sampleJournal 2000`).

### Accessibility

- VoiceOver: each strip cell is a button "Sunday, 9 November 2026, 2 drives, 34 km" (value from
  the cached month; nothing while unknown), selected trait; future cells disabled. Swiping weeks
  has accessibility actions "Previous week" / "Next week" (`accessibilityScrollAction` or custom
  actions), so paging never needs a gesture. The header announces the expanded state.
- Dynamic Type: at accessibility sizes the week strip cannot hold seven cells; compact becomes a
  day stepper "‹ Sun, 9 Nov ›" and expanded the existing vertical list of past days (as Activity
  today). See Decision Q5.
- Differentiate Without Color: the mark shows the drive count, as the heatmap does.
- Reduce Motion: expansion cross-fades; paging is the system scroll.

## Phases

Each phase ends with `task format`, `task lint`, `task warnings`, `task test`. Nothing is committed
until the owner has reviewed the screenshots (UI still being iterated); then one commit per finished
outcome, staged by path (`MainTabView.swift`, the String Catalogs and `docs/operations/setup.md`
are shared with other sessions: stage by hunk).

### Phase 1 — specifications, naming and state architecture

- `docs/specs/journeys.md`: Header (Explore / Day), List → Explore (wording only), Activity → **Day**
  (this plan's Design), Days: device calendar stated as the V1 rule, recorded zone moved to
  "Not built" with what it needs (a padded window regrouped by `trips.time_zone`, and the month
  aggregate grouped the same way).
- `docs/data-model.md#time`: the *day* is the device calendar today; the recorded-zone day is
  deferred (links journeys.md). Fixes the conflict found by the audit.
- `docs/operations/setup.md`: `-journeys.displayMode explore|day` (old values still read);
  `-carodo.debugDay yyyy-MM-dd` (Day opens on that date) and `-carodo.debugDayExpanded YES`
  replace `-carodo.debugMonthPicker`.
- Code: `JourneyDisplayMode` rename + migration; `DayCalendar` (pure) with tests;
  `JourneyDayViewModel` skeleton (selection, visible week, header month, expansion, caches, loads,
  generation checks; R2 rules); `latestDrivingStart()` (Q1);
  Activity members removed from `JourneysViewModel`; `JourneysView` switches between Explore and a
  new `JourneyDayView`. Catalog keys `Journeys.modeExplore`, `Journeys.modeDay` replace
  `modeList`, `modeActivity`.

### Phase 2 — week strip and expandable month calendar

- `JourneyWeekStrip` (new): horizontal `ScrollView` of week pages (`LazyHStack`,
  `.scrollTargetBehavior(.paging)`, `.scrollPosition(id:)` on the week start), a window of weeks
  that grows as the person pages back; no week after the current one.
- `JourneyActivityCalendar` takes values instead of `JourneysViewModel` (`days`, `leadingDays`,
  `weekdaySymbols`, `selected`, `today`, `onSelect`) so Day hosts it inline; `JourneyMonthNavigation`
  becomes the inline header (the `MonthYearPicker` popover leaves; `MonthYearPicker` itself is
  deleted if nothing else uses it).
- Expand / collapse, Today, month paging, selection collapsing to the week; haptics as today
  (selection tick on a day or month change).

### Phase 3 — daily statistics and adaptive journey presentation

- Day heading + `JourneyStatsBlock` (day aggregate).
- One journey: `JourneyHeroCard` gains a style (`.latest`, Explore's, unchanged; `.day`, R1) that
  picks the map height and the leading line; Explore's call site is untouched.
- Several journeys: `JourneyCompactCard`, oldest first.
- Long-press Delete as on Explore (the same confirmation), so a journey can be removed from either
  mode. See Decision Q6.

### Phase 4 — navigation, empty states, accessibility and visual polish

- `NavigationLink(value: AppRoute.journey(...))` for every journey; detail models built as today
  (`canExplorePoints` kept).
- The three empty notes and the latest-day shortcut; the failure state with Retry.
- Calendar change, zone change, midnight and foreground handling.
- VoiceOver labels and actions, accessibility-size layouts, Differentiate Without Color, Reduce
  Motion. Light and Dark from tokens only (Charcoal, Ivory, Stone, Copper as accent).

### Phase 5 — tests and simulator verification

Unit tests (`CarodoTests/`):

- `DayCalendarTests`: week start for first weekday Sunday and Monday (en_US, vi_VN); a week across
  two months (28 Oct – 3 Nov 2026) and across a year (28 Dec 2026 – 3 Jan 2027): its seven days,
  the months it touches (both loaded), the header month with and without the selected day in it; previous/next week; future days not selectable; DST weeks in
  America/New_York (2026-03-08 23 h, 2026-11-01 25 h) give seven days with right intervals; a zone
  change moves "today".
- `JourneyDayViewModelTests`: swiping weeks or months never changes the selected day; expanding
  opens the browsed month (a week across a month or a year boundary); collapsing returns to the
  visible week or the shown month's first week; selecting in the month collapses to its week;
  opens on today with no drives; latest-day shortcut present / absent;
  one vs several journeys, oldest first; totals exclude pending and passenger while the list shows
  them; marks exclude them; a stale request never replaces a newer day; a revision change drops
  the cache, an unchanged one does not reload; midnight with today selected moves to the new day,
  a chosen day stays; failure shows no empty note; drive across midnight sits on its start day.
- `JourneysViewModelTests`: the preference migration (`list` → explore, `activity` → day, unknown
  → explore); Explore unchanged after the Activity code leaves.
- `JourneyActivityTests` / `JourneyStatisticsServiceTests` kept green (month aggregate unchanged).
- `LocalizationTests`: new keys in English and Vietnamese with comments; removed keys gone.

Simulator (by UDID, `-carodo.sampleJournal 2000`, Light and Dark, `AX3`-sized Dynamic Type,
Vietnamese), screenshots of:

- today with the single long drive (one-journey layout, ≈ 150 km);
- a weekday with commutes and errands (several journeys);
- a weekend out-of-town day (two long legs);
- a quiet past day; today with no drives (shortcut); an empty journal;
- the expanded month; a week across two months; the accessibility-size stepper;
- Day → Journey Detail → back: same date, same calendar state, same scroll, no spinner.

VoiceOver run on the simulator (Accessibility Inspector) for the strip, the expanded calendar and
the content. DST and midnight are proven by unit tests; a device check of midnight with the app
open is listed as still required.

## Acceptance criteria

- The picker reads Explore / Day (EN and VI); a saved `list`/`activity` opens the matching mode.
- Day opens on today; future days are never selectable; the strip pages whole weeks starting on the
  locale's first weekday; the header expands the month calendar inline and selecting a day
  collapses to its week.
- Marks and totals count only sure, driven journeys; the list shows every journal journey of the
  day, oldest first, with their marks.
- One journey shows the prominent summary, several show compact entries, none shows the note for
  its case; never a note while loading or after a failure.
- Every journey opens the existing Journey Detail; returning keeps date, calendar state and scroll
  with no reload when the journal did not change.
- No raw track is read by Day; no schema, API, recording or sync change; Explore behaves as before.
- `task lint`, `task warnings`, `task test` pass; screenshots as listed.

## Decisions (answered 2026-11-11: every recommendation accepted)

- **Q1** — a new read `JourneyRepository.latestDrivingStart()`: the newest sure, driven
  journey's start (one `LIMIT 1` row on `trips_on_journal`; a protocol method, no schema change).
- **Q2** — no lower bound on paging back; weeks load lazily.
- **Q3** — a day with only pending or passenger journeys shows the totals at zero above them.
- **Q4** — the latest-day shortcut only on today; a past empty day says "No drives recorded."
- **Q5** — accessibility sizes: compact is a day stepper "‹ Sun, 9 Nov ›", expanded the vertical
  list of past days.
- **Q6** — the same long-press Delete as Explore, one shared confirmation.
- **Q7** — no climb on Day's one-journey card.
- **R1** — the one-journey card is a compact Day variant of `JourneyHeroCard` (Design, Content).
- **R2** — visible week, selected day and header month are separate (Design, Calendar).
- **R3** (owner, 2026-11-11, mockup `design/mockups/journeys/journeys-day-v1.png`): the compact
  week strip is Day's default and the calendar stays small (Day must not spend its space on a
  calendar or repeat Explore). Header "November 2026 ⌄" leading, a **Today** pill trailing; the
  selected day is a **solid Copper cell** (Charcoal content, design-system "Which copper"), days
  with drives carry a small Copper dot; the day's label ("WEDNESDAY · 11 NOVEMBER", Copper caps)
  sits inside the totals card; several journeys are rows in one container with a Copper time
  range ("07:02 – 07:23"), title, km · duration and a thumbnail. Out of V1: the "2 stops" line and
  photos on the one-journey card (raw tracks, D11; Memories do not exist), the timeline
  connectors and "Coffee break" / "Lunch" lines of `journeys-day-v1-sample.png` (D5; a stop is
  never an activity). Future days never carry a dot (the mockup's 13 and 15 are a drawing slip).

## Risks and trade-offs

- **Scope**: the inline month calendar and the week strip together are most of the work; the strip
  paging with lazy month aggregates is the part most likely to show stale or late marks. Tests
  cover marks arriving after the numbers.
- **Shared files**: `MainTabView.swift`, the catalogs and `setup.md` are edited by other sessions
  (Feed, Places); hunk staging and a rebuild before commit.
- **Complexity budget**: `JourneysViewModel` shrinks (Activity leaves), `JourneyDayViewModel` and
  `DayCalendar` are new; target each under the budget in `docs/architecture.md#complexity-budget`.
- **Not in V1, and why**: between-drive gaps (D5, they infer places), stops on Day (raw tracks,
  D11), a day map of all routes (a new snapshot request shape; worth it once Places/Memories
  shape the day), recorded-zone days (D6, every date query moves at once).

## Device checks still required after the build

- Midnight with the app open on Day (selection moves to the new today).
- Changing the device zone while the app is in the background.
