# Showcase drives

**Synthetic drives on public roads. Not recorded drives.** Five made-up car drives (four of
Vietnam's mountain passes and the Ho Chi Minh City – Phan Thiết expressway) for App Store
screenshots, the website and tests. The plan, its decisions and status:
[`../plans/showcase-drives.md`](../plans/showcase-drives.md).

Road lines: © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors (ODbL), routed
by the public OSRM server. Elevation: Open-Meteo's elevation API (Copernicus DEM, 90 m), smoothed
along the road. Anything shown in public that is drawn from these lines credits OpenStreetMap.

| File | What it is |
|---|---|
| `drives.json` | The drives: public waypoints, fixed start times (local, with their zone), seeds, stops |
| `fetch_routes.py` | S1: fetches each road line and its elevation into `routes/` |
| `routes/<id>.gpx` | The road line with elevation (no time): the generator's input |
| `routes/<id>.svg` | A preview: the line, its waypoints and the elevation profile |
| `noise.json` | S0: GPS noise measured on real drives, aggregate figures only |
| `generate.py` | S2: turns each route into a drive of raw fixes (`--check` runs its self-test) |
| `out/<id>.json` | Every fix with every `trip_points` field, 1 Hz, UTC; the app's loader (S3) and tests read these |
| `out/<id>.sim.gpx` | The same fixes, timed, for Xcode's location playback |
| `out/summary.md`, `out/shapes.json` | Per-drive figures; simplified unit-box shapes for the website (no coordinate) |
| `sim_drive.py` | Plays a route on the iOS Simulator so the app records it live |
| `web_shapes.py` | S6: the website's route shapes (Prenn, Mã Pí Lèng, Hải Vân), fitted to each illustration, into carodo-app `apps/web/src/components/site/route-shapes.ts` |

Python 3, standard library only; network through `curl`. Run from the handbook root:

```sh
python3 showcase/fetch_routes.py              # every drive (about 5 min: the elevation API's per-minute limit)
python3 showcase/fetch_routes.py hai-van      # one drive
python3 showcase/fetch_routes.py --preview-only hai-van   # redraw a preview from routes/hai-van.gpx
```

## The routes (S1, 2026-11-15)

| id | Road | Length | Elevation | Climb / descent | OSRM time |
|---|---|---|---|---|---|
| `ma-pi-leng` | QL4C, Đồng Văn → Mã Pí Lèng → Mèo Vạc | 22.4 km | 912–1,255 m | +484 / −556 m | 17 min |
| `hai-van` | QL1 over Đèo Hải Vân (not the tunnel), Nam Ô → Hải Vân Quan → Lăng Cô | 22.9 km | 0–470 m | +481 / −484 m | 27 min |
| `expressway` | An Phú → CT.29 Long Thành – Dầu Giây → CT.01 Dầu Giây – Phan Thiết → Phan Thiết | 161.1 km | 2–259 m | +376 / −375 m | 111 min |
| `ngoan-muc` | QL27, Cầu Sông Pha → Đèo Ngoạn Mục → Thạnh Mỹ (Đơn Dương) | 41.3 km | 188–1,041 m | +950 / −130 m | 31 min |
| `prenn` | QL20, Thác Prenn → Đèo Prenn → Chợ Đà Lạt | 14.0 km | 1,131–1,509 m | +390 / −30 m | 12 min |

A waypoint with `"via": false` marks a stop only: on a road with one way through (QL27, QL4C)
forcing the route through a point made it turn back there. Hải Vân keeps a via point on the pass
road itself, north of the gate, or the route takes the tunnel.

**Redrawing a route.** If a line is wrong, draw it in [gpx.studio](https://gpx.studio/app):
the routing tool, profile car, follow roads on; click the start and the end, drag the line onto
the road you want (that adds a waypoint); check the elevation profile; File → Export → GPX with
elevation; save it as `routes/<id>.gpx` and run `--preview-only <id>`.

## GPS noise on real drives (S0, 2026-11-15)

Measured on 19 car drives (50,914 fixes, 12.8 moving hours, 2026-10-30 to 2026-11-10), mostly city
streets. Full figures in `noise.json`; the analysis script is not kept (it reads real drives).

| Measure | Value |
|---|---|
| Fix interval | 1 s (p99 1.001 s) |
| Horizontal accuracy while moving | two states: good ≈ 2.0 m (p90 2.9) and degraded ≈ 8 m (p90 14.25), degraded 31 % of the time |
| How long a state lasts | good: median 79 s, mean 9 min; degraded: median 6 s, mean 3.5 min (long tails) |
| Horizontal accuracy while stopped | median 13.7 m |
| Cross-track error | sd median 5.1 m (p25 3.7, p75 7.1); autocorrelation 0.93 at 1 s, 0.64 at 5 s, 0.37 at 10 s, ~0 at 20 s: decorrelates in about 11 s |
| Gaps over 3 s | 8.5 per moving hour; length median 11.5 s, p75 35 s, p90 111 s |
| Drift while stopped | rms median 0.75 m, p90 2.0 m |
| Vertical accuracy | median 6.4 m (p10 3.0, p90 11.0) |
| Speed | reported vs from positions: median −0.02 m/s, sd 0.56; speed accuracy median 1.5 m/s |
| Course accuracy | median 25°, p90 180°; missing in 1.6 % of fixes below 1.5 m/s |
| Pressure | lapse −11.9 Pa/m (physics; the measured slope is not usable on flat roads); drift at stops median 1.7 Pa/min |

**What S0's cross-track figure measures.** The ±15 s moving-average residual mixes GPS error with
the road's own turns: on the generated mountain drives the same measure reads about 20 m, on the
expressway 8 m, and no pure noise process reproduces the real 0.37 correlation at 10 s (2026-11-15).
On city streets the 5.1 m is mostly turns. The generator therefore sizes the error from the reported
accuracy instead (below), and S0's cross-track figure is kept as a record, not a target.

What the generator takes from it (S2): the two accuracy states as a Markov chain with these run
lengths, the error as a smooth second-order process (an AR(1) of φ 0.93 driven by an AR(1) of 0.9,
as iOS's filtered fixes drift rather than jitter) sized so its 68 % radius matches the reported
accuracy (generated: 2.3 m good, 8.4 m degraded, against 2.0 and 8.0 reported), gaps at the
measured rate, stop drift and accuracy, speed noise, course accuracy and pressure drift.

## Generating (S2, 2026-11-15)

```sh
python3 showcase/generate.py --check     # self-test: curve speed, accel/brake caps, determinism, stops, gaps
python3 showcase/generate.py             # all drives into out/ (about 1 s); --noise measured for tests
```

Speed follows the road: `v = min(road speed × the driver's slowly drifting pace, √(a_lat × R))`,
a_lat 2.0 m/s² on passes and 1.5 on the expressway, capped by +1.2 m/s² acceleration and −2.0
braking; 12 s still before setting off and 20 s after arriving; stops under 5 min (past the app's
300 s grace a stop ends the drive). `--noise showcase` (the default) starts each drive with a clear
sky, halves the degraded runs and keeps gaps to 4–9 s so a Replay never jumps; `--noise measured`
uses S0's figures as measured. The generated figures are in `out/summary.md`.

## Load all the drives in the app (Simulator, instant)

The DEBUG loader (carodo-ios, `-carodo.showcaseJournal`) writes the five generated drives and the car
into an in-memory journal at launch, through the app's real trip store; nothing is kept.

```sh
xcrun simctl launch $U app.carodo.ios -carodo.hasCompletedOnboarding YES \
  -carodo.showcaseJournal ~/code/carodo/carodo-handbook/showcase -carodo.showcaseNow YES \
  -carodo.debugTab journeys                                  # add e.g. -carodo.debugOpenJourney 4 -carodo.debugOpenReplay YES
```

Newest first: 0 Prenn, 1 Ngoạn Mục, 2 the expressway, 3 Hải Vân, 4 Mã Pí Lèng. Their ends are named
with Apple's lookup a few seconds after launch (needs the network); nothing is kept or synced.

## Try a route in the app (Simulator, real time)

The app records the drive through its real path; nothing is imported. Real time: Prenn takes
about 18 min, Hải Vân 34 min, the expressway 1 h 45.

```sh
U=<simulator UDID>                         # carodo-ios/.env SIM_ID
xcrun simctl privacy $U grant location-always app.carodo.ios
xcrun simctl location $U set 11.876520,108.470100      # the route's first point (routes/<id>.gpx)
xcrun simctl launch $U app.carodo.ios -carodo.hasCompletedOnboarding YES
xcrun simctl openurl $U carodo://trip/start              # tap Open (or tap Start Drive in the app)
python3 showcase/sim_drive.py prenn --udid $U            # plays the route; the app ends the drive ~5 min after arrival
```

Then open what it recorded with the app's DEBUG launch arguments (carodo-ios
`docs/operations/setup.md`), for example `-carodo.debugTab journeys -carodo.debugOpenJourney 0`
with `-carodo.debugOpenReplay YES -carodo.debugReplayAt 0.55` or `-carodo.debugOpenShareCard YES`.

First run (2026-11-15, Prenn, `--profile`): the drive saved and ended by itself; detail, Replay and
the share card drew the pass correctly; 17 restarts of the scenario jumped ahead, so the app kept
12.1 of 14.0 km and Replay shows those jumps as gaps. Plain playback (the default now) has no restart.
