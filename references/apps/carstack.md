# Carstack

A car community app: a feed of other drivers' activity and a map of the roads you have driven.
The closest app to Carodo's Map and Feed. Checked 2026-11-02, database and changelog read 2026-11-03; screenshots, if kept, are in
`../screens/carstack/` (not committed).

## What we took

| Pattern | Why it works | Where it landed |
|---|---|---|
| **Map controls cycle on tap.** One location button steps through follow with heading → follow north up → close, and one map-type button steps through the map types; the icon shows the current state | Two small buttons instead of menus; one thumb, no sheet over the map | `carodo-ios/docs/specs/navigation.md` (Map) |
| **The direction cone shows only while the map turns with you** | The cone means "the map follows where you face"; on a north-up map it would be noise | Same spec, "Your position" |
| **Roads coloured by how often they were driven,** with a small legend | Turns many overlapping routes into a readable picture of your habits | Same spec; copper ramp in five levels (1 · 2–5 · 6–10 · 11–20 · 20+) |
| **A Feed of other drivers' activity** | Community without a social graph to build first | carodo-ios ADR 0007 |
| **Gap healing** (2026-11-03): a GPS gap is routed by the map's directions, stored apart from the raw points | Distance follows the road through tunnels; raw data untouched | carodo-ios `docs/tracking.md`, Gap healing |
| **A place cache keyed by a rounded coordinate, with a version** | One lookup per spot; naming rules change without asking again | `geocoded_cells` table, `PlaceNaming` |
| **Drives stamped with the build** | Device data reads against the rules that produced it | `trips.recorded_build`, `recorder_version` |
| **Replay panel** (screenshot 2026-11-03, a drive "X. Ninh Sơn → P. Tân Thuận"): the scrubber is a bar chart of the drive's speed, coloured by band, with the local clock under the handle; play, a speed button, distance so far and a speed gauge in one bottom panel; the route ahead faint, the driven part coloured, a car model on it | The scrubber shows the whole drive's shape before playing; one panel holds everything | carodo-ios `docs/specs/replay.md`, Layout |
| **Changelog as a feature list** (121 releases read) | — | [`../../plans/backlog.md`](../../plans/backlog.md) |

## What we do differently

- **The Feed never shows where.** Carodo shows how people drive (car, time, distance), never the
  route or places (ADR 0007).
- **Raw points never reach a server.** CarStack uploads points and sessions to its backend and also
  syncs through iCloud; Carodo keeps every fix packed on the device and backs it up only to the
  person's iCloud (carodo-ios ADR 0004, 0005).
- **Copper, not their palette.** Heat levels use the Carodo copper ramp, darker on a light map and
  brighter on a dark one; copper stays a line colour, never a fill.
- **Replay starts on the whole route and plays in 30 s** (a setting: 15, 30, 60, 90 s, for short
  videos), with 10×, 30×, 60×, 120× on the button; CarStack opens following the car at 15×.
  Points of interest stay hidden on the whole route and show muted only while following; CarStack
  shows every shop label, which crowds the road.
- **Moving between follow states keeps the zoom close to where it was**, so a tap never jumps from
  street level to the whole city.

## Open questions

- Whether the close state needs its own icon or a short name hint (today it shares the north-up
  icon).
