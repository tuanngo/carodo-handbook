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

Read by the agent on 2026-11-17 from `drive-data/carodo-20261117-120206-…sqlite` (pulled 12:02).
Driven: drive A only (Auto Mode, Carodo swiped away, iPhone locked, owner leaving about 11:45).
Drive B and the restart-without-unlock case were not run.

| # | Seen | Verdict |
|---|---|---|
| A1 | 11:49:34 `woke reason=geofence region=parking`, `leftParking`; 11:49:35 `launched recovered=0 discarded=0 state=background … sinceLastS=449 lastMode=standby`, **no** `waited`/`store=` | Pass on what matters: iOS relaunched Carodo in the locked iPhone and the services started at once (the gate's assumption holds after the first unlock). But see A4: `state=background` does not prove it was iOS |
| A2 | `mode to=detecting`, 11:49:52 `detection end=confirmed windowS=17 … conf=0.49`, `driveStarted trigger=auto` | Pass |
| A3 | 11:58:29 `autoFinished reason=walkedAway conf=0.80`, `mode to=standby`, `geofence set region=parking source=drive`; trip `completed`, `end_reason=walked_away` | Pass |
| A4 | 12:01:45 `app foreground`, no second `launched` (the process stayed) | Pass for this step, but **`state=` fails as a signal**: the three launches before leaving (11:35:06, 11:39:45, 11:40:31) read `state=background`, and each has the shape of a tap launch (an `app background` follows seconds later with no `app foreground`, exactly like the old build's tap launches at 07:22:36 and 10:34:33, which read `state=active`). `UIApplication.applicationState` at `didFinishLaunching` reads `.background` for a person's launch too in a scene-based app: the reviewer's I1 in a new form. The owner confirmed all three were opens by hand (step 2), Carodo then closed before the drive |
| B1 | not driven | — |

Journal: drive A is in `trips` (`start_trigger=auto`), 3.03 km, 8 min 50 s, started 11:49:48. Core
Motion dates the departure at 11:48:38, so about 70 s of driving before the relaunch and the first
fix are missing (`fromParkedM=460`): the first metres missed by design, made longer here because the
parking circle was set from a home fix 160 m off (`woke … parked=1 distM=160` all morning).

Outcome: the fix works on the device (A1–A3). PV-31 stays Open: `state=` cannot tell the person from
iOS (fix needed, e.g. the `location` launch option or whether a scene became active), Drive B
(`shortcut result=started`) and the restart case are still unproven.
