# Study follow-ups: hot-phone GPS, MetricKit diagnostics, versioned place sweeps (L2, L3, L4)

Status: approved 2026-11-13 with every recommended decision (D2.1 no, D2.2 no, D3.1 Developer
only, D4.1 yes). **L2 committed** 2026-11-13 (carodo-ios `1c29c11`): the thermal state is read fresh on every fix (Pilgrim's guard re-reads it the same way), so the desk check was dropped (Xcode 27 has no thermal condition for an iPhone) and the log of real drives measures it (PV-17). **L3 built and committed** 2026-11-13 (carodo-ios `03bafd8`; device check PV-18). L4: not started.
L5 is handed to another agent.
Source: [`references/repos/drive-recorders-study.md`](../references/repos/drive-recorders-study.md)
L2, L3, L4. Audited at carodo-ios `caf0915` (after the repository split `7260c5f` and the perf
commits `53edd24`, `b39f20c`).

Three independent slices, each one commit, in this order: **L2 → L3 → L4**. L4 changes the
schema, so it goes last and alone (one `CONFIRM=erase` on the iPhones).

---

## L2 — A hot phone gives up navigation accuracy

### What the code does today (files read)

- `Core/Recording/RecordingGPS.swift`: one pure rule `settings(_ Conditions, rules:)`, first match
  wins: (1) lasting stop, not charging, Low Power Mode or `lowerWhileStoppedOnBattery` (off in
  production) → 100 m, 50 m filter, `why=stopped`; (2) charging → `BestForNavigation`,
  `why=charging`; (3) otherwise → `Best`, `why=battery`. `Conditions` holds vehicle class,
  charging, Low Power Mode and the stop's age; there is no thermal input.
- `Core/Diagnostics/BatteryMonitor.swift`: reads battery state and Low Power Mode, calls
  `onPowerChange` when charging or Low Power Mode flips; logs a `battery` entry at a drive's start,
  end and each level change.
- `App/DependencyContainer.swift:490-491`: `driveSession.power = { (battery.isCharging,
  battery.isLowPower) }`, `battery.onPowerChange = { driveSession.powerChanged() }`.
- `DriveSessionManager.applyGPS` (`:811`) builds `Conditions` from `power()` and applies a change
  with its log line.
- `docs/tracking.md` "Recording GPS" holds the three-row table. Nothing in code or docs reads
  `ProcessInfo.thermalState`.

**The gap.** The case where a phone runs hottest (mounted on the windscreen in the sun, charging
over CarPlay) is exactly the case that selects `BestForNavigation`, the most expensive mode. When
the phone reaches `.serious`, iOS throttles the app and may end it; a drive that loses the app
loses its track until relaunch.

### Proposal

1. `RecordingGPS.Conditions` gains `thermal: Thermal` (`nominal`, `fair`, `serious`, `critical`),
   a plain enum mapped from `ProcessInfo.ThermalState` in the adapter only; the rule stays pure.
2. The rule, first match wins (new row 2):

   | # | When | Accuracy | Filter | `why=` |
   |---|---|---|---|---|
   | 1 | Lasting stop (unchanged) | 100 m | 50 m | `stopped` |
   | 2 | Thermal `serious` or `critical` | `Best` | none | `hot` |
   | 3 | Charging | `BestForNavigation` | none | `charging` |
   | 4 | Otherwise | `Best` | none | `battery` |

   On battery row 2 changes only the log reason (it was `Best` already); while charging it gives up
   navigation accuracy. The route keeps every fix: `Best` is what every battery drive records with.
3. `BatteryMonitor` (already the one source of power conditions for the session) also observes
   `ProcessInfo.thermalStateDidChangeNotification`, keeps `thermal`, and calls `onPowerChange`
   when it changes. `power` returns the thermal state too. `RaiseCause.power` covers it (its
   comment says so).
4. Log: the `battery` entry gains `thermal=nominal|fair|serious|critical`, and a thermal change
   during a drive writes a `battery moment=drive` line like a level change. The field is a state,
   not an identifier or a time: `sharedKeys` (`TrackingLogFieldsTests`).
5. Docs: `docs/tracking.md` table and its paragraph; `docs/specs/developer-mode.md` (Battery, the
   line format).

### Owner decisions

- **D2.1 — At `critical`, also lower the GPS at a lasting stop even on battery?** Recommendation:
  **no** for now. It would cut the corner after a long light (the 2026-11-09 reason B1 is off on
  battery); revisit if a field log shows `critical` drives ending.
- **D2.2 — Use the battery level as Pilgrim does (≤ 20 %)?** Recommendation: **no**, it stays out
  (the 2026-11-09 "battery off" decision; a car usually charges the phone).

### Acceptance

- `RecordingGPSTests`: both sides of the threshold: charging + `fair` → navigation; charging +
  `serious` → `Best why=hot`; charging + `critical` → `Best why=hot`; battery + `serious` → `Best
  why=hot`; a lasting stop in Low Power Mode + `serious` → still `stopped` (row 1 first).
- A session test: a thermal change while recording re-applies the rule and logs the change.
- `TrackingLogFieldsTests` passes with `thermal` in `sharedKeys`.
- `task lint`, `task warnings`, `task test` pass.
- **Device check (required before commit):** Xcode → Devices and Simulators → the iPhone → Device
  Conditions → Thermal State "Serious" during a charging drive (or a stationary recording on a
  cable): the log shows `gps accuracy=best … why=hot`, then `why=charging` after the condition is
  stopped. Confirm the notification arrives while the app is in the background.

### Files

`RecordingGPS.swift`, `BatteryMonitor.swift`, `DriveSessionManager.swift` (the `power` tuple),
`DependencyContainer.swift` (one line), `TrackingLog.swift` (the `battery` entry),
`DiagnosticsLogFormat.swift`, tests above, `docs/tracking.md`, `docs/specs/developer-mode.md`.
No schema, permission, entitlement or dependency change.

---

## L3 — Why iOS ended Carodo: MetricKit exits and diagnostics

### What the code does today

- `Core/Diagnostics/MetricKitStore.swift`: subscribes to `MXMetricManager`, keeps from each daily
  `MXMetricPayload` an `EnergyReport` (foreground, background, background-location and CPU time;
  location time by accuracy) in `Application Support/Carodo/energy-report.json`.
  `didReceive(_: [MXDiagnosticPayload])` is not implemented, and `applicationExitMetrics` is not
  read.
- `Features/Developer/Views/DeveloperView.swift` shows the energy report
  (`docs/specs/developer-mode.md`, Battery).
- Field tests read only the tracking log; a drive whose app iOS ended in the background shows a
  gap and a recovery, never the reason.

### Proposal

1. **Exit reasons (daily).** From `MXMetricPayload.applicationExitMetrics.backgroundExitData`
   (and foreground), keep the counts by reason: memory limit, memory pressure, CPU limit,
   watchdog, locked file, background-task timeout, bad access, illegal instruction, abnormal,
   normal. Stored beside the energy report as new optional fields (an old file still decodes).
   Shown on the Battery & energy page: "Ended by iOS in the background (last report)".
2. **Diagnostics (crash, hang, CPU exception, disk-write exception).** Implement
   `didReceive(_: [MXDiagnosticPayload])`: keep each diagnostic's kind, build, OS, signal or
   exception type, termination reason, hang duration, its time, and the call stack as
   `jsonRepresentation()`, one file each in `Application Support/Carodo/diagnostics/`.
   **Bound (the risk it prevents: a crash loop filling the disk):** the newest 20 files and 2 MB
   in total; older ones are deleted on write.
3. **Developer → Logs → Crashes and hangs**: the list (kind, build, OS, when), a detail view, and
   Share as `.json` for symbolication on the Mac. Developer only; nothing is sent anywhere by
   itself. The payload carries no coordinates; its exact times are the person's own data shown
   back to them (P9 exception), and they never enter the shared log.
4. Docs: `docs/specs/developer-mode.md` (Battery & energy, Logs), `docs/operations/device-testing.md`
   (read the exits after a field test).

### Found on the way (to confirm while building)

Done in `03bafd8`: the store is `@Observable` now. `MetricKitStore` was not `@Observable`, so `latest` changing on the main actor may not refresh an
open Developer page. If so, fix it in this slice (a one-word change, with the store's
`nonisolated deinit` kept).

### Owner decisions

- **D3.1 — Developer only, or also a line in Settings → Drive diagnostics** ("iOS ended Carodo in
  the background N times yesterday")? Recommendation: **Developer only** for now; the shared
  diagnostics stay about what the person can fix.

### Acceptance

- `MetricKitStoreTests` (new) with fixture payload values: exit counts mapped; an old
  `energy-report.json` without the new fields still decodes; diagnostics kept newest-first and
  pruned at 20 files and at 2 MB; a damaged diagnostic file is skipped, not a crash (foreign bytes
  get bounds).
- Screenshots: the Battery & energy page and Crashes and hangs (Light, Dark, a large Dynamic Type
  size, Vietnamese), strings in the Developer catalog with English and Vietnamese.
- `task lint`, `task warnings`, `task test` pass.
- **Device check:** Xcode → Debug → Simulate MetricKit Payloads on the iPhone fills both pages.
  Real payloads arrive about a day later (diagnostics sooner); read them after the next field test.

### Files

`MetricKitStore.swift`, `DeveloperView.swift` and a new page under `Features/Developer/Views/`,
`Developer.xcstrings`, `CarodoTests/MetricKitStoreTests.swift`, the two docs above. No schema,
permission, entitlement or dependency change (MetricKit needs none).

---

## L4 — Place sweeps select by rules version, not by "done once"

### What the code does today

- `trips.places_looked_up_at` (REAL): `PlaceNaming.run` picks
  `WHERE … places_looked_up_at IS NULL` (`GRDBJourneyRepository+Places.swift:63`), keys each end
  to a `PlaceKey` cell, looks up cells older than `PlaceNaming.lookupVersion` (2), then
  `setPlaceKeys` writes `start_cell`, `end_cell`, the timestamp, clears the narrative, and **always**
  sets `ck_pending` and bumps `revision` (`:166`).
- `trips.points_matched_at` (REAL): `PlaceDetection.run` (`Core/Recording/PlaceDetectionRun.swift`)
  picks `WHERE … points_matched_at IS NULL` (`:123`), makes detected places for the journey's
  points that no place holds yet (`newPlaces(…among: places)`), and stamps the time (`:142`).
- Both are set back to NULL by a trim, a join or split, a re-derive and a track from iCloud
  (`+Joins.swift:155,201`, `+Edits.swift:290,337`, `GRDBCloudSyncStore.swift:349`).
- Everything else derived carries a version: `recorder_version` with `SummaryRefresh`,
  `trip_gaps.rules_version`, `geocoded_cells.lookup_version`, `narrative_version`,
  `trip_tracks.codec_version`.

**The gap.** A change to how a trip's ends are keyed (`PlaceKey`, which ends count after a trim)
or to how points become places (`PlaceDetection.Configuration`, `StopPlaceResolver`) never reaches
a trip already done. Pre-release, the in-place schema and reinstall hide it; from the first
TestFlight build it becomes a silent difference between old and new drives.

### Proposal

1. Replace the two timestamps by versions, as `recorder_version` does:
   `places_version INTEGER NOT NULL DEFAULT 0` and `points_version INTEGER NOT NULL DEFAULT 0`
   (0 = never done). The timestamps are read only as NULL markers today; nothing shows them.
2. `PlaceNaming.rulesVersion = 1` (how a trip's ends become cells; `lookupVersion` stays what a
   cell holds) and `PlaceDetection.rulesVersion = 1`. Each comment says when to bump it.
   The sweeps select `WHERE places_version < ?` / `WHERE points_version < ?`.
3. Every reset writes `0` instead of NULL (the five places listed above).
4. **A bump must not re-upload every drive.** `setPlaceKeys` sets `ck_pending`, bumps `revision`
   and clears the narrative **only when `start_cell` or `end_cell` actually changes**; otherwise it
   only records the version (what `SummaryRefresh` does with `markDerived`). Today it rewrites
   unconditionally; harmless while each trip is named once, a full iCloud upload after a bump.
5. Re-matching points stays safe: `newPlaces(…among: places)` makes a place only where no place
   holds the point, so a re-run never duplicates. It also never removes a place made under the old
   rules; that is accepted (a place the person can see and delete), and the Apple budget per run
   (`budget: 12`, `limit: 20`) already spreads a full re-run over several launches.
6. `docs/data-model.md`: the two columns, and the rule under "Ownership" or "Derived data":
   *a change to how stored derived data is computed bumps its version, even when its shape does
   not change; a sweep selects by version, never by presence*.

### Owner decisions

- **D4.1 — Schema change (P6):** replace the two `_at` columns by `places_version` and
  `points_version` in `v1_initial`. Recommendation: **yes**. Cost: the next `task device` stops on
  the schema change; back up, `CONFIRM=erase`, restore the `.carodo` (TD-20's routine). After a
  restore every trip is at version 0 and is named and matched again, 20 at a time.
- **D4.2 — Alternative:** keep the timestamps and add the version columns beside them. Not
  recommended: two markers for one fact.

### Acceptance

- `DatabaseManagerTests`: the migrator on an in-memory `DatabaseQueue` creates both columns with
  default 0.
- `PlaceNamingTests`: a trip at the current version is skipped; one below is redone; an unchanged
  result records the version without bumping `revision` or setting `ck_pending`; a changed cell
  does both and clears the narrative.
- `PlaceDetectionTests`: a journey below the version is matched again with no duplicate place.
- Each reset path (trim, join, split, re-derive, iCloud track) sets the versions to 0 (existing
  tests updated).
- `task lint`, `task warnings`, `task test` pass; the `DriveDataReplayTests` replays unchanged.
- Device: after `CONFIRM=erase` and the restore, titles and journey points come back over a few
  launches; the tracking log shows the naming runs.

### Files

`DatabaseManager.swift` (`v1_initial`), `GRDBJourneyRepository+Places.swift`, `+Joins.swift`,
`+Edits.swift`, `GRDBCloudSyncStore.swift`, `Core/Repositories/TripStores.swift` (comments,
`markDerived`-style method if needed), `PlaceNaming.swift`, `PlaceDetectionRun.swift`, tests above,
`docs/data-model.md`. Schema change: yes (D4.1). No API, permission or dependency change.

---

## Non-goals

- Live Activity (L1), the End-drive intent (L6) and `docs/solutions/` (L5): separate plans.
- Battery-level tiers, Pilgrim's checkpoint file, sending any diagnostic off the device.
- Removing places made under old detection rules.

## Risks

- L2 depends on iOS delivering `thermalStateDidChangeNotification` to a backgrounded recording
  app: the device check decides; if it does not arrive, read `ProcessInfo.thermalState` on each
  fix instead (the session already re-asks the rule on every fix).
- L3: MetricKit delivers on its own schedule; a field test may end before its payload arrives.
- L4: the erase on the owner's iPhones; a backup must be taken first.
