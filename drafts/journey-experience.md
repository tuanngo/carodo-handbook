# Journey Experience — concept

Status: **Draft** (owner, 2026-11-14). Not Ready: the decisions in
[`../plans/journey-experience.md`](../plans/journey-experience.md) (Owner decisions) are open.
When a slice ships, its rules land in carodo-ios `docs/specs/journeys.md`, `journey-detail.md` and
`docs/design-system.md`; this draft stays the concept they follow.

## Product vision

Carodo does not only record drives. It helps a person look back on the places they have been.

Three screens answer three different questions, and none repeats another's answer:

| Screen | Question | What it is |
|---|---|---|
| **Explore** | Where have I been? | A discovery journal along time: the journeys, the ground covered and what was worth remembering. |
| **Day** | What happened that day? | How a day went: how many drives, when, where to, total distance and time. |
| **Journey Detail** | How did I travel? | The full log of one drive: route, replay, speed, elevation, weather, stops, events. |

## Design principles (reviewable)

Each is a check a screenshot review can pass or fail.

1. **Editorial, not dashboard.** Information reads as a travel journal, not an endless KPI board:
   no screen is a stack of figure cards.
2. **Meaningful hierarchy.** An ordinary journey is a compact, quiet row; only something worth
   noticing (a discovery) is raised.
3. **No repetitive map thumbnails.** Lists draw the Route Glyph; a real map appears only where it
   earns its place (Latest drive, Journey Detail).
4. **Content first.** No empty card, no discovery placeholder, no badge added to make a screen look
   full. Data not known yet is absent, never a skeleton.
5. **Carodo identity.** Charcoal, Copper, Ivory, Stone and the current design language. Never a
   social feed and never a fitness tracker. Explore is a private journal, not the Feed.
6. **Offline is complete.** With no network for days, Explore and Day are whole and good-looking
   from what was recorded: glyph, time, distance, titles from cached places.

## Route rendering — three styles

| Style | What | Where | Source |
|---|---|---|---|
| **Route Glyph** (the default in lists) | The drive's real GPS geometry, drawn without a map: north up, aspect kept, Copper stroke, start and end marked | Explore rows, Day timeline, anywhere a drive is a line in a list | the display route (`trips.route`), on device |
| **Contextual Map** | The route on a real map (Apple Maps) | Latest drive in Explore, Journey Detail | `JourneyMapSnapshotService`, live MapKit |

*Naming note:* the owner's working name was "Route Signature"; "Signature" is already the name of
the Copper route style on every map (`JourneyRouteDisplay.signature`, design-system "Route line
colours"), so this draft calls the list mark the **Route Glyph** (decision D15 in the plan).

### Route Glyph requirements

- Drawn from real GPS geometry, never a decorative curve (the 2026-11 mockup's curves are
  placeholders, not the target).
- The route's bounding box normalised into the glyph's square, aspect ratio kept, centred, with
  the same padding on every glyph; north up (unlike the Feed's `DriveShape`, which is turned on its
  own axis on purpose and must stay apart: ADR 0007).
- Simplified for its size: a 44–56 pt glyph needs tens of points, not the display route's hundreds.
- Drawn the Feed's way (a soft curve, a faint ribbon under a thin core) but on the real shape,
  with a small start ring and an end dot; large art fades toward the text. No place symbol inside a list glyph
  (owner, 2026-11-14: too small); the title carries the place.
- **Edge cases**, each with a defined look:
  - *very short* (under about 300 m of span): drawn at a minimum span, so a car-park shuffle is a
    small line in the middle, never a giant shape filling the box;
  - *no drawable route* (fewer than 2 points or under 50 m, today's `hasDrawableRoute`): a quiet
    neutral mark, never a made-up line;
  - *a loop* (end within a few tens of metres of the start): one combined end mark;
  - *several parts* (a GPS jump or an impossible gap): drawn as separate strokes, never joined
    by a straight line across the gap.
- Needs no network. Made once per route and size, kept in memory; cheap enough to need no file
  cache (to be measured, plan step 02a).
- Light and Dark, and readable at xxxLarge text (the glyph does not scale with text; the row
  around it does).

## Explore — Journey Discovery Journal

- Every journey stays: nothing ordinary is filtered out, infinite scroll as today.
- **Month** and **day** headers give the structure of time.
- **Open editorial timeline**: no card for a journey, none around a day, no rule beside it. A row
  reads *when · where · how long · what shape · how far*: the start time in a leading column, the
  title (with its place symbol) over the driving time, the route sized by distance, and the GPS
  distance as the trailing figure. The route has no frame: its own proportions, spilling into
  the space between rows and fading toward the title. Separation by space, not boxes or
  hairlines; no chevron. A day header counts every drive of the day, the latest included.
- **Latest drive** ("Latest drive", sentence case) opens the page as a featured block: title,
  figures and its route drawn large in the Feed's style over a faded map (the muted snapshot,
  fading toward the text; none offline). The same component shows a
  one-drive Day and "A journey worth remembering".
- A **Discovery Highlight** appears only when something notable is verified (a first visit, a new
  province, a milestone); never one per journey by rule.
- A **Journey Story** may later gather several drives (a road trip over days); it is a layer over
  drives, never replaces a drive, and is derived.

## Day — Daily Activity Timeline

- Keeps the foundation built in Day V1: week strip, month calendar, the day's totals.
- **One drive:** the featured block (as Latest drive), its time range as kicker.
- **Several drives:** no card; a **compact timeline** (a dot and a hairline rail at the edge, time
  range in Copper, title, distance · duration) over one frame that draws every route of the day
  together on their real geography, fading before the text.
- Journeys oldest first; each shows start–end time, title, distance and duration.
- No speed, elevation or weather: Journey Detail owns them.
- No Discovery Highlight in Day V2.
- A day with no drives keeps the whole calendar; the content area shows a light empty state, no
  false empty space.
- Later, real events (a fuel log, a break, a stop) may join the timeline, once their data source
  and time order are defined.

## Journey Detail

Keeps its role as the in-depth log (`journey-detail.md`); this concept only lets it reuse the
shared primitives (title, metrics, time range) and, where it helps, the Route Glyph.

## Shared component system

One presentation model, small primitives, and a separate composition per context: no single row
with a dozen booleans (`showMap`, `isTimeline`, `isCompact`, …).

```
Journey Experience
├── Shared primitives (DesignSystem)
│   ├── RouteGlyph
│   ├── JourneyTitle          (title with its start place's symbol)
│   ├── JourneyMetrics        (distance · duration; Detail adds the rest)
│   ├── JourneyTimeRange      (start; start–end with "+1"; full)
│   └── JourneyLocationLabel  (where it ended)
├── Explore
│   ├── LatestDriveHero       (today's JourneyHeroCard, Explore style)
│   ├── MonthSection / DayGroupHeader
│   ├── ExploreJourneyRow     (compact composition)
│   ├── DiscoveryHighlight
│   └── JourneyStoryCard      (future)
├── Day
│   ├── CalendarHeader, WeekStrip / MonthGrid, DailyStats   (built in Day V1)
│   └── DailyTimeline → DayJourneyRow (timeline composition)
└── Journey Detail            (existing)
```

| Component | Explore | Day | Detail |
|---|---|---|---|
| Journey row | compact | timeline | — |
| Route Glyph | yes | yes | may reuse |
| Title | yes | yes | yes |
| Metrics | distance + duration | distance + duration | full |
| Time range | start | start–end | full |
| Month header | yes | calendar header | — |
| Day summary | small, optional | daily stats | — |
| Discovery Highlight | yes | not by default | may link |
| Journey Story card | yes (future) | no | — |

Both rows read one value, the **journey row model** (title, start and end marks, glyph input,
figures, time range, status marks), built once by the view models from the journal read, so Explore
and Day can never word the same drive differently.

## Discovery enrichment — a capability, not a screen

Independent of Explore's UI: Explore only reads what it has produced.

| Layer | Data | Where it stands (audit 2026-11-14) |
|---|---|---|
| L0 Recorded | GPS, time, distance, stops | Built |
| L1 Derived | glyph, repeated routes, visited cells | Partly: route heat and Footprint cells exist in memory; `visited_cells` is reserved and unused |
| L2 Geographic | areas, provinces, notable roads, bridges, tunnels | Partly: `geocoded_cells` (ward → province), Provinces Crossed on Detail; no source for roads, bridges or tunnels |
| L3 Discovery | new territory, meaningful places, milestones | Partly: milestones (`badge_unlocks`) and first visits to places exist; no "new territory" store |
| L4 Story | multi-drive grouping, narrative | Future |

Rules:

1. Local derivation runs when a journey is saved or its data changes (trim, merge, a track from
   iCloud), as places and journey points do today.
2. Network enrichment (Apple's geocoder only) runs in the background, deferred on an expensive or
   constrained connection, within the existing per-run lookup budget.
3. Results are kept per journey with a rules version, so a rule change re-derives and a re-run is
   idempotent (the `places_version` / `points_version` pattern).
4. Older journeys are backfilled in batches, newest first, resumable.
5. Explore shows no loading placeholder for enrichment.
6. A discovery is shown only once its evidence is verified (a cached geocode, a saved place, a
   ledger entry), never guessed.
7. No AI-written story without geographic data behind every claim.
8. Enrichment never weakens offline-first: nothing in Explore or Day waits on it.

## Definition of done (for the whole concept)

- Explore scrolls smoothly with hundreds to thousands of journeys (measured: an opt-in test with a
  synthetic journal of 2,000 drives, iPhone, Release).
- Day changes day and opens the calendar without layout jumps.
- Explore and Day are visibly one family.
- The Route Glyph draws correctly from real drives, short and unusual ones included.
- No regression in Journey Detail or navigation.
- Offline shows every core figure.
- Enrichment is idempotent and resumable, and never duplicates a highlight.
- Days with none, one and many drives, and runs of busy days, each look finished.
- No location leaves the device except the requests already allowed and disclosed (Apple's
  geocoder, map tiles).
- Screenshot review of Explore and Day with short, long, repeated and mixed drives (Light, Dark,
  xxxLarge, Vietnamese).
