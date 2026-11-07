# Vehicle art v4 — rounded vector proposal

**Archived exploration.** This 11-silhouette variant is retained for comparison. The current
app uses SF Symbols; this archive is not its renderer. See the [artwork index](../../README.md)
and [current iOS design system](../../../../../carodo-ios/docs/design-system.md#vehicle-artwork-and-paint).

## Review

- `preview.html`: self-contained responsive gallery, with inline SVG and system light/dark theme.
- `overview.png` / `overview.svg`: all regular silhouettes on light and dark surfaces.
- `sizes.png` / `sizes.svg`: compact drawings at 88 and 144 CSS px; regular drawings at 280 CSS px.
  Image viewers may scale the entire sheet. Use the HTML gallery for CSS pixel sizing.
- `colors.png` / `colors.svg`: the ten existing vehicle paint colours.

## Changes from v3

Unified dark greenhouse surrounds (`dlo`) and circular wheel arches (`arc_q`) on all six cars,
with 5-twin-spoke alloy wheels, brake rotors, sheetmetal fender flares and sculpted lower door
recesses (`suv` and `pickup` add dark wheel-arch and sill cladding). Dedicated open-spoke
motorcycle wheels (`moto_wheel`) and corrected wheelbase proportions on `scooter`, `underbone`,
`manual` and `sport`. Added the `bicycle` silhouette with a compound hydroformed diamond frame,
aero fork, drop handlebars, water bottle, drivetrain and tension-spoked 700c wheels (`bike_wheel`).

Compact versions omit door handles, seams, rotor rings, spoke detail and water bottle, and use
simpler wheel centres. Suggested usage: compact at 88–144 px wide and regular at 180 px or wider.

## Paint and embedding

Inline SVG reads `--vehicle-paint` (fallback `#8195a6`). Only painted panels inherit `currentColor`;
glass, tyres, seats, wheels, lights and metal keep their colours. A neutral translucent overlay
provides shading without replacing the chosen paint.

External SVG `<img>` files do not inherit the host page's CSS variable. Inline them for dynamic
paint. Each instance needs unique title/gradient IDs and matching reference updates; `preview.html`
demonstrates this. SVG files have transparent backgrounds and a common `0 0 240 110` viewBox.

For iOS, transfer paths and layers to the existing SwiftUI Canvas. Geometry still uses M/L/Q/Z,
circles and ellipses; no SVG library is required. Choose the compact drawing explicitly for small
badges. The `manual` filename still maps to the existing vehicle style and is drawn as a naked bike.

## Source and verification

Run `python3 -B generate.py` from this directory. This dependency-free
generator contains the geometry and rounds linear corners using quadratic curves while retaining
authored curves. It emits 22 vehicle SVGs (11 regular and 11 compact), three comparison sheets and
the HTML gallery.

`python3 -B palette.py` regenerates the approved palette sheet and JSON. Its paint values are mapped
to existing persisted keys in iOS: Silver → silver, Slate → grey, Pearl → white, Graphite → black,
Crimson → red, Ocean → blue, Forest → green, Champagne → yellow, Terracotta → orange, Cocoa → brown.
Keep `VehicleColor.rgb` and the iOS design-system palette table in sync if these values change.

To inspect the historical Swift export without overwriting the app, run from this directory:

```sh
python3 -B export_swift.py /private/tmp/carodo-vehicle-art-review.swift
xcrun swift-format format -i /private/tmp/carodo-vehicle-art-review.swift
```

`export_swift.py` consumes the same SVG generation functions used by the previews. It emits cached
paths, ellipse geometry, paint/gradient layers and strokes, not flattened raster images. The historical renderer chose compact art below 180 pt and resolved the body outline against
Light/Dark at draw time; the current SF Symbol renderer does not consume this export.

PNG sheets were exported with:

```sh
qlmanage -t -s 1600 -o /private/tmp overview.svg sizes.svg colors.svg palette-proposal.svg
```

The SVGs were parsed for XML validity, checked for duplicate IDs and unresolved paint references,
and the overview and size exports were visually inspected. The HTML's inline SVG IDs were checked
for uniqueness. Physical iPhone and Safari rendering still need visual verification.
Review labels in these artifacts are not shipped app copy. No schema/API/permission/dependency change.
