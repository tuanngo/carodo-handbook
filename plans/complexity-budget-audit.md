# Complexity budget audit — findings and fix brief (2026-11-07)

Status: **Closed 2026-11-07: F1–F6 fixed in carodo-ios (uncommitted).** One thing left, carried to
the next field test (`field-tests/`): on the iPhone, CPU with the Map tab open (F2) and the expanded
panel open (F1) while recording, before vs after; installed on TuanNgo iPhone 2026-11-07 12:30.
1153 unit tests pass; lint clean on the touched files. Notes from the fix: F1 also removed
`DriveMetrics.elevation` and `RouteRecorder.Configuration.elevationStepM` (only the chart read them;
`docs/tracking.md` row dropped). F2 split `AtlasOverlayGroup.live` into `liveCasing`,
`liveTipCasing`, `live`, `liveTip` (both casings under both lines); `LiveLine` exposes `keptRuns` and
`tip`. F6b also indexes the narration's drive endpoints (a second search in the same loop).
Originally: Read-only audit of `carodo-ios` against the complexity
budget (`carodo-ios/docs/architecture.md#complexity-budget`). Costs below are estimated from the
code, not measured: each fix is confirmed by a test of the large case and, where marked, on the
iPhone. Re-check each finding against the current code before fixing it (the tree moves fast).

Budget reminder: O(1) per GPS fix and per frame/body/tick; O(k) per changed journey; no O(n²) over
a drive's samples; no array search inside a loop over another; one query (transaction) per
screen/batch, not per row. `n` = fixes of one drive (3 h ≈ 10,000), `N` = drives (design: 2,000).

## Owner decision (2026-11-07): remove the live elevation chart

**Decided: F1 removes the elevation chart from the expanded recording panel; the altitude row
stays.** Why: the panel is a driving surface (legible at a glance, no interaction while moving); a
profile of the road behind adds little while driving, and the Journey Detail page shows the full
profile right after the drive. The current altitude stays as a row (`RecordingPanels.swift` ~line
386). Removing the chart removes the cost entirely, so no downsampling is needed here.

- Update `docs/specs/drive-recording.md` (lines ~116–118 mention the elevation profile) in the same change.
- Remove what only the chart used (the private `ElevationChart` wrapper in `RecordingPanels.swift`;
  any string only it used, from the catalog in English and Vietnamese). `ElevationProfileChart`
  stays: Journey Detail uses it.
- Keep `DriveMetrics.elevation` unless nothing else reads it live; if the finished drive's summary
  or tests read it, leave it.

## Findings

| # | Severity | Path broken | Where | What |
|---|---|---|---|---|
| F1 | Medium | per tick (1 s) while recording, panel expanded | `Features/Drive/Views/RecordingPanels.swift` ~302; `DesignSystem/Components/ElevationProfileChart.swift` | The expanded panel lives in `TimelineView(.periodic(by: 1))`; every second `ElevationProfileChart` recomputes min/max over all points and rebuilds 2 Swift Charts marks per point. `metrics.elevation` grows every 50 m with no cap: 200 km ≈ 4,000 points ≈ 8,000 marks/s |
| F2 | Medium | per GPS fix, Map tab while recording | `Features/Map/Views/AtlasMapView.swift` ~65–72 (`AtlasOverlaySync.apply`), `AtlasOverlays.live` | Any move of the live line's end changes `LiveKey`, so `replace(.live)` rebuilds `MKPolyline`s for every kept point (2 overlays: casing + line): O(m) per fix, m = kept points (hundreds to ~1,000 on a long drive) |
| F3a | Low (high once) | first iCloud sync / restore | `Core/Sync/CloudSyncService.swift` ~232 (`enqueue`) | `waiting` is an array; `changes.filter { !waiting.contains($0) }` is O(n·m): ~4 M comparisons for 2,000 trips |
| F3b | Low | per sent batch | `Core/Sync/CloudSyncService.swift` ~389–397, `GRDBCloudSyncStore.markSent` | One write transaction per saved record (100 per batch) |
| F4 | Low | per frame while a trim grip is dragged | `Features/Journeys/Views/JourneyTrimSheet.swift` ~116, 270 | `route.map(\.coordinate)` over the whole route every body pass; the kept part already uses binary search |
| F5 | Low | per body, Passport milestones page | `Features/Passport/Views/PassportStampsSection.swift` ~428–434 (`detail(for:)`) | Evaluated for every `NavigationLink` value: each milestone filters all N journeys (`journeys` is `[UUID: Journey]`) |
| F6a | Very low | per Passport load | `Core/Domain/Achievements.swift` ~252 | Per-vehicle distance sums recomputed for each vehicle-scoped badge definition |
| F6b | Very low (O(N²) after a restore) | narration of pending drives | `Core/Narrative/JourneyNarration.swift` ~41 | `history.first(id:)` per pending journey |

## Fix brief (one commit per finding)

```text
Outcome: every path within the complexity budget, with no visible change except F1 (the live
  elevation chart removed, owner's decision).
Acceptance criteria:
  F1  owner decision above: the chart is gone from the expanded recording panel, the altitude row
      stays, the panel's 1 s tick no longer does work that grows with the drive; the spec updated.
  F2  live overlays split: the kept part replaced only when a point is kept or a run breaks; the tip
      (last kept point → newest fix) is its own 2-point overlay. Order and look unchanged (casing
      under line); a pause still never bridges runs. Test: N fixes along a straight road rebuild
      the kept overlay O(1) times, the tip each fix.
  F3a Set of pending changes (CKSyncEngine.PendingRecordZoneChange is Hashable; verify).
  F3b markSent over the batch in one transaction (keep the per-record CASE semantics).
  F4  coordinates of the whole route computed once per loaded track (model), not per body.
  F5  journeys of a milestone by lookup: trips.compactMap { journeys[$0] }, O(k).
  F6a sums computed once before the definitions loop.
  F6b history indexed once (Dictionary by id) before the loop.
Non-goals: new features; changing measured values (distance, speeds); the GPS-distance question
  (separate: architecture.md Reference, "GPS distance at a crawl").
Relevant docs: carodo-ios/docs/architecture.md (Algorithms; Complexity budget),
  docs/design-system.md#map-rules--learned-the-hard-way, docs/specs/drive-recording.md.
Constraints: carodo-ios/AGENTS.md (Swift 6 main-actor default, no Task.detached, swift-format).
Validation: task ios:test, task ios:lint; device: Map tab recording a drive (F2) and expanded
  panel (F1) in Time Profiler / Activity Monitor before and after, same method as
  plans/perf-resource-audit.md.
Do not: cap or merge lines to fit (map rules); change the persistence schema; commit without being asked.
```

## Checked and within budget

- `RouteRecorder`, `StopDetector`, sample writes: O(1) per fix; the growing route is mutated in place
  (views read `metrics` transiently, no lasting copy).
- `LiveLine.append`: O(points since the last kept one), bounded by `maxSpanM` (250 m).
- `RouteHeatIndex`, `HistoryAtlas` footprint: incremental, cached per zoom.
- `ProvinceBisection` visit pass: the gap check scans disjoint slices, O(n) in total.
- Journeys list: rebuilt on data change only, paged.
- Backup restore and iCloud apply: per-row statements inside one transaction, primary-key lookups.
- Searches inside loops over small arrays (vehicles, places, badge definitions; ~10–30 items): accepted.
