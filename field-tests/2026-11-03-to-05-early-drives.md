# Early device drives, 2026-11-03 to 05

Moved from carodo-ios `docs/operations/device-testing.md` on 2026-11-07: the full notes of the
first drives and the first motorbike script. The repository keeps one coarse line per drive.

## Motorbike test script (first: 2026-11-04 morning)

Before: if the drives on the phone matter, `task pull-db`; then delete the app (the schema changed
on 2026-11-03) and `task device`. In onboarding name the vehicle and pick **Motorbike**; allow
Location, then Motion. Settings → About → Developer shows the battery (a real level, not "–").

On the road (the phone in a mount, not charging if possible):
1. **A manual drive:** Start, ride 10+ minutes through lights and slow traffic, park, walk away.
   It should end by itself about 5 minutes after the stop, ending at the stop.
2. **A wait on the bike:** stop for 6–15 minutes without walking, then ride on: one journey
   (`waitJoin joined`), not two.
3. **Auto Mode on** (the Map's Auto Mode button → turn on, allow Always): leave the parking spot and
   ride; the drive should start by itself (`woke leftParking`, then `driveStarted auto`).

After: `task pull-db` and `task drives`; Developer → Full tracking log → Copy as Text, paste into
the Results below (no coordinates in it). Read per drive: `stop` lines (did a light reach the
5-minute grace?), `fixes` (rejections), `motion` (automotive or cycling?), `battery` (% per hour).

## Results (full notes)

| Date | Build | Scenario | Result | Notes |
|---|---|---|---|---|
| 2026-11-03 | 1.0 (1) | Two short drives with a 12.6-min wait between | Split in two, as the rules say | Auto start 3 s after leaving the parking geofence; ~1 point/s (896 and 535 points); end time at the stop. Led to Stop and wait (`tracking.md`) |
| 2026-11-03 | 1.0 (1) | Manual start indoors, phone still 5 min (night) | 0.4 km, 64 s moving, 13 km/h top speed: GPS drift | 283 fixes, 210 with no speed, reported speeds 1–3.7 m/s at 1.8–2.7 m/s accuracy, drift to 85 m. Led to trusted speeds and the stop anchor (`tracking.md`, rules v3): replayed 0 m |
| 2026-11-04 | 1.0 (1) | Motorbike, manual, 31 min city, one fuel stop | Good: 1 Hz, one segment, accuracy median 8 m, 45 km/h top speed | 1,762 fixes, 5 jumps rejected; 60 → 55 % battery (Low Power Mode on at start). Rules v3: 8.32 → 8.22 km, fuel stop one stop (216 s) instead of two |
| 2026-11-05 | 1.0 (1) | Two iPhones together: a 0.9 km loop round home (VanSam manual), then home → school → home (TuanNgo Auto Mode, Low Power Mode, cars only in the garage), both on a motorbike | Loop: kept on VanSam; nothing on TuanNgo, correctly (never more than 151 m from home, no wake possible). School run: **the way there lost ~2 km**: first fix 2,051 m from home, 455 m short of the school | No `geofence left` while leaving home: it came at 07:05:46 in the same second as `significantChange`, 2 km out. iOS relaunched Carodo at 07:00:45 with no wake logged (a significant change padded by its cell accuracy is the suspect). No lead-in: no drive before it. Detection took 3 s; the vehicle class played no part. Core Motion read the motorbike as 423 s `automotive`, 282 s `unknown`, as on 2026-11-04: motion cannot tell a motorbike from a car. On VanSam a significant change at home opened a window that timed out 12 s before the manual start. Led to region monitoring, place geofences, `ParkedCheck` and the lead-in from a place (`tracking.md`) |
| 2026-11-05 | 1.0 (1) | TuanNgo alone, a 16.8 km loop home → a 7 min wait → home on a motorbike; Auto Mode, a Home place (150 m, saved 6 min before), one car only in the garage | **Whole loop kept**: first fix 18 m from Home, last fix 4 m from it; the two legs (8.6 km, 8.2 km) joined across the wait (437 s, 281 m). Both pending (`confirm_by` set) | Out: iOS relaunched Carodo on a `significantChange` at home, GPS confirmed in 1:47, still inside the Home circle, so no `geofence left place` was needed. The Home region was watched only from that relaunch: a place saved in the app waited for the next return to the foreground (fixed: a saved place is watched at once). Back: `geofence left parking` started it in 19 s, on its own. Later, `geofence left place` and `parking` woke Carodo with no significant change at all: the first region exit seen to wake it by itself. Found: later writes (motion, narration, join) queued the pending drives for backup, `needs_push` 1 (fixed). Battery 75 → 70 % in 44 min, unplugged. `walkAfterStop=none` at the wait, `walkAfterStopS=9` at home |
| 2026-11-04 | 1.0 (1) | Two iPhones carried together (17 Pro Max and 14), a manual drive then an Auto Mode drive, motorbike | **Auto Mode proven on a device**: `woke leftParking` → `driveStarted auto` in 3–4 s on both; both ended by themselves (`autoFinished stopped`) | Manual 16:15: 3,885 m on both. Auto 16:39 (a jam, 49 % stopped): 5.17 vs 5.62 km; same-second separation p50 4 m; smoothed (8 m) 5.37 vs 5.43 km, so the 14 adds ~4 % jitter while moving and the stop anchor held ~220 m of crawl on the 17. Arrival fell 77 s after an automatic end (fixed, rules v5). The 17 ended the manual drive by hand, the 14 by itself after the grace; then Auto Mode started both. **The 14 had no internet the whole time**: it recorded and Auto Mode worked (invariant P1 on a device); its accuracy (p50 14.2 m vs 12.6, more fixes without speed) may be the model or the missing network assistance; its places and gaps waited for the network, and drives that end by themselves now get them on the next return to the app |
