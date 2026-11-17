# 2026-11-17 · Locked relaunch: Auto Mode and Start Drive with Carodo swiped away

Build: carodo-ios `main` at `cd1c7ac` (fix `8b4185d`), installed by the owner with `task device`
before leaving · Phone: the owner's iPhone · Vehicle: <car>
With a passenger: no (every look at the phone is parked) · Start: Auto Mode (drive A), and if the
car has CarPlay or Bluetooth, a Shortcuts automation (drive B) · Plan items:
[`plans/locked-relaunch.md`](../plans/locked-relaunch.md) (section 7),
[`plans/locked-relaunch-plan.md`](../plans/locked-relaunch-plan.md), PV-31

What changed: iOS relaunching Carodo in a locked iPhone (after its first unlock since a restart)
used to wait for the unlock, so a drive started with Carodo swiped away was lost (the morning of
2026-11-17). Now the services start at once. The `launched` line says who launched Carodo
(`state=`) and whether the start waited (`waited=1 store=…`); Start Drive from Shortcuts logs
`shortcut result=…` for every outcome.

The point of the drive is the **swipe-away**: Carodo must be closed from the app switcher before
leaving. Nothing is looked at or touched while moving.

## Before leaving (parked)

1. **parked** · The iPhone has been unlocked at least once since it was last restarted (do not
   restart it now). Auto Mode on, location **Always**. Battery __ %. Time __:__.
2. **parked** · Open Carodo once, then **swipe it away** in the app switcher. Lock the iPhone and
   put it away. Time __:__.

## Drive A (Auto Mode, Carodo swiped away)

3. **parked** · Wait 1–2 min, then drive at least 1.5–2 km (well out of the 150 m parking circle)
   without touching the phone. Time of leaving __:__.
4. **after parking** · Wait about 5 min for the drive to end by itself. Do not open Carodo before.
   Then unlock and open it: the drive is in Journeys. Time __:__.

## Drive B (Shortcuts automation, only if the car has CarPlay or Bluetooth)

Needs the automation "When CarPlay connects (or the car's Bluetooth) → Start Drive", set to run
immediately. Skip this part if it is not set up.

5. **parked** · Swipe Carodo away again, lock the iPhone, engine off and on (or reconnect) so the
   car's audio connects. Note whether any "Open Carodo?" prompt appears (it should not). Time __:__.
6. **drive** · Drive back. **after parking** · Let it end by itself or finish it, then open
   Carodo: the drive is in Journeys. Was a Live Activity on the Lock Screen during the drive? __

## After the drive

7. **at the desk** · Cable the iPhone. In the new session: `task ios:pull-db` (from the workspace
   root), then read the log.

## What the log must show (read by the agent)

`task ios:events LIMIT=400` on the pulled database (local time, no coordinates; `LIMIT` defaults to 80 lines), or
`sqlite3 -readonly <db> "select datetime(occurred_at,'unixepoch','localtime'), kind, detail from
tracking_events where occurred_at > strftime('%s','<YYYY-MM-DD hh:mm>','utc') order by id"`.

| # | Line | Pass | Fail means |
|---|---|---|---|
| A1 | `launched … state=background` a minute or so after leaving (step 3), **no** `waited` | iOS relaunched Carodo and it started at once | `waited=1 store=unreadable` here: opening a class-C file fails while locked after the first unlock (the gate's assumption is wrong on the device); no `launched` at all until step 4: iOS did not relaunch Carodo (region monitoring after a swipe-away) |
| A2 | Right before or after A1: `woke reason=geofence region=parking` (or `significantChange`), `mode to=detecting`, `detection …`, `driveStarted trigger=auto` | Auto Mode ran with no screen | `woke` but no `driveStarted`: detection's own rules, not this fix (read `detection` counts) |
| A3 | The drive ends: `autoFinished`/`driveSaved`, `mode to=standby`, `geofence set region=parking source=drive` | Normal end | — |
| A4 | Step 4's open: `app foreground`, no second `launched` (the process stayed) or one with `state=active` | `state=` tells the person apart from iOS | `state=background` for a tap launch: the capture's moment is wrong (the reviewer's I1) |
| B1 | `launched … state=background` near step 5 (if Carodo was not already running), then `shortcut result=started` and `driveStarted trigger=shortcut` | The automation started the drive with no prompt | `shortcut result=needsAlways` or `needsPermission`: permissions, not this fix; no `shortcut` line and a prompt: the intent ran before the services (should not happen after the first unlock) |
| — | Nothing in any line carries a coordinate, place, plate or id in the shared rendering (Settings → Drive diagnostics) | P5, P9 | — |

Also check the journal: drive A (and B) in `trips`, distance near the trip meter, start within a
few hundred metres of the parking spot (the first metres are missed by design, docs/tracking.md).

## Closing (the agent, once the owner agrees)

- All of A1–A4 pass (and B1 if driven): PV-31 → Closed with the date and the lines seen; spec
  status → verified; result written below.
- Any fail: the cause from the table, a TD or a fix plan; PV-31 stays Open.
- Cleanup, the owner's call: worktree `carodo-ios-locked-relaunch`, branch `fix/locked-relaunch`,
  simulator "Carodo locked-relaunch".

## Result

(to fill in after the drive)
