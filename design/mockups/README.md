# Mockups

These are the owner's visual explorations. **They are ideas, not specs.** They show a direction for look and feel, and any of them may be revised or dropped. When a mockup disagrees with the docs, the specs in [`../../../carodo-ios/docs/specs/`](../../../carodo-ios/docs/specs/README.md) and the shipped design system win. Turning an idea from here into the product needs a spec, or an ADR for a lasting decision.

## Browse by feature

Images are grouped by feature; editable HTML/JS stays together in [`source/`](source/) because the
boards share `first-run-kit.js`. File names are lowercase kebab-case. Existing dated approvals
below describe the review at that time, not proof that a board matches the current app.

- [`onboarding/`](onboarding/): Day 0, Day 1 and the first-car concept.
- [`drive/`](drive/): recording, Auto Mode and recording polish.
- [`journeys/`](journeys/): the list, detail, replay, trim and provinces.
- [`replay/`](replay/): the Replay video's frame.
- [`share/`](share/): the share card and its editor.
- [`garage/`](garage/): Garage, vehicle identity, showcase and editor concepts.
- [`passport/`](passport/): milestone and Passport concepts.
- [`feed/`](feed/): early Feed concepts.
- [`concepts/`](concepts/): cross-feature mood and visual direction.

## Previously uncatalogued explorations

These boards are retained as explorations; their presence does not establish approval or shipping status.

- [First-car concept](onboarding/your-first-car.jpeg)
- [Passport and Garage overview](garage/passport-garage-overview.png)
- [Vehicle identity with an emblem](garage/vehicle-identity-emblem.png)
- [Vehicle identity concept](garage/vehicle-identity.png)
- [Garage showcase concept](garage/garage-showcase.png)
- [Vehicle editor concept](garage/vehicle-editor.png)
- [Journey experience concept](journeys/journey-experience.png)
- [Journey Experience V2: Explore, Day, Route Glyph](journeys/journey-experience-v2.png) (2026-11-14, `plans/journey-experience.md`; source `source/journey-experience.html`)
- [Route ends: one mark everywhere](journeys/route-ends.png) (2026-11-14, `plans/journey-experience-02a-route-glyph.md` D32; source `source/route-ends.html`)
- [Journeys overview](journeys/journeys-overview.png)
- [Along the Way route variations](journeys/along-the-way-route-variations.png)
- [Four-province exploration concept](journeys/regions-explored-four-provinces.png)
- [Passport and Feed editorial headers](passport/passport-feed-headers.png) (2026-11-14, `plans/passport-tab-and-header.md`; source `source/passport-feed-headers.html`): three Passport directions, the Passport as a tab, the Feed, Journeys' Filter; P2 chosen and built
- [Milestones dashboard](passport/milestones-dashboard.png)
- [Passport milestones](passport/passport-milestones.png)
- [Warm Copper visual direction](concepts/warm-copper-ui-collage.png)

## Existing review records

| File | Shows | Status |
|---|---|---|
| [`drive-recording-spec.png`](drive/drive-recording-spec.png) | Drive recording: Start Drive button, recording panels | Visual target for [`drive-recording.md`](../../../carodo-ios/docs/specs/drive-recording.md) |
| [`journeys-dark.png`](journeys/journeys-dark.png) | Journey list (by month), trip detail, Driving Passport card; colour and contrast notes | Idea |
| [`journeys-light.png`](journeys/journeys-light.png) | The same three screens in light mode | Idea |
| [`journey-detail-conditions-dark.png`](journeys/journey-detail-conditions-dark.png) | Journey list and a detail panel with Driving Conditions (city / open road / highway) and an elevation chart; key UX decisions | Idea |
| [`journey-detail-fullmap-dark.png`](journeys/journey-detail-fullmap-dark.png) | Journey list and a full-map detail with Replay and continuous content | Idea |
| [`journeys-map-passport-dark.png`](journeys/journeys-map-passport-dark.png) | Journey list with a month map header, detail, Driving Passport with places and a driving calendar | Idea |
| [`journey-detail-replay-light.png`](journeys/journey-detail-replay-light.png) | Detail and Replay with a timeline scrubber, light mode; UX flow Journey → Detail → Replay | Idea |
| [`feed-draft-01.png`](feed/feed-draft-01.png), [`feed-draft-02.png`](feed/feed-draft-02.png) | Feed explorations | Idea (before the headline, shape and badge rules of 2026-11-03) |
| [`first-run-day0.png`](onboarding/first-run-day0.png) | Day 0, revision 3: Your first car with a title, the name, Car / Motorbike as drawn tiles and the colour (the wheel steps aside for the keyboard), the Garage as a carousel of vehicle cards with a drawing by body style and colour, the vehicle form, Settings → Units, the first-run Map with a standing Auto Mode button, four permission lines (source: `source/first-run-day0.html`) | Drawn 2026-11-03, revision 3; built 2026-11-03 |
| [`first-run-day1.png`](onboarding/first-run-day1.png) | Day 1: the Start panel (no, one, several vehicles; AX size), the compact recording panel with Undo and the vehicle pill, Journeys with one drive, the detail before and after place names (source: `source/first-run-day1.html`) | Drawn and built 2026-11-03 |
| [`auto-mode.png`](drive/auto-mode.png) | The Auto Mode sheet: off, running with a car-audio link prompt, all set (Dark), Set Up Automation steps, blocked without Always (source: `source/auto-mode.html`; spec `carodo-ios/docs/specs/auto-mode.md`) | Visual target, decisions 2026-11-03 |
| [`journey-trim.png`](journeys/journey-trim.png) | Trim as a video-editor timeline: **chosen** A with B's chips (figures with what the trim takes away in Copper, speed-coloured bar timeline, Starts/Ends with the old time struck through, chips After leaving Home · Leave out the walks · After the stop); explored: A Photos-style (map above, speed-profile timeline with two Copper handles, recommended), B the same with one-tap smart ends (leave out the walks, after a stop) and snapping, C full-screen map with the timeline in a glass card and a scrubbing playhead; the detail after a trim; largest Dynamic Type; open decisions (source: `source/journey-trim.html`; spec `carodo-ios/docs/specs/journeys.md`, Trim) | Drawn 2026-11-05; A + chips chosen 2026-11-05 |
| [`replay-video-frame.png`](replay/replay-video-frame.png), [`replay-video-built.png`](replay/replay-video-built.png) | What a Replay video shows beside the map, on real frames of the renderer (sample drive): three layouts (A top block, B card at the foot, C no surface), A in Light and Dark, English and Vietnamese, the opening and the arrival; then frames of the build (source: `source/replay-video.html`, frames in `source/replay-video/`; plan `plans/cinematic-replay.md`, W4b) | Drawn 2026-11-13; **A chosen** and built 2026-11-13 |
| [`recording-polish.png`](drive/recording-polish.png) | Recording polish: the Map while recording (live line, "Recording · time · distance" chip, Auto Mode button marking its own drive), the stop and car-audio countdowns, the source in the panels (by hand · Auto Mode · Shortcut), paused, the toast after an automatic end, the 24 h dropped-drive line with Keep it, the source filter and detail line, largest Dynamic Type (source: `source/recording-polish.html`; plan `plans/recording-polish.md`) | Drawn and approved 2026-11-03 |

## Where the ideas differ from the current docs

- **Navigation.** The mockups use a bottom tab bar (Drive · Map · Journey · Passport/Profile). The decided navigation is Map · Journeys · Feed with a floating Start Drive button ([`drive-recording.md`](../../../carodo-ios/docs/specs/drive-recording.md)).
- **Driving Passport** is now specified in [`../../../carodo-ios/docs/specs/passport.md`](../../../carodo-ios/docs/specs/passport.md):
  it opens from the avatar rather than a tab, and it has **no speed highlights**. The mockups'
  "Highest speed" is dropped (ADR 0007).
- **Driving Conditions and elevation** are now in the journey detail
  ([`../../../carodo-ios/docs/specs/journeys.md`](../../../carodo-ios/docs/specs/journeys.md)). They are measured as time per
  speed band (< 30, 30–60, 60–90, 90+ km/h) rather than "city / open road / highway", because the device
  records speed, not road type.
- **Brand.** The mockups' logo comes from the brand board. The locked mark is in [`../brand/`](../brand/brand.md).

Hand-drawn boards keep their HTML in `source/`; `source/render.sh` renders them with headless Chrome. To add a mockup, give it a descriptive kebab-case name (screen, variant, mode) and a row here.

## Drawing backlog recorded on 2026-11-03

Historical planning snapshot, not a current coverage audit: additional explorations are indexed above.
Check the current app and its specs before treating a row as missing or done.

Originally ordered by the first week of use: what
someone sees in their first five minutes decides whether they ever reach Share or the Feed. Each
needs Light and Dark, the largest Dynamic Type, and the states listed. Tick a row by linking the
file in the table above.

### Day 0: right after onboarding (draw first)

| Screen | Spec | States to draw | Status |
|---|---|---|---|
| Onboarding · Your first car (polish) | [`onboarding.md`](../../../carodo-ios/docs/specs/onboarding.md) Steps 4–6, [`garage.md`](../../../carodo-ios/docs/specs/garage.md) | name ("My car" when blank), **Car / Motorbike** (missing today), distance unit, "No licence plate needed", Continue and Later; the same car as it then appears in the Garage, so both read as one object | [Day 0 board](onboarding/first-run-day0.png), built |
| First-run Map | [`navigation.md`](../../../carodo-ios/docs/specs/navigation.md), [`drive-recording.md`](../../../carodo-ios/docs/specs/drive-recording.md) | no drives yet, the Start Drive button idle and not ready, one line on Auto Mode ("Auto Mode is on: just drive" / off with why) | [Day 0 board](onboarding/first-run-day0.png), built |
| Permission states | [`onboarding.md`](../../../carodo-ios/docs/specs/onboarding.md), [`passport.md`](../../../carodo-ios/docs/specs/passport.md) Settings | When In Use only (Auto Mode off), location denied (manual only), Motion denied, reduced accuracy: a quiet line with one action, never a wall | [Day 0 board](onboarding/first-run-day0.png), built |

### Day 1: the first drive

| Screen | Spec | States to draw | Status |
|---|---|---|---|
| Start Drive on the first run | [`drive-recording.md`](../../../carodo-ios/docs/specs/drive-recording.md) Panels | the first tap opens the Start panel asking for what is missing: vehicle (none, one, several; "no vehicle" allowed), GPS readiness, mode; afterwards one tap starts with the last-used vehicle; the compact panel "Recording · <vehicle>" with Undo and the vehicle switch | [Day 1 board](onboarding/first-run-day1.png), built |
| First drive saved | [`journeys.md`](../../../carodo-ios/docs/specs/journeys.md) Detail | Journeys with one drive; the detail before its place names and summary arrive, then after; the vehicle section | [Day 1 board](onboarding/first-run-day1.png), built |
| Replay panel | [`replay.md`](../../../carodo-ios/docs/specs/replay.md) Layout, Speed, Camera, Timeline | speed-profile scrubber, 30 s → 10× … button, Follow on and off, a compressed stop label, a healed and a straight gap | To do |

### Day 2–3: wanting to show it

| Screen | Spec | States to draw | Status |
|---|---|---|---|
| Share card | [`share.md`](../../../carodo-ios/docs/specs/share.md) Share card, Time | 9:16 and 1:1, the size picker, trim on and off, "Sunday 1 Nov · Morning" | Drawn: [`share/share-card.png`](share/share-card.png); direction D approved by the owner 2026-11-13 ([plan](../../plans/share-card.md)) |
| Share page and link preview | [`share.md`](../../../carodo-ios/docs/specs/share.md) Share link, Link preview | the web page (static route, figures), the 1200 × 630 preview in a chat, a revoked link | To do |
| Journeys search and filters | [`journeys.md`](../../../carodo-ios/docs/specs/journeys.md) Search | the search field, vehicle and tag tokens, no results | To do |
| Journey edit | [`journeys.md`](../../../carodo-ios/docs/specs/journeys.md) Edit | vehicle, custom name (empty = automatic), note | To do |
| Delete and Recently Deleted | [`journeys.md`](../../../carodo-ios/docs/specs/journeys.md) Delete | the swipe, the confirmation text, the Recently Deleted list with days left, Restore, Delete Now | To do |
| Garage and vehicle page | [`garage.md`](../../../carodo-ios/docs/specs/garage.md) | the first car from onboarding, adding a motorbike, a vehicle page with its drives; Last parked with Directions (later) | To do |

### Day 4 and after: the app starts to know you

| Screen | Spec | States to draw | Status |
|---|---|---|---|
| Places suggestion and list | [`places.md`](../../../carodo-ios/docs/specs/places.md) Finding, Managing places | the card on Journeys ("Is it Home?"), the list by role, empty | To do |
| Place editor | [`places.md`](../../../carodo-ios/docs/specs/places.md) Managing places | the circle on a map (50 m to 1 km), role picker, name, private switch (100 m minimum), delete | To do |
| Place symbols on journeys | [`places.md`](../../../carodo-ios/docs/specs/places.md) Symbols and rendering | row title "⌂ Home → Work", start and end markers on the detail map, timeline rows; a drive at no place | To do |
| Join the Feed and Feed items | [`feed.md`](../../../carodo-ios/docs/specs/feed.md) Joining, Item layout, Headline, Shape | the one Join screen; an item with headline, data line and shape; several drives; with and without area | To do |
| Feed badge item and thin region | [`feed.md`](../../../carodo-ios/docs/specs/feed.md) Badges, Scope | a stamp item; the "showing everyone" line on Nearby | To do |
| Passport stamps | [`achievements.md`](../../drafts/achievements.md), ADR 0013 | inked stamps by tier, faint pencil outlines with progress, the 3D die turned and pressed | To do |
| The earned moment | [`achievements.md`](../../drafts/achievements.md) | the stamp coming down on the page, name, what earned it, Share; the Passport dot | To do |

### Later

| Screen | Spec | States to draw | Status |
|---|---|---|---|
| Profile | [`profile.md`](../../../carodo-ios/docs/specs/profile.md) | another driver's page: cars, totals, level, stamps, recent items, Follow | To do |
| Settings additions | [`passport.md`](../../../carodo-ios/docs/specs/passport.md) Settings | Places, Recently Deleted, Privacy (Show my area, Show my drive shapes), Account (Sign out everywhere) | To do |
| 3D and video camera | [`replay.md`](../../../carodo-ios/docs/specs/replay.md) 3D and video camera | the four beats as a storyboard (opening, descent, follow, closing) | To do |
