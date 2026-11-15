# Vehicle marker: one slot, one box, the tip on the video's clock

Status: approved by the owner 2026-11-15 ("đồng ý lên plan và làm thôi"); built and committed (carodo-ios `ac5a361`); device check open.

## Why now

The marker shrank to 32 pt (carodo-ios `15f6c08`). The owner's export of 2026-11-15 shows it at
the new size in the video (disc about 98 px of 1080; 32 pt × 3 = 96 px expected), because the
Export editor and the renderer use Replay's own map (`ReplayVideoStage` → `ReplayMapCoordinator`
→ `ReplayWheelView` → `DriveLocationMarker`).

A later feature lets the person pick the marker a Replay video shows. Three things are prepared
first. Two of them change nothing on screen, and the third fixes a defect that already exists.

## Audit

- `ReplayWheelView` hosts `DriveLocationMarker` and nothing else: no slot for another marker.
- A marker's box is known only to the wheel (`DriveLocationMarker.side`); another marker would
  pick its own size, centre and heading behaviour, and FollowCamera's framing assumes the
  position is the box's centre.
- **Defect:** the travel tip turns with a SwiftUI `.easeOut(0.35 s)` on the wall clock. A
  rendered frame takes longer than 1/30 s of real time, so in a video the tip turns over a
  different number of frames than on screen, and differently on each iPhone. In Follow the map
  heading changes every frame, so the tip lags the road in the video.
- A comment in `ReplayMapCoordinator` still says "The wheel (40 pt)".

## Steps (one commit)

1. **Slot.** `VehicleMarkerStyle` (design system, beside `DriveLocationMarker`): one case today,
   `.wheel`. `ReplayMapLook` gains `marker` (default `.wheel`); `ReplayWheelView` draws
   `VehicleMarker(style:…)`, which switches on the style. A changed style re-shows the annotation
   view. Not persisted: no raw value, so nothing becomes data (iOS invariant 8) until the
   customisation feature decides where the choice lives.
2. **Box.** `VehicleMarkerStyle` states the contract every style meets: drawn in
   `VehicleMarkerStyle.side` × `side` (disc 32 + tip reach), centred on the position, and how it
   shows heading (`.tip`: a tip turns around a still disc; `.whole`: the drawing turns, for a
   top-down car later). The wheel's sizes move there; `DriveLocationMarker.side` reads it. A test
   pins the box. `docs/design-system.md` names the contract.
3. **Tip on the player's clock.** A pure `MarkerTipEase` (Core/Replay) eases the tip's angle
   toward the travel course by the frame's `dt` (exponential, the time constant that matches the
   old 0.35 s ease-out), snaps on a seek (`dt == nil`), turns the short way (`UnwrappedAngle`).
   Replay and the video drive the tip from it every frame; the marker then draws the angle as given,
   without its own animation (`DriveLocationMarker(…, animatesTip: false)`). The live map keeps
   the SwiftUI ease (GPS at about 1 Hz, no video). The map's heading is read right after the
   camera is set, not only in the delegate callback. Tests: converges, same result for the same
   frames, snap on seek, short way across north.

Not now: marker size as a share of the frame. There is one frame (360 × 640 pt); it is done when a
second aspect ratio arrives.

## Checks

`task lint`, `task warnings`, `task test`; a Replay and an export on the simulator (the tip turns
smoothly, follows the road in Follow). Device check: export the same drive twice on the iPhone and
compare the tip at a bend.

## State

- [x] Steps 1–3 built 2026-11-15, carodo-ios `ac5a361`: lint, warnings and 2,251 tests pass
- [ ] Owner: export one drive twice on the iPhone, the tip the same at a bend and following the road in Follow
