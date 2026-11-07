# Journey V2.2: identity, context and story

Order agreed with the owner on 2026-11-06. Each step lands in `carodo-ios/docs/specs/` when built
(`journey-detail.md`, `journeys.md`, `journey-editing.md`, `vehicle-detection.md`); this file keeps
only the order, the state and what is still open.

| Step | Scope | State |
|---|---|---|
| **V2.2A.1** Journey Identity & Context | Who travelled, how, in which vehicle: Journey Context on the detail page, its editor "Your trip", the recording-source symbol, passenger wording, the `railConf` shadow score | Built 2026-11-06, uncommitted; device checks open (below) |
| **V2.2A.2** Adaptive Elevation | Show the elevation card only when it means something and its data is trustworthy | Done 2026-11-07 (uncommitted); device checks below |
| **V2.2A.3** Provinces Crossed | Boundaries crossed, their order, an editorial presentation | Built 2026-11-07, uncommitted; needs a real inter-province drive (below) |
| **V2.2A.4** Contextual Summary | Verified facts only, a deterministic fallback, localization | Later |
| **V2.2B** Intelligent Journey Story | Apple Foundation Models, cache, invalidation and fallback | Later |

## V2.2A.1: the three questions (decided)

1. **Who travelled?** Driver or passenger; a pending Auto Mode drive asks "Were you driving?" Yes / No.
2. **In what?** From the vehicle when the person drove (Kia → car); unknown with "Not specified";
   not asked for a passenger (only whether the person drove matters, like the Driving Focus).
   Metro: the shadow `railConf`, labelled by testers through Developer → Report, before any rule.
3. **Which vehicle?** Chosen in the editor; Auto Mode's guess is the last-used vehicle, linked car
   audio is sure. No inline "Right vehicle?": the row is tapped to change it.

No new confidence engine, no schema change; Movement and Trip confidence are the existing GPS
engine and its `conf=` shadow scores.

## Still open from V2.2A.1

- Device checks: tap the Journey Context row and its editor; "Delete trip recorded by mistake" once
  the sheet has closed (sure and pending); Yes / No on a real pending drive; editor height with a
  large text size and four vehicles; Dark Mode.
- Backlog, outside the brief: "My other vehicle" from an answer, the "Add your motorbike?" hint,
  one-tap answers on the Journeys row, the parked-spot rule (vehicle rule 3).
- Metro labels from colleagues who ride it (install a build on their phones).
- Titles: the English part-of-day fallback still says "drive" for a passenger trip ("Morning
  drive"); Vietnamese is neutral.

## V2.2A.2: Adaptive Elevation (built 2026-11-06)

Owner decisions: GPS-only noise level 10 m (barometer stays 3 m); thresholds as proposed
(barometer 25 m range + 30 m change, significant 150 m; GPS 40/50/200); steepest grade removed
from the UI (still computed). Result in carodo-ios `docs/specs/journey-detail.md` (item 6).

Still open:
- A drive through real hills (barometer) to tune the thresholds: today's 14 city drives are all flat.
- One GPS spike of 50 m+ on a GPS-only drive can still make it "meaningful" (no spike filter).
- Polish (2026-11-06, same day): the card became a terrain story (character + one cumulative figure
  + bare profile); the sheet adds start-to-finish and a line on cumulative climb.
- Device check: the sheet at the large detent, Dark Mode (the simulator shots stayed light),
  VoiceOver reading the card and the chart, drag-to-read on the sheet chart.

## V2.2A.3: Provinces Crossed (built 2026-11-07)

Owner decisions: Apple reverse geocoding, not a bundled boundary dataset (no CC attribution, works
worldwide; Apple already returns the 34 provinces, checked 2026-11-07); the owner's cell-based
adaptive bisection over `geocoded_cells` (35 km coarse span, 12 km split span); private places never
sent; a gap between two provinces hides the row; leaving Vietnam is kept as a country change, not
shown; derived on each visit, no schema change. Result in carodo-ios `docs/specs/journey-detail.md`
(Along the way) and `docs/privacy.md`.

Still open:
- A real drive across provinces (e.g. HCM → Đồng Nai or Tây Ninh): every recorded drive so far stays
  inside TP. Hồ Chí Minh, so the bisection has only run on synthetic tests. Count the lookups.
- Passport's "new province" still reads only the end cell's province; it could reuse these visits.
- Names outside Vietnam are cached in the device language at lookup time: a language change between
  lookups could split one state into two names.
- Device check: the row in Dark Mode, at a large text size, and VoiceOver order.

## Journey Detail loading (2026-11-07)

Done: one raw-track read per open (`detailTrack`, shared by the analysis, provinces and the trim
line), a session cache of derived results (`JourneyDetailCache`, 6 journeys), places read once, and
the routine line reading only each route's two end points in SQL.

Proposed, waiting for the owner (a `v1_initial` edit erases the DEBUG database on every dev iPhone):
a partial index `trips(merged_into_trip_id) WHERE merged_into_trip_id IS NOT NULL`. Each open looks
up joined parts by that column with a full table scan (EXPLAIN QUERY PLAN: `SCAN trips`). Best
bundled with the next schema change so the phones are wiped once. Measure the open on the iPhone
with a long drive before and after (perf audit follow-up).
