# Place card: names on the Map, the card, its visits

Status: Approved (2026-11-19). Steps 1–3 done on `feat/map-look` (carodo-ios `d213e19` names, `70ee211` card, `0a21202` naming from the card; simulator only). The card's figures come from the visits page already read (no `firstAt` was needed). After the owner's first look (2026-11-19): the card fits its content on the sheet's own glass ground, says "A place you stopped" and where the place is when Apple named nothing, and one sheet serves the group list and the card. Step 3 gives the card Find Nearby Places and Rename. Open: Save place (a detected place made a saved one) and Edit place, which touch how two places on one spot are kept; the owner decides.
[`design/mockups/journeys/place-card.png`](../design/mockups/journeys/place-card.png) (source
`design/mockups/source/place-card.html`). Follows `map-layers-legibility.md` step 4 (the Places
switch, carodo-ios `55edceb` on `feat/map-look`); built on that branch or on main once merged.

## Problem

Places will be used to find a stop again, and the Map shows them badly for that:

- A place says nothing until tapped: the marker is a symbol, the name only in the callout.
- The callout is MapKit's, with SwiftUI lines hosted inside (`PlaceCalloutAccessories`,
  `CalloutHost`). It opens oversized: reproduced on the simulator 2026-11-19, a blank band above
  the title row, the callout three times its height. The lines are measured (`sizeThatFits`) before
  the view is in a window, and MapKit lays the callout out from that. Two earlier sizing fixes are
  in the code's comments (a blank screen-tall callout; accessories lost on reopening).
- The drives at a place are two steps away: the callout's button, then the visits page.
- A detected place cannot be given the person's own name: only an Apple point of interest can be
  picked (Find Nearby Places), and that name is Apple's, cached 7 days.

## Today (audited 2026-11-19)

- Markers: `AtlasPlaceView` (`Features/Map/Views/AtlasPointMarkers.swift`), an image per kind from
  `MarkerImageCache`; detected places cluster (`AtlasPlaceClusterView`), saved ones never;
  `displayPriority` by visits (step 4).
- Names: `Place.shownName` (`Core/Formatting/PlaceLabel.swift`) already prefers `name` (the
  person's) over `poi.name` (Apple's, from `POINameCache`); the marker's label falls back to the
  cached area, then the category, then "A place you stopped" (`MapAtlasViewModel.placeMarker`).
- Category: `place.poi?.category`, Apple's `MKPointOfInterestCategory` raw value, when Apple matched
  a point of interest; `POICategoryStyle` maps 13 of them to a symbol and a name, the others draw a
  pin with no kind. Never stored (data-model.md, Place names).
- Offline: the same callout, never MapKit's default; only Apple's name and the address may be
  missing. Visits and figures are the device's own.
- Visits: `PlaceVisitSummary` (count, latest, its zone) per place, computed off the main actor
  (`MapAtlasViewModel.visitSummaries`); the visits page (`PlaceVisitsPage`, `AppRoute.placeVisits`)
  lists every arrival, a row opens `AppRoute.journey`.
- `places.name` is documented as the person's own only (places.md, Naming); a detected place's
  is NULL today. No schema change is needed to store one.

## Decided (owner, 2026-11-19)

- **C**: names under the markers on the Map, and a tap opens a place card (a sheet) in place of
  MapKit's callout.
- Figures: **Visits · Last · First**.
- The card lists the **three** latest visits, then "All N visits".
- **Rename (a)**: a detected place stays detected with the person's own name in `places.name`.
  Only the name is edited there (type, radius, privacy stay in the place editor).
- Open in Maps: later (nice to have), not in this plan.

## Proposal

### 1. Names under the markers

- At street level (the map under about 3 km across) each place's marker carries its name under it,
  in the marker's image (one image per name and look, `MarkerImageCache`), the same text VoiceOver
  reads. A group carries its first member's name (by `displayPriority`, then visits) and
  "+N more". Wider out, markers only, as today.
- The label shares the marker's `displayPriority` and collision frame, so MapKit drops a once-visited
  place's name and marker together rather than letting labels overlap.
- A name is at most one line, cut short at about 18 characters (the card shows it whole).
- Light and Dark (Discovery's dark map included): the label has a halo of the map's ground, as
  Apple's labels do.

### 2. The place card

- A tap on a place (or a row of `PlaceGroupSheet`) opens the card: a sheet with a medium and a large
  detent over the Map, in place of MapKit's callout. The tapped marker grows (selected look) and the
  map slides so it stays above the card. Closing the card deselects it.
- Medium: symbol, name, what it is · area (a Private area badge for a private saved place); the
  three figures; the three latest visits (date · time, "From <origin> · km · duration"), each opening
  that journey's Journey Detail (`AppRoute.journey`); "All N visits"; Rename and Save place for a
  detected place, Edit place for a saved one.
- Large: every visit, newest first (the visits page's content), so the card and the page are one
  surface on the Map. The visits page stays for the places reached from elsewhere (Journeys).
- Figures: `PlaceVisitSummary` gains the first arrival (`firstAt`), computed in the same pass.
  Home and Work say "Arrivals" instead of "Visits".
- Unknown is not zero: the journal unreadable hides the figures and the list (no "0 visits").
- Removed from the Map tab: `PlaceCalloutAccessories` and `MapCalloutFit` usage there. Journey
  Detail's map keeps its callouts for now (its oversize bug is recorded as debt, below).

### 3. Rename a detected place

- Rename on the card opens one text field on the card. It starts **empty**; Apple's name, or the
  area, is only its placeholder. Save writes `places.name` through `PlaceRepository.save` (sets
  `ck_pending`, syncs to iCloud as every place edit). The name then wins everywhere `shownName` is
  read: the marker, the card, journey titles, the visits page, offline.
- Saving text equal to the Apple name shown stores nothing: Apple Map Data is cached only
  (ADPLA Attachment 6 §2.5, data-model.md); the person's own typing is theirs. Clearing a name
  returns to Apple's, the area, or "A place you stopped".
- The place stays `source = detected`: its marker, clustering and Discovery rule are unchanged.

## Non-goals

- Open in Maps (Apple Maps directions to the place).
- Journey Detail's point callouts (same MapKit callout; a later pass).
- A place search on the Map.
- Changing how places are detected or named by Apple.

## Files

`Features/Map/Views/AtlasPointMarkers.swift` (label in the image, cluster label),
`Features/Map/Views/AtlasMapView.swift` (selection → card, no callout),
`Features/Map/Views/MapAtlasView.swift` (the sheet), a new `Features/Map/Views/PlaceCard.swift`,
`Features/Map/ViewModels/MapAtlasViewModel.swift` (the card's model, rename),
`Core/Domain/Places/PlaceVisitLog.swift` (`firstAt`), `Resources/Localization/Map.xcstrings`,
`Previews/Map/PlaceCard+Previews.swift`. Docs: `docs/specs/navigation.md` (Places on the Map),
`docs/specs/places.md` (Naming a detected place), `docs/design-system.md` (Map markers, the place
callout row becomes the card).

No schema, API, permission or dependency change.

## Acceptance

- Street level: every shown place has its name under it; colliding ones give way by priority with
  their marker; nothing overlaps. Wider out: markers only.
- A tap opens the card at the right size on the first tap, Light and Dark, xxxLarge, Vietnamese.
- A visit row opens that journey's Journey Detail; back returns to the Map with the card.
- Rename: a typed name shows on the marker, the card and journey titles, survives a relaunch and
  offline; an untouched Apple name is not stored (test: `places.name` stays NULL).
- Tests: `firstAt`; the label and cluster label; rename stores the typed name, not Apple's
  unchanged, and clearing returns to the fallback; the card's unknown state.
- Device: the Map at rest under 1 % CPU with labels on (Instruments), panning not slower than before.

## Steps (one commit each, proven)

1. Names under the markers.
2. The place card (callout removed on the Map tab), with `firstAt`.
3. Rename on the card.

## Debt to record

- Journey Detail's callouts share the oversize-on-first-open bug (`CalloutHost` measured before the
  view is in a window); fixed when that map gets the card or a measured host.

## Handoff: Save place and Edit place (2026-11-19, not built)

Left for a new session. Analysis and a recommendation, for the owner to decide.

**What exists.** `places.source` is `suggested`, `added` or `detected`; `name` is the person's own
only. Rename (step 3) already gives a detected place a lasting name without making it saved. The
place editor (`PlaceEditorView`, Places feature) edits radius, type (role or Private area), name and
Private, and is opened only from Settings → Places. Every saved place's circle is an Auto Mode
geofence: iOS watches 20 regions per app, one is the parking spot, so the **oldest 19** saved places
are watched (carodo-ios `docs/tracking.md`, Place geofences).

**Should a detected place be saveable from its card? Yes, but as a promotion, not a copy.**
- Saving makes sense when the place has a role (Home, Work, School, Family) or must be private:
  roles name drives ("Home → Work"), privacy hides route ends. A name alone no longer needs it
  (Rename).
- A copy (a new `added` row on the same spot) is the wrong shape: two circles on one spot, visits
  go to the smaller one (`PlaceMatch`), the detected marker sits under the saved one, and the group
  lists both. The duplicates seen in real data (three "X. Hàm Thuận Bắc") show the cost already.
- **Recommended: promote in place.** The same row (same id, so its visits, journey titles and Apple
  `poi_id` stay) changes `source` from `detected` to `added`, with the role, name, radius and
  privacy chosen in the editor. Its marker becomes a saved marker on every layer, never grouped.
- Cost to name to the owner: a promoted place takes a geofence slot. With the oldest 19 watched,
  promoting many stops leaves new ones unwatched, never Home or Work if those were saved first. The
  editor could say so past 19 (a line, not a block).
- Detection must not re-detect a promoted spot: it already skips cells inside an existing place
  (`docs/specs/places.md`, Finding frequent places); check that holds for a promoted row.

**Edit place for a saved place:** the same editor on the existing row. No open question.

**How to open the editor from the card** (a feature never shows another's views): a route the App
layer resolves, e.g. `AppRoute.placeEditor(Place.ID)` pushed on the Map tab's stack, or the
`AnyView` builder pattern already used for Find Nearby (`AppDestination.Models.placeNearbySheet`).
The editor needs a "promote" entry: `PlaceEditorModel(existing:)` with a detected place, saving it
as `added` with the same id. Persistence: a change of `source` on one row, no schema change; iCloud
syncs it as any place edit (check the conflict rule for a row whose `source` changed on one device).

**Decisions for the owner:**
1. Promote in place (recommended) or copy.
2. Which entry: the card's "Save place" for a detected place only, "Edit" for a saved one.
3. Whether the editor warns past 19 watched places.

**Also seen, separate from the card:** several detected places on one spot, all but one with no
visits (each end goes to the smallest circle holding it). Worth a look at merging detected places
that overlap, in the detection code, not the Map.
