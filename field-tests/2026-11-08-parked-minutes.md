# 2026-11-08 · The parked minutes are cut off the drive

Build: carodo-ios `af84aa1` or later (install before the first drive of the day) · Phone: <name> ·
Vehicle: <car / motorbike>
With a passenger: no (all checks are parked or after parking) · Start: manual and Auto Mode ·
Plan items: `plans/gps-engine.md` (Field: "Parked minutes cut off")

What changed (carodo-ios `fca3622`, `af84aa1`): a drive that ends at a stop now ends when the car
stopped, and the GPS fixes recorded while it waited parked are deleted when it is saved. Three ways
to end at a stop, one drive each. Rename this file if the drive is on another day.

## Before leaving (parked)

1. **parked** · Before the first drive: export from the app if the drives on the phone matter, then
   `task device` (it stops before erasing anything if the schema changed). Auto Mode on. Note the
   battery %.

## Drive A: it ends by itself, staying in the car

2. **after parking** · Drive 10+ min. Park, stay in the car with the phone in the mount, don't touch
   it and don't walk. Note the clock time the car stops (A-stop).
3. **after parking** · About 5 min later the panel shows "Looks parked · ends in …", then the drive
   is saved by itself. Note the time it disappears (A-saved). Good: in Journeys the drive ends at
   A-stop, not at A-saved.

## Drive B: Finish by hand after waiting

4. **after parking** · Drive 10+ min. Park and wait 1–2 min without touching the phone. Note the
   stop time (B-stop), then hold Finish. Good: the summary and Journeys say it ended at B-stop.

## Drive C: the app is closed while parked

5. **after parking** · Drive 10+ min. Park, note the stop time (C-stop), then within 1–2 min swipe
   Carodo away in the app switcher (force-quit) while it is still recording.
6. **after parking** · Wait **more than 10 min** without opening Carodo (sooner, it carries the drive
   on instead). Then open it. Good: the drive is in Journeys and ends at C-stop.

## After parking

7. **after parking** · For each drive, open Trim: the timeline ends where the drive ends; no long
   flat stretch at the end.

## Notes during the drive

Time · what happened (A-stop, A-saved, B-stop, C-stop, the time Carodo was opened again, anything odd).

---

## Results (filled by the agent at the review)

Pulled: <database file in drive-data/> · Drives: <id prefix, start–end local, distance, points>

What to read per drive (logs):
- `task events`: A `autoFinished stopped stoppedS=…`; C `launched recovered=1` (not `resumed=1`).
- `ended_at` against the noted stop time (within ~30 s: the stop counts from its first slow fix).
- The last packed fix is at `ended_at`, none after it, and `point_count` has no ~300 parked fixes:
  `SELECT substr(id,1,8), datetime(ended_at,'unixepoch','localtime'), end_reason FROM trips`, and the
  track's last fix through `task replay`.
- Distance and moving time match `task replay` (the summary re-derived from the fixes kept).

| Step | Result | Evidence |
|---|---|---|
| 3 (A) | not run | |
| 4 (B) | not run | |
| 6 (C) | not run | |
| 7 (Trim) | not run | |

Notes matched to the log: <time → event around it>

Next: <fix, tuning or repeat, with the plan item it updates>
