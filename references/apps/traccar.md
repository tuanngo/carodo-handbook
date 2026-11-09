# Traccar: trip rules compared with Carodo's

Moved from carodo-ios `docs/tracking.md` on 2026-11-07 (reference, not a rule).

Traccar (open-source GPS tracking server, Apache 2.0; ideas only, no code) cuts trips on the server
from stored positions, so a new setting re-cuts history, as `SummaryRefresh` does here.

| Traccar (`report.trip.*`, defaults) | Carodo | Note |
|---|---|---|
| Stop = no position within `minDistance` 200 m during `minDuration` 180 s (displacement, no speed) | stopped = ≤ 3 km/h for 30 s, moving again = ≥ 12 km/h (speed, hysteresis) | Speed reacts sooner; displacement ignores GPS speed spikes while parked. `RouteRecorder`'s stop anchor ends a stop only at a trusted 2 m/s or 100 m from it, which trims the parked jitter; a speed within 2 × its accuracy never ends a stop in either (`speedTrustFactor`) |
| Moving: start backdated to where the movement began | detection seeds the session with its confirming fixes | same idea |
| `minimalParkingDuration` 300 s: a shorter parking never splits a trip | stop grace 300 s, then Stop and wait joins waits ≤ 20 min, ≤ 150 m, same vehicle, no walking | Carodo's join is stricter (walking keeps an errand apart) |
| `minimalTripDistance` 500 m / `minimalTripDuration` 300 s | short drive: < 500 m or < 120 s moving | same distance; Carodo counts moving time, not the whole duration |
| `minimalNoDataDuration` / `stopGap` 3600 s: a data gap counts as a stop | `completionTimeoutS` 720 s with no usable fix ends the drive | a phone, not a tracker: GPS gaps are tunnels and pockets |
| `useIgnition`: ignition on/off defines trips | CarPlay / linked audio is only a hint that shortens the grace while stopped (P4) | a phone cannot read ignition |

