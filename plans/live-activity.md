# Live Activity for a recording drive (L1 + L6)

Status: **LA1 `2e65d77`, LA2 `13a496d`, pause hold `7ac0ace`, LA3 `526720a` committed in carodo-ios**
(2026-11-15); device checks open (below): Resume from the Lock Screen with When In Use, Log fuel at a
real stop, a motorbike drive shows none. D1–D7 approved as recommended (D4 kept: no Pause on the Lock
Screen, Resume only). Owner, 2026-11-15: Log fuel only for a car's drive (not a motorbike), at a stop
of 2 min or a pause, Log charge for an electric car, in the app's panel too.
Owner, 2026-11-15, after the first
device look: look **C** (the Carodo mark, a Copper hairline, a warm Copper light on Charcoal; system
glass refused for contrast), **three rows** (status · named figures · buttons only when asked), and
**no vehicle name** on the Lock Screen (D2 amended). Ready shows from Start on: iOS starts an
activity only while the app is on screen.
Owner, 2026-11-15 (second device look): no End at Ready; the distance in metres under 1 km with
rolling digits; the status word stays the panels' ("Live" / "Đang ghi", right for a passenger trip too).
Mockup: [`design/mockups/drive/live-activity.png`](../design/mockups/drive/live-activity.png)
(source [`design/mockups/source/live-activity.html`](../design/mockups/source/live-activity.html));
the looks compared: [`design/mockups/drive/live-activity-identity.png`](../design/mockups/drive/live-activity-identity.png).
Sources: [`references/repos/drive-recorders-study.md`](../references/repos/drive-recorders-study.md)
(L1, L6), [`backlog.md`](backlog.md) (Interactive Live Activity, b10, b204), carodo-ios
`docs/specs/drive-recording.md` (Live Activity, planned), Apple's ActivityKit documentation
(*Displaying live data with Live Activities*, `Activity.request`, `LiveActivityIntent`,
`ActivityAuthorizationError.visibility`).

## Frame

**Outcome.** While a drive records, the Lock Screen and the Dynamic Island show it with the same
words as the recording panels: its phase, its time, its distance, a stop and the countdown to an
automatic end. At a stop the person can answer from the Lock Screen what the panel asks in the
app (Still going, Resume), and at a long stop reach the fuel form in one tap.

**Why.** A drive is recorded with the phone locked or in another app (Maps, music). Today nothing
outside Carodo says a drive is being recorded, that it paused, or that it is about to end by
itself.

**Non-goals.** No map, route, place name or coordinate on the Lock Screen (P5). No speed. No
ActivityKit push, no backend, no App Group, no new entitlement. No Home Screen widget work (the
"Ready" widget stays as it is, a release follow-up). No Apple Watch app.

## What the code does today

| Fact | Where |
|---|---|
| The widget target exists with one placeholder widget; `CarodoShared/` is empty and compiled into both targets | `CarodoWidgets/CarodoWidgetsBundle.swift`, `project.yml` |
| `NSSupportsLiveActivities: true` is already in the app's Info.plist | `project.yml` |
| One session state, read by every surface: `state`, `phase` (`DrivePhase`), `stopStage(at:)` (`StopStage`), `metrics`, `elapsed(at:)`, `pause()`, `resume()`, `keepGoing()`, `finish()` | `Core/Recording/DriveSessionManager.swift`, `DrivePhase.swift`, `Core/Tracking/StopDetector.swift` |
| The session tells the composition root when it becomes active or ends (`onActiveChange`) | `App/DependencyContainer.swift` |
| Starts, finishes and the foreground catch-up | `App/DriveFlow.swift` (`start`, `handle`, `returnedToForeground`) |
| Unfinished trips are resumed at launch | `Core/Recording/TripRecovery.swift` |
| `StartDriveIntent` (Shortcuts) opens the app and starts like `carodo://trip/start` | `App/StartDriveIntent.swift` |
| The fuel form | `Features/Garage/Views/FuelEntrySheet.swift`, `FuelEntryModel.swift` |
| Deep links: only `carodo://trip/start` | `App/DeepLink.swift` |
| The spec already binds the Live Activity to `DrivePhase` and `StopStage` and the same words | `docs/specs/drive-recording.md` |

## What Apple allows (read 2026-11-15)

1. **A Live Activity starts only while the app is in the foreground.** A start from the background
   throws `ActivityAuthorizationError.visibility`. Updating and ending from the background are
   allowed. The one documented exception: an App Intent conforming to `LiveActivityIntent` may
   start one from the background (Shortcuts, a Control Center control).
   **Consequence for Carodo:** an Auto Mode drive that iOS wakes the app for in the background
   cannot show a Live Activity by itself. It appears when the person opens Carodo during that
   drive. A drive started by hand, or by the Shortcuts automation, has it from the start.
2. Push-to-start (iOS 17.2) needs a server and APNs: refused here (P1, P7; a trigger derived from
   location would leave the device).
3. An activity lives at most 8 hours, then the system ends it (it may stay on the Lock Screen 4
   more hours). A longer drive requests a new one the next time the app is in the foreground.
4. The Live Activity runs in the widget extension's sandbox: no network, no location, no database.
   Everything it shows arrives in `ContentState` (static + dynamic ≤ 4 KB). So the app and the
   activity share **types**, not storage: no App Group is needed.
5. A button is `Button(intent:)` with a `LiveActivityIntent`; its `perform()` runs in the app's
   process, so it calls the session directly. A Live Activity has **no text input**: logging fuel
   cannot happen on the Lock Screen, only a link that opens the app on the fuel form (after Face
   ID).
6. Time runs by itself: `Text(timerInterval:)` counts up or down with no update from the app.
   `symbolEffect` and endless animation do nothing in a Live Activity.
7. `staleDate` on each update: past it, `context.isStale` is true and the view says so.
8. iOS 18+: `supplementalActivityFamilies([.small])` puts the activity on CarPlay's Home (iOS 26)
   and the Apple Watch Smart Stack with a small layout.

## Proposal

### What it shows (one line per state, the panels' words)

| State (`DrivePhase` / `StopStage`) | Lock Screen | Island compact |
|---|---|---|
| Finding GPS | "Finding GPS" | mark · — |
| Ready | "Ready · Waiting to move" | mark · — |
| Live, moving | "Live" · elapsed (ticks by itself) · distance · vehicle name | mark · distance |
| Live, stopped (`waiting`) | "Stopped · 1:12" (ticks by itself) · distance | mark · stop time |
| Looks parked (`ending`) | "Looks parked · ends in 1:30" (counts down by itself) · **Still going** | mark · countdown |
| Car audio off (`ending`) | "Car audio off · ends in 1:10" · **Still going** | mark · countdown |
| Paused | "Paused" · distance · **Resume** | pause · distance |
| No location | "Location is off. Not recording." | crossed location |
| Ended (final frame) | "Saved · 24.6 km · 38 min" with no running timer, gone after 5 minutes | — |
| Stale (app suspended) | figures dimmed, "Not updating" in place of the status | mark dimmed |
| Pending (not sure it is the person's drive) | **no activity** (spec: pending is quiet) | — |

Vietnamese follows the glanceable-lines table in `docs/copy-and-localization.md` ("Xe đang dừng ·
1:12", "Đã đỗ xe · Lưu sau 1:30", "Đi tiếp").

### How it shares with the app

- `CarodoShared/DriveActivityAttributes.swift`: the `ActivityAttributes` type (vehicle name,
  distance unit) and its `ContentState` (a status enum with its dates, `distanceM`, the clock's
  start). SI at rest (P3); the widget formats with the one distance formatter, moved to
  `CarodoShared` so both targets use the same code.
- The live surface's colours (Charcoal, Ivory, Copper) and the glanceable strings move to where
  both targets compile them: one source, no copy.
- The intents (`KeepGoingIntent`, `ResumeDriveIntent`, `FinishDriveIntent`) are declared in
  `CarodoShared` so the widget can name them; they run in the app and call the session through
  one small protocol registered by the composition root.
- In the app: a pure mapping `DrivePhase + StopStage + DriveMetrics → ContentState`, a pure
  update gate, and `DriveActivityController` (a long-lived service owned by
  `DependencyContainer`, outside SwiftUI and outside the tracking path: a failure to start or
  update the activity never touches recording).

### Battery and budget

- Timers and countdowns cost no update (`Text(timerInterval:)`).
- The gate updates at once on a phase or stop-stage change; the distance at most every 30 s and
  only when the shown figure changes. Pure, tested on both sides. A hypothesis to tune on a
  device, like the tracking thresholds.
- `staleDate` = now + 3 gate intervals on every update.
- No speed, no map, no image, no push, no frequent-updates key.

### Lessons taken from the reference study (L1)

1. Orphans end at launch: an activity whose trip `TripRecovery` resumes is kept and updated,
   every other one ends immediately (walk `Activity.activities`, never trust a remembered one).
2. `staleDate` on every update ("Unknown is not zero").
3. The pure update gate.
4. A frozen final frame: figures, no timer.
5. No place names on the Lock Screen.

### Slices

| Slice | Outcome | Contracts (P6) |
|---|---|---|
| **LA1** Display | Attributes, mapping, gate, controller (start in foreground, update, end, orphans, stale, 8 h restart), Lock Screen + Dynamic Island views, no buttons; a tap opens the app | Live Activity identifier (the attributes type name becomes data once shipped) |
| **LA2** Answers | Still going, Resume (and Finish at a parked stop if D4 says so) as `LiveActivityIntent`s; `StartDriveIntent` starts the activity too, so a Shortcuts start has it with the phone locked | New App Intents identifiers |
| **LA3** Log fuel | At a long stop the Lock Screen offers "Log fuel": a link that opens the fuel form for the drive's vehicle | A new deep link under `carodo://` |
| **LA4** Later | A Control Center / Action button "Start Drive" control; the small family for CarPlay and Apple Watch | New control identifier |

Each slice: unit tests for the mapping, the gate (both sides) and the orphan rule; previews of
every state; simulator screenshots (Light, Dark, Vietnamese, xxxLarge where it applies);
`docs/specs/drive-recording.md` updated in the same change.

### Device checks it will leave open

Update cadence while the app is in the background on a real drive; orphan cleanup after a force
quit; a Shortcuts start with the phone locked; the 8 h limit; battery over a one-hour drive with
and without the activity (same phone, same route).

## Decisions for the owner

| # | Decision | Recommendation |
|---|---|---|
| D1 | An Auto Mode drive started in the background has no Live Activity until Carodo is opened (Apple's rule). Accept for V1? | **Accept.** The alternatives are a server push (refused: P1, P7) or a local notification "Recording · open to follow" (a notification permission Carodo does not ask for today). Revisit the notification with the notification work, if any. |
| D2 | What the Lock Screen shows: phase, elapsed, distance, vehicle name; no speed, no place, no start time | **As listed.** Speed needs an update every few seconds and invites a look while moving. The vehicle name is the person's own label, never a plate. **Revised 2026-11-18:** the average speed joins distance and driving time as a third figure (it moves slowly, so a frame every 30 s stays true); still no current speed. |
| D3 | Still going and Resume on the Lock Screen (LA2) | **Yes**: they mirror the panel and only keep a drive going, so a wrong tap loses nothing. |
| D4 | Finish from the Lock Screen | **Only at a parked stop** ("Looks parked"), beside Still going. Never while moving: the app asks for a hold to finish, a Lock Screen button is one tap. No Pause button. |
| D5 | Log fuel at a stop (LA3): shown after the car has been stopped 2 minutes, with a vehicle chosen; opens the app on the fuel form (Face ID first), since the Lock Screen cannot take numbers | **Yes, as LA3**, with the new link `carodo://vehicle/fuel` (P6). |
| D6 | The final frame "Saved · distance · time" stays 5 minutes, then goes | **Yes.** A tap opens the saved journey. |
| D7 | Order | **LA1 → LA2 → LA3**; LA4 after the first release. |

## Assumed, not checked

- `Activity.update` from the app while it runs in the background on location is not throttled at
  one update per 30 s (Apple documents a budget for pushes, not for local updates): device check.
- A `LiveActivityIntent` run by a Shortcuts automation with the phone locked may start the
  activity (documented in general; not tried here).
- iOS 18.0 behaves as iOS 26 does for all of the above (no iOS 18 simulator: carodo-ios ADR 0018).
