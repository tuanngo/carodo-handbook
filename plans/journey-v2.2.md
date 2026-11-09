# Journey V2.2: identity, context and story

Order agreed with the owner on 2026-11-06. Each step lands in `carodo-ios/docs/specs/` when built
(`journey-detail.md`, `journeys.md`, `journey-editing.md`, `vehicle-detection.md`); this file keeps
only the order, the state and what is still open.

| Step | Scope | State |
|---|---|---|
| **V2.2A.1** Journey Identity & Context | Who travelled, how, in which vehicle: Journey Context on the detail page, its editor "Your trip", the recording-source symbol, passenger wording, the `railConf` shadow score | Built 2026-11-06, uncommitted; device checks open (below) |
| **V2.2A.2** Adaptive Elevation | Show the elevation card only when it means something and its data is trustworthy | Done 2026-11-07 (uncommitted); device checks below |
| **V2.2A.3** Provinces Crossed | Boundaries crossed, their order, an editorial presentation | Built 2026-11-07, uncommitted; needs a real inter-province drive (below) |
| **V2.2A.4** Contextual Summary | Verified facts only, a deterministic fallback, localization | Done 2026-11-07 (carodo-ios `59a4ff2`, `a86ec30`); device checks below |
| **V2.2B** Intelligent Journey Story | Apple Foundation Models, cache, invalidation and fallback | Parked 2026-11-07: research below; model text off (`NarrativeModelGate`) |

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

## V2.2A.4: Contextual Summary (built 2026-11-07)

Shipped in carodo-ios `docs/specs/journey-detail.md` (Summary) and ADR 0012: an adaptive summary,
one lead and at most one detail (region, significant terrain, much longer than usual, early or
late start), one selection for the template and the model, `trips.narrative_basis`. Owner
decisions: F1 the column in `v1_initial`; F2 no summary for a routine on its own; F3 three
provinces or a border lead over a significant terrain, two yield to it.

Still open:

- Device checks: `task ios:pull-db`, then reinstall (schema changed; the owner's call); an
  Apple Intelligence text in Vietnamese and English (answered in V2.2B below); a real
  inter-province drive and a mountain road.

## V2.2B: carried over (owner, 2026-11-07)

- **An on-device AI switch in Settings** (deferred from V2.2A.4). One preference in `AppState`
  (UserDefaults, like the appearance). Off: the background pass writes no model text, Journey
  Detail ignores a stored one and shows the template (no schema change; the stored text stays
  for when it is turned back on), and the garage's vehicle name uses Carodo's list only
  (`VehicleNameModel`). Both AI uses already work without the model, so the switch only gates
  those two points. Needs a Settings string (EN/VI), `settings.md`, ADR 0012 and tests for both
  states.
- Model wording quality; a check of the names in a model text; Vietnamese support tested on the
  device; asking a refused text again when the model updates.

## V2.2B: research so far (parked 2026-11-07)

Measured on the owner's iPhone with the DEBUG Developer → Narrative lab (carodo-ios `ef4131e` …
`d74d4a1`; `docs/specs/developer-mode.md`). The architecture stays: AI narrative with a
deterministic fallback (ADR 0012); `NarrativeModelGate` is off, so Journey Detail shows the
template and nothing is generated in the background (`be5fb69`, `8119e5b`).

What is known:

- **The instructions' language decides the answer's.** `JourneyPrompt` (English instructions and
  English fact phrases) answered in English 60/60 with Vietnamese asked, the app in English or in
  Vietnamese (the system is `vi-VN`). The pre-2026-11-07 prompt (v6, word for word) did the same.
  `LanguageModelSession` takes no locale. Instructions and facts written in Vietnamese: Vietnamese
  every time.
- **Quality:** the best prompt (`native`: instructions in the asked language, two worked examples,
  the facts as clauses) came level with the template, not above it (reading of 40 lines: same ~12,
  AI better ~3, template better ~5). It mostly copies the clauses; it dropped the supporting fact
  in 2–3 of 20; the passenger clause leaked ("Người dùng đi cùng, không lái."); the English example
  taught "A ride" for drives the person drove (5/20).
- **Production's check keeps nearly everything** (0 rejected of 40 at baseline). The lab's
  `ProposedCheck` (language, exact names, each fact said and none reversed, capital and full stop)
  caught most defects but not the two leaks above.
- With few facts per drive (region, terrain, much longer, start), the template already says them
  well: a tighter prompt only makes the model copy. Most of the owner's drives (8/9, in town) have
  nothing to say at all (V2.2A.4 by design), so the summary rarely shows.
- Latency ~0.6–0.9 s a line on the device; the first call ~1.6–2 s.

Open before reopening:

- Decide what the model would add that the template cannot (richer facts? a week/month recap?),
  or keep the template for v1.
- If continuing: no clause for the passenger (an instruction instead), examples that do not teach
  "ride", the two leaks in `ProposedCheck`, then a prompt that beats the template in ≥ 60 % of
  reviewed lines before it replaces `JourneyPrompt` and the gate opens.
- iOS 27: the narrator maps only `GenerationError`; the model now throws `LanguageModelError`, so
  a refusal would be retried every session (journey-detail.md, Summary).
- Whether routine drives should get any summary (owner noticed Journey Detail is mostly empty).
