# Location runtime: every sensor in one place, with rules a test holds

Design, for the owner's approval. Written 2026-11-16 from the audit
[`../audits/2026-11-16-ios-location-runtime-audit.md`](../audits/2026-11-16-ios-location-runtime-audit.md)
and a read of five open-source recorders (section 3). `carodo-ios` at `ef650f0`. After approval
this becomes a step-by-step implementation plan; no code before that
([`../AGENT_WORKFLOW.md`](../AGENT_WORKFLOW.md), Plan before code).

**Status (2026-11-16):** design approved by the owner with D1, D2 and D3 (section 9); the folder is
`Core/MapLookup`. Next: the implementation plan. The base moved to `b143467` (lookups only while
the app is on screen) after this was written: the plan re-reads the files it names.
**Built (2026-11-16):** [`location-runtime-plan.md`](location-runtime-plan.md), carodo-ios
`567a787` (slice A) and `9ccaa95` (slice B) on `refactor/location-runtime`, waiting for the
owner's merge; section 8's field test is PV-26.

## 1. Why

Location is the core of Carodo, and it has been reviewed more than once. Each review still found
something, because the code that touches GPS, the compass and motion is spread over several
folders and some of it sits where nobody looks:

- a `CLLocationManager` made on every call inside a MapKit lookup (`MapKitStationFinder`);
- a compass made by a View (`MapAtlasView`), with no seam to test its start and stop;
- the recording GPS in `Core/Recording`, the standby GPS in `Core/Location`, its protocol in
  `Core/Tracking`;
- `Core/Location` holding 13 files of which 3 are sensors and the rest are MapKit and place-name
  lookups.

Fixing the audit's four findings one by one would leave the cause. This work fixes them **and**
makes the layout and a few tested rules do the watching, so the next review starts from one folder
and one table, and a new stray sensor fails a test.

## 2. Goals, non-goals, anti-goals

**Goals**

1. One folder per sensor family is the only place that creates the system's managers.
2. Every sensor has a protocol, a fake, and a start and stop that are safe to call twice.
3. Only the composition root creates a sensor; a View or ViewModel never does.
4. One table in `carodo-ios/docs/` says, for each sensor: who owns it, what turns it on, what turns
   it off.
5. The audit's findings F1–F4 are fixed.
6. On/off handling that turns out loose while gathering is tightened in the same work (owner,
   2026-11-16), each with a test.
7. The pattern is written so the next resource family can adopt it by adding a row to the same test.

**Non-goals**

- One `CLLocationManager` for the whole app. Several managers, one job each, stay (section 4).
- `CLLocationUpdate.liveUpdates` for recording or detection. Standard updates stay.
- Any threshold, filter or detection rule (`TrackingRules`, `RecordingGPS`, `StopDetector`).
- The audit's ideas I1 (temporary full accuracy) and I2 (absolute altitude): product and schema
  decisions, their own work.
- The inside of the MapKit and place-name lookups. They only move out of `Core/Location`.
- Other resource families (section 10).
- Schema, API, permissions, entitlements, background modes, dependencies: none change.

**Anti-goals** (a failure even if it works)

- A drive recorded after this work differs from one recorded before, other than by a tightening
  this document names.
- A new abstraction layer over Core Location that every caller must learn. The seams are the
  existing protocols plus two small new ones.
- A rule kept by a document only. Each rule in section 6 is a test or it is not a rule.

## 3. What the reference apps do

Read 2026-11-16 in `~/code/oss/swift`. Driveline, TrailMate and FreePace are permissively licensed
or read for layout only; OutRun and pilgrim-ios are GPL-3.0: **ideas only, no code copied**.

| App | Layout | Taken |
|---|---|---|
| TrailMate | `Services/Location/`: the protocol, the Core Location service and the mock side by side; `Services/Motion/` apart | The protocol, the real adapter and the fake live in one folder; the adapter emits the app's own fix type |
| OutRun | `Recording/`: `LocationService`, `AltitudeService`, `StepService` under one recorder | One service per sensor; updates start and stop in exactly one function, on a state transition |
| Driveline | `Services/LocationService` with `LocationStreaming` and a background-session provider | System types behind small protocols, injected; `start()` and `stop()` ignore a repeat |
| pilgrim-ios | One component per sensor; `HeadingProvider` with a `running` flag | The compass's shape (F2). Also the counter-example: `CLLocationManager()` made ad hoc in views and view models in five places |
| FreePace | `LocationProviding` with `currentLocation` | One source for "where the phone is now" |

Not taken: one manager for everything (OutRun, FreePace: they have two modes and no background
start), a GPS on whenever the app is open (OutRun), `liveUpdates` for recording (Driveline: its
drives start in the foreground).

## 4. Several managers, one job each

**Today** there are five long-lived `CLLocationManager`s and one made per call:

| Manager | Job | File today |
|---|---|---|
| Recording | The open drive's fixes, background updates while it records | `Core/Recording/LocationSource.swift` (`CoreLocationSource`) |
| Standby | Significant changes, the parking circle, place regions | `Core/Location/CoreLocationServices.swift` (`manager`) |
| Detection | 1 Hz fixes during a detection window | same file (`detector`) |
| Permission | Authorization and accuracy status, the prompts | `Core/Location/LocationPermissionManager.swift` |
| Compass | Heading for the Map's heading follow | `Core/Location/CompassHeading.swift` |
| (per call) | One fix for the fill-up sheet | `Core/Location/MapKitStationFinder.swift:40` |

**Kept.** A `CLLocationManager` is a thin handle on the system's location service; its settings
(accuracy, distance filter, background updates) are per manager, so sharing one between recording
and detection would let one job change the other's. Memory per manager is small and the GPS chip
runs once at the highest accuracy any of them asks for; the cost that matters is a manager left
running or made where nobody looks. (Memory is from how the framework works, not measured.)

**Proposed:** six long-lived managers, each with a named owner; the per-call one goes
(`CurrentPosition`, section 5.3).

## 5. Design

### 5.1 Folders

```
Carodo/Core/
  Location/     position, heading and permission sensors. The only place that creates
                CLLocationManager, CLBackgroundActivitySession or reads CLLocationUpdate.
    LocationSource.swift          protocol + BackgroundHold        (from Recording/)
    CoreLocationSource.swift      the recording GPS                (split from the same file)
    ManualLocationSource.swift    its fake                         (split from the same file)
    LocationServicesControlling.swift   protocol                   (from Tracking/TrackingModeController.swift)
    CoreLocationServices.swift    standby + detection
    InertLocationServices.swift   its fake
    HeadingSource.swift           protocol + fake                  (new)
    CompassHeading.swift          the compass
    CurrentPosition.swift         protocol + fake                  (new)
    CoreCurrentPosition.swift     the one-shot fix                 (new)
    LocationPermissionManager.swift
  Motion/       unchanged. The only place that creates CMAltimeter, CMMotionActivityManager
                (and CMMotionManager, CMPedometer if ever used).
  MapLookup/    MapKit and place-name lookups, moved out of Location/ unchanged:
                AppleMapsGapRouter, MapDataCache, MapKitPOISearch, MapKitStationFinder,
                PlaceLookup, PlaceNameCache, POINameLookup, JourneyPointServices
  Recording/    the pure pipeline and the session; creates no sensor
  Tracking/     pure detection and the mode controller; creates no sensor
```

- **No type is renamed.** Files move and one file splits in three; every Swift name stays, so the
  diff outside the moved files is the project file only (XcodeGen picks folders up by itself).
- `TravelHeading` (a pure rule on course and speed) moves to `Core/Tracking` or stays; the
  builder's call.
- Protocols sit beside their adapter and fake (TrailMate's layout), so one folder shows the whole
  sensor. `Recording` and `Tracking` keep depending on the protocols only.
- `MapLookup` is this document's name for the folder: **the owner's decision** (section 9).

### 5.2 The compass (F2)

**Today.** `CompassHeading.headings()` keeps one continuation and stops the compass in a `Task`
that runs after the stream ended, so a new stream started in between is switched off by the old
one's stop. It takes no injected manager and is created in `MapAtlasView`'s `@State`.

**Proposed.**

- A protocol `HeadingSource` (`headings() -> AsyncStream<CLLocationDirection>`) with a fake that
  counts starts and stops; `MapAtlasView` receives it from `DependencyContainer`.
- Each stream carries a token. Ending a stream stops the compass and clears the continuation only
  when its token is still the current one. A second `headings()` while one is live ends the first
  cleanly (one consumer at a time, by contract).
- `MapAtlasView`'s `.task(id: followMode == .heading)` does not change.

### 5.3 One source for "where the phone is now" (F4)

**Today** three places answer it three ways (the audit's table). The parking circle's answer is
part of Auto Mode's wake logic (a fix under 2 min old from either manager, else a request whose
answer becomes the circle only while a circle is still wanted): **a different question, kept as it
is**, and said so in the docs table.

**Proposed** for the other two:

- A protocol `CurrentPositionProviding`:
  `current(maxAge:maxAccuracyM:timeout:) async -> LocationSample?` and a synchronous
  `lastKnown: LocationSample?` (what the system already has, with its age, for a marker).
- `CoreCurrentPosition` answers in this order: the open drive's last accepted fix when it is fresh
  enough (read through a closure the composition root wires to `DriveSessionManager.lastFix`, so
  the sensor folder does not import the session); else the cached fix of its own manager when
  fresh and accurate enough; else one requested fix within the timeout. It never asks for
  permission and returns nil without it. Foreground use only (a sheet, a marker); it is never on
  the tracking path.
- `MapKitStationFinder` takes a `CurrentPositionProviding` and loses its own manager and its
  `liveUpdates` loop. Its limits stay: 120 s, 100 m, 8 s.
- `LocationPermissionManager.lastKnownCoordinate` goes; the Map's first marker reads `lastKnown`.
  Whether the marker should ignore an old fix (it has no age check today) is the builder's call
  with a sound default: keep today's behaviour unless a test shows a stale marker.

Result on a drive: "Log fuel" from the Live Activity lists stations from the drive's own fix, with
no second GPS request.

### 5.4 On/off tightening

Found while reading for this design. Each is **a candidate to confirm in the plan's audit step**,
fixed only with a test on the fake, and listed in the report with its root cause. None changes a
threshold.

| Where | Today | Candidate |
|---|---|---|
| `CoreMotionActivity.follow` | A second `follow` while following returns early: the new handler is dropped silently, the old one stays | Replace the handler, or assert one follower; decide from its one caller |
| `CoreLocationSource.startUpdates` | A second start replaces the handler with no guard; `stopUpdates` and `endDrive` are separate calls a caller can forget one of | A `running` state; a repeat is a no-op or a replace, said in the protocol's comment; a test that every way a drive ends reaches both |
| `CoreLocationServices.didFailWithError` | Logs "Significant changes failed" for any failure, also the detection GPS's and the one-shot request's; a failed one-shot leaves `anchorWhenLocated` set until the next delivery | Name which manager failed; decide whether the pending anchor should clear |
| `Barometer.apply` | Re-evaluated when the drive's recording state changes, not when Motion access changes mid-drive | Probably fine (access rarely changes mid-drive); confirm and say so in a comment, or re-apply on return to foreground |
| `CoreLocationSource.didFailWithError` | Silent | Keep silent for transient errors; a denied error mid-drive should reach the tracking log (no coordinate) if it does not already through the permission path |

Anything found beyond this table that needs a contract, a schema or another feature's files stops
the work and goes to the owner (`AGENT_WORKFLOW.md`, After approval).

### 5.5 The audit's other findings

- **F1.** `DependencyContainer.latestCarDrive()` builds the invite's shape on the main actor. The
  shape work moves to a `@concurrent nonisolated` function. The lighter read (the audit's option
  b: find the newest car drive without decoding 30 routes) is included only if an existing query
  already answers it; a new repository query is out of scope. The size of the hitch is not
  measured: the fix is claimed as correct isolation, not as a speed-up, unless Instruments numbers
  are taken on the iPhone.
- **F3.** `DemoRoute.bearing` calls `Geo.bearing`. `GapHealing.closest` projects through
  `LocalProjection` (its `xy` points; the closest fraction stays a dot product or becomes a small
  `LocalProjection` helper). Lead-in distances move by about 0.1 % (constants 111,195 against
  111,320), inside every lead-in threshold; `GapHealingTests` must pass unchanged.

## 6. The rules, each a test

In `CarodoTests/ArchitectureTests.swift`, read from the sources like the test already there.

| # | Rule | The test fails when |
|---|---|---|
| R1 | Only `Core/Location` creates location managers | `CLLocationManager(`, `CLBackgroundActivitySession(`, `CLLocationUpdate.` or `CLMonitor(` appears in another folder of `Carodo/`. Geocoding and MapKit searches are not sensors: they get their own row when that family is done (section 10) |
| R2 | Only `Core/Motion` creates motion managers | `CMAltimeter(`, `CMMotionActivityManager(`, `CMMotionManager(`, `CMPedometer(` appear elsewhere |
| R3 | Only the composition root creates a sensor adapter | `CoreLocationSource(`, `CoreLocationServices(`, `CompassHeading(`, `CoreCurrentPosition(`, `CoreMotionActivity(`, `Barometer(` appear outside `App/DependencyContainer.swift`. The two permission managers are left out: they hold status, start no updates, and previews create them |
| R4 | Work in a `nonisolated async` function is `@concurrent` | A `nonisolated … async` function without `@concurrent` is not on a short allow-list in the test (today: `JourneyMapSnapshotService.snapshot`, `CloudSyncService.handleEvent` and `nextRecordZoneChangeBatch`), each entry with its reason |
| R5 | One flat-earth projection | A metres-per-degree literal (`111_`) appears outside `LocalProjection` and `Core/PreviewData` |

Behaviour, on the fakes (one test file per subject, as the repo does):

- compass: start, end, start again before the old stop runs; the second stream keeps receiving;
  starts and stops balance;
- current position: the drive's fix wins when fresh; a stale drive fix falls through; no
  permission gives nil; the timeout gives nil;
- station finder: with a recording drive's fix it asks for no other;
- each tightening of 5.4: the test that would have caught it;
- F1: the invite for a synthetic journal is the same as before.

R1 is exact about what it matches and is written first against today's tree to prove it fails on
`MapKitStationFinder` before the fix (a guard that cannot fail guards nothing).

## 7. Docs

In the same change as the code (`carodo-ios/AGENTS.md`, Recipes):

- `docs/architecture.md`: a section "Sensors: one owner each" with the table of section 4 grown to
  every sensor (the six managers, the background hold, the altimeter, motion activity): owner,
  turned on by, turned off by, runs in the background or not. The audit's "Checked and fine" is its
  source. The folder tree and the "wired today" rows follow the moves.
- `docs/tracking.md`: the headings and paths that name moved files; "Core Location notes" points
  to the new section.
- `carodo-ios/AGENTS.md`: the Architecture tree (`Location/`, `MapLookup/`), and one recipe, "A
  sensor or a system manager", naming the folder, the protocol-and-fake pair, the composition root
  and the docs table.
- The handbook: the audit's status line; rows in `plans/technical-debt.md` for what is left open.

## 8. Slices and how each is proven

Two slices, two commits (`carodo-ios/AGENTS.md`, Git: one finished outcome each).

**Slice A: gather, no behaviour change.** The moves and the file split, R2, R4, the docs, F1, and
`DemoRoute.bearing`. (R1, R3 and R5 wait for slice B: each fails today on a file slice B fixes:
`MapKitStationFinder`, `CompassHeading` in `MapAtlasView`, `GapHealing`.) Proof: `task lint`, `task warnings`,
`task test`; the Feed's invite on the simulator. Committed when these pass.

**Slice B: behaviour.** The compass (5.2), `CurrentPosition` and the station finder (5.3), R1, R3
and R5, the tightenings (5.4), `GapHealing` on `LocalProjection`. Proof, in the owner's
order (2026-11-16):

1. **Unit tests** on the fakes (section 6).
2. **Simulator, before and after.** One showcase route (`showcase/sim_drive.py`, the same id, UDID
   from `.env`) recorded on the build before slice B and on the build after: the two drives' point
   counts, distance and durations are compared (`task drives`), and the tracking log's start, hold,
   stop and end events appear once each and in the same order. During the second run: Map in
   heading follow toggled and the tab switched (compass), "Log fuel" opened while recording
   (stations listed, no second GPS start in the log). A simulated route proves plumbing only.
3. **Field test.** A script in `field-tests/` from `_template.md`, written by the agent and driven
   by the owner on the iPhone: a manual drive and an Auto Mode drive, a pause and Resume from the
   Lock Screen, a fill-up logged mid-drive with a passenger or at a stop, the Map's heading follow
   at a stop. The database and logs are pulled (`task ios:pull-db`) and read back: every step's
   evidence is a log line or a number, and the open PV rows are swept as the README says.
4. Slice B is **committed once steps 1 and 2 pass** (owner, 2026-11-16, changed the same day: it
   first waited for the field review). Step 3 follows as a pending validation in
   `plans/technical-debt.md`, naming what the simulator cannot show: the real compass, a
   background start, the hold across a pause, a station list on a real fix.

If a step of 2 or 3 differs from the baseline, it is explained, never tuned away.

## 9. Decisions

**The owner's**

| # | Decision | Recommendation |
|---|---|---|
| D1 | A new folder `Core/MapLookup` for the MapKit and place-name lookups (a new module name, P6) | Yes; the name is open (`MapLookup`, `MapServices`, `Places`) |
| D2 | Slice A committed on green checks, before the field test | Yes: it changes no behaviour, and a smaller slice B is easier to read back from a drive |
| D3 | F4 done now, not deferred as the audit proposed | Yes: it removes the one hidden manager, which is the point of this work |

**Made here, for the owner to check**

- Six long-lived managers (the audit counted five jobs; the one-shot fix becomes the sixth with an
  owner, in place of one per call).
- No Swift type is renamed.
- The parking circle keeps its own "current location" logic.
- The permission managers are exempt from R3.
- F1 is fixed as isolation, with no speed claim unless measured.
- The specs land in `carodo-ios/docs/architecture.md` and `tracking.md`; no new ADR, because no
  decision changes (several managers and standard updates are already how the app works). If the
  owner wants the rule "sensors are created in one folder" to be lasting law, a short ADR is the
  place; say so.

**Tests' folder (owner left it to the agent, 2026-11-16).** `CarodoTests/` stays flat in this
work: it holds about 250 files, other sessions add to it daily, and moving them inside a change to
the recording path would bury that change's diff. New tests follow today's rule (one file per
subject, at the top level). Mirroring `Carodo/`'s folders in `CarodoTests/` is worth doing as its
own `refactor(tests)` commit of pure moves, when no other session is open (section 10).

**Left to the builder**

Exact protocol signatures and file names inside the folders, where `TravelHeading` lives, how the
source-scanning tests match (regular expression or token), the one-shot fix's API (a
`requestLocation` on its manager, or `liveUpdates` in the foreground as today), and each 5.4
candidate's outcome after reading its callers.

## 10. After this

Proposed, not started; rows for `plans/backlog.md` if the owner agrees.

1. **MapKit and place-name lookups** (`MapLookup`): the same rules for `CLGeocoder`,
   `MKLocalSearch`, `MKDirections`, `MKMapSnapshotter` (six files in three folders today), with
   TD-43 (geocoding that may start in the background).
2. **An audit of `UserDefaults.standard`** (read directly in 21 View files across 8 features) and
   of battery, heat and Low Power reads (`BatteryMonitor`, `DriveFlow`, one Journeys view), before
   deciding whether either needs gathering. A count of files, not yet a finding.
3. I1 and I2 from the audit, as product decisions.
4. `CarodoTests/` in folders that mirror `Carodo/` (pure moves, one commit, no session in parallel).

Already in one place and left alone: car audio, the Live Activity, background tasks, the network
client, iCloud, the Keychain.

## 11. Assumed, not checked

- Memory and battery per `CLLocationManager` (section 4): from the framework's design, not measured.
- `DriveSessionManager.lastFix` is the last accepted fix and is fresh while a drive records
  (declared at `DriveSessionManager.swift:211`; its update path not read line by line).
- XcodeGen picks up the moved folders with no `project.yml` change.
- The simulator's tracking log carries the same start, hold and stop events as the iPhone's.
- No other session is editing these files; checked again before the first move
  (`AGENT_WORKFLOW.md`, Working in parallel).
