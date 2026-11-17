# Locked relaunch: Auto Mode starts when iOS relaunches Carodo in a locked iPhone

Design, for the owner's approval. Written 2026-11-17 from the morning drive of 2026-11-17 (no trip
recorded) and the tracking log pulled at 07:29 (`drive-data/carodo-20261117-072944-…`, never
committed). `carodo-ios` at `853f28e`. After approval this becomes a step-by-step implementation
plan; no code before that ([`../AGENT_WORKFLOW.md`](../AGENT_WORKFLOW.md), Plan before code).

**Status (2026-11-17):** approved by the owner; built in carodo-ios `8b4185d`, merged into `main`
in `cd1c7ac`; waiting for the device check (PV-31, [`technical-debt.md`](technical-debt.md)).
Built beyond 5.1–5.3 after the review: `state=` is taken once when UIKit finishes launching
(`LaunchStateCapture`; read when the line is written it raced the person opening Carodo), the
wait says why (`waited=1 store=unreadable|missing`), and Start Drive from Shortcuts logs
`shortcut result=started|recording|onScreen|needsAlways|needsPermission` for every outcome.

## 1. What happened

Auto Mode on, location Always. The owner opened Carodo at 07:01, swiped it away and drove off
around 07:01–07:04. Nothing was recorded. The tracking log:

| Time | Line | Reading |
|---|---|---|
| 07:01:16 | `launched … state=active`, `mode to=detecting` | Opened by the owner; a detection window opens |
| 07:01:22 | `app background` | Then the swipe: the window's 120 s timeout is never logged |
| — | (nothing until 07:22:35) | |
| 07:22:35 | `woke reason=significantChange parked=1 …`, `launched … state=active sinceLastS=178 lastMode=detecting` | The owner unlocks and opens Carodo |

`sinceLastS` is measured from the **process start** (`LaunchContext.Origin.at`, read in
`CarodoApp.init`) to the run before's last line (07:01:22). 178 s puts the process start at about
**07:04:20**: iOS relaunched Carodo as the car left (a parking-region exit, most likely), and the
process logged nothing for 18 minutes, until the owner unlocked the iPhone.

## 2. Cause

`AppLaunch` (`Carodo/App/AppLaunch.swift`) starts the services (database, Auto Mode, recording,
the log) only when `UIApplication.isProtectedDataAvailable` is true, else waits for
`protectedDataDidBecomeAvailableNotification` or a screen appearing. Its comment and
`docs/architecture.md` ("Launch before the first unlock") assume that value is false only **before
the first unlock since a restart**.

It is not: Apple documents `isProtectedDataAvailable` as false whenever data protection is on and
the device is **locked**, the state of files of class `complete`. Carodo's files are not of that
class: there is no `default-data-protection` entitlement, so the database, its `-wal`/`-shm` and
UserDefaults take iOS's default, `completeUntilFirstUserAuthentication`, readable while locked
once the iPhone was unlocked after its restart (`DatabaseManager.makeDatabase` already says so).
`CloudSyncService` writes its track files with the same class; only `BackupService` uses
`complete`, for a backup the person makes in the open app.

So every time iOS relaunches Carodo from terminated while the iPhone is locked (in a pocket, in a
car: exactly when Auto Mode is needed), the services wait for the unlock and the drive is lost.
Drives recorded by Auto Mode so far had a process still alive (suspended): iOS woke it, nothing
was launched.

**A second fault hid it.** No `launched` line in any pulled database says `state=background`, not
even this 07:04 relaunch. `CarodoApp.init` reads `UIApplication.shared.applicationState` before
UIKit has finished launching, where it does not yet say who launched the process. The log cannot
tell "iOS relaunched Carodo" from "the person opened it". The 2026-11-09 silence read as "iOS
relaunched no fresh install" (`docs/tracking.md`, Was Carodo running?) may be the same fault;
unproven.

**The Shortcuts start is hit too.** A "When CarPlay / Bluetooth connects → Start Drive"
automation runs `StartDriveIntent` in Carodo's process. Swiped away, the process is launched for
the intent; locked, `AppLaunch` has no container yet, so `DriveStartActions.start` answers
`.needsApp` (`CarodoApp.init`) and the intent asks to continue in the foreground
(`continueInForeground` / `needsToContinueInForegroundError`): the drive starts only if the person
unlocks and opens Carodo, in the car, at the wheel. Ignored, the drive is lost. With the process
still alive (not swiped away) the intent starts the drive in the background, as designed. The
`carodo://trip/start` deep link always opens the app, so it needs the unlock anyway and is not
changed by this fault.

Not a cause: the deleted places (Home and School are soft-deleted, so `places=0`); Auto Mode
watches the parking region and significant changes without them. Being offline makes iOS's region
and significant-change reports coarser, but iOS did relaunch Carodo here.

## 3. References: how others handle it

Read 2026-11-17 in `~/code/oss/swift/`:

| App | Background launch | Waits for protected data? |
|---|---|---|
| Driveline | Opens its SwiftData store and every service in `App.init` (`AppBootstrap.boot()`), no gate. Its "automatic" drives start from a Shortcuts automation (`AppIntents.swift`), not region or significant-change wakes | No |
| OutRun | Manual workouts only; `LifecycleLoggingViewModifier` only **logs** `protectedDataWillBecomeUnavailable` / `DidBecomeAvailable`, it gates nothing | No |
| pilgrim-ios | Manual walks only; `allowsBackgroundLocationUpdates` during a walk; no relaunch handling | No |

None relaunches from a region exit, so none meets this case; none gates its start on
`isProtectedDataAvailable`. All three rely on the default file class, readable while locked after
the first unlock. Both point the same way as this design: start at once, and treat only "before
the first unlock" as the case to wait for. Driveline and OutRun write exports with
`.completeFileProtection`, which is right for a file made in the open app, as Carodo's backup does.

## 4. Goals, non-goals

**Goals**

1. A relaunch by iOS while the iPhone is locked, after its first unlock since a restart, starts the
   services at once: Auto Mode's standby, detection and recording run as on any launch.
2. Start Drive from a Shortcuts automation (CarPlay or Bluetooth connect) with Carodo swiped away
   and the iPhone locked starts the drive in the background, with no prompt, when location is
   Always (as with the process alive).
3. Only a launch before the first unlock since a restart waits (database and UserDefaults
   unreadable then); it starts on the unlock as today.
4. The `launched` line says truly who launched the process and how long the start waited.
5. `docs/architecture.md`, `docs/tracking.md` and `docs/specs/drive-recording.md` (Starting) say
   what is true.

**Non-goals**

- Why iOS delays or skips a relaunch after a swipe-away (iOS's decision; `docs/tracking.md`,
  Wake strategy).
- A drive during the wait before the first unlock: still not recorded (no file can be read).
- Wake quieting, `DeparturePace`, places: unchanged.
- Schema, API, entitlements, background modes, file protection classes, dependencies, targets:
  none change.

## 5. Design

### 5.1 When to start: can the store be read

`AppLaunch` takes `canReadStore: () -> Bool` instead of `isProtectedDataAvailable`. The live
check, `StoreReadability` (`App/`, pure apart from one file read):

- the database file exists: open it for reading and read its first bytes (`FileHandle`). Success
  means the store's class is readable now; a failure (`EPERM`, before the first unlock) means wait;
- the database file does not exist (a fresh install, never opened): fall back to
  `isProtectedDataAvailable`. A fresh install is opened by the person first, so this path never
  meets a locked relaunch.

The waiting path is unchanged: `protectedDataDidBecomeAvailableNotification` or a screen appearing
calls `startIfReady()`, which starts once.

Why the database file and not a new probe file: it is the file whose class decides whether the
start can work, and nothing new is stored. UserDefaults shares its class.

### 5.2 Who launched: read where UIKit knows

`state=` is read when the `launched` line is written (after the launch reconciliation, an async
task; UIKit has finished launching by then), not in `CarodoApp.init`. A relaunch by iOS reads
`background`, a launch by the person `active` or `inactive`. With the start no longer waiting
(5.1), the line is written seconds after the process starts, so the state is still the launch's.

Considered and left out: an `UIApplicationDelegateAdaptor` reading `launchOptions[.location]`
(which event launched Carodo). It adds an app delegate and an ordering question between it and
`App.init` for a detail the log does not need: `background` already says "not the person". Taken
up if a device shows `background` from causes worth telling apart.

### 5.3 How long it waited

`launched … waitedS=…` when the start waited for the store (Developer only: with the process's
start it could tell a minute, P9), and `waited=1` in the shared log. With the fix this should only
ever appear after a restart.

## 6. Tests

- `AppLaunchTests` (new; `AppLaunch` already takes its check and start as closures):
  store readable with `isProtectedDataAvailable` false (the locked iPhone) → starts in `begin()`;
  store unreadable → waits, starts on the notification, once; a screen appearing after the
  notification starts nothing twice.
- `StoreReadabilityTests`: a readable file → true; a missing file → the fallback's answer; an
  unreadable file (a path that cannot be opened) → false.
- `DriveStartActions` as `CarodoApp` wires it: with the store readable and the iPhone locked, the
  container exists by the time the intent asks, so `start` answers a started drive, not `.needsApp`
  (the intent's own call is not unit-testable; the wiring is).
- `TrackingLogFieldsTests`: `waited` shared, `waitedS` Developer only.
- The `UIApplication.State` → `LaunchState` mapping, and the launched line with `waited`.

## 7. Device check (PV, the owner's iPhone)

1. Auto Mode on, Always. Open Carodo, swipe it away, lock the iPhone, drive off.
2. Expected: `launched … state=background` within a minute or two of leaving, no
   `waited`, a detection window, `driveStarted trigger=auto`, the drive in the journal.
3. Shortcuts automation "When CarPlay (or the car's Bluetooth) connects → Start Drive", set to run
   immediately. Swipe Carodo away, lock the iPhone, connect in the car: `launched … state=background`,
   `driveStarted trigger=shortcut`, the Live Activity on the Lock Screen, no "Open Carodo?" prompt.
4. Restart the iPhone, do not unlock, move: `waited=1` on the first unlock (a drive before it is
   lost, as documented).

## 8. Docs changed with the code

- `carodo-ios/docs/architecture.md`, "Launch before the first unlock": the store's readability,
  not `isProtectedDataAvailable`; locked after the first unlock starts at once.
- `carodo-ios/docs/tracking.md`, Was Carodo running?: `state=` (when it is read), `waited`; the
  2026-11-09 reading marked as possibly this fault.
- `carodo-ios/docs/specs/drive-recording.md`, Starting: Start Drive from an automation starts in
  the background with Carodo swiped away and the iPhone locked.
- `technical-debt.md`: a PV row for section 7.

## 9. Open questions for the owner

None on product or contracts: no schema, API, entitlement or dependency changes. The approval asked
is the design itself (sections 5.1–5.3). Section 5.2 was simplified on 2026-11-17 after the
refactor of the same day: no app delegate, `state=` read when the line is written.

Risk: the 2026-11-17 cause is inferred from `sinceLastS` and Apple's documentation, not seen in a
line (the second fault is why). Section 7 is the proof; if the device check still shows a silent
relaunch, the cause is elsewhere and this spec is revisited before more code.
