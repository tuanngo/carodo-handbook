# 2026-11-13 · A hot phone gives up navigation accuracy (L2)

Build: carodo-ios with L2 (uncommitted on `main` until this passes; install with `task device`) ·
Phone: <name> · Vehicle: <car / motorbike>
With a passenger: no (every check is parked, after parking or logs) · Start: manual for the desk
check, as usual for the drive · Plan items:
[`plans/study-followups-thermal-diagnostics-derived.md`](../plans/study-followups-thermal-diagnostics-derived.md) (L2)

What changed: while a drive records, a phone at thermal state `serious` or worse records with `Best`
instead of `BestForNavigation`, even on a charger (`why=hot`); cooling down brings navigation back.
The battery line carries `thermal=`. Rule and reasons: carodo-ios `docs/tracking.md`, Recording GPS.

Part 1 needs the Mac (Xcode simulates the thermal state only while the iPhone is connected); part 2
is an ordinary drive whose log shows the real thermal state.

## Before leaving (parked, at the desk, iPhone on the cable)

1. **parked** · `task device`. If it stops on a schema change, the owner decides (`CONFIRM=erase`).
2. **parked** · Indoors, on the cable (charging): start a drive by hand. It stays "Ready · Waiting
   to move"; that is enough, the GPS rule already runs.
3. **parked** · Xcode → Window → Devices and Simulators → the iPhone → Device Conditions → Thermal
   State → **Serious** → Start. Wait 30 s. Note the time (T-hot).
4. **parked** · Lock the iPhone (Carodo in the background) for 1 min, then Device Conditions →
   **Critical** → Start. Note the time (T-critical). Unlock after 1 min.
5. **parked** · Device Conditions → Stop. Wait 30 s. Note the time (T-cool). Then discard the drive
   (Undo, or Finish; under the short threshold it is not kept).

## The drive (an ordinary one)

6. **parked** · Before leaving: note whether the phone charges on this drive (CarPlay cable) and
   whether it sits in the sun. Drive as usual; nothing to look at while moving.

## After parking

7. **after parking** · Note how warm the phone feels (cool / warm / hot) and the battery %.

## Notes during the drive

Time · what happened (T-hot, T-critical, T-cool, anything odd).

---

## Results (filled by the agent at the review)

Pulled: <database file in drive-data/> · Drives: <id prefix, start–end local, distance, points>

What to read (logs; `task pull-db`, then `task events`):
- Desk check, near T-hot: `gps accuracy=best activity=automotive filter=none why=hot` after a
  `why=charging` line, and `sys battery moment=drive … state=charging … thermal=serious`.
- Near T-critical, with the app in the background: a `battery … thermal=critical` line (proof the
  notification reaches a backgrounded recording app); the GPS line stays `why=hot`.
  If no line comes while locked: L2's fallback (read the state on each fix) is needed.
- Near T-cool: `battery … thermal=nominal` (or `fair`) and `gps … why=charging` again.
- The drive: every `battery` line has `thermal=`; any `why=hot` line, and what came after it
  (fixes per minute, `fixes … accuracy=` rejections); a `launch recovered=` after a `critical` line
  would be the case D2.1 asks to revisit.
- Privacy: the same lines in Settings → Drive diagnostics (shared log) show only the hour and the
  allowlisted fields; no coordinate, place or id on any of them.

| Step | Result | Evidence |
|---|---|---|
| 3 hot on a charger | not run | |
| 4 background + critical | not run | |
| 5 cooled | not run | |
| 6–7 real drive | not run | |

Notes matched to the log: <time → event around it>

Open checks swept (every `Waiting` PV row in `plans/technical-debt.md`, PV-17 being this script's):

| PV | Proven / partly / no data | Evidence or why not |
|---|---|---|
| PV-… | | |

Next: commit L2 (carodo-ios, its 11 files only) once 3–5 pass; tune `hotFrom` only with drive evidence.
