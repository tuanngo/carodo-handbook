# Journey Experience 02c — Day in two cases

Status: **Done** (carodo-ios `e7dec1b`, `0dda072`; route bends fix `9f21129`). Next: light polish (owner), then the weather slice once D-weather is decided. Parent:
[`journey-experience.md`](journey-experience.md) (D12, D18, D25, D27, D28), on 02b (carodo-ios `7d91aeb`).

## Changes

- **Totals** (`JourneyStatsBlock`): three figures on the page, value over label, no card (D18).
- **One drive:** the featured block (`JourneyFeature`, as Explore's latest drive): the time range
  as kicker, title, "302 km · 6 h 40 min", its status mark, the glyph over the faded map.
- **Several drives:** an open timeline (`DayJourneyRow`): a Copper dot on a hairline rail, the time
  range in Copper, the title with its place's colour, distance · driving time (and the car with
  several in the garage, `[Vehicle].namedOnRow`, shared with Explore), status mark; no card, no
  chevron. Behind it one drawing of all the day's routes in one frame, earlier drives quieter,
  fading toward the words and cleared around every line of text.
- **Featured block** now clears its glyph around its text too (a one-line title had the route
  through it).
- **Removed:** `JourneyHeroCard`, `JourneyMapThumbnail` and the snapshot service's per-journey
  images (`hero`, `thumbnail`): no list draws a map image now; the service keeps the Passport's
  Footprint and the featured drive's backdrop.

## Tests

`JourneyDayViewModelTests`: the day's drives share one frame (where the morning drive ended the
evening one set off), a drive without a route takes no part, tones rise toward the last drive.
Snapshot tests moved to backdrop and footprint requests.
