# GPS accuracy tiering — audit and plan (2026-11-09)

Status: **built 2026-11-09**: 1 (docs), 2a (shadow), 3 (B1 upgrades; on battery turned back **off**
after the corner analysis below). 2b waits for field data. Source of truth for thresholds stays `carodo-ios/docs/tracking.md`.

Related: [`gps-engine.md`](gps-engine.md) §3 B1, [`gps-perf-audit.md`](gps-perf-audit.md).

## 1. Audit of `desiredAccuracy`

| Where | Value | When |
|---|---|---|
| `Core/Recording/LocationSource.swift` `CoreLocationSource.init` | `Best` | default before the session configures it |
| `CoreLocationSource.configure` | `BestForNavigation` / `Best` / `HundredMeters` | from `RecordingGPS.settings`, recording only |
| `Core/Location/CoreLocationServices.swift` detector | `Best`, fixed | the detection window (120 s, +120 s once) |
| `CoreLocationServices` `manager.requestLocation()` | iOS default (`Best`) | one shot, anchoring the parking circle with no fresh fix |
| `Core/Location/MapKitStationFinder.swift` | `CLLocationUpdate.liveUpdates()` default | foreground station search, first fix ≤ 100 m or timeout |

No `LiveConfiguration` anywhere.

- `BestForNavigation` only while a drive records **and** `BatteryMonitor.isCharging`
  (`.charging`/`.full`); never unplugged, never in the detection window. Device log agrees
  (2026-11-09 08:03 `navigation why=charging`; every other line `best why=battery`).
- **Decided:** charging only, no CarPlay condition (wired CarPlay reports charging; wireless
  CarPlay unplugged is on battery → `Best`).
- A1: `docs/tracking.md` "Core Location notes" claimed `BestForNavigation`: fixed.
- A2: `requestLocation()` stays at `Best` (the circle's centre matters).

## 2. Early exit of the detection window (2a shadow → 2b)

Evidence: 7 confirmed windows confirmed in 3–13 s; 2 false windows (both `significantChange`,
`car=none`) ran 120 s with 121–122 fixes, `maxKmh=4`, `netM=0|10`. The false 2026-11-07 window
read automotive in Core Motion *before* it opened, so Motion is read **since the window opened**.
Max spread and trusted speed were not logged: thresholds are hypotheses.

| Condition | Threshold |
|---|---|
| Check from (`significantChange`) | 30 s |
| Check from (`leftParking`, `leftPlace`, `departing`) | 60 s |
| Check from, no Motion access | 60 s |
| Usable fixes | ≥ 15 |
| Max spread from the first usable fix | < 15 m |
| Max trusted speed (speed > 2 × accuracy) | < 1.0 m/s |
| Core Motion since the window opened | no confident (≥ medium) automotive or cycling |
| Car audio | not connected |
| Window | not extended |

Motion is asked **at most once per window**: the GPS conditions are monotone (spread and
speed only grow), so once they pass Motion is asked; the answer latches (vehicle → blocked, clear →
would exit, no access → GPS-only from 60 s). Never a query per fix.

2a: `earlyExit` off; the `detection` line adds `usable=… spreadM=… maxTrustedMps=…` and
`wouldExitS=…` or `still=vehicle|carAudio`. 2b: turn on after field windows show no real drive
would have been closed.

## 3. B1 on battery

| Change | Before | Now |
|---|---|---|
| Lower at a stop on battery | off | off (was turned on, then back off after the corner analysis) |
| Held stop before lowering | 60 s | **90 s on battery**, 60 s in Low Power Mode |
| Lowered | `HundredMeters` + 50 m filter | same |
| Raise | any fix | any fix, **or live Core Motion** (confident automotive not stationary, or cycling), or power |
| Log | `gps … why=` | `+ raisedBy=fix|motion|power afterS=<seconds lowered> distM=<metres to the first fix after>` |
| Lowering checked | on a fix / power change | also on the 20 s check (a silent stop lowers too) |

Live Motion runs only while lowered. Walk-away and auto-finish run on the 20 s check with no fix
(test: lowered, walk < 50 m, ends at the stop).

### Decision after the corner scenario (2026-11-09)

Analysis: at a light Core Motion rarely reads stationary (drives of 2026-11-08/09: `stationaryS` 0–17
over 10 stops each), so the reading in force when following starts is the drive's own automotive one.
Two defects found and fixed: that reading raised the GPS the moment it lowered (now only a reading
begun after lowering counts), and a resume after a pause counted the pause as a stop. With Motion
silent, the GPS comes back only at the 50 m fix (~14 s after moving off, first Best fix ~15–17 s,
55–65 m out): a turn 8 m after the line is cut, ~8 m off the corner, ~7.5 m short.

Owner decision: `lowerWhileStoppedOnBattery = false` (B1 only in Low Power Mode, where the person
chose battery over the corner); no 20 m filter (Wi-Fi noise), no road snapping (new algorithm). Keep
90 s/60 s, both fixes, the 20 s check; add `distM=` to the raise line. 2a keeps querying Motion from
the window's opening; if the device log shows the automotive reading in force is missed, 2b queries
from 60 s before it.

## Tests (both sides)

- 2a: 29/30 s and 59/60 s; 14/15 fixes; 14.9/15 m; 0.99/1.0 m/s trusted, raw 1.1 m/s untrusted
  passes; Motion automotive/cycling blocks, stationary passes; no access → 60 s; car audio blocks;
  extended never; one Motion query per window; a late answer is dropped.
- 3: battery 89/90 s; Low Power 59/60 s; charging never; Motion moving raises, stationary does
  not; fix raises and the stop counts 90 s again; power raises; walk-away while lowered ends the
  drive; Motion follow stops when raised and at the end.

## Device checks

- Carodo keeps running in the background with lowered GPS; `raisedBy`/`afterS` on real stops.
- `wouldExitS` and `spreadM` on false and real windows; what Motion reads at a gate.
- Battery %/h before and after (Developer → Battery).
