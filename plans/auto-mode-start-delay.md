# Auto Mode start delay — evidence and the staged fix (2026-11-06)

Status: **A (diagnostics) built 2026-11-06 (uncommitted; 954 tests pass, lint clean; on the iPhones after the next install); B, C, D approved by the owner, waiting for drives with A's
log** before they are built. No coordinates in this file; distances are relative.

## Evidence: two passenger drives on 2026-11-06 (same car, two iPhones)

Build: the one installed ~07:38 (before `TripContinuation`, `StopStage`, `leaveRadiusM`).
Databases: `drive-data/carodo-20261106-114234-tuanngo-iphone.sqlite` (iPhone 17 Pro Max) and
`drive-data/carodo-20261106-121309-onphatsam-s-iphone.sqlite` (iPhone 12 Pro Max).

| Drive | Phone | Wake (geofence exit) | Drive started | Lost before the first fix | Recovered by the lead-in |
|---|---|---|---|---|---|
| Out 09:00 | 17 Pro Max | 09:00:51, ~165–185 m from the circle centre | 09:00:59 (8 s) | ~78 s, ~250 m road | yes, 253 m |
| Back 10:20 | 17 Pro Max | 10:18:59, at the circle edge | 10:20:13 (**74 s in the window**) | the window's 74 s + the way to the edge, 218 m straight | **no**: the drive before was a passenger one, skipped by `leadInStart`; the last driver drive was 7.3 km away (`fromParkedM=7320`) |
| Back 10:22 | 12 Pro Max | 10:22:05, **~590 m out** (372 m after the other phone's first fix) | 10:22:11 (6 s) | ~2.5 min, ~590 m | — |

- The 17 Pro Max's slow start (back) is the **detection window**: from the circle edge to 218 m
  in ~71 s (~1 m/s), so no run of 4 fixes ≥ 12 km/h; confirmed the moment it reached 12.7 km/h.
  The window's own fixes are not stored, so a crawl and a walk cannot be told apart yet (A).
- The 12 Pro Max's slow start is **iOS waking late** on the region exit; nothing in the app can
  shorten that except the Shortcuts start.
- Both confirmations ran at 12.3–13 km/h: the 12 km/h × 4 rule waited for the speed, never for
  the count.

The split on swipe-away (OnPhatSam, out): three pieces. 09:01:36–09:03:44 (~411 m, ~2 min) was
**discarded as a short drive** at the relaunch (`launched recovered=0 discarded=1`); 09:03:44–09:15:25
was `recovered` at the second relaunch and joined to 09:15:34– (`waitJoin joined gapS=9
distanceM=46`); "Maybe on the move" was asked three times. With `TripContinuation` (resume before
discard, `TripRecovery`) both relaunches would resume the same trip: **device check on the 11:50
build** (swipe away while recording, reopen within 10 min; expect `launched … resumed=1`, one trip,
one question).

Stops (both phones): longest 94 s; nothing near `warnS` 120 s or the 300 s grace; a crawl of 73 s
at ~4 km/h over 85 m. No stop threshold changes.

## A — diagnostics (built 2026-11-06)

- `detection …` at each window's end (confirmed, timed out, on foot, skipped): fixes, moving,
  slow, untrusted, inaccurate, stale, first fix after the wake, max km/h, net displacement (10 m).
- `launched … state=background|foreground`: who launched the app.
- `map free reason=gesture|journey|history`: the Map leaving its follow during a drive.
- Device check: does `state=` read `background` on a relaunch by iOS (read in `CarodoApp.init`)?

## B — seed the slow roll-out (approved, waiting)

Keep the window's fixes; on confirmation prepend the contiguous fixes before the 4-fix run whose
speed is ≥ 2.0 m/s (7.2 km/h), trusted (> 2 × speed accuracy), accuracy ≤ 50 m, ≤ 5 s apart. The
moment of confirmation does not change; the start moves earlier, real fixes only.
Tests: 1.99 m/s stops / 2.0 joins; 5.0 s apart joins / 5.1 s stops; an untrusted fix stops.

## C — extend the window once (approved, waiting)

At the 120 s timeout, when the window saw ≥ 3 trusted fixes ≥ 2.0 m/s or moved ≥ 50 m from its
first fix: one more 120 s (240 s at most). Why: the back drive confirmed with 46 s to spare; a
slower roll-out would have closed the window and moved the circle (another ~150 m).
Tests: 49 m closes / 50 m extends; 2 fixes close / 3 extend; the second timeout closes.

## D — lead-in from the drive before, whoever rode (approved, waiting; after B)

`leadInStart` takes the previous drive's last fix whatever its rider (driver or passenger), within
the existing 1,500 m, and routes to the first fix after B. `fromParkedM` in the ride log uses the
same origin. Tests: 1,500 / 1,501 m; passenger → passenger, driver → passenger, passenger → driver.
Watch: the walk to the car (67–93 s on 2026-11-06) may be counted as road.

## E — hold a short piece an interruption cut (approved and built 2026-11-06)

A drive under the short-drive threshold that ended by an interruption (`recovered`, `noSignal`) is
saved as `trips.status = 'held'` (P6 approved), out of Journeys, offered to the next Auto Mode
start; a drive that carries it on joins it and it becomes the journey's head. After `maxGapS`
(10 min) with no drive carrying it: kept if ≥ 5 trusted fixes ≥ 25 km/h or Core Motion automotive
≥ 60 s, else deleted. Drives that really ended keep the < 500 m / < 2 min rule (owner, 2026-11-06).
Logs `driveHeld`, `heldKept`, `heldDiscarded`, `launched … held=N`. Built: `HeldFragment`,
`TripHeldStore`, `DependencyContainer.settleHeldTrips` (launch, each saved drive, back to the app);
968 tests pass (14 new), lint clean; docs: tracking.md, drive-recording.md, data-model.md,
device-testing.md. Device check: swipe away 1–2 min into an Auto Mode drive, then (a) reopen at once
→ `resumed=1`; (b) reopen after 10+ min → `held=1` then `heldKept`.

## B, C, D and DriveConfidence (built 2026-11-06, on the owner's request the same day)

B (`DetectionWindow.rollOut`), C (`DetectionWindow.extends`, `TrackingModeController.extendDetection`),
D (`leadInStart` takes the drive just before, whoever rode it) and `DriveConfidence` (`conf=` on
detection, leadIn, heldKept/heldDiscarded, carriedOn, autoFinished; shadow metric only). 988 tests
pass, lint clean; docs/tracking.md (Auto Mode detection, Lead-in, Confidence). Next: read the
`detection`/`leadIn` lines and `conf=` of the next drives against what really happened.

## Before building B–D (superseded: built the same day)

1. Two or three Auto Mode drives with A's log, ideally one leaving a car park or an alley slowly.
2. Read `detection` lines: was the window waiting on speed (slow/untrusted) or on a walk?
3. Then B and C with their tests; D after B; update `docs/tracking.md` (Auto Mode detection,
   Lead-in) in the same change.

## Open at the end of the 2026-11-06 session

Device checks (TuanNgo iPhone has the 12:57 build with A–E and `conf=`):
1. Swipe Carodo away 1–2 min into an Auto Mode drive: reopen at once → `launched … resumed=1`, one
   trip, one question; reopen after 10+ min → `held=1`, then `heldKept … conf=`.
2. Leave a car park or alley slowly: read `detection … extended= prependedFixes=` and `leadIn … conf=`.
3. Does `launched state=` read `background` when iOS relaunches Carodo?
4. Still from earlier: the stop panel lines ("Xe đang dừng", "Đã tạm dừng ghi"), `leaveRadiusM`
   100 m in a crawling jam, `walkAwayS` timing.
5. Map: `map free reason=…` lines if the Map leaves its follow with nobody touching it.

To do / decide:
- Install the new build on VanSam and OnPhatSam (`task device-all`; both still on the 07:38 build).
- OnPhatSam (iPhone 12) woke ~590 m late: set up the Shortcuts automation (CarPlay/Bluetooth).
- Tune `DriveConfidence` anchors and weights after a few drives (`conf=` vs the real label).
- Known limits: B moves the start time but RouteRecorder may not count the slowest roll-out
  metres; a bicycle's held piece is judged by car speed; a kept held piece gets places/gaps at the
  next launch.
- Map "Modifying state during view update" (7 runtime warnings): fixed in `AtlasMapCoordinator`
  (`updating`/`emit`, 991 tests pass); confirmed gone in Xcode by the owner (2026-11-06 13:43); not
  yet installed on an iPhone. Repro
  before the fix: Map tab, a recording drive, a moving simulated location → 75 warnings in ~50 s
  (`lastCamera`, `viewport` via `settle`; `cameraCommand`, `cameraCommandCount` via `show` → `move`).
- Nothing is committed (the owner decides when).
