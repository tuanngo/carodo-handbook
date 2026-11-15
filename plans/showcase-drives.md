# Showcase drives: synthetic GPS on real mountain passes

Status: **S0–S3 done** (2026-11-15). S3 is carodo-ios `7139b9a`: DEBUG
`-carodo.showcaseJournal <folder>` (+ `-carodo.showcaseNow YES`) loads `showcase/` into an in-memory
journal through the real trip store; tried on the Simulator (Journeys, Mã Pí Lèng's detail and
Replay, Hải Vân's share card). Next: S4 (tests on the drives), S5 (screenshots), S6 (web shapes).
The drives' ends are named with Apple's lookup as saved drives are (carodo-ios `d67b0e0`: "X. Đồng
Văn → X. Mèo Vạc", "P. Hải Vân → X. Chân Mây - Lăng Cô"); the journal stays in memory, no iCloud.

One set of made-up car drives on real public roads (four of Vietnam's best-known passes and one
long expressway run), generated as realistic raw GPS fixes. It serves three uses:

1. **Showcase**: App Store screenshots and the website, taken from the app's real screens.
2. **Test data**: the iOS tests can run the recording pipeline, stops, elevation, Replay and the
   share card on believable mountain roads, without the real drives in `drive-data/`.
3. **Simulator drives**: timed GPX files Xcode plays as location, to record a "live" drive through
   the real tracking path for the recording and Auto Mode screens.

Everything this plan produces lives **in this handbook** (`showcase/`), never in `carodo-ios` or
`carodo-app` (owner, D1): the app and its tests read it from a path given at run time, the way
`task replay` reads `drive-data/`.

## Owner decisions (2026-11-15)

- **D1 — Where the data lives:** committed **in carodo-handbook** (`showcase/`), not in the app
  repositories. They hold synthetic drives on public roads, generated from OpenStreetMap lines,
  never a recorded drive; each folder's README says so. The app repositories' "never commit a
  location trace" (P5) is untouched.
- **D2 — Generator:** **Python** (standard library only), in the handbook: it is showcase data, and
  Python is quicker to write and closer to how `drive-data/` is analysed.
- **D3 — Drives: car only.** Đèo Ngoạn Mục, Đèo Hải Vân, Mã Pí Lèng, Đèo Prenn, and one long
  expressway drive from Ho Chi Minh City (via Long Thành – Dầu Giây) to Phan Thiết (owner,
  2026-11-15), for the long curves at highway speed. No motorbike and no short city trips.
- **D4 — OpenStreetMap credit:** in `showcase/README.md`, and a small "Route shapes ©
  OpenStreetMap contributors" line on the website wherever a real road shape is drawn (S6).
- **D5 — Dates:** the drives' dates and times are fixed in the handbook (`showcase/drives.json`);
  the app may shift them to "now" for a screenshot (a flag, S3).
- **D6 — Routes:** the agent draws them (OSRM over OpenStreetMap, elevation from a public terrain
  model) and shows a preview for the owner to confirm; the owner redraws any that is wrong in
  gpx.studio (guide below).

## Audit (what exists today)

- **`carodo-ios/Carodo/Core/PreviewData/SampleJournal.swift`** (302 lines, `#if DEBUG`): N
  synthetic drives on a made-up city grid around (10.7769, 106.7009); straight legs at constant
  speed ±15 %, a few metres of jitter, altitude fixed at 8 m, accuracy fixed at 5 m, no course or
  pressure. `fill(_:vehicles:count:now:)` writes the garage and drives through the real `TripStore`
  (begin → samples → finish), deterministic per `now`. Built for scale and performance, not looks.
- **Launch arguments** (`carodo-ios/docs/operations/setup.md`): `-carodo.sampleJournal N`
  (in-memory database, the live repositories), `-carodo.sampleData YES`,
  `-carodo.debugSamplePlaces`, `-carodo.debugMapCamera`, among others.
- **`TripPointRecord`** (`trip_points`): `recorded_at`, latitude, longitude, `altitude_m`,
  `speed_mps`, `course_deg`, `horizontal_accuracy_m`, `vertical_accuracy_m`, `speed_accuracy_mps`,
  `course_accuracy_deg`, `pressure_kpa`, `segment`, `sequence`. A believable fix fills them all,
  pressure included (elevation uses the barometer).
- **`CarodoTests/DriveDataReplayTests.swift`** and `task replay`: replay the pulled real drives
  through today's `RouteRecorder` and print figures only, skipped unless `CARODO_DRIVE_DATA` is set.
  This is the pattern the showcase tests follow (`CARODO_SHOWCASE`).
- **`drive-data/`** (workspace root): databases and `.carodo` backups pulled from three iPhones
  since 2026-11-10; readable and analysable locally (carodo-ios `AGENTS.md`, Development data).
- **Mockups**: the share card (Direction D), the Replay video frame, `gallery/route-glyphs-*.png`.
  The Replay frames show a real Ho Chi Minh City map and the `drive-N` glyphs come from real drives:
  neither is reused in public.
- **Web**: `carodo-app/apps/web/src/components/site/feature-art.tsx`, three SVG illustrations with
  a made-up curve (2026-11-15).
- **Routing check (2026-11-15):** the public OSRM server answered a route between two points near
  Đèo Ngoạn Mục; the request carries only public road coordinates.

Not checked yet (assumptions): that `RouteRecorder` takes 1 Hz fixes with correlated noise without
a rule change (expected: it handles real drives); that the iOS Simulator can read a JSON file from a
path on the Mac (expected: Simulator apps are not sandboxed from the host); that the Simulator's GPX
playback honours `<time>` at 1 Hz; the expressway speed limits (assumed 120 km/h on Long Thành – Dầu
Giây and 90 km/h on Dầu Giây – Phan Thiết; to confirm before S2).

## The drives

| id | Road | Approx. length | What it shows |
|---|---|---|---|
| `ngoan-muc` | Đèo Ngoạn Mục, Sông Pha → Đơn Dương (QL27) | ≈ 20 km | hairpins, a 900 m climb, a viewpoint stop |
| `hai-van` | Đèo Hải Vân, Đà Nẵng → Lăng Cô (QL1, the pass road) | ≈ 21 km | the famous pass by the sea; a stop at the gate on top |
| `ma-pi-leng` | Mã Pí Lèng, Đồng Văn → Mèo Vạc (QL4C) | ≈ 22 km | the hero for Replay and the share card |
| `prenn` | Đèo Prenn into Đà Lạt (QL20) | ≈ 10 km | short and fast; a second drive in Lâm Đồng |
| `expressway` | Ho Chi Minh City → Long Thành – Dầu Giây → Phan Thiết (or → Vũng Tàu, S1) | ≈ 200 km (≈ 100 km) | long curves at highway speed, a rest stop, a long Replay |

All in one car (the garage holds one or two cars named for the screenshots). Dates in
`showcase/drives.json` read as one trip: the expressway out, then the passes on following days.

## Pipeline

```
showcase/routes/<id>.gpx        road line + elevation        (OSRM / gpx.studio, OSM ODbL)
        │
        ▼  python3 showcase/generate.py   (deterministic, a seed per drive)
        │     model parameters from showcase/noise.json (S0, numbers only)
        ├─► showcase/out/<id>.json         raw fixes, every TripPointRecord field
        ├─► showcase/out/<id>.sim.gpx      timed GPX for Xcode location playback
        ├─► showcase/out/summary.md        length, duration, average/top speed, stops, climb
        └─► showcase/out/shapes.json       simplified, normalised shapes for the web (S6)
```

### The drive model

1. **Resample** the line every metre; ease sharp vertices so no corner is a kink.
2. **Speed from curvature:** radius R from three points about 20 m apart; target
   `v = min(v_road, sqrt(a_lat × R))`, `a_lat` ≈ 2.0 m/s² on passes and 1.5 on the expressway;
   `v_road` per stretch (pass 40–50 km/h, national road 60–70, expressway 90–120); a forward and a
   backward pass cap acceleration (+1.2 m/s²) and braking (−2.0 m/s²). Hairpins fall to 15–20
   km/h; straights reach the limit.
3. **Events:** a viewpoint or summit stop of 4–10 min on each pass, a 15 min rest stop on the
   expressway, a toll-gate slowdown; a few seconds of slowing before each.
4. **Time:** one fix a second from the start in `drives.json` (local time, stored in UTC).
5. **Noise** (parameters from S0):
   - horizontal error as a correlated random walk (AR(1)), not white noise, so the line wobbles like
     a real one; a little larger under cliffs;
   - `horizontal_accuracy_m` from the measured distribution, moving with the error;
   - short gaps (a few seconds without a fix) at the measured rate;
   - drift while stopped, as measured;
   - `speed_mps` from the true speed plus noise; `course_deg` from the motion, −1 when slow; their
     accuracies as measured.
6. **Elevation:** altitude from the line's elevation plus noise; `pressure_kpa` from the barometric
   formula on the true altitude, with a slow drift; vertical accuracy as measured.
7. **Determinism:** a seed per drive; the same route, parameters and seed always give the same file
   (the generator's self-test hashes it).

## Slices

- **S0 — Calibrate on real drives** (agent, local). A scratch analysis of `drive-data/` measures the
  fix interval, the horizontal and vertical accuracy distributions, the error's autocorrelation
  (against a smoothed line), gap rate and length, drift while stopped, speed and course noise, and
  pressure drift. Output: `showcase/noise.json` and a table in `showcase/README.md`, numbers only,
  with the drives counted and their date range. No coordinate and no plot of a real drive is
  committed; the analysis script stays out of Git.
- **S1 — Routes** (agent, owner confirms). For each drive: waypoints on public places (towns, the
  pass's ends), the line from OSRM, elevation from a public terrain model, saved as
  `showcase/routes/<id>.gpx`, plus `showcase/routes/<id>.svg`, a preview with the elevation
  profile. The owner confirms each, or redraws it in gpx.studio (guide below). The owner also picks
  Phan Thiết or Vũng Tàu for the expressway drive.
- **S2 — Generator.** `showcase/generate.py` and its self-test (`python3 showcase/generate.py
  --check`): speed on a circle of known radius, the acceleration caps, stops and gaps present,
  determinism by hash. Writes `out/` and `summary.md`.
- **S3 — Load it in the app** (carodo-ios, DEBUG; needs the owner's go on that repo).
  `-carodo.showcaseJournal <folder>` reads `out/*.json` and `drives.json` from the Mac path (the
  Simulator only) and writes the car, the drives and two made-up places through the real
  `TripStore`, in memory, beside `SampleJournal` and sharing its write path; `-carodo.showcaseNow
  YES` shifts the dates so the last drive ends today. Nothing is bundled in the app.
- **S4 — Tests on the showcase** (carodo-ios). `ShowcaseDriveTests`, skipped unless
  `CARODO_SHOWCASE` names the folder (as `CARODO_DRIVE_DATA`): each drive through today's
  `RouteRecorder`; distance within 3 % of the line, the planned stops found and no false one,
  elevation gain within 10 % of the line's, the share card's privacy trim at both ends, Replay's
  timeline covering the drive. Prints figures only. A failure is a recorder regression or a mistake
  in the data, never tuned away. A `task ios:showcase` runs it.
- **S5 — Screenshots.** The App Store set (6.9" iPhone, Light and Dark, English and Vietnamese):
  Map, Journeys, a detail mid-Reveal, Replay on Mã Pí Lèng, the share card editor, Garage,
  Passport, and the recording panel from a Simulator GPX playback of `hai-van`. Captured on the
  Simulator from the showcase journal; the same frames feed the website.
- **S6 — Web shapes** (carodo-app). `out/shapes.json` (Mã Pí Lèng and Hải Vân, about 100 points,
  normalised to a box, no coordinate) is copied into `feature-art.tsx` as SVG paths in place of the
  made-up curve, with the OpenStreetMap line (D4).

Order: S0 and S1 together → S2 → S4 → S3 → S5 → S6. After S2 the data is usable for tests.

## Drawing a route in gpx.studio (owner, when a line is wrong)

1. Open https://gpx.studio/app (free, no account needed for this).
2. In the left toolbar, choose the **routing** tool (the route icon); set the profile to **car**
   and keep **follow roads** on.
3. Click the start, then the end: the line snaps to the road. To make it take a particular road
   (the old Hải Vân pass road, not the tunnel), drag the line onto that road; that adds a waypoint.
4. Check the **elevation profile** at the bottom: a pass shows its climb.
5. **File → Export**, format **GPX**, keep elevation; name it with the drive's id
   (`hai-van.gpx`) and put it in `carodo-handbook/showcase/routes/`, replacing the agent's.

## Acceptance criteria

- `python3 showcase/generate.py --check` passes; the same inputs give byte-identical outputs.
- Every fix in `out/` fills every `TripPointRecord` field plausibly; `summary.md` lists each drive.
- `noise.json` records the real drives it was measured on. The generated moving accuracy matches the
  real one (median 2.26 m both; degraded share 21 % against 31 % over five drives) and so does the
  gap rate (8.6 against 8.5 per moving hour, `--noise measured`). The error autocorrelation is **not**
  compared: S0's cross-track measure mixes the road's turns with the GPS error (README, S0), so the
  error is sized from the reported accuracy instead (68 % radius 2.3 m against 2.0 reported).
- With `CARODO_SHOWCASE` set, `ShowcaseDriveTests` passes on all five drives in under 10 s.
- `-carodo.showcaseJournal` opens the Simulator app on the five drives and the car, with no network,
  no location service and no device database touched.
- Each `*.sim.gpx` records a drive through the real tracking path of the expected length (±5 %).
- Nothing derived from `drive-data/` except `noise.json` is committed; no showcase coordinate is in
  `carodo-ios` or `carodo-app` (only S6's normalised shapes, which carry none).

## Non-goals

- No change to `RouteRecorder`, stop detection or any recording rule; a finding goes to the owner.
- No GPX import in the app (the owner's "No database or GPX export" stands).
- `SampleJournal`'s grid stays for scale and performance tests.
- No real map imagery and no real recorded drive in public.
- No App Store submission work beyond the screenshot list.

## Files

- `carodo-handbook/showcase/` (new): `README.md`, `drives.json`, `noise.json`, `routes/`,
  `generate.py`, `out/`; a line in the handbook README's table.
- `carodo-ios` (S3, S4): a `ShowcaseJournal` beside `Core/PreviewData/SampleJournal.swift`, the
  launch arguments, `CarodoTests/ShowcaseDriveTests.swift`, `Taskfile.yml` (`showcase`),
  `docs/operations/setup.md`.
- `carodo-app/apps/web` (S6): `components/site/feature-art.tsx` and the README.
