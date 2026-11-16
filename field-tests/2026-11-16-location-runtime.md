# 2026-11-16 · Location runtime: sensors in one folder, one "where is the phone now"

Build: carodo-ios branch `refactor/location-runtime` (slices A and B), installed with `task device`
before the first drive of the day · Phone: <name> · Vehicle: <car / motorbike>
With a passenger: no (every look at the phone is parked, at a stop or after parking) · Start: one
manual drive, one Auto Mode drive · Plan items:
[`plans/location-runtime-plan.md`](../plans/location-runtime-plan.md) (Task 8),
[`plans/location-runtime.md`](../plans/location-runtime.md) (section 8, step 3), PV-26

What changed: the files that touch GPS, the compass and motion moved into `Core/Location` and
`Core/Motion` (no behaviour change), then four behaviours: the compass keeps turning the map when
heading follow is toggled or the tab left and re-entered; the fill-up sheet's stations come from
the recording drive's own fix while it is fresh (no second GPS request then); a lead-in's closest point is projected with
the app's one flat projection (distances within about 0.1 %); Core Motion's follower can be replaced
without a second start. What the simulator already showed and what only this drive shows: PV-26.

Nothing is looked at or touched while moving.

## Before leaving (parked)

1. **parked** · `task device` at the desk. If it stops on a schema change, the owner decides
   (`CONFIRM=erase`); this work changes no schema, so it should not.
2. **parked** · Auto Mode on (Always), a car in the garage, battery __ %. Note the car's trip meter.

## Drive 1 (manual)

3. **parked** · Start a drive by hand. On the Map tap the follow button until the map turns with
   the phone (heading follow). Turn the phone a quarter turn: the map turns. Switch to Journeys and
   straight back to the Map, then tap follow off and on again: the map still turns with the phone
   each time. Note the time if it ever stops turning.
4. **at a stop, engine off** · Pause the drive, lock the phone, wait 2 min, then Resume from the
   Lock Screen (the Live Activity). Note the time. Drive on.
5. **at a stop (a fuel station if there is one)** · "Log fuel" from the Live Activity or the
   recording panel: the Station & time page lists stations within a second or two, the nearest one
   first. Note the time and whether the list was right for where the car stood. Save or cancel.
6. **after parking** · Finish (or let it end by itself). The drive is in Journeys with its route
   whole across the pause.

## Drive 2 (Auto Mode)

7. **parked** · Carodo closed from the app switcher is not needed: just lock the phone, wait
   3 min parked, then drive at least 2 km without touching the phone.
8. **after parking** · Wait for the drive to end by itself (about 5 min), then open Carodo: "Drive
   saved", and both drives are in Journeys. Note the car's trip meter for each.

## Logs (read by the agent after `task ios:pull-db`)

9. Drive 1: one `driveStarted` and one `driveSaved`/`autoFinished`; `gps hold=held` once at the
   start and no `hold=notInUse`/`denied` after the Resume of step 4; `drivePaused` and
   `driveResumed` at the noted times; fixes continue within seconds of the Resume.
10. Drive 1, around the time of step 5: the recording is undisturbed (no gap in the fixes beyond
    the stop's own, no `gps` line other than the stop's lowering and its raise). The log has no
    line for a one-shot request: stopped under 2 min the list comes from the drive's own fix,
    longer from iOS's cached fix or a short request; the owner's note says whether the list was
    right for where the car stood.
11. Drive 2: `woke` → `mode to=detecting` → `detection …` → `driveStarted trigger=auto`, each once
    and in that order; the detection window's events as before this work; `mode to=standby` and a
    `geofence set region=parking … source=drive` after the end.
12. Both drives: points, distance against the trip meter and durations in line with earlier drives
    of the same roads (`task drives`); `task replay` on the pulled database reads stored equal to
    replayed.

## Notes during the drive

Time · what happened (filled by the owner after the drive, or pasted from Apple Notes).

---

## Results (filled by the agent at the review)

Pulled: <database file in drive-data/> · Drives: <id prefix, start–end local, distance, points>

| Step | Result | Evidence |
|---|---|---|
| 1 | passed / failed / not run | <log line or number> |

Notes matched to the log: <time → event around it>

Open checks swept (every `Waiting` PV row in `plans/technical-debt.md`, not only this script's):

| PV | Proven / partly / no data | Evidence or why not |
|---|---|---|
| PV-26 | | |

Next: <fix, tuning or repeat, with the plan item it updates>
