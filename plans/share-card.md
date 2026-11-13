# Share card — a drive as one image

Status: **S1 built, uncommitted, waiting for the owner's review** (carodo-ios working tree,
2026-11-13). Direction D of the mock-up and Q1–Q4 approved by the owner the same day. Open: PV-19
(device), TD-26 (private regions, Apple's map terms), TD-27 (pieces shared with the Replay Export
editor).
Audit: this session, 2026-11-13 (files read are listed under Existing behaviour).
Mock-up: [`design/mockups/share/share-card.png`](../design/mockups/share/share-card.png), section 4
(source `design/mockups/source/share-card.html`). Sections 1 and 3 are the directions it came from.

## Outcome

Share on the journey detail opens an editor whose preview is the image: the whole route on a map
that fills the card, the drive's figures on a soft ground at the top, and the day as the Driving
Passport's round stamp. One tap sends it to the system share sheet. It works with no network and no
account.

User story: "I finish a nice drive, tap Share, see a card I would post as it is, switch it to 1:1
for a message, and send it. Nobody can tell where I live or what time I left."

## Owner decisions

Made (2026-11-13):

| # | Decision |
|---|---|
| D1 | The map fills the card; no boxed map window. The route is the centre. |
| D2 | The map's own labels (streets, wards) stay: they cannot be removed. Carodo itself writes no place name, title, stop or place symbol on a card. |
| D3 | The line is the real route on its roads, drawn with the Feed shape's soft curve. Not the Feed's shape (turned and mirrored on purpose, it matches no road). |
| D4 | Two styles, chosen in the editor: **Stamp** (the Passport's round stamp carries the day; no lockup) and **Simple** (the lockup and a line of text, as a Replay video frame). |
| D5 | The editor reuses the Replay Export editor's shape: preview, a row of tools, one Copper button. |
| D6 | The line is always Copper, never coloured by speed: on a shared image the colours have no meaning to the viewer and they make the card worse. No such option. |

Answered as recommended (owner, 2026-11-13):

| # | Question | Decision |
|---|---|---|
| Q1 | Which style is the default? | Stamp: it is the one no other app has. |
| Q2 | Average speed on the card? The spec listed distance, duration and vehicle only. | Yes, moving average, beside the duration. No top speed (backlog: only if the person adds it). |
| Q3 | A Save button that writes straight to Photos? It needs the add-only Photos permission: an Info.plist key with English and Vietnamese text (P6). | ~~Not in S1~~ Replaced by the owner the same evening: **Share and Save side by side**. The recommendation's reason was also wrong: the share sheet's Save Image needs the same key (`NSPhotoLibraryAddUsageDescription`), which the Replay Export session had already added for Save Video; its text now names a card as well as a video. |
| Q4 | Is 1:1 in the first slice? | Yes: it is the same renderer with another layout table, and the spec already decided two sizes. |

## The card (direction D)

In points, 360 wide; written at 3x: 1080 × 1920 (9:16, default) and 1080 × 1080 (1:1).

- **Map:** a snapshot, muted, no points of interest, Light or Dark; north up. Apple's logo stays
  clear at the foot (the block is at the top for that reason).
- **Fit:** the route, after the privacy zone is cut, is fitted into the area the block leaves free
  (above Apple's logo), centred, with a floor on the zoom so a very short drive never shows at house
  level. The map follows the route; nothing of the route is under the block.
- **Line:** Catmull-Rom through the route's points, round ends, Copper on a casing of the ground
  colour. ~~Zone on: the line simply ends, no marker. Zone off: the start and end markers.~~
  Replaced by the owner (2026-11-13, third look): both ends are always the design system's plain
  discs (no flag), at the ends of what is shown, so a cut end looks like a real one.
- **Block (top, on a ground that fades into the map):** distance (large), duration and average
  speed, the vehicle, `carodo.app` in Copper.
  - Stamp: the round stamp at the right, the wheel in its centre, the day around the top
    ("14 NOV 2026") and the part of day around the bottom ("MORNING DRIVE"), Copper ink, a little
    off straight.
  - Simple: the lockup at the left, "Saturday 14 Nov · Morning" and the vehicle at the right.
- **No map** (offline with nothing cached, or the snapshot fails): the same card on the plain
  ground. A card can always be made.
- **Never:** a clock time, the journey's title, a place name or symbol written by Carodo, a stop, a
  top speed.

## The editor

Full screen over the journey detail. Header: Close and "Share Card · 17.8 km · 29 min". The preview
is the image, redrawn at once when a tool changes. Tools: size (9:16, 1:1), style (Stamp, Simple),
look (Light, Dark map), privacy zone (only when the setting is not Off; off here is for this card
only and changes no setting). Bottom: Share (Copper), the system sheet with the PNG.

A drive shorter than its privacy zone: the preview says so and Share is off until the zone is
turned off for this card; never the whole route instead (as the Replay Export editor does).

## Existing behaviour (files read)

- `Features/Journeys/Views/JourneyDetailView.swift:261`: the Share toolbar button, disabled, with
  `Journeys.detailShareHint`.
- `docs/specs/share.md`: Status Ready, not built. Two sizes, the privacy zone, day and part of day,
  no place name on a card.
- `Core/Domain/PrivacyZone.swift`: the setting (Off, 300 m, 500 m, 1 km).
- `Core/Domain/DriveShapeMaker.swift`: `trimmed(_:privacyZone:homeAndWork:)` cuts both ends along
  the route, with the Feed's own floor of 300 m and Home/Work removal.
- `Core/Replay/ReplayTimeline.swift:370`: `trimmed(endsBy:)`, the same cut for a timeline.
- `Core/Formatting/DisplayFormat.swift:134`: `dayAndPartOfDay(of:)`.
- `Core/Journal/JourneyMapSnapshotService.swift`: `MKMapSnapshotter`, muted, no points of interest,
  `RouteFraming.rect(for:size:)`, drawn with Core Graphics, cached in Caches.
- `DesignSystem/Components/RouteViews.swift`: `RouteShape(shape:smoothed:)`, the Catmull-Rom curve.
- `DesignSystem/Components/PassportMarks.swift`: `PassportStamp` (double ring, lettering on two
  arcs, the mark), `CarodoMarkView`.
- `DesignSystem/Components/RouteEndMarker.swift`: `RouteEnd`, `RouteEndMarker`.
- `Features/Journeys/Views/ReplayVideoOverlay.swift` (committed) and `ReplayExportView.swift`
  (another session's, uncommitted): the frame's block, the editor's shape, `ReplayShareSheet`,
  `ReplayRoundButton`.

Assumed, not checked: that the Catmull-Rom code in `RouteShape` can be shared with a Core Graphics
path without copying it;
whether `PassportStamp`'s arc lettering can take any two strings as it stands.

## Slices

**S1: the card and the editor.**
- `ShareCard` (pure, `Core/Domain` or `Core/Journal`): the layout tables of both sizes and both
  styles, the fit (route box → map rect for a free rectangle, with the zoom floor), the figures.
- The cut along the route by metres becomes one function used by the Feed shape and the card
  (extracted from `DriveShapeMaker`, which keeps its floor and Home/Work rule on top).
- `ShareCardRenderer`: snapshot (or none), the line, the block, the stamp → `UIImage` at 3x.
- `PassportStamp` takes its two arc strings (the Passport header keeps its own).
- `ShareCardModel` + `ShareCardView` in `Features/Journeys`; the Share button is wired; strings in
  `Journeys.xcstrings` (English, Vietnamese).
- The share sheet and the round tool button are shared with the Replay Export editor once that is
  committed; until then nothing of that session's files is touched.
- Tests: the fit (tall, wide, one-point and very short routes; both sizes), the cut (zone longer
  than the drive, Off), the stamp's strings in both languages, layout tables inside the card.
- Evidence: simulator screenshots on the sample drive, Light and Dark, large text, Vietnamese.

**S2:** Save to Photos if approved (Q3), private regions cut along the route (the card's part of
TD-25).

**S3 (backlog):** a badge earned on the drive pressed as its visa stamp, photo background, hidden
plates. Not the speed profile strip in speed colours (D6 applies to it too).

## S1 as built (2026-11-13)

- `PrivacyZone.hidingEnds(of:)`: the display route's ends cut on the line. The Feed's cut
  (`DriveShapeMaker.trimmed`) is left as it is: it drops whole recorded fixes, which a simplified
  route cannot afford (two points on a straight road).
- `ShareCard` (layout, `mapRect(for:size:area:)`, `Content`), `ShareCardRenderer` (one snapshot a
  size, appearance and zone; both styles share it), `ShareCardModel`, `ShareCardView`.
- `RouteCurve` extracted from `RouteShape`; `PassportStamp` takes its two arcs' lettering and its
  ink; new `CarodoLockup` and `ActivitySheet` in the design system.
- The card's figures are the whole drive's (distance, elapsed time, moving average), whatever the
  zone hides: they say nothing about where.
- The block's ground is opaque to 0.7 of its height: a map label showing through the figures made
  both unreadable on the first run.
- Map labels are drawn at two thirds of MapKit's size (the snapshot is taken larger at a lower
  scale), as the journal's list images do.
- After the owner's first look (2026-11-13): the editor is a **sheet** with no header (no title,
  no Close; pulled down to close), so the card sits higher; the chosen size is a pale Copper fill
  with a Copper border (the design system's "chosen", not a Charcoal segment); **Share** (Copper)
  and **Save** (a control's surface) side by side, one above the other at accessibility text
  sizes. Save: `PhotoSaver` (add only), "Saved" with a check until the card changes, an alert with
  Open Settings when refused. The mock-up's editor (header, one button) is older than this.
- Second look (2026-11-13): the sheet is Charcoal in both appearances; its height follows the card
  on screen (1:1 shorter), eased with `.snappy` (none under Reduce Motion); a selection haptic on
  every choice, success or error on Save.
- Third look (2026-11-13): the line and map are the journey detail's (`CarodoRouteStyle`: brand
  Copper 6 pt on a 10 pt casing; `CarodoMapLook`: Apple's map not muted in Light), ends as plain
  discs whatever the zone; the other size's map is taken right after the first card, so 9:16 ↔ 1:1
  is one drawing with no card shown without its map, and each new card fades in over the last.
- QA: `-carodo.debugOpenShareCard YES`, `-carodo.debugShareCard simple,square,dark,whole`.
- Checks: lint, a clean build with no warning, the whole test suite (27 new tests).

## Acceptance criteria

- With no network and no account, a card is made and shared; with no map it is the plain card.
- With the zone at 300 m, 500 m or 1 km the card shows neither the first nor the last that many
  metres, and the map is centred on what is left; Off, or off for this card, shows the whole route
  with its markers.
- A card shows no clock time, no title, no place name or symbol written by Carodo.
- Both sizes and both styles in Light and Dark; the route never under the block or Apple's logo.
- Changing a tool redraws the preview without a visible wait on an iPhone (to measure on a device
  before it is claimed).

## Non-goals

The share link and its preview image, the web page, the backend; a video (Replay Export); editing
the figures; accent colours; a top speed; a line coloured by speed (D6).

## Constraints and risks

- No schema, API, entitlement or dependency change in S1. Q3 would add an Info.plist key.
- **Before the card leaves development builds:** TD-2 (Apple map terms: a map image shared
  outside, `plans/apple-maps-data-review.md` row 10) and the private regions cut (S2).
- The card image is never cached on disk beyond the share: it carries a route.
- A snapshot needs tiles: the no-map card is the offline path and is tested as such.
- Device checks: snapshot time and memory at 1080 × 1920 on the oldest test iPhone; the share
  sheet's Save Image.

## Validation

`task lint`, `task warnings`, `task test`; screenshots as in `docs/operations/setup.md`
(Screenshots as evidence), sample data only.
