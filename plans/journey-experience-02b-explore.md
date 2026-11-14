# Journey Experience 02b — Explore as an open editorial timeline

Status: **Built, waiting for the owner's review** (2026-11-14; uncommitted in carodo-ios). Approved to build (owner: "viết plan và làm luôn"); a screen change, so the
owner reviews screenshots before the commit. Parent: [`journey-experience.md`](journey-experience.md)
(D17, D23, D24, D28, D29, D30, D31), on 02a's route glyph (carodo-ios `bfaa4a4`).

## Outcome

Explore reads as a journal: no card around a journey or a day, no overview card, the latest drive
as a featured block over a faded map, and every other drive an open row: start time, title,
driving time, its route unboxed and sized by distance, its GPS distance.

## Existing behaviour (files read)

`Features/Journeys/Views/Explore/JourneysView.swift` (overview `JourneyStatsBlock`, `JourneyHeroCard`,
`JourneyListRowView` → `JourneyCompactCard` with a 56 pt `JourneyMapThumbnail`, `JourneyMonthHeader`,
`JourneyDayHeader`), `ViewModels/Explore/JourneysViewModel.swift` (pages of 20 finished to a whole
day, `rows`, hero left out of rows, `details` for titles and start marks, the hero's climb),
`DesignSystem/Components/JourneyCards.swift`, `Core/Journal/JourneyMapSnapshotService.swift`,
`JourneyHeroCard.swift` (also Day's one-drive card until 02c).

## Changes

1. **Featured block** `JourneyFeature` (DesignSystem, shared with Day in 02c): a kicker line, the
   title with its start place's symbol, one figures line, the route glyph drawn large at the
   trailing edge (`RouteGlyphView`, `.art`), over the muted map (`JourneyMapSnapshotService`, a new
   `backdrop` image: the map only, framed so the glyph lies on its roads), at half strength, fading
   toward the text and the edges. Offline or before the image: the block without the map.
   Explore's latest drive: kicker "Latest drive · Today" (sentence case, "First drive" for the only
   one), "17:40 · 112 km · 2 h 12 min"; no climb (D13), no car or end place (mockup V9).
2. **Rows** `ExploreJourneyRow`: a time column (start time, secondary ink), the title with its start
   place's symbol over the driving time (moving time, as Day) and the status mark, the GPS distance
   as the trailing figure (value over unit); the route behind the row's trailing part, before the
   figure, sized by distance (`RouteGlyphMaker.scale`), spilling above and below, cleared around
   every line of text (`TextClearance`). No chevron, no tile, no recording-source symbol (detail
   only). A long press keeps Delete.
3. **Headers**: the day header adds "3 drives · 128.9 km" counting every driven, sure drive of the
   day, the latest included (`Journey.countsAsDriving`, Day's rule); the month header unchanged.
4. **Removed** from Explore: the overview card (the all-time read stays: it decides "First drive"),
   the hero card (Day keeps `JourneyHeroCard` until 02c), `JourneyCompactCard` (no other user).
5. **Glyphs** are made once per page in the view model (`RouteGlyphMaker`, off the main actor) and
   kept with the rows; the hero's with the hero.

## Tests

`JourneysViewModelTests`: day header counts (latest included, pending and passenger left out);
glyphs present for drawable journeys, empty otherwise. `RouteGlyphMakerTests`: the frame's centre
and side (for the backdrop). Snapshot service: a backdrop key differs from a journey's.
Opt-in perf: 2,000 synthetic journeys' glyphs (`CARODO_PERF=1`).

## Docs

`docs/specs/journeys.md` Explore section rewritten; `docs/design-system.md` Route glyph ("on
Explore"), and the featured block.

## Acceptance

Screenshots Light, Dark, Vietnamese, xxxLarge (supported, D31) on sample data; `task lint`,
`task warnings`, `task test`. Device check: scrolling a long journal on the iPhone.
